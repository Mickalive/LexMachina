"""Tests for the round-1 repair of rejected evaluation cycle 39986080045.

Independent audit ``results/audit/evaluation/CYCLE_39986080045_GATE.json``
(gate=REVISE, repair round 0) ordered exactly three required fixes:

* **D-A** (material) — the frozen success rule states "(float tolerance 1e-6)"
  literally while the instrument compared floats at 5e-4, and the instrument's
  docstring/``FLOAT_TOL`` constant misstated the implementation.
* **D-B** (material) — the multilingual reuse record's two schema-completeness
  claims were factually wrong against the packet bytes.
* **D-C** (cosmetic) — two identical "Ordered item 4" report sections.

Every expectation below is either (a) the audit's own required-fix wording,
(b) the frozen hypothesis's literal rule, or (c) arithmetic recomputed from the
committed artifacts without reusing the instrument under test.

SCOPE / NON-WEAKENING CONTRACT
--------------------------------
* No frozen rule, rubric, bar, threshold or success rule is re-derived, edited
  or re-scored here — the hypothesis and frozen rules are only RE-HASHED.
* No falsification is re-executed by these tests; the committed falsification
  record's outcomes are asserted unchanged.
* Mount-dependent byte recomputation and the idempotency rerun skip with an
  explicit reason when the ephemeral product mount is absent (never a pass);
  the mount-free tests still pin every committed claim.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
RUN_ID = "39986080045"
OUT_DIR = REPO / f"results/evaluation/v65_currency_crosscheck"
RUN_JSON = OUT_DIR / f"{RUN_ID}.json"
MULTILINGUAL_JSON = OUT_DIR / f"{RUN_ID}_multilingual_provenance_reuse.json"
REPAIR_LOG = OUT_DIR / f"{RUN_ID}_repair_round1.json"
ENGINE_RECORD = OUT_DIR / f"falsification" / f"{RUN_ID}_engine_mapping_free_recall_falsifier.json"
FALSIFICATION_RECORD = OUT_DIR / f"falsification" / f"{RUN_ID}.json"
REPORT = REPO / f"reports/evaluation/V65_CURRENCY_CROSSCHECK_{RUN_ID}.md"
INSTRUMENT = REPO / "evaluation/v65_currency_crosscheck.py"
REPAIR_INSTRUMENT = REPO / "evaluation/v65_repair_round1_da_db.py"
MOUNT = Path("/tmp/lex_accepted/product")
QUESTIONS_DIR = MOUNT / f"results/product/gate_packet/39319405429/questions"

FROZEN_PINS = {
    REPO / "evaluation/V65_CURRENCY_CROSSCHECK_HYPOTHESIS_V1.json":
        "34fbbe1ad7c83b47d31146690631fdc0c105fff39150be1e532d2a85710a82a2",
    REPO / "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
}
PACKET_PIN = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
EXPECTED_LANGUAGE_NULL = {
    "de-kapitalverletzung": 50, "fr-bail-entretien": 37, "it-responsabilita-medica": 47}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# D-A: the instrument discloses BOTH tolerances and no longer misstates itself
# ---------------------------------------------------------------------------

def test_instrument_constants_and_docstring_are_honest_about_tolerance():
    """Audit D-A: docstring + constant said 1e-6 while the code used 5e-4."""
    src = INSTRUMENT.read_text(encoding="utf-8")
    # the false single-constant claim is gone ...
    assert "\nFLOAT_TOL = 1e-6\n" not in src, "false FLOAT_TOL constant resurfaced"
    assert "compared at 1e-6 float tolerance" not in src, "false docstring resurfaced"
    # ... and both real tolerances exist, are documented and are USED
    sys.path.insert(0, str(REPO))
    import evaluation.v65_currency_crosscheck as mod
    assert mod.FROZEN_LITERAL_FLOAT_TOL == 1e-6
    assert mod.APPLIED_FLOAT_TOL == 5e-4
    assert mod.PUBLICATION_DECIMALS == 3
    # the docstring must state the deviation explicitly (audit wording)
    assert "FLOAT-COMPARISON DISCLOSURE" in src
    assert "float tolerance 1e-6" in src
    assert "half-ulp" in src
    # both tolerances are consumed through the named constants at every real
    # comparison site; the only bare-literal occurrences left are inside the
    # disclosure prose string (self-describing reproduction of the two rules)
    assert "APPLIED_FLOAT_TOL" in src and "FROZEN_LITERAL_FLOAT_TOL" in src
    prose = "strict = delta <= 1e-6, applied = delta <= 5e-4"
    assert src.count("<= 5e-4") == 1 and prose in src
    assert src.count("<= 1e-6") == 1 and prose in src
    assert "<= APPLIED_FLOAT_TOL" in src and "<= FROZEN_LITERAL_FLOAT_TOL" in src


def test_strict_and_applied_verdicts_recompute_independently():
    """Recompute both verdicts from the committed raw values, without importing
    the instrument: strict 1e-6 must give 24/4, applied 5e-4 must give 28/0."""
    doc = _load(RUN_JSON)
    cc = doc["currency_crosscheck"]
    rows = cc["rows"]
    assert len(rows) == 28

    strict_conf = strict_div = app_conf = app_div = 0
    float_rows = []
    for row in rows:
        assert row["verdict"] in ("CONFIRMED", "DIVERGENT", "NOT_FOUND")
        if row["kind"] == "float":
            delta = abs(float(row["raw_found"]) - float(row["raw_published"]))
            float_rows.append((row, delta))
            strict_ok = delta <= 1e-6
            applied_ok = delta <= 5e-4
        else:
            strict_ok = applied_ok = row["verdict"] == "CONFIRMED"
        strict_conf += bool(strict_ok)
        strict_div += not strict_ok and row["verdict"] != "NOT_FOUND"
        app_conf += bool(applied_ok)
        app_div += not applied_ok and row["verdict"] != "NOT_FOUND"

    assert (strict_conf, strict_div) == (24, 4), (strict_conf, strict_div)
    assert (app_conf, app_div) == (28, 0), (app_conf, app_div)

    disc = cc["float_comparison_disclosure"]
    assert disc["counts_frozen_literal_1e_6"] == {
        "n_confirmed": 24, "n_divergent": 4, "n_not_found": 0}
    assert disc["counts_applied_precision_matched"] == {
        "n_confirmed": 28, "n_divergent": 0, "n_not_found": 0}
    assert disc["headline_frozen_literal_1e_6"] == "DIVERGENCE_PRESENT"
    assert disc["headline_applied_precision_matched"] == "ALL_CONFIRMED"
    assert disc["frozen_literal_tolerance"] == 1e-6
    assert disc["applied_tolerance"] == 5e-4
    assert disc["deviation_from_literal_frozen_rule"] is True
    assert disc["deviation_disclosed_not_absorbed"] is True
    assert disc["frozen_rule_edited"] is False
    assert disc["n_float_quantities"] == len(float_rows) == 7

    # the four divergent-under-strict quantities carry their raw deltas
    divergent = [f for f in disc["float_quantities"]
                 if f["strict_verdict_1e_6"] == "DIVERGENT"]
    assert len(divergent) == 4
    for f in divergent:
        assert 1e-6 < f["abs_delta"] <= 5e-4, f
        assert f["applied_verdict_precision_matched"] == "CONFIRMED"
        assert f["round_found_to_3dp_equals_published"] is True
    # published-vs-found pairs match the audit's own four values
    assert {round(f["published_3dp"], 3) for f in divergent} == {0.857, 0.667, 0.571, 0.286}
    # and every float row dual-reports inline as well
    for row, _delta in float_rows:
        assert "strict_verdict_1e_6" in row and "applied_verdict_precision_matched" in row


def test_strict_leg_control_is_not_vacuous():
    """Control: the strict 1e-6 leg must actually discriminate (otherwise the
    published 24/4 split would be an unfalsifiable decoration)."""
    sys.path.insert(0, str(REPO))
    from evaluation.v65_currency_crosscheck import build_float_disclosure

    def _row(delta):
        return {"id": "ctl", "kind": "float", "verdict": "CONFIRMED",
                "raw_found": 1.0 + delta, "raw_published": 1.0,
                "found": 1.0 + delta, "published": 1.0}

    just_above = build_float_disclosure([_row(1.5e-6)])
    assert just_above["float_quantities"][0]["strict_verdict_1e_6"] == "DIVERGENT"
    assert just_above["float_quantities"][0]["applied_verdict_precision_matched"] == "CONFIRMED"
    way_off = build_float_disclosure([dict(_row(6e-4), verdict="DIVERGENT")])
    assert way_off["float_quantities"][0]["applied_verdict_precision_matched"] == "DIVERGENT"
    exact = build_float_disclosure([_row(0.0)])
    assert exact["float_quantities"][0]["strict_verdict_1e_6"] == "CONFIRMED"


def test_frozen_hypothesis_and_rules_rehash_to_their_pins():
    """The repair may not touch the frozen success rule or either rubric."""
    for path, expected in FROZEN_PINS.items():
        assert _sha256(path) == expected, path
    # repair log proves before == after for every pin
    log = _load(REPAIR_LOG)
    assert log["frozen_pins_unchanged"] is True
    for key, blk in log["frozen_pins_before"].items():
        assert blk["ok"] is True, key
        assert log["frozen_pins_after"][key]["found"] == blk["found"], key
    assert log["falsification_reexecuted"] is False
    assert log["posture_unchanged"] == {
        "human_gate_ready": False, "machine_gate_ready": False,
        "packet_admitted": False, "ready_for_owner_session": False}


def test_run_record_posture_and_repair_block():
    doc = _load(RUN_JSON)
    assert doc["posture_unchanged"] == {
        "human_gate_ready": False, "machine_gate_ready": False,
        "packet_admitted": False, "ready_for_owner_session": False}
    assert doc["verdict"] == "PASS_NO_FALSIFICATION"
    assert doc["repair_round1"]["audit_gate"] == "REVISE"
    assert doc["repair_round1"]["required_fixes_applied"] == ["D-A"]
    assert doc["repair_round1"]["reexecuted"] is False
    assert doc["repair_round1"]["frozen_rule_edited"] is False
    # the falsification block itself is untouched in substance
    fr = doc["falsification_rerun"]
    assert fr["verdict"] == "PRODUCT_FALSIFIED" and fr["exit_code"] == 1
    assert fr["failed_gates_equals_accepted"] is True
    assert fr["input_drift"] == []
    assert fr["n_passed"] == 11 and fr["n_gates"] == 18 and fr["n_failed"] == 4


# ---------------------------------------------------------------------------
# D-B: the multilingual characterization matches the bytes
# ---------------------------------------------------------------------------

def _engine_unlabelled() -> dict:
    """Read the committed engine record's per-qid UNLABELLED counts (mount-free)."""
    engine = _load(ENGINE_RECORD)
    found: dict = {}

    def walk(obj):
        if isinstance(obj, dict):
            g = obj.get("gate")
            if isinstance(g, str):
                for qid in QIDS:
                    if g.endswith("::" + qid):
                        meas = obj.get("measured") or {}
                        ld = meas.get("language_distribution")
                        if isinstance(ld, dict) and "UNLABELLED" in ld:
                            found.setdefault(qid, set()).add(ld["UNLABELLED"])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(engine)
    assert all(len(v) == 1 for v in found.values()), found
    return {q: next(iter(v)) for q, v in found.items()}


