#!/usr/bin/env python3
"""Precision adjudication of the 42 -> 70 heuristic-signal reach trade.

Direction v65 ordered item 3: the accepted coverage measurement
``results/product/counter_surface_known/CYCLE_39956256289.json`` showed that
raising the cached hydration budget from 8 to 24 lifts total counter-surface
signals 42 -> 70 (+28) while known-authority signalling lifts only 8 -> 11
(+3).  That is a **reach-for-noise trade** and it was explicitly left
unadjudicated.  This module adjudicates it on the same four cached fixture
legs, with the same base bundles and the same frozen machinery the shipped
span seam already uses.  Nothing here changes a rank, budget, threshold or
frozen bar; the live/refresh budget stays 8 regardless of the outcome.

What is measured
----------------
For each offline leg:

1. rebuild the base bundle (counter-surface scan off, fixture mode, network
   blocked) exactly as ``counter_surface_known`` does;
2. scan it at cap 8 (shipped live/refresh budget) and cap 24 (cached budget);
3. partition every signalled row of the cap-24 scan into:

   * ``baseline`` - the row also carries a signal at cap 8;
   * ``delta``    - the row is signalled ONLY at cap 24 (the +28 cohort);

4. run the accepted verbatim-span confirm-or-abstain gate
   (:func:`product.query.counter_evidence_span.select_span`, precision guard
   ON for the shipped arm, OFF for the diagnostic arm) on each signalled row.

The adjudicated quantity is the **evidence yield** of each arm: the fraction
of heuristic signals whose own text carries a byte-exact span the frozen
classifier confirms.  A delta signal that no span can evidence is, for this
gate, noise; a delta signal that is confirmed is genuine reach.  This is NOT
a legal-correctness precision claim and never asserts a decision IS contrary
or limiting.

Pre-registered adjudication rule (declared here, before measurement)
-------------------------------------------------------------------
Let ``r_base`` be the baseline arm's guarded evidence yield and ``r_delta``
the delta arm's guarded evidence yield (evidenced / signals, per arm, over
all legs pooled).  The verdict is:

* ``BASELINE_UNEVIDENCED``           if ``r_base == 0`` (the gate cannot
  discriminate on this pool; no budget conclusion);
* ``BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE``
                                     if ``r_delta >= 0.5 * r_base``;
* ``BROADER_BUDGET_DOMINATED_BY_UNEVIDENCED_SIGNALS``
                                     otherwise.

The 0.5 ratio is a product adjudication constant of THIS module, published
with the raw rates; it is not a frozen bar and is never applied to anything
but this trade.  Whatever the verdict, the live/refresh budget stays 8 until
a live latency/precision measurement exists (direction v65 item 3).

Frozen-profile resolution is disclosed per leg.  The frozen rules carry five
anchor profiles; a fixture leg whose query resolves to ``None`` or to a
domain-mismatched profile is measured and PUBLISHED as such (the shipped
seam resolves the same way), and the aggregate is additionally broken out
over profile-resolved legs only, so a resolution gap can never silently
drive a rate.

Reproduction (network-free, cached fixtures, no LLM):

    python3 -m product.query.counter_precision \
        --out results/product/counter_precision/CYCLE_<run>.json
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_surface as cs  # noqa: E402
from product.query import counter_surface_known as csk  # noqa: E402
from product.query.counter_anchor import (  # noqa: E402
    _import_component,
    load_frozen_rules,
    resolve_anchor_profile,
)
from product.query.counter_evidence_span import (  # noqa: E402
    SPAN_GUARD_ENV,
    SPAN_VERSION,
    guard_terms,
    select_span,
)

SCHEMA = "product-counter-precision/1"
PRECISION_VERSION = "counter_precision/1"

#: Shipped live/refresh budget and the cached budget under adjudication.
BASELINE_CAP = cs.LIVE_HYDRATION_TOP          # 8
BROAD_CAP = cs.CACHED_HYDRATION_TOP           # 24

#: Pre-registered ratio constant (see module docstring).  Product-internal,
#: published with the raw rates; NOT a frozen bar.
MIN_DELTA_RATE_RATIO = 0.5

#: Frozen anchor key that the rent-default leg's French bail query is
#: expected to resolve to; recorded so a silent mis-resolution is visible.
PROFILE_KEY_RENT_DEFAULT = "fr-bail-entretien"
PROFILE_KEY_CORPORATE = "responsabilite-penale-entreprise-102cp"

VERDICT_PROPORTIONAL = "BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE"
VERDICT_DOMINATED = "BROADER_BUDGET_DOMINATED_BY_UNEVIDENCED_SIGNALS"
VERDICT_UNDISCRIMINATING = "BASELINE_UNEVIDENCED"


@contextlib.contextmanager
def _no_network() -> Any:
    """Fail closed during a fixture measurement (a blocked call is recorded)."""
    attempts: list[str] = []
    real_connect = socket.socket.connect

    def _blocked(self, address, *args, **kwargs):  # noqa: ANN001
        attempts.append(repr(address))
        raise AssertionError("fixture measurement attempted network access")

    socket.socket.connect = _blocked
    try:
        yield attempts
    finally:
        socket.socket.connect = real_connect


def _signalled_rows(bundle: dict) -> dict[str, dict]:
    """decision_id -> row for every row carrying a counter_surface_signal."""
    out: dict[str, dict] = {}
    for row in bundle.get("decisions") or []:
        signal = row.get("counter_surface_signal")
        if signal:
            out[str(row.get("decision_id") or "")] = row
    return out


def _adjudicate_row(
    row: dict,
    *,
    rules: Any,
    profile: dict | None,
    decide_label,
    guard: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run the accepted span gate (guarded + unguarded) on one signalled row."""
    rec: dict[str, Any] = {
        "decision_id": str(row.get("decision_id") or ""),
        "heuristic_status": (row.get("counter_surface_signal") or {}).get(
            "heuristic_status"
        ),
        "text_fields_present": [
            name for name in ("full_text", "regeste", "snippet", "title")
            if str(row.get(name) or "").strip()
        ],
    }
    if profile is None:
        rec.update({
            "guarded": {"evidenced": False, "reason_code": "no_frozen_anchor_profile"},
            "unguarded": {"evidenced": False, "reason_code": "no_frozen_anchor_profile"},
        })
        return rec
    for arm, precision_guard in (("guarded", True), ("unguarded", False)):
        sel = select_span(
            row,
            rules=rules,
            profile=profile,
            decide_label=decide_label,
            guard=guard or {},
            precision_guard=precision_guard,
        )
        rec[arm] = {
            "evidenced": bool(sel.selected),
            "reason_code": sel.reason_code,
            "field": sel.field or None,
            "quote_chars": len(sel.quote) if sel.quote else 0,
            "n_guard_rejected": sel.n_guard_rejected,
        }
    return rec


