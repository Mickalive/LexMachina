# Evaluation cycle report — run 38934722443 (direction v49)

Lane: evaluation. Question: encode and enforce the observed reality-check
failures; keep the frozen substantive gates for rent-default Art. 257d(2),
Art. 102 CP primary/subsidiary split, direct TF BJR authority/criteria and
low-value theft authority; reject wrong-language/corrupted outputs and full
runs >= 300s.

## What this cycle did

1. Re-validated the frozen benchmark digest before execution:
   `evaluation/reality_gate/frozen_benchmark.json` sha256 =
   `ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8` —
   unchanged, no re-freeze, no threshold/question/scope movement.
2. Re-executed the frozen benchmark against the refreshed ACCEPTED product
   mount (`/tmp/lex_accepted/product`), which now carries the product lane's
   V49_TARGETED_REALITY_REPAIR_4OF4_LIVE packet (run 38924869286): 16 new
   artifacts in `results/product/reality_check/` (5 live legs, 5 fixture
   fatal stubs, 6 roll-ups).
3. Fixed one harness precision gap (no gate change): the minimal
   durable-workflow roll-up shape (`legs` array + `mode`, no
   `all_legs_passed`) now classifies as `summary_rollup` with its per-leg
   array preserved in the record; previously it fell into `unmatched_kind`
   with a misleading exclusion reason. Roll-ups are excluded from verdicts
   under both classifications, so no verdict moved.
4. Pinned the current packet's verdicts with regression tests
   (`tests/evaluation/test_reality_gate.py`, +2 tests; suite now 48/48).

## Execution record

`results/evaluation/reality_benchmark/38934722443.json` — byte-identical
across repeated executions (verified). Inputs (read-only, ACCEPTED product
evidence only): `results/product/reality_check/` (62 files),
`results/product/gate_packet/38839347028/questions/` (3 full bundles +
auxiliary), `results/product/adversarial_retrieval/38828034436` (4 full
bundles + scoring). No 174k benchmark rerun; no Product code imported.

Counts: 82 artifacts = 29 slim reports + 12 fatal stubs + 21 roll-ups +
13 unmatched-kind + 7 full bundles. 36 evaluated (29 full-match +
7 question-independent), 46 excluded without verdict (each with explicit
`not_measurable_gates` + reasons). 35 bundle-structural gate executions.
7/7 multilingual FR/DE/IT coverage checks PASS.

## Verdict: FAIL on the recorded history (negative evidence, preserved)

19 falsifying failures across 17 artifacts:

| gate | n | artifacts |
|---|---|---|
| `latency::under_budget` | 5 | historical 20261014 legs: 463.773s, 548.452s, 340.782s, 360.542s, 861.409s |
| `truth::art257d2_end_of_month` | 4 | historical rent-default legs (20261014T120802/140446/142206/142443) |
| `structural::adversarial_clean` | 2 | historical rent-default legs (20261014T113201/120802) |
| `structural::counter_classifications_supported` | 6 | recorded full bundles (gate_packet 38839347028 x3, adversarial 38828034436 x3) |
| `recall::citation_controlling_authority` | 2 | **NEW this cycle**: `business-judgment-rule_live_20261016T161006Z` (missing all five frozen BJR authorities) and `petty-theft-dismissal_live_20261016T155135Z` (missing both frozen petty-theft authorities) |

Delta vs the accepted record 38920872324: exactly +2 recall failures, both
on the current packet. All 66 pre-existing artifact verdicts are identical
(recomputed, not assumed); 13 pre-existing minimal summaries moved kind
`unmatched_kind` -> `summary_rollup` under the classifier fix (no verdict
change — excluded either way).

## The current product packet, leg by leg

Product cycle V49_TARGETED_REALITY_REPAIR_4OF4_LIVE (run 38924869286) ran
four fresh live legs. Frozen-benchmark verdicts:

| leg | verdict | latency | note |
|---|---|---|---|
| `rent-default_live_20261016T154849Z` | PASS | 111.774s | all three truth gates fire ('30', 'fin de mois', 'abus') |
| `corporate-criminal-liability_live_20261016T160526Z` | PASS | 276.119s | cites both frozen authorities (BGE 142 IV 333, 6B_124_2016); under the 300s budget but within model-speed variance — the product flagged the same residual latency risk |
| `petty-theft-dismissal_live_20261016T160318Z` | PASS | 111.158s | partial recall pass: cites `bger_4A_177_2017`, misses `bger_4A_228_2015` (>=1-of-set semantics, missing list disclosed) |
| `business-judgment-rule_live_20261016T161006Z` | **FAIL** | 150.401s | cites **none** of the five frozen direct-TF BJR authorities (`bger_4A_219_2015/259_2016/626_2013/603_2014/62_2024`); its citations are BGE 110 II 391, BGE 139 III 24, zh_handelsgericht_HG120149 |
| `petty-theft-dismissal_live_20261016T155135Z` | **FAIL** (preserved) | 197.184s | pre-fix negative: cites neither `bger_4A_177_2017` nor `bger_4A_228_2015`; the failure the product repaired in the 160318Z leg |

The BJR falsification is the cycle's key finding. The producer's own gates
pass the 161006Z leg (structural + phrase-level truth: information / conflit /
retenue all present). The frozen benchmark adds the authority-recall
dimension the producer's gates do not check: the answer's authority base
contains no decision from the TF 4A_ BJR line the lane froze. This is
exactly the "structural bundle validity is insufficient" failure mode the
v49 lane question names — machine-green on the producer's own gates, red on
the frozen authority gate. The product's exit criterion ("the frozen
four-question substantive benchmark is reliably green") is therefore NOT
met for the BJR question on this packet.

The five 20261016 fixture legs are fatal stubs (OpenCaseLaw retrieval
returned no decisions) — preserved as negative evidence, excluded from
verdicts with reasons. The six 20261016 roll-ups are excluded as
run-level aggregates; their per-leg arrays are preserved in the record.

## Claim ceiling

The benchmark falsifies machine-checkable properties of recorded product
artifacts (substantive truth phrases with two disclosed weak lexical
proxies, >=1-of-frozen-set authority recall with partial passes disclosed,
wrong-language/corrupted output, >=300s full-run latency, bundle structure
incl. counter-evidence support, multilingual coverage). It does NOT prove
map usefulness to a jurist; `human_gate_ready` stays false. The whole-mount
FAIL is a statement about the recorded history (which contains preserved
negatives), not a claim that every current leg fails: 3 of the 4 fresh
live legs pass every machine-measurable gate.

## Tests

`tests/evaluation/test_reality_gate.py`: 48/48 PASS (46 prior + 2 new:
minimal-rollup classification pin; current-packet verdict pin, skipped
cleanly when the accepted mount is absent). The v49 active suite
(test_reality_gate 48 + test_audit_correction_verification 4 +
test_frontier_verdict_adoption 9) is green. Legacy 174k test collection
errors (numpy-missing obsolete benchmarks) are pre-existing and correctly
not rerun per the lane directive.

## Recommendation

CONTINUE. The frozen benchmark is executed against the current accepted
packet and falsifies the BJR leg's authority base. Concrete next-cycle
purpose under the SAME v49 question: re-execute against the next accepted
product packet and check whether the BJR answer's citation set recovers at
least one frozen direct-TF authority; the product lane's exit gate stays
closed until the four-question benchmark is reliably green without
weakening truth/authority/language/latency gates. Do not reopen
174k/global-map research.
