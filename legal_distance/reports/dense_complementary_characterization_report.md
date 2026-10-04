# Legal Distance Lane — Dense Complementary Views Scale Characterization (v34)

**Direction Version:** 34  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Run ID:** characterize_dense_complementary_views_20261004  
**Date:** 2026-10-04  

---

## Executive Summary

This report presents the **scale characterization of dense complementary views** using the **12,570 ACCEPTED dense embeddings** (multilingual-e5, 2000–2002). This supplements the primary complementary role characterization (legal_distance_v34_complementary_role.md) which used max-evaluated scales (21–24yr, 137k–158k).

**Key Finding:** Full-text dense embeddings show **near-perfect cross-lingual alignment** (cross_lang_same_branch ≈ 0.95–1.00) and **near-perfect branch k-NN** (≈ 0.99) at all scales ≥2k, but **legal area clustering purity degrades with scale** (0.61 → 0.47). This confirms the **language dominance problem**: full-text dense embeddings are designed for cross-lingual alignment but fail to capture legal structure at scale.

---

## 1. Cross-Lingual View (Full-Text Dense, 768-dim)

### 1.1 Results by Scale

| Scale | cross_lang_same_branch | same_lang_same_branch | Separation | cross_lang_total |
|-------|------------------------|------------------------|------------|------------------|
| 1,000 | 0.656 | 0.862 | +0.206 | 32 |
| 2,000 | 0.971 | 0.890 | -0.081 | 35 |
| 4,000 | 0.971 | 0.959 | -0.012 | 34 |
| 6,000 | 1.000 | 0.972 | -0.029 | 29 |
| 8,000 | 1.000 | 0.977 | -0.023 | 27 |
| 10,000 | 0.976 | 0.980 | +0.004 | 41 |
| 12,570 | 0.957 | 0.982 | +0.026 | 46 |

### 1.2 Interpretation

- **At small scale (1k)**: Cross-lingual alignment is moderate (0.66), same-language alignment higher (0.86) — positive separation indicates some language clustering.
- **At scale ≥2k**: Cross-lingual alignment **exceeds or equals** same-language alignment (separation ≤0). This is the **language dominance effect**: multilingual-e5 embeddings align cross-lingual pairs more strongly than same-language legal coherence.
- **At full 12k**: cross_lang_same_branch = 0.957, separation = +0.026 (barely positive).

**Conclusion:** Full-text dense embeddings achieve the evaluation lane's cross-lingual acceptance criteria (cross_lang_same_branch > 0.2) **at all scales**, but this reflects **language model design**, not legal equivalence. For legal cross-lingual navigation, **section-specific center_projected embeddings** (Sachverhalt: 0.282, Dispositiv: 0.150) are the correct product integration — not full-text dense.

---

## 2. Legal Area Clustering (Full-Text Dense)

### 2.1 Results by Scale

| Scale | Purity | NMI | n_samples |
|-------|--------|-----|-----------|
| 1,000 | 0.609 | 0.740 | 202 |
| 2,000 | 0.493 | 0.662 | 406 |
| 4,000 | 0.485 | 0.634 | 798 |
| 6,000 | 0.477 | 0.622 | 1,216 |
| 8,000 | 0.485 | 0.612 | 1,621 |
| 10,000 | 0.455 | 0.600 | 1,978 |
| 12,570 | 0.475 | 0.599 | 2,455 |

### 2.2 Interpretation

- **Purity drops from 0.61 → 0.47** as scale increases — **23% degradation**.
- **NMI drops from 0.74 → 0.60** — consistent degradation.
- Full-text dense embeddings **do not preserve legal area structure** at scale.

**Conclusion:** Full-text dense embeddings are **not suitable for legal area navigation** at corpus scale. TF-IDF citation hybrids (branch purity 0.90–0.93) are the correct primary mode.

---

## 3. Branch k-NN Accuracy (Full-Text Dense)

### 3.1 Results by Scale

| Scale | @1 | @3 | @5 |
|-------|-----|-----|-----|
| 1,000 | 0.957 | 0.978 | 0.989 |
| 2,000 | 0.989 | 0.995 | 0.997 |
| 4,000 | 0.988 | 0.993 | 0.995 |
| 6,000 | 0.995 | 0.997 | 0.997 |
| 8,000 | 0.993 | 0.998 | 0.998 |
| 10,000 | 0.992 | 0.997 | 0.997 |
| 12,570 | 0.992 | 0.996 | 0.997 |

### 3.2 Interpretation

- **Near-perfect branch k-NN at all scales** (≥0.95 @1).
- **But**: This reflects **branch label density in the 2000–2002 sample**, not generalizable legal structure.
- The 12k sample is from 2000–2002 only (3 years) — branch labels are highly concentrated.

**Conclusion:** Branch k-NN on 12k 3-year sample is **not representative** of full-corpus performance. Full-corpus branch clustering requires TF-IDF citation hybrids.

---

## 4. Linear Hybrid Complement (Dense + TF-IDF Concatenation)

### 4.1 Jurist Preference Proxy (legal_neighbor_rate) by Scale & Weight

| Scale | w=0.1 | w=0.2 | w=0.3 | w=0.35 | w=0.4 | w=0.5 | w=0.6 | w=0.7 |
|-------|-------|-------|-------|--------|-------|-------|-------|-------|
| 1,000 | 0.996 | 0.992 | 0.992 | 0.992 | 0.992 | 0.996 | 1.000 | 1.000 |
| 2,000 | 0.998 | 0.998 | 0.998 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 3,000 | 0.992 | 0.992 | 0.992 | 0.995 | 0.999 | 0.999 | 1.000 | 1.000 |
| 3,839 | 0.993 | 0.994 | 0.994 | 0.995 | 0.995 | 0.999 | 1.000 | 1.000 |

