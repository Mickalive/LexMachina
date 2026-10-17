"""Hydration predicate: which bundle rows are shells versus retrievable decisions.

The predicate is the one the ACCEPTED ablation used (frontier-served-packet-
falsification run 38880639079, vendored ``frontier_map_semantics.textgeo``):
``detail_status != 'search_hit'`` marks an un-hydrated shell.  It is vendored
byte-identically in this package and re-exported here so that the variants and
the before/after report use exactly one definition.

MEASURED (gate packet 38839347028, three served bundles): shell bodies are the
docket number only ("4A_173/2017"), median TF-IDF nnz 0-1, while search_hit
bodies are 3-4.7 KB of regeste/full text (median nnz 27-29).
"""
from __future__ import annotations

from .vendored.frontier_map_semantics.textgeo import is_unhydrated  # noqa: F401

PREDICATE = "detail_status != 'search_hit'"
PREDICATE_SOURCE = (
    "vendored frontier_map_semantics.textgeo.is_unhydrated, byte-identical to "
    "the predicate that produced the accepted un-hydrated-row ablation "
    "(french_largest_share 0.7696 -> hydrated 0.268, dominant-member Jaccard 0.235)"
)


def hydration_mask(decisions: list[dict]) -> list[bool]:
    """True where the row IS a shell (un-hydrated), in bundle row order."""
    return [bool(is_unhydrated(d)) for d in decisions]


def hydration_report(decisions: list[dict], query_language: str) -> dict:
    mask = hydration_mask(decisions)
    n = len(decisions)
    shells = [d for d, s in zip(decisions, mask) if s]
    kept = [d for d, s in zip(decisions, mask) if not s]

    def langs(rows: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in rows:
            k = str(d.get("language"))
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    return {
        "predicate": PREDICATE,
        "predicate_source": PREDICATE_SOURCE,
        "n_rows": n,
        "n_shells": len(shells),
        "n_clusterable": len(kept),
        "shell_language_mix": langs(shells),
        "clusterable_language_mix": langs(kept),
        "clusterable_query_language_share": (
            sum(1 for d in kept if d.get("language") == query_language) / max(1, len(kept))
        ),
        "bundle_query_language_share": (
            sum(1 for d in decisions if d.get("language") == query_language) / max(1, n)
        ),
    }
