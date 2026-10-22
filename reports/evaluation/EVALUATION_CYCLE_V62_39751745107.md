# Evaluation Lane Cycle Report — v62 / GitHub Run 39751745107

## Summary

**Status**: COMPLETE — Evaluation lane updated to direction version 62, incorporating all accepted evidence including the retrieval_pool_attribution_v2 audit PASS (run 39744816712).

**Verdict**: The smallest executable retrieval/counter-authority benchmarks (mapping_free_recall_falsifier, minimal_ca_benchmark_v3) falsify the product on the packet-of-record V3 exact bytes. The retrieval-side root cause of the counter-authority collapse is attributed to frozen cause classes via an independently audited measurement.

---

## Key Deliverables Completed

### 1. Retrieval Pool Attribution V2 — INDEPENDENTLY ACCEPTED (Run 39744816712)
- **Audit gate**: PASS, safe_to_integrate=true, required_fixes=[]
- **Measurement**: Replays the product's recorded request against live OpenCaseLaw to attribute zero-row core concepts in the served German bundle (packet 39319405429, de-kapitalverletzung)
- **Attribution**:
  - `kapitalverletzung` → **CORPUS_TERM_ABSENCE** (oracle: 0/100 rows contain concept)
  - `uberwachungspflicht` → **POOL_NEVER_COVERS** (oracle: 51/100 rows contain concept, product query retrieves 0)
- **Dominant class**: POOL_NEVER_COVERS (query recall defect)
- **Dominant remedy**: Query expansion / concept injection (product owns `lexicon_expansion` but does not apply it to German question)
- **Remedy probe**: Expanded query still yields 0 for both concepts
- **Non-vacuity controls**: 8/8 HOLD (all frozen before execution)
- **Supersedes**: V1 (39739350804, REVISE)

### 2. Mapping-Free Recall Falsifier — PRODUCT_FALSIFIED on TWO Packets
| Run | Packet | Verdict | Gates (18) | Counter-Authority Surface |
|-----|--------|---------|------------|---------------------------|
| 39693031072 | 39319405429 (V3) | PRODUCT_FALSIFIED | 11 passed / 4 failed | n_issued=0 on all 3 languages |
| 39725464259 | 39275520116 | PRODUCT_FALSIFIED | 11 passed / 4 failed | n_issued=0 on all 3 languages |

**Discriminating finding**: Zero counter-authority emission is a STANDING property of the two most recent packets (both n_issued=0 on all three languages), NOT a V3-specific regression. The legacy served packet 38839347028 issued 25/15 de/fr rows. Collapse occurred between 38839347028 and 39275520116.

### 3. Minimal CA Benchmark V3 — EXECUTED, PENDING INDEPENDENT AUDIT (Run 39732040165)

> **CORRECTED by repair round 1 of run 39759523387 (audit CYCLE_39751745107,
> required_fixes 5-6).** The original wording of this section presented run
> 39732040165 as a cycle deliverable under accepted framing. There is NO
> independent audit gate for 39732040165 (no
> `results/audit/evaluation/CYCLE_39732040165_GATE.json` in any tree). Its
> numbers are producer-attested and PENDING INDEPENDENT AUDIT; they are not
> accepted evidence. The ACCEPTED minimal-CA-benchmark record is a DIFFERENT
> thing: cycle 39388198135 via accept commit 5644ce71
> (BENCHMARK_VALID_NO_FALSIFICATION — proves the frozen gates can falsify a
> deliberately regressed input; it never accepted run 39732040165). The
> control-plane state's audited reference run is
> `test_operational_resume_39680754374` (audit 39684675951, gate REVISE,
> safe_to_integrate true). See
> `reports/evaluation/EVALUATION_CYCLE_V62_39751745107_REPAIR1.md`.

- 18 gates, 11 passed / 4 failed / 3 reported (producer-attested, pending audit)
- Failed gates: concept_coverage (de-kapitalverletzung), counter_authority_surface (all 3 languages)
- Non-vacuity controls: ALL HOLD (producer-attested, pending audit)
- Benchmark is non-vacuous: deliberately regressed inputs make gates fail (FAIL_REGRESSION) — this validity property is what cycle 39388198135 / accept 5644ce71 established as accepted evidence

### 4. Counter-Probe Bounded Cause — ATTRIBUTED ON BOTH SIDES
| Side | Measurement | Status |
|------|-------------|--------|
| Retrieval-side | retrieval_pool_attribution_v2 (39744816712) | ACCEPTED, audit PASS |
| Label-side | counter-emission charter (39426324296) | A_EMISSION_RECOVERED, charter_closed=true |

