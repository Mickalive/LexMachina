# Frontier - Counter-Evidence Span Selection (charter v1)

**Run:** `39986101767`
**Branch:** `lab/frontier/frontier-counter-evidence-span-selection`
**Protocol freeze commit:** `dad93c36` (before any measurement)
**Protocol:** `results/frontier/frontier-counter-evidence-span-selection/PROTOCOL.json`
**Protocol sha256:** `b5d14121e86ea0b39c181aacef1c30d4a2788a4751af4cfa00c33189c0afb7ea`
**Frozen rubric sha256:** `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`
**Product mount HEAD:** `f4cd7d7c7d2dea09b2f4f4388072fdc517d5cf3e`
**Tests:** 19 passed (`python3 -m unittest discover -s tests/frontier/frontier-counter-evidence-span-selection`)
**Network calls / model calls:** 0 / 0

## 0. Executive summary

The deterministic extract-verify-abstain selector raises the packet-of-record-v3
emitted counter rows from **0/20 to 7/20** and all seven pass the frozen scorer
as written (`reason_code=supported`, support-among-emitted = 1.0, denominator
unchanged at 20). The baseline is reproduced exactly (20 scored / 20 abstained /
0 emitted, with the published abstention reasons), every adversarial control is
green, and two full candidate runs are byte-identical.

That is the **mechanical** outcome A. It is **not** a product result.

A post-hoc semantic audit of the seven quotes finds **zero clear legal
counter-authorities** for their questions:

- **4/7** are string coincidences licensed by the frozen anchor matcher's
  >=5-character prefix tolerance: `unter` matches `untergang` (3 rows) and
  `kapital` matches `kapitalverletzung` (1 row). The quoted passages are about
  voting rights, water-space construction, arson, and a corporate loan.
- **1/7** is a legitimate morphological prefix (`resili` for `resiliation`) but
  the quote is about the validity of a lease termination, not the maintenance
  defect in the question.
- **2/7** match `defaut` exactly, but the quotes are about appeal standing and an
  arbitration clause, not the maintenance defect.

The frozen scorer's `supported` label is a mechanical gate result, not a legal
judgment. The selector solved the mechanical gate; it did not solve the semantic
problem. **Product recommendation: `DO_NOT_ADOPT_AS_IS`.** The reusable
extraction/verification loop is sound; the frozen anchor profile and prefix
tolerance are the binding defect. A successor charter should test an
exact-token semantic gate (and/or better retrieval), not re-run this frozen
protocol.

## 1. What was frozen before measurement

`PROTOCOL.json` was committed at `dad93c36` before the baseline or candidate was
computed. It fixes:

- the deciding population (packet-of-record `39319405429`, 20 repair-promoted
  rows: 8 de / 8 fr / 4 it);
- the only extraction source (`decisions[].full_text` of the row itself);
- the span rule (verbatim window, 40-700 chars, at most 4 passages, intent
  marker + domain anchor + pivot anchor, no inversion, no pointer);
- the deterministic selection order (shortest window, earliest start);
- the abstain reason codes and their precedence;
- the baseline reproduction requirement and the success rule;
- the controls (swapped evidence, inverted evidence, seeded positive/negative,
  frozen injection rows, verbatim mutation and cross-decision quotes);
- the claim ceiling.

No field of the protocol was edited after execution. `PROTOCOL.sha256` matches
the committed payload, and every result artifact embeds the same digest.

## 2. Input verification

All frozen inputs re-hashed cleanly: 27 checks, 0 mismatches, product mount HEAD
matches the expected `f4cd7d7c...`, and the frozen rubric hash matches
`4457e971...`. Packet-of-record bundle hashes:

| qid | bundle sha256 |
|---|---|
| de-kapitalverletzung | `9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b` |
| fr-bail-entretien | `054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b` |
| it-responsabilita-medica | `345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b` |

The served packet `38839347028` was also re-hashed and measured as a **secondary
replication only**; it never decides the outcome.

