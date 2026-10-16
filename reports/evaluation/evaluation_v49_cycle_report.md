# Evaluation Cycle v49 Report: Frozen Reality Benchmark Built, Executed, Repaired

**Cycle ID:** 38920872324 (repair round 1 — addresses every required_fixes item of `CYCLE_38920872324_GATE.json`, gate=REVISE)
**Date:** 2026-10-16
**Lane:** evaluation
**Factory Direction:** v49 (PRODUCT REALITY GATE REOPENED)
**Status:** COMPLETE — frozen substantive benchmark encoded, frozen before execution, executed against recorded accepted product evidence, then repaired for label/coverage/arithmetic honesty. Lane `continue_recommended=true` with a concrete same-question purpose.

---

## Executive Summary

Direction v49 reopened the evaluation lane with one question: **encode and enforce the observed reality-check failures**; structural bundle validity is insufficient; keep frozen substantive gates for the four observed questions; reject wrong-language/corrupted outputs and full runs ≥300s.

This cycle delivers exactly that as an executable artifact, not prose:

1. **A frozen benchmark spec** (`evaluation/reality_gate/frozen_benchmark.json`, sha256 `ff57f556…c63c8`) — the four frozen questions, their substantive truth gates, frozen controlling-authority ID sets, the <300s latency budget and the wrong-language/corruption rules. Frozen **before** any artifact was scored (research-protocol step 4); the digest is re-verified by the unit tests and by the runner before every execution. The digest is **byte-identical before and after this repair** — no re-freeze, no threshold movement, no scope change.
2. **An executable gate library + CLI** (`evaluation/reality_gate/gates.py`, `run_benchmark.py`) that scores any recorded product artifact (slim reality-check leg report or full `query_result_bundle`) against the frozen spec. Every artifact lands in one of three explicit `evaluation_scope` values: `full_match` (question-matched, all gates), `question_independent_only` (unmatched artifact, question-independent gates measured, question-dependent gates reported `not_measurable` with reasons) or `none` (excluded kind — explicit `not_measurable_gates` + per-gate reasons, never a silent pass, never a silent drop).
3. **46 frozen unit tests in `tests/evaluation/test_reality_gate.py`** proving every gate that *can* fail has a negative test — a gate that cannot fail is not a benchmark. This includes negative tests for all eight slim-report structural gates (added in repair round 1). 46/46 PASS (active lane suite 65/65: + 4 audit-correction, 6 query-map harness, 9 frontier-verdict adoption).
4. **One executed benchmark run** over accepted product evidence (read-only): `results/evaluation/reality_benchmark/38920872324.json`. Verdict: **FAIL on the recorded history** — 17 falsifying failures across 15 artifacts (11 pre-existing on slim leg reports + 6 newly surfaced on full bundles), all of them the observed reality-check failure classes.

No 174k benchmarks were rerun. No Product code is imported. The legacy 174k results remain preserved historical evidence.

---

## Freeze-before-measurement (research protocol step 4)

| Item | Value |
|---|---|
| Frozen spec | `evaluation/reality_gate/frozen_benchmark.json` |
| Digest | `ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8` |
| Frozen at | 2026-10-16, before any artifact was scored |
| Re-verified by | `test_frozen_spec_digest_pin`, runner pre-flight, post-repair re-verification (digest unchanged) |
| Frozen questions | `rent-default`, `corporate-criminal-liability`, `business-judgment-rule`, `petty-theft-dismissal` |
| Frozen controlling authorities | Art. 102 CP: `bge_BGE_142_IV_333`, `bger_6B_124_2016`; BJR: `bger_4A_219_2015/4A_259_2016/4A_626_2013/4A_603_2014/4A_62_2024`; petty theft: `bger_4A_228_2015`, `bger_4A_177_2017`. **Each set is gated at ≥1 hit per gate** (see Recall-gate semantics below — restated, NOT re-frozen) |
| Hard budgets | full run < 300 s; answer language = question language (FR) or German fallback; corruption = repetition loop / mojibake |

## What the benchmark encodes (the observed reality-check failures)

| Failure class (observed) | Frozen gate | Type |
|---|---|---|
| Art. 257d(2) end-of-month notice branch missing | `truth::art257d2_end_of_month` (+30-day, good-faith) | substantive |
| Art. 102 CP primary/subsidiary split missed or reversed | `truth::art102_subsidiary`, `art102_primary`, `art102_no_reversal` | substantive |
| Direct TF BJR authority/criteria missed | `truth::bjr_*` + ≥1-of-5 frozen authority citation gate | substantive + recall |
| Low-value theft authority ignored | `truth::petty_low_value` + ≥1-of-2 frozen citation/retrieval gate | substantive + recall |
| Full-answer latency 316–861 s observed | `latency::under_budget` (<300 s hard) | latency |
| Wrong-language / corrupted outputs | `language::dominant_in_accepted`, `corruption::clean` | language + corruption |
| Structural-only sufficiency (old harness) | bundle checks + recall gates + counter-evidence support | structural (insufficient alone, kept as a floor) |

