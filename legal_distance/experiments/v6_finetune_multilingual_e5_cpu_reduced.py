#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Fine-tune multilingual-e5-small on Swiss Legal Corpus
REDUCED CPU VERSION - Minimal run to get signal on fine-tuning viability
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
from torch.utils.data import Dataset, DataLoader
from torch.nn import functional as F
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer, losses, InputExample
from sklearn.metrics import normalized_mutual_info_score
from sklearn.metrics.pairwise import cosine_similarity

import sys
# Fix the path for cross_language_benchmarks import (it has hardcoded wrong path)
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')

from hierarchical_leiden import load_metadata_with_branch, leiden_clustering, compute_branch_purity
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster
from cross_language_benchmarks import adversarial_language_dominance
from jurist_usability import simulate_pairwise_preference, prepare_metadata

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/finetune_multilingual_e5_cpu_reduced")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "intfloat/multilingual-e5-small"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

# REDUCED Training config for CPU
BATCH_SIZE = 8
EPOCHS = 1
LEARNING_RATE = 2e-5
MAX_SEQ_LENGTH = 256
WARMUP_STEPS = 10
SEED = 42
MAX_PAIRS = 5000
MAX_TRIPLETS = 3000

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
        other_indices = []
        for other_area, other_idxs in by_legal_area.items():
            if other_area != area:
                other_indices.extend(other_idxs)
        
        if not other_indices:
            continue
            
        for anchor_idx in indices[:8]:
            pos_candidates = [idx for idx in indices if idx != anchor_idx]
            if not pos_candidates:
                continue
            pos_idx = random.choice(pos_candidates)
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


