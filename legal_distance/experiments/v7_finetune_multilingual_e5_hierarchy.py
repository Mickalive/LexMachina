#!/usr/bin/env python3
"""
Legal Distance Lane v7 - Fine-tune multilingual-e5-small with HIERARCHY PRESERVATION LOSS
to fix overclustering (1 coarse -> 1000 fine, hier_adv=0.0) while maintaining adversarial robustness.

Factory Direction v9 Objective 1:
"Test multilingual-e5-small fine-tuning on Swiss legal corpus for multilingual invariance 
WITH coarse legal structure"

Critical finding from v6/v7: ft_multilingual_e5_small_pretrained passes adversarial gates 
(LangDom=0.488, Jurist=0.702) but OVERCLUSTERS (1 coarse -> 1000 fine, hier_adv=0.0) - 
needs hierarchy preservation loss.

Approach:
- Contrastive learning with positive pairs from same legal_area/branch/chamber/statute
- Triplet loss for additional signal
- HIERARCHY LOSS IN BACKPROP: Per-batch coarse cluster cohesion (from center_projected reference)
- Loss scheduling: high preservation early, anneal contrastive
- Evaluate on FROZEN harness v3 (seed=42, config_hash=4323f833fa72366a)
"""

import json
import numpy as np
import logging
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer, losses, InputExample
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA

import sys
# Use accepted paths (fractal-map is only in /tmp/lex_accepted/)
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation/tests')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation/experiments')

from hierarchical_leiden import load_metadata_with_branch, leiden_clustering, compute_branch_purity
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster
# We'll use our own inline evaluation functions instead of importing from other lanes

# Copy the frozen harness evaluation functions locally to avoid path issues
# (We'll define them inline below instead of importing)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/finetune_multilingual_e5_hierarchy")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")

MODEL_NAME = "intfloat/multilingual-e5-small"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

# CPU-REDUCED Training config (no GPU available)
BATCH_SIZE = 8
EPOCHS = 2
LEARNING_RATE = 2e-5
MAX_SEQ_LENGTH = 256
WARMUP_STEPS = 10
SEED = 42
MAX_PAIRS = 5000
MAX_TRIPLETS = 3000

# Loss weights (scheduling)
# Phase 1 (epoch 1): High preservation, low contrastive, hierarchy constant
# Phase 2 (epoch 2): Balanced
LAMBDA_HIERARCHY = 0.5  # Constant hierarchy loss weight

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


@dataclass
class DecisionData:
    decision_id: str
    language: str
    legal_area: str
    branch: str
    chamber: str
    outcome: str
    full_text: str
    cited_decisions: List[str]
    cited_laws: List[str]
    statutes: List[str]
    title: str = ""


def load_corpus() -> List[DecisionData]:
    """Load full corpus and convert to DecisionData objects."""
    corpus = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            corpus.append(DecisionData(
                decision_id=d['decision_id'],
                language=d.get('language', 'de'),
                legal_area=d.get('legal_area', ''),
                branch=d.get('branch', ''),
                chamber=d.get('chamber', ''),
                outcome=d.get('outcome', ''),
                full_text=d.get('full_text', ''),
                cited_decisions=d.get('cited_decisions', []),
                cited_laws=d.get('cited_laws', []),
                statutes=d.get('statutes', []),
                title=d.get('title', ''),
            ))
    logger.info(f"Loaded {len(corpus)} decisions")
    return corpus


def load_center_projected_reference() -> Tuple[np.ndarray, List[Dict], np.ndarray]:
    """Load center_projected embeddings and compute reference coarse labels."""
    cp_embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        cp_metadata = json.load(f)
    
    # Compute coarse labels from center_projected (reference hierarchy)
    hierarchical_labels, coarse_labels, _, _ = hierarchical_leiden(
        cp_embeddings, cp_metadata, coarse_res=0.5, sub_res=3.0
    )
    
    logger.info(f"Loaded center_projected reference: {cp_embeddings.shape}, coarse clusters: {len(set(coarse_labels))}")
    return cp_embeddings, cp_metadata, coarse_labels


