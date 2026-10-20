# Frontier frontier-counter-label-emission — Measurement Record (charter v1, run 39422328377)

**Promotion: A_EMISSION_RECOVERED.** The adversarial/counter stage on the shipped
packet-of-record v3 was emitting zero counter labels because the LLM adversarial
reviewer — the *sole writer* of `counter_status` by design — aborted or failed its
verified-evidence precision gate, while the adversarial retrieval channel itself
ran fine and already held gate-passed heuristic evidence sentences on 20 of 24
adversarial rows. A minimal, offline, deterministic repair promotes those
already-verified heuristic proposals into scored statuses so the accepted
classifier can confirm-or-abstain on them, recovering `n_scored>0` on all three
bundles (8 / 8 / 4, up from 0 / 0 / 0) with byte-identical determinism across
3 runs and a passing seeded + negative non-vacuity control on every bundle.

## 1. Attribution (byte-level, per bundle)

Primary cause on **all three v3 bundles**: `e_EMISSION_WRITER_ABORT`.

| Bundle | adversarial rows | heuristic-positive rows | LLM reviewer n_findings | scored rows BEFORE | primary cause |
|---|---|---|---|---|---|
| de-kapitalverletzung | 8 | 8 | 0 (all providers failed / returned `[]`) | 0 | e_EMISSION_WRITER_ABORT |
| fr-bail-entretien | 8 | 8 | 0 (all four providers failed) | 0 | e_EMISSION_WRITER_ABORT |
| it-responsabilita-medica | 8 | 4 | 2 (written to rows but `counter_evidence=""`, precision gate failed) | 0 | e_EMISSION_WRITER_ABORT |

The four charter cause classes are ruled out by the bytes:

* **(a) POPULATION** — ruled out. The adversarial channel did *not* degrade to
  exception-only: each bundle carries 8 adversarial rows across 3–4 intents
  (exception / minority / contrary / older_line), and 20 of 24 rows carry a
  non-null `adversarial_retrieval_signal.heuristic_status` with a non-empty
  verbatim evidence sentence (72–400 chars). `mode=live`, `failures=[]`,
  `network_calls>0` in every bundle's `provenance.adversarial_retrieval`.
* **(b) PLANNER/PROBE** — ruled out. `attempted=true`, `n_candidates` 15–20,
  `probes` and `channels` populated, `request_summary` logged in all three.
* **(c) HYDRATION** — secondary only. 12 of 15–20 candidates were hydrated per
  bundle; the 4 heuristic-negative rows on it-responsabilita-medica are hydrated
  with full text but the product's own topical/marker gate did not fire on them.
  Hydration is not the primary cause on any bundle.
* **(d) GATE** — ruled out as primary. The topical/marker gate *passed* on all
  20 heuristic-positive rows; it is the LLM reviewer stage downstream of the
  gate that failed.

The actual mechanism, from the shipped code:

