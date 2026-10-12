"""
Query Result Bundle - Normalized integration contract for downstream consumers.

This module defines the canonical query_result_bundle structure that the
frontier-query-retrieval adapter produces. The bundle is consumed by the
product layer for answer generation, counter-authority search, and map building.

Contract version: 1.0
Compatible with: QUERY_MAP_MVP.md specification
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from .client import Decision
from .retrieval import RetrievalStats


# Bundle version - increment when contract changes
BUNDLE_VERSION = "1.0"
BUNDLE_SCHEMA_VERSION = 1


@dataclass
class BundleDecision:
    """
    Decision entry in the query result bundle.
    
    Contains all fields needed for answer generation, mapping, and citation.
    """
    # Core identity (required)
    decision_id: str
    canonical_decision_id: str
    canonical_url: str
    
    # Citation strings (multilingual)
    citation_string_de: Optional[str] = None
    citation_string_fr: Optional[str] = None
    citation_string_it: Optional[str] = None
    
    # Metadata
    court: str = ""
    court_name: Optional[str] = None
    canton: Optional[str] = None
    chamber: Optional[str] = None
    docket_number: str = ""
    decision_date: str = ""
    publication_date: Optional[str] = None
    language: str = "?"
    legal_area: Optional[str] = None
    
    # Content (snippet always available, full_text lazy)
    regeste: Optional[str] = None
    rule_statement: Optional[str] = None
    full_text: Optional[str] = None
    snippet: str = ""
    
    # Retrieval provenance
    rank: int = 0
    score: Optional[float] = None
    provenance: str = "unknown"  # live, cache, fixture
    retrieval_method: str = "search"  # search, citation_expansion, leading_cases
    query_variant: Optional[str] = None
    
    # Citation graph
    statutes: List[str] = field(default_factory=list)
    citation_count: int = 0
    cited_by_count: int = 0
    
    # Map positioning (filled by downstream map builder)
    cluster_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    is_outlier: bool = False
    
    # Counter-authority status (filled by adversarial pass)
    counter_status: str = "none"  # none, cited, candidate-limiting, candidate-contrary
    counter_evidence: str = ""
    counter_markers: List[str] = field(default_factory=list)
    
    # Content hash for change detection
    content_hash: Optional[str] = None
    
    @classmethod
    def from_decision(cls, decision: Decision, rank: int = 0, snippet_max: int = 600) -> "BundleDecision":
        """Create BundleDecision from a Decision."""
        # Build snippet
        snippet = decision.get_snippet(snippet_max)
        
        # Compute content hash
        content_hash = None
        if decision.full_text:
            import hashlib
            content_hash = hashlib.sha256(decision.full_text.encode()).hexdigest()[:16]
        
        return cls(
            decision_id=decision.decision_id,
            canonical_decision_id=decision.canonical_decision_id,
            canonical_url=decision.canonical_url,
            citation_string_de=decision.citation_string_de,
            citation_string_fr=decision.citation_string_fr,
            citation_string_it=decision.citation_string_it,
            court=decision.court,
            court_name=decision.court_name,
            canton=decision.canton,
            chamber=decision.chamber,
            docket_number=decision.docket_number,
            decision_date=decision.decision_date,
            publication_date=decision.publication_date,
            language=decision.language,
            legal_area=decision.legal_area,
            regeste=decision.regeste,
            rule_statement=decision.rule_statement,
            full_text=decision.full_text,
            snippet=snippet,
            rank=rank,
            score=decision.relevance_score,
            provenance=decision.provenance,
            statutes=decision.statutes,
            citation_count=decision.citation_count,
            cited_by_count=decision.cited_by_count,
            content_hash=content_hash,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def get_citation_string(self, language: str = "de") -> str:
        """Get citation string for specified language."""
        if language == "fr" and self.citation_string_fr:
            return self.citation_string_fr
        if language == "it" and self.citation_string_it:
            return self.citation_string_it
        return self.citation_string_de or self.canonical_decision_id


@dataclass
class BundleCluster:
    """Cluster in the query result bundle."""
    cluster_id: int
    label: str
    size: int
    centroid_x: Optional[float] = None
    centroid_y: Optional[float] = None
    member_decision_ids: List[str] = field(default_factory=list)
    sample_decisions: List[Dict[str, Any]] = field(default_factory=list)
    dominant_language: Optional[str] = None
    dominant_legal_area: Optional[str] = None


@dataclass
class BundleRelation:
    """Relation/edge in the query result bundle."""
    source_id: str
    target_id: str
    relation_type: str  # citation, co_citation, shared_statute, similarity
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BundleAnswer:
    """AI answer in the query result bundle."""
    prose: str
    statements: List[Dict[str, Any]] = field(default_factory=list)
    cited_decision_ids: List[str] = field(default_factory=list)
    method: str = "extractive_tfidf"
    model: str = "none-local-extractive"
    confidence: Optional[float] = None
    uncertainties: List[str] = field(default_factory=list)
    counter_authorities_mentioned: List[str] = field(default_factory=list)


@dataclass
class BundleProvenance:
    """Provenance metadata for the bundle."""
    bundle_version: str = BUNDLE_VERSION
    schema_version: int = BUNDLE_SCHEMA_VERSION
    query: str = ""
    query_variants: List[str] = field(default_factory=list)
    retrieval: Dict[str, Any] = field(default_factory=dict)
    answer: Dict[str, Any] = field(default_factory=dict)
    counter_authority: Dict[str, Any] = field(default_factory=dict)
    map: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    adapter_version: str = "1.0.0"
    charter_version: int = 2


@dataclass
class QueryResultBundle:
    """
    Canonical query result bundle.
    
    This is the primary output of the frontier-query-retrieval adapter.
    It contains all information needed for downstream answer generation,
    counter-authority search, and map building.
    """
    query: str
    query_variants: List[str]
    decisions: List[BundleDecision]
    clusters: List[BundleCluster] = field(default_factory=list)
    relations: List[BundleRelation] = field(default_factory=list)
    answer: Optional[BundleAnswer] = None
    provenance: BundleProvenance = field(default_factory=BundleProvenance)
    
    def __post_init__(self):
        if self.provenance.query == "":
            self.provenance.query = self.query
        if not self.provenance.query_variants:
            self.provenance.query_variants = self.query_variants
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "bundle_version": BUNDLE_VERSION,
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "query": self.query,
            "query_variants": self.query_variants,
            "decisions": [d.to_dict() for d in self.decisions],
            "clusters": [asdict(c) for c in self.clusters],
            "relations": [asdict(r) for r in self.relations],
            "answer": asdict(self.answer) if self.answer else None,
            "provenance": asdict(self.provenance),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResultBundle":
        """Deserialize from dictionary."""
        decisions = [BundleDecision(**d) for d in data.get("decisions", [])]
        clusters = [BundleCluster(**c) for c in data.get("clusters", [])]
        relations = [BundleRelation(**r) for r in data.get("relations", [])]
        answer = BundleAnswer(**data["answer"]) if data.get("answer") else None
        provenance = BundleProvenance(**data.get("provenance", {}))
        
        return cls(
            query=data["query"],
            query_variants=data.get("query_variants", []),
            decisions=decisions,
            clusters=clusters,
            relations=relations,
            answer=answer,
            provenance=provenance,
        )
    
    def get_decision(self, decision_id: str) -> Optional[BundleDecision]:
        """Get a decision by ID."""
        for d in self.decisions:
            if d.decision_id == decision_id or d.canonical_decision_id == decision_id:
                return d
        return None
    
    def get_decisions_by_language(self, language: str) -> List[BundleDecision]:
        """Get decisions filtered by language."""
        return [d for d in self.decisions if d.language == language]
    
    def get_decisions_by_cluster(self, cluster_id: int) -> List[BundleDecision]:
        """Get decisions in a specific cluster."""
        return [d for d in self.decisions if d.cluster_id == cluster_id]
    
    def get_cited_decisions(self) -> List[BundleDecision]:
        """Get decisions cited in the answer."""
        if not self.answer:
            return []
        cited_ids = set(self.answer.cited_decision_ids)
        return [d for d in self.decisions if d.decision_id in cited_ids]
    
    def get_counter_authorities(self) -> List[BundleDecision]:
        """Get decisions flagged as counter-authorities."""
        return [d for d in self.decisions if d.counter_status != "none"]
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the bundle."""
        langs: Dict[str, int] = {}
        for d in self.decisions:
            langs[d.language] = langs.get(d.language, 0) + 1
        
        counter_count = sum(1 for d in self.decisions if d.counter_status != "none")
        
        return {
            "bundle_id": self.provenance.bundle_id,
            "query": self.query,
            "n_decisions": len(self.decisions),
            "n_clusters": len(self.clusters),
            "n_relations": len(self.relations),
            "n_cited": len(self.answer.cited_decision_ids) if self.answer else 0,
            "n_counter": counter_count,
            "languages": langs,
            "provenance_breakdown": self.provenance.retrieval.get("provenance_breakdown", {}),
            "retrieval_duration": self.provenance.retrieval.get("duration_seconds", 0),
        }


