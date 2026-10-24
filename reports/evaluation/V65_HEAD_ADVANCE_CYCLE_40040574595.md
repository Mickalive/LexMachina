# Evaluation cycle 40040574595 — report of record

**Lane:** evaluation (query-map MVP falsifier)
**Direction:** v65 — re-opened lane question, ordered work items 1 / 2 / 3 / 5 executed; item 4 conditional and not resumed
**Run:** 40040574595
**Executed:** 2026-10-24 (UTC)
**Verdict:** `PASS_NO_FALSIFICATION` (exit 0) **with an accepted-class NEGATIVE RESULT on H2** (`H2_FALSIFIED`)
**Freeze-first:** hypothesis `734a447d…` + freeze record `c954f62c…` + instrument `8a7e19c9…` + guard tests `e45c6641…` committed at `d2649360` BEFORE any claim-bearing execution of this run
**Posture (unchanged, fail-closed):** `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`. Both DO-NOT-SERVE orders stand. Admission stays fail-closed.

---

## 0. Re-open trigger and requirement-4 lineage

The v65 lane question re-opens on **PRODUCT HEAD CHANGE** and **NEWER ACCEPTED PRODUCT MEASUREMENT**.

| step | accept commit | cycle | gate | accept commit present | counts as lineage |
|---|---|---|---|---|---|
| prior anchor (run 40012474431) | `f9618377` | 40005362253 | PASS | yes | prior |
| new | `2ee36779` | 40025340938 | PASS, safe_to_integrate=true | yes | **yes** |
| new | `e4f72a8e` | 40032389983 | PASS, safe_to_integrate=true | yes | **yes** |

Frozen NON-lineage exclusions, both **verified excluded by measurement, not assumed**:

* **40018153655** — audit gate `REVISE`, no accept commit on `lab/product`. Exclusion verified: `requirement_4_both_halves=false`.
* **40028750240** — audit gate `PASS` but **no** `accept product cycle 40028750240` commit exists on `lab/product`. Exclusion verified: `requirement_4_both_halves=false`. A PASS gate alone is not an accept event under factory-wide requirement 4; the cycle is disclosed, not laundered into the lineage.

New accepted head: **`e4f72a8e6c0460bc52dc625ff3e2da86161e2564`** (accept product cycle 40032389983).

---

## 1. Ordered item 1 — currency cross-check

39 frozen quantities were checked against the product's own committed artifacts on the new head. Published values are the product's committed claims (audit evidence summaries of the two accepted cycles plus `state/product.json`); found values are read from the artifacts.

| class | count |
|---|---|
| CONFIRMED | **36** |
| DIVERGENT | **0** |
| NOT_FOUND | 0 |
| CONFIRMED_LAG (disclosed exception) | 2 |
| NOT_REEXECUTED_THIS_CYCLE (disclosed exception) | 1 |

**Headline (applied precision-matched, 5e-4): `ALL_CONFIRMED`.**
**Headline (frozen literal 1e-6): `ALL_CONFIRMED`.** No float quantity is at issue this cycle; both verdicts are published anyway under the accepted D-A dual-verdict convention.

Confirmed families (all reproduce from the committed artifacts):

* offline slice `20261023T224250Z` (accept 40032389983): `verified=true`, `page_contract=true`, `PASS 67 assertions`, 100 decisions, 8 clusters, largest cluster 35, 4 cited decision IDs, 5 counter-status-bearing rows, `answer_status=ready`, `geometry_preserved_by_enrich=true`, network `none`, 165 candidates → 100 rows, `rows_with_source_url=100`;
* server slice `20261023T224255Z` (accept 40032389983): 10/10 checks PASS, 100 first → 100 final decisions, 8 clusters, 2 cited IDs, 1 counter authority, `rows_with_source_url=100`, geometry preserved;
* source validity: 100/100 `canonical_url` hosts exactly `mcp.opencaselaw.ch`; all `answer.cited_decision_ids` resolve to bundle rows; `provenance.cache_stats.writes=0`;
* prior-head offline slice `20261023T190402Z` (accept 40005362253): 100 decisions, 5 counter-status-bearing rows (stability anchor);
* `state/product.json`: `rows_with_source_url=100`, `offline_slice_legs_passed=4`, `page_contract_assertions=67`, `served_checks_passed="10/10"`, and all four fail-closed posture flags still `false`;
* both new gate files carry `gate=PASS`.

