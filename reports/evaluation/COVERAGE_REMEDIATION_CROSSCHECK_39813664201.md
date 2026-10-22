# Coverage-Remediation Cross-Check — run 39813664201

- Verdict: **COVERAGE_EVIDENCE_REPRODUCES** (exit 0)
- Product mount head: `443302120a5b7221d8bb5c605848b29eb68bca19`
- Fresh offline replay: planned=24 executed=24 network=0 frozen_ids_reached=23
- Committed live reach: 23 (recomputed 23)
- Committed offline reach: 16 (recomputed 16)

## Gates

- **V1_frozen_text_snapshot_pins_the_accepted_benchmark**: passed=True
- **V2_fresh_offline_replay_is_offline_and_cache_pure**: passed=True
- **V3_reach_unions_recompute_and_offline_replay_supersets_committed_reach**: passed=True

## Controls

- **D1_frozen_spec_rehash**: holds=True
- **D2_planted_union_detects_a_fake_id**: holds=True
- **D3_planted_reach_loss_detects_falsification**: holds=True

## Claim ceiling

This instrument establishes exactly one thing: that the product lane's committed query-coverage remediation evidence is internally consistent (its reach unions recompute from its own per_text rows), pin-clean (the snapshot pins the accepted frozen benchmark), and REPLAYABLE offline through the shipped product code from the product's own cache with zero network, with no reach loss against the committed offline evidence. It is NOT a counter-authority recall measurement under the frozen known-counter sets (the marker/lexicon blindness finding of accepted run 39771077625 stands unchanged: lexical norm+limitation conjunctions still hide retrieved known counter authorities; coverage fixes the CHANNEL gap, not the lexicon gap); it is NOT a re-score of the mapping-free counter_authority_surface gates; it is NOT a label or geometry bar claim (both stay REPORTED-ONLY and unmet); it is NOT a serve recommendation and lifts no DO-NOT-SERVE order; admission stays fail-closed; human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session and owner_decision_required stay false. It re-derives no threshold, bar, rubric or verdict contract and runs no obsolete universal-174k benchmark.
