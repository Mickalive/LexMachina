#!/usr/bin/env python3
"""Frozen D2/D3/D4 content-defect re-probe over the committed bundle family.

Why this exists
---------------
Direction v68 ordered work item (2) asks the product to *publish* a per-bundle
and per-class histogram of the frozen D2/D3/D4 content predicates over the
flagship offline/server slice family, together with the false-reject count on
the confirmed set, instead of restating the result as prose in
``state/product.json``.  Until this module existed the only statement of that
result was the narrative line

    "All 4 offline slice bundles and the server slice bundle regenerated with
     the fix show correct downgrades"

which no committed instrument re-derived.  This module is that instrument.

What it measures (and what it deliberately does not)
----------------------------------------------------
For every committed ``*.bundle.json`` under ``results/product/offline_slice/``
and ``results/product/server_slice/`` it applies the product's own frozen
content predicates (``product.query.counter_evidence_span.frozen_content_defects``)
to every row that is still ``counter_evidence_verified is True`` and counts the
defect classes that survive on the *shipped* (post-filter) bytes.

* ``fixed_path_family`` — bundles whose provenance carries
  ``provenance.counter_evidence_span.content_filter``, i.e. bundles that were
  regenerated on the fixed path.  This family is *identified from the bytes*,
  never hard-coded, so a future regeneration is picked up automatically.
* ``all_committed`` — every committed bundle, including historical ones that
  predate the fix.  Historical defects are preserved evidence, not a defect of
  the current head; both populations are published side by side so the two are
  never conflated.

It imports the frozen predicate constants verbatim through the accepted
``counter_evidence_span`` module and re-publishes their provenance hashes.  It
NEVER re-derives, re-tunes or edits the frozen gate, rubric, threshold or bar,
it never runs the evaluation scorer and it makes no serve/admission claim.

Claim ceiling
-------------
Reported-only measurement of committed bytes under the frozen content
predicates.  It says nothing about legal usefulness, nothing about a frozen
scorer's emission predicate (factory-wide requirement 26 keeps those families
separate), and nothing about bundles outside this repository.

Usage
-----
    python3 product/content_family_probe.py --run-id 40143042888
    python3 product/content_family_probe.py --json
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

SCHEMA = "product-content-family-probe/1"

#: The frozen defect classes ordered work item (2) is scored on.
DEFECT_CLASSES = (
    "D1_empty_evidence",
    "D2_letterhead_zone",
    "D3_markup_residue",
    "D4_language_marker_mismatch",
)

#: The confirmed (frozen-gate-confirmed, content-sound) row that must survive
#: the filter.  Ordered-work success rule: "the known sound row
#: bstger_SK.2023.49 stays verified/sound".
CONFIRMED_SOUND_ROW = (
    "results/product/offline_slice/20261024T185300Z"
    "/corporate-criminal-liability.bundle.json",
    "bstger_SK.2023.49",
)

CLAIM_CEILING = (
    "REPORTED-ONLY measurement of committed bundle bytes under the frozen "
    "D1-D4 content predicates. It re-derives no frozen scorer population or "
    "emission predicate, scores no frozen bar, evaluates no serve verdict and "
    "makes no legal-usefulness claim. Historical bundles that predate the fix "
    "are preserved evidence, not current-head defects."
)


def bundle_paths() -> list[Path]:
    """Every committed flagship bundle, sorted for determinism."""
    patterns = (
        "results/product/offline_slice/*/*.bundle.json",
        "results/product/server_slice/*/*.bundle.json",
    )
    out: list[Path] = []
    for pat in patterns:
        out.extend(Path(p) for p in glob.glob(str(ROOT / pat)))
    return sorted(set(out))


def _has_fixed_path_provenance(doc: dict) -> bool:
    cf = ((doc.get("provenance") or {}).get("counter_evidence_span") or {}).get(
        "content_filter"
    )
    return isinstance(cf, dict) and bool(cf)


def probe_bundle(path: Path) -> dict:
    """Per-bundle histogram of surviving frozen content defects."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("decisions") or []
    hist: dict[str, int] = {}
    defective: list[dict] = []
    verified_ids: list[str] = []
    for row in rows:
        if row.get("counter_evidence_verified") is not True:
            continue
        did = str(row.get("decision_id"))
        verified_ids.append(did)
        defects = ces.frozen_content_defects(str(row.get("counter_evidence") or ""), row)
        for d in defects:
            hist[d] = hist.get(d, 0) + 1
        if defects:
            defective.append({"decision_id": did, "defects": defects})
    return {
        "path": str(path.relative_to(ROOT)),
        "fixed_path_family": _has_fixed_path_provenance(doc),
        "n_decisions": len(rows),
        "n_verified": len(verified_ids),
        "n_verified_defective": len(defective),
        "defect_histogram": {c: hist.get(c, 0) for c in DEFECT_CLASSES},
        "verified_defective_rows": defective,
        "verified_ids": verified_ids,
    }


