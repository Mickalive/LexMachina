"""Tests for the run 39552967253 operational resume of producer snapshot 39548140787.

What these tests pin (all fail-closed, all mount-independent):

1. DIAGNOSIS - run 39548140787's team job succeeded and its audit job failed at
   the step 'Enforce audit scope and read gate', no audit branch exists, and
   lab/evaluation never advanced past b486e0cc. The step's underlying CAUSE is
   published as inference only.
2. SNAPSHOT DEFECT - the subject snapshot cited three claim-bearing artifacts
   absent from its own committed tree and one DIRECTORY evidence ref that the
   lane's own ``test_evidence_refs_exist`` rejects. The missing artifacts are
   asserted to be STILL ABSENT: this resume re-executes under run
   39552967253 instead of fabricating them after the fact.
3. RESTORATION - every one of the 73 state keys the snapshot deleted is present
   again, 62 byte-identical to the accepted base and 11 changed only inside the
   disclosed ``UPDATED_KEYS`` list (the other 4 of the 15 UPDATED_KEYS were
   retained-and-overwritten by the snapshot, so they were never "removed"),
   and the five fail-closed probes are false.
4. RE-EXECUTION - the cached-bundle benchmark record of run 39552967253 exists,
   carries BENCHMARK_VALID_NO_FALSIFICATION / exit 0, and its per-question
   vector is identical to the three prior committed artifacts and to
   ``state['benchmark_result']``.
5. NEGATIVE RESULT PRESERVED - the counter-authority yield negative result
   (2 of 4 frozen questions at zero candidate counter labels) is still recorded.
6. FROZEN PINS - all four frozen inputs re-hash to their pinned digests.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

RUN_ID = "39552967253"
RESUMED_FROM = "39548140787"
RESUMED_HEAD = "8fe862e83ade65dcd136e3bcba370347e50e7e66"
ACCEPTED_BASE = "b486e0ccc3a2df1ab0b86d8517ec90d90cdc7c49"
LAST_ACCEPTED_RUN = "39546829058"

STATE = REPO / "state" / "evaluation.json"
DIAGNOSIS = (REPO / "results" / "evaluation" / f"orchestration_resume_{RESUMED_FROM}"
             / f"{RUN_ID}_diagnosis.json")
VERIFY = (REPO / "results" / "evaluation" / f"orchestration_resume_{RESUMED_FROM}"
          / f"{RUN_ID}_state_restoration_verify.json")
BENCH = (REPO / "results" / "evaluation" / "query_map_cached_bundle_benchmark"
         / f"{RUN_ID}.json")
BENCH_REPORT = (REPO / "reports" / "evaluation"
                / f"QUERY_MAP_CACHED_BUNDLE_{RUN_ID}.md")
CYCLE_REPORT = REPO / "reports" / "evaluation" / f"CYCLE_{RUN_ID}.md"
SUBJECT_REPORT = REPO / "reports" / "evaluation" / "CYCLE_local_1792559615.md"
HYPOTHESIS = REPO / "evaluation" / "OPERATIONAL_RESUME_39548140787_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation" / "OPERATIONAL_RESUME_39548140787_FREEZE_RECORD_V1.json"

#: Claimed-but-absent artifacts of the subject snapshot. Never fabricated here.
ABSENT_BY_DESIGN = [
    REPO / "results" / "evaluation" / "query_map_cached_bundle_benchmark"
    / "local_1792559615.json",
    REPO / "reports" / "evaluation" / "QUERY_MAP_CACHED_BUNDLE_local_1792559615.md",
]

PRIOR_ARTIFACTS = [
    REPO / "results" / "evaluation" / "query_map_cached_bundle_benchmark"
    / "local_test.json",
    REPO / "results" / "evaluation" / "query_map_cached_bundle_benchmark"
    / "39462322100.json",
    REPO / "results" / "evaluation" / "query_map_cached_bundle_benchmark"
    / "39200567493.json",
]

FAIL_CLOSED_FLAGS = ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                     "ready_for_owner_session", "owner_decision_required")

UPDATED_KEYS = {
    "accepted_run_id", "accepted_run_promotion_status", "claim_ceiling",
    "continue_recommended_reason", "cycle_status", "evidence_ref_corrections",
    "evidence_refs", "evidence_refs_n", "github_run", "last_verified_run",
    "last_verified_timestamp", "next_recommendation", "proposed_run_id",
    "pytest_execution_disclosure", "summary",
}

FROZEN_PINS = {
    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
}

ZERO_YIELD_EXPECTED = {"corporate-criminal-liability", "business-judgment-rule"}

needs_report = pytest.mark.skipif(
    not CYCLE_REPORT.is_file(),
    reason=f"{CYCLE_REPORT.name} is written after the first pytest reading")
needs_verify = pytest.mark.skipif(
    not VERIFY.is_file(), reason="verify-phase record not written yet")


def _git_show(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=str(REPO),
                          check=True, capture_output=True).stdout


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vector(rec: dict) -> dict[str, dict]:
    out = {}
    for q in rec.get("questions", []):
        m, r = q.get("producer_meta", {}), q.get("recall_measured_not_thresholded", {})
        kr, kc = r.get("known_relevant", {}), r.get("known_counter_reach", {})
        out[q["slug"]] = {
            "decisions": m.get("n_decisions"),
            "clusters": m.get("n_clusters"),
            "counter_candidates": m.get("n_counter_candidates"),
            "duplicates_suppressed": m.get("n_duplicates_suppressed"),
            "leg1_pass": bool(q["leg1_producer_baseline"]["pass"]),
            "leg2_fired": bool(
                q["leg2_falsification_blanked_counter_evidence"]["fired"]),
            "leg3_fired": bool(q["leg3_falsification_broken_source_url"]["fired"]),
            "known_relevant": f"{kr.get('found')}/{kr.get('expected')}",
            "known_counter_reach": f"{kc.get('found')}/{kc.get('expected')}",
        }
    return out


def _vector_from_state(bench: dict) -> dict[str, dict]:
    out = {}
    for q in bench.get("questions", []):
        out[q["slug"]] = {
            "decisions": q.get("decisions"),
            "clusters": q.get("clusters"),
            "counter_candidates": q.get("counter_candidates"),
            "duplicates_suppressed": q.get("duplicates_suppressed"),
            "leg1_pass": q.get("leg1_pass"),
            "leg2_fired": q.get("leg2_fired"),
            "leg3_fired": q.get("leg3_fired"),
            "known_relevant": str(q.get("known_relevant_recall", "")).split(" ")[0],
            "known_counter_reach": str(q.get("known_counter_reach", "")).split(" ")[0],
        }
    return out


# ---------------------------------------------------------------- 1. state ----
def test_state_mandatory_fields_and_direction_pin():
    state = json.loads(STATE.read_text())
    for field in ("lane", "direction_version", "evidence_tier", "cycle_status",
                  "continue_recommended", "accepted_run_id", "evidence_refs",
                  "next_recommendation"):
        assert field in state, f"missing mandatory field {field}"
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 61


def test_state_fail_closed_probes_present_and_false():
    state = json.loads(STATE.read_text())
    for flag in FAIL_CLOSED_FLAGS:
        assert flag in state, f"fail-closed probe deleted from state: {flag}"
        assert state[flag] is False, f"{flag} must stay false"


def test_all_73_snapshot_deleted_state_keys_are_present_again():
    base = json.loads(_git_show(ACCEPTED_BASE, "state/evaluation.json"))
    subj = json.loads(_git_show(RESUMED_HEAD, "state/evaluation.json"))
    cur = json.loads(STATE.read_text())
    removed = set(base) - set(subj)
    assert len(removed) == 73, (
        f"pre-registered count slip? machine count of removed keys is "
        f"{len(removed)}; the frozen hypothesis hand-counted 71 - the SET rule "
        f"below, not the number, governs")
    missing = sorted(k for k in removed if k not in cur)
    assert missing == [], f"state keys deleted by the snapshot never restored: {missing}"


def test_non_updated_restored_keys_are_byte_identical_to_accepted_base():
    base = json.loads(_git_show(ACCEPTED_BASE, "state/evaluation.json"))
    subj = json.loads(_git_show(RESUMED_HEAD, "state/evaluation.json"))
    cur = json.loads(STATE.read_text())
    removed = sorted(set(base) - set(subj))
    static = [k for k in removed if k not in UPDATED_KEYS]
    changed = [k for k in static
               if json.dumps(base[k], sort_keys=True, ensure_ascii=False, default=str)
               != json.dumps(cur[k], sort_keys=True, ensure_ascii=False, default=str)]
    assert changed == [], f"non-updated restored keys were modified: {changed}"
    # 73 removed = 62 non-updated (byte-exact) + 11 carrying this cycle's
    # disclosed UPDATED_KEYS content. The other 4 of the 15 UPDATED_KEYS were
    # retained-and-overwritten by the snapshot, so they are not "removed".
    removed_updated = [k for k in removed if k in UPDATED_KEYS]
    assert len(static) == 62, f"expected 62 static restored keys, got {len(static)}"
    assert len(removed_updated) == 11, (
        f"expected 11 removed keys inside UPDATED_KEYS, got {len(removed_updated)}")
    assert sorted(UPDATED_KEYS - set(removed_updated)) == [
        "accepted_run_id", "cycle_status", "evidence_refs", "next_recommendation"], (
        "the 4 UPDATED_KEYS retained-and-overwritten by the snapshot must stay "
        "the disclosed ones")


def test_all_updated_keys_carry_this_cycles_content():
    base = json.loads(_git_show(ACCEPTED_BASE, "state/evaluation.json"))
    cur = json.loads(STATE.read_text())
    unchanged = [k for k in UPDATED_KEYS
                 if k in base and json.dumps(base[k], sort_keys=True,
                                             ensure_ascii=False, default=str)
                 == json.dumps(cur[k], sort_keys=True, ensure_ascii=False, default=str)]
    assert unchanged == [], f"UPDATED_KEYS still carrying accepted-base content: {unchanged}"


def test_evidence_refs_are_all_existing_files():
    state = json.loads(STATE.read_text())
    assert state["evidence_refs"], "evidence_refs must not be empty"
    bad = [r for r in state["evidence_refs"] if not (REPO / r).is_file()]
    assert bad == [], f"evidence refs that are not existing files: {bad}"


def test_run_ids_are_corrected():
    state = json.loads(STATE.read_text())
    assert state["accepted_run_id"] == LAST_ACCEPTED_RUN
    assert state["proposed_run_id"] == RUN_ID
    assert state["github_run"] in (RUN_ID, int(RUN_ID))


# --------------------------------------------------- 2. snapshot defects ------
def test_subject_snapshot_cited_three_absent_artifacts_and_a_directory():
    subj = json.loads(_git_show(RESUMED_HEAD, "state/evaluation.json"))
    refs = subj["evidence_refs"]
    missing = [r for r in refs if not (REPO / r).is_file()]
    assert (f"results/evaluation/query_map_cached_bundle_benchmark/"
            f"local_1792559615.json") in missing
    assert (f"reports/evaluation/QUERY_MAP_CACHED_BUNDLE_"
            f"local_1792559615.md") in missing
    assert "results/evaluation/retrieval_benchmark/cache" in missing, (
        "the subject snapshot also cited a DIRECTORY, which "
        "test_evidence_refs_exist (Path.is_file) rejects")
    # and the bundle glob named in the subject report matches nothing there
    subj_paths = set(subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", RESUMED_HEAD], cwd=str(REPO),
        check=True, capture_output=True, text=True).stdout.splitlines())
    assert not [p for p in subj_paths
                if p.startswith("results/evaluation/query_map_cached_bundle_benchmark/"
                                "bundles/local_1792559615_")]


def test_defective_artifacts_were_never_fabricated_after_the_fact():
    """A file named for run local_1792559615 would be a fabricated back-fill."""
    for p in ABSENT_BY_DESIGN:
        assert not p.exists(), (
            f"{p.relative_to(REPO)} must NOT be created: the resume re-executes "
            f"under run {RUN_ID} instead of back-filling a scratch run id")


def test_subject_defective_report_preserved_byte_identical():
    assert _sha256(SUBJECT_REPORT) == (
        "93a0b580b309e83b0ab9c7488c679d66c133e836eb7626fab1e33eb19fcff6b3"), (
        "the defective cycle's report must be preserved, not rewritten")


# --------------------------------------------------------- 3. diagnosis -------
def test_diagnosis_names_the_failed_job_and_step():
    assert DIAGNOSIS.is_file(), f"missing {DIAGNOSIS.name}"
    d = json.loads(DIAGNOSIS.read_text())
    api = d["prior_run_api"]
    assert api["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in api["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    failed_names = [s["name"] for s in jobs["audit"]["failed_steps"]]
    assert failed_names == ["Enforce audit scope and read gate"], (
        "the gate step is the only failed audit step recorded by the API")
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert api["job_log_endpoint_accessible"] is False, (
        "job logs stay inaccessible, so the step's CAUSE must remain labelled "
        "inference in every artifact")
    assert "INFERENCE" in d["findings"]["F2_failed_step"]["attribution"]


def test_diagnosis_shows_no_audit_branch_and_no_promotion():
    d = json.loads(DIAGNOSIS.read_text())
    b = d["branch_facts"]
    assert b["audit_branch_exists"] is False
    assert b["team_branch_exists"] is True
    assert b["lab_evaluation_head"] == ACCEPTED_BASE
    assert b["lab_evaluation_advanced_past_accepted_base"] is False
    assert d["findings"]["F1_no_audit_branch"]["holds"] is True


def test_diagnosis_findings_that_are_decisive_all_hold():
    d = json.loads(DIAGNOSIS.read_text())
    for key in ("F1_no_audit_branch", "F2_failed_step", "F3_missing_refs",
                "F4_content_reproduces", "F5_reexecution", "F7_pins"):
        assert d["findings"][key]["holds"] is True, f"{key} did not hold"
    assert d["exit_code"] == 0
    assert d["frozen_pins_match_expected"] is True


# ------------------------------------------------------- 4. re-execution ------
def test_benchmark_record_of_this_run_exists_and_passes_its_own_legs():
    assert BENCH.is_file(), f"missing {BENCH.name}"
    assert BENCH_REPORT.is_file(), f"missing {BENCH_REPORT.name}"
    rec = json.loads(BENCH.read_text())
    assert rec["run_id"] == RUN_ID
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is True
    assert rec["n_questions"] == 4
    for q in rec["questions"]:
        assert q["leg1_producer_baseline"]["pass"] is True
        assert q["leg2_falsification_blanked_counter_evidence"]["fired"] is True
        assert q["leg3_falsification_broken_source_url"]["fired"] is True


def test_reexecuted_benchmark_vector_is_identical_to_the_three_prior_records():
    rec = json.loads(BENCH.read_text())
    new_vec = _vector(rec)
    assert new_vec, "no questions in the new record"
    for prior in PRIOR_ARTIFACTS:
        assert _vector(json.loads(prior.read_text())) == new_vec, (
            f"{prior.name} diverges from the {RUN_ID} vector")
    state = json.loads(STATE.read_text())
    assert _vector_from_state(state["benchmark_result"]) == new_vec, (
        "state benchmark_result diverges from the committed record")


def test_counter_authority_yield_negative_result_is_preserved():
    rec = json.loads(BENCH.read_text())
    zero = set(rec["counter_authority_yield"]["questions_with_zero_counter_candidates"])
    assert zero == ZERO_YIELD_EXPECTED, (
        "the 2/4 zero-yield negative result must survive re-execution unchanged")
    state = json.loads(STATE.read_text())
    finding = state["benchmark_result"]["counter_authority_yield_finding"]
    for slug in ZERO_YIELD_EXPECTED:
        assert slug in finding
    assert "NEGATIVE RESULT" in finding
    assert rec["counter_authority_yield"]["n_counter_candidates_total"] == 20


def test_frozen_spec_rehashed_identical_before_and_after_execution():
    rec = json.loads(BENCH.read_text())
    spec = rec["frozen_spec"]
    assert spec["sha256_before"] == spec["sha256_after"] == FROZEN_PINS[
        "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"]


# ---------------------------------------------------------- 5. verify ---------
@needs_verify
def test_verify_phase_records_full_restoration():
    v = json.loads(VERIFY.read_text())
    assert v["n_removed_keys"] == 73
    assert v["n_restored"] == 73
    assert v["n_removed_keys_that_are_updated"] == 11
    assert v["n_removed_non_updated_keys"] == 62
    assert v["n_restored_byte_exact_non_updated"] == 62
    assert v["checks"]["all_removed_keys_present"] is True
    assert v["checks"]["all_non_updated_removed_keys_byte_exact_vs_accepted_base"] is True
    assert v["checks"]["all_updated_keys_present"] is True
    assert v["checks"]["all_updated_keys_changed_from_accepted_base"] is True
    assert v["checks"]["fail_closed_flags_present_and_false"] is True
    assert v["checks"]["accepted_run_id_corrected"] is True
    assert v["checks"]["all_live_evidence_refs_resolve"] is True
    assert v["checks"]["all_live_evidence_refs_are_files"] is True
    assert v["checks"]["frozen_pins_intact"] is True
    assert v["checks"]["cycle_report_references_resolve_if_written"] is True
    assert v["all_checks_hold"] is True
    assert v["verdict"] == "RESUME_AUDIT_READY"
    # the hypothesis hand-count slip stays disclosed, never silently corrected
    assert v["n_removed_keys_per_hypothesis_handcount"] == 71
    assert "73" in v["count_disclosure"]


# ------------------------------------------------- 6. freeze-first discipline --
def test_freeze_record_pins_the_hypothesis_hash():
    fr = json.loads(FREEZE.read_text())
    assert fr["hypothesis_sha256"] == _sha256(HYPOTHESIS)
    assert fr["frozen_before_execution"] is True
    assert fr["no_threshold_or_bar_edits"] is True
    assert fr["zero_new_thresholds"] is True
    assert fr["obsolete_universal_174k_benchmarks_rerun"] is False


def test_frozen_pins_unchanged():
    for rel, expected in FROZEN_PINS.items():
        assert _sha256(REPO / rel) == expected, f"frozen pin drifted: {rel}"


# ------------------------------------------------------- 7. cycle report ------
@needs_report
def test_cycle_report_references_only_existing_paths():
    text = CYCLE_REPORT.read_text()
    tokens = set()
    for line in text.replace("`", "\n").splitlines():
        tok = line.strip()
        if (tok.startswith("results/") or tok.startswith("reports/")
                or tok.startswith("evaluation/") or tok.startswith("tests/")) \
                and " " not in tok and "*" not in tok and not tok.endswith(":"):
            tokens.add(tok)
    assert tokens, "cycle report cites no artifact paths"
    missing = sorted(t for t in tokens if not (REPO / t).exists())
    assert missing == [], f"cycle report cites non-existent paths: {missing}"
