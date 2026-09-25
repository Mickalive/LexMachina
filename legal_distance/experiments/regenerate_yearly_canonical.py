#!/usr/bin/env python3
"""
Download parquet from HuggingFace and generate yearly canonical JSONL files.
Optimized for 174k corpus with year-split output for dense embedding computation.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Iterator, List
from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq
import urllib.request

# Add corpus to path
sys.path.insert(0, "/tmp/lex_accepted/corpus")
from corpus.normalization.normalize import DecisionNormalizer, NormalizationStats
from corpus.acquisition.opencaselaw_client import DecisionRaw


PARQUET_URL = "https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet"
PARQUET_PATH = "/tmp/bger.parquet"
CANONICAL_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
SCHEMA_PATH = "/tmp/lex_accepted/corpus/corpus/schema/decision_schema.json"
SOURCE_VERSION = "opencaselaw_parquet_2026-09-25"


def download_parquet(url: str, output_path: str, force: bool = False) -> str:
    """Download Parquet file with progress reporting."""
    if os.path.exists(output_path) and not force:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Parquet file already exists at {output_path} ({size_mb:.1f} MB)")
        return output_path

    print(f"Downloading from {url}...")

    def progress_hook(block_num, block_size, total_size):
        if total_size > 0:
            percent = min(100, (block_num * block_size * 100) // total_size)
            downloaded_mb = block_num * block_size / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            if block_num % 50 == 0 or percent == 100:
                print(f"  Progress: {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")

    urllib.request.urlretrieve(url, output_path, reporthook=progress_hook)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Downloaded {size_mb:.1f} MB to {output_path}")
    return output_path


def parse_parquet_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single Parquet row into fields matching our raw schema."""
    import math
    
    def clean_nan(val):
        if isinstance(val, float) and math.isnan(val):
            return None
        return val
    
    full_text = str(clean_nan(row.get("full_text")) or "")

    decision_id = clean_nan(row.get("id")) or clean_nan(row.get("decision_id")) or clean_nan(row.get("doc_id")) or ""
    if decision_id and not decision_id.startswith("bger_"):
        decision_id = f"bger_{decision_id}"

    decision_date = clean_nan(row.get("date")) or clean_nan(row.get("decision_date")) or clean_nan(row.get("publication_date")) or ""
    if len(str(decision_date)) == 10:
        pass  # YYYY-MM-DD
    elif len(str(decision_date)) == 7:
        decision_date = f"{decision_date}-01"
    elif len(str(decision_date)) == 4:
        decision_date = f"{decision_date}-01-01"

    language = clean_nan(row.get("language")) or clean_nan(row.get("lang")) or "de"
    if len(str(language)) > 2:
        lang_map = {"german": "de", "french": "fr", "italian": "it", "deutsch": "de", "französisch": "fr", "italienisch": "it"}
        language = lang_map.get(str(language).lower(), "de")[:2]

    court = clean_nan(row.get("court")) or clean_nan(row.get("court_id")) or "bger"
    if court not in ("bge", "bger", "bvger", "bstger", "bpatger"):
        court = "bger"

    # Generate content hash
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest() if full_text else None

    # Provide required fields for DecisionRaw
    citation_string_de = clean_nan(row.get("docket_number")) or clean_nan(row.get("citation")) or decision_id
    canonical_url = clean_nan(row.get("url")) or clean_nan(row.get("source_url")) or f"https://entscheide.bger.ch/{decision_id}"

    return {
        "decision_id": str(decision_id),
        "court": str(court),
        "decision_date": str(decision_date)[:10],
        "language": str(language)[:2],
        "title": clean_nan(row.get("title")),
        "full_text": full_text,
        "docket_number": clean_nan(row.get("docket_number")) or clean_nan(row.get("citation")) or decision_id,
        "legal_area": clean_nan(row.get("legal_area")) or clean_nan(row.get("branch")),
        "chamber": clean_nan(row.get("chamber")),
        "branch": clean_nan(row.get("branch")),
        "outcome": clean_nan(row.get("outcome")),
        "regeste": clean_nan(row.get("regeste")),
        "cited_decisions": clean_nan(row.get("cited_decisions")),
        "cited_laws": clean_nan(row.get("cited_laws")),
        "judges": clean_nan(row.get("judges")),
        "source_url": clean_nan(row.get("url")) or clean_nan(row.get("source_url")),
        "pdf_url": clean_nan(row.get("pdf_url")),
        "publication_date": clean_nan(row.get("publication_date")),
        "proceeding_type": clean_nan(row.get("proceeding_type")),
        "abstract_de": clean_nan(row.get("abstract_de")),
        "abstract_fr": clean_nan(row.get("abstract_fr")),
        "abstract_it": clean_nan(row.get("abstract_it")),
        "decision_type": clean_nan(row.get("decision_type")),
        "bge_reference": clean_nan(row.get("bge_reference")),
        # Structural fields (may not be in Parquet)
        "sachverhalt": clean_nan(row.get("sachverhalt")),
        "erwaegungen": clean_nan(row.get("erwaegungen")),
        "dispositiv": clean_nan(row.get("dispositiv")),
        "dispositiv_orders": clean_nan(row.get("dispositiv_orders")),
        "preparatory_materials": clean_nan(row.get("preparatory_materials")),
        "outgoing_citations": clean_nan(row.get("outgoing_citations")),
        "incoming_citations": clean_nan(row.get("incoming_citations")),
        # Required fields for DecisionRaw
        "citation_string_de": citation_string_de,
        "canonical_url": canonical_url,
        "content_hash": content_hash,
    }


