#!/usr/bin/env python3
"""
Legal Distance Lane v10 - True Out-of-Sample Metric Learning Retrain

Tests whether supervised metric learning generalizes when TRAINED ONLY on 1000
train decisions and evaluated on 200 held-out decisions. This eliminates the
pre-training leakage caveat from v9 (where metric learning was pre-trained on
full 1200 including holdout).

Frozen setup:
- Corpus: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- Split: 1000 train (matching evaluation metadata) / 200 holdout (same as v6/v8/v9)
- Harness: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- Metrics: Adversarial Language Dominance (threshold < 0.85), Jurist Pairwise Preference (threshold > 0.5)
- Citation-independent retrieval: legal_area/branch match with NO shared cited_decisions

v9 CAVEAT ADDRESSED: Metric learning was pre-trained on full 1200 (including holdout).
v10 FIX: Train metric learning ONLY on 1000 train decisions. Evaluate on holdout.

Factory targets:
- LangDom < 0.6
- JuristPref > 0.7
- Citation-independent retrieval > 15%
"""

import json
import numpy as np
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
LEGAL_SIGNALS_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
CITATION_ROLES_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_id_resolution_bge/citation_roles_resolved.json")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v10/out_of_sample_metric_learning")
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
    'langdom_target': 0.6,
    'jurist_pref_target': 0.7,
    'citation_independent_recall_target': 0.15,
}

# Training config (matching v6)
BATCH_SIZE = 256
EPOCHS = 50
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
TEMPERATURE = 0.07
MAX_PAIRS = 100000

random.seed(FROZEN_SEED)
np.random.seed(FROZEN_SEED)
torch.manual_seed(FROZEN_SEED)

DEVICE = "cpu"
logger.info(f"Using device: {DEVICE}")


# ============================================================
# Metric Learning Models (from v6)
# ============================================================

class SimpleLinearHead(nn.Module):
    """Simple linear projection: 768 -> 128"""
    def __init__(self, input_dim: int = 768, output_dim: int = 128):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        return F.normalize(self.linear(x), dim=1, p=2)


