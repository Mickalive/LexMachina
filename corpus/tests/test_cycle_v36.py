#!/usr/bin/env python3
"""Corpus lane v36 tests: section extraction, BGE/bger crosswalk, eval alignment.

Direction v36 acceptance (corpus lane):
  * section extraction across the 174k corpus with coverage metrics,
  * BGE/bger id crosswalk for dense/evaluation alignment
    (covering >=95% of evaluation bger_ ids),
  * 2024-2026 parquet/embeddings published deterministically.

These tests are read-only over the committed artifacts under ``results/corpus``
and the pinned ``bger.parquet``.  They run as a plain script (no pytest):

    python corpus/tests/test_cycle_v36.py
"""
from __future__ import annotations

import json
import os
import sys

import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

RESULTS = os.path.join(PROJECT_ROOT, "results", "corpus")
SPANS = os.path.join(RESULTS, "section_spans_174k.parquet")
SECTION_METRICS = os.path.join(RESULTS, "section_extraction_metrics_v36.json")
CROSSWALK = os.path.join(RESULTS, "bge_bger_crosswalk.parquet")
CROSSWALK_METRICS = os.path.join(RESULTS, "bge_bger_crosswalk_metrics_v36.json")
EVAL_ALIGN = os.path.join(RESULTS, "eval_id_alignment_v36.json")
PINNED_PARQUET = os.path.join(PROJECT_ROOT, "corpus", "acquisition", "parquet", "bger.parquet")

_results = []


def _record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    _results.append((name, passed))
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if not passed:
        raise AssertionError(f"[FAIL] {name}{suffix}")


# ===========================================================================
# GROUP 1: section span artifact
# ===========================================================================
def test_section_artifact_exists():
    _record("section_spans_174k.parquet exists", os.path.exists(SPANS))


def test_section_row_count():
    n = pq.ParquetFile(SPANS).metadata.num_rows
    _record("section spans cover 174,114 decisions", n == 174114, f"got {n}")


def test_section_schema():
    names = set(pq.ParquetFile(SPANS).schema_arrow.names)
    required = {
        "decision_id", "language",
        "has_sachverhalt", "has_erwaegungen", "has_dispositiv",
        "erwaegungen_start", "erwaegungen_end", "erwaegungen_chars",
        "erwaegungen_method", "erwaegungen_paragraph_count",
    }
    missing = required - names
    _record("section spans has required schema", not missing, f"missing {missing}")


def test_section_coverage_thresholds():
    m = json.load(open(SECTION_METRICS))
    cov = m["unconditional_coverage"]
    ok = cov["erwaegungen"] >= 0.99 and cov["dispositiv"] >= 0.95 and cov["sachverhalt"] >= 0.6
    _record("section unconditional coverage sane", ok, json.dumps(cov))


def test_section_structure_parity():
    m = json.load(open(SECTION_METRICS))
    v = m["validation_vs_structure_parquet"]
    ok = all(v[s]["coverage"] >= 0.999 and v[s]["precision"] >= 0.999 for s in
             ("sachverhalt", "erwaegungen", "dispositiv"))
    ok = ok and v["erwaegungen_paragraph_count_exact_match"]["rate"] >= 0.95
    _record("section parity vs published structure table", ok)


def test_section_span_validity():
    t = pq.read_table(
        SPANS,
        columns=["has_sachverhalt", "has_erwaegungen", "has_dispositiv",
                 "sachverhalt_start", "sachverhalt_end",
                 "erwaegungen_start", "erwaegungen_end",
                 "dispositiv_start", "dispositiv_end"],
    ).to_pandas()
    bad = 0
    for s in ("sachverhalt", "erwaegungen", "dispositiv"):
        has = t[f"has_{s}"] == 1
        bad += int((t.loc[has, f"{s}_start"] >= t.loc[has, f"{s}_end"]).sum())
    _record("present sections have start < end", bad == 0, f"violations={bad}")


def test_section_method_present_when_has():
    t = pq.read_table(SPANS, columns=["has_erwaegungen", "erwaegungen_method"]).to_pandas()
    has = t[t.has_erwaegungen == 1]
    n_null = int(has.erwaegungen_method.isna().sum())
    _record("erwaegungen method non-null when present", n_null == 0, f"nulls={n_null}")


