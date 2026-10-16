"""Independent adversarial RETRIEVAL pass (product-owned).

Why this module exists
----------------------
The accepted, independently audited measurement
``frontier-adversarial-discoverability`` (audit CYCLE_38794235870, gate=PASS,
named verdict ``CLASSIFICATION_ONLY``) established on three accepted bundles
that every counter-authority row entered through a retrieval channel the
initial broad pass had already used::

    retrieval_independence = FAIL   (0 of 8 counter rows used a new channel)
    counter channels       = {search, search.language_filter}
    counter ranks          = 1, 2, 3, 4, 6, 13, 14, 27   (all top-ranked already)

The single bounded candidate cause that audit named is exactly what this module
removes: the product's adversarial stage classified a bounded shortlist drawn
from the *initial* pool.  A visualization cannot reveal an authority that
retrieval never looked for (Master Prompt, "Retrieval-first doctrine"), and the
canonical product flow requires "an independent adversarial retrieval pass
against the provisional answer".

What this module adds
---------------------
A real second retrieval route, run **after** the provisional answer exists:

1. :func:`plan_adversarial_queries` builds counter-directed probes from the
   *answer* (its key legal terms) plus a DE/FR/IT limitation vocabulary.  These
   are not variants of the initial query, so they are not routes the initial
   pass used.
2. :func:`fetch_adversarial_candidates` issues those probes through the ACCEPTED
   OpenCaseLaw adapter's client/cache/transport/normalizer - reused, not
   reimplemented - and labels each row with its own channel
   (``adversarial.<intent>``).
3. Every decision the initial pass already put on the map, by id **and** by
   court+docket identity, is excluded.  What survives is genuinely unseen
   authority (``pool_never_seen``).
4. :func:`apply_adversarial_pass` joins the survivors into the existing map
   through the existing incremental projection seam
   (:func:`progressive.map_model_from_bundle` + :func:`qmap.build_map`), so
   already-rendered points never move.

Classification honesty (Master Prompt non-negotiable: "Never classify a case as
supporting/contrary/limiting unless the evidence supports that label"): a row is
only labelled as counter-authority when a verbatim sentence from its own decision
text contains an explicit limitation marker **and** shares a topical term with the
answer/query, **and** the sentence is neither procedural Eintretens boilerplate
nor a disposal/dismissal narration (a rejected appeal means the challenged ruling
stood, which is the opposite of counter-authority).  Hydration is bounded and
lazy, and unlabelled survivors stay ``counter_status="none"`` - they keep recall
without inventing a legal label.

Scope: this module is product-owned by construction.  ``frontier/**`` is outside
product write scope, so the new channel is declared here and recorded in bundle
provenance instead of being added to the accepted adapter's channel enum.
"""
from __future__ import annotations

import copy
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_ROOT = REPO_ROOT / "frontier" / "frontier-query-retrieval"
if RETRIEVAL_ROOT.is_dir() and str(RETRIEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_ROOT))

from ocl_adapter.config import AdapterConfig  # noqa: E402
from ocl_adapter.cache import FileCache  # noqa: E402
from ocl_adapter.client import OCLClient  # noqa: E402
from ocl_adapter.pipeline import make_transport  # noqa: E402
from ocl_adapter.ratelimit import RateLimiter, RequestBudget  # noqa: E402
from ocl_adapter.normalize import normalize_search_hit, normalize_decision_detail  # noqa: E402

from .answer import split_sentences  # noqa: E402
from .retrieval import tokenize  # noqa: E402

#: Bumped whenever the plan, the channel names or the labelling rule change, so
#: a bundle's provenance identifies the exact adversarial contract it was built
#: under.  Never reuse an old value for new behaviour.
#:
#: /2 (cycle 38831241913, audit-required repair of 38828034436):
#: - probes interleave the per-language intent terms (D1: /1 truncated every
#:   intent list to German-first entries, so no Italian term was ever issued);
#: - an empty answer vocabulary now yields an *empty* plan (D4: /1's docstring
#:   documented a vacuous-pass guard that did not exist);
#: - labelling is topic-gated, disposal/boilerplate-guarded, and reports only
#:   the markers present in the cited evidence sentence (D2: /1 licensed labels
#:   from negation-blind, boilerplate-blind, topic-blind substrings).
ADVERSARIAL_RETRIEVAL_VERSION = "adversarial_retrieval/2"

#: The product's *own* channels.  These strings are disjoint from the accepted
#: adapter's channel inventory (``search``, ``search.language_filter``,
#: ``leading_case``, ``citation.incoming``, ``citation.outgoing``,
#: ``decision_lookup``) by construction, which is what makes the independence
#: claim checkable rather than asserted.
CHANNEL_EXCEPTION = "adversarial.exception"
CHANNEL_CONTRARY = "adversarial.contrary"
CHANNEL_MINORITY = "adversarial.minority"
CHANNEL_OLDER_LINE = "adversarial.older_line"

