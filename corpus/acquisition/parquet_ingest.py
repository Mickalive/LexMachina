"""
Parquet ingestion pipeline: download BGer Parquet from HuggingFace, load, normalize to canonical schema.
End-to-end validation of the bulk corpus path.
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator

import pandas as pd
import pyarrow.parquet as pq

from corpus.normalization.normalize import DecisionNormalizer, NormalizationStats


@dataclass
class ParquetIngestConfig:
    """Configuration for Parquet ingestion."""
    parquet_url: str = "https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet"
    output_dir: str = "corpus/acquisition/parquet"
    canonical_output_dir: str = "corpus/normalization/canonical"
    sample_size: Optional[int] = 500  # None = all rows
    source_version: str = "opencaselaw_parquet_2026-08-27"
    force_download: bool = False


def download_parquet(url: str, output_path: str, force: bool = False) -> str:
    """Download Parquet file with progress reporting."""
    import urllib.request

    if os.path.exists(output_path) and not force:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Parquet file already exists at {output_path} ({size_mb:.1f} MB)")
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
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


def inspect_parquet_schema(parquet_path: str) -> Dict[str, Any]:
    """Inspect Parquet schema and metadata without loading full dataset."""
    pf = pq.ParquetFile(parquet_path)
    schema = pf.schema_arrow
    metadata = pf.metadata

    result = {
        "num_rows": metadata.num_rows,
        "num_row_groups": metadata.num_row_groups,
        "num_columns": metadata.num_columns,
        "schema_fields": [],
        "file_size_mb": os.path.getsize(parquet_path) / (1024 * 1024),
    }

    for field in schema:
        result["schema_fields"].append({
            "name": field.name,
            "type": str(field.type),
            "nullable": field.nullable,
        })

    return result


def load_parquet_sample(
    parquet_path: str,
    sample_size: Optional[int] = None
) -> pd.DataFrame:
    """Load Parquet into pandas, optionally sampling rows."""
    if sample_size:
        pf = pq.ParquetFile(parquet_path)
        # Read first N rows from first row groups
        df = pd.read_parquet(parquet_path, engine="pyarrow")
        if len(df) > sample_size:
            # Stratified sample by language if available
            if "language" in df.columns:
                df = df.groupby("language", group_keys=False).apply(
                    lambda x: x.sample(min(len(x), max(1, sample_size // df["language"].nunique())),
                                       random_state=42)
                )
            else:
                df = df.head(sample_size)
    else:
        df = pd.read_parquet(parquet_path, engine="pyarrow")
    return df


def parse_parquet_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single Parquet row into fields matching our raw schema.
    
    The HuggingFace 'voilaj/swiss-caselaw' Parquet has columns like:
    - id, title, text, date, court, language, etc.
    We need to map these to our canonical schema fields.
    """
    # Handle various possible column names from different Parquet sources
    full_text = (
        row.get("text") or 
        row.get("full_text") or 
        row.get("content") or 
        row.get("decision_text") or 
        ""
    )
    
    decision_id = row.get("id") or row.get("decision_id") or row.get("doc_id") or ""
    if decision_id and not decision_id.startswith("bger_"):
        decision_id = f"bger_{decision_id}"
    
    decision_date = row.get("date") or row.get("decision_date") or row.get("publication_date") or ""
    if len(str(decision_date)) == 10:
        pass  # YYYY-MM-DD
    elif len(str(decision_date)) == 7:
        decision_date = f"{decision_date}-01"
    elif len(str(decision_date)) == 4:
        decision_date = f"{decision_date}-01-01"
    
    language = row.get("language") or row.get("lang") or "de"
    if len(str(language)) > 2:
        lang_map = {"german": "de", "french": "fr", "italian": "it", "deutsch": "de", "französisch": "fr", "italienisch": "it"}
        language = lang_map.get(str(language).lower(), "de")[:2]
    
    court = row.get("court") or row.get("court_id") or "bger"
    if court not in ("bge", "bger", "bvger", "bstger", "bpatger"):
        court = "bger"
    
    return {
        "decision_id": str(decision_id),
        "court": str(court),
        "decision_date": str(decision_date)[:10],
        "language": str(language)[:2],
        "title": row.get("title"),
        "full_text": str(full_text),
        "docket_number": row.get("docket_number") or row.get("citation") or decision_id,
        "legal_area": row.get("legal_area") or row.get("branch"),
        "chamber": row.get("chamber"),
        "branch": row.get("branch"),
        "outcome": row.get("outcome"),
        "regeste": row.get("regeste"),
        "cited_decisions": row.get("cited_decisions"),
        "cited_laws": row.get("cited_laws"),
        "judges": row.get("judges"),
        "source_url": row.get("url") or row.get("source_url"),
        "pdf_url": row.get("pdf_url"),
        "publication_date": row.get("publication_date"),
        "proceeding_type": row.get("proceeding_type"),
        "abstract_de": row.get("abstract_de"),
        "abstract_fr": row.get("abstract_fr"),
        "abstract_it": row.get("abstract_it"),
        "decision_type": row.get("decision_type"),
        "bge_reference": row.get("bge_reference"),
        # Structural fields (may not be in Parquet)
        "sachverhalt": row.get("sachverhalt"),
        "erwaegungen": row.get("erwaegungen"),
        "dispositiv": row.get("dispositiv"),
        "dispositiv_orders": row.get("dispositiv_orders"),
        "preparatory_materials": row.get("preparatory_materials"),
        "outgoing_citations": row.get("outgoing_citations"),
        "incoming_citations": row.get("incoming_citations"),
        "content_hash": hashlib.sha256(str(full_text).encode("utf-8")).hexdigest() if full_text else None,
    }


