# Evaluation Lane - Monitoring Cycle Report (v28)

**Date:** 2026-09-29T00:50:00Z  
**Factory Direction Version:** 28  
**Lane Status:** MONITORING (active)  
**Evidence Tier:** REPRODUCED  
**Monitor Check Count:** 215 (incremented from 206)

---

## Executive Summary

The evaluation lane continues in **active MONITORING mode** as specified in factory direction v28. All three TF-IDF family deliverables are **COMPLETE and VERIFIED REPRODUCIBLE** at 174k scale:

| Deliverable | Status | Key Result |
|------------|--------|------------|
| **1. 12-benchmark formal suite** | ✅ COMPLETE | 8 TF-IDF reps evaluated with frozen harness v3 (HNSW artifact fixed via exact k-NN on stratified subsample n=2000). Config hash: `b51701f5a9c11692` |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen 137,314 pair pool (95.9% citation resolution). ALL 8 TF-IDF FAIL recall@10 < 0.2 — confirmed negative result |
| **3. v17b label normalization** | ✅ COMPLETE | 214→164 unique areas (23.5% reduction). Differential effect REPRODUCED: Citation-based reps improve hierarchy/legal_area 5-7%; text-based reps DEGRADE zoom_fine 30-34% |

**No new awaited representations detected** — dense embeddings (25/26 years in checkpoints, only 3 ACCEPTED), citation roles, and linear hybrids remain blocked on legal-distance audit promotion.

---

## Current State: TF-IDF Family (8 representations, 174k scale)

| Representation | Adversarial Gates | LangDom | Jurist Pref | Citation Heritage | v17b Effect |
|---|---|---|---|---|---|
| `cited_decisions_tfidf` | ✅ PASS | 0.529 | 0.802 | AUC=0.76, R@10=0.044 | Hierarchy +6%, Zoom +4%, LA +6% |
| `outcome_tfidf` | ✅ PASS | 0.447 | 0.732 | AUC=0.79, R@10=0.000 | Hierarchy +5%, Zoom +8%, LA +4% |
| `regeste_tfidf` | ✅ PASS | 0.478 | 0.612 | AUC=0.78, R@10=0.000 | Hierarchy 0%, Zoom +10%, LA +2% |
| `full_text_tfidf_light` | ❌ FAIL | 1.000 | 0.000 | AUC=0.49, R@10=0.052 | **Zoom -33%**, Hier 0%, LA -3% |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | ✅ PASS | **0.516** | **0.805** | AUC=0.76, R@10=0.053 | Hierarchy +6%, Zoom +4%, LA +6% |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | ✅ PASS | 0.518 | 0.804 | AUC=0.76, R@10=0.049 | Hierarchy +5%, Zoom +5%, LA +6% |
| `regeste_full_text_hybrid_0.5` | ❌ FAIL | 0.998 | 0.000 | AUC=0.49, R@10=0.035 | **Zoom -34%**, Hier 0%, LA -3% |
| `regeste_full_text_hybrid_0.7` | ❌ FAIL | 0.999 | 0.000 | AUC=0.49, R@10=0.036 | **Zoom -30%**, Hier 0%, LA -4% |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** both adversarial gates (LangDom=0.5164, Jurist=0.8055)

---

## Fundamental Two-Mode Tradeoff (REPRODUCED at 174k)

| Mode | Language Dominance | Jurist Pairwise | Citation Heritage | Branch KNN | Hierarchy | Multilingual |
|---|---|---|---|---|---|---|
| **Citation-based** (5 reps) | ✅ PASS (<0.85) | ✅ PASS (>0.5) | AUC PASS, R@10 FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS |
| **Text-based** (3 reps) | ❌ FAIL (~0.999) | ❌ FAIL (~0.0) | AUC PASS, R@10 FAIL | ✅ PASS | NMI↑ (but LD FAIL) | ❌ FAIL |

> **Key finding:** No single representation passes all benchmarks. Citation signals preserve citation structure but lose branch/legal_area coherence. Text signals capture branch/legal_area but collapse on language dominance at 174k scale.

---

## Awaited Representations (from legal-distance)

| Category | Representations | Status |
|---|---|---|
| **Dense embeddings (174k)** | `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | ❌ NOT LANDED — 25/26 years (2000-2024) in checkpoints, **only 3/26 years ACCEPTED** (2000-2002, ~19k decisions) |
| **Citation roles (174k)** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | ❌ NOT LANDED — awaits dense completion |
| **Linear hybrids (174k)** | `linear_citation_concat`, `linear_hybrid05_concat` | ❌ NOT LANDED — awaits dense completion |

**Legal-distance progress:** Checkpoints show 25/26 years (2000-2024, ~174k decisions) completed — **PENDING AUDIT**. Years 2025-2026 not yet processed. Per factory direction v28: only 3/26 years (2000-2002) are ACCEPTED.

---

## Infrastructure Verification (2026-09-29)

| Component | Status | Details |
|---|---|---|
| **Adversarial benchmarks (v3)** | ✅ VERIFIED | Exact reproduction: prod default LangDom=0.5167 (exp 0.5164), Jurist=0.8050 (exp 0.8055) |
| **Citation heritage pairs** | ✅ VERIFIED | Frozen 137,314 pairs; evaluation re-run on new pool |
| **v17b normalization** | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps |
| **HNSW artifact fix** | ✅ CONFIRMED | Exact k-NN on stratified subsample (n=2000) avoids HNSW masking representation differences |
| **V25 formal suite** | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps; config hash `4323f833fa72366a` |
| **Monitor script** | ✅ ACTIVE | Check 215 completed; no new awaited representations detected |
| **Scalable NN** | ✅ OPERATIONAL | sklearn exact k-NN for adversarial; HNSW for full-corpus citation heritage |

---

## Blocker Summary

| Blocker | Impact | Resolution Path |
|---|---|---|
| **Dense embeddings 174k** | Blocks fractal-map, product, evaluation of dense modes | legal-distance must complete years 2003-2026 and pass audit |
| **Citation role embeddings 174k** | Blocks citation-role-specific map modes | legal-distance must deliver |
| **Linear hybrid embeddings 174k** | Blocks production default optimization | legal-distance must deliver |
| **Jurist human study** | External validation pending | Framework ready; requires 5-10 Swiss jurists |

---

## Next Actions

1. **MONITORING CONTINUES** — `monitor_and_evaluate_174k.py` runs periodically (check_count=215)
2. **AUTO-EVALUATE** when awaited representations land in `/tmp/lex_accepted/legal-distance/...`
3. **NO NEW EVALUATION WORK** until legal-distance promotes 174k dense embeddings, citation roles, or linear hybrids to ACCEPTED state
4. **continue_recommended = TRUE** — monitoring has concrete discriminating purpose (auto-evaluate awaited representations)

---

## Reproducibility Artifacts

| Artifact | Location | Config Hash |
|---|---|---|
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

*Generated by evaluation lane monitoring cycle 215. Lane state audit-ready. Next cycle triggered on representation landing detection.*