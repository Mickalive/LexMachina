"""Tests for ``evaluation/minimal_retrieval_ca_benchmark.py`` (FAST-MVP retrieval /
counter-authority falsification benchmark on the packet-of-record V3).

Dedicated test for the minimal retrieval/CA falsification benchmark, repaired by
run 39491098975 against audit gate CYCLE_39485386650_GATE.json required_fixes
F1-F7.  Every expectation below is either (a) the frozen hypothesis' own rule
committed before the claim-bearing run, or (b) the repair audit's own required
fix, stated as a machine-checkable assertion.

SCOPE / NON-WEAKENING CONTRACT
--------------------------------
* No frozen rule, rubric, threshold, predicate or success rule is re-derived or
  re-tuned here.  ``RULES_LABEL`` / ``RULES_GEOMETRY`` / ``VERDICT_CONTRACT``
  and the V3 bundle shas are only RE-HASHED against the pins frozen in
  ``evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json`` (corrected
  pins, repair F3) and the history-stable
  ``evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json``.
* The pytest-claim test asserts the NUMBER against a committed artifact (F1),
  never merely the presence of a boilerplate string.
* The V3 packet test is FAIL-CLOSED (F3): pins must be the real packet shas and,
  when the mount is present, every pinned file must exist and re-hash; there is
  no silent ``continue``.
* Mount-dependent tests skip with an explicit reason when the V3 packet mount is
  absent (never a pass); the offline tests still pin the committed evidence.
* Scratch-run obligation: the end-to-end leg passes ``--out-dir`` /
  ``--report-dir`` inside ``tmp_path`` so a suite run can never rewrite a
  committed claim-bearing record.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import minimal_retrieval_ca_benchmark as BM  # noqa: E402
from evaluation import mapping_free_recall_falsifier as ENGINE  # noqa: E402

# --- frozen pins ---------------------------------------------------------------
HYPOTHESIS = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"
COMPANION_FREEZE_RECORD = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"
FREEZE_RECORD_V1 = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"
POST_HOC_PINS_DISCLOSURE = (
    _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_POST_HOC_PINS_DISCLOSURE_39491098975.json")
ENGINE_INSTRUMENT = _REPO_ROOT / "evaluation/mapping_free_recall_falsifier.py"
WRAPPER_INSTRUMENT = _REPO_ROOT / "evaluation/minimal_retrieval_ca_benchmark.py"
STATE = Path(os.environ.get("LEXMACHINA_STATE_OVERRIDE")
             or (_REPO_ROOT / "state/evaluation.json"))
RESULTS_DIR = _REPO_ROOT / "results/evaluation/minimal_retrieval_ca_benchmark"
PYTEST_ARTIFACT = RESULTS_DIR / "pytest_39491098975.json"

#: history-stable FROZEN hypothesis digest (audit F2: restored bytes; every
#: historical pin names this digest; the b1015e7b post-edit digest 48c43d66... is
#: an at-run-time digest, disclosed, never a freeze proof).
FROZEN_HYPOTHESIS_SHA256 = (
    "d1135f9f919140a30dd31250cdb2e782fc3b32a74e39472a24d31560d7de009d")
#: history-stable companion freeze-record digest.
COMPANION_FREEZE_RECORD_SHA256 = (
    "431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5")
#: commit that first committed the hypothesis + companion freeze record.
FREEZE_COMMIT = "c9d97b50"
#: the rejected cycle's claim-bearing commit (historical record still pinned).
REJECTED_CLAIM_BEARING_COMMIT = "b1015e7b"
#: TRUE engine instrument digest (audit F3); unchanged since 7efbd60e.
ENGINE_INSTRUMENT_SHA256 = (
    "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302")
ENGINE_INSTRUMENT_FROZEN_SINCE = "7efbd60e"

PACKET_OF_RECORD = "39319405429"
#: TRUE V3 packet pins (audit F3); the b1015e7b hypothesis field wrongly held bar shas.
V3_PACKET_PINS = {
    "packet.json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "de-kapitalverletzung.bundle.json": "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "fr-bail-entretien.bundle.json": "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "it-responsabilita-medica.bundle.json": "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}
#: fields the engine entry point must have lifted into the wrapper record (F5).
PROVENANCE_FIELDS = (
    "rehash_before_execution", "rehash_after_execution", "input_drift",
    "input_drift_invalidates_run", "numeric_environment", "product_mount_head",
    "frozen_spec", "frozen_label_rubric", "analyst_mapping_not_consumed",
    "retraction_provenance",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(_REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _hypothesis() -> dict:
    return json.loads(HYPOTHESIS.read_text(encoding="utf-8"))


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def _current_record_path() -> Path:
    """This repair run's claim-bearing record (committed by run 39491098975)."""
    return RESULTS_DIR / "39491098975.json"


