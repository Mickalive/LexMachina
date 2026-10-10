#!/usr/bin/env python3
"""Produce deterministic dense embeddings for 2024-2026 (corpus lane, v36).

Closes the "2024-2026 dense-input gap" recorded in direction v36 by embedding
the regenerated canonical ``bger_2024/2025/2026.jsonl`` records with the same
model/dim as the accepted 2000-2023 checkpoints
(``sentence-transformers/paraphrase-multilingual-mpnet-base-v2``, 768-dim,
float32, un-normalised).

Outputs (per year) mirror the accepted checkpoint layout:
  embeddings_YYYY.npy   float32 [n, 768]
  metadata_YYYY.json    [{decision_id, language, branch, chamber, legal_area, year}]
plus a manifest with shapes + sha256 so the run is verifiable.

Requires: sentence-transformers + torch (network for first model download).

Usage:
    python corpus/acquisition/build_dense_2024_2026.py \
        --out-dir results/corpus/dense_2024_2026 [--years 2024 2025 2026] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
N_DIMS = 768


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_year(path, limit=None):
    ids, texts, meta = [], [], []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            ids.append(r["decision_id"])
            texts.append(r.get("full_text") or "")
            meta.append({
                "decision_id": r["decision_id"],
                "language": r.get("language"),
                "branch": r.get("branch"),
                "chamber": r.get("chamber"),
                "legal_area": r.get("legal_area"),
                "year": (str(r.get("decision_date")) or "")[:4],
            })
            if limit and len(ids) >= limit:
                break
    return ids, texts, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-dir", default="corpus/normalization/canonical")
    ap.add_argument("--out-dir", default="results/corpus/dense_2024_2026")
    ap.add_argument("--years", nargs="+", default=["2024", "2025", "2026"])
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, device="cpu")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "dim": N_DIMS,
        "normalized": False,
        "years": {},
    }
    for year in args.years:
        path = os.path.join(args.canonical_dir, f"bger_{year}.jsonl")
        if not os.path.exists(path):
            manifest["years"][year] = {"status": "missing_source"}
            continue
        ids, texts, meta = load_year(path, args.limit or None)
        t0 = time.time()
        emb = model.encode(
            texts, batch_size=args.batch_size, show_progress_bar=True,
            convert_to_numpy=True, normalize_embeddings=False,
        ).astype("float32")
        npy = os.path.join(args.out_dir, f"embeddings_{year}.npy")
        npy_meta = os.path.join(args.out_dir, f"metadata_{year}.json")
        np.save(npy, emb)
        with open(npy_meta, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        manifest["years"][year] = {
            "n": len(ids),
            "shape": list(emb.shape),
            "elapsed_seconds": round(time.time() - t0, 2),
            "embeddings_sha256": sha256_file(npy),
            "metadata_sha256": sha256_file(npy_meta),
        }
        print(f"{year}: {emb.shape} in {time.time()-t0:.1f}s")
    with open(os.path.join(args.out_dir, "manifest_dense_2024_2026.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
