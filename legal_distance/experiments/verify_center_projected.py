#!/usr/bin/env python3
"""
Verify center_projected representation on full benchmark suite.
Uses the accepted evaluation modules directly.
"""
import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from collections import Counter
import sys

# Use the accepted evaluation modules
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map')

from tests.cross_language_benchmarks import (
    cross_language_neighbor_quality,
    zero_shot_cross_language_transfer,
    language_specific_representation_quality,
    adversarial_language_dominance,
)
from tests.jurist_usability import (
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_zoom_task,
    simulate_cross_language_retrieval,
    prepare_metadata,
)

# Load center_projected embeddings and metadata
print("Loading center_projected embeddings...")
emb = np.load('/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected/embeddings_center_projected.npy')
with open('/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected/metadata.json') as f:
    metadata = json.load(f)
print(f"  Shape: {emb.shape}")
print(f"  Metadata: {len(metadata)} decisions")
print(f"  Languages: {Counter(m['language'] for m in metadata)}")
print(f"  Branches: {Counter(m.get('branch') for m in metadata)}")

# V2 Cross-language benchmarks
print("\n" + "="*70)
print("V2 CROSS-LANGUAGE BENCHMARKS")
print("="*70)

print("Running cross-language neighbor quality...")
cl_nq = cross_language_neighbor_quality(emb, metadata)
print(f"  cross_lang_same_branch_mean: {cl_nq['cross_lang_same_branch_mean']:.4f}")
print(f"  same_lang_same_branch_mean: {cl_nq['same_lang_same_branch_mean']:.4f}")
print(f"  invariance_gap: {cl_nq['invariance_gap']:.4f}")

print("Running zero-shot cross-language transfer...")
zs_ct = zero_shot_cross_language_transfer(emb, metadata)
print(f"  zero_shot_mean_nmi: {zs_ct['zero_shot_mean_nmi']:.4f}")
print(f"  in_domain_mean_nmi: {zs_ct['in_domain_mean_nmi']:.4f}")
print(f"  transfer_gap: {zs_ct['transfer_gap']:.4f}")
print(f"  status: {zs_ct['status']}")

print("Running language-specific representation quality...")
ls_rq = language_specific_representation_quality(emb, metadata)
print(f"  mean_nmi: {ls_rq['mean_nmi']:.4f}")
print(f"  std_nmi: {ls_rq['std_nmi']:.4f}")
print(f"  status: {ls_rq['status']}")

print("Running adversarial language dominance...")
adv_ld = adversarial_language_dominance(emb, metadata)
print(f"  mean_language_dominance: {adv_ld['mean_language_dominance']:.4f}")
print(f"  threshold: {adv_ld['threshold']}")
print(f"  status: {adv_ld['status']}")

# Jurist usability benchmarks
print("\n" + "="*70)
print("V2 JURIST USABILITY BENCHMARKS")
print("="*70)

branches, languages, chambers, valid_indices = prepare_metadata(metadata)
rep_valid = emb[valid_indices]

print("Running jurist pairwise preference simulation...")
pp = simulate_pairwise_preference(rep_valid, branches, languages)
print(f"  legal_neighbor_rate: {pp['legal_neighbor_rate']:.4f}")
print(f"  jurist_would_succeed_rate: {pp['jurist_would_succeed_rate']:.4f}")
print(f"  status: {pp['status']}")

print("Running jurist cluster coherence rating simulation...")
ccr = simulate_cluster_coherence_rating(rep_valid, branches, languages)
print(f"  mean_branch_purity: {ccr['mean_branch_purity']:.4f}")
print(f"  mean_language_purity: {ccr['mean_language_purity']:.4f}")
print(f"  status: {ccr['status']}")

print("Running jurist zoom task simulation...")
from pathlib import Path as PathLib
zt = simulate_zoom_task(rep_valid, branches, languages, valid_indices,
                       PathLib('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json'))
print(f"  coarse_purity: {zt.get('coarse_purity', 'N/A')}")
print(f"  fine_purity: {zt.get('fine_purity', 'N/A')}")
print(f"  status: {zt.get('status', 'N/A')}")

print("Running jurist cross-language retrieval simulation...")
clr = simulate_cross_language_retrieval(rep_valid, branches, languages)
print(f"  mean_cross_language_recall_at_k: {clr['mean_cross_language_recall_at_k']:.4f}")
print(f"  status: {clr['status']}")

# Summary
print("\n" + "="*70)
print("CRITICAL ADVERSARIAL TESTS SUMMARY")
print("="*70)
center_dom = adv_ld['mean_language_dominance']
center_pref = pp['jurist_would_succeed_rate']
print(f"Adversarial Language Dominance (< 0.85): {center_dom:.4f} {'PASS' if center_dom < 0.85 else 'FAIL'}")
print(f"Jurist Pairwise Preference (> 0.5): {center_pref:.4f} {'PASS' if center_pref > 0.5 else 'FAIL'}")
both_pass = (center_dom < 0.85) and (center_pref > 0.5)
print(f"BOTH PASS: {'YES' if both_pass else 'NO'}")

if both_pass:
    print("\n✅ center_projected is the ONLY representation passing both adversarial tests")
else:
    print("\n❌ center_projected does not pass both tests")

