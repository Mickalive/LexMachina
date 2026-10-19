#!/usr/bin/env python3
"""Consume the accepted frontier-query-concept-recall numbers BESIDE this lane's own.

Factory direction v57 (evaluation lane) orders: the RECALL half of the accepted
coverage finding was chartered to Frontier team frontier-query-concept-recall
behind the bundle seam; this lane builds or re-scores NO candidate for it, and
when its numbers arrive they are published BESIDE this lane's own, never in
place of them, with any divergence named as the headline.

The team has reached OUTCOME_B_BOUNDED_NEGATIVE and been independently accepted
(audit gate PASS, accept commit bd1b4d73a).  This instrument re-hashes every
pinned input, verifies that audit gate, then compares frozen cells:

  coverage   per served question: n_rows, the under-covered SET and the full
             concept list across three sides - this lane's mapping-free
             instrument (subject_match_audit 39113690481), this lane's
             product-side admission self-check (coverage_finding_falsification
             39177046762) and the frontier's A0_baseline_shipped reproduction.
  recall     per (frozen leg, language) cell: the frontier's A0 baseline hits
             vs this lane's accepted run of record (39098571937), with the
             charter-cited replay (39117425713) published beside both.

Every divergence is the HEADLINE of the record and report; nothing is smoothed.
No cell, digest or exit mapping may be edited after the hypothesis commit.

Exit codes
  0  CONSUMED_NO_DIVERGENCE   every pinned digest matches, audit gate PASS,
                              every frozen cell matches
  1  DIVERGENCE_HEADLINE      every pinned digest matches, audit gate PASS,
                              at least one frozen cell diverges
  2  ENVIRONMENT              pinned input missing/drifted or audit gate not
                              PASS; no cell comparison is read

SCRATCH-RUN OBLIGATION: a non-claim-bearing invocation (unit test, local poke)
MUST pass --out and --report-dir; the defaults are the committed claim-bearing
trees and a scratch run that does not redirect becomes accepted evidence via the
workflow's `git add -A` persist step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-frontier-recall-handoff/1"
DEFAULT_HYPOTHESIS = (_REPO_ROOT / "evaluation"
                      / "FRONTIER_RECALL_HANDOFF_HYPOTHESIS_V1.json")
SERVED_QUESTIONS = ("de-kapitalverletzung", "fr-bail-entretien",
                    "it-responsabilita-medica")
LANGS = ("de", "fr", "it")
MEASURABLE_LEG_SLUGS = ("corporate-criminal-liability", "business-judgment-rule",
                        "petty-theft-dismissal", "rent-default")

#: Verdict vocabulary - frozen by the hypothesis; never extended here.
VERDICT_NO_DIVERGENCE = "CONSUMED_NO_DIVERGENCE"
VERDICT_DIVERGENCE = "DIVERGENCE_HEADLINE"
VERDICT_ENVIRONMENT = "ENVIRONMENT"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_inputs(hypothesis: dict) -> tuple[dict, list[str]]:
    """Re-hash every pinned input. Returns (resolved path map, problems)."""
    resolved: dict[str, Path] = {}
    problems: list[str] = []
    for name, pin in (hypothesis.get("inputs") or {}).items():
        path = Path(pin["path"])
        if not path.is_absolute():
            path = _REPO_ROOT / path
        if not path.is_file():
            problems.append(f"{name}: missing {path}")
            continue
        got = _sha256_file(path)
        if got != pin["sha256"]:
            problems.append(f"{name}: digest drift expected {pin['sha256'][:12]} "
                            f"got {got[:12]} ({path})")
            continue
        resolved[name] = path
    return resolved, problems


# --------------------------------------------------------------------------- #
# extraction (pure; unit-testable without the frontier mount)
# --------------------------------------------------------------------------- #


def extract_lane_eval_coverage(subject_match_audit: dict) -> dict[str, dict]:
    """This lane's mapping-free coverage numbers, per served question."""
    out: dict[str, dict] = {}
    for gate in subject_match_audit.get("gates") or []:
        name = str(gate.get("gate") or "")
        if not name.startswith("question_native_concept_coverage::"):
            continue
        qid = name.split("::", 1)[1]
        measured = gate.get("measured") or {}
        out[qid] = {
            "n_rows": measured.get("n_bundle_rows"),
            "concepts": list(measured.get("concepts") or []),
            "under_covered": sorted(measured.get("concepts_with_zero_rows") or []),
        }
    return out