ADVERSARIAL_CHANNELS = (CHANNEL_EXCEPTION, CHANNEL_CONTRARY, CHANNEL_MINORITY, CHANNEL_OLDER_LINE)

#: Counter-directed intents.  Each is a distinct *purpose*, so its rows can be
#: explained to a jurist instead of appearing as undifferentiated "counter".
#:
#: Terms are ``(language, term)`` pairs.  The planner interleaves them across
#: languages (cycle 38828034436 audit D1: truncating the flat list kept only
#: German-first entries, so the shipped probes carried zero Italian vocabulary
#: while the report claimed DE+FR+IT).  Probe-only disposal words (``abgelehnt``,
#: ``rejeté`` …) are kept here on purpose — they *retrieve* contrary discussion —
#: but they are deliberately absent from :data:`EVIDENCE_MARKERS`, because on a
#: real decision they usually mean an appeal failed and the challenged ruling
#: stood, which is the opposite of counter-authority.
INTENTS: dict[str, dict[str, Any]] = {
    "exception": {
        "channel": CHANNEL_EXCEPTION,
        "label": "Ausnahme / exception / eccezione",
        # the decision states an exception, reservation or carve-out
        "terms": [
            ("de", "ausnahme"), ("fr", "exception"), ("it", "eccezione"),
            ("de", "vorbehalt"), ("fr", "réserve"), ("it", "riserva"),
            ("de", "einschränkung"), ("fr", "excepté"), ("it", "fatta eccezione"),
            ("de", "ausgenommen"), ("fr", "sous réserve"), ("fr", "sauf"),
            ("de", "vorbehalten"),
        ],
    },
    "contrary": {
        "channel": CHANNEL_CONTRARY,
        "label": "abweichende Auffassung / contrary position / posizione contraria",
        "terms": [
            ("de", "abweichend"), ("fr", "a contrario"), ("it", "contrario"),
            ("de", "entgegen"), ("fr", "contraire"), ("it", "respinto"),
            ("de", "anderer auffassung"), ("fr", "contrairement"), ("it", "inammissibile"),
            ("de", "abgelehnt"), ("fr", "rejeté"),
            ("de", "abgewiesen"), ("fr", "écarté"),
        ],
    },
    "minority": {
        "channel": CHANNEL_MINORITY,
        "label": "Minderheitslinie / ligne minoritaire / minoranza",
        "terms": [
            ("de", "minderheit"), ("fr", "minorité"), ("it", "minoranza"),
            ("de", "minderheitsmeinung"), ("fr", "minoritaire"), ("it", "dissenso"),
            ("de", "dissens"), ("fr", "avis minoritaire"),
            ("de", "abweichende meinung"),
        ],
    },
    "older_line": {
        "channel": CHANNEL_OLDER_LINE,
        "label": "ältere Rechtsprechung / ligne plus ancienne / linea precedente",
        "terms": [
            ("de", "ältere rechtsprechung"), ("fr", "ancienne jurisprudence"),
            ("it", "precedente giurisprudenza"),
            ("de", "früher"), ("fr", "autrefois"), ("it", "in passato"),
            ("de", "früheren rechtsprechung"), ("fr", "désormais"),
            ("de", "mittlerweile"),
        ],
    },
}

#: Languages in probe interleaving order.  Every intent above carries at least
#: two terms per listed language, so a 9-term probe is always DE+FR+IT.
PROBE_LANGUAGES = ("de", "fr", "it")

#: Cheap, high-precision *marker* lexicon used only to decide whether a retrieved
#: decision's own text licenses a counter label.  Kept separate from the query
#: vocabulary above: these are substrings matched in the hydrated decision text,
#: so they are language- and morphology-tolerant.
#:
#: Two deliberate omissions versus /1 (audit D2):
#: - disposal/dismissal words (``abgelehnt``, ``abgewiesen``, ``rejeté``,
#:   ``écarté``, ``respinto``, bare ``entgegen``) are NOT here.  On real Swiss
#:   decisions they usually mark that an appeal was *rejected* and the challenged
#:   ruling *stood*, so a substring hit on them licensed affirmatively inverted
#:   counter labels (audit examples: ``bge_136 III 190``, ``bge_115 II 78``,
#:   ``bge_111 II 384``, ``bge_123 III 124``).  They remain in the probe
#:   vocabulary above, where they help *retrieve* contrary discussion;
#: - procedural Eintretens formulas are handled at sentence level by
#:   :data:`BOILERPLATE_SENTENCE_PATTERNS`.
EVIDENCE_MARKERS: dict[str, tuple[str, ...]] = {
    "exception": (
        "ausnahme", "vorbehalt", "einschränkung", "ausgenommen",
        "exception", "réserve", "excepté", "sauf", "eccezione", "riserva",
    ),
    "contrary": (
        "abweichend", "a contrario", "contraire", "contrairement", "contrario",
    ),
    "minority": (
        "minderheit", "minderheitsmeinung", "dissens", "minorité", "minoritaire",
        "minoranza", "dissenso",
    ),
    "older_line": (
        "ältere rechtsprechung", "älteren rechtsprechung", "früheren rechtsprechung",
        "frühere rechtsprechung", "älteren bundesgerichtsentscheid",
        "ancienne jurisprudence", "autrefois", "in passato",
    ),
}

