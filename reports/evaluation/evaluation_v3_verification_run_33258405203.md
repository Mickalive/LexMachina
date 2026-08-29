# Evaluation Lane v3 — Final Verification Report (GitHub Run 33258405203)

**Factory Direction Version:** 6  
**Evaluation Version:** v3 (Frozen)  
**Config Hash:** `4323f833fa72366a`  
**Global Seed:** 42  
**GitHub Run:** 33258405203  
**Date:** 2026-08-29  
**Status:** FULLY REPRODUCED — All frozen harness results match prior verified runs

---

## Executive Summary

This run **independently verifies** the frozen Evaluation Lane v3 harness (config hash `4323f833fa72366a`, seed=42) in a fresh environment. All three core evaluation scripts reproduce **identical results** to the original GitHub runs 33232234741 and 33240972425, and the local reproduction on 2026-08-29.

**Verification Result: ✅ COMPLETE REPRODUCIBILITY CONFIRMED**

---

## Verification Details

### 1. Frozen Adversarial Evaluation Harness (`evaluation_v3_harness.py`)

| Representation | LangDom | LD-Pass | Jurist | JP-Pass | Both Gates | Verdict | Jurivoc L0 | Scale | Boiler | ImpRate |
|---|---|---|---|---|---|---|---|---|---|---|
| linear_metric_epoch4 | 0.6805 | ✅ | 0.6847 | ✅ | ✅ | PASS | 0.6895 | 0.7037 | -0.8879 | 72.0% |
| mahalanobis_metric_epoch4 | 0.6843 | ✅ | 0.6781 | ✅ | ✅ | PASS | 0.7041 | 0.7154 | -0.8954 | 65.2% |
| hybrid_stabilized_epoch1 | 0.6704 | ✅ | 0.6656 | ✅ | ✅ | PASS | 0.6360 | 0.7067 | -0.9194 | 73.8% |
| hybrid_v2_epoch3 | 0.7115 | ✅ | 0.5988 | ✅ | ✅ | PASS | 0.7415 | 0.7092 | -0.9144 | 59.6% |
| **center_projected_64dim** | **0.7664** | ✅ | **0.5121** | ✅ | ✅ | **PASS** | 0.0653 | 0.7071 | -0.9012 | 64.7% |
| center_projected_768 | 0.7738 | ✅ | 0.4912 | ❌ | ❌ | FAIL | 0.0945 | 0.7104 | -0.8959 | 60.0% |

**Config Hash Match:** ✅ `4323f833fa72366a` (identical)  
**Global Seed Enforced:** ✅ 42  
**All Adversarial Scores Match:** ✅ Exact to 4 decimal places  
**All Supplementary Scores Match:** ✅ Exact match  

---

### 2. Cited Decisions TF-IDF Adversarial Validation (`run_cited_decisions_adversarial.py`)

| Representation | LangDom | LD-Pass | Jurist | JP-Pass | Both Gates | Verdict |
|---|---|---|---|---|---|---|
| **cited_decisions_tfidf** | **0.6107** | ✅ | **0.6922** | ✅ | ✅ | **PASS** |
| cited_decisions_tfidf_hybrid_cp768_0.7 | 0.6477 | ✅ | 0.6764 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.7 | 0.6518 | ✅ | 0.6564 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.5 | 0.6838 | ✅ | 0.6280 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp768_0.5 | 0.7062 | ✅ | 0.6105 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.3 | 0.7483 | ✅ | 0.5346 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp768_0.3 | 0.7604 | ✅ | 0.5254 | ✅ | ✅ | PASS |
| **center_projected_64dim** | **0.7664** | ✅ | **0.5121** | ✅ | ✅ | **PASS** |
| center_projected_768 | 0.7738 | ✅ | 0.4912 | ❌ | ❌ | FAIL |

**Key Finding Reproduced:** `cited_decisions_tfidf` achieves **highest jurist preference (0.6922)** and **best language invariance (0.6107)** among ALL unsupervised representations — competitive with supervised metric learning (0.6847) WITHOUT training.

**All 6 hybrids PASS both adversarial gates** — robust parameter region confirmed.

---

### 3. Real Boilerplate Resistance Test (`run_boilerplate_resistance_real.py`)

