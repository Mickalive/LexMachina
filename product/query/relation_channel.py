"""Why the map has no relation edge — measured, stated, and never invented.

The problem this solves
-----------------------
``QUERY_MAP_MVP`` §7 requires "citation/relation edges available on selection"
and §10A lists typed relations/citations as required ``query_result_bundle``
fields. The product ships both — and on a perfectly healthy query the bundle
carries ``relations: []``, so ``showDetail()`` renders no ``Relations:`` line at
all. To a jurist that is indistinguishable from a broken feature.

Measured on the shipped offline slice (rent-default, 100 decisions):
``gate_admissibility`` raises its ``no_relations_on_map`` warning,
``relations_provenance`` reports ``shared_citation_relations: 0`` — and the
*reason* was never published. Only 8 of 100 rows carry a detectable authority
reference at all, and no two of them share one. That is a property of the
retrieved set, not a defect, and it is exactly the kind of fact a research
interface should state instead of silently omitting a panel.

What this module does and does not claim
----------------------------------------
It **classifies an observed channel state from measured counts**. It never
synthesises an edge, never infers a citation that the records do not carry, and
never touches geometry, clusters or any counter-authority classification.

The detector is injected by the caller (``qmap.find_citations`` in production).
Keeping this module stdlib-only means the browser-facing bundle builder and the
``human_gate_finalize`` CLI can both import it — the same reason
``counter_status.py`` is a leaf.

States
------
``POPULATED``
    At least one relation edge is on the map.
``EMPTY_NO_CITATIONS_DETECTED``
    No retrieved row carries a detectable authority reference, so no shared
    reference can exist.
``EMPTY_NO_SHARED_AUTHORITY``
    Rows do carry references, but no two of them reference the same authority.
    This is the interesting negative: it is what a ranked list cannot show and a
    map cannot fake.
``EMPTY_NO_DECISIONS``
    Degenerate: nothing was retrieved.
"""
from __future__ import annotations

CHANNEL_STATES = (
    "POPULATED",
    "EMPTY_NO_SHARED_AUTHORITY",
    "EMPTY_NO_CITATIONS_DETECTED",
    "EMPTY_NO_DECISIONS",
)

#: How many shared references are listed per row in the detail panel. Matches the
#: bundle's own relation cap so the panel and the data agree.
REFERENCE_SAMPLE = 5


def citation_sets(decisions: list[dict], detector) -> list[set]:
    """Per-decision sets of detectable authority references.

    ``detector(text) -> iterable[str]``. Injected so this module stays a leaf;
    the caller decides how a reference is spelled.
    """
    out: list[set] = []
    for decision in decisions or []:
        try:
            out.append(set(detector(decision) or ()))
        except Exception:  # pragma: no cover - a detector must never break a bundle
            out.append(set())
    return out


def coverage(decisions: list[dict], detector, *, sample_size: int = REFERENCE_SAMPLE) -> dict:
    """Measure the relation channel from the rows actually on the map.

    Counting is done with an inverted index rather than an O(n^2) scan: the bundle
    can hold ~300 decisions and this runs on the map hot path.
    """
    rows = list(decisions or [])
    n = len(rows)
    if n == 0:
        return {
            "n_decisions": 0,
            "n_rows_with_citation": 0,
            "n_distinct_references": 0,
            "n_rows_in_a_shared_pair": 0,
            "n_pairs_sharing_citation": 0,
            "shared_reference_sample": [],
            "per_row_reference_sample": sample_size,
        }
    sets = citation_sets(rows, detector)
    with_ref = [s for s in sets if s]
    inverted: dict[str, int] = {}
    for refs in sets:
        for ref in refs:
            inverted[ref] = inverted.get(ref, 0) + 1
    pairs = 0
    in_pair = set()
    shared_sample: list[str] = []
    for ref, count in sorted(inverted.items()):
        if count < 2:
            continue
        if len(shared_sample) < sample_size:
            shared_sample.append(ref)
        pairs += count * (count - 1) // 2
    for i, refs in enumerate(sets):
        if any(inverted.get(ref, 0) >= 2 for ref in refs):
            in_pair.add(rows[i].get("decision_id"))
    return {
        "n_decisions": n,
        "n_rows_with_citation": len(with_ref),
        "n_distinct_references": len(inverted),
        "n_rows_in_a_shared_pair": len(in_pair),
        "n_pairs_sharing_citation": pairs,
        "shared_reference_sample": shared_sample,
        "per_row_reference_sample": sample_size,
    }


def classify(meas: dict, n_relations: int = 0) -> dict:
    """Name the channel state. Pure function of the measurement + edge count."""
    meas = dict(meas or {})
    n_relations = int(n_relations or 0)
    if n_relations > 0:
        state = "POPULATED"
    elif not meas.get("n_decisions"):
        state = "EMPTY_NO_DECISIONS"
    elif not meas.get("n_rows_with_citation"):
        state = "EMPTY_NO_CITATIONS_DETECTED"
    else:
        state = "EMPTY_NO_SHARED_AUTHORITY"
    out = {
        "state": state,
        "n_relations": n_relations,
        "measured": meas,
        "disclosure_required": state != "POPULATED",
        "claim_ceiling": (
            "shared-reference counts are text coincidences between retrieved records in the "
            "reference form the detector recognises; they are not a verified citation graph "
            "and are not re-derived from decision text"
        ),
    }
    out["note"] = describe(out)
    return out


def describe(channel: dict) -> str:
    """One honest sentence a jurist can read next to an empty relations panel."""
    state = (channel or {}).get("state")
    m = (channel or {}).get("measured") or {}
    n_rel = int((channel or {}).get("n_relations") or 0)
    if state == "POPULATED":
        return f"{n_rel} relation edge(s) on the map."
    if state == "EMPTY_NO_DECISIONS":
        return "No decision is on the map, so there is nothing to relate."
    if state == "EMPTY_NO_CITATIONS_DETECTED":
        return (
            "No relation edge: none of the "
            f"{m.get('n_decisions', 0)} retrieved decisions cites an authority in a form this "
            "product detects. Nothing is hidden here - the retrieved set simply carries no "
            "citation to relate."
        )
    if state == "EMPTY_NO_SHARED_AUTHORITY":
        return (
            f"No relation edge: {m.get('n_rows_with_citation', 0)} of {m.get('n_decisions', 0)} "
            "retrieved decisions cite an authority, but no two cite the same one, so there is "
            "no shared authority to draw an edge along."
        )
    return ""


def channel_state(bundle_provenance: dict) -> str:
    """Read the published state back out of a bundle's provenance (or '' if absent).

    Kept so a consumer never has to re-derive the classification — and so a
    bundle that predates this field degrades to "unknown" instead of to a guess.
    """
    prov = (bundle_provenance or {}).get("relations_provenance") or {}
    return str(prov.get("channel_state") or "")


def state_flags() -> dict:
    """Vocabulary for tests and for the UI, published rather than hard-coded."""
    return {
        "states": list(CHANNEL_STATES),
        "populated": "POPULATED",
        "empty_no_shared_authority": "EMPTY_NO_SHARED_AUTHORITY",
        "empty_no_citations_detected": "EMPTY_NO_CITATIONS_DETECTED",
        "reference_sample": REFERENCE_SAMPLE,
    }
