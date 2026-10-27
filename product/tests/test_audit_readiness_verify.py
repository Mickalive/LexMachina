"""Regression guard for committed audit-readiness dossiers.

Cycle 40423889401 was rejected for one provenance defect: its dossier was
generated *before* the report and state were final, so two recorded
``claim_artifacts`` sha256 values matched bytes that were never committed.
Generation-time hashing cannot catch that, because the artifact is edited
after the dossier is written.

``product.audit_readiness.verify_dossier`` is the post-commit instrument: it
re-reads a committed dossier and re-hashes every recorded artifact. These
tests exercise it on synthetic dossiers only (never the repository's own
dossier) so it is safe to run inside dossier generation itself.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product.audit_readiness import _sha256, verify_dossier  # noqa: E402


def _dossier(path: Path, hashes: dict) -> Path:
    path.write_text(json.dumps({
        "schema": "product-audit-readiness/1",
        "run_id": "synthetic",
        "generated_at": "2026-01-01T00:00:00Z",
        "checks": [{
            "id": "claim_artifacts",
            "status": "PASS",
            "detail": {"sha256": hashes},
        }],
    }), encoding="utf-8")
    return path


def test_verify_accepts_matching_bytes(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"a": 1}\n', encoding="utf-8")
    dossier = _dossier(tmp_path / "dossier.json",
                       {str(artifact): _sha256(artifact)})
    verdict = verify_dossier(dossier)
    assert verdict["ok"] is True, verdict
    assert verdict["n_checked"] == 1
    assert verdict["problems"] == []


def test_verify_detects_a_stale_hash_after_the_artifact_changes(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"a": 1}\n', encoding="utf-8")
    dossier = _dossier(tmp_path / "dossier.json",
                       {str(artifact): _sha256(artifact)})
    artifact.write_text('{"a": 2}\n', encoding="utf-8")
    verdict = verify_dossier(dossier)
    assert verdict["ok"] is False
    assert verdict["n_checked"] == 1
    problem = verdict["problems"][0]
    assert problem["path"] == str(artifact)
    assert problem["problem"] == "STALE"
    assert problem["recorded"] != problem["actual"]


def test_verify_detects_a_missing_artifact(tmp_path):
    dossier = _dossier(tmp_path / "dossier.json",
                       {str(tmp_path / "gone.json"): "0" * 64})
    verdict = verify_dossier(dossier)
    assert verdict["ok"] is False
    assert verdict["problems"][0]["problem"] == "MISSING"


def test_verify_fails_closed_on_a_missing_or_malformed_dossier(tmp_path):
    missing = verify_dossier(tmp_path / "absent.json")
    assert missing["ok"] is False
    assert missing["problems"][0]["problem"] == "DOSSIER_MISSING"

    no_check = tmp_path / "no_check.json"
    no_check.write_text(json.dumps({"checks": []}), encoding="utf-8")
    verdict = verify_dossier(no_check)
    assert verdict["ok"] is False
    assert verdict["problems"][0]["problem"] == "CLAIM_ARTIFACTS_CHECK_MISSING"
