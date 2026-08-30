#!/usr/bin/env python3
"""
Build Missing Fractal Map Modes for Factory Direction v9.

Extends the validated hierarchical Leiden map to ALL 12 breakthrough representations:
- Metric Learning family: linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1
- Citation/Outcome family: cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7
- Citation Role family: following_alpha0.3, criticizing_alpha0.3, citing_alpha0.3
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Import Leiden clustering from existing code
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hierarchical.hierarchical_map_builder import leiden_clustering

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_BASE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/legal_distance_modes")

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

# Missing modes configuration
MISSING_MODES = {
    "hybrid_stabilized_epoch1": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/hybrid_objective_stabilized/final_embeddings.npy"),
        "description": "Metric Learning (Hybrid Stabilized Epoch 1) - HIGH PURITY pattern. Fine=0.9638, NMI=0.5788, ImpRate=73.8%. 128-dim embeddings.",
        "legal_distance_config": {"type": "metric_learning", "config": {"method": "hybrid_stabilized", "base_embedding": "center_projected_64dim", "epoch": 1, "objective": "jurist_pairwise"}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.6656, "language_dominance": 0.660, "hierarchical_purity": 0.9638},
        "subset_first_n": 1000,  # First 1000 of 1200
    },
    "cited_decisions_tfidf_outcome_hybrid_0.5": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids/cited_decisions_tfidf_outcome_hybrid_0.5.npy"),
        "description": "Cited Decisions TF-IDF + Outcome Hybrid α=0.5 - BEST PRODUCTION. ImpRate=86.8%, HierAdv=+0.2918. LangDom=0.4911, JP=0.7990. 2-dim embeddings.",
        "legal_distance_config": {"type": "hybrid", "config": {"alpha": 0.5, "cited_decisions_weight": 0.5, "outcome_weight": 0.5, "boilerplate_suppression": True}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.799, "language_dominance": 0.4911, "hierarchical_purity": 0.868},
        "subset_first_n": 1000,
    },
    "cited_decisions_tfidf_outcome_hybrid_0.7": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids/cited_decisions_tfidf_outcome_hybrid_0.7.npy"),
        "description": "Cited Decisions TF-IDF + Outcome Hybrid α=0.7 - BEST FRACTAL. ImpRate=90.3%, HierAdv=+0.3703. LangDom=0.4907, JP=0.7907. 2-dim embeddings.",
        "legal_distance_config": {"type": "hybrid", "config": {"alpha": 0.7, "cited_decisions_weight": 0.7, "outcome_weight": 0.3, "boilerplate_suppression": True}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.7907, "language_dominance": 0.4907, "hierarchical_purity": 0.903},
        "subset_first_n": 1000,
    },
    "following_alpha0.3": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_following_rebuilt.npy"),
        "description": "Citation Role: Following (α=0.3) - HIGH ADVANTAGE pattern. ImpRate=82.2%, Fine=0.9501. 64-dim embeddings.",
        "legal_distance_config": {"type": "citation_role", "config": {"role": "following", "alpha": 0.3}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.5188, "language_dominance": 0.753, "hierarchical_purity": 0.9501},
        "subset_first_n": None,  # Already 1000
    },
    "criticizing_alpha0.3": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_criticizing_rebuilt.npy"),
        "description": "Citation Role: Criticizing (α=0.3) - HIGH ADVANTAGE pattern. Fine=0.9619, HierAdv=+0.0815. 64-dim embeddings.",
        "legal_distance_config": {"type": "citation_role", "config": {"role": "criticizing", "alpha": 0.3}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.5004, "language_dominance": 0.7676, "hierarchical_purity": 0.9619},
        "subset_first_n": None,
    },
    "citing_alpha0.3": {
        "embedding_path": Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_citing_rebuilt.npy"),
        "description": "Citation Role: Citing (α=0.3) - ImpRate=66.9%. 64-dim embeddings.",
        "legal_distance_config": {"type": "citation_role", "config": {"role": "citing", "alpha": 0.3}},
        "benchmark_results": {"summary": {"total_benchmarks": 14, "passed": 14, "failed": 0}, "adversarial_both_pass": True, "jurist_preference": 0.5363, "language_dominance": 0.7414, "hierarchical_purity": 0.9203},
        "subset_first_n": None,
    },
}


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def compute_cluster_metadata(labels: np.ndarray, metadata: List[Dict]) -> Dict:
    """Compute rich metadata for each cluster."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        
        # Language distribution
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if indices.size > 0 else 0
        
        # Branch distribution
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if indices.size > 0 else 0
        
        # Legal area distribution
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        # Year distribution
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        
        # Chamber distribution
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': float(lang_purity),
            'dominant_branch': dominant_branch[0],
            'branch_purity': float(branch_purity),
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_indices': indices.tolist(),
        }
    
    return cluster_info


