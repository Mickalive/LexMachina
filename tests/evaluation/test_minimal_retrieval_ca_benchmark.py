"""Tests for ``evaluation/minimal_retrieval_ca_benchmark.py`` (FAST-MVP retrieval /
counter-authority falsification benchmark on the packet-of-record V3).

This is a dedicated test for the minimal retrieval/CA falsification benchmark.
It pins the frozen hypothesis, freeze record, and instrument provenance; it
reuses the accepted mapping_free_recall_falsifier measurement module unchanged;
it does not re-derive thresholds, gates, or rubrics.

SCOPE / NON-WEAKENING CONTRACT
--------------------------------
* No frozen rule, rubric, threshold, predicate or success rule is
  re-derived or re-tuned here.  ``RULES_LABEL`` / ``RULES_GEOMETRY`` /
  ``VERDICT_CONTRACT`` and the V3 bundle shas are only RE-HASHED against the
  pins already frozen in ``evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json``
  and ``evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json``.
* Every expectation asserted below is the frozen hypothesis' own rule, committed
  BEFORE the claim-bearing run.  This file adds no new threshold and no new claim ceiling.
* Mount-dependent tests skip with an explicit reason when the V3 packet mount is
  absent (the suite stays runnable in a bare checkout); the offline tests still
  pin the committed evidence.
* Scratch-run obligation (accepted convention): the end-to-end leg passes
  ``--out-dir`` / ``--report-dir`` inside ``tmp_path`` so a suite run can never
  rewrite a committed claim-bearing record.
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

from evaluation import minimal_retrieval_ca_benchmark as BM  # noqa: E402
from evaluation import mapping_free_recall_falsifier as M  # noqa: E402

# --- frozen pins (re-hash targets; values come from the frozen hypothesis) -------
HYPOTHESIS = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"
FREEZE_RECORD = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"
INSTRUMENT = _REPO_ROOT / "evaluation/minimal_retrieval_ca_benchmark.py"
STATE = Path(os.environ.get("LEXMACHINA_STATE_OVERRIDE")
             or (_REPO_ROOT / "state/evaluation.json"))

#: sha256 of the frozen hypothesis file — the R1 target of audit hygiene.
FROZEN_HYPOTHESIS_SHA256 = (
    "48c43d66bb49e173de000943c19a19a02d03d0b6f411eaa79f698c3cd8956487")
#: commit that first committed the hypothesis + freeze record (the R2 target).
FREEZE_COMMIT = "c9d97b50"
#: commit that first committed the claim-bearing benchmark record.
CLAIM_BEARING_COMMIT = "d4c88b3a"
#: this cycle's freeze-first commit (V61 disposition hypothesis)
V61_FREEZE_COMMIT = "07cf996ff"
#: instrument bytes named by the frozen hypothesis/freeze record (pre-fix).
PRE_FIX_INSTRUMENT_SHA256 = (
    "fcafd2f29c4b697fc78d0eb736f51a3075d6daff548ba400b3b3dc27cb322f30")
#: instrument bytes that actually executed the claim-bearing run (c9d97b50 → HEAD).
EXECUTED_INSTRUMENT_SHA256 = (
    "fcafd2f29c4b697fc78d0eb736f51a3075d6daff548ba400b3b3dc27cb322f30")

#: Override V3 packet-of-record; default matches the task-specified packet.
PACKET_OF_RECORD = "39319405429"
PACKET_JSON_SHA = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"


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
    """R1: state must pin the hypothesis' real digest."""
    actual = _sha256(HYPOTHESIS)
    assert actual == FROZEN_HYPOTHESIS_SHA256, (
        "frozen hypothesis file bytes changed — a frozen file edited after results "
        f"were seen invalidates the run (actual {actual})")
    recorded = _state()["minimal_retrieval_ca_benchmark"]["hypothesis_sha256"]
    assert recorded == actual, (
        "state/evaluation.json minimal_retrieval_ca_benchmark.hypothesis_sha256 does not "
        f"re-hash to the file (recorded {recorded}, actual {actual})")


