# Counter-emission cross-check — run 39457963802 (direction v61 ordered work (2))

**Lane:** evaluation (Core Evaluation — continuous falsifier)
**Direction:** factory_direction v61, ordered work (2): *the emission team's accepted artifact has landed; publish the established side-by-side cross-check — the serve-verdict-cross-check pattern — placing every quantity the team publishes beside this lane's own recomputation of the same bytes, naming any divergence as the headline; re-deriving no threshold, bar, rubric or verdict contract.*
**Verdict:** `CROSSCHECK_COMPLETE` — **ZERO_DIVERGENCE_ACROSS_96_COMPARABLE_QUANTITIES**, 6 NOT_COMPARABLE published (lane-only aggregates), 4/4 non-vacuity controls detect planted divergences, exit 0.

---

## 0. Headline up front

The independently ACCEPTED **frontier-counter-label-emission** record (team run 39426324296, audit gate `PASS` safe_to_integrate=true, promote commit `437c7117`, outcome `A_EMISSION_RECOVERED`) reproduces **exactly** against this lane's own recomputation of the same packet-of-record V3 bytes and against internal-consistency recomputation over the team's committed artifacts. 102 side-by-side rows: 96 comparable, **96 match, 0 diverge**; 6 rows are lane-only aggregates the team never published as aggregates (NOT_COMPARABLE, published with reasons, never dropped). Headline: `ZERO_DIVERGENCE_ACROSS_96_COMPARABLE_QUANTITIES`.

What the cross-checked numbers **mean** (published, not softened):

| quantity | de-kapitalverletzung | fr-bail-entretien | it-responsabilita-medica |
|---|---|---|---|
| adversarial rows in bundle (lane-recomputed) | 8 | 8 | 8 |
| all with `counter_evidence=''`, `counter_status=none` (BEFORE) | 8/8 | 8/8 | 8/8 |
| n_scored BEFORE / AFTER | 0 → **8** | 0 → **8** | 0 → **4** |
| n_abstained AFTER | 8 | 8 | 4 |
| **n_emitted AFTER** | **0** | **0** | **0** |
| support-among-issued | 0.0 | 0.0 | 0.0 |
| yield over population | 0.0 | 0.0 | 0.0 |
| absolute bar status AFTER (1.0 as written) | LABEL_UNSOUND | LABEL_UNSOUND | INSUFFICIENT_POPULATION |
| primary cause (all bundles) | e_EMISSION_WRITER_ABORT | e_EMISSION_WRITER_ABORT | e_EMISSION_WRITER_ABORT |
| determinism (3 runs, identical) | true | true | true |

The accepted emission repair (`heuristic_proposal_promotion_v1`, min_evidence_chars=40) moved rows from **never reaching the classifier** (n_scored=0, NOT_MEASURED) to **reaching the classifier, which abstains on every row** (n_scored 8/8/4, n_emitted 0). The frozen absolute bar stays unmet on the team's own after-state; yield stays 0.0. This is the honest rubric-faithful outcome, verified byte-for-byte; this lane certifies the *numbers*, not the product.

## 1. Freeze-first discipline

- Hypothesis `evaluation/COUNTER_EMISSION_CROSSCHECK_HYPOTHESIS_V1.json`, sha256 `2691e1aff1a0ae3e77bfc58149c810b12234ae2532115c26166686c0533e84e3`, committed at freeze commit `6a3f70ef` **before** the instrument existed or ran.
- Freeze record `evaluation/COUNTER_EMISSION_CROSSCHECK_FREEZE_RECORD_V1.json`.
- Precedent invoked verbatim: the accepted serve-verdict cross-check (run 39381093325, accept `70f1a2b7`).

## 2. Inputs, vendoring, identity (all re-hashed, never re-derived)

- The team's nine accepted artifacts were vendored **byte-exactly via `git cat-file`** from `origin/lab/frontier/frontier-counter-label-emission` @ `437c7117` into `evaluation/vendored_frontier_counter_emission/` with `PROVENANCE.json`; every file's **git blob oid** was re-verified live against the origin ref (9/9 match).
- Frozen pins re-hashed, 0 mismatch: RULES_LABEL `4457e971…`, RULES_GEOMETRY `a7452748…`, VERDICT_CONTRACT `b9cdb894…`, all vendored shas, packet `32ac8126…`, manifest `8ea3c92d…`, bundles `9b856e2b… / 054bec47… / 345e20d1…`.
- The team's own `ARTIFACT_DIGESTS.json` internal pin re-hashed by this lane: **holds** (5/5).
- Instrument: `evaluation/counter_emission_crosscheck.py` (pure stdlib; imports no Product or Frontier code; no network).

