# Evaluation cycle report — run 38939239917 (direction v49)

Lane: evaluation. Question (factory direction v49 + FAST MVP lane directive):
*encode and enforce the observed reality-check failures — build the smallest
executable retrieval/counter-authority benchmark that can falsify the product,
reuse the existing multilingual/provenance discipline, do not rerun obsolete
universal-174k benchmarks.*

This cycle ships that missing benchmark. The frozen reality benchmark
(`evaluation/reality_gate/`) measures recorded product **answer** artifacts;
nothing measured whether the frozen controlling authorities are reachable at
all in OpenCaseLaw retrieval, in which query language, at what rank, with what
duplicates, and at what latency. The new frozen retrieval benchmark
(`evaluation/retrieval_gate/`) does exactly that, against live OpenCaseLaw,
with an independent client that never imports Product code.

## Hypothesis, baseline, success rule (frozen BEFORE execution)

* **Hypothesis.** For the four frozen reality-check questions, a plain
  single-shot OpenCaseLaw `/decisions` search retrieves at least one frozen
  controlling authority per question-with-a-frozen-set in each of FR/DE/IT
  top-50, and an explicit counter/limiting pass reaches known counter
  authority. If it does not, the product's observed authority failures are
  retrieval-side (language/reachability), not answer-side.
* **Baseline** (lane directive): one plain OpenCaseLaw search call per
  (question, language, channel) — no lexicon expansion, no reranking, no
  citation-neighbourhood expansion. 24 searches: 4 questions x {fr, de, it} x
  {baseline (frozen question text), counter (frozen limiting-authority query)}.
* **Success rule.** Exit 0 only when every measurable gate passes; any
  falsifying failure is exit 1 with the record preserved; `not_measurable`
  gates carry an explicit reason and never count as passes.

Freeze artifacts (written before any frozen query was executed):

| artifact | sha256 |
| --- | --- |
| `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` | `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` |
| `evaluation/retrieval_gate/FREEZE_RECORD.json` (`frozen_at` 2026-10-16T17:37:01Z, `frozen_before_execution: true`) | `b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49` |
| frozen reality benchmark (unchanged, re-owned authority sets) | `ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8` |

Pre-freeze disclosure (recorded in the freeze record and in the spec): two
schema probes with a **non-frozen** query (`Konventionalstrafe Vertragsstrafe`,
limit 3 and 50) and one generic probe (`query=business judgment rule`,
limit 3, first 400 chars read) established response shape/size/latency. No
frozen query text was executed and no frozen authority-hit determination was
made before the freeze record was written. Authority and known-counter sets
were derived from already-frozen/accepted artifacts only.

Frozen gate inventory (36 gates): per question — `authority::baseline_recall`,
`authority::baseline_lang_recall::{fr,de,it}`, `norm::retrievable`,
`counter::known_counter_recall`, `counter::limiting_marker_verified`,
`source::rows_valid`, `duplicate::unique_ids`; global —
`transport::all_queries_ok`, `latency::search_under_budget` (30s/call),
`latency::full_pass_under_budget` (240s/live pass),
`reproducible::cached_second_pass_identical`. Authority sets are re-owned
from the frozen reality benchmark (`citation ∪ retrieval` ids); known-counter
ids are the union of counter-classified `cited_decisions` rows across every
accepted `results/product/reality_check/` leg of the same slug, with source
file + status recorded per id and the label-soundness caveat stated in the
spec (label truth is not re-verified here).

## What this cycle built (executable, lane-owned)

* `evaluation/retrieval_gate/frozen.py` — digest pin, freeze-record check,
  NFKD/markup-stripping normalization, alnum-core id mapping (legacy
  `bger_4A_219_2015` ≡ ATF-style `bge_4A 219/2015` ≡ citation `BGE 4A 219/2015`).
* `evaluation/retrieval_gate/client.py` — stdlib-only paced (<=2.5 req/s),
  retried (3x backoff) search client with content-addressed raw-response
  cache; pass A is always live, pass B is strictly offline.
* `evaluation/retrieval_gate/gates.py` — pure, recomputable gate functions
  (verdict = f(frozen spec, run record), byte-identical on recompute).
* `evaluation/retrieval_gate/run_retrieval_benchmark.py` — CLI with exit
  codes 0/1/2/3; **exit 2 (environment error) emits no verdict record**, and
  the runner refuses to write a record when every search fails transport.