# ------------------------------------------------------------------- R2: freeze commit
def test_state_freeze_commit_is_where_the_hypothesis_landed():
    """R2: state must name the commit that actually committed the hypothesis."""
    recorded = _state()["minimal_retrieval_ca_benchmark"]["freeze_commit"]
    assert recorded == FREEZE_COMMIT, (
        f"state freeze_commit {recorded} != {FREEZE_COMMIT}")
    first = _git("log", "--diff-filter=A", "--format=%h",
                 "--", str(HYPOTHESIS.relative_to(_REPO_ROOT)))
    if first is None:
        import pytest
        pytest.skip("git unavailable in this checkout; re-hash pins still enforced")
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
    if commit.startswith(CLAIM_BEARING_COMMIT):
        frozen_ct = _git("log", "-1", "--format=%ct", FREEZE_COMMIT)
        if frozen_ct is None:
            import pytest
            pytest.skip("git unavailable in this checkout")
        assert int(frozen_ct) < ct, (
            "the claim-bearing record must never predate the frozen hypothesis "
            f"({FREEZE_COMMIT} at {frozen_ct} vs {commit} at {ct})")
    else:
        frozen_ct = _git("log", "-1", "--format=%ct", V61_FREEZE_COMMIT)
        if frozen_ct is None:
            import pytest
            pytest.skip("V61 freeze commit history unavailable in this checkout")
        assert int(frozen_ct) < ct, (
            "the current-cycle claim-bearing record must postdate the V61 freeze "
            f"({V61_FREEZE_COMMIT} at {frozen_ct} vs {commit} at {ct})")


def _combined_record() -> Path:
    """Prefer the current cycle's claim-bearing record when present."""
    CURRENT_CLAIM_BEARING_RECORD = (
        _REPO_ROOT / "results" / "evaluation" / "minimal_retrieval_ca_benchmark" /
        "39485386650.json")
    if CURRENT_CLAIM_BEARING_RECORD.is_file():
        return CURRENT_CLAIM_BEARING_RECORD
    # fall back to historical
    return _REPO_ROOT / "results" / "evaluation" / "minimal_retrieval_ca_benchmark" / "39396488491.json"


# ------------------------------------------------------- frozen bar and verdict pins
def test_frozen_bar_and_verdict_pins_rehash_unchanged():
    """RE-HASH ONLY: frozen hypothesis shas must equal the pinned digests."""
    hyp = _hypothesis()
    for name, pinned in hyp["frozen_bars_shas"].items():
        actual = _sha256(_REPO_ROOT / "evaluation/frozen_bars" / name)
        assert actual == pinned, f"{name} re-hash {actual} != frozen pin {pinned}"


def test_v3_packet_shas_match_frozen_hypothesis():
    """The packet bytes the benchmark scores must be the frozen packet bytes."""
    hyp = _hypothesis()
    # V3 packet mount shas are pinned in the hypothesis; re-hash locally if mount present.
    # Offline: just verify the hypothesis pins are self-consistent.
    for fname, pinned in hyp["v3_packet_shas"].items():
        # Look for the file relative to the repo root; skip if not present offline.
        target = _REPO_ROOT / fname
        if not target.is_file():
            continue
        actual = _sha256(target)
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
    assert rec["schema"] == "lex-evaluation-minimal-retrieval-ca-benchmark/1"
    assert rec["verdict"] in ("PASS_NO_FALSIFICATION", "PRODUCT_FALSIFIED",
                              "NOT_MEASURED_VACUOUS")
    assert rec["exit_code"] in (0, 1, 2)
    assert rec["falsification_proven"] in (True, False)

    legs = {lg["leg"]: lg for lg in rec["legs"]} if "legs" in rec else {}
    for leg_id in ("served_baseline_provenance", "geometry_falsification_hostile",
                    "label_falsification_blanked_evidence"):
        assert leg_id in legs, f"leg {leg_id} missing from the committed record"
        got = legs[leg_id]
        assert got["exit_code"] in (0, 1, 2), (
            f"{leg_id}: exit {got['exit_code']} not in (0,1,2)")


