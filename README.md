# LexMachina

LexMachina is a **query-specific visual legal-research system for Swiss law**.

A user asks a legal question. The product retrieves relevant case law, generates a sourced answer, independently searches for contrary/limiting/exception authorities, and displays the retrieved jurisprudence as an interactive map so minority lines and outliers are harder to miss.

Current MVP flow:

```
question
  -> OpenCaseLaw retrieval
  -> query_result_bundle
  -> sourced generative answer
  -> counter-authority pass
  -> query-conditioned clusters/map
  -> clickable decision/source inspection
```

The repository is operated by an autonomous OpenCode/Ox engineering factory. The factory optimizes for **minimal repository-owner attention** and aggressive reuse of the prior LexMachina research/codebase.

`main` is intentionally a lightweight control plane. Full historical artifacts remain on accepted `lab/*` and cycle branches; only compact accepted-state summaries are mirrored to `main`.


## Run the v45 query-map product

The normal path uses live OpenCaseLaw retrieval and the free/local generative provider abstraction:

```bash
pip install -r product/requirements-query.txt
python product/query_app.py --port 8787
```

Open `http://127.0.0.1:8787/`. The UI renders the retrieved query map first, then enriches it with the sourced answer and independent counter-authority audit.

For deterministic offline development/tests:

```bash
python product/query_app.py --fixture --port 8787
pytest -q product/tests/test_query_map_mvp.py
```

The extractive TF-IDF answer is a degraded fallback only. Normal v45 behavior is the promoted `generative-audit` contract 2.2.
