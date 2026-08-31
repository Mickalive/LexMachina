"""
Scaled Parquet ingestion pipeline: chunked processing with checkpoint/resume
for full BGer coverage (2000-2024, ~192k decisions).
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

import pyarrow.parquet as pq

from corpus.acquisition.opencaselaw_client import DecisionRaw
from corpus.normalization.normalize import DecisionNormalizer


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


def _clean_nan(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert NaN/NaT values from pandas to None for schema validation."""
    import math
    cleaned = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def parse_parquet_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single Parquet row into fields matching our raw schema."""
    # Clean NaN values from pandas
    row = _clean_nan(row)

    full_text = (
        row.get("text")
        or row.get("full_text")
        or row.get("content")
        or row.get("decision_text")
        or ""
    )

    decision_id = row.get("id") or row.get("decision_id") or row.get("doc_id") or ""
    court = row.get("court") or row.get("court_id") or "bger"
    if court not in ("bge", "bger", "bvger", "bstger", "bpatger"):
        court = "bger"

    # Normalize decision_id: ensure proper prefix, replace spaces with underscores
    if decision_id:
        if court == "bge" and not decision_id.startswith("bge_"):
            decision_id = f"bge_{decision_id}"
        elif court != "bge" and not decision_id.startswith("bger_"):
            decision_id = f"bger_{decision_id}"
        # Replace spaces with underscores for schema compliance
        decision_id = decision_id.replace(" ", "_")

    decision_date = row.get("date") or row.get("decision_date") or row.get("publication_date") or ""
    decision_date = str(decision_date)
    if len(decision_date) == 10:
        pass
    elif len(decision_date) == 7:
        decision_date = f"{decision_date}-01"
    elif len(decision_date) == 4:
        decision_date = f"{decision_date}-01-01"

    language = row.get("language") or row.get("lang") or "de"
    if len(str(language)) > 2:
        lang_map = {
            "german": "de", "french": "fr", "italian": "it",
            "deutsch": "de", "französisch": "fr", "italienisch": "it",
        }
        language = lang_map.get(str(language).lower(), "de")[:2]

    # Handle BGE docket_number: prefix with "BGE " for citation matching
    docket_number = row.get("docket_number") or row.get("citation") or decision_id
    if court == "bge" and docket_number and not docket_number.startswith("BGE "):
        # BGE docket numbers are like "151 III 481" -> "BGE 151 III 481"
        docket_number = f"BGE {docket_number}"

    # For BGE court, the docket_number IS the bge_reference
    bge_reference = row.get("bge_reference")
    if court == "bge" and not bge_reference and docket_number and docket_number.startswith("BGE "):
        bge_reference = docket_number

    return {
        "decision_id": str(decision_id),
        "court": str(court),
        "decision_date": decision_date[:10],
        "language": str(language)[:2],
        "title": row.get("title"),
        "full_text": str(full_text),
        "docket_number": docket_number,
        "legal_area": row.get("legal_area") or row.get("branch"),
        "chamber": row.get("chamber"),
        "branch": row.get("branch"),
        "outcome": row.get("outcome"),
        "regeste": row.get("regeste"),
        "cited_decisions": row.get("cited_decisions"),
        "citation_string_de": row.get("citation_string_de") or bge_reference,
        "canonical_url": row.get("url") or row.get("source_url") or f"{court}://{decision_id}",
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
        "bge_reference": bge_reference,
        "sachverhalt": row.get("sachverhalt"),
        "erwaegungen": row.get("erwaegungen"),
        "dispositiv": row.get("dispositiv"),
        "dispositiv_orders": row.get("dispositiv_orders"),
        "preparatory_materials": row.get("preparatory_materials"),
        "outgoing_citations": row.get("outgoing_citations"),
        "incoming_citations": row.get("incoming_citations"),
        "content_hash": (
            hashlib.sha256(str(full_text).encode("utf-8")).hexdigest()
            if full_text
            else None
        ),
    }


def _load_checkpoint(path: str) -> Dict[str, Any]:
    """Load checkpoint from disk. Returns empty dict if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_checkpoint(path: str, data: Dict[str, Any]) -> None:
    """Atomically write checkpoint (write-then-rename)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _fmt_time(seconds: float) -> str:
    """Human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def _determine_row_groups(
    parquet_path: str,
    full_corpus: bool,
    sample_size: Optional[int],
    chunk_size: int,
) -> List[int]:
    """Return list of row-group indices to process, respecting sample_size."""
    pf = pq.ParquetFile(parquet_path)
    total_rgs = pf.metadata.num_row_groups

    if full_corpus or sample_size is None:
        return list(range(total_rgs))

    # Accumulate row counts until we hit sample_size
    selected = []
    accumulated = 0
    for i in range(total_rgs):
        rg_rows = pf.metadata.row_group(i).num_rows
        if accumulated >= sample_size:
            break
        selected.append(i)
        accumulated += rg_rows
    return selected


