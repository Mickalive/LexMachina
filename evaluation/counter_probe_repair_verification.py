#!/usr/bin/env python3
"""Counter-probe REPAIR-VERIFICATION falsifier (freeze-first, run 39687372110).

    python -m evaluation.counter_probe_repair_verification \
        --run-id 39687372110 \
        --out results/evaluation/counter_probe_repair_verification/39687372110.json \
        --report reports/evaluation/COUNTER_PROBE_REPAIR_VERIFICATION_39687372110.md

WHAT THIS MEASURES
------------------
The accepted EXPLORATORY falsifier run 39674402905
(``evaluation/counter_probe_anchor_falsifier.py``, COUNTER_PROBE_ANCHOR_FALSIFIED)
established, on the 14-bundle accepted product population, that the generative
audit's redaction placeholder ``[citation removed: not in retrieved set]``
displaces real legal vocabulary out of the four-slot TOPIC ANCHOR of the
product's issued counter-authority probes on the two German bundles of packets
39275520116 and 39319405429, and that its published G4 de-redaction
counterfactual (strip ONLY the placeholder occurrences from the answer prose,
re-plan with the product's own planner) restores a topical anchor on exactly
those two bundles while being a no-op on the other twelve.

The product lane's ordered remedy for that bounded cause — handed off in
``state/evaluation.json -> counter_probe_anchor_falsifier.product_handoff`` — is
remedy (a): exclude the redaction placeholder from the probe key terms in
``product/query/adversarial_retrieval.py``.  As of the product mount pinned
below, that fix has NOT landed: the shipped planner still anchors on the raw
post-redaction prose.

This instrument converts the accepted counterfactual into a FALSIFIABLE REPAIR
CONTRACT with gates and exit codes, and re-measures the counterfactual arm with
its own committed code path so the prediction is a cross-instrument
verification rather than a re-quotation:

    BASELINE arm  = product.plan_adversarial_queries(query, prose)          (shipped behaviour)
    FIXED    arm  = product.plan_adversarial_queries(query,
                     prose.replace(REDACTION_PLACEHOLDER, " "))             (emulates remedy (a))

Per bundle it then checks four gates (below) and five controls, and publishes
the exact repaired probe strings so the product lane has an acceptance fixture.

WHY IT IS NOT A DUPLICATION OF ACCEPTED WORK
-------------------------------------------
* The accepted falsifier 39674402905 measures the SHIPPED anchor and reports a
  de-redaction counterfactual as REPORTED-ONLY diagnosis.  This instrument makes
  that counterfactual the CLAIM UNDER TEST (the repair prediction), freezes it
  as gates G1-G4 with exit codes, and cross-checks its own computation against
  the accepted record's published G4 arm byte-for-byte (gate G4).
* No frozen bar, rubric, verdict contract or absolute threshold is read for
  enforcement, edited, re-derived or paraphrased.  RULES_LABEL.json /
  RULES_GEOMETRY.json / VERDICT_CONTRACT.json are not inputs.

EXIT CODES (frozen; see the hypothesis file for the full contract)
------------------------------------------------------------------
0  REPAIR_VERIFIED_ON_RECORDED_BYTES   — all four gates and all five controls
   hold: on the recorded bytes the recommended remedy (a) removes every
   placeholder-derived anchor token, restores a topical anchor on both
   contaminated bundles, is a byte-for-byte no-op on the twelve clean-anchor
   bundles, and reproduces the accepted falsifier's published G4 anchors.
1  REPAIR_INSUFFICIENT_ON_RECORDED_BYTES — at least one gate fails while all
   controls hold: the remedy as specified would NOT repair the bounded cause
   on these bytes.
2  ENVIRONMENT_OR_VACUOUS — a pin drifted, a control failed, the population was
   empty, or the product bytes no longer reproduce the recorded probes (the
   shipped behaviour changed — re-freeze against the new accepted measurement).
   Never a product verdict.

The instrument is dependency-light on purpose: it imports the ACCEPTED
falsifier's own ``ProductCode`` loader, population, manifest and pin machinery,
so the product's tokenisation, stoplist, planner and placeholder constant are
never re-implemented here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation import counter_probe_anchor_falsifier as cpa

SCHEMA = "lex-evaluation-counter-probe-repair-verification/1"

ANCHOR_SLOTS = cpa.ANCHOR_SLOTS
EXIT_OK = 0
EXIT_INSUFFICIENT = 1
EXIT_ENVIRONMENT = 2

DEFAULT_PRODUCT_ROOT = "/tmp/lex_accepted/product"
DEFAULT_SECONDARY = "results/evaluation/rebuilt_packet_adjudication_39049030442/packet"
DEFAULT_ACCEPTED_RECORD = (
    "results/evaluation/counter_probe_anchor_falsifier/39674402905.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# per-bundle two-arm measurement
# --------------------------------------------------------------------------- #


def _queries_of(plan: list[dict]) -> list[str]:
    return [str(p.get("query") or "") for p in plan]


def measure_bundle(item: dict, product: cpa.ProductCode, *,
                   accepted_row: dict | None, packet_label: str) -> dict:
    path: Path = item["path"]
    bundle: dict = item["bundle"]
    ar = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    probes = ar.get("probes") or []
    prose = str((bundle.get("answer") or {}).get("prose") or "")
    query = str(bundle.get("query") or "")
    placeholder = product.redaction_placeholder

    recorded_queries = [str(p.get("query") or "") for p in probes]
    recorded_anchor = cpa._anchor_of(recorded_queries[0]) if recorded_queries else []

    # --- BASELINE arm: the shipped planner on the shipped prose --------------
    baseline_plan = product.plan_adversarial_queries(query, prose)
    baseline_queries = _queries_of(baseline_plan)
    baseline_anchor = cpa._anchor_of(baseline_queries[0]) if baseline_queries else []

    # --- FIXED arm: remedy (a) emulated — strip the placeholder, re-plan -----
    de_redacted = prose.replace(placeholder, " ")
    fixed_plan = product.plan_adversarial_queries(query, de_redacted)
    fixed_queries = _queries_of(fixed_plan)
    fixed_anchor = cpa._anchor_of(fixed_queries[0]) if fixed_queries else []

    # --- gate observables ----------------------------------------------------
    ph_tokens = product.placeholder_tokens()
    g1_tokens = sorted(set(fixed_anchor) & set(ph_tokens))

    q_terms = product.content_terms(query)
    g2_topical = sorted(set(fixed_anchor) & q_terms)

    baseline_contaminated = bool(set(baseline_anchor) & set(ph_tokens))
    g3_noop = fixed_queries == baseline_queries

    accepted_g4_anchor = None
    if accepted_row is not None:
        accepted_g4_anchor = list(
            (accepted_row.get("G4_counterfactual") or {}).get("de_redacted_anchor") or [])
    g4_match = (fixed_anchor == accepted_g4_anchor) if accepted_g4_anchor is not None else None

    n_ph = prose.count(placeholder)

    return {
        "packet": packet_label,
        "source_path": str(path),
        "source_sha256": cpa.sha256_file(path),
        "query_head": query[:200],
        "n_probe_plans": len(probes),
        "placeholder_occurrences_in_prose": n_ph,
        "baseline_reproduces_recorded": baseline_queries == recorded_queries,
        "baseline_anchor": baseline_anchor,
        "baseline_anchor_contaminated": baseline_contaminated,
        "fixed_anchor": fixed_anchor,
        "G1_fixed_anchor_placeholder_tokens": g1_tokens,
        "G1_fixed_anchor_clean": not g1_tokens,
        "G2_fixed_anchor_question_terms": g2_topical,
        "G2_required": baseline_contaminated,
        "G2_fixed_anchor_topical": bool(g2_topical),
        "G3_fixed_equals_baseline": g3_noop,
        "G3_required": not baseline_contaminated,
        "G4_accepted_de_redacted_anchor": accepted_g4_anchor,
        "G4_fixed_matches_accepted": g4_match,
        "C5_baseline_had_plan": bool(baseline_queries),
        "C5_fixed_had_plan": bool(fixed_queries),
        "C4_placeholder_absent_noop": (g3_noop if n_ph == 0 else None),
        "recorded_probe_queries": recorded_queries,
        "baseline_probe_queries": baseline_queries,
        "fixed_probe_queries": fixed_queries,
        "probe_query_diff": [
            {"index": i, "baseline": b, "fixed": f}
            for i, (b, f) in enumerate(zip(baseline_queries, fixed_queries))
            if b != f
        ],
    }


# --------------------------------------------------------------------------- #
# gates and controls
# --------------------------------------------------------------------------- #


def run_gates(measurements: list[dict]) -> dict:
    g1_bad = [m["source_path"] for m in measurements if not m["G1_fixed_anchor_clean"]]
    g2_required = [m for m in measurements if m["G2_required"]]
    g2_bad = [m["source_path"] for m in g2_required if not m["G2_fixed_anchor_topical"]]
    g3_required = [m for m in measurements if m["G3_required"]]
    g3_bad = [m["source_path"] for m in g3_required if not m["G3_fixed_equals_baseline"]]
    g4_rows = [m for m in measurements if m["G4_fixed_matches_accepted"] is not None]
    g4_bad = [m["source_path"] for m in g4_rows if not m["G4_fixed_matches_accepted"]]
    return {
        "G1_no_placeholder_token_in_fixed_anchor": {
            "description": ("the FIXED arm's topic anchor contains no token the "
                            "product's own answer_key_terms extracts from the "
                            "redaction placeholder, on every measured bundle"),
            "passed": not g1_bad,
            "n_bundles": len(measurements),
            "n_failed": len(g1_bad),
            "failed": g1_bad,
        },
        "G2_fixed_anchor_topical_on_contaminated_bundles": {
            "description": ("on every bundle whose BASELINE anchor is "
                            "placeholder-contaminated, the FIXED anchor shares at "
                            "least one content term (product pool rule) with the "
                            "question it is supposed to attack"),
            "passed": bool(g2_required) and not g2_bad,
            "n_required": len(g2_required),
            "n_failed": len(g2_bad),
            "failed": g2_bad,
        },
        "G3_fixed_is_noop_on_clean_anchor_bundles": {
            "description": ("on every bundle whose BASELINE anchor is NOT "
                            "contaminated, the FIXED arm issues byte-for-byte the "
                            "same probe queries as the BASELINE arm — the remedy "
                            "must not perturb working probes"),
            "passed": bool(g3_required) and not g3_bad,
            "n_required": len(g3_required),
            "n_failed": len(g3_bad),
            "failed": g3_bad,
        },
        "G4_fixed_matches_accepted_counterfactual": {
            "description": ("the FIXED arm's anchor equals, byte-for-byte, the G4 "
                            "de-redacted anchor published by the accepted falsifier "
                            "record 39674402905, on every bundle where that record "
                            "published one — two separately committed computations "
                            "of the remedy must agree"),
            "passed": bool(g4_rows) and not g4_bad,
            "n_compared": len(g4_rows),
            "n_failed": len(g4_bad),
            "failed": g4_bad,
        },
    }


def run_controls(measurements: list[dict], product: cpa.ProductCode) -> dict:
    controls: dict[str, dict] = {}

    bad = [m["source_path"] for m in measurements if not m["baseline_reproduces_recorded"]]
    controls["C1_baseline_reproduces_recorded_probes"] = {
        "description": ("the BASELINE arm (product's own planner on the bundle's "
                        "own recorded prose) reproduces every recorded probe query "
                        "byte-for-byte, so the measurement is faithful to the "
                        "shipped behaviour"),
        "passed": not bad,
        "n_bundles": len(measurements),
        "n_failed": len(bad),
        "failed": bad,
    }

    ph_only = " " * 8 + str(product.redaction_placeholder) * 3
    blank_fixed = product.plan_adversarial_queries(
        "Arbeitsvertrag Kündigung", ph_only.replace(str(product.redaction_placeholder), " "))
    blank_base = product.plan_adversarial_queries("Arbeitsvertrag Kündigung", "")
    controls["C2_blank_prose_yields_no_plan_in_both_arms"] = {
        "description": ("after the remedy, a prose consisting only of the "
                        "placeholder still yields NO probe plan (the product's D4 "
                        "vacuity guard is restored for placeholder-only prose), "
                        "and a blank prose yields none in the BASELINE arm"),
        "passed": blank_fixed == [] and blank_base == [],
        "n_plans_fixed": len(blank_fixed),
        "n_plans_baseline": len(blank_base),
    }

    n_contaminated = sum(1 for m in measurements if m["baseline_anchor_contaminated"])
    controls["C3_repair_target_exists"] = {
        "description": ("at least one measured bundle has a BASELINE "
                        "placeholder-contaminated anchor, so the repair target "
                        "still exists on the pinned bytes (non-vacuity)"),
        "passed": n_contaminated >= 1,
        "n_baseline_contaminated": n_contaminated,
    }

    placebo_bad = [m["source_path"] for m in measurements
                   if m["C4_placeholder_absent_noop"] is not True]
    controls["C4_fix_is_noop_without_the_placeholder"] = {
        "description": ("for every bundle whose answer prose contains no redaction "
                        "placeholder, the FIXED arm is a byte-for-byte no-op — the "
                        "shim's own placebo arm"),
        "passed": not placebo_bad,
        "n_failed": len(placebo_bad),
        "failed": placebo_bad,
    }

    death = [m["source_path"] for m in measurements
             if m["C5_baseline_had_plan"] and not m["C5_fixed_had_plan"]]
    controls["C5_fix_does_not_kill_probe_emission"] = {
        "description": ("every bundle whose BASELINE arm emitted at least one probe "
                        "plan still emits at least one under the FIXED arm"),
        "passed": not death,
        "n_failed": len(death),
        "failed": death,
    }

    return controls


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def render_report(record: dict) -> str:
    lines: list[str] = []
    a = lines.append
    a(f"# Counter-probe repair-verification falsifier — run {record['run_id']}")
    a("")
    a(f"**Verdict: `{record['verdict']}`** (exit {record['exit_code']})")
    a("")
    a(record["verdict_statement"])
    a("")
    a("## What was measured")
    a("")
    a("Two arms per bundle of the accepted 14-bundle population, both computed "
      "with the product's OWN `plan_adversarial_queries`:")
    a("")
    a("- **BASELINE** — the shipped planner on the shipped (post-redaction) "
      "answer prose; must reproduce the recorded probes byte-for-byte (C1).")
    a("- **FIXED** — the recommended remedy (a) emulated: the redaction "
      "placeholder stripped from the answer prose, then the same planner.")
    a("")
    a("## Population")
    a("")
    a(f"- source: `{record['source']['label']}` (`{record['source']['root']}`)")
    a(f"- measurable bundles: **{record['n_bundles']}**")
    a(f"- population manifest sha256: `{record['source']['manifest_sha256']}`")
    a("")
    a("## Gates")
    a("")
    a("| gate | result | detail |")
    a("|---|---|---|")
    for name, g in record["gates"].items():
        detail = ", ".join(f"{k}={v}" for k, v in g.items()
                           if k not in ("description", "passed", "failed"))
        a(f"| `{name}` | {'PASS' if g['passed'] else 'FAIL'} | {detail} |")
    a("")
    a("## Per-bundle result")
    a("")
    a("| packet | lang | ph | baseline anchor | contaminated | fixed anchor | "
      "G1 clean | G2 topical | G3 noop | G4 match |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for m in record["bundles"]:
        a(f"| {m['packet']} | {m['language']} | {m['placeholder_occurrences_in_prose']} | "
          f"`{' '.join(m['baseline_anchor'])}` | "
          f"{'**YES**' if m['baseline_anchor_contaminated'] else 'no'} | "
          f"`{' '.join(m['fixed_anchor'])}` | "
          f"{'yes' if m['G1_fixed_anchor_clean'] else '**NO**'} | "
          f"{'yes' if m['G2_fixed_anchor_topical'] else ('n/a' if not m['G2_required'] else '**NO**')} | "
          f"{'yes' if m['G3_fixed_equals_baseline'] else ('n/a' if not m['G3_required'] else '**NO**')} | "
          f"{'yes' if m['G4_fixed_matches_accepted'] else 'no/n/a'} |")
    a("")
    a("`ph` = occurrences of the redaction placeholder in the answer prose. "
      "`G2 topical`/`G3 noop` are gates only where marked required "
      "(contaminated baseline anchors / clean baseline anchors respectively).")
    a("")
    a("## Repaired probe queries on the contaminated bundles (acceptance fixture)")
    a("")
    for m in record["bundles"]:
        if m["probe_query_diff"]:
            a(f"### {m['packet']} / {m['language']}")
            a("")
            for d in m["probe_query_diff"]:
                a(f"- intent#{d['index']}: `{d['baseline']}` → `{d['fixed']}`")
            a("")
    a("## Controls")
    a("")
    a("| control | result | detail |")
    a("|---|---|---|")
    for name, c in record["controls"].items():
        detail = ", ".join(f"{k}={v}" for k, v in c.items()
                           if k not in ("description", "passed", "failed"))
        a(f"| `{name}` | {'PASS' if c['passed'] else 'FAIL'} | {detail} |")
    a("")
    a("## Pin discipline")
    a("")
    a(f"- pins re-hashed BEFORE execution: {record['pins_before']['n_checks']} "
      f"checks, all_ok={record['pins_before']['all_ok']}")
    a(f"- pins re-hashed AFTER execution: {record['pins_after']['n_checks']} "
      f"checks, all_ok={record['pins_after']['all_ok']}")
    a("")
    a("## Claim ceiling")
    a("")
    a(record["claim_ceiling"])
    a("")
    a("## Pre-freeze disclosure")
    a("")
    a(record["pre_freeze_disclosure"])
    a("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="39687372110")
    ap.add_argument("--product-root", default=DEFAULT_PRODUCT_ROOT)
    ap.add_argument("--secondary", default=DEFAULT_SECONDARY)
    ap.add_argument("--source", choices=("auto", "mount", "secondary"),
                    default="auto")
    ap.add_argument("--accepted-record", default=DEFAULT_ACCEPTED_RECORD)
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--freeze-record", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--selftest", action="store_true",
                    help="structural self-test on SYNTHETIC prose only; never "
                         "touches the real population and never writes a result "
                         "file")
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    product_root = Path(args.product_root)

    if args.selftest:
        return _selftest(product_root)

    hypothesis_path = Path(args.hypothesis) if args.hypothesis else (
        repo_root / "evaluation/COUNTER_PROBE_REPAIR_VERIFICATION_HYPOTHESIS_V1.json")
    freeze_path = Path(args.freeze_record) if args.freeze_record else (
        repo_root / "evaluation/COUNTER_PROBE_REPAIR_VERIFICATION_FREEZE_RECORD_V1.json")

    for p in (hypothesis_path, freeze_path):
        if not p.is_file():
            print(f"::error::missing frozen input: {p}", file=sys.stderr)
            return EXIT_ENVIRONMENT
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    hypothesis = json.loads(hypothesis_path.read_text(encoding="utf-8"))

    accepted_record_path = Path(args.accepted_record)
    if not accepted_record_path.is_absolute():
        accepted_record_path = repo_root / accepted_record_path
    if not accepted_record_path.is_file():
        print(f"::error::accepted falsifier record missing: {accepted_record_path}",
              file=sys.stderr)
        return EXIT_ENVIRONMENT
    accepted = json.loads(accepted_record_path.read_text(encoding="utf-8"))
    accepted_by_path = {str(b.get("source_path")): b
                        for b in (accepted.get("bundles") or [])}

    # -- source selection ---------------------------------------------------
    secondary_root = Path(args.secondary)
    if not secondary_root.is_absolute():
        secondary_root = repo_root / secondary_root
    if args.source == "mount" or (args.source == "auto"
                                  and (product_root / "results/product").is_dir()):
        source_label, source_root = "mount", product_root
    elif args.source == "secondary" or secondary_root.is_dir():
        source_label, source_root = "secondary", secondary_root
    else:
        print("::error::no product source available", file=sys.stderr)
        return EXIT_ENVIRONMENT

    # -- pins BEFORE --------------------------------------------------------
    pins_before = cpa.rehash_pins(freeze, repo_root, source_root, source_label)
    if not pins_before["all_ok"]:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before,
                                     "pin drift before execution "
                                     "(if the product pins drifted, the shipped "
                                     "behaviour has changed since the accepted "
                                     "measurement — re-freeze under a new run id)")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    # -- product code -------------------------------------------------------
    try:
        product = cpa.ProductCode(source_root)
    except Exception as exc:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before,
                                     f"product code could not be loaded: "
                                     f"{type(exc).__name__}: {exc}")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    # -- measure ------------------------------------------------------------
    items = cpa.population(source_root)
    if not items:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before, "no measurable bundle")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    measurements: list[dict] = []
    for item in items:
        packet, lang = cpa._label_of(item["path"], item["bundle"], source_label)
        accepted_row = accepted_by_path.get(str(item["path"]))
        m = measure_bundle(item, product, accepted_row=accepted_row,
                           packet_label=packet)
        m["language"] = lang
        m["question_slug"] = item["path"].stem
        m["accepted_record_row_found"] = accepted_row is not None
        measurements.append(m)

    gates = run_gates(measurements)
    controls = run_controls(measurements, product)
    control_failures = [n for n, c in controls.items() if not c["passed"]]
    gate_failures = [n for n, g in gates.items() if not g["passed"]]

    n_compared_g4 = sum(1 for m in measurements
                        if m["G4_fixed_matches_accepted"] is not None)
    if n_compared_g4 == 0:
        control_failures.append("G4_NO_ACCEPTED_ROWS_COMPARABLE")

    if control_failures:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_ENVIRONMENT
        statement = ("a non-vacuity control failed "
                     f"({', '.join(control_failures)}); this run is NOT a product "
                     "verdict and no repair claim is made.")
    elif gate_failures:
        verdict = "REPAIR_INSUFFICIENT_ON_RECORDED_BYTES"
        exit_code = EXIT_INSUFFICIENT
        statement = (
            "the recommended remedy (a) — strip the redaction placeholder from "
            "the answer prose before the product's own probe planner — does NOT "
            "fully repair the bounded cause on the pinned recorded bytes: "
            f"{', '.join(gate_failures)} failed while all five controls held. "
            "The product lane must not treat remedy (a) as sufficient on these "
            "bytes.")
    else:
        verdict = "REPAIR_VERIFIED_ON_RECORDED_BYTES"
        exit_code = EXIT_OK
        statement = (
            "on the pinned recorded bytes of the accepted 14-bundle population, "
            "the recommended remedy (a) repairs the probe-anchor bounded cause: "
            "every FIXED anchor is free of placeholder-derived tokens (G1), both "
            "baseline-contaminated German anchors regain a topical anchor (G2), "
            "the twelve clean-anchor bundles are byte-for-byte unperturbed (G3), "
            "and every FIXED anchor equals the accepted falsifier record "
            "39674402905's published G4 de-redacted anchor (G4), with all five "
            "controls held. This is a repair VERIFICATION on recorded bytes, not "
            "a live-retrieval or counter-authority-recall measurement.")

    # -- pins AFTER ---------------------------------------------------------
    pins_after = cpa.rehash_pins(freeze, repo_root, source_root, source_label)
    if not pins_after["all_ok"]:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_ENVIRONMENT
        statement = "pin drift after execution; this run is NOT a product verdict."

    record = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "generated_at_utc": _now(),
        "direction_version": hypothesis.get("direction_version"),
        "verdict": verdict,
        "exit_code": exit_code,
        "verdict_statement": statement,
        "source": {
            "label": source_label,
            "root": str(source_root),
            "manifest_sha256": cpa.manifest(source_root)["manifest_sha256"],
        },
        "accepted_falsifier_record": {
            "path": str(accepted_record_path.relative_to(repo_root))
            if accepted_record_path.is_relative_to(repo_root)
            else str(accepted_record_path),
            "sha256": cpa.sha256_file(accepted_record_path),
            "verdict": accepted.get("verdict"),
            "n_rows_compared": n_compared_g4,
        },
        "n_bundles": len(measurements),
        "n_baseline_contaminated": sum(1 for m in measurements
                                       if m["baseline_anchor_contaminated"]),
        "n_fixed_contaminated": sum(1 for m in measurements
                                    if not m["G1_fixed_anchor_clean"]),
        "placeholder_tokens": product.placeholder_tokens(),
        "redaction_placeholder": product.redaction_placeholder,
        "frozen_rule": freeze.get("frozen_rule"),
        "exit_code_contract": freeze.get("exit_code_contract"),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "gates": gates,
        "controls": controls,
        "control_failures": control_failures,
        "gate_failures": gate_failures,
        "bundles": measurements,
        "claim_ceiling": hypothesis.get("claim_ceiling"),
        "pre_freeze_disclosure": hypothesis.get("pre_freeze_disclosure"),
        "frozen_hypothesis": str(hypothesis_path.relative_to(repo_root)),
        "frozen_hypothesis_sha256": cpa.sha256_file(hypothesis_path),
        "freeze_record": str(freeze_path.relative_to(repo_root)),
        "freeze_record_sha256": cpa.sha256_file(freeze_path),
        "instrument": "evaluation/counter_probe_repair_verification.py",
        "instrument_sha256": cpa.sha256_file(Path(__file__).resolve()),
        "accepted_instrument_reused": "evaluation/counter_probe_anchor_falsifier.py",
        "network_calls": 0,
    }
    _write(args.out, args.report, record)
    print(f"verdict: {verdict} (exit {exit_code})")
    print(f"bundles measured: {len(measurements)}; baseline contaminated: "
          f"{record['n_baseline_contaminated']}; fixed contaminated: "
          f"{record['n_fixed_contaminated']}")
    for name, g in gates.items():
        print(f"  gate {name}: {'PASS' if g['passed'] else 'FAIL'}")
    return exit_code


def _environment_record(run_id: str, label: str, root: Path, pins: dict,
                        why: str) -> dict:
    return {
        "schema": SCHEMA, "run_id": run_id, "generated_at_utc": _now(),
        "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENVIRONMENT,
        "verdict_statement": f"{why}; this run is NOT a product verdict.",
        "source": {"label": label, "root": str(root), "manifest_sha256": None},
        "n_bundles": 0, "n_baseline_contaminated": 0, "n_fixed_contaminated": 0,
        "pins_before": pins, "pins_after": None, "gates": {}, "controls": {},
        "control_failures": [], "gate_failures": [], "bundles": [],
        "claim_ceiling": "not measured; no repair claim is made.",
        "pre_freeze_disclosure": "not measured; no repair claim is made.",
        "network_calls": 0,
    }


def _write(out: str | None, report: str | None, record: dict) -> None:
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, ensure_ascii=False, indent=2,
                                sort_keys=True) + "\n", encoding="utf-8")
        print(f"record: {p}")
    if report:
        p = Path(report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_report(record), encoding="utf-8")
        print(f"report: {p}")


def _selftest(product_root: Path) -> int:
    """Structural self-test on SYNTHETIC prose only.  Never touches the real
    population, never writes a result file."""
    try:
        product = cpa.ProductCode(product_root)
    except Exception as exc:
        print(f"SELFTEST FAIL: product code could not be loaded: "
              f"{type(exc).__name__}: {exc}")
        return EXIT_ENVIRONMENT

    failures: list[str] = []
    ph = product.redaction_placeholder
    ph_tokens = product.placeholder_tokens()
    if not ph or not ph_tokens:
        failures.append("placeholder or its key tokens empty")

    legal = ("Der Arbeitgeber schuldet aktive Fürsorgepflicht und Überwachung "
             "der Kapitalverletzung. ")
    contaminated_prose = (ph * 6) + legal * 4
    clean_prose = legal * 4

    base_c = product.plan_adversarial_queries("Kapitalverletzung Fürsorgepflicht",
                                              contaminated_prose)
    fix_c = product.plan_adversarial_queries(
        "Kapitalverletzung Fürsorgepflicht",
        contaminated_prose.replace(ph, " "))
    if not base_c or not fix_c:
        failures.append("synthetic contaminated prose yielded no plan in an arm")
    else:
        ba = cpa._anchor_of(base_c[0]["query"])
        fa = cpa._anchor_of(fix_c[0]["query"])
        if not (set(ba) & set(ph_tokens)):
            failures.append(f"synthetic baseline not contaminated: {ba}")
        if set(fa) & set(ph_tokens):
            failures.append(f"synthetic fixed arm still contaminated: {fa}")
        if not (set(fa) & product.content_terms("Kapitalverletzung Fürsorgepflicht")):
            failures.append(f"synthetic fixed anchor not topical: {fa}")

    base_n = product.plan_adversarial_queries("Kapitalverletzung Fürsorgepflicht",
                                              clean_prose)
    fix_n = product.plan_adversarial_queries(
        "Kapitalverletzung Fürsorgepflicht", clean_prose.replace(ph, " "))
    if _queries_of(base_n) != _queries_of(fix_n):
        failures.append("synthetic clean prose: fixed arm is not a no-op")

    # The D4 guard is RESTORED by the remedy for placeholder-only prose: the
    # BASELINE arm on such prose yields a contaminated plan (that is the defect,
    # reproduced synthetically), while the FIXED arm must yield none.
    base_ph_only = product.plan_adversarial_queries("Kapitalvertrag", " " + ph * 3)
    fix_ph_only = product.plan_adversarial_queries(
        "Kapitalvertrag", (" " + ph * 3).replace(ph, " "))
    if base_ph_only == []:
        failures.append("synthetic placeholder-only baseline unexpectedly empty")
    if fix_ph_only != []:
        failures.append("fixed arm on placeholder-only prose did not restore "
                        "the D4 guard")

    for f in failures:
        print(f"SELFTEST FAIL: {f}")
    if failures:
        return EXIT_ENVIRONMENT
    print("SELFTEST PASS: loader, contaminated synthetic baseline, fixed-arm "
          "de-contamination + topicality, clean-prose no-op, D4 guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
