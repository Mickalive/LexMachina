"""Tests for ``evaluation/d2_letterhead_pattern_profile.py`` (direction v68,
OPERATIONAL population extension; cycle 40246705199 repair round 2).

Pins the REUSE-FIRST contract: the frozen D2/D3/D4 predicates are imported BY
VALUE from the accepted instrument ``counter_evidence_quality_benchmark.py``
(sha256 aac86527...), which is re-hashed REPORTED-ONLY at runtime (control C4)
and never edited. The profile scores no frozen bar, edits nothing frozen, and
its population is the product's shipped slice bundles plus the packet-of-record
question bundles — never the RULES_LABEL population.

Pins the repair-1 falsified-claim contract (audit R1): reachability labels are
MEASURED from each bundle's own committed
``provenance.counter_evidence_span`` payload; the pre-51d306c fixture-bypass
clause (and its three banned wordings) is superseded as explanation and may
appear in this instrument only inside an explicitly marked SUPERSEDED block.

Pure-logic checks run without the mount; the live end-to-end run is exercised
against an available product mount into a pytest tmp directory so that no
non-run-id measurement filename is ever re-written.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.d2_letterhead_pattern_profile import (  # noqa: E402
    ACCEPTED_BASELINE_HISTOGRAM,
    CONTROLLING_DIRECTION_VERSION,
    FROZEN_INSTRUMENT_SHA_EXPECTED,
    MAX_LINE_LEN_P1,
    SCHEMA,
    _classify_pattern,
    _normalize_ws,
    _reachability_label,
    _span_state,
    classify_verified_row,
)

# The three wordings the repair-1 artifact published as current state for a
# claim the product code does not support (audit R1). They must not appear as
# live text anywhere in the instrument, its report template or this file.
BANNED_STALE_CLAIM_STRINGS = (
    "pipeline.py:1339",
    "the filter never runs",
    "BOTH legs per v67",
)

_PINNED_MOUNT = Path("/tmp/lex_eval_mount_3de8431d")
_PINNED_HEAD = "3de8431d46bfe757469720682253e63f0d763c4b"


def test_schema_and_frozen_predicates():
    assert SCHEMA == "lex-evaluation-d2-letterhead-pattern-profile/1"
    src = (_REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py").read_text(
        encoding="utf-8")
    # REUSE-FIRST: the profile must NOT import Product code
    assert "from product" not in src
    # The frozen predicates are imported BY VALUE from the accepted benchmark
    assert "from evaluation.counter_evidence_quality_benchmark import" in src
    assert "LETTERHEAD_ZONE_OFFSET_MAX" in src
    assert "MARKUP_TOKENS" in src
    assert "MIN_MARKER_HITS" in src
    assert "LANGUAGE_MARKER_SETS" in src
    # No frozen bar is scored and nothing frozen is edited
    assert "probe_is_not_a_frozen_bar" in src
    assert FROZEN_INSTRUMENT_SHA_EXPECTED in src


def test_frozen_predicate_values_match_accepted_instrument():
    assert classify_verified_row.__module__ == (
        "evaluation.counter_evidence_quality_benchmark")
    # accepted baseline histogram the C6 control pins
    assert ACCEPTED_BASELINE_HISTOGRAM == {
        "D2_letterhead_zone": 10,
        "D3_markup_residue": 4,
        "D4_language_marker_mismatch": 4,
    }


def test_detectability_taxonomy_p1_p2_p3():
    p1_ev = "Kantonsgericht X\nGericht Y\nGericht Z\n____"
    det, struct = _classify_pattern(p1_ev, {"first_offset": 0})
    assert det == "P1_OFFSET0_MULTILINE_COURT_HEADER"
    assert struct["n_lines"] == 4
    assert all(n <= MAX_LINE_LEN_P1 for n in struct["line_lengths"])

    p2_ev = "Erwägung 1. something substantive"
    det, struct = _classify_pattern(p2_ev, {"first_offset": 123})
    assert det == "P2_MID_DOCUMENT_HEADER_ZONE"

    # offset-0 single-line form is P3 (requires inspection), never silently P1
    p3_ev = "Einzeiliger Kopf"
    det, struct = _classify_pattern(p3_ev, {"first_offset": 0})
    assert det == "P3_OTHER_LETTERHEAD_ZONE_FORM"

    # P1 line-length ceiling enforced: an offset-0 multi-line span whose lines
    # exceed 120 chars is NOT auto-mechanical
    long_line = "x" * 200
    det, _ = _classify_pattern(f"{long_line}\n{long_line}", {"first_offset": 0})
    assert det == "P3_OTHER_LETTERHEAD_ZONE_FORM"


def test_planted_non_vacuity_matches_frozen_classifier():
    planted_lh = {
        "counter_evidence": "Kantonsgericht X\nGericht Y\n____",
        "full_text": "Kantonsgericht X\nGericht Y\n____" + (" body" * 40),
        "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
    }
    cl = classify_verified_row(planted_lh)
    assert "D2_letterhead_zone" in cl["defects"]
    ev = "Erwägung: substantielle Erwägung im vorliegenden Urteil."
    planted_mid = {
        "counter_evidence": ev,
        "full_text": "x" * 500 + "\n" + ev,
        "language": "de", "counter_status": "cited",
        "counter_evidence_verified": True,
    }
    cl2 = classify_verified_row(planted_mid)
    assert "D2_letterhead_zone" not in cl2["defects"]
    assert cl2["detail"]["first_offset"] == 501


def test_reachability_labels_are_measured_from_bundle_provenance():
    """Repair round 2 (audit R1): reachability is MEASURED, never asserted.

    The old test pinned the falsified ``fixture_bypass_only`` wording and the
    stale ``pipeline.py:1339`` citation; both are superseded as explanation.
    """
    # 1. bundle that predates the seam: absence is reported as absence
    absent = _reachability_label("offline_slice_other_20261021T021147Z",
                                 "shipped_slice", prov=None, head=_PINNED_HEAD)
    assert absent.startswith("span_provenance_absent MEASURED")
    assert "NOT MEASURED here" in absent
    assert "40070818687" in absent  # ARM2 cited, not re-run
    assert "SUPERSEDED AS EXPLANATION" in absent
    for banned in BANNED_STALE_CLAIM_STRINGS:
        assert banned not in absent

    # 2. bundle whose seam payload is committed: the numbers come from the
    #    bundle itself, so the label carries the measured telemetry
    applied = {
        "applied": True, "n_candidates": 1, "n_selected": 0,
        "n_abstained": 1, "abstained_ids": ["gr_gerichte_ERZ 2010 25"],
        "abstention_reasons": {"pivot_absent": 1},
        "content_filter_present": True, "n_downgraded": 1,
        "downgraded_ids": ["gr_gerichte_ERZ 2010 25"],
    }
    assert _span_state(applied) == "span_seam_applied"
    lbl = _reachability_label("offline_accept_40032389983", "shipped_slice",
                              prov=applied, head=_PINNED_HEAD)
    assert lbl.startswith("span_seam_applied MEASURED")
    assert "applied=true" in lbl
    assert "abstained_ids=['gr_gerichte_ERZ 2010 25']" in lbl
    assert "pivot_absent" in lbl
    assert "pipeline.py:1400-1407" in lbl   # corrected seam call citation
    assert "pipeline.py:1408" in lbl        # corrected fixture-gate citation

    # 3. seam ran but did not apply
    assert _span_state({"applied": False}) == "span_seam_ran_applied_false"
    assert _reachability_label("f", "shipped_slice",
                               prov={"applied": False},
                               head=_PINNED_HEAD).startswith(
        "span_seam_ran_applied_false MEASURED")

    # 4. packet-of-record keeps its production-path label
    packet_label = _reachability_label(
        "packet_of_record_39319405429", "packet_of_record")
    assert "packet_of_record" in packet_label


def test_no_stale_bypass_claim_in_instrument_source():
    """Audit R1: the three falsified wordings are gone from live text.

    An explicitly marked SUPERSEDED context may name the old clause; every
    other occurrence is a regression of the falsified P0 claim.
    """
    src = (_REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py").read_text(
        encoding="utf-8")
    for banned in BANNED_STALE_CLAIM_STRINGS:
        assert banned not in src, f"stale bypass claim leaked back in: {banned}"
    # corrected citations and the measured framing must be present
    assert "pipeline.py:1400-1407" in src
    assert "counter_evidence_span.py:385-394" in src
    assert "SUPERSEDED_AS_EXPLANATION" in src
    assert "span_provenance" in src
    # direction pin: v68 is the controlling direction for this lane
    assert CONTROLLING_DIRECTION_VERSION == 68
    assert "scope_label" in src


def test_operational_scope_fields_present():
    """Direction v68 item (5): an operational label must be carried."""
    from evaluation import d2_letterhead_pattern_profile as mod
    assert mod.CONTROLLING_DIRECTION_VERSION == 68
    for needle in ("OPERATIONAL_POPULATION_EXTENSION_NO_ORDERED_ITEM_DISCHARGED",
                   "ordered_item_status",
                   "NOT_YET_DISCRIMINATING",
                   "span_provenance_summary"):
        assert needle in (mod.__doc__ or "") or needle in (
            _REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py"
        ).read_text(encoding="utf-8"), needle


def test_normalize_ws_pattern_key_stability():
    a = _normalize_ws("Kantonsgericht  von\nGraubünden")
    b = _normalize_ws("Kantonsgericht von Graubünden")
    assert a == b


def test_live_run_when_mount_available(tmp_path):
    """One live run against a product mount, written ONLY into ``tmp_path``.

    F-3B: a file named for a run holds that run's measurement, so this test
    never writes ``results/.../test_live_profile.json`` (that file is a
    superseded named-run artifact and must stay byte-untouched).
    """
    mount = Path("/tmp/lex_accepted/product")
    if not mount.is_dir():
        pytest.skip("accepted-product mount unavailable")
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    env = dict(**__import__("os").environ)
    env["LEXMACHINA_PRODUCT_MOUNT"] = str(mount)
    proc = subprocess.run(
        [sys.executable,
         str(_REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py"),
         "--run-id", "test_live_profile",
         "--out-dir", str(out_dir),
         "--report-dir", str(report_dir)],
        capture_output=True, text=True, timeout=600,
        cwd=str(_REPO_ROOT), env=env)
    # exit 0 (all P1/P2) or 1 (P3 observed) are both published profiles;
    # 2 is CONTROLS_FAILED / ENVIRONMENT_ERROR and must not happen here
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["controls_all_pass"] is True
    assert out["n_bundles"] >= 3
    result = json.loads(
        (out_dir / "test_live_profile.json").read_text(encoding="utf-8"))
    assert result["schema"] == SCHEMA
    # F-3B: the legacy non-run-id filename in the repo was NOT rewritten
    legacy = (_REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
              / "test_live_profile.json")
    assert not (out_dir / "..").resolve().is_relative_to(
        _REPO_ROOT / "results")
    if legacy.is_file():
        assert json.loads(legacy.read_text(encoding="utf-8"))["schema"] == SCHEMA
    # packet-of-record labelled population: frozen verified-row predicate
    # yields 0 rows on served bytes (accepted requirement 36/42)
    assert result["n_verified_rows_packet_of_record"] == 0
    assert result["verdict"] in (
        "LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED",
        "HETEROGENEOUS_BEYOND_MECHANICAL_DETECTION")
    # v68 operational labelling travels with every run
    assert result["scope_label"].startswith("OPERATIONAL_")
    assert result["controlling_direction_version"] == 68
    assert "span_provenance_summary" in result
    for banned in BANNED_STALE_CLAIM_STRINGS:
        assert banned not in json.dumps(result), banned


@pytest.mark.skipif(not _PINNED_MOUNT.is_dir(),
                    reason="pinned-head product mount unavailable")
def test_pinned_head_reproduction_matches_measurement_of_record(tmp_path):
    """Audit R1: the measurement of record must be reproducible bit-for-bit.

    Re-running the instrument on the pinned head must reproduce the exact
    population/detection numbers the rejected cycle published — only the
    provenance/labelling framing may change.
    """
    env = dict(**__import__("os").environ)
    env["LEXMACHINA_PRODUCT_MOUNT"] = str(_PINNED_MOUNT)
    proc = subprocess.run(
        [sys.executable,
         str(_REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py"),
         "--run-id", "40246705199",
         "--expect-head", _PINNED_HEAD,
         "--out-dir", str(tmp_path / "results"),
         "--report-dir", str(tmp_path / "reports")],
        capture_output=True, text=True, timeout=900,
        cwd=str(_REPO_ROOT), env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads((tmp_path / "results" / "40246705199.json").read_text(
        encoding="utf-8"))
    assert rec["n_bundles"] == 144
    assert rec["n_bundles_shipped_slice"] == 141
    assert rec["n_bundles_packet_of_record"] == 3
    assert rec["n_verified_rows_shipped_slice"] == 126
    assert rec["population_defect_histogram"]["D2_letterhead_zone"] == 44
    assert rec["d2_rows_profiled"] == 44
    assert rec["n_distinct_letterhead_patterns"] == 2
    assert rec["head_pin"] == {"expected": _PINNED_HEAD, "applied": True}
    assert rec["product_mount_head"] == _PINNED_HEAD
    assert rec["supersession"]["status"] == "SUPERSEDED_AS_EXPLANATION"
    assert rec["ordered_item_status"][
        "item_2_conditional_remeasure"].startswith("NOT_YET_DISCRIMINATING")
    for banned in BANNED_STALE_CLAIM_STRINGS:
        assert banned not in json.dumps(rec), banned

