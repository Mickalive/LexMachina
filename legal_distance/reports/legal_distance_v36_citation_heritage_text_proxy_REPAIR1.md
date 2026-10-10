# Legal-Distance — v36 Citation-Heritage Text-Only Proxy — Repair Round 1

**Lane:** legal-distance · **Direction version:** 35
**Repair run (GitHub):** 38057380692
**Cycle under repair:** 38056432926 (audit gate `REVISE`, `safe_to_integrate=false`)
**Audit evidence boundaries:** `/tmp/lex_prior_audit/results/audit/legal-distance/CYCLE_38056432926_GATE.json`
**Date:** 2026-10-10

## 1. Scope

This is repair round 1 of the rejected cycle. The audit states that **no experiment re-run is
required for D1–D3**: they are report/provenance text edits and change no committed JSON or AUC
(reference values live in `legal_distance/results/citation_heritage_text_proxy_v36/text_proxy_results.json`
→ `protocol_results.ORIG_matched_no_self` and `relation_text_baselines_results.json`). Accordingly,
**no committed result file, frozen spec, or AUC was modified**; the repair touches exactly four files:

- `legal_distance/reports/legal_distance_v36_citation_heritage_text_proxy.md` (D1, D2, D3 disclosure,
  §5 narrative, test-count updates)
- `tests/legal_distance/test_citation_heritage_text_proxy_v36.py` (audit §6 non-blocking
  recommendation: assert the full text-only family; plus new Section C guarding report↔JSON
  consistency so a D1-class drift would fail the suite)
- `state/legal-distance.json` and `legal_distance/state/legal-distance.json` (identical; repair
  `verification_runs` entry + corrected "weakest" wording in `critical_findings`)

## 2. Required-fix disposition

### D1 — §2.1 H1 table cells (numeric correction, no evidence change)

| row | audited (wrong) | repaired | committed JSON (`ORIG_matched_no_self`) | Δ vs dense (repaired) |
|---|---|---|---|---|
| `regeste_full_text_hybrid_0.5` | 0.5863 | **0.5521** | 0.552138… | −0.1668 |
| `regeste_tfidf` | 0.5759 | **0.4850** | 0.485012… | −0.2339 |

- The repaired table marks `regeste_tfidf` **(below chance)**; the corrected narrative states the
  weakest text-only baseline is `regeste_tfidf` at ~0.23 AUC below dense (the minimal
  `full_text_tfidf_light` 0.5308 sits between). A new test check
  `report_notes_regeste_tfidf_below_chance` enforces the annotation.
- Headline conclusion unaffected: best text-only `regeste_full_text_hybrid_0.7` 0.5866, margin
  +0.1324 (CI +0.0925..+0.1709); H1/H1b PASS; verdict `DENSE_TEXT_PROXY_JUSTIFIED` unchanged.
- New Section B asserts the **full text-only family** (regeste_tfidf, hybrid 0.5, hybrid 0.7,
  full_text_tfidf_light on ORIG **and** DIRECT) against the committed JSONs (audit §6).

### D2 — §2.4 heading / exact-reproduction claim

- Heading changed from "Reproduced exactly from raw inputs" to
  **"Recomputed from raw inputs (protocol reconciled, not bit-identical)"**.
- Added explicit disclosure: the frozen evaluation value `0.7296` is a with-self, mixed-relation,
  1000/2000-sampled number; **this run applied no `max_positive_sampled=1000` /
  `max_negative_sampled=2000` caps** and scored the full 1020/1020 with-self ORIG (0.7426) and the
  matched self-pair-free set (0.7159), so `0.7296` is **not exactly reproduced** here; the two
  lanes measure different protocols, not contradictory capabilities (reconciliation verdict PASS).
- New test check `report_heading_reconciled_not_identical` asserts the heading no longer
  overclaims exact reproduction and that the caps disclosure paragraph exists.

### D3 — §4 provenance disclosure of the state-file reconciliation

- §4 now states explicitly that `legal_distance/state/legal-distance.json` **was overwritten with
  (i.e. reconciled to) the canonical `state/legal-distance.json`** `verification_runs` list
  (103 entries) plus this run `38051603155` (104 entries total), replacing 5 divergent entries
  that existed only in the accepted-base duplicate:
  `38031579621, 38027372192, 38026456230, 38017387070, 38014429418` — all retained in git history;
  the reconciliation toward the canonical control-plane file (constitution §10: `main` is
  authoritative) is intended.
- New test check `report_discloses_state_reconciliation` asserts the disclosure exists in §4.

## 3. Claim-ceiling protection

- No committed JSON/AUC changed → the audited, independently reproduced numbers are byte-identical.
- State fields preserved: `evidence_tier=REPRODUCED`, `cycle_status=SUCCESSOR_RECOMMENDED`,
  `continue_recommended=false`, `accepted_run_id` unchanged; the repair entry is appended to
  `verification_runs` only (`status=REPAIR1_REPORT_NUMERIC_AND_PROVENANCE_FIX`).
- Negative results preserved verbatim in §5 (dense still loses to the citation graph on DIRECT
  0.6924 vs 0.7718; graph oracle on SHARED; the original non-comparable comparison used
  `full_text_tfidf_light` which is NOT the strongest text-only rep).
- Note: pre-registered H3 wording in §1 ("reproduce … exactly") is the frozen, pre-outcome record
  and was left untouched; §2.4 explains the reconciliation honestly.

## 4. Verification

Run `python3 tests/legal_distance/test_citation_heritage_text_proxy_v36.py` (script-style runner):

| environment | result |
|---|---|
| with citation-graph peer mount (`LEX_CITATION_GRAPH=…/citation_graph_174k.json`) | **39 passed, 0 failed, 0 skipped** |
| auditor environment (`LEX_CITATION_GRAPH=/nonexistent/graph.json`, graph-dependent jaccard/H2 checks demoted to SKIP) | **38 passed, 0 failed, 1 skipped** |

New/strengthened checks (vs 23 in the rejected snapshot):

- Section B: full text-only family asserted on ORIG and DIRECT against committed JSONs;
  `committed_text_only_family_best_is_max` cross-checks the committed text-only family best
  equals the reported 0.5866.
- Section C (report-parsing, all values against committed JSONs to 4dp): H1 table, H1b table
  (DIRECT), margin cells, §2.4 heading, caps disclosure, H3 table, §4 state-reconciliation
  disclosure, below-chance annotation.

Validation was performed **after** all report/state edits were finalized (outcome-free evaluation
was already claimed in the original cycle; repair edits are documentation, verified post-edit).

## 5. Files changed

| file | change |
|---|---|
| `legal_distance/reports/legal_distance_v36_citation_heritage_text_proxy.md` | D1/D2/D3 fixes, §5 wording, header + §4 test counts (39/38+1) |
| `tests/legal_distance/test_citation_heritage_text_proxy_v36.py` | full-family Section B + Section C report↔JSON guards (39 checks) |
| `state/legal-distance.json` | repair `verification_runs` entry, WEAKEST wording fix, tests field |
| `legal_distance/state/legal-distance.json` | byte-identical copy of the above |