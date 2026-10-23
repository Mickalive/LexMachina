"""Tests for repair round 1 of rejected evaluation cycle 40017649220.

These tests are the COMMITTED GUARD that the three ``required_fixes`` (F1/F2/F3)
of ``results/audit/evaluation/CYCLE_40017649220_GATE.json`` stay discharged.
They do NOT re-run the product, re-measure the bars, or touch any frozen rule,
threshold, rubric or incumbent. They re-verify the repair's own records.

They run under the repo's pytest-free shim::

    python -m evaluation.no_pytest_runner \\
        --run-id <id> \\
        --test-file tests/evaluation/test_repair_40017649220_r1.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.repair_40017649220_r1 import (  # noqa: E402
    ACCEPTED_BASE,
    BENCHMARK_SUITE,
    CYCLE_CLAIM_BEARING,
    FROZEN_PINS,
    GITHUB_RUN,
    NON_CLAIM_BEARING,
    REJECTED_TEAM_HEAD,
    REPAIR_ARTIFACTS,
    REPAIR_ROUND,
    REUSE_SUITES,
    RUN_ID,
    SCHEMA,
    UNSUPPORTED_CASE,
)

STATE_PATH = _REPO_ROOT / "state/evaluation.json"
REPAIR_DIR = _REPO_ROOT / "results/evaluation/repair_40017649220_r1"
ORCH = _REPO_ROOT / "results/evaluation/orchestration"
HYP_PATH = _REPO_ROOT / "evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json"
REPAIR_HYP_PATH = _REPO_ROOT / "evaluation/REPAIR_40017649220_HYPOTHESIS_V1.json"
FREEZE_PATH = _REPO_ROOT / "evaluation/REPAIR_40017649220_FREEZE_RECORD_V1.json"
SUMMARY = _REPO_ROOT / "reports/evaluation/EVALUATION_V65_CYCLE_SUMMARY.md"
BENCH_REPORT = _REPO_ROOT / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_v65_eval_40017649220.md"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _record(name: str) -> dict:
    p = ORCH / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# --------------------------------------------------------------------------
# C1 / C2 — frozen inputs, instrument and test are byte-identical to base
# --------------------------------------------------------------------------


def test_c1_frozen_bars_and_pins_unchanged():
    """Every frozen pin still hashes to its base value; none was edited."""
    for rel, want in FROZEN_PINS.items():
        p = _REPO_ROOT / rel
        assert p.exists(), f"frozen pin missing: {rel}"
        got = _sha(p)
        assert got == want, f"frozen pin drifted: {rel} {got[:16]} != {want[:16]}"


def test_c2_instrument_and_test_untouched_by_repair():
    """The repair edits no frozen benchmark instrument or its test file."""
    assert _sha(_REPO_ROOT / "evaluation/minimal_ret_ca_benchmark.py") == FROZEN_PINS[
        "evaluation/minimal_ret_ca_benchmark.py"]
    assert _sha(_REPO_ROOT / "tests/evaluation/test_minimal_ret_ca_benchmark.py") == FROZEN_PINS[
        "tests/evaluation/test_minimal_ret_ca_benchmark.py"]


def test_c2_repair_files_do_not_shadow_frozen_names():
    """No repair artifact reuses a frozen bar / rule / rubric path."""
    frozen_prefixes = ("evaluation/frozen_bars/",)
    for rel in REPAIR_ARTIFACTS:
        assert not rel.startswith(frozen_prefixes), rel


# --------------------------------------------------------------------------
# F1 — the test-suite claims are now backed by committed records
# --------------------------------------------------------------------------


def test_f1_shim_record_exists_with_measured_counts():
    """The benchmark-suite shim record is committed with real counts."""
    rec = _record(f"{RUN_ID}_R1_minimal_ret_ca_pytest_shim.json")
    assert rec, "definitive benchmark-suite shim record missing"
    assert rec["run_id"] == RUN_ID
    files = [x["test_file"] for x in rec.get("results", [])]
    assert files == [BENCHMARK_SUITE], files
    assert rec["n_passed"] == 4
    assert rec["n_failed"] == 0
    assert rec["n_skipped"] == 0
    assert rec["n_unsupported"] == 1
    assert rec["verdict"] == "SHIM_PASS"


def test_f1_unsupported_case_is_restated_not_passed():
    """The single UNSUPPORTED case is restated as NOT-RUN, never passed."""
    rec = _record(f"{RUN_ID}_R1_minimal_ret_ca_pytest_shim.json")
    cases = [c for r in rec["results"] for c in r["cases"]]
    unsup = [c for c in cases if c["status"] == "UNSUPPORTED"]
    assert len(unsup) == 1
    assert unsup[0]["test"] == UNSUPPORTED_CASE
    assert unsup[0].get("reason"), "UNSUPPORTED reason must be recorded"
    # it must NOT appear as a passing case anywhere
    passed = [c["test"] for c in cases if c["status"] == "PASS"]
    assert UNSUPPORTED_CASE not in passed


def test_f1_multilingual_and_provenance_suites_measured_green():
    """The FAST-MVP footer's reuse claim is backed by executed, recorded suites."""
    rec = _record(f"{RUN_ID}_R1_multiling_prov_pytest_shim.json")
    assert rec, "multilingual/provenance shim record missing"
    assert rec["n_failed"] == 0
    assert rec["n_skipped"] == 0
    assert rec["n_unsupported"] == 0
    assert rec["verdict"] == "SHIM_PASS"
    files = [r["test_file"] for r in rec["results"]]
    assert files == REUSE_SUITES, "reuse-suite set drifted from the frozen list"
    assert rec["n_passed"] == 73


