#!/usr/bin/env python3
"""
Verification of v2 evaluation completion on current codebase.
Tests the frozen debiased_citation_blended baseline and center_projected alternative
on the key v2 adversarial benchmarks: adversarial_language_dominance and jurist_pairwise_preference.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict
import hashlib

# Load the frozen debiased_citation_blended baseline from workspace results
WORKSPACE_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/results")
ACCEPTED_FRACTAL = Path("/tmp/lex_accepted/fractal-map/results/fractal_map")
CORPUS_DIR = Path("/tmp/lex_accepted/product/product/results/corpus/normalization/canonical")

@dataclass
class Decision:
    decision_id: str
    language: str
    legal_area: str
    branch: str
    chamber: str
    year: str

def load_corpus() -> List[Decision]:
    """Load the 1000-decision evaluation slice."""
    decisions = []
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    with open(slice_path, 'r') as f:
        for line in f:
            d = json.loads(line)
            decisions.append(Decision(
                decision_id=d["decision_id"],
                language=d["language"],
                legal_area=d["legal_area"],
                branch=d["branch"],
                chamber=d["chamber"],
                year=d.get("decision_date", "").split("-")[0] if d.get("decision_date") else "unknown"
            ))
    return decisions

def load_debiased_citation_blended() -> Tuple[np.ndarray, List[str]]:
    """Load frozen debiased_citation_blended embeddings (n_pca=1, alpha=0.7)."""
    emb = np.load(WORKSPACE_RESULTS / "debiased_citation_blended_64.npy")
    with open(WORKSPACE_RESULTS / "debiased_citation_blended_metadata.json") as f:
        meta = json.load(f)
    decision_ids = [m["decision_id"] for m in meta]
    return emb, decision_ids

def load_center_projected() -> Tuple[np.ndarray, List[str]]:
    """Load center_projected embeddings from accepted fractal-map."""
    emb = np.load(ACCEPTED_FRACTAL / "language_debiasing/embeddings_center_projected.npy")
    # Load decision IDs from the 1000-decision slice
    slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
    with open(slice_path) as f:
        decision_ids = [json.loads(line)["decision_id"] for line in f]
    return emb, decision_ids

def align_decisions(decisions: List[Decision], rep_decision_ids: List[str]) -> Tuple[List[Decision], np.ndarray]:
    """Align decisions with representation decision IDs."""
    decision_id_to_idx = {d.decision_id: i for i, d in enumerate(decisions)}
    aligned_indices = []
    aligned_decision_ids = []
    for i, did in enumerate(rep_decision_ids):
        if did in decision_id_to_idx:
            aligned_indices.append(i)
            aligned_decision_ids.append(did)
    aligned_decisions = [decisions[decision_id_to_idx[did]] for did in aligned_decision_ids]
    return aligned_decisions, np.array(aligned_indices)

def cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix."""
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    return normalized @ normalized.T

def adversarial_language_dominance(embeddings: np.ndarray, decisions: List[Decision], k: int = 20) -> Dict:
    """
    Adversarial language dominance benchmark.
    For each decision, check if its k nearest neighbors are dominated by same-language decisions.
    Lower is better (language should not dominate).
    Threshold: < 0.85 PASS
    """
    n = len(decisions)
    languages = [d.language for d in decisions]
    
    # Compute similarities
    sim_matrix = cosine_similarity_matrix(embeddings)
    
    # For each decision, get top-k neighbors (excluding self)
    dominance_scores = []
    for i in range(n):
        # Get top k neighbors (excluding self at index i)
        sims = sim_matrix[i]
        neighbor_indices = np.argsort(sims)[::-1][1:k+1]  # Skip self
        
        neighbor_languages = [languages[j] for j in neighbor_indices]
        same_lang_count = sum(1 for lang in neighbor_languages if lang == languages[i])
        dominance = same_lang_count / k
        dominance_scores.append(dominance)
    
    mean_dominance = np.mean(dominance_scores)
    std_dominance = np.std(dominance_scores)
    max_dominance = np.max(dominance_scores)
    
    return {
        "mean_language_dominance": float(mean_dominance),
        "std_language_dominance": float(std_dominance),
        "max_language_dominance": float(max_dominance),
        "k": k,
        "threshold": 0.85,
        "status": "PASS" if mean_dominance < 0.85 else "FAIL",
        "note": "Lower is better - language should not dominate neighbors"
    }

