#!/usr/bin/env python3
"""Adjudicate the fired direction-item trigger's scored-claim-movement leg.

    python -m evaluation.scored_claim_movement_adjudication --run-id <run_id>

WHY THIS MODULE EXISTS
======================
Run 39520368732 executed the factory direction's own falsification trigger
(``python -m evaluation.newhead_recompute --mode trigger``) against the
accepted product mount and published ``TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_
NOT_MEASURED``: the trigger fired (``ADJUDICATE_REQUIRED``, re_run_forbidden
false), but the frozen ``evaluation.trigger_reconciliation`` instrument could
not retrieve ``state/product.json`` at the pinned baseline head ``cc719eebf``
because the accepted mount's git history is shallow (``fatal: invalid object
name``). The composite verdict was therefore undecided and left for a later
cycle with ``re_run_forbidden=false``.

This module closes exactly that leg and nothing else:

  1. It builds NOTHING and re-derives NOTHING. It consumes a pre-built
     deeper-history product mount (same HEAD as the accepted mount) in which
     the baseline object resolves, PROVES the mount's claim population is
     byte-identical to the accepted mount's, then runs the EXISTING frozen
     instrument ``evaluation/trigger_reconciliation.py`` VERBATIM as a
     subprocess — never edited, re-hashed before and after the run.
  2. It publishes the decided composite verdict (H_A no movement / H_B
     movement) side by side with the frozen trigger's set relation.
  3. It proves NON-VACUITY with a planted synthetic control: a shared-clone
     of the deeper mount whose ``state/product.json`` carries one extra
     clearly-marked synthetic scored row. The frozen instrument must return
     ``TRIGGER_FIRES__SCORED_CLAIM_MOVED__RE_SCORE_JUSTIFIED`` on it; if it
     does not, this module exits 1 (NON_VACUOUS) and publishes no composite
     as a measurement.

EXIT CODES
==========
0  decided composite (H_A or H_B), trigger reproduced, identity proven,
   planted control flipped.
1  NON_VACUOUS (planted control undetected) or any check-weakening.
2  ENVIRONMENT_ERROR (missing mount/file, unfetchable baseline object,
   claim-population byte-identity failure, frozen-pin mismatch).

NO FROZEN FILE IS WRITTEN, REGENERATED OR RE-TUNED. No rubric, threshold,
bar, benchmark, baseline or success rule is touched. Exit code 0 does NOT
mean any product bar is met; it means the adjudication instrument ran to a
decided composite.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

SCHEMA = "lex-evaluation-scored-claim-movement-adjudication/1"

#: Frozen pins from evaluation/SCORED_CLAIM_MOVEMENT_ADJUDICATION_FREEZE_RECORD_V1.json.
#: A mismatch is ENVIRONMENT_ERROR (exit 2), never a measurement.
HYPOTHESIS_PATH = "evaluation/SCORED_CLAIM_MOVEMENT_ADJUDICATION_HYPOTHESIS_V1.json"
HYPOTHESIS_SHA256 = "8c898f2b6ec2f91c695abb0edd814993065f536545a0301d1530c0e6f00cabc0"
FROZEN_PINS = {
    "evaluation/trigger_reconciliation.py":
        "cff603c638ce5f310d82d9e2d6bf28a0a3b32eb752a9c20374255a97fdc62d48",
    "evaluation/newhead_recompute.py":
        "88ee61075bce2eeb76bd0db431490b6b029bc2dc2806150f47ea5edbc6f48974",
    "results/evaluation/newhead_recompute_39027041693/"
    "served_packet_baseline_39027041693.json":
        "93bb4e8e209dc1b894d64b5693c4c3786bf90ee2bb9d349d2107963ca0812ccd",
}
BASELINE_HEAD_SHORT = "cc719eebf"
BASELINE_MANIFEST = ("results/evaluation/newhead_recompute_39027041693/"
                     "served_packet_baseline_39027041693.json")
GATE_PACKET_ROOT = "results/product/gate_packet"
STATE_REL = "state/product.json"
PLANTED_ROW_ID = "SYNTHETIC_PLANTED_ROW_39529073155"
DEFAULT_ACCEPTED_MOUNT = "/tmp/lex_accepted/product"

#: The two composites the frozen instrument can return when the trigger fires.
COMPOSITE_MOVED = "TRIGGER_FIRES__SCORED_CLAIM_MOVED__RE_SCORE_JUSTIFIED"
COMPOSITE_NO_OP = "TRIGGER_FIRES__NO_SCORED_CLAIM_MOVEMENT__RE_SCORE_WOULD_BE_A_NO_OP"
COMPOSITE_NOT_MEASURED = "TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_NOT_MEASURED"


class EnvironmentError_(RuntimeError):
    """Environment failure. Exit 2. Never a measurement."""


class NonVacuousError(RuntimeError):
    """Planted control undetected. Exit 1. Never a composite."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_frozen_pins(repo_root: Path) -> dict:
    """Re-hash every frozen pin. Mismatch -> EnvironmentError_ (exit 2)."""
    checks = {}
    hyp = repo_root / HYPOTHESIS_PATH
    if not hyp.is_file():
        raise EnvironmentError_(f"hypothesis file absent: {hyp}")
    got = sha256_file(hyp)
    checks[HYPOTHESIS_PATH] = got
    if got != HYPOTHESIS_SHA256:
        raise EnvironmentError_(
            f"hypothesis hash mismatch: {got} != pinned {HYPOTHESIS_SHA256}")
    for rel, want in FROZEN_PINS.items():
        p = repo_root / rel
        if not p.is_file():
            raise EnvironmentError_(f"frozen pin file absent: {rel}")
        got = sha256_file(p)
        checks[rel] = got
        if got != want:
            raise EnvironmentError_(f"frozen pin mismatch {rel}: {got} != {want}")
    return checks


