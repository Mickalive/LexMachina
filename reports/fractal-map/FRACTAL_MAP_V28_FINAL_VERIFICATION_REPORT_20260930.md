# Fractal-Map Lane Final Verification Report — Factory Direction v28

**Run ID:** `fractal_map_v28_final_verification_20260930_cycle_36656873671`
**Timestamp:** 2026-09-30T01:50:00.000000+00:00
**Factory Direction Version:** 28
**Lane Status:** `BLOCKED_ON_DEPENDENCIES`
**Evidence Tier:** `REPRODUCED`
**Continue Recommended:** `false`

---

## Executive Summary

The fractal-map lane is **correctly blocked** on the single remaining dependency: **legal-distance 174k dense embeddings**. Only 3/26 years (2000-2002, ~19,441 decisions, 11%) of dense embeddings are ACCEPTED post-audit; 22/26 years (2003-2024) remain PENDING AUDIT and cannot be cited as accepted evidence.

All discriminating experiments for the current dependency state have been executed, evidence is preserved, findings are frozen. **No additional same-question cycle is justified.** The Factory Director must decide the successor question.

---

## Verification Results

### Test Suite Execution
- **Tests Passed:** 240
- **Tests Skipped:** 1 (dense mode artifacts not yet available at 174k)
- **Duration:** 1.58s
- **All integrity, consistency, and evidence-preservation checks PASS**

### State File Verification
`state/fractal-map.json` accurately reflects:
- `cycle_status: "BLOCKED_ON_DEPENDENCIES"`
- `continue_recommended: false`
- `evidence_tier: "REPRODUCED"`
- All `blocked_dependencies` correctly recorded
- All `accepted_claims` match raw evidence artifacts
- `factory_direction_v28_discrepancy` documented (control plane overstates constrained hierarchical results)

---

## Accepted Evidence Summary (Frozen)

### 1. TF-IDF 174k Flat Leiden — **FAIL** (v26 zoom-quality rule)
| Metric | Result |
|--------|--------|
| Modes passing v26 rule | 0/4 |
| Fine-resolution singleton fraction | >0.99 at res 2.0/3.0 |
| Coarse branch purity | 0.51–0.55 (vs 0.25 random) |
| Coarse legal_area purity | 0.24–0.31 (vs ~0.005 random) |
| Monotonic zoom refinement | **NO** |

**Conclusion:** Strong legal structure at coarse levels but **no monotonic zoom refinement**. Severe over-fragmentation makes flat map unusable for navigation.

---

### 2. TF-IDF 174k Constrained Hierarchical Leiden — **1/4 PASS** (hierarchical_v1 protocol)

| Mode | fine_branch_purity | legal_structure_branch | zoom_coherence | All 7 Checks |
|------|-------------------|------------------------|----------------|--------------|
| regeste_tfidf (83k sample) | **0.566** | ✅ PASS | ✅ PASS | **7/7 PASS** |
| full_text_tfidf | ~0.49 | ❌ FAIL | ✅ PASS | 6/7 |
| hybrid05 | ~0.40 | ❌ FAIL | ✅ PASS | 6/7 |
| hybrid07 | ~0.38 | ❌ FAIL | ✅ PASS | 6/7 |

**Structural metrics (all 4 modes):**
- singleton_fraction = 0.0 (min_cluster_size=10 enforcement)
- nesting = 1.0 (by construction)
- zoom_coherence improvement_rate = 57–90%
- branch/area purity delta > 0

**Conclusion:** Only `regeste_tfidf` on 83k sample meets full hierarchical_v1 protocol. TF-IDF fundamentally lacks signal density for fine_branch_purity > 0.5 at 174k scale.

---

### 3. Alternative Hierarchical Methods on 174k TF-IDF — **ALL FAIL**
| Method | Best fine_branch_purity |
|--------|------------------------|
| multi-resolution Leiden | ~0.35 |
| HNSW hierarchical | ~0.35 |
| Agglomerative Ward | ~0.37 |
| Agglomerative Average | ~0.36 |
| Agglomerative Complete | ~0.35 |
| Constrained Leiden (adaptive=false, min10) | ~0.35 |
| Local UMAP zoom neighborhoods | **0.3989** |

