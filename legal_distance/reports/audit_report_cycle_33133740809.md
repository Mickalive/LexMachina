# Legal Distance Lane — Audit Report for Cycle 33133740809

**Factory Direction Version:** 6 (target) / 5 (current control plane)  
**Lane:** legal-distance  
**Run ID:** center_projected_reproduction_20260828  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED (with documented gaps)  
**Date:** 2026-08-28

---

## 1. Executive Summary

This audit report documents the actual completion status of Legal Distance lane objectives under Factory Direction v6, correcting a prior orchestration failure where all 6 objectives were marked COMPLETED when only 2 were fully completed and 4 require significant additional work.

### 1.1 Orchestration Failure Diagnosed

**Prior state claim (legal_distance.json before correction):**
> "All factory direction v6 legal-distance objectives completed."

**Actual status:**
| Objective | Factory Direction v6 Requirement | Actual Status | Evidence |
|-----------|----------------------------------|---------------|----------|
| 1. Reproduce center_projected | Validate on full v1+v2 benchmark suite | ✅ **COMPLETED** | v2_benchmark_results.json, full_benchmark_results.json |
| 2. Re-run signal ablation & scale test | **USING center_projected as baseline** | ⚠️ **PARTIAL** | Scale test run on debiased_citation_blended baseline only |
| 3. Legal embeddings fine-tuning | Fine-tune multilingual-e5-small on Swiss legal corpus | ⚠️ **PARTIAL** | Only pre-trained models tested; no fine-tuning |
| 4. Citation role integration | Integrate 2,988 roles once ID resolution ready | ⚠️ **PARTIAL** | Roles extracted; ID resolution pipeline NOT BUILT |
| 5. Jurist pairwise evaluation | Execute with 5-10 Swiss jurists | ⚠️ **PARTIAL** | Framework ready; human evaluation NOT EXECUTED |
| 6. Benchmark refinement | Maintain 16-benchmark suite with adversarial gates | ✅ **COMPLETED** | benchmark_refinement_analysis.json |

### 1.2 Key Validated Result

**center_projected is the ONLY representation passing BOTH critical adversarial tests:**
- **Adversarial Language Dominance:** 0.7593 < 0.85 ✅ PASS
- **Jurist Pairwise Preference:** 0.5215 > 0.5 ✅ PASS

The previous default (debiased_citation_blended) FAILS jurist pairwise preference (0.4515).

**Product Decision:** center_projected must become the default reference representation. Product lane v6 has already integrated it (97/97 tests passing, 12 representations).

---

## 2. Evidence Inventory

### 2.1 Primary Evidence (Claim-Bearing)

| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| v2 Benchmark Results | `legal_distance/results/v5/center_projected/v2_benchmark_results.json` | Cross-language + jurist usability benchmarks for center_projected vs baseline | ✅ VALID |
| Full Benchmark Results | `legal_distance/results/v5/center_projected/full_benchmark_results.json` | v1 fractal-map + v2 adversarial + scale stability | ✅ VALID |
| Center Projected Embeddings (768) | `legal_distance/results/v5/center_projected/embeddings_center_projected.npy` | 1000 decisions × 768 dim, L2-normalized | ✅ VALID |
| Center Projected Embeddings (multi-dim) | `legal_distance/results/v5/center_projected_full/` | 768, 128, 64 dim variants for 1000 decisions | ✅ VALID |
| Scale Test (1200 decisions) | `legal_distance/results/v5/scale_test/scale_test_all_results.json` | 15 modes on fractal-map harness | ⚠️ BASELINE MISMATCH |
| Legal Embeddings Test | `legal_distance/results/v5/legal_embeddings/legal_embeddings_all_results.json` | 3 multilingual models on fractal-map harness | ⚠️ NO FINE-TUNING |
| Citation Roles | `legal_distance/results/v5/citation_roles/` | 2,988 annotations, 6 role-specific matrices | ⚠️ NO ID RESOLUTION |
| Jurist Eval Framework | `legal_distance/results/v5/jurist_eval/` | 200 questions, UI spec, sampling, analysis plan | ⚠️ NOT EXECUTED |
| Benchmark Refinement | `legal_distance/results/v5/benchmark_refinement/benchmark_refinement_analysis.json` | 37 → 16 non-redundant benchmarks | ✅ VALID |

