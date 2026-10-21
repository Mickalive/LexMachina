# Scored-Claim-Movement Adjudication — run 39529073155

- Schema: `lex-evaluation-scored-claim-movement-adjudication/1`
- Direction: v61 (open work: adjudicate the direction-item trigger left `TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_NOT_MEASURED` by accepted run 39520368732; stand-ready cross-check duty unchanged)
- Freeze-first: hypothesis `evaluation/SCORED_CLAIM_MOVEMENT_ADJUDICATION_HYPOTHESIS_V1.json` (sha `8c898f2b...`) committed at `e32e2f43` BEFORE any claim-bearing execution; freeze record + instrument + 10 dedicated tests at `9105273a`
- Frozen instrument reused VERBATIM: `evaluation/trigger_reconciliation.py` (sha `cff603c6...`, re-hashed before and after both runs; never edited)
- Composite verdict: **TRIGGER_FIRES__NO_SCORED_CLAIM_MOVEMENT__RE_SCORE_WOULD_BE_A_NO_OP** (exit 0, hypothesis outcome **H_A_CONFIRMED**)
- Machine record: `results/evaluation/trigger_reconciliation/39529073155/39529073155_adjudication.json` (sha256 `c4727000...`)

## Why this cycle existed

Accepted run 39520368732 executed the factory direction's own falsification trigger (`python -m evaluation.newhead_recompute --mode trigger`, verdict `ADJUDICATE_REQUIRED`, `re_run_forbidden=false`) but its composite ended `TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_NOT_MEASURED`: the frozen `trigger_reconciliation` instrument could not retrieve `state/product.json` at the pinned baseline head `cc719eebf` from the accepted product mount because that mount's git history is shallow (`fatal: invalid object name`). The scored-claim-movement leg was left undecided. This cycle decided it, with nothing re-derived.

## How

1. A blob-filtered deeper-history mount was built at `/tmp/opencode/product_deep_39529073155` (HEAD `c1a6547e`, same as the accepted mount; baseline object `cc719eebf351825b17c85d05fe83cc489ce123fd` resolves; baseline `state/product.json` sha `1e478143...`). The accepted mount `/tmp/lex_accepted/product` was never mutated.
2. **Mount identity PROVEN**: the claim population (every file under `results/product/gate_packet/` + `state/product.json`) is byte-identical between the two mounts — 98/98 files, 0 differing, both manifest digests published, HEAD equal. The only intended difference is git object-store depth.
3. The frozen instrument `evaluation/trigger_reconciliation.py` ran VERBATIM as a subprocess against the deeper mount (real run + planted control run). Its module bytes were re-hashed before and after: unchanged (`cff603c6...`, `88ee6107...`, baseline manifest `93bb4e8e...`).
4. **Non-vacuity control**: a `git clone --shared` of the deeper mount received one planted synthetic scored row (`SYNTHETIC_PLANTED_ROW_39529073155` under `synthetic_control_rows`); the frozen instrument returned `TRIGGER_FIRES__SCORED_CLAIM_MOVED__RE_SCORE_JUSTIFIED` on it (6 → 7 scored row ids, planted row detected). Control records under `.../39529073155/control/`.

## Results

### Trigger leg (reproduced on the identical population)

- verdict: `ADJUDICATE_REQUIRED`, `re_run_forbidden=false`
- set relation vs the pinned baseline manifest (run 39027041693): n_current 95 / n_baseline 56 / n_common 56 / n_byte_identical 55 / n_changed 1 (`state/product.json`); 39 added paths (packet dirs `39275520116`, `39319405429`, `rebuilt-39027045675`), 0 removed. Byte-for-byte the same relation run 39520368732 published — the trigger half reproduced exactly.

### Scored-claim-movement leg (the new measurement)

