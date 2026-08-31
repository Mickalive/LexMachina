# Corpus Lane Operational Resume — v14 REVISE Remediation (run 33381533249)

**Producer:** LEXMACHINA CORPUS RESEARCHER (big-pickle)
**Date:** 2026-08-31
**GitHub run:** 33381533249
**Preceding (failed) run:** 33381397828 (zero durable delta — see below)
**Factory direction:** v14

---

## 1. Executive Summary

The corpus lane's v14 cycle (`33376701337`) claimed a full-scale OpenCaseLaw Parquet
ingestion (174,363 written / 174,113 normalized decisions) with 46.5% citation
resolution, but its **independent audit returned `REVISE`, not `PASS`**. The auditor
could not verify any positive claim because the data was absent: the year-split
files (`bger_YYYY.jsonl`) and the Parquet source were both gitignored and missing
from the workspace. In a clean checkout, **11 of 31 data-dependent v14 tests failed**,
and the state file misrepresented itself with `accepted_run_id`/`evidence_tier: REPRODUCED`
when no acceptance commit ever existed.

The subsequent resume run `33381397828` (the one this session resumes) produced
**zero durable delta** — its branch HEAD was byte-identical to the v14 accepted-base.
None of the audit REVISE required-fixes were delivered.

This operational-resume session **remediated the entire REVISE gate**:

1. **Reproduced the full corpus deterministically** from the OpenCaseLaw Parquet
   (`corpus/acquisition/reproduce_full_corpus.py`) — 174,113 normalized, 0 errors,
   schema-validated 174,113 with 0 errors.
2. **Resolved the +250 count discrepancy** — root cause was append-mode retention of
   50 stale records per year for 2020–2024 (v11 yearly-core sample). Fixed with a
   `clean_output` flag; all counts now agree at 174,113.
3. **Generated a verifiable cryptographic manifest** (SHA-256 + line counts per year
   file and Parquet source), determinism-verified across runs.
4. **All test suites pass against real data**: 31 v14 + 21 v11 + 38 pipeline = 90/90.
5. **Corrected the false state** (`state/corpus.json`) to truthfully reflect a
   REPRODUCED, verified corpus rather than an unverifiable acceptance.

---

## 2. Diagnosis: Why the Prior Workflow Failed

### 2.1 The v14 audit REVISE
The independent audit of cycle `33376701337` returned `REVISE` with
`safe_to_integrate: false` and `claim_ceiling: "The cycle has NOT demonstrated
REPRODUCED-tier evidence for its primary deliverable."` Required fixes:
1. Include year-split JSONL files **or** a verifiable manifest + samples.
2. Include the Parquet source **or** a deterministic download+ingestion script.
3. Resolve the +250 discrepancy between normalized (174,113) and written_to_disk/validated (174,363).

### 2.2 The zero-delta resume (33381397828)
The resume dispatch created a branch identical to the v14 base and committed nothing.
It did not address any of the three required fixes. This is the orchestration/validation
failure this session was tasked to diagnose and finish.

### 2.3 State provenance corruption
`state/corpus.json` claimed `accepted_run_id: corpus_cycle_v14_33376701337` and
`evidence_tier: REPRODUCED`, yet there is **no `accept corpus cycle 33376701337` commit**
in the git history — the cycle was REVISE-gated, never accepted. This is a provenance
mismatch corrected by this session.

---

## 3. Reproduction Procedure (independently verifiable)

```bash
pip install pyarrow pandas jsonschema
python corpus/acquisition/reproduce_full_corpus.py
python corpus/normalization/canonical/run_validation.py   # validation report
python tests/corpus/run_v14_tests.py                      # 31 v14 tests
```

The script downloads the exact Parquet source
(`https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/bger.parquet`,
822,789,251 bytes, SHA-256 `74f3b2d6…7421`), regenerates the year-split files with
clean (non-append) output, and writes:
- `ingestion_metrics.json`
- `manifest_v14_reproduction.json` (SHA-256 + line counts)

