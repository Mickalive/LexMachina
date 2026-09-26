"""
LexMachina Proximity Explainer
Computes feature-level explanations for why two legal decisions are
neighbors on the map.

The baseline representation groups primarily by language (dominance 0.982),
not legal content. This module decomposes proximity into interpretable
features so users understand WHAT drives similarity — and whether it's
legally meaningful.
"""
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from .corpus_loader import CorpusLoader, Decision


# Feature weights reflecting legal relevance, NOT baseline dominance.
# Language is intentionally downweighted — it's the known confound.
FEATURE_WEIGHTS: Dict[str, float] = {
    "language": 0.15,
    "branch": 0.25,
    "legal_area": 0.20,
    "citation_overlap": 0.20,
    "text_length": 0.05,
    "date_proximity": 0.15,
}


@dataclass
class FeatureContribution:
    """A single feature's contribution to proximity."""
    feature: str
    match: bool
    contribution: float
    weight: float
    detail: str = ""


@dataclass
class ProximityExplanation:
    """Structured explanation of why two decisions are neighbors."""
    decision_a: str
    decision_b: str
    distance: float
    proximity_score: float
    feature_contributions: List[FeatureContribution]
    warnings: List[str]
    suggested_views: List[str]
    summary: str


def _extract_year(date_str: str) -> Optional[int]:
    """Extract a 4-digit year from a date string (YYYY-MM-DD or YYYY)."""
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, IndexError):
        return None


def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _length_similarity(len_a: int, len_b: int) -> float:
    """Compute similarity based on relative text length difference.

    Returns 1.0 for identical lengths, approaching 0.0 for large differences.
    Uses a logistic-like curve so small differences don't matter much.
    """
    if len_a == 0 and len_b == 0:
        return 1.0
    max_len = max(len_a, len_b)
    min_len = min(len_a, len_b)
    if max_len == 0:
        return 1.0
    ratio = min_len / max_len
    return ratio


