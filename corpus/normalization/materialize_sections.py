#!/usr/bin/env python3
"""Materialise section text from the compact span artifact.

``results/corpus/section_spans_174k.parquet`` stores, for every decision, the
character offsets of Sachverhalt / Erwaegungen / Dispositiv (plus the extraction
method and char counts) rather than ~2 GB of duplicated section text.  This
module turns those spans back into text deterministically from the pinned
``bger.parquet`` source, so the full section corpus is reproducible without
bloating git.

Semantics (matching ``corpus.normalization.section_extractor``):
    section_text = full_text[start:end].strip()

Usage:
    python corpus/normalization/materialize_sections.py --decision bger_4P.253_1999
    python corpus/normalization/materialize_sections.py --out results/corpus/section_sample_200.jsonl --sample 200
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import os

import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

SECTIONS = ("sachverhalt", "erwaegungen", "dispositiv")
DEFAULT_SPANS = os.path.join(PROJECT_ROOT, "results", "corpus", "section_spans_174k.parquet")
DEFAULT_PARQUET = os.path.join(PROJECT_ROOT, "corpus", "acquisition", "parquet", "bger.parquet")


def load_spans(path=DEFAULT_SPANS):
    return pq.read_table(path).to_pandas().set_index("decision_id", drop=False)


def load_texts(path=DEFAULT_PARQUET, decision_ids=None):
    cols = ["decision_id", "full_text", "decision_date", "language", "court"]
    table = pq.read_table(path, columns=cols).to_pandas()
    if decision_ids is not None:
        table = table[table.decision_id.isin(set(decision_ids))]
    return table.set_index("decision_id", drop=False)


def materialize_row(row, full_text):
    """Return {section: text-or-None} for one span-table row."""
    out = {}
    for s in SECTIONS:
        if int(row.get(f"has_{s}", 0)) != 1:
            out[s] = None
            continue
        start = int(row[f"{s}_start"])
        end = int(row[f"{s}_end"])
        out[s] = (full_text[start:end] or "").strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spans", default=DEFAULT_SPANS)
    ap.add_argument("--parquet", default=DEFAULT_PARQUET)
    ap.add_argument("--decision", help="materialise a single decision id")
    ap.add_argument("--sample", type=int, default=0, help="materialise N random decisions to --out")
    ap.add_argument("--seed", type=int, default=36)
    ap.add_argument("--out", help="output .jsonl for --sample")
    args = ap.parse_args()

    spans = load_spans(args.spans)

    if args.decision:
        if args.decision not in spans.index:
            print(json.dumps({"error": "unknown decision", "id": args.decision}))
            return 1
        row = spans.loc[args.decision]
        texts = load_texts(args.parquet, [args.decision])
        ft = texts.loc[args.decision, "full_text"]
        result = materialize_row(row, ft)
        result["decision_id"] = args.decision
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.sample and args.out:
        rng = random.Random(args.seed)
        ids = sorted(spans.index.tolist())
        picked = rng.sample(ids, min(args.sample, len(ids)))
        texts = load_texts(args.parquet, picked)
        with open(args.out, "w", encoding="utf-8") as fh:
            for did in picked:
                row = spans.loc[did]
                ft = texts.loc[did, "full_text"]
                rec = materialize_row(row, ft)
                rec["decision_id"] = did
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"wrote {len(picked)} decisions to {args.out}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
