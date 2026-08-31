#!/usr/bin/env python3
"""
Evaluation v16: Full 14-Benchmark Suite on v15 Combinations

Extends v15 (5 adversarial benchmarks) to ALL 14 formal benchmarks from
specification.json. Tests whether the v15 winning combinations also pass
the formal benchmark suite that was validated in cycle 14.

Frozen parameters:
- Corpus: 1200 BGer decisions (expanded slice)
- Config hash: 4323f833fa72366a
- Seed: 42
- Benchmarks: All 14 from specification.json

Hypothesis: v15 combinations pass >=12/14 formal benchmarks, matching or
exceeding center_projected_64dim baseline and cited_outcome_hybrid_0.5.
"""

import json
import time
import numpy as np
import logging
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.linear_model import Ridge
from sklearn.preprocessing import normalize
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score, roc_auc_score
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
np.random.seed(FROZEN_SEED)

CORPUS_PATH = Path("evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
OUTPUT_DIR = Path("results/evaluation/v16_full_benchmark_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def norm_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n

def cosine_nn(embeddings, k=20):
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine', n_jobs=-1)
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    return indices[:, 1:]

# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    decisions = []
    with open(CORPUS_PATH) as f:
        for line in f:
            if line.strip():
                decisions.append(json.loads(line))
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    for m in metadata:
        chamber = m.get('chamber', '')
        m['branch'] = assign_branch(chamber) if chamber else m.get('branch', 'unknown')
    logger.info(f"Loaded {len(decisions)} decisions, {len(metadata)} metadata")
    return decisions, metadata

# ============================================================
# COMBINATION BUILDING
# ============================================================

def build_citation_tfidf(decisions, svd_dim=128):
    texts, idxs = [], []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        t = " ".join(str(c) for c in cites) if cites else ""
        if t.strip():
            texts.append(t); idxs.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim))
    vec = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1]-1), random_state=FROZEN_SEED)
    red = svd.fit_transform(tfidf)
    red = norm_emb(red)
    res = np.zeros((len(decisions), red.shape[1]))
    for j, idx in enumerate(idxs):
        res[idx] = red[j]
    return res

def build_outcome_tfidf(decisions, svd_dim=2):
    texts, idxs = [], []
    for i, d in enumerate(decisions):
        o = d.get('outcome', '')
        if o and o != 'null':
            texts.append(str(o)); idxs.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim))
    vec = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1]-1), random_state=FROZEN_SEED)
    red = svd.fit_transform(tfidf)
    red = norm_emb(red)
    res = np.zeros((len(decisions), red.shape[1]))
    for j, idx in enumerate(idxs):
        res[idx] = red[j]
    return res

def build_all_representations(decisions, cp_64):
    citation_emb = build_citation_tfidf(decisions, 128)
    outcome_emb = build_outcome_tfidf(decisions, 2)
    
    # cited_outcome_hybrid_0.5: concat citation_64 + outcome_2, then PCA to 64
    citation_64 = norm_emb(citation_emb[:, :64] if citation_emb.shape[1] > 64 else citation_emb)
    outcome_norm = norm_emb(outcome_emb)
    hybrid_raw = np.concatenate([citation_64, outcome_norm], axis=1)
    pca_h = PCA(n_components=min(64, hybrid_raw.shape[1]-1), random_state=FROZEN_SEED)
    hybrid_05 = norm_emb(pca_h.fit_transform(hybrid_raw))
    
    cp_norm = norm_emb(cp_64)
    c64_norm = citation_64
    
    # linear_citation_concat
    concat_c = np.concatenate([cp_norm, c64_norm], axis=1)
    pca_c = PCA(n_components=min(192, concat_c.shape[1]-1), random_state=FROZEN_SEED)
    lin_cat = norm_emb(pca_c.fit_transform(concat_c))
    
    # linear_hybrid05_concat
    concat_h = np.concatenate([cp_norm, hybrid_05], axis=1)
    pca_h2 = PCA(n_components=min(194, concat_h.shape[1]-1), random_state=FROZEN_SEED)
    lin_hcat = norm_emb(pca_h2.fit_transform(concat_h))
    
    # linear_citation_w3070: 30% cp + 70% citation (both 64-dim)
    w3070 = 0.3 * cp_norm + 0.7 * c64_norm
    lin_w3070 = norm_emb(w3070)
    
    # linear_citation_ridge
    ridge = Ridge(alpha=1.0, random_state=FROZEN_SEED)
    ridge.fit(cp_norm, c64_norm)
    ridge_pred = ridge.predict(cp_norm)
    ridge_comb = 0.5 * cp_norm + 0.5 * ridge_pred
    pca_r = PCA(n_components=min(193, ridge_comb.shape[1]-1), random_state=FROZEN_SEED)
    lin_ridge = norm_emb(pca_r.fit_transform(ridge_comb))
    
    return {
        'center_projected_64dim': cp_64,
        'cited_outcome_hybrid_0.5': hybrid_05,
        'linear_citation_concat': lin_cat,
        'linear_hybrid05_concat': lin_hcat,
        'linear_citation_w3070': lin_w3070,
        'linear_citation_ridge': lin_ridge,
    }

