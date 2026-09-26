#!/usr/bin/env python3
"""
Extended v26 zoom-quality evaluation on ALL 12 TF-IDF 174k modes with 5-level compressed ladder.

The v26 frozen evaluation only tested 4 modes. This script evaluates the other 8 modes
using the IDENTICAL success rule and metrics to see if ANY TF-IDF 174k mode passes.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import numpy as np

BASE = Path('/home/runner/work/LexMachina/LexMachina')
MODES_DIR = BASE / 'results/fractal_map/legal_distance_modes'
EVAL_DIR = BASE / 'results/fractal_map/zoom_quality_174k_eval'
EVAL_META = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3

# All 12 modes with 5-level compressed ladder at 174k
ALL_MODES = [
    "cited_decisions_tfidf_174k_compressed",
    "cited_decisions_tfidf_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "full_text_tfidf_light_174k_compressed",
    "outcome_tfidf_174k_compressed",
    "outcome_tfidf_174k_compressed_v25",
    "regeste_full_text_hybrid_0.5_174k_compressed",
    "regeste_full_text_hybrid_0.7_174k_compressed",
    "regeste_tfidf_174k",
]

# The 4 frozen modes from v26
FROZEN_MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "regeste_tfidf_174k",
]

# The 8 additional modes
ADDITIONAL_MODES = [m for m in ALL_MODES if m not in FROZEN_MODES]


def load_metadata():
    with open(EVAL_META) as f:
        return json.load(f)


def load_decision_clusters(mode):
    with open(MODES_DIR / mode / 'decision_clusters.json') as f:
        return json.load(f)


def load_labels(mode, res):
    return np.load(MODES_DIR / mode / f'labels_res_{res}.npy')


def purity_per_res(dc, meta_by_id, field):
    """Mean cluster purity per resolution (ID space; excludes 'unknown')."""
    out = {}
    for res in RESOLUTIONS:
        key = f'res_{res}'
        cluster_vals = {}
        for did, m in meta_by_id.items():
            val = m.get(field)
            if not val or val == 'unknown':
                continue
            c = dc[did][key]
            cluster_vals.setdefault(c, []).append(val)
        purities = []
        for c, vals in cluster_vals.items():
            if len(vals) < MIN_CLUSTER_SIZE:
                continue
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
        out[key] = {
            'mean_purity': round(float(np.mean(purities)), 4) if purities else None,
            'n_clusters_used': len(purities),
        }
    return out


def zoom_per_transition(dc, meta_by_id, field='branch'):
    """Zoom metrics per transition in ID space (canonical builder semantics)."""
    out = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser, finer = RESOLUTIONS[i], RESOLUTIONS[i + 1]
        ck, fk = f'res_{coarser}', f'res_{finer}'
        # id-level structure: (coarse cluster, fine cluster) for ALL ids
        id_pairs = {}
        for did in dc:
            id_pairs[did] = (dc[did][ck], dc[did][fk])
        # labeled values per cluster
        coarse_vals = {}
        fine_vals = {}
        for did, m in meta_by_id.items():
            if did not in id_pairs:
                continue
            val = m.get(field)
            if not val or val == 'unknown':
                continue
            cc, fc = id_pairs[did]
            coarse_vals.setdefault(cc, []).append(val)
            fine_vals.setdefault(fc, []).append(val)
        # membership counts (all ids)
        coarse_members = {}
        fine_members = {}
        for did, (cc, fc) in id_pairs.items():
            coarse_members.setdefault(cc, []).append(did)
            fine_members.setdefault(fc, []).append(did)
        # child -> parent: majority coarse cluster among ALL member ids
        fine_coarse_counter = {}
        for did, (cc, fc) in id_pairs.items():
            fine_coarse_counter.setdefault(fc, Counter())[cc] += 1
        child_to_parent = {fc: cc.most_common(1)[0][0]
                           for fc, cc in fine_coarse_counter.items() if cc}
        improvements = []
        n_parents = 0
        parent_details = {}
        for pc, cmems in coarse_members.items():
            if len(cmems) < MIN_CLUSTER_SIZE:          # parent >= 3 member ids
                continue
            cvals = coarse_vals.get(pc, [])
            if not cvals:                               # parent has >= 1 labeled decision
                continue
            # children of this parent with >= 3 labeled decisions
            child_clusters = [fc for fc, p in child_to_parent.items()
                              if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
            if not child_clusters:
                continue
            child_purities = []
            for fc in child_clusters:
                fvals = fine_vals[fc]
                child_purities.append(Counter(fvals).most_common(1)[0][1] / len(fvals))
            coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
            mean_child = float(np.mean(child_purities))
            improvements.append(mean_child - coarse_purity)
            parent_details[int(pc)] = {
                'coarse_purity': round(float(coarse_purity), 4),
                'mean_child_purity': round(mean_child, 4),
                'improvement': round(mean_child - coarse_purity, 4),
                'n_children': len(child_clusters),
            }
            n_parents += 1
        out[f'{ck}_to_{fk}'] = {
            'mean_improvement': round(float(np.mean(improvements)), 4) if improvements else None,
            'improvement_rate': round(float(sum(1 for j in improvements if j > 0) / len(improvements)), 4)
                                if improvements else None,
            'n_parents': n_parents,
            'parent_details': parent_details,
        }
    return out


def compute_nesting(labels_by_res):
    """Strict nesting from labels: fraction of fine clusters whose members share ONE unique coarse parent."""
    cross = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser, finer = RESOLUTIONS[i], RESOLUTIONS[i + 1]
        cl = labels_by_res[f'res_{coarser}']
        fl = labels_by_res[f'res_{finer}']
        n_strict = 0
        n_valid = 0
        for fid in np.unique(fl[fl != -1]):
            members = cl[fl == fid]
            members = members[members != -1]
            if len(members) == 0:
                continue
            n_valid += 1
            if len(set(members.tolist())) == 1:
                n_strict += 1
        cross[f'res_{coarser}_to_res_{finer}'] = round(n_strict / n_valid, 6) if n_valid else None
    return cross


def fragmentation_from_labels(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


def main():
    meta = load_metadata()
    meta_by_id = {m['decision_id']: m for m in meta}
    print(f"ACCEPTED metadata: {len(meta)} entries")
    print(f"  labeled branch: {sum(1 for m in meta if m.get('branch') and m['branch'] != 'unknown')}")
    print(f"  labeled area: {sum(1 for m in meta if m.get('legal_area') and m['legal_area'] != 'unknown')}")

    # baseline random purities
    branches = {m['branch'] for m in meta if m.get('branch') and m['branch'] != 'unknown'}
    areas = {m['legal_area'] for m in meta if m.get('legal_area') and m['legal_area'] != 'unknown'}
    baseline = {
        'branch_random': round(1 / len(branches), 4),
        'n_branch_classes': len(branches),
        'area_random': round(1 / len(areas), 4),
        'n_area_classes': len(areas),
    }
    print('baseline:', baseline)

    results = {
        'run_id': f'extended_v26_12_modes_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'modes': {}
    }

    # First, verify frozen modes match v26 verdict
    print("\n=== VERIFYING FROZEN MODES MATCH V26 VERDICT ===")
    v26_verdict = json.load(open(EVAL_DIR / 'v26_verdict.json'))
    
    for mode in FROZEN_MODES:
        print(f"\n=== {mode} (FROZEN) ===")
        dc = load_decision_clusters(mode)
        joined = sum(1 for did in meta_by_id if did in dc)
        labels_by_res = {f'res_{r}': load_labels(mode, r) for r in RESOLUTIONS}
        pur_b = purity_per_res(dc, meta_by_id, 'branch')
        pur_a = purity_per_res(dc, meta_by_id, 'legal_area')
        zoom_b = zoom_per_transition(dc, meta_by_id, 'branch')
        nesting = compute_nesting(labels_by_res)
        frag = {f'res_{r}': fragmentation_from_labels(labels_by_res[f'res_{r}']) for r in RESOLUTIONS}
        
        # per-mode checks (v25 success rule)
        b_mono = pur_b['res_3.0']['mean_purity'] > pur_b['res_0.25']['mean_purity']
        a_mono = pur_a['res_3.0']['mean_purity'] > pur_a['res_0.25']['mean_purity']
        rates = [v['improvement_rate'] for v in zoom_b.values()]
        rate_ok = sum(1 for r in rates if r is not None and r > 0.5) >= 2
        mode_pass = b_mono and a_mono and rate_ok
        
        # Cross-check with v26 verdict
        v26_entry = v26_verdict['modes'][mode]
        assert pur_b['res_0.25']['mean_purity'] == v26_entry['branch_purity']['res_0.25'], f"Branch purity mismatch at res_0.25 for {mode}"
        assert pur_b['res_3.0']['mean_purity'] == v26_entry['branch_purity']['res_3.0'], f"Branch purity mismatch at res_3.0 for {mode}"
        assert pur_a['res_0.25']['mean_purity'] == v26_entry['area_purity']['res_0.25'], f"Area purity mismatch at res_0.25 for {mode}"
        assert pur_a['res_3.0']['mean_purity'] == v26_entry['area_purity']['res_3.0'], f"Area purity mismatch at res_3.0 for {mode}"
        assert mode_pass == (v26_entry['per_mode_verdict'] == 'PASS'), f"Verdict mismatch for {mode}"
        
        entry = {
            'joined_to_meta': joined,
            'branch_purity': {k: v['mean_purity'] for k, v in pur_b.items()},
            'area_purity': {k: v['mean_purity'] for k, v in pur_a.items()},
            'zoom_branch': {k: {'mean_improvement': v['mean_improvement'],
                                'improvement_rate': v['improvement_rate'],
                                'n_parents': v['n_parents'], 'parent_details': v['parent_details']}
                            for k, v in zoom_b.items()},
            'checks': {
                'branch_monotonic_res3_vs_res0.25': bool(b_mono),
                'area_monotonic_res3_vs_res0.25': bool(a_mono),
                'improvement_rate_gt_0.5_on_2_of_4': bool(rate_ok),
            },
            'per_mode_verdict': 'PASS' if mode_pass else 'FAIL',
            'strict_nesting_recomputed': nesting,
            'fragmentation': frag,
            'labels_shape': list(labels_by_res['res_0.25'].shape),
            'decision_clusters_keys': len(dc),
        }
        results['modes'][mode] = entry
        print(f"  branch mono: {b_mono} ({pur_b['res_0.25']['mean_purity']} -> {pur_b['res_3.0']['mean_purity']}) | "
              f"area mono: {a_mono} | rate_ok: {rate_ok} ({[round(r,4) if r else None for r in rates]}) | verdict: {entry['per_mode_verdict']}")

    # Now evaluate additional modes
    print("\n=== EVALUATING ADDITIONAL MODES ===")
    for mode in ADDITIONAL_MODES:
        print(f"\n=== {mode} ===")
        dc = load_decision_clusters(mode)
        joined = sum(1 for did in meta_by_id if did in dc)
        labels_by_res = {f'res_{r}': load_labels(mode, r) for r in RESOLUTIONS}
        pur_b = purity_per_res(dc, meta_by_id, 'branch')
        pur_a = purity_per_res(dc, meta_by_id, 'legal_area')
        zoom_b = zoom_per_transition(dc, meta_by_id, 'branch')
        nesting = compute_nesting(labels_by_res)
        frag = {f'res_{r}': fragmentation_from_labels(labels_by_res[f'res_{r}']) for r in RESOLUTIONS}
        
        # per-mode checks (v25 success rule)
        b_mono = pur_b['res_3.0']['mean_purity'] > pur_b['res_0.25']['mean_purity']
        a_mono = pur_a['res_3.0']['mean_purity'] > pur_a['res_0.25']['mean_purity']
        rates = [v['improvement_rate'] for v in zoom_b.values()]
        rate_ok = sum(1 for r in rates if r is not None and r > 0.5) >= 2
        mode_pass = b_mono and a_mono and rate_ok
        
        entry = {
            'joined_to_meta': joined,
            'branch_purity': {k: v['mean_purity'] for k, v in pur_b.items()},
            'area_purity': {k: v['mean_purity'] for k, v in pur_a.items()},
            'zoom_branch': {k: {'mean_improvement': v['mean_improvement'],
                                'improvement_rate': v['improvement_rate'],
                                'n_parents': v['n_parents'], 'parent_details': v['parent_details']}
                            for k, v in zoom_b.items()},
            'checks': {
                'branch_monotonic_res3_vs_res0.25': bool(b_mono),
                'area_monotonic_res3_vs_res0.25': bool(a_mono),
                'improvement_rate_gt_0.5_on_2_of_4': bool(rate_ok),
            },
            'per_mode_verdict': 'PASS' if mode_pass else 'FAIL',
            'strict_nesting_recomputed': nesting,
            'fragmentation': frag,
            'labels_shape': list(labels_by_res['res_0.25'].shape),
            'decision_clusters_keys': len(dc),
        }
        results['modes'][mode] = entry
        print(f"  branch mono: {b_mono} ({pur_b['res_0.25']['mean_purity']} -> {pur_b['res_3.0']['mean_purity']}) | "
              f"area mono: {a_mono} ({pur_a['res_0.25']['mean_purity']} -> {pur_a['res_3.0']['mean_purity']}) | "
              f"rate_ok: {rate_ok} ({[round(r,4) if r else None for r in rates]}) | verdict: {entry['per_mode_verdict']}")
        print(f"  nesting: {nesting}")
        print(f"  frag res_3.0: n={frag['res_3.0']['n_clusters']}, median={frag['res_3.0']['median_size']:.1f}, singleton={frag['res_3.0']['singleton_fraction']}")

    results['baseline'] = baseline
    any_pass = any(results['modes'][m]['per_mode_verdict'] == 'PASS' for m in ALL_MODES)
    results['overall_verdict'] = 'PASS' if any_pass else 'FAIL'
    results['modes_tested'] = len(ALL_MODES)
    results['modes_passed'] = sum(1 for m in ALL_MODES if results['modes'][m]['per_mode_verdict'] == 'PASS')
    
    verdict_path = EVAL_DIR / f'v26_extended_12_modes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    verdict_path.write_text(json.dumps(results, indent=2) + '\n')
    print(f"\n{'='*60}")
    print(f"OVERALL VERDICT: {results['overall_verdict']} ({results['modes_passed']}/{results['modes_tested']} modes PASS)")
    print(f"VERDICT WRITTEN: {verdict_path}")
    print(f"{'='*60}")
    
    # Summary table
    print("\nSUMMARY:")
    for mode in ALL_MODES:
        m = results['modes'][mode]
        status = "FROZEN" if mode in FROZEN_MODES else "NEW"
        print(f"  {mode}: {m['per_mode_verdict']} [{status}] "
              f"branch={m['branch_purity']['res_0.25']:.4f}->{m['branch_purity']['res_3.0']:.4f} "
              f"area={m['area_purity']['res_0.25']:.4f}->{m['area_purity']['res_3.0']:.4f} "
              f"rates={[round(r,4) if r else None for r in [v['improvement_rate'] for v in m['zoom_branch'].values()]]}")


if __name__ == '__main__':
    main()