Disclosed exception classes (frozen before execution, never absorbed):

1. **CONFIRMED_LAG ×2** — `state/product.json` still carries `accepted_run_id=40000001926` and `current_run=40005362253`, both behind the accepted head `e4f72a8e` / accept 40032389983. This lag was already disclosed by the v65 director question and by evaluation run 40012474431; this run measures it and labels it `CONFIRMED_LAG`. It is a state-pointer hygiene item for Core Product, **not** a currency divergence.
2. **NOT_REEXECUTED_THIS_CYCLE** — the `claim_ceiling` string in `state/product.json` asserts "All 188 MVP tests pass". This lane does not re-execute the product's 1550-test suite; the accepted independent audit of CYCLE_40032389983 already recorded the MVP-relevant suite counts. The claim is recorded `NOT_REEXECUTED_THIS_CYCLE` and is never laundered into a confirmation.

---

## 2. Ordered item 2 — shipped-slice counter-evidence probe (H2) — **H2_FALSIFIED**

This is the new discriminating leg of this cycle and the smallest executable counter-authority falsification on the product's **own** shipped artifacts. It targets the binding v65 bottleneck (**EVIDENCED COUNTER AUTHORITY**) directly.

**It scores no frozen bar.** Its population is the product's shipped slice bundles, which are **not** the `RULES_LABEL` population (packet-of-record `39319405429`). The frozen rubrics were re-hashed REPORTED-ONLY and were never applied, edited or re-derived (factory-wide requirement 22). No abstention semantics, support rate or geometry criterion of the frozen scorer is computed or implied.

**Population (frozen):** 14 newly shipped slice bundles (10 offline from accepts 40025340938 / 40032389983, 4 server from accept 40032389983) + 1 prior-cycle control bundle (`20261023T190402Z`, accept 40005362253). Claim-bearing rows = rows with `counter_evidence_verified === true`.

**Frozen defect predicates:**

| code | predicate |
|---|---|
| `D1_empty_evidence` | `counter_evidence` null/empty/whitespace on a verified row |
| `D2_letterhead_zone` | evidence is a verbatim substring of the row's **own** `full_text` at first-occurrence offset `< 400` |
| `D3_markup_residue` | evidence contains any frozen markup token (`<mark>`, `</mark>`, `<em>`, `</em>`, `<b>`, `</b>`, `<highlight>`) |
| `D4_language_marker_mismatch` | row language ∈ {de, fr, it}; evidence has **0** markers of its own language and `≥ 3` markers of a different frozen language set |

### Result

| quantity | value |
|---|---|
| bundles probed | 15 (14 present + … one bundle `20261023T202433Z` present with **0** verified rows) |
| `counter_evidence_verified` rows | **14** |
| of those carrying ≥ 1 frozen defect | **14 (100 %)** |
| defect histogram | `D2_letterhead_zone` 10 · `D3_markup_residue` 4 · `D4_language_marker_mismatch` 4 |
| verdict | **`H2_FALSIFIED`** |

Per-bundle: every offline snapshot except `20261023T202433Z` marks exactly one verified row, and it is the **same decision every time**; every server snapshot marks exactly one verified row, and it is the **same decision every time**.

### The two distinct defective decisions

Aggregated post-hoc under a disclosed aggregation artifact (`…_H2_distinct_decision_aggregation.json`, sha256 `dd1d0bb8…`) — an aggregation, **not** a new predicate or threshold:

| decision | language | status | defect(s) | grounded in | evidence | bundles |
|---|---|---|---|---|---|---|
| `gr_gerichte_ERZ 2010 25` | de | candidate-limiting | **D2_letterhead_zone** | own `full_text` at offset **0** | the court **letterhead** — "Kantonsgericht von Graubünden / Dretgira chantunala dal Grischun / Tribunale cantonale dei Grigioni / ___…" (120 chars of document header), verbatim in the row's own 48 339-char full text | 10 offline + 1 prior-cycle control |
| `bge_BGE_121_III_260` | **it** | candidate-limiting | **D3_markup_residue + D4_language_marker_mismatch** | `snippet` only (`full_text` is `lazy`, empty) | a **German** headnote opening carrying raw search-highlight markup: `Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; Erstreckung (Art. 255, 271 und 271a, 272…` on a row whose own `language` field is `it` | 4 server |

### Why this is material even though the cycle verdict is PASS

The product's **flagship shipped slice** — the artifact it points `state/product.json.vertical_slice_status.served_artifact` at and the artifact the accepted audits independently reproduced — marks its **only** counter-evidence-verified row as verified with (a) a court letterhead as the evidence, or (b) a German headnote with `<mark>` residue on an Italian-labelled row. 14 of 14. No verified row in any shipped slice carries counter-authority *reasoning*.

This is exactly the content class the direction names as the binding bottleneck, now measured **on the product's own artifacts** and not only on the frozen packet. It reinforces, with new evidence, why the comparative map-versus-ranked-list half of the Master Prompt's central product question stays **VACUOUS**: the surface that would have to be evidenced is not evidenced, and the defect is in the evidence extractor, not in retrieval.

**Preserved as a NEGATIVE RESULT.** It is not a frozen-bar score, not a serve-verdict input, not a divergence of a published quantity, and it changes no threshold.

### Scoping disclosure (frozen before execution)

Three of the fourteen new bundles were inspected during scoping in order to decide the probe was worth building and are labelled `scoping_inspected=true` in the artifact (`…T203316Z`, `…T224250Z`, server `…T224255Z`). The other eleven new bundles and the prior-cycle control were **not** inspected per-row before the freeze; all reproduce the same two defects. Every definition, offset, marker list and success rule was fixed before any of them was read.

---

## 3. Ordered item 3 — falsification re-run on the new head (same frozen rule set)

Re-executed through the **accepted** wrapper `evaluation.minimal_retrieval_ca_benchmark` (no re-implementation) against **unchanged** packet-of-record bytes `39319405429` (re-hashed `32ac8126…`, identical before and after).

| quantity | value |
|---|---|
| verdict | **`PRODUCT_FALSIFIED`** (exit 1) |
| falsification proven | true (served packet passes regression; regressed input makes the gate fail) |
| gates | 11 passed / 4 failed / 18 total, 3 questions measured |
| failed gates | identical to the accepted four-gate set |
| engine `input_drift` | **empty** |
| product mount head read by the engine | `e4f72a8e…` (the new head) |

Accepted failed-gate set, reproduced byte-for-byte:

* `mf::concept_coverage::39319405429::de-kapitalverletzung`
* `mf::counter_authority_surface::39319405429::de-kapitalverletzung`
* `mf::counter_authority_surface::39319405429::fr-bail-entretien`
* `mf::counter_authority_surface::39319405429::it-responsabilita-medica`

The packet-versus-product delta is therefore **isolated, not inferred**: the product head moved two accepted steps and the frozen-rule falsification verdict did not move.

*direction_version disclosure:* wrapper/engine carry `61`/`57` against lane `65`. Those are historical fixture pins of the accepted instrument; disclosed, not repaired.

---

## 4. Ordered item 4 — planner-remedy and degradation pin re-verify (new run id)

