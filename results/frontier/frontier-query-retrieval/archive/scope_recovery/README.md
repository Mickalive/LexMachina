# Scope recovery quarantine (run 38195272963)

Operational-resume cycle for charter v2, team `frontier-query-retrieval`.
Nothing here was deleted: every artifact produced by the two scope-violating
runs was **moved** (git mv) into this in-team archive so the snapshot tree
again matches the charter's write scope while provenance is preserved.

## Why

The Frontier workflow enforces team scope on the *working tree*
(`.github/workflows/frontier-team.yml` -> "Enforce team scope"):

    frontier/<team>/* | tests/frontier/<team>/* | results/frontier/<team>/*
    reports/frontier/<team>/* | state/frontier/<team>.json | data/frontier/<team>/*

Two consecutive cycles failed with exit code 4 ("Frontier crossed scope"),
which skipped the audit job and forced the resilience loop to re-dispatch
operational resumes:

* run 38192249068 - scope failure on `bundle.json`, `bundle1.json`, `bundle2.json`
  at the repository root (by-products of running the documented CLI replay
  command with a relative `--out bundle.json` from the repository root).
* run 38193491547 - scope failure on `product/**` (19 files): a product-lane
  adapter/cache copy written outside the team namespace, duplicating the
  product lane the charter says this team must not build.

## Contents

* `run_38192249068/bundle*.json` - CLI replay outputs (3 near-identical
  scratch bundles) written at the repository root by the failed cycle.
* `run_38193491547/product/` - out-of-scope product-lane copy
  (`oclaw_adapter.py`, `integration_contract.json`, query cache and query
  fixture copies) written by the failed cycle.

Neither directory is on the adapter critical path. The canonical, supported
artifacts remain `frontier/frontier-query-retrieval/ocl_adapter/`,
`frontier/frontier-query-retrieval/INTEGRATION_CONTRACT.json` and
`results/frontier/frontier-query-retrieval/fixtures/`.

See `reports/frontier/frontier-query-retrieval/OPERATIONAL_RESUME_38195272963.md`
for the full diagnosis and the contract-level fix that prevents recurrence.
