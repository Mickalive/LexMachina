# frontier-counter-label-integrity — run 38848314260

**Charter v1 · cycle: harness-defect repair under the charter's sole continuation clause**
**Verdict: UNCHANGED — `LABEL_UNSOUND` (primary 0 / 7, replication 0 / 39)**
**`continue_recommended: false`**

---

## Why this cycle was not a fourth no-change verification

Runs `38841035773`, `38845649012` and `38846758718` each re-dispatched this terminated charter and each
re-verified the same mount to the same result. Each also reported the same thing: the test suite is
**64 passed / 2 failed**, and neither run fixed it.

The charter permits one more cycle and only one:

> "Continue under the same charter **ONLY** for a concrete defect in this team's own harness."

That is a concrete defect in this team's own harness. So this cycle spent the clause: it found the
defect, repaired it, had the repair independently attacked, hardened the repair against what the
attack found, and changed nothing about the measurement.

**No label was re-scored. No rule was re-frozen. No threshold moved. No bundle was re-measured.
The verdict is untouched.**

---

## The defect

`tests/frontier/frontier-counter-label-integrity/test_artifacts.py` globbed

```
results/audit/frontier/frontier-counter-label-integrity/CYCLE_*_GATE.json
```

into a single undifferentiated list and applied **the independent-audit contract** to every member:

- `gate in ("PASS", "REVISE")`
- `isinstance(required_fixes, list)`
- `safe_to_integrate is True or gate == "REVISE"`
- claim ceiling contains three exact-case literals

That directory legitimately holds **two different artifact classes**:

| class | files | `gate` | self-declares |
|---|---|---|---|
| independent audit of record | `CYCLE_38839354961`, `CYCLE_38841035773` | `PASS` | no — it *is* the audit |
| producer placement copy | `CYCLE_38845649012`, `CYCLE_38846758718` | `TERMINATE` | yes, via `artifact_provenance_warning` |

A placement copy records **the team's cycle disposition** under the charter's `stop_promote_rule`
(`TERMINATE`), not a product audit verdict. And the team's own charter carries a factory-wide
**AUDIT ARTIFACT PLACEMENT REQUIREMENT** that *mandates* writing placement copies into that exact
directory.

So the suite was **red by construction on every re-dispatch of a terminated charter**. Three
consecutive dispatches shipped a permanently failing suite.

That is worse than a wrong assertion. A wrong assertion is a bug. A permanently red suite teaches the
gate reader to ignore test failures — and the two files it flagged were, in fact, honest artifacts
doing exactly what they were supposed to do. Their claim ceilings carry all three substantive claim
limits; they differ only in wording and capitalisation from the literals the test hard-coded.

---

## The repair

New module `frontier_counter_label_integrity/audit_contract.py` routes each gate artifact to the
contract of its own class and validates it. `test_artifacts.py` dispatches by class.

### Why this is not benchmark weakening

`AGENTS.md` forbids weakening a frozen benchmark. It does not weaken one:

1. **The independent-audit contract is enforced verbatim**, exact-case literals included.
   *Proven by mutation:* downcasing `BASELINE ONLY` in the real audit of record still fails.
2. **A new anti-vacuity invariant** requires at least one independent audit of record to exist and
   forbids any unclassified artifact. Routing the classes apart therefore **cannot** make the audit
   requirement vacuous — which is exactly what a naive "just skip the placement copies" fix would
   have broken. *Proven by mutation:* deleting both audits of record fails the tree.
3. **The placement-copy contract is new.** It was previously enforced not at all. Nothing was relaxed
   to add it.
4. **`RULES.json` is frozen and untouched** — `4457e971…`, and `git diff 416c2aec..207447c2` on it is
   **0 lines**.
5. **No historical artifact was edited or deleted.** `git status` shows one modified test file and two
   new files. Nothing under `results/` or `reports/` changed.
6. **Net assertions went up**: 64 passed / 2 failed → **96 passed / 0 failed**.

---

## The repair was attacked, and the attack found real defects

An independent fresh-context subagent was given the role of *refuting* the change, with the
pre-change test file, the frozen hashes and the benchmark-weakening rule as its brief. It returned
`LEGITIMATE_HARNESS_REPAIR` — and found genuine defects **in the first version of my own fix**:

> The normalized claim-limit matcher was **vacuous**. A fallback regex dropped the `supporting`
> anchor, so a 53-character ceiling — `"no assert contrary limiting baseline only 38828034436"` —
> passed. So did the **semantic inverse** of this team's own ceiling: *"Every specific decision IS
> supporting, contrary and limiting. No assertion limit applies."*