def parquet_to_canonical(
    parquet_path: str,
    output_path: str,
    config: ParquetIngestConfig,
    schema_path: str = "corpus/schema/decision_schema.json"
) -> Dict[str, Any]:
    """
    End-to-end Parquet ingestion: download, load, normalize, validate.
    Returns metrics dict.
    """
    start_time = time.time()
    
    # Step 1: Download
    print("=" * 60)
    print("STEP 1: Download Parquet")
    print("=" * 60)
    os.makedirs(config.output_dir, exist_ok=True)
    local_path = os.path.join(config.output_dir, "bger.parquet")
    download_parquet(config.parquet_url, local_path, force=config.force_download)
    
    # Step 2: Inspect schema
    print("\n" + "=" * 60)
    print("STEP 2: Inspect Parquet Schema")
    print("=" * 60)
    schema_info = inspect_parquet_schema(local_path)
    print(f"Rows: {schema_info['num_rows']}")
    print(f"Row groups: {schema_info['num_row_groups']}")
    print(f"Columns: {schema_info['num_columns']}")
    print(f"File size: {schema_info['file_size_mb']:.1f} MB")
    print("Schema fields:")
    for f in schema_info["schema_fields"]:
        print(f"  {f['name']}: {f['type']} (nullable={f['nullable']})")
    
    # Step 3: Load sample
    print("\n" + "=" * 60)
    print("STEP 3: Load Parquet Sample")
    print("=" * 60)
    sample_size = config.sample_size
    df = load_parquet_sample(local_path, sample_size)
    print(f"Loaded {len(df)} rows")
    if sample_size:
        print(f"Sample target: {sample_size}")
    print(f"Columns: {list(df.columns)}")
    
    # Show language distribution
    if "language" in df.columns:
        print(f"Language distribution: {df['language'].value_counts().to_dict()}")
    
    # Step 4: Normalize
    print("\n" + "=" * 60)
    print("STEP 4: Normalize to Canonical Schema")
    print("=" * 60)
    normalizer = DecisionNormalizer(schema_path)
    stats = NormalizationStats()
    stats.total_input = len(df)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    normalized_count = 0
    skipped_count = 0
    
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            parsed = parse_parquet_row(row_dict)
            
            # Create a DecisionRaw-like object for the normalizer
            from corpus.acquisition.opencaselaw_client import DecisionRaw
            try:
                raw = DecisionRaw(**{k: v for k, v in parsed.items() 
                                    if k in DecisionRaw.__dataclass_fields__})
            except Exception as e:
                skipped_count += 1
                continue
            
            try:
                canonical = normalizer.normalize(raw, config.source_version)
                if canonical:
                    f.write(json.dumps(canonical, ensure_ascii=False) + "\n")
                    normalized_count += 1
                    
                    # Update stats
                    lang = canonical.get("language", "unknown")
                    stats.by_language[lang] = stats.by_language.get(lang, 0) + 1
                    year = canonical.get("decision_date", "unknown")[:4]
                    stats.by_year[year] = stats.by_year.get(year, 0) + 1
                    court = canonical.get("court", "unknown")
                    stats.by_court[court] = stats.by_court.get(court, 0) + 1
                    branch = canonical.get("branch", "unknown")
                    stats.by_branch[branch] = stats.by_branch.get(branch, 0) + 1
                else:
                    skipped_count += 1
            except Exception as e:
                skipped_count += 1
                continue
    
    stats.total_output = normalized_count
    elapsed = time.time() - start_time
    
    print(f"\nNormalization complete:")
    print(f"  Input: {stats.total_input}")
    print(f"  Output: {normalized_count}")
    print(f"  Skipped (dedup/empty): {skipped_count}")
    print(f"  By language: {stats.by_language}")
    print(f"  By year: {dict(sorted(stats.by_year.items()))}")
    print(f"  By court: {stats.by_court}")
    print(f"  By branch: {stats.by_branch}")
    print(f"  Elapsed: {elapsed:.1f}s")
    
    # Step 5: Validate
    print("\n" + "=" * 60)
    print("STEP 5: Schema Validation")
    print("=" * 60)
    import jsonschema
    with open(schema_path, "r") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)
    
    validation_errors = 0
    with open(output_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            decision = json.loads(line)
            errors = list(validator.iter_errors(decision))
            if errors:
                validation_errors += 1
                if validation_errors <= 3:
                    print(f"  Validation error at line {i}: {errors[0].message[:100]}")
    
    print(f"  Validated: {normalized_count} decisions")
    print(f"  Validation errors: {validation_errors}")
    
    return {
        "parquet_file_size_mb": schema_info["file_size_mb"],
        "parquet_rows": schema_info["num_rows"],
        "parquet_columns": schema_info["num_columns"],
        "sample_size": len(df),
        "normalized": normalized_count,
        "skipped": skipped_count,
        "validation_errors": validation_errors,
        "language_distribution": stats.by_language,
        "year_distribution": dict(sorted(stats.by_year.items())),
        "court_distribution": stats.by_court,
        "branch_distribution": stats.by_branch,
        "elapsed_seconds": round(elapsed, 1),
    }


if __name__ == "__main__":
    config = ParquetIngestConfig(
        sample_size=500,
        force_download=False,
    )
    metrics = parquet_to_canonical(
        parquet_path=None,  # Will be determined by config
        output_path="corpus/normalization/canonical/bger_parquet_sample_500.jsonl",
        config=config,
    )
    print("\n" + "=" * 60)
    print("METRICS")
    print("=" * 60)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
