#!/usr/bin/env python3
"""
Product-integration 174k join alignment probe v1 (fractal-map lane).
Pre-registered probe for the reconciliation cycle (run 38048724922 repair).

Question: are product_integration_174k decision->cluster mappings ID-truthful?

Two embeddings families exist:
  A) EVAL family  /tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings/{mode}.npy
     (173963 x 128; row i = eval metadata row i; accepted 0.906-0.930 verdicts were
      computed in this row space, which IS the id space)
  B) PRODUCT family results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/{mode}.npy
     (175440 x 128; corpus-jsonl row order; the first 173963 rows were positionally
      truncated and keyed to eval metadata ids by build_production_modes_product_integration_174k.py)

If the first 173963 PRODUCT rows were in eval-metadata order, the diagonal of the
product-vs-eval cosine matrix would be the argmax for essentially every row.
A low "diagonal-is-best" fraction proves the product rows are in a different order,
i.e. the id->cluster mapping in product_integration_174k decision_clusters.json is
scrambled (a join/alignment defect, not a scientific falsification).

Method (frozen): sample 2000 product rows (rng default_rng(0), replace=False),
cosine-similarity vs all 173963 eval rows, report diagonal-match statistics.
Deterministic given numpy>=1.24.

Output: results/fractal_map/diagnostics/product_integration_174k_join_probe_v1.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
EVAL_EMB = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings')
PROD_EMB = ROOT / 'results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings'
OUT = ROOT / 'results/fractal_map/diagnostics'
OUT.mkdir(parents=True, exist_ok=True)

# Scope: the 3 text modes of the accepted 0.906-0.930 headline (frozen recon spec).
# cited_decisions_tfidf is EXCLUDED: it contains zero-norm rows (missing citation text),
# which make cosine probing degenerate; the headline under test never included it.
MODES = ['full_text_tfidf_light', 'regeste_full_text_hybrid_0.5', 'regeste_full_text_hybrid_0.7']
SAMPLE = 2000
SEED = 0


def _l2_normalize(rows):
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    with np.errstate(invalid='ignore', divide='ignore'):
        out = rows / norms
    out[~np.isfinite(out)] = 0.0
    return out


def probe(mode):
    pe = np.load(PROD_EMB / f'{mode}.npy', mmap_mode='r')
    ee = np.load(EVAL_EMB / f'{mode}.npy', mmap_mode='r')
    n = ee.shape[0]
    pn = np.asarray(pe[:n], dtype=np.float32)
    en = np.asarray(ee, dtype=np.float32)
    p = _l2_normalize(pn)
    e = _l2_normalize(en)
    rng = np.random.default_rng(SEED)
    idx = rng.choice(n, SAMPLE, replace=False)
    S = p[idx] @ e.T  # SAMPLE x n
    diag_sim = S[np.arange(SAMPLE), idx]
    best = S.argmax(axis=1)
    best_sim = S[np.arange(SAMPLE), best]
    off = np.abs(best - idx)
    return {
        'mode': mode,
        'sample_size': SAMPLE,
        'seed': SEED,
        'n_rows': int(n),
        'product_embedding_shape': [int(pe.shape[0]), int(pe.shape[1])],
        'eval_embedding_shape': [int(ee.shape[0]), int(ee.shape[1])],
        'diag_cosine_mean': float(diag_sim.mean()),
        'diag_cosine_min': float(diag_sim.min()),
        'diag_is_best_match_fraction': float((best == idx).mean()),
        'best_match_cosine_mean': float(best_sim.mean()),
        'rows_identical_diag_fraction': float((diag_sim > 0.9999).mean()),
        'median_abs_best_minus_idx': int(np.median(off)),
        'frac_abs_diff_gt_1000': float((off > 1000).mean()),
        'verdict_if_aligned_expect': 'diag_is_best_match_fraction ~ 1.0',
        'interpretation': ('diag_is_best_match_fraction near 0 with high best_match_cosine_mean and '
                           'large median |best-idx| => product row order != eval metadata order; '
                           'positional id->cluster keying in product_integration_174k is SCRAMBLED'),
    }


if __name__ == '__main__':
    results = {m: probe(m) for m in MODES}
    blob = {
        'probe_id': 'product_integration_174k_join_probe_v1',
        'lane': 'fractal-map',
        'direction_version': 35,
        'created_utc': '2026-10-10',
        'frozen': True,
        'motivation': 'Run 38048724922 reconciliation: PRODUCT artifacts showed at-chance purity '
                      '(R1/R2) while accepted headline comes from eval-aligned embeddings. '
                      'This probe isolates whether product id->cluster joins are ID-truthful.',
        'results': results,
    }
    out_path = OUT / 'product_integration_174k_join_probe_v1.json'
    with open(out_path, 'w') as f:
        json.dump(blob, f, indent=1)
    for m, r in results.items():
        print(f"{m}: diag_is_best={r['diag_is_best_match_fraction']:.4f} "
              f"diag_cos={r['diag_cosine_mean']:.4f} best_cos={r['best_match_cosine_mean']:.4f} "
              f"median|diff|={r['median_abs_best_minus_idx']} frac>1000={r['frac_abs_diff_gt_1000']:.4f}")
    print('Wrote', out_path)