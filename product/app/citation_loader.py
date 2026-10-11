"""
LexMachina Citation Graph Loader
Loads the citation graph and enables citation-based navigation:
- Outgoing citations: which decisions does this one cite?
- Incoming citations: which decisions cite this one?
- Citation-proximity clustering
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class CitationGraph:
    """Citation graph for the corpus."""
    outgoing: Dict[str, List[str]]  # decision_id -> [cited references]
    incoming: Dict[str, Set[str]]   # reference -> {citing decision_ids}
    n_decisions_with_citations: int
    total_citation_edges: int


class CitationLoader:
    """Loads and queries the citation graph."""

    def __init__(self, graph_path: str):
        self.graph_path = Path(graph_path)
        self.graph: Optional[CitationGraph] = None

    def load(self) -> bool:
        """Load the citation graph. Returns True if successful."""
        if not self.graph_path.exists():
            return False

        with open(self.graph_path, "r") as f:
            data = json.load(f)

        outgoing = data.get("outgoing", {})

        # Build reverse index (incoming citations)
        incoming: Dict[str, Set[str]] = {}
        for citing_id, references in outgoing.items():
            for ref in references:
                if ref not in incoming:
                    incoming[ref] = set()
                incoming[ref].add(citing_id)

        total_edges = sum(len(refs) for refs in outgoing.values())

        self.graph = CitationGraph(
            outgoing=outgoing,
            incoming=incoming,
            n_decisions_with_citations=len(outgoing),
            total_citation_edges=total_edges,
        )
        return True

    def get_outgoing(self, decision_id: str) -> List[str]:
        """Get references cited by this decision."""
        if not self.graph:
            return []
        return self.graph.outgoing.get(decision_id, [])

    def get_incoming(self, reference: str) -> List[str]:
        """Get decisions that cite this reference."""
        if not self.graph:
            return []
        return sorted(self.graph.incoming.get(reference, set()))

    def get_citation_count(self, decision_id: str) -> Dict[str, int]:
        """Get citation counts for a decision."""
        if not self.graph:
            return {"outgoing": 0, "incoming": 0}
        return {
            "outgoing": len(self.graph.outgoing.get(decision_id, [])),
            "incoming": len(self.graph.incoming.get(decision_id, set())),
        }

    def get_stats(self) -> Dict:
        """Get citation graph statistics."""
        if not self.graph:
            return {}
        return {
            "n_decisions_with_citations": self.graph.n_decisions_with_citations,
            "total_citation_edges": self.graph.total_citation_edges,
        }
