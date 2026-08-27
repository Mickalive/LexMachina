#!/usr/bin/env python3
"""
Multi-Resolution Structure Coherence Test

Tests whether the zoom hierarchy is legally meaningful:
1. Cluster nesting: Are finer clusters nested within coarser clusters?
2. Legal area consistency: Do legal areas remain coherent across zoom levels?
3. Language consistency: Does language remain consistent across zoom levels?
4. NMI between adjacent zoom levels

Evidence tier: EXPLORATORY
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from sklearn.metrics import normalized_mutual_info_score
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HIERARCHICAL_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/zoom_api")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load cluster labels and metadata."""
    # Load metadata
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    # Load multi-resolution Leiden labels
    with open(HIERARCHICAL_DIR / "leiden_multi_resolution.json") as f:
        leiden_data = json.load(f)
    
    # Extract labels for different resolutions
    resolution_map = {
        0: "resolution_0.25",  # Domain level
        1: "resolution_1.0",   # Subdomain level
        2: "resolution_3.0",   # Microcluster level
    }
    
    labels = {}
    for zoom_level, res_key in resolution_map.items():
        if res_key in leiden_data:
            labels[zoom_level] = np.array(leiden_data[res_key]['labels'])
    
    return metadata, labels


def test_cluster_nesting(labels):
    """Test whether finer clusters are nested within coarser clusters."""
    logger.info("=== Testing Cluster Nesting ===")
    
    nesting_scores = {}
    
    for coarse_level in [0, 1]:
        fine_level = coarse_level + 1
        if fine_level not in labels:
            continue
        
        coarse_labels = labels[coarse_level]
        fine_labels = labels[fine_level]
        
        # For each coarse cluster, check if fine clusters are mostly contained
        coarse_unique = np.unique(coarse_labels)
        containment_scores = []
        
        for coarse_id in coarse_unique:
            coarse_mask = coarse_labels == coarse_id
            fine_in_coarse = fine_labels[coarse_mask]
            
            # Get the most common fine cluster in this coarse cluster
            fine_counts = Counter(fine_in_coarse)
            most_common_fine = fine_counts.most_common(1)[0][0]
            
            # Compute containment: fraction of fine cluster that's in this coarse cluster
            fine_mask = fine_labels == most_common_fine
            total_in_fine = np.sum(fine_mask)
            in_both = np.sum(coarse_mask & fine_mask)
            
            if total_in_fine > 0:
                containment = in_both / total_in_fine
                containment_scores.append(containment)
        
        avg_containment = np.mean(containment_scores) if containment_scores else 0
        nesting_scores[f"{coarse_level}_to_{fine_level}"] = {
            'average_containment': avg_containment,
            'n_coarse_clusters': len(coarse_unique),
            'containment_scores': containment_scores,
        }
        
        logger.info(f"  Zoom {coarse_level} -> {fine_level}: "
                    f"avg containment = {avg_containment:.3f}")
    
    return nesting_scores


def test_legal_area_consistency(metadata, labels):
    """Test whether legal areas remain consistent across zoom levels."""
    logger.info("=== Testing Legal Area Consistency ===")
    
    consistency_scores = {}
    
    for zoom_level, cluster_labels in labels.items():
        # For each cluster, compute dominant legal area purity
        purities = []
        cluster_sizes = []
        
        for cluster_id in np.unique(cluster_labels):
            mask = cluster_labels == cluster_id
            cluster_meta = [metadata[i] for i in np.where(mask)[0]]
            
            areas = [m.get('legal_area') for m in cluster_meta if m.get('legal_area')]
            if not areas:
                continue
            
            # Compute purity (fraction of dominant area)
            area_counts = Counter(areas)
            dominant_area = area_counts.most_common(1)[0]
            purity = dominant_area[1] / len(areas)
            
            purities.append(purity)
            cluster_sizes.append(np.sum(mask))
        
        avg_purity = np.mean(purities) if purities else 0
        weighted_purity = np.average(purities, weights=cluster_sizes) if purities else 0
        
        consistency_scores[f"zoom_{zoom_level}"] = {
            'average_purity': avg_purity,
            'weighted_purity': weighted_purity,
            'n_clusters': len(np.unique(cluster_labels)),
        }
        
        logger.info(f"  Zoom {zoom_level}: avg purity = {avg_purity:.3f}, "
                    f"weighted purity = {weighted_purity:.3f}")
    
    return consistency_scores


