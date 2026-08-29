#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Standalone Benchmark Validation

Runs key benchmarks from the 16-benchmark suite on the best representations
using standalone implementations (no relative import issues).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/standalone_benchmarks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Chamber to branch mapping
CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber: str) -> str:
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = meta.get("branch") or assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


# ============================================================
# ADVERSARIAL BENCHMARKS (from evaluation tests)
# ============================================================

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = 20) -> Dict:
    """Adversarial test: measure language dominance in nearest neighbors."""
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    
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
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
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


# ============================================================
# CROSS-LANGUAGE BENCHMARKS (from evaluation tests)
# ============================================================

def cross_language_neighbor_quality(embeddings: np.ndarray, metadata: List[Dict], k: int = 10) -> Dict:
    """Measure cross-language neighbor quality."""
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    cross_lang_same_branch = []
    same_lang_same_branch = []
    
    for i in range(len(embeddings)):
        lang_i = languages[i]
        branch_i = branches[i]
        
        cross_count = 0
        same_count = 0
        cross_total = 0
        same_total = 0
        
        for n_idx in neighbors[i]:
            lang_n = languages[n_idx]
            branch_n = branches[n_idx]
            
            if branch_n == branch_i:
                if lang_n != lang_i:
                    cross_total += 1
                    if lang_n != lang_i:
                        cross_count += 1
                else:
                    same_total += 1
                    if lang_n == lang_i:
                        same_count += 1
        
        if cross_total > 0:
            cross_lang_same_branch.append(cross_count / cross_total)
        if same_total > 0:
            same_lang_same_branch.append(same_count / same_total)
    
    return {
        'cross_lang_same_branch_mean': float(np.mean(cross_lang_same_branch)) if cross_lang_same_branch else 0.0,
        'same_lang_same_branch_mean': float(np.mean(same_lang_same_branch)) if same_lang_same_branch else 0.0,
        'invariance_gap': float(np.mean(same_lang_same_branch) - np.mean(cross_lang_same_branch)) if cross_lang_same_branch and same_lang_same_branch else 0.0,
        'status': 'PASS' if (cross_lang_same_branch and np.mean(cross_lang_same_branch) > 0.3) else 'FAIL',
    }


def zero_shot_cross_language_transfer(embeddings: np.ndarray, metadata: List[Dict], n_clusters: int = 16) -> Dict:
    """Zero-shot cross-language transfer test."""
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    unique_langs = list(set(languages))
    
    if len(unique_langs) < 2:
        return {'status': 'SKIP', 'note': 'Need at least 2 languages'}
    
    nmi_scores = []
    
    for source_lang in unique_langs:
        for target_lang in unique_langs:
            if source_lang == target_lang:
                continue
            
            source_mask = np.array([l == source_lang for l in languages])
            target_mask = np.array([l == target_lang for l in languages])
            
            if np.sum(source_mask) < n_clusters or np.sum(target_mask) < n_clusters:
                continue
            
            # Cluster source language
            source_emb = embeddings[source_mask]
            source_branches = np.array(branches)[source_mask]
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            source_labels = kmeans.fit_predict(source_emb)
            
            # Project target language onto source centroids
            target_emb = embeddings[target_mask]
            target_branches = np.array(branches)[target_mask]
            
            target_labels = kmeans.predict(target_emb)
            
            # Compute NMI for each language
            source_nmi = normalized_mutual_info_score(source_branches, source_labels)
            target_nmi = normalized_mutual_info_score(target_branches, target_labels)
            
            nmi_scores.append({
                'source_lang': source_lang,
                'target_lang': target_lang,
                'source_nmi': source_nmi,
                'target_nmi': target_nmi,
                'transfer_gap': source_nmi - target_nmi
            })
    
    if not nmi_scores:
        return {'status': 'SKIP', 'note': 'Insufficient data per language'}
    
    zero_shot_mean = np.mean([s['target_nmi'] for s in nmi_scores])
    in_domain_mean = np.mean([s['source_nmi'] for s in nmi_scores])
    transfer_gap = in_domain_mean - zero_shot_mean
    
    return {
        'zero_shot_mean_nmi': float(zero_shot_mean),
        'in_domain_mean_nmi': float(in_domain_mean),
        'transfer_gap': float(transfer_gap),
        'status': 'PASS' if transfer_gap < 0.15 else 'FAIL',
        'details': nmi_scores
    }


