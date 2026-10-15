# `frontier-adversarial-discoverability` — charter v1

Pre-registered, audited measurement of one question:

> Does the product genuinely **execute** the Master Prompt's independent adversarial
> **retrieval** pass, and does the map make contrary/limiting authority discoverable — or is
> the pass classification over the initial candidate pool, with counter rows merely
> re-labelled at the top of the conventional ranked list?

**Run 38792663259 verdict: `CLASSIFICATION_ONLY`.** 0 of 8 counter rows across 3 accepted
bundles entered through a retrieval route the initial broad pass did not use — as far as
the pool's declared channel vocabulary can show (metric b1's declared D10 limitation;
the run-38797568256 stage-evidence channel closes it: no frozen artifact declares or
logs an adversarial retrieval stage at all). Details:
`reports/frontier/frontier-adversarial-discoverability/CYCLE_38792663259.md`.

**Run 38794235870 (operational resume): re-verified, not re-measured.** The frozen matrix was
re-executed against the current accepted mount and reproduced the frozen report
**byte-identically** (`b15ea198…`); an independent second implementation agrees on every number.
Two harness defects, two prose errors and one provenance limitation were found and declared:
`reports/frontier/frontier-adversarial-discoverability/OPERATIONAL_RESUME_CYCLE_38794235870.md`.

**Run 38797568256 (audit of the accepted measurement): verdict unchanged, three harness defects
closed.** The charter permits continuation only for a concrete defect in the harness, so this run
audited run 38792663259 rather than re-measuring it, reproduced the frozen report byte-identically
again (`b15ea198…`), and fixed: **D10** the load-bearing metric `b1` reads the *final pool's*
channel union and so cannot distinguish "no adversarial retrieval ran" from "one ran and was
absorbed into that union"; **D11** the single named cause named one of **two** shipped
counter-authority mechanisms (`product/query/answer.py::counter_authority_pass`, documented as
"Independent adversarial retrieval", reachable only from the degraded fallback and executed for
none of the 7 artifacts); **D12** an absent language marker (`"?"`) was scored as a non-consensus
language, inflating the one metric that PASSes on all three bundles. `adversarial_paths.py` adds the
missing falsification channel — retrieval stage inventory, per-stage request log, unaccounted-channel
check, mechanism discovery and execution fingerprints — plus a self-test proving it can fire.
Three defects in that new code were caught by running it (D13 line-shifting prose stripper,
D14 `re.search(` read as a retrieval call, D15 overlapping scan roots double-counting).
`reports/frontier/frontier-adversarial-discoverability/CYCLE_38797568256.md`.

**Run 38799078780 (audit repair, round 1): F1–F3 landed, verdict unchanged.** The audit of
run 38797568256 required three fixes and no re-measurement: **F1** the "freeze commits
unresolvable / history squashed" disclosure was false and is replaced by the verified
statement (freeze `1d50633` is a direct ancestor of measurement `72ecb19` on the published
lab branch; `RULES.json` at the freeze hashes identically to the current file); **F2**
no-provenance artifacts now report `NOT_APPLICABLE_NO_PROVENANCE` (observed_channel_count=0)
instead of a vacuous negative, and the aggregate claim is scoped to the three bundles;
**F3** the test suite is green-with-skips in any checkout and the executed-count figure is
stated as mount-conditional. The frozen report reproduces byte-identically again
(`b15ea198…`). `reports/frontier/frontier-adversarial-discoverability/CYCLE_38799078780.md`.

## Layout

```
adversarial_discoverability/
  __init__.py           frozen constants (counter values, placeholder, corruption seed)
  populations.py        C_strict / C_challenged / consensus cluster / channel inventory / language helpers
  metrics.py            the seven frozen metric families (a)-(g) + the per-input verdict rule
  corrupt.py            five deterministic corruptions, one per metric (non-vacuity)
  shortlist.py          offline replay of the ACCEPTED AdversarialPass._prompt_decisions()
  adversarial_paths.py  ADDITIVE evidence (run 38797568256): retrieval stage inventory, per-stage
                        request log, unaccounted channels, mechanism discovery + structural
                        capability reads, execution fingerprints, self-test. Never touches the
                        frozen report. (Run 38799078780, audit F2: inputs carrying no retrieval
                        provenance report NOT_APPLICABLE_NO_PROVENANCE with
                        observed_channel_count=0 — the frozen report's own convention for
                        metric (b) — and the aggregate detection claim is scoped to the
                        provenance-carrying bundles.)
  harness.py            integrity-verified CLI: --matrix / --input / --corrupt / --non-vacuity
                        / --run-id / --path-evidence
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

# + the additive adversarial-path evidence (stage inventory, mechanism discovery, self-test)
python3 -m adversarial_discoverability.harness --matrix --path-evidence --run-id <this_run_id>

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
   (2026-10-15T19:21:34Z; `RULES.json`'s own `frozen_at_utc` records 2026-10-15T19:21:04Z)
   before any measured artifact existed: `1d50633` is a direct ancestor of the
   measurement commit `72ecb19` (2026-10-15T19:28:13Z) on the published lab branch
   `origin/lab/frontier/frontier-adversarial-discoverability`, and `RULES.json` as
   committed at the freeze hashes identically to the current file (`5e78d8f1…`). The
   pre-registration order is therefore verifiable, not merely asserted. A later
   threshold edit invalidates the run; none was made. (An earlier "squashed /
   unresolvable" disclosure was an artifact of the workflow's depth-1 fetch of the
   cycle team branch; corrected in the run-38799078780 repair, audit F1.)
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
10. **A negative is only evidence if the instrument can fire.** Metric (b) reads the final pool's
    channel union, so on its own it could not see an adversarial round whose channel was absorbed
    into that union. `adversarial_paths.py` reads the retrieval stage inventory and the per-stage
    request log instead, and its self-test injects a synthetic adversarial retrieval and asserts
    the detector fires — with `b1_adversarial_channel_rows` still reading `0`, which is the defect
    made visible. The residual blind spot of the stage channel is declared in the artifact and
    covered by the complementary mechanism-capability read; neither channel is load-bearing alone.
11. **Fixes are additive, never interpretive.** No defect fix since the freeze changed a threshold,
    a metric definition or a published number. `CYCLE_38792663259_REPORT.json` still hashes to
    `b15ea198…` and every later run reproduces it byte for byte; new evidence is published beside
    it under its own name and sha256.
