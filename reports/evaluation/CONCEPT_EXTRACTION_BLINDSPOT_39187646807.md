# Concept-extraction blind-spot falsification - run 39187646807

- Schema: `lex-evaluation-concept-extraction-blindspot/1`
- Verdict: **BLIND_SPOT_LATENT_COUNTERFACTUAL_PROVEN**
- Falsification proven: True
- Headline: the product's stoplist filters core concepts that today have >=1 row, but a minimal counterfactual row-removal proves the disclosure stays silent while an eval-side re-count flags the concept as zero-row

## Extraction divergence (leg A)

| question | n_product | n_eval | filtered_out | added |
|---|---|---|---|---|
| de-kapitalverletzung | 6 | 8 | ['begrenzen', 'blossen'] | [] |
| fr-bail-entretien | 8 | 9 | ['resiliation', 'jusqu'] | ['decisions'] |
| it-responsabilita-medica | 8 | 13 | ['quale', 'devono', 'essere', 'dimostrati', 'escludono'] | [] |

## Active blind spot (leg B)

- none: every filtered-out concept has >=1 row on the served bundle

## Counterfactual (leg C)

| question | target | served_rows | removed | product_under_covered | eval_count_cf | proven |
|---|---|---|---|---|---|---|
| de-kapitalverletzung | begrenzen | 1 | 1 | ['kapitalverletzung', 'uberwachungspflicht'] | 0 | True |
| fr-bail-entretien | jusqu | 21 | 21 | [] | 0 | True |
| it-responsabilita-medica | escludono | 3 | 3 | [] | 0 | True |

## Divergences (each is a headline, never smoothed)

- de-kapitalverletzung::filtered_out ['begrenzen', 'blossen'] (product 6 vs eval 8)
- de-kapitalverletzung::COUNTERFACTUAL_BLIND_SPOT target=begrenzen removed=1 rows; product never emits it, eval-side re-count is 0
- fr-bail-entretien::filtered_out ['resiliation', 'jusqu'] (product 8 vs eval 9)
- fr-bail-entretien::added ['decisions'] (product-only concepts)
- fr-bail-entretien::COUNTERFACTUAL_BLIND_SPOT target=jusqu removed=21 rows; product never emits it, eval-side re-count is 0
- it-responsabilita-medica::filtered_out ['quale', 'devono', 'essere', 'dimostrati', 'escludono'] (product 8 vs eval 13)
- it-responsabilita-medica::COUNTERFACTUAL_BLIND_SPOT target=escludono removed=3 rows; product never emits it, eval-side re-count is 0

## Publishes beside the frontier handoff

the accepted DIVERGENCE_HEADLINE of delivered cycle 39180276526 (results/evaluation/frontier_recall_handoff/39180276526.json) is the naming of the concept-count divergence; this record is the MATERIALITY verdict on that divergence and never replaces it

## Claim ceiling

verdict vocabulary is BLIND_SPOT_ACTIVE / BLIND_SPOT_LATENT_COUNTERFACTUAL_PROVEN / NO_BLIND_SPOT / ENVIRONMENT. This instrument decides ONE thing: whether the product's stoplist-filtered concept extraction creates a structural blind spot in the query_concepts_under_covered disclosure. It does NOT re-score any frozen bar, does NOT re-execute the Item-2 handoff consumption (accepted at 39177046762), does NOT re-dispatch or re-score any Frontier charter, does NOT change any packet byte or admission record, does NOT meet any absolute LABEL_SOUND / GEOMETRY_SOUND bar, does NOT unblock the human gate (both accepted DO-NOT-SERVE orders stand), and authorises no owner question (owner_decision_required stays false).

