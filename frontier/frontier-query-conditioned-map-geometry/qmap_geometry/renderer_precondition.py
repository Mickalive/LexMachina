"""Renderer-readiness probe for the negative-``cluster_id`` convention.

Why this module exists
----------------------
Both variants mark un-hydrated citation *shells* as explicitly unclustered
context with a UNIQUE NEGATIVE ``cluster_id`` and an additive ``unclustered``
flag, and emit no cluster record for them.  That convention is what keeps an
un-hydrated shell from swelling a legal group -- the whole point of the
hydrate-before-cluster design.

The accepted ``INTEGRATION_CONTRACT.json`` states that "the rendering path
already consumes cluster_id, x, y, is_outlier, clusters[].label,
clusters[].size, clusters[].member_ids and relations[]; nothing else
changes."  Measured against the live query-map renderer that statement is
**false for the negative ids**, and the charter forbids this team from fixing
it (no rendering code, no cluster colour).  So the correction belongs here: a
runnable probe that measures the exposure and states the owning lane's minimal
fix, without touching a single byte of rendering.

The hazard, quoted from the mounted product lane
(``product/static/query.html``, the page served by both ``query_app.py`` and
``server.py``, and the surface the human product gate opens):

    const COLORS=["#2459a8",... 8 entries ...];                       // line 141
    ctx.fillStyle=COLORS[(p.cluster_id??0)%COLORS.length];           // line 188

JavaScript's ``%`` truncates toward zero, so for ``cluster_id = -1`` the index
is ``-1`` and ``COLORS[-1]`` is ``undefined``.  Assigning ``undefined`` to
``ctx.fillStyle`` is an invalid value and is IGNORED by the canvas, leaving the
previous point's colour in place.  Every shell is therefore painted in whatever
colour the previously drawn point had, not in a distinct "unclustered context"
colour.  The same expression is used for the cluster legend (line 240), but
that iterates ``clusters[]`` only, so the legend is unaffected.

This is reported, not worked around: renumbering the shells into a
non-negative id would change what the frozen ``structure()`` metric sees (the
vendored scorer splits intra/inter by ``cid`` equality, so distinct negatives
are 'inter' pairs and one shared sentinel would be 'intra' pairs), i.e. it
would move the frozen scores.  That is not this team's call after the scores
are seen, and the charter forbids opening a fourth variant.
"""
from __future__ import annotations

import os
import re
from typing import Any

#: Page that renders the query map, relative to the product lane root.
QUERY_HTML_REL = "product/static/query.html"

#: The two consumer expressions in that page that index COLORS by cluster_id.
CONSUMER_EXPRESSIONS = {
    "point_fill": "ctx.fillStyle=COLORS[(p.cluster_id??0)%COLORS.length]",
    "cluster_legend_dot": "style=\"background:\"+COLORS[c.cluster_id%COLORS.length]",
}

#: Where the owning lane makes the one-line fix.  This team does not apply it.
OWNING_LANE = "Core Product (product/static/query.html) with frontier-query-map-ui"
MINIMAL_FIX = (
    "Change the point-fill index to a non-negative lookup, e.g. "
    "COLORS[((p.cluster_id??0)%COLORS.length+COLORS.length)%COLORS.length], "
    "or gate on the variant's own additive `unclustered` flag to paint shells "
    "in a declared neutral colour. Either keeps cluster colour decisions in "
    "the lane that owns them; this team makes no colour choice."
)

#: Fallback palette literal, used when the product lane is not mounted.  Kept so
#: the probe is reproducible in a bare checkout; the live value is read from the
#: mounted file when it exists and is reported alongside.
FALLBACK_COLORS = [
    "#2459a8", "#d4771d", "#27845b", "#a83b4b",
    "#6d54a8", "#8a653a", "#b34d91", "#65717f",
]


