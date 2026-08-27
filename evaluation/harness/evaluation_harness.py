"""
LexMachina Evaluation Harness
Builds falsification-capable benchmarks for legal map representations.
Uses TF/Jurivoc-style human indexing (legal_area, branch, chamber, language) as imperfect ground truth.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

# Paths to accepted data
ACCEPTED_BASE = Path("/tmp/lex_accepted/product/product")
CORPUS_DIR = ACCEPTED_BASE / "results/corpus/normalization/canonical"
FRACTAL_DIR = ACCEPTED_BASE / "results/fractal_map"
EVAL_DIR = FRACTAL_DIR / "evaluation"


@dataclass
class Decision:
    decision_id: str
    language: str
    legal_area: str
    branch: str
    chamber: str
    year: str
    full_text: str = ""


@dataclass
class RepresentationData:
    name: str
    embeddings: np.ndarray  # (n_decisions, dim)
    decision_ids: List[str]
    metadata: Dict


def load_corpus(sample_file: str = "bger_eval_balanced.jsonl") -> List[Decision]:
    """Load decisions from canonical corpus file."""
    decisions = []
    with open(CORPUS_DIR / sample_file, 'r') as f:
        for line in f:
            d = json.loads(line)
            decisions.append(Decision(
                decision_id=d["decision_id"],
                language=d["language"],
                legal_area=d["legal_area"],
                branch=d["branch"],
                chamber=d["chamber"],
                year=d.get("decision_date", "").split("-")[0] if d.get("decision_date") else "unknown",
                full_text=d.get("full_text", "")
            ))
    return decisions


def load_embeddings(repr_name: str) -> RepresentationData:
    """Load embeddings for a given representation."""
    
    repr_paths = {
        "baseline": FRACTAL_DIR / "baseline/embeddings.npy",
        "center_projected": FRACTAL_DIR / "language_debiasing/embeddings_center_projected.npy",
        "concat_center_tfidf": None,  # Not directly available as single file
        "hierarchical_leiden": None,  # This is cluster assignments, not embeddings
    }
    
    # For section modes
    section_modes = [
        "sachverhalt", "erwaegungen", "dispositiv", "full_text",
        "erwaegungen_dispositiv", "sachverhalt_erwaegungen_dispositiv"
    ]
    
    if repr_name in section_modes:
        path = FRACTAL_DIR / f"section_experiment_clean/projection_{repr_name}.npy"
        if path.exists():
            emb = np.load(path)
            # Load metadata to get decision_ids
            meta_path = FRACTAL_DIR / "section_experiment_clean/metadata.json"
            with open(meta_path) as f:
                meta = json.load(f)
            decision_ids = [m["decision_id"] for m in meta]
            return RepresentationData(repr_name, emb, decision_ids, {"source": "section_experiment"})
    
    if repr_name.startswith("scaled_section_"):
        section = repr_name.replace("scaled_section_", "")
        path = FRACTAL_DIR / f"section_scaled/projection_{section}.npy"
        if path.exists():
            emb = np.load(path)
            meta_path = FRACTAL_DIR / "section_scaled/metadata.json"
            with open(meta_path) as f:
                meta = json.load(f)
            # metadata.json is a dict with section_modes, need to get decision_ids from the decisions list
            slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
            with open(slice_path) as f:
                decision_ids = [json.loads(line)["decision_id"] for line in f]
            return RepresentationData(repr_name, emb, decision_ids, {"source": "section_scaled"})
    
    if repr_name in repr_paths and repr_paths[repr_name] and repr_paths[repr_name].exists():
        emb = np.load(repr_paths[repr_name])
        # For baseline/center_projected, we need to match with the 1000 decision slice
        slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
        with open(slice_path) as f:
            decision_ids = [json.loads(line)["decision_id"] for line in f]
        return RepresentationData(repr_name, emb, decision_ids, {"source": "baseline"})
    
    if repr_name == "hierarchical_leiden":
        # Load hierarchical Leiden cluster assignments
        path = FRACTAL_DIR / "hierarchical_map/hierarchical_leiden_results.json"
        with open(path) as f:
            data = json.load(f)
        # Return cluster assignments as "embeddings" (one-hot encoded)
        best_config = data["hierarchical_results"]["coarse_0.5_fine_3.0"]
        # We need the actual cluster labels for each decision
        labels_path = FRACTAL_DIR / "hierarchical_map/labels_res_3.0.npy"
        if labels_path.exists():
            labels = np.load(labels_path)
            slice_path = CORPUS_DIR / "bger_2000plus_slice_1000.jsonl"
            with open(slice_path) as f:
                decision_ids = [json.loads(line)["decision_id"] for line in f]
            # One-hot encode cluster assignments
            n_clusters = len(np.unique(labels))
            emb = np.eye(n_clusters)[labels]
            return RepresentationData(repr_name, emb, decision_ids, {
                "source": "hierarchical_leiden",
                "config": best_config["config"],
                "cluster_labels": labels.tolist()
            })
    
    raise ValueError(f"Unknown or unavailable representation: {repr_name}")


def load_all_representations() -> Dict[str, RepresentationData]:
    """Load all available representations."""
    reps = {}
    
    # Baseline representations
    for name in ["baseline", "center_projected"]:
        try:
            reps[name] = load_embeddings(name)
        except Exception as e:
            print(f"Warning: Could not load {name}: {e}")
    
    # Section modes (original 63 decisions)
    section_modes = [
        "sachverhalt", "erwaegungen", "dispositiv", "full_text",
        "erwaegungen_dispositiv", "sachverhalt_erwaegungen_dispositiv"
    ]
    for mode in section_modes:
        try:
            reps[f"section_{mode}"] = load_embeddings(mode)
        except Exception as e:
            print(f"Warning: Could not load section {mode}: {e}")
    
    # Scaled section modes (1000 decisions)
    scaled_modes = [
        "scaled_section_sachverhalt", "scaled_section_erwaegungen",
        "scaled_section_dispositiv", "scaled_section_full_text",
        "scaled_section_erwaegungen_dispositiv", "scaled_section_sachverhalt_erwaegungen_dispositiv"
    ]
    for mode in scaled_modes:
        try:
            reps[mode] = load_embeddings(mode)
        except Exception as e:
            print(f"Warning: Could not load {mode}: {e}")
    
    # Hierarchical Leiden
    try:
        reps["hierarchical_leiden"] = load_embeddings("hierarchical_leiden")
    except Exception as e:
        print(f"Warning: Could not load hierarchical_leiden: {e}")
    
    return reps


def load_citation_graph() -> Dict[str, List[str]]:
    """Load citation graph."""
    path = FRACTAL_DIR / "citation_graph/citation_graph.json"
    with open(path) as f:
        return json.load(f)


def compute_purity(cluster_labels: np.ndarray, ground_truth: np.ndarray) -> float:
    """Compute cluster purity against ground truth labels."""
    from sklearn.metrics import normalized_mutual_info_score
    
    # Purity: for each cluster, find most common ground truth label
    n_clusters = len(np.unique(cluster_labels))
    n_samples = len(cluster_labels)
    
    purity_sum = 0
    for c in range(n_clusters):
        mask = cluster_labels == c
        if mask.sum() == 0:
            continue
        gt_in_cluster = ground_truth[mask]
        # Most common ground truth in this cluster
        most_common = np.bincount(gt_in_cluster).max()
        purity_sum += most_common
    
    return purity_sum / n_samples


def compute_nmi(labels1: np.ndarray, labels2: np.ndarray) -> float:
    """Normalized Mutual Information between two clusterings."""
    from sklearn.metrics import normalized_mutual_info_score
    return normalized_mutual_info_score(labels1, labels2)


def get_ground_truth_labels(decisions: List[Decision], field: str) -> Tuple[np.ndarray, Dict[str, int]]:
    """Convert a metadata field to integer labels."""
    values = [getattr(d, field) for d in decisions]
    unique_vals = sorted(set(values))
    val_to_idx = {v: i for i, v in enumerate(unique_vals)}
    labels = np.array([val_to_idx[v] for v in values])
    return labels, val_to_idx


def compute_legal_area_purity(cluster_labels: np.ndarray, decisions: List[Decision]) -> float:
    """Compute purity against legal_area ground truth."""
    gt_labels, _ = get_ground_truth_labels(decisions, "legal_area")
    return compute_purity(cluster_labels, gt_labels)


def compute_branch_purity(cluster_labels: np.ndarray, decisions: List[Decision]) -> float:
    """Compute purity against branch ground truth."""
    gt_labels, _ = get_ground_truth_labels(decisions, "branch")
    return compute_purity(cluster_labels, gt_labels)


def compute_language_purity(cluster_labels: np.ndarray, decisions: List[Decision]) -> float:
    """Compute purity against language ground truth."""
    gt_labels, _ = get_ground_truth_labels(decisions, "language")
    return compute_purity(cluster_labels, gt_labels)


def compute_chamber_purity(cluster_labels: np.ndarray, decisions: List[Decision]) -> float:
    """Compute purity against chamber ground truth."""
    gt_labels, _ = get_ground_truth_labels(decisions, "chamber")
    return compute_purity(cluster_labels, gt_labels)


def compute_ratio(legal_purity: float, language_purity: float) -> float:
    """Compute legal/language ratio (higher = more legal signal, less language signal)."""
    if language_purity == 0:
        return 0.0
    return legal_purity / language_purity


def cluster_from_embeddings(embeddings: np.ndarray, resolution: float = 1.0) -> np.ndarray:
    """Cluster embeddings using Leiden algorithm."""
    try:
        import igraph as ig
        import leidenalg as la
    except ImportError:
        # Fallback to KMeans
        from sklearn.cluster import KMeans
        n_clusters = max(2, int(len(embeddings) * resolution / 100))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        return kmeans.fit_predict(embeddings)
    
    # Build kNN graph
    from sklearn.neighbors import NearestNeighbors
    n_neighbors = min(15, len(embeddings) - 1)
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric='cosine')
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    # Build igraph
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j, dist in zip(indices[i][1:], distances[i][1:]):  # Skip self
            edges.append((i, j))
            weights.append(1.0 - dist)  # Convert distance to similarity
    
    g = ig.Graph(edges=edges, directed=False)
    g.es['weight'] = weights
    
    # Run Leiden
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=resolution, seed=42)
    return np.array(partition.membership)


def evaluate_representation_clustering(rep: RepresentationData, decisions: List[Decision],
                                        resolutions: List[float] = None) -> Dict:
    """Evaluate a representation across multiple clustering resolutions."""
    if resolutions is None:
        resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    # Align decisions with representation
    decision_id_to_idx = {d.decision_id: i for i, d in enumerate(decisions)}
    aligned_indices = [decision_id_to_idx[did] for did in rep.decision_ids if did in decision_id_to_idx]
    aligned_decisions = [decisions[i] for i in aligned_indices]
    aligned_embeddings = rep.embeddings[[rep.decision_ids.index(did) for did in rep.decision_ids if did in decision_id_to_idx]]
    
    results = {"representation": rep.name, "resolutions": {}}
    
    for res in resolutions:
        labels = cluster_from_embeddings(aligned_embeddings, resolution=res)
        
        legal_purity = compute_legal_area_purity(labels, aligned_decisions)
        branch_purity = compute_branch_purity(labels, aligned_decisions)
        language_purity = compute_language_purity(labels, aligned_decisions)
        chamber_purity = compute_chamber_purity(labels, aligned_decisions)
        ratio = compute_ratio(legal_purity, language_purity)
        
        n_clusters = len(np.unique(labels))
        # Modularity (approximate using silhouette)
        from sklearn.metrics import silhouette_score
        try:
            sil = silhouette_score(aligned_embeddings, labels, metric='cosine')
        except:
            sil = 0.0
        
        results["resolutions"][f"resolution_{res}"] = {
            "n_clusters": int(n_clusters),
            "modularity": float(sil),
            "legal_area_purity": float(legal_purity),
            "language_purity": float(language_purity),
            "branch_purity": float(branch_purity),
            "chamber_purity": float(chamber_purity),
            "ratio": float(ratio)
        }
    
    return results


if __name__ == "__main__":
    # Quick test
    decisions = load_corpus("bger_eval_balanced.jsonl")
    print(f"Loaded {len(decisions)} decisions")
    
    reps = load_all_representations()
    print(f"Loaded {len(reps)} representations:")
    for name, rep in reps.items():
        print(f"  {name}: {rep.embeddings.shape} embeddings for {len(rep.decision_ids)} decisions")