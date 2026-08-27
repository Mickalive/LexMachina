"""
Evaluation Cycle 7: Fixed Citation Graph + Zoom Coherence

Runs evaluation with:
1. Fixed citation_graph_neighborhood benchmark (>=2 shared citations, not direct links)
2. New zoom_coherence benchmark (formalized from fractal-map results)
3. Existing citation_proximity, legal_area_clustering benchmarks

This cycle validates that the citation graph benchmark now works with the actual
data (300 decisions, 2,103 unique cited references) and adds zoom coherence as
a formal benchmark.

Frozen before observation:
- Sample: All fractal-map embeddings (10 representations)
- Benchmarks: citation_graph_neighborhood (fixed), citation_proximity, legal_area_clustering, zoom_coherence
- Targets: citation_graph AUC > 0.7, citation_proximity AUC > 0.75, legal_area NMI > 0.3, legal_area purity > 0.7, zoom_coherence improvement_rate > 0.5
"""

import json
import numpy as np
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict
import random
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# --- Paths ---
FRACTAL_MAP_RESULTS = "/tmp/lex_accepted/fractal-map/results/fractal_map"
CORPUS_DATA = "/tmp/lex_accepted/corpus/corpus/normalization/canonical"
CITATION_GRAPH_PATH = "/tmp/lex_accepted/corpus/corpus/normalization/canonical/citation_graph.json"
WORKSPACE_RESULTS = Path(__file__).parent.parent / "results"
WORKSPACE_REPORTS = Path(__file__).parent.parent / "reports"

# --- Representation configs ---
REPRESENTATIONS = {
    "baseline": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/baseline/embeddings.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/baseline/metadata.json",
        "description": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)",
    },
    "section_sachverhalt": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_sachverhalt.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on Sachverhalt (facts) section only",
    },
    "section_erwaegungen": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_erwaegungen.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on Erwaegungen (reasoning) section only",
    },
    "section_dispositiv": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_dispositiv.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on Dispositiv (disposition) section only",
    },
    "section_full_text": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_full_text.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on full text",
    },
    "section_combined": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_sachverhalt_erwaegungen_dispositiv.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on Sachverhalt + Erwaegungen + Dispositiv",
    },
    "section_erwaegungen_dispositiv": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/embeddings_erwaegungen_dispositiv.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/section_experiment_clean/metadata.json",
        "description": "TF-IDF on Erwaegungen + Dispositiv",
    },
    "language_debiased_pca2": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/language_debiasing/embeddings_pca2.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/baseline/metadata.json",
        "description": "Baseline with language debiasing (PCA 2 components removed)",
    },
    "citation_blended": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/citation_graph/embeddings_blended.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/baseline/metadata.json",
        "description": "Blended citation + semantic embeddings",
    },
    "citation_graph_only": {
        "embeddings": f"{FRACTAL_MAP_RESULTS}/citation_graph/embeddings_graph_only.npy",
        "metadata": f"{FRACTAL_MAP_RESULTS}/baseline/metadata.json",
        "description": "Citation graph embeddings only",
    },
}

TARGETS = {
    "citation_graph_auc": 0.7,
    "citation_proximity_auc": 0.75,
    "legal_area_nmi": 0.3,
    "legal_area_purity": 0.7,
    "zoom_coherence_improvement_rate": 0.5,
}


# --- Utility functions ---

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class EmbeddingIndex:
    """Wraps pre-computed embeddings as a callable + lookup."""

    def __init__(self, embeddings_path: str, metadata_path: str):
        self.embeddings = np.load(embeddings_path).astype(np.float32)
        with open(metadata_path) as f:
            self.metadata = json.load(f)
        self.id_to_idx = {}
        for i, entry in enumerate(self.metadata):
            did = entry.get("decision_id", "")
            if did:
                self.id_to_idx[did] = i
        # Normalize for cosine
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.normed = self.embeddings / norms
        logger.info(f"  Loaded {len(self.embeddings)} embeddings, dim={self.embeddings.shape[1]}, "
                     f"{len(self.id_to_idx)} indexed")

    def __call__(self, decision_id: str) -> Optional[np.ndarray]:
        idx = self.id_to_idx.get(decision_id)
        if idx is None:
            return None
        return self.embeddings[idx]

    def get_all_ids(self) -> List[str]:
        return [did for did, _ in sorted(self.id_to_idx.items(), key=lambda x: x[1])]