## 3. Baseline reproduction (frozen scorer, as written)

The incumbent path is `apply_counter_emission_repair` followed by
`apply_anchor_labels` under the frozen rubric. It reproduces the published
packet-of-record-v3 record:

| qid | scored | abstained | emitted | support among emitted | yield | abstention reasons |
|---|---:|---:|---:|---:|---:|---|
| de-kapitalverletzung | 8 | 8 | 0 | 0.0 | 0.0 | `no_domain_anchor:1`, `no_intent_marker:2`, `pivot_absent:5` |
| fr-bail-entretien | 8 | 8 | 0 | 0.0 | 0.0 | `no_intent_marker:2`, `pivot_absent:6` |
| it-responsabilita-medica | 4 | 4 | 0 | 0.0 | 0.0 | `pivot_absent:4` |
| **overall** | **20** | **20** | **0** | **0.0** | **0.0** | |

The secondary served packet reproduces the accepted 65-row partition: 65
scored, 60 abstained, 5 emitted, 5 supported (support among emitted 1.0, yield
5/65 = 0.0769). Its per-bundle rows are de 25/23/2, fr 15/15/0, it 25/22/3.

## 4. Candidate measurement (span selection added before the same scorer)

The candidate applies the selector after the repair seam and before
`apply_anchor_labels`. It leaves `counter_status` unchanged and only replaces
evidence.

| qid | scored | abstained | emitted | evidenced | support among emitted | yield | frozen-scorer abstention reasons |
|---|---:|---:|---:|---:|---:|---:|---|
| de-kapitalverletzung | 8 | 4 | 4 | 4 | 1.0 | 0.500 | `evidence_absent:4` |
| fr-bail-entretien | 8 | 5 | 3 | 3 | 1.0 | 0.375 | `evidence_absent:5` |
| it-responsabilita-medica | 4 | 4 | 0 | 0 | 0.0 | 0.000 | `evidence_absent:4` |
| **overall** | **20** | **13** | **7** | **7** | **1.0** | **0.350** | |

Per-bundle emitted ids:

- **de:** `bge_105 II 114`, `zg_verwaltungsgericht_V 2012 _ 151`,
  `bge_146 II 304`, `bge_117 IV 259`
- **fr:** `bge_136 III 196`, `bge_140 III 583`, `bge_136 III 583`
- **it:** none

The selector's own abstentions (before the frozen scorer) are:

- de: `no_domain_anchor_in_retrieved_text:2`, `no_retrieved_text:2`
- fr: `no_domain_anchor_in_retrieved_text:2`, `no_qualifying_span:2`,
  `no_retrieved_text:1`
- it: `no_domain_anchor_in_retrieved_text:3`, `no_qualifying_span:1`

The secondary served packet is unchanged by the component because its rows do
not carry the repair promotion marker (`n_promoted=0`), so the selector has no
row to act on. This is a scope limitation, not a result: the component addresses
the packet-of-record's repair-promoted rows, not the already-issued 65 labels.

## 5. Controls and determinism

| control | observed | required |
|---|---|---|
| swapped-evidence scorer control | 0 emitted | strictly below candidate (7) |
| inverted-evidence scorer control | 0 emitted | strictly below candidate (7) |
| seeded positive row | 1 emitted | exactly 1 |
| seeded negative row | 0 emitted | exactly 0 |
| mutated quote (not in cited text) | 7/7 rejected | all rejected |
| cross-decision donor quote | 7/7 rejected | all rejected |
| frozen non-vacuity injection rows | 7/7 match expected reason | all match |
| denominator | 20 -> 20 | unchanged |
| deterministic rerun | `03a004cc...` = `03a004cc...` | byte-identical |

No clock, randomness, network, model call or cache write is involved. The
determinism hash covers the full candidate output; the two runs differ only in
the top-level `run_label` handling, which is constant here.

## 6. Post-hoc semantic audit (not part of the frozen verdict)

