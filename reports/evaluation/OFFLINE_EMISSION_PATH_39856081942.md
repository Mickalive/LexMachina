# Offline Emission Path Benchmark — run 39856081942

## Verdict

- **PATH_MEASURED_NO_FALSIFICATION** (exit 0)
- Reason: promotion and three-number publication held; total n_scored=20 n_abstained=20 n_emitted=0; comparative half VACUOUS (n_emitted=0)
- Product mount head: `fe219a197e4bfb129984a732ab9adca917556eac`
- Packet: 39319405429 (packet-of-record v3 exact bytes)
- Instrument: `lex-evaluation-offline-emission-path-benchmark/1` via `evaluation/offline_emission_path_benchmark.py`
- Generated: 2026-10-22T21:39:46Z
- Hypothesis: `None` sha256 `119e25e9e78de356...`

## Why this run (not another static-packet re-score)

Ordered work (1) of the v63 evaluation question requires this lane to re-score the
mapping-free `counter_authority_surface` gates on **regenerated / post-path** bundles
once remedy (a) lands. Remedy (a) HAS landed on the accepted product mount
(adversarial_retrieval.py sha256 `9764a37e...` contains `strip_redaction_placeholders`;
shipped-planner verification accepted at run 39813664201). The last two accepted
cycles (39852758814, 39854748616) re-scored the SAME static packet bytes and both
returned PRODUCT_FALSIFIED with `n_issued=0` — that re-verification is discharged.
This cycle measures the SHIPPED offline emission PATH that was integrated after the
packet was built: `apply_counter_emission_repair` then `apply_anchor_labels`, exactly
as `product/query/pipeline.py` wires them between `adversarial_retrieval_pass` and
`apply_anchor_labels`. Each served bundle still carries `provenance.counter_emission_repair`
ABSENT while 8/8/4 heuristic signals with non-empty evidence are present.

## Aggregate — three-number publication (always co-published)

| quantity | value |
|---|---|
| n_promoted | 20 |
| n_scored | 20 |
| n_abstained | 20 |
| n_emitted | 0 |
| comparative map-vs-ranked-list | **VACUOUS** |
| frozen absolute bars | REPORTED-ONLY and unmet on the v3 bytes; not re-derived here |
| packet_admitted | False |
| human_gate_ready | False |

`n_emitted=0` means the comparative map-versus-ranked-list half stays **VACUOUS**
(neither a map-negative nor a gate input). The frozen absolute LABEL_SOUND bar
stays REPORTED-ONLY and unmet; this instrument never re-derives it.

## Per-question

### de-kapitalverletzung

- **baseline** (served packet bytes): heuristic signals with evidence = 8; emission-repair provenance present = False; counter_anchor = {'n_scored': 0, 'n_emitted': 0, 'n_abstained': 0, 'yield': 0.0}; mf n_issued = 0
- **post-path**: n_promoted=8 n_scored=8 n_abstained=8 n_emitted=0 yield=0.0 support_rate_among_emitted=0.0
- **abstention reasons**: {'no_domain_anchor': 1, 'no_intent_marker': 2, 'pivot_absent': 5}
- **post-path mf::counter_authority_surface**: n_issued=0 n_with_empty_evidence=0 gate_pass=False
- E1 promotion exact: True — n_promoted=8 vs heuristic-signal rows with evidence=8

### fr-bail-entretien

- **baseline** (served packet bytes): heuristic signals with evidence = 8; emission-repair provenance present = False; counter_anchor = {'n_scored': 0, 'n_emitted': 0, 'n_abstained': 0, 'yield': 0.0}; mf n_issued = 0
- **post-path**: n_promoted=8 n_scored=8 n_abstained=8 n_emitted=0 yield=0.0 support_rate_among_emitted=0.0
- **abstention reasons**: {'no_intent_marker': 2, 'pivot_absent': 6}
- **post-path mf::counter_authority_surface**: n_issued=0 n_with_empty_evidence=0 gate_pass=False
- E1 promotion exact: True — n_promoted=8 vs heuristic-signal rows with evidence=8

