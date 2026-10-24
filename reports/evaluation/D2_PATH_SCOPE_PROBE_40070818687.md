# D2 PATH-SCOPE PROBE — run 40070818687 (evaluation lane, direction v66)

**Verdict: `PATH_SCOPE_RESIDUAL`** — H1 supported: the regenerated bundle reproduces the letterhead evidence and the span seam (which hosts the accepted content filter) still never ran on this path. The residual D2 is structural path scope, not staleness; regenerating the artifact alone cannot clear it. ARM2 shows what the filter would do if routed: FILTER_LEAVES_ROW.

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

- command: `/usr/bin/python3 /tmp/opencode/lex_run_40070818687/product_tree/product/offline_slice.py --slug rent-default --out /tmp/opencode/lex_run_40070818687/arm1_slice_exec3`
- returncode: 0 in 1.347s
- scratch key files identical to the accepted mount: {'product/offline_slice.py': True, 'product/query/pipeline.py': True, 'product/query/counter_evidence_span.py': True}
- regenerated bundle sha256 `b115243227581449`
- verified rows: 1, defective: 1, histogram: {'D2_letterhead_zone': 1}
- span-seam provenance present on regenerated bundle: **False**

## ARM2 — routed-filter counterfactual (DIAGNOSTIC)

- seam applied: True (anchor profile fr-bail-entretien, frozen rules 4457e971df3dc5d1)
- target row before: class D2_letterhead_zone (verified=True)
- target row after: class D2_letterhead_zone (verified=True, selected=False, reason=pivot_absent)
- ARM2 outcome: **FILTER_LEAVES_ROW**

## Product-facing reading (evaluation does not implement the fix)

The shipped offline/server slice's counter-evidence emission path never reaches the accepted content filter: `product/offline_slice.py` enriches with fixture_generation=True and `product/query/pipeline.py` gates apply_verified_span_selection behind `not fixture_generation and adversarial_retrieval`, so the fixture path emits letterhead evidence with counter_evidence_verified=True and no span record. ARM2 refinement: merely routing the seam onto this path would NOT by itself clear this row — the frozen gate abstained on it (reason `pivot_absent`, anchor profile `fr-bail-entretien`, qid=None) and the seam's accepted abstention semantics leave the incumbent verified evidence untouched counter_evidence_span.py writes counter fields only on selected=True). The residual is therefore emitted by the fixture path's own pre-verified marking. Minimal product repair candidates, in order of cost: (a) run the content filter over the fixture path's incumbent evidence (never the frozen gate) so letterhead spans are never marked verified on that path, or (b) regenerate slice bundles through the non-fixture audit path where the seam confirms-or-abstains before a row is marked verified. Regenerating slice artifacts WITHOUT changing the path cannot clear D2. Core Product owns the implementation; this lane only measures.

## Numeric environment

```json
{
  "numpy": "2.5.4",
  "platform": "linux",
  "python": "3.12.3",
  "scipy": "1.18.1",
  "sklearn": "1.9.1",
  "thread_env": {
    "MKL_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "OPENBLAS_NUM_THREADS": null
  }
}
```

## Reproducibility disclosure

The frozen instrument was executed TWICE on this run (two independent
regenerations of the offline slice, same scratch copy of product head
`3495c1336`). Machine artifact:
`results/evaluation/d2_path_scope_probe/40070818687_stability.json`.

- every field the H0/H1 verdict depends on is **identical** across the two
  executions (`discrimination_fields_identical: true`): verdict, D2 count,
  defective decision ids, defect histogram, target evidence sha256, frozen
  class before/after, span reason code, ARM2 outcome, anchor profile, ARM0
  gate line numbers;
- the regenerated bundle's full sha256 DIFFERS between executions because the
  product bundle embeds generation timestamps/latency fields. Per factory-wide
  requirement 30 no unconditional cross-machine byte-identity claim is made;
  the discrimination fields, not the byte identity, are what this probe pins.

## Cycle deliverables

- instrument: `evaluation/d2_path_scope_probe.py`;
- unit tests: `tests/evaluation/test_d2_path_scope_probe.py` (7/7 PASS,
  synthetic fixtures only: decision-rule branches, controls, line-finder);
- machine artifact: `results/evaluation/d2_path_scope_probe/40070818687.json`;
- stability artifact: `results/evaluation/d2_path_scope_probe/40070818687_stability.json`;
- freeze-first records: `evaluation/D2_PATH_SCOPE_PROBE_40070818687_{HYPOTHESIS,FREEZE}_V1.json`,
  committed BEFORE the first claim-bearing execution.

## Non-movements

- no frozen bar, rubric, threshold or verdict contract edited or applied;
- no serve verdict re-run; both DO-NOT-SERVE orders stand; admission stays fail-closed;
- no obsolete universal-174k benchmark rerun;
- no product code modified; the seam is imported unmodified for ARM2 only;
- comparative map-vs-ranked-list half NOT scored; posture flags stay FALSE.
