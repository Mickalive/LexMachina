# Disclosure-provenance cross-check — evaluation run 39516448683 (direction v61, FAST-MVP)

**Verdict: `VERDICT_DISCLOSURE_PROVENANCE_VERIFIED_ZERO_DIVERGENCE`, exit 0 —
`ZERO_DIVERGENCE_ACROSS_19_COMPARABLE_ROWS` (verbatim 2/2, pin 3/3, quantity
12/12, placement 2/2); non-vacuity 4/4.**
Record of record: `results/evaluation/disclosure_provenance_crosscheck/39516448683.json`
(instrument `evaluation/disclosure_provenance_crosscheck.py`, sha256
`2e9d9f08c5f4c3753e46825729c42968f7492842d236513f52dc2a5407857b1f`).

## 1. What this cycle measured and why it is the lane's question

Direction v61 ordered the lane to (1) finish the repair2 chain — discharged and
accepted at `44fec3dd` / cycle 39491098975 before this dispatch — and (2) stand
ready with the side-by-side cross-check pattern for the next accepted
measurement; the counter-emission cross-check (39457963802) is COMPLETE. The
open falsifiable surface under the same question was the newest claim-bearing
product artifact that transcribes **Evaluation-owned numbers**:
Product's counter-instability disclosure (run 39422322667, landed **without an
in-tree audit gate file** per Product's own state), which places open items 5/6
and their P1/P1ext REPORTED-ONLY quantities on the packet-of-record V3
disclosure layer.

This cycle froze (freeze-first, hypothesis committed at `56a51aa2`, freeze
record + instrument at `a04405a3`, both **before** any execution) and executed
the smallest executable cross-check that can falsify that artifact: does every
published quantity reproduce byte-for-byte from Evaluation's committed
evidence, or does any claim fail to reproduce from the committed tree?

## 2. Inputs (all re-hashed before and after the run; `safety.pins_unchanged=true`)