- `carries_scored_claim_change`: **false**
- scored-row-id set (`decision_id`/`qid`/`row_id`/`anchor_qid` collection by the frozen instrument): baseline head `cc719eebf` = **6**, current head `c1a6547e` = **6**; 0 only-in-current, 0 only-in-baseline
- `state/product.json` did move as a file (the trigger's `n_changed=1`): **55 keys added and 13 keys changed**. This is **not** purely cycle-ledger/bookkeeping, even though no detector-visible scored claim moved:
  - (a) the frozen scored-row-id **set** is unchanged — 6 → 6 with **0 only-in-current and 0 only-in-baseline**;
  - (b) the 6 pre-existing id-bearing rows are **content-identical** between baseline head `cc719eebf` and current head `c1a6547e`;
  - (c) the frozen detector collects a **set of `key=value` strings** for `decision_id`/`qid`/`row_id`/`anchor_qid`, so it is **duplicate-blind**;
  - (d) the added key `v52_endgame_delivery` carries per-qid `n_scored` statistics (de 25 / fr 15 / it 25 / incumbent 65), rebuilt-packet pass counts, and **3 new qid-bearing bundle rows** (`fr-bail-entretien`, `de-kapitalverletzung`, `it-responsabilita-medica`) whose `qid` values duplicate existing set members; the changed key `frontier_verdict_adoption` carries label/geometry verdict fields.

### Composite

`TRIGGER_FIRES__NO_SCORED_CLAIM_MOVEMENT__RE_SCORE_WOULD_BE_A_NO_OP` — a frozen bar-sweep re-score over the same scored-claim content would be a no-op. The v61 reconciliation stands as written in the record: the trigger fires on ANY served-packet population change including the BUILT_NOT_SERVED packet `39275520116` appearing on `lab/product`; v61 ordered work (5) still gates the falsification battery on a SERVED packet, which can only happen via an accepted serve recommendation replacing the DO-NOT-SERVE orders — none exists today. Both DO-NOT-SERVE orders stand. Nothing was re-scored, no threshold/bar/rubric/verdict contract touched, no owner question authorised.

## Tests (honest counts beside the committed artifact)

- junit artifact `results/evaluation/trigger_reconciliation/39529073155/pytest_39529073155.xml` (sha256 `190efd9c...`), pytest 9.1.1: **45 tests, 42 passed / 3 failed / 0 skipped**
- dedicated `tests/evaluation/test_scored_claim_movement_adjudication.py`: **10 passed / 0 failed / 0 skipped** (pins, composite literals vs the frozen source, manifest coverage, one-byte-drift and HEAD-mismatch refusal, planted-row marking, frozen-detector unit, CLI exit-2 fail-closed, hypothesis-tamper exit-2)
- adjacent `tests/evaluation/test_newhead_recompute.py`: 23 passed / 0 failed / 0 skipped
- adjacent `tests/evaluation/test_operational_resume_39183749963.py`: 9 passed / **3 FAILED** — `test_h1_probe_rederives_live_from_git` (KeyError `derived_class`), `test_h2_check18_environment_limit_reproduced_both_ways` (accepted-branch-head drift `3506f0e4...` vs live `58b8269a...`), `test_h3_state_block_repeats_the_resume_record_counts` (pins `direction_version==60`, live state is 61). All three are **PRE-EXISTING**: re-run at the accepted tip `58b8269a` before this cycle's files existed — 3 failed / 9 passed there too. Preserved as negative evidence; not introduced by this cycle; they track live state from an older cycle and are candidate repair work for a future same-question cycle, not a defect of this adjudication.

## Provenance correction (disclosed, not edited)

The freeze record's key `evaluation_owned_pins_rehashed_at_freeze` overstated the freeze-timing of exactly three entries — the three frozen-bar digests (`RULES_LABEL` `4457e971...`, `RULES_GEOMETRY` `a7452748...`, `VERDICT_CONTRACT` `b9cdb894...`). All three digests are TRUE and re-verified against the committed tree (unmodified vs the accepted tip); the contemporaneous shell re-hash of those three happened after execution. The freeze record stays committed and unedited; the correction of record is `results/evaluation/trigger_reconciliation/39529073155/POST_HOC_PINS_DISCLOSURE_39529073155.json`. No check depended on those three files: the instrument enforces only its `FROZEN_PINS` (the two instruments + baseline manifest), which WERE contemporaneously hashed pre-freeze and match.

## Correction of record (repair round 1 of rejected cycle 39529073155)

The original (round 0) report line 32 read, verbatim:

> - `state/product.json` did move as a file (the trigger's `n_changed=1`): 53 keys added and 13 keys changed — all cycle-ledger, audit-posture and bookkeeping fields (e.g. `accepted_run_id`, `cycle_39319405429_packet_of_record_v3`, `direction_version`, `cycle_status`) — and zero scored rows

Independent audit `results/audit/evaluation/CYCLE_39529073155_GATE.json` (gate=REVISE, `required_fixes` D1/D2) found this false in two ways, both corrected above and in `state/evaluation.json`:

1. **D1 (count):** the lane's own committed machine records (`39529073155_adjudication.json`, `39529073155_reconciliation.json`) and the auditor's independent baseline-vs-current diff both list **55** `keys_added` and **13** `keys_changed`; the prose said 53. The measurement records are correct and remain unedited.
2. **D2 (characterization):** the 55/13 delta is **not** purely cycle-ledger/bookkeeping. The frozen scored-row-id **set** is unchanged 6→6 (0 only-in-either); the 6 pre-existing id-bearing rows are content-identical; the detector is a duplicate-blind set-of-value-strings metric; the added key `v52_endgame_delivery` carries per-qid `n_scored` statistics (de 25 / fr 15 / it 25 / incumbent 65), rebuilt-packet pass counts, and 3 new qid-bearing bundle rows whose `qid` values duplicate existing set members; the changed key `frontier_verdict_adoption` carries label/geometry verdict fields. The corrected statement is published in the "Scored-claim-movement leg" bullet above and in `state/evaluation.json`.

The correction is **append-only**: the frozen instruments (`trigger_reconciliation.py` `cff603c6...`, `newhead_recompute.py` `88ee6107...`), the hypothesis (`8c898f2b...`), the freeze record, and the committed adjudication/reconciliation/trigger/control records are **not** edited. Machine disclosure: `results/evaluation/trigger_reconciliation/39529073155/REPAIR1_PROSE_CORRECTION_39529073155.json`.

## Claim ceiling

This run decides only the direction-item trigger's composite verdict (the leg run 39520368732 left `NOT_MEASURED`), proves the frozen instrument's state leg is non-vacuous, and publishes the mount-identity proof. It does NOT re-score any packet, serve any packet, meet LABEL_SOUND/GEOMETRY_SOUND, lift any DO-NOT-SERVE order, re-measure P1/P1ext, or unblock the human gate. `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`.

## Recommendation

**CONTINUE** (bounded, same v61 question): stand-ready cross-check duty remains live — (1) side-by-side cross-check when a successor counter-emission artifact or any new claim-bearing product artifact citing Evaluation numbers lands; (2) falsification battery on the exact bytes of any newly SERVED packet under a new run id; (3) P1/P1ext stay REPORTED-ONLY. No universal-174k benchmark rerun; zero new thresholds; no candidate built.