# Validation functions

REQUIRED_TOP_KEYS = [
    "bundle_version", "schema_version", "query", "query_variants",
    "decisions", "clusters", "relations", "answer", "provenance"
]

REQUIRED_DECISION_KEYS = [
    "decision_id", "canonical_decision_id", "canonical_url",
    "court", "docket_number", "decision_date", "language",
    "rank", "provenance", "snippet", "cluster_id", "x", "y",
    "counter_status", "counter_evidence", "counter_markers"
]


def validate_bundle(bundle: Dict[str, Any]) -> List[str]:
    """
    Validate a query result bundle.
    
    Returns list of validation errors (empty = valid).
    """
    errors = []
    
    # Check top-level keys
    for key in REQUIRED_TOP_KEYS:
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    
    if errors:
        return errors
    
    # Check decisions
    decisions = bundle.get("decisions", [])
    if not isinstance(decisions, list):
        errors.append("decisions must be a list")
        return errors
    
    if not decisions:
        errors.append("decisions must be non-empty")
        return errors
    
    seen_ids = set()
    for i, d in enumerate(decisions):
        for key in REQUIRED_DECISION_KEYS:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        
        did = d.get("decision_id") or d.get("canonical_decision_id")
        if did in seen_ids:
            errors.append(f"duplicate decision_id: {did}")
        seen_ids.add(did)
    
    # Check answer citations exist in decisions
    if bundle.get("answer"):
        cited = set(bundle["answer"].get("cited_decision_ids", []))
        unknown = cited - seen_ids
        if unknown:
            errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
    
    # Check clusters
    for i, c in enumerate(bundle.get("clusters", [])):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster[{i}] missing id/label")
    
    return errors


