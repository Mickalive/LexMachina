# frontier-concept-seed-recall — charter v1, run 39237146851

**OUTCOME_A (component).** One narrow, positive, reproducible retrieval result,
published beside the accepted predecessor's bounded negative and never in place
of it.

> A natural-language concept-seeded search, issued as one extra full-sentence
> variant per under-covered core concept, **recovered one of the nine frozen
> controlling-authority ids** the accepted benchmark records as missing:
> `bge_BGE_142_IV_333` on `corporate-criminal-liability::fr`, taking that cell
> from **0/2 to 1/2**. **Zero frozen gates regressed.** The coverage axis did
> **not** move: `kapitalverletzung` and `uberwachungspflicht` are still
> uncovered on `de-kapitalverletzung`.

Claim ceiling in force throughout: no artifact here asserts that a map helps a
jurist, that any authority is absent from the corpus, that any frozen bar is met
or moved, or that any packet is fit to serve. Usefulness remains the human
product gate's question; admission remains fail-closed.

---

## 1. What was tested, and why it is not the closed layer

The accepted OUTCOME_B record of `frontier-query-concept-recall` named one
bounded cause:

> "TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR THE OPENCASELAW RELEVANCE
> INDEX"

That layer issued bare mined-term lists of ≤ 12 tokens with no natural-language
question text. It is **closed, not re-run, not re-scored and not improved here**.
Its A1 numbers appear in this record only as a historical comparator.

This charter tested the input class the cause names as untested: **full-sentence
natural-language variants that embed the question's own frozen under-covered core
concepts as phrased text.**

| | predecessor (closed) | this run |
|---|---|---|
| query shape | ≤ 12 bare mined tokens | full sentence + concept apposition |
| `de-kapitalverletzung` added search | HTTP 200, **0 rows** | HTTP 200, **50 rows**, both concepts |
| frozen authority ids recovered | **0** of 9 | **1** of 9 |
| frozen gates regressed | 0 | 0 |

## 2. The frozen arm (template NLCS-1)

Deterministic, offline, zero model calls, zero paid API. For a unit whose
question text is an accepted text in language *L* and whose under-covered concept
is *c*:

```
V = <the accepted question sentence>
  + JOIN[L] + <c's own surface form> + ( <c's morphological variants> ) + TAIL[L]
```

Example, `de-kapitalverletzung`, concept `uberwachungspflicht`:

```
Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: wie weit
geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn gegenüber
einer blossen Überwachungspflicht? – Überwachungspflicht (Überwachungspflichten,
Ueberwachungspflicht, Uberwachungspflicht)?
```

Every word in that string is either the question's own accepted text or the
concept's own morphological forms. No synonym, no translation, no paraphrase, no
corpus mining. A variant is **never** emitted for a language with no accepted
question text — which is why `fr-bail-entretien` and `it-responsabilita-medica`
fired **zero** added searches (their retrieved sets already cover all their
concepts).

**9 units, 7 targeted, 14 frozen variant strings**, all committed before the
first search.

## 3. Freeze ordering (acceptance test 1)

Recomputed from **real git commit times**, not from a hand-written timestamp
(`results/frontier/frontier-concept-seed-recall/freeze_ordering.json`):

| commit | time (UTC) | RULES.json sha256 |
|---|---|---|
| `3ddae8e` freeze | 2026-10-19T10:35:21Z | `c1fd517e…` |
| `f083f16` amendment **A2** (latency budget scope), still pre-measurement | 2026-10-19T10:38:06Z | `311ac6d0…` |
| `c3467a8` **first commit carrying a measurement** | 2026-10-19T10:43:51Z | — |

Margin from the **final** freeze commit to the first measurement: **345 s**.
The rules blob at `f083f16`, at `HEAD` and on disk are byte-identical
(`311ac6d0913f22d3…`), so the frozen bytes were not touched after the first
candidate result existed. The frozen bytes were not touched after the first candidate
result existed. Two amendments are declared in-file with what/why/direction; both
were made before any search.

