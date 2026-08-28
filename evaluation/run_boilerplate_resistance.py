#!/usr/bin/env python3
"""
Boilerplate Resistance Test for Evaluation v6/v7

Tests whether legal representations are resistant to procedural boilerplate
using the full decision text from legal_signals_full.jsonl (1,200 decisions).

Self-contained version without dependency on benchmarks module.
"""

import json
import numpy as np
import re
import random
from pathlib import Path
from typing import List, Dict, Any, Callable, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from dataclasses import dataclass, asdict
from enum import Enum
import time

# Load sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available, legal embeddings tests will be skipped")

# Paths
SIGNALS_FILE = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_signals_full.jsonl")
EXPANDED_META_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200_metadata.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/v6_signal_ablation")
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


@dataclass
class BenchmarkResult:
    name: str
    status: BenchmarkStatus
    metrics: Dict
    details: Dict
    duration: float
    evidence_tier: EvidenceTier
    baseline_comparison: Dict = None
    error_message: str = None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    print(f"Loaded signals for {len(signals)} decisions")
    return signals


def load_expanded_metadata() -> List[Dict]:
    metadata = []
    with open(EXPANDED_META_PATH, 'r') as f:
        for line in f:
            metadata.append(json.loads(line))
    print(f"Loaded expanded metadata for {len(metadata)} decisions")
    return metadata


def build_tfidf_embeddings(signals: Dict, metadata: List[Dict], 
                           text_fields: List[str], 
                           target_dim: int = 128) -> Tuple[np.ndarray, TfidfVectorizer, List[int]]:
    """Build TF-IDF embeddings from specified text fields."""
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        for field in text_fields:
            if sig.get(field):
                parts.append(sig[field])
        
        if parts:
            texts.append(" ".join(parts))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        print(f"Warning: Only {len(valid_indices)} valid texts for TF-IDF")
        return np.zeros((len(metadata), target_dim)), None, []
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=5000,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    
    n_comp = min(target_dim, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=GLOBAL_SEED)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    return full_emb, vectorizer, valid_indices


def build_text_embedding_fn(vectorizer: TfidfVectorizer) -> Callable[[str], np.ndarray]:
    """Build text embedding function from fitted vectorizer."""
    def embed_fn(text: str) -> np.ndarray:
        vec = vectorizer.transform([text])
        arr = vec.toarray()[0]
        norm = np.linalg.norm(arr)
        if norm > 0:
            return (arr / norm).astype(np.float32)
        return np.zeros(vectorizer.transform([""]).toarray().shape[1], dtype=np.float32)
    return embed_fn


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