### it-responsabilita-medica

- **baseline** (served packet bytes): heuristic signals with evidence = 4; emission-repair provenance present = False; counter_anchor = {'n_scored': 0, 'n_emitted': 0, 'n_abstained': 0, 'yield': 0.0}; mf n_issued = 0
- **post-path**: n_promoted=4 n_scored=4 n_abstained=4 n_emitted=0 yield=0.0 support_rate_among_emitted=0.0
- **abstention reasons**: {'pivot_absent': 4}
- **post-path mf::counter_authority_surface**: n_issued=0 n_with_empty_evidence=0 gate_pass=False
- E1 promotion exact: True — n_promoted=4 vs heuristic-signal rows with evidence=4

## Gates (frozen before execution)

| gate | all_questions |
|---|---|
| E1 promotion matches heuristic-signal count | True |
| E2 scored statuses after repair | True |
| E3 three-number publication | True |
| E4 mapping-free surface rescored | REPORTED (never pass/fail by design) |
| E5 multilingual coverage de/fr/it | True |

## Controls (all must hold)

- **C1_vendored_repair_rehash**: True — verify_vendored ok
- **C2_frozen_rubric_rehash**: True — RULES_LABEL.json sha256 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608
- **C5_anchor_classifier_nonvacuity**: True — planted row classified=True applied=True n_scored=1 reason=supported final_status=candidate-limiting
- **C4_zero_network**: True — network calls=0
- **C3_blanked_promotion_control**: True — every blanked bundle yielded n_promoted=0

## Finding (product handoff)

The emission repair promotes every heuristic signal that carries evidence (8/8/4).
The frozen abstain-and-disclose classifier then abstains on **all 20** promoted rows.
Dominant abstention reason is `pivot_absent` (15/20), then `no_intent_marker` (4) and
`no_domain_anchor` (1). The mapping-free `counter_authority_surface` gate therefore
still FAILS (`n_issued=0`) on all three languages even after the shipped emission path
runs. This is a BOUNDED NEGATIVE about the shipped path on the v3 heuristic signals,
not a harness defect: C5 proves the classifier can emit on a planted scored-status row
under frozen anchor de-kapitalverletzung (reason=`supported`).

Product handoff: either (i) regenerate served bundles so they carry
`provenance.counter_emission_repair` and re-serve under an accepted serve
recommendation (none exists today), or (ii) improve the heuristic signals'
pivot/domain anchors so the classifier can emit. Evaluation never patches product
code and never re-derives a threshold, bar, rubric or verdict contract.

## Standing posture (unchanged)

- both DO-NOT-SERVE orders stand;
- admission stays fail-closed on every probe;
- frozen absolute bars stay REPORTED-ONLY and unmet on the v3 bytes;
- `human_gate_ready` stays false; `owner_decision_required` stays false;
- no obsolete universal-174k benchmark was run.

## Claim ceiling

This instrument establishes exactly one thing: on the accepted product mount and the packet-of-record v3 bundle bytes, whether the shipped offline emission path promotes the existing heuristic signals, publishes the three numbers, and what the frozen mapping-free counter_authority_surface predicate scores on the post-path bytes. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars; it does NOT lift either DO-NOT-SERVE order; it does NOT certify packet admission; it does NOT claim the map helps a jurist; it does NOT claim the comparative map-versus-ranked-list question is non-vacuous unless n_emitted>0 is measured; it does NOT rebuild any Frontier component; it runs no obsolete universal-174k benchmark; human_gate_ready stays false.

## Provenance

- Input drift: []
- Network calls: []
- Numeric environment disclosed: yes (python 3.12.3, numpy 2.5.4)
- Result: `None`
- Test shim: `results/evaluation/orchestration/39856081942_oepb_pytest_shim.json` (8/8 PASS)
