#!/usr/bin/env python3
"""
Evaluation Lane — Cross-validate v11 OOS hybrid_stabilized on Frozen Harness v3

BOUNDED QUESTION: Do the v11 OOS hybrid_stabilized models (repaired, train-selection
discipline), when evaluated on the canonical frozen harness v3 (1200-decision expanded
slice), confirm or contradict the legal-distance lane's reported OOS results?

This is an independent cross-lane adversarial check:
- v11 evaluated on 200-decision holdout with jurist_would_succeed_rate metric
- Frozen harness v3 evaluates on full 1200-decision slice with canonical metrics
  (Jurivoc NMI, scale stability, fractal quality, etc.)

If v11 models generalize to the full slice, they should pass both adversarial gates
on the frozen harness. If not, the v11 claims are falsified.

FROZEN SETUP:
- Harness: v3 (seed=42, config_hash=4323f833fa72366a)
- Corpus: 1200 decisions (full expanded slice)
- Model: v11 OOS hybrid_stabilized (hierarchy + no-hierarchy ablation arms)
- Input: center_projected_768 embeddings (full 1200-decision slice)
- Output: 128-dim projected embeddings → frozen harness evaluation

HYPOTHESIS: v11 OOS models will pass both adversarial gates on the full slice,
confirming the legal-distance lane's OOS claims.

BASELINE: v11 report results (hierarchy: LD=0.6015, JP=0.535 on 200 holdout)

SUCCESS RULE (frozen before inspection):
- v11 hierarchy arm PASSES both adversarial gates on full 1200-decision slice
  (LangDom < 0.85, JuristPref > 0.5)
- v11 no-hierarchy arm PASSES both adversarial gates
- Hierarchy-loss effect direction consistent with v11 report (positive JP delta)
"""

import json
import sys
import time
import hashlib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# PATHS
# ============================================================
REPO_ROOT = Path("/home/runner/work/LexMachina/LexMachina")
ACCEPTED_ROOT = Path("/tmp/lex_accepted")
EVAL_CONFIG = REPO_ROOT / "evaluation/config/evaluation_v3_config.json"

# v11 model checkpoints (from accepted legal-distance lane)
V11_HIER_PATH = ACCEPTED_ROOT / "legal-distance/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/best_hybrid_stabilized_oos.pt"
V11_NOHIER_PATH = ACCEPTED_ROOT / "legal-distance/legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized_nohier/best_hybrid_stabilized_oos_nohier.pt"

# Input embeddings (full 1200-decision slice)
CP_768_PATH = ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy"
METADATA_PATH = ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/center_projected_full/metadata.json"

# Output
OUTPUT_DIR = REPO_ROOT / "evaluation/results/v11_cross_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen harness parameters
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"

ADVERSARIAL_THRESHOLDS = {
    "language_dominance": 0.85,
    "jurist_pairwise": 0.5,
}

SUCCESS_RULE = {
    "langdom_gate": 0.85,
    "jurist_pref_gate": 0.5,
    "langdom_target": 0.6,
    "jurist_pref_target": 0.7,
}

# ============================================================
# MODEL (matching v6/v11 HybridProjectionHead)
# ============================================================
class HybridProjectionHead(nn.Module):
    """Projection head: 768 -> 512 -> 256 -> 128 (normalized)."""
    def __init__(self, input_dim=768, hidden_dims=[512, 256], output_dim=128):
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
# ADVERSARIAL BENCHMARKS (canonical frozen harness v3)
# ============================================================
def adversarial_language_dominance(embeddings, metadata, k=20):
    from sklearn.neighbors import NearestNeighbors
    nn_model = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
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
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
    from sklearn.neighbors import NearestNeighbors
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
        "jurist_forced_wrong_rate": round(language_artifact_count / total, 4),
    }


def run_adversarial_benchmarks(embeddings, metadata):
    from collections import Counter
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    lang_dom = adversarial_language_dominance(embeddings, metadata, k=20)
    jurist_pref = simulate_pairwise_preference(embeddings, branches, languages, k=10)
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }


# ============================================================
# JURIVOC ALIGNMENT (canonical frozen harness v3)
# ============================================================
def compute_jurivoc_alignment(embeddings, metadata):
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    kmeans_l0 = KMeans(n_clusters=4, random_state=FROZEN_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = normalized_mutual_info_score(branches, labels_l0)
    kmeans_l1 = KMeans(n_clusters=16, random_state=FROZEN_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    return {
        "level_0_nmi": float(nmi_l0),
        "level_1_nmi": float(nmi_l1),
        "status": "PASS" if nmi_l0 > 0.3 and nmi_l1 > 0.2 else "FAIL",
    }


# ============================================================
# SCALE STABILITY (canonical frozen harness v3)
# ============================================================
def compute_scale_stability(embeddings, metadata):
    from sklearn.neighbors import NearestNeighbors
    n = embeddings.shape[0]
    np.random.seed(FROZEN_SEED)
    indices = np.arange(n)
    np.random.shuffle(indices)
    split_idx = int(0.8 * n)
    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]
    nn_full = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_full.fit(embeddings)
    _, full_neighbors = nn_full.kneighbors(embeddings)
    full_neighbors = full_neighbors[:, 1:]
    train_embeddings = embeddings[train_idx]
    train_to_full = {i: idx for i, idx in enumerate(train_idx)}
    nn_sub = NearestNeighbors(n_neighbors=11, metric='cosine')
    nn_sub.fit(train_embeddings)
    _, sub_neighbors = nn_sub.kneighbors(embeddings[test_idx])
    sub_neighbors = sub_neighbors[:, 1:]
    sub_neighbors_full = np.array([[train_to_full[n] for n in row] for row in sub_neighbors])
    overlaps = []
    for i, test_i in enumerate(test_idx):
        full_set = set(full_neighbors[test_i])
        sub_set = set(sub_neighbors_full[i])
        overlap = len(full_set & sub_set) / len(full_set)
        overlaps.append(overlap)
    mean_overlap = np.mean(overlaps)
    return {
        "mean_neighbor_overlap": float(mean_overlap),
        "status": "PASS" if mean_overlap > 0.5 else "FAIL",
    }


# ============================================================
# FRACTAL QUALITY (canonical frozen harness v3)
# ============================================================
def run_fractal_quality_benchmarks(embeddings, metadata):
    from collections import Counter, defaultdict
    from sklearn.metrics import normalized_mutual_info_score
    FRACTAL_MAP_PATH = ACCEPTED_ROOT / "fractal-map/fractal_map/hierarchical"
    sys.path.insert(0, str(FRACTAL_MAP_PATH))
    try:
        from hierarchical_leiden import hierarchical_leiden, compute_branch_purity
        HAS_HL = True
    except ImportError:
        HAS_HL = False

    if not HAS_HL or embeddings.shape[0] != len(metadata):
        return {'improvement_rate': 0.0, 'n_coarse': 0, 'n_fine': 0,
                'coarse_purity': 0.0, 'fine_purity': 0.0, 'hierarchical_advantage': 0.0}

    result = hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0)
    hierarchical_labels, coarse_labels, cluster_info = result
    coarse_to_fine = defaultdict(list)
    for sub_id, info in cluster_info.items():
        if not info.get('too_small', False):
            coarse_to_fine[info['coarse_id']].append(sub_id)
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    coarse_purities = {}
    for c in np.unique(coarse_labels[coarse_labels != -1]):
        mask = coarse_labels == c
        cluster_branches = [metadata[i].get('branch', 'unknown') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b != 'unknown']
        if cluster_branches:
            coarse_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    fine_purities = {}
    for c in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        mask = hierarchical_labels == c
        cluster_branches = [metadata[i].get('branch', 'unknown') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b != 'unknown']
        if cluster_branches:
            fine_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    coarse_overall = np.mean(list(coarse_purities.values())) if coarse_purities else 0
    fine_overall = np.mean(list(fine_purities.values())) if fine_purities else 0
    total_improvements = 0
    total_fine = 0
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        total_improvements += improvements
        total_fine += len(fine_purs)
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    flat_result = hierarchical_leiden(embeddings, metadata, coarse_res=3.0, sub_res=0.5)
    flat_labels = flat_result[0]
    flat_purity = compute_branch_purity(flat_labels, metadata)
    hierarchical_advantage = fine_overall - flat_purity
    return {
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'improvement_rate': float(improvement_rate),
        'hierarchical_advantage': float(hierarchical_advantage),
        'flat_purity': float(flat_purity),
    }


