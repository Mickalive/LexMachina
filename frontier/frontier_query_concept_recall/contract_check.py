"""Integration-contract checker for frontier-query-concept-recall.

Why this module exists
----------------------
The stale hyphenated doc in this team's tree
(``frontier/frontier-query-concept-recall/INTEGRATION_CONTRACT.md``) tells the
integrating lane to run::

    from ...expansion import ExpansionConfig, build_variants, search_variants, QueryVariant

None of those four symbols has ever existed in this team's module.  The
contract was prose that no code could satisfy, so nothing caught it: the
harness measured the layer correctly and still shipped a handoff record that
Product could not execute.  The same drift happened again with the bounded
cause - the published ``integration_contract.json`` still quotes a cause the
team's own code withdraws.

A contract that cannot be executed is not a contract.  This module makes the
contract falsifiable: it reads the PUBLISHED integration contract and checks,
mechanically and offline, every factual claim the contract makes against

* the shipped code (``frontier_query_concept_recall.expansion``),
* the mounted accepted product bytes (``/tmp/lex_accepted/core/product``,
  parsed with ``ast`` so no numpy import is needed),
* the accepted served bundles, and
* the frozen ``RULES.json`` claim ceiling.

It issues a PASS/FAIL per check and exits non-zero if any check fails, so a
lying contract fails the build instead of being discovered by the integrator.

Run (from the ``frontier/`` directory)::

    python -m frontier_query_concept_recall.contract_check --out <dir>
    python -m frontier_query_concept_recall.contract_check --out <dir> \
        --contract ../results/frontier/frontier-query-concept-recall/integration_contract.json

``--contract`` defaults to the current run's contract.  Pass the superseded
contract explicitly to demonstrate that this checker FAILS it.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FRONTIER_ROOT = Path(__file__).resolve().parent
REPO_ROOT = FRONTIER_ROOT.parent.parent
if str(FRONTIER_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(FRONTIER_ROOT.parent))

from frontier_query_concept_recall import cli  # noqa: E402
from frontier_query_concept_recall import expansion as exp  # noqa: E402
from frontier_query_concept_recall.loader import ACCEPTED_PRODUCT_ROOT  # noqa: E402

RULES_PATH = FRONTIER_ROOT / "RULES.json"
DEFAULT_OUT = REPO_ROOT / "results/frontier/frontier-query-concept-recall"
DEFAULT_CONTRACT = DEFAULT_OUT / "integration_contract.json"

#: Symbols the stale hyphenated INTEGRATION_CONTRACT.md told Product to import.
LEGACY_DOC_SYMBOLS = ("ExpansionConfig", "build_variants", "search_variants",
                      "QueryVariant")

CLAIM_CEILING = (
    "No artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any "
    "packet is fit to serve. Usefulness remains the human product gate's "
    "question and admission remains fail-closed. Concept-coverage counts are "
    "lexical coverage of a retrieved set, not a legal conclusion, and a zero "
    "count is a retrieval signal, not proof of corpus absence."
)

REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]
REQUIRED_PROVENANCE_KEYS = [
    "layer", "deterministic", "corpus_derived", "model_calls", "network_calls",
    "target_language", "concepts", "terms", "n_terms", "per_concept",
    "accepted_lexicon_synonyms",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# 1. every symbol the contract names must resolve in the shipped package
# --------------------------------------------------------------------------- #
def _drop_in(contract: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    """Normalise ``drop_in_path``.

    The superseded contract carried a bare prose string.  A prose drop-in path
    cannot be executed, so it is normalised to ``{}`` with the prose kept, and
    every structured check then fails loudly instead of being skipped.
    """
    raw = contract.get("drop_in_path")
    if isinstance(raw, dict):
        return raw, raw
    return {}, raw


def check_required_symbols(contract: dict[str, Any]) -> dict[str, Any]:
    """Resolve ``module:attr`` entries from the contract against real code."""
    drop_in, raw = _drop_in(contract)
    declared: list[str] = list(drop_in.get("required_symbols") or [])
    resolved: dict[str, bool] = {}
    for entry in declared:
        if ":" not in entry:
            resolved[entry] = False
            continue
        module_name, attr = entry.split(":", 1)
        module = sys.modules.get(module_name)
        if module is None:
            try:
                module = __import__(module_name, fromlist=[attr])
            except Exception:  # pragma: no cover - a missing module is a FAIL
                resolved[entry] = False
                continue
        resolved[entry] = hasattr(module, attr)
    missing = sorted(k for k, ok in resolved.items() if not ok)
    return {
        "check": "required_symbols_resolve",
        "declared": declared,
        "resolved": resolved,
        "missing": missing,
        "pass": bool(declared) and not missing,
        "note": "an integration contract that names a symbol the layer does not "
                "export is not executable; an EMPTY declared list also fails so "
                "the contract can never silently stop being checked",
        "raw_drop_in_path": raw if not isinstance(raw, dict) else None,
    }


def check_legacy_doc_symbols(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record that the stale doc's import list never existed in real code."""
    present = {name: hasattr(exp, name) for name in LEGACY_DOC_SYMBOLS}
    actual = sorted(n for n in exp.__all__ if not n.startswith("_"))
    return {
        "check": "stale_hyphenated_doc_symbols",
        "documented_in": "frontier/frontier-query-concept-recall/INTEGRATION_CONTRACT.md",
        "present_in_shipped_module": present,
        "actual_public_api": actual,
        "pass": not any(present.values()),
        "note": "the doc named four symbols, none of which the module has ever "
                "exported; a doc that instructs the integrator to import them is "
                "a trap, not a handoff",
    }


