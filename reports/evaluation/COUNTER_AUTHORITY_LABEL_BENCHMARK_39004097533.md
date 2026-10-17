# COUNTER-AUTHORITY LABEL BENCHMARK — run 39004097533

**Verdict: `PRODUCT_FALSIFIED` (exit 1). Non-vacuity battery 4/4 proven. Five gate
predicates fired.** First-class negative results on both the product's
counter-authority label axis and the accepted frozen counter-label gate.

Entry point: `python -m evaluation.counter_authority_label_benchmark --run-id <id>`
Record: `results/evaluation/counter_authority_label_benchmark/39004097533.json`
Frozen hypothesis: `results/evaluation/counter_authority_label_benchmark/FROZEN_HYPOTHESIS_39004097533.json`
(frozen at commit `10135a0f`, **before** the module existed or was executed once)
Direction version 50 · lane `evaluation` · run `39004097533`

---

## 0. What this benchmark is, in one paragraph

The standing accepted DO-NOT-SERVE order rests on a counter-label bar:
`support 5/65 = 0.0769` against a frozen absolute bar of `1.0`. Accepted cycle
38993062549 already falsified the **geometry** half of the two frozen gates as
CI packet-admission gates (their regression verdict is anchor-determined on the
product's own lineage). The **label** half had not been tested at all, and it is
the half the DO-NOT-SERVE order actually rests on. This benchmark is the smallest
executable test of two falsifiable questions on **real accepted product
artifacts**, with the **identical frozen rubric**, and with no new threshold:

* **Q1 (product axis)** — did the accepted pre-repair → post-repair repair improve
  counter-label support?
* **Q2 (bar axis)** — is the accepted counter-label gate observable on, and safe
  as packet admission over, the product's own accepted lineage?

No classification is asserted here. This lane measures the **support of the labels
the product issued**; it never says a named decision *is* contrary or limiting.
A self-policing scan over the whole record using the accepted
`forbidden_construction_patterns` (5 patterns, sha `511962a9…`) reports **0
violations**.

---

## 1. Q1 — the product's counter-label support did NOT improve

Frozen predicate **L1**: *after* support_rate > *before* support_rate pooled over
DE/FR/IT under the matched anchor **AND** no INVERTED-class row in *after*.

| arm | artifact (accepted product mount) | scored | supported | support_rate |
|---|---|---:|---:|---:|
| BEFORE | `adversarial_retrieval/38828034436/bundle_{de,fr,it}.json` | 70 | 11 | **0.1571** |
| AFTER | `adversarial_retrieval/38831241913/bundle_{de,fr,it}_repaired.json` | 58 | 7 | **0.1207** |

**L1 does not hold. Δ = −0.0365.** By the success rule committed before
execution, that is `PRODUCT_FALSIFIED`.

### 1a. Language robustness on the counter axis (FR/DE/IT)

This is the lane-directive requirement, and it is the sharpest single result:

| language | before | after | Δ rate | before classes | after classes |
|---|---|---|---|---|---|
| **de** | 7/29 = 0.2414 | 6/29 = 0.2069 | −0.034 | OFF-DOMAIN 6, SUPPORTED 7, UNBACKED 16 | OFF-DOMAIN 8, SUPPORTED 6, UNBACKED 15 |
| **fr** | **0/24 = 0.0000** | **0/22 = 0.0000** | 0.000 | OFF-DOMAIN 14, UNBACKED 9, **INVERTED 1** | OFF-DOMAIN 17, UNBACKED 5 |
| **it** | 4/17 = 0.2353 | 1/7 = 0.1429 | −0.092 | FRAGMENT 2, INVERTED 1, OFF-DOMAIN 2, SUPPORTED 4, UNBACKED 8 | FRAGMENT 1, OFF-DOMAIN 2, SUPPORTED 1, UNBACKED 3 |

**Not one French counter-authority label is supported by its own cited evidence,
before or after the repair (0 of 24, then 0 of 22).** The repair did not touch
that. Pinned by
`tests/evaluation/test_counter_authority_label_benchmark.py::test_french_counter_rows_are_never_supported_in_either_arm`.

### 1b. The part of the repair that genuinely worked — not explained away

* **INVERTED rows: 2 → 0.** The repair eliminated both affirmatively inverted
  labels the audit had named. That is a real, correctly-attributed improvement
  and it is reported here with the same prominence as the regressions.
* Pooled `UNBACKED` share 0.471 → 0.397; `FRAGMENT` 2 → 1.
* Counter-label yield falls exactly where the product's own report says it does:
  `reports/product/CYCLE_38831241913.md` records "most sharply on IT (12 → 2),
  because 10 of the 12 old IT labels were the off-domain / boilerplate / inverted /
  fragment class the audit named". My independent scoring agrees on the removal
  (IT scored rows 17 → 7) and adds what that report does not measure: **of the ten
  removed IT labels the repair also removed three SUPPORTED ones**, and the seven
  survivors contain only one supported row.

### 1c. Disclosed confound — and why it does not rescue the product

The two arms carry the **same query text** but **not the same retrieved decision
population**: de swaps 14 rows out / 12 in, fr swaps 22 / 24, it swaps 2 / 0. The
repair also changed the probe plan (product audit fix **D1** re-interleaved DE/FR/IT
probe terms), so this is not a pure labelling repair of one candidate set.

A pooled rate delta across two different candidate sets mixes the repair effect,
retrieval non-determinism and anchor-fit. So the record also carries
`shared_id_sensitivity`: both arms re-scored restricted to the decision ids they
**share**, isolating the labelling effect.

| arm | pooled on shared ids | support_rate |
|---|---|---:|
| BEFORE | 11/53 | 0.2075 |
| AFTER | 6/44 | 0.1364 |

**Δ = −0.0712, i.e. controlling for retrieval non-determinism makes the product
result WORSE, not better.** Per language on shared ids: de −0.080, it −0.092,
fr 0.000.

The control was added **after** the confound was discovered and was deliberately
**not** allowed to relax the frozen rule. `enforced: false`,
`part_of_frozen_predicate_L1: false`. Using a post-hoc confound analysis to rescue
the product would be exactly the laundering this lane exists to prevent; reporting
it is mandatory either way.

### 1d. Anchor-fit sensitivity (why the anchor choice is not cherry-picked)

Every artifact was scored under **all five** frozen anchors. `kuendigung-mietrecht`
is the most generous anchor available by a wide margin:

| artifact | matched anchor | best alternative anchor | margin |
|---|---:|---:|---:|
| before de | 0.2414 | 0.0000 | **+0.2414** |
| before it | 0.2353 | 0.0000 | **+0.2353** |
| before fr | 0.0000 | 0.0000 | 0.0000 |
| after de | 0.2069 | 0.0000 | **+0.2069** |
| after it | 0.1429 | 0.0000 | **+0.1429** |

The falsification therefore holds under the anchor most favourable to the product.
On FR every anchor gives 0.0000, so the French result is anchor-independent.
Descriptive, `enforced: false`.

---

## 2. Q2 — the accepted counter-label gate cannot see a collapse of label support

All three accepted packets carrying the three frozen qids, scored by the
**accepted** `label_gate.score_packet`:

| packet | n_scored | n_supported | support_rate | lineage matches incumbent | regression_verdict | gate_blocks_build |
|---|---:|---:|---:|---|---|---|
| 38799024807 (pre-repair) | 7 | **0** | **0.0000** | false | `NOT_APPLICABLE` | **false** |
| 38812599575 | 9 | 1 | 0.1111 | false | `NOT_APPLICABLE` | **false** |
| 38839347028 (incumbent) | 65 | 5 | 0.0769 | true | `PASS_NO_REGRESSION` | false |

The incumbent reproduces the accepted numbers of record **exactly**: 65 scored, 5
supported, classes `OFF-DOMAIN 38 / UNBACKED 22 / SUPPORTED 5`, geometry untouched.

### The five fired gate predicates

* **L2 — the gate admits a total label collapse.** Packet 38799024807 has
  **zero supported counter labels out of seven**. Its support rate (0.0000) is
  strictly worse than the incumbent's (0.0769) *and* its supported count (0) is
  below the incumbent's (5). The accepted gate still returns
  `NOT_APPLICABLE` with `gate_blocks_build = false`. **A complete failure of the
  axis the DO-NOT-SERVE order is predicated on is invisible to the gate as a build
  blocker.**
* **L3 — the population predicate is confounded with counter-row volume.** The
  regression predicate fires only at `n_scored == 65` exactly, over exactly the
  three frozen qids. Admissible packets: **1 of 3**. The scored-row population
  across the accepted lineage is 7 / 9 / 65 — the predicate keys on how many
  counter rows the classifier emitted, not on their quality.
* **L4 — rate and count semantics disagree.** Packet 38812599575 has a
  *strictly better* support rate (0.1111 > 0.0769) and a *worse* supported count
  (1 < 5). At a matched population the gate would **FAIL an artifact with a
  strictly better support rate**: the regression predicate is an absolute count at
  a fixed population, while the absolute bar is a rate.
* **L6 — the anchor ordering is not a quality ordering.** By supported count the
  lineage orders `38799024807 < 38812599575 < 38839347028`; by support rate it
  orders `38799024807 < 38839347028 < 38812599575`. The gate's verdict is a
  monotone function of the **declared anchor's row count**, not of measured label
  quality — the label-side counterpart of accepted finding F5 for geometry.
* **L5 — the frozen rubric and the gate incumbent describe different bars.**
  Compared as **set relations with both differences computed**, never by matching
  cardinality: the incumbent packet's three bundle shas (`2441ff2b…`, `6c5ea31d…`,
  `76e7f7ad…`) are **not among the shas RULES_LABEL.json declares** (`declared_not_incumbent`
  9, `incumbent_not_declared` 3), and `required_min_population_primary = 7` ≠
  `label_gate.INCUMBENT["n_scored"] = 65`. The frozen rubric's own
  `populations.primary.definition` names **packet 38799024807** — the *zero-support*
  packet, whose bundles are also the geometry rubric's declared inputs.
  **Re-deriving, re-pointing or re-freezing RULES_LABEL.json is out of this lane's
  scope and was not attempted.** The divergence is recorded, not resolved.

