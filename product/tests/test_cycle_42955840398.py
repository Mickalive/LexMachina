"""Cycle 42955840398: operational resume of snapshot 42949721176.

Run 42931129328 was the last cycle to write a report/state (team job green,
delta 25af4ca1) but its own independent audit consumed the whole 2700 s work
quantum before writing a gate, so its delta was never adjudicated. Seven more
runs followed without a single adjudication: 42939030694 and 42939338810
failed at 'Run lane cycle' with exit 1 (zero durable delta), 42939662796 hit
the same team-side work-quantum expiry AFTER committing a real 3-file delta
(the 42939338810 raw+diagnosis and its own progressive smoke), 42945255785 /
42945527654 / 42949488384 failed with exit 1 (42945527654 shows a
LEX_MODEL_ROTATE annotation), and 42949721176 — the persisted snapshot this
cycle resumes — had a fully green team job (all twelve steps success) whose
producer committed exactly two raw run/jobs captures and then stopped, with
its independent audit quantum-expiring at exit 78 before any gate.

This cycle resumes that snapshot, diagnoses the entire chain from committed
public evidence, closes the two chain-of-record gaps (42930240440,
42939030694 — runs absent from every previously committed raw), re-verifies
the inherited lane deliverable and makes the snapshot audit-ready.

These tests pin, against the committed bytes:

1. snapshot 42949721176's orchestration facts (team all-steps-green with the
   2-file raw-capture delta, audit failure at 'Independent audit' with
   LEX_WORK_QUANTUM_EXPIRED exit 78, gate/scope/persist skipped, integrate
   skipped);
2. the per-run diagnoses for the whole unadjudicated chain: 42930240440,
   42939030694, 42939338810, 42939662796, 42945255785, 42945527654,
   42949488384 (each ZERO_DURABLE_DELTA or COMMITTED_DELTA as observed from
   git refs, each UNADJUDICATED) and the resumed 42949721176 (COMMITTED_DELTA
   2 files, audit quantum, UNADJUDICATED);
3. 42939662796's inherited 3-file delta is exactly the 42939338810
   raw+diagnosis plus its own PASS progressive smoke artifact — no
   unaccounted bytes;
4. state hygiene: run_history rows exist for every chain run and this cycle,
   the state block records the resume, the accepted pointer is unchanged
   (CYCLE_40284658455 / 7be4480e), every fail-closed posture flag is still
   false, and no producer-minted gate exists for this run.

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

ORCH = ROOT / "results/product/orchestration"
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42955840398.md"

# The resumed snapshot and its delta baseline.
RESUMED = 42949721176
PREDECESSOR = 42949488384
SNAPSHOT_HEAD = "bdd1bdec790558ee4857320984c59acc92d77c6e"
PREDECESSOR_HEAD = "d290d307da7f9c620ea6afda64af7f9890ab4440"

# The chain between the last reported cycle and this one. Each row is
# (run_id, predecessor_run_id, expected delta classification).
CHAIN = [
    (42930240440, 42820069517, "ZERO_DURABLE_DELTA"),
    (42931129328, None, "TEAM_GREEN_AUDIT_QUANTUM"),  # reported cycle, no resume diag
    (42939030694, 42931129328, "ZERO_DURABLE_DELTA"),
    (42939338810, 42931129328, "ZERO_DURABLE_DELTA"),
    (42939662796, 42939338810, "COMMITTED_DELTA"),
    (42945255785, 42939662796, "ZERO_DURABLE_DELTA"),
    (42945527654, 42945255785, "ZERO_DURABLE_DELTA"),
    (42949488384, 42945527654, "ZERO_DURABLE_DELTA"),
    (42949721176, 42949488384, "COMMITTED_DELTA"),
]


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _diag(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_resume_diagnosis.json")


def _raw(run_id: int) -> dict:
    return _load(ORCH / f"CYCLE_{run_id}_run_jobs_raw.json")


def test_snapshot_42949721176_team_green_audit_quantum_no_gate():
    raw = _raw(RESUMED)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == 42955840398
    assert raw["run"]["id"] == RESUMED
    assert raw["run"]["name"] == "Core product dirV68 repair0"
    assert raw["run"]["conclusion"] == "failure"
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


def test_diagnosis_42949721176_two_file_delta_unadjudicated():
    diag = _diag(RESUMED)
    assert diag["run_id"] == str(RESUMED)
    assert diag["predecessor_run_id"] == str(PREDECESSOR)
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert orch["mechanism"]["quantum_expired"] is True
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["changed_files"] == 2
    assert sorted(delta["changed_paths_sample"]) == [
        "results/product/orchestration/CYCLE_42939662796_run_jobs_raw.json",
        "results/product/orchestration/CYCLE_42949488384_run_jobs_raw.json",
    ]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    # The classification is pinned to the committed raw bytes.
    import hashlib

    raw_bytes = (ORCH / f"CYCLE_{RESUMED}_run_jobs_raw.json").read_bytes()
    assert diag["raw_snapshot_sha256"] == hashlib.sha256(raw_bytes).hexdigest()


def test_chain_of_record_every_run_diagnosed_and_unadjudicated():
    """Every run between the last reported cycle and this one has a
    committed resume diagnosis pinned to its own raw snapshot, with the
    durable-delta classification reproducible from git refs."""
    for run_id, pred, expected in CHAIN:
        if pred is None:
            continue  # 42931129328 is the reported cycle, not a resume target
        diag = _diag(run_id)
        assert diag["run_id"] == str(run_id), run_id
        assert diag["durable_delta"]["classification"] == expected, run_id
        assert diag["adjudication"]["status"] == "UNADJUDICATED", run_id
        assert diag["adjudication"]["accepted"] is False, run_id
        raw = ORCH / f"CYCLE_{run_id}_run_jobs_raw.json"
        assert raw.is_file(), run_id
        import hashlib

        assert diag["raw_snapshot_sha256"] == hashlib.sha256(
            raw.read_bytes()).hexdigest(), run_id


def test_chain_gap_runs_are_now_committed():
    """42930240440 and 42939030694 were absent from every previously
    committed raw snapshot; this cycle closed both chain-of-record gaps."""
    for run_id in (42930240440, 42939030694):
        raw = _raw(run_id)
        assert raw["run"]["id"] == run_id
        assert raw["run"]["conclusion"] == "failure"
        jobs = {j["name"]: j for j in raw["jobs"]}
        assert jobs["team"]["conclusion"] == "failure"
        assert jobs["audit"]["conclusion"] == "skipped"
        diag = _diag(run_id)
        # Both runs failed at the lane-cycle step with exit 1 and left the
        # team ref at the predecessor's commit.
        assert diag["orchestration"]["classification"] == (
            "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
        assert diag["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
        assert diag["durable_delta"]["changed_files"] == 0


def test_42945527654_carries_model_rotation_annotation():
    """The only chain run with an observed provider mechanism: LEX_MODEL_ROTATE
    selected opencode/beam-free before the retry, then exit 1."""
    raw = _raw(42945527654)
    jobs = {j["name"]: j for j in raw["jobs"]}
    block = raw["check_run_annotations_by_job_id"][str(jobs["team"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("LEX_MODEL_ROTATE selected=opencode/beam-free" in m
               for m in messages)
    assert any("Transient Ox/OpenCode failure" in m for m in messages)


def test_42939662796_inherited_delta_is_fully_accounted():
    """42939662796 committed exactly three files: the 42939338810 raw +
    diagnosis and its own progressive smoke artifact. Nothing unaccounted."""
    diag = _diag(42939662796)
    assert diag["orchestration"]["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert diag["orchestration"]["team"]["failed_step"] == "Run lane cycle"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 3
    assert sorted(delta["changed_paths_sample"]) == [
        "results/product/orchestration/CYCLE_42939338810_resume_diagnosis.json",
        "results/product/orchestration/CYCLE_42939338810_run_jobs_raw.json",
        "results/product/progressive_smoke/CYCLE_42939662796_progressive_smoke.json",
    ]
    smoke = _load(ROOT / "results/product/progressive_smoke"
                  / "CYCLE_42939662796_progressive_smoke.json")
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23


def test_42931129328_audit_outcome_correction_is_recorded():
    """The 42931129328 state row said 'PROPOSED, pending independent audit'
    because the producer cannot observe its own audit. The committed raw of
    42939662796 observed that audit quantum-expiring; this cycle corrects the
    state row without deleting the original summary."""
    state = _load(STATE)
    row = next(r for r in state["run_history"] if r.get("run_id") == 42931129328)
    assert row["audit_gate"] == "NONE_ON_ANY_REF"
    assert row["correction"]["from"] == "NONE_YET_THIS_RUN"
    assert row["correction"]["to"] == "NONE_ON_ANY_REF"
    assert "42939662796" in json.dumps(row["correction"])


def test_state_hygiene_this_cycle():
    state = _load(STATE)
    # POINTER-PIN AMENDMENT (product cycle 42983901071), following
    # ``test_cycle_40263666190_resume.py``: later cycles legitimately
    # advance the pointer past this cycle's era; only regression below this
    # cycle's executing run is a defect.
    assert state["current_cycle_run_id"] >= 42955840398, (
        "current_cycle_run_id regressed below this cycle's executing run",
        state["current_cycle_run_id"])
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    # Every chain run and this cycle now has a run_history row.
    history_ids = {r.get("run_id") for r in state["run_history"]}
    for run_id, _, _ in CHAIN:
        assert run_id in history_ids, run_id
    assert 42955840398 in history_ids
    # The resume state block exists and names the resumed snapshot.
    block = state["cycle_42955840398_operational_resume"]
    assert block["run_id"] == 42955840398
    assert block["resumed_run"] == str(RESUMED)
    assert block["mode"].startswith("OPERATIONAL RESUME")
    # Accepted pointer unchanged: no run after 40284658455 has both halves
    # of requirement 4.
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    # Posture stays fail-closed.
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert state[flag] is False, flag
    assert state["continue_recommended"] is True


def test_no_producer_minted_gate_for_this_run():
    gate = ROOT / "results/audit/product/CYCLE_42955840398_GATE.json"
    assert not gate.exists()
    audit_report = ROOT / "reports/audit/product/CYCLE_42955840398.md"
    assert not audit_report.exists()


def test_lane_deliverable_spot_checks():
    """The inherited one-command clickable slice is intact on the resumed
    bytes: the committed offline bundles still validate under the product's
    own bundle contract (full clickable-slice server behaviour is covered by
    product/tests/test_bundle_preload.py, re-run in the MVP core set)."""
    from product.query.bundle import validate_bundle

    for name in ("rent-default", "petty-theft-dismissal",
                 "corporate-criminal-liability", "business-judgment-rule"):
        path = (ROOT / "results/product/offline_slice"
                / f"CYCLE_42794322956" / f"{name}.bundle.json")
        bundle = _load(path)
        validate_bundle(bundle)
        assert len(bundle["decisions"]) >= 100
        assert len(bundle["clusters"]) >= 8


def test_report_exists_and_names_the_chain():
    text = REPORT.read_text(encoding="utf-8")
    for run_id, _, _ in CHAIN:
        assert str(run_id) in text, run_id
    assert "42955840398" in text
    assert "UNADJUDICATED" in text
