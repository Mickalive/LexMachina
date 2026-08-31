#!/usr/bin/env python3
"""
Evaluation v15 Extension: Full Adversarial Suite on Best Combinations

Tests the v15 winning combinations (linear_citation_concat, linear_hybrid05_concat, 
linear_citation_ridge, linear_citation_w3070) on the COMPLETE v3 adversarial harness
(5 benchmarks: LangDom, JuristPref, Jurivoc, Scale Stability, Boilerplate Resistance).

The v15 CV only tested 2 gates (LangDom, JuristPref). This evaluates whether the 
combinations also pass the other 3 adversarial benchmarks.

Frozen parameters:
- Corpus: 1200 BGer decisions (expanded slice), canonical frozen harness v3
- Config hash: 4323f833fa72366a
- Seed: 42
- Adversarial gates: All 5 benchmarks from v3 harness
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, normalize
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN PARAMETERS - DO NOT CHANGE
# ============================================================
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
np.random.seed(FROZEN_SEED)

CORPUS_PATH = Path("evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")

OUTPUT_DIR = Path("results/evaluation/v15_combinations_full_harness")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Adversarial thresholds (from v3 harness)
LANGDOM_THRESHOLD = 0.85
JURIST_THRESHOLD = 0.5
JURIVOC_THRESHOLD = 0.3
SCALE_STAB_THRESHOLD = 0.95
BOILERPLATE_THRESHOLD = 0.3

LANGDOM_K = 20
JURIST_K = 10

CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber):
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    cl = chamber.lower()
    if any(kw in cl for kw in ["öffentlich", "public"]): return "oeffentliches_recht"
    if any(kw in cl for kw in ["zivil", "civil"]): return "zivilrecht"
    if any(kw in cl for kw in ["straf", "pénal", "penal"]): return "strafrecht"
    if any(kw in cl for kw in ["sozial", "social"]): return "sozialversicherungsrecht"
    return "unknown"

def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n

# ============================================================
# ADVERSARIAL BENCHMARKS (from v3 harness)
# ============================================================

def adversarial_language_dominance(embeddings, metadata, k=LANGDOM_K):
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine', n_jobs=-1)
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / len(neighbor_langs))
    mean_dominance = float(np.mean(dominance_rates))
    return {
        'mean_language_dominance': mean_dominance,
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': LANGDOM_THRESHOLD,
        'status': 'PASS' if mean_dominance < LANGDOM_THRESHOLD else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }

def jurist_pairwise_preference(embeddings, branches, languages, k=JURIST_K):
    n = len(branches)
    nn = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine', n_jobs=-1)
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        has_legal_relevant = False
        has_language_artifact = False
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i:
                has_legal_relevant = True
            if nb != branch_i and nl == lang_i:
                has_language_artifact = True
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    jurist_correct = legal_relevant_count + both_count
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    return {
        "status": "PASS" if legal_neighbor_rate > JURIST_THRESHOLD else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round(language_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(language_artifact_count / total, 4),
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }

def jurivoc_hierarchy_alignment(embeddings, legal_areas, n_clusters_list=None):
    valid_mask = np.array([la is not None and la != 'unknown' for la in legal_areas])
    if not valid_mask.any():
        return {'per_resolution': {}, 'avg_nmi': 0.0, 'avg_ari': 0.0, 'status': 'FAIL', 'note': 'No valid legal_area labels'}
    valid_embeddings = embeddings[valid_mask]
    valid_legal_areas = legal_areas[valid_mask]
    if n_clusters_list is None:
        n_clusters_list = [5, 10, 15, 20, 30, 50]
    results = {}
    for n_clusters in n_clusters_list:
        kmeans = KMeans(n_clusters=n_clusters, random_state=FROZEN_SEED, n_init=10)
        cluster_labels = kmeans.fit_predict(valid_embeddings)
        nmi = normalized_mutual_info_score(valid_legal_areas, cluster_labels)
        ari = adjusted_rand_score(valid_legal_areas, cluster_labels)
        results[f'n_clusters_{n_clusters}'] = {'nmi': float(nmi), 'ari': float(ari)}
    avg_nmi = float(np.mean([v['nmi'] for v in results.values()]))
    avg_ari = float(np.mean([v['ari'] for v in results.values()]))
    return {
        'per_resolution': results,
        'avg_nmi': avg_nmi,
        'avg_ari': avg_ari,
        'status': 'PASS' if avg_nmi > JURIVOC_THRESHOLD else 'FAIL',
        'note': 'NMI with legal_area (proxy for Jurivoc). Higher = better alignment with human legal taxonomy.'
    }

def scale_stability_frozen_pca(embeddings, metadata, valid_indices=None, subsample_frac=0.8, n_trials=10):
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
    else:
        rep_embeddings = embeddings
    n = len(rep_embeddings)
    subsample_size = int(n * subsample_frac)
    pca = PCA(n_components=min(64, n-1), random_state=FROZEN_SEED)
    pca.fit(rep_embeddings)
    full_proj = pca.transform(rep_embeddings)
    full_proj = normalize(full_proj, norm='l2', axis=1)
    similarities = []
    for trial in range(n_trials):
        rng = np.random.RandomState(FROZEN_SEED + trial)
        subsample_idx = rng.choice(n, size=subsample_size, replace=False)
        subsample_emb = rep_embeddings[subsample_idx]
        sub_proj = pca.transform(subsample_emb)
        sub_proj = normalize(sub_proj, norm='l2', axis=1)
        full_proj_sub = full_proj[subsample_idx]
        cos_sims = np.sum(full_proj_sub * sub_proj, axis=1)
        similarities.append(float(np.mean(cos_sims)))
    mean_sim = float(np.mean(similarities))
    std_sim = float(np.std(similarities))
    return {
        'mean_cosine_similarity': mean_sim,
        'std_cosine_similarity': std_sim,
        'subsample_frac': subsample_frac,
        'n_trials': n_trials,
        'pca_dims': pca.n_components_,
        'status': 'PASS' if mean_sim > SCALE_STAB_THRESHOLD else 'FAIL',
        'note': 'Frozen PCA projection consistency under subsampling. Higher = more stable.'
    }

def boilerplate_resistance(embeddings, metadata, valid_indices=None, k=LANGDOM_K):
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]
    boilerplate_dominated = 0
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        if same_lang / k > 0.8:
            boilerplate_dominated += 1
    boilerplate_rate = boilerplate_dominated / len(rep_metadata)
    return {
        'boilerplate_dominated_rate': float(boilerplate_rate),
        'k': k,
        'threshold': BOILERPLATE_THRESHOLD,
        'status': 'PASS' if boilerplate_rate < BOILERPLATE_THRESHOLD else 'FAIL',
        'note': 'Fraction of decisions with >80% same-language neighbors. Lower = less boilerplate-driven.'
    }

def run_full_benchmark_suite(name, embeddings, metadata):
    logger.info(f"\n--- Evaluating {name} ({embeddings.shape[0]} decisions, {embeddings.shape[1]} dim) ---")
    rep_branches = np.array([m.get('branch', 'unknown') for m in metadata])
    rep_languages = np.array([m.get('language', 'unknown') for m in metadata])
    rep_legal_areas = np.array([m.get('legal_area', 'unknown') for m in metadata])
    
    # 1. Adversarial Language Dominance
    lang_dom = adversarial_language_dominance(embeddings, metadata)
    logger.info(f"  Language Dominance: {lang_dom['mean_language_dominance']:.4f} ({lang_dom['status']})")
    
    # 2. Jurist Pairwise Preference
    jurist_pref = jurist_pairwise_preference(embeddings, rep_branches, rep_languages)
    logger.info(f"  Jurist Preference: {jurist_pref['jurist_would_succeed_rate']:.4f} ({jurist_pref['status']})")
    
    # 3. Jurivoc Hierarchy Alignment
    jurivoc = jurivoc_hierarchy_alignment(embeddings, rep_legal_areas)
    logger.info(f"  Jurivoc Alignment (avg NMI): {jurivoc['avg_nmi']:.4f} ({jurivoc['status']})")
    
    # 4. Scale Stability
    scale_stab = scale_stability_frozen_pca(embeddings, metadata)
    logger.info(f"  Scale Stability: {scale_stab['mean_cosine_similarity']:.4f} ({scale_stab['status']})")
    
    # 5. Boilerplate Resistance
    boilerplate = boilerplate_resistance(embeddings, metadata)
    logger.info(f"  Boilerplate Resistance: {boilerplate['boilerplate_dominated_rate']:.4f} ({boilerplate['status']})")
    
    all_pass = all([
        lang_dom['status'] == 'PASS',
        jurist_pref['status'] == 'PASS',
        jurivoc['status'] == 'PASS',
        scale_stab['status'] == 'PASS',
        boilerplate['status'] == 'PASS'
    ])
    
    n_passed = sum([
        lang_dom['status'] == 'PASS',
        jurist_pref['status'] == 'PASS',
        jurivoc['status'] == 'PASS',
        scale_stab['status'] == 'PASS',
        boilerplate['status'] == 'PASS'
    ])
    
    return {
        'name': name,
        'n_decisions': len(embeddings),
        'embedding_dim': int(embeddings.shape[1]),
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'jurivoc_hierarchy_alignment': jurivoc,
        'scale_stability_frozen_pca': scale_stab,
        'boilerplate_resistance': boilerplate,
        'all_benchmarks_pass': all_pass,
        'n_passed': n_passed,
        'n_total': 5
    }

# ============================================================
# COMBINATION BUILDING (from v15b, but on FULL corpus)
# ============================================================

def build_citation_tfidf_full(decisions, svd_dim=128):
    texts, has_content = [], []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            texts.append(text)
            has_content.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim)), set()
    vectorizer = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vectorizer.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1] - 1), random_state=FROZEN_SEED)
    reduced = svd.fit_transform(tfidf)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    result = np.zeros((len(decisions), reduced.shape[1]))
    for idx, emb_idx in enumerate(has_content):
        result[emb_idx] = reduced[idx]
    return result, set(has_content), vectorizer, svd

def build_outcome_tfidf_full(decisions, svd_dim=2):
    texts, has_content = [], []
    for i, d in enumerate(decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(str(outcome))
            has_content.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim)), set()
    vectorizer = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vectorizer.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1] - 1), random_state=FROZEN_SEED)
    reduced = svd.fit_transform(tfidf)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    result = np.zeros((len(decisions), reduced.shape[1]))
    for idx, emb_idx in enumerate(has_content):
        result[emb_idx] = reduced[idx]
    return result, set(has_content), vectorizer, svd

def build_cited_outcome_hybrid(cites_emb, outcome_emb, alpha=0.5):
    hybrid = np.concatenate([normalize_emb(cites_emb) * alpha, normalize_emb(outcome_emb) * (1 - alpha)], axis=1)
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return hybrid / norms

def build_combinations(cp64, corpus, metadata):
    """Build all combination embeddings on FULL corpus."""
    logger.info("Building citation TF-IDF on full corpus...")
    cite_emb, _, _, _ = build_citation_tfidf_full(corpus, svd_dim=128)
    logger.info(f"  Citation TF-IDF: {cite_emb.shape}")
    
    logger.info("Building outcome TF-IDF on full corpus...")
    outcome_emb, _, _, _ = build_outcome_tfidf_full(corpus, svd_dim=2)
    logger.info(f"  Outcome TF-IDF: {outcome_emb.shape}")
    
    logger.info("Building zero-shot hybrid...")
    hybrid05 = build_cited_outcome_hybrid(cite_emb, outcome_emb, alpha=0.5)
    hybrid07 = build_cited_outcome_hybrid(cite_emb, outcome_emb, alpha=0.7)
    logger.info(f"  Hybrid 0.5: {hybrid05.shape}, Hybrid 0.7: {hybrid07.shape}")
    
    combinations = {}
    
    # Zero-shot baselines
    combinations['center_projected_64dim'] = cp64
    combinations['cited_outcome_hybrid_0.5'] = hybrid05
    combinations['cited_outcome_hybrid_0.7'] = hybrid07
    
    # Combinations
    logger.info("Building combinations...")
    
    # linear_citation_concat
    combo_lc = normalize_emb(np.concatenate([normalize_emb(cp64), normalize_emb(cite_emb)], axis=1))
    combinations['linear_citation_concat'] = combo_lc
    logger.info(f"  linear_citation_concat: {combo_lc.shape}")
    
    # linear_hybrid05_concat
    combo_lh = normalize_emb(np.concatenate([normalize_emb(cp64), normalize_emb(hybrid05)], axis=1))
    combinations['linear_hybrid05_concat'] = combo_lh
    logger.info(f"  linear_hybrid05_concat: {combo_lh.shape}")
    
    # linear_citation_w3070
    w_ml, w_cite = 0.3, 0.7
    combo_w = normalize_emb(np.concatenate([normalize_emb(cp64)*w_ml, normalize_emb(cite_emb)*w_cite], axis=1))
    combinations['linear_citation_w3070'] = combo_w
    logger.info(f"  linear_citation_w3070: {combo_w.shape}")
    
    # linear_citation_ridge
    branch_labels = np.array([m.get('branch', 'unknown') for m in metadata])
    unique_branches = sorted(set(branch_labels))
    b2i = {b: i for i, b in enumerate(unique_branches)}
    branch_ints = np.array([b2i[b] for b in branch_labels])
    X_r = np.concatenate([normalize_emb(cp64), normalize_emb(cite_emb)], axis=1)
    scaler = StandardScaler()
    X_rs = scaler.fit_transform(X_r)
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_rs, branch_ints)
    train_proj = X_rs @ ridge.coef_
    combo_r = normalize_emb(np.column_stack([normalize_emb(cp64), normalize_emb(cite_emb), train_proj.reshape(-1,1)]))
    combinations['linear_citation_ridge'] = combo_r
    logger.info(f"  linear_citation_ridge: {combo_r.shape}")
    
    return combinations

def main():
    run_id = f"eval_v15_full_harness_{int(time.time())}"
    logger.info(f"Starting v15 combinations full adversarial harness: {run_id}")
    logger.info(f"Config hash: {FROZEN_CONFIG_HASH}, Seed: {FROZEN_SEED}")
    
    # Load data
    logger.info("Loading corpus and metadata...")
    corpus = []
    with open(CORPUS_PATH) as f:
        for line in f: corpus.append(json.loads(line))
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip(): metadata.append(json.loads(line))
    
    logger.info(f"Loaded {len(corpus)} decisions, {len(metadata)} metadata entries")
    
    # Load center_projected_64
    logger.info("Loading center_projected_64 embeddings...")
    cp64 = np.load(EMBEDDINGS_64_PATH)
    logger.info(f"  Loaded: {cp64.shape}")
    
    # Align corpus to metadata
    meta_ids = {m['decision_id'] for m in metadata}
    corpus_aligned = [d for d in corpus if d['decision_id'] in meta_ids]
    logger.info(f"Aligned corpus: {len(corpus_aligned)} decisions")
    
    # Enrich metadata with branch, language, legal_area, cited_decisions, outcome
    enriched_meta = []
    for m in metadata:
        em = dict(m)
        for d in corpus_aligned:
            if d['decision_id'] == m['decision_id']:
                em['branch'] = d.get('branch', assign_branch(d.get('chamber', '')))
                em['language'] = d.get('language', 'unknown')
                em['legal_area'] = d.get('legal_area', 'unknown')
                em['cited_decisions'] = d.get('cited_decisions', [])
                em['outcome'] = d.get('outcome', '')
                break
        if 'branch' not in em: em['branch'] = assign_branch(em.get('chamber', ''))
        if 'language' not in em: em['language'] = 'de'
        enriched_meta.append(em)
    
    # Build combinations on FULL corpus
    logger.info("\nBuilding combination embeddings on FULL corpus...")
    combinations = build_combinations(cp64, corpus_aligned, enriched_meta)
    
    # Run full adversarial benchmark suite on each
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING FULL v3 ADVERSARIAL HARNESS (5 benchmarks)")
    logger.info("=" * 80)
    
    all_results = {}
    for name, emb in combinations.items():
        results = run_full_benchmark_suite(name, emb, enriched_meta)
        all_results[name] = results
    
    # Save results
    output_file = OUTPUT_DIR / f"v15_full_harness_{run_id}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    with open(OUTPUT_DIR / "v15_full_harness_latest.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 100)
    logger.info("V15 COMBINATIONS - FULL ADVERSARIAL HARNESS SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Representation':<35} {'N':>4} {'Dim':>4} {'LangDom':>8} {'LD':>4} {'Jurist':>7} {'JP':>4} {'Jurivoc':>8} {'JV':>4} {'Scale':>7} {'SC':>4} {'Boiler':>7} {'BP':>4} {'Pass':>4}/5")
    logger.info("-" * 100)
    
    def sort_key(item):
        name, res = item
        n_passed = res['n_passed']
        jurist = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
        lang_dom = res['adversarial_language_dominance']['mean_language_dominance']
        return (-n_passed, -jurist, lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key)
    
    for name, res in sorted_results:
        ld = res['adversarial_language_dominance']['mean_language_dominance']
        ld_status = "✓" if res['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
        jp_status = "✓" if res['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        jv = res['jurivoc_hierarchy_alignment']['avg_nmi']
        jv_status = "✓" if res['jurivoc_hierarchy_alignment']['status'] == 'PASS' else "✗"
        sc = res['scale_stability_frozen_pca']['mean_cosine_similarity']
        sc_status = "✓" if res['scale_stability_frozen_pca']['status'] == 'PASS' else "✗"
        bp = res['boilerplate_resistance']['boilerplate_dominated_rate']
        bp_status = "✓" if res['boilerplate_resistance']['status'] == 'PASS' else "✗"
        
        logger.info(f"{name:<35} {res['n_decisions']:>4} {res['embedding_dim']:>4} {ld:>8.4f} {ld_status:>4} {jp:>7.4f} {jp_status:>4} {jv:>8.4f} {jv_status:>4} {sc:>7.4f} {sc_status:>4} {bp:>7.4f} {bp_status:>4} {res['n_passed']:>4}/5")
    
    # Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS")
    logger.info("=" * 80)
    
    # Find combinations that beat hybrid on all 5
    hybrid05_key = 'cited_outcome_hybrid_0.5'
    hybrid05_results = all_results[hybrid05_key]
    logger.info(f"\nBaseline: {hybrid05_key}")
    logger.info(f"  LangDom: {hybrid05_results['adversarial_language_dominance']['mean_language_dominance']:.4f} ({hybrid05_results['adversarial_language_dominance']['status']})")
    logger.info(f"  Jurist: {hybrid05_results['jurist_pairwise_preference']['jurist_would_succeed_rate']:.4f} ({hybrid05_results['jurist_pairwise_preference']['status']})")
    logger.info(f"  Jurivoc NMI: {hybrid05_results['jurivoc_hierarchy_alignment']['avg_nmi']:.4f} ({hybrid05_results['jurivoc_hierarchy_alignment']['status']})")
    logger.info(f"  Scale: {hybrid05_results['scale_stability_frozen_pca']['mean_cosine_similarity']:.4f} ({hybrid05_results['scale_stability_frozen_pca']['status']})")
    logger.info(f"  Boilerplate: {hybrid05_results['boilerplate_resistance']['boilerplate_dominated_rate']:.4f} ({hybrid05_results['boilerplate_resistance']['status']})")
    logger.info(f"  ALL 5 PASS: {hybrid05_results['all_benchmarks_pass']} ({hybrid05_results['n_passed']}/5)")
    
    combo_names = ['linear_citation_concat', 'linear_hybrid05_concat', 'linear_citation_ridge', 'linear_citation_w3070']
    logger.info(f"\nCombinations vs baseline:")
    for cn in combo_names:
        if cn not in all_results:
            continue
        res = all_results[cn]
        ld_diff = res['adversarial_language_dominance']['mean_language_dominance'] - hybrid05_results['adversarial_language_dominance']['mean_language_dominance']
        jp_diff = res['jurist_pairwise_preference']['jurist_would_succeed_rate'] - hybrid05_results['jurist_pairwise_preference']['jurist_would_succeed_rate']
        jv_diff = res['jurivoc_hierarchy_alignment']['avg_nmi'] - hybrid05_results['jurivoc_hierarchy_alignment']['avg_nmi']
        sc_diff = res['scale_stability_frozen_pca']['mean_cosine_similarity'] - hybrid05_results['scale_stability_frozen_pca']['mean_cosine_similarity']
        bp_diff = res['boilerplate_resistance']['boilerplate_dominated_rate'] - hybrid05_results['boilerplate_resistance']['boilerplate_dominated_rate']
        
        beats_all_5 = res['all_benchmarks_pass'] and hybrid05_results['all_benchmarks_pass']
        beats_2_gates = (res['adversarial_language_dominance']['status'] == 'PASS' and 
                        res['jurist_pairwise_preference']['status'] == 'PASS' and
                        res['jurist_pairwise_preference']['jurist_would_succeed_rate'] > hybrid05_results['jurist_pairwise_preference']['jurist_would_succeed_rate'])
        
        logger.info(f"  {cn}:")
        logger.info(f"    ΔLangDom={ld_diff:+.4f}, ΔJurist={jp_diff:+.4f}, ΔJurivoc={jv_diff:+.4f}, ΔScale={sc_diff:+.4f}, ΔBoiler={bp_diff:+.4f}")
        logger.info(f"    All 5 PASS: {res['all_benchmarks_pass']} ({res['n_passed']}/5), Beats hybrid on 2 gates: {beats_2_gates}")
        if not res['all_benchmarks_pass']:
            failed = []
            if res['adversarial_language_dominance']['status'] == 'FAIL': failed.append('LangDom')
            if res['jurist_pairwise_preference']['status'] == 'FAIL': failed.append('Jurist')
            if res['jurivoc_hierarchy_alignment']['status'] == 'FAIL': failed.append('Jurivoc')
            if res['scale_stability_frozen_pca']['status'] == 'FAIL': failed.append('Scale')
            if res['boilerplate_resistance']['status'] == 'FAIL': failed.append('Boiler')
            logger.info(f"    FAILED benchmarks: {', '.join(failed)}")
    
    logger.info(f"\nResults saved to: {output_file}")
    return all_results

if __name__ == "__main__":
    main()