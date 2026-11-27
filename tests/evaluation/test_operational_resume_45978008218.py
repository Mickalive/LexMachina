#!/usr/bin/env python3
"""Executable acceptance test for operational-resume snapshot 45978008218.

Uses only the standard library so it runs in the producer image (pytest is not
installed).  Run with:

    python3 -m unittest tests.evaluation.test_operational_resume_45978008218 -v
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = 45978008218
RESUMED = 45977830089
BASE = "9aea0dbeb6ce26bcaccd17e818a9efb6c404fbdf"
DIR = REPO / "results" / "evaluation" / f"operational_resume_{RUN}"


def jload(rel: str):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OperationalResumeSnapshot(unittest.TestCase):
    def test_freeze_precedes_execution(self):
        freeze = jload(f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
        self.assertTrue(freeze["frozen_before_claim_bearing_execution"])
        self.assertEqual(freeze["run_id"], RUN)
        self.assertEqual(freeze["resumed_from_run"], RESUMED)
        self.assertEqual(freeze["control_plane"]["direction_version"], 68)
        self.assertEqual(freeze["packet_of_record"], "39319405429")
        hyp = REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"
        self.assertEqual(sha(hyp), freeze["hypothesis_sha256"])

    def test_snapshot_is_preserved_not_restarted(self):
        cap = jload(f"results/evaluation/operational_resume_{RUN}/public_run_capture_{RESUMED}.json")
        g = cap["git_facts"]
        self.assertEqual(g["snapshot_head"], BASE)
        self.assertEqual(g["commits_ahead_of_inherited_base"], "0")
        self.assertFalse(g["gate_present_in_worktree"])
        self.assertFalse(g["gate_present_in_any_ref"])
        self.assertFalse(g["audit_ref_present"])

    def test_diagnosis_is_producer_step_death_not_a_verdict(self):
        d = jload(f"results/evaluation/operational_resume_{RUN}/diagnosis_{RESUMED}.json")
        self.assertEqual(d["failure_class"], "PRODUCER_STEP_ORCHESTRATION_DEATH")
        self.assertEqual(d["observed"]["failing_step"], "Run lane cycle")
        self.assertFalse(d["gate_artifact"]["verdict_issued"])
        self.assertTrue(d["persisted_snapshot"]["zero_new_commits"])
        self.assertFalse(d["quantum_arithmetic"]["producer_step_is_quantum_death"])

    def test_deliverable_verification_all_checks_pass(self):
        v = jload(f"results/evaluation/operational_resume_{RUN}/deliverable_verification_{RUN}.json")
        self.assertEqual(v["verdict"], "DELIVERABLE_VERIFIED")
        self.assertEqual(v["n_passed"], v["n_checks"])
        self.assertGreaterEqual(v["n_checks"], 26)
        self.assertEqual([c["check"] for c in v["checks"] if c["verdict"] == "FAIL"], [])

    def test_replay_reproduces_and_pins_match(self):
        c = jload(f"results/evaluation/operational_resume_{RUN}/replay_comparison_{RUN}.json")
        p = jload(f"results/evaluation/operational_resume_{RUN}/pin_rehash_{RUN}.json")
        self.assertEqual(c["verdict"], "REPLAY_REPRODUCES")
        self.assertEqual(c["n_differences"], 0)
        self.assertEqual(p["verdict"], "PINS_ALL_MATCH")
        self.assertEqual(p["n_match"], p["n_pins"])

    def test_v68_conditional_remeasure_not_executed(self):
        g = jload(f"results/evaluation/operational_resume_{RUN}/v68_conditional_gate_status_{RUN}.json")
        self.assertFalse(g["conditional_remeasure_performed"])
        self.assertEqual(g["status"], "OUT_OF_SCOPE_FOR_OPERATIONAL_RESUME")
        self.assertEqual(g["served_packet_measurement_stands"]["verdict"], "PRODUCT_FALSIFIED")

    def test_state_parity_and_additivity(self):
        root = jload("state/evaluation.json")
        lane = jload("evaluation/state/evaluation.json")
        for d in (root, lane):
            self.assertEqual(d["direction_version"], 68)
            self.assertEqual(d["accepted_run_id"], 40265377500)
            self.assertEqual(d["github_run"], RUN)
            self.assertEqual(d["evidence_refs_n"], len(d["evidence_refs"]))
            self.assertTrue(d[f"prior_next_recommendation_{RUN}"].startswith(
                "CURRENT RUN 45973119386"))
            self.assertFalse(d[f"operational_resume_{RUN}"]["pending_independent_audit"] is False)
        proof = jload(f"results/evaluation/operational_resume_{RUN}/state_additive_proof_{RUN}.json")
        for p in proof.values():
            self.assertEqual(p["verdict"], "ADDITIVE_ONLY")
            self.assertEqual(p["removed_evidence_refs"], [])

    def test_guides_and_scope_clean(self):
        guards = jload(f"results/evaluation/operational_resume_{RUN}/guard_results_{RUN}.json")
        self.assertTrue(all(g["returncode"] == 0 for g in guards.values()))
        self.assertEqual(guards["state_integrity"]["stdout"]["verdict"], "ALL_CHECKS_PASS")
        self.assertEqual(guards["nested_refs"]["stdout"]["verdict"], "NESTED_REFS_RESOLVED")
        scope = jload(f"results/evaluation/operational_resume_{RUN}/no_out_of_lane_proof_{RUN}.json")
        self.assertEqual(scope["verdict"], "IN_LANE_ONLY")
        self.assertEqual(scope["out_of_lane_entries"], [])
        self.assertEqual(scope["frozen_artifact_writes"], [])
        self.assertEqual(scope["audit_gate_files_created"], [])

    def test_audit_index_hashes_match(self):
        idx = jload(f"results/evaluation/operational_resume_{RUN}/AUDIT_INDEX_{RUN}.json")
        self.assertEqual(idx["verdict"], "AUDIT_READY_PENDING_INDEPENDENT_AUDIT")
        self.assertEqual(idx["missing"], [])
        mismatches = []
        for entry in idx["artifacts"]:
            p = REPO / entry["path"]
            if not p.is_file() or sha(p) != entry["sha256"]:
                mismatches.append(entry["path"])
        self.assertEqual(mismatches, [])

    def test_no_audit_gate_created_by_this_run(self):
        for name in (f"CYCLE_{RUN}_GATE.json", f"CYCLE_{RESUMED}_GATE.json"):
            self.assertFalse((REPO / "results/audit/evaluation" / name).exists())
        out = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(REPO), capture_output=True,
            text=True, check=False).stdout.splitlines()
        bad = [line[3:] for line in out if len(line) > 3 and not line[3:].startswith((
            "evaluation/", "tests/evaluation/", "results/evaluation/",
            "reports/evaluation/", "state/evaluation.json"))]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
