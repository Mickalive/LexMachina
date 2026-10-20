#!/usr/bin/env python3
"""Serve-verdict intake for the packet-of-record: a machine gate input, never an owner card.

Why this module exists
----------------------
Factory direction v59, product ordered work (1) and note (b):

  * the independent serve audit on packet-of-record V3's exact bytes is
    chartered to ``frontier-packet-serve-audit``;
  * *when the serve audit's accepted verdict lands, this lane's posture is
    unchanged by it* — the frozen bars stay REPORTED-ONLY and the verdict is
    consumed as a **machine gate input of packet admission**, never as an
    owner card.

Until that verdict lands, product must still leave a runnable, fail-closed
path: packet admission can disclose ``PENDING_VERDICT`` and cannot open on
narrative.  This module is the product-owned seam that makes both states
machine-readable without re-measuring anything.

What this module does
---------------------
1. Pins the packet-of-record V3 by path and raw ``packet.json`` sha256
   (``32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70``).
2. Reads the product-owned serve-verdict snapshot under
   ``results/product/frontier_verdicts/`` (committed; admission never depends
   on a CI mount being present).
3. Exposes ``current_status()`` / ``assess_for_packet()`` for packet admission.
4. Provides ``harvest()`` so a future accepted verdict is snapshotted once,
   with provenance, without overwriting historical claim-bearing bytes.

What this module never does
---------------------------
* never re-derives a frozen rubric, bar or threshold;
* never sets ``human_gate_ready``, ``ready_for_owner_session`` or an owner card;
* never converts a serve recommendation into owner-readiness by itself;
* never edits packet bytes or a DO-NOT-SERVE order that already stands.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Product-owned snapshots of accepted (or pending) serve verdicts.
SNAPSHOT_DIR = REPO_ROOT / "results" / "product" / "frontier_verdicts"

#: The current intake record for frontier-packet-serve-audit.  Committed from
#: the first cycle so admission can disclose PENDING without a mount.
INTAKE_PATH = SNAPSHOT_DIR / "frontier-packet-serve-audit_intake.json"

#: Packet-of-record V3 — the ONLY serve-audit target until a product repair
#: supersedes it with an accepted successor (then rebind by content_sha256).
PACKET_OF_RECORD_V3 = {
    "team_id": "frontier-packet-serve-audit",
    "packet_run_id": "39319405429",
    "packet_dir": "results/product/gate_packet/39319405429",
    "packet_json": "results/product/gate_packet/39319405429/packet.json",
    "packet_json_raw_sha256": (
        "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
    ),
    "manifest_sha256": (
        "8ea3c92d11e915bcea98b3bc1bd80724b08e920c6ff3bdcade18ed39db388bb7"
    ),
}

#: Charter-1 portfolio status observed at this cycle's dispatch (v59).
#: The team branch exists; no independent serve verdict has been produced.
CHARTER_OBSERVED = {
    "charter_version": 1,
    "portfolio_status_at_observation": "RUN",
    "team_state_cycle_status": "INITIALIZED",
    "accepted_run_id": None,
    "accepted_commit": None,
    "accepted_mount_observed": (
        "/tmp/lex_accepted/frontier/frontier-packet-serve-audit is a bootstrap "
        "tree with state INITIALIZED and no results/serve verdict artifacts"
    ),
}

SCHEMA = "product-serve-verdict-intake/packet-of-record/1"

#: Recommendations that keep a packet unservable as-is.
DO_NOT_SERVE_RECS = frozenset({
    "DO-NOT-SERVE",
    "DO-NOT-SERVE-UNCHANGED",
    "DO-NOT-SERVE-AS-IS",
})

#: The single recommendation that may replace a standing DO-NOT-SERVE order
#: under supersession condition (a).  Even then, product admission still needs
#: both frozen bars met; this flag alone never opens the owner gate.
SERVE_RECS = frozenset({"SERVE", "SERVE-CHANGED", "BOUNDED-NEGATIVE"})


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return str(path)


def packet_sha256_on_disk() -> str | None:
    return _sha256_file(REPO_ROOT / PACKET_OF_RECORD_V3["packet_json"])


def default_intake() -> dict[str, Any]:
    """The committed intake snapshot (pending or harvested)."""
    snap = _read_json(INTAKE_PATH)
    if snap is not None:
        return snap
    # Fail-closed synthetic pending record if the snapshot is missing/corrupt.
    return {
        "schema": SCHEMA,
        "record_type": "PRODUCT_OWNED_SERVE_VERDICT_STATUS_INTAKE",
        "team_id": PACKET_OF_RECORD_V3["team_id"],
        "status": "PENDING_VERDICT",
        "accepted": False,
        "evidence_tier": "UNTESTED",
        "packet_measured": {
            "packet_run_id": PACKET_OF_RECORD_V3["packet_run_id"],
            "packet_json_raw_sha256": PACKET_OF_RECORD_V3["packet_json_raw_sha256"],
            "packet_json_sha_on_disk": packet_sha256_on_disk(),
            "bytes_match_pin": (
                packet_sha256_on_disk() == PACKET_OF_RECORD_V3["packet_json_raw_sha256"]
            ),
        },
        "serve_recommendation": None,
        "owner_decision_required": None,
        "blocking": True,
        "reason": "intake_snapshot_missing_fail_closed",
        "charter_observed": CHARTER_OBSERVED,
    }


def _norm_rec(rec: Any) -> str | None:
    if rec is None:
        return None
    s = str(rec).strip().upper().replace(" ", "-")
    return s or None


def assess_for_packet(
    *,
    packet_sha256: str | None = None,
    intake: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Machine-readable serve-verdict input for packet admission.

    Never opens the owner gate by itself.  Callers (packet admission) combine
    this with the frozen bar verdicts; a DO-NOT-SERVE recommendation denies
    admission for the covered packet even if bars would otherwise pass.
    """
    snap = intake if intake is not None else default_intake()
    on_disk = packet_sha256 if packet_sha256 is not None else packet_sha256_on_disk()
    pin = PACKET_OF_RECORD_V3["packet_json_raw_sha256"]
    measured = snap.get("packet_measured") or {}
    measured_sha = (
        measured.get("packet_json_raw_sha256")
        or measured.get("packet_json_sha256")
        or snap.get("packet_json_raw_sha256")
    )
    rec = _norm_rec(snap.get("serve_recommendation"))
    status = str(snap.get("status") or "PENDING_VERDICT")
    accepted = bool(snap.get("accepted"))
    owner_dec = snap.get("owner_decision_required")

    covers_v3 = bool(measured_sha and measured_sha == pin)
    covers_on_disk = bool(on_disk and on_disk == pin)
    covers_this = covers_v3 or (covers_on_disk and not measured_sha)

    block_reason: str | None = None
    if not accepted:
        if status.upper().startswith("PENDING") or rec is None:
            block_reason = (
                "serve_audit_pending: no independently accepted serve verdict "
                f"for packet-of-record V3 ({PACKET_OF_RECORD_V3['packet_run_id']})"
            )
        else:
            block_reason = (
                f"serve_verdict_not_accepted: status={status} "
                f"serve_recommendation={rec}"
            )
    elif rec in DO_NOT_SERVE_RECS and covers_this:
        block_reason = f"serve_recommendation={rec} (accepted verdict covers this packet)"
    elif rec in DO_NOT_SERVE_RECS:
        # Accepted DO-NOT-SERVE on a different packet: standing order is
        # disclosed but does not by itself block a different packet's bars.
        block_reason = None
    elif rec in SERVE_RECS and covers_this:
        # A SERVE recommendation is necessary but never sufficient: admission
        # still requires both frozen bars.  No block from this channel alone.
        block_reason = None
    elif rec is not None and covers_this:
        block_reason = f"serve_recommendation_unrecognised={rec}"
    else:
        block_reason = (
            "serve_audit_pending: no accepted serve verdict for this packet"
        )

    deny_for_recommendation = bool(
        accepted and covers_this and rec in DO_NOT_SERVE_RECS
    )

    return {
        "schema": SCHEMA,
        "team_id": snap.get("team_id") or PACKET_OF_RECORD_V3["team_id"],
        "status": status,
        "accepted": accepted,
        "evidence_tier": snap.get("evidence_tier"),
        "serve_recommendation": rec,
        "owner_decision_required": owner_dec,
        "owner_decision_required_authorises_session": False,
        "owner_gate_ceiling": (
            "A serve verdict is a machine gate input of packet admission only. "
            "It never sets ready_for_owner_session, human_gate_ready or an "
            "owner card. Requirement 13 conditions (a)/(b) are evaluated "
            "elsewhere and are not satisfied by this field alone."
        ),
        "packet_pin": {
            "packet_run_id": PACKET_OF_RECORD_V3["packet_run_id"],
            "packet_json_raw_sha256": pin,
            "packet_json_sha_on_disk": on_disk,
            "on_disk_matches_pin": on_disk == pin if on_disk else None,
            "intake_measured_sha256": measured_sha,
            "covers_this_packet": covers_this,
        },
        "deny_for_recommendation": deny_for_recommendation,
        "blocking_reason": block_reason,
        "verdict_snapshot": _safe_rel(INTAKE_PATH),
        "charter_observed_at_intake": snap.get("charter_observed") or CHARTER_OBSERVED,
        "do_not_serve_orders_untouched": [
            "results/product/gate_packet/38839347028 (served packet, standing order)",
            "results/product/gate_packet/rebuilt-39027045675 "
            "(packet.json raw sha256 2942c3c2..., DO-NOT-SERVE-UNCHANGED)",
        ],
    }


