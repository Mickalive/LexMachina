"""Operational resume 40493520783: zero-delta streak diagnosis + deliverable verify.

The resumed producer snapshot of run 40493217504 was byte-identical to its
predecessor ``413eaf0a`` (cycle 40478699159's snapshot), the FOURTH
consecutive repair dispatch that published no durable delta.  This test locks
the diagnosis and this cycle's verification facts:

* all four streak runs failed their team job at ``Run lane cycle``; their
  always-run persist step republished the unchanged tree; audit was skipped
  for every run, so no run in the streak is adjudicated;
* public check-run annotations give exit codes ``1, 1, 67, 1`` - exit 67 is
  the wrapper's ``LEX_ZERO_DELTA_REPAIR`` (producer found nothing to do) and
  exit 1 carries NO wrapper sentinel (log body HTTP 403, mechanism
  UNOBSERVED);
* the streak diagnosis recomputes the launcher's deterministic slot ->
  model selection from the head_sha-pinned model_health blobs: all three
  exit-1 runs selected the same model, while every health blob in the streak
  records ``tool_probe PASS`` for it - an association from public facts, not
  proven causation;
* this cycle's fresh content-family probe re-verifies the v68 ordered-work
  (2) success rule: 50 fixed-path bundles / 5000 decisions, 55 verified rows,
  D2=D3=D4=D1=0, 0 false rejects, sound row still verified;
* the accepted pointer still satisfies both halves of requirement 4 and the
  posture stays fail-closed.

No gate is written here, no run is adjudicated, no log-level cause is
asserted, and no frozen bar, rubric, threshold or serve verdict is touched.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "40493520783"
SNAPSHOT_RUN_ID = "40493217504"
PREDECESSOR_RUN_ID = "40491258620"
STREAK_RUNS = ("40490645980", "40490967419", "40491258620", "40493217504")
SNAPSHOT_HEAD = "413eaf0a1f5b314238c9d8bab97ba4df243b0c5f"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
EXIT_CODES = {"40490645980": 1, "40490967419": 1,
              "40491258620": 67, "40493217504": 1}

ORCH = ROOT / "results" / "product" / "orchestration"
STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
ATTRIBUTION = (ROOT / "results" / "product" / "regression"
               / f"CYCLE_{EXECUTING_RUN_ID}_test_delta_attribution.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
STREAK = (ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_streak_model_slot_diagnosis.json")
DIAG = ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_resume_diagnosis.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=False)


def test_every_streak_run_observably_failed_at_run_lane_cycle_and_persisted() -> None:
    for run in STREAK_RUNS:
        raw = _load(ORCH / f"CYCLE_{run}_run_jobs_raw.json")
        assert raw["run"]["id"] == int(run)
        assert raw["run"]["conclusion"] == "failure"
        assert raw["logs_endpoint_status"] == 403, run
        team = next(j for j in raw["jobs"] if j["name"] == "team")
        steps = {s["name"]: s["conclusion"] for s in team["steps"]}
        assert team["conclusion"] == "failure", run
        assert steps["Run lane cycle"] == "failure", run
        assert steps["Persist team snapshot"] == "success", run
        audit = next(j for j in raw["jobs"] if j["name"] == "audit")
        assert audit["conclusion"] == "skipped", run
        # Public annotations carry the exit code and no wrapper sentinel
        # except the one explicit zero-delta guard.
        messages = [str(a.get("message") or "")
                    for rows in (raw.get("annotations") or {}).values()
                    for a in (rows if isinstance(rows, list) else [])]
        exit_msgs = [m for m in messages if "Process completed with exit code" in m]
        assert exit_msgs, run
        assert f"exit code {EXIT_CODES[run]}." in exit_msgs[0], (run, exit_msgs)
        sentinels = [m for m in messages
                     if "LEX_ZERO_DELTA_REPAIR" in m
                     or "LEX_MODEL" in m or "LEX_NETWORK" in m
                     or "LEX_WORK_QUANTUM" in m]
        if EXIT_CODES[run] == 67:
            assert sentinels and "LEX_ZERO_DELTA_REPAIR" in sentinels[0], run
        else:
            assert not sentinels, (run, sentinels)


def test_resume_diagnosis_classifies_the_resumed_snapshot_honestly() -> None:
    diag = _load(DIAG)
    assert diag["run_id"] == SNAPSHOT_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    assert orch["mechanism"]["status"] == "UNOBSERVED"
    assert orch["mechanism"]["logs_endpoint_status"] == 403
    assert orch["mechanism"]["exit_code"] == 1
    assert orch["mechanism"]["quantum_expired"] is False
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["product_defect"] is False
    # The persisted snapshot really is the predecessor lineage head.
    assert _git("rev-parse", f"origin/cycle/core/product/{SNAPSHOT_RUN_ID}/team"
                ).stdout.strip() == SNAPSHOT_HEAD
    assert _git("rev-parse", f"origin/cycle/core/product/{PREDECESSOR_RUN_ID}/team"
                ).stdout.strip() == SNAPSHOT_HEAD


def test_streak_diagnosis_recomputes_from_committed_public_evidence() -> None:
    art = _load(STREAK)
    assert art["schema"] == "product-streak-model-slot-diagnosis/1"
    assert art["direction_version"] == 68 and art["lane"] == "product"
    assert [r["run_id"] for r in art["runs"]] == list(STREAK_RUNS)
    obs = art["recomputed_observations"]
    assert obs["all_failed_at_run_lane_cycle"] is True
    assert obs["all_snapshots_persisted"] is True
    assert obs["audit_skipped_for_every_run"] is True
    assert obs["pool_identical_across_head_sha_blobs"] is True
    assert obs["exit_code_1_models_all_equal"] is True
    assert obs["exit_code_1_selected_models"] == [
        "opencode/beam-free", "opencode/beam-free", "opencode/beam-free"]
    assert obs["exit_code_67_selected_models"] == [
        "opencode/nemotron-3.5-lightning-free"]
    # Recompute the deterministic slot arithmetic independently.
    from product.streak_slot_diagnosis import slot_model
    for entry in art["runs"]:
        sel = entry["slot_selection"]
        redo = slot_model(entry["run_id"], "product", 68,
                          entry["model_health"]["pool"])
        assert redo == sel, entry["run_id"]
        assert entry["exit_code_from_annotations"] == EXIT_CODES[entry["run_id"]]
        # Every health blob in the streak records a shallow PASS probe for
        # the selected model - the probe-vs-session gap this file discloses.
        assert entry["model_health"]["healthy"] is True
        if entry["slot_selection"]["selected_model"] == "opencode/beam-free":
            # probe facts are quoted from the pinned blob; the pool lists it.
            assert "opencode/beam-free" in entry["model_health"]["pool"]
    assert "UNOBSERVED" in art["mechanism"]["log_level"]
    assert "NOT proven causation" in art["mechanism"]["association_only"]
    assert "requirement 10" in art["route_around"]


def test_content_family_probe_re_verifies_ordered_work_two_success_rule() -> None:
    fam = _load(FAMILY)
    assert fam["run_id"] == int(EXECUTING_RUN_ID) or fam.get("run_id") in (
        int(EXECUTING_RUN_ID), EXECUTING_RUN_ID, None)
    fixed = fam["fixed_path_family"]
    bundles = fixed["bundles"]
    assert len(bundles) == 50
    assert sum(b["n_decisions"] for b in bundles) == 5000
    assert sum(b["n_verified"] for b in bundles) == 55
    assert sum(b["n_verified_defective"] for b in bundles) == 0
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_success_rule"]["defect_histogram_zero_D2_D3_D4"] is True
    assert fam["ordered_work_2_success_rule"]["confirmed_sound_row_still_verified"] is True
    totals = {"D1_empty_evidence": 0, "D2_letterhead_zone": 0,
              "D3_markup_residue": 0, "D4_language_marker_mismatch": 0}
    for b in bundles:
        assert b["defect_histogram"] == totals, b["path"]
    # Historical bundles stay preserved, never rewritten.
    assert fam["historical_population"]["totals"]["n_verified_defective"] > 0


def test_state_is_hygiened_for_this_cycle_and_stays_fail_closed() -> None:
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    assert int(st["current_cycle_run_id"]) == int(EXECUTING_RUN_ID)
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        assert st[key] is False, key
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, ROOT)
    assert pointer["problems"] == [], pointer
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["resumed_run"] == SNAPSHOT_RUN_ID
    assert block["streak_runs"] == list(STREAK_RUNS)
    assert block["accepted_this_cycle"] is False
    assert block["posture"]["human_gate_ready"] is False
    hist = st["run_history"]
    assert EXECUTING_RUN_ID in str(hist[-1]) or any(
        str(EXECUTING_RUN_ID) in str(h) for h in hist[-3:]), hist[-3:]


def test_report_and_attribution_are_published_and_quoted_consistently() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert SNAPSHOT_RUN_ID in text and "ZERO_DURABLE_DELTA" in text
    assert "UNADJUDICATED" in text
    attr = _load(ATTRIBUTION)
    line = attr["decomposition_line"]
    assert line and line in text, "the report must quote the attribution line verbatim"
    assert attr["working_tree"]["collected_total"] is not None
    # Per-commit deltas sum to the published total (same predicate cycle_verify
    # applies).
    assert sum(s.get("collected_delta_vs_previous_step", 0)
               for s in attr.get("steps", [])) == attr.get("observed_collected_delta")


def test_two_stale_historical_cycle_tests_were_repaired_not_weakened() -> None:
    """The exact pins this cycle would turn red were converted to contracts."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest",
         "product/tests/test_cycle_40429931848_resume.py",
         "product/tests/test_cycle_40247189361.py", "-q", "--no-header"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert out.returncode == 0, (out.stdout[-2000:], out.stderr[-2000:])
    # The monotonic contract is what replaced the equality pin.
    text48 = (ROOT / "product" / "tests"
              / "test_cycle_40429931848_resume.py").read_text(encoding="utf-8")
    assert 'int(st["current_cycle_run_id"]) >= int(EXECUTING_RUN_ID)' in text48
    text61 = (ROOT / "product" / "tests"
              / "test_cycle_40247189361.py").read_text(encoding="utf-8")
    assert "Post-acceptance truth" in text61
    assert 'gate["gate"] == "PASS"' in text61


