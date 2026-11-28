"""Executable re-derivation of product cycle 46125190884's published claims.

The v68 P0 residual was not a new scoring gate: when stage 2's frozen label
gate abstained, a verified counter-evidence incumbent carrying frozen D2/D3/D4
content defects could stay verified.  This test re-derives, from committed
bytes, that the shipped rejection leg now clears such incumbents on both the
abstention and prior-confirmation paths, that the regenerated flagship family
carries zero fixed-path verified+defective rows, and that the published
histogram, packet-of-record re-emission, report and state all agree.

No historical bundle is rewritten, no frozen gate/rubric/threshold/bar is
re-derived, and no product posture flag is promoted by this evidence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query.counter_evidence_span import frozen_content_defects  # noqa: E402

RUN_ID = "46125190884"
SLUGS = (
    "rent-default",
    "petty-theft-dismissal",
    "corporate-criminal-liability",
    "business-judgment-rule",
)
MODULE = ROOT / "product" / "query" / "counter_evidence_span.py"
UNIT_TEST = ROOT / "product" / "tests" / "test_counter_surface_rejection_v68.py"
PROBE = (ROOT / "results" / "product" / "counter_content_family"
         / f"CYCLE_{RUN_ID}.json")
STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
EXPOSURE = (ROOT / "results" / "product" / "fixture_anchor_exposure"
            / f"CYCLE_{RUN_ID}.json")
LEGACY_SCOPE_TEST = (ROOT / "product" / "tests"
                     / "test_cycle_40234815780.py")
STATE_KEY = f"cycle_{RUN_ID}_stage2_rejection"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_paths() -> list[Path]:
    paths = [
        ROOT / "results" / "product" / "offline_slice" / f"{RUN_ID}-{slug}"
        / f"{slug}.bundle.json"
        for slug in SLUGS
    ]
    paths.append(
        ROOT / "results" / "product" / "server_slice" / RUN_ID
        / "served.bundle.json")
    return paths


def test_shipped_module_carries_the_stage2_content_rejection_leg() -> None:
    src = MODULE.read_text(encoding="utf-8")
    assert "def _reject_stage2_incumbent" in src
    assert 'leg="stage2_prior_recheck"' in src
    assert 'leg="stage2_abstention"' in src
    assert '"n_downgraded": len(downgrades)' in src
    assert '"content_rejection_leg"' in src
    assert '"content_filter": content_filter_provenance()' in src

    tsrc = UNIT_TEST.read_text(encoding="utf-8")
    for needle in ("d2_letterhead_zone", "d3_markup_residue",
                   "d4_language_marker_mismatch", "stage2_prior_recheck",
                   "stage2_abstention"):
        assert needle in tsrc, needle


def test_regenerated_bundles_are_content_clean_and_publish_stage2_provenance(
) -> None:
    for path in _bundle_paths():
        assert path.is_file(), path
        bundle = _load(path)
        for row in bundle.get("decisions") or []:
            if row.get("counter_evidence_verified") is True:
                defects = frozen_content_defects(
                    str(row.get("counter_evidence") or ""), row)
                assert defects == [], (path, row.get("decision_id"), defects)
        prov = bundle["provenance"]
        stage1 = prov["counter_evidence_span"]
        if stage1.get("applied") is True:
            assert "content_filter" in stage1, path
        else:
            # No frozen anchor profile for this query: the observed
            # population is still published and no gate write may happen.
            assert stage1["reason"] == "no_frozen_anchor_profile_for_query", path
            assert stage1["n_candidates"] == 0, path
        stage2 = prov["counter_evidence_span_surface"]
        if stage2.get("applied") is True:
            assert stage2["geometry_touched"] is False
            assert "n_downgraded" in stage2, path
            assert len(stage2.get("downgrades") or []) == stage2["n_downgraded"]
            for rec in stage2.get("downgrades") or []:
                assert rec["leg"] in ("stage2_abstention",
                                      "stage2_prior_recheck")
                assert rec["after"]["counter_evidence_verified"] is False
                assert rec["before"]["counter_evidence_verified"] is True

    # The fixed-path rent bundle must actually exercise the D3 downgrade;
    # a zero-downgrade family could pass the histogram while proving nothing.
    rent = _load(_bundle_paths()[0])
    s1 = rent["provenance"]["counter_evidence_span"]
    assert s1["n_downgraded"] == 1
    assert s1["downgrades"][0]["decision_id"] == "vd_gerichte_JL09.019144"
    assert s1["downgrades"][0]["defects"] == ["D3_markup_residue"]


def test_regenerated_summaries_still_pass_the_shipped_slice_contracts() -> None:
    for slug in SLUGS:
        summary = _load(
            ROOT / "results" / "product" / "offline_slice"
            / f"{RUN_ID}-{slug}" / "summary.json")
        assert summary["verified"] is True, slug
        assert summary["page_contract"] is True, slug
        assert summary["stats"]["n_decisions"] == 100, slug
        assert summary["stats"]["n_clusters"] == 8, slug
        assert summary["stats"]["answer_status"] == "ready", slug
    server = _load(
        ROOT / "results" / "product" / "server_slice" / RUN_ID
        / "summary.json")
    assert server["verdict"] == "PASS"
    assert server["failures"] == []


def test_published_histogram_rederives_the_ordered_work_success_rule() -> None:
    rec = _load(PROBE)
    assert rec["schema"] == "product-content-family-probe/1"
    assert rec["run_id"] == RUN_ID
    assert rec["direction_version"] == 68

    totals = rec["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 54
    assert totals["n_decisions"] == 5400
    assert totals["n_verified"] == 64
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    # Historical evidence is preserved, not erased; the two populations are
    # published side by side so nobody can confuse old bytes with fixed bytes.
    hist = rec["before_after"]["per_class_histogram"]
    assert hist["historical_before_population"]["D2_letterhead_zone"] == 44
    assert hist["historical_before_population"]["D3_markup_residue"] == 31
    assert hist["historical_before_population"]["D4_language_marker_mismatch"] == 7
    assert hist["fixed_path_after_population"] == totals["defect_histogram"]
    assert len(rec["all_committed"]["bundles"]) > totals["n_bundles"]

    ba = rec["before_after"]
    coverage = {r["decision_id"]: r
                for r in ba["per_row"]["accepted_four_coverage"]}
    assert set(coverage) == {
        "gr_gerichte_ERZ 2010 25",
        "bge_BGE_110_II_391",
        "ge_gerichte_CAPH_107_2004",
        "bge_BGE_121_III_260",
    }
    for row in coverage.values():
        assert row["present"] is True
        assert row["before_verified"] is True
        assert row["after_verified"] is False
        assert row["observed_defects"] == row["expected_defects"]
        assert row["after_reason_code"]
    assert ba["per_row"]["all_four_before_verified"] is True
    assert ba["per_row"]["all_four_after_unevidenced"] is True
    assert rec["ordered_work_2_full_success_rule"][
        "accepted_four_before_after_complete"] is True
    assert ba["per_row"]["defect_free_downgrades"] == []
    assert rec["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert rec["confirmed_set"]["defects"] == []
    assert rec["confirmed_set"]["still_verified"] is True
    assert rec["false_reject_count"] == 0
    assert rec["ordered_work_2_success_rule"]["met"] is True
    assert rec["ordered_work_2_full_success_rule"]["met"] is True


def test_packet_v3_bytes_are_unchanged_and_guarded_yield_is_not_reduced() -> None:
    pv = _load(PROBE)["packet_v3_reemission"]
    assert pv["available"] is True
    assert pv["packet"] == "39319405429"
    assert pv["accepted_artifact"] == (
        "results/product/counter_span/CYCLE_39986094168_span_selection.json")
    assert pv["checks"]["packet_bytes_unchanged"] is True
    assert pv["checks"]["baseline_reproduced"] is True
    assert pv["checks"]["guarded_reproduced"] is True
    assert pv["checks"]["unguarded_reproduced"] is True
    assert pv["checks"]["guarded_yield_not_decreased"] is True
    assert pv["checks"]["guarded_emitted_content_clean"] is True

    totals = pv["totals"]
    assert totals["accepted_baseline"] == totals["current_baseline"]
    assert totals["accepted_guarded"] == totals["current_guarded"]
    assert totals["accepted_unguarded"] == totals["current_unguarded"]
    assert totals["current_baseline"]["yield"] == 0.0
    assert totals["current_baseline"]["n_abstained"] == 20
    assert totals["current_guarded"]["yield"] == 0.05
    assert totals["current_guarded"]["n_emitted"] == 1
    assert totals["current_guarded"]["support_rate_among_emitted"] == 1.0
    assert pv["v68_rejection_effect_on_v3"]["total_downgrades"] == 0


def test_anchor_exposure_is_refreshed_for_the_enlarged_family() -> None:
    rec = _load(EXPOSURE)
    assert rec["run_id"] == RUN_ID
    assert rec["direction_version"] == 68
    fixed = rec["populations"]["fixture_fixed_path"]
    assert fixed["n_bundles"] == 54
    assert fixed["n_decisions"] == 5400
    assert rec["decision"]["exposure_rows_on_fixture_fixed_path"] == 44
    assert fixed["n_counter_evidence_verified_flips"] == 10
    assert rec["decision"]["verdict"] == "DO_NOT_CLOSE"
    assert rec["decision"]["pipeline_gate_changed"] is False
    # The earlier cycle's artifact is preserved as historical evidence.
    assert (EXPOSURE.parent / "CYCLE_40272586794.json").is_file()


def test_legacy_write_scope_guard_allows_only_append_only_run_evidence() -> None:
    src = LEGACY_SCOPE_TEST.read_text(encoding="utf-8")
    assert "pending_tracked" in src
    assert "tracked_offenders" in src
    assert "pending_untracked" in src
    assert r're.search(r"\d{10,}", part)' in src
    assert "append-only under a run-id" in src


def test_state_record_is_written_and_posture_stays_fail_closed() -> None:
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    # The legacy pointer still names the last accepted executing run; this
    # cycle is recorded in its own append-only block so no older cycle test
    # is broken by a moving pointer.
    assert st["current_cycle_run_id"] == 40284658455
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert st[flag] is False, flag

    rec = st[STATE_KEY]
    assert rec["schema"] == "product-cycle-stage2-rejection/1"
    assert rec["run_id"] == int(RUN_ID)
    assert rec["direction_version"] == 68
    assert rec["ordered_work_item"] == 2
    assert rec["defect_population"]["fixed_path_n_bundles"] == 54
    assert rec["defect_population"]["n_verified_defective"] == 0
    assert rec["defect_population"]["false_reject_count"] == 0
    assert rec["posture"]["human_gate_ready"] is False
    assert rec["posture"]["continue_recommended"] is True
    assert any(d.startswith("CONTROL_PLANE_ACCEPTED_CYCLE_DIVERGENCE")
               for d in rec["disclosures"])
    for rel in rec["artifacts"] + rec["slice_dirs"]:
        assert (ROOT / rel).exists(), rel


def test_report_of_record_cites_only_artifacts_that_exist() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert f"Cycle {RUN_ID}" in text
    assert "CONTROL_PLANE_ACCEPTED_CYCLE_DIVERGENCE" in text
    for needle in ("54 bundles", "5400 decisions", "0 verified+defective",
                   "false rejects: 0", "yield 0.05", "REPORTED-ONLY",
                   "human_gate_ready=false"):
        assert needle in text, needle
    for rel in (
        "product/query/counter_evidence_span.py",
        "product/tests/test_counter_surface_rejection_v68.py",
        f"results/product/counter_content_family/CYCLE_{RUN_ID}.json",
        f"results/product/fixture_anchor_exposure/CYCLE_{RUN_ID}.json",
        f"results/product/offline_slice/{RUN_ID}-rent-default/rent-default.bundle.json",
        f"results/product/server_slice/{RUN_ID}/served.bundle.json",
    ):
        assert rel in text, rel
        assert (ROOT / rel).is_file(), rel
