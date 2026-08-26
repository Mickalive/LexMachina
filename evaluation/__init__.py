"""
LexMachina Evaluation Framework
Core evaluation infrastructure for testing legal distance representations.
"""

from .benchmarks import BenchmarkHarness, BenchmarkResult
from .tests.neighbor_relevance import NeighborRelevanceTest
from .tests.boilerplate_resistance import BoilerplateResistanceTest
from .tests.multilingual_invariance import MultilingualInvarianceTest
from .tests.stability import CorpusStabilityTest
from .tests.hierarchy_coherence import HierarchyCoherenceTest
from .tests.citation_proximity import CitationProximityBenchmark
from .tests.legal_area_clustering import LegalAreaClusteringBenchmark

__all__ = [
    "BenchmarkHarness",
    "BenchmarkResult",
    "NeighborRelevanceTest",
    "BoilerplateResistanceTest",
    "MultilingualInvarianceTest",
    "CorpusStabilityTest",
    "HierarchyCoherenceTest",
    "CitationProximityBenchmark",
    "LegalAreaClusteringBenchmark",
]