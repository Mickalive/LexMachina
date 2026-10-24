# Frozen Retrieval / Counter-Authority Benchmark — live_test

- **Schema**: `lex-retrieval-benchmark/1`
- **Direction**: v49 (frozen retrieval benchmark spec sha 187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72)
- **Engine**: `python -m evaluation.retrieval_gate.run_retrieval_benchmark` (pure standard library, no product code)
- **Endpoint**: `https://mcp.opencaselaw.ch/api/decisions` (OpenCaseLaw public API)
- **Combined verdict**: **FAIL** (exit 1)
- **Falsification proven**: **YES** — 11 measurable gates fail on live OpenCaseLaw searches
- **Elapsed**: 225.95 s (live pass), 0.079 s (cached replay)

---

## Summary

The frozen retrieval benchmark executes 24 independent OpenCaseLaw searches (4 questions × 3 languages × {baseline, counter} channels) and evaluates them against 40 executable gates. **11 gates fail**, demonstrating that plain OpenCaseLaw retrieval does **not** reach frozen controlling authorities in French and Italian for 3 of 4 questions, fails to surface limiting-marker evidence for corporate-criminal-liability, and returns duplicate decision IDs in every query response.

This is the smallest executable retrieval/counter-authority benchmark that can falsify the query-map product. It uses only the public OpenCaseLaw API, no product machinery, and its query set, thresholds and success rules were frozen **before** any frozen query was executed (FREEZE_RECORD.json asserts `frozen_before_execution: true`).

---

## Per-Question Results

### rent-default ⚠️ FAIL (5/9 measurable gates pass)
| Gate | Result | Detail |
|------|--------|--------|
| `authority::baseline_recall::rent-default` | NOT MEASURABLE | Frozen reality benchmark carries no controlling-authority set for this question |
| `authority::baseline_lang_recall::rent-default::fr` | NOT MEASURABLE | Same |
| `authority::baseline_lang_recall::rent-default::de` | NOT MEASURABLE | Same |
| `authority::baseline_lang_recall::rent-default::it` | NOT MEASURABLE | Same |
| `norm::retrievable::rent-default` | **PASS** | 3+ rows contain norm token `257d` |
| `counter::known_counter_recall::rent-default` | **PASS** | 3 of 9 known counter IDs retrieved (BGE 117 II 415, GR PGK 2010 20, ZH MB170006-L) |
| `counter::limiting_marker_verified::rent-default` | **PASS** | 3 counter rows with both `257d` and limitation tokens (`abus`, `exception`) |
| `source::rows_valid::rent-default` | **PASS** | All 240 rows valid (HTTPS mcp.opencaselaw.ch, language in {de,fr,it}) |
| `duplicate::unique_ids::rent-default` | **FAIL** | 8 duplicate alnum-core pairs in FR baseline (e.g. `ge_gerichte_C_6552_2022` / `ge_gerichte_ACJC_1511_2022` share core `gegerichteacjc15112022`) |

### corporate-criminal-liability ❌ FAIL (5/9 gates pass)
| Gate | Result | Detail |
|------|--------|--------|
| `authority::baseline_lang_recall::corporate-criminal-liability::fr` | **FAIL** | **0 of 2 frozen authorities** (BGE 142 IV 333, BGer 6B 124 2016) in FR top-50 |
| `authority::baseline_lang_recall::corporate-criminal-liability::de` | **PASS** | Both authorities retrieved in DE |
| `authority::baseline_lang_recall::corporate-criminal-liability::it` | **FAIL** | **0 of 2 frozen authorities** in IT top-50 |
| `authority::baseline_recall::corporate-criminal-liability` | **PASS** | Union of FR/DE/IT retrieves both (via DE) |
| `norm::retrievable::corporate-criminal-liability` | **PASS** | 3+ rows with `art. 102` |
| `counter::known_counter_recall::corporate-criminal-liability` | **PASS** | 4 of 6 known counter IDs retrieved |
| `counter::limiting_marker_verified::corporate-criminal-liability` | **FAIL** | **0 of 90 counter rows** contain both `art. 102` AND a limitation token (`ausnahme`, `eccezione`, `grenze`, etc.) |
| `source::rows_valid::corporate-criminal-liability` | **PASS** | All 240 rows valid |
| `duplicate::unique_ids::corporate-criminal-liability` | **FAIL** | 8 duplicate pairs in FR baseline (e.g. GE court `P_17078_2019` / `ACPR_74_2021`) |

### business-judgment-rule ❌ FAIL (6/9 gates pass)
| Gate | Result | Detail |
|------|--------|--------|
| `authority::baseline_lang_recall::business-judgment-rule::fr` | **FAIL** | **0 of 5 frozen authorities** in FR top-50 |
| `authority::baseline_lang_recall::business-judgment-rule::de` | **PASS** | 2 of 5 retrieved (BGer 4A 219 2015, 4A 603 2014) |
| `authority::baseline_lang_recall::business-judgment-rule::it` | **FAIL** | **0 of 5 frozen authorities** in IT top-50 |
| `authority::baseline_recall::business-judgment-rule` | **PASS** | Union retrieves 2 (via DE) |
| `norm::retrievable::business-judgment-rule` | **PASS** | 3+ rows with `business judgment rule` / `bjr` |
| `counter::known_counter_recall::business-judgment-rule` | **PASS** | 1 of 4 known counter IDs retrieved (ZH HG120149) |
| `counter::limiting_marker_verified::business-judgment-rule` | **PASS** | 1 counter row with `business judgment rule` + `pflichtwidrig` |
| `source::rows_valid::business-judgment-rule` | **PASS** | All 240 rows valid |
| `duplicate::unique_ids::business-judgment-rule` | **FAIL** | 8 duplicate pairs in FR baseline (GE court ATA/A duplicates) |

