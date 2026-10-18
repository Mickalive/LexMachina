"""Committed-evidence diagnostics behind the ONE bounded cause (audit repair F2).

Scope
-----
This module is REPORTING ONLY.  Every number it produces is derived from
inputs that already exist before this cycle:

* the frozen corpus sample the harness already builds
  (``expansion.CorpusSample`` over the three served bundles + the accepted
  benchmark record's embedded cached rows);
* the expansions the harness already emitted (their ``per_concept``
  provenance is carried in ``harness_results.json``);
* the committed retrieval-cache envelopes already disclosed in
  ``latency_budget``;
* the accepted benchmark record's own embedded query rows.

It issues no search, adds no retrieval call, changes no threshold, edits no
frozen file and touches no part of the candidate generator.  The harness's
claim-bearing coverage and recall numbers are computed elsewhere and are not
modified by anything here.

Why it exists
-------------
Audit gate ``CYCLE_39171009594`` F2 withdrew the previous bounded cause
("term-only expansion queries are too narrow for the OpenCaseLaw relevance
index") because the committed cache contradicts it: the same term-only shape
returned 50/50 rows on several cells.  The replacement cause must be exactly
what the committed cache shows - zero mined vocabulary for the failing German
concepts, cross-language citation-string pollution in the per-language sample,
terms expanded from already-covered concepts, and the latency profile of that
composition - ceilinged to THIS layer as built.  Fixing the generator itself
is post-outcome tuning under frozen RULES and is forbidden, so no repair is
proposed here.

Claim ceiling (verbatim, in force on every artifact this module produces)
-------------------------------------------------------------------------
No artifact may assert that a map helps a jurist, that any authority is
absent from the corpus, that any frozen bar is met or moved, or that any
packet is fit to serve.  Usefulness remains the human product gate's question
and admission remains fail-closed.  Concept-coverage counts are lexical
coverage of a retrieved set, not a legal conclusion, and a zero count is a
retrieval signal, not proof of corpus absence.
"""
from __future__ import annotations

from typing import Any, Iterable

from frontier_query_concept_recall import expansion as exp

#: The cause this module publishes, replacing the withdrawn statement.
WITHDRAWN_PRIOR_CAUSE = (
    "TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR THE OPENCASELAW RELEVANCE "
    "INDEX. Each A1 search sent a bare mined-vocabulary term list (up to 12 "
    "tokens) with no natural-language question text, while every accepted "
    "baseline query is a full sentence and returned 50/50 results."
)

CEILINGED_TO = (
    "THIS measured layer as built: 0/6 fr-it cells improved, 0/3 served "
    "questions reduced, 0/9 missing frozen authority ids recovered. It is "
    "NOT a claim about any other deterministic corpus-derived expansion, "
    "NOT a claim about the plain shipped baseline, and NOT a claim that any "
    "authority or concept is absent from the corpus."
)


# --------------------------------------------------------------------------- #
# 1. cross-language vocabulary witnesses
# --------------------------------------------------------------------------- #
def language_df(sample: exp.CorpusSample, token: str) -> dict[str, int]:
    """Document frequency of ``token`` in each language of the JOINED sample.

    "Joined" = the miner's own view, i.e. including the citation_string_de/fr/it
    triple; see :func:`own_language_document_frequency` for the unpolluted
    counterpart.
    """
    return {lang: sample.df(token, lang) for lang in exp.LANGUAGES}


def strict_dominant_language(sample: exp.CorpusSample, token: str) -> str | None:
    """The one language whose JOINED-sample document frequency is STRICTLY highest.

    Returns ``None`` on any tie, so an ambiguous token is never reported as
    foreign-language evidence.  Kept as a public helper because the tie rule is
    part of the published definitions; :func:`token_language_profile` is the
    reporting entry point.
    """
    df = language_df(sample, token)
    best = max(df.values())
    winners = [lang for lang, n in df.items() if n == best]
    return winners[0] if len(winners) == 1 and best > 0 else None


