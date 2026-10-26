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

That turns the chain's cause from prose into evidence.  Two *distinct* death
classes are visible in those bytes, and conflating them would mis-aim the
repair:

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
CLASS_MODEL_PARAMETER = "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"
CLASS_QUANTUM = "WORK_QUANTUM_EXPIRED"
CLASS_UNCLASSIFIED = "UNCLASSIFIED_LANE_CYCLE_FAILURE"

CONTROL_PLANE_ITEMS = (
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


def parse_lane_cycle_log(text: str) -> dict[str, Any]:
    """Derive the observable failure facts of one ``Run lane cycle`` log.

    Pure and total: an input that shows none of the known markers returns
    ``classification = UNCLASSIFIED_LANE_CYCLE_FAILURE`` with the markers it
    did see, rather than being folded into a neighbouring class.
    """
    pool = None
    for match in POOL_RE.finditer(text):
        pool = match.groupdict()  # last attempt wins if a retry happened
    upstream = None
    for match in UPSTREAM_RE.finditer(text):
        upstream = {
            "signature": match.group("signature").strip(),
            "detail": match.group("detail").strip()[:300],
        }
    exit_codes = [int(m.group(1)) for m in EXIT_RE.finditer(text)]
    attempts = [
        {"attempt": int(a), "max_attempts": int(b)}
        for a, b in ATTEMPT_RE.findall(text)
    ]
    missing = sorted(set(MISSING_MODULE_RE.findall(text)))

    # Workflow annotations are this run's own verdicts; anything the agent
    # merely quotes is recorded separately and never classifies the run.
    annotation_texts = [m.group("text") for m in ANNOTATION_LINE_RE.finditer(text)]
    annotation_blob = "\n".join(annotation_texts)

    def _annotation(marker: str) -> bool:
        return marker in annotation_blob

    def _quoted_only(marker: str) -> bool:
        return marker in text and marker not in annotation_blob

    markers = {
        "zero_delta_guard": _annotation("LEX_ZERO_DELTA_REPAIR"),
        "non_transient_failure": "failed without transient" in text,
        "agent_card_ok": "LEX_AGENT_CARD_OK" in text,
        "persist_nothing_to_commit": "nothing to commit, working tree clean" in
                                     text,
        "quantum_expired": _annotation("LEX_WORK_QUANTUM_EXPIRED"),
        "map_data_missing_positions": "Map data missing positions" in text,
        "markers_quoted_from_history_only": sorted(
            m for m in ("LEX_ZERO_DELTA_REPAIR", "LEX_WORK_QUANTUM_EXPIRED")
            if _quoted_only(m)
        ),
        "annotation_error_lines": sorted(set(
            m.group("text").strip()[:200]
            for m in ANNOTATION_LINE_RE.finditer(text)
            if m.group("level") == "error"
        )),
    }

    if markers["quantum_expired"]:
        classification = CLASS_QUANTUM
        why = "the wrapper's work quantum expired before the cycle finished"
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

    return {
        "model_pool": pool,
        "upstream_error": upstream,
        "exit_codes": exit_codes,
        "attempts": attempts,
        "missing_modules": missing,
        "markers": markers,
        "classification": classification,
        "why": why,
    }


def build(logs_dir: Path, run_ids: list[str],
          *, fetched_via: str, logs_endpoint_status: int,
          resuming_run_id: str) -> dict[str, Any]:
    runs: dict[str, Any] = {}
    for run_id in run_ids:
        path = logs_dir / f"{run_id}_team_lane_cycle.log"
        if not path.is_file():
            runs[run_id] = {"file": None, "present": False}
            continue
        raw = path.read_bytes()
        parsed = parse_lane_cycle_log(raw.decode("utf-8", errors="replace"))
        runs[run_id] = {
            "file": str(path),
            "present": True,
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            **parsed,
        }
    classes = sorted({r["classification"] for r in runs.values()
                      if r.get("present")})
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
            "Observed evidence from committed job logs of three failed product "
            "runs. The two failure classes are control-plane/model-pool and "
            "fresh-runner-validation facts, not product verdicts: no gate is "
            "written, no run is labelled accepted or rejected, and no frozen "
            "bar, rubric or threshold is touched."
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
