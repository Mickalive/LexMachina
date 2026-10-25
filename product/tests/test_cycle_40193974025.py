"""Executable re-derivation of product cycle 40193974025's diagnosis.

Run 40193974025 is the OPERATIONAL RESUME of the persisted producer snapshot
of that same run: the ``team`` job failed inside *Run lane cycle*, the
``Validate active MVP producer state`` and ``Enforce lane write scope`` steps
were therefore skipped, and ``Persist team snapshot`` - guarded by
``if: always()`` - published the unchanged tree.  Its team ref points at the
predecessor's exact commit (``c6e81324...`` from run 40188639817), so the run
has ZERO durable delta.

The claims below are deliberately separated:

1. **Orchestration** - re-classified from the committed public run/jobs
   snapshot by ``product.audit_step_diagnosis``.  No job logs (403), so no
   provider/auth/quantum mechanism is claimed.
2. **Durable delta** - re-derived from local git refs by
   ``product.resume_snapshot_diagnosis``.  Zero delta is an orchestration
   outcome, never a product defect and never a verdict.
3. **Lane deliverable** - the shipped progressive slice still passes over a
   real socket in fixture mode, and the MVP core suite is green in the
   disclosed environment.
4. **Posture** - the accepted pointer is unchanged, the run is UNADJUDICATED
   (neither half of factory-wide requirement 4 exists for it), and every
   fail-closed flag stays FALSE.

Nothing here writes a gate, scores a frozen bar, or labels a run rejected.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_step_diagnosis as asd              # noqa: E402
from product import resume_snapshot_diagnosis as rsd        # noqa: E402

RUN_ID = "40193974025"
PREDECESSOR_RUN_ID = "40188639817"
DIRV = 68
ORCH = REPO_ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RUN_ID}_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RUN_ID}_resume_diagnosis.json"
SMOKE = (REPO_ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{RUN_ID}_progressive_smoke.json")
STATE = REPO_ROOT / "state" / "product.json"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


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
# 1. Orchestration: team-job failure, not an audit verdict
# ---------------------------------------------------------------------------

def test_team_step_failure_is_reproducible_from_the_raw_snapshot() -> None:
    raw = _load(RAW)
    art = _load(DIAG)["orchestration"]
    assert str(raw["run"]["id"]) == RUN_ID
    assert raw["run"]["conclusion"] == "failure"
    fresh = asd.classify(raw)
    assert fresh["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert fresh["classification"] == art["classification"]
    assert fresh["team"] == art["team"]
    assert fresh["audit"] == art["audit"]
    assert fresh["integrate"] == art["integrate"]
    assert fresh["mechanism"]["status"] == "UNOBSERVED"
    assert fresh["mechanism"]["logs_endpoint_status"] == 403


def test_the_snapshot_was_published_after_the_failed_producer_step() -> None:
    art = _load(DIAG)["orchestration"]
    team = art["team"]
    assert team["conclusion"] == "failure"
    assert team["failed_step"] == "Run lane cycle"
    # The persist step's own conclusion is the fact - the team job failed.
    assert team["team_snapshot_step_conclusion"] == "success"
    assert team["team_snapshot_persisted"] is True
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    # No audit job ever ran, so no gate can exist.
    assert art["audit"]["conclusion"] == "skipped"
    assert art["audit"]["gate_file_written"] is False
    assert art["integrate"]["conclusion"] == "skipped"


def test_gate_file_written_is_true_only_when_the_gate_step_succeeded() -> None:
    raw = _load(RAW)
    # Synthetic audit-success snapshot: gate step actually ran.
    ok = copy.deepcopy(raw)
    team = next(j for j in ok["jobs"] if j["name"] == "team")
    ok["jobs"].append({
        "name": "audit", "conclusion": "success",
        "steps": [
            {"name": "Independent audit", "conclusion": "success"},
            {"name": "Enforce audit scope and read gate", "conclusion": "success"},
            {"name": "Persist audit snapshot", "conclusion": "success"},
        ],
    })
    assert asd.classify(ok)["audit"]["gate_file_written"] is True
    # The real snapshot has no audit job at all.
    assert asd.classify(raw)["audit"]["gate_file_written"] is False
    # And a failed audit job that skipped the gate step is still not a gate.
    failed = copy.deepcopy(raw)
    team = next(j for j in failed["jobs"] if j["name"] == "team")
    team["conclusion"] = "success"
    for step in team["steps"]:
        if step["name"] in ("Run lane cycle", "Validate active MVP producer state",
                            "Enforce lane write scope"):
            step["conclusion"] = "success"
    failed["jobs"].append({
        "name": "audit", "conclusion": "failure",
        "steps": [
            {"name": "Independent audit", "conclusion": "failure"},
            {"name": "Enforce audit scope and read gate", "conclusion": "skipped"},
        ],
    })
    rec = asd.classify(failed)
    assert rec["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    )
    assert rec["audit"]["gate_file_written"] is False


# ---------------------------------------------------------------------------
# 2. Durable delta: the persisted snapshot is the predecessor's bytes
# ---------------------------------------------------------------------------

def test_resume_diagnosis_reproduces_from_committed_snapshot_and_refs() -> None:
    art = _load(DIAG)
    fresh = rsd.run(RUN_ID, PREDECESSOR_RUN_ID, RAW)
    assert fresh["schema"] == art["schema"]
    assert _without_timestamps(fresh) == _without_timestamps(art)


def test_the_snapshot_has_zero_durable_delta_and_the_predecessor_bytes() -> None:
    art = _load(DIAG)["durable_delta"]
    team_ref = f"origin/cycle/core/product/{RUN_ID}/team"
    pred_ref = f"origin/cycle/core/product/{PREDECESSOR_RUN_ID}/team"
    assert _rev(team_ref) is not None, "the team ref must be available"
    assert _rev(pred_ref) is not None, "the predecessor ref must be available"
    assert art["classification"] == "ZERO_DURABLE_DELTA"
    assert art["snapshot_head"] == art["predecessor_head"]
    assert art["changed_files"] == 0
    assert art["changed_paths_sample"] == []
    assert _rev(team_ref) == _rev(pred_ref)


def test_the_run_is_unadjudicated_and_wrote_no_auditor_bytes() -> None:
    art = _load(DIAG)
    audit = art["adjudication"]["audit"]
    accept = art["adjudication"]["accept"]
    assert audit["audit_ref_present"] is False
    assert audit["gate_file_present"] is False
    assert accept["accept_commit"] is None
    assert art["adjudication"]["accepted"] is False
    assert art["adjudication"]["status"] == "UNADJUDICATED"
    assert not (REPO_ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN_ID}_GATE.json").exists()
    # Producer never writes the auditor namespace.  When origin/lab/product
    # is checked out (as the audit job fetches it) the inventory must show no
    # producer-minted file waiting on this unadjudicated chain.
    if art["audit_namespace"].get("accepted_ref_present"):
        assert art["audit_namespace"][
            "producer_minted_unadjudicated_chain"] == []


# ---------------------------------------------------------------------------
# 3. Lane deliverable: the shipped vertical slice still runs
# ---------------------------------------------------------------------------

def test_progressive_slice_still_passes_within_budget() -> None:
    art = _load(SMOKE)
    assert art["schema"] == "product-progressive-smoke/1"
    assert art["verdict"] == "PASS", art.get("failures")
    assert art["checks_passed"] == art["checks_total"] == 23
    assert art["mode"].startswith("fixture")
    t = art["timings_s"]
    assert t["server_boot_s"] < 3.0, t
    assert t["start_s"] < 1.0, t
    # The clickable-map contract: decisions, clusters, coordinates, sources.
    by_name = {c["check"]: c for c in art["checks"]}
    assert by_name["start_first_page_nonempty"]["detail"] >= 100
    assert by_name["start_has_clusters"]["detail"] >= 5
    assert by_name["start_points_have_xy"]["detail"] == "100/100"
    assert by_name["answer_has_citations"]["detail"] >= 1
    assert by_name["counter_status_rows_present"]["ok"] is True


# ---------------------------------------------------------------------------
# 4. Posture
# ---------------------------------------------------------------------------

def test_state_stays_fail_closed_and_the_accepted_pointer_is_unchanged() -> None:
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == DIRV
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    # This run has neither half of requirement 4, so it may not advance the
    # pointer; the pointer still names the last BOTH-halves accepted cycle.
    # Later accepted cycles may advance it, so validate the invariant rather
    # than pinning a literal that is expected to drift.
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, REPO_ROOT)
    assert not pointer["problems"], pointer
    assert st.get("cycle_40193974025_operational_resume"), (
        "the state must record this resume, not silently inherit the predecessor")
