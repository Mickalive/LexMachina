"""Evaluation lane: frozen retrieval/counter-authority benchmark (direction v49).

The smallest executable retrieval benchmark that can falsify the query-map
product's retrieval/counter-authority path: four frozen questions x FR/DE/IT
plain OpenCaseLaw baseline searches, an explicit counter/limiting pass, frozen
controlling-authority and known-counter recall gates, source/duplicate
validity, latency budgets and cached reproducibility.  See ``frozen.py`` (freeze
discipline) and ``run_retrieval_benchmark.py`` (CLI).  No 174k/global-geometry
benchmark is involved and Product code is never imported.
"""
from evaluation.retrieval_gate import client, frozen, gates  # noqa: F401
