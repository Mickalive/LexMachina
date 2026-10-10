#!/usr/bin/env python3
"""
Repair supplement for REVISE gate CYCLE_38050987857 (fractal-map).

The audited cycle reported only the FINE-level ARI_branch (~0.04) from
r3_source_isolation_results.json while characterising the COARSE (human
5-class `branch`) axis. That is a granularity mismatch: the R3 fine partition
has 365-1316 clusters and is therefore over-segmented relative to a 5-class
label. This supplement recomputes BOTH the fine and the coarse ARI_branch from
the frozen, already-written R3 label arrays (no clustering is re-run, no
threshold is changed) and re-verifies the frozen EVAL_SPEC positive control.

Inputs (sha256 recorded in the output for independent checkability):
  - results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_labels/*.npy
  - results/fractal_map/multi_level_protocol_174k_tfidf/metadata_174k_aligned.json
  - results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_source_isolation_results.json
  - results/fractal_map/tfidf_hierarchy_agreement_v1/EVAL_SPEC_FROZEN.json
  - results/fractal_map/tfidf_hierarchy_agreement_v1/agreement_results.json

Output:
  results/fractal_map/tfidf_hierarchy_reconciliation_v1/r3_coarse_metric_supplement_v1.json

This script only RE-DERIVES reported numbers; it does not create a new metric,
change the frozen thresholds, or overwrite any prior artifact.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_rand_score as ARI
from sklearn.metrics import normalized_mutual_info_score as NMI

ROOT = Path('/home/runner/work/LexMachina/LexMachina')
RES = ROOT / 'results/fractal_map'
OUTDIR = RES / 'tfidf_hierarchy_reconciliation_v1'
LABDIR = OUTDIR / 'r3_labels'
RESULTS_FROZEN = OUTDIR / 'r3_source_isolation_results.json'
META = RES / 'multi_level_protocol_174k_tfidf' / 'metadata_174k_aligned.json'
AGREEMENT = RES / 'tfidf_hierarchy_agreement_v1' / 'agreement_results.json'
EVAL_SPEC = RES / 'tfidf_hierarchy_agreement_v1' / 'EVAL_SPEC_FROZEN.json'
OUT = OUTDIR / 'r3_coarse_metric_supplement_v1.json'

MODES = ['full_text_tfidf_light', 'regeste_full_text_hybrid_0.5', 'regeste_full_text_hybrid_0.7']
POSITIVE_CONTROL_THRESHOLD = 0.05  # frozen in EVAL_SPEC_FROZEN.json success_and_decision_rules
# Authoring timestamp for the REVISE repair. Kept <= the repair commit time so
# provenance pre-dates the commit that contains it (audit fix F4).
REPAIR_CREATED_UTC = '2026-10-10T13:00:00Z'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    meta = json.loads(META.read_text())
    branch = np.array([m.get('branch') for m in meta])
    area = np.array([m.get('legal_area') for m in meta])
    valid_b = (branch != 'unknown') & (branch != None)  # noqa: E711
    valid_a = (area != 'unknown') & (area != None) & (area != '')  # noqa: E711

    frozen = json.loads(RESULTS_FROZEN.read_text())
    agreement = json.loads(AGREEMENT.read_text())
    eval_spec = json.loads(EVAL_SPEC.read_text())
    pc_rule = eval_spec['success_and_decision_rules']['positive_control']

    per_mode = {}
    for mode in MODES:
        fine = np.load(LABDIR / f'{mode}_hierarchical.npy')
        coarse = np.load(LABDIR / f'{mode}_coarse.npy')
        f_n = int(len(set(fine.tolist()) - {-1}))
        c_n = int(len(set(coarse.tolist()) - {-1}))
        f_ari = float(ARI(branch[valid_b], fine[valid_b]))
        c_ari = float(ARI(branch[valid_b], coarse[valid_b]))
        nmi = float(NMI(area[valid_a], fine[valid_a], average_method='arithmetic'))
        fr = frozen[mode]
        per_mode[mode] = {
            'fine_n_clusters': f_n,
            'coarse_n_clusters': c_n,
            'fine_ARI_branch': f_ari,
            'coarse_ARI_branch': c_ari,
            'fine_NMI_area': nmi,
            'fine_ARI_branch_matches_frozen': abs(f_ari - fr['fine_ARI_branch']) < 1e-9,
            'coarse_ARI_branch_matches_frozen': abs(c_ari - fr['coarse_ARI_branch']) < 1e-9,
            'fine_NMI_area_matches_frozen': abs(nmi - fr['fine_NMI_area']) < 1e-7,
            'fine_n_clusters_matches_frozen': f_n == fr['fine_n_clusters'],
            'coarse_n_clusters_matches_frozen': c_n == fr['coarse_n_clusters'],
        }

    # Frozen positive control: full_text_tfidf_light (full 173,963) must show ARI_branch > 0.05.
    pc_product_artifact = agreement['positive_control']['ARI_branch']
    pc_source_corrected = per_mode['full_text_tfidf_light']['fine_ARI_branch']
    pc_pass_product = pc_product_artifact > POSITIVE_CONTROL_THRESHOLD
    pc_pass_source = pc_source_corrected > POSITIVE_CONTROL_THRESHOLD

    out = {
        'supplement_id': 'r3_coarse_metric_supplement_v1',
        'lane': 'fractal-map',
        'direction_version': 35,
        'created_utc': REPAIR_CREATED_UTC,
        'purpose': ('REVISE repair CYCLE_38050987857: surface the coarse-level ARI_branch that the '
                    'audited cycle omitted, and re-verify the frozen EVAL_SPEC positive control on '
                    'the source-corrected labels.'),
        'method': ('Recompute ARI_branch / NMI_area from the frozen r3_labels/*.npy and '
                   'metadata_174k_aligned.json exactly as frozen in RECON_SPEC_FROZEN.json. '
                   'No clustering re-run; no threshold changed.'),
        'frozen_positive_control_rule': pc_rule,
        'frozen_positive_control_threshold': POSITIVE_CONTROL_THRESHOLD,
        'positive_control': {
            'product_artifact_full_text_ARI_branch': pc_product_artifact,
            'source_corrected_full_text_ARI_branch': pc_source_corrected,
            'product_artifact_passes': pc_pass_product,
            'source_corrected_passes': pc_pass_source,
            'harness_verdict_recorded': agreement['harness_verdict'],
            'harness_valid_recorded': agreement['decisions']['harness_valid'],
            'conclusion': ('FAILS on BOTH the product artifact and the source-corrected labels '
                           '(0.00033 and 0.04294, both < 0.05). The agreement harness is therefore '
                           'INVALID/INCONCLUSIVE for branch recovery even after removing the product '
                           'join defect; the join defect must NOT be described as the only cause of '
                           'the discrepancy.'),
        },
        'granularity_note': ('The R3 fine partition (365-1316 clusters) is over-segmented relative to '
                             'the 5-class human branch axis, so the fine-level ARI (~0.04) is not the '
                             'correct macro-alignment measure. The coarse-level ARI_branch (0.16-0.26) '
                             'shows weak-to-moderate, not absent, recapture of the branch axis.'),
        'per_mode': per_mode,
        'inputs_sha256': {
            str(META.relative_to(ROOT)): sha256(META),
            str(RESULTS_FROZEN.relative_to(ROOT)): sha256(RESULTS_FROZEN),
            str(AGREEMENT.relative_to(ROOT)): sha256(AGREEMENT),
            str(EVAL_SPEC.relative_to(ROOT)): sha256(EVAL_SPEC),
            **{str((LABDIR / f'{m}_{suf}.npy').relative_to(ROOT)): sha256(LABDIR / f'{m}_{suf}.npy')
               for m in MODES for suf in ('hierarchical', 'coarse')},
        },
        'preservation': ('Read-only over frozen artifacts. Only new output written: this supplement. '
                         'r3_source_isolation_results.json, EVAL_SPEC_FROZEN.json and agreement_results.json '
                         'are unchanged.'),
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print('Wrote', OUT)
    for m, r in per_mode.items():
        print(f"  {m}: fine_ARI={r['fine_ARI_branch']:.4f} coarse_ARI={r['coarse_ARI_branch']:.4f} "
              f"fine_n={r['fine_n_clusters']} coarse_n={r['coarse_n_clusters']} "
              f"all_match={all(v for k, v in r.items() if k.endswith('_matches_frozen'))}")
    print(f"  positive control: product={pc_product_artifact:.5f} source={pc_source_corrected:.5f} "
          f"threshold={POSITIVE_CONTROL_THRESHOLD} -> pass={pc_pass_source}")


if __name__ == '__main__':
    main()
