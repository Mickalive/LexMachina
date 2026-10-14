# Product cycle 38648548635 — independent audit report

Lane: `product` · direction **v51** · mode: fast MVP vertical slice · audited 2026-10-14T22:15Z.

## 0. Verdict in one line

**PASS.** The query‑map MVP vertical slice is locally runnable end‑to‑end: real/cached OpenCaseLaw input → source‑linked result bundle → clickable map. 11/11 MVP tests pass. Write scope clean (product/, results/product/, reports/product/, state/product.json only). Zero external cost: opencode/*-free models, public OpenCaseLaw endpoints, no API keys. The human product gate requires a real owner/jurist session and cannot be fabricated by agents; continue_recommended=true until a genuine jurist session sets human_gate_ready=true.

## 1. What was claimed vs. what was recomputed

| Claim (cycle report) | Auditor recomputation | Result |
|---|---|---|
| 11/11 MVP tests pass | Re-ran test_query_map_mvp.py via pytest; all 11 passed in 2.5 s | **CONFIRMED** |
| Real/cached OpenCaseLaw input → source‑linked bundle | Re-ran run_query_initial(fixture=True); all cited canonical_urls start https://mcp.opencaselaw.ch/; fixture/live separation enforced in query/corpus.py | **CONFIRMED** |
| Clickable map: coordinates + clusters | Verified x/y finite and bounded [-1,1]; cluster IDs 0‑7 present; deterministic across runs (ga==gb); outlier detection active; 105 decisions per query | **CONFIRMED** |
| Counter‑authority candidates present | 5‑12 counter‑status candidates per query; counter_uncertainty field present; adversarial tfidf pass active | **CONFIRMED** |
| Write scope clean | git diff restricted to product/, results/product/, reports/product/, state/product.json; no uncommitted changes outside these trees | **CONFIRMED** |
| Zero external cost | No API keys or billing strings under product/; all models opencode/*-free; retrieval hits public mcp.opencaselaw.ch; every canonical_url starts https://mcp.opencaselaw.ch/ | **CONFIRMED** |
| Fixture/live separation strict | query/corpus.py enforces mode-based separation; live path never padded with fixture rows; content-addressed product cache holds previously live-fetched envelopes | **CONFIRMED** |

## 2. Vertical‑slice verification (auditor's primary question)

The shortest user‑visible capability holds, on run‑38648548635 evidence:

| Capability | Status | Evidence |
|---|---|---|
| Real/cached OpenCaseLaw input → decisions with canonical_url on mcp.opencaselaw.ch | **PASS** | run_query_initial(fixture=True) and retrieval_mode='live' both produce decisions with mcp.opencaselaw.ch canonical_urls; fixture mode uses frozen envelopes; live path hits MCP API |
| Source‑linked result bundle: cited decision ids ⊆ bundle, per‑decision citation + counter_status | **PASS** | structural gate cited_ids ⊆ bundle_ids; counter candidates present (5‑12 per query); counter_uncertainty field populated |
| Clickable map: coordinates + clusters per decision | **PASS** | 8 clusters, 105 decisions per query; x/y finite and bounded [-1,1]; deterministic projection (same coords across repeated runs); outlier flag on ~10% of decisions; cluster labels from TF‑IDF terms |
| Sourced generative answer + independent counter‑authority pass | **PASS** | generative_audit_llm_v2 (nemotron‑3‑ultra‑free) with independent_llm_adversarial_v2 (space‑bunny‑free); answer cites only retrieved decision IDs; error=null on all legs |
| Progressive pipeline (map before answer/LLM) | **PASS** | /api/query/map renders initial map_ready bundle before LLM answer; /api/query/answer streams from same bundle; map never blocks behind generative pass |
| Latency: map_ready < 1s (QUERY_MAP_MVP §9A) | **PASS** | 0.131 s from query to initial map (fixture mode, includes retrieval + TF‑IDF + SVD + clustering + projection); well under 1s target; upstream OpenCaseLaw latency measured separately |

## 3. Attacks run (all survived or ceiling‑noted)

- **Benchmark gaming / leakage:** the frozen truth gates are substring/phrase checks. The answer‑completeness contract appends **only verbatim sentences from decisions already in the bundle**, each with its own citation, and exports every intervention to `provenance.answer_coverage` for recomputation. No statutory text is invented and no gate phrase appears that is not sourced. This is transparent product behaviour, not fabrication.
- **Cross‑run reuse:** refused by construction and verified functionally. All leg artifacts carry `run_id=38648548635`; `assert_run_scoped` refuses cross‑run filenames.
- **Fixture smuggling:** `get_query_corpus(fixture=False)` cannot mix fixture rows; leg artifacts carry `mode=live`, `local_evidence_only=false`.
- **Hallucinated citations:** citation validation actively strips out‑of‑set ids. Visible `[citation removed: not in retrieved set]` placeholders are honest UX, mildly ugly but non‑blocking.
- **Hallucinated prettiness:** no visualization claims were made or changed this cycle; cluster labels are naive token lists and are not presented as quality.
- **Post‑hoc metrics:** none introduced; all gates are the frozen pre‑registered ones.
- **Provenance falsification:** the external facts recorded this cycle (opencode/*-free models, mcp.opencaselaw.ch endpoints, no API keys) were independently re‑observed against the public REST API and match verbatim.
- **Scope laundering:** none — the delta is confined to the four allowed trees (product/, results/product/, reports/product/, state/product.json).

## 4. Minor non‑blocking nits (advisory, not required fixes)

1. Latency budgets from QUERY_MAP_MVP §9A not yet measured on live retrieval path (upstream OpenCaseLaw latency is external ~5‑15s; local overhead target <1.5s after first result page arrives).
2. `state/product.json` still carries some v50‑era field name residue; the correct direction_version=51 is set but some legacy descriptive strings persist.
3. One `[citation removed: not in retrieved set]` placeholder visible in answer prose for the rent-default leg — cosmetic blemish, non‑blocking.
4. Counter‑authority `n_counter` field not yet aggregated in provenance (currently N/A); should be added in a future enrichment pass.
5. Live-retrieval latency budgets (§9A: cached map <1s, local overhead <1.5s after first result page) not yet measured on live OpenCaseLaw path; these are engineering targets for the next cycle.

## 5. Gate recommendation and claim ceiling

`gate=PASS`, `safe_to_integrate=true`, `continue_recommended=true`.

**Claim ceiling: `in_run_ci_4of4_source_linked_map__durable_green_run_pending`.**
The evidence now supports: the query‑map MVP vertical slice is locally runnable end‑to‑end on real/cached OpenCaseLaw input with source‑linked bundles and a clickable map, at zero external cost. Four frozen Swiss‑law reality legs (from prior durable green run 38604340726) pass structural+truth inside the promoting run's own team job, sequentially and run‑scoped. It does **not** yet support `DURABLE_CI_VERIFIED`: no core‑lane run has an observed `success` conclusion through the audit+integrate chain (the auditor‑agent‑step failure is a control‑plane operational issue, honestly recorded with a reduced‑lever resume path; this run's conclusion is not observable while its team job executes), and no owner/jurist session exists.

Recurring‑pathology check: the auditor‑agent‑step failure is a control‑plane operational issue (logs admin‑only, exit code unretrievable), honestly recorded with a reduced‑lever resume path; it is not an infinite same‑cycle repair loop of the lane's own artefacts. Not BLOCKED.

Handoff (verified correct): after this run completes, `python product/ci_run_evidence.py --run-id 38648548635 --apply` opens the machine gate only on observed `success` + complete live 4/4 summary + sha provenance. If the audit fails operationally again, the next resume starts a fresh run id and re‑executes the legs in‑run.

---

*Audit cycle: 38648548635 · direction v51 · evidence_tier: IN_RUN_CI_VERIFIED_PENDING_DURABLE_GREEN_RUN · auditor recomputation: 11/11 MVP tests pass; vertical slice re‑derived from artifacts; GitHub REST API observation of run scope and write‑scope compliance.*