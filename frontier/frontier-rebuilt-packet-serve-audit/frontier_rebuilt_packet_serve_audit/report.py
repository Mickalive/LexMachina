"""Assemble the full audit record (deterministic, offline).

The record also publishes PROCESS_RULES: the claim-verification disciplines that
bind this team's own absence claims (audit FIX-4) and its reproduction/sha-pin
claims (audit CYCLE_39056749213 FIX-1). No clock, randomness or network input
enters the record, so two runs on the same bytes are byte-identical.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import before_after, cross_check, freeze_verify, geometry_half, label_half
from . import marginal_discovery, non_vacuity, verdict
from .paths import DEFAULT_OLD_PACKET_CANDIDATES, QIDS, resolve_packet

SCHEMA = "frontier-rebuilt-packet-serve-audit/report/1"

# PROCESS RULES published inside the record (audit CYCLE_39056749213 FIX-1
# extends the round-1 FIX-4 rule to reproduction/sha-pinning claims). These are
# constant strings: the record stays deterministic and clock-free.
PROCESS_RULES = {
    "absence_and_negativity_claims": cross_check.EVAL_RESCORE_SEARCH_BASIS["process_rule"],
    "reproduction_and_sha_pin_claims": (
        "Any byte-identical-reproduction claim or published sha256 pin over a "
        "claim-bearing artifact must be re-verified at the FINAL attempt, AFTER the "
        "last code edit of the cycle and BEFORE promotion: regenerate the artifact "
        "with the SHIPPED harness via the INTEGRATION_CONTRACT.json "
        "reproduction.command recipe, obtain the sha256 from two consecutive fresh "
        "runs that are byte-identical to each other AND to the published artifact, "
        "and only then pin it in REPRODUCTION.json, INTEGRATION_CONTRACT.json, "
        "REPORT.md and the state file. A published sha the shipped harness cannot "
        "reproduce is a false claim, never evidence. A subsequent produced-work "
        "cycle shipping a published-record sha its own shipped harness/recipe "
        "cannot reproduce (this same defect class) gates BLOCKED under the "
        "recurring-repair rule, not a further REVISE (audit FIX-1 of "
        "CYCLE_39056749213)."
    ),
}


def run_audit(packet_dir: Path | None, old_packet_dir: Path | None,
              k: int = marginal_discovery.FROZEN_K,
              evaluation_rescore_paths=None) -> dict:
    packet_dir = resolve_packet(str(packet_dir) if packet_dir else None)
    if old_packet_dir is None:
        old_packet_dir = next((c for c in DEFAULT_OLD_PACKET_CANDIDATES if (c / "packet.json").is_file()), None)
    freeze = freeze_verify.load_freeze()
    freeze_verification = freeze_verify.verify_all(packet_dir, old_packet_dir, freeze)
    questions = packet_dir / "questions"
    half_a = label_half.measure(questions)
    half_b = geometry_half.measure(questions)
    half_c = marginal_discovery.measure(questions, k=k)
    cross = cross_check.build(half_a, half_b, packet_dir / "packet.json",
                              evaluation_rescore_paths=evaluation_rescore_paths)
    vacuity = non_vacuity.run_all(
        questions,
        old_questions=(old_packet_dir / "questions") if old_packet_dir is not None else None,
        real_halves={"half_a": half_a, "half_b": half_b, "half_c": half_c},
    )
    before = (
        before_after.measure(old_packet_dir / "questions", questions)
        if old_packet_dir is not None
        else {"before_after": {"status": "OLD_PACKET_NOT_MOUNTED"}}
    )
    recommendation = verdict.resolve(half_a, half_b, half_c)
    record = {
        "schema": SCHEMA,
        "team_id": "frontier-rebuilt-packet-serve-audit",
        "charter_version": 3,
        "packet_dir": str(packet_dir),
        "packet_json_sha256": freeze_verification["packet"]["packet.json"]["observed_sha256"],
        "freeze_verification": freeze_verification,
        "half_a_label": half_a,
        "half_b_geometry": half_b,
        "half_c_marginal_discovery": half_c,
        "cross_check": cross,
        "process_rules": PROCESS_RULES,
        "non_vacuity": vacuity,
        **before,
        "verdict": recommendation,
        "deterministic": True,
        "network_used": False,
        "threshold_re_derived": False,
        "human_gate_touched": False,
    }
    return record
