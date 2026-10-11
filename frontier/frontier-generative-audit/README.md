# Frontier `frontier-generative-audit` — canonical tree (charter v2, contract 2.1)

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
| OpenCode CLI, free models | default; model chosen from `state/model_health.json` | yes, live in CI (run 38176699303) |
| Local OpenAI-compatible server (Ollama/LM Studio/vLLM) | `LEX_GENAUDIT_BACKEND=openai LEX_OPENAI_BASE_URL=http://127.0.0.1:11434/v1` | documented local mode |
| Deterministic fixture | `Provider(fixture_mode=True, ...)` / `run_e2e.py --fixture` | yes, frozen suite |

Post-generation validation uses OpenCaseLaw `/api/attest` when reachable
(`LEX_OCL_ATTEST=1`), otherwise strict local bundle validation (the CI
sandbox used for this cycle has no egress to opencaselaw.org — recorded
negative result, fallback verified by tests).

## Run it

```bash
# frozen deterministic suite (23 tests)
python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py

# include the live free-model smoke test
LEX_REAL_MODEL=1 python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py

# end-to-end cached example (fixture or real)
python3 frontier/frontier-generative-audit/run_e2e.py --fixture \
    --out results/frontier/frontier-generative-audit/cached_example_fixture.json
python3 frontier/frontier-generative-audit/run_e2e.py --real --model opencode/mimo-v2.6-flash-free \
    --out results/frontier/frontier-generative-audit/cached_example_real_model.json
```

## Layout

```
frontier/frontier-generative-audit/
  generative_audit/            canonical package (provider, adversarial, models,
                               source_packing, opencaselaw, integration_contract, paths)
  run_e2e.py                   CLI orchestrator producing cached examples
  README.md                    this contract
tests/frontier/frontier-generative-audit/
  test_generative_audit_v2.py  frozen suite (acceptance 1-8)
  fixtures/sample_bundle.json  product-shaped query_result_bundle v1.0 fixture
results/frontier/frontier-generative-audit/
  acceptance_matrix.json       acceptance (1)-(8) -> evidence
  cached_example_*.json        end-to-end cached examples (fixture + live models)
```
