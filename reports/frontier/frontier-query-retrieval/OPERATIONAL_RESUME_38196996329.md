# Operational resume — Frontier `frontier-query-retrieval` charter v2, run 38196996329

Resumed from persisted producer snapshot **38195272963**. Charter unchanged
(`/tmp/lex_frontier_charter.json`, v2). No work was restarted from scratch:
the durable adapter, fixtures, contract and tests from the accepted cycle
(38190325825) were preserved and re-verified; this cycle fixed the operational
defects that kept killing the run and closed the provenance gap.

---

## 1. Diagnosis of the operational failure

Chain of failure (evidence: `results/frontier/frontier-query-retrieval/archive/scope_recovery/`):

| run | outcome | cause |
|---|---|---|
| 38192249068 | workflow exit 4 (scope gate) | documented replay command `... --out bundle.json` executed from the repository root wrote 3 stray `bundle*.json` files outside the team namespace |
| 38193491547 | workflow exit 4 (scope gate) | wrote a 19-file `product/**` adapter/cache copy outside the team namespace (duplicating the product lane the charter forbids) |
| 38195272963 | incomplete operational resume | quarantined the out-of-scope files and added `verify_scope_safe.sh`, but never advanced `state/frontier/frontier-query-retrieval.json`, never wrote its promised report, and shipped a harness whose repo-root detection was wrong |
| **38196996329** (this run) | completed | see §2–§5 |

Additional defect found this cycle while re-verifying:

* **`verify_scope_safe.sh` repo-root false positive** — it walked `path.parents`
  for `frontier/frontier-query-retrieval`, matched
  `results/frontier/frontier-query-retrieval` first, and crashed the
  contract-import check with `FileNotFoundError`
  (`verification/38196996329/contract_import.txt` preserves the failure).
  Fixed: the shell now passes the root it computed from its own location;
  regression pinned by `test_verify_scope_safe_passes_repo_root_explicitly`.

Provenance defect found this cycle (independent of the scope failures):

* **claim-bearing live evidence had been silently overwritten.** The top-level
  `LIVE_*.json` set at resume time was a **zero-network cache replay**
  (18/18 cache hits, primary elapsed 0.815 s) that still carried
  `run_id=38190325825`, while its candidate set *differed* from the true live
  evidence of that same run id (archived under `archive/run_38190325825/`).
  Quarantined to `archive/pre_resume_38196996329_overwritten_live_evidence/`
  with a full manifest; discriminating test in §3.

---

## 2. Charter acceptance — re-verified this cycle by direct execution

| # | requirement | result | evidence |
|---|---|---|---|
| 1 | runnable adapter/CLI, live + cached modes | **PASS** | `python3 -m ocl_adapter` live/offline/refresh/`--preset fixtures`; exit codes 0/2/3/4 |
| 2 | real Swiss query → normalized bundle ≥100 with provenance | **PASS** | live primary `Kündigung Mietvertrag Mietrecht` → **300** candidates (18 network requests, 32.5 s, 4.0 rps); secondary `responsabilité contractuelle dommages indemnisation` → **175** (7 requests, 20.5 s); every candidate carries decision_id, canonical_url, source_url, citation, language, date, court, title/regeste/snippet, rank/score, provenance |
| 3 | deterministic dedupe by canonical identity | **PASS** | `canonical_identity_v1`, order-independent; live bundles have `n_candidates == unique decision_ids` |
| 4 | lazy full decision/structure fetch | **PASS** | live primary hydrated 3 with `full_text` + `structure` |
| 5 | citation-neighbourhood + leading-case expansion, bounded | **PASS** | live primary: 28 incoming + 7 outgoing citation candidates from 4 seeds, 15 leading cases, all channel-provenanced |
| 6 | FR/DE/IT variants / language filters, no fabricated translations | **PASS** | primary spans de 165 / fr 50 / it 50; secondary de 45 / fr 81 / it 49; lexicon expansion only, server-side language filters |
| 7 | cached fixtures → deterministic offline tests | **PASS** | 19 committed envelopes; two replays identical (ids + provenance); cross-process probe identical |
| 8 | tests: pagination, cache, dedupe, provenance, remote-failure degradation | **PASS** | **56/56** stdlib unittest tests, 0.9 s, offline, no third-party imports |
| 9 | machine-readable integration contract | **PASS** | `INTEGRATION_CONTRACT.json` (1.0, revision 1.0.1); documented sys.path import executed end-to-end → `replay_fixtures()` → `validate_candidate_bundle()==[]`, `validate_against_product()==[]`, `to_product_bundle()` → 105 decisions with all `REQUIRED_DECISION` keys |

Rate limits: all live traffic at 4.0 rps ≤ charter 5.0; `AdapterConfig` rejects
`max_rps` outside `(0, 5.0]`.

---

## 3. Discriminating test: is the adapter deterministic?

Question raised by the quarantined overwrite: why would a "live"-labelled
re-run produce a *different* candidate set?

`frontier/frontier-query-retrieval/verify_determinism.py` (new this cycle):

* **warm-cache probe** — same scenario, same shared cache, two passes:
  2 × 300 candidates, 0 network calls on both, **byte-identical**
  ids/ordering/provenance/scores/ranks/dedupe stats;
* **cross-process fixture probe** — two separate interpreters (different
  `PYTHONHASHSEED`) replaying the committed fixtures: identical candidate
  content, 105 candidates each.

⇒ given identical responses the adapter is deterministic. The differing
candidate set in the quarantined files is therefore **stale cached responses
from an earlier network session**, not pipeline non-determinism.
Report: `results/frontier/frontier-query-retrieval/verification/38196996329/determinism.json`.

---

