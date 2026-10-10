#!/usr/bin/env python3
"""
TF-IDF hierarchy reconciliation v1 (frozen spec
results/fractal_map/tfidf_hierarchy_reconciliation_v1/RECON_SPEC_FROZEN.json,
sha256 7b57b9e4178cd490a2b2a6437c24251d11783841448c84f5d7b7436e72ab33ad).

Answers R1 (reproduce accepted purity metric on PRODUCT artifacts) and R2
(size-matched permutation null: weak-alignment vs chance) of the frozen spec.

Does NOT cluster anything. Re-evaluates FROZEN product label arrays joined by
decision_id (provenance-safe). Output:
  results/fractal_map/tfidf_hierarchy_reconciliation_v1/reconciliation_results.json
"""
import json
import hashlib
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_rand_score as ARI
from sklearn.metrics import normalized_mutual_info_score as NMI

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
RES = ROOT / 'results/fractal_map'
OUTDIR = RES / 'tfidf_hierarchy_reconciliation_v1'
SPEC = OUTDIR / 'RECON_SPEC_FROZEN.json'
OUT = OUTDIR / 'reconciliation_results.json'
META = RES / 'multi_level_protocol_174k_tfidf' / 'metadata_174k_aligned.json'

EXPECTED_SHA = '7b57b9e4178cd490a2b2a6437c24251d11783841448c84f5d7b7436e72ab33ad'
MODES = [
    'full_text_tfidf_light',
    'regeste_full_text_hybrid_0.5',
    'regeste_full_text_hybrid_0.7',
    'cited_decisions_tfidf',
    'cited_decisions_tfidf_outcome_hybrid_0.5_174k',
    'regeste_tfidf_174k',
]
# accepted headline values from hierarchical_v1 verdict (direction v29)
ACCEPTED_HEADLINE = {
    'full_text_tfidf_light': 0.930,
    'regeste_full_text_hybrid_0.5': 0.906,
    'regeste_full_text_hybrid_0.7': 0.909,
}
N_PERM = 30
SEED = 12345
RNG = np.random.default_rng(SEED)


def spec_ok():
    h = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    assert h == EXPECTED_SHA, f'frozen spec hash mismatch: {h}'
    return h


def load_meta():
    meta = json.load(open(META))
    did = [m['decision_id'] for m in meta]
    branch = np.array([m.get('branch') if m.get('branch') not in (None, 'null', 'unknown')
                       else None for m in meta], dtype=object)
    area = np.array([m.get('legal_area') if m.get('legal_area') not in (None, 'null', 'unknown')
                     else None for m in meta], dtype=object)
    return did, branch, area


def accepted_purity(labels, values):
    """Accepted metric: mean over clusters of dominant-valid / n-valid."""
    purs = []
    for u in np.unique(labels):
        if u == -1:
            continue
        vals = values[labels == u]
        vals = vals[[v is not None for v in vals]]
        if len(vals):
            purs.append(Counter(vals.tolist()).most_common(1)[0][1] / len(vals))
    return float(np.mean(purs)) if purs else 0.0


def weighted_purity(labels, values):
    dom = tot = 0
    for u in np.unique(labels):
        if u == -1:
            continue
        vals = values[labels == u]
        vals = vals[[v is not None for v in vals]]
        if len(vals):
            dom += Counter(vals.tolist()).most_common(1)[0][1]
            tot += len(vals)
    return float(dom / tot) if tot else 0.0


def observed(labels, branch, area):
    m = {}
    m['accepted_purity_unweighted'] = accepted_purity(labels, branch)
    m['accepted_purity_weighted'] = weighted_purity(labels, branch)
    m['accepted_area_purity_unweighted'] = accepted_purity(labels, area)
    valid_b = np.array([v is not None for v in branch]) & (labels != -1)
    valid_a = np.array([v is not None for v in area]) & (labels != -1)
    bl = np.array([str(branch[i]) for i in np.where(valid_b)[0]])
    lb = labels[valid_b]
    m['ARI_branch'] = float(ARI(bl, lb)) if len(np.unique(bl)) > 1 and len(np.unique(lb)) > 1 else 0.0
    al = np.array([str(area[i]) for i in np.where(valid_a)[0]])
    la = labels[valid_a]
    m['NMI_area'] = float(NMI(al, la, average_method='arithmetic')) if len(np.unique(la)) > 1 else 0.0
    counts = np.bincount(labels[labels != -1])
    n = int((labels != -1).sum())
    m['n_labeled'] = n
    m['n_clusters'] = int(len(np.unique(labels[labels != -1])))
    m['singleton_fraction'] = float((counts == 1).sum() / n) if n else 0.0
    m['largest_cluster_fraction'] = float(counts.max() / n) if n else 0.0
    return m


def chance_weighted_branch(branch):
    vals = [b for b in branch if b is not None]
    c = Counter(vals)
    n = len(vals)
    return float(sum((v / n) ** 2 for v in c.values()))