def validate_bundle_object(bundle: QueryResultBundle) -> List[str]:
    """Validate a QueryResultBundle object."""
    return validate_bundle(bundle.to_dict())


# Builder functions

def build_bundle_from_retrieval(
    query: str,
    query_variants: List[str],
    decisions: List[Decision],
    retrieval_stats: RetrievalStats,
    max_decisions: int = 300,
) -> QueryResultBundle:
    """
    Build a QueryResultBundle from retrieval results.
    
    This is the main entry point for creating a bundle from the retrieval adapter.
    Downstream components (answer generation, clustering, counter-authority)
    will enrich this bundle further.
    """
    # Limit decisions
    decisions = decisions[:max_decisions]
    
    # Convert to bundle decisions
    bundle_decisions = []
    for i, d in enumerate(decisions):
        bd = BundleDecision.from_decision(d, rank=i + 1)
        bd.retrieval_method = getattr(d, "_retrieval_method", "search")
        bd.query_variant = getattr(d, "_query_variant", None)
        bundle_decisions.append(bd)
    
    # Build provenance
    provenance = BundleProvenance(
        query=query,
        query_variants=query_variants,
        retrieval={
            "total_api_calls": retrieval_stats.total_api_calls,
            "cache_hits": retrieval_stats.cache_hits,
            "decisions_fetched": retrieval_stats.decisions_fetched,
            "decisions_after_dedupe": retrieval_stats.decisions_after_dedupe,
            "citation_expansions": retrieval_stats.citation_expansions,
            "leading_cases_added": retrieval_stats.leading_cases_added,
            "full_text_fetched": retrieval_stats.full_text_fetched,
            "errors": retrieval_stats.errors,
            "duration_seconds": retrieval_stats.duration_seconds,
            "provenance_breakdown": retrieval_stats.provenance_breakdown,
            "query_variants_used": retrieval_stats.query_variants_used,
        },
    )
    
    return QueryResultBundle(
        query=query,
        query_variants=query_variants,
        decisions=bundle_decisions,
        clusters=[],  # Filled by map builder
        relations=[],  # Filled by map builder
        answer=None,  # Filled by answer generator
        provenance=provenance,
    )


def enrich_bundle_with_answer(bundle: QueryResultBundle, answer: BundleAnswer) -> QueryResultBundle:
    """Enrich bundle with AI answer."""
    bundle.answer = answer
    bundle.provenance.answer = {
        "method": answer.method,
        "model": answer.model,
        "n_citations": len(answer.cited_decision_ids),
        "n_statements": len(answer.statements),
    }
    return bundle


def enrich_bundle_with_counter_authority(
    bundle: QueryResultBundle,
    counter_decisions: List[BundleDecision],
    counter_info: Dict[str, Any],
) -> QueryResultBundle:
    """Enrich bundle with counter-authority results."""
    # Merge counter decisions into bundle (deduplicate by ID)
    existing_ids = {d.decision_id for d in bundle.decisions}
    for cd in counter_decisions:
        if cd.decision_id not in existing_ids:
            bundle.decisions.append(cd)
            existing_ids.add(cd.decision_id)
    
    # Update counter status on existing decisions
    for cd in counter_decisions:
        bd = bundle.get_decision(cd.decision_id)
        if bd:
            bd.counter_status = cd.counter_status
            bd.counter_evidence = cd.counter_evidence
            bd.counter_markers = cd.counter_markers
    
    bundle.provenance.counter_authority = counter_info
    return bundle


def enrich_bundle_with_map(
    bundle: QueryResultBundle,
    clusters: List[BundleCluster],
    relations: List[BundleRelation],
    map_info: Dict[str, Any],
) -> QueryResultBundle:
    """Enrich bundle with map data (clusters, positions, relations)."""
    bundle.clusters = clusters
    bundle.relations = relations
    bundle.provenance.map = map_info
    
    # Update decision cluster/position info
    cluster_map = {c.cluster_id: c for c in clusters}
    for decision in bundle.decisions:
        if decision.cluster_id is not None and decision.cluster_id in cluster_map:
            cluster = cluster_map[decision.cluster_id]
            if decision.x is None:
                decision.x = cluster.centroid_x
            if decision.y is None:
                decision.y = cluster.centroid_y
    
    return bundle