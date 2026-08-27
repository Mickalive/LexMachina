#!/usr/bin/env python3
"""
Concatenated Representation Benchmark Evaluation (v2)

Tests the concat_center_tfidf representation against formal evaluation benchmarks.
Loads branch metadata from corpus files (not in baseline metadata).
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
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Load branch info from corpus files
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    # Enrich metadata
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_representations():
    """Load pre-computed embeddings."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


def extract_erwaegungen(text, language):
    """Extract Erwaegungen section."""
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n', r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n', r'(?:Considerando\s*:)\s*\n']
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
    """Load corpus decisions."""
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions):
    """Compute TF-IDF on Erwaegungen."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            erwaegungen = extract_erwaegungen(text, lang)
            if erwaegungen.strip():
                texts.append((i, erwaegungen))
    
    if not texts:
        return np.zeros((len(metadata), 128)), []
    
    indices = [t[0] for t in texts]
    only_texts = [t[1] for t in texts]
    
    vectorizer = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
        min_df=2, max_df=0.95, strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(only_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(only_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    tfidf_full = np.zeros((len(metadata), n_comp))
    for j, i in enumerate(indices):
        tfidf_full[i] = reduced[j]
    
    return tfidf_full, indices


def build_concat(baseline_emb, center_emb, tfidf_full):
    """Build concatenated representation."""
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return concat / norms


class RepWrapper:
    """Wraps embeddings for benchmark consumption."""
    def __init__(self, embeddings):
        self.embeddings = embeddings
    
    def get(self, idx):
        return self.embeddings[idx].astype(np.float32)


def compute_purity(true_labels, pred_labels):
    """Compute clustering purity."""
    purity_scores = []
    for cid in set(pred_labels):
        mask = pred_labels == cid
        cluster_true = [true_labels[i] for i in range(len(true_labels)) if mask[i]]
        if cluster_true:
            most_common = Counter(cluster_true).most_common(1)[0][1]
            purity_scores.append(most_common / len(cluster_true))
    return float(np.mean(purity_scores)) if purity_scores else 0.0


def run_legal_area_clustering(concat_rep, baseline_rep, metadata):
    """Legal area clustering benchmark using branch metadata."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import normalized_mutual_info_score
    
    # Group by branch
    branch_decisions = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch')
        if branch and branch != 'null':
            branch_decisions[branch].append(i)
    
    valid_branches = {b: ids for b, ids in branch_decisions.items() if len(ids) >= 10}
    logger.info(f"   Branches found: {list(valid_branches.keys())} ({', '.join(f'{b}:{len(ids)}' for b, ids in valid_branches.items())})")
    
    if len(valid_branches) < 2:
        return {"error": "Insufficient branches", "found": list(branch_decisions.keys())}
    
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
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        embeddings = np.stack([rep.embeddings[i] for i in sampled_indices])
        true_labels = [sampled_labels[i] for i in sampled_indices]
        
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms
        
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
            purity = compute_purity(true_labels, pred_labels)
            
            best_nmi = max(best_nmi, nmi)
            best_purity = max(best_purity, purity)
            level_metrics.append({"n_clusters": n_clusters, "nmi": nmi, "purity": purity})
        
        results[name] = {
            "best_nmi": best_nmi, "best_purity": best_purity,
            "num_decisions": len(sampled_indices),
            "num_branches": len(valid_branches),
            "level_metrics": level_metrics,
        }
    
    return results


def run_multilingual_test(concat_rep, baseline_rep, metadata):
    """Multilingual invariance: cross-language same-branch similarity."""
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
                    n_pairs = min(50, len(lang_groups[langs[i]]), len(lang_groups[langs[j]]))
                    for _ in range(n_pairs):
                        idx1 = random.choice(lang_groups[langs[i]])
                        idx2 = random.choice(lang_groups[langs[j]])
                        cross_lang_pairs.append((idx1, idx2))
    
    logger.info(f"   Cross-language pairs found: {len(cross_lang_pairs)}")
    
    if len(cross_lang_pairs) < 10:
        return {"error": "Insufficient cross-language pairs", "found": len(cross_lang_pairs)}
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        cross_sims = []
        same_lang_sims = []
        
        for idx1, idx2 in cross_lang_pairs[:200]:
            emb1 = rep.embeddings[idx1]
            emb2 = rep.embeddings[idx2]
            norm1, norm2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
            if norm1 > 0 and norm2 > 0:
                cross_sims.append(float(np.dot(emb1, emb2) / (norm1 * norm2)))
        
        # Same-language different-branch control
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
                    norm1, norm2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
                    if norm1 > 0 and norm2 > 0:
                        same_lang_sims.append(float(np.dot(emb1, emb2) / (norm1 * norm2)))
        
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


