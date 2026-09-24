# Evaluation Lane — v25 174k Formal Suite, Execution & Verification Report

- **Cycle**: producer run `36013963912` (persisted snapshot on `cycle/core/evaluation/36013963912/team`), operational-resume verification run `36020066596`
- **Branch**: `cycle/core/evaluation/36013963912/team` (`operational-resume` worktree), commit `b4d4435c`
- **Date**: 2026-09-24
- **Direction version**: 25
- **Evidence tier**: REPRODUCED (independent bitwise reproduction + conformance suite)

---

## 1. Factory-direction v25 question (frozen)

> Run the machine-executable 174k formal suite autonomously as representations land:
> 1. full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged);
> 2. validate `citation_heritage` benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved);
> 3. test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained `legal_area` labels.

All three sub-questions are now **executed at 174k** and **independently reproduced** in this cycle.

---

## 2. Diagnosis: why run 36013963912 was stranded

Producer run 36013963912 produced a complete, high-quality 174k snapshot but the factory never saw it:

1. **No audit branch exists** for the run. Branch topology shows only `cycle/core/evaluation/36013963912/team` and `team-attempt-1`, both at `b4d4435c`. The workflow's audit/integrate legs therefore never ran.
2. **`state/evaluation.json` was never updated** by the producer. At the start of this resume it still carried the run-35988508077 entry with `cycle_status: BLOCKED_ON_DEPENDENCIES`, `continue_recommended: false`. The factory supervisor consequently had no signal that 174k machine-executable results existed.
3. **No conformance/validation artifact** accompanied the snapshot, so nothing could be mechanically accepted.
4. Additionally, the committed `state/evaluation.json` at HEAD was **invalid JSON** (stray trailing `}` at line 1074 — an artifact of the previous repair commit `7da8cc0b`). Repaired in this cycle (stray brace removed; all historical records preserved).

The combination (2)+(3) meant the evaluation lane looked "done, nothing new to cycle" while real 174k work sat unaccepted on the branch.

---

## 3. Snapshot contents (run 36013963912, persisted on cycle branch)

| Artifact | Location |
|---|---|
| 8 embeddings, `(173963, 128)` float32 each | `results/evaluation/v25_174k_formal_suite/embeddings/*.npy` |
| Build manifest (run id `eval_v25_174k_embeddings_1790261893`, seed 42, dim 128, `n_missing=0`) | `results/evaluation/v25_174k_formal_suite/embeddings/build_manifest.json` |
| Suite summary + 8 per-rep 12-benchmark result files | `results/evaluation/v25_174k_formal_suite/results/` |
| Fixed deterministic subsamples (hierarchy 15,000 / temporal 30,000, seed 42) | `results/evaluation/v25_174k_formal_suite/fixed_samples/` |
| Dedicated citation-heritage files (8) | `results/evaluation/v25_174k_citation_heritage/` |
| Dedicated v17b clustering-test files (8) | `results/evaluation/v25_174k_v17b/` |
| Frozen protocol | `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` |

Representations: `cited_decisions_tfidf`, `outcome_tfidf`, `regeste_tfidf`, `full_text_tfidf_light`, and hybrids `cited_outcome_hybrid_0.5/0.7`, `regeste_full_text_hybrid_0.5/0.7`. Row order = exact order of `evaluation/data/174k/metadata_174k.json`; empty fields are scattered as zero rows (cited 82,780; outcome 85,343; regeste 91,200; full_text 0).

---

## 4. Independent verification performed (this cycle)

### 4.1 Embedding provenance — BITWISE EXACT reproduction
Regenerated the pinned parquet corpus with the corpus lane's script
`reproduce_full_corpus.py --output-dir /tmp/opencode/lexcorpus2/out/canonical`
(174,113 decisions; de 106,571 / fr 57,555 / it 9,987; matches accepted corpus claims),
then rebuilt all 8 representations from scratch (sklearn TF-IDF → TruncatedSVD(128) → L2-normalize; seed 42; `full_text` truncated to 5,000 chars; hybrid = alpha-weighted re-normalized combination).

