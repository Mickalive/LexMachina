#!/usr/bin/env python3
"""How much of the surfaced counter set is a function of the REQUEST BUDGET?

Why this module exists (factory direction v54, backlog item 3(c))
-----------------------------------------------------------------
The gate packet is rebuilt in a run with a request budget, and the number of
counter-authority rows it ships is disclosed per question.  That disclosure
answers the wrong question if the *identity* of the rows is itself budget
dependent: the audit of run 38828034436 compared two live bundles that differed
only in request budget and found an overlap of **1 row out of 27 and 37
adversarial rows** (audit advisory 3).  A jurist told "this bundle surfaces 27
counter rows" reasonably concludes that the map's contrary-authority coverage is
27 decisions wide.  If a smaller budget yields a *different* 27, that number is
a property of the budget, not of the case law, and the packet has to say so.

What is measured, and what is not
---------------------------------
One variable is changed and nothing else: :func:`fetch_adversarial_candidates`
is called twice with the same plan, the same exclusions, the same cache and the
same ``max_new``/``page_size``, and only ``max_requests`` differs.  The budget is
consumed by :meth:`OCLClient._call` *before* the cache is consulted, so a warm
cache does not soften the difference and the two runs are comparable by
construction rather than by hope.

The measurement is a **disclosure, never a verdict**.  It says how much of the
surfaced set survives a smaller budget.  It does not say which budget is
"correct", it does not tune anything, and it never changes a frozen threshold.
Nothing here gates a bundle.

Usage
-----
    python -m product.query.counter_budget_sensitivity \
        --bundle results/product/gate_packet/<run>/questions/<qid>.bundle.json
        --out results/product/counter_budget_sensitivity/<run>/<qid>.json

    # offline/fixture mode replays the frozen envelopes instead of the network
    python -m product.query.counter_budget_sensitivity --bundle <b> --mode fixture
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

from product.query.adversarial_retrieval import (  # noqa: E402
    DEFAULT_MAX_REQUESTS,
    apply_adversarial_pass,
    fetch_adversarial_candidates,
    plan_adversarial_queries,
)

SCHEMA = "product-counter-budget-sensitivity/1"

#: Budgets compared by default.  The low value is deliberately small enough that
#: the hydration phase is cut off while all four probes still run, which is the
#: regime a rate-limited or time-boxed owner session actually runs in.
FULL_BUDGET = DEFAULT_MAX_REQUESTS
REDUCED_BUDGET = 8

NON_COUNTER_STATUSES = frozenset({"none", "", None, "unclassified", "supporting-candidate", "context"})


def _strip_adversarial_rows(bundle: dict) -> dict:
    """Restore the initial population so only the budget differs between runs."""
    initial = copy.deepcopy(bundle)
    initial["decisions"] = [d for d in initial.get("decisions") or []
                            if not d.get("adversarial_channel")]
    prov = initial.setdefault("provenance", {})
    prov.pop("adversarial_retrieval", None)
    return initial


def _exclusions(initial: dict) -> tuple[set[str], set[tuple[str, str]]]:
    ids = {str(d.get("decision_id")) for d in initial.get("decisions") or []}
    identities: set[tuple[str, str]] = set()
    for d in initial.get("decisions") or []:
        docket = str(d.get("docket_number") or "").strip()
        if docket:
            identities.add((str(d.get("court") or "").strip().lower(),
                            re.sub(r"[^a-z0-9]", "", docket.lower())))
    return ids, identities


def _counter_ids(bundle: dict) -> list[str]:
    return sorted(
        str(d.get("decision_id"))
        for d in bundle.get("decisions") or []
        if str(d.get("counter_status") or "none") not in NON_COUNTER_STATUSES
    )


def _run(initial: dict, query: str, plan: list[dict], *, budget: int, mode: str) -> dict:
    exclude_ids, exclude_identities = _exclusions(initial)
    fetched = fetch_adversarial_candidates(
        query, plan, mode=mode, exclude_ids=exclude_ids,
        exclude_identities=exclude_identities, max_requests=budget,
    )
    applied = apply_adversarial_pass(
        initial, list(fetched.get("candidates") or []), fetched.get("provenance")
    )
    prov = fetched.get("provenance") or {}
    return {
        "budget": budget,
        "adversarial_rows": len(fetched.get("candidates") or []),
        "hydrated_ids": list(prov.get("hydrated_ids") or []),
        "counter_ids": _counter_ids(applied),
        "probes": [
            {"intent": p.get("intent"), "new_rows": p.get("new_rows"), "error": p.get("error")}
            for p in prov.get("probes") or []
        ],
        "request_summary": prov.get("request_summary"),
        "failures": prov.get("failures") or [],
    }


def compare_counter_sets(full_ids: list[str], reduced_ids: list[str]) -> dict:
    """Pure overlap arithmetic, so the disclosure cannot drift from its meaning."""
    a, b = set(full_ids or ()), set(reduced_ids or ())
    union = a | b
    return {
        "full_n": len(a),
        "reduced_n": len(b),
        "overlap": sorted(a & b),
        "overlap_n": len(a & b),
        "only_in_full": sorted(a - b),
        "only_in_reduced": sorted(b - a),
        "union_n": len(union),
        "jaccard": round(len(a & b) / len(union), 4) if union else None,
        "full_retained_by_reduced_budget": (round(len(a & b) / len(a), 4) if a else None),
    }


def measure(bundle: dict, *, mode: str = "live",
            full_budget: int = FULL_BUDGET, reduced_budget: int = REDUCED_BUDGET) -> dict:
    """Run the same adversarial pass at two budgets and compare the counter sets."""
    query = str(bundle.get("query") or "")
    prose = str((bundle.get("answer") or {}).get("prose") or "")
    plan = plan_adversarial_queries(query, prose)
    if not plan:
        # D4's vacuous-pass guard: an answer with no usable vocabulary yields no
        # probes, so there is no counter set whose budget dependence could be
        # measured.  Recorded as skipped, never as "no budget dependence".
        return {
            "schema": SCHEMA,
            "skipped": True,
            "skip_reason": "the answer carries no usable vocabulary, so the adversarial plan is "
                           "empty (adversarial_retrieval/2 D4 guard) and there is no counter set "
                           "to compare",
            "query": query,
            "n_probes": 0,
        }
    initial = _strip_adversarial_rows(bundle)
    full = _run(initial, query, plan, budget=int(full_budget), mode=mode)
    reduced = _run(initial, query, plan, budget=int(reduced_budget), mode=mode)
    return {
        "schema": SCHEMA,
        "skipped": False,
        "query": query,
        "n_probes": len(plan),
        "initial_decisions": len(initial.get("decisions") or []),
        "full": full,
        "reduced": reduced,
        "counter_set": compare_counter_sets(full["counter_ids"], reduced["counter_ids"]),
        "interpretation": (
            "The two runs differ only in max_requests; the plan, exclusions, cache and page size "
            "are identical, and the budget is consumed before the cache is consulted. A low "
            "overlap means the identity of the surfaced counter set - not merely its size - is a "
            "property of the request budget, so the per-question counter count must be read as "
            "'what this run surfaced', never as 'how much contrary authority exists'."
        ),
        "claim_ceiling": (
            "Measured on one bundle, one query and two budget settings of the product's own "
            "adversarial route. It is a disclosure about this artifact, not a bound on recall, "
            "and it tunes nothing."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle", type=Path, help="query_result_bundle json")
    ap.add_argument("--mode", choices=("live", "fixture", "offline"), default="live")
    ap.add_argument("--full-budget", type=int, default=FULL_BUDGET)
    ap.add_argument("--reduced-budget", type=int, default=REDUCED_BUDGET)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    out = measure(bundle, mode=args.mode, full_budget=args.full_budget,
                  reduced_budget=args.reduced_budget)
    out["bundle_path"] = str(args.bundle)
    out["bundle_content_sha256"] = __import__("hashlib").sha256(
        json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())