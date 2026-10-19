"""Build the FROZEN plan for frontier-concept-seed-recall charter v1.

Everything here is computed from ACCEPTED, already-committed artefacts only:
the served bundles, the accepted question-native coverage record, the frozen
retrieval spec and the accepted retrieval-benchmark record.  There is no network
call, no model call, no corpus mining and no reading of this run's own output.

The plan is written to ``results/frontier/frontier-concept-seed-recall/RULES.json``
and COMMITTED BEFORE the harness issues a single search.  ``harness.py`` then
re-derives this plan from the same accepted inputs and refuses to run if it
differs from the committed bytes in any way: a plan that drifts after the
freeze is a void run, and the refusal is the evidence.

TARGET UNIT SELECTION (frozen, declared, computed before any candidate search)
-----------------------------------------------------------------------------
* Coverage units: served bundles whose ACCEPTED question-native coverage record
  reports a non-empty ``concepts_with_zero_rows``.
* Recall units: ``authority::baseline_lang_recall::<slug>::<lang>`` cells that
  the ACCEPTED record marks ``passed is not True`` with a non-empty ``missing``
  list.  Cells that pass and cells that are not measurable are NOT targeted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import inputs as I
from . import nlcs

SCHEMA = "frontier_concept_seed_recall.RULES.v1"
TEAM_ID = "frontier-concept-seed-recall"
CHARTER_VERSION = 1

#: Frozen caps.  Declared, not tuned.
MAX_CONCEPTS_PER_UNIT = 2
MAX_TOTAL_SEARCHES = 16

FROZEN_LATENCY = {"per_search_seconds": 30.0, "full_live_pass_seconds": 240.0,
                  "min_interval_seconds": 0.4}

#: Frozen endpoint parameters for BOTH arms.  Identical to the accepted
#: baseline's own parameters except for the ``query`` string, so the
#: head-to-head differs in exactly one variable.
FROZEN_SEARCH_PARAMS = {
    "path": "/decisions",
    "limit": "50",
    "offset": "0",
    "sort": "relevance",
    "fields": "full",
    "include_pinpoint": "false",
    "language_filter": None,
}

#: Declared amendments.  Every entry below was made BEFORE this file was
#: committed and BEFORE any search was issued, so none of them can be
#: post-hoc tuning.
AMENDMENTS = [
    {
        "id": "A1-morphology-rule-tables",
        "when": "during the offline dry run, before this file was committed and "
                "before any search was issued",
        "what": "the German, French and Italian plural rules were replaced with "
                "declared per-language rule tables (-ung/-heit/-keit/-schaft/-pflicht "
                "take -en; -al takes -aux; -eau takes -x; an already s/x/z-final French "
                "surface is idempotent with its singular emitted separately; Italian "
                "-o drops the -o and takes -i, -a takes -e, -e drops the -e and takes -i)",
        "why": "the first rule set emitted non-words ('Kapitalverletzungn', "
               "'Uberwachungspflichte', 'prouveeses', 'furtoe', 'astienee'). Emitting "
               "non-words into the query string would have measured the team's own "
               "generator rather than the hypothesis, and attributing that to the corpus "
               "would be the dishonest outcome rather than the honest negative",
        "direction": "affects ONLY the concept-seeded variant strings, never the A0 "
                     "baseline, the coverage metric, the recall metric, any threshold "
                     "and no frozen accepted file",
    },
]


def _frozen_leg_row_text(row: dict) -> str:
    """Text a frozen-leg search row offers for concept containment.

    The accepted coverage rule reads ``title/regeste/snippet/full_text/
    citation/decision_id``.  Frozen-leg cached rows carry none of the first four
    and use ``citation_string_*`` rather than ``citation``.  The frozen field set
    for THIS harness is therefore declared explicitly, in the same spirit and the
    same permissive (substring, can only over-report) direction as the accepted
    rule.  It is declared here, before measurement, and never adjusted after.
    """
    return " ".join(str(row.get(k) or "") for k in (
        "decision_id", "citation_string_de", "citation_string_fr",
        "citation_string_it", "text_head"))


def served_units(product_mount: Path | None = None) -> list[dict]:
    """Coverage units, with their ACCEPTED under-covered concepts."""
    sma, _, _ = I.load_evaluation_modules()
    accepted_cov = I.load_json(I.EVALUATION_MOUNT /
                              "results/evaluation/subject_match_audit/39113690481.json")
    entries = accepted_cov.get("question_native_coverage") or []
    if isinstance(entries, dict):  # tolerated shape drift, never assumed
        entries = [dict(v, served_question_id=k) for k, v in entries.items()]
    cov_q = {e["served_question_id"]: e for e in entries}
    units = []
    for qid in I.SERVED_QUESTIONS:
        qpath = I.question_path(qid, product_mount)
        qrec = I.load_json(qpath)
        bundle = I.load_json(I.bundle_path(qid, product_mount))
        text = qrec["question"]
        lang = qrec["language"]
        concepts = sma.question_concepts(text)
        acc = cov_q.get(qid) or {}
        under = list(acc.get("concepts_with_zero_rows") or [])
        variants = nlcs.build_unit_variants(text, lang, under, MAX_CONCEPTS_PER_UNIT)
        units.append({
            "unit_id": f"served::{qid}",
            "kind": "served_coverage",
            "question_id": qid,
            "language": lang,
            "question_text": text,
            "bundle_path": str(I.bundle_path(qid, product_mount)),
            "bundle_sha256": I.sha256_file(I.bundle_path(qid, product_mount)),
            "bundle_n_rows": len(bundle.get("decisions") or []),
            "accepted_question_concepts": list(concepts),
            "accepted_under_covered": under,
            "target_languages": [lang],
            "variants": variants,
        })
    return units


def frozen_recall_units() -> list[dict]:
    """Recall units: the accepted cells that FAIL with missing ids."""
    sma, _, _ = I.load_evaluation_modules()
    spec = I.load_json(I.EVALUATION_MOUNT /
                       "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    rec = I.load_json(I.EVALUATION_MOUNT /
                      "results/evaluation/retrieval_benchmark/39117425713.json")
    by_slug = {q["slug"]: q for q in spec["questions"]}
    units = []
    for gate in rec["verdict"]["gates"]:
        name = gate.get("gate") or ""
        if not name.startswith("authority::baseline_lang_recall::"):
            continue
        _, _, slug, lang = name.split("::")
        missing = list((gate.get("measured") or {}).get("missing") or [])
        if gate.get("passed") is True or not missing:
            continue
        qtext = by_slug[slug]["queries"]["baseline"][lang]
        concepts = sma.question_concepts(qtext)
        pool = [q for q in rec["queries"]
                if q.get("slug") == slug and q.get("channel") == "baseline"
                and q.get("language") == lang]
        rows = [r for q in pool for r in (q.get("rows") or [])]
        texts = [sma.deaccent(_frozen_leg_row_text(r)).lower() for r in rows]
        counts = {c: sum(1 for t in texts if c in t) for c in concepts}
        under = [c for c, n in counts.items() if n == 0]
        variants = nlcs.build_unit_variants(qtext, lang, under, MAX_CONCEPTS_PER_UNIT)
        units.append({
            "unit_id": f"frozen::{slug}::{lang}",
            "kind": "frozen_recall",
            "slug": slug,
            "language": lang,
            "channel": "baseline",
            "question_text": qtext,
            "frozen_authority_ids": list(by_slug[slug].get("authority_ids") or []),
            "accepted_missing_ids": missing,
            "accepted_gate_passed": gate.get("passed"),
            "a0_rows": len(rows),
            "accepted_question_concepts": list(concepts),
            "accepted_concept_row_counts": counts,
            "accepted_under_covered": under,
            "target_languages": [lang],
            "variants": variants,
        })
    units.sort(key=lambda u: u["unit_id"])
    return units


def build_plan(*, charter_version: int = CHARTER_VERSION,
               direction_version: int | None = None) -> dict:
    served = served_units()
    frozen = frozen_recall_units()
    units = sorted(served + frozen, key=lambda u: u["unit_id"])
    n_variants = sum(len(u["variants"]) for u in units)
    targeted = [u for u in units if u["variants"]]
    missing_ids = sorted({i for u in frozen for i in u["accepted_missing_ids"]})
    return {
        "schema": SCHEMA,
        "team_id": TEAM_ID,
        "charter_version": charter_version,
        "direction_version": direction_version,
        "template_id": nlcs.TEMPLATE_ID,
        "question": (
            "Does ONE deterministic, additive, free, in-budget natural-language "
            "concept-seeded retrieval arm, issuing full-sentence OpenCaseLaw variant "
            "queries that explicitly mention the question's frozen under-covered core "
            "concepts in each target language, raise (i) per-concept row coverage of "
            "those under-covered concepts on the bundles where the accepted baseline "
            "records zero, and/or (ii) recall of the frozen controlling-authority id "
            "sets on the cells the accepted frozen benchmark records as failing, with "
            "zero regression on any frozen retrieval gate, zero owner cost and no change "
            "to any rubric, bar, threshold, frozen file, packet byte or admission record?"),
        "hypothesis": (
            "Yes, plausibly, because the accepted bounded cause of the CLOSED "
            "frontier-query-concept-recall layer indicts the QUERY FORMAT, not the "
            "concept choice: that layer issued bare mined-term lists with no "
            "natural-language question text and returned 0 rows on de-kapitalverletzung, "
            "whereas the identical endpoint answers every accepted full-sentence baseline "
            "query with 50/50 rows. A full-sentence variant that says what the question "
            "asks and names the missing concept as phrased text is the untested input the "
            "accepted cause names. A bounded negative is an acceptable and expected "
            "outcome wherever the corpus genuinely lacks the concept; a zero-row result "
            "is itself load-bearing evidence separating a query-format gap from a "
            "corpus-side gap."),
        "predecessor_record": {
            "team_id": "frontier-query-concept-recall",
            "status": "CLOSED / OUTCOME_B_BOUNDED_NEGATIVE",
            "accepted_tip": "c242127a7f42293adcdda797d6973ed2ed45fc90",
            "prior_accept": "bd1b4d73aac1d26224f34584140135a99ece3bb1",
            "harness_results": "harness_results_39179862363.json",
            "harness_results_sha256":
                "a54f6a4fa64948652d04eab629436cf482d415f882160157bdc46431e0014c92",
            "integration_contract": "integration_contract_39179862363.json",
            "integration_contract_sha256":
                "08c64784673bdb09209bce4104af3c715900f9c714d85cd4a49a30c3a2139589",
            "rules_sha256":
                "c5447bac0605a8bcf8c3d1820bee56a5bb0e814365978ec1fa12ac189776ee9a",
            "bounded_cause_verbatim": (
                "TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR THE OPENCASELAW "
                "RELEVANCE INDEX"),
            "what_this_charter_does_not_do": (
                "The declined layer is NOT re-run, re-scored, re-dispatched or "
                "'improved'. Its A1 numbers appear here only as the historical "
                "comparator, published BESIDE this run's numbers and never in place "
                "of them. Any divergence from an accepted number is the headline."),
            "reproduction_targets": {
                "improved_fr_it_cells": 0,
                "reduced_under_covered_questions": 0,
                "de_added_search_status": 200,
                "de_added_search_n_results": 0,
                "de_under_covered": ["kapitalverletzung", "uberwachungspflicht"],
                "de_baseline_n_rows": 214,
                "failing_fr_it_cells": [
                    "corporate-criminal-liability::fr",
                    "corporate-criminal-liability::it",
                    "business-judgment-rule::fr",
                    "business-judgment-rule::it",
                    "petty-theft-dismissal::fr",
                    "petty-theft-dismissal::it",
                ],
                "missing_frozen_authority_ids": missing_ids,
            },
        },
        "inputs": {
            "read_only_mounts": {
                "product": str(I.PRODUCT_MOUNT),
                "evaluation": str(I.EVALUATION_MOUNT),
            },
            "digests": I.verify_digests(),
            "frozen_retrieval_spec_sha256":
                I.ACCEPTED_DIGESTS["frozen_retrieval_benchmark.json"],
            "freeze_record_sha256": I.ACCEPTED_DIGESTS["FREEZE_RECORD.json"],
            "accepted_benchmark_record": {
                "run_id": 39117425713,
                "path": str(I.EVALUATION_MOUNT /
                            "results/evaluation/retrieval_benchmark/39117425713.json"),
                "sha256": I.ACCEPTED_DIGESTS["retrieval_benchmark/39117425713.json"],
            },
            "accepted_question_native_coverage": {
                "run_id": 39113690481,
                "path": str(I.EVALUATION_MOUNT /
                            "results/evaluation/subject_match_audit/39113690481.json"),
                "sha256": I.ACCEPTED_DIGESTS["subject_match_audit/39113690481.json"],
            },
        },
        "definitions": {
            "concept_extraction": (
                "DELEGATED byte-identical to evaluation.subject_match_audit."
                "question_concepts: de-accented, lowercased, alnum-split tokens of the "
                "question text with len >= 5 and the frozen generic stoplist removed; "
                "order preserved; de-duplicated; UNCAPPED. This harness re-implements "
                "nothing."),
            "served_row_coverage": (
                "DELEGATED byte-identical to evaluation.subject_match_audit."
                "build_coverage: text = deaccent(row_match_text(row)).lower(); a concept "
                "is COVERED iff >= 1 row's text contains it as a substring. Substring "
                "containment can only over-report coverage, which is the conservative "
                "direction. concepts_with_zero_rows is the under-covered set. UNCHANGED "
                "from the accepted definition."),
            "frozen_leg_row_coverage": (
                "DECLARED for this run, in the accepted permissive direction: text = "
                "deaccent(decision_id + citation_string_de + citation_string_fr + "
                "citation_string_it + text_head).lower(); a concept is COVERED iff >= 1 "
                "row's text contains it as a substring. Frozen-leg search rows carry no "
                "title/regeste/snippet/full_text, so the accepted field set cannot be "
                "used; this substitution is declared before measurement and is never "
                "adjusted afterwards. It is used ONLY to pick the concept seeds, never "
                "to report a served-bundle coverage number."),
            "authority_recall": (
                "DELEGATED byte-identical to evaluation.retrieval_gate.gates."
                "match_authorities(authority_ids, rows, min_len=6) over the frozen "
                "authority_ids of frozen_retrieval_benchmark.json; recall = hits / "
                "len(authority_ids); a cell with authority_ids == [] is NOT MEASURABLE "
                "and is never counted as a pass. Per-language cells score the rows of "
                "that language's own query pool; the union cell scores all rows."),
            "authority_id_set": (
                "frozen.question_by_slug(spec)[slug]['authority_ids'] from "
                "frozen_retrieval_benchmark.json, sha256 187b0e54..., never regenerated."),
            "pools": {
                "A0_baseline_shipped": (
                    "served: the accepted bundle's own decisions, byte-reused from the "
                    "accepted mount; frozen legs: the accepted benchmark record's own "
                    "cached channel=='baseline' rows for (slug, language), byte-reused."),
                "A1_candidate_only": "the frozen variant's rows alone (secondary).",
                "A1_union": ("A0 rows plus the variant rows, deduplicated by "
                             "canonical_decision_id then decision_id -- the product's own "
                             "identity order; the headline cell number."),
            },
        },
        "arms": {
            "A0_baseline_shipped": (
                "the accepted baseline verbatim, byte-reused from accepted artefacts; "
                "never re-queried for a claim-bearing number"),
            "A1_natural_language_concept_seeded": (
                "A0 plus, per target unit, ONE additional OpenCaseLaw search per "
                "under-covered concept (cap " + str(MAX_CONCEPTS_PER_UNIT) + "), with the "
                "frozen NLCS-1 variant string and endpoint parameters identical to A0 "
                "except for the query string"),
            "A2_blanked_control": (
                "the same harness with an EMPTY variant string set; MUST reproduce A0 "
                "exactly -- every coverage count, every recall number and every row "
                "count. This charter does NOT inherit the predecessor's tie=>void clause: "
                "a tie between blanked and candidate is a BOUNDED NEGATIVE result, not a "
                "void and not a reason to re-run."),
            "A3_rotated_control": (
                "unit i seeded with unit j's frozen variant strings, where j is the next "
                "unit in the sorted unit order (wrapping); MUST NOT raise coverage or "
                "recall on unit i"),
            "A4_corpus_presence_diagnostic": (
                "AUXILIARY DIAGNOSTIC, NOT A CANDIDATE ARM. One bare-concept search per "
                "served under-covered concept, to separate a query-format gap from a "
                "corpus-side gap. Its numbers are NEVER eligible for OUTCOME_A, are never "
                "an adoptable arm and are never presented as a candidate result. It "
                "exists because the charter calls a zero-row natural-language result "
                "load-bearing only if the corpus-side alternative is also measured."),
        },
        "variant_construction": {
            "template_id": nlcs.TEMPLATE_ID,
            "rule": (
                "V = question_text + JOIN[lang] + surface(concept) + variants-apposition "
                "+ TAIL[lang]; surface() recovers the concept's own spelling from the "
                "accepted question text by de-accented case-insensitive token match; "
                "variants are the concept's own morphological forms (de plural -n and "
                "ae/oe/ue/ss spelling, fr/it plural rules, plus the NFKD accent-stripped "
                "form), de-duplicated."),
            "literals": nlcs.LITERALS,
            "prohibited": [
                "any synonym, translation or paraphrase not present in the accepted text",
                "any corpus mining or post-hoc vocabulary selection",
                "any model call",
                "any language for which no ACCEPTED question text exists",
                "any edit after this file is committed",
            ],
            "max_concepts_per_unit": MAX_CONCEPTS_PER_UNIT,
            "max_total_searches": MAX_TOTAL_SEARCHES,
        },
        "search_params": FROZEN_SEARCH_PARAMS,
        "latency_budget": FROZEN_LATENCY,
        "thresholds": {
            "outcome_A": {
                "coverage": (
                    "A1 adds >= 1 row carrying 'kapitalverletzung' or "
                    "'uberwachungspflicht' to the de-kapitalverletzung pool "
                    "(accepted definition: >= 1 row whose de-accented row text contains "
                    "the concept as a substring)"),
                "recall": (
                    "A1 recovers >= 1 of the " + str(len(missing_ids)) +
                    " missing frozen authority ids on any accepted-failing cell"),
                "non_regression": (
                    "every frozen gate that PASSES in accepted record "
                    "results/evaluation/retrieval_benchmark/39117425713.json still passes "
                    "with the A1 rows in the pool, recomputed with the accepted "
                    "evaluation.retrieval_gate.gates.evaluate on the accepted frozen spec"),
                "acceptance_tests": "(1) through (9) satisfied",
            },
            "outcome_B_bounded_negative": (
                "A1 adds zero concept-carrying rows to de-kapitalverletzung AND recovers "
                "zero missing frozen authority ids. Publish the exact zero-result cells "
                "with HTTP status and measured latency, beside -- never in place of -- the "
                "accepted predecessor record, and stop."),
            "non_regression_gates": [
                "duplicate::unique_ids", "counter::known_counter_recall",
                "source::rows_valid", "transport::all_queries_ok",
                "authority::baseline_lang_recall", "authority::baseline_recall",
                "norm::retrievable", "counter::limiting_marker_verified",
                "reproducible::cached_second_pass_identical",
            ],
            "latency_rule": (
                "every added call is disclosed with its measured wall time; a per-search "
                "or full-pass breach is NAMED in the verdict, never hidden and never "
                "made to invalidate a content number"),
            "no_vacuity_void_clause": (
                "THIS CHARTER DOES NOT INHERIT THE PREDECESSOR'S TIE=>VOID CLAUSE. A "
                "blanked control that ties the candidate is a measured bounded negative. "
                "The controls are reported honestly whatever they show."),
        },
        "acceptance_tests_1_to_9": {
            "1_freeze_first": (
                "this file is committed before any search; ordering is demonstrated from "
                "real git commit times, and a hand-written frozen_at_utc is NOT evidence"),
            "2_reproduce_first": (
                "the accepted coverage finding and the accepted OUTCOME_B headline numbers "
                "are reproduced BEFORE any new measurement; a non-reproduction is the "
                "headline and ends the run as a bounded negative"),
            "3_runnable_offline_harness": (
                "the harness emits per-bundle rows_per_concept, under_covered and "
                "frozen-authority recall per language in the accepted record shape, so "
                "accepted and new numbers publish in ONE side-by-side table"),
            "4_head_to_head": (
                "A0 and A1 in the same run on identical inputs, same endpoint parameters, "
                "same top_k, same cache, published beside the accepted benchmark cells"),
            "5_non_vacuity_proven": (
                "A2 blanked reproduces A0 exactly; A3 rotated does not raise coverage on "
                "its target; neither is asserted, both are measured"),
            "6_no_frozen_regression": "read-only re-scoring of the accepted frozen gates",
            "7_regression_suite": (
                "pins per-bundle decision-count bounds, dedup behaviour, provenance "
                "channel fields, every query_result_bundle contract field, and the "
                "invariant that no decision is dropped, duplicated or re-ranked out of "
                "existence by the additive arm"),
            "8_integration_contract": "see integration_contract_<run>.json",
            "9_write_scope": (
                "nothing under product/, evaluation/, results/product/, "
                "results/evaluation/, state/, directives/, .github/ or product/static/"),
        },
        "claim_ceiling": (
            "No artifact may assert that a map helps a jurist, that any authority is "
            "absent from the corpus, that any frozen bar is met or moved, or that any "
            "packet is fit to serve. Usefulness remains the human product gate's "
            "question and admission remains fail-closed. Concept-coverage counts are "
            "lexical coverage of a retrieved set, not a legal conclusion; a zero count "
            "is a retrieval signal, not proof of corpus absence. A zero-row natural-"
            "language concept-seeded search means: 'a natural-language search for the "
            "missing concept returned no rows - a retrieval signal, not proof of corpus "
            "absence'. Product decides adoption or decline under factory-wide "
            "requirement 21 and records the decision; silent non-consumption is not "
            "permitted."),
        "freeze_discipline": (
            "Committed before any search. Ordering is demonstrated from git commit times, "
            "not from a hand-written timestamp. Any edit after the first candidate result "
            "exists invalidates the run and must be declared as an amendment with what, "
            "why and direction. The run stops at its FIRST outcome; there is no threshold, "
            "phrasing or prompt tuning afterwards."),
        "pre_freeze_transport_probes": {
            "disclosure": (
                "Before this file was committed, FIVE free, key-less OpenCaseLaw GET "
                "/decisions probes were issued to establish that the endpoint is "
                "query-sensitive and to size the latency budget. They are disclosed here "
                "in full, with their exact query strings. NONE of them is a frozen "
                "candidate variant: the candidate strings below all append an apposition "
                "that no probe used, so no probe result is a candidate result and no "
                "probe number enters any coverage, recall, gate or verdict figure. The "
                "frozen template was fixed by the charter's own recipe "
                "(question text + concept + morphological variants), not by any probe's "
                "row counts or totals."),
            "n_probes": 5,
            "purpose": "transport control only: is the query parameter load-bearing, and "
                       "what is the per-search latency distribution",
            "observed": [
                {"label": "A0 de question (the accepted shipped query)",
                 "http_status": 200, "total": 254, "returned": 50,
                 "id_head_sha256_prefix": "568b8c4941a0", "latency_seconds": 12.270},
                {"label": "de natural-language probe (discarded, not a frozen variant)",
                 "http_status": 200, "total": 254, "returned": 50,
                 "id_head_sha256_prefix": None, "latency_seconds": 8.793},
                {"label": "SENSE-1 nonsense token control",
                 "http_status": 200, "total": 194, "returned": 50,
                 "id_head_sha256_prefix": "b3e1410ce7f8", "latency_seconds": 5.740},
                {"label": "SENSE-2 accepted fr baseline query for business-judgment-rule",
                 "http_status": 200, "total": 377, "returned": 50,
                 "id_head_sha256_prefix": "5edf30b2eea5", "latency_seconds": 20.600},
                {"label": "SENSE-3 bare de concept token list",
                 "http_status": 200, "total": 252, "returned": 50,
                 "id_head_sha256_prefix": "7668e2cb1200", "latency_seconds": 6.680},
            ],
            "conclusion": (
                "distinct query strings produce distinct totals and distinct ordered id "
                "heads, so the query parameter is load-bearing and a zero-row or "
                "zero-hit natural-language result is a property of the query and not of a "
                "dead parameter"),
            "latency_observed_range_seconds": [5.74, 20.60],
        },
        "units": units,
        "n_units": len(units),
        "n_targeted_units": len(targeted),
        "n_variants": n_variants,
        "frozen_missing_authority_ids": missing_ids,
        "amendments": AMENDMENTS,
        "amendment_discipline": (
            "Amendments are declared here, in the committed file, with what/why/direction, "
            "and are visible in git history. After the first candidate outcome number "
            "exists, no further amendment of any kind is permitted: the run stops at its "
            "first outcome and post-hoc tuning invalidates it."),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="emit the frozen concept-seed-recall plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--charter-version", type=int, default=CHARTER_VERSION)
    ap.add_argument("--direction-version", default=None)
    args = ap.parse_args(argv)
    plan = build_plan(
        charter_version=args.charter_version,
        direction_version=(int(args.direction_version)
                           if str(args.direction_version or "").isdigit() else None))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(plan, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({"out": args.out, "n_units": plan["n_units"],
                      "n_targeted_units": plan["n_targeted_units"],
                      "n_variants": plan["n_variants"],
                      "missing_ids": len(plan["frozen_missing_authority_ids"])},
                     indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())