def jurist_pairwise_preference(embeddings: np.ndarray, decisions: List[Decision], k: int = 10) -> Dict:
    """
    Jurist pairwise preference simulation.
    For each decision, check if at least one legally-relevant neighbor (same branch, different language)
    appears in top-k before any language-artifact neighbor (different branch, same language).
    Higher is better. Threshold: > 0.5 PASS
    """
    n = len(decisions)
    branches = [d.branch for d in decisions]
    languages = [d.language for d in decisions]
    
    sim_matrix = cosine_similarity_matrix(embeddings)
    
    legal_relevant_only = 0
    language_artifact_only = 0
    both_available = 0
    neither_available = 0
    legal_neighbor_count = 0
    language_neighbor_count = 0
    
    for i in range(n):
        sims = sim_matrix[i]
        neighbor_indices = np.argsort(sims)[::-1][1:k+1]  # Skip self
        
        neighbor_branches = [branches[j] for j in neighbor_indices]
        neighbor_languages = [languages[j] for j in neighbor_indices]
        
        target_branch = branches[i]
        target_language = languages[i]
        
        # Find first legally-relevant neighbor (same branch, different language)
        legal_rank = None
        for rank, (nb, nl) in enumerate(zip(neighbor_branches, neighbor_languages)):
            if nb == target_branch and nl != target_language:
                legal_rank = rank
                break
        
        # Find first language-artifact neighbor (different branch, same language)
        lang_rank = None
        for rank, (nb, nl) in enumerate(zip(neighbor_branches, neighbor_languages)):
            if nb != target_branch and nl == target_language:
                lang_rank = rank
                break
        
        has_legal = legal_rank is not None
        has_lang = lang_rank is not None
        
        if has_legal and not has_lang:
            legal_relevant_only += 1
            legal_neighbor_count += 1
        elif has_lang and not has_legal:
            language_artifact_only += 1
            language_neighbor_count += 1
        elif has_legal and has_lang:
            both_available += 1
            # Jurist would pick the one that appears first
            if legal_rank < lang_rank:
                legal_neighbor_count += 1
            else:
                language_neighbor_count += 1
        else:
            neither_available += 1
    
    total = len(decisions)
    legal_neighbor_rate = legal_neighbor_count / total
    language_neighbor_rate = language_neighbor_count / total
    
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_only,
        "language_artifact_only": language_artifact_only,
        "both_available": both_available,
        "neither_available": neither_available,
        "legal_neighbor_rate": float(legal_neighbor_rate),
        "language_neighbor_rate": float(language_neighbor_rate),
        "jurist_would_succeed_rate": float(legal_neighbor_rate),
        "jurist_forced_wrong_rate": float(language_neighbor_rate),
        "threshold": 0.5,
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }

def main():
    print("=" * 80)
    print("V2 EVALUATION COMPLETION VERIFICATION")
    print("=" * 80)
    
    # Load corpus
    print("\nLoading corpus...")
    decisions = load_corpus()
    print(f"Loaded {len(decisions)} decisions")
    
    # Load representations
    print("\nLoading representations...")
    debiased_emb, debiased_ids = load_debiased_citation_blended()
    center_emb, center_ids = load_center_projected()
    print(f"debiased_citation_blended: {debiased_emb.shape}")
    print(f"center_projected: {center_emb.shape}")
    
    # Align decisions with representations
    aligned_decisions_debiased, debiased_indices = align_decisions(decisions, debiased_ids)
    aligned_decisions_center, center_indices = align_decisions(decisions, center_ids)
    
    debiased_aligned_emb = debiased_emb[debiased_indices]
    center_aligned_emb = center_emb[center_indices]
    
    print(f"Aligned debiased: {len(aligned_decisions_debiased)} decisions, {debiased_aligned_emb.shape}")
    print(f"Aligned center: {len(aligned_decisions_center)} decisions, {center_aligned_emb.shape}")
    
    # Run adversarial language dominance
    print("\n" + "=" * 80)
    print("ADVERSARIAL LANGUAGE DOMINANCE (k=20, threshold < 0.85)")
    print("=" * 80)
    
    debiased_lang_dom = adversarial_language_dominance(debiased_aligned_emb, aligned_decisions_debiased, k=20)
    center_lang_dom = adversarial_language_dominance(center_aligned_emb, aligned_decisions_center, k=20)
    
    print(f"\ndebiased_citation_blended:")
    print(f"  mean_language_dominance: {debiased_lang_dom['mean_language_dominance']:.4f}")
    print(f"  std: {debiased_lang_dom['std_language_dominance']:.4f}")
    print(f"  max: {debiased_lang_dom['max_language_dominance']:.4f}")
    print(f"  status: {debiased_lang_dom['status']}")
    
    print(f"\ncenter_projected:")
    print(f"  mean_language_dominance: {center_lang_dom['mean_language_dominance']:.4f}")
    print(f"  std: {center_lang_dom['std_language_dominance']:.4f}")
    print(f"  max: {center_lang_dom['max_language_dominance']:.4f}")
    print(f"  status: {center_lang_dom['status']}")
    
    # Run jurist pairwise preference
    print("\n" + "=" * 80)
    print("JURIST PAIRWISE PREFERENCE (k=10, threshold > 0.5)")
    print("=" * 80)
    
    debiased_jurist = jurist_pairwise_preference(debiased_aligned_emb, aligned_decisions_debiased, k=10)
    center_jurist = jurist_pairwise_preference(center_aligned_emb, aligned_decisions_center, k=10)
    
    print(f"\ndebiased_citation_blended:")
    print(f"  legal_neighbor_rate: {debiased_jurist['legal_neighbor_rate']:.4f}")
    print(f"  language_neighbor_rate: {debiased_jurist['language_neighbor_rate']:.4f}")
    print(f"  legal_relevant_only: {debiased_jurist['legal_relevant_only']}")
    print(f"  language_artifact_only: {debiased_jurist['language_artifact_only']}")
    print(f"  both_available: {debiased_jurist['both_available']}")
    print(f"  neither_available: {debiased_jurist['neither_available']}")
    print(f"  status: {debiased_jurist['status']}")
    
    print(f"\ncenter_projected:")
    print(f"  legal_neighbor_rate: {center_jurist['legal_neighbor_rate']:.4f}")
    print(f"  language_neighbor_rate: {center_jurist['language_neighbor_rate']:.4f}")
    print(f"  legal_relevant_only: {center_jurist['legal_relevant_only']}")
    print(f"  language_artifact_only: {center_jurist['language_artifact_only']}")
    print(f"  both_available: {center_jurist['both_available']}")
    print(f"  neither_available: {center_jurist['neither_available']}")
    print(f"  status: {center_jurist['status']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    v2_findings_confirmed = True
    
    # Check debiased_citation_blended fails language dominance (should be ~0.999 or >0.85)
    if debiased_lang_dom['mean_language_dominance'] >= 0.85:
        print("✓ CONFIRMED: debiased_citation_blended FAILS adversarial language dominance (catastrophic)")
    else:
        print("✗ UNEXPECTED: debiased_citation_blended PASSES language dominance")
        v2_findings_confirmed = False
    
    # Check debiased_citation_blended fails jurist pairwise (< 0.5)
    if debiased_jurist['legal_neighbor_rate'] <= 0.5:
        print("✓ CONFIRMED: debiased_citation_blended FAILS jurist pairwise preference")
    else:
        print("✗ UNEXPECTED: debiased_citation_blended PASSES jurist pairwise")
        v2_findings_confirmed = False
    
    # Check center_projected passes language dominance (< 0.85)
    if center_lang_dom['mean_language_dominance'] < 0.85:
        print("✓ CONFIRMED: center_projected PASSES adversarial language dominance")
    else:
        print("✗ UNEXPECTED: center_projected FAILS language dominance")
        v2_findings_confirmed = False
    
    # Check center_projected passes jurist pairwise (> 0.5)
    if center_jurist['legal_neighbor_rate'] > 0.5:
        print("✓ CONFIRMED: center_projected PASSES jurist pairwise preference")
    else:
        print("✗ UNEXPECTED: center_projected FAILS jurist pairwise")
        v2_findings_confirmed = False
    
    # Check center_projected is the ONLY representation passing BOTH
    center_both = (center_lang_dom['status'] == 'PASS' and center_jurist['status'] == 'PASS')
    debiased_both = (debiased_lang_dom['status'] == 'PASS' and debiased_jurist['status'] == 'PASS')
    
    if center_both and not debiased_both:
        print("✓ CONFIRMED: center_projected is the ONLY representation passing BOTH critical benchmarks")
    else:
        print("✗ UNEXPECTED: center_projected is not uniquely passing both")
        v2_findings_confirmed = False
    
    print(f"\nV2 FINDINGS CONFIRMED: {v2_findings_confirmed}")
    
    # Save results
    results = {
        "run_id": "v2_verification_20260827",
        "timestamp": "2026-08-27T23:30:00Z",
        "direction_version": 4,
        "frozen_sample": "1000 BGer decisions (2020-2024) from canonical slice",
        "representations_tested": ["debiased_citation_blended", "center_projected"],
        "benchmarks": {
            "adversarial_language_dominance": {
                "debiased_citation_blended": debiased_lang_dom,
                "center_projected": center_lang_dom
            },
            "jurist_pairwise_preference": {
                "debiased_citation_blended": debiased_jurist,
                "center_projected": center_jurist
            }
        },
        "v2_findings_confirmed": v2_findings_confirmed,
        "key_v2_findings": {
            "debiased_citation_blended_language_dominance": debiased_lang_dom['mean_language_dominance'],
            "debiased_citation_blended_jurist_rate": debiased_jurist['legal_neighbor_rate'],
            "center_projected_language_dominance": center_lang_dom['mean_language_dominance'],
            "center_projected_jurist_rate": center_jurist['legal_neighbor_rate'],
            "center_projected_unique_pass_both": center_both and not debiased_both
        }
    }
    
    output_path = WORKSPACE_RESULTS / "evaluation" / "v2_verification_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    
    return results

if __name__ == "__main__":
    main()