v67 counter-authority falsification benchmark
packet_of_record: 39319405429
direction_version: 67
verdict: PRODUCT_FALSIFIED
exit_code: 1
questions_measured: 3
gates: 11/4/3 (total 18)
failed_gates: [{'gate': 'mf::concept_coverage::39319405429::de-kapitalverletzung', 'detail': '2/8 core concepts of the served question retrieve ZERO served rows', 'measured': {'n_rows': 182, 'concepts': ['aktive', 'fursorgepflicht', 'arbeitgebers', 'kapitalverletzung', 'eingriff', 'begrenzen', 'blossen', 'uberwachungspflicht'], 'concept_row_counts': {'aktive': 7, 'fursorgepflicht': 23, 'arbeitgebers': 29, 'kapitalverletzung': 0, 'eingriff': 11, 'begrenzen': 1, 'blossen': 4, 'uberwachungspflicht': 0}, 'concepts_with_zero_rows': ['kapitalverletzung', 'uberwachungspflicht'], 'n_concepts': 8, 'n_zero': 2}}, {'gate': 'mf::counter_authority_surface::39319405429::de-kapitalverletzung', 'detail': '0 counter-authority row(s) issued, 0 with empty evidence', 'measured': {'n_issued': 0, 'n_with_empty_evidence': 0, 'empty_evidence_examples': [], 'statuses_seen': [], 'scored_statuses_from_frozen_rubric': ['candidate-limiting', 'candidate-contrary', 'contrary_or_exception', 'limiting']}}, {'gate': 'mf::counter_authority_surface::39319405429::fr-bail-entretien', 'detail': '0 counter-authority row(s) issued, 0 with empty evidence', 'measured': {'n_issued': 0, 'n_with_empty_evidence': 0, 'empty_evidence_examples': [], 'statuses_seen': [], 'scored_statuses_from_frozen_rubric': ['candidate-limiting', 'candidate-contrary', 'contrary_or_exception', 'limiting']}}, {'gate': 'mf::counter_authority_surface::39319405429::it-responsabilita-medica', 'detail': '0 counter-authority row(s) issued, 0 with empty evidence', 'measured': {'n_issued': 0, 'n_with_empty_evidence': 0, 'empty_evidence_examples': [], 'statuses_seen': [], 'scored_statuses_from_frozen_rubric': ['candidate-limiting', 'candidate-contrary', 'contrary_or_exception', 'limiting']}}]
packet_admitted: False
human_gate_ready: False
ready_for_owner_session: False
