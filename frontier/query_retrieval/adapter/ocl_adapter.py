"""OpenCaseLaw Retrieval Adapter.

Production-ready adapter for OpenCaseLaw public REST API with:
- Multilingual query expansion (DE/FR/IT)
- Pagination support for 100-300 decision bundles
- Deterministic deduplication by decision_id
- Lazy full-text/structure retrieval
- Citation-neighborhood expansion (incoming/outgoing/leading-cases)
- File-based caching with TTL
- Rate limiting (<=5 req/s)
- Graceful degradation for remote failures
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
from threading import Lock
from collections import OrderedDict

# ──────────────────────────────────────────────────────────────────────
# Configuration & Data Classes
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OCLConfig:
    """Configuration for OpenCaseLaw adapter."""
    base_url: str = "https://mcp.opencaselaw.ch/api/decisions"
    rate_limit_rps: float = 5.0  # Soft limit per documented spec
    request_timeout: int = 15
    cache_ttl_seconds: int = 86400  # 24 hours
    cache_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "cache")
    fixture_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "fixtures")
    max_total_results: int = 300
    default_page_size: int = 50
    user_agent: str = "LexMachina-Frontier/1.0"


@dataclass(frozen=True)
class SearchRequest:
    """Search request parameters."""
    query: str
    languages: tuple[str, ...] = ("de", "fr", "it")  # Search across all three
    limit: int = 100
    offset: int = 0
    include_full_text: bool = False


@dataclass(frozen=True)
class Decision:
    """Normalized decision record with provenance."""
    decision_id: str
    court: str
    canton: Optional[str]
    chamber: Optional[str]
    docket_number: str
    decision_date: str
    publication_date: Optional[str]
    language: str
    title: str
    regeste: Optional[str]
    abstract_de: Optional[str]
    abstract_fr: Optional[str]
    abstract_it: Optional[str]
    full_text: str
    canonical_url: str
    source_url: Optional[str]
    pdf_url: Optional[str]
    citation_string_de: str
    citation_string_fr: str
    citation_string_it: str
    rule_statement: Optional[str]
    cited_decisions: list[str] = field(default_factory=list)
    statutes: list[str] = field(default_factory=list)
    provenance: str = "ocl:search"
    retrieved_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_bundle_format(self) -> dict[str, Any]:
        """Convert to query_result_bundle decision format."""
        # Build snippet from regeste or full_text
        snippet_source = self.regeste or self.full_text or ""
        snippet = " ".join(snippet_source.split())[:600]
        
        # Use the appropriate citation string for the decision's language
        citation_map = {
            "de": self.citation_string_de,
            "fr": self.citation_string_fr,
            "it": self.citation_string_it,
        }
        citation = citation_map.get(self.language, self.citation_string_de)
        
        return {
            "decision_id": self.decision_id,
            "court": self.court,
            "language": self.language,
            "decision_date": self.decision_date,
            "docket_number": self.docket_number,
            "provenance": self.provenance,
            "snippet": snippet,
            "canonical_url": self.canonical_url,
            "citation": citation,
            "title": self.title,
            "regeste": self.regeste,
            "full_text": self.full_text,
            "cited_decisions": self.cited_decisions,
            "statutes": self.statutes,
            "retrieved_at": self.retrieved_at,
        }


@dataclass(frozen=True)
class SearchResult:
    """Search result with metadata."""
    decisions: list[Decision]
    total: int
    returned: int
    offset: int
    has_more: bool
    provenance: str
    query: str
    languages: tuple[str, ...]
    latency_ms: float


@dataclass(frozen=True)
class CitationNeighborhood:
    """Citation neighborhood expansion result."""
    decision_id: str
    outgoing_citations: list[Decision]  # Decisions this decision cites
    incoming_citations: list[Decision]  # Decisions that cite this decision
    leading_cases: list[Decision]       # Leading cases related to this decision
    provenance: str
    bounds: dict[str, int]  # Limits applied


# ──────────────────────────────────────────────────────────────────────
# Multilingual Query Expansion
# ──────────────────────────────────────────────────────────────────────

# Swiss legal term expansion across DE/FR/IT (extends product's EXPANSION)
MULTILINGUAL_EXPANSION = {
    # Core legal domains
    "miete": ["mietrecht", "loyer", "bail", "locazione", "affitto", "mietvertrag", "mietzins", "rent", "mietzinserhöhung"],
    "mietrecht": ["miete", "loyer", "bail", "locazione", "mietvertrag", "mietzins", "kündigung", "congé"],
    "loyer": ["miete", "mietrecht", "bail", "locazione", "mietvertrag", "augmentation", "congé"],
    "bail": ["miete", "mietrecht", "loyer", "locazione", "affitto", "disdetta"],
    "locazione": ["miete", "mietrecht", "loyer", "bail", "affitto", "canone"],
    
    "arbeit": ["arbeitsrecht", "travail", "emploi", "lavoro", "kündigung", "licenciement", "dismissal", "congé", "disdetta"],
    "arbeitsrecht": ["arbeit", "droit du travail", "diritto del lavoro", "kündigungsschutz"],
    "kündigung": ["arbeit", "licenciement", "dismissal", "congé", "disdetta", "entlassung", "résiliation"],
    "licenciement": ["kündigung", "arbeit", "dismissal", "congé", "disdetta", "renvoi"],
    "congé": ["kündigung", "licenziamento", "arbeit", "licenciement", "preavviso"],
    
    "strafe": ["strafrecht", "peine", "pénal", "pena", "penale", "sanction", "strafe", "condanna"],
    "strafrecht": ["strafe", "droit pénal", "diritto penale", "strafgesetzbuch", "code pénal", "codice penale"],
    "pénal": ["strafe", "strafrecht", "pena", "penale", "penal"],
    
    "asyl": ["asile", "asilo", "migration", "flüchtling", "réfugié", "rifugiato", "asylum", "protezione"],
    "asile": ["asyl", "asilo", "migration", "asylum", "protezione"],
    "flüchtling": ["réfugié", "rifugiato", "asyl", "asile", "refugee"],
    
    "sozialversicherung": ["assurance", "sociale", "assicurazione", "invalidität", "invalidité", "invalidità", "ahv", "avs", "iv", "ai"],
    "invalidität": ["invalidité", "invalidità", "sozialversicherung", "assurance", "invalidity", "invalidità"],
    "ahv": ["avs", "altersrente", "rente vieillesse", "rendita vecchiaia"],
    "iv": ["ai", "invalidenversicherung", "assurance invalidité", "assicurazione invalidità"],
    
    "steuer": ["impôt", "fiscal", "imposta", "tax", "steuerrecht", "droit fiscal", "diritto fiscale", "steuerpflicht"],
    "impôt": ["steuer", "steuerrecht", "imposta", "tax", "fiscal"],
    
    "familie": ["famille", "famiglia", "scheidung", "divorce", "divorzio", "ehe", "mariage", "matrimonio"],
    "scheidung": ["divorce", "divorzio", "familie", "ehe", "trennung", "séparation"],
    "divorce": ["scheidung", "divorzio", "famille", "famiglia", "séparation"],
    
    "vertrag": ["contrat", "contratto", "obligation", "obbligazione", "schuld", "accordo", "convention"],
    "haftung": ["responsabilité", "responsabilità", "liability", "schadenersatz", "dommages", "danni", "risarcimento"],
    "eigentum": ["propriété", "proprietà", "property", "besitz", "possession", "possesso"],
    
    "umwelt": ["environnement", "ambiente", "environment", "umweltrecht", "droit de l'environnement"],
    "datenschutz": ["protection des données", "protezione dei dati", "data protection", "privacy", "schutz personenbezogener daten"],
    
    # Procedural
    "beschwerde": ["recours", "ricorso", "appeal", "reclamazione", "réclamation"],
    "revision": ["révision", "revisione", "überprüfung"],
    "vorsorge": ["mesure provisionnelle", "misura cautelare", "provisional measure"],
    
    # Courts
    "bundesgericht": ["tribunal fédéral", "tribunale federale", "bger", "tf", "bge"],
    "bger": ["bundesgericht", "tribunal fédéral", "tribunale federale"],
    "bvger": ["bverwaltungsgericht", "tribunal administratif fédéral", "taf", "tribunale amministrativo federale"],
    "bpatg": ["bpatentgericht", "tribunal fédéral des brevets", "tribunale federale dei brevetti"],
    
    # Common legal concepts
    "rechtsmissbrauch": ["abus de droit", "abuso del diritto", "abuse of right"],
    "treu und glauben": ["bonne foi", "buona fede", "good faith"],
    "verhältnismässigkeit": ["proportionnalité", "proporzionalità", "proportionality"],
    "gleichbehandlung": ["égalité de traitement", "parità di trattamento", "equal treatment"],
    "willkür": ["arbitraire", "arbitrio", "arbitrariness"],
}

TOKEN_RE = None  # Lazy compile


def _get_token_re():
    global TOKEN_RE
    if TOKEN_RE is None:
        import re
        TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
    return TOKEN_RE


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase terms > 1 char."""
    return [t.lower() for t in _get_token_re().findall(text or "") if len(t) > 1]