## 4. Acceptance test (2) — the accepted numbers were reproduced FIRST

Recomputed from accepted artefacts only, **before** any new measurement, with
zero network calls. A non-reproduction would have been the headline and would
have ended the run.

| accepted number | recomputed | verdict |
|---|---|---|
| `de-kapitalverletzung` coverage, 214 rows, `kapitalverletzung` 0, `uberwachungspflicht` 0 | identical, concept lists and counts | **reproduced** |
| predecessor `de` added search | HTTP 200, **0 rows** | **reproduced** |
| `improved_fr_it_cells = 0` | 0, recomputed with the accepted matcher against the predecessor's own committed envelopes | **reproduced** |
| `reduced_under_covered_questions = 0` | 0, recomputed from the accepted bundles + the predecessor's envelopes | **reproduced** |

`baseline_reproduction_39237146851.json` carries the full side-by-side.

## 5. Head-to-head (acceptance test 4)

Identical endpoint, identical parameters (`limit=50`, `offset=0`,
`sort=relevance`, `fields=full`, `include_pinpoint=false`, **no language
filter**), identical top_k, identical cache. The query string is the only
variable.

### 5a. Coverage axis — no effect

| bundle | A0 rows | A1 union | newly covered | still under-covered |
|---|---|---|---|---|
| `de-kapitalverletzung` | 214 | 220 (+6) | **none** | `kapitalverletzung`, `uberwachungspflicht` |
| `fr-bail-entretien` | 217 | 217 | n/a (0 under-covered at baseline) | — |
| `it-responsabilita-medica` | 211 | 211 | n/a (0 under-covered at baseline) | — |

The six added rows moved `arbeitgebers`, `eingriff` and `fursorgepflicht` by +1
each and **neither missing concept by a single row**.

### 5b. Recall axis — one recovery

Published beside the accepted frozen-benchmark cells.

| cell | accepted | A0 recall | A1 union recall | newly found |
|---|---|---|---|---|
| `corporate-criminal-liability::fr` | **FAIL 0/2** | 0.0 | **0.5** | **`bge_BGE_142_IV_333`** |
| `corporate-criminal-liability::it` | FAIL 0/2 | 0.0 | 0.0 | — |
| `business-judgment-rule::fr` | FAIL 0/5 | 0.0 | 0.0 | — |
| `business-judgment-rule::it` | FAIL 0/5 | 0.0 | 0.0 | — |
| `petty-theft-dismissal::fr` | FAIL 0/2 | 0.0 | 0.0 | — |
| `petty-theft-dismissal::it` | FAIL 0/2 | 0.0 | 0.0 | — |

`bger_6B_124_2016` and the other seven ids remain missing everywhere.

**Independent confirmation.** The harness does not only recompute its own cell.
It re-scores the accepted frozen spec with the **accepted**
`evaluation.retrieval_gate.gates.evaluate` over the same pool, and that gate
independently flips `authority::baseline_lang_recall::corporate-criminal-liability::fr`
from FAIL to PASS.

## 6. Controls (acceptance test 5) — measured, not asserted

This charter explicitly does **not** inherit the predecessor's defective
tie⇒void clause, and says so in its own frozen RULES.