class MetricLearningHead(nn.Module):
    """
    Learn a linear transformation on center_projected space.
    Mahalanobis: x^T M x where M = L^T L (low-rank)
    """
    def __init__(self, input_dim: int = 768, output_dim: int = 128, rank: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.rank = min(rank, input_dim, output_dim)
        self.L = nn.Parameter(torch.randn(self.rank, input_dim) * 0.01)
        self.projection = nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        x_metric = F.linear(x, self.L)
        x_out = self.projection(x)
        return F.normalize(x_out, dim=1, p=2)


# ============================================================
# Loss Functions (from v6)
# ============================================================

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


def structure_preservation_loss(projected, target):
    """Preserve the pairwise similarity structure of center_projected."""
    proj_norm = F.normalize(projected, dim=1, p=2)
    target_norm = F.normalize(target, dim=1, p=2)
    proj_sim = torch.mm(proj_norm, proj_norm.t())
    target_sim = torch.mm(target_norm, target_norm.t())
    return F.mse_loss(proj_sim, target_sim)


# ============================================================
# Data Loading
# ============================================================

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


def load_center_projected() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected embeddings and metadata."""
    embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected: {embeddings.shape}, {len(metadata)} decisions")
    return embeddings, metadata


def load_corpus() -> List[DecisionData]:
    """Load full corpus for pair creation."""
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
    logger.info(f"Loaded {len(corpus)} decisions from full corpus")
    return corpus


def assign_branch_from_legal_area(legal_area: str) -> str:
    """Map legal_area to high-level branch."""
    if not legal_area:
        return "unknown"
    la_lower = legal_area.lower()
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
            d['language'] = 'de'
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


# ============================================================
# Metric Learning Pair Creation (TRAIN ONLY)
# ============================================================

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


def create_metric_learning_pairs_train_only(
    corpus: List[DecisionData],
    train_indices: List[int],
    decisions: List[Dict],
    max_pairs: int = MAX_PAIRS
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Create pairs for metric learning using ONLY train decisions.
    Positive: Same branch, different language (multilingual invariance)
    Negative: Same language, different branch (language artifact)
    """
    logger.info("Creating metric learning pairs (TRAIN ONLY)...")
    
    # Build mapping from train_indices to local train indices
    id_to_local = {}
    for local_idx, global_idx in enumerate(train_indices):
        did = decisions[global_idx]['decision_id']
        id_to_local[did] = local_idx
    
    # Group train decisions by branch and language
    by_branch_lang = defaultdict(lambda: defaultdict(list))
    by_language = defaultdict(list)
    by_branch = defaultdict(list)
    
    for local_idx, global_idx in enumerate(train_indices):
        d = decisions[global_idx]
        branch = d.get('branch', 'unknown')
        lang = d.get('language', 'de')
        if branch and lang:
            by_branch_lang[branch][lang].append(local_idx)
            by_language[lang].append(local_idx)
            by_branch[branch].append(local_idx)
    
    positive_pairs = set()
    negative_pairs = set()
    
    # Positive: Same branch, different language
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
    
    logger.info(f"Generated {len(positive_pairs)} positive pairs")
    
    # Negative: Same language, different branch
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
                for idx1 in idxs1[:20]:
                    for idx2 in idxs2[:20]:
                        negative_pairs.add((idx1, idx2))
                        negative_pairs.add((idx2, idx1))
    
    logger.info(f"Generated {len(negative_pairs)} negative pairs")
    
    # Cap and balance
    target_per_class = max_pairs // 2
    positive_pairs = list(positive_pairs)[:target_per_class]
    negative_pairs = list(negative_pairs)[:target_per_class]
    
    logger.info(f"Using {len(positive_pairs)} positive, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs


class MetricDataset(Dataset):
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
        return self.embeddings[i], self.embeddings[j], torch.tensor(self.labels[idx], dtype=torch.float)


# ============================================================
# Adversarial Benchmarks (same as v8/v9)
# ============================================================

def adversarial_language_dominance(embeddings, metadata, k=20):
    """Adversarial test: measure language dominance in nearest neighbors."""
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
        'note': 'Lower is better - language should not dominate neighbors'
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
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
    }


def run_adversarial_benchmarks(embeddings, metadata):
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
    holdout_embeddings, holdout_metadata,
    train_embeddings, train_metadata,
    k=10
):
    """Test retrieval of legally related decisions WITHOUT shared citations."""
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


# ============================================================
# Evaluation
# ============================================================

