"""Pin product/audit_handoff.py: one read-only, budgeted auditor handoff.

Why these specific assertions
-----------------------------
Runs 40429931848 and 40436981920 both died in the audit job at
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78) and run 40427889739 died at
``auditor crossed scope:`` (exit 3).  The product lane cannot edit
``.github/**``; what it can do is make its own claims cheap to check and make
an accidental write impossible to miss.  So the harness is pinned on exactly
those two properties:

* ``test_it_writes_nothing_into_the_repository`` - the command's own
  before/after ``git status --porcelain -uall`` must be identical, and the
  published report must carry ``read_only.ok``.
* ``test_it_fails_closed_when_a_check_fails`` - a scope check run in the
  producer checkout with the auditor's scope must FAIL (the producer tree is
  full of in-scope-for-a-producer, out-of-scope-for-an-auditor paths), and the
  process exit code must be non-zero.
* ``test_it_refuses_to_write_inside_the_producer_checkout`` - ``--out`` may
  only target a path outside the repository or the auditor's own two
  directories, so a producer can never use this tool to touch
  ``results/audit/**`` by accident.

Everything else (JSON schema, budget accounting, selection parsing) is cheap
structure that an auditor reading the handoff report relies on.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "product" / "audit_handoff.py"
for _p in (str(ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product import audit_handoff as ah  # noqa: E402


def _porcelain() -> list[str]:
    out = subprocess.run(  # noqa: S603
        ["git", "status", "--porcelain", "-uall"],
        cwd=str(ROOT), capture_output=True, text=True, check=False).stdout
    return sorted(line[3:] for line in out.splitlines() if len(line) > 3)


def _run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(MODULE), *argv],
        cwd=str(ROOT), capture_output=True, text=True, check=False)


def test_module_is_importable_and_declares_its_claim_ceiling():
    report = ah.build(ROOT, checks=("scope",), budget=60.0, dossier=None,
                      scope="producer", tests=None, skip_tests=True)
    assert report["schema"] == "product-audit-handoff/1"
    assert report["claim_ceiling"].startswith("Engineering verification")
    for phrase in ("writes no gate", "scores no frozen bar"):
        assert phrase in report["claim_ceiling"], (
            f"the claim ceiling lost the phrase {phrase!r}")
    assert report["n_checks"] == 1 and report["checks"][0]["check"] == "scope"


def test_it_writes_nothing_into_the_repository():
    """The property run 40427889739 lost its audit ref to."""
    before = _porcelain()
    proc = _run(["--only", "scope", "--scope", "producer", "--json"])
    after = _porcelain()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["read_only"]["ok"] is True, (
        f"the handoff changed the tree: {report['read_only']}")
    assert before == after, "git status moved while the handoff ran"
    assert "_stdout_full" not in json.dumps(report), (
        "the raw sub-tool stream leaked into the published report")


def test_it_fails_closed_when_a_check_fails():
    """A producer checkout is not an audit workspace - and says so."""
    proc = _run(["--only", "scope", "--scope", "audit", "--json"])
    report = json.loads(proc.stdout)
    assert proc.returncode != 0, "an out-of-scope tree must not exit 0"
    assert report["verdict"] == "FAIL"
    scope = next(c for c in report["checks"] if c["check"] == "scope")
    assert scope["status"] == "FAIL"


def test_unknown_selection_is_rejected_before_anything_runs():
    proc = _run(["--only", "nope"])
    assert proc.returncode == 2
    assert "unknown check" in (proc.stderr + proc.stdout)


def test_a_root_without_product_is_rejected(tmp_path: Path):
    proc = _run(["--root", str(tmp_path), "--only", "scope"])
    assert proc.returncode == 2
    assert "no product/" in (proc.stderr + proc.stdout)


def test_it_refuses_to_write_inside_the_producer_checkout():
    inside = ROOT / "results" / "product" / "audit_handoff_should_not_exist.json"
    outside = Path("/tmp") / "lex_audit_handoff_out.json"
    try:
        proc = _run(["--only", "scope", "--scope", "producer",
                     "--out", str(inside)])
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "refusing to write" in proc.stderr
        assert not inside.exists()

        proc = _run(["--only", "scope", "--scope", "producer",
                     "--out", str(outside), "--json"])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert outside.is_file()
        assert json.loads(outside.read_text())["schema"] == (
            "product-audit-handoff/1")
    finally:
        outside.unlink(missing_ok=True)


def test_auditor_directories_are_the_allowed_in_repo_targets():
    root = Path("/repo")
    assert ah._writable_target(Path("/repo/results/audit/product/X.json"),
                               root) is None
    assert ah._writable_target(Path("/repo/reports/audit/product/X.md"),
                               root) is None
    assert ah._writable_target(Path("/elsewhere/handoff.json"), root) is None
    assert ah._writable_target(Path("/repo/results/product/X.json"),
                               root) is not None
    # directory boundary: results/audit/product_backup/ is NOT the scope
    assert ah._writable_target(Path("/repo/results/audit/product_backup/X.json"),
                               root) is not None


def test_budget_is_reported_and_enforced_as_a_fail_not_a_silent_pass(tmp_path: Path):
    """A budget that cannot be met is a FAIL with the elapsed time recorded."""
    report = ah.build(ROOT, checks=("scope",), budget=0.0, dossier=None,
                      scope="producer", tests=None, skip_tests=True)
    # 0 s cannot fit a subprocess: the check fails rather than being skipped.
    assert report["checks"][0]["status"] in {"PASS", "FAIL"}
    assert report["budget_ok"] is False
    assert report["verdict"] == "FAIL"
    assert report["elapsed_s"] >= 0.0


def test_json_tail_parser_reads_a_multi_line_document():
    doc = json.dumps({"a": 1, "b": {"c": [1, 2, 3]}}, indent=2)
    assert ah._parse_json_tail("noise\n" + doc + "\n") == {
        "a": 1, "b": {"c": [1, 2, 3]}}
    assert ah._parse_json_tail("no json here") is None


@pytest.mark.parametrize("name", list(ah.CHECKS))
def test_every_declared_check_has_a_docstring_entry(name: str):
    """CHECKS is the selection vocabulary; each entry must be documented."""
    assert name in ah.__doc__, f"check {name!r} is not described in the docstring"