**Result: all 8 rebuilt npy files are BITWISE IDENTICAL to the committed snapshot
(`max_abs_diff = 0.0` for each).** This proves:
- the producer's pipeline is deterministic and reproducible,
- every row is aligned with `metadata_174k.json` (173,963/173,963 present, 0 missing),
- the embeddings are exactly what the frozen protocol specifies.

Evidence: `results/evaluation/v25_174k_snapshot_verification/embedding_rebuild_verification.json`.

### 4.2 12-benchmark suite — frozen config & thresholds
- Suite config hash `4323f833fa72366a` (frozen v16 suite) confirmed in all result files.
- All thresholds frozen and unchanged across all 8 reps and all 12 benchmarks.
- Suite summary ↔ per-rep files: 0 mismatches. Dedicated citation-heritage files ↔ suite blocks: 0 mismatches.

Per-rep results (pass/fail):

| Representation | Pass / Fail |
|---|---|
| cited_decisions_tfidf | 6 / 6 |
| outcome_tfidf | 3 / 9 |
| regeste_tfidf | 5 / 7 |
| full_text_tfidf_light | 7 / 5 |
| cited_outcome_hybrid_0.5 | 6 / 6 |
| cited_outcome_hybrid_0.7 | 6 / 6 |
| regeste_full_text_hybrid_0.5 | 7 / 5 |
| regeste_full_text_hybrid_0.7 | 7 / 5 |

### 4.3 Citation heritage — independent AUC recomputation
Independently recomputed AUC-ROC (sklearn, float64, on the frozen 137,314 + 137,314 pair pool; all pairs resolve to metadata IDs) and re-derived HNSW neighborhoods (hnswlib, k=20, ef=100) for spot-checked reps:

| Representation | Independent AUC | Producer AUC | Verdict (≥0.65) |
|---|---|---|---|
| cited_decisions_tfidf | 0.973104 | ~0.973 | PASS |
| outcome_tfidf | 0.718365 | 0.720444 | PASS |
| regeste_tfidf | 0.486484 | 0.486484 | **FAIL** |
| full_text_tfidf_light | 0.843878 | ~0.844 | PASS |
| cited_outcome_hybrid_0.5 | 0.919341 | ~0.919 | PASS |
| cited_outcome_hybrid_0.7 | 0.960489 | ~0.960 | PASS |
| regeste_full_text_hybrid_0.5 | 0.850500 | ~0.850 | PASS |
| regeste_full_text_hybrid_0.7 | 0.865039 | ~0.865 | PASS |

**Important — superseded negative:** the earlier recorded "citation heritage FAIL (AUC=0.482) on cited_outcome_hybrid_0.5_174k" (in `state/evaluation.json` under `v25_dependencies`/citation_heritage and in the run-35988508077 record) was measured on an **ad-hoc cycle-branch embedding with broken row alignment vs `metadata_174k.json`** — an artifact, not a property of the frozen zero-shot TF-IDF family. Under the frozen protocol the same benchmark **passes (AUC=0.919341)**, consistent with the cited-outcome hybrid's strong nearest-neighbor citation rates.

HNSW recomputation notes (independent): `branch_knn` adversarial-overlap FAIL (0.6333 threshold; overlap ≈0.38-0.39); adversarial `language_dominance`/`branch_coherence` PASS (0.85/0.3; ld ≈0.58, bc ≈0.35); `nn_citation_rate@10` ≈0.45-0.47 (report metric). Statuses unchanged from producer.

