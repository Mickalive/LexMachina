"""Corrected entry point for charter acceptance test (3).

The contract
------------
Charter acceptance test (3) names exactly this invocation::

    python -m frontier_query_concept_recall.cli --bundle <path> --out <dir>

and requires it to be runnable and to emit, per bundle and per frozen leg,
``rows_per_concept``, ``under_covered`` and frozen-authority recall per
language, in the same record shape as the accepted evaluation artifacts.

The defect this file repairs
----------------------------
``frontier_query_concept_recall.cli`` loads ONLY the bundles passed to
``--bundle`` (``load_bundles`` returns early when ``paths`` is non-empty,
cli.py:1005-1015), but its A3 shuffled non-vacuity control unconditionally
indexes a *sibling* served question::

    other = next(o for o in SERVED_QUESTIONS if o != qid)          # cli.py:416
    a3_rows = union_rows(base_rows, (outcomes.get(served_expansions[other].query).rows
                                     if outcomes.get(served_expansions[other].query) else []))

Any ``--bundle`` argument set that is a strict subset of the three served
questions therefore dies with a raw ``KeyError`` before it can emit a record.
Reproduced this cycle, offline, zero network::

    $ python -m frontier_query_concept_recall.cli \
        --bundle .../de-kapitalverletzung.bundle.json --out <fresh> --offline
    KeyError: 'fr-bail-entretien'          # cli.py:418

So the one invocation the charter names is not runnable in the one-bundle
form the charter names. That is an engineering defect, not a result.

The fix
-------
The served-question SET is fixed by the charter, not by the caller: it is
exactly ``de-kapitalverletzung``, ``fr-bail-entretien``,
``it-responsabilita-medica`` of packet ``rebuilt-39027045675``. ``--bundle``
selects which of them are *named on the command line*; it does not redefine
the set. This entry point therefore

1. completes any missing served question from the RULES.json-pinned,
   sha256-verified, READ-ONLY accepted bundle bytes,
2. records exactly which questions it completed, in the output record, under
   ``entry_point`` - the completion is disclosed, never silent, and
3. if a sibling cannot be resolved, exits 2 with an actionable message.

It never fabricates a control, never degrades a control to a pass, and never
writes outside ``--out``. The sibling expansions are already in the committed
A1 cache (15 envelopes = 3 served + 4 legs x 3 languages), so completing the
set costs zero extra network in an offline replay.

Defect C (offline replay against a fresh ``--out`` finding no cache and
fabricating a ``transport::all_queries_ok`` regression) is repaired here too,
by seeding a scratch copy read-only from this team's committed cache and
aborting loudly when no envelope is visible anywhere.

Scope
-----
This file lives under ``frontier/frontier-query-concept-recall/``, inside the
Frontier team's enforced write scope. The accepted package at
``frontier/frontier_query_concept_recall/`` is left byte-untouched: a Python
package cannot be named with the hyphens in the team id, so that path is
outside the workflow's scope guard, and the package is already accepted
(``lab/frontier/frontier-query-concept-recall`` = bd1b4d73, audit gate PASS)
and independently audited. The remedy lives here instead of in audited code.

Usage
-----
::

    PYTHONPATH=frontier python frontier/frontier-query-concept-recall/cli_entry.py \
        --bundle <path> [--bundle <path> ...] --out <dir> [--offline] [--print-verdict]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
_PACKAGE_PARENT = _REPO / "frontier"
for _p in (str(_PACKAGE_PARENT), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from frontier_query_concept_recall import cli as harness_cli  # noqa: E402

from run_harness import COMMITTED_CACHE_DIRS  # noqa: E402  (same directory)

SERVED_QUESTIONS = tuple(harness_cli.SERVED_QUESTIONS)

#: Canonical frozen rules.  Resolved from the harness's OWN RULES_PATH, which is
#: what `cli.py` reads and what every published record reports as
#: ``rules_file_sha256`` (c5447bac0605a8bc...).
#:
#: DEFECT G: this directory ALSO contains ``frontier/frontier-query-concept-recall/
#: RULES.json`` -- a STALE, DIFFERENT-SCHEMA rules file written by run 39157032880
#: at 2026-10-18T19:18:59Z, i.e. BEFORE the real freeze at 21:21:56Z, and last
#: touched 2026-10-19T00:10:18Z.  Its input pins do NOT match the accepted bytes
#: (it pins de-kapitalverletzung as 2441ff2b..., the accepted bundle is
#: c4005d4b...).  It is a claim-discipline trap for anything that resolves "the
#: RULES" by directory.  It is left byte-untouched as the historical record of
#: that run; ``RULES_CANONICAL.json`` beside it says which file is authoritative.
RULES_PATH = Path(harness_cli.RULES_PATH)
RESULTS_RULES_PATH = _REPO / "results/frontier/frontier-query-concept-recall/RULES.json"
STALE_RULES_PATH = _HERE / "RULES.json"
EXPECTED_RULES_SHA256 = "c5447bac0605a8bcf8c3d1820bee56a5bb0e814365978ec1fa12ac189776ee9a"

ABORT_NO_SIBLING = """\
cannot resolve the served-question sibling the A3 shuffled control needs.

  --bundle gave      : {given}
  served set         : {served}
  unresolved         : {missing}

