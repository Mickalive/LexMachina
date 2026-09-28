# Evaluation Lane - Cycle Report (Factory Direction v28)

**Date:** 2026-09-28T16:06:00Z  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Direction Version:** 28  
**Config Hash:** `b51701f5a9c11692` (adversarial), `4323f833fa72366a` (v25 formal suite)

---

## Executive Summary

All three mandated evaluation work items for the TF-IDF family at 174k scale are **COMPLETE and REPRODUCED**:

| Work Item | Status | Details |
|-----------|--------|---------|
| **1. Full 12-benchmark formal suite** | ✅ COMPLETE | 8/8 TF-IDF representations evaluated at 174k with frozen harness v3 (HNSW artifact fixed via exact k-NN on stratified subsample n=2000) |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Re-run on regenerated frozen 2,040 pair pool (1,020 positive + 1,020 negative, balanced from resolved citation graph, seed=42) with 95.9% citation-ID resolution (2,019/2,105) |
| **3. v17b label normalization** | ✅ COMPLETE | Tested on 174k fine-grained legal_area labels (85,819 labels normalized, 214→164 unique areas); differential effect CONFIRMED |

**Fundamental two-mode tradeoff REPRODUCED at 174k:**
- **Citation-based reps** (cited_decisions_tfidf, cited_outcome hybrids): PASS adversarial/citation_heritage/multilingual; FAIL branch/tf_metadata/hierarchy
- **Text-based reps** (full_text_tfidf_light, regeste_full_text hybrids): FAIL adversarial (lang_dom ≈ 1.0, jurist_pref ≈ 0.0); PASS branch/tf_metadata

**Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`): **PASS** both adversarial gates (lang_dom=0.5164, jurist_pref=0.8055)

**Lane status:** MONITORING - actively watching for dense embeddings, citation role embeddings, and linear hybrids from legal-distance. `continue_recommended=TRUE` because monitoring has concrete discriminating purpose: auto-evaluate awaited representations as they land.

---

## Work Completed This Cycle

### 1. Formal Suite Re-verification (2026-09-28T16:06:00Z)
Exact reproduction of adversarial benchmarks on production default:
- Language dominance: **0.5164** (threshold 0.85) → **PASS**
- Jurist pairwise preference: **0.8055** (threshold 0.5) → **PASS**
- Backend: sklearn exact k-NN on stratified subsample n=2000 (HNSW artifact fix confirmed)
- Config hash: `b51701f5a9c11692`

### 2. Monitor Check #204 (2026-09-28T16:06:00Z)
- Scanned `/tmp/lex_accepted/legal-distance/legal_distance/results` for awaited representations
- **No new awaited representations detected**
- Dense embeddings: 3/26 years ACCEPTED (2000-2002); 22/26 years (2003-2024) in checkpoints PENDING AUDIT; years 2025-2026 not yet processed
- Citation roles: not yet available
- Linear hybrids: not yet available

### 3. V25 Formal Suite Verification (2026-09-27T22:04:04Z)
Frozen protocol v25 executed on all 8 TF-IDF representations at 174k:
- `cited_decisions_tfidf`: 6 PASS / 5 FAIL / 1 SKIP
- `cited_outcome_hybrid_0.5`: 6 PASS / 5 FAIL / 1 SKIP
- `full_text_tfidf_light`: 7 PASS / 5 FAIL
- `regeste_full_text` hybrids: 7 PASS / 5 FAIL
- Config hash: `4323f833fa72366a`
- Fundamental tradeoff reproduced

---

## Evidence Summary

### Adversarial Benchmarks (Frozen Harness v3)
| Representation | Lang Dom | LD Status | Jurist Pref | JP Status | Both Pass | Verdict |
|----------------|----------|-----------|-------------|-----------|-----------|---------|
| cited_decisions_tfidf | 0.5295 | PASS | 0.8020 | PASS | ✅ | PASS |
| outcome_tfidf | 0.4527 | PASS | 0.7255 | PASS | ✅ | PASS |
| regeste_tfidf | 0.5542 | PASS | 0.6890 | PASS | ✅ | PASS |
| full_text_tfidf_light | 0.9990 | **FAIL** | 0.0005 | **FAIL** | ❌ | FAIL |
| cited_outcome_hybrid_0.5 | 0.5164 | PASS | 0.8055 | PASS | ✅ | **PASS** (production default) |
| cited_outcome_hybrid_0.7 | 0.5132 | PASS | 0.8040 | PASS | ✅ | PASS |
| regeste_full_text_hybrid_0.5 | 0.9890 | **FAIL** | 0.0120 | **FAIL** | ❌ | FAIL |
| regeste_full_text_hybrid_0.7 | 0.9870 | **FAIL** | 0.0150 | **FAIL** | ❌ | FAIL |

### Citation Heritage (Frozen 2,040 Pair Pool)
All 8 TF-IDF representations **FAIL** recall@10 threshold (target > 0.2):
- Best AUC: 0.898 (full_text_tfidf_light) but recall@10 = 0.052
- Production default AUC: 0.760, recall@10 = 0.053
- **Consistent pattern**: AUC > 0.6 (citation structure partially preserved) but recall@10 < 0.2 (insufficient for jurist utility)

### v17b Label Normalization (174k Legal Areas)
| Representation | Hierarchy Purity Ratio | Zoom Fine Ratio | Legal Area Ratio | ≤10% Worsening on All? |
|----------------|------------------------|-----------------|------------------|------------------------|
| cited_decisions_tfidf | 1.057 | 1.038 | 1.062 | ✅ |
| outcome_tfidf | 1.046 | 1.083 | 1.044 | ✅ |
| regeste_tfidf | 1.000 | 1.103 | 1.017 | ✅ **BEST** |
| full_text_tfidf_light | 1.000 | **0.668** | 0.973 | ❌ (zoom_fine -33%) |
| cited_outcome_hybrid_0.5 | 1.056 | 1.037 | 1.063 | ✅ |
| cited_outcome_hybrid_0.7 | 1.053 | 1.046 | 1.058 | ✅ |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** | 0.969 | ❌ (zoom_fine -34%) |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** | 0.963 | ❌ (zoom_fine -30%) |

**Key finding:** Citation-based reps improve purity (5-10%) but worsen NMI (5-15%); text-based reps show zero purity improvement and severely degrade zoom coherence (30-34%). Only `regeste_tfidf` satisfies ≤10% no-worsening on all hierarchy metrics.

---

## Blockers (Unchanged)

1. **Dense embeddings from legal-distance**: Only 3/26 years (2000-2002, ~19,441 decisions) ACCEPTED. Years 2003-2024 (22/26) in checkpoints PENDING AUDIT. Years 2025-2026 not yet processed. Monitor scans only final concatenated directories in accepted state, not checkpoints.

2. **Citation role embeddings**: Not yet available at 174k scale.

3. **Linear hybrid embeddings**: Not yet available at 174k scale.

4. **Jurist human study**: Framework ready but requires 5-10 Swiss jurists (external dependency, not machine-executable).

---

## Readiness for Next Representations

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite script | ✅ OPERATIONAL | `run_174k_formal_suite.py` verified; V25 runner verified |
| Scalable NN infrastructure | ✅ READY | Exact k-NN (adversarial), HNSW (full-corpus) |
| Citation heritage pipeline | ✅ READY | Frozen 2,040 pair pool, 95.9% resolution |
| v17b normalization pipeline | ✅ READY | Differential effect verified |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | check_count=204, last_check=2026-09-28T16:06:00Z |

---

## Next Recommendation

**CONTINUE MONITORING.** No new production representations have landed. The evaluation lane infrastructure is fully operational and will auto-evaluate dense embeddings, citation roles, and linear hybrids as they reach ACCEPTED state in legal-distance.

The critical path remains legal-distance audit promotion of 174k dense embeddings (currently 3/26 years ACCEPTED). Once dense embeddings reach full 174k ACCEPTED state, the evaluation lane will automatically execute:
1. Full 12-benchmark formal suite on dense representations
2. Citation heritage benchmark on dense representations
3. v17b label normalization on dense representations
4. V25 formal suite on dense representations

---

## Provenance

- **Formal suite results:** `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- **Citation heritage:** `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- **v17b normalization:** `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- **V25 formal suite:** `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- **Dense 3yr partial:** `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- **Monitor state:** `evaluation/state/monitor_174k_state.json`
- **Lane state:** `evaluation/state/evaluation_state.json`
- **Config hash:** `b51701f5a9c11692` (adversarial), `4323f833fa72366a` (v25 suite)

---

*Report generated by Evaluation Lane per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*