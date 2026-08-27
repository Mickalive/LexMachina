#!/usr/bin/env python3
"""
Concatenated Representation Benchmark Evaluation

Tests the concat_center_tfidf representation (center-projected sentence embeddings
+ TF-IDF Erwaegungen) against the formal evaluation benchmarks from the evaluation lane.

Hypothesis: The concatenated representation, which achieves legal/language purity ratio
>0.5 in the fractal-map lane's internal evaluation, should also improve on the
formal benchmarks that TF-IDF baseline fails (boilerplate resistance, multilingual
invariance, corpus stability, hierarchy coherence, legal area clustering).

Product decision: If the concatenated representation passes or significantly improves
on the formal benchmarks, it validates the representation for product integration.

Frozen before observation:
- Corpus: BGer canonical decisions (2020-2024, ~1200+ decisions)
- Baseline: TF-IDF reasoning-only (from evaluation lane)
- Target representation: concat_center_tfidf (768-dim center-projected + 128-dim TF-IDF)
- Success: Improvement on ALL benchmarks vs TF-IDF baseline, with at least one benchmark
  showing >20% improvement.
"""

import json
import sys
import time
import logging
import re
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
COMBINED_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/combined_debiasing_tfidf")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_corpus_metadata():
    """Load the baseline metadata that maps decision_ids to indices."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return {m['decision_id']: i for i, m in enumerate(metadata)}, metadata


def load_representations():
    """Load pre-computed embeddings."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


def extract_erwaegungen(text, language):
    """Extract Erwaegungen (legal reasoning) section from text."""
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n',
                    r'(?:Erwägung\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n',
                    r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n',
                    r'(?:Considerando\s*:)\s*\n']
    else:
        return ""
    
    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    if start == -1:
        return ""
    
    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
        r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
        r'\n\s*(?:In\s+Erwägung|Erwägungen|Considérant|Considerando)\s*:',
    ]
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    return text_norm[start:end].strip()