# ===========================================================================
# GROUP 2: materializer round-trip (needs pinned parquet)
# ===========================================================================
def test_materializer_roundtrip():
    if not os.path.exists(PINNED_PARQUET):
        print("  [SKIP] materializer round-trip (pinned parquet absent)")
        return
    from corpus.normalization.materialize_sections import (
        load_spans, load_texts, materialize_row, SECTIONS,
    )
    import random
    spans = load_spans(SPANS)
    ids = sorted(spans.index.tolist())
    rng = random.Random(36)
    picked = rng.sample(ids, 40)
    texts = load_texts(PINNED_PARQUET, picked)
    mismatches = 0
    for did in picked:
        row = spans.loc[did]
        ft = texts.loc[did, "full_text"]
        secs = materialize_row(row, ft)
        for s in SECTIONS:
            if row.get(f"has_{s}", 0) == 1:
                if len(secs[s]) != int(row[f"{s}_chars"]) or not secs[s]:
                    mismatches += 1
    _record("materialised section chars match stored counts", mismatches == 0,
            f"mismatches={mismatches}")


# ===========================================================================
# GROUP 3: BGE <-> bger crosswalk
# ===========================================================================
def test_crosswalk_exists():
    _record("bge_bger_crosswalk.parquet exists", os.path.exists(CROSSWALK))


def test_crosswalk_schema_and_unique_ids():
    t = pq.read_table(CROSSWALK).to_pandas()
    required = {"bge_decision_id", "bge_volume", "originating_docket",
                "bger_decision_id", "method", "confidence", "matched"}
    ok = required.issubset(set(t.columns)) and t.bge_decision_id.is_unique
    _record("crosswalk schema + unique bge ids", ok,
            f"rows={len(t)} cols_ok={required.issubset(set(t.columns))}")


def test_crosswalk_matched_consistency():
    t = pq.read_table(CROSSWALK, columns=["matched", "bger_decision_id", "method"]).to_pandas()
    matched = t[t.matched]
    bad = int((~matched.bger_decision_id.str.startswith("bger_")).sum())
    bad += int(matched.bger_decision_id.isna().sum())
    bad += int((t[~t.matched].bger_decision_id.notna()).sum())
    _record("matched rows carry a bger_ id; unmatched carry none", bad == 0, f"bad={bad}")


def test_crosswalk_eval_alignment_acceptance():
    a = json.load(open(EVAL_ALIGN))
    ok = a["coverage"] >= 0.95
    _record("crosswalk covers >=95% of evaluation bger_ ids", ok,
            f"coverage={a['coverage']} ({a['resolved_in_corpus']}/{a['evaluation_ids']})")


def test_crosswalk_relevant_universe():
    m = json.load(open(CROSSWALK_METRICS))
    r = m["relevant_universe_volume_ge_127"]
    ok = r["link_rate"] >= 0.85
    _record("vol>=127 BGE link rate >=0.85", ok,
            f"{r['linked']}/{r['n']} = {r['link_rate']}, unmapped={r['unmapped']}")


def test_crosswalk_confidences():
    m = json.load(open(CROSSWALK_METRICS))
    c = m["method_counts"]
    ok = c.get("docket_number_2", 0) > 0
    _record("crosswalk records docket_number_2 evidence", ok, json.dumps(c))


# ===========================================================================
def main():
    print("=" * 70)
    print("  CORPUS LANE v36 TESTS")
    print("=" * 70)
    groups = [
        ("section artifact", [
            test_section_artifact_exists, test_section_row_count,
            test_section_schema, test_section_coverage_thresholds,
            test_section_structure_parity, test_section_span_validity,
            test_section_method_present_when_has,
        ]),
        ("materializer", [test_materializer_roundtrip]),
        ("crosswalk", [
            test_crosswalk_exists, test_crosswalk_schema_and_unique_ids,
            test_crosswalk_matched_consistency,
            test_crosswalk_eval_alignment_acceptance,
            test_crosswalk_relevant_universe, test_crosswalk_confidences,
        ]),
    ]
    for label, fns in groups:
        print(f"\n-- {label} --")
        for fn in fns:
            try:
                fn()
            except AssertionError:
                pass
    passed = sum(1 for _, p in _results if p)
    failed = len(_results) - passed
    print("\n" + "=" * 70)
    if failed == 0:
        print(f"  ALL {len(_results)} TESTS PASSED")
    else:
        print(f"  {passed}/{len(_results)} passed, {failed} FAILED")
        for name, p in _results:
            if not p:
                print(f"    - {name}")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