### 4.4 v17b label normalization at 174k
- Metadata: 173,963 decisions; 214 raw `legal_area` labels → 164 normalized (23.4% reduction); 85,819 labels changed (49.3%); 82,770 unknown (47.6%); 33 canonical concepts with multi-language variants (state previously recorded 32 — this cycle's recount: 33).
- Frozen success rule — *no hierarchy-family purity metric worsened by >10% relative to raw labels* — **PASSES for all 8 reps** (performance of all 8 consumed representations by v17b-normalized labels, per dedicated `results/evaluation/v25_174k_v17b/` files).
- Nuances (recorded, not hidden):
  - `full_text` family: purity ratio 1.000 (unchanged) but NMI drops 0.577→0.418 (hierarchy) and 0.600→0.454 (legal_area); 94.2% of hierarchy-subsample labels changed.
  - `regeste`/`outcome` gains (ratios ~1.46-1.64) come from degenerate zero-vector clustering where purity equals label-frequency statistics (raw hier=zoom=area identical).
  - The 1200-scale uniform 15-25% purity gain does **not** fully generalize to 174k.

### 4.5 Frozen harness v3 integrity (standard gate, at 1200)
Re-ran the frozen harness v3 (`LEX_ACCEPTED_ROOT=/tmp/lex_accepted`), config hash `a31c443a9b0e992e`:
EXACT baseline match on all 6 representations (center_projected_64dim PASS 0.7664/0.5121; center_projected_768 FAIL 0.7738/0.4912; linear_metric PASS 0.6805/0.6847; mahalanobis PASS 0.6843/0.6781; hybrid_stabilized PASS 0.6704/0.6656; hybrid_v2 PASS 0.7115/0.5988). Worktree `evaluation/results/v3/evaluation_v3_results.json` restored after run (only `duration_seconds` differed). Log: `/tmp/v3_harness_repro2.log`.

---

## 5. Conformance test added (audit gate)

`tests/evaluation/test_v25_174k_suite_snapshot.py` — 7 checks, **7/7 PASS** (7.8 s):

1. embedding inventory (shape, dtype, finiteness, zero-row pattern)
2. hybrid exact reconstruction from saved bases (producer normalize semantics)
3. fixed-subsample determinism (hierarchy 15,000 / temporal 30,000, seed 42)
4. suite-summary ↔ per-rep ↔ dedicated citation-heritage consistency
5. frozen thresholds for all 12 benchmarks
6. citation-heritage spot AUC on fixed seed-42 pair subsample vs frozen expected values
7. v17b label-level record (214→164, 49.3% changed, 47.6% unknown)

This test is the mechanical gate that would have prevented the stranding: any agent appending to the snapshot must keep the conformance checks green.

---

## 6. State and recommendations

`state/evaluation.json` updated (valid JSON; all historical records preserved):
- `evidence_tier: REPRODUCED`, `cycle_status: AWAITING_AUDIT`, `continue_recommended: false`
- `accepted_run_id: eval_v25_174k_formal_suite_36013963912` (candidate, pre-audit); `last_accepted_run_id: eval_v25_comprehensive_verification_35981467715`
- appended record `v25_174k_formal_suite_execution_36013963912` with manifest, per-rep pass/fail, independent AUCs, v17b results, diagnosis, and supersession of the 0.482 negative
- refreshed top-level `next_recommendation` and `evidence_refs`

**Recommendation to Factory Director**: audit candidate `eval_v25_174k_formal_suite_36013963912` (evidence: conformance test + this report + `embedding_rebuild_verification.json`). Then authorize the legal-distance lane to deliver dense 174k representations (`center_projected_64`, `center_projected_768`, `linear_metric`, `mahalanobis`, `hybrid_stabilized`, `hybrid_v2`) so the suite and the `DEFAULT_map_mode_center_projected_64dim_hierarchical` production gate can be re-verified at 174k. No additional same-question cycle is justified on the 8 TF-IDF-family representations (v25 question fully answered at 174k).

## 7. Blockers / negatives preserved

- **NEGATIVE (preserved)**: regeste_tfidf citation-heritage AUC 0.486484 — TF-IDF over regeste alone does not recover citation proximity at 174k; the full-text and cited-outcome hybrids do.
- **NEGATIVE (preserved)**: full_text family NMI drops at 174k under v17b normalization (hierarchy 0.577→0.418, legal_area 0.600→0.454), flagged as reported nuance.
- **SUPERSEDED**: citation-heritage "FAIL 0.482" on cited_outcome_hybrid_0.5_174k → PASS 0.919341 under frozen protocol (row-order artifact on the ad-hoc cycle embedding).
- **External**: dense 174k embeddings pending from legal-distance; jurist human study blocked (requires 5-10 Swiss jurists).
- **Orchestration**: run 36013963912 has no audit branch; exact failing step not observable without `gh` (no GH_TOKEN in this environment). Remediation: conformance test + state update + this report; audit branch to be created by the workflow after this cycle's persist step.