def own_language_document_frequency(
        bundle_rows: Iterable[dict],
        bench_queries: Iterable[dict]) -> dict[str, Any]:
    """Document frequency over OWN-AUTHORED text only, per language.

    Bundle rows contribute their own text fields (regeste/title/snippet/
    citation/docket_number); benchmark rows contribute ``text_head`` ONLY -
    deliberately EXCLUDING the ``citation_string_de/fr/it`` triple that
    :func:`expansion.CorpusSample.build` joins into every row.  This is the
    unpolluted counterpart of the miner's sample and is what makes a
    "foreign-language term" statement checkable without a tuned threshold.

    No threshold is applied here: raw counts only.
    """
    from collections import Counter
    df: dict[str, Counter] = {lang: Counter() for lang in exp.LANGUAGES}
    docs = {lang: 0 for lang in exp.LANGUAGES}

    def add(lang: str, text: str) -> None:
        docs[lang] += 1
        for tok in {t for t in exp.tokens(text)
                    if len(t) >= exp.MIN_TERM_CHARS and t.isalpha()}:
            df[lang][tok] += 1

    for row in bundle_rows or []:
        lang = str(row.get("language") or "").lower()
        if lang in df:
            add(lang, " \n ".join(str(row.get(f) or "") for f in (
                "regeste", "title", "snippet", "citation", "docket_number")))
    for query in bench_queries or []:
        for row in query.get("rows") or []:
            lang = str(row.get("language") or "").lower()
            if lang in df:
                add(lang, str(row.get("text_head") or ""))
    return {
        "definition": (
            "own-authored text only: bundle text fields for bundle rows, "
            "text_head ONLY for benchmark rows (citation_string_de/fr/it "
            "excluded on purpose); raw counts, no threshold"),
        "documents_per_language": dict(docs),
        "df": {lang: dict(sorted(counter.items()))
               for lang, counter in df.items()},
    }


#: The independent auditor's own cross-language witness, quoted and attributed
#: (audit gate CYCLE_39171009594, section F2, committed on
#: origin/cycle/frontier/frontier-query-concept-recall/39171009594/audit).
#: It is reported as AUDITOR-COMPUTED evidence: this producer does not claim to
#: have re-derived the "21 of 421" figure, because the auditor's token detector
#: definition was not published.  Everything else in this module is
#: producer-recomputed from committed bytes and is labelled as such.
AUDIT_COMMITTED_WITNESS = {
    "source": "results/audit/frontier/frontier-query-concept-recall/CYCLE_39171009594.md (gate CYCLE_39171009594, required_fixes F2)",
    "quote": (
        "CorpusSample.build() joins text_head + citation_string_de + "
        "citation_string_fr + citation_string_it into every benchmark row "
        "regardless of the row's language. Witness: 21 of 421 French "
        "documents in the sample carry Italian tokens, and the emitted lists "
        "contain them - effetti inside the de expansion, assicuratore inside "
        "an fr expansion, and the corporate-criminal-liability::fr query "
        "begins with Italian (prova risponde adeguata padrone cassation...)."),
    "recomputed_by_producer": [
        "the join itself (code fact in expansion.CorpusSample.build)",
        "all three citation strings non-empty on every benchmark row - see "
        "citation_join_pollution",
        "'effetti' is present in the emitted de-kapitalverletzung query string "
        "and 'prova risponde adeguata padrone cassation' opens the emitted "
        "corporate-criminal-liability::fr query string - both query strings are "
        "byte-identical in harness_results.json"],
    "not_recomputed_by_producer": (
        "the auditor's 21-of-421 token-detector figure; its detector "
        "definition was not published, so it is cited as auditor-computed "
        "evidence rather than restated as a producer measurement"),
}


