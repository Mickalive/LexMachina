"""Cycle 42809155715: resume of zero-delta snapshot 42808654760.

Cycle 42794322956 shipped a false-green audit dossier: its raw snapshot was
regenerated after the diagnosis was written, so the dossier recorded 5/5 green
while the committed diagnosis pinned a sha the committed raw no longer had.
This cycle repairs that drift and adds a one-command offline serving path.

These tests pin, against the committed bytes:

1. snapshot 42808654760's orchestration facts (zero-delta exit 67, state
   validation/write-scope skipped, always-run persist republished 4db23e85)
   and the predecessor audit quantum expiry that made the resume necessary;
2. the re-pinned diagnosis and the preserved-but-stale predecessor diagnosis;
3. ``query_app.py --bundle`` loads a committed ``query_result_bundle`` and
   serves it through the existing resumable-run UI path;
4. state hygiene: the new cycle ids, accepted pointer untouched, every
   fail-closed posture flag still false.

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

RAW = ROOT / "results/product/orchestration/CYCLE_42808654760_run_jobs_raw.json"
DIAG = ROOT / ("results/product/orchestration/"
               "CYCLE_42808654760_resume_diagnosis.json")
OLD_RAW = ROOT / "results/product/orchestration/CYCLE_42793313084_run_jobs_raw.json"
OLD_DIAG = ROOT / ("results/product/orchestration/"
                   "CYCLE_42793313084_resume_diagnosis.json")
OLD_DIAG_REPAIRED = ROOT / ("results/product/orchestration/"
                            "CYCLE_42793313084_resume_diagnosis_"
                            "REPAIRED_42809155715.json")
STALE_DOSSIER = ROOT / ("results/product/audit_readiness/"
                        "CYCLE_42794322956_audit_readiness.json")
BUNDLE = ROOT / ("results/product/offline_slice/CYCLE_42794322956/"
                 "rent-default.bundle.json")
STATE = ROOT / "state/product.json"
REPORT = ROOT / "reports/product/CYCLE_42809155715.md"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_snapshot_42808654760_is_the_observed_zero_delta_guard():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-raw/2"
    assert raw["fetched_by_run"] == 42809155715
    assert raw["run"]["id"] == 42808654760
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"

    block = raw["check_run_annotations_by_job_id"][str(jobs["team"]["id"])]
    messages = [row[-1] for row in block["annotations"]]
    assert any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert any("exit code 67" in m for m in messages)

    # the direct predecessor is the audit quantum expiry this resume inherited
    chain = {row["run_id"]: row for row in raw["chain_of_record"]}
    assert chain[42798377691]["jobs"]["team"]["conclusion"] == "success"
    assert chain[42798377691]["jobs"]["audit"]["conclusion"] == "failure"
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m
               for m in chain[42798377691]["jobs"]["audit"]["annotations"])
    # 42794322956 is the last substantive tree (42bea5a3), even though its
    # team job failed after writing: the persist step published it.
    assert chain[42794322956]["jobs"]["team"]["conclusion"] == "failure"
    assert any("LEX_MODEL_AUTH_FAILURE" in m
               for m in chain[42794322956]["jobs"]["team"]["annotations"])
    assert "LEX_ZERO_DELTA_REPAIR" in \
        chain[42808654760]["jobs"]["team"]["annotations"]


def test_diagnosis_pins_the_committed_raw_and_the_zero_delta_fact():
    import audit_step_diagnosis as asd

    raw = _load(RAW)
    diag = _load(DIAG)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == "42808654760"
    assert diag["predecessor_run_id"] == "42798377691"
    assert diag["raw_snapshot_sha256"] == _sha(RAW)
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
    assert delta["snapshot_head"] == delta["predecessor_head"] == \
        "4db23e85ed32dd89717a8ff804a72135a635dc7c"
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_the_predecessor_false_green_dossier_is_repaired_not_erased():
    stale = _load(STALE_DOSSIER)
    assert stale["overall_status"] == "PASS"
    cycle_check = next(c for c in stale["checks"] if c["id"] == "cycle_test")
    assert cycle_check["detail"]["passed"] == 5
    assert cycle_check["detail"]["failed"] == 0

    old = _load(OLD_DIAG)
    repaired = _load(OLD_DIAG_REPAIRED)
    old_raw_sha = _sha(OLD_RAW)
    # the historical diagnosis still pins bytes that are not the committed raw
    assert old["raw_snapshot_sha256"] != old_raw_sha
    # the repair is re-pinned and keeps the same zero-delta/adjudication facts
    assert repaired["raw_snapshot_sha256"] == old_raw_sha
    assert repaired["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert repaired["adjudication"]["status"] == "UNADJUDICATED"

    import audit_readiness as ar
    prof = ar.select_profile("42794322956")
    assert Path(prof["resume_diag"]) == OLD_DIAG_REPAIRED
    assert Path(prof["resume_diag_superseded"]) == OLD_DIAG


def test_bundle_preload_is_the_shipped_offline_clickable_slice():
    app_source = (PRODUCT / "query_app.py").read_text(encoding="utf-8")
    assert '"--bundle"' in app_source
    assert "--bundle-run-id" in app_source
    assert "preloaded_run_id" in app_source
    assert (PRODUCT / "tests/test_bundle_preload.py").is_file()
    assert BUNDLE.is_file()

    # the committed bundle validates with the product's own contract
    from query.bundle import validate_bundle
    assert validate_bundle(_load(BUNDLE)) == []
    assert _load(BUNDLE)["answer"]["prose"]


def test_state_hygiene_and_operational_resume_record():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == 42809155715
    block = st["cycle_42809155715_operational_resume"]
    assert block["run_id"] == 42809155715
    assert block["resumed_run"] == "42808654760"
    assert block["predecessor_run_id"] == "42798377691"
    assert block["direction_version"] == 68
    assert block["orchestration_failure_of_record"]["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert block["orchestration_failure_of_record"]["mechanism"] == \
        "OBSERVED_ZERO_DELTA_GUARD"
    assert block["stale_dossier_reconciliation"]["old_diagnosis_sha_matches_raw"] \
        is False
    assert block["stale_dossier_reconciliation"]["repaired_diagnosis_sha_matches_raw"] \
        is True
    assert block["bundle_preload"]["flag"] == "--bundle"

    history = {row["run_id"]: row for row in st["run_history"]}
    for run_id in (42798377691, 42808654760, 42809155715):
        assert run_id in history, run_id
    assert history[42808654760]["status"] == \
        "ZERO_DURABLE_DELTA_GUARD_EXIT_67_DIAGNOSED"
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"] == \
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert st[flag] is False, flag

    assert REPORT.is_file()
    report = REPORT.read_text(encoding="utf-8")
    assert "42809155715" in report
    assert "42808654760" in report
    assert "--bundle" in report
