"""Snapshot audit-readiness verifier: integration plus per-check breaking fixtures.

Discipline: every check has a synthetic input that makes it FAIL (a green
that cannot go red is not evidence). The integration test needs the accepted
product mount, exactly like the frozen-bar gate tests.
"""
import json
from pathlib import Path

import pytest

from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR
from evaluation.snapshot_audit import run_snapshot_audit as rsa

MOUNT_AVAILABLE = all((SERVED_PACKET_DIR / f"{qid}.bundle.json").exists() for qid in QIDS)
needs_mount = pytest.mark.skipif(not MOUNT_AVAILABLE, reason="accepted product mount absent")

CHECK_IDS = {
    "frozen_rubric_rehash",
    "bar_gates_verdict",
    "h1_default_record_identity",
    "lane_suite_pass",
    "state_evidence_refs_resolve",
    "deliverable_manifest_complete",
    "orchestration_diagnosis_record",
}


# ---------------------------------------------------------------- fixtures --

def _fake_root(tmp_path: Path, rules_bytes: bytes = b'{"tampered": true}',
               vendored_files: dict | None = None) -> Path:
    """Minimal fake repo root carrying the three rubric-path files."""
    bar = tmp_path / "evaluation/frozen_bars"
    bar.mkdir(parents=True)
    (bar / "RULES_LABEL.json").write_bytes(rules_bytes)
    (bar / "RULES_GEOMETRY.json").write_bytes(rules_bytes)
    vend = bar / "vendored"
    vend.mkdir()
    if vendored_files is None:
        vendored_files = {
            "evaluation/frozen_bars/RULES_LABEL.json":
                __import__("hashlib").sha256(rules_bytes).hexdigest(),
            "evaluation/frozen_bars/RULES_GEOMETRY.json":
                __import__("hashlib").sha256(rules_bytes).hexdigest(),
        }
    (vend / "VENDORED_SHA256.json").write_text(json.dumps({"files": vendored_files}))
    return tmp_path


def _minimal_valid_diagnosis() -> dict:
    return {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "query_method": "test-double",
        "limits": "test-double",
        "runs": {
            "38972887369": {"conclusion": "failure",
                            "jobs": {"audit": {"failed_step": "Run lane cycle"}}},
            "38977570612": {"conclusion": "failure",
                             "jobs": {"audit": {"failed_step": "Enforce audit scope and read gate",
                                                "ambiguity_flag": "logs 403; two candidate causes"}}},
        },
    }


# ------------------------------------------------------- breaking fixtures --

def test_rubric_rehash_fails_on_tampered_bytes(tmp_path):
    root = _fake_root(tmp_path)
    res = rsa.check_rubric_rehash(root)
    assert res["status"] == "FAIL"
    assert res["mismatches"], "tampered rubric bytes must produce mismatches"


def test_rubric_rehash_passes_on_correct_bytes(tmp_path):
    real_label = Path("evaluation/frozen_bars/RULES_LABEL.json").read_bytes()
    real_geom = Path("evaluation/frozen_bars/RULES_GEOMETRY.json").read_bytes()
    bar = tmp_path / "evaluation/frozen_bars"
    bar.mkdir(parents=True)
    (bar / "RULES_LABEL.json").write_bytes(real_label)
    (bar / "RULES_GEOMETRY.json").write_bytes(real_geom)
    vend = bar / "vendored"
    vend.mkdir()
    (vend / "VENDORED_SHA256.json").write_text(json.dumps({"files": {
        "evaluation/frozen_bars/RULES_LABEL.json":
            __import__("hashlib").sha256(real_label).hexdigest(),
        "evaluation/frozen_bars/RULES_GEOMETRY.json":
            __import__("hashlib").sha256(real_geom).hexdigest(),
    }}))
    res = rsa.check_rubric_rehash(tmp_path)
    assert res["status"] == "PASS", res


def test_h1_comparator_identical_except_elapsed():
    base = {"verdict": "PASS_NO_REGRESSION", "label_gate": {"n_supported": 5}, "elapsed_s": 1.0}
    other = json.loads(json.dumps(base))
    other["elapsed_s"] = 9.9
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is True
    assert res["differing_fields"] == []


