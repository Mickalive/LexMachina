#!/usr/bin/env python3
"""Apply the adopted counter-anchor gate to the served packet's own bundles.

Why this exists (factory direction v50, obligations (1) and (4))
--------------------------------------------------------------
The served packet 38839347028 is under an accepted DO-NOT-SERVE order whose
label half measured 5 of 65 counter labels supported by their own cited
evidence.  The accepted Frontier component now adopted by this lane decides,
per row, whether that row's OWN cited passage licenses the label it carries.
This tool runs exactly that decision over the packet's frozen bundles and
publishes the emitted/abstained partition — side by side with the accepted
measurement, never instead of it.

What it is NOT
--------------
* It does NOT score label support under the frozen rubric.  Scoring is
  Frontier's / Core Evaluation's job; this tool publishes the COMPONENT's own
  per-row decisions (emitted vs abstained, with the frozen reason codes).
* It does NOT regenerate, edit or overwrite the frozen packet: the input
  bundles are read-only and the output goes to results/product/.
* It never asserts that a decision IS supporting, contrary or limiting.

Usage:
    python product/apply_counter_label_gate_to_packet.py \
        --packet results/product/gate_packet/38839347028 \
        --out results/product/counter_anchor_adoption/ADOPTED_ON_SERVED_PACKET.json

Exit codes: 0 written, 2 bad arguments, 3 a bundle failed to load.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query.counter_label_gate import (  # noqa: E402
    FROZEN_RULES_SHA256,
    apply_counter_label_gate,
    load_frozen_rules,
)

DEFAULT_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
DEFAULT_OUT = (
    REPO_ROOT / "results" / "product" / "counter_anchor_adoption" /
    "ADOPTED_ON_SERVED_PACKET.json"
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_packet(packet_dir: Path, qid: str | None = None) -> dict:
    rules = load_frozen_rules()  # re-hashes; refuses any other bytes
    bundles = sorted((packet_dir / "questions").glob("*.bundle.json"))
    if not bundles:
        raise SystemExit(3)
    rows_out = []
    for path in bundles:
        bundle_qid = path.name[: -len(".bundle.json")]
        if qid and bundle_qid != qid:
            continue
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::error::cannot load {path}: {exc}", file=sys.stderr)
            raise SystemExit(3) from exc
        gated = apply_counter_label_gate(copy.deepcopy(bundle))
        gate = gated["provenance"]["counter_label_gate"]
        rows = []
        for d in gated["decisions"]:
            anchor = d.get("counter_label_anchor")
            if not anchor:
                continue
            rows.append({
                "decision_id": d.get("decision_id"),
                "language": d.get("language"),
                "rank": d.get("rank"),
                "proposed_status": anchor.get("proposed_status"),
                "decision": "abstained" if anchor.get("abstained") else "emitted",
                "product_counter_status_after_gate": d.get("counter_status"),
                "reason_code": anchor.get("reason_code"),
                "counter_uncertainty": d.get("counter_uncertainty"),
                "anchor_profile_status": anchor.get("anchor_profile_status"),
                "cited_passage_present": bool(str(d.get("counter_evidence") or "").strip()),
            })
        rows_out.append({
            "qid": bundle_qid,
            "bundle_file": str(path.relative_to(REPO_ROOT)),
            "bundle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "anchor_profile": gate["anchor_profile"],
            "n_proposed_labels": gate["n_proposed_labels"],
            "n_emitted": gate["n_emitted"],
            "n_abstained": gate["n_abstained"],
            "abstention_reasons": gate["abstention_reasons"],
            "rows": rows,
        })
    return {
        "schema": "product-counter-label-gate/served-packet-application/1",
        "applied_at": _now(),
        "packet_dir": str(packet_dir.relative_to(REPO_ROOT)),
        "frozen_rules_sha256": FROZEN_RULES_SHA256,
        "rules_rehash_verified": rules.sha256 == FROZEN_RULES_SHA256,
        "component": "frontier-counter-anchor-classifier/decide_label (accepted team run 38964146628)",
        "adopt_mode": "abstain_and_disclose",
        "what_this_is": (
            "the accepted component's own per-row decisions (emitted vs abstained) "
            "applied to the served packet's frozen bundles"
        ),
        "what_this_is_not": (
            "a frozen-rubric support score: scoring label support is Frontier's / "
            "Core Evaluation's job and is NOT recomputed here"
        ),
        "bundles": rows_out,
        "totals": {
            "n_proposed_labels": sum(b["n_proposed_labels"] for b in rows_out),
            "n_emitted": sum(b["n_emitted"] for b in rows_out),
            "n_abstained": sum(b["n_abstained"] for b in rows_out),
        },
        "accepted_reference_measurement": {
            "team_run_id": "38880639079",
            "label_verdict": "LABEL_UNSOUND",
            "n_scored": 65,
            "n_supported": 5,
            "note": (
                "the accepted Frontier measurement of the SAME packet; reported "
                "side by side and never replaced by this application"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--packet", default=str(DEFAULT_PACKET))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--qid", default=None)
    args = ap.parse_args(argv)
    report = apply_packet(Path(args.packet), qid=args.qid)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = report["totals"]
    print(json.dumps({"wrote": str(out), **t}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
