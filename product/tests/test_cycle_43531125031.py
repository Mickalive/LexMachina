"""Cycle 43531125031: resume model-health-gated run 43530889474, audit-ready.

Run 43530889474 was dispatched to resume 43530681515.  Its team job died in
2 s at ``Run lane cycle`` with exit 76 and the annotation
``LEX_NO_HEALTHY_FREE_TOOL_MODEL``: the workflow-owned model-health preflight
refused to launch an agent, so no product step ran.  The always-run persist
step nevertheless published the predecessor's exact commit, which makes the
snapshot a ZERO_DURABLE_DELTA orchestration outcome, not a product defect.

The same unchanged snapshot carried a claim-bearing defect from run
43406325896: that run rewrote ``CYCLE_43373102286.json`` in place (append-only
violation) to include a later verification bundle.  This cycle restores the
historical bytes and re-homes the later measurement under its own run id.

The assertions below are deliberately byte- and fact-level: a claim that
cannot be reproduced from the committed tree is not published.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
import sys

for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43531125031"
RESUMED_RUN_ID = "43530889474"
PREDECESSOR_RUN_ID = "43530681515"
SNAPSHOT_HEAD = "afcfca0dcd14ca7aa56303abee249e47991a777c"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
LOGS = ORCH / f"CYCLE_{RESUMED_RUN_ID}_job_logs"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
LOG_EV = ORCH / f"CYCLE_{RESUMED_RUN_ID}_lane_cycle_log_evidence.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
HISTORICAL = (ROOT / "results" / "product" / "counter_content_family"
              / "CYCLE_43373102286.json")
HISTORICAL_SHA256 = (
    "78ba2a1f73bfd71725e417f038fbd0c1531b66139b27fc4adddf3565a6c520d2"
)
SLICE = ROOT / "results" / "product" / "offline_slice" / f"{EXECUTING_RUN_ID}_verify"
BUNDLE = SLICE / "rent-default.bundle.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
STATE = ROOT / "state" / "product.json"
CREDENTIAL_RE = re.compile(
    r"gh[somp]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+", re.IGNORECASE)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_run_is_observed_model_health_gate_with_zero_delta():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert diag["raw_snapshot"] == str(RAW.relative_to(ROOT))

    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["conclusion"] == "failure"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 2.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_step_conclusion"] == "skipped"
    assert orch["team"]["write_scope_step_conclusion"] == "skipped"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"

    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
    assert mech["logs_available"] is True
    assert mech["logs_endpoint_status"] == 200
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 76
    assert "no provider, auth or token cause" in mech["claim"]

    observed = orch["observed_failure"]
    assert observed["source"] == "github_actions_check_run_annotations"
    assert observed["exit_code"] == 76
    joined = " | ".join(observed["messages"])
    assert "LEX_NO_HEALTHY_FREE_TOOL_MODEL" in joined
    assert "exit code 76" in joined

    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["product_defect"] is False
    assert diag["adjudication"]["verdict_written"] is False


def test_lane_cycle_log_evidence_names_the_health_gate_not_a_quantum():
    from product import lane_cycle_log_evidence as lcle

    ev = _load(LOG_EV)
    assert ev["resuming_run_id"] == EXECUTING_RUN_ID
    entry = ev["runs"][RESUMED_RUN_ID]
    assert entry["classification"] == "MODEL_HEALTH_GATE_BLOCKED_DISPATCH"
    assert entry["exit_codes"] == [76]
    assert entry["markers"]["model_health_gate"] is True
    assert entry["markers"]["quantum_expired"] is False
    assert entry["markers"]["agent_card_ok"] is True
    assert entry["markers"]["persist_nothing_to_commit"] is True
    assert any(i.get("item") == "model_health_preflight_gate"
               for i in ev["control_plane_items"])

    manifest = _load(LOGS / "MANIFEST.json")
    for row in manifest["logs"]:
        if not row.get("file"):
            continue
        path = LOGS / row["file"]
        assert path.is_file()
        assert row["bytes"] == path.stat().st_size, row["file"]
        assert not CREDENTIAL_RE.search(path.read_text(encoding="utf-8"))

    # A quoted marker must not relabel a different exit.  The parser reads only
    # ``##[error]`` annotation lines as this run's own verdict.
    quoted = (
        '2026-11-14T00:00:00Z    "annotation": '
        '"LEX_NO_HEALTHY_FREE_TOOL_MODEL; model-health workflow must pass",\n'
        "2026-11-14T00:00:01Z ##[error]Process completed with exit code 67.\n"
    )
    rec = lcle.parse_lane_cycle_log(quoted, run_id=RESUMED_RUN_ID)
    assert rec["classification"] != "MODEL_HEALTH_GATE_BLOCKED_DISPATCH"
    assert rec["markers"]["model_health_gate"] is False

    annotated = (
        "2026-11-14T00:00:00Z LEX_AGENT_CARD_OK agent=product_engineer\n"
        "2026-11-14T00:00:01Z ##[error]LEX_NO_HEALTHY_FREE_TOOL_MODEL; "
        "model-health workflow must pass before agent work is dispatched.\n"
        "2026-11-14T00:00:02Z ##[error]Process completed with exit code 76.\n"
    )
    rec2 = lcle.parse_lane_cycle_log(annotated, run_id=RESUMED_RUN_ID)
    assert rec2["classification"] == "MODEL_HEALTH_GATE_BLOCKED_DISPATCH"
    assert rec2["exit_codes"] == [76]


def test_historical_artifact_is_restored_and_later_bytes_are_rehomed():
    raw = HISTORICAL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HISTORICAL_SHA256
    old = json.loads(raw)
    assert old["run_id"] == "43373102286"
    assert old["generated_at"] == "20261113T055037Z"
    assert old["fixed_path_family"]["totals"]["n_bundles"] == 49
    assert old["all_committed"]["totals"]["n_bundles"] == 149
    assert old["all_committed"]["totals"]["n_bundles"] == len(
        old["all_committed"]["bundles"])
    # The 43406325896 in-place rewrite inserted the LATER
    # 43380426686_verify bundle; the restored historical record must not
    # contain it.  (Older verify dirs that existed at generation time remain.)
    assert not any("43380426686_verify" in b["path"]
                   for b in old["all_committed"]["bundles"])

    new = _load(FAMILY)
    assert new["run_id"] == EXECUTING_RUN_ID
    fp = new["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 49
    assert fp["n_decisions"] == 4900
    assert fp["n_verified"] == 55
    assert fp["n_verified_defective"] == 0
    assert fp["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert all("_verify/" not in b["path"]
               for b in new["fixed_path_family"]["bundles"])
    assert new["false_reject_count"] == 0
    assert new["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert new["confirmed_set"]["still_verified"] is True
    assert new["ordered_work_2_full_success_rule"]["met"] is True
    # Verification outputs remain measured in the all-committed population.
    all_totals = new["all_committed"]["totals"]
    assert all_totals["n_bundles"] >= 150
    assert all_totals["n_bundles"] == len(new["all_committed"]["bundles"])
    assert any("_verify/" in b["path"]
               for b in new["all_committed"]["bundles"])
    assert all_totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 44,
        "D3_markup_residue": 31,
        "D4_language_marker_mismatch": 7,
    }


def test_end_to_end_slice_and_page_contract_on_current_bytes():
    summary = _load(SLICE / "summary.json")
    assert summary["bundle"] == str(BUNDLE.relative_to(ROOT))
    assert summary["mode"] == "full_loop"
    assert summary["degraded"] is False
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_source_link"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["rows_with_cluster_id"] == 100
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] == 4
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"

    bundle = _load(BUNDLE)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    answer = bundle.get("answer") or {}
    assert answer.get("status") == "ready"
    assert len(answer.get("cited_decision_ids") or []) == 4
    offline = bundle["provenance"]["offline_slice"]
    assert offline["network"] == "none"
    assert offline["geometry_preserved"] is True

    from offline_slice import verify_page
    ok, detail = verify_page(BUNDLE)
    assert ok, detail


def test_audit_readiness_profile_and_state_posture():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["mechanism_kind"] == "observed_health_gate"
    assert prof["delta_kind"] == "zero"
    assert prof["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert prof["lane_cycle_classification"] == (
        "MODEL_HEALTH_GATE_BLOCKED_DISPATCH")
    assert prof["exit_code"] == 76
    assert prof["cycle_test"] == (f"product/tests/test_cycle_"
                                  f"{EXECUTING_RUN_ID}.py")
    for field in ("raw", "resume_diag", "lane_cycle_log_evidence",
                  "current_report", "content_family"):
        assert Path(prof[field]).is_file(), field

    st = _load(STATE)
    # POINTER-PIN AMENDMENT (cycle 43538547811): the live pointer must not move
    # backwards past this cycle, but a later operational-resume cycle may
    # advance it. Pin non-regression, not equality.
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID)
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["ready_for_owner_session"] is False
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_HEAD
    block = st["cycle_43531125031_operational_resume"]
    assert block["resumed_snapshot"]["run_id"] == RESUMED_RUN_ID
    assert block["resumed_snapshot"]["durable_delta"] == "ZERO_DURABLE_DELTA"
    assert block["gate_minted"] is False
    assert block["auditor_namespace_written"] is False
    assert block["posture"]["owner_decision_required"] is False
    assert REPORT.is_file()


def test_historical_cycle_test_pins_its_own_artifact_not_the_live_tree():
    """The restored artifact must stay reproducible as more verify dirs land."""
    src = (ROOT / "product/tests/test_cycle_43373102286.py").read_text(
        encoding="utf-8")
    assert 'assert rec["all_committed"]["totals"]["n_bundles"] == 149' in src
    assert "== len(all_paths)" not in src
