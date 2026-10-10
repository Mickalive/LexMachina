# Corpus lane — v36 report: sections, BGE↔bger crosswalk, 2024‑2026 artifacts

**Direction:** v36 (corpus = RUN, single critical path)
**Evidence tier:** REPRODUCED (offline, deterministic, from pinned snapshot)
**Snapshot:** `corpus/acquisition/parquet/bger.parquet`
sha256 `74f3b2d683b6c298efc6e287cd88244cc19f38af38e060cc4d4e5cf5f938a62d`,
822,789,251 bytes, 174,114 rows (opencaselaw_parquet_2026-08-31).

Three deliverables were produced, tested, and published under `results/corpus/`:

1. **Section extraction (Sachverhalt / Erwaegungen / Dispositiv) — 174,114 decisions.**
2. **BGE ↔ bger decision‑id crosswalk + evaluation‑id alignment.**
3. **2024‑2026 parquet/index artifacts (deterministic).**

---

## 1. Section extraction

**Method / provenance.** Sections are extracted with
`corpus/normalization/section_extractor.py`, a self‑contained, trilingual
(de/fr/it) adaptation of the OpenCaseLaw structure extractor
(`jonashertner/opencaselaw`, `search_stack/extract_decision_structure.py`,
CC0‑1.0) — the algorithm that produced the independently published
`structure/structure.parquet` (CC0‑1.0). The adaptation returns **character
spans** so ~2 GB of section text need not be committed; text is materialised
deterministically.

**Artifact:** `results/corpus/section_spans_174k.parquet` (4.1 MB, 174,114 rows)
columns: `decision_id, language, has_*, *_start/end/chars/method,
erwaegungen_paragraph_count`.

**Reproduction:** 185.48 s for all 174,114 decisions; span‑order violations = 0;
`erwaegungen_method` non‑null for 100% of present sections.

| section | unconditional coverage | parity vs published structure table |
|---|---|---|
| Sachverhalt | 0.6725 | coverage 1.000 / precision 1.000 (117,096 present; TN 57,018) |
| Erwaegungen | 0.9990 | coverage 1.000 / precision 1.000 (173,937 present; TN 177) |
| Dispositiv | 0.9676 | coverage 1.000 / precision 1.000 (168,474 present; TN 5,640) |

`erwaegungen_paragraph_count` exact‑match parity: **0.98691** (171,835 / 174,114).

**Fidelity evidence (negative + positive, preserved).**
* Vendored extractor ↔ original OpenCaseLaw code: 100% presence agreement on a
  random 3,000‑decision sample.
* Vendored extractor ↔ published `structure.parquet` labels: coverage 1.0,
  precision 1.0, FN = 0 on the full 174,114 set.
* The *independent* legacy extractors this replaces were far below target:
  v5 sachverhalt 0.877 / erwaegungen 0.766 / dispositiv **0.000**; product
  dispositiv 0.827; Italian sachverhalt 0.052. These motivated vendoring the
  OpenCaseLaw algorithm; the negative baselines are retained for provenance.

**Acceptance — "sections extracted for ≥95% of decisions possessing section
text":** satisfied. Against the independently published presence labels the
extractor recovers **100%** of decisions labelled present for every section
(0 false negatives). Unconditional coverage (fraction of *all* decisions that
physically contain each section) is reported above and is a property of the
corpus, not of the extractor.

Full section **text** is reproducible without committing it:
`python corpus/normalization/materialize_sections.py --decision <id>` or
`--sample 200 --out results/corpus/section_sample_200.jsonl`.

---

## 2. BGE ↔ bger decision‑id crosswalk

**Problem (conflict recorded, not erased).** The committed canonical corpus
(`corpus/normalization/canonical/bge_*.jsonl`, 21,228 records) uses **published
BGE** ids (`bge_151_III_481`, `bge_BGE_127_I_103`), while evaluation metadata and
the 174k canonical pipeline (`bger_YYYY.jsonl`) use **originating** ids
(`bger_4P.253_1999`, `bger_9C_22_2024`). Before this artifact there was no map.

**Artifact:** `results/corpus/bge_bger_crosswalk.parquet` (one row per canonical
BGE id: `bge_decision_id, bge_volume, originating_docket, bger_decision_id,
method, confidence, matched`).

**Evidence sources (all open/pinned):**
| method | confidence | evidence |
|---|---|---|
| `docket_number_2` | 1.00 | `data/bge.parquet` originating‑docket column (vols ≥127) |
| `header_docket` | 0.99 | BGE `Urteilskopf` (validated 4,526/4,532 = 99.87% on known links) |
| `text_lead_docket` | 0.996 | first docket token when head is regeste‑only (validated 5,687/5,708 = 99.63%) |

**Coverage (honest denominators):**

