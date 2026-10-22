# Product counter-signal layer on the frozen cached sample — run 39838415410

**Verdict: `PRODUCT_COUNTER_SIGNAL_LAYER_FALSIFIED_ON_CACHED_SURFACE` (exit 1).**
7/7 controls hold; 5/7 gates pass. The failure is specific and surface-bound:
on the offline cached regeste path the shipped `adversarial_retrieval/3` signal
layer reached **0 of 14** frozen known-counter authorities, and on the marker
rule's own title+regeste+snippet surface it signalled **0** known rows versus
the marker rule's **1**. Hydrated sensitivity is positive (**3 of 5** reached
rows with product-cache full text), but hydration covered only **5 of 14**
reached rows. This report does **not** claim the live independent LLM counter
reviewer is blind.

## Why this run exists

Accepted run `39834312064` measured a frozen lexical **marker rule** and found
counter-authority discovery empty on 2/4 questions. Accepted run `39771077625`
attributed the marker blind spot but explicitly did **not** measure the shipped
product classifier. This run closes exactly that gap on the same 24 cached
OpenCaseLaw envelopes, with no new retrieval and no network.

The product's `apply_adversarial_pass` uses
`classify_against_intent(text, intent, topic_terms=...)` as an **admission
signal**; the later independent LLM reviewer is the sole writer of the
user-visible `counter_status`. A known authority that the heuristic never
signals cannot be preferentially admitted to the bounded reviewer set. That is
the product capability measured here.

## Frozen setup

| Item | Value |
|---|---|
| Run | `39838415410` |
| Direction | v62, evaluation lane |
| Product mount | `/tmp/lex_accepted/product` |
| Product head | `fe219a197e4bfb129984a732ab9adca917556eac` |
| Product module | `adversarial_retrieval/3`, sha256 `9764a37e…fd06a9` |
| Frozen spec | `evaluation/retrieval_gate/frozen_retrieval_benchmark.json`, sha256 `187b0e54…78ba72` |
| Cache | 24 raw HTTP 200 envelopes, 4 questions × FR/DE/IT × baseline/counter |
| Known-counter ids | 28 frozen; 14 reached by the frozen id matcher |
| Topic proxy | product `answer.build_answer` (`extractive_tfidf_v1`) then `bundle_topic_terms` |
| Network | zero, enforced by a fail-closed socket guard |

Freeze artifacts:
`evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_HYPOTHESIS_V1.json` (sha256
`3c57196a…a5f2c`) and
`evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_FREEZE_RECORD_V1.json` (sha256
`ce062399…db5e`).

Pre-freeze scratch reconnaissance observed the same counts and is disclosed in
the freeze record. The formal run is confirmatory, not blind; the gates remain
falsifiable and the controls are frozen.

## Result

| Question | Pool | Marker labels | Offline product signals | Languages (signal rows) | Known reached | Offline known signalled | Marker known | Same-surface product known | Hydrated / signalled |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| rent-default | 223 | 16 | 4 | FR 4 | 3/9 | 0 | 0 | 0 | 0 / 0 |
| corporate-criminal-liability | 218 | 0 | 8 | FR 3, IT 5 | 4/6 | 0 | 0 | 0 | 3 / 2 |
| business-judgment-rule | 221 | 0 | 2 | FR 2 | 1/4 | 0 | 0 | 0 | 0 / 0 |
| petty-theft-dismissal | 205 | 4 | 2 | DE 2, FR 1 | 6/9 | 0 | 1 | 0 | 2 / 1 |
| **Total** | **867** | **20** | **16** | — | **14/28** | **0** | **1** | **0** | **5 / 3** |

Language counts can sum above the signal-row count because a row may be
retrieved by more than one channel/language tag.

Aggregate:
- offline product signals: **16/867 rows**;
- same-surface optimistic signals: **48/867 rows**, but **0** on reached known authorities;
- known-counter expected/reached/offline-signalled: **28 / 14 / 0**;
- marker rule on reached known: **1** (`ar_gerichte_KG_ARGVP_2005_3462`);
- query-only topic terms also signalled **0** reached known rows;
- product-cache hydration: **5 reached rows**, **3 signalled**;
- blank-topic control: **0** signals on all rows;
- planted exception control: signals with verbatim evidence; blank topic and negative row return none.

### What the 16 signals look like

The offline signals are not confined to the question's legal domain. Examples
from the result record (surface-level mismatch, not an adjudicated legal
false-positive finding):

- `rent-default`: `bge_94 IV 28` (parking duration under the LCR) and
  `bge_103 II 321` (succession) — matched via generic topic tokens.
- `corporate-criminal-liability`: `ti_gerichte_31.2015.17` (employer liability
  under LAVS) and `bge_106 IB 357` (state liability).
- `business-judgment-rule`: `ecthr_chamber_43422_07_20190314` (ECtHR
  admissibility) and `vd_omni_GE.2020.0166` (municipal decision).
- `petty-theft-dismissal`: `bge_129 III 380` (immediate termination) and
  `ge_gerichte_C_9460_2003` (unjustified dismissal).

The extractive-answer topic vocabulary is broad (`gerichte`, `parte`,
`conditions`, `droit`, `selon`, …). This is a precision risk for the offline
proxy and a reason the live answer proxy matters. The benchmark does not score
legal precision; it scores known-authority reach.