def token_language_profile(*, sample: exp.CorpusSample,
                           own_df: dict[str, Any],
                           terms: Iterable[str],
                           target_language: str) -> dict[str, Any]:
    """Three explicitly-labelled frequency views of the emitted terms.

    Every view states its own definition, because a frequency in THIS sample is
    not a claim about which language a word belongs to.  The views are:

    * ``absent_from_target_own_text`` - the term occurs in NO own-authored
      document of the query's target language while occurring in another
      language's own text (the rigorous "foreign to the target sample" test);
    * ``highest_own_text_elsewhere`` - the term's own-authored document
      frequency is STRICTLY highest in another language (ties excluded);
    * ``highest_joined_sample_elsewhere`` - the same argmax rule but on the
      miner's JOINED sample, which is the polluted one; reported so the effect
      of the citation join is visible rather than hidden.
    """
    terms = [exp.norm(t) for t in terms]
    joined_df = own = None
    absent: list[dict[str, Any]] = []
    own_elsewhere: list[dict[str, Any]] = []
    joined_elsewhere: list[dict[str, Any]] = []

    def argmax_strict(counts: dict[str, int]) -> str | None:
        best = max(counts.values())
        winners = [lang for lang, n in counts.items() if n == best]
        return winners[0] if len(winners) == 1 and best > 0 else None

    for term in terms:
        own_counts = {lang: int(own_df["df"][lang].get(term, 0))
                      for lang in exp.LANGUAGES}
        joined_counts = language_df(sample, term)
        entry = {"term": term, "own_text_df": own_counts,
                 "joined_sample_df": joined_counts}
        if own_counts[target_language] == 0 and max(
                own_counts[l] for l in own_counts if l != target_language) > 0:
            absent.append(dict(entry))
        if argmax_strict(own_counts) not in (None, target_language):
            own_elsewhere.append(dict(entry))
        if argmax_strict(joined_counts) not in (None, target_language):
            joined_elsewhere.append(dict(entry))
    return {
        "target_language": target_language,
        "n_terms": len(terms),
        "definitions": {
            "absent_from_target_own_text": (
                "own-authored df in the target language == 0 AND > 0 in "
                "another language; no threshold"),
            "highest_own_text_elsewhere": (
                "own-authored df strictly highest in another language; ties "
                "excluded"),
            "highest_joined_sample_elsewhere": (
                "same argmax rule on the miner's joined sample, i.e. the view "
                "that INCLUDES the citation_string_de/fr/it join; shown to "
                "make the pollution visible, not as a lexical-identity claim"),
        },
        "n_absent_from_target_own_text": len(absent),
        "absent_from_target_own_text": absent,
        "n_highest_own_text_elsewhere": len(own_elsewhere),
        "highest_own_text_elsewhere": own_elsewhere,
        "n_highest_joined_sample_elsewhere": len(joined_elsewhere),
        "highest_joined_sample_elsewhere": joined_elsewhere,
        "caveat": (
            "these are document-frequency statements about this committed "
            "sample only; they are not a claim about which language a word "
            "belongs to, and not a claim that any authority is absent"),
    }


def cross_language_across_queries(
        sample: exp.CorpusSample,
        own_df: dict[str, Any],
        named_expansions: Iterable[tuple[str, exp.Expansion]]) -> dict[str, Any]:
    """Aggregate :func:`token_language_profile` over every emitted query."""
    per_query: dict[str, dict[str, Any]] = {}
    absent_examples: list[dict[str, Any]] = []
    own_elsewhere_examples: list[dict[str, Any]] = []
    joined_elsewhere_examples: list[dict[str, Any]] = []
    n_terms = n_absent = n_own = n_joined = 0
    for name, expansion in named_expansions:
        report = token_language_profile(
            sample=sample, own_df=own_df, terms=expansion.terms,
            target_language=expansion.language)
        per_query[name] = report
        n_terms += report["n_terms"]
        n_absent += report["n_absent_from_target_own_text"]
        n_own += report["n_highest_own_text_elsewhere"]
        n_joined += report["n_highest_joined_sample_elsewhere"]
        for key, bucket in (("absent_from_target_own_text", absent_examples),
                            ("highest_own_text_elsewhere", own_elsewhere_examples),
                            ("highest_joined_sample_elsewhere",
                             joined_elsewhere_examples)):
            for item in report[key]:
                bucket.append({"query": name, "target_language":
                               expansion.language, **item})
    return {
        "n_queries": len(per_query),
        "n_terms": n_terms,
        "n_absent_from_target_own_text": n_absent,
        "absent_from_target_own_text": absent_examples,
        "n_highest_own_text_elsewhere": n_own,
        "highest_own_text_elsewhere": own_elsewhere_examples,
        "n_highest_joined_sample_elsewhere": n_joined,
        "highest_joined_sample_elsewhere": joined_elsewhere_examples,
        "queries_with_absent_terms": sorted({
            e["query"] for e in absent_examples}),
        "audit_committed_witness": AUDIT_COMMITTED_WITNESS,
        "per_query": per_query,
    }



