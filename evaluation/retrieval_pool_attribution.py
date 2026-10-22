#!/usr/bin/env python3
"""v62 retrieval-pool attribution for the accepted V3 concept-coverage failure.

WHY THIS INSTRUMENT EXISTS
--------------------------
The accepted falsification ``mf::concept_coverage::39319405429::de-kapitalverletzung``
says: two of the eight core concepts of the served German question retrieve
ZERO served rows.  The accepted bundle does NOT say *why*.  The two candidate
causes need different product remedies and the factory must not guess:

  (A) RETRIEVAL BUDGET - the ranked candidate pool contains the concept, but the
      product stopped after ONE page.  The accepted bundle's own
      ``provenance.searches[0]`` records ``total: 254`` (lower bound),
      ``limit: 50``, ``next_offset: 50``, ``has_more: true`` and the accepted
      ``provenance.targets`` records ``max_pages_per_variant: 1`` /
      ``max_requests: 1``.  Remedy: fetch more pages.
  (B) SERVED ASSEMBLY - the pool page the product did fetch contains the
      concept, but the shipped bundle dropped it.  Remedy: fix the assembly.
  (C) QUERY RECALL - the concept is not in the ranked pool at all, so no budget
      or assembly change would ever surface it.  Remedy: query expansion /
      language coverage, not paging.

This instrument decides which of (A)/(B)/(C) holds, per concept, by replaying
the product's OWN recorded request against the live OpenCaseLaw corpus and
walking the pages the product declined to fetch.

REUSE-FIRST
-----------
* ``evaluation.subject_match_audit.question_concepts`` - the ACCEPTED
  question-native core-concept rule.  Not re-derived.
* ``evaluation.subject_match_audit.row_match_text`` / ``deaccent`` - the
  ACCEPTED row-text projection.  Not re-derived.
* The request parameters are NOT invented: they are read from the accepted
  bundle's own ``provenance.searches[0]`` (offset, limit, sort, fields) and the
  accepted ``provenance.targets`` (page_size).  The question text is the
  accepted ``questions/<qid>.question.json`` field ``question``.
* The zero-concept input is RECOMPUTED from the accepted bundle with the
  accepted rule and cross-checked against the accepted record
  ``results/evaluation/mapping_free_recall_falsifier/39693031072.json``.

The instrument adds no threshold to any bar, no tokeniser, no stoplist and no
scored-status vocabulary.  Its only numeric conditions are the frozen ones in
``evaluation/V62_RETRIEVAL_POOL_ATTRIBUTION_HYPOTHESIS_V1.json``.

LIVE MEASUREMENT DISCLOSURE
---------------------------
This is the FIRST evaluation instrument in this lane that performs network
calls against the public OpenCaseLaw API.  It does so because the question it
answers - "what is in the pool the product never fetched?" - is unanswerable
from the accepted tree: the accepted packet's own
``CLAIM_CACHE_VERIFICATION.json`` names 26 cache envelopes as "the
packet-of-record build's own retrieval envelopes for the three preregistered
gate questions", and NONE of them exists in the accepted product mount, so the
pool behind the served rows is not reconstructible offline.  Every result
carries ``live_measurement: true`` and the corpus-drift controls.

CLAIM CEILING
-------------
This instrument ATTRIBUTES one accepted failure to one of three cause classes.
It does NOT re-issue, weaken or re-score the accepted falsification; that
verdict stands unchanged.  It does NOT meet, move or re-derive the frozen
absolute LABEL_SOUND or GEOMETRY_SOUND bars (they stay REPORTED-ONLY).  It does
NOT lift any DO-NOT-SERVE order and does NOT certify admission of any packet
(admission stays fail-closed).  It does NOT claim the map helps a jurist.  It
runs no obsolete universal-174k benchmark.  ``human_gate_ready`` stays false.
It changes no product byte.

Exit codes
----------
0  POOL_ATTRIBUTION_NO_NEW_DEFECT   - every zero concept is explained by the
                                     pool the product itself fetched and
                                     shipped; no new product remedy is owed.
1  POOL_ATTRIBUTION_DEFECT_ATTRIBUTED - at least one zero concept is
                                     attributable to a defect class with a
                                     named remedy.
2  NOT_MEASURED_VACUOUS              - a control did not hold, the corpus
                                     drifted, the pool scan was incomplete or
                                     the network was unavailable.  Never a
                                     pass, never a bar-met.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import subject_match_audit as SMA  # noqa: E402

SCHEMA = "lex-evaluation-v62-retrieval-pool-attribution/1"
HYPOTHESIS_RELPATH = "evaluation/V62_RETRIEVAL_POOL_ATTRIBUTION_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/V62_RETRIEVAL_POOL_ATTRIBUTION_FREEZE_RECORD_V1.json"

DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)
PACKET = "39319405429"
PRIMARY_QID = "de-kapitalverletzung"
CROSS_LANG_QIDS = ("fr-bail-entretien", "it-responsabilita-medica")

#: The accepted record whose coverage counts this instrument re-derives.
ACCEPTED_RECORD_RELPATH = "results/evaluation/mapping_free_recall_falsifier/39693031072.json"

OCL_BASE = "https://mcp.opencaselaw.ch/api"
USER_AGENT = "LexMachina-Evaluation/1.0 (v62 retrieval pool attribution)"

#: FROZEN (see the hypothesis): the live scan walks at most this many pages of
#: the product's own ranked result set.
MAX_PAGES = 8
#: FROZEN: minimum page-0 fidelity (Jaccard of id sets) between the live
#: replay and the served page-0 rows.  Below it the corpus drifted and the
#: attribution is NOT_MEASURED_VACUOUS.
PAGE0_JACCARD_MIN = 0.90
#: FROZEN: the nonsense control query.  Must return zero rows.
NONSENSE_QUERY = "zzqxvlexmachinaNonexistentControlToken"
#: FROZEN: soft pace, below the charter's 5 req/s.
MIN_INTERVAL_S = 0.25
#: FROZEN: how many matching rows per concept are hydrated with full text.
MAX_DETAIL_FETCH_PER_CONCEPT = 3

EXIT_NO_DEFECT = 0
EXIT_DEFECT = 1
EXIT_VACUOUS = 2

VERDICT_NO_DEFECT = "POOL_ATTRIBUTION_NO_NEW_DEFECT"
VERDICT_DEFECT = "POOL_ATTRIBUTION_DEFECT_ATTRIBUTED"
VERDICT_VACUOUS = "NOT_MEASURED_VACUOUS"

#: Cause classes, frozen.  Priority order breaks ties between classes.
CAUSE_POOL_COVERS = "POOL_COVERS"
CAUSE_BEYOND_PAGE0 = "BEYOND_PAGE0_ONLY"
CAUSE_PAGE0_ONLY = "PAGE0_COVERS_ONLY"
CAUSE_NEVER = "POOL_NEVER_COVERS"
CAUSE_UNMEASURED = "UNMEASURED"

#: Tie-break priority for the dominant class (frozen, most actionable first).
CLASS_PRIORITY = (CAUSE_BEYOND_PAGE0, CAUSE_PAGE0_ONLY, CAUSE_NEVER)

CLASS_REMEDY = {
    CAUSE_BEYOND_PAGE0: (
        "RETRIEVAL_BUDGET_DEFECT: the ranked pool holds the concept but the "
        "product fetched one page only (max_pages_per_variant=1, "
        "max_requests=1). Remedy: raise the per-variant page budget so the "
        "pool behind the served question is actually read."
    ),
    CAUSE_PAGE0_ONLY: (
        "SERVED_ASSEMBLY_DEFECT: the page the product fetched holds the "
        "concept but the shipped bundle does not. Remedy: fix the bundle "
        "assembly / channel merge, not the retrieval budget."
    ),
    CAUSE_NEVER: (
        "QUERY_RECALL_DEFECT: the concept is absent from the whole ranked "
        "pool the product's own query returns, so no paging or assembly "
        "change can surface it. Remedy: query expansion / language coverage "
        "(concept injection into the retrieval query)."
    ),
    CAUSE_POOL_COVERS: (
        "POOL_COVERS: the concept is present in the fetched pool and in the "
        "served bundle at the same time - no retrieval or assembly defect is "
        "attributable from this measurement."
    ),
    CAUSE_UNMEASURED: (
        "UNMEASURED: the pool for this concept was not completely measured; "
        "no class is attributed."
    ),
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_environment() -> dict[str, Any]:
    """Disclosed numeric environment.  No numpy/BLAS reduction enters a verdict;
    the only arithmetic is set cardinality and integer counting."""
    return {
        "python": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "numpy_used": False,
        "blas_used": False,
        "float_comparisons_in_verdict": False,
        "arithmetic": "integer counting and set cardinality only",
    }


def resolve_mount(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_dir() else None
    for env in ("LEX_ACCEPTED_PRODUCT", "LEX_PRODUCT_MOUNT"):
        val = os.environ.get(env)
        if val and Path(val).is_dir():
            return Path(val)
    for cand in DEFAULT_MOUNTS:
        if Path(cand).is_dir():
            return Path(cand)
    return None


def mount_head(mount: Path) -> str | None:
    import subprocess

    try:
        out = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # pragma: no cover - git absent
        return None
    return None


def _question_paths(mount: Path, packet: str, qid: str) -> tuple[Path, Path]:
    base = mount / "results" / "product" / "gate_packet" / packet / "questions"
    return base / f"{qid}.bundle.json", base / f"{qid}.question.json"


# --------------------------------------------------------------------------- #
# the accepted rule, applied to live rows and to served rows
# --------------------------------------------------------------------------- #
def lexical_row(raw: dict) -> dict:
    """Project a live OpenCaseLaw search hit onto the ACCEPTED row field names.

    The accepted ``row_match_text`` reads ``title``, ``regeste``, ``snippet``,
    ``full_text``, ``citation`` and ``decision_id``.  A live search hit has no
    ``full_text`` (the product hydrates it lazily) and no ``citation`` key, so
    the citation is taken with the accepted normaliser's documented rule:
    ``citation_string_{language}`` first, then de/fr/it, then court+docket.
    ``full_text`` stays empty; a hydrated full text is added only by the
    bounded detail fetch.
    """
    lang = str(raw.get("language") or "").lower()
    citation = ""
    for key in ([f"citation_string_{lang}"] if lang else []) + [
        "citation_string_de", "citation_string_fr", "citation_string_it",
    ]:
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            citation = val.strip()
            break
    if not citation:
        court = str(raw.get("court") or "").strip()
        docket = str(raw.get("docket_number") or "").strip()
        citation = f"{court} {docket}".strip()
    return {
        "decision_id": str(raw.get("decision_id") or ""),
        "title": raw.get("title") or "",
        "regeste": raw.get("regeste") or "",
        "snippet": raw.get("snippet") or "",
        "full_text": "",
        "citation": citation,
        "language": lang,
        "court": raw.get("court") or "",
    }


def strip_full_text(row: dict) -> dict:
    """A copy of a served row with ``full_text`` removed (lexical-only view)."""
    out = dict(row)
    out["full_text"] = ""
    return out


def coverage(rows: Iterable[dict], concepts: list[str]) -> dict[str, Any]:
    """The ACCEPTED coverage rule, verbatim in behaviour.

    ``evaluation.subject_match_audit.row_match_text`` + ``deaccent`` + the
    frozen ``>=1-of-set`` semantics.  No new threshold.
    """
    texts = [SMA.deaccent(SMA.row_match_text(r)).lower() for r in rows]
    counts = {c: sum(1 for t in texts if c in t) for c in concepts}
    zero = sorted(c for c, n in counts.items() if n == 0)
    return {
        "n_rows": len(texts),
        "concepts": list(concepts),
        "concept_row_counts": counts,
        "concepts_with_zero_rows": zero,
        "n_concepts": len(concepts),
        "n_zero": len(zero),
    }


def oracle_query_text(question_text: str, concept: str) -> str:
    """The original-case spelling of a concept token, taken from the question.

    Deterministic: the first whitespace-delimited word of the question whose
    de-accented lowercase alnum form equals the concept token.  Falls back to
    the concept token itself.
    """
    target = SMA.deaccent(concept).lower()
    for word in re.split(r"\s+", str(question_text or "")):
        token = re.sub(r"[^0-9a-z]+", "", SMA.deaccent(word).lower())
        if token == target:
            return word.strip(" ,.;:?!\"'()")
    return concept


# --------------------------------------------------------------------------- #
# network
# --------------------------------------------------------------------------- #
class OclError(RuntimeError):
    pass


def _http_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ocl_search(query: str, offset: int, limit: int, *, sort: str = "relevance",
               fields: str = "full", include_pinpoint: bool = False,
               language: str | None = None, timeout: float = 90.0,
               fetcher: Callable[[str, float], dict] | None = None,
               ) -> dict:
    """One ``GET /decisions`` call with the product's own parameter shape."""
    params = {
        "query": query,
        "limit": int(limit),
        "offset": int(offset),
        "sort": sort,
        "fields": fields,
        "include_pinpoint": "true" if include_pinpoint else "false",
    }
    if language:
        params["language"] = language
    url = OCL_BASE + "/decisions?" + urllib.parse.urlencode(params)
    payload = (fetcher or _http_json)(url, timeout)
    if not isinstance(payload, dict):
        raise OclError("search payload is not an object")
    payload.setdefault("results", [])
    return payload