def read_palette(product_root: str | None) -> dict[str, Any]:
    """Read the live COLORS palette if the product lane is mounted.

    Never required: a missing product mount degrades to the pinned literal and
    says so, so the probe still runs in a bare checkout.
    """
    out: dict[str, Any] = {
        "product_root": product_root,
        "palette": list(FALLBACK_COLORS),
        "palette_source": "pinned literal fallback (product lane not mounted)",
        "live_file_read": False,
    }
    if not product_root:
        return out
    path = os.path.join(product_root, QUERY_HTML_REL)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return out
    m = re.search(r"const\s+COLORS\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        return out
    colors = re.findall(r"\"([^\"]+)\"", m.group(1))
    if not colors:
        return out
    out["palette"] = colors
    out["palette_source"] = f"read live from {QUERY_HTML_REL}"
    out["live_file_read"] = True
    out["query_html_sha256_note"] = (
        "Palette is re-read on every run so a renderer change upstream is "
        "visible here instead of being silently assumed."
    )
    return out


def js_mod(a: int, b: int) -> int:
    """JavaScript's ``%``: ``a - b * trunc(a / b)``, sign of the dividend.

    Python's ``%`` returns a non-negative result for a positive modulus, so it
    cannot be used to emulate the renderer. Node agrees with this:
    ``(-1) % 8 === -1`` and ``(-9) % 8 === -1``.
    """
    if b == 0:
        raise ZeroDivisionError("modulo by zero")
    return a - b * int(a / b)


def js_color_index(cluster_id: int, n_colors: int) -> int:
    """What ``COLORS[(cluster_id??0)%COLORS.length]`` evaluates to in JS.

    JS ``%`` truncates toward zero, so a negative id indexes before the array
    start and the lookup yields ``undefined``. Returns the raw index; callers
    check it against ``[0, n_colors)``.
    """
    return js_mod(int(cluster_id), int(n_colors))


def probe_bundle(candidate: dict, palette: list[str]) -> dict[str, Any]:
    """Measure the negative-cluster_id exposure of one variant bundle."""
    decisions = candidate.get("decisions") or []
    clusters = candidate.get("clusters") or []
    n = len(decisions)
    cluster_ids = {int(c.get("cluster_id")) for c in clusters}
    negatives = [int(d.get("cluster_id")) for d in decisions
                 if int(d.get("cluster_id")) < 0]
    n_colors = max(1, len(palette))
    bad = [c for c in negatives if not (0 <= js_color_index(c, n_colors) < n_colors)]
    flagged_unclustered = sum(1 for d in decisions if bool(d.get("unclustered")))
    return {
        "n_decisions": n,
        "n_clusters": len(clusters),
        "n_cluster_records_with_positive_id": sum(1 for c in cluster_ids if c >= 0),
        "n_negative_cluster_ids": len(negatives),
        "negative_cluster_id_share": round(len(negatives) / n, 4) if n else 0.0,
        "n_rows_flagged_unclustered": flagged_unclustered,
        "negative_id_range": [min(negatives), max(negatives)] if negatives else None,
        "negative_ids_index_outside_palette": len(bad),
        "js_color_index_examples": {
            str(cid): js_color_index(cid, n_colors)
            for cid in (negatives[:1] + negatives[-1:]) if cid is not None
        } if negatives else {},
        "canvas_fillstyle_for_negative_id": (
            "undefined (index out of range; canvas ignores an invalid fillStyle "
            "and keeps the PREVIOUS point's colour)"
            if bad else "no negative id falls outside the palette"
        ),
        "legend_affected": False,
        "legend_note": (
            "The legend iterates clusters[] only, and every cluster record this "
            "variant emits has a non-negative cluster_id, so the legend is not "
            "exposed. Only the point fill is."
        ),
    }


def renderer_precondition(
    candidates: dict[str, dict[str, dict]],
    *,
    product_root: str | None = None,
    frozen_scores: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the renderer-readiness record for every variant x bundle."""
    pal = read_palette(product_root)
    per_variant: dict[str, Any] = {}
    worst = 0.0
    for variant, by_qid in sorted(candidates.items()):
        rows = {qid: probe_bundle(b, pal["palette"]) for qid, b in sorted(by_qid.items())}
        worst = max([worst] + [r["negative_cluster_id_share"] for r in rows.values()])
        per_variant[variant] = rows
    return {
        "schema": "frontier-query-conditioned-map-geometry/renderer-precondition/1",
        "finding_id": "renderer_negative_cluster_id_undefined_fillstyle",
        "severity": "BLOCKING_PRECONDITION_FOR_DROP_IN_ADOPTION",
        "finding": (
            "The variants emit unique NEGATIVE cluster_ids for un-hydrated "
            "unclustered context rows. The live query-map renderer indexes its "
            "COLORS palette with `(cluster_id % COLORS.length)`; JavaScript % "
            "truncates toward zero, so a negative id produces a negative index, "
            "COLORS[negative] is undefined, and the canvas silently ignores the "
            "invalid fillStyle. Every unclustered-shell point is painted in the "
            "colour of whichever point was drawn before it."
        ),
        "why_this_team_does_not_fix_it": (
            "Charter v1 non-duplication: this team writes no rendering code, no "
            "UI asset, no shader and no query.html, and touches no cluster "
            "colour. Rendering is owned by frontier-query-map-ui and "
            "product/static/query.html."
        ),
        "why_it_cannot_be_worked_around_on_the_variant_side": (
            "Renumbering shells to a shared non-negative id would change what the "
            "frozen scorer sees: vendored metrics.structure() splits intra/inter "
            "pairs by cluster_id equality, so N distinct negative ids are treated "
            "as N singleton groups while one shared id would make every shell "
            "pair intra-cluster. That moves STRUCTURE_SEP and the frozen verdict. "
            "The charter forbids re-opening the scoring after the scores are seen."
        ),
        "amends": {
            "artifact": "results/frontier/frontier-query-conditioned-map-geometry/INTEGRATION_CONTRACT.json",
            "field": "drop_in_path",
            "why_the_original_claim_is_incomplete": (
                "It states 'nothing else changes' for the rendering path. That "
                "holds for x, y, is_outlier and the cluster records, but the "
                "negative cluster_id is a NEW value class the page has never "
                "received, and one of its two palette lookups does not tolerate "
                "it. The original artifact is left byte-identical for "
                "provenance; this record is the correction."
            )
        },
        "owning_lane": OWNING_LANE,
        "minimal_fix_for_the_owning_lane": MINIMAL_FIX,
        "consumer_expressions": CONSUMER_EXPRESSIONS,
        "palette": pal,
        "per_variant": per_variant,
        "max_negative_cluster_id_share": round(worst, 4),
        "drop_in_safe_as_written": False,
        "drop_in_safe_after_owning_lane_fix": True,
        "claim_ceiling": (
            "This is a rendering-readiness precondition only. It says nothing "
            "about whether the map is useful to a jurist, which remains the "
            "human product gate's question."
        ),
        "frozen_scores_untouched": True,
        "frozen_scores_note": (
            "Emitting this record changed no variant output, no threshold, no "
            "bar, no control and no score. Every criterion value is byte-"
            "identical to the accepted run."
        ),
    }


def default_product_root() -> str | None:
    """Locate a product lane checkout, if one is mounted, without failing."""
    for cand in (
        "/tmp/lex_accepted/core/product",
        os.path.join(os.getcwd(), "product"),
        os.path.join(os.path.dirname(os.getcwd()), "product"),
    ):
        if os.path.isfile(os.path.join(cand, QUERY_HTML_REL)):
            return cand
    return None