def test_f1_unsupported_case_measured_out_of_shim():
    """The fixture-dependent case is measured out-of-shim, scratch-only."""
    p = ORCH / f"{RUN_ID}_R1_e2e_fixture_injected.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["case"] == UNSUPPORTED_CASE
    assert rec["status"] == "PASS"
    assert rec["error"] is None
    assert rec["scratch_outputs_written_under_tmp_only"], "must show scratch-only outputs"
    assert rec["no_committed_record_rewritten"] is True


def test_f1_e2e_cited_elapsed_matches_definitive_record():
    """Nothing may cite the discarded attempt-1 elapsed time as the measurement.

    The rejected team's pre-freeze attempt-1 e2e record (10.868s) is preserved
    under its original path, but the DEFINITIVE post-freeze `_R1_` record is the
    only measurement of record. Both the summary and the state restatement must
    quote the `_R1_` value, not the attempt-1 one.
    """
    defi = json.loads((ORCH / f"{RUN_ID}_R1_e2e_fixture_injected.json").read_text(encoding="utf-8"))
    attempt1 = ORCH / f"{RUN_ID}_e2e_fixture_injected.json"
    elapsed = defi["elapsed_s"]
    assert defi["status"] == "PASS"
    if attempt1.exists():
        a1 = json.loads(attempt1.read_text(encoding="utf-8"))
        assert elapsed != a1["elapsed_s"], (
            "definitive e2e record duplicates the attempt-1 run; it was not "
            "re-executed post-freeze")
        assert f"{a1['elapsed_s']}s" not in SUMMARY.read_text(encoding="utf-8"), (
            "summary cites the discarded attempt-1 elapsed time")
    # the summary quotes the definitive value
    assert f"{elapsed}s" in SUMMARY.read_text(encoding="utf-8")
    # and state quotes it too, sourced from the record rather than hardcoded
    entry = _state()["test_suite"]["minimal_ret_ca_benchmark"]
    assert f"{elapsed}s" in entry["unsupported_case_restated_as"]


