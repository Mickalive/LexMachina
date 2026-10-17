# frontier-rebuilt-packet-serve-audit — independent serve verdict on the REBUILT packet

**Team** `frontier-rebuilt-packet-serve-audit` · **charter v3** · **run** 39048947212 · **evidence** ACCEPTED-candidate
**Packet measured** `gate_packet/rebuilt-39027045675`, `packet.json` raw sha256 `2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170` (re-hashed before scoring; every pinned artifact verified).
**Claim-bearing artifact** `results/frontier/frontier-rebuilt-packet-serve-audit/AUDIT_RECORD.json` (sha256 `ebe0bd39…a87`). Freeze: `RULES.json`, committed `2026-10-17T16:33:35Z`, before any number was computed.

---

## Verdict — ONE machine-checked recommendation

> **SERVE RECOMMENDATION: DO-NOT-SERVE-UNCHANGED** — The rebuild does not change the serve conclusion: the frozen absolute geometry bar remains unmet on the rebuilt bytes; the accepted DO-NOT-SERVE order stands. Product-improving halves are promoted in this record and must not be explained away by the pre-rebuild baseline.

**Charter outcome (B).** The accepted DO-NOT-SERVE order on `38839347028` is **not** superseded.

Bounded causes (one per failed half):

| failed half | bounded cause |
|---|---|
| geometry | per-criterion counts `de 7 / fr 5 / it 7` of 11 — **no bundle reaches 11/11** on the frozen criteria |
| comparative | marginal discovery is **present**: issued counter authorities are absent from the initial-pool top-20 and/or invisible in the list top-20 |

Nothing is unmet on the label half, and no owner decision is required: outcome (C) requires **both** absolute bars unmet, and the label bar is met as written. This charter does **not** convert the map-versus-ranked-list choice into an owner decision.

---

## (a) LABEL — recomputed independently; the hypothesis was wrong in the rebuild's favour

| quantity | rebuilt packet | old packet `38839347028` |
|---|---|---|
| issued counter rows | 5 | 65 |
| supported under the frozen rubric | **5** | 5 |
| support rate among issued | **1.0** | 0.0769 |
| abstentions (`abstained_unevidenced`) | **60** | 0 |
| `label_gate` absolute status **as written** | **LABEL_SOUND** | LABEL_UNSOUND |
| `label_gate` regression verdict (population-pinned, n_scored=65) | **NOT_APPLICABLE** | PASS_NO_REGRESSION |
| `label_lineage_gate` verdict (population-free) | **PASS_NO_REGRESSION**, not blocking | — |

Per bundle: `de` 2/2 issued (23 abstained), `fr` **0/0 issued** (15 abstained), `it` 3/3 issued (22 abstained).

**Three things the owner must not be allowed to gloss over:**

1. The two accepted instruments disagree on the word "pass" for the same bytes. `label_gate` reads `NOT_APPLICABLE` because its verdict is pinned to a 65-row population and the rebuilt packet carries 5 scored rows; `label_lineage_gate` reads `PASS_NO_REGRESSION` because 1.0 ≥ 5/65. **NOT_APPLICABLE is not a pass**, and the lineage PASS rests on a **5-row** population — 60 rows smaller than the incumbent, with `fr-bail-entretien` contributing **zero** scored rows.
2. The charter's hypothesis predicted the population-free instrument would still emit build-blocking `FAIL_REGRESSION`. **It does not** — on these bytes it passes and does not block. The non-vacuity control shows why that is a live verdict and not a vacuous one: blanking the evidence on the same rows drives the *same* instrument to `FAIL_REGRESSION` with `gate_blocks_build = true`.
3. Soundness among *issued* labels is now perfect, but 60 of 65 candidate rows were abstained on. The bar is met as written on the population it measures; the abstention rate is the number that moved, not the soundness rate.

## (b) GEOMETRY — still far below the frozen bars, improved but not close

| bundle | rebuilt | incumbent | Δ |
|---|---|---|---|
| de-kapitalverletzung | **7** / 11 | 6 | +1 |
| fr-bail-entretien | **5** / 11 | 5 | 0 |
| it-responsabilita-medica | **7** / 11 | 5 | +2 |

