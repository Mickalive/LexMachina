#!/usr/bin/env python3
"""
Analyze 174k legal_area labels and test v17b normalization generalization.
"""
import json
import sys
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "experiments"))
from legal_area_normalize import normalize_legal_area, CROSS_LINGUAL_MAP

METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")

def main():
    logger.info("=" * 70)
    logger.info("ANALYZE 174K LEGAL AREA LABELS - v17b NORMALIZATION GENERALIZATION TEST")
    logger.info("=" * 70)
    
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded {len(metadata)} decisions")
    
    # Collect raw legal_area labels
    raw_labels = []
    for m in metadata:
        la = m.get('legal_area', 'unknown')
        if la and la != 'unknown':
            raw_labels.append(la)
    
    raw_counter = Counter(raw_labels)
    logger.info(f"Raw unique legal_area labels: {len(raw_counter)}")
    logger.info(f"Total decisions with legal_area: {len(raw_labels)}")
    logger.info(f"Avg decisions per label: {len(raw_labels) / len(raw_counter):.1f}")
    
    # Show top 30 raw labels
    logger.info("\nTop 30 raw legal_area labels:")
    for label, count in raw_counter.most_common(30):
        logger.info(f"  {label}: {count}")
    
    # Apply normalization
    normalized_labels = [normalize_legal_area(la) for la in raw_labels]
    norm_counter = Counter(normalized_labels)
    
    logger.info(f"\nNormalized unique legal_area labels: {len(norm_counter)}")
    logger.info(f"Reduction: {len(raw_counter)} -> {len(norm_counter)} ({100*(1-len(norm_counter)/len(raw_counter)):.1f}% fewer)")
    
    # Show top 30 normalized labels
    logger.info("\nTop 30 normalized legal_area labels:")
    for label, count in norm_counter.most_common(30):
        logger.info(f"  {label}: {count}")
    
    # Check how many were changed
    changed = sum(1 for r, n in zip(raw_labels, normalized_labels) if r != n)
    logger.info(f"\nLabels changed by normalization: {changed}/{len(raw_labels)} ({100*changed/len(raw_labels):.1f}%)")
    
    # Show which raw labels map to which canonical
    logger.info("\nCross-lingual mappings found in corpus:")
    mapping_used = {}
    for r, n in zip(raw_labels, normalized_labels):
        if r != n:
            if n not in mapping_used:
                mapping_used[n] = []
            if r not in mapping_used[n]:
                mapping_used[n].append(r)
    
    for canon, variants in sorted(mapping_used.items()):
        logger.info(f"  {canon}: {variants}")
    
    # Umbrella labels that pass through unchanged
    umbrella_labels = [la for la in raw_counter.keys() if la not in CROSS_LINGUAL_MAP and la != 'unknown']
    logger.info(f"\nUmbrella/singleton labels (unchanged): {len(umbrella_labels)}")
    for la in sorted(umbrella_labels)[:20]:
        logger.info(f"  {la}: {raw_counter[la]}")
    if len(umbrella_labels) > 20:
        logger.info(f"  ... and {len(umbrella_labels) - 20} more")
    
    # Stats for hierarchy-family benchmark implications
    logger.info("\n" + "=" * 70)
    logger.info("IMPLICATIONS FOR HIERARCHY-FAMILY BENCHMARKS AT 174K")
    logger.info("=" * 70)
    logger.info(f"Raw unique labels: {len(raw_counter)} (avg {len(raw_labels)/len(raw_counter):.1f} decisions/label)")
    logger.info(f"Normalized unique labels: {len(norm_counter)} (avg {len(raw_labels)/len(norm_counter):.1f} decisions/label)")
    logger.info(f"Label count reduction: {len(raw_counter) - len(norm_counter)} ({100*(len(raw_counter)-len(norm_counter))/len(raw_counter):.1f}%)")
    
    # Save results
    out_dir = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_label_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "total_decisions": len(metadata),
        "decisions_with_legal_area": len(raw_labels),
        "raw_unique_labels": len(raw_counter),
        "normalized_unique_labels": len(norm_counter),
        "label_reduction_pct": 100 * (len(raw_counter) - len(norm_counter)) / len(raw_counter),
        "labels_changed_by_normalization": changed,
        "avg_decisions_per_raw_label": len(raw_labels) / len(raw_counter),
        "avg_decisions_per_normalized_label": len(raw_labels) / len(norm_counter),
        "cross_lingual_mappings_found": {canon: variants for canon, variants in mapping_used.items()},
        "top_30_raw": raw_counter.most_common(30),
        "top_30_normalized": norm_counter.most_common(30),
    }
    
    with open(out_dir / "174k_legal_area_analysis.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {out_dir / '174k_legal_area_analysis.json'}")
    logger.info("=" * 70)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
