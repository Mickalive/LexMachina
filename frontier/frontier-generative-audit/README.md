# Frontier `frontier-generative-audit` — canonical tree (charter v2, contract 2.2)

Provider-agnostic, **source-grounded legal answer generation** plus an
**independent counter-authority / adversarial pass**, constrained to the
retrieved OpenCaseLaw decision IDs of a `query_result_bundle`.

This directory is the CANONICAL deliverable of the team. The repository-root
`generative_audit/` package is the frozen artifact of accepted cycle
38172462365 and stays only as provenance — product must copy/adapt **this**
tree.

## One-call integration contract (product lane)

```python
import sys
sys.path.insert(0, "frontier/frontier-generative-audit")   # this package

from generative_audit.integration_contract import run_generative_audit

audited_bundle = run_generative_audit(query_result_bundle_dict)
```

Input: the product's accepted `query_result_bundle` v1.0 dict
(`product/query/bundle.py`: `bundle_version, query, query_variants, answer,
decisions, clusters, relations, provenance`; each decision carrying
`decision_id, court, language, rank, score, provenance, snippet, cluster_id,
x, y, counter_status, canonical_url, citation`).

Output: a **new** dict of the same shape (input untouched) with

| Field | Change |
|---|---|
| `answer` | replaced: `prose`, `statements`, `cited_decision_ids`, `method="generative_audit_llm_v2"`, `model` |
| `decisions[*].counter_status` | `cited` / `supporting-candidate` / `candidate-limiting` / `candidate-contrary` / `none` |
| `decisions[*].counter_evidence` | evidence span for the counter classification |
| `decisions[*].counter_uncertainty` | float in [0,1] |
| `decisions[*].counter_reason`, `counter_confidence` | present when the adversarial pass produced the finding |
| `provenance.generative_audit` | contract version, provider model, citation-validation report, adversarial info, status summary |

Guarantees enforced programmatically:

1. every `answer.cited_decision_ids` entry is a retrieved bundle decision ID
   (unknown IDs are rejected **and redacted** from the surfaced prose);
2. every `counter_status` comes from the merged status model
   `supporting | limiting | contrary_or_exception | unclassified` with
   uncertainty + evidence references;
3. a decision that is *cited but limited/contrary* keeps a visible
   `candidate-limiting` / `candidate-contrary` status (the UI hides only
   `none`/`cited`, so counter-authorities stay discoverable);
4. output stays JSON-serializable and passes the product's own
   `validate_bundle()` key rules.

## Finer-grained seams

```python
from generative_audit.source_packing import from_product_bundle, DecisionBundle
from generative_audit.provider import Provider
from generative_audit.adversarial import AdversarialPass
from generative_audit.integration_contract import package_answer, apply_to_product_bundle

bundle  = from_product_bundle(product_bundle)            # adapter
result  = Provider(fixture_mode=False).generate(bundle)  # sourced answer (citations constrained)
findings, info = AdversarialPass(bundle, result.answer).run_with_info()  # independent pass
package = package_answer(result, findings, bundle)       # merged statuses
audited = apply_to_product_bundle(product_bundle, package, findings)
```

## Development providers (no owner-provisioned cost)

| Backend | How | Verified |
|---|---|---|
| OpenCode CLI, free models | default; model chosen from `state/model_health.json` | yes, live in CI runs 38176699303 / 38184472515 (`nemotron-3-ultra-free`, `mimo-v2.6-flash-free`) |
| Local OpenAI-compatible server (Ollama/LM Studio/vLLM) | `LEX_GENAUDIT_BACKEND=openai LEX_OPENAI_BASE_URL=http://127.0.0.1:11434/v1` | documented local mode |
| Deterministic fixture | `Provider(fixture_mode=True, ...)` / `run_e2e.py --fixture` | yes, frozen suite |

Post-generation validation uses OpenCaseLaw `/api/attest` and
`/api/decisions/{id}` on the documented live host
**`https://mcp.opencaselaw.ch/api`** when reachable (`LEX_OCL_ATTEST=1` /
`run_e2e.py --attestation`), otherwise strict local bundle validation.
Correction of the earlier cycle's recorded negative: `opencaselaw.org/api/attest`
was the *wrong host* (TLS failure) and a GET against a POST-only route; the
real host is reachable from CI — verified live in runs 38181577763 and
38184472515 (`results/frontier/frontier-generative-audit/ocl_live_probe_run38184472515.json`,
`cached_example_ocl_attested_*_run3818*.json`, all 6 bundle citations
live-verified as decision records). Attestation verdicts are sound: HTTP-200
error bodies, empty/mismatched payloads and non-2xx are **unverified**
(regression-tested against the live `{"error": "Provide draft_text to audit."}` body).

Adversarial `evidence_refs` are source-checked verbatim (unicode-normalised)
against each cited decision's retrieved text before they can reach
`decisions[*].counter_evidence`; unverifiable quotes are rejected and the
finding is downgraded (uncertainty ≥ 0.95) but kept visible.

## Run it

```bash
# frozen deterministic suite (29 tests)
python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py

# include the live free-model smoke test and live OpenCaseLaw probes
LEX_REAL_MODEL=1 LEX_LIVE_OCL=1 \
  python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py

# end-to-end cached example (fixture or real)
python3 frontier/frontier-generative-audit/run_e2e.py --fixture \
    --out results/frontier/frontier-generative-audit/cached_example_fixture.json
python3 frontier/frontier-generative-audit/run_e2e.py --real --model opencode/mimo-v2.6-flash-free \
    --out results/frontier/frontier-generative-audit/cached_example_real_model.json

# end-to-end on a real OpenCaseLaw-derived bundle with live attestation
python3 frontier/frontier-generative-audit/run_e2e.py --real \
    --model opencode/mimo-v2.6-flash-free \
    --bundle tests/frontier/frontier-generative-audit/fixtures/real_ocl_bundle.json \
    --attestation \
    --out results/frontier/frontier-generative-audit/cached_example_ocl_attested.json

# live host/method probe (search, decision existence, integrity, attest, verify-claim)
python3 frontier/frontier-generative-audit/probe_ocl.py \
    --out results/frontier/frontier-generative-audit/ocl_live_probe.json

# deterministic cycle finisher (suites + fixture e2e, emits the per-run
# acceptance matrix). Add --live for the free-model smoke, live OCL probe and
# attested end-to-end. Publishing evidence must never depend on a long-lived
# agent session — run 38193076995 died before publishing and had to be resumed.
python3 frontier/frontier-generative-audit/verify_cycle.py --run-id <RUN_ID>
LEX_REAL_MODEL=1 LEX_LIVE_OCL=1 \
python3 frontier/frontier-generative-audit/verify_cycle.py --run-id <RUN_ID> --live
```

## Layout

```
frontier/frontier-generative-audit/
  generative_audit/            canonical package (provider, adversarial, models,
                               source_packing, opencaselaw, integration_contract, paths)
  run_e2e.py                   CLI orchestrator producing cached examples
  verify_cycle.py              deterministic cycle finisher -> per-run acceptance matrix
  probe_ocl.py                 live OpenCaseLaw host/method probe
  README.md                    this contract
tests/frontier/frontier-generative-audit/
  test_generative_audit_v2.py  frozen suite (acceptance 1-8)
  fixtures/sample_bundle.json  product-shaped query_result_bundle v1.0 fixture
results/frontier/frontier-generative-audit/
  acceptance_matrix.json       acceptance (1)-(8) -> evidence (latest verified run)
  acceptance_matrix_run*.json  immutable per-run matrices
  cached_example_*.json        end-to-end cached examples (fixture + live models)
```
