# Evaluation Lane v29 — Audit-Ready Snapshot

**Date:** 2026-10-02T23:15:00Z  
**Factory Direction Version:** 29  
**Lane:** evaluation  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** RUN (monitoring for new representations)  
**Continue Recommended:** true  
**Accepted Run ID:** `eval_174k_formal_suite_20260930_233546`  
**Monitor Check Count:** 282  
**Frozen Adversarial Config Hash:** `b51701f5a9c11692`  
**Formal Suite Config Hash:** `4323f833fa72366a`

---

## Executive Summary

The evaluation lane has **COMPLETED all three v29 mandated deliverables** for the TF-IDF family (8 representations at 174k scale) and maintains **VERIFIED, AUDIT-READY infrastructure** for evaluating new representations as they land from legal-distance.

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| **1. Full 12-benchmark formal suite at 174k on all 8 TF-IDF reps** | ✅ COMPLETE & REPRODUCIBLE | Frozen harness v3, HNSW artifact fixed via exact k-NN on stratified subsample (n=2000), config hash `b51701f5a9c11692` |
| **2. Citation heritage benchmark on frozen 1,020-pair pool** | ✅ COMPLETE | All 8 TF-IDF reps FAIL recall@10 < 0.2; corpus citation ID resolution 2,019/2,105 (95.9%) |
| **3. v17b label normalization generalization to 174k fine-grained labels** | ✅ COMPLETE (NEGATIVE) | Does NOT generalize: hierarchy=1.0x for ALL reps, zoom_fine=0.83-0.99x (degradation for 4/8), legal_area=~1.0x |

**No same-question cycle justified for TF-IDF.** Evaluation infrastructure is **VERIFIED and AUDIT-READY**.

---

## Orchestration/Validation Failure Diagnosis (RESOLVED)

**Issue:** Prior state file drift between `evaluation.json` and `evaluation_state.json` — one showed `cycle_status=COMPLETED, continue_recommended=false` while factory direction v29 question spans "as representations land" requiring `RUN` status.

**Resolution Timeline:**
- 2026-10-01: State file consistency fix — both files aligned to `cycle_status=COMPLETED, continue_recommended=false`
- 2026-10-01T15:38: Audit CYCLE_36825090988 correction — factory direction v29 explicitly states "as representations land"; TF-IDF complete but lane question ongoing
- 2026-10-01T15:38: Both state files corrected to `cycle_status=RUN, continue_recommended=true`
- **2026-10-02T23:15: Current verification confirms both state files CONSISTENT**

**Root Cause:** Misinterpretation of "COMPLETED" — deliverables for *current representations* are complete, but lane question explicitly continues "as representations land" per factory direction v29.

**Fix Verified:** Both state files now show `cycle_status=RUN, continue_recommended=true, evidence_tier=ACCEPTED, direction_version=29`.

---

## Adversarial Re-Verification (2026-10-02T23:12-23:14)

**Method:** Exact k-NN on stratified subsample (n=2000, seed=42) from 90,632 valid decisions (branch ≠ unknown)  
**Config Hash Reference:** `b51701f5a9c11692` (frozen harness v3)  
**Embedding Shape Note:** 175,440 vs metadata 173,963 — shape mismatch handled by valid-subset filtering

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---------------|-------------------|-------------------|------------|
| cited_decisions_tfidf | 0.4917 ✅ | 0.7075 ✅ | ✅ |
| outcome_tfidf | 0.5078 ✅ | 0.6660 ✅ | ✅ |
| regeste_tfidf | 0.5111 ✅ | 0.6145 ✅ | ✅ |
| full_text_tfidf_light | 0.4854 ✅ | 0.7080 ✅ | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5 (PRODUCTION DEFAULT)** | **0.4895 ✅** | **0.7265 ✅** | **✅** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 ✅ | 0.7195 ✅ | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 ✅ | 0.7140 ✅ | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 ✅ | 0.7120 ✅ | ✅ |

**Summary:** All 8 TF-IDF representations PASS both adversarial gates.  
**LangDom range:** 0.485–0.511 (all < 0.85 threshold)  
**Jurist range:** 0.615–0.727 (all > 0.5 threshold)

---

## Infrastructure Verification

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite runner (v25) | ✅ OPERATIONAL | Config hash `4323f833fa72366a`, 12-benchmark suite |
| Citation heritage pipeline | ✅ READY | Frozen 1,020-pair pool (95.9% corpus resolution) |
| v17b normalization pipeline | ✅ READY | Differential effect reproduced across all 8 TF-IDF reps |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN on stratified subsample avoids masking |
| Scalable NN infrastructure | ✅ OPERATIONAL | sklearn exact for adversarial, HNSW for full-corpus |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | Check count: 282 |

---

## Awaited Representations from Legal-Distance (174k Scale)

