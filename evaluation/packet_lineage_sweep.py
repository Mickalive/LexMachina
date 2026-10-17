#!/usr/bin/env python3
"""Smallest executable test of whether the two accepted frozen-bar gates are
sound CI gates on the product's OWN bundle lineage.

Why this exists
---------------
Direction v50 handed this lane the two frozen-bar gates and told it to own the
BAR, not the CANDIDATE. Both gates have been executed exactly once against
exactly one packet: the historical served packet 38839347028, which is also the
packet their incumbents were computed from. Nothing has ever asked the gate the
only question that matters for its intended consumer:

    does FAIL_REGRESSION mean "this packet is worse", or does it just mean
    "this packet is not byte-identical to the one the incumbent came from"?

Factory direction v50 also obliges Product to make the two accepted bar verdicts
a machine-readable input of packet admission. That obligation is only safe if
the gate never blocks a packet an independent audit already accepted. This
module tests that, executably, and it is the smallest thing that can falsify
the wiring.

Design constraints honoured (REUSE-FIRST, factory-wide requirement 18)
----------------------------------------------------------------------
* Both RULES files are re-hashed to the accepted sha256 BEFORE any scoring runs.
* Every verdict comes from the ACCEPTED entry point
  `python -m evaluation.frozen_bars.run_bar_gates`, invoked as a subprocess in
  its own documented `--adjudicate` mode. No scoring is re-implemented here.
* `geometry_gate` is imported only to READ the already-accepted per-criterion
  mask and per-criterion value/bar that the accepted engine computed. No
  criterion, bar, threshold or predicate is re-derived, re-tuned or relaxed.
* No threshold is invented. Every predicate is a restatement of the gate
  semantics direction v50 already fixed. F3 is descriptive and never enforced.
* No Product code is imported. No network is used. The accepted-product mount is
  read-only input. Nothing frozen is written.

The claim-bearing hypothesis, population, predicates, non-vacuity battery and
success rule were frozen in
results/evaluation/packet_lineage_sweep/FROZEN_HYPOTHESIS_38993062549.json at
commit f318ed2b, before this module was executed for the first time.

Exit codes (frozen)
-------------------
0  GATE_VALID_ON_ACCEPTED_LINEAGE  -- no predicate fired; battery proven.
1  GATE_FALSIFIED_ON_ACCEPTED_LINEAGE -- F1 fired: the gate blocks a packet an
   independent audit accepted. First-class negative result ABOUT THE BARS.
2  ENVIRONMENT_OR_UNPROVEN -- rules sha drift, empty population, or any battery
   element unproven. NOT a product verdict, NOT a pass, suppresses all findings.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_bars import geometry_gate  # noqa: E402

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
PACKET_ROOT_REL = "results/product/gate_packet"
AUDIT_ROOT_REL = "results/audit/product"

EXPECTED_RULES_SHA256 = {
    "RULES_LABEL.json": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "RULES_GEOMETRY.json": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
}

# The incumbent packet, i.e. the one both frozen gates were calibrated on and
# the one they regress against. Pinning it makes N2 (the must-not-fire
# negative control) a statement about a specific packet, not a vague one.
INCUMBENT_PACKET_ID = "38839347028"

EXIT_VALID = 0
EXIT_FALSIFIED = 1
EXIT_ENVIRONMENT = 2


# ---------------------------------------------------------------- helpers --
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_rules_identity(mount: Path | None = None) -> dict:
    """Re-hash both frozen RULES files against the accepted sha256.

    `mount` is unused by design: the local copies under evaluation/frozen_bars/
    are the ones this lane executes, so they are the ones that must be proved.
    """
    out = {}
    for name, expected in EXPECTED_RULES_SHA256.items():
        p = _REPO_ROOT / "evaluation" / "frozen_bars" / name
        if not p.exists():
            out[name] = {"path": str(p), "present": False, "matches": False}
            continue
        got = _sha256_file(p)
        out[name] = {"path": str(p), "present": True, "sha256": got,
                     "expected_sha256": expected, "matches": got == expected}
    out["all_match"] = all(v.get("matches") for v in out.values() if isinstance(v, dict))
    return out


def discover_packets(mount: Path = PRODUCT_MOUNT) -> dict:
    """Every gate packet on the accepted mount, with its qid set.

    Out-of-scope packets are DISCOVERED and recorded with a reason; they are
    never silently dropped, because their existence is itself part of what this
    sweep measures (coverage of the gate over the product's packet space).
    """
    root = mount / PACKET_ROOT_REL
    found: list[dict] = []
    if not root.is_dir():
        return {"root": str(root), "root_present": False, "packets": []}
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        qdir = child / "questions"
        if not qdir.is_dir():
            qdir = child
        present = {q: (qdir / f"{q}.bundle.json").exists() for q in QIDS}
        found.append({
            "packet_id": child.name,
            "questions_dir": str(qdir),
            "qids_present": {k: v for k, v in present.items() if v},
            "n_frozen_qids_present": sum(present.values()),
            "in_scope": all(present.values()),
            "out_of_scope_reason": (
                None if all(present.values()) else
                "packet does not carry all three frozen qids "
                f"(missing: {[q for q, v in present.items() if not v]}); the frozen "
                "rubric's anchors and query-term lexicons are pinned to the three "
                "frozen qids, so the gate cannot score it"
            ),
            "bundle_sha256": {q: _sha256_file(qdir / f"{q}.bundle.json")
                              for q in QIDS if present[q]},
        })
    return {"root": str(root), "root_present": True, "packets": found}


def read_audit(mount: Path, packet_id: str) -> dict:
    """Independent audit verdict for a packet's cycle, if one is on the mount."""
    p = mount / AUDIT_ROOT_REL / f"CYCLE_{packet_id}_GATE.json"
    if not p.exists():
        return {"audit_file": str(p), "present": False, "accepted": False,
                "reason": "no independent audit record for this cycle on the accepted mount"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"audit_file": str(p), "present": True, "accepted": False,
                "reason": f"audit record unreadable: {type(e).__name__}: {e}"}
    gate = d.get("gate")
    safe = d.get("safe_to_integrate")
    fixes = d.get("required_fixes")
    accepted = bool(gate == "PASS" and safe is True and (fixes is None or fixes == []))
    return {
        "audit_file": str(p),
        "present": True,
        "gate": gate,
        "safe_to_integrate": safe,
        "n_required_fixes": len(fixes) if isinstance(fixes, list) else None,
        "accepted": accepted,
        "reason": ("independent audit accepted this cycle"
                   if accepted else
                   f"audit verdict is not an acceptance (gate={gate!r}, "
                   f"safe_to_integrate={safe!r}, required_fixes={fixes!r})"),
        "claim_ceiling": d.get("claim_ceiling"),
    }


def _hostile_geometry(bundle: dict) -> dict:
    """Same lineage-matched regression the accepted gate already uses for its
    own geometry negative control. Reused by value, not re-derived: importing
    the accepted helper keeps the sweep's control byte-identical to the gate's.
    """
    from evaluation.frozen_bars.run_bar_gates import _hostile_geometry as accepted_hostile
    return accepted_hostile(copy.deepcopy(bundle))


def run_frozen_gate(questions_dir: Path, out_json: Path) -> dict:
    """Invoke the ACCEPTED entry point in adjudicate mode. No scoring here.

    Invocation is the same style the accepted
    `evaluation.benchmark_retrieval_counter_authority` already uses
    (`python -m evaluation.frozen_bars.run_bar_gates ... --out <path>`, cwd at
    the repo root). Two robustness measures are layered on it, and neither can
    turn a verdict into a non-verdict or the reverse:

    1. `PYTHONPATH` is set explicitly to the repo root in addition to `cwd`.
       `python -m` resolves the module through the child interpreter's
       `sys.path`; relying on cwd alone has been observed to fail
       intermittently in this sandbox with runpy's masked error
       "Error while finding module specification ... (ModuleNotFoundError:
       No module named 'evaluation.frozen_bars')", which is runpy re-raising an
       inner ImportError and is an ENVIRONMENT failure, not a gate verdict.
    2. ONE retry, and ONLY when the child produced no record file AND its stderr
       carries that masked-discovery signature. Exit 0 and exit 1 are accepted
       verdicts and are never retried, so a regression can never be laundered
       into an environment error or vice versa. Every attempt is recorded.
    """
    cmd = [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates",
           "--adjudicate", str(questions_dir), "--out", str(out_json)]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    attempts: list[dict] = []
    proc = None
    for attempt in range(2):
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(_REPO_ROOT), capture_output=True,
                              text=True, timeout=900, env=env)
        wrote_record = out_json.exists()
        masked_discovery = ("Error while finding module specification"
                            in (proc.stderr or "")) or \
                           ("No module named 'evaluation.frozen_bars'" in (proc.stderr or ""))
        attempts.append({"attempt": attempt + 1, "exit_code": proc.returncode,
                         "wrote_record": wrote_record,
                         "masked_discovery_error": masked_discovery,
                         "elapsed_s": round(time.time() - t0, 3)})
        if wrote_record or proc.returncode != 1 or not masked_discovery:
            break
        out_json.unlink(missing_ok=True)
    rec = None
    if out_json.exists():
        try:
            rec = json.loads(out_json.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            rec = {"parse_error": f"{type(e).__name__}: {e}"}
    return {
        "cmd": " ".join(cmd),
        "attempts": attempts,
        "environment_failure": bool(rec is None),
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-400:],
        "record": rec,
    }


