"""
Retrieval orchestration with lazy fetching and citation neighborhood expansion.

Combines query expansion, search, deduplication, and lazy enrichment to produce
high-recall candidate sets for the query_result_bundle.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Set, Any, Callable
from collections import OrderedDict
import logging

from .client import OpenCaseLawClient, Decision, create_client
from .expansion import QueryExpander, get_search_variants
from .deduplication import DecisionDeduplicator, deduplicate_decisions, DecisionIdentity

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for retrieval behavior."""
    target_count: int = 150          # Target number of decisions
    max_pages_per_query: int = 5     # Max pagination pages per query variant
    max_query_variants: int = 4      # Max expanded query variants to execute
    enable_citation_expansion: bool = True
    citation_expansion_limit: int = 20  # Max citations to fetch per seed decision
    citation_seed_count: int = 10     # Number of top decisions to expand citations for
    enable_leading_cases: bool = True
    leading_cases_limit: int = 10
    prefer_provenance: Tuple[str, ...] = ("live", "cache", "fixture")
    language_filter: Optional[str] = None  # Optional language filter
    court_filter: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sort: str = "relevance"
    full_text_for_top: int = 20       # Fetch full text for top N decisions
    timeout: int = 30


@dataclass
class RetrievalStats:
    """Statistics from a retrieval run."""
    query: str
    query_variants_used: List[str]
    total_api_calls: int = 0
    cache_hits: int = 0
    decisions_fetched: int = 0
    decisions_after_dedupe: int = 0
    citation_expansions: int = 0
    leading_cases_added: int = 0
    full_text_fetched: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    provenance_breakdown: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetrievalOrchestrator:
    """
    Orchestrates the full retrieval pipeline:
    1. Query expansion (multilingual)
    2. Multi-variant search with pagination
    3. Deterministic deduplication
    4. Citation neighborhood expansion
    5. Leading cases expansion
    6. Lazy full-text fetching for top candidates
    """
    
    def __init__(
        self,
        client: Optional[OpenCaseLawClient] = None,
        config: Optional[RetrievalConfig] = None,
        cache_dir: Optional[str] = None,
    ):
        self.client = client or create_client(
            cache_dir=Path(cache_dir) if cache_dir else None,
            use_cache=True,
        )
        self.config = config or RetrievalConfig()
        self.expander = QueryExpander(
            max_expansion_terms=12,
            max_variants=self.config.max_query_variants,
        )
        self.deduplicator = DecisionDeduplicator(
            prefer_provenance=list(self.config.prefer_provenance),
        )
        self._stats = RetrievalStats(query="", query_variants_used=[])
    
    def retrieve(self, query: str) -> Tuple[List[Decision], RetrievalStats]:
        """
        Execute full retrieval pipeline for a query.
        
        Returns (decisions, stats) where decisions are deduplicated and enriched.
        """
        start_time = time.time()
        self._stats = RetrievalStats(query=query, query_variants_used=[])
        self.deduplicator.clear()
        
        # Step 1: Query expansion
        variants = get_search_variants(query, max_variants=self.config.max_query_variants)
        self._stats.query_variants_used = variants
        logger.info(f"Query expansion produced {len(variants)} variants: {variants}")
        
        # Step 2: Multi-variant search with pagination
        all_decisions = []
        for variant in variants:
            try:
                decisions, metadata = self.client.search_decisions_paginated(
                    query=variant,
                    target_count=self.config.target_count,
                    max_pages=self.config.max_pages_per_query,
                    language=self.config.language_filter,
                    court=self.config.court_filter,
                    date_from=self.config.date_from,
                    date_to=self.config.date_to,
                    sort=self.config.sort,
                    use_cache=True,
                )
                
                self._stats.total_api_calls += metadata.get("pages_fetched", 1)
                all_decisions.extend(decisions)
                
                if len(all_decisions) >= self.config.target_count * 2:
                    # We have enough candidates, stop searching variants
                    break
                    
            except Exception as e:
                error_msg = f"Search variant '{variant}' failed: {e}"
                logger.warning(error_msg)
                self._stats.errors.append(error_msg)
        
        logger.info(f"Raw search returned {len(all_decisions)} decisions")
        
        # Step 3: Deduplication
        unique_decisions, dedupe_report = deduplicate_decisions(
            all_decisions,
            prefer_provenance=list(self.config.prefer_provenance),
        )
        self._stats.decisions_fetched = len(all_decisions)
        self._stats.decisions_after_dedupe = len(unique_decisions)
        logger.info(f"After deduplication: {len(unique_decisions)} unique decisions")
        
        # Step 4: Citation neighborhood expansion
        if self.config.enable_citation_expansion and unique_decisions:
            self._expand_citations(unique_decisions)
        
        # Step 5: Leading cases expansion
        if self.config.enable_leading_cases and unique_decisions:
            self._expand_leading_cases(unique_decisions)
        
        # Step 6: Limit to target count
        final_decisions = unique_decisions[:self.config.target_count]
        
        # Step 7: Lazy full-text fetch for top decisions
        self._fetch_full_text(final_decisions)
        
        # Final stats
        self._stats.duration_seconds = time.time() - start_time
        self._stats.provenance_breakdown = self._compute_provenance_breakdown(final_decisions)
        
        # Update client stats
        client_stats = self.client.get_stats()
        self._stats.cache_hits = client_stats.get("cache", {}).get("hits", 0)
        self._stats.total_api_calls += client_stats.get("requests", 0)
        
        return final_decisions, self._stats
    
    def _expand_citations(self, decisions: List[Decision]) -> None:
        """Expand citation neighborhood for top decisions."""
        seed_decisions = decisions[:self.config.citation_seed_count]
        added_count = 0
        
        for decision in seed_decisions:
            try:
                # Fetch outgoing citations (cited decisions)
                cited_decisions, _ = self.client.get_decision_citations(
                    decision.decision_id,
                    direction="outgoing",
                    limit=self.config.citation_expansion_limit,
                    use_cache=True,
                )
                
                # Add cited decisions to our set
                for cited in cited_decisions:
                    if self.deduplicator.add(cited):
                        decisions.append(cited)
                        added_count += 1
                
                self._stats.citation_expansions += 1
                
            except Exception as e:
                logger.warning(f"Citation expansion failed for {decision.decision_id}: {e}")
                self._stats.errors.append(f"Citation expansion: {e}")
        
        self._stats.leading_cases_added += added_count
        logger.info(f"Citation expansion added {added_count} decisions")
    
    def _expand_leading_cases(self, decisions: List[Decision]) -> None:
        """Expand leading cases for top decisions."""
        seed_decisions = decisions[:min(5, len(decisions))]
        added_count = 0
        
        for decision in seed_decisions:
            try:
                leading, _ = self.client.get_leading_cases(
                    decision.decision_id,
                    limit=self.config.leading_cases_limit,
                    use_cache=True,
                )
                
                for lead in leading:
                    if self.deduplicator.add(lead):
                        decisions.append(lead)
                        added_count += 1
                        
            except Exception as e:
                logger.warning(f"Leading cases expansion failed for {decision.decision_id}: {e}")
                self._stats.errors.append(f"Leading cases: {e}")
        
        self._stats.leading_cases_added += added_count
        logger.info(f"Leading cases expansion added {added_count} decisions")
    
    def _fetch_full_text(self, decisions: List[Decision]) -> None:
        """Fetch full text for top decisions that don't have it."""
        fetched = 0
        for decision in decisions[:self.config.full_text_for_top]:
            if not decision.full_text or len(decision.full_text) < 100:
                try:
                    full_decision, provenance = self.client.get_decision(
                        decision.decision_id,
                        full_text=True,
                        use_cache=True,
                    )
                    if full_decision and full_decision.full_text:
                        decision.full_text = full_decision.full_text
                        decision.regeste = full_decision.regeste or decision.regeste
                        decision.rule_statement = full_decision.rule_statement or decision.rule_statement
                        decision.statutes = full_decision.statutes or decision.statutes
                        decision.citation_count = full_decision.citation_count
                        decision.cited_by_count = full_decision.cited_by_count
                        fetched += 1
                except Exception as e:
                    logger.warning(f"Full text fetch failed for {decision.decision_id}: {e}")
        
        self._stats.full_text_fetched = fetched
        logger.info(f"Fetched full text for {fetched} decisions")
    
    def _compute_provenance_breakdown(self, decisions: List[Decision]) -> Dict[str, int]:
        """Compute provenance distribution."""
        breakdown: Dict[str, int] = {}
        for d in decisions:
            prov = d.provenance or "unknown"
            breakdown[prov] = breakdown.get(prov, 0) + 1
        return breakdown


