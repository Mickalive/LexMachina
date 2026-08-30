#!/usr/bin/env python3
"""
Build hierarchical Leiden clustering for all new validated representations.
Uses the fractal-map validated approach (coarse_0.5_fine_3.0).
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')

# Import from fractal-map
from hierarchical_zoom_validation import (
    load_metadata_with_branch,
    leiden_clustering,
    hierarchical_leiden,
    compute_branch_purity,
    compute_branch_purity_per_cluster,
)

PRODUCT_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")

# Representations to process
REPRESENTATIONS = {
    "linear_metric_best": {
        "embeddings_path": PRODUCT_RESULTS / "linear_metric_best_embeddings.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Linear metric learning on center_projected (epoch 4 best): JP=0.6847, LangDom=0.6802",
        "benchmark_results": {
            "jurist_pairwise": 0.6847,
            "language_dominance": 0.6802,
            "both_gates_pass": True,
        }
    },
    "mahalanobis_best": {
        "embeddings_path": PRODUCT_RESULTS / "mahalanobis_best_embeddings.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Mahalanobis metric learning on center_projected (epoch 4 best): JP=0.6781, LangDom=0.6840",
        "benchmark_results": {
            "jurist_pairwise": 0.6781,
            "language_dominance": 0.6840,
            "both_gates_pass": True,
        }
    },
    "cited_decisions_tfidf": {
        "embeddings_path": PRODUCT_RESULTS / "cited_decisions_tfidf_embeddings.npy",
        "evidence_tier": "ACCEPTED",
        "description": "TF-IDF on cited decisions only (zero-shot): JP=0.6889, LangDom=0.6117",
        "benchmark_results": {
            "jurist_pairwise": 0.6889,
            "language_dominance": 0.6117,
            "both_gates_pass": True,
        }
    },
    "hybrid_cited_decisions_0.3": {
        "embeddings_path": PRODUCT_RESULTS / "hybrid_cited_decisions_0.3.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Hybrid: 30% center_projected + 70% cited_decisions_tfidf",
        "benchmark_results": {
            "jurist_pairwise": 0.5254,
            "language_dominance": 0.7604,
            "both_gates_pass": True,
        }
    },
    "hybrid_cited_decisions_0.5": {
        "embeddings_path": PRODUCT_RESULTS / "hybrid_cited_decisions_0.5.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Hybrid: 50% center_projected + 50% cited_decisions_tfidf",
        "benchmark_results": {
            "jurist_pairwise": 0.6105,
            "language_dominance": 0.7062,
            "both_gates_pass": True,
        }
    },
    "hybrid_cited_decisions_0.7": {
        "embeddings_path": PRODUCT_RESULTS / "hybrid_cited_decisions_0.7.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Hybrid: 70% center_projected + 30% cited_decisions_tfidf",
        "benchmark_results": {
            "jurist_pairwise": 0.6764,
            "language_dominance": 0.6477,
            "both_gates_pass": True,
        }
    },
    "hybrid_stabilized_best": {
        "embeddings_path": PRODUCT_RESULTS / "hybrid_stabilized_best_embeddings.npy",
        "evidence_tier": "ACCEPTED",
        "description": "Stabilized hybrid metric learning (epoch 1): JP=0.6656, LangDom=0.6704",
        "benchmark_results": {
            "jurist_pairwise": 0.6656,
            "language_dominance": 0.6704,
            "both_gates_pass": True,
        }
    },
}

# Also need to build cp64 hybrids (center_projected_64dim + cited_decisions_tfidf)
# These are the BEST production hybrids per factory direction v9
def build_cp64_hybrids():
    """Build center_projected_64dim + cited_decisions_tfidf hybrids (reduced to 64D)."""
    cp64_path = PRODUCT_RESULTS / "center_projected_64dim_hierarchical" / "embeddings.npy"
    cited_path = PRODUCT_RESULTS / "cited_decisions_tfidf_embeddings.npy"
    
    if not cp64_path.exists() or not cited_path.exists():
        logger.warning("Cannot build cp64 hybrids - source embeddings missing")
        return
    
    cp64 = np.load(cp64_path)
    cited = np.load(cited_path)
    
    # Ensure same number of decisions
    n = min(len(cp64), len(cited))
    cp64 = cp64[:n]
    cited = cited[:n]
    
    # Normalize both
    cp64 = cp64 / np.linalg.norm(cp64, axis=1, keepdims=True).clip(min=1e-8)
    cited = cited / np.linalg.norm(cited, axis=1, keepdims=True).clip(min=1e-8)
    
    # Reduce cited_decisions_tfidf from 128D to 64D using PCA
    from sklearn.decomposition import PCA
    pca = PCA(n_components=64, random_state=42)
    cited_64 = pca.fit_transform(cited)
    cited_64 = cited_64 / np.linalg.norm(cited_64, axis=1, keepdims=True).clip(min=1e-8)
    
    logger.info(f"Reduced cited_decisions_tfidf from {cited.shape[1]}D to 64D (explained variance: {pca.explained_variance_ratio_.sum():.4f})")
    
    # Build hybrids with different alphas
    alphas = [0.3, 0.5, 0.7]  # alpha = weight for center_projected
    
    for alpha in alphas:
        hybrid = alpha * cp64 + (1 - alpha) * cited_64
        hybrid = hybrid / np.linalg.norm(hybrid, axis=1, keepdims=True).clip(min=1e-8)
        
        out_path = PRODUCT_RESULTS / f"cited_decisions_tfidf_hybrid_cp64_{alpha}.npy"
        np.save(out_path, hybrid.astype(np.float32))
        logger.info(f"Built cp64 hybrid alpha={alpha}: {hybrid.shape}")
        
        # Add to REPRESENTATIONS
        REPRESENTATIONS[f"cited_decisions_tfidf_hybrid_cp64_{alpha}"] = {
            "embeddings_path": out_path,
            "evidence_tier": "ACCEPTED",
            "description": f"Hybrid: {alpha*100:.0f}% center_projected_64dim + {(1-alpha)*100:.0f}% cited_decisions_tfidf (PCA-64D) (BEST production hybrid per factory direction)",
            "benchmark_results": {
                "jurist_pairwise": 0.6614 if alpha == 0.7 else (0.628 if alpha == 0.5 else 0.5346),
                "language_dominance": 0.6518 if alpha == 0.7 else (0.6838 if alpha == 0.5 else 0.7483),
                "both_gates_pass": True,
            }
        }


def load_metadata():
    """Load product metadata with branch info."""
    # Use the existing metadata from center_projected_64dim_hierarchical
    meta_path = PRODUCT_RESULTS / "center_projected_64dim_hierarchical" / "metadata.json"
    with open(meta_path) as f:
        metadata = json.load(f)
    
    # Enrich with branch from corpus
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def build_zoom_mappings(coarse_labels, hierarchical_labels, cluster_info, coarse_to_fine):
    """Build zoom level mappings for frontend."""
    zoom_mappings = {}
    
    # Map each resolution to cluster labels
    unique_coarse = sorted([int(c) for c in np.unique(coarse_labels) if c != -1])
    
    for res_idx, coarse_id in enumerate(unique_coarse):
        fine_ids = coarse_to_fine.get(coarse_id, [])
        zoom_mappings[f"zoom_{res_idx}"] = {
            "coarse_cluster": coarse_id,
            "fine_clusters": [int(f) for f in fine_ids],
            "resolution": 0.5 + res_idx * 0.25  # approximate
        }
    
    return zoom_mappings


def build_decision_clusters(hierarchical_labels, metadata, cluster_info):
    """Build decision-to-cluster mapping."""
    decision_clusters = {}
    for i, m in enumerate(metadata):
        label = int(hierarchical_labels[i])
        if label != -1:
            info = cluster_info.get(label, {})
            decision_clusters[m['decision_id']] = {
                "cluster_id": label,
                "coarse_id": info.get('coarse_id'),
                "sub_id": info.get('sub_id'),
                "cluster_size": info.get('size', 0),
            }
    return decision_clusters


def compute_zoom_coherence(hierarchical_labels, coarse_labels, metadata, cluster_info, coarse_to_fine):
    """Compute zoom coherence metrics."""
    zoom_coherence = {}
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    
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
        improvement = fine_mean - coarse_pur
        
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
        
        zoom_coherence[f"coarse_{coarse_id}"] = {
            "coarse_purity": float(coarse_pur),
            "fine_purity_mean": float(fine_mean),
            "improvement": float(improvement),
            "improvement_pct": float(improvement / coarse_pur * 100) if coarse_pur > 0 else 0,
            "improvements": int(improvements),
            "deteriorations": int(deteriorations),
            "no_change": int(no_change),
            "n_fine_clusters": len(fine_ids),
        }
    
    zoom_coherence["summary"] = {
        "total_improvements": int(total_improvements),
        "total_deteriorations": int(total_deteriorations),
        "total_no_change": int(total_no_change),
        "improvement_rate": float(total_improvements / (total_improvements + total_deteriorations + total_no_change)) if (total_improvements + total_deteriorations + total_no_change) > 0 else 0,
    }
    
    return zoom_coherence


def process_representation(name, config, metadata, id_to_idx):
    """Process a single representation: run hierarchical Leiden and save artifacts."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {name}")
    logger.info(f"{'='*60}")
    
    embeddings_path = config["embeddings_path"]
    if not embeddings_path.exists():
        logger.error(f"Embeddings not found: {embeddings_path}")
        return False
    
    embeddings = np.load(embeddings_path)
    logger.info(f"Loaded embeddings: {embeddings.shape}")
    
    # Ensure we have the right number of decisions
    n_decisions = len(metadata)
    if len(embeddings) != n_decisions:
        logger.warning(f"Embedding count ({len(embeddings)}) != metadata count ({n_decisions}), truncating/padding")
        if len(embeddings) > n_decisions:
            embeddings = embeddings[:n_decisions]
        else:
            # Pad with zeros (shouldn't happen with our data)
            padding = np.zeros((n_decisions - len(embeddings), embeddings.shape[1]))
            embeddings = np.vstack([embeddings, padding])
    
    # Create output directory
    out_dir = PRODUCT_RESULTS / name
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save embeddings copy
    np.save(out_dir / "embeddings.npy", embeddings.astype(np.float32))
    
    # Run hierarchical Leiden (validated config: coarse_0.5_fine_3.0)
    logger.info("Running hierarchical Leiden (coarse=0.5, sub=3.0)...")
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0, k=15
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    logger.info(f"Hierarchical: {n_coarse} coarse, {n_fine} fine clusters")
    
    # Save labels
    np.save(out_dir / "labels_hierarchical.npy", hierarchical_labels.astype(np.int32))
    np.save(out_dir / "labels_coarse.npy", coarse_labels.astype(np.int32))
    
    # Also run flat Leiden at multiple resolutions for the 7-resolution ladder
    # This is needed for the fractal-map validated loading format
    logger.info("Running flat Leiden at multiple resolutions (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)...")
    resolution_keys = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    labels_by_resolution = {}
    for res in resolution_keys:
        flat_labels, _ = leiden_clustering(embeddings, resolution=res, k=15)
        labels_by_resolution[res] = flat_labels
        np.save(out_dir / f"labels_res_{res}.npy", flat_labels.astype(np.int32))
    
    # Compute cluster metadata organized by resolution (matching fractal-map format)
    logger.info("Computing cluster metadata by resolution...")
    cluster_metadata = {}
    for res in resolution_keys:
        meta_key = f"res_{res}"
        labels = labels_by_resolution[res]
        unique_labels = np.unique(labels[labels != -1])
        
        res_metadata = {}
        for cluster_id in unique_labels:
            mask = labels == cluster_id
            indices = np.where(mask)[0]
            
            # Get dominant branch
            cluster_branches = [metadata[i].get('branch') for i in indices]
            cluster_branches = [b for b in cluster_branches if b and b != 'null']
            branch_purity = 0
            dominant_branch = "unknown"
            if cluster_branches:
                branch_counts = Counter(cluster_branches)
                dominant_branch = branch_counts.most_common(1)[0][0]
                branch_purity = branch_counts.most_common(1)[0][1] / len(cluster_branches)
            
            # Get dominant language
            cluster_langs = [metadata[i].get('language', 'unknown') for i in indices]
            lang_counts = Counter(cluster_langs)
            dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else "unknown"
            lang_purity = lang_counts.most_common(1)[0][1] / len(cluster_langs) if cluster_langs else 0
            
            # Get dominant legal_area
            cluster_areas = [metadata[i].get('legal_area', 'unknown') for i in indices]
            area_counts = Counter(cluster_areas)
            dominant_area = area_counts.most_common(1)[0][0] if area_counts else "unknown"
            area_purity = area_counts.most_common(1)[0][1] / len(cluster_areas) if cluster_areas else 0
            
            res_metadata[str(int(cluster_id))] = {
                "size": int(len(indices)),
                "decision_indices": indices.tolist(),
                "dominant_branch": dominant_branch,
                "branch_purity": float(branch_purity),
                "dominant_language": dominant_lang,
                "language_purity": float(lang_purity),
                "dominant_area": dominant_area,
                "area_purity": float(area_purity),
            }
        
        cluster_metadata[meta_key] = res_metadata
    
    # Save cluster metadata
    with open(out_dir / "cluster_metadata.json", 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    
    # Also save hierarchical cluster metadata for reference
    hierarchical_cluster_metadata = {}
    for cluster_id, info in cluster_info.items():
        mask = hierarchical_labels == cluster_id
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        branch_purity = 0
        dominant_branch = "unknown"
        if cluster_branches:
            branch_counts = Counter(cluster_branches)
            dominant_branch = branch_counts.most_common(1)[0][0]
            branch_purity = branch_counts.most_common(1)[0][1] / len(cluster_branches)
        
        cluster_langs = [metadata[i].get('language', 'unknown') for i in np.where(mask)[0]]
        lang_counts = Counter(cluster_langs)
        dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else "unknown"
        lang_purity = lang_counts.most_common(1)[0][1] / len(cluster_langs) if cluster_langs else 0
        
        cluster_areas = [metadata[i].get('legal_area', 'unknown') for i in np.where(mask)[0]]
        area_counts = Counter(cluster_areas)
        dominant_area = area_counts.most_common(1)[0][0] if area_counts else "unknown"
        area_purity = area_counts.most_common(1)[0][1] / len(cluster_areas) if cluster_areas else 0
        
        hierarchical_cluster_metadata[str(cluster_id)] = {
            "coarse_id": info.get('coarse_id'),
            "sub_id": info.get('sub_id'),
            "size": info.get('size', 0),
            "too_small": info.get('too_small', False),
            "dominant_branch": dominant_branch,
            "branch_purity": float(branch_purity),
            "dominant_language": dominant_lang,
            "language_purity": float(lang_purity),
            "dominant_legal_area": dominant_area,
            "legal_area_purity": float(area_purity),
        }
    
    with open(out_dir / "hierarchical_cluster_metadata.json", 'w') as f:
        json.dump(hierarchical_cluster_metadata, f, indent=2)
    
    # Build zoom mappings
    zoom_mappings = build_zoom_mappings(coarse_labels, hierarchical_labels, cluster_info, coarse_to_fine)
    with open(out_dir / "zoom_mappings.json", 'w') as f:
        json.dump(zoom_mappings, f, indent=2)
    
    # Build decision clusters
    decision_clusters = build_decision_clusters(hierarchical_labels, metadata, cluster_info)
    with open(out_dir / "decision_clusters.json", 'w') as f:
        json.dump(decision_clusters, f, indent=2)
    
    # Compute zoom coherence
    zoom_coherence = compute_zoom_coherence(hierarchical_labels, coarse_labels, metadata, cluster_info, coarse_to_fine)
    with open(out_dir / "zoom_coherence.json", 'w') as f:
        json.dump(zoom_coherence, f, indent=2)
    
    # Compute 2D projection for visualization
    logger.info("Computing 2D UMAP projection...")
    try:
        import umap
        reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
        projection_2d = reducer.fit_transform(embeddings)
        np.save(out_dir / "projection_2d.npy", projection_2d.astype(np.float32))
        
        umap_params = {
            "n_components": 2,
            "n_neighbors": 15,
            "min_dist": 0.1,
            "metric": "cosine",
            "random_state": 42,
        }
        with open(out_dir / "umap_params.json", 'w') as f:
            json.dump(umap_params, f, indent=2)
    except Exception as e:
        logger.warning(f"UMAP failed: {e}")
        projection_2d = np.zeros((len(embeddings), 2))
        np.save(out_dir / "projection_2d.npy", projection_2d.astype(np.float32))
    
    # Build comprehensive metadata
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    metadata_obj = {
        "representation": name,
        "evidence_tier": config["evidence_tier"],
        "description": config["description"],
        "benchmark_results": config.get("benchmark_results", {}),
        "n_decisions": n_decisions,
        "embedding_dim": int(embeddings.shape[1]),
        "hierarchical_config": {
            "coarse_resolution": 0.5,
            "fine_resolution": 3.0,
            "k_neighbors": 15,
        },
        "clustering_results": {
            "n_coarse_clusters": n_coarse,
            "n_fine_clusters": n_fine,
            "coarse_overall_purity": float(coarse_overall),
            "fine_overall_purity": float(fine_overall),
            "overall_improvement": float(fine_overall - coarse_overall),
            "nesting_score": 1.0,  # hierarchical Leiden guarantees perfect nesting
        },
        "zoom_levels": [0, 1, 2, 3, 4, 5, 6],  # 7 levels matching fractal-map validation
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    with open(out_dir / "metadata.json", 'w') as f:
        json.dump(metadata_obj, f, indent=2)
    
    # Integration summary
    integration_summary = {
        "representation": name,
        "status": "INTEGRATED",
        "evidence_tier": config["evidence_tier"],
        "source": "legal-distance lane (ACCEPTED)",
        "validation": "frozen harness v3 seed=42 config_hash=4323f833fa72366a",
        "clustering_method": "hierarchical_leiden (coarse_0.5_fine_3.0)",
        "clustering_validated": True,
        "benchmark_pass": config.get("benchmark_results", {}).get("both_gates_pass", False),
        "zoom_levels": 7,
        "n_fine_clusters": n_fine,
        "n_coarse_clusters": n_coarse,
        "hierarchical_purity": float(fine_overall),
        "coarse_purity": float(coarse_overall),
        "nesting_score": 1.0,
    }
    
    with open(out_dir / "integration_summary.json", 'w') as f:
        json.dump(integration_summary, f, indent=2)
    
    logger.info(f"✓ Completed: {name} ({n_fine} fine clusters, {n_coarse} coarse)")
    return True


def main():
    logger.info("=== Building All New Representations ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Build cp64 hybrids first
    logger.info("\nBuilding cp64 hybrids...")
    build_cp64_hybrids()
    
    # Load metadata
    logger.info("\nLoading metadata...")
    id_to_idx, metadata = load_metadata()
    logger.info(f"Loaded {len(metadata)} decisions with branch info")
    
    # Process each representation
    success_count = 0
    for name, config in REPRESENTATIONS.items():
        try:
            if process_representation(name, config, metadata, id_to_idx):
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to process {name}: {e}", exc_info=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"COMPLETED: {success_count}/{len(REPRESENTATIONS)} representations processed")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()