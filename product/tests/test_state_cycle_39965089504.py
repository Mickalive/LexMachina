"""Executable re-derivation of product cycle 39965089504's published claims.

Every number the report of record states is re-derived here from the
committed artifacts, never copied from prose:

* the resumed deliverable of run 39956256289: the D1 min-core-length repair
  (reached 25 -> 24 of 28, signalled counts unchanged) and the regenerated
  coverage artifact;
* the pre-registered live-answer reliability measurement lineage (three
  committed freeze+measurement pairs under the identical protocol sha), its
  NOT-MADE claim on every date, and the writer-abort disclosure of ordered
  item 3 visible on all seven legs of the latest measurement;
* the resume diagnosis artifact's run-id wiring;
* the state record written by this cycle, with every posture flag false.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "39965089504"
RESUMED = "39956256289"
PROTOCOL_SHA = "418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1"

CSK = REPO_ROOT / "results" / "product" / "counter_surface_known"
AR = REPO_ROOT / "results" / "product" / "answer_reliability"
ORCH = REPO_ROOT / "results" / "product" / "orchestration"


def test_the_resume_diagnosis_artifact_is_present_and_wired() -> None:
    path = ORCH / f"CYCLE_{RUN_ID}_resume_diagnosis.json"
    assert path.is_file(), "the resume diagnosis of this cycle must exist"
    diag = json.loads(path.read_text(encoding="utf-8"))
    assert diag["run_id"] == RUN_ID
    assert diag["resumed_run_id"] == RESUMED
    assert diag["direction_version"] == 64
    assert diag["observed_snapshot"]["head_commit"].startswith("fc8b187")
    # the diagnosis must not invent an exit code
    assert "unavailable" in diag["observed_snapshot"]["exact_exit_code"]


def test_the_d1_repair_changed_exactly_the_reached_count() -> None:
    new = json.loads((CSK / f"CYCLE_{RESUMED}.json").read_text(encoding="utf-8"))
    old = json.loads((CSK / "CYCLE_39949461593.json").read_text(encoding="utf-8"))
    for cap in ("8", "24"):
        nb, ob = new["aggregate"]["by_cap"][cap], old["aggregate"]["by_cap"][cap]
        assert nb["known_reached_n"] == 24 == ob["known_reached_n"] - 1
        assert nb["known_signalled_n"] == ob["known_signalled_n"]
        assert nb["n_signalled_total"] == ob["n_signalled_total"]
        assert nb["n_hydrated"] == ob["n_hydrated"]
    leg = new["aggregate"]["by_cap"]["8"]["per_leg"]["corporate-criminal-liability"]
    assert leg["known_reached_n"] == 5
    assert leg["known_short_core_ids"] == ["bstger_BG.2016.5"]
    # the historical artifact stays untouched: no min_core_length key, 25 reached
    assert "min_core_length" not in old["aggregate"]["by_cap"]["8"]["per_leg"]["rent-default"]
    assert old["aggregate"]["by_cap"]["8"]["known_reached_n"] == 25
    assert new["aggregate"]["delta_high_minus_low"]["known_signalled_n"] == 3


def test_the_reliability_lineage_shares_one_protocol_and_never_claims() -> None:
    lineage = ["39799042649", "39924626016", RESUMED]
    shas, claims = [], []
    for run in lineage:
        freeze = json.loads(
            (AR / f"{run}_protocol_freeze.json").read_text(encoding="utf-8"))
        meas = json.loads(
            (AR / f"{run}_measurement.json").read_text(encoding="utf-8"))
        assert freeze["frozen_before_execution"] is True
        assert freeze["protocol_sha256"] == PROTOCOL_SHA
        assert meas["protocol_sha256"] == PROTOCOL_SHA
        assert meas["metrics"]["n_legs_executed"] == 7
        assert meas["metrics"]["n_legs_failed"] == 0
        shas.append(freeze["protocol_sha256"])
        claims.append(meas["product_claim_reliable_live_answer"])
    assert len(set(shas)) == 1
    assert claims == [False, False, False]


def test_the_latest_measurement_publishes_the_outage_honestly() -> None:
    meas = json.loads((AR / f"{RESUMED}_measurement.json").read_text(encoding="utf-8"))
    m = meas["metrics"]
    assert m["answer_ready_rate"] == 0.0
    assert m["citation_validity"] == 1.0
    assert m["source_validity"] == 1.0
    assert m["language_match_rate"] == 1.0
    assert m["degradation_visible_rate"] == 1.0
    assert m["stability_jaccard_min"] == 1.0
    assert m["prose_citation_validity"] < 1.0  # 8/9 as measured
    assert meas["product_claim_reliable_live_answer"] is False
    assert set(meas["posture_unchanged"].values()) == {False}
    for leg in meas["legs"]:
        d = leg["degradation"]
        assert d["degraded"] is True
        assert d["degradation_code"] == "e_EMISSION_WRITER_ABORT"
        assert d["visible"] is True
        assert leg["answer"]["status"] == "degraded"
        assert leg["provider"]["model_used"] is None


def test_the_state_record_of_this_cycle_is_written_and_fail_closed() -> None:
    state = json.loads((REPO_ROOT / "state" / "product.json").read_text(encoding="utf-8"))
    assert state["direction_version"] == 64
    assert state["current_run"] == RUN_ID
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert state[flag] is False, flag
    rec = state[f"cycle_{RUN_ID}_operational_resume"]
    assert rec["resumed_run_id"] == RESUMED
    assert rec["diagnosis_artifact"] == (
        f"results/product/orchestration/CYCLE_{RUN_ID}_resume_diagnosis.json")
    assert (REPO_ROOT / rec["diagnosis_artifact"]).is_file()


def test_the_report_of_record_cites_only_artifacts_that_exist() -> None:
    report = (REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md").read_text(
        encoding="utf-8")
    assert f"Cycle {RUN_ID}" in report
    for rel in (
        f"results/product/counter_surface_known/CYCLE_{RESUMED}.json",
        f"results/product/answer_reliability/{RESUMED}_measurement.json",
        f"results/product/answer_reliability/{RESUMED}_protocol_freeze.json",
        f"results/product/orchestration/CYCLE_{RUN_ID}_resume_diagnosis.json",
    ):
        assert rel in report, f"report must cite {rel}"
        assert (REPO_ROOT / rel).is_file(), f"cited artifact missing: {rel}"
