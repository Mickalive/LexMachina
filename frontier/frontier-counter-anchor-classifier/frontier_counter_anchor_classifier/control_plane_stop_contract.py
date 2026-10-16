"""Machine-checkable STOP CONTRACT for the re-dispatch loop of charter v1.

The loop this module exists to make checkable
--------------------------------------------
Team ``frontier-counter-anchor-classifier`` (charter_version 1) fired its
``stop_promote_rule`` at OUTCOME A, the outcome was accepted, and the charter was
discharged -- yet the supervisor dispatched the SAME charter a fourth time
(current run 38973221261).  The chain is a control-plane inconsistency, not a
team failure, and it is exactly this:

1. ``.github/workflows/factory-supervisor.yml:261`` --
   ``jq -c '.teams[] | select(.status=="RUN")' state/frontier_portfolio.json``
   is the ONLY reliable dispatch gate.  It is a plain string compare on
   ``.status``; nothing else gates a Frontier dispatch.
2. ``.github/workflows/frontier-team.yml:58`` -- the SAME
   ``select(.status=="RUN")`` predicate materialises the executable charter, so
   a team the supervisor selects is a team that runs.
3. The control-plane portfolio (``/tmp/lex_control/state/frontier_portfolio.json``,
   mirrored from ``main``) still carries ``.status == "RUN"`` for this team with
   ``run_history: []`` and ``continue_recommended: true``, even though the team's
   own ``state/frontier/frontier-counter-anchor-classifier.json`` records a
   discharged charter with ``continue_recommended: false``.
4. The "exhausted same-charter work" guard at
   ``.github/workflows/factory-supervisor.yml:277`` is DEAD CODE.  It tests
   ``jq -r '.continue_recommended // true' <<< "$raw" == false``, but jq's ``//``
   operator falls through on the literal ``false`` as well as on null, so the
   expression prints ``true`` for exactly the value it is meant to detect::

       $ echo '{"continue_recommended":false}' | jq -r '.continue_recommended // true'
       true

   The guard can therefore never fire, and no amount of team-side bookkeeping can
   stop the re-dispatch through that path.
5. The team lane CANNOT repair it.  The CI scope gate at
   ``.github/workflows/frontier-team.yml:161`` whitelists only the team
   namespace, so a team job writing ``state/frontier_portfolio.json`` exits 4
   with "Frontier crossed scope".  Only ``.github/workflows/factory-director.yml:94``
   may write the portfolio.

What this module is
-------------------
A pure, read-only contract checker plus a ready-to-apply PROPOSAL.  It never
writes the portfolio, never writes ``/tmp/lex_control`` and never writes outside
the caller's chosen output path.  It answers one question with evidence:

    does the control plane still select this charter for dispatch?

If yes, the contract is NOT satisfied, the process exits 3 (a meaningful
non-zero for CI) and the exact minimal patch is printed as a PROPOSAL FOR THE
CONTROL PLANE -- for ``factory_director`` / the repository owner to execute,
never for the team to apply itself.

The proposed patch is exactly four field changes on the team's own entry, taken
from the accepted team state as the source of truth:

    .status                -> "TERMINATED"
    .promotion_status      -> "PROMOTED_TO_PRODUCT"
    .continue_recommended  -> false
    .run_history           -> the accepted run ids from the team state

``.status`` is the load-bearing field: it is the only one the dispatch predicate
reads.  The other three exist so that the control plane stops contradicting
itself (an entry that says TERMINATED while advertising an empty run history
and ``continue_recommended: true`` is what produced four dispatches in the first
place).

Determinism
-----------
Pure stdlib, no network, no model calls, no clock, no randomness.  ``jq`` is
shelled out to when present -- because the point is to evaluate the EXACT
expressions the workflows evaluate, not a Python paraphrase of them -- and the
module degrades to a documented Python emulation when it is absent, recording
``jq_present: false`` and ``source: "python_emulation"`` so a reader can never
mistake emulation for evidence.

Run it::

    python frontier/frontier-counter-anchor-classifier/frontier_counter_anchor_classifier/control_plane_stop_contract.py
    python frontier/.../control_plane_stop_contract.py --print-diff --json-out /tmp/opencode/x.json
"""

from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