def _historical_record_path() -> Path:
    """The rejected cycle's committed record — preserved, never rewritten (F2)."""
    return RESULTS_DIR / "39485386650.json"


# ---------------------------------------------------------------- R1: hypothesis pin
def test_hypothesis_rehash_matches_frozen_digest():
    """R1/F2: the live hypothesis bytes are the history-stable FROZEN bytes."""
    actual = _sha256(HYPOTHESIS)
    assert actual == FROZEN_HYPOTHESIS_SHA256, (
        "frozen hypothesis file bytes changed — a frozen file edited after results "
        f"were seen invalidates the run (actual {actual})")


def test_companion_freeze_record_rehash_matches_frozen_digest():
    """R1/F2: the companion freeze record bytes are the history-stable FROZEN bytes."""
    actual = _sha256(COMPANION_FREEZE_RECORD)
    assert actual == COMPANION_FREEZE_RECORD_SHA256, (
        f"companion freeze record bytes changed (actual {actual})")


def test_state_pins_match_the_restored_frozen_bytes():
    """R1/F2: state pins the restored (history-stable) digests, not the post-edit ones."""
    blk = _state()["minimal_retrieval_ca_benchmark"]
    assert blk["hypothesis_sha256"] == FROZEN_HYPOTHESIS_SHA256
    assert blk["companion_freeze_record_sha256"] == COMPANION_FREEZE_RECORD_SHA256
    assert blk["post_edit_digests_preserved_in_disclosure"] is True


# ------------------------------------------------------------------- R2: freeze commit
def test_state_freeze_commit_is_where_the_hypothesis_landed():
    """R2: state names the commit that actually committed the hypothesis bytes."""
    blk = _state()["minimal_retrieval_ca_benchmark"]
    recorded = blk["freeze_commit"]
    assert recorded == FREEZE_COMMIT, f"state freeze_commit {recorded} != {FREEZE_COMMIT}"
    first = _git("log", "--diff-filter=A", "--format=%h",
                 "--", str(HYPOTHESIS.relative_to(_REPO_ROOT)))
    if first is None:
        pytest.skip("git history unavailable in this checkout; re-hash pins still enforced")
    assert any(h.startswith(FREEZE_COMMIT) for h in first.split()), (
        f"the hypothesis was first added by {first!r}, not a prefix of {FREEZE_COMMIT}")
    blob = _git("show", f"{FREEZE_COMMIT}:{HYPOTHESIS.relative_to(_REPO_ROOT)}")
    if blob is None:
        pytest.skip("git show unavailable in this checkout")
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    assert digest == FROZEN_HYPOTHESIS_SHA256, (
        "the hypothesis bytes at the freeze commit differ from the frozen digest")


def test_freeze_first_ordering_on_the_historical_claim_bearing_record():
    """Freeze-first discipline on the HISTORICAL rejected record (never rewritten)."""
    rec = _historical_record_path()
    assert rec.is_file(), f"historical record {rec} must be preserved, not deleted"
    added = _git("log", "--diff-filter=A", "--format=%h %ct",
                 "--", str(rec.relative_to(_REPO_ROOT)))
    if added is None or not added.strip():
        pytest.skip("git history for the historical record unavailable in this checkout")
    commit, ct = added.split()[0], int(added.split()[1])
    assert commit.startswith(REJECTED_CLAIM_BEARING_COMMIT), (
        f"historical record was added by {commit!r}, expected {REJECTED_CLAIM_BEARING_COMMIT}")
    frozen_ct = _git("log", "-1", "--format=%ct", FREEZE_COMMIT)
    if frozen_ct is None:
        pytest.skip("git unavailable in this checkout")
    assert int(frozen_ct) < ct, (
        "the claim-bearing record must never predate the frozen hypothesis "
        f"({FREEZE_COMMIT} at {frozen_ct} vs {commit} at {ct})")


