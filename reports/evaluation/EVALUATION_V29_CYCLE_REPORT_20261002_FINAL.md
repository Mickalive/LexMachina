# Evaluation Lane — Cycle Report (Factory Direction v29)

**Date:** 2026-10-02
**Lane:** evaluation
**Direction Version:** 29
**Evidence Tier:** ACCEPTED
**Cycle Status:** RUN
**Continue Recommended:** true

---

## Factory Direction v29 Question

> Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels.

---

## Executive Summary

**All three v29 mandated deliverables DELIVERED and REPRODUCIBLE for TF-IDF family (8 representations at 174k scale).** Evaluation infrastructure is VERIFIED and AUDIT-READY. Lane remains RUN per factory direction "as representations land" — monitoring for new 174k-scale representations from legal-distance.

### Deliverable Status

| Deliverable | Status | Details |
|-------------|--------|---------|
| **1. Full 12-benchmark formal suite at 174k** | ✅ COMPLETE | All 8 TF-IDF reps evaluated on frozen harness v3 (config hash `b51701f5a9c11692`). HNSW artifact fixed via exact k-NN on stratified subsample (n=2000). |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen 1,020-pair pool (95.9% corpus resolution, 43.9% graph resolution). All 8 TF-IDF reps FAIL recall@10 < 0.2. 4/8 PASS AUC≥0.65 (citation-based). |
| **3. v17b label normalization generalization** | ✅ COMPLETE (NEGATIVE) | Tested on 174k fine-grained labels (85,819 normalized, 214→164 unique). **Does NOT generalize**: hierarchy=1.0x (no improvement); zoom_fine DEGRADES 11-16% for 4/8 reps; legal_area~1.0x (no change). regeste_tfidf only no-worsening rep. |

---

## Adversarial Re-Verification (2026-10-02T23:50)

**Method:** Exact k-NN on fixed stratified subsample (n=2000, seed=42)
**Config Hash:** `b51701f5a9c11692` (frozen harness v3)

