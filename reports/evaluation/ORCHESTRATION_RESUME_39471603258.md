# Evaluation Lane — Operational Resume — Run 39471603258

- **Lane:** evaluation
- **Direction version:** 61 (`state/factory_direction.json`, lane question `lanes.evaluation.question`)
- **GitHub run:** 39471603258 (workflow_dispatch, `Core evaluation dirV61 repair0`)
- **Resumed from:** persisted producer snapshot of run **39470495546** (`cycle/core/evaluation/39470495546/team` @ `01ebdab8`)
- **Accepted base at resume:** `lab/evaluation` @ `cbda7853` ("accept evaluation cycle 39457963802")
- **Date:** 2026-10-20
- **Instrument:** `evaluation/orchestration_resume_39471603258.py`
- **Evidence tier:** EXPLORARY (this cycle is PROPOSED pending independent audit)
- **Continue recommended:** true (bounded, same question)

---

## 1. What this cycle does

Run 39470495546 produced a producer snapshot that never reached an independent
audit. This cycle (a) names the exact orchestration/validation failure from the
committed tree and the workflow source, (b) verifies that the lane's
claim-bearing deliverable — the mapping-free retrieval / counter-authority
falsifier on the **packet-of-record V3** (`39319405429`) — still reproduces from
the committed tree and the accepted product mount, and (c) returns the snapshot
to an in-scope, **audit-ready** state without deleting valid completed work and
without editing any frozen bar.

## 2. Diagnosis — the orchestration/validation failure

**Classification: `PRODUCER_AUTHORED_AUDIT_PLACEMENT_OUT_OF_LANE_SCOPE`.**

The 39470495546 producer wrote two files into the **independent auditor's
protected namespace**:

| file | git blob oid | sha256 |
|---|---|---|
| `results/audit/evaluation/CYCLE_39470495546_GATE.json` | `b5e446c6574fd2a39300b518c6ef34ddbf2cc5de` | `8837c52ada748adfadcd0585a3b266b73f67ba52214742a5d638e119cd167af1` |
| `reports/audit/evaluation/CYCLE_39470495546.md` | `6ae419f83b5c367aae4490f5df4d60a53afb2c34` | `063fdef18f10fd60c47c76b1813594e42f8d4ca327bf7a9f2d4a8d38f68d4992` |

These are the **only** files in the resumed snapshot's tree that are (i) new
relative to the accepted base `cbda7853` and (ii) inside `results/audit/` or
`reports/audit/`:

```
$ comm -23 <(git ls-files results/audit reports/audit | sort) \
            <(git ls-tree -r --name-only cbda7853 -- results/audit reports/audit | sort)
reports/audit/evaluation/CYCLE_39470495546.md
results/audit/evaluation/CYCLE_39470495546_GATE.json
```

The core-lane team job's **"Enforce lane write scope"** step
(`.github/workflows/core-lane.yml:123-144`) permits only:

```
evaluation/*  tests/evaluation/*  results/evaluation/*
reports/evaluation/*  state/evaluation.json  data/evaluation/*
```

Neither offending path matches any permitted pattern. The guard therefore exits
`3`; the team job fails; the **audit** job is skipped
(`needs: team`, `if: needs.team.result == 'success'`, `core-lane.yml:163-165`);
**integrate** is skipped. Because **"Persist team snapshot"** is guarded by
`if: always()` (`core-lane.yml:146-147`), the out-of-scope writes are
force-pushed anyway, and the lane re-dispatches forever with no independent gate
ever produced.

**This is not** a verdict, a product defect, an audit finding, a human-gate
problem, or an evidence/claim-path failure. It is the "producer-authored audit
placement copy" pathology recorded in factory-wide requirements 15 and 35: a
lane must not write its own independent-audit output.

**Contributing defect.** The 39470495546 audit report claims a durable delta
(the 39462322100 artifacts) that it did not itself create, and its gate file is
placed in the auditor's namespace rather than the lane namespace.