# ============================================================
# MAIN
# ============================================================
def main():
    from collections import defaultdict
    np.random.seed(FROZEN_SEED)
    torch.manual_seed(FROZEN_SEED)

    logger.info("=" * 80)
    logger.info("EVALUATION LANE — Cross-validate v11 OOS hybrid_stabilized on Frozen Harness v3")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Frozen Harness: seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH}")
    logger.info("=" * 80)

    # 1. Load full 1200-decision embeddings and metadata
    logger.info("\n1. Loading full 1200-decision slice...")
    cp_embeddings = np.load(CP_768_PATH)
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"   Loaded {cp_embeddings.shape[0]} embeddings, dim={cp_embeddings.shape[1]}")
    logger.info(f"   Loaded {len(metadata)} metadata entries")

    assert cp_embeddings.shape[0] == len(metadata), \
        f"Embedding/metadata count mismatch: {cp_embeddings.shape[0]} vs {len(metadata)}"

    # 2. Add branch info to metadata
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
    for m in metadata:
        chamber = m.get("chamber", "")
        if chamber in CHAMBER_TO_BRANCH:
            m['branch'] = CHAMBER_TO_BRANCH[chamber]
        else:
            m['branch'] = 'unknown'
        if 'language' not in m:
            m['language'] = 'de'

    # 3. Baseline: center_projected_768 on full slice
    logger.info("\n2. BASELINE: center_projected_768 on full 1200-decision slice")
    cp_norm = cp_embeddings / np.linalg.norm(cp_embeddings, axis=1, keepdims=True)
    cp_adv = run_adversarial_benchmarks(cp_norm, metadata)
    logger.info(f"   LangDom={cp_adv['language_dominance_score']:.4f} ({cp_adv['adversarial_language_dominance']['status']})")
    logger.info(f"   JuristPref={cp_adv['jurist_preference_rate']:.4f} ({cp_adv['jurist_pairwise_preference']['status']})")
    logger.info(f"   Both pass: {cp_adv['both_pass']}")

    # 4. Load and run v11 models
    all_results = {
        'center_projected_768_baseline': {
            'adversarial': cp_adv,
            'jurivoc': compute_jurivoc_alignment(cp_norm, metadata),
            'scale': compute_scale_stability(cp_norm, metadata),
            'fractal': run_fractal_quality_benchmarks(cp_norm, metadata),
        }
    }

    model_configs = [
        ("v11_oos_hybrid_stabilized_hierarchy", V11_HIER_PATH, "hierarchy"),
        ("v11_oos_hybrid_stabilized_nohierarchy", V11_NOHIER_PATH, "no-hierarchy"),
    ]

    for name, model_path, arm in model_configs:
        logger.info(f"\n3. Loading v11 model: {name}")
        if not model_path.exists():
            logger.error(f"   Model not found: {model_path}")
            all_results[name] = {'error': f'Model not found: {model_path}'}
            continue

        model = HybridProjectionHead(input_dim=768, hidden_dims=[512, 256], output_dim=128)
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        if isinstance(checkpoint, dict) and 'model_state' in checkpoint:
            model.load_state_dict(checkpoint['model_state'])
            epoch = checkpoint.get('epoch', '?')
            logger.info(f"   Loaded model from epoch {epoch}")
        else:
            model.load_state_dict(checkpoint)
            logger.info(f"   Loaded model checkpoint")

        model.eval()
        with torch.no_grad():
            projected = model(torch.from_numpy(cp_embeddings).float()).numpy()

        # Save generated embeddings
        np.save(OUTPUT_DIR / f"{name}_embeddings.npy", projected)
        logger.info(f"   Generated embeddings: {projected.shape}")

        # Evaluate on full frozen harness
        proj_norm = projected / np.linalg.norm(projected, axis=1, keepdims=True)
        logger.info(f"   Running adversarial benchmarks...")
        adv = run_adversarial_benchmarks(proj_norm, metadata)
        logger.info(f"   LangDom={adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"   JuristPref={adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        logger.info(f"   Both pass: {adv['both_pass']}")

        logger.info(f"   Running Jurivoc alignment...")
        jurivoc = compute_jurivoc_alignment(proj_norm, metadata)
        logger.info(f"   Jurivoc L0 NMI={jurivoc['level_0_nmi']:.4f}, L1 NMI={jurivoc['level_1_nmi']:.4f}")

        logger.info(f"   Running scale stability...")
        scale = compute_scale_stability(proj_norm, metadata)
        logger.info(f"   Scale stability={scale['mean_neighbor_overlap']:.4f}")

        logger.info(f"   Running fractal quality...")
        fractal = run_fractal_quality_benchmarks(proj_norm, metadata)
        logger.info(f"   ImpRate={fractal['improvement_rate']:.2%}, HierAdv={fractal['hierarchical_advantage']:.4f}")

        all_results[name] = {
            'adversarial': adv,
            'jurivoc': jurivoc,
            'scale': scale,
            'fractal': fractal,
        }

    # 5. Verdict
    logger.info("\n" + "=" * 80)
    logger.info("CROSS-VALIDATION VERDICT")
    logger.info("=" * 80)

    for name in ["v11_oos_hybrid_stabilized_hierarchy", "v11_oos_hybrid_stabilized_nohierarchy"]:
        if name not in all_results or 'error' in all_results[name]:
            logger.info(f"  {name}: ERROR/SKIPPED")
            continue
        res = all_results[name]
        adv = res['adversarial']
        gate_ld = adv['language_dominance_score'] < SUCCESS_RULE['langdom_gate']
        gate_jp = adv['jurist_preference_rate'] > SUCCESS_RULE['jurist_pref_gate']
        verdict = "PASS" if (gate_ld and gate_jp) else "FAIL"
        logger.info(f"  {name}: {verdict} (LD={adv['language_dominance_score']:.4f}, JP={adv['jurist_preference_rate']:.4f})")

    # Hierarchy effect
    if ('v11_oos_hybrid_stabilized_hierarchy' in all_results and
        'v11_oos_hybrid_stabilized_nohierarchy' in all_results and
        'error' not in all_results.get('v11_oos_hybrid_stabilized_hierarchy', {}) and
        'error' not in all_results.get('v11_oos_hybrid_stabilized_nohierarchy', {})):
        hier_jp = all_results['v11_oos_hybrid_stabilized_hierarchy']['adversarial']['jurist_preference_rate']
        nohier_jp = all_results['v11_oos_hybrid_stabilized_nohierarchy']['adversarial']['jurist_preference_rate']
        delta = hier_jp - nohier_jp
        logger.info(f"\n  Hierarchy loss effect on full slice: ΔJP = {delta:+.4f} ({'positive' if delta > 0 else 'negative'})")
        logger.info(f"  v11 report hierarchy effect on 200 holdout: +0.030")
        if abs(delta - 0.030) < 0.05:
            logger.info(f"  CONSISTENT with v11 report (within 0.05 tolerance)")
        else:
            logger.info(f"  DIVERGENT from v11 report (delta={delta:.4f} vs reported +0.030)")

    # 6. Save results
    output = {
        'run_id': f'v11_cross_validation_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'factory_direction_version': 10,
        'frozen_harness': {'seed': FROZEN_SEED, 'config_hash': FROZEN_CONFIG_HASH},
        'corpus': f'{cp_embeddings.shape[0]} decisions (full expanded slice)',
        'success_rule': SUCCESS_RULE,
        'results': {},
        'verdict_summary': {},
    }

    for name, res in all_results.items():
        if 'error' in res:
            output['results'][name] = res
            output['verdict_summary'][name] = 'ERROR'
            continue
        # Serialize for JSON
        serializable = {}
        for k, v in res.items():
            if isinstance(v, dict):
                serializable[k] = {kk: vv for kk, vv in v.items()
                                   if isinstance(vv, (int, float, str, bool, type(None)))}
            else:
                serializable[k] = v
        output['results'][name] = serializable
        adv = res['adversarial']
        gate_ld = adv['language_dominance_score'] < SUCCESS_RULE['langdom_gate']
        gate_jp = adv['jurist_preference_rate'] > SUCCESS_RULE['jurist_pref_gate']
        output['verdict_summary'][name] = 'PASS' if (gate_ld and gate_jp) else 'FAIL'

    output_path = OUTPUT_DIR / "v11_cross_validation_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nResults saved to: {output_path}")

    return all_results


if __name__ == "__main__":
    main()
