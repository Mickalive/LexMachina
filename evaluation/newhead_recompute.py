"""Product-head re-verification trigger + executor for direction items (1)-(7).

WHAT THIS IS
------------
Factory direction v52, Core Evaluation lane question, deliverables (1)-(7):

(1) ``python -m evaluation.packet_admission_conformance`` may be re-run **only**
    when Product ships a NEW served packet, defined by the direction as "any sha
    change of packet.json / state/product.json"; a re-run over the byte-identical
    population "is the rc-67 zero-delta pathology and must not be issued".
(4) recompute the frozen reality benchmark **per-artifact** on each new Product
    head that claims a recall/label/geometry change.
(5) keep the ``structural::counter_classifications_supported`` failures tracked
    as the only ``overall_pass`` components Product can still move.

Before this module the "only when a new packet" condition was PROSE.  Nothing in
the lane executed it, so nothing could observe that the condition was false, and
a zero-delta re-run was one careless command away.  This module makes the
condition executable and makes the direction's own definition the only definition
used:

* :func:`packet_population`  - the sha manifest of the served-packet claim
  population (every ``gate_packet/<id>/packet.json`` plus every byte under
  ``gate_packet/<id>/``) together with ``state/product.json``.
* :func:`rebuild_trigger`   - the decision ``ADJUDICATE_REQUIRED`` vs
  ``NO_NEW_PACKET`` by **set relation** against a pinned baseline manifest.
  Matching cardinalities are never treated as identity (factory-direction
  set-identity rule): the intersection and both differences are computed.
* :func:`recompute_claim_population` - the frozen reality benchmark re-run
  (deliverable 4) plus the deliverable-5 failure set.

ZERO THRESHOLDS, ZERO NEW BARS.  Every number this module emits is a count of
bytes, files or gate outcomes produced by the FROZEN instruments
(``evaluation.reality_gate`` spec ``ff57f556…``, gate contract ``06781743…``)
or a set relation between sha256 digests.  No threshold, rubric or bar is
introduced, re-derived or tuned here, and nothing accepted is overwritten.

This module never imports Product code and never touches the network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.reality_gate import frozen as reality_frozen  # noqa: E402

SCHEMA = "lex-evaluation-newhead-recompute/1"
TRIGGER_SCHEMA = "lex-evaluation-rebuild-trigger/1"

#: The gate whose failures direction item (5) names as the only ``overall_pass``
#: components Product can still move.  Named here so the record and the tests
#: share one literal; it is a GATE NAME, not a threshold.
MOVABLE_GATE = "structural::counter_classifications_supported"

DEFAULT_PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")


class FrozenRunnerFailure(RuntimeError):
    """The frozen runner emitted no record.  Never a measurement."""


# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def packet_population(product_mount: Path) -> dict:
    """sha manifest of the served-packet claim population.

    The population is every byte under ``results/product/gate_packet/`` plus
    ``state/product.json``.  This is deliberately the whole served-packet tree
    and not only ``packet.json``: a rebuild that changes a bundle without
    renaming the packet directory is still a new packet under the direction's
    intent, and only a byte manifest can tell the two apart.
    """
    root = product_mount.resolve()
    manifest: dict[str, str] = {}
    gp = root / "results" / "product" / "gate_packet"
    n_dirs = 0
    if gp.is_dir():
        for packet_dir in sorted(p for p in gp.iterdir() if p.is_dir()):
            n_dirs += 1
            for path in sorted(packet_dir.rglob("*")):
                if path.is_file():
                    manifest[_rel(root, path)] = sha256_file(path)
    state = root / "state" / "product.json"
    if state.is_file():
        manifest[_rel(root, state)] = sha256_file(state)
    return {
        "root": str(root),
        "packet_dirs": n_dirs,
        "state_product_json_present": state.is_file(),
        "manifest": manifest,
        "n_files": len(manifest),
    }


def set_relation(current: dict[str, str], baseline: dict[str, str]) -> dict:
    """Intersection and BOTH differences.  Never a cardinality match.

    factory-direction requirement 11 (set-identity claims): before writing
    "identical" or "all of the" between two counted sets, compute the
    intersection and both differences.  A matching sub-count inside a larger
    count proves containment at best, never identity.
    """
    c, b = set(current), set(baseline)
    common = c & b
    changed = sorted(k for k in common if current[k] != baseline[k])
    return {
        "n_current": len(c),
        "n_baseline": len(b),
        "n_common": len(common),
        "n_byte_identical": len(common) - len(changed),
        "n_changed": len(changed),
        "added": sorted(c - b),
        "removed": sorted(b - c),
        "changed": changed,
        "identical_as_a_set": (
            len(changed) == 0 and not (c - b) and not (b - c)),
    }


def rebuild_trigger(product_mount: Path, baseline_manifest: dict[str, str],
                    baseline_ref: str) -> dict:
    """Direction item (1)'s condition, executed.

    ``ADJUDICATE_REQUIRED`` iff the served-packet claim population differs from
    the pinned baseline as a SET.  ``NO_NEW_PACKET`` otherwise, which forbids
    re-issuing ``packet_admission_conformance`` and the two bar sweeps over the
    byte-identical population (the rc-67 zero-delta pathology).

    An EMPTY population against an EMPTY baseline is ``NULL_POPULATION``, never
    ``NO_NEW_PACKET``: a parity claim over nothing is not a pass (the same
    lesson as the empty-population guard added to the label-lineage sweep in
    cycle 39020603510).
    """
    pop = packet_population(product_mount)
    rel = set_relation(pop["manifest"], baseline_manifest)
    if not pop["manifest"]:
        verdict = "NULL_POPULATION"
    elif rel["identical_as_a_set"]:
        verdict = "NO_NEW_PACKET"
    else:
        verdict = "ADJUDICATE_REQUIRED"
    return {
        "schema": TRIGGER_SCHEMA,
        "verdict": verdict,
        "re_run_forbidden": verdict != "ADJUDICATE_REQUIRED",
        "reason": {
            "NULL_POPULATION": "served-packet claim population is empty; parity "
                               "over an empty set is not evidence of no change",
            "NO_NEW_PACKET": "served-packet claim population is byte-identical to "
                             "the pinned baseline (set relation: intersection == "
                             "both operands, both differences empty); issuing "
                             "packet_admission_conformance or the two bar sweeps "
                             "over it is the rc-67 zero-delta pathology",
            "ADJUDICATE_REQUIRED": "served-packet claim population differs from the "
                                   "pinned baseline; direction items (1)-(3) fire",
        }[verdict],
        "baseline_ref": baseline_ref,
        "set_relation": rel,
        "population": {k: v for k, v in pop.items() if k != "manifest"},
        "product_head": product_mount.resolve().name,
    }


# --------------------------------------------------------------------------- #
# deliverable (4): per-artifact recompute on the new head
# --------------------------------------------------------------------------- #
def gate_failures(record: dict, gate: str) -> list[str]:
    """Artifacts whose recorded ``gate`` outcome is a FAILURE.

    An artifact that never executed the gate (``passed is None``, i.e.
    ``not_measurable``) is NOT a failure and is NOT counted as one; it is
    reported separately so a population that merely stops measuring the gate
    cannot masquerade as a pass.
    """
    out = []
    for art in record.get("artifacts", []):
        for g in art.get("gates", []):
            if g.get("gate") == gate and g.get("passed") is False:
                out.append(str(art.get("artifact")))
    return sorted(out)


def gate_not_measurable(record: dict, gate: str) -> list[str]:
    out = []
    for art in record.get("artifacts", []):
        for g in art.get("gates", []):
            if g.get("gate") == gate and g.get("passed") is None:
                out.append(str(art.get("artifact")))
    return sorted(out)


def gate_executions(record: dict, gate: str) -> list[str]:
    out = []
    for art in record.get("artifacts", []):
        for g in art.get("gates", []):
            if g.get("gate") == gate and g.get("passed") is not None:
                out.append(str(art.get("artifact")))
    return sorted(out)


def verdict_map(record: dict) -> dict:
    """per-artifact verdict map, used for the drift comparison."""
    out = {}
    for art in record.get("artifacts", []):
        if art.get("artifact_passed") is None:
            continue
        out[str(art.get("artifact"))] = bool(art["artifact_passed"])
    return out


def run_frozen_benchmark(evidence_dir: Path, bundle_dirs: list[Path],
                         out_path: Path) -> dict:
    """Invoke the ACCEPTED frozen runner as a subprocess.

    The frozen instrument is never re-implemented and never re-derived here: the
    same entry point (``python -m evaluation.reality_gate.run_benchmark``) that
    produced every incumbent record is executed with the frozen spec on disk,
    which re-verifies its own digest before scoring.
    """
    cmd = [sys.executable, "-m", "evaluation.reality_gate.run_benchmark",
           "--evidence-dir", str(evidence_dir)]
    for d in bundle_dirs:
        cmd += ["--extra-bundle-dir", str(d)]
    cmd += ["--out", str(out_path)]
    proc = subprocess.run(cmd, cwd=str(_LANE_ROOT), capture_output=True, text=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # The frozen runner prints a HUMAN-READABLE summary on stdout and writes the
    # JSON record to --out.  Reading stdout as JSON is wrong and was caught in
    # cycle 39027041693 before it reached a measurement.
    summary_path = out_path.with_suffix(".summary.txt")
    summary_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path = out_path.with_suffix(".stderr.txt")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    try:
        rec = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # The frozen runner exits 2 (environment/empty input) and 3 (integrity)
        # WITHOUT emitting a record.  A caller must never turn that into a
        # measurement; it is an environment failure, preserved verbatim.
        raise FrozenRunnerFailure(
            f"frozen runner produced no record (exit {proc.returncode}); "
            f"stderr tail: {proc.stderr[-2000:]!r}")
    return {"argv": cmd, "exit_code": proc.returncode, "record_path": str(out_path),
            "summary_path": str(summary_path), "stderr_path": str(stderr_path),
            "frozen_sha256": rec.get("frozen_sha256"),
            "overall_pass": rec.get("overall_pass"), "stderr": proc.stderr[-4000:]}


def recompute(product_mount: Path, run_id: str, baseline_record: Path | None,
              invocations: list[dict], out_dir: Path) -> dict:
    """Run every frozen invocation, then compute the deliverable-(5) set record.

    ``invocations`` is a list of ``{"name":..., "evidence_dir":..., "bundle_dirs":[...]}``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    root = product_mount.resolve()
    results = {}
    for inv in invocations:
        record = out_dir / f"{run_id}_{inv['name']}.json"
        results[inv["name"]] = run_frozen_benchmark(
            Path(inv["evidence_dir"]), [Path(d) for d in inv.get("bundle_dirs", [])],
            record)
        results[inv["name"]]["artifact_count"] = len(
            json.loads(record.read_text(encoding="utf-8")).get("artifacts", []))

    composite: dict = {}
    for name, res in results.items():
        rec = json.loads(Path(res["record_path"]).read_text(encoding="utf-8"))
        composite[name] = {
            "record_path": res["record_path"],
            "record_sha256": sha256_file(Path(res["record_path"])),
            "exit_code": res["exit_code"],
            "overall_pass": res["overall_pass"],
            "frozen_sha256": res["frozen_sha256"],
            "n_artifacts": rec.get("n_artifacts"),
            "n_evaluated": rec.get("n_evaluated"),
            "n_excluded_no_verdict": rec.get("n_excluded_no_verdict"),
            "n_full_match_evaluated": rec.get("n_full_match_evaluated"),
            "n_question_independent_evaluated": rec.get("n_question_independent_evaluated"),
            MOVABLE_GATE: {
                "failures": gate_failures(rec, MOVABLE_GATE),
                "executions": gate_executions(rec, MOVABLE_GATE),
                "not_measurable": gate_not_measurable(rec, MOVABLE_GATE),
            },
        }

    drift = None
    if baseline_record is not None and Path(baseline_record).is_file():
        base = json.loads(Path(baseline_record).read_text(encoding="utf-8"))
        base_map = verdict_map(base)
        for name in composite:
            rec = json.loads(Path(composite[name]["record_path"]).read_text(encoding="utf-8"))
            cur = verdict_map(rec)
            common = set(base_map) & set(cur)
            changed = sorted(k for k in common if base_map[k] != cur[k])
            drift[name] = {
                "baseline_record": str(baseline_record),
                "n_baseline_evaluated": len(base_map),
                "n_common": len(common),
                "n_common_byte_identical_verdict": len(common) - len(changed),
                "n_changed_verdict": len(changed),
                "changed": changed,
                "added": sorted(set(cur) - set(base_map)),
                "dropped": sorted(set(base_map) - set(cur)),
            }

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "product_mount": str(root),
        "frozen_benchmark_sha256": reality_frozen.FROZEN_SHA256,
        "frozen_benchmark_reverified_on_disk": True,
        "invocations": composite,
        "runner_stderr": {n: r.get("stderr") for n, r in results.items()},
        "verdict_drift_vs_incumbent": drift,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product-mount", default=str(DEFAULT_PRODUCT_MOUNT))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--baseline-manifest", default=None,
                    help="pinned baseline manifest JSON (trigger mode)")
    ap.add_argument("--baseline-record", default=None,
                    help="incumbent frozen reality record (drift comparison)")
    ap.add_argument("--invocation", action="append", default=[],
                    help="name=evidence_dir[;bundle_dir;bundle_dir...] (repeatable). "
                         "NOTE: the directory list separator is ';' - '|' was tried "
                         "first and collided with the path list in an attempted run "
                         "of 39027041693, producing a 'evidence directory does not "
                         "exist' error before any artifact was scored.")
    ap.add_argument("--mode", choices=("trigger", "recompute"), default="recompute")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mount = Path(args.product_mount)

    try:
        reality_frozen.load_frozen()
    except Exception as exc:  # pragma: no cover - integrity guard
        print(f"::error::frozen benchmark integrity failure: {exc}", file=sys.stderr)
        return 2

    try:
        if args.mode == "trigger":
            if not args.baseline_manifest:
                print("::error::--mode trigger requires --baseline-manifest", file=sys.stderr)
                return 2
            base = json.loads(Path(args.baseline_manifest).read_text(encoding="utf-8"))
            payload = rebuild_trigger(mount, base.get("manifest", base),
                                      str(args.baseline_manifest))
        else:
            invocations = []
            for spec in args.invocation:
                if "=" not in spec:
                    print(f"::error::bad --invocation {spec!r}", file=sys.stderr)
                    return 2
                name, _, dirs = spec.partition("=")
                paths = [p for p in dirs.split(";") if p]
                if not name or not paths:
                    print(f"::error::bad --invocation {spec!r}", file=sys.stderr)
                    return 2
                invocations.append({
                    "name": name,
                    "evidence_dir": paths[0],
                    "bundle_dirs": paths[1:],
                })
            if not invocations:
                print("::error::at least one --invocation is required", file=sys.stderr)
                return 2
            payload = recompute(mount, args.run_id,
                                Path(args.baseline_record) if args.baseline_record else None,
                                invocations, out_dir)
    except FrozenRunnerFailure as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    out = out_dir / f"{args.run_id}_{args.mode}.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("invocations", "verdict_drift_vs_incumbent")},
                     indent=2, sort_keys=True)[:2000])
    print(f":: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())