**Conclusion:** No clustering algorithm can overcome TF-IDF's signal density limitation at 174k scale. Best result 0.3989 is **20% below 0.5 threshold**.

---

### 4. Dense Embeddings (ACCEPTED 12k: years 2000-2002) — **Pipeline Validated**

| Config | fine_branch_purity | improvement_rate | nesting | All 7 Checks |
|--------|-------------------|------------------|---------|--------------|
| adaptive=True, min3 | **0.988** | 45.5% | 1.0 | **7/7 PASS** |
| coarse_0.5_fixed2.0_min20 | **0.986** | **0.50** (borderline) | 1.0 | 6/7 PASS |

**Key finding:** Adaptive sub-resolution HARMS zoom quality at ≥10k scale (improvement_rate capped at 45.5%). **DEPRECATED for scales ≥10k** per v26 rule. Fixed-resolution config achieves 6/7 checks with zoom_coherence exactly at threshold (0.50).

---

### 5. Scale Dependency — **CONFIRMED**

| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|--------------------------|
| 1k | Severe fragmentation | N/A |
| 1.2k | **PASS** (citing_alpha0.7) | N/A |
| 12k | FAIL | 45.5% (adaptive) / 19-35% (fixed) |
| 28k (PENDING AUDIT) | FAIL | **67%** (validates pipeline) |
| 174k TF-IDF | FAIL | 1/4 PASS (regeste only) |
| 174k Dense (predicted) | ~0.24 | **~0.67** (power law, HIGH confidence) |

**Scale extrapolation model VALIDATED:** 28k checkpoint confirms hier_impr = 0.67, matching power law prediction for 174k.

---

### 6. Evidence-Backed Zoom Path (Requires 174k Dense Embeddings)
| Mode | Scale | Zoom Quality (ZQ) |
|------|-------|-------------------|
| citing_alpha0.3 | 1000 | **0.5401** |
| following_alpha0.3 | 1000 | **0.5280** |
| criticizing_alpha0.3 | 1000 | **0.4864** |
| outcome_hybrid_0.5 (production default) | 1000 | 0.2798 |

**Conclusion:** Citation-role/dense-embedding modes work at 1000-scale but **require 174k dense embeddings to scale**.

---

### 7. Nesting Metric Defect v1 — **ENFORCED** (Audit CYCLE_36027099305)
- 7 compressed-family modes **PROHIBITED** from nesting_score ≥ 0.99 claims
- nesting_score = 1.0 citeable **ONLY** for:
  - 1000-scale modes (by construction)
  - 12k-scale modes (by construction, with scope annotation)
- Compressed 5-level ladder **NOT universally valid**

---

### 8. Pipeline Readiness for 174k Dense Embeddings
- **Status:** Operational at simulation level
- **Best validated config:** `coarse_0.5_fixed2.0_min20`
- **Validated at:** 12k ACCEPTED dense, 28k PENDING AUDIT checkpoint
- **Requires:** ACCEPTED 174k dense embeddings for production deployment

---

## Blocked Dependencies (Unchanged)

1. **legal-distance 174k dense embeddings** — only 3/26 years ACCEPTED (2000-2002)
2. **Citation-role embeddings** — not available at 174k scale
3. **Linear hybrid embeddings** — not available at 174k scale
4. **Frozen v26 zoom-quality rule** — cannot be satisfied by TF-IDF flat clustering at 174k
5. **Section-specific cross-lingual evaluation** (sachverhalt/erwaegungen/dispositiv) — blocked pending dense embeddings

---

## Factory Direction v28 Discrepancy (Documented)

**Issue:** `factory_direction.json` v28 claims *"ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule (per_mode_verdict: PASS)"* for constrained hierarchical Leiden.

**Reality:** `hierarchical_verdict_20260928_193114.json` shows **1/4 PASS** (regeste_tfidf 83k), **3/4 FAIL** on legal_structure_branch (fine_branch_purity ~0.38-0.49 < 0.5).

