#!/usr/bin/env python3
"""
Evaluation Lane — Monte Carlo comparison of debiased_citation_blended variants

Tests the debiased_citation_blended at multiple PCA dimensionalities (64, 128, 768)
to understand if the adversarial gate failure is dimensionality-dependent.
Also compares with the best existing representation (cited_decisions_tfidf) on the
same 1000-decision subset for fair comparison.
"""

import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

REPO_ROOT = Path("/home/runner/work/LexMachina/LexMachina")
ACCEPTED_ROOT = Path("/tmp/lex_accepted")
OUTPUT_DIR = REPO_ROOT / "evaluation/results/debiased_citation_blended_cross_validation"

FROZEN_SEED = 42

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


def assign_branch(chamber):
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    cl = chamber.lower()
    if "öffentlich" in cl or "public" in cl: return "oeffentliches_recht"
    if "zivil" in cl or "civil" in cl: return "zivilrecht"
    if "straf" in cl or "pénal" in cl: return "strafrecht"
    if "sozial" in cl or "social" in cl: return "sozialversicherungsrecht"
    return "unknown"


def load_aligned_data():
    with open(ACCEPTED_ROOT / 'fractal-map/results/fractal_map/baseline/metadata.json') as f:
        fm_meta = json.load(f)
    fm_ids = {m["decision_id"] for m in fm_meta}
    
    with open(ACCEPTED_ROOT / 'legal-distance/legal_distance/results/v5/center_projected_full/metadata.json') as f:
        fh_meta = json.load(f)
    fh_lookup = {m["decision_id"]: m for m in fh_meta}
    
    aligned_meta = []
    aligned_indices = []
    for i, fm_m in enumerate(fm_meta):
        did = fm_m["decision_id"]
        if did in fh_lookup:
            fh_m = fh_lookup[did]
            aligned_meta.append({
                "decision_id": did,
                "language": fh_m.get("language", "unknown"),
                "legal_area": fh_m.get("legal_area", "unknown"),
                "branch": fh_m.get("branch", assign_branch(fh_m.get("chamber", ""))),
                "chamber": fh_m.get("chamber", "unknown"),
            })
            aligned_indices.append(i)
    
    return aligned_meta, aligned_indices


def run_adversarial(embeddings, metadata):
    from sklearn.neighbors import NearestNeighbors
    n = len(embeddings)
    branches = np.array([m["branch"] for m in metadata])
    languages = np.array([m["language"] for m in metadata])
    
    # Language dominance
    k_ld = min(20, n - 1)
    nn = NearestNeighbors(n_neighbors=k_ld + 1, metric='cosine')
    nn.fit(embeddings)
    _, idx = nn.kneighbors(embeddings)
    neighbors = idx[:, 1:]
    dom_rates = []
    for i in range(n):
        lang = languages[i]
        nbr_langs = [metadata[j]["language"] for j in neighbors[i]]
        dom_rates.append(sum(1 for l in nbr_langs if l == lang) / k_ld)
    lang_dom = float(np.mean(dom_rates))
    
    # Jurist preference
    k_jp = min(10, n - 1)
    nn2 = NearestNeighbors(n_neighbors=k_jp + 1, metric='cosine')
    nn2.fit(embeddings)
    _, idx2 = nn2.kneighbors(embeddings)
    neighbors2 = idx2[:, 1:]
    legal_rel = 0
    for i in range(n):
        bi, li = branches[i], languages[i]
        has_legal = False
        for j in neighbors2[i]:
            if branches[j] == bi and languages[j] != li:
                has_legal = True
                break
        if has_legal:
            legal_rel += 1
    jurist = legal_rel / n
    
    return {
        "lang_dom": lang_dom,
        "lang_dom_pass": lang_dom < 0.85,
        "jurist": jurist,
        "jurist_pass": jurist > 0.5,
        "both_pass": lang_dom < 0.85 and jurist > 0.5,
    }


