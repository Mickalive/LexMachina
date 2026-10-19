#!/usr/bin/env python3
"""Direction v57 ordered work (4): hand Core Evaluation the query-concept
disclosure fix to falsify, on the exact bytes already accepted.

What this is
------------
Factory direction v57 orders Core Product to implement the accepted evaluation
handoff ``question_native_coverage_39113690481`` and then, *only after a
gate=PASS promotion*, hand the frozen evaluation feedback cycle to Core
Evaluation.  That promotion has happened: cycle 39172315384 was audited
``gate=PASS`` (``results/audit/product/CYCLE_39172315384_GATE.json``) and
promoted as accept commit ``e21eac3``, which is the tip of ``origin/lab/product``.

This module does the handing.  It does not score anything, does not touch a
frozen bar, rubric, threshold or packet byte, and does not ask the owner
anything.  It recomputes, from the COMMITTED packet bytes only:

* **before** - the admission record as it was written into
  ``results/product/gate_packet/rebuilt-39027045675`` (byte-identical to what
  the accepted DO-NOT-SERVE verdict covers), and
* **after** - the admission record the CURRENT ``product/query`` code produces
  when it is handed those same committed bundle bytes,

and publishes the two side by side with the deltas spelled out, so the
receiving lane can falsify the fix instead of taking the producer's word for it.

Why it is safe to compute "after" from committed bytes
------------------------------------------------------
No bundle is re-retrieved, re-embedded or re-clustered here.  Each committed
bundle is re-hashed with ``product/replay_bundle.content_sha256`` and compared
with the ``content_sha256`` recorded in the committed ``packet.json``; a
mismatch is a hard FAIL, never a quiet pass.  The "after" verdict therefore
differs from the "before" verdict *only* by the product code that ran, which is
the whole point of the handoff.

The falsification protocol it hands over
----------------------------------------
Evaluation's accepted transfer (``39120832665`` -> ``034f2043``,
``DISCLOSURE_DEFECT_TRANSFERRED``) established the defect without an analyst
slug, without a frozen id set, without a baseline record and without any
mapping of any kind.  The same discipline is preserved here: the predicate is
*internal inconsistency of one artifact with itself*, i.e.

    measured.query_concepts_under_covered is non-empty
        AND no finding in the same admission record carries the disclosure.

No judgement about legal usefulness, corpus completeness or doctrine is
encoded anywhere in this file.

Usage
-----
    python product/eval_disclosure_handoff.py --write
    python product/eval_disclosure_handoff.py --json

Exit code is non-zero when any recomputation fails, so this is usable as a
gate and not only as a report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-eval-disclosure-handoff/1"

#: The accepted packet of record.  This is the exact packet the accepted
#: DO-NOT-SERVE verdict (audit of run 39061330426, accept 26582bc5) covered,
#: named in ``results/product/gate_packet/REBUILT_39027045675_CROSS_LANE_HANDOFF.json``.
PACKET_DIR = REPO_ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675"

#: The committed raw sha256 of that packet.json.  Recomputed on every call and
#: compared; a drift is a FAIL, because the whole handoff is scoped to the bytes.
PACKET_SHA256 = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170"

#: The disclosure marker Evaluation's frozen predicate reads in a FINDING CODE.
#: Named here so the handoff cannot drift from what the receiving lane checks.
DISCLOSURE_CODE = "query_concepts_under_covered"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _reroot(recorded: str) -> Path:
    """Committed packets embed the PRODUCER's absolute workspace path.

    ``results/product/gate_packet/REBUILT_39027045675_CROSS_LANE_HANDOFF.json``
    carries that warning verbatim; this helper applies it instead of trusting a
    path that cannot exist on another machine.
    """
    parts = Path(recorded).parts
    if "results" in parts:
        return REPO_ROOT.joinpath(*parts[parts.index("results"):])
    return Path(recorded)


def _codes(verdict: dict) -> list[str]:
    return [str(f.get("code")) for f in (verdict.get("findings") or [])]


def _severity_of(verdict: dict, code: str) -> str | None:
    for f in verdict.get("findings") or []:
        if str(f.get("code")) == code:
            return str(f.get("severity"))
    return None


def _discloses(verdict: dict) -> bool:
    """Evaluation's shape, applied exactly: a FINDING CODE carrying the marker.

    This is the predicate the receiving lane falsifies.  It is deliberately
    written against the finding CODE list and not against any particular term,
    so it cannot be satisfied by naming the right words in prose.
    """
    return DISCLOSURE_CODE in _codes(verdict)


def _row(verdict: dict) -> dict:
    measured = verdict.get("measured") or {}
    return {
        "admissible": bool(verdict.get("admissible")),
        "warning_count": verdict.get("warning_count"),
        "blocking_count": verdict.get("blocking_count"),
        "notice_count": verdict.get("notice_count"),
        "finding_codes": _codes(verdict),
        "query_concepts_under_covered": measured.get("query_concepts_under_covered"),
        "query_concept_rows": measured.get("query_concept_rows"),
        "discloses_under_coverage": _discloses(verdict),
        "disclosure_severity": _severity_of(verdict, DISCLOSURE_CODE),
    }


def build(packet_dir: Path = PACKET_DIR, *, packet_sha256: str = PACKET_SHA256) -> dict:
    """Recompute before/after from committed bytes.  Never raises on bad input.

    The returned record ALWAYS carries ``summary``, including on the
    fail-closed early returns: a caller that cannot find the key must not have
    to distinguish "absent" from "broken".
    """
    packet_dir = Path(packet_dir)

    def _empty_summary(record: dict) -> dict:
        record["questions"] = record.get("questions") or []
        record["summary"] = {
            "n_questions": len(record["questions"]),
            "n_inconsistent_before": 0,
            "n_disclosed_after": 0,
            "n_admission_changed": 0,
            "n_blocking_count_changed": 0,
            "verdict": "FAIL",
        }
        return record

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "packet": {
            "repo_relative_dir": str(packet_dir.relative_to(REPO_ROOT))
            if packet_dir.is_relative_to(REPO_ROOT) else str(packet_dir),
            "packet_json": str((packet_dir / "packet.json").name),
        },
        "questions": [],
        "failures": [],
    }

    packet_path = packet_dir / "packet.json"
    if not packet_path.is_file():
        record["failures"].append(f"missing {packet_path}")
        return _empty_summary(record)

    actual = _sha256_file(packet_path)
    record["packet"]["packet_raw_sha256_recomputed"] = actual
    record["packet"]["packet_raw_sha256_expected"] = packet_sha256
    record["packet"]["packet_bytes_match_expected"] = actual == packet_sha256
    if actual != packet_sha256:
        record["failures"].append(
            f"packet.json raw sha256 {actual} != expected {packet_sha256}"
        )

    from product.query.gate_admissibility import verify_bundle
    from product.replay_bundle import content_sha256

    packet = _load(packet_path)
    for entry in packet.get("questions") or []:
        qid = str(entry.get("qid"))
        row: dict[str, Any] = {"qid": qid, "language": entry.get("language"),
                               "question": entry.get("question")}

        snap = packet_dir / "questions" / f"{qid}.admissibility.json"
        if not snap.is_file():
            record["failures"].append(f"{qid}: missing committed admission snapshot")
            continue
        before = _load(snap)
        row["committed_content_sha256"] = entry.get("content_sha256")
        row["before"] = _row(before)

        bundle_path = _reroot(str(entry.get("bundle_path") or ""))
        if not bundle_path.is_file():
            bundle_path = packet_dir / "questions" / f"{qid}.bundle.json"
        if not bundle_path.is_file():
            record["failures"].append(f"{qid}: missing committed bundle")
            continue
        bundle = _load(bundle_path)
        recomputed = content_sha256(bundle)
        row["bundle_content_sha256_recomputed"] = recomputed
        row["bundle_bytes_match_record"] = recomputed == entry.get("content_sha256")
        if not row["bundle_bytes_match_record"]:
            record["failures"].append(
                f"{qid}: bundle content_sha256 {recomputed} != recorded "
                f"{entry.get('content_sha256')}"
            )

        question = _load(packet_dir / "questions" / f"{qid}.question.json") \
            if (packet_dir / "questions" / f"{qid}.question.json").is_file() else None
        after = verify_bundle(bundle, question=question)
        row["after"] = _row(after)

        b, a = row["before"], row["after"]
        under = list(b.get("query_concepts_under_covered") or [])
        row["delta"] = {
            "measurement_moved": b.get("query_concepts_under_covered") != a.get("query_concepts_under_covered"),
            "warning_count_before": b.get("warning_count"),
            "warning_count_after": a.get("warning_count"),
            "blocking_count_before": b.get("blocking_count"),
            "blocking_count_after": a.get("blocking_count"),
            "discloses_before": b.get("discloses_under_coverage"),
            "discloses_after": a.get("discloses_under_coverage"),
            "admissible_before": b.get("admissible"),
            "admissible_after": a.get("admissible"),
        }
        row["inconsistent_before"] = bool(under) and not b.get("discloses_under_coverage")
        row["disclosed_after"] = bool(a.get("query_concepts_under_covered")) == \
            bool(a.get("discloses_under_coverage"))
        row["disclosure_is_warning_not_blocking"] = (
            row["delta"]["discloses_after"] and a.get("blocking_count") == b.get("blocking_count")
        )
        record["questions"].append(row)

    qs = record["questions"]
    record["summary"] = {
        "n_questions": len(qs),
        "n_inconsistent_before": sum(1 for r in qs if r.get("inconsistent_before")),
        "n_disclosed_after": sum(1 for r in qs if r.get("disclosed_after")),
        "n_admission_changed": sum(
            1 for r in qs if r.get("delta", {}).get("admissible_before")
            != r.get("delta", {}).get("admissible_after")
        ),
        "n_blocking_count_changed": sum(
            1 for r in qs if r.get("delta", {}).get("blocking_count_before")
            != r.get("delta", {}).get("blocking_count_after")
        ),
        "verdict": "PASS" if not record["failures"] and qs and all(
            r.get("disclosed_after") for r in qs
        ) else "FAIL",
    }
    return record


def handoff_envelope(record: dict, *, run_id: str, source_commit: str) -> dict:
    """The machine-readable instruction block the receiving lane executes."""
    return {
        "from_lane": "product",
        "to_lane": "evaluation",
        "handed_over_by_run": run_id,
        "product_commit_of_record": source_commit,
        "ordered_work": (
            "factory direction v57 ordered work (4): falsify-or-pass the accepted "
            "evaluation handoff question_native_coverage_39113690481 on the exact "
            "served bytes, publishing the before/after admission records side by side"
        ),
        "bytes_in_scope": {
            "packet_dir": record["packet"]["repo_relative_dir"],
            "packet_json_raw_sha256": record["packet"].get("packet_raw_sha256_recomputed"),
            "per_question_content_sha256": {
                r["qid"]: r.get("committed_content_sha256") for r in record["questions"]
            },
            "committed_admission_snapshots": (
                "results/product/gate_packet/rebuilt-39027045675/questions/*.admissibility.json"
            ),
            "recompute_command": (
                "python product/eval_disclosure_handoff.py --write"
            ),
            "receiving_lane_verification_command": (
                "python -c \"import json;d=json.load(open("
                "'results/product/gate_packet/rebuilt-39027045675/packet.json'));"
                "print({q['qid']: q['measured'].get('query_concepts_under_covered') for q in d['questions']})\""
            ),
        },
        "falsification_protocol": {
            "predicate": (
                "measured.query_concepts_under_covered is non-empty AND no finding "
                "in the same admission record carries the disclosure marker"
            ),
            "disclosure_marker_in_finding_code": DISCLOSURE_CODE,
            "mapping_free": True,
            "forbidden_in_this_check": [
                "analyst slug", "frozen id set", "baseline record",
                "any id->label or analyst->concept mapping",
            ],
            "what_to_attack": [
                "does the after record disclose EVERY under-covered term the before record measured",
                "is the disclosure a warning and never a blocking finding",
                "is admission (admissible / blocking_count) unchanged by the fix",
                "does the measurement itself move (it must not: the fix is disclosure, not measurement)",
            ],
            "what_this_handoff_does_not_claim": (
                "that any authority is absent from the corpus. Evaluation's caveat is carried "
                "verbatim: a German compound noun may simply not be the doctrine's own vocabulary - "
                "decisions may write Verletzung der Kapitalverwaltung rather than Kapitalverletzung. "
                "The auditable claim is the disagreement between the bundle content and the packet's "
                "own admission record, which is a fact about the product's disclosure behaviour "
                "regardless of which reading is right."
            ),
        },
        "caveat_carried_verbatim_from_evaluation": (
            "a German compound noun may not be the doctrine's own vocabulary, and the auditable "
            "claim is the disagreement between the bundle content and the packet's own admission "
            "record - this is a disclosure fix, NOT a finding that authorities are absent"
        ),
        "no_frozen_input_moved": {
            "rules_label_sha256": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
            "rules_geometry_sha256": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
            "note": "neither file is read or written by this module; the digests are cited as the "
                    "lane's standing re-hash record, not recomputed here",
        },
        "posture_unchanged": {
            "packet_admitted": False,
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "note": "the accepted DO-NOT-SERVE order on rebuilt-39027045675 stands and this "
                    "handoff never authorises an owner question",
        },
        "claim_ceiling": (
            "This artifact claims only that the product's admission record now discloses a "
            "measurement it was already publishing, recomputed on committed bytes whose hashes "
            "are re-verified here. It asserts no legal or jurist usefulness, no retrieval or "
            "counter-authority recall, no frozen bar, rubric or Evaluation score, and no "
            "human-gate readiness."
        ),
    }


def environment() -> dict:
    from product.query_env import PINNED, probe

    p = probe()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numeric_environment_rule": (
            "recorded beside every sha per factory requirement 29: a from-source rebuild is "
            "numeric-environment scoped and is NOT claimed byte-identical across machines. This "
            "handoff makes no rebuild claim at all - it reads committed bytes."
        ),
        "pinned_runtime": dict(PINNED),
        "installed_runtime": p.get("installed"),
        "installed_matches_pin": p.get("installed_matches_pin"),
        "missing": p.get("missing"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the artifact into results/product/")
    ap.add_argument("--out", default=None)
    ap.add_argument("--run-id", default="MANUAL")
    ap.add_argument("--commit", default="UNPINNED")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    record = build()
    record["environment"] = environment()
    record["handoff"] = handoff_envelope(record, run_id=args.run_id, source_commit=args.commit)

    if args.json and not (args.write or args.out):
        print(json.dumps(record, indent=2, ensure_ascii=False))
    elif args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}  verdict={record['summary']['verdict']}")
    elif args.write:
        out = REPO_ROOT / "results" / "product" / "gate_packet" / \
            "REBUILT_39027045675_QUERY_CONCEPT_DISCLOSURE_HANDOFF.json"
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}  verdict={record['summary']['verdict']}")
    else:
        print(json.dumps(record["summary"], indent=2))

    ok = record["summary"]["verdict"] == "PASS"
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())