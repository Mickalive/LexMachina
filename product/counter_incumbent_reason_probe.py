#!/usr/bin/env python3
"""Per-row reason-code probe for the v68 rejection/incumbent leg.

Why this exists
---------------
Direction v68 ordered work (1) requires the shipped rejection/incumbent leg to
*publish per-row before/after evidence, reason_code and verified status for the
four defective decisions and the one sound row*.  The committed fixed-path
bundles record the downgrade reason that was current when they were generated
(``pivot_absent`` — the frozen label gate's abstention reason).  That reason is
truthful about the *gate* but not about the *content cause*: the row was
rejected because its incumbent evidence fails a frozen D2/D3/D4 predicate.

This probe re-applies the product's own ``apply_verified_span_selection`` to the
committed bytes IN MEMORY (``copy.deepcopy``) and reports, per decision, the
real content-defect reason code and verified status.  It never rewrites a
committed bundle, never touches a frozen gate/rubric/threshold/bar, never runs
an evaluation scorer and makes no serve/admission claim.

Usage
-----
    python3 product/counter_incumbent_reason_probe.py --run-id <id>
    python3 product/counter_incumbent_reason_probe.py --json
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402

SCHEMA = "product-counter-incumbent-reason/1"

#: (bundle, decision_id, expected frozen defect classes) — the accepted
#: FAST-MVP falsifier population (run 40105794124) plus the one sound row.
DEFECTIVE = [
    ("results/product/offline_slice/20261024T142517Z/rent-default.bundle.json",
     "gr_gerichte_ERZ 2010 25", ["D2_letterhead_zone"]),
    ("results/product/offline_slice/20261023T121515Z/business-judgment-rule.bundle.json",
     "bge_BGE_110_II_391", ["D2_letterhead_zone"]),
    ("results/product/offline_slice/20261023T121518Z/petty-theft-dismissal.bundle.json",
     "ge_gerichte_CAPH_107_2004", ["D3_markup_residue"]),
    ("results/product/server_slice/20261023T224255Z/served.bundle.json",
     "bge_BGE_121_III_260", ["D3_markup_residue", "D4_language_marker_mismatch"]),
]
SOUND = (
    "results/product/offline_slice/20261023T121512Z/corporate-criminal-liability.bundle.json",
    "bstger_SK.2023.49",
)


def _row_of(bundle: dict, did: str) -> dict | None:
    return next((d for d in bundle.get("decisions") or []
                 if d.get("decision_id") == did), None)


def probe_row(rel: str, did: str) -> dict:
    doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    before = _row_of(doc, did)
    out = ces.apply_verified_span_selection(
        copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid"))
    after = _row_of(out, did)
    span = (out.get("provenance") or {}).get("counter_evidence_span") or {}
    rec = next(
        (r for r in (span.get("downgrades") or [])
         + (span.get("defective_already_unverified") or [])
         if r.get("decision_id") == did),
        None,
    )
    retained = next(
        (r for r in (span.get("retained_content_sound") or [])
         if r.get("decision_id") == did), None)
    return {
        "decision_id": did,
        "path": rel,
        "before": {
            "counter_evidence_verified": bool((before or {}).get(
                "counter_evidence_verified")),
            "defects": ces.frozen_content_defects(
                str((before or {}).get("counter_evidence") or ""), before or {}),
        },
        "after": {
            "counter_evidence_verified": bool((after or {}).get(
                "counter_evidence_verified")),
            "counter_evidence_unevidenced": bool((after or {}).get(
                "counter_evidence_unevidenced")),
            "counter_evidence_unevidenced_reason": (after or {}).get(
                "counter_evidence_unevidenced_reason"),
        },
        "record": rec,
        "retained_content_sound": retained,
        "gate_applied": bool(span.get("applied")),
        "gate_abstention_reasons": span.get("abstention_reasons"),
        "content_filter_leg": span.get("content_filter_leg"),
    }


def run(run_id: str | None = None) -> dict:
    rows = [probe_row(rel, did) for rel, did, _exp in DEFECTIVE]
    sound = probe_row(*SOUND)
    for row, (_rel, _did, expected) in zip(rows, DEFECTIVE):
        row["expected_defects"] = expected
        row["defects_match"] = row["before"]["defects"] == expected
        # the content-fail downgrade reason must be the defect class, not the
        # gate's abstention reason
        want = ces._DEFECT_REASON.get(expected[0])
        row["reason_is_defect"] = (
            row["after"]["counter_evidence_unevidenced_reason"] == want)
    sound_ok = (
        sound["after"]["counter_evidence_verified"] is True
        and sound["before"]["defects"] == []
        and sound["after"]["counter_evidence_unevidenced"] is False
        and sound["retained_content_sound"] is not None
    )
    checks = {
        "four_present": all(r["before"]["counter_evidence_verified"] for r in rows),
        "four_defects_match": all(r["defects_match"] for r in rows),
        "four_no_longer_verified": all(
            r["after"]["counter_evidence_verified"] is False for r in rows),
        "four_reason_names_the_defect": all(r["reason_is_defect"] for r in rows),
        "sound_row_still_verified_and_sound": sound_ok,
    }
    checks["all_met"] = all(v for k, v in checks.items() if k != "all_met")
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "direction_version": 68,
        "claim_ceiling": (
            "Reported-only in-memory re-application of the product's own seam "
            "to committed bundle bytes. No bundle is rewritten, no frozen "
            "gate/rubric/threshold/bar is edited or re-scored, no serve or "
            "admission claim is made."
        ),
        "defective_rows": rows,
        "sound_row": sound,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rec = run(run_id=args.run_id)
    if args.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if rec["checks"]["all_met"] else 1
    out = Path(args.out) if args.out else (
        ROOT / "results" / "product" / "counter_incumbent_reason"
        / f"CYCLE_{args.run_id or rec['generated_at']}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True)
                   + "\n", encoding="utf-8")
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"counter incumbent reason probe -> {shown}")
    for row in rec["defective_rows"]:
        print(f"  {row['decision_id']}: before_verified="
              f"{row['before']['counter_evidence_verified']} "
              f"after_verified={row['after']['counter_evidence_verified']} "
              f"reason={row['after']['counter_evidence_unevidenced_reason']} "
              f"defects={row['before']['defects']}")
    s = rec["sound_row"]
    print(f"  {s['decision_id']}: verified={s['after']['counter_evidence_verified']} "
          f"defects={s['before']['defects']}")
    print(f"  all checks met: {rec['checks']['all_met']}")
    return 0 if rec["checks"]["all_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
