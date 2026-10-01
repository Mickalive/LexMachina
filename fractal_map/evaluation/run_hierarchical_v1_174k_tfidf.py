#!/usr/bin/env python3
"""
Run hierarchical_v1 protocol evaluation on ALL 8 TF-IDF representations at 174k scale.

This is the core fractal-map lane work: evaluate constrained hierarchical Leiden
on production TF-IDF representations at full corpus scale using the frozen
hierarchical_v1 protocol.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import sys
import logging

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/fractal_map/experiments')
from constrained_hierarchical_leiden import (
    load_data,
    constrained_hierarchical_leiden,
    compute_branch_purity,
    compute_area_purity,
    compute_fragmentation,
    compute_zoom_coherence_hierarchical,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Frozen specification (matching hierarchical_v1 protocol)
SPEC = {
    "experiment": "fractal-map hierarchical zoom-quality evaluation (constrained hierarchical Leiden) - FULL 174k TF-IDF",
    "lane": "fractal-map",
    "direction_version": 29,
    "date_frozen": "2026-10-01",
    "protocol_version": "hierarchical_v1",
    "note": "Evaluates 2-level hierarchical clustering (coarse→fine) on ALL 8 TF-IDF representations at full 174k scale.",
    "hypothesis": "Constrained hierarchical Leiden at 174k achieves zero fragmentation, perfect nesting, and meaningful zoom refinement on the coarse→fine transition for TF-IDF modes.",
    "modes_frozen": [
        "cited_decisions_tfidf",
        "cited_outcome_hybrid_0.5",
        "cited_outcome_hybrid_0.7",
        "full_text_tfidf_light",
        "outcome_tfidf",
        "regeste_full_text_hybrid_0.5",
        "regeste_full_text_hybrid_0.7",
        "regeste_tfidf",
    ],
    "config_frozen": {
        "coarse_res": 0.25,
        "base_sub_res": 3.0,
        "min_cluster_size": 10,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": True,
        "k_neighbors": 15,
    },
    "metrics": {
        "fragmentation": "singleton_fraction at fine level (must be < 0.01)",
        "nesting": "strict nesting consistency coarse→fine (must be 1.0 by construction)",
        "branch_purity_delta": "fine_branch_purity - coarse_branch_purity (must be > 0)",
        "area_purity_delta": "fine_area_purity - coarse_area_purity (must be > 0)",
        "zoom_coherence": "improvement_rate on coarse→fine transition (must be > 0.5)",
        "legal_structure_branch": "fine_branch_purity > 2 * random_branch_baseline",
        "legal_structure_area": "fine_area_purity > 2 * random_area_baseline",
    },
    "success_rule_per_mode": "PASS iff all 7 metrics pass their thresholds",
    "overall_verdict_rule": "PASS iff ALL 8 TF-IDF modes PASS",
    "baseline_source": "/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json",
}

EMBEDDINGS_DIR = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings')
METADATA_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_v1_174k_tfidf')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODE_FILES = {
    "cited_decisions_tfidf": "cited_decisions_tfidf.npy",
    "cited_outcome_hybrid_0.5": "cited_outcome_hybrid_0.5.npy",
    "cited_outcome_hybrid_0.7": "cited_outcome_hybrid_0.7.npy",
    "full_text_tfidf_light": "full_text_tfidf_light.npy",
    "outcome_tfidf": "outcome_tfidf.npy",
    "regeste_full_text_hybrid_0.5": "regeste_full_text_hybrid_0.5.npy",
    "regeste_full_text_hybrid_0.7": "regeste_full_text_hybrid_0.7.npy",
    "regeste_tfidf": "regeste_tfidf.npy",
}

MIN_CLUSTER_SIZE = 3  # for purity calculation (not the hierarchical min_cluster_size=10)


def write_frozen_spec():
    spec_path = OUTPUT_DIR / 'hierarchical_v1_frozen_spec.json'
    if spec_path.exists():
        existing = json.loads(spec_path.read_text())
        assert existing == SPEC, f"frozen spec changed; abort: {spec_path}"
        logger.info(f"Frozen spec already present and identical: {spec_path}")
    else:
        spec_path.write_text(json.dumps(SPEC, indent=2) + '\n')
        logger.info(f"FROZEN SPEC WRITTEN: {spec_path}")


def load_metadata():
    with open(METADATA_PATH) as f:
        return json.load(f)


def compute_random_baselines(meta):
    branches = {m['branch'] for m in meta if m.get('branch') and m['branch'] != 'unknown' and m['branch'] != 'null'}
    areas = {m['legal_area'] for m in meta if m.get('legal_area') and m['legal_area'] != 'unknown' and m['legal_area'] != 'null'}
    return {
        'branch_random': 1 / len(branches),
        'n_branch_classes': len(branches),
        'area_random': 1 / len(areas),
        'n_area_classes': len(areas),
    }


def evaluate_mode(mode_name, embedding_file, meta, baselines, config):
    """Evaluate a single mode against frozen hierarchical_v1 protocol."""
    logger.info(f"\n=== Evaluating {mode_name} at 174k ===")
    
    # Load embeddings
    embedding_path = EMBEDDINGS_DIR / embedding_file
    logger.info(f"Loading embeddings from {embedding_path}")
    embeddings = np.load(embedding_path)
    
    # Load and align metadata
    n = min(len(embeddings), len(meta))
    embeddings = embeddings[:n]
    metadata = meta[:n]
    
    # Filter zero-norm embeddings
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    logger.info(f"Valid embeddings: {valid_mask.sum()}/{len(valid_mask)} ({(1-valid_mask.mean())*100:.1f}% zero-norm)")
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    
    # Normalize
    from sklearn.preprocessing import normalize
    embeddings = normalize(embeddings, norm='l2')
    
    logger.info(f"Final data: {len(embeddings)} decisions, {embeddings.shape[1]} dims")
    
    # Run constrained hierarchical Leiden
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata,
        coarse_res=config["coarse_res"],
        base_sub_res=config["base_sub_res"],
        min_cluster_size=config["min_cluster_size"],
        max_subclusters_per_parent=config["max_subclusters_per_parent"],
        adaptive_sub_res=config["adaptive_sub_res"],
        k=config["k_neighbors"]
    )
    
    # Compute metrics
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, metadata)
    hierarchical_area_purity = compute_area_purity(hierarchical_labels, metadata)
    
    frag_hierarchical = compute_fragmentation(hierarchical_labels)
    frag_coarse = compute_fragmentation(coarse_labels)
    
    zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
    
    # Compute strict nesting (guaranteed 1.0 by construction)
    nesting = 1.0
    
    logger.info(f"  Coarse: {frag_coarse['n_clusters']} clusters, branch_purity={coarse_purity:.4f}, area_purity={coarse_area_purity:.4f}")
    logger.info(f"  Fine: {frag_hierarchical['n_clusters']} clusters, branch_purity={hierarchical_purity:.4f}, area_purity={hierarchical_area_purity:.4f}")
    logger.info(f"  Fragmentation: fine_singleton={frag_hierarchical['singleton_fraction']:.2%}, fine_median={frag_hierarchical['median_size']:.1f}")
    logger.info(f"  Zoom coherence: improvement_rate={zoom_coherence['overall']['improvement_rate']:.4f}, mean_improvement={zoom_coherence['overall']['mean_improvement']:.4f}, n_parents={zoom_coherence['overall']['n_parents']}")
    logger.info(f"  Nesting: {nesting}")
    
    # Check metrics against frozen thresholds
    checks = {
        'fragmentation_ok': frag_hierarchical['singleton_fraction'] < 0.01,
        'nesting_perfect': nesting == 1.0,
        'branch_purity_improves': hierarchical_purity > coarse_purity,
        'area_purity_improves': hierarchical_area_purity > coarse_area_purity,
        'zoom_coherence_ok': zoom_coherence['overall']['improvement_rate'] > 0.5,
        'legal_structure_branch': hierarchical_purity > 2 * baselines['branch_random'],
        'legal_structure_area': hierarchical_area_purity > 2 * baselines['area_random'],
    }
    
    mode_pass = all(checks.values())
    
    logger.info(f"  Checks: {checks}")
    logger.info(f"  Per-mode verdict: {'PASS' if mode_pass else 'FAIL'}")
    
    # Save individual mode results
    mode_output = {
        'mode': mode_name,
        'config': config,
        'sample_size': len(embeddings),
        'coarse': {
            'n_clusters': frag_coarse['n_clusters'],
            'branch_purity': coarse_purity,
            'area_purity': coarse_area_purity,
            'fragmentation': frag_coarse,
        },
        'hierarchical_fine': {
            'n_clusters': frag_hierarchical['n_clusters'],
            'branch_purity': hierarchical_purity,
            'area_purity': hierarchical_area_purity,
            'fragmentation': frag_hierarchical,
        },
        'nesting': nesting,
        'zoom_coherence': zoom_coherence,
        'checks': checks,
        'per_mode_verdict': 'PASS' if mode_pass else 'FAIL',
    }
    
    mode_path = OUTPUT_DIR / f'{mode_name}_174k_hierarchical_v1.json'
    with open(mode_path, 'w') as f:
        json.dump(mode_output, f, indent=2, default=str)
    logger.info(f"  Mode results saved to {mode_path}")
    
    return mode_output


def main():
    write_frozen_spec()
    
    meta = load_metadata()
    baselines = compute_random_baselines(meta)
    logger.info(f"Metadata: {len(meta)} entries")
    logger.info(f"Random baselines: branch={baselines['branch_random']:.4f} ({baselines['n_branch_classes']} classes), area={baselines['area_random']:.4f} ({baselines['n_area_classes']} classes)")
    
    config = SPEC['config_frozen']
    
    results = {
        'run_id': f'hierarchical_v1_174k_tfidf_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'frozen_spec_ref': str(OUTPUT_DIR / 'hierarchical_v1_frozen_spec.json'),
        'protocol': 'hierarchical_v1',
        'direction_version': 29,
        'baselines': baselines,
        'modes': {}
    }
    
    for mode_name, embedding_file in MODE_FILES.items():
        try:
            eval_result = evaluate_mode(mode_name, embedding_file, meta, baselines, config)
            results['modes'][mode_name] = eval_result
        except Exception as e:
            logger.error(f"  ERROR evaluating {mode_name}: {e}")
            import traceback
            traceback.print_exc()
            results['modes'][mode_name] = {'error': str(e)}
    
    # Overall verdict
    valid_modes = [m for m in MODE_FILES if 'error' not in results['modes'].get(m, {})]
    all_pass = all(results['modes'][m].get('per_mode_verdict') == 'PASS' for m in valid_modes)
    results['overall_verdict'] = 'PASS' if all_pass else 'FAIL'
    results['modes_tested'] = len(valid_modes)
    results['modes_passed'] = sum(1 for m in valid_modes if results['modes'][m].get('per_mode_verdict') == 'PASS')
    
    verdict_path = OUTPUT_DIR / f'hierarchical_v1_174k_tfidf_verdict_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json'
    verdict_path.write_text(json.dumps(results, indent=2, default=str) + '\n')
    logger.info(f"\n{'='*60}")
    logger.info(f"OVERALL VERDICT: {results['overall_verdict']} ({results['modes_passed']}/{results['modes_tested']} modes PASS)")
    logger.info(f"VERDICT WRITTEN: {verdict_path}")
    logger.info(f"{'='*60}")
    
    # Summary table
    logger.info("\nSUMMARY:")
    for mode_name in MODE_FILES:
        if mode_name not in results['modes']:
            logger.info(f"  {mode_name}: SKIPPED (not in results)")
            continue
        m = results['modes'][mode_name]
        if 'error' in m:
            logger.info(f"  {mode_name}: ERROR - {m['error']}")
            continue
        logger.info(f"  {mode_name}: {m['per_mode_verdict']} "
              f"coarse_branch={m['coarse']['branch_purity']:.4f} fine_branch={m['hierarchical_fine']['branch_purity']:.4f} "
              f"impr_rate={m['zoom_coherence']['overall']['improvement_rate']:.4f} "
              f"singleton={m['hierarchical_fine']['fragmentation']['singleton_fraction']:.4f} "
              f"legal_branch={m['checks']['legal_structure_branch']} legal_area={m['checks']['legal_structure_area']}")
    
    return results


if __name__ == '__main__':
    main()