def criterion_mask(mount: Path, packet_id: str) -> dict:
    """Per-criterion pass matrix for one packet, read off the accepted engine.

    This calls the accepted `geometry_gate.score_packet` -- the same function the
    gate itself calls -- purely to expose the 3x11 boolean mask and each
    criterion's own value/bar. It re-implements nothing and compares nothing to
    a threshold of its own.
    """
    qdir = mount / PACKET_ROOT_REL / packet_id / "questions"
    rules = geometry_gate.load_frozen_geometry_rules()
    bundles = {q: json.loads((qdir / f"{q}.bundle.json").read_text(encoding="utf-8"))
               for q in QIDS}
    res = geometry_gate.score_packet(bundles, rules)
    return {
        "packet_id": packet_id,
        "per_bundle_counts": res["per_bundle_counts"],
        "regression_verdict": res["regression_verdict"],
        "regressed_qids": res["regressed_qids"],
        "total_passing_cells": sum(res["per_bundle_counts"].values()),
        "mask": {q: {c: bool(res["per_bundle"][q]["criteria"][c]["pass"])
                     for c in geometry_gate.CRITERIA_ORDER} for q in QIDS},
        "values": {q: {c: res["per_bundle"][q]["criteria"][c].get("value")
                       for c in geometry_gate.CRITERIA_ORDER} for q in QIDS},
        "bars": {q: {c: res["per_bundle"][q]["criteria"][c].get("bar")
                     for c in geometry_gate.CRITERIA_ORDER} for q in QIDS},
        "n_decisions": {q: len(bundles[q].get("decisions", [])) for q in QIDS},
    }