`0 of 3` bundles pass all 11 criteria → frozen absolute status **GEOMETRY_UNSOUND** (reported, not enforced as a build blocker). The geometry regression verdict is `PASS_NO_REGRESSION`: nothing regressed against the incumbent.
**The size-based mega-cluster disclosure does not fire on any rebuilt bundle** (largest cluster share 0.243 / 0.226 / 0.284 against the 0.5 bar; it fired on the old `fr` bundle at 0.770). Outcome (A) SERVE requires it to fire, so it is a second independent blocker on the serve path.

## (c) COMPARATIVE — the accepted CLASSIFICATION_ONLY negative does **not** reproduce

The accepted `frontier-adversarial-discoverability` negative does not hold on the rebuilt bytes. All **5 of 5** issued counter authorities are **absent from the initial-pool top-20** *and* **invisible in the list top-20** (list positions 51–164). The map is the only channel that surfaces them; a jurist scanning the top-20 of the ranked list sees none of them. The previous negative was measured on a different population before the classifier adoption — this is the non-duplicative successor measurement, not a re-run.

## Cross-check vs Core Evaluation — ABSENT, recorded, not blocking

Core Evaluation has **not** published a re-score of these bytes at this team's hard stop. Verified across every evaluation-lane ref (`git log --all -S<sha>`, `git grep` over all refs, the four newest evaluation cycle refs) and both accepted mounts: zero evaluation-lane hits; the lane's `rebuild_preflight` legs are **synthetic `/tmp` packets built from the old packet**, and the lane's own reports state verbatim that *"no real rebuilt packet was adjudicated"*. Absence is recorded with its search basis in `AUDIT_RECORD.json :: cross_check.evaluation_search_basis`; numbers were never invented. This team's numbers are published alone. When the lane publishes, the recipe in `INTEGRATION_CONTRACT.json` produces the side-by-side table.

An independent recomputation by a separate agent using **only** the vendored accepted instruments reproduced every number here (label 5/5/1.0/60; geometry 7/5/7; mega-cluster not firing) and additionally reproduced the incumbent exactly on the old packet (65 scored / 5 supported / 0.0769, classes `OFF-DOMAIN 38, UNBACKED 22, SUPPORTED 5`; geometry 6/5/5). **No divergence.**

## Non-vacuity — proven, with one honest negative

7 instrument verdicts move under seeded controls (requirement: ≥2):

| control | moved |
|---|---|
| blank the `counter_evidence` on issued rows | `label_gate.absolute_status` LABEL_SOUND→LABEL_UNSOUND; `label_lineage_gate.regression_verdict` →FAIL_REGRESSION and **becomes build-blocking** |
| incumbent-population bytes, same instrument | `label_gate.regression_verdict` NOT_APPLICABLE→PASS_NO_REGRESSION; lineage flag re-entered |
| seeded two-bundle qid set | `geometry_gate.regression_verdict` PASS_NO_REGRESSION→NOT_APPLICABLE; lineage flag lost |
| ACCEPTED frozen geometry control (`C-charter`/`C-full`, seed 0) | **only 1 verdict flip** — reported as measured |

**Honest negative:** the accepted frozen geometry seeded control cannot flip two geometry criteria verdicts on these bytes. The rebuilt bundles sit *far* from the bars (5/11 and 7/11), so permuting cluster ids and coordinates moves 15 criterion **values** materially without crossing a bar. That is itself evidence the geometry is not marginal — and no bar, threshold or control was altered to make it look better.
Capability proven too: the resolver reaches all three frozen outcomes, including **SERVE** and **DO-NOT-SERVE-UNCHANGED**, from synthetic inputs and from the real measurement shapes.

## Reproducibility and scope

Two consecutive offline runs → byte-identical records (`ebe0bd39…a87`). `26 passed` in the deterministic test suite. Zero writes to `product/`, `evaluation/`, `results/product/`, `state/product.json`, `.github/**` (enforced by test, not just asserted). No network, no paid API, no human gate touched.

## Hard stop

Exactly one verdict cycle. If the packet is rebuilt again or a further product repair lands, that is a **new charter** against the new bytes — never a continuation of this one. If a repair supersedes `2942c3c2…` anyway, rebind by `content_sha256`, measure the accepted successor and record both; never overwrite a measured artifact.