# --- Corpus loading ---

def load_corpus_decisions() -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, str]]:
    """Load corpus and return (decisions, docket_to_id, id_to_branch)."""
    decisions = []
    for fname in ["bger_eval_balanced.jsonl", "bger_eval_structure.jsonl", "bger_eval_sample.jsonl"]:
        fpath = os.path.join(CORPUS_DATA, fname)
        if os.path.exists(fpath):
            with open(fpath) as f:
                for line in f:
                    if line.strip():
                        decisions.append(json.loads(line))
    for yr in range(2020, 2025):
        fpath = os.path.join(CORPUS_DATA, f"bger_{yr}.jsonl")
        if os.path.exists(fpath):
            with open(fpath) as f:
                for line in f:
                    if line.strip():
                        decisions.append(json.loads(line))
    seen = set()
    unique = []
    docket_to_id = {}
    id_to_branch = {}
    for d in decisions:
        did = d.get("decision_id", "")
        if did and did not in seen:
            seen.add(did)
            unique.append(d)
            dk = d.get("docket_number", "")
            if dk:
                docket_to_id[dk] = did
            branch = d.get("branch", "")
            if branch:
                id_to_branch[did] = branch
    logger.info(f"Loaded {len(unique)} unique corpus decisions, {len(docket_to_id)} docket mappings, {len(id_to_branch)} branch labels")
    return unique, docket_to_id, id_to_branch


def load_citation_graph() -> Dict:
    with open(CITATION_GRAPH_PATH) as f:
        return json.load(f)


# --- Benchmarks ---

def bench_citation_graph(idx: EmbeddingIndex, corpus: List[Dict]) -> Dict:
    """Citation graph neighborhood: are decisions sharing >=2 citations closer?"""
    t0 = time.time()
    min_shared = 2

    # Build citation index
    citation_index = {}
    for d in corpus:
        did = d.get("decision_id", "")
        cites = d.get("cited_decisions", [])
        if did and cites:
            citation_index[did] = set(cites)

    # Find shared citation pairs
    ref_to_decisions = defaultdict(set)
    for did, refs in citation_index.items():
        for ref in refs:
            ref_to_decisions[ref].add(did)

    pair_shared = defaultdict(int)
    for ref, dids in ref_to_decisions.items():
        dids_list = list(dids)
        for i in range(len(dids_list)):
            for j in range(i + 1, len(dids_list)):
                pair_key = tuple(sorted([dids_list[i], dids_list[j]]))
                pair_shared[pair_key] += 1

    pos_pairs = [(p[0], p[1], c) for p, c in pair_shared.items() if c >= min_shared]

    # Negative pairs
    rng = random.Random(42)
    pos_set = set((p[0], p[1]) for p in pos_pairs)
    all_ids = list(citation_index.keys())
    neg_pairs = []
    max_att = len(pos_pairs) * 20
    att = 0
    while len(neg_pairs) < len(pos_pairs) and att < max_att:
        d1, d2 = rng.sample(all_ids, 2)
        p = tuple(sorted([d1, d2]))
        if p not in pos_set:
            neg_pairs.append(p)
        att += 1

    if len(pos_pairs) > 500:
        rng.shuffle(pos_pairs)
        pos_pairs = pos_pairs[:500]
    if len(neg_pairs) > 500:
        neg_pairs = neg_pairs[:500]

    # Compute similarities
    pos_sims = []
    for d1, d2, _ in pos_pairs:
        if d1 in idx.id_to_idx and d2 in idx.id_to_idx:
            pos_sims.append(cosine_similarity(idx(d1), idx(d2)))
    neg_sims = []
    for d1, d2 in neg_pairs:
        if d1 in idx.id_to_idx and d2 in idx.id_to_idx:
            neg_sims.append(cosine_similarity(idx(d1), idx(d2)))

    metrics = {}
    if pos_sims and neg_sims:
        from sklearn.metrics import roc_auc_score
        y_true = [1] * len(pos_sims) + [0] * len(neg_sims)
        y_scores = pos_sims + neg_sims
        metrics["auc_roc"] = float(roc_auc_score(y_true, y_scores))
        metrics["positive_mean_sim"] = float(np.mean(pos_sims))
        metrics["negative_mean_sim"] = float(np.mean(neg_sims))
        metrics["mean_gap"] = float(np.mean(pos_sims) - np.mean(neg_sims))
    else:
        metrics["auc_roc"] = 0.5

    metrics["num_positive"] = len(pos_sims)
    metrics["num_negative"] = len(neg_sims)
    metrics["num_embedded"] = len(set(d for p in pos_pairs + neg_pairs for d in p if d in idx.id_to_idx))
    metrics["min_shared_citations"] = min_shared

    return {
        "benchmark": "citation_graph_neighborhood",
        "status": "PASSED" if metrics["auc_roc"] > 0.7 else "FAILED",
        "metrics": metrics,
        "duration": time.time() - t0,
    }