* `evaluation/retrieval_gate/build_frozen_spec.py` — construction provenance;
  refuses to overwrite an existing spec (no silent re-freeze path).
* `tests/evaluation/test_retrieval_gate.py` — 33 tests: digest pin, freeze
  record, authority-set parity with the reality benchmark, id-alias and
  markup-normalization rules, a positive all-green fixture, **one falsification
  test per gate**, not-measurable-is-never-a-pass, verdict determinism,
  offline empty-cache exit 2 with no record, rescore-rejects-foreign-sha, and
  (once a claim-bearing record exists) freeze-before-execution ordering +
  byte-identical verdict recomputation.

Active lane suite after this cycle: `test_reality_gate.py` 46 +
`test_audit_correction_verification.py` 4 + `query_map/test_harness.py` 6 +
`test_frontier_verdict_adoption.py` 9 + `test_retrieval_gate.py` 33 =
**98/98 PASS**. The legacy 174k-era modules under `tests/evaluation/`
(`test_v25_174k_*`, `test_v11_*`, `test_cross_lingual_alignment_v10`,
`test_frozen_harness_v3_*`) remain historical and were not collected (they
import numpy/sklearn and belong to the paused 174k program; the direction
forbids rerunning those benchmarks).

## Execution record

`results/evaluation/retrieval_benchmark/38939239917.json` (1.28 MB,
self-contained evidence: per-query rows with id/docket/citation/url/language/
text head, raw-body sha256, ordered id list, verdict). Raw response bodies for
all 24 live searches are preserved under
`results/evaluation/retrieval_benchmark/cache/` (3.3 MB with the record).

* Pass A (live, `https://mcp.opencaselaw.ch/api/decisions`): 24/24 HTTP 200,
  960 retrieved rows, wall **256.827s** (per-search min/median/max =
  4.521s / 10.311s / 20.534s).
* Pass B (strictly offline replay from the lane cache): byte-identical raw
  bodies **and** identical ordered id list for all 24 queries
  (`reproducible::cached_second_pass_identical` PASS; `--rescore` reproduces
  the recorded verdict byte-for-byte).
* `--rescore` exit 1 = FAIL verdict, as expected for this record.
* Post-execution harness fix (gate outcomes unchanged, logged in the record):
  `gates.py` originally iterated `row_cores()` **sets** directly, so the
  `duplicate::unique_ids` example-list order varied with `PYTHONHASHSEED`
  across processes — caught by the verdict-recompute test, fixed by iterating
  `sorted(row_cores(...))` in `unique_ids`/`match_authorities`. The stored
  verdict was recomputed once with the fix (only the corporate
  duplicate-example **ordering** changed; same multiset; all 36 gate outcomes,
  counts and details identical) and the recompute is recorded in the record's
  `verdict_recompute_log` with old/new verdict sha256. Two regression tests
  pin the fix: byte-identical verdict across `PYTHONHASHSEED` 0/1/2 in fresh
  interpreters, and the recompute-log disclosure itself. Verdict sha after
  fix: `93214cb8…` (old `b0f8e2b0…`).

No 174k benchmark was rerun. No Product code was imported. The frozen reality
benchmark digest was re-verified unchanged (its tests pin it).

## Result: 12 falsifying failures, 24 passes, 4 not measurable — overall FAIL

| question | authority baseline (fr / de / it, top-50) | known-counter recall | limiting-marker proxy | duplicates | source rows |
| --- | --- | --- | --- | --- | --- |
| rent-default | *not measurable* (frozen reality spec carries no controlling set) | PASS 3/9 | PASS (257d + abus/exception evidence recorded) | **FAIL** (16 alias-duplicate cores in the FR baseline page) | PASS |
| corporate-criminal-liability | **FAIL fr 0/2, FAIL it 0/2**, de 2/2 (ranks 18, 23); union PASS | PASS 4/6 | **FAIL** (no counter row with `art. 102` + a limitation token in the first 600 chars) | **FAIL** (8 in FR baseline + 8 in FR counter page) | PASS |
| business-judgment-rule | **FAIL fr 0/5, FAIL it 0/5**, de 2/5 (ranks 9, 11); union PASS | PASS 1/4 | PASS (`zh_handelsgericht_HG120149`, BJR + pflichtwidrig) | **FAIL** (10 in FR + 4 in DE baseline page) | PASS |
| petty-theft-dismissal | **FAIL fr 0/2, FAIL it 0/2**, de 1/2 (`bger_4A_177_2017` rank 2); union PASS | PASS 7/9 | PASS (`bge_119 II 162`, art. 337 + proporz) | **FAIL** (13 in FR baseline + 4 in FR counter page) | PASS |

