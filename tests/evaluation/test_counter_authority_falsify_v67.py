#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority falsifier for the
query-map MVP, pinned to the V3 packet-of-record (39319405429) under
factory direction v67.

REUSE-FIRST: imports and uses the ACCEPTED ``evaluation.counter_authority_surface_falsifier``
module unchanged.  No new thresholds, gates, tokenisers, rubrics or stoplists.
No universal-174k benchmark rerun.

EXACT LANE QUESTION (v67):
  On the exact V3 packet-of-record bytes (39319405429), does the served
  bundle satisfy the frozen mapping-free gates — especially
  ``mf::counter_authority_surface`` — such that the AI answer + visual map
  claim is supportable?  The benchmark produces a machine-record that
  product can use to answer this bounded question.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import counter_authority_surface_falsifier as C  # noqa: E402
from evaluation import mapping_free_recall_falsifier as M  # noqa: E402

# --- pinned packet-of-record ---
PACKET_OF_RECORD = "39319405429"

# Resolve product mount via the accepted measurement module (REUSE-FIRST)
MOUNT = M.resolve_mount(None)
PRODUCT_MOUNT_AVAILABLE = MOUNT is not None and MOUNT.is_dir()

# Direction version from current state
STATE_PATH = _REPO_ROOT / "state" / "evaluation.json"
direction_version = C._current_direction_version() if STATE_PATH.is_file() else None

if direction_version is None:
    print("WARNING: could not read direction_version from state/evaluation.json", file=sys.stderr)


def _run_measure(out_path: Path | None = None) -> dict:
    """Run the accepted measurement engine on the V3 packet-of-record.

    Reuses ``M.measure`` (mapping-free recall falsifier) and
    ``C.run`` (counter-authority surface falsifier wrapper) semantics.
    """
    packets = (PACKET_OF_RECORD,)

    if PRODUCT_MOUNT_AVAILABLE:
        # Real end-to-end on the accepted product mount
        # CRITICAL: --out must be provided to avoid writing to the committed tree
        out = out_path or (_REPO_ROOT / "results" / "evaluation" / "counter_authority_falsify_v67" / f"run_{direction_version}.json")
        code, rec = C.run("v67_falsify", out, str(MOUNT), _REPO_ROOT, packets)
        return {"code": code, "record": rec, "mode": "e2e_mount", "direction_version": direction_version}
    else:
        # Scratch mode: no mount -> vacuous exit, no product claim
        out = out_path or (_REPO_ROOT / "results" / "evaluation" / "counter_authority_falsify_v67" / f"run_{direction_version}_vacuous.json")
        code, rec = C.run("v67_falsify", out, None, _REPO_ROOT, packets)
        return {"code": code, "record": rec, "mode": "scratch_no_mount", "direction_version": direction_version}


def _summarize(rec: dict) -> str:
    """Human-readable summary of the record verdict."""
    verdict = rec.get("verdict", "UNKNOWN")
    n_failed = rec.get("n_failed", 0)
    n_gates = rec.get("n_gates", 0)
    n_passed = rec.get("n_passed", 0)
    n_reported = rec.get("n_reported", 0)
    failed_gates = rec.get("failed_gates", [])
    n_questions = rec.get("n_questions_measured", 0)
    packet_admitted = rec.get("packet_admitted", False)
    human_gate_ready = rec.get("human_gate_ready", False)
    ready_for_owner = rec.get("ready_for_owner_session", False)
    direction_v = rec.get("direction_version", direction_version)

    lines = [
        f"v67 counter-authority falsification benchmark",
        f"packet_of_record: {PACKET_OF_RECORD}",
        f"direction_version: {direction_v}",
        f"verdict: {verdict}",
        f"exit_code: {rec.get('exit_code')}",
        f"questions_measured: {n_questions}",
        f"gates: {n_passed}/{n_failed}/{n_reported} (total {n_gates})",
    ]
    if failed_gates:
        lines.append(f"failed_gates: {failed_gates}")
    lines.append(f"packet_admitted: {packet_admitted}")
    lines.append(f"human_gate_ready: {human_gate_ready}")
    lines.append(f"ready_for_owner_session: {ready_for_owner}")
    return "\n".join(lines)


def main() -> int:
    """Executable entry point: run the smallest possible retrieval/
    counter-authority falsification benchmark and print the record."""
    result = _run_measure()
    rec = result["record"]
    print(_summarize(rec))

    # Persist a minimal report alongside the record
    results_dir = _REPO_ROOT / "results" / "evaluation" / "counter_authority_falsify_v67"
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"RETRIEVAL_CA_BENCHMARK_{rec.get('run_id', 'v67')}.md"
    report_path.write_text(_summarize(rec) + "\n", encoding="utf-8")

    # Exit code matches the instrument contract
    return rec.get("exit_code", 1)


if __name__ == "__main__":
    sys.exit(main())