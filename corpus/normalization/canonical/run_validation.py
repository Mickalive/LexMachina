#!/usr/bin/env python3
"""Validation script for LexMachina canonical JSONL corpus."""
import json
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema

CANONICAL_DIR = Path(__file__).parent
SCHEMA_PATH = CANONICAL_DIR.parent.parent / "schema" / "decision_schema.json"
REPORT_PATH = CANONICAL_DIR / "validation_report_v14.json"

# ---------- helpers ----------

def load_year_files():
    """Return dict year_str -> Path for canonical bger_YYYY.jsonl files."""
    year_files = {}
    for p in sorted(CANONICAL_DIR.glob("bger_[0-9][0-9][0-9][0-9].jsonl")):
        year = p.stem.split("_")[1]
        year_files[year] = p
    return year_files

def iter_jsonl(path):
    """Yield parsed JSON objects from a JSONL file, skipping malformed lines."""
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line), i
            except json.JSONDecodeError:
                pass  # count later via error tracking

# ---------- 1. Schema validation ----------

def validate_schema(schema, year_files):
    validator = jsonschema.Draft7Validator(schema)
    total = 0
    errors = []
    per_year = {}
    per_year_errors = {}

    for year, path in sorted(year_files.items()):
        count = 0
        year_err = 0
        for obj, line_no in iter_jsonl(path):
            total += 1
            count += 1
            errs = list(validator.iter_errors(obj))
            if errs:
                year_err += len(errs)
                for e in errs[:3]:  # cap per-record errors to keep list bounded
                    errors.append({
                        "file": path.name,
                        "line": line_no,
                        "decision_id": obj.get("decision_id", "UNKNOWN"),
                        "path": list(e.absolute_path),
                        "message": e.message,
                    })
        per_year[year] = count
        per_year_errors[year] = year_err

    return {
        "total_validated": total,
        "total_errors": len(errors),
        "first_3_errors": errors[:3],
        "per_year_counts": per_year,
        "per_year_errors": per_year_errors,
    }

# ---------- 2. Field coverage ----------

def field_coverage(schema, year_files, n=1000, seed=42):
    # Collect all decision_ids first
    all_records = []
    for year, path in sorted(year_files.items()):
        for obj, _ in iter_jsonl(path):
            all_records.append(obj)

    random.seed(seed)
    if len(all_records) <= n:
        sample = all_records
    else:
        sample = random.sample(all_records, n)

    fields = ["full_text", "regeste", "bge_reference", "cited_decisions",
              "cited_laws", "outcome", "legal_area"]
    fill = {f: 0 for f in fields}

    text_lengths = []
    lang_counter = Counter()

    for rec in sample:
        # full_text: non-empty string
        v = rec.get("full_text")
        if v and isinstance(v, str) and len(v.strip()) > 0:
            fill["full_text"] += 1
            text_lengths.append(len(v))

        # regeste: non-empty string
        v = rec.get("regeste")
        if v and isinstance(v, str) and len(v.strip()) > 0:
            fill["regeste"] += 1

        # bge_reference: non-empty string
        v = rec.get("bge_reference")
        if v and isinstance(v, str) and len(v.strip()) > 0:
            fill["bge_reference"] += 1

        # cited_decisions: non-empty list
        v = rec.get("cited_decisions")
        if isinstance(v, list) and len(v) > 0:
            fill["cited_decisions"] += 1

        # cited_laws: non-empty list
        v = rec.get("cited_laws")
        if isinstance(v, list) and len(v) > 0:
            fill["cited_laws"] += 1

        # outcome: not null
        v = rec.get("outcome")
        if v is not None and v != "null":
            fill["outcome"] += 1

        # legal_area: not null
        v = rec.get("legal_area")
        if v is not None and v != "null":
            fill["legal_area"] += 1

        lang = rec.get("language", "unknown")
        lang_counter[lang] += 1

    total = len(sample)
    fill_rates = {k: {"count": v, "rate": round(v / total, 4)} for k, v in fill.items()}

    if text_lengths:
        tl_stats = {
            "min": min(text_lengths),
            "max": max(text_lengths),
            "mean": round(statistics.mean(text_lengths), 1),
            "median": round(statistics.median(text_lengths), 1),
        }
    else:
        tl_stats = {"min": 0, "max": 0, "mean": 0, "median": 0}

    return {
        "sample_size": total,
        "fill_rates": fill_rates,
        "language_distribution": dict(lang_counter),
        "text_length_stats": tl_stats,
    }

