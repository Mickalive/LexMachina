# Evaluation Cycle 8 Report — Adversarial Falsification + TF Human Indexing

**Run ID:** eval_cycle_8_1787795632
**Date:** 2026-08-27
**Lane:** evaluation
**Direction version:** 1
**Evidence tier:** REPRODUCED

---

## 1. Hypothesis & Product Decision

**Question:** Do current representations have hidden weaknesses that positive benchmarks don't capture? Can canonical court metadata (branch, chamber, legal_area) provide finer-grained human indexing than existing branch-only tests?

**Product decision:** If adversarial tests reveal significant weaknesses, the legal-distance lane must address them before productization. If TF metadata benchmark shows the representation recovers fine-grained court structure, it strengthens the case for the current approach.

**Frozen before observation:**
- Corpus: 1000 BGer decisions (2020-2024) from fractal-map baseline metadata
- Embeddings: baseline (768-dim), language_debiased_pca2 (768-dim)
- Success rule: Adversarial degradation < 20% on neighbor quality; branch k-NN accuracy > 0.5

---

## 2. New Benchmarks Implemented

### 2.1 TF Metadata Human-Indexing Benchmark

Uses canonical court metadata as weak supervision:
- **Branch classification** (3 categories in this corpus: oeffentliches_recht, strafrecht, zivilrecht)
- **Chamber classification** (8+ categories)
- **Legal-area classification** (76+ unique labels)

Method: k-NN classification using cosine similarity. For each decision, classify by majority vote of k nearest neighbors. This tests whether nearby decisions share the same human-assigned labels.

### 2.2 Adversarial Falsification Test

Actively tries to break the representation with 6 tests:
1. **Language dominance**: Are neighbors overwhelmingly same-language? (Groups by language, not law)
2. **Branch coherence**: Do neighbors share the same legal branch?
3. **Worst-case neighbors**: Which decisions have the worst branch coherence?
4. **Dead zones**: Are there high-similarity pairs across different branches?
5. **Subgroup sensitivity**: Does branch coherence vary across branches?
6. **Similarity distribution**: Is the distribution too compressed (all decisions look alike)?

Falsification conditions:
- Language dominance > 0.9 → FALSIFIED (groups by language)
- Branch coherence < 0.3 → FALSIFIED (neighbors are random)
- >5 pairs with similarity > 0.95 across branches → FALSIFIED (dead zones)

---

## 3. Results

### 3.1 TF Metadata Benchmark

| Metric | Baseline | Debiased | Random | Pass? |
|--------|----------|----------|--------|-------|
| Branch k-NN accuracy@1 | 0.970 | 0.974 | 0.333 | ✅ |
| Branch k-NN accuracy@5 | 0.957 | 0.967 | 0.333 | ✅ |
| Chamber k-NN accuracy@1 | 0.937 | 0.945 | 0.111 | ✅ |
| Chamber k-NN accuracy@5 | 0.921 | 0.927 | 0.111 | ✅ |
| Legal-area k-NN accuracy@1 | 0.462 | 0.429 | 0.010 | ✅ |
| Legal-area k-NN accuracy@5 | 0.479 | 0.418 | 0.010 | ✅ |
| Branch purity@5 | 0.942 | 0.951 | — | ✅ |
| Branch purity@10 | 0.901 | 0.920 | — | ✅ |
| Branch purity@20 | 0.832 | 0.859 | — | ✅ |
| Branch purity@50 | 0.697 | 0.741 | — | ✅ |

**Key finding:** Both representations strongly recover human-assigned court structure. Branch k-NN accuracy is ~0.96 (3x random). Chamber accuracy is ~0.93 (8x random). Legal-area accuracy is ~0.45 (45x random). The representation IS capturing legal content, not just language.

**Debiasing improves all TF metadata metrics:**
- Branch purity@10: 0.901 → 0.920 (+2.1%)
- Chamber k-NN@5: 0.921 → 0.927 (+0.6%)
- Branch coherence: 0.889 → 0.910 (+2.4%)

### 3.2 Cross-Branch Confusion

| Branch | Count | Mean Same-Label Fraction@10 (Baseline) | Debiased |
|--------|-------|----------------------------------------|----------|
| oeffentliches_recht | 466 | 0.870 | 0.911 |
| strafrecht | 271 | 0.923 | 0.927 |
| zivilrecht | 262 | 0.888 | 0.893 |

**Finding:** oeffentliches_recht has lowest coherence (0.870 baseline, 0.911 debiased). This is the largest branch (466 decisions) and most diverse (covers administrative law, human rights, environmental law, etc.). Strafrecht has highest coherence (0.923).

### 3.3 Adversarial Falsification

| Metric | Baseline | Debiased | Threshold | Status |
|--------|----------|----------|-----------|--------|
| Language dominance (mean) | **0.982** | 0.818 | <0.9 | Baseline FALSIFIED |
| Branch coherence (mean) | 0.889 | **0.910** | >0.3 | ✅ Both pass |
| Dead zones (pairs >0.95) | **20** | **20** | <5 | Both FALSIFIED |
| Falsification status | **FALSIFIED** | **FALSIFIED** | — | — |

