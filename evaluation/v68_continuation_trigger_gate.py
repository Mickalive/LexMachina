#!/usr/bin/env python3
"""v68 continuation trigger gate: is another same-question evaluation cycle discriminating?

WHAT THIS IS
------------
A small OPERATIONAL instrument that machine-checks the two continuation triggers
named in factory direction v68 for the evaluation lane, so the lane's
``continue_recommended`` decision and the conditional ordered item (2) are
decided from committed bytes instead of from prose:

* TRIGGER A - the product retrieval/reranking surface changed. Measured as the
  set relation between the git-tree blob sha256 of every path under
  ``product/query/`` at the last recall-measured accepted product head
  (5fb312e4) and at the current accepted product head carried by the mount.
* TRIGGER B - the frozen 15-member flagship probe family is member-for-member
  regenerated. Reused, not re-derived, by calling
  ``evaluation.post_repair_family_ca_falsifier.precondition_gate`` with the
  SAME frozen hypothesis this cycle commits for the companion falsifier.

CLAIM CEILING (read before quoting anything from this file)
-----------------------------------------------------------
This instrument measures BYTE IDENTITY and SET RELATIONS only. It makes no
quality, recall, counter-authority, geometry, serve or human-gate claim, it
moves no bar, and a NO_TRIGGER verdict is NOT evidence that the product is
good - only that re-executing an unchanged instrument on unchanged bytes would
be zero delta. It is deliberately separate from the claim-bearing falsifier so
that an operational gate can never be mistaken for a measurement of product
behaviour.

Exit codes (deliberately NOT an outcome signal, so no workflow can read a
trigger as a job failure):
  0  measured successfully (regardless of which triggers fired - see verdict)
  2  NOT_MEASURED (git/mount/hypothesis unavailable or pin drift)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-v68-continuation-trigger-gate/1"
HYPOTHESIS_RELPATH = "evaluation/V68_CONTINUATION_TRIGGER_GATE_44861140260_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/V68_CONTINUATION_TRIGGER_GATE_44861140260_FREEZE_V1.json"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/v68_continuation_trigger_gate"

EXIT_MEASURED = 0
EXIT_NOT_MEASURED = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT),
                          capture_output=True, text=True, timeout=120)


def git_blob_sha256(commit: str, path: str) -> str | None:
    p = subprocess.run(["git", "cat-file", "blob", f"{commit}:{path}"],
                       cwd=str(REPO_ROOT), capture_output=True, timeout=120)
    if p.returncode != 0:
        return None
    return sha256_bytes(p.stdout)


def git_paths(commit: str, prefix: str) -> list[str]:
    p = git(["ls-tree", "-r", "--name-only", commit, "--", prefix])
    if p.returncode != 0:
        raise RuntimeError(f"git ls-tree failed for {commit}: {p.stderr.strip()}")
    return [ln for ln in p.stdout.splitlines() if ln]


def mount_head(mount: Path) -> str | None:
    p = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                       capture_output=True, text=True, timeout=30)
    return p.stdout.strip() or None


def numeric_environment() -> dict:
    env = {"python": sys.version.split()[0], "platform": sys.platform}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    return env


def trigger_a(hyp: dict, mount: Path) -> dict:
    """Set relation of product/query/ blob sha256 between baseline and current head."""
    spec = hyp["triggers_FROZEN"]["trigger_A_retrieval_reranking_code_changed"]
    baseline = spec["baseline_head"]
    current = mount_head(mount) or spec["expected_current_head"]
    prefix = spec["path_prefix"]

    base_paths = git_paths(baseline, prefix)
    cur_paths = git_paths(current, prefix)
    base_set, cur_set = set(base_paths), set(cur_paths)

    added = sorted(cur_set - base_set)
    removed = sorted(base_set - cur_set)
    common = sorted(base_set & cur_set)

    modified: list[dict] = []
    identical = 0
    for rel in common:
        b = git_blob_sha256(baseline, rel)
        c = git_blob_sha256(current, rel)
        if b == c and b is not None:
            identical += 1
        else:
            modified.append({"path": rel, "baseline_sha256": b,
                             "current_sha256": c})

    # the mount I am about to score must carry exactly the current-head bytes
    mount_mismatch: list[dict] = []
    for rel in cur_paths:
        mp = mount / rel
        if not mp.is_file():
            mount_mismatch.append({"path": rel, "reason": "absent_in_mount"})
            continue
        m = sha256_file(mp)
        c = git_blob_sha256(current, rel)
        if m != c:
            mount_mismatch.append({"path": rel, "mount_sha256": m,
                                   "current_sha256": c})

    changed = bool(added or removed or modified)
    return {
        "trigger": "A_retrieval_reranking_code_changed",
        "definition": spec["definition"],
        "baseline_head": baseline,
        "baseline_rationale": spec["baseline_rationale"],
        "current_head": current,
        "path_prefix": prefix,
        "fired": changed,
        "set_relations_REQUIREMENT_16": {
            "baseline_n": len(base_set),
            "current_n": len(cur_set),
            "added_n": len(added), "added": added,
            "removed_n": len(removed), "removed": removed,
            "common_n": len(common),
            "modified_n": len(modified), "modified": modified,
            "identical_n": identical,
            "interpretation": ("product/query/ is byte-identical between the two "
                               "heads, so any retrieval-recall instrument "
                               "re-executed on unchanged cached inputs would "
                               "reproduce its previous verdict by construction"
                               if not changed else
                               "product/query/ CHANGED between the two heads; a "
                               "retrieval/recall re-measure on new bytes is "
                               "discriminating"),
        },
        "mount_matches_current_head": {
            "holds": not mount_mismatch,
            "n_files_checked": len(cur_paths),
            "mismatches": mount_mismatch,
        },
    }


def trigger_b(hyp: dict, mount: Path) -> dict:
    """Family regeneration, reused from the accepted precondition gate."""
    from evaluation import post_repair_family_ca_falsifier as PRF

    spec = hyp["triggers_FROZEN"]["trigger_B_full_family_regenerated"]
    ca_path = REPO_ROOT / spec["ca_hypothesis_file"]
    actual = sha256_file(ca_path)
    pin_ok = actual == spec["ca_hypothesis_sha256_at_freeze"]
    ca_hyp = json.loads(ca_path.read_text(encoding="utf-8"))
    gate = PRF.precondition_gate(ca_hyp, mount)
    relation = gate["set_relations_REQUIREMENT_16"]["member_for_member_matching"]
    return {
        "trigger": "B_full_family_regenerated",
        "definition": spec["definition"],
        "reused_from": "evaluation/post_repair_family_ca_falsifier.precondition_gate "
                       "(accepted instrument, run 40258497460, sha 126a1234...)",
        "ca_hypothesis_file": spec["ca_hypothesis_file"],
        "ca_hypothesis_sha256_at_freeze": spec["ca_hypothesis_sha256_at_freeze"],
        "ca_hypothesis_sha256_actual": actual,
        "ca_hypothesis_pin_ok": pin_ok,
        "fired": bool(gate["H2_precondition_full_family_regenerated"]),
        "leg_landed": bool(gate["H1_precondition_leg_landed"]),
        "member_for_member_matching": relation,
        "item_2_full_protocol_status": gate["item_2_full_protocol_status"],
        "set_relations_REQUIREMENT_16": gate["set_relations_REQUIREMENT_16"],
    }


def evaluate(run_id: str, mount: Path) -> dict:
    hyp_path = REPO_ROOT / HYPOTHESIS_RELPATH
    freeze_path = REPO_ROOT / FREEZE_RELPATH
    hyp = json.loads(hyp_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    hyp_sha = sha256_file(hyp_path)
    freeze_sha = sha256_file(freeze_path)

    vacuous: list[str] = []
    if hyp_sha != freeze.get("hypothesis_sha256_at_freeze"):
        vacuous.append("hypothesis sha256 differs from the freeze record")
    if mount_head(mount) != hyp["triggers_FROZEN"]["trigger_A_retrieval_reranking_code_changed"][
            "expected_current_head"]:
        vacuous.append("mount head differs from the frozen expected head")

    # frozen input re-hash (identity only, never a quality bar)
    pin_rows = []
    pins_ok = True
    for rel, expected in (hyp.get("frozen_inputs_REPORTED_ONLY") or {}).items():
        if rel.startswith("mount:"):
            path = mount / rel[6:]
        else:
            path = REPO_ROOT / rel
        actual = sha256_file(path) if path.is_file() else None
        ok = actual == expected
        pins_ok = pins_ok and ok
        pin_rows.append({"input": rel, "expected": expected, "actual": actual,
                         "match": ok})
    if not pins_ok:
        vacuous.append("frozen input pin drift")

    try:
        a = trigger_a(hyp, mount)
        b = trigger_b(hyp, mount)
    except Exception as exc:  # noqa: BLE001 - measurement failure, reported
        return {
            "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
            "direction_version": hyp["direction_version"],
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verdict": "NOT_MEASURED", "exit_code": EXIT_NOT_MEASURED,
            "error": f"{type(exc).__name__}: {exc}",
            "hypothesis": {"path": HYPOTHESIS_RELPATH, "sha256": hyp_sha},
            "freeze_record": {"path": FREEZE_RELPATH, "sha256": freeze_sha},
            "claim_ceiling": hyp["claim_ceiling"],
            "human_gate_ready": False, "machine_gate_ready": False,
            "owner_decision_required": False,
        }

    if vacuous:
        verdict, code = "NOT_MEASURED_VACUOUS", EXIT_NOT_MEASURED
    elif a["fired"] and b["fired"]:
        verdict, code = "TRIGGERS_A_AND_B_FIRED", EXIT_MEASURED
    elif a["fired"]:
        verdict, code = "TRIGGER_A_FIRED_RETRIEVAL_CODE_CHANGED", EXIT_MEASURED
    elif b["fired"]:
        verdict, code = "TRIGGER_B_FIRED_FAMILY_REGENERATED", EXIT_MEASURED
    else:
        verdict, code = "NO_TRIGGER_FIRED_NOT_DISCRIMINATING", EXIT_MEASURED

    return {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": hyp["direction_version"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": hyp["entry_point"],
        "verdict": verdict,
        "exit_code": code,
        "exit_code_contract": hyp["exit_code_contract"],
        "hypothesis": {"path": HYPOTHESIS_RELPATH, "sha256": hyp_sha},
        "freeze_record": {"path": FREEZE_RELPATH, "sha256": freeze_sha},
        "frozen_inputs": {"all_match": pins_ok, "checks": pin_rows},
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "trigger_A": a,
        "trigger_B": b,
        "next_step_map_FROZEN": hyp["next_step_map_FROZEN"],
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted cycle 40133253347); not re-run",
            "item_2_conditional_remeasure": b["item_2_full_protocol_status"],
            "item_2_leg_half": "LANDED" if b["leg_landed"] else "NOT_LANDED",
            "item_3_standing_falsification_record": "UNCHANGED; benchmark of record "
                "PRODUCT_FALSIFIED on packet-of-record 39319405429 untouched here",
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504": "reported only "
                "where this lane quotes those counts: D1 wording 6-vs-7 tests, D2 "
                "wording new-vs-appended test file, D3 environment skip variance "
                "172/1309/20 vs 172/1308/21 - all non-blocking, gate PASS",
            "item_5_no_re_derivation": "honoured: no frozen bench, no D2 profile, no "
                "bypass diagnosis, no universal-174k benchmark is re-derived here",
        },
        "claim_ceiling": hyp["claim_ceiling"],
        "numeric_environment": numeric_environment(),
        "network_calls": 0,
        "no_174k_benchmark_rerun": True,
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
        "vacuous_reasons": vacuous,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    rec = evaluate(run_id, Path(args.mount))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run_id}.json"
    out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "trigger_A_fired": rec.get("trigger_A", {}).get("fired"),
        "trigger_B_fired": rec.get("trigger_B", {}).get("fired"),
        "item_2_status": rec.get("trigger_B", {}).get("item_2_full_protocol_status"),
        "record": str(out),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