That is **weaker** than the pre-change test on that dimension, so my first "strictly stronger" claim
was simply false. It also found that invented verdicts (`PASS_WITH_CAVEATS`, `AUDIT_PASS`) passed a
denylist of `{PASS, REVISE}`, that the provenance-warning check accepted self-contradicting text, and
that class routing was purely self-declared.

All of it was then fixed:

| finding | repair |
|---|---|
| vacuous / inverted claim ceiling accepted | negation + assertion verb + `supporting` + `contrary` + `limiting` required **within one sentence** |
| invented verdicts passed a denylist | changed to a **closed allow-list** of cycle dispositions |
| incomplete audit-only key denylist | extended to 6 authority-claiming keys |
| self-contradicting provenance warning | now rejected explicitly |
| class routing purely self-declared | routing requires the **full audit signature**; anything ambiguous is `UNCLASSIFIED` and fails the tree |
| non-string `claim_ceiling` skipped the literal check | non-string is itself a failure |

After hardening, **all eight replayed exploits are rejected**, including the semantic inverse, and all
three honest ceiling phrasings are still accepted. The reviewer's one declared residual weakness is
real and inherent: a producer file carrying the complete audit signature is indistinguishable from a
genuine audit by any test. That is a property of the artifact medium, not of this contract.

Seven mutation probes were run against the whole audit tree; all adversarial mutations fail, all
honest artifacts pass.

---

## Verification performed this cycle

| check | result |
|---|---|
| 9 frozen inputs + 5 fixture exclusions + 3 admissibility siblings re-hashed | all match |
| `RULES.json` / `REPORT.json` / `NON_VACUITY.json` / `FREEZE_PROOF.json` sha256 | all match state claims |
| freeze ordering re-proven from git commit times | `416c2aec` 02:22:36Z → `0849f6ed` 02:29:04Z, **388 s margin**, `RULES.json` diff **0 lines** |
| `FREEZE_PROOF.json` regenerated from the original branch | **byte-identical** `7ca4d133…` |
| `REPORT.json` reproduced (`--all`, 9 bundles) | **byte-identical** `e97a4e9c…` |
| CLI form 2 — `--bundle fr-bail-entretien` | correctly returns `INSUFFICIENT_POPULATION`, both gaps named |
| CLI form 3 — `--non-vacuity-only` | passed, **7/7** classes, **5** defect criteria |
| post-repair artifact probe | negative — no `adversarial_retrieval.py`, no `results/product/adversarial_retrieval/` |
| mount population | unchanged; no new counter-issuing accepted bundle |
| test suite | **96 passed, 0 failed** (was 64/2) |

---

## Claim ceiling

**This cycle may claim:** the accepted-chain verdict is unchanged and re-reproduced byte-identically
under a rubric frozen before any label was scored (proven from git commit times); this team's own test
harness contained a concrete defect that made its suite red-by-construction; that defect is repaired,
the repair was independently attacked, and the attack's findings were hardened against and
regression-covered.

**This cycle may NOT claim:**

- that any specific decision **is** supporting / contrary / limiting — those labels remain the
  product's, reported and **not endorsed**;
- that any fix would work — **none was tested**, and no lexicon, threshold, prompt or patch is proposed;
- that the audited non-accepted run `38828034436` is an accepted-chain support rate — it is mechanism
  evidence only and is quoted nowhere as a rate;
- anything about map geometry or cluster semantics — that is `frontier-map-semantics`' lane;
- any post-repair result — **no post-repair artifact exists** on the accepted mount.

---

## Disposition

**`continue_recommended: false` · `cycle_status: TERMINATE`**

The charter's single continuation clause has now been invoked and spent. The harness has no known
open defect: every mutation probe and every adversarial exploit is caught, and every honest artifact
passes. The charter forbids re-measuring the same bytes, re-measuring an already-measured bundle,
re-verifying the machine gate, and re-running `frontier-generative-audit`; none was done.

The one thing that would justify future work — **re-measuring against a promoted product repair to
form a before/after pair with this same frozen `RULES.json`** (`4457e971…`) — is a **new charter**,
and it is the director's to raise, not this team's to continue.

Product backlog item (4) may adopt `LABEL_UNSOUND` as the external falsification of the accepted
chain's counter-label support. It may not read it as a pass of the D2 fix, because no fix was tested.