`SEMANTIC_AUDIT.json` asks a different question after the mechanical verdict is
fixed: was each emitted span licensed by a real anchor, or only by the frozen
prefix tolerance? It does **not** change any count, label or success condition.
It classifies each emitted row as `exact`, `morphological_prefix` or
`string_coincidence`.

| # | qid | decision | domain anchor (match) | pivot anchor (match) | quality | quote head |
|---:|---|---|---|---|---|---|
| 1 | de | `bge_105 II 114` | `kapitalverletzung` -> `kapital` (prefix) | `kapitalverletzung` -> `kapital` (prefix) | **string coincidence** | "Obschon an der Generalversammlung ... der Zins jeweils zum Kapital geschlagen ..." (corporate loan / capital contribution) |
| 2 | de | `zg_verwaltungsgericht_V 2012 _ 151` | `entscheidung` -> `entscheid` (exact) | `untergang` -> `unter` (prefix) | **string coincidence** | "Die Abstimmungsfreiheit gewährleistet ... direktdemokratischer Entscheidungen ..." (voting rights) |
| 3 | de | `bge_146 II 304` | `entscheidung` -> `entscheid` (exact) | `untergang` -> `unter` (prefix) | **string coincidence** | "Zulässig dürften - unter Berücksichtigung des Normzwecks ... Umbauten ... Gewässerraums ..." (water-space construction) |
| 4 | de | `bge_117 IV 259` | `entscheidung` -> `entscheid` (exact) | `untergang` -> `unter` (prefix) | **string coincidence** | "Es verweist auf BGE 97 IV 10 ... eine Brandstiftung (Art. 221 StGB) betraf ..." (arson) |
| 5 | fr | `bge_136 III 196` | `resiliation` -> `resili` (prefix) | `resiliation` -> `resili` (prefix) | **morphological prefix** | "Ceux-ci ne pouvaient dès lors valablement résilier ce contrat ... art. 282 CO." (validity of lease termination) |
| 6 | fr | `bge_140 III 583` | `defaut` (exact) | `defaut` (exact) | **exact** | "Par arrêt ... a déclaré irrecevable l'appel ..." (appeal standing) |
| 7 | fr | `bge_136 III 583` | `defaut` (exact) | `defaut` (exact) | **exact** | "À défaut d'une telle clause expresse ... art. 192 LDIP ..." (arbitration clause) |

Counts: **4 string coincidences, 1 morphological prefix, 2 exact; 7/7
mechanically supported; 0/7 clear legal counter-authorities for the question.**

Why the string coincidences happen: the frozen matcher accepts a token when its
first `min(len(token), len(anchor_stem))` characters match and the shared prefix
is at least 5 characters. `unter` (a common preposition) therefore satisfies
`untergang`; `kapital` satisfies `kapitalverletzung`. The domain anchor
`entscheidung` is also generic and matches the ordinary stem `entscheid`. The
combination is enough for the frozen rubric but carries no legal relation to the
question. This is a defect of the frozen anchor profile/tolerance, not of the
verbatim extraction loop; it cannot be repaired post-hoc without changing the
frozen bytes, which this team may not do.

The two exact `defaut` rows show that exact matching alone is also insufficient:
a procedural passage can contain the exact anchor and still not be counter
evidence about the maintenance defect. A semantic/entailment gate (or a better
candidate/retrieval set) is required before any product use.

## 7. Integration contract (summary)

Full machine-readable contract:
`reports/frontier/frontier-counter-evidence-span-selection/INTEGRATION_CONTRACT.json`.

- **Module:** `frontier/frontier-counter-evidence-span-selection/span_select.py`
- **Entry point:**
  `apply_span_selection(bundle, rules, profile, qid=None, min_chars=40, max_chars=700, max_units=4)`
- **Placement:** after
  `product.query.counter_emission_repair.apply_counter_emission_repair` and
  before `product.query.counter_anchor.apply_anchor_labels`.
- **Population:** rows with
  `counter_proposal_source == "heuristic_proposal_promotion_v1"` and
  `counter_status` in the frozen scored statuses.
