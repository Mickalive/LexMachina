#!/usr/bin/env python3
"""Adopt the accepted Frontier verdicts as gate-packet input (v54 backlog item 4).

Why this exists
---------------
Factory direction v54, backlog item (4): *"Adopt the frontier verdicts as INPUT
without waiting for them ... frontier-counter-label-integrity's support rate is
the external falsifier for the D2 fix ... frontier-map-semantics charter 2's
verdict tells you whether the geometry you are about to serve survives. If
either comes back UNSOUND, fix before the session; if either is merely
informative, adopt it in the gate packet's disclosure."*

Two Frontier teams were human-accepted on ``main`` while the product cycle was
in flight:

- **frontier-counter-label-integrity** (team run 38841035773, accept commit
  ``7c960b4``) — verdict ``LABEL_UNSOUND``: 0 of 7 scored candidate-limiting
  rows carried sentence-level support for the label they were given. Crucially
  the *coverage* block states that **every scored bundle is pre-repair** (the
  primary population is the PRE-FIX packet ``gate_packet/38799024807``) and
  that no post-repair artifact existed on the accepted mount. The verdict is
  therefore a baseline of the OLD labels, not a measurement of this packet's
  post-D2-fix rows — and the frontier's own rule says ``INSUFFICIENT_POPULATION``
  must never be read as ``LABEL_SOUND``.
- **frontier-map-semantics** (team run 38846038296, accept commit ``15362f6``)
  — charter-2 verdict ``FAIL`` on the frozen semantics rule for the pre-rebuild
  bundles (DE 5/11, FR 5/11, IT 4/11), with the machine-checked promoted
  decision: *"keep the shipped geometry and CLOSE geometry work until after the
  human gate"* because every in-budget alternative (A1/A2/A3) also FAILs.

What this tool does and does not do
-----------------------------------
It harvests those two verdicts **once**, into a product-owned snapshot under
``results/product/frontier_verdicts/`` (with source sha256s and provenance),
and exposes a packet-level disclosure built from that snapshot — so the gate
packet, the owner card and their tests work offline and cannot silently drift
if a mount disappears. It never re-measures anything (label measurement and
geometry measurement are Frontier's lane), never re-labels a row, never edits a
bundle or the frozen pre-registration, and never writes ``human_gate_ready``.

Usage
-----
    # harvest once, from the accepted mounts, into the product-owned snapshot
    python product/frontier_verdict_adoption.py harvest \
        --accepted-root /tmp/lex_accepted/frontier

    # print the disclosure that the packet will carry (reads the snapshot)
    python product/frontier_verdict_adoption.py disclosure

    # check the accepted mounts for a newer measurement without re-measuring
    python product/frontier_verdict_adoption.py sweep \
        --accepted-root /tmp/lex_accepted/frontier
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Product-owned snapshot of the two accepted verdicts. Committed, so the
#: packet/disclosure/card path never depends on the CI mount being present.
SNAPSHOT_PATH = (REPO_ROOT / "results" / "product" / "frontier_verdicts"
                 / "ACCEPTED_counter_label_38841035773__map_semantics_38846038296.json")

#: Provenance constants: the accepted Frontier runs, as recorded by the
#: director (factory_direction v54, item (4)) and verified on origin/main.
COUNTER_LABEL_TEAM_RUN_ID = "38841035773"
COUNTER_LABEL_ACCEPT_COMMIT = "7c960b4"
COUNTER_LABEL_REPORT = Path("frontier-counter-label-integrity/results/frontier"
                            "/frontier-counter-label-integrity/REPORT.json")
#: Newest-verdict sweep (v54 item (4) subsequent-measurement rule): per-team
#: verification files published by the Frontier teams under their accepted
#: results tree. A newer file does NOT automatically obsolete the snapshot —
#: only a verification that re-measured (labels_rescored / bundles_remeasured)
#: can move the measurement; anything else leaves the snapshot valid.
COUNTER_LABEL_RESULTS_DIR = Path("frontier-counter-label-integrity/results/frontier"
                                 "/frontier-counter-label-integrity")
MAP_SEMANTICS_RESULTS_DIR = Path("frontier-map-semantics/results/frontier"
                                 "/frontier-map-semantics")

MAP_SEMANTICS_TEAM_RUN_ID = "38846038296"
MAP_SEMANTICS_ACCEPT_COMMIT = "15362f6"
MAP_SEMANTICS_ROOT = Path("frontier-map-semantics/results/frontier/frontier-map-semantics")
MAP_SEMANTICS_BUNDLES = ("de-kapitalverletzung", "fr-bail-entretien",
                         "it-responsabilita-medica", "additional-287")

SCHEMA = "product-frontier-verdict-adoption/1"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def harvest(accepted_root: Path) -> dict[str, Any]:
    """Read the two accepted verdict artifacts and build the product snapshot."""
    root = Path(accepted_root)
    counter_path = root / COUNTER_LABEL_REPORT
    if not counter_path.is_file():
        raise FileNotFoundError(f"counter-label verdict not found: {counter_path}")
    counter = _read_json(counter_path)
    cv = counter.get("verdict") or {}
    coverage = counter.get("coverage") or {}

    semantics_root = root / MAP_SEMANTICS_ROOT
    per_bundle: dict[str, Any] = {}
    source_files = [{"path": str(counter_path), "sha256": _sha256(counter_path)}]
    for qid in MAP_SEMANTICS_BUNDLES:
        report_path = semantics_root / qid / "report.json"
        if not report_path.is_file():
            raise FileNotFoundError(f"map-semantics report not found: {report_path}")
        report = _read_json(report_path)
        criteria = report.get("criteria") or {}
        per_bundle[qid] = {
            "overall": report.get("overall"),
            "n_decisions": report.get("n_decisions"),
            "n_clusters": report.get("n_clusters"),
            "n_relations": report.get("n_relations"),
            "criteria_passed": sorted(k for k, v in criteria.items()
                                      if (v or {}).get("pass") is True),
            "criteria_failed": sorted(k for k, v in criteria.items()
                                      if (v or {}).get("pass") is False),
        }
        source_files.append({"path": str(report_path), "sha256": _sha256(report_path)})

    promoted = (
        "FAIL with NO working in-budget alternative: keep the shipped geometry "
        "and CLOSE geometry work until after the human gate."
    )
    return {
        "schema": SCHEMA,
        "harvested_at": _now(),
        "harvested_from_accepted_root": str(root),
        "source_files": source_files,
        "frontier_counter_label_integrity": {
            "team_run_id": COUNTER_LABEL_TEAM_RUN_ID,
            "accept_commit_on_main": COUNTER_LABEL_ACCEPT_COMMIT,
            "verdict": cv.get("verdict"),
            "support_rate_primary": cv.get("support_rate_primary"),
            "n_scored_primary": cv.get("n_scored_primary"),
            "required_min_population_primary": cv.get("required_min_population_primary"),
            "secondary_verdict_replication": cv.get("secondary_verdict_replication"),
            "non_vacuity_passed": cv.get("non_vacuity_passed"),
            "insufficient_population_rule": cv.get("insufficient_population_is_non_result"),
            "every_scored_bundle_is_pre_repair": coverage.get("every_scored_bundle_is_pre_repair"),
            "before_after_note": coverage.get("before_after_note"),
            "limitations": (counter.get("limitations") or [])[:3],
            "measured_population": (
                "primary: the PRE-FIX packet gate_packet/38799024807 "
                "(7 candidate-limiting rows across de/fr/it) + 6 secondary "
                "bundles; every scored bundle is pre-repair"
            ),
        },
        "frontier_map_semantics": {
            "team_run_id": MAP_SEMANTICS_TEAM_RUN_ID,
            "accept_commit_on_main": MAP_SEMANTICS_ACCEPT_COMMIT,
            "promoted_decision": promoted,
            "measured_population": (
                "the PRE-REBUILD packet bundles (134/131/132 decisions) + the "
                "287-row progressive-slice bundle; NOT this packet's bundles"
            ),
            "per_bundle": per_bundle,
        },
        "claim_ceiling": (
            "Independent Frontier measurements adopted as input (v54 item 4). "
            "Both verdicts were measured on PRE-FIX accepted-chain artifacts, "
            "not on this packet's bundles; neither is a verdict on the rows "
            "this packet ships. Label soundness and geometry semantics remain "
            "Frontier's measurement; this product only carries the verdicts."
        ),
    }


def _newest_verification(results_dir: Path) -> dict[str, Any] | None:
    """Return the newest VERIFICATION_<run_id>.json in a Frontier results dir.

    Newest = largest numeric run id. Returns None when the directory holds no
    verification file (a team that has never published one).
    """
    if not results_dir.is_dir():
        return None
    best: dict[str, Any] | None = None
    best_run = -1
    for child in sorted(results_dir.iterdir()):
        if not (child.name.startswith("VERIFICATION_") and child.name.endswith(".json")):
            continue
        stem = child.name[len("VERIFICATION_"):-len(".json")]
        if not stem.isdigit():
            continue
        run = int(stem)
        if run > best_run:
            try:
                doc = _read_json(child)
            except (json.JSONDecodeError, OSError):
                continue
            best, best_run = {"path": str(child), "run_id": stem, "doc": doc}, run
    return best


def sweep(accepted_root: Path, snapshot_path: Path | None = None) -> dict[str, Any]:
    """Check the accepted mounts for a newer Frontier measurement (read-only).

    Implements the v54 item (4) subsequent-measurement rule: *if Frontier
    later measures THIS packet's post-D2-fix labels or the current geometry,
    harvest that verdict the same way and update the snapshot; never
    re-measure labels or geometry in the product lane.*

    This function performs the *check*, never the measurement: it reports the
    newest accepted verification per team, whether that verification
    re-measured anything (``labels_rescored`` / ``bundles_remeasured``), and
    therefore whether the committed snapshot is still current and whether
    ``covers_this_packet`` may stay False. A newer verification that changed
    nothing observable leaves the snapshot valid — that is the expected
    steady state, not a defect.
    """
    root = Path(accepted_root)
    snap = load(snapshot_path)
    if snap is None:
        return {"ok": False,
                "skip_reason": "no committed verdict snapshot; run harvest first"}
    counter = snap.get("frontier_counter_label_integrity") or {}
    semantics = snap.get("frontier_map_semantics") or {}

    newest_counter = _newest_verification(root / COUNTER_LABEL_RESULTS_DIR)
    newest_map = _newest_verification(root / MAP_SEMANTICS_RESULTS_DIR)

    def _counter_block() -> dict[str, Any]:
        if newest_counter is None:
            return {"newest_verification_run_id": None,
                    "snapshot_team_run_id": counter.get("team_run_id"),
                    "re_measured": None,
                    "snapshot_current": True,
                    "covers_this_packet": False,
                    "note": "no verification file on the mount; snapshot stands"}
        doc = newest_counter["doc"] or {}
        re_measured = bool(doc.get("labels_rescored") or doc.get("bundles_remeasured"))
        return {
            "newest_verification_run_id": newest_counter["run_id"],
            "newest_verdict": doc.get("verdict"),
            "labels_rescored": bool(doc.get("labels_rescored", False)),
            "bundles_remeasured": bool(doc.get("bundles_remeasured", False)),
            "rules_edited": bool(doc.get("rules_edited", False)),
            "measurement_unchanged": doc.get("measurement_unchanged"),
            "snapshot_team_run_id": counter.get("team_run_id"),
            "re_measured": re_measured,
            # The snapshot stays valid unless a newer verification re-measured.
            # A newer run id alone (operational repair, harness delta, scope
            # fix) is explicitly NOT a new measurement.
            "snapshot_current": not re_measured,
            "covers_this_packet": False,
        }

    def _map_block() -> dict[str, Any]:
        if newest_map is None:
            return {"newest_verification_run_id": None,
                    "snapshot_team_run_id": semantics.get("team_run_id"),
                    "snapshot_current": True,
                    "covers_this_packet": False,
                    "note": "no verification file on the mount; snapshot stands"}
        doc = newest_map["doc"] or {}
        return {
            "newest_verification_run_id": newest_map["run_id"],
            "snapshot_team_run_id": semantics.get("team_run_id"),
            "snapshot_current": newest_map["run_id"] == str(semantics.get("team_run_id")),
            "covers_this_packet": False,
        }

    cb, mb = _counter_block(), _map_block()
    return {
        "schema": "product-frontier-verdict-sweep/1",
        "checked_at": _now(),
        "accepted_root": str(root),
        "snapshot_path": str(Path(snapshot_path) if snapshot_path else SNAPSHOT_PATH),
        "frontier_counter_label_integrity": cb,
        "frontier_map_semantics": mb,
        "covers_this_packet": False,
        "action_required": bool(cb.get("re_measured")),
        "claim_ceiling": (
            "Read-only freshness check, not a measurement. covers_this_packet "
            "stays False until a Frontier verification re-measures this "
            "packet's own bundles; only then does the snapshot need a harvest."
        ),
    }


def load(path: Path | None = None) -> dict[str, Any] | None:
    """Load the product-owned snapshot (None when it has never been harvested)."""
    p = Path(path) if path else SNAPSHOT_PATH
    if not p.is_file():
        return None
    return _read_json(p)


def disclosure(path: Path | None = None) -> dict[str, Any]:
    """The packet-level disclosure block carried in ``disclosures.json``.

    The two ``covers_this_packet`` flags are the load-bearing honesty of this
    block: a reader must never walk away thinking LABEL_UNSOUND or the
    geometry FAIL was measured on the rows this packet actually rings.
    """
    snap = load(path)
    if snap is None:
        return {
            "published": False,
            "skip_reason": (
                "no accepted Frontier verdict snapshot found; run "
                "product/frontier_verdict_adoption.py harvest against the "
                "accepted mounts"
            ),
        }
    counter = snap.get("frontier_counter_label_integrity") or {}
    semantics = snap.get("frontier_map_semantics") or {}
    return {
        "published": True,
        "snapshot_path": str(Path(path) if path else SNAPSHOT_PATH),
        "snapshot_sha256": _sha256(Path(path) if path else SNAPSHOT_PATH),
        "harvested_at": snap.get("harvested_at"),
        "claim_ceiling": snap.get("claim_ceiling"),
        "frontier_counter_label_integrity": {
            "team_run_id": counter.get("team_run_id"),
            "accept_commit_on_main": counter.get("accept_commit_on_main"),
            "verdict": counter.get("verdict"),
            "support_rate_primary": counter.get("support_rate_primary"),
            "n_scored_primary": counter.get("n_scored_primary"),
            "measured_population": counter.get("measured_population"),
            "every_scored_bundle_is_pre_repair": counter.get(
                "every_scored_bundle_is_pre_repair"),
            "covers_this_packet": False,
            "insufficient_population_rule": counter.get("insufficient_population_rule"),
            "consequence_for_this_packet": (
                "this packet's counter rows are post-D2-fix output that the "
                "accepted measurement does NOT cover; the packet claims no "
                "label soundness, and a LABEL_UNSOUND baseline on the pre-fix "
                "chain is a warning the jurist must see, never a verdict on "
                "these rows"
            ),
        },
        "frontier_map_semantics": {
            "team_run_id": semantics.get("team_run_id"),
            "accept_commit_on_main": semantics.get("accept_commit_on_main"),
            "promoted_decision": semantics.get("promoted_decision"),
            "per_bundle": semantics.get("per_bundle"),
            "measured_population": semantics.get("measured_population"),
            "covers_this_packet": False,
            "consequence_for_this_packet": (
                "no in-budget alternative geometry passed, so the shipped "
                "projection stays and geometry work closes until after the "
                "human gate; the FAIL verdict on the pre-rebuild bundles is "
                "disclosed to the jurist, not hidden"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("harvest", "disclosure", "sweep"))
    ap.add_argument("--accepted-root", type=Path,
                    default=Path("/tmp/lex_accepted/frontier"),
                    help="accepted Frontier mounts root (harvest only)")
    ap.add_argument("--out", type=Path, default=SNAPSHOT_PATH)
    ap.add_argument("--snapshot", type=Path, default=None,
                    help="alternate snapshot to read (disclosure only)")
    args = ap.parse_args(argv)
    if args.command == "harvest":
        try:
            snap = harvest(args.accepted_root)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"harvest failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 6
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(json.dumps({"harvested": str(args.out),
                          "counter_verdict": snap["frontier_counter_label_integrity"]["verdict"],
                          "map_promoted": snap["frontier_map_semantics"]["promoted_decision"][:80]},
                         indent=2))
        return 0
    if args.command == "sweep":
        print(json.dumps(sweep(args.accepted_root, args.snapshot), indent=2,
                         ensure_ascii=False))
        return 0
    print(json.dumps(disclosure(args.snapshot), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