def test_rejected_record_is_preserved_and_its_embedded_digests_are_disclosed_as_at_run_time():
    """F2: the rejected record stays byte-preserved; its embedded digests are the
    post-edit AT-RUN-TIME digests and are disclosed as such, not as freeze proofs."""
    rec = json.loads(_historical_record_path().read_text(encoding="utf-8"))
    disc = json.loads(POST_HOC_PINS_DISCLOSURE.read_text(encoding="utf-8"))
    assert rec["frozen_hypothesis"]["sha256"] == (
        disc["digest_pairs_side_by_side"]["hypothesis"]["post_edit_digest_at_run_time_of_39485386650"])
    assert rec["freeze_record"]["sha256"] == (
        disc["digest_pairs_side_by_side"]["freeze_record"]["post_edit_digest_at_run_time_of_39485386650"])
    assert "NOT a freeze proof" in (
        disc["digest_pairs_side_by_side"]["hypothesis"]["post_edit_digest_status"])


# ------------------------------------------------------- frozen bar and verdict pins
def test_frozen_bar_and_verdict_pins_rehash_unchanged():
    """RE-HASH ONLY: the disclosure's frozen-bar shas must equal the live bytes."""
    disc = json.loads(POST_HOC_PINS_DISCLOSURE.read_text(encoding="utf-8"))
    bars = disc["pins_re_homed_from_the_post_edit_hypothesis"]["frozen_bars_shas"]
    for name in ("RULES_LABEL.json", "RULES_GEOMETRY.json"):
        actual = _sha256(_REPO_ROOT / "evaluation/frozen_bars" / name)
        assert actual == bars[name], f"{name} re-hash {actual} != pin {bars[name]}"


def test_v3_packet_shas_are_the_real_packet_pins_and_fail_closed():
    """F3: packet pins must be the TRUE V3 shas (not bar shas) and the check is
    fail-closed: with the mount present every pinned file must exist AND match;
    there is no silent ``continue``."""
    fr = json.loads(FREEZE_RECORD_V1.read_text(encoding="utf-8"))
    pins = {k: v for k, v in fr["v3_packet_shas"].items() if not k.startswith("_")}
    assert pins == V3_PACKET_PINS, (
        f"FREEZE_RECORD_V1 v3_packet_shas must equal the true V3 pins; got {pins}")
    # the false bar-sha pins must not reappear anywhere in the v3 pins
    for name, digest in pins.items():
        assert not name.endswith("RULES_LABEL.json") and not name.endswith("RULES_GEOMETRY.json"), (
            f"v3_packet_shas must not hold frozen-bar files ({name})")

    mount = ENGINE.resolve_mount(os.environ.get("LEXMACHINA_PRODUCT_MOUNT"))
    if mount is None:
        pytest.skip("V3 product mount absent; pin-value assertions above still enforced "
                    "(skip is NEVER a pass)")
    base = mount / "results" / "product" / "gate_packet" / PACKET_OF_RECORD
    assert base.is_dir(), f"mount present but packet dir missing: {base}"

    def _target_for(pin_key: str) -> Path:
        if pin_key == "packet.json":
            return base / "packet.json"
        return base / "questions" / pin_key

    for rel, pinned in pins.items():
        target = _target_for(rel)
        assert target.is_file(), (
            f"fail-closed: pinned file {rel} does not exist under the mount at {base}")
        actual = _sha256(target)
        assert actual == pinned, f"{rel} re-hash {actual} != frozen pin {pinned}"


