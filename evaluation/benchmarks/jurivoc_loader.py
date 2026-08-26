"""
Jurivoc/TF Weak-Supervision Benchmark Loader

Loads and processes Jurivoc thesaurus and Swiss Federal Supreme Court metadata
for use as imperfect human supervision in evaluation.

Jurivoc: https://www.bger.ch/ext/jurivoc/live/de/jurivoc/Jurivoc.jsp
Swiss Federal Supreme Court Dataset (SCD): https://zenodo.org/records/11092977
OpenCaseLaw: https://opencaselaw.ch/api/
"""

import json
import requests
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class JurivocConcept:
    """A concept in the Jurivoc thesaurus."""
    uri: str
    pref_label_de: str
    pref_label_fr: str
    pref_label_it: Optional[str] = None
    broader: Optional[str] = None
    narrower: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    scope_note: Optional[str] = None
    notation: Optional[str] = None


@dataclass
class TFDecisionMetadata:
    """Metadata for a Swiss Federal Supreme Court decision."""
    decision_id: str
    docket_number: str
    date: str
    language: str
    court: str
    chamber: Optional[str] = None
    legal_area: Optional[str] = None
    jurivoc_descriptors: List[str] = field(default_factory=list)
    cited_decisions: List[str] = field(default_factory=list)
    citing_decisions: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    parties: List[str] = field(default_factory=list)
    norms: List[str] = field(default_factory=list)