class ProximityExplainer:
    """Explains why two decisions are neighbors on the map."""

    def __init__(self, corpus: CorpusLoader):
        self.corpus = corpus
        self.weights = FEATURE_WEIGHTS

    def explain(
        self,
        decision_id_a: str,
        decision_id_b: str,
        distance: float = 0.0,
    ) -> Dict:
        """Compute proximity explanation between two decisions.

        Args:
            decision_id_a: First decision ID.
            decision_id_b: Second decision ID.
            distance: The distance score from the map projection.

        Returns:
            Dict with decision identifiers, proximity score, feature
            contributions, warnings, suggested views, and a summary.
        """
        dec_a = self.corpus.get(decision_id_a)
        dec_b = self.corpus.get(decision_id_b)

        # Convert Decision objects to dicts for uniform handling
        if dec_a is not None and hasattr(dec_a, 'language'):
            # It's a Decision object, convert to dict
            dec_a = {
                'language': dec_a.language,
                'branch': dec_a.branch,
                'legal_area': dec_a.legal_area,
                'cited_decisions': dec_a.cited_decisions,
                'cited_laws': dec_a.cited_laws,
                'text_length': dec_a.text_length,
                'decision_date': dec_a.decision_date,
            }
        if dec_b is not None and hasattr(dec_b, 'language'):
            dec_b = {
                'language': dec_b.language,
                'branch': dec_b.branch,
                'legal_area': dec_b.legal_area,
                'cited_decisions': dec_b.cited_decisions,
                'cited_laws': dec_b.cited_laws,
                'text_length': dec_b.text_length,
                'decision_date': dec_b.decision_date,
            }

        if dec_a is None or dec_b is None:
            missing = decision_id_a if dec_a is None else decision_id_b
            return self._error_result(
                decision_id_a, decision_id_b, distance,
                f"Decision not found: {missing}",
            )

        contributions = self._compute_contributions(dec_a, dec_b)
        proximity_score = self._compute_proximity_score(contributions)
        warnings = self._generate_warnings(contributions, dec_a, dec_b)
        suggested_views = self._suggest_views(contributions)
        summary = self._build_summary(
            dec_a, dec_b, proximity_score, contributions, warnings,
        )

        return {
            "decision_a": decision_id_a,
            "decision_b": decision_id_b,
            "distance": distance,
            "proximity_score": round(proximity_score, 4),
            "feature_contributions": [
                {
                    "feature": c.feature,
                    "match": c.match,
                    "contribution": round(c.contribution, 4),
                    "weight": c.weight,
                    "detail": c.detail,
                }
                for c in contributions
            ],
            "warnings": warnings,
            "suggested_views": suggested_views,
            "summary": summary,
        }

    def _compute_contributions(
        self, dec_a: Dict, dec_b: Dict,
    ) -> List[FeatureContribution]:
        """Compute each feature's contribution to proximity."""
        contributions: List[FeatureContribution] = []

        def get_val(d, key, default=None):
            """Get value from dict or object."""
            if isinstance(d, dict):
                return d.get(key, default)
            return getattr(d, key, default)

        # Language match
        lang_a = get_val(dec_a, 'language', 'unknown')
        lang_b = get_val(dec_b, 'language', 'unknown')
        lang_match = lang_a == lang_b
        lang_contrib = self.weights["language"] if lang_match else 0.0
        contributions.append(FeatureContribution(
            feature="language",
            match=lang_match,
            contribution=lang_contrib,
            weight=self.weights["language"],
            detail=f"Both in {lang_a}" if lang_match
            else f"{lang_a} vs {lang_b}",
        ))

        # Branch match
        branch_a = get_val(dec_a, 'branch')
        branch_b = get_val(dec_b, 'branch')
        branch_match = (
            branch_a is not None
            and branch_b is not None
            and branch_a == branch_b
        )
        branch_contrib = self.weights["branch"] if branch_match else 0.0
        contributions.append(FeatureContribution(
            feature="branch",
            match=branch_match,
            contribution=branch_contrib,
            weight=self.weights["branch"],
            detail=f"Both in {branch_a}" if branch_match
            else f"{branch_a or 'unknown'} vs {branch_b or 'unknown'}",
        ))

        # Legal area match
        area_a = get_val(dec_a, 'legal_area')
        area_b = get_val(dec_b, 'legal_area')
        area_match = (
            area_a is not None
            and area_b is not None
            and area_a == area_b
        )
        area_contrib = self.weights["legal_area"] if area_match else 0.0
        contributions.append(FeatureContribution(
            feature="legal_area",
            match=area_match,
            contribution=area_contrib,
            weight=self.weights["legal_area"],
            detail=f"Both in {area_a}" if area_match
            else f"{area_a or 'unknown'} vs {area_b or 'unknown'}",
        ))

        # Citation overlap (Jaccard over cited_decisions + cited_laws)
        cited_a = get_val(dec_a, 'cited_decisions', [])
        laws_a = get_val(dec_a, 'cited_laws', [])
        cited_b = get_val(dec_b, 'cited_decisions', [])
        laws_b = get_val(dec_b, 'cited_laws', [])
        citations_a = set(cited_a) | set(laws_a)
        citations_b = set(cited_b) | set(laws_b)
        citation_sim = _jaccard_similarity(citations_a, citations_b)
        citation_contrib = self.weights["citation_overlap"] * citation_sim
        shared_count = len(citations_a & citations_b)
        contributions.append(FeatureContribution(
            feature="citation_overlap",
            match=citation_sim > 0.0,
            contribution=citation_contrib,
            weight=self.weights["citation_overlap"],
            detail=f"{shared_count} shared references (Jaccard: {citation_sim:.3f})",
        ))

        # Text length similarity
        len_a = get_val(dec_a, 'text_length', 0)
        len_b = get_val(dec_b, 'text_length', 0)
        len_sim = _length_similarity(len_a, len_b)
        len_contrib = self.weights["text_length"] * len_sim
        contributions.append(FeatureContribution(
            feature="text_length",
            match=len_sim > 0.8,
            contribution=len_contrib,
            weight=self.weights["text_length"],
            detail=f"{len_a} vs {len_b} chars (sim: {len_sim:.3f})",
        ))

        # Date proximity (same year)
        date_a = get_val(dec_a, 'decision_date', '')
        date_b = get_val(dec_b, 'decision_date', '')
        year_a = _extract_year(date_a)
        year_b = _extract_year(date_b)
        if year_a is not None and year_b is not None:
            year_match = year_a == year_b
            date_contrib = self.weights["date_proximity"] if year_match else 0.0
            detail = (
                f"Both {year_a}" if year_match
                else f"{year_a} vs {year_b}"
            )
        else:
            year_match = False
            date_contrib = 0.0
            detail = "Date unavailable"

        contributions.append(FeatureContribution(
            feature="date_proximity",
            match=year_match,
            contribution=date_contrib,
            weight=self.weights["date_proximity"],
            detail=detail,
        ))

        return contributions

    def _compute_proximity_score(
        self, contributions: List[FeatureContribution],
    ) -> float:
        """Compute overall proximity score (0-1, higher = more similar)."""
        total_weight = sum(c.weight for c in contributions)
        if total_weight == 0:
            return 0.0
        return sum(c.contribution for c in contributions) / total_weight

    def _generate_warnings(
        self,
        contributions: List[FeatureContribution],
        dec_a: Decision,
        dec_b: Decision,
    ) -> List[str]:
        """Generate warnings when proximity is driven by non-legal features."""
        warnings: List[str] = []

        total_contribution = sum(c.contribution for c in contributions)
        if total_contribution == 0:
            warnings.append("No matching features found — decisions are dissimilar.")
            return warnings

        lang_contrib = next(
            c for c in contributions if c.feature == "language"
        ).contribution
        lang_ratio = lang_contrib / total_contribution if total_contribution else 0.0

        if lang_ratio > 0.6:
            warnings.append(
                "Proximity driven primarily by language match, not legal content. "
                f"Language accounts for {lang_ratio:.0%} of similarity."
            )
        elif lang_ratio > 0.4:
            warnings.append(
                "Language match is a significant contributor to proximity. "
                f"Language accounts for {lang_ratio:.0%} of similarity."
            )

        branch_contrib = next(
            c for c in contributions if c.feature == "branch"
        ).contribution
        area_contrib = next(
            c for c in contributions if c.feature == "legal_area"
        ).contribution
        citation_contrib = next(
            c for c in contributions if c.feature == "citation_overlap"
        ).contribution
        legal_total = branch_contrib + area_contrib + citation_contrib
        legal_ratio = legal_total / total_contribution if total_contribution else 0.0

        if legal_ratio < 0.2:
            warnings.append(
                "Weak legal-content overlap. These decisions may share surface "
                "features (language, length) without substantive legal similarity."
            )

        return warnings

    def _suggest_views(
        self, contributions: List[FeatureContribution],
    ) -> List[str]:
        """Suggest alternative map views based on the explanation."""
        suggestions: List[str] = []

        lang_contrib = next(
            c for c in contributions if c.feature == "language"
        ).contribution
        total = sum(c.contribution for c in contributions)
        lang_ratio = lang_contrib / total if total else 0.0

        if lang_ratio > 0.4:
            suggestions.append(
                "Try erwaegungen mode for reasoning-based proximity"
            )

        citation_contrib = next(
            c for c in contributions if c.feature == "citation_overlap"
        ).contribution
        if citation_contrib < 0.05:
            suggestions.append(
                "Citation overlap is low — these decisions address different legal "
                "authorities"
            )

        area_match = next(
            c for c in contributions if c.feature == "legal_area"
        ).match
        if not area_match:
            suggestions.append(
                "Legal areas differ — consider filtering by legal_area to find "
                "topically related decisions"
            )

        branch_match = next(
            c for c in contributions if c.feature == "branch"
        ).match
        if not branch_match:
            suggestions.append(
                "Branches differ — these decisions come from different legal domains"
            )

        return suggestions

    def _build_summary(
        self,
        dec_a: Decision,
        dec_b: Decision,
        proximity_score: float,
        contributions: List[FeatureContribution],
        warnings: List[str],
    ) -> str:
        """Build a human-readable summary of the explanation."""
        matching = [c for c in contributions if c.match]
        non_matching = [c for c in contributions if not c.match]

        parts = []
        parts.append(
            f"Similarity: {proximity_score:.0%} "
            f"({len(matching)}/{len(contributions)} features match)"
        )

        if matching:
            labels = ", ".join(c.feature for c in matching)
            parts.append(f"Matching: {labels}")

        if non_matching:
            labels = ", ".join(c.feature for c in non_matching)
            parts.append(f"Different: {labels}")

        if warnings:
            parts.append(f"Note: {warnings[0]}")

        return ". ".join(parts) + "."

    def _error_result(
        self,
        decision_id_a: str,
        decision_id_b: str,
        distance: float,
        message: str,
    ) -> Dict:
        """Return an error result when inputs are invalid."""
        return {
            "decision_a": decision_id_a,
            "decision_b": decision_id_b,
            "distance": distance,
            "proximity_score": 0.0,
            "feature_contributions": [],
            "warnings": [message],
            "suggested_views": [],
            "summary": f"Error: {message}",
        }