Global: `transport::all_queries_ok` PASS, `latency::search_under_budget` PASS
(worst 20.534s < 30s), `latency::full_pass_under_budget` **FAIL**
(256.827s >= frozen 240s), `reproducible::cached_second_pass_identical` PASS.

### F1 — Authority retrieval is German-brittle, and the product's questions are French

For every question that has a frozen controlling-authority set, the **German**
plain-query baseline retrieves the authorities inside top-50 (corporate 2/2,
BJR 2/5, petty-theft 1/2), while the **French and Italian** plain-query
baselines retrieve **zero** of them (0/2, 0/5, 0/2). The union gates pass only
via the German page. The frozen questions' record language is French — the
language the product actually ships — and it is exactly the language whose
plain search misses every frozen authority.

### F2 — BJR authority base: retrieval can reach it, the answer did not cite it

The independent DE baseline retrieves `bger_4A_219_2015` (rank 9) and
`bger_4A_603_2014` (rank 11). The frozen reality benchmark's fresh BJR leg
(`business-judgment-rule_live_20261016T161006Z`) cites **none** of the five
frozen direct-TF BJR authorities. The EXPLORATORY product-cache cross-check
(tier EXPLORATORY by design, see disclosure) additionally shows all **five**
frozen BJR authorities present in the ACCEPTED product's own
`results/product/query_cache` search envelopes (2-4 envelopes each), reached
via the product's expansion queries (`Geschäftsentscheid Verwaltungsrat…`)
but via **zero** of the 10 accepted envelopes whose query equals the frozen
French question text. Same pattern for petty-theft: `bger_4A_228_2015` appears
in exactly 1 accepted envelope, `bger_4A_177_2017` in 7. Discrimination: the
BJR 0/5 citation failure is **not** a corpus-reachability problem; it sits in
candidate selection / answer synthesis, with an over-reliance on the German
expansion channel that the French question path does not reproduce.

### F3 — Raw OpenCaseLaw result pages carry same-decision duplicates and malformed ids

63 alias-duplicate cores across 7 of 24 queries (worst: 16 in the FR
rent-default baseline page). Verified pairs are the **same decision under two
docket ids** — e.g. `ge_gerichte_C_6552_2022` + `ge_gerichte_ACJC_1511_2022`
(same date 2022-11-21, linked by the row's own `canonical_decision_id` and
cross-docket text), `vd_findinfo_HC___2013___801` + `vd_gerichte_JL13.022381`
(same date 2013-12-09), `ge_gerichte_P_17078_2019` + `ge_gerichte_ACPR_74_2021`
(same date 2020-09-30). Separately, 6 retrieved rows carry **malformed**
upstream ids — `ch_vb__td_class__metadataCell__150000044__td_` (whose raw
`docket_number` is a live HTML fragment `<td class="metadataCell">150000044</td>`)
and four `ge_gerichte_[pjdoc NNNNN]` rows — all confirmed present in the raw
cached HTTP bodies (sha-verified), i.e. upstream scraping noise, not a harness
artefact. Consequence for Product: dedupe by canonical id + cross-docket
alias detection, and id sanitation, are load-bearing retrieval steps, not
cosmetics. (`source::rows_valid` still PASSes: urls and languages are valid;
the defect is in id quality, which no frozen gate covered before this cycle.)

### F4 — Corporate counter-marker proxy failed (proxy limitation disclosed)

No FR/DE/IT counter-channel row for corporate criminal liability carried both
`art. 102` and a frozen limitation token inside the recorded 600-char text
head (90 counter rows checked). This is a **necessary-not-sufficient lexical
proxy** (frozen token lists, frozen 600-char `text_head` truncation), so the
failure is reported as measured but its cause (missing limitation language vs
truncation) is not separable from this record. Known-counter recall for the
same question PASSes 4/6, so Art. 102 limiting authority is retrievable; only
the marker proxy is blind here. Proxy strength caveat is frozen in the spec
(`weak_proxy_disclosure`).

