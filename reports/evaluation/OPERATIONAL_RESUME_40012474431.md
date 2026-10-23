# Operational Resume — run 40012474431 (evaluation, direction v65)

## Why this run exists

Producer runs **40006151200** (Core evaluation dirV65 repair0) and **40011795717** (its
resilience-dispatched resume) both failed the team job with **rc=67
`LEX_ZERO_DELTA_REPAIR`** — the zero-delta guard fired *as designed*: each Ox
producer session explored the v65 question, scoped the deliverable and left a full
work-state/next-move plan in its session log, but committed **zero** durable
repository delta before its session ended, so `HEAD` was unchanged and
`git status --porcelain` was empty when the wrapper evaluated the guard. Audit and
integrate jobs were skipped on both runs; the resilience job succeeded both times
and dispatched the next resume. This run 40012474431 is that next resume.

Full diagnosis (job records, log tails, producer plans, failure classification):
`results/evaluation/orchestration/40011795717_diagnosis.json` (plus per-run REST
captures and log tails under `results/evaluation/orchestration/40006151200/` and
`…/40011795717/`), committed freeze-first at `596fde17` **before** any
claim-bearing execution.

The route-around: this run concretely commits the deliverable the two producers
scoped — freeze-first hypothesis + freeze record (commit 596fde17), then the v65
product-advance currency cross-check instrument, its results, the falsification
re-run, the offline multilingual/provenance reuse, the re-derivation test shim, this
report and the state update — so the zero-delta guard cannot fire on an empty delta.

## Scope executed (same question, same frozen pins)

v65-style product-advance currency cross-check of the two newly accepted product
heads — **beb227a6** (accept product cycle 40000001926) and **f9618377** (accept
product cycle 40005362253, gate PASS) — plus a falsification re-run on unchanged
packet-of-record bytes. FAST MVP mode: reuse accepted instruments; no obsolete 174k
reruns; no coverage-v2 re-freeze (conditional, not triggered).

Frozen pins (re-hashed identically at freeze and at run):

