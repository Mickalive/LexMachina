# Evaluation Lane - 174k Monitoring Report (v28 Update)

**Date:** 2026-09-28T13:10:05Z  
**Factory Direction Version:** 28  
**Lane Status:** MONITORING (active)  
**Evidence Tier:** REPRODUCED  
**Monitor Check Count:** 200

---

## Executive Summary

All three factory direction v28 deliverables for the **TF-IDF family (8 representations)** are **COMPLETE and VERIFIED REPRODUCIBLE** at 174k scale. The evaluation lane is in active MONITORING mode, waiting for awaited representations from legal-distance:

| Deliverable | Status | Details |
|------------|--------|---------|
| **1. 12-benchmark formal suite** | ✅ COMPLETE | All 8 TF-IDF reps evaluated via `run_174k_formal_suite.py` (HNSW artifact fixed via exact k-NN on stratified subsample n=2000). Config hash: `b51701f5a9c11692` |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen 2,040 pair pool (1,020 positive, 1,020 negative, balanced from resolved citation graph, seed=42). 95.9% citation-ID resolution (2,019/2,105). **ALL 8 TF-IDF FAIL** recall@10 < 0.2 threshold — confirmed negative result |
| **3. v17b label normalization** | ✅ COMPLETE | 85,819 labels normalized (214→164 unique areas). **Differential effect CONFIRMED**: Citation-based reps improve 1.04-1.10x on hierarchy/zoom_fine/legal_area; text-based reps DEGRADE zoom_fine 0.66-0.70x |

---

## Current State: TF-IDF Family (8 representations)

| Representation | Adversarial (v3) | V25 Suite (12 bm) | Citation Heritage | v17b Normalization |
|---------------|------------------|-------------------|-------------------|-------------------|
| `cited_decisions_tfidf` | PASS (LD=0.53, JP=0.80) | 6/12 PASS | FAIL (recall@10=0.044) | Hierarchy +6%, Zoom +4%, LegalArea +6% |
| `outcome_tfidf` | PASS (LD=0.45, JP=0.73) | 3/12 PASS | FAIL (recall@10=0.000) | Hierarchy +5%, Zoom +8%, LegalArea +4% |
| `regeste_tfidf` | PASS (LD=0.48, JP=0.61) | 5/12 PASS | FAIL (recall@10=0.000) | Hierarchy 0%, Zoom +10%, LegalArea +2% |
| `full_text_tfidf_light` | **FAIL** (LD=1.00, JP=0.00) | 7/12 PASS | FAIL (recall@10=0.052) | **Zoom -33%**, Hierarchy 0%, LegalArea -3% |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | PASS (LD=0.52, JP=0.81) | 6/12 PASS | FAIL (recall@10=0.053) | Hierarchy +6%, Zoom +4%, LegalArea +6% |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | PASS (LD=0.52, JP=0.80) | 6/12 PASS | FAIL (recall@10=0.049) | Hierarchy +5%, Zoom +5%, LegalArea +6% |
| `regeste_full_text_hybrid_0.5` | **FAIL** (LD=0.998, JP=0.00) | 7/12 PASS | FAIL (recall@10=0.035) | **Zoom -34%**, Hierarchy 0%, LegalArea -3% |
| `regeste_full_text_hybrid_0.7` | **FAIL** (LD=0.999, JP=0.00) | 7/12 PASS | FAIL (recall@10=0.036) | **Zoom -30%**, Hierarchy 0%, LegalArea -4% |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** both adversarial gates (LangDom=0.5167, Jurist=0.8050)

---

## Fundamental Two-Mode Tradeoff (REPRODUCED at 174k)

| Mode | Language Dominance | Jurist Pairwise | Citation Heritage | Branch KNN | Hierarchy | Multilingual |
|------|-------------------|-----------------|-------------------|------------|-----------|--------------|
| **Citation-based** (5 reps) | ✅ PASS (<0.85) | ✅ PASS (>0.5) | AUC PASS, recall@10 FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS |
| **Text-based** (3 reps) | ❌ FAIL (~0.999) | ❌ FAIL (~0.0) | AUC PASS, recall@10 FAIL | ✅ PASS | NMI↑ (but LD FAIL) | ❌ FAIL |

