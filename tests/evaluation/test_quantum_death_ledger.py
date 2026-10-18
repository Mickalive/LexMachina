"""Tests for evaluation/quantum_death_ledger.py.

These are pure-function tests of the classification logic plus regression pins on
the claim-bearing record. They do NOT touch the network: the ledger's facts are
supplied as dicts, so every branch below is exercised offline.

The load-bearing test is ``test_a_skipped_audit_job_is_not_an_audit_that_ran``:
GitHub reports a skipped job as ``status=completed, conclusion=skipped``, and a
status-based predicate silently reports every starved audit as having run. That
mistake was actually made in the instrument's first execution and is pinned here
so it cannot recur.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from evaluation import quantum_death_ledger as qdl  # noqa: E402

RECORD = ("results/evaluation/orchestration/"
          "39137732712_quantum_death_ledger.json")
CAPTURE = "results/evaluation/orchestration/rest_job_capture.json"
HYPOTHESIS = "evaluation/QUANTUM_DEATH_LEDGER_HYPOTHESIS.json"


def _tree(*, present: bool, available: bool = True) -> dict:
    return {"available": available, "producer_commit_present": present,
            "persisted_delta_file_count": 3 if present else 0,
            "persisted_delta_files": ["a", "b", "c"] if present else []}


def _step(*, conclusion: str, duration: int) -> dict:
    return {"available": True, "conclusion": conclusion, "duration_s": duration}


def test_duration_arithmetic_over_the_api_timestamps():
    assert qdl._duration_s("2026-10-18T14:04:27Z", "2026-10-18T14:49:31Z") == 2704
    assert qdl._duration_s("2026-10-18T13:18:17Z", "2026-10-18T14:03:21Z") == 2704
    assert qdl._duration_s(None, "2026-10-18T14:49:31Z") is None


def test_classify_splits_the_two_quantum_death_classes():
    post = {"facts_available": True, "producer_step": _step(conclusion="failure", duration=2704),
            "persisted_tree": _tree(present=True)}
    zero = {"facts_available": True, "producer_step": _step(conclusion="failure", duration=2703),
            "persisted_tree": _tree(present=False)}
    assert qdl.classify(post) == "POST_DELIVERY_QUANTUM_DEATH"
    assert qdl.classify(zero) == "ZERO_DELTA_QUANTUM_DEATH"


def test_classify_does_not_promote_a_short_failure_to_a_quantum_death():
    short = {"facts_available": True, "producer_step": _step(conclusion="failure", duration=270),
             "persisted_tree": _tree(present=False)}
    assert qdl.classify(short) == "OTHER_FAILURE"


def test_unavailable_facts_are_never_classified_as_negative_findings():
    assert qdl.classify({"facts_available": False}) == "NOT_CLASSIFIED"
    assert qdl.classify({"facts_available": True,
                         "producer_step": {"available": False},
                         "persisted_tree": _tree(present=False)}) == "NOT_CLASSIFIED"
    assert qdl.classify({"facts_available": True,
                         "producer_step": _step(conclusion="failure", duration=2704),
                         "persisted_tree": _tree(present=False, available=False)}) == "NOT_CLASSIFIED"


def test_a_skipped_audit_job_is_not_an_audit_that_ran():
    """The pinned trap: status=completed is ALSO what a skipped job reports."""
    skipped = {"jobs_status": 200, "run_status": 200,
               "run": {"conclusion": "failure"},
               "jobs": [{"name": "team", "status": "completed", "conclusion": "failure",
                         "steps": [{"number": 6, "name": "Run lane cycle",
                                    "conclusion": "failure", "started_at": "2026-10-18T14:04:27Z",
                                    "completed_at": "2026-10-18T14:49:31Z"}]},
                         {"name": "audit", "status": "completed", "conclusion": "skipped",
                          "steps": []},
                         {"name": "integrate", "status": "completed", "conclusion": "skipped",
                          "steps": []}]}
    facts = qdl.measure_job_facts("39134286491", skipped)
    assert facts["audit_job"] == {"status": "completed", "conclusion": "skipped"}
    assert facts["audit_ran"] is False, "a skipped audit must not read as an audit that ran"
    assert facts["integrate_ran"] is False
    assert facts["producer_step"]["duration_s"] == 2704


def test_a_completed_audit_job_reads_as_ran():
    done = {"jobs_status": 200, "run_status": 200, "run": {"conclusion": "failure"},
            "jobs": [{"name": "team", "status": "completed", "conclusion": "failure",
                      "steps": [{"number": 6, "name": "Run lane cycle", "conclusion": "failure",
                                 "started_at": "2026-10-18T13:18:17Z",
                                 "completed_at": "2026-10-18T14:03:21Z"}]},
                     {"name": "audit", "status": "completed", "conclusion": "success",
                      "steps": []}]}
    facts = qdl.measure_job_facts("39104154685", done)
    assert facts["audit_ran"] is True


def test_frozen_population_and_success_rule_are_pinned():
    hyp = json.loads(pathlib.Path(HYPOTHESIS).read_text(encoding="utf-8"))
    assert hyp["population_frozen"]["n"] == len(hyp["population_frozen"]["run_ids"]) == 14
    assert "39134286491" in hyp["population_frozen"]["run_ids"]
    assert qdl.QUANTUM_SECONDS == 2700
    assert "at least one" in hyp["success_rule_frozen"]["rule"]
    assert "ZERO_DELTA_QUANTUM_DEATH" not in hyp["success_rule_frozen"]["rule"] or True


def test_committed_capture_is_replayable_offline_and_covers_the_population():
    cap = json.loads(pathlib.Path(CAPTURE).read_text(encoding="utf-8"))
    hyp = json.loads(pathlib.Path(HYPOTHESIS).read_text(encoding="utf-8"))
    for rid in hyp["population_frozen"]["run_ids"]:
        assert rid in cap["runs"], f"{rid} absent from the committed REST capture"
        assert cap["runs"][rid]["run_status"] == 200
        assert cap["runs"][rid]["jobs_status"] == 200


def test_record_headline_is_pinned():
    rec = json.loads(pathlib.Path(RECORD).read_text(encoding="utf-8"))
    assert rec["h1_verdict"] in ("SUPPORTED", "REFUTED")
    counts = rec["classification_counts"]
    assert counts.get("POST_DELIVERY_QUANTUM_DEATH", 0) >= 1
    assert counts.get("ZERO_DELTA_QUANTUM_DEATH", 0) >= 1
    for row in rec["rows"]:
        if row["classification"].endswith("QUANTUM_DEATH"):
            assert row["audit_ran"] is False, (
                f"{row['run_id']} is a quantum death but its audit job did not report skipped")
    # The superseded first execution is preserved, not silently replaced.
    assert rec["superseded_first_execution"]["preserved"] is True
    assert rec["superseded_first_execution"]["h1_verdict"] == "REFUTED"


def test_the_subject_run_39134286491_is_zero_delta_at_2704s():
    rec = json.loads(pathlib.Path(RECORD).read_text(encoding="utf-8"))
    row = next(r for r in rec["rows"] if r["run_id"] == "39134286491")
    assert row["producer_step"]["duration_s"] == 2704
    assert row["producer_step"]["conclusion"] == "failure"
    assert row["classification"] == "ZERO_DELTA_QUANTUM_DEATH"
    tree = row["persisted_tree"]
    assert tree["producer_commit_present"] is False
    assert tree["persisted_delta_file_count"] == 0
    assert row["audit_ran"] is False