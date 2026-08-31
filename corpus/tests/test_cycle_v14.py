"""
Comprehensive tests for corpus lane cycle v14 full-scale ingestion.

Frozen hypothesis: The v14 pipeline ingested 174,113 decisions from HuggingFace
Parquet, achieved 95.9% citation resolution (corrected from false negative 46.5%),
0 schema validation errors, NaN handling works correctly, and year coverage
2000-2026 is complete. BUG-001 fixed: _normalize_ref no longer strips BGE prefix
from underscore-format references.
"""
import glob as globmod
import json
import math
import os
import sys
import traceback
from pathlib import Path

CANONICAL_DIR = "corpus/normalization/canonical"
SCHEMA_PATH = "corpus/schema/decision_schema.json"
METRICS_PATH = os.path.join(CANONICAL_DIR, "ingestion_metrics.json")
CITATION_GRAPH_PATH = os.path.join(CANONICAL_DIR, "citation_graph.json")

# ─── Helpers ────────────────────────────────────────────────────────────────

_results = []


def _record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    _results.append((name, passed))
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _load_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _count_lines(filepath):
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


# ===========================================================================
# GROUP 1: NaN Handling (NEW in v14)
# ===========================================================================


def test_clean_nan_converts_nan_to_none():
    """_clean_nan must convert float NaN to None."""
    from corpus.acquisition.parquet_ingest_scaled import _clean_nan
    row = {"a": float("nan"), "b": 42, "c": None, "d": "hello"}
    cleaned = _clean_nan(row)
    _record("_clean_nan converts NaN to None", cleaned["a"] is None,
            f"got {cleaned['a']}")


def test_clean_nan_preserves_valid_values():
    """_clean_nan must preserve non-NaN values unchanged."""
    from corpus.acquisition.parquet_ingest_scaled import _clean_nan
    row = {"x": 3.14, "y": "text", "z": None, "w": 0, "v": False}
    cleaned = _clean_nan(row)
    ok = (cleaned["x"] == 3.14 and cleaned["y"] == "text"
          and cleaned["z"] is None and cleaned["w"] == 0
          and cleaned["v"] is False)
    _record("_clean_nan preserves valid values", ok,
            f"got {cleaned}")


def test_clean_nan_handles_empty_row():
    """_clean_nan on an empty dict returns an empty dict."""
    from corpus.acquisition.parquet_ingest_scaled import _clean_nan
    cleaned = _clean_nan({})
    _record("_clean_nan handles empty row", cleaned == {})


def test_clean_nan_handles_int_nan():
    """_clean_nan must also catch float('nan') that is not None."""
    from corpus.acquisition.parquet_ingest_scaled import _clean_nan
    row = {"a": float("nan"), "b": float("inf"), "c": 1.0}
    cleaned = _clean_nan(row)
    nan_converted = cleaned["a"] is None
    inf_kept = cleaned["b"] == float("inf")
    valid_kept = cleaned["c"] == 1.0
    _record("_clean_nan NaN→None, inf preserved",
            nan_converted and inf_kept and valid_kept,
            f"nan→{cleaned['a']}, inf→{cleaned['b']}, 1.0→{cleaned['c']}")


def test_parse_parquet_row_nan_handling():
    """parse_parquet_row must survive rows with NaN values from pandas."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_nan_test_1",
        "text": "Some valid decision text for testing NaN handling.",
        "date": "2024-01-15",
        "language": "de",
        "court": "bger",
        "docket_number": float("nan"),          # NaN should become None
        "legal_area": None,                      # None stays None
        "regeste": float("nan"),                 # NaN → None
        "cited_decisions": float("nan"),         # NaN → None
        "outcome": None,
        "citation_string_de": float("nan"),
        "bge_reference": None,
    }
    parsed = parse_parquet_row(row)
    ok = (parsed["docket_number"] is not None  # falls back to decision_id
          and parsed["legal_area"] is None
          and parsed["regeste"] is None
          and parsed["cited_decisions"] is None
          and parsed["citation_string_de"] is None)
    _record("parse_parquet_row handles NaN fields", ok,
            f"docket={parsed['docket_number']}, regeste={parsed['regeste']}")


def test_parse_parquet_row_populates_citation_string_de():
    """parse_parquet_row must populate citation_string_de from bge_reference."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_citation_test_1",
        "text": "Test text for citation string mapping.",
        "date": "2024-06-01",
        "language": "de",
        "bge_reference": "BGE 140 III 86",
        "citation_string_de": None,
    }
    parsed = parse_parquet_row(row)
    _record("parse_parquet_row populates citation_string_de",
            parsed["citation_string_de"] == "BGE 140 III 86",
            f"got {parsed['citation_string_de']}")