### 2.2 Negative Results Preserved (First-Class Evidence)

- **multilingual-e5-small:** FAILS fractal-map harness (improvement_rate=29.4%)
- **cross_language_retrieval:** FAILS for both center_projected (0.1586) and baseline (0.1194)
- **v1 hierarchical_leiden:** PARTIAL (improvement_rate=42.6% < 50% threshold)
- **v1 zoom_coherence:** 0% improvement rate (no language-homogeneous clusters with substructure)
- **Scale test baseline mismatch:** Used debiased_citation_blended, not center_projected
- **No fine-tuning:** multilingual-e5-small not fine-tuned on Swiss legal corpus
- **No ID resolution:** Citation roles cannot be integrated into graph
- **No human jurists:** Evaluation framework complete but unexecuted

---

## 3. Experimental Validation Details

### 3.1 center_projected Reproduction (Objective 1) — COMPLETED

**Method:** Subtract per-language mean from 768-dim baseline embeddings, L2-normalize.

**v2 Benchmark Results (1000 decisions):**

| Benchmark | center_projected | debiased_citation_blended | Threshold |
|-----------|------------------|---------------------------|-----------|
| Adversarial Language Dominance | 0.7593 ✅ | 0.8116 ✅ | < 0.85 |
| Jurist Pairwise Preference | 0.5215 ✅ | 0.4515 ❌ | > 0.5 |
| Zero-shot Transfer NMI | 0.310 ✅ | 0.274 ✅ | PASS |
| Language-specific Quality NMI | 0.391 ✅ | 0.386 ✅ | PASS |
| Cross-language Retrieval | 0.159 ❌ | 0.119 ❌ | > 0.2 |
| Cluster Coherence (branch purity) | 0.916 ✅ | 0.904 ✅ | PASS |
| Zoom Task | +4.62% ✅ | +4.62% ✅ | PASS |

**v1 Fractal-Map Results:**
- Hierarchical Leiden: improvement_rate=42.6% (threshold 50%), legal_area_nmi=0.602
- Zoom Coherence: 0% improvement rate

**Scale Stability (frozen corpus growth test):**
- Position drift: 1.0 (perfect) at all growth steps (200→400→600→800→1000)
- Neighbor preservation @k=10: 51% → 68% → 76% → 80% (improving with scale)
- Cluster stability (NMI/ARI): 1.0 at all steps

### 3.2 Scale Test on Full Corpus (Objective 2) — PARTIAL

**Corpus:** 1,200 deduplicated decisions (DE=735, FR=403, IT=62)

**Modes Tested (15):** baseline, sachverhalt_tfidf, norm_embeddings, erwaegungen_tfidf, legal_area_tfidf, cited_decisions_tfidf, erwaegungen+citations, sachverhalt+erwaegungen, hybrid_erwaegungen_03/05/07, hybrid_sachverhalt_07, hybrid_norm_07, legal_issues_outcomes, core_legal

**Key Findings (on debiased_citation_blended baseline):**
- All 15 modes PASS fractal-map harness
- Best fine purity: sachverhalt_tfidf (0.986), norm_embeddings (0.974)
- Best coarse preservation: hybrid_erwaegungen_07 (+0.039 coarse, +0.047 fine)
- Best NMI: legal_issues_outcomes (0.786, +0.272)
- Best legal area purity: legal_area_tfidf (0.894 coarse, 0.998 fine)

**GAP:** Factory direction v6 requires re-running **using center_projected as baseline**. Not done.

### 3.3 Legal Embeddings (Objective 3) — PARTIAL

| Model | Dim | Fractal-Map | Lang Dominance | Cross-lang Rate | Verdict |
|-------|-----|-------------|----------------|-----------------|---------|
| xlm-roberta-base | 768 | 92.7% ✅ | 1.002 | 0.571 | PASS |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 66.4% ✅ | 1.065 | ~0.6 | PASS (ref) |
| multilingual-e5-small | 384 | 29.4% ❌ | 1.034 | 1.000 | FAIL |

