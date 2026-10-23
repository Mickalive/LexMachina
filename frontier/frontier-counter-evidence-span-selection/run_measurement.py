#!/usr/bin/env python3
"""Run the frozen counter-evidence span-selection measurement.

Protocol: ``results/frontier/frontier-counter-evidence-span-selection/PROTOCOL.json``
(committed before this file was written).  The run is offline and deterministic:

    baseline  = emission repair -> accepted anchor classifier
    candidate = emission repair -> span selection -> accepted anchor classifier

Every number is published side by side.  The outcome is OUTCOME_A only when the
frozen scorer emits at least one verified quote and both adversarial scorer
controls are strictly below; OUTCOME_B when the candidate emits zero and every
control passes; otherwise VOID.  A tie is never a pass.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import socket
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import scorer_bridge  # noqa: E402
import span_select  # noqa: E402

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
DEFAULT_MOUNT = Path("/tmp/lex_accepted/core/product")
DEFAULT_PROTOCOL = (
    HERE.parents[1]
    / "results"
    / "frontier"
    / "frontier-counter-evidence-span-selection"
    / "PROTOCOL.json"
)
DEFAULT_OUT_DIR = (
    HERE.parents[1]
    / "results"
    / "frontier"
    / "frontier-counter-evidence-span-selection"
)

CLAIM_CEILING = (
    "This component measures whether a deterministic extract-verify-abstain step "
    "over the retrieved full text of already-present candidate counter/limiting "
    "decisions raises the number of counter rows the frozen scorer SUPPORTS, under "
    "the frozen rubric reused by re-hash. It NEVER asserts that any decision IS "
    "supporting, contrary or limiting. It does NOT claim jurist usefulness, serve "
    "readiness, reliability, reproduction of the external 0/14 result, or that the "
    "comparative map-versus-ranked-list question is non-vacuous. It changes no "
    "threshold, rubric, verdict class, absolute bar or packet; it adds no retrieval "
    "and no model call. machine_gate_ready and packet_admitted remain product-owned "
    "and false unless independently earned."
)


class NetworkGuard:
    """Fail-closed socket guard; records any attempted call."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._orig_connect = None
        self._orig_create = None

    def __enter__(self) -> "NetworkGuard":
        self._orig_connect = socket.socket.connect
        self._orig_create = socket.create_connection

        def blocked_connect(sock, address):
            self.calls.append(f"connect:{address!r}")
            raise RuntimeError("NETWORK DISABLED by span-selection measurement")

        def blocked_create(address, *args, **kwargs):
            self.calls.append(f"create_connection:{address!r}")
            raise RuntimeError("NETWORK DISABLED by span-selection measurement")

        socket.socket.connect = blocked_connect  # type: ignore[assignment]
        socket.create_connection = blocked_create  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        if self._orig_connect is not None:
            socket.socket.connect = self._orig_connect  # type: ignore[assignment]
        if self._orig_create is not None:
            socket.create_connection = self._orig_create  # type: ignore[assignment]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_protocol(path: Path) -> tuple[dict[str, Any], str, str, bool]:
    payload = path.read_bytes()
    protocol = json.loads(payload.decode("utf-8"))
    digest = hashlib.sha256(payload).hexdigest()
    sha_path = path.with_name("PROTOCOL.sha256")
    expected = ""
    if sha_path.is_file():
        expected = sha_path.read_text(encoding="utf-8").split()[0]
    return protocol, digest, expected, (digest == expected)