def language_specific_representation_quality(embeddings: np.ndarray, metadata: List[Dict], n_clusters: int = 16) -> Dict:
    """Test representation quality within each language."""
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    unique_langs = list(set(languages))
    
    nmi_scores = []
    
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) < n_clusters:
            continue
        
        lang_emb = embeddings[mask]
        lang_branches = np.array(branches)[mask]
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lang_emb)
        
        nmi = normalized_mutual_info_score(lang_branches, labels)
        nmi_scores.append({'language': lang, 'nmi': float(nmi)})
    
    if not nmi_scores:
        return {'status': 'SKIP', 'note': 'Insufficient data per language'}
    
    mean_nmi = np.mean([s['nmi'] for s in nmi_scores])
    std_nmi = np.std([s['nmi'] for s in nmi_scores])
    
    return {
        'mean_nmi': float(mean_nmi),
        'std_nmi': float(std_nmi),
        'per_language': nmi_scores,
        'status': 'PASS' if mean_nmi > 0.4 else 'FAIL'
    }


# ============================================================
# JURIST USABILITY BENCHMARKS
# ============================================================

def simulate_cluster_coherence_rating(embeddings: np.ndarray, branches: np.ndarray, languages: np.ndarray, n_clusters: int = 16) -> Dict:
    """Simulate jurist cluster coherence rating."""
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    branch_purities = []
    lang_purities = []
    
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        if np.sum(mask) == 0:
            continue
        
        cluster_branches = branches[mask]
        cluster_langs = languages[mask]
        
        if len(cluster_branches) > 0:
            branch_counts = Counter(cluster_branches)
            branch_purity = max(branch_counts.values()) / len(cluster_branches)
            branch_purities.append(branch_purity)
        
        if len(cluster_langs) > 0:
            lang_counts = Counter(cluster_langs)
            lang_purity = max(lang_counts.values()) / len(cluster_langs)
            lang_purities.append(lang_purity)
    
    mean_branch_purity = np.mean(branch_purities) if branch_purities else 0
    mean_language_purity = np.mean(lang_purities) if lang_purities else 0
    
    # Jurist would want high branch purity (legal coherence) and low language purity
    coherence_score = mean_branch_purity - mean_language_purity
    
    return {
        'mean_branch_purity': float(mean_branch_purity),
        'mean_language_purity': float(mean_language_purity),
        'coherence_score': float(coherence_score),
        'status': 'PASS' if mean_branch_purity > 0.7 else 'FAIL',
    }


def simulate_zoom_task(embeddings: np.ndarray, branches: np.ndarray, languages: np.ndarray, 
                       valid_indices: List[int], cluster_assignments_path: Path) -> Dict:
    """Simulate jurist zoom task - check if zoom reveals more specific structure."""
    # Load hierarchical cluster assignments
    try:
        with open(cluster_assignments_path, 'r') as f:
            cluster_data = json.load(f)
        
        coarse_labels = np.array(cluster_data.get('coarse_labels', []))
        fine_labels = np.array(cluster_data.get('fine_labels', []))
        
        if len(coarse_labels) == 0 or len(fine_labels) == 0:
            return {'status': 'SKIP', 'note': 'No cluster assignments found'}
        
        # Align to valid indices
        coarse_valid = coarse_labels[valid_indices]
        fine_valid = fine_labels[valid_indices]
        branches_valid = branches
        languages_valid = languages
        
        # Compute purity at each level
        def compute_purity(labels, truth):
            purities = []
            for label in np.unique(labels):
                mask = labels == label
                if np.sum(mask) == 0:
                    continue
                counts = Counter(truth[mask])
                purities.append(max(counts.values()) / np.sum(mask))
            return np.mean(purities) if purities else 0
        
        coarse_purity = compute_purity(coarse_valid, branches_valid)
        fine_purity = compute_purity(fine_valid, branches_valid)
        
        # Jurist wants fine > coarse
        return {
            'coarse_purity': float(coarse_purity),
            'fine_purity': float(fine_purity),
            'improvement': float(fine_purity - coarse_purity),
            'status': 'PASS' if fine_purity > coarse_purity else 'FAIL'
        }
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)}


