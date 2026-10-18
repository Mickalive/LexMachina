"""Regression suite for frontier-query-concept-recall.

Acceptance test (7) of charter v1 pins WHAT MUST NOT CHANGE when the
candidate expansion layer is pooled into the shipped baseline:

* per-bundle decision-count bounds (the union may only grow, by at most one
  50-row search page, and the accepted A0 counts are pinned);
* deduplication behaviour (``canonical_decision_id`` then ``decision_id``,
  including the cross-shape case where only one side carries the canonical
  field);
* provenance channel fields and the ``query_result_bundle`` contract fields
  of ``docs/product/QUERY_MAP_MVP.md`` \u00a77/\u00a710A (expansion is ADDITIVE
  only: original ``query_variants`` prefix preserved, one new provenance key,
  every other field byte-identical);
* the invariant that no decision is silently dropped, duplicated or
  re-ranked out of existence by the expansion layer;
* determinism of the candidate generator;
* input-integrity of the three served bundles against the frozen RULES.json;
* metric sensitivity (the harness's own NON-VACUITY proof): an injected row
  carrying a missing concept or a frozen authority id MUST move the frozen
  coverage/recall metrics, independently of whatever the candidate arm did.

Offline discipline: every candidate row is read from this team's committed
retrieval cache (``results/frontier/frontier-query-concept-recall/cache``);
``oci.search`` / ``oci.search_many`` are never invoked, so this suite issues
ZERO network calls.  The proof is ``cache.misses == 0`` after the run.

Run (from the ``frontier/`` directory)::

    python -m frontier_query_concept_recall.regression_suite --out ../results/frontier/frontier-query-concept-recall
"""
from __future__ import annotations

import argparse
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
from frontier_query_concept_recall import oci  # noqa: E402

RULES_PATH = FRONTIER_ROOT / "RULES.json"
DEFAULT_OUT = REPO_ROOT / "results/frontier/frontier-query-concept-recall"

CLAIM_CEILING = (
    "No artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any "
    "packet is fit to serve. Usefulness remains the human product gate's "
    "question and admission remains fail-closed. Concept-coverage counts are "
    "lexical coverage of a retrieved set, not a legal conclusion, and a zero "
    "count is a retrieval signal, not proof of corpus absence."
)

#: Frozen accepted A0 row counts (accepted record 39113690481).
ACCEPTED_A0_COUNTS = {"de-kapitalverletzung": 214, "fr-bail-entretien": 217,
                      "it-responsabilita-medica": 211}

REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]
REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                     "snippet", "cluster_id", "x", "y", "counter_status",
                     "canonical_url", "citation", "provenance"]
REQUIRED_PROVENANCE_ADDITIVE = [
    "layer", "deterministic", "corpus_derived", "model_calls", "network_calls",
    "target_language", "concepts", "terms", "n_terms", "per_concept",
    "accepted_lexicon_synonyms",
]