def extract_lane_product_coverage(coverage_handoff: dict) -> dict[str, dict]:
    """This lane's product-side admission self-check numbers, per question."""
    out: dict[str, dict] = {}
    for bundle in coverage_handoff.get("bundles") or []:
        after = bundle.get("after") or {}
        out[str(bundle.get("bundle"))] = {
            "concepts": list(after.get("measured_query_concepts") or []),
            "under_covered": sorted(
                after.get("measured_query_concepts_under_covered") or []),
            "bundle_sha256": bundle.get("bundle_sha256"),
        }
    return out


def extract_frontier_coverage(harness: dict) -> dict[str, dict]:
    """Frontier A0_baseline_shipped coverage reproduction, per question."""
    out: dict[str, dict] = {}
    for qid, block in (harness.get("served_questions") or {}).items():
        a0 = (block or {}).get("A0_baseline_shipped") or {}
        out[qid] = {
            "n_rows": a0.get("n_rows"),
            "concepts": list(a0.get("concepts") or []),
            "under_covered": sorted(a0.get("under_covered") or []),
            "method": a0.get("method"),
        }
    return out


def _lang_gate_map(retrieval_record: dict) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for gate in (retrieval_record.get("verdict") or {}).get("gates") or []:
        name = str(gate.get("gate") or "")
        if not name.startswith("authority::baseline_lang_recall::"):
            continue
        _, _, slug, lang = name.split("::", 3)
        measured = gate.get("measured") or {}
        out[(slug, lang)] = {
            "passed": gate.get("passed"),
            "hits": sorted(measured.get("hits") or []),
        }
    return out


def extract_frontier_recall(harness: dict) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for slug, block in (harness.get("frozen_legs") or {}).items():
        for lang, cell in ((block or {}).get("per_language") or {}).items():
            a0 = (cell or {}).get("A0_baseline_shipped") or {}
            out[(slug, lang)] = {
                "measurable": a0.get("measurable"),
                "hits": sorted(a0.get("hits") or []),
                "n_rows": a0.get("n_rows"),
            }
    return out


# --------------------------------------------------------------------------- #
# frozen-cell comparison (pure)
# --------------------------------------------------------------------------- #


