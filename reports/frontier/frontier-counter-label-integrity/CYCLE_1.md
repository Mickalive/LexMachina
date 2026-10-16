# frontier-counter-label-integrity — charter v1, cycle 1

**VERDICT: `LABEL_UNSOUND`**
Primary support rate **0 / 7 (0.0)**. Pre-declared replication **0 / 39 (0.0)**.

This is an external, pre-registered falsification of the counter-authority labels the
accepted query map actually renders. It measures the **support of the labels as issued**
and nothing else. It never asserts that any decision IS supporting, contrary or limiting;
those remain the product's labels — reported here, not endorsed, not re-assigned.

| | |
|---|---|
| team | `frontier-counter-label-integrity` (charter v1, no prior cycles) |
| frozen rubric | `results/frontier/frontier-counter-label-integrity/RULES.json` |
| `rules_sha256` | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` |
| freeze commit | `416c2aec` @ `2026-10-16T02:22:36Z` |
| results commit | `6f4f3e0e`+ @ after the freeze (see `FREEZE_PROOF.json`) |
| report | `REPORT.json`, sha256 `e97a4e9c9377d85837309597aafd36ba9252c3f1f8859096ce219618c588de4c` |
| coverage | 9 accepted live bundles (3 primary + 6 replication), all pre-repair |
| non-vacuity | PASSED — 7/7 injected classes, 5 defect criteria exercised |

---

## 1. Why this axis decides something

The Master Prompt's non-negotiable is *"Never classify a case as supporting/contrary/limiting
unless the evidence supports that label."* Gate question 3 — *"did the map increase confidence
that contrary authority had not been hidden?"* — is answered by a jurist reading the red
counter rings and the evidence each ring cites. No measurement of label validity existed
anywhere in the accepted chain, and none existed by design: the terminated
frontier-adversarial-discoverability charter explicitly measured "yield, channel provenance,
rank placement and evidence quality, **never label correctness**". This cycle fills exactly
that cell, under a rubric frozen before any label was scored.

## 2. Method (what is frozen, what is measured)

`RULES.json` was committed **before the scorer existed** and is the only source of judgement
content: the five criteria, the five defect classes, their assignment precedence, the DE/FR/IT
lexicons, the thresholds, the minimum-population requirement, the two-tier question anchors,
the input inventory with sha256, and the injection manifest. `test_freeze.py` asserts that no
legal vocabulary is hard-coded in the harness, that the committed blob still hashes to
`rules_sha256`, and — from **git commit times, never a written `frozen_at_utc`** — that the
freeze precedes the first scored result.

A label is **SUPPORTED** only if all five hold, judged on the row's **own cited evidence**:

| | criterion | failure class |
|---|---|---|
| i | a counter-intent marker occurs **in the cited evidence string itself** | `UNBACKED` |
| ii | no polarity/role inversion in that string (appeal failed, ruling stood) | `INVERTED` |
| iii | it is not exclusively a procedural-disposal/admission construction | `BOILERPLATE-ONLY` |
| iv | a topical term of the question occurs in the cited evidence or the row title | `UNBACKED` |
| v | the row's own text touches the question's distinguishing subject; language/legal area in domain | `OFF-DOMAIN` |

Markers match **exactly** on stemmed tokens; anchors match with prefix tolerance. `cited` rows
are counted and reported but **never scored as labels** (they assert no polarity).

## 3. Primary result — the seven rows the owner would be shown

| bundle | rank | decision_id | lang | counter_reason | unc | cited evidence (verbatim, truncated) | class |
|---|---|---|---|---|---|---|---|
| de-kapitalverletzung | 13 | `zh_bezirksgericht_buelach_AH240008` | de | limiting | 0.55 | "Das von der Beklagten erlassene Impfobligatorium verstiess nicht nur gegen die Fürsorgepflicht der Arbeitgeberin…" | **OFF-DOMAIN** |
| de-kapitalverletzung | 14 | `zh_obergericht_LA190008` | de | distinguishing | 0.60 | "…er verschiedentlich seiner Arbeit fernbleiben musste, was zu seiner Kündigung führte…" | **OFF-DOMAIN** |
| de-kapitalverletzung | 15 | `zh_obergericht_LA250006` | de | limiting | 0.50 | "…lichkeitsrechte der Arbeitnehmer eingegriffen werden, je intensiver das betriebliche Interesse ist…" | **OFF-DOMAIN** |
| fr-bail-entretien | 14 | `ge_gerichte_4A_286_2015` | fr | distinguishing | **1.00** | *(empty)* | **UNBACKED** |
| it-responsabilita-medica | 4 | `ti_gerichte_13.2019.12` | it | limiting | 0.40 | "Diniego di gratuito patrocinio. Procedimento limitato per semplificazione…" | **BOILERPLATE-ONLY** |
| it-responsabilita-medica | 9 | `ti_gerichte_16.2021.24` | it | limiting | 0.40 | `cited in generated answer` | **FRAGMENT** |
| it-responsabilita-medica | 18 | `ti_gerichte_12.2025.23` | it | distinguishing | **0.95** | *(empty)* | **UNBACKED** |

**Per-class breakdown (n = 7):** `OFF-DOMAIN 3 · UNBACKED 2 · BOILERPLATE-ONLY 1 · FRAGMENT 1 · INVERTED 0 · SUPPORTED 0`
**Criterion failures:** i → 5 rows, iii → 1, iv → 1, v → 5, ii → 0.

The three German rows are labour-law decisions (vaccination mandate, absence from work,
employee rights) carrying **no capital-impairment term anywhere in the row** — not in the cited
sentence, the title or the (empty) regeste. They are plausible-looking neighbour law rendered as
a limitation of a Kapitalverletzung answer. The French and Italian empty-evidence rows carry the
highest uncertainty in their bundles (1.00 / 0.95) and `counter_confidence` 0.30 / 0.35.

**Reported separately, never scored:** 7 `cited` rows (FR 4, IT 3), every one carrying the
accepted contract's placeholder `"cited in generated answer"`.

## 4. Replication on the rest of the accepted live chain

The charter asserts the gate-packet bundles are the *only* accepted-chain material issuing
counter statuses. **The mount falsifies that**: 6 further accepted live bundles issue 39 further
counter labels. They were declared in `RULES.json` *before* scoring and scored with the
identical frozen rubric.

**0 / 39 supported.** `OFF-DOMAIN 26 · UNBACKED 10 · FRAGMENT 2 · INVERTED 1 · BOILERPLATE-ONLY 0 · SUPPORTED 0`.

* the single **INVERTED** row, `ge_gerichte_P_8300_2019`, cites "…**REJETE** Recours TF déposé…" — an appeal rejected, read as limiting authority.
* combined accepted-chain figure: **0 of 46 issued counter labels are supported by the evidence they cite.**
* language distribution of counter rows: DE 24, FR 17, IT 5 — **2 Italian counter rows exist in the entire accepted live chain** outside the medical bundle, consistent with the standing D1 finding that no Italian vocabulary is ever probed.
* ranks of counter rows span 1–34; **no supported row exists at any rank**, inside or outside the conventional top-20. The pre-registered gate's route to a positive q1/q3 (a supported counter authority below the fold) is empty.
* `counter_markers` is **absent from all 92 counter rows** at accepted head, so the product's reported marker precision is unmeasurable there. The measurable proxy is worse: in 27 of 39 replication rows, counter-intent vocabulary occurs somewhere in the row's own text but **not in the sentence the label cites** — the document-wide-vs-cited-sentence scope defect the audit described, now measured on accepted data.

## 5. Robustness — the verdict does not rest on any authored choice

| variant (pre-declared in `RULES.json`) | primary rate |
|---|---|
| primary (frozen rubric) | **0 / 7** |
| `lenient-domain-only` — criterion (v) without the authored PIVOT test | 2 / 7 (0.286) |
| `strict-no-product-vocabulary` — criterion (i) without the product's own marker words | 0 / 7 |

The lenient variant is the only one that can rescue any row, and it rescues 2 of 7 — still far
below the pre-registered soundness threshold of 1.0. **The verdict is the same under every
pre-declared interpretation.** The only interpretive choice in the whole rubric (the PIVOT
anchor) is therefore bounded, not decisive.

**Independent re-derivation.** `test_independent_recheck.py` re-implements the frozen rubric a
second time, importing nothing from the harness, and reproduces all seven verdicts and the 0/7
rate. `test_committed_report_matches_a_fresh_run` re-derives the committed `REPORT.json`
byte-for-byte; `test_identical_inputs_produce_a_byte_identical_report` proves determinism.

## 6. Non-vacuity (charter 8) — passed, not asserted

7 injected rows, each with its expected class frozen before scoring: 2 × INVERTED (FR "rejete le
recours", IT "il ricorso è stato respinto"), BOILERPLATE-ONLY (FR "contre le jugement de la
première instance…"), OFF-DOMAIN (labour-law sentence on the medical question), FRAGMENT
("darüber genaue Angaben BGE 143 III 157 S. 12"), UNBACKED (empty evidence at 1.00), plus a
SUPPORTED positive control. Result: **7/7 classes matched, 5 defect criteria exercised**
(threshold ≥ 2). Injected rows never enter a support rate or the verdict. The harness also had
to be fixed during this step: the frozen `ue→u` digraph fold was silently destroying the frozen
regex patterns (`genaue` → `genau`), which had made the FRAGMENT case undetectable. Regex
matching now runs on the diacritic-folded, non-digraph-folded string; token matching keeps the
fold. That fix changed the harness only, never `RULES.json`.

## 7. Minimum population (charter 7) — resolved, so this is a verdict, not a non-result

All 7 charter-named primary rows exist, were scored, and each carries a class, a reason code and
the frozen precedence step that fired. `INSUFFICIENT_POPULATION` is **not** returned, so product
backlog item (4) may read this as a genuine falsification — and **not** as a pass of any fix.
Two provenance caveats travel with the primary bundle: the DE bundle is itself marked
`admissible: false` (blocking finding `answer_cites_nothing`, and its answer cites zero
decisions), and the FR/IT bundles cite 4 decisions each in the answer prose while issuing only
1 and 3 counter rows respectively.

## 8. Coverage (charter 6) — baseline only, no before/after pair

**No post-repair artifact exists.** The accepted mount has neither
`results/product/adversarial_retrieval/` nor `product/query/adversarial_retrieval.py`. Every one
of the 9 scored bundles is pre-repair; this report is a **baseline only** and is never presented
as a post-repair result. The audited non-accepted run (`38828034436`, 22 of 40 new rows
unsupported) is **mechanism evidence only**: its figures appear nowhere in `REPORT.json` except
in explicit disclaimers, and `test_audited_non_accepted_numbers_are_not_used_as_a_support_rate`
fails the run if they leak into a number.

## 9. ONE bounded candidate cause

**The label survives the loss of its evidence by design, and the map's render predicate is
`counter_status` alone.** Evidence chain, all from the accepted tree:

1. `frontier/frontier-generative-audit/generative_audit/evidence.py`: `DOWNGRADED_MIN_UNCERTAINTY = 0.95`,
   documented as *"uncertainty is raised to at least `DOWNGRADED_MIN_UNCERTAINTY` and it is
   flagged `evidence_backed=False` (**the finding itself stays visible** — the product must never
   hide a possible counter-authority)"*.
2. `…/integration_contract.py::apply_to_product_bundle`: `if quote_refs: dec["counter_evidence_verified"] = rejected == 0`.
   When every quote is rejected the flag is **not written at all** — `counter_evidence` becomes `""`,
   `counter_status` stays a discoverable label.
3. `product/static/query.html:150`: `function isCounter(d){return d.counter_status && !["none","cited",…].includes(d.counter_status)}`
   — no evidence check. The ring (line 184) and the red pill (line 235) are drawn; the
   "Élément contraire" evidence line (line 238) is silently omitted.
4. Observed, accepted live chain: **36 of 46** scored counter rows carry `counter_evidence_verified: true`;
   **zero** carry `false`; the flag is **absent on exactly the 7 rows whose evidence is empty** —
   and all 7 carry `counter_uncertainty ≥ 0.95` (six at 0.95, one at 1.00).

So a jurist sees a red `candidate-limiting` ring on the map with no evidence attached, and the
uncertainty that says so (0.95/1.0) is not rendered as a warning anywhere on the card.

**This team did not test the fix and proposes none** — no lexicon, no threshold, no prompt, no
patch. `product/query/adversarial_retrieval.py`, the retention trade-off, and the disclosure
wording are Core Product's decisions (run `38831241913` is in flight on exactly this defect).

## 10. What product backlog item (4) should take from this

Adopt as input: **the accepted chain's counter labels are not currently supported by the evidence
they cite; 0 of 46 under a frozen external rubric, robust to every pre-declared variant.** Do
not read this as: any specific case is or is not limiting; or that a specific fix works (untested
here); or that the audited non-accepted run's numbers are an accepted-chain rate. A re-measurement
after a promoted repair must use **this same frozen `RULES.json`** — it is a before/after pair
waiting for its second arm.

## 11. Reproduction

```bash
export PYTHONPATH=frontier/frontier-counter-label-integrity
FROZEN=results/frontier/frontier-counter-label-integrity/RULES.json
OUT=results/frontier/frontier-counter-label-integrity

python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN --all --out $OUT
python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN --non-vacuity-only --out $OUT
python3 -m frontier_counter_label_integrity.verify_freeze --repo-root . --out $OUT
python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN \
    --bundle /tmp/lex_accepted/core/product/results/product/gate_packet/38799024807/questions/fr-bail-entretien.bundle.json \
    --out $OUT/single
python3 -m pytest tests/frontier/frontier-counter-label-integrity -q
```

Offline. No network, no provider, no paid API, no clock in any claim-bearing path.