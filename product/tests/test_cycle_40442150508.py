"""Operational resume of producer snapshot 40436981920 — run 40442150508.

What this cycle had to establish, each item pinned by a committed artifact
rather than by prose:

1. **The resumed run's failure mechanism.** Run 40436981920's team job
   succeeded on every step and published a 3-file committed delta, then its
   audit job died inside the *Independent audit* agent step at
   ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78); the gate-reader and the
   persist step were both skipped, so no gate and no audit ref exist and the
   run is UNADJUDICATED - not rejected, and not accepted.
2. **The validation failure is inherited, not introduced.** The product's own
   one-command ledger and the two report-arithmetic guards are RED on the
   accepted base 7be4480e on exactly the same claims they are red for here;
   this cycle repairs them rather than re-diagnosing them.
3. **The lane deliverable still runs.** The query -> result-bundle -> clickable
   map slice passes its progressive smoke on this snapshot, and the server
   slice 40436981920 shipped is preserved and verified as PASS.
4. **The snapshot is audit-ready.** ``product/audit_handoff.py`` re-derives the
   product's claims read-only and inside budget, the audit-readiness dossier is
   written last and re-hashes clean, and state records the whole chain.

No frozen gate, rubric, threshold, bar, serve verdict or accepted pointer is
edited anywhere in this module.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RUN_ID = 40442150508
PRED = 40436981920
ACCEPTED_RUN = 40284658455
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

RAW = ROOT / "results" / "product" / "orchestration" / f"CYCLE_{PRED}_run_jobs_raw.json"
DIAG = ROOT / "results" / "product" / "orchestration" / f"CYCLE_{PRED}_resume_diagnosis.json"
SMOKE = ROOT / "results" / "product" / "progressive_smoke" / f"CYCLE_{RUN_ID}_progressive_smoke.json"
SLICE = ROOT / "results" / "product" / "server_slice" / "20261027T021601Z" / "summary.json"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RUN_ID}_audit_readiness.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE = ROOT / "state" / "product.json"
ATTR = ROOT / "results" / "product" / "regression" / f"CYCLE_{RUN_ID}_test_delta_attribution.json"
DISC = ROOT / "results" / "product" / "regression" / f"CYCLE_{RUN_ID}_report_testcount_disclosure.json"
OLD_ATTR = ROOT / "results" / "product" / "regression" / "CYCLE_39758711075_test_delta_attribution.json"
OLD_DISC = ROOT / "results" / "product" / "regression" / "CYCLE_39689729561_report_testcount_disclosure.json"
LIVE_SLICE = ROOT / "results" / "product" / "live_slice" / "20261022T141111Z.json"


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing committed artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _state() -> dict:
    return _load(STATE)


def _report() -> str:
    assert REPORT.is_file(), f"missing report of record {REPORT.name}"
    return REPORT.read_text(encoding="utf-8")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=False).stdout


# --------------------------------------------------------------------------
# 1. the resumed run's orchestration failure is classified from public evidence
# --------------------------------------------------------------------------

def test_the_resumed_run_is_classified_as_an_audit_quantum_expiry():
    raw = _load(RAW)
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    failed = [s for s in audit["steps"] if s["conclusion"] == "failure"]
    assert [s["name"] for s in failed] == ["Independent audit"]
    later = [s for s in audit["steps"] if s["name"] in {
        "Enforce audit scope and read gate", "Persist audit snapshot"}]
    assert {s["name"]: s["conclusion"] for s in later} == {
        "Enforce audit scope and read gate": "skipped",
        "Persist audit snapshot": "skipped"}
    messages = [a["message"] for group in raw["annotations"].values()
                for a in group if a["job"] == "audit"]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages), (
        f"the quantum-expiry annotation is gone from the public record: {messages}")
    assert any("exit code 78" in m for m in messages)


def test_the_team_job_of_the_resumed_run_succeeded_on_every_step():
    raw = _load(RAW)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    named = {s["name"]: s["conclusion"] for s in team["steps"]}
    for step in ("Run lane cycle", "Validate active MVP producer state",
                 "Enforce lane write scope", "Persist team snapshot"):
        assert named.get(step) == "success", f"{step} was {named.get(step)}"


def test_the_resume_diagnosis_agrees_with_the_raw_record():
    diag = _load(DIAG)
    assert diag["run_id"] == str(PRED)
    assert diag["orchestration"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert diag["orchestration"]["audit"]["gate_file_written"] is False
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 3
    assert diag["durable_delta"]["snapshot_head"].startswith("60e3d898")
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["product_defect"] is False
    # no gate may be invented for a run whose audit never finished
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_no_audit_ref_exists_for_any_run_in_the_failed_chain():
    """Both halves of requirement 4, negatively: nothing was promoted."""
    for run in (40427889739, 40429931848, 40436981920, RUN_ID):
        refs = _git("ls-remote", "--exit-code", "--heads", "origin",
                    f"refs/heads/cycle/core/product/{run}/audit")
        assert refs.strip() == "", f"run {run} unexpectedly has an audit ref"
    accepted = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product")
    assert accepted.split()[0].startswith(ACCEPTED_COMMIT[:8]), (
        f"lab/product moved: {accepted.strip()}")


# --------------------------------------------------------------------------
# 2. the lane deliverable still runs on this snapshot
# --------------------------------------------------------------------------

def test_the_query_map_vertical_slice_still_passes_its_progressive_smoke():
    smoke = _load(SMOKE)
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"]
    checks = {c["id"]: c for c in smoke["checks"]}
    assert checks["bundle_status_counts"]["observed"]["n_decisions"] >= 100
    assert checks["bundle_status_counts"]["observed"]["n_clusters"] >= 1
    assert checks["answer_has_citations"]["observed"]["n_cited"] >= 1
    assert checks["static_query.html"]["observed"]["status"] == 200


def test_the_preserved_server_slice_of_40436981920_is_verified_as_pass():
    """The only durable delta of the resumed run is kept and checked."""
    summary = _load(SLICE)
    assert summary["verdict"] == "PASS"
    assert summary["failures"] == []
    assert summary["mode"] == "fixture"
    counts = summary["counts"]
    assert counts["n_final"] == 100
    assert counts["rows_with_source_url"] == 100
    assert counts["n_cited"] >= 1
    assert counts["counter_authorities"] >= 1
    bundle = _load(SLICE.parent / "served.bundle.json")
    assert len(bundle["decisions"]) == counts["n_final"]
    assert len(bundle["clusters"]) == counts["n_clusters_final"]


# --------------------------------------------------------------------------
# 3. the inherited validation failures are repaired, not restated
# --------------------------------------------------------------------------

def test_the_attribution_pin_moved_and_the_previous_artifact_is_untouched():
    art = _load(ATTR)
    assert art["run_id"] == RUN_ID
    assert art["reconciles"] is True
    assert art["working_tree"]["reconciles"] is True
    old = _load(OLD_ATTR)
    assert old["run_id"] == 39758711075
    assert old["working_tree"]["collected_total"] == 1491, (
        "the previous pin's measurement was rewritten by the pin move")
    assert old["base"]["commit"].startswith("9727a45"), (
        "the new pin must keep the SAME named base the regression scope names")
    assert art["base"]["commit"] == old["base"]["commit"]
    assert art["cross_check"]["base_agrees"] is True


def test_the_report_quotes_the_attribution_decomposition_line_verbatim():
    line = _load(ATTR)["decomposition_line"]
    text = _report()
    assert line, "the attribution published no decomposition line"
    assert line in text, (
        "the report of record does not quote the tool's decomposition line "
        "verbatim - prose is not a second source of truth")


def test_the_disclosure_pin_moved_to_a_measurement_of_this_tree():
    disc = _load(DISC)
    assert disc["run_id"] == RUN_ID
    assert disc["pin_repoint"]["previous_artifact"] == OLD_DISC.name
    assert disc["pin_repoint"]["reason"]
    assert OLD_DISC.is_file()
    # measured against the guard's own sweep functions, not copied
    from product.tests import test_report_artifact_arithmetic as guard
    fresh = guard.sweep_testcount_candidates()
    assert set(fresh) == set(disc["bare_testcount_claims"]), (
        "the new disclosure is not a measurement of this tree")
    coverage = guard.citation_claim_coverage()
    assert (coverage["artifact_report_pairs"]
            == disc["citation_sweep"]["artifact_report_pairs"])
    assert (coverage["citation_claims_parsed"]
            == disc["citation_sweep"]["citation_claims_parsed"])
    assert coverage["artifact_report_pairs"] > 19, (
        "the citation sweep did not grow after the repair - the published scope "
        "would still be stale")
    assert disc["non_claims"], "the disclosure lost its non-coverage list"


def test_the_previously_uncited_live_slice_artifact_now_has_a_report():
    payload = _load(LIVE_SLICE)
    n_cited = payload["answer"]["n_cited"]
    assert n_cited == 0, "re-measure: the pinned n_cited=0 premise moved"
    text = _report()
    assert LIVE_SLICE.name in text, (
        "no report of record cites this artifact, so the citation sweep is "
        "vacuous for it")
    assert f"n_cited={n_cited}" in text, (
        "the report must publish the artifact's OWN count beside the citation")


def test_the_warm_cache_state_record_was_restored_not_rewritten():
    """A deleted claim-bearing state record is restored from git history."""
    state = _state()
    key = "cycle_39891382087_vertical_slice_delivery"
    assert isinstance(state.get(key), dict), (
        "the warm-cache delivery record is missing from state/product.json")
    detail = state[key]["measurements"]["detail_cache"]
    assert (detail["before_detail_ids"], detail["after_detail_ids"]) == (147, 241)
    assert detail["diagnostic_probe_files"] == 2
    # byte-exact restore of the historical value, re-derived from git
    historical = json.loads(_git("show", "0ed7930b^:state/product.json"))
    assert state[key] == historical[key], (
        "the restored record differs from the bytes git history holds")


# --------------------------------------------------------------------------
# 4. posture and both halves of requirement 4
# --------------------------------------------------------------------------

def test_posture_stays_fail_closed_and_the_accepted_pointer_is_both_halves():
    state = _state()
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert state.get(flag) is False, f"{flag} slipped to {state.get(flag)!r}"
    assert state["continue_recommended"] is True
    assert state["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN}"
    assert state["accepted_commit"] == ACCEPTED_COMMIT
    gate = ROOT / "results" / "audit" / "product" / f"CYCLE_{ACCEPTED_RUN}_GATE.json"
    payload = _load(gate)
    assert payload["gate"] == "PASS" and payload["safe_to_integrate"] is True
    assert payload["required_fixes"] == []


def test_the_state_records_this_cycle_and_grows_the_verification_register():
    state = _state()
    block = state.get(f"cycle_{RUN_ID}_operational_resume")
    assert isinstance(block, dict), "state has no record of this cycle"
    assert block["run_id"] == RUN_ID
    assert block["resumed_run_id"] == PRED
    register = state["verification"]
    assert f"cycle_{RUN_ID}_operational_resume" in register, (
        "the verification register did not grow - the non-vacuity guard must "
        "not be green for the wrong reason")
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"


def test_run_history_covers_the_whole_unadjudicated_chain():
    state = _state()
    by_run = {str(r.get("run_id")): r for r in state.get("run_history") or []}
    for run in (40423889401, 40427889739, 40429931848, PRED, RUN_ID):
        assert str(run) in by_run, f"run {run} missing from run_history"
        assert by_run[str(run)].get("status"), "run_history entry has no status"
    assert by_run[str(PRED)]["status"] in {"UNADJUDICATED", "NO_GATE"}
    assert by_run[str(RUN_ID)]["status"] in {"UNADJUDICATED", "IN_FLIGHT"}


def test_the_audit_readiness_dossier_is_written_last_and_rehashes_clean():
    """The exact defect that rejected cycle 40423889401 must not recur."""
    from product import audit_readiness
    rec = _load(DOSSIER)
    assert rec["run_id"] == RUN_ID
    result = audit_readiness.verify_dossier(DOSSIER)
    assert result["ok"] is True, f"stale dossier hashes: {result['problems']}"
    assert result["n_checked"] >= 6


def test_the_handoff_command_verifies_the_snapshot_read_only_and_in_budget():
    from product import audit_handoff
    report = audit_handoff.build(ROOT, checks=("scope", "state"), budget=120.0,
                                 dossier=None, scope="producer", tests=None,
                                 skip_tests=True)
    assert report["verdict"] == "PASS", report["checks"]
    assert report["read_only"]["ok"] is True
    assert report["elapsed_s"] <= 120.0
    assert "writes no gate" in report["claim_ceiling"]


@pytest.mark.parametrize("flag", ["continue_recommended"])
def test_the_lane_still_recommends_continuing(flag: str):
    assert _state()[flag] is True


def test_the_dispatch_time_frontier_mount_absence_is_recorded_not_invented():
    """The mount was empty when this cycle was dispatched; state keeps that fact.

    The live directory is deliberately NOT asserted: the resume run
    40452133317 later populated ``/tmp/lex_accepted/frontier`` read-only so
    this cycle's adoption claims could be re-derived against the accepted
    branches (workflow step "Mount Frontier").  That re-derivation is a
    recorded decision of THAT run, and a test that pinned the directory to
    empty would turn an honest follow-up into a false failure.
    """
    block = _state()[f"cycle_{RUN_ID}_operational_resume"]
    assert block["frontier_mounts_absorbed"] == []
    note = block.get("frontier_mount_note", "")
    assert note.startswith("empty at dispatch"), note