def null_stats(labels, branch, area, obs):
    keys = ['accepted_purity_unweighted', 'accepted_purity_weighted', 'ARI_branch', 'NMI_area']
    acc = {k: [] for k in keys}
    for _ in range(N_PERM):
        perm = RNG.permutation(labels)
        o = observed(perm, branch, area)
        for k in keys:
            acc[k].append(o[k])
    out = {}
    for k in keys:
        arr = np.array(acc[k])
        mu, sd = float(arr.mean()), float(arr.std())
        out[k] = {'observed': obs[k], 'null_mean': mu, 'null_std': sd,
                  'z': float((obs[k] - mu) / sd) if sd > 0 else None,
                  'p_emp': float((np.sum(arr >= obs[k]) + 1) / (N_PERM + 1))}
    return out


def main():
    h = spec_ok()
    did, branch, area = load_meta()
    didx = {d: i for i, d in enumerate(did)}
    n = len(did)
    cw = chance_weighted_branch(branch)
    print(f'spec sha256 verified {h[:12]}... | n={n} | chance_weighted_branch={cw:.4f}')

    out = {'spec_id': 'tfidf_hierarchy_reconciliation_v1', 'spec_sha256': h,
           'n_decisions': n, 'chance_weighted_branch': cw,
           'accepted_headline': ACCEPTED_HEADLINE, 'modes': {}}

    for mode in MODES:
        base = RES / 'product_integration_174k' / mode
        dc_path = base / 'decision_clusters.json'
        if not dc_path.exists():
            out['modes'][mode] = {'error': 'missing decision_clusters.json'}
            continue
        dc = json.load(open(dc_path))
        schemes = set()
        for v in dc.values():
            schemes.update(v.keys())
        entry = {'schemes': {}}
        for scheme in sorted(schemes):
            lab = np.full(n, -1, dtype=np.int64)
            for k, v in dc.items():
                i = didx.get(k)
                if i is not None:
                    lab[i] = int(v[scheme])
            cov = float((lab != -1).mean())
            o = observed(lab, branch, area)
            o['join_coverage'] = cov
            entry['schemes'][scheme] = o
            if scheme in ('hierarchical', 'coarse'):
                entry['schemes'][scheme]['permutation_null'] = null_stats(lab, branch, area, o)
                print(f"  {mode:52s} {scheme:12s} uw={o['accepted_purity_unweighted']:.3f} "
                      f"w={o['accepted_purity_weighted']:.3f} ARI={o['ARI_branch']:.4f} "
                      f"ncl={o['n_clusters']}")
        if mode in ACCEPTED_HEADLINE and 'hierarchical' in entry['schemes']:
            prod = entry['schemes']['hierarchical']['accepted_purity_unweighted']
            entry['headline_comparison'] = {
                'accepted_headline_value': ACCEPTED_HEADLINE[mode],
                'product_artifact_value': prod,
                'absolute_gap': abs(ACCEPTED_HEADLINE[mode] - prod)}
        out['modes'][mode] = entry

    # frozen decision flags
    text_modes = [m for m in ACCEPTED_HEADLINE if m in out['modes']
                  and 'hierarchical' in out['modes'][m].get('schemes', {})]
    gaps = [out['modes'][m]['headline_comparison']['absolute_gap'] for m in text_modes]
    R1 = sum(1 for g in gaps if g > 0.20) >= 2
    prod_ari = [out['modes'][m]['schemes']['hierarchical']['ARI_branch'] for m in out['modes']
                if 'hierarchical' in out['modes'][m].get('schemes', {})]
    R2_weak = all(a < 0.10 for a in prod_ari) if prod_ari else False
    default_mode = 'cited_decisions_tfidf_outcome_hybrid_0.5_174k'
    R2_chance = False
    if default_mode in out['modes'] and 'hierarchical' in out['modes'][default_mode].get('schemes', {}):
        pn = out['modes'][default_mode]['schemes']['hierarchical'].get('permutation_null', {})
        if pn:
            k = 'accepted_purity_weighted'
            z = pn[k]['z']
            R2_chance = (z is not None and abs(z) < 2.0)
    out['decisions'] = {
        'R1_provenance_mismatch_confirmed': bool(R1),
        'R1_text_mode_gaps': {m: out['modes'][m]['headline_comparison']['absolute_gap'] for m in text_modes},
        'R2_product_agreement_weak_but_above_chance': bool(R2_weak),
        'R2_product_ari_values': {m: out['modes'][m]['schemes']['hierarchical']['ARI_branch']
                                   for m in out['modes']
                                   if 'hierarchical' in out['modes'][m].get('schemes', {})},
        'R2_default_purity_weighted_at_chance': bool(R2_chance),
        'R3_pending': True,
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print('\nDECISIONS:', json.dumps(out['decisions'], indent=1, default=str))
    print('Saved', OUT)
    return out


if __name__ == '__main__':
    main()
