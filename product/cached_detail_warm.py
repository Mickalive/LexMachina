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
* **Bounded** — ``--limit`` caps requests per leg.  A row is selected only
  when its decision has **no hydration-capable cached body at all**: ids are
  compared through :func:`normalize_decision_id`, so the equivalent spellings
  ``bge_119 II 147`` (cached body id) and ``bge_BGE_119_II_147`` (rendered row
  id) are one body and the second is never fetched again, and a cached
  ``/decisions/`` envelope whose ``full_text_chars == 0`` is treated as
  *missing* rather than as a body (it cannot hydrate anything).  A row that
  already carries rendered ``full_text`` is never selected either.  Nothing
  here can guarantee that an *upstream* response is not itself served from the
  transport's own cache; "never fetches an already-cached body" is a statement
  about this tool's selection, not about the transport underneath it.
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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import unquote

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


#: Collection tokens an OpenCaseLaw decision id may carry as its leading
#: namespace.  ``bger`` is listed before ``bge`` because ``"bger...".startswith(
#: "bge")`` is true and folding the shorter token first would mangle it.
_COLLECTION_PREFIXES = ("bger", "bge")


def normalize_decision_id(value: Any) -> str:
    """Canonical comparison key for one decision id.

    Audit R2 of rejected cycle 39891382087: the same body was fetched twice
    because the cached envelope's ``decision_id`` (``bge_119 II 147``) and the
    rendered row's id (``bge_BGE_119_II_147``) differ — they are the *same*
    decision (identical content_hash — the audit's name for
    ``sha256(regeste + full_text)`` — of
    ``f6e4b5814366f0fe642e42a992b3c8b0bc2f04b08e3056fe4f1a11e3183919fb``,
    identical source URL, identical full text), so raw string equality is the
    wrong predicate for "already cached".

    Exactly these differences are folded, and nothing else:

    * percent-encoding of a requested cache path (``%20`` → space);
    * case, spaces, underscores and hyphens;
    * **one** redundant leading collection token, and only when the remainder
      still starts with a collection token — ``bge_BGE_119_II_147`` →
      ``bge119ii147``, which is what ``bge_119 II 147`` folds to.  Because a
      fold only happens when a second collection token follows, two genuinely
      different decisions (``bge_119 II 147`` vs ``bger_119 II 147``) can
      never collapse into one key.
    """
    text = unquote(str(value or "")).strip().lower()
    text = re.sub(r"[\s_\-]+", "", text)
    for _ in range(2):  # at most two collection tokens, never more
        for prefix in _COLLECTION_PREFIXES:
            if text.startswith(prefix):
                rest = text[len(prefix):]
                if any(rest.startswith(p) for p in _COLLECTION_PREFIXES):
                    text = rest
                    break
        else:
            break
    return text


def hydration_capable_ids(index: Mapping[str, dict]) -> set[str]:
    """Normalized ids of the entries in ``index`` that can actually hydrate.

    ``detail_cache_index`` deliberately indexes *every* parseable
    ``/decisions/`` body, including empty ones, so a caller can see them; an
    empty body is not evidence and must not be treated as "already cached" —
    that is the second half of audit R2.  Only entries carrying at least one
    ``full_text`` character are hydration-capable.
    """
    return {
        normalize_decision_id(decision_id)
        for decision_id, entry in index.items()
        if int((entry or {}).get("full_text_chars") or 0) > 0
    }


def detail_cache_index(cache_dir: Path | str | None = None) -> dict[str, dict]:
    """Map cached detail bodies by ``decision_id``.

    Only ``/decisions/...`` envelopes with a parseable body count; search and
    citation envelopes are ignored so the index cannot claim a text it does
    not have.  Partial (empty) ``full_text`` bodies are indexed with
    ``full_text_chars == 0`` and are **not** hydration-capable — pass the index
    itself to :func:`select_warm_targets` (or pre-filter it with
    :func:`hydration_capable_ids`) so those entries are treated as missing.
    Keys are the *body's* ``decision_id`` as returned upstream, which is not
    always the spelling the rendered row uses; compare through
    :func:`normalize_decision_id`, never with raw equality.
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
    existing_ids: set[str] | Mapping[str, dict],
    limit: int,
) -> list[str]:
    """Bounded, marker-first, rank-stable ids that still lack a cached body.

    ``existing_ids`` is either the index mapping returned by
    :func:`detail_cache_index` (preferred: only hydration-capable entries
    count, so an empty cached body is selected for warming rather than
    mistaken for a body) or an explicit set of already-known ids.

    Comparison is through :func:`normalize_decision_id` on BOTH sides, so a row
    spelled ``bge_BGE_119_II_147`` is recognised as the body cached under
    ``bge_119 II 147`` and is never selected again.  Returned ids are the
    rendered row ids verbatim — they are what gets requested upstream.
    """
    cap = max(0, int(limit))
    if cap == 0:
        return []
    if isinstance(existing_ids, Mapping):
        known = hydration_capable_ids(existing_ids)
    else:
        known = {normalize_decision_id(v) for v in existing_ids}
    missing = [
        row for row in rows
        if str(row.get("decision_id") or "")
        and not str(row.get("full_text") or "").strip()
        and normalize_decision_id(row.get("decision_id")) not in known
    ]
    marker_ids = [
        str(row.get("decision_id")) for row in missing
        if marker_bearing(probe_text(row))
    ]
    taken = {normalize_decision_id(v) for v in marker_ids}
    ordered = marker_ids + [
        str(row.get("decision_id")) for row in missing
        if normalize_decision_id(row.get("decision_id")) not in taken
    ]
    # Two rows can be the same decision under different spellings; keep the
    # first (rank-stable) spelling only, or the same body would be fetched twice
    # inside one leg.
    deduped: list[str] = []
    seen: set[str] = set()
    for decision_id in ordered:
        key = normalize_decision_id(decision_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(decision_id)
    return deduped[:cap]


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
    # Selection receives the index MAPPING, so only hydration-capable bodies
    # count as "already cached" (an empty body is missing) and every id is
    # compared through normalize_decision_id, so an equivalent spelling of a
    # cached body (bge_BGE_119_II_147 vs bge_119 II 147) is never fetched
    # again.  The warm pass only appends bodies the store cannot answer for;
    # it never rewrites one.
    targets = select_warm_targets(rows, existing_ids=index_before, limit=limit)
    normalized_targets = {normalize_decision_id(v) for v in targets}
    marker_targets = sum(
        1 for row in rows
        if normalize_decision_id(row.get("decision_id")) in normalized_targets
        and marker_bearing(probe_text(row))
    )
    known = hydration_capable_ids(index_before)
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
            and normalize_decision_id(row.get("decision_id")) not in known
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
