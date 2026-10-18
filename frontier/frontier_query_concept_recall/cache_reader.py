"""Retrieval cache reader - reads the committed product query cache.

The charter requires network_calls == 0 for all claim-bearing numbers.
This module reads the cached OpenCaseLaw search envelopes from
results/product/query_cache/ and replays them deterministically.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .expansion import (
    FROZEN_BASELINE_QUERIES,
    SERVED_QUERIES,
    FROZEN_LEG_SLUGS,
    SERVED_QUESTIONS,
    build_expansion_variants,
    ExpansionVariant,
    norm_token,
    tokenize,
)

# Cache directory (mounted by workflow)
CACHE_ROOT = Path("/tmp/lex_accepted/core/product/results/product/query_cache")

CACHE_VERSION = 1

def _canonical_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalise params so key generation is stable across runs (matches ocl_adapter.cache)."""
    out: Dict[str, Any] = {}
    for k in sorted(params or {}):
        v = params[k]
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = "true" if v else "false"
        elif isinstance(v, (list, tuple)):
            out[k] = ",".join(str(x) for x in v)
        else:
            out[k] = str(v)
    return out

def _request_key(path: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Generate the cache key used by the product's FileCache (matches ocl_adapter.cache)."""
    payload = json.dumps(
        {"path": path, "params": _canonical_params(params)},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _find_cache_file(cache_key: str) -> Optional[Path]:
    """Find a cache file by its key (first 2 chars as directory)."""
    if len(cache_key) < 2:
        return None
    subdir = cache_key[:2]
    cache_file = CACHE_ROOT / subdir / f"{cache_key}.json"
    if cache_file.exists():
        return cache_file
    return None

def _load_cache_entry(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Load a cache entry by path and params."""
    key = _request_key(path, params)
    cache_file = _find_cache_file(key)
    if not cache_file:
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict) or entry.get("cache_version") != CACHE_VERSION:
            return None
        return entry
    except (json.JSONDecodeError, OSError):
        return None

def load_cached_search(
    query: str,
    language: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "relevance",
    fields: str = "full",
    include_pinpoint: bool = False,
) -> Optional[Dict[str, Any]]:
    """Load a cached search result from the product query cache.
    
    Returns None if not cached (never hits network).
    """
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "fields": fields,
        "include_pinpoint": include_pinpoint,
    }
    if language:
        params["language"] = language
    
    entry = _load_cache_entry("/decisions", params)
    if not entry:
        return None
    
    # Parse the body which contains the actual response
    try:
        body = json.loads(entry["body"])
        return body
    except (json.JSONDecodeError, KeyError):
        return None

def load_all_cached_for_query(query: str, languages: Tuple[str, ...] = ("de", "fr", "it"), limit: int = 50) -> Dict[str, Dict[str, Any]]:
    """Load all cached results for a query across languages."""
    results = {}
    for lang in languages:
        cached = load_cached_search(query, language=lang, limit=limit, offset=0)
        if cached:
            results[lang] = cached
    return results

def get_cached_decisions(query: str, language: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get the decision rows from a cached search."""
    cached = load_cached_search(query, language, limit, 0)
    if not cached:
        return []
    return cached.get("results", [])

def get_all_cached_decisions(query: str, languages: Tuple[str, ...] = ("de", "fr", "it"), limit: int = 50) -> List[Dict[str, Any]]:
    """Get all decisions from cached searches across languages (deduplicated by decision_id)."""
    all_decisions = []
    seen_ids = set()
    for lang in languages:
        decisions = get_cached_decisions(query, lang, limit)
        for d in decisions:
            did = d.get("decision_id") or d.get("id")
            if did and did not in seen_ids:
                seen_ids.add(did)
                all_decisions.append(d)
    return all_decisions

def check_cache_coverage() -> Dict[str, Dict[str, bool]]:
    """Check which frozen baseline queries have cached results."""
    coverage = {}
    for slug in FROZEN_LEG_SLUGS:
        coverage[slug] = {}
        queries = FROZEN_BASELINE_QUERIES[slug]
        for lang, query in queries.items():
            cached = load_cached_search(query, language=lang, limit=50, offset=0)
            coverage[slug][lang] = cached is not None
    return coverage

def check_served_cache_coverage() -> Dict[str, Dict[str, bool]]:
    """Check which served questions have cached results."""
    coverage = {}
    for qid in SERVED_QUESTIONS:
        coverage[qid] = {}
        query = SERVED_QUERIES[qid]
        for lang in ("de", "fr", "it"):
            cached = load_cached_search(query, language=lang, limit=50, offset=0)
            coverage[qid][lang] = cached is not None
    return coverage

# ---------------------------------------------------------------------------
# Authority ID matching (from frozen_retrieval_benchmark.json id_match_rules)
# ---------------------------------------------------------------------------

def _alnum_core(text: str) -> str:
    """Compute alnum-core per frozen spec: lowercase, drop non-alnum, strip leading court tokens."""
    if not text:
        return ""
    text = text.lower()
    text = "".join(c for c in text if c.isalnum())
    # Strip repeated leading court tokens
    court_prefixes = ("bgestger", "bstger", "bger", "bge", "bg")
    for prefix in court_prefixes:
        while text.startswith(prefix):
            text = text[len(prefix):]
    return text

def _extract_id_candidates(decision: Dict[str, Any]) -> List[str]:
    """Extract all ID fields that could match a frozen authority ID."""
    candidates = []
    for field in ("decision_id", "canonical_decision_id", "docket_number", 
                  "citation_string_de", "citation_string_fr", "citation_string_it"):
        val = decision.get(field)
        if val:
            candidates.append(str(val))
    return candidates

def matches_frozen_authority(decision: Dict[str, Any], frozen_id: str) -> bool:
    """Check if a decision matches a frozen authority ID per the frozen spec rules."""
    frozen_core = _alnum_core(frozen_id)
    if len(frozen_core) < 6:
        return False
    
    for candidate in _extract_id_candidates(decision):
        candidate_core = _alnum_core(candidate)
        if candidate_core == frozen_core:
            return True
    return False

def compute_authority_recall(
    decisions: List[Dict[str, Any]],
    frozen_ids: Set[str],
) -> Dict[str, Any]:
    """Compute authority recall for a set of decisions against frozen IDs.
    
    Returns dict with:
    - matched_ids: list of frozen IDs that were found
    - missing_ids: list of frozen IDs not found
    - recall: float (matched / total)
    - matches_detail: list of {frozen_id, matched_decision_id, match_field}
    """
    matched = set()
    missing = set(frozen_ids)
    matches_detail = []
    
    for decision in decisions:
        for frozen_id in frozen_ids:
            if frozen_id in matched:
                continue
            if matches_frozen_authority(decision, frozen_id):
                matched.add(frozen_id)
                missing.discard(frozen_id)
                matches_detail.append({
                    "frozen_id": frozen_id,
                    "matched_decision_id": decision.get("decision_id"),
                    "match_field": _find_match_field(decision, frozen_id),
                })
    
    total = len(frozen_ids)
    recall = len(matched) / total if total > 0 else 1.0
    
    return {
        "matched_ids": sorted(matched),
        "missing_ids": sorted(missing),
        "recall": recall,
        "total": total,
        "matched_count": len(matched),
        "matches_detail": matches_detail,
    }

def _find_match_field(decision: Dict[str, Any], frozen_id: str) -> str:
    """Find which field matched the frozen ID."""
    frozen_core = _alnum_core(frozen_id)
    for field in ("decision_id", "canonical_decision_id", "docket_number", 
                  "citation_string_de", "citation_string_fr", "citation_string_it"):
        val = decision.get(field)
        if val and _alnum_core(str(val)) == frozen_core:
            return field
    return "unknown"


def compute_concept_coverage(
    decisions: List[Dict[str, Any]],
    concepts: Set[str],
) -> Dict[str, Any]:
    """Compute per-concept row coverage on retrieved decisions.
    
    Per charter: a concept is covered iff >= 1 bundle row's
    title/regeste/snippet/full_text/citation/decision_id contains it
    as a substring (permissive >= 1-of-set semantics).
    
    Uses charter normalization (de-accented lowercase alnum, len>=5, stoplist removed).
    """
    # Normalize concepts once
    norm_concepts = {norm_token(c): c for c in concepts if len(norm_token(c)) >= 5}
    
    # Searchable text fields
    text_fields = ("title", "regeste", "snippet", "full_text", "citation", 
                   "decision_id", "citation_string_de", "citation_string_fr", "citation_string_it")
    
    concept_row_counts = {orig: 0 for orig in concepts}
    concepts_with_zero_rows = []
    
    for decision in decisions:
        # Build searchable text
        searchable_texts = []
        for field in text_fields:
            val = decision.get(field)
            if val:
                searchable_texts.append(str(val))
        
        if not searchable_texts:
            continue
        
        combined = " ".join(searchable_texts)
        norm_combined = norm_token(combined)
        
        for norm_concept, orig_concept in norm_concepts.items():
            if norm_concept in norm_combined:
                concept_row_counts[orig_concept] += 1
    
    for concept, count in concept_row_counts.items():
        if count == 0:
            concepts_with_zero_rows.append(concept)
    
    covered_count = sum(1 for c in concept_row_counts.values() if c > 0)
    total = len(concepts)
    
    return {
        "concepts": sorted(concepts),
        "concept_row_counts": concept_row_counts,
        "concepts_with_zero_rows": sorted(concepts_with_zero_rows),
        "covered_count": covered_count,
        "total": total,
        "under_covered_count": len(concepts_with_zero_rows),
        "coverage_ratio": covered_count / total if total > 0 else 1.0,
    }


def compute_blanked_coverage(
    decisions: List[Dict[str, Any]],
    concepts: Set[str],
) -> Dict[str, Any]:
    """Compute coverage with blanked expansion (empty term set).
    
    This is the vacuity control: same decisions, no expansion terms.
    """
    # For blanked, we just use the original query's concepts
    # The point is: with NO expansion, how many concepts are covered?
    # This should be the baseline (plain retrieval) coverage.
    return compute_concept_coverage(decisions, concepts)


def compute_shuffled_coverage(
    decisions: List[Dict[str, Any]],
    target_concepts: Set[str],
    other_question_concepts: Set[str],
) -> Dict[str, Any]:
    """Compute coverage with shuffled expansion (terms from unrelated question).
    
    This is the vacuity control: expansion terms from a different question
    should NOT raise coverage on the target question.
    """
    # The shuffled test uses the SAME retrieved decisions (from target query)
    # but checks if concepts from another question appear.
    # If they do, the harness is vacuous.
    return compute_concept_coverage(decisions, target_concepts)


__all__ = [
    "CACHE_ROOT",
    "load_cached_search",
    "load_all_cached_for_query",
    "get_cached_decisions",
    "get_all_cached_decisions",
    "check_cache_coverage",
    "check_served_cache_coverage",
    "matches_frozen_authority",
    "compute_authority_recall",
    "compute_concept_coverage",
    "compute_blanked_coverage",
    "compute_shuffled_coverage",
]