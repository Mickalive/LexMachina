# Evaluation Lane — Factory Direction v35 Final Confirmation

**Run ID:** EVALUATION_V35_PRODUCTION_BASELINE_FROZEN_20261007
**Date:** 2026-10-07
**Factory Direction Version:** 35
**Lane Status:** COMPLETE
**Evidence Tier:** TF-IDF_ACCEPTED_DENSE_UNVALIDATED
**Continue Recommended:** false

---

## Factory Direction v35 Question

> Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv).

---

## Confirmation: Work COMPLETE

Both deliverables from the v35 question were **already completed and frozen** in factory direction v34. No new discriminating experiments were required or justified for v35. This confirmation documents the alignment to v35.

### 1. TF-IDF 174k Production Baseline — FROZEN (ACCEPTED)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Best Jurist Preference (JP) | 0.7345 | > 0.5 | **PASS** |
| Language Dominance (LD) | 0.4773 | < 0.85 | **PASS** |
| Representations Tested | 8/8 | All PASS both gates | **PASS** |
| Beats Semantic Baseline (center_projected JP=0.43) | +0.3045 | Mission requirement | **PASS** |
| Production Default Mode | `cited_decisions_tfidf_outcome_hybrid_0.5` | — | **FROZEN** |

**Evidence:** `results/evaluation/tfidf_174k_formal_suite_baseline.json` (config hash: `b51701f5a9c11692`, benchmark suite hash: `4323f833fa72366a`)

All 8 TF-IDF representations pass both adversarial gates at full 173,963 decisions. The formal suite uses frozen v3 harness thresholds and authoritative branch-only stratified subsampling (500 per branch × 4 branches = 2000).

### 2. Dense Embedding Complementary View Criteria — DEFINED AND FROZEN

| Criterion | Threshold | Validation Status | Evidence |
|-----------|-----------|-------------------|----------|
| Citation Heritage AUC | > 0.75 | **PASSED** at 22yr/144k (0.792–0.795) — FAILS at full 174k (0.482) | `dense_complementary_acceptance_criteria.json` |
| Cross-Lingual Sachverhalt | > 0.2 | **PASSED** at 1K sample (0.282) — BLOCKED at 174k (section extraction required) | `dense_complementary_acceptance_criteria.json` |
| Cross-Lingual Dispositiv | > 0.1 | **PASSED** at 1K sample (0.150) — BLOCKED at 174k (section extraction required) | `dense_complementary_acceptance_criteria.json` |
| Linear Hybrid Complement | JP > 0.60 at w=0.3–0.4 | **PASSED** at 22yr — BLOCKED at 174k (no 174k dense embeddings) | `dense_complementary_acceptance_criteria.json` |

**Evidence:** `results/evaluation/dense_complementary_acceptance_criteria.json` (source: legal-distance v34 ACCEPTED evidence at 22-year/144k scale)

### 3. Critical Accepted Negative Findings (Preserved)

| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS Jurist Preference Ceiling | ~0.53 | Dense embeddings cannot be primary navigation mode (factory target 0.7) |
| v18 Coarse Hierarchy Max Purity | 0.65 < 0.7 | Coarse legal taxonomy recovery fails for ALL representations |
| Citation Heritage Recall@10 | 0.0066 | Citation heritage is ranking signal, not retrieval signal |
| Citation Heritage 174k AUC | 0.482 < 0.75 | Full corpus FAILS; partial 22yr PASS does not generalize |
| TF-IDF Universal 174k Fails | Hierarchy, clustering, stability, boilerplate, cross-lang | Known limitations of primary mode — documented |

---

## Data Blockers (Unchanged from v34)

1. **BGE/bger ID mapping** — Cannot align 174k dense embeddings with evaluation metadata
2. **Parquet 2022–2026** — 29,520 decisions missing from parquet
3. **Section extraction at 174k** — Required for cross-lingual section alignment validation

These are **corpus lane** deliverables. Evaluation lane cannot proceed with dense validation until resolved.

---

## Validation Protocol (FROZEN)

| View | Protocol |
|------|----------|
| Citation Heritage | Run `validate_citation_heritage_174k.py` on frozen 137k pair pool with 174k dense embeddings |
| Cross-Lingual | Compute section-segmented embeddings (sachverhalt/dispositiv/erwaegungen), evaluate `cross_lang_same_branch` per section |
| Linear Hybrid | Run formal suite adversarial gates on hybrid weights 0.3, 0.35, 0.4 with 174k dense + TF-IDF |
| Scale | All criteria must hold at full 174k (not subsampled) |

---

## Monitoring Status

- **Monitor Check #323** (GitHub run 37673564960): No new awaited representations detected
- **TF-IDF 174k Baseline:** CONFIRMED_FROZEN (8/8 representations, 15× historical independent verification)
- **Dense 174k:** AWAITED (24 yearly checkpoints in legal-distance covering 2000–2023, 158k+ decisions; concatenation blocked)
- **Last Adversarial Verification:** 2026-10-01
- **No further same-question cycles justified.**

---

## Next Evaluation Cycle Trigger

The next evaluation cycle will trigger **ONLY** when legal-distance delivers 174k dense embeddings for validation against the **already frozen** acceptance criteria. No criteria changes are anticipated.

---

## Evidence References

1. `results/evaluation/tfidf_174k_formal_suite_baseline.json` — Frozen production baseline
2. `results/evaluation/dense_complementary_acceptance_criteria.json` — Frozen dense criteria
3. `results/evaluation/citation_heritage_174k.json` — 174k citation heritage evaluation (AUC 0.482 FAIL)
4. `results/evaluation/v17b_label_normalization_174k_latest.json` — Label normalization at 174k
5. `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — Coarse hierarchy NEGATIVE
6. `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` — Bootstrap CIs for dense criteria
7. `/tmp/lex_accepted/legal-distance/state/legal-distance.json` — Legal-distance v34 ACCEPTED state
8. `/tmp/lex_accepted/fractal-map/state/fractal-map.json` — Fractal-map v34/v35 ACCEPTED state

---

## Audit Trail

- **Final v34 Verification:** GitHub run 37574492135 (2026-10-07T05:15:00Z)
- **Independent Artifact Audit:** GitHub run 37598492933 (2026-10-07T09:30:00Z) — 12 tests PASSED
- **Audit Revision Applied:** Corrected evidence_tier to TF-IDF_ACCEPTED_DENSE_UNVALIDATED, preserved negative findings as first-class evidence
- **Orchestration Defect Documented:** V28-pattern control plane mounting defect persists in `/tmp/lex_control` (shows RUN) while workspace state correctly shows COMPLETE — infrastructure defect, NOT lane failure

---

## Conclusion

**Evaluation lane work for factory direction v35 is COMPLETE.** The TF-IDF 174k production baseline is frozen as the primary navigation mode (beating semantic baseline JP 0.7345 vs 0.43). Dense embedding complementary view acceptance criteria are defined and frozen. All data blockers are upstream (corpus lane). No further same-question cycles are justified.

**Recommendation to Factory Director:** Resume corpus lane for BGE/bger ID mapping, parquet 2022–2026, and section extraction at 174k scale.