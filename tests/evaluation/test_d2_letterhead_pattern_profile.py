"""Tests for ``evaluation/d2_letterhead_pattern_profile.py`` (v67 ordered work
item (1): D2 letterhead pattern heterogeneity profile, population extension).

Pins the REUSE-FIRST contract: the frozen D2/D3/D4 predicates are imported BY
VALUE from the accepted instrument ``counter_evidence_quality_benchmark.py``
(sha256 aac86527...), which is re-hashed REPORTED-ONLY at runtime (control C4)
and never edited. The profile scores no frozen bar, edits nothing frozen, and
its population is the product's shipped slice bundles plus the packet-of-record
question bundles — never the RULES_LABEL population.

Pure-logic checks run without the mount; the live end-to-end run is exercised
once against the accepted-product mount when available.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.d2_letterhead_pattern_profile import (  # noqa: E402
    ACCEPTED_BASELINE_HISTOGRAM,
    FROZEN_INSTRUMENT_SHA_EXPECTED,
    MAX_LINE_LEN_P1,
    SCHEMA,
    _classify_pattern,
    _normalize_ws,
    _reachability_label,
    classify_verified_row,
)


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


def test_reachability_labels_cite_arm2_without_rerun():
    label = _reachability_label("offline_accept_40032389983", "shipped_slice")
    assert "fixture_bypass_only" in label
    assert "40070818687" in label  # ARM2 cited
    assert "pipeline.py:1339" in label
    packet_label = _reachability_label(
        "packet_of_record_39319405429", "packet_of_record")
    assert "packet_of_record" in packet_label


def test_normalize_ws_pattern_key_stability():
    a = _normalize_ws("Kantonsgericht  von\nGraubünden")
    b = _normalize_ws("Kantonsgericht von Graubünden")
    assert a == b


def test_live_run_when_mount_available():
    """One live run against the accepted-product mount (skip when absent)."""
    mount = Path("/tmp/lex_accepted/product")
    if not mount.is_dir():
        import pytest
        pytest.skip("accepted-product mount unavailable")
    proc = subprocess.run(
        [sys.executable,
         str(_REPO_ROOT / "evaluation/d2_letterhead_pattern_profile.py"),
         "--run-id", "test_live_profile"],
        capture_output=True, text=True, timeout=600,
        cwd=str(_REPO_ROOT))
    # exit 0 (all P1/P2) or 1 (P3 observed) are both published profiles;
    # 2 is CONTROLS_FAILED and must not happen on a healthy mount
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["controls_all_pass"] is True
    assert out["n_bundles"] >= 3
    result = json.loads((
        _REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
        / "test_live_profile.json").read_text(encoding="utf-8"))
    assert result["schema"] == SCHEMA
    # packet-of-record labelled population: frozen verified-row predicate
    # yields 0 rows on served bytes (accepted requirement 36/42)
    assert result["n_verified_rows_packet_of_record"] == 0
    assert result["verdict"] in (
        "LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED",
        "HETEROGENEOUS_BEYOND_MECHANICAL_DETECTION")
