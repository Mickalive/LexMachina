# Operational resume of producer snapshot 38200364291

* **Team**: `frontier-query-retrieval`
* **Charter**: v2 (`/tmp/lex_frontier_charter.json`, unchanged)
* **Resuming run**: 38204133740 (GitHub run `38204133740`)
* **Resumed snapshot**: `cycle/frontier/frontier-query-retrieval/38200364291/team`
  (commit `3d2243f`)
* **Mode**: preserve valid completed work, diagnose the operational failure,
  finish/verify the charter. No restart from scratch.

## 1. Verdict

| | |
|---|---|
| Charter | UNCHANGED — same question, hypothesis, acceptance (1)-(9), stop/promote rule |
| Failure class | **snapshot payload corruption**: a stale, second-implementation copy of five core `ocl_adapter` modules was committed over the accepted implementation *after* all of the run's claim-bearing evidence had already been produced |
| Adapter defect | none in the accepted implementation; the corruption was a write-scope-local file overwrite, not a code-logic regression |
| Outcome | restored from the accepted base, all acceptance criteria re-verified live + offline, state advanced, `continue_recommended=false` |

## 2. What was actually wrong

Run 38200364291 left behind a **green-looking but broken** snapshot.
Diffing its team namespace against the accepted base
(`lab/frontier/frontier-query-retrieval`, byte-identical to snapshot
`38196996329` for that namespace) showed exactly 13 changed files:

**Legitimate run-38200364291 work (preserved):**

* `frontier/frontier-query-retrieval/verify_determinism.py` — the
  fixture-subprocess probe now resolves `--out` to an absolute path before
  spawning `python -m ocl_adapter` (the subprocess used to inherit the
  package dir as cwd, write its replay somewhere the probe never looked, and
  therefore report a **false non-determinism verdict**; `n_candidates: null`,
  both children exit 0 — visible in
  `results/.../verification/38200364291a/determinism.json`,
  `deterministic=false`).
* `tests/frontier/frontier-query-retrieval/test_ocl_adapter_scope_safety.py`
  — new `TestDeterminismProbeRelativeOut` regression (+34 lines).

**Corrupting changes (reverted/quarantined):**

* `ocl_adapter/__init__.py`, `bundle.py`, `cli.py`, `client.py`,
  `expansion.py` were replaced by an older "generation-A" copy that:

  * dropped `AdapterConfig`, `build_candidate_bundle`, `bundle_summary`,
    `build_variants`, `to_product_bundle`, `validate_against_product`,
    `validate_candidate_bundle` from the public API;
  * left `pipeline` and `fixtures` unimportable
    (`ImportError: cannot import name 'bundle_summary' from 'ocl_adapter.bundle'`);
  * removed `OCLClient`, `build_variants`, `language_variants`,
    `search_variants` that `pipeline.py` imports;
  * shipped a CLI whose `prog=ocl-retrieve` rejected `--preset fixtures`, so
    **every documented replay/verification command failed**.

* Six files that exist on **no other ref in the repository** were added alongside
  it: `ocl_adapter/deduplication.py`, `ocl_adapter/retrieval.py`,
  `contracts/INTEGRATION_CONTRACT.md`, `fixtures/generate_fixtures.py`,
  `fixtures/minimal_fixture.json`, `tests/test_adapter.py` (the last asserts
  the generation-A CLI).

Measured effect before recovery: `python3 -m unittest discover` ran only
**15 of 57** tests (3 modules failed to import, 4 errors, 3 failures) and the
contract-import bridge was dead.

## 3. Why the previous cycle did not catch it

Timeline of run 38200364291 (all UTC, from its own artifacts):