def compare_coverage(lane_eval: dict, lane_product: dict,
                     frontier: dict) -> dict:
    cells: list[dict] = []
    divergences: list[str] = []
    for qid in SERVED_QUESTIONS:
        e = lane_eval.get(qid) or {}
        p = lane_product.get(qid) or {}
        f = frontier.get(qid) or {}
        # frozen cell: rows
        rows_match = e.get("n_rows") == f.get("n_rows") and e.get("n_rows") is not None
        cells.append({"question": qid, "cell": "n_rows", "lane_eval": e.get("n_rows"),
                      "frontier_a0": f.get("n_rows"), "match": rows_match})
        if not rows_match:
            divergences.append(
                f"{qid}::n_rows lane_eval={e.get('n_rows')} frontier_a0={f.get('n_rows')}")
        # frozen cell: under-covered set (three-way)
        under_match = (sorted(e.get("under_covered") or [])
                       == sorted(f.get("under_covered") or [])
                       == sorted(p.get("under_covered") or []))
        cells.append({"question": qid, "cell": "under_covered_set",
                      "lane_eval": sorted(e.get("under_covered") or []),
                      "lane_product": sorted(p.get("under_covered") or []),
                      "frontier_a0": sorted(f.get("under_covered") or []),
                      "match": under_match})
        if not under_match:
            divergences.append(
                f"{qid}::under_covered_set lane_eval={sorted(e.get('under_covered') or [])} "
                f"lane_product={sorted(p.get('under_covered') or [])} "
                f"frontier_a0={sorted(f.get('under_covered') or [])}")
        # frozen cell: concept list (eval-side vs frontier)
        concepts_match = (list(e.get("concepts") or [])
                          == list(f.get("concepts") or []))
        cells.append({"question": qid, "cell": "concept_list_eval_vs_frontier",
                      "lane_eval": list(e.get("concepts") or []),
                      "frontier_a0": list(f.get("concepts") or []),
                      "match": concepts_match})
        if not concepts_match:
            divergences.append(
                f"{qid}::concept_list lane_eval={list(e.get('concepts') or [])} "
                f"frontier_a0={list(f.get('concepts') or [])}")
        # disclosed pre-observed cell: product-side vs eval-side concept count
        product_subset = set(p.get("concepts") or []) <= set(e.get("concepts") or [])
        product_equal = (list(p.get("concepts") or []) == list(e.get("concepts") or []))
        cells.append({
            "question": qid, "cell": "product_side_concepts_vs_eval_side",
            "lane_product": list(p.get("concepts") or []),
            "lane_eval": list(e.get("concepts") or []),
            "match": product_equal,
            "product_is_subset_of_eval": product_subset,
            "tier": "DISCLOSED_PRE_OBSERVED",
        })
        if not product_equal:
            divergences.append(
                f"{qid}::product_side_concept_extraction lane_product="
                f"{len(p.get('concepts') or [])} concepts vs lane_eval="
                f"{len(e.get('concepts') or [])} concepts "
                f"(subset={product_subset})")
    return {"cells": cells, "divergences": divergences,
            "n_divergences": len(divergences)}