# ---------- 3. Year coverage ----------

def year_coverage(year_files):
    coverage = {}
    for year, path in sorted(year_files.items()):
        count = 0
        for _ in iter_jsonl(path):
            count += 1
        coverage[year] = count

    expected_range = list(range(2000, 2027))
    covered = [int(y) for y in coverage if int(y) in expected_range]
    missing = [y for y in expected_range if y not in covered]

    return {
        "per_year_line_counts": coverage,
        "expected_range": "2000-2026",
        "years_covered": sorted(covered),
        "missing_years": missing,
        "total_pre_2000": sum(v for y, v in coverage.items() if int(y) < 2000),
    }

# ---------- 4. Sample from 2024 ----------

def sample_2024(year_files, n=3, seed=42):
    path = year_files.get("2024")
    if not path:
        return {"error": "No 2024 file found"}

    records = [obj for obj, _ in iter_jsonl(path)]
    random.seed(seed)
    chosen = random.sample(records, min(n, len(records)))

    samples = []
    for rec in chosen:
        samples.append({
            "decision_id": rec.get("decision_id"),
            "language": rec.get("language"),
            "text_length": rec.get("text_length"),
            "has_bge_reference": rec.get("bge_reference") is not None and rec.get("bge_reference") != "null",
        })
    return samples

# ---------- main ----------

def main():
    schema = json.loads(SCHEMA_PATH.read_text())
    year_files = load_year_files()

    print(f"Found {len(year_files)} year-split files")

    print("Running schema validation …")
    sv = validate_schema(schema, year_files)

    print("Running field coverage …")
    fc = field_coverage(schema, year_files)

    print("Running year coverage …")
    yc = year_coverage(year_files)

    print("Sampling from 2024 …")
    sp = sample_2024(year_files)

    report = {
        "report_version": "v14",
        "schema_validation": sv,
        "field_coverage": fc,
        "year_coverage": yc,
        "sample_2024": sp,
    }

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReport written to {REPORT_PATH}")

    # ---------- summary to stdout ----------
    print("\n" + "=" * 70)
    print("VALIDATION REPORT SUMMARY")
    print("=" * 70)

    print(f"\n1. SCHEMA VALIDATION")
    print(f"   Total validated:  {sv['total_validated']}")
    print(f"   Total errors:     {sv['total_errors']}")
    if sv["first_3_errors"]:
        print(f"   First errors:")
        for e in sv["first_3_errors"]:
            print(f"     - {e['file']}:{e['line']} [{e['decision_id']}] path={'.'.join(str(p) for p in e['path'])}")
            print(f"       {e['message'][:120]}")

    print(f"\n2. FIELD COVERAGE (n={fc['sample_size']} sample)")
    for k, v in fc["fill_rates"].items():
        print(f"   {k:20s}: {v['count']:5d}/{fc['sample_size']}  ({v['rate']*100:.1f}%)")
    print(f"   Language dist:     {fc['language_distribution']}")
    tl = fc["text_length_stats"]
    print(f"   text_length:       min={tl['min']}  max={tl['max']}  mean={tl['mean']}  median={tl['median']}")

    print(f"\n3. YEAR COVERAGE")
    yc_data = yc["per_year_line_counts"]
    total_in_range = sum(v for y, v in yc_data.items() if int(y) in range(2000, 2027))
    print(f"   Range: 2000-2026 (requested)")
    print(f"   Covered years: {len(yc['years_covered'])}/27")
    if yc["missing_years"]:
        print(f"   MISSING: {yc['missing_years']}")
    else:
        print(f"   No missing years in 2000-2026")
    print(f"   Total (2000-2026): {total_in_range}")
    print(f"   Pre-2000 records:  {yc['total_pre_2000']}")

    print(f"\n4. 2024 SAMPLES")
    for s in sp:
        print(f"   {s['decision_id']}  lang={s['language']}  len={s['text_length']}  bge_ref={s['has_bge_reference']}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