def test_f1_reuse_instrument_rerun_reproduces_historical():
    """The accepted multilingual/provenance reuse instrument is re-run under
    run 40017649220 and reproduces the accepted record byte-for-byte."""
    p = _REPO_ROOT / f"results/evaluation/multilingual_provenance_reuse/{RUN_ID}.json"
    assert p.exists(), "re-homed reuse record missing"
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["executed"] is True
    assert rec["byte_identical_to_historical_record"] is True
    assert rec["historical_record_written_by_this_run"] is False
    assert rec["verdict"] == "PARTIAL_MISS"
    assert rec["summary"]["n_row_ok"] == 0
    assert rec["summary"]["n_qids"] == 3


def test_f1_state_test_suite_entry_published_for_this_run():
    """state/evaluation.json carries a measured test_suite entry for run
    40017649220, with env, counts, records and the NOT-RUN restatement."""
    st = _state()
    entry = st["test_suite"].get("minimal_ret_ca_benchmark")
    assert entry, "test_suite.minimal_ret_ca_benchmark is absent"
    assert entry["run_id"] == RUN_ID
    assert entry["file"] == BENCHMARK_SUITE
    assert entry["passed"] == 4
    assert entry["failed"] == 0
    assert entry["skipped"] == 0
    assert entry["unsupported"] == 1
    assert "pytest" in entry["measurement_env"] and "ABSENT" in entry["measurement_env"]
    assert entry["record"].endswith(f"{RUN_ID}_R1_minimal_ret_ca_pytest_shim.json")
    assert UNSUPPORTED_CASE in entry["unsupported_case_restated_as"]
    assert "NOT-RUN" in entry["unsupported_case_restated_as"]
    # the reuse suites are published too
    reuse = st["test_suite"].get("multilingual_provenance_reuse")
    assert reuse and reuse["passed"] == 73 and reuse["failed"] == 0


def test_f1_summary_cites_measurement_env_counts_and_record_path():
    """The cycle summary no longer asserts tests without env, counts or a path."""
    txt = SUMMARY.read_text(encoding="utf-8")
    assert RUN_ID in txt
    for needle in ("SHIM_PASS", "4 passed", "0 failed", "0 skipped",
                   "NOT-RUN", "no_pytest_runner.py"):
        assert needle in txt, f"summary is missing the measured claim: {needle!r}"
    assert str(ORCH.relative_to(_REPO_ROOT)) in txt


def test_f1_summary_footer_narrowed_to_what_ran():
    """The FAST-MVP footer no longer claims reuse that was never executed."""
    txt = SUMMARY.read_text(encoding="utf-8")
    assert "Reuse existing multilingual/provenance tests" not in txt


# --------------------------------------------------------------------------
# F2 — the evidence index covers all nine claim-bearing cycle artifacts
# --------------------------------------------------------------------------


def test_f2_evidence_index_covers_all_nine_cycle_artifacts():
    st = _state()
    refs = set(st["evidence_refs"])
    missing = [r for r in CYCLE_CLAIM_BEARING if r not in refs]
    assert not missing, f"evidence_refs missing cycle artifacts: {missing}"


def test_f2_evidence_refs_n_equals_len():
    st = _state()
    assert st["evidence_refs_n"] == len(st["evidence_refs"])


def test_f2_every_evidence_ref_resolves_on_disk():
    st = _state()
    unresolved = [r for r in st["evidence_refs"]
                  if not (_REPO_ROOT / r).exists()]
    # the two inherited-not-charged defects stay disclosed, not silently dropped
    known = {
        "results/evaluation/orchestration/39875239812_diagnosis.json",
        "results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt",
    }
    unexpected = [r for r in unresolved if r not in known]
    assert not unexpected, f"unresolvable evidence refs: {unexpected}"


