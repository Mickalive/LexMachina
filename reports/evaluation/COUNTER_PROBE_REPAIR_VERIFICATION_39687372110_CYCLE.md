# Evaluation cycle 39687372110 — counter-probe REPAIR-VERIFICATION

**Lane:** evaluation · **Direction:** v61 · **GitHub run:** 39687372110 · **Date:** 2026-10-21

## Verdict

**`REPAIR_VERIFIED_ON_RECORDED_BYTES` (exit 0)** — all 4 frozen gates PASS, all 5
controls PASS, all 8 pins held before and after execution, 0 network calls.

On the pinned recorded bytes of the accepted 14-bundle population, the
**recommended product remedy (a)** — strip the redaction placeholder
`[citation removed: not in retrieved set]` from the answer prose before the
product's own probe planner — **repairs the probe-anchor bounded cause**.

This is the lane's ordered work (2) repair-verification duty: the smallest
executable counter-authority benchmark that falsifies-or-verifies the named
product remedy before the product lane spends a cycle landing it. Freeze-first;
no universal-174k benchmark was run.

## What was measured

Two arms per bundle, both computed with the product's OWN
`plan_adversarial_queries` (imported via the accepted falsifier's loader —
tokenisation, stoplist and planner never re-implemented):

- **BASELINE** — shipped planner on shipped (post-redaction) prose; reproduced
  the recorded probes byte-for-byte on 14/14 bundles (C1).
- **FIXED** — remedy (a) emulated: placeholder occurrences replaced by a space,
  same planner.

| gate | result | detail |
|---|---|---|
| `G1_no_placeholder_token_in_fixed_anchor` | **PASS** | 0/14 FIXED anchors carry a placeholder-derived token (baseline: 2/14 contaminated) |
| `G2_fixed_anchor_topical_on_contaminated_bundles` | **PASS** | 2/2 contaminated German anchors regain the question content term `fürsorgepflicht` |
| `G3_fixed_is_noop_on_clean_anchor_bundles` | **PASS** | 12/12 clean-anchor bundles byte-for-byte unperturbed (incl. the 4 ph>0 non-contaminated ones) |
| `G4_fixed_matches_accepted_counterfactual` | **PASS** | 14/14 FIXED anchors equal the accepted falsifier 39674402905's published G4 de-redacted anchors, byte-for-byte |

G4 is the cross-instrument check: two separately committed computations of the
remedy (the accepted falsifier's REPORTED-ONLY counterfactual arm and this
instrument's claim-under-test arm) agree exactly.

## Acceptance fixture for the product lane

The result record publishes the per-intent repaired probe queries. On the two
contaminated German bundles the repair replaces the placeholder anchor with real
legal vocabulary while keeping the intent vocabulary intact, e.g. packet
39319405429 de:

- baseline: `citation removed retrieved nicht ausnahme exception eccezione …`
- fixed: `nicht fürsorgepflicht arbeitgeber bvger ausnahme exception eccezione …`

After the product lands remedy (a), the shipped planner should issue these exact
probe queries on these exact bundles.

## Discipline trail

1. **Freeze-first** (commit `c174e63a`): hypothesis + freeze record + instrument
   committed before any claim-bearing execution; only a synthetic `--selftest`
   ran beforehand.
2. **Attempt 1 → re-freeze seq 2** (commit `60215e0c`): the first claim-bearing
   run returned `ENVIRONMENT_OR_VACUOUS` because control C4 was *implemented*
   as `is not True`, counting the six ph>0 bundles' not-applicable `None`
   values as placebo failures. The frozen control definition ("for every bundle
   whose answer prose contains no redaction placeholder") was always correct;
   only the code diverged. Attempt 1 is preserved verbatim at
   `results/evaluation/counter_probe_repair_verification/39687372110_attempt1_c4_implementation_bug.json`
   (sha256 `967bfd52…`); the fix changed ONLY that predicate to `is False`.
   Rule, gates, control definitions, exit codes, population, thresholds (none)
   and claim ceiling are byte-identical. `ENVIRONMENT_OR_VACUOUS` is never a
   product verdict, so no gate outcome was laundered.
3. **Re-run**: all pins held (hypothesis, instrument, accepted falsifier
   instrument + record, 3 product files, 2 population manifests), 8/8 checks
   before and after.

## Tests

`evaluation/no_pytest_runner.py` shim (pytest is ABSENT in the producer image;
UNSUPPORTED counted as NOT-RUN):

- `tests/evaluation/test_counter_probe_repair_verification.py` — **27 passed /
  0 failed / 0 unsupported**, including a pin of the exact C4 bug the seq-2
  re-freeze corrected (`None` rows never count as failures; a `False` row does)
  and both-direction gate reachability on synthetic input.
- Regression, unchanged accepted files: `test_counter_probe_anchor_falsifier.py`
  25/25; `test_minimal_ca_benchmark.py` 10 passed / 1 unsupported.

## Claim ceiling

Establishes exactly one thing: whether remedy (a) repairs the probe-anchor
bounded cause on the pinned recorded bytes, under four frozen gates. Offline,
zero network calls; the FIXED probes are never executed against OpenCaseLaw.
NOT a counter-authority recall measurement, NOT a live-retrieval measurement,
NOT a label-emission measurement, NOT a measurement of the mapping-free
`counter_authority_surface` gates, NOT a `LABEL_SOUND`/`GEOMETRY_SOUND` claim
(both stay REPORTED-ONLY), NOT a serve recommendation. It lifts no DO-NOT-SERVE
order; packet admission stays fail-closed; `human_gate_ready` and
`owner_decision_required` stay false. It does not authorise the product lane to
skip re-measurement after landing the fix: when product bytes change, this
freeze's product pins drift by design and a NEW freeze under a NEW run id
verifies the shipped planner.

## Standing orders (unchanged)

- Both DO-NOT-SERVE orders stand (served packet 38839347028; rebuilt-39027045675).
- Absolute LABEL/GEOMETRY bars stay REPORTED-ONLY; `NOT_APPLICABLE` is never a
  pass.
- `minimal_ca_benchmark_v3` falsification and `counter_probe_anchor_falsifier`
  bounded-cause attribution are DISCHARGED — not redone, not re-litigated.
- `counter_probe_anchor_falsifier` and `product_cache_parity` remain EXPLORATORY
  with `pending_independent_audit=true` (audits are the audit job's scope).

## Next (same question, v61)

1. **Stand ready** for the product lane to land remedy (a); on landing, re-freeze
   this verification against the NEW shipped planner (new run id) and re-score
   the mapping-free `counter_authority_surface` gates on regenerated bundles.
2. **Stand-ready cross-check duty** on the next accepted product measurement,
   side-by-side, divergence-as-headline, re-deriving no threshold/bar/rubric.

`continue_recommended=true` · `human_gate_ready=false` ·
`owner_decision_required=false`.
