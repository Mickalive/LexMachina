#!/usr/bin/env python3
"""Measure verbatim counter-evidence span selection on packet-of-record v3.

Baseline is the accepted chain: emission repair -> frozen anchor classifier.
Candidate inserts the product-owned span selector before emission repair.  Two
candidate arms are measured: ``unguarded`` (gate only) and ``guarded`` (gate +
profile-statute/exact-query-phrase anchor).  The guarded arm is the shipped
default; the unguarded arm is kept as a diagnostic so the precision cost of the
guard is auditable rather than asserted.

Both arms are deterministic pure functions of the committed bundle bytes.  The
report publishes support-among-emitted, abstention count and yield side by side;
it makes NO serve/admission claim and does not run the evaluation scorer.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from product.query.counter_anchor import apply_anchor_labels, load_frozen_rules
from product.query.counter_emission_repair import apply_counter_emission_repair
from product.query.counter_evidence_span import (
    SPAN_VERSION,
    TEXT_FIELDS,
    apply_verified_span_selection,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
QIDS = {
    "de-kapitalverletzung": "de-kapitalverletzung",
    "fr-bail-entretien": "fr-bail-entretien",
    "it-responsabilita-medica": "it-responsabilita-medica",
}
DEFAULT_OUT = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "CYCLE_39986094168_span_selection.json"
)


def _quote_verbatim(row: dict) -> bool:
    quote = str(row.get("counter_evidence") or "")
    if not quote:
        return False
    return any(quote in str(row.get(field) or "") for field in TEXT_FIELDS)


def _summarise(bundle: dict) -> dict:
    prov = (bundle.get("provenance") or {}).get("counter_anchor") or {}
    emitted_ids = list(prov.get("emitted_ids") or [])
    by_id = {str(d.get("decision_id")): d for d in bundle.get("decisions") or []}
    emitted_rows = [by_id.get(i, {}) for i in emitted_ids]
    abstained = [
        d for d in bundle.get("decisions") or []
        if str(d.get("counter_status") or "") == "abstained_unevidenced"
    ]
    span_prov = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
    return {
        "n_scored": int(prov.get("n_scored") or 0),
        "n_emitted": int(prov.get("n_emitted") or 0),
        "n_abstained": int(prov.get("n_abstained") or 0),
        "support_rate_among_emitted": prov.get("support_rate_among_emitted"),
        "yield": prov.get("yield"),
        "abstention_reasons": prov.get("abstention_reasons") or {},
        "emitted_ids": emitted_ids,
        "n_emitted_verified": sum(
            1 for d in emitted_rows if d.get("counter_evidence_verified") is True
        ),
        "n_emitted_verbatim": sum(1 for d in emitted_rows if _quote_verbatim(d)),
        "span_selection": {
            "applied": span_prov.get("applied"),
            "n_candidates": span_prov.get("n_candidates"),
            "n_selected": span_prov.get("n_selected"),
            "n_abstained": span_prov.get("n_abstained"),
            "n_sentences_evaluated": span_prov.get("n_sentences_evaluated"),
            "abstention_reasons": span_prov.get("abstention_reasons") or {},
            "precision_guard": span_prov.get("precision_guard"),
            "guard_available": span_prov.get("guard_available"),
            "guard_statutes": span_prov.get("guard_statutes") or [],
            "guard_phrase_count": span_prov.get("guard_phrase_count"),
            "n_guard_rejected": span_prov.get("n_guard_rejected"),
        },
        "emitted": [
            {
                "decision_id": str(d.get("decision_id") or ""),
                "counter_status": d.get("counter_status"),
                "counter_evidence": d.get("counter_evidence"),
                "counter_evidence_verified": d.get("counter_evidence_verified"),
                "evidence_verbatim": _quote_verbatim(d),
            }
            for d in emitted_rows
        ],
        "visible_abstained_rows": len(abstained),
    }


def measure_bundle(path: Path, qid: str) -> dict:
    source = json.loads(path.read_text(encoding="utf-8"))
    baseline = apply_anchor_labels(
        apply_counter_emission_repair(copy.deepcopy(source)), qid=qid
    )
    arms = {}
    for name, guard_mode in (("candidate_unguarded", "off"), ("candidate", "on")):
        arms[name] = apply_anchor_labels(
            apply_counter_emission_repair(
                apply_verified_span_selection(
                    copy.deepcopy(source),
                    qid=qid,
                    mode="select",
                    env={**dict(__import__("os").environ),
                         "LEXMACHINA_COUNTER_SPAN_GUARD": guard_mode},
                )
            ),
            qid=qid,
        )
    b = _summarise(baseline)
    out = {
        "qid": qid,
        "bundle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "baseline": b,
    }
    for name, bundle in arms.items():
        c = _summarise(bundle)
        out[name] = c
        out[f"delta_{name}"] = {
            "n_emitted": c["n_emitted"] - b["n_emitted"],
            "n_emitted_verified": c["n_emitted_verified"] - b["n_emitted_verified"],
            "n_emitted_verbatim": c["n_emitted_verbatim"] - b["n_emitted_verbatim"],
            "yield": None if b["yield"] is None else round(c["yield"] - b["yield"], 6),
        }
    return out


def run() -> dict:
    rules, digest = load_frozen_rules()
    bundles = {}
    for slug, qid in QIDS.items():
        bundles[slug] = measure_bundle(PACKET / f"{slug}.bundle.json", qid)
    sums = {}
    for arm in ("baseline", "candidate_unguarded", "candidate"):
        sums[arm] = {
            key: sum(b[arm][key] for b in bundles.values())
            for key in ("n_scored", "n_emitted", "n_abstained",
                        "n_emitted_verified", "n_emitted_verbatim")
        }
        n_scored = sums[arm]["n_scored"]
        n_emitted = sums[arm]["n_emitted"]
        sums[arm]["yield"] = round(n_emitted / n_scored, 6) if n_scored else 0.0
        sums[arm]["support_rate_among_emitted"] = 1.0 if n_emitted else 0.0
    return {
        "cycle": "direction_v65_counter_span_selection",
        "packet": "39319405429",
        "span_version": SPAN_VERSION,
        "frozen_rules_sha256": digest,
        "bundles": bundles,
        "aggregate": sums,
        "claim_ceiling": (
            "Verbatim span selection + the accepted frozen confirm-or-abstain gate. "
            "The shipped candidate arm also requires a profile statute or exact "
            "query phrase; the unguarded arm is a diagnostic, not a product claim. "
            "Support rate, abstention count and yield are published together. This "
            "measurement makes no serve/admission claim and does not run the "
            "evaluation scorer; it never asserts that a decision IS supporting, "
            "contrary or limiting."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    report = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"out": str(args.out), "aggregate": report["aggregate"]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
