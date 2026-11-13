# Product counter-signal layer on the current accepted head — run 43333717014 (v68)

- **Verdict: `PRODUCT_COUNTER_SIGNAL_LAYER_FALSIFIED_ON_CACHED_SURFACE` (exit 1)** — the shipped `adversarial_retrieval/3` layer reaches **0 of 14** frozen known-counter authorities on the offline cached regeste surface.
- Product mount head: **`7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`** (accept product cycle 40284658455; `results/audit/product/CYCLE_40284658455_GATE.json` gate=PASS, safe_to_integrate=true, required_fixes=[]).
- Instrument: `evaluation/product_counter_surface_benchmark.py` (sha256 `9f145f94…`, **bytes unchanged**), executed through the thin run-scoped wrapper `evaluation/product_counter_surface_benchmark_43333717014.py`.
- Direction: v68. `network_calls = 0`; 24/24 cached FR/DE/IT × baseline/counter envelopes replayed offline. Controls **7/7 pass**; validity gates G6/G7 pass.
- Freeze-first: hypothesis + freeze committed at `be80440d` (rev 1) and `db34afd3` (rev 2, frozen-cache provenance) **before** the claim-bearing run. No gate, metric, population or success rule differs from accepted hypothesis `3c57196a…`; the reuse is proved by a canonical-JSON equality assertion at freeze time.
  - `evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_43333717014_HYPOTHESIS_V1.json` sha256 `99420a0b88b93c5319c257ce5ade606c0717a3a2136df2649e226e03cae7fdc8`
  - `evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_43333717014_FREEZE_V1.json` sha256 `ebde44c6cb50d85e41ca81d41b08b8804b23fb32fb3c1e284843d001bc264f2d`

## 1. Why this is not zero-delta

The prior accepted measurement of this instrument is run 39838415410 at product head `fe219a19…`. Since that freeze, three of the four pinned product files are byte-identical:

| product file | 39838415410 | 43333717014 | delta |
|---|---|---|---|
| `product/query/adversarial_retrieval.py` | `9764a37e…` | `9764a37e…` | none |
| `product/query/retrieval.py` | `30ad4190…` | `30ad4190…` | none |
| `product/query/query_texts.py` | `5af67e8e…` | `5af67e8e…` | none |
| `product/query/answer.py` | `acbc1614…` | `474448ed…` | **changed** |

`answer.build_answer` supplies the deterministic extractive-answer topic proxy that the classifier consumes, so the measured surface can change. This run measures the current shipped bytes, not a cached earlier head.

## 2. Frozen sample was restored, not weakened

The repository's live 24-envelope retrieval cache had drifted: **all 24** envelope body hashes differ from the accepted run's fingerprint (the cache was rewritten in commit `05238b36`, cycle 40111496300). A first execution on the drifted live cache produced `ENVIRONMENT_OR_CONTROL_FAILURE` (C2/G7 fail; pool ±1: rent-default 222 vs 223, petty-theft 206 vs 205). That attempt is **preserved** at `results/evaluation/product_counter_surface_benchmark/43333717014.json`; no product claim is made from it.

The claim-bearing run restores the accepted sample bytes from commit `d1de037b` (parent of the cache rewrite) and verifies **24/24** files against the 39838415410 fingerprint before execution. C2 and G7 then pass with pool parity **223/218/221/205** — the accepted counts, not re-derived ones. This is a provenance repair of a drifted input, not a relaxation of any control.

## 3. Result (frozen gates, unchanged)

| gate | role | result |
|---|---|---|
| G1 offline signal on every question | falsifier | **pass** — 4 / 8 / 2 / 2 signals |
| **G2 signal reaches a known counter authority** | **primary falsifier** | **FAIL — 0 of 14 reached known rows signalled** |
| **G5 not worse than the marker rule on known rows** | **falsifier** | **FAIL — product 0 vs marker rule 1** |
| G3 hydrated sensitivity | diagnostic | 7 of 12 hydrated reached rows signalled |
| G4 hydration surface available | non-vacuity guard | pass — 12 of 14 reached rows hydrated (coverage 0.8571) |
| G6 every signal has verbatim evidence | validity | pass |
| G7 pool provenance / duplicate-free | validity | pass |

Per question (reached known authorities / signalled / hydrated / hydrated-signalled):

| question | pool | product signals | reached known | **signalled** | hydrated | hydrated signalled |
|---|---|---|---|---|---|---|
| rent-default | 223 | 4 | 3 of 9 | **0** | 2 | 1 |
| corporate-criminal-liability | 218 | 8 | 4 of 6 | **0** | 4 | 2 |
| business-judgment-rule | 221 | 2 | 1 of 4 | **0** | 1 | 1 |
| petty-theft-dismissal | 205 | 2 | 6 of 9 | **0** | 5 | 3 |

The failure is not vacuous: the product *does* emit signals on every question (G1), and it *does* reach 14 known authorities through retrieval. It simply emits **no** counter signal for any of them on the primary offline surface.

