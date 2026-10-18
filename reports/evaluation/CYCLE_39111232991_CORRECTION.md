# Correction of record — cycle 39111232991, audit `CYCLE_39111232991_GATE.json`

- lane: `evaluation`
- correction run: **39113690481** (repair round 1 of rejected cycle 39111232991)
- direction version: **56**
- audit being answered: `results/audit/evaluation/CYCLE_39111232991_GATE.json` —
  `gate=REVISE`, `safe_to_integrate=false`, `required_fixes=[D1, D2, D3, D4]`
- scope: **the four required fixes and nothing else.** No frozen rubric, bar, threshold, spec,
  baseline, incumbent or accepted verdict is edited by this correction.

---

## 0. What is preserved and what is withdrawn

| artifact | disposition |
|---|---|
| `evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS.json` (sha256 `2e94d1c6…`) | **byte-unchanged.** The first freeze stays the record of what was frozen and when. |
| `results/evaluation/product_counter_recall/39111232991.json` (sha256 `09ce5725…`) | **byte-unchanged.** `FAIL_PARITY_REGRESSION`, exit 1, stands as a **harness result**. |
| `evaluation/product_counter_recall.py`, `evaluation/product_counter_recall/ACCEPTED_SERVED_ID_INDEX.json` | **byte-unchanged.** The instrument still recomputes byte-consistently offline on the vendored index; the audit verified this. |
| `reports/evaluation/CYCLE_39111232991.md` | original text **unaltered** below a dated retraction banner (sha256 before the banner `6996ba9f…`, recorded in the banner). |
| the **product-layer claim** made by that report | **RETRACTED.** Replaced by the narrower claim in §3 below. |
| the **comparator description** "the plain OpenCaseLaw top-50 it wraps" | **WITHDRAWN.** Replaced by measured numbers in §2 below. |
| `continue_recommended` | report said `false`, `state/evaluation.json` said `true`. **Both are now `false`.** |

---

## 1. D1 — the analyst mapping is subject-mismatched; the product claim is retracted

The v1 freeze declared two cells "same subject". The product's own served-question records, which
are in the accepted mount and quoted by the audit, say otherwise:

| frozen slug | served question | the product's own `legal_area` | the frozen slug is about | shared norm | shared content token |
|---|---|---|---|---|---|
| `rent-default` | `fr-bail-entretien` | *droit du bail — entretien de l'immeuble et résiliation (CP 257d ss.)* | terminating a residential lease for **rent arrears** | **257d** | `bailleur`, `résiliation` |
| `corporate-criminal-liability` | `de-kapitalverletzung` | *Arbeitsrecht — Sorgfaltspflichten des Arbeitgebers bei Kapitalverletzung (OR 321 ff., EOG)* | **Art. 102 StGB** corporate criminal liability | none (321 vs 102) | none |
| `petty-theft-dismissal` | `it-responsabilita-medica` | *responsabilità civile — responsabilità medica (c.c. 2052 ss.)* | **art. 337 StGB** petty-theft dismissal | none (2052 vs 337) | none |

The German cell is the decisive one. *Kapitalverletzung* in the served question is the
employment-law *capital-offence* sense under OR 321 ff.; in the frozen slug it is the
criminal-law sense under Art. 102 StGB. The v1 basis text read the shared German word as a shared
legal subject. It is a shared word and two different norms.

**Consequence, stated plainly.** A baseline that searched the *frozen* subject and a product bundle
that answered a *different* subject are not comparable measurements of the same retrieval step. On
such a cell, product < baseline is the expected consequence of asking two different questions.
The v1 success rule — *any* measurable cell with product < baseline ⇒ `FAIL_PARITY_REGRESSION` —
therefore cannot carry a product-layer reading. **No cell of the three is subject-matched**, so the
headline "on every measurable cell the product retrieves strictly fewer … than the plain
OpenCaseLaw result set it wraps" is **not established on any cell** and is withdrawn.

**The v1 basis texts were not edited.** The audit required it and the house rule requires it: a
frozen file is not rewritten after the fact. The retraction lives here and in the banner; the
corrected mapping is a **new freeze with a new digest**
(`evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2.json`, sha256 `8ecf0953…`, superseded by
`…_V2_1.json`, sha256 `d51bb7cd…`), which is exactly what the v1 file's own
`never_weakened_after_results` clause mandates.

**D1 is now mechanically enforceable.** `evaluation/subject_match_audit.py` computes, per cell,
`norm_axis` (from the frozen slug's own `norm_tokens` and query texts against the product's own
`question.json` subject fields) and `subject_axis` (shared content tokens), under a rule where the
**measurement can only downgrade a declared admissibility, never upgrade it**. On the committed
run: `n_admissible_cells = 0`. The catcher is mount-independent and needs no product data —
pinned by `test_a_cell_declaring_same_subject_without_a_shared_norm_is_downgraded`, which would
have failed the v1 declaration on its own.

