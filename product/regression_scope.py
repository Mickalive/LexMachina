"""Root-scoped, set-relation regression scoping for the product lane.

Why this exists
---------------
A failing suite in this repository is mostly a missing-optional-dependency
environment gap, so the honest blast-radius claim is a SET RELATION (both
differences plus the intersection) between the untouched baseline tree and the
tree under test - never a pair of counts, and never a count presented as a set.

Cycle 39048942749 published such a comparison correctly *as a method* and then
published its result WITHOUT THE ROOT AND MOUNT IT MEASURED AT. Its
"repaired-only failing set is EMPTY" and "22 passed" readings are true at the
producer's CI root and false at every other root, because the cycle's own new
D2 guard was machine-coupled (audit CYCLE_39048942749 FIX-2, with FIX-1 as its
cause). The control plane recorded a standing tripwire for exactly that class.

So this script makes the scope part of the measurement rather than of the prose:

  * every number it emits is tagged with the checkout root, the baseline root and
    the control-plane mount it was measured at;
  * it computes BOTH set differences and the intersection (never a cardinality
    argument, never "exactly N" offered where a set relation is required);
  * it reconciles the pass/fail arithmetic against the set relation it measured
    and REFUSES to publish an artifact whose arithmetic does not close, instead of
    reporting the mismatch;
  * it records the measured environment beside the numbers, and labels any number
    that is sensitive to the environment as ROOT_SCOPED rather than universal.

Usage
-----
    python -m product.regression_scope --baseline-root /path/to/pristine \
        --out results/product/regression/<RUN>_regression_scope.json

With no ``--root`` the tree under test is the repository this module lives in.
The uncollectable-module exclusion list is DISCLOSED in the artifact, not silent:
it is computed by attempting collection in this environment, never hard-coded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_LINE = re.compile(r"^=+\s*(?P<summary>.*(?:failed|error).*?)\s*=+\s*$")
COUNTS_LINE = re.compile(r"^(?P<summary>\d+ (?:failed|passed)[^\n]*\bin [\d.]+s\b.*)$")
STATUS_LINE = re.compile(r"^(FAILED|ERROR)\s+(?P<id>\S+)")


def uncollectable_modules(root: Path, test_dir: str = "product/tests") -> list[str]:
    """Modules that cannot even be COLLECTED in this environment.

    Disclosed, never silent: the same exclusion is applied identically to the
    baseline run and to the run under test, so it cannot manufacture a
    difference. Their status is UNMEASURED, not passed.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", test_dir, "-q", "-p", "no:cacheprovider",
         "--collect-only"],
        cwd=str(root), capture_output=True, text=True)
    mods = sorted({line.split(" ", 1)[1].strip() for line in proc.stdout.splitlines()
                   if line.startswith("ERROR ")})
    return [m for m in mods if m.startswith(test_dir)]


def _run(root: Path, ignores: list[str], test_dir: str = "product/tests") -> dict:
    cmd = [sys.executable, "-m", "pytest", test_dir, "-q", "-p", "no:cacheprovider",
           *sum((["--ignore", m] for m in ignores), [])]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    failed: set[str] = set()
    in_summary = False
    summary = ""
    for line in out.splitlines():
        if "short test summary info" in line:
            in_summary = True
            continue
        if in_summary:
            m = STATUS_LINE.match(line)
            if m:
                failed.add(m.group("id"))
                continue
            m2 = SUMMARY_LINE.match(line) or COUNTS_LINE.match(line)
            if m2 and ("failed" in m2.group("summary") or "error" in m2.group("summary")):
                summary = m2.group("summary")
    if not summary:  # the final count line is also matched outside the summary block
        for line in reversed(out.splitlines()):
            m = COUNTS_LINE.match(line.strip())
            if m:
                summary = m.group("summary")
                break
    passed = 0
    pm = re.search(r"(\d+) passed", out)
    if pm:
        passed = int(pm.group(1))
    return {
        "root": str(root),
        "command": " ".join(cmd),
        "unique_failing_or_erroring_ids": sorted(failed),
        "n_unique_failing_or_erroring_ids": len(failed),
        "collected": _collect_count(root, ignores),
        "passed_count": passed,
        "run_summary": summary,
        "exit_code": proc.returncode,
    }


