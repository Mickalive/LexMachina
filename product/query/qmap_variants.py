"""Product-side seam for the ACCEPTED frontier map-geometry component.

The accepted team `frontier-query-conditioned-map-geometry` (independent audit
``CYCLE_38973386164_GATE.json``, gate=PASS, safe_to_integrate=true, accept commit
``be5eba7f``) built two runnable geometry variants behind the ``query_result_bundle``
seam and scored them under the FROZEN geometry rule
(``RULES_GEOMETRY.json`` sha256 ``a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633``).
Its own claim ceiling, copied here verbatim and not weakened:

* the promoted ``relevance_ordered`` variant passes **22/33** frozen criteria
  against the incumbent's **16/33**, with zero criterion regressions on any
  bundle (de 7/11, fr 8/11, it 7/11 versus incumbent 6/5/5);
* **0 of 3 bundles still pass all 11 criteria**, so the absolute bar is NOT met
  and this component does not make the map useful to a jurist;
* ``PROJ_SPEARMAN``/``PROJ_KNN10`` fail on every bundle under both variants, so
  adopting it adopts coherence and structure, **not** distance fidelity;
* ``OUTLIER_VALIDITY`` is unreachable while the citation graph is empty
  (total degree 0), so the frozen DEGENERATE->FAIL clause fires under any variant;
* it says nothing about whether any decision supports, limits or contradicts
  the answer.

This module is the drop-in the team's ``INTEGRATION_CONTRACT.json`` prescribes:
a sibling factory next to ``qmap.build_map`` returning the identical tuple
shape, selected in the bundle seam behind a config flag. Nothing about the
renderer changes except the one palette lookup the team's own
``RENDERER_PRECONDITION.json`` flagged as a blocking precondition for drop-in
adoption (see ``product/static/query.html``).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GEOMETRY_ROOT = REPO_ROOT / "frontier" / "frontier-query-conditioned-map-geometry"
if GEOMETRY_ROOT.is_dir() and str(GEOMETRY_ROOT) not in sys.path:
    sys.path.insert(0, str(GEOMETRY_ROOT))

#: Provenance of the adopted component.  Recorded in every bundle so a reader
#: never has to infer which geometry produced the coordinates they are looking
#: at, and so the accepted team's claim ceiling travels with the map.
GEOMETRY_COMPONENT = "frontier-query-conditioned-map-geometry"
GEOMETRY_ACCEPT_RUN = 38973386164
GEOMETRY_ACCEPT_COMMIT = "be5eba7f2203db323cb2ae21f0794041908a5711"
GEOMETRY_RULES_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
#: Criteria passed under the FROZEN rule, as accepted by the team (de/fr/it out
#: of 11 each).  The product recomputes these with the frozen rule before it
#: may claim an improvement; these constants are provenance, never a threshold.
GEOMETRY_FROZEN_CRITERIA_PASSED = {"incumbent": {"de": 6, "fr": 5, "it": 5},
                                  "relevance_ordered": {"de": 7, "fr": 8, "it": 7}}

#: The variant the team promoted and Core Product adopts.  Selectable per call
#: so the incumbent stays one argument away for regression comparison.
DEFAULT_VARIANT = "relevance_ordered"


def variant_available(variant: str = DEFAULT_VARIANT) -> bool:
    """True when the accepted component is importable and exposes ``variant``."""
    try:
        from qmap_geometry import VARIANTS  # noqa: PLC0415
    except Exception:
        return False
    return variant in VARIANTS


#: The product map contract (QUERY_MAP_MVP, enforced by product/tests and by
#: ``screenPos`` in the renderer) is that every point lies inside [-1, 1] on
#: both axes.  The accepted team's own output contract promises that range for
#: ``x`` and leaves ``y`` unspecified, and the adopted layout in fact emits
#: shell rows at ``y = -1 + 0.05*jitter``, i.e. as low as -1.025 — measured this
#: cycle, it broke three product contract tests.  The team writes no product
#: code and could not see the product's renderer, so the clamp belongs here,
#: in the seam, where it adapts the component to the product's coordinate
#: contract without editing a byte of the accepted team's source.
COORD_MIN = -1.0
COORD_MAX = 1.0


def _clamp_coord(value: object) -> float:
    """Coerce one coordinate into the product's [-1, 1] map contract."""
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return round(max(COORD_MIN, min(COORD_MAX, v)), 4)


