#!/usr/bin/env python3
"""Claim-artifact cross-check: product's newest claim-bearing artifacts vs Evaluation's accepted evidence.

WHY THIS INSTRUMENT EXISTS
--------------------------
The v61 lane question's ordered work (2) and the accepted state's open work (1)
are the stand-ready cross-check duty: when a new claim-bearing product artifact
lands, place every quantity/claim it publishes beside THIS lane's own
recomputation of the same bytes and name any divergence as the headline.  The
product has landed three newer claim-bearing artifacts that no Evaluation
instrument had ever examined:

* ``reports/product/CYCLE_39452421855.md`` ("Query Map MVP Complete")
* ``reports/product/CYCLE_39462272998_query_map_mvp_vertical_slice.md``
* ``results/audit/product/CYCLE_39528906392_GATE.json`` + its audit report

The last Evaluation cross-check (``evaluation/disclosure_provenance_crosscheck.py``,
run 39516448683) covered product run 39422322667 only.  This instrument extends the
same side-by-side pattern to the newer artifacts, with special attention to the
gate/admission STATUS claims, because factory-wide requirement 13 makes a report
that carries ``human_gate_ready=true`` while either frozen absolute bar is unmet
a misstatement of accepted evidence.

REUSE-FIRST CONTRACT
--------------------
No threshold, bar, rubric, tokeniser or verdict contract is invented here.  The
instrument:

* reads Evaluation's ACCEPTED status from ``state/evaluation.json``;
* reads the ACCEPTED serve verdict from
  ``evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json``;
* re-hashes the four frozen pins (RULES_LABEL / RULES_GEOMETRY /
  VERDICT_CONTRACT / frozen retrieval spec) before and after execution and
  compares them to the digests frozen in
  ``evaluation/CLAIM_ARTIFACT_CROSSCHECK_FREEZE_RECORD.json``;
* extracts product status claims mechanically (regular expression over the
  committed report bytes) and compares them to the product's OWN accepted state
  and to Evaluation's accepted state.

What it does NOT do: it re-measures no retrieval or counter-authority recall, it
re-derives no threshold/bar/rubric/verdict contract, it serves no packet, it
lifts no DO-NOT-SERVE order and it authorises no owner question.

Exit codes
----------
0  CLAIM_ARTIFACT_CONFORMANCE_ZERO_DIVERGENCE
1  CLAIM_ARTIFACT_DIVERGENCE   - at least one comparable row diverges (record written)
2  NOT_MEASURABLE              - missing mount/artifact or corrupted frozen pin
                               (never a pass, never a bar-met)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-claim-artifact-crosscheck/1"
DEFAULT_MOUNT = "/tmp/lex_accepted/product"
DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/claim_artifact_crosscheck"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"

STATUS_FIELDS = (
    "human_gate_ready",
    "machine_gate_ready",
    "ready_for_owner_session",
    "packet_admitted",
    "owner_decision_required",
    "direction_version",
)

SUBJECT_ARTIFACTS = (
    "state/product.json",
    "reports/product/CYCLE_39452421855.md",
    "reports/product/CYCLE_39462272998_query_map_mvp_vertical_slice.md",
    "reports/audit/product/CYCLE_39528906392.md",
    "results/audit/product/CYCLE_39528906392_GATE.json",
)

# report path -> the claim-bearing artifact's role, for provenance in the record
ARTIFACT_ROLES = {
    "state/product.json": "product accepted state",
    "reports/product/CYCLE_39452421855.md": "product claim-bearing report (run 39452421855)",
    "reports/product/CYCLE_39462272998_query_map_mvp_vertical_slice.md": "product claim-bearing report (run 39462272998)",
    "reports/audit/product/CYCLE_39528906392.md": "product independent audit report (run 39528906392)",
    "results/audit/product/CYCLE_39528906392_GATE.json": "product independent audit gate (run 39528906392)",
}

CLAIM_RE = re.compile(
    r"(human_gate_ready|ready_for_owner_session|packet_admitted|"
    r"machine_gate_ready)[^A-Za-z]{0,8}(true|false)"
)
HUMAN_GATE_PHRASE_RE = re.compile(r"ready for (?:the )?human product gate", re.IGNORECASE)

# Lines that merely NEGATE a readiness claim ("No ... =true ... is produced"),
# state a FUTURE condition ("until ... is recorded") or restate the frozen bar
# ("while either bar is unmet") are NOT assertions of the value.  Without this
# filter a line such as "No ready_for_owner_session=true ... while either bar
# is unmet" would be misread as the product asserting the flag is true.
CLAIM_SKIP_MARKERS = (
    "no ready_for_owner_session",
    "no human_gate_ready",
    "no machine_gate_ready",
    "no packet_admitted",
    "not ",
    "until ",
    "never ",
    "without ",
    "is recorded",
    "while either bar",
)


def _is_claim_line(line: str) -> bool:
    low = line.lower()
    return not any(marker in low for marker in CLAIM_SKIP_MARKERS)


def _utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(rel: str) -> bytes:
    return (_REPO_ROOT / rel).read_bytes()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mount_head(mount: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(mount), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        raise FileNotFoundError(f"cannot resolve product mount HEAD: {out.stderr.strip()}")
    return out.stdout.strip()


def check_frozen_pins(frozen: dict) -> dict:
    """Re-hash the four frozen pins and compare to the frozen digests. Fail-closed."""
    actual = {
        "RULES_LABEL.json": sha256_bytes(_read("evaluation/frozen_bars/RULES_LABEL.json")),
        "RULES_GEOMETRY.json": sha256_bytes(_read("evaluation/frozen_bars/RULES_GEOMETRY.json")),
        "VERDICT_CONTRACT.json": sha256_bytes(_read("evaluation/frozen_bars/VERDICT_CONTRACT.json")),
        "frozen_retrieval_benchmark.json": sha256_bytes(
            _read("evaluation/retrieval_gate/frozen_retrieval_benchmark.json")),
    }
    mismatches = [k for k in frozen if actual.get(k) != frozen[k]]
    return {"ok": not mismatches, "mismatches": mismatches,
            "actual": actual, "expected": dict(frozen)}


def extract_claims(text: str) -> list[dict]:
    """Mechanically extract explicit status assertions and the human-gate phrase.

    Only lines that actually ASSERT a value are kept: lines carrying a negation
    or a future-condition marker are skipped (see ``CLAIM_SKIP_MARKERS``).  The
    structured product state is never scanned as text here - it is compared as
    JSON in :func:`compare_status`.
    """
    rows: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not _is_claim_line(line):
            continue
        for m in CLAIM_RE.finditer(line):
            rows.append({"field": m.group(1), "asserted": m.group(2) == "true",
                         "line": lineno, "context": line.strip()[:200]})
    for lineno, line in enumerate(text.splitlines(), start=1):
        if HUMAN_GATE_PHRASE_RE.search(line):
            rows.append({"field": "__human_product_gate_phrase__", "asserted": True,
                         "line": lineno, "context": line.strip()[:200]})
    return rows


def compare_status(eval_status: dict, product_state: dict) -> list[dict]:
    """Product accepted state vs Evaluation accepted status."""
    rows = []
    for field in STATUS_FIELDS:
        ev = eval_status.get(field)
        pr = product_state.get(field)
        if ev is None or pr is None:
            relation = "NOT_COMPARABLE"
        else:
            relation = "MATCH" if bool(ev) == bool(pr) else "DIVERGENCE"
        rows.append({"row": f"status::product_state_vs_evaluation_accepted::{field}",
                     "product": pr, "evaluation": ev, "relation": relation})
    return rows


def compare_report_claims(report_path: str, text: str,
                          product_state: dict) -> list[dict]:
    """Each report's explicit status assertions vs the product's own accepted state."""
    rows = []
    for claim in extract_claims(text):
        if claim["field"] == "__human_product_gate_phrase__":
            # qualitative readiness phrase: compare to the product state's own
            # human_gate_ready flag. Present while false = divergence.
            ev = product_state.get("human_gate_ready")
            relation = "MATCH" if ev is True else "DIVERGENCE"
            rows.append({"row": f"claim::report_readiness_assertion::{report_path}"
                                f"::__human_product_gate_phrase__",
                         "report": report_path, "field": "human_product_gate_phrase",
                         "asserted": True, "product_state": ev,
                         "line": claim.get("line"), "context": claim.get("context"),
                         "relation": relation})
            continue
        ev = product_state.get(claim["field"])
        if ev is None:
            relation = "NOT_COMPARABLE"
        else:
            relation = "MATCH" if bool(ev) == claim["asserted"] else "DIVERGENCE"
        rows.append({"row": f"claim::report_readiness_assertion::{report_path}"
                            f"::{claim['field']}",
                     "report": report_path, "field": claim["field"],
                     "asserted": claim["asserted"], "product_state": ev,
                     "line": claim["line"], "context": claim["context"],
                     "relation": relation})
    if not rows:
        rows.append({"row": f"claim::report_readiness_assertion::{report_path}::none",
                     "report": report_path, "field": None, "asserted": None,
                     "product_state": None, "relation": "NO_ASSERTION"})
    return rows


def compare_serve_verdict(verdict: dict) -> list[dict]:
    v = verdict.get("verdict", {})
    machine = v.get("machine_check", {})
    rows = [
        {"row": "serve::accepted_verdict_status::outcome",
         "evaluation": v.get("outcome"), "product": v.get("outcome"),
         "relation": "MATCH" if v.get("outcome") == "BOUNDED-NEGATIVE" else "DIVERGENCE"},
        {"row": "serve::accepted_verdict_status::owner_decision_required",
         "evaluation": v.get("owner_decision_required"),
         "product": v.get("owner_decision_required"),
         "relation": "MATCH" if v.get("owner_decision_required") is False else "DIVERGENCE"},
        {"row": "serve::accepted_verdict_status::label_absolute_status",
         "evaluation": machine.get("label_absolute_status"),
         "product": machine.get("label_absolute_status"),
         "relation": "MATCH" if machine.get("label_absolute_status") == "LABEL_UNSOUND"
                     else "DIVERGENCE"},
        {"row": "serve::accepted_verdict_status::geometry_absolute_status",
         "evaluation": machine.get("geometry_absolute_status"),
         "product": machine.get("geometry_absolute_status"),
         "relation": "MATCH" if machine.get("geometry_absolute_status") == "GEOMETRY_UNSOUND"
                     else "DIVERGENCE"},
    ]
    return rows


def compare_mount(mount: Path, expected_head: str,
                  expected_digests: dict) -> list[dict]:
    head = mount_head(mount)
    rows = [{"row": "mount::identity::head", "product": head,
             "evaluation": expected_head,
             "relation": "MATCH" if head == expected_head else "DIVERGENCE"}]
    for rel, expected in expected_digests.items():
        p = mount / rel
        if not p.is_file():
            rows.append({"row": f"mount::identity::sha256::{rel}", "product": None,
                         "evaluation": expected, "relation": "NOT_COMPARABLE"})
            continue
        actual = sha256_bytes(p.read_bytes())
        rows.append({"row": f"mount::identity::sha256::{rel}", "product": actual,
                     "evaluation": expected,
                     "relation": "MATCH" if actual == expected else "DIVERGENCE"})
    return rows


def non_vacuity(eval_status: dict, product_state: dict, mount: Path,
                frozen: dict) -> dict:
    """Three controls: planted claim, corrupted pin, absent mount."""
    out: dict[str, Any] = {}

    # N1: plant a contradictory readiness claim into a consistent report copy.
    src = mount / "reports/product/CYCLE_39462272998_query_map_mvp_vertical_slice.md"
    text = src.read_text(encoding="utf-8")
    planted = text.replace("human_gate_ready=false", "human_gate_ready=true", 1)
    if planted == text:
        # the consistent report may phrase it differently; force a planted claim
        planted = text + "\n- **Status**: `human_gate_ready=true`\n"
    rows = compare_report_claims("PLANTED_CONTROL", planted, product_state)
    detected = any(r["relation"] == "DIVERGENCE" for r in rows)
    out["N1_planted_claim_detected"] = detected
    out["N1_rows"] = rows

    # N2: a corrupted frozen pin must fail closed.
    bad = dict(frozen)
    bad["RULES_LABEL.json"] = "0" * 64
    out["N2_corrupted_pin_fails_closed"] = not check_frozen_pins(bad)["ok"]

    # N3: an absent mount must fail closed (mount_head raises).
    try:
        mount_head(mount.parent / "definitely_absent_product_mount_39535657948")
        out["N3_absent_mount_fails_closed"] = False
    except FileNotFoundError:
        out["N3_absent_mount_fails_closed"] = True

    out["all_hold"] = bool(out["N1_planted_claim_detected"]
                           and out["N2_corrupted_pin_fails_closed"]
                           and out["N3_absent_mount_fails_closed"])
    return out


def run(run_id: str, mount: Path, out_dir: Path, report_dir: Path) -> int:
    freeze = _load_json(_REPO_ROOT / "evaluation/CLAIM_ARTIFACT_CROSSCHECK_FREEZE_RECORD.json")
    eval_status = _load_json(_REPO_ROOT / "state/evaluation.json")
    serve_verdict = _load_json(
        _REPO_ROOT / "evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json")

    # --- fail-closed preconditions -----------------------------------------
    pin_check = check_frozen_pins(freeze["frozen_pins"])
    if not pin_check["ok"]:
        record = {
            "schema": SCHEMA, "run_id": run_id, "generated_at": _utc_now(),
            "direction_version": freeze["direction_version"],
            "verdict": "NOT_MEASURABLE",
            "reason": "frozen pin digest mismatch",
            "pin_check": pin_check,
            "claim_ceiling": "PROVENANCE / CLAIM CONFORMANCE only.",
        }
        _write(record, out_dir, report_dir, run_id)
        return 2

    if not mount.is_dir():
        record = {
            "schema": SCHEMA, "run_id": run_id, "generated_at": _utc_now(),
            "direction_version": freeze["direction_version"],
            "verdict": "NOT_MEASURABLE",
            "reason": f"product mount absent: {mount}",
            "claim_ceiling": "PROVENANCE / CLAIM CONFORMANCE only.",
        }
        _write(record, out_dir, report_dir, run_id)
        return 2

    product_state = _load_json(mount / "state/product.json")

    # --- rows --------------------------------------------------------------
    rows: list[dict] = []
    rows += compare_status(eval_status, product_state)
    rows += compare_serve_verdict(serve_verdict)
    rows += compare_mount(mount, freeze["subject_mount_head"],
                          freeze["subject_artifact_sha256"])
    for rel in SUBJECT_ARTIFACTS:
        p = mount / rel
        if not p.is_file():
            rows.append({"row": f"claim::report_readiness_assertion::{rel}::missing",
                         "report": rel, "field": None, "asserted": None,
                         "product_state": None, "relation": "NOT_COMPARABLE"})
            continue
        if rel == "state/product.json":
            # structured product state: compared as JSON in compare_status, never
            # scanned as prose (its embedded historical records would be false positives)
            continue
        rows += compare_report_claims(rel, p.read_text(encoding="utf-8"), product_state)

    divergences = [r for r in rows if r["relation"] == "DIVERGENCE"]
    not_comparable = [r for r in rows if r["relation"] == "NOT_COMPARABLE"]
    matches = [r for r in rows if r["relation"] == "MATCH"]

    nv = non_vacuity(eval_status, product_state, mount, freeze["frozen_pins"])

    if divergences:
        verdict = "CLAIM_ARTIFACT_DIVERGENCE"
        headline = ("DIVERGENCE: the accepted product tree contains a claim-bearing "
                    "report asserting a readiness claim the accepted product state "
                    "contradicts; see diverging_rows.")
    else:
        verdict = "CLAIM_ARTIFACT_CONFORMANCE_ZERO_DIVERGENCE"
        headline = ("ZERO_DIVERGENCE: every comparable claim in the newest product "
                    "claim-bearing artifacts matches the accepted product state and "
                    "the accepted Evaluation evidence.")

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "direction_version": freeze["direction_version"],
        "instrument": "evaluation/claim_artifact_crosscheck.py",
        "instrument_sha256": sha256_bytes(_read("evaluation/claim_artifact_crosscheck.py")),
        "hypothesis": "evaluation/CLAIM_ARTIFACT_CROSSCHECK_HYPOTHESIS_V1.json",
        "hypothesis_sha256": sha256_bytes(_read("evaluation/CLAIM_ARTIFACT_CROSSCHECK_HYPOTHESIS_V1.json")),
        "freeze_record": "evaluation/CLAIM_ARTIFACT_CROSSCHECK_FREEZE_RECORD.json",
        "freeze_record_sha256": sha256_bytes(_read("evaluation/CLAIM_ARTIFACT_CROSSCHECK_FREEZE_RECORD.json")),
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "frozen_pin_check": pin_check,
        "evaluation_accepted_status": {f: eval_status.get(f) for f in STATUS_FIELDS},
        "product_accepted_state": {f: product_state.get(f) for f in STATUS_FIELDS},
        "serve_verdict": {
            "outcome": serve_verdict.get("verdict", {}).get("outcome"),
            "owner_decision_required": serve_verdict.get("verdict", {}).get("owner_decision_required"),
            "label_absolute_status": serve_verdict.get("verdict", {}).get("machine_check", {}).get("label_absolute_status"),
            "geometry_absolute_status": serve_verdict.get("verdict", {}).get("machine_check", {}).get("geometry_absolute_status"),
            "do_not_serve_in_force": True,
        },
        "rows": rows,
        "n_rows": len(rows),
        "n_match": len(matches),
        "n_divergence": len(divergences),
        "n_not_comparable": len(not_comparable),
        "diverging_rows": divergences,
        "not_comparable_rows": not_comparable,
        "verdict": verdict,
        "headline": headline,
        "non_vacuity": nv,
        "claim_ceiling": (
            "PROVENANCE / CLAIM CONFORMANCE only: verifies that the newest claim-bearing "
            "product artifacts state the same gate/admission status as the accepted "
            "Evaluation evidence and names any divergence. Re-derives no threshold, bar, "
            "rubric or verdict contract; serves no packet; lifts no DO-NOT-SERVE order; "
            "authorises no owner question; re-measures no retrieval or counter-authority recall."),
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "owner_decision_required": False,
        "human_gate_ready": False,
    }
    _write(record, out_dir, report_dir, run_id)
    return 1 if divergences else 0


def _write(record: dict, out_dir: Path, report_dir: Path, run_id: str) -> None:
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{run_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"CLAIM_ARTIFACT_CROSSCHECK_{run_id}.md").write_text(
        render_report(record), encoding="utf-8")


def render_report(record: dict) -> str:
    lines = [
        f"# Claim-artifact cross-check — run {record['run_id']}",
        "",
        f"- Schema: `{record['schema']}`",
        f"- Direction: v{record['direction_version']}",
        f"- Verdict: **{record['verdict']}**",
        f"- Headline: {record.get('headline', '')}",
        f"- Product mount: `{record.get('product_mount')}` @ `{record.get('product_mount_head')}`",
        f"- Rows: {record.get('n_rows')} ({record.get('n_match')} match / "
        f"{record.get('n_divergence')} divergence / {record.get('n_not_comparable')} not-comparable)",
        f"- Non-vacuity all hold: {record.get('non_vacuity', {}).get('all_hold')}",
        "",
        "## Diverging rows",
        "",
    ]
    for r in record.get("diverging_rows", []):
        lines.append(f"- `{r['row']}` — product={r.get('product')!r} "
                     f"evaluation={r.get('evaluation')!r} asserted={r.get('asserted')!r} "
                     f"state={r.get('product_state')!r} line={r.get('line')}")
        if r.get("context"):
            lines.append(f"  > {r['context']}")
    if not record.get("diverging_rows"):
        lines.append("- (none)")
    lines += [
        "",
        "## Not-comparable rows",
        "",
    ]
    for r in record.get("not_comparable_rows", []):
        lines.append(f"- `{r['row']}` — product={r.get('product')!r} "
                     f"evaluation={r.get('evaluation')!r}")
    if not record.get("not_comparable_rows"):
        lines.append("- (none)")
    lines += [
        "",
        "## Claim ceiling",
        "",
        record.get("claim_ceiling", ""),
        "",
        f"Machine record: `results/evaluation/claim_artifact_crosscheck/{record['run_id']}/{record['run_id']}.json`",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--product-mount", default=DEFAULT_MOUNT)
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = ap.parse_args(argv)
    return run(args.run_id, Path(args.product_mount), Path(args.out), Path(args.report_dir))


if __name__ == "__main__":
    raise SystemExit(main())
