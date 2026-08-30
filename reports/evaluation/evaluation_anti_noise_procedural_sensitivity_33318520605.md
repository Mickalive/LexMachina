# Evaluation — Anti-Noise Procedural-Passage Sensitivity of the Real Boilerplate Conclusion

**Lane:** evaluation
**Factory Direction version:** 10
**Run ID (proposed):** `evaluation_anti_noise_procedural_sensitivity_33318520605`
**Date:** 2026-08-30
**Evidence tier proposal:** REPRODUCED → candidate ACCEPTED (negative finding, first-class)
**Cycle status:** COMPLETED

---

## 1. Bounded question and product decision unlocked

**Question.** The corrected "real boilerplate resistance" test (`run_boilerplate_resistance_real.py`,
ACCEPTED) concluded that procedural boilerplate does NOT drive neighbor structure: **89–93% k-NN
neighbor preservation** when boilerplate is removed. That test removes mostly *header/footer/citation*
patterns — a shallow mean text reduction of only **~5.9%** (de 7.05%, fr 4.16%, it 3.12%).

The Master Prompt's **anti-noise principle** targets a broader and more consequential class than
headers/footers: *"a norm, precedent, phrase or section that is ubiquitous in a corpus should
contribute little positional information unless the decision genuinely litigates that element"* — i.e.
the **routine procedural reasoning passages** (standard admissibility / competence /
standard-of-review paragraphs) that recur across decisions sharing a chamber or procedure.

**Question (frozen before observation).** Is the accepted "boilerplate does not drive neighbors"
conclusion robust when we additionally remove routine procedural *reasoning* passages — or is it an
artifact of shallow removal, with procedural reasoning passages actually leaking into geometry?

**Product decision unlocked.** Whether the anti-noise principle is satisfied (procedural passages are
not disproportionately responsible for map neighborhoods), and hence whether the existing
boilerplate-resistance benchmark is trustworthy as a default-gating test for the product map.

## 2. Hypothesis, sample, metrics, success rule (all frozen before observation)

| Element | Frozen specification |
|---|---|
| **Hypothesis** | Accepted conclusion is FRAGILE under anti-noise targets: deep procedural-reasoning removal drops preservation by ≥ 0.08 (procedural-specific). |
| **Sample** | All 1,200 decisions in `evaluation/data/bger_expanded_1200.jsonl` (seed 42). |
| **Metric** | Mean k-NN (k=20, cosine) neighbor-set preservation between the original full-text TF-IDF+SVD (128d) embedding graph and the cleaned-text embedding graph — computed identically to the accepted real-boilerplate protocol. |
| **Removal ordering** | Procedural-norm-citation density (`art. N ... BGG/LTF/CPP/CPC/...`) + standard competence/admissibility sentence starters (DE/FR/IT) used only to *order* paragraph removal, never to grade. |
| **Tiers** | T0 shallow (accepted `remove_boilerplate`, ~6%); T15 deep procedural; T25 deep procedural; plus a **content-neutral control** removing the *same volume* of lowest-procedural (substantive) paragraphs. |
| **Success rule** | FRAGILE iff `delta = shallow − deep_procedural ≥ 0.08` **AND** `delta − control_delta > 0.03` (i.e. the drop is *specifically* procedural, not just bulk-removal volume). Otherwise ROBUST. |

The success rule requires the control condition; **without a control, a large delta cannot distinguish
procedural leakage from removal-volume confounding.** This is the adversarial rigor the lane mandates.

## 3. Results (raw: `evaluation/results/v3_boilerplate_antinoise/anti_noise_procedural_sensitivity_raw.json`)

| Condition | Actual removal (mean) | Mean k-NN preservation |
|---|---|---|
| T0 shallow (accepted reproduction) | 5.88% | **0.9325** (matches accepted 0.9325 exactly) |
| T15 deep procedural | 26.48% | 0.7095 |
| T15 CONTROL (equal-volume, substantive) | 25.44% | 0.7220 |
| T25 deep procedural | 30.24% | 0.6835 |
| T25 CONTROL (equal-volume, substantive) | 34.89% | 0.6800 |

Per-language at T25 deep: de=0.6529, fr=0.7272, it=0.8105.

### Decisive comparison (frozen success rule)

| Quantity | Value |
|---|---|
| `delta` (shallow − deep proc, T25) | 0.2490 |
| `control_delta` (shallow − equal-volume substantive) | 0.2525 |
| **procedural-specific excess** | **−0.0035** (< 0.03 ⇒ NOT specifically procedural) |
| At well-matched T15 (26.5% vs 25.4%), excess | +0.0125 (< 0.03 ⇒ NOT specifically procedural) |

## 4. Interpretation — NEGATIVE finding (first-class)

**The hypothesis is NOT supported; the accepted conclusion is ROBUST to the anti-noise concern.**

Removing ~25–30% of *routine procedural reasoning* passages drops neighbor preservation substantially
(delta ≈ 0.25), **but removing the same volume of substantive (lowest-procedural) content drops it
just as much** (control ≈ 0.25). The preservation drop at high removal is therefore a **bulk-volume /
TF-IDF+SVD re-fit artifact, not an anti-noise leak**. Procedural passages are **not** disproportionately
responsible for neighbor structure on this slice.

The initial no-control pass of this very experiment *appeared* to falsify the accepted claim
(delta=0.25 ⇒ "FRAGILE"). Adding the mandatory equal-volume control reversed that conclusion — a
concrete demonstration that the lane's control-first doctrine prevents a false negative against an
attractive, previously accepted result.

## 5. Limitations / provenance

- Result is representation-family-scoped: **TF-IDF full-text + SVD (128d)**, the exact family of the
  accepted real-boilerplate test. It does not claim anything about `center_projected`/metric-learning
  families, whose real-input transformations are not textually reconstructible on this slice
  (noted as a dependency).
- Removal is paragraph-granular; actual removal overshoots the 15%/25% targets (26–30%). Reported as actual.
- Procedural-score bias uses citation-density heuristics; it is an *ordering* device, not a grader.

## 6. Recommendation

**CONTINUE within mission (low priority) / otherwise HALT until dependencies resolve.** The anti-noise
question at slice level is now answered (robust). Recommend:
1. **KEEP** the shallow real-boilerplate protocol as canonical slice-level benchmark.
2. When the full corpus (192k) arrives, re-run this sensitivity design at corpus scale — the
   volume-vs-procedural distinction could shift at scale, and this gives a clean ahead-of-time harness.
3. No change to default product representations is warranted from this finding.

No frozen benchmark was modified. No previously accepted result was overwritten. This is an addition.
