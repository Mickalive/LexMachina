# Evaluation Cycle v49 Report: Frozen Reality Benchmark Built and Executed

**Cycle ID:** 38920872324
**Date:** 2026-10-16
**Lane:** evaluation
**Factory Direction:** v49 (PRODUCT REALITY GATE REOPENED)
**Status:** COMPLETE — frozen substantive benchmark encoded, frozen before execution, executed against recorded accepted product evidence. Lane `continue_recommended=true` with a concrete same-question purpose.

---

## Executive Summary

Direction v49 reopened the evaluation lane with one question: **encode and enforce the observed reality-check failures**; structural bundle validity is insufficient; keep frozen substantive gates for the four observed questions; reject wrong-language/corrupted outputs and full runs ≥300s.

This cycle delivers exactly that as an executable artifact, not prose:

1. **A frozen benchmark spec** (`evaluation/reality_gate/frozen_benchmark.json`, sha256 `ff57f556…c63c8`) — the four frozen questions, their substantive truth gates, frozen controlling-authority ID sets, the <300s latency budget and the wrong-language/corruption rules. Frozen **before** any artifact was scored (research-protocol step 4); the digest is re-verified by the unit tests and by the runner before every execution, so the lane under test cannot weaken its own benchmark.
2. **An executable gate library + CLI** (`evaluation/reality_gate/gates.py`, `run_benchmark.py`) that scores any recorded product artifact (slim reality-check leg report or full `query_result_bundle`) against the frozen spec, preserving `not_measurable` coverage honestly instead of silently passing.
3. **30 frozen unit tests** (`tests/evaluation/test_reality_gate.py`) proving every gate *can fail* — a gate that cannot fail is not a benchmark. 30/30 PASS.
4. **One executed benchmark run** over accepted product evidence (read-only): `results/evaluation/reality_benchmark/38920872324.json`. Verdict: **FAIL on the recorded history** — 11 falsifying failures preserved, all of them the observed reality-check failure classes.

No 174k benchmarks were rerun. No Product code is imported. The legacy 174k results remain preserved historical evidence.

---

## Freeze-before-measurement (research protocol step 4)

| Item | Value |
|---|---|
| Frozen spec | `evaluation/reality_gate/frozen_benchmark.json` |
| Digest | `ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8` |
| Frozen at | 2026-10-16, before any artifact was scored |
| Re-verified by | `test_frozen_spec_digest_pin`, runner pre-flight |
| Frozen questions | `rent-default`, `corporate-criminal-liability`, `business-judgment-rule`, `petty-theft-dismissal` |
| Frozen controlling authorities | Art. 102 CP: `bge_BGE_142_IV_333`, `bger_6B_124_2016`; BJR: `bger_4A_219_2015/4A_259_2016/4A_626_2013/4A_603_2014/4A_62_2024`; petty theft: `bger_4A_228_2015`, `bger_4A_177_2017` (retrieval **and** citation) |
| Hard budgets | full run < 300 s; answer language = question language (FR) or German fallback; corruption = repetition loop / mojibake |

## What the benchmark encodes (the observed reality-check failures)

| Failure class (observed) | Frozen gate | Type |
|---|---|---|
| Art. 257d(2) end-of-month notice branch missing | `truth::art257d2_end_of_month` (+30-day, good-faith) | substantive |
| Art. 102 CP primary/subsidiary split missed or reversed | `truth::art102_subsidiary`, `art102_primary`, `art102_no_reversal` | substantive |
| Direct TF BJR authority/criteria missed | `truth::bjr_*` + 5 frozen authority citations | substantive + retrieval |
| Low-value theft authority ignored | `truth::petty_low_value` + retrieval∩citation of `4A_228_2015`/`4A_177_2017` | substantive + retrieval |
| Full-answer latency 316–469 s observed | `latency::under_budget` (<300 s hard) | latency |
| Wrong-language / corrupted outputs | `language::dominant_in_accepted`, `corruption::clean` | language + corruption |
| Structural-only sufficiency (old harness) | bundle checks + recall gates + counter-evidence support | structural (insufficient alone, kept as a floor) |