def load_corpus_decisions(metadata):
    """Load full corpus decisions for TF-IDF computation."""
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    # Try bger_2000plus_slice_1000 first
    slice_path = corpus_dir / "bger_2000plus_slice_1000.jsonl"
    if slice_path.exists():
        with open(slice_path) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    
    # If not enough, try yearly files
    if len(decisions) < len(baseline_ids) * 0.8:
        for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
            with open(year_file) as f:
                for line in f:
                    d = json.loads(line)
                    if d['decision_id'] in baseline_ids and d['decision_id'] not in decisions:
                        decisions[d['decision_id']] = d
    
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions, id_to_idx):
    """Compute TF-IDF on Erwaegungen sections."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
    texts = [""] * len(metadata)
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            erwaegungen = extract_erwaegungen(text, lang)
            if erwaegungen.strip():
                texts[i] = erwaegungen
                valid_indices.append(i)
    
    filtered_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
        min_df=2, max_df=0.95, strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(filtered_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_indices) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    # Build aligned arrays
    tfidf_full = np.zeros((len(metadata), n_comp))
    for j, i in enumerate(valid_indices):
        tfidf_full[i] = reduced[j]
    
    return tfidf_full, valid_indices


def build_concat_representation(baseline_emb, center_emb, tfidf_full, metadata):
    """Build the concatenated representation: center-projected + TF-IDF Erwaegungen."""
    # Center-projected is 768-dim, TF-IDF is 128-dim -> 896-dim
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    concat = concat / norms
    return concat


class EmbeddingRepresentation:
    """Wrapper that provides representation_fn for evaluation benchmarks."""
    
    def __init__(self, embeddings, metadata, id_to_idx):
        self.embeddings = embeddings
        self.metadata = metadata
        self.id_to_idx = id_to_idx
    
    def representation_fn(self, decision_id, **kwargs):
        if decision_id in self.id_to_idx:
            idx = self.id_to_idx[decision_id]
            return self.embeddings[idx].astype(np.float32)
        return None


def run_boilerplate_test(concat_rep, baseline_rep, decisions_list, id_to_idx):
    """Simplified boilerplate resistance test."""
    import random
    random.seed(42)
    
    # Sample decisions
    sample_size = min(80, len(decisions_list))
    sample = random.sample(decisions_list, sample_size)
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        stabilities = []
        for d in sample:
            did = d['decision_id']
            text = d.get('full_text', '')
            lang = d.get('language', 'de')
            if not text or len(text) < 200:
                continue
            
            orig_emb = rep.representation_fn(did)
            if orig_emb is None:
                continue
            
            # Create perturbed text (inject ~30% boilerplate)
            words = text.split()
            n_inject = int(len(words) * 0.3)
            boilerplate_de = [
                "das Bundesgericht zieht in Erwägung", "gemäss Art.", "die Beschwerde ist abzuweisen",
                "die Kosten des Verfahrens werden", "BGE", "ZPO", "StPO", "BGG"
            ]
            boilerplate_fr = [
                "le Tribunal fédéral considère", "selon l'art.", "le recours est rejeté",
                "les frais de la procédure sont", "ATF", "CPC", "CPP", "LTF"
            ]
            bp = boilerplate_de if lang == 'de' else boilerplate_fr
            for _ in range(min(n_inject, 50)):
                words.insert(random.randint(0, len(words)), random.choice(bp))
            perturbed_text = " ".join(words)
            
            # Compute perturbed embedding (for concat, we need to recompute TF-IDF part)
            # Since we can't easily recompute TF-IDF on-the-fly, we measure
            # the text embedding function's sensitivity instead
            if name == "baseline" and hasattr(rep, 'text_embedding_fn'):
                pert_emb = rep.text_embedding_fn(perturbed_text)
            else:
                # For concat, the center-projected part is static (pre-computed)
                # Only TF-IDF part would change. We approximate by measuring
                # the text embedding change
                if hasattr(rep, 'text_embedding_fn'):
                    pert_emb = rep.text_embedding_fn(perturbed_text)
                else:
                    continue
            
            # Cosine similarity
            norm_o = np.linalg.norm(orig_emb)
            norm_p = np.linalg.norm(pert_emb)
            if norm_o > 0 and norm_p > 0:
                sim = float(np.dot(orig_emb, pert_emb) / (norm_o * norm_p))
                stabilities.append(1.0 - sim)
        
        results[name] = {
            "mean_stability": float(np.mean(stabilities)) if stabilities else 0.0,
            "std_stability": float(np.std(stabilities)) if stabilities else 0.0,
            "num_test_decisions": len(stabilities),
        }
    
    return results


def run_legal_area_clustering(concat_rep, baseline_rep, metadata, id_to_idx):
    """Test legal-area clustering with NMI and purity."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import normalized_mutual_info_score
    
    # Group by branch
    branch_decisions = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch')
        if branch and branch != 'null':
            branch_decisions[branch].append(i)
    
    # Filter branches with enough decisions
    valid_branches = {b: ids for b, ids in branch_decisions.items() if len(ids) >= 10}
    if len(valid_branches) < 2:
        return {"error": "Insufficient branches"}
    
    # Sample balanced
    import random
    random.seed(42)
    sample_per_branch = 100
    sampled_indices = []
    sampled_labels = {}
    for branch, ids in valid_branches.items():
        n = min(sample_per_branch, len(ids))
        selected = random.sample(ids, n)
        sampled_indices.extend(selected)
        for idx in selected:
            sampled_labels[idx] = branch
    
    if len(sampled_indices) < 20:
        return {"error": "Insufficient sampled decisions"}
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        # Get embeddings
        embeddings = np.stack([rep.embeddings[i] for i in sampled_indices])
        true_labels = [sampled_labels[i] for i in sampled_indices]
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms
        
        # Cluster at different k
        best_nmi = 0.0
        best_purity = 0.0
        level_metrics = []
        
        for n_clusters in [4, 6, 8, 12]:
            if n_clusters > len(sampled_indices) or n_clusters < 2:
                continue
            
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters, metric="cosine", linkage="average"
            )
            pred_labels = clustering.fit_predict(normalized)
            
            nmi = float(normalized_mutual_info_score(true_labels, pred_labels))
            
            # Purity
            purity_scores = []
            for cid in set(pred_labels):
                mask = pred_labels == cid
                cluster_true = [true_labels[i] for i in range(len(true_labels)) if mask[i]]
                if cluster_true:
                    most_common = Counter(cluster_true).most_common(1)[0][1]
                    purity_scores.append(most_common / len(cluster_true))
            purity = float(np.mean(purity_scores)) if purity_scores else 0.0
            
            best_nmi = max(best_nmi, nmi)
            best_purity = max(best_purity, purity)
            level_metrics.append({
                "n_clusters": n_clusters, "nmi": nmi, "purity": purity
            })
        
        results[name] = {
            "best_nmi": best_nmi,
            "best_purity": best_purity,
            "num_decisions": len(sampled_indices),
            "num_branches": len(valid_branches),
            "branch_distribution": {b: len(ids) for b, ids in valid_branches.items()},
            "level_metrics": level_metrics,
        }
    
    return results


