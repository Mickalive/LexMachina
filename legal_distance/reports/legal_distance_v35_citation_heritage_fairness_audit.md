# Legal-Distance v35 — Citation-Heritage Fairness Audit

**Lane:** legal-distance · **Direction version:** 35 · **GitHub run:** 38039706350
**Date:** 2026-10-10 · **Evidence tier:** REPRODUCED (pending audit)
**Frozen spec:** `legal_distance/results/citation_heritage_fairness_audit_v35/frozen_spec.json`,
`legal_distance/results/citation_heritage_fairness_audit_v35/frozen_spec_relation_decomposition.json`
(registered before outcome inspection)

## 1. Claim under audit

The accepted legal-distance state (`state/legal-distance.json`, tier ACCEPTED) asserts:

> "Dense multilingual-e5 embeddings RECOVER citation heritage at scale (AUC 0.79–0.85 at 21–22yr, 137k–144k; AUC 0.767 at 24yr, 158k with 730 pairs), BETTER than TF-IDF citation-based (AUC 0.71–0.74) and much better than TF-IDF text-based (AUC 0.50–0.63)."

The accepted evaluation lane (`/tmp/lex_accepted/evaluation/state/evaluation.json`) had already
**retracted** a dense citation-heritage claim and froze the TF-IDF citation baseline
(`citation_heritage_auc = 0.7296`). This audit resolves the cross-lane contradiction.

## 2. Frozen falsification test

Success rule (pre-registered): dense must beat the best TF-IDF citation representation by
**≥ +0.02 AUC** on an **identical, matched, self-pair-free** pair set. Otherwise the claim is
FALSIFIED. Threats pre-registered: T1 self-pairs `(d,d)`; T2 pair-set mismatch (dense and
TF-IDF evaluated on different positive sets); T3 subset selection.

Inputs (all mounted artifacts, no new data generation):
- Dense: `legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_{2000..2023}.npy`
  (+ `metadata_{year}.json`) — 158,427 decisions assembled.
- TF-IDF: `evaluation/results/174k/embeddings/{cited_decisions_tfidf*,}.npy` (175,440 × 128).
- Metadata/ID order: `evaluation/data/174k/metadata_174k.json` (173,963).
- Pairs (ORIG): `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` (1020 pos/neg).
- Pairs (FULL, graph-derived, accepted lane):
  `.../citation_pairs_174k_full.json` (137,314 pos/neg).
- Graph: `.../citation_graph_174k.json` (5031 sources, 7799 edges, 918 targets).

## 3. Results

### 3.1 The published gap is a pair-set artifact (T2), not a capability difference

As published, dense was scored on the **730** pairs where a dense checkpoint existed, while
TF-IDF was scored on all **1020** pairs — *different positive and negative sets*. Reproduction:

| pair set | representation | AUC | n_pos |
|---|---|---:|---:|
| ORIG all 1020, with self | cited_decisions TF-IDF | 0.7426 | 1020 |
| ORIG dense-available 730, with self | dense_cp64 | 0.7667 | 730 |
| **identical 730, with self** | cited_decisions TF-IDF | **0.7642** | 730 |
| **identical 730, with self** | dense_cp64 | **0.7667** | 730 |

The apparent +0.024 gap collapses to **+0.0025** once both are scored on the same 730 pairs.

### 3.2 Self-pairs (T1) inflate both representations by ~0.045 AUC

`(d,d)` positives (cos = 1.0) are present in 174/1020 ORIG positives and 601 FULL positives.

| representation | AUC with self | AUC no self | Δ |
|---|---:|---:|---:|
| dense_raw_768 | 0.7844 | 0.7402 | −0.044 |
| dense_cp_768 | 0.7696 | 0.7225 | −0.047 |
| dense_cp64 | 0.7667 | 0.7189 | −0.048 |
| cited_decisions TF-IDF | 0.7426 | 0.6967 | −0.046 |

Self-pairs inflate every representation almost equally, so they do not create the dense lead — but
they do inflate the absolute numbers used in the accepted state.

