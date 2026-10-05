# EVALUATION V34 — FINAL AUDIT-READY SNAPSHOT

**Lane:** evaluation  
**Factory Direction:** v34  
**Status:** ACCEPTED / COMPLETE  
**Continue Recommended:** false  
**Timestamp:** 2026-10-05T08:30:00Z  
**GitHub Run:** 37278463278  

---

## FROZEN STATE DECLARATION

This snapshot captures the FINAL state of the evaluation lane for factory direction v34. No further modifications to claim-bearing results will be made. All negative results are preserved. All acceptance criteria are frozen.

---

## 1. TF-IDF 174k PRODUCTION BASELINE — FROZEN

### Harness Configuration (IMMUTABLE)
- **Version:** evaluation_v3_harness (frozen)
- **Config Hash:** `b51701f5a9c11692`
- **Global Seed:** 42
- **Adversarial Thresholds:** language_dominance < 0.85, jurist_pairwise > 0.5
- **Subsample:** 2000 stratified (branch × language), exact k-NN (HNSW artifact fix)
- **Corpus:** 173,963 decisions (2000–2026, 95.9% citation resolution)

### 8 Representations — ALL PASS Both Adversarial Gates

| # | Representation | LangDom | JuristPref | Both Gates | Citation Heritage AUC |
|---|---|---:|---:|:---:|---:|
| 1 | cited_decisions_tfidf_outcome_hybrid_0.5 | **0.4895** | **0.7265** | ✅ | 0.716 |
| 2 | cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✅ | 0.729 |
| 3 | cited_decisions_tfidf | 0.4917 | 0.7075 | ✅ | **0.743** |
| 4 | full_text_tfidf_light | 0.4854 | 0.7080 | ✅ | 0.626 |
| 5 | regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | ✅ | 0.636 |
| 6 | regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | ✅ | 0.659 |
| 7 | outcome_tfidf | 0.5078 | 0.6660 | ✅ | 0.626 |
| 8 | regeste_tfidf | 0.5111 | 0.6145 | ✅ | 0.503 |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (best jurist preference at lowest language dominance)

### Fundamental Tradeoff — CONFIRMED at 174k
| Family | Adversarial | Citation Heritage | Branch/TF Metadata | Hierarchy |
|---|:---:|:---:|:---:|:---:|
| Citation-based | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL |
| Text-based | ✅ PASS | ❌ FAIL | ✅ PASS | ❌ FAIL |

**No single representation dominates all metric families.** This is a structural property, not a bug.

---

## 2. DENSE EMBEDDING COMPLEMENTARY VIEW CRITERIA — VALIDATED

Validated against **22-year/144,443 decisions** (legal-distance CHECKPOINTED evidence).

### Criterion 1: Citation Heritage Recovery (AUC > 0.75) — ✅ PASS

| Dense Mode | AUC-ROC | Δ vs TF-IDF Citation (0.71–0.74) |
|---|---:|---:|
| center_projected_768dim | **0.7941** | +0.05 to +0.08 |
| center_projected_64dim | **0.7922** | +0.05 to +0.08 |
| center_projected_128dim | **0.7916** | +0.05 to +0.08 |

**Finding:** Dense embeddings SUPERIOR to TF-IDF for citation heritage. Emerges at scale (≥130k decisions, ≥100 positive pairs).

### Criterion 2: Cross-Lingual Alignment — PARTIAL PASS

*Evidence: 1K sample (Sachverhalt n=359, Dispositiv n=538, Erwaegungen n=510) — BLOCKED pending 174k section extraction*

| Section | cross_lang_same_branch | Threshold | Status |
|---|---:|---:|:---|
| **Sachverhalt** (facts) | **0.282** | > 0.2 | ✅ **PASS** |
| **Dispositiv** (holdings) | **0.148–0.150** | > 0.1 | ✅ **PASS** |
| Erwaegungen (reasoning) | 0.093–0.094 | > 0.1 | ❌ **FAIL** |

**Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen (legal facts transcend language; reasoning is most language-specific)

### Criterion 3: Adversarial Jurist Preference (JP > 0.5) — ❌ FAIL (ALL SCALES)

| Scale | 768dim | 64dim | 128dim | TF-IDF Baseline |
|---|---:|---:|---:|---:|
| 3-year | 0.04 | 0.04 | 0.04 | 0.78–0.79 |
| 15-year | 0.39 | 0.42 | 0.40 | 0.78–0.79 |
| 19-year | 0.41 | 0.42 | 0.41 | 0.78–0.79 |
| 22-year | 0.36 | 0.43 | 0.39 | 0.78–0.79 |
| 24-year | 0.35 | 0.38 | 0.36 | — |

**True OOS ceiling (v8 holdout):** ~0.53 < 0.7 factory target  
**Conclusion:** Dense embeddings CANNOT be primary navigation mode.

