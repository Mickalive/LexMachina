"""
Normalized Query Result Bundle
Canonical data structures for the query-specific retrieval pipeline.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import json


class RetrievalSource(Enum):
    """Source of a retrieved decision."""
    OPENCASELAW_SEARCH = "opencaselaw_search"
    OPENCASELAW_CITATION_OUTGOING = "opencaselaw_citation_outgoing"
    OPENCASELAW_CITATION_INCOMING = "opencaselaw_citation_incoming"
    OPENCASELAW_LEADING_CASE = "opencaselaw_leading_case"
    OPENCASELAW_APPEAL_CHAIN = "opencaselaw_appeal_chain"
    CACHE = "cache"
    FIXTURE = "fixture"


class CounterAuthorityStatus(Enum):
    """Counter-authority classification status."""
    UNCLASSIFIED = "unclassified"
    SUPPORTING = "supporting"
    LIMITING = "limiting"
    CONTRARY = "contrary"
    DISTINGUISHING = "distinguishing"
    EXCEPTION = "exception"
    MINORITY_LINE = "minority_line"
    UNCERTAIN = "uncertain"


@dataclass
class RetrievalProvenance:
    """Provenance metadata for a retrieved decision."""
    source: RetrievalSource
    query_variant: Optional[str] = None
    language: Optional[str] = None
    relevance_score: Optional[float] = None
    page: Optional[int] = None
    offset: Optional[int] = None
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    citation_depth: int = 0
    parent_decision_id: Optional[str] = None
    expansion_type: Optional[str] = None  # "multilingual", "citation_outgoing", "citation_incoming", "appeal_chain"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "query_variant": self.query_variant,
            "language": self.language,
            "relevance_score": self.relevance_score,
            "page": self.page,
            "offset": self.offset,
            "retrieved_at": self.retrieved_at,
            "citation_depth": self.citation_depth,
            "parent_decision_id": self.parent_decision_id,
            "expansion_type": self.expansion_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalProvenance":
        return cls(
            source=RetrievalSource(data["source"]),
            query_variant=data.get("query_variant"),
            language=data.get("language"),
            relevance_score=data.get("relevance_score"),
            page=data.get("page"),
            offset=data.get("offset"),
            retrieved_at=data.get("retrieved_at", datetime.utcnow().isoformat() + "Z"),
            citation_depth=data.get("citation_depth", 0),
            parent_decision_id=data.get("parent_decision_id"),
            expansion_type=data.get("expansion_type"),
        )


@dataclass
class DecisionBundleEntry:
    """
    Normalized decision entry in a query_result_bundle.
    
    Contains all metadata needed for downstream answer generation and mapping.
    """
    # Core identifiers
    decision_id: str
    canonical_url: str
    citation_string_de: str
    citation_string_fr: str
    citation_string_it: str
    
    # Metadata
    court: str
    court_level: Optional[str] = None
    canton: Optional[str] = None
    chamber: Optional[str] = None
    docket_number: Optional[str] = None
    decision_date: Optional[str] = None
    language: str = "de"
    legal_area: Optional[str] = None
    title: Optional[str] = None
    regeste: Optional[str] = None
    snippet: Optional[str] = None
    
    # Retrieval provenance
    provenance: List[RetrievalProvenance] = field(default_factory=list)
    
    # Lazy-loaded full content (populated on demand)
    full_text: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None
    citations_outgoing: Optional[List[Dict]] = None
    citations_incoming: Optional[List[Dict]] = None
    appeal_chain: Optional[Dict] = None
    
    # Scoring/ranking
    retrieval_score: float = 0.0
    rerank_score: Optional[float] = None
    
    # Counter-authority status
    counter_authority_status: CounterAuthorityStatus = CounterAuthorityStatus.UNCLASSIFIED
    counter_authority_evidence: Optional[str] = None
    
    # Clustering/projection (for map)
    cluster_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (excludes lazy-loaded full content by default)."""
        return {
            "decision_id": self.decision_id,
            "canonical_url": self.canonical_url,
            "citation_string_de": self.citation_string_de,
            "citation_string_fr": self.citation_string_fr,
            "citation_string_it": self.citation_string_it,
            "court": self.court,
            "court_level": self.court_level,
            "canton": self.canton,
            "chamber": self.chamber,
            "docket_number": self.docket_number,
            "decision_date": self.decision_date,
            "language": self.language,
            "legal_area": self.legal_area,
            "title": self.title,
            "regeste": self.regeste,
            "snippet": self.snippet,
            "provenance": [p.to_dict() for p in self.provenance],
            "retrieval_score": self.retrieval_score,
            "rerank_score": self.rerank_score,
            "counter_authority_status": self.counter_authority_status.value,
            "counter_authority_evidence": self.counter_authority_evidence,
            "cluster_id": self.cluster_id,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            # Lazy fields - only include if populated
            **({"full_text": self.full_text} if self.full_text else {}),
            **({"structure": self.structure} if self.structure else {}),
            **({"citations_outgoing": self.citations_outgoing} if self.citations_outgoing else {}),
            **({"citations_incoming": self.citations_incoming} if self.citations_incoming else {}),
            **({"appeal_chain": self.appeal_chain} if self.appeal_chain else {}),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionBundleEntry":
        """Deserialize from dict."""
        provenance = [RetrievalProvenance.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            decision_id=data["decision_id"],
            canonical_url=data["canonical_url"],
            citation_string_de=data["citation_string_de"],
            citation_string_fr=data["citation_string_fr"],
            citation_string_it=data["citation_string_it"],
            court=data["court"],
            court_level=data.get("court_level"),
            canton=data.get("canton"),
            chamber=data.get("chamber"),
            docket_number=data.get("docket_number"),
            decision_date=data.get("decision_date"),
            language=data.get("language", "de"),
            legal_area=data.get("legal_area"),
            title=data.get("title"),
            regeste=data.get("regeste"),
            snippet=data.get("snippet"),
            provenance=provenance,
            full_text=data.get("full_text"),
            structure=data.get("structure"),
            citations_outgoing=data.get("citations_outgoing"),
            citations_incoming=data.get("citations_incoming"),
            appeal_chain=data.get("appeal_chain"),
            retrieval_score=data.get("retrieval_score", 0.0),
            rerank_score=data.get("rerank_score"),
            counter_authority_status=CounterAuthorityStatus(data.get("counter_authority_status", "unclassified")),
            counter_authority_evidence=data.get("counter_authority_evidence"),
            cluster_id=data.get("cluster_id"),
            x=data.get("x"),
            y=data.get("y"),
            z=data.get("z"),
        )
    
    def add_provenance(self, prov: RetrievalProvenance) -> None:
        """Add a provenance record."""
        self.provenance.append(prov)
    
    def get_primary_provenance(self) -> Optional[RetrievalProvenance]:
        """Get the primary (first) provenance record."""
        return self.provenance[0] if self.provenance else None
    
    def has_full_content(self) -> bool:
        """Check if full text/structure is loaded."""
        return self.full_text is not None or self.structure is not None


@dataclass
class QueryResultBundle:
    """
    Canonical query result bundle for downstream answer generation and mapping.
    
    This is the primary contract between the retrieval adapter and the product layer.
    """
    query: str
    expanded_queries: Dict[str, List[str]]  # language -> query variants
    decisions: List[DecisionBundleEntry]
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    config_hash: str = ""
    
    # Processing status
    total_candidates_found: int = 0
    total_after_dedupe: int = 0
    citation_expanded: bool = False
    multilingual_expanded: bool = False
    
    def to_dict(self, include_full_content: bool = False) -> Dict[str, Any]:
        """Serialize to dict."""
        result = {
            "query": self.query,
            "expanded_queries": self.expanded_queries,
            "decisions": [d.to_dict() for d in self.decisions],
            "retrieval_metadata": self.retrieval_metadata,
            "generated_at": self.generated_at,
            "config_hash": self.config_hash,
            "total_candidates_found": self.total_candidates_found,
            "total_after_dedupe": self.total_after_dedupe,
            "citation_expanded": self.citation_expanded,
            "multilingual_expanded": self.multilingual_expanded,
        }
        
        if not include_full_content:
            # Strip lazy-loaded content for lighter payloads
            for decision in result["decisions"]:
                for key in ["full_text", "structure", "citations_outgoing", "citations_incoming", "appeal_chain"]:
                    decision.pop(key, None)
        
        return result
    
    def to_json(self, include_full_content: bool = False) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(include_full_content), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResultBundle":
        """Deserialize from dict."""
        decisions = [DecisionBundleEntry.from_dict(d) for d in data.get("decisions", [])]
        return cls(
            query=data["query"],
            expanded_queries=data.get("expanded_queries", {}),
            decisions=decisions,
            retrieval_metadata=data.get("retrieval_metadata", {}),
            generated_at=data.get("generated_at", datetime.utcnow().isoformat() + "Z"),
            config_hash=data.get("config_hash", ""),
            total_candidates_found=data.get("total_candidates_found", 0),
            total_after_dedupe=data.get("total_after_dedupe", 0),
            citation_expanded=data.get("citation_expanded", False),
            multilingual_expanded=data.get("multilingual_expanded", False),
        )
    
    def get_decision(self, decision_id: str) -> Optional[DecisionBundleEntry]:
        """Get decision by ID."""
        for d in self.decisions:
            if d.decision_id == decision_id:
                return d
        return None
    
    def get_decisions_by_language(self, language: str) -> List[DecisionBundleEntry]:
        """Get decisions filtered by language."""
        return [d for d in self.decisions if d.language == language]
    
    def get_counter_authorities(self) -> List[DecisionBundleEntry]:
        """Get decisions classified as counter-authorities."""
        statuses = {
            CounterAuthorityStatus.CONTRARY,
            CounterAuthorityStatus.LIMITING,
            CounterAuthorityStatus.DISTINGUISHING,
            CounterAuthorityStatus.EXCEPTION,
            CounterAuthorityStatus.MINORITY_LINE,
        }
        return [d for d in self.decisions if d.counter_authority_status in statuses]
    
    def get_supporting_authorities(self) -> List[DecisionBundleEntry]:
        """Get decisions classified as supporting."""
        return [d for d in self.decisions if d.counter_authority_status == CounterAuthorityStatus.SUPPORTING]
    
    def get_unclassified(self) -> List[DecisionBundleEntry]:
        """Get unclassified decisions."""
        return [d for d in self.decisions if d.counter_authority_status == CounterAuthorityStatus.UNCLASSIFIED]
    
    def decision_ids(self) -> Set[str]:
        """Get set of all decision IDs."""
        return {d.decision_id for d in self.decisions}
    
    def languages(self) -> Set[str]:
        """Get set of languages in the bundle."""
        return {d.language for d in self.decisions}
    
    def courts(self) -> Set[str]:
        """Get set of courts in the bundle."""
        return {d.court for d in self.decisions}


def create_bundle_from_opencaselaw_results(
    query: str,
    expanded_queries: Dict[str, List[str]],
    search_results: List[Dict],
    provenance_base: Dict[str, Any],
) -> QueryResultBundle:
    """Factory: Create bundle from raw OpenCaseLaw search results."""
    decisions = []
    
    for idx, result in enumerate(search_results):
        # Extract provenance info
        prov = RetrievalProvenance(
            source=RetrievalSource.OPENCASELAW_SEARCH,
            query_variant=provenance_base.get("query_variant"),
            language=provenance_base.get("language"),
            relevance_score=result.get("relevance_score"),
            page=provenance_base.get("page"),
            offset=provenance_base.get("offset"),
            expansion_type=provenance_base.get("expansion_type"),
        )
        
        entry = DecisionBundleEntry(
            decision_id=result.get("decision_id", ""),
            canonical_url=result.get("canonical_url", ""),
            citation_string_de=result.get("citation_string_de", ""),
            citation_string_fr=result.get("citation_string_fr", ""),
            citation_string_it=result.get("citation_string_it", ""),
            court=result.get("court", ""),
            court_level=result.get("court_level"),
            canton=result.get("canton"),
            chamber=result.get("chamber"),
            docket_number=result.get("docket_number"),
            decision_date=result.get("decision_date"),
            language=result.get("language", "de"),
            legal_area=result.get("legal_area"),
            title=result.get("title"),
            regeste=result.get("regeste") or result.get("rule_statement"),
            snippet=result.get("snippet"),
            provenance=[prov],
            retrieval_score=result.get("relevance_score", 0.0) or (1.0 - idx * 0.01),
        )
        decisions.append(entry)
    
    bundle = QueryResultBundle(
        query=query,
        expanded_queries=expanded_queries,
        decisions=decisions,
        retrieval_metadata={
            "source": "opencaselaw",
            "total_results": len(search_results),
        },
        total_candidates_found=len(search_results),
        total_after_dedupe=len(search_results),
        multilingual_expanded=len(expanded_queries) > 1,
    )
    
    return bundle


def validate_bundle(bundle: QueryResultBundle) -> List[str]:
    """Validate a query result bundle. Returns list of errors (empty if valid)."""
    errors = []
    
    if not bundle.query:
        errors.append("query is required")
    
    if not bundle.decisions:
        errors.append("bundle must contain at least one decision")
    
    # Check for duplicate decision_ids
    seen_ids = set()
    for d in bundle.decisions:
        if d.decision_id in seen_ids:
            errors.append(f"duplicate decision_id: {d.decision_id}")
        seen_ids.add(d.decision_id)
        
        if not d.decision_id:
            errors.append("decision_id is required for all entries")
        
        if not d.canonical_url:
            errors.append(f"canonical_url required for {d.decision_id}")
        
        if not d.citation_string_de and not d.citation_string_fr and not d.citation_string_it:
            errors.append(f"at least one citation_string required for {d.decision_id}")
        
        if not d.provenance:
            errors.append(f"provenance required for {d.decision_id}")
    
    return errors