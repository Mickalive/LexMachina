"""Warm the cached detail bodies the counter-surface scan needs.

The counter-surface/2 measurement showed the remaining ceiling is not the
selector but the backing store: on the four cached reality legs only 54 of
689 rendered rows had a detail body recorded, so most marker-bearing rows
could never be hydrated offline (``n_hydrateable_in_pool_total`` was 2).

This tool closes that gap **without changing the product path**: it runs the
same fixture query the offline slice runs, selects the rows whose rendered
probe text already carries a limitation marker (marker-first, then rank),
fetches only the missing detail envelopes from OpenCaseLaw, and writes them
into the append-only product cache.  A later offline replay then hydrates
those rows exactly like any other recorded envelope — no network, no new
selector, no fabrication.

Properties:

* **Append-only** — existing cache envelopes are never rewritten (mode
  ``live`` reads a fresh entry and stops); the tool records a digest of the
  existing detail files before/after and fails closed if one changed.
* **Bounded** — ``--limit`` caps requests per leg and the tool never fetches
  a row that already has a cached body or rendered ``full_text``.
* **Fail-closed** — a transport/API error is recorded and the run continues;
  nothing is synthesised and the exit code is non-zero only for an invariant
  break or a wholly failed leg, not for individual upstream 404s.

Usage::

    python product/cached_detail_warm.py --limit 24 --dry-run
    python product/cached_detail_warm.py --limit 24 \
        --out results/product/counter_surface/CYCLE_<run>_warm.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(REPO_ROOT), str(PRODUCT_ROOT), str(REPO_ROOT / "frontier" / "frontier-query-retrieval")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query.cache_path import product_cache_dir  # noqa: E402
from product.query.counter_surface import marker_bearing, probe_text  # noqa: E402

SCHEMA = "product-cached-detail-warm/1"
DEFAULT_LEGS = (
    "rent-default",
    "petty-theft-dismissal",
    "corporate-criminal-liability",
    "business-judgment-rule",
)
#: Selector ceiling per leg.  The scan budget is 200; this is deliberately
#: small so a warm pass stays a bounded, reviewable network spend.
DEFAULT_LIMIT = 24


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detail_cache_index(cache_dir: Path | str | None = None) -> dict[str, dict]:
    """Map cached detail bodies by ``decision_id``.

    Only ``/decisions/...`` envelopes with a parseable body count; search and
    citation envelopes are ignored so the index cannot claim a text it does
    not have.  Partial (empty) ``full_text`` bodies are indexed with
    ``full_text_chars == 0`` and are not treated as hydration-capable.
    """
    root = Path(cache_dir) if cache_dir is not None else product_cache_dir()
    index: dict[str, dict] = {}
    if not root.exists():
        return index
    for path in sorted(root.glob("**/*.json")):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(envelope, dict):
            continue
        if not str(envelope.get("path") or "").startswith("/decisions/"):
            continue
        body = envelope.get("body")
        try:
            parsed = json.loads(body) if isinstance(body, str) else body
        except (TypeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        decision_id = str(parsed.get("decision_id") or "")
        if not decision_id:
            continue
        index[decision_id] = {
            "path": path.name,
            "status": int(envelope.get("status") or 0),
            "full_text_chars": len(str(parsed.get("full_text") or "")),
        }
    return index


def select_warm_targets(
    rows: Iterable[dict],
    *,
    existing_ids: set[str],
    limit: int,
) -> list[str]:
    """Bounded, marker-first, rank-stable ids that still lack a cached body."""
    cap = max(0, int(limit))
    if cap == 0:
        return []
    missing = [
        row for row in rows
        if str(row.get("decision_id") or "")
        and not str(row.get("full_text") or "").strip()
        and str(row.get("decision_id")) not in existing_ids
    ]
    marker_ids = [
        str(row.get("decision_id")) for row in missing
        if marker_bearing(probe_text(row))
    ]
    taken = set(marker_ids)
    ordered = marker_ids + [
        str(row.get("decision_id")) for row in missing
        if str(row.get("decision_id")) not in taken
    ]
    return ordered[:cap]


def _digest_existing(cache_dir: Path, index: dict[str, dict]) -> dict[str, str]:
    """Digest exactly the detail envelopes present before the warm pass."""
    names = {entry["path"] for entry in index.values()}
    out: dict[str, str] = {}
    for path in sorted(cache_dir.glob("**/*.json")):
        if path.name not in names:
            continue
        out[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def warm_targets(
    ids: Iterable[str],
    *,
    client: Any,
    rate_hint: str = "live",
) -> dict[str, int]:
    """Fetch and cache missing detail bodies.  Returns counters only.

    The client is injected so tests can prove selection/appending behaviour
    without a socket.  A decision returned without ``full_text`` is counted
    as ``empty`` — it is not evidence and does not become one.
    """
    counters = {"requested": 0, "fetched": 0, "empty": 0, "failed": 0}
    for decision_id in ids:
        counters["requested"] += 1
        try:
            decision = client.get_decision(decision_id, full_text=True)
        except Exception as exc:  # noqa: BLE001 - per-row degradation
            counters["failed"] += 1
            counters.setdefault("errors", 0)
            counters["errors"] += 1
            if counters["errors"] <= 5:
                counters.setdefault("error_samples", [])
                counters["error_samples"].append(
                    f"{decision_id}: {type(exc).__name__}: {exc}"
                )  # type: ignore[index]
            continue
        chars = len(str((decision or {}).get("full_text") or ""))
        if chars:
            counters["fetched"] += 1
        else:
            counters["empty"] += 1
    counters["rate_hint"] = rate_hint  # type: ignore[assignment]
    return counters


def _make_client(cache_dir: Path) -> Any:
    from ocl_adapter.cache import FileCache
    from ocl_adapter.client import OCLClient
    from ocl_adapter.config import AdapterConfig
    from ocl_adapter.transport import CachedTransport, HttpTransport

    cfg = AdapterConfig(mode="live", cache_dir=str(cache_dir), max_rps=4.0)
    transport = CachedTransport(
        HttpTransport(cfg.base_url), FileCache(cache_dir), mode="live"
    )
    return OCLClient(transport, cfg)


def warm_leg(
    slug: str,
    query: str,
    *,
    top_n: int,
    limit: int,
    cache_dir: Path,
    client_factory: Callable[[Path], Any] | None = None,
    dry_run: bool = False,
) -> dict:
    """Select and (unless dry-run) fetch missing detail bodies for one leg."""
    from product.query.pipeline import run_query_initial

    bundle = run_query_initial(query, top_n=top_n, retrieval_mode="fixture")
    rows = list(bundle.get("decisions") or [])
    index_before = detail_cache_index(cache_dir)
    # Any cached detail envelope is skipped: the warm pass only appends
    # bodies the store cannot answer for at all, never rewrites one.
    existing = set(index_before)
    targets = select_warm_targets(rows, existing_ids=existing, limit=limit)
    marker_targets = sum(
        1 for row in rows
        if str(row.get("decision_id")) in set(targets)
        and marker_bearing(probe_text(row))
    )
    record: dict[str, Any] = {
        "slug": slug,
        "query": query,
        "n_rendered": len(rows),
        "n_detail_cached_before": sum(
            1 for v in index_before.values() if v["full_text_chars"] > 0),
        "n_missing": sum(
            1 for row in rows
            if str(row.get("decision_id") or "")
            and not str(row.get("full_text") or "").strip()
            and str(row.get("decision_id")) not in existing
        ),
        "n_selected": len(targets),
        "n_selected_marker_bearing": marker_targets,
        "targets": targets,
        "dry_run": dry_run,
    }
    if dry_run or not targets:
        record["counters"] = {"requested": 0, "fetched": 0, "empty": 0, "failed": 0}
        return record

    digest_before = _digest_existing(cache_dir, index_before)
    client = (client_factory or _make_client)(cache_dir)
    counters = warm_targets(targets, client=client)
    digest_after = _digest_existing(cache_dir, index_before)
    modified = [name for name, digest in digest_before.items()
                if digest_after.get(name) != digest]
    index_after = detail_cache_index(cache_dir)
    record.update({
        "counters": counters,
        "n_detail_cached_after": sum(
            1 for v in index_after.values() if v["full_text_chars"] > 0),
        "append_only_ok": not modified,
        "modified_existing": modified[:10],
        "cache_dir": str(cache_dir),
    })
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slugs", default=",".join(DEFAULT_LEGS))
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="max detail requests per leg")
    ap.add_argument("--dry-run", action="store_true",
                    help="select targets only; no network, no writes")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    from product.reality_check import LEGS

    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    unknown = [s for s in slugs if s not in LEGS]
    if unknown:
        print(f"unknown slugs: {unknown}; known: {sorted(LEGS)}", file=sys.stderr)
        return 2

    run_id = os.environ.get("GITHUB_RUN_ID") or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")
    cache_dir = product_cache_dir()
    legs = [
        warm_leg(slug, LEGS[slug], top_n=args.top_n, limit=args.limit,
                 cache_dir=cache_dir, dry_run=args.dry_run)
        for slug in slugs
    ]
    total_fetched = sum(l["counters"].get("fetched", 0) for l in legs)
    total_failed = sum(l["counters"].get("failed", 0) for l in legs)
    total_empty = sum(l["counters"].get("empty", 0) for l in legs)
    append_only_ok = all(l.get("append_only_ok", True) for l in legs)
    artifact = {
        "schema": SCHEMA,
        "record_type": "CACHED_DETAIL_WARM",
        "run_id": run_id,
        "generated_at": _now(),
        "cache_dir": str(cache_dir),
        "dry_run": args.dry_run,
        "legs": legs,
        "aggregate": {
            "n_legs": len(legs),
            "n_selected": sum(l["n_selected"] for l in legs),
            "n_selected_marker_bearing": sum(
                l["n_selected_marker_bearing"] for l in legs),
            "n_fetched": total_fetched,
            "n_empty": total_empty,
            "n_failed": total_failed,
            "append_only_ok": append_only_ok,
        },
        "claim_ceiling": (
            "Cache coverage only.  This does not label any decision, does not "
            "score a frozen authority population, and no fetched body is "
            "evidence that a decision is a counter-authority."
        ),
    }
    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "product" / "counter_surface"
        / f"CYCLE_{run_id}_warm.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(json.dumps({"out": str(out_path), "dry_run": args.dry_run,
                      "aggregate": artifact["aggregate"]},
                     ensure_ascii=False, indent=2))
    if not append_only_ok:
        return 1
    if not args.dry_run and total_fetched == 0 and total_failed == 0:
        # Nothing selected is legitimate (cache already warm); a run that
        # selected targets but produced no text is not.
        return 0 if artifact["aggregate"]["n_selected"] == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
