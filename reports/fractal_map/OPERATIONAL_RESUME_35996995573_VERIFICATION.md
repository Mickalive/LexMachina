# Operational Resume Verification — Run 35996995573

## Summary
**Lane**: fractal-map  
**Factory Direction**: v25  
**GitHub Run**: 35996995573  
**Timestamp**: 2026-09-24T12:15:00Z  
**Audit Status**: PASS  

## Verification Results
- **Tests**: 184/184 PASS (1.54s)
- **Artifacts Verified**: 944
- **Legal-Distance Modes Available**: 30 (29 available + 1 placeholder)
- **Nesting Consistency**: 1.0 (perfect) across all validated modes
- **Compressed 5-Level Ladder**: Validated for TF-IDF production modes

## Lane Deliverable Status: COMPLETE for TF-IDF Compressed Ladder

### 174k Scale — 10 Modes (2 Full + 8 Compressed)
| Mode ID | Type | Corpus Size | Resolutions |
|---------|------|-------------|-------------|
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` | Full (BEST PRODUCTION) | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_tfidf_174k` | Full | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_174k_compressed_v25` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_outcome_hybrid_0.5_174k` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `full_text_tfidf_light_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `outcome_tfidf_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `outcome_tfidf_174k_compressed_v25` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_full_text_hybrid_0.5_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_full_text_hybrid_0.7_174k_compressed` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_tfidf_174k` | Compressed | 175,440 | [0.25, 0.5, 1.0, 2.0, 3.0] |

### 21k Scale — 8 Modes (Compressed)
| Mode ID | Corpus Size | Resolutions |
|---------|-------------|-------------|
| `cited_decisions_tfidf_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_outcome_hybrid_0.5_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `cited_decisions_tfidf_outcome_hybrid_0.7_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `full_text_tfidf_light_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `outcome_tfidf_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_full_text_hybrid_0.5_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_full_text_hybrid_0.7_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |
| `regeste_tfidf_21k_compressed` | 21,228 | [0.25, 0.5, 1.0, 2.0, 3.0] |

All modes show **perfect nesting consistency (1.0)** across the compressed 5-level resolution ladder.

## Compressed Resolution Ladder Analysis
The compressed ladder `[0.25, 0.5, 1.0, 2.0, 3.0]` (dropping 0.75 and 1.5) achieves:
- **100% delta retention** across ALL 22 evaluated modes
- **Resolution reduction**: 28.57% (2 fewer levels)
- **Nesting change**: > 1e-6 for 21/22 modes (only `criticizing_alpha0.3` shows 0.0 change)

**Product Decision**: Compressed ladder accepted for production TF-IDF modes. Full 7-level ladder preserved for modes requiring it (citation role modes, dense embeddings).

## Zoom Quality Diagnostic (from run 33338598158)
Citation role views dominate zoom quality:
1. **citing_alpha0.3**: ZQ=0.5401 (rank #1)
2. **following_alpha0.3**: ZQ=0.5280 (rank #2)  
3. **criticizing_alpha0.3**: ZQ=0.4864 (rank #3)

**Tension confirmed**: Best PRODUCTION mode (`cited_decisions_tfidf_outcome_hybrid_0.5`, JP=0.7990) ranks 21st in zoom quality (ZQ=0.2798). Best FRACTAL mode (`cited_decisions_tfidf_outcome_hybrid_0.7`, JP=0.7907) ranks 20th (ZQ=0.2799).

**Multi-view design confirmed**: Citation roles for zoom navigation, outcome hybrids for flat neighborhood exploration.

## Blockers
| Blocker | Since | Required From |
|---------|-------|---------------|
| Citation role modes (citing/following/criticizing_alpha0.3) | 2026-09-24 | legal-distance 174k dense embeddings |
| Dense embedding hybrids | 2026-09-24 | legal-distance 174k dense embeddings |
| 174k metadata (branch/legal_area/chamber) | 2026-09-24 | corpus lane |

## Orchestration Failure (59th Documented Occurrence)
**Root Cause**: Supervisor dispatcher reads ephemeral `/tmp/lex_control/state/factory_direction.json` (shows `fractal-map.status=RUN`) instead of workspace `state/fractal-map.json` (shows `cycle_status=COMPLETED` for TF-IDF).

**Impact**: 59 unnecessary resume cycles dispatched, wasting compute and creating audit noise.

**Fix Required**: Factory Director must update supervisor dispatch logic to read workspace lane state, not ephemeral control plane copy.

## Evidence Tier
**ACCEPTED** — All TF-IDF compressed ladder artifacts verified, tests passing, negative results preserved.

## Next Recommendation
**BLOCKED** — Await legal-distance 174k dense embeddings. When delivered:
1. Run `build_parameterized_legal_distance_map_compressed.py` for all dense modes
2. Validate citation-role zoom quality at 174k per diagnostic thresholds
3. Implement multi-view zoom UI with citation-role views

**continue_recommended = false** — No additional same-question cycle justified. This is the 59th verification confirming stability.

## Provenance
- **Builder**: `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py`
- **Embeddings**: `results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/`
- **Metadata**: `results/fractal_map/hierarchical_map_174k/metadata_174k_bge.json` (175,440 decisions)
- **Tests**: `tests/fractal_map/test_verify.py` (184 tests)
- **Gate**: `results/fractal_map/audit/CYCLE_OPERATIONAL_RESUME_35996995573_GATE.json`

---
*This verification preserves all valid completed work. No scientific regressions detected. Lane deliverable audit-ready.*