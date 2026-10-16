"""Regression tests for the control-plane STOP CONTRACT (cycle 38973221261).

These pin the mechanics of the re-dispatch loop that cost this charter four
producer cycles, so that any future claim "the team stopped" is falsifiable and
so that the upstream control-plane defect cannot silently regress:

  * the dispatch predicate is `.status == "RUN"` (supervisor.yml:261,
    frontier-team.yml:58) and nothing else;
  * the intended exhausted-charter guard (supervisor.yml:277) is DEAD CODE
    because jq's `//` falls through on literal false;
  * therefore the ONLY reliable stop is the portfolio `.status` field, and the
    team lane is structurally forbidden from writing it
    (frontier-team.yml:161 scope gate; only factory-director.yml:94 may).

Nothing here touches the control plane: every test reads fixtures or the
read-only mount and writes only under tmp_path.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from frontier_counter_anchor_classifier.control_plane_stop_contract import (
    DEFAULT_TEAM_STATE_PATH,
    DEFAULT_TEAM_ID,
    DISPATCH_QUERY,
    EXIT_LOOP_LIVE,
    EXIT_OK,
    EXIT_REFUSED_OUTPUT,
    GUARD_BUGGY_EXPRESSION,
    GUARD_CORRECTED_EXPRESSION,
    PATCH_TARGET_PROMOTION_STATUS,
    PATCH_TARGET_STATUS,
    dispatch_predicate,
    exit_code_for,
    main,
    probe_exhausted_guard,
    read_portfolio_entry,
    required_patch,
    stop_contract_state,
)

TEAM = DEFAULT_TEAM_ID
JQ = shutil.which("jq")


def write_portfolio(path, status, *, run_history=None, promotion_status=None,
                    continue_recommended=True, extra_teams=True):
    teams = [
        {
            "team_id": TEAM,
            "charter_version": 1,
            "status": status,
            "product_capability": "cap",
            "question": "q",
            "hypothesis": "h",
            "why_now": "w",
            "non_duplication": "nd",
            "dependencies": [],
            "acceptance_test": [],
            "stop_promote_rule": "terminate after outcome",
            "promotion_status": promotion_status,
            "continue_recommended": continue_recommended,
            "run_history": run_history if run_history is not None else [],
        }
    ]
    if extra_teams:
        teams.append(
            {"team_id": "some-other-team", "charter_version": 2, "status": "PAUSE"}
        )
    path.write_text(json.dumps({"version": 50, "teams": teams}, indent=2) + "\n")
    return path


def write_team_state(path, *, continue_recommended, cycle_status, run_ids=("1", "2")):
    path.write_text(
        json.dumps(
            {
                "team_id": TEAM,
                "charter_version": 1,
                "cycle_status": cycle_status,
                "evidence_tier": "ACCEPTED",
                "continue_recommended": continue_recommended,
                "run_history": [
                    {
                        "run_id": rid,
                        "charter_version": 1,
                        "cycle_status": "COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
                        "evidence_tier": "ACCEPTED",
                        "continue_recommended": False,
                    }
                    for rid in run_ids
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return path


# --------------------------------------------------------------------------
# 1. portfolio entry lookup
# --------------------------------------------------------------------------


def test_read_portfolio_entry_finds_team(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    entry = read_portfolio_entry(str(p), TEAM)
    assert entry is not None
    assert entry["team_id"] == TEAM
    assert entry["charter_version"] == 1


def test_read_portfolio_entry_handles_object_keyed_teams(tmp_path):
    p = tmp_path / "pf.json"
    p.write_text(json.dumps({"teams": {TEAM: {"charter_version": 1, "status": "RUN"}}}))
    entry = read_portfolio_entry(str(p), TEAM)
    assert entry is not None and entry["team_id"] == TEAM


def test_read_portfolio_entry_returns_none_when_absent(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN", extra_teams=False)
    assert read_portfolio_entry(str(p), "no-such-team") is None


# --------------------------------------------------------------------------
# 2. the dispatch predicate is .status == "RUN" and nothing else
# --------------------------------------------------------------------------


def test_dispatch_predicate_true_on_RUN(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    out = dispatch_predicate(str(p), TEAM)
    assert out["would_dispatch"] is True
    assert out["team_in_selected_set"] is True
    assert out["status"] == "RUN"


def test_dispatch_predicate_false_on_TERMINATED(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "TERMINATED")
    out = dispatch_predicate(str(p), TEAM)
    assert out["would_dispatch"] is False
    assert out["team_in_selected_set"] is False


def test_dispatch_predicate_false_on_PAUSE(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "PAUSE")
    assert dispatch_predicate(str(p), TEAM)["would_dispatch"] is False


def test_dispatch_predicate_ignores_continue_recommended(tmp_path):
    """The load-bearing fact: continue_recommended does NOT gate dispatch.

    A TERMINATED team that still advertises continue_recommended=true is not
    re-dispatched, and a RUN team that says false IS re-dispatched.  This is
    exactly why the dead guard cannot be the stop mechanism.
    """
    terminated = write_portfolio(tmp_path / "a.json", "TERMINATED", continue_recommended=True)
    running = write_portfolio(tmp_path / "b.json", "RUN", continue_recommended=False)
    assert dispatch_predicate(str(terminated), TEAM)["would_dispatch"] is False
    assert dispatch_predicate(str(running), TEAM)["would_dispatch"] is True


def test_dispatch_query_is_the_workflow_query():
    assert DISPATCH_QUERY == '.teams[] | select(.status=="RUN")'


# --------------------------------------------------------------------------
# 3. the exhausted-charter guard is DEAD CODE
# --------------------------------------------------------------------------


@pytest.mark.skipif(JQ is None, reason="jq not installed")
def test_buggy_guard_is_dead_code_under_real_jq(tmp_path):
    """Reproduce supervisor.yml:277's defect with the real jq binary.

    The guard reads `.continue_recommended // true`. jq's `//` operator tests
    truthiness, not presence, so it returns the right-hand side for literal
    false. The guard can never fire.
    """
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    out = probe_exhausted_guard(str(state))
    assert out["jq_present"] is True
    assert out["source"] == "jq"
    assert out["team_state_continue_recommended"] is False
    assert out["buggy_output"] == "true", "buggy guard must misreport the stop"
    assert out["buggy_says_stop"] is False
    assert out["corrected_output"] == "false"
    assert out["corrected_says_stop"] is True
    assert out["guard_is_dead_code"] is True


@pytest.mark.skipif(JQ is None, reason="jq not installed")
def test_guard_dead_code_even_when_flag_is_true(tmp_path):
    """The buggy guard prints true for EVERY input, so it is unconditionally dead."""
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=True, cycle_status="COMPLETE"
    )
    out = probe_exhausted_guard(str(state))
    assert out["buggy_output"] == "true"
    assert out["guard_is_dead_code"] is False or out["corrected_says_stop"] is False


def test_guard_probe_degrades_without_crashing_on_missing_file(tmp_path):
    out = probe_exhausted_guard(str(tmp_path / "missing.json"))
    assert out["state_present"] is False
    assert "state file absent" in out["errors"]
    assert isinstance(out["guard_is_dead_code"], bool)


def test_guard_expressions_are_the_documented_ones():
    assert GUARD_BUGGY_EXPRESSION == ".continue_recommended // true"
    assert "== false" in GUARD_CORRECTED_EXPRESSION


# --------------------------------------------------------------------------
# 4. the required patch (a proposal, never applied by the team)
# --------------------------------------------------------------------------


def test_required_patch_sets_exactly_the_four_fields(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT", run_ids=("a", "b", "c"),
    )
    patch = required_patch(str(p), TEAM, str(state))
    by_path = {d["path"]: d for d in patch["field_deltas"]}
    status = by_path[f".teams[team_id={TEAM}].status"]
    assert status["before"] == "RUN"
    assert status["after"] == PATCH_TARGET_STATUS == "TERMINATED"
    assert status["load_bearing"] is True
    assert by_path[f".teams[team_id={TEAM}].promotion_status"]["after"] == (
        PATCH_TARGET_PROMOTION_STATUS
    )
    assert by_path[f".teams[team_id={TEAM}].continue_recommended"]["after"] is False
    assert by_path[f".teams[team_id={TEAM}].continue_recommended"]["before"] is True
    assert patch["accepted_run_ids"] == ["a", "b", "c"]
    assert len(by_path) == 4


def test_required_patch_is_a_diff_and_a_jq_command_and_writes_nothing(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False, cycle_status="COMPLETE"
    )
    before_bytes = p.read_bytes()
    patch = required_patch(str(p), TEAM, str(state))
    assert patch["diff_line_count"] > 0
    assert "TERMINATED" in patch["diff"]
    assert "select(.team_id==$t)" in patch["jq_command"]
    assert "state/frontier_portfolio.json" in patch["jq_command"]
    assert "PROPOSAL FOR THE CONTROL PLANE" in patch["apply_notice"]
    assert patch["already_applied"] is False
    assert p.read_bytes() == before_bytes, "the checker must never write the portfolio"


def test_required_patch_flags_already_applied(tmp_path):
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT", run_ids=("a", "b"),
    )
    # Apply the patch by hand, then re-derive it: it must now be a no-op.
    first = required_patch(str(write_portfolio(tmp_path / "pf.json", "RUN")), TEAM, str(state))
    p = tmp_path / "applied.json"
    doc = json.loads((tmp_path / "pf.json").read_text())
    for entry in doc["teams"]:
        if entry["team_id"] == TEAM:
            entry.update(
                status=first["status_after_patch"],
                promotion_status=PATCH_TARGET_PROMOTION_STATUS,
                continue_recommended=False,
                run_history=first["run_history"],
            )
    p.write_text(json.dumps(doc, indent=2) + "\n")
    second = required_patch(str(p), TEAM, str(state))
    assert second["already_applied"] is True


def test_required_patch_marks_operational_resume_entries_distinctly(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "team_id": TEAM,
                "run_history": [
                    {"run_id": "r1", "charter_version": 1,
                     "cycle_status": "COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT"},
                    {"run_id": "r2", "charter_version": 1,
                     "cycle_kind": "OPERATIONAL_RESUME_OF_A_TERMINATED_CHARTER",
                     "cycle_status": "COMPLETE_OUTCOME_A_..."},
                ],
            }
        )
    )
    patch = required_patch(str(write_portfolio(tmp_path / "pf.json", "RUN")), TEAM, str(state))
    statuses = {item["run_id"]: item["status"] for item in patch["run_history"]}
    assert statuses["r1"] == "PROMOTED"
    assert statuses["r2"] == "OPERATIONAL_RESUME_NO_NEW_CLAIM"
    assert "NEVER applied" in patch["run_history"][1]["notes"]


def test_notes_are_clipped_on_a_word_boundary(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {"team_id": TEAM, "run_history": [
                {"run_id": "r", "charter_version": 1,
                 "cycle_status": "COMPLETE_OUTCOME_A",
                 "note": "alpha beta gamma delta " * 40}]}
        )
    )
    patch = required_patch(str(write_portfolio(tmp_path / "pf.json", "RUN")), TEAM, str(state))
    note = patch["run_history"][0]["notes"]
    assert "[...]" in note
    assert not note.endswith("alph") and " gamma" in note


def test_required_patch_raises_for_unknown_team(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    with pytest.raises(LookupError):
        required_patch(str(p), "ghost-team")


# --------------------------------------------------------------------------
# 5. the verdict
# --------------------------------------------------------------------------


def test_contract_unsatisfied_while_status_is_RUN(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    c = stop_contract_state(str(p), str(state), TEAM)
    assert c["loop_live"] is True
    assert c["team_state_discharged"] is True
    assert c["portfolio_stop_applied"] is False
    assert c["contract_satisfied"] is False
    assert exit_code_for(c) == EXIT_LOOP_LIVE


def test_contract_satisfied_once_status_is_TERMINATED(tmp_path):
    p = write_portfolio(
        tmp_path / "pf.json", "TERMINATED",
        promotion_status=PATCH_TARGET_PROMOTION_STATUS, continue_recommended=False,
        run_history=[{"run_id": "a"}],
    )
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    c = stop_contract_state(str(p), str(state), TEAM)
    assert c["loop_live"] is False
    assert c["contract_satisfied"] is True
    assert exit_code_for(c) == EXIT_OK


def test_team_state_not_discharged_while_flag_is_true(tmp_path):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=True, cycle_status="COMPLETE"
    )
    assert stop_contract_state(str(p), str(state), TEAM)["team_state_discharged"] is False


# --------------------------------------------------------------------------
# 6. CLI contract
# --------------------------------------------------------------------------


def test_cli_exits_3_while_loop_is_live(tmp_path, capsys):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    out = tmp_path / "contract.json"
    code = main(
        ["--portfolio", str(p), "--team-state", str(state),
         "--json-out", str(out)]
    )
    assert code == EXIT_LOOP_LIVE
    text = capsys.readouterr().out
    assert "LOOP LIVE" in text
    assert "PROPOSED PATCH FOR THE CONTROL PLANE" in text
    assert json.loads(out.read_text())["verdict"]["contract_satisfied"] is False


def test_cli_exits_0_once_stopped(tmp_path, capsys):
    p = write_portfolio(
        tmp_path / "pf.json", "TERMINATED",
        promotion_status=PATCH_TARGET_PROMOTION_STATUS, continue_recommended=False,
        run_history=[{"run_id": "a"}],
    )
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    code = main(
        ["--portfolio", str(p), "--team-state", str(state),
         "--json-out", str(tmp_path / "c.json")]
    )
    assert code == EXIT_OK
    assert "contract satisfied              : YES" in capsys.readouterr().out


def test_cli_refuses_to_write_into_the_accepted_results_dir(tmp_path, capsys):
    """The default/CLI output must never be able to clobber an accepted artifact."""
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False, cycle_status="COMPLETE"
    )
    code = main(
        ["--portfolio", str(p), "--team-state", str(state),
         "--json-out",
         os.path.join("results", "frontier", TEAM, "HEAD_TO_HEAD.json")]
    )
    assert code == EXIT_REFUSED_OUTPUT
    assert "refusing to write" in capsys.readouterr().err


def test_cli_print_diff_emits_a_unified_diff(tmp_path, capsys):
    p = write_portfolio(tmp_path / "pf.json", "RUN")
    state = write_team_state(
        tmp_path / "state.json", continue_recommended=False,
        cycle_status="COMPLETE_OUTCOME_A_ADOPTABLE_COMPONENT",
    )
    main(["--portfolio", str(p), "--team-state", str(state),
          "--json-out", str(tmp_path / "c.json"), "--print-diff"])
    out = capsys.readouterr().out
    assert "--- unified diff (PROPOSAL, control plane only) ---" in out
    assert "-      \"status\": \"RUN\"" in out
    assert "+      \"status\": \"TERMINATED\"" in out


def test_cli_missing_portfolio_is_a_clean_error(tmp_path, capsys):
    code = main(["--portfolio", str(tmp_path / "nope.json"),
                 "--json-out", str(tmp_path / "c.json")])
    assert code == 1
    assert "portfolio not found" in capsys.readouterr().err


# --------------------------------------------------------------------------
# 7. live control plane
# --------------------------------------------------------------------------


def test_live_control_plane_state_is_recorded():
    """Pin the loop's CURRENT truth for the read-only control-plane mount.

    If the portfolio has since been stopped by the director this test records
    contract_satisfied=True; that is the intended end state, not a failure.
    """
    path = "/tmp/lex_control/state/frontier_portfolio.json"
    if not os.path.exists(path):
        pytest.skip("control-plane portfolio not mounted in this environment")
    state = DEFAULT_TEAM_STATE_PATH
    if not os.path.exists(state):
        pytest.skip("team state file not present in this checkout")
    c = stop_contract_state(path, state, TEAM)
    assert c["contract_satisfied"] is (not c["loop_live"])
    if c["loop_live"]:
        # The loop is live AND the team state says the charter is discharged:
        # this is exactly the contradiction that costs a cycle every dispatch.
        assert c["portfolio_status"] == "RUN"
        assert c["team_state_discharged"] is True
        assert c["team_continue_recommended"] is False
        assert c["guard"]["guard_is_dead_code"] is True, (
            "the exhausted-charter guard must be provably dead while the loop is live"
        )
