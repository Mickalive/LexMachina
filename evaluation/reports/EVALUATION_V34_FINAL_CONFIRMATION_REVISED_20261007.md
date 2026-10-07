# Evaluation Lane v34 — Final Confirmation REVISED (Post-Audit CYCLE_37591874490)

**Factory Direction:** v34  
**Lane:** evaluation  
**Status:** COMPLETE (continue_recommended: conditional — see below)  
**Evidence Tier:** TF-IDF 174k: ACCEPTED | Dense criteria: UNVALIDATED at 174k (BLOCKED)  
**Date:** 2026-10-07  
**GitHub Run:** 37591874490 (original) / REVISED per audit REVISE gate  

---

## Executive Summary (Corrected)

The evaluation lane has **successfully completed the TF-IDF 174k production baseline mandate** (8/8 adversarial gates PASS, JP=0.7345). However, the **dense embedding acceptance criteria are NOT validated at 174k scale** — they are FROZEN but UNVALIDATED due to external data blockers. The original confirmation report overstated the evidence tier for dense criteria.

### Corrected Deliverable Status

| Deliverable | Status | Evidence |
|---|---|---|
| **TF-IDF 174k production baseline frozen** | ✅ **VALIDATED** | 8/8 representations PASS both adversarial gates; best JP=0.7345 |
| **Dense embedding acceptance criteria defined** | ✅ **DEFINED & FROZEN** | 4 criteria frozen with explicit thresholds |
| **Dense embedding acceptance criteria validated at 174k** | ❌ **UNVALIDATED / BLOCKED** | Full 174k validation FAILS or blocked by corpus lane dependencies |
| **Negative results preserved** | ✅ **VALIDATED** | v17b non-generalization, v18 hierarchy FAIL, dense JP ceiling ~0.53 |
| **Product integration contracts defined** | ✅ **VALIDATED** | 4 complementary views with frozen criteria |
| **Data blockers documented** | ✅ **VALIDATED** | bge_/bger_ mapping, parquet 2022-2026, section extraction |

---

## TF-IDF 174k Frozen Baseline — VALIDATED (ACCEPTED Tier)

### Formal Suite Adversarial Gates (Exact k-NN, Branch-Only Stratification, Seed=42)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.477** | **0.7345** | ✅ **PRODUCTION DEFAULT** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 | 0.7275 | ✅ |
| cited_decisions_tfidf | 0.479 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.5 | 0.487 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.7 | 0.489 | 0.7120 | ✅ |
| full_text_tfidf_light | 0.485 | 0.7080 | ✅ |
| outcome_tfidf | 0.502 | 0.6550 | ✅ |
| regeste_tfidf | 0.485 | 0.6315 | ✅ |

**Config Hash:** `b51701f5a9c11692` (frozen formal suite)  
**Subsampling:** Branch-only stratification, seed=42, n=2000  
**Beats semantic baseline:** 0.7345 vs 0.43 ✅ (mission satisfied)  
**Evidence:** `results/evaluation/tfidf_174k_adversarial_gates_formal_suite_latest.json` (GitHub run 37574492135)

---

## Dense Embedding Acceptance Criteria — FROZEN BUT UNVALIDATED AT 174k

### Critical Correction: Scale Mismatch

The original report claimed dense criteria were "validated against 22yr/144k ACCEPTED evidence." **Audit finding:** The 22-year/144k legal-distance checkpoint (2000-2021 cohort) is **not the full 174k corpus** (2000-2026). The acceptance criteria document explicitly requires validation "at full 174k (not subsampled)." That validation either FAILS or is blocked.

### Evidence Summary by Criterion

| Criterion | Threshold | Evidence at 174k Scale | Evidence at Partial Scale | Status |
|---|---|---|---|---|
| **Citation Heritage AUC** | > 0.75 | **AUC 0.48 FAIL** (`citation_heritage_174k.json`) | AUC 0.79-0.85 on 2000-2002 cohort (n≈144k but restricted temporal slice) | ❌ **FAIL at 174k** / UNVALIDATED |
| **Cross-lang same_branch (Sachverhalt)** | > 0.2 | **Full-doc: 0.0 FAIL** (`cross_language_benchmark_results.json`) | 0.282 on n=359 (36% coverage) section subset | ⚠️ PARTIAL SUBSET ONLY |
| **Cross-lang same_branch (Dispositiv)** | > 0.1 | **Full-doc: 0.0 FAIL** | 0.150 on n=538 (54% coverage) section subset | ⚠️ PARTIAL SUBSET ONLY |
| **Linear Hybrid JP (w=0.3-0.4)** | > 0.60 | **BLOCKED** — no 174k dense embeddings exist | 0.66-0.67 on v6-v10 era embeddings (NOT target legal-distance 174k embeddings) | ⚠️ WRONG EMBEDDINGS |

### Dense Embedding Role: COMPLEMENTARY VIEWS ONLY (Frozen)

