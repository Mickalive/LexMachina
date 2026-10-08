# EVALUATION V35 — TF-IDF 174k Baseline Re-verified & Dense Embedding Complementary Criteria Finalized

**Factory Direction:** v35  
**Lane:** evaluation  
**Date:** 2026-10-07  
**GitHub Run:** 37399175524 (re-verification) + bootstrap CI validation  
**Status:** COMPLETE — `continue_recommended: false`

---

## Executive Summary

The evaluation lane has completed its v35 mission: **TF-IDF 174k evaluation frozen as production baseline** and **dense embedding complementary acceptance criteria defined and validated** with bootstrap 95% confidence intervals.

### Critical Finding: Baseline Mutation Documented
- **Original freeze (2026-10-03):** 8/8 TF-IDF representations PASS both adversarial gates; production default `cited_decisions_tfidf_outcome_hybrid_0.5` JP=0.7345
- **Accepted mount mutated (2026-10-07 fractal-map rebuild):** Embeddings changed post-freeze
- **Re-verification (2026-10-07, GitHub run 37399175524):** 6/8 representations PASS; production default JP=0.556 (still PASS but degraded Δ=-0.178)
- **Working directory embeddings:** Reproduce original frozen baseline exactly (JP=0.7345)
- **Remediation:** Baseline re-frozen with current accepted mount values; mutation documented as ACCEPTED_NEGATIVE finding for provenance

### Dense Embedding Complementary Criteria — VALIDATED with Bootstrap 95% CIs

| Criterion | Threshold | Point Estimate | 95% CI | Status |
|-----------|-----------|----------------|--------|--------|
| Citation Heritage AUC (center_projected_64dim) | > 0.75 | 0.7922 | [0.7619, 0.8223] | **PASS** |
| Cross-lang Same-branch Sachverhalt | > 0.2 | 0.2816 | [0.2669, 0.2964] | **PASS** |
| Cross-lang Same-branch Dispositiv | > 0.1 | 0.1502 | [0.1409, 0.1599] | **PASS** |
| Cross-lang Same-branch Erwaegungen | > 0.1 | 0.0941 | [0.0863, 0.1022] | **FAIL** |
| Jurist Pairwise Preference (adversarial) | > 0.5 | 0.35-0.38 (24yr) | — | **FAIL** |

**Key validation:** All three PASSING criteria have 95% CI lower bounds **exceeding thresholds** — robust against sampling variance.

---

## TF-IDF 174k Production Baseline (Re-verified)

| Representation | LangDom | JP | Both Gates |
|---|---|---|---|
| `cited_decisions_tfidf_outcome_hybrid_0.5` ⭐ | 0.438 | **0.557** | ✅ PASS |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.435 | 0.566 | ✅ PASS |
| `cited_decisions_tfidf` | 0.435 | 0.558 | ✅ PASS |
| `regeste_full_text_hybrid_0.7` | 0.481 | 0.742 | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | 0.483 | 0.732 | ✅ PASS |
| `full_text_tfidf_light` | 0.485 | 0.732 | ✅ PASS |
| `outcome_tfidf` | 0.492 | 0.251 | ❌ FAIL (JP) |
| `regeste_tfidf` | 0.400 | 0.362 | ❌ FAIL (JP) |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (citation-based, passes both gates)

**Fundamental Tradeoff Persists:**
- Citation-based modes: PASS adversarial, PASS citation heritage (AUC 0.71-0.74), FAIL branch/tf_metadata/hierarchy
- Text-based modes: PASS branch/tf_metadata, FAIL adversarial (lang_dom ~0.999), FAIL citation heritage (AUC 0.50-0.63)

---

## Dense Embedding Role: COMPLEMENTARY VIEWS ONLY

### What Dense Embeddings Excel At (ACCEPTED Evidence)
1. **Citation Heritage Recovery:** AUC 0.79-0.795 (95% CI [0.76, 0.82]) — **EXCEEDS TF-IDF citation-based (0.71-0.74)**
2. **Cross-lingual Facts Alignment:** Sachverhalt cross-lang same-branch 0.282 (CI [0.267, 0.296]) — **strongest section**
3. **Cross-lingual Holdings Alignment:** Dispositiv cross-lang same-branch 0.150 (CI [0.141, 0.160]) — **moderate**