---

## 2. D2 — the comparator was baseline ∪ counter-channel, not "the plain top-50"

The frozen baseline record carries an explicit `channel` field per query. The pool `_baseline_pool`
unions **both** channels: `3 × 50` baseline-channel rows **+** `3 × 30` counter-channel rows =
**240 rows per slug**. The counter-channel queries are limitation-token queries
(*"Art. 257d al. 2 CO résiliation abusive exception limite reprise du loyer impayé"*) — they are
themselves a counter-authority search design, not a plain natural-language query.

Measured split, `known_counter` ids, run `39113690481`
(`results/evaluation/subject_match_audit/39113690481.json`):

| slug | product hits | comparator (union, 240 rows) | **baseline channel alone (150 rows)** | comparator hits reachable **only** via the counter channel |
|---|---|---|---|---|
| `rent-default` | 1 | 3 | **1** | 2 — `bge_BGE_117_II_415`, `zh_mietgericht_MB170006-L` |
| `corporate-criminal-liability` | 0 | 4 | 3 | 1 — `so_gerichte_BKBES.2026.74` |
| `petty-theft-dismissal` | 0 | 7 | 5 | 2 — `bge_BGE_124_III_25`, `ge_gerichte_CAPH_107_2004` |

**The derived claim this licenses, and which is pinned by
`test_plain_top50_comparator_is_published_per_cell`:** on `rent-default` — the only cell with a
shared norm — under the comparator the report actually described, **product 1 ≥ baseline 1, so the
cell does not regress.** The v1 parity failure on that cell is carried *entirely* by the
limitation-token counter channel. The other two cells still fail under the plain comparator, but
they remain subject-inadmissible under D1 and therefore still cannot be claimed for the product.

The comparator was left as it was: it is the pool the accepted frozen gate
`counter::known_counter_recall::<slug>` already scores, so changing it would have changed a frozen
gate's population. It is now **named correctly** rather than changed.

---

## 3. D4 — the handoff is rescoped from a product defect to a harness result plus a successor

**Withdrawn:** *"Hand the PRODUCT_PARITY_RECALL_FALSIFIED finding to Product as a concrete P0-class
defect: the served bundle returns strictly less of the frozen controlling-authority and known
counter-authority set than the plain OpenCaseLaw pool it wraps, on all three measurable cells."*

**In its place, the supported statement:**

1. The harness proves that **under the analyst mapping as frozen**, the served packet's bundles
   contain fewer hits of the frozen id sets than the frozen baseline∪counter pools for the mapped
   slugs. That is a statement about the *harness and its mapping*, and it stands.
2. It does **not** prove that the product layer loses recall relative to the same OpenCaseLaw
   search for the same question — on any cell.
3. The successor question, unchanged in substance from §9 of the original report and now backed by
   `n_admissible_cells = 0`: either **(a)** re-derive a frozen spec against the questions the
   product actually serves — new digest, frozen before execution, never an edit — or **(b)** serve
   the frozen questions and re-measure. Neither is possible inside the accepted served packet,
   which serves no frozen slug, and neither is a lane-side dispatch.

**What the lane did instead of waiting for (a) or (b):** a falsifier that needs **no analyst mapping
at all**, and therefore cannot inherit D1. See `reports/evaluation/CYCLE_39113690481.md` §3.

---

## 4. D3 — report and state now agree

| source | before | after |
|---|---|---|
| `reports/evaluation/CYCLE_39111232991.md` §1/§9 | `continue_recommended: false` | unchanged: **false** |
| `state/evaluation.json` | `continue_recommended: true`, with a reason string that itself said "NO for another identical reconciliation cycle" | **false**, with a reason that names the retraction, the successor question and the reason no further dispatch is justified |
| `state/evaluation.json` `next_recommendation` | hand Product a P0-class defect on all three cells | the narrow harness statement + the successor question (§3) |

`human_gate_ready` stays **false**. No owner question is raised. `owner_decision_required` is
unchanged. Both accepted DO-NOT-SERVE orders stand.

---

## 5. Claim ceiling of this correction

This correction establishes exactly one new thing: **the scope of cycle 39111232991's product
claim is now measured, not asserted.** It does not prove the map is useful or useless; it does not
re-classify any decision as supporting/contrary/limiting; it does not re-score or move
`LABEL_UNSOUND` (5/65) or `GEOMETRY_UNSOUND` (0/3 bundles at 11/11); it does not lift the accepted
`DO-NOT-SERVE` order on packet `38839347028` nor `DO-NOT-SERVE-UNCHANGED` on
`rebuilt-39027045675`; it certifies admission of no packet; and `human_gate_ready` stays false.

The product-facing consequence of this cycle is **not** "your recall is worse than plain search".
It is the question-native finding in `CYCLE_39113690481.md`, which is measured on the product's own
questions and cannot be explained by any analyst mapping.