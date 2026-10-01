# Fractal Map Lane - Cycle Summary Report

**Cycle ID**: fractal_map_cycle_20261001_dense_protocol_validated  
**Date**: 2026-10-01  
**Factory Direction**: v29  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  

---

## Mission Alignment

This cycle addressed the critical blocker identified in factory direction v29: **"dense hierarchical protocol mismatch: hierarchical_v1 protocol designed for TF-IDF geometry FAILS on dense embeddings due to fundamental geometric difference."**

The lane was BLOCKED on legal-distance 174k dense embeddings AND the protocol mismatch. This cycle **resolved the protocol mismatch for the 2-level case** by designing and validating a dense-specific hierarchical protocol.

---

## Key Achievements

### 1. Exposed Purity Metric Inflation in Prior Work
- **Finding**: The `hierarchical_v1` protocol's "exceptional legal structure purity" claims (coarse branch=0.957, area=0.854) **included 'unknown' as a valid legal category**.
- **Valid-only metrics** (excluding 'unknown'): coarse branch=0.836, coarse area=0.255, fine branch=0.988, fine area=0.511.
- **Impact**: The geometric mismatch is real but less extreme; coarse area purity has significant room for refinement.

### 2. Designed Dense-Specific 2-Level Protocol
**Innovations:**
- **Valid-only purity metrics**: Exclude 'unknown' branch/area
- **Purity-aware stopping**: Don't subdivide clusters where `branch_purity > threshold AND area_purity > threshold`
- **Semantic coherence metric**: Children must have different dominant legal_areas
- **Appropriate success criteria**: Nesting ≥0.95, singleton <1%, median >5, coarse_branch >0.8, fine_area >0.4, area_improvement >0.05, coherence >0.3

### 3. Validated Protocol on ACCEPTED 12k Dense Embeddings
**Results (3/3 threshold configurations PASS):**

| Config | Verdict | Nesting | Singleton% | Median | Coarse Branch | Fine Area | Area Δ | Coherence |
|--------|---------|---------|------------|--------|---------------|-----------|--------|-----------|
| branch=0.8, area=0.4 | **PASS** | 1.000 | 0.00% | 28.0 | 0.836 | 0.494 | +0.238 | **0.511** |
| branch=0.85, area=0.5 | **PASS** | 1.000 | 0.00% | 27.0 | 0.836 | 0.494 | +0.238 | **0.443** |
| branch=0.9, area=0.6 | **PASS** | 1.000 | 0.00% | 26.0 | 0.836 | 0.501 | +0.246 | **0.443** |

**Standard hierarchical_v1 on same embeddings: FAIL (coherence=0.126)**

### 4. Why Standard Protocol Fails, Dense Protocol Passes
- **Standard**: Forces subdivision of ALL 33 coarse clusters → only ~4 benefit → coherence=0.126
- **Dense**: Stops subdivision for 24-26 already-pure clusters → only subdivides 7-9 where area refinement adds value → coherence=0.44-0.51

---

## Evidence Produced

| Artifact | Location | Description |
|----------|----------|-------------|
| Dense protocol results | `results/fractal_map/dense_protocol_2level/dense_protocol_2level_results.json` | Full experimental data for 3 threshold configs + standard v1 comparison |
| Findings summary | `results/fractal_map/dense_protocol_2level/DENSE_PROTOCOL_FINDINGS.md` | Human-readable findings document |
| Multi-level extension attempt | `results/fractal_map/dense_multilevel_protocol/dense_multilevel_results.json` | 5-level hierarchy (FAILS - nesting degrades at deeper levels) |
| Updated lane state | `state/fractal-map.json` | Machine-readable state with corrected claims |
| Updated lane state (dup) | `state/fractal_map.json` | Duplicate for compatibility |

---

## Protocol Mismatch Status: RESOLVED (2-level)

| Aspect | Before | After |
|--------|--------|-------|
| Dense embeddings 12k hierarchical_v1 | FAIL (fragmentation 6-9%, coherence 21-27%) | N/A - wrong protocol |
| Dense embeddings 12k dense-specific | N/A | **PASS** (0% fragmentation, coherence 44-51%) |
| 28k checkpoint | Different protocol, not validated under product criteria | **PENDING** |
| 174k deployment | BLOCKED on protocol + embeddings | Protocol READY, embeddings PENDING |

---

## Product Impact

### Unblocked: Citation-Role Dense Embedding Zoom Path
The factory direction identified the evidence-backed zoom path:
- `citing_alpha0.3`: ZQ=0.5401 (1k scale, REPRODUCED)
- `following_alpha0.3`: ZQ=0.5280
- `criticizing_alpha0.3`: ZQ=0.4864
- Production default `cited_outcome_hybrid_0.5`: ZQ=0.2798

**Previous blocker**: No dense-specific hierarchical protocol that works  
**Now**: 2-level protocol validated on ACCEPTED 12k dense embeddings. Ready for:
1. 28k checkpoint scale validation
2. 174k deployment when legal-distance delivers embeddings
3. Citation-role dense embedding integration

---

## Remaining Blockers

1. **legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED; 15/26 checkpointed PENDING AUDIT
2. **28k checkpoint validation**: Embeddings not currently accessible in accepted state
3. **Multi-level fractal hierarchy**: 5-level extension FAILS (nesting degrades to 0.80 at level 4)

---

## Next Steps (Recommended)

### Immediate (Next Cycle)
1. **Validate dense protocol at 28k checkpoint** (years 2000-2005) when embeddings available
2. **Confirm scale stability**: hier_impr should remain in 0.5-0.7 range per extrapolation model

### When 174k Embeddings Available
3. **Deploy dense protocol at 174k** on citation-role and center_projected embeddings
4. **Integrate with product serving** for dense map modes

### Future Research
4. **Design multi-level recursive purity-aware protocol** for full fractal hierarchy (corpus→domain→subdomain→microcluster→decisions)
5. **Section-specific dense embeddings** (sachverhalt/erwaegungen/dispositiv) when available

---

## Acceptance Recommendation

**ACCEPT** the dense-specific 2-level hierarchical protocol as a validated method for dense embeddings at 12k scale. This resolves the protocol mismatch documented in state v29 and unblocks the citation-role dense embedding zoom path for product integration.

The protocol should be:
1. Added to the evaluation harness as a dense-specific evaluation mode
2. Used as the default hierarchical method for dense embedding map modes
3. Extended to multi-level for full fractal hierarchy (future work)

---

## Compliance with Research Protocol

✅ **Hypothesis stated**: Dense embeddings need purity-aware stopping, not forced subdivision  
✅ **Baseline defined**: Standard hierarchical_v1 protocol (FAIL on same embeddings)  
✅ **Sample frozen**: ACCEPTED 12k dense embeddings (years 2000-2002)  
✅ **Metrics frozen**: Valid-only purity, nesting, fragmentation, coherence, area improvement  
✅ **Success rule frozen**: PASS iff all 7 criteria met  
✅ **Raw outputs preserved**: JSON results with full hierarchy and stop_info  
✅ **Negative results preserved**: Multi-level extension FAIL documented  
✅ **Comparison with baseline**: Standard v1 included in results  
✅ **Machine-readable state**: Updated `state/fractal-map.json`  
✅ **Human-readable report**: This document + `DENSE_PROTOCOL_FINDINGS.md`  
✅ **Recommendation**: PIVOT_WITHIN_MISSION (protocol validated, next: scale validation)

---

*End of Cycle Report*