| Signal | Neighbor Preservation | Resistance Score | Proxy Rate |
|---|---|---|---|
| sachverhalt_tfidf | 0.9325 | 0.0675 | 1.0000 |
| erwaegungen_tfidf | 0.9325 | 0.0675 | 1.0000 |
| outcome_tfidf | 0.8917 | 0.1083 | 1.0000 |
| full_text_tfidf | 0.9325 | 0.0675 | 1.0000 |
| sachverhalt+erwaegungen | 0.9325 | 0.0675 | 1.0000 |

**Mean Full Text Length:** 16,410 chars  
**Mean Clean Text Length:** 15,795 chars  
**Mean Reduction:** 5.88%

**Finding Confirmed:** Boilerplate resistance remains a **fundamental unsolved problem** — neighbors are stable (>89% preservation when boilerplate removed) but dominated by language artifacts (100% decisions have >80% same-language neighbors).

---

## Evidence Tier Assessment (This Run)

| Finding | Evidence Tier | Provenance |
|---|---|---|
| Frozen harness reproducibility | **REPRODUCED** | GitHub runs 33232234741, 33235485388, 33240972425, **33258405203**, local |
| center_projected_64dim only baseline passing both gates | **REPRODUCED** | v3_evaluation_results.json, this run |
| Metric learning breakthrough (linear, mahalanobis) | **REPRODUCED** | v3_evaluation_results.json, legal-distance v6, this run |
| cited_decisions_tfidf best unsupervised | **REPRODUCED** | cited_decisions_validation, legal-distance v6, this run |
| All 6 hybrids pass both gates | **REPRODUCED** | cited_decisions_validation, this run |
| Signal ablation all FAIL | **REPRODUCED** | v6_signal_ablation, legal-distance v6, this run |
| Boilerplate resistance negative (harness) | **REPRODUCED** | v3_evaluation_results.json, this run |
| Boilerplate resistance real text test | **EXPLORATORY** | v3_boilerplate_real_results.json (this run) |
| Cross-language retrieval metric learning PASS | **REPRODUCED** | v3_evaluation_results.json, this run |
| Scale stability good | **REPRODUCED** | v3_evaluation_results.json, this run |

---

## Lane State Confirmation

```json
{
  "lane": "evaluation",
  "direction_version": 6,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "evaluation_v3_frozen_harness_33232234741",
  "github_run": "33258405203",
  "timestamp": "2026-08-29T14:55:08Z",
  "config_hash": "4323f833fa72366a",
  "global_seed": 42,
  "next_recommendation": "PRODUCTIZE"
}
```

---

## Conclusion

**Evaluation Lane v3 is COMPLETE and FULLY REPRODUCIBLE.**

The frozen evaluation harness has validated:
- ✅ Production default (`center_projected_64dim`) — only pre-trained representation passing both adversarial gates
- ✅ Three independent breakthrough representation families (linear metric, Mahalanobis, stabilized hybrid) — all beat production default on jurist preference (+15-34% relative) and pass both adversarial gates
- ✅ Zero-shot citation signal (`cited_decisions_tfidf`) — competitive with supervised methods (JP=0.6922 vs 0.6847)
- ✅ All 6 hybrids of cited_decisions_tfidf + center_projected PASS both gates — best production hybrid: `cited_decisions_tfidf_hybrid_cp64_0.7` (JP=0.6564, LangDom=0.6518)
- ✅ Signal ablation confirmed — only metric learning and stabilized hybrids produce adversarial-robust representations on center_projected baseline
- ✅ Systematic boilerplate resistance limitation documented (all representations negative)
- ✅ Scale stability good (0.70-0.72), cross-language retrieval passes for breakthrough representations, Jurivoc alignment passes for metric learning/hybrids

**No further cycles under the SAME factory-direction question are justified** (`continue_recommended: false`).

**Next factory direction (v7) should address:**
1. **Full Corpus Scale Evaluation (192k decisions)**
2. **Citation Role Modeling Evaluation** (when citation ID resolution pipeline ready)
3. **Legal Embeddings Fine-Tuning Evaluation** (multilingual-e5-small on Swiss legal corpus)
4. **Jurist Human Study** (framework ready, needs 5-10 Swiss jurists)
5. **Boilerplate Resistance Architecture** (fundamental research beyond embeddings)
6. **User Corpus Import Evaluation**

---

*Report generated by Evaluation Lane v3 Frozen Harness — Config Hash: 4323f833fa72366a — Seed: 42 — GitHub Run: 33258405203*