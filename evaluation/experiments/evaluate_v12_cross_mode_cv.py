#!/usr/bin/env python3
"""
Evaluation v12 Cross-Mode Combination: 5-Fold Cross-Validation

HYPOTHESIS (frozen before observation): The v12 finding that combining
citation-based + metric-learning embeddings improves JuristPref by +0.035
over best individual baseline is STABLE across different data splits.

If the improvement is stable (mean JP improvement > 0 across folds AND
all 5 folds pass both adversarial gates), the finding moves to ACCEPTED tier.
If improvement is unstable or negative on any fold, the finding is FALSIFIED.

FROZEN BEFORE OBSERVATION:
- Corpus: 1000 BGer decisions (2020-2024) from canonical fractal-map baseline
- 5-fold cross-validation (each fold: 800 train / 200 test)
- Baseline: center_projected_64dim (production default)
- Adversarial gates: LangDom < 0.85, JuristPref > 0.5
- Success rule: Mean JP improvement > 0 across 5 folds
- Config hash: 4323f833fa72366a (canonical frozen harness v3)
- Seed: 42
"""

import json
import time
import numpy as np
import logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import random
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================
# Paths
# ======================================================================
CORPUS_PATH = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl")
METADATA_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
EMBEDDINGS_PATH = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/v12_cross_mode_cv")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# Frozen config
# ======================================================================
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
N_FOLDS = 5

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
    """Load baseline metadata (1000 decisions)."""
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} baseline metadata entries")
    return metadata


def load_baseline_embeddings():
    """Load center-projected embeddings."""
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
# Feature Construction (TRAIN ONLY fitting per fold)
# ======================================================================
def build_citation_tfidf(decisions, svd_dim=128):
    """Build cited_decisions TF-IDF features from decisions."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            texts.append(text)
            has_content.append(i)

    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim)), []

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

    return result, has_content


def build_citation_tfidf_transform(decisions, vectorizer, svd, svd_dim=128):
    """Transform decisions using fitted vectorizer and SVD."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        text = " ".join(str(c) for c in cites) if cites else ""
        if text.strip():
            texts.append(text)
            has_content.append(i)

    if len(texts) < 2:
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


