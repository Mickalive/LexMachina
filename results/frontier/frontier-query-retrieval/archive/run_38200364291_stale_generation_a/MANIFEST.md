# Quarantine: stale generation-A adapter copy shipped by snapshot 38200364291

Team `frontier-query-retrieval`, charter v2.
Recovered by operational-resume run **38204133740** (this cycle).

## What was wrong

Snapshot `cycle/frontier/frontier-query-retrieval/38200364291/team` is the only
snapshot in the lineage whose `ocl_adapter` package is **not** the accepted
implementation. Comparing it with the accepted base
(`lab/frontier/frontier-query-retrieval`, byte-identical to snapshot
`38196996329` for this namespace) showed 13 changed files in the team
namespace; **11 of them were a second, older-style ("generation-A") adapter
copy** that overwrote or shadowed the accepted modules:

| file | effect |
|---|---|
| `ocl_adapter/__init__.py` | dropped `AdapterConfig`, `build_candidate_bundle`, `bundle_summary`, `build_variants`, `to_product_bundle`, `validate_against_product`, `validate_candidate_bundle` from the public API |
| `ocl_adapter/bundle.py` | no `build_candidate_bundle`, `rank_candidates`, `bundle_summary`, `validate_candidate_bundle`, `to_product_bundle`, `validate_against_product` -> `pipeline`/`fixtures` unimportable |
| `ocl_adapter/client.py` | no `OCLClient` required by `pipeline` |
| `ocl_adapter/expansion.py` | no `build_variants`, `language_variants`, `search_variants` required by `pipeline` |
| `ocl_adapter/cli.py` | generation-A CLI (`prog=ocl-retrieve`): rejected `--preset fixtures`, so every documented replay/verification command failed |

The five `.py` files above were **restored** to the accepted content from
`lab/frontier/frontier-query-retrieval`. The remaining six files below had no
counterpart in the accepted base, are not referenced by the accepted code or
by `INTEGRATION_CONTRACT.json`, and were **moved** here so provenance is
preserved while the canonical namespace returns to its accepted shape:

* `ocl_adapter/deduplication.py`
* `ocl_adapter/retrieval.py`
* `contracts/INTEGRATION_CONTRACT.md` (conflicts with the canonical machine-readable `../INTEGRATION_CONTRACT.json`)
* `fixtures/generate_fixtures.py`
* `fixtures/minimal_fixture.json`
* `tests/test_adapter.py` (asserts the generation-A `ocl-retrieve` CLI)

None of these files exist on any other ref in the repository (`git cat-file`
over every `refs/remotes/origin/*`), i.e. the copy was created de-novo during
run 38200364291 and never appeared in an accepted or earlier cycle snapshot.

## Why it was not caught inside run 38200364291

The successful evidence of that run predates the overwrite:

* `verification/38200364291a/` - 56 unit tests + deterministic replay + contract
  bridge, generated `2026-10-12T03:38:20Z` against the accepted code;
* `LIVE_EVIDENCE.json` (run 38200364291) - generated `03:40:48Z`, cold cache;
* `verification/38200364291a/determinism.json` - generated `03:43:02Z`,
  `deterministic=false` because of the probe's own relative-`--out` defect
  (`n_candidates: null`, both subprocesses exit 0), which is the defect the
  same cycle diagnosed and fixed afterwards.

The overwrite therefore landed **after** all claim-bearing evidence was
produced, so nothing re-ran and the broken package reached the snapshot
unnoticed; the cycle then failed and the resilience job dispatched this
operational resume.

## Legitimate run-38200364291 work preserved in place

* `frontier/frontier-query-retrieval/verify_determinism.py` - subprocess
  `--out` resolved to an absolute path before spawning (fixes the false
  non-determinism verdict above).
* `tests/frontier/frontier-query-retrieval/test_ocl_adapter_scope_safety.py`
  - new `TestDeterminismProbeRelativeOut` regression (+34 lines), corrected in
  run 38204133740 to read the authoritative `--out` report instead of the
  stdout summary (the original form was written but never executed: it raised
  `TypeError: 'bool' object is not subscriptable`).

## Verification after recovery

`results/frontier/frontier-query-retrieval/verification/38204133740*/` -
57 unit tests, deterministic replay, contract-import bridge, fresh cold-cache
live evidence and a passing determinism probe for this run.