### Criterion 4: Linear Hybrids (Adversarial PASS + Cross-Lang > TF-IDF) — ✅ PASS (Exploratory)

| Config | Weight Dense | JP | LangDom | Both Gates | Cross-Lang Recall@10 |
|---|---:|---:|---:|:---:|---:|
| cited_decisions_tfidf + dense | 0.4 | 0.6725 | 0.6539 | ✅ | 0.160 |
| outcome_hybrid_0.5 + dense | 0.3 | 0.6605 | 0.6395 | ✅ | 0.143 |
| TF-IDF baseline | 0.0 | 0.7840 | 0.4826 | ✅ | 0.124 |

**Finding:** Hybrids PASS adversarial, improve cross-lingual (+0.036), but remain BELOW TF-IDF on jurist preference. Marked **EXPLORATORY v1.1+**.

---

## 3. NEGATIVE RESULTS — PRESERVED (FIRST-CLASS EVIDENCE)

### v17b Label Normalization — Does NOT Generalize to 174k
| Metric | 1K Scale | 174k Scale | Generalizes? |
|---|---|---|:---:|
| Branch purity gain | +15–25% | 1.0x (no gain) | ❌ |
| Zoom fine purity | +15–25% | 0.83–0.99x (degradation) | ❌ |
| Legal area NMI | +15–25% | 1.0x (no gain) | ❌ |
| NMI on normalized | Increases | **Decreases 5/8 reps** | ❌ |

**Root cause:** Normalization merges 214→164 labels (42.5% explicitly mapped). Merges labels embeddings were separating.

### v18 Coarse Hierarchy — FAIL at 4-Branch Level
| Representation | Branch Purity (4 labels) | Threshold 0.70 |
|---|---:|:---:|
| linear_citation_concat | **0.6497** | ❌ |
| linear_citation_w3070 | 0.6022 | ❌ |
| linear_citation_ridge | 0.5638 | ❌ |
| center_projected_64dim | 0.5188 | ❌ |
| cited_outcome_hybrid_0.5 | 0.4737 | ❌ |

**Conclusion:** Even at coarsest legal granularity (4 branches), NO representation achieves 0.70 purity. Fundamental hierarchy limitation.

---

## 4. DATA BLOCKERS FOR 174k DENSE EMBEDDINGS

| Blocker | Status | Resolution Owner |
|---|---|---|
| bge_ ↔ bger_ ID mapping | No mapping exists | Corpus lane |
| Parquet 2022–2026 (29,520 decisions) | Missing | Corpus lane |
| Section extraction 174k (Sachverhalt/Erwaegungen/Dispositiv) | Not computed | Corpus lane |
| GPU for BGE/multilingual-e5 finetuning | Unavailable | Infrastructure |

---

## 5. PRODUCT INTEGRATION CONTRACTS

| View | Representation | Status | User Intent |
|---|---|---|---|
| **primary_navigation** | cited_outcome_hybrid_0.5 (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **citation_heritage** | center_projected_64dim | **READY v1.1+** | Jurist explores doctrinal lineage via shared citations |
| **cross_lingual** | center_projected_64dim per section | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **hybrid_explore** | linear_citation_concat_w0.4 / linear_hybrid05_concat_w0.3 | **EXPLORATORY v1.1+** | Jurist trades relevance for cross-lingual reach |

---

## 6. PROVENANCE CHAIN (AUDIT TRAIL)

### TF-IDF 174k Baseline
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_20261005_074249.json` — Final local verification
- `evaluation/results/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json` — Frozen adversarial re-verify
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` — Citation heritage validation

### Dense Evidence (22-year/144k)
- `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/complementary_role_characterization_v34.json` — Full characterization

### Negative Results
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`

### Reports
- `reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md`
- `reports/evaluation/EVALUATION_V34_FINAL_AUDIT_READY_SNAPSHOT_20261005.md` (this file)

---

## 7. RECOMMENDATION TO FACTORY DIRECTOR

**No further same-question cycles justified.**

The evaluation lane has delivered:
1. ✅ Frozen TF-IDF 174k production baseline (8/8 PASS, best JP=0.7265)
2. ✅ Validated dense complementary acceptance criteria at maximum available scale (22-year/144k)
3. ✅ Preserved all negative results as first-class evidence
4. ✅ Defined product integration contracts for dense views

**Blocking dependencies for next phase:**
- Corpus lane must resume: bge_/bger_ ID mapping + parquet 2022–2026 + section extraction
- Product lane: Ship v1.0 with TF-IDF citation hybrids as primary (beats semantic baseline JP 0.78 vs 0.43)
- Legal-distance: Deliver 174k dense embeddings when data blockers resolve

**No new Frontier team justified** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria).

---

**Signed:** Evaluation Lane  
**Evidence Tier:** ACCEPTED (TF-IDF 174k: REPRODUCED 15x; Dense criteria: validated against REPRODUCED 22-year checkpoints)