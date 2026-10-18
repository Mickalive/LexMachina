#!/usr/bin/env python3
"""Execute the factory direction's own falsification trigger and reconcile it.

    python -m evaluation.trigger_reconciliation --run-id <run_id>

WHY THIS MODULE EXISTS
======================
Run 39079133613's independent audit (results/audit/evaluation/
CYCLE_39079133613_GATE.json, gate=REVISE, safe_to_integrate=false, fix R1/R2)
found that this lane had published ``NO_NEW_PACKET`` / "direction item (1)
re-score trigger does not fire" in FOUR consecutive cycles (39064597912,
39072968899, 39076123103, 39079133613) WITHOUT EVER EXECUTING the direction's
own executable mechanism::

    python -m evaluation.newhead_recompute --mode trigger

The audit executed it against the exact product mount the report named
(origin/lab/product @ 03a4cabb) and got ``verdict=ADJUDICATE_REQUIRED``. The
lane's headline trigger verdict was therefore FALSE, and no snapshot-audit
check could see it: check 19 certifies that prose agrees with the record that
MEASURES it, and no record measured the trigger. A false claim the record never
measured passes vacuously. That is the class of hole R2 names.

This module is the smallest instrument that closes R1 (execute + publish the
trigger record, retract NO_NEW_PACKET) and supplies the measured record that the
new snapshot-audit check 21 reconciles prose against (R2).

WHAT IT MEASURES (and what it does NOT)
=======================================
It measures two SEPARATE things and deliberately never collapses them:

  1. TRIGGER VERDICT -- the direction's own set-relation mechanism, executed as
     a subprocess against the accepted product mount with the direction-pinned
     baseline manifest. ``ADJUDICATE_REQUIRED`` / ``NO_NEW_PACKET``.

  2. SCORED-CLAIM MOVEMENT -- whether the population delta the trigger reports
     actually changes any SCORED claim (a counter-label row, a score, a cluster
     assignment, a projection coordinate). This is computed by byte-comparing
     the newly served packet files against the already-adjudicated packet
     snapshot committed by run 39049030442, and by diffing ``state/product.json``
     against its pinned-baseline bytes at the baseline product head.

The separation is the whole point. A firing trigger with no scored-claim
movement is a REAL signal whose correct consequence is a GATE OF RECORD, not a
new measurement and not a new verdict. Reporting only (1) would be alarmist;
reporting only (2) would be exactly the false negative R1 falsified. Both are
published side by side.

NO FROZEN FILE IS WRITTEN, REGENERATED OR RE-TUNED. No rubric, threshold, bar,
benchmark, baseline or success rule is touched. This module only executes an
existing frozen instrument and records what it returned. Exit code 0 does NOT
mean the trigger did not fire.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "lex-evaluation-trigger-reconciliation/1"

#: The direction-pinned baseline manifest. Written once by run 39027041693; it is
#: a PROVENANCE PIN, not a verdict, and it is read-only here.
BASELINE_MANIFEST = ("results/evaluation/newhead_recompute_39027041693/"
                     "served_packet_baseline_39027041693.json")

#: The already-adjudicated snapshot of the rebuilt packet (run 39049030442).
#: Its packet.json is the direction pin 2942c3c2....
ADJUDICATED_PACKET_SNAPSHOT = "results/evaluation/rebuilt_packet_adjudication_39049030442/packet"

#: The adjudication of record for those same bytes.
ADJUDICATION_OF_RECORD = ("results/evaluation/rebuilt_packet_adjudication_39049030442/"
                          "39049030442_adjudication.json")

DEFAULT_PRODUCT_MOUNT = "/tmp/lex_accepted/product"

#: Keys of a served-packet population under comparison. Named explicitly so the
#: COMPARISON SIDE of every published relation is unambiguous (audit fix R4:
#: the 13-file relation reproduces only against results/product/gate_packet/
#: rebuilt-39027045675/, not against the accepted SERVED dir 38839347028/).
GATE_PACKET_ROOT = "results/product/gate_packet"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_trigger(repo_root: Path, run_id: str, out_dir: Path,
                 product_mount: Path) -> dict:
    """Execute the frozen direction mechanism verbatim, as a subprocess."""
    cmd = [sys.executable, "-m", "evaluation.newhead_recompute",
           "--mode", "trigger",
           "--run-id", run_id,
           "--product-mount", str(product_mount),
           "--out-dir", str(out_dir),
           "--baseline-manifest", BASELINE_MANIFEST]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    return {"argv": cmd, "returncode": proc.returncode,
            "stderr_tail": (proc.stderr or "")[-2000:]}


def _packet_dirs(mount: Path) -> list[str]:
    root = mount / GATE_PACKET_ROOT
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def _scored_row_ids(obj) -> set:
    """Collect identifiers of scored claim rows anywhere in a JSON tree."""
    ids: set = set()
    if isinstance(obj, dict):
        for key in ("decision_id", "qid", "row_id", "anchor_qid"):
            if key in obj and isinstance(obj[key], (str, int)):
                ids.add(f"{key}={obj[key]}")
        for v in obj.values():
            ids |= _scored_row_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            ids |= _scored_row_ids(v)
    return ids


def _json_diff(old: dict, new: dict) -> dict:
    keys = set(old) | set(new)
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    changed = sorted(k for k in (set(old) & set(new)) if old[k] != new[k])
    return {"keys_added": added, "keys_removed": removed, "keys_changed": changed}


def reconcile(repo_root: Path, run_id: str, product_mount: Path,
              out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    trigger_exec = _run_trigger(repo_root, run_id, out_dir, product_mount)
    trigger_record_path = out_dir / f"{run_id}_trigger.json"
    trigger = json.loads(trigger_record_path.read_text(encoding="utf-8")) \
        if trigger_record_path.exists() else {}

    # ---- (2a) newly served packet bytes vs the already-adjudicated bytes ----
    added = (trigger.get("set_relation") or {}).get("added") or []
    added_dirs = sorted({m.group(1) for p in added
                         if (m := re.match(re.escape(GATE_PACKET_ROOT) + r"/([^/]+)/", p))})
    adj_root = repo_root / ADJUDICATED_PACKET_SNAPSHOT
    byte_relation, unidentified = {}, []
    for d in added_dirs:
        cur = product_mount / GATE_PACKET_ROOT / d
        base = adj_root
        if not cur.is_dir():
            byte_relation[d] = {"error": "absent from the product mount"}
            continue
        if not base.is_dir():
            byte_relation[d] = {"error": "adjudicated snapshot absent from the lane tree"}
            continue
        cur_files = sorted(str(p.relative_to(cur)) for p in cur.rglob("*") if p.is_file())
        base_files = sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())
        identical, differing = [], []
        for rel in cur_files:
            if rel not in base_files:
                differing.append(rel)
            elif sha256_file(cur / rel) == sha256_file(base / rel):
                identical.append(rel)
            else:
                differing.append(rel)
        byte_relation[d] = {
            "comparison_side": f"product mount {GATE_PACKET_ROOT}/{d}/  vs  "
                               f"lane tree {ADJUDICATED_PACKET_SNAPSHOT}/",
            "n_current_files": len(cur_files), "n_adjudicated_files": len(base_files),
            "n_byte_identical": len(identical),
            "n_differing": len(differing), "differing_files": differing,
            "only_in_current": sorted(set(cur_files) - set(base_files)),
            "only_in_adjudicated": sorted(set(base_files) - set(cur_files)),
        }
    for p in added:
        if not any(p.startswith(f"{GATE_PACKET_ROOT}/{d}/") for d in added_dirs):
            unidentified.append(p)

    packet_json_sha = None
    for d in added_dirs:
        p = product_mount / GATE_PACKET_ROOT / d / "packet.json"
        if p.is_file():
            packet_json_sha = sha256_file(p)

    # ---- (2b) does the changed state/product.json carry a scored claim? ----
    manifest = json.loads((repo_root / BASELINE_MANIFEST).read_text(encoding="utf-8"))
    baseline_head = str(manifest.get("product_head") or "").split()[0]
    state_relation: dict = {"baseline_product_head": baseline_head}
    cur_state_path = product_mount / "state/product.json"
    if not cur_state_path.exists():
        state_relation["error"] = "state/product.json absent from the product mount"
    elif not baseline_head:
        state_relation["error"] = "baseline manifest carries no product_head to diff against"
    else:
        old_proc = subprocess.run(["git", "-C", str(product_mount), "show",
                                   f"{baseline_head}:state/product.json"],
                                  capture_output=True, text=True)
        if old_proc.returncode != 0:
            state_relation["error"] = ("baseline state/product.json not retrievable at "
                                       f"{baseline_head} (shallow history?)")
            state_relation["git_stderr_tail"] = old_proc.stderr[-400:]
        else:
            old_state = json.loads(old_proc.stdout)
            new_state = json.loads(cur_state_path.read_text(encoding="utf-8"))
            old_rows, new_rows = _scored_row_ids(old_state), _scored_row_ids(new_state)
            state_relation.update({
                "comparison_side": f"product mount state/product.json (HEAD) vs "
                                   f"state/product.json at baseline product head {baseline_head}",
                "sha256_current": sha256_file(cur_state_path),
                **_json_diff(old_state, new_state),
                "scored_row_ids_baseline": len(old_rows),
                "scored_row_ids_current": len(new_rows),
                "scored_row_ids_only_in_current": sorted(new_rows - old_rows),
                "scored_row_ids_only_in_baseline": sorted(old_rows - new_rows),
            })
            state_relation["carries_scored_claim_change"] = bool(
                new_rows - old_rows or old_rows - new_rows)

    # ---- honest composite verdict -----------------------------------------
    trigger_verdict = trigger.get("verdict")
    scored_change = state_relation.get("carries_scored_claim_change")
    if scored_change is None:
        composite = "TRIGGER_FIRES__SCORED_CLAIM_MOVEMENT_NOT_MEASURED"
    elif scored_change:
        composite = "TRIGGER_FIRES__SCORED_CLAIM_MOVED__RE_SCORE_JUSTIFIED"
    else:
        composite = "TRIGGER_FIRES__NO_SCORED_CLAIM_MOVEMENT__RE_SCORE_WOULD_BE_A_NO_OP"

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "produced_at_utc": _utcnow(),
        "trigger": {
            "mechanism": "python -m evaluation.newhead_recompute --mode trigger",
            "argv": trigger_exec["argv"],
            "returncode": trigger_exec["returncode"],
            "stderr_tail": trigger_exec["stderr_tail"],
            "record_path": _rel(trigger_record_path, repo_root),
            "record_sha256": sha256_file(trigger_record_path)
            if trigger_record_path.exists() else None,
            "verdict": trigger_verdict,
            "re_run_forbidden": trigger.get("re_run_forbidden"),
            "reason": trigger.get("reason"),
            "set_relation": trigger.get("set_relation"),
            "product_mount_head": _git_head(product_mount),
        },
        "newly_served_packet_bytes": {
            "comparison_side": f"product mount {GATE_PACKET_ROOT}/<dir>/ vs lane tree "
                               f"{ADJUDICATED_PACKET_SNAPSHOT}/",
            "packet_dirs": added_dirs,
            "relations": byte_relation,
            "packet_json_sha256": packet_json_sha,
            "adjudication_of_record": ADJUDICATION_OF_RECORD,
            "unmatched_added_paths": unidentified,
        },
        "state_product_json": state_relation,
        "verdict": composite,
        "retracted_claim": "NO_NEW_PACKET",
        "claim_ceiling": (
            "This record publishes the trigger verdict the direction's own frozen "
            "mechanism returns, plus whether the reported population delta moves any "
            "SCORED claim. It creates NO new benchmark, threshold, bar or verdict, and "
            "it does not re-adjudicate any packet. A firing trigger whose scored "
            "content is unchanged is a GATE-OF-RECORD signal, not a licence to raise "
            "or lower any product claim. NO_NEW_PACKET is RETRACTED: it was published "
            "in cycles 39064597912 / 39072968899 / 39076123103 / 39079133613 without "
            "ever executing this trigger."),
        "what_this_record_does_NOT_establish": [
            "It does not establish that the served packet should or should not be admitted; "
            "that is the product admission gate's question, not the trigger's.",
            "It does not re-open the accepted rebuilt-packet adjudication "
            "(results/evaluation/rebuilt_packet_adjudication_39049030442), whose bytes are "
            "re-hashed here and not re-scored.",
            "It does not certify any owner-facing readiness claim; human_gate_ready stays false.",
        ],
    }


def _utcnow() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path, repo_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return None


def _git_head(mount: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--product-mount",
                    default=os.environ.get("LEX_PRODUCT_MOUNT", DEFAULT_PRODUCT_MOUNT))
    ap.add_argument("--repo-root", default=str(Path.cwd()))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    mount = Path(args.product_mount)
    out_dir = Path(args.out_dir) if args.out_dir else \
        repo_root / "results/evaluation/trigger_reconciliation" / args.run_id

    if not (mount / "state").is_dir():
        print(f"::error::product mount {mount} has no state/ directory", file=sys.stderr)
        return 2

    record = reconcile(repo_root, args.run_id, mount, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.run_id}_reconciliation.json"
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"verdict": record["verdict"],
                      "trigger_verdict": record["trigger"]["verdict"],
                      "re_run_forbidden": record["trigger"]["re_run_forbidden"],
                      "scored_claim_change": record["state_product_json"]
                      .get("carries_scored_claim_change"),
                      "record": str(out)}, indent=1))
    print(f":: wrote {out}")
    # Exit 0 means "the instrument ran", NOT "the trigger did not fire".
    return 0 if record["trigger"]["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())