def ocl_decision(decision_id: str, *, timeout: float = 90.0,
                 fetcher: Callable[[str, float], dict] | None = None) -> dict:
    url = OCL_BASE + "/decisions/" + urllib.parse.quote(decision_id, safe="") + \
        "?" + urllib.parse.urlencode({"full_text": "true"})
    payload = (fetcher or _http_json)(url, timeout)
    if not isinstance(payload, dict):
        raise OclError("decision payload is not an object")
    return payload


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def scan_pool(query: str, *, limit: int, sort: str, fields: str,
              include_pinpoint: bool, max_pages: int,
              fetcher: Callable[[str, float], dict] | None,
              sleep: Callable[[float], None] = time.sleep,
              ) -> dict[str, Any]:
    """Walk the product's own ranked result set from offset 0."""
    pages: list[dict[str, Any]] = []
    rows: list[dict] = []
    raw_rows: list[dict] = []
    offset = 0
    has_more = True
    total = None
    total_is_lower_bound = None
    for page_no in range(max_pages):
        if not has_more:
            break
        payload = ocl_search(query, offset, limit, sort=sort, fields=fields,
                             include_pinpoint=include_pinpoint, fetcher=fetcher)
        sleep(MIN_INTERVAL_S)
        results = payload.get("results") or []
        page = {
            "page": page_no,
            "offset": offset,
            "returned": len(results),
            "reported_total": payload.get("total"),
            "total_is_lower_bound": payload.get("total_is_lower_bound"),
            "has_more": payload.get("has_more"),
            "next_offset": payload.get("next_offset"),
            "result_set_id": payload.get("result_set_id"),
        }
        pages.append(page)
        total = payload.get("total", total)
        total_is_lower_bound = payload.get("total_is_lower_bound", total_is_lower_bound)
        for raw in results:
            raw_rows.append(raw)
            rows.append(lexical_row(raw))
        has_more = bool(payload.get("has_more"))
        nxt = payload.get("next_offset")
        offset = int(nxt) if isinstance(nxt, int) else offset + limit
    return {
        "pages": pages,
        "n_pages_fetched": len(pages),
        "rows": rows,
        "raw_rows": raw_rows,
        "reported_total": total,
        "total_is_lower_bound": total_is_lower_bound,
        "last_has_more": bool(has_more),
        "pool_complete": not has_more,
    }


