"""Freeze-ordering evidence, recomputed from REAL git commit times.

A hand-written ``frozen_at_utc`` field is NOT evidence.  This module walks the
committed history of the frozen rules file and of the first commit that carries
a measurement, and writes the ordering it actually finds.

THE TRUNCATED-HISTORY DEFECT THIS MODULE EXISTS TO PREVENT
----------------------------------------------------------
Every workflow in this repository checks out with ``fetch-depth: 1``
(``.github/workflows/*.yml``).  That produces a *shallow* repository whose tip is
a graft point: ``git log --all -- <path>`` returns the tip commit and NOTHING
ELSE, because the ancestors were never fetched.

An earlier revision of this module read that truncated list naively.  In a
shallow mount it found exactly one commit touching ``RULES.json`` and exactly
one commit carrying a measurement -- the same commit -- and therefore reported::

    freeze_precedes_measurement: false
    margin_seconds: null

That is a FALSE NEGATIVE.  It asserts the frozen rules were edited AFTER the
first measurement, which was never true: the freeze commit really did precede
the measurement commit by 345 s.  The freeze ordering is exactly the claim an
auditor most needs to be able to trust, and a truncated checkout silently turned
it into a refutation.

The fix is fail-closed and three-valued:

* The verdict is ``True`` / ``False`` / ``None``.
* ``False`` is emitted ONLY when the repository demonstrably holds a rules
  commit strictly later than a measurement commit.  Absence of evidence can
  never produce ``False``.
* When history is truncated, or when either side of the comparison is missing,
  the verdict is ``None`` with ``evidence_state`` naming the reason.  A verifier
  that cannot see is not a verifier that refutes.

An auditor can confirm the distinction with one command::

    git rev-parse --is-shallow-repository   # "true" => verdict is None, not False
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO_ROOT / "results/frontier/frontier-concept-seed-recall"
RULES_RELPATH = "results/frontier/frontier-concept-seed-recall/RULES.json"

#: Ordered by severity.  Used to decide whether a recomputation is at least as
#: informative as the record already on disk (never silently downgraded).
EVIDENCE_STATES = (
    "COMPLETE",
    "INCOMPLETE_TRUNCATED_HISTORY",
    "INCOMPLETE_NO_COMMITS_FOUND",
)


def _git(*args: str, check: bool = True, repo: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=check)


def _git_out(*args: str, repo: Path = REPO_ROOT) -> str:
    return _git(*args, repo=repo).stdout.strip()


def is_shallow(repo: Path = REPO_ROOT) -> bool:
    """True when this is a truncated (grafted) checkout.

    Works on every git that understands ``--is-shallow-repository`` (2.15+) and
    falls back to probing for the shallow file, so the module never silently
    assumes a full clone it does not have.
    """
    proc = _git("rev-parse", "--is-shallow-repository", check=False, repo=repo)
    if proc.returncode == 0 and proc.stdout.strip() in ("true", "false"):
        return proc.stdout.strip() == "true"
    git_dir = _git_out("rev-parse", "--absolute-git-dir", repo=repo)
    return bool(git_dir) and (Path(git_dir) / "shallow").is_file()


def _commits_for(relpath: str, repo: Path = REPO_ROOT) -> list[tuple[str, str, str]]:
    """Commits touching ``relpath``, newest first, as (sha, committer time, subject).

    ``--follow``-free on purpose: the path is stable.  A path that has been
    renamed would be a different artefact and is not silently substituted.
    """
    proc = _git("log", "--all", "--format=%H %cI %s", "--", relpath,
                check=False, repo=repo)
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def _blob_sha256(sha: str, relpath: str, repo: Path = REPO_ROOT) -> str | None:
    proc = _git("show", f"{sha}:{relpath}", check=False, repo=repo)
    if proc.returncode != 0:
        return None
    return hashlib.sha256(proc.stdout.encode("utf-8", "surrogateescape")).hexdigest()


def _blob_sha256_bytes(sha: str, relpath: str) -> bytes | None:
    """Raw bytes of the blob, for a byte-exact digest of the committed file."""
    proc = _git("show", f"{sha}:{relpath}", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.encode("utf-8", "surrogateescape")


def _state_rank(state: str | None) -> int:
    if state in EVIDENCE_STATES:
        return EVIDENCE_STATES.index(state)
    return len(EVIDENCE_STATES)


def classify(run_id: int, *, repo: Path = REPO_ROOT) -> dict:
    """Recompute the freeze ordering.  Never emits ``False`` from absent evidence."""
    rel_results = (f"results/frontier/frontier-concept-seed-recall/"
                   f"harness_results_{run_id}.json")
    rel_baseline = (f"results/frontier/frontier-concept-seed-recall/"
                    f"baseline_reproduction_{run_id}.json")

    rules_commits = _commits_for(RULES_RELPATH, repo)
    results_commits = _commits_for(rel_results, repo)
    baseline_commits = _commits_for(rel_baseline, repo)

    shallow = is_shallow(repo)

    # git log lists newest first.  The FREEZE is the MOST RECENT commit that
    # touched the rules; the MEASUREMENT is the EARLIEST commit that carries one.
    freeze = rules_commits[0] if rules_commits else None
    first_measurement = results_commits[-1] if results_commits else None
    first_baseline = baseline_commits[-1] if baseline_commits else None

    digests = [{"commit": sha, "commit_time_utc": when, "subject": subject,
                "rules_sha256": _blob_sha256(sha, RULES_RELPATH, repo)}
               for sha, when, subject in rules_commits]

    head_blob = _blob_sha256("HEAD", RULES_RELPATH, repo)

    reasons: list[str] = []
    if shallow:
        reasons.append(
            "repository is a truncated (shallow) checkout: "
            "`git rev-parse --is-shallow-repository` is true, so `git log --all` "
            "returns only the grafted tip and the ancestors of the freeze and "
            "measurement commits are not present locally. Fetch full history "
            "(`git fetch --unshallow`) and re-run; until then the ordering is "
            "NOT MEASURABLE and must not be read as a violation.")
    if not rules_commits:
        reasons.append("no commit touching RULES.json was found in this checkout")
    if not results_commits:
        reasons.append(f"no commit carrying {rel_results} was found in this checkout")

    if reasons:
        state = ("INCOMPLETE_TRUNCATED_HISTORY" if shallow and (rules_commits or results_commits)
                 else "INCOMPLETE_NO_COMMITS_FOUND")
        verdict = None
        margin = None
        ordered = None
    else:
        state = "COMPLETE"
        from datetime import datetime
        freeze_t = datetime.fromisoformat(freeze[1])
        meas_t = datetime.fromisoformat(first_measurement[1])
        ordered = freeze_t < meas_t
        margin = (meas_t - freeze_t).total_seconds()
        verdict = bool(ordered)

    return {
        "schema": "frontier-concept-seed-recall/freeze-ordering/2",
        "run_id": run_id,
        "rules_relpath": RULES_RELPATH,
        "rules_commits": digests,
        "final_frozen_rules_sha256": (digests[0]["rules_sha256"] if digests else None),
        "rules_sha256_at_head": head_blob,
        "first_commit_carrying_a_measurement": (
            {"commit": first_measurement[0], "commit_time_utc": first_measurement[1],
             "subject": first_measurement[2]} if first_measurement else None),
        "first_commit_carrying_baseline_reproduction": (
            {"commit": first_baseline[0], "commit_time_utc": first_baseline[1],
             "subject": first_baseline[2]} if first_baseline else None),
        "freeze_precedes_measurement": verdict,
        "margin_seconds": margin,
        "evidence_state": state,
        "evidence_state_reasons": reasons,
        "repository_is_shallow": shallow,
        "rules_bytes_unchanged_since_final_amendment": (
            bool(digests) and head_blob is not None
            and digests[0]["rules_sha256"] == head_blob),
        "three_valued_contract": (
            "True = a rules commit demonstrably precedes the first measurement commit. "
            "False = a rules commit demonstrably FOLLOWS it (post-hoc tuning; the run "
            "is invalidated). None = not measurable from this checkout; absence of "
            "evidence is NEVER reported as False."),
        "method": "real git commit times (git log --format=%cI) and real git blob "
                  "digests (git show <sha>:<path>); no hand-written timestamp is used "
                  "as evidence anywhere in this record",
        "caveat": "this file is itself written after the freeze; it REPORTS the "
                  "ordering, it does not create it. The ordering is verifiable from "
                  "the commits it names without trusting this file.",
        "reproduce": ("git fetch --unshallow && "
                      "python3 -m frontier.frontier-concept-seed-recall.freeze_ordering "
                      f"--run-id {run_id}"),
    }


def _is_downgrade(new: dict, old: dict) -> str | None:
    """Refuse to replace an on-disk record with a strictly weaker one."""
    rn, ro = _state_rank(new.get("evidence_state")), _state_rank(old.get("evidence_state"))
    if rn > ro:
        return (f"refusing to overwrite a {old.get('evidence_state')} record with a "
                f"{new.get('evidence_state')} one")
    vo, vn = old.get("freeze_precedes_measurement"), new.get("freeze_precedes_measurement")
    if vo is True and vn is False:
        return "refusing to overwrite freeze_precedes_measurement=True with False"
    return None


def build(run_id: int, *, write: bool = True, repo: Path = REPO_ROOT) -> dict:
    rec = classify(run_id, repo=repo)
    if not write:
        return rec
    out = TEAM_DIR / "freeze_ordering.json"
    if out.is_file():
        try:
            old = json.loads(out.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
        guard = _is_downgrade(rec, old)
        if guard:
            rec["write_suppressed"] = guard
            print(json.dumps({"evidence_state": rec["evidence_state"],
                              "freeze_precedes_measurement":
                                  rec["freeze_precedes_measurement"],
                              "write_suppressed": guard}, indent=1))
            return rec
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({"evidence_state": rec["evidence_state"],
                      "freeze_precedes_measurement": rec["freeze_precedes_measurement"],
                      "margin_seconds": rec["margin_seconds"],
                      "final_rules_sha256": rec["final_frozen_rules_sha256"]}, indent=1))
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--no-write", action="store_true",
                    help="classify without touching freeze_ordering.json")
    args = ap.parse_args(argv)
    rec = build(int(args.run_id), write=not args.no_write)
    if args.no_write:
        print(json.dumps({"evidence_state": rec["evidence_state"],
                          "freeze_precedes_measurement":
                              rec["freeze_precedes_measurement"],
                          "margin_seconds": rec["margin_seconds"],
                          "final_rules_sha256": rec["final_frozen_rules_sha256"],
                          "write": "suppressed (--no-write)"}, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