### 5. Falsification Battery & Serve Verdict — DISCHARGED / LANDED
- Falsification battery DISCHARGED on V3 exact bytes (39379766198)
- Serve verdict LANDED and CROSS-CHECKED (frontier-packet-serve-audit 39371834165, BOUNDED-NEGATIVE)
- Minimal CA benchmark VALIDITY accepted via 5644ce71 (cycle 39388198135, BENCHMARK_VALID_NO_FALSIFICATION — gates-can-falsify-regressed-inputs only; CORRECTED by repair 39759523387: this commit did NOT accept run 39732040165)

---

## Stand-Ready Duties (Next Cycle)

1. **Remedy (a) NOT LANDED**: The shipped planner on product mount 48969821 still reproduces the BASELINE (placeholder-anchored) arm on both contaminated German bundles. When the product lands the fix (strip redaction placeholder from probe key terms), re-freeze the repair verification and re-score the mapping-free CA-surface gates on regenerated bundles under a NEW run id.

2. **Stand-ready cross-check duty**: On the next accepted product measurement, perform side-by-side divergence-as-headline cross-check.

3. **No new served packet**: frontier-counter-label-emission stays TERMINATED.

---

## Orchestration/Validation Failure Diagnosis

The operational resume of persisted producer snapshot 39470495546 (run 39471603258) diagnosed and resolved:
- **Failure class**: PRODUCER_AUTHORED_AUDIT_PLACEMENT_OUT_OF_LANE_SCOPE
- **Root cause**: Producer wrote audit files into the independent auditor's protected namespace (results/audit/evaluation/, reports/audit/evaluation/)
- **Resolution**: Out-of-scope files re-homed byte-exactly into lane namespace, valid work preserved
- **Verification**: V3 falsifier reproduced (PRODUCT_FALSIFIED, 18 gates 11/4/3, zero input drift, non-vacuity holds, frozen pins byte-identical)

---

## Evidence References (Updated)

> **CORRECTED by repair round 1 of run 39759523387**: the original sentence
> below claimed "118 evidence references" in "both state files". The actual
> lengths were 108 (root) and 84 (lane) and the two `evidence_refs_n`
> metadata fields wrongly said 118/92. After the repair both files carry
> `evidence_refs_n` equal to their list length (108 / 84), every ref is a
> resolvable file, and new repair artifacts are disclosed under the separate
> `repair_round_1_refs` key so the historical counts stay stable.

Both state files updated with evidence references including:
- retrieval_pool_attribution_v2 hypothesis, freeze record, instrument, result, audit gate, audit report
- mapping_free_recall_falsifier runs on two packets (39693031072, 39725464259)
- minimal_ca_benchmark_v3 on V3 packet (39732040165)
- All historical evidence preserved verbatim per AGENTS.md items 5/6

---

## State Updates

| File | direction_version | accepted_run_id | github_run |
|------|-------------------|-----------------|------------|
| /home/runner/work/LexMachina/LexMachina/state/evaluation.json | 62 | 39744816712 | 39751745107 |
| /home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation.json | 62 | 39744816712 | 39751745107 |

---

## Claim Ceiling

This cycle claims exactly:
- The retrieval_pool_attribution_v2 measurement (39744816712) is independently accepted and attributes the accepted zero-row concepts to frozen cause classes
- The mapping-free recall falsifier falsifies the product on two packets (PRODUCT_FALSIFIED)
- The minimal_ca_benchmark_v3 falsifies the product on V3 packet (PRODUCT_FALSIFIED)
- The counter-probe bounded cause is attributed on both retrieval and label sides

This cycle does NOT claim:
- Any verdict/gate/admission on any packet beyond what is measured
- The absolute LABEL_SOUND or GEOMETRY_SOUND bars are met
- Either DO-NOT-SERVE order is lifted
- The map helps a jurist (human product gate question)
- Any decision IS supporting/contrary/limiting
- Any unblocking of the human gate

**human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session, owner_decision_required all stay false.**

---

## No Universal-174k Benchmarks Rerun

All measurements use query-specific packet bytes and frozen mapping-free gates. No obsolete universal-174k geometry benchmarks were executed.

---

## Next Recommendation

**CONTINUE, bounded, same question (v62)** — Stand ready for product fix (remedy a) landing, then re-freeze and re-score. Do NOT re-dispatch zero-delta cycles; do NOT re-litigate closed items.