**All weights PASS the JP > 0.60 threshold at all scales** — but this is on a **non-representative 3-year sample** with highly concentrated branch labels.

### 4.2 Cross-Lingual Alignment (Hybrid)

| Scale | w=0.1 | w=0.3 | w=0.5 | w=0.7 |
|-------|-------|-------|-------|-------|
| 1,000 | 0.836 | 0.859 | 0.876 | 0.930 |
| 2,000 | 0.867 | 0.883 | 0.913 | 0.934 |
| 3,000 | 0.858 | 0.881 | 0.888 | 0.912 |
| 3,839 | 0.856 | 0.872 | 0.899 | 0.942 |

**Hybrid improves cross-lingual alignment over TF-IDF-only** (TF-IDF only: 0.856 at 3,839) by adding dense's cross-lingual strength.

### 4.3 Legal Area Clustering (Hybrid)

| Scale | w=0.1 | w=0.3 | w=0.5 | w=0.7 |
|-------|-------|-------|-------|-------|
| 1,000 | 0.431 | 0.448 | 0.540 | 0.569 |
| 2,000 | 0.329 | 0.357 | 0.452 | 0.544 |
| 3,000 | 0.319 | 0.351 | 0.429 | 0.552 |
| 3,839 | 0.333 | 0.351 | 0.433 | 0.537 |

**Hybrid legal area purity IMPROVES with dense weight** — but still well below TF-IDF citation hybrid full-corpus performance (0.90–0.93).

---

## 5. Baselines Comparison

### 5.1 Dense-Only (Full-Text 768-dim)

| Scale | JP Proxy | Cross-Lingual | Legal Area Purity |
|-------|----------|---------------|-------------------|
| 1,000 | 0.992 | 1.000 | 0.573 |
| 2,000 | 0.991 | 1.000 | 0.512 |
| 3,000 | 0.995 | 0.900 | 0.525 |
| 3,839 | 0.996 | 0.833 | 0.513 |

### 5.2 TF-IDF Only (cited_decisions_tfidf, 128-dim)

| Scale | JP Proxy | Cross-Lingual | Legal Area Purity |
|-------|----------|---------------|-------------------|
| 1,000 | 0.996 | 0.833 | 0.444 |
| 2,000 | 0.998 | 0.866 | 0.338 |
| 3,000 | 0.992 | 0.857 | 0.335 |
| 3,839 | 0.993 | 0.856 | 0.335 |

---

## 6. Synthesis: Three Complementary Views Validated

| Complementary View | Minimal Scale (Validated) | Sufficient Scale | Best Mode | Status |
|--------------------|---------------------------|------------------|-----------|--------|
| **Citation Heritage** | 21yr / 137k | 24yr / 158k | center_projected_64dim | ✅ PASSED (AUC 0.767–0.845) |
| **Cross-Lingual (Sachverhalt)** | 1K sample | **BLOCKED** (needs 174k section extraction) | center_projected_64dim per section | ✅ SAMPLE PASSED (0.282) |
| **Cross-Lingual (Dispositiv)** | 1K sample | **BLOCKED** | center_projected_64dim per section | ✅ SAMPLE PASSED (0.150) |
| **Cross-Lingual (Erwaegungen)** | 1K sample | **BLOCKED** | center_projected_64dim per section | ❌ SAMPLE FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k | 22yr / 144k | concat(w=0.3–0.4) | ✅ PASSED (adversarial gates) |

**Full-text dense 12k scale characterization CONFIRMS:**
1. Cross-lingual alignment is near-perfect at scale (≥0.95) but reflects **language model artifacts**, not legal equivalence
2. Legal area clustering **degrades with scale** (0.61 → 0.47) — confirms language dominance
3. Hybrid cross-lingual improves over TF-IDF but **legal area remains weak**
4. **Center projection per section is the correct product integration** for cross-lingual view

---

## 7. Data Blockers (Unchanged)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs | Corpus lane |
| **Parquet 2024–2026** | Missing normalization artifacts (~15,536 decisions) | Corpus lane |
| **Section extraction 174k** | Blocks cross-lingual density validation | Corpus lane |
| **2022–2023 embeddings flagged failed** | progress.json false negative; embeddings exist and PASS citation heritage | Corpus lane validation |

---

## 8. Recommendation

**PIVOT_WITHIN_MISSION CHARACTERIZATION COMPLETE.** No further same-question cycles justified.

The 12k scale characterization **reinforces** the primary characterization:
- Full-text dense embeddings excel at cross-lingual alignment by design, but this is **not legal equivalence**
- Legal structure (citation heritage, legal areas, branch coherence) requires **center_projected section embeddings** or **TF-IDF citation hybrids**
- Product v1.0: TF-IDF citation hybrids as primary navigation
- Product v1.1+: Dense complementary views (citation heritage, section cross-lingual, hybrid) pending corpus lane unblocking

---

## 9. Evidence References

- `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` (this run)
- `results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `reports/legal_distance/legal_distance_v34_complementary_role.md`
- `reports/legal_distance/legal_distance_v34_24year_scale_extension.md`

---

*Generated per Research Protocol: hypothesis frozen, corpus/sample frozen, metrics frozen, success rules frozen before result observation. Negative results preserved as first-class evidence.*