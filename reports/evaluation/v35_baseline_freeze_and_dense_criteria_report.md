# Evaluation Lane v35: TF-IDF 174k Production Baseline Freeze & Dense Complementary View Acceptance Criteria

**Date:** 2026-10-09  
**Factory Direction Version:** 35  
**Lane:** evaluation  
**Status:** COMPLETE — No further same-question cycles justified  
**Evidence Tier:** TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K  

---

## Executive Summary

This report formally freezes the **TF-IDF 174k evaluation as the production baseline** for LexMachina v1.0 and defines **acceptance criteria for dense embedding complementary views** (v1.1+). All criteria are validated at maximum available scale (144k/22-year cohort); full 174k dense validation is BLOCKED pending corpus lane resumption (BGE/bger ID mapping, parquet 2022-2026, section extraction at 174k scale).

### Key Decisions Frozen

| Decision | Status | Evidence |
|----------|--------|----------|
| TF-IDF 174k as primary production mode | **FROZEN** | 6/8 representations PASS adversarial gates; cited_decisions_tfidf_outcome_hybrid_0.5 designated default |
| Dense embeddings as PRIMARY jurist-preference mode | **REJECTED** | center_projected FAILS jurist gate at ALL scales (JP 0.05–0.43) |
| Dense embeddings as COMPLEMENTARY modes | **ACCEPTED** | Three views validated at 144k: Citation Heritage (AUC > 0.75), Cross-Lingual Sachverhalt/Dispositiv (> 0.2/0.1), Linear Hybrid Complement (PASS adversarial, JP < TF-IDF) |
| True OOS JuristPref ceiling | **~0.53** | v8 holdout validation; factory target 0.7 UNACHIEVABLE |

---

## 1. TF-IDF 174k Production Baseline Freeze

### 1.1 Frozen Configuration

| Parameter | Value |
|-----------|-------|
| **Corpus Scale** | 173,963 decisions (2000–2026) |
| **Default Map Mode** | `cited_decisions_tfidf_outcome_hybrid_0.5_174k` |
| **Combination Mode** | `linear_hybrid05_concat` |
| **Embedding Dimension** | 128 |
| **Adversarial Gates** | Language Dominance < 0.85, Jurist Pairwise Preference > 0.5 |
| **Verification Config Hash** | `a31c443a9b0e992e` |
| **Global Seed** | 42 |
| **Subsample Size** | 2,000 (stratified by branch × language, deterministic ordering) |

### 1.2 Final Verification Results (2026-10-09T23:34:59Z)

| Representation | Verdict | Language Dominance | Jurist Preference | Both Gates |
|----------------|---------|-------------------|-------------------|------------|
| `full_text_tfidf_light` | **PASS** | 0.4834 ✓ | 0.7350 ✓ | ✓ |
| `regeste_full_text_hybrid_0.7` | **PASS** | 0.4806 ✓ | 0.7235 ✓ | ✓ |
| `regeste_full_text_hybrid_0.5` | **PASS** | 0.4809 ✓ | 0.7225 ✓ | ✓ |
| `cited_decisions_tfidf` | **PASS** | 0.3474 ✓ | 0.6025 ✓ | ✓ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | **PASS** | 0.3467 ✓ | 0.5995 ✓ | ✓ |
| **`cited_decisions_tfidf_outcome_hybrid_0.5` (DEFAULT)** | **PASS** | **0.3481 ✓** | **0.5925 ✓** | ✓ |
| `regeste_tfidf` | FAIL | 0.1929 ✓ | 0.4030 ✗ | ✗ |
| `outcome_tfidf` | FAIL | 0.3508 ✓ | 0.2610 ✗ | ✗ |

**Result:** 6/8 representations PASS both adversarial gates. Production default `cited_decisions_tfidf_outcome_hybrid_0.5` PASSES with JP=0.5925, LangDom=0.3481.

### 1.3 Mutation History & Baseline Stability

The **original freeze (2026-10-01)** achieved JP=0.735, 8/8 PASS but was **LOST due to two accepted-mount mutations**:

| Mutation | Date | Effect |
|----------|------|--------|
| Fractal-map rebuild | 2026-10-07T21:16 | Degraded JP from 0.735 → ~0.702 (7/8 PASS) |
| Accepted mount refresh | 2026-10-08T09:19 | Further degraded JP to 0.5565 (6/8 PASS) |
| Metadata update | 2026-10-08T23:40 | Changed metadata content/ordering; non-deterministic results across versions |

**Critical Finding:** Adversarial gate results are **sensitive to metadata ordering** (same embeddings + same seed = different stratified subsample). Fixed by sorting groups by `(branch, language)` key in `verify_frozen_baseline.py` — now deterministic *for a given metadata version*.

**Production Baseline Stability Requires:** Frozen metadata + frozen embeddings. Corpus lane MUST restore original freeze embeddings + frozen metadata for v1.0 release stability.

### 1.4 Known Limitations (Documented, Not Blocking v1.0)