#: Sentences matching these patterns are procedural boilerplate (the BGer
#: Eintretens formula and its siblings).  A marker inside such a sentence never
#: licenses a counter label: routine procedural passages carry no legal weight
#: (audit D2, boilerplate-only category).
BOILERPLATE_SENTENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"unter vorbehalt der gen[üu]ndenden begr[üu]ndung", re.I),
    re.compile(r"vorbehalt[^.]{0,60}einzutreten", re.I),
    re.compile(r"einzutreten[^.]{0,60}vorbehalt", re.I),
    re.compile(r"vereinfachten verfahren als ausnahme", re.I),
    re.compile(r"vorbehalt des rechtsmissbrauchs", re.I),
)

#: Sentences matching these patterns narrate a *dismissal*: a recours/Berufung/
#: Beschwerde was rejected, so the challenged ruling stood.  Such a sentence
#: cannot license ``candidate-contrary`` — the audit's four affirmatively
#: inverted rows were all licensed by exactly this construction.
DISPOSAL_SENTENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(recours|berufung|beschwerde|recurso|ricorso)[^.]{0,80}"
        r"(rejet\w*|abgewiesen|abgelehnt|\u00e9cart\w*|inammissibile|respinto)", re.I),
    re.compile(
        r"(rejet\w*|abgewiesen|abgelehnt|\u00e9cart\w*|inammissibile|respinto)[^.]{0,80}"
        r"(recours|berufung|beschwerde|recurso|ricorso)", re.I),
    re.compile(r"nicht entgegen", re.I),
)

#: Legal terms lifted from the provisional answer.  Keeping the probe close to
#: the answer's own vocabulary is what makes the pass *adversarial to the
#: answer* rather than a second copy of the first query.
_ANSWER_STOP = frozenset(
    """der die das und des den dem ein eine einer eines einem einen auch als bei nach noch nur oder
    vom von vor zum zur über für mit sich sie sind ist war wird werden wurde wurden haben hat hatte aus
    auf an am im ins aber doch denn le la les de des du un une est sont et en dans que qui pour pas sur
    plus par au aux il ils elle elles nous vous leur son sa ses ce cette ces dont comme avec di del
    della dello che non uno dei degli delle dal allo alla al ai agli sul sulla per con come più sono
    era stato stata hanno aveva perché nel cui alle quale quali questo questa questi queste anche tra
    fra può possono deve devono essere ogni dove quando ohne sopra sotto dopo prima mentre the and for
    are with from that this have has had were was will""".split()
)

#: Fixed order in which intent markers are consulted when a row's own text
#: carries a marker from a different intent than the probe that retrieved it.
INTENT_ORDER = ("exception", "contrary", "minority", "older_line")

#: Evidence-supported counter labels.  A row never receives one of these values
#: unless a verbatim sentence of its own text carries the matching marker.
COUNTER_STATUS_BY_INTENT = {
    "exception": "candidate-limiting",
    "contrary": "candidate-contrary",
    "minority": "contrary_or_exception",
    "older_line": "candidate-limiting",
}

DEFAULT_MAX_NEW = 40
DEFAULT_HYDRATE_TOP = 12
DEFAULT_PAGE_SIZE = 25
#: 4 probe pages + bounded hydration.  The initial pass gets its own budget;
#: starving this one would silently drop an intent, which is how the older_line
#: probe failed to run in live cycle 38828034436 attempt 1.
DEFAULT_MAX_REQUESTS = 24


# --------------------------------------------------------------------------
# 1. plan: what to ask, against the provisional answer
# --------------------------------------------------------------------------

def answer_key_terms(answer_prose: str, *, limit: int = 8) -> list[str]:
    """Deterministic key legal terms of the provisional answer.

    Answer-derived rather than query-derived on purpose: the adversarial pass
    must attack the *proposition*, not the question wording.
    """
    counts: dict[str, int] = {}
    for token in tokenize(answer_prose or ""):
        if token in _ANSWER_STOP or len(token) < 4 or token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in ranked[:limit]]


def interleave_intent_terms(terms: list[tuple[str, str]], k: int) -> list[str]:
    """Round-robin the ``(language, term)`` pairs so a truncated probe stays multilingual.

    Cycle 38828034436 audit D1: slicing the flat German-first list kept only DE
    (+ latin/FR stragglers) terms, so no Italian term was ever issued while the
    report claimed DE+FR+IT coverage.  Interleaving keeps every language the
    intent defines alive at any ``k >= number of languages``.
    """
    by_lang: dict[str, list[str]] = {lang: [] for lang in PROBE_LANGUAGES}
    for lang, term in terms:
        by_lang.setdefault(lang, []).append(term)
    out: list[str] = []
    idx = {lang: 0 for lang in by_lang}
    while len(out) < max(0, int(k)):
        added = False
        for lang in PROBE_LANGUAGES:
            if len(out) >= max(0, int(k)):
                break
            i = idx.get(lang, 0)
            if i < len(by_lang.get(lang, [])):
                out.append(by_lang[lang][i])
                idx[lang] = i + 1
                added = True
        if not added:
            break
    return out