def evaluate_representation(
    name, train_embeddings, holdout_embeddings,
    train_metadata, holdout_metadata
):
    """Full evaluation of a representation on train and holdout."""
    logger.info(f"\n=== Evaluating {name} ===")
    
    # Normalize train
    norms = np.linalg.norm(train_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    train_norm = train_embeddings / norms
    
    # Normalize holdout
    norms = np.linalg.norm(holdout_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    holdout_norm = holdout_embeddings / norms
    
    # Adversarial on TRAIN
    logger.info(f"  Adversarial on TRAIN ({len(train_metadata)} decisions)...")
    train_adv = run_adversarial_benchmarks(train_norm, train_metadata)
    
    # Adversarial on HOLDOUT
    logger.info(f"  Adversarial on HOLDOUT ({len(holdout_metadata)} decisions)...")
    holdout_adv = run_adversarial_benchmarks(holdout_norm, holdout_metadata)
    
    # Citation-independent retrieval (holdout -> train)
    logger.info(f"  Citation-independent retrieval (holdout->train)...")
    cite_indep = citation_independent_retrieval(
        holdout_norm, holdout_metadata,
        train_norm, train_metadata
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


# ============================================================
# Main: True Out-of-Sample Metric Learning Retrain
# ============================================================

def train_metric_learning_on_train_only(
    model_name, model, train_cp_embeddings, train_decisions,
    train_indices, decisions, ref_coarse_labels
):
    """
    Train metric learning model on TRAIN ONLY.
    Returns trained model and training log.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Training {model_name} on TRAIN ONLY ({len(train_cp_embeddings)} decisions)")
    logger.info(f"{'='*80}")
    
    # Create pairs from train only
    positive_pairs, negative_pairs = create_metric_learning_pairs_train_only(
        None, train_indices, decisions
    )
    dataset = MetricDataset(train_cp_embeddings, positive_pairs, negative_pairs)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    
    # Setup optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS * len(dataloader))
    
    model.to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Total params: {total_params:,}")
    
    # Loss weights
    LAMBDA_CONTRASTIVE = 1.0
    LAMBDA_PRESERVE = 2.0
    
    best_jurist = 0.0
    best_state = None
    training_log = []
    no_improve_count = 0
    patience = 8
    
    for epoch in range(EPOCHS):
        model.train()
        epoch_loss = 0.0
        num_batches = 0
        optimizer.zero_grad()
        
        for batch_idx, (emb_i, emb_j, labels) in enumerate(dataloader):
            emb_i = emb_i.to(DEVICE)
            emb_j = emb_j.to(DEVICE)
            labels = labels.to(DEVICE)
            
            z_i = model(emb_i)
            z_j = model(emb_j)
            
            loss_c = contrastive_loss(z_i, z_j, labels, TEMPERATURE)
            loss_p = structure_preservation_loss(z_i, emb_i) + structure_preservation_loss(z_j, emb_j)
            loss_p = loss_p / 2
            
            loss = LAMBDA_CONTRASTIVE * loss_c + LAMBDA_PRESERVE * loss_p
            loss.backward()
            
            epoch_loss += loss.item()
            num_batches += 1
            
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        avg_loss = epoch_loss / num_batches
        
        # Quick evaluation every 5 epochs
        if (epoch + 1) % 5 == 0 or epoch == EPOCHS - 1:
            model.eval()
            with torch.no_grad():
                projected = model(torch.from_numpy(train_cp_embeddings).float().to(DEVICE)).cpu().numpy()
            
            norms = np.linalg.norm(projected, axis=1, keepdims=True)
            norms[norms == 0] = 1
            projected_norm = projected / norms
            
            adv = run_adversarial_benchmarks(projected_norm, train_decisions)
            jp = adv['jurist_preference_rate']
            ld = adv['language_dominance_score']
            
            training_log.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'jurist_pref': jp,
                'lang_dom': ld,
                'both_pass': adv['both_pass'],
            })
            
            if adv['both_pass'] and jp > best_jurist:
                best_jurist = jp
                best_state = {
                    'epoch': epoch + 1,
                    'model_state': model.state_dict(),
                    'jurist_pref': jp,
                    'lang_dom': ld,
                }
                torch.save(best_state, OUTPUT_DIR / f"best_oos_{model_name}.pt")
                np.save(OUTPUT_DIR / f"best_oos_{model_name}_train_embeddings.npy", projected)
                logger.info(f"  >>> Epoch {epoch+1}: NEW BEST JP={jp:.4f}, LD={ld:.4f}")
                no_improve_count = 0
            else:
                no_improve_count += 1
            
            if epoch >= 10 and no_improve_count >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
    
    # Final evaluation with best model
    if best_state:
        model.load_state_dict(best_state['model_state'])
    
    model.eval()
    with torch.no_grad():
        train_projected = model(torch.from_numpy(train_cp_embeddings).float().to(DEVICE)).cpu().numpy()
    
    return model, train_projected, training_log, best_state


def main():
    logger.info("=" * 80)
    logger.info("LEGAL DISTANCE v10 - TRUE OUT-OF-SAMPLE METRIC LEARNING RETRAIN")
    logger.info("=" * 80)
    logger.info(f"Frozen Harness: v3 (seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH})")
    logger.info(f"Corpus: 1200 BGer decisions (2024 expanded slice)")
    logger.info(f"Split: 1000 train / 200 holdout (same as v6/v8/v9)")
    logger.info("CRITICAL: Metric learning TRAINED ONLY on 1000 train decisions")
    logger.info("v9 CAVEAT ADDRESSED: No pre-training on holdout data")
    logger.info("Zero-shot holdout baseline: JP ~0.53-0.59, CiteIndep ~13-14%")
    logger.info("v9 pre-trained holdout: JP ~0.52-0.61, CiteIndep ~34-37%")
    
    # Load data
    logger.info("\n1. Loading legal signals (1200 decisions)...")
    decisions = load_legal_signals()
    decisions = prepare_metadata(decisions)
    
    logger.info("\n2. Loading evaluation metadata (1000 decisions)...")
    eval_metadata = load_evaluation_metadata()
    
    logger.info("\n3. Splitting into train (1000) and holdout (200)...")
    train_decisions, holdout_decisions, train_indices, holdout_indices = split_train_holdout(decisions, eval_metadata)
    
    logger.info("\n4. Loading center_projected embeddings (768-dim)...")
    cp_embeddings, cp_metadata = load_center_projected()
    
    # Split center_projected embeddings by the same indices
    train_cp = cp_embeddings[train_indices]
    holdout_cp = cp_embeddings[holdout_indices]
    
    # Also load legal signals for holdout metadata
    holdout_legal_signals = [decisions[i] for i in holdout_indices]
    
    # Map cp_metadata to decisions for branch info
    cp_id_to_decision = {m['decision_id']: decisions[i] for i, m in enumerate(cp_metadata)}
    
    # Build train metadata from cp_metadata (aligned to train_cp)
    train_cp_metadata = []
    for i in train_indices:
        did = decisions[i]['decision_id']
        # Find in cp_metadata
        for m in cp_metadata:
            if m['decision_id'] == did:
                # Add branch from decisions
                m_with_branch = dict(m)
                m_with_branch['branch'] = decisions[i].get('branch', 'unknown')
                m_with_branch['language'] = decisions[i].get('language', 'de')
                m_with_branch['legal_area'] = decisions[i].get('legal_area', '')
                m_with_branch['cited_decisions'] = decisions[i].get('cited_decisions', [])
                train_cp_metadata.append(m_with_branch)
                break
    
    # Build holdout metadata
    holdout_cp_metadata = []
    for i in holdout_indices:
        did = decisions[i]['decision_id']
        for m in cp_metadata:
            if m['decision_id'] == did:
                m_with_branch = dict(m)
                m_with_branch['branch'] = decisions[i].get('branch', 'unknown')
                m_with_branch['language'] = decisions[i].get('language', 'de')
                m_with_branch['legal_area'] = decisions[i].get('legal_area', '')
                m_with_branch['cited_decisions'] = decisions[i].get('cited_decisions', [])
                holdout_cp_metadata.append(m_with_branch)
                break
    
    all_results = {}
    
    # ---- 1. Baseline: center_projected (no metric learning) ----
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE: center_projected (no metric learning, split only)")
    logger.info("=" * 80)
    all_results['center_projected_baseline'] = evaluate_representation(
        'center_projected_baseline', train_cp, holdout_cp,
        train_cp_metadata, holdout_cp_metadata
    )
    
    # ---- 2. Train Linear Projection (768 -> 128) on TRAIN ONLY ----
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING: linear_metric_oos (768->128, TRAIN ONLY)")
    logger.info("=" * 80)
    linear_model = SimpleLinearHead(input_dim=768, output_dim=128)
    linear_trained, linear_train_emb, linear_log, linear_best = train_metric_learning_on_train_only(
        'linear', linear_model, train_cp, train_cp_metadata,
        train_indices, decisions, None
    )
    
    # Evaluate linear on holdout
    with torch.no_grad():
        linear_holdout_emb = linear_trained(torch.from_numpy(holdout_cp).float().to(DEVICE)).cpu().numpy()
    
    np.save(OUTPUT_DIR / "best_oos_linear_holdout_embeddings.npy", linear_holdout_emb)
    
    all_results['linear_metric_oos'] = evaluate_representation(
        'linear_metric_oos', linear_train_emb, linear_holdout_emb,
        train_cp_metadata, holdout_cp_metadata
    )
    
    # ---- 3. Train Mahalanobis (768 -> 128, rank=64) on TRAIN ONLY ----
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING: mahalanobis_metric_oos (768->128 rank=64, TRAIN ONLY)")
    logger.info("=" * 80)
    mahal_model = MetricLearningHead(input_dim=768, output_dim=128, rank=64)
    mahal_trained, mahal_train_emb, mahal_log, mahal_best = train_metric_learning_on_train_only(
        'mahalanobis', mahal_model, train_cp, train_cp_metadata,
        train_indices, decisions, None
    )
    
    # Evaluate mahalanobis on holdout
    with torch.no_grad():
        mahal_holdout_emb = mahal_trained(torch.from_numpy(holdout_cp).float().to(DEVICE)).cpu().numpy()
    
    np.save(OUTPUT_DIR / "best_oos_mahalanobis_holdout_embeddings.npy", mahal_holdout_emb)
    
    all_results['mahalanobis_metric_oos'] = evaluate_representation(
        'mahalanobis_metric_oos', mahal_train_emb, mahal_holdout_emb,
        train_cp_metadata, holdout_cp_metadata
    )
    
    # ---- 4. Also evaluate v9 pre-trained models for comparison ----
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON: v9 pre-trained models (for reference)")
    logger.info("=" * 80)
    
    # Load v9 pre-trained embeddings
    LINEAR_V9_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy")
    MAHAL_V9_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy")
    
    if LINEAR_V9_PATH.exists():
        linear_v9 = np.load(LINEAR_V9_PATH)
        # Align to decisions
        cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
        linear_v9_aligned = np.zeros((len(decisions), linear_v9.shape[1]))
        for i, d in enumerate(decisions):
            if d['decision_id'] in cp_id_to_idx:
                linear_v9_aligned[i] = linear_v9[cp_id_to_idx[d['decision_id']]]
        
        train_linear_v9 = linear_v9_aligned[train_indices]
        holdout_linear_v9 = linear_v9_aligned[holdout_indices]
        
        all_results['linear_metric_v9_pretaind'] = evaluate_representation(
            'linear_metric_v9_pretaind', train_linear_v9, holdout_linear_v9,
            train_cp_metadata, holdout_cp_metadata
        )
    
    if MAHAL_V9_PATH.exists():
        mahal_v9 = np.load(MAHAL_V9_PATH)
        cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
        mahal_v9_aligned = np.zeros((len(decisions), mahal_v9.shape[1]))
        for i, d in enumerate(decisions):
            if d['decision_id'] in cp_id_to_idx:
                mahal_v9_aligned[i] = mahal_v9[cp_id_to_idx[d['decision_id']]]
        
        train_mahal_v9 = mahal_v9_aligned[train_indices]
        holdout_mahal_v9 = mahal_v9_aligned[holdout_indices]
        
        all_results['mahalanobis_metric_v9_pretaind'] = evaluate_representation(
            'mahalanobis_metric_v9_pretaind', train_mahal_v9, holdout_mahal_v9,
            train_cp_metadata, holdout_cp_metadata
        )
    
    # ---- Summary ----
    logger.info("\n" + "=" * 120)
    logger.info("OUT-OF-SAMPLE METRIC LEARNING SUMMARY")
    logger.info("=" * 120)
    
    logger.info(f"\n{'Representation':<40} {'Train LD':>8} {'Train JP':>8} {'Hold LD':>8} {'Hold JP':>8} {'ΔJP':>6} {'CiteIndep':>10} {'Status'}")
    logger.info("-" * 120)
    
    for name, res in all_results.items():
        train_ld = res['train_adversarial']['language_dominance_score']
        train_jp = res['train_adversarial']['jurist_preference_rate']
        holdout_ld = res['holdout_adversarial']['language_dominance_score']
        holdout_jp = res['holdout_adversarial']['jurist_preference_rate']
        
        jp_diff = holdout_jp - train_jp
        
        cite_indep = res['citation_independent_retrieval']
        cite_rate = cite_indep.get('citation_independent_retrieval_rate', 0)
        cite_status = cite_indep.get('status', 'N/A')
        
        train_pass = res['train_adversarial']['both_pass']
        holdout_pass = res['holdout_adversarial']['both_pass']
        cite_pass = cite_indep.get('status') == 'PASS'
        
        if train_pass and holdout_pass and cite_pass:
            overall = "FULL PASS"
        elif train_pass and holdout_pass:
            overall = "ADV PASS"
        elif holdout_pass:
            overall = "HOLDOUT PASS"
        else:
            overall = "FAIL"
        
        logger.info(f"{name:<40} {train_ld:>8.4f} {train_jp:>8.4f} {holdout_ld:>8.4f} {holdout_jp:>8.4f} {jp_diff:>+6.4f} {cite_rate:>10.4f} {overall}")
    
    # Factory target assessment
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
                logger.info(f"  PRODUCTION READY: All targets met on holdout + citation-independent retrieval")
            else:
                logger.info(f"  ROBUST: All adversarial targets met on holdout (cite-indep needs work)")
        elif holdout_both:
            logger.info(f"  PARTIAL: Passes adversarial gates but misses factory targets")
        else:
            logger.info(f"  FAILS: Does not pass adversarial gates on holdout")
    
    # Key comparison: OOS vs v9 pre-trained
    logger.info("\n" + "=" * 80)
    logger.info("KEY COMPARISON: OOS TRAINING vs v9 PRE-TRAINED")
    logger.info("=" * 80)
    
    if 'linear_metric_oos' in all_results and 'linear_metric_v9_pretaind' in all_results:
        oos = all_results['linear_metric_oos']
        v9 = all_results['linear_metric_v9_pretaind']
        oos_jp = oos['holdout_adversarial']['jurist_preference_rate']
        v9_jp = v9['holdout_adversarial']['jurist_preference_rate']
        oos_ld = oos['holdout_adversarial']['language_dominance_score']
        v9_ld = v9['holdout_adversarial']['language_dominance_score']
        oos_ci = oos['citation_independent_retrieval']['citation_independent_retrieval_rate']
        v9_ci = v9['citation_independent_retrieval']['citation_independent_retrieval_rate']
        
        logger.info(f"\nlinear_metric:")
        logger.info(f"  OOS (train-only):   JP={oos_jp:.4f}, LD={oos_ld:.4f}, CiteIndep={oos_ci:.4f}")
        logger.info(f"  v9 (pre-trained):   JP={v9_jp:.4f}, LD={v9_ld:.4f}, CiteIndep={v9_ci:.4f}")
        logger.info(f"  ΔJP: {oos_jp - v9_jp:+.4f}, ΔLD: {oos_ld - v9_ld:+.4f}, ΔCiteIndep: {oos_ci - v9_ci:+.4f}")
        
        if oos_jp > v9_jp:
            logger.info(f"  OOS TRAINING IMPROVES JuristPref by {oos_jp - v9_jp:+.4f}")
        else:
            logger.info(f"  v9 PRE-TRAINING has better JuristPref by {v9_jp - oos_jp:+.4f}")
    
    if 'mahalanobis_metric_oos' in all_results and 'mahalanobis_metric_v9_pretaind' in all_results:
        oos = all_results['mahalanobis_metric_oos']
        v9 = all_results['mahalanobis_metric_v9_pretaind']
        oos_jp = oos['holdout_adversarial']['jurist_preference_rate']
        v9_jp = v9['holdout_adversarial']['jurist_preference_rate']
        oos_ld = oos['holdout_adversarial']['language_dominance_score']
        v9_ld = v9['holdout_adversarial']['language_dominance_score']
        oos_ci = oos['citation_independent_retrieval']['citation_independent_retrieval_rate']
        v9_ci = v9['citation_independent_retrieval']['citation_independent_retrieval_rate']
        
        logger.info(f"\nmahalanobis_metric:")
        logger.info(f"  OOS (train-only):   JP={oos_jp:.4f}, LD={oos_ld:.4f}, CiteIndep={oos_ci:.4f}")
        logger.info(f"  v9 (pre-trained):   JP={v9_jp:.4f}, LD={v9_ld:.4f}, CiteIndep={v9_ci:.4f}")
        logger.info(f"  ΔJP: {oos_jp - v9_jp:+.4f}, ΔLD: {oos_ld - v9_ld:+.4f}, ΔCiteIndep: {oos_ci - v9_ci:+.4f}")
    
    # Save results
    output_path = OUTPUT_DIR / "out_of_sample_metric_learning_validation.json"
    with open(output_path, 'w') as f:
        json.dump(convert_for_json(all_results), f, indent=2)
    
    # Save training logs
    training_logs = {
        'linear': linear_log,
        'mahalanobis': mahal_log,
    }
    with open(OUTPUT_DIR / "training_logs.json", 'w') as f:
        json.dump(convert_for_json(training_logs), f, indent=2)
    
    logger.info(f"\nResults saved to: {output_path}")
    logger.info(f"Training logs saved to: {OUTPUT_DIR / 'training_logs.json'}")
    
    return all_results


if __name__ == "__main__":
    main()