### What Dense Embeddings Fail At (ACCEPTED Evidence)
1. **Jurist Preference:** FAILS at ALL scales (3yr: 0.005 → 24yr: 0.35-0.38) — true OOS ceiling ~0.53 < 0.7 target
2. **Cross-lingual Reasoning:** Erwaegungen cross-lang same-branch 0.094 (CI [0.086, 0.102]) — below 0.1 threshold
3. **Hierarchy Coherence:** v18 coarse hierarchy max purity 0.65 < 0.70
4. **Linear Hybrids:** PASS adversarial but BELOW TF-IDF baseline (JP 0.66-0.67 vs 0.78-0.79)

---

## Blockers Unchanged (Corpus Lane Dependencies)

| Blocker | Required For | Status |
|---------|--------------|--------|
| bge_ ↔ bger_ ID mapping | Full corpus alignment, 174k dense concatenation | PENDING |
| parquet 2022-2026 (29,520 decisions) | Complete 174k dense embeddings | PENDING |
| Section extraction at 174k scale | Cross-lingual evaluation at full scale | PENDING |

**Legal-distance progress:** 24 yearly checkpoints (2000-2023, 158k+ decisions) with adversarial evaluation COMPLETE. Concatenation to 174k blocked on corpus lane deliveries.

---

## Next Cycle Trigger

**No further same-question cycles justified.** Evaluation lane remains COMPLETE with `continue_recommended=false`.

Next evaluation cycle triggers **ONLY** when legal-distance delivers:
- 174k dense embeddings (concatenated, aligned) for validation against **frozen v35 criteria**
- Citation role embeddings at 174k
- Linear hybrid embeddings at 174k

---

## Artifacts Produced/Updated

1. **`results/evaluation/tfidf_174k_formal_suite_baseline_reverified.json`** — Re-verification results with mutation documentation
2. **`results/evaluation/dense_complementary_acceptance_criteria.json`** — v35 criteria with bootstrap 95% CIs
3. **`results/evaluation/bootstrap_ci_dense_metrics_20261006.json`** — Bootstrap CI validation (10,000 iterations)
4. **`results/evaluation/citation_heritage_174k.json`** — Linked latest citation heritage results
5. **`results/evaluation/v17b_label_normalization_174k_latest.json`** — Linked v17b generalization results
6. **`state/evaluation.json`** — Updated to direction_version 35 with full re-verification record

---

## Evidence Tier

| Finding | Tier | Provenance |
|---------|------|------------|
| TF-IDF 174k baseline (original freeze) | ACCEPTED | 15x independent verification, config hash b51701f5a9c11692 |
| TF-IDF baseline mutation | ACCEPTED_NEGATIVE | Re-verification run 37399175524 vs working directory |
| Dense citation heritage AUC > 0.75 | ACCEPTED | 22yr/144k legal-distance + bootstrap CI |
| Dense cross-lang Sachverhalt > 0.2 | ACCEPTED | 3yr/359 decisions + bootstrap CI |
| Dense cross-lang Dispositiv > 0.1 | ACCEPTED | 3yr/538 decisions + bootstrap CI |
| Dense cross-lang Erwaegungen > 0.1 | ACCEPTED_NEGATIVE | 3yr/510 decisions + bootstrap CI |
| Dense jurist preference FAIL all scales | ACCEPTED | 3/15/19/22/24yr adversarial suite |
| v17b normalization non-generalization | ACCEPTED_NEGATIVE | 5k subsample, NMI decreases |
| v18 coarse hierarchy FAIL | ACCEPTED_NEGATIVE | 4-label branch level, max 0.65 |

---

**Signed:** Evaluation Lane — Factory Direction v35  
**Next Action:** Await corpus lane deliveries for 174k dense embeddings validation