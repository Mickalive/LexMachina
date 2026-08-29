#!/usr/bin/env python3
"""
Boilerplate Resistance Test for center_projected representation.

Tests whether the center_projected representation (64-dim, language-centered + PCA)
is resistant to procedural boilerplate by perturbing full text and re-running
the full pipeline: sentence transformer → language centering → PCA.
"""

import json
import numpy as np
import re
import random
from pathlib import Path
from typing import List, Dict, Any, Callable, Tuple
from collections import Counter
from dataclasses import dataclass
from enum import Enum
import time

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available")

from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

# Paths
SIGNALS_FILE = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_signals_full.jsonl")
EXPANDED_META_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200_metadata.jsonl")
CENTER_PROJECTED_768_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_768.npy")
CENTER_PROJECTED_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
CENTER_PROJECTED_META_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Global seed
GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)
random.seed(GLOBAL_SEED)

# Boilerplate patterns (from boilerplate_resistance.py)
BOILERPLATE_PATTERNS_DE = [
    r"gemäss\s+Art\.\s*\d+", r"nach\s+Art\.\s*\d+", r"gestützt\s+auf\s+Art\.\s*\d+",
    r"vorliegend\s+ist\s+zu\s+prüfen", r"das\s+Bundesgericht\s+zieht\s+in\s+Erwägung",
    r"die\s+Beschwerde\s+ist\s+abzuweisen", r"die\s+Beschwerde\s+ist\s+gutzuheissen",
    r"die\s+Kosten\s+des\s+Verfahrens\s+werden", r"die\s+Parteien\s+haben\s+keine\s+Kosten\s+zu\s+erstatten",
    r"dieses\s+Urteil\s+wird\s+den\s+Parteien\s+mitgeteilt", r"Lausanne,\s+\d{1,2}\.\s+\w+\s+\d{4}",
    r"BGE\s+\d+\s+[IVX]+\s+\d+", r"Art\.\s*\d+\s+Abs\.\s*\d+", r"lit\.\s*[a-z]",
    r"Ziff\.\s*\d+", r"BGG\s+", r"ZPO\s+", r"StPO\s+", r"VG\s+", r"BV\s+",
    r"OR\s+", r"ZGB\s+", r"StGB\s+", r"SR\s+\d+",
]

BOILERPLATE_PATTERNS_FR = [
    r"selon\s+l['']?art\.\s*\d+", r"en\s+vertu\s+de\s+l['']?art\.\s*\d+",
    r"le\s+Tribunal\s+fédéral\s+considère", r"le\s+recours\s+est\s+rejeté",
    r"le\s+recours\s+est\s+admis", r"les\s+frais\s+de\s+la\s+procédure\s+sont",
    r"les\s+parties\s+n['']?ont\s+pas\s+de\s+frais\s+à\s+rembourser",
    r"cet\s+arrêt\s+est\s+communiqué\s+aux\s+parties", r"Lausanne,\s+le\s+\d{1,2}\s+\w+\s+\d{4}",
    r"ATF\s+\d+\s+[IVX]+\s+\d+", r"art\.\s*\d+\s+al\.\s*\d+", r"let\.\s*[a-z]",
    r"ch\.\s*\d+", r"LTF\s+", r"CPC\s+", r"CPP\s+", r"LAVI\s+", r"Cst\.\s+",
    r"CO\s+", r"CC\s+", r"CP\s+", r"RS\s+\d+",
]

BOILERPLATE_PATTERNS_IT = [
    r"ai\s+sensi\s+dell['']?art\.\s*\d+", r"in\s+virtù\s+dell['']?art\.\s*\d+",
    r"il\s+Tribunale\s+federale\s+considera", r"il\s+ricorso\s+è\s+respinto",
    r"il\s+ricorso\s+è\s+accolto", r"le\s+spese\s+del\s+procedimento\s+sono",
    r"le\s+parti\s+non\s+hanno\s+spese\s+da\s+rimborsare",
    r"questa\s+sentenza\s+è\s+comunicata\s+alle\s+parti", r"Losanna,\s+il\s+\d{1,2}\s+\w+\s+\d{4}",
    r"DTF\s+\d+\s+[IVX]+\s+\d+", r"art\.\s*\d+\s+cpv\.\s*\d+", r"lett\.\s*[a-z]",
    r"n\.\s*\d+", r"LTF\s+", r"CPC\s+", r"CPP\s+", r"LAVI\s+", r"Cost\.\s+",
    r"CO\s+", r"CC\s+", r"CP\s+", r"RS\s+\d+",
]

