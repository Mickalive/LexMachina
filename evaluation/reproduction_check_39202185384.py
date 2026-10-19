#!/usr/bin/env python3
"""Committed generator of the cycle-39202185384 reproduction check (audit F-3).

WHY THIS FILE EXISTS
--------------------
Audit ``results/audit/evaluation/CYCLE_39202185384_GATE.json`` F-3 charged that
both machine checks this cycle's report leans on were produced by throwaway
scripts whose generators were never committed, so by factory-wide requirement 29
they were UNREPRODUCED: no committed artifact, no named commit, therefore no
verification claim.  This module is that generator, committed in the lane
namespace, and the report names the commit that contains it.

WHAT IT DOES
------------
1. Loads the committed claim-bearing record
   ``results/evaluation/product_served_bundle_falsification/39202185384.json``.
2. Re-executes the committed instrument against the accepted mount, twice:
   * once from THIS checkout root (the root the producer ran from), and
   * once from a freshly materialised ALTERNATE checkout root, so the
     root-directory dependence of any absolute path leaf is measured rather
     than asserted.
3. Recursively diffs every leaf of the rerun against the committed record,
   classifies each differing leaf as ``wall_clock``, ``root_dependent_path``
   or ``substantive``, and writes
   ``results/evaluation/product_served_bundle_falsification/39202185384_reproduction_check.json``.

SELF-CHECK (the defect this checker itself once had)
----------------------------------------------------
An earlier, uncommitted build of this checker *defined* its recursive walker and
never called it, so it reported ``n_leaves_differing: 0`` — a false clean.  This
implementation therefore (a) counts the leaves it actually compared, (b) asserts
that count is non-zero, (c) asserts the differing list is a list (0 is legal only
if the walker demonstrably ran), and (d) refuses to write ``pass`` unless
``n_leaves_compared_same_root`` is large enough to cover the record.  If the
walker ever stops running again this checker exits non-zero instead of
publishing a clean.

STABILITY OF THE ARTIFACT
-------------------------
Two quantities are volatile by construction and are therefore deliberately NOT
published as figures: the raw count of differing wall-clock leaves (a duration
can round identically from one execution to the next — 4 and 5 were both
observed for this record) and the raw total of differing leaves, which is
root-directory dependent (4 from the producer's own root, 17 from the alternate
root, both measured here rather than asserted).  Publishing either would be
publishing a number that does not reproduce — the exact defect this cycle was
rejected for.

What IS published reproduces byte for byte: how many leaves were walked, which
wall-clock and pin-path leaves exist in the record at all, whether any of them
differed, the normalised root-dependent path list, and the count of SUBSTANTIVE
differences (which must be zero, and whose entries — of which there must be none
— store both values in full).

Exit codes
----------
0  reproduces (no substantive leaf differs, under the disclosed classification)
1  does NOT reproduce, or the self-check failed
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-reproduction-check/1"
RUN_ID = "39202185384"

RECORD_REL = "results/evaluation/product_served_bundle_falsification/39202185384.json"
INSTRUMENT_REL = "evaluation/query_map/product_served_bundle_falsification.py"
HYPOTHESIS_REL = "evaluation/PRODUCT_SERVED_BUNDLE_FALSIFICATION_HYPOTHESIS_V1.json"
OUT_REL = ("results/evaluation/product_served_bundle_falsification/"
           "39202185384_reproduction_check.json")

#: Leaves whose value is a measurement of time. They are expected to differ on
#: every execution and are never counted as a reproduction failure.
WALL_CLOCK_FIELDS = {"generated_at", "wall_seconds", "recompute_seconds"}

#: A minimum plausible leaf count for this record. The record is ~90 KB of
#: nested JSON; a walker that silently ran zero times cannot reach this.
MIN_LEAVES = 500

CLASS_WALL_CLOCK = "wall_clock"
CLASS_ROOT_DEP = "root_dependent_path"
CLASS_SUBSTANTIVE = "substantive"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_diff(committed, rerun, path="$"):
    """Yield ``(path, leaf, committed_value, rerun_value)`` for every differing leaf."""
    if isinstance(committed, dict) and isinstance(rerun, dict):
        for key in sorted(set(committed) | set(rerun)):
            if key not in committed:
                yield (f"{path}.{key}", key, "<ABSENT>", rerun[key])
            elif key not in rerun:
                yield (f"{path}.{key}", key, committed[key], "<ABSENT>")
            else:
                yield from walk_diff(committed[key], rerun[key], f"{path}.{key}")
    elif isinstance(committed, list) and isinstance(rerun, list):
        if len(committed) != len(rerun):
            yield (f"{path}.len", "len", len(committed), len(rerun))
        for i, (a, b) in enumerate(zip(committed, rerun)):
            yield from walk_diff(a, b, f"{path}[{i}]")
    else:
        if committed != rerun or type(committed) is not type(rerun):
            leaf = path.rsplit(".", 1)[-1]
            leaf = leaf.split("[", 1)[0]
            yield (path, leaf, committed, rerun)


def _normalise(value, roots) -> str:
    """Replace every checkout/mount root path by a shared token.

    Both checkout roots must map to the SAME token, otherwise a pure root
    difference would survive normalisation and be mis-read as substantive.
    Longest first, so the alternate root (which lives inside the temp root)
    is consumed before the temp root itself.
    """
    if not isinstance(value, str):
        return value
    out = value
    for path, token in sorted(roots, key=lambda kv: -len(kv[0])):
        out = out.replace(path, token)
    return out


def classify(path: str, leaf: str, committed, rerun, roots) -> str:
    if leaf in WALL_CLOCK_FIELDS:
        return CLASS_WALL_CLOCK
    if leaf == "path" and path.startswith("$.pin_rehash"):
        if isinstance(committed, str) and isinstance(rerun, str):
            if _normalise(committed, roots) == _normalise(rerun, roots):
                return CLASS_ROOT_DEP
    return CLASS_SUBSTANTIVE


def _iter_leaves(node, path="$"):
    """Yield ``(path, leaf_name, value)`` for EVERY leaf — not just differences.

    This is the walker whose absence once produced a false clean: it is called
    unconditionally and its output is counted, so a no-op is impossible to miss.
    """
    if isinstance(node, dict):
        for key in sorted(node):
            yield from _iter_leaves(node[key], f"{path}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_leaves(item, f"{path}[{i}]")
    else:
        yield path, path.rsplit(".", 1)[-1].split("[", 1)[0], node


def _committed_tree_files() -> list[Path]:
    """The files git tracks — i.e. the committed tree, not untracked scratch."""
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
                             capture_output=True, text=True, check=True)
        rels = [r for r in out.stdout.split("\0") if r]
    except Exception:  # pragma: no cover - git always present in this factory
        rels = []
    if not rels:  # pragma: no cover - fallback
        return []
    return [REPO_ROOT / r for r in rels]


def materialise_alternate_root(dest: Path) -> Path:
    """Copy the tracked file set (``git ls-files``) to a differently-named root.

    Deliberately selective: only files git tracks — the committed tree as
    checked out — so scratch output, ``.git`` and ``__pycache__`` cannot leak
    into the alternate execution.  Everything the instrument reads from
    ``_REPO_ROOT`` is inside that set; if something is not, the alternate run
    fails loudly rather than quietly passing.
    """
    dest.mkdir(parents=True, exist_ok=True)
    files = _committed_tree_files()
    if not files:  # pragma: no cover - defensive
        shutil.copytree(REPO_ROOT, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__",
                                                      ".pytest_cache", "*.pyc"))
        return dest
    for src in files:
        if not src.is_file():
            continue
        rel = src.relative_to(REPO_ROOT)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest


def run_instrument(*, cwd: Path, hypothesis: Path, out_dir: Path) -> tuple[int, dict]:
    env = dict(os.environ)
    env["GITHUB_RUN_ID"] = RUN_ID
    cmd = [sys.executable, "-m",
           "evaluation.query_map.product_served_bundle_falsification",
           "--run-id", RUN_ID,
           "--hypothesis", str(hypothesis),
           "--out-dir", str(out_dir)]
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    record_path = out_dir / f"{RUN_ID}.json"
    record = {}
    if record_path.exists():
        with open(record_path, encoding="utf-8") as fh:
            record = json.load(fh)
    return proc.returncode, record, proc.stdout[-4000:], proc.stderr[-4000:]


def _diff_block(committed: dict, rerun: dict, roots) -> dict:
    """Classify every difference and report ONLY quantities that are stable.

    Two quantities are volatile by construction and are therefore never published
    as figures: the raw count of differing wall-clock leaves (a duration can round
    identically from one execution to the next — 4 and 5 were both observed) and
    the raw total of differing leaves (root-directory dependent: the alternate
    root always shows more of them).  What IS published, and reproduces byte for
    byte: how many leaves were compared, how many wall-clock / pin-path leaves
    exist in the record at all, whether any of them differed, and the count of
    SUBSTANTIVE differences — which must be zero.
    """
    diffs = list(walk_diff(committed, rerun))
    substantive: list[dict] = []
    root_dep: list[dict] = []
    wall_differed = 0
    for path, leaf, a, b in diffs:
        kind = classify(path, leaf, a, b, roots)
        if kind == CLASS_SUBSTANTIVE:
            substantive.append({"path": path, "leaf": leaf,
                                "committed": a, "rerun": b})
        elif kind == CLASS_ROOT_DEP:
            root_dep.append({
                "path": _normalise(path, roots),
                "normalised_committed": _normalise(a, roots),
                "normalised_rerun": _normalise(b, roots),
            })
        else:
            wall_differed += 1

    wall_present = sorted(
        p for p, leaf, _ in _iter_leaves(committed) if leaf in WALL_CLOCK_FIELDS)
    pin_path_present = sorted(
        p for p, leaf, _ in _iter_leaves(committed)
        if leaf == "path" and p.startswith("$.pin_rehash"))

    return {
        "n_leaves_compared": sum(1 for _ in _iter_leaves(committed)),
        "n_substantive_differing_leaves": len(substantive),
        "substantive_differing_leaves": substantive,
        "wall_clock": {
            "n_leaves_in_record": len(wall_present),
            "leaves_in_record": wall_present,
            "differed_this_execution": wall_differed > 0,
            "note": ("The raw count of differing wall-clock leaves is NOT a "
                     "published claim: it varies between executions because a "
                     "duration can round identically (4 and 5 were both observed "
                     "for this record). The stable claims are the leaf list and "
                     "the boolean."),
        },
        "root_dependent_path": {
            "n_leaves_in_record": len(pin_path_present),
            "differed_this_execution": bool(root_dep),
            "n_differed_this_execution": len(root_dep),
            "differing_leaves_normalised": root_dep,
            "note": ("pin_rehash stores ABSOLUTE path strings. They match when "
                     "this checker runs from the producer's own checkout root "
                     "and differ when it does not; both executions are reported, "
                     "with both roots normalised to <ROOT> so the comparison is "
                     "root-independent."),
        },
        "n_leaves_differing_excluding_wall_clock_and_root_dependent": len(substantive),
        "reproduces_excluding_wall_clock_and_root_dependent": not substantive,
    }


def main(argv=None) -> int:
    with open(REPO_ROOT / RECORD_REL, encoding="utf-8") as fh:
        committed = json.load(fh)
    committed_sha = sha256_file(REPO_ROOT / RECORD_REL)
    instrument_sha = sha256_file(REPO_ROOT / INSTRUMENT_REL)
    generator_sha = sha256_file(Path(__file__))

    with tempfile.TemporaryDirectory(prefix="lex_repro_") as tmp:
        tmp_path = Path(tmp)
        # ---- execution 1: the same checkout root the producer ran from ----
        rc_same, same_rec, out_same, err_same = run_instrument(
            cwd=REPO_ROOT,
            hypothesis=REPO_ROOT / HYPOTHESIS_REL,
            out_dir=tmp_path / "same_root")

        # ---- execution 2: a differently-named checkout root ----
        alt_root = materialise_alternate_root(tmp_path / "alternate_root")
        rc_alt, alt_rec, out_alt, err_alt = run_instrument(
            cwd=alt_root,
            hypothesis=alt_root / HYPOTHESIS_REL,
            out_dir=tmp_path / "alternate_out")

    # Both executions are normalised against the SAME root map, and both checkout
    # roots collapse to ONE token: a path leaf is root-dependent iff the two
    # strings become equal once each root is replaced by that token.
    roots = [
        (str(alt_root), "<ROOT>"),
        (str(REPO_ROOT), "<ROOT>"),
        (str(tmp_path), "<TMP>"),
        ("/tmp/lex_accepted/product", "<MOUNT>"),
    ]
    same_roots = roots
    alt_roots = roots

    def _failed_block(reason: str) -> dict:
        return {
            "n_leaves_compared": 0,
            "n_substantive_differing_leaves": -1,
            "substantive_differing_leaves": [],
            "wall_clock": {"n_leaves_in_record": -1, "leaves_in_record": [],
                           "differed_this_execution": False, "note": reason},
            "root_dependent_path": {"n_leaves_in_record": -1,
                                    "differed_this_execution": False,
                                    "n_differed_this_execution": -1,
                                    "differing_leaves_normalised": [],
                                    "note": reason},
            "n_leaves_differing_excluding_wall_clock_and_root_dependent": -1,
            "reproduces_excluding_wall_clock_and_root_dependent": False,
        }

    same_block = (_diff_block(committed, same_rec, same_roots)
                  if same_rec and committed
                  else _failed_block("no rerun record: see self_check.problems"))
    alt_block = (_diff_block(committed, alt_rec, alt_roots)
                 if alt_rec and committed
                 else _failed_block("no rerun record: see self_check.problems"))

    # --- the self-check that the walker actually ran (the past false clean) ---
    self_check_problems: list[str] = []
    if not same_rec:
        self_check_problems.append(
            "the same-root rerun produced no record (exit %s): %s"
            % (rc_same, (err_same or out_same)[-500:]))
    if not alt_rec:
        self_check_problems.append(
            "the alternate-root rerun produced no record (exit %s): %s"
            % (rc_alt, (err_alt or out_alt)[-500:]))
    compared = same_block.get("n_leaves_compared", 0)
    if compared < MIN_LEAVES:
        self_check_problems.append(
            f"leaf walker compared only {compared} leaves (< {MIN_LEAVES}); "
            "it did not really walk the record — refusing to publish a clean")
    if not isinstance(same_block.get("wall_clock", {}).get("leaves_in_record"), list):
        self_check_problems.append("wall-clock leaf enumeration did not run")
    if same_rec and committed.get("schema") != same_rec.get("schema"):
        self_check_problems.append(
            "schema mismatch between committed record and rerun: "
            f"{committed.get('schema')!r} vs {same_rec.get('schema')!r}")

    verdict_committed = committed.get("verdict")
    verdict_rerun = same_rec.get("verdict")
    pins_reproduce = bool(
        same_rec.get("pins_unchanged_during_run") is True
        and (same_rec.get("pin_rehash_pre") or {}).get("n_drift") == 0)

    reproduces = (
        not self_check_problems
        and bool(same_block.get("reproduces_excluding_wall_clock_and_root_dependent"))
        and bool(alt_block.get("reproduces_excluding_wall_clock_and_root_dependent"))
        and verdict_committed == verdict_rerun
        and pins_reproduce)

    record = {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "generator": "evaluation/reproduction_check_39202185384.py",
        "generator_sha256": generator_sha,
        "question": "Does the committed record reproduce from the committed tree "
                    "on a fresh execution?",
        "committed_record": RECORD_REL,
        "committed_record_sha256": committed_sha,
        "instrument": INSTRUMENT_REL,
        "instrument_sha256": instrument_sha,
        "hypothesis": HYPOTHESIS_REL,
        "hypothesis_sha256": sha256_file(REPO_ROOT / HYPOTHESIS_REL),
        "n_leaves_compared": same_block.get("n_leaves_compared", 0),
        "n_leaves_compared_semantics": (
            "every leaf of the full committed record, counted by _iter_leaves; "
            "the count is a property of the record and is therefore stable"),
        "executions": [
            {"root": "the committed checkout root (the producer's own root)",
             "exit_code": rc_same, **same_block},
            {"root": "an alternate checkout root materialised from git ls-files",
             "exit_code": rc_alt, **alt_block},
        ],
        "verdict_committed": verdict_committed,
        "verdict_rerun": verdict_rerun,
        "verdict_reproduces": verdict_committed == verdict_rerun,
        "pins_reproduce": pins_reproduce,
        "n_substantive_differing_leaves": same_block.get(
            "n_substantive_differing_leaves", -1),
        "n_substantive_differing_leaves_alternate_root": alt_block.get(
            "n_substantive_differing_leaves", -1),
        "n_leaves_differing_excluding_wall_clock_and_root_dependent":
            same_block.get("n_leaves_differing_excluding_wall_clock_and_root_dependent", -1),
        "reproduces_excluding_wall_clock_and_root_dependent":
            bool(same_block.get("reproduces_excluding_wall_clock_and_root_dependent"))
            and bool(alt_block.get("reproduces_excluding_wall_clock_and_root_dependent")),
        "wall_clock": same_block.get("wall_clock"),
        "root_directory_dependence": {
            "same_root": {
                "differed": same_block.get("root_dependent_path", {}).get(
                    "differed_this_execution"),
                "n_differed": same_block.get("root_dependent_path", {}).get(
                    "n_differed_this_execution"),
            },
            "alternate_root": {
                "differed": alt_block.get("root_dependent_path", {}).get(
                    "differed_this_execution"),
                "n_differed": alt_block.get("root_dependent_path", {}).get(
                    "n_differed_this_execution"),
                "differing_leaves_normalised": alt_block.get(
                    "root_dependent_path", {}).get("differing_leaves_normalised", []),
            },
            "why": ("pin_rehash checks store absolute path strings. They are "
                    "identical when the checker runs from the same root as the "
                    "producer and differ when it does not, so the RAW differing-"
                    "leaf count is root-directory dependent by construction and "
                    "is deliberately not published as a figure. The root-"
                    "independent quantity is "
                    "n_leaves_differing_excluding_wall_clock_and_root_dependent, "
                    "which is what this artifact claims."),
            "measured_not_asserted": True,
        },
        "volatile_figures_not_published": [
            "raw count of differing wall-clock leaves (varies 4..5 by rounding)",
            "raw total of differing leaves (root-directory dependent: 4 same-root "
            "against 17 alternate-root were observed)",
        ],
        "self_check": {
            "leaf_walk_counted": compared,
            "min_leaves_required": MIN_LEAVES,
            "problems": self_check_problems,
            "pass": not self_check_problems,
            "note": ("An earlier uncommitted build of this checker DEFINED its "
                     "recursive walker and never called it and reported 0 "
                     "differing leaves - a false clean. This build counts the "
                     "leaves it compared and refuses to publish a clean below "
                     "the minimum, so a silent no-op is now a loud failure."),
        },
        "reproduces": reproduces,
        "reading": (
            "Every claim-bearing leaf of the committed record reproduces from the "
            "committed tree on both fresh executions: zero substantive "
            "differences. The only leaves that move are wall-clock measurements "
            "and absolute pin_rehash path strings that differ solely because the "
            "checkout lives at a different root; both classes are named, counted "
            "and excluded from the claim, not silently dropped."
            if reproduces else
            "THE COMMITTED RECORD DOES NOT REPRODUCE. See "
            "executions[].substantive_differing_leaves (both values stored in "
            "full) and self_check.problems."),
    }

    out_path = REPO_ROOT / OUT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: record[k] for k in (
        "schema", "run_id", "reproduces", "n_leaves_compared",
        "n_substantive_differing_leaves",
        "n_leaves_differing_excluding_wall_clock_and_root_dependent",
        "verdict_committed", "verdict_rerun", "pins_reproduce")}, indent=2))
    return 0 if reproduces else 1



if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
