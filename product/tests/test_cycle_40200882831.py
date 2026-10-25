"""Executable re-derivation of product cycle 40200882831's resume claims.

Run 40196023042's producer job succeeded and persisted a real 9-file delta, but
its audit job died inside *Independent audit* with
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78): the gate and persist
steps were skipped, no audit ref exists, and the run is UNADJUDICATED.  This
resume run (40200882831) preserves that snapshot and publishes a bounded
audit-readiness dossier so the next auditor does not spend its own quantum
rediscovering the slice.

Claims are separated on purpose:

1. **Orchestration** - the quantum expiry is now observed from the public
   check-run annotations, not guessed; the previous snapshots without
   annotations still classify as ``UNOBSERVED``.
2. **Durable delta** - the resumed snapshot carries 9 committed files over its
   predecessor and is not accepted by either half of requirement 4.
3. **Lane deliverable** - the v68 rejection/incumbent leg still flips the D2
   letterhead row from verified to unverified, the fixed-path family is still
   29 bundles / 0 verified-and-defective, and the progressive slice still runs
   over a real socket in fixture mode.
4. **Audit readiness** - one bounded command re-derives or hashes every claim
   and writes no gate.

Nothing here writes a gate, scores a frozen bar, or labels a run rejected.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_readiness as ar                 # noqa: E402
from product import audit_step_diagnosis as asd           # noqa: E402
from product import resume_snapshot_diagnosis as rsd      # noqa: E402

CURRENT_RUN_ID = "40200882831"
RESUMED_RUN_ID = "40196023042"
PREDECESSOR_RUN_ID = "40193974025"
DIRV = 68
D2_DECISION = "gr_gerichte_ERZ 2010 25"

ORCH = REPO_ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
OLD_RAW = ORCH / "CYCLE_40193974025_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
READINESS = (REPO_ROOT / "results" / "product" / "audit_readiness"
             / f"CYCLE_{CURRENT_RUN_ID}_audit_readiness.json")
SMOKE = (REPO_ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{CURRENT_RUN_ID}_progressive_smoke.json")
CONTENT_FAMILY = (REPO_ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40188639817.json")
BEFORE = (REPO_ROOT / "results" / "product" / "offline_slice"
          / "20261024T142517Z" / "rent-default.bundle.json")
AFTER = (REPO_ROOT / "results" / "product" / "offline_slice"
         / "20261025T070356Z" / "rent-default.bundle.json")
STATE = REPO_ROOT / "state" / "product.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)


def _rev(ref: str) -> str | None:
    p = _git("rev-parse", "--verify", "--quiet", ref)
    if p.returncode != 0:
        return None
    return p.stdout.strip() or None


def _without_timestamps(rec: dict) -> dict:
    out = copy.deepcopy(rec)
    out.pop("generated_at", None)
    out.get("orchestration", {}).pop("generated_at", None)
    return out


def _row(bundle: dict, decision_id: str) -> dict | None:
    return next((r for r in bundle.get("decisions") or []
                 if r.get("decision_id") == decision_id), None)


# ---------------------------------------------------------------------------
# 1. Orchestration: quantum expiry is OBSERVED, not guessed
# ---------------------------------------------------------------------------

def test_quantum_expiry_reclassifies_the_resumed_run_from_annotations() -> None:
    raw = _load(RAW)
    art = _load(DIAG)["orchestration"]
    fresh = asd.classify(raw)

    assert str(raw["run"]["id"]) == RESUMED_RUN_ID
    assert raw["run"]["conclusion"] == "failure"
    assert fresh["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert _without_timestamps(fresh) == _without_timestamps(art)

    audit = fresh["audit"]
    assert audit["conclusion"] == "failure"
    assert audit["failed_step"] == "Independent audit"
    assert audit["independent_audit_step_seconds"] == 2705.0
    assert audit["gate_step"] == "skipped"
    assert audit["persist_step"] == "skipped"
    assert audit["gate_file_written"] is False

    mechanism = fresh["mechanism"]
    assert mechanism["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mechanism["quantum_expired"] is True
    assert mechanism["quantum_seconds"] == 2700
    assert mechanism["exit_code"] == 78

    observed = fresh["observed_failure"]
    assert observed["source"] == "github_actions_check_run_annotations"
    assert observed["annotations_available"] is True
    assert observed["quantum_expired"] is True
    assert observed["quantum_seconds"] == 2700
    assert observed["exit_code"] == 78
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in observed[
        "quantum_message"]

    assert fresh["integrate"]["conclusion"] == "skipped"
    assert fresh["adjudication"]["product_defect"] is False
    assert fresh["adjudication"]["verdict_written"] is False


def test_snapshots_without_annotations_are_not_upgraded_to_observed() -> None:
    """The annotation path must not retro-fit a cause onto older snapshots."""
    fresh = asd.classify(_load(OLD_RAW))
    assert fresh["mechanism"]["status"] == "UNOBSERVED"
    assert fresh["mechanism"]["quantum_expired"] is False
    assert fresh["observed_failure"]["annotations_available"] is False
    assert fresh["observed_failure"]["source"] == "none"


# ---------------------------------------------------------------------------
# 2. Durable delta and adjudication
# ---------------------------------------------------------------------------

def test_resume_diagnosis_artifact_is_internally_consistent() -> None:
    art = _load(DIAG)
    assert art["run_id"] == RESUMED_RUN_ID
    assert art["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert art["orchestration"]["mechanism"]["status"] == (
        "OBSERVED_QUANTUM_EXPIRED")
    assert art["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert art["durable_delta"]["changed_files"] == 9
    assert "product/audit_step_diagnosis.py" in art[
        "durable_delta"]["changed_paths_sample"]
    assert art["adjudication"]["status"] == "UNADJUDICATED"
    assert art["adjudication"]["accepted"] is False
    assert art["adjudication"]["audit"]["audit_ref_present"] is False
    assert art["adjudication"]["audit"]["gate_file_present"] is False
    assert art["adjudication"]["accept"]["accept_commit"] is None
    assert not (REPO_ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()


def test_resume_diagnosis_reproduces_when_the_refs_are_mounted() -> None:
    team_ref = f"origin/cycle/core/product/{RESUMED_RUN_ID}/team"
    pred_ref = f"origin/cycle/core/product/{PREDECESSOR_RUN_ID}/team"
    if _rev(team_ref) is None or _rev(pred_ref) is None:
        pytest.skip(
            "REF_ABSENT: the audit worktree fetches only the accepted base "
            "and the current team ref; the committed diagnosis remains the "
            "evidence of record and is checked structurally above")
    fresh = rsd.run(RESUMED_RUN_ID, PREDECESSOR_RUN_ID, RAW)
    art = _load(DIAG)
    assert _without_timestamps(fresh) == _without_timestamps(art)
    assert fresh["durable_delta"]["snapshot_head"] != (
        fresh["durable_delta"]["predecessor_head"])


# ---------------------------------------------------------------------------
# 3. Lane deliverable: v68 rejection leg and bounded slice
# ---------------------------------------------------------------------------

def test_d2_before_after_bytes_show_the_rejection_leg() -> None:
    before_bundle = _load(BEFORE)
    after_bundle = _load(AFTER)
    before = _row(before_bundle, D2_DECISION)
    after = _row(after_bundle, D2_DECISION)
    assert before is not None and after is not None
    assert before["counter_evidence_verified"] is True
    assert after["counter_evidence_verified"] is False
    assert after["counter_evidence_unevidenced_reason"] == "pivot_absent"
    # The defective trilingual head is preserved verbatim for visibility; it
    # is the verification flag that changed, not the evidence text.
    assert before["counter_evidence"] == after["counter_evidence"]
    assert before_bundle["provenance"]["counter_evidence_span"][
        "applied"] is True
    assert after_bundle["provenance"]["counter_evidence_span"][
        "applied"] is True
    assert after_bundle["provenance"]["counter_evidence_span"][
        "n_selected"] == 0


def test_fixed_path_family_has_zero_defects_and_keeps_the_sound_row() -> None:
    cf = _load(CONTENT_FAMILY)
    fp = cf["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 29
    assert fp["n_decisions"] == 2900
    assert fp["n_verified"] == 20
    assert fp["n_verified_defective"] == 0
    assert set(fp["defect_histogram"].values()) == {0}
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert cf["confirmed_set"]["still_verified"] is True
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True


def test_progressive_slice_artifact_still_passes_within_budget() -> None:
    art = _load(SMOKE)
    assert art["schema"] == "product-progressive-smoke/1"
    assert art["run_id"] == CURRENT_RUN_ID
    assert art["verdict"] == "PASS", art.get("failures")
    assert art["checks_passed"] == art["checks_total"] == 23
    assert art["mode"].startswith("fixture")
    t = art["timings_s"]
    assert t["server_boot_s"] < 3.0, t
    assert t["start_s"] < 1.0, t
    by_name = {c["check"]: c for c in art["checks"]}
    assert by_name["start_first_page_nonempty"]["detail"] >= 100
    assert by_name["start_has_clusters"]["detail"] >= 5
    assert by_name["start_points_have_xy"]["detail"] == "100/100"
    assert by_name["answer_has_citations"]["detail"] >= 1
    assert by_name["counter_status_rows_present"]["ok"] is True


# ---------------------------------------------------------------------------
# 4. Audit readiness dossier
# ---------------------------------------------------------------------------

def test_audit_readiness_artifact_covers_every_claim_and_passes() -> None:
    art = _load(READINESS)
    assert art["schema"] == ar.SCHEMA
    assert art["run_id"] == CURRENT_RUN_ID
    assert art["resumed_run_id"] == RESUMED_RUN_ID
    assert art["direction_version"] == DIRV
    assert art["overall_status"] == "PASS"
    assert art["failed_checks"] == []
    statuses = {c["id"]: c["status"] for c in art["checks"]}
    assert statuses == {
        "state_contract": "PASS",
        "posture": "PASS",
        "resumed_diagnosis": "PASS",
        "claim_artifacts": "PASS",
        "audit_namespace": "PASS",
        "progressive_smoke": "PASS",
        "mvp_core_tests": "PASS",
    }
    claim_checks = {c["check"] for c in art["claims"]}
    assert claim_checks <= set(statuses)
    assert art["posture"]["gate_minted"] is False
    assert art["posture"]["run_label"] == "UNADJUDICATED"
    # The dossier must not be an audit artifact.
    assert "results/audit/" not in json.dumps(art.get("audit_entry_points", {}))
    assert (REPO_ROOT / "results" / "audit" / "product"
            / f"CYCLE_{CURRENT_RUN_ID}_GATE.json").exists() is False


def test_lightweight_checks_reproduce_now() -> None:
    committed = _load(READINESS)
    fresh = ar.run(CURRENT_RUN_ID, include_tests=False, include_smoke=False)
    fast_ids = ("state_contract", "posture", "resumed_diagnosis",
                "claim_artifacts", "audit_namespace")
    for check_id in fast_ids:
        old = next(c for c in committed["checks"] if c["id"] == check_id)
        new = next(c for c in fresh["checks"] if c["id"] == check_id)
        assert old["status"] == new["status"] == "PASS", check_id
    assert fresh["overall_status"] == "PARTIAL"
    assert set(fresh["skipped_checks"]) == {"progressive_smoke",
                                            "mvp_core_tests"}


def test_bounded_test_set_exists_and_excludes_ref_dependent_cycles() -> None:
    for rel in ar.MVP_CORE_TESTS:
        assert (REPO_ROOT / rel).is_file(), rel
    assert not any("test_cycle_" in rel for rel in ar.MVP_CORE_TESTS), (
        "historical cycle tests assert predecessor git refs that the audit "
        "worktree does not fetch; keep the bounded set ref-free")


# ---------------------------------------------------------------------------
# 5. Posture and namespace
# ---------------------------------------------------------------------------

def test_state_records_this_resume_and_stays_fail_closed() -> None:
    st = _load(STATE)
    block = st["cycle_40200882831_operational_resume"]
    assert block["resumed_run"] == RESUMED_RUN_ID
    assert block["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert block["orchestration_failure_of_record"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert block["orchestration_failure_of_record"]["mechanism"] == (
        "OBSERVED_QUANTUM_EXPIRED")
    assert block["accepted_this_cycle"] is False
    assert st["lane"] == "product"
    assert st["direction_version"] == DIRV
    assert st["cycle_status"] == "COMPLETE"
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    # The pointer legitimately advances; this run's claim is that it still
    # names a run with BOTH halves of requirement 4.  Likewise the next
    # recommendation evolves, so assert it still names a next action rather
    # than a cycle id that later hops necessarily replace.
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, REPO_ROOT)
    assert not pointer["problems"], pointer
    assert "NEXT:" in st["next_recommendation"]
    assert "audit" in st["next_recommendation"].lower() or (
        "resume" in st["next_recommendation"].lower())


def test_no_producer_audit_namespace_write_for_this_run() -> None:
    gate = (REPO_ROOT / "results" / "audit" / "product"
            / f"CYCLE_{CURRENT_RUN_ID}_GATE.json")
    report = (REPO_ROOT / "reports" / "audit" / "product"
              / f"CYCLE_{CURRENT_RUN_ID}.md")
    assert not gate.exists()
    assert not report.exists()
    pending = _git("status", "--porcelain", "-uall").stdout.splitlines()
    bad = [line[3:] for line in pending
           if line[3:].startswith(("results/audit/product/",
                                   "reports/audit/product/"))]
    assert bad == []
