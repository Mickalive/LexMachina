# Retrieval-instrument falsification - run 39180276526

- Schema: `lex-evaluation-retrieval-instrument-falsification/1`
- Verdict: **REPRODUCTION_MATCHES_AND_FALSIFICATION_PROVEN** (exit implied by verdict)
- Headline: the frozen retrieval instrument reproduces the accepted run of record and both deliberately regressed multilingual/provenance records make it fail exactly where expected
- Reproduction matches: True
- Falsification proven: True

## Legs

### reproduction - OK

- counts: {'n_gates': 40, 'n_passed': 24, 'n_failed': 10, 'n_not_measurable': 6, 'overall_pass': False}
- expected_counts: {'n_gates': 40, 'n_passed': 24, 'n_failed': 10, 'n_not_measurable': 6, 'overall_pass': False}
- failed_gates: ['authority::baseline_lang_recall::business-judgment-rule::fr', 'authority::baseline_lang_recall::business-judgment-rule::it', 'authority::baseline_lang_recall::corporate-criminal-liability::fr', 'authority::baseline_lang_recall::corporate-criminal-liability::it', 'authority::baseline_lang_recall::petty-theft-dismissal::fr', 'authority::baseline_lang_recall::petty-theft-dismissal::it', 'counter::limiting_marker_verified::corporate-criminal-liability', 'duplicate::unique_ids::business-judgment-rule', 'duplicate::unique_ids::corporate-criminal-liability', 'duplicate::unique_ids::petty-theft-dismissal']
- failed_set_matches: True
- not_measurable_gates: ['authority::baseline_lang_recall::rent-default::de', 'authority::baseline_lang_recall::rent-default::fr', 'authority::baseline_lang_recall::rent-default::it', 'authority::baseline_recall::rent-default', 'latency::full_pass_under_budget', 'latency::search_under_budget']
- not_measurable_set_matches: True

### hostile_blank - OK

- query_key: baseline:corporate-criminal-liability:de
- queries_touched: 1
- added_failed_gates: ['authority::baseline_lang_recall::corporate-criminal-liability::de', 'authority::baseline_recall::corporate-criminal-liability']
- expected_added: ['authority::baseline_lang_recall::corporate-criminal-liability::de', 'authority::baseline_recall::corporate-criminal-liability']
- lost_failed_gates: []
- cell_specificity: {'authority::baseline_lang_recall::business-judgment-rule::de': True, 'authority::baseline_lang_recall::petty-theft-dismissal::de': True}

### hostile_duplicate - OK

- query_key: counter:rent-default:fr
- queries_touched: 1
- added_failed_gates: ['duplicate::unique_ids::rent-default']
- expected_added: ['duplicate::unique_ids::rent-default']
- lost_failed_gates: []

## Absolute-status note

the accepted reading itself is overall_pass=false with 10 failed gates (6 fr/it authority-recall cells, 3 duplicate cells, 1 limiting-marker cell); it is preserved verbatim and this instrument claims no absolute retrieval bar is met

## Claim ceiling

verdict vocabulary is REPRODUCTION_MATCHES_AND_FALSIFICATION_PROVEN / FALSIFICATION_OR_REPRODUCTION_FAILURE / ENVIRONMENT. This instrument decides ONE thing: whether the frozen retrieval instrument reproduces the accepted run of record and can fail two deliberately regressed multilingual retrieval records. It does NOT re-run any live search, does NOT change the accepted record, does NOT re-score any label or geometry bar, does NOT claim the absolute retrieval bars are met (the accepted reading itself is overall_pass=false with 10 failed gates, preserved verbatim), does NOT unblock the human gate, and authorises no owner question.