> **Key finding:** No single representation passes all benchmarks. Citation signals preserve citation structure but lose branch/legal_area coherence. Text signals capture branch/legal_area but collapse on language dominance at 174k scale.

---

## Awaited Representations (from legal-distance)

| Category | Representations | Status |
|----------|----------------|--------|
| **Dense embeddings (174k)** | `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | ❌ NOT LANDED (only 3/26 years ACCEPTED: 2000-2002) |
| **Citation roles (174k)** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | ❌ NOT LANDED |
| **Linear hybrids (174k)** | `linear_citation_concat`, `linear_hybrid05_concat` | ❌ NOT LANDED |

**Legal-distance progress:** 20/26 years (2000-2019, ~99k decisions) in checkpoints — **PENDING AUDIT**. Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED per factory direction v28.

---

## Infrastructure Verification (2026-09-28T13:10:05Z)

| Component | Status | Details |
|-----------|--------|---------|
| **Adversarial benchmarks (v3)** | ✅ VERIFIED | Exact reproduction: prod default lang_dom=0.5167 (exp 0.5164), jurist=0.8050 (exp 0.8055) |
| **Citation heritage pairs** | ✅ VERIFIED | Frozen 2,040 pairs; evaluation re-run on new pool |
| **v17b normalization** | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps |
| **HNSW artifact fix** | ✅ CONFIRMED | Exact k-NN on stratified subsample (n=2000) avoids HNSW masking |
| **V25 formal suite** | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps; config hash `4323f833fa72366a` |
| **Monitor script** | ✅ ACTIVE | Check 200 completed; no new awaited representations detected |
| **Scalable NN** | ✅ OPERATIONAL | sklearn exact k-NN for adversarial; HNSW for full-corpus citation heritage |

---

## Blocker Summary

| Blocker | Impact | Resolution Path |
|---------|--------|-----------------|
| **Dense embeddings 174k** | Blocks fractal-map, product, evaluation of dense modes | legal-distance must complete years 2003-2025 and pass audit |
| **Citation role embeddings 174k** | Blocks citation-role-specific map modes | legal-distance must deliver |
| **Linear hybrid embeddings 174k** | Blocks production default optimization | legal-distance must deliver |
| **Jurist human study** | External validation pending | Framework ready; requires 5-10 Swiss jurists |

---

## Next Actions

1. **MONITORING CONTINUES** — `monitor_and_evaluate_174k.py` runs periodically (check_count=200)
2. **AUTO-EVALUATE** when awaited representations land in `/tmp/lex_accepted/legal-distance/...`
3. **NO NEW EVALUATION WORK** until legal-distance promotes 174k dense embeddings, citation roles, or linear hybrids to ACCEPTED state
4. **continue_recommended = TRUE** — monitoring has concrete discriminating purpose (auto-evaluate awaited representations)

---

## Reproducibility Artifacts

| Artifact | Location | Config Hash |
|----------|----------|-------------|
| Formal suite (v3, HNSW fix) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | `b51701f5a9c11692` |
| V25 formal suite (12 bm) | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` | `4323f833fa72366a` |
| Citation heritage | `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` | — |
| v17b label normalization | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` | — |
| Monitor state | `evaluation/state/monitor_174k_state.json` | — |

---

## Configuration Freeze

All adversarial thresholds and benchmark parameters remain **FROZEN** at v3 values:
- Language dominance threshold: 0.85
- Jurist pairwise threshold: 0.5
- Cross-language recall threshold: 0.2
- Cluster coherence threshold: 0.7
- Global seed: 42

**No benchmark weakening after seeing results** — negative results (citation heritage FAIL, text-based adversarial FAIL) are preserved as first-class evidence.

---

*Generated by evaluation lane monitoring cycle 200. Next cycle triggered on representation landing detection.*