def expand_query_multilingual(query: str, max_expansion_terms: int = 12) -> list[str]:
    """Expand a query with multilingual synonyms.
    
    Returns list of query variants: [original, expanded_variant, ...]
    Each variant preserves provenance for debugging.
    """
    toks = tokenize(query)
    extra: list[str] = []
    seen = set(toks)
    
    for t in toks:
        for syn in MULTILINGUAL_EXPANSION.get(t, []):
            if syn not in seen and len(extra) < max_expansion_terms:
                extra.append(syn)
                seen.add(syn)
    
    variants = [query]
    if extra:
        variants.append(query + " " + " ".join(extra))
    
    # Per-language focused variants (original + top terms for that language)
    # This helps when searching with language filter
    lang_terms = {"de": [], "fr": [], "it": []}
    for syn in extra:
        # Heuristic: terms ending in typical DE/FR/IT patterns
        if syn.endswith(("en", "er", "ung", "heit", "keit", "schaft", "recht", "gesetz", "buch")):
            lang_terms["de"].append(syn)
        elif syn.endswith(("ion", "té", "eur", "eau", "ois", "ait", "ment", "ance", "ence")):
            lang_terms["fr"].append(syn)
        elif syn.endswith(("zione", "tà", "ore", "are", "ere", "ire", "mento", "enza")):
            lang_terms["it"].append(syn)
    
    for lang, terms in lang_terms.items():
        if terms:
            variants.append(query + " " + " ".join(terms[:6]))
    
    return variants


