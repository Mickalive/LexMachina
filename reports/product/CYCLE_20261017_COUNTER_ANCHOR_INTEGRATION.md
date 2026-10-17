# CYCLE 20261017 — Counter-anchor-classifier integration (v50 obligation 4)

Lane: product · factory direction: v50 · branch: `lab/product` · head: `cc719ee`

**Obligation applied:** v50 product obligation (4) — *"integrate accepted Frontier components
in the cycle they are promoted and never wait for them."* The Frontier component
`frontier-counter-anchor-classifier` (charter v1, team run 38964146628, independent audit
`CYCLE_38964146628_GATE.json` gate=PASS / safe_to_integrate=true, accept commit `d236f599`)
was promoted on 2026-10-16. This cycle integrates it into the product's label path.

**Scope:** abstain-and-disclose mode. No frozen gate, threshold, rubric or benchmark was
edited; `.github/**` untouched.

---

## What was built

### 1. Vendored the accepted component (byte-identical)

The entire `frontier_counter_anchor_classifier` package was vendored from the accepted
cycle branch `d236f599` into `product/vendored/counter_anchor_classifier/`:

| File | Source |
|------|--------|
| `counter_anchor_classifier.py` | `decide_label` + `LabelDecision` (the drop-in decision function) |
| `vendored/normalize.py` | frozen text normalization pipeline |
| `vendored/rules.py` | `FrozenRules` loader (sha256 verification) |
| `vendored/extract.py` | row extraction from product bundle |
| `vendored/rubric.py` | the frozen support rubric scorer |
| `vendored/injection.py` | non-vacuity defect injection |
| `RULES_LABEL.json` | frozen rubric (sha256 `4457e971...` verified on load) |

`PROVENANCE.json` documents the source branch, accept commit, audit gate and frozen hash.

### 2. Product-owned adapter: `product/query/counter_anchor.py`

A thin adapter that:
- loads the frozen RULES_LABEL.json and **refuses to run on sha256 mismatch**;
- resolves the bundle's query to a qid by matching the query text against the frozen
  `question_anchors[qid].question` fields (the five frozen benchmark queries);
- runs `decide_label` on every decision whose `counter_status` carries a proposed legal
  label;
- **Emitted** (cited evidence passes every frozen criterion (i)-(v)): keeps the label,
  sets `counter_uncertainty=0.2`, `counter_evidence_verified=True`.
- **Abstained** (cited evidence fails a frozen criterion): sets
  `counter_status="abstained_unevidenced"`, records `counter_reason_code` and the
  per-reason `counter_uncertainty`; the row is **kept visible** (counted, never dropped).
- **Fail-closed on unknown qid**: for queries with no authored anchor profile, every
  proposed label is abstained with reason `no_anchor_profile` (the product does not
  invent anchor profiles).
- records provenance: qid, frozen hash, n_proposed / n_emitted / n_abstained,
  `support_rate_emitted` (1.0 by construction), `yield_rate`, abstention reason
  histogram.

### 3. Pipeline wiring: `product/query/pipeline.py::enrich_query_bundle`

`apply_counter_anchor_decisions(audited)` is called after `run_adversarial_audit` (the
last label-writing step) and before geometry preservation. This ensures every proposed
counter label is verified before the bundle is returned.

### 4. Tests: `product/tests/test_counter_anchor.py` (18 tests)

- Frozen rules sha256 verified (non-vacuity: the adapter refuses on mismatch).
- qid resolution matches all five frozen benchmark queries; returns `None` for unknown.
- Pass-through when no labels are proposed.
- Fail-closed: unknown qid → every label abstained.
- Known qid: emitted labels keep their status; abstained rows keep visibility.
- Non-vacuity: deliberately mislabeled rows (empty evidence, off-domain text) are
  abstained with the correct reason codes.
- Provenance records the frozen hash and component identity.
- Abstained rows are never dropped from the decisions list.

---

## Measured evidence

### Gate packet 38839347028, bundle de-kapitalverletzung (offline replay)

| Metric | Value |
|--------|-------|
| Proposed counter labels | 25 |
| Emitted (supported) | 2 |
| Abstained (unevidenced) | 23 |
| Support rate among emitted | 1.0 (by construction) |
| Yield rate | 0.08 |
| Abstention reasons | pivot_absent 20, evidence_absent 1, no_domain_anchor 1, no_intent_marker 1 |

