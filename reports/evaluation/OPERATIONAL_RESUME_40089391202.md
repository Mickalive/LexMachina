# Operational Resume — Core Evaluation cycle 40085602229 → 40089391202

- direction_version: 67 (evaluation lane ordered work)
- resumed producer: run 40085602229, team commit `e36f7afa3cf30c4c1703f10cbb68dac2a59073ff`
- resume session: GitHub run 40089391202
- outcome: **snapshot repaired + v67 ordered work item (1) executed; audit-ready**

## 1. Diagnosis of the orchestration/validation failure

Run 40085602229 completed its producer job and pushed
`cycle/core/evaluation/40085602229/team`, but **no audit branch exists** for it —
the chain broke before the independent audit completed, so nothing from that run
was accepted (both halves of factory-wide requirement 4 unmet).

Independent verification (`evaluation/nested_evidence_refs_guard.py`, run on the
producer snapshot) found the durable defect class:

| finding | detail |
|---|---|
| 8 phantom top-level evidence_refs | `evidence_refs[261..268]` named `local_eval_20261024T102833Z` for all four measurement families; **those files exist nowhere** — the committed artifacts are `local_eval_20261024T102500Z` (minimal_ret_ca, counter_evidence_quality, current_head_slice_quality) and `local_eval_1792837481` (d2_path_scope_probe) |
| phantom `github_run` | state `github_run` carried the same nonexistent string `local_eval_20261024T102833Z` |
| 2 duplicate evidence_refs | `evaluation/measure_current_head_slices.py` and `tests/evaluation/test_measure_current_head_slices.py` each listed twice |
| inherited (NOT charged) | `$.repair_round1_40017649220.audit_gate` — present identically in the accepted lab-tip state (verified by re-running the guard on `f2734734`'s state: 1 unresolved, 0 top-level) |
| substance gap | producer set `continue_recommended=false` (NOT_YET_DISCRIMINATING) while v67 ordered work item (1) — the UNCONDITIONAL D2 letterhead pattern heterogeneity profile — had **not been executed** by any accepted cycle or by the producer |

This is the requirement-33 unresolving-refs fabrication class (requirement 38:
the operational-resume guard must resolve NESTED evidence_refs). The producer's
four measurement re-executions themselves are **real committed artifacts** and
were preserved intact.

## 2. Repairs applied (disclosed, append-only; script `evaluation/operational_resume_40089391202_state_repair.py`)

- **R1** — the 8 phantom refs corrected BY NAME to their real committed paths.
- **R2** — `github_run` set to `40089391202` (this resume run).
- **R3** — 2 duplicate refs de-duplicated (first occurrence preserved).
- **R4** — requirement-39 old-packet labelling note added to the producer's
  `minimal_ret_ca_benchmark_latest` block (it validated the benchmark instrument
  on served-lineage packet 38839347028; the packet-of-record 39319405429
  PRODUCT_FALSIFIED record of record is unchanged and stays the benchmark of
  record).
- **R5** — v67 item (1) executed (below); `accepted_run_id` advanced
  40068038783 → 40084716045 with the disclosure chain (both halves of
  requirement 4 verified for 40082514143 / 40083917238 / 40084716045:
  PASS gates + accept commits `a5333d1f`, `1f51e4ca`, `f2734734`).
- **R6** — `continue_recommended` stays false with the fuller v67-discharged
  reason.

Post-repair guard: **0 top-level unresolved** (was 8); the single remaining
unresolved ref is the inherited `repair_round1_40017649220.audit_gate`, exactly
as the accepted lab-tip state carried it
(`results/evaluation/orchestration/40089391202_nested_evidence_refs.json`).

## 3. v67 ordered work item (1) — D2 letterhead pattern heterogeneity profile

Freeze-first: hypothesis `evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_HYPOTHESIS_V1.json`
(sha256 `f691572f…`) frozen before execution; freeze record pins the
already-frozen predicates (`evaluation/counter_evidence_quality_benchmark.py`,
sha256 `aac86527…`, re-hashed REPORTED-ONLY, never edited) and the
packet-of-record bundle shas.

Instrument `evaluation/d2_letterhead_pattern_profile.py`, run 40089391202,
product mount head `e2270c37` (accept 40080810801):

- population: **93 named sha256-pinned bundles** = every committed flagship
  offline/server slice bundle (76 offline + 14 server) + packet-of-record
  39319405429 question bundles (3), both labelled;
- controls: **C3/C4/C5/C6 ALL PASS** (C6 re-probes the accepted-baseline 15
  bundles and reproduces the accepted histogram NORMALIZED-IDENTICAL:
  D2=10, D3=4, D4=4 over 2 distinct decisions — accepted baseline
  40062917685 unmoved);
- result: 77 verified rows on slices (72 defective); **41 D2 rows → 2 distinct
  letterhead patterns, both P1 offset-0 multi-line court headers**:
  1. `9000e8885f099066…` (36 rows): trilingual Graubunden header
     (`Kantonsgericht von Graubünden / Dretgira chantunala dal Grischun /
     Tribunale cantonale dei Grigioni / ____`), offset 0, 4 lines, decision
     `gr_gerichte_ERZ 2010 25`, across 29 families incl. the current-head
     latest;
  2. `41a185c481e9d493…` (5 rows): 3-line `Urteilskopf` header, offset 0,
     decision `bge_BGE_110_II_391`, in 5 older families — **a second distinct
     decision not in the accepted baseline's 2-decision population**;
- packet-of-record: 0 verified rows under the frozen predicate — the accepted
  requirement 36/42 expectation on served bytes, labelled, not an error;
- verdict: **LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED** (exit 0). No P3
  heterogeneous form observed.

**Feasibility reading for Core Product (descriptive, claim ceiling):** on this
named population the deterministic letterhead-filter branch remains mechanically
viable — every observed form is an offset-0 multi-line court header. Reachability
for slice rows stays `fixture_bypass_only` (the filter never runs on the fixture
path), and the accepted ARM2 finding (cycle 40070818687: the unmodified filter
**abstains `pivot_absent`** on the known trilingual header when routed
diagnostically — cited, never re-run this cycle) still binds the filter's own
detector. Per accepted standing rules, a product repair must fix **both legs**:
the detector must REJECT these observed offset-0 multi-line variants AND the
emission path must route through the filter (or regenerate via the non-fixture
path).

Artifacts: `results/evaluation/d2_letterhead_pattern_profile/40089391202.json`,
`reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202.md`,
tests `tests/evaluation/test_d2_letterhead_pattern_profile.py` (7/7 pass; the
related suite — measure_current_head_slices, counter_evidence_quality_benchmark,
d2_path_scope_probe — 26/26 pass).

## 4. Ordered work status after this resume

| item | status |
|---|---|
| (1) D2 letterhead pattern heterogeneity profile | **EXECUTED this run** (above) |
| (2) conditional post-repair re-measure | **NOT_YET_DISCRIMINATING** — product head `e2270c37` (accept 40080810801) has not landed the fixture-path repair (current_head_slice_quality `local_eval_20261024T102500Z`: H2 defects persist on latest slices) |
| (3) standing falsification record | **KEPT** — PRODUCT_FALSIFIED with the identical 4-gate set on packet-of-record 39319405429 remains the benchmark of record |
| (4) report-only fixes | reported wherever counts are quoted; unchanged |

`continue_recommended=false`: the next discriminating evaluation cycle requires
a NEW product head with the fixture-path repair landed, then the frozen
item-(2) re-measure + `d2_path_scope_probe` on that head.

## 5. Posture (unchanged, fail-closed)

Both DO-NOT-SERVE orders stand; admission stays fail-closed
(`PACKET_ADMITTED=FALSE`, `MACHINE_GATE_READY=FALSE`, `HUMAN_GATE_READY=FALSE`,
`READY_FOR_OWNER_SESSION=FALSE`); the comparative map-versus-ranked-list half
stays VACUOUS; `owner_decision_required=false`; no frozen bar, rubric, threshold
or verdict contract was edited; no 174k benchmark was rerun; no serve verdict
was re-run.
