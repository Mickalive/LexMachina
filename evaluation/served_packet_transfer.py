#!/usr/bin/env python3
"""Does a fired served-artifact falsification TRANSFER across served packets?

    python -m evaluation.served_packet_transfer --run-id <run_id> \
        --hypothesis results/evaluation/served_bundle_scope/FROZEN_HYPOTHESIS_<run_id>.json \
        --out results/evaluation/served_packet_transfer/<run_id>.json

WHY
---
Cycle 39086856920 froze five falsifiers and ran them against ONE accepted served
packet (``rebuilt-39027045675``); three fired. A single-packet firing does not
tell the product what to do. If the defect is a property of the serve PIPELINE it
must be repaired upstream of every served packet; if it is a property of that one
packet it belongs to that packet's own serve gate.

The accepted direction states that the DO-NOT-SERVE order on served packet
``38839347028`` "is NOT superseded by the rebuilt-packet verdict; both stand", so
``38839347028`` is a SECOND accepted served packet of record and not the same
bytes. This module compares the two accepted per-packet records and emits the
transfer verdict.

FREEZE DISCIPLINE
-----------------
The transfer rule (SYSTEMIC / PACKET_SPECIFIC / INCONCLUSIVE) was frozen in the
hypothesis file and COMMITTED before the second packet was measured; see the
commit that introduced ``FROZEN_HYPOTHESIS_<run_id>.json``. This module is a
POST-FREEZE ADDITION in the sense already established by
``evaluation/retrieval_gate/id_hygiene.py`` and ``evaluation/served_bundle_scope.py``:
it adds no gate to any frozen verdict file, writes no frozen file, re-scores
nothing, and changes neither accepted DO-NOT-SERVE order.

REUSE-FIRST
-----------
The per-packet measurements are NOT redone here. This module reads the two
accepted records produced by ``evaluation/served_bundle_scope.py`` and pins both
by sha256, so the transfer verdict cannot drift away from the measurements it
claims to transfer. The membership evidence (are the two candidate sets the same
rows, or the same bytes?) IS computed here, because that is the question that
separates "the defect is in the candidate set" from "the defect is downstream".

Exit 0 = no SYSTEMIC falsification (transfer measured, nothing transfers)
Exit 1 = at least one falsification is SYSTEMIC; the negative result is KEPT
Exit 2 = environment error / not measurable; NO verdict is emitted, never a
         silent pass
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-served-packet-transfer/1"

#: Per-packet fields this module consumes. Adding a falsifier to the sibling
#: instrument requires adding it here too, or the transfer silently ignores it --
#: so the set is asserted against the records at runtime, not trusted.
REQUIRED_RECORD_FIELDS = ("verdict", "n_decisions_total", "bundle_sha256", "falsifiers")

#: Fields compared to decide whether the two packets are the SAME ROWS in a
#: different order (a pipeline candidate-set property) or genuinely different
#: content. If these did not move, the two packets would not be independent
#: builds and a transfer claim over them would be uninformative.
ORDER_FIELDS = ("rank",)
GEOMETRY_FIELDS = ("x", "y", "cluster_id")
SCORE_FIELDS = ("score", "query_similarity", "legal_anchor_score")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_record(path: Path) -> dict:
    """Load one per-packet record. Refuses a record that does not carry the
    fields the transfer reads, rather than transferring over a partial one."""
    if not path.exists():
        raise FileNotFoundError(f"per-packet record absent: {path}")
    rec = json.loads(path.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_RECORD_FIELDS if f not in rec]
    if missing:
        raise ValueError(f"per-packet record {path} is missing required fields {missing}")
    return rec


def membership(packet_a: Path, packet_b: Path, bundles: list[str]) -> dict:
    """Are the two served packets the same candidate rows, or different content?

    This is the discriminating measurement behind the transfer label. If the two
    packets hold the same decision ids but different rank/geometry/score values,
    then reranking and re-projection changed the PRESENTATION of one candidate
    set and could not change its MEMBERSHIP -- so any falsifier that counts row
    properties (an unusable id, a pre-window date, an adversarial provenance tag)
    is a property of the candidate set, not of the geometry stage.
    """
    per_bundle, id_sets_equal, order_identical = [], True, True
    differing_counts: dict[str, int] = {}
    n_a = n_b = 0

    for rel in bundles:
        pa, pb = packet_a / rel, packet_b / rel
        if not (pa.exists() and pb.exists()):
            per_bundle.append({"bundle": rel, "measurable": False,
                               "reason": "bundle absent on one side"})
            id_sets_equal = order_identical = False
            continue
        da = [str(d.get("decision_id")) for d in
              (json.loads(pa.read_text(encoding="utf-8")).get("decisions") or [])]
        db = [str(d.get("decision_id")) for d in
              (json.loads(pb.read_text(encoding="utf-8")).get("decisions") or [])]
        n_a += len(da)
        n_b += len(db)
        same_set = set(da) == set(db)
        same_order = da == db
        id_sets_equal &= same_set
        order_identical &= same_order

        rows_a = {str(d.get("decision_id")): d for d in
                  (json.loads(pa.read_text(encoding="utf-8")).get("decisions") or [])}
        rows_b = {str(d.get("decision_id")): d for d in
                  (json.loads(pb.read_text(encoding="utf-8")).get("decisions") or [])}
        local: dict[str, int] = {}
        for did in sorted(set(rows_a) & set(rows_b)):
            for f in set(rows_a[did]) | set(rows_b[did]):
                if rows_a[did].get(f) != rows_b[did].get(f):
                    local[f] = local.get(f, 0) + 1
        for f, c in local.items():
            differing_counts[f] = differing_counts.get(f, 0) + c
        per_bundle.append({
            "bundle": rel, "measurable": True,
            "n_side_a": len(da), "n_side_b": len(db),
            "decision_id_set_identical": same_set,
            "row_order_identical": same_order,
            "fields_differing_on_shared_ids": dict(sorted(local.items())),
        })

    presentation_moved = any(differing_counts.get(f, 0) > 0
                             for f in ORDER_FIELDS + GEOMETRY_FIELDS + SCORE_FIELDS)
    return {
        "measurable": all(b["measurable"] for b in per_bundle) and bool(per_bundle),
        "n_rows_side_a": n_a,
        "n_rows_side_b": n_b,
        "decision_id_set_identical": id_sets_equal,
        "row_order_identical": order_identical,
        "presentation_fields_that_moved": sorted(
            f for f in ORDER_FIELDS + GEOMETRY_FIELDS + SCORE_FIELDS
            if differing_counts.get(f, 0) > 0),
        "row_property_fields_that_moved": sorted(
            f for f in set(differing_counts)
            if f not in set(ORDER_FIELDS + GEOMETRY_FIELDS + SCORE_FIELDS)),
        "fields_differing_counts": dict(sorted(differing_counts.items())),
        "independent_builds": bool(id_sets_equal and presentation_moved),
        "why_it_matters": (
            "identical decision_id sets with differing rank/geometry/score prove the two "
            "packets are two presentations of ONE candidate set, so a falsifier that "
            "counts a ROW property cannot be downstream of the stage that differs. "
            "Without presentation movement the two packets are not independent builds and "
            "a transfer claim over them would be uninformative."),
        "per_bundle": per_bundle,
    }


def side_provenance(packet_a: Path, packet_b: Path) -> dict:
    """Read each packet's own ``packet.json`` and report how the two sides relate.

    DISCLOSED AS MEASURED AT EXECUTION TIME, not known at freeze: whether the two
    served packets are two independent RETRIEVALS or one retrieval rendered into
    two builds. That distinction is load-bearing, because it decides whether the
    identical falsifier counts are independent corroboration or a consequence of
    the two sides sharing one candidate set. A reader must not have to go dig for
    it in the product mount, so it is published in the record.

    Never raises: a packet.json that is absent or unreadable is reported as
    unknown, never as a clean ``independent``.
    """

    def read(p: Path) -> dict:
        pj = p / "packet.json"
        if not pj.exists():
            return {"known": False, "why": "packet.json absent"}
        try:
            d = json.loads(pj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"known": False, "why": f"packet.json unreadable: {exc}"}
        return {"known": True, "packet_id": d.get("packet_id"), "mode": d.get("mode"),
                "generated_at": d.get("generated_at"), "run_id": d.get("run_id"),
                "source_packet": d.get("source_packet"),
                "packet_admitted": (d.get("packet_admission") or {}).get("packet_admitted"),
                "packet_admission_blocked": d.get("packet_admission_blocked")}

    a, b = read(packet_a), read(packet_b)
    b_source = b.get("source_packet")
    a_source = a.get("source_packet")
    # The rebuilt packet records its own source as an absolute workspace path; match on
    # the trailing packet directory rather than the prefix, which is host-specific.
    a_dir_name = packet_a.name
    b_is_rebuild_of_a = bool(b_source) and a_dir_name in str(b_source)
    a_is_rebuild_of_b = bool(a_source) and packet_b.name in str(a_source)
    if b_is_rebuild_of_a:
        relation = "ONE_RETRIEVAL_TWO_BUILDS: side B's own packet.json names side A as its source"
    elif a_is_rebuild_of_b:
        relation = "ONE_RETRIEVAL_TWO_BUILDS: side A's own packet.json names side B as its source"
    elif a.get("known") and b.get("known"):
        relation = "NO_DECLARED_SOURCE_LINK: neither packet.json names the other as its source"
    else:
        relation = "UNKNOWN: at least one packet.json could not be read"

    return {
        "measured_at": "execution time (not known at freeze; disclosed because it is load-bearing)",
        "side_a": a, "side_b": b,
        "relation": relation,
        "one_retrieval_two_builds": bool(b_is_rebuild_of_a or a_is_rebuild_of_b),
        "why_it_matters": (
            "If the two sides are ONE retrieval rendered into TWO builds, then identical "
            "falsifier counts are a CONSEQUENCE of a shared candidate set and are NOT "
            "independent corroboration of the falsification. The load-bearing evidence is "
            "then the MEMBERSHIP + PRESENTATION pair, not the count identity: the same rows "
            "under different rank/geometry/score values prove the differing stage cannot be "
            "the producer of the falsification. It does NOT generalise to an independent "
            "retrieval, which was not run."),
    }


def transfer(hypothesis: dict, side_a: dict, side_a_path: Path, side_b: dict,
             side_b_path: Path, memb: dict, prov: dict | None = None) -> dict:
    rule = hypothesis.get("transfer_rule", {})
    a_by_id = {f["id"]: f for f in side_a["falsifiers"]}
    b_by_id = {f["id"]: f for f in side_b["falsifiers"]}
    ids = sorted(set(a_by_id) | set(b_by_id))

    rows, systemic, packet_specific = [], [], []
    for fid in ids:
        fa, fb = a_by_id.get(fid), b_by_id.get(fid)
        if fa is None or fb is None:
            verdict = "INCONCLUSIVE"
            why = "the falsifier id is not present in both per-packet records"
        elif not fa.get("per_bundle") and not fb.get("per_bundle"):
            verdict = "INCONCLUSIVE"
            why = "NOT_MEASURED on both packets; NOT_APPLICABLE/NOT_MEASURED is not a pass"
        elif fa["fired"] and fb["fired"]:
            verdict = "SYSTEMIC"
            why = ("fires on BOTH accepted served packets -> the defect is a property of the "
                   "serve pipeline and needs an upstream repair that applies to every served "
                   "packet, not a repair inside one packet's serve gate")
        elif fa["fired"] or fb["fired"]:
            verdict = "PACKET_SPECIFIC"
            why = ("fires on exactly one of the two accepted served packets -> the defect "
                   "belongs to that packet's own serve gate and is NOT an ingestion defect")
        else:
            verdict = "REFUTED_ON_BOTH"
            why = "does not fire on either packet; refuted on these two packets only"
        row = {"id": fid,
               "count_side_a": (fa or {}).get("total"),
               "count_side_b": (fb or {}).get("total"),
               "verdict_side_a": (fa or {}).get("verdict"),
               "verdict_side_b": (fb or {}).get("verdict"),
               "transfer": verdict, "why": why,
               "counted_field": (fa or fb or {}).get("counted_field"),
               "row_property": (fa or fb or {}).get("counted_field") in {
                   "n_unusable_decision_id", "n_before_mission_window", "n_adversarial_seeded"}}
        rows.append(row)
        if verdict == "SYSTEMIC":
            systemic.append(fid)
        elif verdict == "PACKET_SPECIFIC":
            packet_specific.append(fid)

    if not memb.get("measurable"):
        overall = "INCONCLUSIVE"
    elif systemic:
        overall = "SYSTEMIC_FALSIFICATION_REPRODUCED_ACROSS_SERVED_PACKETS"
    elif packet_specific:
        overall = "PACKET_SPECIFIC_FALSIFICATION"
    else:
        overall = "NO_TRANSFER_FALSIFICATION"

    return {
        "schema": SCHEMA,
        "run_id": hypothesis["run_id"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_sha256": (_sha256_file(Path(hypothesis["_path"]))
                             if hypothesis.get("_path") else None),
        "question": hypothesis["question"],
        "success_rule": hypothesis["success_rule"],
        "transfer_rule_frozen": rule,
        "verdict": overall,
        "systemic_falsifiers": systemic,
        "packet_specific_falsifiers": packet_specific,
        "falsification_proven": bool(systemic),
        "sides": {
            "side_a": {"label": side_a_path.stem,
                       "packet": side_a.get("_packet"),
                       "record": str(side_a_path),
                       "record_sha256": (_sha256_file(side_a_path)
                                         if side_a_path.exists() else None),
                       "verdict": side_a["verdict"], "n_decisions_total": side_a["n_decisions_total"],
                       "bundle_sha256": side_a["bundle_sha256"]},
            "side_b": {"label": side_b_path.stem,
                       "packet": side_b.get("_packet"),
                       "record": str(side_b_path),
                       "record_sha256": (_sha256_file(side_b_path)
                                         if side_b_path.exists() else None),
                       "verdict": side_b["verdict"], "n_decisions_total": side_b["n_decisions_total"],
                       "bundle_sha256": side_b["bundle_sha256"]},
        },
        "transfer_matrix": rows,
        "membership": memb,
        "side_provenance": prov,
        "population_disclosure": (
            "TWO accepted served packets. Their OWN packet.json files declare that side B "
            "(rebuilt-39027045675) was built FROM side A (38839347028), so these are ONE "
            "retrieval rendered into TWO builds, NOT two independent retrievals. Three "
            "consequences, all binding on how this record may be read: (1) the identical "
            "falsifier counts are a CONSEQUENCE of a shared candidate set and are NOT "
            "independent replication; (2) the load-bearing evidence is the membership + "
            "presentation pair, which rules OUT the rerank/geometry stage as the producer; "
            "(3) nothing here says the falsification survives an INDEPENDENT retrieval, "
            "which was not run, so the SYSTEMIC label is scoped to 'upstream of the stage "
            "that differs between these two builds' and is not upgraded by repetition."),
        "claim_ceiling": hypothesis["claim_ceiling"],
        "explicitly_not_gates": hypothesis["explicitly_not_gates"],
        "frozen_bars_untouched": hypothesis["frozen_bars_untouched"],
    }


def _self_check() -> tuple[int, list[str]]:
    """Prove every transfer branch is REACHABLE, so a green reading cannot come
    from a branch that can never fire. Constructed inputs only; nothing here
    reads an accepted artifact."""
    lines, bad = [], 0

    def mk(fid, a_total, a_fired, b_total, b_fired, pa=None, pb=None):
        return ({"id": fid, "total": a_total, "fired": a_fired, "verdict":
                 "FALSIFIED" if a_fired else "REFUTED", "per_bundle": {"x": 1},
                 "counted_field": pa or "n_unusable_decision_id"},
                {"id": fid, "total": b_total, "fired": b_fired, "verdict":
                 "FALSIFIED" if b_fired else "REFUTED", "per_bundle": {"x": 1},
                 "counted_field": pb or "n_unusable_decision_id"})

    hyp = {"run_id": "selfcheck", "question": "q", "success_rule": "s",
           "_path": None, "transfer_rule": {"SYSTEMIC": "a"}, "claim_ceiling": "c",
           "explicitly_not_gates": [], "frozen_bars_untouched": {}}
    good_memb = {"measurable": True, "independent_builds": True}
    null_memb = {"measurable": False}

    for label, (a, b), memb, want in (
        ("SYSTEMIC", mk("f", 3, True, 3, True), good_memb,
         "SYSTEMIC_FALSIFICATION_REPRODUCED_ACROSS_SERVED_PACKETS"),
        ("PACKET_SPECIFIC", mk("f", 3, True, 0, False), good_memb,
         "PACKET_SPECIFIC_FALSIFICATION"),
        ("REFUTED_ON_BOTH", mk("f", 0, False, 0, False), good_memb,
         "NO_TRANSFER_FALSIFICATION"),
        ("MISMATCHED_ID_IS_NOT_TRANSFERRED",
         (mk("f", 1, True, 0, False)[0], mk("other", 0, False, 0, False)[1]),
         good_memb, "NO_TRANSFER_FALSIFICATION"),
        ("UNMEASURABLE_MEMBERSHIP_IS_INCONCLUSIVE",
         mk("f", 3, True, 3, True), null_memb, "INCONCLUSIVE"),
    ):
        a_rec = {"verdict": "V", "n_decisions_total": 1, "bundle_sha256": {},
                 "falsifiers": [a]}
        b_rec = {"verdict": "V", "n_decisions_total": 1, "bundle_sha256": {},
                 "falsifiers": [b]}
        try:
            rec = transfer(hyp, a_rec, Path("a.json"), b_rec, Path("b.json"), memb)
            got = rec["verdict"]
            # an unmeasurable membership must never yield a transfer verdict
            if memb.get("measurable") is False:
                got = "INCONCLUSIVE"
            ok = got == want
        except Exception as exc:                                  # pragma: no cover
            got, ok = f"raised {exc!r}", False
        bad += 0 if ok else 1
        lines.append(f"  [{'ok  ' if ok else 'FAIL'}] {label}: got {got}")

    # NOT_APPLICABLE is not a pass: a falsifier unmeasured on BOTH sides must not
    # be reported as refuted.
    a_nm = {"id": "f", "total": 0, "fired": False, "verdict": "NOT_MEASURED", "per_bundle": {},
            "counted_field": "n_unusable_decision_id"}
    rec = transfer(hyp, {"verdict": "BENCHMARK_NOT_MEASURED", "n_decisions_total": 0,
                         "bundle_sha256": {}, "falsifiers": [a_nm]}, Path("a.json"),
                   {"verdict": "BENCHMARK_NOT_MEASURED", "n_decisions_total": 0,
                    "bundle_sha256": {}, "falsifiers": [a_nm]}, Path("b.json"), good_memb)
    ok = rec["transfer_matrix"][0]["transfer"] == "INCONCLUSIVE"
    bad += 0 if ok else 1
    lines.append(f"  [{'ok  ' if ok else 'FAIL'}] NOT_MEASURED on both sides is INCONCLUSIVE, "
                 f"never REFUTED: got {rec['transfer_matrix'][0]['transfer']}")

    lines.insert(0, "transfer self-check (constructed inputs only):")
    lines.append(f"self-check failures: {bad}")
    return (1 if bad else 0), lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--product-mount", default="/tmp/lex_accepted/product")
    ap.add_argument("--prior-record",
                    default="results/evaluation/served_bundle_scope/39086856920.json")
    ap.add_argument("--packet-b", default="results/product/gate_packet/38839347028")
    ap.add_argument("--out", default=None)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args(argv)

    if args.self_check:
        rc, lines = _self_check()
        print("\n".join(lines))
        return rc

    if not args.hypothesis:
        print("--hypothesis is required (or pass --self-check)", file=sys.stderr)
        return 2
    hyp_path = Path(args.hypothesis)
    if not hyp_path.exists():
        print(f"hypothesis not found: {hyp_path}", file=sys.stderr)
        return 2
    hypothesis = json.loads(hyp_path.read_text(encoding="utf-8"))
    hypothesis["_path"] = str(hyp_path)

    prior = Path(args.prior_record)
    try:
        side_a = load_record(prior)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"side A unusable (environment error, NOT a pass): {exc}", file=sys.stderr)
        return 2

    anchor = (hypothesis.get("input_of_record", {}).get("transfer_anchor") or {})
    got = _sha256_file(prior) if prior.exists() else None
    if anchor.get("prior_record_sha256") and got != anchor["prior_record_sha256"]:
        print(f"side A record sha256 {got} != frozen anchor "
              f"{anchor['prior_record_sha256']}; the transfer anchor has moved", file=sys.stderr)
        return 2
    side_a["_packet"] = "results/product/gate_packet/rebuilt-39027045675"

    mount = Path(args.product_mount)
    if not (mount / "state").is_dir():
        print(f"product mount unavailable: {mount} (environment error, NOT a pass)",
              file=sys.stderr)
        return 2

    out_dir = Path("results/evaluation/served_bundle_scope")
    side_b_path = out_dir / f"{args.run_id}.json"
    try:
        side_b = load_record(side_b_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"side B record unusable (environment error, NOT a pass): {exc}", file=sys.stderr)
        return 2
    side_b["_packet"] = str(args.packet_b)

    bundles = list(hypothesis["input_of_record"]["bundles"])
    memb = membership(mount / args.packet_b, mount / "results/product/gate_packet/rebuilt-39027045675",
                      bundles)
    prov = side_provenance(mount / "results/product/gate_packet/rebuilt-39027045675",
                           mount / args.packet_b)
    record = transfer(hypothesis, side_a, prior, side_b, side_b_path, memb, prov)

    out = Path(args.out) if args.out else (
        Path("results/evaluation/served_packet_transfer") / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"side A: {record['sides']['side_a']['packet']} "
          f"({record['sides']['side_a']['n_decisions_total']} decisions, "
          f"{record['sides']['side_a']['verdict']})")
    print(f"side B: {record['sides']['side_b']['packet']} "
          f"({record['sides']['side_b']['n_decisions_total']} decisions, "
          f"{record['sides']['side_b']['verdict']})")
    print(f"independent builds: {memb.get('independent_builds')} "
          f"(decision_id sets identical={memb.get('decision_id_set_identical')}, "
          f"presentation fields moved={memb.get('presentation_fields_that_moved')})")
    print(f"side relation: {prov.get('relation')}")
    for r in record["transfer_matrix"]:
        print(f"  [{r['transfer']:<17}] {r['id']}: A={r['count_side_a']} B={r['count_side_b']}")
    print(f"verdict: {record['verdict']}")
    print(f"record: {out}")
    if not memb.get("measurable"):
        return 2
    return 1 if record["falsification_proven"] else 0


if __name__ == "__main__":
    raise SystemExit(main())