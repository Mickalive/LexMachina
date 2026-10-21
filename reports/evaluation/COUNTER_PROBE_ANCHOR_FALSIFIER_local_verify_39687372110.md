# Counter-probe topic-anchor falsifier — run 39687372110-localverify

**Verdict: `COUNTER_PROBE_ANCHOR_FALSIFIED`** (exit 1)

2 of 14 measured bundles issued a counter probe whose topic anchor contains a token the product's own answer_key_terms extracts from the generative audit's redaction placeholder ['citation', 'removed', 'retrieved']. The anchor of such a probe carries no legal vocabulary of the question it is supposed to attack, so the counter-authority retrieval for that question is topic-blind. The de-redaction counterfactual restores a topical anchor, which isolates the placeholder as the cause.

## What was measured

The product's counter-authority stage anchors every issued probe on the first four key terms of the *answer prose* (`product/query/adversarial_retrieval.py::plan_adversarial_queries`, `probe_terms = key_terms[:4] + terms`). The generative audit rewrites that prose before the probes are planned, replacing ungrounded citations with the literal placeholder `[citation removed: not in retrieved set]` (`frontier/frontier-generative-audit/generative_audit/source_packing.py`).

This run reads the **recorded** probe queries of the accepted product bundles and takes their first four whitespace tokens as the anchor.

## Population

- source: `mount` (`/tmp/lex_accepted/product`)
- measurable bundles (recorded adversarial probes): **14**
- population manifest sha256: `80306fd5fe05c04e36faa5d2adf6a2b98167280a05eb7ea48ce57ec17bdf73db`

## Per-bundle result

| packet | question | lang | ph | anchor | contaminated | anchor topical | rows topical (question) | de-redacted anchor |
|---|---|---|---|---|---|---|---|---|
| 38838116453 | de-kapitalverletzung.bundle | de | 0 | `fürsorgepflicht entscheidungen arbeitgebers kapitalverletzung` | no | yes | 9/37 | `fürsorgepflicht entscheidungen arbeitgebers kapitalverletzung` |
| 38838116453 | fr-bail-entretien.bundle | fr | 0 | `termination defect court landlord` | no | **NO** | 14/40 | `termination defect court landlord` |
| 38839347028 | de-kapitalverletzung.bundle | de | 3 | `duty care employer fürsorgepflicht` | no | yes | 9/40 | `duty care employer fürsorgepflicht` |
| 38839347028 | fr-bail-entretien.bundle | fr | 0 | `landlord defects grave rent` | no | **NO** | 4/40 | `landlord defects grave rent` |
| 38839347028 | it-responsabilita-medica.bundle | it | 0 | `gerichte medico dell tribunale` | no | yes | 2/40 | `gerichte medico dell tribunale` |
| 39275520116 | de-kapitalverletzung.bundle | de | 11 | `citation removed retrieved fürsorgepflicht` | **YES** | yes | 3/8 | `fürsorgepflicht arbeitgeber nicht pflicht` |
| 39275520116 | fr-bail-entretien.bundle | fr | 0 | `défaut résiliation tribunal entretien` | no | yes | 5/8 | `défaut résiliation tribunal entretien` |
| 39275520116 | it-responsabilita-medica.bundle | it | 3 | `tribunale diligenza dell nesso` | no | yes | 6/8 | `tribunale diligenza dell nesso` |
| 39319405429 | de-kapitalverletzung.bundle | de | 9 | `citation removed retrieved nicht` | **YES** | **NO** | 3/8 | `nicht fürsorgepflicht arbeitgeber bvger` |
| 39319405429 | fr-bail-entretien.bundle | fr | 0 | `résiliation bailleur défaut entretien` | no | yes | 4/8 | `résiliation bailleur défaut entretien` |
| 39319405429 | it-responsabilita-medica.bundle | it | 4 | `dell diligenza violazione nesso` | no | yes | 3/8 | `dell diligenza violazione nesso` |
| rebuilt-39027045675 | de-kapitalverletzung.bundle | de | 3 | `duty care employer fürsorgepflicht` | no | yes | 9/40 | `duty care employer fürsorgepflicht` |
| rebuilt-39027045675 | fr-bail-entretien.bundle | fr | 0 | `landlord defects grave rent` | no | **NO** | 4/40 | `landlord defects grave rent` |
| rebuilt-39027045675 | it-responsabilita-medica.bundle | it | 0 | `gerichte medico dell tribunale` | no | yes | 2/40 | `gerichte medico dell tribunale` |

`ph` = occurrences of the redaction placeholder in the answer prose. `contaminated` = the anchor contains a token the product's own `answer_key_terms` extracts from the placeholder (`citation`, `removed`, `retrieved`). `anchor topical` = the anchor shares a content term (len >= 6, product stoplist, not a digit) with the question.

## Controls

