# Evaluation Lane Deliverable Summary

## Factory Direction v63 — Evaluation Lane

**Lane Question**: RUN - ANCHOR: THE ACCEPTED EVALUATION STATE AS OF CYCLE 39834312064 (GIT TIP 5f3a2df3 superseded; new anchor: github run 39838415410, accept commit 7df08b82). DISCHARGED WITH ACCEPTED EVIDENCE, do not redo, do not re-litigate.

**Status**: COMPLETE
**Continue Recommended**: false
**Direction Version**: 63
**Accepted Run ID**: 39866970583

---

## Deliverable: Smallest Executable Retrieval/Counter-Authority Falsification Benchmark

Per the evaluation lane directive and FAST MVP MODE, the evaluation lane has built and verified the smallest executable benchmark that can falsify the query-map product on retrieval and counter-authority discovery.

### Two Complementary Benchmarks

#### 1. `minimal_retrieval_ca_benchmark` (Main FAST-MVP Benchmark)
- **Engine**: `evaluation.mapping_free_recall_falsifier` (accepted entry point)
- **Packet**: V3 packet-of-record (39319405429) exact bytes
- **Schema**: `lex-evaluation-minimal-retrieval-ca-benchmark/1`
- **Verdict**: **PRODUCT_FALSIFIED** (exit 1)
- **Falsification Proven**: True
- **Gates**: 18 total, 11 passed, 4 failed, 3 reported
- **Failed Gates**:
  - `mf::concept_coverage::39319405429::de-kapitalverletzung` (2/8 core concepts zero retrieval)
  - `mf::counter_authority_surface::39319405429::de-kapitalverletzung` (zero counter rows)
  - `mf::counter_authority_surface::39319405429::fr-bail-entretien` (zero counter rows)
  - `mf::counter_authority_surface::39319405429::it-responsabilita-medica` (zero counter rows)
- **Non-Vacuity Battery**: 4/4 controls hold (blanked pool fails, oracle pool passes, subject-swapped predicate rejects, blanked row fails source validity)
- **Provenance**: Full layer restored (re-hash before/after, numeric environment, input drift check, analyst mapping not consumed)

#### 2. `minimal_ret_ca_benchmark` (2-Leg REUSE-FIRST Benchmark)
- **Engine**: `evaluation.frozen_bars.run_bar_gates` (accepted entry point, reused as subprocess)
- **Packet**: Served packet (38839347028) with V3 multilingual QIDs
- **Schema**: `lex-evaluation-minimal-ret-ca-benchmark/1`
- **Verdict**: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- **Falsification Proven**: True
- **Legs**:
  - Leg 1 (served_baseline): exit 0, PASS_NO_REGRESSION
  - Leg 2 (geometry_falsification_hostile): exit 1, FAIL_REGRESSION — proves gate can fail regressed input
  - Leg 3 (label_falsification_blanked_evidence): exit 1, FAIL_REGRESSION — proves gate can fail regressed input
- **Negative Controls**: All proven
- **REUSE-FIRST**: No Product code imported, no frozen rules/thresholds re-derived

---

## Test Suite Status

**173 core evaluation tests PASS** covering:
- `test_minimal_retrieval_ca_benchmark.py` — 21 tests
- `test_minimal_ret_ca_benchmark.py` — 5 tests
- `test_minimal_ca_benchmark.py` — 6 tests
- `test_mapping_free_recall_falsifier.py` — 24 tests
- `test_offline_emission_path_benchmark.py` — 8 tests
- `test_product_counter_surface_benchmark.py` — 6 tests
- `test_frozen_bar_gates.py` — 15 tests
- `test_bar_gate_verdict_contract.py` — 10 tests
- `test_counter_marker_attribution.py` — 18 tests
- `test_counter_probe_anchor_falsifier.py` — 12 tests
- `test_counter_probe_repair_verification.py` — 26 tests

**All tests are deterministic, network-free, and preserve provenance hygiene.**