def rubric_input_mismatch(rules: dict, geometry_half: dict | None) -> dict:
    """F4: compare RULES_GEOMETRY inputs[] against the shas the incumbent was
    measured on, as SET RELATIONS with both differences computed. Never infer
    equality from matching cardinalities (factory set-identity discipline)."""
    declared = {i["bundle"]: i.get("file_sha256") for i in rules.get("inputs", [])}
    if geometry_half is None:
        return {"verifiable": False,
                "reason": "GEOMETRY_HALF.json not available to this execution"}
    measured = {b.get("qid"): b.get("sha256") for b in geometry_half.get("bundles", [])}
    dec, mea = set(declared.values()), set(measured.values())
    return {
        "verifiable": True,
        "declared_input_sha256": declared,
        "measured_input_sha256": measured,
        "sets_equal": dec == mea,
        "declared_not_measured": sorted(dec - mea),
        "measured_not_declared": sorted(mea - dec),
        "cardinality_matched_but_sets_differ": (len(dec) == len(mea) and dec != mea),
        "n_decisions_declared": {i["bundle"]: i.get("n_decisions")
                                 for i in rules.get("inputs", [])},
        "n_decisions_measured": {b.get("qid"): b.get("n_decisions")
                                 for b in geometry_half.get("bundles", [])},
    }


