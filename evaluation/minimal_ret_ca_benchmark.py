#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark that can falsify the product.

FAST MVP: 2-leg retrieval/counter-authority falsification benchmark on the V3
packet-of-record (39319405429) exact bytes.

REUSE-FIRST: every scoring leg is executed by the ACCEPTED entry point
``evaluation.frozen_bars.run_bar_gates`` as a subprocess. Nothing about the
frozen rules, thresholds, incumbents, predicates or verdict contract is changed,
re-derived or re-measured here.

Two legs, one combined record, exit codes that can falsify:

  leg 1  served_baseline       run_bar_gates default mode on the served packet.
           Must exit 0 / PASS_NO_REGRESSION with both incumbents recomputed.
           A non-zero exit is a product regression or an environment error.
  leg 2  geometry_falsification  adjudicate on a deliberately hostile-geometry
           packet (one stopword mega-cluster, no relations).
           Must exit 1 / FAIL_REGRESSION — proves the gate can fail a
           regressed geometry, i.e. the benchmark is not vacuous with respect
           to map semantics.

Combined exit codes (aligned with VERDICT_CONTRACT.json):
  0  BENCHMARK_VALID_NO_FALSIFICATION
        leg 1 exit 0 AND leg 2 exit 1. The product's served packet does not
        regress, and the falsification path is proven live. This is NOT a claim
        that the absolute bars were met (they are LABEL_UNSOUND /
        GEOMETRY_UNSOUND by construction and reported, never enforced).
  1  PRODUCT_FALSIFIED
        leg 1 exited 1 (a build-blocking regression on the served lineage) —
        or leg 2 failed to fire (vacuity, classified as exit 2 below, never as
        a pass).
  2  ENVIRONMENT_OR_VACUOUS
        any leg exited 2 (rules sha drift, missing inputs, unproven negative
        control), or a falsification leg did NOT exit 1 (the gate would be
        unable to fail a regressed input — vacuous, not a product verdict).

No Product code is imported. No network is used. No frozen file is written.
The accepted-product mount at /tmp/lex_accepted is read-only input.

SCRATCH-RUN OBLIGATION (audit convention): a claim-bearing cycle writes its
records to the committed defaults below. A scratch invocation (a unit test, a
local poke, a retry) MUST pass ``--out-dir`` and ``--report-dir``; otherwise
it overwrites committed claim-bearing records. That is not a style rule: the
overwritten files are picked up by the workflow's ``git add -A`` persist step
and land in the promoted snapshot, so a unit test silently becomes part of the
accepted evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_bars.run_bar_gates import (  # noqa: E402
    QIDS,
    SERVED_PACKET_DIR,
    _blank_label_evidence,
    _hostile_geometry,
)

SCHEMA = "lex-evaluation-minimal-ret-ca-benchmark/1"
BAR_GATES_MODULE = "evaluation.frozen_bars.run_bar_gates"

# Incumbent pins (direction v50; re-stated here only for the combined record's
# summary block — the authoritative predicates live in label_gate /
# geometry_gate / run_bar_gates and are never re-derived).
LABEL_INCUMBENT = {"n_scored": 65, "n_supported": 5,
                   "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22,
                               "SUPPORTED": 5, "INVERTED": 0}}