def citation_join_pollution(bench: dict) -> dict[str, Any]:
    """Structural witness: every benchmark row carries all three citations.

    ``expansion.CorpusSample.build`` joins ``text_head`` with
    ``citation_string_de`` + ``citation_string_fr`` + ``citation_string_it``
    for every benchmark row regardless of the row's language (RULES algorithm
    step 2 / step 3 input).  This counts, per row language, how many rows carry
    a non-empty citation string in each of the three languages.
    """
    by_lang: dict[str, dict[str, int]] = {}
    for query in bench.get("queries") or []:
        for row in query.get("rows") or []:
            lang = str(row.get("language") or "").lower()
            cell = by_lang.setdefault(
                lang, {"n_rows": 0, "with_citation_de": 0,
                       "with_citation_fr": 0, "with_citation_it": 0})
            cell["n_rows"] += 1
            for key in ("de", "fr", "it"):
                if str(row.get(f"citation_string_{key}") or "").strip():
                    cell[f"with_citation_{key}"] += 1
    totals = {"n_rows": 0, "with_citation_de": 0, "with_citation_fr": 0,
              "with_citation_it": 0}
    for cell in by_lang.values():
        for k in totals:
            totals[k] += cell[k]
    return {
        "code_fact": (
            "CorpusSample.build joins text_head + citation_string_de + "
            "citation_string_fr + citation_string_it into EVERY benchmark row "
            "regardless of row language, so the per-language sample is not "
            "language-pure"),
        "rows_by_language": dict(sorted(by_lang.items())),
        "totals": totals,
        "sample_documents_per_language": None,  # filled by the caller
    }


# --------------------------------------------------------------------------- #
# 2. mining gap: did the layer ask about the concepts that are missing?
# --------------------------------------------------------------------------- #
def concept_mining_gap(sample: exp.CorpusSample, expansion: exp.Expansion,
                       under_covered: Iterable[str],
                       covered: Iterable[str]) -> dict[str, Any]:
    """Per concept: how many terms the layer mined, and how many it emitted.

    ``holder_documents`` is the count of target-language sample documents whose
    normalised text contains the concept prefix actually passed to the miner -
    the direct witness for ``mined == []`` (no holder document, therefore no
    corpus vocabulary to mine, therefore no query about the gap).
    """
    under_covered = list(under_covered)
    covered = list(covered)
    lang = expansion.language
    per_concept = expansion.provenance()["per_concept"]

    # Reproduce the generator's merge order (synonyms, mined, stems) to know
    # which emitted term came from which concept.  Reading is enough: nothing
    # here rebuilds or re-runs the generator's decision, it only attributes the
    # already-emitted terms.
    assigned: dict[str, str] = {}
    attribution: dict[str, dict[str, Any]] = {}
    for concept in expansion.concepts:
        info = per_concept.get(concept) or {}
        candidates = [exp.norm(t) for t in (
            *(info.get("accepted_lexicon_synonyms") or []),
            *(info.get("mined") or []),
            *(info.get("stems") or []))]
        emitted_here = [t for t in candidates
                        if t in expansion.terms and t not in assigned]
        for t in emitted_here:
            assigned[t] = concept
        prefix = str(info.get("prefix") or "")
        holders = (sum(1 for flat in sample.joined.get(lang) or []
                       if prefix in flat) if prefix else 0)
        attribution[concept] = {
            "prefix": prefix,
            "under_covered": concept in under_covered,
            "holder_documents_in_sample": holders,
            "mined_terms": list(info.get("mined") or []),
            "stems": list(info.get("stems") or []),
            "accepted_lexicon_synonyms": list(
                info.get("accepted_lexicon_synonyms") or []),
            "emitted_terms_attributed": emitted_here,
        }

    terms_for_gap = [t for c in under_covered
                     for t in attribution.get(c, {}).get("emitted_terms_attributed", [])]
    terms_for_covered = [t for c in expansion.concepts if c not in under_covered
                         for t in attribution.get(c, {}).get("emitted_terms_attributed", [])]
    return {
        "language": lang,
        "emitted_terms": list(expansion.terms),
        "n_emitted_terms": len(expansion.terms),
        "under_covered_concepts": under_covered,
        "covered_concepts_at_baseline": covered,
        "per_concept": attribution,
        "n_terms_emitted_for_under_covered_concepts": len(terms_for_gap),
        "n_terms_emitted_for_already_covered_concepts": len(terms_for_covered),
        "terms_emitted_for_under_covered_concepts": terms_for_gap,
        "terms_emitted_for_already_covered_concepts": terms_for_covered,
        "mined_zero_for_every_under_covered_concept": all(
            not attribution.get(c, {}).get("mined_terms")
            and not attribution.get(c, {}).get("stems")
            for c in under_covered),
        "zero_holder_documents_for_every_under_covered_concept": all(
            attribution.get(c, {}).get("holder_documents_in_sample") == 0
            for c in under_covered),
        "reads_as": (
            "the layer emitted NO term derived from the concepts the question "
            "is actually missing; every emitted term expands a concept the "
            "baseline already covers"),
    }


