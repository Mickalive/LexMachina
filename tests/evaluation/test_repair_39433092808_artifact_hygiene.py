"""Regression tests pinning repair round 1 of rejected evaluation cycle 39433092808.

Independent audit ``CYCLE_39433092808`` returned gate=REVISE with five required
fixes (R1-R5), all artifact-hygiene defects in the producer commit ``ca58be99``.
These tests pin that every fix is discharged and that the same defect class
cannot silently return:

R1  the committed claim-bearing disposition record
    ``results/evaluation/repair_39402114706/39422312905_disposition_verification.json``
    is restored to the accepted-base bytes (it had been overwritten and
    re-labelled ``run_id: local_final``), and the instrument's ``DEFAULT_OUT`` no
    longer points at a committed record.
R2  no ``local_*`` / ``pytest_local*`` / ``test_resume*`` scratch run sits in a
    claim-bearing tree; the leaked files are parked verbatim under
    ``_scratch_namespaced/39433092808/``.
R3  the stale direction-v58 probe ``local_test_2.json`` is out of the claim-bearing
    tree and its existence/verdict is disclosed in ``state/evaluation.json``.
R4  ``state/evaluation.json`` preserves the structured ``durable_delta_39422312905``
    fields that the accepted state carried and advances run attribution.
R5  ``evaluation/scratch_output_isolation.py`` enumerates the claim-bearing
    directories instead of a hard-coded ``pytest_local*`` list.

NON-WEAKENING CONTRACT
----------------------
These tests add no new threshold, metric, success rule or scope.  Frozen rubrics,
thresholds and the absolute bars are not re-derived here; the disposition record
is only byte-compared against the accepted-base blob.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

DISPOSITION = (
    _ROOT / "results/evaluation/repair_39402114706"
    / "39422312905_disposition_verification.json")
#: sha256 of the accepted-base (db0e70e1) bytes of the disposition record.
ACCEPTED_BASE_SHA256 = (
    "e5f4b451ce31213f0653220ca7a2a8b5704da7d8ef3291412e3cc722f9f40960")
ACCEPTED_BASE_COMMIT = "db0e70e1"

SCRATCH_NS = _ROOT / "results/evaluation/_scratch_namespaced/39433092808"
REPORT_SCRATCH_NS = _ROOT / "reports/evaluation/_scratch_namespaced/39433092808"

#: The scratch artifacts the audit found in claim-bearing trees (R2 + R3).
LEAKED_SCRATCH = [
    "results/evaluation/retrieval_counter_authority_benchmark/local_final.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_final_leg1_served_baseline.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_final_leg2_hostile_geometry.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_final_leg3_blanked_evidence.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_test_1.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_test_1_leg1_served_baseline.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_test_1_leg2_hostile_geometry.json",
    "results/evaluation/retrieval_counter_authority_benchmark/local_test_1_leg3_blanked_evidence.json",
    "results/evaluation/stand_ready_multilingual_probe/local_test_2.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_final.md",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_test_1.md",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(_ROOT), *args],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _state() -> dict:
    return json.loads((_ROOT / "state/evaluation.json").read_text(encoding="utf-8"))


# ============================================================ R1: restore the record
def test_r1_disposition_record_restored_to_accepted_base_bytes():
    """R1: the committed disposition record re-hashes to the accepted-base digest."""
    assert DISPOSITION.is_file(), f"missing {DISPOSITION}"
    actual = _sha256(DISPOSITION)
    assert actual == ACCEPTED_BASE_SHA256, (
        f"committed disposition record is NOT the accepted-base content "
        f"(actual {actual}, expected {ACCEPTED_BASE_SHA256})")
    rec = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    assert rec["run_id"] == "39422312905", (
        "a file named for run 39422312905 must declare run_id 39422312905; "
        f"observed {rec['run_id']!r}")
    # when the accepted-base commit is present, prove the file's git blob is the
    # accepted-base blob (exact object identity; newline-independent).
    rel = DISPOSITION.relative_to(_ROOT).as_posix()
    accepted_blob = _git("rev-parse", f"{ACCEPTED_BASE_COMMIT}:{rel}")
    current_blob = _git("hash-object", str(DISPOSITION))
    if accepted_blob is not None and current_blob is not None:
        assert current_blob == accepted_blob, (
            f"the restored file's git blob {current_blob} is not the accepted-base "
            f"blob {accepted_blob}")


def test_r1_default_out_is_not_a_committed_record():
    """R1 root cause: the verifier default must not target a claim-bearing file."""
    from evaluation.repair_39402114706_fixes import DEFAULT_OUT
    claim_tree = _ROOT / "results/evaluation/repair_39402114706"
    assert claim_tree not in DEFAULT_OUT.parents and DEFAULT_OUT != claim_tree, (
        "DEFAULT_OUT must not point inside the claim-bearing repair_39402114706 tree")
    assert "_scratch_namespaced" in str(DEFAULT_OUT), (
        f"DEFAULT_OUT must be scratch-namespaced; observed {DEFAULT_OUT}")
    assert not DEFAULT_OUT.name.startswith("39422312905"), (
        "the run-39422312905 committed record must never be the default target")


# ============================================================== R2: scratch leak gone
def test_r2_no_scratch_run_in_claim_bearing_trees():
    """R2: the exact leak class is absent from every claim-bearing tree."""
    for rel in LEAKED_SCRATCH:
        assert not (_ROOT / rel).exists(), f"scratch leak still present: {rel}"
    from evaluation.scratch_output_isolation import scan_claim_trees
    findings = scan_claim_trees(_ROOT)
    assert findings == [], f"claim-bearing trees still carry scratch runs: {findings}"


def test_r2_leaked_scratch_preserved_verbatim_under_scratch_namespace():
    """R2: nothing deleted — the moved records are readable in the scratch namespace."""
    moved = [
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_final.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_final_leg1_served_baseline.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_final_leg2_hostile_geometry.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_final_leg3_blanked_evidence.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_test_1.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_test_1_leg1_served_baseline.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_test_1_leg2_hostile_geometry.json",
        SCRATCH_NS / "retrieval_counter_authority_benchmark/local_test_1_leg3_blanked_evidence.json",
        SCRATCH_NS / "stand_ready_multilingual_probe/local_test_2.json",
        REPORT_SCRATCH_NS / "RETRIEVAL_CA_BENCHMARK_local_final.md",
        REPORT_SCRATCH_NS / "RETRIEVAL_CA_BENCHMARK_local_test_1.md",
    ]
    missing = [str(p) for p in moved if not p.is_file()]
    assert not missing, f"moved scratch artifacts are not all preserved: {missing}"


# ================================================== R3: stale v58 probe out + disclosed
def test_r3_stale_v58_probe_out_of_claim_tree_and_disclosed():
    """R3: the stale probe is moved AND its verdict is disclosed in the lane state."""
    assert not (_ROOT / "results/evaluation/stand_ready_multilingual_probe/local_test_2.json").exists()
    st = _state()
    block = st.get("repair_round_1_39433092808", {})
    assert block.get("stale_v58_probe_disclosed") is True, (
        "the direction-v58 local_test_2 probe must be disclosed in state/evaluation.json")
    assert block.get("stale_v58_probe_verdict") == "ENVIRONMENT_OR_VACUOUS"


# ==================================================== R4: structured state + attribution
def test_r4_structured_durable_delta_fields_preserved():
    """R4: the accepted structured durable_delta_39422312905 fields survive."""
    delta = _state()["durable_delta_39422312905"]
    for key in ("freeze_first_commit", "hypothesis_sha256",
                "disposition_of_blocked_gate", "restored_artifact",
                "rehomed_artifact", "minimal_ca_verdict", "minimal_ca_record",
                "status"):
        assert key in delta, f"durable_delta_39422312905 lost structured field {key!r}"
    assert delta["freeze_first_commit"] == "07cf996ffd7b0ea72bc290afc7c2d021517d1bcc"
    assert delta["hypothesis_sha256"] == (
        "1e694576da7560842d0da8a8887fe454469f9bf269ace7d58a9a417bd12cf51d")
    assert delta["disposition_of_blocked_gate"] == "CYCLE_39413028463"
    assert delta["status"] == "MEASUREMENTS_RECORDED"
    assert delta["minimal_ca_verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"


def test_r4_run_attribution_advanced_to_repair_run():
    """R4: run attribution names the repair run that made the claim."""
    st = _state()
    assert st["github_run"] == 39441009094
    assert st["last_verified_run"] == 39441009094
    assert st["proposed_run_id"] == 39441009094


# ====================================================================== R5: scanner
def test_r5_scratch_isolation_enumerates_claim_trees(tmp_path):
    """R5: a scratch run under a NEW name is caught by the directory enumeration."""
    from evaluation.scratch_output_isolation import scan_claim_trees
    # plant a brand-new scratch name in a claim-bearing dir
    claim = tmp_path / "results/evaluation/retrieval_counter_authority_benchmark"
    claim.mkdir(parents=True)
    (claim / "totally_new_scratch_name.json").write_text("{}", encoding="utf-8")
    findings = scan_claim_trees(tmp_path)
    assert any("totally_new_scratch_name.json" in f["path"] for f in findings), (
        f"the directory-enumeration scanner did not catch a new scratch name: {findings}")


def test_r5_scratch_marker_pattern_is_caught(tmp_path):
    """R5: the historical local_/pytest_local/test_resume markers are caught."""
    from evaluation.scratch_output_isolation import scan_claim_trees
    claim = tmp_path / "reports/evaluation"
    claim.mkdir(parents=True)
    (claim / "RETRIEVAL_CA_BENCHMARK_local_final.md").write_text("x", encoding="utf-8")
    findings = scan_claim_trees(tmp_path)
    assert any("local_final.md" in f["path"] for f in findings)