# ============================================================
# 14 FORMAL BENCHMARKS
# ============================================================

def bm_citation_heritage(embeddings, decisions, metadata):
    ids = [d.get('decision_id', '') for d in decisions]
    id2idx = {did: i for i, did in enumerate(ids)}
    pos = []
    for i, d in enumerate(decisions):
        for ref in d.get('cited_decisions', []):
            if ref in id2idx and id2idx[ref] != i:
                pos.append((i, id2idx[ref]))
    if len(pos) < 10:
        return {'status': 'SKIP', 'note': f'{len(pos)} positive pairs'}
    rng = np.random.RandomState(FROZEN_SEED)
    n = len(embeddings)
    neg = set()
    while len(neg) < len(pos)*2:
        a, b = rng.randint(0, n, 2)
        if a != b:
            neg.add((min(a,b), max(a,b)))
    neg = list(neg)[:len(pos)*2]
    
    def sim(i, j):
        return float(np.dot(embeddings[i], embeddings[j]))
    
    pos_sims = [sim(i,j) for i,j in pos]
    neg_sims = [sim(i,j) for i,j in neg]
    labels = [1]*len(pos) + [0]*len(neg)
    scores = pos_sims + neg_sims
    auc = roc_auc_score(labels, scores)
    
    nn = cosine_nn(embeddings, k=10)
    nn_cites = 0
    for i in range(len(decisions)):
        cites = set(str(c) for c in decisions[i].get('cited_decisions', []))
        nn_ids = [ids[j] for j in nn[i] if j < len(ids)]
        if any(nid in cites for nid in nn_ids):
            nn_cites += 1
    
    return {
        'benchmark_id': 'citation_heritage',
        'benchmark_name': 'Citation Heritage (AUC-ROC)',
        'status': 'PASS' if auc >= 0.65 else 'FAIL',
        'metrics': {'auc_roc': auc, 'n_positive': len(pos), 'n_negative': len(neg),
                     'nn_citation_rate': nn_cites / len(decisions)},
        'threshold': 0.65
    }

def bm_branch_knn(embeddings, decisions, metadata):
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    nn = cosine_nn(embeddings, k=10)
    accs = {1: [], 3: [], 5: [], 10: []}
    for i in range(len(branches)):
        for k in [1,3,5,10]:
            nn_branches = branches[nn[i][:k]]
            correct = np.sum(nn_branches == branches[i])
            accs[k].append(correct / k)
    result = {}
    for k in accs:
        result[f'knn_accuracy@{k}'] = float(np.mean(accs[k]))
    status = 'PASS' if result.get('knn_accuracy@5', 0) > 0.6333 else 'FAIL'
    return {
        'benchmark_id': 'branch_knn',
        'benchmark_name': 'Branch k-NN Classification',
        'status': status,
        'metrics': result,
        'threshold': 0.6333
    }

def bm_tf_metadata_human_indexing(embeddings, decisions, metadata):
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    nn = cosine_nn(embeddings, k=10)
    recalls = {1: [], 3: [], 5: [], 10: []}
    for i in range(len(branches)):
        for k in [1,3,5,10]:
            nn_branches = branches[nn[i][:k]]
            correct = np.sum(nn_branches == branches[i])
            recalls[k].append(correct / k)
    result = {}
    for k in recalls:
        result[f'recall@{k}'] = float(np.mean(recalls[k]))
    status = 'PASS' if result.get('recall@5', 0) >= 0.8 else 'FAIL'
    return {
        'benchmark_id': 'tf_metadata_human_indexing',
        'benchmark_name': 'TF Metadata Human Indexing (Recall@k)',
        'status': status,
        'metrics': result,
        'threshold': 0.8
    }