def retrieve_for_query(
    query: str,
    config: Optional[RetrievalConfig] = None,
    client: Optional[OpenCaseLawClient] = None,
) -> Tuple[List[Decision], RetrievalStats]:
    """
    Convenience function for one-shot retrieval.
    
    Creates orchestrator, runs retrieval, returns decisions and stats.
    """
    orchestrator = RetrievalOrchestrator(client=client, config=config)
    return orchestrator.retrieve(query)


# Lazy fetching utilities for downstream use

def fetch_decision_lazy(
    client: OpenCaseLawClient,
    decision_id: str,
    include_citations: bool = False,
    include_leading: bool = False,
) -> Tuple[Optional[Decision], Dict[str, Any]]:
    """
    Lazily fetch a single decision with optional enrichment.
    
    Used by downstream components (answer generation, map building) to fetch
    full content only for decisions that need it.
    """
    decision, provenance = client.get_decision(decision_id, full_text=True, use_cache=True)
    
    enrichment = {"provenance": provenance}
    
    if decision and include_citations:
        try:
            outgoing, _ = client.get_decision_citations(decision_id, "outgoing", limit=50)
            incoming, _ = client.get_decision_citations(decision_id, "incoming", limit=50)
            enrichment["citations_outgoing"] = [d.to_dict() for d in outgoing]
            enrichment["citations_incoming"] = [d.to_dict() for d in incoming]
        except Exception as e:
            enrichment["citations_error"] = str(e)
    
    if decision and include_leading:
        try:
            leading, _ = client.get_leading_cases(decision_id, limit=20)
            enrichment["leading_cases"] = [d.to_dict() for d in leading]
        except Exception as e:
            enrichment["leading_cases_error"] = str(e)
    
    return decision, enrichment


def fetch_multiple_lazy(
    client: OpenCaseLawClient,
    decision_ids: List[str],
    include_citations: bool = False,
    max_concurrent: int = 3,
) -> Dict[str, Tuple[Optional[Decision], Dict[str, Any]]]:
    """
    Fetch multiple decisions lazily with bounded concurrency.
    
    Respects rate limits by sequential fetching (OpenCaseLaw is fast enough
    that concurrency isn't critical for small batches).
    """
    results = {}
    for did in decision_ids:
        decision, enrichment = fetch_decision_lazy(
            client, did, include_citations=include_citations
        )
        results[did] = (decision, enrichment)
    return results


from pathlib import Path