def write_yearly_jsonl(
    decisions_by_year: Dict[str, List[Dict]],
    canonical_dir: Path,
    normalizer: DecisionNormalizer,
    source_version: str
) -> Dict[str, int]:
    """Write decisions to yearly JSONL files and return counts."""
    counts = {}
    for year, decisions in decisions_by_year.items():
        output_path = canonical_dir / f"bger_{year}.jsonl"
        canonical_dir.mkdir(parents=True, exist_ok=True)
        
        written = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for raw_dict in decisions:
                try:
                    raw = DecisionRaw(**{k: v for k, v in raw_dict.items() if k in DecisionRaw.__dataclass_fields__})
                    canonical = normalizer.normalize(raw, source_version)
                    if canonical:
                        f.write(json.dumps(canonical, ensure_ascii=False) + "\n")
                        written += 1
                except Exception as e:
                    continue
        
        counts[year] = written
        print(f"  {year}: {written} decisions written to {output_path}")
    
    return counts


def main():
    print("=" * 70)
    print("DOWNLOAD PARQUET AND GENERATE YEARLY CANONICAL JSONL FILES")
    print("=" * 70)
    start_time = time.time()

    # Step 1: Download parquet
    print("\n[1/3] Downloading parquet from HuggingFace...")
    download_parquet(PARQUET_URL, PARQUET_PATH, force=False)

    # Step 2: Inspect schema
    print("\n[2/3] Loading parquet and processing...")
    pf = pq.ParquetFile(PARQUET_PATH)
    print(f"Parquet rows: {pf.metadata.num_rows}")
    print(f"Row groups: {pf.metadata.num_row_groups}")
    print(f"Columns: {pf.metadata.num_columns}")

    # Load full parquet into pandas
    print("Loading full parquet into pandas...")
    df = pd.read_parquet(PARQUET_PATH, engine="pyarrow")
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    if "language" in df.columns:
        print(f"Language distribution: {df['language'].value_counts().to_dict()}")

    # Step 3: Normalize and write yearly files
    print("\n[3/3] Normalizing and writing yearly JSONL files...")
    normalizer = DecisionNormalizer(SCHEMA_PATH)
    
    # Group by year
    decisions_by_year = defaultdict(list)
    
    total_input = 0
    total_output = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        total_input += 1
        if total_input % 20000 == 0:
            print(f"  Processed {total_input} rows...")
        
        row_dict = row.to_dict()
        parsed = parse_parquet_row(row_dict)
        
        # Extract year for grouping
        year = parsed.get("decision_date", "unknown")[:4]
        if year == "unkn" or not year.isdigit():
            year = "unknown"
        
        decisions_by_year[year].append(parsed)
    
    print(f"\nYear distribution (raw): {dict(sorted({k: len(v) for k, v in decisions_by_year.items()}.items()))}")
    
    # Normalize and write
    counts = write_yearly_jsonl(decisions_by_year, CANONICAL_DIR, normalizer, SOURCE_VERSION)
    
    print(f"\nYear distribution (normalized): {dict(sorted(counts.items()))}")
    print(f"Total input: {total_input}")
    print(f"Total output: {sum(counts.values())}")
    print(f"Elapsed: {time.time() - start_time:.1f}s")
    
    # Also write a combined file for reference
    print("\nWriting combined bger_2000plus.jsonl for reference...")
    combined_path = CANONICAL_DIR / "bger_2000plus.jsonl"
    with open(combined_path, "w", encoding="utf-8") as f:
        for year in sorted(counts.keys()):
            if year == "unknown":
                continue
            year_path = CANONICAL_DIR / f"bger_{year}.jsonl"
            if year_path.exists():
                with open(year_path, "r") as src:
                    f.write(src.read())
    
    print("Done!")


if __name__ == "__main__":
    main()