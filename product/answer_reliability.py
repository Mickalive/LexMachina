#!/usr/bin/env python3
"""Measure the live generative answer's reliability on REPLAYED LIVE queries.

Why this exists
---------------
Factory direction v62, product ordered item 4: the live-answer reliability
measurement on replayed live OpenCaseLaw queries.  ``state/product.json``
named it "the measurement that is still missing" and "the gate before any
human-gate session is staged".  It had never run, and no reliability figure
was claimed for the generative answer.

What "replayed live" means here
--------------------------------
The retrieval half of every leg is a REPLAY of envelopes that were fetched
LIVE from the public OpenCaseLaw API and are now in the product cache
(``results/product/query_cache``).  The legs run with
``retrieval_mode="offline"``, i.e. cache-first: the decision set a jurist
would see is the set that came back from the live API, and the measurement
itself performs **no** network retrieval.  The generation half is live: the
free OpenCode model is called for real, through the shipped
``product/query/answer_provider.py`` runner and the shipped pipeline.

What it measures (per leg)
--------------------------
* ``answer_ready``      - the answer was produced by the generative writer
  (``status == "ready"``) and not silently downgraded to the extractive
  fallback;
* ``citation_validity`` - every cited decision id is a decision that is
  actually in the bundle the map renders;
* ``source_validity``   - every cited decision carries a canonical source URL
  on an allowed public host (the answer must be clickable to a real source);
* ``language_match``    - the answer is written in the language of the
  question (the reality check has always required a French synthesis for a
  French question);
* ``degradation_visible`` - when the writer aborts, the bundle carries the
  degradation code AND the adversarial pass is marked DEGRADED/VACUOUS, so a
  provider outage can never read as "no contrary authority exists"
  (direction v62 ordered item 3, measured on the live path for the first
  time here);
* ``adversarial_rows``  - how many counter rows the independent adversarial
  pass actually emitted (and how many it abstained on);
* ``wall_seconds``      - the leg's wall clock.

What it does NOT do
-------------------
* it does not score, re-derive or touch any frozen bar, rubric, benchmark or
  verdict contract - none is read here;
* it never labels a decision supporting / contrary / limiting; it only counts
  what the shipped pipeline already emitted;
* it never sets ``human_gate_ready``, ``machine_gate_ready``,
  ``ready_for_owner_session`` or ``packet_admitted``; those stay false;
* it is REPORTED-ONLY: the success rule below is a pre-registered,
  product-owned criterion for the CLAIM "the live generative answer is
  reliable on replayed live queries".  It is not a factory-frozen bar and it
  gates nothing.

Pre-registration
----------------
The protocol (query set, repeats, retrieval mode, budgets, metrics and the
success rule) is a constant of this module.  ``--freeze`` writes it to a
run-named artifact BEFORE any leg runs, and ``--run`` refuses to run unless
that frozen artifact exists and its digest still matches the module constant.
The protocol is therefore fixed before the measurement, not after it.

Usage
-----
    python3 product/answer_reliability.py --freeze --run-id 39799042649
    python3 product/answer_reliability.py --run    --run-id 39799042649
    python3 product/answer_reliability.py --check  --run-id 39799042649

Writes ``results/product/answer_reliability/<run_id>_protocol_freeze.json``
and ``results/product/answer_reliability/<run_id>_measurement.json``.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(REPO_ROOT), str(PRODUCT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query.query_texts import (  # noqa: E402
    MANIFEST_PATH,
    detect_language,
    load_manifest,
)

OUT_DIR = REPO_ROOT / "results" / "product" / "answer_reliability"
SCHEMA = "product-answer-reliability/1"

#: Hosts a cited decision's canonical source URL may use.  A citation to any
#: other host is not a clickable public source and counts as invalid.
ALLOWED_SOURCE_HOSTS = frozenset({
    "mcp.opencaselaw.ch",
    "opencaselaw.ch",
    "www.opencaselaw.ch",
    "bger.ch",
    "www.bger.ch",
    "fedlex.data.admin.ch",
    "www.fedlex.admin.ch",
    "www.fedlex.data.admin.ch",
    "lexfind.ch",
    "www.lexfind.ch",
})

#: --------------------------------------------------------------------------
#: The pre-registered protocol.  Frozen before the measurement runs.
#: --------------------------------------------------------------------------
PROTOCOL: dict[str, Any] = {
    "schema": "product-answer-reliability-protocol/1",
    "title": "live generative answer reliability on replayed live OpenCaseLaw queries",
    "purpose": (
        "Factory direction v62 product ordered item 4: the live-answer "
        "reliability measurement that had never run. It measures whether the "
        "shipped generative answer leg produces a ready, source-linked, "
        "citation-valid answer on decisions that came back from the live "
        "OpenCaseLaw API and are replayed from the product cache."
    ),
    "hypothesis": (
        "On the replayed live OpenCaseLaw coverage cache, the product's live "
        "generative answer is reliable when every leg answers with status "
        "'ready', every cited decision id is present in the rendered bundle, "
        "every cited decision carries a canonical source URL on an allowed "
        "public host, every authority the prose names inline resolves to a "
        "decision in the rendered bundle, the answer is written in the "
        "question's language, a writer abort is always visible as a "
        "degradation, and two repeats of the same question cite a "
        "substantially the same set of decisions."
    ),
    "query_set": [
        # (question slug, channel, language, repeats)
        {"slug": "rent-default", "channel": "baseline", "language": "fr", "repeats": 2},
        {"slug": "rent-default", "channel": "baseline", "language": "de", "repeats": 1},
        {"slug": "rent-default", "channel": "baseline", "language": "it", "repeats": 1},
        {"slug": "petty-theft-dismissal", "channel": "baseline", "language": "fr", "repeats": 1},
        {"slug": "corporate-criminal-liability", "channel": "baseline", "language": "fr", "repeats": 1},
        {"slug": "business-judgment-rule", "channel": "baseline", "language": "fr", "repeats": 1},
    ],
    "query_text_source": (
        "product/data/frozen_retrieval_texts.json (the product-owned snapshot of "
        "the frozen retrieval benchmark's query texts); the texts are read, "
        "never retyped, and their source digest is pinned by the manifest"
    ),
    "retrieval_mode": "offline",
    "retrieval_mode_note": (
        "cache-first replay of envelopes fetched LIVE from the public "
        "OpenCaseLaw API; the measurement performs no network retrieval"
    ),
    "top_n": 120,
    "top_n_note": (
        "the coverage replay wrote the cache at top_n=120, so the replay hits "
        "the recorded envelopes; at the pipeline's default top_n=150 the "
        "request key does not match the recorded envelope and the cache-first "
        "path misses (measured, disclosed in the report of record)"
    ),
    "evidence_count": 12,
    "max_cites": 8,
    "answer_timeout_s": 180,
    "answer_timeout_note": (
        "the shipped default is 300 s per model; this measurement uses 180 s "
        "because the cycle's wall-clock budget is finite. A SHORTER budget can "
        "only turn a ready answer into a degraded one, so the measured "
        "reliability is a CONSERVATIVE (lower) estimate of the shipped path's."
    ),
    "leg_budget_s": 420,
    "concurrency": 2,
    "concurrency_note": (
        "legs run with bounded concurrency; the per-leg wall clock therefore "
        "includes provider contention and is reported as measured, not as a "
        "single-user latency figure"
    ),
    "metrics": [
        "answer_ready",
        "citation_validity",
        "prose_citation_validity",
        "source_validity",
        "language_match",
        "degradation_visible",
        "adversarial_rows",
        "wall_seconds",
    ],
    "stability_metric": (
        "Jaccard of the cited decision-id sets of two repeats of the same "
        "question, plus the fraction of citations present in BOTH repeats "
        "(the stable core). Pre-registered, computed from the recorded legs, "
        "never adjusted after the result is seen."
    ),
    "success_rule": (
        "The measurement is COMPLETE when every planned leg has a recorded "
        "outcome (ready or degraded), no leg is missing, and the "
        "degradation-visibility check holds for every leg. The PRODUCT CLAIM "
        "'the live generative answer is reliable on replayed live queries' is "
        "made only when ALL of: answer_ready_rate == 1.0, citation_validity "
        "== 1.0, prose_citation_validity == 1.0, source_validity == 1.0, "
        "language_match_rate == 1.0, degradation_visible_rate == 1.0 and the "
        "stability Jaccard of the repeated question is >= 0.5. If any "
        "condition fails the claim is NOT made and the failure is published. "
        "This is a pre-registered, product-owned criterion for ONE product "
        "claim; it is not a factory-frozen bar, it scores no frozen rubric "
        "and it gates nothing."
    ),
    "claim_ceiling": (
        "A measurement of the shipped generative answer leg on the recorded "
        "live OpenCaseLaw decision sets, at one date, with one free model "
        "pool. It says nothing about legal correctness, jurist usefulness, "
        "the frozen bars, the serve verdict or the human gate; it changes no "
        "posture field and it labels no decision."
    ),
    "not_claimed": [
        "no legal correctness claim: a cited authority can be real and still be the wrong authority for the question",
        "no jurist-usefulness claim",
        "no human-gate readiness: human_gate_ready stays false",
        "no change to any frozen bar, rubric, benchmark or verdict contract",
        "no re-run of the served packet: the serve question stays closed for the v3 bytes",
    ],
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def protocol_payload(run_id: str) -> dict[str, Any]:
    """The frozen protocol plus the digests that pin what it was frozen against."""
    payload = dict(PROTOCOL)
    manifest_bytes = MANIFEST_PATH.read_bytes()
    payload["run_id"] = int(run_id) if str(run_id).isdigit() else str(run_id)
    payload["protocol_sha256"] = _sha256_bytes(
        json.dumps(PROTOCOL, sort_keys=True, ensure_ascii=False).encode("utf-8")
    )
    payload["query_text_manifest"] = {
        "path": str(MANIFEST_PATH.relative_to(REPO_ROOT)),
        "sha256": _sha256_bytes(manifest_bytes),
        "source_sha256": json.loads(manifest_bytes.decode("utf-8")).get("source_sha256"),
    }
    payload["tool"] = "product/answer_reliability.py"
    payload["frozen_before_execution"] = True
    return payload


def freeze_path(run_id: str) -> Path:
    return OUT_DIR / f"{run_id}_protocol_freeze.json"


def measurement_path(run_id: str) -> Path:
    return OUT_DIR / f"{run_id}_measurement.json"


def query_texts() -> list[dict[str, Any]]:
    """The planned legs, with the query text read from the frozen manifest."""
    manifest = load_manifest()
    by_slug = {str(q.get("slug")): q for q in manifest.get("questions") or []}
    legs: list[dict[str, Any]] = []
    for spec in PROTOCOL["query_set"]:
        question = by_slug.get(spec["slug"])
        if not question:
            raise ValueError(f"frozen manifest has no question {spec['slug']!r}")
        text = str(((question.get("queries") or {}).get(spec["channel"]) or {})
                   .get(spec["language"]) or "").strip()
        if not text:
            raise ValueError(
                f"frozen manifest has no {spec['channel']}/{spec['language']} text "
                f"for {spec['slug']!r}"
            )
        for repeat in range(1, int(spec["repeats"]) + 1):
            legs.append({
                "leg_id": f"{spec['slug']}|{spec['channel']}|{spec['language']}|r{repeat}",
                "slug": spec["slug"],
                "channel": spec["channel"],
                "language": spec["language"],
                "repeat": repeat,
                "text": text,
                "text_sha256": _sha256_bytes(text.encode("utf-8")),
            })
    return legs


def _host_of(url: str) -> str:
    match = re.match(r"^https?://([^/]+)", url.strip(), flags=re.IGNORECASE)
    return match.group(1).lower() if match else ""


def citation_validity(bundle: dict[str, Any]) -> dict[str, Any]:
    """Are the cited ids decisions that are actually in the rendered bundle?"""
    decisions = bundle.get("decisions") or []
    by_id = {str(d.get("decision_id")): d for d in decisions}
    cited = [str(x) for x in ((bundle.get("answer") or {}).get("cited_decision_ids") or [])]
    valid = [c for c in cited if c in by_id]
    invalid = [c for c in cited if c not in by_id]
    return {
        "n_cited": len(cited),
        "n_valid": len(valid),
        "n_invalid": len(invalid),
        "invalid_ids": invalid,
        "cited_ids": cited,
        "all_valid": not invalid and bool(cited),
    }


def source_validity(bundle: dict[str, Any]) -> dict[str, Any]:
    """Does every cited decision carry a clickable canonical public source?"""
    decisions = bundle.get("decisions") or []
    by_id = {str(d.get("decision_id")): d for d in decisions}
    cited = [str(x) for x in ((bundle.get("answer") or {}).get("cited_decision_ids") or [])]
    ok: list[str] = []
    bad: list[dict[str, Any]] = []
    for cid in cited:
        decision = by_id.get(cid) or {}
        url = str(decision.get("canonical_url") or decision.get("source_url") or "").strip()
        host = _host_of(url)
        if url.startswith("https://") and host in ALLOWED_SOURCE_HOSTS:
            ok.append(cid)
        else:
            bad.append({"decision_id": cid, "canonical_url": url, "host": host})
    return {
        "n_cited": len(cited),
        "n_with_valid_source": len(ok),
        "n_without_valid_source": len(bad),
        "invalid": bad,
        "all_valid": not bad and bool(cited),
    }


def _norm(value: str) -> str:
    text = str(value or "")
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    text = re.sub(r"[^0-9a-z\u00c0-\u024f]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


#: The prose names its authorities inline, e.g. "[bge_119 II 147]" or
#: "[BGE 119 II 147]".  A named authority that is NOT in the bundle is an
#: authority the jurist cannot click - the most damaging failure mode of a
#: sourced answer, and one a structured id list alone cannot see.
_MARKER_RE = re.compile(r"\[([^\[\]]{3,120})\]")


def prose_citation_validity(bundle: dict[str, Any]) -> dict[str, Any]:
    """Every authority the prose names inline must exist in the bundle."""
    prose = str((bundle.get("answer") or {}).get("prose") or "")
    decisions = bundle.get("decisions") or []
    aliases: dict[str, str] = {}
    for decision in decisions:
        did = str(decision.get("decision_id") or "")
        for key in ("decision_id", "citation", "title", "court", "date"):
            value = decision.get(key)
            if not value:
                continue
            norm = _norm(str(value))
            if len(norm) >= 4:
                aliases.setdefault(norm, did)
                # also register the bracketed form without its decision id prefix
                if key == "decision_id":
                    aliases.setdefault(_norm(str(value).split("_", 1)[-1]), did)
    markers = [m.strip() for m in _MARKER_RE.findall(prose)]
    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for marker in markers:
        norm = _norm(marker)
        did = None
        if norm in aliases:
            did = aliases[norm]
        else:
            for alias, alias_did in aliases.items():
                if len(alias) >= 6 and (alias in norm or norm in alias):
                    did = alias_did
                    break
        if did:
            resolved.append({"marker": marker, "decision_id": did})
        else:
            unresolved.append(marker)
    return {
        "n_markers": len(markers),
        "n_resolved": len(resolved),
        "n_unresolved": len(unresolved),
        "unresolved_markers": unresolved,
        "resolved": resolved,
        "all_resolved": not unresolved,
    }


def language_match(prose: str, query: str) -> dict[str, Any]:
    """Is the answer written in the language of the question?"""
    query_lang = detect_language(query) or "unknown"
    prose_lang = detect_language(prose) or "unknown"
    return {
        "query_language": query_lang,
        "answer_language": prose_lang,
        "match": query_lang == prose_lang and query_lang != "unknown",
    }


def degradation_visibility(bundle: dict[str, Any]) -> dict[str, Any]:
    """A writer abort must be visible, and must mark the adversarial pass.

    Ordered item 3 is a DISCLOSURE requirement, so this measures exactly the
    disclosure: an aborted writer must publish its code and the adversarial
    pass must be marked DEGRADED / VACUOUS.  A healthy leg must NOT carry a
    writer-abort code.
    """
    answer = bundle.get("answer") or {}
    degradation = answer.get("degradation") or {}
    code = str(degradation.get("code") or "")
    adv = ((bundle.get("provenance") or {}).get("adversarial_retrieval") or {})
    adv_status = str(adv.get("adversarial_status") or "")
    aborted = bool(code)
    if aborted:
        visible = bool(code) and (
            "WRITER_ABORT" in adv_status or adv_status in {"DEGRADED", "VACUOUS"}
        )
        expected = True
    else:
        visible = "WRITER_ABORT" not in adv_status
        expected = True
    return {
        "degraded": aborted,
        "degradation_code": code or None,
        "adversarial_status": adv_status or None,
        "adversarial_degraded": bool(adv.get("degraded")),
        "visible": visible,
        "expected": expected,
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------

def run_leg(leg: dict[str, Any], *, top_n: int, evidence_count: int,
            max_cites: int, answer_timeout_s: float) -> dict[str, Any]:
    """One measurement leg: replayed-live retrieval + the live answer leg."""
    from product.query.pipeline import enrich_query_bundle, run_query_initial

    os.environ["LEX_ANSWER_TIMEOUT_S"] = str(float(answer_timeout_s))
    record: dict[str, Any] = {
        "leg_id": leg["leg_id"],
        "slug": leg["slug"],
        "channel": leg["channel"],
        "language": leg["language"],
        "repeat": leg["repeat"],
        "text_sha256": leg["text_sha256"],
        "text": leg["text"],
    }
    t0 = time.time()
    try:
        initial = run_query_initial(leg["text"], top_n=top_n, retrieval_mode="offline")
    except Exception as exc:
        record.update({
            "outcome": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "wall_seconds": round(time.time() - t0, 3),
        })
        return record
    t_initial = time.time() - t0
    record["retrieval"] = {
        "mode": "offline",
        "seconds": round(t_initial, 3),
        "n_decisions": len(initial.get("decisions") or []),
        "n_clusters": len(initial.get("clusters") or []),
    }
    t1 = time.time()
    try:
        bundle = enrich_query_bundle(
            initial,
            retrieval_mode="offline",
            evidence_count=evidence_count,
            max_cites=max_cites,
        )
    except Exception as exc:
        record.update({
            "outcome": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "wall_seconds": round(time.time() - t0, 3),
        })
        return record
    answer = bundle.get("answer") or {}
    prov = bundle.get("provenance") or {}
    ga = prov.get("generative_audit") or {}
    citations = citation_validity(bundle)
    sources = source_validity(bundle)
    prose_cites = prose_citation_validity(bundle)
    languages = language_match(str(answer.get("prose") or ""), leg["text"])
    degradation = degradation_visibility(bundle)
    adv = prov.get("adversarial_retrieval") or {}
    counter_rows = [d for d in (bundle.get("decisions") or [])
                    if str(d.get("counter_status") or "") not in {"", "none"}]
    record.update({
        "outcome": "OK",
        "wall_seconds": round(time.time() - t0, 3),
        "answer_seconds": round(time.time() - t1, 3),
        "answer": {
            "status": answer.get("status"),
            "ready": answer.get("status") == "ready",
            "method": answer.get("method"),
            "model": answer.get("model"),
            "n_cited": citations["n_cited"],
            "cited_decision_ids": citations["cited_ids"],
            "prose_chars": len(str(answer.get("prose") or "")),
            "prose_head": str(answer.get("prose") or "")[:400],
        },
        "citations": citations,
        "prose_citations": prose_cites,
        "sources": sources,
        "language_check": languages,
        "degradation": degradation,
        "adversarial": {
            "adversarial_status": adv.get("adversarial_status"),
            "n_new_rows": adv.get("n_new_rows"),
            "n_counter_rows": adv.get("n_counter_rows"),
            "n_counter_rows_emitted": len(counter_rows),
            "pass_seconds": adv.get("pass_seconds"),
        },
        "provider": {
            "selected_model": (ga.get("product_answer_provider") or {}).get("selected_model"),
            "model_used": ga.get("model"),
            "provider_error": ga.get("provider_error"),
            "n_attempts": len(ga.get("provider_attempts") or []),
        },
    })
    return record


def aggregate(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """The pre-registered aggregate. Every number is derived from the legs."""
    ok = [leg for leg in legs if leg.get("outcome") == "OK"]
    failed = [leg for leg in legs if leg.get("outcome") != "OK"]
    n = len(ok)
    ready = [leg for leg in ok if (leg.get("answer") or {}).get("ready")]
    cited_total = sum(int((leg.get("citations") or {}).get("n_cited") or 0) for leg in ok)
    valid_total = sum(int((leg.get("citations") or {}).get("n_valid") or 0) for leg in ok)
    src_ok = sum(int((leg.get("sources") or {}).get("n_with_valid_source") or 0) for leg in ok)
    src_total = sum(int((leg.get("sources") or {}).get("n_cited") or 0) for leg in ok)
    lang_ok = sum(1 for leg in ok if (leg.get("language_check") or {}).get("match"))
    markers_total = sum(int((leg.get("prose_citations") or {}).get("n_markers") or 0) for leg in ok)
    markers_resolved = sum(int((leg.get("prose_citations") or {}).get("n_resolved") or 0) for leg in ok)
    legs_without_markers = [
        leg["leg_id"] for leg in ok
        if int((leg.get("prose_citations") or {}).get("n_markers") or 0) == 0
    ]
    degraded_legs = [leg for leg in ok if (leg.get("degradation") or {}).get("degraded")]
    visible_ok = sum(1 for leg in ok if (leg.get("degradation") or {}).get("visible"))
    latencies = sorted(float(leg.get("wall_seconds") or 0.0) for leg in ok)

    # stability: pair the repeats of each (slug, channel, language)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for leg in ok:
        groups.setdefault((leg["slug"], leg["channel"], leg["language"]), []).append(leg)
    stability: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        if len(group) < 2:
            continue
        a = set((group[0].get("citations") or {}).get("cited_ids") or [])
        b = set((group[1].get("citations") or {}).get("cited_ids") or [])
        stability.append({
            "slug": key[0],
            "channel": key[1],
            "language": key[2],
            "n_repeats": len(group),
            "cited_a": sorted(a),
            "cited_b": sorted(b),
            "jaccard": round(jaccard(a, b), 6),
            "stable_core": sorted(a & b),
            "stable_core_fraction": round(
                len(a & b) / len(a | b) if (a | b) else 1.0, 6),
        })
    stability_jaccard = min((s["jaccard"] for s in stability), default=None)

    complete = (not failed) and len(legs) == len(PROTOCOL["query_set"]) and all(
        int(spec["repeats"]) for spec in PROTOCOL["query_set"]
    )
    planned_legs = sum(int(spec["repeats"]) for spec in PROTOCOL["query_set"])
    complete = len(legs) == planned_legs and not failed

    metrics = {
        "n_legs_planned": planned_legs,
        "n_legs_executed": len(legs),
        "n_legs_ok": n,
        "n_legs_failed": len(failed),
        "answer_ready_rate": (len(ready) / n) if n else None,
        "citation_validity": (valid_total / cited_total) if cited_total else None,
        "source_validity": (src_ok / src_total) if src_total else None,
        "language_match_rate": (lang_ok / n) if n else None,
        "prose_citation_validity": (markers_resolved / markers_total) if markers_total else None,
        "n_prose_markers": markers_total,
        "n_prose_markers_resolved": markers_resolved,
        "legs_without_prose_markers": legs_without_markers,
        "degradation_visible_rate": (visible_ok / n) if n else None,
        "n_degraded_legs": len(degraded_legs),
        "stability_jaccard_min": stability_jaccard,
        "stability": stability,
        "wall_seconds": {
            "min": latencies[0] if latencies else None,
            "p50": latencies[len(latencies) // 2] if latencies else None,
            "max": latencies[-1] if latencies else None,
        },
    }
    conditions = {
        "measurement_complete": complete,
        "answer_ready_rate == 1.0": metrics["answer_ready_rate"] == 1.0,
        "citation_validity == 1.0": metrics["citation_validity"] == 1.0,
        "source_validity == 1.0": metrics["source_validity"] == 1.0,
        "language_match_rate == 1.0": metrics["language_match_rate"] == 1.0,
        "prose_citation_validity == 1.0": metrics["prose_citation_validity"] == 1.0,
        "degradation_visible_rate == 1.0": metrics["degradation_visible_rate"] == 1.0,
        "stability_jaccard >= 0.5": (
            stability_jaccard is not None and stability_jaccard >= 0.5
        ),
    }
    claim = all(conditions.values())
    return {
        "metrics": metrics,
        "pre_registered_conditions": conditions,
        "product_claim_reliable_live_answer": claim,
        "claim_ceiling": PROTOCOL["claim_ceiling"],
    }


def run_measurement(run_id: str, *, concurrency: int | None = None) -> dict[str, Any]:
    """Execute every planned leg and publish the measurement."""
    legs = query_texts()
    workers = int(concurrency or PROTOCOL["concurrency"])
    started = time.time()
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(
                run_leg,
                leg,
                top_n=int(PROTOCOL["top_n"]),
                evidence_count=int(PROTOCOL["evidence_count"]),
                max_cites=int(PROTOCOL["max_cites"]),
                answer_timeout_s=float(PROTOCOL["answer_timeout_s"]),
            ): leg
            for leg in legs
        }
        for future in concurrent.futures.as_completed(futures):
            leg = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # never lose a leg to an exception
                results.append({
                    "leg_id": leg["leg_id"],
                    "slug": leg["slug"],
                    "channel": leg["channel"],
                    "language": leg["language"],
                    "repeat": leg["repeat"],
                    "text": leg["text"],
                    "outcome": "ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                })
    order = {leg["leg_id"]: i for i, leg in enumerate(legs)}
    results.sort(key=lambda r: order.get(r.get("leg_id"), 10_000))
    payload = {
        "schema": SCHEMA,
        "record_type": "PRODUCT_LIVE_ANSWER_RELIABILITY_MEASUREMENT",
        "run_id": int(run_id) if str(run_id).isdigit() else str(run_id),
        "tool": "product/answer_reliability.py",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - started, 3),
        "concurrency": workers,
        "protocol_sha256": protocol_payload(run_id)["protocol_sha256"],
        "protocol": PROTOCOL,
        "legs": results,
    }
    payload.update(aggregate(results))
    payload["not_claimed"] = PROTOCOL["not_claimed"]
    payload["posture_unchanged"] = {
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
    }
    return payload


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--freeze", action="store_true",
                    help="write the pre-registered protocol artifact")
    ap.add_argument("--run", action="store_true", help="execute the measurement")
    ap.add_argument("--check", action="store_true",
                    help="re-derive the aggregate from the recorded legs")
    ap.add_argument("--concurrency", type=int, default=None)
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(args.run_id)
    freeze = freeze_path(run_id)
    measurement = measurement_path(run_id)

    if args.freeze:
        payload = protocol_payload(run_id)
        freeze.write_text(_canonical(payload), encoding="utf-8")
        print(f"[ok] froze the protocol: {freeze.relative_to(REPO_ROOT)}")
        print(f"     protocol_sha256 = {payload['protocol_sha256']}")

    if args.run:
        if not freeze.is_file():
            print(f"[FAIL] no frozen protocol at {freeze}; run --freeze first",
                  file=sys.stderr)
            return 2
        frozen = json.loads(freeze.read_text(encoding="utf-8"))
        current = protocol_payload(run_id)
        if frozen.get("protocol_sha256") != current["protocol_sha256"]:
            print("[FAIL] the frozen protocol no longer matches the module "
                  "constant - the protocol changed after it was frozen",
                  file=sys.stderr)
            return 3
        payload = run_measurement(run_id, concurrency=args.concurrency)
        measurement.write_text(_canonical(payload), encoding="utf-8")
        metrics = payload["metrics"]
        print(f"[ok] wrote {measurement.relative_to(REPO_ROOT)}")
        print(f"     legs ok {metrics['n_legs_ok']}/{metrics['n_legs_executed']} "
              f"(planned {metrics['n_legs_planned']}), "
              f"failed {metrics['n_legs_failed']}")
        print(f"     answer_ready_rate   {metrics['answer_ready_rate']}")
        print(f"     citation_validity   {metrics['citation_validity']}")
        print(f"     source_validity     {metrics['source_validity']}")
        print(f"     language_match_rate {metrics['language_match_rate']}")
        print(f"     degradation_visible {metrics['degradation_visible_rate']}")
        print(f"     stability_jaccard   {metrics['stability_jaccard_min']}")
        print(f"     product claim reliable live answer: "
              f"{payload['product_claim_reliable_live_answer']}")
        return 0

    if args.check:
        if not measurement.is_file():
            print(f"[FAIL] missing measurement artifact: {measurement}",
                  file=sys.stderr)
            return 2
        recorded = json.loads(measurement.read_text(encoding="utf-8"))
        fresh = aggregate(recorded.get("legs") or [])
        for key in ("metrics", "pre_registered_conditions",
                    "product_claim_reliable_live_answer"):
            if recorded.get(key) != fresh.get(key):
                print(f"[FAIL] the recorded {key} does not reproduce from the "
                      f"recorded legs", file=sys.stderr)
                return 1
        print("[ok] the recorded aggregate reproduces from the recorded legs")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