def parquet_to_canonical_scaled(
    output_dir: str = "corpus/normalization/canonical",
    checkpoint_path: str = "corpus/acquisition/parquet_checkpoint.json",
    full_corpus: bool = False,
    sample_size: Optional[int] = 500,
    force_download: bool = False,
    source_version: str = "opencaselaw_parquet_2026-08-31",
    chunk_size: int = 5000,
    parquet_url: str = "https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet",
    schema_path: str = "corpus/schema/decision_schema.json",
    clean_output: bool = False,
) -> Dict[str, Any]:
    """
    Scaled Parquet ingestion with chunked processing, checkpoint/resume,
    year-split output, and comprehensive metrics.
    """
    start_time = time.time()

    # ── 1. Download ──────────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Download / locate Parquet")
    print("=" * 60)
    parquet_dir = "corpus/acquisition/parquet"
    local_path = os.path.join(parquet_dir, "bger.parquet")
    download_parquet(parquet_url, local_path, force=force_download)

    # ── 2. Schema inspection ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Inspect Parquet schema")
    print("=" * 60)
    pf = pq.ParquetFile(local_path)
    total_rows = pf.metadata.num_rows
    num_rgs = pf.metadata.num_row_groups
    print(f"  Total rows:      {total_rows}")
    print(f"  Row groups:      {num_rgs}")
    print(f"  File size:       {os.path.getsize(local_path) / 1024 / 1024:.1f} MB")

    # ── 3. Normalizer & validator ────────────────────────────────────
    normalizer = DecisionNormalizer(schema_path)

    import jsonschema
    with open(schema_path, "r") as sf:
        raw_schema = json.load(sf)
    validator = jsonschema.Draft7Validator(raw_schema)

    # ── 4. Checkpoint load ───────────────────────────────────────────
    checkpoint = _load_checkpoint(checkpoint_path)
    completed_chunks: Set[int] = set(checkpoint.get("completed_chunks", []))
    # Global dedup set across chunks
    global_seen_hashes: Set[str] = set(checkpoint.get("seen_content_hashes", []))

    if completed_chunks:
        print(f"\n  Resuming from checkpoint: {len(completed_chunks)} chunks already done")

    # ── 5. Determine row groups to process ───────────────────────────
    row_groups = _determine_row_groups(local_path, full_corpus, sample_size, chunk_size)
    # Partition row groups into logical chunks of roughly chunk_size rows
    chunks: List[List[int]] = []
    current_chunk: List[int] = []
    current_count = 0
    for rg_idx in row_groups:
        rg_rows = pf.metadata.row_group(rg_idx).num_rows
        if current_count + rg_rows > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_count = 0
        current_chunk.append(rg_idx)
        current_count += rg_rows
    if current_chunk:
        chunks.append(current_chunk)

    effective_total = sum(
        pf.metadata.row_group(rg).num_rows for rg in row_groups
    )
    print(f"\n  Row groups to process: {len(row_groups)}")
    print(f"  Chunks: {len(chunks)} (~{chunk_size} rows each)")
    print(f"  Effective total rows: {effective_total:,}")

    # ── 6. Prepare year-based output handles ─────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    year_handles: Dict[str, Any] = {}

    if clean_output:
        # Remove pre-existing year-split files so fresh runs produce only the
        # records ingested in this run. Without this, `_get_year_handle` opens
        # in append mode and silently retains stale records from prior runs,
        # inflating validation/written_to_disk counts (e.g. the historic +250
        # from 50 retained records in each of 2020-2024). See REVISE audit.
        import glob as _glob
        for stale in _glob.glob(os.path.join(output_dir, "bger_[0-9][0-9][0-9][0-9].jsonl")):
            os.remove(stale)
        print(f"[clean_output] Removed pre-existing year-split files in {output_dir}")

    def _get_year_handle(year: str) -> Any:
        if year not in year_handles:
            path = os.path.join(output_dir, f"bger_{year}.jsonl")
            mode = "a" if os.path.exists(path) else "w"
            year_handles[year] = open(path, mode, encoding="utf-8")
        return year_handles[year]

    # ── 7. Processing loop ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Process chunks")
    print("=" * 60)

    # Aggregate counters
    total_normalized = checkpoint.get("total_normalized", 0)
    total_skipped = checkpoint.get("total_skipped", 0)
    total_errors = checkpoint.get("total_errors", 0)
    total_input_rows = checkpoint.get("total_input_rows", 0)
    by_year: Dict[str, int] = checkpoint.get("by_year", {})
    by_language: Dict[str, int] = checkpoint.get("by_language", {})
    by_branch: Dict[str, int] = checkpoint.get("by_branch", {})
    validation_errors_total = checkpoint.get("validation_errors", 0)
    # Count all errors in row-level processing (not just validation)
    row_error_count = 0
    # Carry forward previously-seen errors from checkpoint
    row_error_count = checkpoint.get("row_processing_errors", 0)

    processed_since_last_report = 0
    last_report_time = time.time()

    for chunk_idx, rg_indices in enumerate(chunks):
        if chunk_idx in completed_chunks:
            continue

        # Read row groups via pyarrow ParquetFile API (memory-efficient)
        table = pq.read_table(local_path, filters=None)
        # Read only specific row groups for this chunk
        tables = [pf.read_row_group(i) for i in rg_indices]
        table = pq.concat_tables(tables) if len(tables) > 1 else tables[0]
        chunk_df = table.to_pandas()
        chunk_rows = len(chunk_df)
        total_input_rows += chunk_rows

        chunk_normalized = 0
        chunk_skipped = 0
        chunk_errors = 0
        chunk_valid_err = 0

        for _, row_series in chunk_df.iterrows():
            row_dict = row_series.to_dict()
            parsed = parse_parquet_row(row_dict)

            # Cross-chunk duplicate detection
            ch = parsed.get("content_hash")
            if ch and ch in global_seen_hashes:
                chunk_skipped += 1
                total_skipped += 1
                processed_since_last_report += 1
                continue

            # Build DecisionRaw
            try:
                raw = DecisionRaw(
                    **{
                        k: v
                        for k, v in parsed.items()
                        if k in DecisionRaw.__dataclass_fields__
                    }
                )
            except Exception:
                chunk_errors += 1
                row_error_count += 1
                processed_since_last_report += 1
                continue

            # Normalize
            try:
                canonical = normalizer.normalize(raw, source_version)
            except Exception:
                chunk_errors += 1
                row_error_count += 1
                processed_since_last_report += 1
                continue

            if canonical is None:
                chunk_skipped += 1
                total_skipped += 1
                processed_since_last_report += 1
                continue

            # Schema validation (count errors, don't fail)
            val_errors = list(validator.iter_errors(canonical))
            if val_errors:
                chunk_valid_err += 1
                validation_errors_total += 1

            # Register content hash in global dedup set
            if ch:
                global_seen_hashes.add(ch)

            # Write to year-split file
            year = canonical.get("decision_date", "unknown")[:4]
            fh = _get_year_handle(year)
            fh.write(json.dumps(canonical, ensure_ascii=False) + "\n")

            # Update counters
            chunk_normalized += 1
            total_normalized += 1
            by_year[year] = by_year.get(year, 0) + 1
            lang = canonical.get("language", "unknown")
            by_language[lang] = by_language.get(lang, 0) + 1
            br = canonical.get("branch", "unknown")
            by_branch[br] = by_branch.get(br, 0) + 1

            processed_since_last_report += 1

        # ── Progress report every 1000 decisions ────────────────────
        if processed_since_last_report >= 1000:
            elapsed_so_far = time.time() - start_time
            rate = total_normalized / elapsed_so_far if elapsed_so_far > 0 else 0
            remaining_rows = effective_total - total_input_rows
            est_remaining = remaining_rows / rate if rate > 0 else 0
            print(
                f"  [{total_normalized:,}/{effective_total:,}] "
                f"{_fmt_time(elapsed_so_far)} elapsed | "
                f"{rate:.1f} dec/s | "
                f"~{_fmt_time(est_remaining)} remaining"
            )
            processed_since_last_report = 0

        # ── Write checkpoint after each chunk ────────────────────────
        completed_chunks.add(chunk_idx)
        ckpt_data = {
            "completed_chunks": sorted(completed_chunks),
            "total_normalized": total_normalized,
            "total_skipped": total_skipped,
            "total_errors": total_errors + chunk_errors,
            "total_input_rows": total_input_rows,
            "row_processing_errors": row_error_count,
            "by_year": by_year,
            "by_language": by_language,
            "by_branch": by_branch,
            "validation_errors": validation_errors_total,
            "seen_content_hashes": list(global_seen_hashes),
            "last_chunk_completed": chunk_idx,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        _write_checkpoint(checkpoint_path, ckpt_data)

        total_errors += chunk_errors

    # ── Close year-split file handles ────────────────────────────────
    for fh in year_handles.values():
        fh.close()

    # ── 8. Final metrics ─────────────────────────────────────────────
    elapsed = time.time() - start_time
    error_rate = row_error_count / total_input_rows if total_input_rows > 0 else 0.0

    # Count written lines across year-split files
    total_written = 0
    for y in by_year:
        fp = os.path.join(output_dir, f"bger_{y}.jsonl")
        if os.path.exists(fp):
            with open(fp, "r") as f:
                total_written += sum(1 for _ in f)

    metrics: Dict[str, Any] = {
        "total_rows": total_input_rows,
        "normalized": total_normalized,
        "skipped": total_skipped,
        "by_year": dict(sorted(by_year.items())),
        "by_language": dict(sorted(by_language.items())),
        "by_branch": dict(sorted(by_branch.items())),
        "validation_errors": validation_errors_total,
        "row_processing_errors": row_error_count,
        "error_rate": round(error_rate, 6),
        "elapsed_seconds": round(elapsed, 1),
        "decisions_per_second": round(total_normalized / elapsed, 2) if elapsed > 0 else 0,
        "written_to_disk": total_written,
        "chunks_processed": len(completed_chunks),
    }

    # ── 9. Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Total rows read:    {total_input_rows:,}")
    print(f"  Normalized:         {total_normalized:,}")
    print(f"  Skipped (dedup):    {total_skipped:,}")
    print(f"  Validation errors:  {validation_errors_total:,}")
    print(f"  Row errors:         {row_error_count:,} ({error_rate:.2%})")
    print(f"  By year:            {dict(sorted(by_year.items()))}")
    print(f"  By language:        {dict(sorted(by_language.items()))}")
    print(f"  By branch:          {dict(sorted(by_branch.items()))}")
    print(f"  Rate:               {metrics['decisions_per_second']:.1f} dec/s")
    print(f"  Total time:         {_fmt_time(elapsed)}")
    print(f"  Output dir:         {output_dir}/")
    print(f"  Checkpoint:         {checkpoint_path}")

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scaled Parquet ingestion for LexMachina corpus"
    )
    parser.add_argument(
        "--full", action="store_true", help="Process full corpus (~192k decisions)"
    )
    parser.add_argument(
        "--sample", type=int, default=500, help="Sample size (ignored if --full)"
    )
    parser.add_argument(
        "--output-dir",
        default="corpus/normalization/canonical",
        help="Output directory for year-split JSONL files",
    )
    parser.add_argument(
        "--checkpoint",
        default="corpus/acquisition/parquet_checkpoint.json",
        help="Checkpoint file path",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=5000, help="Rows per chunk"
    )
    parser.add_argument(
        "--clean-output", action="store_true",
        help="Remove pre-existing year-split files before a fresh full run "
             "(prevents append-mode retention of stale records and count inflation)"
    )
    args = parser.parse_args()

    mode = "FULL CORPUS" if args.full else f"SAMPLE ({args.sample} decisions)"
    print(f"Mode: {mode}")

    metrics = parquet_to_canonical_scaled(
        output_dir=args.output_dir,
        checkpoint_path=args.checkpoint,
        full_corpus=args.full,
        sample_size=None if args.full else args.sample,
        chunk_size=args.chunk_size,
        clean_output=args.clean_output,
    )

    # Persist final metrics
    metrics_path = os.path.join(args.output_dir, "ingestion_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\nMetrics written to {metrics_path}")