# ──────────────────────────────────────────────────────────────────────
# Rate Limiter
# ──────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, rate_limit_rps: float):
        self.rate_limit_rps = rate_limit_rps
        self.min_interval = 1.0 / rate_limit_rps if rate_limit_rps > 0 else 0
        self.last_call = 0.0
        self._lock = Lock()
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.time()


# ──────────────────────────────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────────────────────────────

class FileCache:
    """File-based cache with TTL and LRU eviction."""
    
    def __init__(self, cache_dir: Path, ttl_seconds: int, max_entries: int = 10000):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._index_path = cache_dir / "_index.json"
        self._index: dict[str, dict] = self._load_index()
    
    def _load_index(self) -> dict:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}
    
    def _save_index(self) -> None:
        try:
            # LRU eviction if over limit
            if len(self._index) > self.max_entries:
                # Sort by last_access, keep most recent
                sorted_items = sorted(
                    self._index.items(), 
                    key=lambda x: x[1].get("last_access", 0), 
                    reverse=True
                )
                self._index = dict(sorted_items[:self.max_entries])
            self._index_path.write_text(
                json.dumps(self._index, ensure_ascii=False), 
                encoding="utf-8"
            )
        except Exception:
            pass
    
    def _make_key(self, prefix: str, *parts: str) -> str:
        raw = "|".join(parts)
        return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
    
    def get(self, prefix: str, *parts: str) -> Optional[Any]:
        key = self._make_key(prefix, *parts)
        path = self.cache_dir / f"{key}.json"
        
        with self._lock:
            if key not in self._index:
                return None
            
            entry = self._index[key]
            if time.time() - entry["cached_at"] > self.ttl_seconds:
                # Expired
                path.unlink(missing_ok=True)
                del self._index[key]
                self._save_index()
                return None
            
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entry["last_access"] = time.time()
                self._save_index()
                return data
            except Exception:
                path.unlink(missing_ok=True)
                del self._index[key]
                self._save_index()
                return None
    
    def set(self, prefix: str, data: Any, *parts: str) -> None:
        key = self._make_key(prefix, *parts)
        path = self.cache_dir / f"{key}.json"
        
        with self._lock:
            try:
                path.write_text(
                    json.dumps(data, ensure_ascii=False), 
                    encoding="utf-8"
                )
                self._index[key] = {
                    "cached_at": time.time(),
                    "last_access": time.time(),
                }
                self._save_index()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────