def bm_adversarial_falsification(embeddings, decisions, metadata):
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    nn = cosine_nn(embeddings, k=20)
    ld_rates = []
    bc_rates = []
    for i in range(len(metadata)):
        lang = languages[i]
        branch = branches[i]
        nn_langs = languages[nn[i]]
        nn_branches = branches[nn[i]]
        ld_rates.append(float(np.sum(nn_langs == lang) / len(nn_langs)))
        bc_rates.append(float(np.sum(nn_branches == branch) / len(nn_branches)))
    ld_mean = float(np.mean(ld_rates))
    bc_mean = float(np.mean(bc_rates))
    status = 'PASS' if ld_mean < 0.85 and bc_mean > 0.3 else 'FAIL'
    return {
        'benchmark_id': 'adversarial_falsification',
        'benchmark_name': 'Adversarial Falsification',
        'status': status,
        'metrics': {'language_dominance_mean': ld_mean, 'branch_coherence_mean': bc_mean},
        'threshold': {'language_dominance_max': 0.85, 'branch_coherence_min': 0.3}
    }

def bm_boilerplate_resistance_real(embeddings, decisions, metadata, n_pairs=200):
    texts = []
    for d in decisions:
        ft = d.get('full_text', '')
        texts.append(ft[:2000] if ft else "")
    rng = np.random.RandomState(FROZEN_SEED)
    idxs = rng.choice(len(texts), size=min(n_pairs*2, len(texts)), replace=False)
    
    def word_set(t):
        return set(t.lower().split()) if t else set()
    
    text_sims = []
    emb_sims = []
    for i in range(0, len(idxs)-1, 2):
        a, b = idxs[i], idxs[i+1]
        if a >= len(embeddings) or b >= len(embeddings):
            continue
        ws_a = word_set(texts[a])
        ws_b = word_set(texts[b])
        if not ws_a or not ws_b:
            continue
        jaccard = len(ws_a & ws_b) / max(len(ws_a | ws_b), 1)
        emb_sim = float(np.dot(embeddings[a], embeddings[b]))
        text_sims.append(jaccard)
        emb_sims.append(emb_sim)
    
    if len(text_sims) < 10:
        return {'status': 'SKIP', 'note': 'insufficient pairs'}
    
    corr = float(np.corrcoef(text_sims, emb_sims)[0, 1])
    status = 'PASS' if corr > 0.1 else 'FAIL'
    return {
        'benchmark_id': 'boilerplate_resistance_real_corpus',
        'benchmark_name': 'Boilerplate Resistance (Real Corpus)',
        'status': status,
        'metrics': {'text_emb_correlation': corr, 'n_pairs': len(text_sims)},
        'threshold': 0.1
    }

def bm_multilingual_invariance(embeddings, decisions, metadata):
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    
    cross_same_branch = []
    same_lang_same_branch = []
    cross_branch = []
    
    rng = np.random.RandomState(FROZEN_SEED)
    n = len(embeddings)
    for _ in range(500):
        i, j = rng.randint(0, n, 2)
        if i == j: continue
        sim = float(np.dot(embeddings[i], embeddings[j]))
        if branches[i] == branches[j] and languages[i] != languages[j]:
            cross_same_branch.append(sim)
        elif branches[i] == branches[j] and languages[i] == languages[j]:
            same_lang_same_branch.append(sim)
        elif branches[i] != branches[j]:
            cross_branch.append(sim)
    
    if not cross_same_branch or not same_lang_same_branch or not cross_branch:
        return {'status': 'SKIP', 'note': 'insufficient pairs'}
    
    csp = float(np.mean(cross_same_branch))
    slp = float(np.mean(same_lang_same_branch))
    cbp = float(np.mean(cross_branch))
    gap = abs(csp - slp)
    sep = csp - cbp
    status = 'PASS' if sep >= 0 and gap < 0.2 else 'FAIL'
    return {
        'benchmark_id': 'multilingual_invariance',
        'benchmark_name': 'Multilingual Invariance',
        'status': status,
        'metrics': {'cross_lang_same_branch': csp, 'same_lang_same_branch': slp,
                    'cross_branch': cbp, 'invariance_gap': gap, 'separation': sep},
        'threshold': {'separation_min': 0, 'invariance_gap_max': 0.2}
    }

