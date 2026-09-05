"""
Language Analyzer
Analyzes language dominance in clusters and provides cross-language neighbor discovery.
Addresses evaluation finding that baseline representation is FALSIFIED by language dominance (0.982).
"""
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any


class LanguageAnalyzer:
    """Analyzes language dominance and discovers cross-language neighbors."""

    def __init__(self):
        pass

    def analyze_cluster_language_dominance(
        self,
        cluster_decisions: List[Dict],
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Analyze language dominance within a cluster.

        Args:
            cluster_decisions: List of decision dicts with 'language' field
            cluster_id: The cluster identifier

        Returns:
            Dict with language distribution, dominance score, and warnings
        """
        if not cluster_decisions:
            return {
                "cluster_id": cluster_id,
                "n_decisions": 0,
                "language_distribution": {},
                "dominant_language": None,
                "language_dominance": 0.0,
                "warning": "Empty cluster",
            }

        languages = [d.get("language", "unknown") for d in cluster_decisions]
        lang_counter = Counter(languages)
        total = len(languages)

        dominant_lang, dominant_count = lang_counter.most_common(1)[0]
        dominance_score = dominant_count / total

        # Generate warning if dominated by single language
        warning = None
        if dominance_score > 0.9:
            warning = f"Cluster dominated by single language: {dominant_lang} ({dominance_score:.1%})"
        elif dominance_score > 0.7:
            warning = f"Cluster predominantly {dominant_lang} ({dominance_score:.1%})"

        return {
            "cluster_id": cluster_id,
            "n_decisions": total,
            "language_distribution": dict(lang_counter),
            "dominant_language": dominant_lang,
            "language_dominance": round(dominance_score, 3),
            "warning": warning,
            "is_language_dominant": dominance_score > 0.9,
        }

    def find_cross_language_neighbors(
        self,
        decision_id: str,
        decision_language: str,
        all_positions: Dict[str, Tuple[float, float]],
        corpus_summaries: Dict[str, Dict],
        n_neighbors: int = 10,
        same_language_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find neighbors of a decision using spatial (2D) distance.

        Args:
            decision_id: The target decision
            decision_language: Language of the target decision
            all_positions: Dict mapping decision_id -> (x, y)
            corpus_summaries: Dict mapping decision_id -> summary dict
            n_neighbors: Number of neighbors to return
            same_language_only: If True, only return same-language neighbors

        Returns:
            List of neighbor dicts with distance and language info
        """
        if decision_id not in all_positions:
            return []

        target_pos = all_positions[decision_id]
        neighbors = []

        for did, pos in all_positions.items():
            if did == decision_id:
                continue

            summary = corpus_summaries.get(did, {})
            lang = summary.get("language", "unknown")

            # Filter by language if requested
            if same_language_only and lang != decision_language:
                continue

            # Calculate distance
            dist = ((pos[0] - target_pos[0]) ** 2 + (pos[1] - target_pos[1]) ** 2) ** 0.5

            neighbors.append({
                "decision_id": did,
                "distance": round(dist, 4),
                "language": lang,
                "is_cross_language": lang != decision_language,
                "branch": summary.get("branch", "unknown"),
                "legal_area": summary.get("legal_area", "unknown"),
            })

        # Sort by distance
        neighbors.sort(key=lambda x: x["distance"])

        return neighbors[:n_neighbors]

    def find_cross_language_neighbors_by_text(
        self,
        decision_id: str,
        decision_language: str,
        tfidf_model: Any,
        corpus_summaries: Dict[str, Dict],
        all_positions: Dict[str, Tuple[float, float]],
        n_neighbors: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find cross-language neighbors using TF-IDF text similarity.

        Overcomes the language-dominant clustering problem by ranking
        candidates by topical text similarity rather than 2D spatial
        proximity (which is dominated by language).

        Args:
            decision_id: The target decision
            decision_language: Language of the target decision
            tfidf_model: TFIDFProximity instance with built model
            corpus_summaries: Dict mapping decision_id -> summary dict
            all_positions: Dict mapping decision_id -> (x, y) for position info
            n_neighbors: Number of cross-language neighbors to return

        Returns:
            List of cross-language neighbor dicts ranked by text similarity
        """
        if not tfidf_model._built:
            return []

        # Get the target document's TF-IDF vector
        target_vec = tfidf_model._tfidf_vectors.get(decision_id)
        if not target_vec:
            return []

        # Compute text similarity against all other documents
        candidates = []
        for did, vec in tfidf_model._tfidf_vectors.items():
            if did == decision_id:
                continue

            summary = corpus_summaries.get(did, {})
            lang = summary.get("language", "unknown")

            # Only cross-language candidates
            if lang == decision_language:
                continue

            # Compute cosine similarity
            dot_product = sum(
                target_vec.get(idx, 0.0) * vec.get(idx, 0.0)
                for idx in target_vec
                if idx in vec
            )
            mag_target = sum(v ** 2 for v in target_vec.values()) ** 0.5
            mag_candidate = sum(v ** 2 for v in vec.values()) ** 0.5

            if mag_target == 0 or mag_candidate == 0:
                continue

            text_sim = dot_product / (mag_target * mag_candidate)

            pos = all_positions.get(did, (0, 0))
            candidates.append({
                "decision_id": did,
                "text_similarity": round(text_sim, 4),
                "distance": round(1.0 - text_sim, 4),  # Invert for distance convention
                "language": lang,
                "is_cross_language": True,
                "branch": summary.get("branch", "unknown"),
                "legal_area": summary.get("legal_area", "unknown"),
                "x": pos[0],
                "y": pos[1],
            })

        # Sort by text similarity (highest first = lowest distance)
        candidates.sort(key=lambda x: x["text_similarity"], reverse=True)

        return candidates[:n_neighbors]

    def get_language_filter_recommendations(
        self,
        cluster_decisions: List[Dict],
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Provide recommendations for language filtering in a cluster.

        Args:
            cluster_decisions: List of decision dicts with 'language' field
            cluster_id: The cluster identifier

        Returns:
            Dict with filtering recommendations
        """
        if not cluster_decisions:
            return {
                "cluster_id": cluster_id,
                "recommendations": [],
                "suggested_filter": None,
            }

        languages = [d.get("language", "unknown") for d in cluster_decisions]
        lang_counter = Counter(languages)
        total = len(languages)

        recommendations = []
        suggested_filter = None

        # Check if cluster is language-dominant
        if lang_counter:
            dominant_lang, dominant_count = lang_counter.most_common(1)[0]
            dominance = dominant_count / total

            if dominance > 0.9:
                # Cluster is dominated by one language
                other_langs = [lang for lang, count in lang_counter.items() if lang != dominant_lang]
                if other_langs:
                    recommendations.append({
                        "type": "language_filter",
                        "message": f"Filter to {dominant_lang} to see the dominant legal domain",
                        "filter": [dominant_lang],
                    })
                    recommendations.append({
                        "type": "cross_language_exploration",
                        "message": f"Filter to {', '.join(other_langs)} to explore cross-language structure",
                        "filter": other_langs,
                    })
                    suggested_filter = [dominant_lang]
            elif dominance > 0.7:
                recommendations.append({
                    "type": "mixed_language_cluster",
                    "message": f"Mixed language cluster with {dominant_lang} dominant. Consider language filtering to explore sub-structure.",
                    "filter": [dominant_lang],
                })

        return {
            "cluster_id": cluster_id,
            "recommendations": recommendations,
            "suggested_filter": suggested_filter,
            "language_distribution": dict(lang_counter),
        }
