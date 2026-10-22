# Degradation-disclosure crosscheck — run 39820650174

- Lane: evaluation; direction v62
- Question: when the generative writer aborts, does the shipped product disclose that the counter-authority retrieval was **not measured**, rather than silently presenting an empty counter set as "no contrary authority"?
- Verdict: **DEGRADATION_DISCLOSURE_VISIBLE_AT_COMPLETE_BUNDLE_STAGE** (exit 0)
- Result: `results/evaluation/degradation_disclosure_crosscheck/39820650174_v2.json`, sha256 `f4e14a77...`
- V1 result preserved: `results/evaluation/degradation_disclosure_crosscheck/39820650174.json`, sha256 `4b9bc432...`, verdict `DEGRADATION_DISCLOSURE_GAP`, exit 1
- Frozen: V1 hypothesis `23397408...` / instrument `a2a0e12d...`; V2 hypothesis `1439f112...` / freeze `74007814...` / instrument `ced1f11b...`
- Evidence tier: EXPLORATORY; all admission/human flags false

## Inputs

Both inputs are committed, read-only recorded bundles, pinned before and after execution:

| Bundle | sha256 | State |
|---|---|---|
| `results/product/live_slice/CYCLE_39667945530_bundle.json` | `d58eea71...` | degraded: 151 decisions, pre-fix `answer.degradation=None`, writer error `RuntimeError: all provider attempts failed: opencode CLI failed (rc=1)` |
| `results/product/live_slice/CYCLE_39667945530_FIX1_bundle.json` | `f8123012...` | healthy: 158 decisions, `answer.status=ready` |

Product pins hold before and after: `pipeline.py` `f59bba1f...`, `adversarial_retrieval.py` `9764a37e...`, `answer.py` `acbc1614...`, `answer_reliability.py` `46e195de...`. The instrument installs a network guard; zero product calls attempted the network.

## V1 finding (preserved, not overwritten)

V1 asked whether `degradation_visibility()` reports `visible=true` for the abort and returned a gap. The single failing check was `product_visibility_visible` on the standalone extractive-fallback invocation.

Root cause is ordering, not silence:

- `_extractive_degraded_fallback` is called at `product/query/pipeline.py:1256`;
- `adversarial_retrieval_pass` runs at line 1288;
- `degradation_visibility` (lines 425-429) requires `adversarial_status`.

At the standalone fallback stage the pass has not run, so `visible=false` is correct for that stage. V1's sub-check was stage-blind: it demanded complete-bundle visibility from a pre-pass stage. The V1 result is preserved byte-for-byte and re-hashed by C6.

## V2 stage split

V2 keeps the same inputs and pins, and evaluates the fallback and the complete bundle as distinct stages:

1. **Standalone fallback stage**: `degraded=true`, code `e_EMISSION_WRITER_ABORT`, stage `generative_writer`, `visible=false` — expected and disclosed, not a gap.
2. **Complete-bundle stage**: the pass inherits the degradation, marks the counter set `DEGRADED`, and `degradation_visibility().visible=true` with the text: *"the adversarial pass is marked DEGRADED and an empty counter set here means 'not measured', never 'no contrary authority exists'."*
3. **Healthy leg**: no abort, no degradation disclosure raised, `answer.status=ready` — the mechanism does not fire spuriously.

That is the behavior the product needs: an aborted writer cannot be read as "we searched and found no contrary authority."

## Gates and controls

All four gates pass and all six controls hold:

| Gate | Result |
|---|---|
| G1 abort is a first-class answer field at the complete-bundle stage | pass |
| G2 the pass inherits the degradation instead of relabelling it measured | pass |
| G3 disclosure is machine-readable and correctly vacuous without legal vocabulary | pass |
| G4 the healthy leg raises no abort | pass |

| Control | Result |
|---|---|
| C1 deleting the answer field fails G1 | holds |
| C2 relabelling the pass as measured fails G2 | holds |
| C3 injecting an abort into the healthy leg fails G4 | holds |
| C4 network guard armed and unused | holds |
| C5 product and input pins hold before/after | holds |
| C6 V1 result preserved verbatim | holds |

## Claim ceiling

This establishes exactly one thing: on the two recorded bundles, the shipped writer-abort disclosure is visible and machine-readable at the complete-bundle stage, inherited by the adversarial pass, vacuous without legal vocabulary, and absent on the healthy leg. The standalone-fallback stage limitation is disclosed.

It is **not** a retrieval-quality, counter-authority recall, live-answer reliability, served-packet, label or geometry measurement. It does not meet or move either frozen bar (both remain REPORTED-ONLY and unmet on the v3 bytes), lifts no DO-NOT-SERVE order, changes no admission/human gate, builds or scores no frontier candidate, and runs no universal-174k benchmark. `NOT_APPLICABLE`/`NOT_MEASURED` is never treated as a pass.

## Next

The disclosure path is verified on recorded bundles. The remaining product-critical question is whether the counter-authority retrieval itself, and its visual map, return query-specific contrary authority rather than merely a well-labelled empty set. That is the next measurement; this crosscheck does not answer it.
