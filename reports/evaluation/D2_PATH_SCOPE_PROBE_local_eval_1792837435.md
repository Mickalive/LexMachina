# D2 PATH-SCOPE PROBE — run local_eval_1792837435 (evaluation lane, direction v66)

**Verdict: `MIXED_OR_INCONCLUSIVE`** — neither frozen outcome branch matched; see the arm records for the exact evidence. No H0/H1 conclusion is drawn.

Claim ceiling: PATH-SCOPE DIAGNOSTIC ONLY. No frozen bar is scored, no rubric or threshold is edited, no serve verdict changes, and both DO-NOT-SERVE orders stand.

## Why this probe exists

Accepted cycle 40068038783 (frozen item-(2) re-measure) returned REPAIR_NOT_CONFIRMED: product accept 40064639100 landed the v66 P0 content-quality filter, yet the accepted head's own shipped offline slice still carries a D2_letterhead_zone verified row on `gr_gerichte_ERZ 2010 25`. The accepted state named two candidate causes (stale artifact vs slice path not routed through the filter) without discriminating them. This probe discriminates them under a freeze-first protocol.

## Controls (all must pass or the cycle makes no H0/H1 claim)

| control | passed | detail |
|---|---|---|
| C3_frozen_rubric_rehash_reported_only | PASS | True |
| C4_frozen_instrument_digest_unchanged | PASS | True |
| C5_non_vacuity_planted_letterhead_vs_mid_document | PASS | True |

Frozen rubric digests re-hashed REPORTED-ONLY: RULES_LABEL `4457e971…`, RULES_GEOMETRY `a7452748…`. Frozen predicate instrument digest `aac86527e5e54f0f`.

## ARM0 — static provenance on the sha-pinned shipped bundle

- bundle `results/product/offline_slice/20261024T024341Z/rent-default.bundle.json` sha256 `9de09a28784289de` (freeze match: True)
- bundle-level `provenance.counter_evidence_span` present: **False**
- target row `gr_gerichte_ERZ 2010 25` present: True, `counter_evidence_verified`=True
- target row frozen class: D2_letterhead_zone (offset 0)
- pipeline gate lines: [{"file": "pipeline.py", "line": 1339, "snippet": "if not fixture_generation and adversarial_retrieval:", "text": "if not fixture_generation and adversarial_retrieval:"}, {"file": "pipeline.py", "line": 1348, "snippet": "audited = apply_verified_span_selection(", "text": "audited = apply_verified_span_selection("}]
- offline slice call: [{"file": "offline_slice.py", "line": 14, "snippet": "fixture_generation=True", "text": "generative-audit fixture provider (``fixture_generation=True``), so the"}, {"file": "offline_slice.py", "line": 79, "snippet": "fixture_generation=True", "text": "initial, retrieval_mode=\"fixture\", fixture_generation=True)"}]

## ARM1 — unmodified regeneration (network trapped)

- command: `/usr/bin/python /tmp/opencode/lex_run_40070818687/product_tree/product/offline_slice.py --slug rent-default --out /tmp/lex_eval_out`
- returncode: None in Nones
- scratch key files identical to the accepted mount: {}
- regenerated bundle sha256 ``
- verified rows: None, defective: None, histogram: None
- span-seam provenance present on regenerated bundle: **None**

## ARM2 — routed-filter counterfactual (DIAGNOSTIC)

- seam applied: None (anchor profile None, frozen rules )
- target row before: class None (verified=None)
- target row after: class None (verified=None, selected=None, reason=None)
- ARM2 outcome: **None**

## Product-facing reading (evaluation does not implement the fix)

No frozen outcome branch matched. See the arm records; no repair path is recommended from this cycle's evidence.

## Numeric environment

```json
{
  "numpy": "absent",
  "platform": "linux",
  "python": "3.12.3",
  "scipy": "absent",
  "sklearn": "absent",
  "thread_env": {
    "MKL_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "OPENBLAS_NUM_THREADS": null
  }
}
```

## Non-movements

- no frozen bar, rubric, threshold or verdict contract edited or applied;
- no serve verdict re-run; both DO-NOT-SERVE orders stand; admission stays fail-closed;
- no obsolete universal-174k benchmark rerun;
- no product code modified; the seam is imported unmodified for ARM2 only;
- comparative map-vs-ranked-list half NOT scored; posture flags stay FALSE.
