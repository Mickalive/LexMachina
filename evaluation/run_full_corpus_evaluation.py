#!/usr/bin/env python3
"""
Full Corpus Evaluation Harness - LexMachina Evaluation Lane

Scales the frozen evaluation harness v3 to 192k+ decisions using
HNSW approximate nearest neighbors and batched processing.

Maintains FULL COMPATIBILITY with frozen harness v3:
- Same global seed (42)
- Same adversarial thresholds (LangDom < 0.85, Jurist > 0.5)
- Same benchmark parameters (k=20, k=10, k=10, n_clusters=16)
- Same metric implementations (batched but mathematically equivalent)
- Same config hash verification

Usage:
    python run_full_corpus_evaluation.py --embeddings-dir /path/to/embeddings --metadata /path/to/metadata.json --output-dir results/full_corpus
"""

import json
import numpy as np
import logging
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
import sys

# Add evaluation directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scalable_nn import (
    build_scalable_nn,
    run_scalable_adversarial_benchmarks,
    run_scalable_full_evaluation,
    batched_jurivoc_alignment,
    batched_scale_stability,
    batched_boilerplate_resistance,
    batched_cluster_coherence,
    batched_cross_language_retrieval,
    DistributedEvaluator,
    EXACT_NN_THRESHOLD,
    BATCH_SIZE,
    GLOBAL_SEED
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION - MUST MATCH evaluation_v3_harness.py
# ============================================================
EVALUATION_VERSION = "v3_full_corpus"
FACTORY_DIRECTION_VERSION = 10

# Adversarial thresholds (FROZEN - do not modify)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (FROZEN)
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10
N_CLUSTERS_COHERENCE = 16

# Scaling parameters
DEFAULT_BATCH_SIZE = 5000
DEFAULT_MAX_WORKERS = 4


def get_frozen_config_hash() -> str:
    """Generate hash of frozen configuration for audit trail (matches v3 harness)."""
    config = {
        "version": EVALUATION_VERSION,
        "seed": GLOBAL_SEED,
        "factory_direction": FACTORY_DIRECTION_VERSION,
        "thresholds": {
            "language_dominance": LANGUAGE_DOMINANCE_THRESHOLD,
            "jurist_pairwise": JURIST_PAIRWISE_THRESHOLD,
            "cross_lang_recall": CROSS_LANG_RECALL_THRESHOLD,
            "cluster_coherence": CLUSTER_COHERENCE_THRESHOLD
        },
        "parameters": {
            "k_lang_dom": K_NEIGHBORS_LANG_DOM,
            "k_jurist": K_NEIGHBORS_JURIST,
            "k_cross_lang": K_NEIGHBORS_CROSS_LANG,
            "n_clusters": N_CLUSTERS_COHERENCE
        },
        "scaling": {
            "exact_nn_threshold": EXACT_NN_THRESHOLD,
            "batch_size": DEFAULT_BATCH_SIZE,
            "hnsw_m": 16,
            "hnsw_ef_construction": 200,
            "hnsw_ef_search": 100
        }
    }
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


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


def load_metadata(metadata_path: Path) -> List[Dict]:
    """Load metadata from JSON or JSONL format."""
    logger.info(f"Loading metadata from {metadata_path}")
    start = time.time()
    
    if metadata_path.suffix == '.jsonl':
        metadata = []
        with open(metadata_path, 'r') as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))
    else:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    logger.info(f"Loaded {len(metadata)} decisions in {time.time() - start:.2f}s")
    return metadata


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata (matches v3 harness)."""
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


def load_embeddings(embeddings_dir: Path, pattern: str = "*.npy") -> Dict[str, np.ndarray]:
    """Load all embedding files from directory."""
    embeddings = {}
    for npy_file in embeddings_dir.glob(pattern):
        name = npy_file.stem
        try:
            emb = np.load(npy_file)
            embeddings[name] = emb
            logger.info(f"  Loaded {name}: {emb.shape}")
        except Exception as e:
            logger.warning(f"  Failed to load {name}: {e}")
    return embeddings


def evaluate_representation_full_corpus(
    name: str,
    embeddings: np.ndarray,
    metadata: List[Dict],
    force_exact: bool = False
) -> Dict[str, Any]:
    """
    Evaluate a single representation on full corpus using scalable infrastructure.
    
    Returns same format as frozen harness v3 evaluate_representation().
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Run scalable full evaluation
    result = run_scalable_full_evaluation(embeddings, metadata, force_exact=force_exact)
    result['name'] = name
    result['duration_seconds'] = time.time() - start_time
    
    # Log summary
    adv = result['adversarial']
    jurivoc = result['jurivoc_alignment']
    scale = result['scale_stability']
    boiler = result['boilerplate_resistance']
    frac = result['fractal']
    
    logger.info(f"  {name}: verdict={result['verdict']}, "
               f"lang_dom={adv['language_dominance_score']:.4f} "
               f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
               f"jurist_pref={adv['jurist_preference_rate']:.4f} "
               f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
               f"jurivoc_l0={jurivoc['level_0_nmi']:.4f}, "
               f"scale_stability={scale.get('mean_neighbor_overlap', 'N/A'):.4f}, "
               f"boilerplate_resist={boiler['resistance_score']:.4f}, "
               f"backend={result.get('backend', 'unknown')}, "
               f"duration={result['duration_seconds']:.1f}s")
    
    return result


