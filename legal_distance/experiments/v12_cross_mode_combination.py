#!/usr/bin/env python3
"""
Legal Distance Lane v12 - Cross-Mode Combination Evaluation

HYPOTHESIS: The two validated distance modes have complementary strengths:
  - Citation-based (zero-shot): good cross-lingual (LangDom~0.51), moderate JP (~0.58)
  - Metric-learning OOS: good CiteIndep (~37%), moderate JP (~0.53)
A principled combination may break the true OOS JuristPref ceiling of ~0.53.

PRODUCT DECISION: If combination improves JP on holdout > 0.535 (best current OOS),
it becomes a candidate for the production High-Advantage default. If it fails to
improve, the two-mode tradeoff is confirmed as fundamental and the product should
expose both modes separately.

FROZEN SETUP (matching v10/v11):
- Corpus: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- Split: 1000 train / 200 holdout (same as v8/v9/v10/v11)
- Harness: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- Metrics: Adversarial LangDom (gate < 0.85), JuristPref (gate > 0.5),
  CiteIndep (target > 15%)

SUCCESS RULE (frozen before inspection):
  Any combination achieves HOLDOUT JuristPref > 0.535 OR
  achieves both-pass AND CiteIndep > 37% (beats best current individual mode).

FAILURE RULE:
  If NO combination beats the individual baselines on all three metrics,
  the cross-mode tradeoff is confirmed as fundamental.
"""

import json
import numpy as np
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================
# Paths (matching v10/v11)
# ======================================================================
LEGAL_SIGNALS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")

# v10 OOS embeddings (trained on 1000 train only)
V10_LINEAR_TRAIN = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v10/out_of_sample_metric_learning/best_oos_linear_train_embeddings.npy")
V10_LINEAR_HOLDOUT = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v10/out_of_sample_metric_learning/best_oos_linear_holdout_embeddings.npy")
V10_MAHAL_TRAIN = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v10/out_of_sample_metric_learning/best_oos_mahalanobis_train_embeddings.npy")
V10_MAHAL_HOLDOUT = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v10/out_of_sample_metric_learning/best_oos_mahalanobis_holdout_embeddings.npy")

# v11 OOS hybrid_stabilized embeddings
V11_HIER_TRAIN = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/best_train_embeddings.npy")
V11_HIER_HOLDOUT = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/best_holdout_embeddings.npy")
V11_NOHIER_TRAIN = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized_nohier/best_train_embeddings.npy")
V11_NOHIER_HOLDOUT = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized_nohier/best_holdout_embeddings.npy")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v12/cross_mode_combination")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# Frozen harness config (v3)
# ======================================================================
FROZEN_CONFIG_HASH = "1674829901d55e83"
FROZEN_SEED = 42

ADVERSARIAL_CONFIG = {
    'language_dominance_k': 20,
    'language_dominance_threshold': 0.85,
    'jurist_pairwise_k': 10,
    'jurist_pairwise_threshold': 0.5,
}

SUCCESS_RULE = {
    'langdom_target': 0.6,
    'langdom_gate': 0.85,
    'jurist_pref_target': 0.7,
    'jurist_pref_gate': 0.5,
    'citation_independent_recall_target': 0.15,
}

random.seed(FROZEN_SEED)
np.random.seed(FROZEN_SEED)
torch.manual_seed(FROZEN_SEED)
DEVICE = "cpu"


