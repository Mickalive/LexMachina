#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Metric Learning on Center Projected Space

Factory Direction v6: "Metric learning on center_projected space as lower-risk alternative"
- Train a Mahalanobis metric / linear projection on top of center_projected
- Objective: Improve JuristPref while constraining LangDom < 0.85 and n_coarse >= 3
- Lower risk: Starting from valid structure, not destroying it
"""

import json
import numpy as np
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')

from hierarchical_zoom_validation import load_metadata_with_branch, hierarchical_leiden, compute_branch_purity, compute_branch_purity_per_cluster, leiden_clustering
from cross_language_benchmarks import adversarial_language_dominance
from jurist_usability import simulate_pairwise_preference
from sklearn.metrics import normalized_mutual_info_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Training config
SEED = 42
BATCH_SIZE = 256
EPOCHS = 50
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
TEMPERATURE = 0.07
MAX_PAIRS = 100000

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = "cpu"
logger.info(f"Using device: {DEVICE}")


# ============================================================
# Metric Learning Model: Linear Transformation + Mahalanobis
# ============================================================

class MetricLearningHead(nn.Module):
    """
    Learn a linear transformation on center_projected space.
    Two variants:
    1. Linear projection: W @ x (768 -> 128)
    2. Mahalanobis: x^T M x where M = L^T L (low-rank)
    """
    
    def __init__(self, input_dim: int = 768, output_dim: int = 128, rank: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.rank = min(rank, input_dim, output_dim)
        
        # Low-rank factorization: M = L^T L where L is (rank, input_dim)
        # This gives us a Mahalanobis metric in the projected space
        self.L = nn.Parameter(torch.randn(self.rank, input_dim) * 0.01)
        # Optional linear projection after metric
        self.projection = nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        # Apply Mahalanobis transformation: x -> L x (maps to rank-dim space)
        # Then project to output_dim
        x_metric = F.linear(x, self.L)  # (batch, rank)
        x_out = self.projection(x)  # (batch, output_dim)
        # Combine: use metric-transformed features
        return F.normalize(x_out, dim=1, p=2)


class SimpleLinearHead(nn.Module):
    """Simple linear projection: 768 -> 128"""
    def __init__(self, input_dim: int = 768, output_dim: int = 128):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        return F.normalize(self.linear(x), dim=1, p=2)


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


def load_center_projected() -> Tuple[np.ndarray, List[Dict]]:
    embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected: {embeddings.shape}, {len(metadata)} decisions")
    return embeddings, metadata


def load_corpus() -> List[DecisionData]:
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


def prepare_metadata_from_cp(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
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
    
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


def create_metric_learning_pairs(
    corpus: List[DecisionData], 
    center_projected_ids: List[str],
    max_pairs: int = MAX_PAIRS
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Create pairs for metric learning:
    - Positive: Same legal concept, different language (multilingual invariance)
    - Negative: Same language, different legal concept (language artifact)
    """
    logger.info("Creating metric learning pairs...")
    
    id_to_corpus_idx = {d.decision_id: i for i, d in enumerate(corpus)}
    
    cp_to_corpus = {}
    for cp_idx, cp_id in enumerate(center_projected_ids):
        if cp_id in id_to_corpus_idx:
            cp_to_corpus[cp_idx] = id_to_corpus_idx[cp_id]
    
    # Group by legal dimensions
    by_branch_lang = defaultdict(lambda: defaultdict(list))
    by_legal_area_lang = defaultdict(lambda: defaultdict(list))
    by_language = defaultdict(list)
    by_branch = defaultdict(list)
    by_legal_area = defaultdict(list)
    
    for cp_idx, corpus_idx in cp_to_corpus.items():
        d = corpus[corpus_idx]
        if not (d.branch and d.language):
            continue
            
        by_branch_lang[d.branch][d.language].append(cp_idx)
        by_language[d.language].append(cp_idx)
        by_branch[d.branch].append(cp_idx)
        
        if d.legal_area:
            by_legal_area_lang[d.legal_area][d.language].append(cp_idx)
            by_legal_area[d.legal_area].append(cp_idx)
    
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
    
    # Positive: Same legal_area, different language (finer)
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
    
    # Negative: Same language, different legal_area
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
                for idx1 in idxs1[:15]:
                    for idx2 in idxs2[:15]:
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
    def __init__(self, embeddings: np.ndarray, positive_pairs: List, negative_pairs: List):
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
        
        logger.info(f"Dataset size: {len(self.pairs)} pairs")
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        i, j = self.pairs[idx]
        return self.embeddings[i], self.embeddings[j], torch.tensor(self.labels[idx], dtype=torch.float)


