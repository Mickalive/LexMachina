"""
LexMachina Section-Based Map Modes
Loads section-specific projections (sachverhalt, erwaegungen, dispositiv, etc.)
as alternative map views, enabling multi-view navigation per the Master Prompt's
multi-view requirement.

Each mode shows the same decisions positioned by legal similarity computed from
a specific document section, allowing jurists to switch between:
- Legal issue view (erwaegungen = reasoning/considerations)
- Factual view (sachverhalt = facts)
- Holding view (dispositiv = holding/ratio)
- Combined views
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class SectionMode:
    """A section-based map mode with its own 2D projection."""
    name: str
    label: str
    description: str
    decision_ids: List[str]
    positions: Dict[str, Tuple[float, float]]
    n_decisions: int
    clustering: Dict[str, Dict]  # resolution -> {labels, n_clusters, coherence}


class SectionModeLoader:
    """Loads section-based projections as alternative map modes."""

    # Human-readable labels and descriptions for each section mode
    MODE_INFO = {
        "sachverhalt": {
            "label": "Facts (Sachverhalt)",
            "description": "Decisions positioned by factual similarity — legally relevant facts group together",
        },
        "erwaegungen": {
            "label": "Reasoning (Erwägungen)",
            "description": "Decisions positioned by reasoning similarity — similar legal arguments cluster",
        },
        "dispositiv": {
            "label": "Holding (Dispositiv)",
            "description": "Decisions positioned by holding similarity — similar outcomes cluster",
        },
        "full_text": {
            "label": "Full Text",
            "description": "Decisions positioned by overall document similarity",
        },
        "erwaegungen_dispositiv": {
            "label": "Reasoning + Holding",
            "description": "Combined reasoning and holding view — captures doctrinal proximity",
        },
        "sachverhalt_erwaegungen_dispositiv": {
            "label": "Facts + Reasoning + Holding",
            "description": "Structured view excluding procedural boilerplate — captures core legal content",
        },
    }

    def __init__(self, section_dir: str):
        self.section_dir = Path(section_dir)
        self.modes: Dict[str, SectionMode] = {}
        self._loaded = False

    def load(self) -> int:
        """Load all section-based projections. Returns count of modes loaded."""
        if self._loaded:
            return len(self.modes)

        metadata_path = self.section_dir / "metadata.json"
        clustering_path = self.section_dir / "clustering_results.json"

        if not metadata_path.exists():
            return 0

        # Load metadata (decision list)
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        decision_ids = [m["decision_id"] for m in metadata]

        # Load clustering results
        clustering_data = {}
        if clustering_path.exists():
            with open(clustering_path, "r") as f:
                clustering_data = json.load(f)

        # Load each section projection
        section_names = [
            "sachverhalt",
            "erwaegungen",
            "dispositiv",
            "full_text",
            "erwaegungen_dispositiv",
            "sachverhalt_erwaegungen_dispositiv",
        ]

        for section_name in section_names:
            proj_path = self.section_dir / f"projection_{section_name}.npy"
            if not proj_path.exists():
                continue

            projection = np.load(proj_path)
            positions = {}
            for i, did in enumerate(decision_ids):
                if i < len(projection):
                    positions[did] = (float(projection[i, 0]), float(projection[i, 1]))

            info = self.MODE_INFO.get(section_name, {})
            section_clustering = clustering_data.get(section_name, {})

            self.modes[section_name] = SectionMode(
                name=section_name,
                label=info.get("label", section_name),
                description=info.get("description", ""),
                decision_ids=decision_ids,
                positions=positions,
                n_decisions=len(decision_ids),
                clustering=section_clustering,
            )

        self._loaded = True
        return len(self.modes)

    def get_mode(self, name: str) -> Optional[SectionMode]:
        """Get a specific section mode."""
        return self.modes.get(name)

    def get_available_modes(self) -> List[Dict[str, Any]]:
        """List available section modes with metadata."""
        return [
            {
                "name": mode.name,
                "label": mode.label,
                "description": mode.description,
                "n_decisions": mode.n_decisions,
                "type": "section_view",
                "coverage": "63 of 1000 decisions have section-based projections",
            }
            for mode in self.modes.values()
        ]

    def get_positions(self, mode_name: str) -> Dict[str, Tuple[float, float]]:
        """Get 2D positions for a section mode."""
        mode = self.get_mode(mode_name)
        return mode.positions if mode else {}

    def get_clustering(
        self, mode_name: str, resolution: float = 1.0
    ) -> Optional[Dict]:
        """Get clustering results for a section mode at a specific resolution."""
        mode = self.get_mode(mode_name)
        if not mode:
            return None
        key = f"resolution_{resolution}"
        return mode.clustering.get(key)
