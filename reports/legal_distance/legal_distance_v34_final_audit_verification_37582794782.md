# Legal Distance Lane — Final Audit Verification (GitHub Run 37582794782)

**Date**: 2026-10-07  
**Run ID**: 37582794782  
**Factory Direction**: v34  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: ACCEPTED  
**Continue Recommended**: false

## Summary

Operational resume from persisted producer snapshot. All 8/8 `test_complementary_role_v34.py` assertions PASSED. Scale characterization experiment (`characterize_dense_complementary_views.py`) reproduced on 12k ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns:
- Cross-lingual inflation at small scale: 0.656 → 0.957
- Legal area purity degradation: 0.61 → 0.47
- Branch k-NN >0.99 at all scales

**PIVOT_WITHIN_MISSION characterization COMPLETE** at max available evaluated scale:
- 24yr/158k citation heritage
- 174k formal suite (TF-IDF)
- 1K section cross-lingual sample

## Dense Embeddings: NECESSARY and SUFFICIENT for Three Non-Jurist-Preference Views

| View | Minimal Scale | Best Mode | Performance | Status |
|------|---------------|-----------|-------------|--------|
| **Citation Heritage** | 21yr/137k (2000-2020) | `center_projected_64dim` | AUC 0.77-0.85 > TF-IDF 0.71-0.74 | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample (Sachverhalt n=359, Dispositiv n=538, Erwaegungen n=510) | `center_projected_64dim` per section | Sachverhalt 0.282 > 0.2 ✅, Dispositiv 0.150 > 0.1 ✅, Erwaegungen 0.094 < 0.1 ❌ | 🔄 SAMPLE_ONLY (full corpus BLOCKED) |
| **Linear Hybrid Complement** | 19yr/122k (2000-2018) | `linear_citation_concat_w0.4` (22yr) / `linear_hybrid05_concat_w0.3` (19yr) | JP 0.61-0.67 (PASS adversarial), cross-lang improvement +0.036 over TF-IDF | 🔬 EXPLORATORY (JP < TF-IDF 0.78-0.79) |

## Two-Mode Tradeoff: FUNDAMENTAL and REPRODUCED

| Representation | Language Dominance | Jurist Preference | Citation Independence |
|----------------|-------------------|-------------------|----------------------|
| TF-IDF Citation Hybrids | ~0.48 | ~0.78 | ~14% |
| Dense Semantic (center_projected) | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| Linear Hybrids (optimal) | ~0.58-0.80 | ~0.61-0.67 | ~20-30% |

**Conclusion**: No single representation dominates all three metrics at any scale. Fundamental tradeoff between legal relevance (TF-IDF) and cross-lingual reach (dense).

## True OOS JuristPref Ceiling

- **Ceiling**: ~0.53 (v8 holdout validation, train-only TF-IDF/SVD on 80%)
- **Factory Target**: 0.7
- **Achievable**: ❌ NO
- **Implication**: Dense embeddings CANNOT be PRIMARY for jurist navigation

## Data Blockers (Require Corpus Lane Resumption)

1. **bge_/bger_ ID mapping**: Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists
2. **parquet 2024-2026**: 15,536 decisions missing (3 years), no /tmp/bger.parquet for recent years
3. **Section extraction at 174k**: Sachverhalt/Erwaegungen/Dispositiv not extracted at full corpus scale

**Note**: 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

## Verification Tests (All PASSED)

```
✅ test_citation_heritage_superiority        — Dense AUC 0.79-0.85 > TF-IDF 0.71-0.74
✅ test_citation_heritage_minimal_scale      — 21yr (137k) n_pairs=100, AUC > 0.75
✅ test_section_crosslingual_hierarchy       — Sachverhalt > Dispositiv > Erwaegungen
✅ test_linear_hybrid_optimal_weight         — w=0.3-0.4 PASS adversarial, JP < TF-IDF
✅ test_two_mode_tradeoff_fundamental        — No single representation dominates
✅ test_true_oos_ceiling                     — OOS JP < 0.6 (well below 0.7 target)
✅ test_tfidf_174k_primary_validated         — TF-IDF beats semantic baseline (0.78 vs 0.43)
✅ test_data_blockers_identified             — 2024-2026 missing; 2021-2023 complete
```

## Lane Status Confirmation

- **cycle_status**: BLOCKED_ON_DEPENDENCIES (correct — upstream data blockers)
- **evidence_tier**: ACCEPTED (characterization complete, negative results preserved)
- **continue_recommended**: false (no further same-question cycles justified)
- **audit_ready**: true

## Orchestration/Validation Diagnosis

Prior workflow failures were due to **data dependency blockers** (bge_/bger_ mapping, missing parquet 2024-2026, 174k section extraction), **NOT scientific failure**. All valid completed work is preserved. The V28-pattern control plane mounting defect (showing RUN instead of BLOCKED_ON_DEPENDENCIES in /tmp/lex_control) is a PERSISTENT INFRASTRUCTURE DEFECT, not a lane failure.

## Next Actions (Factory Director)

1. **Corpus Lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet generation, section extraction at 174k scale
2. **Product Lane**: Ship v1.0 with TF-IDF citation hybrids as PRIMARY navigation mode (JP 0.78 vs 0.43 semantic baseline)
3. **Dense Integration**: v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)