**Prior unaudited measurement.** The measurement this cycle was chartered to
audit — run **39462322100** (`team` @ `61ecbc61`, record
`results/evaluation/counter_authority_surface_falsifier/39462322100.json`) — has
**no audit branch** on origin either, so it was never independently audited
before this cycle.

**Machine record:** `results/evaluation/orchestration_resume_39471603258/39471603258_diagnosis.json`
(schema `lex-evaluation-orchestration-failure-diagnosis/1`).

## 3. Verification — the lane deliverable reproduces

The accepted instrument `evaluation/counter_authority_surface_falsifier.py`
(byte-pinned `0d0c6827…`) was re-run on the accepted product mount
(`/tmp/lex_accepted/product` @ `f463a817`) to a **scratch** path and compared
field-by-field with the committed record `39462322100.json`:

| field | committed | fresh replay | match |
|---|---|---|---|
| verdict | `PRODUCT_FALSIFIED` | `PRODUCT_FALSIFIED` | ✅ |
| exit_code | 1 | 1 | ✅ |
| n_gates | 18 | 18 | ✅ |
| n_passed / n_failed / n_reported | 11 / 4 / 3 | 11 / 4 / 3 | ✅ |
| failed_gates | 4 named gates | same 4 gates | ✅ |
| input_drift | `[]` | `[]` | ✅ |
| non_vacuity_all_hold | true | true | ✅ |
| admissibility n_pairs_admissible | 1 | 1 | ✅ |

The packet-of-record V3's counter-authority surface is **empty on all three
served questions** (`de-kapitalverletzung`, `fr-bail-entretien`,
`it-responsabilita-medica`), and the single admissible slug→question pair
(`rent-default` → `fr-bail-entretien`) has known counter-authority recall
**0/9**. The deliverable therefore reproduces exactly.

**Tests:** `tests/evaluation/test_counter_authority_surface_falsifier.py`
**12 passed / 0 failed / 0 skipped**; adjacent regression
(`test_mapping_free_recall_falsifier`, `test_counter_emission_crosscheck`,
`test_minimal_ca_benchmark`, `test_benchmark_retrieval_counter_authority`)
**68 passed / 172 subtests**.

**Disclosure divergence (published as-is).** The 39462322100 report and state
entry claim the adjacent regression as **"83 passed / 172 subtests"**. This run
measures **68 passed / 172 subtests** from those same four files
(24 + 27 + 11 + 6). The `83` does not reproduce; the measured value is the
measurement of record and the divergence is named here, never silently
corrected.

**Machine record:** `results/evaluation/orchestration_resume_39471603258/39471603258_verification.json`.

## 4. Audit-ready fix

The two out-of-scope pseudo-audit files were **re-homed byte-exactly** into the
lane namespace — `results/evaluation/orchestration_resume_39471603258/39470495546_producer_authored_audit_copy.json`
records each file's exact bytes (base64), `sha256` and git blob oid — and then
**removed from the auditor's protected namespace**. Nothing valid was deleted:
the re-home preserves the exact bytes and blob oids, and the valid completed work
(the 39462322100 measurement, report, instrument and tests) is untouched.

After the fix the lane owns **no new file** under `results/audit/` or
`reports/audit/` relative to the accepted base, and it owns no file for this run
id (`CYCLE_39471603258_GATE.json` / `CYCLE_39471603258.md`). The team job's
write-scope invariant is restored and the independent auditor can run.

## 5. Frozen pins — re-hashed byte-identical (zero drift)

