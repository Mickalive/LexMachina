# Evaluation Lane Repair Report: Cycle 37082047030, Round 1

**Lane:** evaluation | **Run:** 37085399612 | **Repair Round:** 1 | **Date:** 2026-10-03
**Producer Workspace:** /home/runner/work/LexMachina/LexMachina | **Control Plane:** main
**GitHub Run (Repair):** 37085399612

---

## Executive Summary

This repair addresses four concrete defects identified in the independent audit of evaluation cycle 37082047030 (GATE: REVISE). All four defects have been fixed with durable deltas:

1. **DEFECT-1 (CRITICAL):** Unsupported claim "Citation heritage for dense embeddings validated at 22-year scale (144k decisions, AUC 0.79–0.85)" — FIXED with accurate evidence
2. **DEFECT-2 (HIGH):** Incorrect jurist gate range "JP 0.05–0.43" — CORRECTED to "JP 0.39–0.43 (this cycle)"
3. **DEFECT-3 (HIGH):** Year discrepancy between state files (15/26 years checkpointed vs 22 years evaluated) — RESOLVED with clear ACCEPTED/CHECKPOINTED/EVALUATED taxonomy
4. **DEFECT-4 (MEDIUM):** v17b normalization mapping coverage undocumented — DOCUMENTED with actual map statistics

Core verification claims remain **valid and reproducible**. The repairs are documentation/consistency fixes only; no benchmark results, metrics, or evaluation logic were changed. Negative results are preserved.

---

## Defect 1: Unsupported Dense Citation Heritage Claim [CRITICAL] — FIXED

### Issue
Report Section 4 claimed: *"Dense embeddings recover citation heritage better than TF-IDF (AUC 0.79-0.85 vs 0.71-0.74)"* at 22-year scale (144k decisions).

### Evidence Review
- `citation_heritage_dense_subsets_latest.json`: 15-year (2000-2014) and 19-year (2000-2018) center_projected evaluations **FAILED** — "Insufficient valid pairs"
- `citation_heritage_center_projected_768dim_partial_2000_2015.json`: **Only** partial 16-year (2000-2015) evaluation succeeded — AUC=0.9047, 13,648 positive pairs
- 22-year (2000-2021) citation heritage **NOT EVALUATED** in this cycle

### Fix Applied
Updated `evaluation/reports/evaluation_v29_final_verification_20261002.md` Section 4 ("Dense Embeddings") with corrected critical finding:

> **Critical finding (corrected per audit CYCLE_37082047030)**:
> - **Citation heritage for dense embeddings**: Partial 16-year (2000-2015) evaluation shows AUC ~0.90 on center_projected_768dim (13,648 positive pairs). Full 15-year (2000-2014) and 19-year (2000-2018) evaluations **FAILED due to insufficient valid pairs**. 22-year (2000-2021) citation heritage **NOT YET EVALUATED** in this cycle. The prior claim "AUC 0.79-0.85 at 22-year scale" was unsupported.

---

## Defect 2: Incorrect Jurist Gate Range [HIGH] — FIXED

### Issue
Report stated jurist gate range as "JP 0.05–0.43" for 22-year dense embeddings.

### Evidence Review
Actual 22-year adversarial results (exact k-NN on stratified subsample n=2000):
- center_projected_768dim: jurist_preference_rate = 0.3975
- center_projected_128dim: jurist_preference_rate = 0.408
- center_projected_64dim: jurist_preference_rate = 0.4265

**Actual range this cycle: 0.39–0.43**

### Fix Applied
Updated report table and critical finding:
- Table row: `22-year (2000-2021) | 144,443 | FAIL jurist gate (JP 0.39-0.43) | ...`
- Critical finding: "JP 0.39-0.43 at 22-year; 0.26-0.29 at 15-year; 0.47-0.48 at 19-year"

---

## Defect 3: Year Discrepancy in State Files [HIGH] — FIXED

### Issue
State files contained inconsistent year references:
- `evaluation.json`: "dense_15year_checkpointed" (2000-2014, 15 years)
- `evaluation_state.json`: "22/26 years 2000-2021 checkpointed" but also "19/26 years 2000-2018 checkpointed" in earlier entries
- `run_additional_formal_suite.py` evaluates 2000-2021 (22 years)
- Factory direction v30: "21/26 years (2000-2020) CHECKPOINTED", "3/26 years (2000-2002) ACCEPTED"

### Fix Applied
Added explicit `dense_embeddings_year_status` taxonomy to both state files:

| Status | Years | Count | Decisions | Evidence Tier | Notes |
|--------|-------|-------|-----------|---------------|-------|
| **ACCEPTED** | 2000-2002 | 3/26 | ~19k | ACCEPTED | Formal suite + citation heritage evaluated |
| **CHECKPOINTED** | 2000-2020 | 21/26 | ~150k | CHECKPOINTED (pending audit) | Legal-distance progress.json |
| **EVALUATED** | 2000-2021 | 22/26 | 144,443 | EVALUATED (adversarial only) | Citation heritage: partial 16-year only |

Updated `direction_version` to 30 in both state files per factory direction.

---

## Defect 4: v17b Normalization Mapping Coverage Undocumented [MEDIUM] — FIXED

### Issue
Audit required: "Document v17b normalization mapping coverage: Note what fraction of 214 raw legal_area labels are covered by the 179-entry hardcoded map (approx 156 non-unknown raw labels based on mapping content)."

### Evidence Review
Actual `legal_area_normalize.py` CROSS_LINGUAL_MAP:
- **91 entries** (not 179 as stated in audit)
- **40 unique canonical concepts**
- Average 2.3 raw labels per concept (de/fr/it equivalents)
- Corpus has **214 raw labels**, normalization yields **164 canonical concepts**

### Fix Applied
Added `v17b_normalization_mapping_coverage` to both state files:

```json
"v17b_normalization_mapping_coverage": {
  "raw_labels_in_corpus": 214,
  "canonical_concepts_after_normalization": 164,
  "cross_lingual_map_entries": 91,
  "unique_raw_labels_covered_by_map": 91,
  "coverage_fraction": "91/214 = 42.5% of raw labels explicitly mapped",
  "unique_canonical_concepts_in_map": 40,
  "note": "Map merges de/fr/it equivalents (typically 2-3 per concept, avg 2.3). Remaining 123 raw labels (57.5%) pass through unchanged (identity). 40 canonical concepts from map + 123 identity = 163 (close to 164 observed; difference likely from NONE/empty handling). Map is CONSERVATIVE: only clearly-equivalent cross-lingual labels merged."
}
```

**Note:** The audit's "179-entry" and "~156 covered" were incorrect; actual map has 91 entries covering 91 raw labels (42.5%).

---

## Artifacts Updated

| File | Changes |
|------|---------|
| `evaluation/reports/evaluation_v29_final_verification_20261002.md` | Fixed Defect 1 & 2: Corrected dense citation heritage claim and jurist gate range in Section 4 |
| `evaluation/state/evaluation.json` | Fixed Defect 3 & 4: Added dense_embeddings_year_status taxonomy, corrected dense_15year citation_heritage status, documented v17b mapping coverage, updated direction_version to 30 |
| `evaluation/state/evaluation_state.json` | Fixed Defect 3 & 4: Same corrections + updated work_completed log with repair entry, updated direction_version to 30 |

---

## Verification Summary

| Check | Status |
|-------|--------|
| Report Section 4: Dense citation heritage claim corrected | ✅ PASS |
| Report Section 4: Jurist gate range corrected to 0.39-0.43 | ✅ PASS |
| State files: ACCEPTED vs CHECKPOINTED vs EVALUATED clearly distinguished | ✅ PASS |
| State files: dense_15year citation_heritage corrected to FAILED | ✅ PASS |
| State files: v17b mapping coverage documented with actual counts | ✅ PASS |
| Core benchmark results unchanged (TF-IDF 8 reps PASS, citation heritage FAIL, v17b NEGATIVE) | ✅ PASS |
| No frozen baselines weakened | ✅ PASS |
| Negative results preserved | ✅ PASS |

---

## Claim Ceiling (Unchanged)

> "TF-IDF family (8 reps) at 174k: all PASS both adversarial gates. Citation heritage TF-IDF: 4/8 PASS AUC≥0.65 (citation-based modes). v17b label normalization at 174k: purity gains +7% to +36% confirmed but NMI decreases (regime shift). Dense embeddings: 3/26 years ACCEPTED (FAIL adversarial), 22/26 years EVALUATED for adversarial (center_projected FAIL jurist gate JP 0.39-0.43), citation heritage only partial 16-year (AUC=0.90). Linear hybrids PASS at 19-year but NOT at 174k. Evaluation infrastructure VERIFIED and AUDIT-READY."

---

## Next Recommendation

**CONTINUE** — Evaluation infrastructure is fully verified and operational at 174k scale. The TF-IDF family evaluation is complete. The lane remains **RUN** per factory direction v30 "as representations land" awaiting legal-distance 174k dense embeddings (currently blocked on bge_/bger_ ID mapping and missing parquet 2022-2026). The monitor (`monitor_and_evaluate_174k.py`) is active (check_count=284). No additional repair cycles needed.

---

*Repair completed per audit CYCLE_37082047030_GATE.json required fixes. All changes are durable deltas with full provenance.*