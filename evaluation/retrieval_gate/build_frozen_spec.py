#!/usr/bin/env python3
"""Construct the frozen retrieval/counter-authority benchmark specification.

CONSTRUCTION PROVENANCE (this script exists so the frozen sample's derivation
is reproducible, not so the benchmark can be re-freezen):

* authority sets = ``required_citation_ids ∪ required_retrieval_ids`` of the
  ALREADY-FROZEN reality benchmark (``evaluation/reality_gate/frozen_benchmark.json``,
  sha ff57f556…).  The retrieval gate re-owns the same controlling authorities
  under retrieval semantics; it does not change that frozen spec.
* known counter/limiting authority ids = the union, over every accepted
  ``results/product/reality_check/*`` leg of the same slug, of
  ``cited_decisions[*]`` rows whose ``counter_status`` is a counter status
  (``evaluation/query_map/harness.COUNTER_STATUSES``), each with its source
  file + status recorded.  Label SOUNDNESS is not re-verified here (the
  frontier counter-label verdict covered a different, pre-fix population); the
  ids are treated as *known counter authorities identified by the product*,
  never as proven label truth.
* queries / language variants / norm + limitation token lists are authored here
  in FR/DE/IT and frozen with the rest of the spec.

The script refuses to overwrite an existing spec (no silent re-freeze path).
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path

_LANE = Path(__file__).resolve().parents[2]
if str(_LANE) not in sys.path:
    sys.path.insert(0, str(_LANE))

from evaluation.query_map.harness import COUNTER_STATUSES  # noqa: E402

SPEC_PATH = Path(__file__).resolve().parent / "frozen_retrieval_benchmark.json"
REALITY_SPEC = _LANE / "evaluation" / "reality_gate" / "frozen_benchmark.json"

# --------------------------------------------------------------------------- #
# hand-authored, frozen-with-the-spec query material (FR / DE / IT)
# --------------------------------------------------------------------------- #

QUERIES: dict[str, dict] = {
    "rent-default": {
        "baseline": {
            "fr": "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation "
                  "pour retard dans le paiement du loyer selon le droit suisse, et quelles "
                  "exceptions ou limites jurisprudentielles existent ?",
            "de": "Unter welchen Voraussetzungen kann der Vermieter einen Wohnmietvertrag "
                  "wegen Zahlungsverzug kündigen, und welche Ausnahmen oder Grenzen der "
                  "Rechtsprechung bestehen nach Schweizer Recht?",
            "it": "In quali condizioni il locatore può risolvere un contratto di locazione "
                  "per ritardo nel pagamento dell'affitto secondo il diritto svizzero, e "
                  "quali eccezioni o limiti giurisprudenziali esistono?",
        },
        "counter": {
            "fr": "Art. 257d al. 2 CO résiliation abusive exception limite reprise du loyer impayé",
            "de": "Art. 257d OR Kündigung Rechtsmissbrauch Ausnahme Grenze Mietzinsrückstand",
            "it": "art. 257d CO risoluzione abuso eccezione limite ritardo affitto arretrato",
        },
        "norm_tokens": ["257d"],
        "limitation_tokens": [
            "abus", "rechtsmissbrauch", "abusiv", "abuso", "unbillig",
            "eccezione", "exception", "ausnahme", "buona fede", "treu und glauben",
        ],
    },
    "corporate-criminal-liability": {
        "baseline": {
            "fr": "La responsabilité pénale de l'entreprise selon l'art. 102 CP est-elle "
                  "subsidiaire ou primaire, et pour quelles infractions ? Quelles exigences "
                  "d'organisation doivent être prouvées ?",
            "de": "Ist die Verantwortlichkeit des Unternehmens nach Art. 102 StGB subsidiär "
                  "oder primär, und für welche Straftaten? Welche Organisationspflichten "
                  "müssen nachgewiesen werden?",
            "it": "La responsabilità penale dell'impresa ex art. 102 CP è sussidiaria o "
                  "primaria, e per quali reati? Quali esigenze organizzative devono essere "
                  "provate?",
        },
        "counter": {
            "fr": "Art. 102 CP responsabilité primaire subsidiaire exception limite jurisprudence organisation",
            "de": "Art. 102 StGB primäre subsidiäre Verantwortlichkeit Ausnahme Grenze Rechtsprechung Organisationsmangel",
            "it": "art. 102 CP responsabilità primaria sussidiaria eccezione limite giurisprudenza organizzazione",
        },
        "norm_tokens": ["art. 102"],
        "limitation_tokens": [
            "ausnahme", "eccezione", "exception", "grenze", "limite", "einschränkung",
            "nicht eigenständig", "keine eigenständige", "non costituisce", "ne deroga",
            "kein eigenständiger", "delimitation", "abgrenzung",
        ],
    },
    "business-judgment-rule": {
        "baseline": {
            "fr": "Dans quelles conditions le juge suisse s'abstient-il de revoir une décision "
                  "commerciale d'un conseil d'administration au titre de la business judgment "
                  "rule, et quelles exceptions ou limites ressortent de la jurisprudence ?",
            "de": "Unter welchen Bedingungen enthält sich der Schweizer Richter der Überprüfung "
                  "eines Geschäftsentscheids des Verwaltungsrats aufgrund der Business Judgment "
                  "Rule, und welche Ausnahmen oder Grenzen ergeben sich aus der Rechtsprechung?",
            "it": "In quali condizioni il giudice svizzero si astiene dal riesaminare una "
                  "decisione commerciale del consiglio di amministrazione in applicazione "
                  "della business judgment rule, e quali eccezioni o limiti discendono dalla "
                  "giurisprudenza?",
        },
        "counter": {
            "fr": "business judgment rule exception limite responsabilité conseil d'administration information conflit d'intérêts",
            "de": "Business Judgment Rule Ausnahme Grenze Verwaltungsrat Informationspflicht Interessenkonflikt Haftung",
            "it": "business judgment rule eccezione limite consiglio di amministrazione informazioni conflitto di interessi responsabilità",
        },
        "norm_tokens": ["business judgment rule", "bjr"],
        "limitation_tokens": [
            "ausnahme", "eccezione", "exception", "grenze", "limite", "grenzen", "limiti",
            "pflichtwidrig", "violazione", "interessenkonflikt", "conflitto d'interessi",
            "conflit d'interets", "nicht hinreichend informiert",
        ],
    },
    "petty-theft-dismissal": {
        "baseline": {
            "fr": "Un vol de faible valeur commis par un employé justifie-t-il un licenciement "
                  "immédiat selon l'art. 337 CO ? Quelles circonstances font varier la réponse ?",
            "de": "Rechtfertigt ein geringfügiger Diebstahl durch einen Arbeitnehmer die "
                  "fristlose Kündigung nach Art. 337 OR? Welche Umstände verändern die Antwort?",
            "it": "Un furto di lieve entità commesso da un dipendente giustifica il "
                  "licenziamento immediato ex art. 337 CO? Quali circostanze modificano la "
                  "risposta?",
        },
        "counter": {
            "fr": "art. 337 CO licenciement immédiat vol de faible valeur exception proportionnalité limite",
            "de": "Art. 337 OR fristlose Kündigung geringfügiger Diebstahl Ausnahme Verhältnismäßigkeit Grenze",
            "it": "art. 337 CO licenziamento immediato lieve entità eccezione proporzionalità limite",
        },
        "norm_tokens": ["art. 337"],
        "limitation_tokens": [
            "verhältnismäßig", "proportion", "proporz", "billigkeit", "eccezione",
            "exception", "ausnahme", "grenze", "limite", "treu und glauben",
            "buona fede", "angemessen",
        ],
    },
}

SLUG_ORDER = [
    "rent-default",
    "corporate-criminal-liability",
    "business-judgment-rule",
    "petty-theft-dismissal",
]

COUNTER_COUNTER_STATUSES = tuple(COUNTER_STATUSES)


def _authority_ids(reality: dict) -> tuple[list[str], str]:
    out: list[str] = []
    for q in reality["questions"]:
        for key in ("required_citation_ids", "required_retrieval_ids"):
            for did in q.get(key) or []:
                if did not in out:
                    out.append(did)
    return out, (
        "required_citation_ids ∪ required_retrieval_ids of the frozen reality "
        "benchmark evaluation/reality_gate/frozen_benchmark.json "
        "(sha256 ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8)"
    )


def _counter_rows(reality_check_dir: Path) -> dict[str, list[dict]]:
    """Union of product-classified counter rows across accepted legs, per slug."""
    union: dict[str, dict[str, dict]] = {}
    files = sorted(glob.glob(str(reality_check_dir / "*.json")))
    for path in files:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        slug = data.get("slug")
        rows = data.get("cited_decisions")
        if not slug or not isinstance(rows, list):
            continue
        for row in rows:
            status = row.get("counter_status")
            did = str(row.get("decision_id") or "")
            if not did or status not in COUNTER_COUNTER_STATUSES:
                continue
            slot = union.setdefault(slug, {})
            if did not in slot:
                slot[did] = {
                    "id": did,
                    "counter_status": status,
                    "source_file": Path(path).name,
                    "snippet": str(row.get("snippet") or "")[:240],
                }
    return {slug: sorted(by_id.values(), key=lambda r: r["id"])
            for slug, by_id in union.items()}


def build(reality_check_dir: Path | None = None) -> dict:
    reality = json.loads(REALITY_SPEC.read_text(encoding="utf-8"))
    authority_by_slug = {
        q["slug"]: sorted({*(q.get("required_citation_ids") or []),
                           *(q.get("required_retrieval_ids") or [])})
        for q in reality["questions"]
    }
    counter_by_slug = _counter_rows(
        reality_check_dir or Path("/tmp/lex_accepted/product/results/product/reality_check"))

    questions = []
    for slug in SLUG_ORDER:
        material = QUERIES[slug]
        questions.append({
            "slug": slug,
            "record_language": "fr",
            "queries": material,
            "authority_ids": authority_by_slug.get(slug, []),
            "authority_set_provenance": _authority_ids(reality)[1],
            "known_counter_ids": counter_by_slug.get(slug, []),
            "known_counter_provenance": (
                "union of accepted results/product/reality_check/* legs for this slug: "
                "cited_decisions rows with a counter_status in "
                f"{list(COUNTER_COUNTER_STATUSES)}; product-classified, label soundness "
                "NOT re-verified by this benchmark"
            ),
        })

    return {
        "schema": "lex-frozen-retrieval-benchmark/1",
        "direction_version": 49,
        "frozen_at": "2026-10-16",
        "purpose": (
            "Smallest executable retrieval/counter-authority benchmark that can falsify "
            "the query-map product: does a plain OpenCaseLaw search (baseline, no "
            "query-map/counter-authority machinery) retrieve the frozen controlling "
            "authorities for the four observed reality-check questions, in FR/DE/IT, and "
            "can an explicit counter/limiting pass reach known counter authority?"
        ),
        "baseline_definition": (
            "one OpenCaseLaw GET /decisions call per (question, language, channel) with "
            "sort=relevance, fields=full, offset=0, limit from top_k — i.e. the same "
            "OpenCaseLaw result set WITHOUT query-map reranking, lexicon expansion or "
            "citation-neighbourhood expansion"
        ),
        "endpoint": "https://mcp.opencaselaw.ch/api/decisions",
        "user_agent": "LexMachina-Eval-RetrievalGate/1.0 (evaluation lane)",
        "max_requests_per_second": 2.5,
        "transport": {"timeout_seconds": 30.0, "retries": 3, "backoff_seconds": 1.5},
        "top_k": {"baseline": 50, "counter": 30},
        "latency_budgets": {
            "per_search_seconds": 30.0,
            "full_pass_seconds": 240.0,
            "rule": "one search call must return in < 30s; the whole live pass "
                    "(24 searches) must finish in < 240s",
        },
        "gate_semantics": (
            ">=1-of-set per authority/counter gate; a partial-set pass is a PASS naming "
            "the missing ids in measured.missing (same semantics as the frozen reality "
            "benchmark recall gates)"
        ),
        "language_rule": (
            "the baseline pool of a question is evaluated per query language (fr/de/it) "
            "and as the union of the three; cross-language gates fail when one language's "
            "own top-k misses every frozen authority"
        ),
        "reproducibility_rule": (
            "pass A is fetched live and written to the lane cache; pass B replays the "
            "same 24 URLs strictly offline and must reproduce identical raw-body sha256 "
            "and identical ordered id list per query"
        ),
        "pre_freeze_disclosure": (
            "two schema probes with a NON-frozen query (Konventionalstrafe Vertragsstrafe, "
            "limit 3 and 50; plus one generic probe query=business judgment rule limit=3 "
            "whose payload was only read to the first 400 chars) established response "
            "shape, field names, size and latency before freeze. No frozen query text was "
            "executed and no frozen authority-hit determination was made before the freeze "
            "record was written. The product-cache comparison in the run record is "
            "labelled EXPLORATORY because its design followed an exploratory scan of the "
            "accepted cache."
        ),
        "id_match_rules": {
            "method": (
                "a frozen authority id matches a retrieved row when the alnum-core of any "
                "of (row decision_id, canonical_decision_id, docket_number, "
                "citation_string_de/fr/it) equals the alnum-core of the frozen id; "
                "alnum-core = lowercase, drop every non-alphanumeric character, then strip "
                "repeated leading court tokens (bgestger, bstger, bger, bge, bg)"
            ),
            "rationale": (
                "frozen ids are legacy BGE-style (bger_4A_219_2015) while OpenCaseLaw "
                "returns ATF-style ids (bge_4A 219/2015) and citation strings (BGE 142 IV "
                "333); the core mapping is recorded per match in the run record so every "
                "hit is auditable"
            ),
            "min_core_length": 6,
        },
        "source_validity_rule": (
            "every retrieved row must carry a non-empty decision_id, a canonical_url on "
            "https with host mcp.opencaselaw.ch, and a language in {de, fr, it}"
        ),
        "duplicate_rule": "within one query response the alnum-core id must be unique",
        "weak_proxy_disclosure": (
            "norm_tokens and limitation_tokens are NECESSARY-NOT-SUFFICIENT lexical "
            "proxies (the same disclosure class as the frozen reality benchmark's weak "
            "truth gates): a hit shows the retrieved text speaks about the norm and about "
            "an exception/limitation term, it does not prove the decision is contrary or "
            "limiting authority. Nothing in this benchmark assigns a supporting/contrary "
            "label to any decision."
        ),
        "marker_rule": (
            "counter::limiting_marker_verified::<slug> passes when at least one "
            "COUNTER-channel row's text (title + regeste + snippet, HTML marks stripped, "
            "NFKD/diacritic-stripped/casefolded) contains at least one norm_token AND at "
            "least one limitation_token; the matching row (id, url, tokens, text head) is "
            "recorded as evidence"
        ),
        "exploratory_comparison_rule": (
            "with --accepted-product-root, the runner scans the ACCEPTED product "
            "query_cache search envelopes (params.query present, status 200) and reports, "
            "per question, how many frozen authority ids appear in ANY accepted search "
            "envelope and in the envelope whose query equals the frozen fr baseline query. "
            "TIER = EXPLORATORY (design followed an exploratory scan of that cache before "
            "this spec was frozen); reported as discrimination between an unreachable "
            "authority (retrieval-side) and an uncited-but-retrieved authority "
            "(answer-side), never as a claim-bearing gate."
        ),
        "questions": questions,
        "claim_ceiling": (
            "the benchmark measures retrieval reachability, source validity, duplicate "
            "suppression, cross-language robustness, counter reachability, latency and "
            "cached reproducibility of independent OpenCaseLaw searches for frozen "
            "questions; it cannot show that the map is useful to a jurist and it never "
            "re-classifies a decision as supporting/contrary"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    force = "--i-understand-this-is-a-deliberate-refreeze" in argv
    if SPEC_PATH.exists() and not force:
        print(f"refusing to overwrite existing frozen spec: {SPEC_PATH}", file=sys.stderr)
        return 2
    spec = build()
    text = json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    SPEC_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {SPEC_PATH}")
    print("sha256", hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest())
    for q in spec["questions"]:
        print(f"  {q['slug']}: authorities={len(q['authority_ids'])} "
              f"known_counter={len(q['known_counter_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
