"""Evaluation lane: frozen reality benchmark (factory direction v49).

The smallest executable retrieval/counter-authority benchmark that can falsify
the query-map product: four frozen questions, frozen substantive truth gates,
wrong-language/corrupted-output rejection, and a hard <300s full-run latency
budget.  See ``frozen.py`` (freeze discipline) and ``run_benchmark.py`` (CLI).
"""
from evaluation.reality_gate import frozen, gates, run_benchmark  # noqa: F401
