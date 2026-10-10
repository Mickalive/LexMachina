#!/usr/bin/env python3
"""
Frozen evaluation: TF-IDF hierarchy agreement with human legal indexing.

Spec: results/fractal_map/tfidf_hierarchy_agreement_v1/EVAL_SPEC_FROZEN.json
sha256: 7d290f6bc2b8e61a7b41a5ee56959333e6b1fe43137bcc4e71aec0bd9e16c4a3

This script does NOT re-cluster. It re-evaluates FROZEN label arrays
(preserving provenance) using cluster/human-label agreement metrics
(ARI/NMI/V-measure) instead of the gameable purity-threshold success rule.

Outputs: results/fractal_map/tfidf_hierarchy_agreement_v1/agreement_results.json
"""
import json
import hashlib
import math
import os
from pathlib import Path
from collections import Counter

import numpy as np
from sklearn.metrics import (adjusted_rand_score, normalized_mutual_info_score,
                             v_measure_score)

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
RES = ROOT / 'results/fractal_map'
SPEC = RES / 'tfidf_hierarchy_agreement_v1' / 'EVAL_SPEC_FROZEN.json'
OUT = RES / 'tfidf_hierarchy_agreement_v1' / 'agreement_results.json'
META = RES / 'multi_level_protocol_174k_tfidf' / 'metadata_174k_aligned.json'

EXPECTED_SPEC_SHA = '7d290f6bc2b8e61a7b41a5ee56959333e6b1fe43137bcc4e71aec0bd9e16c4a3'


def spec_ok():
    h = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    assert h == EXPECTED_SPEC_SHA, f'spec hash mismatch {h}'
    return h


def load_metadata():
    with open(META) as f:
        meta = json.load(f)
    n = len(meta)
    did = [m.get('decision_id') for m in meta]
    branch = np.array([m.get('branch') if m.get('branch') not in (None, 'null', 'unknown')
                       else None for m in meta], dtype=object)
    area = np.array([m.get('legal_area') if m.get('legal_area') not in (None, 'null', 'unknown')
                     else None for m in meta], dtype=object)
    return meta, did, branch, area


def metrics(labels, branch, area):
    """Compute frozen agreement metrics on valid-label subsets."""
    labels = np.asarray(labels)
    out = {}
    valid_b = np.array([b is not None for b in branch])
    valid_a = np.array([a is not None for a in area])
    out['valid_branch_fraction'] = float(valid_b.mean())
    out['valid_area_fraction'] = float(valid_a.mean())
    lb = labels[valid_b]
    bb = np.array([str(branch[i]) for i in np.where(valid_b)[0]])
    la = labels[valid_a]
    aa = np.array([str(area[i]) for i in np.where(valid_a)[0]])
    if len(np.unique(lb)) > 1 and len(np.unique(bb)) > 1:
        out['ARI_branch'] = float(adjusted_rand_score(bb, lb))
    else:
        out['ARI_branch'] = 0.0
    if len(np.unique(la)) > 1 and len(np.unique(aa)) > 1:
        out['NMI_area'] = float(normalized_mutual_info_score(aa, la, average_method='arithmetic'))
        out['ARI_area'] = float(adjusted_rand_score(aa, la))
        out['Vmea_area'] = float(v_measure_score(aa, la))
    else:
        out['NMI_area'] = 0.0
        out['ARI_area'] = 0.0
        out['Vmea_area'] = 0.0
    # diagnostics on full sample
    _, counts = np.unique(labels, return_counts=True)
    out['n_clusters'] = int(len(counts))
    out['largest_cluster_fraction'] = float(counts.max() / len(labels))
    out['singleton_fraction'] = float(np.sum(counts == 1) / len(labels))
    out['median_cluster_size'] = float(np.median(counts))
    out['n'] = int(len(labels))
    # frozen structural usability
    out['structurally_usable'] = bool(out['n_clusters'] >= 10 and
                                      out['largest_cluster_fraction'] <= 0.50 and
                                      out['singleton_fraction'] < 0.01)
    out['recovers_branch'] = bool(out['ARI_branch'] > 0.10)
    return out


