#!/usr/bin/env python3
"""
Ingest BGE Parquet (officially published decisions) into the canonical corpus.

This adds ~21k BGE decisions to reach ~195k total, enabling BGE citation resolution.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from corpus.acquisition.opencaselaw_client import DecisionRaw
from corpus.normalization.normalize import DecisionNormalizer
from corpus.acquisition.parquet_ingest_scaled import parse_parquet_row, _clean_nan


BGE_PARQUET_PATH = "corpus/acquisition/parquet/bge.parquet"
OUTPUT_DIR = "corpus/normalization/canonical"
SOURCE_VERSION = "opencaselaw_bge_parquet_2026-08-31"
SCHEMA_PATH = "corpus/schema/decision_schema.json"
REPRODUCTION_ACQUIRED_AT = "2026-08-31T10:23:21Z"


def ingest_bge_parquet():
    """Ingest BGE Parquet into year-split JSONL files."""
    start = time.time()
    
    print("=" * 60)
    print("Ingesting BGE Parquet (officially published decisions)")
    print("=" * 60)
    
    pf = pq.ParquetFile(BGE_PARQUET_PATH)
    total_rows = pf.metadata.num_rows
    print(f"BGE Parquet: {total_rows} rows, {pf.metadata.num_row_groups} row groups")
    
    table = pf.read()
    df = table.to_pandas()
    print(f"Loaded {len(df)} rows")
    
    normalizer = DecisionNormalizer(SCHEMA_PATH)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    counts = {"normalized": 0, "skipped": 0, "errors": 0}
    by_year, by_language = {}, {}
    content_hashes, decision_ids = set(), set()
    year_fh = {}
    
    def get_fh(year):
        if year not in year_fh:
            year_fh[year] = open(
                os.path.join(OUTPUT_DIR, f"bge_{year}.jsonl"), "w", encoding="utf-8"
            )
        return year_fh[year]
    
    for idx, (_, row_series) in enumerate(df.iterrows()):
        row_dict = row_series.to_dict()
        parsed = parse_parquet_row(row_dict)
        
        # For BGE court, ensure docket_number has "BGE " prefix for citation matching
        if parsed.get("court") == "bge" and parsed.get("docket_number"):
            docket = parsed["docket_number"]
            if not docket.startswith("BGE ") and " " in docket:
                parsed["docket_number"] = f"BGE {docket}"
                parsed["bge_reference"] = parsed["docket_number"]
                parsed["citation_string_de"] = parsed["docket_number"]
        
        ch = parsed.get("content_hash")
        did = parsed.get("decision_id")
        if (ch and ch in content_hashes) or did in decision_ids:
            counts["skipped"] += 1
            continue
        
        try:
            raw = DecisionRaw(**{k: v for k, v in parsed.items()
                                 if k in DecisionRaw.__dataclass_fields__})
            canonical = normalizer.normalize(raw, SOURCE_VERSION)
        except Exception as e:
            counts["errors"] += 1
            continue
        
        if canonical is None:
            counts["skipped"] += 1
            continue
        
        # Deterministic provenance timestamp
        canonical.setdefault("provenance", {})["acquired_at"] = REPRODUCTION_ACQUIRED_AT
        
        if ch:
            content_hashes.add(ch)
        decision_ids.add(did)
        
        year = canonical.get("decision_date", "unknown")[:4]
        get_fh(year).write(json.dumps(canonical, ensure_ascii=False) + "\n")
        counts["normalized"] += 1
        by_year[year] = by_year.get(year, 0) + 1
        lang = canonical.get("language", "unknown")
        by_language[lang] = by_language.get(lang, 0) + 1
        
        if idx % 5000 == 0:
            print(f"  {idx:,}/{total_rows:,} normalized={counts['normalized']:,}")
    
    for fh in year_fh.values():
        fh.close()
    
    # Count written
    total_written = 0
    for fp in Path(OUTPUT_DIR).glob("bge_[0-9][0-9][0-9][0-9].jsonl"):
        with open(fp, "r") as f:
            total_written += sum(1 for _ in f)
    
    elapsed = time.time() - start
    print(f"\nBGE Ingestion Complete:")
    print(f"  normalized={counts['normalized']:,} skipped={counts['skipped']:,} errors={counts['errors']:,}")
    print(f"  written_to_disk={total_written:,}")
    print(f"  by_language={by_language}")
    print(f"  by_year={dict(sorted(by_year.items()))}")
    print(f"  elapsed={elapsed:.1f}s ({counts['normalized']/elapsed:.1f} dec/s)")
    
    return {
        "normalized": counts["normalized"],
        "skipped": counts["skipped"],
        "errors": counts["errors"],
        "by_year": dict(sorted(by_year.items())),
        "by_language": by_language,
        "written_to_disk": total_written,
        "elapsed_seconds": round(elapsed, 1),
    }


if __name__ == "__main__":
    metrics = ingest_bge_parquet()
    # Save metrics
    metrics_path = os.path.join(OUTPUT_DIR, "bge_ingestion_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\nMetrics saved to {metrics_path}")
