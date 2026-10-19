# Integration Contract: frontier-query-concept-recall

**Component**: Deterministic multilingual query-expansion layer for concept recall
**Charter**: frontier-query-concept-recall v1
**Status**: Candidate for Product adoption

---

## 1. Drop-in Path

The expansion layer integrates at **one precise seam** in the product pipeline:

**File**: `product/query/pipeline.py`
**Function**: `run_query_initial()` (line ~534)
**Integration Point**: Before `_retrieve()` call, replace the query variant construction.

Current code (lines 539-545):
```python
query = (query or "").strip()
if not query:
    raise ValueError("empty query")
top_n = max(MIN_LIVE_RESULTS, min(MAX_RESULTS, int(top_n))) if retrieval_mode != "fixture" else max(40, min(200, int(top_n)))
t_upstream_start = time.time()
candidate = _retrieve(query, top_n, mode=retrieval_mode, hydrate_top=0)
```

**Proposed change**: Insert expansion layer between query validation and `_retrieve()`:

```python
query = (query or "").strip()
if not query:
    raise ValueError("empty query")

# --- EXPANSION LAYER INTEGRATION ---
from frontier.frontier_query_concept_recall.expansion import (
    ExpansionConfig, build_variants, search_variants, QueryVariant
)
# Infer query language from question_id or detect
query_language = _infer_query_language(query)  # Product owns this
config = ExpansionConfig()
variants = build_variants(query, query_language, config)
query_variants = [v.text for v in search_variants(variants)]
# Store variants in provenance for audit
expansion_provenance = {
    "component": "frontier-query-concept-recall/v1",
    "variants": [v.to_dict() for v in variants],
    "query_language": query_language,
}
# --- END EXPANSION LAYER ---

top_n = max(MIN_LIVE_RESULTS, min(MAX_RESULTS, int(top_n))) if retrieval_mode != "fixture" else max(40, min(200, int(top_n)))
t_upstream_start = time.time()
candidate = _retrieve(query, top_n, mode=retrieval_mode, hydrate_top=0,
                      query_variants=query_variants)  # Adapter must accept variants
```