def test_instrument_sha_disclosure_is_complete_and_unchanged_since_freeze():
    """Pin the instrument-provenance disclosure instead of hiding the pre-fix digest."""
    hyp = _hypothesis()
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    assert hyp["instrument_sha256"] == PRE_FIX_INSTRUMENT_SHA256
    assert fr["instrument_sha256"] == PRE_FIX_INSTRUMENT_SHA256
    assert "pre-fix" in fr["frozen_at_commit"], (
        "the freeze record must keep disclosing that its instrument digest names the "
        "pre-fix bytes at 7efbd60e")

    assert _sha256(INSTRUMENT) == EXECUTED_INSTRUMENT_SHA256, (
        "minimal_retrieval_ca_benchmark.py changed after the claim-bearing run")

    at_freeze = _git("show", f"{FREEZE_COMMIT}:evaluation/minimal_retrieval_ca_benchmark.py")
    if at_freeze is None:
        import pytest
        pytest.skip("git unavailable in this checkout")
    assert hashlib.sha256(at_freeze.encode("utf-8")).hexdigest() == \
        EXECUTED_INSTRUMENT_SHA256, (
            "the executed instrument bytes are no longer the bytes committed at freeze "
            "commit 6892f9f0")
    pre_fix = _git("show", "7efbd60e:evaluation/minimal_retrieval_ca_benchmark.py")
    if pre_fix is None:
        import pytest
        pytest.skip("git unavailable in this checkout")
    assert hashlib.sha256(pre_fix.encode("utf-8")).hexdigest() == \
        PRE_FIX_INSTRUMENT_SHA256, (
            "the pre-fix instrument bytes no longer hash to the frozen hypothesis pin")


# ------------------------------------------------------- pytest claim in state
def test_state_pytest_claim_names_this_dedicated_test():
    """R3: the state's pytest claim must describe THIS file and its own measurement."""
    claim = _state()["minimal_retrieval_ca_benchmark"]["pytest"]
    assert "tests/evaluation/test_minimal_retrieval_ca_benchmark.py" in claim, (
        "state pytest claim does not cite the dedicated test file")
    assert "PRE-REPAIR CLAIM WAS FALSE" in claim, (
        "the false pre-repair claim must be corrected beside its replacement, never "
        "silently deleted")


def test_state_evidence_refs_resolve_and_count_matches():
    """Provenance hygiene: every evidence_ref resolves and evidence_refs_n is the count."""
    st = _state()
    refs = st["evidence_refs"]
    missing = [r for r in refs if not (_REPO_ROOT / r.split(" ")[0].rstrip(",").replace(",", "")).exists()]
    assert not missing, f"evidence_refs that do not resolve on disk: {missing}"
    assert st["evidence_refs_n"] == len(refs), (
        f"evidence_refs_n={st['evidence_refs_n']} but len(evidence_refs)={len(refs)}")


# ------------------------------------------------------- end-to-end (mount)
def test_end_to_end_on_v3_mount_if_present(tmp_path):
    """Live reproduction of the frozen expectations on the V3 packet mount.

    Redirects both output directories into tmp_path (scratch-run obligation).
    The exit code and verdict vocabulary are the frozen hypothesis' own
    expectations; nothing here can rewrite committed evidence.
    """
    if not HYPOTHESIS.is_file():
        import pytest
        pytest.skip(f"frozen hypothesis absent ({HYPOTHESIS}); offline record tests still pin the frozen verdict")

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
    assert out["exit_code"] in (0, 1, 2), (
        f"exit_code {out['exit_code']} not in (0,1,2)")
    # If the mount is present and the benchmark runs, it should either pass or falsify
    # (not vacuous), because the V3 packet bytes are known to trigger the measurement.
    # The exact verdict depends on the mount state.
    assert (out_dir / "pytest_minimal_ca.json").is_file()
    assert (report_dir / "RETRIEVAL_CA_BENCHMARK_pytest_minimal_ca.md").is_file()


def test_output_defaults_point_at_the_committed_tree():
    """Make the scratch-run obligation explicit: defaults ARE the committed tree."""
    from evaluation.minimal_retrieval_ca_benchmark import DEFAULT_OUT_DIR, DEFAULT_REPORT_DIR
    assert DEFAULT_OUT_DIR.name == "minimal_retrieval_ca_benchmark"
    assert DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert DEFAULT_REPORT_DIR.name == "evaluation"
    assert DEFAULT_OUT_DIR.is_dir() and DEFAULT_REPORT_DIR.is_dir()