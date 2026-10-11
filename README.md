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