The A3 control scores question i using the expansion rows mined for a
DIFFERENT served question j.  That is what makes it a non-vacuity control, so
it is never skipped and never fabricated.  Point --bundle at the missing
bundle(s), or omit --bundle entirely to use the accepted served set.
"""

ABORT_NO_CACHE = """\
offline replay found no cached A1-channel envelopes.

  --out cache dir            -> {out_cache}
  committed fallbacks        -> {fallbacks}

Nothing was measured, because a replay with no cache cannot measure anything.
Either point --out at this team's results directory, seed the cache with

    cp -r results/frontier/frontier-query-concept-recall/cache <dir>/

or drop --offline to issue the calls live (network; frozen per-search budget
applies).
"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def committed_cache_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    for path in COMMITTED_CACHE_DIRS:
        resolved = path.resolve()
        if resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def rules_bundle_pins() -> dict[str, dict]:
    """qid -> {'path': str, 'content_sha256': str} from the CANONICAL frozen RULES.

    Read-only and digest-checked three ways:

    * the canonical rules file re-hashes to ``EXPECTED_RULES_SHA256``,
    * the results-directory copy re-hashes to the same digest,
    * every served bundle pin re-hashes to its pinned value.

    A pin that no longer re-hashes is an input-integrity failure and is
    surfaced, never silently used.
    """
    for path in (RULES_PATH, RESULTS_RULES_PATH):
        if not path.is_file():
            raise RuntimeError(f"canonical RULES.json missing at {path}")
        digest = sha256_file(path)
        if digest != EXPECTED_RULES_SHA256:
            raise RuntimeError(
                f"canonical RULES.json at {path} re-hashes to {digest}, expected "
                f"{EXPECTED_RULES_SHA256}. The freeze moved; no measurement was taken.")
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    files = ((rules.get("inputs") or {}).get("files")) or {}
    out: dict[str, dict] = {}
    for qid in SERVED_QUESTIONS:
        meta = files.get(f"{qid}.bundle.json")
        if meta and meta.get("path") and meta.get("content_sha256"):
            out[qid] = dict(meta)
    return out


def add_charter_named_fields(record: dict) -> list[str]:
    """Emit the field NAMES acceptance test (3) uses, additively.

    The harness records the per-concept row counts under the accepted evaluation
    artifact's own key, ``concept_row_counts`` (that is what
    ``QUESTION_NATIVE_COVERAGE.json`` carries, and acceptance test (3) also asks
    for "the same record shape as the accepted evaluation artifacts").  The
    charter's own wording names the same quantity ``rows_per_concept``.

    Both names now resolve to the SAME object, so a reader using either spelling
    finds it, and no number changes.  Purely additive: nothing is renamed,
    removed or recomputed.  Returns the list of paths that gained a field.
    """
    added: list[str] = []
    for qid, entry in (record.get("served_questions") or {}).items():
        for arm, payload in entry.items():
            if not isinstance(payload, dict):
                continue
            if "concept_row_counts" in payload and "rows_per_concept" not in payload:
                payload["rows_per_concept"] = payload["concept_row_counts"]
                added.append(f"served_questions/{qid}/{arm}/rows_per_concept")
            if "under_covered" not in payload and "concepts_with_zero_rows" in payload:
                payload["under_covered"] = payload["concepts_with_zero_rows"]
                added.append(f"served_questions/{qid}/{arm}/under_covered")
    for slug, leg in (record.get("frozen_legs") or {}).items():
        for language, cell in (leg.get("per_language") or {}).items():
            for arm, payload in cell.items():
                if not isinstance(payload, dict):
                    continue
                if "recall" in payload and "authority_recall" not in payload:
                    payload["authority_recall"] = payload["recall"]
                    added.append(
                        f"frozen_legs/{slug}/per_language/{language}/{arm}/authority_recall")
    return added


def stale_rules_report() -> dict:
    """Disclosure of the stale rules file sitting in this directory (defect G)."""
    if not STALE_RULES_PATH.is_file():
        return {"present": False}
    digest = sha256_file(STALE_RULES_PATH)
    return {
        "present": True,
        "path": str(STALE_RULES_PATH.relative_to(_REPO)),
        "sha256": digest,
        "is_canonical": digest == EXPECTED_RULES_SHA256,
        "written_by_run": "39157032880 @ 2026-10-18T19:18:59Z (before the freeze at "
                          "2026-10-18T21:21:56Z); last touched 2026-10-19T00:10:18Z",
        "why_it_is_not_authoritative": (
            "different schema (no inputs.files, an input_bundles map keyed by qid with "
            "repository-relative paths), and its de-kapitalverletzung pin 2441ff2b... does "
            "not match the accepted bundle c4005d4b..."),
        "disposition": "left byte-untouched as the historical record of run 39157032880; "
                       "see RULES_CANONICAL.json in the same directory",
    }


def resolve_served_set(requested: list[str] | None) -> tuple[dict[str, dict], list[str], list[str]]:
    """Return (bundles, completed_qids, unresolved_qids).

    ``bundles`` is keyed by qid.  ``completed_qids`` are served questions that
    were NOT named on the command line and were read from the RULES-pinned
    read-only accepted bytes; ``unresolved_qids`` are served questions that
    could not be resolved from either source.
    """
    pins = rules_bundle_pins()
    bundles: dict[str, dict] = {}
    completed: list[str] = []
    unresolved: list[str] = []

    for raw in requested or []:
        path = Path(raw)
        qid = path.name.replace(".bundle.json", "")
        bundles[qid] = json.loads(path.read_text(encoding="utf-8"))

    for qid in SERVED_QUESTIONS:
        if qid in bundles:
            continue
        pin = pins.get(qid)
        if pin and Path(pin["path"]).is_file():
            path = Path(pin["path"])
            digest = sha256_file(path)
            if digest != pin["content_sha256"]:
                raise RuntimeError(
                    f"input integrity: pinned bundle for {qid} re-hashes to {digest}, "
                    f"RULES.json pins {pin['content_sha256']}. The accepted bytes moved; "
                    "no measurement was taken."
                )
            bundles[qid] = json.loads(path.read_text(encoding="utf-8"))
            # With no --bundle at all the served set IS the default, so nothing
            # was "completed"; only a named subset needs disclosing.
            if requested:
                completed.append(qid)
        else:
            unresolved.append(qid)
    return bundles, completed, unresolved


def _visible_envelopes(out_cache: Path, fallbacks: tuple[Path, ...]) -> int:
    return sum(1 for root in (out_cache, *fallbacks)
               if root.is_dir() for _ in root.glob("*/*.json"))


def _run_harness(bundles: dict[str, dict], out_dir: Path, *, offline: bool) -> dict:
    """Invoke the accepted harness, seeding a scratch cache for a fresh --out."""
    if not offline:
        return harness_cli.run(bundles, out_dir, offline=False)

    out_cache = out_dir / "cache"
    fallbacks = committed_cache_roots()
    if not out_cache.is_dir() or not any(out_cache.glob("*/*.json")):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / "cache"
            for root in fallbacks:
                shutil.copytree(root, scratch, dirs_exist_ok=True)
            record = harness_cli.run(bundles, Path(tmp), offline=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "harness_results.json").write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return record
    return harness_cli.run(bundles, out_dir, offline=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontier/frontier-query-concept-recall/cli_entry.py",
        description="Acceptance-test-(3) entry point for the concept-recall harness")
    parser.add_argument("--bundle", action="append", dest="bundles",
                        help="served bundle; repeat for more than one. Omit for the "
                             "accepted served set.")
    parser.add_argument("--out", default="results/frontier/frontier-query-concept-recall")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--print-verdict", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)

    try:
        bundles, completed, unresolved = resolve_served_set(args.bundles)
    except RuntimeError as exc:
        print(f"input integrity failure: {exc}", file=sys.stderr)
        return 2

    if unresolved:
        print(ABORT_NO_SIBLING.format(
            given=[Path(p).name for p in (args.bundles or ["<none: accepted served set>"])],
            served=list(SERVED_QUESTIONS), missing=unresolved), file=sys.stderr)
        return 2

    if args.offline and _visible_envelopes(out_dir / "cache",
                                           committed_cache_roots()) == 0:
        print(ABORT_NO_CACHE.format(
            out_cache=out_dir / "cache",
            fallbacks=[str(p) for p in committed_cache_roots()] or "none found"),
            file=sys.stderr)
        return 2

    record = _run_harness(bundles, out_dir, offline=args.offline)

    # Acceptance test (3) names rows_per_concept / under_covered / recall per
    # language.  Alias them additively onto the accepted artifact's own key
    # names so either spelling resolves to the same object.
    added_aliases = add_charter_named_fields(record)

    # Disclosure, written into the record itself: the served set is charter-fixed
    # and --bundle did not shrink it.
    entry = record.setdefault("entry_point", {})
    entry["module"] = "frontier/frontier-query-concept-recall/cli_entry.py"
    entry["acceptance_test_3_contract"] = (
        "--bundle <path> --out <dir>; per bundle and per frozen leg it emits "
        "rows_per_concept, under_covered and frozen-authority recall per language "
        "in the accepted evaluation record shape")
    entry["requested_bundles"] = [Path(p).name for p in (args.bundles or [])]
    entry["served_questions_completed_from_pinned_readonly_mount"] = completed
    entry["a3_control_note"] = (
        "the A3 shuffled control needs a sibling served question, so the served set "
        "is completed from the RULES.json-pinned sha256-verified read-only accepted "
        "bundle bytes; --bundle selects which are named, it does not redefine the set")
    entry["repair"] = (
        "reproduces a raw KeyError in frontier_query_concept_recall/cli.py:418 for any "
        "--bundle set that is a strict subset of the three served questions")
    entry["canonical_rules_file"] = str(RULES_PATH.relative_to(_REPO))
    entry["canonical_rules_sha256"] = EXPECTED_RULES_SHA256
    entry["stale_rules_file_in_this_directory"] = stale_rules_report()
    entry["acceptance_test_3_fields_added_additively"] = added_aliases
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "harness_results.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    verdict = record["verdict"]
    summary = {k: verdict[k] for k in (
        "outcome", "accepted_baseline_reproduced", "improved_fr_it_cells",
        "reduced_under_covered_questions", "any_vacuous", "regressed_gates")}
    summary["served_questions_completed_from_pinned_readonly_mount"] = completed
    print(json.dumps(summary, indent=1))
    if args.print_verdict:
        print(json.dumps({
            "network_calls": record["latency_budget"].get("n_network_calls_this_run"),
            "cache_hits": record["latency_budget"].get("n_cache_hits_this_run"),
            "rules_file_sha256": record.get("rules_file_sha256"),
        }, indent=1))
    return 0 if verdict["accepted_baseline_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