| control | result | detail |
|---|---|---|
| `C1_replay_fidelity` | PASS | n_bundles=14, n_failed=0, n_nonuniform_anchor=0 |
| `C2_blank_prose_yields_no_plan` | PASS | n_plans_returned=0 |
| `C3_clean_bundle_not_flagged` | PASS | n_clean_bundles=8, n_clean_flagged=0 |
| `C4_de_redaction_is_a_no_op_without_the_placeholder` | PASS | n_failed=0 |
| `C5_gate_discriminates_not_merely_detects_placeholder` | PASS | n_dirty_bundles=6, n_dirty_not_flagged=4 |

## Pin discipline

- pins re-hashed BEFORE execution: 6 checks, all_ok=True
- pins re-hashed AFTER execution: 6 checks, all_ok=True

## Claim ceiling

This instrument establishes exactly one thing: on the accepted product's recorded counter-probe queries, whether the topic anchor of an issued counter probe contains a token that the product's own key-term extractor derives from the generative audit's redaction placeholder, and whether the de-redaction counterfactual changes that anchor. It is a RETRIEVAL-side construction measurement of the probe, and it is NOT a measurement of the label-emission stage (that is attributed by frontier-counter-label-emission, already cross-checked in run 39457963802 and NOT re-litigated here), NOT a measurement of counter-authority recall against any frozen known-counter set, NOT a claim about LABEL_SOUND or GEOMETRY_SOUND (both stay REPORTED-ONLY), NOT a claim about jurist usefulness or about the map, and NOT a serve recommendation. The reported adversarial-row topicality rates are OBSERVATIONAL — the counterfactual cannot re-run the live retrieval — and are reported with numerator and denominator and no threshold. It lifts no DO-NOT-SERVE order; packet admission stays fail-closed; human_gate_ready and owner_decision_required stay false. No universal-174k benchmark is run and no product source file is modified by this instrument.

## Pre-freeze disclosure

Reconnaissance preceded this freeze and is disclosed verbatim so no reader mistakes this run for a blind confirmation. WHAT I OBSERVED BEFORE FREEZING: (1) the product's redaction placeholder literal `[citation removed: not in retrieved set]` and its location in `frontier/frontier-generative-audit/generative_audit/source_packing.py`; (2) the fact that `product/query/adversarial_retrieval.py::answer_key_terms` applied to that literal yields exactly the three tokens `['citation', 'removed', 'retrieved']` (the product's own stoplist and len>=4 filter drop the rest); (3) that `product/query/pipeline.py::adversarial_retrieval_pass` plans the probes from the POST-redaction answer prose, i.e. after `run_generative_audit` has rewritten it; (4) the RECORDED probe anchor of the German bundle of packet 39319405429, namely `['citation', 'removed', 'retrieved', 'nicht']`, read out of `provenance.adversarial_retrieval.probes[0].query`, and the recorded `label_topic_terms` of that same bundle, whose first four entries are `citation, removed, retrieved, nicht`; (5) the recorded anchors of the French and Italian bundles of the same packet, `['résiliation', 'bailleur', 'défaut', 'entretien']` and `['dell', 'diligenza', 'violazione', 'nesso']`, neither of which contains a placeholder token; (6) the placeholder occurrence counts per bundle and the presence/absence of a placeholder-derived token in each anchor, for the population I had inspected at that time — namely: 39319405429 DE 9 occurrences / anchor contaminated, 39275520116 DE 11 / contaminated, 38839347028 DE 3 / anchor `['duty','care','employer','fürsorgepflicht']` NOT contaminated, 38839347028 IT 4 / NOT contaminated, and the 38838116453, 39275520116 FR/IT and 39319405429 FR/IT bundles with 0 occurrences / NOT contaminated; (7) the eight decision ids adversarially discovered in the German bundle of packet 39319405429 (bge_105 II 114, bge_117 IV 259, bge_126 III 534, bge_135 V 201, bge_136 III 583, bge_146 II 304, bge_131 III 459, zg_verwaltungsgericht_V 2012 _ 151) together with the head of their regeste, which read as a shareholder-liquidation, a rejected Untreue attempt, an Ordre public reservation, a social-benefits ruling, an arbitration clause, a possession guarantee, a social-benefits ruling and a cantonal administrative-court ruling, i.e. none of which is on the subject of the German question (employer duty of care in a capital violation). WHAT WAS NOT OBSERVED BEFORE FREEZING AND IS MEASURED FOR THE FIRST TIME HERE: the aggregate contamination count over the full 14-bundle population; the de-redaction counterfactual for every bundle; the topicality of every anchor; the adversarial-row topicality rates; the outcomes of the five non-vacuity controls; the pin/reproducibility layer; the result file and the report. The hypothesis, rule, metric, controls and exit codes are frozen exactly as written above. Nothing will be adjusted after the result is seen, and a COUNTER_PROBE_ANCHOR_NOT_FALSIFIED result would have been published in exactly the same form, with the same controls and the same disclosure.