class JurivocLoader:
    """Loads and parses the Jurivoc thesaurus."""

    JURIVOC_BASE_URL = "https://www.bger.ch/ext/jurivoc/live/de/jurivoc"
    JURIVOC_SPARQL_ENDPOINT = "https://www.bger.ch/ext/jurivoc/sparql"

    def __init__(self, cache_dir: str = "evaluation/data/jurivoc"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.concepts: Dict[str, JurivocConcept] = {}
        self.hierarchy: Dict[str, List[str]] = {}  # broader -> [narrower]

    def load_from_cache(self) -> bool:
        """Load Jurivoc from local cache."""
        cache_file = self.cache_dir / "jurivoc_concepts.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                data = json.load(f)
            for concept_data in data:
                concept = JurivocConcept(**concept_data)
                self.concepts[concept.uri] = concept
                if concept.broader:
                    self.hierarchy.setdefault(concept.broader, []).append(concept.uri)
            logger.info(f"Loaded {len(self.concepts)} Jurivoc concepts from cache")
            return True
        return False

    def fetch_from_sparql(self) -> bool:
        """Fetch Jurivoc concepts via SPARQL endpoint."""
        query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX jurivoc: <http://www.bger.ch/jurivoc/>

        SELECT ?uri ?prefLabel_de ?prefLabel_fr ?prefLabel_it ?broader ?narrower ?related ?scopeNote ?notation
        WHERE {
            ?uri a skos:Concept .
            ?uri skos:prefLabel ?prefLabel_de .
            FILTER(LANG(?prefLabel_de) = 'de')
            OPTIONAL { ?uri skos:prefLabel ?prefLabel_fr . FILTER(LANG(?prefLabel_fr) = 'fr') }
            OPTIONAL { ?uri skos:prefLabel ?prefLabel_it . FILTER(LANG(?prefLabel_it) = 'it') }
            OPTIONAL { ?uri skos:broader ?broader . }
            OPTIONAL { ?uri skos:narrower ?narrower . }
            OPTIONAL { ?uri skos:related ?related . }
            OPTIONAL { ?uri skos:scopeNote ?scopeNote . }
            OPTIONAL { ?uri skos:notation ?notation . }
        }
        """
        try:
            response = requests.post(
                self.JURIVOC_SPARQL_ENDPOINT,
                data={"query": query, "format": "json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            self._parse_sparql_results(data)
            self._save_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to fetch Jurivoc from SPARQL: {e}")
            return False

    def _parse_sparql_results(self, data: Dict[str, Any]):
        """Parse SPARQL JSON results into JurivocConcept objects."""
        bindings = data.get("results", {}).get("bindings", [])
        concept_map: Dict[str, JurivocConcept] = {}

        for binding in bindings:
            uri = binding["uri"]["value"]
            if uri not in concept_map:
                concept_map[uri] = JurivocConcept(
                    uri=uri,
                    pref_label_de=binding.get("prefLabel_de", {}).get("value", ""),
                    pref_label_fr=binding.get("prefLabel_fr", {}).get("value", ""),
                    pref_label_it=binding.get("prefLabel_it", {}).get("value", None),
                    broader=binding.get("broader", {}).get("value", None),
                    scope_note=binding.get("scopeNote", {}).get("value", None),
                    notation=binding.get("notation", {}).get("value", None),
                )

            if "narrower" in binding:
                concept_map[uri].narrower.append(binding["narrower"]["value"])
            if "related" in binding:
                concept_map[uri].related.append(binding["related"]["value"])

        self.concepts = concept_map
        for concept in self.concepts.values():
            if concept.broader:
                self.hierarchy.setdefault(concept.broader, []).append(concept.uri)

        logger.info(f"Parsed {len(self.concepts)} Jurivoc concepts from SPARQL")

    def _save_cache(self):
        """Save concepts to local cache."""
        cache_file = self.cache_dir / "jurivoc_concepts.json"
        data = [
            {
                "uri": c.uri,
                "pref_label_de": c.pref_label_de,
                "pref_label_fr": c.pref_label_fr,
                "pref_label_it": c.pref_label_it,
                "broader": c.broader,
                "narrower": c.narrower,
                "related": c.related,
                "scope_note": c.scope_note,
                "notation": c.notation,
            }
            for c in self.concepts.values()
        ]
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.concepts)} concepts to cache")

    def load(self, force_refresh: bool = False) -> bool:
        """Load Jurivoc, using cache if available."""
        if not force_refresh and self.load_from_cache():
            return True
        return self.fetch_from_sparql()

    def get_concept(self, uri: str) -> Optional[JurivocConcept]:
        """Get a concept by URI."""
        return self.concepts.get(uri)

    def get_children(self, uri: str) -> List[JurivocConcept]:
        """Get direct children of a concept."""
        return [self.concepts[child_uri] for child_uri in self.hierarchy.get(uri, []) if child_uri in self.concepts]

    def get_all_descendants(self, uri: str) -> List[JurivocConcept]:
        """Get all descendants of a concept (recursive)."""
        descendants = []
        for child_uri in self.hierarchy.get(uri, []):
            if child_uri in self.concepts:
                descendants.append(self.concepts[child_uri])
                descendants.extend(self.get_all_descendants(child_uri))
        return descendants

    def find_by_label(self, label: str, language: str = "de") -> List[JurivocConcept]:
        """Find concepts by preferred label (case-insensitive partial match)."""
        label_lower = label.lower()
        results = []
        for concept in self.concepts.values():
            pref_label = getattr(concept, f"pref_label_{language}", "")
            if label_lower in pref_label.lower():
                results.append(concept)
        return results

    def get_hierarchy_depth(self, uri: str) -> int:
        """Get the depth of a concept in the hierarchy (0 = root)."""
        depth = 0
        current = uri
        while current in self.concepts and self.concepts[current].broader:
            current = self.concepts[current].broader
            depth += 1
        return depth


class TFMetadataLoader:
    """Loads Swiss Federal Supreme Court decision metadata from various sources."""

    def __init__(self, cache_dir: str = "evaluation/data/tf_metadata"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.decisions: Dict[str, TFDecisionMetadata] = {}

    def load_from_opencaselaw_api(
        self,
        court: str = "bger",
        date_from: str = "2000-01-01",
        date_to: Optional[str] = None,
        limit: int = 1000,
    ) -> List[TFDecisionMetadata]:
        """Load decision metadata from OpenCaseLaw REST API."""
        url = "https://opencaselaw.ch/api/decisions"
        params = {
            "court": court,
            "date_from": date_from,
            "limit": limit,
        }
        if date_to:
            params["date_to"] = date_to

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            decisions = []
            for item in data.get("results", []):
                decision = TFDecisionMetadata(
                    decision_id=item.get("decision_id", ""),
                    docket_number=item.get("docket_number", ""),
                    date=item.get("decision_date", ""),
                    language=item.get("language", ""),
                    court=item.get("court", ""),
                    chamber=item.get("chamber"),
                    legal_area=item.get("legal_area"),
                    cited_decisions=item.get("citations", {}).get("cited", []),
                    citing_decisions=item.get("citations", {}).get("citing", []),
                )
                decisions.append(decision)
                self.decisions[decision.decision_id] = decision

            logger.info(f"Loaded {len(decisions)} decisions from OpenCaseLaw API")
            return decisions

        except Exception as e:
            logger.error(f"Failed to load from OpenCaseLaw API: {e}")
            return []

    def load_from_scd_parquet(self, parquet_path: str) -> List[TFDecisionMetadata]:
        """Load decision metadata from SCD Parquet file."""
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)

            decisions = []
            for _, row in df.iterrows():
                decision = TFDecisionMetadata(
                    decision_id=str(row.get("decision_id", "")),
                    docket_number=str(row.get("aktenzeichen", "")),
                    date=str(row.get("entscheiddatum", "")),
                    language=str(row.get("sprache", "")),
                    court="bger",
                    chamber=str(row.get("abteilung", "")) if "abteilung" in row else None,
                    legal_area=str(row.get("rechtsgebiet", "")) if "rechtsgebiet" in row else None,
                    outcome=str(row.get("verfahrensausgang", "")) if "verfahrensausgang" in row else None,
                )
                # Parse Jurivoc descriptors if available
                if "jurivoc" in row and pd.notna(row["jurivoc"]):
                    decision.jurivoc_descriptors = str(row["jurivoc"]).split(";")

                decisions.append(decision)
                self.decisions[decision.decision_id] = decision

            logger.info(f"Loaded {len(decisions)} decisions from SCD Parquet")
            return decisions

        except Exception as e:
            logger.error(f"Failed to load from SCD Parquet: {e}")
            return []

    def get_decisions_by_jurivoc(self, descriptor_uri: str) -> List[TFDecisionMetadata]:
        """Get all decisions annotated with a specific Jurivoc descriptor."""
        return [
            d for d in self.decisions.values()
            if descriptor_uri in d.jurivoc_descriptors
        ]

    def get_decisions_by_legal_area(self, area: str) -> List[TFDecisionMetadata]:
        """Get all decisions in a legal area."""
        return [
            d for d in self.decisions.values()
            if d.legal_area and area.lower() in d.legal_area.lower()
        ]

    def get_citation_pairs(self) -> List[tuple]:
        """Get all (citing, cited) decision pairs."""
        pairs = []
        for decision in self.decisions.values():
            for cited in decision.cited_decisions:
                pairs.append((decision.decision_id, cited))
        return pairs

    def save_cache(self, filename: str = "tf_metadata.json"):
        """Save decisions to local cache."""
        cache_file = self.cache_dir / filename
        data = []
        for decision in self.decisions.values():
            data.append({
                "decision_id": decision.decision_id,
                "docket_number": decision.docket_number,
                "date": decision.date,
                "language": decision.language,
                "court": decision.court,
                "chamber": decision.chamber,
                "legal_area": decision.legal_area,
                "jurivoc_descriptors": decision.jurivoc_descriptors,
                "cited_decisions": decision.cited_decisions,
                "citing_decisions": decision.citing_decisions,
                "outcome": decision.outcome,
                "parties": decision.parties,
                "norms": decision.norms,
            })
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.decisions)} decisions to cache")

    def load_cache(self, filename: str = "tf_metadata.json") -> bool:
        """Load decisions from local cache."""
        cache_file = self.cache_dir / filename
        if not cache_file.exists():
            return False
        with open(cache_file, "r") as f:
            data = json.load(f)
        for item in data:
            decision = TFDecisionMetadata(**item)
            self.decisions[decision.decision_id] = decision
        logger.info(f"Loaded {len(self.decisions)} decisions from cache")
        return True


class WeakSupervisionBenchmark:
    """
    Creates evaluation benchmarks from Jurivoc/TF metadata as weak supervision.

    This implements the "imperfect human supervision" approach from the Master Prompt:
    - Jurivoc descriptors as proxy for legal issue similarity
    - Citation graph as proxy for doctrinal lineage
    - Legal area / chamber as proxy for domain structure
    - Language as test for multilingual invariance
    """

    def __init__(
        self,
        jurivoc_loader: Optional[JurivocLoader] = None,
        tf_loader: Optional[TFMetadataLoader] = None,
    ):
        self.jurivoc = jurivoc_loader or JurivocLoader()
        self.tf = tf_loader or TFMetadataLoader()

    def load_data(self, force_refresh: bool = False) -> bool:
        """Load both Jurivoc and TF metadata."""
        jurivoc_ok = self.jurivoc.load(force_refresh=force_refresh)
        tf_ok = self.tf.load_cache() or len(self.tf.decisions) > 0
        return jurivoc_ok and tf_ok

    def create_jurivoc_similarity_benchmark(
        self,
        min_decisions_per_descriptor: int = 5,
        max_descriptors: int = 100,
    ) -> Dict[str, Any]:
        """
        Create a benchmark where decisions sharing Jurivoc descriptors
        should be closer in the legal distance space.

        Returns a dict with:
        - positive_pairs: list of (decision_id_1, decision_id_2) sharing descriptors
        - negative_pairs: list of (decision_id_1, decision_id_2) with no shared descriptors
        - descriptor_to_decisions: mapping for analysis
        """
        descriptor_to_decisions = {}
        for decision in self.tf.decisions.values():
            for desc in decision.jurivoc_descriptors:
                descriptor_to_decisions.setdefault(desc, []).append(decision.decision_id)

        # Filter descriptors with enough decisions
        valid_descriptors = {
            desc: decisions
            for desc, decisions in descriptor_to_decisions.items()
            if len(decisions) >= min_decisions_per_descriptor
        }

        # Limit to max_descriptors
        sorted_descriptors = sorted(
            valid_descriptors.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:max_descriptors]

        positive_pairs = []
        for desc, decisions in sorted_descriptors:
            for i, d1 in enumerate(decisions):
                for d2 in decisions[i+1:]:
                    positive_pairs.append((d1, d2, desc))

        # Create negative pairs (decisions with no shared descriptors)
        all_decisions = list(self.tf.decisions.keys())
        import random
        random.seed(42)
        negative_pairs = []
        attempts = 0
        while len(negative_pairs) < len(positive_pairs) and attempts < len(positive_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            desc1 = set(self.tf.decisions[d1].jurivoc_descriptors)
            desc2 = set(self.tf.decisions[d2].jurivoc_descriptors)
            if not desc1.intersection(desc2):
                negative_pairs.append((d1, d2))
            attempts += 1

        return {
            "positive_pairs": positive_pairs,
            "negative_pairs": negative_pairs,
            "descriptor_to_decisions": {k: v for k, v in sorted_descriptors},
            "num_descriptors": len(sorted_descriptors),
            "num_positive_pairs": len(positive_pairs),
            "num_negative_pairs": len(negative_pairs),
        }

    def create_citation_lineage_benchmark(
        self,
        max_depth: int = 3,
        min_pairs: int = 100,
    ) -> Dict[str, Any]:
        """
        Create a benchmark where decisions in the same citation lineage
        (directly or indirectly citing each other) should be closer.
        """
        citation_pairs = self.tf.get_citation_pairs()

        # Build adjacency list
        cites_graph = {}
        cited_by_graph = {}
        for citing, cited in citation_pairs:
            cites_graph.setdefault(citing, []).append(cited)
            cited_by_graph.setdefault(cited, []).append(citing)

        # Find lineage pairs up to max_depth
        lineage_pairs = set()
        for start in cites_graph:
            visited = {start}
            frontier = [(start, 0)]
            while frontier:
                node, depth = frontier.pop(0)
                if depth >= max_depth:
                    continue
                for neighbor in cites_graph.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        lineage_pairs.add((start, neighbor))
                        frontier.append((neighbor, depth + 1))
                for neighbor in cited_by_graph.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        lineage_pairs.add((start, neighbor))
                        frontier.append((neighbor, depth + 1))

        lineage_pairs = list(lineage_pairs)[:min_pairs * 2]

        # Create non-lineage negative pairs
        all_decisions = list(self.tf.decisions.keys())
        import random
        random.seed(42)
        non_lineage_pairs = []
        lineage_set = set(lineage_pairs)
        attempts = 0
        while len(non_lineage_pairs) < len(lineage_pairs) and attempts < len(lineage_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            if (d1, d2) not in lineage_set and (d2, d1) not in lineage_set:
                non_lineage_pairs.append((d1, d2))
            attempts += 1

        return {
            "lineage_pairs": lineage_pairs[:min_pairs],
            "non_lineage_pairs": non_lineage_pairs[:min_pairs],
            "num_lineage_pairs": min(len(lineage_pairs), min_pairs),
            "num_non_lineage_pairs": len(non_lineage_pairs),
        }

    def create_legal_area_benchmark(self) -> Dict[str, Any]:
        """Create benchmark based on legal area / chamber metadata."""
        area_to_decisions = {}
        for decision in self.tf.decisions.values():
            area = decision.legal_area or decision.chamber or "unknown"
            area_to_decisions.setdefault(area, []).append(decision.decision_id)

        # Filter areas with enough decisions
        valid_areas = {k: v for k, v in area_to_decisions.items() if len(v) >= 10}

        positive_pairs = []
        for area, decisions in valid_areas.items():
            for i, d1 in enumerate(decisions):
                for d2 in decisions[i+1:]:
                    positive_pairs.append((d1, d2, area))

        all_decisions = list(self.tf.decisions.keys())
        import random
        random.seed(42)
        negative_pairs = []
        attempts = 0
        while len(negative_pairs) < len(positive_pairs) and attempts < len(positive_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            area1 = self.tf.decisions[d1].legal_area or self.tf.decisions[d1].chamber or "unknown"
            area2 = self.tf.decisions[d2].legal_area or self.tf.decisions[d2].chamber or "unknown"
            if area1 != area2:
                negative_pairs.append((d1, d2))
            attempts += 1

        return {
            "positive_pairs": positive_pairs,
            "negative_pairs": negative_pairs,
            "area_to_decisions": valid_areas,
            "num_areas": len(valid_areas),
        }

    def create_multilingual_benchmark(self) -> Dict[str, Any]:
        """Create benchmark for testing cross-language invariance."""
        # Group decisions by docket number (same case in different languages)
        docket_to_decisions = {}
        for decision in self.tf.decisions.values():
            # Normalize docket to find parallel versions
            base_docket = decision.docket_number.split("/")[0] if "/" in decision.docket_number else decision.docket_number
            docket_to_decisions.setdefault(base_docket, []).append(decision)

        # Find dockets with multiple languages
        multilingual_groups = {
            docket: decisions
            for docket, decisions in docket_to_decisions.items()
            if len({d.language for d in decisions}) > 1
        }

        cross_lang_pairs = []
        for docket, decisions in multilingual_groups.items():
            for i, d1 in enumerate(decisions):
                for d2 in decisions[i+1:]:
                    if d1.language != d2.language:
                        cross_lang_pairs.append((d1.decision_id, d2.decision_id, docket))

        return {
            "cross_language_pairs": cross_lang_pairs,
            "num_multilingual_dockets": len(multilingual_groups),
            "num_cross_lang_pairs": len(cross_lang_pairs),
        }