"""
Zoom Coherence Loader
Loads zoom coherence experiment results from fractal-map lane.
Provides metrics showing how zoom reveals legally coherent substructure.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class ZoomCoherenceLoader:
    """Loads and provides access to zoom coherence experiment results."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self._coherence_data: Optional[Dict] = None
        self._api_metadata: Optional[Dict] = None
        self._loaded = False

    def load(self) -> bool:
        """Load zoom coherence results and API metadata."""
        # Load coherence results
        coherence_path = self.results_dir / "evaluation" / "zoom_coherence_results.json"
        if coherence_path.exists():
            with open(coherence_path) as f:
                self._coherence_data = json.load(f)

        # Load API metadata
        api_path = self.results_dir / "zoom_api" / "api_metadata.json"
        if api_path.exists():
            with open(api_path) as f:
                self._api_metadata = json.load(f)

        self._loaded = True
        return self._coherence_data is not None

    def get_summary(self) -> Dict[str, Any]:
        """Get overall zoom coherence summary."""
        if not self._loaded or not self._coherence_data:
            return {"error": "Zoom coherence data not loaded"}

        # Extract key metrics
        flat_baseline = self._coherence_data.get("flat_baseline", {})
        improvement_analysis = self._coherence_data.get("improvement_analysis", {})

        # Calculate overall improvement rate across all coarse resolutions
        total_improvements = 0
        total_deteriorations = 0
        total_no_change = 0

        for res_key, analysis in improvement_analysis.items():
            total_improvements += analysis.get("n_improvements", 0)
            total_deteriorations += analysis.get("n_deteriorations", 0)
            total_no_change += analysis.get("n_no_change", 0)

        total_clusters = total_improvements + total_deteriorations + total_no_change
        improvement_rate = total_improvements / total_clusters if total_clusters > 0 else 0

        return {
            "hypothesis": self._coherence_data.get("hypothesis", ""),
            "frozen_sample": self._coherence_data.get("frozen_sample", ""),
            "frozen_metric": self._coherence_data.get("frozen_metric", ""),
            "success_rule": self._coherence_data.get("success_rule", ""),
            "overall_improvement_rate": improvement_rate,
            "total_improvements": total_improvements,
            "total_deteriorations": total_deteriorations,
            "total_no_change": total_no_change,
            "total_clusters_tested": total_clusters,
            "flat_baseline_best_ratio": self._get_best_flat_ratio(),
            "best_zoom_ratio": self._get_best_zoom_ratio(),
            "resolutions_tested": self._coherence_data.get("resolutions_tested", []),
        }

    def get_flat_baseline(self) -> Dict[str, Any]:
        """Get flat baseline metrics at different resolutions."""
        if not self._loaded or not self._coherence_data:
            return {"error": "Zoom coherence data not loaded"}

        return self._coherence_data.get("flat_baseline", {})

    def get_cluster_improvements(self, coarse_resolution: float = 0.25) -> Dict[str, Any]:
        """Get zoom improvement data for clusters at a specific coarse resolution."""
        if not self._loaded or not self._coherence_data:
            return {"error": "Zoom coherence data not loaded"}

        improvement_analysis = self._coherence_data.get("improvement_analysis", {})
        res_key = f"coarse_res_{coarse_resolution}"

        if res_key not in improvement_analysis:
            return {"error": f"Resolution {coarse_resolution} not found"}

        return improvement_analysis[res_key]

    def _get_best_flat_ratio(self) -> float:
        """Get the best flat baseline ratio across resolutions."""
        flat_baseline = self._coherence_data.get("flat_baseline", {})
        best_ratio = 0.0

        for res_key, metrics in flat_baseline.items():
            if isinstance(metrics, dict):
                ratio = metrics.get("ratio", 0)
                if ratio > best_ratio:
                    best_ratio = ratio

        return best_ratio

    def _get_best_zoom_ratio(self) -> float:
        """Get the best zoom ratio achieved across all clusters."""
        improvement_analysis = self._coherence_data.get("improvement_analysis", {})
        best_ratio = 0.0

        for res_key, analysis in improvement_analysis.items():
            improvements = analysis.get("improvements", [])
            for imp in improvements:
                fine_ratio = imp.get("fine_ratio", 0)
                if fine_ratio > best_ratio:
                    best_ratio = fine_ratio

        return best_ratio