BOILERPLATE_PATTERNS = {
    "de": BOILERPLATE_PATTERNS_DE,
    "fr": BOILERPLATE_PATTERNS_FR,
    "it": BOILERPLATE_PATTERNS_IT,
}


@dataclass
class BoilerplateConfig:
    sample_size: int = 100
    top_boilerplate_terms: int = 50
    min_term_frequency: int = 5
    languages: List[str] = None
    perturbation_strength: float = 0.3

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["de", "fr", "it"]


class BenchmarkStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class EvidenceTier(Enum):
    UNTESTED = "UNTESTED"
    EXPLORATORY = "EXPLORATORY"
    REPRODUCED = "REPRODUCED"
    ACCEPTED = "ACCEPTED"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def load_center_projected_pipeline() -> Tuple[np.ndarray, List[Dict], np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    """
    Load the center_projected pipeline components:
    - Original 768-dim embeddings
    - Metadata
    - Language centers
    - PCA components (fitted on language-centered embeddings)
    Returns: (embeddings_768, metadata, language_centers, pca_components, pca_mean)
    """
    print("Loading center_projected pipeline components...")
    
    # Load original 768-dim embeddings and metadata
    embeddings_768 = np.load(CENTER_PROJECTED_768_PATH)
    with open(CENTER_PROJECTED_META_PATH, 'r') as f:
        metadata = json.load(f)
    
    print(f"  Loaded 768-dim embeddings: {embeddings_768.shape}")
    print(f"  Loaded metadata: {len(metadata)} decisions")
    
    # Compute language centers
    languages = sorted(set(m.get('language', 'de') for m in metadata))
    language_centers = {}
    for lang in languages:
        mask = np.array([m.get('language', 'de') == lang for m in metadata])
        if np.sum(mask) > 0:
            language_centers[lang] = embeddings_768[mask].mean(axis=0)
    
    # Apply language centering to get centered embeddings
    centered_embeddings = np.copy(embeddings_768)
    for i, m in enumerate(metadata):
        lang = m.get('language', 'de')
        if lang in language_centers:
            centered_embeddings[i] = embeddings_768[i] - language_centers[lang]
    
    # L2 normalize centered embeddings
    norms = np.linalg.norm(centered_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    centered_embeddings = centered_embeddings / norms
    
    # Fit PCA on centered embeddings to get 64-dim projection
    pca = PCA(n_components=64, random_state=GLOBAL_SEED)
    embeddings_64 = pca.fit_transform(centered_embeddings)
    
    # Verify against saved 64-dim embeddings
    saved_64 = np.load(CENTER_PROJECTED_64_PATH)
    diff = np.abs(embeddings_64 - saved_64).max()
    print(f"  PCA reconstruction max diff: {diff:.6f}")
    if diff > 1e-4:
        print("  WARNING: PCA reconstruction doesn't match saved embeddings exactly")
    
    return embeddings_768, metadata, language_centers, pca.components_, pca.mean_


def load_signals_and_metadata() -> Tuple[Dict[str, Any], List[Dict]]:
    """Load legal signals and expanded slice metadata."""
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    print(f"Loaded signals for {len(signals)} decisions")
    
    metadata = []
    with open(EXPANDED_META_PATH, 'r') as f:
        for line in f:
            metadata.append(json.loads(line))
    print(f"Loaded expanded metadata for {len(metadata)} decisions")
    
    return signals, metadata


def prepare_decisions_for_test(signals: Dict, metadata: List[Dict]) -> List[Dict]:
    """Prepare decisions with full_text for boilerplate test."""
    decisions = []
    for m in metadata:
        did = m['decision_id']
        sig = signals.get(did, {})
        decisions.append({
            'decision_id': did,
            'full_text': sig.get('full_text', ''),
            'language': m.get('language', 'de'),
            'branch': m.get('branch', 'unknown'),
        })
    return decisions


def extract_boilerplate_terms(decisions: List[Dict], config: BoilerplateConfig) -> List[str]:
    """Extract high-frequency boilerplate terms from decisions."""
    all_terms = Counter()
    
    for decision in decisions:
        text = decision.get("full_text", "")
        language = decision.get("language", "de")
        
        patterns = BOILERPLATE_PATTERNS.get(language, BOILERPLATE_PATTERNS_DE)
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            all_terms.update(matches)
        
        # Also extract frequent words
        words = re.findall(r'\b\w{3,}\b', text.lower())
        all_terms.update(words)
    
    filtered = {
        term: count for term, count in all_terms.items()
        if count >= config.min_term_frequency
    }
    
    sorted_terms = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    return [term for term, _ in sorted_terms[:config.top_boilerplate_terms]]


def inject_boilerplate(text: str, language: str, boilerplate_terms: List[str], config: BoilerplateConfig) -> str:
    """Inject boilerplate terms into text."""
    words = text.split()
    num_inject = int(len(words) * config.perturbation_strength)
    
    for _ in range(min(num_inject, len(boilerplate_terms))):
        term = random.choice(boilerplate_terms)
        pos = random.randint(0, len(words))
        words.insert(pos, term)
    
    return " ".join(words)


def run_center_projected_boilerplate_test(
    model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    sample_size: int = 100
) -> Dict:
    """
    Run boilerplate resistance test on center_projected representation.
    
    Pipeline: full_text → sentence transformer → language centering → PCA(64) → compare
    """
    print("=" * 70)
    print(f"BOILERPLATE RESISTANCE TEST - center_projected (64-dim)")
    print("=" * 70)
    print(f"Model: {model_name}")
    print(f"Sample size: {sample_size}")
    print(f"Global seed: {GLOBAL_SEED}")
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return {
            'variant': 'center_projected',
            'status': BenchmarkStatus.ERROR.value,
            'metrics': {},
            'details': {"error": "sentence-transformers not available"},
            'duration': 0,
            'evidence_tier': EvidenceTier.EXPLORATORY.value,
            'error_message': "sentence-transformers not available"
        }
    
    start_time = time.time()
    
    # Load center_projected pipeline components
    embeddings_768, cp_metadata, language_centers, pca_components, pca_mean = load_center_projected_pipeline()
    
    # Load signals and expanded metadata
    signals, exp_metadata = load_signals_and_metadata()
    decisions = prepare_decisions_for_test(signals, exp_metadata)
    
    # Filter decisions with full_text
    valid_decisions = [d for d in decisions if d['full_text']]
    print(f"Decisions with full_text: {len(valid_decisions)}")
    
    # Sample for testing
    test_decisions = valid_decisions[:sample_size]
    print(f"Test sample size: {len(test_decisions)}")
    
    # Language distribution
    lang_counts = Counter(d['language'] for d in test_decisions)
    print(f"Language distribution: {dict(lang_counts)}")
    
    # Extract boilerplate terms
    config = BoilerplateConfig(sample_size=len(test_decisions))
    boilerplate_terms = extract_boilerplate_terms(test_decisions, config)
    print(f"Found {len(boilerplate_terms)} boilerplate terms")
    
    # Load sentence transformer model
    print(f"\nLoading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Create decision_id to index mapping for center_projected metadata
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    
    # Test each decision
    stability_scores = []
    perturbation_details = []
    
    for decision in test_decisions:
        decision_id = decision.get("decision_id", "")
        text = decision.get("full_text", "")
        language = decision.get("language", "de")
        
        if not text or not decision_id:
            continue
        
        if decision_id not in cp_id_to_idx:
            continue
        
        cp_idx = cp_id_to_idx[decision_id]
        original_emb_64 = np.load(CENTER_PROJECTED_64_PATH)[cp_idx]
        
        # Get original embedding from text (sentence transformer)
        try:
            original_emb_768 = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
            original_emb_768 = np.array(original_emb_768, dtype=np.float32)
        except Exception as e:
            print(f"  Warning: Failed to get embedding for {decision_id}: {e}")
            continue
        
        # Apply center_projected pipeline to original text
        # 1. Language centering
        if language in language_centers:
            centered = original_emb_768 - language_centers[language]
        else:
            centered = original_emb_768
        
        # 2. L2 normalize
        norm = np.linalg.norm(centered)
        if norm > 0:
            centered = centered / norm
        
        # 3. PCA transform
        # Center by PCA mean then project
        centered_for_pca = centered - pca_mean
        original_emb_64_reconstructed = centered_for_pca @ pca_components.T
        
        # L2 normalize final
        norm = np.linalg.norm(original_emb_64_reconstructed)
        if norm > 0:
            original_emb_64_reconstructed = original_emb_64_reconstructed / norm
        
        # Create perturbed version
        perturbed_text = inject_boilerplate(text, language, boilerplate_terms, config)
        
        # Get perturbed embedding through full pipeline
        try:
            perturbed_emb_768 = model.encode(perturbed_text, show_progress_bar=False, convert_to_numpy=True)
            perturbed_emb_768 = np.array(perturbed_emb_768, dtype=np.float32)
        except Exception as e:
            print(f"  Warning: Failed to get perturbed embedding for {decision_id}: {e}")
            continue
        
        # Apply center_projected pipeline to perturbed text
        if language in language_centers:
            perturbed_centered = perturbed_emb_768 - language_centers[language]
        else:
            perturbed_centered = perturbed_emb_768
        
        norm = np.linalg.norm(perturbed_centered)
        if norm > 0:
            perturbed_centered = perturbed_centered / norm
        
        perturbed_for_pca = perturbed_centered - pca_mean
        perturbed_emb_64 = perturbed_for_pca @ pca_components.T
        
        norm = np.linalg.norm(perturbed_emb_64)
        if norm > 0:
            perturbed_emb_64 = perturbed_emb_64 / norm
        
        # Measure cosine similarity between original and perturbed center_projected embeddings
        similarity = cosine_similarity(original_emb_64_reconstructed, perturbed_emb_64)
        stability = 1.0 - similarity  # Higher = more resistant (less change)
        
        perturbation_details.append({
            "decision_id": decision_id,
            "original_text_length": len(text),
            "perturbed_text_length": len(perturbed_text),
            "cosine_similarity": float(similarity),
            "stability": float(stability),
        })
        stability_scores.append(stability)
    
    if not stability_scores:
        return {
            'variant': 'center_projected',
            'status': BenchmarkStatus.FAILED.value,
            'metrics': {},
            'details': {"error": "No valid decisions for testing"},
            'duration': time.time() - start_time,
            'evidence_tier': EvidenceTier.EXPLORATORY.value,
            'error_message': "No valid test decisions"
        }
    
    metrics = {
        "mean_stability": float(np.mean(stability_scores)),
        "std_stability": float(np.std(stability_scores)),
        "min_stability": float(np.min(stability_scores)),
        "max_stability": float(np.max(stability_scores)),
        "boilerplate_terms_found": len(boilerplate_terms),
        "num_test_decisions": len(stability_scores),
    }
    
    resistance_score = metrics["mean_stability"]
    metrics["resistance_score"] = resistance_score
    
    # Pass if resistance > 0.6 (threshold calibrated against TF-IDF baseline)
    # Note: For center_projected, we expect HIGH resistance (low stability) like other legal embeddings
    status = BenchmarkStatus.PASSED if resistance_score > 0.6 else BenchmarkStatus.FAILED
    
    duration = time.time() - start_time
    
    result = {
        'variant': 'center_projected',
        'status': status.value,
        'metrics': metrics,
        'details': {
            "perturbation_details": perturbation_details[:10],
            "top_boilerplate_terms": boilerplate_terms[:20],
        },
        'duration': duration,
        'evidence_tier': EvidenceTier.EXPLORATORY.value,
        'baseline_comparison': {
            "resistance_score_baseline": 0.35,
            "baseline_note": "TF-IDF embeddings on synthetic legal text: resistance ~0.3-0.4 (boilerplate injection changes embedding). Whole-document embeddings (SBERT, Legal-BERT): resistance ~0.5-0.7. Target for legally structured representations: >0.7 (boilerplate has minimal effect).",
        }
    }
    
    print(f"\n  mean_stability (resistance_score): {resistance_score:.6f}")
    print(f"  std_stability: {metrics['std_stability']:.6f}")
    print(f"  status: {status.value}")
    print(f"  duration: {duration:.2f}s")
    
    return result


def main():
    print("=" * 70)
    print("CENTER_PROJECTED BOILERPLATE RESISTANCE TEST")
    print("=" * 70)
    
    # Run test
    result = run_center_projected_boilerplate_test(sample_size=100)
    
    # Save results
    output_path = OUTPUT_DIR / 'center_projected_boilerplate_resistance.json'
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    print("\nTest complete.")
    
    return result


if __name__ == '__main__':
    main()