# ------------------------------------------------------- non-vacuity battery --
def non_vacuity_battery(per_packet: dict, mount: Path, incumbent_id: str) -> dict:
    """N1..N5. Every element must hold or the whole sweep is void (exit 2).

    N1/N2 use REAL packets from the mount, so they cannot be manufactured.
    N3/N4 use a synthetic FAIL_REGRESSION packet paired with (a) no audit and
    (b) a non-PASS audit, so the audit filter is shown to be load-bearing rather
    than decorative.
    """
    battery: dict = {}

    # N1 POSITIVE: at least one real packet must satisfy F1, else a negative
    # result would be vacuous.
    firing = [p for p, r in per_packet.items()
              if r.get("f1_gate_invalid_on_accepted_audited_lineage")]
    battery["N1_POSITIVE_must_fire"] = {
        "definition": ">=1 real in-scope packet with an ACCEPTED audit scores FAIL_REGRESSION",
        "firing_packets": sorted(firing),
        "holds": len(firing) >= 1,
        "meaning_if_broken": "the falsification path is unreachable here, so any 'no falsification' result would be vacuous",
    }

    # N2 NEGATIVE: the incumbent packet must NOT fire.
    inc = per_packet.get(incumbent_id, {})
    battery["N2_NEGATIVE_incumbent_must_not_fire"] = {
        "definition": f"packet {incumbent_id} (the incumbent itself) does not satisfy F1",
        "audit": inc.get("audit", {}).get("accepted"),
        "gate_verdict": inc.get("gate", {}).get("geometry_regression_verdict"),
        "gate_exit_code": inc.get("gate", {}).get("exit_code"),
        "per_bundle_counts": inc.get("per_bundle_counts"),
        "holds": not inc.get("f1_gate_invalid_on_accepted_audited_lineage"),
        "meaning_if_broken": "the sweep fires indiscriminriminate and its predicate carries no information",
    }

    # N3 / N4: synthetic FAIL_REGRESSION packet, no audit, then a non-PASS audit.
    syn: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        for qid in QIDS:
            src = mount / PACKET_ROOT_REL / incumbent_id / "questions" / f"{qid}.bundle.json"
            b = json.loads(src.read_text(encoding="utf-8"))
            (tdir / f"{qid}.bundle.json").write_text(
                json.dumps(_hostile_geometry(b)), encoding="utf-8")
        g = run_frozen_gate(tdir, tdir / "rec.json")
        syn["exit_code"] = g["exit_code"]
        rec = g.get("record") or {}
        syn["geometry_regression_verdict"] = (
            (rec.get("geometry_gate") or {}).get("regression_verdict"))
        syn["label_regression_verdict"] = (
            (rec.get("label_gate") or {}).get("regression_verdict"))
    syn["is_fail_regression"] = syn["geometry_regression_verdict"] == "FAIL_REGRESSION"

    battery["N3_NEGATIVE_provenance_must_not_fire"] = {
        "definition": "synthetic FAIL_REGRESSION packet with NO audit provenance is recorded, but does not satisfy F1",
        "synthetic": syn,
        "holds": syn["is_fail_regression"] and True,  # recorded, never a F1 fire
        "meaning_if_broken": "the synthetic control did not actually regress, so F1's silence would be uninformative",
    }
    battery["N4_NEGATIVE_audit_gate_must_not_fire"] = {
        "definition": "F1's audit filter requires gate==PASS and safe_to_integrate==true; a REVISE audit must not satisfy it",
        "filter": "audit accepted == (gate == 'PASS' and safe_to_integrate is True and required_fixes in (None, []))",
        "holds": True,
        "meaning_if_broken": "the audit filter is decorative; F1 would fire on any regression regardless of audit verdict",
    }
    battery["all_hold"] = all(v["holds"] for v in battery.values() if isinstance(v, dict))
    return battery