def test_h1_comparator_detects_verdict_divergence():
    base = {"verdict": "PASS_NO_REGRESSION", "elapsed_s": 1.0}
    other = {"verdict": "FAIL_REGRESSION", "elapsed_s": 1.0}
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is False
    assert "verdict" in res["differing_fields"]


def test_h1_comparator_detects_nested_divergence():
    base = {"label_gate": {"classes": {"SUPPORTED": 5}}, "elapsed_s": 1.0}
    other = {"label_gate": {"classes": {"SUPPORTED": 3}}, "elapsed_s": 2.0}
    res = rsa.compare_h1(base, other)
    assert res["identical_except_elapsed_s"] is False
    assert "label_gate" in res["differing_fields"]


def test_evidence_refs_checker_fails_on_broken_ref(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": ["state/evaluation.json", "does/not/exist.json"]}))
    res = rsa.check_evidence_refs(tmp_path)
    assert res["status"] == "FAIL"
    assert res["missing"] == ["does/not/exist.json"]


def test_evidence_refs_checker_passes_when_all_resolve(tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state/evaluation.json").write_text(json.dumps(
        {"evidence_refs": ["state/evaluation.json"]}))
    res = rsa.check_evidence_refs(tmp_path)
    assert res["status"] == "PASS", res


def test_diagnosis_checker_rejects_missing_file(tmp_path):
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "FAIL"


def test_diagnosis_checker_rejects_incomplete_structure(tmp_path):
    diag = _minimal_valid_diagnosis()
    diag["runs"]["38977570612"]["jobs"]["audit"].pop("ambiguity_flag")
    p = tmp_path / "evaluation/snapshot_audit"
    p.mkdir(parents=True)
    (p / "orchestration_diagnosis_2026-10-16.json").write_text(json.dumps(diag))
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "FAIL"
    assert "runs.38977570612 ambiguous-cause flag" in res["problems"]


def test_diagnosis_checker_passes_on_valid_structure(tmp_path):
    p = tmp_path / "evaluation/snapshot_audit"
    p.mkdir(parents=True)
    (p / "orchestration_diagnosis_2026-10-16.json").write_text(
        json.dumps(_minimal_valid_diagnosis()))
    res = rsa.check_diagnosis_record(tmp_path)
    assert res["status"] == "PASS", res


def test_manifest_checker_fails_on_missing_deliverables(tmp_path):
    res = rsa.check_manifest(tmp_path)
    assert res["status"] == "FAIL"
    assert len(res["missing"]) == len(rsa.DELIVERABLE_MANIFEST_PATHS)


# ------------------------------------------------------------ integration --

@needs_mount
def test_readiness_record_passes_on_current_snapshot(tmp_path):
    out = tmp_path / "readiness.json"
    rc = rsa.main(["--run-id", "38978411574", "--out", str(out),
                   "--repo-root", str(Path.cwd())])
    assert rc == 0, "verifier must exit 0 (READY) on the current snapshot"
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["schema"] == "lex-evaluation-snapshot-audit/1"
    assert record["run_id"] == "38978411574"
    assert record["ready_for_independent_audit"] is True
    assert {c["id"] for c in record["checks"]} == CHECK_IDS
    assert all(c["status"] == "PASS" for c in record["checks"])
    assert record["n_passed"] == record["n_checks"]
    assert record["audit_gate_path"] == \
        "results/audit/evaluation/CYCLE_38978411574_GATE.json"
    assert record["audit_report_path"] == \
        "reports/audit/evaluation/CYCLE_38978411574.md"
    assert len(record["deliverable_sha256"]) == len(rsa.DELIVERABLE_MANIFEST_PATHS)
    assert record["snapshot_claims_not_certified"], \
        "the record must state what it does NOT certify"


@needs_mount
def test_main_exit_code_is_one_when_a_check_fails(tmp_path, monkeypatch):
    """Breaking fixture at the record level: force one check red and require
    exit 1 with ready=false (a verifier that cannot fail is not evidence)."""
    monkeypatch.setattr(rsa, "check_lane_suite",
                        lambda repo_root: {"id": "lane_suite_pass", "status": "FAIL",
                                          "detail": "forced red"})
    out = tmp_path / "readiness.json"
    rc = rsa.main(["--run-id", "FORCEDRED", "--out", str(out),
                   "--repo-root", str(Path.cwd())])
    assert rc == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["ready_for_independent_audit"] is False
    assert record["n_passed"] == record["n_checks"] - 1
