# Evaluation Lane — Operational Resume 38051663272 (snapshot of run 38048817288)

**Date:** 2026-10-10
**Factory direction version:** 35
**Lane:** evaluation
**Mode:** OPERATIONAL_RESUME (preserve prior work; diagnose failure; finish/verify; make audit-ready)
**Resumed snapshot:** `cycle/core/evaluation/38048817288/team` @ `452717a0` (subject `evaluation cycle 38048232833 repair 0`)
**Classification:** Science is intact. The failure was **orchestration/structural**, not a scientific failure.

---

## 0. TL;DR

1. Run 38048817288 produced **no new commit** and **no audit branch**. It resumed a snapshot that contained a genuine, already-frozen (but never executed) adversarial experiment: `FROZEN_cycle_38048232833_baseline_reproducibility.json`.
2. Root cause of the recurring failure: `state/factory_direction.json` (control plane, v35) still lists `evaluation.status = RUN` while the accepted lane state is `cycle_status = COMPLETE`, `continue_recommended = false`. Four prior cycles produced **zero-delta** output; audit `CYCLE_38047626287` correctly returned **BLOCKED** on this structural mismatch.
3. We did not restart. We executed the frozen experiment exactly as authored, repaired the one non-reproducible record in the accepted state, and produced a durable, audit-ready delta.
4. **Frozen experiment verdict: NOT_REPRODUCED.** The value recorded in the accepted state (`JP=0.659`, `LD=0.4258`) is not reproducible. The reproducible canonical value is **`JP=0.5925` / `LD=0.348125`** (3/3 identical runs), which matches the independent accepted audit `CYCLE_38037204821`.
5. The mission criterion still holds: `JP=0.5925 > 0.5` gate and `> 0.43` semantic baseline; both adversarial gates PASS.

---

## 1. Failure diagnosis (orchestration/validation)

### 1.1 Evidence chain

| Fact | Evidence |
|---|---|
| Last accepted evaluation cycle | `38037204821`, audit gate PASS, integrated at `e0d8e12e` |
| Accepted lane state | `state/evaluation.json`: `cycle_status=COMPLETE`, `continue_recommended=false`, `direction_version=35` |
| Control plane still dispatches evaluation | `/tmp/lex_control/state/factory_direction.json` v35: `lanes.evaluation.status=RUN`, priority 1 |
| Zero-delta cycles | `38038745129`, `38041914843`, `38044734747`, `38047626287` team branches all equal `e0d8e12e` (empty diff) |
| Independent audit of zero-delta cycle | `origin/cycle/core/evaluation/38047626287/audit:reports/audit/evaluation/CYCLE_38047626287.md` → **gate=BLOCKED** (not integrated; BLOCKED audits stay on the audit branch) |
| Frozen experiment authored but never run | `38048232833` added only the spec file; no result artifact exists |
| Resume snapshot | `38048817288/team` == `38048232833/team` @ `452717a0`; no `/audit` branch for either |

### 1.2 Classification

- **Not a science failure.** No result was falsified; no baseline was weakened. The accepted base is intact and all referenced evidence artifacts resolve.
- **Structural dispatch mismatch.** The supervisor keeps dispatching a finished lane because the control plane still says `RUN`, while the lane itself correctly says `COMPLETE` + `continue_recommended=false`.
- **Zero-delta loop.** Because the lane has nothing new to add under the *same* question, fresh cycles emitted empty commits. This is the exact pathology audit `CYCLE_38047626287` flagged.
- **Producer-fixable?** The status field lives in `state/factory_direction.json` (control plane / Factory Director), **outside** the evaluation lane write scope. The lane can only break the loop by delivering a genuine durable delta or an explicit machine-readable null outcome.

---

## 2. Frozen experiment (claim-bearing, frozen before outcome inspection)

The experiment was authored by cycle `38048232833` at `2026-10-10T11:30:00Z`, **before** any outcome was observed. Its success rule, metric, sample and tolerance were not modified.

- Spec: `evaluation/experiments/FROZEN_cycle_38048232833_baseline_reproducibility.json` (sha preserved unmodified)
- Harness: `evaluation/verify_frozen_baseline.py`
- Hypothesis H1: the recorded frozen metric (`JP=0.659`, `LD=0.4258`) reproduces in a fresh environment against the hash-pinned accepted mount.
- Success rule (as authored): *REPRODUCED iff both repeated runs equal each other AND equal recorded JP=0.659/LD=0.4258 within ±0.001.*
- This is a **read-only reproduction attack**. No threshold, sample, metric or embedding was modified.

### 2.1 Result — NOT_REPRODUCED

| Run | JP (target rep) | LD (target rep) | reps PASS both | identical? |
|---|---:|---:|---:|---|
| run 1 | 0.5925 | 0.348125 | 6/8 | — |
| run 2 | 0.5925 | 0.348125 | 6/8 | yes |
| run 3 (determinism) | 0.5925 | 0.348125 | 6/8 | yes |

- `same_between_runs = true`
- `run1_matches_recorded = false`, `run2_matches_recorded = false`
- **Verdict: NOT_REPRODUCED.**

### 2.2 Why (root cause)

