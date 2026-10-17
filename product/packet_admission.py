"""Packet admission gate over the two ACCEPTED frozen-bar verdicts.

Factory direction v50 product obligation (1): *make the two accepted bar
verdicts a machine-readable input of packet admission, so no packet, owner
card, disclosure or state field can carry ``ready_for_owner_session=true`` or
``human_gate_ready=true`` while counter-label support is below the frozen bar
``4457e971...`` or geometry below ``a7452748...``.*

This module is that input.  It reads the accepted independent verdict
``ACCEPTED_frontier-served-packet-falsification_38880639079.json`` (team
``frontier-served-packet-falsification``, run 38880639079, audit gate=PASS,
safe_to_integrate=true, promote commit ``464c45f7``), whose own serve
recommendation is ``DO-NOT-SERVE this packet unchanged``, and turns it into a
boolean admission decision that callers cannot hand-write.

Design constraints taken from the control plane, not invented here:

* Both frozen rubrics are reused by RE-HASH, never re-derived, re-tuned or
  "clarified".  The two rule digests are carried here as the identity of the
  bars; nothing in this file may move them.
* The ABSOLUTE-bar status is reported, never enforced as a build blocker.
  Counter-label support is red against the absolute bar of 1.0 on every
  current artifact by construction, so enforcing it as a build blocker would
  recreate the never-green loop the evaluation lane's gates exist to break.
* The accepted DO-NOT-SERVE order is an independent block.  Admission is
  therefore *frozen at false* while a covering verdict with a DO-NOT-SERVE
  recommendation is on file, and it can only be reopened by an accepted verdict
  that replaces it — never by this module, a flag, or a human.
* FAIL CLOSED.  A missing, unreadable or malformed verdict yields
  ``admissible=False`` with the reason recorded.  The owner's attention is the
  scarcest resource in the system and must not be spent on a packet whose
  admissibility nobody could establish.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
VERDICT_DIR = REPO_ROOT / "results" / "product" / "frontier_verdicts"

#: Frozen rubrics, reused by re-hash only (factory-wide requirement 18).
LABEL_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
GEOMETRY_RULES_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"

DEFAULT_VERDICT = VERDICT_DIR / (
    "ACCEPTED_frontier-served-packet-falsification_38880639079.json"
)

#: The serve recommendation that, while present, freezes admission closed.  A
#: verdict carrying it is an accepted independent DO-NOT-SERVE order, not a
#: heuristic; the product consumes it as an input and does not reinterpret it.
DO_NOT_SERVE = "DO-NOT-SERVE"

#: Forbidden claim constructions, copied verbatim from the accepted verdict's
#: ``forbidden_construction_patterns``.  The product may not assert that a
#: specific decision IS supporting/contrary/limiting (direction obligation (3)).
FORBIDDEN_CLAIM_PATTERNS = [
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+not\s+(supporting|contrary|limiting)\b",
    r"\b[A-Za-z0-9_.\-]+\s+is\s+(a\s+)?(supporting|contrary|limiting)\s+(authority|decision|case)\b",
    r"\bwe\s+(classify|label|find)\s+[A-Za-z0-9_.\-]+\s+as\s+(supporting|contrary|limiting)\b",
    r"\basserts?\s+that\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
]
_FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_CLAIM_PATTERNS]


def find_forbidden_claims(text: str) -> list[dict[str, Any]]:
    """Claim sentences that the accepted verdict forbids the product to make.

    Direction obligation (3): never assert in any artifact that a specific
    decision IS supporting, contrary or limiting.
    """
    hits: list[dict[str, Any]] = []
    for raw in re.split(r"(?<=[.!?\n])\s+", str(text or "")):
        sentence = raw.strip()
        if not sentence:
            continue
        for pattern, rx in zip(FORBIDDEN_CLAIM_PATTERNS, _FORBIDDEN_RE):
            if rx.search(sentence):
                hits.append({"sentence": sentence[:400], "pattern": pattern})
                break
    return hits


def load_verdict(path: Path | None = None) -> dict[str, Any] | None:
    target = Path(path) if path else DEFAULT_VERDICT
    try:
        with open(target, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def evaluate_bars(verdict: dict[str, Any] | None) -> dict[str, Any]:
    """Recompute the two bar halves from the accepted verdict.

    Reported, never enforced as a build blocker — the absolute label bar of 1.0
    is red on every current artifact by construction.
    """
    if not isinstance(verdict, dict) or not (verdict.get("label_half") or verdict.get("geometry_half")):
        return {
            "available": False,
            "reason": "no accepted verdict could be read",
            "label": {"verdict": None, "n_scored": 0, "n_supported": 0,
                      "support_rate": 0.0, "absolute_bar": 1.0,
                      "meets_absolute_bar": False,
                      "rules_sha256": LABEL_RULES_SHA256,
                      "enforced_as_build_blocker": False},
            "geometry": {"verdict": None, "n_bundles": 0, "n_bundles_pass": 0,
                         "pass_counts": {}, "french_largest_share": None,
                         "rules_sha256": GEOMETRY_RULES_SHA256,
                         "meets_all_criteria_on_every_bundle": False,
                         "enforced_as_build_blocker": False},
        }
    label = verdict.get("label_half") or {}
    geometry = verdict.get("geometry_half") or {}
    n_scored = int(label.get("n_scored") or 0)
    n_supported = int(label.get("n_supported") or 0)
    return {
        "available": True,
        "label": {
            "verdict": label.get("verdict"),
            "n_scored": n_scored,
            "n_supported": n_supported,
            "support_rate": float(label.get("support_rate") or 0.0),
            "absolute_bar": 1.0,
            "meets_absolute_bar": bool(n_scored) and n_supported >= n_scored,
            "rules_sha256": LABEL_RULES_SHA256,
            "enforced_as_build_blocker": False,
            "enforcement_note": (
                "The absolute bar is red on every current artifact by "
                "construction; enforcing it as a build blocker would recreate "
                "the never-green loop Core Evaluation's frozen-bar gates exist "
                "to break. Reported here, enforced by nothing in this module."
            ),
        },
        "geometry": {
            "verdict": geometry.get("verdict"),
            "n_bundles": int(geometry.get("n_bundles") or 0),
            "n_bundles_pass": int(geometry.get("n_bundles_pass") or 0),
            "pass_counts": dict(geometry.get("pass_counts") or {}),
            "french_largest_share": geometry.get("french_largest_share"),
            "rules_sha256": GEOMETRY_RULES_SHA256,
            "meets_all_criteria_on_every_bundle": bool(
                geometry.get("n_bundles")
            ) and int(geometry.get("n_bundles_pass") or 0) >= int(geometry["n_bundles"]),
            "enforced_as_build_blocker": False,
        },
    }


def packet_admission(path: Path | None = None) -> dict[str, Any]:
    """Machine-readable admission decision for any packet, owner card or state.

    Returns a dict whose ``admissible`` and ``ready_for_owner_session`` fields
    are DERIVED, never asserted by a caller.  Fail-closed on every error path.
    """
    verdict = load_verdict(path)
    if verdict is None:
        return {
            "schema": "product/packet-admission/1",
            "admissible": False,
            "ready_for_owner_session": False,
            "human_gate_ready": False,
            "blocked_by": ["no_accepted_verdict"],
            "reason": (
                "The accepted bar verdict could not be read, so packet "
                "admission cannot be established. Fail closed: the owner's "
                "attention is not spent on a packet whose admissibility is "
                "unknown."
            ),
            "bars": {"available": False},
            "verdict_source": str(path or DEFAULT_VERDICT),
        }

    bars = evaluate_bars(verdict)
    serve = str(verdict.get("serve_recommendation") or "")
    do_not_serve = DO_NOT_SERVE in serve.upper()
    blocked_by: list[str] = []
    if do_not_serve:
        blocked_by.append("accepted_do_not_serve_order")
    if not bars["geometry"].get("meets_all_criteria_on_every_bundle"):
        blocked_by.append("geometry_below_frozen_bar")
    if not bars["label"].get("meets_absolute_bar"):
        blocked_by.append("counter_label_support_below_absolute_bar")

    admissible = not blocked_by
    return {
        "schema": "product/packet-admission/1",
        "admissible": admissible,
        # Derived from `admissible`, so it can never be set true independently.
        "ready_for_owner_session": admissible,
        "human_gate_ready": admissible,
        "blocked_by": blocked_by,
        "reason": (
            "All accepted frozen bars are met; this packet MAY be put in front "
            "of the owner."
            if admissible else
            "The packet is NOT admissible for the owner session: "
            + ", ".join(blocked_by)
        ),
        "serve_recommendation": serve,
        "verdict_source": str(path or DEFAULT_VERDICT),
        "verdict_team": verdict.get("team_id"),
        "verdict_run": verdict.get("team_run_id"),
        "verdict_accept_commit": verdict.get("accept_commit"),
        "verdict_covers_this_packet": verdict.get("covers_this_packet"),
        "bars": bars,
        "what_product_may_NOT_claim": list(verdict.get("what_product_may_NOT_claim") or []),
        "claim_ceiling": verdict.get("claim_ceiling"),
    }


def is_admissible(path: Path | None = None) -> bool:
    """Single boolean gate for callers that only need the verdict."""
    return bool(packet_admission(path)["admissible"])


def enforce_owner_session(summary: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """Gate a packet summary's owner-session readiness on the accepted bars.

    ``finalize_summary`` in gate_packet.py computes ``ready_for_owner_session``
    from run-time admissibility and guards alone, which is how a packet can
    carry that field while both accepted bars are unmet.  This overwrites it
    with the DERIVED value and records why, so the field cannot drift.
    """
    decision = packet_admission(path)
    claimed = summary.get("ready_for_owner_session")
    summary["ready_for_owner_session"] = bool(decision["ready_for_owner_session"])
    summary["packet_admission"] = {
        "admissible": decision["admissible"],
        "blocked_by": decision["blocked_by"],
        "reason": decision["reason"],
        "verdict_source": decision["verdict_source"],
        "verdict_run": decision.get("verdict_run"),
        "verdict_accept_commit": decision.get("verdict_accept_commit"),
        "bars": decision["bars"],
        "run_time_ready_for_owner_session_before_gate": bool(claimed),
        "gate_applied": bool(claimed) != bool(decision["ready_for_owner_session"]),
        "note": (
            "ready_for_owner_session is DERIVED from the two accepted frozen "
            "bars, never asserted by the run. A run-time computation alone "
            "would let a packet claim owner readiness while the accepted "
            "DO-NOT-SERVE order stands."
        ),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verdict", type=Path, default=None)
    args = ap.parse_args(argv)
    decision = packet_admission(args.verdict)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    return 0 if decision["admissible"] else 3


__all__ = [
    "DEFAULT_VERDICT",
    "DO_NOT_SERVE",
    "FORBIDDEN_CLAIM_PATTERNS",
    "GEOMETRY_RULES_SHA256",
    "LABEL_RULES_SHA256",
    "enforce_owner_session",
    "evaluate_bars",
    "find_forbidden_claims",
    "is_admissible",
    "load_verdict",
    "packet_admission",
]


if __name__ == "__main__":
    raise SystemExit(main())