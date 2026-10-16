#!/usr/bin/env python3
"""Row-level tracking of audit-named decisions, derived from the artifacts only.

Why this module exists
----------------------
The independent audit of repair run 38831241913 returned gate=REVISE on two
sentences of ``reports/product/CYCLE_38831241913.md``:

* the report said ``bge_115 II 78`` *"is re-retrieved and cites a real contrary
  passage"* — the row is **absent from all three repaired bundles**, and the
  quoted BARBEY sentence exists only inside that row's ``full_text`` in the OLD
  bundle, where it was **never** the cited ``counter_evidence``;
* the report said ``bge_115 II 108`` *"is now unlabelled"* — the row is **not
  present in the repaired FR bundle at all**.

Neither code nor metric was at fault. The fault was that a **prose claim about
an artifact was never computed against the artifact**.  ``MEASUREMENT.json``
actually recorded the truth (``re_retrieved_now: false``); the report simply did
not read it back.

The contributing ambiguity is definitional: ``inverted_audit_rows_tracked`` in
``product/run_adversarial_repair.py`` searches the repaired bundle's
*adversarial-channel rows* only.  A row present in the repaired bundle without an
``adversarial_channel`` would therefore also read ``re_retrieved_now: false``,
and "not re-retrieved" is easy to mis-read as "not on the map".

So this module recomputes the row table from the two bundle files, reports
presence and channel membership **separately**, can test whether a quoted
passage is the row's cited evidence or merely somewhere in its text, and can be
asked to check its own derivation against a recorded MEASUREMENT.json so the two
can never silently drift apart.

Nothing here changes a label, a metric, a threshold or a population.  It only
makes a claim checkable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

#: The decisions the audit of the rejected cycle 38828034436 named as inverted.
#: Identical to ``product/run_adversarial_repair.AUDIT_INVERTED_IDS``, so the
#: guard and the repair tool cannot drift apart.
AUDIT_INVERTED_IDS: tuple[str, ...] = (
    "bge_136 III 190",   # FR — "nicht entgegen" affirms the landlord may terminate
    "bge_115 II 78",     # FR — recours rejeté, judgment confirmed
    "bge_111 II 384",    # IT — same French disposal sentence
    "bge_123 III 124",   # IT — Berufung abgewiesen
)

#: The off-domain row the same audit named.  It was never in
#: ``AUDIT_INVERTED_IDS``, so it is tracked here and reported as *not recorded in
#: MEASUREMENT.json* rather than as a mismatch.
AUDIT_OFF_DOMAIN_IDS: tuple[str, ...] = ("bge_115 II 108",)  # FR — maritime charter party

#: Everything the audit named, in one tuple.
AUDIT_NAMED_IDS: tuple[str, ...] = AUDIT_INVERTED_IDS + AUDIT_OFF_DOMAIN_IDS

COUNTER_LABELS = frozenset({"candidate-contrary", "candidate-limiting", "candidate-distinguishing"})


def index_rows(bundle: dict) -> dict[str, dict]:
    """decision_id -> decision row.  First occurrence wins (ids are unique)."""
    out: dict[str, dict] = {}
    for row in bundle.get("decisions") or []:
        did = str(row.get("decision_id") or "")
        if did and did not in out:
            out[did] = row
    return out


def normalise(text: Any) -> str:
    """Whitespace/case-insensitive form used for passage containment."""
    return " ".join(str(text or "").split()).casefold().replace("’", "'").replace("…", "")


def passage_support(row: dict | None, quote: str) -> dict:
    """Where does a quoted passage live in this row, if anywhere?

    Answers the exact question the audit asked about the BARBEY sentence: it is
    inside ``full_text`` (so a reader can find it) but it is not the sentence the
    product cited as ``counter_evidence``, so it supports no label.
    """
    if not row:
        return {"row_present": False, "in_full_text": False, "is_cited_evidence": False}
    needle = normalise(quote)
    evidence = normalise(row.get("counter_evidence"))
    full = normalise(row.get("full_text") or row.get("text"))
    return {
        "row_present": True,
        "in_full_text": bool(needle) and needle in full,
        "in_snippet": bool(needle) and needle in normalise(row.get("snippet")),
        "is_cited_evidence": bool(needle) and bool(evidence) and (
            needle in evidence or evidence in needle
        ),
    }


def track_decision(
    old_bundle: dict,
    new_bundle: dict,
    decision_id: str,
    *,
    quotes: dict[str, str] | None = None,
    relabel_rows: list[dict] | None = None,
) -> dict:
    """One audit-named row, old bundle -> repaired bundle, from the files.

    ``in_repaired_bundle`` and ``in_repaired_adversarial_rows`` are reported
    separately on purpose: the first is "is it on the map", the second is "did
    the adversarial route retrieve it".  Collapsing them is what let the report
    say "re-retrieved" for a row that is on neither.

    ``relabel_rows`` is ``relabel_<lang>_old_rows.json`` — the offline
    relabelling of the OLD counter rows, which is what ``MEASUREMENT.json``'s
    ``in_old_population`` / ``old_relabelled_status`` were computed from.  Pass
    it to make those two fields comparable; without it they read ``None`` and
    are simply not compared.
    """
    old = index_rows(old_bundle).get(decision_id)
    new = index_rows(new_bundle).get(decision_id)
    new_adv = bool(new) and bool(new.get("adversarial_channel"))
    relabel_hit = next(
        (r for r in (relabel_rows or []) if decision_id == str(r.get("decision_id"))), None
    )
    row: dict[str, Any] = {
        "decision_id": decision_id,
        "in_old_bundle": old is not None,
        "old_status": (old or {}).get("counter_status"),
        "old_adversarial_channel": (old or {}).get("adversarial_channel"),
        "old_cited_evidence": (old or {}).get("counter_evidence"),
        # Same names/shape MEASUREMENT.json records, derived from the relabel
        # artifact that tool actually read.
        "relabel_artifact_supplied": relabel_rows is not None,
        "in_old_population": (relabel_hit is not None) if relabel_rows is not None else None,
        "old_relabelled_status": (relabel_hit or {}).get("new_status") if relabel_rows is not None else None,
        "in_repaired_bundle": new is not None,
        "in_repaired_adversarial_rows": new_adv,
        "repaired_status": (new or {}).get("counter_status"),
        "repaired_adversarial_channel": (new or {}).get("adversarial_channel"),
        "repaired_cited_evidence": (new or {}).get("counter_evidence"),
        "repaired_rank": (new or {}).get("rank"),
        # Kept under its recorded name so a MEASUREMENT.json comparison is exact.
        "re_retrieved_now": new_adv,
        "new_status_now": (new or {}).get("counter_status") if new_adv else None,
    }
    for name, quote in (quotes or {}).items():
        row.setdefault("quotes", {})[name] = {
            "old": passage_support(old, quote),
            "repaired": passage_support(new, quote),
        }
    return row


def track_all(
    old_bundle: dict,
    new_bundle: dict,
    *,
    decision_ids: Iterable[str] | None = None,
    quotes: dict[str, str] | None = None,
    relabel_rows: list[dict] | None = None,
) -> list[dict]:
    ids = tuple(decision_ids) if decision_ids is not None else AUDIT_NAMED_IDS
    return [
        track_decision(old_bundle, new_bundle, did, quotes=quotes, relabel_rows=relabel_rows)
        for did in ids
    ]


def compare_with_measurement(rows: list[dict], measurement_entry: dict) -> dict:
    """Do the recorded MEASUREMENT.json fields match what the bundles say?

    Returns the per-id differences instead of a bare boolean so a mismatch names
    the field that drifted.  Fields the caller could not derive (``None``, because
    no relabel artifact was supplied) are skipped rather than counted as
    mismatches - skipping is reported, not hidden.
    """
    recorded = {
        str(r.get("decision_id")): r for r in (measurement_entry.get("inverted_audit_rows_tracked") or [])
    }
    fields = ("in_old_population", "old_relabelled_status", "re_retrieved_now", "new_status_now")
    differences: list[dict] = []
    skipped: list[dict] = []
    unrecorded: list[str] = []
    for row in rows:
        rec = recorded.get(row["decision_id"])
        if rec is None:
            # Tracked here because the audit named it; the recorded table does
            # not cover it.  That is a coverage statement, not a disagreement.
            unrecorded.append(row["decision_id"])
            continue
        for field in fields:
            if (field in {"in_old_population", "old_relabelled_status"}
                    and not row.get("relabel_artifact_supplied")):
                skipped.append({"decision_id": row["decision_id"], "field": field,
                                "note": "no relabel artifact supplied; not derivable here"})
                continue
            if rec.get(field) != row.get(field):
                differences.append({
                    "decision_id": row["decision_id"], "field": field,
                    "recorded": rec.get(field), "derived": row.get(field),
                })
    return {
        "agrees": not differences,
        "n_tracked": len(rows),
        "n_recorded": len(recorded),
        "fields_compared": fields,
        "differences": differences,
        "not_compared": skipped,
        "tracked_but_not_recorded": unrecorded,
    }


def summarise(rows: list[dict]) -> dict:
    """The sentences a report is allowed to make about these rows."""
    on_map = [r["decision_id"] for r in rows if r["in_repaired_bundle"]]
    adv = [r["decision_id"] for r in rows if r["in_repaired_adversarial_rows"]]
    labelled = {
        r["decision_id"]: r["repaired_status"] for r in rows
        if r["in_repaired_bundle"] and str(r["repaired_status"] or "none") not in {"none", "", None}
    }
    absent = [r["decision_id"] for r in rows if not r["in_repaired_bundle"]]
    return {
        "n_rows": len(rows),
        "in_repaired_bundle": on_map,
        "in_repaired_adversarial_rows": adv,
        "absent_from_repaired_bundle": absent,
        "carrying_a_counter_status_on_the_repaired_map": labelled,
        "claim_ceiling": (
            "Presence, channel and status of the named rows, recomputed from the two bundle "
            "files. Nothing here says a label is CORRECT: a row carrying a status is a row the "
            "classifier labelled, which the evidence standard still governs."
        ),
    }


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Recompute audit-named row tracking from the bundles.")
    ap.add_argument("--old", required=True, help="superseded bundle json")
    ap.add_argument("--new", required=True, help="repaired bundle json")
    ap.add_argument("--measurement", default=None,
                    help="MEASUREMENT.json whose inverted_audit_rows_tracked must agree")
    ap.add_argument("--relabel", default=None,
                    help="relabel_<lang>_old_rows.json (needed to compare in_old_population)")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--out", default=None, help="write the tracking table here")
    ap.add_argument("--strict", action="store_true",
                    help="exit 5 when the measurement disagrees with the bundles")
    args = ap.parse_args(argv)

    rows = track_all(_load(args.old), _load(args.new),
                      relabel_rows=_load(args.relabel) if args.relabel else None)
    out: dict[str, Any] = {
        "schema": "product-row-tracking/1",
        "old_bundle": str(args.old),
        "new_bundle": str(args.new),
        "lang": args.lang,
        "rows": rows,
        "summary": summarise(rows),
    }
    if args.measurement:
        measurement = _load(args.measurement)
        entry = measurement
        if isinstance(measurement.get("bundles"), dict) and args.lang:
            entry = measurement["bundles"][args.lang]
        out["measurement_check"] = compare_with_measurement(rows, entry)
        out["measurement_path"] = args.measurement
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2, ensure_ascii=False))
    if args.strict and not out.get("measurement_check", {}).get("agrees", True):
        return 5
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())