**GAP:** Fine-tuning multilingual-e5-small on Swiss legal corpus NOT DONE.

### 3.4 Citation Role Modeling (Objective 4) — PARTIAL

- **200 decisions analyzed, 2,988 role annotations extracted**
- Role distribution: citing (2,427), following (311), criticizing (174), distinguishing (58), overruling (18)
- **6 role-specific embedding matrices created** (64-dim each) + weighted combination
- **BLOCKER:** Citation target IDs (BGE/ATF format) don't match corpus decision_id format → cannot build citation graph

### 3.5 Jurist Evaluation Framework (Objective 5) — PARTIAL

- **200 evaluation questions** generated (30 anchors × mode pairs)
- **6 primary comparisons:** baseline vs sachverhalt_tfidf, baseline vs norm_embeddings, baseline vs hybrid_erwaegungen_07, sachverhalt_tfidf vs erwaegungen_tfidf, norm_embeddings vs legal_area_tfidf, legal_issues_outcomes vs hybrid_erwaegungen_07
- **UI specification:** Decision cards, side-by-side candidates, 4 response options + confidence
- **Sampling strategy:** Stratified by branch/language/year
- **Analysis plan:** Binomial test, McNemar, bootstrap CI, Fleiss' kappa
- **Success criteria:** Preference rate > 55%, p < 0.05, Fleiss' kappa > 0.6, min 30 responses/comparison
- **GAP:** Human evaluation NOT EXECUTED (needs 5-10 Swiss jurists, 3+ years experience)

### 3.6 Benchmark Refinement (Objective 6) — COMPLETED

- **37 benchmarks → 16 non-redundant**
- **Tier 1 Core (7, gating):** adversarial_language_dominance, jurist_pairwise_preference, jurivoc_l2_descriptor_recovery_nmi, zoom_coherence_improvement_rate, citation_heritage_auc, legal_area_classification_accuracy, scale_stability_frozen_pca
- **Tier 2 Diagnostic (6):** zero_shot_transfer, hierarchical_advantage, boilerplate_resistance, collapse_check, temporal_stability, jurivoc_hierarchy_alignment
- **Tier 3 Exploratory (3):** cross_language_retrieval_recall, jurist_cluster_coherence, jurist_zoom_task
- **Removed (4 redundant):** citation_proximity, multilingual_invariance, cross_language_pairs, tf_metadata_human_indexing

---

## 4. Product Integration Status

**Product Lane v6: VERTICAL SLICE COMPLETE**
- 97/97 tests passing
- 12 representations integrated (center_projected DEFAULT + 11 selectable modes)
- User corpus import functional
- Map export functional

**Map Modes Ready for Product (6 selectable):**
1. **debiased_citation_blended** — Default general-purpose (100% coverage)
2. **hybrid_erwaegungen_07** — General + legal reasoning boost (100% coverage)
3. **sachverhalt_tfidf** — Fact-based case finding (60% coverage)
4. **norm_embeddings** — Article/statute doctrine tracking (61% coverage)
5. **legal_issues_outcomes** — Issue/outcome-focused browsing (100% coverage)
6. **erwaegungen+citations** — Precedent-reasoning integration (100% coverage)

---

## 5. Audit Trail & Provenance

### 5.1 Git History (Legal Distance Lane)
```
975f8e3 legal-distance cycle 33133740809 repair 0  ← CURRENT
3452c98 accept legal-distance cycle 33128038871
7e718c0 legal-distance cycle 33128038871 repair 0
2f52075 legal-distance cycle 33125341946 repair 0
a480244 accept legal-distance cycle 33124311346
...
```

