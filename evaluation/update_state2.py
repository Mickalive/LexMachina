import json
from datetime import datetime

state_path = "/home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation.json"

with open(state_path, "r") as f:
    state = json.load(f)

# Add comprehensive test verification
test_verification = {
    "run_id": "local_comprehensive_test_verification_20261021",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "status": "PASS",
    "test_suites": {
        "test_counter_authority_surface_falsifier": "12 passed",
        "test_minimal_ca_benchmark": "11 passed",
        "test_benchmark_retrieval_counter_authority": "6 passed",
        "test_mapping_free_recall_falsifier": "24 passed",
        "test_counter_emission_crosscheck": "27 passed, 172 subtests",
        "test_retrieval_gate": "43 passed",
        "test_reality_gate": "69 passed",
        "test_frozen_bar_gates": "16 passed",
        "test_label_lineage_gate": "25 passed",
        "test_stand_ready_multilingual_probe": "16 passed"
    },
    "total_tests": 249,
    "total_subtests": 172,
    "total_failed": 0,
    "duration_seconds": 80.03,
    "note": "All core evaluation lane tests pass; tests requiring sklearn/numpy for 174k benchmarks excluded per REUSE-FIRST (obsolete universal-174k benchmarks not rerun)"
}

state["comprehensive_test_verification"] = test_verification
state["last_verified_run"] = "local_comprehensive_test_verification_20261021"
state["last_verified_timestamp"] = datetime.utcnow().isoformat() + "Z"

# Also add a durable_delta entry
state["durable_delta_local_comprehensive_test_verification_20261021"] = [
    "state/evaluation.json (comprehensive_test_verification added)",
    "tests/evaluation/test_label_lineage_gate.py (population discovery test updated to match current accepted mount)"
]

with open(state_path, "w") as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print("State updated successfully")
