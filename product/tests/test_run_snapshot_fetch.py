"""The public run/jobs snapshot capture is reproducible and self-consistent.

Run 42794322956 exposed the failure mode this pins: its raw snapshot was
regenerated after its diagnosis was written, so the diagnosis pinned a sha the
committed raw no longer had.  A committed capture function with an injectable
fetcher makes that class of drift visible in a test instead of during an audit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

from product.run_snapshot_fetch import build_snapshot
import audit_step_diagnosis as asd


PRIMARY = 42808654760
HISTORY = 42798377691


def _step(number, name, conclusion, start="2026-11-10T11:35:10Z",
          end="2026-11-10T11:35:11Z"):
    return {"name": name, "status": "completed", "conclusion": conclusion,
            "number": number, "started_at": start, "completed_at": end}


def _team_job(rid, check_run_id):
    return {
        "id": check_run_id, "run_id": rid, "name": "team",
        "status": "completed", "conclusion": "failure",
        "started_at": "2026-11-10T11:35:09Z",
        "completed_at": "2026-11-10T11:38:35Z",
        "html_url": "https://example.invalid/team",
        "check_suite_id": 1,
        "steps": [
            _step(1, "Set up job", "success"),
            _step(6, "Run lane cycle", "failure"),
            _step(7, "Validate active MVP producer state", "skipped"),
            _step(9, "Enforce lane write scope", "skipped"),
            _step(10, "Persist team snapshot", "success"),
        ],
    }


def _skipped_job(rid, name, check_run_id):
    return {
        "id": check_run_id, "run_id": rid, "name": name,
        "status": "completed", "conclusion": "skipped",
        "started_at": "2026-11-10T11:38:36Z",
        "completed_at": "2026-11-10T11:38:35Z",
        "html_url": "https://example.invalid/" + name,
        "check_suite_id": 1, "steps": [],
    }


def _run(rid, sha, created):
    return {"id": rid, "name": "Core product dirV68 repair0",
            "status": "completed", "conclusion": "failure",
            "head_branch": "main", "head_sha": sha,
            "path": ".github/workflows/core-lane.yml",
            "event": "workflow_dispatch", "created_at": created,
            "updated_at": created, "run_number": 1, "check_suite_id": 1,
            "html_url": "https://example.invalid/run/" + str(rid)}


def _fake_fetch():
    annotations = {
        129804225302: [
            {"annotation_level": "failure",
             "message": "Process completed with exit code 67."},
            {"annotation_level": "failure", "message": "LEX_ZERO_DELTA_REPAIR"},
        ],
        129778723764: [
            {"annotation_level": "failure",
             "message": "Process completed with exit code 78."},
            {"annotation_level": "warning",
             "message": "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2541"},
        ],
    }

    def fetch(url: str):
        if "/actions/runs/" in url and url.endswith(str(PRIMARY)):
            return 200, _run(PRIMARY, "cd16ba45", "2026-11-10T11:35:02Z")
        if "/actions/runs/" in url and url.endswith(str(HISTORY)):
            return 200, _run(HISTORY, "a1ce2eb9", "2026-11-10T10:20:59Z")
        if f"/actions/runs/{PRIMARY}/jobs" in url:
            return 200, {"jobs": [
                _team_job(PRIMARY, 129804225302),
                _skipped_job(PRIMARY, "audit", 129805808520),
                _skipped_job(PRIMARY, "integrate", 129805807857),
            ]}
        if f"/actions/runs/{HISTORY}/jobs" in url:
            audit = dict(_team_job(HISTORY, 129778723764))
            audit.update({"name": "audit", "conclusion": "failure",
                          "steps": [_step(5, "Independent audit", "failure")]})
            team = dict(_team_job(HISTORY, 129769305829))
            team.update({"conclusion": "success",
                         "steps": [_step(6, "Run lane cycle", "success")]})
            return 200, {"jobs": [team, audit]}
        for check_run_id, rows in annotations.items():
            if f"/check-runs/{check_run_id}/annotations" in url:
                return 200, rows
        return 404, {}

    return fetch


def test_snapshot_shape_is_the_canonical_raw_v2_contract():
    snap = build_snapshot(
        PRIMARY, fetched_by_run=42809155715, history_run_ids=(HISTORY,),
        fetch=_fake_fetch(), fetched_at="2026-11-10T12:00:00Z",
    )
    assert snap["schema"] == "product-run-jobs-raw/2"
    assert snap["fetched_by_run"] == 42809155715
    assert snap["run"]["id"] == PRIMARY
    assert set(snap["runs"]) == {str(PRIMARY), str(HISTORY)}
    # the primary run owns the per-job map; history may not overwrite it
    assert {j["id"] for j in snap["jobs"]} == {129804225302, 129805808520,
                                               129805807857}
    assert snap["check_run_annotations_by_job_id"]["129804225302"]["annotations"] == [
        ["failure", "Process completed with exit code 67."],
        ["failure", "LEX_ZERO_DELTA_REPAIR"],
    ]
    # chain is oldest -> newest and carries the predecessor's audit expiry
    chain = {row["run_id"]: row for row in snap["chain_of_record"]}
    assert list(chain) == [HISTORY, PRIMARY]
    assert chain[HISTORY]["jobs"]["audit"]["conclusion"] == "failure"
    assert any("LEX_WORK_QUANTUM_EXPIRED" in m
               for m in chain[HISTORY]["jobs"]["audit"]["annotations"])
    assert chain[PRIMARY]["jobs"]["team"]["annotations"][-1] == \
        "LEX_ZERO_DELTA_REPAIR"


def test_captured_snapshot_reclassifies_to_the_observed_zero_delta_guard():
    snap = build_snapshot(
        PRIMARY, fetched_by_run=42809155715, history_run_ids=(HISTORY,),
        fetch=_fake_fetch(), fetched_at="2026-11-10T12:00:00Z",
    )
    cls = asd.classify(snap)
    assert cls["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert cls["mechanism"]["status"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert cls["mechanism"]["zero_delta_repair"] is True
    assert cls["mechanism"]["exit_code"] == 67
    assert cls["mechanism"]["quantum_expired"] is False
    assert cls["observed_failure"]["zero_delta_message"] == \
        "LEX_ZERO_DELTA_REPAIR"


def test_missing_history_run_is_recorded_not_invented():
    def fetch(url: str):
        if "/actions/runs/" in url and url.endswith(str(HISTORY)):
            return 404, {}
        return _fake_fetch()(url)

    snap = build_snapshot(
        PRIMARY, fetched_by_run=42809155715, history_run_ids=(HISTORY,),
        fetch=fetch, fetched_at="2026-11-10T12:00:00Z",
    )
    assert str(HISTORY) not in snap["runs"]
    assert {"run_id": HISTORY, "what": "run", "status": 404} in \
        snap["fetch_failures"]
    assert [row["run_id"] for row in snap["chain_of_record"]] == [PRIMARY]