### 5.2 Files Modified in This Cycle (Repair 0)
- `legal_distance/experiments/evaluate_center_projected_full.py` — Full benchmark evaluation script
- `legal_distance/experiments/reproduce_center_projected.py` — Reproduction script
- `legal_distance/experiments/reproduce_center_projected_v2.py` — V2 benchmark script
- `legal_distance/results/v5/center_projected/` — All benchmark results + embeddings
- `legal_distance/results/v5/center_projected_full/` — Multi-dim embeddings
- `legal_distance/results/v5/jurist_eval/evaluation_questions.json` — Updated questions
- `legal_distance/results/v5/legal_embeddings/` — Updated results
- `legal_distance/results/v5/scale_test/` — Updated scale test results
- `state/legal_distance.json` — **CORRECTED** (this audit)
- `reports/legal-distance/cycle_report_20260828.md` — Cycle report

### 5.3 No Data Fabrication
- All raw experimental outputs preserved in `results/v5/`
- No claim-bearing measurements modified after observation
- Negative results (FAIL benchmarks, incomplete objectives) explicitly documented
- Center_projected reproduction independently verified via direct computation

---

## 6. Recommendations for Factory Director

### 6.1 Immediate Actions (Current Cycle Closure)
1. **ACCEPT** center_projected as reference representation (evidence: REPRODUCED tier)
2. **UPDATE** factory direction to v6 with corrected legal-distance objectives
3. **NOTE** that objectives 2-5 require dedicated cycles (not same-question continuation)

### 6.2 Next Factory Direction (v6 → v7) — Legal Distance Lane
**Priority 1:** Re-run scale test with center_projected as baseline (supersedes debiased_citation_blended)
**Priority 2:** Fine-tune multilingual-e5-small on Swiss legal corpus
**Priority 3:** Build citation ID resolution pipeline (BGE/ATF → decision_id)
**Priority 4:** Execute jurist pairwise evaluation (recruit 5-10 Swiss jurists)
**Priority 5:** Frontier metric_learning_jurivoc must beat center_projected on adversarial benchmarks

### 6.3 Cross-Lane Dependencies
- **Corpus lane:** Must deliver citation ID resolution pipeline for objective 4
- **Fractal-map lane:** Must reproduce hierarchical Leiden on center_projected (in progress)
- **Evaluation lane:** v3 uses center_projected as frozen baseline
- **Frontier metric_learning_jurivoc:** Must beat center_projected on adversarial benchmarks

---

## 7. State File (Machine-Readable) — Corrected

```json
{
  "lane": "legal-distance",
  "direction_version": 6,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": true,
  "accepted_run_id": "center_projected_reproduction_20260828",
  "evidence_refs": [
    "legal_distance/results/v5/center_projected/v2_benchmark_results.json",
    "legal_distance/results/v5/center_projected/full_benchmark_results.json",
    "legal_distance/results/v5/center_projected/embeddings_center_projected.npy",
    "legal_distance/results/v5/scale_test/scale_test_all_results.json",
    "legal_distance/results/v5/legal_embeddings/legal_embeddings_all_results.json",
    "legal_distance/results/v5/citation_roles/citation_roles_summary.json",
    "legal_distance/results/v5/citation_roles/citation_roles_sample.json",
    "legal_distance/results/v5/jurist_eval/evaluation_protocol.json",
    "legal_distance/results/v5/benchmark_refinement/benchmark_refinement_analysis.json"
  ],
  "completed_objectives": {
    "1_reproduce_center_projected": "COMPLETED",
    "2_scale_test_full_corpus": "PARTIAL - baseline mismatch",
    "3_legal_embeddings_multilingual": "PARTIAL - no fine-tuning",
    "4_citation_role_modeling": "PARTIAL - no ID resolution",
    "5_jurist_pairwise_framework": "PARTIAL - not executed",
    "6_benchmark_refinement": "COMPLETED"
  }
}
```

---

## 8. Sign-Off

**Auditor:** LexMachina Legal Distance Lane (autonomous)  
**Verification:** All claim-bearing results traceable to raw outputs in `results/v5/`  
**Integrity:** Negative results preserved; no post-hoc metric changes; no data fabrication  
**Audit Readiness:** ✅ COMPLETE — Snapshot accurately reflects actual completion status

---

*Report generated from frozen experimental results. All raw outputs preserved in `legal_distance/results/v5/`.*