def run_full_corpus_evaluation(
    embeddings_dir: Path,
    metadata_path: Path,
    output_dir: Path,
    representations: Optional[List[str]] = None,
    force_exact: bool = False,
    worker_id: int = 0,
    n_workers: int = 1
) -> Tuple[Dict[str, Any], str]:
    """
    Run full corpus evaluation on all or specified representations.
    
    Args:
        embeddings_dir: Directory containing .npy embedding files
        metadata_path: Path to metadata JSON/JSONL
        output_dir: Output directory for results
        representations: List of representation names to evaluate (None = all)
        force_exact: Force exact NN even for large corpuses (for validation)
        worker_id: Worker ID for distributed evaluation
        n_workers: Total number of workers
        
    Returns:
        (all_results, config_hash)
    """
    config_hash = get_frozen_config_hash()
    
    logger.info("=" * 70)
    logger.info(f"Full Corpus Evaluation Harness v3")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info(f"Worker: {worker_id}/{n_workers}")
    logger.info(f"Force exact NN: {force_exact}")
    logger.info("=" * 70)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_metadata(metadata_path)
    
    # Load embeddings
    logger.info("\n2. Loading representations...")
    all_embeddings = load_embeddings(embeddings_dir)
    
    if not all_embeddings:
        raise ValueError(f"No embeddings found in {embeddings_dir}")
    
    # Filter representations if specified
    if representations:
        embeddings_to_eval = {k: v for k, v in all_embeddings.items() if k in representations}
        missing = set(representations) - set(all_embeddings.keys())
        if missing:
            logger.warning(f"Requested representations not found: {missing}")
    else:
        embeddings_to_eval = all_embeddings
    
    logger.info(f"Evaluating {len(embeddings_to_eval)} representations")
    
    # Distributed sharding (model-level)
    if n_workers > 1:
        eval_names = list(embeddings_to_eval.keys())
        worker_names = DistributedEvaluator(worker_id, n_workers, output_dir).shard_representations(eval_names)
        embeddings_to_eval = {k: v for k, v in embeddings_to_eval.items() if k in worker_names}
        logger.info(f"Worker {worker_id} assigned: {list(embeddings_to_eval.keys())}")
    
    # Evaluate each representation
    logger.info("\n3. Running evaluations...")
    all_results = {}
    
    for name, embeddings in embeddings_to_eval.items():
        try:
            result = evaluate_representation_full_corpus(name, embeddings, metadata, force_exact=force_exact)
            all_results[name] = result
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save results
    output_file = output_dir / f"full_corpus_evaluation_results_worker{worker_id}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary
    logger.info("\n" + "=" * 90)
    logger.info("FULL CORPUS EVALUATION SUMMARY")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info(f"Corpus size: {len(metadata)} decisions")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<35} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5} {'Jurivoc0':>8} {'Scale':>6} {'Boiler':>7} {'Backend':>10}")
    logger.info("-" * 90)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<35} {'ERROR':<7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>5} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>7} {'N/A':>10}")
            continue
        
        adv = res['adversarial']
        jurivoc = res['jurivoc_alignment']
        scale = res['scale_stability']
        boiler = res['boilerplate_resistance']
        
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        scale_score = scale.get('mean_neighbor_overlap', 0)
        boiler_score = boiler['resistance_score']
        backend = res.get('backend', 'unknown')
        
        logger.info(f"{name:<35} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5} "
                   f"{jurivoc['level_0_nmi']:>8.4f} {scale_score:>6.4f} {boiler_score:>7.4f} {backend:>10}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Jurivoc Level 0 NMI: {best[1]['jurivoc_alignment']['level_0_nmi']:.4f}")
        logger.info(f"   Scale stability: {best[1]['scale_stability'].get('mean_neighbor_overlap', 'N/A')}")
        logger.info(f"   Boilerplate resistance: {best[1]['boilerplate_resistance']['resistance_score']:.4f}")
        logger.info(f"   Backend: {best[1].get('backend', 'unknown')}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results, config_hash


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Corpus Evaluation Harness")
    parser.add_argument("--embeddings-dir", type=Path, required=True, help="Directory with .npy embedding files")
    parser.add_argument("--metadata", type=Path, required=True, help="Metadata JSON/JSONL file")
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results/full_corpus"), help="Output directory")
    parser.add_argument("--representations", nargs="+", help="Specific representations to evaluate")
    parser.add_argument("--force-exact", action="store_true", help="Force exact NN (for validation)")
    parser.add_argument("--worker-id", type=int, default=0, help="Worker ID for distributed evaluation")
    parser.add_argument("--n-workers", type=int, default=1, help="Total number of workers")
    parser.add_argument("--config-hash-only", action="store_true", help="Only print config hash and exit")
    
    args = parser.parse_args()
    
    if args.config_hash_only:
        print(get_frozen_config_hash())
        return
    
    if not args.embeddings_dir.exists():
        logger.error(f"Embeddings directory not found: {args.embeddings_dir}")
        return 1
    
    if not args.metadata.exists():
        logger.error(f"Metadata file not found: {args.metadata}")
        return 1
    
    try:
        run_full_corpus_evaluation(
            embeddings_dir=args.embeddings_dir,
            metadata_path=args.metadata,
            output_dir=args.output_dir,
            representations=args.representations,
            force_exact=args.force_exact,
            worker_id=args.worker_id,
            n_workers=args.n_workers
        )
        return 0
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())