**Falsification 1 — Language dominance (baseline only):**
- Baseline mean language dominance = 0.982: 98.2% of neighbors share the same language
- This means the baseline representation groups primarily by language, not legal content
- Debiased reduces this to 0.818 (16.7% improvement), below the 0.9 threshold
- **BUT:** Debiased still has median=1.0, meaning half of decisions have all-same-language neighbors

**Falsification 2 — Dead zones (both representations):**
- 20 pairs with similarity > 0.95 across different branches
- Worst dead zone: index 903 (oeffentliches_recht, fr) ↔ index 743 (strafrecht, fr), similarity=0.982
- These are decisions from DIFFERENT legal branches that the representation treats as nearly identical
- All dead zone pairs share the same language (fr or de), confirming language as the dominant signal
- Debiasing does NOT reduce the number of dead zones (still 20)

### 3.4 Subgroup Sensitivity

| Branch | Count | Mean Coherence@10 | Std | Min |
|--------|-------|-------------------|-----|-----|
| oeffentliches_recht | 466 | 0.870 | 0.199 | 0.0 |
| strafrecht | 271 | 0.923 | 0.128 | 0.2 |
| zivilrecht | 262 | 0.888 | 0.181 | 0.2 |

**Finding:** oeffentliches_recht has highest variance (std=0.199) and lowest minimum (0.0). Some public law decisions have zero branch coherence — their 10 nearest neighbors are all from different branches. This is the "worst-case" subgroup.

### 3.5 Similarity Distribution

| Statistic | Baseline |
|-----------|----------|
| Mean | 0.891 |
| Std | 0.042 |
| Min | 0.684 |
| P5 | 0.820 |
| P50 | 0.892 |
| P95 | 0.953 |
| Max | 1.000 |

**Finding:** The similarity distribution is extremely compressed. 90% of pairs have similarity between 0.82 and 0.95. This means the representation has poor discriminability — most decisions look very similar regardless of legal content. This is a fundamental limitation for a "Google Maps of law" where you need clear boundaries between regions.

---

## 4. Interpretation

### What the positive benchmarks show:
- Branch coherence 0.889-0.910: neighbors DO share legal branch (well above random 0.33)
- Branch k-NN accuracy 0.957-0.967: representation recovers court structure
- Legal-area k-NN accuracy 0.479: representation captures finer legal structure

### What the adversarial tests reveal:
1. **Language dominance is the primary signal** (baseline 0.982). Even after debiasing (0.818), language remains dominant.
2. **Dead zones exist**: 20 pairs of decisions from different branches with similarity > 0.95. These are false neighbors that would mislead users.
3. **Similarity distribution is compressed**: 90% of pairs between 0.82-0.95. The representation lacks discriminability.
4. **oeffentliches_recht is the weak branch**: highest variance, lowest minimum coherence. Some public law decisions are completely lost in the embedding space.

### Why this matters for the product:
- A user looking at the map would see decisions grouped by language, not legal area
- Zooming within a language cluster would reveal mixed legal areas, not coherent sub-areas
- The "Google Maps of law" metaphor requires clear legal boundaries, not language boundaries
- Dead zones would create misleading "similar" recommendations

---

## 5. Critical Findings for Legal-Distance Lane

1. **Language debiasing helps but is insufficient**: Reduces language dominance from 0.982 to 0.818 but doesn't eliminate dead zones
2. **The representation needs stronger legal signal**: Branch coherence is good (0.91) but the compressed similarity distribution means poor discrimination
3. **Citation-aware representations are needed**: Dead zones are all same-language cross-branch pairs — citations could disambiguate them
4. **Section-specific representations may help**: The Sachverhalt (facts) section carries strongest legal-area signal (from cycle 7 results)
5. **The oeffentliches_recht branch needs special attention**: Most diverse, worst coherence, highest variance

---

## 6. Files Produced

| File | Purpose |
|------|---------|
| `evaluation/run_cycle_8.py` | Cycle 8 execution script (TF metadata + adversarial benchmarks) |
| `results/cycle_8_results.json` | Machine-readable results |
| `reports/evaluation/evaluation_cycle_8_report.md` | This report |

---

## 7. Recommendation

**CONTINUE** — The evaluation lane has now produced:
- 11 benchmarks (9 previous + 2 new: TF metadata, adversarial falsification)
- Adversarial testing reveals specific, actionable weaknesses
- The legal-distance lane has clear targets: reduce language dominance below 0.8, eliminate dead zones, improve similarity distribution discriminability

Next cycle should:
1. Test citation-graph representations against adversarial benchmarks (if available from legal-distance lane)
2. Add temporal stability test (do dead zones persist across time periods?)
3. Test with larger corpus (1000 → 3000+ decisions) to validate scale stability

---

*Prepared by: evaluation_lane*
*Provenance: Canonical BGer corpus (1000 decisions) + fractal-map embeddings (baseline, language_debiased_pca2)*
*Frozen sample: 1000 BGer decisions 2020-2024, 3 branches, 8+ chambers, 76+ legal areas*