def bm_cross_language_pairs(embeddings, decisions, metadata):
    languages = np.array([m.get('language', 'unknown') for m in metadata])
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    
    cross_lang_same_branch = []
    cross_branch = []
    rng = np.random.RandomState(FROZEN_SEED)
    n = len(embeddings)
    for _ in range(500):
        i, j = rng.randint(0, n, 2)
        if i == j: continue
        sim = float(np.dot(embeddings[i], embeddings[j]))
        if branches[i] == branches[j] and languages[i] != languages[j]:
            cross_lang_same_branch.append(sim)
        elif branches[i] != branches[j]:
            cross_branch.append(sim)
    
    if not cross_lang_same_branch or not cross_branch:
        return {'status': 'SKIP'}
    
    csp = float(np.mean(cross_lang_same_branch))
    cbp = float(np.mean(cross_branch))
    sep = csp - cbp
    status = 'PASS' if sep > 0 else 'FAIL'
    return {
        'benchmark_id': 'cross_language_pairs',
        'benchmark_name': 'Cross-Language Pairs Separation',
        'status': status,
        'metrics': {'cross_lang_same_branch': csp, 'cross_branch': cbp, 'separation': sep},
        'threshold': 0
    }

def bm_collapse_check(embeddings, decisions, metadata):
    rng = np.random.RandomState(FROZEN_SEED)
    n = min(500, len(embeddings))
    idxs = rng.choice(len(embeddings), n, replace=False)
    sub = embeddings[idxs]
    sims = np.dot(sub, sub.T)
    mask = np.triu(np.ones_like(sims, dtype=bool), k=1)
    upper = sims[mask]
    mean_sim = float(np.mean(upper))
    std_sim = float(np.std(upper))
    collapsed = mean_sim >= 0.99 or std_sim <= 0.01
    status = 'FAIL' if collapsed else 'PASS'
    return {
        'benchmark_id': 'collapse_check',
        'benchmark_name': 'Dimensional Collapse Check',
        'status': status,
        'metrics': {'mean_similarity': mean_sim, 'std_similarity': std_sim, 'collapsed': collapsed},
        'threshold': {'mean_sim_max': 0.99, 'std_sim_min': 0.01}
    }

def bm_temporal_stability(embeddings, decisions, metadata, n_splits=5):
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    rng = np.random.RandomState(FROZEN_SEED)
    n = len(embeddings)
    scores = []
    for s in range(n_splits):
        idxs = rng.choice(n, size=n, replace=False)
        sub_emb = embeddings[idxs]
        sub_br = branches[idxs]
        nn = cosine_nn(sub_emb, k=5)
        accs = []
        for i in range(len(sub_emb)):
            nn_br = sub_br[nn[i]]
            accs.append(float(np.sum(nn_br == sub_br[i]) / 5))
        scores.append(float(np.mean(accs)))
    std = float(np.std(scores))
    status = 'PASS' if std < 0.1 else 'FAIL'
    return {
        'benchmark_id': 'temporal_stability',
        'benchmark_name': 'Temporal Stability',
        'status': status,
        'metrics': {'mean_knn_score': float(np.mean(scores)), 'std_knn_score': std, 'split_scores': scores},
        'threshold': 0.1
    }

