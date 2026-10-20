"""Dedicated test for ``evaluation/minimal_ca_benchmark.py`` (FAST-MVP retrieval /
counter-authority falsification benchmark on the packet-of-record V3).

WHY THIS FILE EXISTS
--------------------
Independent audit ``CYCLE_39402114706`` (gate=REVISE, repair round 0) listed three
required fixes against ``state/evaluation.json``.  The third one was a pytest claim
that cited ``tests/evaluation/test_benchmark_retrieval_counter_authority.py`` while
that file tests a *different* instrument and **no dedicated test for
minimal_ca_benchmark.py existed**.  Repair round 1 of cycle 39402114706 adds this
file so the corrected claim is executable instead of merely reworded.

SCOPE / NON-WEAKENING CONTRACT
-------------------------------
* No frozen rule, rubric, threshold, incumbent, predicate or success rule is
  re-derived or re-tuned here.  ``RULES_LABEL`` / ``RULES_GEOMETRY`` /
  ``VERDICT_CONTRACT`` and the V3 bundle shas are only RE-HASHED against the pins
  already frozen in ``evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json``.
* Every expectation asserted below is the frozen hypothesis's own
  ``expected_leg_outcomes`` / ``combined_verdict`` rule, committed at freeze
  commit ``6892f9f0`` BEFORE the claim-bearing run 39396488491.  This file adds no
  new threshold and no new claim ceiling.
* Scratch-run obligation (accepted convention, audit CYCLE_39164900837 F9): the
  end-to-end leg passes ``--out-dir`` / ``--report-dir`` inside ``tmp_path`` so a
  suite run can never rewrite a committed claim-bearing record.
* Mount-dependent tests skip with an explicit reason when the V3 packet mount is
  absent (the audit environment did not have it), so the suite stays runnable in a
  bare checkout; the offline tests still pin the committed evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.minimal_ca_benchmark import V3_PACKET_DIR  # noqa: E402

# --- frozen pins (re-hash targets; values come from the frozen hypothesis) -------
HYPOTHESIS = _REPO_ROOT / "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json"
FREEZE_RECORD = _REPO_ROOT / "evaluation/MINIMAL_CA_BENCHMARK_FREEZE_RECORD_V1.json"
INSTRUMENT = _REPO_ROOT / "evaluation/minimal_ca_benchmark.py"
#: Overridable so the verifier can re-inject the PRE-REPAIR state and prove these
#: guards actually fail on the defect they were written for (negative control).
STATE = Path(os.environ.get("LEXMACHINA_STATE_OVERRIDE")
             or (_REPO_ROOT / "state/evaluation.json"))

#: sha256 of the frozen hypothesis file — the R1 target of audit CYCLE_39402114706.
FROZEN_HYPOTHESIS_SHA256 = (
    "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072")
#: commit that first committed the hypothesis + freeze record (the R2 target).
FREEZE_COMMIT = "6892f9f0"
#: commit that first committed the claim-bearing benchmark record.
#: Historical accepted-chain record 39396488491 was first committed at d4c88b3a on a
#: rejected branch; this cycle's claim-bearing record (39422312905) is first committed
#: on lab/evaluation under the V61 freeze commit.  Both orderings are checked below.
CLAIM_BEARING_COMMIT = "d4c88b3a"
#: this cycle's freeze-first commit (V61 disposition hypothesis)
V61_FREEZE_COMMIT = "07cf996ff"
CURRENT_CLAIM_BEARING_RECORD = (
    _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/39422312905.json")
#: instrument bytes named by the frozen hypothesis/freeze record (pre-fix, 7efbd60e).
PRE_FIX_INSTRUMENT_SHA256 = (
    "2d40d2e795d9396542bbbc7a811e6cf26da91f3b19220e70199aad8f5f02c84c")
#: instrument bytes that actually executed the claim-bearing run (6892f9f0 → HEAD).
EXECUTED_INSTRUMENT_SHA256 = (
    "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b")

COMBINED_RECORD = (
    _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/39396488491.json")
#: Prefer the current cycle's claim-bearing record when present (freeze-first under
#: the V61 disposition freeze); fall back to the historical 39396488491 record.
def _combined_record() -> Path:
    if CURRENT_CLAIM_BEARING_RECORD.is_file():
        return CURRENT_CLAIM_BEARING_RECORD
    return COMBINED_RECORD


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str | None:
    """Run git in the repo; return stdout stripped, or None if git is unusable."""
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


# ---------------------------------------------------------------- R1: hypothesis pin
def test_hypothesis_rehash_matches_state_pin():
    """R1 (audit CYCLE_39402114706): state must pin the hypothesis' real digest."""
    actual = _sha256(HYPOTHESIS)
    assert actual == FROZEN_HYPOTHESIS_SHA256, (
        "frozen hypothesis file bytes changed — a frozen file edited after results "
        f"were seen invalidates the run (actual {actual})")
    recorded = _state()["minimal_ca_benchmark"]["hypothesis_sha256"]
    assert recorded == actual, (
        "state/evaluation.json minimal_ca_benchmark.hypothesis_sha256 does not "
        f"re-hash to the file (recorded {recorded}, actual {actual})")
    # the freeze record pins the same hypothesis digest
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    assert fr["hypothesis_ref"] == HYPOTHESIS.name


