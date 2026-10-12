# Operational resume diagnosis — run 38195272963 (reconstructed in run 38196996329)

> **Authorship note.** Run 38195272963 created the quarantine under
> `results/frontier/frontier-query-retrieval/archive/scope_recovery/` and its
> `README.md` promised this file, but it never wrote it (the run failed before
> reaching its reporting/state phase). This document was reconstructed during
> the following operational-resume cycle (38196996329) from the durable
> artifacts 38195272963 left behind. Facts are observed from the tree; anything
> inferred is labelled as such.

## What run 38195272963 accomplished (observed)

1. **Scope quarantine completed and committed.** Every artifact written outside
   the team scope by the two preceding failed cycles was moved (`git mv`) into
   `results/frontier/frontier-query-retrieval/archive/scope_recovery/`:
   * `run_38192249068/bundle{,1,2}.json` — three near-identical CLI replay
     outputs (105 candidates each, `mode=offline`, `generated_at` 1791769754 /
     1791769815 / 1791769819) written at the **repository root** by the
     documented replay command with a relative `--out bundle.json`;
   * `run_38193491547/product/**` — 19 files of an out-of-scope product-lane
     adapter/cache copy.
2. **Scope-safe harness added.**
   `frontier/frontier-query-retrieval/verify_scope_safe.sh` smoke-tests the
   adapter from any working directory and writes only into
   `results/frontier/frontier-query-retrieval/verification/<stamp>/`.
3. Working tree returned to scope-clean; the snapshot branch
   `cycle/frontier/frontier-query-retrieval/38195272963/team` contains the
   quarantine (single commit `1ede171`).

## What it did **not** finish (observed)

* `state/frontier/frontier-query-retrieval.json` was never advanced: it still
  recorded `accepted_run_id=38190325825` and a lineage ending there, with no
  mention of 38192249068 / 38193491547 / 38195272963.
* The report this file replaces was never written (dangling reference from the
  scope-recovery `README.md`).
* A latent defect in the newly added harness survived: `verify_scope_safe.sh`
  guessed the repository root by walking `path.parents` looking for
  `frontier/frontier-query-retrieval` — a pattern that also matches
  `results/frontier/frontier-query-retrieval`, so the contract-import check
  crashed with `FileNotFoundError: .../results/frontier/frontier-query-retrieval/INTEGRATION_CONTRACT.json`.

## Failure class

Operational, not charter-level: two cycles died on the workflow's team-scope
gate (exit 4) for writing outside `frontier/<team>/`; the recovery cycle fixed
the scope damage and added a harness, then ended before it could advance state
and close the loop. The adapter itself (`ocl_adapter`, 45 offline tests, fixture
pack, contract) remained green throughout.

## Carried into run 38196996329

* fix the harness root-detection defect;
* re-verify acceptance (1)-(9) end-to-end;
* close the provenance gap this run left open (see
  `archive/pre_resume_38196996329_overwritten_live_evidence/MANIFEST.md`);
* advance `state/frontier/frontier-query-retrieval.json` with the full lineage.