# --------------------------------------------------------------------------- #
# 3. yield and latency profile of that exact term composition
# --------------------------------------------------------------------------- #
def search_yield_profile(cells: list[tuple[str, int, int]]) -> dict[str, Any]:
    """``cells`` = (cell name, n_results, status) for all added searches."""
    n = len(cells)
    rows = [{"cell": c, "n_results": r, "status": s} for c, r, s in cells]
    return {
        "n_added_searches": n,
        "n_status_200": sum(1 for _, _, s in cells if s == 200),
        "n_zero_result": sum(1 for _, r, _ in cells if r == 0),
        "n_1_to_9_rows": sum(1 for _, r, _ in cells if 0 < r < 10),
        "n_ge_13_rows": sum(1 for _, r, _ in cells if r >= 13),
        "n_full_page_50": sum(1 for _, r, _ in cells if r >= 50),
        "per_cell": rows,
        "reads_as": (
            "the added queries DID retrieve - the failure is what they "
            "retrieved relative to the missing concepts and frozen ids, not "
            "that the index rejected the query shape"),
    }


def latency_profile(budget: dict[str, Any]) -> dict[str, Any]:
    """The frozen per-search budget measured on the ORIGINAL live calls."""
    calls = budget.get("per_search_calls") or []
    lat = [float(c.get("latency_seconds") or 0.0) for c in calls]
    over = [x for x in lat if x >= float(budget.get("per_search_seconds", 30.0))]
    return {
        "per_search_budget_seconds": budget.get("per_search_seconds"),
        "n_added_calls": len(calls),
        "n_calls_over_per_search_budget": len(over),
        "max_seconds": round(max(lat), 3) if lat else 0.0,
        "sum_seconds": round(sum(lat), 3) if lat else 0.0,
        "full_live_pass_budget_seconds": budget.get("full_live_pass_seconds"),
        "full_pass_re_verifiable_from_cache": False,
        "note": (
            "wall times of the ORIGINAL live calls as disclosed by the "
            "committed cache envelopes; a cached replay costs no network but "
            "does not make the original call cheaper"),
    }


