# Multilingual / provenance reuse — run 40017649220 (repair round 1)

- Schema: `lex-evaluation-multilingual-provenance-reuse-rehome/1`
- Direction: v65
- Measurement env: python 3.12.3, network=none, scratch cwd mlp_reuse_40017649220_mk2ooluz, accepted product mount present, instrument sha256 52076c974aae7199dfb990efad92aaa427487e6720402342b930cc851bda3c61
- Reused instrument: `evaluation/run_v3_multilingual_provenance_reuse.py (accepted V61-era instrument, unchanged)`
- Verdict: **PARTIAL_MISS** — {'n_qids': 3, 'n_row_ok': 0, 'all_row_ok': False}
- Byte-identical to the accepted historical record: **True** (historical record NOT written by this run: True)

## Per-qid

| qid | row_ok | language_ok | urls valid | provenance | query@provenance |
|---|---|---|---|---|---|
| de-kapitalverletzung | False | True | True | True | False |
| fr-bail-entretien | False | True | True | True | False |
| it-responsabilita-medica | False | True | True | True | False |

## Why PARTIAL_MISS is carried, not repaired

Re-execution of the accepted multilingual/provenance reuse instrument reproduces the accepted PARTIAL_MISS byte-for-byte: 0/3 qids row_ok. Every decision carries a language key with explicit null on de 50 / fr 37 / it 47 decisions (accepted D-B characterisation), the top-level query key is checked inside the provenance block and is absent there while the bundle top-level query exists, and provenance lacks lane/instrument/counter_rule/layout. This is the accepted packet-schema property, disclosed as-is; the packet bytes 32ac8126... are untouched and the accepted instrument is unchanged.

## Posture

{"human_gate_ready": false, "machine_gate_ready": false, "packet_admitted": false, "ready_for_owner_session": false, "owner_decision_required": false}

Machine record: `results/evaluation/multilingual_provenance_reuse/40017649220.json`
