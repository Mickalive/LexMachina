#!/usr/bin/env python3
"""
Legal Distance Lane - Independent Validation of Breakthrough Representations

Validates the three breakthrough representations from v6:
1. linear_metric_epoch4 (JP=0.685, LangDom=0.680)
2. hybrid_stabilized_epoch1 (JP=0.666, LangDom=0.670)
3. mahalanobis_metric_epoch4 (JP=0.678, LangDom=0.684)

Against the two adversarial gates:
- adversarial_language_dominance < 0.85
- jurist_pairwise_preference > 0.5

This is an independent verification using the same evaluation harness.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/validation_breakthrough")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BREAKTHROUGH_EMBEDDINGS = {
    'linear_metric_epoch4': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy"),
    'hybrid_stabilized_epoch1': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/hybrid_objective_stabilized/best_embeddings.npy"),
    'mahalanobis_metric_epoch4': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy"),
}

# Reference
CENTER_PROJECTED_EMBEDDINGS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CENTER_PROJECTED_METADATA = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")

# Evaluation metadata (fractal-map baseline 1000 decisions)
EVAL_METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")


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
        import sys
        sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
        from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity, compute_branch_purity_per_cluster, leiden_clustering

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


def main():
    logger.info("=" * 80)
    logger.info("INDEPENDENT VALIDATION: Breakthrough Representations v6")
    logger.info("Testing: linear_metric_epoch4, hybrid_stabilized_epoch1, mahalanobis_metric_epoch4")
    logger.info("=" * 80)

    # Load evaluation metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_evaluation_metadata()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")

    # Load center_projected reference
    logger.info("\n2. Loading center_projected reference...")
    cp_embeddings = np.load(CENTER_PROJECTED_EMBEDDINGS)
    with open(CENTER_PROJECTED_METADATA) as f:
        cp_metadata = json.load(f)

    # Align center_projected to evaluation metadata
    cp_by_id = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    eval_ids = [m['decision_id'] for m in metadata]
    valid_ids = [did for did in eval_ids if did in cp_by_id]
    valid_cp_indices = [cp_by_id[did] for did in valid_ids]
    center_projected_aligned = cp_embeddings[valid_cp_indices]
    metadata_aligned = [m for m in metadata if m['decision_id'] in cp_by_id]

    logger.info(f"Center projected aligned: {center_projected_aligned.shape}")
    logger.info(f"Metadata aligned: {len(metadata_aligned)} decisions")

    # Evaluate center_projected baseline
    logger.info("\n3. Evaluating center_projected baseline...")
    cp_results = run_adversarial_benchmarks(center_projected_aligned, metadata_aligned)
    cp_fractal = evaluate_fractal_quality(center_projected_aligned, metadata_aligned)

    logger.info(f"  Language Dominance: {cp_results['language_dominance_score']:.4f} ({cp_results['adversarial_language_dominance']['status']})")
    logger.info(f"  Jurist Preference: {cp_results['jurist_preference_rate']:.4f} ({cp_results['jurist_pairwise_preference']['status']})")
    logger.info(f"  BOTH PASS: {cp_results['both_pass']}")
    logger.info(f"  Fractal: {cp_fractal.get('n_coarse', 'N/A')} coarse → {cp_fractal.get('n_fine', 'N/A')} fine, imp_rate={cp_fractal.get('improvement_rate', 0):.1%}")

    # Evaluate breakthrough representations
    logger.info("\n4. Evaluating breakthrough representations...")
    all_results = {'center_projected': {'adversarial': cp_results, 'fractal': cp_fractal}}

    for name, path in BREAKTHROUGH_EMBEDDINGS.items():
        logger.info(f"\n--- Evaluating {name} ---")
        try:
            embeddings = np.load(path)
            logger.info(f"  Loaded shape: {embeddings.shape}")

            # Align to metadata if needed
            if embeddings.shape[0] != len(metadata_aligned):
                if embeddings.shape[0] > len(metadata_aligned):
                    embeddings = embeddings[:len(metadata_aligned)]
                    logger.warning(f"  Truncated to {len(metadata_aligned)}")
                else:
                    logger.warning(f"  Shape mismatch ({embeddings.shape[0]} vs {len(metadata_aligned)}), skipping")
                    continue

            # Normalize
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            embeddings = embeddings / norms

            adv_results = run_adversarial_benchmarks(embeddings, metadata_aligned)
            fractal_results = evaluate_fractal_quality(embeddings, metadata_aligned)

            all_results[name] = {
                'adversarial': adv_results,
                'fractal': fractal_results,
                'embedding_shape': list(embeddings.shape),
            }

            adv = adv_results['adversarial_language_dominance']
            jp = adv_results['jurist_pairwise_preference']
            fr = fractal_results

            logger.info(f"  Language Dominance: {adv['mean_language_dominance']:.4f} ({adv['status']})")
            logger.info(f"  Jurist Preference: {jp['jurist_would_succeed_rate']:.4f} ({jp['status']})")
            logger.info(f"  BOTH PASS: {adv_results['both_pass']}")
            logger.info(f"  Fractal: {fr.get('n_coarse', 'N/A')} coarse → {fr.get('n_fine', 'N/A')} fine, imp_rate={fr.get('improvement_rate', 0):.1%}, NMI={fr.get('legal_area_nmi', 0):.4f}")
            logger.info(f"  Overclustering: {fr.get('overclustering', 'N/A')}")

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e)}

    # Summary
    logger.info("\n" + "=" * 100)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Representation':<35} {'LangDom':>8} {'LD-Pass':>7} {'Jurist':>8} {'JP-Pass':>7} {'Both':>5} {'C/F':>8} {'Imp%':>6} {'NMI':>6} {'OverC':>5}")
    logger.info("-" * 100)

    for name, res in all_results.items():
        if 'error' in res:
            logger.info(f"{name:<35} {'ERROR':>8} {'N/A':>7} {'ERROR':>8} {'N/A':>7} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>6} {'N/A':>5}")
            continue

        adv = res['adversarial']
        fr = res['fractal']

        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✅" if adv['adversarial_language_dominance']['status'] == 'PASS' else "❌"
        jp_pass = "✅" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "❌"
        both = "✅" if adv['both_pass'] else "❌"
        c_f = f"{fr.get('n_coarse', '?')}/{fr.get('n_fine', '?')}"
        imp = f"{fr.get('improvement_rate', 0):.1%}"
        nmi = f"{fr.get('legal_area_nmi', 0):.4f}"
        overc = "✅" if fr.get('overclustering', True) else "❌"

        logger.info(f"{name:<35} {ld:>8.4f} {ld_pass:>7} {jp:>8.4f} {jp_pass:>7} {both:>5} {c_f:>8} {imp:>6} {nmi:>6} {overc:>5}")

    # Final verdict
    logger.info("\n" + "=" * 80)
    logger.info("FINAL VERDICT")
    logger.info("=" * 80)

    valid_count = 0
    for name, res in all_results.items():
        if name == 'center_projected':
            continue
        if 'error' not in res and res['adversarial']['both_pass'] and not res['fractal'].get('overclustering', True):
            valid_count += 1
            logger.info(f"✅ {name}: VALID - passes both adversarial gates with meaningful fractal structure")

    logger.info(f"\nBreakthrough representations VALIDATED: {valid_count}/3")
    logger.info(f"Results saved to: {OUTPUT_DIR / 'validation_results.json'}")

    # Save results
    with open(OUTPUT_DIR / "validation_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    return all_results


if __name__ == "__main__":
    main()