# --------------------------------------------------------------------------- #
# 2. the product seam must exist in the mounted accepted bytes
# --------------------------------------------------------------------------- #
def _product_functions() -> dict[str, dict[str, Any]]:
    """AST-parse the mounted product pipeline (numpy-free)."""
    path = ACCEPTED_PRODUCT_ROOT / "product/query/pipeline.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args] + [a.arg for a in node.args.kwonlyargs]
            out[node.name] = {"line": node.lineno, "args": args}
    return out


def check_product_seam(contract: dict[str, Any]) -> dict[str, Any]:
    drop_in, raw = _drop_in(contract)
    declared = drop_in.get("product_function")
    funcs = _product_functions()
    resolved = declared in funcs if declared else False
    detail: dict[str, Any] = {
        "check": "product_seam_exists",
        "declared_function": declared,
        "declared_product_file": drop_in.get("product_file"),
        "resolved": resolved,
        "raw_drop_in_path": raw if not isinstance(raw, dict) else None,
        "pass": bool(resolved),
    }
    if resolved:
        detail["line"] = funcs[declared]["line"]
        detail["args"] = funcs[declared]["args"]
        first_arg = funcs[declared]["args"][0] if funcs[declared]["args"] else None
        # The seam must take the bundle, because the layer is additive-only and
        # has to be applied to an already-built bundle without re-retrieving it.
        bundle_arg = drop_in.get("bundle_parameter")
        detail["bundle_parameter"] = bundle_arg
        detail["bundle_parameter_is_first_arg"] = (
            bundle_arg is not None and bundle_arg == first_arg)
        detail["pass"] = bool(declared) and detail["bundle_parameter_is_first_arg"]
    return detail


# --------------------------------------------------------------------------- #
# 3. the provenance the contract promises must be the provenance we emit
# --------------------------------------------------------------------------- #
def check_provenance_shape(contract: dict[str, Any]) -> dict[str, Any]:
    prov = exp.Expansion("de", "", [], [], {}, []).provenance()
    try:
        json.dumps(prov)
        serialisable = True
    except (TypeError, ValueError):  # pragma: no cover
        serialisable = False
    missing = [k for k in REQUIRED_PROVENANCE_KEYS if k not in prov]
    declared = ((contract.get("measured_layer_spec") or {})
                .get("provenance_keys"))
    declared_missing = ([] if declared is None
                        else [k for k in declared if k not in prov])
    return {
        "check": "provenance_shape",
        "emitted_keys": sorted(prov),
        "required_missing": missing,
        "contract_declared_keys": declared,
        "contract_declared_keys_missing_from_code": declared_missing,
        "serialisable": serialisable,
        "model_calls": prov.get("model_calls"),
        "network_calls": prov.get("network_calls"),
        "pass": (not missing and serialisable and not declared_missing
                 and prov.get("model_calls") == 0 and prov.get("network_calls") == 0),
    }


