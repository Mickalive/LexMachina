#!/usr/bin/env python3
"""
Evaluation v12 Temporal Holdout: Train Early → Test Late

HYPOTHESIS (frozen before observation): The v12 cross-mode combination
improvement (linear_citation_ridge: JP=0.860 on random 5-fold CV) is an
artifact of random splitting and will NOT hold when training on temporally
earlier decisions and testing on later ones.

FREEZE BEFORE OBSERVATION:
- Corpus: 1200 BGer decisions (canonical expanded slice)
- Temporal split: First 80% by date → train, last 20% → test
- Baselines: center_projected_64dim, cited_decisions_tfidf
- Combinations: linear_citation_ridge (v12 best), linear_citation_concat,
  linear_hybrid05_concat, linear_citation_w3070, linear_citation_pca128
- Adversarial gates: LangDom < 0.85, JuristPref > 0.5
- Success rule: Mean JP improvement > 0 on temporal test set
- Seed: 42
- Config hash: 4323f833fa72366a

WHY TEMPORAL: Random CV tests whether the combination works on different
samples from the SAME period. Temporal holdout tests whether it generalizes
to FUTURE decisions — a harder and more realistic deployment scenario.

RATIONALE: If v12 combination only helps on random splits but not on
temporal splits, the improvement is spurious (overfitting to temporal
patterns in the training set).
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
from sklearn.preprocessing import StandardScaler
import random
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================
# Paths
# ======================================================================
CORPUS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/v12_temporal_holdout")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# Frozen config
# ======================================================================
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
TRAIN_FRACTION = 0.80  # First 80% by date → train

ADVERSARIAL_CONFIG = {
    'language_dominance_k': 20,
    'language_dominance_threshold': 0.85,
    'jurist_pairwise_k': 10,
    'jurist_pairwise_threshold': 0.5,
}

random.seed(FROZEN_SEED)
np.random.seed(FROZEN_SEED)

# ======================================================================
# Chamber-to-branch mapping (canonical)
# ======================================================================
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


def assign_branch(chamber: str) -> str:
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    cl = chamber.lower()
    if any(kw in cl for kw in ["öffentlich", "public"]):
        return "oeffentliches_recht"
    if any(kw in cl for kw in ["zivil", "civil"]):
        return "zivilrecht"
    if any(kw in cl for kw in ["straf", "pénal", "penal"]):
        return "strafrecht"
    if any(kw in cl for kw in ["sozial", "social"]):
        return "sozialversicherungsrecht"
    return "unknown"


# ======================================================================
# Data Loading
# ======================================================================
def load_corpus():
    """Load canonical corpus with citations and metadata."""
    corpus = []
    with open(CORPUS_PATH) as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from canonical corpus")
    return corpus


def load_baseline_metadata():
    """Load baseline metadata (1200 decisions, canonical harness)."""
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    logger.info(f"Loaded {len(metadata)} baseline metadata entries")
    return metadata


def load_baseline_embeddings():
    """Load center-projected 64-dim embeddings (canonical harness)."""
    embeddings = np.load(EMBEDDINGS_PATH)
    logger.info(f"Loaded embeddings: shape={embeddings.shape}")
    return embeddings


def align_corpus_to_metadata(corpus, metadata):
    """Align corpus entries to metadata by decision_id."""
    meta_ids = {m['decision_id'] for m in metadata}
    aligned = []
    for d in corpus:
        if d['decision_id'] in meta_ids:
            aligned.append(d)
    logger.info(f"Aligned {len(aligned)} corpus entries to metadata")
    return aligned


# ======================================================================
# Temporal Sort and Split
# ======================================================================
def temporal_sort_and_split(corpus_aligned, metadata, embeddings, train_fraction=0.80):
    """
    Sort decisions by date and split into train (earlier) and test (later).
    Returns sorted indices for train and test sets.
    """
    # Get dates from corpus
    dates = []
    for i, d in enumerate(corpus_aligned):
        date_str = d.get('decision_date', '9999-12-31')
        if not date_str or date_str == 'unknown':
            date_str = '9999-12-31'
        dates.append((date_str, i))

    # Sort by date
    dates.sort(key=lambda x: x[0])

    # Split
    n = len(dates)
    split_point = int(n * train_fraction)

    train_indices = [idx for _, idx in dates[:split_point]]
    test_indices = [idx for _, idx in dates[split_point:]]

    train_dates = [d for d, _ in dates[:split_point]]
    test_dates = [d for d, _ in dates[split_point:]]

    logger.info(f"Temporal split: train={len(train_indices)} (first {train_fraction:.0%} by date), "
                f"test={len(test_indices)} (last {1-train_fraction:.0%} by date)")
    logger.info(f"Train date range: {min(train_dates)} to {max(train_dates)}")
    logger.info(f"Test date range: {min(test_dates)} to {max(test_dates)}")
    logger.info(f"Gap between train end and test start: "
                f"{train_dates[-1]} → {test_dates[0]}")

    return train_indices, test_indices, {
        'train_size': len(train_indices),
        'test_size': len(test_indices),
        'train_date_range': [min(train_dates), max(train_dates)],
        'test_date_range': [min(test_dates), max(test_dates)],
        'train_fraction': train_fraction,
    }


# ======================================================================
# Feature Construction (TRAIN ONLY fitting per split)
# ======================================================================
def build_citation_tfidf_fit(decisions):
    """Build cited_decisions TF-IDF features from decisions (fit)."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            texts.append(text)
            has_content.append(i)

    if len(texts) < 5:
        return None, None, np.zeros((len(decisions), 128)), has_content

    vectorizer = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vectorizer.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(128, tfidf.shape[1] - 1), random_state=FROZEN_SEED)
    reduced = svd.fit_transform(tfidf)

    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms

    result = np.zeros((len(decisions), reduced.shape[1]))
    for idx, emb_idx in enumerate(has_content):
        result[emb_idx] = reduced[idx]

    return vectorizer, svd, result, has_content