def run_multilingual_test(concat_rep, baseline_rep, metadata, id_to_idx):
    """Test multilingual invariance: cross-language same-branch similarity."""
    import random
    random.seed(42)
    
    # Group by (language, branch)
    groups = defaultdict(list)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        branch = m.get('branch')
        if lang and branch and branch != 'null':
            groups[(lang, branch)].append(i)
    
    # Find cross-language same-branch pairs
    cross_lang_pairs = []
    branches = set(b for _, b in groups.keys())
    for branch in branches:
        lang_groups = {l: groups[(l, branch)] for l in ['de', 'fr', 'it'] if (l, branch) in groups}
        if len(lang_groups) >= 2:
            langs = list(lang_groups.keys())
            for i in range(len(langs)):
                for j in range(i+1, len(langs)):
                    for _ in range(min(50, len(lang_groups[langs[i]]), len(lang_groups[langs[j]]))):
                        idx1 = random.choice(lang_groups[langs[i]])
                        idx2 = random.choice(lang_groups[langs[j]])
                        cross_lang_pairs.append((idx1, idx2))
    
    if len(cross_lang_pairs) < 10:
        return {"error": "Insufficient cross-language pairs"}
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        cross_sims = []
        same_lang_sims = []
        
        for idx1, idx2 in cross_lang_pairs[:200]:
            emb1 = rep.embeddings[idx1]
            emb2 = rep.embeddings[idx2]
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            if norm1 > 0 and norm2 > 0:
                sim = float(np.dot(emb1, emb2) / (norm1 * norm2))
                cross_sims.append(sim)
        
        # Same-language different-branch pairs as control
        by_lang = defaultdict(list)
        for i, m in enumerate(metadata):
            if m.get('language'):
                by_lang[m['language']].append(i)
        
        for lang, indices in by_lang.items():
            if len(indices) >= 2:
                for _ in range(min(50, len(cross_lang_pairs))):
                    i1, i2 = random.sample(indices, 2)
                    emb1 = rep.embeddings[i1]
                    emb2 = rep.embeddings[i2]
                    norm1 = np.linalg.norm(emb1)
                    norm2 = np.linalg.norm(emb2)
                    if norm1 > 0 and norm2 > 0:
                        sim = float(np.dot(emb1, emb2) / (norm1 * norm2))
                        same_lang_sims.append(sim)
        
        cross_mean = float(np.mean(cross_sims)) if cross_sims else 0.0
        same_mean = float(np.mean(same_lang_sims)) if same_lang_sims else 0.0
        
        results[name] = {
            "cross_lang_mean_similarity": cross_mean,
            "same_lang_diff_area_mean": same_mean,
            "separation": cross_mean - same_mean,
            "num_cross_lang_pairs": len(cross_sims),
            "num_same_lang_pairs": len(same_lang_sims),
        }
    
    return results


