# Operational resume — run 38794235870 (resumed from producer snapshot 38792663259)

**Outcome: the charter was already complete and is re-verified. Verdict unchanged:
`CLASSIFICATION_ONLY`. The failure that triggered this resume was a workflow false negative,
not missing work.**

Machine-readable record:
`results/frontier/frontier-adversarial-discoverability/CYCLE_38794235870_RESUME_VERIFICATION.json`

---

## 1. What was preserved

Run 38792663259 finished the charter: frozen pre-registered rules, 3 accepted bundles + all 4
frozen reality-check legs measured, non-vacuity proven, verdict named, one bounded candidate
cause delivered, 36 tests green. All of it was durable on the snapshot branch
`cycle/frontier/frontier-adversarial-discoverability/38792663259/team` and is reused unchanged:

| artifact | state on resume |
|---|---|
| `RULES.json` (sha256 `5e78d8f1…`) | untouched |
| `CYCLE_38792663259_REPORT.json` (sha256 `b15ea198…`) | untouched — **re-hashed to the same value** |
| `CYCLE_38792663259_REPRODUCIBILITY.json` | untouched |
| `superseded/CYCLE_38792663259_REPORT_defect-v1.json` (negative result) | preserved |
| `CYCLE_38792663259.md`, `INTEGRATION_CONTRACT.md` | preserved, one declared correction applied (§4) |
| `state/frontier/frontier-adversarial-discoverability.json` | updated, `charter_version` and verdict retained |

Nothing was restarted from scratch and no threshold, metric definition, population, verdict or
candidate cause was touched.

## 2. Re-verification (not a re-measurement)

The accepted `lab/product` mount has advanced since the freeze (it is now at
`49d6593 "accept product cycle 38789874982"`). That is a stronger test than a re-run against the
same commit would have been, because a moved mount is exactly where a stale measurement would
break:

- **All 7 frozen inputs re-hashed on the current mount: observed == frozen** (recorded in
  `CYCLE_38794235870_ENVELOPE.json`). Product's citation-repair cycle did not touch the seven
  named artifacts.
- **Full matrix re-executed: `CYCLE_38794235870_REPORT.json` is byte-identical to the frozen
  report** — same sha256 `b15ea198c2df9a1bedeaff6a33d12d96153a84e331f8ce91e601c124292006bd`.
- Non-vacuity gate `PASS` on all 3 real bundles; `network_calls: 0`; mount read-only.
- Tests: **52, `OK`** (was 36; +16 covering the defects fixed here and the cross-check oracle).

**Independent cross-check.** `frontier/frontier-adversarial-discoverability/independent_crosscheck.py`
recomputes the numbers the narrative report asserts, from the raw bundles, *importing nothing
from the harness*. It agrees with the harness on every counter-row count, rank, channel, cluster,
evidence and answer-linkage figure, and on every prose claim. An auditor can now re-derive the
claim without trusting the measuring code:

```bash
cd frontier/frontier-adversarial-discoverability && python3 independent_crosscheck.py
```

## 3. The operational failure, diagnosed

**Failing step:** `Validate Frontier producer delta and state` in `.github/workflows/frontier-team.yml`.
**Exit code 67.** The guard is:

```bash
if git diff --quiet && git diff --cached --quiet && [[ -z "$(git status --porcelain -uall)" ]]; then
  echo "::error::Frontier producer returned success with zero durable delta"
  exit 67
fi
```

**Root cause.** The guard infers "a durable delta exists" from the *absence of a clean tree*. It
never looks at `git log`. Run 38792663259 committed its own work — the snapshot's HEAD is the
producer's own commit `72ecb19`, message
`"Frontier frontier-adversarial-discoverability v1 run 38792663259: frozen pre-registered
measurement, verdict CLASSIFICATION_ONLY"`, not the workflow's generic
`"Frontier <team> v<ver> run <id>"` message. A committed tree is clean, so all three conditions
held and the step failed **after** the work was already durable.

Reproduced verbatim in the resumed checkout, against the same clean tree:

```
::error::Frontier producer returned success with zero durable delta  <-- exit 67 TRIPPED
```

Ruled out, with evidence:

| candidate | why it is not the cause |
|---|---|
| exit 68 / 69 (state missing or un-advanced) | the state file exists and satisfies every `jq` condition (`charter_version==1`, `cycle_status != INITIALIZED`, `evidence_tier` non-empty) |
| `Enforce team scope` exit 4 | the snapshot contains no path outside this team's five allowed prefixes |
| job timeout | `Persist team snapshot` runs with `if: always()` and the snapshot branch exists, so the job reached the end of its step list |
| the Ox/OpenCode step itself | the state's artifacts, the four declared harness corrections and the preserved negative result show a multi-stage run that completed |

**Why it matters beyond this team:** any producer that commits its own work is failed after the
fact, and the `resilience` job then re-dispatches the same charter from the snapshot. A team that
commits correctly can therefore loop forever, burning cycles and owner attention on a
re-measurement it is forbidden to reinterpret.

