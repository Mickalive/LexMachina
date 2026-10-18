#!/usr/bin/env python3
"""One-command offline clickable slice: frozen question -> bundle -> verified map.

    python product/offline_slice.py                      # rent-default fixture
    python product/offline_slice.py --slug business-judgment-rule --verify
    python product/offline_slice.py --no-enrich          # map-only, skip answer

What it proves in a single command (no network, no owner time):

* ``query -> query_result_bundle`` from the recorded OpenCaseLaw envelopes
  (``retrieval_mode="fixture"``, ``socket.connect`` booby-trapped so any
  network attempt fails loudly);
* the sourced answer + counter-authority pass of the SAME loop, from the
  generative-audit fixture provider (``fixture_generation=True``), so the
  offline slice covers question -> answer -> counter -> map, not just the map;
* enrichment never moves a rendered point (the geometry of the first map is
  compared row by row against the final bundle);
* the bundle is a *clickable* map input: every row carries ``x`` / ``y`` /
  ``cluster_id`` and a ``canonical_url`` source link, and every decision the
  answer cites is reachable from the answer panel;
* ``product/verify_query_page.js`` (the product's own DOM contract) renders it,
  so "source-linked clickable map" is checked, not asserted.

It is a developer/CI entry point for the FAST-MVP vertical slice. It never
touches the network, never claims legal usefulness, and never evaluates a
frozen live gate (fixture runs are wiring evidence only).
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

# RF1: one shared definition of "counter authority" across the product.
from product.query.counter_status import (  # noqa: E402
    counter_authority_count,
    counter_status_bearing_count,
)

DEFAULT_SLUG = "rent-default"


def _no_network(*_a, **_k):  # pragma: no cover - exercised on every run
    raise AssertionError("offline slice attempted network access")


def _geometry(bundle: dict) -> dict:
    return {
        d.get("decision_id"): (d.get("x"), d.get("y"), d.get("cluster_id"))
        for d in bundle.get("decisions") or []
    }


def build_bundle(slug: str, top_n: int, *, enrich: bool = True) -> dict:
    from query import enrich_query_bundle, run_query_initial
    from reality_check import LEGS

    if slug not in LEGS:
        raise SystemExit(f"unknown slug {slug!r}; known: {', '.join(sorted(LEGS))}")
    real_connect = socket.socket.connect
    socket.socket.connect = _no_network
    try:
        initial = run_query_initial(LEGS[slug], top_n=top_n, retrieval_mode="fixture")
        if not enrich:
            return initial
        # Full offline loop: sourced answer + counter-authority pass from the
        # fixture provider. Hydration/generation/adversarial retrieval are all
        # fixture-configured, so the network trap above stays armed throughout.
        final = enrich_query_bundle(
            initial, retrieval_mode="fixture", fixture_generation=True)
        before, after = _geometry(initial), _geometry(final)
        preserved = (
            set(before) <= set(after)
            and all(after.get(did) == geo for did, geo in before.items())
        )
        final.setdefault("provenance", {})["offline_slice"] = {
            "enriched": True,
            "geometry_preserved": preserved,
            "n_first_map": len(before),
            "n_final": len(after),
            "network": "none",
        }
        return final
    finally:
        socket.socket.connect = real_connect


def _repo_relative(path: Path) -> str:
    """Repo-relative when inside the checkout, absolute otherwise (``--out`` may
    legitimately point at a scratch directory outside the repository)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def summarise(bundle: dict) -> dict:
    rows = bundle.get("decisions") or []
    clusters: dict = {}
    for r in rows:
        cid = r.get("cluster_id")
        if cid is None:
            continue  # a None-keyed bucket is not a cluster (audit D3)
        clusters[cid] = clusters.get(cid, 0) + 1
    # RF1: the old test was `counter_status.startswith("candidate")`, which is
    # both too narrow (it misses `abstained_unevidenced`, a real counter status
    # the frozen counter-anchor classifier emits) and definitionally wrong. Use
    # the accepted single source of truth and publish both counts.
    counter_authorities = counter_authority_count(rows)
    counter_status_bearing = counter_status_bearing_count(rows)
    slice_prov = (bundle.get("provenance") or {}).get("offline_slice") or {}
    return {
        "n_decisions": len(rows),
        "n_clusters": len(clusters),
        "largest_cluster": max(clusters.values()) if clusters else 0,
        "rows_with_source_url": sum(1 for r in rows if r.get("canonical_url")),
        "rows_with_xy": sum(1 for r in rows
                            if isinstance(r.get("x"), (int, float))
                            and isinstance(r.get("y"), (int, float))),
        # audit D3: the docstring/report claim 'cluster_id on every row' —
        # the tool must actually verify it, not just assert it.
        "rows_with_cluster_id": sum(1 for r in rows if r.get("cluster_id") is not None),
        "counter_rows": counter_authorities,
        "counter_status_bearing_rows": counter_status_bearing,
        "answer_status": (bundle.get("answer") or {}).get("status"),
        "cited_decision_ids": len((bundle.get("answer") or {}).get("cited_decision_ids") or []),
        "enriched": bool(slice_prov.get("enriched")),
        "geometry_preserved_by_enrich": slice_prov.get("geometry_preserved"),
        "fixture_replay": ((bundle.get("provenance") or {}).get("product_fixture_replay") or {}),
    }


