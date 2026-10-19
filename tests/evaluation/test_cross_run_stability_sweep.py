"""Tests for evaluation.cross_run_stability_sweep (run 39322925971).

The sweep answers one falsifiable question that the accepted P1 finding of
cycle 39315343123 left open: is FR counter-authority RUN-INSTABILITY an
ISOLATED counter-stage defect, or is run-to-run instability SYSTEMIC in the
product's live query pipeline?  Every gate predicate is IMPORTED from the
accepted mapping-free falsifier; the claim-bearing metric is VERDICT
DIVERGENCE under that already-accepted gate contract; every overlap / rank /
cluster / language number is REPORTED-ONLY and can never flip the exit code.

These tests pin:
* the freeze-first contract (hypothesis + freeze record digests re-derive);
* the frozen population partition (exactly 2 same-query groups of 2, from the
  hypothesis's own pinned query_text fields — no mount read required);
* the non-vacuity battery V1-V5 (the divergence detector fires on a hostile
  synthetic group and stays silent on an identical one);
* NOT_APPLICABLE is never a verdict and never counts toward either exit;
* cross-query comparison is structurally impossible (grouping key equality);
* frozen-pin and population drift both fail closed to exit 2;
* the unserved packet 39275520116 is never touched by the sweep.

All tests here are MOUNT-INDEPENDENT unless marked ``needs_mount``; the
mount-dependent end-to-end run re-executes into a SCRATCH path and never
overwrites the committed claim-bearing record.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import cross_run_stability_sweep as S  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")

SCORED = ["candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting"]

FROZEN_DIALECT = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_benchmark": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "freeze_record": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    "mf_freeze": "431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5",
    "frozen_cells": "f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75",
}


def _hyp() -> dict:
    return json.loads((REPO / S.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))


def _freeze() -> dict:
    return json.loads((REPO / S.FREEZE_RELPATH).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. freeze-first contract
# --------------------------------------------------------------------------- #
def test_hypothesis_and_freeze_record_exist_and_pin_accepted_digests():
    h, f = _hyp(), _freeze()
    assert h["frozen_before_claim_bearing_execution"] is True
    assert h["github_run"] == "39322925971"
    assert h["lane"] == "evaluation"
    assert h["direction_version"] == 58
    pins = f["frozen_inputs_rehashed_before_execution"]
    assert pins["evaluation/frozen_bars/RULES_LABEL.json"] == FROZEN_DIALECT["rules_label"]
    assert pins["evaluation/frozen_bars/RULES_GEOMETRY.json"] == FROZEN_DIALECT["rules_geometry"]
    assert (pins["evaluation/retrieval_gate/frozen_retrieval_benchmark.json"]
            == FROZEN_DIALECT["frozen_benchmark"])
    assert (pins["evaluation/retrieval_gate/FREEZE_RECORD.json"]
            == FROZEN_DIALECT["freeze_record"])
    assert (pins["evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"]
            == FROZEN_DIALECT["mf_freeze"])
    assert (pins["results/evaluation/retrieval_benchmark/39117425713.json"]
            == FROZEN_DIALECT["frozen_cells"])
    actual = hashlib.sha256((REPO / S.HYPOTHESIS_RELPATH).read_bytes()).hexdigest()
    assert f["hypothesis_sha256"] == actual, "freeze record must pin the live hypothesis bytes"


def test_hypothesis_forbids_every_preemption_and_every_new_threshold():
    h = _hyp()
    prohibited = " ".join(h["prohibited"]).lower()
    for needle in ("39275520116", "threshold", "owner", "174k", "frontier"):
        assert needle in prohibited, f"prohibition list must name {needle!r}"
    assert h["metrics_frozen"]["no_new_thresholds"].startswith("ZERO thresholds")
    assert "diagnostics_never_gate" in h["falsification_rule"]


def test_hypothesis_pins_the_accepted_baseline_measurement():
    h = _hyp()
    base = h["gates_reused_not_rederived"]["accepted_baseline_measurement"]
    assert ("results/evaluation/stand_ready_multilingual_probe/39315343123.json"
            in base)
    assert h["baseline"].startswith("The accepted per-run stand-ready measurement")


# --------------------------------------------------------------------------- #
# 2. frozen population partition (V4) — from the hypothesis's own pinned fields
# --------------------------------------------------------------------------- #
def test_population_partition_is_exactly_two_groups_of_two():
    h = _hyp()
    runs = h["population_pinned_before_execution"]["live_runs"]
    assert len(runs) == 4
    keys = [S.normalise_query(r["query_text"]) for r in runs]
    groups: dict[str, list[str]] = {}
    for r, k in zip(runs, keys):
        groups.setdefault(k, []).append(r["run"])
    assert len(groups) == 2, "exactly two same-query groups are expected"
    assert sorted(len(v) for v in groups.values()) == [2, 2]
    exp = h["population_pinned_before_execution"]["expected_groups"]
    assert exp["expected_n_groups"] == 2


def test_population_entries_carry_unique_digests_for_record_and_bundle():
    h = _hyp()
    runs = h["population_pinned_before_execution"]["live_runs"]
    rec = [r["record_sha256"] for r in runs]
    bun = [r["bundle_sha256"] for r in runs]
    assert len(set(rec)) == 4 and len(set(bun)) == 4
    for r in runs:
        assert len(r["record_sha256"]) == 64 and len(r["bundle_sha256"]) == 64
        assert r["record"].endswith(".json") and r["bundle"].endswith("_bundle.json")


def test_mount_head_is_the_accepted_product_head():
    h = _hyp()
    assert (h["population_pinned_before_execution"]["product_mount_head"]
            == "6c4b8f7d8100871499de0c8465f959d9bab29215")


# --------------------------------------------------------------------------- #
# 3. non-vacuity battery
# --------------------------------------------------------------------------- #
def test_non_vacuity_battery_all_controls_hold():
    vac = S.non_vacuity(SCORED)
    names = [c["control"] for c in vac["controls"]]
    assert names == ["V1_divergence_detector_must_fire",
                     "V2_identical_runs_must_not_fire",
                     "V3_not_applicable_is_never_a_verdict"]
    assert vac["all_hold"] is True
    for c in vac["controls"]:
        assert c["holds"] is True, f"{c['control']} must hold: {c['why']}"


def test_v1_the_divergence_detector_actually_fires():
    vac = S.non_vacuity(SCORED)
    v1 = vac["controls"][0]
    assert v1["measured"]["run_a_passed"] is True
    assert v1["measured"]["run_b_passed"] is False


# --------------------------------------------------------------------------- #
# 4. gate contract: NOT_APPLICABLE is never a verdict
# --------------------------------------------------------------------------- #
def _row(did: str, status: str = "none", evidence: str = "", rank: int = 0,
         cluster: int = 0, lang: str = "de") -> dict:
    return {
        "decision_id": did, "canonical_url": f"https://example.invalid/{did}",
        "title": did, "counter_status": status, "counter_evidence": evidence,
        "language": lang, "rank": rank, "cluster_id": cluster,
    }


def test_stage_not_run_yields_not_applicable_and_no_verdict():
    bundle = {"query": "Q", "decisions": [_row("a")], "clusters": []}
    record = {"query": "Q", "stages_executed": {"counter_authority": False},
              "counters": {"counter_authorities": 0, "by_status": {"none": 1}}}
    run = S.evaluate_run(record, bundle, SCORED, "r1")
    g = next(x for x in run["gates"] if x["gate"] == "sr::counter_authority_surface")
    assert g["passed"] is None
    assert run["counter_stage_applicable"] is False
    assert "NOT_APPLICABLE" in g["qualification"]


def test_applicable_gate_reads_scored_statuses_from_the_argument_not_a_hardcode():
    bundle = {"query": "Q",
              "decisions": [_row("a", "candidate-contrary", "contra evidence")],
              "clusters": []}
    record = {"query": "Q", "counters": {"counter_authorities": 1,
                                         "by_status": {"candidate-contrary": 1}}}
    run = S.evaluate_run(record, bundle, SCORED, "r1")
    g = next(x for x in run["gates"] if x["gate"] == "sr::counter_authority_surface")
    assert g["passed"] is True
    assert (g["measured"]["scored_statuses_from_frozen_rubric"] == SCORED)


def test_language_robustness_is_reported_only_never_a_verdict():
    bundle = {"query": "Q", "decisions": [_row("a", lang="")], "clusters": []}
    record = {"query": "Q", "counters": {"counter_authorities": 0,
                                         "by_status": {"none": 1}}}
    run = S.evaluate_run(record, bundle, SCORED, "r1")
    g = next(x for x in run["gates"] if x["gate"] == "sr::language_robustness")
    assert g["passed"] is None
    assert "REPORTED-ONLY" in g["qualification"]


# --------------------------------------------------------------------------- #
# 5. grouping: cross-query comparison is structurally impossible
# --------------------------------------------------------------------------- #
def test_grouping_key_is_nfkc_normalised_query_text():
    assert S.normalise_query("Kündigung Mietvertrag") == S.normalise_query("Kündigung Mietvertrag")
    assert S.normalise_query("  Q  ") == S.normalise_query("Q")
    assert S.normalise_query({"text": "Q"}) == S.normalise_query("Q")
    assert S.normalise_query("Q1") != S.normalise_query("Q2")


def test_group_runs_never_mixes_different_queries():
    entries = [
        {"run": "a1", "record": "x", "bundle": "y"},
        {"run": "a2", "record": "x", "bundle": "y"},
        {"run": "b1", "record": "x", "bundle": "y"},
    ]
    loaded = {
        "a1": {"query_key": "Query A"},
        "a2": {"query_key": "Query A"},
        "b1": {"query_key": "Query B"},
    }
    groups = S.group_runs(entries, loaded)
    assert sorted(groups) == ["Query A", "Query B"]
    assert groups["Query A"] == ["a1", "a2"]
    assert groups["Query B"] == ["b1"]


# --------------------------------------------------------------------------- #
# 6. reported-only diagnostics never invent instability
# --------------------------------------------------------------------------- #
def test_pair_diagnostics_on_identical_bundles_are_exactly_zero():
    rows = [_row("a", "cited", "ev", 0), _row("b", "none", "", 1, lang="fr")]
    a = {"query": "Q", "decisions": copy.deepcopy(rows), "clusters": []}
    b = {"query": "Q", "decisions": copy.deepcopy(rows), "clusters": []}
    d = S.pair_diagnostics(a, b)
    assert d["jaccard"] == 1.0
    assert d["n_only_a"] == 0 and d["n_only_b"] == 0
    assert d["rank"]["n_rank_changed"] == 0
    assert d["cluster"]["n_reassigned"] == 0
    assert d["counter_status_changes"]["n_changed"] == 0
    assert all(v == 0 for v in d["language_delta"].values())
    assert d["qualification"].startswith("REPORTED-ONLY")


def test_pair_diagnostics_reports_membership_and_cluster_movement():
    a = {"query": "Q", "decisions": [_row("a", rank=0, cluster=0), _row("b", rank=1, cluster=0)],
         "clusters": []}
    b = {"query": "Q", "decisions": [_row("a", rank=0, cluster=1), _row("c", rank=1, cluster=1)],
         "clusters": []}
    d = S.pair_diagnostics(a, b)
    assert d["n_common"] == 1
    assert d["n_only_a"] == 1 and d["n_only_b"] == 1
    assert d["only_a_examples"] == ["b"] and d["only_b_examples"] == ["c"]
    assert d["cluster"]["n_reassigned"] == 1
    assert d["cluster"]["reassigned_examples"] == ["a"]


# --------------------------------------------------------------------------- #
# 7. fail-closed behaviour: pin drift and population drift -> exit 2
# --------------------------------------------------------------------------- #
def test_verify_frozen_pins_detects_a_mutated_input(tmp_path):
    fake_repo = tmp_path / "repo"
    (fake_repo / "evaluation" / "frozen_bars").mkdir(parents=True)
    (fake_repo / "evaluation" / "frozen_bars" / "RULES_LABEL.json").write_text(
        "{}", encoding="utf-8")
    freeze = {"frozen_inputs_rehashed_before_execution": {
        "evaluation/frozen_bars/RULES_LABEL.json": FROZEN_DIALECT["rules_label"]},
        "hypothesis_sha256": "0" * 64}
    res = S.verify_frozen_pins(fake_repo, freeze)
    assert res["all_match"] is False
    assert any(not c["match"] for c in res["checks"])


def test_verify_population_detects_a_mutated_record(tmp_path):
    mount = tmp_path / "mount"
    (mount / "results" / "product" / "live_slice").mkdir(parents=True)
    p = mount / "results" / "product" / "live_slice" / "r.json"
    p.write_text("{}", encoding="utf-8")
    hypothesis = {"population_pinned_before_execution": {
        "product_mount_head": None,
        "live_runs": [{"run": "r", "record": "results/product/live_slice/r.json",
                       "record_sha256": "f" * 64,
                       "bundle": "results/product/live_slice/r_bundle.json",
                       "bundle_sha256": "e" * 64}]}}
    res = S.verify_population(mount, hypothesis)
    assert res["all_match"] is False
    assert any(not c["match"] for c in res["files"])


def test_verdict_contract_exit_codes_are_the_frozen_three():
    h = _hyp()
    vc = h["verdict_contract"]
    assert set(vc) == {"exit_0", "exit_1", "exit_2"}
    assert "STABILITY_NOT_GENERALIZED" in vc["exit_0"]
    assert "RUN_INSTABILITY_GENERALIZED" in vc["exit_1"]
    assert "ENVIRONMENT_OR_VACUOUS" in vc["exit_2"]
    assert S.EXIT_STABLE == 0 and S.EXIT_GENERALIZED == 1 and S.EXIT_ENVIRONMENT == 2


# --------------------------------------------------------------------------- #
# 8. claim ceiling: the unserved packet is never touched
# --------------------------------------------------------------------------- #
def test_hypothesis_and_instrument_never_touch_the_unserved_packet():
    h = _hyp()
    assert "39275520116" in " ".join(h["prohibited"])
    src = (REPO / "evaluation" / "cross_run_stability_sweep.py").read_text(encoding="utf-8")
    # the instrument may NAME the packet in its withheld-status note, but must
    # never construct a filesystem path into any gate_packet directory
    assert '"gate_packet"' not in src, "no gate_packet path component may appear"
    assert "'gate_packet'" not in src, "no gate_packet path component may appear"
    assert "gate_packet/" not in src
    assert "WITHHELD_PENDING_SERVE" in src


def test_claim_ceiling_keeps_every_gate_closed():
    h = _hyp()
    cc = h["claim_ceiling"].lower()
    for needle in ("human_gate_ready stays false", "admission stays fail-closed",
                   "owner_decision_required stays false", "does not move the frozen"):
        assert needle in cc


# --------------------------------------------------------------------------- #
# 9. reuse: predicates are imported, never re-implemented
# --------------------------------------------------------------------------- #
def test_instrument_imports_predicates_and_reimplements_none():
    src = (REPO / "evaluation" / "cross_run_stability_sweep.py").read_text(encoding="utf-8")
    for name in ("concept_coverage", "source_validity", "duplicate_suppression",
                 "counter_authority_surface", "language_robustness",
                 "counter_stage_applicability"):
        assert f"from evaluation" in src
        assert name in src
    # no local def may shadow the imported predicates
    for name in ("concept_coverage", "source_validity", "duplicate_suppression",
                 "counter_authority_surface", "language_robustness"):
        assert f"def {name}(" not in src


def test_instrument_declares_the_frozen_exit_codes_in_its_docstring():
    src = (REPO / "evaluation" / "cross_run_stability_sweep.py").read_text(encoding="utf-8")
    assert "STABILITY_NOT_GENERALIZED" in src
    assert "RUN_INSTABILITY_GENERALIZED" in src
    assert "ENVIRONMENT_OR_VACUOUS" in src


# --------------------------------------------------------------------------- #
# 10. mount-dependent scratch re-execution (never overwrites the claim record)
# --------------------------------------------------------------------------- #
@needs_mount
def test_scratch_rerun_reproduces_the_committed_record(tmp_path):
    committed = (REPO / "results" / "evaluation" / "cross_run_stability_sweep"
                 / "39322925971.json")
    if not committed.is_file():
        pytest.skip("claim-bearing record not present in this checkout")
    out = tmp_path / "scratch.json"
    proc = __import__("subprocess").run(
        [sys.executable, str(REPO / "evaluation" / "cross_run_stability_sweep.py"),
         "--mount", str(MOUNT), "--run-id", "scratch-rerun", "--out", str(out)],
        capture_output=True, text=True, timeout=300)
    fresh = json.loads(out.read_text(encoding="utf-8"))
    old = json.loads(committed.read_text(encoding="utf-8"))
    assert fresh["verdict"] == old["verdict"]
    assert fresh["n_groups_comparable"] == old["n_groups_comparable"]
    assert fresh["n_groups_divergent"] == old["n_groups_divergent"]
    assert fresh["frozen_pin_verification"]["all_match"] is True
    assert fresh["population_pin_verification"]["all_match"] is True
    assert fresh["non_vacuity"]["all_hold"] is True
    assert proc.returncode == old["exit_code"]
