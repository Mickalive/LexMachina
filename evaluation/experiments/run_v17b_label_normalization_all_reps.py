#!/usr/bin/env python3
"""
Evaluation v17b: Normalize-vs-raw hierarchy-family benchmarks across ALL 6
representations (baseline + hybrid + 4 v15 combinations).

Extends v17 (baseline only) to confirm the cross-lingual label-normalization
effect is UNIFORM across representations, i.e. that v16's hierarchy-family
FAIL was a shared label artifact, not representation-specific. Directly checks
whether the product-integration recommendation (linear_hybrid05_concat /
linear_citation_concat / linear_citation_ridge) is robust to label hygiene.

Frozen hypothesis: for EVERY representation, normalized labels improve or match
raw on the three hierarchy-family purity metrics (no representation is made
worse by a material margin).
"""

import json
import sys
import time
import numpy as np
import logging
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import run_v16_full_benchmark_suite as v16
from run_v17_label_normalization import (
    make_label_variants, run_one, RAW_BASELINE, load_data, load_embeddings,
)
from legal_area_normalize import normalize_legal_area

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

REPS = [
    'center_projected_64dim',
    'cited_outcome_hybrid_0.5',
    'linear_citation_concat',
    'linear_hybrid05_concat',
    'linear_citation_w3070',
    'linear_citation_ridge',
]


def main():
    t0 = time.time()
    # Use v16's load_data (adds branch) so build_all_representations is identical
    decisions, metadata = v16.load_data()
    cp_64_full = np.load(v16.EMBEDDINGS_64_PATH)
    cp_64 = cp_64_full[:len(decisions)]
    reps = v16.build_all_representations(decisions, cp_64)

    raw_labels, norm_labels, n_norm = make_label_variants(decisions, metadata)
    logger.info(f"labels normalized: {n_norm}/{len(metadata)}")

    out = {
        "run_id": f"eval_v17b_label_normalization_all_reps_{int(time.time())}",
        "direction_version": 13,
        "seed": v16.FROZEN_SEED,
        "n_labels_normalized": n_norm,
        "per_representation": {},
    }

    for name in REPS:
        emb = reps[name]
        raw_res = run_one(emb, raw_labels, "raw")
        norm_res = run_one(emb, norm_labels, "normalized")
        # purity ratios (normalized/raw, live same-machinery)
        def ratio(a, b):
            return round((a / b), 4) if b else (None)
        out["per_representation"][name] = {
            "raw": raw_res,
            "normalized": norm_res,
            "purity_ratios_norm_over_raw": {
                "hierarchy": ratio(norm_res["hierarchy_coherence"]["best_purity"],
                                   raw_res["hierarchy_coherence"]["best_purity"]),
                "zoom_fine": ratio(norm_res["zoom_coherence"]["fine_purity"],
                                   raw_res["zoom_coherence"]["fine_purity"]),
                "legal_area": ratio(norm_res["legal_area_clustering"]["overall_purity"],
                                    raw_res["legal_area_clustering"]["overall_purity"]),
            },
            "norm_num_areas": norm_res["legal_area_clustering"]["num_areas"],
        }
        logger.info(f"{name}: ratios {out['per_representation'][name]['purity_ratios_norm_over_raw']}")

    # Uniformity check: every rep has hierarchy_purity_ratio >= 1 and none worsens by >10%
    worsened = {}
    for name, d in out["per_representation"].items():
        for k, v in d["purity_ratios_norm_over_raw"].items():
            if v is not None and v < 0.9:
                worsened[f"{name}.{k}"] = v
    out["uniform_improvement_or_matching"] = (len(worsened) == 0)
    out["representations_worsened_by_gt10pct"] = worsened
    out["total_duration_seconds"] = round(time.time() - t0, 2)

    out_dir = Path("results/evaluation/v17b_label_normalization_all_reps")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "v17b_label_normalization_all_reps_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    with open(out_dir / "v17b_label_normalization_all_reps_latest.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    print(json.dumps(out, indent=2)[:4000])
    logger.info(f"Saved. uniform={out['uniform_improvement_or_matching']}")
    return out


if __name__ == "__main__":
    main()
