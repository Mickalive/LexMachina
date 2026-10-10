#!/usr/bin/env python3
"""Publish deterministic 2024-2026 corpus artifacts (direction v36, corpus lane).

The pinned ``bger.parquet`` (opencaselaw_parquet_2026-08-31) and the canonical
``bger_YYYY.jsonl`` corpus are gitignored (multi-GB).  To make the 2024-2026
slice *auditable in git* without duplicating ~140 MB of text, this script
publishes:

  * ``results/corpus/bger_2024_2026_index.parquet``
      per-decision metadata for 2024-2026 (no full text): id, court, language,
      decision_date, docket, text_length, sha256(full_text).
  * ``results/corpus/bger_2024_2026_sample_100.jsonl``
      a deterministic stratified sample (year x language) with full records,
      so the text is inspectable inside git.
  * ``results/corpus/parquet_2024_2026_manifest_v36.json``
      counts per year/language, source sha, artifact sha256s, and the
      regeneration command.  Full section text for these 15,536 decisions is
      materialised from the pinned parquet via
      ``corpus/normalization/materialize_sections.py``.

The embeddings stage (dense vectors) is owned by the legal-distance lane; the
corpus lane provides the deterministic *input* parquet/index here and records
its provenance.

Usage:
    python corpus/acquisition/build_2024_2026_artifacts.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

PINNED_PARQUET_SHA256 = (
    "74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d"
)
YEARS = ("2024", "2025", "2026")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="corpus/acquisition/parquet/bger.parquet")
    ap.add_argument("--out-dir", default="results/corpus")
    ap.add_argument("--sample-size", type=int, default=100)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    have = sha256_file(args.parquet)
    assert have == PINNED_PARQUET_SHA256, f"pinned parquet sha mismatch: {have}"

    cols = [
        "decision_id", "court", "language", "decision_date",
        "docket_number", "full_text", "text_length",
    ]
    df = pq.read_table(args.parquet, columns=cols).to_pandas()
    year = df.decision_date.astype(str).str[:4]
    sub = df[year.isin(YEARS)].copy()
    sub["year"] = year[year.isin(YEARS)]

    sub["content_sha256"] = [
        sha256_bytes(("" if t is None else t).encode("utf-8")) for t in sub.full_text
    ]
    index = sub[
        ["decision_id", "year", "court", "language", "decision_date",
         "docket_number", "text_length", "content_sha256"]
    ].sort_values("decision_id").reset_index(drop=True)
    index_path = os.path.join(args.out_dir, "bger_2024_2026_index.parquet")
    pq.write_table(pa.Table.from_pandas(index), index_path)

    # deterministic stratified sample (round-robin over year x language)
    groups = {}
    for _, r in sub.sort_values("decision_id").iterrows():
        groups.setdefault((r["year"], r["language"]), []).append(dict(r))
    order = sorted(groups)
    picked, i = [], 0
    while len(picked) < args.sample_size and any(groups[k] for k in order):
        key = order[i % len(order)]
        if groups[key]:
            picked.append(groups[key].pop(0))
        i += 1
    sample_path = os.path.join(args.out_dir, "bger_2024_2026_sample_100.jsonl")
    with open(sample_path, "w", encoding="utf-8") as fh:
        for r in picked:
            tl = r["text_length"]
            fh.write(json.dumps({
                "decision_id": r["decision_id"],
                "court": r["court"],
                "language": r["language"],
                "decision_date": r["decision_date"],
                "docket_number": r["docket_number"],
                "text_length": int(tl) if tl == tl else None,
                "content_sha256": r["content_sha256"],
                "full_text": r["full_text"],
            }, ensure_ascii=False, default=str) + "\n")

    per_year = {y: int((sub.year == y).sum()) for y in YEARS}
    per_lang = {k: int(v) for k, v in sub.language.value_counts().items()}
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "direction_version": 36,
        "source_parquet": args.parquet,
        "source_parquet_sha256": have,
        "total_2024_2026": int(len(sub)),
        "per_year": per_year,
        "per_language": per_lang,
        "index_rows": int(len(index)),
        "index_sha256": sha256_file(index_path),
        "sample_rows": len(picked),
        "sample_sha256": sha256_file(sample_path),
        "regeneration": {
            "full_corpus": "python corpus/acquisition/reproduce_full_corpus.py",
            "sections": "python corpus/acquisition/build_section_artifacts.py --structure-parquet <structure.parquet>",
            "materialize": "python corpus/normalization/materialize_sections.py --sample 200 --out results/corpus/section_sample_200.jsonl",
        },
        "embeddings": {
            "owner": "legal-distance lane",
            "status": "input published; dense vectors not produced by corpus lane",
            "existing_checkpoints": "2000-2023 present in accepted legal-distance results",
            "missing": ["2024", "2025", "2026"],
        },
    }
    with open(os.path.join(args.out_dir, "parquet_2024_2026_manifest_v36.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
