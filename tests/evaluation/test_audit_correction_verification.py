#!/usr/bin/env python3
"""Lane-state consistency verification (current direction v55).

HISTORY: this file originally verified the v35-era lane state (TF-IDF 174k
freeze, dense criteria blockers).  That question is COMPLETE; its state was
superseded by accepted cycles e0d8e12e (v45 freeze confirmation) and
fd38704/v56 (frontier verdict adoption), and the file was never updated.  The
v35 claims remain preserved in git history and results/; they are NOT active
lane state and are not re-asserted here.

It now verifies the mandatory accepted-state fields required by
docs/RESEARCH_PROTOCOL.md against the CURRENT state/evaluation.json, and that
the active reality-benchmark assets exist and are non-empty.

REPAIR 38966576940 (audit R1): the direction pin was bumped 49 -> 50 to match
the v50 lane state; the prior pin made the full active pytest set red
(1 failed / 119 passed / 1 skipped) and falsely contradicted the state file.

REPAIR 39027041693 (in-cycle, same pattern): the direction pin was bumped
50 -> 52 to match the v52 lane state; the stale pin made the full active pytest
set red at 1 failed / 236 passed and falsified the '237 passed' claim. No
frozen benchmark, rubric, incumbent, threshold or success rule is touched by a
direction pin repair; the state file's direction_version (52) is authoritative.

REPAIR 39076123103 (audit results/audit/evaluation/CYCLE_39064597912_GATE.json
R1): the direction pin was bumped 52 -> 55 to match the v55 lane state. The
stale pin made the lane's own pytest scope red (test_audit_correction_
verification.py::test_state_file_has_mandatory_fields asserted 55 == 52) and
the 39064597912 audit returned gate=REVISE safe_to_integrate=false until the
pin was advanced. Same disclosed convention as the 49->50 and 50->52 repairs;
the state file's direction_version (55) is authoritative. No frozen benchmark,
rubric, incumbent, threshold or success rule is touched.
"""
import json
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def test_state_file_has_mandatory_fields():
    state = load_json("state/evaluation.json")
    for field in ("lane", "direction_version", "evidence_tier", "cycle_status",
                   "continue_recommended", "accepted_run_id", "evidence_refs",
                   "next_recommendation"):
        assert field in state, f"missing mandatory field {field}"
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 55


def test_evidence_refs_exist():
    state = load_json("state/evaluation.json")
    for ref in state["evidence_refs"]:
        assert Path(ref).is_file(), f"evidence ref missing: {ref}"


def test_reality_benchmark_assets_exist():
    for path in (
        "evaluation/reality_gate/frozen_benchmark.json",
        "evaluation/reality_gate/frozen.py",
        "evaluation/reality_gate/gates.py",
        "evaluation/reality_gate/run_benchmark.py",
        "tests/evaluation/test_reality_gate.py",
        "results/evaluation/reality_benchmark/38920872324.json",
    ):
        p = Path(path)
        assert p.is_file() and p.stat().st_size > 0, f"missing benchmark asset: {path}"


def test_frozen_benchmark_tests_pass():
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/evaluation/test_reality_gate.py", "-q",
         "--tb=short"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"reality benchmark tests FAILED:\n{result.stdout}\n{result.stderr}"
