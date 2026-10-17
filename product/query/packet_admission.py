#!/usr/bin/env python3
"""Packet admission: consume the accepted frozen bar verdicts as a machine gate.

Why this module exists
----------------------
Factory direction v50, product obligation (1):

    *"make the two accepted bar verdicts a machine-readable input of packet
    admission, so no packet, owner card, disclosure or state field can carry
    ``ready_for_owner_session=true`` or ``human_gate_ready=true`` while
    counter-label support is below the frozen bar ``4457e971...`` or geometry
    below ``a7452748....``"*

The standing accepted DO-NOT-SERVE order (``ACCEPTED_frontier-served-packet-
falsification_38880639079.json``) exists because both frozen bars are unmet on
the served packet:

* counter-label support **5/65 = 0.0769** against the frozen **absolute** bar of
  ``1.0`` (rules sha256 ``4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608``);
* map geometry **0/3** bundles passing all **11** criteria against that same
  all-11 bar (rules sha256 ``a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633``).

This module does **not** re-measure anything and does **not** re-derive a
threshold.  Label measurement and geometry measurement are Frontier's lane and
the executable bar gates are Core Evaluation's.  Packet admission only READS the
product-owned snapshots of those accepted verdicts and answers one question:
*is the packet admissible to a human owner session yet?*

Bars, verbatim and frozen (never tuned here)
--------------------------------------------
``FROZEN_LABEL_BAR = 1.0`` (absolute; ANY single unsupported label fails).
``FROZEN_GEOMETRY_CRITERIA = 11`` (all criteria on every bundle).

Fail-closed
-----------
If no accepted bar verdict can be read, admission is **denied** with reason
``no_accepted_bar_verdict``.  Missing evidence is never a pass.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Product-owned snapshots of the accepted Frontier measurements.  Both are
#: committed; admission never depends on the CI mount being present.
FALSIFICATION_SNAPSHOT = (REPO_ROOT / "results" / "product" / "frontier_verdicts"
                          / "ACCEPTED_frontier-served-packet-falsification_38880639079.json")
PRIOR_SNAPSHOT = (REPO_ROOT / "results" / "product" / "frontier_verdicts"
                  / "ACCEPTED_counter_label_38841035773__map_semantics_38846038296.json")

SCHEMA = "product-packet-admission/1"

#: Frozen rubric hashes.  Admission must never accept a verdict that does not
#: name the frozen rubric it was scored under.
FROZEN_LABEL_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_RULES_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"

#: The frozen bars themselves.  Absolute, unchanged since pre-registration.
FROZEN_LABEL_BAR = 1.0
FROZEN_GEOMETRY_CRITERIA = 11


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _collect_label_measurements(snapshots: list[tuple[str, dict]]) -> list[dict]:
    """Every accepted counter-label support measurement we can name."""
    out: list[dict] = []
    for source, snap in snapshots:
        half = snap.get("label_half")
        if isinstance(half, dict) and half.get("n_scored"):
            out.append({
                "source": source,
                "team_run_id": snap.get("team_run_id"),
                "measured_packet": snap.get("measured_packet"),
                "n_scored": int(half.get("n_scored") or 0),
                "n_supported": int(half.get("n_supported") or 0),
                "support_rate": float(half.get("support_rate") or 0.0),
                "verdict": half.get("verdict"),
                "rules_sha256": FROZEN_LABEL_RULES_SHA256,
            })
        counter = snap.get("frontier_counter_label_integrity")
        if isinstance(counter, dict) and counter.get("n_scored_primary"):
            out.append({
                "source": source,
                "team_run_id": counter.get("team_run_id"),
                "measured_packet": counter.get("measured_population"),
                "n_scored": int(counter.get("n_scored_primary") or 0),
                "n_supported": None,
                "support_rate": float(counter.get("support_rate_primary") or 0.0),
                "verdict": counter.get("verdict"),
                "rules_sha256": FROZEN_LABEL_RULES_SHA256,
            })
    return out


def _collect_geometry_measurements(snapshots: list[tuple[str, dict]]) -> list[dict]:
    out: list[dict] = []
    for source, snap in snapshots:
        half = snap.get("geometry_half")
        if isinstance(half, dict) and half.get("n_bundles"):
            out.append({
                "source": source,
                "team_run_id": snap.get("team_run_id"),
                "measured_packet": snap.get("measured_packet"),
                "n_bundles": int(half.get("n_bundles") or 0),
                "n_bundles_pass": int(half.get("n_bundles_pass") or 0),
                "pass_counts": half.get("pass_counts") or {},
                "verdict": half.get("verdict"),
                "rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
            })
        semantics = snap.get("frontier_map_semantics")
        if isinstance(semantics, dict) and semantics.get("per_bundle"):
            per = semantics["per_bundle"]
            n_pass = sum(1 for v in per.values()
                         if str(v.get("overall")) == "PASS")
            out.append({
                "source": source,
                "team_run_id": semantics.get("team_run_id"),
                "measured_packet": semantics.get("measured_population"),
                "n_bundles": len(per),
                "n_bundles_pass": n_pass,
                "pass_counts": {k: len(v.get("criteria_passed") or [])
                                for k, v in per.items()},
                "verdict": "PASS" if n_pass == len(per) else "FAIL",
                "rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
            })
    return out


def assess(*, snapshots: list[tuple[str, dict]] | None = None) -> dict[str, Any]:
    """Return the machine-readable packet-admission decision.

    ``snapshots`` is an optional list of ``(source_label, snapshot_dict)`` for
    tests; production reads the two committed product-owned snapshots.
    """
    if snapshots is None:
        loaded: list[tuple[str, dict]] = []
        for path in (FALSIFICATION_SNAPSHOT, PRIOR_SNAPSHOT):
            snap = _read_json(path)
            if snap is not None:
                loaded.append((path.name, snap))
        snapshots = loaded

    labels = _collect_label_measurements(snapshots)
    geometries = _collect_geometry_measurements(snapshots)

    if not labels or not geometries:
        return {
            "schema": SCHEMA,
            "packet_admitted": False,
            "ready_for_owner_session_allowed": False,
            "blocking_reason": "no_accepted_bar_verdict",
            "bars": {
                "counter_label": {"satisfied": False, "measurements": labels},
                "map_geometry": {"satisfied": False, "measurements": geometries},
            },
            "frozen": _frozen_block(),
            "claim_ceiling": (
                "Admission is DENIED fail-closed: no accepted frozen-bar verdict "
                "could be read. Missing evidence is never a pass."
            ),
        }

    # Admission is conservative: EVERY accepted measurement must satisfy the
    # frozen bar.  The measurement REPORTED as binding is the one that scored
    # the served packet (frontier-served-packet-falsification) when present,
    # because that is the artifact the owner would actually be shown; absent
    # that, the weakest accepted measurement.
    worst_label = min(labels, key=lambda m: (m["support_rate"], m["source"]))
    worst_geometry = min(geometries,
                         key=lambda m: (m["n_bundles_pass"] / max(1, m["n_bundles"]),
                                        m["source"]))
    binding_label = next(
        (m for m in labels if m.get("measured_packet", "").startswith("gate_packet/")),
        worst_label,
    )
    binding_geometry = next(
        (m for m in geometries if m.get("measured_packet", "").startswith("gate_packet/")),
        worst_geometry,
    )
    label_met = all(m["support_rate"] >= FROZEN_LABEL_BAR for m in labels)
    geometry_met = all(m["n_bundles_pass"] >= m["n_bundles"] > 0 for m in geometries)
    admitted = bool(label_met and geometry_met)

    reasons: list[str] = []
    if not label_met:
        reasons.append(
            "counter_label_support "
            f"{binding_label['n_supported']}/{binding_label['n_scored']} = "
            f"{round(binding_label['support_rate'], 4)} < frozen absolute bar "
            f"{FROZEN_LABEL_BAR}"
        )
    if not geometry_met:
        reasons.append(
            "map_geometry "
            f"{binding_geometry['n_bundles_pass']}/{binding_geometry['n_bundles']} "
            "bundles pass all "
            f"{FROZEN_GEOMETRY_CRITERIA} criteria"
        )

    return {
        "schema": SCHEMA,
        "packet_admitted": admitted,
        "ready_for_owner_session_allowed": admitted,
        "blocking_reason": None if admitted else "; ".join(reasons),
        "bars": {
            "counter_label": {
                "satisfied": label_met,
                "bar": FROZEN_LABEL_BAR,
                "binding_measurement": binding_label,
                "measurements": labels,
            },
            "map_geometry": {
                "satisfied": geometry_met,
                "bar_criteria": FROZEN_GEOMETRY_CRITERIA,
                "binding_measurement": binding_geometry,
                "measurements": geometries,
            },
        },
        "frozen": _frozen_block(),
        "claim_ceiling": (
            "Admission consumes accepted Frontier verdicts as INPUT; it does not "
            "re-measure labels or geometry and does not rule on map usefulness. "
            "Admitted does not mean useful, and unmet bars never mean a decision "
            "IS or IS NOT supporting/limiting."
        ),
    }


def _frozen_block() -> dict[str, Any]:
    return {
        "label_rules_sha256": FROZEN_LABEL_RULES_SHA256,
        "geometry_rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
        "label_bar": FROZEN_LABEL_BAR,
        "geometry_criteria": FROZEN_GEOMETRY_CRITERIA,
        "note": "Bars are frozen; this module never tunes, re-derives or relaxes them.",
    }


def enforce(summary: dict[str, Any], *, admission: dict[str, Any] | None = None
            ) -> dict[str, Any]:
    """Force ``ready_for_owner_session`` false while the frozen bars are unmet.

    Returns the admission used.  The caller keeps the base ``ready`` value under
    ``ready_for_owner_session_base`` so the hold-back is auditable, never silent.
    """
    adm = admission if admission is not None else assess()
    base = bool(summary.get("ready_for_owner_session"))
    summary["ready_for_owner_session_base"] = base
    if not adm.get("ready_for_owner_session_allowed", False):
        summary["ready_for_owner_session"] = False
        summary["packet_admission_blocked"] = True
        summary["packet_admission_reason"] = adm.get("blocking_reason")
    else:
        summary["packet_admission_blocked"] = False
    summary["packet_admission"] = adm
    return adm


def offending_owner_claims(record: dict[str, Any],
                           *, admission: dict[str, Any] | None = None) -> list[str]:
    """Names of fields that claim owner-readiness while the bars are unmet.

    Used by tests and by any producer that wants to self-check a packet, owner
    card, disclosure or state artifact before writing it.
    """
    adm = admission if admission is not None else assess()
    if adm.get("ready_for_owner_session_allowed", False):
        return []
    out = []
    for key in ("ready_for_owner_session", "human_gate_ready",
                "ready_for_owner_session_allowed"):
        if record.get(key) is True:
            out.append(key)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true",
                    help="print the admission decision as JSON")
    args = ap.parse_args(argv)
    adm = assess()
    if args.json:
        print(json.dumps(adm, indent=1))
    else:
        print(f"packet_admitted={adm['packet_admitted']} "
              f"ready_for_owner_session_allowed={adm['ready_for_owner_session_allowed']}")
        if adm["blocking_reason"]:
            print(f"blocked: {adm['blocking_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
