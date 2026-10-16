"""The producer must never finish a cycle with out-of-scope writes.

Regression pin for the diagnosed operational failure: the producer wrote its own
audit placement copies to ``results/audit/frontier/frontier-counter-label-integrity/``
and ``reports/audit/frontier/frontier-counter-label-integrity/``, which are OUT of
the workflow's "Enforce team scope" allow-list (and out of charter acceptance test
12, which forbids producer writes outside the team's namespace). GitHub runs
38845649012, 38846758718, 38848314260, 38849513219, 38849940657, 38850302366,
38850765576 and 38851515402 -- eight dispatches, ending at run 38851515402 --
all failed at exactly that step while the resilience job re-dispatched them.

The guard mirrors the WORKFLOW rule, never RULES.json: the frozen ``write_scope``
lists the audit dirs because it describes the AUDIT job's checkout, not the
producer's.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from conftest import HARNESS_DIR

from frontier_counter_label_integrity.scope_guard import (
    TEAM_ID,
    allowed_prefixes,
    check_repo_scope,
    git_status_paths,
    main as scope_main,
    porcelain_paths,
    violations,
)

TEAM = TEAM_ID
HISTORICAL_RUNS = (
    "38845649012", "38846758718", "38848314260", "38849513219",
    "38849940657", "38850302366", "38850765576", "38851515402",
)


def _git_init(path) -> str:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    return str(path)


# ---------------------------------------------------------------- allowed list

def test_allowed_prefixes_is_exactly_the_workflow_order():
    assert allowed_prefixes() == (
        f"frontier/{TEAM}/",
        f"tests/frontier/{TEAM}/",
        f"results/frontier/{TEAM}/",
        f"reports/frontier/{TEAM}/",
        f"data/frontier/{TEAM}/",
        f"state/frontier/{TEAM}.json",
    )


def test_allowed_entries_and_nested_files_pass():
    paths: list[str] = []
    for entry in allowed_prefixes():
        paths.append(entry)
        if entry.endswith("/"):
            paths.append(entry + "some/inner/file.txt")
    paths.append("")  # the empty string is in scope in the workflow's case
    assert violations(paths) == []


def test_empty_path_is_in_scope():
    assert violations([""]) == []


# ------------------------------------------------------- historical regression

def test_historical_audit_tree_writes_are_violations():
    """Regression: the audit tree belongs to the AUDIT job, never the producer.

    These are the two placement copies whose writes made runs
    38845649012 -> 38851515402 (eight dispatches) fail the workflow's
    "Enforce team scope" step over and over.
    """
    assert HISTORICAL_RUNS[-1] == "38851515402"
    gate = f"results/audit/frontier/{TEAM}/CYCLE_1_GATE.json"
    report = f"reports/audit/frontier/{TEAM}/CYCLE_1.md"
    assert violations([gate]) == [gate]
    assert violations([report]) == [report]
    assert violations([gate, report]) == sorted([gate, report])
    # the literal historical names
    assert violations([f"results/audit/frontier/{TEAM}/CYCLE_38851515402_GATE.json"]) == [
        f"results/audit/frontier/{TEAM}/CYCLE_38851515402_GATE.json"
    ]
    assert violations([f"reports/audit/frontier/{TEAM}/CYCLE_38851515402.md"]) == [
        f"reports/audit/frontier/{TEAM}/CYCLE_38851515402.md"
    ]


def test_out_of_scope_paths_are_violations():
    bad = [
        # outside the allow-list entirely (results/product is NOT results/frontier/)
        "results/product/gate_packet/38799024807/questions/fr-bail-entretien.bundle.json",
        # state: only the team's own exact file is in scope
        "state/frontier/some-other-team.json",
        f"state/frontier/{TEAM}.json.bak",
        # sibling-directory trick: the trailing slash must anchor on the team id
        f"frontier/{TEAM}-extra/file.py",
        f"results/frontier/{TEAM}-extra/SCORES.json",
        # other top-level trees
        "evaluation/something.json",
        "product/core/x.py",
    ]
    assert violations(bad) == sorted(bad)


def test_state_file_semantics():
    own = f"state/frontier/{TEAM}.json"
    assert violations([own]) == []
    for other in (
        "state/frontier/some-other-team.json",
        f"state/frontier/{TEAM}.json.bak",
        f"state/frontier/{TEAM}.json/x",
        f"state/{TEAM}.json",
    ):
        assert violations([other]) == [other], other


# --------------------------------------------------------------------- parsing

def test_clean_git_tree_yields_no_paths(tmp_path):
    repo = _git_init(tmp_path)
    assert git_status_paths(repo) == []
    assert check_repo_scope(repo)["ok"] is True
    assert check_repo_scope(repo)["violations"] == []


def test_porcelain_line_parsing_on_synthetic_input():
    lines = [
        f" M frontier/{TEAM}/frontier_counter_label_integrity/cli.py",
        f"?? results/frontier/{TEAM}/new_artifact.json",
        f"?? results/audit/frontier/{TEAM}/CYCLE_1_GATE.json",
        f"?? reports/audit/frontier/{TEAM}/CYCLE_1.md",
        "?? results/product/gate_packet/x.json",
        "?? evaluation/metrics.json",
        f"R  scratch/notes.md -> state/frontier/{TEAM}.json",
        f"R  scratch/gate.json -> results/audit/frontier/{TEAM}/CYCLE_2_GATE.json",
    ]
    paths = porcelain_paths(lines)
    # workflow's literal behaviour: drop the first 3 characters ("XY ")
    assert paths == [
        f"frontier/{TEAM}/frontier_counter_label_integrity/cli.py",
        f"results/frontier/{TEAM}/new_artifact.json",
        f"results/audit/frontier/{TEAM}/CYCLE_1_GATE.json",
        f"reports/audit/frontier/{TEAM}/CYCLE_1.md",
        "results/product/gate_packet/x.json",
        "evaluation/metrics.json",
        f"state/frontier/{TEAM}.json",
        f"results/audit/frontier/{TEAM}/CYCLE_2_GATE.json",
    ]
    assert violations(paths) == sorted([
        f"results/audit/frontier/{TEAM}/CYCLE_1_GATE.json",
        f"reports/audit/frontier/{TEAM}/CYCLE_1.md",
        "results/product/gate_packet/x.json",
        "evaluation/metrics.json",
        f"results/audit/frontier/{TEAM}/CYCLE_2_GATE.json",
    ])
    assert porcelain_paths([]) == []


def test_git_status_paths_sees_untracked_files(tmp_path):
    repo = _git_init(tmp_path)
    os.makedirs(os.path.join(repo, f"frontier/{TEAM}"))
    with open(os.path.join(repo, f"frontier/{TEAM}/x.py"), "w", encoding="utf-8") as fh:
        fh.write("x = 1\n")
    os.makedirs(os.path.join(repo, "results/audit/frontier", TEAM))
    gate = os.path.join(repo, "results/audit/frontier", TEAM, "CYCLE_1_GATE.json")
    with open(gate, "w", encoding="utf-8") as fh:
        fh.write("{}\n")
    assert git_status_paths(repo) == sorted([
        f"frontier/{TEAM}/x.py",
        f"results/audit/frontier/{TEAM}/CYCLE_1_GATE.json",
    ])


# --------------------------------------------------------------- CLI/main exits

def test_main_exit_codes_and_output(tmp_path, capsys):
    # clean repo -> 0
    clean = _git_init(tmp_path / "clean")
    assert scope_main(["--repo-root", clean, "--quiet"]) == 0
    capsys.readouterr()

    # out-of-scope untracked file -> 1, violation printed unless --quiet
    dirty = _git_init(tmp_path / "dirty")
    os.makedirs(os.path.join(dirty, "results/product"))
    with open(os.path.join(dirty, "results/product/x.json"), "w", encoding="utf-8") as fh:
        fh.write("{}\n")
    assert scope_main(["--repo-root", dirty]) == 1
    out = capsys.readouterr().out
    assert "results/product/x.json" in out
    assert scope_main(["--repo-root", dirty, "--quiet"]) == 1
    assert capsys.readouterr().out == ""

    # --json prints the full payload and still exits 1
    assert scope_main(["--repo-root", dirty, "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["violations"] == ["results/product/x.json"]
    assert payload["allowed_prefixes"] == list(allowed_prefixes())

    # git error (not a repository) -> 2
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    assert scope_main(["--repo-root", str(not_a_repo)]) == 2
    assert capsys.readouterr().err


# ------------------------------------------------------------- anti-drift: CI

def _workflow_scope_patterns(repo_root: str) -> set[str]:
    """Exact pattern set of the case statement in the "Enforce team scope" step."""
    path = os.path.join(repo_root, ".github", "workflows", "frontier-team.yml")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("- name: Enforce team scope")
    end = text.index("- name:", start + len("- name:"))  # next step ("Persist team snapshot")
    step = text[start:end]
    # The case arms are terminated by the shell's `case ... in <arms>) ;;`.  The
    # workflow writes its last (empty-string) arm as `""` with the terminator
    # glued to it -- literally `|"") ;;` -- so the arm list must be cut at the
    # `)` and NOT at the first ` ;;`, otherwise the final token parses as `"")`
    # and the empty-string arm is mis-read.  re.S so a re-indented or wrapped
    # workflow still parses.
    m = re.search(r'case "\$p" in\s*(.*?)\)\s*;;', step, re.S)
    assert m, "case allow-list not found inside the Enforce team scope step"
    patterns: set[str] = set()
    for token in m.group(1).split("|"):
        token = token.strip()
        assert token, f"empty pattern token in {m.group(1)!r}"
        # shell's empty-string pattern is the two-character literal ""
        patterns.add("" if token == '""' else token)
    return patterns


def test_allowed_prefixes_exactly_equal_the_workflow_allowlist(repo_root):
    """Fails if either side is widened (or narrowed) without the other.

    Exact-set equality: the patterns extracted from the workflow's
    `case "$p" in ... ;;` must equal the patterns derived from
    allowed_prefixes() (plus the workflow's "" catch-all).
    """
    from frontier_counter_label_integrity.scope_guard import WORKFLOW_REL

    assert os.path.isfile(os.path.join(repo_root, WORKFLOW_REL))
    workflow_patterns = _workflow_scope_patterns(repo_root)
    assert "" in workflow_patterns, "the workflow case must keep its empty-string arm"

    derived: set[str] = {""}
    for entry in allowed_prefixes():
        e = entry.replace(TEAM, "$TEAM")
        if e.endswith("/"):
            derived.add(f'"{e[:-1]}"/*')
        else:
            derived.add(f'"{e}"')

    # Explicit cardinality, so a truncated or over-broad parse fails with a clear
    # message instead of only as a set mismatch.  Six allow-list patterns + the
    # workflow's empty-string catch-all.
    assert len(workflow_patterns) == 7, (
        f"expected 6 allow-list patterns + the empty-string arm, parsed "
        f"{len(workflow_patterns)}: {sorted(workflow_patterns)}"
    )
    assert workflow_patterns == derived, (
        "workflow allow-list drifted from scope_guard.allowed_prefixes(): "
        f"only_in_workflow={sorted(workflow_patterns - derived)} "
        f"only_in_guard={sorted(derived - workflow_patterns)}"
    )
    # every prefix must also appear verbatim in the workflow file
    with open(os.path.join(repo_root, ".github", "workflows", "frontier-team.yml"),
              encoding="utf-8") as fh:
        text = fh.read()
    for entry in allowed_prefixes():
        assert entry.replace(TEAM, "$TEAM").rstrip("/") in text


# ------------------------------------------------------------- CLI integration

def _cli_env() -> dict:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = HARNESS_DIR + (os.pathsep + existing if existing else "")
    return env


def test_cli_scope_check_mode_on_real_repo(repo_root, tmp_path):
    """python3 -m ...cli --scope-check --out <tmp>: exit 0, --out untouched."""
    out = tmp_path / "out"
    proc = subprocess.run(
        [sys.executable, "-m", "frontier_counter_label_integrity.cli",
         "--scope-check", "--out", str(out)],
        cwd=repo_root, env=_cli_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "scope ok" in proc.stdout
    assert not out.exists(), "--out must not be touched by --scope-check"

    # frozen rules are irrelevant to this mode
    proc = subprocess.run(
        [sys.executable, "-m", "frontier_counter_label_integrity.cli",
         "--frozen-rules", str(tmp_path / "missing_RULES.json"),
         "--scope-check", "--out", str(out)],
        cwd=repo_root, env=_cli_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert not out.exists()

    # no violations at this moment, verified in-process too
    result = check_repo_scope(repo_root)
    assert result["violations"] == []
    assert result["ok"] is True
    assert result["allowed_prefixes"] == list(allowed_prefixes())
