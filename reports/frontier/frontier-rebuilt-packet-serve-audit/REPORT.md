# frontier-rebuilt-packet-serve-audit — independent serve verdict on the REBUILT packet

**Team** `frontier-rebuilt-packet-serve-audit` · **charter v3** · **run** 39048947212 (resume 39053132092, repair round 1) · **evidence** ACCEPTED-candidate
**Packet measured** `gate_packet/rebuilt-39027045675`, `packet.json` raw sha256 `2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170` (re-hashed before scoring; every pinned artifact verified).
**Claim-bearing artifact** `results/frontier/frontier-rebuilt-packet-serve-audit/AUDIT_RECORD.json` (sha256 `11eb58ef…b497`). Freeze: `RULES.json`, committed `2026-10-17T16:33:35Z`, before any number was computed and untouched by this repair.

**Repair provenance**: audit `CYCLE_39053132092` gate=REVISE — required fixes FIX-1..FIX-4 repaired on the SAME frozen bytes: (1) the evaluation-lane re-sweep was re-run at this final resume and Core Evaluation's real same-bytes adjudication (run 39049030442) is now consumed as the cross-check input; (2) the cross-check mapper was rebuilt on an explicit schema mapping to that record (the first-key resolver is demoted to a non-authoritative fallback); (3) the label-bar status is published **by instrument/text**; (4) absence claims are re-verified at the final resume and the falsified prior ABSENT claim is disclosed. The verdict enum is unchanged.

---

## Verdict — ONE machine-checked recommendation

> **SERVE RECOMMENDATION: DO-NOT-SERVE-UNCHANGED** — The rebuild does not change the serve conclusion: the frozen absolute geometry bar remains unmet on the rebuilt bytes; the accepted DO-NOT-SERVE order stands. Product-improving halves are promoted in this record and must not be explained away by the pre-rebuild baseline.

**Charter outcome (B).** The accepted DO-NOT-SERVE order on `38839347028` is **not** superseded.

Bounded causes (one per failed half):

| failed half | bounded cause |
|---|---|
| geometry | per-criterion counts `de 7 / fr 5 / it 7` of 11 — **no bundle reaches 11/11** on the frozen criteria |
| comparative | marginal discovery is **present**: issued counter authorities are absent from the initial-pool top-20 and/or invisible in the list top-20 |

Nothing is unmet on the label half, and no owner decision is required: outcome (C) requires **both** absolute bars unmet. The label bar is met **as written by the accepted instrument** (`label_gate` absolute `LABEL_SOUND`, population-free reading); the frozen `RULES_LABEL.json` prose verdict_rule's population-conditioned residual at `n_scored=5 < 7` is `INSUFFICIENT_POPULATION` — **disclosed, not re-derived** (see below). This charter does **not** convert the map-versus-ranked-list choice into an owner decision.

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

**Label-bar status BY INSTRUMENT/TEXT (audit FIX-3):**

| reading | source | value at n_scored=5 | governs the verdict enum |
|---|---|---|---|
| instrument reading | ACCEPTED vendored `label_gate.score_packet` AS WRITTEN; accepted `VERDICT_CONTRACT.json` restates `LABEL_SOUND := n_scored > 0 and n_supported == n_scored` (population-free) | **LABEL_SOUND** | **yes** |
| frozen rules-text residual | frozen `RULES_LABEL.json` verdict_rule (sha `4457e971…`, byte-identical, re-hashed before use) | **INSUFFICIENT_POPULATION** — *"n_scored < required_min_population_primary … This is a NON-RESULT: it must not be read as LABEL_SOUND nor as a pass of any product fix."* | no — disclosed, not re-derived |

Outcome (B) vs (C) turns on this reading; both are published in `AUDIT_RECORD.json :: half_a_label.label_bar_status_by_instrument_and_text`, and neither threshold, rubric nor verdict contract was re-derived.

**Three things the owner must not be allowed to gloss over:**

1. The two accepted instruments disagree on the word "pass" for the same bytes. `label_gate` reads `NOT_APPLICABLE` because its verdict is pinned to a 65-row population and the rebuilt packet carries 5 scored rows; `label_lineage_gate` reads `PASS_NO_REGRESSION` because 1.0 ≥ 5/65. **NOT_APPLICABLE is not a pass**, and the lineage PASS rests on a **5-row** population — 60 rows smaller than the incumbent, with `fr-bail-entretien` contributing **zero** scored rows.
2. The charter's hypothesis predicted the population-free instrument would still emit build-blocking `FAIL_REGRESSION`. **It does not** — on these bytes it passes and does not block. The non-vacuity control shows why that is a live verdict and not a vacuous one: blanking the evidence on the same rows drives the *same* instrument to `FAIL_REGRESSION` with `gate_blocks_build = true`.
3. Soundness among *issued* labels is now perfect, but 60 of 65 candidate rows were abstained on. The bar is met as written **by the accepted instrument, on the population it measures**; the abstention rate is the number that moved, not the soundness rate.

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