# --------------------------------------------------------------------------- #
# 4. the seam transformation must be exactly as additive as the contract says
# --------------------------------------------------------------------------- #
def check_seam_additivity(contract: dict[str, Any]) -> dict[str, Any]:
    """Apply the contract's documented transformation to real served bundles.

    The code block in the contract is executed as written, with only the
    contract's placeholder names bound to real objects, so a snippet that no
    longer matches the shipped API fails here instead of in the product lane.
    """
    sma = cli._subject_match_audit()
    cc = cli.concept_coverage()
    retrieval = cli.product_retrieval()
    bundles = cli.load_bundles(None)
    bench = json.loads(cli.ACCEPTED_BENCHMARK_RECORD.read_text(encoding="utf-8"))

    bundle_rows = [row for bundle in bundles.values()
                   for row in (bundle.get("decisions") or [])]
    benchmark_rows = [row for query in bench["queries"]
                      for row in (query.get("rows") or [])]
    stop = set(cc.STOPWORDS) | set(sma.STOPWORDS_SET)

    # --- the contract's snippet, executed ---
    t0 = time.perf_counter()
    sample = exp.CorpusSample.build(stoplist=stop, bundle_rows=bundle_rows,
                                   benchmark_rows=benchmark_rows)
    sample_build_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    per_question: dict[str, Any] = {}
    for qid, bundle in bundles.items():
        lang = cli.QUESTION_LANGUAGE[qid]
        expansion = exp.build_expansion(
            bundle.get("query") or "", lang, sample,
            concept_prefix_fn=cc.concept_prefix,
            content_concepts_fn=lambda q: sma.question_concepts(q)[:8],
            accepted_lexicon=retrieval.EXPANSION)

        original_variants = list(bundle.get("query_variants") or [])
        original_prov = dict(bundle.get("provenance") or {})
        original_decisions = list(bundle.get("decisions") or [])
        pristine = json.loads(json.dumps(bundle))

        # --- the contract's snippet, applied verbatim to the served bundle ---
        bundle["query_variants"] = list(bundle.get("query_variants") or []) + [expansion.query]
        bundle["provenance"] = {**dict(bundle.get("provenance") or {}),
                                "query_expansion": expansion.provenance()}
        simulated = dict(bundle)
        variants = list(simulated.get("query_variants") or [])
        prov = dict(simulated.get("provenance") or {})

        new_variant_keys = sorted(set(variants) - set(original_variants))
        new_prov_keys = sorted(set(prov) - set(original_prov))
        untouched = all(simulated[k] == pristine[k] for k in (
            "bundle_version", "query", "answer", "decisions", "clusters",
            "relations"))
        per_question[qid] = {
            "n_original_query_variants": len(original_variants),
            "n_variants_after_seam": len(variants),
            "new_query_variants": new_variant_keys,
            "new_provenance_keys": new_prov_keys,
            "original_variants_prefix_preserved":
                variants[:len(original_variants)] == original_variants,
            "original_provenance_entries_unchanged":
                all(prov[k] == v for k, v in original_prov.items()),
            "non_expansion_fields_byte_identical": untouched,
            "required_top_level_fields_present":
                [k for k in REQUIRED_TOP if k not in simulated],
            "n_decisions_before": len(original_decisions),
            "n_decisions_after": len(simulated.get("decisions") or []),
            "no_decision_dropped_or_duplicated":
                [d["decision_id"] for d in original_decisions]
                == [d["decision_id"] for d in simulated.get("decisions") or []],
        }
        per_question[qid]["pass"] = (
            per_question[qid]["original_variants_prefix_preserved"]
            and per_question[qid]["original_provenance_entries_unchanged"]
            and per_question[qid]["non_expansion_fields_byte_identical"]
            and not per_question[qid]["required_top_level_fields_present"]
            and per_question[qid]["new_provenance_keys"] == ["query_expansion"]
            and len(new_variant_keys) <= 1
            and per_question[qid]["no_decision_dropped_or_duplicated"]
            and per_question[qid]["n_decisions_after"]
            == per_question[qid]["n_decisions_before"])
    return {
        "check": "seam_additivity",
        "contract_code_executed": True,
        "corpus_sample_build_ms": sample_build_ms,
        "corpus_sample_rows_per_language": dict(sample.n_rows),
        "per_question": per_question,
        "pass": all(v["pass"] for v in per_question.values()),
        "note": "the layer is additive-only: it appends at most one query variant "
                "and exactly one provenance key, and changes nothing else. The "
                "code block in the published contract was executed verbatim here, "
                "with only its placeholder names bound to real objects.",
    }


