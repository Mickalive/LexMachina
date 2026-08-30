# Evaluation v9 Comprehensive - Verification Run (GitHub Run 33299401770)

**Date:** 2026-08-30  
**Factory Direction:** v9  
**Harness:** Frozen v3 (seed=42, config_hash=4323f833fa72366a)  
**Corpus:** 1,200 decisions (expanded slice) + 1,000 decisions (multilingual-e5-small)

## Verification Summary

✅ **FULL REPRODUCIBILITY CONFIRMED** - All 9 breakthrough representations from legal-distance v8 fractal validation PASS both adversarial gates on frozen harness v3.

## Adversarial Gate Results (LangDom < 0.85, JuristPref > 0.5)

| Representation | LangDom | LD-Pass | JuristPref | JP-Pass | Both | Verdict |
|----------------|---------|---------|------------|---------|------|---------|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4919** | ✓ | **0.8374** | ✓ | ✓ | **PASS** |
| **cited_decisions_tfidf_outcome_hybrid_0.7** | **0.4938** | ✓ | **0.7865** | ✓ | ✓ | **PASS** |
| **multilingual_e5_small_pretrained** | **0.4877** | ✓ | **0.7017** | ✓ | ✓ | **PASS** (hierarchy collapse) |
| **cited_decisions_tfidf_proc_pairs (FRESH)** | **0.6100** | ✓ | **0.6889** | ✓ | ✓ | **PASS** |
| **cited_decisions_tfidf** | **0.6100** | ✓ | **0.6889** | ✓ | ✓ | **PASS** |
| **linear_metric_epoch4** | **0.6805** | ✓ | **0.6847** | ✓ | ✓ | **PASS** |
| **mahalanobis_metric_epoch4** | **0.6843** | ✓ | **0.6781** | ✓ | ✓ | **PASS** |
| **hybrid_stabilized_epoch1** | **0.6704** | ✓ | **0.6656** | ✓ | ✓ | **PASS** |
| **cited_decisions_tfidf_joint_pca** | **0.6237** | ✓ | **0.6472** | ✓ | ✓ | **PASS** |
| **cited_decisions_tfidf_mean_center** | **0.6595** | ✓ | **0.5997** | ✓ | ✓ | **PASS** |
| center_projected_64dim (reference) | 0.7664 | ✓ | 0.5121 | ✓ | ✓ | **PASS** |
| center_projected_768 | 0.7738 | ✓ | 0.4912 | ✗ | ✗ | **FAIL** |
| cited_decisions_tfidf_procrustes | 0.7121 | ✓ | 0.3603 | ✗ | ✗ | **FAIL** |
| cited_decisions_tfidf_cca | 0.8897 | ✗ | 0.2143 | ✗ | ✗ | **FAIL** |

**9/9 Breakthrough representations PASS both adversarial gates** ✅

## Design Patterns Validated

### High-Purity (Metric Learning Family)
- **linear_metric_epoch4**: JP=0.6847, LangDom=0.6805, Jurivoc L0=0.6895, Scale=0.7037
- **mahalanobis_metric_epoch4**: JP=0.6781, LangDom=0.6843, Jurivoc L0=0.7041, Scale=0.7154 (BEST)
- **hybrid_stabilized_epoch1**: JP=0.6656, LangDom=0.6704, Jurivoc L0=0.6360, Cross-lang=0.2360 (BEST)

### High-Advantage (Citation/Outcome Family)
- **cited_decisions_tfidf_outcome_hybrid_0.5**: JP=0.8374, LangDom=0.4919, HierAdv=+0.2144 (BEST PRODUCTION)
- **cited_decisions_tfidf_outcome_hybrid_0.7**: JP=0.7865, LangDom=0.4938, HierAdv=+0.2740 (BEST FRACTAL)
- **cited_decisions_tfidf**: JP=0.6889, LangDom=0.6100, ImpRate=92.3%, HierAdv=+0.1174
- **cited_decisions_tfidf_proc_pairs**: LOSSLESS cross-lingual (JP=0.6889, LangDom=0.6100, Jurivoc L0=0.2542)

## Additional Benchmarks

| Representation | Jurivoc L0 NMI | Scale Stability | Cross-lang Recall@10 | Fractal ImpRate |
|----------------|----------------|-----------------|---------------------|-----------------|
| linear_metric_epoch4 | 0.6895 | 0.7037 | 0.2114 | 72.0% |
| mahalanobis_metric_epoch4 | 0.7041 | 0.7154 | 0.2083 | 65.2% |
| hybrid_stabilized_epoch1 | 0.6360 | 0.7067 | 0.2360 | 73.8% |
| cited_decisions_tfidf | 0.2458 | 0.5946 | 0.2017 | 92.3% |
| cited_outcome_hybrid_0.5 | 0.1165 | 0.6438 | 0.2339 | 84.9% |
| cited_outcome_hybrid_0.7 | 0.1635 | 0.6454 | 0.2299 | 89.4% |
| cited_decisions_tfidf_proc_pairs | 0.2542 | 0.6013 | 0.2013 | 93.6% |

## Factory Direction v9 Objective Status

| Objective | Status | Evidence |
|-----------|--------|----------|
| 1. Full corpus scale (192k) | ⏳ BLOCKED | Corpus lane dependency |
| 2. Citation role modeling (2,988) | ✅ COMPLETE | Legal-distance v7 + frozen harness validation |
| 3. Legal embeddings fine-tuning | ⏳ BLOCKED | GPU + hierarchy preservation loss needed |
| 4. Jurist human study (5-10) | ⏳ BLOCKED | Jurist recruitment needed |
| 5. Cross-lingual alignment deeper | ✅ COMPLETE | v10 cross-lingual + proc_pairs LOSSLESS |
| 6. User corpus import evaluation | ✅ COMPLETE | 45/45 tests PASS |

## Test Suite Results

| Test | Status |
|------|--------|
| test_frozen_harness_v3_reproducibility | ✅ PASSED |
| test_cross_lingual_alignment_v10 | ✅ PASSED |
| test_boilerplate_resistance_real | ✅ PASSED |

## Key Confirmation

**FRESH PROC PAIRS COMPUTATION CONFIRMED LOSSLESS:**
- Fresh Procrustes on 526 language pairs: LangDom=0.6100, JuristPref=0.6889
- Matches base cited_decisions_tfidf exactly (LangDom=0.6100, JuristPref=0.6889)
- Resolves audit discrepancy from stale pre-saved embedding

## Provenance

- **Results file:** `evaluation/results/v3_extended/evaluation_v9_comprehensive_results.json`
- **Global seed:** 42
- **Config hash:** 4323f833fa72366a
- **Embeddings source:** `/tmp/lex_accepted` (ACCEPTED lane artifacts)
- **Metadata source:** `evaluation/data/bger_expanded_1200_metadata.jsonl` (1200 decisions)

## Recommendation

**BLOCKED_ON_DEPENDENCIES** - Evaluation v9 comprehensive objectives 2, 5, 6 COMPLETE. Objectives 1, 3, 4 blocked on external dependencies (corpus lane, GPU, jurist recruitment). No further same-cycle work justified. Next cycle requires factory direction v10+ with resolved dependencies.