# OpenCaseLaw Adapter
# ──────────────────────────────────────────────────────────────────────

class OpenCaseLawAdapter:
    """Main adapter for OpenCaseLaw public REST API."""
    
    def __init__(self, config: Optional[OCLConfig] = None):
        self.config = config or OCLConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_rps)
        self.cache = FileCache(
            self.config.cache_dir, 
            self.config.cache_ttl_seconds
        )
        self._session_stats = {
            "requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "rate_limited_waits": 0,
        }
    
    def _make_request(self, url: str) -> Optional[dict]:
        """Make HTTP request with rate limiting and error handling."""
        self.rate_limiter.wait()
        self._session_stats["requests"] += 1
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.config.request_timeout) as resp:
                if resp.status == 200:
                    payload = resp.read(5_000_000).decode("utf-8", "replace")
                    return json.loads(payload)
                else:
                    self._session_stats["errors"] += 1
                    return None
        except Exception as e:
            self._session_stats["errors"] += 1
            return None
    
    def _parse_decision(self, item: dict, provenance: str) -> Optional[Decision]:
        """Parse API response item into Decision object."""
        try:
            decision_id = str(item.get("decision_id") or item.get("canonical_decision_id") or item.get("id") or "")
            if not decision_id or decision_id == "?":
                return None
            
            return Decision(
                decision_id=decision_id,
                court=str(item.get("court", "?")),
                canton=item.get("canton"),
                chamber=item.get("chamber"),
                docket_number=str(item.get("docket_number", "")),
                decision_date=str(item.get("decision_date", "")),
                publication_date=item.get("publication_date"),
                language=str(item.get("language", "?")),
                title=str(item.get("title", "")),
                regeste=item.get("regeste"),
                abstract_de=item.get("abstract_de"),
                abstract_fr=item.get("abstract_fr"),
                abstract_it=item.get("abstract_it"),
                full_text=str(item.get("full_text", "")),
                canonical_url=str(item.get("canonical_url", "")),
                source_url=item.get("source_url"),
                pdf_url=item.get("pdf_url"),
                citation_string_de=str(item.get("citation_string_de", "")),
                citation_string_fr=str(item.get("citation_string_fr", "")),
                citation_string_it=str(item.get("citation_string_it", "")),
                rule_statement=item.get("rule_statement"),
                cited_decisions=item.get("cited_decisions", []) or [],
                statutes=item.get("statutes", []) or [],
                provenance=provenance,
            )
        except Exception:
            return None
    
    def search(self, request: SearchRequest, use_cache: bool = True) -> SearchResult:
        """Execute search with multilingual expansion and pagination."""
        t0 = time.time()
        
        # Build search URLs for each language variant
        all_decisions: list[Decision] = []
        seen_ids: set[str] = set()
        total = 0
        has_more = False
        provenance_parts = []
        
        variants = expand_query_multilingual(request.query)
        
        for lang in request.languages:
            for variant_idx, variant in enumerate(variants):
                if len(all_decisions) >= request.limit:
                    break
                
                # Calculate remaining needed
                remaining = request.limit - len(all_decisions)
                page_size = min(self.config.default_page_size, remaining)
                
                # Build URL with search, language, limit, offset
                params = {
                    "search": variant,
                    "language": lang,
                    "limit": page_size,
                    "offset": request.offset,
                }
                url = self.config.base_url + "?" + urllib.parse.urlencode(params)
                
                # Check cache
                cache_key = f"search|{variant}|{lang}|{page_size}|{request.offset}"
                cached = self.cache.get("ocl", cache_key) if use_cache else None
                
                if cached is not None:
                    self._session_stats["cache_hits"] += 1
                    data = cached
                    provenance_parts.append(f"cache:{lang}:v{variant_idx}")
                else:
                    self._session_stats["cache_misses"] += 1
                    data = self._make_request(url)
                    if data:
                        self.cache.set("ocl", data, cache_key)
                        provenance_parts.append(f"live:{lang}:v{variant_idx}")
                    else:
                        provenance_parts.append(f"failed:{lang}:v{variant_idx}")
                        continue
                
                if not data:
                    continue
                
                # Track total from first successful response
                if total == 0:
                    total = data.get("total", 0)
                
                items = data.get("results", [])
                for item in items:
                    decision = self._parse_decision(item, f"search:{lang}:v{variant_idx}")
                    if decision and decision.decision_id not in seen_ids:
                        seen_ids.add(decision.decision_id)
                        all_decisions.append(decision)
                        if len(all_decisions) >= request.limit:
                            break
                
                has_more = data.get("has_more", False)
                if not has_more or len(items) < page_size:
                    break
        
        latency_ms = (time.time() - t0) * 1000
        
        return SearchResult(
            decisions=all_decisions[:request.limit],
            total=total,
            returned=len(all_decisions),
            offset=request.offset,
            has_more=has_more and len(all_decisions) < request.limit,
            provenance=";".join(provenance_parts) if provenance_parts else "no_results",
            query=request.query,
            languages=request.languages,
            latency_ms=latency_ms,
        )
    
    def search_paginated(self, query: str, target_count: int = 100, 
                         languages: tuple[str, ...] = ("de", "fr", "it"),
                         use_cache: bool = True) -> list[Decision]:
        """Search with automatic pagination to reach target_count."""
        all_decisions: list[Decision] = []
        offset = 0
        page_size = self.config.default_page_size
        
        while len(all_decisions) < target_count and offset < self.config.max_total_results:
            remaining = min(page_size, target_count - len(all_decisions))
            request = SearchRequest(
                query=query,
                languages=languages,
                limit=remaining,
                offset=offset,
            )
            result = self.search(request, use_cache=use_cache)
            
            if not result.decisions:
                break
            
            all_decisions.extend(result.decisions)
            
            if not result.has_more or len(result.decisions) < remaining:
                break
            
            offset += page_size
        
        return all_decisions[:target_count]
    
    def fetch_decision(self, decision_id: str, use_cache: bool = True) -> Optional[Decision]:
        """Fetch full decision by ID (lazy full-text retrieval)."""
        cache_key = f"decision|{decision_id}"
        
        if use_cache:
            cached = self.cache.get("ocl", cache_key)
            if cached:
                self._session_stats["cache_hits"] += 1
                return self._parse_decision(cached, "cache:decision")
        
        self._session_stats["cache_misses"] += 1
        url = f"{self.config.base_url}/{urllib.parse.quote(decision_id)}"
        data = self._make_request(url)
        
        if data:
            self.cache.set("ocl", data, cache_key)
            return self._parse_decision(data, "live:decision")
        
        return None
    
    def fetch_citation_neighborhood(self, decision_id: str, 
                                     max_outgoing: int = 20,
                                     max_incoming: int = 20,
                                     max_leading: int = 10,
                                     use_cache: bool = True) -> CitationNeighborhood:
        """Fetch citation neighborhood for a decision.
        
        Note: OpenCaseLaw API may not expose all these endpoints.
        This implements the interface with graceful degradation.
        """
        outgoing: list[Decision] = []
        incoming: list[Decision] = []
        leading: list[Decision] = []
        provenance_parts = []
        
        # Fetch the decision first to get cited_decisions
        decision = self.fetch_decision(decision_id, use_cache=use_cache)
        
        if decision:
            # Outgoing: decisions this decision cites (from cited_decisions field)
            for cited_id in decision.cited_decisions[:max_outgoing]:
                cited = self.fetch_decision(cited_id, use_cache=use_cache)
                if cited:
                    outgoing.append(cited)
            
            provenance_parts.append("outgoing:cited_decisions")
        
        # Incoming citations: search for decisions that cite this one
        # Using search with the decision_id as query (may not be perfect)
        try:
            incoming_request = SearchRequest(
                query=f'"{decision_id}"',  # Exact phrase search
                languages=("de", "fr", "it"),
                limit=max_incoming,
            )
            incoming_result = self.search(incoming_request, use_cache=use_cache)
            incoming = incoming_result.decisions
            provenance_parts.append(f"incoming:search:{incoming_result.provenance}")
        except Exception:
            provenance_parts.append("incoming:failed")
        
        # Leading cases: search for decisions referencing this as leading
        # This is a best-effort approximation
        try:
            if decision:
                leading_request = SearchRequest(
                    query=f"leading case {decision.title[:50]}",
                    languages=("de", "fr", "it"),
                    limit=max_leading,
                )
                leading_result = self.search(leading_request, use_cache=use_cache)
                leading = leading_result.decisions
                provenance_parts.append(f"leading:search:{leading_result.provenance}")
        except Exception:
            provenance_parts.append("leading:failed")
        
        return CitationNeighborhood(
            decision_id=decision_id,
            outgoing_citations=outgoing,
            incoming_citations=incoming,
            leading_cases=leading,
            provenance=";".join(provenance_parts),
            bounds={
                "max_outgoing": max_outgoing,
                "max_incoming": max_incoming,
                "max_leading": max_leading,
            },
        )
    
    def get_stats(self) -> dict:
        """Return session statistics."""
        return dict(self._session_stats)


