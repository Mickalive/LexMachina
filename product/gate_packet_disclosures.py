#!/usr/bin/env python3
"""Per-question disclosures the rebuilt gate packet must publish (v54 item 3).

Why this exists
---------------
Factory direction v54, backlog item (3): the packet must be REBUILT and all
three questions re-verified at run time, and each bundle must *measure and
disclose* four composition facts that the v52/v53 packets never published:

(a) the dominant cluster's query-language share and its un-hydrated
    (``detail_status != search_hit``) share, against the pre-registered
    ``language_coverage_expectation`` — because ``gate_admissibility`` had no
    language-composition finding at all, so a rebuilt packet could ship the same
    composition failure and still verify ``admissible=true``;
(b) the ``source_url`` host distribution per bundle, with any bare-IP host
    flagged explicitly rather than averaged into a histogram;
(c) the budget-dependence of the surfaced counter set — two runs differing only
    in request budget, measured, not asserted;
(d) the mega-cluster share computed from each cluster's ``size`` field rather
    than ``len(member_ids)`` (which ``product/query/qmap.py`` truncates at 50),
    with the truncation recorded. ``MEGA_CLUSTER_SHARE`` is not touched.

What this tool does and does not do
-----------------------------------
It re-verifies every bundle in a packet directory **now** with the product's own
:mod:`product.query.gate_admissibility` and :mod:`product.query.counter_budget_sensitivity`,
rewrites the per-question ``*.admissibility.json`` from that verdict, and writes
the disclosures beside them. It never edits a bundle, never edits the frozen
pre-registration, never reuses a bundle from another run, never tunes a
threshold, and never answers a gate question or writes ``human_gate_ready``.

Usage
-----
    python product/gate_packet_disclosures.py \
        --packet results/product/gate_packet/<run> --mode live

Exit codes: 0 all questions re-verified, 5 at least one question not admissible,
6 packet I/O problem.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = REPO_ROOT / "product"
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gate_packet as gp  # noqa: E402
from product.query import counter_budget_sensitivity as cbs  # noqa: E402
from product.query import gate_admissibility as ga  # noqa: E402

SCHEMA = "product-gate-packet-disclosures/1"

#: The four v54 disclosures, named in the artifact so a reader can check the
#: packet against the requirement without reading this file.
REQUIRED_DISCLOSURES = ("dominant_cluster_composition", "largest_cluster_share_from_size",
                        "source_url_host_distribution", "counter_budget_sensitivity")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def disclose_question(bundle: dict, question: dict | None, *, mode: str) -> dict[str, Any]:
    """Re-verify one bundle now and measure the four required disclosures."""
    verdict = ga.verify_bundle(bundle, question=question)
    verdict["verified_at"] = _now()
    measured = verdict.get("measured") or {}
    codes = {f["code"] for f in verdict.get("findings") or []}
    sensitivity = cbs.measure(bundle, mode=mode)
    return {
        "verdict": verdict,
        "budget_sensitivity": sensitivity,
        "v54_disclosures": {
            "a_dominant_cluster_language_and_hydration": {
                "published": bool({"dominant_cluster_language_composition",
                                   "dominant_cluster_composition"} & codes),
                "dominant_cluster": measured.get("dominant_cluster"),
                "language_coverage_expectation": (question or {}).get(
                    "language_coverage_expectation"),
            },
            "b_source_url_host_distribution": {
                "published": "source_url_host_distribution" in codes,
                "hosts": measured.get("source_url_hosts"),
                "n_hosts": measured.get("source_url_n_hosts"),
                "schemes": measured.get("source_url_schemes"),
                "federal_court_hosted_share_of_linked": measured.get(
                    "source_url_federal_court_hosted_share_of_linked"),
                "rows_without_source_url": measured.get("source_url_rows_without_url"),
                "ip_literal_rows": measured.get("source_url_ip_literal_rows"),
            },
            "c_counter_budget_sensitivity": {
                "published": sensitivity.get("skipped") is True
                or "counter_set" in sensitivity,
                "skipped": sensitivity.get("skipped", False),
                "skip_reason": sensitivity.get("skip_reason"),
                "counter_set": sensitivity.get("counter_set"),
                "budgets": {"full": sensitivity.get("full", {}).get("budget"),
                            "reduced": sensitivity.get("reduced", {}).get("budget")},
            },
            "d_mega_cluster_share_from_size": {
                "published": "largest_cluster_share_definition" in measured,
                "definition": measured.get("largest_cluster_share_definition"),
                "share": measured.get("largest_cluster_share"),
                "share_from_member_ids": measured.get("largest_cluster_member_ids_share"),
                "member_ids_truncated": measured.get("largest_cluster_member_ids_truncated"),
                "member_ids_cap": measured.get("cluster_member_ids_cap"),
                "threshold_unchanged": ga.MEGA_CLUSTER_SHARE,
                "disclosure_fired": "map_is_one_mega_cluster" in codes,
            },
        },
    }


def run(packet_dir: Path, *, mode: str = "live", write_verdicts: bool = True) -> dict:
    packet = gp.recheck_packet(packet_dir)  # raises FileNotFoundError / ValueError
    questions_dir = Path(packet_dir) / "questions"
    manifest = gp.load_manifest(gp._resolve_artifact(packet_dir / "manifest.json",
                                                      packet_dir), strict=False)
    by_qid = {q.get("qid"): q for q in manifest.get("questions") or []}
    out: dict[str, Any] = {
        "record_type": "lex_gate_packet_disclosures",
        "schema": SCHEMA,
        "packet_dir": str(packet_dir),
        "packet_id": packet.get("packet_id"),
        "checked_at": _now(),
        "mode": mode,
        "required_disclosures": list(REQUIRED_DISCLOSURES),
        "questions": [],
    }
    for record in packet.get("questions") or []:
        qid = record.get("qid")
        bundle_path = Path(record["bundle_path"])
        if not bundle_path.is_file():
            out["questions"].append({"qid": qid, "error": "bundle missing", "present": False})
            continue
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        spec = by_qid.get(qid) or {"qid": qid, "language": record.get("language")}
        result = disclose_question(bundle, spec, mode=mode)
        verdict = result["verdict"]
        if write_verdicts:
            (questions_dir / f"{qid}.admissibility.json").write_text(
                json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            (questions_dir / f"{qid}.budget_sensitivity.json").write_text(
                json.dumps(result["budget_sensitivity"], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
        out["questions"].append({
            "qid": qid,
            "language": spec.get("language"),
            "present": True,
            "admissible": bool(verdict["admissible"]) and not record.get("drifted"),
            "drifted_since_preflight": bool(record.get("drifted")),
            "blocking": [f["code"] for f in verdict["findings"] if f["severity"] == "blocking"],
            "warnings": [f["code"] for f in verdict["findings"] if f["severity"] == "warning"],
            "v54_disclosures": result["v54_disclosures"],
        })
    done = [q for q in out["questions"] if q.get("present")]
    out["n_questions"] = len(packet.get("questions") or [])
    out["n_reverified"] = len(done)
    out["admissible_questions"] = [q["qid"] for q in done if q["admissible"]]
    out["blocked_questions"] = [q["qid"] for q in done if not q["admissible"]]
    out["ok"] = bool(done) and len(done) == out["n_questions"] and not out["blocked_questions"]
    out["claim_ceiling"] = (
        "Composition disclosures about the bundles this run produced. They are facts about "
        "these artifacts, not claims about map quality (frontier-map-semantics owns that "
        "measurement), and the budget comparison is a property of this product's own "
        "adversarial route at two budget settings - not a recall bound."
    )
    if write_verdicts:
        (Path(packet_dir) / "disclosures.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--packet", required=True, type=Path)
    ap.add_argument("--mode", choices=("live", "fixture", "offline"), default="live")
    ap.add_argument("--no-write", dest="write_verdicts", action="store_false", default=True)
    args = ap.parse_args(argv)
    try:
        out = run(args.packet, mode=args.mode, write_verdicts=args.write_verdicts)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"packet unusable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 6
    print(json.dumps({k: v for k, v in out.items() if k != "questions"}, indent=2,
                     ensure_ascii=False))
    for q in out["questions"]:
        if not q.get("present"):
            print(f"  {q['qid']}: MISSING", file=sys.stderr)
            continue
        a = q["v54_disclosures"]["a_dominant_cluster_language_and_hydration"]
        c = q["v54_disclosures"]["c_counter_budget_sensitivity"]
        d = q["v54_disclosures"]["d_mega_cluster_share_from_size"]
        dom = a["dominant_cluster"] or {}
        print(f"  {q['qid']}: admissible={q['admissible']} "
              f"dominant_cluster_lang={dom.get('question_language_share')} "
              f"unhydrated={dom.get('unhydrated_share')} "
              f"mega={d['share']} (member_ids {d['share_from_member_ids']}) "
              f"budget_overlap={(c.get('counter_set') or {}).get('overlap_n')}")
    return 0 if out["ok"] else 5


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())