# ============================================================
# Loss Functions
# ============================================================

def contrastive_loss(z_i: torch.Tensor, z_j: torch.Tensor, labels: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
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


def structure_preservation_loss(projected: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Preserve the pairwise similarity structure of center_projected."""
    proj_norm = F.normalize(projected, dim=1, p=2)
    target_norm = F.normalize(target, dim=1, p=2)
    
    proj_sim = torch.mm(proj_norm, proj_norm.t())
    target_sim = torch.mm(target_norm, target_norm.t())
    
    return F.mse_loss(proj_sim, target_sim)


def hierarchy_cohesion_loss(projected: torch.Tensor, coarse_labels: torch.Tensor) -> torch.Tensor:
    """Minimize within-coarse-cluster variance."""
    unique_clusters = coarse_labels.unique()
    total_loss = torch.tensor(0.0, device=projected.device)
    count = 0
    
    for cluster_id in unique_clusters:
        mask = coarse_labels == cluster_id
        if mask.sum() < 2:
            continue
        cluster_embeds = projected[mask]
        n = min(len(cluster_embeds), 30)
        indices = torch.randperm(len(cluster_embeds))[:n]
        sampled = cluster_embeds[indices]
        
        center = sampled.mean(dim=0, keepdim=True)
        loss = F.mse_loss(sampled, center.expand_as(sampled))
        total_loss += loss
        count += 1
    
    return total_loss / max(count, 1)


# ============================================================
# Evaluation
# ============================================================

def evaluate_representation(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    logger.info(f"\n=== Evaluating {name} ===")
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    adv_results = adversarial_language_dominance(embeddings, metadata)
    lang_dom = adv_results['mean_language_dominance']
    lang_dom_status = adv_results['status']
    
    branches, languages, chambers, valid_indices = prepare_metadata_from_cp(metadata)
    rep_valid = embeddings[valid_indices]
    jurist_results = simulate_pairwise_preference(rep_valid, branches, languages)
    jurist_pref = jurist_results['jurist_would_succeed_rate']
    jurist_status = jurist_results['status']
    
    adversarial_pass = (lang_dom < 0.85) and (jurist_pref > 0.5)
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
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
    
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    flat_labels, _ = leiden_clustering(embeddings, resolution=3.0)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    hierarchical_advantage = fine_overall - flat_purity
    
    overclustering = (n_coarse == 1 and n_fine >= 500)
    valid_representation = adversarial_pass and not overclustering and n_coarse >= 3
    
    logger.info(f"  Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Hierarchical advantage: {hierarchical_advantage:+.4f}")
    logger.info(f"  Language dominance: {lang_dom:.4f} ({lang_dom_status})")
    logger.info(f"  Jurist preference: {jurist_pref:.4f} ({jurist_status})")
    logger.info(f"  Overclustering: {overclustering}")
    logger.info(f"  Adversarial BOTH PASS: {adversarial_pass}")
    logger.info(f"  Valid representation: {valid_representation}")
    
    return {
        'name': name,
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(hierarchical_advantage),
        'language_dominance': float(lang_dom),
        'language_dominance_status': lang_dom_status,
        'jurist_preference': float(jurist_pref),
        'jurist_status': jurist_status,
        'adversarial_both_pass': adversarial_pass,
        'overclustering': overclustering,
        'valid_representation': valid_representation,
    }


def get_reference_coarse_labels(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    hierarchical_labels, coarse_labels, _, _ = hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0
    )
    return coarse_labels


# ============================================================
# Main Training
# ============================================================

def train_metric_learning(model_name: str, model: nn.Module, cp_embeddings: np.ndarray, 
                         eval_metadata: List[Dict], corpus: List[DecisionData], 
                         center_projected_ids: List[str], ref_coarse_labels: np.ndarray):
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Training {model_name}")
    logger.info(f"{'='*80}")
    
    # Create pairs
    positive_pairs, negative_pairs = create_metric_learning_pairs(corpus, center_projected_ids)
    dataset = MetricDataset(cp_embeddings, positive_pairs, negative_pairs)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    
    # Setup optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS * len(dataloader))
    
    # Reference coarse labels tensor
    ref_coarse_tensor = torch.from_numpy(ref_coarse_labels).long().to(DEVICE)
    
    # Baseline evaluation
    baseline_results = evaluate_representation(cp_embeddings, eval_metadata, "center_projected (ref)")
    
    model.to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Total params: {total_params:,}, Trainable: {trainable_params:,}")
    
    # Loss weights - conservative to preserve structure
    LAMBDA_CONTRASTIVE = 1.0
    LAMBDA_PRESERVE = 2.0  # High preservation
    LAMBDA_HIERARCHY = 0.5
    
    best_valid = False
    best_jurist = 0.0
    best_state = None
    training_log = []
    
    patience = 8
    no_improve_count = 0
    best_epoch = 0
    
    for epoch in range(EPOCHS):
        model.train()
        epoch_loss = 0.0
        epoch_loss_c = 0.0
        epoch_loss_p = 0.0
        epoch_loss_h = 0.0
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
            
            loss = (LAMBDA_CONTRASTIVE * loss_c + 
                    LAMBDA_PRESERVE * loss_p)
            loss.backward()
            
            epoch_loss += loss.item()
            epoch_loss_c += loss_c.item()
            epoch_loss_p += loss_p.item()
            num_batches += 1
            
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        avg_loss = epoch_loss / num_batches
        avg_loss_c = epoch_loss_c / num_batches
        avg_loss_p = epoch_loss_p / num_batches
        
        logger.info(f"  Epoch {epoch+1}/{EPOCHS} - Loss: {avg_loss:.4f} (C:{avg_loss_c:.4f} P:{avg_loss_p:.4f})")
        
        # Evaluate every 2 epochs for first 20, then every 5
        eval_freq = 2 if epoch < 20 else 5
        if (epoch + 1) % eval_freq == 0 or epoch == EPOCHS - 1:
            model.eval()
            with torch.no_grad():
                projected = model(torch.from_numpy(cp_embeddings).float().to(DEVICE)).cpu().numpy()
            
            eval_results = evaluate_representation(projected, eval_metadata, f"{model_name}_epoch_{epoch+1}")
            
            training_log.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'loss_c': avg_loss_c,
                'loss_p': avg_loss_p,
                'eval': eval_results
            })
            
            if eval_results['valid_representation'] and eval_results['jurist_preference'] > best_jurist:
                best_jurist = eval_results['jurist_preference']
                best_valid = True
                best_state = {
                    'epoch': epoch + 1,
                    'model_state': model.state_dict(),
                    'results': eval_results,
                }
                torch.save(best_state, OUTPUT_DIR / f"best_{model_name}.pt")
                np.save(OUTPUT_DIR / f"best_{model_name}_embeddings.npy", projected)
                logger.info(f"  >>> NEW BEST VALID REPRESENTATION! JuristPref={best_jurist:.4f}, Coarse={eval_results['n_coarse']}")
                best_epoch = epoch + 1
                no_improve_count = 0
            elif eval_results['valid_representation']:
                no_improve_count += 1
            else:
                no_improve_count += 1
            
            # Early stopping
            if epoch >= 10 and no_improve_count >= patience:
                logger.info(f"Early stopping at epoch {epoch+1} (no improvement for {patience} epochs)")
                break
    
    # Final evaluation with best model
    if best_state:
        model.load_state_dict(best_state['model_state'])
    
    model.eval()
    with torch.no_grad():
        final_projected = model(torch.from_numpy(cp_embeddings).float().to(DEVICE)).cpu().numpy()
    
    final_results = evaluate_representation(final_projected, eval_metadata, f"{model_name}_final")
    
    np.save(OUTPUT_DIR / f"final_{model_name}_embeddings.npy", final_projected)
    torch.save(model.state_dict(), OUTPUT_DIR / f"final_{model_name}.pt")
    
    return {
        'model_name': model_name,
        'baseline': baseline_results,
        'final': final_results,
        'best': best_state['results'] if best_state else None,
        'best_epoch': best_epoch,
        'training_log': training_log,
    }


def main():
    logger.info("=" * 80)
    logger.info("Legal Distance v6 - Metric Learning on Center Projected Space")
    logger.info("Lower-risk alternative: Learn metric on top of valid structure")
    logger.info("=" * 80)
    
    logger.info("\n1. Loading center_projected embeddings and metadata...")
    cp_embeddings, cp_metadata = load_center_projected()
    center_projected_ids = [m['decision_id'] for m in cp_metadata]
    
    logger.info("\n2. Loading full corpus for pair creation...")
    corpus = load_corpus()
    
    logger.info("\n3. Using center_projected metadata for evaluation...")
    eval_metadata = cp_metadata
    
    logger.info("\n4. Computing reference coarse labels from center_projected...")
    ref_coarse_labels = get_reference_coarse_labels(cp_embeddings, eval_metadata)
    
    # Train two variants
    results = {}
    
    # Variant 1: Simple Linear Projection (768 -> 128)
    logger.info("\n\n>>> VARIANT 1: Simple Linear Projection <<<")
    linear_model = SimpleLinearHead(input_dim=768, output_dim=128)
    results['linear'] = train_metric_learning(
        'linear', linear_model, cp_embeddings, eval_metadata, corpus, 
        center_projected_ids, ref_coarse_labels
    )
    
    # Variant 2: Mahalanobis Metric Learning (low-rank)
    logger.info("\n\n>>> VARIANT 2: Mahalanobis Metric Learning <<<")
    mahalanobis_model = MetricLearningHead(input_dim=768, output_dim=128, rank=64)
    results['mahalanobis'] = train_metric_learning(
        'mahalanobis', mahalanobis_model, cp_embeddings, eval_metadata, corpus, 
        center_projected_ids, ref_coarse_labels
    )
    
    # Summary
    logger.info("\n" + "=" * 100)
    logger.info("METRIC LEARNING SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Model':<30} {'LangDom':>8} {'LD-Pass':>7} {'Jurist':>8} {'JP-Pass':>7} {'Both':>5} {'NMI':>6} {'Imp%':>6} {'C/F':>8} {'Valid':>5}")
    logger.info("-" * 100)
    
    for variant, res in results.items():
        for key in ['baseline', 'final', 'best']:
            if key in res and res[key]:
                r = res[key]
                ld = r['language_dominance']
                jp = r['jurist_preference']
                ld_pass = "✅" if ld < 0.85 else "❌"
                jp_pass = "✅" if jp > 0.5 else "❌"
                both = "✅" if r['adversarial_both_pass'] else "❌"
                valid = "✅" if r['valid_representation'] else "❌"
                c_f = f"{r['n_coarse']}/{r['n_fine']}"
                logger.info(f"{variant}_{key:<25} {ld:>8.4f} {ld_pass:>7} {jp:>8.4f} {jp_pass:>7} {both:>5} {r['legal_area_nmi']:>6.4f} {r['improvement_rate']:>5.1%} {c_f:>8} {valid:>5}")
    
    # Save all results
    with open(OUTPUT_DIR / "metric_learning_results.json", 'w') as f:
        # Convert numpy types to JSON-serializable
        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj
        json.dump(convert(results), f, indent=2)
    
    logger.info("\n=== Metric Learning Complete ===")
    return results


if __name__ == "__main__":
    main()