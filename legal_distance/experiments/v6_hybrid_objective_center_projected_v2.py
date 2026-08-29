#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Hybrid Objective on Center Projected (Variant 2)

Adjusted loss weights: lower preservation, higher contrastive to improve jurist preference
while still maintaining structure.
"""

import json
import numpy as np
import logging
import time
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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/hybrid_objective_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Training config - ADJUSTED WEIGHTS
SEED = 42
BATCH_SIZE = 128
EPOCHS = 30
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
TEMPERATURE = 0.07
GRAD_ACCUM_STEPS = 2
MAX_PAIRS = 100000

# LOSS WEIGHTS - Higher contrastive, lower preservation
LAMBDA_CONTRASTIVE = 2.0      # Increased to push jurist preference
LAMBDA_PRESERVE = 0.5         # Decreased to allow more adaptation
LAMBDA_HIERARCHY = 0.5        # Kept low

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = "cpu"
logger.info(f"Using device: {DEVICE}")


# ============================================================
# Projection Head Architecture
# ============================================================

class HybridProjectionHead(nn.Module):
    """Projection head: 768 -> 512 -> 256 -> 128 (normalized)"""
    
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


def create_contrastive_pairs(
    corpus: List[DecisionData], 
    center_projected_ids: List[str],
    max_pairs: int = MAX_PAIRS
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    logger.info("Creating contrastive pairs from legal structure...")
    
    id_to_corpus_idx = {d.decision_id: i for i, d in enumerate(corpus)}
    
    cp_to_corpus = {}
    for cp_idx, cp_id in enumerate(center_projected_ids):
        if cp_id in id_to_corpus_idx:
            cp_to_corpus[cp_idx] = id_to_corpus_idx[cp_id]
    
    by_branch_lang = defaultdict(lambda: defaultdict(list))
    by_language = defaultdict(list)
    
    for cp_idx, corpus_idx in cp_to_corpus.items():
        d = corpus[corpus_idx]
        if d.branch and d.language:
            by_branch_lang[d.branch][d.language].append(cp_idx)
            by_language[d.language].append(cp_idx)
    
    positive_pairs = set()
    negative_pairs = set()
    
    # Positive pairs: same branch, different language
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
    
    logger.info(f"Generated {len(positive_pairs)} positive pairs (same branch, diff language)")
    
    # Negative pairs: same language, different branch
    branch_to_indices = defaultdict(list)
    for branch, lang_dict in by_branch_lang.items():
        for lang, indices in lang_dict.items():
            branch_to_indices[branch].extend(indices)
    
    for lang, indices in by_language.items():
        lang_branch_indices = defaultdict(list)
        for idx in indices:
            for branch, b_indices in branch_to_indices.items():
                if idx in b_indices:
                    lang_branch_indices[branch].append(idx)
                    break
        
        branches = list(lang_branch_indices.keys())
        if len(branches) < 2:
            continue
            
        for i, branch1 in enumerate(branches):
            for branch2 in branches[i+1:]:
                idxs1 = lang_branch_indices[branch1]
                idxs2 = lang_branch_indices[branch2]
                for idx1 in idxs1[:20]:
                    for idx2 in idxs2[:20]:
                        negative_pairs.add((idx1, idx2))
                        negative_pairs.add((idx2, idx1))
    
    logger.info(f"Generated {len(negative_pairs)} negative pairs (same language, diff branch)")
    
    target_per_class = max_pairs // 2
    positive_pairs = list(positive_pairs)[:target_per_class]
    negative_pairs = list(negative_pairs)[:target_per_class]
    
    logger.info(f"Using {len(positive_pairs)} positive, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs


class HybridDataset(Dataset):
    def __init__(self, embeddings: np.ndarray, positive_pairs: List, negative_pairs: List, target_embeddings: np.ndarray):
        self.embeddings = torch.from_numpy(embeddings).float()
        self.target_embeddings = torch.from_numpy(target_embeddings).float()
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
        return (self.embeddings[i], self.embeddings[j], 
                self.target_embeddings[i], self.target_embeddings[j],
                torch.tensor(self.labels[idx], dtype=torch.float))


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


def preservation_loss(projected: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Cosine similarity preservation loss - preserves angular structure of center_projected."""
    proj_norm = F.normalize(projected, dim=1, p=2)
    target_norm = F.normalize(target, dim=1, p=2)
    
    proj_sim = torch.mm(proj_norm, proj_norm.t())
    target_sim = torch.mm(target_norm, target_norm.t())
    
    return F.mse_loss(proj_sim, target_sim)


