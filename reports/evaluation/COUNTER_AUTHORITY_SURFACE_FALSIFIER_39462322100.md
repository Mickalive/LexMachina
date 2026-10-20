# Counter-authority surface falsifier on the packet-of-record V3 — run 39462322100

- **Schema:** `lex-evaluation-counter-authority-surface-falsifier/1`
- **Lane:** evaluation
- **Direction:** v61 (derived from `state/evaluation.json` at run time)
- **Instrument:** `evaluation/counter_authority_surface_falsifier.py`
- **Measurement reused from:** `evaluation/mapping_free_recall_falsifier.py` (accepted, run 39225862749, `PRODUCT_FALSIFIED`)
- **Combined verdict:** **PRODUCT_FALSIFIED** (exit 1)
- **Elapsed:** see machine record `elapsed_s`

## What this cycle does

The lane owns the smallest executable retrieval / counter-authority falsifier, but
it had only ever been run on the served packet `38839347028` and the rebuilt packet
`rebuilt-39027045675`. The **packet of record** is `39319405429` — the exact bytes the
accepted serve verdict, the frozen LABEL/GEOMETRY falsification battery and both
standing DO-NOT-SERVE orders are pinned to. This cycle runs the same accepted
measurement functions on V3's exact bytes for the first time.

This is a **different instrument** from the discharged `run_bar_gates` falsification
battery (run 39379766198). That battery measured the frozen LABEL and GEOMETRY gates;
this instrument measures retrieval recall and the product's counter-authority
**surface**. It is not a re-run of the discharged battery.

## Frozen population pin

| field | value |
|---|---|
| packet | `39319405429` |
| packet.json sha256 | `32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70` |
| accepted product mount | `/tmp/lex_accepted/product` @ `f463a8171cb48e8d13f9216f2069d37f3b7e0942` |
| qids | `de-kapitalverletzung`, `fr-bail-entretien`, `it-responsabilita-medica` |

## Frozen pins re-hashed before AND after execution (zero drift)

| input | sha256 |
|---|---|
| `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` | `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` |
| `evaluation/frozen_bars/RULES_LABEL.json` | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` |
| `evaluation/frozen_bars/RULES_GEOMETRY.json` | `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` |
| `evaluation/mapping_free_recall_falsifier.py` (reused measurement) | `58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302` |
| `evaluation/counter_authority_surface_falsifier.py` (this instrument) | `0d0c6827c0983a66504040c81b29e36b8ec324b8f06fa80d250f8db192547171` |

`input_drift = []` — every frozen repo input and every pinned V3 mount file
(packet.json + 3 bundles + 3 admissibility + 3 question files) re-hashed to the
frozen digests before and after execution.

## Result — the product is falsified on the packet of record

| metric | value |
|---|---|
| questions measured | 3 |
| gates | 18 (6 per question) |
| passed | 11 |
| failed | 4 |
| reported (language robustness, never a pass/fail) | 3 |
| non-vacuity controls all hold | **true** |
| slug→question pairs enumerated | 12 (4 frozen slugs × 3 questions) |
| pairs admissible (SAME_NORM AND SAME_SUBJECT_TERMS) | 1 |
| input drift | none |

### Failed gates

| gate | detail |
|---|---|
| `mf::concept_coverage::39319405429::de-kapitalverletzung` | 2/8 core concepts of the served question retrieve ZERO served rows |
| `mf::counter_authority_surface::39319405429::de-kapitalverletzung` | 0 counter-authority row(s) issued |
| `mf::counter_authority_surface::39319405429::fr-bail-entretien` | 0 counter-authority row(s) issued |
| `mf::counter_authority_surface::39319405429::it-responsabilita-medica` | 0 counter-authority row(s) issued |

The **counter-authority surface is empty on all three served questions** of the packet
of record. The product cannot surface contrary or limiting authority on the packet the
whole product verdict rests on, so the comparative half of the central product question
stays VACUOUS. This is the first time this instrument has measured V3's exact bytes.

### Concept coverage (retrieval recall)

| qid | bundle sha256 | concepts with zero rows |
|---|---|---|
| `de-kapitalverletzung` | `9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b` | `kapitalverletzung`, `uberwachungspflicht` |
| `fr-bail-entretien` | `054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b` | (none) |
| `it-responsabilita-medica` | `345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b` | (none) |

### Known counter/limiting authority recall (admissible pair only)

The single admissible pair is frozen slug `rent-default` → served question
`fr-bail-entretien` (SAME_NORM, SAME_SUBJECT_TERMS). Its known counter-authority
recall is **0/9**: none of the 9 frozen known contrary/limiting authorities
(`candidate-limiting` / `candidate-contrary`) is present in the product's retrieved
pool for the FR bail question. The other 11 slug→question pairs are
`NOT_MEASURED_ADMISSIBILITY` and contribute zero to every aggregate and claim.

### Language robustness (REPORTED, never a pass/fail)

| qid | rows | distribution |
|---|---|---|
| `de-kapitalverletzung` | 182 | de 56, fr 39, it 37, UNLABELLED 50 |
| `fr-bail-entretien` | 185 | de 68, fr 43, it 37, UNLABELLED 37 |
| `it-responsabilita-medica` | 179 | de 45, fr 50, it 50, UNLABELLED 47 |

The frozen FR/DE/IT recall defects are owned by Frontier team
`frontier-query-concept-recall` and are NOT re-scored here.

## Claim ceiling

This instrument establishes exactly one thing: on the packet-of-record V3's
(`39319405429`) exact bytes, whether the served bundles satisfy the frozen
mapping-free gates. It does NOT meet, move or re-derive the frozen absolute
LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the
accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on
rebuilt-39027045675, and it does NOT change V3's BUILT_NOT_SERVED /
WITHHELD_PENDING_SERVE status. It does NOT certify admission of any packet;
admission stays fail-closed. It does NOT claim the map helps a jurist; that remains
the human product gate's question. It does NOT build, tune, score or re-score any
candidate for any Frontier team; the accepted `frontier-counter-label-emission`
repair is never re-run here, and where its numbers touch the accepted ones they are
published BESIDE them with any divergence named as the headline. It runs no obsolete
universal-174k benchmark. `human_gate_ready` stays false.

## Fail-closed flags

`human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`,
`ready_for_owner_session=false`, `owner_decision_required=false`.

## Reproduction

```
cd /home/runner/work/LexMachina/LexMachina
python -m evaluation.counter_authority_surface_falsifier --run-id 39462322100
```

Machine record: `results/evaluation/counter_authority_surface_falsifier/39462322100.json`
Re-run is deterministic; `tests/evaluation/test_counter_authority_surface_falsifier.py`
pins the committed record's verdict, failed-gate vector, admissibility count and
zero input drift.
