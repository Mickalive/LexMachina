"""Cycle 42983901071: operational resume of snapshot 42976016321.

Run 42955840398 was the last cycle to write a report/state (team job green,
delta 2b343317) but its own independent audit consumed the whole 2700 s work
quantum before writing a gate, so its delta was never adjudicated. Four more
runs followed without a single adjudication: 42964203118 failed at 'Run lane
cycle' after 16 s with exit 1 (mechanism UNOBSERVED, zero durable delta),
42964472484 was team-green with an 11-file cache delta and quantum-expired on
its audit at exit 78, 42970556900 hit the same team-side quantum AFTER
committing a real 7-file delta (the 42964203118/42964472484 raw+diagnoses, the
42964472484 reconciliation and its own PASS progressive smoke) and then wrote
no report or state at all, and 42976016321 - the persisted snapshot this cycle
resumes - had a fully green team job whose producer committed a 37-file
cache/state refresh and then stopped, with its independent audit
quantum-expiring at exit 78 before any gate.

This cycle resumes that snapshot, diagnoses the entire chain from committed
public evidence, finishes the incomplete 42970556900/42976016321 producer
work, repairs the cache-refresh instrument's claim-path defect and makes the
snapshot audit-ready.

These tests pin, against the committed bytes:

1. snapshot 42976016321's orchestration facts (team all-steps-green with the
   37-file cache/state delta, audit failure at 'Independent audit' with
   LEX_WORK_QUANTUM_EXPIRED exit 78, scope/persist skipped, integrate
   skipped);
2. the per-run diagnoses for the whole unadjudicated chain (42964203118
   ZERO_DURABLE_DELTA / UNOBSERVED, 42964472484 COMMITTED_DELTA 11,
   42970556900 COMMITTED_DELTA 7, 42976016321 COMMITTED_DELTA 37, each
   UNADJUDICATED), each sha-pinned to its own raw snapshot;
3. the resumed run's 37-file delta is characterized as 13 added + 23
   modified (6 fetched_at-only, 17 upstream drift) plus a byte-only
   state/product.json re-serialization in `non_cache_paths` - never
   paraphrased as "just timestamps";
4. the repaired cache-refresh instrument records a captured run record
   (captured=true with per-job conclusions and the diagnosis's mechanism)
   while still emitting the historical UNOBSERVED wording for a run whose
   record is genuinely absent from the cited raw;
5. state hygiene: run_history rows exist for every chain run and this cycle,
   the state block records the resume, the accepted pointer is unchanged
   (CYCLE_40284658455 / 7be4480e), every fail-closed posture flag is still
   false, and no producer-minted gate exists for this run.

No frozen bar, rubric, threshold, verdict contract or audit namespace is
touched; this test writes nothing outside pytest's own output.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

ORCH = ROOT / "results/product/orchestration"
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42983901071.md"
SMOKE = ROOT / "results/product/progressive_smoke" / (
    "CYCLE_42983901071_progressive_smoke.json")

# The resumed snapshot and its delta baseline.
RESUMED = 42976016321
PREDECESSOR = 42970556900
SNAPSHOT_HEAD = "ca40f71250d5ba0b894ddc8170d6a0a2b2056a79"
PREDECESSOR_HEAD = "66e4dbcb4fe9ff52cf7a354c35e72f298485e6be"

# The chain between the last reported cycle (42955840398) and this one. Each
# row is (run_id, predecessor_run_id, expected delta classification).
CHAIN = [
    (42964203118, 42955840398, "ZERO_DURABLE_DELTA"),
    (42964472484, 42955840398, "COMMITTED_DELTA"),
    (42970556900, 42964472484, "COMMITTED_DELTA"),
    (42976016321, 42970556900, "COMMITTED_DELTA"),
]


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _diag(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_resume_diagnosis.json")


def _raw(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_run_jobs_raw.json")


def test_snapshot_42976016321_team_green_audit_quantum_no_gate():
    raw = _raw(RESUMED)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == 42983901071
    assert raw["run"]["id"] == RESUMED
    assert raw["run"]["name"] == "Core product dirV68 repair0"
    assert raw["run"]["conclusion"] == "failure"
    assert raw["fetch_failures"] == []
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert len(raw["jobs"]) == 4

    # The producer ran to completion: every team step is green, including
    # state validation and write-scope enforcement.
    team_steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "success"
    assert team_steps["Run lane cycle"] == "success"
    assert team_steps["Validate active MVP producer state"] == "success"
    assert team_steps["Enforce lane write scope"] == "success"
    assert team_steps["Persist team snapshot"] == "success"

    # The failure is the independent audit's work quantum, not the producer.
    audit_steps = {s["name"]: s["conclusion"] for s in jobs["audit"]["steps"]}
    assert jobs["audit"]["conclusion"] == "failure"
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"] == "skipped"
    assert audit_steps["Persist audit snapshot"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"

    block = raw["check_run_annotations_by_job_id"][str(jobs["audit"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("exit code 78" in m for m in messages)
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)


def test_diagnosis_42976016321_37_file_delta_unadjudicated():
    diag = _diag(RESUMED)
    assert diag["run_id"] == str(RESUMED)
    assert diag["predecessor_run_id"] == str(PREDECESSOR)
    orch = diag["orchestration"]
    assert orch["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert orch["mechanism"]["quantum_expired"] is True
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["changed_files"] == 37
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    # The classification is pinned to the committed raw bytes.
    raw_bytes = (ORCH / f"CYCLE_{RESUMED}_run_jobs_raw.json").read_bytes()
    assert diag["raw_snapshot_sha256"] == hashlib.sha256(raw_bytes).hexdigest()


def test_chain_of_record_every_run_diagnosed_and_unadjudicated():
    """Every run between the last reported cycle and this one has a
    committed resume diagnosis pinned to its own raw snapshot, with the
    durable-delta classification reproducible from git refs."""
    for run_id, pred, expected in CHAIN:
        diag = _diag(run_id)
        assert diag["run_id"] == str(run_id), run_id
        assert diag["predecessor_run_id"] == str(pred), run_id
        assert diag["durable_delta"]["classification"] == expected, run_id
        assert diag["adjudication"]["status"] == "UNADJUDICATED", run_id
        assert diag["adjudication"]["accepted"] is False, run_id
        raw = ORCH / f"CYCLE_{run_id}_run_jobs_raw.json"
        assert raw.is_file(), run_id
        assert diag["raw_snapshot_sha256"] == hashlib.sha256(
            raw.read_bytes()).hexdigest(), run_id


def test_42964203118_is_zero_delta_with_an_unobserved_mechanism():
    """The only exit-1 run in the chain: 16 s at 'Run lane cycle', no log
    access, so the mechanism stays UNOBSERVED and the team ref stayed at the
    predecessor's commit."""
    diag = _diag(42964203118)
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 16.0
    # No job logs are downloadable without admin rights, so no provider,
    # auth, timeout or token cause is claimed for this run.
    assert orch["mechanism"]["status"] == "UNOBSERVED"
    assert orch["mechanism"]["quantum_expired"] is False
    assert orch["mechanism"]["exit_code"] == 1
    assert "no provider, auth, timeout or token mechanism is claimed" in \
        orch["mechanism"]["claim"]
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    raw = _raw(42964203118)
    assert raw["fetched_by_run"] == 42970556900
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "failure"
    assert jobs["audit"]["conclusion"] == "skipped"