1. `product/query/adversarial_retrieval.py` (v2) computes the heuristic proposal
   via `classify_against_intent` and stores it in `adversarial_retrieval_signal`,
   but **deliberately does not write** `counter_status` / `counter_evidence`
   (lines 754–766: *"the independent LLM reviewer runs later ... and is the sole
   writer of counter_status"*). It hard-codes `counter_status="none"`.
2. `product/query/pipeline.py` then calls `run_adversarial_audit` (the LLM
   reviewer). On the v3 run this returned **0 findings** on de and fr (provider
   failures: `space-bunny` rc=1, `mimo` timeout 180s, `longcat` timeout 180s,
   `muse-spark` rc=1) and **2 findings** on it that failed the
   `verified_evidence + confidence>=0.5 + uncertainty<0.9` precision gate
   (`counter_evidence=""`, `counter_evidence_verified=False`), so
   `apply_to_product_bundle` forced `counter_status="none"`.
3. `product/query/counter_anchor.py` (the accepted seam) only scores rows whose
   `counter_status ∈ SCORED_STATUSES`; with zero such rows it reports
   `n_scored=0 / n_emitted=0 / n_abstained=0`.

So the accepted classifier never saw a proposal. Its `n_abstained=0` proves it
was never handed one; the abstain-and-disclose config is **not** the cause and
was never re-tuned.

## 2. The minimal in-budget repair

`heuristic_proposal_promotion_v1` (`emission.py`): for each decision row whose
`counter_status` is not already scored **and** whose
`adversarial_retrieval_signal.heuristic_status` is non-null with ≥40 chars of
evidence, copy the heuristic proposal into the scored-status fields
(`counter_status`, `counter_evidence` truncated to 400 chars,
`counter_proposal_source='heuristic_proposal_promotion_v1'`,
`counter_uncertainty=0.5`). Pure, offline, O(rows), no network, no model call.
Never touches geometry, ranks, clusters, existing scored labels, the accepted
classifier, or either frozen rubric.

The accepted classifier is the safety net: any proposal whose evidence fails the
frozen emission gate becomes a **counted abstention**
(`counter_status='abstained_unevidenced'`), never a shipped label.

## 3. Emission measurement (before / after, all three bundles)

| Bundle | n_proposed BEFORE | n_scored BEFORE | n_scored AFTER | n_emitted AFTER | n_abstained AFTER | support-among-issued | yield (of pop.) | absolute bar (as written) |
|---|---|---|---|---|---|---|---|---|
| de-kapitalverletzung | 0 | 0 | **8** | 0 | 8 | 0.0 | 0.0 | LABEL_UNSOUND (n_scored 8 ≥ 7, support 0 < 1.0) |
| fr-bail-entretien | 0 | 0 | **8** | 0 | 8 | 0.0 | 0.0 | LABEL_UNSOUND (n_scored 8 ≥ 7, support 0 < 1.0) |
| it-responsabilita-medica | 0 | 0 | **4** | 0 | 4 | 0.0 | 0.0 | INSUFFICIENT_POPULATION (n_scored 4 < 7) |

Abstention reasons (honest fail-closed under the frozen rubric):

* de: `pivot_absent` 5, `no_intent_marker` 2, `no_domain_anchor` 1
* fr: `pivot_absent` 6, `no_intent_marker` 2
* it: `pivot_absent` 4

The frozen absolute bar **1.0 remains unmet as written** and is never
re-derived. `NOT_APPLICABLE` and `NOT_MEASURED` are never counted as a pass
(tested). The value of the measurement is the recovered, evidenced,
deterministic **issuance** itself (`n_scored>0` on all three bundles), with
support-among-issued, the abstention count and the yield published together.

## 4. Determinism

3 identical offline runs per bundle produce byte-identical proposal and label
sets on all three bundles (`DETERMINISM.json`, `identical=true`, `n_runs=3`).
No bounded-instability disclosure is required.

## 5. Non-vacuity

Seeded control: inject one eligible counter-evidence sentence (frozen
counter-intent marker + topical term, not boilerplate) into one candidate row →
the emission flips on every bundle (`n_scored` +1 on all three; `n_emitted` +1
on de-kapitalverletzung). Negative control: blank the topical vocabulary → the
emission is suppressed relative to the seeded control. Both controls pass on
all three bundles. The harness measures the pipeline, not a constant.

## 6. Frozen-artifact integrity

* Packet-of-record v3 hashes re-verified before and after every claim-bearing
  execution (`input_hash_verification.ok=true`).
* Accepted classifier (accept `d236f599`, 9 files) re-hashed byte-identical
  before and after (`classifier_config_byte_identical_after=true`).
* Frozen rubric `RULES_LABEL.json` sha256
  `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`
  re-verified byte-identical.
* `RULES.json` frozen and committed at `d20a3edd` (2026-10-20T12:39:28Z from
  git commit time) **before** any claim-bearing measurement.
* 33 deterministic offline tests pass (`tests/frontier/frontier-counter-label-emission/`).

## 7. What Product consumes

See `INTEGRATION_CONTRACT.json`. Product integrates the drop-in module at the
`enrich_query_bundle` seam between `adversarial_retrieval_pass` and
`apply_anchor_labels`, appends the attribution + measurement record to its
append-only intake, and re-runs packet admission. Nothing here asserts any case
IS contrary/limiting beyond the rubric's own sentence evidence. No serve
recommendation is produced; the accepted BOUNDED-NEGATIVE verdict of record
stands untouched; `human_gate_ready` is never touched.

## 8. Provenance

* Team: `frontier-counter-label-emission`, charter v1, GitHub run 39422328377
* Branch: `lab/frontier/frontier-counter-label-emission`
* Frozen rules commit: `d20a3edd`
* Accepted classifier: `d236f5990` (never rebuilt, never re-tuned)
* Frozen rubric: `4457e971…` (never regenerated, never edited)
* Zero writes to `product/`, `evaluation/`, `results/product/`,
  `results/evaluation/`, `state/product.json`, `state/evaluation.json`,
  `.github/**`, or any frozen artifact.