**Remediation applied here.** This run leaves its delta in the working tree **uncommitted**,
which is precisely what the guard inspects; the workflow's own `Persist team snapshot` step
commits it afterwards. Committing this run's work would have reproduced exit 67 and re-armed the
loop.

**Handoff to the factory owner (not patched here — `.github/**` is outside this team's write
scope).** Suggested one-line change to that guard, in preference order:

```bash
# accept a durable delta that is already committed as well as one in the working tree
if git diff --quiet && git diff --cached --quiet && [[ -z "$(git status --porcelain -uall)" ]] \
   && [[ -z "$(git log --oneline "${BASE_SHA:-HEAD~1}"..HEAD)" ]]; then
```

i.e. compare the tree against the checkout base rather than against a clean tree. Until that
lands, the convention for Frontier producers is: **do not commit; let the workflow persist.**

## 4. Defects found and declared while verifying

Full list with impact analysis: `declared_corrections_this_run` in the verification record.

| id | what | severity | verdict effect |
|---|---|---|---|
| **D5** | `write_report` hardcoded `CYCLE_38792663259_REPORT.json` and overwrote it unconditionally — a later run could silently destroy another run's claim-bearing artifact (AGENTS.md rule 6) | MAJOR | none; body unchanged, still `b15ea198…` |
| **D6** | the harness re-hashed every input but recorded no evidence of it; the report body's `integrity` key was a hardcoded empty list | MAJOR | none |
| **D7** | `CYCLE_38792663259.md` §4 said "only **2** of 8 sit outside the consensus mega-cluster"; the report's own metric (d) column (0.33, 0.25, 1.00) and the raw bundles both give **3** | prose | none — it makes the placement finding *less* unfavourable to the product |
| **D8** | §7 headed "Two harness defects" then listed D1–D4 | prose | none |
| **D9** | the freeze commits `1d50633` / `4c83b45` are **not resolvable** in the published branch (the producer's history was squashed into `72ecb19`; no reflog, no dangling objects) | provenance | none |

Fixes for D5/D6: `--run-id` parameterises the output name; rewriting identical bytes is a no-op;
rewriting *different* bytes over an existing claim-bearing report raises `ReportOverwriteRefused`
and exits 4 unless `--overwrite` is explicit. Observed input hashes now travel in a per-run
`ENVELOPE` sidecar — deliberately **outside** the report body, so the frozen artifact stays
byte-stable. Three new tests cover the guard, including a CLI test that tampers with a report and
asserts the refused write leaves the bytes intact.

D7's corrected number is now recomputed from the report JSON by a test, so the prose cannot drift
from the data again. D9 is disclosed rather than repaired: re-authoring the missing commits would
fabricate provenance. Threshold immutability remains independently locked by
`test_thresholds_match_the_frozen_rules_file`.

## 5. Verdict and the single candidate cause — unchanged

> **`CLASSIFICATION_ONLY`.** 0 of 8 counter-authority rows across the 3 accepted bundles entered
> through a retrieval channel the initial broad pass did not use. The accepted
> `AdversarialPass(bundle, answer, …)` holds no retrieval client and selects a deterministic
> 24-decision shortlist, leaving 89.4% / 91.6% / 76.0% of the retrieved corpus structurally
> uninspected.

Exactly **one** bounded candidate cause is carried forward, unchanged from run 38792663259, with
the same evidence. **This resume adds no second cause** — the charter permits one. **This team did
not test any fix**; the remedy is product's.

## 6. Scope

Writes confined to `frontier/`, `tests/`, `results/`, `reports/` for this team plus
`state/frontier/frontier-adversarial-discoverability.json`. `product/`, `evaluation/`,
`results/product/`, `state/product.json` and `.github/` untouched. The citation-identity defect is
not re-litigated. Geometry was consumed read-only and is never asserted as a geometry verdict.
The accepted mount was read-only throughout.

**Audit artifacts.** `results/audit/frontier/frontier-adversarial-discoverability/CYCLE_<run_id>_GATE.json`
and `reports/audit/frontier/frontier-adversarial-discoverability/CYCLE_<run_id>.md` were **not**
written by this team. They are outside the team scope guard (`Enforce team scope` exits 4 on any
path outside the five team prefixes) and are produced by the audit job into its own checkout, as
the charter's `operational_revision_reason` describes. All evidence the audit needs lives under
`results/frontier/frontier-adversarial-discoverability/`.

## 7. Continuation

`continue_recommended: false`. The charter's `stop_promote_rule` terminates this team after the
verdict plus one bounded candidate cause; both were delivered in 38792663259 and re-verified here.
The only defect found this run was in this team's own harness/report and is fixed. The remaining
work — giving the adversarial pass a retrieval capability, repositioning counter rows, revisiting
the status gate — is product-owned, and per the charter's `lane_discharge` fallback it should be
folded into product backlog item (4) / the evaluation lane rather than continued as a Frontier
program.
