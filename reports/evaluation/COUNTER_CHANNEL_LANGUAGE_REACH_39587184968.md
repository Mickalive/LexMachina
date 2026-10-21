# Counter-Channel Single-Language Reach — run 39587184968

- Schema: `lex-evaluation-counter-channel-language-reach/1`
- Direction: v61 (`state/evaluation.json` at run time)
- Engine: `evaluation/counter_channel_language_reach.py`
- Frozen input: `results/evaluation/retrieval_benchmark/39117425713.json` (accepted offline replay, audit gate PASS for run 39117425713), pinned sha256 `f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75`
- Frozen spec: `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` sha256 `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` (re-hashed after execution: MATCH)
- Combined verdict: **COUNTER_SINGLE_LANGUAGE_REACH_LOST** (exit 1)
- Elapsed: 0.039 s

## Reason

at least one frozen question loses ALL known counter reach in at least one of FR/DE/IT on the counter channel alone: ['rent-default', 'corporate-criminal-liability', 'business-judgment-rule']

## Per-question result (frozen rule)

| question | classification | fr | de | it | distinct hit sets | pooled (accepted) | pooled-only |
|---|---|---|---|---|---|---|---|
| rent-default | `REACH_LOST` | 1 | 1 | 0 | 3 | 3 | 1 |
| corporate-criminal-liability | `REACH_LOST` | 0 | 3 | 0 | 2 | 4 | 1 |
| business-judgment-rule | `REACH_LOST` | 0 | 1 | 0 | 2 | 1 | 0 |
| petty-theft-dismissal | `REACH_HELD` | 3 | 3 | 1 | 3 | 7 | 1 |