def harvest(
    source: Path,
    *,
    accepted: bool,
    independent_audit: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Snapshot a serve-verdict source into the product-owned intake path.

    A file named for run X holds run X's measurement (requirement 34).  This
    never overwrites a non-pending intake unless ``overwrite`` is explicitly
    set by a repair that re-homes content under its own run id.
    """
    src = _read_json(source)
    if src is None:
        raise SystemExit(f"unreadable serve-verdict source: {source}")
    on_disk = packet_sha256_on_disk()
    intake = {
        "schema": SCHEMA,
        "record_type": "PRODUCT_OWNED_SERVE_VERDICT_STATUS_INTAKE",
        "harvested_at": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "team_id": src.get("team_id") or PACKET_OF_RECORD_V3["team_id"],
        "charter_version": src.get("charter_version"),
        "status": (
            "ACCEPTED_VERDICT" if accepted else str(src.get("status") or "REPRODUCED_VERDICT")
        ),
        "accepted": bool(accepted),
        "evidence_tier": "ACCEPTED" if accepted else str(src.get("evidence_tier") or "REPRODUCED"),
        "serve_recommendation": _norm_rec(
            src.get("serve_recommendation")
            or (src.get("verdict") or {}).get("serve_recommendation")
        ),
        "owner_decision_required": src.get("owner_decision_required"),
        "packet_measured": {
            "packet_run_id": src.get("packet_run_id")
            or (src.get("packet_measured") or {}).get("packet_run_id")
            or PACKET_OF_RECORD_V3["packet_run_id"],
            "packet_json_raw_sha256": src.get("packet_json_raw_sha256")
            or (src.get("packet_measured") or {}).get("packet_json_raw_sha256")
            or PACKET_OF_RECORD_V3["packet_json_raw_sha256"],
            "packet_json_sha_on_disk": on_disk,
            "bytes_match_pin": on_disk == PACKET_OF_RECORD_V3["packet_json_raw_sha256"],
        },
        "independent_audit": independent_audit or src.get("independent_audit"),
        "source_path": str(source),
        "source_sha256": _sha256_file(source),
        "charter_observed": CHARTER_OBSERVED,
        "purpose": (
            "Product-lane record of the independent serve verdict on "
            "packet-of-record V3. Consumed only as a machine gate input of "
            "packet admission. Never an owner card."
        ),
    }
    if INTAKE_PATH.exists() and not overwrite:
        existing = _read_json(INTAKE_PATH) or {}
        if existing.get("accepted") and accepted:
            raise SystemExit(
                "refusing to overwrite an accepted serve-verdict intake; "
                "re-home under a new run-id filename (requirement 34)"
            )
        if existing.get("accepted") and not accepted:
            raise SystemExit(
                "refusing to overwrite an accepted intake with a non-accepted verdict"
            )
    INTAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTAKE_PATH.write_text(
        json.dumps(intake, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return intake


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--harvest",
        metavar="PATH",
        help="harvest a serve-verdict JSON into the product-owned intake",
    )
    ap.add_argument(
        "--accepted",
        action="store_true",
        help="with --harvest: mark the verdict independently accepted",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="with --harvest: allow replacing a non-accepted pending intake",
    )
    args = ap.parse_args(argv)
    if args.harvest:
        out = harvest(
            Path(args.harvest),
            accepted=bool(args.accepted),
            overwrite=bool(args.overwrite),
        )
        print(json.dumps(out, indent=2) if args.json else f"harvested -> {INTAKE_PATH}")
        return 0
    out = assess_for_packet()
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(
            f"status={out['status']} accepted={out['accepted']} "
            f"serve_recommendation={out['serve_recommendation']} "
            f"deny_for_recommendation={out['deny_for_recommendation']}"
        )
        if out["blocking_reason"]:
            print(f"blocking: {out['blocking_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
