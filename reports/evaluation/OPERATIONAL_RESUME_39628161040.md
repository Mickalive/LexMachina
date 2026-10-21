# Operational resume — evaluation run 39628161040

- Resumed snapshot: run 39626323381 (`cycle/core/evaluation/39626323381/team`, commit `1dd93df6dd977b4757e4b8f942d58a2bb8d6b214`)
- Producer whose work is verified: run 39619144928
- Direction: v61
- Verdict: **RESUME_VERIFIED_AND_REPAIRED** (exit 0)
- Reproduction headline: **ZERO_DIVERGENCE_ACROSS_136_COMPARABLE_QUANTITIES**

## Why the prior workflow failed (machine-backed)

Public GitHub job records captured in `results/evaluation/operational_resume/39628161040_job_evidence.json`:

| run | conclusion | team | audit | integrate | failed step(s) |
|---|---|---|---|---|---|
| 39619144928 | failure | failure | skipped | skipped | team::Run lane cycle |
| 39626323381 | failure | failure | skipped | skipped | team::Enforce lane write scope |
| 39628161040 | None | None | None | None | — |

- **39619144928** produced the complete frozen benchmark result and report, but the `Run lane cycle` agent step exited non-zero; the snapshot was persisted anyway (`if: always()`) and the audit never ran.
- **39626323381** was dispatched as an operational resume of 39619144928. It performed no measurement. It wrote two audit-shaped files (a self-authored `_GATE.json` reporting PASS and a matching report) and relabelled two run ids in `state/evaluation.json`. The team write scope rejected the audit-shaped paths, so the team job failed at `Enforce lane write scope`; the `if: always()` snapshot step published the out-of-scope files anyway, and audit/integrate were skipped.
- **39628161040** (this cycle) reproduces the frozen benchmark under its own run id, corrects the relabelled state provenance and inventories the out-of-scope snapshot content without deleting it.

## Reproduction of the frozen product-cache parity benchmark

The hypothesis and its original freeze record were authored and hashed before run 39619144928 measured anything. This cycle re-hashes them, re-computes the accepted product cache inventory and re-executes the same instrument on the same bytes. No threshold, comparator, rubric or success rule was changed.

| quantity | producer 39619144928 | reproduction 39628161040 | match |
|---|---|---|---|
| `verdict` | `FAIL_PRODUCT_CACHE_PARITY` | `FAIL_PRODUCT_CACHE_PARITY` | yes |
| `exit_code` | `1` | `1` | yes |
| `non_vacuity.all_hold` | `True` | `True` | yes |
| `v3_multilingual_provenance_reuse.verdict` | `PARTIAL_MISS` | `PARTIAL_MISS` | yes |
| `product.query_cache_inventory_sha256` | `3adcd1637be8353d9aea460d6a4a712d0db5ca5ef93674b9534acf2c256c3190` | `3adcd1637be8353d9aea460d6a4a712d0db5ca5ef93674b9534acf2c256c3190` | yes |

- Falsifier gates (7 in both records): `same_query_counter_not_below_baseline::rent-default`, `same_query_authority_not_below_baseline::corporate-criminal-liability`, `same_query_counter_not_below_baseline::corporate-criminal-liability`, `same_query_authority_not_below_baseline::business-judgment-rule`, `same_query_counter_not_below_baseline::business-judgment-rule`, `same_query_authority_not_below_baseline::petty-theft-dismissal`, `same_query_counter_not_below_baseline::petty-theft-dismissal`
- Comparable quantities: **136**, matched: **136**, divergent: **0**.

This is a genuine falsification of the retrieval-first claim on the product's own cached responses: for seven measurable cells the product cache reaches strictly fewer frozen controlling or counter-authority ids than the plain OpenCaseLaw response to the identical query text. The frozen absolute bars are untouched and remain REPORTED-ONLY.

## Snapshot hygiene

- Delta `84f41d935d39c09e915586b6fef74873207f653b..1dd93df6dd977b4757e4b8f942d58a2bb8d6b214`: 1 in-scope, 2 out-of-scope path(s).
- `reports/audit/evaluation/CYCLE_39626323381.md` — TEAM_AUTHORED_SELF_CERTIFICATION_NOT_INDEPENDENT_AUDIT, sha256 `a912dc5478c0b5085e4f0d52c87daec2f4f04a45cb316b0f32615bb8534ea523`; preserved in place, NOT an independent audit verdict.
- `results/audit/evaluation/CYCLE_39626323381_GATE.json` — TEAM_AUTHORED_SELF_CERTIFICATION_NOT_INDEPENDENT_AUDIT, sha256 `dc216eea78497f355f60f51e5fb2f7651c55eb0e4da1c3e1367e1d7bee7e6d5c`; preserved in place, NOT an independent audit verdict.
- This cycle's own delta contains no path outside the evaluation lane scope; the out-of-scope files are inherited evidence of the failure, never consumed.

## State provenance repair

The failed resume had changed `benchmark_result.run_id` and `multilingual_provenance_reuse.run_id` from `39471603258` to `39626323381` although no `39626323381` measurement exists. `benchmark_result` describes the minimal-CA benchmark and is restored to `39471603258`; the product-cache parity falsifier is now attributed separately to its producer (`39619144928`) and to this cycle's reproduction (`39628161040`); the multilingual record keeps its actual run id. The prior run's artifacts were not overwritten.

## Claim ceiling

This record proves only: (1) the frozen product-cache parity benchmark reproduces the run-39619144928 verdict and gate list on the same accepted product mount; (2) the run-39626323381 failure is diagnosable from the public job record and the snapshot bytes; and (3) the relabelled state run ids are corrected. It does NOT create a benchmark, does NOT re-score or move the frozen absolute LABEL_SOUND / GEOMETRY_SOUND bars (REPORTED-ONLY), does NOT lift either DO-NOT-SERVE order, does NOT certify any packet, does NOT assert that any decision is supporting/contrary/limiting, and authorises NO owner question. NOT_APPLICABLE / NOT_MEASURED is never a pass.

## Evidence

- Freeze record: `evaluation/OPERATIONAL_RESUME_39628161040_FREEZE.json` (sha256 `ee40ce42e32b2b06818b7f136b1f680bf4e8e2dee7fbc100c8d1513f6bc3367a`)
- Producer record: `results/evaluation/product_cache_parity/39619144928.json` (read-only)
- Reproduction record: `results/evaluation/product_cache_parity/39628161040.json`
- Reproduction report: `reports/evaluation/PRODUCT_CACHE_PARITY_39628161040.md`
- Job evidence: `results/evaluation/operational_resume/39628161040_job_evidence.json`
- This verification record: `results/evaluation/operational_resume/39628161040.json`
