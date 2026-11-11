"""Cycle 42931129328: operational resume of zero-delta snapshot 42930681665.

Run 42820069517 committed a real but narrow query-cache delta (44 rows) and
then stopped without a report, state block or dossier; its public GitHub run
record was pruned before any snapshot could capture it. Run 42930681665 was
dispatched to resume that snapshot, found nothing to do and was rejected by the
workflow's own zero-delta guard (exit 67). This cycle resumes 42930681665's
persisted snapshot, diagnoses both runs from committed evidence, reconciles
the unreported commit into the chain of record and re-verifies the lane
deliverable end to end.

These tests pin, against the committed bytes:

1. snapshot 42930681665's orchestration facts (zero-delta exit 67, state
   validation/write-scope skipped, always-run persist republished 49a276d9)
   and the pruned GitHub records for the history runs it could not fetch;
2. the diagnosis for 42930681665 (ZERO_DURABLE_DELTA over 42820069517,
   UNADJUDICATED) and for 42820069517 (RAW_SNAPSHOT_UNAVAILABLE,
   COMMITTED_DELTA 44 files, UNADJUDICATED);
3. the cache-refresh reconciliation: the 44-file delta is characterized as 34
   modified (5 fetched_at-only, 29 upstream OpenCaseLaw drift) + 10 new
   entries, reproduced from git by the committed instrument, with no
   mechanism asserted for why the run stopped;
4. state hygiene: the new cycle ids, the previously-missing 42820069517
   run_history row, accepted pointer untouched, every fail-closed posture
   flag still false, and no producer-minted gate for this run.

No frozen bar, rubric, threshold, verdict contract or audit namespace is
touched; this test writes nothing outside pytest's own output.
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

RAW = ROOT / "results/product/orchestration/CYCLE_42930681665_run_jobs_raw.json"
DIAG = ROOT / ("results/product/orchestration/"
               "CYCLE_42930681665_resume_diagnosis.json")
DIAG_PRED = ROOT / ("results/product/orchestration/"
                    "CYCLE_42820069517_resume_diagnosis.json")
RECON = ROOT / ("results/product/orchestration/"
                "CYCLE_42820069517_reconciliation.json")
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42931129328.md"
SNAPSHOT_HEAD = "49a276d92642d99cd88db52721e6476e344dd237"
PRED_HEAD = "ef7abc7d9d75214afc04a9d646dccbec62151494"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_snapshot_42930681665_is_the_observed_zero_delta_guard():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == 42931129328
    assert raw["run"]["id"] == 42930681665
    assert raw["run"]["name"] == "Core product dirV68 repair0"
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert len(raw["jobs"]) == 4
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    assert jobs["team"]["conclusion"] == "failure"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"

    block = raw["check_run_annotations_by_job_id"][str(jobs["team"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert any("exit code 67" in m for m in messages)

    # The history runs were pruned from the public API before this snapshot
    # was captured; the fetcher recorded the 404s instead of inventing data.
    failures = {str(f["run_id"]): f for f in raw["fetch_failures"]}
    for run_id in ("42820069517", "42809155715", "42808654760"):
        assert failures[run_id]["status"] == 404, run_id


def test_diagnosis_42930681665_pins_zero_delta_over_42820069517():
    import audit_step_diagnosis as asd

    raw = _load(RAW)
    diag = _load(DIAG)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == "42930681665"
    assert diag["predecessor_run_id"] == "42820069517"
    assert diag["raw_snapshot_sha256"] is not None
    cls = asd.classify(raw)
    assert cls["classification"] == diag["orchestration"]["classification"]
    assert cls["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert cls["mechanism"]["status"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert cls["mechanism"]["zero_delta_repair"] is True
    assert cls["mechanism"]["exit_code"] == 67
    assert cls["mechanism"]["quantum_expired"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert delta["snapshot_ref"] == "origin/cycle/core/product/42930681665/team"
    assert delta["predecessor_ref"] == \
        "origin/cycle/core/product/42820069517/team"
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_diagnosis_42820069517_is_unobserved_but_committed():
    diag = _load(DIAG_PRED)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == "42820069517"
    assert diag["predecessor_run_id"] == "42809155715"
    # No public run/jobs snapshot exists for this run, so the mechanism is
    # unobserved rather than narrated.
    assert diag["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert diag["orchestration"]["mechanism_unobserved"] is True
    assert "mechanism" not in diag["orchestration"]
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 44
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PRED_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_reconciliation_characterizes_the_unreported_commit_from_git():
    import cache_refresh_delta as crd

    rec = _load(RECON)
    assert rec["schema"] == "product-cache-refresh-reconciliation/1"
    assert rec["run_id"] == "42820069517"
    assert rec["commit"] == SNAPSHOT_HEAD
    assert rec["base_commit"] == PRED_HEAD

    d = rec["delta"]
    assert d["n_files"] == 44
    assert d["n_modified"] == 34
    assert d["n_added"] == 10
    assert d["n_deleted"] == 0
    assert d["modified_fetched_at_only"] == 5
    assert d["modified_upstream_drift"] == 29
    assert d["added_new_cache_entries"] == 10
    assert d["added_http_status_200"] == 10
    assert d["non_cache_paths"] == []
    assert len(d["per_file"]) == 44
    assert all(r["path"].startswith("results/product/query_cache/")
               for r in d["per_file"])
    # Every characterized row is one of the two honest kinds; the drift rows
    # name which cached fields actually moved.
    for row in d["per_file"]:
        assert row["kind"] in ("fetched_at_only", "upstream_drift",
                               "new_cache_entry"), row
        if row["kind"] == "upstream_drift":
            assert row.get("body_drift", {}).get("changed_keys"), row["path"]

    # The characterization is reproducible from git by the committed
    # instrument on the same two commits the artifact pins.
    fresh = crd.characterize(PRED_HEAD, SNAPSHOT_HEAD)
    for key in ("n_files", "n_modified", "n_added", "n_deleted",
                "modified_fetched_at_only", "modified_upstream_drift",
                "added_new_cache_entries", "added_http_status_200"):
        assert fresh[key] == d[key], key
    assert fresh["upstream_drift_body_key_counts"] == \
        d["upstream_drift_body_key_counts"]

    # The run's public record is cited from the committed raw snapshot, not
    # from memory: a 404 fetch failure for exactly this run id.
    assert rec["github_record"]["raw_snapshot"] == str(
        RAW.relative_to(ROOT))
    assert rec["github_record"]["fetch_failure"] == {
        "run_id": 42820069517, "what": "run", "status": 404}

    # No stop mechanism is asserted and the run stays unadjudicated.
    assert rec["adjudication"]["status"] == "UNADJUDICATED"
    assert rec["adjudication"]["accept_half"]["accept_commit"] is None
    assert rec["adjudication"]["audit_ref_present"] is False
    assert rec["adjudication"]["gate_file_in_tree"] is False
    assert any("UNOBSERVED" in c for c in rec["claim_ceiling"])

    # The remote-ref observation recorded at reconciliation time saw only
    # the team refs and no audit ref for this run.
    remote = rec["remote_refs_observed"]
    assert remote["ok"] is True
    assert remote["has_audit_ref"] is False
    assert remote["refs"] == [
        "refs/heads/cycle/core/product/42820069517/team",
        "refs/heads/cycle/core/product/42820069517/team-attempt-1",
    ]


def test_reconciliation_closed_a_real_state_gap():
    rec = _load(RECON)
    st = _load(STATE)
    # The artifact was generated before the state edit: the run was absent
    # from run_history at generation time...
    assert rec["state_run_history"]["present_at_generation_time"] is False
    # ...and this cycle's state edit added it, closing the gap.
    history = {row["run_id"]: row for row in st["run_history"]}
    assert 42820069517 in history
    assert history[42820069517]["status"] == \
        "UNREPORTED_CACHE_REFRESH_COMMIT_RAW_UNAVAILABLE_RECONCILED"
    assert 42930681665 in history
    assert history[42930681665]["status"] == \
        "ZERO_DURABLE_DELTA_GUARD_EXIT_67_DIAGNOSED"
    assert 42931129328 in history


def test_audit_readiness_profile_pins_this_cycle():
    import audit_readiness as ar
    import pytest

    prof = ar.select_profile("42931129328")
    assert prof["resumed_run_id"] == "42930681665"
    assert prof["predecessor_run_id"] == "42820069517"
    assert prof["mechanism_kind"] == "observed_zero_delta"
    assert prof["delta_kind"] == "zero"
    assert prof["exit_code"] == 67
    assert Path(prof["raw"]) == RAW
    assert Path(prof["resume_diag"]) == DIAG
    assert Path(prof["cache_refresh_reconciliation"]) == RECON
    assert prof["cycle_test"] == "product/tests/test_cycle_42931129328.py"
    assert prof["state_block"] == "cycle_42931129328_operational_resume"
    assert Path(prof["current_report"]) == REPORT

    # 42820069517 deliberately has NO dossier profile: it wrote no dossier of
    # its own, and the instrument refuses to fall back to a default profile
    # instead of silently borrowing one.
    with pytest.raises(SystemExit):
        ar.select_profile("42820069517")


def test_state_hygiene_and_operational_resume_record():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == 42931129328
    block = st["cycle_42931129328_operational_resume"]
    assert block["run_id"] == 42931129328
    assert block["resumed_run"] == "42930681665"
    assert block["predecessor_run_id"] == "42820069517"
    assert block["direction_version"] == 68
    assert block["mode"].startswith("OPERATIONAL RESUME")
    failure = block["orchestration_failure_of_record"]
    assert failure["run_id"] == "42930681665"
    assert failure["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert failure["mechanism"] == "OBSERVED_ZERO_DELTA_GUARD"
    assert failure["exit_code"] == 67
    assert failure["snapshot_head"] == SNAPSHOT_HEAD
    assert failure["durable_delta"] == "ZERO_DURABLE_DELTA"
    assert failure["adjudication"] == "UNADJUDICATED"
    gap = block["unreported_commit_reconciliation"]
    assert gap["run_id"] == "42820069517"
    assert gap["commit"] == SNAPSHOT_HEAD
    assert gap["delta"] == {
        "n_files": 44, "n_modified": 34, "n_added": 10,
        "modified_fetched_at_only": 5, "modified_upstream_drift": 29}
    assert gap["mechanism"] == "UNOBSERVED"
    assert gap["adjudication"] == "UNADJUDICATED"
    assert gap["artifact"] == str(RECON.relative_to(ROOT))

    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"] == \
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert st[flag] is False, flag

    assert REPORT.is_file()
    report = REPORT.read_text(encoding="utf-8")
    for needle in ("42931129328", "42930681665", "42820069517",
                   "ZERO_DURABLE_DELTA", "UNADJUDICATED"):
        assert needle in report, needle


def test_no_producer_minted_gate_for_this_cycle():
    gate = ROOT / "results/audit/product/CYCLE_42931129328_GATE.json"
    report = ROOT / "reports/audit/product/CYCLE_42931129328.md"
    assert not gate.exists()
    assert not report.exists()
