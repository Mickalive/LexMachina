# Operational discrimination gate — evaluation run 44855886880 (direction v68)

**Cycle kind:** OPERATIONAL_VERIFICATION, not evidence. Re-dispatch of an already-exhausted same-question lane.
**Surface read:** committed artifacts on `lab/evaluation` HEAD `ea98384e` + the workflow-mounted accepted product worktree `/tmp/lex_accepted/product` at HEAD `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`. Acceptance currency was read from **both halves of factory-wide requirement 4** (audit gate file with `gate=PASS, safe_to_integrate=true` **and** an `accept <lane> cycle <run>` commit), never from the mount or `results/accepted-state` alone (requirement 39).

## 1. Hypothesis, baseline, metric, success rule — frozen before execution

- Frozen hypothesis: `evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_HYPOTHESIS_V1.json`, sha256 `e99ea54bbfb80b78269dcd66af4d5e5fcc6fefbf742b982b1bf4f0bdf173aabc`.
- Freeze record: `evaluation/OPERATIONAL_DISCRIMINATION_GATE_44855886880_FREEZE_V1.json` (pins that digest; content-based ordering proof).
- Instrument: `evaluation/operational_discrimination_gate_44855886880.py`. Test: `tests/evaluation/test_operational_discrimination_gate_44855886880.py` (8 tests).
- Machine result: `results/evaluation/operational_discrimination_gate/44855886880.json` — **verdict `OPERATIONAL_NO_DELTA`, exit 0, 8/8 claims ok, 4/4 controls holding, 0 failed claims, 0 failed controls**.
- Freeze-first success rule: `OPERATIONAL_NO_DELTA` iff all claims C1–C8 and controls K1–K4 hold; otherwise `OPERATIONAL_CHECKS_FAILED` published as-is with no frozen edit.
- **No frozen bar, rubric, threshold, predicate, verdict contract, baseline or historical artifact was edited.** Frozen inputs were re-hashed **report-only**: `counter_evidence_quality_benchmark.py` `aac86527…`, `fast_mvp_current_head_ca_falsifier.py` `fe4db7ec…`, `mapping_free_recall_falsifier.py` `58a2e77a…`, `fast_mvp_retrieval_recall_benchmark.py` `fa5aa9a5…`, `retrieval_gate/frozen_retrieval_benchmark.json` `187b0e54…`, `RULES_LABEL.json` `4457e971…`, `RULES_GEOMETRY.json` `a7452748…`, `VERDICT_CONTRACT.json` `b9cdb894…` — all byte-identical to accepted pins.

**Instrument self-correction (negative result preserved honestly):** the first execution of the instrument this run returned `OPERATIONAL_CHECKS_FAILED` on control K3 because the initial raw-string scan matched the forbidden falsifier names inside the instrument's own `FORBIDDEN_FALSIFIERS` tuple, not an actual import/call. The check was replaced with an AST-based import/call detector; the result of record above is from the corrected instrument. This was an in-run instrument bug fix, not a change to any frozen input or acceptance rule.

## 2. Adjudication of the v68 ordered work