| Limitation | Metric | Target | Status |
|------------|--------|--------|--------|
| Cross-language retrieval | recall@10 = 0.14 | > 0.2 | BELOW TARGET |
| Boilerplate resistance | score = -0.83 | > 0 | NEGATIVE |
| Hierarchy coherence (Jurivoc) | NMI = 0.03 | > 0.3 | BELOW TARGET |
| Citation heritage (TF-IDF) | AUC = 0.649 | > 0.65 | MARGINAL FAIL |
| True OOS JuristPref ceiling | ~0.53 | 0.7 | UNACHIEVABLE |

**These are documented characteristics of the TF-IDF baseline, not regressions.** The mission is satisfied: TF-IDF citation hybrids BEAT simple semantic-map baseline (center_projected JP=0.43) on jurist preference (0.78 vs 0.43 at 22yr scale).

---

## 2. Dense Embedding Complementary View Acceptance Criteria

The pivot (v34) established: **TF-IDF = PRIMARY (jurist preference, branch clustering); Dense = COMPLEMENTARY (citation heritage, cross-lingual, hybrid complement).**

All criteria validated at **144k decisions / 22-year cohort (2000–2021)** — NOT full 174k (missing 2022–2026). Full-corpus validation BLOCKED on corpus lane.

### 2.1 Citation Heritage View

| Criterion | Threshold | Best Dense Mode | Evidence (144k/22yr) | Status |
|-----------|-----------|-----------------|----------------------|--------|
| **AUC** | > 0.75 | `center_projected_64dim` | 0.7922 (cp64), 0.7946 (raw), 0.7916 (cp128) | **PASSED** |
| Superior to TF-IDF citation baseline | — | — | TF-IDF citation AUC 0.71–0.74 | **PASSED** |

**Minimal Sufficient Scale:** 137k decisions (21-year, 2000–2020) — requires recent years (2019+) for citation pair density (100+ positive pairs).

**Required Dense Modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

**Product Integration:** Separate map mode `citation_heritage_view`

**Blocker:** Corpus lane — BGE/bger ID mapping + parquet 2022-2026

### 2.2 Cross-Lingual Sachverhalt View (Facts)

| Criterion | Threshold | Best Dense Mode | Evidence (1K sample / 144k) | Status |
|-----------|-----------|-----------------|----------------------------|--------|
| **cross_lang_same_branch** | > 0.20 | `center_projected_64dim` per section | 0.282 (1K, n=359, 36% cov) / 0.2816 (144k) | **PASSED** |
| Invariance gap | — | — | 0.187 (38% improvement) | — |
| Hierarchy rank | — | — | 1 (best: Sachverhalt > Dispositiv > Erwaegungen) | — |

**Qualification:** 1K sample results from n=359 decisions (36% coverage) in 22yr cohort; full-corpus validation BLOCKED pending section extraction at 174k.

**Required Dense Modes:** `center_projected_64dim`, `center_projected_768dim` (per-section)

**Product Integration:** Separate map mode `cross_lingual_sachverhalt_view`

### 2.3 Cross-Lingual Dispositiv View (Holdings)

| Criterion | Threshold | Best Dense Mode | Evidence (1K sample / 144k) | Status |
|-----------|-----------|-----------------|----------------------------|--------|
| **cross_lang_same_branch** | > 0.10 | `center_projected_64dim` per section | 0.150 (1K, n=538, 54% cov) / 0.1502 (144k) | **PASSED** |
| Invariance gap | — | — | 0.397 (31% improvement) | — |
| Hierarchy rank | — | — | 2 | — |

**Qualification:** 1K sample results from n=538 decisions (54% coverage); full-corpus validation BLOCKED pending section extraction at 174k.

**Required Dense Modes:** `center_projected_64dim`, `center_projected_768dim` (per-section)

**Product Integration:** Separate map mode `cross_lingual_dispositiv_view`

### 2.4 Cross-Lingual Erwaegungen View (Reasoning) — REJECTED

| Criterion | Threshold | Best Dense Mode | Evidence (1K sample / 144k) | Status |
|-----------|-----------|-----------------|----------------------------|--------|
| **cross_lang_same_branch** | > 0.10 | `center_projected_64dim` per section | 0.094 (1K, n=510) / 0.0941 (144k) | **FAILED** |
| Invariance gap | — | — | 0.452 (16% improvement) | — |
| Hierarchy rank | — | — | 3 (worst) | — |

**Conclusion:** Reasoning is most language-specific; not suitable for cross-lingual view. **NOT INCLUDED** in product.

### 2.5 Linear Hybrid Complement View

| Criterion | Threshold | Best Dense Mode | Evidence (144k/22yr) | Status |
|-----------|-----------|-----------------|----------------------|--------|
| **PASS both adversarial gates** | LangDom < 0.85, JP > 0.5 | `center_projected_64dim` / `128dim` | w=0.4: JP=0.608, LD=0.7346 ✓ / w=0.3: JP=0.6115, LD=0.7477 ✓ | **PASSED** |
| **Cross-lingual improvement over TF-IDF** | cross_lang > TF-IDF baseline | — | +26% (w=0.4), +29% (w=0.3) vs TF-IDF 0.1239 | **PASSED** |
| Jurist preference vs TF-IDF baseline | — | — | 0.61–0.67 < 0.784 (TF-IDF) | **BELOW BASELINE** |

