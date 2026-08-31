#!/usr/bin/env python3
"""
Evaluation v15b: 5-Fold CV — Combination vs Best Zero-Shot Hybrid

Follow-up to v15: Verify the finding with 5-fold cross-validation for stability.
Same frozen parameters as v15.
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
from sklearn.model_selection import KFold
import random
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
N_FOLDS = 5
LANGDOM_THRESHOLD = 0.85
JURIST_THRESHOLD = 0.5
LANGDOM_K = 20
JURIST_K = 10

CORPUS_PATH = Path("evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
OUTPUT_DIR = Path("results/evaluation/v15_combination_vs_hybrid")
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

def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n

def build_citation_tfidf(decisions, svd_dim=128):
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
    return result, set(has_content)

def build_citation_tfidf_transform(decisions, vectorizer, svd, svd_dim=128):
    texts, has_content = [], []
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
    return result, set(has_content)

def build_outcome_tfidf_transform(decisions, vectorizer, svd, svd_dim=2):
    texts, has_content = [], []
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
    hybrid = np.concatenate([normalize_emb(cites_emb) * alpha, normalize_emb(outcome_emb) * (1 - alpha)], axis=1)
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return hybrid / norms

def adversarial_language_dominance(embeddings, metadata, k=LANGDOM_K):
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
    return {'mean_language_dominance': mean_dominance, 'status': 'PASS' if mean_dominance < LANGDOM_THRESHOLD else 'FAIL'}

def simulate_pairwise_preference(embeddings, branches, languages, k=JURIST_K):
    n = len(branches)
    nn = NearestNeighbors(n_neighbors=min(k+1, n), metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    legal_relevant_count = 0
    both_count = 0
    for i in range(n):
        branch_i, lang_i = branches[i], languages[i]
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        has_legal_relevant = False
        has_language_artifact = False
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i: has_legal_relevant = True
            if nb != branch_i and nl == lang_i: has_language_artifact = True
        if has_legal_relevant and has_language_artifact: both_count += 1
        elif has_legal_relevant: legal_relevant_count += 1
    jurist_correct = legal_relevant_count + both_count
    legal_neighbor_rate = jurist_correct / n
    return {'jurist_would_succeed_rate': round(legal_neighbor_rate, 4), 'status': 'PASS' if legal_neighbor_rate > JURIST_THRESHOLD else 'FAIL'}

def evaluate_fold(name, train_emb, test_emb, train_meta, test_meta):
    train_branches = np.array([m.get('branch', 'unknown') for m in train_meta])
    train_langs = np.array([m.get('language', 'unknown') for m in train_meta])
    test_branches = np.array([m.get('branch', 'unknown') for m in test_meta])
    test_langs = np.array([m.get('language', 'unknown') for m in test_meta])
    lang_dom = adversarial_language_dominance(normalize_emb(test_emb), test_meta)
    jurist_pref = simulate_pairwise_preference(normalize_emb(test_emb), test_branches, test_langs)
    both_pass = lang_dom['status'] == 'PASS' and jurist_pref['status'] == 'PASS'
    return {
        'langdom': lang_dom['mean_language_dominance'],
        'jurist_pref': jurist_pref['jurist_would_succeed_rate'],
        'both_pass': both_pass,
    }

def main():
    run_id = f"eval_v15b_cv_{int(time.time())}"
    logger.info(f"Starting v15b 5-fold CV comparison: {run_id}")

    corpus = []
    with open(CORPUS_PATH) as f:
        for line in f: corpus.append(json.loads(line))
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip(): metadata.append(json.loads(line))
    cp64 = np.load(EMBEDDINGS_64_PATH)

    meta_ids = {m['decision_id'] for m in metadata}
    corpus_aligned = [d for d in corpus if d['decision_id'] in meta_ids]

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

    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=FROZEN_SEED)
    indices = np.arange(len(metadata))
    fold_results = []

    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(indices)):
        logger.info(f"\nFOLD {fold_idx+1}/{N_FOLDS} (train={len(train_idx)}, test={len(test_idx)})")

        train_meta = [enriched_meta[i] for i in train_idx]
        test_meta = [enriched_meta[i] for i in test_idx]
        train_cp64, test_cp64 = cp64[train_idx], cp64[test_idx]

        # Build citation features (train-fitted)
        cite_train_raw, _ = build_citation_tfidf([corpus_aligned[i] for i in train_idx])
        train_texts = []
        for d in [corpus_aligned[i] for i in train_idx]:
            cites = d.get('cited_decisions', [])
            text = " ".join(str(c) for c in cites) if cites else ""
            if text.strip(): train_texts.append(text)
        if len(train_texts) >= 5:
            vec = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
            tfidf_train = vec.fit_transform(train_texts)
            svd = TruncatedSVD(n_components=min(128, tfidf_train.shape[1]-1), random_state=FROZEN_SEED)
            svd.fit(tfidf_train)
            cite_test = build_citation_tfidf_transform([corpus_aligned[i] for i in test_idx], vec, svd)
        else:
            cite_test = np.zeros((len(test_idx), 128))

        # Build outcome features (train-fitted)
        outcome_texts = []
        for d in [corpus_aligned[i] for i in train_idx]:
            outcome = d.get('outcome', '')
            if outcome and outcome != 'null': outcome_texts.append(str(outcome))
        if len(outcome_texts) >= 5:
            ovec = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
            otfidf = ovec.fit_transform(outcome_texts)
            osvd = TruncatedSVD(n_components=min(2, otfidf.shape[1]-1), random_state=FROZEN_SEED)
            osvd.fit(otfidf)
            outcome_test = build_outcome_tfidf_transform([corpus_aligned[i] for i in test_idx], ovec, osvd)
        else:
            outcome_test = np.zeros((len(test_idx), 2))

        # Build hybrid features
        hybrid05_train = build_cited_outcome_hybrid(cite_train_raw[:len(train_idx)], np.zeros((len(train_idx), 2)), alpha=0.5)
        hybrid05_test = build_cited_outcome_hybrid(cite_test, outcome_test, alpha=0.5)
        hybrid07_train = build_cited_outcome_hybrid(cite_train_raw[:len(train_idx)], np.zeros((len(train_idx), 2)), alpha=0.7)
        hybrid07_test = build_cited_outcome_hybrid(cite_test, outcome_test, alpha=0.7)

        fold_fold = {}
        # Zero-shot baselines
        fold_fold['center_projected_64dim'] = evaluate_fold('cp64', train_cp64, test_cp64, train_meta, test_meta)
        fold_fold['cited_outcome_hybrid_0.5'] = evaluate_fold('hybrid05', hybrid05_train, hybrid05_test, train_meta, test_meta)
        fold_fold['cited_outcome_hybrid_0.7'] = evaluate_fold('hybrid07', hybrid07_train, hybrid07_test, train_meta, test_meta)

        # Combinations
        combo_lc = normalize_emb(np.concatenate([normalize_emb(train_cp64), normalize_emb(cite_train_raw[:len(train_idx)])], axis=1))
        combo_lc_test = normalize_emb(np.concatenate([normalize_emb(test_cp64), normalize_emb(cite_test)], axis=1))
        fold_fold['linear_citation_concat'] = evaluate_fold('lc_concat', combo_lc, combo_lc_test, train_meta, test_meta)

        combo_lh = normalize_emb(np.concatenate([normalize_emb(train_cp64), normalize_emb(hybrid05_train)], axis=1))
        combo_lh_test = normalize_emb(np.concatenate([normalize_emb(test_cp64), normalize_emb(hybrid05_test)], axis=1))
        fold_fold['linear_hybrid05_concat'] = evaluate_fold('lh_concat', combo_lh, combo_lh_test, train_meta, test_meta)

        w_ml, w_cite = 0.3, 0.7
        combo_w = normalize_emb(np.concatenate([normalize_emb(train_cp64)*w_ml, normalize_emb(cite_train_raw[:len(train_idx)])*w_cite], axis=1))
        combo_w_test = normalize_emb(np.concatenate([normalize_emb(test_cp64)*w_ml, normalize_emb(cite_test)*w_cite], axis=1))
        fold_fold['linear_citation_w3070'] = evaluate_fold('lc_w3070', combo_w, combo_w_test, train_meta, test_meta)

        # Ridge
        branch_labels = np.array([m.get('branch', 'unknown') for m in train_meta])
        unique_branches = sorted(set(branch_labels))
        b2i = {b: i for i, b in enumerate(unique_branches)}
        branch_ints = np.array([b2i[b] for b in branch_labels])
        X_r = np.concatenate([normalize_emb(train_cp64), normalize_emb(cite_train_raw[:len(train_idx)])], axis=1)
        X_rt = np.concatenate([normalize_emb(test_cp64), normalize_emb(cite_test)], axis=1)
        scaler = StandardScaler()
        X_rs = scaler.fit_transform(X_r)
        X_rts = scaler.transform(X_rt)
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_rs, branch_ints)
        train_proj = X_rs @ ridge.coef_
        test_proj = X_rts @ ridge.coef_
        combo_r = normalize_emb(np.column_stack([normalize_emb(train_cp64), normalize_emb(cite_train_raw[:len(train_idx)]), train_proj.reshape(-1,1)]))
        combo_rt = normalize_emb(np.column_stack([normalize_emb(test_cp64), normalize_emb(cite_test), test_proj.reshape(-1,1)]))
        fold_fold['linear_citation_ridge'] = evaluate_fold('lc_ridge', combo_r, combo_rt, train_meta, test_meta)

        fold_results.append({'fold': fold_idx+1, 'results': fold_fold})

    # Aggregate
    rep_names = list(fold_results[0]['results'].keys())
    aggregated = {}
    for name in rep_names:
        jp = [fr['results'][name]['jurist_pref'] for fr in fold_results]
        ld = [fr['results'][name]['langdom'] for fr in fold_results]
        ap = [fr['results'][name]['both_pass'] for fr in fold_results]
        aggregated[name] = {
            'jp_mean': float(np.mean(jp)), 'jp_std': float(np.std(jp)), 'jp_folds': jp,
            'ld_mean': float(np.mean(ld)), 'ld_folds': ld,
            'adv_pass_rate': sum(ap)/len(ap), 'adv_all_pass': all(ap),
        }

    logger.info(f"\n{'='*80}")
    logger.info("5-FOLD CV RESULTS — Combination vs Best Zero-Shot Hybrid")
    logger.info(f"{'='*80}")
    logger.info(f"{'Representation':<35} {'JP mean':>8} {'JP std':>7} {'LD mean':>8} {'AdvPass':>7}")
    logger.info("-" * 70)
    for name, agg in sorted(aggregated.items(), key=lambda x: -x[1]['jp_mean']):
        logger.info(f"{name:<35} {agg['jp_mean']:>8.4f} {agg['jp_std']:>7.4f} {agg['ld_mean']:>8.4f} {agg['adv_pass_rate']:>7.0%}")

    best_hybrid_name = 'cited_outcome_hybrid_0.5'
    best_hybrid_jp = aggregated[best_hybrid_name]['jp_mean']

    logger.info(f"\nComparison against {best_hybrid_name} (JP={best_hybrid_jp:.4f}):")
    combo_names = [n for n in rep_names if n.startswith('linear_')]
    for cn in sorted(combo_names, key=lambda x: -aggregated[x]['jp_mean']):
        delta = aggregated[cn]['jp_mean'] - best_hybrid_jp
        logger.info(f"  {cn:<35} ΔJP={delta:+.4f} {'BEATS' if delta > 0.02 else 'does not beat'}")

    beats = [cn for cn in combo_names if aggregated[cn]['jp_mean'] - best_hybrid_jp > 0.02]
    verdict = "COMBINATION_BEATS_HYBRID" if beats else "HYBRID_REMAINS_DOMINANT"

    output = {
        'run_id': run_id,
        'direction_version': 11,
        'config_hash': FROZEN_CONFIG_HASH,
        'seed': FROZEN_SEED,
        'n_folds': N_FOLDS,
        'corpus': '1200 BGer decisions, canonical frozen harness v3',
        'hypothesis': 'Combinations beat best zero-shot hybrid on 5-fold CV',
        'success_rule': f'JP improvement > 0.02 over {best_hybrid_name}',
        'frozen_before_observation': True,
        'aggregated': aggregated,
        'combinations_beating_hybrid': beats,
        'verdict': verdict,
    }

    with open(OUTPUT_DIR / f"v15b_cv_{run_id}.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)
    with open(OUTPUT_DIR / "v15b_cv_latest.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nVerdict: {verdict}")
    logger.info(f"Results saved to {OUTPUT_DIR}")
    return output

if __name__ == "__main__":
    main()
