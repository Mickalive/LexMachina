# Quarantined live-evidence overwrite (found by operational resume 38196996329)

These five files were the top-level `results/frontier/frontier-query-retrieval/LIVE_*.json`
set when operational-resume run 38196996329 started. They were **moved** here
(not edited, not deleted) so the freshly generated evidence for run 38196996329
could take the top-level, claim-bearing position without destroying history.

## What was wrong with them

| property | this quarantined set | original run 38190325825 set (also archived) |
|---|---|---|
| `LIVE_EVIDENCE.json.run_id` | `38190325825` | `38190325825` |
| `generated_at` | ~2243 s **after** the original | original |
| primary elapsed | 0.815 s | 33.832 s |
| primary network calls | **0** (18/18 cache hits) | 18 |
| primary candidate set | 300 candidates, **different id set** from the original | 300 candidates |

So this set was a *cache replay* of whatever was then in `/tmp/opencode/lex_ocl_live_cache`
— i.e. responses from an earlier network session — re-labelled with the id of an
older, genuinely live run. It therefore could not support the "live retrieval"
claim it was filed under, and its candidate set differed from the true live
evidence of the same run id (order and membership both diverge; first order
divergence at rank 3).

## Discriminating test (why this is stale cache, not adapter non-determinism)

`frontier/frontier-query-retrieval/verify_determinism.py` runs the same scenario
twice against one shared cache and compares candidate content:

* warm-cache probe: 2 × 300 candidates, 0 network calls on both passes,
  byte-identical ids/ordering/provenance/scores → deterministic given identical
  responses (`results/frontier/frontier-query-retrieval/verification/38196996329/determinism.json`);
* cross-process fixture probe: two separate interpreters replaying the committed
  fixtures produce identical candidate content.

Conclusion: identical responses ⇒ identical bundle. The differing candidate set
in the quarantined files is therefore explained by *different cached responses*
(stale cache), not by pipeline non-determinism.

## Prevention now in place

* `run_live_evidence.py` takes its run id only from `LEX_FRONTIER_RUN_ID`
  (fallback `unattributed-<epoch>`) — a previous accepted run id can never be a
  default again;
* check `A0_fresh_live_network` fails the run when a scenario performs zero
  network calls, unless `LEX_ALLOW_CACHE_REPLAY=1` is set explicitly, and the
  evidence records `cache_replayed` / `cache_dir`;
* both rules are pinned by
  `tests/frontier/frontier-query-retrieval/test_ocl_adapter_scope_safety.py`.

See `reports/frontier/frontier-query-retrieval/OPERATIONAL_RESUME_38196996329.md`.