**Adapter Change Required**: The `ocl_adapter.build_candidate_bundle()` must accept an optional `query_variants` parameter and execute each variant as an independent search (already supported via the adapter's channel architecture).

---

## 2. Extra Query Variants Emitted

The layer adds **three new variant kinds** to the existing `query_variants` list:

| Kind | Purpose | Provenance |
|------|---------|------------|
| `cross_language_concept` | Corpus-derived multilingual concept expansions for languages the query was NOT asked in | `corpus_derived_concept_variants + statute_aliases` |
| `language_filter` (extended) | Server-side OpenCaseLaw language filters for non-query languages | `server-side OpenCaseLaw language={lang} filter` |
| `legal_concept` / `statute_alias` | Existing doctrine/statute aliases (preserved from ocl_adapter.expansion) | `ocl_adapter.expansion:versioned_legal_aliases` |

**Example** for `de-kapitalverletzung` (German query):
- Original: `"Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung..."`
- Cross-language concept: Adds FR/IT equivalents like `"responsabilité de l'entreprise"`, `"responsabilità dell'impresa"`, plus statute aliases `Art. 102 CP`, `Art. 102 StGB`
- Language filters: Adds `language=fr` and `language=it` server-side filters on the original query

**All variants are additive** — the original query is always preserved as the first variant.

---

## 3. Provenance Entries Added

Every bundle produced with the layer includes this provenance block:

```json
{
  "provenance": {
    "expansion_layer": {
      "component": "frontier-query-concept-recall/v1",
      "charter_version": 1,
      "query_language": "de",
      "variants_emitted": 7,
      "variant_breakdown": {
        "original": 1,
        "lexicon_expansion": 1,
        "statute_alias": 2,
        "legal_concept": 1,
        "cross_language_concept": 1,
        "language_filter": 2
      },
      "cross_language_terms_added": [
        "responsabilité de l'entreprise",
        "responsabilità dell'impresa",
        "Art. 102 CP",
        "Art. 102 StGB",
        "Unternehmensstrafbarkeit Art. 102 StGB"
      ],
      "terms_added_from": "corpus_derived_concept_variants + statute_aliases",
      "deterministic": true,
      "model_calls": 0,
      "network_calls": 0
    },
    "retrieval": {
      "adapter": "ocl_adapter/v2",
      "candidate_bundle_version": "...",
      "n_candidates": 187,
      "candidate_languages": {"de": 98, "fr": 54, "it": 35},
      "candidate_channels": {"search": 120, "language_filter": 45, "leading_case": 12, "citation": 10},
      "dedupe": {"n_before": 214, "n_after": 187, "n_merged": 27}
    }
  }
}
```

The `query_variants` field in the bundle (required by `QUERY_MAP_MVP.md` §7) contains the full text of each search variant executed.

---

## 4. Runtime Cost

| Metric | Value | Notes |
|--------|-------|-------|
| **Model calls** | 0 | Purely deterministic lookup |
| **Network calls** | 0 (in fixture mode) | In live mode: +2-4 OpenCaseLaw searches (FR/IT language filters + cross-language concept) |
| **Latency added** | < 50ms local | Hash computation + variant construction |
| **Upstream latency** | +2×30s max | Two additional language-filter searches (FR, IT) in parallel |
| **Cache impact** | New cache keys | Config-shaped keys include variant list; no collision with existing cache |

**Budget compliance**: The frozen retrieval benchmark allows 24 searches in < 240s. The layer adds at most 2 searches (FR + IT language filters) per question, well within budget. Cross-language concept variant is a single additional search.

---

## 5. Disclosure Text Per Outcome

### If Outcome A (Component Promotes)
> "The query-expansion layer recovered **[N]** previously missing core concepts and improved cross-language authority recall on **[M]** of **[K]** frozen FR/IT cells. The expansion is deterministic, corpus-derived, and adds no model calls. The map now includes decisions addressing the question's own core concepts in DE, FR, and IT."

### If Outcome B (Bounded Negative)
> "No in-budget deterministic expansion recovered the missing concepts or authority IDs. The unrecoverable cells are: **[exact list]**. The measured lexical cause is: **[exact cause, e.g., 'corpus lacks FR/IT decisions discussing Kapitalverletzung as a doctrine term']**. This closes the recall half; the admission-disclosure half remains with Product."

### Claim Ceiling (VERBATIM, IN FORCE)
> **No artifact may assert that:**
> - a map helps a jurist
> - any authority is absent from the corpus
> - any frozen bar is met or moved
> - any packet is fit to serve
>
> **Usefulness remains the human product gate's question and admission remains fail-closed.**
> Product decides adoption or decline under factory-wide requirement 21 and records the decision; silent non-consumption is not an outcome this contract permits of itself.

---

## 6. Contract Invariants (What Must Not Change)

The expansion layer **must not** alter:
- [ ] Deduplication behaviour (`merge_duplicate_identities`)
- [ ] Provenance channel fields (`channels` on decisions)
- [ ] Any `query_result_bundle` contract field (§7, §10A of `QUERY_MAP_MVP.md`)
- [ ] Decision ranking (expansion happens BEFORE retrieval; rerank is unchanged)
- [ ] Counter-authority classification (`apply_anchor_labels`)
- [ ] Geometry/variant selection (`selected_variant()`)
- [ ] Admission gates (`gate_admissibility.py`)

The layer **only** adds query variants before retrieval and records them in provenance.

---

## 7. Acceptance Test Results (To Be Filled After Harness Run)

| Test | Baseline | Candidate | Pass/Fail |
|------|----------|-----------|-----------|
| (1) Freeze-first by re-hash | ✓ | ✓ | |
| (2) Reproduce accepted baseline | N/A | measured | |
| (3) Runnable offline harness | N/A | `python -m frontier_query_concept_recall.cli --all --out ...` | |
| (4) Head-to-head identical inputs | measured | measured | |
| (5) Non-vacuity proven | N/A | controls run | |
| (6) No regression frozen gates | N/A | verified | |
| (7) Regression suite pinned | N/A | documented | |
| (8) Integration contract | N/A | this document | |
| (9) Zero out-of-scope writes | N/A | verified | |

---

## 8. Product Decision Required

Per factory-wide requirement 21, **Product must explicitly record adoption or decline** of this component. The decision and rationale must be recorded in the product lane's cycle record. Silent non-consumption is not a permitted outcome.

**Adoption Checklist for Product:**
- [ ] Integration tested in `product/query/pipeline.py` with live retrieval
- [ ] Cache keys verified compatible (no silent cache misses)
- [ ] Bundle validation passes (`validate_bundle()`)
- [ ] Provenance fields render correctly in UI
- [ ] Human product gate evaluation scheduled

---

*Generated by frontier-query-concept-recall charter v1*
*Integration contract version 1.0*