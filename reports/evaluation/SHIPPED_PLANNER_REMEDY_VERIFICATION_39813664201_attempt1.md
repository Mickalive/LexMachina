# Shipped-Planner Remedy (a) Verification — run 39813664201

- Verdict: **ENVIRONMENT_OR_VACUOUS** (exit 2)
- Product mount head: `443302120a5b7221d8bb5c605848b29eb68bca19` (expected `443302120a5b7221d8bb5c605848b29eb68bca19`)
- Shipped planner sha256: `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9`
- Pre-remedy planner pin (disclosed): `57b6a6f99793ef6663957ccdcd51a577feb9c8d7075efcc339f5c25bece065e1`
- Population: 14 measured bundles (2 formerly contaminated)
- Pins: before 4 checks all_ok=True; after 4 checks all_ok=True
- Network calls: 0

## Gates

- **G1s_shipped_anchor_clean**: passed=True (failed=0) — no placeholder token in the shipped topic anchor on any measured bundle
- **G2s_formerly_contaminated_regain_topicality**: passed=True (failed=0) — shipped anchor shares a content term with the question on every formerly-contaminated bundle
- **G3s_clean_bundles_unperturbed**: passed=True (failed=0) — shipped probe queries byte-equal the accepted BASELINE queries on every formerly-clean bundle
- **G4s_shipped_matches_accepted_fixed**: passed=True (failed=0) — shipped probe queries and anchor byte-equal the accepted repair-verification FIXED arm on every bundle

## Controls

- **C1s_fixture_integrity**: holds=False — accepted repair-verification record re-hashes to its pin and its verdict is REPAIR_VERIFIED_ON_RECORDED_BYTES
- **C2s_placeholder_preconditions_intact**: holds=False — REDACTION_PLACEHOLDER unchanged and shipped answer_key_terms derives exactly {citation, removed, retrieved} from it
- **C3s_defect_was_real**: holds=True — the accepted record carries at least one baseline-contaminated row
- **C4s_planted_preremedy_extractor_detects_the_defect**: holds=False — PRE-REMEDY-emulated extractor reproduces contamination on exactly the 2 formerly-contaminated bundles and stays clean on the other 12
- **C5s_zero_network_and_emission_preserved**: holds=True — zero network calls; shipped planner still emits probe plans on every measured bundle

## Claim ceiling

This instrument establishes exactly one thing: whether the SHIPPED planner at the pinned product head reproduces, byte-for-byte on the pinned recorded 14-bundle population, the probe queries and anchors that the accepted offline repair verification verified synthetically. It is NOT a counter-authority RECALL measurement (no probe is executed against OpenCaseLaw; network_calls=0); it is NOT a re-score of the mapping-free counter_authority_surface gates (the V3 packet-of-record bytes stay frozen with 0 issued counter rows and the ordered re-score awaits REGENERATED bundles, which do not exist because no accepted serve recommendation exists); it is NOT a label or geometry bar claim (both stay REPORTED-ONLY and unmet); it is NOT a serve recommendation and lifts no DO-NOT-SERVE order; admission stays fail-closed; human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session and owner_decision_required stay false. It re-derives no threshold, bar, rubric or verdict contract; the frozen RULES_LABEL/RULES_GEOMETRY/VERDICT_CONTRACT hashes are not consumed by this instrument and are not re-tuned. It runs no obsolete universal-174k benchmark.
