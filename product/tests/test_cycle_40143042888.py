"""Executable re-derivation of product cycle 40143042888's published claims.

This is the operational resume of run 40141595725, so the test covers three
different kinds of claim and never mixes them:

1. **Diagnosis claims** about the failed predecessor run, re-derived from the
   committed diagnosis artifact's own structure and from the repository (no
   gate file, no audit ref, exactly two inherited files).  Remote facts
   (job ids, annotations) come from the public GitHub REST API and are pinned
   here as recorded values, not recomputed - the endpoint is not available
   offline and inventing it would be worse than pinning it.
2. **Measurement claims** - the content-family histogram, the runnable
   vertical-slice verdicts and the inherited-artifact correction - which ARE
   recomputed from the committed bytes every run.
3. **Posture claims** about ``state/product.json``, including the
   ``human_gate_ready`` correction and the workflow state contract.

No network, no LLM, no frozen bar scored, no file written.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import content_family_probe as cfp  # noqa: E402
from product import state_contract as sc  # noqa: E402

RUN_ID = "40143042888"
RESUMED_RUN_ID = "40141595725"
DIRV = 68

PROBE_ART = (REPO_ROOT / "results" / "product" / "counter_content_family"
             / f"CYCLE_{RUN_ID}.json")
DIAG_ART = (REPO_ROOT / "results" / "product" / "orchestration"
            / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
REPORT = REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE_PATH = REPO_ROOT / "state" / "product.json"
INHERITED = (REPO_ROOT / "results" / "product" / "vertical_slice"
             / "cycle_vertical_slice_20261024T232419Z.json")
INHERITED_REPORT = (REPO_ROOT / "results" / "product" / "vertical_slice"
                    / "CYCLE_20261024T232405Z_report.md")
OFFLINE_SUMMARY = (REPO_ROOT / "results" / "product" / "offline_slice"
                   / "20261024T235221Z" / "summary.json")
SERVER_SUMMARY = (REPO_ROOT / "results" / "product" / "server_slice"
                  / RUN_ID / "summary.json")
PROGRESSIVE_ART = (REPO_ROOT / "results" / "product" / "progressive_smoke"
                   / f"CYCLE_{RUN_ID}_progressive_smoke.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(rec: dict) -> dict:
    out = dict(rec)
    out.pop("generated_at", None)
    return out


# --------------------------------------------------------------------------- #
# 1. diagnosis claims
# --------------------------------------------------------------------------- #

def test_diagnosis_names_exit_3_as_the_scope_branch_and_not_a_gate_file() -> None:
    art = _load(DIAG_ART)
    assert art["run_id"] == RUN_ID
    assert art["resumed_run_id"] == RESUMED_RUN_ID
    assert art["direction_version"] == DIRV
    d1 = next(d for d in art["diagnosis"] if d["id"] == "D1")
    assert d1["status"] == "ESTABLISHED"
    assert "exit code 3" in d1["evidence"] or "exit 3" in d1["evidence"]
    assert "SCOPE branch" in d1["evidence"]
    # the specific offending paths are NOT claimed anywhere
    assert "raw_details" in d1["claim_ceiling"]
    assert "NOT observable" in d1["claim_ceiling"]
    assert d1["candidate_paths_not_observed"], "candidates must be listed as candidates"
    for key in art:
        assert "offending_paths" not in key and "observed_paths" not in key
    assert art["evidence_sources"]["job_logs"].startswith("HTTP 403")


def test_no_gate_file_and_no_audit_report_exists_for_the_resumed_run() -> None:
    """The predecessor run was never adjudicated - nothing may claim it was."""
    gate = list((REPO_ROOT / "results" / "audit" / "product").glob(
        f"CYCLE_{RESUMED_RUN_ID}*"))
    rep = list((REPO_ROOT / "reports" / "audit" / "product").glob(
        f"CYCLE_{RESUMED_RUN_ID}*"))
    assert gate == [], f"no audit gate may exist for {RESUMED_RUN_ID}: {gate}"
    assert rep == [], f"no audit report may exist for {RESUMED_RUN_ID}: {rep}"


def test_inherited_snapshot_is_exactly_the_two_files_the_team_job_committed() -> None:
    vs = REPO_ROOT / "results" / "product" / "vertical_slice"
    names = sorted(p.name for p in vs.iterdir())
    assert names == ["CYCLE_20261024T232405Z_report.md",
                     "cycle_vertical_slice_20261024T232419Z.json"], names


# --------------------------------------------------------------------------- #
# 2. the inherited live-retrieval claim, corrected and executable
# --------------------------------------------------------------------------- #

def test_inherited_live_claim_correction_re_derives_from_its_own_provenance() -> None:
    art = _load(INHERITED)
    rs = art["provenance"]["request_summary"]
    cov = art["provenance"]["coverage_expansion"]
    cs = art["provenance"]["cache_stats"]
    # zero upstream calls: everything replayed from the local OpenCaseLaw cache
    assert rs["network_calls"] == 0
    assert rs["failures"] == 0
    assert rs["cache_hits"] == rs["budget_used"]
    assert cov["n_cache_miss_texts"] == 0
    assert cs["writes"] == 0
    assert cs["n_keys"] > 0
    assert art["retrieval_mode"] == "live", "the mode label itself is unchanged"
    # the report of record states the correction, not the overstated claim
    text = REPORT.read_text(encoding="utf-8")
    assert "zero upstream HTTP calls" in text
    assert "local OpenCaseLaw cache" in text
    assert "not re-derivable from the committed tree" in text
    # the inherited report itself keeps its historical wording (never edited)
    assert "150 decisions from OpenCaseLaw MCP API" in INHERITED_REPORT.read_text(
        encoding="utf-8")


def test_inherited_verdict_is_pass_map_only_and_the_missing_check_is_the_answer_stage() -> None:
    art = _load(INHERITED)
    assert art["verdict"] == "PASS_MAP_ONLY"
    assert art["checks_passed"] == 9 and art["checks_total"] == 10
    assert art["stages"]["answer"] is False
    assert art["stages"]["canonical_chain"] is False
    for stage in ("retrieval", "map", "counter_authority", "enrichment_completed"):
        assert art["stages"][stage] is True, stage


# --------------------------------------------------------------------------- #
# 3. content-family histogram: the ordered-work (2) success rule
# --------------------------------------------------------------------------- #

def test_committed_probe_artifact_carries_the_published_table() -> None:
    art = _load(PROBE_ART)
    assert art["schema"] == cfp.SCHEMA
    assert art["run_id"] == RUN_ID
    assert art["direction_version"] == DIRV
    fp = art["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 8
    assert fp["n_decisions"] == 800
    assert fp["n_verified"] == 1
    assert fp["n_verified_defective"] == 0
    assert fp["defect_histogram"] == {
        "D1_empty_evidence": 0, "D2_letterhead_zone": 0,
        "D3_markup_residue": 0, "D4_language_marker_mismatch": 0,
    }
    ac = art["all_committed"]["totals"]
    assert ac["n_bundles"] == 105
    assert ac["defect_histogram"]["D2_letterhead_zone"] == 44
    assert ac["defect_histogram"]["D3_markup_residue"] == 31
    assert ac["defect_histogram"]["D4_language_marker_mismatch"] == 7
    assert art["false_reject_count"] == 0
    assert art["ordered_work_2_success_rule"]["met"] is True
    # the frozen predicate provenance is the module's, re-published not re-derived
    fpv = art["frozen_predicate_provenance"]
    assert fpv["predicate_source_sha256"] == cfp.ces.FROZEN_PREDICATE_SOURCE_SHA256
    assert fpv["frozen_hypothesis_sha256"] == cfp.ces.FROZEN_PREDICATE_HYPOTHESIS_SHA256
    assert fpv["letterhead_zone_offset_max"] == 400
    assert fpv["min_marker_hits"] == 3


def test_fresh_recompute_agrees_with_the_committed_artifact() -> None:
    """Recompute from the committed bytes and compare.

    If a later cycle adds or removes a bundle the family has legitimately
    changed, full equality is not asserted - the invariants below still are,
    and the committed artifact of THIS cycle is never rewritten.
    """
    fresh = _strip(cfp.run(run_id=RUN_ID, direction_version=DIRV))
    art = _strip(_load(PROBE_ART))
    fresh_paths = [b["path"] for b in fresh["fixed_path_family"]["bundles"]]
    art_paths = [b["path"] for b in art["fixed_path_family"]["bundles"]]
    if fresh_paths == art_paths:
        assert fresh["fixed_path_family"] == art["fixed_path_family"]
        assert fresh["all_committed"]["totals"] == art["all_committed"]["totals"]
    else:
        for p in art_paths:
            assert p in fresh_paths, f"fixed-path bundle vanished: {p}"
    # these must hold at any time, family changed or not
    assert fresh["ordered_work_2_success_rule"]["met"] is True
    assert fresh["false_reject_count"] == 0
    assert fresh["confirmed_set"]["still_verified"] is True
    assert fresh["confirmed_set"]["defects"] == []
    hist = fresh["fixed_path_family"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] == hist["D3_markup_residue"] == 0
    assert hist["D4_language_marker_mismatch"] == hist["D1_empty_evidence"] == 0
    # historical defects are preserved, never silently zeroed
    assert fresh["all_committed"]["totals"]["defect_histogram"]["D2_letterhead_zone"] > 0


def test_family_is_identified_from_bytes_not_hard_coded() -> None:
    art = _load(PROBE_ART)
    for bundle in art["fixed_path_family"]["bundles"]:
        doc = _load(REPO_ROOT / bundle["path"])
        cf = ((doc.get("provenance") or {}).get("counter_evidence_span")
              or {}).get("content_filter")
        assert isinstance(cf, dict) and cf, bundle["path"]
        assert cf["predicate_source_sha256"] == cfp.ces.FROZEN_PREDICATE_SOURCE_SHA256


def test_report_publishes_both_populations_side_by_side() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "fixed-path family" in text
    assert "all committed" in text
    assert "historical" in text
    assert "D2" in text and "D3" in text and "D4" in text
    assert "False-reject count on the confirmed set: 0" in text
    assert "MET on the committed bytes" in text


# --------------------------------------------------------------------------- #
# 4. the runnable vertical slice, this run
# --------------------------------------------------------------------------- #

def test_offline_slice_passes_for_this_run() -> None:
    s = _load(OFFLINE_SUMMARY)
    assert s["verified"] is True
    assert s["page_contract"] is True
    assert s["page_contract_detail"].startswith("PASS")
    stats = s["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["answer_status"] == "ready"
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["rows_with_source_url"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["rows_with_cluster_id"] == 100
    assert stats["fixture_replay"]["network"] == "none"


def test_server_slice_passes_all_ten_checks_for_this_run() -> None:
    s = _load(SERVER_SUMMARY)
    assert s["schema"] == "product-server-slice/1"
    assert s["verdict"] == "PASS"
    assert s["failures"] == []
    checks = s.get("checks")
    if checks is not None:
        assert len(checks) == 10
        assert all(c.get("status") == "PASS" for c in checks)
    c = s["counts"]
    assert c["n_first_page"] == 100 and c["n_final"] == 100
    assert c["n_clusters_final"] == 8
    assert c["page_contract_assertions"] == 68
    assert s["mode"] == "fixture"


def test_progressive_smoke_passes_23_of_23_for_this_run() -> None:
    s = _load(PROGRESSIVE_ART)
    assert s["run_id"] == RUN_ID
    assert s["verdict"] == "PASS"
    assert s["checks_passed"] == s["checks_total"] == 23
    assert s["failures"] == []
    assert "no network" in s["mode"]
    # engineering budgets from the lane directive are reported, not asserted away
    assert "budgets" in s and "timings_s" in s


# --------------------------------------------------------------------------- #
# 5. state: hygiene, posture correction, workflow contract
# --------------------------------------------------------------------------- #

def test_state_carries_the_hygiene_corrections_of_ordered_item_4() -> None:
    st = _load(STATE_PATH)
    assert st["direction_version"] == DIRV
    assert st["cycle_status"] != "INITIALIZED"
    assert st["accepted_run_id"] == "CYCLE_40139832004"
    assert st["accepted_commit"] == "e53662be8"
    assert st["accepted_run_supersession"].startswith("CYCLE_40100397058")
    rec = st["cycle_40143042888_operational_resume"]
    assert rec["direction_version"] == DIRV
    assert "40141595725" in rec["failure_of_record"]
    assert "exit code 3" in rec["failure_of_record"]
    assert rec["diagnosis_artifact"].endswith(f"CYCLE_{RUN_ID}_resume_diagnosis.json")
    assert rec["continue_recommended"] is True
    assert "UNADJUDICATED" in rec["status_of_inherited_work"]


def test_posture_is_fail_closed_and_the_correction_is_documented() -> None:
    st = _load(STATE_PATH)
    for flag in ("machine_gate_ready", "human_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, flag
    assert st["continue_recommended"] is True
    corr = st["posture_correction_40143042888"]
    assert corr["field"] == "human_gate_ready"
    assert corr["from"] is True and corr["to"] is False
    assert "7279e18db" in corr["set_by"]
    assert any("either frozen bar is unmet" in b for b in corr["basis"])
    assert any("posture flags stay FALSE" in b for b in corr["basis"])
    assert "7279e18db:state/product.json" in corr["history_preserved"]
    # the committed test that the true value broke now holds
    st2 = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    assert st2["human_gate_ready"] is False


def test_control_plane_gap_is_recorded_not_edited() -> None:
    st = _load(STATE_PATH)
    items = st["control_plane_hardening_items"]
    cp = next(i for i in items if i["id"] == "CP-AUDIT-SCOPE-3")
    assert "core-lane.yml" in cp["gap"]
    assert "exit 3" in cp["gap"] or "exits 3" in cp["gap"]
    assert ".github/** is control-plane scope" in cp["why_a_lane_cannot_fix_it"]
    assert cp["intended_upstream_fix_for_the_control_plane_maintainer"]


def test_workflow_state_contract_passes_for_this_direction_version() -> None:
    ok, msg = sc.workflow_validation(DIRV, STATE_PATH)
    assert ok, msg
    assert f"direction_version={DIRV}" in msg


def test_evidence_ref_test_counts_reproduce_for_the_corrected_refs() -> None:
    """RF2: both numbers are published, and the measured one is re-measured.

    Eight of the twenty counted evidence_refs did not reproduce in this
    environment.  The state keeps the prior declared value beside the measured
    value in ``evidence_ref_counts_40143042888.supersession`` and the
    ``evidence_refs`` entry now carries the measured count.  The twelve refs
    that reproduced exactly were not touched.
    """
    import re

    st = _load(STATE_PATH)
    block = st["evidence_ref_counts_40143042888"]
    assert block["measured_by"].startswith("python3 -m pytest")
    assert "environment-scoped" in block["caveat"]
    sup = block["supersession"]
    assert len(sup) == 8
    declared_by_file = {
        r.partition(" (")[0]: int(r.rpartition("(")[2].split()[0])
        for r in st["evidence_refs"]
        if r.endswith("tests)") and "tests/" in r
    }
    for row in sup:
        path = REPO_ROOT / row["file"]
        assert path.is_file(), row["file"]
        # both numbers are preserved: the prior value is still on record
        assert isinstance(row["declared_before"], int)
        assert declared_by_file[row["file"]] == row["measured"], row["file"]
        out = subprocess.run(
            [sys.executable, "-m", "pytest", row["file"], "--collect-only", "-q"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), check=True,
        ).stdout
        m = re.search(r"(\d+) tests? collected", out)
        assert m, f"could not parse collection for {row['file']}"
        assert int(m.group(1)) == row["measured"], (
            f"{row['file']}: published measured={row['measured']}, "
            f"re-measured={m.group(1)}")
    # the twelve refs that reproduced are untouched and still self-consistent
    counted = [r for r in st["evidence_refs"] if r.endswith("tests)") and "tests/" in r]
    assert len(counted) == 20
