# Evaluation Lane v29 Cycle Report

**Date:** 2026-10-02  
**Factory Direction Version:** 29  
**Lane:** evaluation  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** RUN (monitoring for new representations)  
**Continue Recommended:** true

---

## Executive Summary

The evaluation lane has **COMPLETED all three v29 mandated deliverables** for the TF-IDF family (8 representations at 174k scale) and maintains **VERIFIED, AUDIT-READY infrastructure** for evaluating new representations as they land from legal-distance.

### Deliverables Status

| Deliverable | Status | Details |
|------------|--------|---------|
| **1. Full 12-benchmark formal suite at 174k on all 8 TF-IDF reps** | ✅ COMPLETE & REPRODUCIBLE | Frozen harness v3, HNSW artifact fixed via exact k-NN on stratified subsample (n=2000), config hash `b51701f5a9c11692` |
| **2. Citation heritage benchmark on frozen 1,020-pair pool** | ✅ COMPLETE | All 8 TF-IDF reps FAIL recall@10 < 0.2; corpus citation ID resolution 2,019/2,105 (95.9%) |
| **3. v17b label normalization generalization to 174k fine-grained labels** | ✅ COMPLETE (NEGATIVE) | Does NOT generalize: hierarchy=1.0x for ALL reps, zoom_fine=0.83-0.99x (degradation for 4/8), legal_area=~1.0x |

**No same-question cycle justified for TF-IDF.** Evaluation infrastructure is **VERIFIED and AUDIT-READY**.

---

## Adversarial Re-Verification (2026-10-02)

**Method:** Exact k-NN on stratified subsample (n=2000, seed=42) from 90,632 valid decisions (branch ≠ unknown)  
**Config Hash Reference:** `b51701f5a9c11692` (frozen harness v3)  
**Evidence:** `evaluation/results/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---------------|-------------------|-------------------|------------|
| cited_decisions_tfidf | 0.4753 ✅ | 0.8670 ✅ | ✅ |
| outcome_tfidf | 0.4754 ✅ | 0.8780 ✅ | ✅ |
| regeste_tfidf | 0.4613 ✅ | 0.8465 ✅ | ✅ |
| full_text_tfidf_light | 0.4729 ✅ | 0.9115 ✅ | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5 (PRODUCTION DEFAULT)** | **0.4742 ✅** | **0.8780 ✅** | **✅** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4750 ✅ | 0.8790 ✅ | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4765 ✅ | 0.9190 ✅ | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4764 ✅ | 0.9160 ✅ | ✅ |

**Summary:** All 8 TF-IDF representations PASS both adversarial gates.  
**LangDom range:** 0.461–0.477 (all < 0.85 threshold)  
**Jurist range:** 0.847–0.919 (all > 0.5 threshold)

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
| Monitor script | ✅ ACTIVE | Check count: 276, last check: 2026-10-02T04:45 |

---

## Awaited Representations from Legal-Distance (174k Scale)

| Representation Family | Status | Details |
|----------------------|--------|---------|
| **Dense embeddings** | ❌ NOT YET AVAILABLE | 20/26 years (2000-2019) checkpointed (~130k decisions); ONLY 3/26 years (2000-2002, ~19k) ACCEPTED; concatenation to 174k NOT DONE; center_projected FAIL at all tested scales (LangDom ~0.86-0.99) |
| **Citation roles** | ❌ NOT YET AVAILABLE | Available in legal-distance v6 but not at 174k scale |
| **Linear hybrids** | 🟡 PARTIAL EVIDENCE | PASS at 19-year/122k scale: `linear_citation_concat` (LangDom=0.767, JP=0.545), `linear_hybrid05_concat` (LangDom=0.778, JP=0.540); legal-distance v12/v13/v14 REPRODUCED at 1k scale; **await 174k concatenation** |

**Legal-distance checkpoint progress:** 20/26 years (2000-2019) in checkpoints; years 2020-2026 not yet processed. Blocked on: data acquisition (corpus lane PAUSED), bger_↔bge_ ID mapping, GPU unavailability for finetuning.

---

## Key Negative Results Preserved

1. **Citation heritage at 174k:** ALL 8 TF-IDF reps FAIL recall@10 < 0.2 — citation signals do not recover citation heritage at corpus scale
2. **v17b label normalization at 174k:** Does NOT generalize to fine-grained labels; zoom coherence DEGRADES for 4/8 reps (production default zoom_fine ratio 0.8827)
3. **Dense embeddings (v6, 12k scale):** FAIL adversarial (LangDom=0.99, JP~0.04), cluster by language not law
4. **Center-projected dense:** FAIL adversarial at all tested scales (12k, 100k, 122k) — LangDom ~0.86-0.99
5. **v18 coarse hierarchy:** Even at 4-label branch level, best purity 0.65 < 0.7 threshold — fundamental hierarchy limitation
6. **Boilerplate resistance:** All representations FAIL (resistance_score ≈ -0.74 to -0.92) — proxy measures language dominance, not procedural boilerplate

---

## Two-Mode Tradeoff Reproduced

| Mode | Language Dominance | Jurist Preference | Citation Independence |
|------|-------------------|-------------------|----------------------|
| **Citation/Outcome (TF-IDF hybrids)** | ~0.47 | ~0.73 | ~14% |
| **Semantic Embeddings (center_projected)** | ~0.86 | ~0.36-0.39 | ~37% |
| **Metric Learning** | ~0.58-0.61 | ~0.53-0.61 | ~34-37% |

**No single representation dominates all metrics.** Citation-based signals dominate jurist preference at 174k scale.

---

## Recommendation

**CONTINUE** — Lane remains RUN per factory direction "as representations land". 

- TF-IDF family (8 reps) evaluation at 174k is **COMPLETE and REPRODUCIBLE**
- Evaluation infrastructure is **FULLY OPERATIONAL and AUDIT-READY**
- Monitor active (check 276) — no new awaited representations detected
- **AWAITING:** 174k-scale dense embeddings, citation roles, and linear hybrids from legal-distance
- Next factory direction decision point: when legal-distance delivers 174k concatenated representations

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_3year_formal_suite/evaluation_3year_dense_formal_suite_latest.json`
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `evaluation/results/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- `reports/evaluation/cycle_174k_formal_suite_completion.md`

---

## State Files Updated

- `evaluation/state/evaluation.json` — monitor_check_count: 276, latest adversarial re-verification recorded
- `evaluation/state/evaluation_state.json` — monitor_check_count: 276, latest adversarial re-verification recorded
- `evaluation/state/monitor_174k_state.json` — check_count: 276, dense embeddings progress updated (20/26 years checkpointed)

---

**Frozen Config Hash (adversarial):** `b51701f5a9c11692`  
**Formal Suite Config Hash:** `4323f833fa72366a`  
**Full Corpus Evaluation Config Hash:** `4047da047fb339c1`

*Report generated 2026-10-02T04:45:00Z*