def run_hierarchy_coherence(concat_rep, baseline_rep, metadata):
    """Multi-resolution hierarchy coherence."""
    from sklearn.cluster import AgglomerativeClustering
    
    n_total = len(metadata)
    branch_labels = [m.get('branch', 'unknown') for m in metadata]
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        norms = np.linalg.norm(rep.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = rep.embeddings / norms
        
        hierarchy = []
        for n_clusters in [3, 11, 25]:
            n_clusters = min(n_clusters, n_total)
            if n_clusters < 2:
                break
            
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters, metric="cosine", linkage="average"
            )
            labels = clustering.fit_predict(normalized)
            clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                clusters[label].append(idx)
            hierarchy.append(dict(clusters))
        
        # Nesting
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
        
        # Purity per level
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
        }
    
    return results


def run_language_purity_test(concat_rep, baseline_rep, metadata):
    """Test language purity ratio (from fractal-map lane's core metric)."""
    from sklearn.cluster import AgglomerativeClustering
    
    def purity_for_field(rep, metadata, field):
        embeddings = rep.embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms
        
        results_by_res = {}
        for res in [0.5, 1.0, 2.0, 3.0]:
            # Use agglomerative with varying k as proxy for Leiden resolution
            n_clusters = max(3, min(30, int(res * 8)))
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters, metric="cosine", linkage="average"
            )
            labels = clustering.fit_predict(normalized)
            
            # Compute purity
            total_purity = 0
            total_size = 0
            for cid in set(labels):
                mask = labels == cid
                cluster_vals = [metadata[i].get(field) for i in np.where(mask)[0] 
                               if metadata[i].get(field)]
                if cluster_vals:
                    most_common = Counter(cluster_vals).most_common(1)[0][1]
                    total_purity += most_common
                    total_size += len(cluster_vals)
            
            purity = total_purity / total_size if total_size > 0 else 0
            results_by_res[f"res_{res}"] = {
                "purity": purity, "n_clusters": n_clusters
            }
        
        return results_by_res
    
    results = {}
    for name, rep in [("baseline", baseline_rep), ("concat", concat_rep)]:
        legal_purity = purity_for_field(rep, metadata, 'legal_area')
        lang_purity = purity_for_field(rep, metadata, 'language')
        
        # Compute ratios
        ratios = {}
        for res_key in legal_purity:
            lp = legal_purity[res_key]['purity']
            lgp = lang_purity[res_key]['purity']
            ratios[res_key] = {
                "legal_purity": lp, "language_purity": lgp,
                "ratio": lp / lgp if lgp > 0 else 0,
            }
        
        results[name] = ratios
    
    return results