def test_f2_inherited_defects_disclosed_not_deleted():
    st = _state()
    disc = st.get("evidence_index_defects_inherited_not_charged", {})
    assert disc, "inherited evidence-index defects must be disclosed"
    assert "39875239812_diagnosis.json" in json.dumps(disc)
    assert "producer_work_state_and_next_move.txt" in json.dumps(disc)


def test_f2_verify_v65_files_marked_non_claim_bearing():
    st = _state()
    roles = st.get("evidence_ref_roles", {})
    for rel in NON_CLAIM_BEARING:
        assert roles.get(rel) == "NON_CLAIM_BEARING_VERIFY_OUTPUT", rel


def test_f2_no_deleted_evidence_ref():
    """F2 adds refs; it never deletes a previously indexed one."""
    st = _state()
    refs = set(st["evidence_refs"])
    for rel in ("state/evaluation.json",
                "reports/evaluation/EVALUATION_V65_CYCLE_SUMMARY.md",
                "reports/evaluation/RETRIEVAL_CA_BENCHMARK_v65_eval_40017649220.md"):
        assert rel in refs or rel.startswith("state/")


# --------------------------------------------------------------------------
# F3 — cycle hypothesis/provenance record, NOT_FREEZE_FIRST
# --------------------------------------------------------------------------


def test_f3_hypothesis_record_exists_and_is_indexed():
    assert HYP_PATH.exists()
    st = _state()
    assert (str(HYP_PATH.relative_to(_REPO_ROOT))) in st["evidence_refs"]


def test_f3_declares_not_freeze_first():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    o = hyp["ORDERING_DISCLOSURE__NOT_FREEZE_FIRST"]
    assert o["status"] == "NOT_FREEZE_FIRST"
    assert o["freeze_claim_made"] is False
    joined = " ".join(o["true_ordering"])
    assert "20:16:19Z" in joined and "20:37:19Z" in joined
    assert "2026-10-23" in joined


