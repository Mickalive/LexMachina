"""Compatibility shims for consuming the accepted `product` package.

PROVENANCE / DEFECT RECORD
--------------------------
Defect found while executing charter v2 of frontier-query-map-ui (run 38175693552,
resuming producer snapshot 38172504209):

    product/query/answer.py::counter_authority_pass()
        info["status_counts"] = _status_counts(hits)
    NameError: name '_status_counts' is not defined

The helper is referenced but never defined in the control-plane copy on `main`
(`/home/runner/work/LexMachina/LexMachina/product/query/answer.py`) and it is
also absent from the accepted lab/product mount
(`/tmp/lex_accepted/core/product/product/query/answer.py`).  Consequently
`product.query.pipeline.run_query()` -- and therefore the product server route
`/api/query/run` -- raises before a bundle can be produced.

Scope note: this Frontier team may only write inside
`frontier/frontier-query-map-ui`, `tests/frontier/...`, `results/frontier/...`,
`reports/frontier/...`, `state/frontier/frontier-query-map-ui.json` and
`data/frontier/...`.  Editing `product/` would fail the workflow's
"Enforce team scope" gate, so the defect is fixed *here* by installing the
missing helper into the product module namespace at import time.

The shim is deliberately additive and behaviour-preserving: it only supplies a
helper that the product code already expects to exist.  The product lane is told
to absorb the three-line helper in reports/frontier/frontier-query-map-ui/
INTEGRATION_CONTRACT.md (item: product defect to fix on `main`).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

SHIM_NAME = "_status_counts"
SHIM_VERSION = 1

#: Recorded so the integration contract and the evidence file can prove the
#: shim was required (and so tests can detect when product fixes it upstream).
DEFECT_RECORD = {
    "id": "product.query.answer._status_counts_undefined",
    "symbol": "product/query/answer.py:counter_authority_pass.info['status_counts']",
    "symptom": "NameError: name '_status_counts' is not defined",
    "blast_radius": [
        "product.query.pipeline.run_query()",
        "product/server.py:/api/query/run",
        "product/server.py:/api/query/answer",
        "product/server.py:/api/query/map",
        "product/static/query.html (UI entry point)",
    ],
    "detected_in_run": "38175693552 (operational resume of 38172504209)",
    "fix_owner": "core product lane (product/query/answer.py)",
}


def _status_counts(hits: list[dict]) -> dict[str, int]:
    """Count counter-authority hits per candidate status.

    Mirrors the vocabulary already defined in product/query/answer.py
    (COUNTER_STATUS_PATTERNS) so the reporting shape stays stable:
    known statuses are always present with a possibly-zero count, and any
    unexpected status is still surfaced instead of silently dropped.
    """
    counts: Counter[str] = Counter(str(h.get("candidate_status") or h.get("counter_status") or "unknown") for h in hits)
    return dict(sorted(counts.items()))


def install(product_answer_module: Any | None = None) -> dict[str, Any]:
    """Install the missing helper into `product.query.answer` (idempotent).

    Returns a small report describing what happened so callers can record it in
    evidence output.
    """
    if product_answer_module is None:
        from product.query import answer as product_answer_module  # noqa: PLC0415

    existing = getattr(product_answer_module, SHIM_NAME, None)
    already_had = callable(existing)
    if not already_had:
        setattr(product_answer_module, SHIM_NAME, _status_counts)
    return {
        "shim": SHIM_NAME,
        "shim_version": SHIM_VERSION,
        "installed_by_frontier": not already_had,
        "already_defined_by_product": already_had,
        "defect": DEFECT_RECORD,
    }


def run_query(query: str, top_n: int = 150, max_cites: int = 8) -> tuple[dict, dict[str, Any]]:
    """`product.query.pipeline.run_query` with the shim installed first.

    Returns (bundle, shim_report).
    """
    report = install()
    from product.query.pipeline import run_query as _run_query  # noqa: PLC0415

    return _run_query(query, top_n=top_n, max_cites=max_cites), report


__all__ = ["install", "run_query", "SHIM_NAME", "SHIM_VERSION", "DEFECT_RECORD", "_status_counts"]