__all__ = [
    "DEFAULT_PORTFOLIO_PATH",
    "DEFAULT_TEAM_ID",
    "DEFAULT_TEAM_STATE_PATH",
    "DISPATCH_QUERY",
    "GUARD_CORRECTED_EXPRESSION",
    "GUARD_BUGGY_EXPRESSION",
    "PATCH_TARGET_STATUS",
    "PATCH_TARGET_PROMOTION_STATUS",
    "exit_code_for",
    "dispatch_predicate",
    "main",
    "probe_exhausted_guard",
    "read_portfolio_entry",
    "required_patch",
    "stop_contract_state",
    "summarize",
]

# --------------------------------------------------------------------------
# Constants that quote the workflows this contract is checked against.
# --------------------------------------------------------------------------

#: .github/workflows/factory-supervisor.yml:261 and
#: .github/workflows/frontier-team.yml:58 -- the ONLY reliable dispatch gate.
#: The supervisor invokes it as ``jq -c`` (compact output, one charter per line);
#: DISPATCH_QUERY is just the filter, and :data:`DISPATCH_JQ_ARGS` is the flag
#: set the workflows actually pass. Compact output is load-bearing: plain ``jq``
#: pretty-prints each charter over many lines and a per-line parser cannot read
#: it back.
DISPATCH_QUERY = '.teams[] | select(.status=="RUN")'
DISPATCH_JQ_ARGS = ["-c", "-r"]

#: .github/workflows/factory-supervisor.yml:277 -- the dead exhausted-work guard.
GUARD_BUGGY_EXPRESSION = ".continue_recommended // true"

#: The same test with jq's `//` fall-through removed: `false` stays `false`.
GUARD_CORRECTED_EXPRESSION = (
    'if .continue_recommended == false then "false" else "true" end'
)

#: The value the dispatch predicate must NOT match any more.
PATCH_TARGET_STATUS = "TERMINATED"
PATCH_TARGET_PROMOTION_STATUS = "PROMOTED_TO_PRODUCT"

DEFAULT_TEAM_ID = "frontier-counter-anchor-classifier"
DEFAULT_PORTFOLIO_PATH = "/tmp/lex_control/state/frontier_portfolio.json"

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
DEFAULT_TEAM_STATE_PATH = os.path.join(
    REPO_ROOT, "state", "frontier", DEFAULT_TEAM_ID + ".json"
)

#: Throwaway output path.  Deliberately NOT inside
#: ``results/frontier/<team>/`` so a plain run can never overwrite an accepted
#: artifact (HEAD_TO_HEAD.json and friends).
DEFAULT_JSON_OUT = "/tmp/opencode/control_plane_stop_contract.json"

#: Exit codes.  3 is the CI-visible "the loop is still live" signal.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED_OUTPUT = 2
EXIT_LOOP_LIVE = 3

PROPOSAL_AUTHORITY = (
    "PROPOSAL FOR THE CONTROL PLANE ONLY. This team lane must not apply it: "
    "the CI scope gate at .github/workflows/frontier-team.yml:161 whitelists only "
    "the team namespace, so a team job that writes state/frontier_portfolio.json "
    "exits 4 with 'Frontier crossed scope'. Only "
    ".github/workflows/factory-director.yml:94 may write that file."
)


# --------------------------------------------------------------------------
# Small internal helpers
# --------------------------------------------------------------------------


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _jq_available() -> bool:
    return shutil.which("jq") is not None


