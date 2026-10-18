"""The ONE predicate for "is this row a counter authority?".

Why this module exists
----------------------
Direction v56 item RF1 (from audit ``CYCLE_39069382456``, gate=BLOCKED, material):
the product published a "counter authorities" number that was really "rows whose
``counter_status`` is not ``none``". ``counter_status`` is a *provenance* field as
well as a verdict field, so that broad test swept in every decision the sourced
answer had cited (``"cited"``) and every row kept purely for recall
(``"supporting-candidate"``, ``"context"``, ``"unclassified"``). On the demo
bundle it reported 5 where exactly 1 row is a real counter-authority finding.

``product/query/gate_admissibility.py`` has always been the single source of
truth for this set, and it still is: it imports and re-exports the names below,
so ``gate_admissibility.NON_COUNTER_STATUSES`` is *the same object* (the
identity assertion in ``tests/test_gate_composition.py`` keeps holding).

Why a separate module, then, rather than importing from ``gate_admissibility``?
Pure import cost. ``gate_admissibility`` pulls in ``product.query.pipeline``,
which needs numpy + scikit-learn. ``product/human_gate_finalize.py`` is the
browser export finaliser and must stay importable in a bare environment; it was
previously hard-coding the broad predicate inline for exactly this reason. This
leaf has stdlib-only imports, so every surface can share one definition without
the light ones inheriting the heavy ones' dependencies.

Never add a second definition of "counter authority" anywhere in the product.
If a surface needs a different question, ask the different question under a
different name - e.g. :func:`counter_status_bearing_count`, which is the honest
provenance count and is always published *beside*, never instead of,
:func:`counter_authority_count`.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

#: Statuses that mean "this row is not a counter-authority finding". Kept in step
#: with ``isCounter()`` in product/static/query.html, so the packet's disclosed
#: counter yield is exactly the set the researcher sees ringed on the map.
#:
#: - ``none`` / ``""`` / ``None``  - no counter pass touched this row.
#: - ``cited``                     - the generative answer CITED this decision.
#:   Citing a case is the opposite of countering it.
#: - ``supporting-candidate``      - kept as supporting context for the answer.
#: - ``context``                   - kept for recall / map context.
#: - ``unclassified``              - seen by the counter pass, no verdict issued.
#:
#: Anything outside this set is a counter-authority finding and is ringed on the
#: map (``candidate-limiting``, ``candidate-contrary``, ``abstained_unevidenced``,
#: and any future evidence-supported status).
NON_COUNTER_STATUSES = frozenset(
    {"none", "", None, "cited", "unclassified", "supporting-candidate", "context"}
)


def is_counter_status(status: Any) -> bool:
    """True only when ``status`` marks a real counter-authority finding.

    Keyed on :data:`NON_COUNTER_STATUSES`, so ``cited`` / ``supporting-candidate``
    / ``context`` / ``unclassified`` rows are excluded however they were set.
    """
    return status not in NON_COUNTER_STATUSES


def _rows(decisions: Iterable[Any]) -> Iterable[dict]:
    for d in decisions or ():
        if isinstance(d, dict):
            yield d


def counter_authority_count(decisions: Any) -> int:
    """Number of rows that are genuinely counter authorities.

    Counts by membership in :data:`NON_COUNTER_STATUSES`, so ``cited`` /
    ``supporting-candidate`` / ``context`` / ``unclassified`` rows - including
    every decision the sourced answer cited - are excluded.
    """
    return sum(1 for d in _rows(decisions) if is_counter_status(d.get("counter_status")))


def counter_status_bearing_count(decisions: Any) -> int:
    """Rows carrying *any* non-empty ``counter_status``, provenance included.

    This is what the old, mislabelled ``counts.counter`` actually measured. It
    stays available because it is a true and useful provenance number, but it is
    published beside :func:`counter_authority_count` under this honest name and
    must never be labelled "counter authorities" (audit ``CYCLE_39065274887``
    F3: publish both definitions side by side).
    """
    return sum(
        1 for d in _rows(decisions) if str(d.get("counter_status") or "none") != "none"
    )


def counter_authority_ids(decisions: Any) -> list[str]:
    """Decision ids that are genuinely counter authorities, in bundle order."""
    return [
        did
        for did in (
            str(d.get("decision_id") or "")
            for d in _rows(decisions)
            if is_counter_status(d.get("counter_status"))
        )
        if did
    ]


def counter_status_histogram(decisions: Any) -> dict[str, int]:
    """``counter_status`` -> count, with ``none``/absent collapsed to ``none``.

    Lets a report state the breakdown that reconciles the two counts above
    (e.g. ``{"cited": 4, "candidate-limiting": 1, "none": 95}``) instead of
    asserting a bare total.
    """
    hist: Counter = Counter(
        str(d.get("counter_status") or "none") for d in _rows(decisions)
    )
    return dict(sorted(hist.items()))


def counter_evidenced(row: Any) -> bool:
    """True only when a counter row carries BOTH a verified flag AND its text.

    Python twin of ``counterEvidenced()`` in ``product/static/query.html``:

        isCounter(d) && !!(d.counter_evidence||"").trim() && d.counter_evidence_verified===true

    Audit ``CYCLE_39091749561`` F7: the product ledger counted a row as
    "evidenced" from ``counter_evidence_verified is True`` alone, while the
    researcher-facing page additionally requires non-empty ``counter_evidence``.
    Those two predicates can disagree exactly on rows whose status name says the
    reviewer abstained (``abstained_unevidenced``). Measured on the committed
    live bundle they do NOT disagree - both abstained rows carry text - which is
    a measurement of that bundle, not a guarantee about the next one; the shared
    predicate exists so that any future disagreement is decided by one definition
    instead of by whichever surface was edited last.

    One predicate, shared, under this honest name. A surface that needs a
    different question must ask it under a different name.
    """
    if not isinstance(row, dict):
        return False
    if not is_counter_status(row.get("counter_status")):
        return False
    has_text = bool(str(row.get("counter_evidence") or "").strip())
    return has_text and row.get("counter_evidence_verified") is True


def evidenced_counter_ids(decisions: Any) -> list[str]:
    """Counter rows that are evidenced under :func:`counter_evidenced`, in order."""
    return [
        did
        for did in (
            str(d.get("decision_id") or "")
            for d in _rows(decisions)
            if counter_evidenced(d)
        )
        if did
    ]


def unevidenced_counter_ids(decisions: Any) -> list[str]:
    """Counter rows kept for visibility WITHOUT evidence (amber ring in the UI)."""
    return [
        did
        for did in (
            str(d.get("decision_id") or "")
            for d in _rows(decisions)
            if is_counter_status(d.get("counter_status")) and not counter_evidenced(d)
        )
        if did
    ]