### 3.3 PRIMARY VERDICT — FALSIFIED on the fair matched set

On the identical matched self-pair-free set (606 pos / 834 neg):

| representation | AUC |
|---|---:|
| dense_raw_768 | 0.7402 |
| dense_cp_768 | 0.7225 |
| dense_cp64 | 0.7189 |
| cited_decisions TF-IDF | **0.7159** |
| cited_decisions TF-IDF outcome_hybrid 0.7 | 0.6906 |

Margin = **+0.0030** (threshold +0.02). Bootstrap (2000 resamples, seed 42):
95% CI **[−0.0343, +0.0366]**, mean +0.0028. → **FALSIFIED.** Dense is statistically
indistinguishable from the TF-IDF citation representation on this relation.

### 3.4 Relation decomposition — what each representation actually encodes

The FULL graph admits clean relation sets. Results (seed 42, matched negatives):

| positive relation | dense_cp64 | cited_decisions TF-IDF (128) | citation Jaccard (full-dim) |
|---|---:|---:|---:|
| DIRECT `A→B` (7198) | 0.6924 | 0.6054 | **0.7735** |
| SHARED1 (≥1 shared target) | 0.9248 | 0.6364 | **1.0000** |
| SHARED2 (≥2, evaluation lane's criterion) | 0.9698 | 0.6765 | **1.0000** |

- A **faithful citation representation** (full-dimensional binary citation Jaccard) beats dense on
  DIRECT (0.7735 vs 0.6924) and is an oracle on shared-precedent relations. The benchmark for a
  shared-citation relation is nearly circular for any representation with access to citations.
- The **production TF-IDF citation representation is a poor citation encoder (0.60–0.68)** because
  its 128-dim SVD reduction destroys the sparse exact-match citation signal. This — not dense
  superiority — is why dense "wins" against it on the FULL set (0.9176 vs 0.6489).
- Dense embeddings **do** carry genuine citation-relatedness signal (0.69 DIRECT, 0.92–0.97
  shared), far above the 0.50 chance level. The capability is real; the *superiority over a faithful
  citation representation* is not.

## 4. Decision-relevant conclusion

1. **RETRACT** the specific comparison "dense (0.79–0.85) BETTER than TF-IDF citation-based
   (0.71–0.74)". On identical pairs dense_cp64 (0.7189) ≈ cited_decisions TF-IDF (0.7159),
   Δ = +0.003, 95% CI [−0.034, +0.037]. The accepted numbers mixed pair sets (T2) and included
   self-pairs (T1).
2. **The citation-heritage view does not require dense embeddings.** For corpora with resolved
   citations, the citation graph (or a full-dimensional citation representation) is the correct,
   stronger, cheaper baseline (Jaccard 0.77 DIRECT / 1.00 shared).
3. **Dense embeddings remain justified as a text-only proxy** for citation-heritage when citation
   metadata is absent/unresolved (user-imported corpora), where a citation representation cannot be
   built. This is the defensible product role; it is complementary, not superior.
4. This resolves the cross-lane contradiction **in favour of the evaluation lane's retraction.**
   The legal-distance state's ACCEPTED citation-heritage claim was not reproducible as stated.

## 5. Provenance & reproducibility

- `legal_distance/experiments/citation_heritage_fairness_audit_v35.py` → `fairness_audit_results.json`
- `legal_distance/experiments/citation_heritage_relation_decomposition_v35.py` → `relation_decomposition_results.json`
- `tests/legal_distance/test_citation_heritage_fairness_v35.py` — **18/18 pass**
- Deterministic: seed 42; bootstrap 2000; pure numpy (no sklearn/scipy).

## 6. Negative result preserved

Dense embeddings **win decisively against the 128-dim TF-IDF citation representation on the FULL
shared-citation relation (0.9176 vs 0.6489)**. This is recorded as a real (but representation-
conditional) positive result and is the source of the original over-claim; it does **not** overturn
§3.3 because that comparison uses a lossy citation baseline and a relation that is circular for
citation-based representations.
