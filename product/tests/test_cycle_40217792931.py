"""Executable re-derivation of product cycle 40217792931's resume claims.

Run 40217792931's producer was stopped by the workflow's own 2700 s work
quantum inside *Run lane cycle* (exit 78).  Its validation and write-scope
steps were therefore skipped and the always-run persist step published the
tree it had.  This cycle resumes that snapshot instead of restarting, and —
unlike the two previous resumes — the mechanism is **observed** from public
check-run annotations rather than recorded as unobservable.

Claims are separated on purpose:

1. **Orchestration** - quantum expiry observed from annotations, classification
   from the committed jobs snapshot, no gate minted, run UNADJUDICATED.  The
   attribution repair is asserted directly: a *team*-job expiry must not be
   described as the independent-audit agent's.
2. **Durable delta** - 15 committed files over 40211497166, of which the five
   regenerated offline-slice bundles are verified with the shipped validator.
3. **Lane deliverable** - progressive slice PASS 23/23 inside the local
   budgets, bounded MVP set green, posture fail-closed.
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
from product.query.bundle import validate_bundle          # noqa: E402

CURRENT_RUN_ID = "40217792931"
RESUMED_RUN_ID = "40217792931"
PREDECESSOR_RUN_ID = "40211497166"
SNAPSHOT_HEAD = "d4e8a862e818eeb84f454f130b9aade159e0f447"
DIRV = 68

ORCH = REPO_ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
OLD_RAW = ORCH / "CYCLE_40193974025_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
READINESS = (REPO_ROOT / "results" / "product" / "audit_readiness"
             / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")
SMOKE = (REPO_ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{RESUMED_RUN_ID}_progressive_smoke.json")
STATE = REPO_ROOT / "state" / "product.json"
NEW_BUNDLE_DIRS = (
    "20261025T174808Z", "20261025T181726Z", "20261025T181736Z",
    "20261025T182837Z", "20261025T182847Z",
)


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


# ---------------------------------------------------------------------------
# 1. Orchestration: the mechanism is OBSERVED from public annotations
# ---------------------------------------------------------------------------

def test_raw_snapshot_carries_public_check_run_annotations() -> None:
    raw = _load(RAW)
    assert str(raw["run"]["id"]) == RESUMED_RUN_ID
    assert raw["run"]["conclusion"] == "failure"
    assert raw["schema"] == "lex-github-run-jobs-snapshot/1"
    assert raw.get("annotation_endpoint_status") == 200
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    anns = raw["annotations"][str(team["id"])]
    messages = [a["message"] for a in anns]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    assert any("exit code 78" in m for m in messages)


def test_quantum_expiry_reclassifies_the_resumed_run_from_annotations() -> None:
    raw = _load(RAW)
    art = _load(DIAG)["orchestration"]
    fresh = asd.classify(raw)

    assert fresh["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert _without_timestamps(fresh) == _without_timestamps(art)

    team = fresh["team"]
    assert team["conclusion"] == "failure"
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 2704.0
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    assert team["producer_state_validation_ran"] is False
    assert team["write_scope_step_ran"] is False

    assert fresh["audit"]["conclusion"] == "skipped"
    assert fresh["audit"]["gate_file_written"] is False
    assert fresh["integrate"]["conclusion"] == "skipped"

    mechanism = fresh["mechanism"]
    assert mechanism["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mechanism["quantum_expired"] is True
    assert mechanism["quantum_seconds"] == 2700
    assert mechanism["exit_code"] == 78
    observed = fresh["observed_failure"]
    assert observed["source"] == "github_actions_check_run_annotations"
    assert observed["annotations_available"] is True
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in observed["quantum_message"]


def test_a_team_quantum_expiry_is_not_attributed_to_the_audit_agent() -> None:
    """Requirement 33: no false attribution in published text.

    The instrument used to name "the independent-audit agent" for every
    quantum expiry.  This run's expiry was the PRODUCER's, and the skipped
    steps were the producer-side validation and write-scope steps.
    """
    rec = asd.classify(_load(RAW))
    attention = rec["adjudication"]["control_plane_attention"]
    assert "lane-cycle (producer) agent" in attention
    assert "independent-audit agent" not in attention
    claim = rec["mechanism"]["claim"]
    assert "independent-audit agent" not in claim
    assert "state validation and write-scope steps" in claim


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
    delta = art["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 15
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert any(p.startswith("results/product/offline_slice/")
               for p in delta["changed_paths_sample"])
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


# ---------------------------------------------------------------------------
# 3. Lane deliverable: regenerated bundles, bounded slice, posture
# ---------------------------------------------------------------------------

def test_every_bundle_the_resumed_producer_regenerated_validates_clean() -> None:
    root = REPO_ROOT / "results" / "product" / "offline_slice"
    seen = 0
    for run_dir in NEW_BUNDLE_DIRS:
        for bundle_path in sorted((root / run_dir).glob("*.bundle.json")):
            seen += 1
            bundle = _load(bundle_path)
            assert validate_bundle(bundle) == [], bundle_path
            assert len(bundle.get("decisions") or []) == 100
            span = (bundle.get("provenance") or {}).get(
                "counter_evidence_span") or {}
            assert span.get("applied") is True, bundle_path
            assert span.get("n_selected") == 0, bundle_path
    assert seen == 5, f"expected 5 regenerated bundles, found {seen}"


def test_progressive_smoke_artifact_still_passes_within_budget() -> None:
    art = _load(SMOKE)
    assert art["schema"] == "product-progressive-smoke/1"
    assert art["run_id"] == RESUMED_RUN_ID
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

def test_audit_readiness_profile_is_selected_by_run_id() -> None:
    assert ar.select_profile("40217792931")[
        "classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert ar.select_profile("40221519475")[
        "resumed_run_id"] == "40217792931"       # alias of the same profile
    assert ar.select_profile("40200882831")[
        "resumed_run_id"] == ar.RESUMED_RUN_ID   # default profile preserved
    assert ar.select_profile("40200882831")[
        "classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"


def test_audit_readiness_artifact_covers_every_claim_and_passes() -> None:
    art = _load(READINESS)
    assert art["schema"] == ar.SCHEMA
    assert art["run_id"] == RESUMED_RUN_ID
    assert art["resumed_run_id"] == RESUMED_RUN_ID
    assert art["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert art["direction_version"] == DIRV
    assert art["overall_status"] == "PASS", art.get("failed_checks")
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
    assert art["resumed_run"]["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert art["resumed_run"]["failed_job"] == "team"
    claim_checks = {c["check"] for c in art["claims"]}
    assert claim_checks <= set(statuses)
    assert art["posture"]["gate_minted"] is False
    assert art["posture"]["run_label"] == "UNADJUDICATED"
    assert "results/audit/" not in json.dumps(art.get("audit_entry_points", {}))
    assert (REPO_ROOT / "results" / "audit" / "product"
            / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists() is False


def test_lightweight_checks_reproduce_now() -> None:
    committed = _load(READINESS)
    fresh = ar.run(RESUMED_RUN_ID, include_tests=False, include_smoke=False)
    fast_ids = ("state_contract", "posture", "resumed_diagnosis",
                "claim_artifacts", "audit_namespace")
    for check_id in fast_ids:
        old = next(c for c in committed["checks"] if c["id"] == check_id)
        new = next(c for c in fresh["checks"] if c["id"] == check_id)
        assert old["status"] == new["status"] == "PASS", check_id
    assert fresh["overall_status"] == "PARTIAL"
    assert set(fresh["skipped_checks"]) == {"progressive_smoke",
                                            "mvp_core_tests"}


# ---------------------------------------------------------------------------
# 5. State and namespace
# ---------------------------------------------------------------------------

def test_state_records_this_resume_and_stays_fail_closed() -> None:
    st = _load(STATE)
    block = st["cycle_40217792931_operational_resume"]
    assert block["resumed_run"] == RESUMED_RUN_ID
    assert block["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert block["recorded_by_run"] == "40221519475"
    failure = block["orchestration_failure_of_record"]
    assert failure["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert failure["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert failure["quantum_seconds"] == 2700
    assert failure["exit_code"] == 78
    assert failure["product_defect"] is False
    assert failure["verdict_written"] is False
    assert block["accepted_this_cycle"] is False
    assert block["durable_delta"]["changed_files"] == 15

    assert st["lane"] == "product"
    assert st["direction_version"] == DIRV
    assert st["cycle_status"] == "COMPLETE"
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    # The pointer and the recommendation both evolve as cycles are accepted;
    # validate the durable invariant (both halves of requirement 4, a named
    # next action) instead of freezing a predecessor's literals.
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, REPO_ROOT)
    assert not pointer["problems"], pointer
    assert "NEXT:" in st["next_recommendation"]
    assert "audit" in st["next_recommendation"].lower() or (
        "resume" in st["next_recommendation"].lower())


def test_no_producer_audit_namespace_write_for_this_run() -> None:
    gate = (REPO_ROOT / "results" / "audit" / "product"
            / f"CYCLE_{RESUMED_RUN_ID}_GATE.json")
    report = (REPO_ROOT / "reports" / "audit" / "product"
              / f"CYCLE_{RESUMED_RUN_ID}.md")
    assert not gate.exists()
    assert not report.exists()
    pending = _git("status", "--porcelain", "-uall").stdout.splitlines()
    bad = [line[3:] for line in pending
           if line[3:].startswith(("results/audit/product/",
                                   "reports/audit/product/"))]
    assert bad == []