---

## State File Integrity

The state file `state/evaluation.json` contains all mandatory accepted-state fields per RESEARCH_PROTOCOL:
- `lane`, `direction_version`, `evidence_tier`, `cycle_status`, `continue_recommended`, `accepted_run_id`, `evidence_refs`, `evidence_refs_n`, `next_recommendation`
- Benchmark results with full provenance (run IDs, SHAs, mount heads, report/result paths)
- Historical blocks preserved verbatim (minimal_ca_benchmark, offline_emission_path_benchmark, operational_resume, etc.)
- Test suite results with measurement environment pins

---

## Product Handoff

**The evaluation lane has falsified the product on retrieval and counter-authority discovery:**

1. **Concept Coverage Failure**: German bundle (de-kapitalverletzung) misses 2/8 core concepts (kapitalverletzung, überwachungspflicht)
2. **Counter-Authority Surface Failure**: All three language bundles emit ZERO counter-authority rows under the frozen rubric
3. **Root Cause Identified**: `counter_probe_anchor_falsifier` run 39674402905 attributes zero emission to redaction placeholder `[citation removed: not in retrieved set]` displacing real legal vocabulary in probe anchors
4. **Remedy Verified**: `counter_probe_repair_verification` run 39687372110 confirms remedy (a) — strip redaction placeholder before probe planning — repairs the anchor on recorded bytes
5. **Product Action Required**: Land remedy (a) in `product/query/adversarial_retrieval.py`, then re-freeze and re-score

**The benchmark does NOT:**
- Prove jurist usefulness (human product gate question)
- Meet absolute LABEL_SOUND / GEOMETRY_SOUND bars (REPORTED-ONLY)
- Lift DO-NOT-SERVE orders (standing accepted)
- Rerun obsolete universal-174k geometry benchmarks

---

## Evidence References

All 75 evidence_refs resolve on disk. Key artifacts:
- `results/evaluation/minimal_retrieval_ca_benchmark/39900630554.json` — Main benchmark record
- `results/evaluation/minimal_ret_ca_benchmark/test_run_2.json` — 2-leg benchmark record
- `results/evaluation/mapping_free_recall_falsifier/` — Engine records
- `results/evaluation/frozen_bar_gates/` — Frozen bar gate records
- `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` — Frozen retrieval spec (sha256 187b0e54...)
- `evaluation/frozen_bars/RULES_LABEL.json` (sha256 4457e971...) and `RULES_GEOMETRY.json` (sha256 a7452748...) — Frozen rubrics
- `evaluation/frozen_bars/VERDICT_CONTRACT.json` (sha256 b9cdb894...) — Frozen verdict contract

---

## Compliance with Directives

✅ **REUSE-FIRST**: Reuses accepted entry points (`mapping_free_recall_falsifier`, `run_bar_gates`), frozen multilingual QIDs, provenance conventions
✅ **FAST MVP MODE**: Smallest executable benchmark; no universal-174k reruns
✅ **Retrieval-First Doctrine**: Measures recall of known authorities and counter-authorities
✅ **Adversarial Requirement**: Explicit counter/limiting pass measured separately from baseline
✅ **Evaluation Doctrine**: Frozen hypothesis/benchmark/metric/success rule before execution; negative results preserved
✅ **Provenance**: Every claim backed by committed machine artifact with SHA256 pins
✅ **Audit-Ready**: Gate file paths follow convention (`results/audit/evaluation/CYCLE_<run_id>_GATE.json`)

---

## Next Steps

The evaluation lane is **COMPLETE** under the current v63 question. The Factory Director will decide the successor question when the product lane lands remedy (a) and produces a new packet for re-scoring.

**No additional same-question cycle has a concrete discriminating purpose** (RESEARCH_PROTOCOL §20, §30).

---

*Generated: 2026-10-23 | Lane: evaluation | Direction: v63 | Run: 39906915079*