# ------------------------------------------------------------------- R2: freeze commit
def test_state_freeze_commit_is_where_the_hypothesis_landed():
    """R2: state must name the commit that actually committed the hypothesis."""
    recorded = _state()["minimal_ca_benchmark"]["freeze_commit"]
    assert recorded == FREEZE_COMMIT, (
        f"state freeze_commit {recorded} != {FREEZE_COMMIT}")
    first = _git("log", "--diff-filter=A", "--format=%h",
                 "--", str(HYPOTHESIS.relative_to(_REPO_ROOT)))
    if first is None:
        import pytest
        pytest.skip("git unavailable in this checkout; re-hash pins still enforced")
    # Accept an abbreviated hash that PREFIX-matches the pinned freeze commit
    # (git may abbreviate to 9+ chars: e.g. 6892f9f06 for pin 6892f9f0).
    assert any(h.startswith(FREEZE_COMMIT) for h in first.split()), (
        f"the hypothesis was first added by {first!r}, not a prefix of {FREEZE_COMMIT}")
    blob = _git("show", f"{FREEZE_COMMIT}:{HYPOTHESIS.relative_to(_REPO_ROOT)}")
    if blob is None:
        import pytest
        pytest.skip("git show unavailable in this checkout")
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    assert digest == FROZEN_HYPOTHESIS_SHA256, (
        "the hypothesis bytes at the freeze commit differ from the frozen digest")


def test_freeze_first_ordering_hypothesis_before_claim_bearing_record():
    """Freeze-first discipline: freeze commit predates the claim-bearing commit."""
    rec = _combined_record()
    added = _git("log", "--diff-filter=A", "--format=%h %ct",
                 "--", str(rec.relative_to(_REPO_ROOT)))
    if added is None or not added.strip():
        import pytest
        pytest.skip(f"git history for {rec.name} unavailable in this checkout")
    commit, ct = added.split()[0], int(added.split()[1])
    # Historical pin: the original claim-bearing commit (rejected chain) still
    # must postdate the original freeze commit when that history is present.
    if commit.startswith(CLAIM_BEARING_COMMIT):
        frozen_ct = _git("log", "-1", "--format=%ct", FREEZE_COMMIT)
        if frozen_ct is None:
            import pytest
            pytest.skip("git unavailable in this checkout")
        assert int(frozen_ct) < ct, (
            "the claim-bearing record must never predate the frozen hypothesis "
            f"({FREEZE_COMMIT} at {frozen_ct} vs {commit} at {ct})")
    else:
        # Current-cycle claim-bearing record: must postdate the V61 freeze commit.
        frozen_ct = _git("log", "-1", "--format=%ct", V61_FREEZE_COMMIT)
        if frozen_ct is None:
            # V61 freeze may be the HEAD itself; use its committer time via rev-parse
            import pytest
            pytest.skip("V61 freeze commit history unavailable in this checkout")
        assert int(frozen_ct) < ct, (
            "the current-cycle claim-bearing record must postdate the V61 freeze "
            f"({V61_FREEZE_COMMIT} at {frozen_ct} vs {commit} at {ct})")


# ------------------------------------------------------------------- frozen pins
def test_frozen_bar_and_verdict_pins_rehash_unchanged():
    """RE-HASH ONLY: RULES_* / VERDICT_CONTRACT must equal the frozen hypothesis pins."""
    hyp = _hypothesis()
    for name, pinned in hyp["frozen_bars_shas"].items():
        actual = _sha256(_REPO_ROOT / "evaluation/frozen_bars" / name)
        assert actual == pinned, f"{name} re-hash {actual} != frozen pin {pinned}"
    # re-hash proven in the freeze record too (same convention, never re-derived)
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    assert fr["frozen_bars_shas"] == hyp["frozen_bars_shas"]