def compare_recall(lane_hits: dict, charter_hits: dict,
                   frontier_hits: dict) -> dict:
    cells: list[dict] = []
    divergences: list[str] = []
    for slug in MEASURABLE_LEG_SLUGS:
        for lang in LANGS:
            lane = lane_hits.get((slug, lang)) or {}
            charter = charter_hits.get((slug, lang)) or {}
            front = frontier_hits.get((slug, lang)) or {}
            # rent-default carries no frozen authority set: both sides n/m, empty hits
            if slug == "rent-default":
                match = (front.get("hits", []) == [] and lane.get("hits", [])
                         == [] and front.get("measurable") is False)
                cells.append({"slug": slug, "lang": lang, "cell": "authority_hits",
                              "lane_run_of_record": lane.get("hits"),
                              "lane_charter_cited": charter.get("hits"),
                              "frontier_a0": front.get("hits"),
                              "frontier_measurable": front.get("measurable"),
                              "match": match})
                if not match:
                    divergences.append(
                        f"{slug}::{lang} rent-default n/m mismatch "
                        f"lane={lane.get('hits')} frontier={front.get('hits')}")
                continue
            match = lane.get("hits") == front.get("hits")
            cells.append({"slug": slug, "lang": lang, "cell": "authority_hits",
                          "lane_run_of_record_passed": lane.get("passed"),
                          "lane_run_of_record": lane.get("hits"),
                          "lane_charter_cited": charter.get("hits"),
                          "frontier_a0": front.get("hits"),
                          "match": match,
                          "charter_cited_matches_run_of_record":
                              charter.get("hits") == lane.get("hits")})
            if not match:
                divergences.append(
                    f"{slug}::{lang} authority_hits lane_run_of_record="
                    f"{lane.get('hits')} frontier_a0={front.get('hits')}")
    return {"cells": cells, "divergences": divergences,
            "n_divergences": len(divergences)}


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def run(run_id: str, hypothesis_path: Path, out_path: Path,
        report_path: Path) -> tuple[int, dict]:
    if not hypothesis_path.is_file():
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": VERDICT_ENVIRONMENT,
                   "detail": f"hypothesis missing: {hypothesis_path}"}
    hypothesis = _load(hypothesis_path)
    resolved, problems = verify_inputs(hypothesis)
    base = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis.get("direction_version"),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_path": str(hypothesis_path),
        "hypothesis_sha256": _sha256_file(hypothesis_path),
        "input_digests_verified": sorted(resolved),
        "input_digest_problems": problems,
    }
    if problems:
        base.update(verdict=VERDICT_ENVIRONMENT,
                    detail=("pinned input missing or drifted; no cell comparison "
                            "was read"), headline="ENVIRONMENT_INPUT_DRIFT")
        _persist(base, out_path, report_path)
        return 2, base

    gate = _load(resolved["frontier_audit_gate"])
    if gate.get("gate") != "PASS" or gate.get("safe_to_integrate") is not True:
        base.update(verdict=VERDICT_ENVIRONMENT,
                    detail=("frontier audit gate is not PASS/safe_to_integrate; "
                            "its numbers are not accepted evidence"),
                    headline="ENVIRONMENT_GATE_NOT_PASS",
                    observed_gate=gate.get("gate"),
                    observed_safe_to_integrate=gate.get("safe_to_integrate"))
        _persist(base, out_path, report_path)
        return 2, base

    lane_eval = extract_lane_eval_coverage(_load(resolved["lane_subject_match_audit_accepted"]))
    lane_product = extract_lane_product_coverage(_load(resolved["lane_coverage_handoff_latest"]))
    frontier_cov = extract_frontier_coverage(_load(resolved["frontier_harness_results"]))
    harness = _load(resolved["frontier_harness_results"])
    lane_hits = _lang_gate_map(
        _load(resolved["lane_retrieval_benchmark_accepted_run_of_record"]))
    charter_hits = _lang_gate_map(_load(resolved["lane_retrieval_benchmark_charter_cited"]))
    frontier_hits = extract_frontier_recall(harness)

    coverage = compare_coverage(lane_eval, lane_product, frontier_cov)
    recall = compare_recall(lane_hits, charter_hits, frontier_hits)

    verdict_block = harness.get("verdict") or {}
    frontier_outcome_copy = {
        "outcome": verdict_block.get("outcome"),
        "improved_fr_it_cells": verdict_block.get("improved_fr_it_cells"),
        "reduced_under_covered_questions": verdict_block.get("reduced_under_covered_questions"),
        "any_vacuous": verdict_block.get("any_vacuous"),
        "n_calls_over_per_search_budget": verdict_block.get("n_calls_over_per_search_budget"),
        "latency_budget_breach_named": verdict_block.get("latency_budget_breach_named"),
        "bounded_cause": (verdict_block.get("bounded_cause") or {}).get("one_bounded_cause"),
        "copy_only_note": ("copied verbatim from the accepted harness record; this "
                           "lane issues no verdict on the candidate"),
    }

    divergences = coverage["divergences"] + recall["divergences"]
    if divergences:
        verdict, exit_code = VERDICT_DIVERGENCE, 1
        headline = divergences[0]
    else:
        verdict, exit_code = VERDICT_NO_DIVERGENCE, 0
        headline = ("frontier A0 baseline reproduction equals this lane's own "
                    "accepted numbers on every frozen cell")

    record = dict(base)
    record.update(
        verdict=verdict,
        headline=headline,
        divergences=divergences,
        n_divergences=len(divergences),
        coverage_side_by_side=coverage,
        recall_side_by_side=recall,
        frontier_outcome_copy=frontier_outcome_copy,
        frontier_audit_gate={"gate": gate.get("gate"),
                             "safe_to_integrate": gate.get("safe_to_integrate"),
                             "required_fixes": gate.get("required_fixes")},
        lanes_own_sources={
            "eval_side_coverage": "results/evaluation/subject_match_audit/39113690481.json",
            "product_side_coverage": "results/evaluation/coverage_finding_falsification/39177046762.json",
            "recall_run_of_record": "results/evaluation/retrieval_benchmark/39098571937.json",
            "recall_charter_cited": "results/evaluation/retrieval_benchmark/39117425713.json",
        },
        claim_ceiling=hypothesis.get("claim_ceiling"),
        human_gate_ready=False,
        owner_decision_required=False,
    )
    _persist(record, out_path, report_path)
    return exit_code, record


