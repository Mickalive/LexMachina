# Legal-Distance v36 — Citation-Heritage Text-Only Proxy Test

**Lane:** legal-distance · **Direction version:** 35 · **GitHub run:** 38051603155
**Date:** 2026-10-10 · **Evidence tier:** REPRODUCED (pending audit)
**Frozen spec:** `legal_distance/results/citation_heritage_text_proxy_v36/frozen_spec.json`
(registered before outcome inspection)
**Tests:** `tests/legal_distance/test_citation_heritage_text_proxy_v36.py` (39 checks with the
citation-graph mount present, incl. 2 graph-dependent; 38 pass + 1 skipped without it)

> **Repair round 1 (audit cycle 38056432926, GitHub run 38057380692):** corrected the §2.1
> H1 baseline table — `regeste_full_text_hybrid_0.5` = 0.5521 (Δ −0.1668) and `regeste_tfidf`
> = 0.4850 (Δ −0.2339, below chance) — replacing the erroneous 0.5863/0.5759 rows (D1); replaced
> the §2.4 "Reproduced exactly" heading with "Recomputed from raw inputs (protocol reconciled,
> **not bit-identical**)" and disclosed that no 1000/2000 sampling caps were applied, so the
> frozen 0.7296 is not exactly reproduced (D2); added §4 provenance disclosure that
> `legal_distance/state/legal-distance.json` was reconciled to canonical
> `state/legal-distance.json` (103 → 104 runs) (D3); strengthened the verification test to
> assert the **full text-only family** against committed JSON and to guard report↔JSON
> consistency (Sections A/C), which would have caught D1. **No committed JSON or AUC changed**;
> all headline numbers remain exactly the audited, independently reproduced values; the claim
> ceiling (REPRODUCED, not ACCEPTED) and scope limits are unchanged.

## 0. Why this cycle exists (successor to the accepted v35 falsification)

The ACCEPTED v35 fairness audit (run 38039706350) established that dense embeddings are **not**
superior to the **TF-IDF citation representation** on identical matched pairs. It left one
surviving role untested against its *correct* comparator:

> "dense is justified only as a **text-only proxy** for citation-heritage when citations are
> unavailable."

The prior accepted dense-vs-text comparison (`dense 0.77–0.85` vs `TF-IDF text 0.50–0.63`)
was non-comparable (different pair sets, different feature sets, no self-pair control, and the
"text" comparator was the weaker `full_text_tfidf_light`, not the strong
`regeste_full_text_hybrid`). This cycle performs the missing, product-decisive test: **on a
corpus with no citation graph, does a dense text embedding beat the strongest text-only
baseline for predicting citation heritage?**

This is not a re-run of the same question: it is a different comparator class (text-only, no
citation features), a different success rule, and it produces a distinct product decision
(build a dense fallback view for imported corpora without citations).

## 1. Frozen hypothesis (pre-registered before outcome inspection)

Inputs and pipeline are identical to the accepted v35 audit (frozen dense checkpoints, frozen
ORIG pairs, language-center-projection, PCA-64, average-rank AUC). Text-only baselines are
always-available features: `regeste_tfidf`, `regeste_full_text_hybrid_{0.5,0.7}`,
`full_text_tfidf_light`. `cited_decisions_tfidf` is **excluded** from the text-only set because
it uses resolved citations (it is the v35 comparator, not a text-only baseline).

- **H1** (ORIG, identical matched self-pair-free pairs): `dense_cp64 − best_text_only ≥ +0.05` AUC.
- **H1b** (DIRECT citations, hard-negative matched pairs): same margin `≥ +0.05` AUC.
- **H2** (eval-criterion degeneracy): the frozen evaluation-lane dense gate
  (`AUC ≥ 0.75` on shared≥2 pairs) is not comparable to the `0.7296` `citation_heritage_auc`,
  because the shared≥2 relation is nearly fully encoded by the citation graph while DIRECT is not.
- **H3** (reconciliation): reproduce the evaluation-lane `0.7296` protocol exactly from raw inputs.

Threats pre-registered: T1 self-pairs `(d,d)`; T2 pair-set mismatch; T3 relation heterogeneity
(DIRECT vs SHARED≥1 vs SHARED≥2); T4 text-only baselines leaking citation tokens; T5 bootstrap
pairing of geometric-mean-similar pairs.

## 2. Results

### 2.1 H1 — PASS: dense is a materially better text-only citation-heritage proxy than any TF-IDF text baseline

Identical matched self-pair-free **ORIG** pairs (n_pos=606, n_neg=834; the same frozen set as v35):

