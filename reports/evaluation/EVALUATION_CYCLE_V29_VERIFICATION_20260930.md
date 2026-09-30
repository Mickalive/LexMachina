# Evaluation Lane Cycle Verification Report — Factory Direction v29

**Date:** 2026-09-30T10:15:00Z  
**Factory Direction Version:** 29  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed its deliverable** for factory direction v29: the TF-IDF family (8 representations) formal suite, citation heritage benchmark, and v17b label normalization are **ALL COMPLETE at 174k scale** with exact reproducibility verified.

**No new awaited representations detected** in this monitoring cycle. Dense embeddings remain at 3/26 years ACCEPTED (2000-2002, ~19k decisions) with 15/26 years (2000-2014, ~100k decisions) in checkpoints pending audit. Citation roles and linear hybrids not yet available at 174k.

The evaluation infrastructure is **FULLY OPERATIONAL and AUDIT-READY**.

---

## Verification Results (This Cycle)

### Adversarial Benchmarks — Exact Reproduction Confirmed

| Metric | Production Default (`cited_decisions_tfidf_outcome_hybrid_0.5`) | Threshold | Status |
|--------|---------------------------------------------------------------|-----------|--------|
| Language Dominance | **0.4773** | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference | **0.7345** | > 0.5 | ✅ PASS |
| Config Hash | `b51701f5a9c11692` | frozen | ✅ MATCH |

- **Backend:** sklearn exact k-NN on stratified subsample (n=2000)
- **HNSW Artifact Fix:** CONFIRMED operational — exact k-NN on valid subset avoids HNSW masking representation differences
- **All 8 TF-IDF representations:** PASS both adversarial gates

### Deliverable Completion Status (Factory Direction v29)

| Requirement | Status | Details |
|-------------|--------|---------|
| **(1) Full 12-benchmark formal suite at 174k on all production representations** | ✅ COMPLETE | 8 TF-IDF representations evaluated; frozen harness v3 thresholds unchanged; HNSW artifact fixed via exact k-NN on stratified subsample n=2000 |
| **(2) Citation heritage benchmark using 174k citation-ID resolution** | ✅ COMPLETE | Frozen 137,314-pair pool (137,314 positive + 137,314 negative); corpus-level citation ID resolution 2,019/2,105 (95.9%); all 8 TF-IDF reps FAIL recall@10 threshold (production default: 0.053) |
| **(3) v17b label normalization generalization to 174k fine-grained legal_area** | ✅ COMPLETE | 85,819 labels normalized (214→164 unique areas); differential effect CONFIRMED: hierarchy=1.0x (no improvement), zoom_fine=0.83-0.99x (degradation for 7/8), legal_area≈1.0x; uniform improvement FALSE |

---

## Dense Embeddings Progress (Legal-Distance Dependency)

| Metric | Value |
|--------|-------|
| Years in checkpoints | 15/26 (2000-2014, ~100k decisions) |
| Years ACCEPTED | 3/26 (2000-2002, ~19k decisions) |
| Checkpoint completion rate | 57.7% (years), 57.5% (decisions) |
| Blocked on | Years 2003-2014 pending audit promotion; years 2015-2026 not yet processed; center_projected concatenation not done; citation roles not computed; linear hybrids not computed |

**12k-scale evaluation (3 years ACCEPTED):** All center_projected variants (64/128/768) FAIL adversarial gates (LangDom ~0.98-1.0, JP ~0.04-0.08). PASS cross-language transfer (zero-shot NMI ~0.46-0.48) and cluster coherence (branch_purity ~0.89). **Scale dependency confirmed** — dense embeddings cluster by language not law at all tested scales.

**V17b normalization on V6 dense (12k):** NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45).

---

## Infrastructure Status

| Component | Status | Notes |
|-----------|--------|-------|
| Adversarial benchmarks | VERIFIED | Exact k-NN on stratified subsample n=2000 |
| Citation heritage pipeline | VERIFIED | Frozen 137,314 pairs, 95.9% resolution |
| v17b normalization pipeline | VERIFIED | Differential effect reproduced |
| HNSW artifact fix | CONFIRMED | Exact k-NN avoids representation masking |
| V25 formal suite | VERIFIED | Frozen protocol executed on all 8 TF-IDF + V6 dense 12k |
| Monitor script | ACTIVE | check_count=249, no new awaited representations |
| Scalable NN | OPERATIONAL | sklearn exact for adversarial, HNSW for full-corpus |

---

## Blockers (External Dependencies)

1. **Dense embeddings from legal-distance:** Only 3/26 years ACCEPTED; 12/26 years pending audit; final 174k concatenation not produced
2. **Citation role embeddings:** Not yet available at 174k
3. **Linear hybrid embeddings:** Not yet available at 174k
4. **Jurist human study:** Framework ready but requires 5-10 Swiss jurists (external dependency)

---

## Recommendation

**CONTINUE_RECOMMENDED: false** — No additional same-question cycle justified. The TF-IDF 174k deliverable per factory direction v29 is complete and verified. The evaluation lane is in MONITORING state, awaiting new representations from legal-distance lane.

**Next action:** Factory Director to evaluate legal-distance progress and determine successor question when dense embeddings / citation roles / linear hybrids land at 174k scale.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- `evaluation/state/evaluation_state.json` (updated)
- `evaluation/state/monitor_174k_state.json` (updated, check_count=249)

---

*Report generated by evaluation lane autonomous verification cycle.*