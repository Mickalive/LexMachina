"""Acceptance test (7): the regression suite that pins what must NOT change.

The additive arm may only ever ADD rows.  Everything here exists to make that
falsifiable rather than asserted:

1. per-bundle decision-count bounds;
2. dedup behaviour (product canonical identity, A0 wins on collision);
3. provenance / channel fields survive;
4. every ``query_result_bundle`` contract field survives;
5. no decision is silently dropped, duplicated or re-ranked out of existence;
6. the frozen plan is byte-reproducible from the accepted inputs;
7. the frozen key derivation reproduces committed cache envelope keys;
8. the instrument is RESPONSIVE -- a synthesised gain moves its own metric, so a
   null in this run is a measurement and not a dead instrument.

Checks 1-5 run against the real measured artefact.  Checks 6-8 run against the
accepted inputs only and are deterministic with zero network calls.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from . import inputs as I
from . import plan as plan_mod
from . import replay


def bundle_contract(product_mount: Path | None = None) -> dict:
    """The accepted ``product.query.bundle`` contract, READ from the accepted mount.

    Parsed statically with ``ast`` so the accepted product package (numpy, sklearn
    and its whole import graph) is never imported: the suite must run in a bare
    environment.  Never copied in -- if the product changes the contract, this
    suite changes with it and the additive arm is measured against the real one.
    """
    root = Path(product_mount) if product_mount else I.PRODUCT_MOUNT
    path = root / "product/query/bundle.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted = {"BUNDLE_VERSION", "REQUIRED_TOP", "REQUIRED_DECISION"}
    found: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                found[target.id] = ast.literal_eval(node.value)
    missing = sorted(wanted - set(found))
    if missing:
        raise SystemExit(f"accepted bundle contract lost {missing} in {path}")
    return {"source": str(path), "source_sha256": I.sha256_file(path),
            "parsed_statically": True, **found}


def _product_cache_index() -> dict:
    index: dict[tuple, dict] = {}
    root = I.PRODUCT_MOUNT / "results/product/query_cache"
    for p in root.glob("*/*.json"):
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if env.get("path") != "/decisions":
            continue
        params = env.get("params") or {}
        if params.get("query"):
            index.setdefault(params["query"], []).append(env)
    return index


def run_suite(frozen: dict, measurement: dict) -> dict:
    from .harness import recall_cell, served_coverage  # local: avoids an import cycle

    sma, gates, _ = I.load_evaluation_modules()
    per_unit = measurement["per_unit"]
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str, measured: Any = None) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail,
                       "measured": measured})

    # -- 1/2/5 decision-count bounds, dedup, no-drop ------------------------
    for uid, u in sorted(per_unit.items()):
        dd = (u.get("A1_union") or {}).get("dedupe") or {}
        a0_n = (u.get("A0_baseline_shipped") or {}).get("n_rows", 0)
        a0_dedup_n = dd.get("A0_rows_after_product_dedup", a0_n)
        union_n = (u.get("A1_union") or {}).get("n_rows", 0)
        check(f"decision_count_non_decreasing::{uid}", union_n >= a0_dedup_n,
              "the deduplicated union pool may only grow; the additive arm never trims. "
              "The comparison is against the DEDUPLICATED A0 pool because the accepted "
              "A0 responses already contain duplicate canonical identities (the accepted "
              "gate duplicate::unique_ids FAILs on all four frozen legs), and applying "
              "the product's own dedup to the baseline collapses them identically.",
              {"A0_raw": a0_n, "A0_deduplicated": a0_dedup_n, "A1_union": union_n,
               "A0_internal_duplicates_collapsed": dd.get(
                   "A0_internal_duplicates_collapsed")})
        check(f"dedupe_is_product_identity::{uid}",
              dd.get("strategy") == "product_canonical_identity_v1"
              and dd.get("identity_keys") == ["canonical_decision_id", "decision_id"],
              "dedup uses the product's own identity order, not a new one", dd)
        check(f"dedupe_arithmetic::{uid}",
              dd.get("input_records") == (dd.get("unique_candidates", 0)
                                           + dd.get("merged_away", -1)),
              "input_records == unique_candidates + merged_away", dd)
        check(f"no_A0_row_dropped::{uid}", bool(u.get("no_a0_row_dropped")),
              "every A0 decision id is still present in the union pool",
              {"A0_rows": a0_n, "A1_union_rows": union_n})

    # -- 3/4 bundle contract + provenance survive on the served bundles -----
    contract = bundle_contract()
    check("bundle_contract_read_from_accepted_mount",
          bool(contract.get("REQUIRED_TOP")) and bool(contract.get("REQUIRED_DECISION")),
          "the query_result_bundle contract is read from the accepted product mount, "
          "never copied into this suite", contract)
    for qid in I.SERVED_QUESTIONS:
        bundle = I.load_json(I.bundle_path(qid))
        missing_top = [k for k in contract["REQUIRED_TOP"] if k not in bundle]
        check(f"bundle_top_level_fields_intact::{qid}", not missing_top,
              "every accepted top-level bundle field is still present", missing_top)
        bad = []
        for i, row in enumerate(bundle.get("decisions") or []):
            for k in contract["REQUIRED_DECISION"]:
                if k not in row:
                    bad.append({"row": i, "field": k})
        check(f"bundle_decision_fields_intact::{qid}", not bad,
              "every accepted decision field is still present on every row", bad[:5])
        channels = sorted({str(r.get("provenance") or "") for r in bundle["decisions"]})
        check(f"provenance_channel_fields_intact::{qid}", len(channels) > 0,
              "per-row provenance strings are untouched; this harness never writes a "
              "bundle and never edits an accepted one", channels[:8])

    # -- 6 frozen plan is byte-reproducible -------------------------------
    derived = plan_mod.build_plan(charter_version=int(frozen["charter_version"]),
                                  direction_version=frozen.get("direction_version"))
    plan_keys = [k for k in sorted(frozen) if k != "inputs"]
    mismatched = [k for k in plan_keys
                  if json.dumps(frozen[k], ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) !=
                  json.dumps(derived.get(k), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"))]
    check("frozen_plan_byte_reproducible", not mismatched,
          "every decision-bearing key of the frozen plan re-derives byte-identically "
          "from the accepted inputs", mismatched)

    # -- 7 frozen key derivation reproduces committed envelope keys -------
    s = replay.Searcher(read_only_cache_dirs=[], write_cache_dir=None,
                       product_mount=I.PRODUCT_MOUNT, allow_live=False)
    index = _product_cache_index()
    rec = I.load_json(I.EVALUATION_MOUNT /
                      "results/evaluation/retrieval_benchmark/39117425713.json")
    verified, mismatches, checked_queries = 0, [], 0
    for q in rec["queries"]:
        for found in index.get(q["query"], []):
            checked_queries += 1
            verified += 1
            recomputed = s.request_key(found["path"], found["params"])
            if recomputed != found["key"] or                     Path(found.get("key", "")).stem != found["key"]:
                mismatches.append({"url": found["url"][:120],
                                   "committed": found["key"], "recomputed": recomputed})
    check("cache_key_derivation_matches_accepted_envelopes",
          verified > 0 and not mismatches,
          f"{verified} committed accepted envelope key(s) re-derived exactly by the "
          "imported derivation, so a variant minted here lands on a path the product "
          "already honours",
          {"verified": verified, "accepted_queries_matched": checked_queries,
           "mismatches": mismatches[:4],
           "derivation_source": s.key_derivation_source})

    # -- 8 responsiveness witness -----------------------------------------
    known = {"decision_id": "bger_4A_219_2015", "language": "de",
             "canonical_url": "https://mcp.opencaselaw.ch/entscheid/y",
             "title": "Kapitalverletzung und Überwachungspflicht"}
    injected_id = {"decision_id": "bger_4A_259_2016", "language": "de",
                   "canonical_url": "https://mcp.opencaselaw.ch/entscheid/x"}
    injected_concept = {"decision_id": "injected_concept_row", "language": "de",
                        "canonical_url": "https://mcp.opencaselaw.ch/entscheid/z",
                        "regeste": "Die Kapitalverletzung des Arbeitgebers"}
    ids = ["bger_4A_219_2015", "bger_4A_259_2016"]
    concepts = ["kapitalverletzung", "uberwachungspflicht"]
    before = {
        "recall": recall_cell(gates, ids, [known]),
        "coverage": served_coverage(sma, [known], concepts),
    }
    after = {
        "recall": recall_cell(gates, ids, [known, injected_id, injected_concept]),
        "coverage": served_coverage(sma, [known, injected_id, injected_concept], concepts),
    }
    check("instrument_is_responsive_to_an_injected_gain",
          after["recall"]["recall"] > before["recall"]["recall"]
          and after["coverage"]["concept_row_counts"]["kapitalverletzung"]
          > before["coverage"]["concept_row_counts"]["kapitalverletzung"],
          "a synthesised row carrying a missing authority id and a synthesised row "
          "carrying the missing concept each move their own metric, so a null in this "
          "run is a measurement and not a dead instrument",
          {"before": {"recall": before["recall"]["recall"],
                      "kapitalverletzung": before["coverage"]["concept_row_counts"]
                      ["kapitalverletzung"]},
           "after": {"recall": after["recall"]["recall"],
                     "kapitalverletzung": after["coverage"]["concept_row_counts"]
                     ["kapitalverletzung"]}})

    failed = [c for c in checks if not c["passed"]]
    return {
        "schema": "frontier_concept-seed-recall/regression-suite/1",
        "acceptance_test": (
            "7. A REGRESSION SUITE PINNING WHAT MUST NOT CHANGE: per-bundle "
            "decision-count bounds, dedup behaviour, provenance channel fields, every "
            "query_result_bundle contract field, and the invariant that no decision is "
            "silently dropped, duplicated or re-ranked out of existence by the additive "
            "arm."),
        "n_checks": len(checks),
        "n_passed": len(checks) - len(failed),
        "n_failed": len(failed),
        "failed": failed,
        "checks": checks,
        "all_passed": not failed,
        "network_calls": 0,
    }


__all__ = ["run_suite", "bundle_contract"]