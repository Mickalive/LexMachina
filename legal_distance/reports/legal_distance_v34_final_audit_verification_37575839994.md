# Legal Distance v34 Final Audit Verification — GitHub Run 37575839994

**Factory Direction v34 | Legal-Distance Lane | ACCEPTED Evidence Tier**

---

## Summary

**Status**: FINAL_AUDIT_VERIFICATION_COMPLETE  
**Lane State**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: FALSE  
**Evidence Tier**: ACCEPTED  

All 8/8 `test_complementary_role_v34.py` assertions PASSED. The PIVOT_WITHIN_MISSION characterization of dense embeddings' complementary role alongside TF-IDF citation hybrids is **complete** at maximum available evaluated scale.

---

## Verified Findings (Reproduced)

| Finding | Evidence | Status |
|---|---|---|
| **Citation Heritage Superiority** | Dense (cp64) AUC 0.79-0.85 > TF-IDF citation 0.71-0.74 > TF-IDF text 0.50-0.63 | ✅ ACCEPTED |
| **Minimal Scale for Citation Heritage** | 21yr/137k (100+ positive pairs) — first scale with AUC > 0.75 on cp64 | ✅ ACCEPTED |
| **Section Cross-Lingual Hierarchy** | Sachverhalt 0.282 > Dispositiv 0.150 > Erwaegungen 0.094 (cp64 cross_lang_same_branch) | ✅ ACCEPTED |
| **Linear Hybrid Complement** | PASS adversarial at w=0.3-0.4 (19yr+), JP 0.61-0.67 < TF-IDF 0.78-0.79 | ✅ ACCEPTED |
| **Two-Mode Tradeoff Fundamental** | No single representation dominates JP + LangDom + CiteIndep at any scale | ✅ ACCEPTED |
| **True OOS JuristPref Ceiling** | ~0.53 < 0.7 factory target (v8 holdout) | ✅ ACCEPTED |
| **TF-IDF 174k Primary Validated** | LangDom=0.5785 PASS, beats semantic baseline (JP 0.78 vs 0.43) | ✅ ACCEPTED |
| **Data Blockers Identified** | bge_/bger_ mapping, parquet 2024-2026 (15.5k), 174k section extraction | ✅ ACCEPTED |

---

## Scale Characterization Reproduction

The `characterize_dense_complementary_views.py` experiment on 12k ACCEPTED dense embeddings (2000-2002) reproduces **identical scale-dependent patterns**:

| Metric | 1k | 2k | 4k | 6k | 8k | 10k | 12.5k | Trend |
|---|---|---|---|---|---|---|---|---|
| Cross-lang same-branch | 0.66 | 0.97 | 0.97 | 1.0 | 1.0 | 0.98 | 0.96 | ↗ plateau |
| Legal area purity | 0.61 | 0.49 | 0.48 | 0.48 | 0.48 | 0.45 | 0.48 | ↘ |
| Branch k-NN@1 | 0.96 | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 | ↗ plateau |

**Critical caveat**: The "jurist proxy" (branch neighbor rate) saturates near 1.0 on this homogeneous 12k sample and **does not correlate** with real adversarial jurist preference (dense embeddings FAIL at all scales: JP 0.05–0.43). The proxy measures branch label coherence, not legal usefulness.

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | PRODUCTION v1.0 | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | READY v1.1+ | Jurist explores doctrinal lineage via shared citations |
| **Cross-Lingual** | `center_projected_64dim` per section (sachverhalt > dispositiv) | BLOCKED v1.1+ | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat` w=0.4 (22yr+) / w=0.3 (19yr) | EXPLORATORY v1.1+ | Jurist trades some legal relevance for cross-lingual reach |

---

## Data Blockers (Unchanged — Require Corpus Lane)

| Blocker | Impact | Required For |
|---|---|---|
| **BGE/bger ID mapping** | Cannot align published/unpublished decision IDs | 174k citation heritage evaluation, full section cross-lingual |
| **Parquet 2024–2026** | 15,536 decisions missing embeddings | 174k completion (173,963 → 189,499 target) |
| **Section extraction 174k** | No Sachverhalt/Erwaegungen/Dispositiv at scale | Full-corpus cross-lingual view density |

**Note**: 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (AUC > 0.75 at 24yr/158k), contradicting progress.json 'failed' flag. Only 2024–2026 are genuinely missing.

---

## Recommendation

**CONTINUE = FALSE** — No further same-question cycles justified.

The complementary role characterization is complete at maximum available evaluated scale:
- **24yr/158k** for citation heritage (730 positive pairs, AUC 0.767–0.85)
- **165k** formal evaluation suite (all center_projected variants FAIL jurist gate)
- **1K sample** for section cross-lingual (Sachverhalt/Dispositiv PASS, Erwaegungen FAIL)

**Next Actions (Dependent on Corpus Lane Resumption)**:
1. Corpus lane: BGE/bger mapping + 2024–2026 parquet + 174k section extraction
2. When unblocked: Compute 174k dense embeddings for all three complementary views
3. Evaluation lane: Freeze TF-IDF 174k as production baseline; apply acceptance criteria for dense view promotion
4. Product lane: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones
5. No new Frontier team — portfolio v7 confirmed, all teams TERMINATED

---

## Evidence References

```json
{
  "citation_heritage_21yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json",
  "citation_heritage_22yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json",
  "citation_heritage_24yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json",
  "section_crosslingual": "legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json",
  "linear_hybrid_sweep_22yr": "legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json",
  "scale_characterization_12k": "legal_distance/results/dense_complementary_characterization/scale_characterization_results.json",
  "evaluation_v25_174k_suite": "/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "v8_oos_validation": "legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json",
  "test_results": "tests/legal_distance/test_complementary_role_v34.py (8/8 PASS)"
}
```

---

**Report Status**: FINAL — Complementary role characterization complete. Awaiting corpus lane unblocking for 174k deployment.