def _persist(record: dict, out_path: Path, report_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Frontier recall handoff consumption - run {record['run_id']}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Verdict: **{record.get('verdict')}** (headline below)",
        f"- Headline: {record.get('headline')}",
        "",
        "## Coverage side by side",
        "",
        "| question | cell | lane eval-side | lane product-side | frontier A0 | match |",
        "|---|---|---|---|---|---|",
    ]
    for cell in (record.get("coverage_side_by_side") or {}).get("cells", []):
        lines.append(
            f"| {cell.get('question')} | {cell.get('cell')} | "
            f"{cell.get('lane_eval')} | {cell.get('lane_product', '-')} | "
            f"{cell.get('frontier_a0', '-')} | {cell.get('match')} |")
    lines += ["", "## Recall side by side (per-language authority hits)", "",
              "| slug | lang | lane run-of-record | lane charter-cited | frontier A0 | match |",
              "|---|---|---|---|---|---|"]
    for cell in (record.get("recall_side_by_side") or {}).get("cells", []):
        lines.append(
            f"| {cell.get('slug')} | {cell.get('lang')} | "
            f"{cell.get('lane_run_of_record')} | {cell.get('lane_charter_cited')} | "
            f"{cell.get('frontier_a0')} | {cell.get('match')} |")
    outcome = record.get("frontier_outcome_copy") or {}
    lines += [
        "",
        "## Frontier outcome (copied verbatim, no verdict issued here)",
        "",
        f"- outcome: `{outcome.get('outcome')}`",
        f"- improved fr/it cells: {outcome.get('improved_fr_it_cells')}",
        f"- reduced under-covered questions: {outcome.get('reduced_under_covered_questions')}",
        f"- any_vacuous: {outcome.get('any_vacuous')}",
        f"- per-search budget breaches: {outcome.get('n_calls_over_per_search_budget')}",
        f"- bounded cause: {outcome.get('bounded_cause')}",
        "",
        "## Divergences (each is a headline, never smoothed)",
        "",
    ]
    divs = record.get("divergences") or []
    lines += [f"- {d}" for d in divs] or ["- none"]
    lines += ["", "## Claim ceiling", "", str(record.get("claim_ceiling")), ""]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", default=str(DEFAULT_HYPOTHESIS))
    ap.add_argument("--out", default=None,
                    help="machine record (default: committed "
                         "results/evaluation/frontier_recall_handoff/<run_id>.json)")
    ap.add_argument("--report-dir", default=None,
                    help="report directory (default: committed reports/evaluation)")
    args = ap.parse_args(argv)
    out_path = (Path(args.out) if args.out else
                _REPO_ROOT / "results/evaluation/frontier_recall_handoff"
                / f"{args.run_id}.json")
    report_dir = (Path(args.report_dir) if args.report_dir else
                  _REPO_ROOT / "reports/evaluation")
    report_path = report_dir / f"FRONTIER_RECALL_HANDOFF_{args.run_id}.md"
    exit_code, record = run(args.run_id, Path(args.hypothesis), out_path, report_path)
    print(json.dumps({"verdict": record.get("verdict"),
                      "headline": record.get("headline"),
                      "n_divergences": record.get("n_divergences"),
                      "exit_code": exit_code}, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