# ──────────────────────────────────────────────────────────────────────
# Query Bundle Builder (compatible with product's query_result_bundle)
# ──────────────────────────────────────────────────────────────────────

def build_query_bundle(query: str, 
                       target_count: int = 100,
                       languages: tuple[str, ...] = ("de", "fr", "it"),
                       include_citation_expansion: bool = False,
                       max_citation_expansion: int = 10,
                       use_cache: bool = True,
                       config: Optional[OCLConfig] = None) -> dict[str, Any]:
    """Build a query_result_bundle from OpenCaseLaw search.
    
    This is the main integration point for the product lane.
    Returns a bundle compatible with product/query/bundle.py validation.
    """
    adapter = OpenCaseLawAdapter(config)
    
    # Get multilingual query variants for provenance
    variants = expand_query_multilingual(query)
    
    # Broad search with pagination
    decisions = adapter.search_paginated(
        query=query,
        target_count=target_count,
        languages=languages,
        use_cache=use_cache,
    )
    
    # Deduplicate by decision_id (deterministic)
    seen = set()
    unique_decisions = []
    for d in decisions:
        if d.decision_id not in seen:
            seen.add(d.decision_id)
            unique_decisions.append(d)
    
    # Convert to bundle format
    bundle_decisions = []
    for rank, decision in enumerate(unique_decisions):
        d = decision.to_bundle_format()
        d["rank"] = rank + 1
        d["score"] = 1.0 - (rank / max(len(unique_decisions), 1))  # Simple rank-based score
        d["cluster_id"] = -1  # Will be filled by downstream map builder
        d["x"] = 0.0
        d["y"] = 0.0
        d["is_outlier"] = False
        d["counter_status"] = "none"
        d["counter_evidence"] = ""
        d["counter_markers"] = []
        bundle_decisions.append(d)
    
    # Citation neighborhood expansion (optional, bounded)
    citation_provenance = {}
    if include_citation_expansion and bundle_decisions:
        # Expand for top N decisions
        for d in bundle_decisions[:max_citation_expansion]:
            neighborhood = adapter.fetch_citation_neighborhood(
                d["decision_id"],
                max_outgoing=5,
                max_incoming=5,
                max_leading=3,
                use_cache=use_cache,
            )
            citation_provenance[d["decision_id"]] = neighborhood.provenance
            
            # Add neighborhood decisions to bundle (with provenance marking)
            for nd in neighborhood.outgoing_citations + neighborhood.incoming_citations + neighborhood.leading_cases:
                if nd.decision_id not in seen:
                    seen.add(nd.decision_id)
                    nd_bundle = nd.to_bundle_format()
                    nd_bundle["rank"] = len(bundle_decisions) + 1
                    nd_bundle["score"] = 0.1  # Lower score for expansion
                    nd_bundle["cluster_id"] = -1
                    nd_bundle["x"] = 0.0
                    nd_bundle["y"] = 0.0
                    nd_bundle["is_outlier"] = True
                    nd_bundle["counter_status"] = "none"
                    nd_bundle["counter_evidence"] = ""
                    nd_bundle["counter_markers"] = []
                    nd_bundle["provenance"] = f"citation_expansion:{neighborhood.provenance}"
                    bundle_decisions.append(nd_bundle)
    
    # Build minimal bundle structure (compatible with product/query/bundle.py)
    bundle = {
        "bundle_version": "1.0",
        "query": query,
        "query_variants": variants,
        "answer": {
            "text": "",
            "cited_decision_ids": [],
            "method": "ocl_retrieval_only",
            "confidence": 0.0,
        },
        "decisions": bundle_decisions,
        "clusters": [],
        "relations": [],
        "provenance": {
            "adapter": "OpenCaseLawAdapter",
            "adapter_version": "1.0",
            "search_provenance": "paginated_multilingual",
            "decisions_retrieved": len(bundle_decisions),
            "unique_decisions": len(seen),
            "languages_searched": list(languages),
            "citation_expansion": citation_provenance if include_citation_expansion else {},
            "session_stats": adapter.get_stats(),
            "latency_seconds": 0.0,  # Filled by caller
        },
    }
    
    return bundle


