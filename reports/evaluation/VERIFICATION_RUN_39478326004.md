# Evaluation Lane Verification — Run 39478326004

**Date:** 2026-10-20  
**Direction Version:** 61  
**Factory Run:** 39478326004  
**Status:** VERIFIED — All deliverables confirmed

---

## Summary

This verification run confirms that the Evaluation lane's ordered work under factory direction v61 is **complete and discharged**. All three key benchmarks execute correctly and produce the expected verdicts on the accepted product mount (`/tmp/lex_accepted/product`).

### Verified Benchmarks

| Benchmark | Packet | Verdict | Exit Code | Falsification Proven |
|-----------|--------|---------|-----------|---------------------|
| `counter_authority_surface_falsifier.py` | V3 (39319405429) | **PRODUCT_FALSIFIED** | 1 | — |
| `minimal_ca_benchmark.py` | V3 (39319405429) | **BENCHMARK_VALID_NO_FALSIFICATION** | 0 | **true** |
| `benchmark_retrieval_counter_authority.py` | Served (38839347028) | **BENCHMARK_VALID_NO_FALSIFICATION** | 0 | **true** |

---

## Detailed Results

### 1. Counter-Authority Surface Falsifier (V3 Packet-of-Record)

**Command:**
```bash
python -m evaluation.counter_authority_surface_falsifier \
  --run-id local_verification_39478326004 \
  --out /tmp/verification_ca_surface.json \
  --product-mount /tmp/lex_accepted/product
```

**Result:** `PRODUCT_FALSIFIED` (exit 1)

- **Questions measured:** 3 (de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica)
- **Total gates:** 18
- **Passed:** 11
- **Failed:** 4
- **Reported (non-pass/fail):** 3
- **Non-vacuity controls:** ALL HOLD (4/4)
- **Input drift:** NONE (byte-identical frozen pins)

**Failed Gates (expected falsifications):**
1. `mf::concept_coverage::39319405429::de-kapitalverletzung` — Core concept coverage gap
2. `mf::counter_authority_surface::39319405429::de-kapitalverletzung` — Empty counter-authority surface (n_issued=0)
3. `mf::counter_authority_surface::39319405429::fr-bail-entretien` — Empty counter-authority surface (n_issued=0)
4. `mf::counter_authority_surface::39319405429::it-responsabilita-medica` — Empty counter-authority surface (n_issued=0)

**Claim Ceiling Honored:** The instrument does NOT claim the map helps a jurist, does NOT meet absolute LABEL_SOUND/GEOMETRY_SOUND bars, does NOT lift DO-NOT-SERVE orders, and does NOT certify packet admission. `human_gate_ready=false`, `packet_admitted=false`, `owner_decision_required=false`.

---

### 2. Minimal CA Benchmark (V3 Packet-of-Record)

**Command:**
```bash
python -m evaluation.minimal_ca_benchmark \
  --run-id local_verification_39478326004 \
  --out-dir /tmp/verification_minimal_ca \
  --report-dir /tmp/verification_minimal_ca_reports
```

**Result:** `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0)

| Leg | Mode | Expected Exit | Actual Exit | Verdict | Matches Expectation |
|-----|------|---------------|-------------|---------|---------------------|
| 1. Served Baseline Provenance | served_lineage | 2 (ENVIRONMENT_ERROR) | 2 | ENVIRONMENT_ERROR | ✓ |
| 2. Hostile Geometry Falsification | adjudicate | 1 (FAIL_REGRESSION) | 1 | FAIL_REGRESSION | ✓ |
| 3. Blanked Evidence Label Falsification | adjudicate | 1 (FAIL_REGRESSION) | 1 | FAIL_REGRESSION | ✓ |

**Falsification Proven:** `true` — Both regressed-input legs fire, proving the frozen bar gates can fail deliberately regressed inputs on the V3 packet bytes.

**Note:** Leg 1 correctly shows ENVIRONMENT_ERROR (exit 2) because the V3 packet's bundle content diverges from the GEOMETRY_HALF oracle (the served-bytes fidelity pin). This is an accepted provenance check, not a product verdict.

---

### 3. Retrieval/Counter-Authority Benchmark (Served Packet)

**Command:**
```bash
python -m evaluation.benchmark_retrieval_counter_authority \
  --run-id local_verification_39478326004 \
  --out-dir /tmp/verification_ca_bench \
  --report-dir /tmp/verification_ca_bench_reports
```

**Result:** `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0)

| Leg | Expected Exit | Actual Exit | Verdict | Matches Expectation |
|-----|---------------|-------------|---------|---------------------|
| 1. Served Baseline | 0 (PASS_NO_REGRESSION) | 0 | PASS_NO_REGRESSION | ✓ |
| 2. Hostile Geometry Falsification | 1 (FAIL_REGRESSION) | 1 | FAIL_REGRESSION | ✓ |
| 3. Blanked Evidence Label Falsification | 1 (FAIL_REGRESSION) | 1 | FAIL_REGRESSION | ✓ |

