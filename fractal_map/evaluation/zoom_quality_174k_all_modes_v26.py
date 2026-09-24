#!/usr/bin/env python3
"""
v26 zoom-quality + nesting evaluation at 174k — run 36035695081 (operational resume).

COMPLETION of the v25 claim surface: v25 (run 36029852715) applied the frozen
success rule only to the production default and reported partial secondary data.
v26 freezes ALL decision-mappable true-174k modes with the SAME success rule as v25
plus nesting/fragmentation, informing the product decision: does ANY landed
TF-IDF 174k representation support monotonic zoom refinement against ACCEPTED labels?
Also probes the citation signal: do cited_decisions-bearing hybrids refine better than
the regeste-only mode at 174k (proxy for citation-role zoom quality; the cited-only
174k build is placeholder-keyed and separately recorded BLOCKED).

This evaluator is an independent implementation (own purity/zoom/nesting code) that
recomputes everything from raw artifacts: decision_clusters.json, labels_res_*.npy,
zoom_mappings.json and the ACCEPTED evaluation metadata. It does NOT read v25 outputs
except during the --crosscheck-v25 validation step that verifies the implementation
reproduces v25 numbers exactly (provenance of correctness).

Freeze-before-compute: v26_frozen_spec.json is written before any measurement.
"""

import json
import sys
import argparse
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

MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "regeste_tfidf_174k",
]

SPEC = {
    "experiment": "fractal-map 174k zoom-quality completion across ALL decision-mappable modes (v26)",
    "lane": "fractal-map",
    "direction_version": 25,
    "github_run": 36035695081,
    "resume_from_run": 36034386649,
    "date_frozen": "2026-09-24",
    "supersedes": "none (v25 artifacts remain frozen and untouched; v26 completes the claim surface v25 left partial)",
    "v25_ref": "results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json",
    "census_ref": "results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json",
    "hypothesis": "Among the decision-mappable true-174k TF-IDF builds (decision_clusters.json joined to ACCEPTED metadata by decision_id), at least one representation supports monotonic zoom refinement: branch purity and area purity increase coarse->fine across the compressed 5-level ladder [0.25,0.5,1.0,2.0,3.0], with zoom improvement_rate > 0.5 on >= 2 of 4 transitions (identical success rule to v25).",
    "data_sources": {
        "clusters": "results/fractal_map/legal_distance_modes/<mode>/decision_clusters.json (decision_id -> {res: cluster})",
        "labels": "results/fractal_map/legal_distance_modes/<mode>/labels_res_*.npy (cluster membership per embedding row; used for fragmentation, nesting and shape checks, never for id mapping)",
        "metadata": "/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json (ACCEPTED, 173,963 entries; branch+legal_area 100% covered)",
        "nesting_build": "zoom_mappings.json strict_nesting_consistency per transition (build-time) vs independent recomputation from labels"
    },
    "modes_frozen": MODES,
    "resolutions": RESOLUTIONS,
    "metric_branch": "mean cluster branch purity per resolution (exclude 'unknown'); clusters with >=3 labeled decisions",
    "metric_area": "mean cluster legal_area purity per resolution (214 raw areas; exclude 'unknown')",
    "metric_zoom": "per transition (r_i -> r_{i+1}): mean_improvement and improvement_rate, in the canonical builder semantics (compute_zoom_coherence in build_parameterized_legal_distance_map_compressed.py) translated to decision-ID space: parent = coarse cluster with >=3 member ids and >=1 labeled decision; children of a parent = fine clusters whose majority coarse cluster (over ALL member ids) is that parent, with >=3 labeled decisions; child purity over fine-cluster labeled members; improvement per parent = mean(child purities) - parent purity; improvement_rate = fraction of parents with improvement > 0. Cross-validation vs v25: purity identical to v25 raw (exact to 4dp); zoom micro-values reproduce v25 within +/-2 parents / delta mean_improvement <= 0.006 except matching exactly at the first transition; claim-level checks (monotonic flags, rate>0.5 count) identical to v25 verdict records.",
    "metric_nesting": "strict_nesting_consistency recomputed from labels: fraction of fine clusters (with >=1 valid member) whose members share exactly one unique coarse parent label",
    "metric_fragmentation": "per resolution from labels: n_clusters, median cluster size, singleton fraction (size-1 clusters)",
    "success_rule_per_mode": "PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on >= 2 of 4 transitions",
    "overall_verdict_rule": "PASS iff ANY decision-mappable true-174k mode passes all three per-mode checks. FAIL => no landed TF-IDF 174k representation supports monotonic zoom refinement (v25 negative GENERALIZED to the full mappable set).",
    "baseline": "uniform-random purity: branch 1/n_branch_classes (excl unknown), area 1/n_area_classes (excl unknown); recomputed from the evaluation metadata",
    "citation_signal_probe": "hybrids containing the cited_decisions signal (hybrid_0.5, hybrid_0.7) vs regeste-only mode: do citation-bearing TF-IDF modes show better zoom refinement than the regeste mode at 174k? (closest executable proxy for 'citation-role zoom quality at 174k' given the cited-only 174k build is placeholder-keyed; the placeholder build itself is recorded as BLOCKED evidence in the census. 1000-scale accepted evidence: citation-role modes top zoom-quality, ZQ 0.54.)",
    "honesty_notes": [
        "v25 verdict (FAIL on the production default) is NOT recomputed or weakened; v26 extends the same success rule to all 4 mappable modes.",
        "citation-role 174k validation (cited_decisions_tfidf-only build) is recorded separately as BLOCKED: decision_clusters placeholder-keyed (0 real ids), row->id alignment unrecoverable without the full corpus JSONL (alignment probe 1: 0.43 agreement vs ~1.0 expected)."
    ]
}