def test_v3_bundle_shas_match_frozen_hypothesis():
    """The packet bytes the benchmark scored must be the frozen packet bytes."""
    if not V3_PACKET_DIR.exists():
        import pytest
        pytest.skip(f"V3 packet mount absent ({V3_PACKET_DIR}); offline pins still apply")
    hyp = _hypothesis()
    for fname, pinned in hyp["v3_packet_shas"].items():
        actual = _sha256(V3_PACKET_DIR / fname)
        assert actual == pinned, f"{fname} re-hash {actual} != frozen pin {pinned}"


# ------------------------------------------------------- committed claim-bearing record
def test_committed_record_conforms_to_frozen_expectations():
    """The committed record must satisfy the hypothesis' frozen verdict rule.

    Fully offline: this pins the evidence an auditor reads without the mount.
    """
    rec_path = _combined_record()
    assert rec_path.is_file(), f"missing committed record {rec_path}"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    hyp = _hypothesis()
    assert rec["schema"] == "lex-evaluation-minimal-ca-benchmark/1"
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is True
    assert rec["reuses_entry_point"] == "evaluation.frozen_bars.run_bar_gates"

    legs = {lg["leg"]: lg for lg in rec["legs"]}
    for leg_id, exp in hyp["expected_leg_outcomes"].items():
        assert leg_id in legs, f"leg {leg_id} missing from the committed record"
        got = legs[leg_id]
        assert got["exit_code"] == exp["expected_exit_code"], (
            f"{leg_id}: exit {got['exit_code']} != frozen expectation "
            f"{exp['expected_exit_code']}")
        assert got["verdict"] == exp["expected_verdict"], (
            f"{leg_id}: verdict {got['verdict']} != {exp['expected_verdict']}")
        assert got["exit_code_matches_expectation"] is True

    # both falsification legs fired → the frozen combined rule yields exit 0
    assert legs["geometry_falsification_hostile"]["exit_code"] == 1
    assert legs["label_falsification_blanked_evidence"]["exit_code"] == 1
    assert legs["served_baseline_provenance"]["exit_code"] == 2

    # packet identity: the scored bundles are the frozen V3 bundles
    # (hypothesis keys are filenames, the record keys are qids — same digests)
    expected_bundles = {
        qid: hyp["v3_packet_shas"][f"{qid}.bundle.json"]
        for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
    }
    assert rec["v3_bundle_sha256"] == expected_bundles

    # full leg records carry the frozen rubric pins (re-hash, never re-derived)
    out_dir = rec_path.parent
    run_id = rec.get("run_id", rec_path.stem)
    for suffix, exp_verdict in (("_leg2_hostile_geometry", "FAIL_REGRESSION"),
                                ("_leg3_blanked_evidence", "FAIL_REGRESSION")):
        leg = json.loads((out_dir / f"{run_id}{suffix}.json").read_text(encoding="utf-8"))
        assert leg["verdict"] == exp_verdict
        assert leg["rules_label_sha256"] == hyp["frozen_bars_shas"]["RULES_LABEL.json"]
        assert leg["rules_geometry_sha256"] == hyp["frozen_bars_shas"]["RULES_GEOMETRY.json"]
        assert leg["negative_controls_all_proven"] is True


def test_instrument_sha_disclosure_is_complete_and_unchanged_since_freeze():
    """Pin the instrument-provenance disclosure instead of hiding the pre-fix digest.

    The frozen hypothesis/freeze record name the PRE-FIX instrument (commit
    7efbd60e); the repaired instrument that executed run 39396488491 is byte-identical
    from freeze commit 6892f9f0 to HEAD.  Both facts are asserted here so neither can
    drift silently and neither has to be re-derived in prose.
    """
    hyp = _hypothesis()
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    assert hyp["instrument_sha256"] == PRE_FIX_INSTRUMENT_SHA256
    assert fr["instrument_sha256"] == PRE_FIX_INSTRUMENT_SHA256
    assert "pre-fix" in fr["frozen_at_commit"], (
        "the freeze record must keep disclosing that its instrument digest names the "
        "pre-fix bytes at 7efbd60e")

    assert _sha256(INSTRUMENT) == EXECUTED_INSTRUMENT_SHA256, (
        "minimal_ca_benchmark.py changed after the claim-bearing run")

    at_freeze = _git("show", f"{FREEZE_COMMIT}:evaluation/minimal_ca_benchmark.py")
    if at_freeze is None:
        import pytest
        pytest.skip("git unavailable in this checkout")
    assert hashlib.sha256(at_freeze.encode("utf-8")).hexdigest() == \
        EXECUTED_INSTRUMENT_SHA256, (
            "the executed instrument bytes are no longer the bytes committed at freeze "
            "commit 6892f9f0")
    pre_fix = _git("show", "7efbd60e:evaluation/minimal_ca_benchmark.py")
    if pre_fix is None:
        import pytest
        pytest.skip("git unavailable in this checkout")
    assert hashlib.sha256(pre_fix.encode("utf-8")).hexdigest() == \
        PRE_FIX_INSTRUMENT_SHA256, (
            "the pre-fix instrument bytes no longer hash to the frozen hypothesis pin")


