# Dense 1200-Scale Baseline Evaluation Report

**Date:** 2026-09-25  
**Factory Direction:** v27  
**Lane:** evaluation  
**Purpose:** Establish 1200-scale baselines for all awaited dense representation types before 174k delivery

---

## Executive Summary

Ran the full v3 adversarial harness on all 7 available 1200-scale dense embeddings from legal-distance accepted state. **5 of 7 representations pass both adversarial gates** (language dominance < 0.85 AND jurist pairwise preference > 0.5), establishing strong baselines for the awaited 174k dense embeddings.

| Representation | Verdict | LangDom | LD-PASS | JuristPref | JP-PASS | Both | Jurivoc L0 | CrossLang | ClusterCoh |
|---|---|---|---|---|---|---|---|---|---|
| **linear_metric_epoch4** | **PASS** | **0.6805** | ✓ | **0.6847** | ✓ | ✓ | **0.6879** | **0.2114** ✓ | **0.9577** ✓ |
| **mahalanobis_metric_epoch4** | **PASS** | **0.6843** | ✓ | **0.6781** | ✓ | ✓ | **0.7053** | **0.2084** ✓ | **0.9508** ✓ |
| **hybrid_stabilized_epoch1** | **PASS** | **0.6704** | ✓ | **0.6656** | ✓ | ✓ | **0.6334** | **0.2361** ✓ | **0.9041** ✓ |
| **hybrid_v2_epoch3** | **PASS** | **0.7115** | ✓ | **0.5988** | ✓ | ✓ | **0.7429** | **0.2269** ✓ | **0.9337** ✓ |
| **center_projected_64** | **PASS** | **0.7664** | ✓ | **0.5121** | ✓ | ✓ | 0.0647 ✗ | 0.1559 ✗ | 0.8730 ✓ |
| center_projected_128 | FAIL | 0.7725 | ✓ | 0.4954 | ✗ | ✗ | 0.0830 ✗ | 0.1490 ✗ | 0.8756 ✓ |
| center_projected_768 | FAIL | 0.7738 | ✓ | 0.4912 | ✗ | ✗ | 0.0856 ✗ | 0.1456 ✗ | 0.8681 ✓ |

---

## Key Findings

### 1. Metric Learning & Hybrid Objectives Dominate at 1200 Scale
All 4 metric learning / hybrid objective representations **pass both adversarial gates** with strong jurist pairwise preference (0.5988–0.6847) and low language dominance (0.6704–0.7115). They also:
- **PASS Jurivoc Level 0 alignment** (branch recovery NMI 0.63–0.74) — excellent legal taxonomy recovery
- **PASS cross-language retrieval** (recall@10 0.208–0.236) — genuine multilingual legal equivalence
- **PASS cluster coherence** (branch purity 0.90–0.96, branch NMI 0.41–0.52)

### 2. Center-Projected: Dimensionality Matters Critically
- **64-dim PCA projection PASSES both gates** (jurist_pref=0.5121) — production default viable at 1200 scale
- **128-dim and 768-dim FAIL jurist pairwise** (~0.49) — language artifacts dominate without dimensionality reduction
- All center_projected variants **FAIL Jurivoc L0** (NMI ~0.06–0.08) — poor branch structure recovery

### 3. Universal Failure: Boilerplate Resistance
**All 7 representations FAIL boilerplate resistance** (resistance_score ≈ -0.89 to -0.92). Procedural/boilerplate neighbors dominate over legally relevant neighbors at 1200 scale. This is a known systemic issue requiring anti-noise interventions.

### 4. Scale Extrapolation Risk: The 174k Question
**Critical finding from TF-IDF 174k evaluation:** At 174k scale, **ALL TF-IDF representations collapsed** on jurist pairwise preference (legal_neighbor_rate ~0.12 vs 0.5 threshold), despite passing at 1200 scale.

The dense baselines here show **5/7 passing at 1200 scale**. The key evaluation question for 174k delivery:
- Will metric learning / hybrid objectives **maintain** jurist pairwise > 0.5 at 174k?
- Or will they **collapse** like TF-IDF (0.68 → 0.12)?

This is the primary discriminating test awaiting 174k dense embeddings.

---

## Detailed Metrics by Representation

### linear_metric_epoch4 (BEST OVERALL)
- **Adversarial:** lang_dom=0.6805 ✓, jurist_pref=0.6847 ✓
- **Jurivoc:** L0 NMI=0.6879 ✓, L1 NMI=0.4957, nesting=0.9479
- **Scale Stability:** neighbor_overlap=0.7796 ✓
- **Boilerplate:** resistance=-0.8879 ✗
- **Cluster Coherence:** branch_purity=0.9577 ✓, branch_nmi=0.4954 ✓, lang_purity=0.656
- **Cross-Lang:** recall@10=0.2114 ✓