| Item | Status discharged this run | Evidence |
|---|---|---|
| (1) correction of record | **DISCHARGED, artifacts intact** (not re-run) | Accept `40133253347` (gate `results/audit/evaluation/CYCLE_40133253347_GATE.json` PASS/safe, accept commit `7165d9e0`). Note `BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` sha `b10eeb3a…`, follow-up `CORRECTION_FOLLOWUP_CITATION_40198184759.md` sha `8c3750a5…`, machine records `40113448025.json` + `40144816305.json` all resolve; required needles present (`pipeline.py:1339`, bundle `6eee1149…`, `applied = true`, `n_selected = 0`, `pivot_absent`, `counter_evidence_verified = true`, `4/5`, `51d306c`, `rejection/incumbent handling`). Both machine records honestly publish `CORRECTION_NOT_CONFIRMED`/exit 1 with the CC6/CC7 mount-history limitation; the accepted gate classified those NON-BLOCKING. The 4/5 measurement is unchanged. |
| (2) leg half | **LANDED and byte-identical** | `product/query/counter_evidence_span.py` at current accepted product head hashes to `82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce` — identical to the file accepted evaluation `40258497460` measured — with `REJECTION/INCUMBENT`, `_content_rejection_sweep`, `n_incumbent_downgraded` markers present. |
| (2) full-family half | **NOT MET — 14/15** | The direction's named frozen probe family is 15 members (11 `offline/rent-default` + 4 `server/served`). On the current accepted product mount the post-repair `server/served` bundles carrying `provenance.counter_evidence_span.content_filter` are exactly **3** (`20261024T185740Z`, `40143042888`, `40247189361`). The stale `39202428670/served.bundle.json` has **no** content-filter marker and is not a post-repair member. Member-for-member regeneration is therefore 11+3 = 14/15; the 15th member is still absent. |
| (2) protocol | **NOT EXECUTED — NOT_YET_DISCRIMINATING** | Both H2 triggers unmet: (a) 15th member not regenerated; (b) no evidenced retrieval/reranking code change on the advanced head. No synthetic stand-in, `d2_path_scope_probe` not re-run as the ordered re-measure, packet-of-record `39319405429` not scored, standing falsification not re-run. |
| (3) standing falsification | **UNCHANGED** | Benchmark of record `PRODUCT_FALSIFIED` on packet-of-record `39319405429` (identical 4-gate set) stands; superseded by nothing here. |
| (4) non-blocking fixes | **REPORTED here** | `CYCLE_39965089504_GATE.json` three non-blocking fixes (D1 wording 6-vs-7 tests; D2 wording new-vs-appended test file; D3 environment skip variance 172/1309/20 vs 172/1308/21; gate PASS). Not silently quoted elsewhere in this cycle. |
| (5) no re-derivation | **HONOURED** | No frozen bench, D2 profile or bypass-diagnosis re-derivation; no universal-174k benchmark. |

**Requirement-4 both-halves verified this run:** evaluation `40133253347`, `40258497460`, `40105794124` — each gate file PASS/safe plus accept commits `7165d9e0`, `64208e15`, `bcb4520a` respectively; product current head — accept commit `7be4480e` plus gate `origin/lab/product:results/audit/product/CYCLE_40284658455_GATE.json` PASS/safe/fixes=0. The historical product baseline `8b5b08dd`/`40100397058` commits are absent in this shallow checkout; their both-halves acceptance was audited by accepted evaluation `40258497460` and is **cited, not re-derived** (disclosed in the machine result).

## 3. Side-by-side defect reading — READ from committed records, not measured here

