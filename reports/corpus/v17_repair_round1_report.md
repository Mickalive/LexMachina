# Corpus Lane — Cycle v17 Repair Round 1 Report

**Run:** 33420652112 (factory direction v14, GitHub run 33422592725)
**Date:** 2026-08-31
**Lane:** corpus
**Direction version:** 14
**Repair type:** Same-cycle audit repair (REVISE → PASS)

## Audit Finding

Gate `CYCLE_33420652112_GATE.json` returned **REVISE** with 2 required fixes:

### F1 (HIGH): Inflated field_coverage in state/corpus.json

**Problem:** `state/corpus.json` `metrics.field_coverage` reported `cited_decisions: 0.993` and `outcome: 1.0`, but `validation_report_v14.json` (the authoritative source, based on a 1000-record cross-year sample) reports `cited_decisions: 0.526` and `outcome: 0.505`. The validation_report_v14.json is byte-identical between base and producer — no re-computation occurred during the cycle, so the inflated values were carried forward from a prior copy-paste error.

**Fix applied:** Updated `state/corpus.json` field_coverage:
- `cited_decisions`: 0.993 → **0.526** (matches validation_report_v14.json: 526/1000)
- `outcome`: 1.0 → **0.505** (matches validation_report_v14.json: 505/1000)

### F4 (LOW): Stale ingestion rate in report

**Problem:** `reports/corpus/v17_reproduction_verification_report.md` line 45 claimed "Ingestion rate: ~837 decisions/second" but `ingestion_metrics.json` records **1426.83 decisions/second** for this run. The report text was copied from a prior cycle.

**Fix applied:** Updated report line 45 from `~837 decisions/second` to `~1,427 decisions/second`. Also corrected line 69 field coverage text from inflated values (99.3%, 100%) to accurate values (52.6%, 50.5%) citing validation_report_v14.json as the source.

## Verification

- **Test suite:** 75/75 tests PASS (pytest, fresh install). Zero regressions.
- **State-artifact consistency:** state/corpus.json field_coverage now matches validation_report_v14.json exactly.
- **Report-artifact consistency:** v17 report ingestion rate now matches ingestion_metrics.json.
- **Claim ceiling unchanged:** REPRODUCED tier maintained. 174,113 decisions, 75/75 tests, 95.9% citation resolution. The only change is correcting inflated coverage claims to honest values.

## Diff Summary

| File | Change |
|------|--------|
| `state/corpus.json` | field_coverage.cited_decisions 0.993→0.526, outcome 1.0→0.505 |
| `reports/corpus/v17_reproduction_verification_report.md` | Line 45: ~837→~1,427 decisions/sec; Line 69: corrected field coverage text |

**No production pipeline code modified. No test code modified. No data artifacts modified. No baselines weakened. No historical results overwritten.**

## Recommendation

**PASS** — All required fixes applied and verified. Cycle 33420652112 is now safe to integrate.
