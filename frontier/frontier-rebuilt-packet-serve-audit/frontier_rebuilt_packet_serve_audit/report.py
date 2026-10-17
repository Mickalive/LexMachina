"""Assemble the full audit record (deterministic, offline)."""
from __future__ import annotations

import json
from pathlib import Path

from . import before_after, cross_check, freeze_verify, geometry_half, label_half
from . import marginal_discovery, non_vacuity, verdict
from .paths import DEFAULT_OLD_PACKET_CANDIDATES, QIDS, resolve_packet

SCHEMA = "frontier-rebuilt-packet-serve-audit/report/1"


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
        "non_vacuity": vacuity,
        **before,
        "verdict": recommendation,
        "deterministic": True,
        "network_used": False,
        "threshold_re_derived": False,
        "human_gate_touched": False,
    }
    return record
