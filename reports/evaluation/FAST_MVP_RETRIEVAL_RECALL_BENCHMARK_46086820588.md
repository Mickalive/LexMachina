# FAST-MVP retrieval / counter-authority RECALL@K benchmark - run 46086820588

- **Verdict: `PRODUCT_FALSIFIED_RECALL_LOSS` (exit 1)** - the frozen recall-loss rule is violated on the current accepted product head.
- Instrument: `evaluation/fast_mvp_retrieval_recall_benchmark.py` (sha256 `fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283`), executed unchanged.
- Product mount head: `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` - accepted product cycle **40284658455**, both halves of factory-wide requirement 4 verified (`results/audit/product/CYCLE_40284658455_GATE.json` gate=PASS / safe_to_integrate=true / required_fixes=[] on the audit job checkout, and `origin/lab/product` head `7be4480e accept product cycle 40284658455`). **This head had never been measured by this instrument in the accepted lineage.**
- Direction: v68. `network_calls = 0` (offline cache replay only, 24/24 cells status 200 from cache).

## 1. Why this cycle was not zero delta

This cycle re-executes the accepted smallest executable retrieval/counter-authority benchmark that can falsify the product (`FAST MVP MODE: build the smallest executable retrieval/counter-authority benchmark that can falsify the product. Reuse existing multilingual/provenance tests. No universal-174k reruns.`) against the **current** accepted product mount head (`7be4480e`, accept product cycle 40284658455) rather than at the head frozen or last measured (`e53662be` / `5fb312e4`).

The prior accepted execution is `results/evaluation/fast_mvp_retrieval_recall_benchmark/40261335674.json` (run 40261335674), which pinned `product_mount_head = 5fb3124a71c99dce0ed6fbd2d3fce9a88ad6e68` - the head at which the defect was already published as `PRODUCT_FALSIFIED_RECALL_LOSS`. The head moved (product cycles 40247189361 -> 40284658455) and this cycle measures the newer bytes for the first time.

Nothing else in this run duplicates accepted work: the frozen hypothesis + freeze + spec + amendments are unchanged, the benchmark of record on packet-of-record 39319405429 is not re-run, the D2 profile and bypass diagnosis are not re-derived, ordered item (2) is not executed, and no universal-174k benchmark is run.

## 2. Result (frozen claim rule, unchanged)

Frozen rule: exit 0 iff (a) every discriminating cell `product_retention@20 >= input_retention@20`; (b) micro-aggregate `product_hits@20 >= input_hits@20`; (c) no language with `input_hits@20 > 0` has `product_hits@20 < input_hits@20`.

| measured | value |
|---|---|
| verdict / exit | `PRODUCT_FALSIFIED_RECALL_LOSS` / 1 |
| cells / discriminating / not measured | 24 / 10 / 14 |
| aggregate `all` | input_hits **17** vs product_hits **15** of present_denominator 18 (input retention 0.9444, product retention 0.8333) |
| aggregate `baseline` channel | input_hits **5** -> product_hits **3** (n_cells 3) |
| aggregate `counter` channel | input_hits **12** -> product_hits **12** (n_cells 7) - **no loss** |
| language leg `fr` | input 4 -> product 3, holds=**false** |
| language leg `de` | input 12 -> product 11, holds=**false** |
| language leg `it` | input 1 -> product 1, holds=true |
| blocking controls | 9/10 passed, `failed_controls = []` (C7b duplicates is REPORTED-ONLY under the frozen V1_2 amendment and never gates) |
| rerank latency (reported-only) | mean 0.004000 s, max 0.022871 s over 24 cells; no frozen latency threshold exists and none was invented |

Cells that lose ground truth under the product ordering:

- `baseline:business-judgment-rule:de` - input retention 1.0 -> product retention **0.0**; `loss_vs_input` = `bger_4A_219_2015`, `bger_4A_603_2014`.
- `counter:petty-theft-dismissal:fr` - input retention 1.0 -> product retention 0.667; `loss_vs_input` = `ge_gerichte_CAPH_107_2004`.

The loss sits in the **known-relevant / baseline** leg (5 -> 3), not in the counter-authority leg (12 -> 12): the product reranker, not the OpenCaseLaw search layer, drops frozen authorities its own candidate input had already kept in the top-20.

## 3. Pre-registered side-by-side against the prior accepted run 40261335674

Machine record: `results/evaluation/fast_mvp_retrieval_recall_benchmark/46086820588_COMPARISON_40261335674.json`.

