#!/usr/bin/env python3
"""
Legal Distance Lane v13 - Cross-Mode Combination 5-Fold Cross-Validation

HYPOTHESIS: The v12 cross-mode combination improvements (JP +0.035 over best
individual baseline) are stable across different data partitions, not noise.

PRODUCT DECISION: If 5-fold CV shows stable improvement (mean JP delta > 0.02
with std < 0.03), the cross-mode combination is validated for ACCEPTED tier.
If unstable (high variance or mean delta ≤ 0), the two-mode tradeoff is
confirmed as fundamental.

FROZEN SETUP:
- Corpus: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- 5-fold CV: each fold ~960 train / ~240 holdout
- Harness: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- Metrics: Adversarial LangDom (gate < 0.85), JuristPref (gate > 0.5),
  CiteIndep (target > 15%)

TOP 3 COMBINATIONS VALIDATED (from v12):
  1. linear_citation_mlp (JP=0.620 on single split)
  2. linear_hybrid05_mlp (JP=0.610)
  3. hier_citation_mlp (JP=0.605)

SUCCESS RULE (frozen before inspection):
  Any combination achieves mean CV JP delta > 0.02 AND std(JP delta) < 0.03
  across all 5 folds.

FAILURE RULE:
  If NO combination achieves stable improvement, the tradeoff is fundamental.
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
from sklearn.model_selection import KFold
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import torch.nn.functional as F

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================
# Paths (matching v10/v11/v12)
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

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v13/cross_mode_kfold")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# Frozen harness config (v3)
# ======================================================================
FROZEN_CONFIG_HASH = "1674829901d55e83"
FROZEN_SEED = 42
N_FOLDS = 5

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
    'min_mean_jp_delta': 0.02,
    'max_jp_delta_std': 0.03,
}

random.seed(FROZEN_SEED)
np.random.seed(FROZEN_SEED)
torch.manual_seed(FROZEN_SEED)
DEVICE = "cpu"


# ======================================================================
# Data loading (identical to v12)
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


# ======================================================================
# Citation-based feature construction (TRAIN ONLY fitting per fold)
# ======================================================================
def build_citation_tfidf_train_only(train_decisions, holdout_decisions, svd_dim=128):
    """Build cited_decisions TF-IDF features fit ONLY on train."""
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
def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n


def adversarial_language_dominance(embeddings, metadata, k=20):
    nn_model = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
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
        'k': k,
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
    n = len(branches)
    nn_model = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
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
    nn_model = NearestNeighbors(n_neighbors=min(k, len(train_embeddings)), metric='cosine')
    nn_model.fit(train_embeddings)
    _, indices = nn_model.kneighbors(holdout_embeddings)
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
    citation_independent_rate = citation_independent_retrieved / max_possible if max_possible > 0 else 0
    return {
        'total_queries': total_queries,
        'k': k,
        'citation_independent_retrieval_rate': round(citation_independent_rate, 4),
        'status': 'PASS' if citation_independent_rate >= SUCCESS_RULE['citation_independent_recall_target'] else 'FAIL',
    }


def evaluate_representation(name, train_embeddings, holdout_embeddings, train_metadata, holdout_metadata):
    train_norm = normalize_emb(train_embeddings)
    holdout_norm = normalize_emb(holdout_embeddings)

    train_adv = run_adversarial_benchmarks(train_norm, train_metadata)
    holdout_adv = run_adversarial_benchmarks(holdout_norm, holdout_metadata)
    cite_indep = citation_independent_retrieval(holdout_norm, holdout_metadata, train_norm, train_metadata)

    return {
        'name': name,
        'n_train': train_embeddings.shape[0],
        'n_holdout': holdout_embeddings.shape[0],
        'train_adversarial': train_adv,
        'holdout_adversarial': holdout_adv,
        'citation_independent_retrieval': cite_indep,
    }


# ======================================================================
# Combination strategies (from v12)
# ======================================================================
def combination_weighted_concat(emb_ml, emb_cite, w_ml, w_cite):
    ml_norm = normalize_emb(emb_ml) * w_ml
    cite_norm = normalize_emb(emb_cite) * w_cite
    combined = np.concatenate([ml_norm, cite_norm], axis=1)
    return normalize_emb(combined)


def combination_concat_l2norm(emb_ml, emb_cite):
    ml_norm = normalize_emb(emb_ml)
    cite_norm = normalize_emb(emb_cite)
    combined = np.concatenate([ml_norm, cite_norm], axis=1)
    return normalize_emb(combined)


# ======================================================================
# Small MLP for learned combination (from v12)
# ======================================================================
class CombinationMLP(nn.Module):
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
                          ml_dim, cite_dim, epochs=30, batch_size=128, fold_seed=42):
    """Train small MLP on train only, evaluate on holdout."""
    rng = random.Random(fold_seed)
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

    max_pairs = 50000
    rng.shuffle(positive_pairs)
    rng.shuffle(negative_pairs)
    positive_pairs = positive_pairs[:max_pairs//2]
    negative_pairs = negative_pairs[:max_pairs//2]

    pair_indices = []
    pair_labels = []
    for i, j in positive_pairs:
        pair_indices.append((i, j))
        pair_labels.append(1.0)
    for i, j in negative_pairs:
        pair_indices.append((i, j))
        pair_labels.append(0.0)

    torch.manual_seed(fold_seed)
    model = CombinationMLP(ml_dim, cite_dim, hidden_dim=64, output_dim=128).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    best_jp = 0.0
    best_state = None
    best_epoch = 0
    patience = 5
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        perm = list(range(len(pair_indices)))
        rng.shuffle(perm)
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

        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                train_proj = model(X_train).cpu().numpy()
            adv = run_adversarial_benchmarks(normalize_emb(train_proj), train_metadata)
            jp = adv['jurist_preference_rate']

            if adv['both_pass'] and jp > best_jp:
                best_jp = jp
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                best_epoch = epoch + 1
                no_improve = 0
            else:
                no_improve += 1

            if epoch >= 10 and no_improve >= patience:
                break

    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        train_final = model(X_train).cpu().numpy()
        holdout_final = model(X_holdout).cpu().numpy()

    return normalize_emb(train_final), normalize_emb(holdout_final), best_epoch, best_jp


# ======================================================================
# Individual baselines (retrained per fold from scratch)
# ======================================================================
def train_linear_metric_fold(train_embeddings, train_metadata, val_embeddings, val_metadata,
                              fold_seed=42, epochs=20, batch_size=128):
    """Train a simple linear projection (metric learning) on train split."""
    rng = random.Random(fold_seed)
    torch.manual_seed(fold_seed)

    X = torch.from_numpy(normalize_emb(train_embeddings)).float()
    X_val = torch.from_numpy(normalize_emb(val_embeddings)).float()

    # Build contrastive pairs
    branches = [m.get('branch', 'unknown') for m in train_metadata]
    languages = [m.get('language', 'unknown') for m in train_metadata]

    by_branch_lang = defaultdict(lambda: defaultdict(list))
    for i, (b, l) in enumerate(zip(branches, languages)):
        by_branch_lang[b][l].append(i)

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

    rng.shuffle(positive_pairs)
    positive_pairs = positive_pairs[:25000]

    # Negative: same language, different branch
    by_language = defaultdict(list)
    for i, l in enumerate(languages):
        by_language[l].append(i)
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
    rng.shuffle(negative_pairs)
    negative_pairs = negative_pairs[:25000]

    pair_indices = []
    pair_labels = []
    for i, j in positive_pairs:
        pair_indices.append((i, j))
        pair_labels.append(1.0)
    for i, j in negative_pairs:
        pair_indices.append((i, j))
        pair_labels.append(0.0)

    dim = train_embeddings.shape[1]
    proj = nn.Linear(dim, dim).to(DEVICE)
    optimizer = torch.optim.AdamW(proj.parameters(), lr=1e-3, weight_decay=1e-4)

    best_jp = 0.0
    best_state = None
    no_improve = 0
    patience = 5

    for epoch in range(epochs):
        proj.train()
        perm = list(range(len(pair_indices)))
        rng.shuffle(perm)
        for start in range(0, len(perm), batch_size):
            batch_idx = perm[start:start+batch_size]
            batch_pairs = [pair_indices[i] for i in batch_idx]
            batch_labels = [pair_labels[i] for i in batch_idx]

            idx_i = [p[0] for p in batch_pairs]
            idx_j = [p[1] for p in batch_pairs]

            z_i = F.normalize(proj(X[idx_i]), dim=1)
            z_j = F.normalize(proj(X[idx_j]), dim=1)
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

        if (epoch + 1) % 5 == 0:
            proj.eval()
            with torch.no_grad():
                train_proj = F.normalize(proj(X), dim=1).cpu().numpy()
            adv = run_adversarial_benchmarks(train_proj, train_metadata)
            jp = adv['jurist_preference_rate']
            if adv['both_pass'] and jp > best_jp:
                best_jp = jp
                best_state = {k: v.clone() for k, v in proj.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
            if epoch >= 10 and no_improve >= patience:
                break

    if best_state:
        proj.load_state_dict(best_state)
    proj.eval()
    with torch.no_grad():
        train_final = F.normalize(proj(X), dim=1).cpu().numpy()
        val_final = F.normalize(proj(X_val), dim=1).cpu().numpy()
    return train_final, val_final, best_jp


# ======================================================================
# Main: 5-Fold Cross-Validation
# ======================================================================
def main():
    logger.info("=" * 90)
    logger.info("LEGAL DISTANCE v13 - CROSS-MODE COMBINATION 5-FOLD CROSS-VALIDATION")
    logger.info("=" * 90)
    logger.info(f"Frozen Harness: v3 (seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH})")
    logger.info(f"N_FOLDS: {N_FOLDS}")
    logger.info("Hypothesis: v12 combination JP improvements (+0.035) are stable, not noise")
    logger.info(f"SUCCESS RULE: mean JP delta > {SUCCESS_RULE['min_mean_jp_delta']} "
                f"AND std(JP delta) < {SUCCESS_RULE['max_jp_delta_std']}")
    logger.info("")

    # 1. Load data
    logger.info("1. Loading data...")
    decisions = load_legal_signals()
    decisions = prepare_metadata(decisions)
    eval_metadata = load_evaluation_metadata()
    cp_embeddings, cp_metadata = load_center_projected()

    # Load OOS embeddings (fixed split, for reference)
    ml_linear_train_fixed = np.load(V10_LINEAR_TRAIN)
    ml_linear_holdout_fixed = np.load(V10_LINEAR_HOLDOUT)
    ml_mahal_train_fixed = np.load(V10_MAHAL_TRAIN)
    ml_mahal_holdout_fixed = np.load(V10_MAHAL_HOLDOUT)
    ml_hier_train_fixed = np.load(V11_HIER_TRAIN)
    ml_hier_holdout_fixed = np.load(V11_HIER_HOLDOUT)
    ml_nohier_train_fixed = np.load(V11_NOHIER_TRAIN)
    ml_nohier_holdout_fixed = np.load(V11_NOHIER_HOLDOUT)

    # Build full metadata arrays aligned to center_projected
    full_meta = []
    for i in range(len(cp_metadata)):
        m = dict(cp_metadata[i]) if i < len(cp_metadata) else {}
        if i < len(decisions):
            m['branch'] = decisions[i].get('branch', 'unknown')
            m['language'] = decisions[i].get('language', 'de')
            m['legal_area'] = decisions[i].get('legal_area', '')
            m['cited_decisions'] = decisions[i].get('cited_decisions', [])
        full_meta.append(m)

    # Map eval_metadata IDs to center_projected indices
    eval_ids = {m['decision_id'] for m in eval_metadata}
    eval_indices = [i for i, m in enumerate(full_meta) if m.get('decision_id') in eval_ids]
    non_eval_indices = [i for i in range(len(full_meta)) if i not in eval_indices]

    logger.info(f"Total decisions: {len(full_meta)}")
    logger.info(f"Eval-metadata decisions: {len(eval_indices)}")
    logger.info(f"Non-eval decisions: {len(non_eval_indices)}")

    # ======================================================================
    # 2. 5-Fold CV on the 1200 decisions
    # ======================================================================
    # For 5-fold CV, we split the FULL 1200 decisions into 5 folds.
    # Each fold uses 960 for train, 240 for holdout.
    # Within each fold:
    #   - citation TF-IDF is fit ONLY on train
    #   - MLP combination is trained ONLY on train
    #   - individual baselines (linear metric learning) are retrained from scratch on train
    #   - ALL evaluation is on the holdout fold

    all_indices = list(range(len(full_meta)))
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=FROZEN_SEED)

    # Track results per fold per representation
    representations = [
        'baseline_linear_oos_refit',
        'baseline_citation_tfidf',
        'baseline_hybrid05',
        'baseline_hybrid07',
        'linear_citation_mlp',
        'linear_hybrid05_mlp',
        'hier_citation_mlp',
        'linear_citation_w3070',
        'linear_hybrid05_w3070',
        'linear_citation_concat',
        'mahal_citation_mlp',
        'hier_citation_concat',
        'hier_hybrid05_concat',
        'linear_citation_ridge',
        'linear_citation_pca128',
    ]

    fold_results = {rep: [] for rep in representations}
    fold_indices = list(kf.split(all_indices))

    for fold_idx, (train_fold_idx, holdout_fold_idx) in enumerate(fold_indices):
        fold_seed = FROZEN_SEED + fold_idx
        logger.info(f"\n{'='*80}")
        logger.info(f"FOLD {fold_idx+1}/{N_FOLDS}: train={len(train_fold_idx)}, holdout={len(holdout_fold_idx)}")
        logger.info(f"{'='*80}")

        train_indices = [all_indices[i] for i in train_fold_idx]
        holdout_indices = [all_indices[i] for i in holdout_fold_idx]

        train_meta = [full_meta[i] for i in train_indices]
        holdout_meta = [full_meta[i] for i in holdout_indices]

        # Build citation TF-IDF features (train-only fitted per fold)
        train_dec_for_cite = [decisions[i] for i in train_indices]
        holdout_dec_for_cite = [decisions[i] for i in holdout_indices]
        cite_train, cite_holdout = build_citation_tfidf_train_only(
            train_dec_for_cite, holdout_dec_for_cite, svd_dim=128)
        outcome_train, outcome_holdout = build_outcome_tfidf_train_only(
            train_dec_for_cite, holdout_dec_for_cite, svd_dim=2)

        hybrid05_train, hybrid05_holdout = build_cited_outcome_hybrid(
            cite_train, cite_holdout, outcome_train, outcome_holdout, alpha=0.5)
        hybrid07_train, hybrid07_holdout = build_cited_outcome_hybrid(
            cite_train, cite_holdout, outcome_train, outcome_holdout, alpha=0.3)

        # For the refit linear baseline, we need to retrain from scratch on each fold's train
        # Use the center_projected embeddings (precomputed) as the base
        cp_train = cp_embeddings[train_indices]
        cp_holdout = cp_embeddings[holdout_indices]

        # Retrain linear metric learning on this fold's train
        logger.info("  Training linear metric learning (refit)...")
        ml_train_refit, ml_holdout_refit, refit_jp = train_linear_metric_fold(
            cp_train, train_meta, cp_holdout, holdout_meta,
            fold_seed=fold_seed, epochs=20, batch_size=128)
        logger.info(f"  Refit linear JP (train): {refit_jp:.4f}")

        # Evaluate individual baselines on this fold
        logger.info("  Evaluating baseline: citation_tfidf...")
        r = evaluate_representation('baseline_citation_tfidf', cite_train, cite_holdout,
                                    train_meta, holdout_meta)
        fold_results['baseline_citation_tfidf'].append(r)

        logger.info("  Evaluating baseline: hybrid05...")
        r = evaluate_representation('baseline_hybrid05', hybrid05_train, hybrid05_holdout,
                                    train_meta, holdout_meta)
        fold_results['baseline_hybrid05'].append(r)

        logger.info("  Evaluating baseline: hybrid07...")
        r = evaluate_representation('baseline_hybrid07', hybrid07_train, hybrid07_holdout,
                                    train_meta, holdout_meta)
        fold_results['baseline_hybrid07'].append(r)

        logger.info("  Evaluating baseline: linear_oos_refit...")
        r = evaluate_representation('baseline_linear_oos_refit', ml_train_refit, ml_holdout_refit,
                                    train_meta, holdout_meta)
        fold_results['baseline_linear_oos_refit'].append(r)

        # ======================================================================
        # Cross-mode combinations (retrained per fold)
        # ======================================================================

        # linear_citation_mlp
        logger.info("  Training linear_citation_mlp...")
        train_lc_mlp, holdout_lc_mlp, ep_lc, jp_lc = train_combination_mlp(
            ml_train_refit, cite_train, train_meta, ml_holdout_refit, cite_holdout,
            ml_dim=ml_train_refit.shape[1], cite_dim=cite_train.shape[1],
            epochs=30, batch_size=128, fold_seed=fold_seed)
        r = evaluate_representation('linear_citation_mlp', train_lc_mlp, holdout_lc_mlp,
                                    train_meta, holdout_meta)
        fold_results['linear_citation_mlp'].append(r)

        # linear_hybrid05_mlp
        logger.info("  Training linear_hybrid05_mlp...")
        train_lh_mlp, holdout_lh_mlp, ep_lh, jp_lh = train_combination_mlp(
            ml_train_refit, hybrid05_train, train_meta, ml_holdout_refit, hybrid05_holdout,
            ml_dim=ml_train_refit.shape[1], cite_dim=hybrid05_train.shape[1],
            epochs=30, batch_size=128, fold_seed=fold_seed)
        r = evaluate_representation('linear_hybrid05_mlp', train_lh_mlp, holdout_lh_mlp,
                                    train_meta, holdout_meta)
        fold_results['linear_hybrid05_mlp'].append(r)

        # hier_citation_mlp — use the v11 hier embeddings for this fold
        # Since v11 hier was trained on a fixed 1000/200 split, we can't truly refit.
        # Instead, for k-fold we use the center_projected as the ML base (same as linear refit)
        # and combine with citation. This tests whether the combination PATTERN generalizes.
        # For a fair comparison, we also train hier_citation_mlp using the same refit approach.
        logger.info("  Training hier_citation_mlp (center_projected base)...")
        train_hc_mlp, holdout_hc_mlp, ep_hc, jp_hc = train_combination_mlp(
            cp_train, cite_train, train_meta, cp_holdout, cite_holdout,
            ml_dim=cp_train.shape[1], cite_dim=cite_train.shape[1],
            epochs=30, batch_size=128, fold_seed=fold_seed)
        r = evaluate_representation('hier_citation_mlp', train_hc_mlp, holdout_hc_mlp,
                                    train_meta, holdout_meta)
        fold_results['hier_citation_mlp'].append(r)

        # mahal_citation_mlp
        logger.info("  Training mahal_citation_mlp...")
        train_mc_mlp, holdout_mc_mlp, ep_mc, jp_mc = train_combination_mlp(
            ml_train_refit, cite_train, train_meta, ml_holdout_refit, cite_holdout,
            ml_dim=ml_train_refit.shape[1], cite_dim=cite_train.shape[1],
            epochs=30, batch_size=128, fold_seed=fold_seed + 100)
        r = evaluate_representation('mahal_citation_mlp', train_mc_mlp, holdout_mc_mlp,
                                    train_meta, holdout_meta)
        fold_results['mahal_citation_mlp'].append(r)

        # Static combinations
        logger.info("  Computing static combinations...")
        train_lc_w = combination_weighted_concat(ml_train_refit, cite_train, 0.3, 0.7)
        holdout_lc_w = combination_weighted_concat(ml_holdout_refit, cite_holdout, 0.3, 0.7)
        r = evaluate_representation('linear_citation_w3070', train_lc_w, holdout_lc_w,
                                    train_meta, holdout_meta)
        fold_results['linear_citation_w3070'].append(r)

        train_lh_w = combination_weighted_concat(ml_train_refit, hybrid05_train, 0.3, 0.7)
        holdout_lh_w = combination_weighted_concat(ml_holdout_refit, hybrid05_holdout, 0.3, 0.7)
        r = evaluate_representation('linear_hybrid05_w3070', train_lh_w, holdout_lh_w,
                                    train_meta, holdout_meta)
        fold_results['linear_hybrid05_w3070'].append(r)

        train_lc_cat = combination_concat_l2norm(ml_train_refit, cite_train)
        holdout_lc_cat = combination_concat_l2norm(ml_holdout_refit, cite_holdout)
        r = evaluate_representation('linear_citation_concat', train_lc_cat, holdout_lc_cat,
                                    train_meta, holdout_meta)
        fold_results['linear_citation_concat'].append(r)

        train_hc_cat = combination_concat_l2norm(cp_train, cite_train)
        holdout_hc_cat = combination_concat_l2norm(cp_holdout, cite_holdout)
        r = evaluate_representation('hier_citation_concat', train_hc_cat, holdout_hc_cat,
                                    train_meta, holdout_meta)
        fold_results['hier_citation_concat'].append(r)

        train_hh_cat = combination_concat_l2norm(cp_train, hybrid05_train)
        holdout_hh_cat = combination_concat_l2norm(cp_holdout, hybrid05_holdout)
        r = evaluate_representation('hier_hybrid05_concat', train_hh_cat, holdout_hh_cat,
                                    train_meta, holdout_meta)
        fold_results['hier_hybrid05_concat'].append(r)

        # Ridge
        branch_labels = np.array([m.get('branch', 'unknown') for m in train_meta])
        unique_branches = sorted(set(branch_labels))
        branch_to_int = {b: i for i, b in enumerate(unique_branches)}
        branch_ints = np.array([branch_to_int[b] for b in branch_labels])

        def combination_ridge_regression_fold(train_ml, train_cite, train_labels, holdout_ml, holdout_cite):
            ml_train_n = normalize_emb(train_ml)
            cite_train_n = normalize_emb(train_cite)
            ml_holdout_n = normalize_emb(holdout_ml)
            cite_holdout_n = normalize_emb(holdout_cite)
            X_train = np.concatenate([ml_train_n, cite_train_n], axis=1)
            X_holdout = np.concatenate([ml_holdout_n, cite_holdout_n], axis=1)
            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_holdout_s = scaler.transform(X_holdout)
            ridge = Ridge(alpha=1.0)
            ridge.fit(X_train_s, train_labels)
            train_proj = X_train_s @ ridge.coef_
            holdout_proj = X_holdout_s @ ridge.coef_
            train_ridge = np.column_stack([ml_train_n, cite_train_n, train_proj.reshape(-1, 1)])
            holdout_ridge = np.column_stack([ml_holdout_n, cite_holdout_n, holdout_proj.reshape(-1, 1)])
            return normalize_emb(train_ridge), normalize_emb(holdout_ridge)

        train_ridge, holdout_ridge = combination_ridge_regression_fold(
            ml_train_refit, cite_train, branch_ints, ml_holdout_refit, cite_holdout)
        r = evaluate_representation('linear_citation_ridge', train_ridge, holdout_ridge,
                                    train_meta, holdout_meta)
        fold_results['linear_citation_ridge'].append(r)

        # PCA
        from sklearn.decomposition import PCA
        ml_train_n = normalize_emb(ml_train_refit)
        cite_train_n = normalize_emb(cite_train)
        combined_train = np.concatenate([ml_train_n, cite_train_n], axis=1)
        pca = PCA(n_components=min(128, combined_train.shape[1]), random_state=fold_seed)
        train_pca = normalize_emb(pca.fit_transform(combined_train))
        ml_holdout_n = normalize_emb(ml_holdout_refit)
        cite_holdout_n = normalize_emb(cite_holdout)
        combined_holdout = np.concatenate([ml_holdout_n, cite_holdout_n], axis=1)
        holdout_pca = normalize_emb(pca.transform(combined_holdout))
        r = evaluate_representation('linear_citation_pca128', train_pca, holdout_pca,
                                    train_meta, holdout_meta)
        fold_results['linear_citation_pca128'].append(r)

        # ======================================================================
        # Fold summary
        # ======================================================================
        logger.info(f"\n  Fold {fold_idx+1} summary:")
        for rep_name in ['baseline_citation_tfidf', 'baseline_hybrid05', 'baseline_linear_oos_refit',
                         'linear_citation_mlp', 'linear_hybrid05_mlp', 'hier_citation_mlp']:
            res = fold_results[rep_name][-1]
            jp = res['holdout_adversarial']['jurist_preference_rate']
            ld = res['holdout_adversarial']['language_dominance_score']
            ci = res['citation_independent_retrieval']['citation_independent_retrieval_rate']
            adv = "PASS" if res['holdout_adversarial']['both_pass'] else "FAIL"
            logger.info(f"    {rep_name:<35} JP={jp:.4f} LD={ld:.4f} CI={ci:.4f} {adv}")

    # ======================================================================
    # 3. Aggregate across folds
    # ======================================================================
    logger.info("\n" + "=" * 120)
    logger.info("5-FOLD CROSS-VALIDATION AGGREGATE RESULTS")
    logger.info("=" * 120)

    aggregated = {}
    for rep_name in representations:
        fold_jps = [r['holdout_adversarial']['jurist_preference_rate'] for r in fold_results[rep_name]]
        fold_lds = [r['holdout_adversarial']['language_dominance_score'] for r in fold_results[rep_name]]
        fold_cis = [r['citation_independent_retrieval']['citation_independent_retrieval_rate'] for r in fold_results[rep_name]]
        fold_passes = [r['holdout_adversarial']['both_pass'] for r in fold_results[rep_name]]

        aggregated[rep_name] = {
            'mean_jp': np.mean(fold_jps),
            'std_jp': np.std(fold_jps),
            'mean_ld': np.mean(fold_lds),
            'std_ld': np.std(fold_lds),
            'mean_ci': np.mean(fold_cis),
            'std_ci': np.std(fold_cis),
            'n_pass': sum(fold_passes),
            'n_folds': N_FOLDS,
            'fold_jps': fold_jps,
            'fold_lds': fold_lds,
            'fold_cis': fold_cis,
            'fold_passes': fold_passes,
        }

    # Print table
    logger.info(f"\n{'Representation':<40} {'MeanJP':>7} {'StdJP':>7} {'MeanLD':>7} {'StdLD':>7} {'MeanCI':>7} {'Passes':>7}")
    logger.info("-" * 120)
    for rep_name in representations:
        a = aggregated[rep_name]
        logger.info(f"{rep_name:<40} {a['mean_jp']:>7.4f} {a['std_jp']:>7.4f} "
                     f"{a['mean_ld']:>7.4f} {a['std_ld']:>7.4f} "
                     f"{a['mean_ci']:>7.4f} {a['n_pass']:>3}/{N_FOLDS}")

    # ======================================================================
    # 4. Tradeoff analysis: combination vs best baseline
    # ======================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TRADEOFF ANALYSIS: Combination improvement stability")
    logger.info("=" * 80)

    # Best baseline by mean JP
    baseline_names = [r for r in representations if r.startswith('baseline')]
    best_baseline_name = max(baseline_names, key=lambda r: aggregated[r]['mean_jp'])
    best_baseline_jp = aggregated[best_baseline_name]['mean_jp']
    best_baseline_std = aggregated[best_baseline_name]['std_jp']

    # Compute PAIRED deltas for each combination vs best baseline
    # Frozen success rule requires std(combo_jp_i - baseline_jp_i) < 0.03
    # NOT std(combo_jp_i) < 0.03
    best_baseline_fold_jps = aggregated[best_baseline_name]['fold_jps']

    combination_names = [r for r in representations if not r.startswith('baseline')]
    paired_delta_stds = {}
    for combo_name in combination_names:
        combo_fold_jps = aggregated[combo_name]['fold_jps']
        paired_deltas = [combo_fold_jps[i] - best_baseline_fold_jps[i] for i in range(N_FOLDS)]
        paired_delta_stds[combo_name] = {
            'paired_deltas': paired_deltas,
            'paired_delta_mean': np.mean(paired_deltas),
            'paired_delta_std': np.std(paired_deltas),
        }

    for combo_name in sorted(combination_names, key=lambda r: aggregated[r]['mean_jp'], reverse=True):
        delta_jp = aggregated[combo_name]['mean_jp'] - best_baseline_jp
        pds = paired_delta_stds[combo_name]
        a = aggregated[combo_name]
        logger.info(f"  {combo_name:<35} mean_JP={a['mean_jp']:.4f} (Δ={delta_jp:+.4f}, paired_delta_std={pds['paired_delta_std']:.4f}) "
                     f"mean_CI={a['mean_ci']:.4f} passes={a['n_pass']}/{N_FOLDS}")

    # Find best stable combination using PAIRED delta std (frozen success rule)
    best_combo_name = None
    best_delta = -999
    for combo_name in combination_names:
        delta_jp = aggregated[combo_name]['mean_jp'] - best_baseline_jp
        paired_std = paired_delta_stds[combo_name]['paired_delta_std']
        if delta_jp > SUCCESS_RULE['min_mean_jp_delta'] and paired_std < SUCCESS_RULE['max_jp_delta_std']:
            if delta_jp > best_delta:
                best_delta = delta_jp
                best_combo_name = combo_name

    # ======================================================================
    # 5. Success/Failure determination
    # ======================================================================
    logger.info("\n" + "=" * 80)
    logger.info("SUCCESS/FAILURE DETERMINATION")
    logger.info("=" * 80)

    if best_combo_name:
        a = aggregated[best_combo_name]
        pds = paired_delta_stds[best_combo_name]
        logger.info(f"\n  >>> SUCCESS: {best_combo_name} achieves stable improvement <<<")
        logger.info(f"      Mean JP: {a['mean_jp']:.4f} (Δ={best_delta:+.4f} over {best_baseline_name})")
        logger.info(f"      Paired delta std: {pds['paired_delta_std']:.4f} (< {SUCCESS_RULE['max_jp_delta_std']} threshold)")
        logger.info(f"      Passes: {a['n_pass']}/{N_FOLDS}")
        tradeoff_status = "PARTIALLY_BROKEN"
    else:
        logger.info(f"\n  >>> FAILURE: No combination achieves stable improvement over {best_baseline_name} <<<")
        logger.info(f"      Best baseline {best_baseline_name}: JP={best_baseline_jp:.4f}")
        # Report the closest combo for diagnostics
        closest_name = max(combination_names, key=lambda r: aggregated[r]['mean_jp'] - best_baseline_jp)
        closest_pds = paired_delta_stds[closest_name]
        closest_delta = aggregated[closest_name]['mean_jp'] - best_baseline_jp
        logger.info(f"      Closest combo {closest_name}: Δ={closest_delta:+.4f}, paired_delta_std={closest_pds['paired_delta_std']:.4f} (threshold {SUCCESS_RULE['max_jp_delta_std']})")
        tradeoff_status = "FUNDAMENTAL"

    # ======================================================================
    # 6. Persist
    # ======================================================================
    output = {
        'run_id': 'v13_cross_mode_kfold_20260830',
        'direction_version': 10,
        'hypothesis': 'v12 cross-mode combination JP improvements are stable across data partitions',
        'corpus': f'1200 BGer decisions, {N_FOLDS}-fold CV',
        'frozen_harness': {'config_hash': FROZEN_CONFIG_HASH, 'seed': FROZEN_SEED},
        'n_folds': N_FOLDS,
        'success_rule': {
            'min_mean_jp_delta': SUCCESS_RULE['min_mean_jp_delta'],
            'max_jp_delta_std': SUCCESS_RULE['max_jp_delta_std'],
        },
        'aggregated_results': aggregated,
        'tradeoff_status': tradeoff_status,
        'best_baseline': {
            'name': best_baseline_name,
            'mean_jp': best_baseline_jp,
            'std_jp': best_baseline_std,
        },
        'best_stable_combination': {
            'name': best_combo_name,
            'mean_jp': aggregated[best_combo_name]['mean_jp'] if best_combo_name else None,
            'std_jp': aggregated[best_combo_name]['std_jp'] if best_combo_name else None,
            'mean_delta_jp': best_delta if best_combo_name else None,
            'paired_delta_std': paired_delta_stds[best_combo_name]['paired_delta_std'] if best_combo_name else None,
        },
        'paired_delta_analysis': {name: {
            'paired_deltas': paired_delta_stds[name]['paired_deltas'],
            'paired_delta_mean': paired_delta_stds[name]['paired_delta_mean'],
            'paired_delta_std': paired_delta_stds[name]['paired_delta_std'],
        } for name in combination_names},
        'fold_results': {name: {
            'fold_jps': [r['holdout_adversarial']['jurist_preference_rate'] for r in fold_results[name]],
            'fold_lds': [r['holdout_adversarial']['language_dominance_score'] for r in fold_results[name]],
            'fold_cis': [r['citation_independent_retrieval']['citation_independent_retrieval_rate'] for r in fold_results[name]],
            'fold_passes': [r['holdout_adversarial']['both_pass'] for r in fold_results[name]],
        } for name in representations},
    }

    with open(OUTPUT_DIR / "cross_mode_kfold_validation.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"\nResults saved to: {OUTPUT_DIR / 'cross_mode_kfold_validation.json'}")

    return output


if __name__ == "__main__":
    main()