| Representation Family | Status | Details |
|----------------------|--------|---------|
| **Dense embeddings** | ❌ NOT YET AVAILABLE | 22/26 years (2000-2021, ~144k decisions) checkpointed; ONLY 3/26 years (2000-2002, ~19k) ACCEPTED; concatenation to 174k NOT DONE; center_projected FAIL at all tested scales (LangDom ~0.83-0.99) |
| **Citation roles** | ❌ NOT YET AVAILABLE | Available in legal-distance v6 but not at 174k scale |
| **Linear hybrids** | 🟡 PARTIAL EVIDENCE | PASS at 22-year/144k scale: optimal w=0.4 for `cited_decisions_tfidf` (JP=0.6725, LangDom=0.6539), w=0.3 for `outcome_hybrid_0.5` (JP=0.6605, LangDom=0.6395); legal-distance v12/v13/v14 REPRODUCED at 1k scale; **await 174k concatenation** |

**Legal-distance checkpoint progress:** 22/26 years (2000-2021) in checkpoints; years 2022-2026 missing (~29k decisions). Blocked on: bger_↔bge_ ID mapping, parquet availability for 2022-2026, GPU unavailability for finetuning.

---

## Key Negative Results Preserved (First-Class Evidence)

1. **Citation heritage at 174k:** ALL 8 TF-IDF reps FAIL recall@10 < 0.2 — citation signals do not recover citation heritage at corpus scale
2. **v17b label normalization at 174k:** Does NOT generalize to fine-grained labels; zoom coherence DEGRADES for 4/8 reps (production default zoom_fine ratio 0.8827)
3. **Dense embeddings (v6, 12k scale):** FAIL adversarial (LangDom=0.99, JP~0.04), cluster by language not law
4. **Center-projected dense:** FAIL adversarial at all tested scales (12k, 92k, 122k, 130k, 144k) — LangDom ~0.83-0.99
5. **v18 coarse hierarchy:** Even at 4-label branch level, best purity 0.65 < 0.7 threshold — fundamental hierarchy limitation
6. **Boilerplate resistance:** All representations FAIL (resistance_score ≈ -0.74 to -0.92) — proxy measures language dominance, not procedural boilerplate

---

## Two-Mode Tradeoff Reproduced Across All Scales

| Mode | Language Dominance | Jurist Preference | Citation Independence |
|------|-------------------|-------------------|----------------------|
| **Citation/Outcome (TF-IDF hybrids)** | ~0.48 | ~0.73 | ~14% |
| **Semantic Embeddings (center_projected)** | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| **Metric Learning** | ~0.58-0.61 | ~0.53-0.61 | ~34-37% |
| **Linear Hybrids (optimal weight)** | ~0.64-0.65 | ~0.66-0.67 | Intermediate |

**No single representation dominates all metrics.** Citation-based signals dominate jurist preference at 174k scale. Dense embeddings recover citation heritage better (AUC 0.79-0.85) but fail jurist gate due to language dominance.

---

## Evidence References (All Verified Extant)

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_3year_formal_suite/evaluation_3year_dense_formal_suite_latest.json`
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `evaluation/results/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- `reports/evaluation/cycle_174k_formal_suite_completion.md`
- `reports/evaluation/EVALUATION_V29_CYCLE_REPORT_20261002_FINAL.md`

---

## State Files (Both Consistent)

**`evaluation/state/evaluation_state.json`:**
```json
{
  "lane": "evaluation",
  "direction_version": 29,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "RUN",
  "continue_recommended": true,
  "accepted_run_id": "eval_174k_formal_suite_20260930_233546",
  "monitor_check_count": 282,
  "last_verification": "2026-10-02T23:15:00Z"
}
```

**`evaluation/state/evaluation.json`:**
```json
{
  "lane": "evaluation",
  "direction_version": 29,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "RUN",
  "continue_recommended": true,
  "accepted_run_id": "eval_174k_formal_suite_20260930_233546",
  "monitor_check_count": 282,
  "monitor_last_check": "2026-10-02T23:15:00Z"
}
```

---

## Recommendation

**CONTINUE** — Lane remains RUN per factory direction "as representations land".

- ✅ TF-IDF family (8 reps) evaluation at 174k is **COMPLETE and REPRODUCIBLE**
- ✅ Evaluation infrastructure is **FULLY OPERATIONAL and AUDIT-READY**
- ✅ Monitor active (check 282) — no new awaited representations detected at 174k
- 🟡 **AWAITING:** 174k-scale dense embeddings, citation roles, and linear hybrids from legal-distance
- 📍 Next factory direction decision point: when legal-distance delivers 174k concatenated representations

---

## Compliance with Research Protocol

✅ Hypothesis, baseline, and success rules frozen before measurement  
✅ Claim-bearing sample (173,963 decisions) frozen  
✅ Negative results preserved as first-class evidence  
✅ Strong baselines compared (TF-IDF citation-based vs text-based vs dense)  
✅ Machine-readable state + human-readable report  
✅ Provenance preserved for all claim-bearing outputs  
✅ No benchmark weakened after seeing results  
✅ No fabrication of data, labels, or results  

---

**Snapshot Status:** AUDIT-READY  
**Generated:** 2026-10-02T23:15:00Z  
**Factory Direction:** v29