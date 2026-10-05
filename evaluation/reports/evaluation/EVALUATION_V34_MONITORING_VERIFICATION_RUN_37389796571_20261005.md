# Evaluation Lane — Monitoring Verification for GitHub Run 37389796571

**Lane:** evaluation  
**Factory Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  
**Accepted Run ID:** eval_174k_v34_baseline_and_dense_criteria_20261003  
**GitHub Run:** 37389796571  
**Verification Date:** 2026-10-05  
**Previous Verification:** 37298319501 (2026-10-05)

---

## Executive Summary

This monitoring verification confirms the evaluation lane state **remains unchanged** from the final verification at GitHub run 37298319501:

1. ✅ **TF-IDF 174k evaluation FROZEN as production baseline** — 8/8 representations PASS both adversarial gates on frozen harness v3 (config hash `b51701f5a9c11692`, seed 42). Best production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JP=0.7345).

2. ✅ **Dense embedding complementary view acceptance criteria DEFINED and VALIDATED** against 22-year/144,443-decision ACCEPTED evidence from legal-distance lane (audit run 37090665528).

3. ✅ **True OOS JuristPref ceiling ~0.53 documented** — No representation meets 0.7 factory target under true out-of-sample conditions.

4. ✅ **Lane correctly BLOCKED_ON_DEPENDENCIES** — 174k dense embeddings require corpus lane resumption (bge_↔bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale).

5. ✅ **Monitor scan confirms**: All 8 TF-IDF 174k representations available and evaluated; all 12 awaited representations (8 dense embeddings, 3 citation roles, 2 linear hybrids) still missing — no change.

---

## Monitor Scan Results (GitHub Run 37389796571)

### Representations Found (via `/tmp/lex_accepted` mount)

| Source | Representations | Status |
|--------|----------------|--------|
| `fractal-map/hierarchical_map_174k/legal_tfidf_embeddings` | 8 TF-IDF .npy files | ✅ COMPLETED & EVALUATED |
| `fractal-map/hierarchical_map_174k/tfidf_embeddings` | 4 TF-IDF .npy files (alt) | ✅ COMPLETED & EVALUATED |
| `legal-distance/174k_dense_embeddings` | **No final embeddings found** | ❌ AWAITED — checkpointed only |
| legal-distance version dirs | No 174k dense/citation_role/linear dirs | ❌ AWAITED |

### Readiness Status

**COMPLETED (TF-IDF family at 174k):**
- ✅ `cited_decisions_tfidf`
- ✅ `outcome_tfidf`
- ✅ `cited_decisions_tfidf_outcome_hybrid_0.5`
- ✅ `cited_decisions_tfidf_outcome_hybrid_0.7`
- ✅ `regeste_tfidf`
- ✅ `full_text_tfidf_light`
- ✅ `regeste_full_text_hybrid_0.5`
- ✅ `regeste_full_text_hybrid_0.7`

**AWAITED (dense embeddings, citation roles, linear hybrids):**
- ❌ `center_projected_768dim` / `center_projected_64dim` / `center_projected_128dim`
- ❌ `linear_metric_epoch4` / `mahalanobis_metric_epoch4` / `hybrid_stabilized_epoch1` / `hybrid_v2_epoch3`
- ❌ `citation_role_citing_alpha0.3` / `citation_role_following_alpha0.3` / `citation_role_criticizing_alpha0.3`
- ❌ `linear_citation_concat` / `linear_hybrid05_concat`

**No new awaited representations detected** — state unchanged.

---

## Frozen TF-IDF 174k Production Baseline (Reconfirmed)

| Representation | Language Dominance | Jurist Preference | Both Gates | Verdict |
|----------------|-------------------|-------------------|------------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4773** | **0.7345** | ✅ | **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4783 | 0.7275 | ✅ | PASS |
| `cited_decisions_tfidf` | 0.4794 | 0.7140 | ✅ | PASS |
| `full_text_tfidf_light` | 0.4855 | 0.7080 | ✅ | PASS |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ | PASS |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ | PASS |
| `outcome_tfidf` | 0.5015 | 0.6550 | ✅ | PASS |
| `regeste_tfidf` | 0.4853 | 0.6315 | ✅ | PASS |

**All 8 PASS both adversarial gates** (Language Dominance < 0.85, Jurist Preference > 0.5) on exact k-NN (sklearn) over fixed stratified subsample (n=2,000 valid decisions with known branch).

**Harness:** v3 frozen, config_hash=`b51701f5a9c11692`, seed=42.

---

## Dense Embedding Complementary Views — Acceptance Criteria (Revalidated)

### 2.1 Citation Heritage Recovery (AUC-ROC) — PASS at 22-year/144k

| Mode | AUC-ROC | Threshold | Status |
|------|---------|-----------|--------|
| `center_projected_768dim` | 0.7941 | > 0.75 | ✅ PASS |
| `center_projected_64dim` | 0.7922 | > 0.75 | ✅ PASS |
| `center_projected_128dim` | 0.7916 | > 0.75 | ✅ PASS |
| `raw_768dim` | 0.7946 | > 0.75 | ✅ PASS |

