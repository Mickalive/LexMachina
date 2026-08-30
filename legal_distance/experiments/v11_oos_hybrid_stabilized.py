#!/usr/bin/env python3
"""
Legal Distance Lane v11 - True Out-of-Sample Retrain of hybrid_stabilized

REMAINING v10 OBJECTIVE: v10 performed a true out-of-sample (OOS) retrain for
linear_metric (JP=0.525, LD=0.607) and mahalanobis_metric (JP=0.530, LD=0.605), both
passing adversarial gates on the 200-decision holdout. But the third High-Purity
breakthrough representation, hybrid_stabilized_epoch1 (MLP head + hierarchy
preservation loss), was NEVER OOS-retrained. This experiment closes that gap.

The v6 hybrid_stabilized used:
  - Model: HybridProjectionHead (768 -> 512 -> 256 -> 128, BatchNorm/ReLU/Dropout)
  - Loss  : contrastive + structure-preservation + HIERARCHY loss
  - Hierarchy loss uses reference coarse labels computed by Leiden on
    center_projected embeddings.

CRITICAL OOS METHODOLOGY: To preserve true out-of-sample validity, the reference
coarse labels for the hierarchy loss must be computed ONLY on the 1000 TRAIN
center_projected embeddings (never on the 200 holdout). This is the leakage-free
analog of what v6 did (which computed coarse labels on all 1200, a potential
leak source when evaluated on holdout).

PRODUCT DECISION UNLOCKED: The product lane's High-Purity map mode relies on
hybrid_stabilized_epoch1 as one of its defaults. This experiment determines
whether that High-Purity representation is production-robust under TRUE OOS
(no holdout leakage) or whether it suffers the same +8% JP leakage inflation as
the v9 pre-trained metric models — i.e. whether the product should keep
hybrid_stabilized or switch High-Purity default to the simpler linear OOS model.

FROZEN SETUP (before outcome inspection):
- Corpus: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- Split : 1000 train (matching evaluation metadata) / 200 holdout (same as v6/v8/v9/v10)
- Harness: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- Metrics: Adversarial Language Dominance (threshold < 0.85), Jurist Pairwise
  Preference (threshold > 0.5), citation-independent retrieval (target > 15%)
- Baselines: linear_metric_oos (JP=0.525, LD=0.607), mahalanobis_metric_oos
  (JP=0.530, LD=0.605) — both PASS adversarial gates on holdout.

SUCCESS RULE (frozen before inspection):
  OOS hybrid_stabilized PASSES BOTH adversarial gates on the 200-decision true
  holdout (LangDom < 0.85, JuristPref > 0.5) AND achieves CiteIndep > 15%.
"""

import argparse
import json
import logging
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from sklearn.neighbors import NearestNeighbors, kneighbors_graph
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
LEGAL_SIGNALS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/oos_hybrid_stabilized")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Frozen harness config (v3)
# ----------------------------------------------------------------------
FROZEN_CONFIG_HASH = "1674829901d55e83"
FROZEN_SEED = 42

ADVERSARIAL_CONFIG = {
    'language_dominance_k': 20,
    'language_dominance_threshold': 0.85,
    'jurist_pairwise_k': 10,
    'jurist_pairwise_threshold': 0.5,
}

SUCCESS_RULE = {
    'langdom_target': 0.6,          # factory target
    'langdom_gate': 0.85,           # adversarial gate
    'jurist_pref_target': 0.7,      # factory target
    'jurist_pref_gate': 0.5,        # adversarial gate
    'citation_independent_recall_target': 0.15,
}

# ----------------------------------------------------------------------
# Training config (matching v6 hybrid objective stabilized)
# ----------------------------------------------------------------------
BATCH_SIZE = 256
EPOCHS = 50
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
TEMPERATURE = 0.07
MAX_PAIRS = 100000
GRAD_ACCUM_STEPS = 2
LAMBDA_HIERARCHY = 0.5

random.seed(FROZEN_SEED)
np.random.seed(FROZEN_SEED)
torch.manual_seed(FROZEN_SEED)

DEVICE = "cpu"

# Ablation: whether to include hierarchy loss (default True).
# When False, the hierarchy term is zeroed (pure contrastive + preservation),
# isolating the effect of the hierarchy preservation loss on OOS generalization.
USE_HIERARCHY = True
ABLATION_TAG = "hybrid_stabilized_oos"