def plan_adversarial_queries(
    query: str,
    answer_prose: str = "",
    *,
    max_intents: int = 4,
    per_intent_terms: int = 9,
) -> list[dict[str, Any]]:
    """Build the counter-directed probes. Pure and deterministic.

    Returns ``[{intent, channel, label, query, terms}]``.  An empty list means
    the answer carries no usable legal vocabulary — the caller records a
    vacuous pass with a skip reason rather than fabricating topic-free probes
    (cycle 38828034436 audit D4: the /1 docstring documented this guard but the
    code issued four marker-word-only searches against an empty answer).

    Default ``per_intent_terms=9`` interleaves three terms per language for
    every intent (audit D1); the intent vocabulary is round-robined across
    DE/FR/IT so no language can be silently truncated away.
    """
    key_terms = answer_key_terms(answer_prose)
    if not key_terms:
        return []
    out: list[dict[str, Any]] = []
    for intent in list(INTENTS)[:max(0, int(max_intents))]:
        spec = INTENTS[intent]
        terms = interleave_intent_terms(list(spec["terms"]), per_intent_terms)
        # The topic anchor keeps the probe on the legal question; the intent
        # vocabulary is what turns it into a counter-directed search.
        probe_terms = [t for t in key_terms[:4]] + terms
        probe = " ".join(probe_terms)
        out.append({
            "intent": intent,
            "channel": spec["channel"],
            "label": spec["label"],
            "query": probe,
            "terms": probe_terms,
            "answer_terms_used": key_terms[:4],
            "intent_term_languages": sorted({
                lang for lang, t in spec["terms"] if t in set(terms)
            }),
        })
    return out


# --------------------------------------------------------------------------
# 2. fetch: a real second retrieval route through the accepted adapter
# --------------------------------------------------------------------------

def _identity(row: dict) -> tuple[str, str] | None:
    docket = str(row.get("docket_number") or "").strip()
    if not docket:
        return None
    court = str(row.get("court") or "").strip().lower()
    return (court, re.sub(r"[^a-z0-9]", "", docket.lower()))


def _client(mode: str, cache_dir: str, *, max_requests: int, max_rps: float) -> OCLClient:
    cfg = AdapterConfig(
        mode=mode,
        cache_dir=cache_dir,
        page_size=DEFAULT_PAGE_SIZE,
        max_pages_per_variant=1,
        max_requests=max_requests,
        max_rps=max_rps,
        stages=("search",),
    )
    transport = make_transport(cfg, FileCache(cfg.cache_dir))
    return OCLClient(transport, cfg, limiter=RateLimiter(cfg.max_rps),
                     budget=RequestBudget(cfg.max_requests))