def _totals(rows: list[dict]) -> dict:
    hist = {c: 0 for c in DEFECT_CLASSES}
    for r in rows:
        for c, n in r["defect_histogram"].items():
            hist[c] = hist.get(c, 0) + n
    return {
        "n_bundles": len(rows),
        "n_decisions": sum(r["n_decisions"] for r in rows),
        "n_verified": sum(r["n_verified"] for r in rows),
        "n_verified_defective": sum(r["n_verified_defective"] for r in rows),
        "defect_histogram": hist,
    }


def confirmed_set_status() -> dict:
    """False-reject check: the known sound row must still be verified."""
    rel, did = CONFIRMED_SOUND_ROW
    path = ROOT / rel
    if not path.is_file():
        return {
            "decision_id": did,
            "path": rel,
            "present": False,
            "still_verified": False,
            "defects": ["bundle_missing"],
        }
    doc = json.loads(path.read_text(encoding="utf-8"))
    row = next((d for d in doc.get("decisions") or [] if d.get("decision_id") == did), None)
    if row is None:
        return {
            "decision_id": did,
            "path": rel,
            "present": False,
            "still_verified": False,
            "defects": ["row_missing"],
        }
    defects = ces.frozen_content_defects(str(row.get("counter_evidence") or ""), row)
    return {
        "decision_id": did,
        "path": rel,
        "present": True,
        "still_verified": row.get("counter_evidence_verified") is True,
        "defects": defects,
        "counter_status": row.get("counter_status"),
    }


def run(run_id: str | None = None, direction_version: int | None = None) -> dict:
    rows = [probe_bundle(p) for p in bundle_paths()]
    fixed = [r for r in rows if r["fixed_path_family"]]
    fixed_totals = _totals(fixed)
    all_totals = _totals(rows)
    confirmed = confirmed_set_status()
    hist = fixed_totals["defect_histogram"]
    success = (
        hist["D2_letterhead_zone"] == 0
        and hist["D3_markup_residue"] == 0
        and hist["D4_language_marker_mismatch"] == 0
        and confirmed["still_verified"] is True
        and not confirmed["defects"]
    )
    prov = ces.content_filter_provenance()
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "run_id": run_id,
        "direction_version": direction_version,
        "claim_ceiling": CLAIM_CEILING,
        "frozen_predicate_provenance": {
            "predicate_source": prov.get("predicate_source"),
            "predicate_source_sha256": ces.FROZEN_PREDICATE_SOURCE_SHA256,
            "frozen_hypothesis_sha256": ces.FROZEN_PREDICATE_HYPOTHESIS_SHA256,
            "letterhead_zone_offset_max": prov.get("letterhead_zone_offset_max"),
            "min_marker_hits": prov.get("min_marker_hits"),
            "markup_tokens": prov.get("markup_tokens"),
            "alignment": prov.get("alignment"),
        },
        "family_definition": (
            "fixed_path_family = bundle provenance carries "
            "counter_evidence_span.content_filter (regenerated on the fixed "
            "path); identified from the bytes, never hard-coded"
        ),
        "fixed_path_family": {"totals": fixed_totals, "bundles": fixed},
        "all_committed": {"totals": all_totals, "bundles": rows},
        "confirmed_set": confirmed,
        "ordered_work_2_success_rule": {
            "defect_histogram_zero_D2_D3_D4": (
                hist["D2_letterhead_zone"] == 0
                and hist["D3_markup_residue"] == 0
                and hist["D4_language_marker_mismatch"] == 0
            ),
            "confirmed_sound_row_still_verified": confirmed["still_verified"] is True,
            "false_reject_count": 0 if confirmed["still_verified"] else 1,
            "met": success,
        },
        "false_reject_count": 0 if confirmed["still_verified"] else 1,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--direction-version", type=int, default=None)
    ap.add_argument("--out", default=None, help="output json path")
    ap.add_argument("--json", action="store_true", help="print record and exit")
    args = ap.parse_args(argv)

    rec = run(run_id=args.run_id, direction_version=args.direction_version)
    if args.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    out = args.out
    if not out:
        rid = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = str(
            ROOT / "results" / "product" / "counter_content_family" / f"CYCLE_{rid}.json"
        )
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    t = rec["fixed_path_family"]["totals"]
    h = t["defect_histogram"]
    print(f"content family probe -> {out_path.relative_to(ROOT)}")
    print(f"  fixed-path family: {t['n_bundles']} bundle(s), {t['n_decisions']} decisions")
    print(f"  verified rows: {t['n_verified']}  verified+defective: {t['n_verified_defective']}")
    print(f"  D2={h['D2_letterhead_zone']} D3={h['D3_markup_residue']} "
          f"D4={h['D4_language_marker_mismatch']} D1={h['D1_empty_evidence']}")
    a = rec["all_committed"]["totals"]["defect_histogram"]
    print(f"  all committed ({rec['all_committed']['totals']['n_bundles']} bundles): "
          f"D2={a['D2_letterhead_zone']} D3={a['D3_markup_residue']} "
          f"D4={a['D4_language_marker_mismatch']} (historical, preserved)")
    print(f"  confirmed set false rejects: {rec['false_reject_count']}")
    print(f"  ordered-work (2) success rule met: "
          f"{rec['ordered_work_2_success_rule']['met']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