- **On emit:** set `counter_evidence` to the verified quote,
  `counter_evidence_verified=true`,
  `counter_evidence_source="retrieved_full_text"`, and record
  `counter_evidence_span` (decision id, quote, offsets, marker, anchors,
  `full_text_sha256`). Leave `counter_status` unchanged.
- **On abstain:** clear `counter_evidence`, set
  `counter_evidence_verified=false`, `counter_evidence_span=null`, keep
  `counter_status` at the proposed scored status.
- **Never touched by the component:** `counter_status`, the denominator,
  `packet_admitted`, `machine_gate_ready`, `human_gate_ready`, serve
  recommendations, the visible counter ring, the rubric, or any threshold.
- **Product decision:** the contract recommends **decline as-is**. A product lane
  may use the selector only as a shadow diagnostic behind a flag, never as a
  user-visible evidence source, until a successor exact-token/semantic gate is
  measured and accepted.

## 8. Claim ceiling

This report does **not** claim that any decision is supporting, contrary or
limiting. It does not claim jurist usefulness, serve readiness, reliability,
reproduction of the external 0/14 result, or that the map-versus-ranked-list
question is non-vacuous. It does not move a frozen absolute bar, threshold,
verdict class, rubric byte or bar; it adds no retrieval and no model call.
`packet_admitted`, `machine_gate_ready` and `human_gate_ready` remain
product-owned and false unless independently earned. The seven emitted spans are
a measurement of what the frozen scorer accepts, not a legal conclusion; the
semantic audit shows they should not be published as counter-authority.

## 9. Negative results preserved

- **4/7 spans are prefix artifacts** (`unter` -> `untergang`,
  `kapital` -> `kapitalverletzung`). These are the clearest negative result and
  the reason for the decline recommendation.
- **3/7 are exact or morphological but off-point** (termination validity,
  appeal standing, arbitration clause). Exact matching is not sufficient.
- **it emits 0/4.** The selector abstains on all four Italian rows; the frozen
  scorer records `evidence_absent:4`.
- **The served packet is unchanged** because `n_promoted=0`; the component is
  scoped to repair-promoted rows and does not address the 65 already-issued
  labels.
- **No model was called and no network was used.** This is a deterministic
  string/offset result, not a semantic model result.

## 10. Reproduction

From the repository root, with the accepted product mounted at
`/tmp/lex_accepted/core/product`:

```bash
python3 frontier/frontier-counter-evidence-span-selection/run_measurement.py --run-label primary
python3 frontier/frontier-counter-evidence-span-selection/semantic_audit.py
python3 -m unittest discover -s tests/frontier/frontier-counter-evidence-span-selection -v
```

The measurement overwrites only
`results/frontier/frontier-counter-evidence-span-selection/` and is
byte-identical across two runs on identical inputs apart from the constant
`run_label`. The semantic audit is post-hoc and writes `SEMANTIC_AUDIT.json`
only; it never edits `MEASUREMENT.json`, `BASELINE.json`, `CANDIDATE.json`,
`CONTROLS.json` or `DETERMINISM.json`.

## 11. Stop / successor recommendation

Mechanical outcome A is reached, so this charter version stops here:
`continue_recommended=false`, `cycle_status=COMPLETE_OUTCOME_A_MECHANICAL_ONLY`.
No same-charter cycle is justified: the protocol is frozen, post-hoc tuning
would invalidate the measurement, and the semantic defect is outside the frozen
payload.

**Product recommendation:** `DO_NOT_ADOPT_AS_IS`.

**Successor question (for the director, not this charter):** can an exact-token
semantic gate (no prefix tolerance on short generic tokens, plus an
off-topic/entailment check) turn the same 20-row population into spans that a
human reviewer would accept as counter-authority? If not, the defect is in the
candidate/retrieval set, and retrieval-side work is the correct next funding
target.

## 12. Artifact hashes