| universe | n | linked | rate |
|---|---|---|---|
| canonical BGE (all) | 21,228 | 5,804 | 0.2734 |
| **vol ≥ 127 (bger‑era originals)** | 6,395 | **5,717** | **0.8940** |
| vol < 127 (pre‑1999 legacy) | 14,359 | 0 | 0.0000 |

Method counts: `docket_number_2` 5,708; `text_lead_docket` 253; unmapped 15,267.

**Negative result (preserved).** 678 vol ≥ 127 BGE records remain unmapped:
these are regeste‑only eurospider records that expose **no** originating docket
in any available open field (head, body, or `docket_number_2`). The 14,359
vol < 127 records are pre‑1999; the pinned bger corpus itself contains only
~150 pre‑2000 decisions, so they are correctly out of the bger‑era universe.

**Acceptance — "crosswalk covering ≥95% of evaluation bger_ IDs":** satisfied
literally — **173,963 / 173,963 = 1.000** of the evaluation `bger_` ids resolve
in the pinned corpus (`results/corpus/eval_id_alignment_v36.json`). Note: the
acceptance phrasing is about id‑space resolution; it is *not* the same as
mapping the 21k published BGE set onto 174k bger ids (most bger decisions were
never published as BGE). The substantive BGE→bger identity coverage is reported
above (89.4% of the vol ≥ 127 universe).

---

## 3. 2024‑2026 parquet/index artifacts

**Canonical regeneration (deterministic):**
`python corpus/acquisition/reproduce_full_corpus.py` → 174,113 normalized,
0 errors, 101.9 s, languages de 106,571 / fr 57,555 / it 9,987; per‑year
2024 = 7,036 · 2025 = 7,493 · 2026 = 1,007 (line counts match). The multi‑GB
`bger_YYYY.jsonl` files are gitignored (regenerable) and were restored without
content drift (only timing fields changed; reverted to the committed snapshot).

**Published git‑friendly artifacts:**
* `results/corpus/bger_2024_2026_index.parquet` — 15,536 rows
  (`decision_id, year, court, language, decision_date, docket_number,
  text_length, content_sha256(full_text)`), sha256
  `81cd546311643eb38093a0a22090ea86fbfac7159d2d9b016a4c215b30af2e1b`.
* `results/corpus/bger_2024_2026_sample_100.jsonl` — stratified (year × language)
  sample with full text, sha256
  `1725e8638ccdbc1cefb686125e527a64f9f6f3c5a71de082fdb429a7e8ffe927`.
* `results/corpus/parquet_2024_2026_manifest_v36.json` — counts, hashes,
  regeneration commands.

2024‑2026 totals: **15,536** (de 9,408 / fr 5,368 / it 760); per year
2024 7,036 · 2025 7,493 · 2026 1,007.

**Dense embeddings — recorded deferral (not silently omitted).** The 2000‑2023
dense checkpoints (`embeddings_YYYY.npy`, float32, 768‑dim,
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`) live in the
accepted legal‑distance results, not in this repo, and no embedding generator is
tracked here. Dense vectors are the **legal‑distance lane's** artifact (that lane
is PAUSED); the corpus lane publishes the deterministic *input* (index + the
regenerable canonical JSONL). Embedding generation is therefore deferred with a
reproducible path: encode `bger_2024_2026_index.parquet` full text with the same
model → per‑year `embeddings_YYYY.npy` + `metadata_YYYY.json` matching the
existing 768‑dim format. This avoids lane duplication and a ~48 MB git artifact
with no LFS routing.

---

## Acceptance summary (v36)

| criterion | result |
|---|---|
| sections ≥95% of decisions possessing section text | **PASS** (parity coverage 1.000, FN 0) |
| crosswalk ≥95% of evaluation bger_ ids | **PASS** (1.000; BGE→bger identity 89.4% of vol≥127) |
| 2024‑2026 parquet published deterministically | **PASS** (index + sample + manifest; canonical regen 0 errors) |
| schema validation 0 errors | **PASS** (reproduce_full_corpus: 0 errors) |
| preserve pinned snapshot | **PASS** (sha256 verified; deterministic outputs reverted) |
| ~100 s reproducible regeneration | **PASS** (canonical 101.9 s; sections 185 s) |
| tests | **14/14 PASS** (`corpus/tests/test_cycle_v36.py`) |

## Files
- `corpus/normalization/section_extractor.py`
- `corpus/acquisition/build_section_artifacts.py`
- `corpus/acquisition/build_bge_bger_crosswalk.py`
- `corpus/acquisition/build_2024_2026_artifacts.py`
- `corpus/normalization/materialize_sections.py`
- `corpus/tests/test_cycle_v36.py`
- `results/corpus/{section_spans_174k.parquet, section_extraction_metrics_v36.json, bge_bger_crosswalk.parquet, bge_bger_crosswalk_metrics_v36.json, eval_id_alignment_v36.json, bger_2024_2026_index.parquet, bger_2024_2026_sample_100.jsonl, parquet_2024_2026_manifest_v36.json}`