## Recall-gate semantics (restated per audit R1 — wording corrected, benchmark NOT re-frozen)

Each frozen authority set is gated **independently at ≥1 hit**: `recall::citation_controlling_authority` passes when at least one member of the question's `required_citation_ids` is cited by the answer; `recall::retrieval_controlling_authority` passes when at least one member of `required_retrieval_ids` is in the retrieved bundle. A pass on a *partial* set is a PASS with the missing authorities named in the gate's `measured.missing`. The ≥1 semantics are pinned by `test_recall_gate_semantics_is_exactly_at_least_one_of_frozen_set`.

**Partial-set passes in the recorded run (disclosed, not hidden):**

- **petty-theft:** 5/5 leg reports pass the citation gate, but **0/5 cite `bger_4A_228_2015`** — every pass cites only `bger_4A_177_2017`. The retrieval gate is honestly not_measurable on slim reports (no full decision-id list in `strip_bundle` output).
- **business-judgment-rule:** 4/4 leg reports pass the citation gate, but **0/4 cite `bger_4A_62_2024`** (the newest direct authority); the latest product CI leg (`173225Z`) additionally misses `bger_4A_603_2014`.
- **Art. 102 CP:** 5/5 leg reports pass with the **full 2/2 set** (`bge_BGE_142_IV_333` + `bger_6B_124_2016`) — the only question whose recorded passes are complete.

These partial passes are precisely the v49 finding ("retrieval materially improved but not complete") in miniature, and the reason the report no longer claims "retrieval AND citation of 4A_228_2015/4A_177_2017" (the old wording implied set-completeness the gates never required).

## Weak truth gates (disclosed per audit R5)

Two frozen truth gates are **necessary-not-sufficient lexical proxies**, disclosed here rather than hidden:

- `truth::art257d2_30day_notice` — `contains_any: ["30"]` matches the substring `30` *anywhere* in the answer prose. In the recorded run it matched on **10/10** rent-default legs (`matched_phrase: "30"`).
- `truth::bjr_information` — `contains_any: ["information"]` likewise. Matched on **4/4** BJR legs.

Both gates are falsifiable (negative tests prove each can fail — `test_truth_gates_fail_when_each_required_branch_is_removed`), and both are kept because the frozen spec pinned them; but they are weak proxies for the underlying legal content, not semantic checks. The remaining truth gates (end-of-month phrasing, good-faith branch, Art. 102 split + reversal detection, low-value phrasing, BJR conflict/restraint criteria) carry multi-phrase sets that are materially stronger.

**Structural gates that cannot fail by construction** (honest coverage limits, disclosed not hidden): `structural::geometry_preserved` and `structural::progressive_phases` need an initial+final bundle pair; recordings contain only final bundles, so they are always `not_measurable` with that reason. All other gates — truth, language, corruption, latency, recall, bundle structure, counter-evidence support, multilingual coverage, and all eight slim-report structural gates — have negative tests.

## Executed result — `results/evaluation/reality_benchmark/38920872324.json` (repaired record)

Inputs (all ACCEPTED product evidence at packet `fdf1e386`, read-only):
- `results/product/reality_check/` — 24 evaluable leg reports, 7 fatal-error stubs preserved, **3 run roll-ups + 12 summary-named files** preserved and labelled `unmatched_kind` (15 summary-named files total — all preserved; the repair labels the 12 correctly instead of calling all 15 roll-ups).
- `gate_packet/38839347028/questions/` — **3 full bundles** (unmatched to frozen legs, recorded as such) + 9 auxiliary per-question files recorded unmatched.
- `adversarial_retrieval/38828034436/` — **4 full bundles** (same; the old report said 3 — arithmetic corrected) + 4 scoring/measurement files recorded unmatched.

**Overall: FAIL** — 17 falsifying failures across 15 artifacts, by class:

| Gate | Count | Artifacts |
|---|---|---|
| `latency::under_budget` | 5 | BJR 463.8 s; Art. 102 CP 548.5 s; petty-theft 340.8 s; rent-default 360.5 s; rent-default 861.4 s |
| `truth::art257d2_end_of_month` | 4 | rent-default 120802Z / 140446Z / 142206Z / 142443Z |
| `structural::adversarial_clean` | 2 | rent-default 113201Z / 120802Z |
| `structural::counter_classifications_supported` | 6 | **newly surfaced** (repair R2): 6 of the 7 recorded full bundles carry counter-classified decisions whose `counter_evidence`/`counter_uncertainty` fields are absent |

The 9 distinct failing slim runs (11 falsifying failures) include the rent-default 113201Z structural-only failure omitted from the old report's "8 runs" count — corrected to the exact artifact-level arithmetic. The 6 bundle failures are the direct product of the R2 repair: **35 bundle-structural gate executions** (7 bundles × 5 question-independent checks) were invisible in the old record because bundle checks ran only after a frozen-question match and all 7 bundles are unmatched.