def verify_page(bundle_path: Path) -> tuple[bool, str]:
    node = subprocess.run(["bash", "-lc", "command -v node"], capture_output=True, text=True)
    if node.returncode != 0:
        return False, "node not found (page contract not checked)"
    proc = subprocess.run(
        ["node", str(PRODUCT_ROOT / "verify_query_page.js"), str(bundle_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip().splitlines()[-1] if out.strip() else ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", default=DEFAULT_SLUG, help="reality-leg slug (frozen question)")
    ap.add_argument("--top-n", type=int, default=100, help="map size target (MVP: ~100-300)")
    ap.add_argument("--out", default=None, help="output directory (default results/product/offline_slice/<utc>)")
    ap.add_argument("--verify", action="store_true",
                    help="also run product/verify_query_page.js on the written bundle")
    ap.add_argument("--no-enrich", action="store_true",
                    help="map-only slice: skip the sourced answer + counter-authority pass")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "product" / "offline_slice" / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    bundle = build_bundle(args.slug, args.top_n, enrich=not args.no_enrich)
    elapsed = round(time.time() - t0, 3)
    stats = summarise(bundle)
    bundle_path = out_dir / f"{args.slug}.bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True),
                           encoding="utf-8")

    ok = True
    reasons = []
    if stats["n_decisions"] < 40:
        ok = False; reasons.append(f"only {stats['n_decisions']} decisions (<40)")
    if stats["rows_with_xy"] != stats["n_decisions"]:
        ok = False; reasons.append("rows missing map coordinates")
    if stats["rows_with_cluster_id"] != stats["n_decisions"]:
        ok = False; reasons.append("rows missing cluster_id")
    if stats["rows_with_source_url"] != stats["n_decisions"]:
        ok = False; reasons.append("rows missing canonical_url source link")
    if stats["n_clusters"] < 2:
        ok = False; reasons.append("fewer than 2 clusters (no map structure)")
    # The full-loop slice must actually deliver the two other halves of the
    # product question: a sourced answer, and a map the answer pass did not
    # rearrange. A bundle that skipped enrichment simply carries no claim.
    if stats["enriched"]:
        if stats["answer_status"] != "ready":
            ok = False; reasons.append(f"answer not ready ({stats['answer_status']})")
        if stats["cited_decision_ids"] < 1:
            ok = False; reasons.append("sourced answer cites no retrieved decision")
        if stats["geometry_preserved_by_enrich"] is not True:
            ok = False; reasons.append("enrichment moved or dropped a rendered point")

    page_ok, page_last = False, ""
    if args.verify:
        page_ok, page_last = verify_page(bundle_path)
        if not page_ok:
            ok = False; reasons.append(f"page contract failed: {page_last}")

    if not args.quiet:
        print(f"offline slice [{args.slug}] in {elapsed}s (network: none)")
        for k in ("n_decisions", "n_clusters", "largest_cluster", "rows_with_source_url",
                  "rows_with_xy", "rows_with_cluster_id", "counter_rows",
                  "counter_status_bearing_rows", "answer_status",
                  "cited_decision_ids", "enriched", "geometry_preserved_by_enrich"):
            print(f"  {k}: {stats[k]}")
        print(f"  replay: {stats['fixture_replay'].get('source')}"
              f" (candidates={stats['fixture_replay'].get('n_candidates')})")
        print(f"  bundle: {_repo_relative(bundle_path)}")
        if args.verify:
            print(f"  page contract: {'PASS' if page_ok else 'FAIL'} - {page_last}")
        print(f"  verdict: {'PASS' if ok else 'FAIL'}" +
              ("" if ok else f" ({'; '.join(reasons)})"))

    (out_dir / "summary.json").write_text(json.dumps(
        {"slug": args.slug, "seconds": elapsed, "verified": ok,
         "page_contract": page_ok, "page_contract_detail": page_last,
         "stats": stats,
         "bundle": _repo_relative(bundle_path),
         "claim_ceiling": "OFFLINE WIRING EVIDENCE ONLY: runnable vertical-slice check of "
                          "query -> bundle -> sourced answer -> counter-authority pass -> "
                          "clickable map from recorded envelopes (fixture provider); no frozen "
                          "gate is evaluated and no legal-usefulness claim is made."},
        ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