def _arm_summary(rows: Iterable[dict], arm_name: str) -> dict[str, Any]:
    rows = [r for r in rows if r.get("arm") == arm_name]
    n = len(rows)

    def _n(arm: str) -> int:
        return sum(1 for r in rows if (r.get(arm) or {}).get("evidenced"))

    reasons: dict[str, int] = {}
    for r in rows:
        code = str((r.get("guarded") or {}).get("reason_code") or "unknown")
        reasons[code] = reasons.get(code, 0) + 1
    g, u = _n("guarded"), _n("unguarded")
    return {
        "n_signals": n,
        "n_evidenced_guarded": g,
        "n_evidenced_unguarded": u,
        "evidence_yield_guarded": round(g / n, 6) if n else None,
        "evidence_yield_unguarded": round(u / n, 6) if n else None,
        "guarded_abstention_reasons": dict(sorted(reasons.items())),
    }


def measure_leg(slug: str, *, known: list[str] | None = None) -> dict[str, Any]:
    """Adjudicate one offline leg at the shipped and cached hydration caps."""
    bundle = csk._build_base_bundle(slug, top_n=csk.DEFAULT_TOP_N)  # reuse
    scans: dict[str, dict] = {}
    for cap in (BASELINE_CAP, BROAD_CAP):
        scanned = csk._scan(bundle, cap)  # reuse
        scans[str(cap)] = {
            "signalled": _signalled_rows(scanned),
            "provenance": dict((scanned.get("provenance") or {}).get(
                "counter_surface") or {}),
        }

    base_ids = set(scans[str(BASELINE_CAP)]["signalled"])
    broad_ids = set(scans[str(BROAD_CAP)]["signalled"])
    monotone = broad_ids >= base_ids

    query = str(bundle.get("query") or "")
    rules, digest = load_frozen_rules()
    profile = resolve_anchor_profile(rules, query=query)
    profile_key = next(
        (k for k, v in (getattr(rules, "anchors", {}) or {}).items() if v is profile),
        None,
    )
    decide_label, _load = _import_component()
    guard = guard_terms(profile, query) if profile is not None else {"available": False}

    rows: list[dict[str, Any]] = []
    for did in sorted(broad_ids):
        row = scans[str(BROAD_CAP)]["signalled"][did]
        rec = _adjudicate_row(
            row, rules=rules, profile=profile, decide_label=decide_label, guard=guard
        )
        rec["arm"] = "baseline" if did in base_ids else "delta"
        rows.append(rec)

    known_reached = {}
    if known:
        from product.query import known_authorities as ka

        def _lookup(signalled: dict[str, dict]) -> list[str]:
            cores = {}
            for row in signalled.values():
                for core in ka.row_id_cores(row):
                    cores.setdefault(core, row)
            hit = []
            for frozen_id in known:
                core = ka.alnum_core(frozen_id)
                if len(core) < ka.MIN_CORE_LENGTH:
                    continue
                if core in cores:
                    hit.append(frozen_id)
            return hit

        known_reached = {
            "known_n": len(known),
            "signalled_at_baseline_cap": _lookup(scans[str(BASELINE_CAP)]["signalled"]),
            "signalled_at_broad_cap": _lookup(scans[str(BROAD_CAP)]["signalled"]),
        }

    return {
        "slug": slug,
        "query": query,
        "bundle_n": len(bundle.get("decisions") or []),
        "resolved_profile_key": profile_key,
        "profile_applicable": profile is not None,
        "guard_available": bool(guard.get("available")),
        "n_signalled_baseline_cap": len(base_ids),
        "n_signalled_broad_cap": len(broad_ids),
        "n_delta_only": len(broad_ids - base_ids),
        "signals_monotone_in_cap": monotone,
        "arms": {
            "baseline": _arm_summary(rows, "baseline"),
            "delta": _arm_summary(rows, "delta"),
        },
        "known_authority_reach": known_reached or None,
        "rows": rows,
        "frozen_rules_sha256": digest,
    }