## Cross-check vs Core Evaluation — PRESENT and consumed; all 8 published quantities agree

Core Evaluation's re-score of these same bytes **had published** before this team's measurement: run `39049030442`, `results/evaluation/rebuilt_packet_adjudication_39049030442/39049030442_adjudication.json`, commit `27a1d309` on `origin/cycle/core/evaluation/39052366154/team` @ **2026-10-17T17:05:31Z** — before the producer's measurement commit (17:14:39Z) and before its final resume (17:39:45Z). Its `packet_json_raw_sha256` is `2942c3c2…` and its vendored `packet.json` re-hashes identically; the `fr` bundle re-hashes to the frozen pin `0b3a224e…`. The record is consumed via a byte-identical vendored copy inside this team's namespace (`frontier/frontier-rebuilt-packet-serve-audit/vendored_cross_check_input/`, sha `67656e94…ba32f`, provenance sidecar attached); this team never writes `evaluation/`.

| quantity | this team recomputed | Core Evaluation published | divergence |
|---|---|---|---|
| label.n_scored_on_issued_population | 5 | 5 | none |
| label.n_supported_among_issued | 5 | 5 | none |
| label.support_rate_among_issued | 1.0 | 1.0 | none |
| label.n_abstained | 60 | 60 | none |
| label.yield_over_classifier_population | 0.076923… | 0.076923… | none |
| geometry.de-kapitalverletzung.n_pass_of_11 | 7 | 7 | none |
| geometry.fr-bail-entretien.n_pass_of_11 | 5 | 5 | none |
| geometry.it-responsabilita-medica.n_pass_of_11 | 7 | 7 | none |
| geometry.mega_cluster_disclosure_fires | false | *Evaluation publishes no mega-cluster quantity* | **absent, not divergent** |

**Headline finding: NO divergence** between this team's recomputation and Evaluation's published numbers — on the eight published quantities above and on every instrument verdict beside them (`label_gate` absolute `LABEL_SOUND` / regression `NOT_APPLICABLE`; lineage `PASS_NO_REGRESSION`; geometry absolute `GEOMETRY_UNSOUND` / regression `PASS_NO_REGRESSION`; `n_bundles_pass_all_11 = 0`). The verdict enum is unchanged by the cross-check.

**Disclosure of the repaired defect (audit FIX-1/FIX-2):** the prior cycle claimed the re-score was absent, verified across every evaluation-lane ref. That was false: the evaluation-lane sweep was never re-run at the final resume (the record's own `detected_at_run` stayed 39048947212). The old first-key resolver also mis-read the real schema (it surfaced `fr-bail-entretien`'s *per-bundle* yield 0.0 as the packet yield and dropped five quantities to `None`); the mapper now resolves Evaluation's schema through an explicit dotted-path mapping, records which mapping produced each row, refuses a re-score that names different bytes, and records the mega row as **absent-not-divergent** because Evaluation publishes no mega quantity. The falsified claim's text was deleted from every claim-bearing artifact as ordered; its status, cause and correction are recorded in `AUDIT_RECORD.json :: cross_check.evaluation_search_basis.prior_absent_claim`.

**Process rule (audit FIX-4):** any absence or "verified across every ref" claim must be re-verified at the FINAL resume/attempt of a run before promotion; the re-run timestamp and the found record are recorded in `cross_check.evaluation_search_basis`. A future produced-work cycle shipping a stale absence claim of this same class gates **BLOCKED** under the recurring-repair rule, not a further REVISE.

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

Two consecutive offline runs → byte-identical records (`11eb58ef…b497`). `34 passed` in the deterministic test suite (four added by this repair, including the real-record explicit-mapping regression test). Zero writes to `product/`, `evaluation/`, `results/product/`, `state/product.json`, `.github/**` (enforced by test, not just asserted). No network, no paid API, no human gate touched.

## Hard stop

Exactly one verdict cycle. If the packet is rebuilt again or a further product repair lands, that is a **new charter** against the new bytes — never a continuation of this one. If a repair supersedes `2942c3c2…` anyway, rebind by `content_sha256`, measure the accepted successor and record both; never overwrite a measured artifact.