## Hydration sensitivity

The product cache contains 609 files, 317 detail envelopes, 154 unique
decision docs, and 145 unique docs with non-empty `full_text`. Of the 14
reached known authorities, 5 have full text and 3 signal on it:

| Known authority | Question | Full text | Hydrated signal |
|---|---|---:|---|
| `bge_146 IV 68` | corporate-criminal-liability | 20,768 chars | yes, `candidate-limiting`, marker `ausnahme` |
| `bger_6B_7_2014` | corporate-criminal-liability | present | yes, `candidate-limiting` |
| `so_gerichte_STBER.2011.32` | corporate-criminal-liability | present | no |
| `bge_124 III 25` | petty-theft-dismissal | 15,556 chars | yes, `candidate-limiting`, markers `exception`/`sauf` |
| `so_gerichte_ZZ.1990.7` | petty-theft-dismissal | present | no |

The remaining 9 reached known authorities have no non-empty full text in the
product cache. The live product hydrates a bounded top set; this run cannot
simulate which rows the live top-12 hydration would choose, so the 5/14
coverage is a **cache-availability** measurement, not a live-selection
measurement. It does show that the heuristic can work when full text is
present; the gap is surface/coverage, not an absolute inability to signal.

## Diagnosis

- **14/14** reached known rows carry **zero** product `EVIDENCE_MARKERS` in the
  offline regeste text. The one marker-labelled row
  (`ar_gerichte_KG_ARGVP_2005_3462`) carries frozen limitation tokens
  `billigkeit` / `treu und glauben` but no product marker, so the product
  lexicon misses a token the frozen marker rule uses.
- Hydration changes the result materially: **3/5** hydrated reached rows
  signal. The heuristic is therefore full-text-dependent on this sample.
- The same-surface optimistic pass (title+regeste+snippet) still signals **0**
  reached known rows, so simply concatenating display fields does not close
  the gap; full text or lexicon alignment is required.
- Query-only topic terms also signal **0** reached known rows, so the negative
  offline result is not an artifact of the extractive answer's extra terms.

## Gates and controls

Passed:
- `G1_offline_product_signal_on_every_question` (4/8/2/2 > 0);
- `G3_hydrated_product_signal_reaches_known_counter_authority` (3 > 0);
- `G4_hydration_surface_available_for_g3` (5 > 0);
- `G6_every_signal_has_verbatim_evidence`;
- `G7_pool_provenance_and_duplicate_free` (pools 223/218/221/205 match accepted
  run; final pools duplicate-free).

Failed falsifiers:
- `G2_offline_product_signal_reaches_known_counter_authority` — 0/14;
- `G5_same_surface_product_signal_not_worse_than_marker_rule_on_known` — 0 vs 1.

Controls 7/7: pin re-hash, 24-envelope cache + product-cache manifest + pool
parity, product module identity, planted detection / blank-topic vacuity, zero
network, deterministic repeat, product head match. The run is therefore a
valid negative measurement, not an environment failure.

## Product implication

For the cached/offline path, the counter-admission layer is effectively empty
for known counter authority: 0/14. When full text is available it can recover
3/5, but only 5/14 reached rows have full text in the product cache. The
smallest product-side repair candidates are therefore:

1. hydrate more of the counter candidate pool before the heuristic pass, or
2. align the heuristic lexicon with the frozen limitation vocabulary (at
   minimum the `billigkeit` / `treu und glauben` class the marker rule uses),
   while keeping the verbatim-evidence gate.

This run does not prescribe which repair; the product lane owns that choice.
It also does not claim the live LLM reviewer shares this blindness.

## Claim ceiling

**Measured:** the shipped `adversarial_retrieval/3` heuristic signal layer on
the 24 frozen cached OpenCaseLaw regeste surfaces (primary offline path) and on
product-cache `full_text` where available (hydrated sensitivity), with the
product's deterministic extractive-answer topic proxy.

**Not measured:** live generative answer quality/UI; the independent LLM
counter reviewer that writes user-visible `counter_status`; live top-12
hydration selection; the full live `apply_adversarial_pass` admission path
(this run feeds every final-bundle row to the classifier, including baseline
rows and frozen counter-channel rows that the live adversarial probes may not
re-retrieve); legal correctness of frozen `known_counter_ids` beyond their
provenance; any universal-174k or external retrieval run.

## Reproduce

```bash
cd /home/runner/work/LexMachina/LexMachina
python3 evaluation/product_counter_surface_benchmark.py --run-id 39838415410
python3 -m evaluation.no_pytest_runner --run-id 39838415410 \
  --test-file tests/evaluation/test_product_counter_surface_benchmark.py \
  --out results/evaluation/orchestration/39838415410_product_counter_surface_pytest_shim.json
```

Result: `results/evaluation/product_counter_surface_benchmark/39838415410.json`
(sha256 `ed79678e48640a17f7d67f8353b5be6456007fe82cee9e92d2fcb082d7172a6d`).
Tests: **6 passed / 0 failed / 0 unsupported** under the no-pytest shim
(`SHIM_PASS`; pytest still absent in the producer image).