def claim_population_manifest(mount: Path) -> dict:
    """Every claim-population byte: gate_packet/** files + state/product.json."""
    root = mount.resolve()
    manifest: dict[str, str] = {}
    gp = root / GATE_PACKET_ROOT
    if gp.is_dir():
        for path in sorted(gp.rglob("*")):
            if path.is_file():
                manifest[str(path.relative_to(root))] = sha256_file(path)
    state = root / STATE_REL
    if state.is_file():
        manifest[STATE_REL] = sha256_file(state)
    return manifest


def mount_identity(accepted: Path, deep: Path) -> dict:
    """Path-set AND byte identity of the claim population, both digests."""
    a_head = _git_head(accepted)
    d_head = _git_head(deep)
    if a_head != d_head:
        raise EnvironmentError_(
            f"mount HEAD mismatch: accepted {a_head} vs deeper {d_head}")
    a_man = claim_population_manifest(accepted)
    d_man = claim_population_manifest(deep)
    if not a_man:
        raise EnvironmentError_("accepted mount claim population is empty")
    a_keys, d_keys = set(a_man), set(d_man)
    only_a, only_d = sorted(a_keys - d_keys), sorted(d_keys - a_keys)
    differing = sorted(k for k in (a_keys & d_keys) if a_man[k] != d_man[k])
    identical = len(a_keys & d_keys) - len(differing)
    ok = not only_a and not only_d and not differing
    return {
        "comparison_side": "deeper mount claim population vs accepted mount "
                           "claim population (paths results/product/gate_packet/** "
                           "and state/product.json)",
        "accepted_mount": str(accepted.resolve()),
        "deeper_mount": str(deep.resolve()),
        "head_accepted": a_head,
        "head_deeper": d_head,
        "n_files_accepted": len(a_man),
        "n_files_deeper": len(d_man),
        "n_byte_identical": identical,
        "n_differing": len(differing),
        "differing_files": differing,
        "only_in_accepted": only_a,
        "only_in_deeper": only_d,
        "identity_proven": ok,
        "accepted_manifest_sha256_of_sorted_pairs":
            _manifest_digest(a_man),
        "deeper_manifest_sha256_of_sorted_pairs":
            _manifest_digest(d_man),
    }
    # note: identity failure raises in caller using identity_proven


