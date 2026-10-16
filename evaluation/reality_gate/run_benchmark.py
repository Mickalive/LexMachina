"""Execute the frozen reality benchmark over recorded product artifacts.

Inputs (read-only reuse of ACCEPTED product evidence, never regenerated):
  * slim reality-check leg reports (``*_ci-*.json`` / ``*_live_*.json``):
    carry question, answer_prose, cited_decision_ids, timing, structural
    signals and the producer's own gate verdicts;
  * full bundles (``*.bundle.json``): carry decisions, answer and provenance.

Every artifact is matched to a frozen question (by slug for reports, by
normalized question text for bundles).  Artifacts that match no frozen
question are reported ``unmatched`` — never silently dropped — and are still
subject to the per-bundle multilingual robustness check.

Usage:
    python -m evaluation.reality_gate.run_benchmark \
        --evidence-dir /tmp/lex_accepted/product/results/product/reality_check \
        --extra-bundle-dir /tmp/lex_accepted/product/results/product/gate_packet/38839347028/questions \
        --extra-bundle-dir /tmp/lex_accepted/product/results/product/adversarial_retrieval/38828034436 \
        --out results/evaluation/reality_benchmark/38920872324.json

Exit codes: 0 every evaluated artifact passes every measurable gate;
           1 at least one falsifying failure (negative evidence, preserved);
           2 bad arguments or absent/empty evidence input (NO verdict record is
             emitted from empty input — an empty run is an environment error,
             never a FAIL verdict);
           3 frozen benchmark integrity failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.reality_gate import frozen  # noqa: E402
from evaluation.reality_gate import gates  # noqa: E402


def _classify(data: dict) -> str:
    """Artifact kind, by shape. Fatal-error stubs and roll-ups are evidence too:
    they are recorded with their exclusion reason, never silently dropped.

    Roll-ups come in two recorded shapes: the run-level summary carrying
    ``all_legs_passed`` (with a ``legs`` array) and the minimal durable-workflow
    summary carrying only ``legs``/``mode``/``generated_at``.  Both are
    recognized by the ``legs`` list without a top-level ``slug``; a slim leg
    report always carries its own ``slug``+``leg_passed``.
    """
    if isinstance(data.get("decisions"), list) and isinstance(data.get("answer"), dict):
        return "full_bundle"
    if "slug" in data and "leg_passed" in data and "answer_prose" in data:
        return "slim_report"
    if "slug" in data and "leg_passed" in data and "fatal_error" in data:
        return "fatal_stub"
    if isinstance(data.get("legs"), list) and "slug" not in data:
        return "summary_rollup"
    return "unmatched_kind"


def _load_artifacts(evidence_dir: Path, extra_bundle_dirs: list[Path]) -> list[dict]:
    artifacts: list[dict] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path.resolve())
        if key in seen:
            return
        seen.add(key)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            artifacts.append({"artifact": str(path), "kind": "unreadable",
                              "error": f"{type(exc).__name__}: {exc}"})
            return
        if not isinstance(data, dict):
            return
        artifacts.append({"artifact": str(path), "kind": _classify(data), "data": data})

    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*.json")):
            add(path)
    for bundle_dir in extra_bundle_dirs:
        if bundle_dir.is_dir():
            for path in sorted(bundle_dir.glob("*.json")):
                add(path)
    return artifacts


def _match_bundle_question(data: dict, questions: dict[str, dict]) -> str | None:
    q = gates.normalize_text(data.get("query"))
    if not q:
        return None
    for slug, spec in questions.items():
        if gates.normalize_text(spec["question"]) == q:
            return slug
    return None


def _evaluate_slim_report(data: dict, question: dict, spec: dict) -> dict:
    prose = str(data.get("answer_prose") or "")
    cited = {str(x) for x in (data.get("answer") or {}).get("cited_decision_ids", [])}
    cited |= {str(x) for x in data.get("cited_decision_ids") or []}
    out: list[dict] = []
    out += gates.evaluate_structural_from_report(data)
    out += gates.evaluate_truth_gates(question, prose)
    out.append(gates.evaluate_language_gate(question, prose, spec))
    out.append(gates.evaluate_corruption_gate(prose))
    out.append(gates.evaluate_latency(data.get("total_seconds"),
                                     spec["latency_budget_seconds"]))
    out.append(gates.evaluate_required_hits(
        question["required_citation_ids"], cited, "citation", available=True))
    out.append(gates.evaluate_required_hits(
        question["required_retrieval_ids"], set(), "retrieval",
        available=False))
    return out


def _evaluate_full_bundle(data: dict, question: dict, spec: dict) -> dict:
    answer = data.get("answer") or {}
    prose = str(answer.get("prose") or "")
    cited = {str(x) for x in answer.get("cited_decision_ids", [])}
    retrieved = {str(d.get("decision_id")) for d in data.get("decisions", [])}
    prov = data.get("provenance") or {}
    out: list[dict] = []
    out += gates.evaluate_structural_from_bundle(data)
    out += gates.evaluate_truth_gates(question, prose)
    out.append(gates.evaluate_language_gate(question, prose, spec))
    out.append(gates.evaluate_corruption_gate(prose))
    total = prov.get("latency_seconds_total")
    if total is None:
        total = (prov.get("stages") or {}).get("total_s")
    out.append(gates.evaluate_latency(total, spec["latency_budget_seconds"]))
    out.append(gates.evaluate_required_hits(
        question["required_citation_ids"], cited, "citation", available=True))
    out.append(gates.evaluate_required_hits(
        question["required_retrieval_ids"], retrieved, "retrieval",
        available=True))
    return out


def _excluded_not_measurable(mode: str, slug: str | None, questions: dict[str, dict],
                              reason: str) -> tuple[list[str], dict[str, str]]:
    """Explicit not_measurable gate list + per-gate reasons for artifacts that
    carry no measurable fields (fatal stubs, roll-ups, unrecognized shapes).

    Truth gates are enumerated concretely when the artifact's slug matches a
    frozen question; otherwise the whole truth family is reported under one
    named placeholder.  Never silently passed, never an empty promise.
    """
    names: list[str] = []
    reasons: dict[str, str] = {}

    def add(gate: str, r: str = reason) -> None:
        names.append(gate)
        reasons[gate] = r

    structural = (gates._BUNDLE_STRUCTURAL_GATES + ("structural::geometry_preserved",
                                                    "structural::progressive_phases")
                  if mode == "full_bundle" else gates._SLIM_STRUCTURAL_GATES)
    for g in structural:
        add(g)
    question = questions.get(slug) if slug else None
    if question is not None:
        for gate in question["truth_gates"]:
            add(f"truth::{gate['id']}")
    else:
        add("truth::*")
    add("language::dominant_in_accepted")
    add("corruption::clean")
    add("latency::under_budget")
    add("recall::citation_controlling_authority")
    add("recall::retrieval_controlling_authority")
    return names, reasons


def evaluate_artifacts(artifacts: list[dict], spec: dict) -> dict:
    questions = frozen.question_by_slug(spec)
    records: list[dict] = []
    unmatched_bundles: list[dict] = []
    producer_verdicts: list[dict] = []
    bundle_structural_executions = 0

    def finalize(gate_outcomes: list[dict], **extra) -> dict:
        not_measurable = [g["gate"] for g in gate_outcomes if g["passed"] is None]
        failed = [g for g in gate_outcomes if g["passed"] is False]
        return {
            "gates": gate_outcomes,
            "not_measurable_gates": not_measurable,
            "not_measurable_reasons": {g["gate"]: g["detail"] for g in gate_outcomes
                                       if g["passed"] is None},
            "failed_gates": [g["gate"] for g in failed],
            "artifact_passed": not failed,
            **extra,
        }

    for art in artifacts:
        if art["kind"] == "unreadable":
            names, reasons = _excluded_not_measurable(
                "full_blob", None, questions,
                f"unreadable file: {art.get('error')}")
            records.append({
                "artifact": art["artifact"], "kind": art["kind"],
                "matched_slug": None,
                "error": art.get("error"),
                "exclusion": "file could not be read as JSON",
                "evaluation_scope": "none",
                "gates": [], "not_measurable_gates": names,
                "not_measurable_reasons": reasons,
                "artifact_passed": None,
            })
            continue
        if art["kind"] == "fatal_stub":
            slug = art["data"].get("slug")
            names, reasons = _excluded_not_measurable(
                "slim_report", slug, questions,
                "fatal-error stub: leg died before answer/provenance existed; "
                "error preserved as negative evidence")
            records.append({
                "artifact": art["artifact"], "kind": art["kind"],
                "matched_slug": slug,
                "exclusion": "fatal-error leg stub; error preserved as negative evidence",
                "fatal_error": art["data"].get("fatal_error"),
                "producer_leg_passed": art["data"].get("leg_passed"),
                "evaluation_scope": "none",
                "gates": [], "not_measurable_gates": names,
                "not_measurable_reasons": reasons,
                "artifact_passed": None,
            })
            continue
        if art["kind"] == "summary_rollup":
            names, reasons = _excluded_not_measurable(
                "rollup", None, questions,
                "run roll-up aggregate, not an individual leg artifact; "
                "no per-leg fields to check")
            rollup_record = {
                "artifact": art["artifact"], "kind": art["kind"],
                "matched_slug": None,
                "exclusion": "run roll-up, not an individual artifact",
                "producer_all_legs_passed": art["data"].get("all_legs_passed"),
                "evaluation_scope": "none",
                "gates": [], "not_measurable_gates": names,
                "not_measurable_reasons": reasons,
                "artifact_passed": None,
            }
            # both recorded roll-up shapes carry a per-leg array; preserve it
            # so the roll-up's own per-leg verdicts stay visible in the record
            legs = art["data"].get("legs")
            if isinstance(legs, list):
                rollup_record["producer_legs"] = [
                    {"slug": leg.get("slug"), "passed": leg.get("passed"),
                     "report": leg.get("report")}
                    for leg in legs if isinstance(leg, dict)
                ]
            records.append(rollup_record)
            continue
        if art["kind"] == "unmatched_kind":
            names, reasons = _excluded_not_measurable(
                "unknown", None, questions,
                "artifact shape not recognized as leg report, bundle, stub "
                "or roll-up; preserved as recorded, nothing measured")
            records.append({
                "artifact": art["artifact"], "kind": art["kind"],
                "matched_slug": None,
                "exclusion": "neither a leg report, bundle, stub nor roll-up",
                "evaluation_scope": "none",
                "gates": [], "not_measurable_gates": names,
                "not_measurable_reasons": reasons,
                "artifact_passed": None,
            })
            continue

        data = art["data"]
        if art["kind"] == "slim_report":
            slug = str(data.get("slug") or "")
            question = questions.get(slug)
            matched = slug if question else None
            mode = "slim_report"
        else:
            slug = _match_bundle_question(data, questions)
            question = questions.get(slug) if slug else None
            matched = slug
            mode = "full_bundle"

        if question is None:
            # Unmatched but still measurable where the artifact alone suffices
            # (audit repair R2): question-INDEPENDENT checks run on every
            # recorded artifact of report/bundle shape, matched or not.
            match_note = ("unknown report slug" if mode == "slim_report"
                          else "bundle question text matches no frozen leg")
            if mode == "full_bundle":
                gate_outcomes = gates.evaluate_question_independent_bundle(data, spec)
                unmatched_bundles.append(data)
                qdep_reason = ("bundle question matches no frozen leg; frozen "
                               "truth/language/recall gate set unknown")
            else:
                gate_outcomes = gates.evaluate_question_independent_report(data, spec)
                qdep_reason = ("report slug matches no frozen leg; frozen "
                               "truth/language/recall gate set unknown")
            qdep = gates.question_dependent_gates(mode, None, questions, qdep_reason)
            gate_outcomes = gate_outcomes + qdep
            bundle_structural_executions += sum(
                1 for g in gate_outcomes
                if g["gate"] in gates._BUNDLE_STRUCTURAL_GATES and g["passed"] is not None)
            records.append(finalize(
                gate_outcomes,
                artifact=art["artifact"], kind=mode,
                matched_slug=None, match_note=match_note,
                evaluation_scope="question_independent_only",
            ))
            continue

        if mode == "slim_report":
            gate_outcomes = _evaluate_slim_report(data, question, spec)
            producer_verdicts.append({
                "artifact": art["artifact"], "slug": slug,
                "producer_gates": data.get("gates"),
                "producer_leg_passed": data.get("leg_passed"),
            })
        else:
            gate_outcomes = _evaluate_full_bundle(data, question, spec)
            bundle_structural_executions += sum(
                1 for g in gate_outcomes
                if g["gate"] in gates._BUNDLE_STRUCTURAL_GATES and g["passed"] is not None)

        records.append(finalize(
            gate_outcomes,
            artifact=art["artifact"], kind=mode,
            matched_slug=slug,
            evaluation_scope="full_match",
        ))

    # per-bundle multilingual robustness over the unmatched recorded bundles
    ml_records: list[dict] = []
    for data in unmatched_bundles:
        import hashlib
        norm_q = gates.normalize_text(data.get("query"))
        digest = hashlib.sha256(norm_q.encode("utf-8")).hexdigest()[:6]
        label = f"{norm_q[:20]}#{digest}" if norm_q else f"bundle#{digest}"
        data = dict(data)
        data["_label"] = label
        ml_records += gates.evaluate_multilingual_coverage([data])

    evaluated = [r for r in records if r["artifact_passed"] is not None]
    failed_records = [r for r in evaluated if not r["artifact_passed"]]
    return {
        "schema": "lex-reality-benchmark/1",
        "frozen_sha256": frozen.FROZEN_SHA256,
        "frozen_direction_version": spec.get("direction_version"),
        "latency_budget_seconds": spec["latency_budget_seconds"],
        "n_artifacts": len(artifacts),
        "n_evaluated": len(evaluated),
        "n_full_match_evaluated": sum(
            1 for r in records if r.get("evaluation_scope") == "full_match"),
        "n_question_independent_evaluated": sum(
            1 for r in records if r.get("evaluation_scope") == "question_independent_only"),
        "n_excluded_no_verdict": sum(
            1 for r in records if r.get("evaluation_scope") == "none"),
        "n_unmatched": len(records) - len(evaluated),
        "n_unreadable": sum(1 for r in records if r.get("error")),
        "bundle_structural_gate_executions": bundle_structural_executions,
        "artifacts": records,
        "multilingual_checks": ml_records,
        "producer_verdicts_preserved": producer_verdicts,
        "overall_pass": bool(evaluated) and not failed_records
        and all(m["passed"] for m in ml_records),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence-dir", required=True,
                    help="directory of recorded slim reality-check leg reports")
    ap.add_argument("--extra-bundle-dir", action="append", default=[],
                    help="additional directory of full *.bundle.json (repeatable)")
    ap.add_argument("--out", default=None, help="where to write the benchmark report")
    args = ap.parse_args(argv)

    try:
        spec = frozen.load_frozen()
    except frozen.FrozenBenchmarkError as exc:
        print(f"::error::frozen benchmark integrity failure: {exc}", file=sys.stderr)
        return 3

    evidence = Path(args.evidence_dir)
    if not evidence.is_dir():
        print(f"::error::evidence directory does not exist: {evidence}",
              file=sys.stderr)
        return 2
    extra_dirs: list[Path] = []
    for raw in args.extra_bundle_dir:
        p = Path(raw)
        if not p.is_dir():
            print(f"::warning::extra bundle directory not found, skipped: {p}",
                  file=sys.stderr)
        else:
            extra_dirs.append(p)

    artifacts = _load_artifacts(evidence, extra_dirs)
    if not artifacts:
        print("::error::no readable artifacts found in any evidence directory; "
              "refusing to emit a verdict record from empty input",
              file=sys.stderr)
        return 2
    report = evaluate_artifacts(artifacts, spec)

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")

    print(f"frozen benchmark v{spec['direction_version']} "
          f"(sha {frozen.FROZEN_SHA256[:12]}…) over {report['n_artifacts']} artifacts:")
    for rec in report["artifacts"]:
        name = rec["artifact"].rsplit("/", 1)[-1]
        if rec.get("error"):
            print(f"  [UNREADABLE] {name}: {rec['error'][:80]}")
        elif rec["kind"] == "fatal_stub":
            print(f"  [FATAL-STUB] {name}: {str(rec.get('fatal_error'))[:80]}")
        elif rec["kind"] == "summary_rollup":
            print(f"  [ROLLUP]     {name} (all_legs_passed="
                  f"{rec.get('producer_all_legs_passed')})")
        elif rec["kind"] == "unmatched_kind":
            print(f"  [SKIP]       {name} ({rec.get('exclusion', '')[:40]})")
        elif rec["artifact_passed"] is None:
            print(f"  [UNMATCHED]  {name} — {rec.get('match_note', '')[:60]}")
        else:
            mark = "PASS" if rec["artifact_passed"] else "FAIL"
            slug = rec.get("matched_slug") or f"<{rec.get('evaluation_scope', '?')}>"
            line = f"  [{mark}] {slug:32s} {name}"
            if rec["failed_gates"]:
                line += f"  failed={rec['failed_gates']}"
            if rec["not_measurable_gates"]:
                line += f"  n/m={len(rec['not_measurable_gates'])}"
            print(line)
    for m in report["multilingual_checks"]:
        mark = "PASS" if m["passed"] else "FAIL"
        print(f"  [{mark}] {m['gate']}: {m['detail'][:70]}")
    print(f"\noverall: {'PASS' if report['overall_pass'] else 'FAIL'} "
          f"({report['n_full_match_evaluated']} full-match + "
          f"{report['n_question_independent_evaluated']} question-independent "
          f"evaluated, {report['n_excluded_no_verdict']} excluded without verdict; "
          f"{report['bundle_structural_gate_executions']} bundle-structural gate "
          f"executions)")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
