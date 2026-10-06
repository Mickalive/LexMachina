# Evaluation Lane Verification Report — GitHub Run 37399175524

**Run ID:** `verification_37399175524_20261006_014640`
**Factory Direction Version:** 34
**Date:** 2026-10-06T01:46:43Z
**Evidence Tier:** ACCEPTED (verification of existing ACCEPTED baseline)

---

## Executive Summary

This verification run confirms the **TF-IDF 174k production baseline remains operational** on the current working directory embeddings, with the production default (`cited_decisions_tfidf_outcome_hybrid_0.5`) passing both adversarial gates. However, the working directory embeddings were regenerated after the frozen baseline verification, resulting in metric drift from the exact frozen values.

**Key Findings:**
1. **Production baseline OPERATIONAL**: 7/8 representations PASS both adversarial gates (LangDom < 0.85, JuristPref > 0.5)
2. **Production default PASSES**: `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4236, JP=0.7020
3. **Metric drift from frozen baseline**: JP=0.7020 vs frozen 0.7345 (Δ=-0.0325); config hash differs (04b6d5f0c13131ef vs b51701f5a9c11692)
4. **Working directory embeddings regenerated**: Created at 2026-10-06T01:27Z, AFTER the 00:52Z frozen baseline reproduction
5. **No further same-question cycles justified**: Evaluation lane deliverable for v34 COMPLETE

---

## 1. Verification Configuration (Frozen Harness v3)

| Parameter | Value |
|---|---|
| Global seed | 42 |
| Subsample size | 2,000 (stratified by branch × language) |
| Subsample seed | 42 |
| NN backend | sklearn exact (cosine) |
| Language dominance threshold | < 0.85 |
| Jurist pairwise threshold | > 0.5 |
| Config hash | `04b6d5f0c13131ef` |

---

## 2. Adversarial Results (Exact k-NN on Stratified Subsample)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| `regeste_full_text_hybrid_0.7` | 0.4810 ✅ | 0.7420 ✅ | ✅ PASS |
| `full_text_tfidf_light` | 0.4849 ✅ | 0.7320 ✅ | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | 0.4828 ✅ | 0.7315 ✅ | ✅ PASS |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4211 ✅ | 0.7125 ✅ | ✅ PASS |
| `cited_decisions_tfidf` | 0.4207 ✅ | 0.7055 ✅ | ✅ PASS |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4236 ✅** | **0.7020 ✅** | ✅ **PASS (PROD)** |
| `regeste_tfidf` | 0.3758 ✅ | 0.6395 ✅ | ✅ PASS |
| `outcome_tfidf` | 0.4578 ✅ | 0.3910 ❌ | ❌ FAIL |

**Summary:** 7/8 PASS, 1 FAIL (`outcome_tfidf` fails jurist preference at JP=0.391)

---

## 3. Comparison with Frozen Baseline

| Metric | Frozen Baseline (b51701f5a9c11692) | This Run (04b6d5f0c13131ef) | Delta |
|---|---|---|---|
| Config hash | `b51701f5a9c11692` | `04b6d5f0c13131ef` | Different |
| Production default JP | 0.7345 | 0.7020 | -0.0325 |
| Production default LangDom | 0.4773 | 0.4236 | -0.0537 |
| All 8 PASS | ✅ Yes | ❌ No (7/8) | -1 |
| Embedding source | Accepted lane (pre-mutation) | Working directory (regenerated 01:27Z) | — |

**Root cause:** Working directory embeddings were regenerated at 2026-10-06T01:27:45Z (after the 00:52Z frozen baseline reproduction). The new embeddings have different file hashes, hence different config hash and metric values.

---

## 4. Production Readiness Assessment

✅ **Product v1.0 can ship with current working directory embeddings:**
- Production default PASSES both adversarial gates (JP=0.7020 > 0.5, LangDom=0.4236 < 0.85)
- 7/8 representations viable for multi-view map modes
- TF-IDF citation hybrids BEAT semantic baseline (center_projected JP ~0.35-0.43)

⚠️ **Exact frozen baseline NOT reproducible from current artifacts:**
- Frozen baseline values (JP=0.7345) require original accepted-lane embeddings
- Accepted lane embeddings were mutated at 2026-10-05T21:27Z (violates immutability invariant)
- Fractal-map lane must restore frozen embeddings to accepted lane for audit compliance

---

## 5. Dense Embedding Complementary View Criteria — STATUS UNCHANGED

Validated against 22-year/144k legal-distance ACCEPTED evidence (unchanged from v34):

| Capability | Metric | Threshold | Status |
|---|---|---|---|
| Citation Heritage | AUC-ROC | > 0.75 | ✅ PASS (0.79-0.80) |
| Cross-lingual Sachverhalt | cross_lang_same_branch@10 | > 0.20 | ✅ PASS (0.282) |
| Cross-lingual Dispositiv | cross_lang_same_branch@10 | > 0.10 | ✅ PASS (0.148-0.150) |
| Cross-lingual Erwaegungen | cross_lang_same_branch@10 | > 0.10 | ❌ FAIL (0.093) |
| Jurist Preference (primary) | JP score | > 0.50 | ❌ FAIL (~0.35-0.43) |

**Conclusion:** Dense embeddings serve ONLY complementary views (citation heritage, cross-lingual sachverhalt/dispositiv), NOT primary navigation.

---

## 6. Blockers & Dependencies

| Blocker | Impact | Resolution |
|---|---|---|
| BGE/bger ID mapping | Cannot align 174k dense embeddings with evaluation metadata | Corpus lane resumption required |
| Parquet 2022-2026 | 29,520 decisions missing from 174k dense computation | Corpus lane resumption required |
| Section extraction 174k | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at scale | Corpus lane resumption required |
| Jurist human study | True OOS JuristPref validation beyond adversarial proxy | External dependency (5-10 Swiss jurists) |

---

## 7. Recommendations

### For Product Lane
- **v1.0 Release**: Ship with TF-IDF citation hybrids as PRIMARY navigation mode (beats semantic baseline JP 0.70 vs 0.43)
- **v1.1+ Enhancements**: Dense embedding integration for citation-heritage view (AUC > 0.75) and cross-lingual view (sachverhalt > 0.2, dispositiv > 0.1)

### For Legal-Distance Lane
- Compute 174k dense embeddings once data blockers resolved
- Focus on: center_projected (citation heritage + cross-lingual), linear hybrids (complement)
- Do NOT pursue center_projected for primary navigation (falsified at all scales)

### For Fractal-Map Lane
- TF-IDF hierarchical modes OPERATIONAL at 174k (3 production modes)
- **MUST**: Restore frozen embeddings (config hash b51701f5a9c11692) to accepted lane for audit compliance
- Dense integration contract: accept embeddings meeting complementary view criteria above

### For Evaluation Lane
- **No further same-question cycles justified** (`continue_recommended: false`)
- Next cycle only when 174k dense embeddings available (corpus lane unblocked)
- Maintain frozen adversarial harness for regression testing

---

## 8. Evidence References (Machine-Readable)

```json
{
  "this_verification": "evaluation/results/174k/formal_suite/evaluation_174k_adversarial_verification_20261006_014640.json",
  "frozen_baseline": "evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_20261006_005230.json",
  "tfidf_v25_formal_suite": "results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "dense_citation_heritage_22year": "results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json",
  "dense_section_crosslingual": "results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json",
  "dense_acceptance_criteria": "results/evaluation/dense_complementary_acceptance_criteria.json",
  "v17b_negative": "evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json",
  "v18_hierarchy_negative": "evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json"
}
```

---

## 9. State Update

The evaluation lane state is updated to reflect:
- `evidence_tier`: ACCEPTED
- `cycle_status`: COMPLETE
- `continue_recommended`: **false** (no additional same-question cycle justified)
- `last_verified_run`: 37399175524
- `last_verified_timestamp`: 2026-10-06T01:46:43Z
- `next_recommendation`: TF-IDF 174k evaluation FROZEN as production baseline; dense embedding acceptance criteria defined and validated; blocked on corpus data for 174k dense evaluation

---

*Report generated by Evaluation Lane verification for GitHub Run 37399175524*