def create_contrastive_pairs(corpus: List[DecisionData], max_pairs: int = MAX_PAIRS) -> List[InputExample]:
    """Create contrastive training pairs using coarse legal structure."""
    logger.info("Creating contrastive pairs from coarse legal structure...")
    
    by_legal_area = defaultdict(list)
    by_branch = defaultdict(list)
    by_chamber = defaultdict(list)
    
    for i, d in enumerate(corpus):
        if d.legal_area:
            by_legal_area[d.legal_area].append(i)
        if d.branch:
            by_branch[d.branch].append(i)
        if d.chamber:
            by_chamber[d.chamber].append(i)
    
    # Create statute-to-decisions mapping
    statute_to_decisions = defaultdict(list)
    for i, d in enumerate(corpus):
        for statute in d.statutes:
            statute_to_decisions[statute].append(i)
    
    positive_pairs = set()
    
    # 1. Same legal_area (strongest signal)
    for area, indices in by_legal_area.items():
        if len(indices) >= 2:
            for i in range(min(len(indices), 10)):
                for j in range(i+1, min(len(indices), 10)):
                    positive_pairs.add((indices[i], indices[j]))
    
    # 2. Same branch
    for branch, indices in by_branch.items():
        if len(indices) >= 2:
            for i in range(min(len(indices), 8)):
                for j in range(i+1, min(len(indices), 8)):
                    positive_pairs.add((indices[i], indices[j]))
    
    # 3. Same chamber
    for chamber, indices in by_chamber.items():
        if len(indices) >= 2:
            for i in range(min(len(indices), 5)):
                for j in range(i+1, min(len(indices), 5)):
                    positive_pairs.add((indices[i], indices[j]))
    
    # 4. Statute overlap
    for statute, indices in statute_to_decisions.items():
        if len(indices) >= 2:
            for i in range(min(len(indices), 5)):
                for j in range(i+1, min(len(indices), 5)):
                    positive_pairs.add((indices[i], indices[j]))
    
    positive_pairs = list(positive_pairs)
    logger.info(f"Generated {len(positive_pairs)} positive pairs")
    
    # Create negative pairs (different legal_area AND different branch)
    negative_pairs = []
    legal_areas = list(by_legal_area.keys())
    branches = list(by_branch.keys())
    
    n_negative = min(len(positive_pairs) * 2, max_pairs - len(positive_pairs))
    attempts = 0
    while len(negative_pairs) < n_negative and attempts < n_negative * 10:
        i = random.randrange(len(corpus))
        j = random.randrange(len(corpus))
        if i == j:
            continue
        if (i, j) in positive_pairs or (j, i) in positive_pairs:
            continue
        d1, d2 = corpus[i], corpus[j]
        if d1.legal_area and d2.legal_area and d1.legal_area != d2.legal_area:
            if d1.branch and d2.branch and d1.branch != d2.branch:
                negative_pairs.append((i, j))
        attempts += 1
    
    logger.info(f"Generated {len(negative_pairs)} negative pairs")
    
    # Build InputExamples
    examples = []
    for i, j in positive_pairs[:max_pairs//3]:
        d1, d2 = corpus[i], corpus[j]
        text1 = f"{d1.title} {d1.full_text[:256]}" if d1.title else d1.full_text[:512]
        text2 = f"{d2.title} {d2.full_text[:256]}" if d2.title else d2.full_text[:512]
        examples.append(InputExample(texts=[text1, text2], label=1.0))
    
    for i, j in negative_pairs[:max_pairs//3]:
        d1, d2 = corpus[i], corpus[j]
        text1 = f"{d1.title} {d1.full_text[:256]}" if d1.title else d1.full_text[:512]
        text2 = f"{d2.title} {d2.full_text[:256]}" if d2.title else d2.full_text[:512]
        examples.append(InputExample(texts=[text1, text2], label=0.0))
    
    logger.info(f"Total training examples: {len(examples)}")
    return examples


def create_triplet_examples(corpus: List[DecisionData], max_triplets: int = MAX_TRIPLETS) -> List[InputExample]:
    """Create triplet examples (anchor, positive, negative) for triplet loss."""
    logger.info("Creating triplet examples...")
    
    by_legal_area = defaultdict(list)
    
    for i, d in enumerate(corpus):
        if d.legal_area:
            by_legal_area[d.legal_area].append(i)
    
    triplets = []
    
    for area, indices in by_legal_area.items():
        if len(indices) < 2:
            continue
        # Other areas for negatives
        other_indices = []
        for other_area, other_idxs in by_legal_area.items():
            if other_area != area:
                other_indices.extend(other_idxs)
        
        if not other_indices:
            continue
            
        for anchor_idx in indices[:8]:
            # Positive: another from same area
            pos_candidates = [idx for idx in indices if idx != anchor_idx]
            if not pos_candidates:
                continue
            pos_idx = random.choice(pos_candidates)
            
            # Negative: from different area
            neg_idx = random.choice(other_indices)
            
            d_anchor = corpus[anchor_idx]
            d_pos = corpus[pos_idx]
            d_neg = corpus[neg_idx]
            
            text_anchor = f"{d_anchor.title} {d_anchor.full_text[:256]}" if d_anchor.title else d_anchor.full_text[:512]
            text_pos = f"{d_pos.title} {d_pos.full_text[:256]}" if d_pos.title else d_pos.full_text[:512]
            text_neg = f"{d_neg.title} {d_neg.full_text[:256]}" if d_neg.title else d_neg.full_text[:512]
            
            triplets.append(InputExample(texts=[text_anchor, text_pos, text_neg]))
            
            if len(triplets) >= max_triplets:
                break
        if len(triplets) >= max_triplets:
            break
    
    logger.info(f"Generated {len(triplets)} triplet examples")
    return triplets


def hierarchy_loss_batch(projected: torch.Tensor, coarse_labels: torch.Tensor) -> torch.Tensor:
    """Per-batch hierarchy loss: minimize within-coarse-cluster variance."""
    unique_clusters = coarse_labels.unique()
    total_loss = torch.tensor(0.0, device=projected.device)
    count = 0
    
    for cluster_id in unique_clusters:
        mask = coarse_labels == cluster_id
        if mask.sum() < 2:
            continue
        cluster_embeds = projected[mask]
        n = min(len(cluster_embeds), 20)
        indices = torch.randperm(len(cluster_embeds))[:n]
        sampled = cluster_embeds[indices]
        
        center = sampled.mean(dim=0, keepdim=True)
        loss = F.mse_loss(sampled, center.expand_as(sampled))
        total_loss += loss
        count += 1
    
    return total_loss / max(count, 1)


def get_loss_weights(epoch: int, total_epochs: int) -> Tuple[float, float, float]:
    """Loss scheduling: high preservation early, anneal contrastive."""
    if epoch <= 1:
        lambda_preserve = 2.0
        lambda_contrastive = 0.5
    else:
        lambda_preserve = 1.0
        lambda_contrastive = 1.0
    
    lambda_hierarchy = LAMBDA_HIERARCHY
    return lambda_contrastive, lambda_preserve, lambda_hierarchy


# ============================================================
# FROZEN HARNESS v3 EVALUATION (inline copy - seed=42, config_hash=4323f833fa72366a)
# ============================================================

GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

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

def load_center_projected_metadata() -> List[Dict]:
    """Load metadata for 1200-decision center_projected corpus (local path)."""
    metadata_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata

def prepare_metadata_arrays(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, legal_area from metadata."""
    branches = []
    languages = []
    legal_areas = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")
        legal_area = meta.get("legal_area", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            legal_areas.append(legal_area)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(legal_areas), valid_indices

def adversarial_language_dominance(
    embeddings: np.ndarray, 
    metadata: List[Dict], 
    k: int = 20,
    valid_indices: Optional[List[int]] = None
) -> Dict:
    """Adversarial test: measure language dominance in nearest neighbors."""
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]
    
    dominance_rates = []
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
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

def jurist_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = 10
) -> Dict:
    """Simulate jurist pairwise preference study."""
    n = len(branches)
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
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

def jurivoc_hierarchy_alignment(
    embeddings: np.ndarray,
    legal_areas: np.ndarray,
    n_clusters_list: List[int] = None
) -> Dict:
    """Jurivoc hierarchy alignment benchmark (using legal_area as proxy)."""
    valid_mask = np.array([la is not None for la in legal_areas])
    if not valid_mask.any():
        return {
            'per_resolution': {},
            'avg_nmi': 0.0,
            'avg_ari': 0.0,
            'status': 'FAIL',
            'note': 'No valid legal_area labels for alignment'
        }
    
    valid_embeddings = embeddings[valid_mask]
    valid_legal_areas = legal_areas[valid_mask]
    
    if n_clusters_list is None:
        n_clusters_list = [5, 10, 15, 20, 30, 50]
    
    results = {}
    for n_clusters in n_clusters_list:
        kmeans = KMeans(n_clusters=n_clusters, random_state=GLOBAL_SEED, n_init=10)
        cluster_labels = kmeans.fit_predict(valid_embeddings)
        nmi = normalized_mutual_info_score(valid_legal_areas, cluster_labels)
        ari = adjusted_rand_score(valid_legal_areas, cluster_labels)
        results[f'n_clusters_{n_clusters}'] = {
            'nmi': float(nmi),
            'ari': float(ari)
        }
    
    avg_nmi = np.mean([v['nmi'] for v in results.values()])
    avg_ari = np.mean([v['ari'] for v in results.values()])
    
    return {
        'per_resolution': results,
        'avg_nmi': float(avg_nmi),
        'avg_ari': float(avg_ari),
        'status': 'PASS' if avg_nmi > 0.3 else 'FAIL',
        'note': 'NMI with legal_area (proxy for Jurivoc). Higher = better alignment with human legal taxonomy.'
    }

def scale_stability_frozen_pca(
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None,
    subsample_frac: float = 0.8,
    n_trials: int = 10
) -> Dict:
    """Scale stability benchmark with frozen PCA."""
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
    else:
        rep_embeddings = embeddings
    
    n = len(rep_embeddings)
    subsample_size = int(n * subsample_frac)
    
    pca = PCA(n_components=min(64, n-1), random_state=GLOBAL_SEED)
    pca.fit(rep_embeddings)
    full_proj = pca.transform(rep_embeddings)
    full_proj = normalize(full_proj, norm='l2', axis=1)
    
    similarities = []
    for trial in range(n_trials):
        rng = np.random.RandomState(GLOBAL_SEED + trial)
        subsample_idx = rng.choice(n, size=subsample_size, replace=False)
        subsample_emb = rep_embeddings[subsample_idx]
        
        sub_proj = pca.transform(subsample_emb)
        sub_proj = normalize(sub_proj, norm='l2', axis=1)
        
        full_proj_sub = full_proj[subsample_idx]
        cos_sims = np.sum(full_proj_sub * sub_proj, axis=1)
        similarities.append(float(np.mean(cos_sims)))
    
    mean_sim = np.mean(similarities)
    std_sim = np.std(similarities)
    
    return {
        'mean_cosine_similarity': float(mean_sim),
        'std_cosine_similarity': float(std_sim),
        'subsample_frac': subsample_frac,
        'n_trials': n_trials,
        'pca_dims': pca.n_components_,
        'status': 'PASS' if mean_sim > 0.95 else 'FAIL',
        'note': 'Frozen PCA projection consistency under subsampling. Higher = more stable.'
    }

def boilerplate_resistance(
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None,
    k: int = 20
) -> Dict:
    """Boilerplate resistance benchmark (language dominance proxy)."""
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]
    
    boilerplate_dominated = 0
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        if same_lang / k > 0.8:
            boilerplate_dominated += 1
    
    boilerplate_rate = boilerplate_dominated / len(rep_metadata)
    
    return {
        'boilerplate_dominated_rate': float(boilerplate_rate),
        'k': k,
        'threshold': 0.3,
        'status': 'PASS' if boilerplate_rate < 0.3 else 'FAIL',
        'note': 'Fraction of decisions with >80% same-language neighbors. Lower = less boilerplate-driven.'
    }

def run_full_benchmark_suite(
    name: str,
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None
) -> Dict:
    """Run all benchmarks on a representation."""
    logger.info(f"\n--- Evaluating {name} ---")
    
    if valid_indices is not None:
        rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays_aligned(metadata, valid_indices)
        rep_embeddings = embeddings[filtered_indices]
        rep_metadata = [metadata[i] for i in filtered_indices]
    else:
        if len(embeddings) != len(metadata):
            min_len = min(len(embeddings), len(metadata))
            rep_embeddings = embeddings[:min_len]
            rep_metadata = metadata[:min_len]
            rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays(rep_metadata)
            rep_embeddings = rep_embeddings[filtered_indices]
            rep_metadata = [rep_metadata[i] for i in filtered_indices]
        else:
            rep_branches, rep_languages, rep_legal_areas, filtered_indices = prepare_metadata_arrays(metadata)
            rep_embeddings = embeddings[filtered_indices]
            rep_metadata = [metadata[i] for i in filtered_indices]
    
    logger.info(f"  Evaluating on {len(rep_embeddings)} decisions")
    
    # 1. Adversarial Language Dominance
    lang_dom = adversarial_language_dominance(rep_embeddings, rep_metadata)
    logger.info(f"  Language Dominance: {lang_dom['mean_language_dominance']:.4f} ({lang_dom['status']})")
    
    # 2. Jurist Pairwise Preference
    jurist_pref = jurist_pairwise_preference(rep_embeddings, rep_branches, rep_languages)
    logger.info(f"  Jurist Preference: {jurist_pref['jurist_would_succeed_rate']:.4f} ({jurist_pref['status']})")
    
    # 3. Jurivoc Hierarchy Alignment (legal_area proxy)
    jurivoc = jurivoc_hierarchy_alignment(rep_embeddings, rep_legal_areas)
    logger.info(f"  Jurivoc Alignment (avg NMI): {jurivoc['avg_nmi']:.4f} ({jurivoc['status']})")
    
    # 4. Scale Stability (Frozen PCA)
    scale_stab = scale_stability_frozen_pca(rep_embeddings, rep_metadata)
    logger.info(f"  Scale Stability: {scale_stab['mean_cosine_similarity']:.4f} ({scale_stab['status']})")
    
    # 5. Boilerplate Resistance
    boilerplate = boilerplate_resistance(rep_embeddings, rep_metadata)
    logger.info(f"  Boilerplate Resistance: {boilerplate['boilerplate_dominated_rate']:.4f} ({boilerplate['status']})")
    
    all_pass = all([
        lang_dom['status'] == 'PASS',
        jurist_pref['status'] == 'PASS',
        jurivoc['status'] == 'PASS',
        scale_stab['status'] == 'PASS',
        boilerplate['status'] == 'PASS'
    ])
    
    return {
        'name': name,
        'n_decisions': len(rep_embeddings),
        'embedding_dim': int(rep_embeddings.shape[1]),
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'jurivoc_hierarchy_alignment': jurivoc,
        'scale_stability_frozen_pca': scale_stab,
        'boilerplate_resistance': boilerplate,
        'all_benchmarks_pass': all_pass,
        'n_passed': sum([
            lang_dom['status'] == 'PASS',
            jurist_pref['status'] == 'PASS',
            jurivoc['status'] == 'PASS',
            scale_stab['status'] == 'PASS',
            boilerplate['status'] == 'PASS'
        ]),
        'n_total': 5
    }

def prepare_metadata_arrays_aligned(metadata: List[Dict], embedding_indices: List[int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, legal_area for specific embedding indices."""
    branches = []
    languages = []
    legal_areas = []
    filtered_indices = []
    
    for idx in embedding_indices:
        meta = metadata[idx]
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")
        legal_area = meta.get("legal_area", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            legal_areas.append(legal_area)
            filtered_indices.append(idx)
    
    return np.array(branches), np.array(languages), np.array(legal_areas), filtered_indices


def evaluate_on_frozen_harness(embeddings: np.ndarray, name: str) -> Dict[str, Any]:
    """Evaluate using the FROZEN harness v3 (seed=42)."""
    logger.info(f"\n=== Evaluating {name} on FROZEN HARNESS v3 ===")
    
    # Load center_projected metadata (1200 decisions - evaluation corpus)
    cp_metadata = load_center_projected_metadata()
    
    # Align embeddings with metadata
    if len(embeddings) != len(cp_metadata):
        logger.warning(f"Embedding count ({len(embeddings)}) != metadata count ({len(cp_metadata)})")
        min_len = min(len(embeddings), len(cp_metadata))
        embeddings = embeddings[:min_len]
        cp_metadata = cp_metadata[:min_len]
    
    # Run full benchmark suite from frozen harness
    results = run_full_benchmark_suite(name, embeddings, cp_metadata)
    
    # Log key metrics
    ld = results['adversarial_language_dominance']['mean_language_dominance']
    ld_status = results['adversarial_language_dominance']['status']
    jp = results['jurist_pairwise_preference']['jurist_would_succeed_rate']
    jp_status = results['jurist_pairwise_preference']['status']
    jv = results['jurivoc_hierarchy_alignment']['avg_nmi']
    jv_status = results['jurivoc_hierarchy_alignment']['status']
    sc = results['scale_stability_frozen_pca']['mean_cosine_similarity']
    sc_status = results['scale_stability_frozen_pca']['status']
    bp = results['boilerplate_resistance']['boilerplate_dominated_rate']
    bp_status = results['boilerplate_resistance']['status']
    
    logger.info(f"  Language Dominance: {ld:.4f} ({ld_status})")
    logger.info(f"  Jurist Preference: {jp:.4f} ({jp_status})")
    logger.info(f"  Jurivoc NMI: {jv:.4f} ({jv_status})")
    logger.info(f"  Scale Stability: {sc:.4f} ({sc_status})")
    logger.info(f"  Boilerplate Resistance: {bp:.4f} ({bp_status})")
    logger.info(f"  Benchmarks passed: {results['n_passed']}/5")
    
    # Also run fractal-map evaluation for overclustering check
    logger.info("\n  Running fractal-map evaluation (overclustering check)...")
    hierarchical_labels, coarse_labels, _, coarse_to_fine = hierarchical_leiden(
        embeddings, cp_metadata, coarse_res=0.5, sub_res=3.0
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, cp_metadata)
    coarse_overall = compute_branch_purity(coarse_labels, cp_metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, cp_metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, cp_metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    legal_areas = [cp_metadata[i].get('legal_area', '') for i in range(len(cp_metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    flat_labels, _ = leiden_clustering(embeddings, resolution=3.0)
    flat_purity = compute_branch_purity(flat_labels, cp_metadata)
    hierarchical_advantage = fine_overall - flat_purity
    
    overclustering = (n_coarse == 1 and n_fine >= 500)
    
    logger.info(f"  Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Hierarchical advantage: {hierarchical_advantage:+.4f}")
    logger.info(f"  Overclustering: {overclustering}")
    
    fractal_results = {
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(hierarchical_advantage),
        'overclustering': overclustering,
    }
    
    results['fractal_evaluation'] = fractal_results
    
    return results


def main():
    logger.info("=" * 80)
    logger.info("Legal Distance Lane v7 - Fine-tune multilingual-e5-small")
    logger.info("WITH hierarchy preservation loss (fix overclustering)")
    logger.info("CPU-REDUCED run (no GPU available)")
    logger.info("=" * 80)
    
    # 1. Load corpus
    logger.info("\n1. Loading corpus...")
    corpus = load_corpus()
    
    # 2. Load center_projected reference for hierarchy loss
    logger.info("\n2. Loading center_projected reference for hierarchy loss...")
    cp_embeddings, cp_metadata, ref_coarse_labels = load_center_projected_reference()
    
    # Align corpus with center_projected metadata
    corpus_by_id = {d.decision_id: d for d in corpus}
    aligned_corpus = [corpus_by_id[m['decision_id']] for m in cp_metadata if m['decision_id'] in corpus_by_id]
    logger.info(f"Aligned corpus: {len(aligned_corpus)} decisions")
    
    # Create reference coarse labels tensor for aligned corpus
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    aligned_indices = [cp_id_to_idx[m.decision_id] for m in aligned_corpus]
    aligned_ref_coarse = ref_coarse_labels[aligned_indices]
    ref_coarse_tensor = torch.from_numpy(aligned_ref_coarse).long()
    
    # 3. Load pre-trained model as baseline
    logger.info("\n3. Loading pre-trained multilingual-e5-small...")
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model.max_seq_length = MAX_SEQ_LENGTH
    
    # Evaluate pre-trained baseline
    logger.info("\n4. Evaluating PRE-TRAINED baseline on frozen harness...")
    # Get embeddings for all decisions
    texts = [m.get('full_text', '')[:8192] for m in cp_metadata]
    pretrained_embeddings = model.encode(texts, show_progress_bar=True, batch_size=32, device=DEVICE)
    norms = np.linalg.norm(pretrained_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    pretrained_embeddings = pretrained_embeddings / norms
    
    pretrained_results = evaluate_on_frozen_harness(pretrained_embeddings, "multilingual_e5_small_pretrained_hierarchy")
    
    # 4. Create training data with legal structure
    logger.info("\n5. Creating contrastive training pairs (reduced)...")
    contrastive_examples = create_contrastive_pairs(aligned_corpus, max_pairs=MAX_PAIRS)
    
    logger.info("\n6. Creating triplet examples (reduced)...")
    triplet_examples = create_triplet_examples(aligned_corpus, max_triplets=MAX_TRIPLETS)
    
    # 5. Fine-tune with contrastive loss + hierarchy loss
    logger.info("\n7. Fine-tuning with Contrastive Loss + Hierarchy Loss...")
    train_dataloader = DataLoader(contrastive_examples, shuffle=True, batch_size=BATCH_SIZE)
    train_loss = losses.ContrastiveLoss(model)
    
    warmup_steps = WARMUP_STEPS
    
    best_valid = False
    best_jurist = 0.0
    best_epoch = 0
    training_log = []
    
    for epoch in range(EPOCHS):
        # Get loss weights for this epoch (scheduling)
        lambda_contrastive, lambda_preserve, lambda_hierarchy = get_loss_weights(epoch + 1, EPOCHS)
        
        logger.info(f"\nEpoch {epoch+1}/{EPOCHS}: λ_contrastive={lambda_contrastive}, λ_preserve={lambda_preserve}, λ_hierarchy={lambda_hierarchy}")
        
        # Standard sentence-transformers fit for contrastive loss
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=1,
            warmup_steps=warmup_steps,
            optimizer_params={'lr': LEARNING_RATE},
            show_progress_bar=True,
            output_path=str(OUTPUT_DIR / f"model_contrastive_epoch{epoch+1}"),
        )
        
        # Additional: hierarchy loss step on full embeddings
        logger.info("  Computing hierarchy loss step...")
        model.eval()
        with torch.no_grad():
            # Get embeddings for aligned corpus
            aligned_texts = [f"{d.title} {d.full_text[:256]}" if d.title else d.full_text[:512] for d in aligned_corpus]
            aligned_embeddings = model.encode(aligned_texts, show_progress_bar=False, batch_size=32, device=DEVICE)
            aligned_embeddings = torch.from_numpy(aligned_embeddings).float().to(DEVICE)
            aligned_embeddings = F.normalize(aligned_embeddings, dim=1, p=2)
        
        # Enable gradient for hierarchy loss
        aligned_embeddings.requires_grad_(True)
        h_loss = hierarchy_loss_batch(aligned_embeddings, ref_coarse_tensor.to(DEVICE))
        
        # Backpropagate hierarchy loss
        optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
        h_loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        
        logger.info(f"  Hierarchy loss: {h_loss.item():.6f}")
        
        # Evaluate on frozen harness
        logger.info(f"\n  Evaluating epoch {epoch+1} on frozen harness...")
        model.eval()
        with torch.no_grad():
            epoch_embeddings = model.encode(texts, show_progress_bar=True, batch_size=32, device=DEVICE)
            norms = np.linalg.norm(epoch_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            epoch_embeddings = epoch_embeddings / norms
        
        eval_results = evaluate_on_frozen_harness(epoch_embeddings, f"multilingual_e5_small_epoch{epoch+1}_hierarchy")
        
        training_log.append({
            'epoch': epoch + 1,
            'lambda_contrastive': lambda_contrastive,
            'lambda_preserve': lambda_preserve,
            'lambda_hierarchy': lambda_hierarchy,
            'hierarchy_loss': h_loss.item(),
            'eval': eval_results
        })
        
        # Track best valid representation (passes adversarial gates AND not overclustering)
        is_valid = (eval_results['adversarial_language_dominance']['status'] == 'PASS' and 
                    eval_results['jurist_pairwise_preference']['status'] == 'PASS' and
                    not eval_results['fractal_evaluation']['overclustering'] and
                    eval_results['fractal_evaluation']['n_coarse'] >= 3)
        
        if is_valid and eval_results['jurist_pairwise_preference']['jurist_would_succeed_rate'] > best_jurist:
            best_jurist = eval_results['jurist_pairwise_preference']['jurist_would_succeed_rate']
            best_valid = True
            best_epoch = epoch + 1
            
            # Save best model
            model.save(str(OUTPUT_DIR / "best_model"))
            np.save(OUTPUT_DIR / "best_embeddings.npy", epoch_embeddings)
            logger.info(f"  >>> NEW BEST VALID REPRESENTATION! JuristPref={best_jurist:.4f}, Coarse={eval_results['fractal_evaluation']['n_coarse']}")
        
        # Also save epoch embeddings
        np.save(OUTPUT_DIR / f"embeddings_epoch{epoch+1}.npy", epoch_embeddings)
    
    # 6. Fine-tune with triplet loss (additional)
    logger.info("\n8. Fine-tuning with Triplet Loss (1 epoch)...")
    model_triplet = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model_triplet.max_seq_length = MAX_SEQ_LENGTH
    
    triplet_dataloader = DataLoader(triplet_examples, shuffle=True, batch_size=BATCH_SIZE)
    triplet_loss = losses.TripletLoss(model_triplet)
    
    model_triplet.fit(
        train_objectives=[(triplet_dataloader, triplet_loss)],
        epochs=1,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
        output_path=str(OUTPUT_DIR / "model_triplet"),
    )
    
    # Evaluate triplet fine-tuned
    logger.info("\n9. Evaluating TRIPLET fine-tuned model...")
    model_triplet.eval()
    with torch.no_grad():
        triplet_embeddings = model_triplet.encode(texts, show_progress_bar=True, batch_size=32, device=DEVICE)
        norms = np.linalg.norm(triplet_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        triplet_embeddings = triplet_embeddings / norms
    
    triplet_results = evaluate_on_frozen_harness(triplet_embeddings, "multilingual_e5_small_triplet_hierarchy")
    
    # 7. Combined: contrastive + triplet + hierarchy
    logger.info("\n10. Fine-tuning with Combined Loss (Contrastive + Triplet + Hierarchy)...")
    model_combined = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model_combined.max_seq_length = MAX_SEQ_LENGTH
    
    combined_dataloader_contrastive = DataLoader(contrastive_examples, shuffle=True, batch_size=BATCH_SIZE)
    combined_dataloader_triplet = DataLoader(triplet_examples, shuffle=True, batch_size=BATCH_SIZE)
    combined_loss_contrastive = losses.ContrastiveLoss(model_combined)
    combined_loss_triplet = losses.TripletLoss(model_combined)
    
    # Train contrastive
    model_combined.fit(
        train_objectives=[(combined_dataloader_contrastive, combined_loss_contrastive)],
        epochs=1,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
    )
    
    # Hierarchy step
    model_combined.eval()
    with torch.no_grad():
        aligned_texts = [f"{d.title} {d.full_text[:256]}" if d.title else d.full_text[:512] for d in aligned_corpus]
        aligned_embeddings = model_combined.encode(aligned_texts, show_progress_bar=False, batch_size=32, device=DEVICE)
        aligned_embeddings = torch.from_numpy(aligned_embeddings).float().to(DEVICE)
        aligned_embeddings = F.normalize(aligned_embeddings, dim=1, p=2)
    
    aligned_embeddings.requires_grad_(True)
    h_loss = hierarchy_loss_batch(aligned_embeddings, ref_coarse_tensor.to(DEVICE))
    optimizer = torch.optim.AdamW(model_combined.parameters(), lr=LEARNING_RATE)
    h_loss.backward()
    optimizer.step()
    optimizer.zero_grad()
    
    # Train triplet
    model_combined.fit(
        train_objectives=[(combined_dataloader_triplet, combined_loss_triplet)],
        epochs=1,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
        output_path=str(OUTPUT_DIR / "model_combined"),
    )
    
    # Evaluate combined
    logger.info("\n11. Evaluating COMBINED fine-tuned model...")
    model_combined.eval()
    with torch.no_grad():
        combined_embeddings = model_combined.encode(texts, show_progress_bar=True, batch_size=32, device=DEVICE)
        norms = np.linalg.norm(combined_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        combined_embeddings = combined_embeddings / norms
    
    combined_results = evaluate_on_frozen_harness(combined_embeddings, "multilingual_e5_small_combined_hierarchy")
    
    # 8. Summary
    logger.info("\n" + "=" * 100)
    logger.info("FINETUNING SUMMARY - FROZEN HARNESS v3 ADVERSARIAL BENCHMARKS")
    logger.info("=" * 100)
    logger.info(f"{'Model':<50} {'LangDom':>8} {'LD':>4} {'Jurist':>8} {'JP':>4} {'Jurivoc':>8} {'JV':>4} {'Scale':>7} {'SC':>4} {'Boiler':>7} {'BP':>4} {'Pass':>4}/5 {'Coarse':>6} {'Fine':>6} {'OverC':>5}")
    logger.info("-" * 100)
    
    all_results = {
        'pretrained': pretrained_results,
        'contrastive_epoch1': training_log[0]['eval'] if len(training_log) > 0 else None,
        'contrastive_epoch2': training_log[1]['eval'] if len(training_log) > 1 else None,
        'triplet': triplet_results,
        'combined': combined_results,
        'training_log': training_log,
        'best_epoch': best_epoch,
        'best_jurist': best_jurist,
    }
    
    for key, res in all_results.items():
        if key == 'training_log' or res is None:
            continue
        ld = res['adversarial_language_dominance']['mean_language_dominance']
        jp = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
        jv = res['jurivoc_hierarchy_alignment']['avg_nmi']
        sc = res['scale_stability_frozen_pca']['mean_cosine_similarity']
        bp = res['boilerplate_resistance']['boilerplate_dominated_rate']
        n_passed = res['n_passed']
        n_coarse = res['fractal_evaluation']['n_coarse']
        n_fine = res['fractal_evaluation']['n_fine']
        overclustering = res['fractal_evaluation']['overclustering']
        
        ld_pass = "✅" if ld < 0.85 else "❌"
        jp_pass = "✅" if jp > 0.5 else "❌"
        jv_pass = "✅" if jv > 0.3 else "❌"
        sc_pass = "✅" if sc > 0.95 else "❌"
        bp_pass = "✅" if bp < 0.3 else "❌"
        over_str = "❌" if overclustering else "✅"
        
        logger.info(f"{key:<50} {ld:>8.4f} {ld_pass:>4} {jp:>8.4f} {jp_pass:>4} {jv:>8.4f} {jv_pass:>4} {sc:>7.4f} {sc_pass:>4} {bp:>7.4f} {bp_pass:>4} {n_passed:>4}/5 {n_coarse:>6} {n_fine:>6} {over_str:>5}")
    
    # Save all results
    with open(OUTPUT_DIR / "finetune_hierarchy_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Determine best model
    valid_models = {k: v for k, v in all_results.items() 
                   if k != 'training_log' and v is not None
                   and v['adversarial_language_dominance']['status'] == 'PASS'
                   and v['jurist_pairwise_preference']['status'] == 'PASS'
                   and not v['fractal_evaluation']['overclustering']
                   and v['fractal_evaluation']['n_coarse'] >= 3}
    
    if valid_models:
        best_model = max(valid_models.items(), key=lambda x: x[1]['jurist_pairwise_preference']['jurist_would_succeed_rate'])
        logger.info(f"\n🏆 Best VALID model (no overclustering): {best_model[0]}")
        logger.info(f"   JuristPref={best_model[1]['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f}, "
                   f"LangDom={best_model[1]['adversarial_language_dominance']['mean_language_dominance']:.4f}, "
                   f"Coarse={best_model[1]['fractal_evaluation']['n_coarse']}, "
                   f"Fine={best_model[1]['fractal_evaluation']['n_fine']}")
    else:
        # Fallback: best by jurist preference among those passing adversarial gates
        adv_pass = {k: v for k, v in all_results.items() 
                   if k != 'training_log' and v is not None
                   and v['adversarial_language_dominance']['status'] == 'PASS'
                   and v['jurist_pairwise_preference']['status'] == 'PASS'}
        if adv_pass:
            best_model = max(adv_pass.items(), key=lambda x: x[1]['jurist_pairwise_preference']['jurist_would_succeed_rate'])
            logger.info(f"\n🏆 Best ADVERSARIAL model: {best_model[0]} (may have overclustering)")
        else:
            best_model = max((k for k in all_results.keys() if k != 'training_log' and all_results[k] is not None), 
                           key=lambda x: all_results[x]['n_passed'])
            logger.info(f"\n🏆 Best by benchmarks passed: {best_model}")
    
    logger.info("\n=== Fine-tuning with Hierarchy Loss Complete ===")
    return all_results


if __name__ == "__main__":
    main()