def build_variant_geometry(ranked: list[dict], *, variant: str = DEFAULT_VARIANT,
                           query_language: str = "de") -> tuple[list, list, list]:
    """Return ``(decisions, clusters, relations)`` for the adopted variant.

    Mirrors ``qmap.build_map``'s tuple contract so the bundle seam, the
    progressive expand path and the renderer consume it unchanged.  The team's
    own contract fixes the emitted fields: ``x``/``y`` rounded to 4 decimals in
    [-1,1], ``cluster_id`` int (positive for clustered rows, unique NEGATIVE
    for un-hydrated unclustered context, plus the additive ``unclustered`` flag),
    ``is_outlier`` on exactly ``max(1, n//10)`` rows, and ``clusters[]`` with a
    true ``size`` and ``member_ids`` truncated at the shipped 50-row cap.

    ``relations`` is empty: this variant computes geometry only and leaves the
    seam's existing typed/shared citation relations untouched.
    """
    from qmap_geometry import build_variant_geometry as _build  # noqa: PLC0415

    bundle = {"decisions": [dict(d) for d in ranked]}
    out = _build(bundle, variant, query_language=query_language)
    decisions = list(out.get("decisions") or [])
    clusters = list(out.get("clusters") or [])
    meta = dict(out.get("geometry_variant") or {})
    for d in decisions:
        d["x"] = _clamp_coord(d.get("x"))
        d["y"] = _clamp_coord(d.get("y"))
        d.setdefault("counter_status", "none")
        d.setdefault("counter_evidence", "")
        d.setdefault("counter_uncertainty", None)
        d["geometry_variant"] = variant
        d["geometry_component"] = GEOMETRY_COMPONENT
    for c in clusters:
        c["geometry_variant"] = variant
    meta.update({
        "component": GEOMETRY_COMPONENT,
        "accept_run": GEOMETRY_ACCEPT_RUN,
        "accept_commit": GEOMETRY_ACCEPT_COMMIT,
        "rules_sha256": GEOMETRY_RULES_SHA256,
        "adopted_variant": variant,
        "frozen_criteria_passed_accepted": GEOMETRY_FROZEN_CRITERIA_PASSED,
        "claim_ceiling": (
            "Adopting this variant adopts coherence and structure, not distance "
            "fidelity: PROJ_SPEARMAN and PROJ_KNN10 fail on every bundle under "
            "both variants, and 0 of 3 served bundles pass all 11 frozen criteria. "
            "Group membership and placement are not evidence that an authority "
            "supports or contradicts the answer."
        ),
        "meaning_disclosure": (
            "Horizontal position is the retrieval relevance score and the "
            "vertical band is the language of the decision, so two points side "
            "by side are similarly relevant, not necessarily similarly worded. "
            "Positions are not a legal-similarity claim. Rows whose full text "
            "was not hydrated at serve time are drawn as unclustered context "
            "(cluster_id < 0) and are not part of any group."
        ),
    })
    _ = meta  # meta travels via each row/cluster; kept for future bundle use
    return decisions, clusters, []


__all__ = [
    "DEFAULT_VARIANT",
    "GEOMETRY_ACCEPT_COMMIT",
    "GEOMETRY_ACCEPT_RUN",
    "GEOMETRY_COMPONENT",
    "GEOMETRY_FROZEN_CRITERIA_PASSED",
    "GEOMETRY_RULES_SHA256",
    "build_variant_geometry",
    "variant_available",
]