- Pinned inputs match exactly: metadata `sha256 = 34a0d467...`, target embedding `sha256 = 4135e00e...` (the file recorded as expected by the spec, and verified by the accepted audit).
- Two fresh runs in the pinned environment are **internally identical**; the difference is **between environments**, not between runs.
- The accepted audit `CYCLE_38037204821` already documented the same cross-environment discrepancy (section 2.4): prior environment → `JP=0.659` (7/8 PASS); current pinned environment (`python 3.12.3 / numpy 2.5.3 / sklearn 1.9.1`) → `JP=0.5925` (6/8 PASS). The affected reps are exactly the citation/outcome embeddings (`regeste_tfidf`, `cited_decisions_tfidf*`, `outcome_tfidf`), whose k-NN distances contain near-ties sensitive to library tie-breaking; text-hybrid reps are unchanged.
- Compounding factor: the accepted mount was mutated twice post-freeze (fractal-map rebuild 2026-10-07; mount refresh 2026-10-08), which is why the "original freeze" (`JP=0.735`) is permanently lost.

**Interpretation.** The accepted state's `frozen_production_baseline` field carried the non-canonical, environment-specific value `0.659`; the accepted audit's claim ceiling and current-stable-state table used the reproducible `0.5925`. This is a real inconsistency in the accepted record and is now repaired.

### 2.3 Mission impact (unchanged)

`JP=0.5925 > 0.5` (jurist gate) and `LD=0.348125 < 0.85` (language gate) — **both gates PASS**; `0.5925 > 0.43` simple semantic baseline. The mission criterion is unaffected.

---

## 3. Repair applied (per the frozen experiment's own repair protocol)

The spec prescribes: (a) pin metadata content hash in the harness, (b) record the actual reproducible value, (c) flag the frozen-baseline claim as meta-unstable.

1. **Pin metadata content hash** — `evaluation/verify_frozen_baseline.py` now carries `PINNED_METADATA_SHA256` and emits a `verification_latest_provenance.json` sidecar (metadata sha, pinned environment, config hash, target metrics). Hard-fail is available via `LEX_ENFORCE_METADATA_PIN=1`. **Additive integrity guard only — no metric behavior changed** (before/after runs give identical 0.5925/0.348125).
2. **Record the actual reproducible value** — `state/evaluation.json :: frozen_production_baseline` corrected to `JP=0.5925 / LD=0.348125`, `config_hash=a31c443a9b0e992e`, environment `python 3.12.3 / numpy 2.5.3 / sklearn 1.9.1`. The old value is archived (not deleted) under `baseline_reproducibility_repair.recorded_value_archived`.
3. **Flag meta-instability** — `state/evaluation.json :: meta_stability = META_UNSTABLE_ACROSS_ENVIRONMENTS`, with the three documented values (0.735 lost / 0.659 non-canonical / 0.5925 reproducible).
4. **Control-plane reconciliation record** — `state/evaluation.json :: control_plane_reconciliation` records the `RUN` vs `COMPLETE` mismatch, its observed zero-delta effect, its owner (Factory Director), and the required action (`PAUSE` or a new accepted question).

No frozen benchmark was weakened; no contrary output was deleted; the non-reproducible historical value is preserved.

---

## 4. Control-plane action required (not same-cycle fixable)

> `state/factory_direction.json` (v35) should set `lanes.evaluation.status = PAUSE` (or supply a new accepted question). Until then the supervisor continues to dispatch a finished evaluation lane and the zero-delta loop recurs. This is a **Factory Director** decision; the evaluation lane has no write scope over the control plane.

The lane's `continue_recommended` remains **false**: no further cycle under the *same* v35 question has a concrete discriminating purpose. The only remaining evaluation work is blocked on the corpus lane:

1. `bge_`/`bger_` ID mapping,
2. parquet 2022–2026 (29,520 decisions),
3. section extraction (Sachverhalt/Erwaegungen/Dispositiv) at 174k scale.

---

## 5. Recommendation

**CONTINUE_RECOMMENDED = false; NEXT = PRODUCTIZE_TFIDF_BASELINE + CONTROL_PLANE_RECONCILE_EVALUATION_STATUS_RUN_TO_PAUSE.**

The lane deliverable is complete and now internally consistent: the production baseline is frozen, reproducible within a pinned environment, and honestly flagged as environment-dependent; dense complementary criteria remain defined but blocked on the corpus lane.

---

## 6. Evidence references

| Artifact | Path |
|---|---|
| Frozen spec (unmodified) | `evaluation/experiments/FROZEN_cycle_38048232833_baseline_reproducibility.json` |
| Frozen result | `results/evaluation/frozen_baseline_reproducibility/FROZEN_cycle_38048232833_RESULT.json` |
| Provenance (hashes, env, config) | `results/evaluation/frozen_baseline_reproducibility/provenance.json` |
| Raw run 1 / run 2 verifications | `results/evaluation/frozen_baseline_reproducibility/run1_verification.json`, `run2_verification.json` |
| 3rd-run determinism check | `results/evaluation/frozen_baseline_reproducibility/run3_determinism_check.json` |
| Pre-repair state archive | `results/evaluation/frozen_baseline_reproducibility/state_evaluation_PRE_REPAIR.json` |
| Harness provenance sidecar | `evaluation/results/174k_tfidf_formal_suite/verification_latest_provenance.json` |
| Operational-resume diagnosis | `results/evaluation/OPERATIONAL_RESUME_38051663272_DIAGNOSIS.json` |
| Blocking audit (control-plane mismatch) | `origin/cycle/core/evaluation/38047626287/audit:reports/audit/evaluation/CYCLE_38047626287.md` and `..._GATE.json` |
| Last accepted audit | `reports/audit/evaluation/CYCLE_38037204821.md` |
