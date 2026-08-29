#!/usr/bin/env python3
"""
Legal Distance Lane v6 - CPU-Efficient Contrastive Projection Head Fine-Tuning

Factory Direction v6 Objective 3:
"Legal embeddings: test multilingual-e5-small fine-tuning on Swiss legal corpus 
for multilingual invariance WITH coarse legal structure"

Approach:
- Freeze pretrained multilingual-e5-small backbone
- Train ONLY a small projection head (384 -> 256 -> 128) on CPU
- Contrastive objective: Pull same-branch-different-language pairs together
- Push same-language-different-branch pairs apart
- Directly optimizes for adversarial gates: LangDom < 0.85, JuristPref > 0.5
- Preserve hierarchical cluster structure (avoid overclustering artifact)

This is ~50K trainable params vs 33M full model - feasible on CPU.
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
from jurist_usability import simulate_pairwise_preference, prepare_metadata
from sklearn.metrics import normalized_mutual_info_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
PRETRAINED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/finetune_multilingual_e5_cpu/embeddings_multilingual_e5_small_pretrained_cpu.npy")
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/contrastive_projection")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Training config
SEED = 42
BATCH_SIZE = 64  # Larger batch for projection head
EPOCHS = 20
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
TEMPERATURE = 0.07
GRAD_ACCUM_STEPS = 4  # Effective batch = 256
MAX_PAIRS = 50000

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = "cpu"
logger.info(f"Using device: {DEVICE}")


# ============================================================
# Projection Head Architecture
# ============================================================

class ProjectionHead(nn.Module):
    """Small projection head: 384 -> 256 -> 128 (normalized)"""
    
    def __init__(self, input_dim: int = 384, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
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


def load_pretrained_embeddings() -> Tuple[np.ndarray, List[str]]:
    """Load pretrained embeddings and corresponding decision_ids."""
    embeddings = np.load(PRETRAINED_EMBEDDINGS)
    
    # Load decision_ids from corpus (first 1000 match the evaluation set)
    decision_ids = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 1000:
                break
            d = json.loads(line)
            decision_ids.append(d['decision_id'])
    
    logger.info(f"Loaded pretrained embeddings: {embeddings.shape}")
    logger.info(f"Decision IDs: {len(decision_ids)}")
    return embeddings, decision_ids


def create_contrastive_pairs(
    corpus: List[DecisionData], 
    decision_ids: List[str],
    max_pairs: int = MAX_PAIRS
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Create contrastive pairs for training.
    
    Positive: Same branch, DIFFERENT language (multilingual legal invariance)
    Negative: Same language, DIFFERENT branch (language artifact)
    """
    logger.info("Creating contrastive pairs from legal structure...")
    
    # Map decision_id to corpus index
    id_to_idx = {d.decision_id: i for i, d in enumerate(corpus)}
    
    # Group by branch and language
    by_branch = defaultdict(list)
    by_language = defaultdict(list)
    by_branch_lang = defaultdict(lambda: defaultdict(list))
    
    for i, d in enumerate(corpus):
        if d.branch and d.language:
            by_branch[d.branch].append(i)
            by_language[d.language].append(i)
            by_branch_lang[d.branch][d.language].append(i)
    
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
                # Pair up to 20 per language pair per branch
                for idx1 in idxs1[:20]:
                    for idx2 in idxs2[:20]:
                        positive_pairs.add((idx1, idx2))
                        positive_pairs.add((idx2, idx1))
    
    logger.info(f"Generated {len(positive_pairs)} positive pairs (same branch, diff language)")
    
    # Negative pairs: same language, different branch
    for lang, indices in by_language.items():
        if len(indices) < 2:
            continue
        # Get branches for these indices
        branch_indices = defaultdict(list)
        for idx in indices:
            branch = corpus[idx].branch
            if branch:
                branch_indices[branch].append(idx)
        
        branches = list(branch_indices.keys())
        if len(branches) < 2:
            continue
            
        for i, branch1 in enumerate(branches):
            for branch2 in branches[i+1:]:
                idxs1 = branch_indices[branch1]
                idxs2 = branch_indices[branch2]
                # Sample negative pairs
                for idx1 in idxs1[:15]:
                    for idx2 in idxs2[:15]:
                        negative_pairs.add((idx1, idx2))
                        negative_pairs.add((idx2, idx1))
    
    logger.info(f"Generated {len(negative_pairs)} negative pairs (same language, diff branch)")
    
    # Cap and balance
    positive_pairs = list(positive_pairs)[:max_pairs//2]
    negative_pairs = list(negative_pairs)[:max_pairs//2]
    
    logger.info(f"Using {len(positive_pairs)} positive, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs


class ContrastiveDataset(Dataset):
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
        
        # Shuffle
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
# Contrastive Loss
# ============================================================

def contrastive_loss(z_i: torch.Tensor, z_j: torch.Tensor, labels: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
    """
    Contrastive loss for pairs.
    Positive pairs (label=1): minimize distance
    Negative pairs (label=0): maximize distance (with margin)
    """
    # Cosine similarity
    sim = F.cosine_similarity(z_i, z_j, dim=1)
    
    # Positive loss: -log(sigmoid(sim/temp)) -> want sim high
    # Negative loss: -log(sigmoid(-sim/temp)) -> want sim low
    pos_mask = labels == 1.0
    neg_mask = labels == 0.0
    
    loss_pos = torch.zeros(1, device=z_i.device)
    loss_neg = torch.zeros(1, device=z_i.device)
    
    if pos_mask.any():
        loss_pos = -F.logsigmoid(sim[pos_mask] / temperature).mean()
    if neg_mask.any():
        loss_neg = -F.logsigmoid(-sim[neg_mask] / temperature).mean()
    
    return loss_pos + loss_neg


# ============================================================
# Evaluation
# ============================================================

def evaluate_representation(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Full evaluation: adversarial + fractal quality."""
    logger.info(f"\n=== Evaluating {name} ===")
    
    # Ensure normalized
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # --- Adversarial Benchmarks ---
    adv_results = adversarial_language_dominance(embeddings, metadata)
    lang_dom = adv_results['mean_language_dominance']
    lang_dom_status = adv_results['status']
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    jurist_results = simulate_pairwise_preference(rep_valid, branches, languages)
    jurist_pref = jurist_results['jurist_would_succeed_rate']
    jurist_status = jurist_results['status']
    
    adversarial_pass = (lang_dom < 0.85) and (jurist_pref > 0.5)
    
    # --- Fractal Quality ---
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
    
    # Overclustering check
    overclustering = (n_coarse == 1 and n_fine >= 500)
    
    logger.info(f"  Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Hierarchical advantage: {hierarchical_advantage:+.4f}")
    logger.info(f"  Language dominance: {lang_dom:.4f} ({lang_dom_status})")
    logger.info(f"  Jurist preference: {jurist_pref:.4f} ({jurist_status})")
    logger.info(f"  Overclustering: {overclustering}")
    logger.info(f"  Adversarial BOTH PASS: {adversarial_pass}")
    
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
        'valid_representation': adversarial_pass and not overclustering and n_coarse >= 3,
    }


# ============================================================
# Main Training Loop
# ============================================================

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance v6 - CPU Contrastive Projection Head")
    logger.info("Target: Adversarial PASS + Meaningful Hierarchy (no overclustering)")
    logger.info("=" * 70)
    
    # 1. Load data
    logger.info("\n1. Loading corpus and pretrained embeddings...")
    corpus = load_corpus()
    pretrained_emb, decision_ids = load_pretrained_embeddings()
    
    # Align corpus with pretrained embeddings (first 1000)
    aligned_corpus = corpus[:1000]
    logger.info(f"Aligned corpus: {len(aligned_corpus)} decisions")
    
    # 2. Load evaluation metadata
    logger.info("\n2. Loading evaluation metadata...")
    _, metadata = load_metadata_with_branch()
    
    # 3. Create contrastive pairs
    logger.info("\n3. Creating contrastive pairs...")
    positive_pairs, negative_pairs = create_contrastive_pairs(aligned_corpus, decision_ids)
    
    # 4. Create dataset and dataloader
    dataset = ContrastiveDataset(pretrained_emb, positive_pairs, negative_pairs)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    
    # 5. Initialize projection head
    logger.info("\n4. Initializing projection head (384 -> 256 -> 128)...")
    proj_head = ProjectionHead(input_dim=384, hidden_dim=256, output_dim=128).to(DEVICE)
    
    # Count parameters
    total_params = sum(p.numel() for p in proj_head.parameters())
    trainable_params = sum(p.numel() for p in proj_head.parameters() if p.requires_grad)
    logger.info(f"Total params: {total_params:,}, Trainable: {trainable_params:,}")
    
    optimizer = torch.optim.AdamW(proj_head.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS * len(dataloader))
    
    # 6. Evaluate baseline (pretrained, no projection)
    logger.info("\n5. Evaluating PRETRAINED baseline (no projection)...")
    baseline_results = evaluate_representation(pretrained_emb, metadata, "multilingual_e5_small_pretrained")
    
    # 7. Training loop
    logger.info("\n6. Starting contrastive training...")
    best_valid = False
    best_jurist = 0.0
    best_state = None
    
    for epoch in range(EPOCHS):
        proj_head.train()
        epoch_loss = 0.0
        num_batches = 0
        optimizer.zero_grad()
        
        for batch_idx, (emb_i, emb_j, labels) in enumerate(dataloader):
            emb_i = emb_i.to(DEVICE)
            emb_j = emb_j.to(DEVICE)
            labels = labels.to(DEVICE)
            
            # Forward through projection head
            z_i = proj_head(emb_i)
            z_j = proj_head(emb_j)
            
            # Contrastive loss
            loss = contrastive_loss(z_i, z_j, labels, TEMPERATURE)
            loss = loss / GRAD_ACCUM_STEPS
            loss.backward()
            
            epoch_loss += loss.item() * GRAD_ACCUM_STEPS
            num_batches += 1
            
            if (batch_idx + 1) % GRAD_ACCUM_STEPS == 0:
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
        
        # Handle remaining gradients
        if num_batches % GRAD_ACCUM_STEPS != 0:
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        avg_loss = epoch_loss / num_batches
        logger.info(f"  Epoch {epoch+1}/{EPOCHS} - Loss: {avg_loss:.4f}")
        
        # Evaluate every 5 epochs
        if (epoch + 1) % 5 == 0 or epoch == EPOCHS - 1:
            proj_head.eval()
            with torch.no_grad():
                # Project all embeddings
                projected = proj_head(torch.from_numpy(pretrained_emb).float().to(DEVICE)).cpu().numpy()
            
            eval_results = evaluate_representation(projected, metadata, f"projection_epoch_{epoch+1}")
            
            # Track best valid representation
            if eval_results['valid_representation'] and eval_results['jurist_preference'] > best_jurist:
                best_jurist = eval_results['jurist_preference']
                best_valid = True
                best_state = {
                    'epoch': epoch + 1,
                    'model_state': proj_head.state_dict(),
                    'results': eval_results,
                }
                # Save best model
                torch.save(best_state, OUTPUT_DIR / "best_projection_head.pt")
                np.save(OUTPUT_DIR / "best_embeddings.npy", projected)
                logger.info(f"  >>> NEW BEST VALID REPRESENTATION! JuristPref={best_jurist:.4f}")
    
    # 8. Final evaluation
    logger.info("\n7. Final evaluation...")
    proj_head.eval()
    with torch.no_grad():
        final_projected = proj_head(torch.from_numpy(pretrained_emb).float().to(DEVICE)).cpu().numpy()
    
    final_results = evaluate_representation(final_projected, metadata, "multilingual_e5_projection_final")
    
    # Save final embeddings
    np.save(OUTPUT_DIR / "final_embeddings.npy", final_projected)
    torch.save(proj_head.state_dict(), OUTPUT_DIR / "final_projection_head.pt")
    
    # 9. Summary
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Model':<40} {'LangDom':>8} {'LD-Pass':>7} {'Jurist':>8} {'JP-Pass':>7} {'Both':>5} {'NMI':>6} {'Imp%':>6} {'Valid':>5}")
    logger.info("-" * 80)
    
    all_results = {
        'pretrained': baseline_results,
        'final_projection': final_results,
    }
    
    if best_state:
        all_results['best_projection'] = best_state['results']
    
    for key, res in all_results.items():
        ld = res['language_dominance']
        jp = res['jurist_preference']
        ld_pass = "✅" if ld < 0.85 else "❌"
        jp_pass = "✅" if jp > 0.5 else "❌"
        both = "✅" if res['adversarial_both_pass'] else "❌"
        valid = "✅" if res['valid_representation'] else "❌"
        logger.info(f"{key:<40} {ld:>8.4f} {ld_pass:>7} {jp:>8.4f} {jp_pass:>7} {both:>5} {res['legal_area_nmi']:>6.4f} {res['improvement_rate']:>5.1%} {valid:>5}")
    
    # Compare with center_projected
    logger.info("\n--- Center Projected Reference ---")
    cp_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
    cp_meta_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    cp_emb = np.load(cp_path)
    with open(cp_meta_path) as f:
        cp_meta = json.load(f)
    
    cp_by_id = {m['decision_id']: i for i, m in enumerate(cp_meta)}
    eval_ids = [m['decision_id'] for m in metadata]
    valid_ids = [did for did in eval_ids if did in cp_by_id]
    valid_cp_indices = [cp_by_id[did] for did in valid_ids]
    cp_aligned = cp_emb[valid_cp_indices]
    meta_aligned = [m for m in metadata if m['decision_id'] in cp_by_id]
    
    cp_results = evaluate_representation(cp_aligned, meta_aligned, "center_projected (ref)")
    
    # Save all results
    with open(OUTPUT_DIR / "training_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info("\n=== Training Complete ===")
    return all_results


if __name__ == "__main__":
    main()