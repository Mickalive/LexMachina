"""Adoption seam for the accepted query-conditioned geometry variant.

Why this module exists
----------------------
The Frontier component ``frontier-query-conditioned-map-geometry`` (charter v1,
team run 38970483941, independent audit ``CYCLE_38973386164_GATE.json`` PASS /
``safe_to_integrate=true``, accept commit ``be5eba7f2203db323cb2ae21f0794041908a5711``)
delivered two runnable geometry candidates behind the ``query_result_bundle``
seam.  Its promoted, adoptable variant is ``relevance_ordered``: it is strictly
better than the accepted incumbent under the FROZEN geometry rule
(``a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633``) with
**zero regressions** (incumbent 16/33 criteria, ``relevance_ordered`` 22/33).

Its own ``INTEGRATION_CONTRACT.json`` asks Core Product to expose the variant
behind the bundle seam: *"Add a sibling factory ... returning the identical tuple
shape, then select it in the bundle seam behind a config flag."*  That is exactly
this module.  The variant is OFF by default, so the shipped map is byte-identical
unless an operator opts in:

    LEXMACHINA_GEOMETRY_VARIANT=relevance_ordered

Nothing here re-scores, re-tunes or re-measures the frozen rule; the vendored
package under ``product/vendored/qmap_geometry/`` is the accepted component,
byte-identical (see ``PROVENANCE.json`` next to it).

Claim ceiling
-------------
Adopting the variant does NOT make the map pass the frozen geometry bar: 0 of 3
bundles pass all 11 criteria under any candidate.  ``relevance_ordered`` also
changes the meaning of the axes (x = rerank score, y = query-language band) and
its ``PROJ_SPEARMAN``/``PROJ_KNN10`` criteria remain FAILED.  This module only
makes the accepted candidate selectable; the product gate remains the human one.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDORED_ROOT = REPO_ROOT / "product" / "vendored"

#: Environment variable an operator sets to opt into a variant.
GEOMETRY_VARIANT_ENV = "LEXMACHINA_GEOMETRY_VARIANT"

#: The frontier-promoted variant.  ``incumbent``/empty keeps the shipped map.
ADOPTABLE_VARIANT = "relevance_ordered"
KNOWN_VARIANTS = ("incumbent", "relevance_ordered", "hydrate_then_cluster")


def _load_variant_builder():
    """Import the vendored accepted package lazily (keeps startup light)."""
    import sys

    if str(_VENDORED_ROOT) not in sys.path:
        sys.path.insert(0, str(_VENDORED_ROOT))
    from qmap_geometry import build_variant_geometry  # noqa: E402
    return build_variant_geometry


def selected_variant(env: dict[str, str] | None = None) -> str:
    """The variant named by the environment, or ``""`` for the incumbent map."""
    env = os.environ if env is None else env
    raw = str(env.get(GEOMETRY_VARIANT_ENV) or "").strip().lower()
    if raw in ("", "incumbent", "off", "none"):
        return ""
    if raw not in KNOWN_VARIANTS:
        raise ValueError(
            f"unknown {GEOMETRY_VARIANT_ENV}={raw!r}; known: {list(KNOWN_VARIANTS)}"
        )
    return raw


def apply_geometry_variant(decisions: list[dict], clusters: list[dict], query: str,
                           variant: str, *, query_language: str | None = None,
                           ) -> tuple[list[dict], list[dict], dict[str, Any]]:
    """Rewrite ``decisions``/``clusters`` with the accepted variant geometry.

    Returns the identical tuple shape ``qmap.build_map`` emits, plus a metadata
    dict for provenance.  Does not touch relations or any row payload other than
    ``x``, ``y``, ``cluster_id``, ``is_outlier`` and the additive ``unclustered``.
    """
    if not variant:
        return decisions, clusters, {"name": "incumbent"}
    builder = _load_variant_builder()

    lang = query_language
    if not lang:
        try:
            from product.query.answer_gap import detect_language
            lang = detect_language(query, decisions)
        except Exception:  # pragma: no cover - detection is best-effort metadata
            lang = "de"
    if lang not in ("de", "fr", "it"):
        lang = "de"

    bundle = {
        "query": query,
        "decisions": [dict(d) for d in decisions],
        "clusters": [dict(c) for c in clusters],
    }
    out = builder(bundle, variant, query_language=lang)
    meta = dict(out.get("geometry_variant") or {})
    meta["query_language"] = lang
    return list(out.get("decisions") or []), list(out.get("clusters") or []), meta


__all__ = [
    "GEOMETRY_VARIANT_ENV", "ADOPTABLE_VARIANT", "KNOWN_VARIANTS",
    "selected_variant", "apply_geometry_variant",
]