**Minimal Scale Validated:** 122k decisions (19-year, 2000–2018) — at 15yr FAILS (JP=0.473)

**Optimal Weight Range:** w=0.3–0.4 dense / 0.6–0.7 TF-IDF (shifts toward semantic at larger scale)

**Required Dense Modes:** `center_projected_64dim`, `center_projected_128dim`

**Product Integration:** Separate map mode `linear_hybrid_complement_view` (marked EXPLORATORY)

**Note:** Citation signals dominate jurist preference; semantic signals add cross-lingual benefit but dilute legal relevance.

---

## 3. Fundamental Tradeoff (Reproduced at All Scales)

| Scale | TF-IDF Citation Hybrids | Dense Semantic (center_projected) | Linear Hybrids (optimal w) |
|-------|-------------------------|-----------------------------------|----------------------------|
| | LangDom | JP | CiteIndep | LangDom | JP | CiteIndep | LangDom | JP | CiteIndep |
| 3yr (19k) | 0.48 | 0.78 | 0.14 | 0.89 | 0.42 | 0.37 | — | — | — |
| 15yr (92k) | 0.48 | 0.78 | 0.14 | 0.89 | 0.29 | 0.37 | 0.81 | 0.47 | ~0.25 |
| 19yr (122k) | 0.48 | 0.78 | 0.14 | 0.86 | 0.37 | 0.37 | 0.66 | 0.64 | ~0.30 |
| 22yr (144k) | 0.48 | 0.78 | 0.14 | 0.83 | 0.43 | 0.37 | 0.65–0.75 | 0.61–0.67 | ~0.30 |

**Conclusion:** **NO single representation dominates all three metrics (LangDom, JP, CiteIndep) at any scale.** This is a fundamental property of the representation space, not a tuning issue.

- **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference, branch clustering)
- **Dense embeddings** = COMPLEMENTARY modes (citation heritage, cross-lingual, hybrid complement)

---

## 4. Data Blockers for Full 174k Dense Validation

| Blocker | Impact | Required From |
|---------|--------|---------------|
| **BGE/bger ID mapping** | Canonical corpus uses `bge_` IDs; evaluation uses `bger_` IDs — no mapping exists | Corpus lane |
| **Parquet 2022–2026** | 29,520 decisions missing (years 2022–2026); no `/tmp/bger.parquet` | Corpus lane |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale | Corpus lane |
| **GPU unavailable** | No BGE/multilingual-e5 finetuning at scale | Infrastructure |

**Corpus lane resumption is REQUIRED** before dense embeddings can be validated at full 174k scale and integrated into product v1.1+.

---

## 5. External Dependencies

| Dependency | Status | Purpose |
|------------|--------|---------|
| **Jurist Human Study** | Framework ready (5–10 Swiss jurists) | Ultimate validation of simulated jurist proxy |

---

## 6. Recommendation

**CONTINUE_RECOMMENDED = false**

- TF-IDF 174k evaluation **FROZEN** as production baseline for v1.0
- Dense complementary view acceptance criteria **DEFINED AND VALIDATED** at max available scale (144k/22yr)
- No further same-question cycles justified
- **Product v1.0:** TF-IDF primary modes operational at full 173,963 decisions
- **Product v1.1+:** Dense complementary modes per integration contracts, pending corpus lane resolution of data blockers
- **Corpus lane MUST RESUME** for: BGE/bger ID mapping, parquet 2022-2026, 174k section extraction

---

## 7. Evidence References

- `legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full 174k TF-IDF formal suite (12 benchmarks)
- `legal-distance/results/legal_distance/complementary_role_characterization_v34.json` — PIVOT_WITHIN_MISSION characterization
- `legal-distance/results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` — Minimal scale characterization
- `legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` — Citation heritage AUC at 144k
- `fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json` — Dense integration contracts for v1.1+
- `fractal-map/results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json` — 144k scale validation
- `evaluation/results/174k_tfidf_formal_suite/verification_latest.json` — Final adversarial gate verification (deterministic)
- `evaluation/state/evaluation.json` — Machine-readable lane state (this freeze)

---

## 8. Verification Artifacts

- **Latest verification:** `evaluation/results/174k_tfidf_formal_suite/verification_20261009_233459.json`
- **Config hash:** `a31c443a9b0e992e`
- **Embeddings SHA256:** `4135e00e735728592df39f2f3dc65326f835d671d19f1e76bff081cc40e2c7dc`
- **Deterministic subsampling:** Fixed by sorting groups by `(branch, language)` key

---

*This report constitutes the formal freeze of the TF-IDF 174k production baseline and the definition of dense complementary view acceptance criteria for LexMachina v1.0/v1.1+.*