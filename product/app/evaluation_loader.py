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

    HOLDOUT_METRICS = {
        "linear_metric_epoch4": {
            "jp_score": 0.6050,
            "jp_note": "best holdout",
            "language_dominance": 0.5795,
            "citation_independence": 34.95,
            "design_pattern": "HIGH-PURITY",
            "epoch": 4,
        },
        "mahalanobis_metric_epoch4": {
            "jp_score": 0.5850,
            "language_dominance": 0.5810,
            "citation_independence": 35.2,
            "design_pattern": "HIGH-PURITY",
            "epoch": 4,
        },
        "hybrid_stabilized_epoch1": {
            "jp_score": 0.5150,
            "language_dominance": 0.6050,
            "citation_independence": 36.95,
            "design_pattern": "HIGH-PURITY",
            "epoch": 1,
        },
        "cited_decisions_tfidf": {
            "jp_score": 0.6922,
            "jp_note": "train (no holdout available)",
            "language_dominance": 0.6107,
            "citation_independence": None,
            "design_pattern": "HIGH-ADVANTAGE",
        },
        "cited_outcome_hybrid_0.5": {
            "jp_score": 0.7990,
            "jp_note": "train (no holdout available), PRODUCTION DEFAULT per v15b-audit",
            "language_dominance": 0.4911,
            "citation_independence": None,
            "design_pattern": "DEFAULT",
        },
        "cited_outcome_hybrid_0.7": {
            "jp_score": 0.7907,
            "jp_note": "train (no holdout available), BEST FRACTAL",
            "language_dominance": 0.4907,
            "citation_independence": None,
            "design_pattern": "DEFAULT",
        },
        "center_projected_64dim_hierarchical": {
            "jp_score": 0.512,
            "language_dominance": 0.766,
            "citation_independence": None,
            "design_pattern": "LEGACY-DEFAULT",
        },
        "following_alpha0.3": {
            "jp_score": 0.5188,
            "language_dominance": 0.7530,
            "citation_independence": None,
            "design_pattern": "CITATION-ROLE",
        },
        "criticizing_alpha0.3": {
            "jp_score": None,
            "jp_note": "not reported",
            "language_dominance": None,
            "citation_independence": None,
            "design_pattern": "CITATION-ROLE",
        },
        "citing_alpha0.3": {
            "jp_score": 0.5363,
            "language_dominance": 0.7414,
            "citation_independence": None,
            "design_pattern": "CITATION-ROLE",
        },
    }

    DESIGN_PATTERNS = {
        "DEFAULT": {
            "representations": ["cited_outcome_hybrid_0.5"],
            "description": "PRODUCTION DEFAULT per v15b-audit CRITICAL. Wins full-harness LangDom/JuristPref/Boilerplate. Best for user-imported corpora where branch metadata unavailable.",
            "strengths": ["full-harness winner", "LangDom/JuristPref/Boilerplate", "production-ready", "user-import ready"],
            "use_when": "General-purpose legal-case clustering; default choice. Wins full-harness evaluation vs center_projected_64dim_hierarchical.",
        },
        "LEGACY-DEFAULT": {
            "representations": ["center_projected_64dim_hierarchical"],
            "description": "LEGACY DEFAULT (factory direction v6). 64-dim frozen PCA. Both adversarial gates PASS. Replaced by cited_outcome_hybrid_0.5 per v15b-audit.",
            "strengths": ["passes adversarial gates", "language-debiased", "balanced metrics"],
            "use_when": "Legacy comparison; when language-debiased PCA embeddings are specifically needed.",
        },
        "HIGH-PURITY": {
            "representations": ["linear_metric_epoch4", "mahalanobis_metric_epoch4", "hybrid_stabilized_epoch1"],
            "description": "Metric learning representations. Best for citation-independent retrieval. Achieves 2.5x citation-independent retrieval vs zero-shot hybrids.",
            "strengths": ["citation-independent retrieval", "high purity", "legal-distance metric learning"],
            "use_when": "Citation-independent retrieval, cases where citation features are unavailable or unreliable.",
        },
        "HIGH-ADVANTAGE": {
            "representations": ["cited_decisions_tfidf", "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7"],
            "description": "Citation/outcome representations. Best for cross-lingual alignment. Highest JP scores on train set.",
            "strengths": ["cross-lingual alignment", "highest JP scores", "citation-informed features"],
            "use_when": "Cross-lingual alignment, fractal quality analysis, when citation data is available and reliable.",
        },
        "CITATION-ROLE": {
            "representations": ["following_alpha0.3", "criticizing_alpha0.3", "citing_alpha0.3"],
            "description": "Citation role embeddings. Encode the semantic role of citations (following, criticizing, citing).",
            "strengths": ["citation role semantics", "directional citation features"],
            "use_when": "Analyzing citation relationships and argumentative structure between cases.",
        },
    }

    RECOMMENDATIONS = {
        "production": {
            "representation": "cited_outcome_hybrid_0.5",
            "pattern": "DEFAULT",
            "rationale": "PRODUCTION DEFAULT per v15b-audit CRITICAL. Wins full-harness LangDom/JuristPref/Boilerplate. Best for user-imported corpora where branch metadata unavailable.",
        },
        "citation_independent": {
            "representation": "linear_metric_epoch4",
            "pattern": "HIGH-PURITY",
            "rationale": "Best holdout JP (0.6050) among citation-independent representations. 2.5x retrieval improvement over zero-shot hybrids.",
        },
        "cross_lingual": {
            "representation": "cited_outcome_hybrid_0.5",
            "pattern": "DEFAULT",
            "rationale": "PRODUCTION DEFAULT per v15b-audit. Wins full-harness LangDom/JuristPref/Boilerplate.",
        },
        "fractal_quality": {
            "representation": "cited_outcome_hybrid_0.7",
            "pattern": "DEFAULT",
            "rationale": "Best fractal representation. Highest JP (0.7907 train) with deep hierarchical structure. DEFAULT pattern per v15b-audit.",
        },
        "default": {
            "representation": "cited_outcome_hybrid_0.5",
            "pattern": "DEFAULT",
            "rationale": "PRODUCTION DEFAULT per v15b-audit. Wins full-harness LangDom/JuristPref/Boilerplate.",
        },
        "best_stable_combination": {
            "representation": "linear_hybrid05_concat",
            "pattern": "COMBINATION",
            "rationale": "v15b ACCEPTED: JP=0.838, std=0.027, BEST STABLE combination. Beats all zero-shot hybrids. For doctrinal/Jurivoc exploration.",
        },
    }

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
            "design_patterns": self.get_design_patterns(),
            "holdout_validation": self.get_holdout_metrics(),
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

    def get_holdout_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return holdout-validated metrics per representation.

        These are the ground truth about representation quality from
        legal-distance v9 experiments.
        """
        return self.HOLDOUT_METRICS

    def get_design_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Return design pattern classification for representations.

        Patterns group representations by their construction approach
        and optimal use case.
        """
        return self.DESIGN_PATTERNS

    def get_representation_recommendation(self, purpose: str) -> Dict[str, Any]:
        """Return recommended representation for a given purpose.

        Purposes:
            - "production": general-purpose production use
            - "citation_independent": retrieval without citation features
            - "cross_lingual": cross-language alignment
            - "fractal_quality": deep hierarchical structure
            - "default": same as production

        Returns dict with representation name, design pattern, and rationale.
        """
        purpose = purpose.lower().strip()
        if purpose not in self.RECOMMENDATIONS:
            valid = ", ".join(sorted(self.RECOMMENDATIONS.keys()))
            return {"error": f"Unknown purpose '{purpose}'. Valid purposes: {valid}"}
        return self.RECOMMENDATIONS[purpose]

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