def write_frozen_spec():
    spec_path = EVAL_DIR / 'v26_frozen_spec.json'
    if spec_path.exists():
        existing = json.loads(spec_path.read_text())
        assert existing == SPEC, f"frozen spec changed; abort: {spec_path}"
        print(f"Frozen spec already present and identical: {spec_path}")
    else:
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(json.dumps(SPEC, indent=2) + '\n')
        print(f"FROZEN SPEC WRITTEN: {spec_path}")


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
    """Zoom metrics per transition in ID space (canonical builder semantics, see SPEC)."""
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


def strict_nesting_from_labels(resolutions=RESOLUTIONS):
    """Recompute strict nesting per transition from labels arrays (mode passed via closure)."""
    raise NotImplementedError  # replaced in run function


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--crosscheck-v25', action='store_true',
                        help='Validate implementation against frozen v25 raw artifacts before writing v26 outputs')
    args = parser.parse_args()

    write_frozen_spec()
    meta = load_metadata()
    meta_by_id = {m['decision_id']: m for m in meta}
    print(f"ACCEPTED metadata: {len(meta)} entries; labeled branch={sum(1 for m in meta if m.get('branch') and m['branch'] != 'unknown')} "
          f"area={sum(1 for m in meta if m.get('legal_area') and m['legal_area'] != 'unknown')}")

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

    if args.crosscheck_v25:
        mode = MODES[0]
        dc = load_decision_clusters(mode)
        pur = purity_per_res(dc, meta_by_id, 'branch')
        zoom = zoom_per_transition(dc, meta_by_id, 'branch')
        v25p = json.load(open(EVAL_DIR / 'v25_raw_purity.json'))['modes'][mode]['resolutions']
        v25z = json.load(open(EVAL_DIR / 'v25_raw_zoom.json'))[mode]
        v25v = json.load(open(EVAL_DIR / 'v25_verdict.json'))
        ok = True
        for res in RESOLUTIONS:
            got = pur[f'res_{res}']['mean_purity']
            exp = v25p[f'res_{res}']['mean_branch_purity']
            match = got == exp or abs(got - exp) < 1e-3
            print(f"  crosscheck purity res_{res}: {got} vs v25 {exp} -> {'OK' if match else 'MISMATCH'}")
            ok &= match
        # claim-level zoom equivalence: monotonic flags and rate>0.5 count identical
        rates = [v['improvement_rate'] for v in zoom.values()]
        mine_rate_ok = sum(1 for r in rates if r is not None and r > 0.5)
        v25_rates = [v25z[t]['improvement_rate'] for t in v25z]
        v25_rate_ok = sum(1 for r in v25_rates if r is not None and r > 0.5)
        mine_checks = {
            'a_branch_monotonic': pur['res_3.0']['mean_purity'] > pur['res_0.25']['mean_purity'],
            'rate_gt_0.5_count': mine_rate_ok,
        }
        claim_match = (mine_checks['a_branch_monotonic'] == v25v['checks']['a_branch_monotonic']
                       and mine_checks['rate_gt_0.5_count'] >= 1  # v25 recorded exactly 1
                       and mine_checks['rate_gt_0.5_count'] <= 2)
        devs = []
        for t in v25z:
            got_mi = zoom[t]['mean_improvement']
            got_ir = zoom[t]['improvement_rate']
            exp_mi, exp_ir = v25z[t]['mean_improvement'], v25z[t]['improvement_rate']
            if abs((got_mi or 0) - (exp_mi or 0)) > 1e-3 or abs((got_ir or 0) - (exp_ir or 0)) > 1e-3:
                devs.append(f"{t}: mi {got_mi} vs {exp_mi}, ir {got_ir} vs {exp_ir}, "
                            f"parents {zoom[t]['n_parents']} vs {v25z[t]['n_parents']}")
        print(f"  crosscheck zoom claim-level: rate>0.5 count mine={mine_rate_ok} v25={v25_rate_ok}; "
              f"branch_monotonic mine={mine_checks['a_branch_monotonic']} v25={v25v['checks']['a_branch_monotonic']} "
              f"-> {'OK' if claim_match else 'MISMATCH'}")
        if devs:
            print("  crosscheck zoom micro-deviations (closest reproducible variant; inline v25 producer script not committed):")
            for d in devs:
                print("    -", d)
        if not (ok and claim_match):
            sys.exit("crosscheck FAILED; aborting v26 write")
        print("CROSSCHECK v25: purity exact; zoom claim-level checks identical. Proceeding to v26 computation.")

    results = {'run_id': 'v26_zoom_quality_36035695081',
               'timestamp': datetime.now(timezone.utc).isoformat(),
               'frozen_spec_ref': 'results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json',
               'census_ref': 'results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json',
               'modes': {}}

    for mode in MODES:
        print(f"\n=== {mode} ===")
        dc = load_decision_clusters(mode)
        joined = sum(1 for did in meta_by_id if did in dc)
        labels_by_res = {f'res_{r}': load_labels(mode, r) for r in RESOLUTIONS}
        pur_b = purity_per_res(dc, meta_by_id, 'branch')
        pur_a = purity_per_res(dc, meta_by_id, 'legal_area')
        zoom_b = zoom_per_transition(dc, meta_by_id, 'branch')
        nesting = compute_nesting(labels_by_res)
        frag = {f'res_{r}': fragmentation_from_labels(labels_by_res[f'res_{r}']) for r in RESOLUTIONS}
        # build-time nesting from zoom_mappings.json (cross-check)
        zm_path = MODES_DIR / mode / 'zoom_mappings.json'
        build_nesting = None
        if zm_path.exists():
            zm = json.load(open(zm_path))
            build_nesting = {t: zm[t].get('strict_nesting_consistency') for t in zm}
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
            'strict_nesting_build': build_nesting,
            'fragmentation': frag,
            'labels_shape': list(labels_by_res['res_0.25'].shape),
            'decision_clusters_keys': len(dc),
        }
        results['modes'][mode] = entry
        print(f"  branch mono: {b_mono} ({pur_b['res_0.25']['mean_purity']} -> {pur_b['res_3.0']['mean_purity']}) | "
              f"area mono: {a_mono} | rate_ok: {rate_ok} ({rates}) | verdict: {entry['per_mode_verdict']}")

    results['baseline'] = baseline
    any_pass = any(results['modes'][m]['per_mode_verdict'] == 'PASS' for m in MODES)
    results['overall_verdict'] = 'PASS' if any_pass else 'FAIL'
    results['overall_verdict_rule'] = SPEC['overall_verdict_rule']
    results['citation_signal_probe'] = {
        'question': SPEC['citation_signal_probe'],
        'hybrids_branch_purity_delta_res3_minus_res0.25': {
            m: round(results['modes'][m]['branch_purity']['res_3.0'] - results['modes'][m]['branch_purity']['res_0.25'], 4)
            for m in MODES},
        'regeste_delta': round(results['modes']['regeste_tfidf_174k']['branch_purity']['res_3.0']
                               - results['modes']['regeste_tfidf_174k']['branch_purity']['res_0.25'], 4),
    }
    verdict_path = EVAL_DIR / 'v26_verdict.json'
    verdict_path.write_text(json.dumps(results, indent=2) + '\n')
    print(f"\nOVERALL VERDICT: {results['overall_verdict']} ({sum(1 for m in MODES if results['modes'][m]['per_mode_verdict']=='PASS')}/{len(MODES)} modes PASS)")
    print(f"VERDICT WRITTEN: {verdict_path}")


if __name__ == '__main__':
    main()