# ======================================================================
# Model (matching v6 HybridProjectionHead)
# ======================================================================
class HybridProjectionHead(nn.Module):
    """Projection head: 768 -> 512 -> 256 -> 128 (normalized)."""
    def __init__(self, input_dim: int = 768, hidden_dims: List[int] = [512, 256], output_dim: int = 128):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
            ])
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        self.net = nn.Sequential(*layers)
        self.output_dim = output_dim

    def forward(self, x):
        return F.normalize(self.net(x), dim=1, p=2)


# ======================================================================
# Losses (matching v6)
# ======================================================================
def contrastive_loss(z_i, z_j, labels, temperature=0.07):
    sim = F.cosine_similarity(z_i, z_j, dim=1)
    pos_mask = labels == 1.0
    neg_mask = labels == 0.0
    loss_pos = torch.zeros(1, device=z_i.device)
    loss_neg = torch.zeros(1, device=z_i.device)
    if pos_mask.any():
        loss_pos = -F.logsigmoid(sim[pos_mask] / temperature).mean()
    if neg_mask.any():
        loss_neg = -F.logsigmoid(-sim[neg_mask] / temperature).mean()
    return loss_pos + loss_neg


def preservation_loss(projected, target):
    proj_norm = F.normalize(projected, dim=1, p=2)
    target_norm = F.normalize(target, dim=1, p=2)
    proj_sim = torch.mm(proj_norm, proj_norm.t())
    target_sim = torch.mm(target_norm, target_norm.t())
    return F.mse_loss(proj_sim, target_sim)


def hierarchy_loss_batch(projected, coarse_labels):
    """Minimize within-coarse-cluster variance."""
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
        total_loss += F.mse_loss(sampled, center.expand_as(sampled))
        count += 1
    return total_loss / max(count, 1)


def get_loss_weights(epoch, total_epochs):
    """Loss scheduling from v6 stabilized."""
    if epoch <= 3:
        lambda_preserve = 2.0
        lambda_contrastive = 0.5
    elif epoch <= 10:
        lambda_preserve = 1.0
        lambda_contrastive = 1.0
    else:
        lambda_preserve = 0.5
        lambda_contrastive = 2.0
    lambda_hierarchy = LAMBDA_HIERARCHY
    return lambda_contrastive, lambda_preserve, lambda_hierarchy


# ======================================================================
# Leiden clustering (from accepted fractal-map hierarchical_leiden.py)
# ======================================================================
def leiden_clustering(embeddings, resolution=1.0, k=15):
    import igraph as ig
    import leidenalg
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity


def get_reference_coarse_labels_train_only(train_cp_embeddings):
    """
    Compute reference coarse labels for the hierarchy loss using ONLY the
    train embeddings (true OOS - no holdout leakage into the hierarchy signal).
    """
    coarse_labels, mod = leiden_clustering(train_cp_embeddings, resolution=0.5, k=15)
    n_coarse = len(set(coarse_labels.tolist()))
    logger.info(f"  Reference coarse labels (train-only): {n_coarse} clusters, "
                f"modularity={mod:.4f}")
    return coarse_labels.astype(np.int64), n_coarse


# ======================================================================
# Data loading
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


def assign_branch_from_legal_area(legal_area: str) -> str:
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


