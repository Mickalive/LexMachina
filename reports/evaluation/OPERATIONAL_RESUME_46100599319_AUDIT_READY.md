# Operational resume of producer run 46100599319 — orchestration diagnosis, deliverable verification, audit-ready snapshot

- **Lane:** evaluation · **Direction:** v68 (mounted control plane `main`)
- **Run under resume:** `46100599319` (`Core evaluation dirV68 repair0`, run_number 25657, conclusion `failure`)
- **This resume run:** `46106181686` (`workflow_dispatch`, `resume_from_run_id=46100599319`, team job)
- **Persisted producer snapshot:** `39784cc02d5eb06915cab32bfc5e2647631de74a` — `evaluation cycle 46100599319 repair 0` — identical on `HEAD`/`operational-resume` and `origin/cycle/core/evaluation/46100599319/team`
- **Mode:** FAST MVP operational resume — deterministic offline, no benchmark re-execution, no frozen edit
- **Claim ceiling:** operational record only. No new measurement, no product re-score, no frozen-bar/verdict change, no serve verdict, no claim promotion.
- Machine records: `results/evaluation/operational_resume_46106181686/diagnosis_46100599319.json`, `.../deliverable_verification_46100599319.json`, `.../audit_readiness_46106181686.json`, `.../AUDIT_INDEX_46106181686.json`.

---

## 1. Orchestration / validation failure — diagnosed

Source: pinned unauthenticated public GitHub REST envelopes `results/evaluation/operational_resume_46106181686/api/{run,jobs}_46100599319_api.json` (sha256 `a6407c8f…`, `13fc7173…`) and git ref/file inspection. Job logs return **HTTP 403 unauthenticated**, so any statement about the agent's internal exit reason is an inference and is labelled as such (factory-wide requirement on unreadable logs).

| Job | Conclusion | Detail |
|---|---|---|
| `team` | **success** | all 11 steps green, including `Run lane cycle`, `Validate active MVP producer state`, `Enforce lane write scope`, `Persist team snapshot` |
| `audit` | **failure** | single failing step `Independent audit`; `Enforce audit scope and read gate` and `Persist audit snapshot` skipped; 2763 s (~46 min) |
| `integrate` | skipped | gated on `needs.audit.result == 'success'` |
| `resilience` | success | recovered the failed chain and dispatched this resume |

**Established facts.** The producer job did not cross write scope and did not fail state validation; the snapshot was force-persisted. No audit branch exists (`git for-each-ref` returns only `/team` and `/team-attempt-1` at `39784cc0`), and neither `results/audit/evaluation/CYCLE_46100599319_GATE.json` nor `reports/audit/evaluation/CYCLE_46100599319.md` exists on any ref or in the worktree. Therefore run `46100599319` produced **no independent gate and no promotion**, and `lab/evaluation` did not advance.

**Classification: `AUDIT_AGENT_STEP_FAILURE_NOT_A_VERDICT`; cause `NOT_ESTABLISHED`.** The 46-minute step is consistent with the documented agent-death class (provider rotation/overload or work-quantum expiry — factory-wide requirement index 16 and the rc-78 class in index 6), but **that is a hedged inference, not an observed log line**. It is explicitly *not* a verdict, product defect, scope violation, frozen-bar result, serve verdict or human decision.

**Separate validation defect (concrete, repaired in §3).** Independently of the audit job death, the lane's own frozen `evaluation.state_integrity_gate` returned `AT_LEAST_ONE_CHECK_FAILED`, exit 1, 2 failures at the snapshot: `evidence_refs_n_matches@state/evaluation.json` (255 declared vs 267 actual) and `root_lane_parity@both` (`github_run` 46100599319 root vs 40261335674 lane). These are mechanical state-hygiene defects introduced by the producer's append, not measurement failures. This is the "validation failure" that had to be repaired to make the snapshot audit-ready.

## 2. Deliverable verification — `DELIVERABLE_VERIFIED`, 14/14 checks

Executed by `python3 -B evaluation/operational_resume_46106181686.py verify`; no benchmark, falsifier or probe was re-run. Full ledger: `.../deliverable_verification_46100599319.json`.