## Executed result — `results/evaluation/reality_benchmark/38920872324.json`

Inputs (all ACCEPTED product evidence at packet `fdf1e386`, read-only):
- `results/product/reality_check/` — 24 evaluable leg reports (+ 7 fatal-error stubs preserved, 15 roll-ups preserved)
- `gate_packet/38839347028/questions/` — 3 full bundles (unmatched to frozen legs, recorded as such)
- `adversarial_retrieval/38828034436/` — 3 full bundles (same)

**Overall: FAIL** — 11 falsifying failures across 8 recorded runs, by class:

| Gate | Count | Runs |
|---|---|---|
| `latency::under_budget` | 5 | BJR 463.8 s; Art. 102 CP 548.5 s; petty-theft 340.8 s; rent-default 360.5 s; rent-default 861.4 s |
| `truth::art257d2_end_of_month` | 4 | rent-default 120802Z / 140446Z / 142206Z / 142443Z |
| `structural::adversarial_clean` | 2 | rent-default 113201Z / 120802Z |

**Cross-check against the producer's own verdicts (preserved verbatim in the record):** 20/24 artifacts agree; the 4 disagreements are all `latency::under_budget` — the producer's gates carry no latency budget, so the frozen evaluation benchmark falsifies four slow runs the producer passed. This is precisely the v49 finding ("machine green, human review invalidated") in miniature, and it is why the evaluation lane — not the producer — owns this gate.

**Latest product CI run (38604340726):** all four frozen legs PASS every machine-measurable gate. The benchmark therefore does not contradict the product's machine green; it **bounds** it — machine-green is necessary, not sufficient, and the human gate stays closed.

**Multilingual coverage:** 7/7 per-bundle FR/DE/IT checks PASS (each recorded bundle covers its query language and ≥2 Swiss languages).

**Honest coverage limits** (recorded, not hidden): geometry-preservation needs initial+final pairs (only finals recorded); petty-theft retrieval-id recall is not measurable from slim reports (no full ID list); cached reproducibility needs repeated live runs. The 30 unit tests cover all three logics.

## Lane hygiene

- `tests/evaluation/test_audit_correction_verification.py` was stale since cycle 38017153411: it asserted the **v35-era** state (superseded by accepted cycles e0d8e12e/v45 and fd38704/v56). Repaired to verify the *current* mandatory state fields (RESEARCH_PROTOCOL.md) and the benchmark assets. v35 claims remain in git history and `results/`; nothing was deleted.
- Active lane suite now: `test_reality_gate.py` 30/30 PASS, `test_audit_correction_verification.py` PASS, `query_map/test_harness.py` PASS, `test_frontier_verdict_adoption.py` PASS.
- Obsolete 174k benchmarks: **not reruned** (pre-existing numpy-missing collection errors are preserved as historical).

## Recommendation

**CONTINUE (`continue_recommended=true`).** Concrete next-cycle purpose under the *same* v49 question: re-execute `python -m evaluation.reality_gate.run_benchmark` against the **next accepted product packet** (live, run-scoped), verifying the frozen digest first. The product lane may exit RUN only when the four-question benchmark is reliably green on a live packet without weakening the truth/authority/language/latency gates. `human_gate_ready` stays false.

## Evidence References

- `evaluation/reality_gate/frozen_benchmark.json` — frozen spec (sha `ff57f556…c63c8`)
- `evaluation/reality_gate/frozen.py`, `gates.py`, `run_benchmark.py` — loader + gates + CLI
- `tests/evaluation/test_reality_gate.py` — 30 frozen tests
- `results/evaluation/reality_benchmark/38920872324.json` — executed benchmark record (verdicts, not-measurable list, producer cross-check, multilingual checks)
- `state/evaluation.json` — lane state, direction_version 49, evidence_tier REPRODUCED