# ======================================================================
# Data loading (identical to v10/v11)
# ======================================================================
def load_legal_signals():
    data = []
    with open(LEGAL_SIGNALS_PATH, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    logger.info(f"Loaded {len(data)} decisions from legal_signals_full.jsonl")
    return data


def load_evaluation_metadata():
    with open(EVAL_METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions from evaluation metadata")
    return metadata


def load_center_projected():
    embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected: {embeddings.shape}, {len(metadata)} decisions")
    return embeddings, metadata


def assign_branch_from_legal_area(legal_area):
    if not legal_area:
        return "unknown"
    la_lower = legal_area.lower()
    if any(kw in la_lower for kw in ["public", "öffentlich", "administrative", "verwaltung",
           "verfassungs", "constitution", "droit public", "droit administratif", "droit fiscal",
           "finances", "steuer", "strafprozess", "procédure pénale", "straf", "pena",
           "infractions", "straftaten", "exécution", "vollzug", "military", "militär",
           "sicherheit"]):
        return "public"
    elif any(kw in la_lower for kw in ["civil", "zivil", "vertrag", "contrat", "obligation",
             "obligationen", "schuld", "poursuite", "faillite", "execution", "famille",
             "familien", "erbrecht", "nachlass", "sachen", "biens", "personen", "personnes",
             "gesellschaft", "societ", "immobilien", "grund"]):
        return "civil"
    elif any(kw in la_lower for kw in ["criminal", "straf", "pena", "infraction", "straftat"]):
        return "criminal"
    elif any(kw in la_lower for kw in ["social", "sozial", "insurance", "versicherung", "avs",
             "ai", "iv", "invalid", "unfall", "accident", "kranken", "maladie", "ergänzungs",
             "prestations", "erwerb", "alters", "hinterlass", "survivants"]):
        return "social_insurance"
    elif any(kw in la_lower for kw in ["tax", "steuer", "fiscal", "abgab"]):
        return "tax"
    elif any(kw in la_lower for kw in ["administrative", "verwaltung", "procédure administrative",
             "verwaltungsverfahren"]):
        return "administrative"
    return "other"


def prepare_metadata(decisions):
    for d in decisions:
        if 'branch' not in d or not d.get('branch'):
            d['branch'] = assign_branch_from_legal_area(d.get('legal_area', ''))
        if 'language' not in d:
            d['language'] = 'de'
    return decisions


def split_train_holdout(decisions, eval_metadata):
    eval_ids = {m['decision_id'] for m in eval_metadata}
    train_decisions, holdout_decisions = [], []
    train_indices, holdout_indices = [], []
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


# ======================================================================
# Citation-based feature construction (TRAIN ONLY fitting)
# ======================================================================
def build_citation_tfidf_train_only(train_decisions, holdout_decisions, svd_dim=128):
    """
    Build cited_decisions TF-IDF features fit ONLY on train.
    Returns train (1000 x svd_dim) and holdout (200 x svd_dim).
    """
    train_texts = []
    train_has_content = []
    for i, d in enumerate(train_decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            train_texts.append(text)
            train_has_content.append(i)

    holdout_texts = []
    holdout_has_content = []
    for i, d in enumerate(holdout_decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            holdout_texts.append(text)
            holdout_has_content.append(i)

    if len(train_texts) < 2:
        logger.warning("Too few train decisions with citations")
        return np.zeros((len(train_decisions), svd_dim)), np.zeros((len(holdout_decisions), svd_dim))

    vectorizer = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
    train_tfidf = vectorizer.fit_transform(train_texts)
    svd = TruncatedSVD(n_components=min(svd_dim, train_tfidf.shape[1] - 1), random_state=FROZEN_SEED)
    train_reduced = svd.fit_transform(train_tfidf)

    norms = np.linalg.norm(train_reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    train_reduced = train_reduced / norms

    if len(holdout_texts) > 0:
        holdout_tfidf = vectorizer.transform(holdout_texts)
        holdout_reduced = svd.transform(holdout_tfidf)
        norms = np.linalg.norm(holdout_reduced, axis=1, keepdims=True)
        norms[norms == 0] = 1
        holdout_reduced = holdout_reduced / norms
    else:
        holdout_reduced = np.zeros((len(holdout_decisions), svd_dim))

    train_full = np.zeros((len(train_decisions), train_reduced.shape[1]))
    for idx, emb_idx in enumerate(train_has_content):
        train_full[emb_idx] = train_reduced[idx]

    holdout_full = np.zeros((len(holdout_decisions), holdout_reduced.shape[1]))
    for idx, emb_idx in enumerate(holdout_has_content):
        holdout_full[emb_idx] = holdout_reduced[idx]

    logger.info(f"Citation TF-IDF: train={train_full.shape}, holdout={holdout_full.shape}")
    return train_full, holdout_full


def build_outcome_tfidf_train_only(train_decisions, holdout_decisions, svd_dim=2):
    """Build outcome TF-IDF features fit ONLY on train."""
    train_texts = []
    train_has_content = []
    for i, d in enumerate(train_decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            train_texts.append(str(outcome))
            train_has_content.append(i)

    holdout_texts = []
    holdout_has_content = []
    for i, d in enumerate(holdout_decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            holdout_texts.append(str(outcome))
            holdout_has_content.append(i)

    if len(train_texts) < 2:
        return np.zeros((len(train_decisions), svd_dim)), np.zeros((len(holdout_decisions), svd_dim))

    vectorizer = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
    train_tfidf = vectorizer.fit_transform(train_texts)
    svd = TruncatedSVD(n_components=min(svd_dim, train_tfidf.shape[1] - 1), random_state=FROZEN_SEED)
    train_reduced = svd.fit_transform(train_tfidf)

    norms = np.linalg.norm(train_reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    train_reduced = train_reduced / norms

    if len(holdout_texts) > 0:
        holdout_tfidf = vectorizer.transform(holdout_texts)
        holdout_reduced = svd.transform(holdout_tfidf)
        norms = np.linalg.norm(holdout_reduced, axis=1, keepdims=True)
        norms[norms == 0] = 1
        holdout_reduced = holdout_reduced / norms
    else:
        holdout_reduced = np.zeros((len(holdout_decisions), svd_dim))

    train_full = np.zeros((len(train_decisions), train_reduced.shape[1]))
    for idx, emb_idx in enumerate(train_has_content):
        train_full[emb_idx] = train_reduced[idx]

    holdout_full = np.zeros((len(holdout_decisions), holdout_reduced.shape[1]))
    for idx, emb_idx in enumerate(holdout_has_content):
        holdout_full[emb_idx] = holdout_reduced[idx]

    return train_full, holdout_full


def build_cited_outcome_hybrid(train_cites, holdout_cites, train_outcome, holdout_outcome, alpha=0.5):
    """Build cited_outcome_hybrid: alpha*cites + (1-alpha)*outcome, normalized concatenation."""
    def norm_emb(emb):
        n = np.linalg.norm(emb, axis=1, keepdims=True)
        n[n == 0] = 1
        return emb / n

    train_hybrid = np.concatenate([norm_emb(train_cites) * alpha, norm_emb(train_outcome) * (1 - alpha)], axis=1)
    holdout_hybrid = np.concatenate([norm_emb(holdout_cites) * alpha, norm_emb(holdout_outcome) * (1 - alpha)], axis=1)

    norms = np.linalg.norm(train_hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    train_hybrid = train_hybrid / norms

    norms = np.linalg.norm(holdout_hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    holdout_hybrid = holdout_hybrid / norms

    return train_hybrid, holdout_hybrid


# ======================================================================
# Adversarial benchmarks (frozen v3 harness)
# ======================================================================
def adversarial_language_dominance(embeddings, metadata, k=20):
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
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
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
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
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round((language_artifact_count + both_count) / total, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(language_artifact_count / total, 4),
    }


def run_adversarial_benchmarks(embeddings, metadata):
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


def citation_independent_retrieval(holdout_embeddings, holdout_metadata, train_embeddings, train_metadata, k=10):
    nn = NearestNeighbors(n_neighbors=min(k, len(train_embeddings)), metric='cosine')
    nn.fit(train_embeddings)
    _, indices = nn.kneighbors(holdout_embeddings)
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
            legally_related = (train_branch == holdout_branch and holdout_branch != 'unknown') or \
                             (train_legal_area == holdout_legal_area and holdout_legal_area != 'unknown')
            if legally_related:
                legal_retrieved += 1
                if len(holdout_citations & train_cites) == 0:
                    citation_independent_retrieved += 1
    max_possible = total_queries * k
    legal_rate = legal_retrieved / max_possible if max_possible > 0 else 0
    citation_independent_rate = citation_independent_retrieved / max_possible if max_possible > 0 else 0
    return {
        'total_queries': total_queries,
        'k': k,
        'legal_retrieval_rate': round(legal_rate, 4),
        'citation_independent_retrieval_rate': round(citation_independent_rate, 4),
        'status': 'PASS' if citation_independent_rate >= SUCCESS_RULE['citation_independent_recall_target'] else 'FAIL',
    }


def evaluate_representation(name, train_embeddings, holdout_embeddings, train_metadata, holdout_metadata):
    logger.info(f"\n=== Evaluating {name} ===")
    tn = np.linalg.norm(train_embeddings, axis=1, keepdims=True)
    tn[tn == 0] = 1
    train_norm = train_embeddings / tn
    hn = np.linalg.norm(holdout_embeddings, axis=1, keepdims=True)
    hn[hn == 0] = 1
    holdout_norm = holdout_embeddings / hn

    train_adv = run_adversarial_benchmarks(train_norm, train_metadata)
    holdout_adv = run_adversarial_benchmarks(holdout_norm, holdout_metadata)
    cite_indep = citation_independent_retrieval(holdout_norm, holdout_metadata, train_norm, train_metadata)

    logger.info(f"  Train: LangDom={train_adv['language_dominance_score']:.4f}, "
                f"JuristPref={train_adv['jurist_preference_rate']:.4f} ({train_adv['both_pass']})")
    logger.info(f"  Holdout: LangDom={holdout_adv['language_dominance_score']:.4f}, "
                f"JuristPref={holdout_adv['jurist_preference_rate']:.4f} ({holdout_adv['both_pass']})")
    logger.info(f"  Cite-indep: {cite_indep['citation_independent_retrieval_rate']:.4f} ({cite_indep['status']})")
    return {
        'name': name,
        'n_train': train_embeddings.shape[0],
        'n_holdout': holdout_embeddings.shape[0],
        'embedding_dim': train_embeddings.shape[1],
        'train_adversarial': train_adv,
        'holdout_adversarial': holdout_adv,
        'citation_independent_retrieval': cite_indep,
    }


# ======================================================================
# Combination strategies
# ======================================================================
def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n


def combination_concat_l2norm(emb_ml, emb_cite):
    """Simple concatenation with L2 normalization."""
    ml_norm = normalize_emb(emb_ml)
    cite_norm = normalize_emb(emb_cite)
    combined = np.concatenate([ml_norm, cite_norm], axis=1)
    return normalize_emb(combined)


def combination_weighted_concat(emb_ml, emb_cite, w_ml, w_cite):
    """Weighted concatenation then L2 normalize."""
    ml_norm = normalize_emb(emb_ml) * w_ml
    cite_norm = normalize_emb(emb_cite) * w_cite
    combined = np.concatenate([ml_norm, cite_norm], axis=1)
    return normalize_emb(combined)


def combination_pca_reduction(emb_ml, emb_cite, n_components=128):
    """Concatenate then PCA reduce to target dim."""
    from sklearn.decomposition import PCA
    ml_norm = normalize_emb(emb_ml)
    cite_norm = normalize_emb(emb_cite)
    combined = np.concatenate([ml_norm, cite_norm], axis=1)
    pca = PCA(n_components=min(n_components, combined.shape[1]), random_state=FROZEN_SEED)
    reduced = pca.fit_transform(combined)
    return normalize_emb(reduced), pca


def combination_ridge_regression(train_ml, train_cite, train_labels, holdout_ml, holdout_cite):
    """Learn a ridge regression to predict a pseudo-label (branch) from concatenated features, use embeddings as features."""
    ml_train = normalize_emb(train_ml)
    cite_train = normalize_emb(train_cite)
    ml_holdout = normalize_emb(holdout_ml)
    cite_holdout = normalize_emb(holdout_cite)

    X_train = np.concatenate([ml_train, cite_train], axis=1)
    X_holdout = np.concatenate([ml_holdout, cite_holdout], axis=1)

    # Standardize
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_holdout_s = scaler.transform(X_holdout)

    # Ridge regression to predict branch
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_s, train_labels)

    # Use the coefficients as a linear combination weight
    # The ridge coefficients give a meaningful direction in the combined space
    # We use them as a weighted projection
    train_proj = X_train_s @ ridge.coef_
    holdout_proj = X_holdout_s @ ridge.coef_

    # Stack as 1D feature alongside original
    train_ridge = np.column_stack([ml_train, cite_train, train_proj.reshape(-1, 1)])
    holdout_ridge = np.column_stack([ml_holdout, cite_holdout, holdout_proj.reshape(-1, 1)])

    return normalize_emb(train_ridge), normalize_emb(holdout_ridge), ridge


# ======================================================================
# Small MLP for learned combination (trained on train only)
# ======================================================================
class CombinationMLP(nn.Module):
    """Small MLP to learn optimal combination of ML + citation features."""
    def __init__(self, ml_dim, cite_dim, hidden_dim=64, output_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(ml_dim + cite_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim),
        )
        self.output_dim = output_dim

    def forward(self, x):
        return F.normalize(self.net(x), dim=1, p=2)


def train_combination_mlp(train_ml, train_cite, train_metadata, holdout_ml, holdout_cite,
                          ml_dim, cite_dim, epochs=30, batch_size=128):
    """Train small MLP on train only, evaluate on holdout."""
    train_ml_n = normalize_emb(train_ml)
    train_cite_n = normalize_emb(train_cite)
    holdout_ml_n = normalize_emb(holdout_ml)
    holdout_cite_n = normalize_emb(holdout_cite)

    X_train = torch.from_numpy(np.concatenate([train_ml_n, train_cite_n], axis=1)).float()
    X_holdout = torch.from_numpy(np.concatenate([holdout_ml_n, holdout_cite_n], axis=1)).float()

    # Create contrastive pairs from train metadata
    branches = [m.get('branch', 'unknown') for m in train_metadata]
    languages = [m.get('language', 'unknown') for m in train_metadata]

    by_branch_lang = defaultdict(lambda: defaultdict(list))
    by_language = defaultdict(list)
    for i, (b, l) in enumerate(zip(branches, languages)):
        by_branch_lang[b][l].append(i)
        by_language[l].append(i)

    positive_pairs = []
    for branch, lang_dict in by_branch_lang.items():
        langs = list(lang_dict.keys())
        if len(langs) < 2:
            continue
        for li in range(len(langs)):
            for lj in range(li+1, len(langs)):
                for a in by_branch_lang[branch][langs[li]]:
                    for b in by_branch_lang[branch][langs[lj]]:
                        positive_pairs.append((a, b))

    negative_pairs = []
    for lang, indices in by_language.items():
        branch_indices = defaultdict(list)
        for idx in indices:
            branch_indices[branches[idx]].append(idx)
        b_list = list(branch_indices.keys())
        for bi in range(len(b_list)):
            for bj in range(bi+1, len(b_list)):
                for a in branch_indices[b_list[bi]]:
                    for b in branch_indices[b_list[bj]]:
                        negative_pairs.append((a, b))

    # Cap
    max_pairs = 50000
    random.shuffle(positive_pairs)
    random.shuffle(negative_pairs)
    positive_pairs = positive_pairs[:max_pairs//2]
    negative_pairs = negative_pairs[:max_pairs//2]

    # Dataset
    pair_indices = []
    pair_labels = []
    for i, j in positive_pairs:
        pair_indices.append((i, j))
        pair_labels.append(1.0)
    for i, j in negative_pairs:
        pair_indices.append((i, j))
        pair_labels.append(0.0)

    model = CombinationMLP(ml_dim, cite_dim, hidden_dim=64, output_dim=128).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    best_jp = 0.0
    best_state = None
    best_epoch = 0
    patience = 5
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        # Shuffle pairs
        perm = list(range(len(pair_indices)))
        random.shuffle(perm)
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, len(perm), batch_size):
            batch_idx = perm[start:start+batch_size]
            batch_pairs = [pair_indices[i] for i in batch_idx]
            batch_labels = [pair_labels[i] for i in batch_idx]

            idx_i = [p[0] for p in batch_pairs]
            idx_j = [p[1] for p in batch_pairs]

            z_i = model(X_train[idx_i])
            z_j = model(X_train[idx_j])
            labels = torch.tensor(batch_labels, dtype=torch.float, device=DEVICE)

            sim = F.cosine_similarity(z_i, z_j, dim=1)
            pos_mask = labels == 1.0
            neg_mask = labels == 0.0
            loss = torch.tensor(0.0, device=DEVICE)
            if pos_mask.any():
                loss = loss - F.logsigmoid(sim[pos_mask] / 0.07).mean()
            if neg_mask.any():
                loss = loss - F.logsigmoid(-sim[neg_mask] / 0.07).mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        # Evaluate every 5 epochs on train
        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                train_proj = model(X_train).cpu().numpy()
            adv = run_adversarial_benchmarks(normalize_emb(train_proj), train_metadata)
            jp = adv['jurist_preference_rate']
            ld = adv['language_dominance_score']

            if adv['both_pass'] and jp > best_jp:
                best_jp = jp
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                best_epoch = epoch + 1
                no_improve = 0
            else:
                no_improve += 1

            logger.info(f"  Epoch {epoch+1}: loss={epoch_loss/n_batches:.4f} train_JP={jp:.4f} LD={ld:.4f}")

            if epoch >= 10 and no_improve >= patience:
                logger.info(f"  Early stopping at epoch {epoch+1}")
                break

    if best_state:
        model.load_state_dict(best_state)
        logger.info(f"  Best model from epoch {best_epoch} (train JP={best_jp:.4f})")

    model.eval()
    with torch.no_grad():
        train_final = model(X_train).cpu().numpy()
        holdout_final = model(X_holdout).cpu().numpy()

    return normalize_emb(train_final), normalize_emb(holdout_final), best_epoch, best_jp


# ======================================================================
# Main
# ======================================================================
def main():
    logger.info("=" * 90)
    logger.info("LEGAL DISTANCE v12 - CROSS-MODE COMBINATION EVALUATION")
    logger.info("=" * 90)
    logger.info(f"Frozen Harness: v3 (seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH})")
    logger.info("Hypothesis: Combining citation-based + metric-learning OOS may break JP ceiling ~0.53")

    # 1. Load data
    logger.info("\n1. Loading data...")
    decisions = load_legal_signals()
    decisions = prepare_metadata(decisions)
    eval_metadata = load_evaluation_metadata()
    train_decisions, holdout_decisions, train_indices, holdout_indices = split_train_holdout(decisions, eval_metadata)
    cp_embeddings, cp_metadata = load_center_projected()

    # Build metadata aligned to train/holdout
    train_meta = []
    for i in train_indices:
        m = dict(cp_metadata[i]) if i < len(cp_metadata) else {}
        m['branch'] = decisions[i].get('branch', 'unknown')
        m['language'] = decisions[i].get('language', 'de')
        m['legal_area'] = decisions[i].get('legal_area', '')
        m['cited_decisions'] = decisions[i].get('cited_decisions', [])
        train_meta.append(m)

    holdout_meta = []
    for i in holdout_indices:
        m = dict(cp_metadata[i]) if i < len(cp_metadata) else {}
        m['branch'] = decisions[i].get('branch', 'unknown')
        m['language'] = decisions[i].get('language', 'de')
        m['legal_area'] = decisions[i].get('legal_area', '')
        m['cited_decisions'] = decisions[i].get('cited_decisions', [])
        holdout_meta.append(m)

    # 2. Build citation-based features (TRAIN ONLY fitting)
    logger.info("\n2. Building citation-based features (train-only fitting)...")
    cite_train, cite_holdout = build_citation_tfidf_train_only(train_decisions, holdout_decisions, svd_dim=128)
    outcome_train, outcome_holdout = build_outcome_tfidf_train_only(train_decisions, holdout_decisions, svd_dim=2)

    # Also build the best zero-shot hybrid: cited_outcome_hybrid_0.5
    hybrid05_train, hybrid05_holdout = build_cited_outcome_hybrid(
        cite_train, cite_holdout, outcome_train, outcome_holdout, alpha=0.5)
    hybrid07_train, hybrid07_holdout = build_cited_outcome_hybrid(
        cite_train, cite_holdout, outcome_train, outcome_holdout, alpha=0.3)

    # 3. Load existing OOS metric learning embeddings
    logger.info("\n3. Loading existing OOS metric learning embeddings...")
    ml_linear_train = np.load(V10_LINEAR_TRAIN)
    ml_linear_holdout = np.load(V10_LINEAR_HOLDOUT)
    ml_mahal_train = np.load(V10_MAHAL_TRAIN)
    ml_mahal_holdout = np.load(V10_MAHAL_HOLDOUT)
    ml_hier_train = np.load(V11_HIER_TRAIN)
    ml_hier_holdout = np.load(V11_HIER_HOLDOUT)
    ml_nohier_train = np.load(V11_NOHIER_TRAIN)
    ml_nohier_holdout = np.load(V11_NOHIER_HOLDOUT)

    logger.info(f"  Linear: train={ml_linear_train.shape}, holdout={ml_linear_holdout.shape}")
    logger.info(f"  Mahalanobis: train={ml_mahal_train.shape}, holdout={ml_mahal_holdout.shape}")
    logger.info(f"  Hybrid (hier): train={ml_hier_train.shape}, holdout={ml_hier_holdout.shape}")
    logger.info(f"  Hybrid (no hier): train={ml_nohier_train.shape}, holdout={ml_nohier_holdout.shape}")

    all_results = {}

    # ======================================================================
    # 4. INDIVIDUAL BASELINES (re-evaluate for apples-to-apples)
    # ======================================================================
    logger.info("\n" + "=" * 80)
    logger.info("4. INDIVIDUAL BASELINES (apples-to-apples)")
    logger.info("=" * 80)

    all_results['baseline_linear_oos'] = evaluate_representation(
        'baseline_linear_oos', ml_linear_train, ml_linear_holdout, train_meta, holdout_meta)
    all_results['baseline_mahal_oos'] = evaluate_representation(
        'baseline_mahal_oos', ml_mahal_train, ml_mahal_holdout, train_meta, holdout_meta)
    all_results['baseline_hier_oos'] = evaluate_representation(
        'baseline_hier_oos', ml_hier_train, ml_hier_holdout, train_meta, holdout_meta)
    all_results['baseline_nohier_oos'] = evaluate_representation(
        'baseline_nohier_oos', ml_nohier_train, ml_nohier_holdout, train_meta, holdout_meta)
    all_results['baseline_citation_tfidf'] = evaluate_representation(
        'baseline_citation_tfidf', cite_train, cite_holdout, train_meta, holdout_meta)
    all_results['baseline_hybrid05'] = evaluate_representation(
        'baseline_hybrid05', hybrid05_train, hybrid05_holdout, train_meta, holdout_meta)
    all_results['baseline_hybrid07'] = evaluate_representation(
        'baseline_hybrid07', hybrid07_train, hybrid07_holdout, train_meta, holdout_meta)

    # ======================================================================
    # 5. COMBINATION STRATEGIES
    # ======================================================================
    logger.info("\n" + "=" * 80)
    logger.info("5. CROSS-MODE COMBINATIONS")
    logger.info("=" * 80)

    # 5a. Linear + citation: simple concatenation L2-norm
    logger.info("\n--- 5a: linear + citation_concat_l2norm ---")
    train_5a, holdout_5a = combination_concat_l2norm(ml_linear_train, cite_train), \
                           combination_concat_l2norm(ml_linear_holdout, cite_holdout)
    # Fix: need to compute properly
    train_5a = combination_concat_l2norm(ml_linear_train, cite_train)
    holdout_5a = combination_concat_l2norm(ml_linear_holdout, cite_holdout)
    all_results['linear_citation_concat'] = evaluate_representation(
        'linear_citation_concat', train_5a, holdout_5a, train_meta, holdout_meta)

    # 5b. Linear + cited_outcome_hybrid_0.5: concatenation
    logger.info("\n--- 5b: linear + hybrid05_concat ---")
    train_5b = combination_concat_l2norm(ml_linear_train, hybrid05_train)
    holdout_5b = combination_concat_l2norm(ml_linear_holdout, hybrid05_holdout)
    all_results['linear_hybrid05_concat'] = evaluate_representation(
        'linear_hybrid05_concat', train_5b, holdout_5b, train_meta, holdout_meta)

    # 5c. Mahalanobis + citation: concatenation
    logger.info("\n--- 5c: mahal + citation_concat ---")
    train_5c = combination_concat_l2norm(ml_mahal_train, cite_train)
    holdout_5c = combination_concat_l2norm(ml_mahal_holdout, cite_holdout)
    all_results['mahal_citation_concat'] = evaluate_representation(
        'mahal_citation_concat', train_5c, holdout_5c, train_meta, holdout_meta)

    # 5d. Mahalanobis + hybrid05: concatenation
    logger.info("\n--- 5d: mahal + hybrid05_concat ---")
    train_5d = combination_concat_l2norm(ml_mahal_train, hybrid05_train)
    holdout_5d = combination_concat_l2norm(ml_mahal_holdout, hybrid05_holdout)
    all_results['mahal_hybrid05_concat'] = evaluate_representation(
        'mahal_hybrid05_concat', train_5d, holdout_5d, train_meta, holdout_meta)

    # 5e. Hier + citation: concatenation
    logger.info("\n--- 5e: hier + citation_concat ---")
    train_5e = combination_concat_l2norm(ml_hier_train, cite_train)
    holdout_5e = combination_concat_l2norm(ml_hier_holdout, cite_holdout)
    all_results['hier_citation_concat'] = evaluate_representation(
        'hier_citation_concat', train_5e, holdout_5e, train_meta, holdout_meta)

    # 5f. Hier + hybrid05: concatenation
    logger.info("\n--- 5f: hier + hybrid05_concat ---")
    train_5f = combination_concat_l2norm(ml_hier_train, hybrid05_train)
    holdout_5f = combination_concat_l2norm(ml_hier_holdout, hybrid05_holdout)
    all_results['hier_hybrid05_concat'] = evaluate_representation(
        'hier_hybrid05_concat', train_5f, holdout_5f, train_meta, holdout_meta)

    # 5g. Weighted combinations: linear + citation at various weights
    for w_ml, w_cite in [(0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]:
        name = f'linear_citation_w{int(w_ml*100)}{int(w_cite*100)}'
        logger.info(f"\n--- {name} ---")
        train_g = combination_weighted_concat(ml_linear_train, cite_train, w_ml, w_cite)
        holdout_g = combination_weighted_concat(ml_linear_holdout, cite_holdout, w_ml, w_cite)
        all_results[name] = evaluate_representation(name, train_g, holdout_g, train_meta, holdout_meta)

    # 5h. Weighted: linear + hybrid05
    for w_ml, w_cite in [(0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]:
        name = f'linear_hybrid05_w{int(w_ml*100)}{int(w_cite*100)}'
        logger.info(f"\n--- {name} ---")
        train_h = combination_weighted_concat(ml_linear_train, hybrid05_train, w_ml, w_cite)
        holdout_h = combination_weighted_concat(ml_linear_holdout, hybrid05_holdout, w_ml, w_cite)
        all_results[name] = evaluate_representation(name, train_h, holdout_h, train_meta, holdout_meta)

    # 5i. PCA reduction: concat ML + citation, PCA to 128d
    logger.info("\n--- 5i: linear + citation PCA128 ---")
    train_5i, pca_model = combination_pca_reduction(ml_linear_train, cite_train, n_components=128)
    # Apply same PCA to holdout
    ml_holdout_n = normalize_emb(ml_linear_holdout)
    cite_holdout_n = normalize_emb(cite_holdout)
    holdout_combined = np.concatenate([ml_holdout_n, cite_holdout_n], axis=1)
    holdout_5i = normalize_emb(pca_model.transform(holdout_combined))
    all_results['linear_citation_pca128'] = evaluate_representation(
        'linear_citation_pca128', train_5i, holdout_5i, train_meta, holdout_meta)

    # 5j. PCA: mahal + citation
    logger.info("\n--- 5j: mahal + citation PCA128 ---")
    train_5j, pca_5j = combination_pca_reduction(ml_mahal_train, cite_train, n_components=128)
    holdout_5j = normalize_emb(pca_5j.transform(np.concatenate([normalize_emb(ml_mahal_holdout), normalize_emb(cite_holdout)], axis=1)))
    all_results['mahal_citation_pca128'] = evaluate_representation(
        'mahal_citation_pca128', train_5j, holdout_5j, train_meta, holdout_meta)

    # 5k. Ridge regression combination
    logger.info("\n--- 5k: linear + citation ridge ---")
    branch_labels = np.array([m.get('branch', 'unknown') for m in train_meta])
    # Encode branches as integers
    unique_branches = sorted(set(branch_labels))
    branch_to_int = {b: i for i, b in enumerate(unique_branches)}
    branch_ints = np.array([branch_to_int[b] for b in branch_labels])

    train_5k, holdout_5k, ridge_model = combination_ridge_regression(
        ml_linear_train, cite_train, branch_ints, ml_linear_holdout, cite_holdout)
    all_results['linear_citation_ridge'] = evaluate_representation(
        'linear_citation_ridge', train_5k, holdout_5k, train_meta, holdout_meta)

    # 5l. Learned MLP combination
    logger.info("\n--- 5l: linear + citation MLP ---")
    train_5l, holdout_5l, best_epoch_5l, best_jp_5l = train_combination_mlp(
        ml_linear_train, cite_train, train_meta, ml_linear_holdout, cite_holdout,
        ml_dim=ml_linear_train.shape[1], cite_dim=cite_train.shape[1], epochs=30, batch_size=128)
    all_results['linear_citation_mlp'] = evaluate_representation(
        'linear_citation_mlp', train_5l, holdout_5l, train_meta, holdout_meta)

    # 5m. Learned MLP: mahal + citation
    logger.info("\n--- 5m: mahal + citation MLP ---")
    train_5m, holdout_5m, best_epoch_5m, best_jp_5m = train_combination_mlp(
        ml_mahal_train, cite_train, train_meta, ml_mahal_holdout, cite_holdout,
        ml_dim=ml_mahal_train.shape[1], cite_dim=cite_train.shape[1], epochs=30, batch_size=128)
    all_results['mahal_citation_mlp'] = evaluate_representation(
        'mahal_citation_mlp', train_5m, holdout_5m, train_meta, holdout_meta)

    # 5n. Learned MLP: hier + citation
    logger.info("\n--- 5n: hier + citation MLP ---")
    train_5n, holdout_5n, best_epoch_5n, best_jp_5n = train_combination_mlp(
        ml_hier_train, cite_train, train_meta, ml_hier_holdout, cite_holdout,
        ml_dim=ml_hier_train.shape[1], cite_dim=cite_train.shape[1], epochs=30, batch_size=128)
    all_results['hier_citation_mlp'] = evaluate_representation(
        'hier_citation_mlp', train_5n, holdout_5n, train_meta, holdout_meta)

    # 5o. Learned MLP: linear + hybrid05
    logger.info("\n--- 5o: linear + hybrid05 MLP ---")
    train_5o, holdout_5o, best_epoch_5o, best_jp_5o = train_combination_mlp(
        ml_linear_train, hybrid05_train, train_meta, ml_linear_holdout, hybrid05_holdout,
        ml_dim=ml_linear_train.shape[1], cite_dim=hybrid05_train.shape[1], epochs=30, batch_size=128)
    all_results['linear_hybrid05_mlp'] = evaluate_representation(
        'linear_hybrid05_mlp', train_5o, holdout_5o, train_meta, holdout_meta)

    # ======================================================================
    # 6. SUMMARY
    # ======================================================================
    logger.info("\n" + "=" * 120)
    logger.info("CROSS-MODE COMBINATION SUMMARY")
    logger.info("=" * 120)

    logger.info(f"\n{'Representation':<40} {'TrLD':>6} {'TrJP':>6} {'HoLD':>6} {'HoJP':>6} {'CiteInd':>9} {'AdvPass':>7} {'CitePass':>8}")
    logger.info("-" * 120)

    for name, res in all_results.items():
        tr_ld = res['train_adversarial']['language_dominance_score']
        tr_jp = res['train_adversarial']['jurist_preference_rate']
        ho_ld = res['holdout_adversarial']['language_dominance_score']
        ho_jp = res['holdout_adversarial']['jurist_preference_rate']
        ci = res['citation_independent_retrieval']['citation_independent_retrieval_rate']
        adv = "YES" if res['holdout_adversarial']['both_pass'] else "no"
        cite = "PASS" if res['citation_independent_retrieval']['status'] == 'PASS' else 'FAIL'
        logger.info(f"{name:<40} {tr_ld:>6.3f} {tr_jp:>6.3f} {ho_ld:>6.3f} {ho_jp:>6.3f} {ci:>9.4f} {adv:>7} {cite:>8}")

    # 7. Best results analysis
    logger.info("\n" + "=" * 80)
    logger.info("BEST HOLDOUT RESULTS (sorted by JuristPref)")
    logger.info("=" * 80)

    sorted_results = sorted(all_results.items(), key=lambda x: x[1]['holdout_adversarial']['jurist_preference_rate'], reverse=True)
    for rank, (name, res) in enumerate(sorted_results[:10]):
        ho_jp = res['holdout_adversarial']['jurist_preference_rate']
        ho_ld = res['holdout_adversarial']['language_dominance_score']
        ci = res['citation_independent_retrieval']['citation_independent_retrieval_rate']
        adv_pass = res['holdout_adversarial']['both_pass']
        logger.info(f"  #{rank+1} {name}: JP={ho_jp:.4f}, LD={ho_ld:.4f}, CiteIndep={ci:.4f}, both_pass={adv_pass}")

    # 8. Tradeoff analysis
    logger.info("\n" + "=" * 80)
    logger.info("TRADEOFF ANALYSIS: Does combination break the two-mode tradeoff?")
    logger.info("=" * 80)

    best_baseline_jp = max(r['holdout_adversarial']['jurist_preference_rate'] for name, r in all_results.items() if name.startswith('baseline'))
    best_combination_jp = max(r['holdout_adversarial']['jurist_preference_rate'] for name, r in all_results.items() if not name.startswith('baseline'))
    best_baseline_ld = min(r['holdout_adversarial']['language_dominance_score'] for name, r in all_results.items() if name.startswith('baseline') and r['holdout_adversarial']['both_pass'])
    best_combination_ld = min(r['holdout_adversarial']['language_dominance_score'] for name, r in all_results.items() if not name.startswith('baseline') and r['holdout_adversarial']['both_pass'])
    best_baseline_ci = max(r['citation_independent_retrieval']['citation_independent_retrieval_rate'] for name, r in all_results.items() if name.startswith('baseline'))
    best_combination_ci = max(r['citation_independent_retrieval']['citation_independent_retrieval_rate'] for name, r in all_results.items() if not name.startswith('baseline'))

    logger.info(f"  Best baseline JP:     {best_baseline_jp:.4f}")
    logger.info(f"  Best combination JP:  {best_combination_jp:.4f}")
    logger.info(f"  ΔJP:                  {best_combination_jp - best_baseline_jp:+.4f}")
    logger.info(f"  Best baseline LD:     {best_baseline_ld:.4f}")
    logger.info(f"  Best combination LD:  {best_combination_ld:.4f}")
    logger.info(f"  Best baseline CiteIndep: {best_baseline_ci:.4f}")
    logger.info(f"  Best combination CiteIndep: {best_combination_ci:.4f}")

    if best_combination_jp > best_baseline_jp:
        logger.info(f"\n  >>> COMBINATION IMPROVES JP by {best_combination_jp - best_baseline_jp:+.4f} <<<")
    else:
        logger.info(f"\n  >>> COMBINATION DOES NOT IMPROVE JP (best is still individual baseline) <<<")

    # 9. Persist
    output = {
        'run_id': 'v12_cross_mode_combination_20260830',
        'direction_version': 10,
        'hypothesis': 'Combining citation-based + metric-learning OOS embeddings may break the JP ceiling of ~0.53',
        'corpus': '1200 BGer decisions, 1000 train / 200 holdout',
        'frozen_harness': {'config_hash': FROZEN_CONFIG_HASH, 'seed': FROZEN_SEED},
        'success_rule': SUCCESS_RULE,
        'results': all_results,
        'summary': {
            'best_baseline_jp': best_baseline_jp,
            'best_combination_jp': best_combination_jp,
            'delta_jp': best_combination_jp - best_baseline_jp,
            'best_baseline_ld': best_baseline_ld,
            'best_combination_ld': best_combination_ld,
            'best_baseline_cite_indep': best_baseline_ci,
            'best_combination_cite_indep': best_combination_ci,
            'tradeoff_broken': best_combination_jp > best_baseline_jp,
        },
    }

    with open(OUTPUT_DIR / "cross_mode_combination_validation.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"\nResults saved to: {OUTPUT_DIR / 'cross_mode_combination_validation.json'}")


if __name__ == "__main__":
    main()