| field | 40261335674 (head `5fb312e4`) | 46086820588 (head `7be4480e`) | identical |
|---|---|---|---|
| verdict | PRODUCT_FALSIFIED_RECALL_LOSS | PRODUCT_FALSIFIED_RECALL_LOSS | yes |
| exit_code | 1 | 1 | yes |
| claim (rule, aggregate, losses_by_cell, language_leg, n_discriminating_cells) | - | - | **yes (byte-equal)** |
| failed_controls / n_controls / n_controls_passed | [] / 10 / 9 | [] / 10 / 9 | yes |
| frozen hypothesis + spec digests | `a9fe256c...` / `187b0e54...` | `a9fe256c...` / `187b0e54...` | yes |
| per-cell substantantive content | 24 cells | 24 cells | **0 of 24 cells differ** (only the reported-only `rerank_seconds` wall-clock field differed) |

H1 as pre-registered is **confirmed**: the reranking recall-loss defect observed at `5fb312e4` persists unchanged on the newer accepted head `7be4480e`, with a byte-equal claim object and identical controls.

## 4. What this run does NOT claim

- It does not claim absolute retrieval quality, that "retrieval works", any frozen bar met, serving readiness or jurist utility; a PASS would only ever have meant "no loss observed on the discriminating cells".
- It does not move, re-derive or re-tune any frozen bar, rubric, threshold, k value, population predicate or verdict contract.
- It does not lift either accepted DO-NOT-SERVE order, does not certify packet admission, and does not re-issue the retracted parity claim.
- It does not re-run the benchmark of record on packet-of-record 39319405429, does not re-run the D2 profile or the bypass diagnosis, and does not execute ordered item (2).
- `human_gate_ready = false`, `machine_gate_ready = false`, `ready_for_owner_session = false`, `owner_decision_required = false`. The comparative map-versus-ranked-list half stays NOT SCORED.
- Corpus docs are `gates.row_text` (title + regeste + snippet) from the per-cell OCL cache, not the product's production `full_text` pipeline.
- No cross-machine byte-identity is asserted.

## 5. Reused assets (REUSE-FIRST)

- Frozen multilingual ground truth and 24-cell FR/DE/IT x baseline/counter cache - reused by re-hash, never re-derived.
- Accepted multilingual / provenance suite `tests/evaluation/test_retrieval_benchmark.py` (protocol digest `e1a0b18d...`, sha256 `558e1f1b...`) - **not edited**, re-executed under the documented no-pytest shim: `SHIM_PASS`, 2 passed / 0 failed.
- Accepted instrument suite `tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py` - `SHIM_PASS`, 7 passed / 0 failed.
- Lane claim-path state integrity gate - **ALL_CHECKS_PASS 11/11**.
- Lane suite - **PASS 88/89 checks** (the single non-pass is the standing pytest-absent SKIP).

## 6. Environment and network disclosure (factory-wide requirement 30)

The producer image ships no `numpy`/`scipy`/`sklearn`; three free public-index packages were installed before execution: numpy **2.5.4**, scipy **1.18.1**, scikit-learn **1.9.1** - byte-version-identical to the numeric environment recorded by the prior accepted run 40153908549. Python 3.14.4; `numeric_environment` in the result record. No BLAS build, thread count or `PYTHONHASHSEED` pin is claimed.

**Non-measurement network this run**: three `pip install`s and package verification only; **zero** OpenCaseLaw, retrieval, embedding, model or paid-API calls; the measurement itself ran with `network_calls = 0`.

## 7. Ordered-work status (v68)

| item | status |
|---|---|
| (1) bypass-clause correction of record | **DISCHARGED**; not re-run, measurement unchanged |
| (2) conditional post-repair re-measure | **NOT_YET_DISCRIMINATING** - frozen 15-member family is 14/15 at an unchanged product head; full protocol not executed, no synthetic stand-in, packet-of-record not scored, standing falsification not re-run |
| (3) standing falsification record of record | **KEPT**, untouched; this run adds a separate pre-registered recall measurement on new bytes and supersedes nothing |
| (4) the three non-blocking required fixes of `CYCLE_39965089504_GATE.json` | reported only where quoted; not quoted here |
| (5) no re-derivation of closed work | **HONOURED** - no frozen bench, D2 profile or bypass diagnosis re-derived; no 174k benchmark run |

## 8. Recommendation

**`PIVOT_WITHIN_MISSION`** at the lane level is not needed; the concrete next step belongs to Core Product: treat the reranking recall loss as an open product defect on the current accepted head - the current accepted head still drops `bger_4A_219_2015`, `bger_4A_603_2014` (DE, business-judgment-rule) and `ge_gerichte_CAPH_107_2004` (FR, petty-theft-dismissal) out of the top-20 that its own input order kept, and the loss is in the known-relevant channel (5 -> 3), not the counter channel (12 -> 12).

For this lane: `continue_recommended = false` - after this run there is no further same-question cycle with a discriminating purpose until Product changes either the retrieval/reranking code or the item-(2) family. This cycle is **PENDING_INDEPENDENT_AUDIT**; `accepted_run_id` remains 40258497460 (both halves of requirement 4 verified), and no claim here is promoted to accepted evidence before that audit.
