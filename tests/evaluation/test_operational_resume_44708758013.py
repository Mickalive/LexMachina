"""Regression guard for the 44708758013 operational-resume deliverable.

Pins the audit-quantum diagnosis of run 44700681660, the byte-identity proof of
its preserved producer pack, the freeze inputs and the unchanged frozen
references, so a later cycle cannot silently rewrite this operational record or
edit a frozen reference to obtain a pass.
"""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "44708758013"
RESUMED = "44700681660"


def _sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_result_record_and_snapshot_facts():
    result = _load(f"results/evaluation/operational_resume_{RUN}/{RUN}.json")
    assert result["run_id"] == 44708758013
    assert result["resumes_snapshot_of_run"] == 44700681660
    assert result["snapshot_head"] == "a3dd61fbddd8d973dfc438542ede3bc33ca7f6d6"
    assert result["accepted_run_id"] == 40265377500
    assert result["direction_version"] == 68
    assert result["accepted_head_both_halves"]["half_i_audit_gate"]["gate"] == "PASS"
    assert result["accepted_head_both_halves"]["half_ii_accept_commit"]["passed"] is True
    assert result["snapshot_integrity"]["head_matches_snapshot"] is True
    assert result["snapshot_integrity"]["tracked_tree_identical_to_snapshot"] is True
    assert result["posture"]["human_gate_ready"] is False
    assert result["posture"]["owner_decision_required"] is False


def test_audit_quantum_diagnosis_pinned():
    result = _load(f"results/evaluation/operational_resume_{RUN}/{RUN}.json")
    fd = result["failure_diagnosis"]
    assert fd["classification"] == "ORCHESTRATION_AUDIT_QUANTUM_EXPIRY_RC78"
    assert fd["independent_audit_duration_s"] == 2705
    assert fd["quantum_s"] == 2700
    assert fd["rc78_annotation_confirmed"] is True
    assert fd["gate_written"] is False
    assert fd["producer_work_preserved"] is True
    d = _load(f"results/evaluation/operational_resume_{RUN}/run_{RESUMED}_audit_quantum_diagnosis.json")
    assert d["failure_class"] == "ORCHESTRATION_AUDIT_QUANTUM_EXPIRY_RC78"
    assert d["independent_audit_duration_s"] - d["quantum_s"] == 5
    assert "Process completed with exit code 78." in d["annotation_messages"]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in a for a in d["annotation_messages"])
    assert d["producer_work_preserved"]["prior_final_gates_verdict"] == "AUDIT_READY"
    assert d["parallel_product_run_corroboration"]["run"] == 44700830021
    assert d["parallel_product_run_corroboration"]["independent_audit_step"]["duration_s"] == 2705
    assert d["controls"]["no_log_body_quoted"] is True


def test_prior_producer_pack_byte_identity():
    pack = _load(f"results/evaluation/operational_resume_{RUN}/{RESUMED}_producer_pack_byte_identity.json")
    assert pack["all_match"] is True
    assert pack["n_files"] == 7
    assert pack["prior_final_gates"]["verdict"] == "AUDIT_READY"
    assert pack["prior_final_gates"]["passed"] is True
    for row in pack["files"]:
        assert row["matches_pin"] is True, row["path"]
        assert _sha(row["path"]) == row["pinned_sha256"], row["path"]
        assert row["disposition"] if "disposition" in row else True


def test_ordered_work_unchanged():
    result = _load(f"results/evaluation/operational_resume_{RUN}/{RUN}.json")
    ow = result["ordered_work"]
    assert ow["item_1"]["status"] == "DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN"
    assert ow["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert ow["item_3"]["status"] == "KEPT_NOT_RERUN"
    assert ow["item_3"]["sha256_matches_this_run_pin"] is True
    assert ow["item_5"]["status"] == "HONOURED"
    assert ow["item_5"]["no_universal_174k_benchmark"] is True
    assert ow["all_pins_match"] is True
    assert result["reuse"]["falsifier_or_probe_rerun"] is False
    assert result["reuse"]["universal_174k_benchmark"] is False


def test_frozen_references_unedited():
    assert _sha("evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha("evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert _sha("evaluation/fast_mvp_retrieval_recall_benchmark.py") == \
        "fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283"


def test_freeze_pins_instrument_and_prior_pack():
    freeze = _load(f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    assert freeze["direction_version"] == 68
    assert freeze["failed_run"] == 44700681660
    assert freeze["failure_class"] == "ORCHESTRATION_AUDIT_QUANTUM_EXPIRY_RC78"
    assert freeze["freeze_precedes_execution"] is True
    assert freeze["frozen_edits"] == []
    assert freeze["instrument_sha256"] == _sha(f"evaluation/operational_resume_{RUN}.py")
    assert freeze["hypothesis_sha256"] == \
        _sha(f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
    for name, pin in freeze["prior_producer_pack_pins"].items():
        path = (f"results/evaluation/operational_resume_{RESUMED}/{name}"
                if name.startswith("44700681660") else
                f"reports/evaluation/{name}" if name.endswith(".md") else
                f"tests/evaluation/{name}" if name.startswith("test_") else
                f"evaluation/{name}")
        assert _sha(path) == pin, path


def test_prior_run_artifacts_preserved():
    """Every claim-bearing file of run 44700681660 still exists and is untouched."""
    for rel in [
        f"results/evaluation/operational_resume_{RESUMED}/{RESUMED}.json",
        f"results/evaluation/operational_resume_{RESUMED}/{RESUMED}_final_gates.json",
        f"results/evaluation/operational_resume_{RESUMED}/run_44693400630_failure_diagnosis.json",
        f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}.md",
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json",
        f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RESUMED}.py",
    ]:
        assert (ROOT / rel).is_file(), rel
    fg = _load(f"results/evaluation/operational_resume_{RESUMED}/{RESUMED}_final_gates.json")
    assert fg["verdict"] == "AUDIT_READY" and fg["passed"] is True


def test_state_blocks_and_pointer_advance():
    root = _load("state/evaluation.json")
    lane = _load("evaluation/state/evaluation.json")
    for st in (root, lane):
        blk = st[f"operational_resume_{RUN}"]
        assert blk["claim_bearing_run"] == 44708758013
        assert blk["accepted_as_evidence"] is False
        assert blk["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        assert st["github_run"] == 44708758013
        assert st["proposed_run_id"] == 44708758013
        assert st["accepted_run_id"] == 40265377500
        assert st["evidence_refs_n"] == len(st["evidence_refs"])
    assert root["github_run"] == lane["github_run"]


def test_final_gates_auditable():
    fg = _load(f"results/evaluation/operational_resume_{RUN}/{RUN}_final_gates.json")
    assert fg["run_id"] == 44708758013
    assert fg["resumes_snapshot_of"] == 44700681660
    assert fg["accepted_as_evidence"] is False
    assert fg["passed"] is True
    assert fg["verdict"] == "AUDIT_READY"
    assert all(fg["rule_pass"].values())
    idx = _load(f"results/evaluation/operational_resume_{RUN}/{RUN}_AUDIT_INDEX.json")
    assert idx["headline"]["failure_class"] == "ORCHESTRATION_AUDIT_QUANTUM_EXPIRY_RC78"
    assert idx["headline"]["prior_pack_byte_identity"] is True