| artifact | sha256 |
|---|---|
| `PROTOCOL.json` | `b5d14121e86ea0b39c181aacef1c30d4a2788a4751af4cfa00c33189c0afb7ea` |
| `BASELINE.json` | `8d8664dc6d1e58af1abcf43deda6f69542cec2685e45628a9d2ea193bd03c965` |
| `CANDIDATE.json` | `05d270af97ddf5fafb3cab1ac4d25a0e9ba881182390a3bbbb643485b39d76d3` |
| `CONTROLS.json` | `811c2fb8d9459d62e361f32e68aeae593a07eac9e92ceb4b0529b93464e9f84b` |
| `DETERMINISM.json` | `65aa0b17c9e92d956c447cfd57c4589bc1919988fed58abb55e684db209dc780` |
| `MEASUREMENT.json` | `e60a5af60a513b9ee613b6ec611cbefd696b26aa36617e5655979f4907bc9194` |
| `SERVED_PACKET_SECONDARY.json` | `fa1cf1258f4b8bc4d66f43ddd4ce21f69b91c41967650be0b12d88b30a80e922` |
| `SEMANTIC_AUDIT.json` | `9b543b91629aa86146f85cb7b147ce7a92830bf037143c60b7a2025941402601` |
| `span_select.py` | `a8625ff649075749487725c9218e3f0c12c95e0663e18dff855de456605b2988` |
| `scorer_bridge.py` | `dbfa2a886a92b008b8f36b9dea30fed7cacd55ff094b8ad7cbcec8910cb6a5d0` |
| `run_measurement.py` | `82eca3c826a861969f65f65e970a65911733a409c077b8f532358c1f6b3ef01c` |
| `semantic_audit.py` | `d40403142b60f89a23da07e7e1649a8d54e69b05d4a06f67aa10af0fd1c24694` |
| `test_span_select.py` | `ebdd646d31ae354f195dfb02cbe71de13286b83067f7a5f73dc837ab883f1b83` |

---

## Appendix R1 - Operational-resume provenance correction (run `39990225759`)

*This appendix is additive. Sections 0-12 above are left byte-for-byte as the
producer run `39986101767` wrote them. Machine-readable record:
`results/frontier/frontier-counter-evidence-span-selection/PROVENANCE_RESUME.json`.*

### R1.1 What failed operationally

The producer run `39986101767` completed its measurement and published commit
`e9ee955e8f5e2679572257731130c70febcb4c68` on
`origin/cycle/frontier/frontier-counter-evidence-span-selection/39986101767/team`.
The measurement itself is sound; the **provenance citation is not**.

Sections 0 and 1 above, and
`state/frontier/frontier-counter-evidence-span-selection.json` `run_history[0].note`,
cite commit **`dad93c36`** as the pre-measurement protocol freeze commit. That
object does not exist in the repository:

```
$ git cat-file -t dad93c36
fatal: Not a valid object name dad93c36
```