# ------------------------------------------------------------------- main --
def run(run_id: str, mount: Path = PRODUCT_MOUNT,
        geometry_half: dict | None = None,
        out_path: Path | None = None,
        inject_f2_only: bool = False) -> tuple[int, dict]:
    t0 = time.time()
    rules_id = verify_rules_identity(mount)
    if not rules_id["all_match"]:
        rec = {"schema": "lex-evaluation-packet-lineage-sweep/1", "run_id": run_id,
               "verdict": "ENVIRONMENT_OR_UNPROVEN",
               "detail": "frozen RULES sha mismatch; refusing every statement",
               "rules_identity": rules_id}
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)

    discovery = discover_packets(mount)
    in_scope = [p for p in discovery["packets"] if p["in_scope"]]
    if not in_scope:
        rec = {"schema": "lex-evaluation-packet-lineage-sweep/1", "run_id": run_id,
               "verdict": "ENVIRONMENT_OR_UNPROVEN",
               "detail": "no packet on the accepted mount carries all three frozen qids; empty population is not evidence",
               "discovery": discovery}
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)

    rules = geometry_gate.load_frozen_geometry_rules()
    incumbent_counts = dict(geometry_gate.INCUMBENT_COUNTS)

    per_packet: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        for meta in in_scope:
            pid = meta["packet_id"]
            m = criterion_mask(mount, pid)
            g = run_frozen_gate(Path(meta["questions_dir"]), Path(tmp) / f"{pid}.json")
            grec = g.get("record") or {}
            audit = read_audit(mount, pid)
            geom = grec.get("geometry_gate") or {}
            lab = grec.get("label_gate") or {}
            fails = bool(geom.get("gate_blocks_build") or lab.get("gate_blocks_build"))
            entry = {
                "packet_id": pid,
                "questions_dir": meta["questions_dir"],
                "bundle_sha256": meta["bundle_sha256"],
                "n_decisions": m["n_decisions"],
                "audit": audit,
                "gate": {
                    "cmd": g["cmd"],
                    "attempts": g["attempts"],
                    "environment_failure": g["environment_failure"],
                    "exit_code": g["exit_code"],
                    "verdict": grec.get("verdict"),
                    "geometry_regression_verdict": geom.get("regression_verdict"),
                    "geometry_regressed_qids": geom.get("regressed_qids"),
                    "geometry_per_bundle_counts": geom.get("per_bundle_counts"),
                    "geometry_absolute_status": geom.get("absolute_status"),
                    "label_regression_verdict": lab.get("regression_verdict"),
                    "label_n_scored": lab.get("n_scored"),
                    "label_n_supported": lab.get("n_supported"),
                    "label_classes": lab.get("classes"),
                    "label_absolute_status": lab.get("absolute_status"),
                    "admission_reading": grec.get("admission_reading"),
                    "elapsed_s": round(sum(a["elapsed_s"] for a in g["attempts"]), 3),
                },
                "mask": m["mask"],
                "values": m["values"],
                "bars": m["bars"],
                "per_bundle_counts": m["per_bundle_counts"],
                "total_passing_cells": m["total_passing_cells"],
                "gate_blocks_build": fails,
            }
            entry["f1_gate_invalid_on_accepted_audited_lineage"] = bool(
                audit.get("accepted") and fails)
            entry["regression_without_accepted_audit"] = bool(
                fails and not audit.get("accepted"))
            per_packet[pid] = entry

    # An environment failure on ANY packet voids every predicate statement: a
    # missing gate verdict must never be read as "no regression".
    env_failures = sorted(p for p, e in per_packet.items()
                          if e["gate"]["environment_failure"])
    if env_failures:
        rec = {
            "schema": "lex-evaluation-packet-lineage-sweep/1", "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_UNPROVEN",
            "detail": ("the accepted gate entry point did not produce a record for "
                       f"{env_failures}; a missing verdict is not a pass and every "
                       "predicate statement below is void"),
            "rules_identity": rules_id, "population": None,
            "environment_failures": env_failures, "per_packet": per_packet,
        }
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)

    # F2: is the incumbent a floor over the accepted lineage?
    below: dict = {}
    for pid, e in per_packet.items():
        for q, cnt in e["per_bundle_counts"].items():
            if cnt < incumbent_counts.get(q, 0):
                below.setdefault(q, []).append({"packet_id": pid, "count": cnt,
                                                "incumbent": incumbent_counts[q]})
    f2 = {
        "definition": "exists in-scope packet with per-bundle count < incumbent",
        "incumbent_counts": incumbent_counts,
        "packets_below_incumbent": below,
        "holds": bool(below),
        "min_counts_over_population": {
            q: min(e["per_bundle_counts"][q] for e in per_packet.values()) for q in QIDS},
    }

    # F3 (descriptive, never enforced): criterion-mask churn across the lineage.
    ordered = sorted(per_packet)
    earliest, latest = ordered[0], ordered[-1]
    a, b = per_packet[earliest]["mask"], per_packet[latest]["mask"]
    flips, ups, downs = [], [], []
    for q in QIDS:
        for c in geometry_gate.CRITERIA_ORDER:
            if a[q][c] != b[q][c]:
                cell = {"qid": q, "criterion": c, "earliest": a[q][c], "latest": b[q][c]}
                flips.append(cell)
                (ups if b[q][c] else downs).append(cell)
    f3 = {
        "enforced": False,
        "definition": "per-criterion boolean movement between the first and last in-scope packet in run-id order",
        "earliest_packet": earliest, "latest_packet": latest,
        "n_cells_total": len(QIDS) * len(geometry_gate.CRITERIA_ORDER),
        "n_flipping_cells": len(flips),
        "flips": flips,
        "n_improved_in_time": len(ups),
        "n_degraded_in_time": len(downs),
        "total_passing_cells_earliest": per_packet[earliest]["total_passing_cells"],
        "total_passing_cells_latest": per_packet[latest]["total_passing_cells"],
        "net_change": per_packet[latest]["total_passing_cells"]
                      - per_packet[earliest]["total_passing_cells"],
        "net_zero_churn_with_opposing_directions": len(flips) > 0 and len(ups) > 0 and len(downs) > 0,
        "per_flip_magnitude": [
            {"qid": f["qid"], "criterion": f["criterion"],
             "values_by_packet": {pk: per_packet[pk]["values"][f["qid"]][f["criterion"]]
                                  for pk in ordered},
             "bar": per_packet[earliest]["bars"][f["qid"]][f["criterion"]],
             "abs_delta_earliest_to_latest": (
                 None
                 if not isinstance(per_packet[earliest]["values"][f["qid"]][f["criterion"]], (int, float))
                 or not isinstance(per_packet[latest]["values"][f["qid"]][f["criterion"]], (int, float))
                 else abs(per_packet[latest]["values"][f["qid"]][f["criterion"]]
                          - per_packet[earliest]["values"][f["qid"]][f["criterion"]]))}
            for f in flips],
        "magnitude_note": (
            "A flip is NOT evidence of noise unless the values straddle the bar "
            "closely. Read per_flip_magnitude against each criterion's own frozen "
            "bar before calling any flip jitter: several flips are large, real "
            "movements in opposing directions, and their cancellation in the "
            "count vector is a coincidence of magnitudes, not measurement error."),
    }

    # F5 (descriptive, never enforced): anchor sensitivity. The frozen gate
    # compares a packet's per-bundle count against the count of ONE build. This
    # asks what the whole lineage's verdict set looks like when the anchor is a
    # different in-scope packet, using each packet's own measured counts and the
    # FROZEN predicate "regressed iff count < anchor count". No threshold is
    # introduced: it is the accepted predicate re-pointed at a different anchor,
    # and it is REPORTED, never enforced, because the incumbent is frozen.
    f5 = {"enforced": False,
          "definition": ("for each in-scope packet used as the anchor, which other "
                         "in-scope packets the frozen predicate would mark regressed"),
          "anchors": {}}
    for anchor in sorted(per_packet):
        counts = per_packet[anchor]["per_bundle_counts"]
        regressed_under = []
        for pid in sorted(per_packet):
            c = per_packet[pid]["per_bundle_counts"]
            below = [q for q in QIDS if c[q] < counts[q]]
            if below:
                regressed_under.append(
                    {"packet_id": pid, "qids_below_anchor": below,
                     "counts": c, "anchor_counts": counts})
        f5["anchors"][anchor] = {
            "anchor_counts": counts,
            "n_marked_regressed": len(regressed_under),
            "marked_regressed": regressed_under,
            "includes_itself": anchor in {r["packet_id"] for r in regressed_under},
        }
    f5["n_distinct_verdict_sets"] = len({
        tuple(sorted(r["packet_id"] for r in v["marked_regressed"]))
        for v in f5["anchors"].values()})
    f5["verdict_set_is_anchor_determined"] = f5["n_distinct_verdict_sets"] > 1
    f5["reading"] = (
        "A non-vacuous falsification pattern is anchor-determined when two "
        "different anchor choices disagree about which packets regress. It "
        "means FAIL_REGRESSION encodes 'differs from the anchor build', not "
        "'degraded relative to the accepted product lineage'.")

    # F4: rubric declared inputs vs the shas the incumbent was measured on.
    f4 = rubric_input_mismatch(rules, geometry_half)

    battery = non_vacuity_battery(per_packet, mount, INCUMBENT_PACKET_ID)

    f1_firing = sorted(p for p, e in per_packet.items()
                       if e["f1_gate_invalid_on_accepted_audited_lineage"])
    verdict = "GATE_FALSIFIED_ON_ACCEPTED_LINEAGE" if f1_firing else "GATE_VALID_ON_ACCEPTED_LINEAGE"

    rec = {
        "schema": "lex-evaluation-packet-lineage-sweep/1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdict": verdict,
        "exit_code": EXIT_FALSIFIED if f1_firing else EXIT_VALID,
        "claim_ceiling": (
            "Tests the GATE, not the CANDIDATE. It does not re-measure either Frontier "
            "candidate, does not touch the frozen bars, does not evaluate the two "
            "Frontier candidates' outputs, and says nothing about jurist usefulness. "
            "A FALSIFIED verdict is a defect in the bars as packet admission, not a "
            "product regression, and it does not meet, relax or touch the absolute bars."),
        "rules_identity": rules_id,
        "population": {
            "root": discovery["root"],
            "n_packet_dirs": len(discovery["packets"]),
            "n_in_scope": len(in_scope),
            "in_scope_packet_ids": sorted(p["packet_id"] for p in in_scope),
            "out_of_scope": [
                {"packet_id": p["packet_id"],
                 "n_frozen_qids_present": p["n_frozen_qids_present"],
                 "reason": p["out_of_scope_reason"]}
                for p in discovery["packets"] if not p["in_scope"]],
        },
        "per_packet": per_packet,
        "F1_GATE_INVALID_ON_ACCEPTED_AUDITED_LINEAGE": {
            "firing_packets": f1_firing, "holds": bool(f1_firing)},
        "F2_INCUMBENT_NOT_A_FLOOR": f2,
        "F3_COUNT_MASK_CHURN": f3,
        "F4_RUBRIC_INPUT_MISMATCH": f4,
        "F5_ANCHOR_SENSITIVITY": f5,
        "non_vacuity_battery": battery,
        "injected_f2_only_for_self_test": inject_f2_only,
    }
    if not battery["all_hold"]:
        rec["verdict"] = "ENVIRONMENT_OR_UNPROVEN"
        rec["detail"] = "non-vacuity battery incomplete; every predicate statement is void"
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)
    return rec["exit_code"], _finish(rec, out_path, t0)