This is consistent with the accepted measurement (incumbent 5/65 = 0.0769 across all
three bundles): the component emits only evidence-backed labels and converts the rest
into counted abstentions.

### Live BJR recall leg (this run, with the integration active)

```
== reality leg: business-judgment-rule (mode=live) ==
   [PASS] structural
   [PASS] truth::business-judgment-rule
   [PASS] recall::citation_controlling_authority
```

The answer cites 3 of the 5 frozen direct-TF BJR authorities
(`bger_4A_219_2015`, `bger_4A_259_2016`, `bger_4A_626_2013`). The counter-anchor
integration is active: `bge_BGE_110_II_391` → `abstained_unevidenced`.

**Cause of that abstention (corrected in repair round 1).** It is the
fail-closed branch, **not** a frozen-rubric verdict. The BJR question text
matches none of the five authored `question_anchors`, so `resolve_qid` returns
`None` and the adapter abstains every proposed label with
`counter_reason_code='no_anchor_profile'` and `counter_uncertainty=1.0`
(`product/query/counter_anchor.py` lines 210-221); the frozen rubric was never
invoked on this query. This is the 3rd consecutive post-repair live run passing
the BJR recall gate.

### Test suite

- `product/tests/test_counter_anchor.py`: 18/18 pass.
- Relevant suite (counter_anchor, frontier_verdict_adoption, qmap_geometry_variant,
  fixture_replay_and_wiring, offline_slice, reality_check, query_map_mvp,
  gate_composition, answer_gap, renderer_unclustered_context): **144 pass**, zero
  regressions.
- One existing test (`test_query_map_mvp.py::test_independent_adversarial_result_patches_visible_counter_status`)
  was updated to reflect the new abstain-and-disclose behavior: it now asserts that
  proposed labels on the (non-frozen) fixture query are abstained and kept visible as
  `abstained_unevidenced`, with the counts in provenance.

---

## What is NOT claimed

- **No frozen bar is met.** The counter-label absolute bar (1.0) and the geometry
  11-criteria bar both remain unmet. The abstain-and-disclose mode raises
  `support_rate_emitted` to 1.0, but the frozen rubric scores the full 65-row
  population (5/65 = 0.0769), not just emitted labels.
- **No durable Actions run.** The BJR recall leg passes live (local evidence); the
  durable workflow recompute is still required and is Core Evaluation's lane.
- **No owner session.** `human_gate_ready=false`, `machine_gate_ready=false`. The
  standing accepted DO-NOT-SERVE order holds.
- **No gate/threshold/rubric weakening.** `.github/**` untouched; frozen gate
  functions byte-unchanged; no frozen constant modified.
- **No claim that any specific decision IS supporting, contrary or limiting.** The
  component confirms or abstains on the product's own proposed labels; it never
  assigns a polarity the row did not carry.
- **No rubric-based verification on the live BJR query.** `bge_BGE_110_II_391`
  was abstained with `counter_reason_code='no_anchor_profile'` because the BJR
  question has no authored anchor profile; the frozen rubric was **not** applied
  to it. (Correction of the prior report wording, which wrongly said "its cited
  evidence failed the frozen rubric".) The rubric-based measurement remains the
  offline gate-packet replay on `de-kapitalverletzung` above.

---

## Control-plane hardening items (recorded, not edited)

1. **durable_reality_check_trigger_gap** (carried from prior cycle): the product cannot
   trigger a durable `[reality-check]` Actions run because the core-lane integrate
   commit message never carries the marker. Recorded; `.github/**` is control-plane
   scope.

2. **Portfolio re-dispatch loop** (carried): `frontier-query-conditioned-map-geometry`
   and `frontier-counter-anchor-classifier` may re-dispatch while the portfolio reads
   `status=RUN`. The standing stop contract is: set `.status` to `TERMINATED` the
   moment a charter's stop/promote rule is met and independently accepted.

---

## Next

1. Durable Actions `[reality-check]` run and Core Evaluation's frozen-benchmark recompute
   on a promoted head (the BJR recall repair is in the promoted head; the local evidence
   is 3/3 pass).
2. The two accepted bars must be met (or an accepted bounded negative converts
   map-vs-ranked-list into ONE owner decision) before any owner session.
3. Keep every frozen gate byte-unchanged.