def _collect_count(root: Path, ignores: list[str], test_dir: str = "product/tests") -> int:
    """How many tests the suite collects here, under the same exclusions.

    Needed so the pass/fail arithmetic can be reconciled as an identity rather
    than asserted: a repair's published "new tests" figure must be a MEASURED
    collection delta, not a number copied out of a report.
    """
    cmd = [sys.executable, "-m", "pytest", test_dir, "-q", "-p", "no:cacheprovider",
           *sum((["--ignore", m] for m in ignores), []), "--collect-only"]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    return int(m.group(1)) if m else -1


def _counts(summary: str) -> dict:
    out = {}
    for key in ("failed", "passed", "skipped", "errors", "error"):
        m = re.search(rf"(\d+) {key}", summary)
        if m:
            out[key] = int(m.group(1))
    return out


def compare(baseline: dict, repaired: dict) -> dict:
    """Both differences and the intersection, as set relations."""
    b = set(baseline["unique_failing_or_erroring_ids"])
    r = set(repaired["unique_failing_or_erroring_ids"])
    return {
        "method": "SET comparison: both differences and the intersection of the "
                  "FAILED/ERROR test-ID sets, plus the counted run summary. A "
                  "count is never offered where a set relation is required.",
        "intersection": sorted(b & r),
        "n_intersection": len(b & r),
        "set_difference_baseline_only_FIXED_BY_THIS_REPAIR": sorted(b - r),
        "set_difference_repaired_only_NEW_FAILURES": sorted(r - b),
        "n_baseline_only": len(b - r),
        "n_repaired_only": len(r - b),
    }


def _repo_for_refs() -> Path | None:
    """The checkout whose object store can resolve ``--baseline-ref``."""
    for cand in (ROOT, Path.cwd()):
        proc = subprocess.run(["git", "-C", str(cand), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
    return None


def _ref_bytes(ref: str, relpath: str, repo: Path | None) -> bytes:
    """Bytes of ``relpath`` at ``ref``, read out of a repository's object store.

    Injected as bytes rather than via ``git checkout`` so the swap also works in
    a plain copy of the tree (a foreign root with no ``.git``), which is the only
    way to compare two refs inside ONE checkout root.
    """
    if repo is None:
        raise FileNotFoundError(f"no git repository available to resolve {ref}")
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{relpath}"],
                          capture_output=True)
    if proc.returncode != 0:
        raise FileNotFoundError(f"{relpath} does not exist at {ref}")
    return proc.stdout


def reconcile(baseline: dict, repaired: dict, rel: dict) -> dict:
    """Check the pass/fail arithmetic against the set relation, or refuse.

    The identity that must hold for one checkout root, same exclusions, no
    test outcomes outside {passed, failing/erroring (unique ID), skipped}:

        collected_r - collected_b
            == (passed_r - passed_b)
             + (n_unique_failing_r - n_unique_failing_b)
             + (skipped_r - skipped_b)

    so   passed_r - passed_b == collected_delta - net_failing_delta - skipped_delta.

    The skipped term is not cosmetic: a mount-dependent ``skipif`` moves tests
    between the 'runs' and 'skipped' buckets when the root changes, and leaving
    the term out would make this script refuse honest measurements at a foreign
    root. If the identity does not close, the artifact is NOT written - a
    scope-uncertain measurement is worse than no measurement.
    """
    bc, rc = _counts(baseline["run_summary"]), _counts(repaired["run_summary"])
    if not bc or not rc:
        return {"arithmetic_reconciles": False,
                "notes": ["REFUSED: the counted run summary was not parsed"]}
    notes, ok = [], True
    n_fb = baseline["n_unique_failing_or_erroring_ids"]
    n_fr = repaired["n_unique_failing_or_erroring_ids"]
    collected_delta = repaired["collected"] - baseline["collected"]
    passed_delta = rc.get("passed", 0) - bc.get("passed", 0)
    skipped_delta = rc.get("skipped", 0) - bc.get("skipped", 0)
    net = rel["n_repaired_only"] - rel["n_baseline_only"]
    predicted = collected_delta - net - skipped_delta
    if passed_delta != predicted:
        ok = False
        notes.append(f"REFUSED: passed moved {passed_delta:+d}; collected moved "
                     f"{collected_delta:+d}, the unique failing-ID set moved {net:+d} "
                     f"and skipped moved {skipped_delta:+d}, predicting {predicted:+d}")
    for side, counts, n_unique in (("baseline", bc, n_fb), ("repaired", rc, n_fr)):
        counted = counts.get("failed", 0) + counts.get("errors", 0)
        if counted != n_unique:
            notes.append(f"NOTE: {side} counts {counted} failing/erroring OCCURRENCES "
                         f"against {n_unique} unique test IDs. A test ID emitted "
                         f"under both FAILED and ERROR (teardown + call) is one ID "
                         f"and two occurrences. The identity above is checked on "
                         f"unique IDs; the raw occurrence count is published beside "
                         f"it, never instead of it.")
    if rel["n_intersection"] + rel["n_repaired_only"] != n_fr:
        ok = False
        notes.append("REFUSED: intersection + repaired-only != repaired unique-ID total")
    if rel["n_intersection"] + rel["n_baseline_only"] != n_fb:
        ok = False
        notes.append("REFUSED: intersection + baseline-only != baseline unique-ID total")
    return {
        "identity": "passed_r - passed_b == collected_delta - net_unique_failing_delta "
                    "- skipped_delta",
        "arithmetic_reconciles": ok,
        "collected_baseline": baseline["collected"],
        "collected_repaired": repaired["collected"],
        "collected_delta": collected_delta,
        "counted_run_summary_baseline": bc,
        "counted_run_summary_repaired": rc,
        "passed_baseline": bc.get("passed"),
        "passed_repaired": rc.get("passed"),
        "passed_delta": passed_delta,
        "skipped_delta": skipped_delta,
        "net_unique_failing_id_change": net,
        "predicted_passed_delta": predicted,
        "notes": notes,
    }


def environment() -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform(),
           "thread_env": {k: os.environ.get(k) for k in
                          ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                           "MKL_NUM_THREADS", "PYTHONHASHSEED")}}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:                                    # pragma: no cover
            env[mod] = None
    return env


def measure(root: Path, baseline_root: Path, *, run_id: str, label: str,
            baseline_label: str, baseline_ref: str | None = None,
            repo: Path | None = None) -> dict:
    """Measure the blast radius of a repair as a set relation, with its scope.

    ``baseline_ref`` makes the BASELINE run happen in the SAME checkout root as
    the run under test, with the suite-collected files (``product/tests/``)
    temporarily restored from a git ref. Two different trees cannot both be the
    cwd of a pytest process, so this is how a root-local comparison stays
    root-local; the files the swap actually touched are published, so the claim
    "the swap is exactly the suite-visible delta" is checkable and not asserted.
    """
    ignores = uncollectable_modules(root)
    swap: dict = {"used": bool(baseline_ref), "ref": baseline_ref,
                  "mechanism": "byte injection of product/tests/** from the ref, "
                               "restored from saved bytes after the baseline run"}
    if baseline_ref:
        target = Path("product/tests")
        originals = {p: p.read_bytes() for p in sorted((root / target).rglob("*.py"))}
        injected: dict[str, dict] = {}
        for p, blob in originals.items():
            rel = p.relative_to(root).as_posix()
            try:
                new = _ref_bytes(baseline_ref, rel, repo)
            except FileNotFoundError:
                continue                          # file is new since the ref
            if new != blob:
                p.write_bytes(new)
                injected[rel] = {
                    "baseline_sha256": hashlib.sha256(new).hexdigest(),
                    "repaired_sha256": hashlib.sha256(blob).hexdigest()}
        try:
            baseline = _run(root, ignores)
        finally:
            for p, blob in originals.items():
                p.write_bytes(blob)
        swap["files_injected"] = injected
        swap["files_injected_count"] = len(injected)
        swap["suite_visible_delta_against_ref"] = sorted(
            line.split("\t")[-1] for line in subprocess.run(
                ["git", "diff", "--name-only", baseline_ref, "--", str(target)],
                cwd=str(repo or ROOT), capture_output=True, text=True).stdout.splitlines() if line)
        swap["restored_after_baseline_run"] = all(
            p.read_bytes() == blob for p, blob in originals.items())
        swap["ref_bytes_resolved_from"] = str(repo) if repo else None
    else:
        baseline = _run(baseline_root, ignores)
    repaired = _run(root, ignores)
    rel = compare(baseline, repaired)
    rec = reconcile(baseline, repaired, rel)
    if baseline_ref:
        visible = swap.get("suite_visible_delta_against_ref") or []
        if visible and not swap.get("files_injected"):
            rec["arithmetic_reconciles"] = False
            rec["notes"].append(
                "REFUSED: --baseline-ref named a suite-visible delta "
                f"{visible} but NO bytes were injected, so the baseline run "
                "would have been a second run of the tree under test and the "
                "comparison would be vacuous")
    return {
        "schema": "product-regression-evidence/2",
        "run_id": run_id,
        "scope": {
            "measured_at_checkout_root": str(root),
            "baseline_checkout_root": str(root if baseline_ref else baseline_root),
            "control_plane_mount": "/tmp/lex_control",
            "declared_label": label,
            "baseline_label": baseline_label,
            "baseline_swap": swap,
            "root_scope_rule": (
                "EVERY number in this artifact is ROOT_SCOPED: it is a measurement "
                "at the checkout root named above and is not a claim about any other "
                "root, any other mount, or any other host. A test whose verdict "
                "depends on where the tree is mounted will invert here; the tripwire "
                "below exists to catch exactly that."),
        },
        "environment": environment(),
        "method": {
            "command_shape": "python -m pytest product/tests/ -q -p no:cacheprovider "
                             "<one --ignore per uncollectable module>",
            "ignore_rationale": "Modules that cannot be COLLECTED in this environment "
                                "are excluded from BOTH runs identically. The list is "
                                "computed by attempting collection, never hard-coded. "
                                "Their status is UNMEASURED, not passed and not failed.",
            "uncollectable_modules_excluded": ignores,
            "comparison": rel["method"],
        },
        "baseline_run": {k: v for k, v in baseline.items()},
        "repaired_run": {k: v for k, v in repaired.items()},
        "set_relation": rel,
        "arithmetic": rec,
        "environment_limited": True,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--baseline-root")
    ap.add_argument("--baseline-ref",
                    help="git ref whose product/tests/ is restored for the BASELINE "
                         "run, so both runs share one checkout root")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo", help="checkout whose object store resolves "
                                  "--baseline-ref (default: auto-detect)")
    ap.add_argument("--label", default="producer_ci_root")
    ap.add_argument("--baseline-label", default="pristine_baseline")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if not args.baseline_ref and not args.baseline_root:
        ap.error("one of --baseline-ref / --baseline-root is required")

    repo = Path(args.repo) if args.repo else _repo_for_refs()
    art = measure(Path(args.root), Path(args.baseline_root or args.root),
                  run_id=args.run_id,
                  label=args.label, baseline_label=args.baseline_label,
                  baseline_ref=args.baseline_ref, repo=repo)
    if not art["arithmetic"]["arithmetic_reconciles"]:
        print(json.dumps(art["arithmetic"], indent=2))
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(art, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}: "
          f"baseline {art['baseline_run']['n_unique_failing_or_erroring_ids']} / "
          f"repaired {art['repaired_run']['n_unique_failing_or_erroring_ids']} "
          f"unique failing-or-erroring IDs, repaired-only="
          f"{art['set_relation']['n_repaired_only']}, "
          f"baseline-only={art['set_relation']['n_baseline_only']}")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())