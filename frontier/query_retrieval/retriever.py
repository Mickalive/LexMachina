"""
OpenCaseLaw Retrieval Adapter
Main entry point for turning Swiss legal questions into normalized query_result_bundles.
"""
import hashlib
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path

from .opencaselaw_client import OpenCaseLawClient, create_client
from .query_expansion import (
    expand_query,
    build_multilingual_search_queries,
    detect_query_language,
    get_legal_area_filter,
    ExpandedQuery,
)
from .bundle import (
    QueryResultBundle,
    DecisionBundleEntry,
    RetrievalProvenance,
    RetrievalSource,
    CounterAuthorityStatus,
    create_bundle_from_opencaselaw_results,
    validate_bundle,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for the retrieval pipeline."""
    target_candidate_count: int = 150
    max_candidate_count: int = 300
    min_candidate_count: int = 50
    
    # Multilingual
    enable_multilingual: bool = True
    languages: List[str] = field(default_factory=lambda: ["de", "fr", "it"])
    max_variants_per_language: int = 3
    
    # Citation expansion
    enable_citation_expansion: bool = True
    max_citation_depth: int = 1
    max_outgoing_citations: int = 20
    max_incoming_citations: int = 20
    max_appeal_chain_decisions: int = 10
    
    # Deduplication
    deduplicate_by_decision_id: bool = True
    
    # Lazy loading
    lazy_load_full_text: bool = True
    lazy_load_structure: bool = True
    lazy_load_citations: bool = True
    
    # Filters
    legal_area_filter: Optional[str] = None
    court_filter: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    
    # Cache/offline
    use_cache: bool = True
    offline_mode: bool = False
    
    def to_hash(self) -> str:
        """Generate deterministic hash of config for bundle tracking."""
        import json
        config_str = json.dumps({
            "target": self.target_candidate_count,
            "max": self.max_candidate_count,
            "multilingual": self.enable_multilingual,
            "languages": self.languages,
            "citation_expansion": self.enable_citation_expansion,
            "citation_depth": self.max_citation_depth,
            "dedupe": self.deduplicate_by_decision_id,
        }, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


class OpenCaseLawRetriever:
    """
    Production-ready OpenCaseLaw retrieval adapter.
    
    Transforms a Swiss legal question into a normalized QueryResultBundle
    with provenance, deduplication, multilingual expansion, and citation neighborhoods.
    """
    
    def __init__(
        self,
        client: Optional[OpenCaseLawClient] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        self.client = client or create_client()
        self.config = config or RetrievalConfig()
        self._stats = {
            "queries_executed": 0,
            "total_results_fetched": 0,
            "citations_expanded": 0,
            "deduplicates_removed": 0,
        }
    
    def retrieve(
        self,
        query: str,
        config_override: Optional[RetrievalConfig] = None,
    ) -> QueryResultBundle:
        """
        Main entry point: execute full retrieval pipeline for a query.
        
        Pipeline:
        1. Query expansion (multilingual)
        2. Parallel search across language variants
        3. Merge and deduplicate results
        4. Citation neighborhood expansion (if enabled)
        5. Build normalized bundle with provenance
        """
        config = config_override or self.config
        logger.info(f"Starting retrieval for query: {query[:100]}")
        
        # Step 1: Query expansion
        expanded_queries = {}
        if config.enable_multilingual:
            expanded_queries = build_multilingual_search_queries(
                query,
                languages=config.languages,
                max_variants_per_lang=config.max_variants_per_language,
            )
            logger.info(f"Expanded to {len(expanded_queries)} languages: "
                       f"{', '.join(f'{k}:{len(v)}' for k, v in expanded_queries.items())}")
        else:
            # Single language (detect or default)
            lang = detect_query_language(query)
            expanded_queries = {lang: [query]}
        
        # Step 2: Execute searches
        all_results = []
        search_metadata = []
        
        for lang, variants in expanded_queries.items():
            for variant_idx, variant in enumerate(variants):
                # Determine filters
                legal_area = config.legal_area_filter or get_legal_area_filter(variant, lang)
                
                results = self.client.search_decisions_paginated(
                    query=variant,
                    target_count=config.target_candidate_count,
                    language=lang,
                    court=config.court_filter,
                    date_from=config.date_from,
                    date_to=config.date_to,
                    legal_area=legal_area,
                    use_cache=config.use_cache,
                )
                
                if results:
                    provenance_base = {
                        "query_variant": variant,
                        "language": lang,
                        "page": 1,
                        "offset": 0,
                        "expansion_type": "multilingual" if variant != query else None,
                    }
                    search_metadata.append({
                        "language": lang,
                        "variant": variant,
                        "count": len(results),
                        "provenance": provenance_base,
                    })
                    all_results.extend(results)
        
        self._stats["queries_executed"] += len(search_metadata)
        self._stats["total_results_fetched"] += len(all_results)
        
        # Step 3: Deduplicate
        if config.deduplicate_by_decision_id:
            all_results = self._deduplicate_results(all_results)
            self._stats["deduplicates_removed"] += len(search_metadata) - len(all_results)
        
        # Step 4: Limit to max candidates
        if len(all_results) > config.max_candidate_count:
            all_results = all_results[:config.max_candidate_count]
        
        # Step 5: Build initial bundle
        bundle = create_bundle_from_opencaselaw_results(
            query=query,
            expanded_queries=expanded_queries,
            search_results=all_results,
            provenance_base={},  # Individual provenance already set in factory
        )
        
        # Fix provenance (the factory sets it per-result, so we need to update)
        for idx, entry in enumerate(bundle.decisions):
            if idx < len(all_results):
                result = all_results[idx]
                # Find matching metadata
                for meta in search_metadata:
                    # Match by decision_id
                    if any(r.get("decision_id") == entry.decision_id for r in [result]):
                        entry.provenance[0] = RetrievalProvenance(
                            source=RetrievalSource.OPENCASELAW_SEARCH,
                            query_variant=meta["variant"],
                            language=meta["language"],
                            relevance_score=result.get("relevance_score"),
                            expansion_type=meta["provenance"].get("expansion_type"),
                        )
                        break
        
        bundle.retrieval_metadata["search_metadata"] = search_metadata
        bundle.config_hash = config.to_hash()
        bundle.multilingual_expanded = config.enable_multilingual
        
        # Step 6: Citation expansion
        if config.enable_citation_expansion and bundle.decisions:
            self._expand_citations(bundle, config)
            bundle.citation_expanded = True
        
        # Final validation
        errors = validate_bundle(bundle)
        if errors:
            logger.warning(f"Bundle validation warnings: {errors}")
        
        logger.info(f"Retrieval complete: {len(bundle.decisions)} decisions in bundle")
        return bundle
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Deduplicate results by decision_id (keep first/highest score)."""
        seen: Dict[str, Dict] = {}
        for result in results:
            decision_id = result.get("decision_id", "")
            if decision_id and decision_id not in seen:
                seen[decision_id] = result
            elif decision_id and result.get("relevance_score", 0) > seen[decision_id].get("relevance_score", 0):
                # Keep higher relevance score
                seen[decision_id] = result
        return list(seen.values())
    
    def _expand_citations(self, bundle: QueryResultBundle, config: RetrievalConfig) -> None:
        """Expand citation neighborhoods for decisions in the bundle."""
        # Select seed decisions for expansion (top N by retrieval score)
        seed_decisions = sorted(
            bundle.decisions,
            key=lambda d: d.retrieval_score,
            reverse=True
        )[:min(20, len(bundle.decisions))]
        
        existing_ids = bundle.decision_ids()
        new_entries = []
        
        for seed in seed_decisions:
            # Outgoing citations (cited decisions)
            if config.max_outgoing_citations > 0:
                cited = self._fetch_outgoing_citations(seed, config)
                for cited_entry in cited:
                    if cited_entry.decision_id not in existing_ids:
                        existing_ids.add(cited_entry.decision_id)
                        new_entries.append(cited_entry)
            
            # Incoming citations (citing decisions)
            if config.max_incoming_citations > 0:
                citing = self._fetch_incoming_citations(seed, config)
                for citing_entry in citing:
                    if citing_entry.decision_id not in existing_ids:
                        existing_ids.add(citing_entry.decision_id)
                        new_entries.append(citing_entry)
            
            # Appeal chain
            if config.max_appeal_chain_decisions > 0:
                appeal = self._fetch_appeal_chain(seed, config)
                for appeal_entry in appeal:
                    if appeal_entry.decision_id not in existing_ids:
                        existing_ids.add(appeal_entry.decision_id)
                        new_entries.append(appeal_entry)
        
        # Add new entries to bundle
        bundle.decisions.extend(new_entries)
        bundle.total_after_dedupe = len(bundle.decisions)
        self._stats["citations_expanded"] += len(new_entries)
        logger.info(f"Citation expansion added {len(new_entries)} decisions")
    
    def _fetch_outgoing_citations(
        self,
        seed: DecisionBundleEntry,
        config: RetrievalConfig,
    ) -> List[DecisionBundleEntry]:
        """Fetch outgoing citations for a seed decision."""
        try:
            response = self.client.get_citations(
                seed.decision_id,
                direction="outgoing",
                limit=config.max_outgoing_citations,
                use_cache=config.use_cache,
            )
            
            outgoing = response.get("outgoing", [])
            entries = []
            
            for idx, citation in enumerate(outgoing):
                target_id = citation.get("target_decision_id")
                if not target_id:
                    continue
                
                # Get full decision for metadata
                try:
                    decision = self.client.get_decision(target_id, use_cache=config.use_cache)
                    entry = self._create_entry_from_decision(
                        decision,
                        RetrievalSource.OPENCASELAW_CITATION_OUTGOING,
                        seed.decision_id,
                        1,
                        "citation_outgoing",
                    )
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to fetch cited decision {target_id}: {e}")
            
            return entries[:config.max_outgoing_citations]
        except Exception as e:
            logger.warning(f"Failed to fetch outgoing citations for {seed.decision_id}: {e}")
            return []
    
    def _fetch_incoming_citations(
        self,
        seed: DecisionBundleEntry,
        config: RetrievalConfig,
    ) -> List[DecisionBundleEntry]:
        """Fetch incoming citations (citing decisions) for a seed decision."""
        try:
            response = self.client.get_citations(
                seed.decision_id,
                direction="incoming",
                limit=config.max_incoming_citations,
                use_cache=config.use_cache,
            )
            
            incoming = response.get("incoming", [])
            entries = []
            
            for idx, citation in enumerate(incoming):
                source_id = citation.get("source_decision_id")
                if not source_id:
                    continue
                
                try:
                    decision = self.client.get_decision(source_id, use_cache=config.use_cache)
                    entry = self._create_entry_from_decision(
                        decision,
                        RetrievalSource.OPENCASELAW_CITATION_INCOMING,
                        seed.decision_id,
                        1,
                        "citation_incoming",
                    )
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to fetch citing decision {source_id}: {e}")
            
            return entries[:config.max_incoming_citations]
        except Exception as e:
            logger.warning(f"Failed to fetch incoming citations for {seed.decision_id}: {e}")
            return []
    
    def _fetch_appeal_chain(
        self,
        seed: DecisionBundleEntry,
        config: RetrievalConfig,
    ) -> List[DecisionBundleEntry]:
        """Fetch appeal chain (procedural history) for a seed decision."""
        try:
            response = self.client.get_appeal_chain(seed.decision_id, use_cache=config.use_cache)
            
            # The appeal chain response format varies; extract decision IDs
            entries = []
            chain = response.get("chain", response.get("appeal_chain", []))
            
            for item in chain[:config.max_appeal_chain_decisions]:
                decision_id = item.get("decision_id") or item.get("id")
                if not decision_id:
                    continue
                
                try:
                    decision = self.client.get_decision(decision_id, use_cache=config.use_cache)
                    entry = self._create_entry_from_decision(
                        decision,
                        RetrievalSource.OPENCASELAW_APPEAL_CHAIN,
                        seed.decision_id,
                        1,
                        "appeal_chain",
                    )
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to fetch appeal chain decision {decision_id}: {e}")
            
            return entries
        except Exception as e:
            logger.warning(f"Failed to fetch appeal chain for {seed.decision_id}: {e}")
            return []
    
    def _create_entry_from_decision(
        self,
        decision: Dict,
        source: RetrievalSource,
        parent_id: str,
        depth: int,
        expansion_type: str,
    ) -> Optional[DecisionBundleEntry]:
        """Create a DecisionBundleEntry from a full decision response."""
        decision_id = decision.get("decision_id") or decision.get("canonical_decision_id")
        if not decision_id:
            return None
        
        prov = RetrievalProvenance(
            source=source,
            query_variant=None,
            language=decision.get("language"),
            relevance_score=None,
            citation_depth=depth,
            parent_decision_id=parent_id,
            expansion_type=expansion_type,
        )
        
        return DecisionBundleEntry(
            decision_id=decision_id,
            canonical_url=decision.get("canonical_url", ""),
            citation_string_de=decision.get("citation_string_de", ""),
            citation_string_fr=decision.get("citation_string_fr", ""),
            citation_string_it=decision.get("citation_string_it", ""),
            court=decision.get("court", ""),
            court_level=decision.get("court_level"),
            canton=decision.get("canton"),
            chamber=decision.get("chamber"),
            docket_number=decision.get("docket_number"),
            decision_date=decision.get("decision_date"),
            language=decision.get("language", "de"),
            legal_area=decision.get("legal_area"),
            title=decision.get("title"),
            regeste=decision.get("regeste") or decision.get("rule_statement"),
            snippet=decision.get("snippet"),
            provenance=[prov],
            retrieval_score=0.5,  # Default for citation-expanded entries
        )
    
    # ===== Lazy loading methods =====
    
    def load_full_text(self, bundle: QueryResultBundle, decision_ids: List[str]) -> int:
        """Lazy load full text for specified decisions."""
        loaded = 0
        for decision_id in decision_ids:
            entry = bundle.get_decision(decision_id)
            if entry and entry.full_text is None:
                try:
                    decision = self.client.get_decision(decision_id, use_cache=self.config.use_cache)
                    entry.full_text = decision.get("full_text")
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load full text for {decision_id}: {e}")
        return loaded
    
    def load_structure(self, bundle: QueryResultBundle, decision_ids: List[str]) -> int:
        """Lazy load structure (regeste, sachverhalt, erwaegungen) for decisions."""
        loaded = 0
        for decision_id in decision_ids:
            entry = bundle.get_decision(decision_id)
            if entry and entry.structure is None:
                try:
                    structure = self.client.get_decision_structure(decision_id, use_cache=self.config.use_cache)
                    entry.structure = structure
                    # Also update regeste if not present
                    if not entry.regeste and structure.get("regeste"):
                        entry.regeste = structure["regeste"]
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load structure for {decision_id}: {e}")
        return loaded
    
    def load_citations(self, bundle: QueryResultBundle, decision_ids: List[str]) -> int:
        """Lazy load citation graph for decisions."""
        loaded = 0
        for decision_id in decision_ids:
            entry = bundle.get_decision(decision_id)
            if entry and (entry.citations_outgoing is None or entry.citations_incoming is None):
                try:
                    citations = self.client.get_citations(decision_id, direction="both", use_cache=self.config.use_cache)
                    entry.citations_outgoing = citations.get("outgoing", [])
                    entry.citations_incoming = citations.get("incoming", [])
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load citations for {decision_id}: {e}")
        return loaded
    
    def load_appeal_chain(self, bundle: QueryResultBundle, decision_ids: List[str]) -> int:
        """Lazy load appeal chain for decisions."""
        loaded = 0
        for decision_id in decision_ids:
            entry = bundle.get_decision(decision_id)
            if entry and entry.appeal_chain is None:
                try:
                    chain = self.client.get_appeal_chain(decision_id, use_cache=self.config.use_cache)
                    entry.appeal_chain = chain
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load appeal chain for {decision_id}: {e}")
        return loaded
    
    # ===== Utility methods =====
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            **self._stats,
            "client_stats": self.client.get_stats(),
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "queries_executed": 0,
            "total_results_fetched": 0,
            "citations_expanded": 0,
            "deduplicates_removed": 0,
        }
    
    def save_fixtures(self, bundle: QueryResultBundle, fixture_dir: Path) -> None:
        """Save bundle decisions as fixtures for offline testing."""
        fixture_dir.mkdir(parents=True, exist_ok=True)
        for entry in bundle.decisions:
            if entry.full_text:
                self.client.save_fixture("GET", f"/decisions/{entry.decision_id}", 
                                       {"full_text": entry.full_text})
            if entry.structure:
                self.client.save_fixture("GET", f"/structure/{entry.decision_id}", entry.structure)
            if entry.citations_outgoing is not None or entry.citations_incoming is not None:
                self.client.save_fixture("GET", f"/citations/{entry.decision_id}", {
                    "outgoing": entry.citations_outgoing or [],
                    "incoming": entry.citations_incoming or [],
                })
            if entry.appeal_chain:
                self.client.save_fixture("GET", f"/appeal-chain/{entry.decision_id}", entry.appeal_chain)


def create_retriever(
    target_count: int = 150,
    max_count: int = 300,
    enable_multilingual: bool = True,
    enable_citations: bool = True,
    offline: bool = False,
    cache_ttl: int = 3600,
) -> OpenCaseLawRetriever:
    """Factory function to create a configured retriever."""
    config = RetrievalConfig(
        target_candidate_count=target_count,
        max_candidate_count=max_count,
        enable_multilingual=enable_multilingual,
        enable_citation_expansion=enable_citations,
        offline_mode=offline,
    )
    
    client = create_client(
        offline=offline,
        cache_ttl=cache_ttl,
    )
    
    return OpenCaseLawRetriever(client=client, config=config)