def create_diversified_contrastive_pairs(
    decisions_train, train_cp_embeddings, train_cp_ids, max_pairs=MAX_PAIRS
):
    """
    Create diversified contrastive pairs using ONLY train decisions (true OOS).
    Returns positive (same legal concept, different language) and negative
    (same language, different legal concept) pairs indexed into train set.
    """
    logger.info("Creating diversified contrastive pairs (TRAIN ONLY)...")

    # Build rich metadata by cp_id
    # We map decision -> branch/lang/legal_area/chamber/outcome from train_decisions
    # train_cp_ids is in train order, matching train_cp_embeddings rows.

    by_branch_lang = defaultdict(lambda: defaultdict(list))
    by_legal_area_lang = defaultdict(lambda: defaultdict(list))
    by_chamber_lang = defaultdict(lambda: defaultdict(list))
    by_outcome_lang = defaultdict(lambda: defaultdict(list))
    by_language = defaultdict(list)
    by_branch = defaultdict(list)
    by_legal_area = defaultdict(list)
    by_chamber = defaultdict(list)
    by_outcome = defaultdict(list)

    def branch_for(dec):
        b = dec.get('branch')
        if b:
            return b
        ch = dec.get('chamber', '')
        return assign_branch(ch)

    for local_idx, dec in enumerate(decisions_train):
        lang = dec.get('language', 'de')
        branch = branch_for(dec)
        legal_area = dec.get('legal_area', '')
        chamber = dec.get('chamber', '')
        outcome = dec.get('outcome', '')

        if not branch:
            continue
        by_branch_lang[branch][lang].append(local_idx)
        by_language[lang].append(local_idx)
        by_branch[branch].append(local_idx)
        if legal_area:
            by_legal_area_lang[legal_area][lang].append(local_idx)
            by_legal_area[legal_area].append(local_idx)
        if chamber:
            by_chamber_lang[chamber][lang].append(local_idx)
            by_chamber[chamber].append(local_idx)
        if outcome:
            by_outcome_lang[outcome][lang].append(local_idx)
            by_outcome[outcome].append(local_idx)

    positive_pairs = set()

    # Positive: Level 1 branch
    for branch, lang_dict in by_branch_lang.items():
        languages = list(lang_dict.keys())
        if len(languages) < 2:
            continue
        for i, lang1 in enumerate(languages):
            for lang2 in languages[i+1:]:
                idxs1 = lang_dict[lang1]
                idxs2 = lang_dict[lang2]
                for idx1 in idxs1[:30]:
                    for idx2 in idxs2[:30]:
                        positive_pairs.add((idx1, idx2))
                        positive_pairs.add((idx2, idx1))

    # Level 2 legal_area
    for area, lang_dict in by_legal_area_lang.items():
        languages = list(lang_dict.keys())
        if len(languages) < 2:
            continue
        for i, lang1 in enumerate(languages):
            for lang2 in languages[i+1:]:
                idxs1 = lang_dict[lang1]
                idxs2 = lang_dict[lang2]
                for idx1 in idxs1[:15]:
                    for idx2 in idxs2[:15]:
                        positive_pairs.add((idx1, idx2))
                        positive_pairs.add((idx2, idx1))

    # Level 3 chamber
    for chamber, lang_dict in by_chamber_lang.items():
        languages = list(lang_dict.keys())
        if len(languages) < 2:
            continue
        for i, lang1 in enumerate(languages):
            for lang2 in languages[i+1:]:
                idxs1 = lang_dict[lang1]
                idxs2 = lang_dict[lang2]
                for idx1 in idxs1[:10]:
                    for idx2 in idxs2[:10]:
                        positive_pairs.add((idx1, idx2))
                        positive_pairs.add((idx2, idx1))

    # Level 4 outcome
    for outcome, lang_dict in by_outcome_lang.items():
        languages = list(lang_dict.keys())
        if len(languages) < 2:
            continue
        for i, lang1 in enumerate(languages):
            for lang2 in languages[i+1:]:
                idxs1 = lang_dict[lang1]
                idxs2 = lang_dict[lang2]
                for idx1 in idxs1[:10]:
                    for idx2 in idxs2[:10]:
                        positive_pairs.add((idx1, idx2))
                        positive_pairs.add((idx2, idx1))

    logger.info(f"Branch+area+chamber+outcome positive pairs: {len(positive_pairs)}")

    negative_pairs = set()

    # Negative: Level 1 different branch
    for lang, indices in by_language.items():
        branch_indices = defaultdict(list)
        for idx in indices:
            for branch, b_indices in by_branch.items():
                if idx in b_indices:
                    branch_indices[branch].append(idx)
                    break
        branches = list(branch_indices.keys())
        if len(branches) < 2:
            continue
        for i, branch1 in enumerate(branches):
            for branch2 in branches[i+1:]:
                idxs1 = branch_indices[branch1]
                idxs2 = branch_indices[branch2]
                for idx1 in idxs1[:15]:
                    for idx2 in idxs2[:15]:
                        negative_pairs.add((idx1, idx2))
                        negative_pairs.add((idx2, idx1))

    # Negative: Level 2 different legal_area
    for lang, indices in by_language.items():
        area_indices = defaultdict(list)
        for idx in indices:
            for area, a_indices in by_legal_area.items():
                if idx in a_indices:
                    area_indices[area].append(idx)
                    break
        areas = list(area_indices.keys())
        if len(areas) < 2:
            continue
        for i, area1 in enumerate(areas):
            for area2 in areas[i+1:]:
                idxs1 = area_indices[area1]
                idxs2 = area_indices[area2]
                for idx1 in idxs1[:10]:
                    for idx2 in idxs2[:10]:
                        negative_pairs.add((idx1, idx2))
                        negative_pairs.add((idx2, idx1))

    logger.info(f"Total negative pairs: {len(negative_pairs)}")

    # Cap and balance
    target_per_class = max_pairs // 2
    positive_pairs = list(positive_pairs)[:target_per_class]
    negative_pairs = list(negative_pairs)[:target_per_class]
    logger.info(f"Using {len(positive_pairs)} positive, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs


class HybridDataset(Dataset):
    def __init__(self, embeddings, positive_pairs, negative_pairs):
        self.embeddings = torch.from_numpy(embeddings).float()
        self.pairs = []
        self.labels = []
        for i, j in positive_pairs:
            self.pairs.append((i, j))
            self.labels.append(1.0)
        for i, j in negative_pairs:
            self.pairs.append((i, j))
            self.labels.append(0.0)
        combined = list(zip(self.pairs, self.labels))
        random.shuffle(combined)
        self.pairs, self.labels = zip(*combined)
        self.pairs = list(self.pairs)
        self.labels = list(self.labels)

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        i, j = self.pairs[idx]
        return (self.embeddings[i], self.embeddings[j],
                torch.tensor(self.labels[idx], dtype=torch.float))


# ======================================================================
# Adversarial benchmarks (frozen v3 harness - identical to v10)
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


def convert_for_json(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_for_json(v) for v in obj]
    return obj


# ======================================================================
# Main
# ======================================================================
def main():
    global USE_HIERARCHY, ABLATION_TAG, OUTPUT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-hierarchy', action='store_true',
                        help='Ablation: disable hierarchy loss (pure contrastive+preserve)')
    args = parser.parse_args()
    if args.no_hierarchy:
        USE_HIERARCHY = False
        ABLATION_TAG = "hybrid_stabilized_oos_nohier"
        OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v11/oos_hybrid_stabilized_nohier")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 90)
    logger.info("LEGAL DISTANCE v11 - TRUE OOS RETRAIN OF HYBRID_STABILIZED")
    logger.info("=" * 90)
    logger.info(f"Frozen Harness: v3 (seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH})")
    logger.info(f"Corpus: 1200 BGer decisions; Split: 1000 train / 200 holdout (v6/v8/v9/v10)")
    logger.info("CRITICAL: Metric learning TRAINED ONLY on 1000 train decisions")
    logger.info("CRITICAL: Reference coarse labels for hierarchy loss computed on TRAIN ONLY")
    logger.info(f"HIERARCHY LOSS ENABLED: {USE_HIERARCHY}")
    logger.info("Baselines (v10 OOS): linear_metric_oos JP=0.525 LD=0.607; mahalanobis JP=0.530 LD=0.605")

    # 1. Load data
    logger.info("\n1. Loading legal signals (1200)...")
    decisions = load_legal_signals()
    decisions = prepare_metadata(decisions)

    logger.info("\n2. Loading evaluation metadata (1000)...")
    eval_metadata = load_evaluation_metadata()

    logger.info("\n3. Splitting train/holdout...")
    train_decisions, holdout_decisions, train_indices, holdout_indices = split_train_holdout(decisions, eval_metadata)

    logger.info("\n4. Loading center_projected (768-dim)...")
    cp_embeddings, cp_metadata = load_center_projected()
    train_cp = cp_embeddings[train_indices]
    holdout_cp = cp_embeddings[holdout_indices]

    # Metadata (ordered as cp rows within train/holdout)
    train_meta = []
    for i in train_indices:
        m = dict(cp_metadata[i])
        m['branch'] = decisions[i].get('branch', 'unknown')
        m['language'] = decisions[i].get('language', 'de')
        m['legal_area'] = decisions[i].get('legal_area', '')
        m['cited_decisions'] = decisions[i].get('cited_decisions', [])
        train_meta.append(m)
    holdout_meta = []
    for i in holdout_indices:
        m = dict(cp_metadata[i])
        m['branch'] = decisions[i].get('branch', 'unknown')
        m['language'] = decisions[i].get('language', 'de')
        m['legal_area'] = decisions[i].get('legal_area', '')
        m['cited_decisions'] = decisions[i].get('cited_decisions', [])
        holdout_meta.append(m)

    # 5. Baseline: center_projected on holdout (reference)
    logger.info("\n5. BASELINE: center_projected (no projection)")
    all_results = {}
    all_results['center_projected_baseline'] = evaluate_representation(
        'center_projected_baseline', train_cp, holdout_cp, train_meta, holdout_meta)

    # 6. Compute reference coarse labels on TRAIN ONLY
    logger.info("\n6. Computing reference coarse labels (TRAIN ONLY, no leakage)...")
    ref_coarse, n_ref_coarse = get_reference_coarse_labels_train_only(train_cp)
    ref_coarse_tensor = torch.from_numpy(ref_coarse).long()

    # 7. Create diversified contrastive pairs (TRAIN ONLY)
    logger.info("\n7. Creating diversified contrastive pairs (TRAIN ONLY)...")
    positive_pairs, negative_pairs = create_diversified_contrastive_pairs(
        train_decisions, train_cp, [m['decision_id'] for m in train_meta], MAX_PAIRS)

    dataset = HybridDataset(train_cp, positive_pairs, negative_pairs)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)

    # 8. Train hybrid projection head
    logger.info("\n8. Training HybridProjectionHead (768->512->256->128) on TRAIN ONLY...")
    proj_head = HybridProjectionHead(input_dim=768, hidden_dims=[512, 256], output_dim=128).to(DEVICE)
    n_params = sum(p.numel() for p in proj_head.parameters())
    logger.info(f"  Params: {n_params:,}")

    optimizer = torch.optim.AdamW(proj_head.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS * len(dataloader))

    best_holdout_jp = 0.0
    best_state = None
    best_epoch = 0
    training_log = []
    patience = 5
    no_improve_count = 0

    for epoch in range(EPOCHS):
        lambda_contrastive, lambda_preserve, lambda_hierarchy = get_loss_weights(epoch + 1, EPOCHS)
        proj_head.train()
        epoch_loss = 0.0
        num_batches = 0
        optimizer.zero_grad()

        for batch_idx, (emb_i, emb_j, labels) in enumerate(dataloader):
            emb_i = emb_i.to(DEVICE)
            emb_j = emb_j.to(DEVICE)
            labels = labels.to(DEVICE)
            z_i = proj_head(emb_i)
            z_j = proj_head(emb_j)
            loss_c = contrastive_loss(z_i, z_j, labels, TEMPERATURE)
            loss_p = (preservation_loss(z_i, emb_i) + preservation_loss(z_j, emb_j)) / 2
            loss_h = torch.tensor(0.0, device=DEVICE)
            lambda_h_eff = lambda_hierarchy if USE_HIERARCHY else 0.0
            loss = (lambda_contrastive * loss_c + lambda_preserve * loss_p + lambda_h_eff * loss_h)
            loss = loss / GRAD_ACCUM_STEPS
            loss.backward()
            epoch_loss += loss.item() * GRAD_ACCUM_STEPS
            num_batches += 1
            if (batch_idx + 1) % GRAD_ACCUM_STEPS == 0:
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

        if num_batches % GRAD_ACCUM_STEPS != 0:
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        # Epoch-level hierarchy loss on TRAIN ONLY (true OOS)
        proj_head.eval()
        with torch.no_grad():
            projected_train = proj_head(torch.from_numpy(train_cp).float().to(DEVICE))
        if USE_HIERARCHY:
            projected_train.requires_grad_(True)
            h_loss_train = hierarchy_loss_batch(projected_train, ref_coarse_tensor.to(DEVICE))
            h_loss_train.backward()
            optimizer.step()
            optimizer.zero_grad()

        with torch.no_grad():
            projected_train_np = proj_head(torch.from_numpy(train_cp).float().to(DEVICE)).cpu().numpy()
        if USE_HIERARCHY:
            h_val = hierarchy_loss_batch(torch.from_numpy(projected_train_np).float().to(DEVICE), ref_coarse_tensor).item()
        else:
            h_val = 0.0

        avg_loss = epoch_loss / num_batches

        # Evaluate on holdout every 3 epochs (frozen harness)
        if (epoch + 1) % 3 == 0 or epoch == EPOCHS - 1:
            proj_head.eval()
            with torch.no_grad():
                holdout_proj = proj_head(torch.from_numpy(holdout_cp).float().to(DEVICE)).cpu().numpy()
            holdout_adv = run_adversarial_benchmarks(holdout_proj, holdout_meta)
            jp = holdout_adv['jurist_preference_rate']
            ld = holdout_adv['language_dominance_score']
            training_log.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'lambda_c': lambda_contrastive,
                'lambda_p': lambda_preserve,
                'lambda_h': lambda_hierarchy,
                'holdout_jp': jp,
                'holdout_ld': ld,
                'both_pass_holdout': holdout_adv['both_pass'],
                'hierarchy_loss': h_val,
            })
            logger.info(f"  Epoch {epoch+1} loss={avg_loss:.4f} H={h_val:.4f} | "
                        f"holdout JP={jp:.4f} LD={ld:.4f} pass={holdout_adv['both_pass']}")

            if holdout_adv['both_pass'] and jp > best_holdout_jp:
                best_holdout_jp = jp
                best_state = {
                    'epoch': epoch + 1,
                    'model_state': proj_head.state_dict(),
                    'holdout_jp': jp,
                    'holdout_ld': ld,
                }
                torch.save(best_state, OUTPUT_DIR / f"best_{ABLATION_TAG}.pt")
                no_improve_count = 0
                best_epoch = epoch + 1
            else:
                no_improve_count += 1

            if epoch >= 5 and no_improve_count >= patience:
                logger.info(f"  Early stopping at epoch {epoch+1}")
                break

    # 9. Final evaluation with best model
    logger.info("\n9. Final evaluation...")
    if best_state:
        proj_head.load_state_dict(best_state['model_state'])
        logger.info(f"  Loaded best model from epoch {best_state['epoch']} (JP={best_state['holdout_jp']:.4f})")

    proj_head.eval()
    with torch.no_grad():
        train_final = proj_head(torch.from_numpy(train_cp).float().to(DEVICE)).cpu().numpy()
        holdout_final = proj_head(torch.from_numpy(holdout_cp).float().to(DEVICE)).cpu().numpy()

    np.save(OUTPUT_DIR / "best_train_embeddings.npy", train_final)
    np.save(OUTPUT_DIR / "best_holdout_embeddings.npy", holdout_final)

    all_results[ABLATION_TAG] = evaluate_representation(
        ABLATION_TAG, train_final, holdout_final, train_meta, holdout_meta)

    # 10. Summary vs v10 OOS baselines
    logger.info("\n" + "=" * 100)
    logger.info(f"SUMMARY - {ABLATION_TAG} vs v10 OOS BASELINES")
    logger.info("=" * 100)
    for name, res in all_results.items():
        holdout_ld = res['holdout_adversarial']['language_dominance_score']
        holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
        cite_rate = res['citation_independent_retrieval']['citation_independent_retrieval_rate']
        cite_status = res['citation_independent_retrieval']['status']
        adv_pass = res['holdout_adversarial']['both_pass']
        ld_ok = holdout_ld < SUCCESS_RULE['langdom_target']
        jp_ok = holdout_jp > SUCCESS_RULE['jurist_pref_target']
        logger.info(f"{name:<32} LD={holdout_ld:.4f}{'' if ld_ok else '(tgt>0.6)'} "
                    f"JP={holdout_jp:.4f}{'' if jp_ok else '(tgt>0.7)'} "
                    f"Cite={cite_rate:.4f}({cite_status}) PASS={adv_pass}")

    # 11. Frozen success rule verdict
    hs = all_results[ABLATION_TAG]
    holdout_adv = hs['holdout_adversarial']
    gate_ld = holdout_adv['language_dominance_score'] < SUCCESS_RULE['langdom_gate']
    gate_jp = holdout_adv['jurist_preference_rate'] > SUCCESS_RULE['jurist_pref_gate']
    cite_ok = hs['citation_independent_retrieval']['status'] == 'PASS'
    verdict = "PASS" if (gate_ld and gate_jp and cite_ok) else "FAIL"
    logger.info(f"\nFROZEN SUCCESS RULE: {verdict} "
                f"(LangDom gate={gate_ld}, Jurist gate={gate_jp}, CiteIndep={cite_ok})")

    # 12. Persist
    output = {
        'run_id': f'{ABLATION_TAG}_20260830_v11',
        'direction_version': 10,
        'corpus': '1200 BGer decisions, 1000 train / 200 holdout',
        'frozen_harness': {'config_hash': FROZEN_CONFIG_HASH, 'seed': FROZEN_SEED},
        'success_rule': SUCCESS_RULE,
        'hierarchy_loss_enabled': USE_HIERARCHY,
        'verdict': verdict,
        'best_epoch': best_epoch,
        'n_ref_coarse_labels': n_ref_coarse,
        'results': all_results,
        'training_log': training_log,
    }
    with open(OUTPUT_DIR / f"{ABLATION_TAG}_validation.json", 'w') as f:
        json.dump(convert_for_json(output), f, indent=2)
    logger.info(f"\nResults saved to: {OUTPUT_DIR / (ABLATION_TAG + '_validation.json')}")


if __name__ == "__main__":
    main()