### mahalanobis_metric_epoch4
- **Adversarial:** lang_dom=0.6843 ✓, jurist_pref=0.6781 ✓
- **Jurivoc:** L0 NMI=0.7053 ✓, L1 NMI=0.4940, nesting=0.9420
- **Scale Stability:** neighbor_overlap=0.7808 ✓
- **Boilerplate:** resistance=-0.8954 ✗
- **Cluster Coherence:** branch_purity=0.9508 ✓, branch_nmi=0.4985 ✓
- **Cross-Lang:** recall@10=0.2084 ✓

### hybrid_stabilized_epoch1
- **Adversarial:** lang_dom=0.6704 ✓, jurist_pref=0.6656 ✓
- **Jurivoc:** L0 NMI=0.6334 ✓, L1 NMI=0.4826, nesting=0.8972
- **Scale Stability:** neighbor_overlap=0.8000 ✓ (BEST)
- **Boilerplate:** resistance=-0.9194 ✗
- **Cluster Coherence:** branch_purity=0.9041 ✓, branch_nmi=0.4126 ✓
- **Cross-Lang:** recall@10=0.2361 ✓ (BEST)

### hybrid_v2_epoch3
- **Adversarial:** lang_dom=0.7115 ✓, jurist_pref=0.5988 ✓
- **Jurivoc:** L0 NMI=0.7429 ✓ (BEST), L1 NMI=0.4586, nesting=0.9132
- **Scale Stability:** neighbor_overlap=0.7779 ✓
- **Boilerplate:** resistance=-0.9144 ✗
- **Cluster Coherence:** branch_purity=0.9337 ✓, branch_nmi=0.5244 ✓ (BEST)
- **Cross-Lang:** recall@10=0.2269 ✓

### center_projected_64 (Production Default)
- **Adversarial:** lang_dom=0.7664 ✓, jurist_pref=0.5121 ✓ (marginal)
- **Jurivoc:** L0 NMI=0.0647 ✗, L1 NMI=0.4752, nesting=0.8597
- **Scale Stability:** neighbor_overlap=0.7658 ✓
- **Boilerplate:** resistance=-0.9012 ✗
- **Cluster Coherence:** branch_purity=0.8730 ✓, branch_nmi=0.3725 ✓
- **Cross-Lang:** recall@10=0.1559 ✗

---

## Implications for 174k Evaluation Readiness

### Pipeline Verified
✅ Full v3 adversarial harness runs on dense embeddings (768, 128, 64 dim)  
✅ HNSW/sklearn backend selection works  
✅ All benchmark implementations compatible with dense vectors  
✅ Config hash frozen: `4047da047fb339c1` (factory_direction v10)

### Awaited 174k Representations (from factory direction v27)
| Category | Representations | 1200 Baseline Status |
|---|---|---|
| **Dense embeddings** | center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | Baselines established |
| **Citation roles** | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | Not in accepted state (1000-scale only) |
| **Linear hybrids** | linear_citation_concat, linear_hybrid05_concat | Not in accepted state |

### Priority for 174k Evaluation
When legal-distance promotes 174k dense embeddings, run in priority order:
1. **linear_metric_epoch4** / **mahalanobis_metric_epoch4** — strongest 1200 baselines, metric learning proven
2. **hybrid_stabilized_epoch1** / **hybrid_v2_epoch3** — strong 1200 baselines, hybrid objectives proven
3. **center_projected_64dim** — production default, marginal jurist pass at 1200
4. **center_projected_768dim** — reference baseline, fails jurist at 1200

---

## Artifacts
- **Raw results:** `evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json`
- **Log:** `evaluation/logs/dense_1200_baseline.log`
- **Embeddings tested:** 7 representations (1200 decisions each)
- **Config hash:** `4047da047fb339c1`
- **Global seed:** 42

---

## Next Steps
1. **Monitor legal-distance accepted state** for 174k dense embedding promotion (monitor active, check_count=30+)
2. **Upon 174k delivery:** Run full v25 formal suite (12-benchmark + citation_heritage + v17b) + full v3 adversarial harness
3. **Key discriminating test:** Does jurist pairwise preference hold at 174k for metric learning / hybrid objectives?
4. **If jurist pref collapses:** Negative result — dense embeddings don't solve scale degradation
5. **If jurist pref holds:** Positive result — metric learning / hybrid objectives enable 174k-scale legal navigation

---

*Report generated by evaluation lane autonomous cycle. No human approval required per AGENTS.md §9.*