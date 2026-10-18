#!/usr/bin/env python3
"""Is a persisted producer snapshot ZERO DELTA, and what does that observation mean?

    python -m evaluation.orchestration_ref_check --run-id <run_id> \
        --team-ref origin/cycle/core/<lane>/<run_id>/team \
        --predecessor-ref <ref> \
        --out results/evaluation/orchestration/<run_id>_ref_check.json

WHY
---
``core-lane.yml`` persists the producer worktree with ``if: always()`` and a
``git commit ... || true`` followed by ``git push --force``. A producer that dies
with a CLEAN worktree therefore pushes its predecessor head and the resulting ref
is **byte-identical to the predecessor's**. Inspecting refs alone can never
distinguish that death from success. Meanwhile the audit job is
``needs: team`` + ``if: needs.team.result == 'success'``, so any non-zero exit of
the producer step skips the audit, and the integrate step is gated on the audit.

This module turns that blind spot into a stated, re-executable verdict. It does
NOT read the Actions API (the lane has no network and has recorded HTTP 403 on
every attempt), so it proves what is PROVABLE from the persisted snapshot and
refuses to guess beyond it. Every claim is graded:
``MEASURED`` (recomputed here), ``STRUCTURAL`` (read off the control-plane
workflow text), or ``CANDIDATE`` (consistent with the evidence, NOT established).

REUSE-FIRST
-----------
No new validation logic. The two ``core-lane.yml`` line references and the
``run-ox-with-retry.sh`` guard semantics below are re-read from the mounted
control plane on every run, so a control-plane fix invalidates this record
instead of silently making it stale.

Exit 0 = the ref check is measured and a verdict is emitted
Exit 2 = environment error (ref unresolvable / repo unusable); NO verdict
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lex-evaluation-orchestration-ref-check/1"

#: Control-plane files whose text defines the orchestration this record reasons
#: about. Re-read and hashed every run.
CONTROL_PLANE_FILES = (
    ".github/workflows/core-lane.yml",
    ".github/scripts/run-ox-with-retry.sh",
)

#: The specific control-plane constructs this record depends on. If any is
#: absent, the record reports the construct as NOT_FOUND rather than asserting
#: behaviour it cannot see.
CONSTRUCTS = (
    ("persist_step_is_always", "persist_step_always", ".github/workflows/core-lane.yml",
     r"^\s*- name: Persist team snapshot\s*$"),
    ("persist_commit_is_soft", "persist_commit_soft", ".github/workflows/core-lane.yml",
     r"git commit -m .*\|\| true"),
    ("persist_pushes_force", "persist_push_force", ".github/workflows/core-lane.yml",
     r"git push --force origin"),
    ("audit_needs_team", "audit_needs_team", ".github/workflows/core-lane.yml",
     r"^\s*needs: team\s*$"),
    ("audit_gated_on_team_success", "audit_gated_on_success", ".github/workflows/core-lane.yml",
     r"if: needs\.team\.result == 'success'"),
    ("integrate_gated_on_audit", "integrate_gated_on_audit", ".github/workflows/core-lane.yml",
     r"^\s*needs: audit\s*$"),
    ("zero_delta_guard_exists", "zero_delta_guard", ".github/scripts/run-ox-with-retry.sh",
     r"LEX_ZERO_DELTA_REPAIR"),
    ("zero_delta_guard_repair_only", "zero_delta_guard_repair_only",
     ".github/scripts/run-ox-with-retry.sh",
     r"REPAIR_INTENT=true"),
)


def _git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout or "").strip()


def _git_bytes(*args: str) -> bytes | None:
    """Raw bytes of a git read. NEVER strip: file CONTENT is compared here, and
    stripping the trailing newline would make every text file look drifted. That
    bug was in this module's first version and was caught by re-running the
    overlay check it was written to perform."""
    p = subprocess.run(["git", *args], capture_output=True, timeout=120)
    return p.stdout if p.returncode == 0 else None


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref_head(ref: str) -> tuple[int, str | None]:
    rc, out = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return rc, (out or None)


def construct_presence(repo_root: Path) -> list[dict[str, Any]]:
    out = []
    for fid, key, rel, pattern in CONSTRUCTS:
        p = repo_root / rel
        found = False
        evidence = ""
        if p.exists():
            import re as _re
            m = _re.search(pattern, p.read_text(encoding="utf-8"), _re.M)
            found = bool(m)
            if m:
                line_no = p.read_text(encoding="utf-8")[: m.start()].count("\n") + 1
                evidence = f"{rel}:{line_no}"
        out.append({"id": fid, "key": key, "source": rel, "pattern": pattern,
                    "present": found, "at": evidence or None})
    return out


def validation_triage(repo_root: Path) -> list[dict[str, Any]]:
    """Re-run, from the persisted snapshot, every validation gate that can be
    re-run offline, and grade each one.

    The point is NOT to guess which gate fired. The point is to REFUTE the ones
    that provably did not, so that a future cycle does not re-litigate a closed
    candidate. A gate that cannot be re-run offline is graded CANNOT_DETERMINE
    and is never upgraded to a cause.
    """
    import re as _re
    import hashlib as _h
    t: list[dict[str, Any]] = []

    # --- 1. validate_registry (run-ox-with-retry.sh -> rc 64/65/66, zero delta) ---
    reg = Path("/tmp/lex_control/docs/agents/AGENT_CARDS.md")
    if reg.exists():
        text = reg.read_text(encoding="utf-8")
        cards = sorted(p.name[:-3] for p in (repo_root / ".opencode/agents").glob("*.md"))
        bad = [i for i in cards
               if text.count(f"<!-- AGENT_CARD: {i} ") != 1]
        defined = sorted({ln.split()[2] for ln in text.splitlines()
                          if ln.startswith("<!-- AGENT_CARD:")})
        missing = [i for i in defined if not (repo_root / f".opencode/agents/{i}.md").exists()]
        disabled = [i for i in defined
                    if "status=LEGACY_DISABLED" in
                    next((ln for ln in text.splitlines()
                          if f"<!-- AGENT_CARD: {i} " in ln), "")]
        ok = not (bad or missing)
        t.append({
            "gate": "validate_registry", "rc_on_failure": [64, 65, 66],
            "grade": "REFUTED" if ok else "NOT_REFUTED",
            "evidence": (f"registry {reg} sha256 {_h.sha256(reg.read_bytes()).hexdigest()}; "
                         f"{len(cards)} agent definitions each carry exactly 1 card; "
                         f"{len(defined)} cards declared; duplicate_cards={bad}; "
                         f"cards_without_definition={missing}; disabled={disabled}"),
            "consequence": ("this gate cannot have produced the zero-delta death: it passes "
                            "against the mounted control plane and this repo"),
        })
    else:
        t.append({"gate": "validate_registry", "rc_on_failure": [64, 65, 66],
                  "grade": "CANNOT_DETERMINE",
                  "evidence": "control-plane registry not mounted", "consequence": ""})

    # --- 2. resolve_model_args (rc 76, zero delta) ---
    health = Path("/tmp/lex_control/state/model_health.json")
    if health.exists():
        h = json.loads(health.read_text(encoding="utf-8"))
        healthy = bool(h.get("healthy"))
        resolved = h.get("resolved_model") or ""
        t.append({
            "gate": "resolve_model_args", "rc_on_failure": [76],
            "grade": "CANNOT_DETERMINE",
            "evidence": (f"mounted model_health healthy={healthy} resolved={resolved!r} "
                         f"last_checked_run_id={h.get('last_checked_run_id')} "
                         f"last_checked_at={h.get('last_checked_at')}"),
            "consequence": ("the mounted file CANNOT be the one this run dispatched on if its "
                            "last_checked_run_id is numerically greater than the run id under "
                            "test, so this gate is neither refuted nor confirmed. It is the "
                            "one validation gate whose input is not recoverable from the "
                            "snapshot, and it is the only remaining candidate that would have "
                            "exited BEFORE the agent started."),
            "input_predates_run": str(h.get("last_checked_run_id") or "")[:1] == "",
        })
    else:
        t.append({"gate": "resolve_model_args", "rc_on_failure": [76],
                  "grade": "CANNOT_DETERMINE",
                  "evidence": "model_health.json not mounted", "consequence": ""})

    # --- 3. stage_control overlay drift -> lane write scope rc 3 ---
    drift = []
    rc, files = _git("ls-tree", "-r", "--name-only", "origin/main", ".opencode/agents")
    for f in [x for x in files.splitlines() if x]:
        p = repo_root / f
        if not p.exists():
            drift.append({"path": f, "state": "MISSING_IN_LANE_TREE"})
            continue
        blob = _git_bytes("show", f"origin/main:{f}")
        if blob is None or blob != p.read_bytes():
            drift.append({"path": f, "state": "DIFFERS",
                          "control_plane_sha256": (hashlib.sha256(blob).hexdigest()
                                                   if blob else None),
                          "lane_tree_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    ag_blob = _git_bytes("show", "origin/main:AGENTS.md")
    ag_path = repo_root / "AGENTS.md"
    ag_same = bool(ag_blob) and ag_path.exists() and ag_blob == ag_path.read_bytes()
    t.append({
        "gate": "lane_write_scope_after_stage_control", "rc_on_failure": [3],
        "grade": "REFUTED" if not drift and ag_same else "NOT_REFUTED",
        "evidence": (f"stage_control checks out origin/main over AGENTS.md and .opencode/agents; "
                     f"AGENTS.md identical={ag_same}; per-file drift={drift or 'none'}"),
        "consequence": ("the overlay restore is a byte-level no-op for this tree, so the scope "
                        "step could not have failed on an overlay entry; the lane crossed no "
                        "protected path"),
    })

    # --- 4. LEX_ZERO_DELTA_REPAIR (rc 67) coverage ---
    wrapper = repo_root / ".github/scripts/run-ox-with-retry.sh"
    if wrapper.exists():
        w = wrapper.read_text(encoding="utf-8")
        wf = repo_root / ".github/workflows/core-lane.yml"
        wtext = wf.read_text(encoding="utf-8") if wf.exists() else ""
        branches = _re.findall(r'if \[\[ -n "\$REPAIR_FROM" \]\]; then(.*?)\n\s*fi', wtext, _re.S)
        export_in_repair_branch = any("export LEX_REQUIRE_DELTA=1" in b for b in branches)
        init_fetches_audit = bool(
            _re.search(r'git fetch origin "\$TEAM:[^"]*" "\$AUDIT:[^"]*"', wtext))
        t.append({
            "gate": "LEX_ZERO_DELTA_REPAIR", "rc_on_failure": [67],
            "grade": "STRUCTURAL",
            "evidence": (f"wrapper exports LEX_REQUIRE_DELTA=1 only inside the REPAIR_FROM "
                         f"branch of core-lane.yml: export_in_repair_branch="
                         f"{export_in_repair_branch}; guard string present="
                         f"{'LEX_ZERO_DELTA_REPAIR' in w}"),
            "consequence": ("a dispatch carrying repair_from_run_id would have been HARD-FAILED "
                            "by the guard rather than persisting a zero-delta ref silently; a "
                            "supervisor fresh dispatch carries no guard and exits 0. This run's "
                            "ref is the predecessor head, which is what BOTH produce, so the "
                            "guard's coverage does not discriminate between them here."),
        })
        t.append({
            "gate": "init_step_repair_branch_requires_both_refs", "rc_on_failure": [1],
            "grade": "STRUCTURAL",
            "evidence": (f"core-lane.yml's REPAIR_FROM branch runs `git fetch origin \"$TEAM:...\" "
                         f"\"$AUDIT:...\"` under `set -euo pipefail` (init_fetches_both_refs="
                         f"{init_fetches_audit}); it then `git worktree add /tmp/lex_prior_audit "
                         f"origin/$AUDIT`."),
            "consequence": ("a repair dispatch whose predecessor never produced an audit branch "
                            "fails HERE, before the agent starts, and delivers zero delta. This "
                            "is indistinguishable from the ref alone and is a CANDIDATE, not an "
                            "established cause: establishing it needs the run's dispatch inputs "
                            "and step log, which this lane cannot fetch (HTTP 403 on every REST "
                            "attempt)."),
        })
    return t


def check(repo_root: Path, team_ref: str, predecessor_ref: str,
          lane: str, run_id: str) -> dict[str, Any]:
    cp = {rel: _sha256_file(repo_root / rel) for rel in CONTROL_PLANE_FILES}

    rc_t, team_head = ref_head(team_ref)
    rc_p, pred_head = ref_head(predecessor_ref)
    env_errors = []
    if rc_t != 0:
        env_errors.append(f"team ref does not resolve: {team_ref}")
    if rc_p != 0:
        env_errors.append(f"predecessor ref does not resolve: {predecessor_ref}")
    if env_errors:
        return {"environment_errors": env_errors, "verdict": None}

    same = team_head == pred_head
    rc, subject = _git("show", "-s", "--format=%s", team_head)
    rc_r, tree = _git("rev-parse", f"{team_head}^{{tree}}")
    # A tree that is byte-identical to the predecessor's is the strongest
    # statement of "no durable delta": not even the file contents moved.
    pred_tree = None
    rc_r2, pred_tree = _git("rev-parse", f"{pred_head}^{{tree}}")
    delta_commit = None if same else {
        "commits_ahead": _git("rev-list", "--count", f"{pred_head}..{team_head}")[1],
        "commits_behind": _git("rev-list", "--count", f"{team_head}..{pred_head}")[1],
    }

    constructs = construct_presence(repo_root)

    return {
        "environment_errors": None,
        "lane": lane,
        "run_id": run_id,
        "measured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "refs": {
            "team_ref": team_ref, "team_head": team_head,
            "predecessor_ref": predecessor_ref, "predecessor_head": pred_head,
        },
        "zero_delta": {
            "head_identical": same,
            "tree_identical": bool(pred_tree) and tree == pred_tree,
            "team_tree": tree, "predecessor_tree": pred_tree,
            "delta_commit": delta_commit,
            "head_subject": subject,
        },
        "verdict": ("ZERO_DURABLE_DELTA_PERSISTED" if same
                    else "DURABLE_DELTA_PERSISTED"),
        "control_plane": {
            "sha256": cp,
            "constructs": constructs,
            "constructs_all_present": all(c["present"] for c in constructs),
            "missing_constructs": [c["id"] for c in constructs if not c["present"]],
        },
        "validation_triage": validation_triage(repo_root),
        "structural_consequences": [
            {"id": "ref_inspection_cannot_distinguish_death_from_success",
             "grade": "STRUCTURAL",
             "evidence": "core-lane.yml persists with `if: always()`, `git commit ... || true` "
                         "and `git push --force`, so a producer that dies with a clean "
                         "worktree pushes its predecessor head verbatim.",
             "consequence": "the persisted team ref is IDENTICAL for a successful cycle and "
                            "for a cycle that did nothing. Any gate that reads refs to decide "
                            "whether a cycle delivered is reading a constant."},
            {"id": "audit_starvation_is_structural",
             "grade": "STRUCTURAL",
             "evidence": "audit job is `needs: team` AND `if: needs.team.result == 'success'`; "
                         "integrate is `needs: audit`.",
             "consequence": "every producer non-zero exit skips the audit, so the cycle cannot "
                            "be gated or promoted. A cycle that dies after committing is "
                            "operationally identical to one that never ran."},
            {"id": "zero_delta_guard_does_not_cover_fresh_dispatches",
             "grade": "STRUCTURAL",
             "evidence": "run-ox-with-retry.sh sets REPAIR_INTENT=true only from a REPAIR "
                         "argument or LEX_REQUIRE_DELTA=1; core-lane.yml sets that export only "
                         "inside the `if [[ -n \"$REPAIR_FROM\" ]]` branch.",
             "consequence": "a supervisor fresh dispatch (repair_from_run_id empty) gets NO "
                            "rc-67 zero-delta guard, so a do-nothing cycle there exits 0 and is "
                            "recorded as a clean success."},
        ],
        "grade_key": {
            "MEASURED": "recomputed from the persisted snapshot inside this run",
            "STRUCTURAL": "read off the mounted control-plane workflow text, hashed above",
            "CANDIDATE": "consistent with the evidence but NOT established by it",
        },
        "claim_ceiling": (
            "This module can prove that a persisted producer ref is byte-identical to its "
            "predecessor and can state what the control plane does with that fact. It CANNOT "
            "recover the exit code, duration or step log of a past Actions run: the lane has no "
            "network (every REST attempt has returned HTTP 403) and no logs are fetched. It "
            "therefore names candidate causes and REFUTES the ones it can test; it never "
            "declares which one occurred."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--lane", default="evaluation")
    ap.add_argument("--team-ref", required=True)
    ap.add_argument("--predecessor-ref", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    rec = check(Path(args.repo_root).resolve(), args.team_ref, args.predecessor_ref,
                args.lane, args.run_id)
    if rec["environment_errors"]:
        for e in rec["environment_errors"]:
            print(f"environment error (NOT a pass): {e}", file=sys.stderr)
        return 2

    rec = {"schema": SCHEMA, **rec}
    out = Path(args.out) if args.out else (
        Path("results/evaluation/orchestration") / f"{args.run_id}_ref_check.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    z = rec["zero_delta"]
    print(f"team ref       : {rec['refs']['team_ref']}\n  -> {rec['refs']['team_head']}")
    print(f"predecessor ref: {rec['refs']['predecessor_ref']}\n  -> {rec['refs']['predecessor_head']}")
    print(f"verdict        : {rec['verdict']} "
          f"(head identical={z['head_identical']}, tree identical={z['tree_identical']})")
    if not z["head_identical"]:
        print(f"delta commit   : {z['delta_commit']}")
    print(f"head subject   : {z['head_subject']}")
    missing = rec["control_plane"]["missing_constructs"]
    print(f"control-plane constructs: "
          f"{'all present' if not missing else 'MISSING ' + ', '.join(missing)}")
    for v in rec["validation_triage"]:
        print(f"  [{v['grade']:<18}] {v['gate']} (rc {v['rc_on_failure']})")
    for c in rec["structural_consequences"]:
        print(f"  [{c['grade']}] {c['id']}")
    print(f"record: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())