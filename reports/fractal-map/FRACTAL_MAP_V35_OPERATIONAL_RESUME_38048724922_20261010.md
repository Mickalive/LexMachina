# Fractal-Map Operational Resume — Run 38048724922 (Direction v35)

- Lane: `fractal-map`
- Factory direction: v35
- Resumed from: persisted producer snapshot of GitHub run **38048724922** (team branch `cycle/core/fractal-map/38048724922/team`, commit `dcf5505e`)
- Report date: 2026-10-10
- Scope: diagnose the run's orchestration/validation failure, complete the frozen falsification experiment (R3), determine the status of the accepted 0.906–0.930 headline, and make the snapshot audit-ready.

## 1. Orchestration failure diagnosis (run 38048724922)

The run's team step persisted partially completed falsification work but failed before completion; no `/audit` branch was ever created for the run, so no audit/gate ran.

Work actually persisted by the run (all claim-bearing, all intact, sha256-verified):
- `results/fractal_map/tfidf_hierarchy_agreement_v1/` — `EVAL_SPEC_FROZEN.json` (+ `.sha256` `7d290f6bc…6c4a3`), `agreement_results.json` (verdict `INCONCLUSIVE_POSITIVE_CONTROL_FAILED`: positive control ARI 0.00033 < 0.05).
- `results/fractal_map/tfidf_hierarchy_reconciliation_v1/` — `RECON_SPEC_FROZEN.json` (+ `.sha256` `7b57b9e4…b33ad`), `reconciliation_results.json` (R1/R2 partial; **`R3_pending: true`**; 2 of 3 text modes errored with "missing decision_clusters.json").

Work that never happened: R3, state update, report, audit branch. Root orchestration causes:
1. The reconciliation harness could not measure the two `regeste_full_text_hybrid_0.5/0.7` product modes because **no product artifacts exist** for them under `results/fractal_map/product_integration_174k/` → R1 incomplete.
2. R3 (the decisive source-isolation run) was never executed → the "discrepancy" was left unresolved.
3. No state/report emission and no audit branch ⇒ the run's gate could not pass.

Prior cycle context: cycle 38047784693 was audited BLOCKED (`results/audit/fractal-map/CYCLE_38047784693_GATE.json`; report `reports/audit/fractal-map/CYCLE_38047784693.md`) with instructions to stop zero-delta cycles and fix the blocker question-hash writer/reader mismatch on `main`.

## 2. The falsification work — completed this resume

All metrics, configs and decision rules below were frozen **before** any computation in the parent run (spec IDs and sha256s above) and were not modified afterwards.

### R1 — metric reconciliation on PRODUCT artifacts (historical, completed)
- `full_text_tfidf_light` product coarse `accepted_purity_unweighted` = **0.3554** (weighted 0.3452) vs accepted headline **0.93** → gap 0.524, far above the pre-registered 0.20 threshold. Pre-registered gap recorded in `reconciliation_results.json`: 0.5239.
- `regeste_full_text_hybrid_0.5/0.7`: no product artifacts exist → the product literally cannot serve the accepted claim.
- Harness recorded `R1_provenance_mismatch_confirmed=False` only because ≥2 of 3 modes could not be measured; semantically the mismatch is confirmed on all 3/3 grounds (2 absent, 1 grossly mismatched).

### R2 — permutation null (historical, completed)
- `full_text_tfidf_light` product labels are **at chance**: observed weighted purity 0.3452 == null mean 0.3452 (std 4.1e-05, z=0.38, p_emp=0.23); NMI_area 0.0135 vs null ~0.0045 (z=2.33, p=0.097).
- Production default mode (`cited_decisions_tfidf_outcome_hybrid_0.5_174k`): weighted 0.3588 vs null 0.3452 → z=329, i.e. technically **above chance** (harness `r2_default_purity_weighted_at_chance=False`) but with near-zero macro structure (ARI_branch 0.0072, NMI_area 0.0333).
- `R2_product_agreement_weak_but_above_chance=True` (historical harness) — correct framing: the product join retains only a faint residual signal.

### R3 — source isolation (completed this resume; `eval_r3_source_isolation_v1.py`, frozen v29 pipeline on evaluation-v25 embeddings)
| mode | accepted headline | R3 reproduced | fine n_clusters | ARI_branch | NMI_area |
|---|---|---|---|---|---|
| full_text_tfidf_light | 0.93 | **0.93007** (bit-exact) | 365 (bit-exact) | 0.0429 | 0.5737 |
| regeste_full_text_hybrid_0.5 | 0.906 | **0.90567** (bit-exact) | 1101 | 0.0441 | 0.5597 |
| regeste_full_text_hybrid_0.7 | 0.909 | **0.90889** (bit-exact) | 1316 | 0.0469 | 0.5550 |

R3 reproduces the accepted headline **bit-for-bit** on the evaluation embeddings with the frozen pipeline.