def test_42970556900_inherited_delta_is_fully_accounted():
    """42970556900 committed exactly seven files and then wrote no report,
    state block or dossier - that incomplete work is what this cycle
    finishes. Nothing in its delta is unaccounted for."""
    diag = _diag(42970556900)
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 7
    assert sorted(delta["changed_paths_sample"]) == [
        "results/product/orchestration/CYCLE_42955840398_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_42964203118_resume_diagnosis.json",
        "results/product/orchestration/CYCLE_42964203118_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_42964472484_cache_refresh_delta.json",
        "results/product/orchestration/CYCLE_42964472484_resume_diagnosis.json",
        "results/product/orchestration/CYCLE_42964472484_run_jobs_raw.json",
        "results/product/progressive_smoke/CYCLE_42970556900_progressive_smoke.json",
    ]
    smoke = _load(ROOT / "results/product/progressive_smoke"
                  / "CYCLE_42970556900_progressive_smoke.json")
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23


def test_new_raw_snapshots_were_captured_by_this_cycle():
    """42970556900's own team job failed before any later run could fetch it,
    so its raw is captured here for the first time."""
    for run_id in (42970556900, RESUMED):
        raw = _raw(run_id)
        assert raw["fetched_by_run"] == 42983901071, run_id
        assert raw["run"]["id"] == run_id, run_id
        assert len(raw["jobs"]) == 4, run_id
        assert raw["fetch_failures"] == [], run_id


def test_cache_refresh_reconciliation_characterizes_the_37_file_delta():
    """The resumed run's delta is 36 cache entries plus a byte-only state
    re-serialization - not 'just timestamps'. Every number below is derived
    from git by the committed instrument."""
    rec = _load(ORCH / f"CYCLE_{RESUMED}_cache_refresh_delta.json")
    assert rec["schema"] == "product-cache-refresh-reconciliation/1"
    assert rec["run_id"] == str(RESUMED)
    assert rec["commit"] == SNAPSHOT_HEAD
    assert rec["base_commit"] == PREDECESSOR_HEAD
    delta = rec["delta"]
    assert delta["n_files"] == 36
    assert delta["n_added"] == 13
    assert delta["n_modified"] == 23
    assert delta["modified_fetched_at_only"] == 6
    assert delta["modified_upstream_drift"] == 17
    assert delta["n_deleted"] == 0
    # The non-cache path is recorded verbatim, never silently dropped.
    assert delta["non_cache_paths"] == ["state/product.json"]
    assert rec["adjudication"]["status"] == "UNADJUDICATED"
    assert rec["adjudication"]["audit_ref_present"] is False
    assert rec["adjudication"]["gate_file_in_tree"] is False
    assert rec["state_run_history"]["present_at_generation_time"] is False
    # The state now carries that row: this cycle finished the producer's
    # incomplete state work (see test_state_hygiene_this_cycle).
    state = _load(STATE)
    history_ids = {r.get("run_id") for r in state["run_history"]}
    assert RESUMED in history_ids