def test_multilingual_record_interpretation_matches_recorded_byte_facts():
    doc = _load(MULTILINGUAL_JSON)
    interp = doc["interpretation"]
    # (ii) retracted: top-level query EXISTS, only provenance.query is absent
    assert "the provenance block has NO 'query' key" in interp
    assert "the top-level 'query' field DOES exist" in interp
    assert "factually WRONG" in interp and "retracted" in interp
    assert doc["top_level_query_field_present"] is True
    assert doc["provenance_query_key_present"] is False
    # (i) corrected: language key present with explicit nulls, exact counts
    assert "every decision carries a 'language' key" in interp
    assert ("de-kapitalverletzung 50, fr-bail-entretien 37, "
            "it-responsabilita-medica 47") in interp
    facts = doc["byte_recomputation_at_repair"]["facts"]
    assert {q: facts[q]["n_language_null"] for q in QIDS} == EXPECTED_LANGUAGE_NULL
    for qid in QIDS:
        assert facts[qid]["n_language_key_absent"] == 0
        assert facts[qid]["top_level_query_field_present"] is True
        assert facts[qid]["provenance_query_key_present"] is False
        assert facts[qid]["null_equals_engine_predicate"] is True
        assert facts[qid]["null_equals_engine_record_unlabelled"] is True
    # cross-check 1: null counts equal the committed engine UNABELLED counts
    assert EXPECTED_LANGUAGE_NULL == _engine_unlabelled()
    for qid in QIDS:
        assert facts[qid]["null_equals_engine_record_unlabelled"] is True
        assert facts[qid]["n_language_null"] == facts[qid]["n_engine_unlabelled_predicate"]
        assert facts[qid]["n_language_null"] == facts[qid]["engine_record_unlabelled"]
    # cross-check 2: bundle SHAs equal the V61 pins carried by the rows
    for row in doc["rows"]:
        assert row["sha_matches_frozen"] is True
        assert facts[row["qid"]]["bundle_sha256"] == row["bundle_sha256"]
        assert row["n_language_null"] == EXPECTED_LANGUAGE_NULL[row["qid"]]
        assert row["n_decisions"] == facts[row["qid"]]["n_decisions"]
        assert row["script_query_field_present_semantics"].startswith("provenance-block")
    # the V61 script itself is unchanged (REUSE-FIRST)
    script = REPO / "evaluation/run_v3_multilingual_provenance_reuse.py"
    assert '"query" in bundle["provenance"]' in script.read_text(encoding="utf-8")


