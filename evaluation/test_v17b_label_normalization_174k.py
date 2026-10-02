#!/usr/bin/env python3
"""
Test v17b label normalization generalization to 174k fine-grained legal_area labels.

v17b at 1000-scale: 15-25% purity gain REPRODUCED across 4 seeds.
At 174k: "purity ratios 4-10x but NMI decreases on normalized. Different regime at scale."

This script tests label normalization on:
1. TF-IDF embeddings at full 174k scale (8 representations available)
2. Dense embeddings at 19k scale (4 representations: raw_768, cp_768, cp_64, cp_128)
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
TFIDF_EMBEDDINGS_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/embeddings")
DENSE_19K_RESULTS_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_19k_formal_suite")
METADATA_174K_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/v17b_label_normalization_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TF-IDF representations at 174k
TFIDF_REPRESENTATIONS = {
    'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
    'full_text_tfidf_light': 'full_text_tfidf_light.npy',
    'outcome_tfidf': 'outcome_tfidf.npy',
    'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
    'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
    'regeste_tfidf': 'regeste_tfidf.npy',
}

# Legal area label normalization rules (from v17b)
# Common normalizations for Swiss Federal Supreme Court legal areas
LEGAL_AREA_NORMALIZATIONS = {
    # Contract law variants
    'Vertragsrecht': 'Vertragsrecht',
    'Droit des contrats': 'Vertragsrecht',
    'Diritto contrattuale': 'Vertragsrecht',
    'Droit des obligations (en général)': 'Vertragsrecht',
    
    # Civil procedure
    'Zivilprozess': 'Zivilprozess',
    'Procédure civile': 'Zivilprozess',
    'Procedura civile': 'Zivilprozess',
    
    # Family law
    'Familienrecht': 'Familienrecht',
    'Droit de la famille': 'Familienrecht',
    'Diritto della famiglia': 'Familienrecht',
    
    # Debt enforcement/bankruptcy
    'Schuldbetreibungs- und Konkursrecht': 'Schuldbetreibungs- und Konkursrecht',
    'Droit des poursuites et faillites': 'Schuldbetreibungs- und Konkursrecht',
    'Diritto delle esecuzioni e del fallimento': 'Schuldbetreibungs- und Konkursrecht',
    
    # Property/real rights
    'Sachenrecht': 'Sachenrecht',
    'Droits réels': 'Sachenrecht',
    'Diritti reali': 'Sachenrecht',
    
    # Inheritance
    'Erbrecht': 'Erbrecht',
    'Droit des successions': 'Erbrecht',
    'Diritto successorio': 'Erbrecht',
    
    # Company law
    'Gesellschaftsrecht': 'Gesellschaftsrecht',
    'Droit des sociétés': 'Gesellschaftsrecht',
    'Diritto societario': 'Gesellschaftsrecht',
    
    # IP/Competition
    'Immaterialgüter-, Wettbewerbs- und Kartellrecht': 'Immaterialgüter-, Wettbewerbs- und Kartellrecht',
    'Droit de la propriété intellectuelle, de la concurrence et des cartels': 'Immaterialgüter-, Wettbewerbs- und Kartellrecht',
    
    # Tort/liability
    'Haftpflichtrecht': 'Haftpflichtrecht',
    'Droit de la responsabilité': 'Haftpflichtrecht',
    'Diritto della responsabilità': 'Haftpflichtrecht',
    
    # Person law
    'Personenrecht': 'Personenrecht',
    'Droit des personnes': 'Personenrecht',
    'Diritto delle persone': 'Personenrecht',
    
    # Criminal law
    'Straftaten': 'Straftaten',
    'Infractions': 'Straftaten',
    'Reati': 'Straftaten',
    
    # Criminal procedure
    'Strafprozess': 'Strafprozess',
    'Procédure pénale': 'Strafprozess',
    'Procedura penale': 'Strafprozess',
    
    # Constitutional/administrative
    'Bürgerrecht und Ausländerrecht': 'Bürgerrecht und Ausländerrecht',
    'Droit de cité et droit des étrangers': 'Bürgerrecht und Ausländerrecht',
    'Cittadinanza e diritto degli stranieri': 'Bürgerrecht und Ausländerrecht',
    
    'Droit de cité et droit des étrangers': 'Bürgerrecht und Ausländerrecht',
    
    # Extradition/mutual assistance
    'Entraide et extradition': 'Entraide und Auslieferung',
    'Rechtshilfe und Auslieferung': 'Entraide und Auslieferung',
    'Assistenza giudiziaria e estradizione': 'Entraide und Auslieferung',
    
    # Public finances/tax
    'Öffentliche Finanzen & Abgaberecht': 'Öffentliche Finanzen & Abgaberecht',
    'Finances publiques & droit fiscal': 'Öffentliche Finanzen & Abgaberecht',
    'Finanze pubbliche & diritto tributario': 'Öffentliche Finanzen & Abgaberecht',
    
    # Social security
    'Gesundheitswesen & soziale Sicherheit': 'Gesundheitswesen & soziale Sicherheit',
    'Santé & sécurité sociale': 'Gesundheitswesen & soziale Sicherheit',
    
    # Media
    'Medien': 'Medien',
    
    # Environment
    'Ökologisches Gleichgewicht': 'Ökologisches Gleichgewicht',
    
    # Planning/construction
    'Raumplanung und öffentliches Baurecht': 'Raumplanung und öffentliches Baurecht',
    'Aménagement du territoire et droit public des constructions': 'Raumplanung und öffentliches Baurecht',
    'Pianificazione territoriale e diritto pubblico edilizio': 'Raumplanung und öffentliches Baurecht',
    
    # Public employment
    'Öffentliches Dienstverhältnis': 'Öffentliches Dienstverhältnis',
    'Fonction publique': 'Öffentliches Dienstverhältnis',
    
    # Fundamental rights
    'Grundrecht': 'Grundrecht',
    'Droit fondamental': 'Grundrecht',
    'Diritto fondamentale': 'Grundrecht',
    
    # Political rights
    'Politische Rechte': 'Politische Rechte',
    
    # Jurisdiction
    'Zuständigkeitsfragen, Garantie des Wohnsitzrichters und des v...': 'Zuständigkeit',
    'Questions de compétence, garantie du juge du domicile et du v...': 'Zuständigkeit',
    
    # Post/telecom
    'Post- und Fernmeldeverkehr': 'Post- und Fernmeldeverkehr',
    
    # Energy
    'Energie': 'Energie',
    
    # Economy
    'Wirtschaft': 'Wirtschaft',
    
    # Registry
    'Registre': 'Registre',
    
    # Debt enforcement specific
    'Schuldbetreibungs- und Konkurskammer': 'Schuldbetreibungs- und Konkursrecht',
    'Camera delle esecuzioni e dei fallimenti': 'Schuldbetreibungs- und Konkursrecht',
}


def normalize_legal_area(label: str) -> str:
    """Normalize a legal_area label using v17b rules."""
    if not label or label == 'null' or label == 'unknown':
        return 'unknown'
    
    # Direct mapping
    if label in LEGAL_AREA_NORMALIZATIONS:
        return LEGAL_AREA_NORMALIZATIONS[label]
    
    # Try case-insensitive match
    label_lower = label.strip().lower()
    for orig, norm in LEGAL_AREA_NORMALIZATIONS.items():
        if orig.strip().lower() == label_lower:
            return norm
    
    # Try partial matching for unmatched labels
    # Contract-related
    if any(kw in label_lower for kw in ['vertrag', 'contrat', 'contratt', 'obligation', 'obblig']):
        return 'Vertragsrecht'
    # Family
    if any(kw in label_lower for kw in ['famili', 'famill', 'personen', 'personne', 'person']):
        return 'Familienrecht'
    # Debt enforcement
    if any(kw in label_lower for kw in ['schuld', 'betreib', 'konkurs', 'poursuit', 'faillit', 'esecuz', 'falliment']):
        return 'Schuldbetreibungs- und Konkursrecht'
    # Property
    if any(kw in label_lower for kw in ['sachen', 'droit reel', 'diritti real', 'immobil']):
        return 'Sachenrecht'
    # Inheritance
    if any(kw in label_lower for kw in ['erb', 'success', 'succession']):
        return 'Erbrecht'
    # Company
    if any(kw in label_lower for kw in ['gesellschaf', 'societ', 'company']):
        return 'Gesellschaftsrecht'
    # IP
    if any(kw in label_lower for kw in ['immateriell', 'intellectuel', 'propriete intellect', 'concorren', 'cartel', 'competit']):
        return 'Immaterialgüter-, Wettbewerbs- und Kartellrecht'
    # Tort
    if any(kw in label_lower for kw in ['haftpflicht', 'responsabilit', 'responsabil']):
        return 'Haftpflichtrecht'
    # Criminal
    if any(kw in label_lower for kw in ['straftat', 'infraction', 'reat', 'straf', 'penal', 'pénal']):
        return 'Straftaten'
    # Criminal procedure
    if any(kw in label_lower for kw in ['strafprozess', 'procédure pénale', 'procedura penale']):
        return 'Strafprozess'
    # Citizenship/foreigners
    if any(kw in label_lower for kw in ['bürgerrecht', 'ausländer', 'cittadinanza', 'stranieri', 'étranger', 'cite']):
        return 'Bürgerrecht und Ausländerrecht'
    # Extradition
    if any(kw in label_lower for kw in ['entraide', 'extradition', 'rechtshilfe', 'auslieferung', 'assistenza giud']):
        return 'Entraide und Auslieferung'
    # Public finance
    if any(kw in label_lower for kw in ['finanz', 'abgab', 'fiscal', 'tributar', 'steuer']):
        return 'Öffentliche Finanzen & Abgaberecht'
    # Social security
    if any(kw in label_lower for kw in ['gesundheit', 'soziale sicher', 'santé', 'sécurité social', 'assistenza']):
        return 'Gesundheitswesen & soziale Sicherheit'
    # Media
    if 'medien' in label_lower or 'media' in label_lower:
        return 'Medien'
    # Environment
    if any(kw in label_lower for kw in ['ökolog', 'ecolog', 'environnement', 'ambiente']):
        return 'Ökologisches Gleichgewicht'
    # Planning
    if any(kw in label_lower for kw in ['raumplan', 'bau', 'construction', 'ediliz', 'territori']):
        return 'Raumplanung und öffentliches Baurecht'
    # Public service
    if any(kw in label_lower for kw in ['dienst', 'fonction public', 'public serv']):
        return 'Öffentliches Dienstverhältnis'
    # Fundamental rights
    if any(kw in label_lower for kw in ['grundrecht', 'droit fondamental', 'diritti fondamentale']):
        return 'Grundrecht'
    # Political rights
    if any(kw in label_lower for kw in ['politisch', 'politique', 'politici']):
        return 'Politische Rechte'
    # Jurisdiction
    if any(kw in label_lower for kw in ['zuständig', 'compétence', 'competenza', 'giudice', 'judge']):
        return 'Zuständigkeit'
    # Post/telecom
    if any(kw in label_lower for kw in ['post', 'fernmelde', 'telecom', 'telecomunic']):
        return 'Post- und Fernmeldeverkehr'
    # Energy
    if any(kw in label_lower for kw in ['energi', 'énergie', 'energia']):
        return 'Energie'
    # Economy
    if any(kw in label_lower for kw in ['wirtschaft', 'économie', 'economia']):
        return 'Wirtschaft'
    # Registry
    if any(kw in label_lower for kw in ['register', 'registre']):
        return 'Registre'
    
    # Return original if no match
    return label


def load_metadata_174k() -> List[Dict]:
    """Load 174k metadata."""
    logger.info("Loading 174k metadata...")
    with open(METADATA_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata


def load_tfidf_embeddings() -> Dict[str, np.ndarray]:
    """Load all TF-IDF embeddings at 174k."""
    embeddings = {}
    for name, fname in TFIDF_REPRESENTATIONS.items():
        path = TFIDF_EMBEDDINGS_DIR / fname
        if path.exists():
            emb = np.load(path)
            logger.info(f"Loaded {name}: {emb.shape}")
            embeddings[name] = emb
        else:
            logger.warning(f"Missing embedding file: {path}")
    return embeddings


def load_dense_19k_embeddings() -> Dict[str, np.ndarray]:
    """Load dense 19k embeddings from evaluation results."""
    # The dense embeddings were created in evaluate_19k_dense_formal_suite.py
    # We need to regenerate them or load from checkpoints
    # For now, we'll load the raw 768 and apply transformations
    
    DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
    FULL_METADATA_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")
    TARGET_YEARS = list(range(2000, 2003))
    
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in TARGET_YEARS:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    subset_metadata = []
    for m in full_metadata:
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    id_to_year_local = {}
    for year in TARGET_YEARS:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    dim = year_emb[TARGET_YEARS[0]].shape[1]
    embeddings_768 = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        year, local_idx = id_to_year_local[m['decision_id']]
        embeddings_768[i] = year_emb[year][local_idx]
    
    logger.info(f"Assembled dense 768-dim: {embeddings_768.shape}")
    
    # Center project
    languages = sorted(set(m.get('language', 'unknown') for m in subset_metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in subset_metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings_768[mask].mean(axis=0)
    
    debiased = np.copy(embeddings_768)
    for i, m in enumerate(subset_metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings_768[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    # PCA to 64
    pca_64 = PCA(n_components=64, random_state=42)
    emb_64 = normalize(pca_64.fit_transform(debiased), norm='l2', axis=1)
    
    # PCA to 128
    pca_128 = PCA(n_components=128, random_state=42)
    emb_128 = normalize(pca_128.fit_transform(debiased), norm='l2', axis=1)
    
    return {
        'dense_raw_768': embeddings_768,
        'dense_center_projected_768': debiased,
        'dense_center_projected_64': emb_64,
        'dense_center_projected_128': emb_128,
    }, subset_metadata


def get_legal_areas(metadata: List[Dict]) -> np.ndarray:
    """Extract legal_area labels from metadata."""
    return np.array([m.get('legal_area', 'unknown') for m in metadata])


def get_normalized_legal_areas(metadata: List[Dict]) -> np.ndarray:
    """Extract normalized legal_area labels from metadata."""
    return np.array([normalize_legal_area(m.get('legal_area', 'unknown')) for m in metadata])


def compute_cluster_purity(labels: np.ndarray, true_labels: np.ndarray) -> float:
    """Compute cluster purity (majority class accuracy per cluster, weighted by cluster size)."""
    unique_labels = np.unique(labels[labels != -1])
    if len(unique_labels) == 0:
        return 0.0
    
    total_correct = 0
    total_points = 0
    
    for label in unique_labels:
        mask = labels == label
        cluster_true = true_labels[mask]
        if len(cluster_true) == 0:
            continue
        majority = Counter(cluster_true).most_common(1)[0][1]
        total_correct += majority
        total_points += len(cluster_true)
    
    return total_correct / total_points if total_points > 0 else 0.0


def test_label_normalization(embeddings: np.ndarray, metadata: List[Dict], 
                              n_clusters: int = None, random_state: int = 42) -> Dict[str, Any]:
    """Test label normalization effect on clustering."""
    
    legal_areas = get_legal_areas(metadata)
    normalized_legal_areas = get_normalized_legal_areas(metadata)
    
    # Count unique labels
    unique_original = len(np.unique(legal_areas))
    unique_normalized = len(np.unique(normalized_legal_areas))
    
    logger.info(f"Original legal_area labels: {unique_original}")
    logger.info(f"Normalized legal_area labels: {unique_normalized}")
    logger.info(f"Reduction: {unique_original} -> {unique_normalized} ({unique_normalized/unique_original*100:.1f}%)")
    
    # Determine n_clusters if not specified
    if n_clusters is None:
        n_clusters = unique_normalized
    
    # Run KMeans on embeddings
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Compute purities
    purity_original = compute_cluster_purity(cluster_labels, legal_areas)
    purity_normalized = compute_cluster_purity(cluster_labels, normalized_legal_areas)
    
    # Compute NMI
    nmi_original = normalized_mutual_info_score(legal_areas, cluster_labels)
    nmi_normalized = normalized_mutual_info_score(normalized_legal_areas, cluster_labels)
    
    # Compute ARI
    ari_original = adjusted_rand_score(legal_areas, cluster_labels)
    ari_normalized = adjusted_rand_score(normalized_legal_areas, cluster_labels)
    
    # Purity gain
    purity_gain = (purity_normalized - purity_original) / purity_original * 100 if purity_original > 0 else 0
    nmi_change = (nmi_normalized - nmi_original) / nmi_original * 100 if nmi_original > 0 else 0
    
    return {
        'n_clusters': int(n_clusters),
        'unique_original_labels': int(unique_original),
        'unique_normalized_labels': int(unique_normalized),
        'label_reduction_ratio': unique_normalized / unique_original if unique_original > 0 else 0,
        'purity_original': float(purity_original),
        'purity_normalized': float(purity_normalized),
        'purity_gain_pct': float(purity_gain),
        'nmi_original': float(nmi_original),
        'nmi_normalized': float(nmi_normalized),
        'nmi_change_pct': float(nmi_change),
        'ari_original': float(ari_original),
        'ari_normalized': float(ari_normalized),
    }


def test_multi_seed(embeddings: np.ndarray, metadata: List[Dict], 
                    n_clusters: int, seeds: List[int] = [42, 123, 456, 789]) -> Dict[str, Any]:
    """Test label normalization across multiple seeds."""
    
    results = []
    for seed in seeds:
        result = test_label_normalization(embeddings, metadata, n_clusters=n_clusters, random_state=seed)
        result['seed'] = seed
        results.append(result)
    
    # Aggregate
    purity_gains = [r['purity_gain_pct'] for r in results]
    nmi_changes = [r['nmi_change_pct'] for r in results]
    
    return {
        'seed_results': results,
        'purity_gain_mean': float(np.mean(purity_gains)),
        'purity_gain_std': float(np.std(purity_gains)),
        'purity_gain_min': float(np.min(purity_gains)),
        'purity_gain_max': float(np.max(purity_gains)),
        'nmi_change_mean': float(np.mean(nmi_changes)),
        'nmi_change_std': float(np.std(nmi_changes)),
        'all_seeds_positive_gain': all(g > 0 for g in purity_gains),
    }


def main():
    logger.info("=" * 70)
    logger.info("v17b Label Normalization Generalization Test at 174k / 19k Scale")
    logger.info("=" * 70)
    
    # Load metadata
    metadata_174k = load_metadata_174k()
    
    # 1. Test on TF-IDF embeddings at 174k
    logger.info("\n" + "=" * 70)
    logger.info("TESTING TF-IDF EMBEDDINGS AT 174k SCALE")
    logger.info("=" * 70)
    
    tfidf_embeddings = load_tfidf_embeddings()
    tfidf_results = {}
    
    for name, embeddings in tfidf_embeddings.items():
        logger.info(f"\nTesting {name} ({embeddings.shape[0]} decisions, {embeddings.shape[1]} dims)...")
        
        # Trim embeddings to match metadata length
        if embeddings.shape[0] != len(metadata_174k):
            logger.info(f"  Trimming embeddings from {embeddings.shape[0]} to {len(metadata_174k)}")
            embeddings = embeddings[:len(metadata_174k)]
        
        # Use normalized label count for n_clusters
        normalized_areas = get_normalized_legal_areas(metadata_174k)
        n_clusters = len(np.unique(normalized_areas))
        
        # Single seed test
        result = test_label_normalization(embeddings, metadata_174k, n_clusters=n_clusters)
        
        # Multi-seed test
        multi_seed = test_multi_seed(embeddings, metadata_174k, n_clusters=n_clusters)
        
        tfidf_results[name] = {
            'single_seed': result,
            'multi_seed': multi_seed,
        }
        
        logger.info(f"  Purity original: {result['purity_original']:.4f}, normalized: {result['purity_normalized']:.4f}")
        logger.info(f"  Purity gain: {result['purity_gain_pct']:.2f}%")
        logger.info(f"  NMI original: {result['nmi_original']:.4f}, normalized: {result['nmi_normalized']:.4f}")
        logger.info(f"  NMI change: {result['nmi_change_pct']:.2f}%")
        logger.info(f"  Multi-seed mean gain: {multi_seed['purity_gain_mean']:.2f}% ± {multi_seed['purity_gain_std']:.2f}%")
    
    # 2. Test on dense embeddings at 19k
    logger.info("\n" + "=" * 70)
    logger.info("TESTING DENSE EMBEDDINGS AT 19k SCALE (2000-2002)")
    logger.info("=" * 70)
    
    dense_embeddings, dense_metadata = load_dense_19k_embeddings()
    dense_results = {}
    
    for name, embeddings in dense_embeddings.items():
        logger.info(f"\nTesting {name} ({embeddings.shape[0]} decisions, {embeddings.shape[1]} dims)...")
        
        normalized_areas = get_normalized_legal_areas(dense_metadata)
        n_clusters = len(np.unique(normalized_areas))
        
        result = test_label_normalization(embeddings, dense_metadata, n_clusters=n_clusters)
        multi_seed = test_multi_seed(embeddings, dense_metadata, n_clusters=n_clusters)
        
        dense_results[name] = {
            'single_seed': result,
            'multi_seed': multi_seed,
        }
        
        logger.info(f"  Purity original: {result['purity_original']:.4f}, normalized: {result['purity_normalized']:.4f}")
        logger.info(f"  Purity gain: {result['purity_gain_pct']:.2f}%")
        logger.info(f"  NMI original: {result['nmi_original']:.4f}, normalized: {result['nmi_normalized']:.4f}")
        logger.info(f"  NMI change: {result['nmi_change_pct']:.2f}%")
        logger.info(f"  Multi-seed mean gain: {multi_seed['purity_gain_mean']:.2f}% ± {multi_seed['purity_gain_std']:.2f}%")
    
    # Save results
    from datetime import datetime
    all_results = {
        'tfidf_174k': tfidf_results,
        'dense_19k': dense_results,
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'tfidf_representations_tested': len(tfidf_results),
            'dense_representations_tested': len(dense_results),
            'normalization_rules_count': len(LEGAL_AREA_NORMALIZATIONS),
        }
    }
    
    output_file = OUTPUT_DIR / f"v17b_label_normalization_174k_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "v17b_label_normalization_174k_test_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary report
    logger.info("\n" + "=" * 70)
    logger.info("v17b LABEL NORMALIZATION GENERALIZATION TEST - SUMMARY")
    logger.info("=" * 70)
    
    logger.info(f"\n{'Representation':<45} {'Labels':>6} {'Purity Gain':>12} {'NMI Change':>10} {'Multi-seed':>12}")
    logger.info("-" * 90)
    
    for name, res in tfidf_results.items():
        ss = res['single_seed']
        ms = res['multi_seed']
        logger.info(f"{name:<45} {ss['unique_normalized_labels']:>6} {ss['purity_gain_pct']:>11.2f}% {ss['nmi_change_pct']:>9.2f}% {ms['purity_gain_mean']:>11.2f}%")
    
    for name, res in dense_results.items():
        ss = res['single_seed']
        ms = res['multi_seed']
        logger.info(f"{name:<45} {ss['unique_normalized_labels']:>6} {ss['purity_gain_pct']:>11.2f}% {ss['nmi_change_pct']:>9.2f}% {ms['purity_gain_mean']:>11.2f}%")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results


if __name__ == "__main__":
    main()