def test_language_consistency(metadata, labels):
    """Test whether language remains consistent across zoom levels."""
    logger.info("=== Testing Language Consistency ===")
    
    consistency_scores = {}
    
    for zoom_level, cluster_labels in labels.items():
        # For each cluster, compute language purity
        purities = []
        cluster_sizes = []
        
        for cluster_id in np.unique(cluster_labels):
            mask = cluster_labels == cluster_id
            cluster_meta = [metadata[i] for i in np.where(mask)[0]]
            
            langs = [m.get('language') for m in cluster_meta if m.get('language')]
            if not langs:
                continue
            
            # Compute purity (fraction of dominant language)
            lang_counts = Counter(langs)
            dominant_lang = lang_counts.most_common(1)[0]
            purity = dominant_lang[1] / len(langs)
            
            purities.append(purity)
            cluster_sizes.append(np.sum(mask))
        
        avg_purity = np.mean(purities) if purities else 0
        weighted_purity = np.average(purities, weights=cluster_sizes) if purities else 0
        
        consistency_scores[f"zoom_{zoom_level}"] = {
            'average_purity': avg_purity,
            'weighted_purity': weighted_purity,
            'n_clusters': len(np.unique(cluster_labels)),
        }
        
        logger.info(f"  Zoom {zoom_level}: avg purity = {avg_purity:.3f}, "
                    f"weighted purity = {weighted_purity:.3f}")
    
    return consistency_scores


def test_nmi_between_levels(labels):
    """Compute NMI between adjacent zoom levels."""
    logger.info("=== Testing NMI Between Zoom Levels ===")
    
    nmi_scores = {}
    
    for coarse_level in [0, 1]:
        fine_level = coarse_level + 1
        if coarse_level not in labels or fine_level not in labels:
            continue
        
        coarse_labels = labels[coarse_level]
        fine_labels = labels[fine_level]
        
        nmi = normalized_mutual_info_score(coarse_labels, fine_labels)
        nmi_scores[f"{coarse_level}_to_{fine_level}"] = nmi
        
        logger.info(f"  Zoom {coarse_level} -> {fine_level}: NMI = {nmi:.3f}")
    
    return nmi_scores


def convert(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    return obj


def main():
    logger.info("=== Multi-Resolution Structure Coherence Test ===")
    
    # Load data
    metadata, labels = load_data()
    logger.info(f"Loaded {len(metadata)} decisions, {len(labels)} zoom levels")
    
    # Run tests
    nesting_scores = test_cluster_nesting(labels)
    legal_area_consistency = test_legal_area_consistency(metadata, labels)
    language_consistency = test_language_consistency(metadata, labels)
    nmi_scores = test_nmi_between_levels(labels)
    
    # Summary
    logger.info("\n=== Summary ===")
    logger.info(f"Cluster nesting (avg containment): "
               f"{np.mean([s['average_containment'] for s in nesting_scores.values()]):.3f}")
    logger.info(f"Legal area consistency (weighted avg): "
               f"{np.mean([s['weighted_purity'] for s in legal_area_consistency.values()]):.3f}")
    logger.info(f"Language consistency (weighted avg): "
               f"{np.mean([s['weighted_purity'] for s in language_consistency.values()]):.3f}")
    logger.info(f"NMI between levels (avg): "
               f"{np.mean(list(nmi_scores.values())):.3f}")
    
    # Save results
    results = {
        'nesting_scores': nesting_scores,
        'legal_area_consistency': legal_area_consistency,
        'language_consistency': language_consistency,
        'nmi_scores': nmi_scores,
    }
    
    with open(OUTPUT_DIR / "coherence_test_results.json", 'w') as f:
        json.dump(convert(results), f, indent=2)
    
    logger.info(f"\nResults saved to {OUTPUT_DIR}")
    return results


if __name__ == "__main__":
    main()
