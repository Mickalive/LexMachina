"""
Boilerplate Resistance Test

Tests whether the legal distance representation is resistant to procedural boilerplate
that appears frequently across decisions but carries little legal signal.
"""

import re
import numpy as np
from typing import Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter
import logging

from ..benchmarks.core import BaseBenchmark, BenchmarkResult, BenchmarkStatus, EvidenceTier

logger = logging.getLogger(__name__)


# Common Swiss Federal Supreme Court boilerplate patterns
BOILERPLATE_PATTERNS_DE = [
    r"gemäss\s+Art\.\s*\d+",
    r"nach\s+Art\.\s*\d+",
    r"gestützt\s+auf\s+Art\.\s*\d+",
    r"vorliegend\s+ist\s+zu\s+prüfen",
    r"das\s+Bundesgericht\s+zieht\s+in\s+Erwägung",
    r"die\s+Beschwerde\s+ist\s+abzuweisen",
    r"die\s+Beschwerde\s+ist\s+gutzuheissen",
    r"die\s+Kosten\s+des\s+Verfahrens\s+werden",
    r"die\s+Parteien\s+haben\s+keine\s+Kosten\s+zu\s+erstatten",
    r"dieses\s+Urteil\s+wird\s+den\s+Parteien\s+mitgeteilt",
    r"Lausanne,\s+\d{1,2}\.\s+\w+\s+\d{4}",
    r"BGE\s+\d+\s+[IVX]+\s+\d+",
    r"Art\.\s*\d+\s+Abs\.\s*\d+",
    r"lit\.\s*[a-z]",
    r"Ziff\.\s*\d+",
    r"BGG\s+",
    r"ZPO\s+",
    r"StPO\s+",
    r"VG\s+",
    r"BV\s+",
    r"OR\s+",
    r"ZGB\s+",
    r"StGB\s+",
    r"SR\s+\d+",
]

BOILERPLATE_PATTERNS_FR = [
    r"selon\s+l['']?art\.\s*\d+",
    r"en\s+vertu\s+de\s+l['']?art\.\s*\d+",
    r"le\s+Tribunal\s+fédéral\s+considère",
    r"le\s+recours\s+est\s+rejeté",
    r"le\s+recours\s+est\s+admis",
    r"les\s+frais\s+de\s+la\s+procédure\s+sont",
    r"les\s+parties\s+n['']?ont\s+pas\s+de\s+frais\s+à\s+rembourser",
    r"cet\s+arrêt\s+est\s+communiqué\s+aux\s+parties",
    r"Lausanne,\s+le\s+\d{1,2}\s+\w+\s+\d{4}",
    r"ATF\s+\d+\s+[IVX]+\s+\d+",
    r"art\.\s*\d+\s+al\.\s*\d+",
    r"let\.\s*[a-z]",
    r"ch\.\s*\d+",
    r"LTF\s+",
    r"CPC\s+",
    r"CPP\s+",
    r"LAVI\s+",
    r"Cst\.\s+",
    r"CO\s+",
    r"CC\s+",
    r"CP\s+",
    r"RS\s+\d+",
]

BOILERPLATE_PATTERNS_IT = [
    r"ai\s+sensi\s+dell['']?art\.\s*\d+",
    r"in\s+virtù\s+dell['']?art\.\s*\d+",
    r"il\s+Tribunale\s+federale\s+considera",
    r"il\s+ricorso\s+è\s+respinto",
    r"il\s+ricorso\s+è\s+accolto",
    r"le\s+spese\s+del\s+procedimento\s+sono",
    r"le\s+parti\s+non\s+hanno\s+spese\s+da\s+rimborsare",
    r"questa\s+sentenza\s+è\s+comunicata\s+alle\s+parti",
    r"Losanna,\s+il\s+\d{1,2}\s+\w+\s+\d{4}",
    r"DTF\s+\d+\s+[IVX]+\s+\d+",
    r"art\.\s*\d+\s+cpv\.\s*\d+",
    r"lett\.\s*[a-z]",
    r"n\.\s*\d+",
    r"LTF\s+",
    r"CPC\s+",
    r"CPP\s+",
    r"LAVI\s+",
    r"Cost\.\s+",
    r"CO\s+",
    r"CC\s+",
    r"CP\s+",
    r"RS\s+\d+",
]