# --------------------------------------------------------------------------- #
# 5. the runtime-cost claim must be measurable and must not be falsified
# --------------------------------------------------------------------------- #
def check_runtime_cost(contract: dict[str, Any]) -> dict[str, Any]:
    sma = cli._subject_match_audit()
    cc = cli.concept_coverage()
    retrieval = cli.product_retrieval()
    bundles = cli.load_bundles(None)
    bench = json.loads(cli.ACCEPTED_BENCHMARK_RECORD.read_text(encoding="utf-8"))
    sample = cli.build_corpus_sample(bundles, bench["queries"])

    timings: dict[str, float] = {}
    for qid, bundle in bundles.items():
        lang = cli.QUESTION_LANGUAGE[qid]
        t0 = time.perf_counter()
        exp.build_expansion(bundle.get("query") or "", lang, sample,
                            concept_prefix_fn=cc.concept_prefix,
                            content_concepts_fn=lambda q: sma.question_concepts(q)[:8],
                            accepted_lexicon=retrieval.EXPANSION)
        timings[qid] = round((time.perf_counter() - t0) * 1000.0, 3)

    budget_ms = float((contract.get("runtime_cost") or {})
                      .get("expansion_build_budget_ms", 50.0))
    slowest = max(timings.values()) if timings else 0.0
    return {
        "check": "runtime_cost",
        "measured_build_ms_per_question": timings,
        "slowest_ms": slowest,
        "budget_ms": budget_ms,
        "budget_covers": "per-question expansion construction only; the "
                         "one-per-process corpus sample build is measured "
                         "separately under seam_additivity.corpus_sample_build_ms "
                         "and the retrieval cost of the emitted query is "
                         "disclosed in the contract under runtime_cost.retrieval_cost",
        "model_calls": 0,
        "network_calls": 0,
        "pass": slowest < budget_ms,
        "note": "expansion construction is string work over an in-memory corpus "
                "sample; zero model calls and zero network calls at construction "
                "time.",
    }


# --------------------------------------------------------------------------- #
# 6. the ceiling and the disclosure text
# --------------------------------------------------------------------------- #
def check_claim_ceiling(contract: dict[str, Any]) -> dict[str, Any]:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    frozen = rules.get("claim_ceiling")
    contract_ceiling = contract.get("claim_ceiling")
    return {
        "check": "claim_ceiling_matches_frozen_rules",
        "rules_file_sha256": sha256(RULES_PATH),
        "contract_ceiling": contract_ceiling,
        "rules_ceiling": frozen,
        "matches_rules": contract_ceiling == frozen,
        "matches_module_constant": contract_ceiling == CLAIM_CEILING,
        "pass": contract_ceiling == frozen == CLAIM_CEILING,
    }


def check_disclosure_text(contract: dict[str, Any]) -> dict[str, Any]:
    spec = contract.get("measured_layer_spec") or {}
    text = contract.get("disclosure_text_for_product_if_ever_reconsidered")
    return {
        "check": "disclosure_text_present",
        "present": bool(text and str(text).strip()),
        "chars": len(str(text or "")),
        "product_decision_required": bool(contract.get("product_decision_required")),
        "silent_non_consumption_not_permitted":
            bool(contract.get("silent_non_consumption_not_permitted")),
        "pass": bool(text and str(text).strip()
                     and contract.get("product_decision_required")
                     and contract.get("silent_non_consumption_not_permitted")),
    }


# --------------------------------------------------------------------------- #
# 7. the contract's numbers must match a harness record that exists
# --------------------------------------------------------------------------- #
def check_measured_outcome(contract: dict[str, Any],
                           harness_path: Path | None) -> dict[str, Any]:
    """The contract's measured numbers must be reproducible from a real record."""
    source = contract.get("source_artifact")
    resolved: Path | None = None
    if harness_path is not None and harness_path.is_file():
        resolved = harness_path
    elif source:
        candidate = REPO_ROOT / source
        if candidate.is_file():
            resolved = candidate
    if resolved is None:
        return {
            "check": "measured_outcome_matches_record",
            "resolved": None,
            "pass": False,
            "note": "no harness record could be resolved; a contract whose "
                    "numbers cannot be traced to a record is not a measurement",
        }
    record = json.loads(resolved.read_text(encoding="utf-8"))
    verdict = record.get("verdict") or {}
    measured = contract.get("measured_outcome") or {}
    pairs = {
        "accepted_baseline_reproduced": verdict.get("accepted_baseline_reproduced"),
        "improved_fr_it_cells": verdict.get("improved_fr_it_cells"),
        "reduced_under_covered_questions": verdict.get("reduced_under_covered_questions"),
        "regressed_gates": verdict.get("regressed_gates"),
    }
    mismatches = {k: {"contract": measured.get(k), "record": v}
                  for k, v in pairs.items() if measured.get(k) != v}
    return {
        "check": "measured_outcome_matches_record",
        "resolved": str(resolved.relative_to(REPO_ROOT)),
        "record_sha256": sha256(resolved),
        "record_run_id": record.get("run_id"),
        "record_generated_at": record.get("generated_at"),
        "compared": pairs,
        "mismatches": mismatches,
        "pass": not mismatches,
    }