# ---------------------------------------------------------------------- R3: test claim
def test_state_pytest_claim_names_this_dedicated_test():
    """R3: the state's pytest claim must describe THIS file and its own measurement.

    Guards against re-introducing the rejected claim (a different instrument's test
    file presented as coverage for minimal_ca_benchmark.py).
    """
    claim = _state()["minimal_ca_benchmark"]["pytest"]
    assert "tests/evaluation/test_minimal_ca_benchmark.py" in claim, (
        "state pytest claim does not cite the dedicated test file")
    assert "PRE-REPAIR CLAIM WAS FALSE" in claim, (
        "the false pre-repair claim must be corrected beside its replacement, never "
        "silently deleted")
    # the misleading citation may only appear as an explicit historical disclosure
    if "test_benchmark_retrieval_counter_authority.py" in claim:
        assert "DIFFERENT instrument" in claim


def test_state_evidence_refs_resolve_and_count_matches():
    """Provenance hygiene: every evidence_ref resolves and evidence_refs_n is the count."""
    st = _state()
    refs = st["evidence_refs"]
    missing = [r for r in refs if not (_REPO_ROOT / r.split(" ")[0].rstrip(",")).exists()]
    assert not missing, f"evidence_refs that do not resolve on disk: {missing}"
    assert st["evidence_refs_n"] == len(refs), (
        f"evidence_refs_n={st['evidence_refs_n']} but len(evidence_refs)={len(refs)}")


# ------------------------------------------------------------------ end-to-end (mount)
def test_end_to_end_on_v3_mount_if_present(tmp_path):
    """Live reproduction of the frozen expectations on the V3 packet mount.

    Redirects both output directories into tmp_path (scratch-run obligation).  The
    exit code and verdict vocabulary are the frozen hypothesis' own expectations;
    nothing here can rewrite committed evidence.
    """
    if not V3_PACKET_DIR.exists():
        import pytest
        pytest.skip(f"V3 packet mount absent ({V3_PACKET_DIR}); "
                    "offline record tests still pin the frozen verdict")
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.minimal_ca_benchmark",
         "--run-id", "pytest_minimal_ca",
         "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, (
        f"expected exit 0 (BENCHMARK_VALID_NO_FALSIFICATION); got {proc.returncode}; "
        f"stderr tail: {proc.stderr[-600:]}")
    out = json.loads(proc.stdout)
    assert out["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert out["falsification_proven"] is True
    expected = {leg: (exp["expected_exit_code"], exp["expected_verdict"])
                for leg, exp in _hypothesis()["expected_leg_outcomes"].items()}
    for leg in out["legs"]:
        exp_rc, exp_verdict = expected[leg["leg"]]
        assert leg["exit_code"] == exp_rc, f"{leg['leg']}: {leg['exit_code']} != {exp_rc}"
        assert leg["verdict"] == exp_verdict
    assert (out_dir / "pytest_minimal_ca.json").is_file()
    assert (report_dir / "RETRIEVAL_CA_BENCHMARK_pytest_minimal_ca.md").is_file()


def test_output_defaults_point_at_the_committed_tree():
    """Make the scratch-run obligation explicit: defaults ARE the committed tree."""
    from evaluation.minimal_ca_benchmark import DEFAULT_OUT_DIR, DEFAULT_REPORT_DIR
    assert DEFAULT_OUT_DIR.name == "retrieval_counter_authority_benchmark"
    assert DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert DEFAULT_REPORT_DIR.name == "evaluation"
    assert DEFAULT_OUT_DIR.is_dir() and DEFAULT_REPORT_DIR.is_dir()