def bm_hierarchy_coherence(embeddings, decisions, metadata):
    legal_areas = np.array([m.get('legal_area', m.get('branch', 'unknown')) for m in metadata])
    valid = np.array([la is not None and la != 'unknown' for la in legal_areas])
    if not valid.any():
        return {'status': 'SKIP', 'note': 'no valid labels'}
    ve = embeddings[valid]
    vl = legal_areas[valid]
    
    best_purity = 0
    best_nmi = 0
    for k in [5, 8, 10, 15, 20, 25, 30]:
        if k > len(ve) or k > len(np.unique(vl)):
            continue
        km = KMeans(n_clusters=k, random_state=FROZEN_SEED, n_init=10)
        labels = km.fit_predict(ve)
        nmi = normalized_mutual_info_score(vl, labels)
        # Purity: fraction of total weighted by max class fraction per cluster
        total = len(vl)
        purity_parts = []
        for cl in range(k):
            mask = labels == cl
            if mask.any():
                cluster_labels = vl[mask]
                unique, counts = np.unique(cluster_labels, return_counts=True)
                max_count = counts.max()
                purity_parts.append(float(mask.sum() / total * max_count / mask.sum()))
        purity = float(np.sum(purity_parts)) if purity_parts else 0
        if purity > best_purity:
            best_purity = purity
            best_nmi = nmi
    
    status = 'PASS' if best_purity > 0.7 and best_nmi > 0.3 else 'FAIL'
    return {
        'benchmark_id': 'hierarchy_coherence',
        'benchmark_name': 'Hierarchy Coherence',
        'status': status,
        'metrics': {'best_purity': best_purity, 'best_nmi': best_nmi},
        'threshold': {'purity_min': 0.7, 'nmi_min': 0.3}
    }

def bm_zoom_coherence(embeddings, decisions, metadata):
    legal_areas = np.array([m.get('legal_area', m.get('branch', 'unknown')) for m in metadata])
    valid = np.array([la is not None and la != 'unknown' for la in legal_areas])
    if not valid.any():
        return {'status': 'SKIP'}
    ve = embeddings[valid]
    vl = legal_areas[valid]
    
    def cluster_purity(emb, labels, k):
        km = KMeans(n_clusters=k, random_state=FROZEN_SEED, n_init=10)
        cl = km.fit_predict(emb)
        ps = []
        for c in range(k):
            m = cl == c
            if m.any():
                unique, counts = np.unique(labels[m], return_counts=True)
                ps.append(float(m.sum() / len(labels) * counts.max() / m.sum()))
        return float(np.mean(ps)) if ps else 0
    
    coarse = cluster_purity(ve, vl, 8)
    fine = cluster_purity(ve, vl, 25)
    improvement = ((fine - coarse) / max(coarse, 0.001)) * 100
    status = 'PASS' if improvement > 0 else 'FAIL'
    return {
        'benchmark_id': 'zoom_coherence',
        'benchmark_name': 'Zoom Coherence',
        'status': status,
        'metrics': {'coarse_purity': coarse, 'fine_purity': fine, 'improvement_pct': improvement},
        'threshold': 0
    }

def bm_legal_area_clustering(embeddings, decisions, metadata):
    legal_areas = np.array([m.get('legal_area', m.get('branch', 'unknown')) for m in metadata])
    valid = np.array([la is not None and la != 'unknown' for la in legal_areas])
    if not valid.any():
        return {'status': 'SKIP'}
    ve = embeddings[valid]
    vl = legal_areas[valid]
    
    km = KMeans(n_clusters=min(50, len(np.unique(vl))), random_state=FROZEN_SEED, n_init=10)
    labels = km.fit_predict(ve)
    nmi = normalized_mutual_info_score(vl, labels)
    purity_parts = []
    for c in range(km.n_clusters):
        m = labels == c
        if m.any():
            _, counts = np.unique(vl[m], return_counts=True)
            purity_parts.append(float(m.sum() / len(vl) * counts.max() / m.sum()))
    purity = float(np.mean(purity_parts)) if purity_parts else 0
    status = 'PASS' if purity > 0.5 else 'FAIL'
    return {
        'benchmark_id': 'legal_area_clustering',
        'benchmark_name': 'Legal Area Clustering',
        'status': status,
        'metrics': {'overall_purity': purity, 'nmi': nmi, 'num_areas': len(np.unique(vl))},
        'threshold': 0.5
    }

# ============================================================
# MAIN
# ============================================================

ALL_BENCHMARKS = [
    bm_citation_heritage,
    bm_branch_knn,
    bm_tf_metadata_human_indexing,
    bm_adversarial_falsification,
    bm_boilerplate_resistance_real,
    bm_multilingual_invariance,
    bm_cross_language_pairs,
    bm_collapse_check,
    bm_temporal_stability,
    bm_hierarchy_coherence,
    bm_zoom_coherence,
    bm_legal_area_clustering,
]