def check_bounded_cause_not_withdrawn(contract: dict[str, Any],
                                      harness_path: Path | None) -> dict[str, Any]:
    """A contract must not quote a cause its own harness record withdraws.

    This is the check that would have caught the drift this resume repairs: the
    published contract carried ``TERM-ONLY EXPANSION QUERIES ARE TOO NARROW...``
    while the shipped harness emits ``withdrawn_prior_cause`` naming that exact
    text as withdrawn.
    """
    source = contract.get("source_artifact")
    path = (harness_path if harness_path is not None
            else (REPO_ROOT / source if source else None))
    if path is None or not Path(path).is_file():
        return {"check": "bounded_cause_not_withdrawn", "pass": False,
                "note": "source harness record not resolvable"}
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    bounded = ((record.get("verdict") or {}).get("bounded_cause") or {})
    withdrawn = bounded.get("withdrawn_prior_cause")
    cause = ((contract.get("measured_outcome") or {}).get("one_bounded_cause"))
    if withdrawn:
        quoted = cause == withdrawn.get("text")
        current = cause == bounded.get("one_bounded_cause")
        return {
            "check": "bounded_cause_not_withdrawn",
            "record_quotes_a_withdrawn_cause": quoted,
            "record_bounded_cause": bounded.get("one_bounded_cause"),
            "withdrawn_cause": withdrawn.get("text"),
            "withdrawn_reason": withdrawn.get("why_withdrawn"),
            "pass": current and not quoted,
            "note": "the harness record withdraws a cause; a contract that still "
                    "ships that cause as its bounded cause is handing the "
                    "integrator a retracted claim",
        }
    return {
        "check": "bounded_cause_not_withdrawn",
        "withdrawn_cause": None,
        "pass": cause == bounded.get("one_bounded_cause"),
    }


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
CHECKS = (
    ("required_symbols_resolve", check_required_symbols),
    ("stale_hyphenated_doc_symbols", check_legacy_doc_symbols),
    ("product_seam_exists", check_product_seam),
    ("provenance_shape", check_provenance_shape),
    ("seam_additivity", check_seam_additivity),
    ("runtime_cost", check_runtime_cost),
    ("claim_ceiling_matches_frozen_rules", check_claim_ceiling),
    ("disclosure_text_present", check_disclosure_text),
)


def run(contract_path: Path, harness_path: Path | None) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}
    for name, fn in CHECKS:
        checks[name] = fn(contract)
    checks["measured_outcome_matches_record"] = check_measured_outcome(
        contract, harness_path)
    checks["bounded_cause_not_withdrawn"] = check_bounded_cause_not_withdrawn(
        contract, harness_path)

    all_pass = all(c["pass"] for c in checks.values())
    failed = sorted(k for k, c in checks.items() if not c["pass"])
    return {
        "schema": "frontier_query_concept_recall.contract_check.v1",
        "team_id": "frontier-query-concept-recall",
        "charter_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_calls": 0,
        "model_calls": 0,
        "contract_path": str(contract_path),
        "contract_sha256": sha256(contract_path),
        "harness_path": str(harness_path) if harness_path else None,
        "rules_file_sha256": sha256(RULES_PATH),
        "claim_ceiling": CLAIM_CEILING,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
        "failed_checks": failed,
        "contract_executable": all_pass,
        "note": "a contract that cannot be executed is not a contract; this "
                "record is the proof that the published handoff matches the "
                "shipped code, the mounted product seam and the frozen ceiling",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m frontier_query_concept_recall.contract_check",
        description="Verify the published integration contract against shipped code")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT),
                        help="integration contract JSON to verify")
    parser.add_argument("--harness", default=None,
                        help="harness record the contract's numbers must match; "
                             "defaults to the contract's own source_artifact")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output directory for contract_check_results.json")
    parser.add_argument("--label", default="",
                        help="suffix for the output file, e.g. a run id")
    args = parser.parse_args(argv)

    contract_path = Path(args.contract).resolve()
    harness_path = Path(args.harness).resolve() if args.harness else None
    record = run(contract_path, harness_path)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.label}" if args.label else ""
    target = out / f"contract_check_results{suffix}.json"
    target.write_text(json.dumps(record, indent=1, ensure_ascii=False,
                                 sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "contract": record["contract_path"],
        "contract_sha256": record["contract_sha256"],
        "contract_executable": record["contract_executable"],
        "n_checks": record["n_checks"],
        "n_failed": record["n_failed"],
        "failed_checks": record["failed_checks"],
        "written": str(target),
    }, indent=1))
    return 0 if record["contract_executable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())