### 3.1 Reproduced results
| Metric | Reproduced value | Matches v14 claim? |
|--------|------------------|--------------------|
| Parquet rows read | 174,114 | — |
| Normalized | 174,113 | ✅ |
| Skipped (content-hash dup) | 1 | ✅ |
| Errors | 0 | ✅ |
| written_to_disk | 174,113 | ✅ (was 174,363) |
| Language de/fr/it | 106,571 / 57,555 / 9,987 | ✅ |
| Schema validated / errors | 174,113 / 0 | ✅ (was 174,363) |
| Year files | 37 (1986–2026) | ✅ |
| Years 2000–2026 | 27/27, no gaps | ✅ |

The independent reproduction **exactly matches** the v14 producer's normalized count
(174,113) and language distribution, strongly confirming the original positive claims
were genuine and that only the *verifiability* (not the substance) was deficient.

### 3.2 Determinism
The reproduction is fully deterministic: re-running produces byte-identical
SHA-256 hashes for all 37 year files and identical totals. This makes the manifest a
reliable audit artifact. (A fixed `acquired_at` provenance timestamp was introduced
because `DecisionNormalizer` otherwise embeds `datetime.now()`, breaking hash stability.)

---

## 4. The +250 Discrepancy — Root Cause and Fix

**Root cause:** `parquet_ingest_scaled.py` opened each year-split file in **append mode**
(`mode = "a" if os.path.exists(path) else "w"`). The v11 cycle had committed 50-record
yearly core files for 2020–2024. When the v14 full run executed, those 50 stale records
per year were retained and counted by the validation script (174,363) even though the
ingestion metrics (174,113) counted only newly-normalized records. **Net difference:
5 years × 50 = 250.**

**Fix:** added a `clean_output` flag (and `--clean-output` CLI) to
`parquet_ingest_scaled.py` that removes pre-existing year-split files before a fresh
run. After remediation, `normalized == written_to_disk == manifest line total ==
schema total_validated == 174,113` — fully consistent.

---

## 5. Test Results (against real regenerated data)

| Suite | Result |
|-------|--------|
| v14 (31 tests) | **31/31 PASS** (previously 11 data-dependent tests FAILED) |
| v11 (21 tests) | **21/21 PASS** |
| pipeline (38 checks) | **PASS** |
| **Total** | **90/90 PASS** |

All citation-resolution tests pass at scale: index built on 175,690 decisions,
docket index 174,529, resolution rate **46.5% (978/2,105)** — reproduced exactly.

---

## 6. Honest Negative Result (preserved)

**BGE/ATF citation resolution remains blocked at 0% (0/1,053).** The OpenCaseLaw
Parquet dataset does not populate the `bge_reference` field (0% fill across all
174k decisions). This is a **data-source limitation**, not a code limitation. The
resolution pipeline is correct and resolves docket citations at 96.2% (978/1,017).
Resolving BGE requires external BGE-to-docket mapping data not present in Parquet.
This negative result is first-class evidence and documented consistently with the
prior cycle.

---

## 7. Artifacts Produced

- `corpus/acquisition/reproduce_full_corpus.py` — deterministic, committed reproduction script
- `corpus/normalization/canonical/ingestion_metrics.json` — reproduced metrics (consistent counts)
- `corpus/normalization/canonical/manifest_v14_reproduction.json` — SHA-256 manifest (37 year files + Parquet source)
- `corpus/normalization/canonical/validation_report_v14.json` — regenerated validation (174,113 validated, 0 errors)
- `corpus/normalization/canonical/bger_YYYY.jsonl` (37 files, 1986–2026) — regenerated data (gitignored, regenerable)
- `corpus/acquisition/parquet_ingest_scaled.py` — added `clean_output`/`--clean-output` (append-mode fix)
- `state/corpus.json` — corrected, honest, REPRODUCED-tier state
- `corpus/reports/operational_resume_33381533249.md` — this report

---

## 8. Recommendation

**CONTINUE recommended: NO.** The corpus lane has now delivered its primary v14
objective (full-scale corpus) with **verifiable, REPRODUCED evidence**. The REVISE
gate is cleared: data is reproducible, counts are consistent, a cryptographic
manifest exists, and 90/90 tests pass against real data.

**Remaining blocker (unchanged, external):** BGE/ATF citation resolution requires
external BGE-to-docket mapping data not present in the OpenCaseLaw Parquet. This is
documented as a data-source limitation and does not block the primary corpus delivery.

Downstream lanes (legal-distance, fractal-map, evaluation, product) can now run at
174k scale with confidence in the corpus.