def served_page0_rows(bundle: dict, variant_id: str) -> list[dict]:
    """The rows the product's own single search shipped (page 0 of one variant)."""
    out = []
    for d in bundle.get("decisions") or []:
        prov = str(d.get("provenance") or "")
        if f"variant={variant_id}" in prov and "page=0" in prov:
            out.append(d)
    return out


def measure_question(mount: Path, packet: str, qid: str, *,
                     fetcher: Callable[[str, float], dict] | None,
                     sleep: Callable[[float], None],
                     max_pages: int,
                     ) -> dict[str, Any]:
    bundle_path, question_path = _question_paths(mount, packet, qid)
    bundle = json.loads(bundle_path.read_text())
    qrec = json.loads(question_path.read_text())
    question_text = str(qrec.get("question") or "")

    searches = (bundle.get("provenance") or {}).get("searches") or []
    original = next((s for s in searches if s.get("kind") == "original"), None)
    if original is None:
        original = searches[0] if searches else {}
    variant_id = str(original.get("variant_id") or "")
    limit = int(original.get("limit") or (bundle.get("provenance") or {}).get("targets", {}).get("page_size") or 50)
    sort = "relevance"
    fields = "full"
    include_pinpoint = False

    # ---- served side (accepted bytes, no network) ------------------------ #
    all_rows = bundle.get("decisions") or []
    concepts = SMA.question_concepts(question_text)
    served_cov_full = coverage(all_rows, concepts)
    served_cov_lex = coverage([strip_full_text(r) for r in all_rows], concepts)
    served_p0 = served_page0_rows(bundle, variant_id)
    served_p0_cov = coverage(served_p0, concepts)
    served_p0_ids = {str(d.get("decision_id") or "") for d in served_p0}

    # ---- live side ------------------------------------------------------- #
    scan = scan_pool(question_text, limit=limit, sort=sort, fields=fields,
                     include_pinpoint=include_pinpoint, max_pages=max_pages,
                     fetcher=fetcher, sleep=sleep)
    live_rows = scan["rows"]
    live_p0 = live_rows[:limit]
    live_p0_ids = {str(r.get("decision_id") or "") for r in live_p0}
    beyond = live_rows[limit:]
    live_p0_cov = coverage(live_p0, concepts)
    live_pool_cov = coverage(live_rows, concepts)
    live_beyond_cov = coverage(beyond, concepts)

    # ---- fidelity of the replay to the served bytes ---------------------- #
    jac = _jaccard(live_p0_ids, served_p0_ids)
    fidelity = {
        "served_page0_ids": sorted(served_p0_ids),
        "live_page0_ids": sorted(live_p0_ids),
        "n_served_page0": len(served_p0_ids),
        "n_live_page0": len(live_p0_ids),
        "n_intersection": len(live_p0_ids & served_p0_ids),
        "jaccard": round(jac, 6),
        "in_live_not_served": sorted(live_p0_ids - served_p0_ids),
        "in_served_not_live": sorted(served_p0_ids - live_p0_ids),
        "threshold": PAGE0_JACCARD_MIN,
        "verdict": "EXACT" if jac >= 0.999 else ("PARTIAL" if jac >= PAGE0_JACCARD_MIN else "DRIFT"),
    }

    # ---- per zero concept: where does the concept live? ------------------ #
    # The zero-concept input of THIS question is recomputed from ITS OWN served
    # bytes with the accepted rule (never copied from another question).
    zero_concepts = list(served_cov_full["concepts_with_zero_rows"])
    per_concept = []
    for concept in zero_concepts:
        in_served = served_cov_full["concept_row_counts"].get(concept, 0)
        in_served_lex = served_cov_lex["concept_row_counts"].get(concept, 0)
        in_live_p0 = live_p0_cov["concept_row_counts"].get(concept, 0)
        in_beyond = live_beyond_cov["concept_row_counts"].get(concept, 0)
        in_pool = live_pool_cov["concept_row_counts"].get(concept, 0)
        if in_pool <= 0:
            cause = CAUSE_NEVER
        elif in_beyond > 0 and in_live_p0 <= 0:
            cause = CAUSE_BEYOND_PAGE0
        elif in_live_p0 > 0 and in_beyond <= 0:
            cause = CAUSE_PAGE0_ONLY
        else:
            cause = CAUSE_POOL_COVERS
        matches = [
            r for r in live_rows
            if concept in SMA.deaccent(SMA.row_match_text(r)).lower()
        ]
        per_concept.append({
            "concept": concept,
            "cause_class": cause,
            "served_bundle_rows": in_served,
            "served_bundle_rows_lexical_only": in_served_lex,
            "live_page0_rows": in_live_p0,
            "live_pool_beyond_page0_rows": in_beyond,
            "live_pool_rows": in_pool,
            "live_pool_match_ids": [str(m.get("decision_id") or "") for m in matches[:10]],
            "remedy": CLASS_REMEDY[cause],
        })

    return {
        "qid": qid,
        "question": question_text,
        "variant_id": variant_id,
        "request_frozen_from_served_provenance": {
            "limit": limit,
            "offset": 0,
            "sort": sort,
            "fields": fields,
            "include_pinpoint": include_pinpoint,
            "base_url": OCL_BASE,
            "endpoint": "/decisions",
            "served_total": original.get("total"),
            "served_total_is_lower_bound": original.get("total_is_lower_bound"),
            "served_next_offset": original.get("next_offset"),
            "served_has_more": original.get("has_more"),
            "served_targets": (bundle.get("provenance") or {}).get("targets"),
        },
        "concepts": concepts,
        "zero_concepts": zero_concepts,
        "served_coverage_with_full_text": served_cov_full,
        "served_coverage_lexical_only": served_cov_lex,
        "served_page0_coverage": served_p0_cov,
        "live_page0_coverage": live_p0_cov,
        "live_pool_beyond_page0_coverage": live_beyond_cov,
        "live_pool_coverage": live_pool_cov,
        "page0_fidelity": fidelity,
        "pool_scan": {
            "n_pages_fetched": scan["n_pages_fetched"],
            "pages": scan["pages"],
            "n_rows_fetched": len(live_rows),
            "reported_total": scan["reported_total"],
            "total_is_lower_bound": scan["total_is_lower_bound"],
            "pool_complete": scan["pool_complete"],
            "max_pages_budget": max_pages,
        },
        "per_concept": per_concept,
    }


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #
def run_controls(measurements: list[dict], accepted_record: dict,
                 primary: dict, *, fetcher, sleep, nonsense_result) -> dict:
    """The frozen non-vacuity battery.  Every control is mechanical."""
    controls: dict[str, Any] = {}

    # C1 - replay fidelity to the served page-0 bytes.
    fid = primary["page0_fidelity"]
    controls["c1_page0_fidelity"] = {
        "definition": "live page-0 id set vs served page-0 id set, Jaccard >= threshold",
        "jaccard": fid["jaccard"],
        "threshold": PAGE0_JACCARD_MIN,
        "holds": fid["verdict"] in ("EXACT", "PARTIAL"),
        "verdict": fid["verdict"],
    }

    # C2 - a nonsense query must return zero rows.
    controls["c2_nonsense_query_zero_rows"] = {
        "definition": "a nonsense query returns 0 rows, so a zero is a measured zero",
        "query": NONSENSE_QUERY,
        "n_rows": nonsense_result.get("n_rows"),
        "holds": int(nonsense_result.get("n_rows") or 0) == 0,
    }

    # C3 - parity with the ACCEPTED record (recomputed, not copied).
    acc_q = None
    for q in accepted_record.get("per_question") or []:
        if q.get("qid") == primary["qid"]:
            acc_q = q
    if acc_q is None:
        acc_q = {}
    recomputed = primary["served_coverage_with_full_text"]
    controls["c3_accepted_record_parity"] = {
        "definition": "recomputed served coverage equals the accepted record's counts and zero list",
        "recomputed_counts": recomputed["concept_row_counts"],
        "accepted_counts": acc_q.get("concept_row_counts"),
        "recomputed_zero": recomputed["concepts_with_zero_rows"],
        "accepted_zero": acc_q.get("concepts_with_zero_rows"),
        "holds": (acc_q.get("concept_row_counts") == recomputed["concept_row_counts"]
                  and list(acc_q.get("concepts_with_zero_rows") or []) ==
                  list(recomputed["concepts_with_zero_rows"])),
    }

    # C4 - the served-side failure is not an artefact of full_text hydration.
    lex = primary["served_coverage_lexical_only"]["concept_row_counts"]
    full = primary["served_coverage_with_full_text"]["concept_row_counts"]
    zero_concepts = [c["concept"] for c in primary["per_concept"]]
    controls["c4_full_text_independence"] = {
        "definition": "every zero concept is zero in the served bundle with AND without full_text",
        "zero_concepts": zero_concepts,
        "lexical_counts": {c: lex.get(c) for c in zero_concepts},
        "full_text_counts": {c: full.get(c) for c in zero_concepts},
        "holds": all(int(lex.get(c, 0)) == 0 and int(full.get(c, 0)) == 0
                     for c in zero_concepts),
    }

    # C5 - the pool scan reached the end of the reported result set.
    scan = primary["pool_scan"]
    controls["c5_pool_scan_complete"] = {
        "definition": "the scan consumed every reported page (last page has_more == false)",
        "n_pages_fetched": scan["n_pages_fetched"],
        "reported_total": scan["reported_total"],
        "pool_complete": scan["pool_complete"],
        "holds": bool(scan["pool_complete"]),
    }

    # C6 - cross-language sanity: the two questions whose served coverage has no
    # zero concept must also have no zero concept on the live page 0.
    cross = []
    holds = True
    for m in measurements[1:]:
        z = m["live_page0_coverage"]["concepts_with_zero_rows"]
        cross.append({"qid": m["qid"], "live_page0_zero_concepts": z,
                      "served_zero_concepts": m["served_coverage_with_full_text"]["concepts_with_zero_rows"]})
        if z:
            holds = False
    controls["c6_cross_language_page0_sanity"] = {
        "definition": "the two non-failing served questions keep zero live page-0 zero-concepts",
        "questions": cross,
        "holds": holds,
    }

    all_hold = all(bool(c.get("holds")) for c in controls.values())
    return {"controls": controls, "all_hold": all_hold}