def test_the_v68_p0_tests_and_bounded_mvp_core_stay_green() -> None:
    """The deliverable this snapshot preserves must still be runnable green."""
    from product.audit_readiness import MVP_CORE_TESTS
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *MVP_CORE_TESTS, "-q", "--no-header"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert out.returncode == 0, (out.stdout[-3000:], out.stderr[-1000:])


def test_dossier_profile_is_registered_for_this_run() -> None:
    from product import audit_readiness as ar
    profile = ar.PROFILES.get(EXECUTING_RUN_ID)
    assert profile, "a run profile must exist before dossier generation"
    assert profile.get("cycle_test", "").endswith("test_cycle_40493520783.py")
    if DOSSIER.is_file():  # present only after the dossier is generated last
        rec = _load(DOSSIER)
        assert rec.get("run_id") in (int(EXECUTING_RUN_ID), EXECUTING_RUN_ID)


def test_no_auditor_namespace_path_was_written_by_this_producer() -> None:
    from product.state_contract import audit_artifact_violations, git_status_paths
    status = git_status_paths(ROOT)
    violations = audit_artifact_violations(
        [p for p in status if p.startswith(("results/audit", "reports/audit"))])
    # The producer never writes results/audit/** or reports/audit/**; any
    # pre-existing committed file is history, not this cycle's write.
    assert violations == [], violations
    own = [p for p in status
           if p.startswith(("results/audit/", "reports/audit/"))
           and EXECUTING_RUN_ID in p]
    assert own == [], own
