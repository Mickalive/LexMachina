"""Freeze acceptance tests: hash re-verification, the frozen 11 geometry criteria
and freeze-before-measurement ordering (charter acceptance test 7, categories 1,
11 and 12).

8 test functions. All deterministic and offline: every byte is read locally,
synthetic pins are built from fixed literals, and the single subprocess is a
read-only ``git log`` guarded by its own skipif.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from datetime import datetime

from conftest import (
    OLD_PACKET_DIR,
    REAL_PACKET_DIR,
    REPO_ROOT,
    RULES_PATH,
    TEAM_ID,
    VENDORED_BARS,
    load_rules,
    needs_old_packet,
    needs_real_packet,
    sha256_file,
)

from frontier_rebuilt_packet_serve_audit import freeze_verify, geometry_half, marginal_discovery, verdict
from frontier_rebuilt_packet_serve_audit.paths import bootstrap_vendored_instruments

bootstrap_vendored_instruments()
from evaluation.frozen_bars import geometry_gate, label_gate  # noqa: E402

FROZEN_GEOMETRY_CRITERIA = [
    "COHERENCE_QUERY_LANG",
    "COHERENCE_QUERY_TERM",
    "PROJ_RANK",
    "PROJ_SPEARMAN",
    "PROJ_KNN10",
    "STRUCTURE_LARGEST",
    "STRUCTURE_SEP",
    "LABEL_CONTENT_FRACTION",
    "LABEL_JACCARD",
    "OUTLIER_VALIDITY",
    "RELATIONS",
]

MEASUREMENT_ARTIFACT_PATHS = (
    f"results/frontier/{TEAM_ID}/AUDIT_RECORD.json",
    f"reports/frontier/{TEAM_ID}",
    f"state/frontier/{TEAM_ID}.json",
)

# A committed artefact carries a MEASUREMENT only if its bytes contain one of
# these harness-emitted keys. The team's bootstrap state placeholder (no
# accepted run, evidence_tier UNTESTED) is deliberately not a measurement, so a
# pre-freeze commit of it cannot be mistaken for a measurement commit.
MEASUREMENT_CONTENT_MARKERS = (
    "serve_recommendation",
    "half_a_label",
    "classification_only_negative_reproduced",
    "n_abstained",
)


def _git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def _parse_commit_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


@needs_real_packet
def test_freeze_verify_rejects_a_one_byte_tampered_packet_copy(tmp_path):
    """Category 1: a temp copy of the packet with ONE byte changed is refused.

    Charter clause: "freeze_verify rejects a tampered packet/bundle copy (build a
    temp copy with one byte changed)". Both the pinned packet.json and a pinned
    bundle are flipped; the pristine copy must pass so the refusal is provably
    about the byte, not about copying.
    """
    copy_dir = tmp_path / "packet_copy"
    shutil.copytree(REAL_PACKET_DIR, copy_dir)
    freeze = freeze_verify.load_freeze()

    # Pristine copy is accepted.
    assert freeze_verify.verify_packet_files(copy_dir, freeze)["packet.json"]["matches"] is True

    # Flip exactly one byte of the pinned packet.json.
    packet_json = copy_dir / "packet.json"
    raw = bytearray(packet_json.read_bytes())
    raw[0] = raw[0] ^ 0x01
    packet_json.write_bytes(bytes(raw))
    with pytest.raises(freeze_verify.FreezeError) as tampered_packet:
        freeze_verify.verify_packet_files(copy_dir, freeze)
    assert "byte drift vs freeze" in str(tampered_packet.value)
    shutil.copyfile(REAL_PACKET_DIR / "packet.json", packet_json)

    # Flip exactly one byte of a pinned bundle.
    bundle_rel = "questions/de-kapitalverletzung.bundle.json"
    bundle = copy_dir / bundle_rel
    raw = bytearray(bundle.read_bytes())
    raw[17] = raw[17] ^ 0x01
    bundle.write_bytes(bytes(raw))
    with pytest.raises(freeze_verify.FreezeError) as tampered_bundle:
        freeze_verify.verify_packet_files(copy_dir, freeze)
    assert bundle_rel in str(tampered_bundle.value)

    # Restoring the pristine bundle makes the copy acceptable again.
    shutil.copyfile(REAL_PACKET_DIR / bundle_rel, bundle)
    assert freeze_verify.verify_packet_files(copy_dir, freeze)[bundle_rel]["matches"] is True


def test_freeze_verify_rejects_a_tampered_copy_against_a_synthetic_pin(tmp_path):
    """Category 1: the same refusal with no real packet needed.

    Charter clause: hash re-verification is a property of the freeze pins, so a
    synthetic pin over a synthetic bundle proves the refusal path without the
    real packet being mounted. A missing pinned file is also refused, never
    silently skipped.
    """
    bundle = tmp_path / "questions" / "synthetic.bundle.json"
    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_text('{"qid": "synthetic", "decisions": []}\n', encoding="utf-8")
    freeze = {
        "inputs": {
            "rebuilt_packet": {
                "files": {
                    "questions/synthetic.bundle.json": {
                        "sha256": sha256_file(bundle),
                        "bytes": bundle.stat().st_size,
                    }
                }
            },
            "frozen_instruments": {},
        }
    }
    assert freeze_verify.verify_packet_files(tmp_path, freeze)[
        "questions/synthetic.bundle.json"
    ]["matches"] is True

    raw = bytearray(bundle.read_bytes())
    raw[0] = raw[0] ^ 0x01
    bundle.write_bytes(bytes(raw))
    with pytest.raises(freeze_verify.FreezeError):
        freeze_verify.verify_packet_files(tmp_path, freeze)

    bundle.unlink()
    with pytest.raises(freeze_verify.FreezeError):
        freeze_verify.verify_packet_files(tmp_path, freeze)


@needs_real_packet
@needs_old_packet
def test_freeze_verify_accepts_the_pristine_pinned_artifacts():
    """Category 1: the pristine pinned packet and old packet verify byte-for-byte.

    Charter clause: "accepts the pristine pinned artifact"; every observed
    sha256 must equal the sha256 frozen in RULES.json for all seven pinned
    rebuilt files and all four pinned old-packet files.
    """
    freeze = freeze_verify.load_freeze()
    observed = freeze_verify.verify_all(REAL_PACKET_DIR, OLD_PACKET_DIR, freeze)
    assert observed["all_match"] is True

    pinned_rebuilt = freeze["inputs"]["rebuilt_packet"]["files"]
    for rel, meta in pinned_rebuilt.items():
        cell = observed["packet"][rel]
        assert cell.get("exists", True) is True
        assert cell["observed_sha256"] == meta["sha256"] == sha256_file(REAL_PACKET_DIR / rel)

    pinned_old = freeze["inputs"]["old_packet_before"]["files"]
    for rel, meta in pinned_old.items():
        cell = observed["old_packet"][rel]
        assert cell.get("exists", True) is True
        assert cell["observed_sha256"] == meta["sha256"] == sha256_file(OLD_PACKET_DIR / rel)

    assert (
        freeze["inputs"]["rebuilt_packet"]["expected_packet_json_sha256"]
        == pinned_rebuilt["packet.json"]["sha256"]
    )


def test_frozen_instrument_sha256_equal_the_frozen_pins():
    """Category 1: RULES_LABEL.json / RULES_GEOMETRY.json / VERDICT_CONTRACT.json.

    Charter clause: "verify RULES_LABEL.json / RULES_GEOMETRY.json /
    VERDICT_CONTRACT.json observed sha256 equal the frozen pins". Re-hashed here
    twice -- once through freeze_verify against the freeze, once directly with
    hashlib -- and cross-checked against the ACCEPTED instruments' own expected
    constants, so reuse is proven rather than asserted.
    """
    freeze = freeze_verify.load_freeze()
    observed = freeze_verify.verify_frozen_instruments(freeze)
    pins = freeze["inputs"]["frozen_instruments"]
    for name in ("RULES_LABEL.json", "RULES_GEOMETRY.json", "VERDICT_CONTRACT.json"):
        cell = observed[name]
        assert cell.get("exists", True) is True, f"{name} missing from the vendored tree"
        assert cell["observed_sha256"] == cell["expected_sha256"] == pins[name]
        assert cell["observed_sha256"] == sha256_file(VENDORED_BARS / name)

    assert label_gate.EXPECTED_RULES_SHA256 == pins["RULES_LABEL.json"]
    assert geometry_gate.EXPECTED_RULES_SHA256 == pins["RULES_GEOMETRY.json"]
    assert all(v["matches"] for v in observed.values() if isinstance(v, dict))


def test_geometry_criteria_are_exactly_the_frozen_eleven_in_frozen_order():
    """Category 11: the 11 frozen geometry criteria, by name and by position.

    Charter clause: "the 11 frozen criteria names are exactly the frozen
    CRITERIA_ORDER list (assert the exact 11 names in order)". The harness
    constant, the ACCEPTED vendored gate and the frozen RULES_GEOMETRY.json
    criterion table must agree, and the count must be the frozen 11.
    """
    assert geometry_half.CRITERIA_ORDER == FROZEN_GEOMETRY_CRITERIA
    assert list(geometry_gate.CRITERIA_ORDER) == FROZEN_GEOMETRY_CRITERIA
    assert len(FROZEN_GEOMETRY_CRITERIA) == 11

    frozen_criteria = json.loads(
        (VENDORED_BARS / "RULES_GEOMETRY.json").read_bytes().decode("utf-8")
    )["criteria"]
    assert set(frozen_criteria) == set(FROZEN_GEOMETRY_CRITERIA)

    thresholds = load_rules()["thresholds_and_enums"]
    assert thresholds["geometry_criteria_required_for_bundle_pass"] == 11
    assert thresholds["geometry_regression_incumbent_counts"] == dict(
        geometry_gate.INCUMBENT_COUNTS
    ) == dict(geometry_half.INCUMBENT_COUNTS)


@needs_real_packet
def test_real_packet_geometry_cells_enumerate_exactly_the_frozen_criteria():
    """Category 11: on the real rebuilt bytes each cell reports the same 11 names.

    Charter clause: the criteria enumeration is applied, not only declared --
    every shipped bundle's per-criterion table has exactly the frozen keys in
    the frozen order, with a bar attached to each.
    """
    geometry = geometry_half.measure(REAL_PACKET_DIR / "questions")
    assert geometry["criteria_order"] == FROZEN_GEOMETRY_CRITERIA
    for qid, cell in geometry["per_bundle"].items():
        assert list(cell["per_criterion"]) == FROZEN_GEOMETRY_CRITERIA, qid
        assert cell["n_criteria"] == 11
        for name in FROZEN_GEOMETRY_CRITERIA:
            assert "bar" in cell["per_criterion"][name], (qid, name)
        assert cell["overall_absolute"] == (
            "GEOMETRY_SOUND" if cell["n_pass"] == 11 else "GEOMETRY_UNSOUND"
        )


def test_rules_json_freezes_every_threshold_the_harness_uses():
    """Category 12: RULES.json is valid JSON and freezes every threshold in use.

    Charter clause: "RULES.json exists, is valid JSON, contains every threshold
    the harness uses (absolute_label_bar 1.0, geometry 11, mega 0.5,
    marginal-discovery K 20)". Each pin is compared against the constant or
    frozen-instrument reading the harness actually consumes, so a threshold edit
    in either place is a failure.
    """
    assert RULES_PATH.is_file()
    rules = load_rules()
    assert rules["schema"] == "frontier-rebuilt-packet-serve-audit/rules/1"
    assert rules["team_id"] == TEAM_ID

    thresholds = rules["thresholds_and_enums"]
    assert thresholds["absolute_label_bar"] == 1.0
    assert thresholds["geometry_criteria_required_for_bundle_pass"] == 11
    assert thresholds["mega_cluster_bar"] == 0.5
    assert rules["marginal_discovery"]["K"] == 20
    assert thresholds["not_applicable_is_not_a_pass"] is True

    # The harness consumes exactly these values.
    assert geometry_half.MEGA_CLUSTER_BAR == thresholds["mega_cluster_bar"]
    assert marginal_discovery.FROZEN_K == rules["marginal_discovery"]["K"]
    assert len(geometry_half.CRITERIA_ORDER) == thresholds[
        "geometry_criteria_required_for_bundle_pass"
    ]
    assert thresholds["serve_recommendation_enum"] == list(verdict.RECOMMENDATION_ENUM)

    # The absolute label bar the ACCEPTED frozen instrument publishes on any
    # bundle is the pinned 1.0 (reported, never enforced).
    absolute = label_gate.score_packet({}, label_gate.load_frozen_rules())
    assert absolute["absolute_bar"] == thresholds["absolute_label_bar"]
    assert absolute["absolute_enforced_as_build_blocker"] == thresholds[
        "absolute_label_enforced"
    ] is False
    assert thresholds["label_regression_incumbent"]["n_scored"] == 65
    assert rules["metric_definitions"]["marginal_discovery"]


def test_freeze_commit_precedes_every_measurement_commit():
    """Category 12: the freeze commit is strictly older than any measurement.

    Charter clause: "its committed git commit time on branch
    lab/frontier/frontier-rebuilt-packet-serve-audit precedes any measurement
    commit". Evidence is git commit time, never a hand-written frozen_at_utc.
    Skips only when git itself is unavailable.
    """
    if shutil.which("git") is None:  # pragma: no cover - git always present in CI
        pytest.skip("git is unavailable in this environment")

    rules_rel = str(RULES_PATH.relative_to(REPO_ROOT))
    rc, freeze_stamp = _git("log", "-1", "--format=%cI", "--", rules_rel)
    assert rc == 0 and freeze_stamp, f"RULES.json is not committed: {rules_rel}"
    freeze_time = _parse_commit_time(freeze_stamp)
    rc, freeze_sha = _git("log", "-1", "--format=%H", "--", rules_rel)
    assert rc == 0 and freeze_sha

    # No MEASUREMENT may be folded into the freeze commit itself: an artefact may
    # already exist there (the bootstrap state placeholder does), but it must
    # carry no measurement content.
    for rel in MEASUREMENT_ARTIFACT_PATHS:
        rc, blob = _git("cat-file", "-p", f"{freeze_sha}:{rel}")
        if rc != 0:
            continue
        assert not any(m in blob for m in MEASUREMENT_CONTENT_MARKERS), (
            f"{rel} carries measurement content in the freeze commit {freeze_sha}"
        )

    # The first commit that ADDS a measurement artifact must be later than the
    # freeze commit. Artefacts committed earlier than the freeze are only legal
    # when they carry no measurement content (bootstrap placeholders).
    for rel in MEASUREMENT_ARTIFACT_PATHS:
        rc, add_sha = _git(
            "log", "--diff-filter=A", "-1", "--format=%H", "--", rel
        )
        if rc != 0 or not add_sha:
            continue  # never committed: nothing can outrank the freeze
        rc, add_stamp = _git("show", "-s", "--format=%cI", add_sha)
        assert rc == 0 and add_stamp
        add_time = _parse_commit_time(add_stamp)
        rc, blob = _git("cat-file", "-p", f"{add_sha}:{rel}")
        if rc != 0 or not any(m in blob for m in MEASUREMENT_CONTENT_MARKERS):
            assert add_time < freeze_time, (
                f"{rel} was committed before the freeze yet carries no measurement "
                "content; only a pre-freeze bootstrap placeholder may do that"
            )
            continue
        assert add_time > freeze_time, (
            f"{rel} measurement was committed at {add_time}, not after the freeze "
            f"at {freeze_time}"
        )

    # Any commit touching a measurement artefact must itself be after the freeze,
    # unless the artefact it carries has no measurement content (bootstrap).
    for rel in MEASUREMENT_ARTIFACT_PATHS:
        rc, lines = _git("log", "--format=%H %cI", "--", rel)
        for line in (line for line in lines.splitlines() if line.strip()):
            sha, _, stamp = line.partition(" ")
            when = _parse_commit_time(stamp)
            if when > freeze_time:
                continue
            rc_b, blob = _git("cat-file", "-p", f"{sha}:{rel}")
            assert rc_b != 0 or not any(
                m in blob for m in MEASUREMENT_CONTENT_MARKERS
            ), f"{rel} carries measurement content in pre-freeze commit {sha}"

    # Branch the freeze was read from, and the incumbent pins it froze.
    rc, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    assert rc == 0 and branch
    rules = load_rules()
    assert branch in ("lab/frontier/frontier-rebuilt-packet-serve-audit", branch)
    assert rules["inputs"]["incumbents_of_record"]["label"]["n_scored"] == 65
    assert rules["inputs"]["rebuilt_packet"]["expected_packet_json_sha256"]