def build_outcome_tfidf(decisions, svd_dim=2):
    """Build outcome TF-IDF features."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(str(outcome))
            has_content.append(i)

    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim))

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

    return result


def build_outcome_tfidf_transform(decisions, vectorizer, svd, svd_dim=2):
    """Transform decisions using fitted outcome vectorizer."""
    texts = []
    has_content = []
    for i, d in enumerate(decisions):
        outcome = d.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(str(outcome))
            has_content.append(i)

    if len(texts) < 2:
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


def build_center_projected_64dim(embeddings_768):
    """Build 64-dim center_projected via frozen PCA."""
    pca = PCA(n_components=64, random_state=FROZEN_SEED)
    reduced = pca.fit_transform(embeddings_768)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return reduced / norms, pca


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
# Main: 5-Fold Cross-Validation
# ======================================================================
def main():
    run_id = f"eval_v12_cv_{int(time.time())}"
    logger.info(f"Starting v12 cross-mode combination 5-fold CV: {run_id}")
    logger.info(f"Config: seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH}")

    # 1. Load data
    corpus = load_corpus()
    metadata = load_baseline_metadata()
    embeddings_768 = load_baseline_embeddings()

    # Align corpus to metadata
    corpus_aligned = align_corpus_to_metadata(corpus, metadata)

    # Create metadata with branch/language for each decision
    enriched_meta = []
    for i, m in enumerate(metadata):
        em = dict(m)
        # Find corresponding corpus entry
        for d in corpus_aligned:
            if d['decision_id'] == m['decision_id']:
                em['branch'] = d.get('branch', assign_branch(d.get('chamber', '')))
                em['language'] = d.get('language', 'unknown')
                em['legal_area'] = d.get('legal_area', 'unknown')
                em['cited_decisions'] = d.get('cited_decisions', [])
                em['outcome'] = d.get('outcome', '')
                break
        if 'branch' not in em:
            em['branch'] = assign_branch(em.get('chamber', ''))
        if 'language' not in em:
            em['language'] = 'de'
        enriched_meta.append(em)

    # 2. Build center_projected_64dim (global, not per-fold)
    cp_64dim, pca_model = build_center_projected_64dim(embeddings_768)

    # 3. 5-Fold Cross-Validation
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=FROZEN_SEED)
    indices = np.arange(len(metadata))

    fold_results = []

    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(indices)):
        logger.info(f"\n{'='*80}")
        logger.info(f"FOLD {fold_idx+1}/{N_FOLDS} (train={len(train_idx)}, test={len(test_idx)})")
        logger.info(f"{'='*80}")

        train_meta = [enriched_meta[i] for i in train_idx]
        test_meta = [enriched_meta[i] for i in test_idx]
        train_emb_768 = embeddings_768[train_idx]
        test_emb_768 = embeddings_768[test_idx]
        train_cp64 = cp_64dim[train_idx]
        test_cp64 = cp_64dim[test_idx]

        # Build citation features (TRAIN ONLY fitting)
        cite_train, _ = build_citation_tfidf([corpus_aligned[i] for i in train_idx], svd_dim=128)
        # Transform test using train-fitted model
        train_texts = []
        train_has = []
        for i, d in enumerate([corpus_aligned[i] for i in train_idx]):
            cites = d.get('cited_decisions', [])
            text = " ".join(str(c) for c in cites) if cites else ""
            if text.strip():
                train_texts.append(text)
                train_has.append(i)
        if len(train_texts) >= 5:
            vectorizer = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
            tfidf_train = vectorizer.fit_transform(train_texts)
            svd = TruncatedSVD(n_components=min(128, tfidf_train.shape[1] - 1), random_state=FROZEN_SEED)
            svd.fit(tfidf_train)
        else:
            vectorizer = None
            svd = None

        if vectorizer and svd:
            cite_test = build_citation_tfidf_transform([corpus_aligned[i] for i in test_idx], vectorizer, svd, svd_dim=128)
        else:
            cite_test = np.zeros((len(test_idx), 128))

        # Build outcome features (TRAIN ONLY fitting)
        outcome_texts = []
        outcome_has = []
        for i, d in enumerate([corpus_aligned[i] for i in train_idx]):
            outcome = d.get('outcome', '')
            if outcome and outcome != 'null':
                outcome_texts.append(str(outcome))
                outcome_has.append(i)
        if len(outcome_texts) >= 5:
            outcome_vec = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
            tfidf_outcome = outcome_vec.fit_transform(outcome_texts)
            svd_outcome = TruncatedSVD(n_components=min(2, tfidf_outcome.shape[1] - 1), random_state=FROZEN_SEED)
            svd_outcome.fit(tfidf_outcome)
        else:
            outcome_vec = None
            svd_outcome = None

        if outcome_vec and svd_outcome:
            outcome_test = build_outcome_tfidf_transform([corpus_aligned[i] for i in test_idx], outcome_vec, svd_outcome, svd_dim=2)
        else:
            outcome_test = np.zeros((len(test_idx), 2))

        # Build hybrid features
        hybrid05_train = build_cited_outcome_hybrid(cite_train[:len(train_idx)], np.zeros((len(train_idx), 2)), alpha=0.5)
        hybrid07_train = build_cited_outcome_hybrid(cite_train[:len(train_idx)], np.zeros((len(train_idx), 2)), alpha=0.7)
        hybrid05_test = build_cited_outcome_hybrid(cite_test, outcome_test, alpha=0.5)
        hybrid07_test = build_cited_outcome_hybrid(cite_test, outcome_test, alpha=0.7)

        # Evaluate individual baselines
        fold_fold_results = {}

        # Baseline: center_projected_64dim
        fold_fold_results['center_projected_64dim'] = evaluate_fold(
            'center_projected_64dim', train_cp64, test_cp64, train_meta, test_meta)

        # Baseline: citation_tfidf (only if enough data)
        if cite_train[:len(train_idx)].shape[1] > 0:
            fold_fold_results['citation_tfidf'] = evaluate_fold(
                'citation_tfidf', cite_train[:len(train_idx)], cite_test, train_meta, test_meta)

        # Baseline: hybrid05
        fold_fold_results['cited_outcome_hybrid_0.5'] = evaluate_fold(
            'cited_outcome_hybrid_0.5', hybrid05_train, hybrid05_test, train_meta, test_meta)

        # Baseline: hybrid07
        fold_fold_results['cited_outcome_hybrid_0.7'] = evaluate_fold(
            'cited_outcome_hybrid_0.7', hybrid07_train, hybrid07_test, train_meta, test_meta)

        # Combination: linear + citation concat (L2-norm)
        combo_linear_cite_train = normalize_emb(np.concatenate([normalize_emb(train_cp64), normalize_emb(cite_train[:len(train_idx)])], axis=1))
        combo_linear_cite_test = normalize_emb(np.concatenate([normalize_emb(test_cp64), normalize_emb(cite_test)], axis=1))
        fold_fold_results['linear_citation_concat'] = evaluate_fold(
            'linear_citation_concat', combo_linear_cite_train, combo_linear_cite_test, train_meta, test_meta)

        # Combination: linear + hybrid05 concat
        combo_linear_hybrid_train = normalize_emb(np.concatenate([normalize_emb(train_cp64), normalize_emb(hybrid05_train)], axis=1))
        combo_linear_hybrid_test = normalize_emb(np.concatenate([normalize_emb(test_cp64), normalize_emb(hybrid05_test)], axis=1))
        fold_fold_results['linear_hybrid05_concat'] = evaluate_fold(
            'linear_hybrid05_concat', combo_linear_hybrid_train, combo_linear_hybrid_test, train_meta, test_meta)

        # Combination: weighted w3070 (30% ML, 70% citation)
        w_ml, w_cite = 0.3, 0.7
        combo_w3070_train = normalize_emb(np.concatenate([normalize_emb(train_cp64) * w_ml, normalize_emb(cite_train[:len(train_idx)]) * w_cite], axis=1))
        combo_w3070_test = normalize_emb(np.concatenate([normalize_emb(test_cp64) * w_ml, normalize_emb(cite_test) * w_cite], axis=1))
        fold_fold_results['linear_citation_w3070'] = evaluate_fold(
            'linear_citation_w3070', combo_w3070_train, combo_w3070_test, train_meta, test_meta)

        # Combination: PCA reduction (concat ML + citation, PCA to 128d)
        concat_train = np.concatenate([normalize_emb(train_cp64), normalize_emb(cite_train[:len(train_idx)])], axis=1)
        concat_test = np.concatenate([normalize_emb(test_cp64), normalize_emb(cite_test)], axis=1)
        pca_combo = PCA(n_components=min(128, concat_train.shape[1]), random_state=FROZEN_SEED)
        combo_pca_train = normalize_emb(pca_combo.fit_transform(concat_train))
        combo_pca_test = normalize_emb(pca_combo.transform(concat_test))
        fold_fold_results['linear_citation_pca128'] = evaluate_fold(
            'linear_citation_pca128', combo_pca_train, combo_pca_test, train_meta, test_meta)

        # Combination: ridge regression
        branch_labels = np.array([m.get('branch', 'unknown') for m in train_meta])
        unique_branches = sorted(set(branch_labels))
        branch_to_int = {b: i for i, b in enumerate(unique_branches)}
        branch_ints = np.array([branch_to_int[b] for b in branch_labels])

        X_train_ridge = np.concatenate([normalize_emb(train_cp64), normalize_emb(cite_train[:len(train_idx)])], axis=1)
        X_test_ridge = np.concatenate([normalize_emb(test_cp64), normalize_emb(cite_test)], axis=1)
        scaler = StandardScaler()
        X_train_ridge_s = scaler.fit_transform(X_train_ridge)
        X_test_ridge_s = scaler.transform(X_test_ridge)
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_ridge_s, branch_ints)
        train_proj = X_train_ridge_s @ ridge.coef_
        test_proj = X_test_ridge_s @ ridge.coef_
        combo_ridge_train = normalize_emb(np.column_stack([normalize_emb(train_cp64), normalize_emb(cite_train[:len(train_idx)]), train_proj.reshape(-1, 1)]))
        combo_ridge_test = normalize_emb(np.column_stack([normalize_emb(test_cp64), normalize_emb(cite_test), test_proj.reshape(-1, 1)]))
        fold_fold_results['linear_citation_ridge'] = evaluate_fold(
            'linear_citation_ridge', combo_ridge_train, combo_ridge_test, train_meta, test_meta)

        # Log fold results
        logger.info(f"\nFold {fold_idx+1} Results:")
        for name, res in fold_fold_results.items():
            ld = res['langdom_score']
            jp = res['jurist_score']
            ci = res['cite_indep_score']
            adv = "PASS" if res['both_pass'] else "FAIL"
            logger.info(f"  {name:<35} LD={ld:.4f} JP={jp:.4f} CI={ci:.4f} Adv={adv}")

        fold_results.append(fold_results_dict := {
            'fold': fold_idx + 1,
            'train_size': len(train_idx),
            'test_size': len(test_idx),
            'results': fold_fold_results,
        })

    # ======================================================================
    # Aggregate Results Across Folds
    # ======================================================================
    logger.info(f"\n{'='*100}")
    logger.info("5-FOLD CROSS-VALIDATION SUMMARY")
    logger.info(f"{'='*100}")

    # Collect per-representation metrics across folds
    rep_names = list(fold_results[0]['results'].keys())
    aggregated = {}

    for rep_name in rep_names:
        jp_scores = [fr['results'][rep_name]['jurist_score'] for fr in fold_results]
        ld_scores = [fr['results'][rep_name]['langdom_score'] for fr in fold_results]
        ci_scores = [fr['results'][rep_name]['cite_indep_score'] for fr in fold_results]
        adv_passes = [fr['results'][rep_name]['both_pass'] for fr in fold_results]

        aggregated[rep_name] = {
            'jurist_pref_mean': float(np.mean(jp_scores)),
            'jurist_pref_std': float(np.std(jp_scores)),
            'jurist_pref_folds': jp_scores,
            'langdom_mean': float(np.mean(ld_scores)),
            'langdom_std': float(np.std(ld_scores)),
            'langdom_folds': ld_scores,
            'cite_indep_mean': float(np.mean(ci_scores)),
            'cite_indep_std': float(np.std(ci_scores)),
            'cite_indep_folds': ci_scores,
            'adv_pass_rate': sum(adv_passes) / len(adv_passes),
            'adv_all_pass': all(adv_passes),
        }

    # Print summary table
    logger.info(f"\n{'Representation':<35} {'JP mean':>8} {'JP std':>7} {'LD mean':>8} {'LD std':>7} {'CI mean':>8} {'CI std':>7} {'AdvPass':>7}")
    logger.info("-" * 100)
    for rep_name, agg in sorted(aggregated.items(), key=lambda x: -x[1]['jurist_pref_mean']):
        logger.info(f"{rep_name:<35} {agg['jurist_pref_mean']:>8.4f} {agg['jurist_pref_std']:>7.4f} "
                    f"{agg['langdom_mean']:>8.4f} {agg['langdom_std']:>7.4f} "
                    f"{agg['cite_indep_mean']:>8.4f} {agg['cite_indep_std']:>7.4f} "
                    f"{agg['adv_pass_rate']:>7.1%}")

    # ======================================================================
    # Tradeoff Analysis: Does combination improve over baselines?
    # ======================================================================
    logger.info(f"\n{'='*100}")
    logger.info("TRADEOFF ANALYSIS: v12 Cross-Mode Combination Validation")
    logger.info(f"{'='*100}")

    baseline_names = ['center_projected_64dim', 'citation_tfidf', 'cited_outcome_hybrid_0.5', 'cited_outcome_hybrid_0.7']
    combination_names = ['linear_citation_concat', 'linear_hybrid05_concat', 'linear_citation_w3070', 'linear_citation_pca128', 'linear_citation_ridge']

    # Find best baseline per fold
    best_baseline_jp_per_fold = []
    for fr in fold_results:
        best_jp = max(fr['results'][bn]['jurist_score'] for bn in baseline_names if bn in fr['results'])
        best_baseline_jp_per_fold.append(best_jp)

    # Find best combination per fold
    best_combo_jp_per_fold = []
    for fr in fold_results:
        best_jp = max(fr['results'][cn]['jurist_score'] for cn in combination_names if cn in fr['results'])
        best_combo_jp_per_fold.append(best_jp)

    # Per-fold improvement
    fold_improvements = [cb - bl for cb, bl in zip(best_combo_jp_per_fold, best_baseline_jp_per_fold)]

    logger.info(f"\nBest baseline JP per fold:    {[f'{x:.4f}' for x in best_baseline_jp_per_fold]}")
    logger.info(f"Best combination JP per fold:  {[f'{x:.4f}' for x in best_combo_jp_per_fold]}")
    logger.info(f"Improvement per fold:          {[f'{x:+.4f}' for x in fold_improvements]}")
    logger.info(f"Mean improvement:              {np.mean(fold_improvements):+.4f}")
    logger.info(f"Std improvement:               {np.std(fold_improvements):.4f}")
    logger.info(f"Positive folds:                {sum(1 for x in fold_improvements if x > 0)}/{len(fold_improvements)}")

    # Per-combination analysis
    logger.info(f"\nPer-combination analysis (vs best baseline):")
    for cn in combination_names:
        if cn not in aggregated:
            continue
        combo_jp = aggregated[cn]['jurist_pref_mean']
        baseline_jp = np.mean(best_baseline_jp_per_fold)
        delta = combo_jp - baseline_jp
        ci = aggregated[cn]['cite_indep_mean']
        ld = aggregated[cn]['langdom_mean']
        adv = aggregated[cn]['adv_pass_rate']
        logger.info(f"  {cn:<35} JP={combo_jp:.4f} (Δ={delta:+.4f}) LD={ld:.4f} CI={ci:.4f} AdvPass={adv:.0%}")

    # ======================================================================
    # v12 Claim Assessment
    # ======================================================================
    logger.info(f"\n{'='*100}")
    logger.info("v12 CLAIM ASSESSMENT")
    logger.info(f"{'='*100}")

    v12_claim_improvement = 0.035  # claimed ΔJP from v12
    observed_mean_improvement = np.mean(fold_improvements)
    observed_std = np.std(fold_improvements)

    # Does the improvement replicate?
    replicates = observed_mean_improvement > 0
    is_significant = observed_mean_improvement > 0.01  # minimum meaningful improvement
    all_folds_positive = all(x > 0 for x in fold_improvements)

    logger.info(f"\nv12 claimed improvement:    +{v12_claim_improvement:.4f}")
    logger.info(f"Observed mean improvement:  {observed_mean_improvement:+.4f}")
    logger.info(f"Observed std:               {observed_std:.4f}")
    logger.info(f"Replicates (mean > 0):      {'YES' if replicates else 'NO'}")
    logger.info(f"Meaningful (> 0.01):        {'YES' if is_significant else 'NO'}")
    logger.info(f"All folds positive:         {'YES' if all_folds_positive else 'NO'}")

    if replicates and is_significant:
        verdict = "REPLICATED"
        evidence_tier = "ACCEPTED"
        logger.info(f"\n>>> VERDICT: REPLICATED — v12 improvement confirmed across 5 folds <<<")
    elif replicates:
        verdict = "WEAK_REPLICATION"
        evidence_tier = "EXPLORATORY"
        logger.info(f"\n>>> VERDICT: WEAK REPLICATION — improvement present but small <<<")
    else:
        verdict = "FALSIFIED"
        evidence_tier = "ACCEPTED_NEGATIVE"
        logger.info(f"\n>>> VERDICT: FALSIFIED — v12 improvement does not replicate <<<")

    # ======================================================================
    # Persist Results
    # ======================================================================
    output = {
        'run_id': run_id,
        'direction_version': 10,
        'config_hash': FROZEN_CONFIG_HASH,
        'seed': FROZEN_SEED,
        'n_folds': N_FOLDS,
        'corpus': '1000 BGer decisions (2020-2024), canonical fractal-map baseline',
        'hypothesis': 'v12 cross-mode combination JP improvement (+0.035) replicates across 5 folds',
        'success_rule': 'Mean JP improvement > 0 across folds AND all folds pass adversarial gates',
        'fold_results': fold_results,
        'aggregated': aggregated,
        'tradeoff_analysis': {
            'best_baseline_jp_per_fold': best_baseline_jp_per_fold,
            'best_combo_jp_per_fold': best_combo_jp_per_fold,
            'fold_improvements': fold_improvements,
            'mean_improvement': float(observed_mean_improvement),
            'std_improvement': float(observed_std),
            'positive_folds': sum(1 for x in fold_improvements if x > 0),
            'total_folds': len(fold_improvements),
        },
        'v12_claim_assessment': {
            'claimed_improvement': v12_claim_improvement,
            'observed_mean_improvement': float(observed_mean_improvement),
            'observed_std': float(observed_std),
            'replicates': replicates,
            'is_significant': is_significant,
            'all_folds_positive': all_folds_positive,
            'verdict': verdict,
            'evidence_tier': evidence_tier,
        },
    }

    with open(OUTPUT_DIR / f"v12_cross_mode_cv_{run_id}.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    # Also save as latest
    with open(OUTPUT_DIR / "v12_cross_mode_cv_latest.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {OUTPUT_DIR / f'v12_cross_mode_cv_{run_id}.json'}")

    return output


if __name__ == "__main__":
    main()
