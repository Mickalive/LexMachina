"""Tests for evaluation/report_claim_check.py.

Audit CYCLE_39164900837 F2 rejected a report that printed fabricated digests
(`a1b2c3d4...`) because nothing compared them against the bytes on disk.  The
lane's guard for that is hard-coded to one run's report path and skips for every
other cycle; these tests cover the re-usable instrument that closes the gap for
the current cycle.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evaluation.report_claim_check import check_report, sha256_file

REPO = Path(__file__).resolve().parent.parent.parent
REPORT = REPO / "reports/evaluation/CYCLE_39200567493_REPAIR.md"
SHIM = REPO / "results/evaluation/orchestration/39200567493_pytest_shim.json"


def test_the_current_report_reproduces_every_checkable_claim():
    res = check_report(REPORT, REPO)
    assert res["pass"], res
    assert res["n_digest_rows"] >= 10, res["n_digest_rows"]
    assert res["digest_problems"] == [] and res["numeric_problems"] == []
    assert res["placeholder_hits"] == []


def test_the_claim_check_detects_a_fabricated_digest():
    forged = REPO / "results/evaluation/_scratch_namespaced/_forged_report_probe.md"
    forged.write_text(
        "| `evaluation/frozen_bars/RULES_LABEL.json` | "
        + "a1b2c3d4" * 8 + " |\n", encoding="utf-8")
    try:
        res = check_report(forged, REPO)
        assert res["pass"] is False
        assert any("digest mismatch" in p for p in res["digest_problems"])
    finally:
        forged.unlink()


def test_the_claim_check_detects_a_withdrawn_claim_asserted_again():
    forged = REPO / "results/evaluation/_scratch_namespaced/_forged_claim_probe.md"
    forged.write_text(
        "| `evaluation/frozen_bars/RULES_LABEL.json` | "
        + sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json") + " |\n"
        "All core evaluation tests pass\n", encoding="utf-8")
    try:
        res = check_report(forged, REPO)
        assert res["pass"] is False
        assert any("withdrawn phrase asserted" in p for p in res["numeric_problems"])
    finally:
        forged.unlink()


def test_a_quoted_withdrawn_phrase_is_disclosure_not_a_claim():
    forged = REPO / "results/evaluation/_scratch_namespaced/_quoted_claim_probe.md"
    forged.write_text(
        "| `evaluation/frozen_bars/RULES_LABEL.json` | "
        + sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json") + " |\n"
        'the rejected report said "All core evaluation tests pass"\n', encoding="utf-8")
    try:
        res = check_report(forged, REPO)
        # The probe report intentionally omits this cycle's numeric claims, so
        # only the withdrawn-phrase axis is asserted here.
        assert not any("withdrawn phrase" in p for p in res["numeric_problems"]), \
            res["numeric_problems"]
    finally:
        forged.unlink()


def test_the_claim_check_fails_when_a_numeric_claim_drifts():
    forged = REPO / "results/evaluation/_scratch_namespaced/_numeric_claim_probe.md"
    forged.write_text(
        "| `evaluation/frozen_bars/RULES_LABEL.json` | "
        + sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json") + " |\n"
        "| Cases passed | **999999** |\n", encoding="utf-8")
    try:
        res = check_report(forged, REPO)
        assert res["pass"] is False
        assert any("Cases passed" in p for p in res["numeric_problems"])
    finally:
        forged.unlink()


def test_the_frozen_spec_digests_are_still_the_pinned_ones():
    for rel, pinned in (
        ("evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
         "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"),
        ("evaluation/retrieval_gate/FREEZE_RECORD.json",
         "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49"),
        ("evaluation/frozen_bars/RULES_LABEL.json",
         "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"),
        ("evaluation/frozen_bars/RULES_GEOMETRY.json",
         "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"),
    ):
        assert sha256_file(REPO / rel) == pinned, rel


def test_the_full_suite_verdict_in_the_report_is_the_record_verdict():
    shim = json.loads(SHIM.read_text(encoding="utf-8"))
    assert shim["verdict"] == "SHIM_FAIL", shim["verdict"]
    text = REPORT.read_text(encoding="utf-8")
    assert f"**{shim['n_passed']}**" in text
    assert f"NOT-RUN** | **{shim['n_unsupported']}**" in text


def test_the_instrument_runs_as_a_subprocess_with_exit_zero():
    proc = subprocess.run(
        [sys.executable, "evaluation/report_claim_check.py",
         "--report", "reports/evaluation/CYCLE_39200567493_REPAIR.md"],
        cwd=str(REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["pass"] is True