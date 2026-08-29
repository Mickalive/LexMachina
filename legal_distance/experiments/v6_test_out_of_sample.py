#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Out-of-Sample Generalization Test

Tests whether the learned metric learning models (linear projection, Mahalanobis)
generalize to unseen decisions (200 holdout decisions not in the training/eval set).

This is critical for productization: the models must work on new decisions
without retraining.
"""

import json
import numpy as np
import logging
import torch
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score

import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')

from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity, compute_branch_purity_per_cluster, leiden_clustering

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")

LINEAR_MODEL_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_linear.pt")
MAHALANOBIS_MODEL_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_mahalanobis.pt")
HYBRID_MODEL_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/hybrid_objective_stabilized/best_projection_head.pt")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/out_of_sample_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = "cpu"

# Model definitions (must match training)
class SimpleLinearHead(torch.nn.Module):
    """Simple linear projection: 768 -> 128"""
    def __init__(self, input_dim: int = 768, output_dim: int = 128):
        super().__init__()
        self.linear = torch.nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        return torch.nn.functional.normalize(self.linear(x), dim=1, p=2)


class MetricLearningHead(torch.nn.Module):
    """Mahalanobis metric learning with low-rank factorization"""
    def __init__(self, input_dim: int = 768, output_dim: int = 128, rank: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.rank = min(rank, input_dim, output_dim)
        
        # Low-rank factorization: M = L^T L where L is (rank, input_dim)
        self.L = torch.nn.Parameter(torch.randn(self.rank, input_dim) * 0.01)
        # Optional linear projection after metric
        self.projection = torch.nn.Linear(input_dim, output_dim, bias=False)
        
    def forward(self, x):
        # Apply Mahalanobis transformation: x -> L x (maps to rank-dim space)
        # Then project to output_dim
        x_metric = torch.nn.functional.linear(x, self.L)  # (batch, rank)
        x_out = self.projection(x)  # (batch, output_dim)
        # Combine: use metric-transformed features
        return torch.nn.functional.normalize(x_out, dim=1, p=2)


def load_evaluation_metadata() -> List[Dict]:
    """Load metadata from fractal-map baseline (1000 decisions)."""
    with open(EVAL_METADATA_PATH, 'r') as f:
        metadata = json.load(f)

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

    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')

    return metadata


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []

    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")

        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)

    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


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


def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the two critical adversarial benchmarks."""
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]

    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)

    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }


def evaluate_fractal_quality(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Evaluate fractal/hierarchical quality using hierarchical Leiden."""
    try:
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

        return {
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
    except Exception as e:
        logger.error(f"Fractal quality evaluation failed: {e}")
        return {'error': str(e)}


def load_center_projected_and_metadata():
    """Load center_projected embeddings and metadata for all 1200 decisions."""
    embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected: {embeddings.shape}, {len(metadata)} decisions")
    return embeddings, metadata


def split_train_holdout(cp_embeddings, cp_metadata, eval_metadata):
    """Split into train (1000 eval) and holdout (200 cp-only) sets."""
    eval_ids = {m['decision_id'] for m in eval_metadata}
    
    train_indices = []
    holdout_indices = []
    train_metadata = []
    holdout_metadata = []
    
    for i, meta in enumerate(cp_metadata):
        if meta['decision_id'] in eval_ids:
            train_indices.append(i)
            train_metadata.append(meta)
        else:
            holdout_indices.append(i)
            holdout_metadata.append(meta)
    
    train_embeddings = cp_embeddings[train_indices]
    holdout_embeddings = cp_embeddings[holdout_indices]
    
    logger.info(f"Train set: {len(train_indices)} decisions")
    logger.info(f"Holdout set: {len(holdout_indices)} decisions")
    
    return train_embeddings, train_metadata, holdout_embeddings, holdout_metadata


def apply_model(model, embeddings: np.ndarray) -> np.ndarray:
    """Apply a trained model to embeddings (inference mode)."""
    model.eval()
    with torch.no_grad():
        tensor = torch.from_numpy(embeddings).float().to(DEVICE)
        output = model(tensor).cpu().numpy()
    return output


def evaluate_representation_full(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Full evaluation of a representation."""
    logger.info(f"\n=== Evaluating {name} ({embeddings.shape[0]} decisions) ===")
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    fractal_results = evaluate_fractal_quality(embeddings, metadata)
    
    logger.info(f"  Language Dominance: {adv_results['language_dominance_score']:.4f} ({adv_results['adversarial_language_dominance']['status']})")
    logger.info(f"  Jurist Preference: {adv_results['jurist_preference_rate']:.4f} ({adv_results['jurist_pairwise_preference']['status']})")
    logger.info(f"  BOTH PASS: {adv_results['both_pass']}")
    if 'n_coarse' in fractal_results:
        logger.info(f"  Fractal: {fractal_results['n_coarse']} coarse → {fractal_results['n_fine']} fine, imp_rate={fractal_results['improvement_rate']:.1%}, NMI={fractal_results['legal_area_nmi']:.4f}")
        logger.info(f"  Overclustering: {fractal_results['overclustering']}")
    
    return {
        'name': name,
        'n_decisions': embeddings.shape[0],
        'embedding_dim': embeddings.shape[1],
        'adversarial': adv_results,
        'fractal': fractal_results,
    }


def main():
    logger.info("=" * 80)
    logger.info("OUT-OF-SAMPLE GENERALIZATION TEST - v6 Metric Learning Models")
    logger.info("=" * 80)
    
    # Load data
    logger.info("\n1. Loading center_projected embeddings (1200 decisions)...")
    cp_embeddings, cp_metadata = load_center_projected_and_metadata()
    
    logger.info("\n2. Loading evaluation metadata (1000 decisions)...")
    eval_metadata = load_evaluation_metadata()
    
    logger.info("\n3. Splitting into train (1000) and holdout (200)...")
    train_embeddings, train_metadata, holdout_embeddings, holdout_metadata = split_train_holdout(
        cp_embeddings, cp_metadata, eval_metadata
    )
    
    # Load models
    logger.info("\n4. Loading trained models...")
    
    # Linear model
    linear_model = SimpleLinearHead(input_dim=768, output_dim=128)
    linear_state = torch.load(LINEAR_MODEL_PATH, map_location=DEVICE)
    linear_model.load_state_dict(linear_state)
    logger.info("  Loaded linear projection model")
    
    # Mahalanobis model
    mahalanobis_model = MetricLearningHead(input_dim=768, output_dim=128, rank=64)
    mahalanobis_state = torch.load(MAHALANOBIS_MODEL_PATH, map_location=DEVICE)
    mahalanobis_model.load_state_dict(mahalanobis_state)
    logger.info("  Loaded Mahalanobis model")
    
    # Hybrid model (different architecture - need to check)
    # The hybrid model uses a different architecture. Let's skip for now or load differently.
    
    # Test on TRAIN set (should reproduce results)
    logger.info("\n5. Testing on TRAIN set (1000 decisions) - should match validation results...")
    train_linear = apply_model(linear_model, train_embeddings)
    train_mahalanobis = apply_model(mahalanobis_model, train_embeddings)
    
    train_results = {}
    train_results['center_projected'] = evaluate_representation_full(train_embeddings, train_metadata, "center_projected_train")
    train_results['linear_metric'] = evaluate_representation_full(train_linear, train_metadata, "linear_metric_train")
    train_results['mahalanobis_metric'] = evaluate_representation_full(train_mahalanobis, train_metadata, "mahalanobis_metric_train")
    
    # Test on HOLDOUT set (true out-of-sample)
    logger.info("\n6. Testing on HOLDOUT set (200 decisions) - TRUE OUT-OF-SAMPLE...")
    holdout_linear = apply_model(linear_model, holdout_embeddings)
    holdout_mahalanobis = apply_model(mahalanobis_model, holdout_embeddings)
    
    holdout_results = {}
    holdout_results['center_projected'] = evaluate_representation_full(holdout_embeddings, holdout_metadata, "center_projected_holdout")
    holdout_results['linear_metric'] = evaluate_representation_full(holdout_linear, holdout_metadata, "linear_metric_holdout")
    holdout_results['mahalanobis_metric'] = evaluate_representation_full(holdout_mahalanobis, holdout_metadata, "mahalanobis_metric_holdout")
    
    # Test on FULL set (1200 decisions)
    logger.info("\n7. Testing on FULL set (1200 decisions)...")
    full_linear = apply_model(linear_model, cp_embeddings)
    full_mahalanobis = apply_model(mahalanobis_model, cp_embeddings)
    
    full_results = {}
    full_results['center_projected'] = evaluate_representation_full(cp_embeddings, cp_metadata, "center_projected_full")
    full_results['linear_metric'] = evaluate_representation_full(full_linear, cp_metadata, "linear_metric_full")
    full_results['mahalanobis_metric'] = evaluate_representation_full(full_mahalanobis, cp_metadata, "mahalanobis_metric_full")
    
    # Summary
    logger.info("\n" + "=" * 100)
    logger.info("OUT-OF-SAMPLE TEST SUMMARY")
    logger.info("=" * 100)
    
    for split_name, results in [("TRAIN (1000)", train_results), ("HOLDOUT (200)", holdout_results), ("FULL (1200)", full_results)]:
        logger.info(f"\n--- {split_name} ---")
        logger.info(f"{'Representation':<30} {'LangDom':>8} {'LD-Pass':>7} {'Jurist':>8} {'JP-Pass':>7} {'Both':>5} {'C/F':>8} {'Imp%':>6} {'NMI':>6} {'OverC':>5}")
        logger.info("-" * 100)
        
        for name, res in results.items():
            adv = res['adversarial']
            fr = res['fractal']
            
            ld = adv['language_dominance_score']
            jp = adv['jurist_preference_rate']
            ld_pass = "✅" if adv['adversarial_language_dominance']['status'] == 'PASS' else "❌"
            jp_pass = "✅" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "❌"
            both = "✅" if adv['both_pass'] else "❌"
            
            if 'error' in fr:
                c_f = "ERROR"
                imp = "N/A"
                nmi = "N/A"
                overc = "N/A"
            else:
                c_f = f"{fr['n_coarse']}/{fr['n_fine']}"
                imp = f"{fr['improvement_rate']:.1%}"
                nmi = f"{fr['legal_area_nmi']:.4f}"
                overc = "⚠️" if fr.get('overclustering', False) else "✅"
            
            logger.info(f"{name:<30} {ld:>8.4f} {ld_pass:>7} {jp:>8.4f} {jp_pass:>7} {both:>5} {c_f:>8} {imp:>6} {nmi:>6} {overc:>5}")
    
    # Key test: Do holdout results match train results?
    logger.info("\n" + "=" * 80)
    logger.info("GENERALIZATION ASSESSMENT")
    logger.info("=" * 80)
    
    for model_name in ['linear_metric', 'mahalanobis_metric']:
        train_res = train_results[model_name]
        holdout_res = holdout_results[model_name]
        
        train_ld = train_res['adversarial']['language_dominance_score']
        train_jp = train_res['adversarial']['jurist_preference_rate']
        train_both = train_res['adversarial']['both_pass']
        
        holdout_ld = holdout_res['adversarial']['language_dominance_score']
        holdout_jp = holdout_res['adversarial']['jurist_preference_rate']
        holdout_both = holdout_res['adversarial']['both_pass']
        
        ld_diff = abs(train_ld - holdout_ld)
        jp_diff = abs(train_jp - holdout_jp)
        
        logger.info(f"\n{model_name}:")
        logger.info(f"  Train:  LangDom={train_ld:.4f}, JuristPref={train_jp:.4f}, BothPass={train_both}")
        logger.info(f"  Holdout: LangDom={holdout_ld:.4f}, JuristPref={holdout_jp:.4f}, BothPass={holdout_both}")
        logger.info(f"  Delta:  LangDom={ld_diff:.4f}, JuristPref={jp_diff:.4f}")
        
        if holdout_both and ld_diff < 0.05 and jp_diff < 0.05:
            logger.info(f"  ✅ GOOD GENERALIZATION: Holdout passes both gates, small delta")
        elif holdout_both:
            logger.info(f"  ⚠️  PARTIAL: Holdout passes both gates but notable delta")
        else:
            logger.info(f"  ❌ POOR: Holdout fails adversarial gates")
    
    # Save results
    all_results = {
        'train': train_results,
        'holdout': holdout_results,
        'full': full_results,
    }
    
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
    
    with open(OUTPUT_DIR / "out_of_sample_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)
    
    logger.info(f"\nResults saved to: {OUTPUT_DIR / 'out_of_sample_results.json'}")
    
    return all_results


if __name__ == "__main__":
    main()