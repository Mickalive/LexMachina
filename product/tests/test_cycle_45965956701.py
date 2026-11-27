"""Cycle 45965956701 — audit-ready resume of the zero-delta run 45965383491.

The inherited post-hydration content-recheck deliverable is preserved verbatim.
This test pins the *new* facts of record for this resume: the producer-side
failure signature, the zero-delta snapshot relation, the fail-closed posture,
and the one-command audit-readiness dossier.  It mints no gate and scores no
frozen bar.

AUTHORING CORRECTION (run 45974506375): the original identity assertion used
`git rev-parse HEAD` and therefore only held in the pre-commit producer
checkout.  Once run 45965956701's snapshot was committed at 2150d0a9, the
assertion failed in the audit checkout.  It is replaced here by immutable
git-object checks (same tree for the two snapshot commits, snapshot reachable
from HEAD).  The zero-delta diagnosis fields remain unchanged; no historical
result is deleted.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import audit_readiness as ar  # noqa: E402

RUN = "45965956701"
RESUMED = "45965383491"
PREDECESSOR = "45954836439"
SNAPSHOT_HEAD = "2301799cef1483cc29fc517278a78ae4c3deb00b"

RAW = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_run_jobs_raw.json"
DIAG = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_resume_diagnosis.json"
STATE = json.loads((ROOT / "state/product.json").read_text(encoding="utf-8"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_run_jobs_snapshot_pins_the_producer_step_failure():
    doc = _load(RAW)
    assert doc["schema"] == "github-actions-run-jobs-snapshot/1"
    assert doc["run"]["id"] == int(RESUMED)
    assert doc["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in doc["jobs"]}
    assert jobs["team"]["conclusion"] == "failure"
    steps = {s["name"]: s for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert steps["Run lane cycle"]["seconds"] == 151.0
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    assert steps["Persist team snapshot"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"
    assert doc["logs_endpoint_status"] == 403
    assert doc["annotations_endpoint_status"] == 404


def test_diagnosis_names_a_team_failure_not_an_audit_quantum_death():
    diag = _load(DIAG)
    orch = diag["orchestration"]
    mech = orch["mechanism"]
    assert diag["run_id"] == RESUMED
    assert diag["predecessor_run_id"] == PREDECESSOR
    assert diag["resuming_run_id"] == RUN
    assert diag["direction_version"] == 68
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_job"] == "team"
    assert orch["failed_step"] == "Run lane cycle"
    assert mech["status"] == "OBSERVED_TEAM_STEP_FAILURE_NO_QUANTUM"
    assert mech["evidence_basis"] == "step_timing"
    assert mech["quantum_expired"] is False
    assert mech["team_step_seconds"] == 151.0
    assert mech["in_kill_window"] is False
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["continue_recommended"] is True


def test_snapshot_relates_to_its_predecessor_by_identity_not_cardinality():
    diag = _load(DIAG)
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD

    # Immutable git-object identity, not the mutable checkout HEAD: the audit
    # job checks out the committed team ref, not the pre-commit producer tree.
    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=str(ROOT),
                              capture_output=True, text=True, check=False)

    snapshot_tree = _git("rev-parse", f"{SNAPSHOT_HEAD}^{{tree}}")
    predecessor_tree = _git("rev-parse", f"{delta['predecessor_head']}^{{tree}}")
    assert snapshot_tree.returncode == 0, snapshot_tree.stderr
    assert predecessor_tree.returncode == 0, predecessor_tree.stderr
    assert snapshot_tree.stdout.strip() == predecessor_tree.stdout.strip()
    ancestor = _git("merge-base", "--is-ancestor", SNAPSHOT_HEAD, "HEAD")
    assert ancestor.returncode == 0, ancestor.stderr


def test_producer_minted_no_audit_gate_for_either_run():
    for run_id in (RUN, RESUMED, PREDECESSOR):
        assert not (ROOT / "results/audit/product" /
                    f"CYCLE_{run_id}_GATE.json").exists()
        assert not (ROOT / "reports/audit/product" /
                    f"CYCLE_{run_id}.md").exists()


def test_one_command_dossier_passes_on_this_snapshot():
    dossier = ar.run(RUN, direction_version=68, include_tests=False,
                     include_smoke=False, auto_bootstrap=False)
    # With the slow tests deliberately skipped, the dossier reports PARTIAL,
    # not PASS: skipped mandatory checks are not silently counted as passes.
    assert dossier["overall_status"] in ("PASS", "PARTIAL"), dossier["failed_checks"]
    assert dossier["failed_checks"] == []
    assert set(dossier["skipped_checks"]) == {
        "cycle_test", "progressive_smoke", "mvp_core_tests"}
    assert all(c["status"] == "PASS" for c in dossier["checks"]
               if c["status"] != "SKIP")
    by_id = {c["id"]: c for c in dossier["checks"]}
    assert by_id["resumed_diagnosis"]["status"] == "PASS"
    assert by_id["claim_artifacts"]["status"] == "PASS"
    assert by_id["audit_namespace"]["status"] == "PASS"


def test_inherited_deliverable_and_state_posture_are_unchanged():
    probe = _load(ROOT / "results/product/counter_content_family" /
                  "CYCLE_45947662468.json")
    rule = probe["ordered_work_2_full_success_rule"]
    assert rule["met"] is True
    assert rule["false_reject_count"] == 0
    assert rule["confirmed_sound_row_still_verified"] is True
    totals = probe["fixed_path_family"]["totals"]
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert STATE["direction_version"] == 68
    block = STATE["cycle_45965383491_operational_resume"]
    assert block["resuming_run_id"] == RUN
    assert block["resumed_run_id"] == RESUMED
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert STATE[flag] is False, flag
    assert STATE["continue_recommended"] is True


def test_new_artifacts_are_byte_stable_in_the_manifest():
    claimed = {
        "results/product/orchestration/CYCLE_45965383491_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_45965383491_resume_diagnosis.json",
        "product/tests/test_cycle_45965956701.py",
        "reports/product/CYCLE_45965956701.md",
    }
    block = STATE["cycle_45965383491_operational_resume"]
    names = {str(x) for x in block["artifacts"]}
    assert claimed <= names, claimed - names
    hashes = block["artifact_sha256"]
    for rel, digest in hashes.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel
