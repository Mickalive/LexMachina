"""Test accounting: an honest, COMMIT-ANCHORED count of tests and deltas.

Why this tool exists
--------------------
Two ordered defects in factory direction v56 that are the same defect at heart.

**RF2** (arithmetic): a report claimed net new passing tests of "+7" when the
measured change was "+10" (base 564 -> head 574). A delta that disagrees with the
two numbers it is derived from is a fabricated number.

**RF4** (the pin): that same report's supporting count was pinned to a
*re-probed moving snapshot* rather than to a named run and commit. The audit of
run 39073545280 found the pin (21:30:00Z) already stale against the control
plane's 22:24:12Z snapshot, recomputed 162 passed / 1 failed, and thereby falsified
the report's "163 passed / 13 passed (fixed)" claim. The direction's rule:

    "Pin against a NAMED run id and commit, never against a re-probed moving
     snapshot, and if a pin cannot be made correct say so rather than repinning
     twice."

A timestamp is not a pin. It names an instant, not a tree: the same command
re-run a minute later legitimately produces a different count, so the pin cannot
be checked and quietly rots. A commit sha is a pin: it names the exact tree, so
the measurement is reproducible or it is wrong.

So this tool refuses to record a pin it cannot anchor to a commit, and it derives
every delta from the two measured counts rather than from a hand-written number.

Use
---
    python3 -m product.test_accounting \
        --baseline-run-id <id> --baseline-file <pytest output> \
        --head-run-id <id> --head-file <pytest output> \
        --out results/product/regression/test_accounting.json

Both files are raw ``pytest -q`` outputs. The tool parses the summary line, and it
refuses to invent a delta it cannot compute.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent

SCHEMA = "product-test-accounting/1"

#: ``45 failed, 562 passed, 2 skipped, 30 errors in 82.92s (0:01:22)``
_SUMMARY = re.compile(
    r"(?:(?P<failed>\d+)\s+failed)?,?\s*"
    r"(?:(?P<passed>\d+)\s+passed)?"
    r"(?:,\s*(?P<skipped>\d+)\s+skipped)?"
    r"(?:,\s*(?P<errors>\d+)\s+errors)?"
    r"(?:\s+in\s+(?P<seconds>[\d.]+)s)?"
)

_COUNT_KEYS = ("failed", "passed", "skipped", "errors")


def parse_pytest_summary(text: str) -> dict:
    """Parse the terminal summary line of a ``pytest -q`` run.

    Raises rather than guessing: an unparseable log means the measurement cannot
    be trusted, and a tool that silently returns zeros here is exactly how "+7"
    became a fabricated delta in the first place.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise SystemExit("empty pytest log: nothing to measure")
    tail = lines[-1]
    for line in reversed(lines[-12:]):
        if "passed" in line or "failed" in line or "error" in line:
            tail = line
            break
    m = _SUMMARY.search(tail)
    if not m or not any(m.group(k) for k in _COUNT_KEYS):
        raise SystemExit(
            f"could not parse a pytest summary from the log tail:\n  {tail!r}\n"
            "refusing to record a delta that cannot be computed"
        )
    out = {k: int(m.group(k) or 0) for k in _COUNT_KEYS}
    out["seconds"] = float(m.group("seconds") or 0.0)
    out["total_collected"] = sum(out[k] for k in _COUNT_KEYS)
    return out


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def head_commit() -> str:
    sha = _git("rev-parse", "HEAD")
    if not sha:
        raise SystemExit("cannot resolve HEAD: a pin must name a commit")
    return sha


def _require_anchor(run_id: str, commit: str, label: str) -> dict:
    """A pin is only valid if it names a run id AND a commit. Never a timestamp."""
    if not run_id or run_id.lower() in {"local", "none", "unknown", "now"}:
        raise SystemExit(
            f"{label} pin has no NAMED run id ({run_id!r}). A moving snapshot is not "
            "a pin: name the run the measurement belongs to."
        )
    if not commit or len(commit) < 7 or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise SystemExit(
            f"{label} pin has no resolvable commit ({commit!r}). Pin against a commit "
            "sha so the measurement is reproducible or it is wrong (RF4)."
        )
    return {"run_id": str(run_id), "commit": commit}


def build(baseline: dict, head: dict, delta: dict, ignore_list: list[str], env: dict) -> dict:
    return {
        "schema": SCHEMA,
        "what_this_is": (
            "Commit-anchored test accounting. Replaces both the hand-written delta "
            "(RF2: '+7' published where the measured change was '+10') and the "
            "timestamp pin (RF4: a 21:30:00Z snapshot was already stale against a "
            "22:24:12Z re-probe). Every delta below is computed from the two measured "
            "counts, never written by hand."
        ),
        "pinning_rule": (
            "A pin names a run id and a commit sha. It is never a timestamp and never a "
            "re-probed moving snapshot, because a timestamp names an instant rather than "
            "a tree: the same command re-run later legitimately differs, so the pin cannot "
            "be checked and rots silently. If a pin cannot be made correct, this tool "
            "exits non-zero instead of repinning."
        ),
        "collection_scope": {
            "command_shape": "python3 -m pytest tests/ -q --ignore=<module> ...",
            "cwd": "product",
            "uncollectable_modules_excluded": ignore_list,
            "n_uncollectable_modules": len(ignore_list),
            "why_excluded": (
                "These modules import sentence_transformers/torch, which is not installed "
                "in the CI or bare image. They are excluded identically at baseline and at "
                "head, so the comparison is a set relation over the same population. "
                "Excluding a DIFFERENT set at baseline and head would invalidate the delta."
            ),
        },
        "numeric_environment": {
            **env,
            "warning": (
                "Recorded because a from-source rebuild is environment-scoped, not "
                "byte-identical across machines (BLAS reduction order). A count that "
                "differs run-to-run on the SAME commit is an environment signal, not "
                "evidence of a code change - re-measure before publishing a delta."
            ),
        },
        "baseline": baseline,
        "head": head,
        "delta": delta,
        "claim_ceiling": [
            "This is a local measurement at the two named commits, on this machine. It "
            "is not a universal claim about the test suite.",
            "A passing count does not license a claim that the product works; it only "
            "bounds the code change between two commits.",
            "The excluded modules are still unexecuted. Their RF3 tracked-results writer "
            "defect is recorded separately in "
            "results/product/regression/tracked_results_writer_inventory.json.",
        ],
    }


def _collected(counts: dict) -> int:
    """Total collected, derived here rather than assumed present on the input.

    ``parse_pytest_summary`` supplies it, but ``compute_delta`` must not depend on
    a caller having pre-populated it - a delta that needs an optional key to be
    derived is a delta that can be skipped.
    """
    if "total_collected" in counts:
        return int(counts["total_collected"])
    return sum(int(counts.get(k, 0)) for k in _COUNT_KEYS)


def compute_delta(baseline: dict, head: dict) -> dict:
    """Every delta derived, never asserted."""
    per = {k: int(head.get(k, 0)) - int(baseline.get(k, 0)) for k in _COUNT_KEYS}
    return {
        "per_outcome": per,
        "net_new_passing_tests": per["passed"],
        "net_new_failing_tests": per["failed"],
        "net_new_errors": per["errors"],
        "net_change_in_collected": _collected(head) - _collected(baseline),
        "derived_not_asserted": (
            "net_new_passing_tests is head.passed - baseline.passed, computed here. "
            "It is never written into a report by hand; RF2's '+7' defect was a "
            "hand-written delta that disagreed with the two counts it came from."
        ),
    }


def _is_ancestor(base: str, head: str) -> bool:
    out = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    return out.returncode == 0


def _numeric_environment() -> dict:
    import platform

    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover - optional in a bare image
            env[mod] = None
    return env


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="product.test_accounting")
    ap.add_argument("--baseline-run-id", required=True)
    ap.add_argument("--baseline-commit", required=True,
                    help="commit the baseline measurement was taken at (an ancestor of head)")
    # Not argparse-required: both measurement flags are validated by the tool's own
    # precondition check so the refusal names the missing MEASUREMENT rather than
    # emitting a usage string with an exit code.
    ap.add_argument("--baseline-file", default=None,
                    help="raw pytest -q output at baseline")
    ap.add_argument("--head-run-id", default=None)
    ap.add_argument("--head-commit", default=None,
                    help="commit the head measurement was taken at; defaults to HEAD")
    ap.add_argument("--head-file", default=None, help="raw pytest -q output at head")
    ap.add_argument("--ignore-file", default=None,
                    help="file listing the excluded modules, one per line")
    ap.add_argument("--out", default="results/product/regression/test_accounting.json")
    args = ap.parse_args(argv)

    # Checked FIRST: a delta needs both measured counts. If either measurement is
    # missing there is no delta to report at all, so this precondition is tested
    # before any pin validation - otherwise a caller with a missing --head-file
    # gets a confusing pin error instead of the real problem.
    if not args.head_file:
        raise SystemExit(
            "--head-file is required: a delta needs both measured counts, and this "
            "tool will not report a delta it cannot compute (RF2)"
        )
    if not args.baseline_file:
        raise SystemExit("--baseline-file is required for the same reason (RF2)")

    base_pin = _require_anchor(args.baseline_run_id, args.baseline_commit, "baseline")
    head_pin = _require_anchor(args.head_run_id or "HEAD",
                               args.head_commit or head_commit(), "head")
    if base_pin["commit"] == head_pin["commit"]:
        raise SystemExit(
            "baseline and head pin to the SAME commit "
            f"({base_pin['commit'][:12]}); a delta between one tree is always 0 and "
            "publishing it would be a fabricated measurement"
        )
    # The two commits must be related, or the delta compares unrelated trees.
    if not _is_ancestor(base_pin["commit"], head_pin["commit"]):
        raise SystemExit(
            f"baseline commit {base_pin['commit'][:12]} is not an ancestor of head "
            f"{head_pin['commit'][:12]}; a delta between unrelated trees is meaningless "
            "(RF4: pin to a real base of the head, not to whatever was lying around)"
        )

    baseline = parse_pytest_summary(Path(args.baseline_file).read_text(encoding="utf-8"))
    head = parse_pytest_summary(Path(args.head_file).read_text(encoding="utf-8"))
    delta = compute_delta(baseline, head)

    ignore_list: list[str] = []
    if args.ignore_file:
        ignore_list = [
            ln.strip() for ln in Path(args.ignore_file).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

    artifact = build(
        {**base_pin, **baseline},
        {**head_pin, **head},
        delta,
        ignore_list,
        _numeric_environment(),
    )
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out.relative_to(REPO_ROOT)), "delta": delta}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())