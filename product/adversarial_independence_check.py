#!/usr/bin/env python3
"""Measure a product bundle with the ACCEPTED frontier adversarial-discoverability metrics.

Why this exists
---------------
``frontier-adversarial-discoverability`` measured the product's counter-authority
pass on three accepted bundles and returned the named verdict
``CLASSIFICATION_ONLY``: every counter row had entered through a channel the
initial broad retrieval had already used, so the map could not reveal anything the
conventional ranked list had not already shown at the top.

That verdict was correct at the time.  This tool re-runs the SAME accepted,
audited metric functions (``adversarial_discoverability.metrics`` /
``.populations``) against a bundle the product produced AFTER the independent
adversarial retrieval pass landed, so the flip from ``CLASSIFICATION_ONLY`` to a
retrieval-independent pass is measured by the accepting team's own code rather
than by the team that wrote the fix.

The frontier harness is read as a library only: no metric, threshold, population
or verdict rule is re-implemented here, and nothing under ``frontier/**`` is
written.  If the accepted mount is missing the tool refuses to score rather than
falling back to a private re-implementation, because a self-scored metric is
exactly the kind of evidence the factory forbids.

Usage::

    python product/adversarial_independence_check.py --bundle <bundle.json>
    python product/adversarial_independence_check.py --bundle <b.json> --json out.json

Exit codes: 0 metrics ran, 3 accepted mount missing, 4 bundle unreadable/invalid.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the workflow mounts accepted frontier teams.  Overridable so the check
#: can be re-run against any accepted checkout of the team.
DEFAULT_MOUNT = Path(os.environ.get(
    "LEX_FRONTIER_ADVERSARIAL_MOUNT",
    "/tmp/lex_accepted/frontier/frontier-adversarial-discoverability",
))

TEAM_PACKAGE = DEFAULT_MOUNT / "frontier" / "frontier-adversarial-discoverability"

METRIC_ORDER = ("a_counter_yield", "b_marginal_retrieval_contribution",
                "c_rank_placement", "d_placement_visibility")

#: The verdict the accepted audit named for the pre-fix bundles.  Recorded in the
#: output so the comparison is explicit and cannot be read as a fresh claim.
PRE_FIX_VERDICT = "CLASSIFICATION_ONLY"


def _load_accepted():
    if not (TEAM_PACKAGE / "adversarial_discoverability" / "metrics.py").is_file():
        raise SystemExit(
            f"accepted frontier mount not found at {TEAM_PACKAGE}\n"
            "This tool scores with the ACCEPTED team's own metric functions and "
            "refuses to substitute a private re-implementation (exit 3)."
        )
    sys.path.insert(0, str(TEAM_PACKAGE))
    from adversarial_discoverability import metrics as M  # noqa: E402
    from adversarial_discoverability import populations as pop  # noqa: E402
    from adversarial_discoverability import __version__ as metric_defs  # noqa: E402
    from adversarial_discoverability import CHARTER_VERSION  # noqa: E402
    return M, pop, {"metric_definitions": metric_defs, "charter_version": CHARTER_VERSION}


def score(bundle: dict) -> dict:
    M, pop, provenance = _load_accepted()
    rows = pop.decisions_of(bundle)
    metrics = {
        "a_counter_yield": M.metric_a_counter_yield,
        "b_marginal_retrieval_contribution": M.metric_b_marginal_retrieval,
        "c_rank_placement": M.metric_c_rank_placement,
        "d_placement_visibility": M.metric_d_placement,
    }
    out_metrics = {}
    for name in METRIC_ORDER:
        m = metrics[name](bundle, rows)
        out_metrics[name] = {
            "verdict": m.get("verdict"),
            "applicability": m.get("applicability"),
            "value": m.get("value"),
            "threshold": m.get("threshold"),
        }
        if name == "b_marginal_retrieval_contribution":
            out_metrics[name].update({
                "b1_adversarial_channel_rows": m.get("b1_adversarial_channel_rows"),
                "b1_rows": m.get("b1_rows"),
                "b2_new_channels": m.get("b2_new_channels"),
                "initial_channel_set": m.get("initial_channel_set"),
            })
        if name == "c_rank_placement":
            out_metrics[name].update({
                "counter_ranks": m.get("counter_ranks"),
                "beyond_top20_share": m.get("beyond_top20_share"),
            })
        if name == "d_placement_visibility":
            out_metrics[name].update({
                "discoverable_placement_share": m.get("discoverable_placement_share"),
                "is_outlier_share": m.get("is_outlier_share"),
                "distinct_cluster_share": m.get("distinct_cluster_share"),
                "consensus_cluster_id": m.get("consensus_cluster_id"),
                "consensus_cluster_size": m.get("consensus_cluster_size"),
            })

    # The charter's named-verdict precedence: metric (b) decides retrieval
    # independence, so reproduce that rule here rather than inventing a new one.
    b_verdict = out_metrics["b_marginal_retrieval_contribution"]["verdict"]
    independence = "INDEPENDENT_RETRIEVAL" if b_verdict == "PASS" else PRE_FIX_VERDICT

    adv_prov = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    return {
        "scored_with": {
            "team": "frontier-adversarial-discoverability",
            "accepted_mount": str(DEFAULT_MOUNT),
            "metric_definitions": provenance["metric_definitions"],
            "charter_version": provenance["charter_version"],
            "note": "metric functions are imported from the accepted mount; nothing re-implemented",
        },
        "bundle": {
            "n_decisions": len(rows),
            "n_clusters": len(bundle.get("clusters") or []),
            "query": bundle.get("query"),
            "adversarial_retrieval": {
                k: adv_prov.get(k) for k in (
                    "component", "attempted", "degraded", "skip_reason", "n_new_rows",
                    "n_counter_rows", "channels", "pool_never_seen_rate", "n_hydrated",
                    "counter_status_histogram", "error",
                ) if adv_prov.get(k) is not None
            },
        },
        "metrics": out_metrics,
        "verdict": {
            "retrieval_independence": independence,
            "governing_metric": "b_marginal_retrieval_contribution",
            "pre_fix_verdict_on_accepted_bundles": PRE_FIX_VERDICT,
            "all_metrics_pass": all(out_metrics[n]["verdict"] == "PASS" for n in METRIC_ORDER),
        },
        "claim_ceiling": (
            "these are the accepted team's own frozen metrics applied to one bundle; "
            "they describe that bundle only and do not generalise to untested queries"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", required=True, help="query_result_bundle JSON")
    ap.add_argument("--json", default="", help="write the full result here")
    args = ap.parse_args(argv)
    path = Path(args.bundle)
    if not path.is_file():
        print(f"bundle not found: {path}", file=sys.stderr)
        return 4
    bundle = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(bundle.get("decisions"), list) or not bundle["decisions"]:
        print("bundle carries no decisions", file=sys.stderr)
        return 4
    try:
        result = score(bundle)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 3
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    print(json.dumps(result["metrics"], ensure_ascii=False, sort_keys=True))
    print(json.dumps(result["verdict"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())