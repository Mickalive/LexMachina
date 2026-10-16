"""Id-hygiene measurement for the frozen retrieval benchmark (cycle 38945976309).

WHY THIS IS NOT A FROZEN GATE
-----------------------------
The frozen retrieval verdict recorded in
``results/evaluation/retrieval_benchmark/38939239917.json`` is claim-bearing and
must stay byte-reproducible.  ``source::rows_valid`` PASSes on every recorded
row, including rows whose ``decision_id`` is not a decision id at all — the
upstream source returns unresolved template placeholders
(``ge_gerichte_[pjdoc 15442]``) and raw HTML fragments as ids
(``ch_vb__td_class__metadataCell__150000044__td_``).  Adding a gate to
``gates.py`` now would change that recorded verdict and destroy the
byte-identity test that currently makes it trustworthy, so this measurement is
kept deliberately OUT of the frozen verdict and labelled as a post-freeze
addition.

It is not decoration: six of 866 distinct ids on the recorded run are unusable
as map points, citation anchors or dedupe keys, and ``state/evaluation.json``
advertised "malformed-id detection" as an active metric while no gate performed
it.  This module is what makes that claim true, with provenance.

    python -m evaluation.retrieval_gate.id_hygiene --record <run>.json --out <report>.json

Exit 0 = no defect.  Exit 1 = at least one defect (a falsifying result).
Exit 2 = environment error (missing/unreadable record, foreign frozen spec).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.retrieval_gate import frozen, gates  # noqa: E402

HTML = re.compile(r"<[^>]{1,200}>")
PLACEHOLDER = re.compile(r"\[[^\]]{1,80}\]")
SCHEMA = "lex-retrieval-id-hygiene/1"

#: defect classes, in the order they are reported
DEFECT_CLASSES = (
    "empty_id",
    "html_markup_in_id",
    "unresolved_placeholder_in_id",
    "html_markup_in_docket",
    "unresolved_placeholder_in_docket",
)


def id_defects(row: dict) -> list[str]:
    """Defect classes carried by one retrieved row's id fields."""
    decision_id = str(row.get("decision_id") or "")
    docket = str(row.get("docket_number") or "")
    found: list[str] = []
    if not decision_id.strip():
        found.append("empty_id")
    if HTML.search(decision_id):
        found.append("html_markup_in_id")
    if PLACEHOLDER.search(decision_id):
        found.append("unresolved_placeholder_in_id")
    if HTML.search(docket):
        found.append("html_markup_in_docket")
    if PLACEHOLDER.search(docket):
        found.append("unresolved_placeholder_in_docket")
    return found


def measure(record: dict) -> dict:
    """Id-hygiene measurement over one committed retrieval run record."""
    per_query: list[dict] = []
    defects: Counter = Counter()
    offending: dict[str, dict] = {}
    n_rows = n_queries = 0

    for q in record.get("queries") or []:
        rows = q.get("rows") or []
        if not rows:
            continue
        n_queries += 1
        n_rows += len(rows)
        q_defects: list[dict] = []
        for row in rows:
            classes = id_defects(row)
            if not classes:
                continue
            for c in classes:
                defects[c] += 1
            decision_id = str(row.get("decision_id") or "")
            entry = offending.setdefault(decision_id, {
                "decision_id": decision_id,
                "defect_classes": [],
                "docket_number": str(row.get("docket_number") or "")[:120],
                "canonical_url": str(row.get("canonical_url") or "")[:200],
                "query_keys": [],
            })
            entry["defect_classes"] = sorted(set(entry["defect_classes"]) | set(classes))
            if q.get("query_key") not in entry["query_keys"]:
                entry["query_keys"].append(q.get("query_key"))
            q_defects.append({"decision_id": decision_id, "classes": classes})
        if q_defects:
            per_query.append({"query_key": q.get("query_key"),
                              "channel": q.get("channel"), "slug": q.get("slug"),
                              "language": q.get("language"),
                              "n_rows": len(rows),
                              "n_defective_rows": len(q_defects),
                              "defective_ids": sorted(
                                  {d["decision_id"] for d in q_defects})[:8]})

    duplicates = [g for g in record.get("verdict", {}).get("gates", [])
                  if g["gate"].startswith("duplicate::unique_ids")]

    return {
        "schema": SCHEMA,
        "direction_version": frozen.load_frozen()["direction_version"],
        "frozen_sha256": record.get("frozen_sha256"),
        "measured_record_run_id": record.get("run_id"),
        "tier": "POST-FREEZE ADDITION — deliberately not part of the frozen verdict",
        "why_outside_the_frozen_gates": (
            "source::rows_valid checks non-empty id, https + "
            "mcp.opencaselaw.ch host and language in {de,fr,it}; it cannot see that "
            "the id itself is an unresolved upstream placeholder. Folding this into "
            "gates.py would change the recorded 38939239917 verdict and destroy its "
            "byte-identity test, so it is measured beside the frozen verdict."),
        "n_queries_with_rows": n_queries,
        "n_rows": n_rows,
        "n_distinct_defective_ids": len(offending),
        "defects_by_class": {c: defects.get(c, 0) for c in DEFECT_CLASSES
                             if defects.get(c)},
        "n_defective_occurrences": sum(defects.values()),
        "queries_with_defects": per_query,
        "defective_ids": sorted(offending.values(), key=lambda e: e["decision_id"]),
        "frozen_duplicate_gate_status": [
            {"gate": g["gate"], "passed": g["passed"]} for g in duplicates],
        "product_impact": (
            "Every defective id is unusable as a map point key, a citation anchor "
            "or a dedupe key, and each one silently consumes a slot in the result "
            "budget. The frozen benchmark cannot fail on them; Product must "
            "sanitise ids at ingestion."),
    }


def check(report: dict) -> tuple[bool, str]:
    n = report["n_distinct_defective_ids"]
    if n == 0:
        return True, f"no defective ids among {report['n_rows']} rows"
    classes = ", ".join(f"{k}={v}" for k, v in report["defects_by_class"].items())
    return False, f"{n} distinct defective id(s) [{classes}] among {report['n_rows']} rows"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True, help="committed retrieval run record")
    ap.add_argument("--out", default=None, help="where to write the measurement")
    args = ap.parse_args(argv)

    path = Path(args.record)
    if not path.is_file():
        print(f"::error::record does not exist: {path}", file=sys.stderr)
        return 2
    try:
        spec = frozen.load_frozen()
        record = json.loads(path.read_text(encoding="utf-8"))
    except (frozen.FrozenBenchmarkError, json.JSONDecodeError, OSError) as exc:
        print(f"::error::{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if record.get("frozen_sha256") != frozen.FROZEN_SHA256:
        print("::error::record was produced by a different frozen spec", file=sys.stderr)
        return 2
    if not record.get("queries"):
        print("::error::record carries no queries; refusing to measure empty input",
              file=sys.stderr)
        return 2

    report = measure(record)
    ok, detail = check(report)
    report["passed"] = ok
    report["detail"] = detail
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text if args.out is None else f"{'PASS' if ok else 'FAIL'} {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())