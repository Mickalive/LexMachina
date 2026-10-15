# Integration contract — `frontier-adversarial-discoverability` → product

**Product owns every change named here.** This team measured; it did not modify, and will
not modify, any product, evaluation or human-gate artifact. This contract exists so the
measured finding can be acted on without re-deriving it.

Claim-bearing input: `results/frontier/frontier-adversarial-discoverability/CYCLE_38792663259_REPORT.json`
(sha256 `b15ea198c2df9a1bedeaff6a33d12d96153a84e331f8ce91e601c124292006bd`), frozen against
`RULES.json` (sha256 `5e78d8f156b99d220e34037d829f44ac66e70a597e2073013a4b82adb42a674b`).

---

## 1. The measurement, restated as a contract test

Product may import this team's harness and run it against any future bundle as a regression
gate. Nothing below is required for the product to ship; it is required only for the product
to *claim* independent adversarial retrieval.

```python
import sys
sys.path.insert(0, "frontier/frontier-adversarial-discoverability")
from adversarial_discoverability import harness

# bundle_path: a query_result_bundle v1.0 emitted by the product
report = harness.measure(json.load(open(bundle_path)), with_shortlist=True)

# The claim under test, exactly as the Master Prompt states it:
# "run an independent adversarial retrieval pass against the provisional answer"
assert report["verdicts"]["retrieval_independence"] == "PASS"   # currently FAIL on 3/3 accepted bundles

# The gate-question-1 claim, if product wants to make it:
assert report["verdicts"]["discoverability"] == "PASS"           # currently FAIL on 3/3
```

`harness.measure` is pure: dict in, dict out, no network, no clock, no writes. It needs the
accepted `generative_audit` tree on `sys.path` only for the shortlist replay
(`LEX_PRODUCT_MOUNT`, default `/tmp/lex_accepted/core/product`); without it, metrics (b5)/(b6)
report `NOT_APPLICABLE` and every other metric still computes.

## 2. What product owns, per the single candidate cause

The measured cause is architectural: `AdversarialPass` receives `(bundle, answer)` and holds
no retrieval client. Consequently the options below all belong to product. **This team did
not test any of them and makes no recommendation among them.**

| owner | change | what would make the frozen metric move |
|---|---|---|
| **product** | give the adversarial pass a retrieval capability (an adapter with its own channel, e.g. a negation/distinguishing query variant issued against OpenCaseLaw) and record its requests under a distinct provenance stage | (b) `b1_adversarial_channel_rows` > 0 — requires a channel outside `{search, search.language_filter, leading_case, citation.outgoing, citation.incoming}` on counter rows |
| **product** | widen or re-seed the challenge shortlist so minority/late authority is reachable | (b) `b6_pool_never_seen_rate` below 0.5 (currently 0.89 / 0.92 / 0.76) |
| **product** | place counter rows positionally — an explicit counter cluster, or `is_outlier` | (d) `discoverable_placement_share` ≥ 0.50 (currently 0.33 / 0.25 / 1.00; `is_outlier` is 0/8 today) |
| **product** | adjust the status gate's evidence requirement if the 0.9% yield on B1 is judged too conservative | (a) `counter_yield` ≥ 0.02 (currently 0.0132 / 0.0139 / 0.0100) |
| **frontier-query-retrieval** | only if a new retrieval channel is added upstream — it owns `ocl_adapter` and the channel vocabulary | would define the channel name that (b) then measures |

## 3. What this team will not do

Per charter `stop_promote_rule`, this team terminates after the verdict plus the one bounded
candidate cause. It will **not**:

- propose or test a fix;
- do prompt engineering, provider work, or benchmark construction;
- patch the product;
- offer a second candidate cause;
- write a human-gate answer or touch `human_gate_ready`;
- assert that any case is supporting / contrary / limiting.

## 4. Where the evidence sits

| artifact | purpose |
|---|---|
| `results/frontier/frontier-adversarial-discoverability/RULES.json` | the frozen pre-registration (committed at `1d50633`, before any measurement) |
| `results/frontier/frontier-adversarial-discoverability/CYCLE_38792663259_REPORT.json` | the claim-bearing measurement: 7 metrics × 7 artifacts, thresholds, PASS/FAIL, non-vacuity, verdict |
| `results/frontier/frontier-adversarial-discoverability/CYCLE_38792663259_REPRODUCIBILITY.json` | byte-identity proof + the four declared harness corrections with impact analysis |
| `results/frontier/frontier-adversarial-discoverability/superseded/CYCLE_38792663259_REPORT_defect-v1.json` | preserved defective run (negative result kept as evidence) |
| `reports/frontier/frontier-adversarial-discoverability/CYCLE_38792663259.md` | the short report, named verdict and the single candidate cause |
| `frontier/frontier-adversarial-discoverability/adversarial_discoverability/` | the harness (populations, metrics, corruptions, shortlist replay, CLI) |
| `tests/frontier/frontier-adversarial-discoverability/` | 36 tests: synthetic metrics, corruption determinism, integrity abort, scope, and locks on the published numbers |

## 5. Audit-artifact placement — recorded, not silently resolved

The charter's `operational_revision_reason` asks for
`results/audit/frontier/frontier-adversarial-discoverability/CYCLE_<run_id>_GATE.json` and
`reports/audit/frontier/frontier-adversarial-discoverability/CYCLE_<run_id>.md`.

Those two paths are written by the **audit job**, which `.github/workflows/frontier-team.yml`
provisions separately and whose own scope guard permits exactly
`results/audit/frontier/<team>/**` and `reports/audit/frontier/<team>/**`. The **team** job's
`Enforce team scope` step hard-fails with `exit 4` on any path outside
`frontier/$TEAM/*`, `tests/frontier/$TEAM/*`, `results/frontier/$TEAM/*`,
`reports/frontier/$TEAM/*`, `state/frontier/$TEAM.json`, `data/frontier/$TEAM/*`.

A team-side write into `results/audit/` would therefore destroy the run and prevent the audit
that produces those files. This team writes **zero bytes** under `results/audit/` or
`reports/audit/` and supplies the auditor its evidence at the paths in §4.