The branch was published as a single squashed commit, which orphans the
producer's intermediate local commit hash. An independent auditor verifying
acceptance criterion (1) ("FREEZE FIRST ... commit a machine-readable protocol
record ... no field of it may be edited after execution") by resolving the cited
commit would fail to locate the freeze and could return `AUDIT_BLOCKED` on a
broken provenance chain - even though the freeze itself is intact. That is the
defect this appendix repairs.

### R1.2 The freeze witness, restated content-addressed

The freeze was real and is provable without any commit hash:

| witness | value |
|---|---|
| protocol path | `results/frontier/frontier-counter-evidence-span-selection/PROTOCOL.json` |
| `sha256(PROTOCOL.json)` | `b5d14121e86ea0b39c181aacef1c30d4a2788a4751af4cfa00c33189c0afb7ea` |
| `PROTOCOL.sha256` | matches a fresh `sha256sum` of `PROTOCOL.json` |
| `PROTOCOL.json.status` | `FROZEN_BEFORE_MEASUREMENT` |
| `PROTOCOL.json.frozen_at` | `2026-10-23T16:29:36Z`, before every result artifact |
| success rule | lives **inside** the frozen payload (`success_rule` block) |
| claim ceiling | lives **inside** the frozen payload (`success_rule.claim_ceiling`) |
| chain of custody | all seven result artifacts embed `protocol_sha256 = b5d14121...` |

No field of `PROTOCOL.json` and no claim-bearing result artifact was edited by
this resume. The unresolvable citation is recorded as a defect, not deleted.

### R1.3 Independent re-execution (resume run `39990225759`)

Two full re-executions were run with `--out-dir` redirected **outside** the
repository, so no committed artifact was overwritten:

| artifact | re-exec 1 (`--run-label primary`) | re-exec 2 (`--run-label verify`, independent session) |
|---|---|---|
| `BASELINE.json` | byte-identical | identical modulo declared `run_label` |
| `CANDIDATE.json` | byte-identical | identical modulo declared `run_label` |
| `CONTROLS.json` | byte-identical | identical modulo declared `run_label` |
| `DETERMINISM.json` | byte-identical | identical modulo declared `run_label` |
| `SERVED_PACKET_SECONDARY.json` | byte-identical | identical modulo declared `run_label` |
| `MEASUREMENT.json` | identical modulo the `--out-dir` path strings | identical modulo `run_label` and `--out-dir` |

Re-hash checks: `RULES_LABEL.json` = `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`
(matches the charter), `PROTOCOL.json` = `b5d14121...` (matches
`PROTOCOL.sha256`), product mount HEAD = `f4cd7d7c...` (matches the protocol).

### R1.4 Additional adversarial probes (this resume)

| probe | observed |
|---|---|
| all 7 emitted quotes satisfy `full_text[char_start:char_end] == quote` in the cited decision's own `full_text` | 7/7 pass, 0 failures |
| recorded `full_text_sha256` matches a fresh hash of that `full_text` | 7/7 pass |
| 1-character mutation of each emitted quote | 7/7 rejected |
| end-truncated quote with original offsets | 7/7 rejected |
| donor quote taken from a **different** decision in the same bundle | 7/7 rejected |
| quote re-submitted with offsets shifted by +1 | 7/7 rejected |
| empty quote | 7/7 rejected |
| `apply_span_selection` run twice on the same repaired bundle | identical |
| empty `full_text` | abstains with `no_retrieved_text` |
| `counter_status` multiset before vs after span selection | identical (`contrary_or_exception:3`, `candidate-limiting:3`, `candidate-contrary:2`); `counter_status` is never a changed field |
| only fields written by the component | `counter_evidence`, `counter_evidence_source`, `counter_span_selection`, `counter_evidence_verified`, `counter_evidence_span` |
| served packet `38839347028` `n_promoted` | 0 across all three bundles, reproducing the published scope limitation |

### R1.5 Preserved negative observation: two frozen abstain gates are dead

`rules.anchor_profile(qid).expected_languages == ['de','fr','it']` for all three
questions and `foreign_legal_area_fields == []` for all three, and
`span_select._lang_of` coerces any language code outside `{de,fr,it}` to `'de'`,
which is itself in `expected_languages`. The `language_not_expected` and
`foreign_legal_area` abstain reason codes therefore **cannot fire** under the
frozen profiles. No row in the measured population was affected and **no number
changes**; this is recorded because a successor charter reusing the component
must either wire real per-question profiles or drop the dead gates rather than
report them as safety properties.

### R1.6 Outcome unchanged

The resume changes **no** verdict, count, label or recommendation:

- mechanical: `A_COMPONENT_EVIDENCE_RECOVERED` (candidate 7 emitted vs baseline 0, controls 0/0, denominator 20 unchanged, support among emitted 1.0);
- semantic: 0/7 clear legal counter-authorities, 4/7 string coincidences;
- team verdict: `COMPLETE_OUTCOME_A_MECHANICAL_ONLY`;
- product recommendation: `DO_NOT_ADOPT_AS_IS`;
- `continue_recommended = false` - a further cycle under the **same** charter would require post-hoc tuning of a frozen protocol, which the charter forbids.

### R1.7 One factual correction in the integration contract

`INTEGRATION_CONTRACT.json` `decline_path.what_is_retained` said "16 tests"; the
suite that produced the recorded result is **19** tests. Corrected to 19 in the
same resume commit. No adoption condition, forbidden constant, machine check,
field name or recommendation was changed.

### R1.8 Additive resume test suite

`tests/frontier/frontier-counter-evidence-span-selection/test_resume_verification.py`
is a **new** module; the producer's `test_span_select.py` is left byte-identical
at `ebdd646d31ae354f195dfb02cbe71de13286b83067f7a5f73dc837ab883f1b83` (still
the `19 passed` recorded in section 0). The suite total is now **35 tests, all
passing**. The new module machine-checks, without any network or mount:

- `sha256(PROTOCOL.json) == PROTOCOL.sha256` and `status == FROZEN_BEFORE_MEASUREMENT`;
- `success_rule` (including `claim_ceiling`) and `abstain_condition` and
  `span_rule` are inside the frozen payload;
- every result artifact still embeds `protocol_sha256 = b5d14121...`;
- all eight producer result artifacts are still **byte-identical** to the hashes
  recorded in section 12 - the resume may append records but may never rewrite
  results;
- the dangling `dad93c36` citation is still present in this report (preserved,
  not erased) and the corrected content-addressed witness is in
  `PROVENANCE_RESUME.json`;
- the integration contract still forbids exactly the ten product-owned fields,
  still recommends `DECLINE_AS_IS`, and still pins the denominator and verbatim
  machine checks.

### R1.9 Audit-driven correction: freeze provenance claims retracted (audit CYCLE_39994019404)

**INDEPENDENT AUDIT FINDING (D2):** The statements in Appendix R1.1 above and in
`PROVENANCE_RESUME.json` `operational_failure` that "`git cat-file -t dad93c36`
returns 'fatal: Not a valid object name dad93c36'" and "The branch was published
as a single squashed commit ... which orphans the intermediate local commit hash"
are **FALSE**.

An independent fresh clone of the exact named branch
`origin/cycle/frontier/frontier-counter-evidence-span-selection/39986101767/team`
(HEAD `e9ee955e8f5e2679572257731130c70febcb4c68`) **RESOLVES**:

```
$ git cat-file -t dad93c36
commit
$ git log --oneline -2
e9ee955 measure: counter-evidence span selection (mechanical A, semantic decline)
dad93c3 freeze: counter-evidence span-selection protocol before measurement
$ git merge-base --is-ancestor dad93c36 HEAD   # exit 0 -> YES
```

`dad93c364e996fb430696a510e8de9d55f369bb9` is the **DIRECT PARENT** of the
published measure commit `e9ee955`. The history was **NEVER SQUASHED**. The
original "dangling commit / squashed history" diagnosis was a fabrication based
on a shallow or partial view at resume time.

**RETRACTION:** The following assertions are retracted:
- "`git cat-file -t dad93c36` returns fatal: Not a valid object name" — FALSE
- "The branch was published as a single squashed commit" — FALSE
- "audit-blocking provenance defect" severity — FALSE (the freeze is intact and content-addressed)

**PRESERVATION:** The original sentences in R1.1, R1.2, R1.3, R1.6, R1.7,
R1.8 and the `operational_failure` block in `PROVENANCE_RESUME.json` are
**LEFT VERBATIM** as historical record. This correction is ADDITIVE only.
The freeze witness remains: `PROTOCOL.json` status=FROZEN_BEFORE_MEASUREMENT,
sha256=b5d14121..., all artifacts embed the digest. Criterion (1) FREEZE FIRST
was already PASSED by both the commit-addressed witness (dad93c36 as direct
parent of e9ee955) and the content-addressed witness (PROTOCOL.sha256 match).
No number, label, protocol byte, or verdict changes.