def simulate_cross_language_retrieval(embeddings: np.ndarray, branches: np.ndarray, languages: np.ndarray, k: int = 10) -> Dict:
    """Simulate cross-language retrieval task."""
    unique_langs = list(set(languages))
    recalls = []
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    for source_lang in unique_langs:
        source_mask = np.array([l == source_lang for l in languages])
        source_indices = np.where(source_mask)[0]
        
        if len(source_indices) == 0:
            continue
        
        for target_lang in unique_langs:
            if source_lang == target_lang:
                continue
            
            target_mask = np.array([l == target_lang for l in languages])
            target_indices = set(np.where(target_mask)[0])
            
            if len(target_indices) == 0:
                continue
            
            # For each source doc, check if any target-lang neighbor shares branch
            hits = 0
            for src_idx in source_indices:
                src_branch = branches[src_idx]
                neighbor_branches = branches[neighbors[src_idx]]
                neighbor_langs = languages[neighbors[src_idx]]
                
                # Check if any neighbor is target_lang and same branch
                for nb, nl in zip(neighbor_branches, neighbor_langs):
                    if nl == target_lang and nb == src_branch:
                        hits += 1
                        break
            
            recall = hits / len(source_indices) if len(source_indices) > 0 else 0
            recalls.append(recall)
    
    mean_recall = np.mean(recalls) if recalls else 0
    
    return {
        'mean_cross_language_recall_at_k': float(mean_recall),
        'status': 'PASS' if mean_recall > 0.2 else 'FAIL',
    }


# ============================================================
# BOILERPLATE RESISTANCE
# ============================================================

