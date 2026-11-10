#!/usr/bin/env python3
"""
Minimal vertical slice for the LexMachina query-map MVP.

Demonstrates the shortest runnable path:
  question -> OpenCaseLaw retrieval -> query_result_bundle -> rerank -> sourced answer
  -> independent counter-authority pass -> query-specific clickable map.

This is a standalone script (no server required). It exercises the same
code paths as the product server /api/query/* endpoints.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure product package is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PRODUCT_ROOT = Path(__file__).resolve().parent
for _import_root in (_PRODUCT_ROOT, _REPO_ROOT):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

# Add frontier team namespace for product_compat shim (needs to be before product import)
_SYS_PATH_FRONTIER = str(_REPO_ROOT / "frontier" / "frontier-query-map-ui" / "src")
if _SYS_PATH_FRONTIER not in sys.path:
    sys.path.insert(0, _SYS_PATH_FRONTIER)

from product_compat import install  # noqa: E402 (installs _status_counts shim)
install()

from product.query.pipeline import run_query_initial, enrich_query_bundle  # noqa: E402
from product.query.answer import build_answer, counter_authority_pass  # noqa: E402
from product.query.bundle import annotate_content_state, validate_bundle, bundle_summary  # noqa: E402
from query_bundle_adapter import adapt_bundle_to_visualization  # noqa: E402 (frontier adapter reuse)


def run_minimal_slice(query: str, top_n: int = 120, max_cites: int = 8,
                      mode: str = "live", with_bundle: bool = False):
    """Execute the full vertical slice and return the visualization-ready data.

    ``mode`` is the pipeline retrieval mode: ``live`` (OpenCaseLaw, cache
    assisted), ``offline`` (cache-only, never touches the network) or
    ``fixture`` (frozen envelopes, deterministic).  The offline/fixture modes
    make the slice reproducible under an armed socket trap.
    """
    if mode not in {"live", "offline", "fixture"}:
        raise ValueError(f"unsupported retrieval mode: {mode}")

    # --- Phase 1: Initial retrieval + map (run_query_initial) ---
    print(f"=== Phase 1: Retrieval + map (query='{query}', top_n={top_n}, "
          f"mode={mode}) ===")
    initial = run_query_initial(query, top_n=top_n, retrieval_mode=mode)
    print(f"  Decisions: {len(initial.get('decisions', []))}")
    print(f"  Clusters: {len(initial.get('clusters', []))}")
    print(f"  Answer status: {initial.get('answer', {}).get('status', 'pending')}")

    # --- Phase 2: Build sourced answer ---
    print("\n=== Phase 2: Build sourced answer ===")
    ranked = sorted(initial["decisions"], key=lambda d: d.get("rank") or 10**9)
    answer = build_answer(query, ranked, max_cites=max_cites)
    initial["answer"] = answer
    print(f"  Prose: {answer['prose'][:80]}...")
    print(f"  Cited IDs: {answer['cited_decision_ids']}")

    # --- Phase 3: Independent counter-authority pass ---
    print("\n=== Phase 3: Counter-authority pass ===")
    texts_by_id = {
        d["decision_id"]: d.get("full_text") or d.get("regeste") or d.get("snippet", "")
        for d in initial["decisions"]
    }
    counter_hits, counter_info = counter_authority_pass(
        query, ranked, texts_by_id, top_k=max_cites
    )
    print(f"  Counter hits: {len(counter_hits)}")
    for h in counter_hits[:3]:
        print(f"    {h['decision_id']}: status={h['counter_status']} "
              f"markers={h['markers']}")

    # Assign counter_status to every decision in the bundle
    cited_set = set(answer.get("cited_decision_ids", []))
    for d in initial["decisions"]:
        did = d["decision_id"]
        if did in cited_set:
            d["counter_status"] = "cited"
            d["counter_evidence_verified"] = True
        else:
            counter_hit = next(
                (h for h in counter_hits if h["decision_id"] == did), None
            )
            if counter_hit:
                d["counter_status"] = counter_hit["counter_status"]
                d["counter_evidence"] = counter_hit.get("evidence_sentence", "")
                d["counter_uncertainty"] = counter_hit.get("adversarial_score", 0)
            else:
                d["counter_status"] = "none"
                d["counter_evidence_verified"] = False

    # --- Phase 4: Content state annotation ---
    print("\n=== Phase 4: Content state annotation ===")
    annotate_content_state(initial)
    errors = validate_bundle(initial)
    if errors:
        print(f"  VALIDATION ERRORS: {errors}")
    else:
        print("  Bundle validation: OK")
    summary = bundle_summary(initial)
    print(f"  Summary: {summary}")

    # --- Phase 5: Adapt bundle for visualization ---
    print("\n=== Phase 5: Adapt to visualization format ===")
    viz = adapt_bundle_to_visualization(initial)
    print(f"  Decisions: {viz['n_decisions']}")
    print(f"  Clusters: {viz['n_clusters']}")
    print(f"  Relations: {viz['n_relations']}")
    print(f"  Counter authorities: {viz['n_counter']}")
    print(f"  Cited decisions: {viz['n_cited']}")
    print(f"  Outliers: {viz['n_outliers']}")
    print(f"  Languages: {viz['languages']}")
    print(f"  Bounds: {viz['bounds']}")

    # --- Phase 6: Output ---
    print("\n=== Output ===")
    output = {
        "query": initial["query"],
        "retrieval_mode": mode,
        "decision_ids": [d["decision_id"] for d in initial["decisions"]],
        "summary": summary,
        "visualization": {
            "n_decisions": viz["n_decisions"],
            "n_clusters": viz["n_clusters"],
            "n_relations": viz["n_relations"],
            "n_counter": viz["n_counter"],
            "n_cited": viz["n_cited"],
            "n_outliers": viz["n_outliers"],
            "languages": viz["languages"],
            "bounds": viz["bounds"],
        },
        "answer": {
            "prose": answer["prose"],
            "cited_decision_ids": answer["cited_decision_ids"],
            "method": answer["method"],
        },
        "counter_info": {
            "n_counter_authorities": counter_info["n_candidates"],
            "method": counter_info["method"],
        },
        "stages": {
            "retrieval": True,
            "map": True,
            "answer": answer.get("prose") != "" or len(answer.get("cited_decision_ids", [])) > 0,
            "counter_authority": len(counter_hits) > 0,
        },
    }

    # Print JSON output
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if with_bundle:
        # Preserve the full query_result_bundle (decisions with x/y/cluster/
        # source links, answer, counter status, provenance) instead of only
        # the compact visualization summary.  This is what the clickable map
        # and any downstream audit consume; the summary alone cannot render.
        return output, initial
    return output


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="LexMachina minimal vertical slice"
    )
    parser.add_argument("query", nargs="?", default="Kundigung Mietvertrag Mietrecht",
                        help="Swiss legal research question")
    parser.add_argument("--n", type=int, default=120, help="target decisions (100-300)")
    parser.add_argument("--cites", type=int, default=8, help="max citations in answer")
    parser.add_argument("--mode", choices=("live", "offline", "fixture"),
                        default="live",
                        help="retrieval mode: live (network), offline "
                             "(cache-only, network-free), fixture (frozen)")
    parser.add_argument("--out", type=str, default=None,
                        help="Write visualization JSON to file")
    parser.add_argument("--bundle-out", type=str, default=None,
                        help="Write the full query_result_bundle JSON to file")
    args = parser.parse_args(argv)

    result = run_minimal_slice(
        args.query, top_n=args.n, max_cites=args.cites, mode=args.mode,
        with_bundle=bool(args.bundle_out),
    )
    if args.bundle_out:
        output, bundle = result
    else:
        output, bundle = result, None

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nWrote visualization output to {args.out}")
    if args.bundle_out:
        with open(args.bundle_out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        print(f"Wrote full query_result_bundle to {args.bundle_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())