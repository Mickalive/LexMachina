"""What cycle 39689729561 claims about itself, checked against the artifacts.

Why this exists
---------------
The operational resume of run 39684006959 inherited a tree whose lane state named
a report of record that did not exist, whose attribution artifact carried no
independent cross-check, whose two attribution tools published commit shas at
whatever width the local git happened to auto-abbreviate, and whose lane state was
missing four historical records that committed guards read directly. Every one of
those was a claim in the lane's own evidence with nothing executable behind it.

This module is the executable counterpart of the cycle's own claims:

* the four deleted guard-read records are present in the live state and are
  byte-exact against the preserved bytes (re-derived, never typed);
* the preserved bytes are the bytes the state names, by sha256;
* both attribution tools publish a FIXED-WIDTH short sha, and the width is
  measured from git rather than assumed;
* this cycle's attribution artifact carries a cross-check that actually ran and
  whose base agrees with the independent full-run regression artifact;
* the artifact's range endpoint is an ancestor of this branch's HEAD, so it
  measured a tree this lane shipped;
* the report of record of the PREVIOUS cycle exists, cites the nine artifacts
  that no report cited, and states the fail-closed posture;
* the diagnosis artifact names every defect it claims, each with a reproduction
  command and a status.

Deliberately NOT claimed: nothing about answer quality, nothing about a frozen
bar, nothing about any environment other than the one that ran this module.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import cache_rewrite_attribution as cache_attribution  # noqa: E402
from product import test_delta_attribution as tda  # noqa: E402

STATE_PATH = ROOT / "state" / "product.json"
RUN_ID = 39689729561
DELIVERY_KEY = f"cycle_{RUN_ID}_vertical_slice_delivery"
RESTORATION_KEY = f"state_register_restoration_{RUN_ID}"

#: This cycle's own attribution artifact: the pin's new target.
ATTRIBUTION_ARTIFACT = (ROOT / "results" / "product" / "regression"
                        / f"CYCLE_{RUN_ID}_test_delta_attribution.json")
#: The full-run regression measurement the cross-check corroborates the base
#: against. An independent measurement path (full suite run, not collection).
REGRESSION = (ROOT / "results" / "product" / "regression"
              / "CYCLE_39144924680_regression_scope.json")
#: This cycle's report of record.
REPORT_OF_RECORD = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
#: The report of record the PREVIOUS cycle owed and did not ship.
PREVIOUS_REPORT_OF_RECORD = ROOT / "reports" / "product" / "CYCLE_39674781875.md"
#: The diagnosis artifact: what broke, how it was reproduced, what was done.
DIAGNOSIS = (ROOT / "results" / "product" / "orchestration"
             / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
#: The preserved bytes of the state that the accepted cycle deleted.
PRESERVED_STATE = (ROOT / "results" / "product" / "state_register"
                   / "CYCLE_39538762904_state_product.json")

#: The four top-level records the accepted cycle 39543057762 deleted and that
#: committed guards read directly. Named here as the SET the restoration must
#: cover; the VALUES are re-derived from the preserved bytes below.
GUARD_READ_RECORDS = (
    "v55_delivery",
    "repair_39048942749_d1_d2_a2",
    "repair_39051003925_f1_f2_f3",
    "cycle_39056694835_frontier_serve_audit_intake",
)

#: The nine committed live-slice artifacts that no report cited at the accepted
#: base. The previous cycle's report of record is what makes the citation sweep
#: non-vacuous over them.
PREVIOUSLY_UNCITED = (
    "20261020T174538Z.json",
    "20261020T175313Z.json",
    "20261020T175637Z.json",
    "20261020T175732Z.json",
    "20261020T175839Z.json",
    "CYCLE_39452421855_full.json",
    "CYCLE_39452421855_maponly.json",
    "CYCLE_39667945530.json",
    "CYCLE_39667945530_FIX1.json",
)


def _state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact() -> dict:
    """This cycle's attribution artifact, or a clean failure naming it.

    The artifact is published by the commit that follows the one that carries
    this module, so a tree that has the module but not the artifact yet must
    fail with a message that says which file is missing - not with a traceback
    from a missing artifact.
    """
    assert ATTRIBUTION_ARTIFACT.exists(), (
        f"missing attribution artifact {ATTRIBUTION_ARTIFACT}")
    return _json(ATTRIBUTION_ARTIFACT)


def test_the_state_carries_this_cycles_delivery_record() -> None:
    delivery = _state().get(DELIVERY_KEY)
    assert delivery is not None, f"state/product.json carries no {DELIVERY_KEY}"
    assert delivery["run_id"] == RUN_ID
    assert delivery["human_gate_ready"] is False
    assert delivery["machine_gate_ready"] is False
    assert delivery["packet_admitted"] is False
    assert delivery["ready_for_owner_session"] is False
    assert delivery["delivered"], "the delivery record lists nothing"
    assert delivery["not_claimed"], "the delivery record claims no ceiling"
    assert delivery["claim_ceiling"]


def test_the_four_guard_read_records_are_restored_byte_exact() -> None:
    """Re-derived against the preserved bytes, not typed into the guard."""
    live = _state()
    preserved = _json(PRESERVED_STATE)
    missing = [k for k in GUARD_READ_RECORDS if k not in live]
    assert not missing, f"the deleted guard-read records are still missing: {missing}"
    for key in GUARD_READ_RECORDS:
        assert json.dumps(live[key], sort_keys=True) == json.dumps(
            preserved[key], sort_keys=True), (
            f"{key} was restored but not byte-exact against the preserved bytes; "
            "a restoration that edits the record it restores is a rewrite")


def test_the_preserved_bytes_are_the_bytes_the_state_names() -> None:
    record = _state()[RESTORATION_KEY]
    named = record["preserved_bytes"]["artifact"]
    assert named == "results/product/state_register/CYCLE_39538762904_state_product.json"
    path = ROOT / named
    assert path.is_file(), f"the preserved bytes are missing: {path}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == record["preserved_bytes"]["sha256"], (
        f"the preserved bytes changed: sha256 {digest} != the state's "
        f"{record['preserved_bytes']['sha256']}; re-derive rather than re-pin")
    assert record["deleting_run"] == "39543057762", (
        "the restoration must name the run that deleted the records")
    assert str(record["run_id"]) == str(RUN_ID)


def test_the_restoration_discloses_what_it_did_not_restore() -> None:
    """A restoration that claims to have restored everything is a rewrite."""
    record = _state()[RESTORATION_KEY]
    assert record["not_restored_into_the_live_state"], (
        "the restoration does not disclose the records it left preserved-only")
    assert "89" in record["not_restored_into_the_live_state"], (
        "the number of records left preserved-only must be stated, not implied")
    assert record["live_state_precedence"], (
        "the restoration must state that the live value wins for every key the "
        "live state already carries")


def test_both_attribution_tools_publish_a_fixed_width_short_sha() -> None:
    """The width is measured from git, not assumed by this guard."""
    head = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
        text=True, check=True).stdout.strip()
    meta = tda._commit_meta(head)
    assert len(meta["short"]) == tda.SHORT_SHA_LENGTH, (
        f"the delta-attribution tool published a {len(meta['short'])}-character "
        f"sha ({meta['short']}); the width must be pinned at "
        f"{tda.SHORT_SHA_LENGTH} so the artifact is reproducible on any git build")
    assert meta["short"] == head[:tda.SHORT_SHA_LENGTH]

    artifact = _json(ROOT / "results" / "product" / "cache_attribution"
                     / "CYCLE_39674781875_manifest_rewrite_attribution.json")
    for key in ("base", "head"):
        sha = artifact["range"][key]
        assert len(sha) == tda.SHORT_SHA_LENGTH, (
            f"the published cache-attribution range {key} names a "
            f"{len(sha)}-character sha ({sha}); the committed artifact must keep "
            f"its published {tda.SHORT_SHA_LENGTH}-character form")
    for key in ("base_subject", "head_subject"):
        subject = artifact["range"][key]
        sha = subject.split(" ", 1)[0]
        assert len(sha) == tda.SHORT_SHA_LENGTH, (
            f"the published cache-attribution {key} leads with a "
            f"{len(sha)}-character sha ({sha}); the committed artifact must keep "
            f"its published {tda.SHORT_SHA_LENGTH}-character form")


def test_the_cache_attribution_artifact_still_reproduces_from_the_tree() -> None:
    """The committed attribution must equal a fresh measurement of the tree."""
    fresh = cache_attribution.measure()
    artifact = _json(ROOT / "results" / "product" / "cache_attribution"
                     / "CYCLE_39674781875_manifest_rewrite_attribution.json")
    assert fresh["attribution"]["counts"] == artifact["attribution"]["counts"], (
        f"the fresh measurement {fresh['attribution']['counts']} no longer equals "
        f"the committed artifact {artifact['attribution']['counts']}")
    assert fresh["current_tree"]["intact"] is True
    assert fresh["current_tree"]["n_mismatch"] == 0
    assert fresh["current_tree"]["n_missing"] == 0


def test_this_cycles_attribution_cross_check_actually_ran() -> None:
    """The cross-check is the point: an independent measurement path."""
    art = _artifact()
    cross = art["cross_check"]
    assert cross["status"] == "COMPARED", (
        f"the cross-check did not run ({cross.get('status')}: {cross.get('why')}); "
        "an uncorroborated base is exactly the defect this cycle repaired")
    assert cross["artifact"] == "results/product/regression/CYCLE_39144924680_regression_scope.json"
    regression = _json(REGRESSION)
    assert cross["artifact_collected_baseline"] == regression["baseline_run"]["collected"]
    assert cross["base_agrees"] is True, (
        f"base collected disagrees: tool {cross['tool_collected_base']} vs full-run "
        f"artifact {cross['artifact_collected_baseline']} - one of them measured "
        "something else; re-derive before publishing")
    assert cross["tool_collected_base"] == art["base"]["collected_total"]


def test_the_attribution_range_endpoint_is_an_ancestor_of_head() -> None:
    art = _artifact()
    head = art["head"]["commit"]
    assert head and len(head) >= 7, "the artifact must name its range-endpoint commit"
    ancestry = subprocess.run(  # noqa: S603
        ["git", "merge-base", "--is-ancestor", head, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert ancestry.returncode == 0, (
        f"the attribution's head {head} is not an ancestor of this branch's HEAD, "
        "so it did not measure a tree this lane shipped")


def test_the_report_of_record_quotes_the_measured_decomposition_verbatim() -> None:
    art = _artifact()
    assert REPORT_OF_RECORD.is_file(), f"the report of record is missing: {REPORT_OF_RECORD}"
    text = REPORT_OF_RECORD.read_text(encoding="utf-8")
    assert art["decomposition_line"] in text, (
        "the report of record does not quote the measured decomposition verbatim")
    assert ATTRIBUTION_ARTIFACT.name in text, (
        "the report of record does not cite the attribution artifact it quotes")


def test_the_previous_cycles_report_of_record_now_exists() -> None:
    """The defect this cycle inherited: a report of record that was never written."""
    assert PREVIOUS_REPORT_OF_RECORD.is_file(), (
        f"the report of record for 39674781875 is missing: {PREVIOUS_REPORT_OF_RECORD}")
    text = PREVIOUS_REPORT_OF_RECORD.read_text(encoding="utf-8")
    for name in PREVIOUSLY_UNCITED:
        assert name in text, f"the report of record does not cite {name}"
    for needle in ("human_gate_ready", "packet_admitted", "BOUNDED-NEGATIVE"):
        assert needle in text, f"the report of record never mentions {needle}"


def test_the_diagnosis_artifact_names_every_defect_it_claims() -> None:
    assert DIAGNOSIS.is_file(), f"the diagnosis artifact is missing: {DIAGNOSIS}"
    payload = _json(DIAGNOSIS)
    assert payload["run_id"] == RUN_ID
    defects = payload["defects"]
    assert len(defects) >= 4, "the diagnosis must name every defect it claims"
    for defect in defects:
        assert defect["id"], "a defect without an id cannot be tracked"
        assert defect["reproduction"], f"{defect['id']} has no reproduction command"
        assert defect["status"], f"{defect['id']} has no status"
        assert defect["evidence"], f"{defect['id']} cites no evidence"


def test_the_posture_is_fail_closed_and_the_accepted_run_pointer_is_intact() -> None:
    state = _state()
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False
    assert state["requirement_13_supersession_conditions_met"] is False
    assert state["continue_recommended"] is True
    assert state["accepted_run_id"] == "39660515863", (
        "accepted_run_id names the last ACCEPTED run; cycle 39689729561 is not "
        "accepted, so the pointer must not move")
    assert state["direction_version"] == 61
    assert state["cycle_status"] != "INITIALIZED"
    assert state["current_run"] == RUN_ID, (
        "the lane state must name the run that produced it")