Diagnosis of all 14 reached known rows:

- **0/14** contain a product marker hit in the primary regeste text.
- **13/14** contain neither a product marker nor a frozen limitation token (`no_product_marker_and_no_frozen_limitation_token`).
- **1/14** contains a frozen limitation token (`billigkeit`, `treu und glauben`) but the product marker lexicon misses it (`product_marker_lexicon_misses_frozen_limitation_token`).

Hydration is reported separately and is not a product pass: the product query cache grew from 609 files / 145 full-text docs at the prior freeze to **1018 / 320**, so hydrated sensitivity rose from 3/5 to **7/12**. Five reached known rows still emit no signal even when full text is available, and 2 of 14 reached rows have no full text at all. Live top-12 hydration selection is not simulated.

## 4. Head-drift finding

The primary surface numbers are **identical** to accepted run 39838415410: 16 offline product signals, 14 reached known rows, **0 signalled**, 0 optimistic signalled, marker rule 1. The `answer.py` change therefore **does not rescue** the counter-signal layer on the current accepted head. The larger product cache improves only the diagnostic hydration leg. This is a confirmation on new bytes, not a second, different defect.

## 5. Ordered work status (v68)

- **Item (1), bypass-clause correction:** discharged by accepted runs 40113448025 / 40144816305; report-only, not re-derived.
- **Item (2), conditional comparable re-measure:** **`NOT_YET_DISCRIMINATING`** — see `results/evaluation/v68_item2_family_gate/43333717014.json`.
  - All **50/50** bundles already measured by accepted run 40258497460 are present in the current product mount and **byte-identical**; the product's family claim is its own earlier run 40257275384, so a re-measure is zero-delta.
  - The named frozen family is 11 offline/rent-default + 4 server/served. Current fixed-path multiplicity is 18/10/9/9/3, so `server/served` is 3 vs 4 and member-for-member matching is capped at **14/15** under the frozen role rule. No synthetic stand-in is substituted.
- **Item (3), standing falsification:** unchanged; the benchmark of record is not re-run.
- **Item (4), gate-fix disclosure:** report-only; no fix is re-litigated here.
- **Item (5), no same-question re-derivation:** honoured. No frozen benchmark, D2 profile or bypass diagnosis was re-derived; no universal-174k benchmark was run.

## 6. What this run does NOT claim

It does not measure live generative answer quality, the later independent LLM counter reviewer (the sole writer of user-visible `counter_status`), live top-12 hydration selection, legal correctness of the frozen `known_counter_ids`, or any universal-174k population. It issues no serve verdict, lifts no DO-NOT-SERVE order and admits no packet. The producer-authored gate is not an independent audit; the cycle remains `PENDING_INDEPENDENT_AUDIT`.

## 7. Regression-test status (disclosed, not papered over)

`pytest` is absent in this image (`ModuleNotFoundError`). Under a stdlib shim that provides only `pytest.raises`/`mark`, `tests/evaluation/test_product_counter_surface_benchmark.py` is **4/6 pass, 2 fail**:

- FAIL `test_cached_sample_pool_parity_and_known_counter_reach`
- FAIL `test_frozen_gate_contract_is_complete_and_nonvacuous`

Root cause is the same live-cache drift as §2: the tests read the *live* cache and assert the pre-drift accepted cardinalities `[223, 218, 221, 205]` and G7; the live cache yields `[222, 218, 221, 206]` and G7 false. The failures reproduce on the untouched accepted test **without** the new wrapper; they are not caused by this cycle. Record: `results/evaluation/counter_signal_head_drift_43333717014/regression_shim.json`.

The accepted test was **not edited**. Relaxing its pool assertions would weaken the frozen sample check; the correct repair is to pin the test's cache input to the accepted bytes, which is a separate, explicit decision because the live cache is a new sample used by later accepted cycles.

## 8. Reproduce

```bash
# restore the frozen 24-envelope sample (24/24 sha-checked against 39838415410)
python3 - <<'PY'
import json, subprocess, hashlib
from pathlib import Path
fp=json.load(open('results/evaluation/product_counter_surface_benchmark/39838415410.json'))['cache']['fingerprint']
dest=Path('/tmp/lex_v68_frozen_cache')
for rel,want in fp.items():
    blob=subprocess.check_output(['git','show',f'd1de037bd35a89aa75b31516aac828ebd4f3e5dd:results/evaluation/retrieval_benchmark/cache/{rel}'])
    p=dest/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(blob)
    assert hashlib.sha256(blob).hexdigest()==want
PY
python3 -m evaluation.product_counter_surface_benchmark_43333717014 \
  --product-root /tmp/lex_accepted/product \
  --run-id 43333717014-frozen-cache \
  --cache-dir /tmp/lex_v68_frozen_cache
python3 evaluation/v68_item2_family_gate.py --run-id 43333717014
```