def bench_citation_proximity(idx: EmbeddingIndex, corpus: List[Dict]) -> Dict:
    """Citation proximity: are shared-citation decisions closer?"""
    t0 = time.time()

    # Build citation index
    citation_index = {}
    for d in corpus:
        did = d.get("decision_id", "")
        cites = d.get("cited_decisions", [])
        if did and cites:
            citation_index[did] = set(cites)

    # Find pairs sharing >= 1 citation
    ref_to_decisions = defaultdict(set)
    for did, refs in citation_index.items():
        for ref in refs:
            ref_to_decisions[ref].add(did)

    pair_shared = defaultdict(int)
    for ref, dids in ref_to_decisions.items():
        dids_list = list(dids)
        for i in range(len(dids_list)):
            for j in range(i + 1, len(dids_list)):
                pair_key = tuple(sorted([dids_list[i], dids_list[j]]))
                pair_shared[pair_key] += 1

    pos_pairs = [(p[0], p[1], c) for p, c in pair_shared.items() if c >= 1]

    # Negative pairs
    rng = random.Random(42)
    pos_set = set((p[0], p[1]) for p in pos_pairs)
    all_ids = list(citation_index.keys())
    neg_pairs = []
    max_att = len(pos_pairs) * 20
    att = 0
    while len(neg_pairs) < len(pos_pairs) and att < max_att:
        d1, d2 = rng.sample(all_ids, 2)
        p = tuple(sorted([d1, d2]))
        if p not in pos_set:
            neg_pairs.append(p)
        att += 1

    if len(pos_pairs) > 300:
        rng.shuffle(pos_pairs)
        pos_pairs = pos_pairs[:300]
    if len(neg_pairs) > 300:
        neg_pairs = neg_pairs[:300]

    # Compute similarities
    pos_sims = []
    for d1, d2, _ in pos_pairs:
        if d1 in idx.id_to_idx and d2 in idx.id_to_idx:
            pos_sims.append(cosine_similarity(idx(d1), idx(d2)))
    neg_sims = []
    for d1, d2 in neg_pairs:
        if d1 in idx.id_to_idx and d2 in idx.id_to_idx:
            neg_sims.append(cosine_similarity(idx(d1), idx(d2)))

    metrics = {}
    if pos_sims and neg_sims:
        from sklearn.metrics import roc_auc_score
        y_true = [1] * len(pos_sims) + [0] * len(neg_sims)
        y_scores = pos_sims + neg_sims
        metrics["auc_roc"] = float(roc_auc_score(y_true, y_scores))
        metrics["positive_mean_sim"] = float(np.mean(pos_sims))
        metrics["negative_mean_sim"] = float(np.mean(neg_sims))
    else:
        metrics["auc_roc"] = 0.5

    metrics["num_positive"] = len(pos_sims)
    metrics["num_negative"] = len(neg_sims)

    return {
        "benchmark": "citation_proximity",
        "status": "PASSED" if metrics["auc_roc"] > 0.75 else "FAILED",
        "metrics": metrics,
        "duration": time.time() - t0,
    }