def boilerplate_resistance_test(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Test resistance to procedural boilerplate."""
    # Identify decisions with high boilerplate content (e.g., short erwaegungen)
    # This is a simplified version - real test would analyze text content
    
    # Use legal_area as proxy for substantive content
    legal_areas = [m.get('legal_area', '') for m in metadata]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    
    # Cluster and check if clusters are dominated by legal_area or by procedural markers
    kmeans = KMeans(n_clusters=16, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    nmi = normalized_mutual_info_score(legal_areas, labels)
    
    # High NMI with legal_area means representation captures substantive law
    return {
        'legal_area_nmi': float(nmi),
        'status': 'PASS' if nmi > 0.4 else 'FAIL',
        'note': 'Higher NMI with legal_area indicates better boilerplate resistance'
    }


# ============================================================
# SCALE STABILITY
# ============================================================

def scale_stability_test(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Test stability under corpus subsampling."""
    n = len(embeddings)
    if n < 500:
        return {'status': 'SKIP', 'note': 'Insufficient data for subsampling'}
    
    # Subsample 80% multiple times
    nmi_scores = []
    for seed in range(5):
        np.random.seed(seed)
        sample_size = int(0.8 * n)
        indices = np.random.choice(n, sample_size, replace=False)
        indices = np.sort(indices)
        
        sample_emb = embeddings[indices]
        sample_meta = [metadata[i] for i in indices]
        
        # Cluster full and sample
        kmeans_full = KMeans(n_clusters=16, random_state=42, n_init=10)
        labels_full = kmeans_full.fit_predict(embeddings)
        
        kmeans_sample = KMeans(n_clusters=16, random_state=42, n_init=10)
        labels_sample = kmeans_sample.fit_predict(sample_emb)
        
        # Compare cluster assignments on overlap
        full_labels_on_sample = labels_full[indices]
        nmi = normalized_mutual_info_score(full_labels_on_sample, labels_sample)
        nmi_scores.append(nmi)
    
    mean_nmi = np.mean(nmi_scores)
    std_nmi = np.std(nmi_scores)
    
    return {
        'mean_stability_nmi': float(mean_nmi),
        'std_stability_nmi': float(std_nmi),
        'status': 'PASS' if mean_nmi > 0.7 else 'FAIL',
        'note': 'Higher NMI between full and subsampled clustering indicates better stability'
    }


# ============================================================
# JURIVOC HIERARCHY ALIGNMENT
# ============================================================

def jurivoc_hierarchy_alignment(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Test alignment with Jurivoc hierarchy."""
    # Use legal_area as proxy for Jurivoc categories
    legal_areas = [m.get('legal_area', '') for m in metadata]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    
    kmeans = KMeans(n_clusters=16, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    nmi = normalized_mutual_info_score(legal_areas, labels)
    ari = adjusted_rand_score(legal_areas, labels)
    
    return {
        'jurivoc_nmi': float(nmi),
        'jurivoc_ari': float(ari),
        'status': 'PASS' if nmi > 0.5 else 'FAIL',
        'note': 'NMI with legal_area/Jurivoc categories'
    }


# ============================================================
# MAIN
# ============================================================

def load_canonical_corpus() -> Tuple[np.ndarray, List[Dict]]:
    """Load the 1200-decision expanded corpus with sentence transformer embeddings."""
    from sentence_transformers import SentenceTransformer
    
    corpus = []
    with open("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    
    metadata = []
    with open("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            metadata.append(json.loads(line))
    
    for m in metadata:
        if 'branch' not in m:
            m['branch'] = assign_branch(m.get('chamber', ''))
    
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    texts = [d.get('erwaegungen_text', '')[:2000] for d in corpus]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    return embeddings, metadata


def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    languages = sorted(set(m['language'] for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def load_signals_v2() -> Dict[str, Any]:
    signals = {}
    with open("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v2.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    return signals


def build_cited_decisions_tfidf(signals: Dict[str, Any], metadata: List[Dict], max_features: int = 5000) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        cited = sig.get('cited_decisions', [])
        if cited:
            texts.append(" ".join(cited))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        return np.zeros((len(metadata), 128))
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=max_features, min_df=2, max_df=0.95,
        ngram_range=(1, 2), sublinear_tf=True, lowercase=True, strip_accents='unicode'
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    return full_emb


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    svd = TruncatedSVD(n_components=target_dim, random_state=42)
    return svd.fit_transform(emb)


def create_hybrid_representation(legal_emb: np.ndarray, baseline_emb: np.ndarray, alpha: float = 0.5, target_dim: int = 64) -> np.ndarray:
    from sklearn.preprocessing import normalize
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    return normalize(hybrid, norm='l2', axis=1)


def run_all_benchmarks(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    logger.info(f"\n{'='*70}")
    logger.info(f"Running benchmarks for {name}")
    logger.info(f"{'='*70}")
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    emb_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    results = {}
    
    # 1. Adversarial language dominance
    logger.info("1. Adversarial language dominance...")
    results['adversarial_language_dominance'] = adversarial_language_dominance(emb_valid, meta_valid)
    logger.info(f"   mean_dominance: {results['adversarial_language_dominance']['mean_language_dominance']:.4f}, status: {results['adversarial_language_dominance']['status']}")
    
    # 2. Jurist pairwise preference
    logger.info("2. Jurist pairwise preference...")
    results['jurist_pairwise_preference'] = simulate_pairwise_preference(emb_valid, branches, languages)
    logger.info(f"   jurist_would_succeed_rate: {results['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f}, status: {results['jurist_pairwise_preference']['status']}")
    
    # 3. Cross-language neighbor quality
    logger.info("3. Cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(emb_valid, meta_valid)
    logger.info(f"   invariance_gap: {results['cross_language_neighbor_quality'].get('invariance_gap', 'N/A'):.4f}, status: {results['cross_language_neighbor_quality'].get('status', 'N/A')}")
    
    # 4. Zero-shot cross-language transfer
    logger.info("4. Zero-shot cross-language transfer...")
    results['zero_shot_cross_language_transfer'] = zero_shot_cross_language_transfer(emb_valid, meta_valid)
    logger.info(f"   transfer_gap: {results['zero_shot_cross_language_transfer'].get('transfer_gap', 'N/A'):.4f}, status: {results['zero_shot_cross_language_transfer'].get('status', 'N/A')}")
    
    # 5. Language-specific representation quality
    logger.info("5. Language-specific representation quality...")
    results['language_specific_representation_quality'] = language_specific_representation_quality(emb_valid, meta_valid)
    logger.info(f"   mean_nmi: {results['language_specific_representation_quality'].get('mean_nmi', 'N/A'):.4f}, status: {results['language_specific_representation_quality'].get('status', 'N/A')}")
    
    # 6. Cluster coherence rating
    logger.info("6. Cluster coherence rating...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(emb_valid, branches, languages)
    logger.info(f"   mean_branch_purity: {results['cluster_coherence_rating'].get('mean_branch_purity', 'N/A'):.4f}, status: {results['cluster_coherence_rating'].get('status', 'N/A')}")
    
    # 7. Zoom task
    logger.info("7. Zoom task...")
    zoom_path = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json")
    results['zoom_task'] = simulate_zoom_task(emb_valid, branches, languages, valid_indices, zoom_path)
    logger.info(f"   coarse_purity: {results['zoom_task'].get('coarse_purity', 'N/A')}, status: {results['zoom_task'].get('status', 'N/A')}")
    
    # 8. Cross-language retrieval
    logger.info("8. Cross-language retrieval...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(emb_valid, branches, languages)
    logger.info(f"   mean_cross_language_recall_at_k: {results['cross_language_retrieval'].get('mean_cross_language_recall_at_k', 'N/A'):.4f}, status: {results['cross_language_retrieval'].get('status', 'N/A')}")
    
    # 9. Boilerplate resistance
    logger.info("9. Boilerplate resistance...")
    results['boilerplate_resistance'] = boilerplate_resistance_test(embeddings, metadata)
    logger.info(f"   legal_area_nmi: {results['boilerplate_resistance'].get('legal_area_nmi', 'N/A'):.4f}, status: {results['boilerplate_resistance'].get('status', 'N/A')}")
    
    # 10. Scale stability
    logger.info("10. Scale stability...")
    results['scale_stability'] = scale_stability_test(embeddings, metadata)
    logger.info(f"   mean_stability_nmi: {results['scale_stability'].get('mean_stability_nmi', 'N/A'):.4f}, status: {results['scale_stability'].get('status', 'N/A')}")
    
    # 11. Jurivoc hierarchy alignment
    logger.info("11. Jurivoc hierarchy alignment...")
    results['jurivoc_hierarchy_alignment'] = jurivoc_hierarchy_alignment(embeddings, metadata)
    logger.info(f"   jurivoc_nmi: {results['jurivoc_hierarchy_alignment'].get('jurivoc_nmi', 'N/A'):.4f}, status: {results['jurivoc_hierarchy_alignment'].get('status', 'N/A')}")
    
    # Summary
    benchmark_keys = [
        'adversarial_language_dominance',
        'jurist_pairwise_preference',
        'cross_language_neighbor_quality',
        'zero_shot_cross_language_transfer',
        'language_specific_representation_quality',
        'cluster_coherence_rating',
        'zoom_task',
        'cross_language_retrieval',
        'boilerplate_resistance',
        'scale_stability',
        'jurivoc_hierarchy_alignment',
    ]
    
    passed = sum(1 for k in benchmark_keys if results.get(k, {}).get('status') == 'PASS')
    failed = sum(1 for k in benchmark_keys if results.get(k, {}).get('status') == 'FAIL')
    skipped = sum(1 for k in benchmark_keys if results.get(k, {}).get('status') in ['SKIP', 'ERROR'])
    total = len(benchmark_keys)
    
    results['summary'] = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'pass_rate': passed / (total - skipped) if total > skipped else 0,
    }
    
    logger.info(f"\nSummary for {name}: {passed}/{total-skipped} passed, {failed} failed, {skipped} skipped")
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - Standalone Benchmark Validation")
    logger.info("=" * 70)
    
    # Load canonical corpus and create representations
    logger.info("\n1. Loading canonical corpus and creating representations...")
    st_embeddings, metadata = load_canonical_corpus()
    
    logger.info("Creating center_projected...")
    center_projected = create_center_projected(st_embeddings, metadata)
    
    logger.info("Loading signals and building cited_decisions_tfidf...")
    signals = load_signals_v2()
    cited_decisions_tfidf = build_cited_decisions_tfidf(signals, metadata)
    
    logger.info("Creating hybrid_cited_0.3...")
    hybrid_cited_03 = create_hybrid_representation(cited_decisions_tfidf, center_projected, 0.3)
    
    # Run benchmarks on each representation
    representations = {
        'center_projected': center_projected,
        'hybrid_cited_0.3': hybrid_cited_03,
        'cited_decisions_tfidf': cited_decisions_tfidf,
    }
    
    all_results = {}
    
    for name, emb in representations.items():
        results = run_all_benchmarks(emb, metadata, name)
        all_results[name] = results
        
        with open(OUTPUT_DIR / f"standalone_{name}_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    # Save all results
    with open(OUTPUT_DIR / "standalone_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary comparison
    logger.info("\n" + "=" * 100)
    logger.info("STANDALONE BENCHMARK SUITE SUMMARY")
    logger.info("=" * 100)
    
    benchmark_keys = [
        'adversarial_language_dominance',
        'jurist_pairwise_preference',
        'cross_language_neighbor_quality',
        'zero_shot_cross_language_transfer',
        'language_specific_representation_quality',
        'cluster_coherence_rating',
        'zoom_task',
        'cross_language_retrieval',
        'boilerplate_resistance',
        'scale_stability',
        'jurivoc_hierarchy_alignment',
    ]
    
    logger.info(f"\n{'Benchmark':<40} {'center_projected':<20} {'hybrid_cited_0.3':<20} {'cited_decisions_tfidf':<20}")
    logger.info("-" * 100)
    
    for bm_name in benchmark_keys:
        row = f"{bm_name:<40}"
        for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
            res = all_results[name].get(bm_name, {})
            if 'error' in res:
                row += f" {'ERROR':<20}"
            elif 'status' in res:
                status = res['status']
                row += f" {status:<20}"
            else:
                row += f" {'N/A':<20}"
        logger.info(row)
    
    # Overall summary
    logger.info("\n" + "=" * 80)
    logger.info("OVERALL PASS RATES")
    logger.info("=" * 80)
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        summary = all_results[name].get('summary', {})
        logger.info(f"{name}: {summary.get('passed', 0)}/{summary.get('total', 0) - summary.get('skipped', 0)} passed ({summary.get('pass_rate', 0):.1%})")
    
    # Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS")
    logger.info("=" * 80)
    
    # Compare adversarial gates
    logger.info("\nAdversarial Gates (PRIMARY):")
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        ld = all_results[name]['adversarial_language_dominance']
        jp = all_results[name]['jurist_pairwise_preference']
        both = ld['status'] == 'PASS' and jp['status'] == 'PASS'
        logger.info(f"  {name}: LangDom={ld['mean_language_dominance']:.4f} ({ld['status']}), Jurist={jp['jurist_would_succeed_rate']:.4f} ({jp['status']}), Both={'✓' if both else '✗'}")
    
    # Compare cross-language
    logger.info("\nCross-Language Robustness:")
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        clnq = all_results[name]['cross_language_neighbor_quality']
        zscl = all_results[name]['zero_shot_cross_language_transfer']
        lsrq = all_results[name]['language_specific_representation_quality']
        logger.info(f"  {name}: CLNQ gap={clnq.get('invariance_gap', 0):.4f}, ZS transfer_gap={zscl.get('transfer_gap', 0):.4f}, LS mean_nmi={lsrq.get('mean_nmi', 0):.4f}")
    
    # Compare jurist usability
    logger.info("\nJurist Usability:")
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        ccr = all_results[name]['cluster_coherence_rating']
        zt = all_results[name]['zoom_task']
        clr = all_results[name]['cross_language_retrieval']
        logger.info(f"  {name}: ClusterCoherence={ccr.get('mean_branch_purity', 0):.4f}, ZoomImprovement={zt.get('improvement', 0):.4f}, CrossLangRecall={clr.get('mean_cross_language_recall_at_k', 0):.4f}")
    
    # Boilerplate and scale
    logger.info("\nBoilerplate Resistance & Scale Stability:")
    for name in ['center_projected', 'hybrid_cited_0.3', 'cited_decisions_tfidf']:
        bp = all_results[name]['boilerplate_resistance']
        ss = all_results[name]['scale_stability']
        jh = all_results[name]['jurivoc_hierarchy_alignment']
        logger.info(f"  {name}: BoilerplateNMI={bp.get('legal_area_nmi', 0):.4f}, ScaleStability={ss.get('mean_stability_nmi', 0):.4f}, JurivocNMI={jh.get('jurivoc_nmi', 0):.4f}")
    
    logger.info("\n=== Standalone Benchmark Validation Complete ===")
    return all_results


if __name__ == "__main__":
    main()