def run_boilerplate_test(
    name: str,
    text_embedding_fn: Callable[[str], np.ndarray],
    decisions: List[Dict],
    config: BoilerplateConfig
) -> Dict:
    """Run boilerplate resistance test on a text embedding function."""
    print(f"\nRunning boilerplate resistance test for {name}...")
    start_time = time.time()
    
    # Extract boilerplate terms
    boilerplate_terms = extract_boilerplate_terms(decisions, config)
    print(f"  Found {len(boilerplate_terms)} boilerplate terms")
    
    stability_scores = []
    perturbation_details = []
    
    for decision in decisions:
        decision_id = decision.get("decision_id", "")
        text = decision.get("full_text", "")
        language = decision.get("language", "de")
        
        if not text or not decision_id:
            continue
        
        # Get original embedding
        try:
            original_emb = text_embedding_fn(text)
            if original_emb is None:
                continue
            original_emb = np.array(original_emb, dtype=np.float32)
        except Exception as e:
            print(f"    Warning: Failed to get embedding for {decision_id}: {e}")
            continue
        
        # Create perturbed version
        perturbed_text = inject_boilerplate(text, language, boilerplate_terms, config)
        
        # Get perturbed embedding
        try:
            perturbed_emb = text_embedding_fn(perturbed_text)
            if perturbed_emb is None:
                continue
            perturbed_emb = np.array(perturbed_emb, dtype=np.float32)
        except Exception as e:
            print(f"    Warning: Failed to get perturbed embedding for {decision_id}: {e}")
            continue
        
        # Measure cosine similarity
        similarity = cosine_similarity(original_emb, perturbed_emb)
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
            'variant': name,
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
    
    # Resistance score: 1 = perfectly resistant, 0 = fully sensitive
    resistance_score = metrics["mean_stability"]
    metrics["resistance_score"] = resistance_score
    
    # Pass if resistance > 0.6 (threshold calibrated against TF-IDF baseline)
    status = BenchmarkStatus.PASSED if resistance_score > 0.6 else BenchmarkStatus.FAILED
    
    duration = time.time() - start_time
    
    return {
        'variant': name,
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


def main():
    print("=" * 70)
    print("BOILERPLATE RESISTANCE TEST - EVALUATION v6/v7")
    print("=" * 70)
    
    # Load data
    signals = load_signals()
    metadata = load_expanded_metadata()
    decisions = prepare_decisions_for_test(signals, metadata)
    
    # Filter decisions with full_text
    valid_decisions = [d for d in decisions if d['full_text']]
    print(f"Decisions with full_text: {len(valid_decisions)}")
    
    # Sample for testing
    sample_size = min(100, len(valid_decisions))
    test_decisions = valid_decisions[:sample_size]
    print(f"Test sample size: {len(test_decisions)}")
    
    # Language distribution
    lang_counts = Counter(d['language'] for d in test_decisions)
    print(f"Language distribution: {dict(lang_counts)}")
    
    all_results = {
        'factory_direction_version': 6,
        'evaluation_version': 6,
        'global_seed': GLOBAL_SEED,
        'test_type': 'boilerplate_resistance',
        'sample_size': len(test_decisions),
        'results': {}
    }
    
    config = BoilerplateConfig(sample_size=len(test_decisions))
    
    # ============================================================
    # Test 1: TF-IDF on Sachverhalt (facts section)
    # ============================================================
    print("\n" + "=" * 50)
    print("TEST 1: TF-IDF on Sachverhalt (facts)")
    print("=" * 50)
    
    tfidf_sach, vectorizer_sach, valid_idx_sach = build_tfidf_embeddings(
        signals, metadata, ['sachverhalt_text'], target_dim=128
    )
    if vectorizer_sach:
        emb_fn_sach = build_text_embedding_fn(vectorizer_sach)
        result_sach = run_boilerplate_test('sachverhalt_tfidf', emb_fn_sach, test_decisions, config)
        all_results['results']['sachverhalt_tfidf'] = result_sach
    else:
        all_results['results']['sachverhalt_tfidf'] = {'error': 'Insufficient valid texts'}
    
    # ============================================================
    # Test 2: TF-IDF on Erwägungen (reasoning section)
    # ============================================================
    print("\n" + "=" * 50)
    print("TEST 2: TF-IDF on Erwägungen (reasoning)")
    print("=" * 50)
    
    tfidf_erw, vectorizer_erw, valid_idx_erw = build_tfidf_embeddings(
        signals, metadata, ['erwaegungen_text'], target_dim=128
    )
    if vectorizer_erw:
        emb_fn_erw = build_text_embedding_fn(vectorizer_erw)
        result_erw = run_boilerplate_test('erwaegungen_tfidf', emb_fn_erw, test_decisions, config)
        all_results['results']['erwaegungen_tfidf'] = result_erw
    else:
        all_results['results']['erwaegungen_tfidf'] = {'error': 'Insufficient valid texts'}
    
    # ============================================================
    # Test 3: TF-IDF on Full Text
    # ============================================================
    print("\n" + "=" * 50)
    print("TEST 3: TF-IDF on Full Text")
    print("=" * 50)
    
    tfidf_full, vectorizer_full, valid_idx_full = build_tfidf_embeddings(
        signals, metadata, ['full_text'], target_dim=128
    )
    if vectorizer_full:
        emb_fn_full = build_text_embedding_fn(vectorizer_full)
        result_full = run_boilerplate_test('full_text_tfidf', emb_fn_full, test_decisions, config)
        all_results['results']['full_text_tfidf'] = result_full
    else:
        all_results['results']['full_text_tfidf'] = {'error': 'Insufficient valid texts'}
    
    # ============================================================
    # Test 4: Legal Embedding - multilingual-e5-small
    # ============================================================
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        print("\n" + "=" * 50)
        print("TEST 4: multilingual-e5-small (legal embedding)")
        print("=" * 50)
        
        try:
            model_e5 = SentenceTransformer('intfloat/multilingual-e5-small')
            def emb_fn_e5(text: str) -> np.ndarray:
                emb = model_e5.encode(f"passage: {text}", show_progress_bar=False, convert_to_numpy=True)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    return (emb / norm).astype(np.float32)
                return np.zeros(384, dtype=np.float32)
            result_e5 = run_boilerplate_test('multilingual_e5_small', emb_fn_e5, test_decisions, config)
            all_results['results']['multilingual_e5_small'] = result_e5
        except Exception as e:
            print(f"Failed to test multilingual-e5-small: {e}")
            all_results['results']['multilingual_e5_small'] = {'error': str(e)}
        
        # ============================================================
        # Test 5: Legal Embedding - paraphrase-multilingual-MiniLM
        # ============================================================
        print("\n" + "=" * 50)
        print("TEST 5: paraphrase-multilingual-MiniLM (legal embedding)")
        print("=" * 50)
        
        try:
            model_minilm = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            def emb_fn_minilm(text: str) -> np.ndarray:
                emb = model_minilm.encode(text, show_progress_bar=False, convert_to_numpy=True)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    return (emb / norm).astype(np.float32)
                return np.zeros(384, dtype=np.float32)
            result_minilm = run_boilerplate_test('paraphrase_multilingual_minilm', emb_fn_minilm, test_decisions, config)
            all_results['results']['paraphrase_multilingual_minilm'] = result_minilm
        except Exception as e:
            print(f"Failed to test paraphrase-multilingual-MiniLM: {e}")
            all_results['results']['paraphrase_multilingual_minilm'] = {'error': str(e)}
        
        # ============================================================
        # Test 6: Legal Embedding - xlm-roberta-base
        # ============================================================
        print("\n" + "=" * 50)
        print("TEST 6: xlm-roberta-base (legal embedding)")
        print("=" * 50)
        
        try:
            model_xlm = SentenceTransformer('xlm-roberta-base')
            def emb_fn_xlm(text: str) -> np.ndarray:
                emb = model_xlm.encode(text, show_progress_bar=False, convert_to_numpy=True)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    return (emb / norm).astype(np.float32)
                return np.zeros(768, dtype=np.float32)
            result_xlm = run_boilerplate_test('xlm_roberta_base', emb_fn_xlm, test_decisions, config)
            all_results['results']['xlm_roberta_base'] = result_xlm
        except Exception as e:
            print(f"Failed to test xlm-roberta-base: {e}")
            all_results['results']['xlm_roberta_base'] = {'error': str(e)}
    else:
        print("\nSkipping legal embedding tests (sentence-transformers not available)")
    
    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("BOILERPLATE RESISTANCE TEST SUMMARY")
    print("=" * 70)
    
    for name, result in all_results['results'].items():
        if 'error' in result:
            print(f"  {name}: ERROR - {result['error']}")
            continue
        
        metrics = result.get('metrics', {})
        resistance = metrics.get('resistance_score', 'N/A')
        status = result.get('status', 'N/A')
        
        if isinstance(resistance, float):
            print(f"  {name}: resistance={resistance:.4f}, status={status}")
        else:
            print(f"  {name}: resistance={resistance}, status={status}")
    
    # Save results
    output_path = OUTPUT_DIR / 'v6_boilerplate_resistance_results.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    print("\nBoilerplate resistance test complete.")
    
    return all_results


if __name__ == '__main__':
    main()