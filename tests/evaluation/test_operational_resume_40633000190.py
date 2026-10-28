"""Regression guards for the 40633000190 operational-resume records."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/evaluation/operational_resume_40633000190"
RUN = "40633000190"
RESUMED = "40633000190"
SNAPSHOT = "5552f23630a0fa94d584156557660802cb6becae"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"


def _load(rel: str):
    path = ROOT / rel
    if not path.is_file():
        raise unittest.SkipTest(f"resume record not generated yet: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class DiagnosisTest(unittest.TestCase):
    def test_failure_is_orchestration_not_model_health(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/diagnosis_{RESUMED}.json")
        self.assertIn(rec["verdict"], ["DIAGNOSIS_CONFIRMED", "DIAGNOSIS_INCOMPLETE"])
        self.assertEqual(rec["failure_class"], "ORCHESTRATION_PROVIDER_OR_SESSION_EXIT_AT_LANE_CYCLE")
        self.assertTrue(any("INFERENCE" in c["status"] for c in rec["candidate_causes"]))

    def test_no_audit_ref_was_issued_and_no_verdict_claimed(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/diagnosis_{RESUMED}.json")
        self.assertEqual(rec["snapshot_refs"]["team"], rec["snapshot_refs"]["persisted_snapshot_commit"])


class SnapshotTest(unittest.TestCase):
    def test_snapshot_is_preserved(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/snapshot_identity.json")
        self.assertEqual(rec["verdict"], "SNAPSHOT_PRESERVED_ON_PRIOR_PRODUCER_COMMIT")
        self.assertEqual(rec["persisted_snapshot_commit"], SNAPSHOT)


class DeliverableTest(unittest.TestCase):
    def test_item1_is_present_and_not_reopened(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/deliverable_verification.json")
        item = rec["item_1"]
        self.assertTrue(item["not_reopened"])
        self.assertIs(item["measurement_unchanged"], True)
        self.assertIs(item["falsifier_reexecuted"], False)
        self.assertEqual(sorted(item["failed_claims"]), ["CC6_accepted_code_path_file_line", "CC7_51d306c_diff_provenance"])

    def test_item2_is_still_gated(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/item2_precondition_{RUN}.json")
        matching = rec["member_for_member_matching"]
        self.assertEqual(matching["matched_members"], 14)
        self.assertEqual(matching["of"], 15)
        self.assertIs(rec["H2_precondition_full_family_regenerated"], False)


class ReadinessTest(unittest.TestCase):
    def test_record_is_honestly_not_ready_with_one_known_failure(self):
        rec = _load(f"results/evaluation/snapshot_audit/{RUN}.json")
        self.assertEqual(rec["schema"], "lex-evaluation-snapshot-audit/1")
        self.assertEqual(rec["n_checks"], 21)
        self.assertEqual(rec["n_passed"], 20)
        self.assertIs(rec["ready_for_independent_audit"], False)
        self.assertEqual(rec["failing_checks"], ["packet_admission_conformance_reexecution"])

    def test_state_and_report_repeat_the_record_counts(self):
        rec = _load(f"results/evaluation/snapshot_audit/{RUN}.json")
        state = _load("state/evaluation.json")
        block = state.get(f"snapshot_audit_{RUN}")
        self.assertIsNotNone(block)
        self.assertEqual(block["n_checks"], rec["n_checks"])
        self.assertEqual(block["n_passed"], rec["n_passed"])
        self.assertIs(block["ready_for_independent_audit"], rec["ready_for_independent_audit"])
        self.assertEqual(state["accepted_run_id"], 40258497460)
        self.assertIs(state["continue_recommended"], False)
        report = (ROOT / f"reports/evaluation/CYCLE_{RUN}.md").read_text(encoding="utf-8")
        self.assertIn("NOT READY (20/21 checks PASS)", report)
        self.assertIn("post-write self-reference: VERIFIED", report)

    def test_no_audit_namespace_file_is_written(self):
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0)
        bad = [line[3:].strip() for line in proc.stdout.splitlines()
               if line[3:].strip().startswith(("results/audit/", "reports/audit/"))]
        self.assertEqual(bad, [], f"producer wrote the auditor namespace: {bad}")


if __name__ == "__main__":
    unittest.main()
