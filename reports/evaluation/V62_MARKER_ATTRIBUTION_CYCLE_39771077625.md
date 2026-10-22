# V62 evaluation cycle 39771077625 — marker attribution + stand-ready companions

- Lane: evaluation | Direction: v62 | Run: 39771077625 | FREEZE-FIRST commit: `0f08f400`
- Headline: **MARKER_BLINDSPOT_ATTRIBUTED** (exit 1, 7/7 controls hold) — the accepted cached-bundle negative result (run 39766474798: 0 counter candidates on 2/4 frozen questions) is causally attributed to the marker/lexicon layer on known-counter rows the counter channel already retrieved
- No frozen bar, rubric, threshold or verdict contract was touched; no universal-174k benchmark was run; zero network calls

## 1. Freeze-first discipline

`evaluation/V62_COUNTER_MARKER_ATTRIBUTION_HYPOTHESIS_V1.json` (sha256 `039c0c7f…`) and its freeze record were committed at `0f08f400` BEFORE any claim-bearing execution. The pre-freeze scratch recon (one /tmp reconstruction, three scratch shim runs) is disclosed verbatim in the hypothesis. The instrument (`evaluation/counter_marker_attribution.py`, sha256 `0c31734e…`) imports the accepted `bundle_producer` functions unchanged and re-hashes the frozen spec (`187b0e54…`) and the accepted record (`5fd695aa…`) fail-closed before AND after.

## 2. Attribution result (the deliverable)

Full report: `reports/evaluation/COUNTER_MARKER_ATTRIBUTION_39771077625.md`; machine record: `results/evaluation/counter_marker_attribution/39771077625.json`.

- Both zero-yield questions (corporate-criminal-liability, business-judgment-rule) → **MARKER_RULE_BLINDSPOT_ATTRIBUTED**, dominant class LIMITATION_LEXICON_ABSENT on every reached known-counter row.
- Aggregate: 15/28 frozen known-counter ids reached; 14/15 reached rows unlabelled; 13/14 unlabelled rows carry ZERO limitation tokens on the extended surface too — the blindness is **lexicon-level, not surface-level**; widening the marker surface alone would not fix it.
- Co-existing channel gap published separately: 13/28 known-counter ids NOT reached (remedy: counter-query expansion, never folded into the marker attribution).
- C3 parity reproduced the accepted counts exactly ({16,0,0,4}); `diverged_questions` empty.

## 3. Stand-ready companions (ordered items 1, 2, 5)

- **Remedy (a) probe** (reused unchanged): REMEDY_A_NOT_LANDED, planner pin `57b6a6f9…` re-verified at product head `48969821` (unchanged since the v62 anchor). Record: `results/evaluation/remedy_a_landed_probe/39771077625.json`. The re-freeze duty stays pending until the product lands the fix.
- **Stand-ready status**: no new served packet (no accepted serve recommendation replaces either DO-NOT-SERVE order); cross-check duty NOT DUE (no new accepted product measurement). Record: `results/evaluation/stand_ready_status/39771077625.json`.
- **V3 multilingual/provenance re-measurement** under this run id (functions reused unchanged): PARTIAL_MISS 0/3 with the IDENTICAL failure signature to the accepted record 39471603258 (same four missing product-side provenance fields; all three bundle sha pins HELD; language and source-URL checks pass). Published as a re-measurement of unchanged bytes, NOT a new falsification. Record: `results/evaluation/v3_multilingual_provenance_reuse/39771077625.json`.

## 4. Test suites (claim-bearing shim under run id)

`evaluation/no_pytest_runner.py` (pytest absent in producer image; shim verdicts are upper bounds):

| suite | result |
|---|---|
| tests/evaluation/test_counter_marker_attribution.py (new) | SHIM_PASS 18/0/0 |
| tests/evaluation/test_stand_ready_multilingual_probe.py (reused) | SHIM_PASS 16/0/0 |
| tests/evaluation/test_query_map_bundle_producer.py (reused) | SHIM_PASS 25/0/0 |

Total 59 passed, 0 failed, 0 unsupported. Records: `results/evaluation/orchestration/39771077625_*_pytest_shim.json`.

## 5. State integrity

PRE: `results/evaluation/state_integrity_gate/39771077625_pre.json` — AT_LEAST_ONE_CHECK_FAILED, the single failure `root_lane_parity@both` being the pre-existing github_run divergence (root `39766474798` vs lane `39759523387`) inherited from the previous cycle. This cycle reconciles both state files to github_run `39771077625` and advances `accepted_run_id` to `39766474798` (newest in-tree audited+integrated gate, PASS/safe=true). POST record: `results/evaluation/state_integrity_gate/39771077625_post.json` (see machine record for the verdict).

## 6. Claim ceiling / gate fields

Attributes the evaluation fixture's frozen marker rule on accepted cached rows; measures no product classifier; moves no bar; lifts no order; claims no jurist usefulness. human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session, owner_decision_required all stay false. Both DO-NOT-SERVE orders stand; admission stays fail-closed.

## 7. Next recommendation

CONTINUE, bounded, same question (v62): (1) stand ready for remedy (a) to land — then re-freeze the repair verification under a NEW run id and re-score the mapping-free counter_authority_surface gates; (2) cross-check the product lane's four deliverables as they land; (3) the marker-attribution finding (lexicon-level blindness, 13/28 channel gap) is a product-lane feed: any counter-labelling layer built on a lexical norm+limitation conjunction will hide the very known counter authorities the counter channel retrieves; (4) when product serves a new packet, falsify-or-pass its exact bytes under a NEW run id.
