#!/usr/bin/env python3
"""Build reproducible section-extraction artifacts for the 174k bger corpus.

Pipeline (deterministic, offline after the pinned parquet is present):
  1. Verify the pinned parquet SHA-256 (fails hard on mismatch).
  2. Segment each decision's ``full_text`` into Sachverhalt / Erwaegungen /
     Dispositiv spans with ``corpus.normalization.section_extractor``.
  3. Persist a compact, auditable span table (offsets + methods + char counts)
     so the section text can be *materialised* from the pinned parquet without
     duplicating ~2 GB.
  4. Emit coverage/schema metrics, optionally cross-checked against the
     independently published OpenCaseLaw ``structure/structure.parquet``
     (CC0-1.0) when ``--structure-parquet`` is supplied.

Usage:
    python corpus/acquisition/build_section_artifacts.py \
        --parquet corpus/acquisition/parquet/bger.parquet \
        --out-dir results/corpus \
        [--structure-parquet /path/structure.parquet] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from corpus.normalization.section_extractor import (  # noqa: E402
    extract_structure,
    parse_erwaegungen_paragraphs,
)

PINNED_PARQUET_SHA256 = (
    "74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d"
)
SECTIONS = ("sachverhalt", "erwaegungen", "dispositiv")


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _paragraph_count(structure):
    """Rows the OpenCaseLaw paragraph export holds: numbered non-empty
    paragraphs plus the unnumbered ('0') fallback."""
    if structure.erwaegungen is None:
        return 0
    paras = parse_erwaegungen_paragraphs(structure.erwaegungen.text)
    numbered = {}
    unnumbered = None
    for p in paras:
        if p.get("depth", 0) == 0:
            unnumbered = (p.get("text") or "").strip() or None
            continue
        numbered.pop(p["e_number"], None)
        numbered[p["e_number"]] = p
    return sum(1 for p in numbered.values() if p.get("text")) + (1 if unnumbered else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="corpus/acquisition/parquet/bger.parquet")
    ap.add_argument("--out-dir", default="results/corpus")
    ap.add_argument("--structure-parquet", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--check-sha", action="store_true", default=True)
    ap.add_argument("--no-check-sha", dest="check_sha", action="store_false")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    parquet_path = args.parquet
    if not os.path.exists(parquet_path):
        sys.exit(f"ERROR: pinned parquet not found at {parquet_path}")

    sha = sha256_file(parquet_path) if args.check_sha else "skipped"
    if args.check_sha and sha != PINNED_PARQUET_SHA256:
        sys.exit(f"ERROR: parquet sha256 mismatch\n got {sha}\n exp {PINNED_PARQUET_SHA256}")

    pf = pq.ParquetFile(parquet_path)
    cols = ["decision_id", "language", "full_text"]
    available = set(pf.schema_arrow.names)
    cols = [c for c in cols if c in available]
    table = pf.read(columns=cols).to_pandas()
    if args.limit:
        table = table.iloc[: args.limit]
    n = len(table)

    structure_labels = None
    if args.structure_parquet and os.path.exists(args.structure_parquet):
        st = pq.read_table(
            args.structure_parquet,
            columns=["decision_id", "court", "language",
                     "has_sachverhalt", "has_erwaegungen", "has_dispositiv",
                     "erwaegungen_paragraph_count"],
        ).to_pandas()
        st = st[st.court == "bger"].set_index("decision_id")
        structure_labels = st

    start = time.time()
    rows = []
    metrics = {
        "total": n,
        "unconditional": {s: 0 for s in SECTIONS},
        "by_language": {},
        "methods": {s: Counter() for s in SECTIONS},
        "section_chars": {s: 0 for s in SECTIONS},
        "erwaegungen_paragraph_count_sum": 0,
        "span_order_violations": 0,
        "empty_text": 0,
    }
    check_ids, check_lang, check_has = [], [], []
    check_spans = {s: ([], [], []) for s in SECTIONS}
    check_method = {s: [] for s in SECTIONS}
    check_pcount = []
    agree = {s: {"pos": 0, "tp": 0, "fp": 0, "fn": 0, "tn": 0} for s in SECTIONS}
    pcount_exact = 0
    pcount_compared = 0

    for i, row in enumerate(table.itertuples(index=False)):
        did = row.decision_id
        lang = row.language or "de"
        text = row.full_text or ""
        if not text:
            metrics["empty_text"] += 1
        st = extract_structure(text, lang, did)
        langm = metrics["by_language"].setdefault(
            lang, {s: 0 for s in SECTIONS} | {"n": 0})
        langm["n"] += 1
        spans = {}
        for s in SECTIONS:
            sec = getattr(st, s)
            present = sec is not None and bool(sec.text)
            if present:
                metrics["unconditional"][s] += 1
                langm[s] += 1
                metrics["methods"][s][sec.method] += 1
                metrics["section_chars"][s] += len(sec.text)
                spans[s] = (sec.start, sec.end, sec.method, len(sec.text))
            else:
                spans[s] = (-1, -1, None, 0)
        # span ordering sanity: sav <= erw <= disp when present
        se = [spans[s] for s in SECTIONS if spans[s][0] >= 0]
        ends = [sp[1] for sp in se]
        starts = [sp[0] for sp in se]
        if starts != sorted(starts) or ends != sorted(ends):
            metrics["span_order_violations"] += 1

        pc = _paragraph_count(st)
        metrics["erwaegungen_paragraph_count_sum"] += pc

        check_ids.append(did)
        check_lang.append(lang)
        check_has.append([1 if spans[s][0] >= 0 else 0 for s in SECTIONS])
        for s in SECTIONS:
            check_spans[s][0].append(spans[s][0])
            check_spans[s][1].append(spans[s][1])
            check_spans[s][2].append(spans[s][3])
            check_method[s].append(spans[s][2])
        check_pcount.append(pc)

        if structure_labels is not None and did in structure_labels.index:
            lab = structure_labels.loc[did]
            for s in SECTIONS:
                present = spans[s][0] >= 0
                truth = bool(lab[f"has_{s}"])
                key = "tp" if (present and truth) else "fp" if (present and not truth) else "fn" if (truth and not present) else "tn"
                agree[s][key] += 1
                agree[s]["pos"] += truth
            exp = int(lab["erwaegungen_paragraph_count"])
            pcount_compared += 1
            if exp == pc:
                pcount_exact += 1

        if (i + 1) % 25000 == 0:
            print(f"  {i+1:,}/{n:,} extracted grouped={metrics['unconditional']}", flush=True)

    elapsed = time.time() - start

    # ---- persist span table (compact, auditable) ----
    span_table = pa.table({
        "decision_id": pa.array(check_ids, type=pa.string()),
        "language": pa.array(check_lang, type=pa.string()),
        "has_sachverhalt": pa.array([h[0] for h in check_has], type=pa.int8()),
        "has_erwaegungen": pa.array([h[1] for h in check_has], type=pa.int8()),
        "has_dispositiv": pa.array([h[2] for h in check_has], type=pa.int8()),
        **{f"{s}_start": pa.array(check_spans[s][0], type=pa.int32()) for s in SECTIONS},
        **{f"{s}_end": pa.array(check_spans[s][1], type=pa.int32()) for s in SECTIONS},
        **{f"{s}_chars": pa.array(check_spans[s][2], type=pa.int32()) for s in SECTIONS},
        **{f"{s}_method": pa.array(check_method[s], type=pa.string()) for s in SECTIONS},
        "erwaegungen_paragraph_count": pa.array(check_pcount, type=pa.int32()),
    })
    span_path = os.path.join(args.out_dir, "section_spans_174k.parquet")
    pq.write_table(span_table, span_path, compression="zstd")

    # ---- metrics ----
    out_metrics = {
        "artifact": "section_spans_174k",
        "run": "corpus_v36_section_extraction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "direction_version": 36,
        "source_parquet": args.parquet,
        "source_parquet_sha256": sha,
        "source_parquet_sha256_expected": PINNED_PARQUET_SHA256,
        "extractor": "corpus/normalization/section_extractor.py "
                     "(adaptation of OpenCaseLaw extract_decision_structure.py, CC0-1.0)",
        "total_decisions": n,
        "elapsed_seconds": round(elapsed, 2),
        "decisions_per_second": round(n / elapsed, 1) if elapsed else 0,
        "unconditional_coverage": {
            s: round(metrics["unconditional"][s] / n, 4) for s in SECTIONS
        },
        "coverage_by_language": {
            lang: {**{s: round(d[s] / d["n"], 4) for s in SECTIONS}, "n": d["n"]}
            for lang, d in sorted(metrics["by_language"].items())
        },
        "method_distribution": {
            s: dict(metrics["methods"][s].most_common()) for s in SECTIONS
        },
        "section_total_chars": metrics["section_chars"],
        "empty_text_decisions": metrics["empty_text"],
        "span_order_violations": metrics["span_order_violations"],
        "erwaegungen_paragraph_count_sum": metrics["erwaegungen_paragraph_count_sum"],
    }
    if structure_labels is not None:
        out_metrics["validation_vs_structure_parquet"] = {}
        for s in SECTIONS:
            a = agree[s]
            cond = a["pos"]
            out_metrics["validation_vs_structure_parquet"][s] = {
                "labeled_present": cond,
                "coverage": round(a["tp"] / cond, 6) if cond else None,
                "precision": round(a["tp"] / (a["tp"] + a["fp"]), 6) if (a["tp"] + a["fp"]) else None,
                "tp": a["tp"], "fp": a["fp"], "fn": a["fn"], "tn": a["tn"],
            }
        out_metrics["validation_vs_structure_parquet"]["erwaegungen_paragraph_count_exact_match"] = {
            "compared": pcount_compared,
            "exact": pcount_exact,
            "rate": round(pcount_exact / pcount_compared, 6) if pcount_compared else None,
        }
    out_metrics["artifacts"] = {
        "section_spans": span_path,
        "section_spans_sha256": sha256_file(span_path),
        "section_spans_bytes": os.path.getsize(span_path),
    }
    mpath = os.path.join(args.out_dir, "section_extraction_metrics_v36.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(out_metrics, f, indent=2, ensure_ascii=False)

    print(json.dumps({k: out_metrics[k] for k in
                      ["total_decisions", "elapsed_seconds", "unconditional_coverage",
                       "validation_vs_structure_parquet"] if k in out_metrics}, indent=2))
    print("wrote", span_path, mpath)


if __name__ == "__main__":
    main()