### Verdicts under the frozen rules (`r3_source_isolation_verdict_v1.json`)
- **`R1_provenance_mismatch_confirmed`: TRUE** — product artifacts cannot serve the accepted claim (2 absent, 1 at 0.355 vs 0.93).
- **`R2_product_agreement_at_chance`: FALSE by the letter** (default mode is 329σ above its shuffled null), **but** the full_text mode is exactly at chance and the default mode's macro-alignment is destroyed (NMI_area 0.033 vs 0.574 truth).
- **`R3_source_driven`: TRUE** — accepted purity ≥ 0.85 reproduced on all 3 text modes on evaluation embeddings while product < 0.60 or absent; R3 ARI_branch < 0.10 (0.043–0.047) ⇒ micro-pure / macro-unaligned on the branch axis.
- **Falsification clause: PARTIALLY triggered, but as a scientific characterization, NOT as falsification of the headline.** R3 eval-embedding hierarchies are micro-coherent (purity 0.906–0.930) and keep strong legal_area structure (NMI_area 0.555–0.574, ~40× the product artifacts' 0.013–0.033) but do not recapture the coarse 5-class human **branch** axis (ARI_branch ~0.04). That is expected for content/thematic clustering; the accepted claims stand, provenance-specific.

## 3. Root cause of the discrepancy — product join/alignment defect

The product artifacts' labels are **scrambled relative to decision ids**:

- Accepted verdicts (`hierarchical_v1_174k_tfidf/*.json`) were computed by `fractal_map/evaluation/run_hierarchical_v1_174k_tfidf.py` on the **eval-aligned v25 suite embeddings** (`/tmp/lex_accepted/evaluation/.../v25_174k_formal_suite/embeddings/*.npy`, 173963 rows in eval-metadata order). For that suite, row space == id space ⇒ truthful.
- Product artifacts (`product_integration_174k/*`) were built by `fractal_map/experiments/build_production_modes_product_integration_174k.py` from the **175440-row product embedding matrix** (`hierarchical_map_174k/legal_tfidf_embeddings/*.npy`, corpus-jsonl row order) with `embeddings[:173963]` positional truncation **and no row-order verification**, then keyed `decision_clusters[metadata[i].id] = labels[i]`.
- New pre-registered join probe (`fractal_map/eval_product_join_alignment_probe_v1.py` → `results/fractal_map/diagnostics/product_integration_174k_join_probe_v1.json`): for all 3 text modes, **diagonal-is-best = 0.0%** (2000-row sample, seed 0), best-match cosine 0.836–0.899, median |best−idx| = 1150, 96.8% of rows displaced >1000 rows ⇒ the product row order ≠ eval-metadata order. The product id→cluster mapping is therefore effectively a random join (which is exactly what R1/R2 observe: purity at/near chance).
- Prior lane evidence already flagged this: census/review run 36035695081 (`legal_distance_modes/alignment_probe_v26.json`: candidate agreement 0.426 vs ~1.0 expected, verdict REJECTED; `duplicate_id_count 1003, CORRUPTED` in cluster metadata) and `zoom_quality_174k_all_modes_v26.py` (174k build placeholder-keyed, separately BLOCKED).

**Defect class:** data-integrity / join-alignment defect in the product artifacts — **not** a scientific falsification of the accepted embedding-based claim.

## 4. Blocker raised

`BLOCKER_PRODUCT_JOIN_ALIGNMENT_V1` (severity high, scope corpus+fractal-map): rebuild `product_integration_174k` artifacts from eval-aligned embeddings (or regenerate product embeddings in metadata order) and re-run the join probe (expect diag_is_best ~1.0) before any product promotion. The historical (scrambled) artifacts are preserved untouched; a corrected rebuild must land in a new path (e.g. `product_integration_174k_aligned_v1`) per the constitution's no-overwrite rule. Also note `regeste_full_text_hybrid_0.5/0.7` product artifacts were never built at all.

## 5. Product capability conclusion for direction v35

- **Accepted headline status: CONFIRMED, provenance-specific.** TF-IDF hierarchical fine purity 0.906–0.930 is real and deterministic on the evaluation-v25 embeddings (R3 bit-exact reproduction), and these are the embeddings the product should serve.
- **Scientific characterization:** TF-IDF hierarchies are micro-coherent and area-informative (NMI_area 0.56–0.57) but do not recover the coarse 5-class branch axis (ARI_branch 0.04) — consistent with content/thematic clustering. The map is a faithful geometric structure, not a branch taxonomy.
- **Product blocker:** current `product_integration_174k` artifacts join scrambled (at-chance purity); downstream consumers must not trust their decision→cluster assignments until rebuild + probe verification.

## 6. Preservation & audit-readiness

- No historical claim-bearing file was modified: `reconciliation_results.json`, `agreement_results.json`, `EVAL_SPEC_FROZEN.json`, `RECON_SPEC_FROZEN.json`, all `hierarchical_v1_174k_tfidf/*.json`, all product/hierarchical artifacts — untouched.
- New files this resume: `r3_source_isolation_results.json` (+ `r3_labels/`), `r3_source_isolation_verdict_v1.json`, `fractal_map/eval_product_join_alignment_probe_v1.py`, `results/fractal_map/diagnostics/product_integration_174k_join_probe_v1.json`, this report, and the `state/fractal-map.json` operational-resume record.

## 7. Next steps
1. Corpus/product lane: rebuild product artifacts from eval-aligned embeddings (new path), re-run join probe → expect diag_is_best ≈ 1.0 and purity ≈ 0.91–0.93.
2. Build the two missing regeste hybrid product modes.
3. Re-run the reconciliation harness on the corrected artifacts to close R1/R2 with evidence rather than absence.
4. Update `main` blocker-hash writer/reader to the same canonical format (prior audit requirement).