def bench_legal_area(idx: EmbeddingIndex, corpus: List[Dict], id_to_branch: Dict[str, str]) -> Dict:
    """Legal area clustering: does embedding space recover branch structure?"""
    t0 = time.time()

    # Use corpus branch labels matched by decision_id
    embedded_branches = {did: branch for did, branch in id_to_branch.items() if did in idx.id_to_idx}

    # Need at least 2 branches with enough samples
    branch_counts = defaultdict(int)
    for b in embedded_branches.values():
        branch_counts[b] += 1
    valid_branches = {b for b, c in branch_counts.items() if c >= 10}
    if len(valid_branches) < 2:
        return {"benchmark": "legal_area_clustering", "status": "ERROR",
                "metrics": {}, "error": f"Insufficient branches: {len(valid_branches)}"}

    # Sample balanced across branches
    rng = random.Random(42)
    sample_ids = []
    for branch in valid_branches:
        branch_ids = [did for did, b in embedded_branches.items() if b == branch]
        n = min(150, len(branch_ids))
        sample_ids.extend(rng.sample(branch_ids, n))

    if len(sample_ids) < 20:
        return {"benchmark": "legal_area_clustering", "status": "ERROR",
                "metrics": {}, "error": "Insufficient samples"}

    # Get embeddings
    emb_matrix = np.stack([idx(did) for did in sample_ids])
    labels = np.array([embedded_branches[did] for did in sample_ids])
    unique_labels = list(set(labels))
    label_to_int = {l: i for i, l in enumerate(unique_labels)}
    int_labels = np.array([label_to_int[l] for l in labels])

    # Try multiple k values
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import normalized_mutual_info_score

    best_nmi = -1
    best_purity = -1
    for n_clusters in [len(unique_labels), len(unique_labels) + 2, len(unique_labels) + 4]:
        try:
            clustering = AgglomerativeClustering(n_clusters=n_clusters)
            cluster_labels = clustering.fit_predict(emb_matrix)

            # Compute NMI
            nmi = normalized_mutual_info_score(int_labels, cluster_labels)

            # Compute purity
            purity = 0.0
            for c in set(cluster_labels):
                mask = cluster_labels == c
                if mask.sum() == 0:
                    continue
                vals = list(int_labels[mask])
                most_common = max(set(vals), key=vals.count)
                purity += vals.count(most_common)
            purity /= len(cluster_labels)

            if nmi > best_nmi:
                best_nmi = nmi
                best_purity = purity
        except Exception:
            continue

    metrics = {
        "nmi": float(best_nmi) if best_nmi >= 0 else 0.0,
        "purity": float(best_purity) if best_purity >= 0 else 0.0,
        "num_clusters": len(unique_labels),
        "num_samples": len(sample_ids),
        "branch_distribution": {b: sum(1 for l in labels if l == b) for b in unique_labels},
    }

    passed = metrics["nmi"] > 0.3 and metrics["purity"] > 0.7
    return {
        "benchmark": "legal_area_clustering",
        "status": "PASSED" if passed else "FAILED",
        "metrics": metrics,
        "duration": time.time() - t0,
    }


