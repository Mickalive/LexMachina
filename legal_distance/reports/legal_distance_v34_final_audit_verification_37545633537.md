# Legal Distance v34: Final Audit Verification — GitHub Run 37545633537

**Factory Direction v34 | Legal-Distance Lane | ACCEPTED Evidence Tier**

---

## Verification Summary

| Field | Value |
|---|---|
| **Run ID** | 37545633537 |
| **Date** | 2026-10-06 |
| **Status** | FINAL_AUDIT_VERIFICATION_COMPLETE |
| **Lane State** | BLOCKED_ON_DEPENDENCIES |
| **Continue Recommended** | FALSE |
| **Evidence Tier** | ACCEPTED |

---

## Test Results

All **8/8** assertions in `test_complementary_role_v34.py` **PASSED**:

```
✅ Citation Heritage: Dense AUCs > 0.75, cp64 gap 6.5× raw
✅ Minimal Scale: 21yr (137k) n_pairs=100, AUC > 0.75
✅ Cross-lingual Hierarchy: Sachverhalt > Dispositiv > Erwaegungen
✅ Linear Hybrid: PASS adversarial at w=0.3–0.4, JP < TF-IDF baseline
✅ Two-Mode Tradeoff: Fundamental, no single representation dominates
✅ True OOS Ceiling: ~0.53 < 0.7 factory target
✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
✅ Data Blockers: 2000–2023 complete, 2024–2026 missing
```

---

## Question Answered

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

**Answer — Three complementary modes at characterized minimal scales:**

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21 years / 137k decisions (2000–2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21–24yr (137k–158k) |
| **Section Cross-Lingual Alignment** | 1K sample with extracted sections | Section-specific `center_projected_64dim` | Sachverhalt > 0.2; Dispositiv > 0.1 | ✅ **PASSED** at sample; **BLOCKED** at 174k |
| **Linear Hybrid Complement** | 19 years / 122k decisions (2000–2018) | `linear_citation_concat` / `linear_hybrid05_concat` at w=0.3–0.4 | PASS both adversarial gates | ✅ **PASSED** at 19yr+; **NOT primary** |

---

## Key Findings Reproduced

1. **Citation Heritage**: Dense embeddings **SUPERIOR** to TF-IDF for doctrinal lineage recovery (AUC 0.77–0.85 vs 0.71–0.74). Emerges at 21yr/137k when sufficient citation pairs exist (>100). Center projection preserves capability with 6.5× better similarity gap.

2. **Section Cross-Lingual Hierarchy**: Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094). Legal facts align best cross-lingually; reasoning is most language-specific. Center projection improves all sections 16–38%.

3. **Linear Hybrid Complement**: PASS adversarial gates at 19yr+ (w=0.3–0.4) but **remain BELOW TF-IDF baseline** (JP 0.61–0.67 vs 0.78–0.79). Add cross-lingual benefit (0.160 vs 0.124) but dilute legal relevance.

4. **Two-Mode Tradeoff**: Fundamental and irreducible. No single representation dominates Jurist Preference + Language Dominance + Citation Independence at any scale.

5. **True OOS Ceiling**: Jurist preference ceiling ~0.53 < 0.7 factory target. Dense embeddings **cannot be PRIMARY** for jurist navigation.

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact |
|---|---|
| **BGE/bger ID mapping** | Published (bge_) vs unpublished (bger_) ID systems — no cross-mapping |
| **Parquet 2024–2026** | 15,536 decisions missing embeddings |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at scale |

**Note**: 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (AUC > 0.75 at 24yr/158k). Only 2024–2026 are genuinely missing.

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage via shared citations |
| **Cross-Lingual** | Section-specific `center_projected_64dim` | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Complement** | `linear_citation_concat_w0.4` | **EXPLORATORY v1.1+** | Jurist trades some legal relevance for cross-lingual reach |

---

## Recommendation

**CONTINUE = FALSE** — No further same-question cycles justified.

The complementary role characterization is **COMPLETE** at maximum available evaluated scale (24yr/158k citation heritage, 174k formal suite, 1K section cross-lingual).

**Next actions dependent on Corpus Lane resumption:**
1. Corpus lane: BGE/bger mapping + 2024–2026 parquet + 174k section extraction
2. When unblocked: Compute 174k dense embeddings for all three complementary views
3. Evaluation lane: Apply frozen acceptance criteria for dense view promotion
4. Product lane: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`
- `tests/legal_distance/test_complementary_role_v34.py` — **ALL TESTS PASSED**

---

**Verification Complete — Lane Audit-Ready**