"""
Evaluation test modules.
"""

from .neighbor_relevance import NeighborRelevanceTest
from .boilerplate_resistance import BoilerplateResistanceTest
from .multilingual_invariance import MultilingualInvarianceTest
from .stability import CorpusStabilityTest
from .hierarchy_coherence import HierarchyCoherenceTest

__all__ = [
    "NeighborRelevanceTest",
    "BoilerplateResistanceTest",
    "MultilingualInvarianceTest",
    "CorpusStabilityTest",
    "HierarchyCoherenceTest",
]