| source | sha256 / pin |
|---|---|
| frozen hypothesis `DISCLOSURE_PROVENANCE_CROSSCHECK_HYPOTHESIS_V1.json` | `e72973e0cb3e4934048a18af63e7d9f0f6ae696dc96f185b53ca30e625d47e64` (hard-coded in the instrument; run refuses on mismatch) |
| sweep artifact of record `cross_run_stability_sweep/39322925971.json` | `a287fbe26bbbb6c16e1163e07036474424db2126ab855218ee9738ccf7b71c0e` |
| `origin/main@50166b4c:results/accepted-state/evaluation.json` | `285b32cf…` / blob `a1336f0e…` (re-derived this run, matches Product's published pin) |
| frozen rubrics (re-hashed, never re-derived) | RULES_LABEL `4457e971…`, RULES_GEOMETRY `a7452748…`, VERDICT_CONTRACT `b9cdb894…` |
| product mount (`/tmp/lex_accepted/product`, read-only) | disclosure `ad9e8877…`, vendored open items `aecab7ff…`, packet.json `32ac8126…`, bundles `9b856e2b…` / `054bec47…` / `345e20d1…` — **no drift vs freeze-time observations** |

Environment disclosure: this clone is **shallow** and initially lacked pin
commit `50166b4c…`; an explicit `git fetch --depth=1 origin <pin-commit>`
resolved it (`pin_resolution="already_present"` at execution time because the
fetch was already performed during freeze). The instrument repeats the fetch if
absent and treats an unfetchable commit as `ENVIRONMENT_ERROR` (exit 2), never
as a product divergence.

## 3. Side-by-side result (every quantity Product publishes beside this lane's recomputation)

| rows | result |
|---|---|
| **V1/V2 verbatim open items 5/6** | 4/4 surfaces identical (Product disclosure, Product vendored copy, origin/main **current** accepted-state, this lane's `state/evaluation.json`) **and** equal to the freeze-time text pins `ab771b84…` / `fb26cf86…` |
| **P1/P2/P3 pins** | pin-commit accepted-state re-hashes to `285b32cf…` and blob `a1336f0e…` exactly as Product publishes; pin commit resolvable |
| **P4 current-file drift** | current main accepted-state is `bb90821a…` / `e42e8872…` ≠ the pin — **file-level drift disclosed, expected under Product's own `pin_semantics`; the load-bearing live check is the verbatim row, which passes** |
| **Q1/Q2 jaccard** | DE `0.904762`, FR `0.892216` — match sweep at frozen round-6 |
| **Q3/Q4 rank movement** | DE 26, FR 126 — exact integers |
| **Q5/Q6 cluster reassignment** | DE 71/95 → 0.747, FR 113/149 → 0.758 — exact ints + frozen round-3 shares (sweep: 0.747368 / 0.758389) |
| **Q7/Q8 FR counter evidence** | lost `{bge_146 IV 68, bstger_TPF_2012_62}`, gained `{bger_6B_750_2020}` — set equality with the sweep |
| **Q9 FR divergence block** | `sr::counter_authority_surface` DIVERGENT, passing `CYCLE_39128456801_live`, failing `CYCLE_39139648336_F1F2_VERIFY` with `n_issued=0`, all other applicable legs STABLE on both groups (legs enumerated in the record) |
| **Q10 DE attribution** | sweep DE leg `NOT_APPLICABLE` naming **both** runs `20261019T022100Z` / `20261019T153744Z` — Product's "UNTESTED (NOT_APPLICABLE in both DE runs)" reproduces |
| **Q11 IT attribution** | sweep `n_groups=2`, structure keys `de-kundigung-mietvertrag`, `fr-responsabilite-102cp` (non-empty, no `it-` key) — Product's "no IT same-query group exists" reproduces |
| **Q12 answer swap** | FR group `answer_a.n_cited=6`, `answer_b.n_cited=5`, prose sha256 differ — the "6 cited vs 5 cited" verbatim claim reproduces |
| **L1 placement** | `disclosures.json` **and** `handoff.json` carry `run_to_run_counter_instability` beside `under_coverage_disclosure` for all three V3 qids |
| **L2 packet identity** | packet.json `32ac8126…` and all three bundle shas equal the frozen V3 pins — the disclosure-layer regeneration moved **no scored byte** |

**Divergences: none (19/19 comparable rows match).**

## 4. Non-vacuity (4/4) and fail-closed probes

Four planted perturbations on in-memory copies, each re-run through the real
row comparator, each detected (named row flips match→divergence):
jaccard fr→0.5 (Q2), open-item text edit (V1), pin sha→64 zeros (P1), dropped
lost-id (Q7). Additionally `test_mount_absence_never_produces_a_pass` proves an
absent mount raises `ENVIRONMENT_ERROR` — a missing mount is never a pass.

## 5. Instrument-strengthening disclosure (append-only)

The first execution of this run wrote
`39516448683_initial_instrument_execution_preserved.json` (preserved beside the
final record, never deleted; same verdict, exit 0). Before publication the
**Q10/Q11 structural checks were strengthened only** — DE both-runs
not-applicable naming, non-empty structure keys with no `it-` prefix, and
instrument digest + numeric environment recorded. No check was weakened, no row
dropped, the frozen hypothesis/success rule untouched. This artifact is the
measurement of record.

## 6. Tests (real pytest 9.1.1, artifacts committed)

- dedicated suite `tests/evaluation/test_disclosure_provenance_crosscheck.py`:
  **24 passed / 0 failed / 0 skipped** — artifact
  `results/evaluation/disclosure_provenance_crosscheck/pytest_39516448683.xml`
  (sha256 `4611cfb9…`). 0 skips because the accepted product mount was present;
  the two mount-gated tests are explicitly skip-not-pass in their contracts.
- adjacent regression (cross-check pattern family):
  `test_counter_emission_crosscheck` + `test_minimal_ca_benchmark` +
  `test_serve_verdict_crosscheck` → **59 passed / 0 failed / 205 subtests
  passed**.
- end-to-end re-execution under the test suite produced byte-stable comparison
  rows against the committed record (`test_local_reexec.json`).

## 7. Claim ceiling and standing posture

This cross-check verifies **provenance fidelity** only. It does NOT re-measure
P1/P1ext (ordered work (4): those numbers are measured of record by 39322925971
and are computed here by no one twice — this instrument only verifies Product's
transcription against that artifact), scores no label/geometry bar, publishes
no support triple (no labels scored), meets no frozen bar, serves no packet,
lifts no DO-NOT-SERVE order and authorises no owner question.
`human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`,
`ready_for_owner_session=false`, `owner_decision_required=false`; both
DO-NOT-SERVE orders stand; no universal-174k benchmark rerun; zero new
thresholds; no candidate built.

## 8. Recommendation

**CONTINUE**, bounded, same question (v61): Product's P1/P1ext disclosure
carries evaluation-owned numbers honestly, so Product's ordered-work-(3)
disclosure block is certified transcription-wise and the lane's stand-ready
posture holds for the next accepted measurement (any successor counter-emission
artifact, or a newly served packet's exact bytes under a NEW run id with a
refreshed population pin). No zero-delta verification cycle: the next cycle
needs a new accepted artifact to cross-check or a new packet to falsify.