### Proven non-vacuity — nothing above is vacuous

| element | result |
|---|---|
| N1 positive must fire | accepted `python -m evaluation.benchmark_retrieval_counter_authority` **unmodified**: `BENCHMARK_VALID_NO_FALSIFICATION`, `falsification_proven=true`, legs `{served_baseline: 0, geometry_falsification_hostile: 1, label_falsification_blanked_evidence: 1}` |
| N2 negative incumbent must not fire | `PASS_NO_REGRESSION`, `gate_blocks_build=false` |
| N3 rules identity | `RULES_LABEL` → `4457e971…`, `RULES_GEOMETRY` → `a7452748…`, both re-hashed **before** any scoring |
| N4 population sensitivity | synthetic incumbent at **64** rows → `NOT_APPLICABLE`, `gate_blocks_build=false`; at **66** rows → `NOT_APPLICABLE`, `gate_blocks_build=false`. **L3 is structural, not a data accident** |
| N5 provenance | all 6 artifacts re-hashed on the mount; every gate-packet bundle sha re-hashed from the bytes the gate actually read |

A battery element failing would have forced `ENVIRONMENT_OR_UNPROVEN` and
suppressed every finding. That is what happened on the first execution of this
cycle (an N1 record-shape mismatch in my own harness) and it is the reason the
first run is recorded as exit 2 rather than quietly patched into a pass.