def test_recomputed_byte_facts_match_the_live_packet_bytes():
    """Mount-dependent byte verification of D-B; skips (never passes) when the
    ephemeral product mount is absent."""
    if not QUESTIONS_DIR.is_dir():
        pytest.skip(f"product mount absent at {QUESTIONS_DIR}; "
                    "byte recomputation covered by the committed "
                    "byte_recomputation_at_repair block instead")
    packet = MOUNT / "results/product/gate_packet/39319405429/packet.json"
    assert _sha256(packet) == PACKET_PIN
    facts = _load(MULTILINGUAL_JSON)["byte_recomputation_at_repair"]["facts"]
    for qid in QIDS:
        raw = (QUESTIONS_DIR / f"{qid}.bundle.json").read_bytes()
        bundle = json.loads(raw)
        assert hashlib.sha256(raw).hexdigest() == facts[qid]["bundle_sha256"]
        decs = bundle["decisions"]
        assert "query" in bundle and isinstance(bundle["query"], str) and bundle["query"]
        assert "query" not in bundle["provenance"]
        assert sum(1 for d in decs if d.get("language") is None) == \
            EXPECTED_LANGUAGE_NULL[qid]
        assert sum(1 for d in decs if "language" not in d) == 0


# ---------------------------------------------------------------------------
# D-C + report wording
# ---------------------------------------------------------------------------

