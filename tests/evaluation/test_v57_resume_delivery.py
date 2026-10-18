"""Regression tests for the cycle-39173770080 operational-resume delivery.

FROZEN-BENCHMARK INTEGRITY (audit CYCLE_39164900837 F8) and
SCRATCH-RUN ISOLATION (audit CYCLE_39164900837 F9) were both required fixes
that the repair round recorded as SCHEDULED, NOT DONE.  This file is the
executable half of closing them.

It is a POST-FREEZE ADDITION in the sense of
evaluation/retrieval_gate/id_hygiene.py: no gate is added to any frozen verdict
file, no accepted verdict is overwritten, and no frozen benchmark, rubric,
threshold, incumbent or success rule is touched.  The frozen pins below are
RE-HASHES, not restatements of a literal: if a pin is wrong the test fails.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import coverage_handoff_status, orchestration_resume_probe  # noqa: E402
from evaluation import retrieval_cache_digest_manifest as manifest_mod  # noqa: E402
from evaluation import scratch_output_isolation  # noqa: E402
from evaluation.retrieval_gate import frozen as retrieval_frozen  # noqa: E402

RUN_ID = "39173770080"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# the three frozen pins this cycle re-hashes rather than restates
# --------------------------------------------------------------------------- #


def test_frozen_pins_are_rehashed_not_restated():
    assert _sha256(retrieval_frozen._PATH) == retrieval_frozen.FROZEN_SHA256
    # factory-wide requirement 3 / direction v57: FREEZE_RECORD.json is read-only
    # input for the F8 manifest.  If this assertion ever fails, the F8 fix has
    # edited a pinned freeze artefact and must be reverted, not "re-pinned".
    assert _sha256(retrieval_frozen.FREEZE_RECORD_PATH) == manifest_mod.FREEZE_RECORD_SHA256


# --------------------------------------------------------------------------- #
# H1 - the orchestration probe that diagnosed run 39173551486
# --------------------------------------------------------------------------- #


def test_orchestration_probe_discriminates_every_class():
    report = orchestration_resume_probe.self_test()
    assert report["all_passed"], report["cases"]


def test_orchestration_probe_class_glossary_covers_every_class_it_can_return():
    reachable = {
        orchestration_resume_probe.classify(**kw) for kw in (
            {"tip_moved": False, "files_name_run": False,
             "commit_names_run": False, "gate_present": False},
            {"tip_moved": False, "files_name_run": False,
             "commit_names_run": True, "gate_present": False},
            {"tip_moved": True, "files_name_run": True,
             "commit_names_run": True, "gate_present": True},
            {"tip_moved": True, "files_name_run": True,
             "commit_names_run": True, "gate_present": False},
            {"tip_moved": True, "files_name_run": False,
             "commit_names_run": True, "gate_present": False},
        )
    }
    assert reachable <= set(orchestration_resume_probe.CLASSES)


def test_orchestration_record_of_this_cycle_is_about_the_failed_run():
    path = (_REPO_ROOT / "results/evaluation/orchestration" / f"{RUN_ID}.json")
    assert path.is_file(), f"missing orchestration record: {path}"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == orchestration_resume_probe.SCHEMA
    assert rec["subject_run_id"] == "39173551486"
    assert rec["derived_class"] == (
        "TEAM_JOB_ZERO_COMMIT__AUDIT_SKIPPED__NO_GATE_FILE")
    # the diagnosis must be reproducible from git, not asserted
    assert rec["n_tracked_files_naming_run_id"] == 0
    assert rec["n_commits_naming_run_id"] == 0
    assert rec["audit_gate_present"] is False
    assert rec["tip_moved_versus_seed"] is False
    assert rec["selftest"]["all_passed"] is True
    assert "Orchestration only" in rec["claim_ceiling"]


def test_probe_reproduces_the_diagnosis_live():
    """The committed record must be re-derivable, not a story."""
    live = orchestration_resume_probe.probe(
        "39173551486", "refs/remotes/origin/cycle/core/evaluation/39173551486/team")
    assert live["derived_class"] == (
        "TEAM_JOB_ZERO_COMMIT__AUDIT_SKIPPED__NO_GATE_FILE")
    assert live["audit_gate_present"] is False
    assert live["tracked_files_naming_run_id"] == []


# --------------------------------------------------------------------------- #
# H3/F8 - the additive frozen-cache digest manifest
# --------------------------------------------------------------------------- #


def test_cache_manifest_selftest_detects_drift():
    assert manifest_mod.selftest()["all_passed"]


def test_cache_manifest_of_record_is_stable_and_complete():
    path = (_REPO_ROOT / "results/evaluation/retrieval_cache_digest_manifest"
            / f"{RUN_ID}.json")
    assert path.is_file(), f"missing manifest: {path}"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == manifest_mod.SCHEMA
    assert rec["verdict"] == manifest_mod.VERDICT_STABLE
    assert rec["n_queries"] == 24
    assert rec["n_match"] == 24 and rec["n_drift"] == 0
    # the manifest is additive: it names the pin it refuses to write
    assert rec["frozen_pins"]["freeze_record_edited_by_this_module"] is False
    assert rec["frozen_pins"]["freeze_record_sha256"] == manifest_mod.FREEZE_RECORD_SHA256
    assert rec["accepted_run_of_record_sha256"] == manifest_mod.ACCEPTED_RECORD_SHA256
    # every row pins a real 64-hex digest, never a placeholder
    for row in rec["rows"]:
        for key in ("pinned_body_sha256", "committed_body_sha256"):
            assert row[key] is not None and len(row[key]) == 64
            int(row[key], 16)


def test_cache_manifest_verifies_against_the_committed_tree():
    path = (_REPO_ROOT / "results/evaluation/retrieval_cache_digest_manifest"
            / f"{RUN_ID}.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["rows_by_query_key"] = {r["query_key"]: r for r in manifest["rows"]}
    result = manifest_mod.verify_against(manifest, _REPO_ROOT)
    assert result["verdict"] == manifest_mod.VERDICT_STABLE, result["drift"]
    assert result["n_drift"] == 0
    assert result["n_rows"] == 24


# --------------------------------------------------------------------------- #
# H2/F9 - scratch runs must not rewrite committed evidence
# --------------------------------------------------------------------------- #


def test_scratch_run_leak_pre_fix_measurement_is_preserved():
    path = (_REPO_ROOT / "results/evaluation/scratch_output_isolation"
            / f"{RUN_ID}.json")
    assert path.is_file(), f"missing isolation record: {path}"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == scratch_output_isolation.SCHEMA
    assert rec["verdict"] == "SCRATCH_RUN_ISOLATED"
    assert rec["n_mutated"] == 0
    assert rec["n_committed_artifacts"] == 5
    # the negative result is preserved beside the fix, never overwritten
    assert rec["pre_fix_measurement_39173770080"]["n_mutated"] == 5
    assert rec["pre_fix_measurement_39173770080"]["verdict"] == "SCRATCH_RUN_LEAKS"
    for row in rec["committed_evidence"]:
        assert row["mutated"] is False
        assert row["sha256_before"] == row["sha256_after"]


def test_benchmark_exposes_and_enforces_its_output_directories():
    from evaluation.benchmark_retrieval_counter_authority import (
        DEFAULT_OUT_DIR, DEFAULT_REPORT_DIR, main,
    )
    src = (_REPO_ROOT / "evaluation/benchmark_retrieval_counter_authority.py"
           ).read_text(encoding="utf-8")
    assert "--out-dir" in src and "--report-dir" in src
    assert DEFAULT_OUT_DIR == (_REPO_ROOT / "results/evaluation"
                               / "retrieval_counter_authority_benchmark")
    assert DEFAULT_REPORT_DIR == _REPO_ROOT / "reports/evaluation"
    assert callable(main)


def test_accepted_end_to_end_test_no_longer_targets_the_committed_tree():
    src = (_REPO_ROOT / "tests/evaluation"
           / "test_benchmark_retrieval_counter_authority.py").read_text(
               encoding="utf-8")
    assert '"--out-dir"' in src and '"--report-dir"' in src
    # the regression that produced the leak: a subprocess call with no output
    # redirection at all
    assert '"--run-id", "pytest_local"],' not in src


# --------------------------------------------------------------------------- #
# H4 - the Item-2 consumption gate (must NOT consume)
# --------------------------------------------------------------------------- #


def test_handoff_status_selftest_flips_on_a_moved_head():
    assert coverage_handoff_status.selftest()["all_passed"]


def test_handoff_status_record_blocks_rather_than_pre_empts():
    path = (_REPO_ROOT / "results/evaluation/coverage_handoff_status"
            / f"{RUN_ID}.json")
    assert path.is_file(), f"missing handoff status record: {path}"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == coverage_handoff_status.SCHEMA
    assert rec["executed_this_cycle"] is False
    if rec["product_head_moved"] is False:
        assert rec["status"] == coverage_handoff_status.STATUS_BLOCKED
        assert "DO NOT re-execute" in rec["next_command"]
    else:
        assert rec["status"] == coverage_handoff_status.STATUS_READY
        assert "re-freeze" in rec["next_command"]
    # whatever the status, Item 2 stays OPEN: this cycle cannot consume it
    assert "Item 2" in rec["claim_ceiling"]


def test_this_cycle_did_not_write_a_new_falsification_record():
    """The strongest possible pin on 'do not pre-empt': the set of executed
    falsification records is unchanged by this cycle."""
    out = subprocess.run(
        [sys.executable, "-m", "evaluation.coverage_handoff_status",
         "--run-id", "probe"],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-500:]
    latest = coverage_handoff_status.latest_falsification_record(_REPO_ROOT)
    assert latest is not None
    assert latest["record"]["run_id"] != RUN_ID, (
        "this cycle executed the Item-2 falsification; the handoff must be "
        "consumed once, by a cycle that can publish before/after records")


# --------------------------------------------------------------------------- #
# H5 - the FAST MVP falsification benchmark re-executed for this run
# --------------------------------------------------------------------------- #


def test_benchmark_record_of_this_run_is_a_claim_bearing_result():
    out_dir = _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark"
    combined = out_dir / f"{RUN_ID}.json"
    assert combined.is_file(), f"missing benchmark record: {combined}"
    rec = json.loads(combined.read_text(encoding="utf-8"))
    assert rec["schema"] == "lex-evaluation-retrieval-ca-benchmark/1"
    assert rec["run_id"] == RUN_ID
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is True
    legs = {lg["leg"]: lg for lg in rec["legs"]}
    assert set(legs) == {"served_baseline", "geometry_falsification_hostile",
                         "label_falsification_blanked_evidence"}
    assert legs["served_baseline"]["exit_code"] == 0
    assert legs["served_baseline"]["verdict"] == "PASS_NO_REGRESSION"
    assert legs["geometry_falsification_hostile"]["exit_code"] == 1
    assert legs["label_falsification_blanked_evidence"]["exit_code"] == 1
    for lg in legs.values():
        assert lg["exit_code_matches_expectation"] is True
    # the record may never claim an absolute bar
    assert "does NOT meet the absolute" in rec["absolute_status_note"]
    assert (out_dir / f"{RUN_ID}_leg1_served_baseline.json").is_file()
    assert (out_dir / f"{RUN_ID}_leg2_hostile_geometry.json").is_file()
    assert (out_dir / f"{RUN_ID}_leg3_blanked_evidence.json").is_file()
    report = _REPO_ROOT / "reports/evaluation" / f"RETRIEVAL_CA_BENCHMARK_{RUN_ID}.md"
    assert report.is_file()
    assert "BENCHMARK_VALID_NO_FALSIFICATION" in report.read_text(encoding="utf-8")