---

## 3. Provenance limits, stated rather than glossed

1. **No independent audit gate for the adversarial arms is on the accepted
   product mount.** All six Leg-1 artifacts classify as
   `product_artifact_without_on_mount_audit_record`. The audit of the pre-repair
   cycle **did** happen (`results/audit/product/CYCLE_38828034436_GATE.json`,
   gate=REVISE, fixes D1–D4, cited by the accepted
   `reports/product/CYCLE_38831241913.md`), but that gate file lives on an audit
   branch, not on the mount, so the benchmark's provenance is **byte re-hashing of
   the artifacts themselves** rather than an audit citation. The falsification is
   therefore pinned to artifact bytes, not to an audit verdict.
2. Packet 38839347028 has no audit record on the mount either; it is identified by
   the accepted product verdict adoption file, which names it
   (`measured_packet: gate_packet/38839347028`, `covers_this_packet: true`).
3. The anchor mapping `adversarial_retrieval → kuendigung-mietrecht` is an
   **inference** from each artifact's own query string plus its
   `MEASUREMENT.json` artifact path. It is not a claim that the product labelled
   these bundles that way. §1d bounds the consequence.
4. `relabel_*_old_rows.json` ledgers, the `38838116453` row-tracking run and the
   duplicate `bundle_mietvertrag_kuendigung.json` are recorded **out of scope with
   reasons** in the record, never silently dropped.

