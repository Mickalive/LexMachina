"""LexMachina evaluation package.

v45 query-map evaluation is intentionally lightweight.  Historical 174k
benchmark exports remain available, but are imported lazily so that consuming
`evaluation.query_map` does not pull the legacy dependency graph into the
current product gate.
"""
from __future__ import annotations

from importlib import import_module

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

_LAZY = {
    "BenchmarkHarness": ("evaluation.benchmarks", "BenchmarkHarness"),
    "BenchmarkResult": ("evaluation.benchmarks", "BenchmarkResult"),
    "NeighborRelevanceTest": ("evaluation.tests.neighbor_relevance", "NeighborRelevanceTest"),
    "BoilerplateResistanceTest": ("evaluation.tests.boilerplate_resistance", "BoilerplateResistanceTest"),
    "MultilingualInvarianceTest": ("evaluation.tests.multilingual_invariance", "MultilingualInvarianceTest"),
    "CorpusStabilityTest": ("evaluation.tests.stability", "CorpusStabilityTest"),
    "HierarchyCoherenceTest": ("evaluation.tests.hierarchy_coherence", "HierarchyCoherenceTest"),
    "CitationProximityBenchmark": ("evaluation.tests.citation_proximity", "CitationProximityBenchmark"),
    "LegalAreaClusteringBenchmark": ("evaluation.tests.legal_area_clustering", "LegalAreaClusteringBenchmark"),
}


def __getattr__(name: str):
    try:
        module_name, attr = _LAZY[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value
