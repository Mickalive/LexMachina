"""Self-test for evaluation operational resume run 44715273665 (direction v68).

Runs under the documented no-pytest shim inside the run's own final-gates
phase, after the final-gates record exists and before the audit index is
written (the index is written last, by the state-update phase, so the index
row of this file is stamped after this file's content is final).

No fixtures, no parametrisation, no network. Read-only assertions over this
run's artifacts plus the preserved pack of run 44708758013.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUN = "44715273665"
RESUMED = "44708758013"
PRIOR_DIR = f"results/evaluation/operational_resume_{RESUMED}"
MY_DIR = f"results/evaluation/operational_resume_{RUN}"
SNAPSHOT_HEAD = "7de561aaadecdc08d92df8cb59a5a05077857834"
ACCEPTED_RUN = 40265377500

PIN_RULES_LABEL = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
PIN_RULES_GEOMETRY = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
PIN_FAST_MVP = "fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283"


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _sha(rel):
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def test_h1_failure_class_is_rc78_quantum_not_validation():
    diag = _load(f"{MY_DIR}/run_{RESUMED}_producer_quantum_diagnosis.json")
    assert diag["failure_class"] == "ORCHESTRATION_PRODUCER_QUANTUM_EXPIRY_RC78"
    assert diag["failing_step_duration_s"] == 2705
    assert diag["quantum_s"] == 2700
    assert diag["rc78_annotation_confirmed"] is True
    assert diag["quantum_annotation_confirmed"] is True
    assert diag["state_validation_skipped"] is True
    assert diag["write_scope_skipped"] is True
    assert "Validate active MVP producer state" in diag["skipped_steps"]
    assert "Enforce lane write scope" in diag["skipped_steps"]
    assert diag["gate_written"] is False


def test_h2_snapshot_state_would_have_passed_step7():
    snap = (Path(ROOT) / ".git")
    assert snap.is_dir()
    diag = _load(f"{MY_DIR}/run_{RESUMED}_producer_quantum_diagnosis.json")
    assert diag["state_would_have_passed_step_7"] is True
    st = _load("state/evaluation.json")
    assert st["direction_version"] == 68
    assert st["cycle_status"] != "INITIALIZED"


def test_h3_prior_pack_byte_identity_all_match():
    pack = _load(f"{MY_DIR}/{RESUMED}_pack_byte_identity_at_resume.json")
    assert pack["all_match"] is True
    assert pack["n_files"] == 18
    assert all(r["matches_pin"] for r in pack["files"])
    assert pack["prior_final_gates"]["verdict"] == "AUDIT_READY"
    assert pack["prior_final_gates"]["passed"] is True
    assert pack["prior_final_gates"]["generated_at_utc"] == "2026-11-20T09:43:58Z"


def test_h3_no_prior_file_modified_by_this_run():
    # every pinned prior file still hashes to its intake pin
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_instr", ROOT / f"evaluation/operational_resume_{RUN}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for rel, pin in mod.PRIOR_PACK_PINS.items():
        assert _sha(rel) == pin, f"prior file changed: {rel}"


def test_h4_battery_only_inherited_latent_red_fails():
    rec = _load(f"{MY_DIR}/{RUN}_regression_guard.json")
    rule = rec["run_rule"]
    assert rule["rule_pass"] is True
    assert rule["failed_cases"] == [
        "test_mount_provenance_gate.py::"
        "test_check_provenance_on_the_committed_tree_does_not_re_derive"]
    assert rec["n_absent"] == 0
    assert rule["excluded_from_record"] == []
    assert rule["negative_result_preserved"] is True


def test_h5_final_gates_passed_all_rules():
    fg = _load(f"{MY_DIR}/{RUN}_final_gates.json")
    assert fg["passed"] is True
    assert fg["verdict"] == "AUDIT_READY"
    assert all(fg["rule_pass"].values()), fg["rule_pass"]
    assert fg["exit_code"] == 0


def test_h5_nested_and_state_records_pass():
    nested = _load(f"{MY_DIR}/{RUN}_nested_evidence_refs.json")
    assert nested["n_unresolved"] == 0
    assert nested["n_top_level_unresolved"] == 0
    st = _load(f"{MY_DIR}/{RUN}_state_integrity.json")
    assert st["n_checks"] == 11 and st["n_failed"] == 0


def test_h6_residuals_disclosed_not_rewritten():
    res = _load(f"{MY_DIR}/{RESUMED}_residual_closure.json")
    assert res["R1_regression_record"]["prior_files_preserved"] is True
    assert res["R1_regression_record"]["prior_final_equals_attempt1"] is True
    assert res["R2_dangling_nested_citation"]["exists"] is False
    assert "DISCLOSED_NOT_FABRICATED" in res["R2_dangling_nested_citation"]["disposition"]
    assert res["R3_stale_audit_index"]["n_stale_rows"] >= 1
    assert res["R4_no_independent_audit_gate"]["prior_gate_exists"] is False


def test_h6_state_block_and_parity():
    root = _load("state/evaluation.json")
    lane = _load("evaluation/state/evaluation.json")
    for st in (root, lane):
        blk = st[f"operational_resume_{RUN}"]
        assert blk["direction_version"] == 68
        assert blk["accepted_run_id_unchanged"] == ACCEPTED_RUN
        assert st["direction_version"] == 68
        assert st["github_run"] == int(RUN)
        assert st["accepted_run_id"] == ACCEPTED_RUN
        assert st["evidence_refs_n"] == len(st["evidence_refs"])
        for ref in st["evidence_refs"]:
            assert (ROOT / ref).is_file(), f"unresolved evidence ref: {ref}"
    assert root["github_run"] == lane["github_run"]
    assert root["accepted_run_id"] == lane["accepted_run_id"]
    assert root["direction_version"] == lane["direction_version"]


def test_h6_state_block_cites_no_dangling_canonical_nested_record():
    root = _load("state/evaluation.json")
    blk = root[f"operational_resume_{RUN}"]
    cited = json.dumps(blk)
    dangling = f"{PRIOR_DIR}/44708758013_nested_evidence_refs.json"
    assert dangling not in cited
    assert blk["failure_diagnosis"]["class"].endswith("RC78")


def test_h8_frozen_inputs_unedited():
    assert _sha("evaluation/frozen_bars/RULES_LABEL.json") == PIN_RULES_LABEL
    assert _sha("evaluation/frozen_bars/RULES_GEOMETRY.json") == PIN_RULES_GEOMETRY
    assert _sha("evaluation/fast_mvp_retrieval_recall_benchmark.py") == PIN_FAST_MVP
    bench = _sha("results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
    assert bench == "fd25345b02da6658edbd5ed8722c69c9b3c7dbbc22e7856740cfdd421c5c4592"


def test_freeze_precedes_execution():
    fz = _load(f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    assert fz["freeze_precedes_execution"] is True
    assert fz["hypothesis_sha256"] == _sha(
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
    assert fz["instrument_sha256"] == _sha(
        f"evaluation/operational_resume_{RUN}.py")
    assert fz["test_sha256"] == _sha(
        f"tests/evaluation/test_operational_resume_{RUN}.py")
    assert fz["direction_version"] == 68
    assert fz["frozen_edits"] == []


def test_audit_index_if_written_is_complete_and_stamped_after_result():
    p = ROOT / f"{MY_DIR}/{RUN}_AUDIT_INDEX.json"
    if not p.is_file():
        return  # index is written last, after this self-test runs; checked by
        # the state-update phase exit condition instead
    idx = json.loads(p.read_text(encoding="utf-8"))
    assert idx["all_entries_exist"] is True, idx["missing_entries"]
    assert not idx["missing_entries"]
    result_row = next(r for r in idx["artifacts"] if r["path"].endswith(f"/{RUN}.json"))
    assert result_row["sha256"] == _sha(f"{MY_DIR}/{RUN}.json"), \
        "index row stale: index was written before the result record was stamped"
