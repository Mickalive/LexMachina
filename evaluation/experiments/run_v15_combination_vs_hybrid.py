#!/usr/bin/env python3
"""
Evaluation v15: Combination vs Best Zero-Shot Hybrid — Head-to-Head on Canonical Harness v3

HYPOTHESIS (frozen before observation): The v12/v13/v14 cross-mode combinations
(linear_citation_concat, linear_hybrid05_concat, linear_citation_ridge) do NOT
beat the best zero-shot hybrid (cited_decisions_tfidf_outcome_hybrid_0.5) on the
canonical frozen harness v3 adversarial benchmarks.

If ANY combination beats cited_decisions_tfidf_outcome_hybrid_0.5 by > 0.02 on
JuristPref while passing both adversarial gates, the combination is product-relevant.
If no combination beats it, the zero-shot hybrid remains dominant and the combination
finding is architecturally interesting but NOT product-critical.

FROZEN BEFORE OBSERVATION:
- Corpus: 1200 BGer decisions (expanded slice), canonical frozen harness v3
- Config hash: 4323f833fa72366a (canonical harness v3)
- Seed: 42
- Adversarial gates: LangDom < 0.85, JuristPref > 0.5
- Success rule: combination beats cited_decisions_tfidf_outcome_hybrid_0.5 on JP by > 0.02

Product decision unlocked: Whether to integrate linear_citation_concat as a new
product map mode, or keep cited_decisions_tfidf_outcome_hybrid_0.5 as the best
production representation.
"""

import json
import time
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any
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
# FROZEN PARAMETERS
# ======================================================================
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"
SUCCESS_RULE = {"min_jp_delta_vs_hybrid05": 0.02}

# ======================================================================
# Paths
# ======================================================================
CORPUS_PATH = Path("evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
OUTPUT_DIR = Path("results/evaluation/v15_combination_vs_hybrid")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# Adversarial benchmark thresholds (canonical v3 harness)
# ======================================================================
LANGDOM_THRESHOLD = 0.85
JURIST_THRESHOLD = 0.5
LANGDOM_K = 20
JURIST_K = 10

# ======================================================================
# Chamber-to-branch mapping
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
    corpus = []
    with open(CORPUS_PATH) as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from canonical corpus")
    return corpus

def load_metadata():
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    logger.info(f"Loaded {len(metadata)} baseline metadata entries")
    return metadata

def load_embeddings_64():
    embeddings = np.load(EMBEDDINGS_64_PATH)
    logger.info(f"Loaded 64-dim embeddings: shape={embeddings.shape}")
    return embeddings

def align_corpus_to_metadata(corpus, metadata):
    meta_ids = {m['decision_id'] for m in metadata}
    aligned = []
    for d in corpus:
        if d['decision_id'] in meta_ids:
            aligned.append(d)
    logger.info(f"Aligned {len(aligned)} corpus entries to metadata")
    return aligned


# ======================================================================
# Feature Construction (FULL corpus, no train/test split)
# ======================================================================
def normalize_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n

def build_citation_tfidf_full(decisions, svd_dim=128):
    """Build cited_decisions TF-IDF features on full corpus."""
    texts = []
    has_content = []
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

def build_outcome_tfidf_full(decisions, svd_dim=2):
    """Build outcome TF-IDF features on full corpus."""
    texts = []
    has_content = []
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

def build_cited_outcome_hybrid(cites_emb, outcome_emb, alpha=0.5):
    """Build cited_outcome_hybrid: concat(alpha*cites, (1-alpha)*outcome)."""
    hybrid = np.concatenate([normalize_emb(cites_emb) * alpha, normalize_emb(outcome_emb) * (1 - alpha)], axis=1)
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return hybrid / norms


# ======================================================================
# Adversarial Benchmarks (canonical v3 harness)
# ======================================================================
def adversarial_language_dominance(embeddings, metadata, k=LANGDOM_K):
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
        'status': 'PASS' if mean_dominance < LANGDOM_THRESHOLD else 'FAIL',
    }

def simulate_pairwise_preference(embeddings, branches, languages, k=JURIST_K):
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
        "jurist_would_succeed_rate": round(legal_neighbor_rate, 4),
        "status": "PASS" if legal_neighbor_rate > JURIST_THRESHOLD else "FAIL",
    }