# ──────────────────────────────────────────────────────────────────────
# Fixture Support (for deterministic offline tests)
# ──────────────────────────────────────────────────────────────────────

def load_fixture_decisions(fixture_path: Path) -> list[Decision]:
    """Load decisions from JSONL fixture file."""
    decisions = []
    with open(fixture_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            decisions.append(Decision(
                decision_id=r.get("decision_id", ""),
                court=r.get("court", "?"),
                canton=r.get("canton"),
                chamber=r.get("chamber"),
                docket_number=r.get("docket_number", ""),
                decision_date=r.get("decision_date", ""),
                publication_date=r.get("publication_date"),
                language=r.get("language", "?"),
                title=r.get("title", ""),
                regeste=r.get("regeste"),
                abstract_de=r.get("abstract_de"),
                abstract_fr=r.get("abstract_fr"),
                abstract_it=r.get("abstract_it"),
                full_text=r.get("full_text", ""),
                canonical_url=r.get("canonical_url", ""),
                source_url=r.get("source_url"),
                pdf_url=r.get("pdf_url"),
                citation_string_de=r.get("citation_string_de", ""),
                citation_string_fr=r.get("citation_string_fr", ""),
                citation_string_it=r.get("citation_string_it", ""),
                rule_statement=r.get("rule_statement"),
                cited_decisions=r.get("cited_decisions", []),
                statutes=r.get("statutes", []),
                provenance="fixture",
            ))
    return decisions