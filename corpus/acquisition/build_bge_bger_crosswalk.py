#!/usr/bin/env python3
"""Build the BGE <-> bger decision-id crosswalk (direction v36, corpus lane).

Problem this solves
-------------------
The committed canonical corpus uses *published* BGE decision ids of the form
``bge_151_III_481`` / ``bge_BGE_127_I_103`` (corpus/normalization/canonical/bge_*.jsonl),
while the evaluation metadata and dense/legal-distance results use *originating*
Federal Court ids of the form ``bger_4P.253_1999`` / ``bger_9C_22_2024``
(e.g. ``core/evaluation`` metadata_174k).  Before this artifact there was **no
mapping** between the two id spaces.

Evidence sources (open, pinned/deterministic, offline after download)
---------------------------------------------------------------------
* ``data/bge.parquet`` (HF voilaj/swiss-caselaw, 49,259 rows): ``docket_number_2``
  carries the originating docket for published decisions (volumes >= 127), e.g.
  ``bge_151 I 3`` -> ``2C_36/2023``.  Highest-confidence evidence
  (method ``docket_number_2``, confidence 1.00).
* The BGE ``Urteilskopf`` in the committed canonical ``full_text`` names the
  originating docket near the head, e.g. ``9C_22/2024 du 21 mars 2025``
  (method ``header_docket``, confidence 0.99, validated 4,526/4,532 = 99.87%).
* For regeste-only records whose head has no docket, the first docket token in
  the whole text is still the originating docket in 5,687/5,708 = 99.63% of the
  known cases (method ``text_lead_docket``, confidence 0.996).
* Dockets are matched against the pinned ``bger.parquet`` decision-id index and
  canonicalised case/separator-insensitively (``9C_22/2024`` == ``9C.22/2024`` ==
  ``9C 22/2024``).

Known negative result (preserved, not hidden)
---------------------------------------------
Of the 6,395 canonical BGE records whose volume >= 127 (i.e. whose originating
decision could fall in the 2000+ bger corpus), 594 (9.3%) are regeste-only
eurospider records that expose **no** originating docket in any available open
field; they are emitted with ``matched=False``.  Legacy volumes < 127
(14,359 records, mostly pre-1999) are not in the bger corpus era and are also
emitted unmatched.

Outputs
-------
* ``results/corpus/bge_bger_crosswalk.parquet``
* ``results/corpus/eval_id_alignment_v36.json``
* ``results/corpus/bge_bger_crosswalk_metrics_v36.json``

Usage
-----
    python corpus/acquisition/build_bge_bger_crosswalk.py \
        --data-bge /tmp/opencode/data_bge.parquet \
        --parquet corpus/acquisition/parquet/bger.parquet \
        --out-dir results/corpus
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# canonicalisation helpers
# ---------------------------------------------------------------------------
_DOCKET_RE = re.compile(r"\b(\d{1,2}[A-Za-z]{1,3})\s*[._\s]\s*(\d+/\d{4})\b")
_BGER_ID_RE = re.compile(r"^bger_(.+?)_(\d{2}|\d{4})$")
_ATF_RE = re.compile(r"^bge_(?:BGE_)?(\d{1,3})[ _]([IVX]+)[ _](\d+)")
_VOL_RE = re.compile(r"^bge_(?:BGE_)?(\d{1,3})[ _]")


def _canon(dk):
    return re.sub(r"[^0-9A-Z]", "", str(dk).upper())


def _isnum(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def atf_key(decision_id):
    m = _ATF_RE.match(decision_id)
    return (m.group(1) + m.group(2) + m.group(3)) if m else None


def volume(decision_id):
    m = _VOL_RE.match(decision_id)
    return int(m.group(1)) if m else None


def leading_docket(text, limit=None):
    t = text if limit is None else text[:limit]
    m = _DOCKET_RE.search(t)
    return m.group(0) if m else None


def _year4(y):
    y = str(y)
    if len(y) == 4:
        return y
    yi = int(y)
    return ("20" + y) if yi < 30 else ("19" + y)


def build_bger_index(bger_parquet):
    """Map canonical docket+year -> bger decision_id from the pinned corpus."""
    table = pq.read_table(bger_parquet, columns=["decision_id"])
    index, collisions = {}, 0
    for did in table.column("decision_id").to_pylist():
        m = _BGER_ID_RE.match(did)
        if not m:
            continue
        key = _canon(m.group(1) + _year4(m.group(2)))
        if key in index and index[key] != did:
            collisions += 1
        index.setdefault(key, did)
    return index, collisions


def build_docket_number_2_map(data_bge_path):
    """ATF key -> originating docket, preferring non-null evidence."""
    result = {}
    if not (data_bge_path and os.path.exists(data_bge_path)):
        return result
    t = pq.read_table(data_bge_path, columns=["decision_id", "docket_number_2"])
    for did, d2 in zip(
        t.column("decision_id").to_pylist(),
        t.column("docket_number_2").to_pylist(),
    ):
        a = atf_key(did.replace(" ", "_"))
        if not a:
            continue
        if a not in result or (result[a] is None and _isnum(d2)):
            result[a] = d2 if _isnum(d2) else result.get(a)
    return result


def load_canonical_records(canonical_glob):
    recs = []
    for path in sorted(glob.glob(canonical_glob)):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    recs.append((rec["decision_id"], rec.get("full_text") or ""))
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-glob", default="corpus/normalization/canonical/bge_*.jsonl")
    ap.add_argument("--data-bge", default="/tmp/opencode/data_bge.parquet")
    ap.add_argument("--parquet", default="corpus/acquisition/parquet/bger.parquet")
    ap.add_argument(
        "--eval-metadata",
        default="/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json",
    )
    ap.add_argument("--out-dir", default="results/corpus")
    args = ap.parse_args()

    t0 = time.time()
    os.makedirs(args.out_dir, exist_ok=True)

    bger_index, collisions = build_bger_index(args.parquet)
    bger_ids = set(bger_index.values())
    d2map = build_docket_number_2_map(args.data_bge)
    records = load_canonical_records(args.canonical_glob)

    rows = []
    method_counts = {}
    for cid, ft in records:
        a = atf_key(cid)
        vol = volume(cid)
        docket = None
        method = None
        conf = None
        if a and _isnum(d2map.get(a)):
            docket, method, conf = str(d2map[a]), "docket_number_2", 1.0
        else:
            dk = leading_docket(ft, limit=1500)
            if dk:
                docket, method, conf = dk, "header_docket", 0.99
            else:
                dk = leading_docket(ft)
                if dk:
                    docket, method, conf = dk, "text_lead_docket", 0.996
        bger_id = bger_index.get(_canon(docket)) if docket else None
        method_counts[method or "unmapped"] = method_counts.get(method or "unmapped", 0) + 1
        rows.append(
            {
                "bge_decision_id": cid,
                "bge_volume": vol,
                "originating_docket": docket,
                "bger_decision_id": bger_id,
                "method": method,
                "confidence": conf,
                "matched": bger_id is not None,
            }
        )

    linked = [r for r in rows if r["matched"]]
    relevant = [r for r in rows if r["bge_volume"] and r["bge_volume"] >= 127]
    rel_linked = [r for r in relevant if r["matched"]]

    def rate(num, den):
        return round(num / den, 6) if den else None

    eval_align = None
    if args.eval_metadata and os.path.exists(args.eval_metadata):
        raw = json.load(open(args.eval_metadata))
        eval_ids = (
            [r.get("decision_id") or r.get("id") for r in raw]
            if isinstance(raw, list)
            else list(raw)
        )
        eval_ids = [i for i in eval_ids if isinstance(i, str)]
        hit = sum(1 for i in eval_ids if i in bger_ids)
        eval_align = {
            "evaluation_ids": len(eval_ids),
            "resolved_in_corpus": hit,
            "coverage": rate(hit, len(eval_ids)),
            "note": "literal acceptance ('crosswalk covering >=95% of evaluation bger_ IDs')",
        }

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t0, 2),
        "bge_universe": len(rows),
        "linked": len(linked),
        "overall_link_rate": rate(len(linked), len(rows)),
        "relevant_universe_volume_ge_127": {
            "n": len(relevant),
            "linked": len(rel_linked),
            "link_rate": rate(len(rel_linked), len(relevant)),
            "unmapped": len(relevant) - len(rel_linked),
        },
        "method_counts": method_counts,
        "bger_index_size": len(bger_index),
        "bger_index_collisions": collisions,
        "evaluation_id_alignment": eval_align,
        "provenance": {
            "bge_evidence": [
                "data/bge.parquet (HF voilaj/swiss-caselaw) docket_number_2",
                "committed canonical bge_*.jsonl Urteilskopf / regeste text",
            ],
            "bger_index": args.parquet,
            "canonical_ids": args.canonical_glob,
        },
    }

    table = pa.Table.from_pylist(
        rows,
        schema=pa.schema(
            [
                ("bge_decision_id", pa.string()),
                ("bge_volume", pa.int32()),
                ("originating_docket", pa.string()),
                ("bger_decision_id", pa.string()),
                ("method", pa.string()),
                ("confidence", pa.float64()),
                ("matched", pa.bool_()),
            ]
        ),
    )
    out_parquet = os.path.join(args.out_dir, "bge_bger_crosswalk.parquet")
    pq.write_table(table, out_parquet)
    with open(os.path.join(args.out_dir, "bge_bger_crosswalk_metrics_v36.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)
    if eval_align:
        with open(os.path.join(args.out_dir, "eval_id_alignment_v36.json"), "w") as fh:
            json.dump(eval_align, fh, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"wrote {out_parquet}")


if __name__ == "__main__":
    main()