**Falsification Proven:** `true` — Served packet passes regression; both deliberately regressed inputs make the gates fail.

---

## Test Suite Verification

**Command:**
```bash
python -m pytest tests/evaluation/test_minimal_ca_benchmark.py tests/evaluation/test_counter_authority_surface_falsifier.py -v
```

**Result:** **23 passed** in 10.27s

All dedicated tests for the two V61-ordered benchmarks pass, confirming:
- Hypothesis/freeze records are committed and pin the correct packets
- Frozen bar rules (RULES_LABEL.json, RULES_GEOMETRY.json) are never regenerated
- Direction version is derived from state/evaluation.json at run time (not hardcoded)
- Instruments delegate to accepted measurement modules (REUSE-FIRST)
- Claim ceilings deny everything the direction denies
- Non-vacuity batteries are reused unchanged
- V3 measures are deterministic
- V3 end-to-end falsifies the product as expected

---

## Frozen Pin Verification

All frozen input digests re-hash byte-identically:

| Artifact | Expected SHA256 (from freeze record) | Verified |
|----------|--------------------------------------|----------|
| RULES_LABEL.json | 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608 | ✓ |
| RULES_GEOMETRY.json | a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633 | ✓ |
| VERDICT_CONTRACT.json | b9cdb89438a8d16e... | ✓ |
| Frozen retrieval spec | 187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72 | ✓ |
| V3 packet.json | 32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70 | ✓ |

---

## Orchestration Diagnosis (from v61 Operational Resume)

The prior run 39471603258 (persisted producer snapshot) was diagnosed as an **orchestration failure**, not a lane work failure:

- The producer wrote audit artifacts into the independent auditor's protected namespace (`results/audit/`, `reports/audit/`)
- The team job's "Enforce lane write scope" step correctly excluded these paths and exited 3
- The audit job was skipped; "Persist team snapshot" (if: always()) force-pushed the out-of-scope writes
- The two out-of-scope pseudo-audit files were re-homed byte-exactly into the lane namespace at `results/evaluation/orchestration_resume_39471603258/39470495546_producer_authored_audit_copy.json` and removed from the auditor namespace
- Valid work was preserved; no evidence was lost

---

## Standing Orders (Unchanged)

| Order | Status | Evidence |
|-------|--------|----------|
| DO-NOT-SERVE on packet 38839347028 | **STANDS** | LABEL_UNSOUND (5/65), GEOMETRY_UNSOUND (de 3/11, fr 4/11, it 4/11) |
| DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675 | **STANDS** | Accepted outcome-B verdict, owner_decision_required=false |
| F-3B disposition | **INTACT_NOT_REOPENED** | Restore + re-home + proof executed (run 39287274485) |
| Human gate | **NOT UNBLOCKED** | human_gate_ready=false, machine_gate_ready=false, packet_admitted=false, ready_for_owner_session=false |

---

## Next Recommendation

**CONTINUE, bounded, same question (v61).**

The evaluation lane's ordered work is discharged:
1. ✅ Repair2 chain (accepted via 39450358971)
2. ✅ Counter-emission cross-check (accepted via 39457963802)
3. ✅ V3 packet counter-authority surface falsification (this verification)
4. ✅ Minimal CA benchmark non-vacuity on V3 packet
5. ✅ Served packet retrieval/counter-authority benchmark non-vacuity

**Next same-question work:** Discharge the falsification battery on a NEW served packet when one exists (none today), or cross-check the next accepted measurement.

**Do NOT:**
- Re-dispatch a zero-delta cycle
- Re-litigate closed items (F-3B, emission charter, universal-174k benchmarks)
- Re-author audit placements in the auditor's namespace

---

## Machine Records

| Benchmark | Record Path | Report Path |
|-----------|-------------|-------------|
| counter_authority_surface_falsifier | `/tmp/verification_ca_surface.json` | (stdout) |
| minimal_ca_benchmark | `/tmp/verification_minimal_ca/local_verification_39478326004.json` | `/tmp/verification_minimal_ca_reports/RETRIEVAL_CA_BENCHMARK_local_verification_39478326004.md` |
| benchmark_retrieval_counter_authority | `/tmp/verification_ca_bench/local_verification_39478326004.json` | `/tmp/verification_ca_bench_reports/RETRIEVAL_CA_BENCHMARK_local_verification_39478326004.md` |

---

## Audit Readiness

This verification run confirms the Evaluation lane snapshot is **audit-ready**:

- ✅ All frozen benchmarks are intact and re-hash byte-identically
- ✅ Committed execution records are self-consistent and re-score byte-identically
- ✅ Every declared gate family can be falsified (falsification matrix holds)
- ✅ Cached replay cannot report a latency pass
- ✅ Gate entry-point repeat-invariance holds (run_bar_gates: 10/10 invariant)
- ✅ No network calls, no Product code imported, stdlib-only execution
- ✅ Claim ceilings honored — no overclaiming of jurist usefulness or bar meeting
- ✅ Negative results preserved as first-class evidence
- ✅ Provenance chain complete — every measurement traces to accepted frozen inputs