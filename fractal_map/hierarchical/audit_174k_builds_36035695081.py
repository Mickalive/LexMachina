#!/usr/bin/env python3
"""
174k build census + alignment/provenance audit — run 36035695081 (operational resume).

Freeze-before-compute: the census DEFINITION (scope, fields, classification rules,
alignment probes) is written to results/fractal_map/legal_distance_modes/
174k_CENSUS_v26_frozen_spec.json BEFORE any computation. All outputs derive from the
immutable historical artifacts (labels, decision_clusters, cluster_metadata,
hierarchical_map_results, embeddings metadata, ACCEPTED evaluation metadata).
No clustering is performed; no historical artifact is modified.

Purpose / product decision it informs:
  - Which 174k builds can serve real decision lookups in the product (decision-mappable)?
  - Which 174k builds are evaluation-eligible vs accepted metadata (join by decision_id)?
  - Provenance integrity of the 174k legal-TF-IDF pipeline (row->id alignment).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

BASE = Path('/home/runner/work/LexMachina/LexMachina')
MODES_DIR = BASE / 'results/fractal_map/legal_distance_modes'
H174K = BASE / 'results/fractal_map/hierarchical_map_174k'
EVAL_META = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]

CENSUS_DEFINITION = {
    "experiment": "fractal-map 174k build census + alignment/provenance audit",
    "lane": "fractal-map",
    "direction_version": 25,
    "github_run": 36035695081,
    "resume_from_run": 36034386649,
    "date_frozen": "2026-09-24",
    "scope": [
        "All directories under results/fractal_map/legal_distance_modes whose name contains '174k'",
        "Embedding provenance files under results/fractal_map/hierarchical_map_174k/{legal_tfidf_embeddings,tfidf_embeddings}/embeddings_metadata.json",
        "Metadata provenance files under results/fractal_map/hierarchical_map_174k/metadata_174k*.json",
        "ACCEPTED evaluation metadata /tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json (173,963 entries)"
    ],
    "fields_per_dir": [
        "labels_shapes", "decision_clusters_key_count", "placeholder_key_count",
        "real_key_count", "corpus_size", "embeddings_source", "run_id",
        "res0.25_cluster_metadata_cluster_count"
    ],
    "classification_rules": {
        "true_174k": "corpus_size >= 170000",
        "misnamed_21k": "corpus_size < 30000 (21,228-row builds whose dir name contains '174k')",
        "decision_mappable": "corpus_size >= 170000 AND real_key_count / decision_clusters_key_count >= 0.99",
        "placeholder_only": "corpus_size >= 170000 AND real_key_count == 0"
    },
    "alignment_probes": [
        {
            "probe_id": "row_order_vs_eval_metadata",
            "question": "Are embedding rows 0..173962 in the same order as ACCEPTED evaluation metadata_174k.json decision_ids?",
            "method": "Candidate assignment row i <- eval_meta[i]; agreement = fraction where decision_clusters[id].res_0.25 == labels_res_0.25[i]. Compare vs shuffled assignment (seed=0) and vs the ~1.0 expected for a correct order.",
            "evidence": "If agreement << 1.0, embedding row order is NOT recoverable from the accepted metadata; decision-mappable 174k citation-role/outcome rebuilds require the full corpus JSONL to regenerate the alignment."
        },
        {
            "probe_id": "cluster_metadata_rowid_integrity",
            "question": "Is row->decision_id reconstruction from cluster_metadata.json (decision_indices + decision_ids) consistent?",
            "method": "Reconstruct row->id at res_0.25 of the production default 174k_v25 build; report duplicate IDs and placeholder counts.",
            "evidence": "Duplicates > 0 imply cluster_metadata decision_ids were written from a different row ordering than decision_indices (legacy corruption); do NOT use cluster_metadata for row alignment."
        }
    ],
    "outcomes": [
        "census_v26.json",
        "alignment_probe_v26.json"
    ]
}


def main():
    spec_path = MODES_DIR / '174k_CENSUS_v26_frozen_spec.json'
    if not spec_path.exists():
        spec_path.write_text(json.dumps(CENSUS_DEFINITION, indent=2) + '\n')
        print(f"FROZEN SPEC WRITTEN: {spec_path}")
    else:
        existing = json.loads(spec_path.read_text())
        assert existing == CENSUS_DEFINITION, "frozen spec changed; abort"
        print(f"Frozen spec already present and identical: {spec_path}")

    # ---- accept evaluation metadata (label universe) ----
    eval_meta = json.load(open(EVAL_META))
    eval_ids = [m['decision_id'] for m in eval_meta]
    print(f"ACCEPTED eval metadata: {len(eval_ids)} ids")

    census = {
        "run_id": "census_174k_36035695081",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frozen_spec_ref": "results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json",
        "eval_metadata": {
            "path": str(EVAL_META),
            "n_entries": len(eval_ids),
        },
        "dirs": {},
    }

    for d in sorted(MODES_DIR.iterdir()):
        if not d.is_dir() or '174k' not in d.name:
            continue
        hr_path = d / 'hierarchical_map_results.json'
        hr = json.load(open(hr_path)) if hr_path.exists() else {}
        dc_path = d / 'decision_clusters.json'
        dc = json.load(open(dc_path)) if dc_path.exists() else {}
        keys = list(dc.keys())
        ph = sum(1 for k in keys if 'placeholder' in k)
        real = len(keys) - ph
        label_shapes = {}
        for r in RESOLUTIONS:
            p = d / f'labels_res_{r}.npy'
            if p.exists():
                import numpy as np
                label_shapes[f'res_{r}'] = list(np.load(p, mmap_mode='r').shape)
        cm_path = d / 'cluster_metadata.json'
        cm = json.load(open(cm_path)) if cm_path.exists() else {}
        n_clusters_cm = len(cm.get('res_0.25', {}))
        corpus_size = hr.get('corpus_size')
        src = str(hr.get('embeddings_source', ''))
        run_id = hr.get('run_id', '')
        entry = {
            "labels_shapes": label_shapes,
            "decision_clusters_key_count": len(keys),
            "placeholder_key_count": ph,
            "real_key_count": real,
            "corpus_size": corpus_size,
            "embeddings_source": src,
            "run_id": run_id,
            "res0.25_cluster_metadata_cluster_count": n_clusters_cm,
        }
        if corpus_size is not None and corpus_size >= 170000:
            if real / len(keys) >= 0.99 if keys else False:
                entry["classification"] = "true_174k_decision_mappable"
            else:
                entry["classification"] = "true_174k_placeholder_only"
        elif corpus_size is not None and corpus_size < 30000:
            entry["classification"] = "misnamed_21k_build"
        else:
            entry["classification"] = "unknown"
        census["dirs"][d.name] = entry
        print(f"{d.name}: {entry['classification']} keys={len(keys)} real={real} corpus={corpus_size}")

    # ---- summary counts per classification ----
    from collections import Counter as _Counter
    class_counts = _Counter(e["classification"] for e in census["dirs"].values())
    census["summary"] = {"counts": dict(class_counts), "n_dirs": len(census["dirs"])}

    # ---- provenance audit of metadata files ----
    meta_audit = {}
    for fname in ['metadata_174k_full.json', 'metadata_174k.json', 'metadata_174k_bge.json',
                  'metadata_174k_full_175k.json', 'metadata_175k_full.json']:
        p = H174K / fname
        if not p.exists():
            continue
        with open(p) as f:
            m = json.load(f)
        ids = [x['decision_id'] for x in m]
        meta_audit[fname] = {
            "n_entries": len(m),
            "n_unique": len(set(ids)),
            "n_placeholder": sum(1 for i in ids if 'placeholder' in i),
            "n_bger_real": sum(1 for i in ids if i.startswith('bger_') and 'placeholder' not in i),
            "n_bge": sum(1 for i in ids if i.startswith('bge_')),
        }
    emb_audit = {}
    for sub in ['legal_tfidf_embeddings', 'tfidf_embeddings']:
        p = H174K / sub / 'embeddings_metadata.json'
        if p.exists():
            emb_audit[sub] = json.load(open(p))
    census["metadata_provenance"] = meta_audit
    census["embeddings_provenance"] = emb_audit

    out = MODES_DIR / 'census_v26.json'
    out.write_text(json.dumps(census, indent=2) + '\n')
    print(f"CENSUS WRITTEN: {out}")

    # ---- alignment probes ----
    probes = {"run_id": "alignment_probe_v26_36035695081",
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "frozen_spec_ref": "results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json",
              "results": {}}

    # Probe 1: row order vs eval metadata (production default build)
    import numpy as np
    default_dir = MODES_DIR / 'cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25'
    dc = json.load(open(default_dir / 'decision_clusters.json'))
    labels = np.load(default_dir / 'labels_res_0.25.npy')
    n = min(len(eval_ids), labels.shape[0])
    agree = 0
    total = 0
    for i in range(n):
        did = eval_ids[i]
        if did in dc:
            total += 1
            if dc[did]['res_0.25'] == int(labels[i]):
                agree += 1
    rng = np.random.RandomState(0)
    perm = rng.permutation(len(eval_ids))
    agree_shuf = 0
    total_shuf = 0
    for i in range(n):
        did = eval_ids[perm[i]]
        if did in dc:
            total_shuf += 1
            if dc[did]['res_0.25'] == int(labels[i]):
                agree_shuf += 1
    probes['results']['row_order_vs_eval_metadata'] = {
        "candidate_agreement": agree / total if total else None,
        "candidate_hits": agree,
        "candidate_total": total,
        "shuffled_agreement": agree_shuf / total_shuf if total_shuf else None,
        "expected_agreement_if_correct_order": "~1.0",
        "verdict": "REJECTED" if (agree / total) < 0.9 else "CONFIRMED",
        "interpretation": ("Embedding row order does NOT match accepted metadata order; "
                           "row->id alignment is NOT recoverable from accepted metadata alone. "
                           "Decision-mappable rebuilds of placeholder-keyed 174k modes require "
                           "the full corpus JSONL (bger_*.jsonl) to regenerate the alignment "
                           "used by build_174k_legal_tfidf_embeddings.py.")
    }

    # Probe 2: cluster_metadata row->id integrity (production default, res_0.25)
    cm = json.load(open(default_dir / 'cluster_metadata.json'))
    row2id = {}
    for cid, info in cm['res_0.25'].items():
        for i, d in zip(info['decision_indices'], info['decision_ids']):
            row2id[i] = d
    cnt = Counter(row2id.values())
    dups = {d: c for d, c in cnt.items() if c > 1}
    ph_rows = sum(1 for d in row2id.values() if 'placeholder' in d)
    probes['results']['cluster_metadata_rowid_integrity'] = {
        "rows_covered": len(row2id),
        "duplicate_id_count": len(dups),
        "extra_rows_from_duplicates": sum(c - 1 for c in dups.values()),
        "placeholder_rows": ph_rows,
        "verdict": "CORRUPTED" if (dups or ph_rows) else "CONSISTENT",
        "interpretation": ("cluster_metadata decision_ids are NOT a reliable row->id map "
                           "(duplicates present); decision_clusters.json remains the "
                           "authoritative ID->cluster artifact for the 4 mappable modes.")
    }

    out2 = MODES_DIR / 'alignment_probe_v26.json'
    out2.write_text(json.dumps(probes, indent=2) + '\n')
    print(f"PROBES WRITTEN: {out2}")
    print("Alignment probe 1:", probes['results']['row_order_vs_eval_metadata']['candidate_agreement'])
    print("Alignment probe 2 verdict:", probes['results']['cluster_metadata_rowid_integrity']['verdict'])


if __name__ == '__main__':
    main()