# Frontier bounded-cause reproduction — run 39195084218

- Verdict: **DIVERGENCE_HEADLINE**
- Headline: C2::business-judgment-rule::de::status_ok=False,rows_ok=True,latency_ok=True
- Divergences: 17
- Cells: 15, bijection_ok: True
- C1 recovered_distinct: [] (size 9 distinct missing ids)
- C4 latency: n_over_30=10, max=83.5047721599999, sum_round3=600.568 (vs harness 600.569, vs audit 600.568)
- C5 witness cells: 13/15
- C6 FR/IT side-by-side rows: 6 (all FAIL/empty expected)

## Divergences (each is the headline, never smoothed)
- C2::business-judgment-rule::de::status_ok=False,rows_ok=True,latency_ok=True
- C2::business-judgment-rule::fr::status_ok=False,rows_ok=True,latency_ok=True
- C2::business-judgment-rule::it::status_ok=False,rows_ok=True,latency_ok=True
- C2::corporate-criminal-liability::de::status_ok=False,rows_ok=True,latency_ok=True
- C2::corporate-criminal-liability::fr::status_ok=False,rows_ok=True,latency_ok=True
- C2::corporate-criminal-liability::it::status_ok=False,rows_ok=True,latency_ok=True
- C2::petty-theft-dismissal::de::status_ok=False,rows_ok=True,latency_ok=True
- C2::petty-theft-dismissal::fr::status_ok=False,rows_ok=True,latency_ok=True
- C2::petty-theft-dismissal::it::status_ok=False,rows_ok=True,latency_ok=True
- C2::rent-default::de::status_ok=False,rows_ok=True,latency_ok=True
- C2::rent-default::fr::status_ok=False,rows_ok=True,latency_ok=True
- C2::rent-default::it::status_ok=False,rows_ok=True,latency_ok=True
- C2::de-kapitalverletzung::status_ok=True,rows_ok=False,latency_ok=True
- C2::fr-bail-entretien::status_ok=True,rows_ok=False,latency_ok=True
- C2::it-responsabilita-medica::status_ok=True,rows_ok=False,latency_ok=True
- C4::sum_round3=600.568 != harness published 600.569 (rounding-level, named)
- C5::witness_cells=13 expected 12

Claim ceiling: reproduces or fails to reproduce published numbers of an
already-accepted OUTCOME_B bounded negative against its own committed cache
and the frozen spec. No candidate is built or re-scored; no frozen bar is
met or moved; no owner question is authorised.
