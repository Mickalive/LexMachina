#!/usr/bin/env python3
"""
R3 of tfidf_hierarchy_reconciliation_v1 (frozen spec sha256
7b57b9e4178cd490a2b2a6437c24251d11783841448c84f5d7b7436e72ab33ad).

Re-runs the FROZEN v29 hierarchical_v1 pipeline
(fractal_map/experiments/constrained_hierarchical_leiden.py) on the
ECONOMY evaluation-v25 embeddings used by the accepted 0.906-0.930 verdict,
then computes BOTH the accepted purity metric and ARI_branch/NMI_area on the
resulting labels. Isolates whether the accepted purity is genuine for that
embedding source and whether that hierarchy macro-aligns with human indexing.

Usage: python3 fractal_map/eval_r3_source_isolation_v1.py <mode> [<mode> ...]
Writes results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_source_isolation_results.json
and per-mode label arrays under .../r3_labels/.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.preprocessing import normalize
from sklearn.metrics import adjusted_rand_score as ARI
from sklearn.metrics import normalized_mutual_info_score as NMI

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
RES = ROOT / 'results/fractal_map'
OUTDIR = RES / 'tfidf_hierarchy_reconciliation_v1'
LABDIR = OUTDIR / 'r3_labels'
LABDIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / 'fractal_map' / 'experiments'))
from constrained_hierarchical_leiden import (  # noqa: E402
    constrained_hierarchical_leiden, compute_branch_purity, compute_area_purity)

EMB_EVAL = Path('/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/embeddings')
META_EVAL = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
CONFIG = dict(coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10,
              max_subclusters_per_parent=20, adaptive_sub_res=True, k=15)
OUT = OUTDIR / 'r3_source_isolation_results.json'


def accepted_purity(labels, values):
    purs = []
    for u in np.unique(labels[labels != -1]):
        vals = [values[i] for i in np.where(labels == u)[0]]
        vals = [v for v in vals if v and v not in ('unknown', 'null')]
        if vals:
            purs.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purs)) if purs else 0.0


def weighted_purity(labels, values):
    dom = tot = 0
    for u in np.unique(labels[labels != -1]):
        vals = [values[i] for i in np.where(labels == u)[0]]
        vals = [v for v in vals if v and v not in ('unknown', 'null')]
        if vals:
            dom += Counter(vals).most_common(1)[0][1]
            tot += len(vals)
    return float(dom / tot) if tot else 0.0


def main(modes):
    results = {}
    if OUT.exists():
        results = json.load(open(OUT))
    meta = json.load(open(META_EVAL))
    branch_all = [m.get('branch') for m in meta]
    area_all = [m.get('legal_area') for m in meta]

    for mode in modes:
        t0 = time.time()
        emb = np.load(EMB_EVAL / f'{mode}.npy')
        n = min(len(emb), len(meta))
        emb = emb[:n]
        meta_n = meta[:n]
        norms = np.linalg.norm(emb, axis=1)
        vm = norms > 0
        emb = normalize(emb[vm], norm='l2')
        meta_n = [m for i, m in enumerate(meta_n) if vm[i]]
        branch = [m.get('branch') for m in meta_n]
        area = [m.get('legal_area') for m in meta_n]
        print(f'[{mode}] data {emb.shape} in {time.time()-t0:.1f}s; clustering...', flush=True)
        hl, cl, info, c2f = constrained_hierarchical_leiden(emb, meta_n, **CONFIG)
        dt = time.time() - t0
        rec = {
            'mode': mode, 'n_valid_embeddings': int(vm.sum()),
            'runtime_seconds': round(dt, 1),
            'fine_n_clusters': int(len(np.unique(hl[hl != -1]))),
            'coarse_n_clusters': int(len(np.unique(cl[cl != -1]))),
            'fine_accepted_purity_unweighted': accepted_purity(hl, branch),
            'fine_accepted_purity_weighted': weighted_purity(hl, branch),
            'coarse_accepted_purity_unweighted': accepted_purity(cl, branch),
            'fine_accepted_area_purity': accepted_purity(hl, area),
        }
        # ARI/NMI computed only on rows with valid human label AND label != -1
        vb = np.array([(b not in (None, 'unknown', 'null')) for b in branch]) & (hl != -1)
        bl = np.array([str(branch[i]) for i in np.where(vb)[0]])
        rec['fine_ARI_branch'] = float(ARI(bl, hl[vb])) if len(np.unique(bl)) > 1 else 0.0
        va = np.array([(a not in (None, 'unknown', 'null')) for a in area]) & (hl != -1)
        al = np.array([str(area[i]) for i in np.where(va)[0]])
        rec['fine_NMI_area'] = float(NMI(al, hl[va], average_method='arithmetic')) if len(np.unique(al)) > 1 else 0.0
        vb2 = np.array([(b not in (None, 'unknown', 'null')) for b in branch]) & (cl != -1)
        bl2 = np.array([str(branch[i]) for i in np.where(vb2)[0]])
        rec['coarse_ARI_branch'] = float(ARI(bl2, cl[vb2])) if len(np.unique(bl2)) > 1 else 0.0
        np.save(LABDIR / f'{mode}_hierarchical.npy', hl.astype(np.int32))
        np.save(LABDIR / f'{mode}_coarse.npy', cl.astype(np.int32))
        results[mode] = rec
        print(f'[{mode}] done in {dt:.1f}s fine_ncl={rec["fine_n_clusters"]} '
              f'purity_uw={rec["fine_accepted_purity_unweighted"]:.4f} '
              f'ARI={rec["fine_ARI_branch"]:.4f} NMI={rec["fine_NMI_area"]:.4f}', flush=True)
        OUT.write_text(json.dumps(results, indent=2, default=str))
    print('Saved', OUT)


if __name__ == '__main__':
    main(sys.argv[1:] or ['full_text_tfidf_light'])
