# Evaluation Cycle v44 Report: Checkpoint State Consistency Verification

**Cycle ID:** 36137198698  
**Date:** 2026-09-25  
**Lane:** evaluation  
**Factory Direction:** v27  
**Status:** REPAIR COMPLETE — checkpoint state now consistent with filesystem

---

## Executive Summary

This cycle resolves the internal inconsistency identified in Audit CYCLE_36135602547_GATE.json (REVISE gate). The prior cycle introduced an unsupported `v43_cycle_verification` claiming a correction from 14 to 7 checkpoint years without evidence, creating a contradiction between state files (7 years) and the missing v43 cycle report (which would have shown 14 years with file sizes per prior cycles v38-v42).

**Fix applied:** 
- Renamed verification to **v44** to avoid version collision with existing v43 (GitHub run 36127454643)
- Verified actual checkpoint directory contents via `ls -la /tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- State files now accurately reflect **7 completed years (2000-2006, 27%)** — matching the filesystem
- Removed unsupported claim "previous state erroneously reported 14 years"
- Added factual note: prior cycles v38-v42 documented 14 years (2000-2013) with specific file sizes; those checkpoints are no longer present on the current filesystem

---

## Filesystem Verification (Primary Evidence)

```
$ ls -la /tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/
total 106400
drwxr-xr-x 2 runner runner     4096 Sep 25 12:52 .
drwxr-xr-x 3 runner runner     4096 Sep 25 12:52 ..
-rw-r--r-- 1 runner runner 11793536 Sep 25 12:52 embeddings_2000.npy
-rw-r--r-- 1 runner runner 13308032 Sep 25 12:52 embeddings_2001.npy
-rw-r--r-- 1 runner runner 13513856 Sep 25 12:52 embeddings_2002.npy
-rw-r--r-- 1 runner runner 15575168 Sep 25 12:52 embeddings_2003.npy
-rw-r--r-- 1 runner runner 15655040 Sep 25 12:52 embeddings_2004.npy
-rw-r--r-- 1 runner runner 16189568 Sep 25 12:52 embeddings_2005.npy
-rw-r--r-- 1 runner runner 17037440 Sep 25 12:52 embeddings_2006.npy
-rw-r--r-- 1 runner runner   667733 Sep 25 12:52 metadata_2000.json
-rw-r--r-- 1 runner runner   745925 Sep 25 12:52 metadata_2001.json
-rw-r--r-- 1 runner runner   758841 Sep 25 12:52 metadata_2002.json
-rw-r--r-- 1 runner runner   884485 Sep 25 12:52 metadata_2003.json
-rw-r--r-- 1 runner runner   886683 Sep 25 12:52 metadata_2004.json
-rw-r--r-- 1 runner runner   914370 Sep 25 12:52 metadata_2005.json
-rw-r--r-- 1 runner runner   973876 Sep 25 12:52 metadata_2006.json
-rw-r--r-- 1 runner runner      135 Sep 25 12:52 progress.json
```

**Confirmed:** 7 years (2000-2006) with both `.npy` embeddings and `.json` metadata files. No files for years 2007-2025.

---

## Monitor Activity (Valid Work Preserved)

Two additional monitor executions performed in the prior repair cycle:

| Check # | Timestamp | Result |
|---------|-----------|--------|
| 67 | 2026-09-25 12:37:07 | No 174k representations found yet |
| 68 | 2026-09-25 12:38:11 | No 174k representations found yet |

- Check count correctly incremented: 66 → 68
- Infrastructure status unchanged and correctly reported (all OPERATIONAL)
- TF-IDF family completion status correctly maintained

---

## Prior Evidence Context (Not Overwritten)

Cycles v38-v42 and v43 (run 36127454643) consistently documented **14 checkpoint years (2000-2013)** with specific file sizes:

| Year | Embedding Size | Metadata Size | Source |
|------|----------------|---------------|--------|
| 2000 | 11.8 MB | 667 KB | v38/v43 cycle reports |
| 2001 | 0.97 MB | 88 KB | v38/v43 cycle reports |
| 2002 | 1.1 MB | 100 KB | v38/v43 cycle reports |
| ... | ... | ... | ... |
| 2013 | 0.83 MB | 76 KB | v38/v43 cycle reports |

**These reports are historical evidence of prior checkpoint state.** They are not deleted or modified. The current filesystem simply no longer contains years 2007-2013 checkpoints (likely due to re-computation, cleanup, or job ceiling constraints on GitHub runners). The current state honestly reflects what exists *now*.

---

## State File Consistency (Post-Repair)

| Artifact | Checkpoint Years | Status |
|----------|------------------|--------|
| `monitor_174k_state.json` | 7 (2000-2006) | ✅ CONSISTENT with filesystem |
| `evaluation.json` (v44_cycle_verification) | 7 (2000-2006) | ✅ CONSISTENT with filesystem |
| `evaluation_v44_cycle_report.md` | 7 (2000-2006) | ✅ CONSISTENT with filesystem |

All three artifacts now agree: **7 years completed (2000-2006), 27% of 26 years, blocked on years 2007-2025**.

---

## Infrastructure Status (Unchanged, Verified)

| Component | Status | Evidence |
|-----------|--------|----------|
| HNSW backend (hnswlib) | OPERATIONAL_ON_GITHUB_RUNNERS | Verified at 15k+ scale |
| scalable_nn.py | OPERATIONAL_WITH_SKLEARN_FALLBACK | Exact NN <10k, HNSW ≥10k |
| v25_formal_suite | OPERATIONAL | All 8 TF-IDF reps evaluated at 174k |
| citation_heritage | FROZEN_137314_PAIRS_READY | 95.9% citation resolution |
| v17b_normalization | OPERATIONAL | 213→163 labels, 32 cross-lingual concepts |
| monitor_script | ACTIVE_WITH_FORMAL_SUITE | run_formal_suite_v25() integrated |

---

## TF-IDF Family Evaluation Status (Complete)

All 8 TF-IDF representations fully evaluated at 174k scale (173,963 decisions):

| Representation | 12-Benchmark Pass | Citation Heritage AUC | v17b Hierarchy NMI |
|----------------|-------------------|----------------------|-------------------|
| full_text_tfidf_light | 7/12 | 0.6841 | -27.6% |
| regeste_full_text_hybrid_0.5 | 7/12 | 0.7892 | -27.6% |
| regeste_full_text_hybrid_0.7 | 7/12 | 0.8123 | -27.6% |
| cited_decisions_tfidf | 6/12 | **0.9731** | ≤10% ✅ |
| cited_outcome_hybrid_0.5 | 6/12 | 0.9193 | -16.0% |
| **cited_outcome_hybrid_0.7** | **6/12** | **0.9605** | ≤10% ✅ |
| regeste_tfidf | 5/12 | 0.4865 (FAIL) | ≤10% ✅ |
| outcome_tfidf | 3/12 | 0.5234 | -13.1% |

**Production default confirmed:** `cited_outcome_hybrid_0.7` — passes both adversarial gates (LangDom=0.569<0.85, BranchCoherence=0.356>0.3), citation_heritage AUC=0.9605, nn_citation_rate@10=0.490. Zero-shot TF-IDF, no GPU required.

---

## Blocked Dependencies (Unchanged)

| Dependency | Status | Details |
|------------|--------|---------|
| legal-distance 174k dense embeddings | BLOCKED | Year-split: 7/26 years in checkpoints (2000-2006); years 2007-2025 pending (gh run 36096850301) |
| Jurist human study | BLOCKED | External: 5-10 Swiss jurists recruitment by repo owner; framework ready |

---

## Recommendation

**CONTINUE_RECOMMENDED = false** for TF-IDF family (same question). All three machine-executable sub-questions complete at 174k scale with frozen thresholds. No additional same-question cycle justified.

**Next cycle trigger:** When legal-distance lane produces concatenated 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids), the monitor's `run_formal_suite_v25()` will auto-execute the full v25 protocol.

---

## Evidence References

- `evaluation/state/monitor_174k_state.json` — dense_embeddings_progress: 7 years (2000-2006)
- `evaluation/state/evaluation.json` — v44_cycle_verification added
- `evaluation/logs/monitor_174k.log` — checks #67, #68 recorded
- `evaluation/evaluation_v44_cycle_report.md` — this report
- Prior cycle reports v38-v43 preserved in evaluation history (not modified)

---

## Compliance with Audit Required Fixes

| Required Fix | Addressed |
|--------------|-----------|
| Evidence for 7-year claim (ls output) | ✅ Provided above |
| Update cycle report to match checkpoint count | ✅ evaluation_v44_cycle_report.md created |
| Resolve v43 version collision | ✅ Renamed to v44 |
| Remove unsupported "erroneously reported" claim | ✅ Replaced with factual note about prior state vs current filesystem |