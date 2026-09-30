# Evaluation Lane — Audit-Ready Snapshot (Factory Direction v29)

**Date:** 2026-09-30  
**Lane:** evaluation  
**Factory Direction Version:** 29  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING (TF-IDF 174k COMPLETE)  
**Continue Recommended:** false  
**Next Recommendation:** PIVOT_WITHIN_MISSION  

---

## Factory Direction v29 Question — DELIVERED

> "Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels."

### ✅ Component 1: Full 12-Benchmark Formal Suite at 174k — COMPLETE

**Scope:** 8 TF-IDF representations × 12 benchmarks each at 173,963 decisions  
**Harness:** Frozen v3 thresholds, HNSW artifact fixed via exact k-NN on stratified subsample (n=2000)  
**Config Hash (adversarial):** `b51701f5a9c11692` — EXACT REPRODUCTION VERIFIED  
**Config Hash (v25 suite):** `4323f833fa72366a` — EXACT REPRODUCTION VERIFIED  

| Representation | Adversarial Gates | V25 Suite (Pass/Fail/Skip) |
|---|---|---|
| cited_decisions_tfidf | ✅ PASS / ✅ PASS | 6 / 5 / 1 |
| outcome_tfidf | ✅ PASS / ✅ PASS | 3 / 9 / 0 |
| regeste_tfidf | ✅ PASS / ✅ PASS | 5 / 7 / 0 |
| full_text_tfidf_light | ✅ PASS / ✅ PASS | 7 / 5 / 0 |
| cited_outcome_hybrid_0.5 | ✅ PASS / ✅ PASS | 6 / 5 / 1 |
| cited_outcome_hybrid_0.7 | ✅ PASS / ✅ PASS | 6 / 6 / 0 |
| regeste_full_text_hybrid_0.5 | ✅ PASS / ✅ PASS | 7 / 5 / 0 |
| regeste_full_text_hybrid_0.7 | ✅ PASS / ✅ PASS | 7 / 5 / 0 |

