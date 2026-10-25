#!/usr/bin/env python3
"""Before/after measurement of the direction-v68 stage-2 surface→gate bridge.

Why this exists
---------------
The claim ceiling of the accepted product chain names the residual precisely:

    *"the comparative map-versus-ranked-list question stays VACUOUS until
    evidenced sound counter rows exist"*,

and the shipped path produced almost none: on the flagship offline family
stage 1 ran with ``n_candidates=1`` per 100-row bundle and ``n_selected=0`` on
every profile-bearing bundle, while the accepted pool counter-surface scan
already held 10..26 verbatim evidence sentences per bundle that the frozen
confirm-or-abstain gate had never been shown.  ``apply_surface_span_confirmation``
is the hand-off; this module is its instrument, so the effect is a committed
number rather than a sentence in a report.

What it measures (and what it deliberately does not)
----------------------------------------------------
For every flagship bundle under ``results/product/offline_slice/`` and
``results/product/server_slice/`` it records, per slug:

* stage-1 emission (``provenance.counter_evidence_span``),
* stage-2 emission (``provenance.counter_evidence_span_surface``),
* verified row count, counter-authority count (``counter_status`` predicate),
* the frozen D1-D4 content-defect histogram over every verified row.

Bundles are partitioned **from the bytes**: ``pre_stage2`` carries the fixed
path's ``counter_evidence_span.content_filter`` but no
``counter_evidence_span_surface`` block; ``stage2`` carries both.  The two
populations are published side by side; the pairing is by slug, latest bundle
first, and every path is printed so a reader can re-derive it.

It NEVER re-derives a frozen scorer population or emission predicate (factory
wide requirement 26 keeps those families separate), never scores a frozen bar,
never evaluates a serve verdict and makes no legal-usefulness claim.  It
publishes ``n_candidates`` / ``n_selected`` / ``n_abstained`` together and
pre-declares **no** support rate: whether a frozen scorer counts abstained rows
is decided by that scorer's own population predicate as written.

Usage
-----
    python3 product/surface_confirmation_report.py --run-id 40160899758
    python3 product/surface_confirmation_report.py --json
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402
from product.query.counter_status import (  # noqa: E402
    counter_authority_count,
    counter_status_bearing_count,
)

SCHEMA = "product-surface-confirmation-report/1"

DEFECT_CLASSES = (
    "D1_empty_evidence",
    "D2_letterhead_zone",
    "D3_markup_residue",
    "D4_language_marker_mismatch",
)

CLAIM_CEILING = (
    "REPORTED-ONLY before/after measurement of committed bundle bytes. It "
    "re-derives no frozen scorer population or emission predicate (factory-wide "
    "requirement 26 keeps those measurement families separate), scores no "
    "frozen bar, evaluates no serve verdict and makes no legal-usefulness "
    "claim. n_candidates / n_selected / n_abstained are published together and "
    "no support rate is pre-declared. The pre_stage2 population is preserved "
    "historical evidence, not a defect of the current head."
)


def bundle_paths() -> list[Path]:
    out: list[Path] = []
    for pat in (
        "results/product/offline_slice/*/*.bundle.json",
        "results/product/server_slice/*/*.bundle.json",
    ):
        out.extend(Path(p) for p in glob.glob(str(ROOT / pat)))
    return sorted(set(out))


def _slug(path: Path) -> str:
    return path.stem.replace(".bundle", "")


def measure(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("decisions") or []
    prov = doc.get("provenance") or {}
    p1 = prov.get("counter_evidence_span") or {}
    p2 = prov.get("counter_evidence_span_surface") or {}
    hist: dict[str, int] = {}
    verified_ids: list[str] = []
    for row in rows:
        if row.get("counter_evidence_verified") is not True:
            continue
        did = str(row.get("decision_id"))
        verified_ids.append(did)
        for d in ces.frozen_content_defects(str(row.get("counter_evidence") or ""), row):
            hist[d] = hist.get(d, 0) + 1
    return {
        "path": str(path.relative_to(ROOT)),
        "slug": _slug(path),
        "n_decisions": len(rows),
        "counter_authorities": counter_authority_count(rows),
        "counter_status_bearing": counter_status_bearing_count(rows),
        "n_verified": len(verified_ids),
        "verified_ids": verified_ids,
        "defect_histogram": {c: hist.get(c, 0) for c in DEFECT_CLASSES},
        "stage1": {
            "applied": p1.get("applied"),
            "n_candidates": p1.get("n_candidates"),
            "n_selected": p1.get("n_selected"),
            "n_abstained": p1.get("n_abstained"),
            "abstention_reasons": p1.get("abstention_reasons"),
        },
        "stage2": {
            "present": bool(p2),
            "applied": p2.get("applied"),
            "reason": p2.get("reason"),
            "n_surface_signals": p2.get("n_surface_signals"),
            "n_candidates": p2.get("n_candidates"),
            "n_selected": p2.get("n_selected"),
            "n_abstained": p2.get("n_abstained"),
            "n_excluded_cited": p2.get("n_excluded_cited"),
            "n_owned_by_stage_1": p2.get("n_owned_by_stage_1"),
            "yield_on_candidates": p2.get("yield_on_candidates"),
            "abstention_reasons": p2.get("abstention_reasons"),
            "selected_ids": p2.get("selected_ids"),
        },
        "stage2_present": bool(p2),
        "fixed_path_family": isinstance(
            ((prov.get("counter_evidence_span") or {}).get("content_filter") or {}),
            dict,
        ) and bool((prov.get("counter_evidence_span") or {}).get("content_filter")),
    }


def _totals(rows: list[dict]) -> dict:
    hist = {c: 0 for c in DEFECT_CLASSES}
    for r in rows:
        for c, n in r["defect_histogram"].items():
            hist[c] = hist.get(c, 0) + n
    agg = {
        "n_bundles": len(rows),
        "n_decisions": sum(r["n_decisions"] for r in rows),
        "counter_authorities": sum(r["counter_authorities"] for r in rows),
        "counter_status_bearing": sum(r["counter_status_bearing"] for r in rows),
        "n_verified": sum(r["n_verified"] for r in rows),
        "stage1_n_candidates": sum(r["stage1"]["n_candidates"] or 0 for r in rows),
        "stage1_n_selected": sum(r["stage1"]["n_selected"] or 0 for r in rows),
        "stage2_n_candidates": sum(r["stage2"]["n_candidates"] or 0 for r in rows),
        "stage2_n_selected": sum(r["stage2"]["n_selected"] or 0 for r in rows),
        "stage2_n_abstained": sum(r["stage2"]["n_abstained"] or 0 for r in rows),
        "stage2_n_excluded_cited": sum(
            r["stage2"]["n_excluded_cited"] or 0 for r in rows),
        "defect_histogram": hist,
    }
    c = agg["stage2_n_candidates"]
    agg["stage2_yield_on_candidates"] = (
        round(agg["stage2_n_selected"] / c, 6) if c else None
    )
    return agg


def run(run_id: str | None = None, direction_version: int | None = None) -> dict:
    rows = [measure(p) for p in bundle_paths()]
    fixed = [r for r in rows if r["fixed_path_family"]]
    pre = [r for r in fixed if not r["stage2_present"]]
    post = [r for r in fixed if r["stage2_present"]]

    # Like-for-like pairing by slug: newest bundle of each population.
    by_slug: dict[str, dict[str, dict]] = {}
    for r in sorted(pre, key=lambda x: x["path"]):
        by_slug.setdefault(r["slug"], {})["before"] = r
    for r in sorted(post, key=lambda x: x["path"]):
        by_slug.setdefault(r["slug"], {})["after"] = r
    paired = {
        slug: {
            "before_path": v.get("before", {}).get("path"),
            "after_path": v.get("after", {}).get("path"),
            "before": {k: v.get("before", {}).get(k) for k in (
                "n_decisions", "counter_authorities", "counter_status_bearing",
                "n_verified", "defect_histogram", "stage1")},
            "after": {k: v.get("after", {}).get(k) for k in (
                "n_decisions", "counter_authorities", "counter_status_bearing",
                "n_verified", "defect_histogram", "stage1", "stage2")},
        }
        for slug, v in sorted(by_slug.items())
        if v.get("before") and v.get("after")
    }

    before_totals = _totals([v["before"] for v in paired.values()])
    after_totals = _totals([v["after"] for v in paired.values()])
    after_hist = after_totals["defect_histogram"]

    delta = {
        "counter_authorities": (
            after_totals["counter_authorities"] - before_totals["counter_authorities"]
        ),
        "n_verified": after_totals["n_verified"] - before_totals["n_verified"],
        "counter_status_bearing": (
            after_totals["counter_status_bearing"]
            - before_totals["counter_status_bearing"]
        ),
        "stage1_n_selected_unchanged_at_zero": (
            before_totals["stage1_n_selected"] == 0
            and after_totals["stage1_n_selected"] == 0
        ),
    }

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "run_id": run_id,
        "direction_version": direction_version,
        "claim_ceiling": CLAIM_CEILING,
        "component": ces.SURFACE_SPAN_VERSION,
        "kill_switch": ces.SURFACE_SPAN_ENV,
        "family_definition": (
            "fixed_path = provenance.counter_evidence_span.content_filter "
            "(the accepted fixed path); stage2 = the same bundle additionally "
            "carries provenance.counter_evidence_span_surface. Both families "
            "are identified from the bytes, never hard-coded; the before/after "
            "comparison pairs them by slug, newest first"
        ),
        "frozen_predicate_provenance": ces.content_filter_provenance(),
        "paired_by_slug": paired,
        "before_pre_stage2": {"totals": before_totals},
        "after_stage2": {"totals": after_totals},
        "delta": delta,
        "content_histogram": {
            "before": before_totals["defect_histogram"],
            "after": after_hist,
        },
        "stage2_success_rule": {
            "defect_histogram_zero_D2_D3_D4_after": (
                after_hist["D2_letterhead_zone"] == 0
                and after_hist["D3_markup_residue"] == 0
                and after_hist["D4_language_marker_mismatch"] == 0
            ),
            "no_new_verified_row_is_content_defective": all(
                (r["defect_histogram"][c] == 0 for c in DEFECT_CLASSES)
                for r in post
            ),
            "emitted_verified_rows_increased": delta["n_verified"] > 0,
            "stage1_still_zero_so_the_gain_is_the_bridge": (
                before_totals["stage1_n_selected"] == 0
                and after_totals["stage1_n_selected"] == 0
                and delta["n_verified"] > 0
            ),
            "three_numbers_published_together": (
                after_totals["stage2_n_candidates"]
                == after_totals["stage2_n_selected"]
                + after_totals["stage2_n_abstained"]
            ),
            "support_rate_pre_declared": False,
        },
        "unpaired_fixed_path_bundles": sorted(
            [r["path"] for r in fixed
             if not (r["slug"] in paired)]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--direction-version", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rec = run(run_id=args.run_id, direction_version=args.direction_version)
    if args.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    out = args.out
    if not out:
        rid = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = str(ROOT / "results" / "product" / "counter_surface_confirmation"
                   / f"CYCLE_{rid}.json")
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    b, a, d = rec["before_pre_stage2"]["totals"], rec["after_stage2"]["totals"], rec["delta"]
    print(f"surface confirmation report -> {out_path.relative_to(ROOT)}")
    print(f"  paired slugs: {len(rec['paired_by_slug'])}")
    print(f"  BEFORE counter_authorities={b['counter_authorities']} "
          f"verified={b['n_verified']} stage1_selected={b['stage1_n_selected']}")
    print(f"  AFTER  counter_authorities={a['counter_authorities']} "
          f"verified={a['n_verified']} stage1_selected={a['stage1_n_selected']} "
          f"stage2={a['stage2_n_selected']}/{a['stage2_n_candidates']} "
          f"(abstained {a['stage2_n_abstained']}, cited-excluded "
          f"{a['stage2_n_excluded_cited']})")
    print(f"  delta  counter_authorities={d['counter_authorities']} "
          f"verified={d['n_verified']}")
    print(f"  defect histogram before={rec['content_histogram']['before']} "
          f"after={rec['content_histogram']['after']}")
    print(f"  stage-2 success rule: {rec['stage2_success_rule']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
