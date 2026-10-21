# Claim-artifact cross-check — run 39535657948

- Schema: `lex-evaluation-claim-artifact-crosscheck/1`
- Direction: v61
- Verdict: **CLAIM_ARTIFACT_DIVERGENCE**
- Headline: DIVERGENCE: the accepted product tree contains a claim-bearing report asserting a readiness claim the accepted product state contradicts; see diverging_rows.
- Product mount: `/tmp/lex_accepted/product` @ `5c59ba890c2bc5a7ba640eacdeb13544161a57bc`
- Rows: 28 (24 match / 3 divergence / 1 not-comparable)
- Non-vacuity all hold: True

## Diverging rows

- `claim::report_readiness_assertion::reports/product/CYCLE_39452421855.md::human_gate_ready` — product=None evaluation=None asserted=True state=False line=129
  > - ⏳ **Milestone D**: Frozen benchmark queries + human test (ready — `human_gate_ready: true`)
- `claim::report_readiness_assertion::reports/product/CYCLE_39452421855.md::human_gate_ready` — product=None evaluation=None asserted=True state=False line=137
  > No new files created — all work was **reuse and integration** of existing accepted components. The only state change is the product lane status update to `human_gate_ready=true`.
- `claim::report_readiness_assertion::reports/product/CYCLE_39452421855.md::__human_product_gate_phrase__` — product=None evaluation=None asserted=True state=False line=5
  > The query-map MVP is **functionally complete and ready for human product gate**. All core capabilities specified in `docs/product/QUERY_MAP_MVP.md` have been implemented, tested, and verified.

## Not-comparable rows

- `status::product_state_vs_evaluation_accepted::owner_decision_required` — product=None evaluation=False

## Claim ceiling

PROVENANCE / CLAIM CONFORMANCE only: verifies that the newest claim-bearing product artifacts state the same gate/admission status as the accepted Evaluation evidence and names any divergence. Re-derives no threshold, bar, rubric or verdict contract; serves no packet; lifts no DO-NOT-SERVE order; authorises no owner question; re-measures no retrieval or counter-authority recall.

Machine record: `results/evaluation/claim_artifact_crosscheck/39535657948/39535657948.json`
