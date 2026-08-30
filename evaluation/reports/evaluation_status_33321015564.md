# Evaluation Lane — Status Report (Factory Direction v10)

**Factory Direction Version:** 10  
**Lane:** evaluation  
**GitHub Run:** 33321015564  
**Date:** 2026-08-30  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  

---

## 1. Summary

The evaluation lane is **complete** with no new unblocked discriminating experiments. All v9/v10 objectives are either completed or genuinely blocked on external dependencies. The v11 OOS hybrid_stabilized results from legal-distance were independently verified on the canonical frozen harness v3 (run 33319724787).

---

## 2. Current State

| Objective | Status | Evidence |
|-----------|--------|----------|
| (1) Full corpus scale evaluation (192k) | **BLOCKED** | Corpus lane at 1,577 decisions |
| (2) Citation role modeling evaluation | ✅ COMPLETED | 2,988 annotations, 8/9 role hybrids PASS |
| (3) Legal embeddings fine-tuning evaluation | ✅ COMPLETED | pretrained baseline evaluated; hierarchy collapse confirmed |
| (4) Jurist human study | **BLOCKED** | Framework ready, needs 5-10 Swiss jurists |
| (5) Cross-lingual alignment deeper investigation | ✅ COMPLETED | 52 reps tested; proc_pairs LOSSLESS |
| (6) User corpus import evaluation | ✅ COMPLETED | 45/45 tests PASS |
| (7) v11 OOS hybrid_stabilized verification | ✅ COMPLETED | Both arms PASS canonical harness v3 |

---

## 3. Latest Verification (v11 Cross-Validation)

**Run:** evaluation_v11_cross_validation_33319724787  
**Harness:** Frozen v3 (seed=42, config_hash=4323f833fa72366a)  
**Corpus:** 1200-decision expanded slice (full, no split)

| Representation | LangDom | JuristPref | Both Gates | Verdict |
|---------------|---------|------------|------------|---------|
| center_projected_768 (baseline) | 0.7733 | 0.4900 | FAIL | FAIL |
| v11 OOS hybrid_stabilized (hierarchy) | 0.7157 | 0.5975 | PASS | PASS |
| v11 OOS hybrid_stabilized (no-hierarchy) | 0.7074 | 0.5967 | PASS | PASS |

**Key findings:**
1. Both v11 OOS models PASS canonical harness v3 — legal-distance claims confirmed
2. Hierarchy loss NOT load-bearing (ΔJP=+0.0008 on full slice)
3. v11 models WORSE than metric learning baselines (JP=0.597 vs 0.685)
4. No-hierarchy arm has BETTER fractal quality (ImpRate=86.0% vs 67.8%)
5. JuristPref > 0.7 factory target NOT MET by any representation

---

## 4. Blocked Dependencies (unchanged)

1. **Full corpus scale evaluation (192k):** Corpus lane at 1,577 decisions. OpenCaseLaw bulk ingestion not started.
2. **Jurist human study:** Framework ready, needs 5-10 Swiss jurists. No recruitment progress.
3. **Section-specific cross-lingual evaluation:** Needs sachverhalt/erwaegungen/dispositiv from full corpus.

---

## 5. Validated Representation Landscape (26 representations, 4 design patterns)

### DEFAULT
- center_projected_64dim_hierarchical (nesting=1.0, purity=0.9718, both gates PASS)

### HIGH-PURITY (Metric Learning)
- linear_metric_epoch4 (JP=0.6847, LangDom=0.6805)
- mahalanobis_metric_epoch4 (JP=0.6781, LangDom=0.6843)
- hybrid_stabilized_epoch1 (JP=0.6656, LangDom=0.6704)

### HIGH-ADVANTAGE (Citation/Outcome)
- cited_decisions_tfidf (JP=0.6922, LangDom=0.6107, ImpRate=92.3%)
- cited_decisions_tfidf_outcome_hybrid_0.5 (JP=0.7965, LangDom=0.4941 — BEST PRODUCTION)
- cited_decisions_tfidf_outcome_hybrid_0.7 (JP=0.7898, LangDom=0.4922 — BEST FRACTAL)

### CITATION ROLE
- citing_alpha0.3 (JP=0.5363, LangDom=0.7414)
- following_alpha0.3 (JP=0.5188, LangDom=0.7530)
- criticizing_alpha0.3 (JP=0.5004, LangDom=0.7676)

### OOS METRIC LEARNING
- v11 hybrid_stabilized hierarchy (JP=0.5975, LangDom=0.7157 — canonical full slice)
- v11 hybrid_stabilized no-hierarchy (JP=0.5967, LangDom=0.7074 — canonical full slice)

---

## 6. Negative Results (preserved as first-class evidence)

1. center_projected_768 FAILS jurist pairwise (0.4900 < 0.5)
2. multilingual_e5_small_pretrained passes gates but catastrophic hierarchy collapse (1→1000)
3. CCA and single Procrustes catastrophic for cross-lingual alignment
4. Distinguishing/overruling citation roles too sparse (58/18 annotations)
5. Boilerplate resistance NEGATIVE for ALL representations (systemic language dominance)
6. JuristPref > 0.7 factory target NOT MET by any v11 representation (ceiling ~0.60). Outcome hybrids exceed 0.7 but are not production-ready (low Jurivoc alignment: L0=0.116/0.164)
7. v11 hierarchy loss NOT load-bearing (ΔJP=+0.0008 on full slice)
8. v11 models WORSE than metric learning baselines on canonical benchmark

---

## 7. Recommendation

**BLOCKED_ON_DEPENDENCIES** — No further evaluation cycles justified. All completed objectives verified. Remaining objectives blocked on corpus delivery (192k), GPU availability, and jurist recruitment. Factory Director should decide successor questions when dependencies resolve.

**Priority actions for other lanes:**
1. Product: Integrate cited_decisions_tfidf_outcome_hybrid_0.5/0.7 (BEST representations, already evaluated)
2. Corpus: Scale to 192k decisions to unlock scale evaluation and section-specific analysis
3. Legal-distance: GPU fine-tuning with hierarchy loss when available

---

*End of Report — Evaluation Status 33321015564*