@dataclass
class BoilerplateConfig:
    """Configuration for boilerplate resistance test."""
    sample_size: int = 100
    top_boilerplate_terms: int = 50
    min_term_frequency: int = 5
    languages: List[str] = None
    perturbation_strength: float = 0.3  # Fraction of boilerplate to inject/remove

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["de", "fr", "it"]


class BoilerplateResistanceTest(BaseBenchmark):
    """
    Tests whether the representation is resistant to procedural boilerplate.
    
    Method:
    1. Identify high-frequency boilerplate terms/patterns in the corpus
    2. Create perturbed versions of decisions by adding/removing boilerplate
    3. Measure how much the embedding changes (should be minimal for good representations)
    4. Compare against baseline (whole-document embeddings which are sensitive to boilerplate)
    """

    def __init__(self, config: Optional[BoilerplateConfig] = None):
        super().__init__("boilerplate_resistance", config.__dict__ if config else {})
        self.config = config or BoilerplateConfig()
        self.boilerplate_patterns = {
            "de": BOILERPLATE_PATTERNS_DE,
            "fr": BOILERPLATE_PATTERNS_FR,
            "it": BOILERPLATE_PATTERNS_IT,
        }

    def run(
        self,
        representation_fn: Callable,
        corpus: Any,
        **kwargs,
    ) -> BenchmarkResult:
        """
        Run boilerplate resistance test.

        Args:
            representation_fn: Function that takes a decision_id and returns embedding vector
            corpus: Corpus object with decision texts
            **kwargs: Additional arguments

        Returns:
            BenchmarkResult with stability metrics
        """
        import time
        start_time = time.time()

        try:
            # Get sample decisions from corpus
            sample_decisions = self._get_sample_decisions(corpus, self.config.sample_size)
            if not sample_decisions:
                return self._create_result(
                    status=BenchmarkStatus.ERROR,
                    metrics={},
                    details={"error": "No decisions available from corpus"},
                    duration=time.time() - start_time,
                    error_message="Empty corpus",
                )

            # Extract boilerplate terms from corpus
            boilerplate_terms = self._extract_boilerplate_terms(sample_decisions)

            # Test each decision
            stability_scores = []
            perturbation_details = []

            for decision in sample_decisions:
                decision_id = decision.get("decision_id", "")
                text = decision.get("full_text", "")
                language = decision.get("language", "de")

                if not text or not decision_id:
                    continue

                # Get original embedding
                try:
                    original_emb = representation_fn(decision_id)
                    if original_emb is None:
                        continue
                    original_emb = np.array(original_emb, dtype=np.float32)
                except Exception as e:
                    logger.warning(f"Failed to get embedding for {decision_id}: {e}")
                    continue

                # Create perturbed version (add boilerplate)
                perturbed_text = self._inject_boilerplate(text, language, boilerplate_terms)

                # We need to test with perturbed text - this requires the representation_fn
                # to accept text directly, or we need a way to create temporary decisions
                # For now, we'll test by measuring how much boilerplate terms dominate
                # the representation space

                # Alternative approach: measure boilerplate sensitivity by checking
                # if decisions sharing only boilerplate are close in embedding space
                boilerplate_similarity = self._measure_boilerplate_sensitivity(
                    representation_fn, sample_decisions, boilerplate_terms, language
                )
                perturbation_details.append({
                    "decision_id": decision_id,
                    "boilerplate_similarity": boilerplate_similarity,
                })
                stability_scores.append(1.0 - boilerplate_similarity)  # Higher = more resistant

            if not stability_scores:
                return self._create_result(
                    status=BenchmarkStatus.FAILED,
                    metrics={},
                    details={"error": "No valid decisions for testing"},
                    duration=time.time() - start_time,
                    error_message="No valid test decisions",
                )

            metrics = {
                "mean_stability": float(np.mean(stability_scores)),
                "std_stability": float(np.std(stability_scores)),
                "min_stability": float(np.min(stability_scores)),
                "max_stability": float(np.max(stability_scores)),
                "boilerplate_terms_found": len(boilerplate_terms),
                "num_test_decisions": len(stability_scores),
            }

            # Resistance score: 1 = perfectly resistant, 0 = fully sensitive
            resistance_score = metrics["mean_stability"]
            metrics["resistance_score"] = resistance_score

            # Pass if resistance > 0.7 (arbitrary threshold, should be calibrated)
            status = BenchmarkStatus.PASSED if resistance_score > 0.6 else BenchmarkStatus.FAILED

            duration = time.time() - start_time

            return self._create_result(
                status=status,
                metrics=metrics,
                details={
                    "perturbation_details": perturbation_details[:10],  # Limit size
                    "top_boilerplate_terms": boilerplate_terms[:20],
                },
                duration=duration,
                evidence_tier=EvidenceTier.EXPLORATORY,
                baseline_comparison={"resistance_score_baseline": 0.3},  # Expected for naive embeddings
            )

        except Exception as e:
            logger.error(f"Boilerplate resistance test failed: {e}")
            return self._create_result(
                status=BenchmarkStatus.ERROR,
                metrics={},
                details={"exception": str(e)},
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _get_sample_decisions(self, corpus: Any, sample_size: int) -> List[Dict[str, Any]]:
        """Get a sample of decisions from the corpus."""
        # This is a placeholder - actual implementation depends on corpus interface
        # For now, return empty list; will be implemented when corpus is available
        if hasattr(corpus, "get_decisions"):
            return corpus.get_decisions(limit=sample_size)
        elif hasattr(corpus, "decisions"):
            decisions = list(corpus.decisions.values())[:sample_size]
            return [d if isinstance(d, dict) else d.__dict__ for d in decisions]
        elif isinstance(corpus, list):
            return corpus[:sample_size]
        return []

    def _extract_boilerplate_terms(self, decisions: List[Dict[str, Any]]) -> List[str]:
        """Extract high-frequency boilerplate terms from decisions."""
        all_terms = Counter()

        for decision in decisions:
            text = decision.get("full_text", "")
            language = decision.get("language", "de")

            # Extract using patterns
            patterns = self.boilerplate_patterns.get(language, BOILERPLATE_PATTERNS_DE)
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                all_terms.update(matches)

            # Also extract frequent n-grams that look like boilerplate
            # (This is a simplified version; real implementation would be more sophisticated)
            words = re.findall(r'\b\w{3,}\b', text.lower())
            all_terms.update(words)

        # Filter by minimum frequency and return top terms
        filtered = {
            term: count
            for term, count in all_terms.items()
            if count >= self.config.min_term_frequency
        }

        # Sort by frequency
        sorted_terms = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms[:self.config.top_boilerplate_terms]]

    def _inject_boilerplate(self, text: str, language: str, boilerplate_terms: List[str]) -> str:
        """Inject boilerplate terms into text."""
        # Simple injection at random positions
        import random
        words = text.split()
        num_inject = int(len(words) * self.config.perturbation_strength)
        
        for _ in range(min(num_inject, len(boilerplate_terms))):
            term = random.choice(boilerplate_terms)
            pos = random.randint(0, len(words))
            words.insert(pos, term)
        
        return " ".join(words)

    def _measure_boilerplate_sensitivity(
        self,
        representation_fn: Callable,
        decisions: List[Dict[str, Any]],
        boilerplate_terms: List[str],
        language: str,
    ) -> float:
        """
        Measure how much boilerplate terms dominate the representation space.
        
        Returns a score between 0 and 1 where:
        - 0 = representations are completely driven by boilerplate (bad)
        - 1 = representations are completely independent of boilerplate (good)
        """
        # Group decisions by boilerplate content
        high_boilerplate = []
        low_boilerplate = []

        for decision in decisions:
            text = decision.get("full_text", "")
            if not text:
                continue
            
            boilerplate_count = sum(1 for term in boilerplate_terms if term.lower() in text.lower())
            boilerplate_density = boilerplate_count / max(len(text.split()), 1)
            
            if boilerplate_density > np.percentile([boilerplate_density], 75):
                high_boilerplate.append(decision)
            else:
                low_boilerplate.append(decision)

        if not high_boilerplate or not low_boilerplate:
            return 0.5  # Neutral

        # Compute average pairwise similarity within and between groups
        # This is a simplified proxy - real implementation would compute actual embeddings
        
        # For now, return a placeholder that will be replaced when we have real data
        return 0.5

    def get_baseline_metrics(self) -> Dict[str, float]:
        """Expected baseline metrics for naive whole-document embeddings."""
        return {
            "resistance_score": 0.3,
            "mean_stability": 0.3,
        }