def bench_zoom_coherence() -> Dict:
    """Zoom coherence: does zooming reveal legally coherent substructure?"""
    t0 = time.time()

    # Load pre-computed zoom coherence results
    zoom_path = "/tmp/lex_accepted/fractal-map/results/fractal_map/evaluation/zoom_coherence_results.json"
    if not os.path.exists(zoom_path):
        return {
            "benchmark": "zoom_coherence",
            "status": "ERROR",
            "metrics": {},
            "error": "Zoom coherence results not found",
            "duration": time.time() - t0,
        }

    with open(zoom_path) as f:
        zoom_results = json.load(f)

    # Analyze zoom coherence
    zoom_data = zoom_results.get("zoom_results", {})
    flat_baseline = zoom_results.get("flat_baseline", {})

    improvements = 0
    deteriorations = 0
    total_clusters = 0
    improvement_rates = []

    min_lang_purity = 0.7
    min_cluster_size = 10
    improvement_threshold = 0.05

    for coarse_res, clusters in zoom_data.items():
        for cluster_id, cluster_data in clusters.items():
            lang_purity = cluster_data.get("lang_purity", 0.0)
            if lang_purity < min_lang_purity:
                continue
            cluster_size = cluster_data.get("size", 0)
            if cluster_size < min_cluster_size:
                continue

            total_clusters += 1
            coarse_ratio = cluster_data.get("ratio", 0.0)

            fine_results = cluster_data.get("fine_results", {})
            best_cluster_improvement = 0.0

            for fine_res, fine_data in fine_results.items():
                fine_ratio = fine_data.get("ratio", 0.0)
                improvement = fine_ratio - coarse_ratio
                improvement_rate = improvement / max(coarse_ratio, 0.001)
                best_cluster_improvement = max(best_cluster_improvement, improvement_rate)

            if best_cluster_improvement > improvement_threshold:
                improvements += 1
            elif best_cluster_improvement < -improvement_threshold:
                deteriorations += 1

            improvement_rates.append(best_cluster_improvement)

    improvement_rate = improvements / max(total_clusters, 1)

    # Flat baseline
    flat_best_ratio = 0.0
    for res, data in flat_baseline.items():
        ratio = data.get("ratio", 0.0)
        flat_best_ratio = max(flat_best_ratio, ratio)

    # Find best zoom result
    best_fine_ratio = 0.0
    best_coarse_to_fine_pct = 0.0
    for coarse_res, clusters in zoom_data.items():
        for cluster_id, cluster_data in clusters.items():
            coarse_ratio = cluster_data.get("ratio", 0.0)
            for fine_res, fine_data in cluster_data.get("fine_results", {}).items():
                fine_ratio = fine_data.get("ratio", 0.0)
                if fine_ratio > best_fine_ratio:
                    best_fine_ratio = fine_ratio
                if coarse_ratio > 0:
                    pct = (fine_ratio - coarse_ratio) / coarse_ratio * 100
                    best_coarse_to_fine_pct = max(best_coarse_to_fine_pct, pct)

    metrics = {
        "overall_improvement_rate": improvement_rate,
        "total_improvements": improvements,
        "total_deteriorations": deteriorations,
        "total_clusters_evaluated": total_clusters,
        "best_coarse_to_fine_improvement_pct": best_coarse_to_fine_pct,
        "best_fine_ratio": best_fine_ratio,
        "flat_baseline_best_ratio": flat_best_ratio,
        "mean_improvement_rate": float(np.mean(improvement_rates)) if improvement_rates else 0.0,
    }

    return {
        "benchmark": "zoom_coherence",
        "status": "PASSED" if improvement_rate > 0.5 else "FAILED",
        "metrics": metrics,
        "duration": time.time() - t0,
    }


# --- Main evaluation ---

def evaluate_representation(name: str, config: Dict, corpus: List[Dict], id_to_branch: Dict[str, str]) -> Dict:
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"  {config['description']}")
    logger.info(f"{'='*60}")

    if not os.path.exists(config["embeddings"]):
        return {"name": name, "error": f"Embeddings not found: {config['embeddings']}"}
    if not os.path.exists(config["metadata"]):
        return {"name": name, "error": f"Metadata not found: {config['metadata']}"}

    try:
        idx = EmbeddingIndex(config["embeddings"], config["metadata"])
    except Exception as e:
        return {"name": name, "error": f"Failed to load: {e}"}

    t0 = time.time()
    benchmarks = {}

    # Run each benchmark
    for bname, bfn in [
        ("citation_graph_neighborhood", lambda: bench_citation_graph(idx, corpus)),
        ("legal_area_clustering", lambda: bench_legal_area(idx, corpus, id_to_branch)),
        ("citation_proximity", lambda: bench_citation_proximity(idx, corpus)),
    ]:
        try:
            logger.info(f"  Running {bname}...")
            result = bfn()
            benchmarks[bname] = result
            m = result.get("metrics", {})
            logger.info(f"  {bname}: {result['status']}")
            for k, v in m.items():
                if isinstance(v, float):
                    logger.info(f"    {k}: {v:.4f}")
        except Exception as e:
            logger.error(f"  {bname}: ERROR - {e}")
            benchmarks[bname] = {"benchmark": bname, "status": "ERROR", "error": str(e)}

    # Zoom coherence (same for all representations)
    try:
        logger.info(f"  Running zoom_coherence...")
        result = bench_zoom_coherence()
        benchmarks["zoom_coherence"] = result
        m = result.get("metrics", {})
        logger.info(f"  zoom_coherence: {result['status']}")
        for k, v in m.items():
            if isinstance(v, float):
                logger.info(f"    {k}: {v:.4f}")
    except Exception as e:
        logger.error(f"  zoom_coherence: ERROR - {e}")
        benchmarks["zoom_coherence"] = {"benchmark": "zoom_coherence", "status": "ERROR", "error": str(e)}

    total = time.time() - t0

    # Evaluate targets
    target_results = {}
    target_mapping = {
        "citation_graph_auc": ("citation_graph_neighborhood", "auc_roc"),
        "citation_proximity_auc": ("citation_proximity", "auc_roc"),
        "legal_area_nmi": ("legal_area_clustering", "nmi"),
        "legal_area_purity": ("legal_area_clustering", "purity"),
        "zoom_coherence_improvement_rate": ("zoom_coherence", "overall_improvement_rate"),
    }
    for tname, threshold in TARGETS.items():
        bench_name, metric_name = target_mapping.get(tname, (None, None))
        if bench_name and metric_name:
            bres = benchmarks.get(bench_name, {})
            m = bres.get("metrics", {})
            achieved = m.get(metric_name)
            if achieved is not None:
                target_results[tname] = {
                    "achieved": achieved,
                    "target": threshold,
                    "pass": achieved > threshold,
                }

    return {
        "name": name,
        "description": config["description"],
        "num_embeddings": len(idx.id_to_idx),
        "embedding_dim": int(idx.embeddings.shape[1]),
        "benchmarks": benchmarks,
        "targets": target_results,
        "total_duration": total,
    }