| pin | value |
|---|---|
| product mount HEAD | `f9618377f67d8a79205fab86646d724f9739a339` |
| packet 39319405429 | `32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70` |
| RULES_LABEL | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` |
| RULES_GEOMETRY | `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` |
| planner `product/query/adversarial_retrieval.py` | `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9` |
| hypothesis | `9382a0a9a666a2e883a5c9590efd8c3759707c223f228cd4d9447889dc97b9f6` |

Hypothesis: `evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json`.
Freeze record: `evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_FREEZE_RECORD_V1.json`
(17 product artifacts pinned; requirement-4 halves enumerated; dual float
tolerances frozen).

## Verdict

**PASS_NO_FALSIFICATION** (instrument exit 0).
Record: `results/evaluation/v65_product_advance_crosscheck/40012474431.json`.
Report: `reports/evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_40012474431.md`.

### Currency cross-check

- 57 frozen quantities across both accepted cycles: **CONFIRMED 57, DIVERGENT 0,
  NOT_FOUND 0, CONFIRMED_CORRECTED (disclosed) 1**.
- Requirement-4 lineage: both accepted product cycles carry both halves (gate PASS
  + accept commit) — **all accepted**.
- Frozen exception class `kind=correction_landed`: the CYCLE_39986094168 report
  table labels the 6-emission arm `candidate` while the artifact's `candidate` arm
  emits 1 and `candidate_unguarded` emits 6; product's CYCLE_40005362253.md carries
  the correction ("unguarded diagnostic", "arm semantics disclosed"). Row counted
  in n_corrected, never silent.
- Planner/degradation pins: overall **CONFIRMED**; one product-advance drift
  (`product/query/pipeline.py` `e105bfed…` → `265b82ac…`) disclosed, never a
  must-hold pin. Degradation pin weakened on purpose to marker-visibility
  semantics on the newest measurement 40000001926 (6 MEASURED +
  1 DEGRADED_WRITER_ABORT, rate 1.0, all n_counter_rows==0), disclosed in the
  hypothesis.

### Dual float convention (accepted D-A)

- Frozen literal 1e-6: DIVERGENCE_PRESENT (54 / 2 / 0) — the two divergences are
  the known 3-decimal publication-precision artefacts
  (`ready_rate` 0.857 vs 0.85714…, `prose_citation_validity` 0.982 vs 0.98181…).
- Applied precision-matched 5e-4: **ALL_CONFIRMED** (57 / 0 / 0).
- Both verdicts published per quantity; the frozen rule was not edited.

### Falsification re-run (accepted wrapper, unchanged)

`python -m evaluation.minimal_retrieval_ca_benchmark --run-id 40012474431
--packets 39319405429 --product-mount /tmp/lex_accepted/product` →
**PRODUCT_FALSIFIED**, 11/18 gates passed, **4 failed gates identical to the
accepted set of run 39986080045** (concept_coverage de 2/8 zero; zero
counter-authority rows on de/fr/it), input drift empty, non-vacuity controls hold.
Artifacts: `results/evaluation/v65_product_advance_crosscheck/falsification/`.
Wrapper/engine direction_version 61/57 vs lane 65 disclosed (historical fixture
pins, not repaired).

### Multilingual / provenance reuse (accepted V61-era instrument, unchanged)

Offline re-run verdict **PARTIAL_MISS** (0/3 row_ok) — the accepted D-B
characterization of record: the top-level query field exists on all three bundles
(the script tests the provenance-block query key); the language key is present on
every decision with an explicit null on de 50 / fr 37 / it 47 decisions, equal to
the engine's UNLABELLED counts. Bundle SHAs match frozen pins; language
robustness holds. Rows byte-equivalent to the accepted 39986080045 record.
Wrapper: `results/evaluation/v65_product_advance_crosscheck/40012474431_multilingual_provenance_reuse.json`.

### Controls

- **C1** planted currency divergence is detected (0.857 planted vs 0.85714…,
  abs delta 0.357): **PASS**
- **C2** frozen rules re-hash holds (before == after == frozen pins): **PASS**
- **C3** packet bytes unchanged (mount pin before == after): **PASS**

## Re-derivation test shim

`tests/evaluation/test_v65_product_advance_crosscheck.py` — **22 passed / 0
failed / 0 skipped** (real pytest 9.1.1). Independent re-derivation of the
headline floats, the span-selection arms, the correction-row disclosure, the
verdict contract, the dual-float counts, the falsification gate set, the freeze
pins and the multilingual wrapper equivalence. Mount-dependent tests skip with an
explicit reason when the ephemeral product mount is absent (never a silent pass).

## Posture (unchanged)

- `human_gate_ready` = false; `machine_gate_ready` = false;
  `packet_admitted` = false; `ready_for_owner_session` = false.
- Both DO-NOT-SERVE orders stand. Admission stays fail-closed. Frozen absolute
  bars stay REPORTED-ONLY and unmet on the v3 bytes. The comparative
  map-versus-ranked-list half of the Master Prompt's central product question
  stays VACUOUS (zero counter-authority rows evidenced). No threshold, bar,
  rubric or verdict contract was re-derived or weakened. No obsolete 174k
  benchmark was run. `owner_decision_required` = false.

## Lineage

- Accepted evaluation base: `c7913e95` (accept evaluation cycle 40002636192).
- Accepted measurement of record: run 39986080045 (gate PASS) with repair round 1
  (D-A/D-B/D-C).
- Freeze-first commit of this cycle: `596fde17` (hypothesis, freeze record,
  orchestration diagnosis of 40006151200/40011795717).
- Instrument of record: `evaluation/v65_product_advance_crosscheck.py` (new file;
  the prior pinned instrument `evaluation/v65_currency_crosscheck.py` was not
  edited).

## Next recommendation

CONTINUE under the same v65 question: cross-check the next accepted product head
as it lands; execute the coverage-v2 re-freeze ONLY IF the coverage family is
resumed. The binding blocker remains the counter-authority evidence gap — the
falsification re-run still returns PRODUCT_FALSIFIED with n_emitted=0 on all three
V3 questions, so the comparative map-vs-ranked-list half stays VACUOUS. Both
DO-NOT-SERVE orders stand; the Factory Director decides the successor question.