## 3. What this lane recomputed itself (not copied)

1. **From the packet bytes:** per-bundle row totals (182/185/179) and the BEFORE-state of the adversarial surface — exactly 8 `ocl:adversarial.*` rows per bundle, every one `counter_evidence=''` / `counter_status=none`. This independently establishes the zero-emission BEFORE state the team published.
2. **Internal consistency of the team's artifacts:** `n_scored == n_abstained + n_emitted`; abstention-reasons sums; determinism signature lengths vs n_scored; repair `n_promoted == n_proposed == n_scored`. All true on all three bundles.
3. **Requirement 25/26 triples, always published together** (never split, never laundered): support-among-issued 0.0, abstention counts 8/8/4, yield 0.0, plus both regression-verdict semantics (NOT_MEASURED/NOT_APPLICABLE/INSUFFICIENT_POPULATION are never a pass).

## 4. Non-vacuity (4/4 detect)

Perturbations, each detected as a divergence by the comparator: team after.n_scored de 8→9; lane n_total_rows de 182→181; team absolute status fr →LABEL_SOUND; lane packet sha flipped. The comparator sees both sides, not just one.

## 5. Tests

- Real pytest 9.1.1: **27 passed / 0 failed / 0 skipped** (+172 subtests), junit sha256 `03a59e3746c2e1b7e0d67f778cbd63037b6cdc420f93688bd2dae8d19cf13b03`, record `results/evaluation/orchestration/39457963802_pytest_real.json`.
- In-tree shim beside (disclosure, never merged): `SHIM_PASS` with **0 discovered cases** — the shim does not discover `unittest.TestCase` classes; the real pytest reading is the measurement of record and the degenerate shim count is disclosed, not hidden.
- Adjacent regression spot-check: `test_serve_verdict_crosscheck.py` + `test_minimal_ca_benchmark.py` + `test_repair_39433092808_artifact_hygiene.py` → 41 passed / 0 failed.

## 6. Claim ceiling (binding)

This cycle claims exactly one thing with a committed machine record: **every quantity the accepted emission team published reproduces against this lane's recomputation of the same bytes (ZERO_DIVERGENCE across 96 comparable quantities)**. It does **not**: re-derive, edit or re-tune any threshold/bar/rubric/incumbent/predicate; assert any decision IS supporting/contrary/limiting; certify LABEL_SOUND or GEOMETRY_SOUND; lift any DO-NOT-SERVE order; override the accepted BOUNDED-NEGATIVE serve verdict; re-run the closed emission charter; or authorise any owner question. `human_gate_ready`, `machine_gate_ready`, `packet_admitted`, `ready_for_owner_session` all stay **false**; `owner_decision_required` stays **false**; both DO-NOT-SERVE orders stand; no universal-174k benchmark was rerun.

## 7. Recommendation

**CONTINUE** (bounded, same question). The ordered-work-(2) cross-check duty is discharged and machine-backed. Standing work remains: (3) frozen pins stay byte-identical; (4) P1/P1ext stay REPORTED-ONLY; (5) when Product serves a NEW packet (only via an accepted serve recommendation replacing the DO-NOT-SERVE orders — none exists today), discharge the falsification battery on its exact bytes under a new run id. The zero-label emission fact after the accepted repair (yield 0.0, all rows abstained) is now cross-verified evidence for the director's routing of the BOUNDED-NEGATIVE's bounded cause #1 — this lane issues no verdict on it.

Artifacts: `results/evaluation/counter_emission_crosscheck/39457963802.json` (instrument record of record) · `evaluation/vendored_frontier_counter_emission/` · `tests/evaluation/test_counter_emission_crosscheck.py` · twin pytest readings under `results/evaluation/orchestration/39457963802_pytest_{real,shim}.json`.