def _verdict(baseline: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    r_base = baseline.get("evidence_yield_guarded")
    r_delta = delta.get("evidence_yield_guarded")
    if not r_base:
        verdict = VERDICT_UNDISCRIMINATING
    elif r_delta is not None and r_delta >= MIN_DELTA_RATE_RATIO * r_base:
        verdict = VERDICT_PROPORTIONAL
    else:
        verdict = VERDICT_DOMINATED
    return {
        "verdict": verdict,
        "rule": (
            "BASELINE_UNEVIDENCED if baseline guarded yield == 0; "
            "BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE if delta guarded yield "
            f">= {MIN_DELTA_RATE_RATIO} * baseline; else "
            "BROADER_BUDGET_DOMINATED_BY_UNEVIDENCED_SIGNALS."
        ),
        "min_delta_rate_ratio": MIN_DELTA_RATE_RATIO,
        "baseline_yield_guarded": r_base,
        "delta_yield_guarded": r_delta,
        "budget_effect": (
            "The live/refresh budget stays 8 under direction v65 item 3 "
            "regardless of this verdict; only the cached/fixture budget is in "
            "scope, and changing it is a separate, measured decision."
        ),
    }


def measure(*, legs: Iterable[str] | None = None) -> dict[str, Any]:
    from product.query import known_authorities as ka

    fixture = ka.load_fixture(None)
    selected = list(legs) if legs else list((fixture.get("questions") or {}))
    known_by_slug = {
        slug: ka.known_ids(fixture, slug) for slug in selected
    }
    with _no_network() as attempts:
        measured = [measure_leg(slug, known=known_by_slug[slug]) for slug in selected]

    pooled: dict[str, list[dict]] = {"baseline": [], "delta": []}
    for leg in measured:
        for row in leg["rows"]:
            pooled[row["arm"]].append(row)

    baseline = _arm_summary(
        ({**r, "arm": "baseline"} for r in pooled["baseline"]), "baseline"
    )
    delta = _arm_summary(
        ({**r, "arm": "delta"} for r in pooled["delta"]), "delta"
    )
    baseline["evidence_yield_guarded"] = (
        round(baseline["n_evidenced_guarded"] / baseline["n_signals"], 6)
        if baseline["n_signals"] else None
    )
    baseline["evidence_yield_unguarded"] = (
        round(baseline["n_evidenced_unguarded"] / baseline["n_signals"], 6)
        if baseline["n_signals"] else None
    )
    delta["evidence_yield_guarded"] = (
        round(delta["n_evidenced_guarded"] / delta["n_signals"], 6)
        if delta["n_signals"] else None
    )
    delta["evidence_yield_unguarded"] = (
        round(delta["n_evidenced_unguarded"] / delta["n_signals"], 6)
        if delta["n_signals"] else None
    )

    resolved = [leg for leg in measured if leg["profile_applicable"]]
    pooled_resolved: dict[str, list[dict]] = {"baseline": [], "delta": []}
    for leg in resolved:
        for row in leg["rows"]:
            pooled_resolved[row["arm"]].append(row)
    baseline_r = _arm_summary(
        ({**r, "arm": "baseline"} for r in pooled_resolved["baseline"]), "baseline"
    )
    delta_r = _arm_summary(
        ({**r, "arm": "delta"} for r in pooled_resolved["delta"]), "delta"
    )

    return {
        "schema": SCHEMA,
        "version": PRECISION_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "fixture replay (network blocked; no live fetch; no LLM)",
        "span_version": SPAN_VERSION,
        "baseline_cap": BASELINE_CAP,
        "broad_cap": BROAD_CAP,
        "reference_coverage_artifact": (
            "results/product/counter_surface_known/CYCLE_39956256289.json"
        ),
        "reference_counts": {
            "signals_at_8": 42,
            "signals_at_24": 70,
            "known_signalled_at_8": 8,
            "known_signalled_at_24": 11,
        },
        "profile_resolution_disclosure": {
            "note": (
                "The frozen rules carry five anchor profiles. Each leg's "
                "resolved profile key is published; a leg resolving to None "
                "or to a domain-mismatched profile is still measured (the "
                "shipped seam resolves identically) and is visible per leg."
            ),
            "per_leg": {
                leg["slug"]: leg["resolved_profile_key"] for leg in measured
            },
        },
        "invariants": {
            "network_calls_blocked": len(attempts) == 0,
            "network_attempts": attempts,
            "signals_monotone_in_cap": all(
                leg["signals_monotone_in_cap"] for leg in measured
            ),
            "same_base_bundle_across_caps": True,
            "budgets_unchanged": (
                BASELINE_CAP == cs.LIVE_HYDRATION_TOP
                and BROAD_CAP == cs.CACHED_HYDRATION_TOP
            ),
        },
        "legs": measured,
        "aggregate": {
            "pooled_all_legs": {"baseline": baseline, "delta": delta},
            "pooled_profile_resolved_legs_only": {
                "leg_slugs": [leg["slug"] for leg in resolved],
                "baseline": baseline_r,
                "delta": delta_r,
            },
            "known_authority_reach": {
                "at_baseline_cap": sum(
                    len((leg["known_authority_reach"] or {}).get(
                        "signalled_at_baseline_cap") or [])
                    for leg in measured
                ),
                "at_broad_cap": sum(
                    len((leg["known_authority_reach"] or {}).get(
                        "signalled_at_broad_cap") or [])
                    for leg in measured
                ),
            },
            "adjudication": _verdict(baseline, delta),
        },
        "interpretation": (
            "Each heuristic counter-surface signal is tested for whether the "
            "row's own text carries a byte-exact span the frozen "
            "confirm-or-abstain classifier accepts under the shipped precision "
            "guard. The delta arm (signals the cached budget 24 adds beyond "
            "the shipped budget 8) is compared with the baseline arm. This "
            "adjudicates evidence yield, not legal correctness."
        ),
        "claim_ceiling": (
            "Product-owned adjudication of one cached-budget trade on four "
            "cached fixture legs. Evidence yield = fraction of heuristic "
            "signals with a frozen-gate-confirmed verbatim span. NOT a legal "
            "precision/recall claim, NOT an evaluation verdict, NOT a serve or "
            "admission input, and it never asserts a decision IS supporting, "
            "contrary or limiting. The 0.5 ratio constant belongs to this "
            "module and applies only to this adjudication. No network, no "
            "frozen bar, no threshold change."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--legs", nargs="+", default=None,
                    help="subset of fixture slugs (default: all)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    out = measure(legs=args.legs)
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    agg = out["aggregate"]
    print(json.dumps({
        "out": str(args.out) if args.out else None,
        "adjudication": agg["adjudication"],
        "pooled": agg["pooled_all_legs"],
        "known_reach": agg["known_authority_reach"],
        "invariants": out["invariants"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