| Representation | Language Dominance | Jurist Preference | Both Pass |
|----------------|-------------------|-------------------|-----------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` (PROD DEFAULT) | **0.4895** ✅ | **0.7265** ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 ✅ | 0.7195 ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 ✅ | 0.7140 ✅ | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 ✅ | 0.7120 ✅ | ✅ |
| `full_text_tfidf_light` | 0.4854 ✅ | 0.7080 ✅ | ✅ |
| `cited_decisions_tfidf` | 0.4917 ✅ | 0.7075 ✅ | ✅ |
| `outcome_tfidf` | 0.5078 ✅ | 0.6660 ✅ | ✅ |
| `regeste_tfidf` | 0.5111 ✅ | 0.6145 ✅ | ✅ |

**All 8 TF-IDF representations PASS both adversarial gates.**
- LangDom range: 0.485–0.511 (all < 0.85 threshold)
- Jurist range: 0.614–0.727 (all > 0.5 threshold)
- HNSW artifact fix CONFIRMED operational

---

## Citation Heritage Results (Frozen 1,020-Pair Pool)

| Representation | AUC-ROC | Status (AUC≥0.65) |
|----------------|---------|-------------------|
| `cited_decisions_tfidf` | 0.743 | ✅ PASS |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.729 | ✅ PASS |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 0.716 | ✅ PASS |
| `regeste_full_text_hybrid_0.7` | 0.659 | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | 0.636 | ❌ FAIL |
| `outcome_tfidf` | 0.626 | ❌ FAIL |
| `full_text_tfidf_light` | 0.626 | ❌ FAIL |
| `regeste_tfidf` | 0.503 | ❌ FAIL |

**Fundamental tradeoff reproduced:** Citation-based signals recover citation heritage; text-based signals do not.

---

## v17b Label Normalization (174k Fine-Grained Labels)

**Result: NEGATIVE — Does not generalize to 174k scale**

| Metric | Effect (Normalized/Raw) | Interpretation |
|--------|------------------------|----------------|
| Hierarchy coherence | 1.0x (all reps) | No improvement |
| Zoom fine purity | 0.83–0.99x (all reps) | **Degradation for 4/8 reps** (11-16% drop) |
| Legal area clustering | ~1.0x (all reps) | No meaningful change |

**Worst degradations (>10%):**
- `full_text_tfidf_light`: zoom_fine ratio 0.8352
- `cited_decisions_tfidf_outcome_hybrid_0.5`: zoom_fine ratio 0.8827
- `cited_decisions_tfidf_outcome_hybrid_0.7`: zoom_fine ratio 0.8861
- `cited_decisions_tfidf`: zoom_fine ratio 0.8869

**Only `regeste_tfidf` shows no worsening on ALL hierarchy metrics** (zoom_fine ratio 0.9885).

V6 dense (12k): NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45).

**Conclusion:** v17b normalization at 1000-scale (15-25% purity gain, reproduced 4 seeds) operates in a DIFFERENT REGIME than 174k fine-grained labels. Uniform improvement FALSE.

---

## Awaited Representations from Legal-Distance (Status: NOT YET AVAILABLE at 174k)

| Category | Status | Details |
|----------|--------|---------|
| **Dense embeddings** | ❌ BLOCKED | 22/26 years (2000-2021, 144,443 decisions) checkpointed. ONLY 3/26 years (2000-2002) ACCEPTED. Concatenation to 174k BLOCKED on: bge_↔bger_ ID mapping missing, parquet files for 2022-2026 missing. Legal-distance evaluation at 22-year scale: center_projected FAILS jurist gate (LangDom 0.83-0.98), linear hybrids PASS but BELOW TF-IDF baseline. |
| **Citation roles** | ❌ NOT AVAILABLE | Citation role embeddings exist in legal-distance v6 (citing/following/criticizing) but NOT at 174k scale. |
| **Linear hybrids** | ⚠️ PARTIAL EVIDENCE | `linear_citation_concat` and `linear_hybrid05_concat` PASS adversarial at 19-year/122k scale (JP=0.545, 0.540) but BELOW TF-IDF baseline (JP=0.724). 174k concatenation NOT DONE. Optimal weight sweep at 22-year: w=0.4 for cited_tfidf (JP=0.6725), w=0.3 for hybrid_0.5 (JP=0.6605) — both PASS but still BELOW TF-IDF. |

---

## Monitor Check #283 (2026-10-02T23:47)

- Scanned legal-distance accepted state: 22/26 years (2000-2021) checkpointed per progress.json
- NO 174k-scale .npy embeddings detected in legal-distance 174k_dense_embeddings directory
- Adversarial re-verification PASS on ALL 8 TF-IDF representations
- All evaluation infrastructure VERIFIED and AUDIT-READY

---

## Blockers (Unchanged)

1. **Dense embeddings 174k concatenation** — bge_/bger_ ID mapping missing; parquet 2022-2026 missing
2. **Citation role embeddings** — not computed at 174k scale
3. **Linear hybrids 174k** — not concatenated at 174k scale
4. **Jurist human study** — framework ready, requires 5-10 Swiss jurists (external dependency)

---

## Infrastructure Verification

| Component | Status |
|-----------|--------|
| Adversarial benchmarks (exact k-NN n=2000) | ✅ VERIFIED |
| Citation heritage (frozen 1,020 pairs) | ✅ VERIFIED |
| v17b normalization pipeline | ✅ VERIFIED |
| HNSW artifact fix (exact k-NN on valid subset) | ✅ CONFIRMED |
| v25 formal suite (frozen protocol) | ✅ VERIFIED |
| Scalable NN (sklearn exact + HNSW) | ✅ OPERATIONAL |
| Monitor script | ✅ ACTIVE (check_count=283) |
| Metadata 174k (173,963 entries, 100% branch+legal_area) | ✅ VERIFIED |

---

## Recommendation

**CONTINUE** — Lane remains RUN per factory direction v29 ("as representations land").

- TF-IDF family (8 reps) COMPLETE at 174k — no further same-question cycles justified
- Evaluation infrastructure FULLY OPERATIONAL and AUDIT-READY
- AWAITING: legal-distance 174k dense embeddings concatenation, citation roles, linear hybrids
- When new 174k representations land: execute frozen formal suite v3, citation heritage on 1,020-pair pool, v17b normalization test
- Factory Director successor question needed when 174k dense embeddings become available

---

## Evidence References

- Formal suite latest: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash `b51701f5a9c11692`)
- Citation heritage latest: `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- v17b normalization latest: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Dense 3-year formal suite: `evaluation/results/174k/dense_3year_formal_suite/evaluation_3year_dense_formal_suite_latest.json`
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=283)

---

*Report generated per Research Protocol §8: machine-readable lane state plus human-readable report.*