"""Tests for ``evaluation/measure_current_head_slices.py`` (FAST-MVP
current head slice quality benchmark under frozen item-(2) protocol).

These tests pin the REUSE-FIRST contract: the frozen D1-D4 defect predicates are
imported BY VALUE from the accepted v65_head_advance_crosscheck_v2 hypothesis
(sha256 734a447d...). The predicates are mechanical, require no legal reasoning/
LLM/paid API, and are frozen — never re-tuned, re-derived or edited after
results are seen.

The heavy end-to-end probe (reading the accepted-product mount) is exercised
once via a live run; pure-logic checks run without the mount so the suite stays
runnable in a bare checkout.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.measure_current_head_slices import (  # noqa: E402
    EXPECTED_HYPOTHESIS_SHA,
    LANGUAGE_MARKER_SETS,
    LETTERHEAD_ZONE_OFFSET_MAX,
    MARKUP_TOKENS,
    MIN_MARKER_HITS,
    SCHEMA,
    classify_verified_row,
)


def test_schema_and_frozen_predicates():
    assert SCHEMA == "lex-evaluation-current-head-slice-quality/1"
    src = (_REPO_ROOT / "evaluation/measure_current_head_slices.py").read_text(
        encoding="utf-8")
    # REUSE-FIRST: the benchmark must NOT import Product code
    assert "from product" not in src
    # The frozen predicates are imported BY VALUE from the accepted benchmark
    assert "from evaluation.counter_evidence_quality_benchmark import" in src
    assert "LETTERHEAD_ZONE_OFFSET_MAX" in src
    assert "MARKUP_TOKENS" in src
    assert "MIN_MARKER_HITS" in src
    assert "LANGUAGE_MARKER_SETS" in src
    # No frozen bar is scored
    assert "probe_is_not_a_frozen_bar" in src


def test_frozen_predicate_values_match_accepted_hypothesis():
    # These values are frozen in the accepted v65 hypothesis (sha256
    # 734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881)
    assert LETTERHEAD_ZONE_OFFSET_MAX == 400
    assert MARKUP_TOKENS == ["<mark>", "</mark>", "<em>", "</em>", "<b>", "</b>", "<highlight>"]
    assert MIN_MARKER_HITS == 3
    assert LANGUAGE_MARKER_SETS == {
        "de": ["Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"],
        "fr": ["Considérant", "résiliation", "bail", "Tribunal fédéral", "recours", "art."],
        "it": ["Dispositivo", "risoluzione", "affitto", "Tribunale federale", "ricorso", "regola"],
    }


def test_classify_verified_row_frozen_predicates():
    # C1 control: letterhead zone detection (offset < 400)
    base_ft = ("Kantonsgericht von Graubünden\nDretgira chantunala dal Grischun\n" +
               ("_" * 120) + "\nRef.:\n" + ("x" * 500) +
               "\nGericht hat in Erwägung gesetzt, dass die Kündigung des Mietvertrags "
               "unwirksam ist.\n")
    letterhead_row = {"decision_id": "planted_letterhead", "language": "de",
                      "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                      "counter_evidence": base_ft[:120], "full_text": base_ft,
                      "snippet": "", "regeste": "", "full_text_status": "hydrated"}
    mid_row = {"decision_id": "planted_mid", "language": "de",
               "counter_status": "candidate-limiting", "counter_evidence_verified": True,
               "counter_evidence": "Gericht hat in Erwägung gesetzt, dass die Kündigung des Mietvertrags unwirksam ist.",
               "full_text": base_ft, "snippet": "", "regeste": "", "full_text_status": "hydrated"}
    markup_row = {"decision_id": "planted_markup", "language": "de",
                  "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                  "counter_evidence": "Regeste <mark>Mietvertrag</mark> Anfechtung der Kündigung",
                  "full_text": base_ft, "snippet": "", "regeste": "",
                  "full_text_status": "hydrated"}
    c_letterhead = classify_verified_row(letterhead_row)
    c_mid = classify_verified_row(mid_row)
    c_markup = classify_verified_row(markup_row)
    assert "D2_letterhead_zone" in c_letterhead["defects"]
    assert "D2_letterhead_zone" not in c_mid["defects"]
    assert "D3_markup_residue" in c_markup["defects"]
    assert c_letterhead["detail"]["first_offset"] == 0
    assert c_mid["detail"]["first_offset"] > LETTERHEAD_ZONE_OFFSET_MAX

    # C2 control: language marker mismatch
    lang_row = {"decision_id": "planted_lang", "language": "it",
                "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "full_text": "y" * 900 + "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "snippet": "", "regeste": "", "full_text_status": "lazy"}
    c_lang = classify_verified_row(lang_row)
    assert "D4_language_marker_mismatch" in c_lang["defects"]
    assert c_lang["detail"]["marker_hits_own"] == 0
    assert c_lang["detail"]["marker_hits_other"]["de"] >= MIN_MARKER_HITS

    # D1 empty evidence
    empty_row = {"decision_id": "empty", "language": "de",
                 "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                 "counter_evidence": "", "full_text": "text", "snippet": "", "regeste": "",
                 "full_text_status": "hydrated"}
    c_empty = classify_verified_row(empty_row)
    assert "D1_empty_evidence" in c_empty["defects"]

    # No defects -> COUNTER_REASONING (evidence at offset > 400, no markup, correct language markers)
    good_ft = ("x" * 500 + "\nGericht hat in Erwägung gesetzt, dass die Kündigung unwirksam ist.")
    good_row = {"decision_id": "good", "language": "de",
                "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                "counter_evidence": "Gericht hat in Erwägung gesetzt, dass die Kündigung unwirksam ist.",
                "full_text": good_ft, "snippet": "", "regeste": "", "full_text_status": "hydrated"}
    c_good = classify_verified_row(good_row)
    assert c_good["defects"] == []
    assert c_good["class"] == "COUNTER_REASONING"
    assert c_good["detail"]["first_offset"] > LETTERHEAD_ZONE_OFFSET_MAX


def test_end_to_end_on_accepted_mount_if_present(tmp_path):
    """Live end-to-end: only when the accepted-product mount is available.

    SCRATCH-RUN OBLIGATION: this test must redirect output to tmp_path so it
    cannot rewrite committed claim-bearing records.
    """
    mount = Path("/tmp/lex_accepted/product")
    if not mount.exists():
        import pytest
        pytest.skip("accepted product mount absent; frozen logic tests still pin the predicates")
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.measure_current_head_slices",
         "--run-id", "pytest_local",
         "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode in (0, 1, 2), (
        f"unexpected exit {proc.returncode}; stderr tail: {proc.stderr[-500:]}")
    if proc.returncode == 1:
        # H2_FALSIFIED is the expected outcome on the current product artifacts
        out = json.loads(proc.stdout)
        assert out["verdict"] == "H2_FALSIFIED"
        assert out["h2_falsified"] is True
        assert out["n_defective"] > 0
        # the redirected run must actually have written there, not to the repo
        assert (out_dir / "pytest_local.json").is_file()
        assert (report_dir / "CURRENT_HEAD_SLICE_QUALITY_pytest_local.md").is_file()


def test_committed_tree_is_not_a_benchmark_output_directory():
    """The defaults are the committed tree - so a scratch run must redirect."""
    from evaluation.measure_current_head_slices import (
        DEFAULT_OUT_DIR, DEFAULT_REPORT_DIR,
    )
    assert DEFAULT_OUT_DIR.name == "current_head_slice_quality"
    assert DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert DEFAULT_REPORT_DIR.name == "evaluation"
    assert DEFAULT_OUT_DIR.is_dir() and DEFAULT_REPORT_DIR.is_dir()