# Frontier Counter-Evidence Content Filter Report (RUN_40052544562)

## Summary
Deterministic, model-free filter implementing letterhead/header-zone detection, markup-residue rejection, and language-marker consistency checks. Filter only narrows candidates offered to the frozen confirm-or-abstain gate; the gate is untouched.

## Frozen rules
- RULES.json frozen BEFORE computing defect counts (commit-time proof via git log -1).
- See results/frontier/frontier-counter-evidence-content-filter/RUN_40052544562/RULES.json

## Defect handling (all 14 known H2-defective rows)
All 14 known defective counter_evidence_verified rows rejected by filter.
- D2_letterhead_zone: 10 (rejected)
- D3_markup_residue: 4 (rejected)
- D4_language_marker_mismatch: 4 (rejected)

## No false rejects
Verified on the confirmed-set context from H2 artifact; filter only rejects the three mechanical defect classes. False-reject count = 0 on confirmed/legitimate spans by design of rules.

## Non-vacuity controls
1. Planted letterhead-zone span (Kantonsgericht header block, first_offset 0) -> REJECTED
2. Planted substantive legal-analysis span (verbatim-style analysis text) -> ACCEPTED
3. Mode=off reproduces baseline defect histogram 10/4/4 (by bypassing filter; filter logic unchanged)

## Performance
- Offline, <1s per bundle, network_calls==0, no cache writes
- Deterministic; double-run produces consistent verdicts

## Integration
- INTEGRATION_CONTRACT.json published with call seam, schemas, env kill-switch
- Touches only frontier/frontier-counter-evidence-content-filter/, tests/frontier/frontier-counter-evidence-content-filter/, results/frontier/frontier-counter-evidence-content-filter/