### petty-theft-dismissal ❌ FAIL (6/9 gates pass)
| Gate | Result | Detail |
|------|--------|--------|
| `authority::baseline_lang_recall::petty-theft-dismissal::fr` | **FAIL** | **0 of 2 frozen authorities** (BGer 4A 177 2017, 4A 228 2015) in FR top-50 |
| `authority::baseline_lang_recall::petty-theft-dismissal::de` | **PASS** | 1 of 2 retrieved (BGer 4A 177 2017) |
| `authority::baseline_lang_recall::petty-theft-dismissal::it` | **FAIL** | **0 of 2 frozen authorities** in IT top-50 |
| `authority::baseline_recall::petty-theft-dismissal` | **PASS** | Union retrieves 1 (via DE) |
| `norm::retrievable::petty-theft-dismissal` | **PASS** | 3+ rows with `art. 337` |
| `counter::known_counter_recall::petty-theft-dismissal` | **PASS** | 7 of 9 known counter IDs retrieved |
| `counter::limiting_marker_verified::petty-theft-dismissal` | **PASS** | 1 counter row with `art. 337` + `proportion` |
| `source::rows_valid::petty-theft-dismissal` | **PASS** | All 240 rows valid |
| `duplicate::unique_ids::petty-theft-dismissal` | **FAIL** | 8 duplicate pairs in FR baseline (GE court CAPH/C duplicates) |

---

## Global Gates

| Gate | Result | Detail |
|------|--------|--------|
| `transport::all_queries_ok` | **PASS** | 24/24 searches HTTP 200 |
| `latency::search_under_budget` | **PASS** | Worst single search 17.95 s < 30 s budget |
| `latency::full_pass_under_budget` | **PASS** | Full live pass 225.95 s < 240 s budget |
| `reproducible::cached_second_pass_identical` | **PASS** | 24/24 queries byte-identical raw SHA256 and ordered ID list on offline replay |

---

## Key Findings

### 1. Cross-Language Authority Recall Failure (6 gates)
**French and Italian baseline searches fail to retrieve frozen controlling authorities** for 3 of 4 questions:
- **corporate-criminal-liability**: 0/2 authorities in FR, 0/2 in IT (DE retrieves both)
- **business-judgment-rule**: 0/5 in FR, 0/5 in IT (DE retrieves 2/5)
- **petty-theft-dismissal**: 0/2 in FR, 0/2 in IT (DE retrieves 1/2)

The union (FR/DE/IT) passes for all three because German searches succeed, but **per-language gates fail**. This means a jurist searching only in French or Italian would miss controlling authority.

### 2. Counter-Channel Limiting Marker Failure (1 gate)
**corporate-criminal-liability counter channel**: 90 rows returned, **zero** contain both the norm token `art. 102` AND any limitation token (`ausnahme`, `eccezione`, `grenze`, `limite`, `einschrankung`, etc.). The counter query formulation does not surface decisions discussing exceptions/limits to Art. 102 StGB.

### 3. Systematic Duplicate Decision IDs (4 gates)
**All 4 questions** show duplicate alnum-core IDs within single query responses. OpenCaseLaw returns both the court-specific ID (e.g. `ge_gerichte_C_6552_2022`) and the canonical appeal ID (e.g. `ge_gerichte_ACJC_1511_2022`) for the same decision. The frozen benchmark's `alnum_core` normalization correctly identifies these as the same authority. This is a **source-side deduplication issue**, not a product defect, but it inflates result counts and affects downstream clustering.

---

## Claim Ceiling

This benchmark measures **retrieval reachability, source validity, duplicate suppression, cross-language robustness, counter reachability, latency and cached reproducibility** of independent OpenCaseLaw searches for frozen questions.

It **cannot** show that the visual map is useful to a jurist, and it **never** re-classifies a decision as supporting/contrary. A FAIL on authority recall means the product's query-map pipeline starts from an incomplete evidence base for FR/IT researchers.

---

## Machine Record

`results/evaluation/retrieval_benchmark/live_test.json`

## Reproduction

```bash
# Live run (requires network, ~226s)
python -m evaluation.retrieval_gate.run_retrieval_benchmark --run-id live_test --cache-dir results/evaluation/retrieval_benchmark/cache

# Offline rescore (no network, deterministic)
python -m evaluation.retrieval_gate.run_retrieval_benchmark --rescore results/evaluation/retrieval_benchmark/live_test.json
```

The offline rescore produces **byte-identical verdict** (verified by `test_verdict_byte_identical_across_hash_seeds`).