def eval_product_integration(meta, did, branch, area):
    """Use decision_clusters.json (decision_id-joined, provenance-safe)."""
    base = RES / 'product_integration_174k'
    did_index = {d: i for i, d in enumerate(did)}
    results = {}
    if not base.exists():
        return results
    for mode_dir in sorted(base.iterdir()):
        dc = mode_dir / 'decision_clusters.json'
        if not dc.exists():
            continue
        with open(dc) as f:
            mapping = json.load(f)
        # build per-scheme label arrays aligned to metadata order
        schemes = set()
        for v in mapping.values():
            schemes.update(v.keys())
        schemes = sorted(schemes)
        per_scheme = {s: np.array([-1] * len(did), dtype=np.int64) for s in schemes}
        covered = np.zeros(len(did), dtype=bool)
        for k, v in mapping.items():
            i = did_index.get(k)
            if i is None:
                continue
            covered[i] = True
            for s, lab in v.items():
                per_scheme[s][i] = int(lab)
        # only evaluate rows we can join for ALL schemes; use covered rows
        idx = np.where(covered)[0]
        entry = {'join_coverage': float(covered.mean()),
                 'n_joined': int(covered.sum()), 'schemes': {}}
        for s in schemes:
            lab = per_scheme[s][idx]
            m = metrics(lab, branch[idx], area[idx])
            entry['schemes'][s] = m
        results[mode_dir.name] = entry
    return results


def eval_multi_level(meta, did, branch, area, subdir):
    base = RES / subdir
    results = {}
    if not base.exists():
        return results
    for mode_dir in sorted(base.iterdir()):
        if not mode_dir.is_dir():
            continue
        for jf in sorted(mode_dir.glob('*.json')):
            with open(jf) as f:
                d = json.load(f)
            if 'level_labels' not in d:
                continue
            entry = {'file': str(jf.relative_to(ROOT)), 'levels': {}}
            for lvl, lab in d['level_labels'].items():
                lab = np.asarray(lab)
                if len(lab) != len(did):
                    entry['levels'][lvl] = {'error': f'length {len(lab)} != {len(did)}'}
                    continue
                entry['levels'][lvl] = metrics(lab, branch, area)
            results[mode_dir.name] = entry
    return results


