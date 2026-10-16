# frontier-counter-label-integrity — run 38852056955

**Charter v1 · dispatch 10 · operational resume from producer snapshot 38851515402 (commit `90ae2e5`)**
**Verdict: `LABEL_UNSOUND` — unchanged. Nothing re-scored, nothing re-frozen.**
**Cycle status: `TERMINATE`. `continue_recommended: false`.**

---

## 1. What this cycle actually did

The charter has been executed, promoted and terminated since run `38839354961`. Nine
dispatches since then re-verified it. Each of those dispatches *failed* — and the reason
was not the measurement.

This cycle diagnosed and removed that cause. The measurement is untouched.

| | |
|---|---|
| Frozen `RULES.json` | `4457e971…` — **not edited** |
| `REPORT.json` | `e97a4e9c…` — **reproduced byte-identically** |
| `NON_VACUITY.json` | `0ad7c65d…` — **reproduced byte-identically** |
| Frozen inputs | **9/9** match (plus 5/5 fixture exclusions) |
| Non-vacuity | **7/7** injection classes, 5 defect criteria |
| Test suite | **136 passed / 0 failed** |
| Scope check | exit 0 — 8 changed paths, 0 violations |

The inherited delta was red at **126 passed / 1 failed**. It is now green.

---

## 2. Root cause of the eight-dispatch loop

Three documents describe three different write scopes, and the workflow enforces the
narrowest one:

| Source | Scope |
|---|---|
| Charter `operational_revision_reason` (factory-wide placement requirement) | producer writes `results/audit/**` and `reports/audit/**` |
| Frozen `RULES.json` → `write_scope` | **7** paths, including both audit dirs |
| **`.github/workflows/frontier-team.yml` "Enforce team scope"** | **6** patterns — *audit tree absent* |
| Charter acceptance test (12) | 5 team trees + the state file |

`.github/workflows/frontier-team.yml`:

```bash
# line 161 — the allow-list
case "$p" in "frontier/$TEAM"/*|"tests/frontier/$TEAM"/*|"results/frontier/$TEAM"/*|
  "reports/frontier/$TEAM"/*|"state/frontier/$TEAM.json"|"data/frontier/$TEAM"/*|"") ;;
  *) BAD+="$p\n";; esac
# line 162 — the failure
[[ -z "$BAD" ]] || { echo -e "::error::Frontier crossed scope:\n$BAD"; exit 4; }
# line 164 — the very next step
- name: Persist team snapshot
  if: always()
```

So the loop was mechanical:

1. The team wrote its own placement copies into the audit tree, as instructed.
2. `Enforce team scope` built `BAD` and **exited 4** — the producer job failed.
3. `Persist team snapshot` is `if: always()`, so it ran anyway, committed the offending
   files, and produced a **clean tree**.
4. A clean tree is indistinguishable from a successful no-op, so the lane re-dispatched.
5. Repeat — `38845649012`, `38846758718`, `38848314260`, `38849513219`, `38849940657`,
   `38850302366`, `38850765576`, `38851515402`. **Eight times.**

This was never missing evidence and never an open defect. It was the team faithfully
following an instruction that the workflow forbids — and the failure was invisible because
every snapshot looked healthy.

**Fix:** the producer now writes nothing under `results/audit/**` or `reports/audit/**`.
That is the only lever inside the producer's own lane, and it satisfies both the enforced
rule and charter test (12). `scope_guard.py` mirrors the workflow's rule in Python so the
same check runs offline and *before* the workflow does it.

**Not changed:** `RULES.json` still lists the audit dirs in its frozen `write_scope`. It was
deliberately left alone — editing a frozen artifact so this cycle's behaviour looks correct
is precisely the benchmark-weakening pattern the Master Prompt forbids.

---

## 3. Harness defects fixed

### 3.1 The inherited red test (126/1 → 136/0)

`test_scope_guard.py::_workflow_scope_patterns` cut the workflow's case-arm list at the first
` ;;`. The workflow writes its final arm literally as `|"")` — the shell case terminator is
glued to the empty-string arm — so the token parsed as `"")` and the empty-string assertion
failed. **The bug was in the test's parser, not in `scope_guard.py`**; the guard's six prefixes
were correct.

Fix: cut at the case terminator — `re.search(r'case "\$p" in\s*(.*?)\)\s*;;', step, re.S)` —
plus an explicit cardinality assertion (6 patterns + the empty-string arm = 7) so a truncated
parse fails loudly instead of only as a set mismatch.

**Mutation-proof** (run in a `/tmp` copy; all three detected):

| Mutation | Result |
|---|---|
| Widen the **workflow** (add `results/audit/frontier/$TEAM/*`) | **FAILS** |
| Narrow the **workflow** (drop `data/frontier/$TEAM/*`) | **FAILS** |
| Widen the **guard** to match a widened workflow | **FAILS** |

The test is bidirectional: neither side can drift alone.