def fetch_adversarial_candidates(
    query: str,
    plan: list[dict[str, Any]],
    *,
    mode: str = "live",
    cache_dir: str | None = None,
    exclude_ids: set[str] | None = None,
    exclude_identities: set[tuple[str, str]] | None = None,
    max_new: int = DEFAULT_MAX_NEW,
    hydrate_top: int = DEFAULT_HYDRATE_TOP,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_rps: float = 4.0,
) -> dict[str, Any]:
    """Run the probes upstream and return a candidate bundle of unseen rows.

    Never raises for an upstream problem: a failed route is reported in
    ``provenance.failures`` and yields zero new rows, which is an honest result
    (an adversarial pass that could not run found nothing) rather than a crash
    of the whole bundle.
    """
    started = time.time()
    exclude_ids = set(exclude_ids or ())
    exclude_identities = set(exclude_identities or ())
    if cache_dir is None:
        from .cache_path import product_cache_dir
        cache_dir = str(product_cache_dir())

    rows: dict[str, dict] = {}
    failures: list[dict] = []
    per_probe: list[dict] = []
    network_calls = 0
    cache_hits = 0
    client: OCLClient | None = None
    if plan and max_new > 0:
        try:
            client = _client(mode, cache_dir, max_requests=max_requests, max_rps=max_rps)
        except Exception as exc:  # pragma: no cover - construction is cheap
            failures.append({"stage": "adversarial", "error": f"{type(exc).__name__}: {exc}"})

    # Per-probe share of the budget.  Without it the first probe (the broadest
    # exception vocabulary) fills the whole cap and the minority / older-line
    # intents contribute nothing, which is the same shape of blindness the
    # initial pass already has.
    per_probe_cap = max(4, max_new // max(1, len(plan))) if plan else max_new
    for probe in plan:
        if client is None or len(rows) >= max_new or client.budget.exhausted:
            break
        probe_rows = 0
        channel = probe["channel"]
        intent = probe["intent"]
        seen_before = len(rows)
        try:
            payload = client.search_page(
                query=probe["query"], limit=page_size, offset=0, stage="adversarial",
            )
        except Exception as exc:
            failures.append({
                "stage": "adversarial",
                "intent": intent,
                "error": f"{type(exc).__name__}: {exc}",
            })
            per_probe.append({"intent": intent, "channel": channel, "hits": 0, "new_rows": 0,
                              "error": f"{type(exc).__name__}: {exc}"})
            continue
        hits = 0
        for raw in payload.get("results") or []:
            hits += 1
            rec = normalize_search_hit(raw, channel=channel, query=probe["query"],
                                       variant_id=f"adversarial:{intent}", page=0)
            if rec is None:
                continue
            did = str(rec.get("decision_id") or "")
            if not did or did in exclude_ids:
                continue
            ident = _identity(rec)
            if ident is not None and ident in exclude_identities:
                continue
            if did in rows:
                # Same decision via a second probe: keep the first channel only.
                # Re-labelling would overstate the channel evidence.
                continue
            rec["adversarial_intent"] = intent
            rec["adversarial_probe"] = probe["query"]
            rec["rank"] = len(rows) + 1
            rows[did] = rec
            exclude_ids.add(did)
            probe_rows += 1
            if ident is not None:
                exclude_identities.add(ident)
            if len(rows) >= max_new or probe_rows >= per_probe_cap:
                break
        per_probe.append({
            "intent": intent,
            "channel": channel,
            "label": probe.get("label"),
            "query": probe["query"],
            "hits": hits,
            "new_rows": len(rows) - seen_before,
        })

    # Bounded lazy hydration: only the evidence subset, only when a row will be
    # labelled.  Keeps the runtime budget (detail fetch, not map build).
    ordered = sorted(rows.values(), key=lambda r: int(r.get("rank") or 10**9))
    hydrated_ids: list[str] = []
    if client is not None and hydrate_top > 0:
        for rec in ordered[:hydrate_top]:
            did = str(rec.get("decision_id") or "")
            try:
                detail = client.get_decision(did, full_text=True)
                merged = normalize_decision_detail(detail, channel=str(rec.get("channel")))
            except Exception as exc:
                failures.append({"stage": "adversarial_hydrate", "decision_id": did,
                                 "error": f"{type(exc).__name__}: {exc}"})
                continue
            if not merged:
                continue
            for key in ("full_text", "regeste", "snippet", "title", "structure",
                        "full_text_status", "source_url", "pdf_url"):
                if merged.get(key):
                    rec[key] = merged.get(key)
            rec["detail_status"] = merged.get("detail_status") or "full"
            hydrated_ids.append(did)

    try:
        summary = client.stats() if client is not None else {}
    except Exception:  # pragma: no cover - stats is optional
        summary = {}
    network_calls = int(summary.get("network_calls") or 0)
    cache_hits = int(summary.get("cache_hits") or 0)

    return {
        "candidates": ordered,
        "query": query,
        "query_variants": [],
        "provenance": {
            "component": ADVERSARIAL_RETRIEVAL_VERSION,
            "route": "ocl_adapter /decisions via dedicated adversarial stage",
            "mode": mode,
            "probes": per_probe,
            "n_candidates": len(ordered),
            "n_hydrated": len(hydrated_ids),
            "hydrated_ids": hydrated_ids,
            "pool_never_seen_rate": 1.0 if ordered else None,
            "channels": sorted({str(r.get("channel")) for r in ordered}),
            "failures": failures,
            "request_summary": {"network_calls": network_calls, "cache_hits": cache_hits},
            "seconds": round(time.time() - started, 3),
            "claim_ceiling": (
                "rows reached this map only through the product's adversarial probes; "
                "counter_status is assigned solely when a verbatim sentence of the "
                "decision's own text carries a limitation marker, shares a topical "
                "term with the answer/query, and is neither procedural boilerplate "
                "nor a dismissal narration"
            ),
        },
    }


# --------------------------------------------------------------------------
# 3. label: evidence-gated counter classification
# --------------------------------------------------------------------------

def bundle_topic_terms(bundle: dict) -> list[str]:
    """Topical vocabulary a counter-evidence sentence must share.

    Three sources, in order (all deterministic, all recorded in provenance):

    1. the answer's own key terms (the pass attacks the *proposition*);
    2. the query tokens (fallback when the answer is degraded);
    3. the initial pool's shared regeste/snippet vocabulary — the
       **cross-lingual bridge**.  Swiss case law is trilingual: an Italian
       answer's terms will never appear in a German BGE abstract, yet the
       initial retrieval already established that those decisions are
       on-topic for this query.  A token qualifies when it occurs in
       >= max(3, n_pool/12) distinct decisions, which surfaces the pool's
       dominant legal nouns (``mietvertrag``, ``locazione`` …) without
       admitting one-off noise.

    The gate exists to stop off-domain markers (Arbeitsvertrag, KVG, maritime
    …) from licensing a label inside a locazione/bail bundle (cycle
    38828034436 audit D2, off-domain category).
    """
    answer_prose = str((bundle.get("answer") or {}).get("prose") or "")
    terms: list[str] = list(answer_key_terms(answer_prose, limit=8))
    seen = set(terms)
    for token in tokenize(str(bundle.get("query") or "")):
        if len(token) >= 4 and token not in seen:
            terms.append(token)
            seen.add(token)
    pool = list(bundle.get("decisions") or [])
    if pool and len(terms) < 24:
        counts: dict[str, int] = {}
        for d in pool:
            for field in ("regeste", "snippet", "title"):
                for token in tokenize(str(d.get(field) or "")):
                    if len(token) >= 6 and token not in _ANSWER_STOP and not token.isdigit():
                        counts[token] = counts.get(token, 0) + 1
        threshold = max(3, len(pool) // 12)
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        for token, count in ranked:
            if len(terms) >= 24:
                break
            if count >= threshold and token not in seen:
                terms.append(token)
                seen.add(token)
    return terms[:24]


def _sentence_eligible(sentence: str, markers: tuple[str, ...] | list[str],
                       *, intent: str) -> bool:
    """Guards a candidate evidence sentence (audit D2).

    A sentence licenses a counter label only when it
    1. carries at least one intent marker (caller-checked),
    2. is not procedural Eintretens boilerplate,
    3. is not a pure disposal/dismissal narration when the status in play is
       ``candidate-contrary`` (an appeal that failed is not counter-authority).
    """
    low = (sentence or "").lower()
    if any(p.search(low) for p in BOILERPLATE_SENTENCE_PATTERNS):
        return False
    if intent == "contrary" and any(p.search(low) for p in DISPOSAL_SENTENCE_PATTERNS):
        return False
    return any(m in low for m in markers)


def classify_against_intent(
    text: str,
    intent: str,
    *,
    topic_terms: list[str] | tuple[str, ...] | None = None,
) -> tuple[str | None, str, list[str]]:
    """Return ``(counter_status, evidence_sentence, markers)`` or ``(None, "", [])``.

    A row is labelled only on a verbatim sentence of its own text, so the
    product never asserts a legal label it cannot point at.

    Guards (cycle 38828034436 audit D2, replacing the negation/boilerplate/
    topic-blind substring match of /1):
    - the matched sentence must carry a topical term from the answer's/query's
      own vocabulary (``topic_terms``); with no topical vocabulary available no
      label is issued — an unlabelled row keeps recall without inventing law;
    - standard Eintretens formulas and disposal/dismissal narrations never
      license a label (a rejected appeal means the challenged ruling stood);
    - the reported markers are only those present in the *cited evidence
      sentence*, not the union of markers anywhere in the decision text.

    The probe that retrieved a row only expresses *what was searched for*; the
    evidence in the decision decides *what the row is*.  Intent order is fixed,
    never score-ranked, so the result is deterministic.
    """
    lowered = (text or "").lower()
    topical = [str(t).lower() for t in (topic_terms or []) if str(t).strip()]
    if not lowered or not topical:
        return None, "", []
    probe_first = [intent] + [i for i in INTENT_ORDER if i != intent]
    for candidate_intent in probe_first:
        markers = [m for m in EVIDENCE_MARKERS.get(candidate_intent, ())
                   if m in lowered]
        if not markers:
            continue
        status = COUNTER_STATUS_BY_INTENT.get(candidate_intent, "candidate-limiting")
        for sentence in split_sentences(text):
            low = sentence.lower()
            if not _sentence_eligible(sentence, markers, intent=candidate_intent):
                continue
            if not any(t in low for t in topical):
                continue
            sent_markers = sorted({m for m in markers if m in low})
            return status, sentence[:400], sent_markers[:6]
        # The marker exists in the decision but not inside a long enough
        # sentence: report the decision's own line rather than invent prose,
        # under the very same guards.
        for line in (text or "").splitlines():
            if not _sentence_eligible(line, markers, intent=candidate_intent):
                continue
            low = line.lower()
            if not any(t in low for t in topical):
                continue
            sent_markers = sorted({m for m in markers if m in low})
            anchor = line.strip()
            if anchor:
                return status, anchor[:400], sent_markers[:6]
    return None, "", []


# --------------------------------------------------------------------------
# 4. apply: join unseen rows into the already-rendered map
# --------------------------------------------------------------------------

def apply_adversarial_pass(
    bundle: dict,
    candidates: list[dict],
    candidate_provenance: dict | None = None,
    *,
    extra_hydrated_texts: dict[str, str] | None = None,
) -> dict:
    """Append unseen adversarial rows to ``bundle`` without moving existing points.

    Geometry comes from the existing incremental seam: the map is refitted with
    the new rows present and then every previously rendered point is restored to
    its shipped coordinates, so a jurist's view never shifts under them.
    """
    out = copy.deepcopy(bundle)
    existing = {str(d.get("decision_id")) for d in out.get("decisions") or []}
    incoming = [c for c in candidates if str(c.get("decision_id")) not in existing]
    prov: dict[str, Any] = {
        "component": ADVERSARIAL_RETRIEVAL_VERSION,
        "attempted": bool(incoming),
        "n_existing_before": len(existing),
        "n_new_rows": 0,
        "n_counter_rows": 0,
        "new_counter_ids": [],
        "counter_status_histogram": {},
        "channels": [],
        "probes": [],
        "pool_never_seen_rate": None,
    }
    prov.update({k: v for k, v in (candidate_provenance or {}).items() if k != "component"})
    if not incoming:
        out.setdefault("provenance", {})["adversarial_retrieval"] = prov
        return out

    from .progressive import map_model_from_bundle
    from .qmap import build_map

    model = map_model_from_bundle(out)
    if model is None:
        # Without the shipped projection the new rows could only be placed in a
        # different space than the rendered one, which would make proximity a
        # lie.  Refuse instead: an adversarial pass that cannot be placed
        # honestly contributes nothing, and says so.
        prov.update({
            "skipped": True,
            "skip_reason": "map_model_from_bundle returned None; rows would not share the rendered projection",
        })
        out.setdefault("provenance", {})["adversarial_retrieval"] = prov
        return out

    # Topic vocabulary for the labelling gate (audit D2): the matched evidence
    # sentence must share a term with the answer/query or no label is issued.
    topic_terms = bundle_topic_terms(out)
    prov["label_topic_terms"] = topic_terms

    # Turn adapter candidates into product rows with the same conversion the
    # initial pass uses, so an adversarial row is indistinguishable in shape.
    from .pipeline import _candidate_to_product
    product_rows = _candidate_to_product({
        "candidates": incoming,
        "query": out.get("query", ""),
        "query_variants": [],
        "bundle_version": "1.0-candidate",
    }).get("decisions") or []
    by_id = {str(c.get("decision_id")): c for c in incoming}
    texts = dict(extra_hydrated_texts or {})
    rows: list[dict] = []
    labels: dict[str, tuple[str | None, str, list[str]]] = {}
    for row in product_rows:
        did = str(row.get("decision_id") or "")
        cand = by_id.get(did) or {}
        for key in ("full_text", "regeste", "title", "structure", "source_url",
                    "pdf_url", "legal_area", "channels", "detail_status", "full_text_status"):
            if cand.get(key) is not None and row.get(key) is None:
                row[key] = copy.deepcopy(cand.get(key))
        row["snippet"] = row.get("snippet") or row.get("regeste") or row.get("title") or ""
        if not row.get("docket_number") and cand.get("docket_number"):
            row["docket_number"] = cand["docket_number"]
        text = texts.get(did) or str(cand.get("full_text") or "") or str(row.get("regeste") or "")
        intent = str(cand.get("adversarial_intent") or "exception")
        status, evidence, markers = classify_against_intent(text, intent, topic_terms=topic_terms)
        labels[did] = (status, evidence, markers)
        # Retrieval heuristics are admission signals only. They MUST NOT become
        # product-visible legal labels. The independent LLM reviewer runs later
        # over the final bounded set and is the sole writer of counter_status.
        row["counter_status"] = "none"
        row["counter_evidence"] = ""
        row["counter_markers"] = []
        row["counter_uncertainty"] = None
        row["counter_evidence_verified"] = False
        row["adversarial_retrieval_signal"] = {
            "heuristic_status": status,
            "evidence": evidence,
            "markers": markers,
        }
        row["adversarial_channel"] = str(cand.get("channel") or "")
        row["adversarial_intent"] = intent
        # Per-row probe attribution (audit advisory 2): which probe string
        # actually retrieved this row, so the answer-derived-probe claim is
        # auditable per row and not only in aggregate probes[].new_rows.
        row["adversarial_probe"] = str(cand.get("adversarial_probe") or "")
        row.setdefault("channels", [])
        if row["adversarial_channel"] and row["adversarial_channel"] not in row["channels"]:
            row["channels"] = [*row["channels"], row["adversarial_channel"]]
        row["rank"] = None  # placed after the initial ranked list, deterministically
        rows.append(row)

    # The product has a hard result budget. Answer-conditioned retrieval may
    # discover unseen authorities, but it is not allowed to inflate a 100-row
    # product into 140+ rows. Admit a tiny challenger set and replace the weakest
    # conventional tail while protecting cited/visible authorities.
    from .relevance import rerank_product_bundle

    target_size = len(out.get("decisions") or [])
    candidate_packet = {
        "query": out.get("query", ""),
        "query_variants": list(out.get("query_variants") or []),
        "decisions": copy.deepcopy(rows),
        "provenance": {},
    }
    ranked_rows = (
        rerank_product_bundle(candidate_packet).get("decisions") or []
        if rows else []
    )

    def _admission_key(row: dict) -> tuple:
        did = str(row.get("decision_id") or "")
        status, evidence, _markers = labels.get(did, (None, "", []))
        signalled = 1 if status and evidence else 0
        try:
            score = float(row.get("score") or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        return (signalled, score, str(did))

    ranked_rows.sort(key=_admission_key, reverse=True)
    max_adversarial_slots = min(8, target_size)
    proposed = ranked_rows[:max_adversarial_slots]

    cited_ids = {
        str(x) for x in (out.get("answer") or {}).get("cited_decision_ids") or []
    }
    protected_ids = set(cited_ids)
    for d in out.get("decisions") or []:
        if str(d.get("counter_status") or "none") not in {"none", "cited", "unclassified"}:
            protected_ids.add(str(d.get("decision_id") or ""))

    def _existing_rank(row: dict) -> int:
        try:
            return int(row.get("rank") or 10**9)
        except (TypeError, ValueError):
            return 10**9

    droppable = [
        d for d in sorted(out.get("decisions") or [], key=_existing_rank, reverse=True)
        if str(d.get("decision_id") or "") not in protected_ids
    ]
    admitted = proposed[: min(len(proposed), len(droppable))]
    dropped = droppable[: len(admitted)]
    dropped_ids = {str(d.get("decision_id") or "") for d in dropped}
    admitted_ids = {str(d.get("decision_id") or "") for d in admitted}

    retained = [
        copy.deepcopy(d)
        for d in out.get("decisions") or []
        if str(d.get("decision_id") or "") not in dropped_ids
    ]
    # New rows are candidates only until the independent reviewer classifies
    # them after this function returns.
    for row in admitted:
        row["counter_status"] = "none"
        row["counter_evidence"] = ""
        row["counter_evidence_verified"] = False
        row["counter_uncertainty"] = None

    frozen = {
        str(d["decision_id"]): (d.get("x"), d.get("y"), d.get("cluster_id"), bool(d.get("is_outlier")))
        for d in retained
    }
    combined = retained + admitted
    decisions, clusters, shared_relations = build_map(combined, model=model)
    for d in decisions:
        did = str(d.get("decision_id") or "")
        if did in frozen:
            d["x"], d["y"], d["cluster_id"], d["is_outlier"] = frozen[did]
        d["counter_status"] = d.get("counter_status") or "none"
        d["counter_evidence"] = d.get("counter_evidence") or ""
        d["counter_uncertainty"] = d.get("counter_uncertainty")
        d["counter_evidence_verified"] = bool(d.get("counter_evidence_verified", False))

    # Preserve the conventional order for retained rows; newly discovered
    # adversarial candidates occupy only the replaced tail slots.
    original_rank = {
        str(d.get("decision_id")): _existing_rank(d)
        for d in retained
    }
    decisions.sort(
        key=lambda d: (
            0 if str(d.get("decision_id")) in original_rank else 1,
            original_rank.get(str(d.get("decision_id")), 10**9),
            -float(d.get("score") or 0.0) if isinstance(d.get("score"), (int, float)) else 0.0,
            str(d.get("decision_id") or ""),
        )
    )
    for position, d in enumerate(decisions, start=1):
        d["rank"] = position

    appended = [
        str(d.get("decision_id"))
        for d in decisions
        if str(d.get("decision_id")) in admitted_ids
    ]
    out["decisions"] = decisions
    out["clusters"] = clusters
    from .pipeline import _merge_relations
    out["relations"] = _merge_relations(out.get("relations") or [], shared_relations)

    prov.update({
        "admission_policy": "bounded_replace_tail_v1",
        "max_adversarial_slots": max_adversarial_slots,
        "n_proposed_rows": len(proposed),
        "n_admitted_rows": len(admitted),
        "admitted_row_ids": appended,
        "n_replaced_rows": len(dropped_ids),
        "replaced_row_ids": sorted(dropped_ids),
        "final_decision_count": len(decisions),
        "heuristic_labels_surfaceable": False,
    })

    hist: dict[str, int] = {}
    for d in decisions:
        k = str(d.get("counter_status") or "none")
        hist[k] = hist.get(k, 0) + 1
    prov.update({
        "n_new_rows": len(appended),
        "n_counter_rows": 0,
        "new_row_ids": appended,
        "new_counter_ids": [],
        "counter_status_histogram": dict(sorted(hist.items())),
        "channels": sorted({str(d.get("adversarial_channel")) for d in decisions
                            if d.get("adversarial_channel")}),
        "pool_never_seen_rate": round(len(appended) / max(1, len(decisions)), 6),
    })
    out.setdefault("provenance", {})["adversarial_retrieval"] = prov
    return out


__all__ = [
    "ADVERSARIAL_CHANNELS",
    "ADVERSARIAL_RETRIEVAL_VERSION",
    "INTENTS",
    "PROBE_LANGUAGES",
    "answer_key_terms",
    "apply_adversarial_pass",
    "bundle_topic_terms",
    "classify_against_intent",
    "fetch_adversarial_candidates",
    "interleave_intent_terms",
    "plan_adversarial_queries",
]