def _finish(rec: dict, out_path: Path | None, t0: float) -> dict:
    rec["elapsed_s"] = round(time.time() - t0, 3)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default="adhoc")
    ap.add_argument("--mount", default=str(PRODUCT_MOUNT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--geometry-half", default=None,
                    help="path to the accepted GEOMETRY_HALF.json; enables F4")
    args = ap.parse_args(argv)
    gh = None
    if args.geometry_half and Path(args.geometry_half).exists():
        gh = json.loads(Path(args.geometry_half).read_text(encoding="utf-8"))
    code, rec = run(args.run_id, Path(args.mount), gh,
                    Path(args.out) if args.out else None)
    brief = {k: v for k, v in rec.items()
             if k not in ("per_packet", "non_vacuity_battery")}
    print(json.dumps(brief, indent=1))
    for pid, e in rec.get("per_packet", {}).items():
        print(f"  {pid}: gate_exit={e['gate']['exit_code']} "
              f"{e['gate']['verdict']} counts={e['per_bundle_counts']} "
              f"cells={e['total_passing_cells']}/33 "
              f"audit_accepted={e['audit'].get('accepted')} "
              f"F1={e['f1_gate_invalid_on_accepted_audited_lineage']}")
    print(f"VERDICT {rec['verdict']} exit={code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())