def main():
    logger.info("=== Concatenated Representation Benchmark Evaluation (v2) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # Branch distribution
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Load corpus
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    # 3. Compute TF-IDF
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid")
    
    # 4. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 5. Create wrappers
    concat_rep = RepWrapper(concat_emb)
    baseline_rep = RepWrapper(baseline_emb)
    
    # 6. Run benchmarks
    all_results = {}
    
    logger.info("\n5. Running benchmarks...")
    
    logger.info("\n   5a. Legal area clustering...")
    all_results['legal_area_clustering'] = run_legal_area_clustering(concat_rep, baseline_rep, metadata)
    if 'error' not in all_results['legal_area_clustering']:
        lac = all_results['legal_area_clustering']
        logger.info(f"      Baseline: NMI={lac['baseline']['best_nmi']:.4f}, Purity={lac['baseline']['best_purity']:.4f}")
        logger.info(f"      Concat:   NMI={lac['concat']['best_nmi']:.4f}, Purity={lac['concat']['best_purity']:.4f}")
    
    logger.info("\n   5b. Multilingual invariance...")
    all_results['multilingual_invariance'] = run_multilingual_test(concat_rep, baseline_rep, metadata)
    if 'error' not in all_results['multilingual_invariance']:
        ml = all_results['multilingual_invariance']
        logger.info(f"      Baseline: cross_lang={ml['baseline']['cross_lang_mean_similarity']:.4f}, sep={ml['baseline']['separation']:.4f}")
        logger.info(f"      Concat:   cross_lang={ml['concat']['cross_lang_mean_similarity']:.4f}, sep={ml['concat']['separation']:.4f}")
    
    logger.info("\n   5c. Hierarchy coherence...")
    all_results['hierarchy_coherence'] = run_hierarchy_coherence(concat_rep, baseline_rep, metadata)
    hc = all_results['hierarchy_coherence']
    logger.info(f"      Baseline: nesting={hc['baseline']['mean_nesting']:.4f}, purity={hc['baseline']['mean_purity']:.4f}")
    logger.info(f"      Concat:   nesting={hc['concat']['mean_nesting']:.4f}, purity={hc['concat']['mean_purity']:.4f}")
    
    logger.info("\n   5d. Language/legal purity ratio...")
    all_results['purity_ratio'] = run_language_purity_test(concat_rep, baseline_rep, metadata)
    pr = all_results['purity_ratio']
    for res_key in ['res_1.0', 'res_3.0']:
        if res_key in pr.get('baseline', {}) and res_key in pr.get('concat', {}):
            b = pr['baseline'][res_key]
            c = pr['concat'][res_key]
            logger.info(f"      {res_key}: baseline ratio={b['ratio']:.3f}, concat ratio={c['ratio']:.3f}")
    
    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("BENCHMARK SUMMARY")
    logger.info("=" * 70)
    
    summary = {}
    
    if 'legal_area_clustering' in all_results and 'error' not in all_results['legal_area_clustering']:
        lac = all_results['legal_area_clustering']
        b_nmi, c_nmi = lac['baseline']['best_nmi'], lac['concat']['best_nmi']
        b_pur, c_pur = lac['baseline']['best_purity'], lac['concat']['best_purity']
        imp_nmi = ((c_nmi - b_nmi) / b_nmi * 100) if b_nmi > 0 else float('inf')
        imp_pur = ((c_pur - b_pur) / b_pur * 100) if b_pur > 0 else float('inf')
        logger.info(f"\nLegal Area Clustering:")
        logger.info(f"  NMI:    baseline={b_nmi:.4f}, concat={c_nmi:.4f} ({imp_nmi:+.1f}%)")
        logger.info(f"  Purity: baseline={b_pur:.4f}, concat={c_pur:.4f} ({imp_pur:+.1f}%)")
        summary['legal_area_clustering'] = {
            "baseline_nmi": b_nmi, "concat_nmi": c_nmi, "improvement_nmi_pct": imp_nmi,
            "baseline_purity": b_pur, "concat_purity": c_pur, "improvement_purity_pct": imp_pur,
        }
    
    if 'multilingual_invariance' in all_results and 'error' not in all_results['multilingual_invariance']:
        ml = all_results['multilingual_invariance']
        b_sep, c_sep = ml['baseline']['separation'], ml['concat']['separation']
        logger.info(f"\nMultilingual Invariance:")
        logger.info(f"  Baseline separation: {b_sep:.4f}")
        logger.info(f"  Concat separation:   {c_sep:.4f}")
        summary['multilingual_invariance'] = {"baseline_separation": b_sep, "concat_separation": c_sep}
    
    if 'hierarchy_coherence' in all_results:
        hc = all_results['hierarchy_coherence']
        b_nest, c_nest = hc['baseline']['mean_nesting'], hc['concat']['mean_nesting']
        b_pur, c_pur = hc['baseline']['mean_purity'], hc['concat']['mean_purity']
        logger.info(f"\nHierarchy Coherence:")
        logger.info(f"  Baseline: nesting={b_nest:.4f}, purity={b_pur:.4f}")
        logger.info(f"  Concat:   nesting={c_nest:.4f}, purity={c_pur:.4f}")
        summary['hierarchy_coherence'] = {
            "baseline_nesting": b_nest, "concat_nesting": c_nest,
            "baseline_purity": b_pur, "concat_purity": c_pur,
        }
    
    if 'purity_ratio' in all_results:
        pr = all_results['purity_ratio']
        for res_key in ['res_1.0', 'res_3.0']:
            if res_key in pr.get('baseline', {}) and res_key in pr.get('concat', {}):
                b = pr['baseline'][res_key]
                c = pr['concat'][res_key]
                logger.info(f"\nPurity Ratio ({res_key}):")
                logger.info(f"  Baseline: legal={b['legal_purity']:.3f}, lang={b['language_purity']:.3f}, ratio={b['ratio']:.3f}")
                logger.info(f"  Concat:   legal={c['legal_purity']:.3f}, lang={c['language_purity']:.3f}, ratio={c['ratio']:.3f}")
                summary[f'purity_ratio_{res_key}'] = {
                    "baseline_ratio": b['ratio'], "concat_ratio": c['ratio'],
                    "improvement_pct": ((c['ratio'] - b['ratio']) / b['ratio'] * 100) if b['ratio'] > 0 else float('inf'),
                }
    
    # 8. Save
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
    
    output = {
        "run_id": f"fractal_map_concat_benchmark_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "representation": "concat_center_tfidf",
        "baseline_representation": "sentence-transformer-mpnet",
        "corpus_size": len(metadata),
        "detailed_results": all_results,
        "summary": summary,
    }
    
    output_path = OUTPUT_DIR / "concat_benchmark_results_v2.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Benchmark evaluation complete ===")


if __name__ == "__main__":
    main()