# ------------------------------------------------------- committed claim-bearing record
def test_committed_record_conforms_to_the_wrapper_contract():
    """The repair run's committed record must satisfy the wrapper contract (F5):
    wrapper schema, engine invoked, provenance layer present, measured payloads on
    failed gates."""
    rec_path = _current_record_path()
    assert rec_path.is_file(), (
        f"missing committed record {rec_path}; the repair run must commit its own "
        "claim-bearing record")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["schema"] == BM.WRAPPER_SCHEMA
    assert rec["verdict"] in ("PASS_NO_FALSIFICATION", "PRODUCT_FALSIFIED",
                              "NOT_MEASURED_VACUOUS")
    assert rec["exit_code"] in (0, 1, 2)
    # F5: the accepted engine entry point must have been invoked and its
    # provenance layer must be present with real payloads.
    assert rec.get("engine_invoked_run") is True
    for field in PROVENANCE_FIELDS:
        assert field in rec, f"provenance field {field} missing from the committed record"
    assert rec.get("numeric_environment"), "numeric_environment must be non-empty (requirement 30)"
    assert rec.get("product_mount_head"), "product_mount_head must be recorded"
    rb = rec["rehash_before_execution"]
    assert rb.get("repo") and rb.get("mount"), "rehash_before_execution must carry repo+mount maps"
    assert rec["analyst_mapping_not_consumed"]["read_into_any_gate"] is False
    # measured payloads restored on failed gates
    for g in rec.get("failed_gates") or []:
        assert "measured" in g and "detail" in g, (
            f"failed gate {g.get('gate')} lost its measured payload (F5)")
    assert isinstance(rec.get("input_drift"), list)


def test_engine_instrument_pin_is_the_true_digest():
    """F3: the instrument pin must be the TRUE engine digest, not the false
    fcafd2f2... wrapper digest enshrined at b1015e7b."""
    fr = json.loads(FREEZE_RECORD_V1.read_text(encoding="utf-8"))
    assert fr["engine_instrument"]["instrument_sha256"] == ENGINE_INSTRUMENT_SHA256
    assert fr["engine_instrument"]["unchanged_since_commit"] == ENGINE_INSTRUMENT_FROZEN_SINCE
    assert _sha256(ENGINE_INSTRUMENT) == ENGINE_INSTRUMENT_SHA256, (
        "mapping_free_recall_falsifier.py changed; the engine is frozen")
    blob = _git("show", f"{ENGINE_INSTRUMENT_FROZEN_SINCE}:evaluation/mapping_free_recall_falsifier.py")
    if blob is None:
        pytest.skip("git unavailable in this checkout")
    assert hashlib.sha256(blob.encode("utf-8")).hexdigest() == ENGINE_INSTRUMENT_SHA256, (
        "the engine bytes at the frozen-since commit no longer match the pin")