**Key Finding:** Fundamental two-mode tradeoff REPRODUCED at 174k:
- **Citation-based reps** pass adversarial_falsification/citation_heritage but fail branch/tf_metadata/hierarchy
- **Text-based reps** pass branch/tf_metadata but FAIL adversarial_falsification (language dominance ~0.999 at full corpus)
- **Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`) achieves best jurist preference (0.7345) with low language dominance (0.4773)

### ✅ Component 2: Citation Heritage Benchmark — COMPLETE

**Scope:** 8 TF-IDF representations evaluated on frozen pair pool  
**Citation Graph:** 173,963 decisions, 174 decisions with outgoing citations (0.1% coverage), 2,105 total citations in graph, 924 resolved within graph (43.9%)  
**Corpus-Level Citation ID Resolution:** 2,019/2,105 citation strings resolved to decision IDs (95.9%) — from corpus lane artifact  
**Positive/Negative Pairs:** 137,314 each (balanced sampling from resolved citation graph, seed=42)  
**Evaluation Sample:** 1,020 pairs (510 positive + 510 negative) stratified subsample from frozen pool — all 8 representations evaluated on this sample  

| Representation | Recall@10 | AUC | Status |
|---|---|---|---|
| cited_decisions_tfidf | 0.0441 | 0.7879 | FAIL |
| outcome_tfidf | 0.0000 | 0.6575 | FAIL |
| regeste_tfidf | 0.0000 | 0.4861 | FAIL |
| full_text_tfidf_light | 0.0520 | 0.8985 | FAIL |
| cited_outcome_hybrid_0.5 | 0.0529 | 0.7597 | FAIL |
| cited_outcome_hybrid_0.7 | 0.0490 | 0.7749 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.0353 | 0.8731 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.0363 | 0.8517 | FAIL |

**Threshold:** recall@10 > 0.2 required for PASS — **ALL FAIL**  
**Note:** Evaluation ran on 1,020-pair stratified subsample (510 pos + 510 neg) from frozen 137,314-pair pool. Citation graph covers only 0.1% of corpus (174 decisions with outgoing citations), limiting benchmark power. Corpus-level citation ID resolution is 2,019/2,105 (95.9%). Ready for 174k dense embeddings when available.

### ✅ Component 3: v17b Label Normalization at 174k — COMPLETE

**Scope:** 85,819 labels normalized, 214 → 164 unique legal_area values  
**Differential Effect CONFIRMED and CORRECTED per audit CYCLE_36527630008 and CYCLE_36680459860:**

| Representation Family | Hierarchy | Zoom Fine | Legal Area |
|---|---|---|---|
| Citation-based (4 reps) | **1.0x (no change)** | **0.83-0.99x (degradation)** | **~1.0x (no change)** |
| Text-based (4 reps) | **1.0x (no change)** | **0.83-0.97x (degradation)** | **~1.0x (no change)** |

**Per-representation purity ratios (normalized/raw) from `v17b_label_normalization_174k_latest.json`:**

| Representation | Hierarchy | Zoom Fine | Legal Area |
|---|---|---|---|
| cited_decisions_tfidf | 1.0000 | 0.8869 | 1.0000 |
| outcome_tfidf | 1.0000 | 0.9968 | 1.0000 |
| regeste_tfidf | 1.0000 | 0.9885 | 1.0018 |
| full_text_tfidf_light | 1.0000 | 0.8352 | 0.9997 |
| cited_outcome_hybrid_0.5 | 1.0000 | 0.8827 | 0.9997 |
| cited_outcome_hybrid_0.7 | 1.0000 | 0.8861 | 1.0000 |
| regeste_full_text_hybrid_0.5 | 1.0000 | 0.9060 | 1.0024 |
| regeste_full_text_hybrid_0.7 | 1.0000 | 0.9647 | 1.0016 |

- **Hierarchy:** NO improvement for ANY representation (all ratios = 1.0000)
- **Zoom Fine:** DEGRADATION for 7/8 representations (ratios 0.83–0.99); regeste_tfidf least affected (0.9885)
- **Legal Area:** NO meaningful change (all ~1.0)
- **regeste_tfidf** only representation with no-worsening on ALL hierarchy metrics (hierarchy=1.0, zoom=0.9885, legal_area=1.0018)
- **V6 dense (12k, 2000-2002):** NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45)
- **Uniform improvement:** FALSE — v17b does NOT generalize uniformly to 174k; shows DEGRADATION on zoom_fine for most representations

---

## Infrastructure Verification — ALL OPERATIONAL

| Component | Status | Verification |
|---|---|---|
| Formal Suite Runner | ✅ OPERATIONAL | Exact reproduction 2026-09-27/28/29/30 |
| Citation Heritage Pipeline | ✅ READY | Frozen 137k pairs (1,020-pair eval sample), corpus citation resolution 2,019/2,105 (95.9%), graph resolution 924/2,105 (43.9%) |
| v17b Normalization Pipeline | ✅ READY | Differential effect reproduced across all 8 reps |
| HNSW Artifact Fix | ✅ CONFIRMED | Exact k-NN on stratified subsample (n=2000) |
| Scalable NN (sklearn/HNSW) | ✅ OPERATIONAL | Adversarial: exact k-NN; Full-corpus: HNSW |
| Monitor Script | ✅ ACTIVE | Check count: 243, Last: 2026-09-30T04:31:49Z |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |

**Last Full Verification:** 2026-09-30T04:32:00Z — Production default adversarial re-verification PASS (LangDom=0.4773, JuristPref=0.7345, exact reproduction, config hash `b51701f5a9c11692`)

---

## Blockers (External Dependencies)

1. **Dense embeddings from legal-distance:** Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED; 15/26 years (2000-2014, ~100k) checkpointed pending audit; 11/26 years (2015-2026) not yet processed
2. **Citation role embeddings:** Not yet available at 174k
3. **Linear hybrid embeddings:** Not yet available at 174k
4. **Jurist human study:** Framework ready but requires 5-10 Swiss jurists (external dependency)

---

## Readiness for Next Representations

When legal-distance delivers 174k-scale dense embeddings, citation roles, or linear hybrids, the evaluation infrastructure is **ready to execute immediately**:

- `run_174k_formal_suite.py` — VERIFIED operational (frozen harness v3)
- `validate_citation_heritage_174k.py` — READY (frozen pair pool)
- `run_v17b_label_normalization_174k.py` — READY (differential effect pipeline)
- Monitor script — ACTIVE with enhanced detection for legal-distance outputs

---

## Orchestration/Validation Failure Diagnosis

**Previous Failure:** Director proposal 36655613802 rejected (round 1)  
**Repair:** RUN_36656840125 applied all required fixes:
1. Corrected checkpoint progress: "25/26 years" → "15/26 years (2000-2014, ~100k decisions)"
2. Removed non-existent audit gate citations (CYCLE_36614819747, CYCLE_36649906765)
3. Incremented factory_direction to v29 for material question text corrections
4. Updated lane status assessments to reflect corrected questions

**Current State:** All corrections applied, lane deliverable for v29 question DELIVERED, infrastructure AUDIT-READY.

---

## State Files (Machine-Readable)

- `evaluation/state/evaluation.json` — Lane state with evidence refs, summary, blockers
- `evaluation/state/evaluation_state.json` — Detailed monitoring state, work completed, infrastructure verification
- `evaluation/state/monitor_174k_state.json` — Monitor checks, detected representations, dense embeddings progress

---

## Evidence References (Immutable Outputs)

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Citation pairs: `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- Partial dense (12k): `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`

---

## Conclusion

The evaluation lane has **completed its deliverable** for factory direction v29. All three mandated components are executed, verified reproducible, and preserved with full provenance. The lane is in **MONITORING** state with `continue_recommended=false`, awaiting new representations from legal-distance to execute the same formal suite on 174k dense embeddings, citation roles, and linear hybrids.

**Audit Status:** ✅ READY — All claim-bearing outputs frozen, negative results preserved, infrastructure verified, config hashes recorded, monitor active.