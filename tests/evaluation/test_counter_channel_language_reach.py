"""Tests for the counter-channel single-language reach instrument.

Every scratch invocation of the engine passes ``--out`` / ``--report`` into a
temporary directory (SCRATCH-RUN OBLIGATION) so a test can never rewrite the
committed claim-bearing record.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import counter_channel_language_reach as ENGINE  # noqa: E402
from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402

SPEC_PATH = REPO_ROOT / ENGINE.SPEC_RELPATH
RECORD_PATH = REPO_ROOT / ENGINE.RECORD_RELPATH
HYP_PATH = REPO_ROOT / ENGINE.HYPOTHESIS_RELPATH
FREEZE_PATH = REPO_ROOT / ENGINE.FREEZE_RECORD_RELPATH
COMMITTED_RESULT = REPO_ROOT / ENGINE.DEFAULT_OUT


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# frozen rule classification (pure function)
# --------------------------------------------------------------------------- #
def test_rule_reach_lost_when_one_language_zero():
    hits = {"fr": ["a"], "de": ["a"], "it": []}
    resp = {l: {"status": 200, "n_rows": 30} for l in rg_frozen.LANGUAGES}
    assert ENGINE.classify(hits, ["a", "b"], resp) == ENGINE.CLASS_REACH_LOST


def test_rule_reach_held_when_every_language_hits_at_least_one():
    hits = {"fr": ["a"], "de": ["b"], "it": ["c"]}
    resp = {l: {"status": 200, "n_rows": 30} for l in rg_frozen.LANGUAGES}
    assert ENGINE.classify(hits, ["a", "b", "c"], resp) == ENGINE.CLASS_REACH_HELD


def test_rule_not_measured_on_empty_frozen_set_even_if_all_zero():
    resp = {l: {"status": 200, "n_rows": 30} for l in rg_frozen.LANGUAGES}
    assert ENGINE.classify({"fr": [], "de": [], "it": []}, [], resp) == \
        ENGINE.CLASS_NM_EMPTY_SET


def test_rule_not_measured_when_a_counter_query_is_unanswered():
    hits = {"fr": ["a"], "de": ["a"], "it": ["a"]}
    resp = {l: {"status": 200, "n_rows": 30} for l in rg_frozen.LANGUAGES}
    resp["it"] = {"status": 503, "n_rows": 0}
    assert ENGINE.classify(hits, ["a"], resp) == ENGINE.CLASS_NM_NO_RESPONSE


# --------------------------------------------------------------------------- #
# measurement on the pinned accepted record
# --------------------------------------------------------------------------- #
def test_measure_is_deterministic_on_the_pinned_record():
    a = ENGINE.measure(_spec(), _record())
    b = ENGINE.measure(_spec(), _record())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["n_slugs"] == 4


def test_measure_reports_every_language_row_count_and_never_invents_hits():
    res = ENGINE.measure(_spec(), _record())
    spec = _spec()
    for s in res["slugs"]:
        known = set(s["known_counter_ids"])
        assert s["n_known"] == len(known)
        for lang in rg_frozen.LANGUAGES:
            cell = s["per_language"][lang]
            assert set(cell["hits"]) <= known
            assert set(cell["hits"]) | set(cell["missing"]) == known or not known
            assert cell["n_hits"] == len(cell["hits"])
        # classification must agree with the frozen rule applied to its own cells
        resp = {l: {"status": s["per_language"][l]["status"],
                    "n_rows": s["per_language"][l]["n_rows"]} for l in rg_frozen.LANGUAGES}
        hits = {l: s["per_language"][l]["hits"] for l in rg_frozen.LANGUAGES}
        assert s["classification"] == ENGINE.classify(hits, s["known_counter_ids"], resp)


def test_decomposition_union_is_subset_of_accepted_pooled_gate():
    res = ENGINE.measure(_spec(), _record())
    for s in res["slugs"]:
        d = s["decomposition"]
        assert d["accepted_pooled_gate_present"] is True
        assert d["counter_union_not_in_pooled"] == []
        pooled = set(d["accepted_pooled_gate_hits"])
        union = set(d["counter_channel_union_hits"])
        assert union <= pooled


def test_baseline_language_cells_are_republished_read_only():
    res = ENGINE.measure(_spec(), _record())
    for s in res["slugs"]:
        cells = s["republished_baseline_language_cells"]
        for lang, cell in cells.items():
            assert cell["republished_not_redecided"] is True
            assert lang in rg_frozen.LANGUAGES


# --------------------------------------------------------------------------- #
# non-vacuity controls
# --------------------------------------------------------------------------- #
def test_controls_all_hold_on_the_pinned_record():
    for c in ENGINE.controls(_spec(), _record()):
        assert c["holds"], f"control {c['control']} did not hold: {c['measured']}"


def test_c1_missing_response_is_never_a_product_verdict():
    spec = _spec()
    rec = _record()
    rec["queries"] = [
        dict(q, rows=[], status=503, error="simulated") if q.get("channel") == "counter"
        else q for q in rec["queries"]
    ]
    res = ENGINE.measure(spec, rec)
    for s in res["slugs"]:
        assert s["classification"] == ENGINE.CLASS_NM_NO_RESPONSE
    assert res["n_reach_lost"] == 0
    assert res["n_measured"] == 0


def test_c3_oracle_flip_both_directions():
    spec = _spec()
    rec = _record()
    full = ENGINE._oracle_counter_record(spec, rec, tuple(rg_frozen.LANGUAGES))
    held = ENGINE.measure(spec, full)
    assert held["n_reach_lost"] == 0
    assert held["n_measured"] == 4
    minus = ENGINE._oracle_counter_record(spec, rec, ("fr", "de"))
    lost = ENGINE.measure(spec, minus)
    assert lost["n_reach_lost"] == 4
    # the IT query stays answered with rows, so the flip is a reach loss, never
    # a NOT_MEASURED artefact
    for s in lost["slugs"]:
        it = s["per_language"]["it"]
        assert it["status"] == 200 and it["n_rows"] > 0 and it["n_hits"] == 0


# --------------------------------------------------------------------------- #
# verdict / exit codes
# --------------------------------------------------------------------------- #
def _controls_ok() -> list[dict]:
    return [{"control": "c", "holds": True, "why": "", "measured": {}}]


def test_verdict_environment_on_pin_drift():
    v = ENGINE.verdict_of({"n_measured": 4, "n_reach_lost": 0,
                           "reach_lost_slugs": []}, _controls_ok(), False)
    assert v["exit_code"] == ENGINE.EXIT_ENVIRONMENT
    assert v["verdict"] == "ENVIRONMENT_OR_VACUOUS"


def test_verdict_environment_when_control_fails():
    v = ENGINE.verdict_of({"n_measured": 4, "n_reach_lost": 0, "reach_lost_slugs": []},
                          [{"control": "C3", "holds": False, "why": "", "measured": {}}],
                          True)
    assert v["exit_code"] == ENGINE.EXIT_ENVIRONMENT


def test_verdict_lost_and_held_are_distinguishable():
    lost = ENGINE.verdict_of({"n_measured": 4, "n_reach_lost": 1,
                              "reach_lost_slugs": ["x"]}, _controls_ok(), True)
    held = ENGINE.verdict_of({"n_measured": 4, "n_reach_lost": 0,
                              "reach_lost_slugs": []}, _controls_ok(), True)
    assert lost["exit_code"] == ENGINE.EXIT_LOST
    assert held["exit_code"] == ENGINE.EXIT_HELD
    assert lost["verdict"] != held["verdict"]


# --------------------------------------------------------------------------- #
# freeze discipline + full scratch run
# --------------------------------------------------------------------------- #
def test_freeze_record_pins_the_accepted_inputs():
    assert HYP_PATH.is_file(), "hypothesis must be committed before execution"
    assert FREEZE_PATH.is_file(), "freeze record must be written before execution"
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    pins = freeze["pins"]
    import hashlib
    for rel, expected in pins.items():
        path = REPO_ROOT / rel
        assert path.is_file(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel
    # the frozen retrieval spec sha must be the standing accepted one
    assert pins[ENGINE.SPEC_RELPATH] == \
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"


def test_full_run_scratch_is_reproducible_and_writes_nothing_claim_bearing():
    """Scratch run: ``--out``/``--report`` are redirected into a temporary
    directory so no committed claim-bearing record can be rewritten (the
    SCRATCH-RUN OBLIGATION of the engine's own docstring)."""
    assert HYP_PATH.is_file() and FREEZE_PATH.is_file()
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        out = tmp_path / "scratch.json"
        report = tmp_path / "scratch.md"
        result, exit_code = ENGINE.run(SPEC_PATH, RECORD_PATH, HYP_PATH, FREEZE_PATH, out,
                                       report, "scratch")
        assert exit_code in (ENGINE.EXIT_HELD, ENGINE.EXIT_LOST, ENGINE.EXIT_ENVIRONMENT)
        assert result["pins"]["ok"] is True
        assert result["post_execution_pins"]["ok"] is True
        assert out.is_file() and report.is_file()
        # re-run reproduces the same classification set byte-for-byte
        out2 = tmp_path / "scratch2.json"
        report2 = tmp_path / "scratch2.md"
        result2, exit2 = ENGINE.run(SPEC_PATH, RECORD_PATH, HYP_PATH, FREEZE_PATH, out2,
                                    report2, "scratch2")
        assert exit2 == exit_code
        assert json.dumps(result["measurement"], sort_keys=True) == \
            json.dumps(result2["measurement"], sort_keys=True)


def test_committed_result_if_present_reproduces_from_pinned_inputs():
    """Reproducibility of the committed record: same pinned inputs -> same
    measurement.  Skipped until the claim-bearing run exists."""
    if not COMMITTED_RESULT.is_file():
        pytest.skip("committed claim-bearing result not produced yet")
    committed = json.loads(COMMITTED_RESULT.read_text(encoding="utf-8"))
    live = ENGINE.measure(_spec(), _record())
    assert json.dumps(live, sort_keys=True) == \
        json.dumps(committed["measurement"], sort_keys=True)
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        _, exit_code = ENGINE.run(SPEC_PATH, RECORD_PATH, HYP_PATH, FREEZE_PATH,
                                  tmp_path / "r.json", tmp_path / "r.md", "recheck")
    assert exit_code == committed["verdict"]["exit_code"]


def test_pin_drift_fails_closed():
    """A tampered record must exit 2 and must not emit a product verdict."""
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        tampered = copy.deepcopy(_record())
        tampered["queries"][0]["rows"] = []
        bad_record = tmp_path / "tampered.json"
        bad_record.write_text(json.dumps(tampered), encoding="utf-8")
        out = tmp_path / "drift.json"
        report = tmp_path / "drift.md"
        result, exit_code = ENGINE.run(SPEC_PATH, bad_record, HYP_PATH, FREEZE_PATH, out,
                                       report, "drift")
        assert exit_code == ENGINE.EXIT_ENVIRONMENT
        assert result["pins"]["ok"] is False
        assert result["verdict"]["verdict"] == "ENVIRONMENT_OR_VACUOUS"
        assert result["measurement"]["n_measured"] == 0