| input | sha256 | status |
|---|---|---|
| `evaluation/frozen_bars/RULES_LABEL.json` | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` | ✅ |
| `evaluation/frozen_bars/RULES_GEOMETRY.json` | `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` | ✅ |
| `evaluation/frozen_bars/VERDICT_CONTRACT.json` | `b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c` | ✅ |
| `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` | `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` | ✅ |
| `evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json` | `f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072` | ✅ |
| `evaluation/minimal_ca_benchmark.py` | `567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b` | ✅ |
| `evaluation/counter_authority_surface_falsifier.py` | `0d0c6827c0983a66504040c81b29e36b8ec324b8f06fa80d250f8db192547171` | ✅ |
| `evaluation/mapping_free_recall_falsifier.py` | `58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302` | ✅ |
| V3 `packet.json` | `32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70` | ✅ |
| V3 de / fr / it bundles | `9b856e2b…` / `054bec47…` / `345e20d1…` | ✅ |

Zero new thresholds; no candidate built; no universal-174k benchmark rerun.

## 6. Claim ceiling

This cycle may claim exactly: **(a)** the 39470495546 snapshot's failure
mechanism is a lane-owned write-scope violation in the auditor's protected
namespace, proved from the committed tree and the workflow source; **(b)** the V3
counter-authority surface falsifier reproduces its committed record from the
accepted mount; **(c)** the lane snapshot was returned to an in-scope,
audit-ready state with the offending files re-homed, not destroyed.

It must **NOT** claim: any verdict, gate or admission on any packet; that the
absolute `LABEL_SOUND` or `GEOMETRY_SOUND` bars are met; that either
DO-NOT-SERVE order is lifted; that the map helps a jurist; that any Frontier
component was rebuilt or re-scored; that run 39462322100 is accepted (it is
proposed pending audit); or any unblocking of the human gate.

`human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`,
`ready_for_owner_session=false`, `owner_decision_required=false`. Both
DO-NOT-SERVE orders stand.

## 7. Tests

`tests/evaluation/test_orchestration_resume_39471603258.py`:
**10 passed / 0 failed / 0 skipped** (pytest 9.1.1). It pins the diagnosis, the
audit-ready invariant, the byte-exact re-home, the frozen pins and (mount-
dependent) the fresh V3 replay.

## 8. Control-plane hardening items — recorded, not patched

`.github/**` is control-plane scope and is NOT edited from this lane:

1. **"Persist team snapshot" is `if: always()`** (`core-lane.yml:146-147`), so it
   force-pushes an out-of-scope snapshot after a failed scope check. The durable
   fix is to gate it on the scope check (factory-wide requirement 35).
2. **The audit job's "Persist audit snapshot" has no `if: always()`**, so an
   auditor death leaves no audit branch and the lane re-dispatches
   (factory-wide requirement 20).

## 9. Next recommendation

**CONTINUE, bounded, same question (v61).** The lane stands ready for the next
accepted measurement (the counter-emission cross-check is already accepted;
`frontier-counter-label-emission` is consumed from its accepted branch). When
Product serves a NEW packet — only via an accepted serve recommendation replacing
the DO-NOT-SERVE orders, and none exists today — discharge the falsification
battery on its exact bytes under a NEW run id with a refreshed population pin.

Do **NOT** re-dispatch a zero-delta cycle; do **NOT** re-litigate closed items;
do **NOT** re-run the closed emission charter; do **NOT** re-author an audit
placement in the auditor's namespace.

## 10. Reproduction

```
cd /home/runner/work/LexMachina/LexMachina
python3 -m evaluation.orchestration_resume_39471603258        # exit 0
python3 -m pytest tests/evaluation/test_orchestration_resume_39471603258.py -q
```

## 11. Artifacts

| Artifact | Path |
|---|---|
| Diagnosis record | `results/evaluation/orchestration_resume_39471603258/39471603258_diagnosis.json` |
| Verification record | `results/evaluation/orchestration_resume_39471603258/39471603258_verification.json` |
| Re-home (exact bytes) | `results/evaluation/orchestration_resume_39471603258/39470495546_producer_authored_audit_copy.json` |
| Hypothesis (freeze-first) | `evaluation/ORCHESTRATION_RESUME_39471603258_HYPOTHESIS_V1.json` |
| Freeze record | `evaluation/ORCHESTRATION_RESUME_39471603258_FREEZE_RECORD.json` |
| Instrument | `evaluation/orchestration_resume_39471603258.py` |
| Test | `tests/evaluation/test_orchestration_resume_39471603258.py` |
| Cycle report | `reports/evaluation/ORCHESTRATION_RESUME_39471603258.md` |
