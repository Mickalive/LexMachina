# Minimal Retrieval / Counter-authority Falsification Benchmark — run 39693031072

- Schema: `lex-evaluation-mapping-free-recall-falsifier/1`
- Direction: v61 (derived from state/evaluation.json at run time; factory direction v61)
- Engine: `python -m evaluation.mapping_free_recall_falsifier` invoked as the accepted entry point (full provenance layer restored, audit F5)
- Packet: 39319405429 (V3 packet-of-record exact bytes)
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: **True**
- Elapsed: timing included in machine record

## Engine verdict before drift guard

- Engine verdict before drift guard: **PRODUCT_FALSIFIED** (exit 1)
- Input drift: none (run_valid=true)

## Provenance (restored layer)

- Frozen hypothesis SHA256: engine record internal
- Freeze record SHA256: engine record internal
- Engine record: `results/evaluation/mapping_free_recall_falsifier/39693031072.json`
- Re-hash before execution: repo / mount inputs recorded
- Re-hash after execution: drift=none
- Numeric environment disclosed: yes (factory requirement 30)
- Analyst mapping not consumed: true (this module never reads the mapping file for a value; it opens it only to list which mapping blocks exist and to digest-pin the bytes)
- Retraction provenance: retracted/ correction records referenced

## Non-vacuity battery

(all five controls hold, as engine reports non_vacuity_all_hold=true)

## Claim ceiling (verbatim)

This instrument establishes exactly one thing: on the exact accepted packet bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675. It does NOT certify admission of any packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that remains the human product gate's question. It builds and re-scores no candidate for Frontier team frontier-query-concept-recall. human_gate_ready stays false. It runs no obsolete universal-174k geometry benchmark.

## Failed gates

The following mapping-free gates failed on the exact accepted bytes, falsifying the product's retrieval/authority discovery capability:

- `mf::concept_coverage::39319405429::de-kapitalverletzung` — 0 core concepts retrieved for de-kapitalverletzung question
- `mf::counter_authority_surface::39319405429::de-kapitalverletzung` — 0 counter-authority rows issued under frozen rubric for de bundle
- `mf::counter_authority_surface::39319405429::fr-bail-entretien` — 0 counter-authority rows issued under frozen rubric for fr bundle
- `mf::counter_authority_surface::39319405429::it-responsabilita-medica` — 0 counter-authority rows issued under frozen rubric for it bundle

## Reason

On the V3 packet-of-record exact bytes (39319405429), the product's mapping-free retrieval and counter-authority surface gates fail on all three served questions (German, French, Italian bundles). The counter-authority surface issues confirm that the product cannot surface contrary/limiting authority on the exact V3 bytes. All five non-vacuity controls pass. This is NOT a re-litigation of accepted evidence: the accepted counter-emission attribution covers cause classes c_HYDRATION and e_EMISSION_WRITER_ABORT only (LABEL-side), and the accepted cross-check 39457963802 compares the label stage only (ZERO_DIVERGENCE over 96 comparable quantities). Neither looks at mapping-free retrieval/CA surface. This is the retrieval-side measurement of the counter probe on the V3 packet. No universal-174k benchmark was run.

## Product handoff (for product lane)

A PRODUCT defect, not an evaluation defect; the fix belongs to the product lane and this lane's write scope forbids touching product code. Either (a) exclude the redaction placeholder from the probe key terms in product/query/adversarial_retrieval.py (strip REDACTION_PLACEHOLDER from the prose before answer_key_terms, or exclude the placeholder's tokens from the candidate set) — the smaller change, and it keeps the audit's redaction intact — or (b) plan the probes from the PRE-redaction prose by reordering product/query/pipeline.py so adversarial_retrieval_pass sees the prose the answer was written from. Option (b) alone does not help if the answer itself lacks legal vocabulary, so (a) is the recommended remedy.

## Machine record

`results/evaluation/mapping_free_recall_falsifier/39693031072.json`

Report: `RETRIEVAL_CA_BENCHMARK_39693031072.md`