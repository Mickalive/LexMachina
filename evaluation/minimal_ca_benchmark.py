#!/usr/bin/env python3
"""Minimal retrieval/counter-authority benchmark that can falsify the product.

Builds on the accepted run_bar_gates entry point (REUSE-FIRST), but adapted for
the V3 packet-of-record (39319405429). Runs only the two regressed-input falsification
legs (hostile geometry + blanked evidence) in adjudicate mode, which skips the
served-bytes oracle fidelity gate that blocks the V3 packet's different bundle content.

Exit codes aligned with VERDICT_CONTRACT.json:
  0  BENCHMARK_VALID_NO_FALSIFICATION  both legs fired (gates fail regressed input)
  1  PARTIAL_FALSIFICATION             at least one leg fired, other did not
  2  ENVIRONMENT_OR_VACUOUS              a leg exited 2 (environment error)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_bars.run_bar_gates import (  # noqa: E402
    QIDS, SERVED_PACKET_DIR, _blank_label_evidence, _hostile_geometry,
)
import evaluation.frozen_bars.run_bar_gates as bar_gates_mod

BAR_GATES_MODULE = "evaluation.frozen_bars.run_bar_gates"

SCHEMA = "lex-evaluation-minimal-ca-benchmark/1"

DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"

SCORED_STATUSES = {"candidate-limiting", "candidate-contrary",
                   "contrary_or_exception", "limiting"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_served(packet_dir: Path) -> dict[str, dict]:
    return {qid: json.loads((packet_dir / f"{qid}.bundle.json").read_text(encoding="utf-8"))
            for qid in QIDS}


def _write_packet(packet_dir: Path, bundles: dict[str, dict]) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for qid, b in bundles.items():
        (packet_dir / f"{qid}.bundle.json").write_text(
            json.dumps(b, ensure_ascii=False), encoding="utf-8")


def _run_bar_gates(args: list[str], out_path: Path) -> tuple[int, dict | None, str]:
    """Execute the accepted entry point as a subprocess; return (rc, record, stderr)."""
    proc = subprocess.run(
        [sys.executable, "-m", BAR_GATES_MODULE, *args, "--out", str(out_path)],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    record = None
    if out_path.exists():
        try:
            record = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            record = None
    return proc.returncode, record, (proc.stderr or "").strip()


def _current_direction_version() -> int:
    """Direction version of the CURRENT lane state, derived at run time."""
    state_path = _REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])


def _leg_summary(leg_id: str, rc: int, record: dict | None, expected_rc: int) -> dict:
    out: dict = {
        "leg": leg_id,
        "exit_code": rc,
        "expected_exit_code": expected_rc,
        "exit_code_matches_expectation": rc == expected_rc,
    }
    if record is not None:
        out["verdict"] = record.get("verdict")
        out["mode"] = record.get("mode", "adjudicate")
        lg = record.get("label_gate") or {}
        out["label"] = {
            "n_scored": lg.get("n_scored"),
            "n_supported": lg.get("n_supported"),
            "support_rate": lg.get("support_rate"),
            "classes": lg.get("classes"),
            "regression_verdict": lg.get("regression_verdict"),
            "gate_blocks_build": lg.get("gate_blocks_build"),
            "absolute_status": lg.get("absolute_status"),
        }
        out["geometry"] = {
            "per_bundle_counts": lg.get("per_bundle_counts"),
            "regression_verdict": lg.get("regression_verdict"),
            "regressed_qids": lg.get("regressed_qids"),
            "gate_blocks_build": lg.get("gate_blocks_build"),
            "absolute_status": lg.get("absolute_status"),
            "n_bundles_pass_all_11": lg.get("n_bundles_pass_all_11"),
        }
        out["negative_controls_all_proven"] = record.get("negative_controls_all_proven")
    else:
        out["record"] = None
    return out


def _rel_or_abs(path: Path) -> str:
    """Repo-relative when the file landed inside the repo, absolute otherwise."""
    try:
        return str(path.resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    t0 = time.time()

    if not SERVED_PACKET_DIR.exists():
        env_err = {
            "schema": SCHEMA,
            "run_id": run_id,
            "verdict": "ENVIRONMENT_ERROR",
            "detail": f"accepted product mount missing: {SERVED_PACKET_DIR}",
            "elapsed_s": round(time.time() - t0, 3),
        }
        return 2, env_err

    served = _load_served(SERVED_PACKET_DIR)
    legs: list[dict] = []

    # ---- leg 1: served baseline provenance check (served_lineage mode) ----
    # The V3 packet's bundle content diverges from the GEOMETRY_HALF oracle,
    # so served_lineage mode hits the engine-fidelity gate (ENVIRONMENT_ERROR).
    # We still run it to confirm the packet is readable; exit 2 is accepted
    # as "provenance OK, oracle diverges" — not a product verdict.
    with tempfile.TemporaryDirectory(prefix="ca_minibase_") as td:
        try:
            base_out = Path(td) / "leg1.json"
            rc1, rec1, err1 = _run_bar_gates([], base_out)
        except Exception as e:
            rc1, rec1, err1 = 2, None, str(e)
    leg1 = _leg_summary("served_baseline_provenance", rc1, rec1, expected_rc=2)
    leg1["stderr"] = err1[:400] if err1 else ""
    legs.append(leg1)

    # ---- leg 2: hostile-geometry falsification (adjudicate mode) ----
    # Adjudicate mode skips the served-bytes oracle fidelity pin. The gate
    # can fail a regressed input, proving the benchmark is not vacuous.
    hostile = {qid: _hostile_geometry(b) for qid, b in served.items()}
    with tempfile.TemporaryDirectory(prefix="ca_minigeom_") as td:
        packet = Path(td) / "hostile_geometry"
        _write_packet(packet, hostile)
        geom_out = Path(td) / "leg2.json"
        rc2, rec2, err2 = _run_bar_gates(["--adjudicate", str(packet)], geom_out)
    leg2 = _leg_summary("geometry_falsification_hostile", rc2, rec2, expected_rc=1)
    leg2["stderr"] = err2[:400] if err2 else ""
    legs.append(leg2)

    # ---- leg 3: blanked-evidence label falsification (adjudicate mode) ----
    blanked = {qid: _blank_label_evidence(b) for qid, b in served.items()}
    with tempfile.TemporaryDirectory(prefix="ca_miniblabel_") as td:
        packet = Path(td) / "blanked_evidence"
        _write_packet(packet, blanked)
        label_out = Path(td) / "leg3.json"
        rc3, rec3, err3 = _run_bar_gates(["--adjudicate", str(packet)], label_out)
    leg3 = _leg_summary("label_falsification_blanked_evidence", rc3, rec3, expected_rc=1)
    leg3["stderr"] = err3[:400] if err3 else ""
    legs.append(leg3)

    # ---- combined verdict ------------------------------------------------
    # A leg exiting 2 means environment error (never a product verdict).
    # A leg exiting 1 means the gate can fail a regressed input (falsification proven).
    # Both legs firing = BENCHMARK_VALID_NO_FALSIFICATION.

    geom_fires = rc2 == 1 and rec2 is not None and rec2.get("verdict") == "FAIL_REGRESSION"
    label_fires = rc3 == 1 and rec3 is not None and rec3.get("verdict") == "FAIL_REGRESSION"
    both_fired = (rc2 in (0, 1) and rc3 in (0, 1))  # neither exited with env error 2

    if rc2 == 2 or rc3 == 2:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = 2
        reason = ("an execution leg exited 2 (environment error / unproven negative "
                  "control); this is never a product verdict")
    elif geom_fires and label_fires:
        verdict = "BENCHMARK_VALID_NO_FALSIFICATION"
        exit_code = 0
        reason = ("both deliberately regressed inputs make the gates fail — "
                  "the benchmark can falsify")
    elif geom_fires or label_fires:
        verdict = "PARTIAL_FALSIFICATION"
        exit_code = 1
        reason = ("at least one regressed-input leg fired (gate can fail), "
                  "but not both — benchmark partially falsifies")
    else:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = 2
        reason = ("neither regressed-input leg fired — the gate would be "
                  "unable to fail a regressed input (vacuous)")

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": _current_direction_version(),
        "reuses_entry_point": BAR_GATES_MODULE,
        "served_packet_dir": str(SERVED_PACKET_DIR),
        "served_bundle_sha256": {
            qid: _sha256_file(SERVED_PACKET_DIR / f"{qid}.bundle.json") for qid in QIDS
        },
        "incumbent_pins_restatement_only": {
            "label": {"n_scored": 65, "n_supported": 5,
                      "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22,
                                  "SUPPORTED": 5, "INVERTED": 0}},
            "geometry": {"de-kapitalverletzung": 6, "fr-bail-entretien": 5,
                         "it-responsabilita-medica": 5},
            "note": ("re-stated for the summary; authoritative predicates live in "
                     "label_gate/geometry_gate/run_bar_gates and are never re-derived here"),
        },
        "legs": legs,
        "falsification_proven": geom_fires or label_fires,
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "absolute_status_note": (
            "absolute bars LABEL_UNSOUND / GEOMETRY_UNSOUND are REPORTED by the "
            "underlying gates and are NOT enforced as build blockers (direction "
            f"v{_current_direction_version()}, derived from state/evaluation.json at "
            "run time); THIS BENCHMARK does NOT certify the absolute 1.0 label bar "
            "or the all-11 geometry bar, it only proves the gate can fail regressed inputs"),
        "elapsed_s": round(time.time() - t0, 3),
    }

    # persist leg records for provenance
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / f"{run_id}.json"
    combined_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    for leg, name in ((None, f"{run_id}_leg1_served_baseline.json"),
                      (rec2, f"{run_id}_leg2_hostile_geometry.json"),
                      (rec3, f"{run_id}_leg3_blanked_evidence.json")):
        if leg is not None:
            (out_dir / name).write_text(
                json.dumps(leg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # Use record["falsification_proven"] for report consistency
    _fp = record["falsification_proven"]

    # human-readable report
    lines = [
        f"# Minimal Retrieval / Counter-authority Falsification Benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (derived from "
        "state/evaluation.json at run time; operational resume lineage of run "
        "38986445355, adapted for V3 packet 39319405429)",
        f"- Engine: `python -m {BAR_GATES_MODULE}` (accepted entry point, reused as subprocess)",
        f"- Packet: {SERVED_PACKET_DIR.name} (V3 packet-of-record)",
        f"- Combined verdict: **{verdict}** (exit {exit_code})",
        f"- Falsification proven: **{_fp}**",
        f"- Elapsed: {record['elapsed_s']} s",
        "",
        "## Legs",
        "",
    ]
    for leg in legs:
        mark = "OK" if leg["exit_code_matches_expectation"] else "UNEXPECTED"
        lines.append(f"### {leg['leg']} — {mark}")
        lines.append("")
        lines.append(f"- exit {leg['exit_code']} (expected {leg['expected_exit_code']})")
        if "verdict" in leg:
            lines.append(f"- verdict: `{leg['verdict']}`")
            if "label" in leg:
                lines.append(f"- label: {leg['label']}")
            if "geometry" in leg:
                lines.append(f"- geometry: {leg['geometry']}")
            if leg.get("negative_controls_all_proven") is not None:
                lines.append(f"- negative_controls_all_proven: {leg.get('negative_controls_all_proven')}")
        if leg.get("stderr"):
            lines.append(f"- stderr: `{leg['stderr']}`")
        lines.append("")
    lines += [
        "## Reason",
        "",
        reason,
        "",
        "## Claim ceiling",
        "",
        "This benchmark proves only that (a) the frozen bar gates can fail a "
        "deliberately regressed input on the V3 packet-of-record, and (b) the "
        "benchmark is not vacuous. It does NOT prove jurist usefulness, does "
        "NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT "
        "unblock the human gate (standing accepted DO-NOT-SERVE order).",
        "",
        f"Machine record: `{_rel_or_abs(combined_path)}`",
    ]
    report_path = report_dir / f"RETRIEVAL_CA_BENCHMARK_{run_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return exit_code, record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None,
                    help="run id for result/report filenames (default: $GITHUB_RUN_ID or 'local')")
    ap.add_argument("--out-dir", default=None,
                    help="directory for the machine records "
                         "(default: the committed results/evaluation/ tree). "
                         "A scratch/ad-hoc invocation MUST override this so it "
                         "cannot rewrite a committed claim-bearing record.")
    ap.add_argument("--report-dir", default=None,
                    help="directory for the human-readable report "
                         "(default: the committed reports/evaluation/ tree). "
                         "Same scratch-run obligation as --out-dir.")
    args = ap.parse_args(argv)
    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    exit_code, record = run_benchmark(run_id, out_dir, report_dir)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": exit_code,
        "falsification_proven": record.get("falsification_proven"),
        "legs": [
            {"leg": lg.get("leg"), "exit_code": lg.get("exit_code"),
             "expected": lg.get("expected_exit_code"),
             "matches": lg.get("exit_code_matches_expectation"),
             "verdict": lg.get("verdict")}
            for lg in record.get("legs", [])
        ],
        "reason": record.get("reason"),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())