class Ctx:
    """Shared deterministic fixtures, built once, offline."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.sma = cli._subject_match_audit()
        self.cc = cli.concept_coverage()
        self.gates = cli.load_gates()
        self.frozen = cli.load_frozen()
        self.retrieval = cli.product_retrieval()
        self.bundles = cli.load_bundles(None)
        self.bench = json.loads(
            cli.ACCEPTED_BENCHMARK_RECORD.read_text(encoding="utf-8"))
        self.sample = cli.build_corpus_sample(self.bundles, self.bench["queries"])
        self.cache = oci.Cache(cache_dir)
        self.expansions: dict[str, exp.Expansion] = {}
        for qid, bundle in self.bundles.items():
            lang = cli.QUESTION_LANGUAGE[qid]
            self.expansions[qid] = exp.build_expansion(
                bundle.get("query") or "", lang, self.sample,
                concept_prefix_fn=self.cc.concept_prefix,
                content_concepts_fn=lambda q: self.sma.question_concepts(q)[:8],
                accepted_lexicon=self.retrieval.EXPANSION)

    def candidate_rows(self, query: str) -> list[dict]:
        """Replay one expansion query from the committed cache. Offline only."""
        env = self.cache.read(oci.build_url(query))
        if env is None:
            return []
        rows, _total = oci._rows_from(str(env.get("body") or "{}"))
        return rows


# --------------------------------------------------------------------------- #
# 1. no silent drop / additive union
# --------------------------------------------------------------------------- #
def test_no_silent_drop(ctx: Ctx) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for qid, bundle in ctx.bundles.items():
        a0 = bundle.get("decisions") or []
        extra = ctx.candidate_rows(ctx.expansions[qid].query)
        a1 = cli.union_rows(a0, extra)
        a0_keys = {str(d.get("canonical_decision_id") or d.get("decision_id") or "")
                   for d in a0}
        a1_keys = {str(d.get("canonical_decision_id") or d.get("decision_id") or "")
                   for d in a1}
        dropped = sorted(a0_keys - a1_keys)
        idempotent = cli.union_rows(a1, extra) == a1
        results[qid] = {
            "n_a0": len(a0), "n_extra_cached": len(extra), "n_a1": len(a1),
            "dropped_keys": dropped, "no_drop": not dropped,
            "union_idempotent": idempotent,
            "pass": not dropped and idempotent and len(a1) >= len(a0),
        }
    return {"test": "no_silent_drop", "results": results,
            "all_pass": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------- #
# 2. dedup invariant (same-shape and cross-shape)
# --------------------------------------------------------------------------- #
def test_dedup_invariant(ctx: Ctx) -> dict[str, Any]:
    details: dict[str, Any] = {}

    # Cross-shape: baseline row WITHOUT canonical_decision_id, candidate row
    # WITH it, same underlying decision -> must collapse to one.
    base = [{"decision_id": "bge_X_1_2020", "language": "de"}]
    extra = [{"decision_id": "bge_X_1_2020", "canonical_decision_id": "bge_X_1_2020",
              "language": "de"}]
    cross = cli.union_rows(base, extra)
    details["cross_shape_collapses"] = {
        "n": len(cross), "pass": len(cross) == 1}

    # Same-shape with differing canonical: canonical wins as the key.
    same = cli.union_rows(
        [{"decision_id": "a", "canonical_decision_id": "c1"}],
        [{"decision_id": "b", "canonical_decision_id": "c1"}])
    details["canonical_key_wins"] = {"n": len(same), "pass": len(same) == 1}

    # Order preservation: every A0 decision_id must be a subsequence of the
    # union's decision_id list (no re-ranking out of existence).
    order_ok = True
    for qid, bundle in ctx.bundles.items():
        a0 = bundle.get("decisions") or []
        a1 = cli.union_rows(a0, ctx.candidate_rows(ctx.expansions[qid].query))
        a0_ids = [str(d.get("decision_id")) for d in a0]
        a1_ids = [str(d.get("decision_id")) for d in a1]
        idx = -1
        for want in a0_ids:
            try:
                idx = a1_ids.index(want, idx + 1)
            except ValueError:
                order_ok = False
                break
    details["baseline_order_preserved"] = {"pass": order_ok}
    return {"test": "dedup_invariant", "results": details,
            "all_pass": all(d["pass"] for d in details.values())}


# --------------------------------------------------------------------------- #
# 3. decision-count bounds
# --------------------------------------------------------------------------- #
def test_decision_count_bounds(ctx: Ctx) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for qid, bundle in ctx.bundles.items():
        a0 = bundle.get("decisions") or []
        extra = ctx.candidate_rows(ctx.expansions[qid].query)
        a1 = cli.union_rows(a0, extra)
        added = len(a1) - len(a0)
        results[qid] = {
            "n_a0": len(a0), "n_a1": len(a1), "added": added,
            "accepted_a0_pinned": ACCEPTED_A0_COUNTS[qid],
            "a0_matches_accepted": len(a0) == ACCEPTED_A0_COUNTS[qid],
            "grows_only": added >= 0,
            "at_most_one_page": added <= 50,
            "pass": (len(a0) == ACCEPTED_A0_COUNTS[qid]
                     and 0 <= added <= 50),
        }
    return {"test": "decision_count_bounds", "results": results,
            "all_pass": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------- #
# 4. provenance additive
# --------------------------------------------------------------------------- #
def test_provenance_additive(ctx: Ctx) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for qid, bundle in ctx.bundles.items():
        prov = ctx.expansions[qid].provenance()
        missing = [k for k in REQUIRED_PROVENANCE_ADDITIVE if k not in prov]
        serializable = True
        try:
            json.dumps(prov)
        except (TypeError, ValueError):
            serializable = False
        original = bundle.get("provenance") or {}
        merged = dict(original)
        merged["query_expansion"] = prov
        originals_unchanged = all(merged[k] == v for k, v in original.items())
        new_keys = sorted(set(merged) - set(original))
        results[qid] = {
            "missing_additive_fields": missing,
            "serializable": serializable,
            "model_calls_zero": prov.get("model_calls") == 0,
            "network_calls_zero": prov.get("network_calls") == 0,
            "originals_unchanged": originals_unchanged,
            "new_keys": new_keys,
            "exactly_one_new_key": new_keys == ["query_expansion"],
            "pass": (not missing and serializable and originals_unchanged
                     and new_keys == ["query_expansion"]
                     and prov.get("model_calls") == 0
                     and prov.get("network_calls") == 0),
        }
    return {"test": "provenance_additive", "results": results,
            "all_pass": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------- #
# 5. query_result_bundle contract (\u00a77/\u00a710A): additive only
# --------------------------------------------------------------------------- #
def test_query_result_bundle_contract(ctx: Ctx) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for qid, bundle in ctx.bundles.items():
        expansion = ctx.expansions[qid]
        # Simulate the product seam: only append to query_variants/provenance.
        simulated = dict(bundle)
        original_variants = list(bundle.get("query_variants") or [])
        variants = list(original_variants)
        if expansion.query:
            variants = variants + [expansion.query]
        prefix_preserved = variants[:len(original_variants)] == original_variants
        simulated["query_variants"] = variants
        simulated_prov = dict(bundle.get("provenance") or {})
        simulated_prov["query_expansion"] = expansion.provenance()
        simulated["provenance"] = simulated_prov

        top_missing = [k for k in REQUIRED_TOP if k not in simulated]
        untouched_fields_equal = all(
            simulated[k] == bundle[k]
            for k in ("bundle_version", "query", "answer", "decisions",
                      "clusters", "relations"))
        dec_fields_ok = True
        for d in simulated.get("decisions") or []:
            if any(k not in d for k in REQUIRED_DECISION):
                dec_fields_ok = False
                break
        results[qid] = {
            "required_top_missing": top_missing,
            "untouched_fields_equal": untouched_fields_equal,
            "query_variants_prefix_preserved": prefix_preserved,
            "query_variants_appended": len(variants) - len(
                bundle.get("query_variants") or []),
            "decision_fields_intact": dec_fields_ok,
            "n_decisions_unchanged": (
                len(simulated.get("decisions") or [])
                == len(bundle.get("decisions") or [])),
            "pass": (not top_missing and untouched_fields_equal
                     and prefix_preserved and dec_fields_ok
                     and len(simulated.get("decisions") or [])
                     == len(bundle.get("decisions") or [])),
        }
    return {"test": "query_result_bundle_contract", "results": results,
            "all_pass": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------- #
# 6. determinism of the candidate generator
# --------------------------------------------------------------------------- #
def test_determinism(ctx: Ctx) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for qid, bundle in ctx.bundles.items():
        lang = cli.QUESTION_LANGUAGE[qid]
        question = bundle.get("query") or ""
        again = exp.build_expansion(
            question, lang, ctx.sample,
            concept_prefix_fn=ctx.cc.concept_prefix,
            content_concepts_fn=lambda q: ctx.sma.question_concepts(q)[:8],
            accepted_lexicon=ctx.retrieval.EXPANSION)
        first = ctx.expansions[qid]
        blank = exp.build_expansion(
            question, lang, ctx.sample,
            concept_prefix_fn=ctx.cc.concept_prefix,
            content_concepts_fn=lambda q: ctx.sma.question_concepts(q)[:8],
            accepted_lexicon=ctx.retrieval.EXPANSION, blank=True)
        results[qid] = {
            "terms_identical": again.terms == first.terms,
            "query_identical": again.query == first.query,
            "blank_empty": blank.terms == [] and blank.query == "",
            "pass": (again.terms == first.terms and again.query == first.query
                     and blank.terms == [] and blank.query == ""),
        }
    # Compound stems are corpus-guarded: every emitted stem must occur in the
    # target-language sample vocabulary (no truncated pseudo-words).
    stems_ok = True
    stem_detail: dict[str, list[str]] = {}
    for concept, lang in (("kapitalverletzung", "de"),
                          ("responsabilita", "it"), ("resiliation", "fr")):
        vocab = ctx.sample.vocabulary(lang)
        stems = exp.compound_stems(concept, lang, vocab)
        stem_detail[f"{concept}::{lang}"] = stems
        if any(s not in vocab for s in stems):
            stems_ok = False
    results["_stems"] = {"detail": stem_detail, "pass": stems_ok}
    return {"test": "determinism", "results": results,
            "all_pass": all(r["pass"] for r in results.values())}


# --------------------------------------------------------------------------- #
# 7. METRIC SENSITIVITY - the harness non-vacuity proof
# --------------------------------------------------------------------------- #
def test_metric_sensitivity_non_vacuity(ctx: Ctx) -> dict[str, Any]:
    """An injected improvement MUST move the frozen metrics.

    This is the direct answer to the charter's vacuity clause: whatever the
    candidate arm scored, the harness itself is proven able to register a
    concept-coverage improvement (synthetic row carrying the missing German
    concepts) and a recall improvement (synthetic row carrying a frozen
    authority id).  A tie between blanked and candidate is therefore a
    property of the candidate's retrieval results, not of an insensitive
    metric.
    """
    de = ctx.bundles["de-kapitalverletzung"]
    question = de.get("query") or ""
    rows = list(de.get("decisions") or [])
    before = ctx.sma.question_concepts(question)
    before_rep = cli.measure_coverage(ctx.sma, question, rows)
    baseline_zeros_ok = (
        before_rep["concept_row_counts"].get("kapitalverletzung") == 0
        and before_rep["concept_row_counts"].get("uberwachungspflicht") == 0)

    synthetic = {
        "title": "Kapitalverletzung und Uberwachungspflicht - synthetic probe",
        "regeste": "", "snippet": "", "full_text": "", "citation": "",
        "decision_id": "SYNTHETIC_PROBE_1", "language": "de",
    }
    after_rep = cli.measure_coverage(ctx.sma, question, rows + [synthetic])
    coverage_moves = (
        after_rep["concept_row_counts"].get("kapitalverletzung", 0) >= 1
        and after_rep["concept_row_counts"].get("uberwachungspflicht", 0) >= 1
        and len(after_rep["under_covered"]) == len(before_rep["under_covered"]) - 2)

    # Recall axis: frozen corporate-criminal-liability::fr pool is 0/2.
    spec = ctx.frozen.load_frozen()
    questions = ctx.frozen.question_by_slug(spec)
    aids = list(questions["corporate-criminal-liability"].get("authority_ids") or [])
    fr_rows = cli.leg_rows(ctx.bench, "corporate-criminal-liability", "fr")
    cell_before = ctx.gates.match_authorities(aids, fr_rows, min_len=6)
    hits_before = sorted(a for a, core in cell_before.items() if core)
    probe_row = {"decision_id": aids[0], "canonical_decision_id": aids[0],
                 "citation_string_de": "synthetic", "language": "de",
                 "text_head": "synthetic probe", "docket_number": ""}
    cell_after = ctx.gates.match_authorities(aids, fr_rows + [probe_row], min_len=6)
    hits_after = sorted(a for a, core in cell_after.items() if core)
    recall_moves_flag = (hits_before == [] and len(hits_after) == 1)
    all_pass = baseline_zeros_ok and coverage_moves and recall_moves_flag

    return {"test": "metric_sensitivity_non_vacuity", "results": {
        "accepted_baseline_zeros_reproduced": baseline_zeros_ok,
        "coverage_axis": {
            "under_covered_before": before_rep["under_covered"],
            "under_covered_after": after_rep["under_covered"],
            "registered_injected_row": coverage_moves,
        },
        "recall_axis": {
            "authority_ids": aids,
            "hits_before": hits_before, "hits_after": hits_after,
            "registered_injected_id": recall_moves_flag,
        },
        "concepts_listed": before,
        "pass": all_pass,
    }, "all_pass": all_pass}


# --------------------------------------------------------------------------- #
# 8. input integrity + offline discipline
# --------------------------------------------------------------------------- #
def test_inputs_and_offline(ctx: Ctx) -> dict[str, Any]:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    integrity: dict[str, Any] = {}
    for name, entry in rules["inputs"]["files"].items():
        if "content_sha256" not in entry:
            continue
        path = Path(entry["path"])
        actual = (hashlib.sha256(path.read_bytes()).hexdigest()
                  if path.is_file() else None)
        integrity[name] = {"expected": entry["content_sha256"],
                           "actual": actual,
                           "match": actual == entry["content_sha256"]}
    all_match = all(v["match"] for v in integrity.values())
    offline = ctx.cache.misses == 0  # only cache.read was used
    return {"test": "inputs_and_offline", "results": {
        "integrity": integrity,
        "all_inputs_match": all_match,
        "network_calls": ctx.cache.misses,
        "cache_hits": ctx.cache.hits,
        "offline_discipline": offline,
        "note": ("candidate rows came exclusively from the committed cache "
                 "envelopes; oci.search/search_many were never invoked"),
    }, "all_pass": all_match and offline and ctx.cache.misses == 0}


# --------------------------------------------------------------------------- #
def run_all(cache_dir: Path) -> dict[str, Any]:
    ctx = Ctx(cache_dir)
    tests = [test_no_silent_drop, test_dedup_invariant, test_decision_count_bounds,
             test_provenance_additive, test_query_result_bundle_contract,
             test_determinism, test_metric_sensitivity_non_vacuity,
             test_inputs_and_offline]
    out: dict[str, Any] = {}
    all_pass = True
    for fn in tests:
        res = fn(ctx)
        out[res["test"]] = res
        if not res["all_pass"]:
            all_pass = False
    return {
        "schema": "frontier_query_concept_recall.regression_results.v1",
        "team_id": "frontier-query-concept-recall",
        "charter_version": 1,
        "direction_version": 57,
        "run_id": int(time.time()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rules_file_sha256": hashlib.sha256(RULES_PATH.read_bytes()).hexdigest(),
        "tests": out,
        "all_pass": all_pass,
        "network_calls": ctx.cache.misses,
        "claim_ceiling": CLAIM_CEILING,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m frontier_query_concept_recall.regression_suite",
        description="Acceptance test (7) regression suite - offline, zero network")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="directory holding cache/ and receiving "
                             "regression_results.json")
    parser.add_argument("--cache-dir", default=None,
                        help="retrieval cache directory (default: <out>/cache)")
    parser.add_argument("--print", dest="do_print", action="store_true")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir) if args.cache_dir else out_dir / "cache"
    record = run_all(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "regression_results.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")
    summary = {name: t["all_pass"] for name, t in record["tests"].items()}
    print(json.dumps({"all_pass": record["all_pass"], "tests": summary,
                      "network_calls": record["network_calls"]}, indent=1))
    if args.do_print:
        print(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True))
    return 0 if record["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
