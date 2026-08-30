# Fractal Map Lane — Operational Resume + New Scale Evidence (Run 33317287543)

## Cycle Type
Audit resume from persisted producer snapshot of run 33317287543, PLUS new executable deliverable work that closes a gap flagged across all prior audit-resume cycles.

## Timestamp
2026-08-30T18:20:00Z

## Diagnosis of Orchestration/Validation Failure
The prior run 33317287543 did **NOT fail** — it completed with GATE PASS, wrote its CYCLE_GATE.json, OPERATIONAL_RESUME_AUDIT.md, and updated state/fractal-map.json (all git-tracked and present). The recurring "failure" across fractal-map history is the **systemic ephemeral-storage gap** (intermediate audit mirror files lost between CI invocations), now resolved: all recent CYCLE gates and resume reports are committed to the branch.

**The real validation gap this run closes:** every prior audit-resume (10+) concluded "PRODUCTIZE, BLOCKED on corpus" WITHOUT establishing that the two BEST modes' source embeddings can reproduce the map, or that any legal-distance mode has a parameterized/scalable builder. This run closes both.

## Verified State (unchanged, re-confirmed)
- **128/128 pytest tests PASS** (re-ran this session).
- All 24 map modes artifact-complete (1 placeholder by design).
- Both outcome-hybrid gates ACCEPTED tier.

## NEW Evidence (this run)

### 1. Provenance: EXACT Reproduction from Accepted Cache
The accepted 1200-decision outcome-hybrid cache, `cited_decisions_tfidf_outcome_hybrid_{0.5,0.7}.npy`, when sliced to the first 1000 rows **BEFORE clustering**, reproduces the validated 1000-decision map labels **exactly (purity=1.0)** at every resolution step (0.25→3.0), plus coarse_0.5 and hierarchical_best.

**Critical operating rule discovered:** clustering the FULL 1200 superset then taking the first 1000 rows yields only **0.88** purity. The scalable builder must slice-before-cluster.

### 2. New Parameterized Legal-Distance Builder
`fractal_map/hierarchical/build_parameterized_legal_distance_map.py` — closes the scalability gap (prior builder supported center_projected ONLY). It:
- accepts any legal-distance embedding `.npy`
- follows the slice-before-cluster provenance rule
- **byte-exactly reproduces** all 9 accepted label artifacts for both BEST modes at N=1000

### 3. Scale Extension: N=1000 → N=1200 (new, unvalidated scale)
Built both BEST modes at the full 1200-decision cache size (real, not synthetic).

| Mode | N | nesting | zoom_improvement_rate | branch_purity (mean) |
|------|---|---------|----------------------|----------------------|
| outcome_0.5 (BEST PROD) | 1000 (accepted) | 1.0 | 0.171 | — |
| outcome_0.5 | 1200 (new) | 1.0 | 0.260 | 0.506 |
| outcome_0.7 (BEST FRACTAL) | 1000 (accepted) | 1.0 | 0.234 | — |
| outcome_0.7 | 1200 (new) | 1.0 | 0.265 | 0.511 |

**Verdict: SCALE-ROBUST.** Both modes keep nesting=1.0 and zoom_improvement_rate stable-to-improved at 1200. Caveat: mode 0.7 shows some individual resolution steps with negative mean improvement (fine clusters less pure than coarse parents), unlike 0.5 which is positive at every step — suggesting 0.5 is the more robust candidate for DEFAULT at full-corpus scale.

## Recommendation: PRODUCTIZE (with new confidence)
The lane deliverable is now audit-ready with **full provenance and a scalable builder** for the two BEST modes, in addition to the verified accepted state. True 192k build remains BLOCKED on corpus lane. When corpus delivers: run the new parameterized builder on the accepted embeddings at 192k, then re-validate zoom coherence / nesting at full scale.

**Recommendation to Factory Director:** consider outcome_hybrid_0.5 as DEFAULT at scale (stronger per-step zoom robustness), retaining 0.7 as BEST-FRACTAL mode.
