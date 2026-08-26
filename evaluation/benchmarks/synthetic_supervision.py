"""
Synthetic Weak Supervision for Evaluation

Provides weak supervision benchmarks using synthetic ground truth data
when real TF/Jurivoc data is not available.
"""

import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SyntheticSupervisionConfig:
    """Configuration for synthetic weak supervision."""
    min_positive_pairs: int = 50
    max_pairs_per_query: int = 100
    random_seed: int = 42


class SyntheticWeakSupervision:
    """
    Creates evaluation benchmarks from synthetic corpus ground truth.
    
    This replaces the real TF/Jurivoc weak supervision when running on synthetic data.
    """

    def __init__(self, ground_truth: Dict[str, Any], config: Optional[SyntheticSupervisionConfig] = None):
        self.ground_truth = ground_truth
        self.config = config or SyntheticSupervisionConfig()
        self.decision_metadata = ground_truth.get("decision_metadata", {})
        self.area_to_jurivoc = ground_truth.get("area_to_jurivoc", {})

        # Build reverse mappings
        self.jurivoc_to_area = {}
        for area, concepts in self.area_to_jurivoc.items():
            for concept in concepts:
                self.jurivoc_to_area[concept] = area

    def create_jurivoc_similarity_benchmark(self) -> Dict[str, Any]:
        """Create benchmark where decisions sharing Jurivoc descriptors should be closer."""
        # Group decisions by Jurivoc descriptor
        descriptor_to_decisions = defaultdict(list)
        for did, meta in self.decision_metadata.items():
            for desc in meta.get("jurivoc_descriptors", []):
                descriptor_to_decisions[desc].append(did)

        # Filter descriptors with enough decisions
        valid_descriptors = {
            desc: decisions
            for desc, decisions in descriptor_to_decisions.items()
            if len(decisions) >= 2
        }

        positive_pairs = []
        for desc, decisions in valid_descriptors.items():
            for i, d1 in enumerate(decisions):
                for d2 in decisions[i+1:]:
                    positive_pairs.append((d1, d2, desc))

        # Create negative pairs (decisions with no shared descriptors)
        all_decisions = list(self.decision_metadata.keys())
        random.seed(self.config.random_seed)
        negative_pairs = []
        attempts = 0
        while len(negative_pairs) < len(positive_pairs) and attempts < len(positive_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            desc1 = set(self.decision_metadata[d1].get("jurivoc_descriptors", []))
            desc2 = set(self.decision_metadata[d2].get("jurivoc_descriptors", []))
            if not desc1.intersection(desc2):
                negative_pairs.append((d1, d2))
            attempts += 1

        return {
            "positive_pairs": positive_pairs,
            "negative_pairs": negative_pairs,
            "descriptor_to_decisions": dict(valid_descriptors),
            "num_descriptors": len(valid_descriptors),
            "num_positive_pairs": len(positive_pairs),
            "num_negative_pairs": len(negative_pairs),
        }

    def create_citation_lineage_benchmark(self) -> Dict[str, Any]:
        """Create benchmark based on citation graph."""
        # Build citation graph from ground truth
        citation_pairs = []
        for did, meta in self.decision_metadata.items():
            for cited in meta.get("cited_decisions", []):
                if cited in self.decision_metadata:
                    citation_pairs.append((did, cited))

        # Build adjacency
        cites_graph = defaultdict(list)
        cited_by_graph = defaultdict(list)
        for citing, cited in citation_pairs:
            cites_graph[citing].append(cited)
            cited_by_graph[cited].append(citing)

        # Find lineage pairs (up to 2 hops)
        lineage_pairs = set()
        for start in cites_graph:
            visited = {start}
            frontier = [(start, 0)]
            while frontier:
                node, depth = frontier.pop(0)
                if depth >= 2:
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

        lineage_pairs = list(lineage_pairs)

        # Create non-lineage negative pairs
        all_decisions = list(self.decision_metadata.keys())
        random.seed(self.config.random_seed)
        non_lineage_pairs = []
        lineage_set = set(lineage_pairs)
        attempts = 0
        while len(non_lineage_pairs) < len(lineage_pairs) and attempts < len(lineage_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            if (d1, d2) not in lineage_set and (d2, d1) not in lineage_set:
                non_lineage_pairs.append((d1, d2))
            attempts += 1

        return {
            "lineage_pairs": lineage_pairs,
            "non_lineage_pairs": non_lineage_pairs,
            "num_lineage_pairs": len(lineage_pairs),
            "num_non_lineage_pairs": len(non_lineage_pairs),
        }

    def create_legal_area_benchmark(self) -> Dict[str, Any]:
        """Create benchmark based on legal area metadata."""
        area_to_decisions = defaultdict(list)
        for did, meta in self.decision_metadata.items():
            area = meta.get("legal_area", "unknown")
            area_to_decisions[area].append(did)

        positive_pairs = []
        for area, decisions in area_to_decisions.items():
            if len(decisions) >= 2:
                for i, d1 in enumerate(decisions):
                    for d2 in decisions[i+1:]:
                        positive_pairs.append((d1, d2, area))

        # Negative pairs from different areas
        all_decisions = list(self.decision_metadata.keys())
        random.seed(self.config.random_seed)
        negative_pairs = []
        attempts = 0
        while len(negative_pairs) < len(positive_pairs) and attempts < len(positive_pairs) * 10:
            d1, d2 = random.sample(all_decisions, 2)
            area1 = self.decision_metadata[d1].get("legal_area", "unknown")
            area2 = self.decision_metadata[d2].get("legal_area", "unknown")
            if area1 != area2:
                negative_pairs.append((d1, d2))
            attempts += 1

        return {
            "positive_pairs": positive_pairs,
            "negative_pairs": negative_pairs,
            "area_to_decisions": dict(area_to_decisions),
            "num_areas": len(area_to_decisions),
        }

    def create_multilingual_benchmark(self) -> Dict[str, Any]:
        """Create benchmark for testing cross-language invariance."""
        # Group by docket number (parallel versions)
        docket_to_decisions = defaultdict(list)
        for did, meta in self.decision_metadata.items():
            docket = meta.get("docket_number", "").split("/")[0] if "/" in meta.get("docket_number", "") else meta.get("docket_number", "")
            docket_to_decisions[docket].append(did)

        # Find dockets with multiple languages
        multilingual_groups = {
            docket: decisions
            for docket, decisions in docket_to_decisions.items()
            if len({self.decision_metadata[d].get("language") for d in decisions}) > 1
        }

        cross_lang_pairs = []
        for docket, decisions in multilingual_groups.items():
            for i, d1 in enumerate(decisions):
                for d2 in decisions[i+1:]:
                    lang1 = self.decision_metadata[d1].get("language")
                    lang2 = self.decision_metadata[d2].get("language")
                    if lang1 != lang2:
                        cross_lang_pairs.append((d1, d2, docket))

        return {
            "cross_language_pairs": cross_lang_pairs,
            "num_multilingual_dockets": len(multilingual_groups),
            "num_cross_lang_pairs": len(cross_lang_pairs),
        }