| Pin (state block → committed bytes) | sha256 | Result |
|---|---|---|
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json` | `9755b6ce2ef359481016ffd8c96a730c28b96956eec202433406bdc8df740d25` | match |
| `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json` | `6b77be8432c42c7c4d4179b8908f709ebf6334f5b3ab133ce64635e176ce595a` | match |
| `evaluation/fast_mvp_retrieval_recall_benchmark.py` | `fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283` | match |
| `results/evaluation/fast_mvp_retrieval_recall_benchmark/46100599319.json` | `f89a91289a783d3142cfdb8078d48aa613bc9de15a5292a86ca040462a622446` | match |

- All 12 files added by commit `39784cc0` resolve; **0 out-of-scope paths** (`results/audit/**`, `reports/audit/**`, `.github/**`, other lanes untouched).
- The 16-check claim recompute was **independently recomputed from result + state block**: all 16 true; the committed `46100599319_claim_recompute.json` also reports `all_pass=true`. Headline: verdict `PRODUCT_FALSIFIED_RECALL_LOSS`, exit 1, `network_calls=0`, 24 cells / 10 discriminating / 14 not-measured, 17→15 hits over denominator 18, baseline 5→3, counter 12→12, fr 4→3, de 12→11, it 1→1, `failed_controls=[]`, 9/10 controls with C7b REPORTED_ONLY.
- Freeze-first ordering holds: subject freeze `2026-11-28T03:08:06Z` < result `2026-11-28T03:09:03Z`; rehash-before/after pins unchanged. The report's headline numbers agree with the artifact.
- Reused suites (re-hashed, not edited): multilingual/provenance SHIM_PASS 2/2, recall instrument SHIM_PASS 7/7, CA suites SHIM_PASS 14/14 + 1 unsupported (NOT-RUN, never counted as passed), lane suite 88/89 with the standing pytest-absent SKIP.
- One **pre-existing, annotated** nested ref (`github_run_advance_40246705199.required_fixes_source → results/audit/evaluation/CYCLE_40246705199_GATE.json`) does not resolve in-tree. It is not added by this snapshot; it is disclosed through the guard's own `known_unresolvable` mechanism. No audit-namespace file is fabricated to make it resolve.

## 3. State repair — two disclosed, append-only changes

`evaluation/operational_resume_46106181686_state_repair.py` applied exactly:

1. `evidence_refs_n` corrected to `len(evidence_refs)` in **both** `state/evaluation.json` and `evaluation/state/evaluation.json`; every listed ref is an existing file. Root was 255 declared vs 267 actual; lane was 162/162. After appending this resume's 18 in-scope artifact refs, both are 285/285 (root) and 180/180 (lane).
2. `github_run` and `proposed_run_id` synchronized across both state files to `46106181686` (root had 46100599319, lane 40261335674).

It also appends the new `operational_resume_46106181686` block (claim-bearing, `audit_status=PENDING_INDEPENDENT_AUDIT`, `pending_independent_audit=true`, `accepted_as_evidence=false`), preserves the superseded `next_recommendation` as `prior_next_recommendation_46100599319`, and discloses the non-measurement GitHub API calls. **No historical claim-bearing key, frozen bar, rubric, threshold, verdict contract, packet or gate was edited; `accepted_run_id` stays `40258497460`; all posture flags stay false.**

## 4. Audit-readiness verification

`python3 -B evaluation/operational_resume_46106181686.py finalize` re-runs the frozen state-integrity gate after the state write (plus a post-write re-check), the nested-ref guard and the write-scope classifier. Result: **11/11 checks pass** before and after the state write (`ALL_CHECKS_PASS`, exit 0), scope `SCOPE_CLEAN` with **0 bad paths**, and `audit_readiness=AUDIT_READY_PENDING_INDEPENDENT_AUDIT` with `all_pass=true`. The nested guard resolves all top-level evidence refs; exactly one **annotated pre-existing historical** nested ref remains (`github_run_advance_40246705199.required_fixes_source`), preserved verbatim and disclosed in `pre_existing_nested_unresolved`, never fabricated or deleted.

The hash-indexed `results/evaluation/operational_resume_46106181686/AUDIT_INDEX_46106181686.json` lists every artifact with byte sha256, claim→artifact mapping, exact commands, and an auditor shortcut; `.../summary_46106181686.json` is the one-page companion. A final `state_integrity_gate` run after the index appended its refs again returned `ALL_CHECKS_PASS`. The producer lane writes **only** `evaluation/**`, `results/evaluation/**`, `reports/evaluation/**` and `state/evaluation.json`; the independent auditor alone may write `results/audit/evaluation/CYCLE_46106181686_GATE.json` (uppercase `_GATE.json`) and `reports/audit/evaluation/CYCLE_46106181686.md`.

## 5. v68 ordered-work disposition (carried forward, not re-derived)

1. **Report-only correction of record** — discharged at `40144816305`; not re-run.
2. **Conditional re-measure** — `NOT_YET_DISCRIMINATING`, not executed: the frozen 15-member family remains 14/15; no post-repair protocol, `d2_path_scope_probe`, packet-of-record scoring or synthetic stand-in. The standing falsification was not re-run.
3. **Standing falsification record** — kept: `PRODUCT_FALSIFIED` on packet-of-record `39319405429` with the identical 4-gate set; the counter-authority-yield negative for 2/4 frozen questions remains a measurement of this lane's own producer's lexical marker rule, never Core Product's counter channel.
4. **CYCLE_39965089504 three non-blocking fixes** — reported only where those counts are quoted; not quoted in this cycle's headline.
5. **No zero-delta re-derivation** — honoured: this resume re-ran no frozen benchmark, D2 profile or bypass diagnosis and no universal-174k work.

The verified open product defect handed to Core Product remains the reranking RECALL@K loss: `baseline:business-judgment-rule:de` (`bger_4A_219_2015`, `bger_4A_603_2014`) and `counter:petty-theft-dismissal:fr` (`ge_gerichte_CAPH_107_2004`), unchanged across heads `e53662be`, `5fb312e4` and `7be4480e`.

## 6. Compliance / posture

- ✅ no universal-174k benchmark; ✅ no benchmark/falsifier re-execution; ✅ no frozen edit or posture flip
- ✅ no audit-namespace write by the producer; ✅ no history deleted; negative results preserved
- ✅ non-measurement network disclosed (GitHub REST API only); zero OpenCaseLaw/retrieval/model/paid-API calls
- ✅ `packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`, `ready_for_owner_session=false`, `owner_decision_required=false`; both DO-NOT-SERVE orders stand
- ✅ `continue_recommended=false`; no human decision raised; no blockage claimed

**next_recommendation.** Audit-ready pending independent audit. No further same-question cycle has a discriminating purpose until Core Product changes the retrieval/reranking code or regenerates the 15th frozen-family member. The successor question remains the Factory Director's under `RESEARCH_PROTOCOL.md` §20.