def test_freeze_record_v1_hypothesis_pin_targets_the_right_file():
    """F3: FREEZE_RECORD_V1's hypothesis pin must be the MAPPING hypothesis digest,
    not the MINIMAL_CA hypothesis digest f0c7711c..."""
    fr = json.loads(FREEZE_RECORD_V1.read_text(encoding="utf-8"))
    assert fr["hypothesis"]["hypothesis_sha256_at_freeze"] == FROZEN_HYPOTHESIS_SHA256
    assert fr["hypothesis"]["hypothesis_ref"].endswith("MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json")
    assert fr["hypothesis"]["false_pin_preserved_verbatim"].startswith("f0c7711c")
    # the false pin must actually be the digest of the OTHER file, as disclosed
    other = _sha256(_REPO_ROOT / "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
    assert other == fr["hypothesis"]["false_pin_preserved_verbatim"]


def test_freeze_record_v1_mount_digests_are_real_not_placeholder():
    """F3: the mount digests must be real packet pins, never the {'mount':
    'placeholder'} literal."""
    fr = json.loads(FREEZE_RECORD_V1.read_text(encoding="utf-8"))
    md = fr["mount_input_digests_before_execution"]
    assert md.get("mount") == "/tmp/lex_accepted/product"
    # no digest VALUE may be the literal placeholder (the _provenance prose may
    # name the historical defect; values may not carry it)
    digest_values = {k: v for k, v in md.items() if k != "_provenance"}
    for k, v in digest_values.items():
        assert v != "placeholder", f"mount digest {k} is still the literal placeholder"
    assert md["results/product/gate_packet/39319405429/packet.json"] == V3_PACKET_PINS["packet.json"]


def test_wrapper_instrument_pin_matches_state():
    """The wrapper's commit-time digest is state-pinned and is NEVER called a
    freeze proof."""
    blk = _state()["minimal_retrieval_ca_benchmark"]
    actual = _sha256(WRAPPER_INSTRUMENT)
    assert blk["instrument_sha256_at_repair"] == actual, (
        "state wrapper-instrument pin does not re-hash to the file")
    assert "NEVER a freeze proof" in blk["instrument_sha256_status"]


# ------------------------------------------------------- F4: synthetic fixture hygiene
def test_synthetic_fixture_is_marked_and_out_of_the_results_namespace():
    """F4: the fabricated 39396488491 record must live only as a marked fixture."""
    fixture = (_REPO_ROOT / "tests/evaluation/fixtures/minimal_retrieval_ca_benchmark/"
               "SYNTHETIC_PLACEHOLDER_RECORD_39396488491.json")
    assert fixture.is_file(), "the fabricated record must be re-homed, not deleted"
    marked = json.loads(fixture.read_text(encoding="utf-8"))
    assert marked["_synthetic_fixture"] is True
    assert "SYNTHETIC SCHEMA-FIXTURE" in marked["_fixture_warning"]
    assert marked["_genuine_artifact_for_run_39396488491"] == (
        "results/evaluation/retrieval_counter_authority_benchmark/39396488491.json")
    # it must NOT sit in the claim-bearing results namespace under the real run id
    assert not (RESULTS_DIR / "39396488491.json").exists(), (
        "the synthetic record must not occupy the claim-bearing results namespace")
    # the genuine artifact for that run id must still exist untouched
    genuine = (_REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/"
               "39396488491.json")
    assert genuine.is_file(), "the genuine 39396488491 artifact must never be removed"


# ------------------------------------------------------- F1: pytest claim in state
def test_state_pytest_claim_numbers_match_the_committed_artifact():
    """F1: the state's pytest claim must carry the NUMBER measured on the repaired
    tree, and that number must equal the committed pytest artifact."""
    blk = _state()["minimal_retrieval_ca_benchmark"]
    claim = blk["pytest"]
    assert "tests/evaluation/test_minimal_retrieval_ca_benchmark.py" in claim, (
        "state pytest claim does not cite the dedicated test file")
    # extract "<N> passed / <M> failed / <K> skipped" triples
    triples = re.findall(r"(\d+)\s*passed\s*/\s*(\d+)\s*failed\s*/\s*(\d+)\s*skipped", claim)
    assert triples, f"pytest claim carries no measurable counts: {claim!r}"
    assert PYTEST_ARTIFACT.is_file(), (
        "no committed pytest artifact; the claim must sit beside a committed artifact")
    art = json.loads(PYTEST_ARTIFACT.read_text(encoding="utf-8"))
    assert art["test_file"] == "tests/evaluation/test_minimal_retrieval_ca_benchmark.py"
    measured = (str(art["passed"]), str(art["failed"]), str(art["skipped"]))
    assert measured in triples, (
        f"state claim counts {triples} do not include the committed measurement {measured}")
    # the false pre-repair claim must be preserved verbatim beside its correction
    assert "PRE-REPAIR CLAIM WAS FALSE" in claim
    false_claim = blk.get("pytest_39485386650_false_claim_verbatim")
    assert false_claim and "11 passed / 0 failed / 0 skipped" in false_claim, (
        "the false pre-repair claim must be preserved verbatim, never silently deleted")


def test_state_evidence_refs_resolve_and_count_matches():
    """Provenance hygiene: every evidence_ref resolves and evidence_refs_n is the count."""
    st = _state()
    refs = st["evidence_refs"]
    missing = [r for r in refs
               if not (_REPO_ROOT / r.split(" ")[0].rstrip(",").replace(",", "")).exists()]
    assert not missing, f"evidence_refs that do not resolve on disk: {missing}"
    assert st["evidence_refs_n"] == len(refs), (
        f"evidence_refs_n={st['evidence_refs_n']} but len(evidence_refs)={len(refs)}")


# ------------------------------------------------------- F6: state block consistency
def test_state_block_names_the_claim_bearing_run_and_no_fabricated_legs():
    """F6: claim_bearing_run is the rejected run; the fabricated legs are removed;
    the measurement is disclosed as field-identical to the earlier falsifier run."""
    blk = _state()["minimal_retrieval_ca_benchmark"]
    assert blk["claim_bearing_run"] == "39485386650"
    assert "legs" not in blk, "the fabricated legs block must be removed from state"
    assert "counter_authority_surface_falsifier/39462322100.json" in (
        blk["field_identical_measurement_disclosure"])
    assert blk["field_identical_measurement_disclosure"].startswith(
        "The 39485386650 measurement is field-identical")
    assert blk["repair_round"] == 1
    assert blk["repair_of_run"] == "39485386650"
    assert blk["github_run"] == 39491098975
    # top-level proposal advanced to the repair run
    st = _state()
    assert str(st["proposed_run_id"]) == "39491098975"
    assert st["github_run"] == 39491098975
    assert "39491098975" in st["cycle_status"]
    assert "39491098975" in st["summary"]["headline"]


# ------------------------------------------------------- F7: serialization hygiene
def test_state_serialization_is_surgical_not_reserialized():
    """F7: pre-existing keys must be byte-identical to the accepted base except the
    explicitly advanced fields; the diff must be surgical."""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "diff", "--stat", "5ac1ba5a", "--", "state/evaluation.json"],
        capture_output=True, text=True, timeout=60)
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip("cannot diff against accepted base 5ac1ba5a in this checkout")
    m = re.search(r"(\d+) insertion.*?(\d+) deletion", proc.stdout)
    if not m:
        pytest.skip(f"unparsable diff stat: {proc.stdout!r}")
    ins, dele = int(m.group(1)), int(m.group(2))
    # surgical: the block + advanced fields; nowhere near the 1966-line reserialization
    assert ins + dele < 220, (
        f"state/evaluation.json diff against 5ac1ba5a is {ins}+{dele} lines; expected a "
        "surgical edit (F7 forbids whole-file re-serialization)")