def baseline_checks(protocol: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected = protocol["population"]
    checks: list[dict[str, Any]] = []
    for qid in QIDS:
        got = actual[qid]
        for field, exp_key in (
            ("n_scored", "expected_n_scored"),
            ("n_abstained", "expected_n_abstained"),
            ("n_emitted", "expected_n_emitted"),
        ):
            want = expected[exp_key][qid]
            checks.append({
                "qid": qid,
                "field": field,
                "expected": want,
                "actual": got[field],
                "pass": got[field] == want,
            })
        want_support = expected["expected_support_rate_among_emitted"][qid]
        checks.append({
            "qid": qid,
            "field": "support_rate_among_emitted",
            "expected": want_support,
            "actual": got["support_rate_among_emitted"],
            "pass": got["support_rate_among_emitted"] == want_support,
        })
        checks.append({
            "qid": qid,
            "field": "abstention_reasons",
            "expected": expected["expected_abstention_reasons"][qid],
            "actual": got["abstention_reasons"],
            "pass": got["abstention_reasons"] == expected["expected_abstention_reasons"][qid],
        })
        checks.append({
            "qid": qid,
            "field": "emitted_ids",
            "expected": [],
            "actual": got["emitted_ids"],
            "pass": got["emitted_ids"] == [],
        })
        checks.append({
            "qid": qid,
            "field": "n_promoted",
            "expected": expected["expected_n_scored"][qid],
            "actual": got["n_promoted"],
            "pass": got["n_promoted"] == expected["expected_n_scored"][qid],
        })
    overall_expected = expected["expected_n_scored"]["overall"]
    overall_scored = sum(actual[q]["n_scored"] for q in QIDS)
    checks.append({
        "qid": "overall",
        "field": "n_scored",
        "expected": overall_expected,
        "actual": overall_scored,
        "pass": overall_scored == overall_expected,
    })
    return {"ok": all(c["pass"] for c in checks), "checks": checks, "actual": actual}


def candidate_checks(
    protocol: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    row_details: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    denominator = []
    for qid in QIDS:
        b = baseline[qid]["summary"]
        c = candidate[qid]["summary"]
        expected = protocol["population"]["expected_n_scored"][qid]
        denominator.append({
            "qid": qid,
            "baseline_n_scored": b["n_scored"],
            "candidate_n_scored": c["n_scored"],
            "expected_n_scored": expected,
            "pass": b["n_scored"] == c["n_scored"] == expected,
        })
    verbatim_failures = []
    for qid, details in row_details.items():
        for d in details:
            if d["counter_status_after"] in span_select.SCORED_STATUSES:
                if not d["quote_verbatim_in_full_text"]:
                    verbatim_failures.append({
                        "qid": qid,
                        "decision_id": d["decision_id"],
                        "reason": "emitted_quote_not_verbatim",
                    })
                if not d["counter_evidence_equals_quote"]:
                    verbatim_failures.append({
                        "qid": qid,
                        "decision_id": d["decision_id"],
                        "reason": "counter_evidence_not_equal_to_selected_quote",
                    })
                if d["counter_reason_code"] != "supported":
                    verbatim_failures.append({
                        "qid": qid,
                        "decision_id": d["decision_id"],
                        "reason": f"emitted_with_non_supported_reason:{d['counter_reason_code']}",
                    })
    return {
        "denominator_ok": all(d["pass"] for d in denominator),
        "denominator": denominator,
        "verbatim_ok": not verbatim_failures,
        "verbatim_failures": verbatim_failures,
    }


def aggregate_controls(controls: dict[str, Any]) -> dict[str, Any]:
    swapped = sum(v["n_emitted"] for v in controls["swapped"].values())
    inverted = sum(v["n_emitted"] for v in controls["inverted"].values())
    return {
        "n_emitted_swapped": swapped,
        "n_emitted_inverted": inverted,
        "swapped_all_zero": swapped == 0,
        "inverted_all_zero": inverted == 0,
    }


def determine_outcome(
    *,
    protocol_sha_ok: bool,
    input_hashes_ok: bool,
    baseline_ok: bool,
    denominator_ok: bool,
    verbatim_ok: bool,
    injection_ok: bool,
    seeded_ok: bool,
    baseline_n_emitted: int,
    candidate_n_emitted: int,
    candidate_n_evidenced: int,
    candidate_support_rate: float,
    control_n_emitted_swapped: int,
    control_n_emitted_inverted: int,
) -> tuple[str, str, dict[str, bool]]:
    controls_strictly_below = (
        control_n_emitted_swapped < candidate_n_emitted
        and control_n_emitted_inverted < candidate_n_emitted
    )
    controls_at_zero = control_n_emitted_swapped == 0 and control_n_emitted_inverted == 0
    preconditions = protocol_sha_ok and input_hashes_ok and baseline_ok
    conditions = {
        "protocol_sha_ok": protocol_sha_ok,
        "input_hashes_ok": input_hashes_ok,
        "baseline_reproduced": baseline_ok,
        "denominator_unchanged": denominator_ok,
        "verbatim_quotes_only": verbatim_ok,
        "seeded_positive_1_and_negative_0": seeded_ok,
        "frozen_injection_rows_match": injection_ok,
        "candidate_emitted_above_baseline": candidate_n_emitted > baseline_n_emitted,
        "candidate_emitted_at_least_1": candidate_n_emitted >= 1,
        "candidate_evidenced_at_least_1": candidate_n_evidenced >= 1,
        "candidate_support_among_emitted_1": candidate_support_rate == 1.0,
        "scorer_controls_strictly_below_candidate": controls_strictly_below,
        "scorer_controls_at_zero": controls_at_zero,
        "candidate_control_tie_at_zero": (
            candidate_n_emitted == 0
            and control_n_emitted_swapped == 0
            and control_n_emitted_inverted == 0
        ),
    }
    if not preconditions:
        return "VOID", "protocol/input/baseline precondition failed", conditions
    if not denominator_ok:
        return "VOID", "candidate denominator changed", conditions
    if not verbatim_ok:
        return "VOID", "a candidate quote was not verbatim or was not supported", conditions
    if not injection_ok:
        return "VOID", "frozen non-vacuity injection rows did not match", conditions
    if not seeded_ok:
        return "VOID", "seeded positive/negative control failed", conditions

    if candidate_n_emitted > 0:
        a_ok = (
            candidate_n_emitted >= 1
            and candidate_n_evidenced >= 1
            and candidate_support_rate == 1.0
            and candidate_n_emitted > baseline_n_emitted
            and controls_strictly_below
        )
        if a_ok:
            return (
                "A_COMPONENT_EVIDENCE_RECOVERED",
                (
                    f"candidate emitted {candidate_n_emitted} verified counter row(s) "
                    f"({candidate_n_evidenced} evidenced) above baseline "
                    f"{baseline_n_emitted}; swapped={control_n_emitted_swapped}, "
                    f"inverted={control_n_emitted_inverted}, both strictly below"
                ),
                conditions,
            )
        return (
            "VOID",
            (
                "candidate emitted rows but a success condition failed: "
                f"candidate={candidate_n_emitted}, evidenced={candidate_n_evidenced}, "
                f"support={candidate_support_rate}, swapped={control_n_emitted_swapped}, "
                f"inverted={control_n_emitted_inverted}"
            ),
            conditions,
        )

    # candidate_n_emitted == 0
    if controls_at_zero:
        return (
            "B_BOUNDED_NEGATIVE",
            (
                "candidate emitted 0 verified counter rows; the scorer controls also "
                "emitted 0, so candidate_control_tie is recorded at zero and is NEVER "
                "a pass. The defect is relocated to retrieval/candidate quality for "
                "these already-retrieved decisions."
            ),
            conditions,
        )
    return (
        "VOID",
        (
            "candidate emitted 0 but a scorer control emitted rows "
            f"(swapped={control_n_emitted_swapped}, inverted={control_n_emitted_inverted}); "
            "not a clean bounded negative"
        ),
        conditions,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mount", type=Path, default=DEFAULT_MOUNT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-label", default="primary")
    args = parser.parse_args(argv)

    protocol, protocol_sha, protocol_sha_expected, protocol_sha_ok = load_protocol(
        args.protocol
    )
    inputs = protocol["inputs"]
    primary_packet_dir = Path(inputs["packet_of_record"]["path_prefix"])
    served_packet_dir = Path(inputs["served_packet_secondary"]["path_prefix"])
    limits = protocol["span_rule"]["limits"]
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    with NetworkGuard() as guard:
        input_verification = scorer_bridge.verify_input_hashes(protocol, args.mount)
        modules = scorer_bridge.load_product_modules(args.mount)
        decide_label, _load_rules = scorer_bridge.load_classifier(args.mount)
        rules = scorer_bridge.load_rules_verified(
            args.mount, inputs["frozen_rules"]["sha256"]
        )

        # --- baseline reproduction ---
        baseline: dict[str, Any] = {}
        bundles: dict[str, dict[str, Any]] = {}
        for qid in QIDS:
            bundle = scorer_bridge.load_bundle(primary_packet_dir, qid)
            bundles[qid] = bundle
            baseline[qid] = scorer_bridge.run_baseline(bundle, qid, modules)
        baseline_summaries = {qid: baseline[qid]["summary"] for qid in QIDS}
        baseline_check = baseline_checks(protocol, baseline_summaries)
        write_json(
            out_dir / "BASELINE.json",
            {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                "protocol_sha256_expected": protocol_sha_expected,
                "protocol_sha_ok": protocol_sha_ok,
                "input_verification": input_verification,
                "baseline": baseline_summaries,
                "promoted_rows": {
                    qid: [
                        {
                            "decision_id": r.get("decision_id"),
                            "proposed_status": r.get("counter_status"),
                            "evidence_len": len(str(r.get("counter_evidence") or "")),
                            "full_text_len": len(str(r.get("full_text") or "")),
                            "full_text_status": r.get("full_text_status"),
                            "language": r.get("language"),
                            "legal_area": r.get("legal_area"),
                        }
                        for r in baseline[qid]["promoted_rows"]
                    ]
                    for qid in QIDS
                },
                "checks": baseline_check["checks"],
                "pass": baseline_check["ok"],
            },
        )

        if not (protocol_sha_ok and input_verification["ok"] and baseline_check["ok"]):
            outcome = "VOID"
            reason = []
            if not protocol_sha_ok:
                reason.append("PROTOCOL.sha256 does not match PROTOCOL.json")
            if not input_verification["ok"]:
                reason.append("frozen input hash mismatch")
            if not baseline_check["ok"]:
                reason.append("accepted baseline not reproduced")
            measurement = {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                "outcome": outcome,
                "verdict_reason": "; ".join(reason),
                "baseline_checks": baseline_check,
                "input_verification": input_verification,
                "claim_ceiling": CLAIM_CEILING,
                "forbidden_claims": protocol["success_rule"]["forbidden_claims"],
                "network_calls": guard.calls,
            }
            write_json(out_dir / "MEASUREMENT.json", measurement)
            print(json.dumps({
                "outcome": outcome,
                "reason": measurement["verdict_reason"],
            }, ensure_ascii=False))
            return 2

        # --- candidate ---
        candidate: dict[str, Any] = {}
        row_details: dict[str, list[dict[str, Any]]] = {}
        for qid in QIDS:
            profile = rules.anchor_profile(qid)
            candidate[qid] = scorer_bridge.run_candidate(
                bundles[qid], qid, modules, rules, profile,
                min_chars=int(limits["min_span_chars"]),
                max_chars=int(limits["max_span_chars"]),
                max_units=int(limits["max_window_units"]),
            )
            row_details[qid] = scorer_bridge.row_details(
                candidate[qid]["final_bundle"], candidate[qid]["span_decisions"]
            )
        candidate_summaries = {qid: candidate[qid]["summary"] for qid in QIDS}
        candidate_check = candidate_checks(
            protocol, baseline, candidate, row_details
        )
        write_json(
            out_dir / "CANDIDATE.json",
            {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                "candidate": candidate_summaries,
                "row_details": row_details,
                "denominator_check": candidate_check["denominator"],
                "denominator_ok": candidate_check["denominator_ok"],
                "verbatim_ok": candidate_check["verbatim_ok"],
                "verbatim_failures": candidate_check["verbatim_failures"],
            },
        )

        # --- controls ---
        donor_bundles = {qid: bundles[qid] for qid in QIDS}
        controls: dict[str, Any] = {
            "verbatim_mutated": {},
            "verbatim_cross_decision": {},
            "swapped": {},
            "inverted": {},
            "seeded": {},
            "injection": {},
        }
        for qid in QIDS:
            final_bundle = candidate[qid]["final_bundle"]
            selected_bundle = candidate[qid]["selected_bundle"]
            decisions = candidate[qid]["span_decisions"]
            emitted_ids = candidate_summaries[qid]["emitted_ids"]

            mutated_records = []
            for dec in decisions:
                if not dec.evidenced:
                    continue
                row = next(
                    (
                        d for d in final_bundle.get("decisions") or []
                        if str(d.get("decision_id") or "") == dec.decision_id
                    ),
                    {},
                )
                mutated = scorer_bridge.mutate_quote(dec.quote)
                rejected = not span_select.verify_span(
                    str(row.get("full_text") or ""), mutated, dec.char_start, dec.char_end
                )
                mutated_records.append({
                    "decision_id": dec.decision_id,
                    "mutated_quote_rejected": rejected,
                })
            controls["verbatim_mutated"][qid] = {
                "n_checked": len(mutated_records),
                "all_rejected": all(r["mutated_quote_rejected"] for r in mutated_records),
                "records": mutated_records,
            }

            controls["verbatim_cross_decision"][qid] = (
                scorer_bridge.cross_decision_verbatim_controls(
                    final_bundle, decisions, donor_bundles, qid
                )
            )

            donor_quotes: dict[str, str] = {}
            donor_meta: dict[str, Any] = {}
            for did in emitted_ids:
                row = next(
                    (
                        d for d in selected_bundle.get("decisions") or []
                        if str(d.get("decision_id") or "") == did
                    ),
                    {},
                )
                donor = scorer_bridge.find_non_occurring_donor_quote(
                    row, qid, donor_bundles
                )
                donor_quotes[did] = donor["quote"]
                donor_meta[did] = donor
            controls["swapped"][qid] = scorer_bridge.run_swapped_control(
                selected_bundle, qid, emitted_ids, donor_quotes, modules
            )
            controls["swapped"][qid]["donors"] = donor_meta
            controls["inverted"][qid] = scorer_bridge.run_inverted_control(
                selected_bundle, qid, emitted_ids, modules
            )

        controls["injection"] = scorer_bridge.score_injection_rows(rules, decide_label)
        controls["seeded"] = scorer_bridge.run_seeded_controls(
            rules, modules,
            min_chars=int(limits["min_span_chars"]),
            max_chars=int(limits["max_span_chars"]),
            max_units=int(limits["max_window_units"]),
        )
        aggregate = aggregate_controls(controls)
        controls["aggregate"] = aggregate
        write_json(
            out_dir / "CONTROLS.json",
            {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                **controls,
            },
        )

        # --- determinism: full candidate rerun ---
        rerun: dict[str, Any] = {}
        for qid in QIDS:
            profile = rules.anchor_profile(qid)
            rerun[qid] = scorer_bridge.run_candidate(
                bundles[qid], qid, modules, rules, profile,
                min_chars=int(limits["min_span_chars"]),
                max_chars=int(limits["max_span_chars"]),
                max_units=int(limits["max_window_units"]),
            )
        hash1 = scorer_bridge.canonical_sha256({
            qid: {
                "summary": candidate[qid]["summary"],
                "rows": row_details[qid],
                "span_decisions": [
                    d.to_dict() for d in candidate[qid]["span_decisions"]
                ],
            }
            for qid in QIDS
        })
        hash2 = scorer_bridge.canonical_sha256({
            qid: {
                "summary": rerun[qid]["summary"],
                "rows": scorer_bridge.row_details(
                    rerun[qid]["final_bundle"], rerun[qid]["span_decisions"]
                ),
                "span_decisions": [
                    d.to_dict() for d in rerun[qid]["span_decisions"]
                ],
            }
            for qid in QIDS
        })
        write_json(
            out_dir / "DETERMINISM.json",
            {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                "n_runs": 2,
                "run_1_sha256": hash1,
                "run_2_sha256": hash2,
                "identical": hash1 == hash2,
                "note": "Full candidate rerun on identical frozen inputs; no clock, randomness or network.",
            },
        )

        # --- served-packet secondary replication (never decides the verdict) ---
        served: dict[str, Any] = {}
        for qid in QIDS:
            try:
                bundle = scorer_bridge.load_bundle(served_packet_dir, qid)
            except FileNotFoundError as exc:
                served[qid] = {"error": str(exc)}
                continue
            base = scorer_bridge.run_baseline(bundle, qid, modules)
            cand = scorer_bridge.run_candidate(
                bundle, qid, modules, rules, rules.anchor_profile(qid),
                min_chars=int(limits["min_span_chars"]),
                max_chars=int(limits["max_span_chars"]),
                max_units=int(limits["max_window_units"]),
            )
            served[qid] = {
                "baseline": base["summary"],
                "candidate": cand["summary"],
                "candidate_emitted_ids": cand["summary"]["emitted_ids"],
                "candidate_row_details": scorer_bridge.row_details(
                    cand["final_bundle"], cand["span_decisions"]
                ),
            }
        write_json(
            out_dir / "SERVED_PACKET_SECONDARY.json",
            {
                "run_label": args.run_label,
                "protocol_sha256": protocol_sha,
                "packet": inputs["served_packet_secondary"]["packet_id"],
                "role": "secondary replication only; never the deciding population",
                **served,
            },
        )

        # --- outcome ---
        baseline_n_emitted = sum(baseline_summaries[q]["n_emitted"] for q in QIDS)
        candidate_n_emitted = sum(candidate_summaries[q]["n_emitted"] for q in QIDS)
        candidate_n_evidenced = sum(
            1
            for q in QIDS
            for d in row_details[q]
            if d["span"]["evidenced"]
            and d["counter_status_after"] in span_select.SCORED_STATUSES
            and d["quote_verbatim_in_full_text"]
            and d["counter_reason_code"] == "supported"
        )
        emitted_supported = sum(
            1
            for q in QIDS
            for d in row_details[q]
            if d["counter_status_after"] in span_select.SCORED_STATUSES
            and d["counter_reason_code"] == "supported"
        )
        candidate_support_rate = (
            emitted_supported / candidate_n_emitted
            if candidate_n_emitted > 0
            else 0.0
        )
        injection_ok = bool(controls["injection"]["pass"])
        seeded_ok = bool(
            controls["seeded"]["positive"]["pass"]
            and controls["seeded"]["negative"]["pass"]
        )
        outcome, verdict_reason, conditions = determine_outcome(
            protocol_sha_ok=protocol_sha_ok,
            input_hashes_ok=bool(input_verification["ok"]),
            baseline_ok=bool(baseline_check["ok"]),
            denominator_ok=bool(candidate_check["denominator_ok"]),
            verbatim_ok=bool(candidate_check["verbatim_ok"]),
            injection_ok=injection_ok,
            seeded_ok=seeded_ok,
            baseline_n_emitted=baseline_n_emitted,
            candidate_n_emitted=candidate_n_emitted,
            candidate_n_evidenced=candidate_n_evidenced,
            candidate_support_rate=candidate_support_rate,
            control_n_emitted_swapped=int(aggregate["n_emitted_swapped"]),
            control_n_emitted_inverted=int(aggregate["n_emitted_inverted"]),
        )
        measurement = {
            "run_label": args.run_label,
            "protocol_sha256": protocol_sha,
            "protocol_sha256_expected": protocol_sha_expected,
            "outcome": outcome,
            "verdict_reason": verdict_reason,
            "side_by_side": {
                "baseline_n_scored": sum(baseline_summaries[q]["n_scored"] for q in QIDS),
                "baseline_n_abstained": sum(baseline_summaries[q]["n_abstained"] for q in QIDS),
                "baseline_n_emitted": baseline_n_emitted,
                "candidate_n_scored": sum(candidate_summaries[q]["n_scored"] for q in QIDS),
                "candidate_n_abstained": sum(candidate_summaries[q]["n_abstained"] for q in QIDS),
                "candidate_n_emitted": candidate_n_emitted,
                "candidate_n_evidenced": candidate_n_evidenced,
                "candidate_n_emitted_supported": emitted_supported,
                "candidate_support_rate_among_emitted": candidate_support_rate,
                "candidate_yield": (
                    candidate_n_emitted
                    / max(1, sum(candidate_summaries[q]["n_scored"] for q in QIDS))
                ),
                "control_n_emitted_swapped": aggregate["n_emitted_swapped"],
                "control_n_emitted_inverted": aggregate["n_emitted_inverted"],
                "seeded_positive_emitted": controls["seeded"]["positive"]["n_emitted"],
                "seeded_negative_emitted": controls["seeded"]["negative"]["n_emitted"],
            },
            "per_qid": {
                "baseline": baseline_summaries,
                "candidate": candidate_summaries,
            },
            "conditions": conditions,
            "candidate_checks": candidate_check,
            "controls": {
                "aggregate": aggregate,
                "injection_pass": injection_ok,
                "seeded_ok": seeded_ok,
                "verbatim_mutated_all_rejected": all(
                    controls["verbatim_mutated"][q]["all_rejected"] for q in QIDS
                ),
                "verbatim_cross_decision_all_rejected": all(
                    controls["verbatim_cross_decision"][q]["all_donors_rejected"]
                    for q in QIDS
                ),
            },
            "input_verification": input_verification,
            "determinism": {
                "run_1_sha256": hash1,
                "run_2_sha256": hash2,
                "identical": hash1 == hash2,
            },
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "network_calls": guard.calls,
                "mount": str(args.mount),
                "mount_head": input_verification.get("mount_head"),
                "offline": True,
            },
            "claim_ceiling": CLAIM_CEILING,
            "forbidden_claims": protocol["success_rule"]["forbidden_claims"],
            "artifacts": {
                "protocol": str(args.protocol),
                "protocol_sha256": str(args.protocol.with_name("PROTOCOL.sha256")),
                "baseline": str(out_dir / "BASELINE.json"),
                "candidate": str(out_dir / "CANDIDATE.json"),
                "controls": str(out_dir / "CONTROLS.json"),
                "determinism": str(out_dir / "DETERMINISM.json"),
                "served_packet_secondary": str(out_dir / "SERVED_PACKET_SECONDARY.json"),
            },
        }
        write_json(out_dir / "MEASUREMENT.json", measurement)
        print(json.dumps({
            "outcome": outcome,
            "reason": verdict_reason,
            "side_by_side": measurement["side_by_side"],
            "determinism_identical": hash1 == hash2,
        }, ensure_ascii=False, indent=2))
        return 0 if outcome in ("A_COMPONENT_EVIDENCE_RECOVERED", "B_BOUNDED_NEGATIVE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