def build_parent_child_mapping(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> Tuple[Dict, Dict]:
    """Build parent-child mapping between two resolution levels."""
    fine_unique = np.unique(labels_fine[labels_fine != -1])
    child_to_parent = {}
    
    for fine_id in fine_unique:
        fine_mask = labels_fine == fine_id
        parent_labels = labels_coarse[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        
        if len(parent_labels_valid) > 0:
            parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
            child_to_parent[int(fine_id)] = int(parent_id)
        else:
            child_to_parent[int(fine_id)] = -1
    
    # Build inverse mapping
    parent_to_children = defaultdict(list)
    for child, parent in child_to_parent.items():
        parent_to_children[parent].append(child)
    
    return child_to_parent, dict(parent_to_children)


def compute_zoom_coherence(labels_coarse: np.ndarray, labels_fine: np.ndarray, metadata: List[Dict]) -> Dict:
    """Compute zoom coherence: does branching reveal more specific legal structure?"""
    coarse_unique = np.unique(labels_coarse[labels_coarse != -1])
    results = {}
    
    for coarse_id in coarse_unique:
        coarse_mask = labels_coarse == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        
        if len(coarse_indices) == 0:
            continue
        
        # Coarse cluster metadata
        coarse_meta = [metadata[i] for i in coarse_indices]
        coarse_branches = Counter(m.get('branch') for m in coarse_meta if m.get('branch'))
        coarse_dom = coarse_branches.most_common(1)[0] if coarse_branches else (None, 0)
        coarse_purity = coarse_dom[1] / len(coarse_indices) if coarse_indices.size > 0 else 0
        
        # Fine clusters within this coarse cluster
        fine_labels_in_coarse = labels_fine[coarse_indices]
        fine_unique = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        
        fine_purities = []
        fine_improvements = 0
        fine_deteriorations = 0
        fine_no_change = 0
        
        for fine_id in fine_unique:
            fine_mask = labels_fine == fine_id
            fine_indices = np.where(fine_mask)[0]
            
            fine_meta = [metadata[i] for i in fine_indices]
            fine_branches = Counter(m.get('branch') for m in fine_meta if m.get('branch'))
            fine_dom = fine_branches.most_common(1)[0] if fine_branches else (None, 0)
            fine_purity = fine_dom[1] / len(fine_indices) if fine_indices.size > 0 else 0
            
            fine_purities.append(fine_purity)
            
            if fine_purity > coarse_purity + 0.01:
                fine_improvements += 1
            elif fine_purity < coarse_purity - 0.01:
                fine_deteriorations += 1
            else:
                fine_no_change += 1
        
        mean_fine_purity = np.mean(fine_purities) if fine_purities else 0
        
        results[int(coarse_id)] = {
            'size': int(len(coarse_indices)),
            'coarse_purity': float(coarse_purity),
            'dominant_branch': coarse_dom[0],
            'fine_mean_purity': float(mean_fine_purity),
            'improvement': float(mean_fine_purity - coarse_purity),
            'improvement_pct': float((mean_fine_purity - coarse_purity) / coarse_purity * 100) if coarse_purity > 0 else 0,
            'n_fine_clusters': len(fine_unique),
            'improvements': fine_improvements,
            'deteriorations': fine_deteriorations,
            'no_change': fine_no_change,
        }
    
    return results


def build_decision_clusters(labels_dict: Dict[float, np.ndarray], metadata: List[Dict]) -> Dict:
    """Build decision-to-cluster index for fast lookups."""
    decision_clusters = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        decision_clusters[did] = {}
        for res, labels in labels_dict.items():
            decision_clusters[did][f"res_{res}"] = int(labels[i])
    
    return decision_clusters


def build_mode(mode_id: str, config: Dict, force: bool = False) -> bool:
    """Build a legal-distance map mode."""
    output_dir = OUTPUT_BASE_DIR / mode_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if embeddings exist
    embedding_path = config["embedding_path"]
    if not embedding_path.exists():
        logger.error(f"Embeddings not found: {embedding_path}")
        return False
    
    # Check if already built
    summary_path = output_dir / "integration_summary.json"
    if summary_path.exists() and not force:
        logger.info(f"Mode {mode_id} already built. Use --force to rebuild.")
        return True
    
    logger.info(f"=== Building map mode: {mode_id} ===")
    
    # Load embeddings
    logger.info(f"Loading embeddings from {embedding_path}")
    embeddings = np.load(embedding_path)
    logger.info(f"Original embeddings shape: {embeddings.shape}")
    
    # Subset if needed
    subset_n = config.get("subset_first_n")
    if subset_n is not None and embeddings.shape[0] > subset_n:
        embeddings = embeddings[:subset_n]
        logger.info(f"Subset to first {subset_n}: {embeddings.shape}")
    
    # Load metadata
    logger.info("Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    logger.info(f"Metadata: {len(metadata)} decisions")
    
    # Verify alignment
    if len(embeddings) != len(metadata):
        logger.error(f"Embedding count ({len(embeddings)}) != metadata count ({len(metadata)})")
        return False
    
    # Multi-resolution Leiden clustering
    logger.info("Running multi-resolution Leiden clustering...")
    labels_dict = {}
    hierarchy_info = {}
    
    for res in RESOLUTIONS:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        labels_dict[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': n_clusters,
            'modularity': float(modularity),
        }
        logger.info(f"  res={res}: {n_clusters} clusters, modularity={modularity:.4f}")
        
        # Save label array
        np.save(output_dir / f"labels_res_{res}.npy", labels)
    
    # Build cluster metadata at each resolution
    logger.info("Computing cluster metadata...")
    cluster_metadata = {}
    for res in RESOLUTIONS:
        cluster_metadata[f"res_{res}"] = compute_cluster_metadata(labels_dict[res], metadata)
    
    # Build parent-child mappings (zoom navigation)
    logger.info("Building zoom navigation...")
    zoom_mappings = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser = RESOLUTIONS[i]
        finer = RESOLUTIONS[i + 1]
        key = f"{coarser}_to_{finer}"
        child_to_parent, parent_to_children = build_parent_child_mapping(
            labels_dict[coarser], labels_dict[finer]
        )
        zoom_mappings[key] = {
            'coarser_resolution': coarser,
            'finer_resolution': finer,
            'child_to_parent': child_to_parent,
            'parent_to_children': parent_to_children,
        }
    
    # Compute zoom coherence
    logger.info("Computing zoom coherence...")
    zoom_coherence = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser = RESOLUTIONS[i]
        finer = RESOLUTIONS[i + 1]
        key = f"{coarser}_to_{finer}"
        zoom_coherence[key] = compute_zoom_coherence(
            labels_dict[coarser], labels_dict[finer], metadata
        )
    
    # Build decision clusters index
    logger.info("Building decision-to-cluster index...")
    decision_clusters = build_decision_clusters(labels_dict, metadata)
    
    # Save all artifacts
    logger.info("Saving artifacts...")
    
    with open(output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    
    with open(output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(zoom_mappings, f, indent=2)
    
    with open(output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(zoom_coherence, f, indent=2)
    
    with open(output_dir / "decision_clusters.json", 'w') as f:
        json.dump(decision_clusters, f, indent=2)
    
    # Integration summary
    summary = {
        'mode_id': mode_id,
        'description': config["description"],
        'n_decisions': len(metadata),
        'resolutions': RESOLUTIONS,
        'n_resolutions': len(RESOLUTIONS),
        'cluster_counts': {
            f"res_{res}": len(np.unique(labels_dict[res][labels_dict[res] != -1]))
            for res in RESOLUTIONS
        },
        'legal_distance_config': config["legal_distance_config"],
        'benchmark_results': config["benchmark_results"],
        'evidence_tier': 'ACCEPTED',
        'built_timestamp': datetime.now(timezone.utc).isoformat(),
    }
    
    with open(output_dir / "integration_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Create mode-specific integration spec
    spec = generate_mode_spec(mode_id, config, summary, cluster_metadata, zoom_mappings, zoom_coherence)
    with open(output_dir / "INTEGRATION_SPEC.md", 'w') as f:
        f.write(spec)
    
    logger.info(f"Mode {mode_id} built successfully at {output_dir}")
    return True


def generate_mode_spec(mode_id: str, config: Dict, summary: Dict, 
                       cluster_metadata: Dict, zoom_mappings: Dict, zoom_coherence: Dict) -> str:
    """Generate integration spec for a legal-distance mode."""
    spec = f"""# Legal-Distance Map Mode: {mode_id}

**Generated:** {datetime.now(timezone.utc).isoformat()}
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `{mode_id}`
**Description:** {config["description"]}

**Legal-Distance Config:** {json.dumps(config["legal_distance_config"], indent=2)}

**Benchmarks:** {config["benchmark_results"]["summary"]["passed"]}/{config["benchmark_results"]["summary"]["total_benchmarks"]} PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
"""
    for res in RESOLUTIONS:
        count = summary['cluster_counts'].get(f'res_{res}', 'N/A')
        spec += f"| {res} | {count} |\n"
    
    spec += f"""

---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/{mode_id}/`:

| Artifact | Path | Purpose |
|----------|------|---------|
| Cluster metadata | `cluster_metadata.json` | Legal context per cluster |
| Zoom mappings | `zoom_mappings.json` | Parent-child navigation |
| Zoom coherence | `zoom_coherence.json` | Validation metrics |
| Decision clusters | `decision_clusters.json` | Fast decision-to-cluster lookup |
| Label arrays | `labels_res_*.npy` | Rendering/visualization |

---

## 4. Product Integration

This mode is compatible with the unified `ProductMapLoader` API:

```python
from product_map_loader import ProductMapLoader

loader = ProductMapLoader()
artifacts = loader.load_mode("{mode_id}")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("{mode_id}", 1.0)
metadata = loader.get_cluster_metadata("{mode_id}", 0.5)
zoom = loader.get_zoom_mapping("{mode_id}", 0.5, 1.0)
```

---

## 5. Benchmark Results

{json.dumps(config["benchmark_results"], indent=2)}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
"""
    return spec


def build_all_missing_modes(force: bool = False) -> Dict[str, bool]:
    """Build all missing legal-distance map modes."""
    results = {}
    for mode_id, config in MISSING_MODES.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Building {mode_id}")
        logger.info(f"{'='*60}")
        results[mode_id] = build_mode(mode_id, config, force=force)
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build missing fractal map modes for factory direction v9")
    parser.add_argument("--mode", type=str, help="Specific mode to build")
    parser.add_argument("--all", action="store_true", help="Build all missing modes")
    parser.add_argument("--force", action="store_true", help="Force rebuild")
    
    args = parser.parse_args()
    
    if args.mode:
        if args.mode in MISSING_MODES:
            success = build_mode(args.mode, MISSING_MODES[args.mode], force=args.force)
            print(f"Build {'successful' if success else 'failed'}")
        else:
            print(f"Unknown mode: {args.mode}")
            print(f"Available modes: {list(MISSING_MODES.keys())}")
    
    elif args.all:
        results = build_all_missing_modes(force=args.force)
        print("\n=== Build Results ===")
        for mode_id, success in results.items():
            print(f"  {mode_id}: {'✅' if success else '❌'}")
        print(f"\nTotal successful: {sum(results.values())}/{len(results)}")
    
    else:
        print("=== Missing Fractal Map Modes Builder (Factory Direction v9) ===")
        print("Usage:")
        print("  --mode MODE_ID   Build specific mode")
        print("  --all            Build all missing modes")
        print("  --force          Force rebuild")
        print("\nMissing modes:")
        for mode_id in MISSING_MODES:
            print(f"  {mode_id}")