| control | result |
|---|---|
| **A2 blanked** (empty variant set) | reproduces A0 **exactly on every measured unit** |
| **A3 rotated** (unit *i* seeded with unit *j*'s frozen strings) | raised coverage or recall on **no** target |
| candidate strictly beats blanked | **yes**, on `corporate-criminal-liability::fr` |

A3 reuses the donor unit's already-committed A1 envelopes, so it costs no
network of its own and its rows can never be confused with the candidate's.

## 7. Zero frozen-gate regression (acceptance test 6)

23 gates pass in the accepted record; **all 23 still pass**. One gate improves.

`reproducible::cached_second_pass_identical` is not excused: the harness performs
a **real offline second pass** over all 14 candidate envelopes, recomputes the
raw-body and ordered-ids digests, and hands the accepted gate a replay block in
the accepted record's own shape. 14/14 identical. No frozen file was modified.

## 8. Regression suite (acceptance test 7) — 49/49

Decision-count bounds, product dedup identity order, dedup arithmetic,
no-A0-row-dropped, per-row provenance channels, every `query_result_bundle`
contract field (read live from the accepted mount, never copied), frozen-plan
byte-reproducibility, cache-key derivation against committed envelopes, and a
**responsiveness witness** proving the instrument registers an injected gain —
so this run's nulls are measurements, not a dead instrument.

## 9. The finding that most matters to Product

An auxiliary **corpus-presence diagnostic** (A4 — *not* a candidate arm, *not*
eligible for OUTCOME_A, reported and not built on) separates a query-format gap
from a corpus-side gap:

| query | HTTP | rows | rows carrying the concept |
|---|---|---|---|
| `Überwachungspflicht` — the shortest possible query | 200 | 50 | **28** |
| the full natural-language question **containing** the same word | 200 | 50 | **0** |
| `Kapitalverletzung` — shortest possible query | 200 | 50 | **0** |

Read honestly, this **qualifies the predecessor's accepted cause**. At least 28
retrievable decisions carry `Überwachungspflicht`, and the *narrowest* query
finds them while the *long* natural-language query that contains the same word
finds none. So the problem is not "term queries are too narrow": **embedding the
concept in a long question suppresses it** in OpenCaseLaw's relevance ranking.
That points Product at a *short, concept-focused* query as an additional
variant, not at a longer sentence.

For `Kapitalverletzung`, 50 documents come back for the bare term and **none of
them contains the word**. That is a corpus-side or index-side signal. It is
**not** proof that the concept is absent from Swiss case law — the disclosure
text says exactly that:

> "A natural-language search for the missing concept returned no rows — a
> retrieval signal, not proof of corpus absence."

**Attribution ceiling.** The harness does **not** isolate whether the
`corporate-criminal-liability::fr` recovery comes from the appended apposition or
from the sentence-level re-issue itself. The A0 and A1 queries differ only by the
apposition, no further ablation is permitted (the rules are frozen and the
charter stops at its first outcome), and that ceiling is stated rather than
papered over.

## 10. Cost

| | |
|---|---|
| endpoint | `https://mcp.opencaselaw.ch/api/decisions` — free, no key |
| added searches, this run | 14 (+2 diagnostic) |
| added searches per question at adoption | one per under-covered concept, capped at 2; **0** for a question whose concepts are all covered |
| model calls | **0** |
| paid API / owner provisioning | **none** |
| per-search budget | 30.0 s — max measured **22.7 s**, 0 breaches |
| per-pass budget | 240.0 s — A1 / A3 / A4 all within budget |
| claim-bearing replay | `network_calls = 0` (34/34 calls served from committed envelopes) |

## 11. Integration contract (acceptance test 8)

`integration_contract_39237146851.json` — drop-in path, additive
`nl_concept_seeded` provenance entry, runtime cost, and the disclosure text for
each outcome including the zero-row case.

**Product decides adoption or decline under factory-wide requirement 21 and
records the decision. Silent non-consumption is not permitted.**

## 12. Stop

The charter ends at this first outcome. No threshold, phrasing or prompt tuning
follows. This team does not grow into classifier, abstention, layout, geometry,
benchmark construction, a product patch or a second hypothesis. Any further work
on this capability is a **new charter with its own frozen rules**, published
beside this record.

## 13. Reproduce

```bash
python3 -m frontier.frontier-concept-seed-recall.plan --out RULES.json   # must match the committed bytes
python3 -m frontier.frontier-concept-seed-recall.harness --run-id 39237146851
python3 -m frontier.frontier-concept-seed-recall.contract --run-id 39237146851
python3 -m frontier.frontier-concept-seed-recall.freeze_ordering --run-id 39237146851
python3 -m pytest tests/frontier/frontier-concept-seed-recall -q
```

The harness refuses to run if the re-derived plan differs from the committed
RULES.json in any decision-bearing key. `--offline` replays cache-only and
refuses every uncached query rather than reaching the network.