def build_citation_tfidf_transform(decisions, vectorizer, svd):
    """Transform decisions using fitted vectorizer and SVD."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            texts.append(text)
            has_content.append(i)

    if not texts or vectorizer is None:
        return np.zeros((len(decisions), 128))

    tfidf = vectorizer.transform(texts)
    reduced = svd.transform(tfidf)

    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms

    result = np.zeros((len(decisions), reduced.shape[1]))
    for idx, emb_idx in enumerate(has_content):
        result[emb_idx] = reduced[idx]

    return result


def build_outcome_tfidf_fit(decisions, svd_dim=2):
    """Build outcome TF-IDF features (fit)."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(str(outcome))
            has_content.append(i)

    if len(texts) < 5:
        return None, None, np.zeros((len(decisions), svd_dim))

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

    return vectorizer, svd, result


def build_outcome_tfidf_transform(decisions, vectorizer, svd, svd_dim=2):
    """Transform decisions using fitted outcome vectorizer."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(str(outcome))
            has_content.append(i)

    if not texts or vectorizer is None:
        return np.zeros((len(decisions), svd_dim))

    tfidf = vectorizer.transform(texts)
    reduced = svd.transform(tfidf)

    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms

    result = np.zeros((len(decisions), reduced.shape[1]))
    for idx, emb_idx in enumerate(has_content):
        result[emb_idx] = reduced[idx]

    return result


def build_cited_outcome_hybrid(cites_emb, outcome_emb, alpha=0.5):
    """Build cited_outcome_hybrid: alpha*cites + (1-alpha)*outcome."""
    def norm_emb(emb):
        n = np.linalg.norm(emb, axis=1, keepdims=True)
        n[n == 0] = 1
        return emb / n

    hybrid = np.concatenate([norm_emb(cites_emb) * alpha, norm_emb(outcome_emb) * (1 - alpha)], axis=1)
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return hybrid / norms


def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n


# ======================================================================
# Adversarial Benchmarks (canonical v3 harness)
# ======================================================================
def adversarial_language_dominance(embeddings, metadata, k=20):
    """Compute language dominance on k-NN neighbors."""
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
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
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
    """Simulate jurist pairwise preference using branch/language heuristics."""
    n = len(branches)
    nn = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine')
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
    legal_neighbor_rate = jurist_correct / total
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
    }


def citation_independent_retrieval(test_emb, test_meta, train_emb, train_meta, k=10):
    """Compute citation-independent retrieval rate."""
    nn = NearestNeighbors(n_neighbors=min(k, len(train_emb)), metric='cosine')
    nn.fit(train_emb)
    _, indices = nn.kneighbors(test_emb)

    train_citations = [set(m.get('cited_decisions', [])) for m in train_meta]
    total_queries = len(test_meta)
    legal_retrieved = 0
    citation_independent_retrieved = 0

    for i, meta in enumerate(test_meta):
        holdout_branch = meta.get('branch', 'unknown')
        holdout_legal_area = meta.get('legal_area', 'unknown')
        holdout_citations = set(meta.get('cited_decisions', []))
        neighbor_indices = indices[i]

        for n_idx in neighbor_indices:
            train_meta_n = train_meta[n_idx]
            train_branch = train_meta_n.get('branch', 'unknown')
            train_legal_area = train_meta_n.get('legal_area', 'unknown')
            train_cites = train_citations[n_idx]

            legally_related = (train_branch == holdout_branch and holdout_branch != 'unknown') or \
                             (train_legal_area == holdout_legal_area and holdout_legal_area != 'unknown')
            if legally_related:
                legal_retrieved += 1
                if len(holdout_citations & train_cites) == 0:
                    citation_independent_retrieved += 1

    max_possible = total_queries * k
    legal_rate = legal_retrieved / max_possible if max_possible > 0 else 0
    citation_independent_rate = citation_independent_retrieved / max_possible if max_possible > 0 else 0
    return {
        'total_queries': total_queries,
        'k': k,
        'legal_retrieval_rate': round(legal_rate, 4),
        'citation_independent_retrieval_rate': round(citation_independent_rate, 4),
        'status': 'PASS' if citation_independent_rate >= 0.15 else 'FAIL',
    }


def evaluate_fold(name, train_emb, test_emb, train_meta, test_meta):
    """Full evaluation of a representation on a fold."""
    tn = np.linalg.norm(train_emb, axis=1, keepdims=True)
    tn[tn == 0] = 1
    train_norm = train_emb / tn
    hn = np.linalg.norm(test_emb, axis=1, keepdims=True)
    hn[hn == 0] = 1
    test_norm = test_emb / hn

    train_branches = np.array([m.get('branch', 'unknown') for m in train_meta])
    train_langs = np.array([m.get('language', 'unknown') for m in train_meta])
    test_branches = np.array([m.get('branch', 'unknown') for m in test_meta])
    test_langs = np.array([m.get('language', 'unknown') for m in test_meta])

    lang_dom = adversarial_language_dominance(test_norm, test_meta, k=ADVERSARIAL_CONFIG['language_dominance_k'])
    jurist_pref = simulate_pairwise_preference(test_norm, test_branches, test_langs, k=ADVERSARIAL_CONFIG['jurist_pairwise_k'])
    cite_indep = citation_independent_retrieval(test_norm, test_meta, train_norm, train_meta)

    both_pass = lang_dom['status'] == 'PASS' and jurist_pref['status'] == 'PASS'

    return {
        'name': name,
        'language_dominance': lang_dom,
        'jurist_preference': jurist_pref,
        'citation_independent_retrieval': cite_indep,
        'both_pass': both_pass,
        'langdom_score': lang_dom['mean_language_dominance'],
        'jurist_score': jurist_pref['jurist_would_succeed_rate'],
        'cite_indep_score': cite_indep['citation_independent_retrieval_rate'],
    }


# ======================================================================
# Main: Temporal Holdout
# ======================================================================
def main():
    run_id = f"eval_v12_temporal_{int(time.time())}"
    logger.info(f"Starting v12 temporal holdout: {run_id}")
    logger.info(f"Config: seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH}")
    logger.info(f"Split: train={TRAIN_FRACTION:.0%} earliest, test={1-TRAIN_FRACTION:.0%} latest")

    # 1. Load data
    corpus = load_corpus()
    metadata = load_baseline_metadata()
    embeddings_64 = load_baseline_embeddings()

    # Align corpus to metadata
    corpus_aligned = align_corpus_to_metadata(corpus, metadata)

    # Create enriched metadata
    enriched_meta = []
    for i, m in enumerate(metadata):
        em = dict(m)
        for d in corpus_aligned:
            if d['decision_id'] == m['decision_id']:
                em['branch'] = d.get('branch', assign_branch(d.get('chamber', '')))
                em['language'] = d.get('language', 'unknown')
                em['legal_area'] = d.get('legal_area', 'unknown')
                em['cited_decisions'] = d.get('cited_decisions', [])
                em['outcome'] = d.get('outcome', '')
                em['decision_date'] = d.get('decision_date', 'unknown')
                break
        if 'branch' not in em:
            em['branch'] = assign_branch(em.get('chamber', ''))
        if 'language' not in em:
            em['language'] = 'de'
        enriched_meta.append(em)

    # 2. Temporal sort and split
    train_idx, test_idx, split_info = temporal_sort_and_split(
        corpus_aligned, enriched_meta, embeddings_64, TRAIN_FRACTION
    )

    # Get train/test data
    train_meta = [enriched_meta[i] for i in train_idx]
    test_meta = [enriched_meta[i] for i in test_idx]
    train_emb_64 = embeddings_64[train_idx]
    test_emb_64 = embeddings_64[test_idx]
    train_corpus = [corpus_aligned[i] for i in train_idx]
    test_corpus = [corpus_aligned[i] for i in test_idx]

    # 3. Build features (FIT ON TRAIN ONLY)
    cite_vec, cite_svd, cite_train_emb, _ = build_citation_tfidf_fit(train_corpus)
    cite_test_emb = build_citation_tfidf_transform(test_corpus, cite_vec, cite_svd)

    outcome_vec, outcome_svd, outcome_train_emb = build_outcome_tfidf_fit(train_corpus)
    outcome_test_emb = build_outcome_tfidf_transform(test_corpus, outcome_vec, outcome_svd)

    # 4. Build hybrid features
    hybrid05_train = build_cited_outcome_hybrid(cite_train_emb, outcome_train_emb, alpha=0.5)
    hybrid07_train = build_cited_outcome_hybrid(cite_train_emb, outcome_train_emb, alpha=0.7)
    hybrid05_test = build_cited_outcome_hybrid(cite_test_emb, outcome_test_emb, alpha=0.5)
    hybrid07_test = build_cited_outcome_hybrid(cite_test_emb, outcome_test_emb, alpha=0.7)

    # 5. Evaluate all representations
    results = {}

    # Baseline: center_projected_64dim
    results['center_projected_64dim'] = evaluate_fold(
        'center_projected_64dim', train_emb_64, test_emb_64, train_meta, test_meta)

    # Baseline: citation_tfidf
    results['citation_tfidf'] = evaluate_fold(
        'citation_tfidf', cite_train_emb, cite_test_emb, train_meta, test_meta)

    # Baseline: cited_outcome_hybrid_0.5
    results['cited_outcome_hybrid_0.5'] = evaluate_fold(
        'cited_outcome_hybrid_0.5', hybrid05_train, hybrid05_test, train_meta, test_meta)

    # Baseline: cited_outcome_hybrid_0.7
    results['cited_outcome_hybrid_0.7'] = evaluate_fold(
        'cited_outcome_hybrid_0.7', hybrid07_train, hybrid07_test, train_meta, test_meta)

    # Combination: linear + citation concat
    combo_linear_cite_train = normalize_emb(np.concatenate([normalize_emb(train_emb_64), normalize_emb(cite_train_emb)], axis=1))
    combo_linear_cite_test = normalize_emb(np.concatenate([normalize_emb(test_emb_64), normalize_emb(cite_test_emb)], axis=1))
    results['linear_citation_concat'] = evaluate_fold(
        'linear_citation_concat', combo_linear_cite_train, combo_linear_cite_test, train_meta, test_meta)

    # Combination: linear + hybrid05 concat
    combo_linear_hybrid_train = normalize_emb(np.concatenate([normalize_emb(train_emb_64), normalize_emb(hybrid05_train)], axis=1))
    combo_linear_hybrid_test = normalize_emb(np.concatenate([normalize_emb(test_emb_64), normalize_emb(hybrid05_test)], axis=1))
    results['linear_hybrid05_concat'] = evaluate_fold(
        'linear_hybrid05_concat', combo_linear_hybrid_train, combo_linear_hybrid_test, train_meta, test_meta)

    # Combination: weighted w3070 (30% ML, 70% citation)
    w_ml, w_cite = 0.3, 0.7
    combo_w3070_train = normalize_emb(np.concatenate([normalize_emb(train_emb_64) * w_ml, normalize_emb(cite_train_emb) * w_cite], axis=1))
    combo_w3070_test = normalize_emb(np.concatenate([normalize_emb(test_emb_64) * w_ml, normalize_emb(cite_test_emb) * w_cite], axis=1))
    results['linear_citation_w3070'] = evaluate_fold(
        'linear_citation_w3070', combo_w3070_train, combo_w3070_test, train_meta, test_meta)

    # Combination: PCA reduction (concat ML + citation, PCA to 128d)
    concat_train = np.concatenate([normalize_emb(train_emb_64), normalize_emb(cite_train_emb)], axis=1)
    concat_test = np.concatenate([normalize_emb(test_emb_64), normalize_emb(cite_test_emb)], axis=1)
    pca_combo = PCA(n_components=min(128, concat_train.shape[1]), random_state=FROZEN_SEED)
    combo_pca_train = normalize_emb(pca_combo.fit_transform(concat_train))
    combo_pca_test = normalize_emb(pca_combo.transform(concat_test))
    results['linear_citation_pca128'] = evaluate_fold(
        'linear_citation_pca128', combo_pca_train, combo_pca_test, train_meta, test_meta)

    # Combination: ridge regression (v12 best)
    branch_labels = np.array([m.get('branch', 'unknown') for m in train_meta])
    unique_branches = sorted(set(branch_labels))
    branch_to_int = {b: i for i, b in enumerate(unique_branches)}
    branch_ints = np.array([branch_to_int[b] for b in branch_labels])

    X_train_ridge = np.concatenate([normalize_emb(train_emb_64), normalize_emb(cite_train_emb)], axis=1)
    X_test_ridge = np.concatenate([normalize_emb(test_emb_64), normalize_emb(cite_test_emb)], axis=1)
    scaler = StandardScaler()
    X_train_ridge_s = scaler.fit_transform(X_train_ridge)
    X_test_ridge_s = scaler.transform(X_test_ridge)
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_ridge_s, branch_ints)
    train_proj = X_train_ridge_s @ ridge.coef_
    test_proj = X_test_ridge_s @ ridge.coef_
    combo_ridge_train = normalize_emb(np.column_stack([normalize_emb(train_emb_64), normalize_emb(cite_train_emb), train_proj.reshape(-1, 1)]))
    combo_ridge_test = normalize_emb(np.column_stack([normalize_emb(test_emb_64), normalize_emb(cite_test_emb), test_proj.reshape(-1, 1)]))
    results['linear_citation_ridge'] = evaluate_fold(
        'linear_citation_ridge', combo_ridge_train, combo_ridge_test, train_meta, test_meta)

    # 6. Log results
    logger.info(f"\n{'='*100}")
    logger.info("TEMPORAL HOLDOUT RESULTS")
    logger.info(f"{'='*100}")
    logger.info(f"\n{'Representation':<35} {'JP':>8} {'LD':>8} {'CI':>8} {'Adv':>5}")
    logger.info("-" * 100)
    for name, res in sorted(results.items(), key=lambda x: -x[1]['jurist_score']):
        adv = "PASS" if res['both_pass'] else "FAIL"
        logger.info(f"{name:<35} {res['jurist_score']:>8.4f} {res['langdom_score']:>8.4f} "
                    f"{res['cite_indep_score']:>8.4f} {adv:>5}")

    # 7. Temporal degradation analysis
    logger.info(f"\n{'='*100}")
    logger.info("TEMPORAL DEGRADATION ANALYSIS")
    logger.info(f"{'='*100}")

    # Compare with random CV results (from v12 cross_mode_cv)
    random_cv_best_jp = 0.860  # linear_citation_ridge from random 5-fold CV
    temporal_best_jp = results['linear_citation_ridge']['jurist_score']
    temporal_degradation = random_cv_best_jp - temporal_best_jp

    logger.info(f"\nRandom 5-fold CV (v12):  JP=0.860 (linear_citation_ridge)")
    logger.info(f"Temporal holdout:       JP={temporal_best_jp:.4f} (linear_citation_ridge)")
    logger.info(f"Temporal degradation:   {temporal_degradation:+.4f}")

    if temporal_degradation > 0.1:
        logger.info(f"\n>>> SIGNIFICANT TEMPORAL DEGRADATION ({temporal_degradation:+.4f}) — v12 combination overfits to temporal patterns <<<")
    elif temporal_degradation > 0.05:
        logger.info(f"\n>>> MODERATE TEMPORAL DEGRADATION ({temporal_degradation:+.4f}) — v12 combination partially overfits <<<")
    else:
        logger.info(f"\n>>> MINIMAL TEMPORAL DEGRADATION ({temporal_degradation:+.4f}) — v12 combination generalizes to future decisions <<<")

    # 8. v12 claim assessment
    logger.info(f"\n{'='*100}")
    logger.info("v12 CLAIM ASSESSMENT (TEMPORAL)")
    logger.info(f"{'='*100}")

    # Best baseline on temporal test
    baseline_names = ['center_projected_64dim', 'citation_tfidf', 'cited_outcome_hybrid_0.5', 'cited_outcome_hybrid_0.7']
    best_baseline_jp = max(results[bn]['jurist_score'] for bn in baseline_names)
    best_baseline_name = max(baseline_names, key=lambda bn: results[bn]['jurist_score'])

    combination_names = ['linear_citation_concat', 'linear_hybrid05_concat', 'linear_citation_w3070', 'linear_citation_pca128', 'linear_citation_ridge']
    best_combo_jp = max(results[cn]['jurist_score'] for cn in combination_names)
    best_combo_name = max(combination_names, key=lambda cn: results[cn]['jurist_score'])

    temporal_improvement = best_combo_jp - best_baseline_jp

    logger.info(f"\nBest baseline: {best_baseline_name} JP={best_baseline_jp:.4f}")
    logger.info(f"Best combination: {best_combo_name} JP={best_combo_jp:.4f}")
    logger.info(f"Temporal improvement: {temporal_improvement:+.4f}")

    replicates = temporal_improvement > 0
    is_significant = temporal_improvement > 0.01

    if replicates and is_significant:
        verdict = "REPLICATED"
        evidence_tier = "ACCEPTED"
        logger.info(f"\n>>> VERDICT: REPLICATED — v12 combination generalizes temporally <<<")
    elif replicates:
        verdict = "WEAK_REPLICATION"
        evidence_tier = "EXPLORATORY"
        logger.info(f"\n>>> VERDICT: WEAK REPLICATION — improvement present but small <<<")
    else:
        verdict = "FALSIFIED"
        evidence_tier = "ACCEPTED_NEGATIVE"
        logger.info(f"\n>>> VERDICT: FALSIFIED — v12 combination does NOT generalize temporally <<<")

    # 9. Per-representation comparison with random CV
    logger.info(f"\n{'='*100}")
    logger.info("TEMPORAL vs RANDOM CV COMPARISON")
    logger.info(f"{'='*100}")

    # Known random 5-fold CV values from v12 cross_mode_cv aggregated results
    # Source: results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_latest.json
    # These are 5-fold MEANS, not individual fold values.
    random_cv_jps = {
        'center_projected_64dim': 0.7992,   # jurist_pref_mean (5-fold)
        'citation_tfidf': 0.7850,           # jurist_pref_mean (5-fold)
        'cited_outcome_hybrid_0.5': 0.7800, # jurist_pref_mean (5-fold)
        'cited_outcome_hybrid_0.7': 0.7750, # jurist_pref_mean (5-fold)
        'linear_citation_ridge': 0.8600,    # 5-fold mean across fold_results
    }

    logger.info(f"\n{'Representation':<35} {'Random CV JP':>12} {'Temporal JP':>12} {'Delta':>8}")
    logger.info("-" * 80)
    for name in ['center_projected_64dim', 'citation_tfidf', 'cited_outcome_hybrid_0.5',
                  'cited_outcome_hybrid_0.7', 'linear_citation_ridge']:
        if name in results and name in random_cv_jps:
            delta = results[name]['jurist_score'] - random_cv_jps[name]
            logger.info(f"{name:<35} {random_cv_jps[name]:>12.4f} {results[name]['jurist_score']:>12.4f} {delta:>+8.4f}")

    # 10. Branch-level analysis
    logger.info(f"\n{'='*100}")
    logger.info("BRANCH-LEVEL TEMPORAL ANALYSIS")
    logger.info(f"{'='*100}")

    # Count branches in train and test
    train_branches = [m.get('branch', 'unknown') for m in train_meta]
    test_branches = [m.get('branch', 'unknown') for m in test_meta]
    from collections import Counter
    logger.info(f"\nTrain branches: {Counter(train_branches).most_common()}")
    logger.info(f"Test branches:  {Counter(test_branches).most_common()}")

    # 11. Persist results
    output = {
        'run_id': run_id,
        'direction_version': 10,
        'config_hash': FROZEN_CONFIG_HASH,
        'seed': FROZEN_SEED,
        'split': split_info,
        'hypothesis': 'v12 cross-mode combination JP improvement does NOT hold on temporal holdout',
        'success_rule': 'Mean JP improvement > 0 on temporal test set',
        'results': results,
        'temporal_degradation': {
            'random_cv_best_jp': random_cv_best_jp,
            'temporal_best_jp': temporal_best_jp,
            'degradation': temporal_degradation,
        },
        'v12_claim_assessment': {
            'best_baseline_name': best_baseline_name,
            'best_baseline_jp': best_baseline_jp,
            'best_combo_name': best_combo_name,
            'best_combo_jp': best_combo_jp,
            'temporal_improvement': temporal_improvement,
            'replicates': replicates,
            'is_significant': is_significant,
            'verdict': verdict,
            'evidence_tier': evidence_tier,
        },
        'branch_distribution': {
            'train': dict(Counter(train_branches)),
            'test': dict(Counter(test_branches)),
        },
    }

    with open(OUTPUT_DIR / f"v12_temporal_holdout_{run_id}.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    with open(OUTPUT_DIR / "v12_temporal_holdout_latest.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {OUTPUT_DIR / f'v12_temporal_holdout_{run_id}.json'}")

    return output


if __name__ == "__main__":
    main()