## 4. Fixes landed this cycle (all inside team scope)

1. `verify_scope_safe.sh` — explicit repo-root argument (defect in §1). Re-run:
   `verification/38196996329b/VERIFICATION.json` → 3/3 PASS (unit tests,
   deterministic replay, contract-import bridge).
2. `run_live_evidence.py` —
   * run id only from `LEX_FRONTIER_RUN_ID`, fallback `unattributed-<epoch>`
     (a previous accepted run id can no longer be a default);
   * new check `A0_fresh_live_network`: a scenario with **zero** network calls
     fails the run unless `LEX_ALLOW_CACHE_REPLAY=1`, and the evidence records
     `cache_replayed` + `cache_dir`.
   * Functional proof: a warm-cache re-execution now exits 1 with
     `A0=false, cache_replayed=true, run_id=unattributed-*` (one-off driver,
     executed against a temp `RESULTS` so no claim-bearing file was touched).
3. `ocl_adapter/cli.py` + `INTEGRATION_CONTRACT.json` — every documented
   `--out`/`--product-bundle` now targets
   `results/frontier/frontier-query-retrieval/scratch/...` (or `/tmp`); new
   `scope_safety` and `evidence_freshness` contract sections; contract revision
   1.0.1 recorded (schema unchanged).
4. New regression suite
   `tests/frontier/frontier-query-retrieval/test_ocl_adapter_scope_safety.py`
   (11 tests): documented commands are scope-safe, the legacy
   `--out bundle.json` shape is rejected (negative control), no hardcoded prior
   run id, freshness check present, harness passes the repo root explicitly,
   determinism probe falls back to temp dirs, and the documented replay command
   is executed verbatim (offline) with `--out` re-targeted to a temp dir.
5. Test count 45 → **56**, all green offline.

---

## 5. Claim-bearing evidence status

* Top-level `LIVE_*.json` now belong to **this run (38196996329)** and were
  produced from a **cold cache** by the final code: 18 + 7 real network calls,
  0 cache hits, `A0_fresh_live_network=true`, `cache_replay_allowed=false`,
  all A1–A9 checks pass.
* History preserved, nothing overwritten in place:
  * `archive/run_38172061004/` — original live evidence (untouched);
  * `archive/run_38190325825/` — accepted-cycle live evidence (untouched);
  * `archive/run_38196996329_pre_freshness_guard/` — this run's first live
    output, generated before the freshness guard existed (genuine network
    evidence, superseded within the same run id);
  * `archive/pre_resume_38196996329_overwritten_live_evidence/` — the
    mislabelled cache-replay set found at resume, with `MANIFEST.md`;
  * `archive/scope_recovery/` — out-of-scope artifacts of the two failed runs
    (untouched this cycle).
* Fixtures (`fixtures/cache`, 19 envelopes + `FIXTURE_META.json`) were **not**
  re-recorded: evaluation benchmarks stay frozen.

---

## 6. Negative results preserved

* Stale-cache "live" evidence can silently differ from true live evidence while
  carrying a valid-looking run id — now detected by `A0_fresh_live_network`
  (quarantined set + manifest are the retained evidence of the phenomenon).
* An offline bundle built with non-fixture parameters against the fixture cache
  degrades to an empty, `provenance.degraded=true` bundle instead of fabricating
  results (carried forward from 38190325825; still the documented behaviour).
* `verify_scope_safe.sh` as first shipped was itself broken (repo-root false
  positive); the failing log is kept in `verification/38196996329/`.

---

## 7. Commands (reproducible, scope-safe)

```bash
# 56 offline tests
python3 -m unittest discover -s tests/frontier/frontier-query-retrieval -p 'test_*.py'

# supported harness from any working directory
bash frontier/frontier-query-retrieval/verify_scope_safe.sh          # 3/3 PASS
bash frontier/frontier-query-retrieval/verify_scope_safe.sh --live   # + live run

# deterministic offline replay (contract-documented, scope-safe path)
cd frontier/frontier-query-retrieval
python3 -m ocl_adapter 'Kündigung Mietvertrag Mietrecht' --preset fixtures \
    --out ../results/frontier/frontier-query-retrieval/scratch/replay.json --validate

# fresh live evidence (cold cache, attributed)
rm -rf /tmp/opencode/lex_ocl_live_cache
LEX_FRONTIER_RUN_ID=<run id> python3 run_live_evidence.py

# determinism probe
LEX_FRONTIER_RUN_ID=<run id> python3 verify_determinism.py \
    --cache-dir /tmp/opencode/lex_ocl_live_cache \
    --out ../results/frontier/frontier-query-retrieval/verification/<stamp>/determinism.json
```

---

## 8. Handoff and recommendation

**PROMOTE.** Acceptance (1)–(9) all pass by direct execution this cycle; the
three operational failure modes (scope escape ×2, stale-cache evidence
re-labelling) now have both tooling and regression-test prevention. No adapter
defect was found that requires another cycle under this charter:

* **product**: import via
  `sys.path.insert(0, <repo>/frontier/frontier-query-retrieval)` →
  `AdapterConfig(mode='live', target=150)` → `build_candidate_bundle` →
  `to_product_bundle`; do not re-implement dedupe/caching/provenance/expansion.
  When vendoring into a lane, keep CLI `--out` inside that lane's namespace.
* **evaluation**: freeze on `results/frontier/frontier-query-retrieval/fixtures/`
  + `LIVE_EVIDENCE.json` (run 38196996329); replay with
  `ocl_adapter.fixtures.replay_fixtures()`; do not re-record fixtures.

`continue_recommended=false`. Continue only if product/evaluation integration
surfaces a concrete adapter defect under this same charter.
