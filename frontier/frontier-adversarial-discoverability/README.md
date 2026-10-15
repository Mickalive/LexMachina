# `frontier-adversarial-discoverability` — charter v1

Pre-registered, audited measurement of one question:

> Does the product genuinely **execute** the Master Prompt's independent adversarial
> **retrieval** pass, and does the map make contrary/limiting authority discoverable — or is
> the pass classification over the initial candidate pool, with counter rows merely
> re-labelled at the top of the conventional ranked list?

**Run 38792663259 verdict: `CLASSIFICATION_ONLY`.** 0 of 8 counter rows across 3 accepted
bundles entered through a retrieval route the initial broad pass did not use. Details:
`reports/frontier/frontier-adversarial-discoverability/CYCLE_38792663259.md`.

**Run 38794235870 (operational resume): re-verified, not re-measured.** The frozen matrix was
re-executed against the current accepted mount and reproduced the frozen report
**byte-identically** (`b15ea198…`); an independent second implementation agrees on every number.
Two harness defects, two prose errors and one provenance limitation were found and declared:
`reports/frontier/frontier-adversarial-discoverability/OPERATIONAL_RESUME_CYCLE_38794235870.md`.

## Layout

```
adversarial_discoverability/
  __init__.py     frozen constants (counter values, placeholder, corruption seed)
  populations.py  C_strict / C_challenged / consensus cluster / channel inventory / shortlist-aware helpers
  metrics.py      the seven frozen metric families (a)-(g) + the per-input verdict rule
  corrupt.py      five deterministic corruptions, one per metric (non-vacuity)
  shortlist.py    offline replay of the ACCEPTED AdversarialPass._prompt_decisions()
  harness.py      integrity-verified CLI: --matrix / --input / --corrupt / --non-vacuity / --run-id
independent_crosscheck.py  second implementation, imports nothing from the harness
```

## Run it

```bash
cd frontier/frontier-adversarial-discoverability

# full frozen matrix: 3 bundles + 4 legs, integrity-checked, non-vacuity, offline
python3 -m adversarial_discoverability.harness --matrix

# one artifact
python3 -m adversarial_discoverability.harness --input /path/to/bundle.json

# one corruption, to inspect a counterfactual
python3 -m adversarial_discoverability.harness --corrupt N2_deep_permute_ranks --input /path/to/bundle.json

# publish this run's copy alongside a prior run instead of overwriting it
python3 -m adversarial_discoverability.harness --matrix --run-id <this_run_id>

# independent cross-check of every number the narrative report asserts
python3 independent_crosscheck.py            # --json for a machine-readable block

cd ../../.. && python3 -m unittest discover -s tests/frontier/frontier-adversarial-discoverability -p 'test_*.py'
```

`LEX_PRODUCT_MOUNT` selects the read-only accepted `lab/product` mount
(default `/tmp/lex_accepted/core/product`).

Exit codes: `0` ok · `3` non-vacuity failed · `4` refused to overwrite a claim-bearing report
with different bytes.

## Design rules this harness holds itself to

1. **Freeze first.** Every input sha256, metric definition and threshold lives in
   `results/frontier/frontier-adversarial-discoverability/RULES.json`, committed at `1d50633`
   (2026-10-15T19:21:04Z) before any measured artifact existed. A later threshold edit
   invalidates the run; none was made.
2. **Integrity abort.** Inputs are re-hashed before any metric runs. A mismatch aborts with
   no report written.
3. **Missing is not zero.** A metric whose input the artifact does not export returns
   `NOT_APPLICABLE` with a stated reason. It never returns `FAIL 0.0`. This distinction was
   worth a 23× correction on the reality-check legs.
4. **Non-vacuity is a gate.** A metric that can never report PASS is not evidence. Five
   deterministic corruptions must each flip their target metric; if one does not, the run
   reports `NON_VACUITY_FAILED` and the verdict is void.
5. **Reproducible bytes.** The report body carries no timestamp and the harness reads no
   clock, so identical inputs give identical bytes (verified across three independent runs, and
   again on resume). `__version__` denotes the frozen **metric definitions** only; CLI/IO changes
   after the freeze are versioned separately as `IO_REVISION` and recorded in the run envelope,
   so a frozen report reproduced after an IO fix still hashes identically.
6. **A claim-bearing report is never destroyed.** `--run-id` names the output; rewriting
   identical bytes is a no-op, and rewriting *different* bytes over an existing report is refused
   (exit 4) unless `--overwrite` is explicit.
7. **Read-only outside this namespace.** The accepted mount is never written; no file is
   created outside `frontier/`, `tests/frontier/`, `results/frontier/`, `reports/frontier/`
   and `state/frontier/` for this team.
8. **Reuse first.** The shortlist metric imports and calls the **accepted**
   `frontier-generative-audit` `AdversarialPass` in `fixture_mode` rather than reimplementing
   its selection, which is why the replay reproduces the product's own recorded
   `prompt_decisions = 24` exactly.
9. **Two implementations.** `independent_crosscheck.py` re-derives the same numbers from the raw
   bundles while importing nothing from the harness, and the test suite asserts the two agree —
   so the published claim is not resting on one implementation's word alone.
