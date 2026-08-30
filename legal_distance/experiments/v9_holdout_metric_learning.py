#!/usr/bin/env python3
"""
Legal Distance Lane v9 - Holdout Validation of Metric Learning Representations

Tests whether the supervised metric learning representations (linear_metric_epoch4,
mahalanobis_metric_epoch4, hybrid_stabilized_epoch1) generalize to unseen decisions (200 holdout)
and can retrieve legally related decisions WITHOUT shared citations.

This addresses the critical gap: metric learning achieves JP~0.68 on full 1200-decision set
but has NEVER been tested on true holdout. Zero-shot hybrids achieve JP~0.58 on holdout.

Frozen setup:
- Corpus: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- Split: 1000 train (matching evaluation metadata) / 200 holdout (same as v6/v8)
- Harness: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- Metrics: Adversarial Language Dominance (threshold < 0.85), Jurist Pairwise Preference (threshold > 0.5)
- Citation-independent retrieval: legal_area/branch match with NO shared cited_decisions

Factory targets (from v9 direction):
- LangDom < 0.6 (ACHIEVED by zero-shot hybrids)
- JuristPref > 0.7 (MISSED by zero-shot hybrids on holdout - best 0.585)
- Citation-independent retrieval > 15% (MISSED by zero-shot hybrids - best 14.05%)
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
LEGAL_SIGNALS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")

# Metric learning embeddings (pre-trained on full 1200, but we'll split same way)
LINEAR_EMBEDDINGS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy")
MAHALANOBIS_EMBEDDINGS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy")
HYBRID_STABILIZED_EMBEDDINGS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/hybrid_objective_stabilized/best_embeddings.npy")

# Center projected metadata (for alignment)
CP_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v9/holdout_metric_learning")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen harness config
FROZEN_CONFIG_HASH = "1674829901d55e83"
FROZEN_SEED = 42

ADVERSARIAL_CONFIG = {
    'language_dominance_k': 20,
    'language_dominance_threshold': 0.85,
    'jurist_pairwise_k': 10,
    'jurist_pairwise_threshold': 0.5,
}

SUCCESS_RULE = {
    'langdom_target': 0.6,  # Factory direction v8/v9 target
    'jurist_pref_target': 0.7,  # Factory target for production
    'citation_independent_recall_target': 0.15,  # At least 15% cross-citation retrieval
}

def load_legal_signals() -> List[Dict]:
    """Load all 1200 decisions with legal signals."""
    data = []
    with open(LEGAL_SIGNALS_PATH, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    logger.info(f"Loaded {len(data)} decisions from legal_signals_full.jsonl")
    return data

def load_evaluation_metadata() -> List[Dict]:
    """Load the 1000-decision evaluation metadata (fractal-map baseline)."""
    with open(EVAL_METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions from evaluation metadata")
    return metadata

def assign_branch_from_legal_area(legal_area: str) -> str:
    """Map legal_area to high-level branch."""
    if not legal_area:
        return "unknown"
    la_lower = legal_area.lower()
    
    # High-level branches (from factory direction / evaluation)
    if any(kw in la_lower for kw in ["public", "öffentlich", "administrative", "verwaltung", "verfassungs", "constitution", "droit public", "droit administratif", "droit fiscal", "finances", "steuer", "strafprozess", "procédure pénale", "straf", "pena", "infractions", "straftaten", "exécution", "vollzug", "military", "militär", "sicherheit"]):
        return "public"
    elif any(kw in la_lower for kw in ["civil", "zivil", "vertrag", "contrat", "obligation", "obligationen", "schuld", "poursuite", "faillite", "execution", "famille", "familien", "erbrecht", "nachlass", "sachen", "biens", "personen", "personnes", "gesellschaft", "societ", "immobilien", "grund"]):
        return "civil"
    elif any(kw in la_lower for kw in ["criminal", "straf", "pena", "infraction", "straftat"]):
        return "criminal"
    elif any(kw in la_lower for kw in ["social", "sozial", "insurance", "versicherung", "avs", "ai", "iv", "invalid", "unfall", "accident", "kranken", "maladie", "ergänzungs", "prestations", "erwerb", "alters", "hinterlass", "survivants"]):
        return "social_insurance"
    elif any(kw in la_lower for kw in ["tax", "steuer", "fiscal", "abgab"]):
        return "tax"
    elif any(kw in la_lower for kw in ["administrative", "verwaltung", "procédure administrative", "verwaltungsverfahren"]):
        return "administrative"
    return "other"

def prepare_metadata(decisions: List[Dict]) -> List[Dict]:
    """Add branch field and ensure language field."""
    for d in decisions:
        if 'branch' not in d:
            d['branch'] = assign_branch_from_legal_area(d.get('legal_area', ''))
        if 'language' not in d:
            d['language'] = 'de'  # default
    return decisions

def split_train_holdout(decisions: List[Dict], eval_metadata: List[Dict]) -> Tuple[List[Dict], List[Dict], List[int], List[int]]:
    """Split into train (1000 matching eval) and holdout (200) sets."""
    eval_ids = {m['decision_id'] for m in eval_metadata}
    
    train_decisions = []
    holdout_decisions = []
    train_indices = []
    holdout_indices = []
    
    for i, d in enumerate(decisions):
        if d['decision_id'] in eval_ids:
            train_decisions.append(d)
            train_indices.append(i)
        else:
            holdout_decisions.append(d)
            holdout_indices.append(i)
    
    logger.info(f"Train set: {len(train_decisions)} decisions")
    logger.info(f"Holdout set: {len(holdout_decisions)} decisions")
    
    return train_decisions, holdout_decisions, train_indices, holdout_indices

def load_and_align_embeddings(embeddings_path: Path, decisions: List[Dict]) -> np.ndarray:
    """Load embeddings and align to decisions order using center_projected metadata."""
    embeddings = np.load(embeddings_path)
    with open(CP_METADATA_PATH) as f:
        cp_metadata = json.load(f)
    
    # Build decision_id -> embedding mapping
    cp_id_to_emb = {m['decision_id']: embeddings[i] for i, m in enumerate(cp_metadata)}
    
    # Align to decisions order
    aligned = np.zeros((len(decisions), embeddings.shape[1]))
    missing = 0
    for i, d in enumerate(decisions):
        if d['decision_id'] in cp_id_to_emb:
            aligned[i] = cp_id_to_emb[d['decision_id']]
        else:
            missing += 1
    if missing > 0:
        logger.warning(f"Missing {missing} decisions in {embeddings_path.name} embeddings")
    
    logger.info(f"Loaded and aligned {embeddings_path.name}: {aligned.shape}")
    return aligned

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = 20) -> Dict:
    """Adversarial test: measure language dominance in nearest neighbors."""
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / len(neighbor_langs))
    
    mean_dominance = np.mean(dominance_rates)
    
    return {
        'mean_language_dominance': float(mean_dominance),
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }

def simulate_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = 10
) -> Dict:
    """Simulate jurist pairwise preference study."""
    n = len(branches)
    
    nn = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        
        has_legal_relevant = False
        has_language_artifact = False
        
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i:
                has_legal_relevant = True
            if nb != branch_i and nl == lang_i:
                has_language_artifact = True
        
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round(language_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(jurist_forced_wrong / total, 4),
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }

def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the two critical adversarial benchmarks."""
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    
    lang_dom = adversarial_language_dominance(embeddings, metadata, k=ADVERSARIAL_CONFIG['language_dominance_k'])
    jurist_pref = simulate_pairwise_preference(embeddings, branches, languages, k=ADVERSARIAL_CONFIG['jurist_pairwise_k'])
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }

def citation_independent_retrieval(
    holdout_embeddings: np.ndarray,
    holdout_metadata: List[Dict],
    train_embeddings: np.ndarray,
    train_metadata: List[Dict],
    k: int = 10
) -> Dict:
    """
    Test retrieval of legally related decisions WITHOUT shared citations.
    
    For each holdout decision, find top-k neighbors in train set.
    Count how many neighbors share legal_area/branch but have ZERO shared cited_decisions.
    """
    nn = NearestNeighbors(n_neighbors=min(k, len(train_embeddings)), metric='cosine')
    nn.fit(train_embeddings)
    _, indices = nn.kneighbors(holdout_embeddings)
    
    # Build citation sets for train decisions
    train_citations = [set(m.get('cited_decisions', [])) for m in train_metadata]
    
    total_queries = len(holdout_metadata)
    legal_retrieved = 0
    citation_independent_retrieved = 0
    
    for i, meta in enumerate(holdout_metadata):
        holdout_branch = meta.get('branch', 'unknown')
        holdout_legal_area = meta.get('legal_area', 'unknown')
        holdout_citations = set(meta.get('cited_decisions', []))
        
        neighbor_indices = indices[i]
        
        for n_idx in neighbor_indices:
            train_meta = train_metadata[n_idx]
            train_branch = train_meta.get('branch', 'unknown')
            train_legal_area = train_meta.get('legal_area', 'unknown')
            train_cites = train_citations[n_idx]
            
            # Check legal relatedness (same branch or legal_area)
            legally_related = (train_branch == holdout_branch and holdout_branch != 'unknown') or \
                             (train_legal_area == holdout_legal_area and holdout_legal_area != 'unknown')
            
            if legally_related:
                legal_retrieved += 1
                # Check if NO shared citations
                if len(holdout_citations & train_cites) == 0:
                    citation_independent_retrieved += 1
    
    # Rates
    max_possible = total_queries * k
    legal_rate = legal_retrieved / max_possible if max_possible > 0 else 0
    citation_independent_rate = citation_independent_retrieved / max_possible if max_possible > 0 else 0
    
    # Also compute per-query rate
    per_query_rates = []
    for i, meta in enumerate(holdout_metadata):
        holdout_branch = meta.get('branch', 'unknown')
        holdout_legal_area = meta.get('legal_area', 'unknown')
        holdout_citations = set(meta.get('cited_decisions', []))
        
        neighbor_indices = indices[i]
        query_legal = 0
        query_cite_indep = 0
        
        for n_idx in neighbor_indices:
            train_meta = train_metadata[n_idx]
            train_branch = train_meta.get('branch', 'unknown')
            train_legal_area = train_meta.get('legal_area', 'unknown')
            train_cites = train_citations[n_idx]
            
            legally_related = (train_branch == holdout_branch and holdout_branch != 'unknown') or \
                             (train_legal_area == holdout_legal_area and holdout_legal_area != 'unknown')
            
            if legally_related:
                query_legal += 1
                if len(holdout_citations & train_cites) == 0:
                    query_cite_indep += 1
        
        if query_legal > 0:
            per_query_rates.append(query_cite_indep / query_legal)
    
    mean_per_query = np.mean(per_query_rates) if per_query_rates else 0
    
    return {
        'total_queries': total_queries,
        'k': k,
        'total_legal_retrieved': legal_retrieved,
        'total_citation_independent_retrieved': citation_independent_retrieved,
        'legal_retrieval_rate': round(legal_rate, 4),
        'citation_independent_retrieval_rate': round(citation_independent_rate, 4),
        'mean_per_query_cite_indep_rate': round(mean_per_query, 4),
        'status': 'PASS' if citation_independent_rate >= SUCCESS_RULE['citation_independent_recall_target'] else 'FAIL',
        'note': f'Retrieval of legally related decisions WITHOUT shared citations. Target: {SUCCESS_RULE["citation_independent_recall_target"]:.0%}'
    }

