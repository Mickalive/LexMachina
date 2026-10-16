"""Executable reachability matrix for the frozen-bar gates' verdict states.

Proves, on real accepted-product inputs, every reachability claim the
VERDICT_CONTRACT.json makes — including the two that matter for Product's
packet-admission obligation (direction v50, product obligation (1)):

1. the entry point's exit-1 (build-blocking) path is UNREACHABLE through
   served_lineage mode on every input (served bytes recompute the incumbent
   by construction; any byte drift is refused as exit 2 before scoring);
2. the naive-consumer trap is REACHABLE: one adjudicated packet carries
   exit 0 AND gate_blocks_build false AND label n_supported 0 in the same
   record, i.e. a consumer reading only "exit 0 = the label bar was met"
   would admit a packet whose scored counter-label support is zero.

Stdlib only, no network, no Product code imported, no frozen artifact
modified; the accepted-product mount is read-only. Probe packets are built
in a temporary directory and discarded; the durable evidence is the written
reachability record.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent))

from evaluation.frozen_bars import geometry_gate, label_gate, verdict_contract  # noqa: E402
from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR  # noqa: E402

SCORED_STATUSES = {"candidate-limiting", "candidate-contrary",
                   "contrary_or_exception", "limiting"}


def _load_served(packet_dir: Path) -> dict[str, dict]:
    return {qid: json.loads((packet_dir / f"{qid}.bundle.json").read_text(encoding="utf-8"))
            for qid in QIDS}


def _write(packet_dir: Path, bundles: dict[str, dict]) -> None:
    for qid, b in bundles.items():
        (packet_dir / f"{qid}.bundle.json").write_text(json.dumps(b), encoding="utf-8")


def probe_blanked_full_population(bundles: dict[str, dict]) -> dict[str, dict]:
    """Label regression at the pinned 65-row population (support 5 -> 0)."""
    out = {}
    for qid, b in bundles.items():
        b = copy.deepcopy(b)
        for d in b.get("decisions", []):
            if d.get("counter_status") in SCORED_STATUSES:
                d["counter_evidence"] = ""
        out[qid] = b
    return out


def probe_hostile_geometry(bundles: dict[str, dict]) -> dict[str, dict]:
    """Geometry regression: one stopword mega-cluster, no relations."""
    out = {}
    for qid, b in bundles.items():
        b = copy.deepcopy(b)
        decs = b.get("decisions", [])
        for d in decs:
            d["cluster_id"] = 0
            d["is_outlier"] = False
        b["clusters"] = [{"cluster_id": 0, "label": "der und die",
                          "member_ids": [d.get("decision_id") for d in decs][:50],
                          "size": len(decs)}]
        b["relations"] = []
        out[qid] = b
    return out


def probe_naive_consumer_trap(bundles: dict[str, dict]) -> dict[str, dict]:
    """Label support collapsed to 0 at a CHANGED population, geometry untouched.

    Every scored counter row loses its evidence AND exactly one scored counter
    row per bundle is re-statused out of the scored set, so the scored
    population leaves the pinned 65 rows (frozen label regression predicate
    becomes NOT_APPLICABLE) while the geometry inputs are byte-for-byte the
    served ones apart from the counter_status/counter_evidence text fields,
    which no geometry criterion reads.
    """
    out = {}
    for qid, b in bundles.items():
        b = copy.deepcopy(b)
        flipped = False
        for d in b.get("decisions", []):
            if d.get("counter_status") in SCORED_STATUSES:
                d["counter_evidence"] = ""
                if not flipped:
                    d["counter_status"] = "supporting"
                    flipped = True
        out[qid] = b
    return out


def probe_one_byte_drift(bundles: dict[str, dict]) -> dict[str, dict]:
    out = {qid: copy.deepcopy(b) for qid, b in bundles.items()}
    q0 = QIDS[0]
    out[q0] = copy.deepcopy(out[q0])
    out[q0]["_drift"] = True  # any byte-level change; content-irrelevant key
    return out


def run_cli(packet_dir: Path, adjudicate: bool) -> tuple[int, dict]:
    """Run the entry point; return (exit_code, FULL record via --out).

    stdout carries only the summary (label_gate/geometry_gate excluded by
    design), so the durable fields must be read from the --out file.
    """
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "record.json"
        cmd = [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates", "--out", str(out_path)]
        if adjudicate:
            cmd += ["--adjudicate", str(packet_dir)]
        else:
            cmd += ["--packet-dir", str(packet_dir)]
        p = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(_BAR_DIR.parent.parent))
        if out_path.exists():
            record = json.loads(out_path.read_text(encoding="utf-8"))
        else:
            try:
                record = json.loads(p.stdout)
            except json.JSONDecodeError:
                record = {"_unparsed_stdout_tail": p.stdout[-400:],
                          "_stderr_tail": p.stderr[-400:]}
        return p.returncode, record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet-dir", default=str(SERVED_PACKET_DIR))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--bar-out-dir", default=None,
                    help="where adjudicate records are written "
                         "(default results/evaluation/bar_gates; tests point it at a temp dir "
                         "so a test run never mutates committed results)")
    args = ap.parse_args(argv)
    packet_dir = Path(args.packet_dir)
    out_dir = Path(args.out_dir) if args.out_dir else (
        _BAR_DIR.parent.parent / "results" / "evaluation" / "verdict_contract")
    bar_out = Path(args.bar_out_dir) if args.bar_out_dir else (
        _BAR_DIR.parent.parent / "results" / "evaluation" / "bar_gates")
    out_dir.mkdir(parents=True, exist_ok=True)
    bar_out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    served = _load_served(packet_dir)

    matrix: list[dict] = []

    def record_probe(name: str, bundles: dict[str, dict] | None, adjudicate: bool,
                     expectation: str) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            if bundles is None:
                target = packet_dir  # served bytes as-is
            else:
                _write(td_path, bundles)
                target = td_path
            exit_code, record = run_cli(target, adjudicate=adjudicate)
            key = {
                "label_regression_verdict": record.get("label_gate", {}).get("regression_verdict"),
                "label_n_scored": record.get("label_gate", {}).get("n_scored"),
                "label_n_supported": record.get("label_gate", {}).get("n_supported"),
                "label_blocks": record.get("label_gate", {}).get("gate_blocks_build"),
                "geometry_regression_verdict": record.get("geometry_gate", {}).get("regression_verdict"),
                "geometry_counts": record.get("geometry_gate", {}).get("per_bundle_counts"),
                "geometry_blocks": record.get("geometry_gate", {}).get("gate_blocks_build"),
                "verdict": record.get("verdict"),
            }
            trap = (exit_code == 0
                    and key["label_regression_verdict"] == "NOT_APPLICABLE"
                    and key["label_n_supported"] == 0)
            matrix.append({
                "probe": name,
                "mode": "adjudicate" if adjudicate else "served_lineage",
                "exit_code": exit_code,
                "expectation": expectation,
                "key_fields": key,
                "naive_consumer_trap": trap,
            })
            if adjudicate and exit_code != 2 and bundles is not None:
                (bar_out / f"{args.run_id}_adjudicate_{name}.json").write_text(
                    json.dumps(record, indent=1), encoding="utf-8")

    # ---- served_lineage mode: H1/H2 ------------------------------------
    record_probe("served_bytes", None, adjudicate=False,
                 expectation="exit 0 PASS_NO_REGRESSION (incumbent recompute)")
    record_probe("served_bytes_one_byte_drift", probe_one_byte_drift(served), adjudicate=False,
                 expectation="exit 2 ENVIRONMENT_ERROR (byte pin refuses before scoring)")
    record_probe("blanked_full_population", probe_blanked_full_population(served), adjudicate=False,
                 expectation="exit 2 ENVIRONMENT_ERROR (byte pin; blocking path unreachable)")
    record_probe("hostile_geometry", probe_hostile_geometry(served), adjudicate=False,
                 expectation="exit 2 ENVIRONMENT_ERROR (byte pin; blocking path unreachable)")
    record_probe("naive_consumer_trap", probe_naive_consumer_trap(served), adjudicate=False,
                 expectation="exit 2 ENVIRONMENT_ERROR (byte pin; blocking path unreachable)")

    # ---- adjudicate mode: H3/H4 ----------------------------------------
    record_probe("served_bytes", None, adjudicate=True,
                 expectation="exit 0, same verdict as default mode (pin is provenance, not threshold)")
    record_probe("blanked_full_population", probe_blanked_full_population(served), adjudicate=True,
                 expectation="exit 1: label FAIL_REGRESSION blocks at the pinned 65-row population")
    record_probe("hostile_geometry", probe_hostile_geometry(served), adjudicate=True,
                 expectation="exit 1: geometry FAIL_REGRESSION blocks on the three frozen qids")
    record_probe("naive_consumer_trap", probe_naive_consumer_trap(served), adjudicate=True,
                 expectation="exit 0 with label NOT_APPLICABLE and n_supported 0 — the trap")

    try:
        run_id_field: int | str = int(args.run_id)
    except ValueError:  # test invocations use non-numeric ids
        run_id_field = args.run_id
    reachability = {
        "schema": "lex-evaluation-bar-verdict-reachability/1",
        "run": run_id_field,
        "lane": "evaluation",
        "direction_version": 50,
        "verdict_contract_sha256": verdict_contract.contract_digest(),
        "packet_dir": str(packet_dir),
        "probes": matrix,
        "claims_tested": {
            "default_exit1_unreachable": all(
                m["exit_code"] != 1 for m in matrix if m["mode"] == "served_lineage"),
            "adjudicate_exit1_reachable": any(
                m["exit_code"] == 1 for m in matrix if m["mode"] == "adjudicate"),
            "naive_consumer_trap_reachable": any(m["naive_consumer_trap"] for m in matrix),
        },
        "elapsed_s": round(time.time() - t0, 3),
    }
    (out_dir / f"{args.run_id}_reachability.json").write_text(
        json.dumps(reachability, indent=1), encoding="utf-8")
    print(json.dumps({"claims_tested": reachability["claims_tested"],
                      "probes": [{"probe": m["probe"], "mode": m["mode"],
                                  "exit_code": m["exit_code"]} for m in matrix]}, indent=1))
    ok = (reachability["claims_tested"]["default_exit1_unreachable"]
          and reachability["claims_tested"]["adjudicate_exit1_reachable"]
          and reachability["claims_tested"]["naive_consumer_trap_reachable"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