def main():
    run_id = f"dcbl_variants_{int(time.time())}"
    logger.info(f"Starting variant comparison: {run_id}")
    
    aligned_meta, aligned_indices = load_aligned_data()
    logger.info(f"Aligned: {len(aligned_meta)} decisions")
    
    # Load debiased_citation_blended (768-dim)
    emb_768 = np.load(ACCEPTED_ROOT / 'fractal-map/results/legal_distance/embeddings/debiased_citation_blended.npy')
    emb_768_aligned = emb_768[aligned_indices]
    
    # Load cited_decisions_tfidf (128-dim) — need to align to 1000-slice
    cdtf = np.load(ACCEPTED_ROOT / 'legal-distance/legal_distance/results/v7/outcome_cited_hybrids/cited_decisions_tfidf.npy')
    logger.info(f"Full cited_decisions_tfidf shape: {cdtf.shape}")
    
    # Load full 1200-slice metadata for cited_decisions_tfidf alignment
    with open(ACCEPTED_ROOT / 'legal-distance/legal_distance/results/v5/center_projected_full/metadata.json') as f:
        fh_meta = json.load(f)
    
    # Find indices in the 1200-slice that correspond to the 1000-slice
    fm_ids_ordered = [m["decision_id"] for m in aligned_meta]
    fh_id_to_idx = {m["decision_id"]: i for i, m in enumerate(fh_meta)}
    cdtf_indices = [fh_id_to_idx[did] for did in fm_ids_ordered if did in fh_id_to_idx]
    cdtf_aligned = cdtf[cdtf_indices]
    logger.info(f"Aligned cited_decisions_tfidf shape: {cdtf_aligned.shape}")
    
    # PCA project debiased_citation_blended to 64 and 128 dims
    from sklearn.decomposition import PCA
    pca_64 = PCA(n_components=64, random_state=42)
    emb_64 = pca_64.fit_transform(emb_768_aligned)
    logger.info(f"PCA 64-dim explained variance: {sum(pca_64.explained_variance_ratio_):.4f}")
    
    pca_128 = PCA(n_components=128, random_state=42)
    emb_128 = pca_128.fit_transform(emb_768_aligned)
    logger.info(f"PCA 128-dim explained variance: {sum(pca_128.explained_variance_ratio_):.4f}")
    
    # Normalize all embeddings
    def normalize(e):
        norms = np.linalg.norm(e, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return e / norms
    
    variants = {
        "debiased_cb_768dim": normalize(emb_768_aligned),
        "debiased_cb_128dim": normalize(emb_128),
        "debiased_cb_64dim": normalize(emb_64),
        "cited_decisions_tfidf_128dim": normalize(cdtf_aligned),
    }
    
    results = {}
    for name, emb in variants.items():
        logger.info(f"\n--- {name} (dim={emb.shape[1]}) ---")
        r = run_adversarial(emb, aligned_meta)
        logger.info(f"  LangDom: {r['lang_dom']:.4f} ({'PASS' if r['lang_dom_pass'] else 'FAIL'})")
        logger.info(f"  Jurist: {r['jurist']:.4f} ({'PASS' if r['jurist_pass'] else 'FAIL'})")
        logger.info(f"  Both: {'PASS' if r['both_pass'] else 'FAIL'}")
        results[name] = r
    
    # Save
    output = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus": f"{len(aligned_meta)} decisions (1000-slice aligned)",
        "variants": results,
    }
    out_path = OUTPUT_DIR / f"{run_id}_variant_comparison.json"
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nResults saved to {out_path}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VARIANT COMPARISON SUMMARY")
    logger.info("=" * 60)
    for name, r in results.items():
        status = "PASS" if r["both_pass"] else "FAIL"
        logger.info(f"  {name:40s} LD={r['lang_dom']:.4f} JP={r['jurist']:.4f} [{status}]")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