def evaluate_model(model: SentenceTransformer, metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Evaluate model using fractal-map harness and adversarial benchmarks."""
    logger.info(f"\n=== Evaluating {name} ===")
    
    embeddings_path = OUTPUT_DIR / f"embeddings_{name}.npy"
    if embeddings_path.exists():
        embeddings = np.load(embeddings_path)
    else:
        logger.info("Computing embeddings...")
        texts = [m.get('full_text', '')[:8192] for m in metadata]
        embeddings = model.encode(texts, show_progress_bar=True, batch_size=32, device=DEVICE)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = embeddings / norms
        np.save(embeddings_path, embeddings)
    
    logger.info(f"Embeddings shape: {embeddings.shape}")
    
    # Fractal-map evaluation
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
        fine_mean = np.mean(fine_purs) if fine_purs else 0
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
    
    # Flat Leiden at equivalent resolution for comparison
    flat_labels, _ = leiden_clustering(embeddings, resolution=3.0)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    
    # Adversarial language dominance
    adv_results = adversarial_language_dominance(embeddings, metadata)
    lang_dom = adv_results['mean_language_dominance']
    lang_dom_status = adv_results['status']
    
    # Jurist pairwise preference
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    jurist_results = simulate_pairwise_preference(rep_valid, branches, languages)
    jurist_pref = jurist_results['jurist_would_succeed_rate']
    jurist_status = jurist_results['status']
    
    logger.info(f"  Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Language dominance: {lang_dom:.4f} ({lang_dom_status})")
    logger.info(f"  Jurist preference: {jurist_pref:.4f} ({jurist_status})")
    
    verdict = "PASS" if (lang_dom < 0.85 and jurist_pref > 0.5) else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(fine_overall - flat_purity),
        'language_dominance': float(lang_dom),
        'language_dominance_status': lang_dom_status,
        'jurist_preference': float(jurist_pref),
        'jurist_status': jurist_status,
        'adversarial_both_pass': lang_dom < 0.85 and jurist_pref > 0.5,
        'verdict': verdict,
    }


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - Fine-tune multilingual-e5-small (CPU REDUCED)")
    logger.info("WITH coarse legal structure supervision")
    logger.info("=" * 70)
    
    # 1. Load corpus
    logger.info("\n1. Loading corpus...")
    corpus = load_corpus()
    
    # 2. Load metadata for evaluation
    logger.info("\n2. Loading metadata for evaluation...")
    _, metadata = load_metadata_with_branch()
    
    # Align corpus with metadata
    corpus_by_id = {d.decision_id: d for d in corpus}
    aligned_corpus = [corpus_by_id[m['decision_id']] for m in metadata if m['decision_id'] in corpus_by_id]
    logger.info(f"Aligned corpus: {len(aligned_corpus)} decisions")
    
    # 3. Load pre-trained model as baseline
    logger.info("\n3. Loading pre-trained multilingual-e5-small...")
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model.max_seq_length = MAX_SEQ_LENGTH
    
    # Evaluate pre-trained baseline
    logger.info("\n4. Evaluating PRE-TRAINED baseline...")
    pretrained_results = evaluate_model(model, metadata, "multilingual_e5_small_pretrained_cpu")
    
    # 4. Create training data with legal structure (reduced)
    logger.info("\n5. Creating contrastive training pairs (reduced)...")
    contrastive_examples = create_contrastive_pairs(aligned_corpus, max_pairs=MAX_PAIRS)
    
    logger.info("\n6. Creating triplet examples (reduced)...")
    triplet_examples = create_triplet_examples(aligned_corpus, max_triplets=MAX_TRIPLETS)
    
    # 5. Fine-tune with contrastive loss (1 epoch)
    logger.info("\n7. Fine-tuning with Contrastive Loss (1 epoch)...")
    train_dataloader = DataLoader(contrastive_examples, shuffle=True, batch_size=BATCH_SIZE)
    train_loss = losses.ContrastiveLoss(model)
    
    warmup_steps = WARMUP_STEPS
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=EPOCHS,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
        output_path=str(OUTPUT_DIR / "model_contrastive"),
    )
    
    # Evaluate contrastive fine-tuned
    logger.info("\n8. Evaluating CONTRASTIVE fine-tuned model...")
    contrastive_results = evaluate_model(model, metadata, "multilingual_e5_small_contrastive_cpu")
    
    # 6. Fine-tune with triplet loss (additional, 1 epoch)
    logger.info("\n9. Fine-tuning with Triplet Loss (1 epoch)...")
    model_triplet = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model_triplet.max_seq_length = MAX_SEQ_LENGTH
    
    triplet_dataloader = DataLoader(triplet_examples, shuffle=True, batch_size=BATCH_SIZE)
    triplet_loss = losses.TripletLoss(model_triplet)
    
    model_triplet.fit(
        train_objectives=[(triplet_dataloader, triplet_loss)],
        epochs=EPOCHS,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
        output_path=str(OUTPUT_DIR / "model_triplet"),
    )
    
    # Evaluate triplet fine-tuned
    logger.info("\n10. Evaluating TRIPLET fine-tuned model...")
    triplet_results = evaluate_model(model_triplet, metadata, "multilingual_e5_small_triplet_cpu")
    
    # 7. Combined: contrastive + triplet (1 epoch)
    logger.info("\n11. Fine-tuning with Combined Loss (1 epoch)...")
    model_combined = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model_combined.max_seq_length = MAX_SEQ_LENGTH
    
    combined_dataloader_contrastive = DataLoader(contrastive_examples, shuffle=True, batch_size=BATCH_SIZE)
    combined_dataloader_triplet = DataLoader(triplet_examples, shuffle=True, batch_size=BATCH_SIZE)
    combined_loss_contrastive = losses.ContrastiveLoss(model_combined)
    combined_loss_triplet = losses.TripletLoss(model_combined)
    
    model_combined.fit(
        train_objectives=[
            (combined_dataloader_contrastive, combined_loss_contrastive),
            (combined_dataloader_triplet, combined_loss_triplet),
        ],
        epochs=EPOCHS,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': LEARNING_RATE},
        show_progress_bar=True,
        output_path=str(OUTPUT_DIR / "model_combined"),
    )
    
    # Evaluate combined fine-tuned
    logger.info("\n12. Evaluating COMBINED fine-tuned model...")
    combined_results = evaluate_model(model_combined, metadata, "multilingual_e5_small_combined_cpu")
    
    # 8. Load center_projected baseline for comparison
    logger.info("\n13. Loading center_projected baseline for comparison...")
    center_projected_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
    center_projected_emb = np.load(center_projected_path)
    center_projected_metadata_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    with open(center_projected_metadata_path) as f:
        center_metadata = json.load(f)
    
    # Align center_projected metadata with our metadata
    center_by_id = {m['decision_id']: i for i, m in enumerate(center_metadata)}
    aligned_center = np.array([center_projected_emb[center_by_id[m['decision_id']]] for m in metadata if m['decision_id'] in center_by_id])
    aligned_center_meta = [m for m in metadata if m['decision_id'] in center_by_id]
    
    logger.info(f"Aligned center_projected: {aligned_center.shape}")
    
    # Evaluate center_projected with same harness
    from hierarchical_leiden import compute_branch_purity
    hierarchical_labels_cp, coarse_labels_cp, _, coarse_to_fine_cp = hierarchical_leiden(
        aligned_center, aligned_center_meta, coarse_res=0.5, sub_res=3.0
    )
    coarse_purities_cp = compute_branch_purity_per_cluster(coarse_labels_cp, aligned_center_meta)
    coarse_overall_cp = compute_branch_purity(coarse_labels_cp, aligned_center_meta)
    fine_purities_cp = compute_branch_purity_per_cluster(hierarchical_labels_cp, aligned_center_meta)
    fine_overall_cp = compute_branch_purity(hierarchical_labels_cp, aligned_center_meta)
    
    total_improvements_cp = 0
    total_deteriorations_cp = 0
    total_no_change_cp = 0
    for coarse_id in sorted(coarse_to_fine_cp.keys()):
        fine_ids = coarse_to_fine_cp[coarse_id]
        if not fine_ids: continue
        coarse_pur = coarse_purities_cp.get(coarse_id, 0)
        fine_purs = [fine_purities_cp.get(fid, 0) for fid in fine_ids]
        fine_mean = np.mean(fine_purs) if fine_purs else 0
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements_cp += improvements
        total_deteriorations_cp += deteriorations
        total_no_change_cp += no_change
    
    overall_improvement_cp = fine_overall_cp - coarse_overall_cp
    total_fine_cp = total_improvements_cp + total_deteriorations_cp + total_no_change_cp
    improvement_rate_cp = total_improvements_cp / total_fine_cp if total_fine_cp > 0 else 0
    
    legal_areas_cp = [m.get('legal_area', '') for m in aligned_center_meta]
    legal_areas_cp = [la if la else 'unknown' for la in legal_areas_cp]
    nmi_cp = normalized_mutual_info_score(legal_areas_cp, hierarchical_labels_cp)
    
    adv_cp = adversarial_language_dominance(aligned_center, aligned_center_meta)
    lang_dom_cp = adv_cp['mean_language_dominance']
    lang_dom_status_cp = adv_cp['status']
    
    branches_cp, languages_cp, _, valid_indices_cp = prepare_metadata(aligned_center_meta)
    rep_valid_cp = aligned_center[valid_indices_cp]
    jurist_cp = simulate_pairwise_preference(rep_valid_cp, branches_cp, languages_cp)
    jurist_pref_cp = jurist_cp['jurist_would_succeed_rate']
    jurist_status_cp = jurist_cp['status']
    
    center_results = {
        'name': 'center_projected',
        'coarse_purity': float(coarse_overall_cp),
        'fine_purity': float(fine_overall_cp),
        'overall_improvement': float(overall_improvement_cp),
        'improvement_rate': float(improvement_rate_cp),
        'legal_area_nmi': float(nmi_cp),
        'language_dominance': float(lang_dom_cp),
        'language_dominance_status': lang_dom_status_cp,
        'jurist_preference': float(jurist_pref_cp),
        'jurist_status': jurist_status_cp,
        'adversarial_both_pass': lang_dom_cp < 0.85 and jurist_pref_cp > 0.5,
        'verdict': "PASS" if (lang_dom_cp < 0.85 and jurist_pref_cp > 0.5) else "FAIL",
    }
    
    # 9. Summary
    logger.info("\n" + "=" * 80)
    logger.info("FINETUNING SUMMARY - ADVERSARIAL BENCHMARKS (CPU REDUCED)")
    logger.info("=" * 80)
    logger.info(f"{'Model':<45} {'LangDom':>8} {'LangPass':>8} {'Jurist':>8} {'JurPass':>8} {'Both':>6} {'NMI':>6} {'ImpRate':>8}")
    logger.info("-" * 80)
    
    all_results = {
        'pretrained': pretrained_results,
        'contrastive': contrastive_results,
        'triplet': triplet_results,
        'combined': combined_results,
        'center_projected_baseline': center_results,
    }
    
    for key, res in all_results.items():
        ld = res['language_dominance']
        jp = res['jurist_preference']
        ld_pass = "✅" if ld < 0.85 else "❌"
        jp_pass = "✅" if jp > 0.5 else "❌"
        both = "✅" if res['adversarial_both_pass'] else "❌"
        logger.info(f"{key:<45} {ld:>8.4f} {ld_pass:>8} {jp:>8.4f} {jp_pass:>8} {both:>6} {res['legal_area_nmi']:>6.4f} {res['improvement_rate']:>7.1%}")
    
    # Save all results
    with open(OUTPUT_DIR / "finetune_all_results_cpu_reduced.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Determine best model
    best_model = max(all_results.items(), key=lambda x: (x[1]['adversarial_both_pass'], x[1]['jurist_preference'], -x[1]['language_dominance']))
    logger.info(f"\n🏆 Best model: {best_model[0]} (adversarial_both_pass={best_model[1]['adversarial_both_pass']})")
    
    logger.info("\n=== Fine-tuning Complete ===")
    return all_results


if __name__ == "__main__":
    main()