def evaluate_representation(name, embeddings, metadata, branches, languages):
    """Full adversarial evaluation of a representation."""
    norm = normalize_emb(embeddings)
    lang_dom = adversarial_language_dominance(norm, metadata)
    jurist_pref = simulate_pairwise_preference(norm, branches, languages)

    both_pass = lang_dom['status'] == 'PASS' and jurist_pref['status'] == 'PASS'

    return {
        'name': name,
        'langdom': lang_dom['mean_language_dominance'],
        'langdom_pass': lang_dom['status'] == 'PASS',
        'jurist_pref': jurist_pref['jurist_would_succeed_rate'],
        'jurist_pass': jurist_pref['status'] == 'PASS',
        'both_pass': both_pass,
    }


# ======================================================================
# Main
# ======================================================================
def main():
    run_id = f"eval_v15_{int(time.time())}"
    logger.info(f"Starting v15 combination vs hybrid head-to-head: {run_id}")
    logger.info(f"Config: seed={FROZEN_SEED}, config_hash={FROZEN_CONFIG_HASH}")

    # 1. Load data
    corpus = load_corpus()
    metadata = load_metadata()
    cp64 = load_embeddings_64()
    corpus_aligned = align_corpus_to_metadata(corpus, metadata)

    # 2. Enrich metadata
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
                break
        if 'branch' not in em:
            em['branch'] = assign_branch(em.get('chamber', ''))
        if 'language' not in em:
            em['language'] = 'de'
        enriched_meta.append(em)

    branches = np.array([m.get('branch', 'unknown') for m in enriched_meta])
    languages = np.array([m.get('language', 'unknown') for m in enriched_meta])

    # 3. Build features on FULL corpus
    logger.info("\nBuilding features on full 1200 corpus...")
    citation_emb, cite_has = build_citation_tfidf_full(corpus_aligned, svd_dim=128)
    outcome_emb, outcome_has = build_outcome_tfidf_full(corpus_aligned, svd_dim=2)

    # 4. Build representations
    representations = {}

    # Zero-shot baselines
    representations['center_projected_64dim'] = cp64
    representations['cited_decisions_tfidf'] = citation_emb
    representations['cited_outcome_hybrid_0.5'] = build_cited_outcome_hybrid(citation_emb, outcome_emb, alpha=0.5)
    representations['cited_outcome_hybrid_0.7'] = build_cited_outcome_hybrid(citation_emb, outcome_emb, alpha=0.7)

    # Combinations (concatenation-based)
    representations['linear_citation_concat'] = normalize_emb(
        np.concatenate([normalize_emb(cp64), normalize_emb(citation_emb)], axis=1))

    representations['linear_hybrid05_concat'] = normalize_emb(
        np.concatenate([normalize_emb(cp64), normalize_emb(representations['cited_outcome_hybrid_0.5'])], axis=1))

    representations['linear_hybrid07_concat'] = normalize_emb(
        np.concatenate([normalize_emb(cp64), normalize_emb(representations['cited_outcome_hybrid_0.7'])], axis=1))

    # Weighted combinations
    w_ml, w_cite = 0.3, 0.7
    representations['linear_citation_w3070'] = normalize_emb(
        np.concatenate([normalize_emb(cp64) * w_ml, normalize_emb(citation_emb) * w_cite], axis=1))

    # Ridge regression combination
    branch_labels = branches
    unique_branches = sorted(set(branch_labels))
    branch_to_int = {b: i for i, b in enumerate(unique_branches)}
    branch_ints = np.array([branch_to_int[b] for b in branch_labels])

    X_ridge = np.concatenate([normalize_emb(cp64), normalize_emb(citation_emb)], axis=1)
    scaler = StandardScaler()
    X_ridge_s = scaler.fit_transform(X_ridge)
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_ridge_s, branch_ints)
    ridge_proj = X_ridge_s @ ridge.coef_

    representations['linear_citation_ridge'] = normalize_emb(
        np.column_stack([normalize_emb(cp64), normalize_emb(citation_emb), ridge_proj.reshape(-1, 1)]))

    # PCA reduction combination
    concat_all = np.concatenate([normalize_emb(cp64), normalize_emb(citation_emb)], axis=1)
    pca_combo = PCA(n_components=min(128, concat_all.shape[1]), random_state=FROZEN_SEED)
    representations['linear_citation_pca128'] = normalize_emb(pca_combo.fit_transform(concat_all))

    # 5. Evaluate all representations
    logger.info("\nEvaluating all representations on canonical adversarial benchmarks...")
    logger.info(f"{'Representation':<40} {'LangDom':>8} {'JuristPref':>10} {'BothPass':>8}")
    logger.info("-" * 70)

    results = []
    for name, emb in representations.items():
        res = evaluate_representation(name, emb, enriched_meta, branches, languages)
        results.append(res)
        logger.info(f"{name:<40} {res['langdom']:>8.4f} {res['jurist_pref']:>10.4f} {'PASS' if res['both_pass'] else 'FAIL':>8}")

    # 6. Identify best zero-shot hybrid
    hybrid_results = [r for r in results if r['name'].startswith('cited_outcome_hybrid')]
    best_hybrid = max(hybrid_results, key=lambda x: x['jurist_pref'])
    logger.info(f"\nBest zero-shot hybrid: {best_hybrid['name']} (JP={best_hybrid['jurist_pref']:.4f})")

    # 7. Compare combinations against best hybrid
    combo_results = [r for r in results if r['name'].startswith('linear_')]
    logger.info(f"\nCombination comparison against {best_hybrid['name']}:")
    logger.info(f"{'Combination':<40} {'JP':>8} {'ΔJP':>8} {'Beats?':>8}")
    logger.info("-" * 70)

    beats_hybrid = []
    for r in combo_results:
        delta_jp = r['jurist_pref'] - best_hybrid['jurist_pref']
        beats = delta_jp > SUCCESS_RULE["min_jp_delta_vs_hybrid05"]
        if beats:
            beats_hybrid.append(r)
        logger.info(f"{r['name']:<40} {r['jurist_pref']:>8.4f} {delta_jp:>+8.4f} {'YES' if beats else 'NO':>8}")

    # 8. Determine verdict
    if beats_hybrid:
        best_combo = max(beats_hybrid, key=lambda x: x['jurist_pref'])
        verdict = "COMBINATION_BEATS_HYBRID"
        recommendation = "INTEGRATE_BEST_COMBINATION"
        logger.info(f"\n>>> VERDICT: {verdict} — {best_combo['name']} (JP={best_combo['jurist_pref']:.4f}) beats {best_hybrid['name']} (JP={best_hybrid['jurist_pref']:.4f}) by {best_combo['jurist_pref'] - best_hybrid['jurist_pref']:+.4f} <<<")
    else:
        verdict = "HYBRID_REMAINS_DOMINANT"
        recommendation = "KEEP_HYBRID_AS_DEFAULT"
        logger.info(f"\n>>> VERDICT: {verdict} — No combination beats {best_hybrid['name']} (JP={best_hybrid['jurist_pref']:.4f}) <<<")

    # 9. Persist results
    output = {
        'run_id': run_id,
        'direction_version': 11,
        'config_hash': FROZEN_CONFIG_HASH,
        'seed': FROZEN_SEED,
        'corpus': '1200 BGer decisions (expanded slice), canonical frozen harness v3',
        'hypothesis': 'Combinations beat best zero-shot hybrid on canonical adversarial benchmarks',
        'success_rule': f'JP improvement > {SUCCESS_RULE["min_jp_delta_vs_hybrid05"]} over {best_hybrid["name"]}',
        'frozen_before_observation': True,
        'results': results,
        'best_zero_shot_hybrid': best_hybrid,
        'combinations_beating_hybrid': [r['name'] for r in beats_hybrid],
        'verdict': verdict,
        'recommendation': recommendation,
        'product_decision': {
            'integrate_combination': bool(beats_hybrid),
            'best_combination': best_combo['name'] if beats_hybrid else None,
            'best_combination_jp': best_combo['jurist_pref'] if beats_hybrid else None,
            'hybrid_jp': best_hybrid['jurist_pref'],
            'hybrid_name': best_hybrid['name'],
        },
    }

    with open(OUTPUT_DIR / f"v15_combination_vs_hybrid_{run_id}.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    with open(OUTPUT_DIR / "v15_combination_vs_hybrid_latest.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {OUTPUT_DIR / f'v15_combination_vs_hybrid_{run_id}.json'}")
    return output


if __name__ == "__main__":
    main()