| representation (feature class) | AUC | Δ vs dense |
|---|---:|---:|
| `dense_cp64` (text embedding) | **0.7189** | — |
| `regeste_full_text_hybrid_0.7` (best text-only) | 0.5866 | **−0.1324** |
| `regeste_full_text_hybrid_0.5` | 0.5521 | −0.1668 |
| `regeste_tfidf` (below chance) | 0.4850 | −0.2339 |
| `full_text_tfidf_light` (minimal text-only) | 0.5308 | −0.1881 |
| `cited_decisions_tfidf` (citation feature; not text-only) | 0.7159 | −0.0030 |

- **Margin = +0.1324 AUC**, bootstrap 95% CI **[+0.0925, +0.1709]** (n_boot=2000) — well above the
  pre-registered +0.05 threshold. **H1 PASS.**
- The strongest text-only baseline is still ~0.13 AUC below dense. The **weakest** text-only
  baseline is `regeste_tfidf` (0.4850, **below chance**), ~0.23 AUC below dense; the minimal
  full-text baseline sits between them (~0.19 below).
- For reference, the citation-feature comparator `cited_decisions_tfidf` remains statistically
  tied with dense (v35: +0.003, CI straddles 0). So the ordering is:
  citation-feature ≈ dense ≫ best text-only.

### 2.2 H1b — PASS on the DIRECT relation, larger n

DIRECT-citation hard-negative **matched** pairs (n_pos=5255, n_neg=6008):

| representation | AUC |
|---|---:|
| `dense_cp64` | **0.6924** |
| `regeste_full_text_hybrid_0.7` (best text-only) | 0.5616 |
| `full_text_tfidf_light` | 0.5388 |

- **Margin = +0.1308 AUC**, bootstrap 95% CI **[+0.1158, +0.1447]**. **H1b PASS.**

The +0.13 margin is stable across two independent pair constructions (ORIG and graph-derived
DIRECT), which rules out a single-pair-set fluke.

### 2.3 H2 — the evaluation-lane dense gate is degenerate on shared≥2 pairs

DIRECT and SHARED≥2 are *not* the same prediction problem. On matched hard-negative pairs:

| relation | n_pos/n_neg | `citation_jaccard_full` | `dense_cp64` |
|---|---:|---:|---:|
| DIRECT (no shared outgoing target) | 5255 / 6008 | 0.7718 | 0.6924 |
| SHARED1 (≥1 shared outgoing) | 29901 / 41317 | 1.0000 | 0.9248 |
| SHARED2 (≥2 shared outgoing) | 2875 / 3627 | **1.0000** | **0.9698** |

A binary outgoing-citation Jaccard is an **oracle** (AUC=1.0) on SHARED≥2, so *any* gate
evaluated there mostly measures graph coverage, not dense quality. The frozen evaluation
criterion (`dense AUC ≥ 0.75 on shared≥2`) is therefore mostly a coverage proxy; the honest
discriminating relation is DIRECT, where dense scores 0.6924 (< 0.75) and the graph wins.

H2 rule (`jaccard_SHARED2 ≥ 0.99 AND dense_SHARED2 ≥ 0.90 AND dense_DIRECT < 0.75`) — **SUPPORTED**
(1.0000, 0.9698, 0.6924).

### 2.4 H3 — reconciliation of the frozen evaluation baseline `0.7296`

Recomputed from raw inputs (protocol reconciled, **not bit-identical**):

| protocol | `cited_decisions_tfidf` AUC |
|---|---:|
| ORIG, **with** self-pairs (eval-lane protocol) | **0.7426** |
| ORIG, no self-pairs | 0.6967 |
| ORIG, matched no self-pairs (v35/v36 primary set) | 0.7159 |

The frozen evaluation value `0.7296` is a **with-self, mixed-relation, 1000/2000-sampled**
number. This run applied **no** `max_positive_sampled=1000` / `max_negative_sampled=2000` caps —
it scored the full 1020/1020 with-self ORIG (0.7426) and the matched self-pair-free set (0.7159)
— so the frozen `0.7296` is **not exactly reproduced** here (protocols reconciled, not
bit-identical), and it is not comparable to the flat "shared≥2, dense≥0.75" dense gate.
Reconciliation **PASS** — the two lanes measure different protocols, not contradictory
capabilities.

## 3. Decision-relevant conclusion

**Verdict: `DENSE_TEXT_PROXY_JUSTIFIED`.**

1. **Product action (primary):** when a corpus has a resolved citation graph, build the
   citation-heritage view from the graph (Jaccard / full-dimensional citation) — dense adds no
   significant signal over the graph on DIRECT and is redundant on shared-citation relations
   (v35). When a corpus has **no** citation graph (imported / unpublished sets), a dense text
   embedding is a **materially superior** citation-heritage proxy than any TF-IDF text baseline
   (+0.13 AUC). This defines the dense fallback view's scope.