| Record | n_enriched | verified scored rows | defective rows | defect histogram | sound rows |
|---|---|---|---|---|---|
| Baseline `40105794124` (accepted, product head `8b5b08dd`) | 5 | 5 | **4** | D2 2 / D3 2 / D4 1 over 4 distinct decisions | 1 (`bstger_SK.2023.49`) |
| Post-repair `40258497460` (accepted, product's 49-bundle 4-offline-query+1-server family) | 49 | 55 | **0** | {} (no D2/D3/D4) | 19 |

These two rows are **different families** and are published side by side, never merged or substituted (factory-wide requirement 16): the direction's named frozen probe family is 15 members, while Product's claimed regenerated family is a different 49-bundle set. Post-repair `0` defects on Product's family does **not** discharge item (2)'s member-for-member precondition on the named family.

## 4. Negative results preserved (evidence of record, not re-derived here)

- **FAST-MVP falsifier `40105794124` (accepted bcb4520a):** `SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false` (H2 false); 4/5 enriched source-valid bundles carry a frozen content defect (D2 2, D3 2, D4 1) over 4 distinct decisions; exactly 1 sound row (`bstger_SK.2023.49`); pins matched and controls C1–C4 held. The v67 "fixture_generation bypasses the filter" explanatory clause is superseded as explanation by the accepted bundle provenance at `8b5b08dd`; the 4/5 measurement stands.
- **Post-repair CA falsifier `40258497460` (accepted 64208e15):** `SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`, 0 defects on 49 bundles — but named frozen family only 14/15, so item (2) stayed NOT_YET_DISCRIMINATING.
- **Fastest retrieval/CA falsifier `40261335674` (producer-attested, recorded PENDING_INDEPENDENT_AUDIT — not accepted evidence):** `PRODUCT_FALSIFIED_RECALL_LOSS`, exit 1, 0 retrieval network calls over 24 cached FR/DE/IT × baseline/counter cells; input hits 17 vs product hits 15 of 18 present; language legs fr 4→3 (holds=false), de 12→11 (holds=false), it 1→1 (holds=true); the product reranker drops frozen authorities its own candidate input kept in the top-20 (`baseline:business-judgment-rule:de` retention 1.0→0.0; `counter:petty-theft-dismissal:fr` fr authority loss). Byte-identical to accepted comparison run `40153908549` (0 of 24 cells differ). This is a known-relevant-channel recall loss handed to Core Product; because the retrieval/reranking code shows no evidenced change on the advanced head, it was **not** re-run this cycle.
- **Frozen-bar cycles `40109694894` (accepted d1de037b):** `LABEL_SOUND NOT_MET` 5/65 = 0.076923; `GEOMETRY_SOUND NOT_MET` 0/3. Both DO-NOT-SERVE orders stand.
- **Multilingual/provenance reuse suite could NOT be executed in this producer image:** `tests/evaluation/test_retrieval_benchmark.py` fails to import (`ModuleNotFoundError: No module named 'numpy'` once the product mount is on `PYTHONPATH`; `ModuleNotFoundError: No module named 'product'` without it). The shim's `SHIM_PASS (0 passed …)` is a **vacuous pass and is not claimed as a reuse-suite pass**; records `44855886880_multilingual_provenance_shim{,_retry}.json` preserve the limitation. Prior accepted cycles' reuse results (e.g. 73/0/0/0 under `40209360877`) remain the evidence of record. Installing numpy/pytest is not a lane call and no benchmark was re-run to chase it.

## 5. Re-dispatch pathology (control-plane hardening, recorded not patched)

`state/evaluation.json` already declared `cycle_status=COMPLETE`, `continue_recommended=false`, `direction_version=68`. The lane was nevertheless re-dispatched as run `44855886880`. This is the standing supervisor `jq '.continue_recommended // true'` dead-code pathology (requirements 13/15/22): `//` treats literal `false` as empty, so an exhausted lane re-dispatches. `.github/**` is control-plane scope and was **not** edited; the supervisory stop is the portfolio/status field, recorded here for the director.

## 6. Decision

- **Recommendation:** PAUSE this lane under the v68 question — `continue_recommended=false`. No further same-question cycle has a discriminating purpose until Core Product either (a) regenerates the 15th named frozen-family member (4th post-repair `server/served` bundle) or (b) changes the retrieval/reranking code, at which point item (2) or the recall falsifier becomes discriminating under a NEW freeze-first record.
- **Product-facing handoff (unchanged, concrete):** the reranking recall loss (`40261335674`) and the missing 15th post-repair family member are the two open product facts that would unlock a discriminating evaluation cycle.
- **No posture change:** `human_gate_ready`, `machine_gate_ready`, `packet_admitted`, `ready_for_owner_session` all FALSE; `owner_decision_required` false; both DO-NOT-SERVE orders stand; no serve verdict issued.
- **Claim ceiling:** operational provenance/acceptance verification only. No new quality measurement, no frozen-bar result, no serve verdict, no human-gate claim.
