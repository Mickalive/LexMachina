# Evaluation Lane — v25 174k v17b Provenance Gate (run 36035803010)

- **Cycle**: GitHub run `36035803010`
- **Branch**: `lab/evaluation` (accepted base, HEAD `e75b2df7` = accept cycle 36028392571)
- **Date**: 2026-09-24
- **Direction version**: 25
- **Evidence tier**: REPRODUCED (frozen-spec gate executed; verdict matches frozen expectation exactly; negative controls pass; snapshot conformance 8/8 + provenance gate 4/4 under pytest)

---

## 1. Why this cycle exists

Audit `CYCLE_36028392571` (accepted at `e75b2df7`) verified the v25 174k formal-suite snapshot (producer run `36013963912`) and **finding 4** recommended:

> extend `tests/evaluation/test_v25_174k_suite_snapshot.py` with a per-rep v17b provenance check (recompute per-rep metrics from saved embeddings and assert correspondence), so this copy-defect class is caught mechanically by the conformance gate in future cycles.

The copy-defect class: in producer run `36013963912`, the v17b result files for `regeste_full_text_hybrid_0.5/0.7` were **byte-identical copies** of `full_text_tfidf_light.json` (modulo the representation name). The auditor discovered it by file-level comparison, not by any mechanical gate — a conformance gap. This cycle closes that gap with a frozen provenance gate **and** executes it.

Map to factory direction v25 (evaluation question): the three sub-questions (12-benchmark suite at 174k, citation-heritage validation, v17b 174k generalization) were executed and audited in the prior cycles; this cycle is the recommended conformance-hardening follow-up that protects those accepted measurements from the discovered provenance-failure class. No frozen threshold, sample, benchmark or historical artifact is touched.

---

## 2. Frozen gate spec (no-tuning rule)

- **Spec**: `evaluation/experiments/v25_174k_suite/provenance_gate_spec_v1.json` — `protocol_id: eval_v25_v17b_provenance_gate_v1`, status FROZEN, frozen at 2026-09-24T18:05:00Z **before** any gate execution.
- **Implementation**: `tests/evaluation/test_v25_174k_v17b_provenance.py`, which imports the **frozen** benchmark functions from `run_v25_174k_suite.py` (`bm_hierarchy`, `bm_zoom`, `bm_legal_area`, `normalize_labels`, `load_metadata`) — no reimplementation.
- **Sample**: frozen `hierarchy_subsample_15000_seed42.npy` (15,000 rows, branch-stratified among known-`legal_area` rows).
- **Embeddings**: the snapshot-verified 173,963×128 float32 `.npy` files.
- **Reference sets**: recorded (`results/evaluation/v25_174k_v17b/`, producer 36013963912) and authoritative recheck (`results/evaluation/v25_174k_audit_fixes_36028392571/v17b_recheck/`).

Rules (all frozen before execution):

| Rule | Severity | Requirement |
|---|---|---|
| P1 own-embedding correspondence | HARD FAIL | recompute 14 v17b metric values per rep from the rep's **own** saved embedding on the frozen subsample; `max_abs_delta <= 0.02` vs each reference file |
| P2 file-identity ⇒ on-sample embedding identity | HARD FAIL | identical-content files must have `max_abs_diff <= 1e-4` on the subsample (copied files are the defect signal) |
| P3 degeneracy probe | WARN only | for identical-file pairs, probe 10,000 **regeste-active** rows (seed 42); `probe_diff > 1e-3` ⇒ WARN "measurement provenance must be documented" |
| P4 status consistency | HARD FAIL | recomputed PASS/FAIL/SKIP statuses must equal the reference file statuses |

Negative controls (frozen): **NC_swap** — for every ordered non-degenerate pair of reps, writing donor's recorded content into victim's slot must FAIL P1 (0 unexpected passes); **NC_fileid** — crafting identical files over different on-sample embeddings must FAIL P2 everywhere expected.

The full spec (rules, tolerances, frozen expectations, success rule, no-tuning rule) is committed at `evaluation/experiments/v25_174k_suite/provenance_gate_spec_v1.json` and is immutable for this protocol id.

