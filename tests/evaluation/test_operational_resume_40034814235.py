"""Guard tests for evaluation operational-resume cycle 40034814235.

These tests are the COMMITTED GUARD that this run's verification claims stay
backed by committed machine artifacts. They do NOT re-run the product, re-measure
the bars, or touch any frozen rule, threshold, rubric or incumbent. They verify:

  * the freeze-first hypothesis record and its ordering declaration;
  * the six-run orchestration failure-chain diagnosis (zero work lost);
  * the freeze-first benchmark confirmation (verdict + frozen pins + identity
    with the measurement of record modulo normalised fields);
  * the three shim-suite re-execution records and their counts;
  * the multilingual-reuse byte-identity pin;
  * frozen-input re-hash pins at this head;
  * state/evaluation.json run identity, posture-false flags, evidence-index
    coverage of this run's artifacts and the repair-discharge pointers.

They run under the repo's pytest-free shim::

    python -m evaluation.no_pytest_runner \\
        --run-id 40034814235 \\
        --test-file tests/evaluation/test_operational_resume_40034814235.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN = "40034814235"
STATE_PATH = _REPO_ROOT / "state/evaluation.json"
ORCH = _REPO_ROOT / "results/evaluation/orchestration"
BENCH_DIR = _REPO_ROOT / "results/evaluation/minimal_ret_ca_benchmark"
HYP = _REPO_ROOT / "evaluation/OPERATIONAL_RESUME_40034814235_HYPOTHESIS_V1.json"
DIAG = ORCH / "40034814235_failure_chain_diagnosis.json"
VERIF = ORCH / "40034814235_verification_of_repair_40017649220_r1.json"

FROZEN_PINS = {
    "evaluation/frozen_bars/RULES_LABEL.json": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json": "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/minimal_ret_ca_benchmark.py": "70f8158c9049df2d03ebcc460b782178967ab9da7a11e48dd1b5b132d9f17167",
    "tests/evaluation/test_minimal_ret_ca_benchmark.py": "49c94f7bfae80bfbad93da431d7a25ddb68e44bf9aab6daeef80cd37f42cfb6e",
    "evaluation/no_pytest_runner.py": "c12097da9d910574380b32c5dafa371a3b24ec14ef2551d92bb9453b8ed57584",
}
SERVED_BUNDLE_PINS = {
    "de-kapitalverletzung": "2441ff2b16722afcd22dca9ad39eafcbeb079b2dfc367d763fbe53fce1356f9c",
    "fr-bail-entretien": "6c5ea31d4b9af4abfa39e9f8025cfa3d34279ff1f04d0f643e571e27b23a2618",
    "it-responsabilita-medica": "76e7f7ad998f3878e7b08635663e2d594a7a77bdaeb33bcf5fa52d0af00b7aff",
}
FAILED_CHAIN_RUNS = [
    "40023576675",
    "40029231841",
    "40029524205",
    "40033424089",
    "40033628306",
    "40034534808",
]
MLP_RAW_SHA = "82ae91b536623e77dbd39888db3b0df4dce45c9a3c21879549b6b755b07da428"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _j(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _state() -> dict:
    return _j(STATE_PATH)


def _normalised(d: dict) -> dict:
    skip = {
        "run_id",
        "generated_at_utc",
        "elapsed_s",
        "served_packet_dir",
        "report_md",
    }
    return {k: v for k, v in d.items() if k not in skip}


# --- freeze record ---------------------------------------------------------


def test_freeze_record_exists_and_declares_ordering():
    hyp = _j(HYP)
    assert hyp["run_id"] == RUN
    assert hyp["lane"] == "evaluation"
    assert hyp["direction_version"] == 65
    assert "committed BEFORE the claim-bearing" in hyp["record_kind"]


def test_freeze_record_pins_match_files_on_disk():
    hyp = _j(HYP)
    pins = hyp["A__INHERITED_FROZEN_SPEC_REHASHED"]["frozen_rules"]
    for rel, want in pins.items():
        assert _sha(_REPO_ROOT / rel) == want, rel
    inst = hyp["A__INHERITED_FROZEN_SPEC_REHASHED"]["instrument_and_tests"]
    for rel, meta in inst.items():
        if not isinstance(meta, dict) or "sha256" not in meta:
            continue  # prose key (e.g. byte_identity_vs_accepted_base...), not a path
        assert _sha(_REPO_ROOT / rel) == meta["sha256"], rel


# --- orchestration diagnosis ----------------------------------------------


def test_diagnosis_covers_the_six_failed_runs():
    diag = _j(DIAG)
    runs = [c["run"] for c in diag["failure_chain_of_record"]]
    for r in FAILED_CHAIN_RUNS:
        assert r in runs, r
    assert RUN in runs


def test_diagnosis_records_zero_work_loss_and_rc_classes():
    diag = _j(DIAG)
    assert "ZERO WORK LOST" in diag["work_loss_assessment"]["statement"]
    rc67 = [c for c in diag["failure_chain_of_record"] if "rc=67" in c.get("conclusion", "")]
    rc78 = [c for c in diag["failure_chain_of_record"] if "rc=78" in c.get("conclusion", "")]
    assert len(rc78) == 1 and rc78[0]["run"] == "40023576675"
    assert len(rc67) == 5


# --- benchmark confirmation ------------------------------------------------


def test_benchmark_confirmation_verdict_legs_and_pins():
    rec = _j(BENCH_DIR / f"{RUN}.json")
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is True
    assert rec["served_bundle_sha256"] == SERVED_BUNDLE_PINS
    leg1, leg2 = rec["legs"]
    assert leg1["exit_code"] == 0 and leg1["verdict"] == "PASS_NO_REGRESSION"
    assert leg2["exit_code"] == 1 and leg2["verdict"] == "FAIL_REGRESSION"
    assert leg1["label"]["n_scored"] == 65 and leg1["label"]["n_supported"] == 5
    assert leg1["geometry"]["per_bundle_counts"] == {
        "de-kapitalverletzung": 6,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 5,
    }
    assert leg1["geometry"]["n_bundles_pass_all_11"] == 0
    assert leg1["negative_controls_all_proven"] is True
    assert leg2["negative_controls_all_proven"] is True


def test_benchmark_confirmation_identical_to_measurement_of_record():
    new = _normalised(_j(BENCH_DIR / f"{RUN}.json"))
    rec = _normalised(_j(BENCH_DIR / "v65_eval_40017649220.json"))
    assert new == rec


def test_benchmark_leg_records_exist():
    assert (BENCH_DIR / f"{RUN}_leg1_served_baseline.json").exists()
    assert (BENCH_DIR / f"{RUN}_leg2_hostile_geometry.json").exists()
    assert (
        _REPO_ROOT / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_40034814235.md"
    ).exists()


# --- shim suites -----------------------------------------------------------


def test_shim_suite_counts_match_committed_r1_records():
    for mine, r1 in (
        ("40034814235_minimal_ret_ca_pytest_shim.json", "40017649220_R1_minimal_ret_ca_pytest_shim.json"),
        ("40034814235_multiling_prov_pytest_shim.json", "40017649220_R1_multiling_prov_pytest_shim.json"),
        ("40034814235_repair_r1_suite_shim.json", "local_pytest_shim.json"),
    ):
        a, b = _j(ORCH / mine), _j(ORCH / r1)
        for key in ("verdict", "n_passed", "n_failed", "n_skipped", "n_unsupported"):
            assert a[key] == b[key], (mine, key, a[key], b[key])
    assert _j(ORCH / "40034814235_minimal_ret_ca_pytest_shim.json")["n_unsupported"] == 1
    assert _j(ORCH / "40034814235_repair_r1_suite_shim.json")["n_passed"] == 32


def test_multilingual_reuse_raw_output_pin():
    rehome = _j(_REPO_ROOT / "results/evaluation/multilingual_provenance_reuse/40017649220.json")
    assert rehome["raw_output_sha256"] == MLP_RAW_SHA
    hist = _REPO_ROOT / "results/evaluation/v3_multilingual_provenance_reuse/local_v3_multilingual_reuse.json"
    assert _sha(hist) == MLP_RAW_SHA


# --- frozen inputs ---------------------------------------------------------


def test_frozen_inputs_unchanged_at_this_head():
    for rel, want in FROZEN_PINS.items():
        assert _sha(_REPO_ROOT / rel) == want, rel


# --- state -----------------------------------------------------------------


def test_state_run_identity_and_posture():
    s = _state()
    assert s["github_run"] == RUN
    assert s["proposed_run_id"] == RUN
    assert s["direction_version"] == 65
    assert s["cycle_status"] != "INITIALIZED"
    for key in (
        "human_gate_ready",
        "machine_gate_ready",
        "packet_admitted",
        "ready_for_owner_session",
        "owner_decision_required",
    ):
        assert s[key] is False, key


def test_state_evidence_index_covers_this_run_and_rederives():
    s = _state()
    assert s["evidence_refs_n"] == len(s["evidence_refs"])
    for ref in (
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        f"results/evaluation/orchestration/{RUN}_failure_chain_diagnosis.json",
        f"results/evaluation/orchestration/{RUN}_verification_of_repair_40017649220_r1.json",
        f"results/evaluation/orchestration/{RUN}_minimal_ret_ca_pytest_shim.json",
        f"results/evaluation/orchestration/{RUN}_multiling_prov_pytest_shim.json",
        f"results/evaluation/orchestration/{RUN}_repair_r1_suite_shim.json",
        f"results/evaluation/minimal_ret_ca_benchmark/{RUN}.json",
        f"reports/evaluation/RETRIEVAL_CA_BENCHMARK_{RUN}.md",
        "reports/evaluation/OPERATIONAL_RESUME_40034814235.md",
    ):
        assert ref in s["evidence_refs"], ref
        assert (_REPO_ROOT / ref).exists(), ref


def test_state_repair_discharge_pointers_and_benchmark_confirmation():
    s = _state()
    r1 = s["repair_round1_40017649220"]
    assert r1["discharge_verified_by_run"] == RUN
    assert r1["discharge_verification_verdict"] == "VERIFIED_UNDER_INDEPENDENT_REEXECUTION"
    b = s["minimal_ret_ca_benchmark"]
    assert b["run_id"] == "v65_eval_40017649220"  # measurement of record untouched
    assert b["latest_confirmation_run"] == RUN
    assert b["latest_confirmation_verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert s["benchmark_result"]["accepted_run_of_record"] == "39927760701"


def test_state_operational_resume_block_and_verification_record_consistent():
    s = _state()
    blk = s[f"operational_resume_{RUN}"]
    assert blk["verdict"] == "REPAIR_DISCHARGE_VERIFIED_SNAPSHOT_AUDIT_READY"
    assert blk["work_loss"].startswith("ZERO")
    assert len(blk["resume_chain"]) == 8
    verif = _j(VERIF)
    assert verif["run_id"] == RUN
    assert "REPAIR DISCHARGE VERIFIED" in verif["overall_verdict"]
    assert verif["E4_frozen_input_integrity_after"]["verdict"] == "ALL IDENTICAL"


def test_state_defect_detail_correction_applied_and_ref_list_unchanged():
    s = _state()
    defects = s["evidence_index_defects_inherited_not_charged"]["defects"]
    dup = [d for d in defects if d.get("kinds") == ["DUPLICATE_ONLY"]]
    assert len(dup) == 1
    assert "DOES resolve" in dup[0]["detail"]
    assert dup[0]["detail_corrected_by_run"] == RUN
    # ref list itself must still contain the duplicated ref twice
    assert s["evidence_refs"].count("results/evaluation/orchestration/39875239812_diagnosis.json") == 2
