from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ..filter import CounterEvidenceContentFilter


def load_bundle(bundle_path: Path) -> dict:
    with bundle_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic counter-evidence content filter")
    parser.add_argument("--bundle", required=True, help="Path to bundle JSON")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--frozen-rules", required=False, help="Path to frozen RULES.json")
    parser.add_argument("--mode", default="filter", choices=["filter", "off"])
    args = parser.parse_args(argv)

    bundle_path = Path(args.bundle)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_bundle(bundle_path)
    filt = CounterEvidenceContentFilter()

    results = []
    decisions = bundle.get("decisions") or []
    for dec in decisions:
        ce_verified = dec.get("counter_evidence_verified")
        ce = dec.get("counter_evidence")
        if ce_verified is False and not ce:
            continue  # skip if no counter evidence
        row = {
            "decision_id": dec.get("id") or dec.get("decision_id"),
            "language": dec.get("language"),
            "counter_evidence": ce,
            "full_text": dec.get("full_text") or "",
            "snippet": dec.get("snippet") or "",
            "regeste": dec.get("regeste") or "",
        }
        if args.mode == "off":
            res = filt.filter_span(row)  # compute but we report baseline; we'll mark accepted for baseline reproduction
            results.append({
                "decision_id": row["decision_id"],
                "mode": "off",
                "accepted": True,  # baseline accepts all
                "reject_reasons": [],
                "defects_caught": [],
                "details": res.details,
                "original_defects_would_be": res.defects_caught,
            })
            continue
        res = filt.filter_span(row)
        results.append({
            "decision_id": row["decision_id"],
            "mode": "filter",
            "accepted": res.accepted,
            "reject_reasons": res.reject_reasons,
            "defects_caught": res.defects_caught,
            "details": res.details,
        })

    out_path = out_dir / "filter_results.json"
    summary_path = out_dir / "filter_summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    # compute summary
    summary = {
        "n_total": len(results),
        "n_accepted": sum(1 for r in results if r["accepted"]),
        "n_rejected": sum(1 for r in results if not r["accepted"]),
        "defect_histogram": {"D2_letterhead_zone": 0, "D3_markup_residue": 0, "D4_language_marker_mismatch": 0},
    }
    for r in results:
        for d in r.get("defects_caught") or []:
            if d in summary["defect_histogram"]:
                summary["defect_histogram"][d] += 1
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
