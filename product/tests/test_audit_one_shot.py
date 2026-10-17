"""Tests for product/audit_one_shot.py — the one-command audit recomputation.

Why this suite exists
---------------------
Three consecutive independent audits of this lane burned their 45-minute work
quantum re-deriving the same headline claims (runs 3888477028, 38993348615,
38995823263).  ``audit_one_shot.py`` packages the audits' own check set into one
bounded offline command.  These tests prove the packaging is sound AND
non-vacuous: every load-bearing check has a negative control that must fail.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audit_one_shot as aos  # noqa: E402


# --------------------------------------------------------------------------- #
# registry and record shape
# --------------------------------------------------------------------------- #

def test_registry_lists_the_audit_check_set():
    assert list(aos.CHECKS) == [
        "state_contract",
        "rebuild_served_packet_check",
        "evidence_pack_recall_nc",
        "targeted_product_suite",
        "query_page_dom_smoke",
        "forbidden_claims_scan",
        "packet_admission_invariant",
    ]


def test_every_check_has_a_default_timeout():
    for name in aos.CHECKS:
        assert name in aos.DEFAULT_TIMEOUTS, name


def test_committed_inputs_exist():
    # The frozen inputs the one-shot recomputes from must stay committed.
    assert aos.BJR_BUNDLE.exists(), aos.BJR_BUNDLE
    assert aos.BJR_LEG.exists(), aos.BJR_LEG
    assert aos.DOM_SMOKE_BUNDLE.exists(), aos.DOM_SMOKE_BUNDLE


def test_fast_subset_end_to_end_writes_a_passing_record(tmp_path, capsys):
    out = tmp_path / "record.json"
    rc = aos.main([
        "--run-id", "TESTFAST",
        "--only", "state_contract,forbidden_claims_scan,packet_admission_invariant",
        "--out", str(out),
    ])
    assert rc == 0, capsys.readouterr()
    record = json.loads(out.read_text())
    assert record["schema"] == "product/audit-one-shot/1"
    assert record["run_id"] == "TESTFAST"
    assert record["overall"] == "PASS"
    assert record["failed"] == []
    assert set(record["passed"]) == {
        "state_contract", "forbidden_claims_scan", "packet_admission_invariant"}
    assert any("no gate the product does not already own" in c
               for c in record["claim_ceiling"])


def test_unknown_check_name_exits_2(tmp_path, capsys):
    rc = aos.main(["--run-id", "X", "--only", "no_such_check", "--out",
                   str(tmp_path / "r.json")])
    assert rc == 2
    assert "unknown check" in capsys.readouterr().err


def test_bad_timeout_exits_2(tmp_path, capsys):
    rc = aos.main(["--run-id", "X", "--timeout", "noseconds", "--out",
                   str(tmp_path / "r.json")])
    assert rc == 2


# --------------------------------------------------------------------------- #
# negative controls — every load-bearing check must FAIL on a regressed input
# --------------------------------------------------------------------------- #

def test_rebuild_check_fails_on_a_tampered_reference(tmp_path, monkeypatch):
    """Non-vacuity of the headline obligation-(5) reproduction: flip the
    reference's recall n and the check must fail."""
    tampered = tmp_path / "leg_tampered.json"
    leg = json.loads(aos.BJR_LEG.read_text())
    gate = leg["recall_gate_recall_controlling_authority"]
    assert gate["n"] == 3  # the committed reality this control regresses
    gate["n"] = 5
    tampered.write_text(json.dumps(leg))
    monkeypatch.setattr(aos, "BJR_LEG", tampered)
    rec = aos.check_rebuild_served_packet(aos.DEFAULT_TIMEOUTS["rebuild_served_packet_check"])
    assert rec["verdict"] == "FAIL"
    assert rec["rc"] == 1
    assert rec["key_findings"]["reproduces_19_fields"] is False


def test_packet_admission_invariant_fails_on_a_laundered_ready_flag(monkeypatch):
    """Obligation (1): if some future code sets ready_for_owner_session=True
    while the DO-NOT-SERVE order stands, this check must fail."""
    import packet_admission as pa
    real = pa.packet_admission

    def laundered(path=None):
        out = real(path)
        out["ready_for_owner_session"] = True
        out["human_gate_ready"] = True
        out["blocked_by"] = []
        return out

    monkeypatch.setattr(pa, "packet_admission", laundered)
    rec = aos.check_packet_admission_invariant(60.0)
    assert rec["verdict"] == "FAIL"
    assert rec["key_findings"]["do_not_serve_order_active"] is True
    assert rec["key_findings"]["ready_for_owner_session"] is True


def test_packet_admission_invariant_holds_on_the_committed_state():
    rec = aos.check_packet_admission_invariant(60.0)
    assert rec["verdict"] == "PASS"
    kf = rec["key_findings"]
    assert kf["do_not_serve_order_active"] is True
    assert kf["ready_for_owner_session"] is False
    assert "accepted_do_not_serve_order" in kf["blocked_by"]


def test_forbidden_claims_scan_fails_on_a_forbidden_construction(tmp_path):
    bad = tmp_path / "report.md"
    bad.write_text(
        "Summary of findings.\n"
        "bge_BGE_115_II_1 is a supporting authority for the answer.\n"
    )
    rec = aos.check_forbidden_claims_scan(60.0, report=bad)
    assert rec["verdict"] == "FAIL"
    hits = rec["key_findings"]["forbidden_claim_hits"]
    assert any("bge_BGE_115_II_1" in str(v) for v in hits.values())


def test_forbidden_claims_scan_passes_on_the_committed_artifacts():
    rec = aos.check_forbidden_claims_scan(60.0)
    assert rec["verdict"] == "PASS"
    assert rec["key_findings"]["forbidden_claim_hits"] == {}


def test_dom_smoke_is_skipped_without_node(monkeypatch):
    monkeypatch.setattr(aos.shutil, "which", lambda name: None)
    rec = aos.check_query_page_dom_smoke(60.0)
    assert rec["verdict"] == "SKIPPED"
    assert rec["rc"] is None


def test_timeout_is_recorded_as_failure(monkeypatch):
    def fake_run(argv, timeout):
        return 124, "", "timeout", 5.0, f"TIMEOUT after {timeout}s"
    monkeypatch.setattr(aos, "_run", fake_run)
    rec = aos.check_state_contract(1.0)
    assert rec["verdict"] == "FAIL"
    assert rec["rc"] == 124
    assert "TIMEOUT" in rec["timeout"]


def test_run_checks_rejects_unknown_names():
    with pytest.raises(ValueError, match="unknown check"):
        aos.run_checks(["bogus"])


def test_recall_values_are_reported_not_gated():
    """The claim ceiling of the recall instrument must survive into the record:
    evidence_pack_recall values are reported, and only the documented
    non-vacuity property is enforced."""
    src = Path(aos.__file__).read_text()
    assert "recall values are reported, not gated" in src
    assert "frozen-bar measurement is Core Evaluation's" in src