### F5 — Retrieval pass latency alone breaches a 300s product budget

The 24-search live pass took 256.827s (max single search 20.534s) — above the
frozen 240s retrieval-pass budget, and enough on its own to leave <45s for
reranking, answer synthesis, the counter pass and the map inside the product's
hard <300s full-run budget. This is consistent with the product's observed
~316-469s reality-check latencies on free models. The budget was frozen before
execution and is **not** weakened here; the number is preserved as negative
evidence.

## What passed (also evidence)

* Counter/limiting reachability: known-counter ids retrieved for all four
  questions (3/9, 4/6, 1/4, 7/9) and independently verified limitation
  evidence recorded for three questions.
* Governing-norm retrievability for all four questions.
* Source validity of all 960 rows (https `mcp.opencaselaw.ch` canonical urls,
  non-empty ids, de/fr/it languages).
* Transport robustness (24/24 with retries) and cached reproducibility
  (offline replay byte-identical to the live pass, including raw sha256).
* Per-search latency under the 30s frozen budget.

## Not measurable (explicit, never counted as passes)

* 4 rent-default authority gates: the frozen reality benchmark carries no
  controlling-authority set for rent-default (`authority_ids = []`), so
  recall cannot be measured; the question is still covered by the norm,
  counter, source, duplicate and latency gates and by the frozen reality
  benchmark's truth gates.

## Claim ceiling

This benchmark measures retrieval reachability, cross-language robustness,
counter reachability, source validity, duplicate structure, latency and cached
reproducibility of **independent** OpenCaseLaw searches for the frozen
questions. It does not prove that the map is useful to a jurist, it does not
re-classify any decision as supporting/contrary/limiting, and the product
cache comparison stays EXPLORATORY (its design followed a pre-freeze scan of
that cache). `human_gate_ready` remains false; the product lane's exit gate
(the four-question frozen reality benchmark reliably green without weakening
truth/authority/language/latency gates) is unchanged and still closed.

## Product-lane consequences (falsification targets, not requests)

1. **FR/IT authority recall**: the French-first question path must add
   cross-language expansion/translation so FR/IT queries recover at least the
   DE-level authority recall (>=1-of-set per authority gate in the frozen
   reality benchmark's citation gates, and >=1-of-set retrievable here).
2. **BJR candidate selection**: five frozen BJR authorities were in the
   product's own accepted cache and in the DE baseline, yet none were cited —
   fix selection/citation, not retrieval plumbing.
3. **Dedupe + id sanitation**: collapse `canonical_decision_id` /
   cross-docket aliases (GE `C/ACPR/ATA`, VD `HC/JL`) and reject malformed
   scraped ids (`[pjdoc …]`, HTML-fragment ids) before ranking/map insertion.
4. **Latency**: the 24-search retrieval pass must be parallelised or budgeted
   explicitly, otherwise the <300s full-run gate cannot be met end-to-end.

## Recommendation

**CONTINUE** under the same v49 question. Concrete next-cycle purpose: when
the product lane publishes a new accepted packet, (a) re-run the frozen
reality benchmark on it (BJR authority-citation recovery is the headline), and
(b) re-run this frozen retrieval benchmark from cache to confirm the recorded
verdict is stable, plus one fresh live pass only if the product changed its
retrieval stack (then check FR/IT authority recall and retrieval-pass latency
against the same frozen budgets). Do not reopen 174k/global-map research.

## Provenance

* frozen spec / freeze record: `evaluation/retrieval_gate/`
* run record: `results/evaluation/retrieval_benchmark/38939239917.json`
  (sha256 of file on disk; verdict recomputable byte-identically via
  `python -m evaluation.retrieval_gate.run_retrieval_benchmark --rescore <record>`)
* raw live responses: `results/evaluation/retrieval_benchmark/cache/`
* tests: `tests/evaluation/test_retrieval_gate.py` (33)
* inputs read-only: `/tmp/lex_accepted/product/results/product/query_cache`
  (EXPLORATORY cross-check), `/tmp/lex_accepted/product/results/product/reality_check`
  (known-counter set construction), `evaluation/reality_gate/frozen_benchmark.json`
  (authority sets).