Re-pinned under run id `40040574595`; no prior freeze was edited in place (a file named for run X holds run X's measurement).

| finding | value | verdict |
|---|---|---|
| `product/query/adversarial_retrieval.py` sha256 | `9764a37e…` | **CONFIRMED** |
| remedy-A ordering (`strip_redaction_placeholders` defined and nested inside `answer_key_terms`) | holds | **CONFIRMED** |
| `e_EMISSION_WRITER_ABORT` marker visible on measurement `40000001926`, 1/7 legs degraded, `degradation_visible_rate=1.0` | holds | **CONFIRMED** |
| `product/query/pipeline.py` sha256 | `265b82ac…` | **CONFIRMED** as the **new baseline of record** |
| frozen product pins re-hash (9 pins) | 8 CONFIRMED, 1 divergent | `DRIFT_REPORTED` |

The single divergent pin is `pipeline.py` `e105bfed… → 265b82ac…`, the **same** product-advance drift already disclosed (not absorbed) by run 40012474431. This run re-pins `265b82ac…` as the new baseline of record under run id `40040574595` and leaves every prior freeze byte-untouched. The degradation pin's older 7-of-7-DEGRADED property belongs to measurement `39956256289` (the outage date) and is **not** re-required here; the frozen pin semantics for this run is marker visibility with rate 1.0.

---

## 5. Controls — 5/5 PASS

| control | result |
|---|---|
| `C1_planted_currency_divergence_is_detected` | PASS — planted `n_decisions=42` detected against published 100 |
| `C2_probe_classifies_planted_letterhead_mid_and_markup` | PASS — planted letterhead fires `D2`, planted mid-document legal phrase (offset > 400) does **not** fire `D2` and classifies `COUNTER_REASONING`, planted `<mark>` fires `D3` |
| `C3_probe_detects_language_marker_mismatch` | PASS — planted German headnote on an `it` row fires `D4`; the same string on a `de` row does not |
| `C4_frozen_rules_rehash_holds_reported_only` | PASS — `RULES_LABEL` `4457e971…`, `RULES_GEOMETRY` `a7452748…`, identical before and after, never applied |
| `C5_packet_of_record_bytes_unchanged` | PASS — `32ac8126…` before and after |

All 25 frozen pins were re-identical after execution (zero frozen/historical edits). Numeric environment disclosed (requirement 30): Python 3.12.3, linux, numpy/scipy/sklearn **absent**, thread env unset — the instrument is pure-Python and has no BLAS reduction-order dependency.

---

## 6. Ordered item 5 — required fixes D1/D2/D3 of CYCLE_39965089504

Reported only where this lane quotes those counts: the CYCLE_39965089504 independent audit returned **three NON-BLOCKING required fixes D1/D2/D3**; they were discharged by the product lane before the heads cross-checked here. No new D-fix count is asserted by this cycle.

---

## 7. Coverage-v2 re-freeze — CONDITIONAL, NOT EXECUTED

The coverage family is **not** resumed this cycle, so the transferred coverage-v2 re-freeze (v64 product item 7(b), ceded to this lane's freeze) is **not** executed. The underlying parity record `39631600439` stays `EXPLORATORY` with `pending_independent_audit=true` — disclosed, never laundered into REPRODUCED or ACCEPTED.

---

## 8. Test reuse (REUSE-FIRST) — no new framework, existing suites re-executed

| suite | files | result |
|---|---|---|
| this cycle's guard tests | `tests/evaluation/test_v65_head_advance_crosscheck_v2.py` | **12 passed / 0 failed** |
| multilingual / provenance reuse | `test_stand_ready_multilingual_probe.py`, `test_f3b_restore_disposition.py`, `test_v59_stand_ready_verification.py`, `test_packet_of_record_stand_ready.py` | **73 passed / 0 failed** |
| falsification family | `test_minimal_ret_ca_benchmark.py`, `test_mapping_free_recall_falsifier.py`, `test_v65_product_advance_crosscheck.py`, `test_minimal_retrieval_ca_benchmark.py` | 50 passed / **1 failed** / 21 unsupported (shim) |

The single failure is a **pre-existing state hygiene defect, reproduced not caused by this cycle**: `state/evaluation.json.evidence_refs` contains 187 refs of which exactly one — `results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt` — does not resolve on disk. `git log --all` over that path is empty: the file was **never committed**. It is a dangling pointer to a producer work-state text file, not a deleted claim-bearing result. Disposition: the ref is removed from `state/evaluation.json` in this cycle's state update, with the removal disclosed here and in the state, and `n_evidence_refs` reconciled to 186.

21 `UNSUPPORTED` cases are the shim's documented upper bound (parametrised/marker constructs the no-pytest runner does not implement); they are counted as not-run, never as passed.

**No obsolete universal-174k benchmark was rerun.** The 174k corpora, dense embeddings, join-alignment and fractal-map suites were not touched.

---

## 9. Claim ceiling

This cycle cross-checks published product quantities against their own committed artifacts on the newest accepted head; audits the counter-evidence quality of the product's own newly shipped slice bundles under frozen, non-bar definitions; and re-executes the accepted mapping-free falsification benchmark on unchanged packet-of-record bytes under the same frozen rules re-hashed REPORTED-ONLY.

It **scores no frozen bar**, re-derives no threshold, classifies no decision under the frozen rubric, and asserts no serve or human-gate readiness. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is **NOT scored** while zero counter rows are evidenced on the packet (requirement 22). The `H2_FALSIFIED` result is a preserved negative finding about the product's own artifacts; it does not by itself change any accepted verdict, and no owner decision is requested.

---

## 10. Recommendation

**CONTINUE** under the same v65 question, with one sharpening for the Director's successor question:

* the currency/falsification/pin legs of the v65 question are now **exhausted for this product head** — they re-confirm cleanly and would only re-confirm again;
* the binding, now *measured-on-shipped-artifacts* blocker is the **counter-evidence extractor itself**: 14/14 verified rows on the flagship slice are letterhead / markup-residue / language-mismatch. A further evaluation cycle under the same question has a concrete discriminating purpose **only if the product lands a counter-evidence-extractor change**; otherwise the next useful cycle is the product-side repair, not another cross-check.

`continue_recommended = true` (the counter-authority evidence gap is still the binding blocker and the product head keeps moving), `evidence_tier = REPRODUCED` pending independent audit, `human_gate_ready = false`, `owner_decision_required = false`.

---

## 11. Artifacts of record

| artifact | sha256 (first 16) |
|---|---|
| `evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json` | `734a447dffd86a36` |
| `evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json` | `c954f62cfab2b5c3` |
| `evaluation/v65_head_advance_crosscheck_v2.py` | `8a7e19c9f1c31bbc` |
| `tests/evaluation/test_v65_head_advance_crosscheck_v2.py` | `e45c6641e7d74e7b` |
| `results/evaluation/v65_head_advance_crosscheck/40040574595.json` | `5f1e51ac9f101ed1` |
| `results/evaluation/v65_head_advance_crosscheck/40040574595_H2_distinct_decision_aggregation.json` | `dd1d0bb8d259bf00` |
| `results/evaluation/v65_head_advance_crosscheck/falsification/40040574595.json` | `8bfd45fb0286ae48` |
| `results/evaluation/v65_head_advance_crosscheck/falsification/40040574595_engine_mapping_free_recall_falsifier.json` | `d9ada2ee0ec33bab` |
| `results/evaluation/orchestration/40040574595_self_suite_pytest_shim.json` | `5f99d47778988ffa` |
| `results/evaluation/orchestration/40040574595_multiling_prov_pytest_shim.json` | `85dbcc554f62158a` |
| `results/evaluation/orchestration/40040574595_falsification_family_pytest_shim.json` | `a49d9148624626ad` |
| `reports/evaluation/V65_HEAD_ADVANCE_CROSSCHECK_40040574595.md` | `e0603d4d7cf23437` |
