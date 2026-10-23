"""Operational-resume verification tests (run 39990225759, charter v1).

These tests are additive to ``test_span_select.py`` and exist so that an
independent auditor can machine-check, without any network or product mount,
that:

1. the frozen protocol is still content-addressed (``PROTOCOL.sha256`` matches
   a fresh hash, and every result artifact embeds the same digest);
2. the operational failure diagnosed in ``PROVENANCE_RESUME.json`` - the
   producer's dangling ``dad93c36`` freeze-commit citation - is recorded rather
   than silently rewritten, and the corrected content-addressed witness is
   present;
3. the resume re-execution reproduced every claim-bearing result artifact, and
   no result artifact was overwritten by the resume;
4. the integration contract still forbids exactly the product-owned fields it
   forbade before the resume (the resume must not widen the component's reach).

None of these tests writes a repository file.
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS = REPO_ROOT / "results" / "frontier" / "frontier-counter-evidence-span-selection"
REPORTS = REPO_ROOT / "reports" / "frontier" / "frontier-counter-evidence-span-selection"

#: sha256 of each claim-bearing artifact as published by producer run 39986101767.
#: The resume cycle must leave these byte-for-byte untouched.
PRODUCER_ARTIFACT_SHA256 = {
    "PROTOCOL.json": "b5d14121e86ea0b39c181aacef1c30d4a2788a4751af4cfa00c33189c0afb7ea",
    "BASELINE.json": "8d8664dc6d1e58af1abcf43deda6f69542cec2685e45628a9d2ea193bd03c965",
    "CANDIDATE.json": "05d270af97ddf5fafb3cab1ac4d25a0e9ba881182390a3bbbb643485b39d76d3",
    "CONTROLS.json": "811c2fb8d9459d62e361f32e68aeae593a07eac9e92ceb4b0529b93464e9f84b",
    "DETERMINISM.json": "65aa0b17c9e92d956c447cfd57c4589bc1919988fed58abb55e684db209dc780",
    "MEASUREMENT.json": "e60a5af60a513b9ee613b6ec611cbefd696b26aa36617e5655979f4907bc9194",
    "SERVED_PACKET_SECONDARY.json": "fa1cf1258f4b8bc4d66f43ddd4ce21f69b91c41967650be0b12d88b30a80e922",
    "SEMANTIC_AUDIT.json": "9b543b91629aa86146f85cb7b147ce7a92830bf037143c60b7a2025941402601",
}

DANGLING_COMMIT = "dad93c36"
RESUME_RUN_ID = "39990225759"
PRODUCER_RUN_ID = "39986101767"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


class FrozenProtocolIntegrityTests(unittest.TestCase):
    """The freeze must be content-addressed and untouched by the resume."""

    def test_protocol_sha256_file_matches_payload(self) -> None:
        recorded = (RESULTS / "PROTOCOL.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(recorded, _sha256(RESULTS / "PROTOCOL.json"))

    def test_protocol_declares_frozen_before_measurement(self) -> None:
        protocol = _load("PROTOCOL.json")
        self.assertEqual(protocol["status"], "FROZEN_BEFORE_MEASUREMENT")
        self.assertEqual(protocol["github_run"], PRODUCER_RUN_ID)
        self.assertIn("frozen_at", protocol)

    def test_success_rule_lives_inside_frozen_payload(self) -> None:
        protocol = _load("PROTOCOL.json")
        self.assertIn("success_rule", protocol)
        self.assertIn("claim_ceiling", protocol["success_rule"])
        self.assertIn("abstain_condition", protocol)
        self.assertIn("span_rule", protocol)

    def test_every_result_artifact_embeds_the_protocol_digest(self) -> None:
        digest = PRODUCER_ARTIFACT_SHA256["PROTOCOL.json"]
        for name in PRODUCER_ARTIFACT_SHA256:
            if name == "PROTOCOL.json":
                # the protocol cannot embed its own digest; PROTOCOL.sha256 covers it
                continue
            with self.subTest(artifact=name):
                self.assertEqual(_load(name)["protocol_sha256"], digest)


class ProducerArtifactImmutabilityTests(unittest.TestCase):
    """The resume cycle may append records; it may never rewrite results."""

    def test_producer_artifacts_byte_identical(self) -> None:
        for name, expected in PRODUCER_ARTIFACT_SHA256.items():
            with self.subTest(artifact=name):
                self.assertEqual(_sha256(RESULTS / name), expected)


class ProvenanceResumeRecordTests(unittest.TestCase):
    """The operational failure must be diagnosed and recorded, not erased."""

    def setUp(self) -> None:
        self.prov = _load("PROVENANCE_RESUME.json")

    def test_record_identity(self) -> None:
        self.assertEqual(self.prov["team_id"], "frontier-counter-evidence-span-selection")
        self.assertEqual(self.prov["charter_version"], 1)
        self.assertEqual(self.prov["resume_run_id"], RESUME_RUN_ID)
        self.assertEqual(self.prov["resumed_producer_run_id"], PRODUCER_RUN_ID)

    def test_failure_is_named_and_content_addressed(self) -> None:
        failure = self.prov["operational_failure"]
        self.assertEqual(failure["diagnosis"], "DANGLING_FREEZE_COMMIT_CITATION")
        witness = self.prov["freeze_witness_content_addressed"]
        self.assertEqual(witness["protocol_sha256"], PRODUCER_ARTIFACT_SHA256["PROTOCOL.json"])
        self.assertTrue(witness["success_rule_inside_frozen_payload"])
        self.assertTrue(witness["claim_ceiling_inside_frozen_payload"])

    def test_chain_of_custody_matches_disk(self) -> None:
        for entry in self.prov["freeze_witness_content_addressed"]["chain_of_custody"]:
            with self.subTest(artifact=entry["artifact"]):
                self.assertEqual(
                    _sha256(RESULTS / entry["artifact"]), entry["sha256"]
                )

    def test_verbatim_probe_record_is_seven_of_seven(self) -> None:
        probes = self.prov["resume_verification"]["independent_adversarial_probes"]
        self.assertIn("7/7", probes["c1_verbatim_offsets"])
        self.assertIn("0 failures", probes["c1_verbatim_offsets"])
        for key in (
            "c2_mutation",
            "c2_truncation",
            "c2_cross_decision",
            "c2_shifted_offsets",
            "c2_empty",
        ):
            self.assertIn("7/7", probes[key])

    def test_dangling_commit_is_recorded_not_rewritten(self) -> None:
        """The historical report keeps the broken citation; the fix is additive."""
        report = (REPORTS / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn(DANGLING_COMMIT, report)
        self.assertIn("Appendix R1", report)
        self.assertIn("Not a valid object name", report)
        self.assertIn(DANGLING_COMMIT, self.prov["operational_failure"]["detail"])

    def test_outcome_unchanged_by_resume(self) -> None:
        outcome = self.prov["outcome_unchanged"]
        self.assertFalse(outcome["continue_recommended"])
        self.assertEqual(outcome["product_recommendation"], "DO_NOT_ADOPT_AS_IS")
        self.assertEqual(outcome["team_verdict"], "COMPLETE_OUTCOME_A_MECHANICAL_ONLY")


class IntegrationContractScopeTests(unittest.TestCase):
    """The resume may not widen what Core Product is told the component does."""

    FORBIDDEN = {
        "counter_status",
        "n_scored",
        "n_abstained",
        "n_emitted",
        "packet_admitted",
        "machine_gate_ready",
        "human_gate_ready",
        "serve_recommendation",
        "the visible counter ring",
        "frozen rubric / thresholds / verdict classes / absolute bars",
    }

    def setUp(self) -> None:
        self.contract = json.loads(
            (REPORTS / "INTEGRATION_CONTRACT.json").read_text(encoding="utf-8")
        )

    def test_charter_version_and_producer_run_preserved(self) -> None:
        self.assertEqual(self.contract["charter_version"], 1)
        self.assertEqual(self.contract["run_id"], PRODUCER_RUN_ID)
        self.assertEqual(self.contract["protocol_sha256"], PRODUCER_ARTIFACT_SHA256["PROTOCOL.json"])

    def test_product_owned_fields_still_forbidden(self) -> None:
        self.assertEqual(
            set(self.contract["product_owned_fields_never_written"]), self.FORBIDDEN
        )

    def test_decline_recommendation_unchanged(self) -> None:
        self.assertEqual(self.contract["adoption_recommendation"]["decision"], "DECLINE_AS_IS")

    def test_machine_checks_still_pin_denominator_and_verbatim(self) -> None:
        checks = "\n".join(self.contract["machine_checks"])
        self.assertIn("assert candidate_n_scored == baseline_n_scored == 20", checks)
        self.assertIn("assert counter_status is unchanged on every row", checks)
        self.assertIn("full_text[char_start:char_end] == quote", checks)

    def test_resume_verification_block_present_and_scoped(self) -> None:
        block = self.contract["resume_verification"]
        self.assertEqual(block["run_id"], RESUME_RUN_ID)
        self.assertEqual(block["resumed_run_id"], PRODUCER_RUN_ID)
        self.assertIn("PROVENANCE_RESUME.json", block["record"])


if __name__ == "__main__":
    unittest.main()