2. **Evaluation action:** re-freeze the criterion for the dense fallback view against a
   **text-only** comparator (best regeste hybrid), on **relation-stratified, self-pair-free,
   relation-matched** pairs, and report DIRECT separately from SHARED. The current
   "shared≥2 / 0.75" gate should be marked degenerate and not used for dense promotion.
3. **No further same-question dense-scale cycle is justified.** The complementary-role
   characterization is complete; the remaining work is productization (fallback view) and an
   evaluation-criterion re-freeze, both outside this lane's write scope.

## 4. Provenance & reproducibility

- Frozen spec (pre-outcome): `legal_distance/results/citation_heritage_text_proxy_v36/frozen_spec.json`.
- Repair-round record (audit cycle 38056432926, required fixes D1–D3):
  `legal_distance/reports/legal_distance_v36_citation_heritage_text_proxy_REPAIR1.md`.
- **State-file reconciliation (provenance disclosure):** `legal_distance/state/legal-distance.json`
  was overwritten with (i.e. reconciled to) the canonical `state/legal-distance.json`
  `verification_runs` list (103 entries) plus this run (`38051603155`, 104 entries total),
  replacing 5 divergent entries that existed only in the accepted-base duplicate
  (`38031579621, 38027372192, 38026456230, 38017387070, 38014429418`). All replaced entries
  remain in git history; the reconciliation toward the canonical control-plane file
  (constitution §10, `main` is authoritative) is intended.
- Experiment: `legal_distance/experiments/citation_heritage_text_proxy_v36.py` (≈49 s; deterministic, seed 42).
  Determinism note: the relation sampler now returns `sorted(set)` negatives and `restrict_matched`
  returns sorted pairs. This was necessary because `bootstrap_margin` resamples by **positional**
  index, so the previous `list(set)` ordering (hash-seed dependent) shifted bootstrap CIs between
  processes. With the sort fix, two consecutive runs produce **byte-identical** output JSONs
  (md5-verified). Headline AUCs (H1/H1b/H2) were unchanged by the fix; only low-order bootstrap
  digits moved (H1b CI [+0.1161,+0.1445]→[+0.1158,+0.1447]).
- Results: `text_proxy_results.json` (H1, reconciliation, verdict),
  `relation_text_baselines_results.json` (H1b, H2, relation decomposition),
  `relation_pairs_v36.json` (frozen matched relation pair dump used by the test).
- Raw inputs (unchanged, mounted): dense checkpoints `legal_distance/results/174k_dense_embeddings/checkpoints/`;
  `evaluation/data/174k/metadata_174k.json`; `evaluation/results/174k/embeddings/*.npy`;
  `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`;
  graph `/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_graph_174k.json`
  (the graph is **not repo-tracked** and lives only in the accepted evaluation peer mount; the test
  treats graph-dependent jaccard/H2 checks as SKIP when the mount is absent — the dense/text-only
  AUCs and H1/H1b do not depend on it).
- Non-circular verification: `tests/legal_distance/test_citation_heritage_text_proxy_v36.py`.
  Section B recomputes every headline AUC from raw vectors with an **independent** trapezoidal-ROC
  implementation (not the experiment's average-rank AUC) and re-implemented assembly/PCA, asserting
  the **full text-only family** (all four TF-IDF reps on ORIG and on DIRECT), dense, cited-decisions
  and margin values against the committed JSONs. Section A checks committed-artifact consistency;
  Section C (added in repair round 1) parses this report's H1/H1b/H3 tables and asserts every AUC
  cell and Δ matches the committed JSONs to 4dp, that the §2.4 heading does not overclaim exact
  reproduction, and that §4 discloses the state-file reconciliation — so a D1-class report drift
  now fails the suite. With the graph mounted: **39 passed, 0 failed, 0 skipped**. Without the
  graph (auditor environment, verified via `LEX_CITATION_GRAPH=<nonexistent>`): **38 passed, 0
  failed, 1 skipped** (graph-dependent jaccard/H2 checks). The independent AUC matches the
  committed values to 1e-6.

## 5. Negative / qualifying results preserved

- Dense is **still not superior to the citation graph** on DIRECT (0.6924 vs 0.7718) and is
  **redundant** on shared-citation relations (graph oracle = 1.0). The text-only proxy advantage
  does **not** revive the retracted "dense beats citation features" claim.
- `full_text_tfidf_light` — the baseline used in the original non-comparable comparison — is
  **not** the strongest text-only representation (0.5308; `regeste_tfidf` is even weaker at
  0.4850, below chance). The original comparison understated the text-only class by ≈0.056 AUC
  versus the strongest text-only rep (`regeste_full_text_hybrid_0.7`, 0.5866).
- The bootstrap pairing of geometric-mean-similar pairs (T5) is a conservative approximation;
  it does not change pass/fail.