def oracle_reachability(primary: dict, *, fetcher, sleep) -> dict:
    """C7 - for every zero concept, a concept-only query must reach a row that
    contains the concept.  If it does not, the corpus itself carries no such
    decision and the cause class is CORPUS_ABSENCE, not a product defect."""
    out = []
    for pc in primary["per_concept"]:
        concept = pc["concept"]
        qtext = oracle_query_text(primary["question"], concept)
        try:
            payload = ocl_search(qtext, 0, 50, fetcher=fetcher)
            sleep(MIN_INTERVAL_S)
            rows = [lexical_row(r) for r in (payload.get("results") or [])]
            cov = coverage(rows, [concept])
            hits = cov["concept_row_counts"].get(concept, 0)
            out.append({
                "concept": concept,
                "oracle_query": qtext,
                "n_rows": len(rows),
                "rows_containing_concept": hits,
                "reachable": hits > 0,
                "example_ids": [r["decision_id"] for r in rows if concept in
                                SMA.deaccent(SMA.row_match_text(r)).lower()][:5],
                "reported_total": payload.get("total"),
            })
        except Exception as exc:  # network or parse failure -> control fails
            out.append({"concept": concept, "oracle_query": qtext,
                        "error": f"{type(exc).__name__}: {exc}", "reachable": False})
    return {
        "definition": "a concept-only query reaches at least one row containing the concept",
        "per_concept": out,
        "holds": all(bool(o.get("reachable")) for o in out),
    }


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def run(run_id: str, out: Path | None, mount_arg: str | None, repo: Path,
        max_pages: int = MAX_PAGES, live: bool = True,
        fetcher: Callable[[str, float], dict] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        ) -> tuple[int, dict]:
    mount = resolve_mount(mount_arg)
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 62,
        "run_id": run_id,
        "entry_point": "evaluation/retrieval_pool_attribution.py",
        "hypothesis": HYPOTHESIS_RELPATH,
        "freeze_record": FREEZE_RELPATH,
        "live_measurement": bool(live),
        "numeric_environment": numeric_environment(),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if mount is None:
        record.update({"verdict": VERDICT_VACUOUS, "exit_code": EXIT_VACUOUS,
                       "vacuity_reason": "accepted product mount not found"})
        return EXIT_VACUOUS, record

    record["product_mount"] = str(mount)
    record["product_mount_head"] = mount_head(mount)

    bundle_path, question_path = _question_paths(mount, PACKET, PRIMARY_QID)
    record["input_digests"] = {
        "bundle": sha256_file(bundle_path),
        "question": sha256_file(question_path),
    }
    acc_path = repo / ACCEPTED_RECORD_RELPATH
    if not acc_path.is_file():
        record.update({"verdict": VERDICT_VACUOUS, "exit_code": EXIT_VACUOUS,
                       "vacuity_reason": f"accepted record missing: {ACCEPTED_RECORD_RELPATH}"})
        return EXIT_VACUOUS, record
    accepted_record = json.loads(acc_path.read_text())
    record["accepted_record"] = ACCEPTED_RECORD_RELPATH
    record["accepted_record_sha256"] = sha256_file(acc_path)

    # The zero-concept input is recomputed from the accepted bytes.
    bundle = json.loads(bundle_path.read_text())
    qrec = json.loads(question_path.read_text())
    concepts = SMA.question_concepts(str(qrec.get("question") or ""))
    served_cov = coverage(bundle.get("decisions") or [], concepts)
    zero_concepts = served_cov["concepts_with_zero_rows"]
    record["recomputed_zero_concepts"] = zero_concepts
    if not zero_concepts:
        record.update({"verdict": VERDICT_NO_DEFECT, "exit_code": EXIT_NO_DEFECT,
                       "note": "no zero-row concept to attribute"})
        return EXIT_NO_DEFECT, record

    if not live:
        record.update({"verdict": VERDICT_VACUOUS, "exit_code": EXIT_VACUOUS,
                       "vacuity_reason": "live measurement disabled (--offline)"})
        return EXIT_VACUOUS, record

    def _fetcher(url: str, timeout: float) -> dict:
        if fetcher is not None:
            return fetcher(url, timeout)
        return _http_json(url, timeout)

    measurements: list[dict] = []
    errors: list[str] = []
    for qid in (PRIMARY_QID,) + CROSS_LANG_QIDS:
        try:
            measurements.append(measure_question(
                mount, PACKET, qid, fetcher=_fetcher, sleep=sleep,
                max_pages=max_pages if qid == PRIMARY_QID else 1))
        except Exception as exc:
            errors.append(f"{qid}: {type(exc).__name__}: {exc}")
    if not measurements:
        record.update({"verdict": VERDICT_VACUOUS, "exit_code": EXIT_VACUOUS,
                       "errors": errors,
                       "vacuity_reason": "no question could be measured"})
        return EXIT_VACUOUS, record

    primary = measurements[0]
    record["errors"] = errors

    # nonsense control
    try:
        payload = ocl_search(NONSENSE_QUERY, 0, 50, fetcher=_fetcher)
        sleep(MIN_INTERVAL_S)
        nonsense_result = {"n_rows": len(payload.get("results") or [])}
    except Exception as exc:
        nonsense_result = {"n_rows": None, "error": f"{type(exc).__name__}: {exc}"}

    control_battery = run_controls(measurements, accepted_record, primary,
                                   fetcher=_fetcher, sleep=sleep,
                                   nonsense_result=nonsense_result)
    oracle = oracle_reachability(primary, fetcher=_fetcher, sleep=sleep)
    control_battery["controls"]["c7_oracle_concept_reachable"] = oracle
    control_battery["all_hold"] = all(
        bool(c.get("holds")) for c in control_battery["controls"].values())

    record["measurements"] = measurements
    record["non_vacuity"] = control_battery

    if not control_battery["all_hold"]:
        record.update({"verdict": VERDICT_VACUOUS, "exit_code": EXIT_VACUOUS,
                       "vacuity_reason": "a frozen non-vacuity control did not hold"})
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        return EXIT_VACUOUS, record

    classes = [pc["cause_class"] for pc in primary["per_concept"]]
    dominant = None
    for cls in CLASS_PRIORITY:
        if cls in classes:
            dominant = cls
            break
    defect = bool(dominant and dominant in (CAUSE_BEYOND_PAGE0, CAUSE_PAGE0_ONLY, CAUSE_NEVER))
    record["attribution"] = {
        "zero_concepts": zero_concepts,
        "per_concept": primary["per_concept"],
        "classes": classes,
        "dominant_class": dominant,
        "dominant_remedy": CLASS_REMEDY.get(dominant) if dominant else None,
        "oracle_reachability": oracle,
        "served_targets": primary["request_frozen_from_served_provenance"]["served_targets"],
        "served_search_record": primary["request_frozen_from_served_provenance"],
    }
    verdict = VERDICT_DEFECT if defect else VERDICT_NO_DEFECT
    record["verdict"] = verdict
    record["exit_code"] = EXIT_DEFECT if defect else EXIT_NO_DEFECT
    record["claim_ceiling"] = (
        "This record attributes ONE accepted failure (the zero-row core concepts of the "
        "served German question in packet 39319405429) to one of three frozen cause classes "
        "by replaying the product's own recorded request against the live OpenCaseLaw corpus. "
        "It does NOT re-issue, weaken or re-score the accepted falsification; that verdict "
        "stands unchanged. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND "
        "or GEOMETRY_SOUND bars. It does NOT lift any DO-NOT-SERVE order and does NOT certify "
        "admission of any packet. It does NOT claim the map helps a jurist. It runs no "
        "obsolete universal-174k benchmark. human_gate_ready stays false."
    )
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record["exit_code"], record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--mount", default=None)
    ap.add_argument("--repo", default=str(REPO_ROOT))
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--offline", action="store_true",
                    help="do not touch the network; exits 2 (NOT_MEASURED_VACUOUS)")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else None
    code, record = run(args.run_id, out, args.mount, Path(args.repo),
                       max_pages=args.max_pages, live=not args.offline)
    if out is None:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        print(f"{record.get('verdict')} exit={code} -> {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