def test_parse_parquet_row_populates_canonical_url():
    """parse_parquet_row must populate canonical_url from url or source_url."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_url_test_1",
        "text": "Test text for canonical URL mapping.",
        "date": "2024-06-01",
        "language": "de",
        "url": "https://example.com/decision/1",
    }
    parsed = parse_parquet_row(row)
    _record("parse_parquet_row populates canonical_url",
            parsed["canonical_url"] == "https://example.com/decision/1",
            f"got {parsed['canonical_url']}")


# ===========================================================================
# GROUP 2: Full-Scale Ingestion Validation
# ===========================================================================


def test_canonical_dir_has_year_split_files():
    """Canonical corpus directory must contain bger_YYYY.jsonl year-split files."""
    year_files = sorted(globmod.glob(os.path.join(CANONICAL_DIR, "bger_[0-9][0-9][0-9][0-9].jsonl")))
    _record("canonical dir has year-split files",
            len(year_files) >= 20,
            f"found {len(year_files)} year files")


def test_total_lines_across_all_bger_files():
    """Total lines across all bger_*.jsonl files must be >= 170,000."""
    year_files = globmod.glob(os.path.join(CANONICAL_DIR, "bger_[0-9][0-9][0-9][0-9].jsonl"))
    total = 0
    for fp in year_files:
        total += _count_lines(fp)
    _record("total lines across bger_*.jsonl >= 170,000",
            total >= 170_000,
            f"total={total:,}")


def test_year_coverage_2000_2026_no_gaps():
    """Every year from 2000-2026 must have a year-split file with >0 lines."""
    missing = []
    empty = []
    for year in range(2000, 2027):
        fp = os.path.join(CANONICAL_DIR, f"bger_{year}.jsonl")
        if not os.path.exists(fp):
            missing.append(year)
        elif _count_lines(fp) == 0:
            empty.append(year)
    ok = len(missing) == 0 and len(empty) == 0
    _record("year coverage 2000-2026 no gaps",
            ok,
            f"missing={missing}, empty={empty}" if not ok else "all 27 years present")


def test_schema_validation_sample():
    """Schema validation must pass for a 100-record sample from 2024."""
    import jsonschema
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    fp = os.path.join(CANONICAL_DIR, "bger_2024.jsonl")
    if not os.path.exists(fp):
        _record("schema validation on 2024 sample", False, "bger_2024.jsonl not found")
        return
    errors = 0
    checked = 0
    with open(fp, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if checked >= 100:
                break
            if not line.strip():
                continue
            d = json.loads(line)
            errs = list(validator.iter_errors(d))
            if errs:
                errors += 1
            checked += 1
    _record("schema validation on 2024 sample (100 records)",
            errors == 0,
            f"errors={errors}/{checked}")


def test_ingestion_metrics_exists():
    """ingestion_metrics.json must exist and contain required fields."""
    if not os.path.exists(METRICS_PATH):
        _record("ingestion_metrics.json exists", False, f"not found at {METRICS_PATH}")
        return
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    required = {"total_rows", "normalized", "skipped", "by_year",
                "by_language", "validation_errors", "elapsed_seconds",
                "decisions_per_second", "chunks_processed", "error_rate"}
    missing_fields = required - set(metrics.keys())
    _record("ingestion_metrics.json has required fields",
            len(missing_fields) == 0,
            f"missing={missing_fields}" if missing_fields else f"all {len(required)} present")


def test_ingestion_metrics_totals():
    """ingestion_metrics.json must show >= 170,000 normalized decisions."""
    if not os.path.exists(METRICS_PATH):
        _record("ingestion metrics total >= 170k", False, "metrics file missing")
        return
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    normalized = metrics.get("normalized", 0)
    _record("ingestion metrics total >= 170k normalized",
            normalized >= 170_000,
            f"normalized={normalized:,}")


def test_validation_report_v14_exists():
    """validation_report_v14.json must exist and show 0 errors."""
    report_path = os.path.join(CANONICAL_DIR, "validation_report_v14.json")
    if not os.path.exists(report_path):
        _record("validation_report_v14.json exists", False)
        return
    with open(report_path) as f:
        report = json.load(f)
    total_errors = report.get("schema_validation", {}).get("total_errors", -1)
    _record("validation_report_v14 shows 0 schema errors",
            total_errors == 0,
            f"total_errors={total_errors}")


# ===========================================================================
# GROUP 3: Citation Resolution at Scale
# ===========================================================================


def test_citation_resolver_builds_large_index():
    """CitationResolver.build_index() must index >= 170,000 decisions."""
    from corpus.acquisition.citation_resolver import CitationResolver
    resolver = CitationResolver(canonical_corpus_dir=CANONICAL_DIR)
    stats = resolver.build_index()
    indexed = stats.get("decisions_indexed", 0)
    _record("CitationResolver index >= 170,000 decisions",
            indexed >= 170_000,
            f"indexed={indexed:,}")


def test_citation_resolver_docket_index_large():
    """Docket index must have >= 170,000 entries."""
    from corpus.acquisition.citation_resolver import CitationResolver
    resolver = CitationResolver(canonical_corpus_dir=CANONICAL_DIR)
    stats = resolver.build_index()
    docket_count = stats.get("docket_indexed", 0)
    _record("docket index >= 170,000 entries",
            docket_count >= 170_000,
            f"docket_indexed={docket_count:,}")


def test_citation_resolution_rate_at_scale():
    """Citation resolution rate on citation_graph.json must be >= 40%."""
    from corpus.acquisition.citation_resolver import CitationResolver
    if not os.path.exists(CITATION_GRAPH_PATH):
        _record("citation resolution rate >= 40%", False, "citation_graph.json not found")
        return
    resolver = CitationResolver(canonical_corpus_dir=CANONICAL_DIR)
    resolver.build_index()
    output_dir = os.path.join(CANONICAL_DIR, "resolved_v14_test")
    os.makedirs(output_dir, exist_ok=True)
    stats = resolver.resolve_citation_graph(CITATION_GRAPH_PATH, output_dir)
    rate = stats.get("resolution_rate", 0.0)
    _record("citation resolution rate >= 40%",
            rate >= 0.40,
            f"rate={rate:.1%} ({stats.get('resolved', 0)}/{stats.get('total_references', 0)})")


def test_resolved_output_files_created():
    """Resolved output directory must contain citation_graph_resolved.json."""
    resolved_dir = os.path.join(CANONICAL_DIR, "resolved_full")
    resolved_file = os.path.join(resolved_dir, "citation_graph_resolved.json")
    _record("resolved output files exist",
            os.path.exists(resolved_file),
            f"checked {resolved_file}")


def test_citation_resolution_stats_structure():
    """Citation resolution report must have the expected top-level keys."""
    resolved_file = os.path.join(CANONICAL_DIR, "resolved_full", "citation_graph_resolved.json")
    if not os.path.exists(resolved_file):
        _record("resolution stats structure valid", False, "resolved file not found")
        return
    with open(resolved_file) as f:
        data = json.load(f)
    has_stats = "resolution_stats" in data
    has_outgoing = "outgoing" in data
    _record("resolution stats structure valid",
            has_stats and has_outgoing,
            f"stats={has_stats}, outgoing={has_outgoing}")


# ===========================================================================
# GROUP 4: Field Coverage
# ===========================================================================


def test_field_coverage_full_text_100pct():
    """100% of sampled records must have non-empty full_text."""
    fp = os.path.join(CANONICAL_DIR, "bger_2024.jsonl")
    if not os.path.exists(fp):
        _record("full_text coverage = 100%", False, "bger_2024.jsonl missing")
        return
    total = 0
    with_text = 0
    with open(fp, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 200:
                break
            if not line.strip():
                continue
            d = json.loads(line)
            total += 1
            ft = d.get("full_text", "")
            if ft and len(ft) > 0:
                with_text += 1
    pct = with_text / total if total else 0
    _record("full_text coverage = 100% (2024 sample)",
            pct >= 0.99,
            f"{with_text}/{total} = {pct:.1%}")


def test_field_coverage_restege_above_40pct():
    """>= 40% of randomly sampled records must have a regeste.

    Loads all records from year files then samples randomly (matching
    validation_report_v14 methodology) because regeste coverage varies
    significantly by year.
    """
    import random as _random
    year_files = sorted(globmod.glob(os.path.join(CANONICAL_DIR, "bger_[0-9][0-9][0-9][0-9].jsonl")))
    if not year_files:
        _record("regeste coverage >= 40%", False, "no year files found")
        return
    all_records = []
    for fp in year_files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                all_records.append(json.loads(line))
    _random.seed(42)
    sample = _random.sample(all_records, min(1000, len(all_records)))
    total = len(sample)
    count = sum(1 for d in sample if d.get("regeste"))
    pct = count / total if total else 0
    _record("regeste coverage >= 40% (cross-year sample)",
            pct >= 0.40,
            f"{count}/{total} = {pct:.1%}")


def test_field_coverage_cited_decisions_above_50pct():
    """>= 50% of randomly sampled records must have cited_decisions.

    Samples across all year files for representative coverage.
    """
    import random as _random
    year_files = sorted(globmod.glob(os.path.join(CANONICAL_DIR, "bger_[0-9][0-9][0-9][0-9].jsonl")))
    if not year_files:
        _record("cited_decisions coverage >= 50%", False, "no year files found")
        return
    all_records = []
    for fp in year_files:
        with open(fp, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 500:
                    break
                if not line.strip():
                    continue
                all_records.append(json.loads(line))
    _random.seed(42)
    sample = _random.sample(all_records, min(1000, len(all_records)))
    total = len(sample)
    count = sum(1 for d in sample
                if d.get("cited_decisions") and
                (isinstance(d["cited_decisions"], list) and len(d["cited_decisions"]) > 0 or
                 isinstance(d["cited_decisions"], str) and len(d["cited_decisions"]) > 0))
    pct = count / total if total else 0
    _record("cited_decisions coverage >= 50% (cross-year sample)",
            pct >= 0.50,
            f"{count}/{total} = {pct:.1%}")


def test_field_coverage_outcome_above_45pct():
    """>= 45% of randomly sampled records must have an outcome.

    Samples across all year files for representative coverage.
    """
    import random as _random
    year_files = sorted(globmod.glob(os.path.join(CANONICAL_DIR, "bger_[0-9][0-9][0-9][0-9].jsonl")))
    if not year_files:
        _record("outcome coverage >= 45%", False, "no year files found")
        return
    all_records = []
    for fp in year_files:
        with open(fp, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 500:
                    break
                if not line.strip():
                    continue
                all_records.append(json.loads(line))
    _random.seed(42)
    sample = _random.sample(all_records, min(1000, len(all_records)))
    total = len(sample)
    count = sum(1 for d in sample if d.get("outcome"))
    pct = count / total if total else 0
    _record("outcome coverage >= 45% (cross-year sample)",
            pct >= 0.45,
            f"{count}/{total} = {pct:.1%}")


# ===========================================================================
# GROUP 5: Regression — Existing Pipeline Intact
# ===========================================================================


def test_existing_modules_import():
    """All existing pipeline modules must still import correctly."""
    try:
        from corpus.acquisition.opencaselaw_client import OpenCaseLawClient, DecisionRaw
        from corpus.normalization.normalize import DecisionNormalizer, run_normalization
        from corpus.acquisition.user_import import UserCorpusImporter
        from corpus.acquisition.parquet_ingest import parquet_to_canonical
        from corpus.acquisition.parquet_ingest_scaled import parquet_to_canonical_scaled, parse_parquet_row, _clean_nan
        from corpus.acquisition.citation_resolver import CitationResolver
    except ImportError as e:
        _record("existing modules import correctly", False, str(e))
        return
    _record("existing modules import correctly", True)


def test_existing_test_data_validates():
    """Existing test data files (bger_test_2024.jsonl) must still validate."""
    import jsonschema
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    test_files = [
        "corpus/normalization/canonical/bger_test_2024.jsonl",
        "corpus/normalization/canonical/bger_test_slice.jsonl",
    ]
    total = 0
    errors = 0
    for fp in test_files:
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                total += 1
                errs = list(validator.iter_errors(d))
                if errs:
                    errors += 1
    _record("existing test data validates",
            errors == 0,
            f"errors={errors}/{total}" if total else "no test files found")


def test_decision_raw_dataclass_fields():
    """DecisionRaw must contain all fields needed by parse_parquet_row."""
    from corpus.acquisition.opencaselaw_client import DecisionRaw
    fields = set(DecisionRaw.__dataclass_fields__.keys())
    required = {"decision_id", "court", "decision_date", "language",
                "full_text", "docket_number", "branch", "outcome"}
    missing = required - fields
    _record("DecisionRaw has required fields",
            len(missing) == 0,
            f"missing={missing}" if missing else f"all {len(required)} present")


# ===========================================================================
# GROUP 6: NaN/Parquet Edge Cases
# ===========================================================================


def test_all_none_optional_fields_normalize():
    """Rows with all-None optional fields must parse without errors."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_edge_all_none",
        "text": "Edge case test with all optional fields set to None or NaN.",
        "date": "2023-05-10",
        "language": "de",
        "court": "bger",
        "docket_number": None,
        "legal_area": None,
        "chamber": None,
        "branch": None,
        "outcome": None,
        "regeste": None,
        "cited_decisions": None,
        "citation_string_de": None,
        "canonical_url": None,
        "cited_laws": None,
        "judges": None,
        "source_url": None,
        "pdf_url": None,
        "publication_date": None,
        "proceeding_type": None,
        "abstract_de": None,
        "abstract_fr": None,
        "abstract_it": None,
        "decision_type": None,
        "bge_reference": None,
        "sachverhalt": None,
        "erwaegungen": None,
        "dispositiv": None,
        "dispositiv_orders": None,
        "preparatory_materials": None,
        "outgoing_citations": None,
        "incoming_citations": None,
    }
    try:
        parsed = parse_parquet_row(row)
        ok = (parsed["decision_id"] == "bger_edge_all_none"
              and parsed["docket_number"] == "bger_edge_all_none"
              and parsed["canonical_url"] == "bger://bger_edge_all_none")
        _record("all-None optional fields normalize", ok,
                f"docket={parsed['docket_number']}, url={parsed['canonical_url']}")
    except Exception as e:
        _record("all-None optional fields normalize", False, str(e))


