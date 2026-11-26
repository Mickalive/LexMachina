"""Operational resume 45783588895: post-accept state-pointer repair.

The persisted team snapshot of run 45783095548 is byte-identical to the
accepted lab/product head, and no audit/accept half exists for it.  The real
validation failure discovered on resume is POST-ACCEPT POINTER REGRESSION:
run 40284658455 had already been audited (gate PASS) and accepted at
7be4480e, while ``state/product.json`` still named CYCLE_40269774540 /
5adaa66d, so its own cycle test failed two assertions.  This test locks the
repair fail-closed:

* the instrument-produced diagnosis proves ZERO_DURABLE_DELTA from git refs
  and records the provider mechanism as UNOBSERVED - no rc-67/rc-78/gateway
  cause is invented from an unavailable run/jobs snapshot;
* the live accepted pointer satisfies BOTH halves of requirement 4 and names
  the integrated accept commit, while the prior pointer is preserved in the
  append-only supersession chain;
* this run minted no audit gate, wrote no auditor namespace path and moved
  no posture flag; ``continue_recommended`` stays true until a human gate.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "45783588895"
RESUMED_RUN_ID = "45783095548"
ACCEPTED_RUN = "40284658455"
ACCEPTED_SHA = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
PRIOR_RUN = "40269774540"

STATE = ROOT / "state" / "product.json"
DIAG = (ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RUN_ID}_audit_readiness.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_zero_delta_snapshot_diagnosis_is_honest():
    diag = _load(DIAG)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == ACCEPTED_RUN
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert diag["orchestration"]["mechanism_unobserved"] is True
    assert "mechanism" not in diag["orchestration"]
    assert diag["raw_snapshot"] is None
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["product_defect"] is False
    assert adj["verdict_written"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["accept"]["accepted_ref_present"] is False


def test_post_accept_pointer_satisfies_both_halves_and_preserves_history():
    from product import state_contract as sc

    st = _load(STATE)
    assert st["current_cycle_run_id"] == int(RUN_ID)
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN}"
    assert st["accepted_commit"] == ACCEPTED_SHA
    ev = sc.accepted_pointer_evidence(st)
    assert ev["problems"] == [], ev
    assert ev["gate_ok"] is True and ev["accept_commit_present"] is True
    gate = _load(ROOT / "results" / "audit" / "product"
                 / f"CYCLE_{ACCEPTED_RUN}_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    assert f"accept product cycle {ACCEPTED_RUN}" in _git(
        "log", "--all", "--oneline",
        f"--grep=^accept product cycle {ACCEPTED_RUN}$")
    head = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product")
    assert head.startswith(ACCEPTED_SHA)
    # The superseded pointer and the observed regression stay on the record.
    supersession = st["accepted_run_supersession"]
    assert f"CYCLE_{PRIOR_RUN}" in supersession
    assert "POST-ACCEPT pointer repair" in supersession
    block = st["cycle_45783588895_operational_resume"]
    assert block["validation_failure"]["class"] == (
        "POST_ACCEPT_STATE_POINTER_REGRESSION")
    assert block["diagnosis_facts"]["provider_cause_claimed"] is False
    hist = {str(h["run_id"]): h for h in st["run_history"]}
    assert hist[RESUMED_RUN_ID]["status"] == (
        "OPERATIONAL_RESUME_SNAPSHOT_ZERO_DELTA_NO_AUDIT")
    assert hist[RUN_ID]["status"] == "OPERATIONAL_RESUME_POST_ACCEPT_POINTER_REPAIR"
    assert "later_integration_note" in hist[ACCEPTED_RUN]


def test_audit_readiness_profile_and_dossier_target_this_run():
    from product import audit_readiness as ar

    prof = ar.select_profile(RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == ACCEPTED_RUN
    assert prof["mechanism_kind"] == "unobserved"
    assert prof["delta_kind"] == "zero"
    assert prof["raw"] is None
    assert prof["cycle_test"] == "product/tests/test_cycle_45783588895.py"
    assert prof["state_block"] == "cycle_45783588895_operational_resume"
    assert Path(prof["resume_diag"]) == DIAG
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown run must never inherit a default profile")

    # The dossier is produced BY audit_readiness, so this test must not depend
    # on its final verdict (that would be circular).  When a generated dossier
    # is present, check only that it targets this run; the dossier itself is
    # the artifact the independent auditor reads.
    if DOSSIER.is_file():
        dossier = _load(DOSSIER)
        assert dossier["run_id"] == RUN_ID
        assert dossier["resumed_run_id"] == RESUMED_RUN_ID


def test_no_producer_minted_gate_and_posture_stays_fail_closed():
    st = _load(STATE)
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is not True
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN_ID}_GATE.json").exists()
    audit_refs = _git("ls-remote", "--heads", "origin",
                      f"refs/heads/cycle/core/product/{RUN_ID}/audit")
    assert audit_refs == ""


def test_report_of_record_names_diagnosis_and_claim_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in text and RESUMED_RUN_ID in text
    assert "POST_ACCEPT_STATE_POINTER_REGRESSION" in text
    assert "ZERO_DURABLE_DELTA" in text
    assert "QUERY_MAP_MIXTURE_VERTICAL_SLICE_V1" in text
    assert "human_gate_ready=false" in text
