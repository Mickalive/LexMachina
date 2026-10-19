# Frontier recall handoff consumption - run 39180276526

- Schema: `lex-evaluation-frontier-recall-handoff/1`
- Verdict: **DIVERGENCE_HEADLINE** (headline below)
- Headline: de-kapitalverletzung::product_side_concept_extraction lane_product=6 concepts vs lane_eval=8 concepts (subset=True)

## Coverage side by side

| question | cell | lane eval-side | lane product-side | frontier A0 | match |
|---|---|---|---|---|---|
| de-kapitalverletzung | n_rows | 214 | - | 214 | True |
| de-kapitalverletzung | under_covered_set | ['kapitalverletzung', 'uberwachungspflicht'] | ['kapitalverletzung', 'uberwachungspflicht'] | ['kapitalverletzung', 'uberwachungspflicht'] | True |
| de-kapitalverletzung | concept_list_eval_vs_frontier | ['aktive', 'fursorgepflicht', 'arbeitgebers', 'kapitalverletzung', 'eingriff', 'begrenzen', 'blossen', 'uberwachungspflicht'] | - | ['aktive', 'fursorgepflicht', 'arbeitgebers', 'kapitalverletzung', 'eingriff', 'begrenzen', 'blossen', 'uberwachungspflicht'] | True |
| de-kapitalverletzung | product_side_concepts_vs_eval_side | ['aktive', 'fursorgepflicht', 'arbeitgebers', 'kapitalverletzung', 'eingriff', 'begrenzen', 'blossen', 'uberwachungspflicht'] | ['aktive', 'fursorgepflicht', 'arbeitgebers', 'kapitalverletzung', 'eingriff', 'uberwachungspflicht'] | - | False |
| fr-bail-entretien | n_rows | 217 | - | 217 | True |
| fr-bail-entretien | under_covered_set | [] | [] | [] | True |
| fr-bail-entretien | concept_list_eval_vs_frontier | ['resiliation', 'defaut', 'entretien', 'bailleur', 'jusqu', 'distinguent', 'grave', 'simple', 'negligence'] | - | ['resiliation', 'defaut', 'entretien', 'bailleur', 'jusqu', 'distinguent', 'grave', 'simple', 'negligence'] | True |
| fr-bail-entretien | product_side_concepts_vs_eval_side | ['resiliation', 'defaut', 'entretien', 'bailleur', 'jusqu', 'distinguent', 'grave', 'simple', 'negligence'] | ['defaut', 'entretien', 'bailleur', 'decisions', 'distinguent', 'grave', 'simple', 'negligence'] | - | False |
| it-responsabilita-medica | n_rows | 211 | - | 211 | True |
| it-responsabilita-medica | under_covered_set | [] | [] | [] | True |
| it-responsabilita-medica | concept_list_eval_vs_frontier | ['responsabilita', 'medico', 'errore', 'terapeutico', 'quale', 'obbligo', 'diligenza', 'nesso', 'causale', 'devono', 'essere', 'dimostrati', 'escludono'] | - | ['responsabilita', 'medico', 'errore', 'terapeutico', 'quale', 'obbligo', 'diligenza', 'nesso', 'causale', 'devono', 'essere', 'dimostrati', 'escludono'] | True |
| it-responsabilita-medica | product_side_concepts_vs_eval_side | ['responsabilita', 'medico', 'errore', 'terapeutico', 'quale', 'obbligo', 'diligenza', 'nesso', 'causale', 'devono', 'essere', 'dimostrati', 'escludono'] | ['responsabilita', 'medico', 'errore', 'terapeutico', 'obbligo', 'diligenza', 'nesso', 'causale'] | - | False |

## Recall side by side (per-language authority hits)

| slug | lang | lane run-of-record | lane charter-cited | frontier A0 | match |
|---|---|---|---|---|---|
| corporate-criminal-liability | de | ['bge_BGE_142_IV_333', 'bger_6B_124_2016'] | ['bge_BGE_142_IV_333', 'bger_6B_124_2016'] | ['bge_BGE_142_IV_333', 'bger_6B_124_2016'] | True |
| corporate-criminal-liability | fr | [] | [] | [] | True |
| corporate-criminal-liability | it | [] | [] | [] | True |
| business-judgment-rule | de | ['bger_4A_219_2015', 'bger_4A_603_2014'] | ['bger_4A_219_2015', 'bger_4A_603_2014'] | ['bger_4A_219_2015', 'bger_4A_603_2014'] | True |
| business-judgment-rule | fr | [] | [] | [] | True |
| business-judgment-rule | it | [] | [] | [] | True |
| petty-theft-dismissal | de | ['bger_4A_177_2017'] | ['bger_4A_177_2017'] | ['bger_4A_177_2017'] | True |
| petty-theft-dismissal | fr | [] | [] | [] | True |
| petty-theft-dismissal | it | [] | [] | [] | True |
| rent-default | de | [] | [] | [] | True |
| rent-default | fr | [] | [] | [] | True |
| rent-default | it | [] | [] | [] | True |

## Frontier outcome (copied verbatim, no verdict issued here)

- outcome: `OUTCOME_B_BOUNDED_NEGATIVE`
- improved fr/it cells: 0
- reduced under-covered questions: 0
- any_vacuous: True
- per-search budget breaches: 10
- bounded cause: TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR THE OPENCASELAW RELEVANCE INDEX. Each A1 search sent a bare mined-vocabulary term list (up to 12 tokens) with no natural-language question text, while every accepted baseline query is a full sentence and returned 50/50 results. Measured on the committed cache: the de-kapitalverletzung expansion returned HTTP 200 with 0 rows, the fr-bail-entretien expansion 1 row, and the corporate-criminal-liability::fr expansion 0 rows; across all measurable (leg, language) cells the candidate-only channel recovered 0 of 9 missing frozen authority ids.

## Divergences (each is a headline, never smoothed)

- de-kapitalverletzung::product_side_concept_extraction lane_product=6 concepts vs lane_eval=8 concepts (subset=True)
- fr-bail-entretien::product_side_concept_extraction lane_product=8 concepts vs lane_eval=9 concepts (subset=False)
- it-responsabilita-medica::product_side_concept_extraction lane_product=8 concepts vs lane_eval=13 concepts (subset=True)

## Claim ceiling

verdict vocabulary is CONSUMED_NO_DIVERGENCE / DIVERGENCE_HEADLINE / ENVIRONMENT. This instrument decides ONE thing: whether the accepted frontier baseline-reproduction numbers equal this lane's own accepted numbers on the frozen cells. It does NOT re-score any frozen bar, does NOT adjudicate the frontier candidate, does NOT rebuild or re-dispatch any Frontier charter, does NOT change any packet byte or admission record, does NOT meet any absolute LABEL_SOUND / GEOMETRY_SOUND bar, does NOT unblock the human gate (both accepted DO-NOT-SERVE orders stand), and authorises no owner question (owner_decision_required stays false).

