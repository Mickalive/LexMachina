# V3 Multilingual/Provenance Reuse Check — 39471603258

- Schema: `lex-evaluation-v3-multilingual-provenance-reuse/1`
- Direction: v61
- Verdict: **PARTIAL_MISS**
- Success rule: 3/3 qids row_ok under the same frozen pins; any miss published as-is
- All 3 qids row_ok: **False**

## Per-qid results

### de-kapitalverletzung — ❌

- SHA match: True
- Language ok (de in ['', 'de', 'fr', 'it']): True
- Source URLs valid: True
- Required fields present: False
- Provenance present: True
- Query field present: False
- Clusters present: True
- Decisions: 182, Clusters: 5
- Missing fields (sample): [{'decision_id': 'bge_126 V 75', 'field': 'language'}]
- Provenance missing fields: ['lane', 'instrument', 'counter_rule', 'layout']

### fr-bail-entretien — ❌

- SHA match: True
- Language ok (fr in ['', 'de', 'fr', 'it']): True
- Source URLs valid: True
- Required fields present: False
- Provenance present: True
- Query field present: False
- Clusters present: True
- Decisions: 185, Clusters: 3
- Missing fields (sample): [{'decision_id': 'bger_4A_173_2017', 'field': 'language'}]
- Provenance missing fields: ['lane', 'instrument', 'counter_rule', 'layout']

### it-responsabilita-medica — ❌

- SHA match: True
- Language ok (it in ['', 'de', 'fr', 'it']): True
- Source URLs valid: True
- Required fields present: False
- Provenance present: True
- Query field present: False
- Clusters present: True
- Decisions: 179, Clusters: 5
- Missing fields (sample): [{'decision_id': 'bge_130 V 229', 'field': 'language'}]
- Provenance missing fields: ['lane', 'instrument', 'counter_rule', 'layout']