---

## 3. Implementation note (one mechanical bug fixed before execution)

The first execution attempt crashed in the P1 comparison loop:

```
ValueError: setting an array element with a sequence ... detected shape was (2,)
```

Cause: `recompute_rep` returned `extract_metric_vector(out)`, which is a **2-tuple** `(vector, statuses)`; the caller unpacked it as `(out, vec)` making `vec` a tuple. This is an implementation defect in the gate harness, **not** a rule/tolerance/sample adjustment. Fixed by returning the vector element only (`extract_metric_vector(out)[0]`). No frozen rule, tolerance, sample, probe or threshold was changed before, during or after execution (spec file byte-unchanged from 17:47 creation through the run).

---

## 4. Gate execution

Environment: numpy 2.5.3 / scikit-learn 1.9.1 (identical to the auditor's verified environment), OMP threads 1, `Pool(4)` for the 8 per-rep recomputations. Runtime 79.3s (cheap enough to run as a standard conformance gate every cycle).

Outputs (raw, preserved):
- `results/evaluation/v25_174k_provenance_gate_36035803010/gate_results.json`
- `results/evaluation/v25_174k_provenance_gate_36035803010/per_rep_recomputation.json`

### 4.1 Verdict

```
P1 PASS | P2 PASS | P4 PASS | P3_warnings 6 | NC_swap PASS | NC_fileid PASS | GATE_OVERALL PASS
```

### 4.2 P1 — own-embedding correspondence (tolerance 0.02)

| Representation | recorded maxΔ | recheck maxΔ |
|---|---|---|
| cited_decisions_tfidf | 0.000000 | 0.001867 |
| outcome_tfidf | 0.000000 | 0.000000 |
| regeste_tfidf | 0.000000 | 0.000000 |
| full_text_tfidf_light | 0.000000 | 0.000000 |
| cited_outcome_hybrid_0.5 | 0.001586 | 0.001586 |
| cited_outcome_hybrid_0.7 | 0.000000 | 0.000000 |
| regeste_full_text_hybrid_0.5 | 0.000000 | 0.000000 |
| regeste_full_text_hybrid_0.7 | 0.000000 | 0.000000 |

Six reps recompute **exactly** (Δ=0) against both reference sets; the two sub-0.002 deviations are the environmental KMeans/BLAS drift the auditor already measured (cited_decisions recheck differs on hierarchy metrics only, verdicts unchanged; `CYCLE_36028392571` §3.6). The recorded `cited_decisions_tfidf` file — whose provenance the auditor had to defend — is reproduced **exactly** (Δ=0.000000).

### 4.3 P2/P3 — identical-file group and degeneracy probe

Exactly one identical-content group exists on **both** reference sets: `{full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7}` — precisely the frozen expectation.

- On-sample max diff: 5.96e-08 and 2.98e-07 (float32 rounding; P2 PASS, ⇒ files identical only where embeddings are identical).
- Degeneracy mechanism verified: **all 15,000** frozen subsample rows are regeste-zero rows (15,000/15,000), so the regeste hybrids numerically equal `full_text_tfidf_light` on this sample. The copied files' values coincide with correct measurements; the defect is provenance-only.
- P3 probe on 10,000 regeste-active rows (seed 42): probe diffs **0.8506 / 1.1541 / 0.3056** for the three triple pairs on both reference sets ⇒ 6 WARNs, all confined to the degenerate triple, exactly as the frozen expectation predicted. The probe demonstrates the copies WOULD be materially wrong (diff up to 1.15) for any benchmark whose sample included regeste-active rows — the reason the copy-defect class matters mechanically.

### 4.4 P4 — status consistency

Zero status mismatches for all 8 reps × both reference sets (hierarchy FAIL, zoom PASS, legal_area FAIL everywhere — unchanged verdicts under normalized labels).

### 4.5 Negative controls

- **NC_swap** (56 ordered non-degenerate victim←donor cells): all cells FAIL P1 as required; **0 unexpected passes**. Swaps within the degenerate triple are the only cells allowed through (numeric invisibility, documented degeneracy).
- **NC_fileid**: every non-identical file pair has on-sample embedding diff ≥ 0.434, so crafted identical files always FAIL P2; **0 unexpected passes**.

The negative controls prove the gate is not vacuously green: it detects the exact corruption class it was built for, and only the documented degenerate-triple cells escape detection (by construction).

---

## 5. Conformance integration (audit finding 4, literal)

`tests/evaluation/test_v25_174k_suite_snapshot.py` now carries **test_08_v17b_provenance_gate**, delegating to the single-source gate module (module-level `_GATE_CACHE` ensures the ~80s recomputation runs once per pytest session). The conformance suite therefore catches the producer-run copy-defect class mechanically in every future cycle.

Pytest result (this cycle, full v25 conformance):

```
tests/evaluation/test_v25_174k_suite_snapshot.py ..........         8 passed
tests/evaluation/test_v25_174k_v17b_provenance.py ....              4 passed
12 passed in 83.28s
```

---

## 6. Audit-fix documentation corrections (findings 1–3, additive)

Per audit `CYCLE_36028392571` §5, applied **additively** (historical files untouched) in
`results/evaluation/v25_174k_audit_fixes_36028392571/documentation_corrections_36035803010.json`:

1. **Narrative overreach corrected**: the run's "the other six reps are independently re-confirmed here" is restated — 5 of the other six exact; `cited_decisions_tfidf` recheck differs ≤0.2% on hierarchy metrics only (env drift), verdicts unchanged; the recorded file is reproduced exactly by this gate (Δ=0).
2. **Defect-framing degeneracy noted**: the copied h5/h7 files are invalid as *provenance* but numerically coincide with correct measurements because all 15,000 frozen subsample rows are regeste-zero → material impact nil; defect stands recorded as an integrity violation.
3. **NMI caveats named per rep** (normalized vs raw, authoritative recheck values): outcome_tfidf −13.1%/−13.1%; full_text (and h5/h7 by degeneracy) −27.6%/−24.3%; cited_outcome_0.5 −9.6%/−14.5%; cited_outcome_0.7 −10.8%/−10.7%; cited_decisions −5.4%/−8.2%; regeste n/a (raw NMI = 0). Purity-only 10% rule passes all 8 reps (all four purity ratios ≥ 1.0, table in the correction record); any future v17b prose must carry the NMI caveats.

---

## 7. Product/evidence impact

- The accepted v25 174k snapshot measurements (`results/evaluation/v25_174k_v17b/` + superseding `v17b_recheck/`) are **provenance-gated**: future corruption of the v17b measurement files now fails conformance mechanically (P1/P2/P4 + NCs).
- No new product-capability claim, no frozen-benchmark change, no threshold change, no representation change. The regeste-family negatives (citation-heritage unmeasurable pool on regeste-zero rows; degenerate zero-vector v17b behavior) remain honest negatives.
- v17b 174k generalization verdict unchanged: label normalization improves all four purity metrics for all 8 reps (ratios ≥ 1.0); NMI caveats disclosed.

---

## 8. State recommendations (mandatory fields)

- `lane`: evaluation
- `direction_version`: 25
- `evidence_tier`: REPRODUCED
- `cycle_status`: COMPLETED
- `continue_recommended`: **false** — the provenance-gate hardening of the accepted 174k v17b measurements is complete; no additional same-question evaluation cycle is justified on the 8 TF-IDF-family representations.
- `accepted_run_id`: `eval_v25_174k_formal_suite_36013963912` (unchanged — the accepted 174k snapshot this gate protects)
- `next_recommendation`: The **remaining** v25 174k suite work is the execution of the 12-benchmark suite + DEFAULT-map-mode gate + citation-heritage on the **dense** 174k representations (center_projected_64/768, linear_metric, mahalanobis, hybrid_stabilized, hybrid_v2) — BLOCKED on legal-distance lane delivery to accepted state (not observed in the mounted accepted peer state as of this cycle). Jurist human study remains externally blocked (5–10 Swiss jurists by the repository owner). When dense 174k representations land in accepted state, evaluation resumes the frozen suite on them (provenance gate will run as part of every v25 conformance).