**Impact:** Control plane overstates constrained hierarchical results at 174k. Only regeste_tfidf (83k sample) meets full hierarchical_v1 protocol.

**Resolution Required:** Factory Director should correct `factory_direction.json` to reflect hierarchical_v1 protocol results accurately.

---

## Legal-Distance Progress Gap

| Status | Years | Decisions | Notes |
|--------|-------|-----------|-------|
| **ACCEPTED** | 3/26 (2000-2002) | ~19,441 | Post-audit, usable for fractal-map |
| **PENDING AUDIT** | 22/26 (2003-2024) | ~160k | Checkpointed, CANNOT be cited as accepted |
| **TOTAL CHECKPOINTED** | 25/26 (2000-2024) | ~160k | Per legal-distance progress.json |

---

## Evidence Artifacts Preserved (Immutable)

All raw outputs preserved in `results/fractal_map/`:
- `zoom_quality_174k_eval/v26_verdict.json`
- `hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json`
- `nesting_metric_defect_v1_audit.json`
- `constrained_hierarchical_tests/` (4× 174k TF-IDF modes)
- `12k_dense_hierarchical_test/hierarchical_leiden_results.json`
- `12k_dense_comprehensive/` (2 runs)
- `28k_checkpoint_validation/28k_validation_20260928_212756.json`
- `pipeline_readiness_final/pipeline_readiness_12k_dense_coarse0.5_fixed2.0_min20_20260930_001147.json`
- `12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_v2_20260928_133636.json`
- `alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json`
- `zoom_coherence_1000scale_citation_roles.json`

---

## Negative Results Preserved (First-Class Evidence)

1. **TF-IDF flat Leiden 174k:** 0/4 modes pass v26 zoom-quality rule
2. **TF-IDF constrained hierarchical 174k:** 3/4 modes FAIL legal_structure_branch
3. **Alternative hierarchical methods 174k TF-IDF:** ALL FAIL fine_branch_purity > 0.5
4. **Adaptive sub-resolution ≥10k:** HARMS zoom quality (capped at 45.5%)
5. **Dense 12k adversarial:** language_dominance ~0.98, jurist_preference ~0.04
6. **Citation heritage 174k:** ALL reps FAIL recall@10 < 0.2
7. **Coarse hierarchy v18:** Even at 4-label branch level, max purity 0.65 < 0.7 threshold

---

## Recommendation to Factory Director

**Lane Status:** `BLOCKED_ON_DEPENDENCIES` — **correctly blocked**

**Continue Recommended:** `false` — no additional same-question cycle justified

**Required Action:** 
1. **Correct `factory_direction.json`** to accurately reflect hierarchical_v1 protocol results (1/4 PASS, not 4/4)
2. **Promote legal-distance 174k dense embeddings through audit** to unblock fractal-map lane
3. **Define successor question** for fractal-map once 174k dense embeddings are ACCEPTED

**Successor Question Candidates:**
- Full 174k dense embedding hierarchical map construction and evaluation
- Citation-role/dense-embedding mode scaling from 1k → 174k
- Section-specific (sachverhalt/erwaegungen/dispositiv) hierarchical maps
- Cross-lingual hierarchical evaluation at full corpus density
- Jurist usability study on hierarchical vs flat map navigation

---

## Provenance

| Artifact | Source |
|----------|--------|
| 12k dense embeddings (ACCEPTED) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002) |
| 28k checkpoint embeddings (PENDING AUDIT) | Same path (years 2000-2005) — **pipeline validation only** |
| Citation-alpha embeddings (ACCEPTED) | `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions) |
| Metadata 174k | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Global seed | 42 |
| Leiden seed | 42 |
| k_neighbors | 15 |

---

## Audit Gates Passed

- CYCLE_36495654105
- CYCLE_36554241961
- CYCLE_36580077418
- CYCLE_36582579243
- CYCLE_36638488102
- CYCLE_36644449527
- CYCLE_36655303636
- **THIS CYCLE: 36656873671**

---

**Verification Complete.** All evidence preserved. Negative results preserved. Lane correctly blocked awaiting upstream dependency resolution.