Cells are known-counter hits per language (denominator = the question's frozen known-counter set); full hit id sets and per-language evidence are in the machine record.

## Hit sets (frozen ids, per language)

### rent-default — `REACH_LOST`

- **fr** (30 counter rows, status 200): 1/9 — ['bge_BGE_117_II_415']
- **de** (30 counter rows, status 200): 1/9 — ['zh_mietgericht_MB170006-L']
- **it** (30 counter rows, status 200): 0/9 — []
- counter-channel union: 2/9
- accepted pooled gate (all channels, all languages): 3/9 (passed=True)
- pooled-only, reached by a BASELINE query but by no single-language counter query: ['gr_gerichte_PKG_2010_20']
- distinct hit sets across languages: 3
- republished accepted BASELINE per-language cells (read-only, not re-decided): de passed=None 0/0; fr passed=None 0/0; it passed=None 0/0

### corporate-criminal-liability — `REACH_LOST`

- **fr** (30 counter rows, status 200): 0/6 — []
- **de** (30 counter rows, status 200): 3/6 — ['bge_BGE_146_IV_68', 'so_gerichte_BKBES.2026.74', 'so_gerichte_STBER.2011.32']
- **it** (30 counter rows, status 200): 0/6 — []
- counter-channel union: 3/6
- accepted pooled gate (all channels, all languages): 4/6 (passed=True)
- pooled-only, reached by a BASELINE query but by no single-language counter query: ['bger_6B_7_2014']
- distinct hit sets across languages: 2
- republished accepted BASELINE per-language cells (read-only, not re-decided): de passed=True 2/2; fr passed=False 0/2; it passed=False 0/2

### business-judgment-rule — `REACH_LOST`

- **fr** (30 counter rows, status 200): 0/4 — []
- **de** (30 counter rows, status 200): 1/4 — ['zh_handelsgericht_HG120149']
- **it** (30 counter rows, status 200): 0/4 — []
- counter-channel union: 1/4
- accepted pooled gate (all channels, all languages): 1/4 (passed=True)
- pooled-only, reached by a BASELINE query but by no single-language counter query: []
- distinct hit sets across languages: 2
- republished accepted BASELINE per-language cells (read-only, not re-decided): de passed=True 2/5; fr passed=False 0/5; it passed=False 0/5

### petty-theft-dismissal — `REACH_HELD`

- **fr** (30 counter rows, status 200): 3/9 — ['bge_BGE_124_III_25', 'bge_BGE_130_III_28', 'ge_gerichte_CAPH_107_2004']
- **de** (30 counter rows, status 200): 3/9 — ['bge_BGE_121_III_467', 'bge_BGE_138_I_113', 'so_gerichte_ZZ.1990.7']
- **it** (30 counter rows, status 200): 1/9 — ['bge_BGE_130_III_28']
- counter-channel union: 6/9
- accepted pooled gate (all channels, all languages): 7/9 (passed=True)
- pooled-only, reached by a BASELINE query but by no single-language counter query: ['ar_gerichte_KG_ARGVP_2005_3462']
- distinct hit sets across languages: 3
- republished accepted BASELINE per-language cells (read-only, not re-decided): de passed=True 1/2; fr passed=False 0/2; it passed=False 0/2

## Non-vacuity controls

- **C1_unanswered_counter_query_is_NOT_MEASURED_not_a_verdict** — HOLDS: with the rent-default counter queries simulated as unanswered, the slug classifies 'NOT_MEASURED_NO_RESPONSE'; a gate that reported a product verdict from missing data would be vacuous
- **C2_counter_channel_union_is_subset_of_accepted_pooled_counter_gate** — HOLDS: the per-language cut pools a subset of the rows the accepted counter::known_counter_recall gate pools (90 counter rows of 240 total), so its hit set can never exceed the accepted gate's; a violation would mean this cut is not a faithful decomposition and must not be published
- **C3_rule_flips_HELD_when_one_language_loses_reach** — HOLDS: an ORACLE counter pool that reaches every known counter id from every language must classify REACH_HELD, and removing only the IT injection (keeping the IT query answered with an unrelated row) must flip every non-empty-set slug to REACH_LOST — otherwise the rule could not discriminate and an observed HELD would be vacuous

## Claim ceiling

This instrument establishes exactly one thing: on the ACCEPTED offline-replay retrieval record of the frozen 4-question benchmark, whether each of the FR/DE/IT counter-authority queries independently reaches at least one of the frozen known counter ids of its question. It is a retrieval-layer measurement of the FROZEN BASELINE channel, NOT a measurement of Product's shipped counter-emission stage (that is attributed by frontier-counter-label-emission, already cross-checked in run 39457963802), NOT a claim about LABEL_SOUND or GEOMETRY_SOUND (both stay REPORTED-ONLY), NOT a claim about jurist usefulness or about the map, and NOT a serve recommendation. It lifts no DO-NOT-SERVE order; packet admission stays fail-closed; human_gate_ready and owner_decision_required stay false. No universal-174k benchmark is run.

## Numeric environment

- python: 3.12.3
- platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- implementation: CPython
- numeric_scope: pure-Python set operations on committed record bytes; no BLAS/numpy reduction order is involved, so no float comparison is made

## Reproducibility

- `evaluation/counter_channel_language_reach.py` sha256 `0672c600f036a7261f2a21217440c2ef332d130ae3a8a32ed73302f576d2fc90` (pre-execution)
- `evaluation/COUNTER_CHANNEL_LANGUAGE_REACH_HYPOTHESIS_V1.json` sha256 `138ddd8eb225c9261be62520f3b35d23ce973cf8ea34aa66eed3bac7dd15d322` (pre-execution)
- `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` sha256 `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` (pre-execution)
- `results/evaluation/retrieval_benchmark/39117425713.json` sha256 `f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75` (pre-execution)
- `evaluation/retrieval_gate/gates.py` sha256 `f9bbbc7d61c927e9b687cfbcf140371d08fa6069509b0a1b6466d514ea37a6d9` (pre-execution)
- `evaluation/retrieval_gate/frozen.py` sha256 `46add5d0a537679db02d87a45ec945779c66349c75c8ed39ae59b57a482ba5c3` (pre-execution)
- `evaluation/counter_channel_language_reach.py` sha256 `0672c600f036a7261f2a21217440c2ef332d130ae3a8a32ed73302f576d2fc90` (post-execution, MATCH)
- `evaluation/COUNTER_CHANNEL_LANGUAGE_REACH_HYPOTHESIS_V1.json` sha256 `138ddd8eb225c9261be62520f3b35d23ce973cf8ea34aa66eed3bac7dd15d322` (post-execution, MATCH)
- `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` sha256 `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72` (post-execution, MATCH)
- `results/evaluation/retrieval_benchmark/39117425713.json` sha256 `f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75` (post-execution, MATCH)
- `evaluation/retrieval_gate/gates.py` sha256 `f9bbbc7d61c927e9b687cfbcf140371d08fa6069509b0a1b6466d514ea37a6d9` (post-execution, MATCH)
- `evaluation/retrieval_gate/frozen.py` sha256 `46add5d0a537679db02d87a45ec945779c66349c75c8ed39ae59b57a482ba5c3` (post-execution, MATCH)

Machine record: `results/evaluation/counter_channel_language_reach/39587184968.json`

No universal-174k benchmark was run; no frozen bar, rubric, threshold or verdict contract was read for enforcement, edited, re-derived or paraphrased.