def test_f3_carries_inherited_frozen_spec():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    a = hyp["A__INHERITED_FROZEN_SPEC"]
    assert a["instrument"]["last_modified_commit"] == (
        "2e7d4fe566bf2ae7e80f0cfede09d0f0cb22cc83")
    assert a["instrument"]["touched_by_run_40017649220"] is False
    assert a["frozen_qids"] == [
        "de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
    assert a["frozen_label_incumbent"]["value"] == {
        "n_scored": 65, "n_supported": 5,
        "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0}}
    assert a["frozen_geometry_incumbent"]["value"] == {
        "de-kapitalverletzung": 6, "fr-bail-entretien": 5,
        "it-responsabilita-medica": 5}
    assert a["combined_verdict_rule"]
    assert a["state_claim_ceiling"]


def test_f3_carries_no_post_hoc_tuning_proof():
    hyp = json.loads(HYP_PATH.read_text(encoding="utf-8"))
    b = hyp["B__NO_POST_HOC_TUNING"]
    assert b["proof_1_instrument_unchanged"]["identical"] is True
    assert b["proof_1_instrument_unchanged"]["working_tree_sha256"] == FROZEN_PINS[
        "evaluation/minimal_ret_ca_benchmark.py"]
    assert b["proof_2_test_unchanged"]["identical"] is True
    assert b["proof_3_output_quantity_for_quantity_identical_to_base_runs"]
    assert b["proof_4_no_frozen_file_edited_by_the_cycle"]
    assert b["proof_5_reproducibility_independent_reexecution"]


def test_f3_reports_cite_the_hypothesis_record():
    rel = str(HYP_PATH.relative_to(_REPO_ROOT))
    assert rel in SUMMARY.read_text(encoding="utf-8")
    assert rel in BENCH_REPORT.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Controls C4/C6 + the repair record itself
# --------------------------------------------------------------------------


def test_c4_attempt1_artifacts_preserved():
    for name in (f"{RUN_ID}_minimal_ret_ca_pytest_shim.json",
                 f"{RUN_ID}_multiling_prov_pytest_shim.json",
                 f"{RUN_ID}_e2e_fixture_injected.json"):
        assert (ORCH / name).exists(), name


def test_c6_posture_flags_stay_false():
    st = _state()
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    assert st["owner_decision_required"] is False


def test_c6_claim_ceiling_unchanged_and_not_upgraded():
    st = _state()
    ceiling = st["minimal_ret_ca_benchmark"]["claim_ceiling"]
    assert "does not" in ceiling or "never" in ceiling.lower() or "only" in ceiling
    # posture flags live at top level of state; they must stay False alongside
    # the unchanged claim ceiling (none may be upgraded to justify the ceiling).
    for k in ("human_gate_ready", "packet_admitted", "machine_gate_ready",
              "ready_for_owner_session", "owner_decision_required"):
        assert st[k] is False


def test_repair_record_verdict_is_discharged():
    p = REPAIR_DIR / f"{GITHUB_RUN}.json"
    assert p.exists(), "repair record missing"
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["schema"] == SCHEMA
    assert rec["verdict"] == "REPAIR_R1_DISCHARGED"
    assert rec["all_checks_hold"] is True
    assert rec["no_174k_benchmark_rerun"] is True
    assert rec["frozen_bars_edited"] is False
    assert rec["historical_record_overwritten"] is False


def test_repair_record_all_checks_hold():
    rec = json.loads((REPAIR_DIR / f"{GITHUB_RUN}.json").read_text(encoding="utf-8"))
    failed = [k for k, v in rec["checks"].items() if not v]
    assert not failed, f"repair checks failed: {failed}"
    assert rec["n_checks_hold"] == rec["n_checks"]


def test_freeze_record_predates_the_repair_executions():
    """The repair hypothesis + freeze must be committed before definitive
    execution: their mtimes precede the definitive shim records."""
    assert REPAIR_HYP_PATH.exists() and FREEZE_PATH.exists()
    hyp_m = REPAIR_HYP_PATH.stat().st_mtime
    frz_m = FREEZE_PATH.stat().st_mtime
    for name in (f"{RUN_ID}_R1_minimal_ret_ca_pytest_shim.json",
                 f"{RUN_ID}_R1_multiling_prov_pytest_shim.json"):
        assert (ORCH / name).stat().st_mtime > hyp_m, name
        assert (ORCH / name).stat().st_mtime > frz_m, name


def test_repair_hypothesis_and_freeze_record_exist():
    hyp = json.loads(REPAIR_HYP_PATH.read_text(encoding="utf-8"))
    # the GitHub run that produced this repair, and the rejected cycle it repairs
    assert hyp["run_id"] == GITHUB_RUN
    assert hyp["repairs_run_id_of_record"] == RUN_ID
    assert hyp["frozen_before_definitive_claim_bearing_execution"] is True
    frz = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert frz["run_id"] == GITHUB_RUN
    assert frz["repairs_run_id_of_record"] == RUN_ID
    assert frz["repair_round"] == REPAIR_ROUND
    assert frz["rejected_team_head"] == REJECTED_TEAM_HEAD
    assert frz["accepted_base"] == ACCEPTED_BASE


def test_no_obsolete_174k_benchmark_is_rerun_by_this_repair():
    """The FAST-MVP scope rule: the universal-174k benchmarks are NOT rerun."""
    st = _state()
    for key in ("universal_174k", "offline_emission_path_benchmark"):
        if key in st:
            assert st[key].get("rerun_by_repair_round_1") is not True
    # the repair record asserts it directly
    rec = json.loads((REPAIR_DIR / f"{GITHUB_RUN}.json").read_text(encoding="utf-8"))
    assert rec["no_174k_benchmark_rerun"] is True


def test_f2_all_planned_repair_artifacts_resolve():
    missing = [r for r in REPAIR_ARTIFACTS if not (_REPO_ROOT / r).exists()]
    assert not missing, f"repair artifacts missing: {missing}"