def hierarchy_loss(projected: torch.Tensor, coarse_labels: torch.Tensor) -> torch.Tensor:
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
# Main Training Loop
# ============================================================

def main():
    logger.info("=" * 80)
    logger.info("Legal Distance v6 - Hybrid Objective on Center Projected (Variant 2)")
    logger.info(f"Loss = {LAMBDA_CONTRASTIVE}*L_contrastive + {LAMBDA_PRESERVE}*L_preserve + {LAMBDA_HIERARCHY}*L_hierarchy")
    logger.info("Target: Adversarial PASS + Meaningful Hierarchy (NO overclustering)")
    logger.info("=" * 80)
    
    logger.info("\n1. Loading center_projected embeddings and metadata...")
    cp_embeddings, cp_metadata = load_center_projected()
    center_projected_ids = [m['decision_id'] for m in cp_metadata]
    
    logger.info("\n2. Loading full corpus for pair creation...")
    corpus = load_corpus()
    
    logger.info("\n3. Using center_projected metadata for evaluation...")
    eval_metadata = cp_metadata
    
    logger.info("\n4. Creating contrastive pairs...")
    positive_pairs, negative_pairs = create_contrastive_pairs(corpus, center_projected_ids)
    
    logger.info("\n5. Computing reference coarse labels from center_projected...")
    ref_coarse_labels = get_reference_coarse_labels(cp_embeddings, eval_metadata)
    ref_coarse_labels_tensor = torch.from_numpy(ref_coarse_labels).long()
    
    dataset = HybridDataset(cp_embeddings, positive_pairs, negative_pairs, cp_embeddings)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    
    logger.info("\n6. Initializing hybrid projection head (768 -> 512 -> 256 -> 128)...")
    proj_head = HybridProjectionHead(input_dim=768, hidden_dims=[512, 256], output_dim=128).to(DEVICE)
    
    total_params = sum(p.numel() for p in proj_head.parameters())
    trainable_params = sum(p.numel() for p in proj_head.parameters() if p.requires_grad)
    logger.info(f"Total params: {total_params:,}, Trainable: {trainable_params:,}")
    
    optimizer = torch.optim.AdamW(proj_head.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS * len(dataloader))
    
    logger.info("\n7. Evaluating CENTER_PROJECTED baseline (no projection)...")
    baseline_results = evaluate_representation(cp_embeddings, eval_metadata, "center_projected (ref)")
    
    logger.info("\n8. Starting hybrid objective training...")
    best_valid = False
    best_jurist = 0.0
    best_state = None
    training_log = []
    
    for epoch in range(EPOCHS):
        proj_head.train()
        epoch_loss = 0.0
        epoch_loss_c = 0.0
        epoch_loss_p = 0.0
        epoch_loss_h = 0.0
        num_batches = 0
        optimizer.zero_grad()
        
        for batch_idx, (emb_i, emb_j, target_i, target_j, labels) in enumerate(dataloader):
            emb_i = emb_i.to(DEVICE)
            emb_j = emb_j.to(DEVICE)
            target_i = target_i.to(DEVICE)
            target_j = target_j.to(DEVICE)
            labels = labels.to(DEVICE)
            
            z_i = proj_head(emb_i)
            z_j = proj_head(emb_j)
            
            loss_c = contrastive_loss(z_i, z_j, labels, TEMPERATURE)
            loss_p = (preservation_loss(z_i, target_i) + preservation_loss(z_j, target_j)) / 2
            loss_h = torch.tensor(0.0, device=DEVICE)
            
            loss = (LAMBDA_CONTRASTIVE * loss_c + 
                    LAMBDA_PRESERVE * loss_p + 
                    LAMBDA_HIERARCHY * loss_h)
            loss = loss / GRAD_ACCUM_STEPS
            loss.backward()
            
            epoch_loss += loss.item() * GRAD_ACCUM_STEPS
            epoch_loss_c += loss_c.item()
            epoch_loss_p += loss_p.item()
            epoch_loss_h += loss_h.item()
            num_batches += 1
            
            if (batch_idx + 1) % GRAD_ACCUM_STEPS == 0:
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
        
        if num_batches % GRAD_ACCUM_STEPS != 0:
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        # Epoch-level hierarchy loss evaluation
        proj_head.eval()
        with torch.no_grad():
            projected_full = proj_head(torch.from_numpy(cp_embeddings).float().to(DEVICE)).cpu().numpy()
        h_loss = hierarchy_loss(torch.from_numpy(projected_full).float().to(DEVICE), ref_coarse_labels_tensor)
        epoch_loss_h = h_loss.item()
        
        avg_loss = epoch_loss / num_batches
        avg_loss_c = epoch_loss_c / num_batches
        avg_loss_p = epoch_loss_p / num_batches
        avg_loss_h = epoch_loss_h
        
        logger.info(f"  Epoch {epoch+1}/{EPOCHS} - Loss: {avg_loss:.4f} (C:{avg_loss_c:.4f} P:{avg_loss_p:.4f} H:{avg_loss_h:.4f})")
        
        if (epoch + 1) % 3 == 0 or epoch == EPOCHS - 1:
            proj_head.eval()
            with torch.no_grad():
                projected = proj_head(torch.from_numpy(cp_embeddings).float().to(DEVICE)).cpu().numpy()
            
            eval_results = evaluate_representation(projected, eval_metadata, f"hybrid_v2_epoch_{epoch+1}")
            
            training_log.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'loss_c': avg_loss_c,
                'loss_p': avg_loss_p,
                'loss_h': avg_loss_h,
                'eval': eval_results
            })
            
            if eval_results['valid_representation'] and eval_results['jurist_preference'] > best_jurist:
                best_jurist = eval_results['jurist_preference']
                best_valid = True
                best_state = {
                    'epoch': epoch + 1,
                    'model_state': proj_head.state_dict(),
                    'results': eval_results,
                }
                torch.save(best_state, OUTPUT_DIR / "best_projection_head.pt")
                np.save(OUTPUT_DIR / "best_embeddings.npy", projected)
                logger.info(f"  >>> NEW BEST VALID REPRESENTATION! JuristPref={best_jurist:.4f}, Coarse={eval_results['n_coarse']}")
    
    logger.info("\n9. Final evaluation...")
    proj_head.eval()
    with torch.no_grad():
        final_projected = proj_head(torch.from_numpy(cp_embeddings).float().to(DEVICE)).cpu().numpy()
    
    final_results = evaluate_representation(final_projected, eval_metadata, "hybrid_projection_final_v2")
    
    np.save(OUTPUT_DIR / "final_embeddings.npy", final_projected)
    torch.save(proj_head.state_dict(), OUTPUT_DIR / "final_projection_head.pt")
    
    logger.info("\n" + "=" * 100)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Model':<35} {'LangDom':>8} {'LD-Pass':>7} {'Jurist':>8} {'JP-Pass':>7} {'Both':>5} {'NMI':>6} {'Imp%':>6} {'C/F':>8} {'Valid':>5}")
    logger.info("-" * 100)
    
    all_results = {
        'center_projected_baseline': baseline_results,
        'final_projection': final_results,
        'training_log': training_log,
    }
    
    if best_state:
        all_results['best_projection'] = best_state['results']
    
    for key, res in all_results.items():
        if key == 'training_log':
            continue
        ld = res['language_dominance']
        jp = res['jurist_preference']
        ld_pass = "✅" if ld < 0.85 else "❌"
        jp_pass = "✅" if jp > 0.5 else "❌"
        both = "✅" if res['adversarial_both_pass'] else "❌"
        valid = "✅" if res['valid_representation'] else "❌"
        c_f = f"{res['n_coarse']}/{res['n_fine']}"
        logger.info(f"{key:<35} {ld:>8.4f} {ld_pass:>7} {jp:>8.4f} {jp_pass:>7} {both:>5} {res['legal_area_nmi']:>6.4f} {res['improvement_rate']:>5.1%} {c_f:>8} {valid:>5}")
    
    with open(OUTPUT_DIR / "training_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info("\n=== Training Complete ===")
    return all_results


if __name__ == "__main__":
    main()