def _run_jq_on_text(expression: str, text: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run `jq [-c] -r <expression>` with `text` on stdin, as the workflows do."""
    if not _jq_available():
        return {
            "ok": False,
            "stdout": "",
            "error": "jq executable not found on PATH",
        }
    argv = ["jq"] + list(extra_args or []) + ["-r", expression]
    try:
        proc = subprocess.run(
            argv,
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - defensive
        return {"ok": False, "stdout": "", "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "error": proc.stderr.strip(),
        "returncode": proc.returncode,
        "argv": argv,
    }


def _python_dispatch_select(document: Any) -> List[Dict[str, Any]]:
    """Python equivalent of `select(.status=="RUN")` over the teams array.

    Used ONLY when jq is unavailable; the caller records that provenance.
    """
    selected: List[Dict[str, Any]] = []
    if not isinstance(document, dict):
        return selected
    for entry in _iter_team_entries(document):
        if isinstance(entry, dict) and entry.get("status") == "RUN":
            selected.append(entry)
    return selected


def _iter_team_entries(document: Any) -> List[Dict[str, Any]]:
    """Both accepted on-disk shapes of the portfolio `teams` collection.

    Shape A (the live one): ``.teams`` is an array of charter objects.
    Shape B (legacy/alternative): ``.teams`` is an object keyed by team id,
    where each value is the charter object and the key is authoritative.
    """
    teams = document.get("teams") if isinstance(document, dict) else None
    entries: List[Dict[str, Any]] = []
    if isinstance(teams, list):
        entries = [entry for entry in teams if isinstance(entry, dict)]
    elif isinstance(teams, dict):
        for key, value in teams.items():
            if not isinstance(value, dict):
                continue
            entry = dict(value)
            entry.setdefault("team_id", key)
            entries.append(entry)
    return entries


def _assert_writable_out(path: str) -> None:
    """Refuse output paths that would violate the read-only contract."""
    target = os.path.abspath(path)
    forbidden = [
        os.path.join(REPO_ROOT, "results", "frontier", DEFAULT_TEAM_ID),
        os.path.join(REPO_ROOT, "state", "frontier_portfolio.json"),
        "/tmp/lex_control",
    ]
    for prefix in forbidden:
        if target == prefix or target.startswith(prefix + os.sep):
            raise ValueError(
                f"refusing to write {target!r}: it is inside the read-only control "
                f"plane / accepted-artifact area {prefix!r}. Pass --json-out to a "
                f"throwaway path (default {DEFAULT_JSON_OUT})."
            )


# --------------------------------------------------------------------------
# 1. portfolio entry lookup
# --------------------------------------------------------------------------


def read_portfolio_entry(
    portfolio_path: str = DEFAULT_PORTFOLIO_PATH,
    team_id: str = DEFAULT_TEAM_ID,
) -> Optional[Dict[str, Any]]:
    """Return this team's charter entry from a frontier_portfolio.json, or None.

    Handles both `.teams` shapes (array of charters, and object keyed by team
    id).  Read-only: the file is opened for reading only.
    """
    document = _load_json(portfolio_path)
    for entry in _iter_team_entries(document):
        if entry.get("team_id") == team_id:
            return entry
    return None


# --------------------------------------------------------------------------
# 2. the dispatch predicate
# --------------------------------------------------------------------------


def dispatch_predicate(
    portfolio_path: str = DEFAULT_PORTFOLIO_PATH,
    team_id: str = DEFAULT_TEAM_ID,
) -> Dict[str, Any]:
    """Evaluate the EXACT supervisor dispatch predicate `select(.status=="RUN")`.

    The predicate is executed by real jq on the real file, then this team's
    charter is looked up in the selected set.  ``would_dispatch`` is True iff the
    supervisor would dispatch this charter again, i.e. iff the team appears in
    the output of ``jq -c '.teams[] | select(.status=="RUN")'``.
    """
    document = _load_json(portfolio_path)
    entries = _iter_team_entries(document)
    jq_present = _jq_available()

    if jq_present:
        raw = _read_text(portfolio_path)
        proc = _run_jq_on_text(DISPATCH_QUERY, raw, extra_args=DISPATCH_JQ_ARGS)
        selected: List[Dict[str, Any]] = []
        parse_error = ""
        if proc["ok"]:
            for line in proc["stdout"].splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    parse_error = f"{type(exc).__name__}: {exc}"
                    continue
                if isinstance(item, dict):
                    selected.append(item)
        else:
            parse_error = proc.get("error", "")
        if proc["ok"] and parse_error:
            # Compact output was requested and still did not parse: fall back to
            # the documented emulation rather than reporting a false negative.
            selected = _python_dispatch_select(document)
            parse_error = f"{parse_error}; fell back to python emulation"
            source = "python_emulation"
        else:
            source = "jq"
    else:  # pragma: no cover - jq is installed in CI
        selected = _python_dispatch_select(document)
        parse_error = ""
        source = "python_emulation"

    selected_ids = sorted(
        str(item.get("team_id")) for item in selected if item.get("team_id")
    )
    entry = next((item for item in entries if item.get("team_id") == team_id), None)

    return {
        "portfolio_path": portfolio_path,
        "team_id": team_id,
        "query": DISPATCH_QUERY,
        "would_dispatch": entry is not None and entry.get("status") == "RUN",
        "status": (entry or {}).get("status"),
        "charter_version": (entry or {}).get("charter_version"),
        "entry_present": entry is not None,
        "run_history_len": len((entry or {}).get("run_history") or []),
        "continue_recommended": (entry or {}).get("continue_recommended"),
        "promotion_status": (entry or {}).get("promotion_status"),
        "selected_teams": selected_ids,
        "selected_count": len(selected),
        "team_in_selected_set": team_id in selected_ids,
        "jq_present": jq_present,
        "source": source,
        "parse_error": parse_error,
        "authority": (
            ".github/workflows/factory-supervisor.yml:261 and "
            ".github/workflows/frontier-team.yml:58"
        ),
    }


# --------------------------------------------------------------------------
# 3. the dead exhausted-same-charter guard
# --------------------------------------------------------------------------


def _emulate_buggy_guard(document: Any) -> str:
    """jq `.continue_recommended // true` semantics: `//` also falls through on false.

    jq's ``//`` tests TRUTHINESS, not presence, so the right-hand side wins for
    BOTH null and false.  The guard therefore yields "true" for every input,
    which is precisely why it can never fire.
    """
    # Every branch returns "true"; written out so the semantics are auditable.
    return "true"


def _emulate_corrected_guard(document: Any) -> str:
    if not isinstance(document, dict):
        return "true"
    return "false" if document.get("continue_recommended") is False else "true"


def probe_exhausted_guard(state_json_path: str = DEFAULT_TEAM_STATE_PATH) -> Dict[str, Any]:
    """Probe the dead guard at .github/workflows/factory-supervisor.yml:277.

    Runs BOTH expressions against the real team state file, feeding the file on
    stdin exactly as the supervisor does (``jq -r EXPR <<< "$raw"``):

      * the buggy one, ``jq -r '.continue_recommended // true'``
      * the corrected one, ``jq -r 'if .continue_recommended == false
        then "false" else "true" end'``

    ``guard_is_dead_code`` is True when the buggy expression fails to report the
    stop that the corrected expression reports -- i.e. the guard can never fire.
    If jq is missing the module degrades to a documented Python emulation and
    records ``jq_present: false`` / ``source: "python_emulation"`` instead of
    crashing.
    """
    exists = bool(state_json_path) and os.path.exists(state_json_path)
    raw = _read_text(state_json_path) if exists else ""
    jq_present = _jq_available()

    if jq_present and exists:
        buggy = _run_jq_on_text(GUARD_BUGGY_EXPRESSION, raw)
        corrected = _run_jq_on_text(GUARD_CORRECTED_EXPRESSION, raw)
        buggy_output = buggy["stdout"].strip() if buggy["ok"] else None
        corrected_output = corrected["stdout"].strip() if corrected["ok"] else None
        errors = [
            err
            for err in (buggy.get("error"), corrected.get("error"))
            if err
        ]
        source = "jq"
    else:
        document = json.loads(raw) if raw else {}
        buggy_output = _emulate_buggy_guard(document)
        corrected_output = _emulate_corrected_guard(document)
        errors = [] if exists else ["state file absent"]
        source = "python_emulation"

    buggy_says_stop = buggy_output == "false"
    corrected_says_stop = corrected_output == "false"

    return {
        "state_path": state_json_path,
        "state_present": exists,
        "team_state_continue_recommended": (
            json.loads(raw).get("continue_recommended") if exists else None
        ),
        "buggy_expression": GUARD_BUGGY_EXPRESSION,
        "buggy_output": buggy_output,
        "corrected_expression": GUARD_CORRECTED_EXPRESSION,
        "corrected_output": corrected_output,
        "buggy_says_stop": buggy_says_stop,
        "corrected_says_stop": corrected_says_stop,
        "guard_is_dead_code": bool(not buggy_says_stop and corrected_says_stop),
        "jq_present": jq_present,
        "source": source,
        "errors": errors,
        "authority": ".github/workflows/factory-supervisor.yml:277",
        "note": (
            "jq's `//` yields the right-hand side for BOTH null and false, so "
            "'.continue_recommended // true' prints 'true' for the very value the "
            "guard is written to detect. The guard cannot fire and must not be "
            "relied on as the stop mechanism; .status is the stop mechanism."
        ),
    }


# --------------------------------------------------------------------------
# 4. the required patch (a PROPOSAL for the control plane)
# --------------------------------------------------------------------------


def _clip(text: str, limit: int) -> str:
    """Clip a note to `limit` characters on a word boundary (never mid-word)."""
    if len(text) <= limit:
        return text
    head = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return head + " [...]"


def _portfolio_history_status(record: Dict[str, Any]) -> str:
    if str(record.get("cycle_kind") or "").startswith("OPERATIONAL_RESUME"):
        return "OPERATIONAL_RESUME_NO_NEW_CLAIM"
    cycle_status = str(record.get("cycle_status") or "")
    if cycle_status.startswith("COMPLETE_OUTCOME_A") or cycle_status.startswith(
        "COMPLETE_OUTCOME_B"
    ):
        return "PROMOTED"
    return "COMPLETE"


def _portfolio_history_entry(record: Dict[str, Any]) -> Dict[str, Any]:
    """Map one team-state run_history record into the portfolio's own shape.

    Portfolio convention (observed in frontier-served-packet-falsification) is
    ``{run_id, status, notes}``.
    """
    cycle_status = str(record.get("cycle_status") or record.get("cycle_kind") or "")
    evidence_tier = str(record.get("evidence_tier") or "")
    parts = [
        f"charter v{record.get('charter_version')}",
        f"cycle_status={cycle_status}",
    ]
    if evidence_tier:
        parts.append(f"evidence_tier={evidence_tier}")
    parts.append("continue_recommended=false")
    if str(record.get("cycle_kind") or "").startswith("OPERATIONAL_RESUME"):
        parts.append(
            "the portfolio stop this run claimed was NEVER applied to the control "
            "plane (team scope forbids it); this entry is the outstanding fix"
        )
    else:
        note = str(record.get("note") or "")
        if note:
            parts.append(_clip(note.strip().replace("\n", " "), 180))
    return {
        "run_id": str(record.get("run_id")),
        "status": _portfolio_history_status(record),
        "notes": "; ".join(parts),
    }


def _patched_entry(entry: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    patched = dict(entry)
    patched["status"] = PATCH_TARGET_STATUS
    patched["promotion_status"] = PATCH_TARGET_PROMOTION_STATUS
    patched["continue_recommended"] = False
    patched["run_history"] = history
    return patched


def required_patch(
    portfolio_path: str = DEFAULT_PORTFOLIO_PATH,
    team_id: str = DEFAULT_TEAM_ID,
    team_state_path: str = DEFAULT_TEAM_STATE_PATH,
) -> Dict[str, Any]:
    """Compute the MINIMAL exact field changes that stop the re-dispatch.

    Returns the before/after field deltas, a unified diff of the on-disk file,
    and the exact one-line `jq` command that applies the patch.  Nothing is
    written: the portfolio is opened for reading only.  The result is labelled
    a PROPOSAL FOR THE CONTROL PLANE (director / repository owner), never
    something the team lane applies itself.
    """
    raw = _read_text(portfolio_path)
    document = json.loads(raw)
    teams = document.get("teams")
    entry = read_portfolio_entry(portfolio_path, team_id)
    if entry is None:
        raise LookupError(f"team {team_id!r} has no entry in {portfolio_path}")

    team_state: Dict[str, Any] = {}
    if os.path.exists(team_state_path):
        team_state = _load_json(team_state_path)
    team_history = team_state.get("run_history") or []
    history = [
        _portfolio_history_entry(record)
        for record in team_history
        if isinstance(record, dict) and record.get("run_id")
    ]

    patched_entry = _patched_entry(entry, history)

    fields = (
        ("status", PATCH_TARGET_STATUS),
        ("promotion_status", PATCH_TARGET_PROMOTION_STATUS),
        ("continue_recommended", False),
    )
    field_deltas = [
        {
            "path": f'.teams[team_id={team_id}].{name}',
            "before": entry.get(name),
            "after": after,
            "existed_before": name in entry,
            "load_bearing": name == "status",
            "note": (
                "the dispatch predicate select(.status==\"RUN\") reads this field"
                if name == "status"
                else "consistency: stops the control plane contradicting itself"
            ),
        }
        for name, after in fields
    ]
    field_deltas.append(
        {
            "path": f'.teams[team_id={team_id}].run_history',
            "before": entry.get("run_history"),
            "after": history,
            "existed_before": "run_history" in entry,
            "load_bearing": False,
            "note": (
                "the portfolio advertised an empty run_history while the charter had "
                "already been accepted; copy the accepted run ids from the team state"
            ),
        }
    )

    patched_document = json.loads(raw)
    if isinstance(teams, list):
        for index, item in enumerate(patched_document["teams"]):
            if isinstance(item, dict) and item.get("team_id") == team_id:
                patched_document["teams"][index] = patched_entry
                break
    else:  # pragma: no cover - object shape is not the live one
        patched_document["teams"][team_id] = patched_entry

    roundtrip_exact = json.dumps(document, indent=2, ensure_ascii=False) + "\n" == raw
    patched_text = json.dumps(patched_document, indent=2, ensure_ascii=False) + "\n"
    diff_lines = list(
        difflib.unified_diff(
            raw.splitlines(),
            patched_text.splitlines(),
            fromfile="a/state/frontier_portfolio.json",
            tofile="b/state/frontier_portfolio.json",
            lineterm="",
            n=3,
        )
    )

    compact_history = json.dumps(history, ensure_ascii=False, separators=(",", ":"))
    jq_filter = (
        '(.teams[] | select(.team_id==$t)) |= '
        '(.status="TERMINATED" | .promotion_status="PROMOTED_TO_PRODUCT" | '
        ".continue_recommended=false | .run_history=$rh)"
    )
    jq_command = (
        "jq --arg t '{team}' --argjson rh '{history}' '{filter}' "
        "state/frontier_portfolio.json > state/frontier_portfolio.json.tmp "
        "&& mv state/frontier_portfolio.json.tmp state/frontier_portfolio.json"
    ).format(team=team_id, history=compact_history, filter=jq_filter)

    already_applied = entry.get("status") == PATCH_TARGET_STATUS and entry.get(
        "run_history"
    ) == history

    return {
        "team_id": team_id,
        "portfolio_path": portfolio_path,
        "team_state_path": team_state_path,
        "team_state_path_present": os.path.exists(team_state_path),
        "field_deltas": field_deltas,
        "diff": "\n".join(diff_lines),
        "diff_line_count": len(diff_lines),
        "format_roundtrip_exact": roundtrip_exact,
        "jq_command": jq_command,
        "jq_filter": jq_filter,
        "run_history": history,
        "accepted_run_ids": [item["run_id"] for item in history],
        "already_applied": already_applied,
        "apply_notice": PROPOSAL_AUTHORITY,
        "status_after_patch": PATCH_TARGET_STATUS,
    }


# --------------------------------------------------------------------------
# 5. the overall verdict
# --------------------------------------------------------------------------


def stop_contract_state(
    portfolio_path: str = DEFAULT_PORTFOLIO_PATH,
    team_state_path: str = DEFAULT_TEAM_STATE_PATH,
    team_id: str = DEFAULT_TEAM_ID,
) -> Dict[str, Any]:
    """The overall verdict.

    ``loop_live``                -- the supervisor would dispatch this charter again.
    ``team_state_discharged``    -- the team's own state says the charter is done.
    ``portfolio_stop_applied``   -- the control plane no longer selects this team.
    ``contract_satisfied``       -- identical to ``portfolio_stop_applied``: the
                                    contract is satisfied only when main's
                                    portfolio no longer selects this team.
    """
    dispatch = dispatch_predicate(portfolio_path, team_id)
    guard = probe_exhausted_guard(team_state_path)

    discharged = False
    cycle_status = None
    continue_recommended = None
    if team_state_path and os.path.exists(team_state_path):
        state = _load_json(team_state_path)
        cycle_status = state.get("cycle_status")
        continue_recommended = state.get("continue_recommended")
        history = state.get("run_history") or []
        discharged = bool(
            str(cycle_status or "").startswith("COMPLETE")
            and continue_recommended is False
            and history
        )

    portfolio_stop_applied = not dispatch["would_dispatch"]

    return {
        "team_id": team_id,
        "portfolio_path": portfolio_path,
        "team_state_path": team_state_path,
        "loop_live": bool(dispatch["would_dispatch"]),
        "team_state_discharged": discharged,
        "portfolio_stop_applied": portfolio_stop_applied,
        "contract_satisfied": portfolio_stop_applied,
        "portfolio_status": dispatch["status"],
        "portfolio_charter_version": dispatch["charter_version"],
        "portfolio_run_history_len": dispatch["run_history_len"],
        "team_cycle_status": cycle_status,
        "team_continue_recommended": continue_recommended,
        "dispatch": dispatch,
        "guard": guard,
    }


def exit_code_for(contract: Dict[str, Any]) -> int:
    """0 when the contract holds, 3 while the loop is live."""
    return EXIT_OK if contract["contract_satisfied"] else EXIT_LOOP_LIVE


# --------------------------------------------------------------------------
# 6. human summary
# --------------------------------------------------------------------------


def summarize(contract: Dict[str, Any]) -> str:
    dispatch = contract["dispatch"]
    guard = contract["guard"]
    lines = [
        f"STOP CONTRACT  team={contract['team_id']}  charter_version="
        f"{contract['portfolio_charter_version']}",
        f"  portfolio        : {contract['portfolio_path']}"
        f"  (status={contract['portfolio_status']!r},"
        f" run_history={contract['portfolio_run_history_len']})",
        f"  team state       : {contract['team_state_path']}"
        f"  (cycle_status={contract['team_cycle_status']!r},"
        f" continue_recommended={contract['team_continue_recommended']!r})",
        "  dispatch predicate (factory-supervisor.yml:261 select(.status==\"RUN\")): "
        + ("WOULD DISPATCH AGAIN -> LOOP LIVE" if contract["loop_live"] else "not selected -> stopped"),
        "  team state discharged           : "
        + ("yes" if contract["team_state_discharged"] else "NO"),
        "  portfolio stop applied          : "
        + ("yes" if contract["portfolio_stop_applied"] else "NO"),
        "  exhausted-work guard            : "
        + ("DEAD CODE (buggy guard never reports stop)" if guard["guard_is_dead_code"]
           else "reports stop"),
        f"      buggy      jq -r '{GUARD_BUGGY_EXPRESSION}' -> {guard['buggy_output']!r}",
        f"      corrected  jq -r '{GUARD_CORRECTED_EXPRESSION}' -> {guard['corrected_output']!r}",
        "  contract satisfied              : "
        + ("YES" if contract["contract_satisfied"] else "NO"),
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _build_arg_parser() -> "Any":
    import argparse

    parser = argparse.ArgumentParser(
        prog="control_plane_stop_contract",
        description=(
            "Check the Frontier re-dispatch stop contract for "
            f"{DEFAULT_TEAM_ID} and, if the loop is live, print the PROPOSED "
            "control-plane patch. Read-only: never writes the portfolio."
        ),
    )
    parser.add_argument("--portfolio", default=DEFAULT_PORTFOLIO_PATH)
    parser.add_argument("--team-state", default=DEFAULT_TEAM_STATE_PATH)
    parser.add_argument("--team-id", default=DEFAULT_TEAM_ID)
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT)
    parser.add_argument(
        "--print-diff",
        action="store_true",
        help="print the unified diff of the proposed portfolio patch",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        _assert_writable_out(args.json_out)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_REFUSED_OUTPUT

    if not os.path.exists(args.portfolio):
        print(
            f"::error::portfolio not found at {args.portfolio}; the control-plane "
            "portfolio is mounted read-only by the workflow. Nothing to check.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        contract = stop_contract_state(args.portfolio, args.team_state, args.team_id)
        patch = required_patch(args.portfolio, args.team_id, args.team_state)
    except (OSError, ValueError, LookupError, json.JSONDecodeError) as exc:
        print(f"::error::{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print(summarize(contract))

    if args.print_diff:
        print("\n--- unified diff (PROPOSAL, control plane only) ---")
        print(patch["diff"] or "(no diff: patch already applied)")

    if not contract["contract_satisfied"]:
        print("\n" + patch["apply_notice"])
        print("\nPROPOSED PATCH FOR THE CONTROL PLANE (factory_director / owner):")
        print(f"  file: state/frontier_portfolio.json -> .teams[team_id={patch['team_id']}]")
        for delta in patch["field_deltas"]:
            marker = "  *" if delta["load_bearing"] else "   "
            print(f"  {marker} {delta['path']}: {json.dumps(delta['before'])} -> "
                  f"{json.dumps(delta['after'], ensure_ascii=False)}")
        print(f"  accepted run ids: {', '.join(patch['accepted_run_ids']) or '(none)'}")
        print("\n  apply with exactly this one-line command:")
        print(f"    {patch['jq_command']}")
        if not args.print_diff:
            print("\n  (unified diff: re-run with --print-diff)")

    out_path = os.path.abspath(args.json_out)
    payload = {
        "contract": contract,
        "patch": patch,
        "verdict": {
            "contract_satisfied": contract["contract_satisfied"],
            "exit_code": exit_code_for(contract),
        },
    }
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        print(f"::warning::could not write {out_path}: {exc}", file=sys.stderr)

    print(f"\nwrote {out_path}")
    return exit_code_for(contract)


if __name__ == "__main__":
    raise SystemExit(main())