---

## 4. What was deliberately NOT done

* No threshold invented. L2–L6 are restatements of the accepted gate semantics and
  the accepted `label_gate.py` source, not new bars.
* No frozen rubric, incumbent, gate success rule or recorded verdict modified.
  `RULES_LABEL.json` and `RULES_GEOMETRY.json` re-hash byte-identically.
* The absolute `LABEL_SOUND` bar (`support_rate == 1.0`) is **reported, never
  enforced**, exactly as direction v50 requires — pinned by a red-before/green-after
  test that fails if the record ever marks it as a build blocker.
* The two Frontier candidates under construction were **not** re-measured; only
  product artifacts on the accepted mount were scored.
* No universal-174k benchmark rerun. No network. DNS to `mcp.opencaselaw.ch` is
  unavailable in this container and no live fetch was attempted.
* No Product code imported; no `.github/**` edit; no audit artifact authored.
* `evaluation/benchmark_retrieval_counter_authority.py` left byte-unchanged and
  executed unmodified as N1.

---

## 5. Product decision unlocked (no owner gate required)

* **Product obligation (1) cannot be wired on `gate_blocks_build` alone.** L2–L4
  and L6 say a packet with zero supported counter labels is admitted with
  `gate_blocks_build=false`. The safe wiring already exists and is published:
  admit on **`absolute_status` + the rubric's own `verdict_rule`**, read through
  the accepted `VERDICT_CONTRACT.json` `admission_reading` — never on
  `gate_blocks_build` in isolation. This needs no owner decision and no new bar.
* **Counter-label support on the reality query regressed.** The most actionable
  single item: FR is 0-for-N in both arms. Any fix must be judged on
  support_rate **at a declared population**, and the population must be declared
  before the result is seen — that is the defect L3 exposes.
* **The standing accepted DO-NOT-SERVE order is unchanged** by this cycle. It was
  already in force and this result strengthens its factual basis (the product's
  counter-label support is worse on the reality query than on the gate-packet
  query), but it does not move any bar and does not unblock the human product gate.

## 6. Recommendation

**PIVOT_WITHIN_MISSION.** The v50 two-gate question stays delivered; this cycle did
not rebuild it, it tested its label half on real product artifacts and produced the
lane's first product-level falsification of the counter-authority labelling.
`continue_recommended = true` for one concrete successor: a **declared-population**
re-freeze question for the counter-label bar, which is the only thing that makes
obligation (1) enforceable, and which is a control-plane decision because it
touches a frozen rubric.