# ------------------------------------------------------- end-to-end (mount)
def test_end_to_end_on_v3_mount_if_present(tmp_path):
    """Live reproduction of the wrapper contract on the V3 packet mount.

    Redirects both output directories into tmp_path (scratch-run obligation).
    The exit code and verdict vocabulary are the frozen hypothesis' own
    expectations; nothing here can rewrite committed evidence.
    """
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
         "--run-id", "pytest_minimal_ca",
         "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode in (0, 1, 2), (
        f"expected exit 0/1/2; got {proc.returncode}; stderr tail: {proc.stderr[-600:]}")
    out = json.loads(proc.stdout)
    assert out["verdict"] in ("PASS_NO_FALSIFICATION", "PRODUCT_FALSIFIED",
                              "NOT_MEASURED_VACUOUS"), (
        f"unexpected verdict: {out.get('verdict')}")
    assert out["exit_code"] in (0, 1, 2)
    assert out.get("engine_invoked_run") is True, "the accepted engine entry point must be invoked"
    rec_file = out_dir / "pytest_minimal_ca.json"
    assert rec_file.is_file()
    rec = json.loads(rec_file.read_text(encoding="utf-8"))
    for field in PROVENANCE_FIELDS:
        assert field in rec, f"live record lost provenance field {field}"
    assert (report_dir / "RETRIEVAL_CA_BENCHMARK_pytest_minimal_ca.md").is_file()
    # engine sub-record persisted beside the wrapper record
    assert (out_dir / "pytest_minimal_ca_engine_mapping_free_recall_falsifier.json").is_file()


def test_output_defaults_point_at_the_committed_tree():
    """Make the scratch-run obligation explicit: defaults ARE the committed tree."""
    assert BM.DEFAULT_OUT_DIR.name == "minimal_retrieval_ca_benchmark"
    assert BM.DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert BM.DEFAULT_REPORT_DIR.name == "evaluation"
    assert BM.DEFAULT_OUT_DIR.is_dir() and BM.DEFAULT_REPORT_DIR.is_dir()
