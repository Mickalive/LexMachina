# Frontier bounded-cause reproduction — run 39195084218

- Verdict: **DIVERGENCE_HEADLINE**
- Headline: C2::de-kapitalverletzung::status_ok=True,rows_ok=False,latency_ok=True (frozen-rule-as-written: A1_candidate.n_rows is the pooled coverage set, not the expansion response; the corrected response-length reading is C3)
- Divergences: 6
- Cells: 15, bijection_ok: True
- C1 recovered_distinct: [] (size 9 distinct missing ids)
- C4 latency: n_over_30=10, max=83.5047721599999, sum_round3=600.568 (vs harness 600.569, vs audit 600.568)
- C5 witness cells: changed=13/15, added-only=12/15, union-shrink anomalies=1
- C6 FR/IT side-by-side rows: 6 (all FAIL/empty expected)

## Divergences (each is the headline, never smoothed)
- C2::de-kapitalverletzung::status_ok=True,rows_ok=False,latency_ok=True (frozen-rule-as-written: A1_candidate.n_rows is the pooled coverage set, not the expansion response; the corrected response-length reading is C3)
- C2::fr-bail-entretien::status_ok=True,rows_ok=False,latency_ok=True (frozen-rule-as-written: A1_candidate.n_rows is the pooled coverage set, not the expansion response; the corrected response-length reading is C3)
- C2::it-responsabilita-medica::status_ok=True,rows_ok=False,latency_ok=True (frozen-rule-as-written: A1_candidate.n_rows is the pooled coverage set, not the expansion response; the corrected response-length reading is C3)
- C4::sum_round3=600.568 != harness published 600.569 (rounding-level, named)
- C5::witness_cells_changed=13 expected 12 (added-only semantics yield 12)
- C5::union_shrink_anomaly::corporate-criminal-liability::fr a0=50 union=45 a1_only=0 (a set union cannot shrink)

Claim ceiling: reproduces or fails to reproduce published numbers of an
already-accepted OUTCOME_B bounded negative against its own committed cache
and the frozen spec. No candidate is built or re-scored; no frozen bar is
met or moved; no owner question is authorised.
