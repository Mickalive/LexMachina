# FAST-MVP retrieval / counter-authority RECALL@K — run 46122736362

- **Verdict: `PRODUCT_FALSIFIED_RECALL_LOSS` (exit 1)** under the frozen claim rule, on the current accepted product head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` (accept cycle 40284658455) — a byte head this instrument had **never measured**.
- **Pre-registered H1 is confirmed**, and published as a **CONFIRMATION on new shipping bytes**, not as a second independent falsification of a different defect.
- Direction `v68` (mounted control plane at `/tmp/lex_control`, authoritative regardless of the 2026-11-28 calendar date). `network_calls = 0`; 24/24 cached cells status 200.
- Fail-closed posture unchanged: `packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`, `ready_for_owner_session=false`, `owner_decision_required=false`. No serve verdict, no DO-NOT-SERVE order lifted.

## 1. Freeze-before-outcome (claim-bearing evaluation)

| artifact | sha256 |
|---|---|
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46122736362_HYPOTHESIS_V1.json` | `dbdec20ebd5aa4ba66eceaddc34b2be586bda270989b278f0627a7d205b01e6d` |
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46122736362_FREEZE_V1.json` | `660e8e561f18318d12408e87a679eb86faf3933dce22e4f19bbb0b4e2d2df2ee` |
| `results/evaluation/fast_mvp_retrieval_recall_benchmark/46122736362_PRE_EXECUTION_PINS.json` | `73e6fe9ffe019aff59ac09a5ca99439f49d9f0924100de2ded7a1bde268b3d24` |
| `results/evaluation/fast_mvp_retrieval_recall_benchmark/46122736362_POST_EXECUTION_PINS.json` | `927c574471f978427252712a82d67b7db2a54f374fa9440a7daa16303b331fd3` |

`freeze_recorded_at_utc = 2026-11-28T07:52:09Z`; the result file `results/evaluation/fast_mvp_retrieval_recall_benchmark/46122736362.json` did **not** exist at freeze time (recorded in the pre-execution pins). Every pin held before execution (`all_pins_hold=true`) and the hypothesis/freeze-record bytes were unchanged after execution (`all_hold=true`). This local execution did **not** create a git commit; freeze-first is established by these timestamped, hash-pinned artifacts and by the absent result file at freeze time — disclosed, not claimed as a commit-ordering proof.

Reused frozen inputs, verified by re-hash and never re-derived: instrument `fa5aa9a5…`, frozen hypothesis `a9fe256c…`, amendments `ce1a481d…` / `13f2eca1…`, spec `187b0e54…`, cache digest manifest `700b2a1c…` (24 envelopes, verifier `all_passed=true`), accepted multilingual/provenance suite `558e1f1b…` / protocol digest `e1a0b18d…`.

## 2. Why this cycle was not zero delta

The accepted executions of this instrument pin product heads `e53662be` (run 40153908549) and `5fb312e4` (run 40261335674); the current shipping head `7be4480e` had never been scored. Both halves of factory-wide requirement 4 hold for it: `results/audit/product/CYCLE_40284658455_GATE.json` (`gate=PASS`, `safe_to_integrate=true`, `required_fixes=[]`, sha256 `d7b902214fd0931a328b366f2e431a7ade89b034ac722d07cd380bb1ddcc8011`) and the mount HEAD commit subject `accept product cycle 40284658455`.

**Disclosed limitation (not hidden):** the product cycles between `5fb312e4` and `7be4480e` were state-pointer hygiene, fixture-anchor exposure and repair rounds; this lane cannot diff them because the accepted mount is a shallow single-commit clone (`git rev-parse --is-shallow-repository=true`; only `7be4480e` resolvable). Because the verdict below is byte-identical to run 40261335674, it is a **confirmation on never-before-measured bytes**, not evidence of a new or worsening defect.

## 3. Result (frozen claim rule, unchanged)

| measured | value |
|---|---|
| verdict / exit | `PRODUCT_FALSIFIED_RECALL_LOSS` / 1 |
| cells / discriminating / not measured | 24 / 10 / 14 |
| aggregate `all` | input_hits **17** vs product_hits **15** of present_denominator 18 (retention 0.9444 → 0.8333) |
| aggregate `baseline` (known-relevant) | input_hits **5** → product_hits **3** (n_cells 3) |
| aggregate `counter` | input_hits **12** → product_hits **12** (n_cells 7) — **no net loss** |
| language `fr` | input 4 → product 3, `holds=false` |
| language `de` | input 12 → product 11, `holds=false` |
| language `it` | input 1 → product 1, `holds=true` |
| blocking controls | 9/10 passed, `failed_controls=[]` (C7b duplicates REPORTED-ONLY under the frozen V1_2 amendment, never gates) |
| rerank latency (reported-only) | mean 0.006551 s, max 0.082295 s over 24 cells; no frozen latency bar exists and none was invented |

Cells losing a frozen authority from the product top-20 that the input order retained:

- `baseline:business-judgment-rule:de` — input retention 1.0 → product retention **0.0**; `loss_vs_input = [bger_4A_219_2015, bger_4A_603_2014]`.
- `counter:petty-theft-dismissal:fr` — input retention 1.0 → product retention **0.667**; `loss_vs_input = [ge_gerichte_CAPH_107_2004]`.

The loss sits in the **known-relevant / baseline** channel (5 → 3); the counter channel shows no net loss (12 → 12). This is the retrieval-first violation the Master Prompt forbids ("a visualization cannot reveal an authority that retrieval failed to find"), measured on the currently shipping bytes.

Under the original V1 blocking C7 the record is `NOT_MEASURED_VACUOUS` / exit 2 (duplicate alnum-core collisions on this frozen cache); published side by side per the frozen V1_2 amendment, never silently preferred.

## 4. Side-by-side with predecessors (honest confirmation)

Machine record: `results/evaluation/fast_mvp_retrieval_recall_benchmark/46122736362_COMPARISON_40261335674.json` (sha256 `9664b77ec9633af1ab93bf481d478f129b58ac27398335cd99068b6733aa369d`).

| field | 40153908549 (`e53662be`) | 40261335674 (`5fb312e4`) | 46122736362 (`7be4480e`) | identical |
|---|---|---|---|---|
| verdict / exit | FALSIFIED / 1 | FALSIFIED / 1 | FALSIFIED / 1 | yes |
| frozen claim fields (rule, aggregate, losses, language legs, n_discriminating) | — | — | — | **byte-equal to 40261335674** |
| per-cell input/product hits and retentions | 24 cells | 24 cells | 24 cells | **0 of 24 differ vs 40261335674** |
| controls | 10 / 9 | 10 / 9 | 10 / 9 | yes |

H1 as pre-registered is **confirmed**: the reranking recall-loss defect persists unchanged at the current shipping head. Because every compared field is identical, this is a confirmation on never-before-measured bytes, not a second independent falsification of a different defect. Both this verdict and the predecessor are published; neither is hidden.

### Numeric environment disclosure (factory-wide requirement 30)

Python **3.14.4**; numpy **2.5.5**, scipy **1.18.1**, scikit-learn **1.9.1** (pip-installed before execution; no paid API/model/OpenCaseLaw call). Accepted run 40261335674 recorded numpy **2.5.4**, scipy 1.18.1, sklearn 1.9.1 on Python 3.12.3 — a patch-level numpy drift and a platform/kernel difference are **disclosed**. No BLAS build, thread-count or `PYTHONHASHSEED` pin is asserted; **no cross-machine byte-identity is claimed**. The byte-equal comparison is reported as measured in this environment, not as a universal reproducibility claim.

## 5. Reused multilingual / provenance tests (REUSE-FIRST)

| suite | shim record | result |
|---|---|---|
| `tests/evaluation/test_retrieval_benchmark.py` (accepted FR/DE/IT + provenance, protocol `e1a0b18d…`) | `results/evaluation/orchestration/46122736362_shim_multilingual.json` | SHIM_PASS 2/0/0 |
| `tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py` | `…_shim_recall.json` | SHIM_PASS 7/0/0 |
| `test_fast_mvp_current_head_ca_falsifier.py` + `test_counter_evidence_quality_benchmark.py` | `…_shim_ca.json` | SHIM_PASS 14/0/1 unsupported (never counted as passed) |
| NEW run gate `test_fast_mvp_recall_shipping_head_46122736362.py` | `…_shim_gate.json` | SHIM_PASS 4/0/0 |

The no-pytest shim is NOT pytest; its counts are an upper bound on what pytest would execute. The standing pytest-absent disclosure is not withdrawn. No universal-174k benchmark was run (`no_174k_benchmark_rerun=true`, `no_universal_174k_benchmarks=true`).

## 6. Ordered-work status (v68 lane question)

| item | status |
|---|---|
| (1) bypass-clause correction of record | **DISCHARGED** earlier (`reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`); not re-run, measurement unchanged |
| (2) conditional post-repair re-measure | **NOT_YET_DISCRIMINATING** — rejection/incumbent leg landed, but the frozen 15-member family is 14/15 regenerated (accepted 40258497460); no synthetic stand-in, packet-of-record 39319405429 not scored, `d2_path_scope_probe` not re-run |
| (3) standing falsification record of record | **KEPT**, untouched; this run adds a separate pre-registered recall confirmation on new bytes and supersedes nothing |
| (4) three non-blocking required fixes of `CYCLE_39965089504_GATE.json` | reported only where quoted; not quoted here |
| (5) no re-derivation of closed work | **HONOURED** — no frozen bar/rubric/predicate/k/population/verdict edit; no D2 profile, bypass diagnosis or packet-of-record re-derivation |

## 7. Claim ceiling

This is a **relative reranking-retention measurement on 24 frozen cached rows**. It does not prove absolute retrieval quality, that "retrieval works", any LABEL_SOUND/GEOMETRY_SOUND bar, serving readiness, counter-label calibration, or that the map helps a jurist. It does not lift either DO-NOT-SERVE order. The comparative map-versus-ranked-list half stays NOT SCORED.

## 8. Recommendation

Concrete next step belongs to **Core Product**: the currently shipping head still drops `bger_4A_219_2015`, `bger_4A_603_2014` (DE, business-judgment-rule) and `ge_gerichte_CAPH_107_2004` (FR, petty-theft-dismissal) from the top-20 its own candidate input kept; the loss is in the known-relevant channel (5 → 3), not the counter channel. Fix the reranker before the human gate. Separately, regenerate at least one more post-repair `server/served` bundle so the frozen family reaches 15/15 and v68 ordered item (2) becomes discriminating.

For this lane: `continue_recommended = false` — there is no further same-question cycle with a discriminating purpose until Product changes the retrieval/reranking code or the item-(2) family. This run is **PENDING_INDEPENDENT_AUDIT**; `accepted_run_id` is unchanged at 40258497460 and no claim here is promoted to accepted evidence before its audit.
