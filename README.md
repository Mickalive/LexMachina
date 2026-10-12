# LexMachina

LexMachina is a **query-specific visual legal-research system for Swiss law**.

A user asks a legal question. The product retrieves relevant case law, generates a sourced answer, independently searches for contrary/limiting/exception authorities, and displays the retrieved jurisprudence as an interactive map so minority lines and outliers are harder to miss.

Current MVP flow:

```
question
  -> live OpenCaseLaw retrieval + deterministic dedupe
  -> query-conditioned clusters/map (rendered immediately)
  -> lazy evidence hydration
  -> source-constrained generative answer
  -> independent adversarial counter-authority pass
  -> patch answer/evidence/statuses without moving the map
  -> clickable decision/source inspection
```

The repository is operated by an autonomous OpenCode/Ox engineering factory. The factory optimizes for **minimal repository-owner attention** and aggressive reuse of the prior LexMachina research/codebase.

`main` is intentionally a lightweight control plane. Full historical artifacts remain on accepted `lab/*` and cycle branches; only compact accepted-state summaries are mirrored to `main`.


## Run the v45 query-map product

The v45 MVP entry point is `product/query_app.py`; `product/server.py` is the preserved legacy 174k-map server, not the query-product hot path.

The normal path uses live OpenCaseLaw retrieval and the free/local generative provider abstraction:

```bash
pip install -r product/requirements-query.txt
python product/query_app.py --port 8787
```

Open `http://127.0.0.1:8787/`. The UI renders the retrieved map first, then lazily hydrates evidence and enriches that same map with the sourced answer and independent counter-authority audit.

A local OpenAI-compatible backend (Ollama / LM Studio / vLLM) can be used by setting `LEX_GENAUDIT_BACKEND=local`, `LEX_OPENAI_BASE_URL`, and optionally `LEX_OPENAI_MODEL`. If no generative provider succeeds, LEX keeps the map and sources and visibly falls back to the extractive answer instead of pretending the generative audit succeeded.

For deterministic offline development/tests:

```bash
python product/query_app.py --fixture --port 8787
pytest -q product/tests/test_query_map_mvp.py
```

The extractive TF-IDF answer is a degraded fallback only. Normal v45 behavior is the promoted `generative-audit` contract 2.2.