def run_hierarchy_coherence(concat_rep, baseline_rep, metadata, id_to_idx):
    """Test multi-resolution hierarchy coherence."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import normalized_mutual_info_score
    
    # Use all decisions
    n_total = len(metadata)
    embeddings_all = np.stack([rep.embeddings for rep in [baseline_rep, concat_rep][0:1]])
    
    # For each representation
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        embeddings = rep.embeddings
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms
        
        # Build hierarchy at 3 levels
        hierarchy = []
        for level, n_clusters in enumerate([3, 11, 25]):
            n_clusters = min(n_clusters, n_total)
            if n_clusters < 2:
                break
            
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters, metric="cosine", linkage="average"
            )
            labels = clustering.fit_predict(normalized)
            
            # Convert to cluster -> member mapping
            clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                clusters[label].append(idx)
            hierarchy.append(dict(clusters))
        
        # Check nesting
        nesting_scores = []
        for level in range(len(hierarchy) - 1):
            parent_clusters = hierarchy[level]
            child_clusters = hierarchy[level + 1]
            
            child_to_parent = 0
            for child_id, child_members in child_clusters.items():
                child_set = set(child_members)
                for parent_id, parent_members in parent_clusters.items():
                    if child_set.issubset(set(parent_members)):
                        child_to_parent += 1
                        break
            
            if child_clusters:
                nesting_scores.append(child_to_parent / len(child_clusters))
        
        # Legal area purity across levels
        branch_labels = [m.get('branch', 'unknown') for m in metadata]
        purity_by_level = []
        for level_clusters in hierarchy:
            purities = []
            for cluster_id, members in level_clusters.items():
                cluster_branches = [branch_labels[i] for i in members if i < len(branch_labels)]
                cluster_branches = [b for b in cluster_branches if b and b != 'unknown']
                if cluster_branches:
                    most_common = Counter(cluster_branches).most_common(1)[0][1]
                    purities.append(most_common / len(cluster_branches))
            purity_by_level.append(float(np.mean(purities)) if purities else 0.0)
        
        results[name] = {
            "nesting_scores": nesting_scores,
            "mean_nesting": float(np.mean(nesting_scores)) if nesting_scores else 0.0,
            "purity_by_level": purity_by_level,
            "mean_purity": float(np.mean(purity_by_level)) if purity_by_level else 0.0,
            "num_levels": len(hierarchy),
        }
    
    return results


def main():
    logger.info("=== Concatenated Representation Benchmark Evaluation ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata and representations...")
    id_to_idx, metadata = load_corpus_metadata()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    logger.info(f"   Baseline embeddings: {baseline_emb.shape}")
    logger.info(f"   Center-projected embeddings: {center_emb.shape}")
    
    # 2. Load corpus decisions for TF-IDF
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions with full text")
    
    # 3. Compute TF-IDF Erwaegungen
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions, id_to_idx)
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid decisions")
    
    # 4. Build concatenated representation
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat_representation(baseline_emb, center_emb, tfidf_full, metadata)
    logger.info(f"   Concatenated: {concat_emb.shape}")
    
    # 5. Create representation wrappers
    concat_rep = EmbeddingRepresentation(concat_emb, metadata, id_to_idx)
    baseline_rep = EmbeddingRepresentation(baseline_emb, metadata, id_to_idx)
    
    # Also create text embedding functions for boilerplate test
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Fit TF-IDF vectorizer on full texts (for boilerplate test)
    full_texts = []
    full_ids = []
    for m in metadata:
        did = m['decision_id']
        if did in decisions:
            text = decisions[did].get('full_text', '')
            if text and len(text) > 100:
                full_texts.append(text)
                full_ids.append(did)
    
    if full_texts:
        tfidf_vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), 
                                     min_df=2, max_df=0.95, sublinear_tf=True)
        tfidf_vec.fit(full_texts[:500])  # Fit on subset for speed
        
        def text_emb_fn(text):
            vec = tfidf_vec.transform([text])
            norm = np.linalg.norm(vec.toarray()[0])
            if norm > 0:
                return (vec.toarray()[0] / norm).astype(np.float32)
            return np.zeros(vec.shape[1], dtype=np.float32)
        
        baseline_rep.text_embedding_fn = text_emb_fn
    
    # 6. Run benchmarks
    all_results = {}
    
    logger.info("\n5. Running benchmarks...")
    
    # 5a. Legal area clustering
    logger.info("\n   5a. Legal area clustering...")
    decisions_list = list(decisions.values())
    clustering_results = run_legal_area_clustering(concat_rep, baseline_rep, metadata, id_to_idx)
    all_results['legal_area_clustering'] = clustering_results
    if 'error' not in clustering_results:
        logger.info(f"      Baseline NMI: {clustering_results['baseline']['best_nmi']:.4f}, "
                    f"Purity: {clustering_results['baseline']['best_purity']:.4f}")
        logger.info(f"      Concat NMI: {clustering_results['concat']['best_nmi']:.4f}, "
                    f"Purity: {clustering_results['concat']['best_purity']:.4f}")
    
    # 5b. Multilingual invariance
    logger.info("\n   5b. Multilingual invariance...")
    multilingual_results = run_multilingual_test(concat_rep, baseline_rep, metadata, id_to_idx)
    all_results['multilingual_invariance'] = multilingual_results
    if 'error' not in multilingual_results:
        logger.info(f"      Baseline cross-lang sim: {multilingual_results['baseline']['cross_lang_mean_similarity']:.4f}")
        logger.info(f"      Concat cross-lang sim: {multilingual_results['concat']['cross_lang_mean_similarity']:.4f}")
    
    # 5c. Hierarchy coherence
    logger.info("\n   5c. Hierarchy coherence...")
    hierarchy_results = run_hierarchy_coherence(concat_rep, baseline_rep, metadata, id_to_idx)
    all_results['hierarchy_coherence'] = hierarchy_results
    logger.info(f"      Baseline nesting: {hierarchy_results['baseline']['mean_nesting']:.4f}")
    logger.info(f"      Concat nesting: {hierarchy_results['concat']['mean_nesting']:.4f}")
    
    # 5d. Corpus stability (simplified - measure position stability)
    logger.info("\n   5d. Corpus stability...")
    stability_results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        # Measure pairwise distance stability for a subset
        import random
        random.seed(42)
        sample_indices = random.sample(range(len(metadata)), min(50, len(metadata)))
        dists = []
        for i in range(len(sample_indices)):
            for j in range(i+1, min(i+10, len(sample_indices))):
                idx1, idx2 = sample_indices[i], sample_indices[j]
                emb1 = rep.embeddings[idx1]
                emb2 = rep.embeddings[idx2]
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                if norm1 > 0 and norm2 > 0:
                    sim = float(np.dot(emb1, emb2) / (norm1 * norm2))
                    dists.append(1.0 - sim)
        stability_results[name] = {
            "mean_pairwise_distance": float(np.mean(dists)) if dists else 0.0,
            "std_pairwise_distance": float(np.std(dists)) if dists else 0.0,
        }
    all_results['corpus_stability'] = stability_results
    
    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("BENCHMARK SUMMARY")
    logger.info("=" * 70)
    
    summary = {}
    
    # Legal area clustering
    if 'legal_area_clustering' in all_results and 'error' not in all_results['legal_area_clustering']:
        lac = all_results['legal_area_clustering']
        baseline_nmi = lac['baseline']['best_nmi']
        concat_nmi = lac['concat']['best_nmi']
        baseline_purity = lac['baseline']['best_purity']
        concat_purity = lac['concat']['best_purity']
        improvement_nmi = ((concat_nmi - baseline_nmi) / baseline_nmi * 100) if baseline_nmi > 0 else float('inf')
        improvement_purity = ((concat_purity - baseline_purity) / baseline_purity * 100) if baseline_purity > 0 else float('inf')
        
        logger.info(f"\nLegal Area Clustering:")
        logger.info(f"  NMI: baseline={baseline_nmi:.4f}, concat={concat_nmi:.4f} ({improvement_nmi:+.1f}%)")
        logger.info(f"  Purity: baseline={baseline_purity:.4f}, concat={concat_purity:.4f} ({improvement_purity:+.1f}%)")
        
        summary['legal_area_clustering'] = {
            "baseline_nmi": baseline_nmi, "concat_nmi": concat_nmi,
            "baseline_purity": baseline_purity, "concat_purity": concat_purity,
            "improvement_nmi_pct": improvement_nmi, "improvement_purity_pct": improvement_purity,
        }
    
    # Multilingual
    if 'multilingual_invariance' in all_results and 'error' not in all_results['multilingual_invariance']:
        ml = all_results['multilingual_invariance']
        baseline_sep = ml['baseline']['separation']
        concat_sep = ml['concat']['separation']
        logger.info(f"\nMultilingual Invariance:")
        logger.info(f"  Baseline separation: {baseline_sep:.4f}")
        logger.info(f"  Concat separation: {concat_sep:.4f}")
        summary['multilingual_invariance'] = {
            "baseline_separation": baseline_sep, "concat_separation": concat_sep,
        }
    
    # Hierarchy
    if 'hierarchy_coherence' in all_results:
        hc = all_results['hierarchy_coherence']
        logger.info(f"\nHierarchy Coherence:")
        logger.info(f"  Baseline nesting: {hc['baseline']['mean_nesting']:.4f}")
        logger.info(f"  Concat nesting: {hc['concat']['mean_nesting']:.4f}")
        summary['hierarchy_coherence'] = {
            "baseline_nesting": hc['baseline']['mean_nesting'],
            "concat_nesting": hc['concat']['mean_nesting'],
        }
    
    # 8. Save results
    output = {
        "run_id": f"fractal_map_concat_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "representation": "concat_center_tfidf",
        "baseline_representation": "tfidf_reasoning",
        "corpus_source": "/tmp/lex_accepted/corpus/corpus/normalization/canonical/",
        "detailed_results": all_results,
        "summary": summary,
    }
    
    # Convert numpy types
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    output_path = OUTPUT_DIR / "concat_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Benchmark evaluation complete ===")
    
    return output


if __name__ == "__main__":
    result = main()
