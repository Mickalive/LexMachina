#!/usr/bin/env python3
"""Measure map integrity of a committed offline-slice family.

    python product/map_integrity_probe.py \
        --run-id 40230559317 \
        --bundle results/product/offline_slice/<stamp>/rent-default.bundle.json \
        --bundle results/product/offline_slice/<stamp2>/petty-theft-dismissal.bundle.json \
        --out results/product/map_integrity/CYCLE_40230559317.json

    (``--family DIR`` works when all bundles live in one directory.)

What it measures, on committed bundle bytes only:

* duplicate map points: two rows whose *decision identity* is the same
  (court+docket, or canonical BGE citation).  "point = decision" is a map
  semantic, not decoration, so a duplicated identity is a defect.
* local inspectability per row (full_text / regeste / snippet / pointer), so a
  citation or leading-case shell is disclosed rather than silently rendered as
  a readable judgment.
* source-link coverage split honestly: canonical_url vs source_url.
* the bundle's own identity_merge provenance (which ids disappeared and why).

This is a product-owned engineering measurement.  It scores no frozen bar, makes
no legal-usefulness claim and changes no threshold.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query.bundle import content_coverage  # noqa: E402
from product.query.pipeline import _decision_identity  # noqa: E402

CLAIM_CEILING = (
    "ENGINEERING MAP-INTEGRITY MEASUREMENT ONLY: duplicate decision identities "
    "and local-inspectability coverage on committed offline bundles. No frozen "
    "bar, no serve verdict, no retrieval-recall and no legal-usefulness claim."
)


def _identity_label(identity: tuple[str, str] | None) -> str | None:
    if identity is None:
        return None
    court, value = identity
    return f"{court}|{value}"


def probe_bundle(path: Path) -> dict[str, Any]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    decisions = bundle.get("decisions") or []
    groups: dict[str, list[str]] = {}
    unidentifiable: list[str] = []
    for decision in decisions:
        key = _identity_label(_decision_identity(decision))
        did = str(decision.get("decision_id") or "")
        if key is None:
            unidentifiable.append(did)
            continue
        groups.setdefault(key, []).append(did)
    duplicates = [
        {"identity": key, "decision_ids": ids}
        for key, ids in sorted(groups.items())
        if len(ids) > 1
    ]
    coverage = content_coverage(decisions)
    merge = (bundle.get("provenance") or {}).get("identity_merge") or {}
    return {
        "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "n_decisions": len(decisions),
        "n_clusters": len(bundle.get("clusters") or []),
        "n_identity_groups": len(groups),
        "n_unidentifiable_rows": len(unidentifiable),
        "unidentifiable_decision_ids": unidentifiable,
        "n_duplicate_identity_groups": len(duplicates),
        "duplicate_groups": duplicates,
        "content_coverage": coverage,
        "rows_with_canonical_url": sum(1 for d in decisions if d.get("canonical_url")),
        "rows_with_source_url": sum(1 for d in decisions if d.get("source_url")),
        "identity_merge": {
            "method": merge.get("method"),
            "n_merges": merge.get("n_merges", 0),
            "n_rows_removed": merge.get("n_rows_removed", 0),
            "merges": merge.get("merges") or [],
        },
    }


def probe_family(family: Path) -> dict[str, Any]:
    """Probe every ``*.bundle.json`` directly inside one directory."""
    return probe_paths(sorted(family.glob("*.bundle.json")), label=str(family))


def probe_paths(paths: list[Path], *, label: str = "explicit_bundle_list") -> dict[str, Any]:
    """Probe an explicit set of committed bundles (the flagship family).

    The four offline-slice bundles are written to four sibling timestamp
    directories, so an explicit list is the reproducible family definition;
    the artifact records the exact paths.
    """
    bundles = [probe_bundle(path) for path in paths]
    return {
        "family": label,
        "bundle_paths": [b["path"] for b in bundles],
        "n_bundles": len(bundles),
        "n_decisions": sum(b["n_decisions"] for b in bundles),
        "n_duplicate_identity_groups": sum(b["n_duplicate_identity_groups"] for b in bundles),
        "n_pointer_only_rows": sum(b["content_coverage"]["n_pointer_only"] for b in bundles),
        "n_with_local_content": sum(b["content_coverage"]["n_with_local_content"] for b in bundles),
        "bundles": bundles,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--family", help="directory of committed *.bundle.json files")
    source.add_argument("--bundle", action="append", metavar="PATH",
                        help="explicit committed bundle path (repeat for the family)")
    parser.add_argument("--run-id", required=True, help="GitHub run id this measurement belongs to")
    parser.add_argument("--out", required=True, help="output JSON path")
    args = parser.parse_args(argv)

    if args.family:
        family = Path(args.family)
        if not family.is_absolute():
            family = REPO_ROOT / family
        if not family.is_dir():
            raise SystemExit(f"family directory not found: {family}")
        result = probe_family(family)
    else:
        paths = []
        for raw in args.bundle:
            path = Path(raw)
            if not path.is_absolute():
                path = REPO_ROOT / path
            if not path.is_file():
                raise SystemExit(f"bundle not found: {path}")
            paths.append(path)
        result = probe_paths(paths)
    result.update({
        "run_id": str(args.run_id),
        "instrument": "product/map_integrity_probe.py",
        "claim_ceiling": CLAIM_CEILING,
        "success_rule": (
            "n_duplicate_identity_groups == 0 on every bundle and "
            "content_coverage.n_decisions == n_decisions"
        ),
        "success_met": (
            result["n_duplicate_identity_groups"] == 0
            and all(b["content_coverage"]["n_decisions"] == b["n_decisions"] for b in result["bundles"])
        ),
    })
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "family": result["family"],
        "n_bundles": result["n_bundles"],
        "n_decisions": result["n_decisions"],
        "n_duplicate_identity_groups": result["n_duplicate_identity_groups"],
        "n_pointer_only_rows": result["n_pointer_only_rows"],
        "success_met": result["success_met"],
        "out": str(out),
    }, ensure_ascii=False, indent=2))
    return 0 if result["success_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