def evaluate_representation(
    name: str,
    train_embeddings: np.ndarray,
    holdout_embeddings: np.ndarray,
    train_metadata: List[Dict],
    holdout_metadata: List[Dict]
) -> Dict[str, Any]:
    """Full evaluation of a representation on train and holdout."""
    logger.info(f"\n=== Evaluating {name} ===")
    
    # Normalize train
    norms = np.linalg.norm(train_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    train_embeddings_norm = train_embeddings / norms
    
    # Normalize holdout
    norms = np.linalg.norm(holdout_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    holdout_embeddings_norm = holdout_embeddings / norms
    
    # Adversarial on TRAIN
    logger.info(f"  Adversarial on TRAIN ({len(train_metadata)} decisions)...")
    train_adv = run_adversarial_benchmarks(train_embeddings_norm, train_metadata)
    
    # Adversarial on HOLDOUT
    logger.info(f"  Adversarial on HOLDOUT ({len(holdout_metadata)} decisions)...")
    holdout_adv = run_adversarial_benchmarks(holdout_embeddings_norm, holdout_metadata)
    
    # Citation-independent retrieval (holdout -> train)
    logger.info(f"  Citation-independent retrieval (holdout->train)...")
    cite_indep = citation_independent_retrieval(
        holdout_embeddings_norm, holdout_metadata,
        train_embeddings_norm, train_metadata
    )
    
    logger.info(f"  Train: LangDom={train_adv['language_dominance_score']:.4f} ({train_adv['adversarial_language_dominance']['status']}), "
                f"JuristPref={train_adv['jurist_preference_rate']:.4f} ({train_adv['jurist_pairwise_preference']['status']})")
    logger.info(f"  Holdout: LangDom={holdout_adv['language_dominance_score']:.4f} ({holdout_adv['adversarial_language_dominance']['status']}), "
                f"JuristPref={holdout_adv['jurist_preference_rate']:.4f} ({holdout_adv['jurist_pairwise_preference']['status']})")
    logger.info(f"  Cite-indep retrieval: {cite_indep['citation_independent_retrieval_rate']:.4f} ({cite_indep['status']})")
    
    return {
        'name': name,
        'n_train': train_embeddings.shape[0],
        'n_holdout': holdout_embeddings.shape[0],
        'embedding_dim': train_embeddings.shape[1],
        'train_adversarial': train_adv,
        'holdout_adversarial': holdout_adv,
        'citation_independent_retrieval': cite_indep,
    }

def convert_for_json(obj):
    """Convert numpy types for JSON serialization."""
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_for_json(v) for v in obj]
    return obj

def main():
    logger.info("=" * 80)
    logger.info("LEGAL DISTANCE v9 - HOLDOUT VALIDATION OF METRIC LEARNING REPRESENTATIONS")
    logger.info("=" * 80)
    logger.info(f"Frozen Harness: v3 (seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH})")
    logger.info(f"Corpus: 1200 BGer decisions (2024 expanded slice)")
    logger.info(f"Split: 1000 train / 200 holdout (same as v6/v8 out-of-sample test)")
    logger.info("Testing: linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1")
    logger.info("Question: Do supervised metric learning representations generalize better than zero-shot hybrids?")
    logger.info("Zero-shot holdout baseline: JP ~0.53-0.59, CiteIndep ~13-14%")
    
    # Load data
    logger.info("\n1. Loading legal signals (1200 decisions)...")
    decisions = load_legal_signals()
    decisions = prepare_metadata(decisions)
    
    logger.info("\n2. Loading evaluation metadata (1000 decisions)...")
    eval_metadata = load_evaluation_metadata()
    
    logger.info("\n3. Splitting into train (1000) and holdout (200)...")
    train_decisions, holdout_decisions, train_indices, holdout_indices = split_train_holdout(decisions, eval_metadata)
    
    # Load and split metric learning embeddings
    logger.info("\n4. Loading metric learning embeddings...")
    
    linear_embeddings = load_and_align_embeddings(LINEAR_EMBEDDINGS_PATH, decisions)
    mahalanobis_embeddings = load_and_align_embeddings(MAHALANOBIS_EMBEDDINGS_PATH, decisions)
    hybrid_stabilized_embeddings = load_and_align_embeddings(HYBRID_STABILIZED_EMBEDDINGS_PATH, decisions)
    
    # Split embeddings using same indices
    train_linear = linear_embeddings[train_indices]
    holdout_linear = linear_embeddings[holdout_indices]
    
    train_mahalanobis = mahalanobis_embeddings[train_indices]
    holdout_mahalanobis = mahalanobis_embeddings[holdout_indices]
    
    train_hybrid = hybrid_stabilized_embeddings[train_indices]
    holdout_hybrid = hybrid_stabilized_embeddings[holdout_indices]
    
    all_results = {}
    
    # 1. linear_metric_epoch4
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: linear_metric_epoch4 (pre-trained, split by same indices)")
    logger.info("=" * 80)
    all_results['linear_metric_epoch4'] = evaluate_representation(
        'linear_metric_epoch4', train_linear, holdout_linear,
        train_decisions, holdout_decisions
    )
    
    # 2. mahalanobis_metric_epoch4
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: mahalanobis_metric_epoch4 (pre-trained, split by same indices)")
    logger.info("=" * 80)
    all_results['mahalanobis_metric_epoch4'] = evaluate_representation(
        'mahalanobis_metric_epoch4', train_mahalanobis, holdout_mahalanobis,
        train_decisions, holdout_decisions
    )
    
    # 3. hybrid_stabilized_epoch1
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: hybrid_stabilized_epoch1 (pre-trained, split by same indices)")
    logger.info("=" * 80)
    all_results['hybrid_stabilized_epoch1'] = evaluate_representation(
        'hybrid_stabilized_epoch1', train_hybrid, holdout_hybrid,
        train_decisions, holdout_decisions
    )
    
    # Summary
    logger.info("\n" + "=" * 100)
    logger.info("HOLDOUT VALIDATION SUMMARY - METRIC LEARNING REPRESENTATIONS")
    logger.info("=" * 100)
    
    logger.info(f"\n{'Representation':<40} {'Train LD':>8} {'Train JP':>8} {'Holdout LD':>10} {'Holdout JP':>10} {'ΔLD':>6} {'ΔJP':>6} {'Cite-Indep':>10} {'Status'}")
    logger.info("-" * 100)
    
    for name, res in all_results.items():
        train_ld = res['train_adversarial']['language_dominance_score']
        train_jp = res['train_adversarial']['jurist_preference_rate']
        holdout_ld = res['holdout_adversarial']['language_dominance_score']
        holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
        
        ld_diff = abs(train_ld - holdout_ld)
        jp_diff = abs(train_jp - holdout_jp)
        
        cite_indep = res['citation_independent_retrieval']
        cite_rate = cite_indep.get('citation_independent_retrieval_rate', 0)
        cite_status = cite_indep.get('status', 'N/A')
        
        # Overall status
        train_pass = res['train_adversarial']['both_pass']
        holdout_pass = res['holdout_adversarial']['both_pass']
        cite_pass = cite_indep.get('status') == 'PASS'
        
        if train_pass and holdout_pass and cite_pass:
            overall = "✅ FULL PASS"
        elif train_pass and holdout_pass:
            overall = "✅ ADV PASS"
        elif holdout_pass:
            overall = "⚠️  HOLDOUT PASS"
        else:
            overall = "❌ FAIL"
        
        logger.info(f"{name:<40} {train_ld:>8.4f} {train_jp:>8.4f} {holdout_ld:>10.4f} {holdout_jp:>10.4f} {ld_diff:>6.4f} {jp_diff:>6.4f} {cite_rate:>10.4f} {overall}")
    
    # Detailed generalization assessment
    logger.info("\n" + "=" * 80)
    logger.info("GENERALIZATION ASSESSMENT - METRIC LEARNING vs ZERO-SHOT HYBRIDS")
    logger.info("=" * 80)
    
    # Load zero-shot results for comparison
    zero_shot_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json")
    if zero_shot_path.exists():
        with open(zero_shot_path) as f:
            zero_shot_results = json.load(f)
        
        logger.info("\nComparison with zero-shot hybrids (from v8 holdout validation):")
        logger.info(f"{'Representation':<35} {'Holdout LD':>10} {'Holdout JP':>10} {'Cite-Indep':>10} {'Status'}")
        logger.info("-" * 70)
        
        for name in ['cited_decisions_tfidf', 'cited_outcome_hybrid_0.3', 'cited_outcome_hybrid_0.5', 'cited_outcome_hybrid_0.7']:
            if name in zero_shot_results:
                res = zero_shot_results[name]
                holdout_ld = res['holdout_adversarial']['language_dominance_score']
                holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
                cite_rate = res['citation_independent_retrieval'].get('citation_independent_retrieval_rate', 0)
                cite_status = res['citation_independent_retrieval'].get('status', 'N/A')
                adv_pass = res['holdout_adversarial']['both_pass']
                status = "✅" if adv_pass else "❌"
                logger.info(f"{name:<35} {holdout_ld:>10.4f} {holdout_jp:>10.4f} {cite_rate:>10.4f} {status} {cite_status}")
    
    logger.info("\nMetric Learning Results:")
    for name, res in all_results.items():
        holdout_ld = res['holdout_adversarial']['language_dominance_score']
        holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
        cite_rate = res['citation_independent_retrieval'].get('citation_independent_retrieval_rate', 0)
        cite_status = res['citation_independent_retrieval'].get('status', 'N/A')
        adv_pass = res['holdout_adversarial']['both_pass']
        status = "✅" if adv_pass else "❌"
        logger.info(f"{name:<35} {holdout_ld:>10.4f} {holdout_jp:>10.4f} {cite_rate:>10.4f} {status} {cite_status}")
    
    # Target assessment
    logger.info("\n" + "=" * 80)
    logger.info("FACTORY TARGET ASSESSMENT ON HOLDOUT")
    logger.info("=" * 80)
    
    for name, res in all_results.items():
        holdout_ld = res['holdout_adversarial']['language_dominance_score']
        holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
        cite_indep = res['citation_independent_retrieval']
        cite_rate = cite_indep.get('citation_independent_retrieval_rate', 0)
        cite_pass = cite_indep.get('status') == 'PASS'
        holdout_both = res['holdout_adversarial']['both_pass']
        
        langdom_ok = holdout_ld < SUCCESS_RULE['langdom_target']
        jurist_ok = holdout_jp > SUCCESS_RULE['jurist_pref_target']
        cite_ok = cite_pass
        
        logger.info(f"\n{name}:")
        logger.info(f"  Holdout:  LangDom={holdout_ld:.4f}, JuristPref={holdout_jp:.4f}, CiteIndep={cite_rate:.4f}")
        logger.info(f"  Targets:  LangDom<{SUCCESS_RULE['langdom_target']}={langdom_ok}, JuristPref>{SUCCESS_RULE['jurist_pref_target']}={jurist_ok}, CiteIndep>{SUCCESS_RULE['citation_independent_recall_target']:.0%}={cite_ok}")
        
        if langdom_ok and jurist_ok and holdout_both:
            if cite_ok:
                logger.info(f"  🎯 PRODUCTION READY: All targets met on holdout + citation-independent retrieval")
            else:
                logger.info(f"  ✅ ROBUST: All adversarial targets met on holdout (cite-indep needs work)")
        elif holdout_both:
            logger.info(f"  ⚠️  PARTIAL: Passes adversarial gates but misses factory targets")
        else:
            logger.info(f"  ❌ FAILS: Does not pass adversarial gates on holdout")
    
    # Save results
    output_path = OUTPUT_DIR / "holdout_metric_learning_validation.json"
    with open(output_path, 'w') as f:
        json.dump(convert_for_json(all_results), f, indent=2)
    
    logger.info(f"\nResults saved to: {output_path}")
    
    return all_results

if __name__ == "__main__":
    main()