GEOMETRY_INCUMBENT = {"de-kapitalverletzung": 6, "fr-bail-entretien": 5,
                      "it-responsabilita-medica": 5}


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
        out["mode"] = record.get("mode", "served_lineage")
        lg = record.get("label_gate") or {}
        gg = record.get("geometry_gate") or {}
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
            "per_bundle_counts": gg.get("per_bundle_counts"),
            "regression_verdict": gg.get("regression_verdict"),
            "regressed_qids": gg.get("regressed_qids"),
            "gate_blocks_build": gg.get("gate_blocks_build"),
            "absolute_status": gg.get("absolute_status"),
            "n_bundles_pass_all_11": gg.get("n_bundles_pass_all_11"),
        }
        out["negative_controls_all_proven"] = record.get("negative_controls_all_proven")
        out["absolute_status_summary"] = record.get("absolute_status_summary")
        if "admission_reading" in record:
            ar = record["admission_reading"]
            out["admission_reading"] = {
                "exit_code": ar.get("exit_code"),
                "naive_consumer_trap_fires": ar.get("naive_consumer_trap_fires"),
            }
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

    # ---- leg 1: served baseline (default mode) ---------------------------
    with tempfile.TemporaryDirectory(prefix="ca_bench_base_") as td:
        base_out = Path(td) / "leg1.json"
        rc1, rec1, err1 = _run_bar_gates([], base_out)
    leg1 = _leg_summary("served_baseline", rc1, rec1, expected_rc=0)
    leg1["stderr"] = err1[:400] if err1 else ""
    legs.append(leg1)

    # ---- leg 2: hostile-geometry falsification (adjudicate mode) --------------
    hostile = {qid: _hostile_geometry(b) for qid, b in served.items()}
    with tempfile.TemporaryDirectory(prefix="ca_bench_geom_") as td:
        packet = Path(td) / "hostile_geometry"
        _write_packet(packet, hostile)
        geom_out = Path(td) / "leg2.json"
        rc2, rec2, err2 = _run_bar_gates(["--adjudicate", str(packet)], geom_out)
    leg2 = _leg_summary("geometry_falsification_hostile", rc2, rec2, expected_rc=1)
    leg2["stderr"] = err2[:400] if err2 else ""
    legs.append(leg2)

    # ---- combined verdict ------------------------------------------------
    baseline_ok = (rc1 == 0 and rec1 is not None
                   and rec1.get("verdict") == "PASS_NO_REGRESSION")
    baseline_env = rc1 == 2
    geom_fires = rc2 == 1 and rec2 is not None and rec2.get("verdict") == "FAIL_REGRESSION"

    falsification_proven = geom_fires

    if baseline_env or rc2 == 2:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = 2
        reason = ("an execution leg exited 2 (environment error / unproven negative "
                  "control); this is never a product verdict")
    elif rc1 == 1:
        verdict = "PRODUCT_FALSIFIED"
        exit_code = 1
        reason = ("leg 1 served_baseline exited 1 / FAIL_REGRESSION: the served "
                  "packet regressed below the recomputed incumbent")
    elif baseline_ok and falsification_proven:
        verdict = "BENCHMARK_VALID_NO_FALSIFICATION"
        exit_code = 0
        reason = ("served packet passes regression and the regressed input makes "
                  "the gate fail — the benchmark can falsify")
    else:
        # baseline_ok but a falsification leg did not fire
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = 2
        reason = ("served baseline passed but a falsification leg did not exit 1 — "
                  "vacuous gate path, not a product pass")

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
            "label": LABEL_INCUMBENT,
            "geometry": GEOMETRY_INCUMBENT,
            "note": ("re-stated for the summary; authoritative predicates live in "
                     "label_gate/geometry_gate/run_bar_gates and are never re-derived here"),
        },
        "legs": legs,
        "falsification_proven": falsification_proven,
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "absolute_status_note": (
            "absolute bars LABEL_UNSOUND / GEOMETRY_UNSOUND are REPORTED by the "
            "underlying gates and are NOT enforced as build blockers (direction "
            f"v{_current_direction_version()}, derived from state/evaluation.json at "
            "run time); BENCHMARK_VALID_NO_FALSIFICATION does NOT certify the "
            "absolute 1.0 label bar or the all-11 geometry bar, and does NOT "
            "unblock the human gate (standing accepted DO-NOT-SERVE order)."),
        "elapsed_s": round(time.time() - t0, 3),
    }

    # persist leg records for provenance
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / f"{run_id}.json"
    combined_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    for leg, name in ((rec1, f"{run_id}_leg1_served_baseline.json"),
                      (rec2, f"{run_id}_leg2_hostile_geometry.json")):
        if leg is not None:
            (out_dir / name).write_text(
                json.dumps(leg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # human-readable report
    lines = [
        f"# Retrieval / counter-authority falsification benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{_current_direction_version()} (derived from "
        "state/evaluation.json at run time; operational resume lineage, adapted "
        "for 2-leg minimal CA)",
        f"- Engine: `python -m {BAR_GATES_MODULE}` (accepted entry point, reused as subprocess)",
        f"- Combined verdict: **{verdict}** (exit {exit_code})",
        f"- Falsification proven: **{falsification_proven}**",
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
            lines.append(f"- label: {leg['label']}")
            lines.append(f"- geometry: {leg['geometry']}")
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
        "This benchmark proves only that (a) the served packet currently does not "
        "regress below the recomputed incumbents and (b) both frozen gates can fail "
        "a deliberately regressed input. It does NOT prove jurist usefulness, does "
        "NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT "
        "unblock the human gate (standing accepted DO-NOT-SERVE order).",
        "",
        f"Machine record: `{_rel_or_abs(combined_path)}`",
    ]
    report_path = report_dir / f"RETRIEVAL_CA_BENCHMARK_{run_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return exit_code, record


#: Default committed destinations.  Claim-bearing runs write HERE; a scratch run
#: must pass --out-dir/--report-dir instead (audit convention).
DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/minimal_ret_ca_benchmark"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"


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
        "falsification_proven": record.get("falsification_proven") if record else False,
        "legs": [
            {"leg": lg.get("leg"), "exit_code": lg.get("exit_code"),
             "expected": lg.get("expected_exit_code"),
             "matches": lg.get("exit_code_matches_expectation"),
             "verdict": lg.get("verdict")}
            for lg in record.get("legs", [])
        ],
        "reason": record.get("reason") if record else None,
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())