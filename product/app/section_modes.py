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

Loader priority: section_scaled/ (1000 decisions) > section_experiment_clean/ (63 decisions)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
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
    n_section_decisions: int
    n_baseline_decisions: int
    clustering: Dict[str, Dict]  # resolution -> {labels, n_clusters, coherence}


class SectionModeLoader:
    """Loads section-based projections as alternative map modes.

    Tries scaled projections first (section_scaled/), falls back to
    experiment-clean projections (section_experiment_clean/).
    """

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

    SECTION_NAMES = [
        "sachverhalt",
        "erwaegungen",
        "dispositiv",
        "full_text",
        "erwaegungen_dispositiv",
        "sachverhalt_erwaegungen_dispositiv",
    ]

    TOTAL_DECISIONS = 1000

    def __init__(self, section_dir: str, fallback_dir: Optional[str] = None):
        self.primary_dir = Path(section_dir)
        self.fallback_dir = Path(fallback_dir) if fallback_dir else None
        self.active_dir: Optional[Path] = None
        self.modes: Dict[str, SectionMode] = {}
        self._loaded = False
        self._source_label: str = ""
        self._is_scaled: bool = False

    def _resolve_active_dir(self) -> Optional[Path]:
        """Pick the best available directory: primary (scaled) then fallback."""
        if self.primary_dir.exists():
            meta = self.primary_dir / "metadata.json"
            if meta.exists():
                self._source_label = self.primary_dir.name
                return self.primary_dir
        if self.fallback_dir and self.fallback_dir.exists():
            meta = self.fallback_dir / "metadata.json"
            if meta.exists():
                self._source_label = self.fallback_dir.name
                return self.fallback_dir
        return None

    def _load_scaled(self) -> None:
        """Load from section_scaled/ directory (blended section+baseline projections)."""
        metadata_path = self.active_dir / "metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        total_decisions = metadata.get("total_decisions", self.TOTAL_DECISIONS)
        self.TOTAL_DECISIONS = total_decisions

        # Get provenance to identify section vs baseline decisions
        provenance = metadata.get("decision_provenance", [])
        section_ids = {p["decision_id"] for p in provenance if p.get("source") == "section_projection"}
        baseline_ids = {p["decision_id"] for p in provenance if p.get("source") == "baseline"}
        all_decision_ids = [p["decision_id"] for p in provenance]

        # Load section-specific metadata for clustering
        section_meta_path = self.active_dir / "section_metadata.json"
        section_metadata = []
        if section_meta_path.exists():
            with open(section_meta_path, "r") as f:
                section_metadata = json.load(f)
        section_id_set = {m["decision_id"] for m in section_metadata}

        # Load clustering results — check scaled dir first, then fallback
        clustering_data = {}
        clustering_path = self.active_dir / "clustering_results.json"
        if clustering_path.exists():
            with open(clustering_path, "r") as f:
                clustering_data = json.load(f)
        elif self.fallback_dir and self.fallback_dir.exists():
            fallback_clustering = self.fallback_dir / "clustering_results.json"
            if fallback_clustering.exists():
                with open(fallback_clustering, "r") as f:
                    clustering_data = json.load(f)

        for section_name in self.SECTION_NAMES:
            proj_path = self.active_dir / f"projection_{section_name}.npy"
            if not proj_path.exists():
                continue

            projection = np.load(proj_path)
            positions: Dict[str, Tuple[float, float]] = {}
            for i, did in enumerate(all_decision_ids):
                if i < len(projection):
                    positions[did] = (float(projection[i, 0]), float(projection[i, 1]))

            info = self.MODE_INFO.get(section_name, {})
            section_clustering = clustering_data.get(section_name, {})
            n_section = len(section_ids)
            n_baseline = len(baseline_ids)

            self.modes[section_name] = SectionMode(
                name=section_name,
                label=info.get("label", section_name),
                description=info.get("description", ""),
                decision_ids=all_decision_ids,
                positions=positions,
                n_decisions=total_decisions,
                n_section_decisions=n_section,
                n_baseline_decisions=n_baseline,
                clustering=section_clustering,
            )

    def _load_experiment_clean(self) -> None:
        """Load from section_experiment_clean/ directory (section-only projections)."""
        metadata_path = self.active_dir / "metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        decision_ids = [m["decision_id"] for m in metadata]

        clustering_path = self.active_dir / "clustering_results.json"
        clustering_data = {}
        if clustering_path.exists():
            with open(clustering_path, "r") as f:
                clustering_data = json.load(f)

        n_section = len(decision_ids)
        n_baseline = max(0, self.TOTAL_DECISIONS - n_section)

        for section_name in self.SECTION_NAMES:
            proj_path = self.active_dir / f"projection_{section_name}.npy"
            if not proj_path.exists():
                continue

            projection = np.load(proj_path)
            positions: Dict[str, Tuple[float, float]] = {}
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
                n_decisions=self.TOTAL_DECISIONS,
                n_section_decisions=n_section,
                n_baseline_decisions=n_baseline,
                clustering=section_clustering,
            )

    def load(self) -> int:
        """Load all section-based projections. Returns count of modes loaded."""
        if self._loaded:
            return len(self.modes)

        self.active_dir = self._resolve_active_dir()
        if self.active_dir is None:
            return 0

        # Detect scaled vs experiment-clean by checking metadata format
        meta_path = self.active_dir / "metadata.json"
        with open(meta_path, "r") as f:
            probe = json.load(f)

        if isinstance(probe, dict) and "decision_provenance" in probe:
            self._is_scaled = True
            self._load_scaled()
        else:
            self._is_scaled = False
            self._load_experiment_clean()

        self._loaded = True
        return len(self.modes)

    def get_mode(self, name: str) -> Optional[SectionMode]:
        """Get a specific section mode."""
        return self.modes.get(name)

    def _coverage_string(self, mode: SectionMode) -> str:
        n_sec = mode.n_section_decisions
        n_base = mode.n_baseline_decisions
        total = mode.n_decisions
        if n_sec == total:
            return f"All {total} decisions have section-specific projections"
        if n_sec == 0:
            return f"No section projections available; all {total} decisions use baseline fallback"
        return (
            f"{n_sec} of {total} decisions have section-specific projections, "
            f"{n_base} use baseline fallback"
        )

    def get_available_modes(self) -> List[Dict[str, Any]]:
        """List available section modes with metadata."""
        return [
            {
                "name": mode.name,
                "label": mode.label,
                "description": mode.description,
                "n_decisions": mode.n_decisions,
                "n_section_decisions": mode.n_section_decisions,
                "n_baseline_decisions": mode.n_baseline_decisions,
                "type": "section_view",
                "source": self._source_label,
                "coverage": self._coverage_string(mode),
            }
            for mode in self.modes.values()
        ]

    def get_positions(self, mode_name: str) -> Dict[str, Tuple[float, float]]:
        """Get 2D positions for a section mode."""
        mode = self.get_mode(mode_name)
        return mode.positions if mode else {}

    def get_position_details(
        self, mode_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get positions with per-decision metadata including has_section_data flag."""
        mode = self.get_mode(mode_name)
        if not mode:
            return {}
        # In scaled mode, we know provenance; otherwise all positions have section data
        if self._is_scaled:
            # All positions exist, but we can't tell provenance per-decision here
            # without reloading metadata. Return all as section_data=True since
            # the projection exists for each decision.
            return {
                did: {"x": pos[0], "y": pos[1], "has_section_data": True}
                for did, pos in mode.positions.items()
            }
        return {
            did: {"x": pos[0], "y": pos[1], "has_section_data": True}
            for did, pos in mode.positions.items()
        }

    def get_clustering(
        self, mode_name: str, resolution: float = 1.0
    ) -> Optional[Dict]:
        """Get clustering results for a section mode at a specific resolution."""
        mode = self.get_mode(mode_name)
        if not mode:
            return None
        key = f"resolution_{resolution}"
        return mode.clustering.get(key)
