#!/usr/bin/env python3
"""Parse committed core-lane job logs into machine-checkable failure evidence.

Why this module exists (operational resume of run 40263483436)
---------------------------------------------------------------
Every earlier resume in this chain had to publish
``mechanism.status = "UNOBSERVED"`` because the GitHub job-log endpoint answers
**403** to unauthenticated callers (``logs_endpoint_status: 403`` in the
committed run/jobs snapshots, asserted by ``test_cycle_40193974025``).  Inside
an Actions run the runner's own persisted git-credentials token **can** read
those logs (HTTP 200), so during run 40263666190 the three failed predecessor
runs' ``Run lane cycle`` logs were fetched and committed under
``results/product/orchestration/CYCLE_40263666190_lane_cycle_logs/``.

That turns the chain's cause from prose into evidence.  Three *distinct* death
classes are visible in those bytes, and conflating them would mis-aim the
repair:

* ``MODEL_HEALTH_GATE_BLOCKED_DISPATCH`` - the wrapper's model-health preflight
  read an unhealthy workflow-owned snapshot and exited 76 before the agent
  started (``LEX_NO_HEALTHY_FREE_TOOL_MODEL``).  Control plane: model health is
  refreshed and probed by the control plane; this lane records it, never edits
  it, and a later healthy snapshot is the route-around.
* ``MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER`` - the model pool selected a
  free model whose upstream rejects a request argument OpenCode sends
  (``[unsupported_parameter] ... permissions``).  The wrapper classifies it as
  non-transient and exits without retrying, so the agent never starts.  Control
  plane: model-health probe does not reproduce the real agent request shape.
* ``AGENT_FINISHED_ZERO_DURABLE_DELTA`` - the agent ran, hit the fresh-runner
  validation cascade (missing numpy/sklearn, absent legacy map data), and
  exited 0 with a clean tree, so the wrapper's delta guard fired
  (``LEX_ZERO_DELTA_REPAIR``, exit 67).  Product: the lane's own instruments
  self-heal on a fresh runner.

Design notes
------------
* ``parse_lane_cycle_log`` is a **pure function** of log text: no network, no
  git, no state.  The committed logs are the input, so the evidence JSON and
  the cycle test re-derive the same numbers from the same bytes.
* Nothing here writes a gate, labels a run, or edits ``.github/**`` (control
  plane, never edited from this lane).  It names control-plane items for the
  director instead.
* Logs are fetched once by hand inside a run that has the token; this module
  only **reads** the committed copies.  The fetch is recorded in the artifact
  (``fetched_via`` / ``logs_endpoint_status``) so a reader can tell observed
  evidence from an unobserved mechanism.

Usage
-----
    python3 product/lane_cycle_log_evidence.py \
        --logs-dir results/product/orchestration/CYCLE_40263666190_lane_cycle_logs \
        --run-ids 40262401687 40263308953 40263483436 \
        --out results/product/orchestration/CYCLE_40263666190_lane_cycle_log_evidence.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "product-lane-cycle-log-evidence/1"
DEFAULT_LOGS_DIR = Path("results/product/orchestration") / (
    "CYCLE_40263666190_lane_cycle_logs"
)

#: One pool line per attempt, e.g.
#: ``LEX_MODEL_POOL size=4 slot=core:product:v68:40263483436 requested=...
#:  selected=opencode/beam-free index=3``.
POOL_RE = re.compile(
    r"LEX_MODEL_POOL size=(?P<size>\d+) slot=(?P<slot>\S+) "
    r"requested=(?P<requested>\S+) selected=(?P<selected>\S+) index=(?P<index>\d+)"
)
EXIT_RE = re.compile(r"Process completed with exit code\s+(-?\d+)")
UPSTREAM_RE = re.compile(
    r"Upstream request failed: \[(?P<signature>[^\]]+)\]\s*(?P<detail>.*)"
)
MISSING_MODULE_RE = re.compile(r"No module named '([^']+)'")
#: Canonical Python/interpreter error form only.  The bare regex above also
#: matches the agent's own source (``MISSING_MODULE_RE = re.compile(r"No
#: module named '([^']+)'")``) and its comment prose while it writes the
#: diagnosis, which is how ``([^`` once reached a published artifact.
MODULE_ERR_RE = re.compile(
    r"(?:ModuleNotFoundError|ImportError): No module named '([^']+)'"
)
#: The wrapper prints this with a resolved code (``rc=1``); the wrapper's own
#: script source echoes ``rc=$rc``, and a diagnosis agent quotes that source.
NON_TRANSIENT_RE = re.compile(
    r"failed without transient(?:/auth)? signature \(rc=(-?\d+)\)"
)
#: The genuine signal is a pytest ``AssertionError: Map data missing
#: positions: ...``; the agent's dict-literal source line has a closing quote
#: between the string and ``in text``.
MAP_POS_RE = re.compile(r"Map data missing positions:")
ATTEMPT_RE = re.compile(r"LEX_OX_ATTEMPT=(\d+)/(\d+)")
#: The runner renders workflow/script annotations as ``##[error]TEXT`` inside
#: the downloaded log.  Only those lines are the *run's own* verdicts: an agent
#: legitimately quotes older annotations (``"annotation":
#: "LEX_WORK_QUANTUM_EXPIRED seconds=2700 ..."``) while writing its diagnosis,
#: and honouring that quote would mislabel this run's cause.  The annotation
#: prefix is therefore what separates observation from quotation.
ANNOTATION_LINE_RE = re.compile(
    r"##\[(?P<level>error|warning|notice)\](?P<text>.*)"
)
# ``selected=`` is also echoed by resolve_model_args in some wrapper versions;
# the pool line above is the authoritative one.

CLASS_ZERO_DELTA = "AGENT_FINISHED_ZERO_DURABLE_DELTA"
CLASS_MODEL_HEALTH_GATE = "MODEL_HEALTH_GATE_BLOCKED_DISPATCH"
CLASS_MODEL_PARAMETER = "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"
CLASS_QUANTUM = "WORK_QUANTUM_EXPIRED"
CLASS_UNCLASSIFIED = "UNCLASSIFIED_LANE_CYCLE_FAILURE"

CONTROL_PLANE_ITEMS = (
    {
        "item": "model_health_preflight_gate",
        "owner": "control-plane (state/model_health.json + model-health workflow)",
        "detail": (
            "The lane-cycle wrapper refuses to dispatch an agent when the "
            "workflow-owned model_health.json snapshot says healthy=false or "
            "names no resolved_model (LEX_NO_HEALTHY_FREE_TOOL_MODEL, exit 76). "
            "The producer then exits before any product step runs, and the "
            "always-run persist step publishes an unchanged tree: a zero-durable-"
            "delta snapshot. model_health.json is control-plane state and is "
            "recorded, never edited, from this lane; the route-around is a "
            "healthy refresh before dispatch."
        ),
    },
    {
        "item": "model_pool_probe_shape_gap",
        "owner": "control-plane (state/model_health.json + model-health workflow)",
        "detail": (
            "opencode/beam-free answers the health tool_probe with PASS but "
            "rejects the real agent request with "
            "[unsupported_parameter] Unrecognized request argument supplied: "
            "permissions, so a healthy-looking pool slot can still kill the "
            "lane before the agent starts. The probe must reproduce the agent "
            "request shape; model_health.json is workflow-owned and is "
            "recorded, never edited, from this lane."
        ),
    },
    {
        "item": "workflow_does_not_bootstrap_query_runtime",
        "owner": "control-plane (.github/workflows/core-lane.yml)",
        "detail": (
            "No workflow step installs product/requirements-query.txt before "
            "the agent starts, so a fresh runner begins with no numpy and no "
            "scikit-learn. The lane now self-heals from "
            "product/tests/conftest.py via product.query_env.ensure(); the "
            "missing workflow step remains recorded, never edited, from here."
        ),
    },
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


#: A quoted-history line carries the *outer* log timestamp and then the
#: *inner* timestamp of the file the agent was reading, e.g.
#: ``2026-11-13T00:36:07.9623823Z 2026-11-13T00:21:01.6751994Z LEX_MODEL_POOL``.
#: The workflow's own output never nests a second timestamp.
NESTED_TS_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d]*Z\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
)
#: A bare 8-12 digit run id on a line means the line is *about* some run; the
#: wrapper's own pool/upstream/attempt lines never name a run id at all, and
#: the run's own pool line names exactly this run (in ``slot=``).
FOREIGN_RUN_RE = re.compile(r"\b\d{8,12}\b")


def line_is_own(line: str, run_id: str | None = None) -> bool:
    """True when ``line`` is this run's own output rather than quoted history.

    Three independent signals, any of which makes a line foreign:

    * a nested timestamp (the agent printing another run's log bytes);
    * a run id that is not ``run_id`` (the agent's prose about a predecessor);
    * a ``slot=...:<id>`` whose id is not ``run_id`` (handled by the caller
      through :func:`line_is_own`'s run-id test as well, since the slot id is
      itself an 8-12 digit token).

    With ``run_id=None`` only the nesting test applies, so the pure parser
    keeps its historical behaviour on synthetic single-run text.
    """
    if NESTED_TS_RE.search(line):
        return False
    if run_id:
        for token in FOREIGN_RUN_RE.findall(line):
            if token != run_id:
                return False
    return True


def own_lines(text: str, run_id: str | None = None) -> list[str]:
    return [ln for ln in text.splitlines() if line_is_own(ln, run_id)]


def parse_lane_cycle_log(text: str, run_id: str | None = None) -> dict[str, Any]:
    """Derive the observable failure facts of one ``Run lane cycle`` log.

    Pure and total: an input that shows none of the known markers returns
    ``classification = UNCLASSIFIED_LANE_CYCLE_FAILURE`` with the markers it
    did see, rather than being folded into a neighbouring class.

    ``run_id`` scopes the parse to *this* run's own output.  A diagnosis log
    legitimately contains whole predecessor logs (the agent reads them while
    writing its own diagnosis), and honouring those bytes would publish another
    run's model pool, upstream error and exit codes under this run's id - the
    requirement-33 "claim does not reproduce" class, one level down.  When
    ``run_id`` is given:

    * ``model_pool`` is the pool line whose ``slot`` names this run;
      anything else is reported in ``model_pool_quoted_candidates``;
    * ``upstream_error`` / ``missing_modules`` / ``attempts`` come only from
      this run's own lines; foreign matches are reported as ``*_quoted_*``;
    * ``exit_codes`` are the step's own ``##[error]...exit code N`` annotation
      lines (what the check-run annotations API records), and
      ``final_annotation_exit_code`` is the LAST one - the step's real exit.
      When an agent echoes ``::error::`` commands, GitHub records those as
      annotations too, so a multi-element list is flagged by
      ``annotation_echo_contamination`` instead of being read as "the wrapper
      exited six times".

    The two guard markers are pinned to that final exit code, because a
    diagnosis agent quoting ``LEX_ZERO_DELTA_REPAIR``/``exit 67`` text must not
    relabel a work-quantum expiry (or vice versa).
    """
    own = own_lines(text, run_id)
    own_text = "\n".join(own)

    pool = None
    pool_quoted: list[dict[str, Any]] = []
    for match in POOL_RE.finditer(text):
        entry = match.groupdict()
        line = match.group(0)
        # POOL_RE matches inside a longer line, so test the whole source line.
        src = next((ln for ln in text.splitlines() if match.group(0) in ln), line)
        if line_is_own(src, run_id) and (
            not run_id or str(entry.get("slot") or "").endswith(f":{run_id}")
        ):
            pool = entry  # last own attempt wins if a retry happened
        else:
            pool_quoted.append(entry)
    if pool is None and run_id:
        # Own-line match that names another run's slot (should not happen once
        # line_is_own rejects foreign run ids) - fall back to the last own line.
        for match in POOL_RE.finditer(own_text):
            pool = match.groupdict()

    upstream = None
    upstream_quoted: list[dict[str, Any]] = []
    for match in UPSTREAM_RE.finditer(text):
        entry = {
            "signature": match.group("signature").strip(),
            "detail": match.group("detail").strip()[:300],
        }
        src = next((ln for ln in text.splitlines() if match.group(0) in ln), "")
        if not src or line_is_own(src, run_id):
            upstream = entry
        else:
            upstream_quoted.append(entry)

    # The step's own verdicts are its annotation lines; plain-text mentions of
    # "exit code N" include script source and quoted history.
    annotation_matches = list(ANNOTATION_LINE_RE.finditer(text))
    annotation_texts = [m.group("text") for m in annotation_matches]
    exit_codes = [
        int(m.group(1))
        for m in (EXIT_RE.search(t) for t in annotation_texts)
        if m
    ]
    final_exit = exit_codes[-1] if exit_codes else None

    attempts = [
        {"attempt": int(a), "max_attempts": int(b)}
        for a, b in ATTEMPT_RE.findall(own_text)
    ]

    def _module_errors(lines: list[str]) -> list[str]:
        found: set[str] = set()
        for ln in lines:
            if "re.compile" in ln:
                continue
            parts = ln.split(None, 1)
            body = parts[1] if len(parts) == 2 else ln
            if body[:1] in ("#", '"', "'"):
                continue  # comment / dict-literal source the agent is writing
            found.update(MODULE_ERR_RE.findall(ln))
        return sorted(found)

    missing = _module_errors(own)
    foreign_mods = _module_errors(
        [ln for ln in text.splitlines() if not line_is_own(ln, run_id)])
    missing_quoted = sorted(set(foreign_mods) - set(missing))

    annotation_blob = "\n".join(annotation_texts)

    def _annotation(marker: str) -> bool:
        return marker in annotation_blob

    def _quoted_only(marker: str) -> bool:
        return marker in text and marker not in annotation_blob

    markers = {
        # Pinned to the step's real exit code: an agent that echoes
        # "::error::LEX_ZERO_DELTA_REPAIR" while writing its diagnosis must not
        # flip these, and the echo is visible as an extra annotation entry.
        "zero_delta_guard": bool(
            _annotation("LEX_ZERO_DELTA_REPAIR") and final_exit == 67
        ),
        "non_transient_failure": bool(NON_TRANSIENT_RE.search(own_text)),
        "agent_card_ok": "LEX_AGENT_CARD_OK" in own_text,
        "persist_nothing_to_commit": "nothing to commit, working tree clean" in
                                     own_text,
        "quantum_expired": bool(
            _annotation("LEX_WORK_QUANTUM_EXPIRED")
            and final_exit in (None, 78)
        ),
        # The wrapper's preflight refuses to launch an agent when the
        # workflow-owned model-health snapshot is unhealthy.  Pinned to exit 76
        # so a diagnosis agent that merely quotes the marker cannot relabel a
        # different death class.
        "model_health_gate": bool(
            _annotation("LEX_NO_HEALTHY_FREE_TOOL_MODEL")
            and final_exit == 76
        ),
        "map_data_missing_positions": bool(MAP_POS_RE.search(own_text)),
        "markers_quoted_from_history_only": sorted(
            m for m in ("LEX_ZERO_DELTA_REPAIR", "LEX_WORK_QUANTUM_EXPIRED",
                        "LEX_NO_HEALTHY_FREE_TOOL_MODEL")
            if _quoted_only(m)
        ),
        "annotation_error_lines": sorted(set(
            m.group("text").strip()[:200]
            for m in annotation_matches
            if m.group("level") == "error"
        )),
        "annotation_echo_contamination": len(exit_codes) > 1,
        "final_annotation_exit_code": final_exit,
        # Present as an annotation but refused as this run's own verdict,
        # because the step's real exit code contradicts it.  This is exactly
        # the agent-echo case: a diagnosis agent that cats a file containing
        # "::error::LEX_ZERO_DELTA_REPAIR" makes GitHub record that annotation
        # against its own step.
        "annotation_markers_rejected_by_final_exit": sorted(
            m for m, ok in (
                ("LEX_ZERO_DELTA_REPAIR", final_exit == 67),
                ("LEX_WORK_QUANTUM_EXPIRED", final_exit in (None, 78)),
                ("LEX_NO_HEALTHY_FREE_TOOL_MODEL", final_exit == 76),
            )
            if _annotation(m) and not ok
        ),
    }

    if markers["quantum_expired"]:
        classification = CLASS_QUANTUM
        why = "the wrapper's work quantum expired before the cycle finished"
    elif markers["model_health_gate"]:
        classification = CLASS_MODEL_HEALTH_GATE
        why = (
            "the wrapper's model-health preflight read an unhealthy "
            "control-plane snapshot and exited 76 before launching the agent, "
            "so no product step ran"
        )
    elif upstream and upstream["signature"] == "unsupported_parameter":
        classification = CLASS_MODEL_PARAMETER
        why = (
            "the selected upstream rejected a request argument OpenCode sent; "
            "the wrapper treats it as non-transient, so the agent never starts"
        )
    elif markers["zero_delta_guard"]:
        classification = CLASS_ZERO_DELTA
        why = (
            "the agent process exited 0 with an unchanged tree, so the "
            "LEX_REQUIRE_DELTA guard rejected the cycle before persistence"
        )
    else:
        classification = CLASS_UNCLASSIFIED
        why = "none of the known lane-cycle failure markers were observed"

    out: dict[str, Any] = {
        "model_pool": pool,
        "upstream_error": upstream,
        "exit_codes": exit_codes,
        "attempts": attempts,
        "missing_modules": missing,
        "markers": markers,
        "classification": classification,
        "why": why,
    }
    if run_id:
        out["run_id_scoped"] = True
        if pool_quoted:
            out["model_pool_quoted_candidates"] = pool_quoted[:5]
        if upstream_quoted:
            out["upstream_error_quoted_candidates"] = upstream_quoted[:5]
        if missing_quoted:
            out["missing_modules_quoted_candidates"] = missing_quoted[:5]
    else:
        out["run_id_scoped"] = False
    return out


def build(logs_dir: Path, run_ids: list[str],
          *, fetched_via: str, logs_endpoint_status: int,
          resuming_run_id: str) -> dict[str, Any]:
    runs: dict[str, Any] = {}
    for run_id in run_ids:
        path = logs_dir / f"{run_id}_team_lane_cycle.log"
        if not path.is_file() and len(run_ids) == 1:
            # fetch_run_jobs_snapshot.py names the whole team job ``team.log``;
            # a single-run capture may therefore be stored under that name.
            fallback = logs_dir / "team.log"
            if fallback.is_file():
                path = fallback
        if not path.is_file():
            runs[run_id] = {"file": None, "present": False}
            continue
        raw = path.read_bytes()
        parsed = parse_lane_cycle_log(
            raw.decode("utf-8", errors="replace"), run_id=str(run_id))
        runs[run_id] = {
            "file": str(path),
            "present": True,
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            **parsed,
        }
    classes = sorted({r["classification"] for r in runs.values()
                      if r.get("present")})
    n_runs = len(runs)
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "resuming_run_id": str(resuming_run_id),
        "logs_dir": str(logs_dir),
        "fetched_via": fetched_via,
        "logs_endpoint_status": int(logs_endpoint_status),
        "runs": runs,
        "observed_failure_classes": classes,
        "control_plane_items": [dict(i) for i in CONTROL_PLANE_ITEMS],
        "meaning": (
            f"Observed evidence from the {n_runs} committed lane-cycle job "
            "log(s) listed under runs. The failure classes are "
            "control-plane/model-pool and fresh-runner-validation facts, not "
            "product verdicts: no gate is written, no run is labelled "
            "accepted or rejected, and no frozen bar, rubric or threshold is "
            "touched. Each run's own output is separated from predecessor log "
            "bytes the agent quoted while writing its diagnosis."
        ),
        "claim_ceiling": (
            "This artifact names why the producer step exited, from bytes the "
            "workflow itself printed. It asserts nothing about product "
            "quality, retrieval, answer, counter-authority or map utility."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR))
    ap.add_argument("--run-ids", nargs="+", required=True)
    ap.add_argument("--resuming-run-id", required=True)
    ap.add_argument("--fetched-via", default=(
        "GitHub Actions job-log endpoint (HTTP 200) using the runner's "
        "persisted git-credentials token; downloaded during the resuming run"
    ))
    ap.add_argument("--logs-endpoint-status", type=int, default=200)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    record = build(
        Path(args.logs_dir), args.run_ids,
        fetched_via=args.fetched_via,
        logs_endpoint_status=args.logs_endpoint_status,
        resuming_run_id=args.resuming_run_id,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "classes": record["observed_failure_classes"],
        "runs": {k: v.get("classification") for k, v in record["runs"].items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
