# How to read the FAST-MVP current-head result (run 40105794124)

Companion to the machine-generated report
`reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124.md`
and record `results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json`.
Written after execution; it adds interpretation only and changes no number.

## Headline

On the NEWEST committed slice bytes at accepted product head `8b5b08dd`
(cycle 40100397058), **4 of 5 enriched, source-valid bundles** emit exactly one
verified scored counter row whose evidence string is a **frozen content defect**:

| bundle | row | frozen defect | grounded in |
|---|---|---|---|
| rent-default 20261024T142517Z | `gr_gerichte_ERZ 2010 25` | `D2_letterhead_zone` | `full_text` offset 0 (court letterhead) |
| business-judgment-rule 20261023T121515Z | `bge_BGE_110_II_391` | `D2_letterhead_zone` | `full_text` offset 0 (`Urteilskopf`) |
| petty-theft-dismissal 20261023T121518Z | `ge_gerichte_CAPH_107_2004` | `D3_markup_residue` | `snippet` offset 0 (`<mark>`) |
| server served 20261023T224255Z | `bge_BGE_121_III_260` | `D3_markup_residue` + `D4_language_marker_mismatch` | `snippet` offset 0 |

The frozen `counter_authority_surface` gate **issues on all five enriched
bundles** (`n_issued=1`, `n_with_empty_evidence=0`) because it is deliberately
content-blind: it checks non-empty evidence, not whether the evidence is counter
reasoning. That gap is the product capability still to be fixed.

## Why the verdict is NOT `CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE`

One enriched bundle is genuinely sound: `corporate-criminal-liability`
20261023T121512Z, row `bstger_SK.2023.49`, class `COUNTER_REASONING`, zero
D1-D4 defects, grounded in `snippet` at offset 0
(`"Subsidiairement, les 4 versements suivants ..."`).

So the pre-registered H2 ("ALL verified scored rows are content-defective") is
**false**. That negative result is preserved, not explained away: the instrument
discriminated correctly instead of rubber-stamping the population. The frozen
rule therefore yields `SOUND_COUNTER_ROW_PRESENT` (exit 0), which by construction
means only "not falsified on this population". It does **not** mean the product
is serving-ready, and it does not withdraw the defects above.

## What this is and is not

- It **is** a NEW pre-registered falsification on NEW bytes (v67 item 3) with its
  own freeze-first record; it reuses the frozen D1-D4 predicates and mapping-free
  gates by import, and adds no threshold.
- It **is not** the benchmark of record. Packet-of-record `39319405429` and its
  `PRODUCT_FALSIFIED` result are untouched; no bar moved; no 174k rerun.
- It **does not** discharge v67 item (2), which remains `NOT_YET_DISCRIMINATING`
  because the product path still sets `fixture_generation=True` and bypasses the
  landed filter.
- Failure rate on this small non-random population is **4/5 enriched bundles**.
  That is a diagnostic signal, not a quality bar and not a generalisation.
- Both DO-NOT-SERVE orders stand. Posture stays fail-closed:
  `packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`,
  `ready_for_owner_session=false`.

## Product-facing next step (not an evaluation claim)

Content defects are localised and mechanical: D2 letterhead trimming for
`full_text`-grounded rows, D3 markup stripping for search-highlight residue, and
D4 marker/language routing for the German-snippet/Italian-query case. A
regenerated slice would let the same frozen instrument test whether the surface
gate stops issuing on non-reasoning text. Until then, evaluation cannot advance
item (2) without new product bytes.