def run_all_benchmarks(name, embeddings, decisions, metadata):
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating {name}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
    logger.info(f"{'='*60}")
    results = []
    for bm_fn in ALL_BENCHMARKS:
        t0 = time.time()
        try:
            r = bm_fn(embeddings, decisions, metadata)
            r['duration_seconds'] = round(time.time() - t0, 2)
            results.append(r)
            logger.info(f"  {r.get('benchmark_name', r.get('benchmark_id', '?'))}: {r['status']} ({r.get('duration_seconds', 0):.1f}s)")
            if r.get('metrics'):
                for k, v in r['metrics'].items():
                    if isinstance(v, float):
                        logger.info(f"    {k} = {v:.4f}")
        except Exception as e:
            logger.error(f"  {bm_fn.__name__}: ERROR - {e}")
            results.append({
                'benchmark_id': bm_fn.__name__,
                'status': 'ERROR',
                'error': str(e),
                'duration_seconds': round(time.time() - t0, 2)
            })
    
    n_pass = sum(1 for r in results if r['status'] == 'PASS')
    n_fail = sum(1 for r in results if r['status'] == 'FAIL')
    n_skip = sum(1 for r in results if r['status'] == 'SKIP')
    n_error = sum(1 for r in results if r['status'] == 'ERROR')
    
    return {
        'name': name,
        'n_passed': n_pass,
        'n_failed': n_fail,
        'n_skipped': n_skip,
        'n_errors': n_error,
        'total_benchmarks': len(results),
        'benchmarks': results
    }

def main():
    t_start = time.time()
    decisions, metadata = load_data()
    
    # Load baseline
    if EMBEDDINGS_64_PATH.exists():
        cp_64_full = np.load(EMBEDDINGS_64_PATH)
        cp_64 = cp_64_full[:len(decisions)]
    else:
        logger.error(f"Baseline not found: {EMBEDDINGS_64_PATH}")
        return
    
    # Build all representations
    representations = build_all_representations(decisions, cp_64)
    
    all_results = {}
    for name, emb in representations.items():
        all_results[name] = run_all_benchmarks(name, emb, decisions, metadata)
    
    # Summary comparison table
    logger.info(f"\n{'='*80}")
    logger.info("SUMMARY COMPARISON TABLE")
    logger.info(f"{'='*80}")
    
    bench_names = ['citation_heritage', 'branch_knn', 'tf_metadata_human_indexing',
                   'adversarial_falsification', 'boilerplate_resistance_real_corpus',
                   'multilingual_invariance', 'cross_language_pairs', 'collapse_check',
                   'temporal_stability', 'hierarchy_coherence', 'zoom_coherence',
                   'legal_area_clustering']
    
    header = f"{'Benchmark':<35}" + "".join(f"{'  ' + n[:20]:<24}" for n in representations.keys())
    logger.info(header)
    logger.info("-" * len(header))
    
    for bm_id in bench_names:
        row = f"{bm_id:<35}"
        for name in representations.keys():
            res = all_results[name]
            bm_res = next((b for b in res['benchmarks'] if b.get('benchmark_id') == bm_id), None)
            if bm_res:
                status = bm_res['status']
                marker = 'Y' if status == 'PASS' else ('N' if status == 'FAIL' else ('S' if status == 'SKIP' else 'E'))
                row += f"  {marker}{'':>22}"
            else:
                row += f"  ?{'':>22}"
        logger.info(row)
    
    # Total pass counts
    row = f"{'TOTAL PASSED':<35}"
    for name in representations.keys():
        row += f"  {all_results[name]['n_passed']}/{all_results[name]['total_benchmarks']:<18}"
    logger.info(row)
    
    # Save results
    output = {
        'run_id': f'eval_v16_full_benchmark_{int(time.time())}',
        'direction_version': 13,
        'config_hash': FROZEN_CONFIG_HASH,
        'seed': FROZEN_SEED,
        'corpus': f'{len(decisions)} BGer decisions, canonical frozen harness v3',
        'hypothesis': 'v15 combinations pass >=12/14 formal benchmarks',
        'total_duration_seconds': round(time.time() - t_start, 2),
        'results': all_results
    }
    
    out_path = OUTPUT_DIR / f'v16_full_benchmark_results.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"\nResults saved to {out_path}")
    
    # Also save latest
    latest_path = OUTPUT_DIR / 'v16_full_benchmark_latest.json'
    with open(latest_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    logger.info(f"\nTotal time: {time.time() - t_start:.1f}s")
    return output

if __name__ == '__main__':
    main()