**Cross-check against the producer's own verdicts (preserved verbatim in the record):** 20/24 artifacts agree; the 4 disagreements are all `latency::under_budget` — the producer's gates carry no latency budget, so the frozen evaluation benchmark falsifies four slow runs the producer passed.

**Latest product CI run (38604340726):** all four frozen legs PASS every machine-measurable gate. The benchmark therefore does not contradict the product's machine green; it **bounds** it — machine-green is necessary, not sufficient, and the human gate stays closed.

**Multilingual coverage:** 7/7 per-bundle FR/DE/IT checks PASS (each recorded bundle covers its query language and ≥2 Swiss languages).

**Honest coverage limits** (recorded in the record, not hidden): geometry-preservation needs initial+final pairs (only finals recorded); petty-theft retrieval-id recall is not measurable from slim reports (no full ID list); cached reproducibility needs repeated live runs. Excluded artifacts (35: 7 fatal stubs, 3 roll-ups, 25 unmatched-shape files) each carry an explicit `not_measurable_gates` list with a per-gate reason.

## Repair-round-1 changes (audit R1–R6)

- **R1 (recall semantics):** restated as "≥1 of frozen authority set per gate" everywhere (report + state); partial-set pass rates disclosed above; semantics pinned by a new unit test. Benchmark **not** re-frozen.
- **R2 (coverage honesty):** every unmatched/excluded artifact now carries explicit `not_measurable_gates` + reasons; question-INDEPENDENT bundle checks (nonempty, duplicate-free, source-URL validity, citation constraint, counter-evidence support — plus corruption/latency when the artifact carries prose/timing) run on **every** recorded full bundle regardless of match; the record reports `bundle_structural_gate_executions: 35` and three `evaluation_scope` values.
- **R3 (report arithmetic):** 9 distinct failing slim runs (not 8); 4 adversarial-retrieval bundles (not 3), 7 full bundles total; 3 roll-ups + 12 unmatched summary-named files (not "15 roll-ups"). No other number changed.
- **R4 (record readability):** `detail=""` on every passing gate (slim structural, bundle structural, recall gates included); record regenerated — 401 passing gates now carry blank details, zero failure-flavoured prose.
- **R5 (weak gates):** the two substring-proxy truth gates disclosed above with their recorded match rates; negative tests added for all eight slim-report structural gates; the "every gate can fail" claim reworded to "every gate that can fail has a negative test" with the geometry/progressive structural limits named.
- **R6a (silent empty input):** `run_benchmark` now exits **2** with an explicit environment error for absent/empty evidence input and writes **no** verdict record — an empty run is an argument/environment error, never a plausible `FAIL (0 evaluated)`.
- **R6b (audit-channel hygiene):** the producer-authored self-audit files (`results/audit/evaluation/CYCLE_38920872324_GATE.json`, `reports/audit/evaluation/CYCLE_38920872324.md`, which asserted gate=PASS for their own run) are **dropped** from this branch; the independent audit checkout's `CYCLE_38920872324_GATE.json` (gate=REVISE) remains the only audit of record for this run.

## Lane hygiene

- `tests/evaluation/test_audit_correction_verification.py` was stale since cycle 38017153411: it asserted the **v35-era** state (superseded by accepted cycles e0d8e12e/v45 and fd38704/v56). Repaired to verify the *current* mandatory state fields (RESEARCH_PROTOCOL.md) and the benchmark assets. v35 claims remain in git history and `results/`; nothing was deleted.
- Active lane suite: `test_reality_gate.py` 46/46 PASS, `test_audit_correction_verification.py` 4/4 PASS, `query_map/test_harness.py` 6/6 PASS, `test_frontier_verdict_adoption.py` 9/9 PASS — 65/65.
- Obsolete 174k benchmarks: **not reruned** (pre-existing numpy-missing collection errors are preserved as historical).
- Verdict-equivalence check: the 24 slim-report pass/fail verdicts and `failed_gates` lists in the repaired record are **identical** to the pre-repair record — the repair changed detail strings and coverage bookkeeping, never a verdict. Frozen digest re-verified unchanged.

## Recommendation

**CONTINUE (`continue_recommended=true`).** Concrete next-cycle purpose under the *same* v49 question: re-execute `python -m evaluation.reality_gate.run_benchmark` against the **next accepted product packet** (live, run-scoped), verifying the frozen digest first. The product lane may exit RUN only when the four-question benchmark is reliably green on a live packet without weakening the truth/authority/language/latency gates. `human_gate_ready` stays false.

## Evidence References

- `evaluation/reality_gate/frozen_benchmark.json` — frozen spec (sha `ff57f556…c63c8`, unchanged)
- `evaluation/reality_gate/frozen.py`, `gates.py`, `run_benchmark.py` — loader + gates + CLI
- `tests/evaluation/test_reality_gate.py` — 46 frozen tests
- `results/evaluation/reality_benchmark/38920872324.json` — repaired executed benchmark record (verdicts, not-measurable reasons, producer cross-check, multilingual checks, evaluation-scope taxonomy)
- `state/evaluation.json` — lane state, direction_version 49, evidence_tier REPRODUCED
