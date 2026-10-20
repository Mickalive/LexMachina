"""Extract the counter-authority rows and their OWN cited evidence from a bundle.

Read-only.  The accepted product bundle contract (product/query/bundle.py) puts
the counter-authority fields on the decision row itself; this module lifts them
verbatim plus the row's own title/regeste/language/rank and the fields the
audit measured (counter_reason, counter_confidence, counter_uncertainty,
counter_evidence_verified, counter_markers).

Nothing here interprets the label.  No network, no provider, no clock.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

#: Fields copied verbatim from the decision row when present.
ROW_FIELDS = (
    "decision_id",
    "rank",
    "language",
    "court",
    "court_name",
    "title",
    "regeste",
    "citation",
    "legal_area",
    "counter_status",
    "counter_evidence",
    "counter_reason",
    "counter_confidence",
    "counter_uncertainty",
    "counter_evidence_verified",
    "counter_markers",
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_bundle(path: str) -> dict[str, Any]:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def _present(row: dict[str, Any], key: str) -> bool:
    """True when the field exists on the row at all (not merely truthy).

    Field PRESENCE is measured separately from emptiness: an accepted row that
    carries counter_status but no counter_evidence_verified flag is itself
    evidence about the product's disclosure, so absence must not be silently
    conflated with ``false``.
    """
    return key in row


def counter_rows(bundle: dict[str, Any], scored_statuses: list[str],
                 reported_statuses: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (scored_rows, reported_only_rows).

    Ordering is deterministic: rank ascending, then decision_id ascending.
    """
    scored: list[dict[str, Any]] = []
    reported: list[dict[str, Any]] = []
    rows = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    for row in sorted(rows, key=lambda d: (int(d.get("rank") or 10**9), str(d.get("decision_id") or ""))):
        status = row.get("counter_status")
        if not status or status == "none":
            continue
        out = {k: row.get(k) for k in ROW_FIELDS}
        out["counter_status"] = status
        out["field_presence"] = {k: _present(row, k) for k in ROW_FIELDS}
        out["full_text_len"] = len(str(row.get("full_text") or ""))
        out["snippet"] = row.get("snippet") or ""
        out["detail_status"] = row.get("detail_status")
        out["channels"] = sorted(row.get("channels") or [])
        out["provenance"] = row.get("provenance")
        # The row's OWN retrievable text: the cited evidence is checked against
        # it to record whether the citation is reproducible from the row.
        out["row_text"] = "\n".join(
            str(x) for x in (row.get("full_text"), row.get("regeste"), row.get("title"), row.get("snippet")) if x
        )
        if status in scored_statuses:
            scored.append(out)
        elif status in reported_statuses:
            reported.append(out)
    return scored, reported


def bundle_facts(bundle: dict[str, Any]) -> dict[str, Any]:
    prov = bundle.get("provenance") or {}
    answer = bundle.get("answer") or {}
    return {
        "query": bundle.get("query"),
        "query_variants": list(bundle.get("query_variants") or []),
        "bundle_version": bundle.get("bundle_version"),
        "answer_status": answer.get("status"),
        "answer_method": answer.get("method"),
        "answer_model": answer.get("model"),
        "answer_cited_decision_ids": list(answer.get("cited_decision_ids") or []),
        "n_decisions": len(bundle.get("decisions") or []),
        "fixture_mode": bool(prov.get("fixture_mode")),
        "generative_audit": prov.get("generative_audit"),
    }


def split_evidence_segments(counter_evidence: str) -> list[str]:
    """Frozen sentence split: the accepted contract joins kept quote refs with '; '."""
    text = str(counter_evidence or "").strip()
    if not text:
        return []
    return [seg.strip() for seg in text.split(";") if seg.strip()]