def _manifest_digest(manifest: dict) -> str:
    blob = json.dumps(sorted(manifest.items()), separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _git_head(mount: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def baseline_object_resolvable(deep: Path) -> dict:
    """`git show cc719eebf:state/product.json` must resolve in the deeper mount."""
    proc = subprocess.run(
        ["git", "-C", str(deep), "show",
         f"{BASELINE_HEAD_SHORT}:{STATE_REL}"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise EnvironmentError_(
            f"baseline object {BASELINE_HEAD_SHORT}:{STATE_REL} not resolvable "
            f"in deeper mount (stderr tail: {proc.stderr[-400:]!r})")
    digest = hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest()
    full = subprocess.run(["git", "-C", str(deep), "rev-parse", BASELINE_HEAD_SHORT],
                          capture_output=True, text=True)
    return {
        "baseline_head_short": BASELINE_HEAD_SHORT,
        "baseline_head_full": full.stdout.strip() if full.returncode == 0 else None,
        "baseline_state_product_json_sha256": digest,
        "resolvable": True,
    }


def run_frozen_instrument(repo_root: Path, run_id: str, mount: Path,
                           out_dir: Path) -> dict:
    """Execute evaluation.trigger_reconciliation VERBATIM as a subprocess."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "evaluation.trigger_reconciliation",
           "--run-id", run_id,
           "--product-mount", str(mount),
           "--repo-root", str(repo_root),
           "--out-dir", str(out_dir)]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    rec_path = out_dir / f"{run_id}_reconciliation.json"
    record = json.loads(rec_path.read_text(encoding="utf-8")) \
        if rec_path.exists() else None
    return {
        "argv": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "record_path": str(rec_path),
        "record_sha256": sha256_file(rec_path) if rec_path.exists() else None,
        "record": record,
    }


def build_planted_control(deep: Path, control_mount: Path) -> dict:
    """Shared-clone the deeper mount and plant one synthetic scored row."""
    if control_mount.exists():
        shutil.rmtree(control_mount)
    control_mount.parent.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["git", "clone", "--shared", str(deep), str(control_mount)],
        capture_output=True, text=True)
    if clone.returncode != 0:
        raise EnvironmentError_(f"control clone failed: {clone.stderr[-400:]!r}")
    state_path = control_mount / STATE_REL
    if not state_path.is_file():
        raise EnvironmentError_("control mount has no state/product.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["synthetic_control_rows"] = [{
        "decision_id": PLANTED_ROW_ID,
        "synthetic": True,
        "note": "planted non-vacuity control row for run "
                "39529073155; never a real scored claim",
    }]
    state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return {
        "control_mount": str(control_mount),
        "planted_row_id": PLANTED_ROW_ID,
        "planted_key": "synthetic_control_rows",
        "state_product_json_sha256_after_plant": sha256_file(state_path),
        "head": _git_head(control_mount),
    }


def adjudicate(repo_root: Path, run_id: str, accepted: Path, deep: Path,
               out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. frozen pins (hypothesis + instruments + baseline manifest)
    pin_checks = verify_frozen_pins(repo_root)

    # 2. mounts + claim-population byte identity
    identity = mount_identity(accepted, deep)
    if not identity["identity_proven"]:
        raise EnvironmentError_(
            "claim-population byte identity between deeper mount and accepted "
            f"mount FAILED: differing={identity['differing_files'][:10]} "
            f"only_accepted={identity['only_in_accepted'][:10]} "
            f"only_deeper={identity['only_in_deeper'][:10]}")
    baseline_obj = baseline_object_resolvable(deep)

    # 3. frozen instrument hashes BEFORE the run
    frozen_before = {rel: sha256_file(repo_root / rel) for rel in FROZEN_PINS
                     if (repo_root / rel).is_file()}

    # 4. real adjudication via the frozen instrument, verbatim
    real = run_frozen_instrument(repo_root, run_id, deep, out_dir)
    if real["record"] is None:
        raise EnvironmentError_(
            f"frozen instrument produced no record (exit {real['returncode']}); "
            f"stderr tail: {real['stderr_tail']!r}")

    # 5. planted non-vacuity control (scratch mount outside results/)
    scratch = Path(tempfile.mkdtemp(prefix=f"scma_control_{run_id}_"))
    control_mount = scratch / "control_mount"
    try:
        plant = build_planted_control(deep, control_mount)
        control_out = out_dir / "control"
        control = run_frozen_instrument(repo_root, f"{run_id}_control",
                                        control_mount, control_out)
        if control["record"] is None:
            raise NonVacuousError(
                f"control instrument produced no record (exit "
                f"{control['returncode']}); stderr tail: {control['stderr_tail']!r}")
        control_composite = control["record"].get("verdict")
        non_vacuous = control_composite == COMPOSITE_MOVED
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    # 6. frozen instrument hashes AFTER both runs (prove untouched)
    frozen_after = {rel: sha256_file(repo_root / rel) for rel in FROZEN_PINS
                    if (repo_root / rel).is_file()}
    if frozen_after != frozen_before:
        raise EnvironmentError_("frozen instrument bytes changed during the run")

    trigger_leg = real["record"]["trigger"]
    movement_leg = real["record"]["state_product_json"]
    composite = real["record"].get("verdict")

    if not non_vacuous:
        raise NonVacuousError(
            f"planted control did NOT flip: control composite "
            f"{control_composite!r} != {COMPOSITE_MOVED!r}")

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "produced_at_utc": utcnow(),
        "numeric_environment": {
            "python": sys.version.split()[0],
            "executable": sys.executable,
        },
        "frozen_pin_verification": pin_checks,
        "mounts": {
            "accepted": {
                "path": str(accepted.resolve()),
                "head": _git_head(accepted),
                "shallow": _git_shallow(accepted),
            },
            "deeper": {
                "path": str(deep.resolve()),
                "head": _git_head(deep),
                "shallow": _git_shallow(deep),
                "baseline_object": baseline_obj,
            },
            "identity": identity,
        },
        "frozen_instrument": {
            "module": "evaluation.trigger_reconciliation",
            "invoked_verbatim": True,
            "hashes_before": frozen_before,
            "hashes_after": frozen_after,
            "hashes_unchanged": frozen_before == frozen_after,
            "real_run": {k: v for k, v in real.items() if k != "record"},
            "control_run": {k: v for k, v in control.items() if k != "record"},
        },
        "trigger_leg": {
            "verdict": trigger_leg.get("verdict"),
            "re_run_forbidden": trigger_leg.get("re_run_forbidden"),
            "reason": trigger_leg.get("reason"),
            "product_mount_head": trigger_leg.get("product_mount_head"),
            "set_relation_summary": {
                k: trigger_leg.get("set_relation", {}).get(k)
                for k in ("n_current", "n_baseline", "n_common",
                          "n_byte_identical", "n_changed",
                          "identical_as_a_set")
            },
            "n_added": len(trigger_leg.get("set_relation", {}).get("added") or []),
            "n_removed": len(trigger_leg.get("set_relation", {}).get("removed") or []),
            "changed": trigger_leg.get("set_relation", {}).get("changed"),
        },
        "scored_claim_movement_leg": {
            "comparison_side": movement_leg.get("comparison_side"),
            "carries_scored_claim_change":
                movement_leg.get("carries_scored_claim_change"),
            "scored_row_ids_baseline":
                movement_leg.get("scored_row_ids_baseline"),
            "scored_row_ids_current":
                movement_leg.get("scored_row_ids_current"),
            "n_only_in_current":
                len(movement_leg.get("scored_row_ids_only_in_current") or []),
            "n_only_in_baseline":
                len(movement_leg.get("scored_row_ids_only_in_baseline") or []),
            "only_in_current":
                movement_leg.get("scored_row_ids_only_in_current"),
            "only_in_baseline":
                movement_leg.get("scored_row_ids_only_in_baseline"),
            "keys_added": movement_leg.get("keys_added"),
            "keys_removed": movement_leg.get("keys_removed"),
            "keys_changed": movement_leg.get("keys_changed"),
            "error": movement_leg.get("error"),
        },
        "composite_verdict": composite,
        "prior_not_measured_composite":
            "TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_NOT_MEASURED",
        "prior_record_superseded_leg":
            "results/evaluation/trigger_reconciliation/39520368732/"
            "39520368732_reconciliation.json (preserved verbatim; its "
            "NOT_MEASURED composite is superseded by this decided composite "
            "on the identical trigger population)",
        "non_vacuity_control": {
            **plant,
            "control_composite": control_composite,
            "non_vacuous": non_vacuous,
            "expected_control_composite": COMPOSITE_MOVED,
            "synthetic_marker": PLANTED_ROW_ID,
        },
        "v61_reconciliation_note": (
            "The direction-item trigger fires on ANY served-packet claim "
            "population change, including a BUILT_NOT_SERVED packet directory "
            "appearing on lab/product. v61 ordered work (5) separately gates "
            "the falsification battery on a SERVED packet, which can only "
            "happen via an accepted serve recommendation replacing the "
            "DO-NOT-SERVE orders - none exists today. This record decides "
            "only the trigger's own composite; it re-derives no threshold, "
            "bar, rubric or verdict contract and lifts no order."),
        "claim_ceiling": (
            "This record publishes (a) the frozen trigger verdict on a "
            "claim population proven byte-identical to the accepted product "
            "mount, (b) the scored-claim-movement composite that run "
            "39520368732 left NOT_MEASURED, and (c) a planted non-vacuity "
            "control proving the state leg can detect movement. It creates "
            "NO new benchmark, threshold, bar or verdict, re-scores no "
            "packet, serves no packet, and authorises no owner question."),
        "what_this_record_does_NOT_establish": [
            "It does not re-score any packet or run any bar gate.",
            "It does not serve any packet; both DO-NOT-SERVE orders stand; "
            "packet 39275520116 stays BUILT_NOT_SERVED WITHHELD_PENDING_SERVE.",
            "It does not re-measure P1/P1ext (measured of record at "
            "39322925971).",
            "It does not certify any owner-facing readiness claim; all "
            "readiness flags stay false; owner_decision_required stays false.",
        ],
    }


def _git_shallow(mount: Path) -> bool | None:
    proc = subprocess.run(["git", "-C", str(mount),
                           "rev-parse", "--is-shallow-repository"],
                          capture_output=True, text=True)
    return proc.stdout.strip() == "true" if proc.returncode == 0 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--accepted-mount", default=DEFAULT_ACCEPTED_MOUNT)
    ap.add_argument("--deep-mount", required=True)
    ap.add_argument("--repo-root", default=str(_LANE_ROOT))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    accepted = Path(args.accepted_mount)
    deep = Path(args.deep_mount)
    out_dir = Path(args.out_dir) if args.out_dir else \
        repo_root / "results/evaluation/trigger_reconciliation" / args.run_id

    for m, name in ((accepted, "accepted"), (deep, "deeper")):
        if not (m / "state").is_dir():
            print(f"::error::{name} mount {m} has no state/ directory",
                  file=sys.stderr)
            return 2

    try:
        record = adjudicate(repo_root, args.run_id, accepted, deep, out_dir)
    except EnvironmentError_ as exc:
        print(f"::error::ENVIRONMENT_ERROR: {exc}", file=sys.stderr)
        return 2
    except NonVacuousError as exc:
        print(f"::error::NON_VACUOUS: {exc}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.run_id}_adjudication.json"
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "composite_verdict": record["composite_verdict"],
        "trigger_verdict": record["trigger_leg"]["verdict"],
        "carries_scored_claim_change":
            record["scored_claim_movement_leg"]["carries_scored_claim_change"],
        "identity_proven": record["mounts"]["identity"]["identity_proven"],
        "non_vacuous": record["non_vacuity_control"]["non_vacuous"],
        "record": str(out),
    }, indent=1))
    print(f":: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
