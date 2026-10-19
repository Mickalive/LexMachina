#!/usr/bin/env python3
"""FAST MVP retrieval-instrument falsification: reproduce the accepted run of
record and prove the frozen retrieval gates can fail two deliberately regressed
multilingual/provenance records.

The counter-authority half of the FAST MVP benchmark can already falsify
(``evaluation.benchmark_retrieval_counter_authority`` legs 2-3).  This module
closes the retrieval half with three legs, all offline over committed bytes:

  leg A  reproduction   re-score the accepted run of record
                        (results/evaluation/retrieval_benchmark/39098571937.json)
                        through the accepted pure entry point
                        ``evaluation.retrieval_gate.gates.evaluate``; the
                        failed/not-measurable gate sets, the four counts and
                        overall_pass must equal the accepted reading exactly.
  leg B  hostile blank  empty the rows of exactly one currently-PASSING
                        multilingual cell (baseline:corporate-criminal-liability:de);
                        the failed set must grow by exactly the two named
                        authority gates for that slug/language, lose nothing,
                        and the de cells of the other two measurable legs must
                        stay passing (cell specificity).
  leg C  hostile dup    append a copy of rows[0] to exactly one query whose
                        duplicate gate currently PASSES
                        (counter:rent-default:fr); the failed set must grow by
                        exactly duplicate::unique_ids::rent-default and lose
                        nothing.

Nothing here re-implements a gate, re-derives a threshold, writes a frozen file
or touches the accepted record.  The expected sets are frozen by
``evaluation/RETRIEVAL_INSTRUMENT_FALSIFICATION_HYPOTHESIS_V1.json``; a moved
input digest is exit 2, never a silent re-pin.

Exit codes
  0  REPRODUCTION_MATCHES_AND_FALSIFICATION_PROVEN
  1  FALSIFICATION_OR_REPRODUCTION_FAILURE
  2  ENVIRONMENT (pinned input missing/drifted)

SCRATCH-RUN OBLIGATION: a non-claim-bearing invocation MUST pass --out and
--report-dir; the defaults are the committed claim-bearing trees.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.retrieval_gate import frozen, gates  # noqa: E402

SCHEMA = "lex-evaluation-retrieval-instrument-falsification/1"
DEFAULT_HYPOTHESIS = (_REPO_ROOT / "evaluation"
                      / "RETRIEVAL_INSTRUMENT_FALSIFICATION_HYPOTHESIS_V1.json")

VERDICT_OK = "REPRODUCTION_MATCHES_AND_FALSIFICATION_PROVEN"
VERDICT_FAIL = "FALSIFICATION_OR_REPRODUCTION_FAILURE"
VERDICT_ENV = "ENVIRONMENT"

LEG_B_QUERY_KEY = "baseline:corporate-criminal-liability:de"
LEG_B_EXPECTED_NEW = {
    "authority::baseline_lang_recall::corporate-criminal-liability::de",
    "authority::baseline_recall::corporate-criminal-liability",
}
LEG_B_MUST_STAY_PASSING = {
    "authority::baseline_lang_recall::business-judgment-rule::de",
    "authority::baseline_lang_recall::petty-theft-dismissal::de",
}
LEG_C_QUERY_KEY = "counter:rent-default:fr"
LEG_C_EXPECTED_NEW = {"duplicate::unique_ids::rent-default"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_inputs(hypothesis: dict) -> tuple[dict[str, Path], list[str]]:
    resolved: dict[str, Path] = {}
    problems: list[str] = []
    for name, pin in (hypothesis.get("inputs") or {}).items():
        path = Path(pin["path"])
        if not path.is_absolute():
            path = _REPO_ROOT / path
        if not path.is_file():
            problems.append(f"{name}: missing {path}")
            continue
        got = _sha256_file(path)
        if got != pin["sha256"]:
            problems.append(f"{name}: digest drift expected {pin['sha256'][:12]} "
                            f"got {got[:12]}")
            continue
        resolved[name] = path
    return resolved, problems


def _gate_map(verdict: dict) -> dict[str, dict]:
    return {g["gate"]: g for g in verdict.get("gates") or []}


def _counts(verdict: dict) -> dict:
    return {"n_gates": verdict.get("n_gates"),
            "n_passed": verdict.get("n_passed"),
            "n_failed": verdict.get("n_failed"),
            "n_not_measurable": verdict.get("n_not_measurable"),
            "overall_pass": verdict.get("overall_pass")}


def _blank_query(record: dict, query_key: str) -> int:
    n = 0
    for q in record.get("queries") or []:
        if q.get("query_key") == query_key:
            q["rows"] = []
            q["ids"] = []
            q["n_results"] = 0
            n += 1
    return n


def _duplicate_first_row(record: dict, query_key: str) -> int:
    n = 0
    for q in record.get("queries") or []:
        if q.get("query_key") == query_key:
            rows = q.get("rows") or []
            if rows:
                rows.append(copy.deepcopy(rows[0]))
                q["ids"] = [r.get("decision_id") for r in rows]
                q["n_results"] = len(rows)
                n += 1
    return n


def run(run_id: str, hypothesis_path: Path, out_path: Path,
        report_path: Path) -> tuple[int, dict]:
    if not hypothesis_path.is_file():
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": VERDICT_ENV,
                   "detail": f"hypothesis missing: {hypothesis_path}"}
    hypothesis = _load(hypothesis_path)
    resolved, problems = verify_inputs(hypothesis)
    base = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis.get("direction_version"),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_path": str(hypothesis_path),
        "hypothesis_sha256": _sha256_file(hypothesis_path),
        "scoring_entry_point": "evaluation.retrieval_gate.gates.evaluate",
        "input_digests_verified": sorted(resolved),
        "input_digest_problems": problems,
    }
    if problems:
        base.update(verdict=VERDICT_ENV,
                    detail="pinned input missing or drifted; no leg was read",
                    headline="ENVIRONMENT_INPUT_DRIFT")
        _persist(base, out_path, report_path)
        return 2, base

    accepted = _load(resolved["accepted_run_of_record"])
    accepted_pin = (hypothesis.get("inputs") or {})["accepted_run_of_record"]
    accepted_reading = accepted_pin.get("accepted_reading") or {}

    try:
        spec = frozen.load_frozen()
        frozen.freeze_record()
    except frozen.FrozenBenchmarkError as exc:
        base.update(verdict=VERDICT_ENV,
                    detail=f"frozen benchmark integrity failure: {exc}",
                    headline="ENVIRONMENT_FROZEN_INTEGRITY")
        _persist(base, out_path, report_path)
        return 2, base

    # ---- leg A: reproduction ------------------------------------------------
    verdict_a = gates.evaluate(spec, accepted)
    failed_a = set(verdict_a.get("failed_gates") or [])
    nm_a = set(verdict_a.get("not_measurable_gates") or [])
    counts_a = _counts(verdict_a)
    expected_failed = set(accepted_reading.get("failed_gates") or [])
    expected_nm = set(accepted_reading.get("not_measurable_gates") or [])
    # The accepted_reading in the hypothesis carries counts + overall_pass; the
    # failed/nm SETS are re-derived from the accepted record itself (they are
    # accepted evidence inside it), never re-typed by hand.
    if not expected_failed:
        expected_failed = {g["gate"] for g in accepted["verdict"]["gates"]
                           if g.get("passed") is False}
    if not expected_nm:
        expected_nm = {g["gate"] for g in accepted["verdict"]["gates"]
                       if g.get("passed") is None}
    leg_a_ok = (failed_a == expected_failed and nm_a == expected_nm
                and counts_a.get("n_gates") == accepted_reading.get("n_gates")
                and counts_a.get("n_passed") == accepted_reading.get("n_passed")
                and counts_a.get("n_failed") == accepted_reading.get("n_failed")
                and counts_a.get("n_not_measurable") == accepted_reading.get("n_not_measurable")
                and counts_a.get("overall_pass") == accepted_reading.get("overall_pass"))
    leg_a = {"leg": "reproduction", "ok": leg_a_ok,
             "counts": counts_a, "expected_counts": accepted_reading,
             "failed_gates": sorted(failed_a),
             "failed_set_matches": failed_a == expected_failed,
             "not_measurable_gates": sorted(nm_a),
             "not_measurable_set_matches": nm_a == expected_nm}

    # ---- leg B: hostile blank ----------------------------------------------
    hostile_b = copy.deepcopy(accepted)
    n_touched_b = _blank_query(hostile_b, LEG_B_QUERY_KEY)
    verdict_b = gates.evaluate(spec, hostile_b)
    failed_b = set(verdict_b.get("failed_gates") or [])
    added_b = failed_b - failed_a
    lost_b = failed_a - failed_b
    gates_b = _gate_map(verdict_b)
    stayed = {g: (gates_b.get(g) or {}).get("passed")
              for g in LEG_B_MUST_STAY_PASSING}
    leg_b_ok = (n_touched_b == 1 and added_b == LEG_B_EXPECTED_NEW
                and not lost_b and all(v is True for v in stayed.values()))
    leg_b = {"leg": "hostile_blank", "ok": leg_b_ok,
             "query_key": LEG_B_QUERY_KEY, "queries_touched": n_touched_b,
             "added_failed_gates": sorted(added_b),
             "expected_added": sorted(LEG_B_EXPECTED_NEW),
             "lost_failed_gates": sorted(lost_b),
             "cell_specificity": stayed}

    # ---- leg C: hostile duplicate ------------------------------------------
    hostile_c = copy.deepcopy(accepted)
    n_touched_c = _duplicate_first_row(hostile_c, LEG_C_QUERY_KEY)
    verdict_c = gates.evaluate(spec, hostile_c)
    failed_c = set(verdict_c.get("failed_gates") or [])
    added_c = failed_c - failed_a
    lost_c = failed_a - failed_c
    leg_c_ok = (n_touched_c == 1 and added_c == LEG_C_EXPECTED_NEW and not lost_c)
    leg_c = {"leg": "hostile_duplicate", "ok": leg_c_ok,
             "query_key": LEG_C_QUERY_KEY, "queries_touched": n_touched_c,
             "added_failed_gates": sorted(added_c),
             "expected_added": sorted(LEG_C_EXPECTED_NEW),
             "lost_failed_gates": sorted(lost_c)}

    # ---- combined -----------------------------------------------------------
    if leg_a_ok and leg_b_ok and leg_c_ok:
        verdict, exit_code = VERDICT_OK, 0
        headline = ("the frozen retrieval instrument reproduces the accepted run "
                    "of record and both deliberately regressed multilingual/"
                    "provenance records make it fail exactly where expected")
    else:
        verdict, exit_code = VERDICT_FAIL, 1
        if not leg_a_ok:
            headline = ("reproduction failure: the accepted run of record does not "
                        "re-score to its accepted reading under the committed gates")
        elif not leg_b_ok:
            headline = ("hostile blank did not produce exactly the named gate flips "
                        "on the frozen retrieval gates (vacuous or global failure)")
        else:
            headline = ("hostile duplicate did not produce exactly the named gate "
                        "flip on the provenance gate")

    record = dict(base)
    record.update(
        verdict=verdict,
        headline=headline,
        legs=[leg_a, leg_b, leg_c],
        falsification_proven=bool(leg_b_ok and leg_c_ok),
        reproduction_matches=bool(leg_a_ok),
        absolute_status_note=(
            "the accepted reading itself is overall_pass=false with 10 failed "
            "gates (6 fr/it authority-recall cells, 3 duplicate cells, 1 limiting-"
            "marker cell); it is preserved verbatim and this instrument claims "
            "no absolute retrieval bar is met"),
        claim_ceiling=hypothesis.get("claim_ceiling"),
        human_gate_ready=False,
        owner_decision_required=False,
    )
    _persist(record, out_path, report_path)
    return exit_code, record


def _persist(record: dict, out_path: Path, report_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Retrieval-instrument falsification - run {record['run_id']}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Verdict: **{record.get('verdict')}** (exit implied by verdict)",
        f"- Headline: {record.get('headline')}",
        f"- Reproduction matches: {record.get('reproduction_matches')}",
        f"- Falsification proven: {record.get('falsification_proven')}",
        "",
        "## Legs",
        "",
    ]
    for leg in record.get("legs") or []:
        lines.append(f"### {leg.get('leg')} - {'OK' if leg.get('ok') else 'NOT OK'}")
        lines.append("")
        for key, value in leg.items():
            if key in ("leg", "ok"):
                continue
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines += ["## Absolute-status note", "", str(record.get("absolute_status_note")),
              "", "## Claim ceiling", "", str(record.get("claim_ceiling")), ""]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", default=str(DEFAULT_HYPOTHESIS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    out_path = (Path(args.out) if args.out else
                _REPO_ROOT / "results/evaluation/retrieval_instrument_falsification"
                / f"{args.run_id}.json")
    report_dir = (Path(args.report_dir) if args.report_dir else
                  _REPO_ROOT / "reports/evaluation")
    report_path = report_dir / f"RETRIEVAL_INSTRUMENT_FALSIFICATION_{args.run_id}.md"
    exit_code, record = run(args.run_id, Path(args.hypothesis), out_path, report_path)
    print(json.dumps({"verdict": record.get("verdict"),
                      "headline": record.get("headline"),
                      "reproduction_matches": record.get("reproduction_matches"),
                      "falsification_proven": record.get("falsification_proven"),
                      "exit_code": exit_code}, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