| View | Primary Mode | Dense Embedding Role | Validation Status |
|---|---|---|---|
| **Jurist Preference / Branch Clustering** | TF-IDF citation hybrids (JP 0.735) | — | TF-IDF VALIDATED |
| **Citation Heritage Recovery** | TF-IDF citation-based (AUC 0.71-0.74) | **Dense target: AUC > 0.75** | **UNVALIDATED at 174k** (174k FAIL: 0.48) |
| **Cross-Lingual Alignment (Facts/Holdings)** | — | **Dense target: sachverhalt > 0.2, dispositiv > 0.1** | **UNVALIDATED at 174k** (partial subset only) |
| **Legal Reasoning / Argument Structure** | — | Dense complementary (erwaegungen > 0.05) | UNVALIDATED at 174k |

**Key Negative Result (ACCEPTED):** True OOS Jurist Preference ceiling ~0.53 < 0.7 factory target → Dense embeddings cannot be primary navigation mode.

---

## Blocking Dependencies (External — Corpus Lane)

| Blocker | Owner | Status | Impact on Dense Validation |
|---|---|---|---|
| **bge_ ↔ bger_ ID mapping** | Corpus lane | **BLOCKING** | Cannot align 174k dense embeddings with evaluation metadata (bger_ IDs) |
| **Parquet 2022-2026** | Corpus lane | **BLOCKING** | 29,520 decisions missing — cannot compute 174k dense embeddings |
| **Section extraction at 174k** | Corpus lane | **REQUIRED** | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k scale |

**Legal-distance progress:** Only 2000-2002 checkpoint years exist (~19k decisions). Years 2003-2025 pending.

---

## Negative Results Preserved (First-Class Evidence)

| Finding | Evidence | Status |
|---|---|---|
| **v18 coarse hierarchy FAIL** | Max branch_purity = 0.6497 (linear_citation_concat) < 0.7 threshold | ✅ ACCEPTED_NEGATIVE |
| **Dense JP ceiling ~0.53** | `scale_benchmark_results.json`, product integration dense-only JP ~0.43-0.51 | ✅ ACCEPTED_NEGATIVE |
| **v17b non-generalization to 174k** | NMI gains negative (-0.02 to -0.03), purity gains modest | ✅ ACCEPTED_NEGATIVE |
| **Citation heritage recall@10** | Max 0.0066 — ranking signal, not retrieval signal | ✅ ACCEPTED_NEGATIVE |
| **174k citation heritage AUC 0.48** | `citation_heritage_174k.json` (cited_outcome_hybrid_0.5_174k embedding) | ✅ PRESERVED |

---

## Conformance Checklist (Corrected)

| Checklist Item | Status | Evidence |
|---|---|---|
| Research Protocol followed | ✅ | Hypothesis/sample/metrics frozen before observation |
| No tuning after results observed | ✅ | Config hashes frozen, seeds fixed |
| Negative results preserved | ✅ | v18 FAIL, dense ceiling, v17b non-generalization documented |
| **Evidence tier: ACCEPTED** | ⚠️ **PARTIAL** | TF-IDF: ACCEPTED (15x reproduced). Dense: **NOT ACCEPTED** — 174k validation FAILS/blocked |
| Provenance preserved | ✅ | Config hashes, seeds, timestamps, run IDs recorded |
| No overwrite of historical results | ✅ | All prior cycles preserved |
| Anti-Noise Principle | ✅ | Universal 174k FAILs documented as corpus/label limitations |
| Multi-view requirement | ✅ | Dense positioned as COMPLEMENTARY only |
| Subsampling discrepancy documented | ✅ | Branch-only vs branch×language stratification root-caused |

---

## Recommendation (Corrected)

**CONTINUE_RECOMMENDED: conditional**

- **TF-IDF 174k evaluation mandate: COMPLETE** — No further same-question cycles justified. Frozen as production baseline.
- **Dense embedding validation mandate: CRITERIA DEFINED BUT VALIDATION BLOCKED** — Evaluation criteria are frozen and ready; validation cannot proceed until corpus lane delivers:
  1. bge_ ↔ bger_ ID mapping
  2. Parquet 2022-2026 (29,520 decisions)
  3. Section extraction at 174k scale

**Next evaluation cycle trigger:** When legal-distance delivers concatenated 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids) — the monitor's formal suite will auto-execute validation against **already-frozen criteria**.

The Factory Director should:
1. **Resume corpus lane** for the three blockers above
2. **Await legal-distance 174k dense embeddings delivery** for validation against frozen criteria
3. **Product lane** ships v1.0 with TF-IDF citation hybrids as primary navigation mode (mission satisfied: beats semantic baseline 0.7345 vs 0.43)

---

*This REVISED confirmation corrects the evidence tier overstatement identified in Audit CYCLE_37591874490 (REVISE gate). All evidence preserved, state frozen, audit-ready. The original confirmation report (EVALUATION_V34_FINAL_CONFIRMATION_20261007.md) is preserved as historical record; this revised version supersedes it for factory direction integrity.*