# --------------------------------------------------------------------------- #
# 4. the one bounded cause
# --------------------------------------------------------------------------- #
def build_bounded_cause(*, de_gap: dict[str, Any],
                        cross_language: dict[str, Any],
                        citation_pollution: dict[str, Any],
                        yield_profile: dict[str, Any],
                        latency: dict[str, Any],
                        recovered_ids: int,
                        missing_ids: int,
                        mining_gaps: dict[str, dict[str, Any]] | None = None,
                        audit_gate: str = "CYCLE_39171009594") -> dict[str, Any]:
    """Assemble the single bounded cause, evidence first, ceiling in force."""
    gap_terms = de_gap.get("terms_emitted_for_already_covered_concepts") or []
    zero_mined = de_gap.get("under_covered_concepts") or []
    poll = citation_pollution.get("totals") or {}
    foreign = [f"{e['query']}:{e['term']}"
               for e in (cross_language.get("absent_from_target_own_text") or [])]
    audit_witness = cross_language.get("audit_committed_witness") or {}

    statement = (
        "MEASURED CAUSE, CEILINGED TO THIS LAYER AS BUILT: the layer never "
        "asked about the gap. On de-kapitalverletzung it mined ZERO corpus "
        "vocabulary for both under-covered concepts "
        f"({', '.join(zero_mined)}: mined == [] and stems == [] for each, with "
        "0 holder documents for their prefixes in the miner's joined German "
        f"view of { (citation_pollution.get('sample_documents_per_language') or {}).get('de') } "
        "documents), so all "
        f"{de_gap.get('n_emitted_terms')} emitted terms expand concepts the "
        "baseline already covers ("
        f"{', '.join(sorted({c for c, a in (de_gap.get('per_concept') or {}).items() if a.get('emitted_terms_attributed') and not a.get('under_covered')})) or 'none'}); "
        "no emitted term derives from either gap concept. The per-language "
        "sample is cross-language polluted BY CONSTRUCTION: "
        f"CorpusSample.build joins citation_string_de/fr/it into every "
        f"benchmark row regardless of row language, so "
        f"{poll.get('with_citation_it')} of {poll.get('n_rows')} benchmark rows "
        "carry a non-empty Italian citation string, "
        f"{poll.get('with_citation_fr')} carry a French one and "
        f"{poll.get('with_citation_de')} a German one, and "
        f"{cross_language.get('n_absent_from_target_own_text')} of "
        f"{cross_language.get('n_terms')} emitted terms occur in NO "
        "own-authored document of their query's target language while "
        "occurring in another language's own text"
        + (f" (e.g. {', '.join(foreign[:4])})" if foreign else "")
        + "; a further "
        f"{cross_language.get('n_highest_joined_sample_elsewhere')} of "
        f"{cross_language.get('n_terms')} terms are strictly more frequent in "
        "another language inside the miner's JOINED sample, which is exactly "
        "the join effect. The independent auditor's own witness (quoted, "
        "attributed, auditor-computed) records the same mechanism with named "
        "terms: "
        f"\"{(audit_witness.get('quote') or '')[:220]}...\". Those bare-term "
        "queries DID return rows ("
        f"{yield_profile.get('n_ge_13_rows')} of "
        f"{yield_profile.get('n_added_searches')} added searches returned >=13 "
        f"rows, {yield_profile.get('n_full_page_50')} returned a full 50-row "
        "page), so the shape retrieves; it retrieves terms sourced from the "
        "wrong concepts and a language-polluted sample, and the composition is "
        "slow: "
        f"{latency.get('n_calls_over_per_search_budget')} of "
        f"{latency.get('n_added_calls')} added calls breached the frozen "
        f"<{latency.get('per_search_budget_seconds')}s per-search budget "
        f"(max {latency.get('max_seconds')}s, sum {latency.get('sum_seconds')}s). "
        "Across the frozen legs the candidate-only channel recovered "
        f"{recovered_ids} of {missing_ids} missing frozen authority ids."
    )

    return {
        "one_bounded_cause": statement,
        "status": f"REPLACES the cause withdrawn by audit gate {audit_gate} F2",
        "withdrawn_prior_cause": {
            "text": WITHDRAWN_PRIOR_CAUSE,
            "withdrawn": True,
            "why_withdrawn": (
                "contradicted by the committed cache: the same term-only shape "
                "returned 50/50 rows on several cells, both failing German "
                "concepts mined zero terms, and the per-language sample is "
                "cross-language polluted by the citation_string join"),
        },
        "evidence": {
            "mining_gap_for_the_missing_concepts": de_gap,
            "mining_gap_all_served_questions": mining_gaps or {},
            "terms_from_already_covered_concepts": gap_terms,
            "cross_language_profile_of_emitted_terms": cross_language,
            "citation_string_join_pollution": citation_pollution,
            "added_search_yield": yield_profile,
            "latency_profile": latency,
        },
        "ceilinged_to_this_layer_as_built": CEILINGED_TO,
        "generator_fix_not_proposed": (
            "the generator-side defect these witnesses expose is NOT repaired "
            "and NOT proposed: any change to it now would be post-outcome "
            "tuning under frozen RULES and is forbidden by the charter stop "
            "rule and by audit gate CYCLE_39171009594 F2"),
        "what_this_does_not_claim": (
            "it does not claim the corpus lacks these authorities or concepts; "
            "a retrieval miss is a retrieval signal, not proof of absence"),
    }


__all__ = [
    "WITHDRAWN_PRIOR_CAUSE",
    "CEILINGED_TO",
    "language_df",
    "strict_dominant_language",
    "own_language_document_frequency",
    "AUDIT_COMMITTED_WITNESS",
    "token_language_profile",
    "cross_language_across_queries",
    "citation_join_pollution",
    "concept_mining_gap",
    "search_yield_profile",
    "latency_profile",
    "build_bounded_cause",
]
