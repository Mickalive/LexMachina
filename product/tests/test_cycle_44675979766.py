"""Cycle 44675979766 — operational resume of the failed run 44669305676.

Re-derives, from committed artifacts only, every number published in
``reports/product/CYCLE_44675979766.md``:

1. the inherited snapshot's 48-file delta composition (4 slice + 44 cache,
   zero report/test/state) and its UNADJUDICATED status, from git refs;
2. the two inherited regenerated bundles are valid and preserved verbatim
   (100 decisions, 8 clusters, coordinates + source links on every row;
   map-only answer pending; full-loop answer ready with 4 citations, the span
   seam applied and the pivot_absent incumbent downgraded);
3. the frozen D1-D4 re-probe over the fixed-path family (D2=D3=D4=0, zero
   verified+defective rows, zero false rejects, success rule met) and the
   accepted four before/after rows plus the one sound row;
4. the real-subprocess progressive smoke (23/23) and the DOM clickable-map
   check inputs (bundle shape);
5. the fail-closed product state and the unchanged accepted pointer.

No network, no model, no paid dependency, no frozen bar re-scored here.  The
probe artifact is itself a product-owned execution over the frozen predicates,
so the test reads its committed output rather than re-deriving the frozen gate.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RESUME = "44675979766"
RESUMED = "44669305676"
SNAPSHOT = "64c468c88df4eed21e2673dca5a06ff9256a7ad9"
PREDECESSOR = "d8c85eeaf51dbc567e6a9886e19eb012ca172240"


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), check=True,
                          capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------- #
# 1. orchestration / validation diagnosis
# --------------------------------------------------------------------------- #

def test_snapshot_refs_and_adjudication_are_as_published():
    diag = _load("results/product/orchestration/"
                 f"CYCLE_{RESUME}_resume_diagnosis.json")
    assert diag["run_id"] == RESUMED
    assert diag["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert diag["orchestration"]["mechanism_unobserved"] is True
    dd = diag["durable_delta"]
    assert dd["snapshot_head"] == SNAPSHOT
    assert dd["predecessor_head"] == PREDECESSOR
    assert dd["classification"] == "COMMITTED_DELTA"
    assert dd["changed_files"] == 48
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["audit"]["gate_file_present"] is False
    assert adj["accept"]["accept_commit"] is None


def test_delta_composition_has_no_report_test_or_state_file():
    gap = _load("results/product/orchestration/"
                f"CYCLE_{RESUME}_validation_gap.json")
    comp = gap["delta_composition_recomputed_from_git"]
    assert comp["total_changed_files"] == 48
    assert comp["by_prefix"]["results/product/offline_slice/"] == 4
    assert comp["by_prefix"]["results/product/query_cache/"] == 44
    assert comp["by_prefix"]["reports/"] == 0
    assert comp["by_prefix"]["product/tests/"] == 0
    assert comp["by_prefix"]["state/"] == 0
    assert comp["report_test_state_paths"] == []
    assert gap["inherited_work_verdict"]["status"] == "PRESERVED_AND_VERIFIED"
    assert gap["inherited_work_verdict"]["not_restarted"] is True
    assert gap["orchestration_mechanism_ceiling"]["mechanism_unobserved"] is True


def test_delta_composition_reproduces_from_git_refs():
    paths = _git("diff", "--name-only", PREDECESSOR, SNAPSHOT).splitlines()
    assert len(paths) == 48
    assert sum(p.startswith("results/product/offline_slice/") for p in paths) == 4
    assert sum(p.startswith("results/product/query_cache/") for p in paths) == 44
    assert not [p for p in paths if p.startswith(("reports/", "product/tests/", "state/"))]


def test_no_gate_was_minted_for_this_resume():
    assert not (ROOT / f"results/audit/product/CYCLE_{RESUMED}_GATE.json").exists()
    assert not (ROOT / f"results/audit/product/CYCLE_{RESUME}_GATE.json").exists()
    assert not (ROOT / f"reports/audit/product/CYCLE_{RESUME}.md").exists()


# --------------------------------------------------------------------------- #
# 2. inherited regenerated bundles are valid
# --------------------------------------------------------------------------- #

MAP_ONLY = "results/product/offline_slice/20261120T034309Z/rent-default.bundle.json"
FULL_LOOP = "results/product/offline_slice/20261120T034311Z/rent-default.bundle.json"


def test_inherited_bundles_have_clickable_map_shape():
    for rel in (MAP_ONLY, FULL_LOOP):
        doc = _load(rel)
        decisions = doc["decisions"]
        assert len(decisions) == 100, rel
        assert len(doc["clusters"]) == 8, rel
        assert all(d.get("x") is not None and d.get("y") is not None
                   for d in decisions), rel
        assert all(d.get("cluster_id") is not None for d in decisions), rel
        assert all(d.get("canonical_url") for d in decisions), rel


def test_inherited_summaries_rederive_from_bundle_bytes():
    for rel in (MAP_ONLY, FULL_LOOP):
        summary = _load(rel.replace("rent-default.bundle.json", "summary.json"))
        doc = _load(rel)
        assert summary["verified"] is True
        assert summary["stats"]["n_decisions"] == len(doc["decisions"]) == 100
        assert summary["stats"]["n_clusters"] == len(doc["clusters"]) == 8
        assert summary["stats"]["rows_with_xy"] == 100
        assert summary["stats"]["rows_with_source_link"] == 100
        assert summary["stats"]["fixture_replay_cache_misses"] == 0


def test_map_only_bundle_makes_no_answer_or_counter_claim():
    doc = _load(MAP_ONLY)
    assert doc["answer"]["status"] == "pending"
    assert doc["answer"]["cited_decision_ids"] == []
    assert not [d for d in doc["decisions"]
                if d.get("counter_status") not in (None, "none")]


def test_full_loop_bundle_carries_applied_span_seam_and_downgrade():
    doc = _load(FULL_LOOP)
    assert doc["answer"]["status"] == "ready"
    assert len(doc["answer"]["cited_decision_ids"]) == 4
    span = doc["provenance"]["counter_evidence_span"]
    assert span["applied"] is True
    assert "vd_gerichte_JL09.019144" in span["abstained_ids"]
    assert span["abstention_reasons"] == {"pivot_absent": 1}
    row = next(d for d in doc["decisions"]
               if d["decision_id"] == "vd_gerichte_JL09.019144")
    assert row["counter_evidence_verified"] is False
    assert row["counter_evidence_unevidenced_reason"] == "pivot_absent"


# --------------------------------------------------------------------------- #
# 3. frozen D1-D4 content-family re-probe
# --------------------------------------------------------------------------- #

FAMILY = "results/product/resume_44675979766/counter_content_family.json"


def test_fixed_path_family_success_rule_met():
    fam = _load(FAMILY)
    assert fam["run_id"] == RESUME
    assert fam["direction_version"] == 68
    fp = fam["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 50
    assert fp["n_decisions"] == 5000
    assert fp["n_verified_defective"] == 0
    hist = fp["defect_histogram"]
    assert [hist[k] for k in ("D2_letterhead_zone", "D3_markup_residue",
                              "D4_language_marker_mismatch")] == [0, 0, 0]
    assert fam["false_reject_count"] == 0
    rule = fam["ordered_work_2_full_success_rule"]
    assert rule["met"] is True
    assert rule["accepted_four_before_after_complete"] is True
    assert rule["confirmed_sound_row_still_verified"] is True
    assert rule["guarded_arm_yield_not_decreased"] is True
    assert rule["packet_v3_bytes_unchanged"] is True


def test_accepted_four_before_after_and_sound_row():
    per_row = _load(FAMILY)["before_after"]["per_row"]
    assert per_row["all_four_present"] is True
    assert per_row["all_four_before_verified"] is True
    assert per_row["all_four_after_unevidenced"] is True
    assert per_row["defect_free_downgrades"] == []
    cov = {r["decision_id"]: r for r in per_row["accepted_four_coverage"]}
    assert set(cov) == {
        "gr_gerichte_ERZ 2010 25", "bge_BGE_110_II_391",
        "ge_gerichte_CAPH_107_2004", "bge_BGE_121_III_260",
    }
    for r in cov.values():
        assert r["before_verified"] is True
        assert r["after_verified"] is False
        assert r["observed_defects"] == r["expected_defects"]
        assert r["after_reason_code"]
    sound = per_row["sound_row"]
    assert sound["decision_id"] == "bstger_SK.2023.49"
    assert sound["defects"] == []
    assert sound["still_verified"] is True


def test_historical_defects_are_disclosed_not_repaired():
    totals = _load(FAMILY)["all_committed"]["totals"]
    hist = totals["defect_histogram"]
    assert (hist["D2_letterhead_zone"], hist["D3_markup_residue"],
            hist["D4_language_marker_mismatch"]) == (44, 31, 7)


def test_frozen_predicates_are_rehashed_not_rederived():
    prov = _load(FAMILY)["frozen_predicate_provenance"]
    assert prov["frozen_hypothesis_sha256"] == (
        "734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881")
    assert prov["predicate_source_sha256"] == (
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d")
    assert prov["predicate_source"] == "evaluation/counter_evidence_quality_benchmark.py"
    assert "never edits the frozen confirm-or-abstain gate" in prov["alignment"]


# --------------------------------------------------------------------------- #
# 4. progressive smoke + packet v3
# --------------------------------------------------------------------------- #

def test_progressive_smoke_passed_over_real_socket():
    smoke = _load("results/product/resume_44675979766/progressive_smoke.json")
    assert smoke["run_id"] == RESUME
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert smoke["failures"] == []
    assert smoke["timings_s"]["server_boot_s"] < 60
    assert smoke["timings_s"]["start_s"] < 120
    assert "no live OpenCaseLaw latency claim" in smoke["claim_ceiling"]


def test_stale_baseline_diagnosis_is_disclosed_not_hidden():
    # The query_map_diagnosis instrument still pins expected accepted cycle
    # CYCLE_40247189361 and older fresh-bundle paths.  Its FAIL is a stale
    # baseline, not a new product finding and not a gate input; preserve it.
    diag = _load("results/product/query_map_diagnosis/CYCLE_44675979766.json")
    assert diag["run_id"] == RESUME
    assert diag["verdict"] == "FAIL"
    sp = diag["state_pointer"]
    assert sp["accepted_run_id"] == "CYCLE_40284658455"
    assert sp["expected_accepted_run_id"] == "CYCLE_40247189361"
    assert sp["matches_latest_accepted"] is False
    checks = diag["checks"]
    assert checks["posture_stays_fail_closed"] is True
    assert checks["this_run_has_no_audit_gate"] is True
    assert checks["probe_full_success_rule_met"] is True
    assert checks["probe_fixed_family_D2_D3_D4_are_zero"] is True
    assert "does not re-run an evaluation finding" in diag["claim_ceiling"]


def test_packet_v3_guarded_arm_yield_unchanged():
    totals = _load(FAMILY)["packet_v3_reemission"]["totals"]
    assert totals["accepted_guarded"]["yield"] == 0.05
    assert totals["current_guarded"]["yield"] == 0.05
    assert totals["accepted_unguarded"]["yield"] == 0.3
    assert totals["current_unguarded"]["yield"] == 0.3
    assert totals["accepted_guarded"]["support_rate_among_emitted"] == 1.0
    assert totals["current_guarded"]["support_rate_among_emitted"] == 1.0


# --------------------------------------------------------------------------- #
# 5. state posture unchanged
# --------------------------------------------------------------------------- #

def test_posture_and_accepted_pointer_unchanged():
    st = _load("state/product.json")
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == "CYCLE_40284658455"
    assert st["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    assert st["continue_recommended"] is True
    block = st["cycle_44675979766_operational_resume"]
    assert block["resumed_run_id"] == int(RESUMED)
    assert block["current_run_id"] == int(RESUME)
    assert block["direction_version"] == 68
    assert block["claim_impact"] == "none: fail-closed posture and accepted pointer unchanged"
    for key in ("product/resume_snapshot_diagnosis.py -> results/product/orchestration/CYCLE_44675979766_resume_diagnosis.json",
                "results/product/orchestration/CYCLE_44675979766_validation_gap.json",
                "product/content_family_probe.py -> results/product/resume_44675979766/counter_content_family.json",
                "product/progressive_smoke.py -> results/product/resume_44675979766/progressive_smoke.json",
                "product/tests/test_cycle_44675979766.py",
                "reports/product/CYCLE_44675979766.md"):
        assert key in st["evidence_refs"], key
