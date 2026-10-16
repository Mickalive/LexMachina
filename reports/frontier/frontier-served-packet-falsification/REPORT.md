# Frontier: Served-Packet Falsification — Verdict Report

**Team:** frontier-served-packet-falsification  
**Charter version:** 1  
**Run:** 38877700234  
**Status:** PROMOTED (one verdict cycle complete; HARD STOP)  
**Date:** 2026-10-16  

---

## Executive verdict

**DO-NOT-SERVE this packet unchanged.**

Both halves fail their frozen bars on the exact gate packet a human owner session would render (`results/product/gate_packet/38839347028`). The counter-authority labels are **LABEL_UNSOUND** (5 of 65 supported, absolute frozen bar is 1.0). The map geometry is **FAIL** on 0 of 3 bundles under the frozen 11-criterion rule.

The D2 repair did produce a **genuine but insufficient** improvement on the label axis (0.0% → 7.69%) and improved geometry pass counts on de (5→6) and it (4→5). This improvement must not be explained away. But the absolute bars were not reached, and the French mega-cluster share **regressed** (0.557 → 0.770). An imminent owner session on this packet would consume the scarcest resource on an artifact that should not have been served unchanged.

---

## 1. Freeze byte-identity (acceptance test 1)

Both frozen RULES.json files were copied and proven byte-identical:

