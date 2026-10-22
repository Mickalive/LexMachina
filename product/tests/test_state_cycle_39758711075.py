"""What cycle 39758711075 claims about itself, checked against the artifacts.

Why this exists
---------------
The operational resume of producer snapshot 39752638579 inherited a tree whose
lane state was still at direction 61 while the run was dispatched with 62 (the
workflow's state contract exits 69), which carried no report of record, whose
pinned collected-test attribution was 20 tests stale, and whose coverage merge
shipped two docket spellings of the same BGE ruling under one citation. Every
claim this resume makes is re-derived here from the committed tree, never
copied from the report:

* the canonical lane state satisfies the workflow contract at direction 62,
  names this run as current, and keeps every fail-closed flag false;
* remedy (a) is the shipped planner: adversarial_retrieval/3 and the
  placeholder strip are live, and the placeholder's own tokens cannot become
  counter-probe vocabulary;
* the writer-abort degradation code is the accepted attribution code and is
  published as a first-class field with its disclosure status;
* the frozen-text manifest pins the accepted benchmark digest and plans six
  texts per frozen question;
* the committed coverage-replay evidence says what the report quotes: the
  second live pass executed 24/24 texts with zero cache modifications, and the
  offline verify replayed from cache with zero network calls;
* the D4 fix holds: the two observed docket spellings of one ruling collapse
  to one merge identity, prefix stripping is court-scoped, and distinct
  dockets stay distinct;
* the diagnosis artifact names defects D1-D6, each with a reproduce command
  and a disposition;
* the report of record exists and cites the artifacts this module checks;
* the regenerated attribution equals what THIS tree collects and carries a
  cross-check that ran (base_agrees true), with the previous pin preserved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import adversarial_retrieval as ar  # noqa: E402
from product.query import pipeline  # noqa: E402
from product.query import query_texts as qt  # noqa: E402
from product import test_delta_attribution as tda  # noqa: E402

RUN_ID = 39758711075
INHERITED_RUN = 39752638579
STATE_PATH = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
DIAGNOSIS = (ROOT / "results" / "product" / "orchestration"
             / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
ATTRIBUTION = (ROOT / "results" / "product" / "regression"
               / f"CYCLE_{RUN_ID}_test_delta_attribution.json")
LIVE2 = ROOT / "results" / "product" / "coverage_replay" / "LOCAL_LIVE_COVERAGE2_live.json"
OFFLINE_VERIFY = (ROOT / "results" / "product" / "coverage_replay"
                  / "LOCAL_OFFLINE_VERIFY_offline.json")
MOUNTED_DIRECTION = Path("/tmp/lex_control/state/factory_direction.json")


def _state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. the workflow contract the inherited run failed (defect D1)
# --------------------------------------------------------------------------

def test_state_carries_the_dispatched_direction_version():
    expected = None
    if MOUNTED_DIRECTION.is_file():
        expected = json.loads(MOUNTED_DIRECTION.read_text(encoding="utf-8")).get("version")
    if not isinstance(expected, int):
        pytest.skip("mounted control plane not present in this environment")
    st = _state()
    assert st["direction_version"] == expected, (
        f"state direction_version {st['direction_version']} != dispatched {expected}"
    )
    assert st["direction_version"] == 62  # this cycle's disclosed pin


def test_state_names_this_run_and_the_inherited_snapshot():
    st = _state()
    assert st["current_run"] == str(RUN_ID) or st["current_run"] == RUN_ID
    delivery = st[f"cycle_{RUN_ID}_vertical_slice_delivery"]
    assert delivery["inherited_snapshot_commit"].startswith("3b9d33b")
    assert delivery["run_id"] == RUN_ID
    assert st["cycle_status"] == "COMPLETE"
    assert st["continue_recommended"] is True


def test_fail_closed_posture_is_unchanged():
    st = _state()
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    assert isinstance(st["accepted_run_id"], str)
    assert str(RUN_ID) not in str(st["accepted_run_id"])


# --------------------------------------------------------------------------
# 2. ordered item 1: remedy (a) is the shipped planner
# --------------------------------------------------------------------------

def test_remedy_a_is_the_shipped_adversarial_planner():
    assert ar.ADVERSARIAL_RETRIEVAL_VERSION == "adversarial_retrieval/3"
    prose = ("Le preneur doit indemniter le bailleur. "
             + ar.REDACTION_PLACEHOLDER + " La résiliation est abusive.")
    cleaned = ar.strip_redaction_placeholders(prose)
    assert ar.REDACTION_PLACEHOLDER not in cleaned
    assert "indemniter" in cleaned and "resiliation" in cleaned.replace("é", "e")
    terms = ar.answer_key_terms(prose)
    for placeholder_token in ("citation", "removed", "retrieved"):
        assert placeholder_token not in terms, terms


def test_placeholder_strip_is_deterministic_and_non_destructive():
    assert ar.strip_redaction_placeholders("") == ""
    assert ar.strip_redaction_placeholders("no placeholder here") == (
        "no placeholder here"
    )
    # bracket/case drift tolerated, real legal text never removed
    drifted = "Ansicht [  CITATION REMOVED : NOT IN RETRIEVED SET ] 366 OR"
    assert "366" in ar.strip_redaction_placeholders(drifted)


# --------------------------------------------------------------------------
# 3. ordered item 3: the writer-abort degradation field
# --------------------------------------------------------------------------

def test_writer_abort_code_is_the_accepted_attribution_code():
    assert pipeline.WRITER_ABORT_CODE == "e_EMISSION_WRITER_ABORT"
    rec = pipeline._writer_abort_degradation("provider timeout")
    assert rec["code"] == "e_EMISSION_WRITER_ABORT"
    assert rec["stage"] == "generative_writer"
    assert rec["adversarial_pass_status"] == "DEGRADED"
    assert "not measured" in rec["disclosure"] or "never" in rec["disclosure"]


def test_query_html_names_the_abort_in_the_degraded_note():
    html = (ROOT / "product" / "static" / "query.html").read_text(encoding="utf-8")
    assert "e_EMISSION_WRITER_ABORT" in html


# --------------------------------------------------------------------------
# 4. ordered item 2: frozen-text manifest + committed replay evidence
# --------------------------------------------------------------------------

def test_frozen_text_manifest_pins_the_accepted_benchmark():
    data = qt.load_manifest()
    assert data["schema"] == "product-frozen-retrieval-texts/1"
    assert data["source_sha256"].startswith("187b0e54")
    questions = data["questions"]
    assert len(questions) >= 1
    plan = qt.plan_query_texts(questions[0]["queries"]["baseline"]["fr"], manifest=data)
    assert len(plan) == 6
    assert {p["language"] for p in plan} == {"fr", "de", "it"}
    assert {p["channel"] for p in plan} == {"baseline", "counter"}


def test_committed_live_coverage_evidence_matches_the_report_quotes():
    rec = json.loads(LIVE2.read_text(encoding="utf-8"))
    assert rec["n_texts_planned"] == 24
    assert rec["n_texts_executed"] == 24
    assert rec["n_texts_with_rows"] == 24
    assert rec["cache"]["n_modified_existing"] == 0
    assert rec["n_frozen_ids_reached"] == 23


def test_committed_offline_verify_replayed_from_cache_without_network():
    rec = json.loads(OFFLINE_VERIFY.read_text(encoding="utf-8"))
    assert rec["mode"] == "offline"
    assert rec["n_network_calls"] == 0
    assert rec["n_texts_cache_miss"] == 0
    assert rec["n_cache_hits"] == 56


# --------------------------------------------------------------------------
# 5. defect D4: the docket-alias merge regression and its fix
# --------------------------------------------------------------------------

def test_the_two_observed_docket_spellings_collapse_to_one_identity():
    a = {"court": "bge", "docket_number": "142 IV 333",
         "decision_id": "bge_142 IV 333", "canonical_decision_id": "bge_142 IV 333"}
    b = {"court": "bge", "docket_number": "BGE 142 IV 333",
         "decision_id": "bge_BGE_142_IV_333",
         "canonical_decision_id": "bge_BGE_142_IV_333"}
    assert qt._identity(a) == qt._identity(b)


def test_prefix_strip_is_court_scoped_and_distinct_dockets_stay_distinct():
    assert qt._bare_docket("bge", "BGE 146 IV 68") == qt._bare_docket("bge", "146 IV 68")
    assert qt._bare_docket("bge", "Verfahren bge 99") == "verfahrenbge99"
    base = [{"court": "bger", "decision_id": "x", "canonical_decision_id": "x",
             "docket_number": "1A_1/2020", "channels": ["search"]}]
    extra = [{"court": "bger", "decision_id": "y", "canonical_decision_id": "y",
              "docket_number": "2A_1/2020", "channels": ["search"]}]
    merged, stats = qt.merge_coverage_candidates(base, extra)
    assert stats["n_added"] == 1 and len(merged) == 2


# --------------------------------------------------------------------------
# 6. the diagnosis and the report of record
# --------------------------------------------------------------------------

def test_diagnosis_names_every_defect_with_reproduce_and_disposition():
    d = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert d["inherited_run_id"] == INHERITED_RUN
    assert d["run_id"] == RUN_ID
    ids = [x["id"] for x in d["defects"]]
    assert ids == ["D1", "D2", "D3", "D4", "D5", "D6"]
    for defect in d["defects"]:
        assert defect["reproduce"], defect["id"]
        assert defect["status"] in {"REPAIRED", "DISCLOSED_INHERITED"}, defect
    by_id = {x["id"]: x for x in d["defects"]}
    assert by_id["D1"]["status"] == "REPAIRED"      # state contract
    assert by_id["D4"]["status"] == "REPAIRED"      # merge identity
    assert by_id["D5"]["status"] == "DISCLOSED_INHERITED"
    assert by_id["D6"]["status"] == "DISCLOSED_INHERITED"


def test_report_of_record_exists_and_cites_the_checked_artifacts():
    text = REPORT.read_text(encoding="utf-8")
    for needle in (
        "39758711075", "39752638579", "adversarial_retrieval/3",
        "e_EMISSION_WRITER_ABORT", "_bare_docket",
        "LOCAL_LIVE_COVERAGE2_live.json", "LOCAL_OFFLINE_VERIFY_offline.json",
        "CYCLE_39758711075_resume_diagnosis.json",
        "CYCLE_39758711075_test_delta_attribution.json",
        "human_gate_ready", "BOUNDED-NEGATIVE",
    ):
        assert needle in text, f"report of record does not cite {needle!r}"


# --------------------------------------------------------------------------
# 7. the regenerated collected-test attribution (defect D3)
# --------------------------------------------------------------------------

def test_attribution_artifact_exists_and_is_compared():
    d = json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    assert d["run_id"] == RUN_ID
    assert d["cross_check"]["status"] == "COMPARED"
    assert d["cross_check"]["base_agrees"] is True


def test_attribution_working_tree_equals_what_this_tree_collects():
    d = json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    measured = d["working_tree"]["collected_total"]
    assert measured == tda.collect_count(ROOT), (
        f"attribution says {measured}, this tree collects {tda.collect_count(ROOT)}"
    )


def test_pin_was_repointed_and_the_previous_pin_is_preserved():
    from product.tests import test_delta_attribution as pin
    assert pin.ATTRIBUTION == ATTRIBUTION
    assert pin.ATTRIBUTION_PREVIOUS_PIN.is_file()
    for old in pin.ATTRIBUTION_HISTORY:
        assert old.is_file(), old
    assert ATTRIBUTION in pin.ATTRIBUTION_HISTORY