def generate_report(all_results: List[Dict]) -> str:
    lines = []
    lines.append("# Evaluation Cycle 7: Fixed Citation Graph + Zoom Coherence")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("Fixing the citation graph benchmark to use shared citation heritage (>=2 shared")
    lines.append("references) instead of direct citation links will produce valid AUC scores. Adding")
    lines.append("zoom coherence as a formal benchmark will validate the fractal architecture hypothesis.")
    lines.append("")
    lines.append("## Frozen Before Observation")
    lines.append("- Sample: All fractal-map embeddings (10 representations)")
    lines.append("- Benchmarks: citation_graph_neighborhood (fixed), citation_proximity, legal_area_clustering, zoom_coherence")
    lines.append("- Targets: citation_graph AUC > 0.7, citation_proximity AUC > 0.75, legal_area NMI > 0.3, legal_area purity > 0.7, zoom_coherence improvement_rate > 0.5")
    lines.append("")

    # Summary table
    lines.append("## Results Summary")
    lines.append("")
    lines.append("| Representation | Dim | CG AUC | CP AUC | LA NMI | LA Purity | Zoom Rate | Targets |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in all_results:
        if "error" in r:
            lines.append(f"| {r['name']} | - | ERROR | - | - | - | - | {r['error'][:30]} |")
            continue
        bm = r.get("benchmarks", {})
        def g(b, k):
            v = bm.get(b, {}).get("metrics", {}).get(k)
            return f"{v:.4f}" if isinstance(v, float) else "N/A"
        targets = r.get("targets", {})
        pc = sum(1 for t in targets.values() if t.get("pass"))
        tc = len(targets)
        lines.append(f"| {r['name']} | {r.get('embedding_dim','?')} | {g('citation_graph_neighborhood','auc_roc')} | {g('citation_proximity','auc_roc')} | {g('legal_area_clustering','nmi')} | {g('legal_area_clustering','purity')} | {g('zoom_coherence','overall_improvement_rate')} | {pc}/{tc} |")

    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")
    for r in all_results:
        if "error" in r:
            lines.append(f"### {r['name']}\nERROR: {r['error']}\n")
            continue
        lines.append(f"### {r['name']}")
        lines.append(f"- Description: {r.get('description','N/A')}")
        lines.append(f"- Embeddings: {r.get('num_embeddings','N/A')} decisions, {r.get('embedding_dim','N/A')}d")
        lines.append(f"- Duration: {r.get('total_duration',0):.1f}s")
        for bname, bres in r.get("benchmarks", {}).items():
            status = bres.get("status", "N/A")
            metrics = bres.get("metrics", {})
            lines.append(f"- **{bname}**: {status}")
            for k, v in metrics.items():
                if isinstance(v, float):
                    lines.append(f"  - {k}: {v:.4f}")
                elif isinstance(v, dict) and len(v) < 10:
                    lines.append(f"  - {k}: {v}")
        targets = r.get("targets", {})
        if targets:
            lines.append("- **Targets:**")
            for tn, tv in targets.items():
                st = "PASS" if tv.get("pass") else "FAIL"
                lines.append(f"  - {tn}: {tv.get('achieved','?'):.4f} vs {tv.get('target','?')} -> {st}")
        lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")
    best = {}
    for r in all_results:
        if "error" in r:
            continue
        for bname, bres in r.get("benchmarks", {}).items():
            for mk, mv in bres.get("metrics", {}).items():
                if isinstance(mv, float):
                    key = f"{bname}_{mk}"
                    if key not in best or mv > best[key][1]:
                        best[key] = (r["name"], mv)
    for key, (name, value) in sorted(best.items()):
        lines.append(f"- Best {key}: **{name}** ({value:.4f})")

    lines.append("")
    lines.append("## Negative Results")
    lines.append("")
    for r in all_results:
        if "error" in r:
            lines.append(f"- {r['name']}: {r['error']}")
        else:
            failed = [t for t, v in r.get("targets", {}).items() if not v.get("pass")]
            if failed:
                lines.append(f"- {r['name']} failed: {', '.join(failed)}")

    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    passing = [r for r in all_results if r.get("targets") and all(t.get("pass") for t in r["targets"].values())]
    if passing:
        best_p = max(passing, key=lambda r: sum(t.get("achieved", 0) for t in r["targets"].values()))
        lines.append(f"RECOMMEND: Use **{best_p['name']}** as default. All targets pass.")
    else:
        lines.append("NO representation passes all targets.")
        lines.append("Legal-distance lane should focus on:")
        lines.append("1. Citation-aware representations (citation proximity AUC is hardest target)")
        lines.append("2. Hybrid methods combining semantic + citation + legal-area signals")
        for tname in TARGETS:
            best_for_target = None
            best_val = -1
            for r in all_results:
                if "error" in r:
                    continue
                tv = r.get("targets", {}).get(tname, {}).get("achieved")
                if tv is not None and tv > best_val:
                    best_val = tv
                    best_for_target = r["name"]
            if best_for_target:
                lines.append(f"   - Best for {tname}: {best_for_target} ({best_val:.4f})")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Evaluation Cycle 7: Fixed Citation Graph + Zoom Coherence")
    print("=" * 60)

    corpus, docket_to_id, id_to_branch = load_corpus_decisions()

    all_results = []
    for name, config in REPRESENTATIONS.items():
        result = evaluate_representation(name, config, corpus, id_to_branch)
        all_results.append(result)

    # Save results
    WORKSPACE_RESULTS.mkdir(parents=True, exist_ok=True)
    results_file = WORKSPACE_RESULTS / "cycle_7_fixed_benchmarks_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "run_id": f"eval_cycle_7_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "representations_evaluated": len(all_results),
            "results": all_results,
            "targets": TARGETS,
            "changes_from_cycle_6": [
                "Fixed citation_graph_neighborhood: now uses >=2 shared citations instead of direct links",
                "Added zoom_coherence benchmark from fractal-map results",
                "All 10 representations now evaluated against 5 targets (was 4)",
            ],
        }, f, indent=2, default=str)
    print(f"\nResults saved to: {results_file}")

    # Generate report
    WORKSPACE_REPORTS.mkdir(parents=True, exist_ok=True)
    report = generate_report(all_results)
    report_file = WORKSPACE_REPORTS / "evaluation_cycle_7_report.md"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"Report saved to: {report_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for r in all_results:
        if "error" in r:
            print(f"  {r['name']}: ERROR - {r['error']}")
        else:
            targets = r.get("targets", {})
            pc = sum(1 for t in targets.values() if t.get("pass"))
            tc = len(targets)
            print(f"  {r['name']}: {pc}/{tc} targets pass")

    any_pass = any(
        r.get("targets") and all(t.get("pass") for t in r["targets"].values())
        for r in all_results
    )
    return 0 if any_pass else 1


if __name__ == "__main__":
    sys.exit(main())