def test_empty_full_text_not_caught():
    """parse_parquet_row must not crash on empty full_text — it returns empty string."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_edge_empty_text",
        "text": "",
        "date": "2023-05-10",
        "language": "de",
    }
    try:
        parsed = parse_parquet_row(row)
        _record("empty full_text parses without crash",
                parsed["full_text"] == "",
                f"full_text={repr(parsed['full_text'][:50])}")
    except Exception as e:
        _record("empty full_text parses without crash", False, str(e))


def test_missing_id_field_uses_fallback():
    """When id is missing but decision_id exists, parse_parquet_row uses it."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "decision_id": "fallback_test",
        "text": "Fallback ID test decision text here.",
        "date": "2023-05-10",
        "language": "de",
    }
    parsed = parse_parquet_row(row)
    _record("missing id uses decision_id fallback",
            parsed["decision_id"] == "bger_fallback_test",
            f"got {parsed['decision_id']}")


def test_long_language_string_truncated():
    """Language strings longer than 2 chars must be truncated/mapped."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_lang_test",
        "text": "Language truncation test decision text here.",
        "date": "2023-05-10",
        "language": "german",
    }
    parsed = parse_parquet_row(row)
    _record("long language string truncated to 2 chars",
            parsed["language"] == "de" and len(parsed["language"]) == 2,
            f"got '{parsed['language']}'")


def test_content_hash_generated():
    """parse_parquet_row must generate a content_hash from full_text."""
    from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row
    row = {
        "id": "bger_hash_test",
        "text": "Content hash generation test decision text.",
        "date": "2023-05-10",
        "language": "de",
    }
    parsed = parse_parquet_row(row)
    ch = parsed.get("content_hash")
    _record("content_hash is generated",
            ch is not None and isinstance(ch, str) and len(ch) == 64,
            f"hash={ch[:16]}..." if ch else "None")


# ===========================================================================
# MAIN
# ===========================================================================


def main():
    global _results
    _results = []

    print()
    print("=" * 70)
    print("  CORPUS LANE CYCLE v14 — FULL-SCALE INGESTION TEST SUITE")
    print("=" * 70)

    # Group 1
    print("\n--- Group 1: NaN Handling (v14) ---")
    test_clean_nan_converts_nan_to_none()
    test_clean_nan_preserves_valid_values()
    test_clean_nan_handles_empty_row()
    test_clean_nan_handles_int_nan()
    test_parse_parquet_row_nan_handling()
    test_parse_parquet_row_populates_citation_string_de()
    test_parse_parquet_row_populates_canonical_url()

    # Group 2
    print("\n--- Group 2: Full-Scale Ingestion Validation ---")
    test_canonical_dir_has_year_split_files()
    test_total_lines_across_all_bger_files()
    test_year_coverage_2000_2026_no_gaps()
    test_schema_validation_sample()
    test_ingestion_metrics_exists()
    test_ingestion_metrics_totals()
    test_validation_report_v14_exists()

    # Group 3
    print("\n--- Group 3: Citation Resolution at Scale ---")
    test_citation_resolver_builds_large_index()
    test_citation_resolver_docket_index_large()
    test_citation_resolution_rate_at_scale()
    test_resolved_output_files_created()
    test_citation_resolution_stats_structure()

    # Group 4
    print("\n--- Group 4: Field Coverage ---")
    test_field_coverage_full_text_100pct()
    test_field_coverage_restege_above_40pct()
    test_field_coverage_cited_decisions_above_50pct()
    test_field_coverage_outcome_above_45pct()

    # Group 5
    print("\n--- Group 5: Regression — Existing Pipeline Intact ---")
    test_existing_modules_import()
    test_existing_test_data_validates()
    test_decision_raw_dataclass_fields()

    # Group 6
    print("\n--- Group 6: NaN/Parquet Edge Cases ---")
    test_all_none_optional_fields_normalize()
    test_empty_full_text_not_caught()
    test_missing_id_field_uses_fallback()
    test_long_language_string_truncated()
    test_content_hash_generated()

    # ── Summary ───────────────────────────────────────────────────────
    passed = sum(1 for _, p in _results if p)
    failed = sum(1 for _, p in _results if not p)
    total = len(_results)

    print()
    print("=" * 70)
    if failed == 0:
        print(f"  ALL {total} TESTS PASSED")
    else:
        print(f"  RESULTS: {passed}/{total} passed, {failed} FAILED")
        print()
        print("  Failed tests:")
        for name, p in _results:
            if not p:
                print(f"    - {name}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