**Verdict:** Dense embeddings EXCEED both 0.75 threshold AND TF-IDF citation-based baseline (0.71-0.74). Novel complementary capability confirmed.

### 2.2 Cross-Lingual Section Alignment — Sachverhalt/Dispositiv PASS (1K sample)

| Section | cross_lang_same_branch | Threshold | Status |
|---------|------------------------|-----------|--------|
| **Sachverhalt** (facts) | 0.2816 | > 0.2 | ✅ PASS (sample) |
| **Dispositiv** (holdings) | 0.1502 | > 0.1 | ✅ PASS (sample) |
| **Erwaegungen** (reasoning) | 0.0941 | > 0.1 | ❌ FAIL |

**Hierarchy:** Sachverhalt > Dispositiv > Erwaegungen. Center projection improves all sections. **Blocked on full-corpus section extraction at 174k.**

### 2.3 Jurist Pairwise Preference — FAIL at ALL Scales (Confirms Complementary-Only)

| Scale | Decisions | center_projected JP | Status |
|-------|-----------|---------------------|--------|
| 3-yr (ACCEPTED) | 19,441 | 0.005 | ❌ FAIL |
| 15-yr | 91,929 | 0.288 | ❌ FAIL |
| 19-yr | 122,015 | ~0.37 | ❌ FAIL |
| 22-yr | 144,443 | 0.389 | ❌ FAIL |
| **174k target** | 173,963 | **BLOCKED** | — |

**Verdict:** Dense embeddings CANNOT be primary navigation mode. Product role: complementary views only.

### 2.4 Linear Hybrid Complement — PASS Adversarial but Below TF-IDF Baseline

| Weight (Dense/TF-IDF) | JP | LangDom | Both Pass | vs TF-IDF (0.78-0.79) |
|-----------------------|-----|---------|-----------|----------------------|
| w=0.3 / 0.7 | 0.66 | 0.65 | ✅ | -0.12 |
| w=0.4 / 0.6 | 0.67 | 0.65 | ✅ | -0.11 |

Cross-lingual recall@10 improves (0.160 vs 0.124 baseline) but remains below 0.2 utility threshold.

---

## Data Blockers (Unchanged — Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **No bge_ ↔ bger_ ID mapping** | Cannot align canonical (BGE) with evaluation (bger) corpus | Corpus lane coordination |
| **Missing parquet 2022–2026** | 29,520 decisions (17%) missing from 174k | Corpus lane acquisition |
| **Section extraction not at scale** | Sachverhalt/Erwaegungen/Dispositiv embeddings only at 1K | Full corpus text access + section encoding |

---

## Compliance with Research Protocol

- ✅ Hypothesis, baseline, success rule frozen before observation
- ✅ Negative results preserved (Dense FAIL jurist gate at ALL scales; v17b FAIL at 174k; v18 FAIL; boilerplate FAIL; hierarchy FAIL)
- ✅ Strong baselines used (whole-doc semantic, TF-IDF citation-only, norms-only, simple hybrids)
- ✅ Evaluation on frozen harness v3 with fixed seed (42)
- ✅ Provenance preserved for all claim-bearing outputs
- ✅ Machine-readable state file updated with evidence_refs and critical_findings
- ✅ PIVOT_WITHIN_MISSION documented with product integration contract

---

## Recommendation: COMPLETE — No Further Same-Question Cycles

**The evaluation lane has completed its factory direction v34 mandate:**

1. ✅ TF-IDF 174k evaluation **FROZEN as production baseline** (8/8 reps PASS, best JP=0.7345)
2. ✅ Dense embedding complementary view acceptance criteria **DEFINED and VALIDATED**
3. ✅ True OOS JuristPref ceiling ~0.53 **documented** — no representation meets 0.7 target
4. ✅ Lane correctly **BLOCKED_ON_DEPENDENCIES** — awaiting 174k dense embeddings

**Next Action:** Corpus lane resumption for bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale. Product lane proceeds with v1.0 release using TF-IDF citation hybrids as primary navigation mode.

---

## Sign-Off

**TF-IDF 174k Production Baseline: FROZEN AND ACCEPTED**  
**Dense Complementary Acceptance Criteria: DEFINED AND VALIDATED**  
**Lane Status: BLOCKED_ON_DEPENDENCIES — continue_recommended=false**

*Monitoring verification from ACCEPTED evidence. No state change since prior verification. Provenance preserved.*

---

## Evidence Artifacts (Machine-Readable)

| Artifact | Path |
|----------|------|
| TF-IDF 174k Frozen Baseline | `evaluation/results/evaluation/tfidf_174k_formal_suite_baseline.json` |
| Dense Acceptance Criteria | `evaluation/results/evaluation/dense_complementary_acceptance_criteria.json` |
| Formal Suite Raw Results (8 reps) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation Heritage 22yr (legal-distance) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` |
| Section Cross-Lingual 1K (legal-distance) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` |
| Complementary Role Characterization | `/tmp/lex_accepted/legal-distance/legal_distance/results/complementary_role_characterization_v34.json` |
| v17b Normalization 174k | `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_latest.json` |
| v18 Coarse Hierarchy | `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json` |
| Monitor State | `evaluation/state/monitor_174k_state.json` |