"""Regression guards for the 40618327881 operational-resume records.

The 40618327881 cycle resumes the persisted snapshot of failed run 40618193656.
These tests do not execute the instrument or the benchmark; they pin the
committed records: the orchestration diagnosis, the snapshot identity, the
ordered-item status, the append-only coverage-record restoration, the readiness
record and the additive state.

They are plain ``unittest`` cases (pytest collects them too), so they run in a
checkout without pytest installed. Each test skips cleanly before the records
exist.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/evaluation/operational_resume_40618327881"
RUN = "40618327881"
RESUMED = "40618193656"
SNAPSHOT = "344da4c98255fd030c61298e8e98a06794056054"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"


def _load(rel: str):
    path = ROOT / rel
    if not path.is_file():
        raise unittest.SkipTest(f"resume record not generated yet: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class DiagnosisTest(unittest.TestCase):
    def test_failure_is_orchestration_not_model_health(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/diagnosis_{RESUMED}.json")
        self.assertEqual(rec["verdict"], "DIAGNOSIS_CONFIRMED")
        self.assertEqual(rec["n_failed"], 0)
        self.assertEqual(
            rec["failure_class"],
            "ORCHESTRATION_PROVIDER_OR_SESSION_EXIT_AT_LANE_CYCLE",
        )
        self.assertLess(rec["step_durations_seconds"]["run_lane_cycle"], 120.0)
        head = rec["model_health"]["run_head"]
        self.assertEqual(head["resolver_exit_code"], 0)
        self.assertIs(head["healthy"], True)
        self.assertTrue(head["resolved_model"])
        # The un-loggable cause must stay an inference, never a fact.
        self.assertTrue(any("INFERENCE" in c["status"] for c in rec["candidate_causes"]))
        self.assertTrue(any("HTTP 403" in lim for lim in rec["limits"]))

    def test_no_audit_ref_was_issued_and_no_verdict_claimed(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/diagnosis_{RESUMED}.json")
        checks = {c["check"]: c for c in rec["checks"]}
        self.assertIs(checks["no_audit_ref_was_issued"]["detail"]["exists"], False)
        self.assertEqual(rec["snapshot_refs"]["team"], SNAPSHOT)
        self.assertEqual(rec["snapshot_refs"]["team_attempt_1"], SNAPSHOT)


class SnapshotTest(unittest.TestCase):
    def test_snapshot_is_the_prior_producer_commit(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/snapshot_identity.json")
        self.assertEqual(rec["verdict"], "SNAPSHOT_PRESERVED_ON_PRIOR_PRODUCER_COMMIT")
        self.assertEqual(rec["persisted_snapshot_commit"], SNAPSHOT)
        self.assertIn("evaluation cycle 40611594771", rec["persisted_snapshot_subject"])
        self.assertEqual(rec["persisted_snapshot_authoring_run"], "40611594771")
        self.assertGreater(len(rec["changed_files"]), 0)

    def test_snapshot_preserves_the_accepted_base(self):
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACCEPTED_BASE, SNAPSHOT],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


class DeliverableTest(unittest.TestCase):
    def test_item1_is_present_and_not_reopened(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/deliverable_verification.json")
        item = rec["item_1"]
        self.assertTrue(item["not_reopened"])
        self.assertIs(item["measurement_unchanged"], True)
        self.assertIs(item["falsifier_reexecuted"], False)
        self.assertEqual(sorted(item["failed_claims"]), [
            "CC6_accepted_code_path_file_line",
            "CC7_51d306c_diff_provenance",
        ])
        self.assertTrue((ROOT / item["record"]).is_file())
        self.assertTrue((ROOT / item["report"]).is_file())

    def test_item2_is_still_gated_at_14_of_15(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/item2_precondition_{RUN}.json")
        matching = rec["member_for_member_matching"]
        self.assertEqual(rec["product_mount_head"], "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83")
        self.assertEqual(matching["matched_members"], 14)
        self.assertEqual(matching["of"], 15)
        self.assertEqual(matching["matched_per_role"]["server/served"], 3)
        self.assertIs(rec["H2_precondition_full_family_regenerated"], False)
        self.assertTrue(str(rec["status"]).startswith("NOT_YET_DISCRIMINATING"))

    def test_structural_accept_is_not_evidence(self):
        rec = _load(f"results/evaluation/operational_resume_{RUN}/deliverable_verification.json")
        lin = rec["accepted_lineage"]
        self.assertEqual(lin["accepted_run_id_unchanged"], "40258497460")
        self.assertIs(lin["structural_accept_accepted_as_evidence"], False)
        self.assertIs(lin["structural_accept_mismatch"], True)


class CoverageRestorationTest(unittest.TestCase):
    def load(self):
        return _load("results/evaluation/accepted_base_gate_coverage_39043684319.json")

    def test_prior_history_and_truncated_bytes_are_preserved(self):
        rec = self.load()
        self.assertIn("restoration_40618327881", rec)
        self.assertIn("superseded_snapshot_40611594771_truncated", rec)
        self.assertGreaterEqual(len(rec["history"]), 3)
        prior = subprocess.run(
            ["git", "show",
             f"{SNAPSHOT}^:results/evaluation/accepted_base_gate_coverage_39043684319.json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(prior.returncode, 0, prior.stderr)
        prior_obj = json.loads(prior.stdout)
        # Every prior top-level key survives the restoration.
        self.assertEqual([k for k in prior_obj if k not in rec], [])
        # The prior history is a prefix of the restored history.
        self.assertEqual(rec["history"][:len(prior_obj["history"])], prior_obj["history"])
        # The prior 34-gate inventory is preserved beside the current one.
        self.assertEqual(
            rec["gates_present_on_accepted_branch_at_3506f0e4"],
            prior_obj["gates_present_on_accepted_branch"],
        )
        # The truncated 40611594771 bytes are kept verbatim.
        self.assertEqual(
            rec["superseded_snapshot_40611594771_truncated"]["accepted_branch_head"],
            ACCEPTED_BASE,
        )

    def test_current_head_and_ungated_set_match_git(self):
        rec = self.load()
        head = subprocess.run(
            ["git", "rev-parse", "origin/lab/evaluation"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        self.assertEqual(rec["accepted_branch_head"], head)
        self.assertEqual(rec["ungated_runs_above_the_newest_accept_commit"], [])
        self.assertGreater(len(rec["gates_present_on_accepted_branch"]), 0)


class ReadinessTest(unittest.TestCase):
    def test_record_is_honestly_not_ready_with_one_known_failure(self):
        rec = _load(f"results/evaluation/snapshot_audit/{RUN}.json")
        self.assertEqual(rec["schema"], "lex-evaluation-snapshot-audit/1")
        self.assertEqual(rec["n_checks"], 21)
        self.assertEqual(rec["n_passed"], 20)
        self.assertIs(rec["ready_for_independent_audit"], False)
        self.assertEqual(
            rec["failing_checks"], ["packet_admission_conformance_reexecution"]
        )
        pac = next(c for c in rec["checks"]
                   if c["id"] == "packet_admission_conformance_reexecution")
        self.assertEqual(pac["status"], "FAIL")
        self.assertEqual(len(pac["violation_files"]), 2)

    def test_state_and_report_repeat_the_record_counts(self):
        rec = _load(f"results/evaluation/snapshot_audit/{RUN}.json")
        state = _load("state/evaluation.json")
        block = state[f"snapshot_audit_{RUN}"]
        self.assertEqual(block["n_checks"], rec["n_checks"])
        self.assertEqual(block["n_passed"], rec["n_passed"])
        self.assertIs(block["ready_for_independent_audit"],
                      rec["ready_for_independent_audit"])
        self.assertEqual(state["accepted_run_id"], 40258497460)
        self.assertEqual(state["github_run"], int(RUN))
        self.assertIs(state["continue_recommended"], False)
        report = (ROOT / f"reports/evaluation/CYCLE_{RUN}.md").read_text(encoding="utf-8")
        self.assertIn("NOT READY (20/21 checks PASS)", report)
        self.assertIn("post-write self-reference: VERIFIED", report)
        self.assertIn("post-write state claim: VERIFIED", report)

    def test_evidence_refs_resolve(self):
        state = _load("state/evaluation.json")
        self.assertEqual(state["evidence_refs_n"], len(state["evidence_refs"]))
        missing = [r for r in state["evidence_refs"]
                   if not (ROOT / (r.split()[0] if r.split() else r)).exists()]
        self.assertEqual(missing, [])

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
