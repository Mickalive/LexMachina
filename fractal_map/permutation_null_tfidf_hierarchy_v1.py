#!/usr/bin/env python3
"""
Permutation-null calibration for TF-IDF hierarchy agreement (frozen spec
tfidf_hierarchy_agreement_v1).

For each FROZEN label scheme we compute observed agreement metrics against human
branch / legal_area and compare with a size-matched permutation null (shuffle
labels), reporting z-score and empirical p-value. This corrects for the fact that
purity grows mechanically with cluster count.
"""
import json, numpy as np, os
from pathlib import Path
from collections import Counter
from sklearn.metrics import adjusted_rand_score as ARI, normalized_mutual_info_score as NMI

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
RES = ROOT / 'results/fractal_map'
OUT = RES / 'tfidf_hierarchy_agreement_v1' / 'permutation_null_results.json'
RNG = np.random.default_rng(12345)
N_PERM = 30


def load_meta():
    meta = json.load(open(RES / 'multi_level_protocol_174k_tfidf' / 'metadata_174k_aligned.json'))
    branch = np.array([m.get('branch') if m.get('branch') not in (None, 'null', 'unknown') else None for m in meta], dtype=object)
    area = np.array([m.get('legal_area') if m.get('legal_area') not in (None, 'null', 'unknown') else None for m in meta], dtype=object)
    return [m['decision_id'] for m in meta], branch, area


def mean_purity(labels, vals):
    pur = []
    for u in np.unique(labels):
        v = vals[labels == u]
        v = v[np.array([x is not None for x in v])]
        if len(v):
            pur.append(Counter(v.tolist()).most_common(1)[0][1] / len(v))
    return float(np.mean(pur)) if pur else 0.0


def observed(labels, branch, area):
    vb = np.array([x is not None for x in branch]); va = np.array([x is not None for x in area])
    b = branch[vb].astype(str); l = labels[vb]
    o = {}
    o['ARI_branch'] = float(ARI(b, l)) if len(np.unique(l)) > 1 else 0.0
    o['mean_purity_branch'] = mean_purity(l, branch[vb])
    a = area[va].astype(str); la = labels[va]
    o['NMI_area'] = float(NMI(a, la, average_method='arithmetic')) if len(np.unique(la)) > 1 else 0.0
    o['mean_purity_area'] = mean_purity(la, area[va])
    o['n_clusters'] = int(len(np.unique(labels)))
    return o


def null_stats(labels, branch, area, obs):
    keys = list(obs.keys())
    acc = {k: [] for k in keys}
    for _ in range(N_PERM):
        perm = RNG.permutation(labels)
        for k, v in observed(perm, branch, area).items():
            if k in acc:
                acc[k].append(v)
    out = {}
    for k in keys:
        arr = np.array(acc[k])
        mu, sd = arr.mean(), arr.std()
        out[k] = {'observed': obs[k], 'null_mean': float(mu), 'null_std': float(sd),
                  'z': float((obs[k] - mu) / sd) if sd > 0 else None,
                  'p_emp': float((np.sum(arr >= obs[k]) + 1) / (N_PERM + 1))}
    return out


def main():
    did, branch, area = load_meta()
    didx = {d: i for i, d in enumerate(did)}
    results = {'n_perm': N_PERM, 'schemes': {}}

    # collect schemes: product integration + flat resolutions (joined by decision_id)
    base = RES / 'product_integration_174k'
    for mode_dir in sorted(base.iterdir()):
        dc = mode_dir / 'decision_clusters.json'
        if not dc.exists():
            continue
        mapping = json.load(open(dc))
        schemes = set()
        for v in mapping.values():
            schemes.update(v.keys())
        for s in sorted(schemes):
            lab = np.array([-1] * len(did), dtype=np.int64)
            for k, v in mapping.items():
                i = didx.get(k)
                if i is not None:
                    lab[i] = int(v[s])
            obs = observed(lab, branch, area)
            results['schemes'][f'product::{mode_dir.name}::{s}'] = null_stats(lab, branch, area, obs)

    # multi-level JSON level labels (positional, same metadata file used by its runner)
    for sub in ('multi_level_protocol_174k_tfidf', 'multi_level_protocol_174k_tfidf_calibrated'):
        d = RES / sub
        if not d.exists():
            continue
        for mode_dir in sorted(d.iterdir()):
            if not mode_dir.is_dir():
                continue
            for jf in sorted(mode_dir.glob('*.json')):
                obj = json.load(open(jf))
                if 'level_labels' not in obj:
                    continue
                for lvl, lab in obj['level_labels'].items():
                    lab = np.asarray(lab)
                    if len(lab) != len(did):
                        continue
                    obs = observed(lab, branch, area)
                    results['schemes'][f'{sub}::{mode_dir.name}::L{lvl}'] = null_stats(lab, branch, area, obs)

    with open(OUT, 'w') as f:
        json.dump(results, f, indent=2)

    # report top schemes by ARI z / p
    rows = []
    for k, v in results['schemes'].items():
        rows.append((v['ARI_branch']['z'], v['ARI_branch']['p_emp'],
                     v['ARI_branch']['observed'], v['NMI_area']['z'],
                     v['NMI_area']['p_emp'], v['NMI_area']['observed'],
                     v['n_clusters']['observed'], k))
    rows.sort(reverse=True)
    print(f"{'z_ARI':>7} {'p_ARI':>6} {'ARI':>7} {'z_NMI':>7} {'p_NMI':>6} {'NMI':>7} {'ncl':>7}  scheme")
    for r in rows[:25]:
        print(f"{r[0]:7.2f} {r[1]:6.3f} {r[2]:7.4f} {r[3]:7.2f} {r[4]:6.3f} {r[5]:7.4f} {r[6]:7d}  {r[7]}")
    print('...')
    print('total schemes:', len(rows))
    n_sig_branch = sum(1 for r in rows if r[1] < 0.05)
    n_sig_area = sum(1 for r in rows if r[4] < 0.05)
    print(f'schemes with p<0.05 ARI_branch: {n_sig_branch}/{len(rows)}; NMI_area: {n_sig_area}/{len(rows)}')
    print('Saved', OUT)


if __name__ == '__main__':
    main()