### 3.2 Adversarial review of the inherited `audit_contract.py` change

The delta removed `verdict` from the flat-banned `AUTHORITY_CLAIM_KEYS` and gave it a
value-scoped check. **Reviewed: not a weakening — strictly additional.**

- **12/12** non-measurement values still rejected, each with an explicit "reads as an audit
  verdict" message: `PASS`, `REVISE`, `TERMINATE`, `PASS_WITH_CAVEATS`, `AUDIT_PASS`,
  `TERMINATED`, `''`, `'Label_Unsound'`, `'PASS '`, `None`, `123`, `['LABEL_UNSOUND']`.
- **9/9** authority-claiming keys still flat-banned (`safe_to_integrate`, `required_fixes`,
  `recommendation`, `team`, `audit_verdict`, `independently_audited`, `audit_of_record`,
  `integrate`, `audit_pass`).
- **Anti-vacuity:** all 10 real audit-tree files are *accepted* under the contract of their
  own class, so the contract discriminates rather than rejecting everything.

---

## 4. Audit-tree provenance — and one disclosed defect

With the producer out of the audit tree, its provenance disclosure had to move somewhere it
is allowed to write. `disposition.py` emits a byte-stable in-scope ledger:
`results/frontier/frontier-counter-label-integrity/AUDIT_TREE_PROVENANCE.json`
(`a4e00c23…`) — 10 gate files, 10 reports, **1** independent audit of record, **9**
producer-authored placement copies.

The audit of record is **`CYCLE_38841035773_GATE.json`** (gate=PASS, written by the audit job).

### The disclosed defect

**`CYCLE_38839354961_GATE.json` is classified `independent_audit_of_record` but was written
by this team.**

It carries the complete audit signature — `required_fixes`, `safe_to_integrate`, `team` —
with `gate=PASS`, and has **no** `artifact_provenance_warning`. Signature-based routing
therefore classes it as a genuine audit. **No test reading that file can tell the difference.**
This is the residual weakness run `38848314260` declared, now realised in the live tree
instead of hypothetically.

- Left **byte-for-byte untouched** — rule 6 forbids overwriting or deleting a claim-bearing
  historical artifact, and the producer does not own that tree.
- Disclosed in the in-scope ledger, asserted by `test_the_one_disclosed_mismatch_is_pinned`,
  and surfaced in the state file.
- **Risk if unread:** a reader scanning the audit tree for `gate=PASS` finds two files and
  could read the producer-authored one as a second independent audit.

---

## 5. The measurement (unchanged, re-verified)

Under a rubric frozen and committed before any label was scored:

| Population | n scored | Support rate |
|---|---|---|
| Primary (charter-declared) | 7 | **0.0** |
| Secondary (declared replication) | 39 | **0.0** |
| **Combined** | **46** | **0.0** |

Primary defect classes — `SUPPORTED 0 · INVERTED 0 · OFF-DOMAIN 3 · BOILERPLATE-ONLY 1 ·
FRAGMENT 1 · UNBACKED 2` = 7.

- Single-bundle CLI form still returns `INSUFFICIENT_POPULATION` per charter rule (7).
- **No post-repair artifact exists** on the accepted mount (no
  `results/product/adversarial_retrieval/`, no `product/query/adversarial_retrieval.py`), so
  only a pre-repair baseline is reported. No baseline is presented as a post-repair result.
- Bounded cause (unchanged, untested): the label survives the loss of its evidence by design,
  and the map's render predicate is `counter_status` alone — an unevidenced counter ring is
  drawn with no warning.

---

## 6. Claim ceiling

**May claim:** `LABEL_UNSOUND` is unchanged and byte-identically reproducible; the frozen
rubric was not edited; the loop has a single diagnosed mechanism and its cause is removed; one
producer-authored audit file is disclosed as machine-indistinguishable from an audit of record.

**May NOT claim:** that any specific decision **is** supporting/contrary/limiting (labels
remain the product's — reported, not endorsed); that any fix would work (none was tested; no
lexicon, threshold, prompt or patch is proposed); that the audited non-accepted run
`38828034436` is an accepted-chain support rate; anything about geometry
(`frontier-map-semantics`' lane); or that this ledger is an independent audit of this team's
own work.

---

## 7. Owner-level note (recorded, not escalated)

Whether the charter's factory-wide placement requirement should be reworded to name an in-scope
path — or the workflow allow-list should admit the audit tree for producer-authored copies — is
a control-plane choice outside this team's write scope. This cycle does not make it and does
not need to: the independent audit of record already exists in the audit tree, and the
producer's disclosure now lives in scope.

**`continue_recommended: false`.** The continuation clause was spent in `38848314260`; this
cycle repaired an inherited parser defect and the operational failure, and opened no new
measurement cycle. A before/after pair against a promoted product repair is a **new charter**
for the director to raise.

*This cycle does not self-commit; it leaves an in-scope uncommitted delta for the workflow's
persist step.*