def test_report_discloses_both_verdicts_and_has_single_item4_section():
    text = REPORT.read_text(encoding="utf-8")
    # D-A disclosure present with both headlines and the deltas
    assert "Float-comparison disclosure (audit defect D-A" in text
    assert "**DIVERGENCE_PRESENT** (CONFIRMED 24, DIVERGENT 4, NOT_FOUND 0)" in text
    assert "applied precision-matched (5e-4)" in text
    assert "half-ulp" in text and "never edited" in text
    for delta in ("1.429e-04", "3.330e-04", "4.286e-04", "2.860e-04"):
        assert delta in text, delta
    # D-C: exactly one "Ordered item 4" section remains
    assert text.count("## Ordered item 4") == 1, text.count("## Ordered item 4")
    # D-B: the original false bullet is gone, the corrected facts are present
    original_false_bullet = (
        "(i) one decision per bundle lacks the `language` field "
        "(bge_126 V 75 / bger_4A_173_2017 / bge_130 V 229); "
        "(ii) the bundle has no top-level `query` field.")
    assert original_false_bullet not in text, "D-B false claim still in report"
    assert "the `provenance` block has no `query` key" in text
    assert "de 50 / fr 37 / it 47" in text
    assert "is retracted" in text
    # repair record exists and names all three fixes
    assert "Repair record — round 1 of run 39986080045" in text
    for fix in ("**D-A**", "**D-B**", "**D-C**"):
        assert fix in text
    # posture claims unchanged
    assert "human_gate_ready=false" in text


# ---------------------------------------------------------------------------
# Falsification evidence + attempt history stay intact (never re-run, never lost)
# ---------------------------------------------------------------------------

def test_falsification_record_and_attempt_history_untouched():
    fr = _load(FALSIFICATION_RECORD)
    assert fr["verdict"] == "PRODUCT_FALSIFIED"
    eng = _load(ENGINE_RECORD)
    assert eng["input_drift"] == []
    accepted = {
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    }
    failed = {e.get("gate") for e in fr.get("failed_gates", [])}
    assert failed == accepted, failed
    for attempt in ("attempt1_preserved", "attempt2_preserved", "attempt3_preserved"):
        assert (OUT_DIR / attempt).is_dir(), attempt


def test_repair_instrument_reruns_byte_identempotently():
    """The repair must be a real, idempotent executable delta: rerunning it must
    rewrite byte-identical artifacts (and must never mutate them)."""
    if not QUESTIONS_DIR.is_dir():
        pytest.skip(f"product mount absent at {QUESTIONS_DIR}; "
                    "idempotency of the repair instrument not re-verifiable here")
    targets = [RUN_JSON, MULTILINGUAL_JSON, REPAIR_LOG]
    before = {p: _sha256(p) for p in targets}
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.v65_repair_round1_da_db"],
        cwd=REPO, capture_output=True, text=True, timeout=300)
    after = {p: _sha256(p) for p in targets}
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"verdict": "REPAIR_APPLIED_D_A_D_B"' in proc.stdout
    assert before == after, {
        "non_idempotent": [str(p) for p in targets if before[p] != after[p]]}


def test_state_discipline_not_prestaged_as_accepted():
    state = _load(REPO / "state/evaluation.json")
    assert state["acceptance_status"] == "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    assert state["lane"] == "evaluation"
    assert state["direction_version"] == 65
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False
    repair = state.get("repair_round1_39986080045") or {}
    assert repair.get("required_fixes_applied") == ["D-A", "D-B", "D-C"]
    assert repair.get("falsification_reexecuted") is False
    assert repair.get("frozen_rules_edited") is False
