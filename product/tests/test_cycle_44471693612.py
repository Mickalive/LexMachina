"""Operational resume 44471693612 of persisted snapshot 44464605045.

The mediated P0 delivery (v68 rejection/incumbent leg) is already LANDED and is
verified here, not rebuilt.  The concrete failure this cycle repairs is a
*validation* failure in the resumed snapshot's own cycle test: it re-derived a
durable-delta diagnosis against the resumed run's conventional team ref, which
an operational-resume checkout does not fetch, so the reproduction degraded to
``REF_ABSENT`` and the snapshot failed its self-check even though its committed
bytes were intact.

This test pins the repair (explicit ``--snapshot-ref``, same COMMITTED_DELTA
assertion), the honest UNKNOWN mechanism for 44464605045 (no committed raw
snapshot; GitHub API rate-limited), the fail-closed posture, and the unchanged
v68 content-rejection deliverable.  It writes no gate, no verdict and no
human-gate readiness.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44471693612"
RESUMED_RUN_ID = "44464605045"
RESUMED_HEAD = "04e07eaceb230fcfd33feb891a75b5599b326830"
PREDECESSOR_HEAD = "c3bd920c342b728f6d2ae29ed8f041a0fbdd968b"
# The conventional team ref is absent in an operational-resume / audit checkout
# (which fetches only the accepted base and the current team ref), so this test
# must name a commit SHA that is present in the fetched history.  RESUMED_HEAD is
# exactly that snapshot commit; using it preserves every claim assertion below
# (9-file COMMITTED_DELTA) while making the reproduction checkout-independent.
SNAPSHOT_REF = RESUMED_HEAD
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
DIAG = (ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
BEFORE = (ROOT / "results" / "product" / "offline_slice"
          / "20261024T142517Z" / "rent-default.bundle.json")
AFTER = (ROOT / "results" / "product" / "offline_slice"
         / "20261025T070356Z" / "rent-default.bundle.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{EXECUTING_RUN_ID}_GATE.json")
PRIOR_TEST = (ROOT / "product" / "tests"
              / f"test_cycle_{RESUMED_RUN_ID}.py")

D2_DECISION = "gr_gerichte_ERZ 2010 25"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_is_fail_closed_and_records_this_resume():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    # A later resume may advance current_cycle_run_id; this snapshot's own
    # fail-closed state block stays preserved.  "At least this run" is the
    # currency invariant (the same relaxation already applied in
    # test_cycle_44464605045.py).
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    hist = [r for r in st["run_history"]
            if r.get("run_id") == int(EXECUTING_RUN_ID)]
    assert len(hist) == 1
    assert hist[0]["audit_gate"] == "NONE_YET"
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["status"] == "UNADJUDICATED_OPERATIONAL_RESUME"
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["head_sha"] == RESUMED_HEAD[:8]
    assert block["mechanism"] == "UNKNOWN_NO_COMMITTED_RAW_SNAPSHOT"
    assert block["validation_failure"] == "OBSERVED_REF_ABSENT_IN_CYCLE_TEST"
    assert block["durable_delta"] == "COMMITTED_DELTA"
    assert block["verdict"] == "NONE_UNADJUDICATED"
    assert block["accepted_this_cycle"] is False
    assert block["gate_minted"] is False
    assert block["audit_namespace_written"] is False


def test_diagnosis_proves_committed_delta_from_present_refs():
    from product import resume_snapshot_diagnosis as rsd

    rec = rsd.run(
        RESUMED_RUN_ID,
        "44459256873",
        predecessor_ref=PREDECESSOR_HEAD,
        snapshot_ref=SNAPSHOT_REF,
    )
    assert rec["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert rec["orchestration"]["mechanism_unobserved"] is True
    delta = rec["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 9
    assert delta["snapshot_ref"] == SNAPSHOT_REF
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]
    assert rec["adjudication"]["status"] == "UNADJUDICATED"
    assert rec["adjudication"]["accepted"] is False

    # The committed artifact is the same fact, generated by the CLI.
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 9


def test_explicit_snapshot_ref_repairs_the_reproduction():
    """The exact failure: without the ref a resume checkout degrades to
    REF_ABSENT; the fix passes a present ref and still proves the same delta.
    No claim is weakened: both arms must resolve before a delta is asserted.
    """
    from product import resume_snapshot_diagnosis as rsd

    absent = rsd._delta(
        "origin/cycle/core/product/44459256873/team", PREDECESSOR_HEAD)
    assert absent["classification"] == "REF_ABSENT"
    present = rsd._delta(SNAPSHOT_REF, PREDECESSOR_HEAD)
    assert present["classification"] == "COMMITTED_DELTA"
    assert present["changed_files"] == 9

    source = PRIOR_TEST.read_text(encoding="utf-8")
    assert "--snapshot-ref" in source, (
        "the resumed snapshot's cycle test must name a present ref so it is "
        "reproducible in an operational-resume checkout")
    # Its repaired test must actually be green here.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(PRIOR_TEST), "-q"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]


def test_audit_readiness_profile_pins_this_run_without_minting_a_gate():
    from product import audit_readiness as ar

    profile = ar.select_profile(EXECUTING_RUN_ID)
    assert profile["resumed_run_id"] == RESUMED_RUN_ID
    assert profile["mechanism_kind"] == "unobserved"
    assert profile["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert profile["delta_kind"] == "committed"
    assert profile["changed_files"] == 9
    assert profile["cycle_test"].endswith(
        f"test_cycle_{EXECUTING_RUN_ID}.py")
    assert profile["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert REPORT.is_file() and "UNADJUDICATED" in REPORT.read_text()
    assert not GATE.exists(), "producer must never write an audit gate"


def test_p0_rejection_leg_still_downgrades_the_letterhead_row():
    from product.query.counter_evidence_span import frozen_content_defects

    before_row = next(
        r for r in _load(BEFORE)["decisions"]
        if r["decision_id"] == D2_DECISION)
    after_row = next(
        r for r in _load(AFTER)["decisions"]
        if r["decision_id"] == D2_DECISION)
    assert before_row["counter_evidence_verified"] is True
    assert "D2_letterhead_zone" in frozen_content_defects(
        before_row["counter_evidence"], before_row)
    assert after_row["counter_evidence_verified"] is False
    assert after_row["counter_evidence_unevidenced"] is True


def test_content_family_still_proves_the_v68_rejection_leg():
    cf = _load(ROOT / "results" / "product" / "counter_content_family"
               / "CYCLE_40257275384.json")
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"]
    assert cf["ordered_work_2_success_rule"]["met"] is True