def test_cache_refresh_instrument_records_captured_and_absent_run_records():
    """Requirement-33 repair: when the cited raw snapshot DOES capture the
    run, the artifact must say so (captured=true, per-job conclusions, the
    diagnosis's mechanism) instead of publishing the pruned-record UNOBSERVED
    text; when the record is genuinely absent the historical wording must
    still be emitted unchanged."""
    import cache_refresh_delta as crd

    diag = ORCH / f"CYCLE_{RESUMED}_resume_diagnosis.json"
    raw_captured = ORCH / f"CYCLE_{RESUMED}_run_jobs_raw.json"

    captured = crd.reconcile(str(RESUMED), diag, raw_captured, STATE,
                             remote_check=False)
    gr = captured["github_record"]
    assert gr["captured"] is True
    assert gr["raw_snapshot"] == (
        f"results/product/orchestration/CYCLE_{RESUMED}_run_jobs_raw.json")
    assert gr["run_name"] == "Core product dirV68 repair0"
    assert gr["run_conclusion"] == "failure"
    assert gr["jobs"] == {"team": "success", "audit": "failure",
                          "integrate": "skipped", "resilience": "success"}
    assert "IS captured" in gr["meaning"]
    assert "OBSERVED_QUANTUM_EXPIRED" in gr["meaning"]
    assert "UNOBSERVED" not in gr["meaning"]

    # A raw that does NOT cite this run: captured stays false and the
    # historical UNOBSERVED wording is what a reader gets.
    absent = crd.reconcile(
        str(RESUMED), diag, None, STATE, remote_check=False)
    gr2 = absent["github_record"]
    assert gr2["captured"] is False
    assert "was unavailable when the cited raw snapshot was captured" in \
        gr2["meaning"]
    assert "UNOBSERVED" in gr2["meaning"]


def test_state_hygiene_this_cycle():
    state = _load(STATE)
    assert state["current_cycle_run_id"] == 42983901071
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    # Every chain run and this cycle now has a run_history row.
    history_ids = {r.get("run_id") for r in state["run_history"]}
    for run_id, _, _ in CHAIN:
        assert run_id in history_ids, run_id
    assert 42983901071 in history_ids
    # The resume state block exists and names the resumed snapshot.
    block = state["cycle_42983901071_operational_resume"]
    assert block["run_id"] == 42983901071
    assert block["resumed_run"] == str(RESUMED)
    assert block["predecessor_run_id"] == PREDECESSOR
    assert block["direction_version"] == 68
    assert block["mode"].startswith("OPERATIONAL RESUME")
    assert block["orchestration_failure_of_record"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    chain_ids = {row["run_id"]
                 for row in block["chain_since_last_reported_cycle"]}
    assert chain_ids >= {run_id for run_id, _, _ in CHAIN}
    # Accepted pointer unchanged: no run after 40284658455 has both halves
    # of requirement 4.
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    # Posture stays fail-closed.
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert state[flag] is False, flag
    assert state["continue_recommended"] is True


def test_no_producer_minted_gate_for_this_run():
    gate = ROOT / "results/audit/product/CYCLE_42983901071_GATE.json"
    assert not gate.exists()
    audit_report = ROOT / "reports/audit/product/CYCLE_42983901071.md"
    assert not audit_report.exists()


def test_progressive_smoke_artifact_for_this_run():
    art = _load(SMOKE)
    assert art["verdict"] == "PASS"
    assert art["checks_passed"] == art["checks_total"] == 23
    timings = art["timings_s"]
    assert timings["server_boot_s"] < 3.0
    assert timings["start_s"] < 1.0


def test_lane_deliverable_spot_checks():
    """The inherited one-command clickable slice is intact on the resumed
    bytes: the committed offline bundles still validate under the product's
    own bundle contract (full clickable-slice server behaviour is covered by
    product/tests/test_bundle_preload.py, re-run in the MVP core set)."""
    from product.query.bundle import validate_bundle

    for name in ("rent-default", "petty-theft-dismissal",
                 "corporate-criminal-liability", "business-judgment-rule"):
        path = (ROOT / "results/product/offline_slice"
                / "CYCLE_42794322956" / f"{name}.bundle.json")
        bundle = _load(path)
        validate_bundle(bundle)
        assert len(bundle["decisions"]) >= 100
        assert len(bundle["clusters"]) >= 8


def test_report_exists_and_names_the_chain():
    text = REPORT.read_text(encoding="utf-8")
    for run_id, _, _ in CHAIN:
        assert str(run_id) in text, run_id
    assert "42983901071" in text
    assert "UNADJUDICATED" in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
