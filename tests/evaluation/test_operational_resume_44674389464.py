"""Regression guards for operational resume run 44674389464.

These pin the durable facts this cycle establishes: the two-failure diagnosis,
the preserved stale-record defect, the byte-identical relocation, the v68
ordered-work carry-forward, and the state claim-path repair.  Stdlib unittest so
they run even where pytest is absent; pytest discovers the same classes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = 44674389464
PRIOR = 44665691117
OUT = ROOT / "results" / "evaluation" / f"operational_resume_{RUN}"
PRIOR_OUT = ROOT / "results" / "evaluation" / f"operational_resume_{PRIOR}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path) -> dict:
    return json.loads(p.read_text())


class OperationalResume44674389464(unittest.TestCase):
    def test_frozen_pins_match_their_files(self):
        frz = load(ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V2.json")
        amd = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1_1_AMENDMENT.json"
        self.assertEqual(sha(ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"),
                         frz["hypothesis"]["sha256"])
        self.assertEqual(sha(ROOT / "evaluation/operational_resume_44674389464.py"),
                         frz["instrument"]["sha256"])
        self.assertEqual(sha(amd), frz["amendment"]["sha256"])
        self.assertEqual(sha(OUT / "github_run_status_capture.json"),
                         frz["evidence_inputs"]["capture_sha256"])
        self.assertEqual(load(amd)["instrument_sha256_corrected"], frz["instrument"]["sha256"])

    def test_v1_freeze_and_amendment_are_preserved(self):
        v1 = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
        self.assertTrue(v1.exists())
        self.assertEqual(load(v1)["run_id"], RUN)
        self.assertEqual(load(v1)["instrument"]["sha256"],
                         "da980d7345a9d0e5ee0a04bb1d2036c6ba1d3432329cdc9178ab6a95dd30189f")

    def test_full_phase_verdict_and_rules(self):
        rec = load(OUT / f"{RUN}.json")
        self.assertEqual(rec["verdict"], "ORCHESTRATION_DIAGNOSIS_CONFIRMED")
        self.assertEqual(rec["exit_code"], 0)
        self.assertTrue(all(rec["rule_pass"].values()))
        self.assertEqual(rec["accepted_run_id"], 40265377500)
        self.assertEqual(rec["audit_status"], "PENDING_INDEPENDENT_AUDIT")

    def test_accepted_head_both_halves(self):
        gate = ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json"
        g = load(gate)
        self.assertEqual((g["gate"], g["safe_to_integrate"], g["required_fixes"]),
                         ("PASS", True, []))
        r = subprocess.run(
            ["git", "log", "origin/lab/evaluation", "--oneline",
             "--grep", "accept evaluation cycle 40265377500"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("accept evaluation cycle 40265377500", r.stdout)

    def test_failure_captures_exact(self):
        ann = load(PRIOR_OUT / "run_44665054809_annotation_evidence.json")
        self.assertEqual(ann["failing_step"]["number"], 9)
        self.assertEqual(ann["failing_step"]["annotation"], "Process completed with exit code 3.")
        self.assertEqual(ann["offending_paths"], [
            "reports/audit/evaluation/CYCLE_40261335674.md",
            "results/audit/evaluation/CYCLE_40261335674_GATE.json"])
        cap = load(OUT / "github_run_status_capture.json")
        self.assertEqual(cap["runs"]["44665691117"]["classification"],
                         "AUDIT_JOB_DEATH_NOT_A_VERDICT")
        self.assertFalse(cap["runs"]["44665691117"]["audit_gate_written"])

    def test_prior_stale_record_preserved(self):
        prior = load(PRIOR_OUT / f"{PRIOR}.json")
        self.assertEqual(prior["verdict"], "DIAGNOSIS_NOT_CONFIRMED")
        self.assertEqual(prior["generated_at_utc"], "2026-11-20T03:25:42Z")
        cur = sha(ROOT / f"evaluation/operational_resume_{PRIOR}.py")
        self.assertNotEqual(cur, "6e9229b9691c16c1ed8fb27c5bef7f81eee04f6bc2f151496e90dd969a8dfdee")

    def test_relocation_byte_identity(self):
        pairs = [
            ("reports/audit/evaluation/CYCLE_40261335674.md",
             "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674.md"),
            ("results/audit/evaluation/CYCLE_40261335674_GATE.json",
             "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674_GATE.json"),
        ]
        for src, dst in pairs:
            self.assertTrue((ROOT / src).is_file())
            self.assertEqual(sha(ROOT / src), sha(ROOT / dst))

    def test_state_claim_path_repaired(self):
        st = load(ROOT / "state/evaluation.json")
        lane = load(ROOT / "evaluation/state/evaluation.json")
        self.assertEqual(st["github_run"], RUN)
        self.assertEqual(st["proposed_run_id"], RUN)
        self.assertEqual(lane["github_run"], RUN)
        self.assertEqual(lane["proposed_run_id"], RUN)
        self.assertEqual(st["accepted_run_id"], 40265377500)
        self.assertEqual(lane["accepted_run_id"], 40265377500)
        self.assertEqual(st["evidence_refs_n"], len(st["evidence_refs"]))
        for bad in ("results/audit/evaluation/CYCLE_40261335674_GATE.json",
                    "reports/audit/evaluation/CYCLE_40261335674.md"):
            self.assertNotIn(bad, st["evidence_refs"])
        for good in ("results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674_GATE.json",
                     "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674.md"):
            self.assertIn(good, st["evidence_refs"])
        block = st["operational_resume_44674389464"]
        self.assertEqual(block["claim_bearing_run"], RUN)
        self.assertEqual(block["audit_status"], "PENDING_INDEPENDENT_AUDIT")
        self.assertFalse(block["accepted_as_evidence"])

    def test_ordered_work_pointers(self):
        rec = load(OUT / f"{RUN}.json")
        ow = rec["ordered_work_status"]
        self.assertTrue(ow["1"].startswith("DISCHARGED_ELSEWHERE"))
        self.assertTrue(ow["2"].startswith("NOT_YET_DISCRIMINATING"))
        self.assertTrue(ow["3"].startswith("KEPT"))
        self.assertTrue(ow["4"].startswith("REPORTED_ONLY"))
        self.assertTrue(ow["5"].startswith("HONOURED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
