"""
Evaluation Loader
Loads unified evaluation results and zoom coherence metrics for benchmark reporting.
Provides key metrics: best representation, zoom coherence improvement, boilerplate resistance.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class EvaluationLoader:
    """Loads and provides access to evaluation benchmark data."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self._unified_data: Optional[Dict] = None
        self._zoom_coherence_data: Optional[Dict] = None
        self._loaded = False

    def load(self) -> bool:
        """Load evaluation results from disk."""
        unified_path = self.results_dir / "unified_evaluation" / "unified_results.json"
        if unified_path.exists():
            with open(unified_path) as f:
                self._unified_data = json.load(f)

        coherence_path = self.results_dir / "evaluation" / "zoom_coherence_results.json"
        if coherence_path.exists():
            with open(coherence_path) as f:
                self._zoom_coherence_data = json.load(f)

        self._loaded = True
        return self._unified_data is not None

    def get_benchmarks(self) -> Dict[str, Any]:
        """Return key evaluation benchmark metrics.

        Includes best representation, zoom coherence improvement rate,
        fine ratio vs flat baseline, boilerplate resistance scores,
        and language dominance warnings.
        """
        if not self._loaded:
            return {"error": "Evaluation data not loaded"}

        best_rep = self._find_best_representation()
        zoom_summary = self._compute_zoom_coherence_metrics()
        boilerplate = self._compute_boilerplate_resistance()
        lang_warnings = self._compute_language_dominance_warnings()

        return {
            "best_representation": best_rep,
            "zoom_coherence_improvement_rate": zoom_summary["improvement_rate"],
            "best_fine_ratio": zoom_summary["best_fine_ratio"],
            "flat_baseline_best_ratio": zoom_summary["flat_baseline_best_ratio"],
            "fine_vs_baseline_delta": zoom_summary["best_fine_ratio"] - zoom_summary["flat_baseline_best_ratio"],
            "boilerplate_resistance": boilerplate,
            "language_dominance_warnings": lang_warnings,
            "total_representations_evaluated": len(self._unified_data) if self._unified_data else 0,
            "resolutions_tested": self._zoom_coherence_data.get("resolutions_tested", []) if self._zoom_coherence_data else [],
        }

    def get_representation_quality(self) -> Dict[str, Dict[str, Any]]:
        """Return quality metrics per representation.

        For each representation, returns best ratio, modularity, purity scores,
        and cluster counts across resolutions.
        """
        if not self._loaded or not self._unified_data:
            return {"error": "Evaluation data not loaded"}

        quality = {}
        for rep_name, resolutions in self._unified_data.items():
            best_ratio = 0.0
            best_resolution = None
            best_modularity = 0.0
            total_clusters = 0
            resolution_details = {}

            for res_key, metrics in resolutions.items():
                if not res_key.startswith("resolution_"):
                    continue
                ratio = metrics.get("ratio", 0)
                modularity = metrics.get("modularity", 0)
                n_clusters = metrics.get("n_clusters", 0)
                total_clusters += n_clusters

                resolution_details[res_key] = {
                    "n_clusters": n_clusters,
                    "modularity": round(modularity, 4),
                    "legal_area_purity": round(metrics.get("legal_area_purity", 0), 4),
                    "language_purity": round(metrics.get("language_purity", 0), 4),
                    "ratio": round(ratio, 4),
                }

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_resolution = res_key
                    best_modularity = modularity

            quality[rep_name] = {
                "best_ratio": round(best_ratio, 4),
                "best_resolution": best_resolution,
                "best_modularity": round(best_modularity, 4),
                "total_clusters_across_resolutions": total_clusters,
                "resolutions": resolution_details,
            }

        return quality

    def _find_best_representation(self) -> Dict[str, Any]:
        """Find the representation with the highest ratio at any resolution."""
        best_name = None
        best_ratio = 0.0
        best_resolution = None

        for rep_name, resolutions in self._unified_data.items():
            for res_key, metrics in resolutions.items():
                if not res_key.startswith("resolution_"):
                    continue
                ratio = metrics.get("ratio", 0)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_name = rep_name
                    best_resolution = res_key

        return {
            "name": best_name,
            "ratio": round(best_ratio, 4),
            "resolution": best_resolution,
        }

    def _compute_zoom_coherence_metrics(self) -> Dict[str, Any]:
        """Compute zoom coherence improvement metrics from coherence data."""
        if not self._zoom_coherence_data:
            return {
                "improvement_rate": 0.0,
                "best_fine_ratio": 0.0,
                "flat_baseline_best_ratio": 0.0,
            }

        flat_baseline = self._zoom_coherence_data.get("flat_baseline", {})
        improvement_analysis = self._zoom_coherence_data.get("improvement_analysis", {})

        # Best flat baseline ratio
        flat_best = 0.0
        for res_key, metrics in flat_baseline.items():
            if isinstance(metrics, dict):
                ratio = metrics.get("ratio", 0)
                if ratio > flat_best:
                    flat_best = ratio

        # Best fine ratio and improvement rate
        total_improvements = 0
        total_deteriorations = 0
        total_no_change = 0
        best_fine = 0.0

        for res_key, analysis in improvement_analysis.items():
            total_improvements += analysis.get("n_improvements", 0)
            total_deteriorations += analysis.get("n_deteriorations", 0)
            total_no_change += analysis.get("n_no_change", 0)
            for imp in analysis.get("improvements", []):
                fine_ratio = imp.get("fine_ratio", 0)
                if fine_ratio > best_fine:
                    best_fine = fine_ratio

        total_clusters = total_improvements + total_deteriorations + total_no_change
        improvement_rate = total_improvements / total_clusters if total_clusters > 0 else 0.0

        return {
            "improvement_rate": round(improvement_rate, 3),
            "best_fine_ratio": round(best_fine, 3),
            "flat_baseline_best_ratio": round(flat_best, 3),
            "total_improvements": total_improvements,
            "total_deteriorations": total_deteriorations,
            "total_no_change": total_no_change,
        }

    def _compute_boilerplate_resistance(self) -> Dict[str, Any]:
        """Compute boilerplate resistance scores per representation.

        Boilerplate resistance = how well legal_area_purity holds when
        language_purity is high (language-homogeneous clusters resist boilerplate).
        """
        if not self._unified_data:
            return {}

        scores = {}
        for rep_name, resolutions in self._unified_data.items():
            purity_values = []
            for res_key, metrics in resolutions.items():
                if not res_key.startswith("resolution_"):
                    continue
                lang_purity = metrics.get("language_purity", 0)
                legal_purity = metrics.get("legal_area_purity", 0)
                # Resistance: legal purity in language-homogeneous contexts
                if lang_purity > 0.9:
                    purity_values.append(legal_purity)

            scores[rep_name] = {
                "mean_legal_purity_in_lang_homogeneous": round(
                    sum(purity_values) / len(purity_values), 4
                ) if purity_values else 0.0,
                "n_resolutions_with_high_lang_purity": len(purity_values),
            }

        return scores

    def _compute_language_dominance_warnings(self) -> List[Dict[str, Any]]:
        """Identify representations with language dominance issues."""
        if not self._unified_data:
            return []

        warnings = []
        for rep_name, resolutions in self._unified_data.items():
            for res_key, metrics in resolutions.items():
                if not res_key.startswith("resolution_"):
                    continue
                lang_purity = metrics.get("language_purity", 0)
                if lang_purity > 0.99:
                    warnings.append({
                        "representation": rep_name,
                        "resolution": res_key,
                        "language_purity": round(lang_purity, 4),
                        "warning": f"Near-perfect language purity ({lang_purity:.3f}) may indicate insufficient cross-language mixing",
                    })

        return warnings
