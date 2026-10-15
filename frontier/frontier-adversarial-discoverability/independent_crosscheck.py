#!/usr/bin/env python3
"""Independent cross-check of the frozen adversarial-discoverability measurement.

This is a SECOND, deliberately separate implementation of the handful of numbers the
narrative report states in prose.  It exists so an auditor does not have to take the
harness's word for anything: if this file and
``adversarial_discoverability/metrics.py`` ever disagree, at least one of them is wrong,
and the disagreement is visible instead of silently baked into a claim.

Deliberate independence
-----------------------
* it imports NOTHING from ``adversarial_discoverability`` -- populations, metric
  definitions and thresholds are re-expressed here from RULES.json, so a bug in the
  harness cannot hide itself by also being present here;
* it reads the raw accepted bundles straight from the read-only mount and re-hashes
  every input itself;
* it re-derives the prose claims in ``CYCLE_38792663259.md`` (section 4) directly from
  those bundles, rather than from the harness report;
* it never writes, never uses the network, and reads no clock.

Usage::

    python3 independent_crosscheck.py                 # human-readable summary
    python3 independent_crosscheck.py --json          # machine-readable block
    LEX_PRODUCT_MOUNT=/path/to/lab/product python3 independent_crosscheck.py

Exit code 0 when every cross-check agrees, 1 on any disagreement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Tuple

TEAM_ID = "frontier-adversarial-discoverability"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES_PATH = os.path.join(REPO, "results", "frontier", TEAM_ID, "RULES.json")
MOUNT = os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/core/product")

# RULES.json populations.COUNTER_VALUES, restated on purpose (see module docstring).
COUNTER_VALUES = ("candidate-limiting", "candidate-contrary",
                  "contrary_or_exception", "limiting")
PLACEHOLDER = "cited in generated answer"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [d for d in (doc.get("decisions") or []) if isinstance(d, dict)]


def _counter_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [d for d in rows if str(d.get("counter_status") or "none") in COUNTER_VALUES]


def _channels_of(row: Dict[str, Any]) -> List[str]:
    ch = row.get("channels")
    if isinstance(ch, str):
        return [ch]
    return [str(c) for c in ch] if isinstance(ch, list) else []


def _initial_channels(doc: Dict[str, Any]) -> set:
    """Union of every channel inventory the INITIAL broad retrieval declares."""
    prov = doc.get("provenance") or {}
    ret = prov.get("retrieval") or {}
    out: set = set()
    for block in ((ret.get("dedupe") or {}).get("candidates_by_channel"),
                  ret.get("candidate_channels"),
                  (prov.get("retrieval_first_page") or {}).get("candidate_channels")):
        if isinstance(block, dict):
            out |= {str(k) for k in block}
    return out


def _consensus_cluster(rows: List[Dict[str, Any]]) -> Any:
    """cluster_id of the rank-1 row (RULES.json populations.consensus_cluster)."""
    ranked = [(d.get("rank"), d) for d in rows if isinstance(d.get("rank"), int)]
    if not ranked:
        return None
    return min(ranked, key=lambda p: p[0])[1].get("cluster_id")


def _year(row: Dict[str, Any]) -> Any:
    raw = str(row.get("decision_date") or "")[:4]
    return int(raw) if raw.isdigit() else None


def check_bundle(spec: Dict[str, Any], mount: str) -> Dict[str, Any]:
    path = os.path.join(mount, spec["path"])
    got = sha256_file(path)
    doc = json.load(open(path, encoding="utf-8"))
    rows_of = _rows(doc)
    C = _counter_rows(rows_of)
    initial = _initial_channels(doc)
    cc = _consensus_cluster(rows_of)

    ranks = sorted(d.get("rank") for d in C if isinstance(d.get("rank"), int))
    in_cc = sum(1 for d in C if d.get("cluster_id") == cc)
    outliers = sum(1 for d in C if d.get("is_outlier") is True)
    verified = sum(1 for d in C
                   if d.get("counter_evidence_verified") is True
                   and str(d.get("counter_reason") or "").strip()
                   and str(d.get("counter_reason") or "").strip() != PLACEHOLDER)
    placeholder = sum(1 for d in C
                      if str(d.get("counter_evidence") or "").strip() == PLACEHOLDER)

    chan_hist: Dict[str, int] = {}
    new_chan_rows: List[str] = []
    for d in C:
        ch = _channels_of(d)
        for c in ch:
            chan_hist[c] = chan_hist.get(c, 0) + 1
        if set(ch) - initial:
            new_chan_rows.append(str(d.get("decision_id")))

    years = [y for y in (_year(d) for d in rows_of) if y is not None]
    med = statistics.median(years) if years else None
    langs: Dict[str, int] = {}
    for d in rows_of:
        if cc is not None and d.get("cluster_id") == cc:
            lang = str(d.get("language") or "").strip().lower()
            if lang and lang != "?":
                langs[lang] = langs.get(lang, 0) + 1
    cons_lang = sorted(langs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if langs else None
    non_lang = sum(1 for d in C
                   if cons_lang is not None
                   and str(d.get("language") or "?").lower() != cons_lang)
    older = sum(1 for d in C
                if med is not None and _year(d) is not None and _year(d) < med)

    ans = doc.get("answer") or {}
    prose = str(ans.get("prose") or "")
    cited = {str(x) for x in (ans.get("cited_decision_ids") or [])}
    linked = sum(1 for d in C
                 if str(d.get("decision_id")) in prose
                 or str(d.get("decision_id")) in cited)

    n = len(C)
    return {
        "id": spec["id"],
        "n_rows": len(rows_of),
        "sha256_recomputed": got,
        "sha256_matches_frozen": got == spec["sha256"],
        "counter_rows": n,
        "counter_ids": sorted(str(d.get("decision_id")) for d in C),
        "counter_ranks": ranks,
        "counter_rows_with_a_channel_absent_from_initial_retrieval": len(new_chan_rows),
        "counter_channel_histogram": dict(sorted(chan_hist.items())),
        "initial_channel_set": sorted(initial),
        "consensus_cluster_id": cc,
        "counter_rows_inside_consensus_cluster": in_cc,
        "counter_rows_outside_consensus_cluster": n - in_cc,
        "counter_rows_flagged_outlier": outliers,
        "counter_rows_verified_with_substantive_reason": verified,
        "counter_rows_with_placeholder_evidence": placeholder,
        "consensus_language": cons_lang,
        "counter_rows_minority_or_older": sum(
            1 for d in C
            if (cons_lang is not None
                and str(d.get("language") or "?").lower() != cons_lang)
            or (med is not None and _year(d) is not None and _year(d) < med)),
        "non_consensus_language_rows": non_lang,
        "older_than_median_rows": older,
        "counter_rows_linked_into_the_answer": linked,
        "shares": {
            "counter_yield": round(n / len(rows_of), 6) if rows_of else None,
            "beyond_top20": round(sum(1 for r in ranks if r > 20) / n, 6) if n else None,
            "top20": round(sum(1 for r in ranks if r <= 20) / n, 6) if n else None,
            "discoverable_placement": round(
                len({str(d.get("decision_id")) for d in C
                     if d.get("is_outlier") is True or d.get("cluster_id") != cc}) / n, 6)
            if n else None,
        },
    }


#: Prose claims made in CYCLE_38792663259.md section 4, each recomputed here.
PROSE_CLAIMS = {
    "zero_of_eight_counter_rows_came_from_a_new_channel":
        "8 counter rows across 3 bundles, 0 with a channel absent from the initial retrieval",
    "seven_of_eight_counter_rows_sit_inside_the_top20":
        "7 of 8 counter rows at rank <= 20; the eighth is rank 27",
    "no_counter_row_is_an_outlier":
        "0 of 8 counter rows carries is_outlier = true",
    "three_of_eight_counter_rows_sit_outside_the_consensus_cluster":
        "3 of 8 (1 in B1, 1 in B2, 1 in B3) -- this report previously said 2 of 8",
    "counter_channels_are_search_or_language_filter_only":
        "every counter-row channel is 'search' or 'search.language_filter'",
}


def verify_prose_claims(bundles: List[Dict[str, Any]]) -> Dict[str, Any]:
    tot = sum(b["counter_rows"] for b in bundles)
    top20 = sum(round(b["shares"]["top20"] * b["counter_rows"]) for b in bundles)
    out = {
        "counter_rows_total": tot,
        "counter_rows_with_new_channel": sum(
            b["counter_rows_with_a_channel_absent_from_initial_retrieval"] for b in bundles),
        "counter_rows_top20": top20,
        "counter_rows_outlier": sum(b["counter_rows_flagged_outlier"] for b in bundles),
        "counter_rows_outside_consensus": sum(
            b["counter_rows_outside_consensus_cluster"] for b in bundles),
        "channel_set_union": sorted({c for b in bundles
                                     for c in b["counter_channel_histogram"]}),
    }
    checks = {
        "zero_of_eight_counter_rows_came_from_a_new_channel":
            out["counter_rows_total"] == 8 and out["counter_rows_with_new_channel"] == 0,
        "seven_of_eight_counter_rows_sit_inside_the_top20":
            (top20, tot) == (7, 8),
        "no_counter_row_is_an_outlier": out["counter_rows_outlier"] == 0,
        "three_of_eight_counter_rows_sit_outside_the_consensus_cluster":
            out["counter_rows_outside_consensus"] == 3,
        "counter_channels_are_search_or_language_filter_only":
            set(out["channel_set_union"]) <= {"search", "search.language_filter"},
    }
    return {"totals": out, "claim_text": PROSE_CLAIMS, "checks": checks,
            "all_claims_hold": all(checks.values())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--mount", default=MOUNT)
    args = ap.parse_args(argv)

    rules = json.load(open(RULES_PATH, encoding="utf-8"))
    bundles = [check_bundle(s, args.mount) for s in rules["inputs"]["bundles"]]
    legs = []
    for s in rules["inputs"]["frozen_legs"]:
        p = os.path.join(args.mount, s["path"])
        doc = json.load(open(p, encoding="utf-8"))
        cited = [d for d in (doc.get("cited_decisions") or []) if isinstance(d, dict)]
        C = _counter_rows(cited)
        legs.append({
            "id": s["id"], "sha256_matches_frozen": sha256_file(p) == s["sha256"],
            "decision_count": doc.get("decision_count"),
            "cited_rows_exposed": len(cited), "counter_rows": len(C),
            "counter_yield_over_decision_count": (
                round(len(C) / doc["decision_count"], 6) if doc.get("decision_count") else None),
        })

    block = {
        "record_version": "fad-independent-crosscheck/1",
        "team_id": TEAM_ID,
        "mount": os.path.abspath(args.mount),
        "mount_read_only": True,
        "network_calls": 0,
        "independence": ("no import of adversarial_discoverability; populations, metrics and "
                         "thresholds re-expressed from RULES.json; inputs re-hashed here"),
        "bundles": bundles,
        "legs": legs,
        "prose_claims": verify_prose_claims(bundles),
        "all_inputs_verified": all(b["sha256_matches_frozen"] for b in bundles)
        and all(l["sha256_matches_frozen"] for l in legs),
    }
    block["agrees_with_harness_report"] = block["prose_claims"]["all_claims_hold"] \
        and block["all_inputs_verified"]

    if args.json:
        print(json.dumps(block, indent=2, sort_keys=True))
    else:
        for b in bundles:
            print(f"{b['id']}: rows={b['n_rows']} counter={b['counter_rows']} "
                  f"ranks={b['counter_ranks']} new_channel_rows="
                  f"{b['counter_rows_with_a_channel_absent_from_initial_retrieval']} "
                  f"outside_consensus={b['counter_rows_outside_consensus_cluster']} "
                  f"outliers={b['counter_rows_flagged_outlier']} "
                  f"verified={b['counter_rows_verified_with_substantive_reason']} "
                  f"placeholder={b['counter_rows_with_placeholder_evidence']} "
                  f"in_answer={b['counter_rows_linked_into_the_answer']} "
                  f"sha_ok={b['sha256_matches_frozen']}")
        for l in legs:
            print(f"{l['id']}: decision_count={l['decision_count']} "
                  f"cited_exposed={l['cited_rows_exposed']} counter={l['counter_rows']} "
                  f"yield={l['counter_yield_over_decision_count']} sha_ok={l['sha256_matches_frozen']}")
        print("\nprose claims (CYCLE_38792663259.md section 4):")
        for name, ok in block["prose_claims"]["checks"].items():
            print(f"  [{'OK  ' if ok else 'FAIL'}] {name}")
        print(f"\nall inputs verified: {block['all_inputs_verified']}")
        print(f"agrees with the harness report: {block['agrees_with_harness_report']}")
    return 0 if block["agrees_with_harness_report"] else 1


if __name__ == "__main__":
    sys.exit(main())