| Rubric | Expected sha256 | Observed | Byte-identical |
|--------|----------------|----------|----------------|
| LABEL (frontier-counter-label-integrity) | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` | same | ✅ |
| GEOMETRY (frontier-map-semantics) | `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` | same | ✅ |

No `frozen_at_utc` field was written. No threshold was introduced, restated or re-derived. The only new frozen artifact is `INPUT_LIST.json` (three bundle paths with sha256 plus the accepted baseline run ids), a precondition for reproducibility, not a benchmark.

---

## 2. Label half — LABEL support

**Population:** Every row of the served gate packet 38839347028 whose `counter_status` is in the frozen scored set `{candidate-limiting, candidate-contrary, contrary_or_exception, limiting}`. That is **65 rows** across de (25), fr (15), it (25).

**Verdict: LABEL_UNSOUND** (frozen bar: support_rate must equal 1.0; any single unsupported label makes the set unsound).

| Metric | Value |
|--------|-------|
| n_scored | 65 |
| n_supported | 5 |
| support_rate | 7.69% (5/65) |
| OFF-DOMAIN | 38 |
| UNBACKED | 22 |
| SUPPORTED | 5 |
| INVERTED | 0 |
| BOILERPLATE-ONLY | 0 |
| FRAGMENT | 0 |

### The 16 empty-evidence rows

The charter named 16 rows with empty `counter_evidence` at `counter_uncertainty` 0.95–1.0. **Each of the 16 appears individually with verdict UNBACKED, reason_code=evidence_absent.** They are never silently skipped. `counter_evidence_verified` is **absent** on exactly these 16 and **present-true** on the other 49, never false anywhere.

### Sensitivity variants

| Variant | n_supported | support_rate |
|---------|-------------|--------------|
| primary (frozen) | 5 | 7.69% |
| lenient-domain-only | 7 | 10.77% |
| strict-no-product-vocabulary | 2 | 3.08% |

All variants remain far below the 1.0 bar.

### Non-vacuity

- **Harness injection:** PASSED (7/7 injected rows match frozen expected classes; ≥2 defect criteria exercised).
- **Population non-vacuity:** 5 of 65 real served-packet rows score SUPPORTED. This is a real population result, not an injection. The harness can produce SUPPORTED on real rows; most rows simply fail.

### Per-bundle support

| Bundle | n_scored | n_supported | support_rate |
|--------|----------|-------------|--------------|
| de-kapitalverletzung | 25 | 2 | 8.0% |
| fr-bail-entretien | 15 | 0 | 0.0% |
| it-responsabilita-medica | 25 | 3 | 12.0% |

---

## 3. Geometry half — map semantics

**Verdict: FAIL (0 of 3 bundles pass all 11 frozen criteria).**

| Bundle | Pass | Overall | Largest share (size field) | Baseline share | Direction |
|--------|------|---------|---------------------------|----------------|-----------|
| de-kapitalverletzung | 6/11 | FAIL | 0.3785 | 0.4104 | IMPROVED (share) |
| fr-bail-entretien | 5/11 | FAIL | **0.7696** | 0.5573 | **REGRESSED** (share) |
| it-responsabilita-medica | 5/11 | FAIL | 0.4692 | 0.3409 | REGRESSED (share) |

### The French one-cluster map

The served French bundle renders one dominant cluster of **167 of 217 decisions (77.0%)** by the cluster `size` field, against the frozen `STRUCTURE_LARGEST` bar of **0.60**. This is **outside** the frozen rule.

Composition of the dominant cluster (read-only context, not a verdict):
- 4 French-language rows (2.4% of the cluster; the manifest's own language expectation is far higher)
- 92 German, 34 Italian, 37 language-less rows
- 12 of the French bundle's own 15 counter rows

The 50-cap on `member_ids` truncates the displayed membership to 50 (0.2304), but the `size` field correctly reports 167. Both definitions are reported side by side; the frozen bar applies to the size-field definition (what the gate renders as the cluster's displayed size).

### Un-hydrated-row ablation (side by side)

| Bundle | ARTIFACT | Shipped share | Hydrated-only share | Dominant Jaccard | Dominant unhyd fraction |
|--------|----------|---------------|---------------------|------------------|-------------------------|
| de | False | 0.3785 | 0.4431 | — | — |
| fr | **False** | 0.7696 | 0.2679 | 0.235 | 0.293 |
| it | **True** | 0.4692 | 0.3232 | — | — |

On the French bundle, ARTIFACT=False because the dominant unhydrated fraction (0.293) is below the frozen 0.40 shell-fraction clause. The hydrated-only recompute nonetheless collapses the share to 0.268 with Jaccard 0.235 — the mega-cluster is not a pure hydration artifact under the frozen predicate, but it still fails the shipped bar.

### Criteria detail (de / fr / it)

| Criterion | de | fr | it |
|-----------|----|----|-----|
| COHERENCE_QUERY_LANG | PASS | FAIL | FAIL |
| COHERENCE_QUERY_TERM | FAIL | FAIL | FAIL |
| PROJ_RANK | FAIL | PASS | PASS |
| PROJ_SPEARMAN | FAIL | FAIL | FAIL |
| PROJ_KNN10 | FAIL | FAIL | FAIL |
| STRUCTURE_LARGEST | PASS | **FAIL** | PASS |
| STRUCTURE_SEP | FAIL | FAIL | FAIL |
| LABEL_CONTENT_FRACTION | PASS | PASS | PASS |
| LABEL_JACCARD | PASS | PASS | PASS |
| OUTLIER_VALIDITY | PASS | PASS | FAIL |
| RELATIONS | PASS | PASS | PASS |

---

## 4. Before/after pair

Every baseline is marked `pre_repair=true`. No baseline is re-measured.

### Label half

| | Pre-repair baseline (run 38839354961) | Served packet (this run) | Direction | Delta |
|--|--------------------------------------|--------------------------|-----------|-------|
| Verdict | LABEL_UNSOUND | LABEL_UNSOUND | SAME | — |
| Support rate | 0.0% (0/46 accepted-chain, 0/7 primary) | **7.69% (5/65)** | **IMPROVED** | +0.077 |

**This improvement is a genuine product-improving result on the axis measured.** The classifier that produced the served rows is the repaired `product/query/adversarial_retrieval.py`; the mechanism is genuinely different code from the one scored at 0/46. It must not be explained away by the pre-repair baseline.

### Geometry half

| Bundle | Pass before | Pass after | Direction | Share before | Share after | Direction |
|--------|-------------|------------|-----------|--------------|-------------|-----------|
| de | 5 | 6 | IMPROVED | 0.410 | 0.379 | IMPROVED |
| fr | 5 | 5 | SAME | 0.557 | **0.770** | **REGRESSED** |
| it | 4 | 5 | IMPROVED | 0.341 | 0.469 | REGRESSED |

Mixed. de and it improved on pass counts. fr's mega-cluster share regressed substantially.

---

## 5. Acceptance tests

| # | Test | Result |
|---|------|--------|
| 1 | Freeze byte-identity proven | ✅ |
| 2 | Runnable offline harness | ✅ `python -m frontier_served_packet_falsification.cli` |
| 3 | Label half: 65 rows, defect classes, 16 empty rows individually, verified distribution | ✅ |
| 4 | Geometry half: 11 criteria, ablation side by side, both share definitions, 50-cap flagged | ✅ |
| 5 | BEFORE_AFTER.json pairs every number, DIRECTION+DELTA, baselines marked pre-repair | ✅ |
| 6 | Non-vacuity on population: 5 real rows reach SUPPORTED | ✅ |
| 7 | Reproducibility: two runs byte-identical (REPRODUCIBILITY.json) | ✅ |
| 8 | Zero out-of-scope writes (SCOPE_CHECK.json) | ✅ |
| 9 | CLAIM_CEILING.json + machine-checked test | ✅ |
| 10 | Audit artifact placement documented (audit job writes to its own checkout) | ✅ |

**34 tests pass (1 skipped: results/product not present in this checkout).**

---

## 6. One bounded candidate cause per failed half

**Label half (UNSOUND):** The 16 empty-evidence rows reach the render predicate with an EMPTY `counter_evidence` string at maximal uncertainty and `counter_evidence_verified` absent rather than false — the exact signature the terminated counter-label-integrity team named as its one bounded cause. The repaired classifier improved the overall rate but still emits labels with no checkable evidence sentence.

**Geometry half (FAIL):** The French bundle's one-cluster map (167/217 = 77.0%) contains only 4 French-language rows and 37 language-less rows. The dominant cluster is not a pure un-hydrated-row artifact under the frozen ARTIFACT predicate (unhydrated fraction 0.293 < 0.40), so the cause is the shipped cluster assignment itself, not hydration. The frozen `STRUCTURE_LARGEST` bar of 0.60 is outside.

---

## 7. Serve recommendation

**DO-NOT-SERVE this packet unchanged.**

The label improvement is real and must be promoted as such. But 60 of 65 issued counter labels remain unsupported under the frozen bar, including 16 with empty evidence at maximal uncertainty. The French map still renders a 77% mega-cluster. The owner's scarce attention should not be spent on this packet until the render fix and a rebuilt packet land — or until a product repair that actually reaches the frozen bars is measured under a NEW charter.

---

## Claim ceiling

This measurement is about the SUPPORT OF THE LABELS AS ISSUED and the SEMANTICS OF THE SHIPPED MAP GEOMETRY. It NEVER asserts that any specific decision IS supporting, contrary or limiting. Those remain the product's labels: reported here, not endorsed, not re-assigned. `is_outlier`, cluster placement, rank position and jurist findability are emitted as READ-ONLY CONTEXT only and are never a verdict of this charter.

---

## Artifacts

- `results/frontier/frontier-served-packet-falsification/LABEL_HALF.json` — per-row label verdicts
- `results/frontier/frontier-served-packet-falsification/GEOMETRY_HALF.json` — per-criterion geometry verdicts
- `results/frontier/frontier-served-packet-falsification/BEFORE_AFTER.json` — before/after pair
- `results/frontier/frontier-served-packet-falsification/REPRODUCIBILITY.json` — byte-identical reproduction proof
- `results/frontier/frontier-served-packet-falsification/SCOPE_CHECK.json` — write-scope proof
- `results/frontier/frontier-served-packet-falsification/FREEZE.json` — freeze byte-identity record
- `results/frontier/frontier-served-packet-falsification/INPUT_LIST.json` — the only new frozen artifact
- `results/frontier/frontier-served-packet-falsification/CLAIM_CEILING.json` — claim ceiling
- `results/frontier/frontier-served-packet-falsification/INTEGRATION_CONTRACT.json` — narrow integration contract for product
- `results/frontier/frontier-served-packet-falsification/SUMMARY.json` — machine-readable summary
- `frontier/frontier-served-packet-falsification/frontier_served_packet_falsification/` — runnable harness
- `tests/frontier/frontier-served-packet-falsification/` — tests

---

*Charter v1, one verdict cycle. HARD STOP. A second cycle under this charter is FORBIDDEN.*
