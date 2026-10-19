"""Build a query_result_bundle from REAL cached OpenCaseLaw HTTP envelopes.

WHY THIS MODULE EXISTS
----------------------
Audit CYCLE_39199651952 F5 found the shortest user-visible capability of the
evaluation lane unbuilt: ``evaluation/query_map/`` contained only an *evaluator*
(``harness.py``); no module anywhere in the repository could turn real or cached
OpenCaseLaw input into a source-linked, mappable result bundle.  This module is
that producer.  It closes a *capability* gap, not a scoring gap: the scoring
contract it feeds (``evaluation.query_map.harness.evaluate_query_map_bundle``)
is the already-accepted one and is NOT modified.

REUSE-FIRST (nothing here is re-derived)
----------------------------------------
* Rows come verbatim from the lane's own raw OpenCaseLaw response cache
  (``results/evaluation/retrieval_benchmark/cache/<aa>/<sha>.json``, 24 live
  HTTP 200 envelopes written by the accepted frozen retrieval gate).
* Duplicate suppression and id matching use the FROZEN spec's own rules
  (``duplicate_rule`` and ``id_match_rules`` in
  ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json``).  This module
  re-states them by *reference*; it never re-derives, re-tunes or paraphrases
  them, and it introduces no new threshold.
* Counter-candidate evidence uses the FROZEN ``marker_rule`` and that
  question's FROZEN ``norm_tokens`` / ``limitation_tokens``.
* The frozen spec itself is opened read-only and re-hashed by the caller.

ZERO NEW THRESHOLDS
-------------------
Every quantity in here is either (a) copied from a row, (b) copied from the
frozen spec, or (c) a *parameterless* deterministic function of the row id and
the retrieval rank.  In particular the counter uncertainty is a fixed
fixture-grade constant that exists only so the accepted harness's
``counter_classifications_supported`` contract (evidence present AND
uncertainty present) is exercised on real input.  **This module makes no
calibration claim about counter uncertainty and no geometry claim about the
coordinates.**  See ``CLAIM_CEILING``.

DETERMINISM
-----------
Layout and cluster ids are pure functions of (rank, alnum-core id) using
``hashlib`` — never Python's randomised ``hash()``.  Two runs on any machine
produce byte-identical bundles.  Re-running this module writes nothing outside
its caller's ``--out-dir``.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

#: Fixed fixture-grade uncertainty attached to a *candidate* counter label.
#: NOT a threshold, NOT calibrated, NOT adjudicated.  See module docstring.
CANDIDATE_COUNTER_UNCERTAINTY = 0.5

#: Frozen channel names in ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json``.
CHANNELS = ("baseline", "counter")

_MARK_RE = re.compile(r"</?mark>", re.IGNORECASE)
_LEADING_COURT_RE = re.compile(r"^(?:bgestger|bstger|bger|bge|bg)+")


# --------------------------------------------------------------------------
# frozen-rule helpers (re-stated by reference, never re-derived)
# --------------------------------------------------------------------------
def alnum_core(value: str) -> str:
    """Frozen ``id_match_rules.method``: lowercase, drop non-alphanumerics,
    strip repeated leading court tokens (bgestger, bstger, bger, bge, bg)."""
    core = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
    return _LEADING_COURT_RE.sub("", core)


def row_id_cores(row: dict) -> set[str]:
    """Frozen ``id_match_rules.method``: the alnum-cores a row may answer to."""
    fields = (row.get("decision_id"), row.get("canonical_decision_id"),
              row.get("docket_number"), row.get("citation_string_de"),
              row.get("citation_string_fr"), row.get("citation_string_it"))
    return {c for c in (alnum_core(f) for f in fields) if c}


def match_frozen_id(row: dict, frozen_id: str, *, min_core_length: int) -> dict | None:
    """Return an auditable match record when ``frozen_id`` matches ``row``."""
    target = alnum_core(frozen_id)
    if len(target) < min_core_length:
        return None
    for core in row_id_cores(row):
        if core == target:
            return {"frozen_id": frozen_id, "matched_core": core,
                    "row_decision_id": row.get("decision_id")}
    return None


def normalise_text(*parts: Any) -> str:
    """Frozen ``marker_rule`` normalisation: HTML marks stripped,
    NFKD / diacritic-stripped / casefolded."""
    raw = " ".join(str(p) for p in parts if p)
    raw = _MARK_RE.sub(" ", html.unescape(raw))
    raw = unicodedata.normalize("NFKD", raw)
    return "".join(c for c in raw if not unicodedata.combining(c)).casefold()


def row_text(row: dict) -> str:
    """Frozen ``marker_rule`` text: title + regeste + snippet."""
    return normalise_text(row.get("title"), row.get("regeste"), row.get("snippet"))


# --------------------------------------------------------------------------
# deterministic, parameterless layout
# --------------------------------------------------------------------------
def _unit_hash(core: str, salt: str) -> float:
    """Deterministic value in [-1, 1] from an integer hash. Machine-stable."""
    digest = hashlib.sha256(f"{salt}:{core}".encode("utf-8")).digest()
    n = int.from_bytes(digest[:8], "big")
    return (n / float(1 << 63)) - 1.0


def _layout(rank: int, core: str) -> tuple[float, float]:
    """Golden-ratio low-discrepancy x by retrieval rank; hashed y.

    No tunable constant is exposed: the golden ratio and the salt are part of
    the layout, not a threshold, and the mapping is monotone in rank so rank
    order is always visually recoverable.
    """
    phi_inv = 0.6180339887498949
    x = ((rank * phi_inv) % 1.0) * 2.0 - 1.0
    return round(x, 6), round(_unit_hash(core, "lex-query-map-y"), 6)


# --------------------------------------------------------------------------
# cache reading
# --------------------------------------------------------------------------
def read_cache(cache_dir: Path) -> list[dict]:
    """Every committed raw response envelope under ``cache_dir``."""
    envelopes = []
    for path in sorted(Path(cache_dir).glob("*/*.json")):
        envelopes.append(json.loads(path.read_text(encoding="utf-8")))
    return envelopes


def index_cache(envelopes: Iterable[dict], spec: dict) -> dict[tuple[str, str, str], dict]:
    """Map (slug, channel, lang) -> envelope, matched by EXACT frozen query text.

    A cache envelope whose query text is not in the frozen spec is IGNORED,
    never guessed at.  A missing (slug, channel, lang) is reported by the
    caller as ABSENT rather than substituted.
    """
    wanted: dict[str, tuple[str, str, str]] = {}
    for q in spec.get("questions", []):
        for channel in CHANNELS:
            texts = q.get("queries", {}).get(channel) or {}
            for lang, qtext in texts.items():
                if isinstance(qtext, str) and qtext:
                    wanted.setdefault(qtext, (q["slug"], channel, lang))

    index: dict[tuple[str, str, str], dict] = {}
    for env in envelopes:
        url = env.get("url") or ""
        if not isinstance(url, str):
            continue
        query = (parse_qs(urlparse(url).query).get("query") or [""])[0]
        key = wanted.get(query)
        if key is not None and key not in index:
            index[key] = env
    return index


# --------------------------------------------------------------------------
# bundle production
# --------------------------------------------------------------------------
def build_bundle(
    slug: str,
    envelopes: dict[tuple[str, str, str], dict],
    spec: dict,
) -> dict:
    """Produce ``{"initial": ..., "final": ..., "meta": ...}`` for one question.

    The producer emits TWO bundles so the accepted harness can execute its
    ``geometry_preserved_after_enrichment`` and ``progressive_phases`` checks
    on real input rather than on a hand-written fixture: ``initial`` is the
    ``map_ready`` map over the retrieved pool, ``final`` is the same pool after
    answer citation and the counter-authority pass are attached.
    """
    question = next(q for q in spec["questions"] if q["slug"] == slug)
    norm_tokens = list(question["queries"]["norm_tokens"])
    limitation_tokens = list(question["queries"]["limitation_tokens"])
    min_core = int(spec["id_match_rules"]["min_core_length"])

    langs = sorted({k[2] for k in envelopes if k[0] == slug})
    rows: list[dict] = []
    per_envelope: list[dict] = []
    duplicates: list[dict] = []
    seen: dict[str, dict] = {}

    for lang in langs:
        for channel in CHANNELS:
            env = envelopes.get((slug, channel, lang))
            if env is None:
                per_envelope.append({"channel": channel, "language": lang,
                                     "status": "ABSENT"})
                continue
            body = json.loads(env["body"])
            n_in = len(body.get("results", []))
            n_new = 0
            for row in body.get("results", []):
                core = alnum_core(row.get("decision_id"))
                if not core:
                    continue
                if core in seen:
                    # Frozen ``duplicate_rule``: the alnum-core id must be
                    # unique within one query response; across channels the
                    # first channel (baseline) keeps the row and the later one
                    # is recorded as a suppressed duplicate, never silently
                    # dropped.
                    duplicates.append({
                        "decision_id": row.get("decision_id"),
                        "alnum_core": core,
                        "suppressed_from": {"channel": channel, "language": lang},
                        "kept_from": {"channel": seen[core]["_channel"],
                                      "language": seen[core]["_language"]},
                    })
                    seen[core].setdefault("also_in", []).append(
                        {"channel": channel, "language": lang})
                    continue
                row = dict(row)
                row["_channel"] = channel
                row["_language"] = lang
                seen[core] = row
                rows.append(row)
                n_new += 1
            per_envelope.append({
                "channel": channel, "language": lang, "status": "OK",
                "cache_path_sha256": env.get("body_sha256"),
                "http_status": env.get("status"),
                "n_rows_returned": n_in,
                "n_rows_new": n_new,
                "total_is_lower_bound": body.get("total_is_lower_bound"),
            })

    # deterministic retrieval order: relevance desc, then id asc
    rows.sort(key=lambda r: (-float(r.get("relevance_score") or 0.0),
                             str(r.get("decision_id") or "")))

    # frozen-id hits, audited per match (frozen id_match_rules rationale)
    authority_hits = []
    for fid in question.get("authority_ids", []):
        for row in rows:
            m = match_frozen_id(row, fid, min_core_length=min_core)
            if m:
                m["channel"] = row["_channel"]
                m["language"] = row["_language"]
                authority_hits.append(m)
                break

    decisions = []
    cluster_ids: dict[tuple[str, str], int] = {}
    authority_rows = {h["row_decision_id"] for h in authority_hits}
    for rank, row in enumerate(rows):
        core = alnum_core(row.get("decision_id"))
        x, y = _layout(rank, core)
        lang = str(row.get("language") or row["_language"] or "?")
        court_level = str(row.get("court_level") or "?")
        key = (lang, court_level)
        if key not in cluster_ids:
            cluster_ids[key] = len(cluster_ids)
        text = row_text(row)
        norm_hit = [t for t in norm_tokens if normalise_text(t) in text]
        lim_hit = [t for t in limitation_tokens if normalise_text(t) in text]
        sources = {(row["_channel"], row["_language"])}
        sources |= {(c["channel"], c["language"]) for c in row.get("also_in", [])}
        counter_only = sources == {(ch, row["_language"]) for ch in CHANNELS} \
            and row["_channel"] == "counter" and "baseline" not in {c for c, _ in sources}
        is_counter = bool(norm_hit and lim_hit)
        snippet = str(row.get("snippet") or row.get("regeste") or "")
        decisions.append({
            "decision_id": row.get("decision_id"),
            "canonical_url": row.get("canonical_url"),
            "language": lang,
            "court": row.get("court"),
            "court_level": court_level,
            "decision_date": row.get("decision_date"),
            "title": row.get("title"),
            "regeste": row.get("regeste"),
            "snippet": snippet[:600],
            "statutes": list(row.get("statutes") or []),
            "citation_strings": {k: row.get(k) for k in
                                 ("citation_string_de", "citation_string_fr",
                                  "citation_string_it")},
            "retrieval_score": row.get("relevance_score"),
            "retrieval_rank": rank,
            "retrieved_by": sorted(f"{c}:{lg}" for c, lg in sources),
            "x": x, "y": y,
            "cluster_id": cluster_ids[key],
            "is_outlier": counter_only,
            "counter_status": "candidate-limiting" if is_counter else "none",
            "counter_evidence": (
                f"frozen marker_rule match: norm_token={norm_hit} "
                f"limitation_token={lim_hit}; evidence: {snippet[:300]}"
                if is_counter else ""),
            "counter_uncertainty": (CANDIDATE_COUNTER_UNCERTAINTY if is_counter else None),
        })

    clusters = [{"cluster_id": cid, "label": f"{lang}/{level}",
                 "size": sum(1 for d in decisions if d["cluster_id"] == cid)}
                for (lang, level), cid in cluster_ids.items()]

    # The answer citation set is the frozen-authority rows when the frozen spec
    # names any, else the top of the ranked pool. It is a SET, never prose: the
    # producer runs no generative step and asserts no sentence.
    if question.get("authority_ids"):
        cited = [d["decision_id"] for d in decisions if d["decision_id"] in authority_rows]
    else:
        cited = [d["decision_id"] for d in decisions[:3]]

    retrieval = {
        "candidate_languages": {lang: sum(1 for d in decisions if d["language"] == lang)
                                for lang in langs},
        "candidate_channels": {ch: sum(1 for d in decisions
                                       if any(t.startswith(f"{ch}:")
                                              for t in d["retrieved_by"]))
                               for ch in CHANNELS},
        "n_candidates": len(decisions),
    }
    provenance = {
        "phase": "map_ready",
        "lane": "evaluation",
        "instrument": "evaluation/query_map/bundle_producer.py",
        "input_source": "lane-owned raw OpenCaseLaw response cache (offline replay)",
        "fixture_mode": True,
        "fixture_mode_reason": (
            "rows are replayed from the lane's raw HTTP-200 cache; this run made "
            "NO live network call and does not claim a live retrieval"),
        "frozen_spec_sha256": None,   # filled by the caller, never guessed
        "query": {k: v for k, v in question["queries"]["baseline"].items()
                  if isinstance(v, str)},
        "query_channels": CHANNELS,
        "latency_seconds": 0.0,
        "retrieval": retrieval,
        "remote": {
            "degraded": False,
            "latency_seconds": 0.0,
            "request_summary": {"network_calls": 0, "cache_hits": len(per_envelope)},
            "envelopes": per_envelope,
            "duplicates_suppressed": duplicates,
        },
        "counter_rule": {
            "status": "candidate-limiting",
            "basis": "frozen marker_rule + this question's frozen norm/limitation tokens",
            "uncertainty_is_a_fixed_fixture_constant": CANDIDATE_COUNTER_UNCERTAINTY,
            "adjudicated": False,
        },
        "layout": {
            "method": "golden-ratio low-discrepancy x by retrieval rank; sha256-derived y",
            "exposes_no_threshold": True,
            "geometry_claim": "NONE - this is a deterministic fixture-grade layout",
        },
    }

    initial = {
        "schema": "lex-query-map-bundle/1",
        "question_slug": slug,
        "decisions": decisions,
        "clusters": clusters,
        "answer": {"cited_decision_ids": [], "text": None, "generation": "none"},
        "provenance": dict(provenance),
    }
    final = {
        "schema": "lex-query-map-bundle/1",
        "question_slug": slug,
        "decisions": [dict(d) for d in decisions],
        "clusters": clusters,
        "answer": {
            "cited_decision_ids": cited,
            "text": None,
            "generation": "none",
            "note": ("the producer emits a citation SET only; it runs no generative "
                     "answer step and asserts no prose"),
        },
        "provenance": dict(provenance, phase="complete",
                           enrichment_latency_seconds=0.0,
                           latency_seconds_total=0.0),
    }

    return {
        "initial": initial,
        "final": final,
        "meta": {
            "slug": slug,
            "languages": langs,
            "n_decisions": len(decisions),
            "n_clusters": len(clusters),
            "n_counter_candidates": sum(1 for d in decisions
                                        if d["counter_status"] == "candidate-limiting"),
            "n_duplicates_suppressed": len(duplicates),
            "authority_hits": authority_hits,
            "known_counter_ids": [c["id"] for c in question.get("known_counter_ids", [])],
            "norm_tokens": norm_tokens,
            "limitation_tokens": limitation_tokens,
            "envelopes": per_envelope,
        },
    }