| time | artifact | state of the tree |
|---|---|---|
| 03:38:20 | `verification/38200364291a/VERIFICATION.json` — 3/3 PASS, 56 tests | accepted code |
| 03:40:48 | `LIVE_EVIDENCE.json` (run 38200364291), cold cache, 18+7 network calls, A0-A9 true | accepted code |
| 03:43:02 | `verification/38200364291a/determinism.json` — `deterministic=false` (probe's own relative-`--out` defect) | accepted code |
| after 03:43 | probe fix + new regression test **and** the generation-A overwrite | corrupt |
| 04:31 | snapshot commit `3d2243f` pushed; state record never advanced | corrupt |

Every claim-bearing artifact therefore *predates* the overwrite, so nothing in
that cycle re-ran against the tree it actually shipped; the state record still
read `producer_snapshot_run=38196996329`, `evidence.live_evidence.run_id=38196996329`,
and no operational-resume report was written. The resilience job saw the failed
team job and dispatched this resume.

Secondary finding (negative result): the run's own new regression test was
written but never executed — after the code restore it raised
`TypeError: 'bool' object is not subscriptable`, because it parsed the
probe's stdout *summary* (`probes` values are booleans) instead of the
authoritative `--out` report.

## 4. Remediation executed this cycle

1. **Restored** `ocl_adapter/{__init__,bundle,cli,client,expansion}.py` from
   the accepted base `lab/frontier/frontier-query-retrieval`.
2. **Quarantined** the six generation-A files (moved, not deleted) to
   `results/frontier/frontier-query-retrieval/archive/run_38200364291_stale_generation_a/`
   with a `MANIFEST.md` that records file-by-file effects and how they were
   detected (`git cat-file` over every remote ref).
3. **Fixed the broken new regression test** to read the `--out` report and to
   cross-check the stdout summary, keeping every original assertion.
4. **Archived** the run-38200364291 `LIVE_*` set to
   `results/.../archive/run_38200364291_final/` (with `MANIFEST.md`) instead of
   overwriting it, then regenerated claim-bearing `LIVE_*` for **this** run
   from a cold cache (`/tmp/opencode/lex_ocl_live_cache` removed first).
5. **Documented** in `verify_determinism.py`'s docstring that `--out` is
   resolved relative to the *current working directory* — the same class of
   relative-path mistake briefly produced `frontier/results/...` during this
   cycle and was caught by a manual scope scan before the workflow's
   "Enforce team scope" step.

No file outside `frontier/frontier-query-retrieval/`,
`tests/frontier/frontier-query-retrieval/`,
`results/frontier/frontier-query-retrieval/`,
`reports/frontier/frontier-query-retrieval/` and
`state/frontier/frontier-query-retrieval.json` was written.

## 5. Re-verification (all executed this cycle)

| acceptance | result |
|---|---|
| (1) runnable adapter/CLI, live + cached | `python3 -m ocl_adapter` live/offline/`--preset fixtures` modes; `run_live_evidence.py` (2 scenarios) exit 0 |
| (2) real query → ≥100 normalized candidates | primary **300** candidates in **18** network requests, secondary **175** in **7**; 4.0 req/s ≤ charter 5.0; every candidate carries `decision_id`, `canonical_url`, `source_url`, `citation`, `language`, `decision_date`, `court`, `title`/`regeste`/`snippet`, `rank`/`score`, `provenance` |
| (3) deterministic dedupe | `canonical_identity_v1`; `n_candidates == unique decision_ids`; determinism probe: warm-cache 2×300 byte-identical, cross-process 2×105 identical → `deterministic=true`, exit 0 |
| (4) lazy full/structure | primary hydrated 3 (full text + structure), secondary hydrated 1 |
| (5) citation + leading expansion | primary: 28 incoming + 7 outgoing citation candidates from 4/5 seeds, 15 leading cases, all channel-provenanced and bounded |
| (6) FR/DE/IT without fabricated translations | primary de 165 / fr 50 / it 50 (+35 unlabelled), secondary de 45 / fr 81 / it 49; original query + lexicon variants + server-side `language_filter`, no translation performed |
| (7) offline fixtures | 19 committed envelopes; two CLI replays → 105 candidates, identical ids + provenance |
| (8) tests | **57/57** stdlib `unittest`, offline, 1.5 s |
| (9) integration contract | `INTEGRATION_CONTRACT.json` v1.0 rev 1.0.1; contract-import bridge → 105 decisions, `validation_errors=[]`, `product_validation_errors=[]`, all required decision keys present |

Commands (re-runnable from the repository root):

```bash
python3 -m unittest discover -s tests/frontier/frontier-query-retrieval -p 'test_*.py'
LEX_VERIFY_RUN_ID=38204133740b bash frontier/frontier-query-retrieval/verify_scope_safe.sh
LEX_FRONTIER_RUN_ID=<run> python3 frontier/frontier-query-retrieval/run_live_evidence.py
python3 frontier/frontier-query-retrieval/verify_determinism.py \
  --out results/frontier/frontier-query-retrieval/verification/<run>/determinism.json
```

Artifacts: `results/frontier/frontier-query-retrieval/verification/38204133740a/`,
`.../38204133740b/`, `.../38204133740_final/` (executed after the final write),
`.../38204133740/determinism.json`,
`results/frontier/frontier-query-retrieval/LIVE_EVIDENCE.json` (run 38204133740).

## 6. Negative results / prevention added

* A snapshot can be **internally inconsistent**: green verification artifacts
  whose timestamps precede the code that was actually committed. Evidence
  freshness must be checked against the *shipped tree*, not against the run id.
* Verification order matters: a final re-run must happen **after** the last
  write. This cycle's final harness stamp (`38204133740_final`) was executed
  after the code restore, the live evidence run, the determinism probe and
  every code edit; only report/state prose followed, which the harness does
  not cover.
* Relative `--out` paths are a recurring scope hazard in this team (runs
  38192249068, 38200364291, and briefly this one). Now pinned by a test and by
  docstrings.

## 7. Stop/promote

**PROMOTE.** Acceptance (1)-(9) re-verified by direct execution for run
38204133740. No concrete adapter defect remains; `continue_recommended=false`.
Continue only if product/evaluation integration surfaces a concrete adapter
defect under this same charter.