def main():
    h = spec_ok()
    meta, did, branch, area = load_metadata()
    print(f'metadata: {len(meta)} decisions; spec sha256 verified {h[:12]}...')
    print('branch distribution (valid):', Counter([str(b) for b in branch if b is not None]).most_common())
    print('area distinct (valid):', len(set(str(a) for a in area if a is not None)))

    out = {'spec_id': 'tfidf_hierarchy_agreement_v1',
           'spec_sha256': h,
           'n_decisions': len(meta),
           'positive_control': {},
           'product_integration': {},
           'multi_level_original': {},
           'multi_level_calibrated': {},
           'flat_leiden_matched': {},
           'decisions': {}}

    out['product_integration'] = eval_product_integration(meta, did, branch, area)
    out['multi_level_original'] = eval_multi_level(meta, did, branch, area,
                                                   'multi_level_protocol_174k_tfidf')
    out['multi_level_calibrated'] = eval_multi_level(meta, did, branch, area,
                                                     'multi_level_protocol_174k_tfidf_calibrated')

    # flat Leiden matched granularity from product_integration res_* schemes already captured.

    # Positive control: full_text_tfidf_light hierarchical level (from decision_clusters join)
    pc = None
    fi = out['product_integration'].get('full_text_tfidf_light')
    if fi and 'hierarchical' in fi['schemes']:
        pc = fi['schemes']['hierarchical']
    elif 'full_text_tfidf_light' in out['multi_level_original']:
        lv = out['multi_level_original']['full_text_tfidf_light']['levels']
        pc = lv.get(str(max(int(k) for k in lv)))
    out['positive_control'] = pc or {'error': 'no positive control artifact found'}
    pc_pass = pc is not None and pc.get('ARI_branch', 0) > 0.05

    # -------------------- decided outcomes (frozen rules) --------------------
    dec = {}
    # H1: production 2-level beats flat matched.
    h1 = False
    h1_detail = []
    for mode, e in out['product_integration'].items():
        fine = e['schemes'].get('hierarchical')
        if not fine:
            continue
        for rs, flat in e['schemes'].items():
            if not rs.startswith('res_'):
                continue
            if flat['n_clusters'] >= 10 and fine['n_clusters'] <= 2 * max(flat['n_clusters'], 1):
                if fine['ARI_branch'] > flat['ARI_branch']:
                    h1 = True
                    h1_detail.append({'mode': mode, 'flat_scheme': rs,
                                      'fine_ARI': fine['ARI_branch'],
                                      'flat_ARI': flat['ARI_branch']})
    dec['H1_supported'] = bool(h1)
    dec['H1_detail'] = h1_detail

    # H2: multi-level adds little / degenerate
    h2 = False
    h2_detail = []
    for src in ('multi_level_original', 'multi_level_calibrated'):
        for mode, e in out[src].items():
            lv = {int(k): v for k, v in e['levels'].items() if 'error' not in v}
            if not lv:
                continue
            top = max(lv)
            coarse = lv.get(1)
            finest = lv.get(top)
            if coarse and finest:
                gain = finest['ARI_branch'] - coarse['ARI_branch']
                degen = finest['largest_cluster_fraction'] > 0.50
                if gain < 0.02 or degen:
                    h2 = True
                h2_detail.append({'src': src, 'mode': mode, 'levels': top,
                                  'coarse_ARI': coarse['ARI_branch'],
                                  'finest_ARI': finest['ARI_branch'],
                                  'gain': gain,
                                  'coarse_LCF': coarse['largest_cluster_fraction'],
                                  'finest_LCF': finest['largest_cluster_fraction'],
                                  'degenerate': degen})
    dec['H2_supported'] = bool(h2)
    dec['H2_detail'] = h2_detail

    # H3: regeste_tfidf zero-purity defect
    reg = out['product_integration'].get('regeste_tfidf_174k', {}).get('schemes', {}).get('hierarchical')
    h3 = False
    h3_detail = {}
    if reg:
        h3 = (reg['ARI_branch'] == 0.0 and reg['NMI_area'] == 0.0 and reg['valid_branch_fraction'] > 0.4) \
             or reg['n_clusters'] > 10000
        h3_detail = {'n_clusters': reg['n_clusters'],
                     'ARI_branch': reg['ARI_branch'], 'NMI_area': reg['NMI_area'],
                     'valid_branch_fraction': reg['valid_branch_fraction'],
                     'fragmentation_defect': reg['n_clusters'] > 10000,
                     'zero_agreement_defect': reg['ARI_branch'] == 0.0}
    dec['H3_supported'] = bool(h3)
    dec['H3_detail'] = h3_detail
    dec['positive_control_pass'] = bool(pc_pass)
    dec['harness_valid'] = bool(pc_pass)

    # production recommendation (frozen: highest ARI_branch among structurally usable levels)
    candidates = []
    for mode, e in out['product_integration'].items():
        fine = e['schemes'].get('hierarchical')
        if fine and fine['structurally_usable']:
            candidates.append((fine['ARI_branch'], mode, 'fine', fine['n_clusters']))
        coarse = e['schemes'].get('coarse')
        if coarse and coarse['structurally_usable']:
            candidates.append((coarse['ARI_branch'], mode, 'coarse', coarse['n_clusters']))
    for src in ('multi_level_original', 'multi_level_calibrated'):
        for mode, e in out[src].items():
            for lvl, v in e['levels'].items():
                if v.get('structurally_usable'):
                    candidates.append((v['ARI_branch'], f'{src}:{mode}', f'L{lvl}', v['n_clusters']))
    candidates.sort(reverse=True)
    dec['recommended_production'] = [
        {'ARI_branch': c[0], 'artifact': c[1], 'level': c[2], 'n_clusters': c[3]}
        for c in candidates[:8]]

    out['decisions'] = dec
    out['harness_verdict'] = 'VALID' if pc_pass else 'INCONCLUSIVE_POSITIVE_CONTROL_FAILED'

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2, default=str)

    # console summary
    print('\n=== POSITIVE CONTROL (full_text_tfidf_light hierarchical) ===')
    print(json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in (pc or {}).items()
                      if k in ('ARI_branch', 'NMI_area', 'n_clusters', 'largest_cluster_fraction',
                               'singleton_fraction', 'structurally_usable')}, indent=1))
    print('\n=== DECISIONS ===')
    print('H1 2-level beats flat:', dec['H1_supported'], '| control', dec['positive_control_pass'])
    print('H2 multi-level adds little/degenerate:', dec['H2_supported'])
    print('H3 regeste_tfidf defect:', dec['H3_supported'], h3_detail)
    print('recommended:', json.dumps(dec['recommended_production'][:3], indent=1))
    print(f'\nSaved {OUT}')
    return out


if __name__ == '__main__':
    main()
