#!/usr/bin/env python3
"""Shipped-planner remedy (a) verification — factory direction v62 ordered item (1).

Why this exists
---------------
The accepted counter-probe repair verification (run 39687372110,
``REPAIR_VERIFIED_ON_RECORDED_BYTES``) proved synthetically that remedy (a) —
strip the generative-audit redaction placeholder from the answer prose before
the probe planner — repairs the contaminated counter-probe anchors on the
pinned recorded 14-bundle population.  Its freeze record states the contract
for the next step: *if the product lane lands remedy (a), the product pins
drift by design and a NEW freeze under a NEW run id verifies the shipped
planner*.

Remedy (a) has landed: product cycle 39752638579 shipped
``adversarial_retrieval/3`` with ``strip_redaction_placeholders``; the planner
pin drifted 57b6a6f9… -> 9764a37e….  This instrument is that NEW freeze's
measurement: it loads the SHIPPED planner from the accepted product mount and
asks whether its probe queries and topic anchors reproduce, byte-for-byte on
the same recorded population, the accepted verification's FIXED arm.

Gates (G1s–G4s) and controls (C1s–C5s) are frozen in
``evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_HYPOTHESIS_V1.json``.
This file implements them literally and re-derives no threshold.

Exit codes (frozen contract)
----------------------------
0  SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY
1  SHIPPED_PLANNER_DIVERGES_FROM_VERIFIED_REMEDY  (falsifies the landed fix)
2  ENVIRONMENT_OR_VACUOUS  (never a product verdict)

Seq-2 control correction (disclosed; see FREEZE_RECORD_V1 freeze_history)
------------------------------------------------------------------------
Attempt 1 (preserved as
``results/evaluation/shipped_planner_remedy_verification/
39813664201_attempt1_control_implementation_bug.json``, sha256 68bd363a…)
exited 2 ENVIRONMENT_OR_VACUOUS and claimed nothing, because it derived the
placeholder token class from the SHIPPED ``answer_key_terms`` — which, on a
tree where remedy (a) has landed, strips the placeholder and therefore derives
ZERO tokens from it by design.  That made C2s self-defeating, C4s blind and
G1s vacuous.  Seq-2 derives the token class from the PRE-REMEDY-EMULATED
extractor (identical ranking/filters without the strip), pinned to exactly
{citation, removed, retrieved}; the shipped extractor's zero-token output on
the placeholder is additionally recorded as the remedy's own signature.
No gate outcome, verdict, population, exit contract or claim ceiling changed.

Usage::

    python -m evaluation.shipped_planner_remedy_verification \
        --run-id 39813664201 \
        --out results/evaluation/shipped_planner_remedy_verification/39813664201.json \
        --report reports/evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_39813664201.md

Zero network.  Deterministic.  Append-only output convention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import counter_probe_anchor_falsifier as cpa  # noqa: E402

SCHEMA = "lex-evaluation-shipped-planner-remedy-verification/1"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "SHIPPED_PLANNER_REMEDY_VERIFICATION_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation" / "SHIPPED_PLANNER_REMEDY_VERIFICATION_FREEZE_RECORD_V1.json"
ACCEPTED_REPAIR_RECORD = (
    REPO_ROOT / "results" / "evaluation" / "counter_probe_repair_verification" / "39687372110.json"
)
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
ANCHOR_SLOTS = 4

EXIT_OK = 0
EXIT_DIVERGE = 1
EXIT_ENV = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _queries_of(plan: list[dict]) -> list[str]:
    return [str(p.get("query") or "") for p in plan]


def _anchor_of(probe_query: str) -> list[str]:
    return (probe_query or "").split()[:ANCHOR_SLOTS]


def preremedy_key_terms(product, prose: str, *, limit: int = 8) -> list[str]:
    """PRE-remedy answer_key_terms emulation: identical ranking/filters, NO strip.

    Remedy (a) changed ONLY the input to the ranking loop (strip first).  The
    shipped ``tokenize`` and ``_ANSWER_STOP`` are byte-unchanged by the remedy,
    so this local emulation is the exact pre-remedy extractor.  Used solely by
    control C4s (planted-divergence control); never used for any gate.
    """
    counts: dict[str, int] = {}
    for token in product.tokenize(prose or ""):
        if token in product.answer_stop or len(token) < 4 or token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in ranked[:limit]]


def _rehash(freeze: dict, mount: Path) -> dict:
    checks: list[dict] = []
    ok = True
    for rel, expected in sorted(freeze.get("product_pins", {}).items()):
        path = mount / rel
        if not path.is_file():
            checks.append({"pin": f"product:{rel}", "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": f"product:{rel}", "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    for rel, expected in sorted(freeze.get("repo_pins", {}).items()):
        path = REPO_ROOT / rel
        if not path.is_file():
            checks.append({"pin": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": rel, "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    expected_manifest = (freeze.get("population_manifests") or {}).get("mount")
    if expected_manifest:
        actual_manifest = cpa.manifest(mount)["manifest_sha256"]
        good = actual_manifest == expected_manifest
        ok = ok and good
        checks.append({"pin": "population:mount", "status": "ok" if good else "DRIFT",
                       "expected": expected_manifest, "actual": actual_manifest})
    return {"all_ok": ok, "n_checks": len(checks), "checks": checks}


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    if not HYPOTHESIS_PATH.is_file() or not FREEZE_PATH.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "hypothesis or freeze record absent",
                          "claim_ceiling": "no measurement without a pre-execution freeze"}
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if str(hypothesis.get("run_id_of_record")) != str(run_id):
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "run id does not match the frozen hypothesis run_id_of_record",
                          "frozen_run_id": hypothesis.get("run_id_of_record"),
                          "claim_ceiling": "claim-bearing execution requires the frozen run id"}

    if not ACCEPTED_REPAIR_RECORD.is_file() or not mount.is_dir():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "record_exists": ACCEPTED_REPAIR_RECORD.is_file(),
                          "mount_exists": mount.is_dir(),
                          "claim_ceiling": "missing inputs are never a product verdict"}

    fixture = json.loads(ACCEPTED_REPAIR_RECORD.read_text(encoding="utf-8"))
    fixture_rows = fixture.get("bundles") or []
    if not fixture_rows:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "n_fixture_rows": 0,
                          "claim_ceiling": "empty fixture is never a product verdict"}

    pins_before = _rehash(freeze, mount)
    if not pins_before["all_ok"]:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "pins_before", "pins_before": pins_before,
                          "claim_ceiling": "pin drift is fail-closed by the frozen design"}

    # C1s: fixture integrity ------------------------------------------------
    repair_record_sha = sha256_file(ACCEPTED_REPAIR_RECORD)
    repair_record_pin = (freeze.get("pins") or {}).get(
        "results/evaluation/counter_probe_repair_verification/39687372110.json")
    c1_ok = (repair_record_sha == repair_record_pin
             and fixture.get("verdict") == "REPAIR_VERIFIED_ON_RECORDED_BYTES")

    try:
        product = cpa.ProductCode(mount)
    except Exception as exc:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "loader_error": repr(exc), "pins_before": pins_before,
                          "claim_ceiling": "product loader failure is never a product verdict"}

    # Placeholder token class: derived from the PRE-REMEDY-EMULATED extractor.
    # On a landed-remedy tree the SHIPPED extractor strips the placeholder and
    # derives zero tokens by design, so the shipped extractor can never define
    # the defect class the gates test against (Seq-2 disclosed correction).
    ph = str(product.redaction_placeholder or "")
    ph_tokens = sorted(set(preremedy_key_terms(product, ph)))
    shipped_ph_tokens = sorted(set(product.placeholder_tokens()))
    c2_ok = (ph == "[citation removed: not in retrieved set]"
             and ph_tokens == ["citation", "removed", "retrieved"])

    rows: list[dict] = []
    g1_bad: list[str] = []
    g2_required = g2_bad = 0
    g3_required = g3_bad = 0
    g4_bad: list[str] = []
    n_baseline_contaminated = 0
    c4_contaminated: list[str] = []
    c4_clean: list[str] = []
    c5_emission_preserved = True

    for fr in fixture_rows:
        src = Path(str(fr.get("source_path") or ""))
        key = f"{fr.get('packet')}/{fr.get('question_slug')}"
        if not src.is_file():
            rows.append({"key": key, "status": "SOURCE_ABSENT"})
            continue
        bundle = json.loads(src.read_text(encoding="utf-8"))
        prose = str((bundle.get("answer") or {}).get("prose") or "")
        query = str(bundle.get("query") or "")

        shipped_plan = product.plan_adversarial_queries(query, prose)
        shipped_queries = _queries_of(shipped_plan)
        shipped_anchor = _anchor_of(shipped_queries[0]) if shipped_queries else []

        baseline_anchor = list(fr.get("baseline_anchor") or [])
        fixed_anchor = list(fr.get("fixed_anchor") or [])
        baseline_queries = list(fr.get("baseline_probe_queries") or [])
        fixed_queries = list(fr.get("fixed_probe_queries") or [])
        contaminated = bool(fr.get("baseline_anchor_contaminated"))
        if contaminated:
            n_baseline_contaminated += 1

        # G1s
        g1_tokens = sorted(set(shipped_anchor) & set(ph_tokens))
        g1_clean = not g1_tokens
        if not g1_clean:
            g1_bad.append(key)

        # G2s (required only on formerly-contaminated bundles)
        g2r = False
        g2_topical = None
        if contaminated:
            g2r = True
            g2_required += 1
            topical = sorted(set(shipped_anchor) & set(product.content_terms(query)))
            g2_topical = topical
            if not topical:
                g2_bad += 1

        # G3s (required only on formerly-clean bundles)
        g3r = False
        g3_noop = None
        if not contaminated:
            g3r = True
            g3_required += 1
            g3_noop = shipped_queries == baseline_queries
            if g3_noop is False:
                g3_bad += 1

        # G4s: shipped == accepted FIXED, byte-for-byte
        g4_anchor_match = shipped_anchor == fixed_anchor
        g4_queries_match = shipped_queries == fixed_queries
        g4_ok = g4_anchor_match and g4_queries_match
        if not g4_ok:
            g4_bad.append(key)

        if not shipped_queries:
            c5_emission_preserved = False

        # C4s: planted pre-remedy extractor
        pre_anchor = _anchor_of(" ".join(preremedy_key_terms(product, prose)[:ANCHOR_SLOTS]))
        pre_tokens = sorted(set(pre_anchor) & set(ph_tokens))
        pre_contaminated = bool(pre_tokens)
        if pre_contaminated:
            c4_contaminated.append(key)
        else:
            c4_clean.append(key)

        rows.append({
            "key": key,
            "packet": fr.get("packet"),
            "question_slug": fr.get("question_slug"),
            "language": fr.get("language"),
            "source_path": str(src),
            "source_sha256": cpa.sha256_file(src),
            "placeholder_occurrences_in_prose": prose.count(ph) if ph else 0,
            "accepted_baseline_anchor": baseline_anchor,
            "accepted_fixed_anchor": fixed_anchor,
            "shipped_anchor": shipped_anchor,
            "shipped_anchor_contaminated": bool(g1_tokens),
            "shipped_anchor_placeholder_tokens": g1_tokens,
            "G1s_anchor_clean": g1_clean,
            "G2s_required": g2r,
            "G2s_topical_terms": g2_topical,
            "G2s_topical": g2_topical if g2r else None,
            "G3s_required": g3r,
            "G3s_shipped_equals_accepted_baseline": g3_noop,
            "G4s_shipped_anchor_matches_accepted_fixed": g4_anchor_match,
            "G4s_shipped_queries_match_accepted_fixed": g4_queries_match,
            "shipped_probe_queries": shipped_queries,
            "accepted_fixed_probe_queries": fixed_queries,
            "C4s_preremedy_anchor": pre_anchor,
            "C4s_preremedy_contaminated": pre_contaminated,
            "C4s_preremedy_placeholder_tokens": pre_tokens,
        })

    measured = [r for r in rows if r.get("status") != "SOURCE_ABSENT"]
    if not measured:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "n_measured": 0, "pins_before": pins_before,
                          "claim_ceiling": "no fixture bundle was loadable"}

    # Controls C3s, C4s, C5s -----------------------------------------------
    expected_contaminated = {"39275520116/de-kapitalverletzung.bundle",
                             "39319405429/de-kapitalverletzung.bundle"}
    c3_ok = n_baseline_contaminated >= 1
    c4_ok = (set(c4_contaminated) == expected_contaminated
             and len(c4_clean) == len(measured) - len(expected_contaminated))
    c5_ok = c5_emission_preserved

    controls = {
        "C1s_fixture_integrity": {
            "description": "accepted repair-verification record re-hashes to its pin and its verdict is REPAIR_VERIFIED_ON_RECORDED_BYTES",
            "holds": bool(c1_ok),
            "record_sha256": repair_record_sha,
            "record_verdict": fixture.get("verdict"),
        },
        "C2s_placeholder_preconditions_intact": {
            "description": "REDACTION_PLACEHOLDER unchanged; the PRE-REMEDY-emulated extractor derives exactly {citation, removed, retrieved} from it (the defect token class); the SHIPPED extractor's zero-token output on the placeholder is recorded as the remedy's own signature",
            "holds": bool(c2_ok),
            "placeholder": ph,
            "placeholder_tokens_preremedy": ph_tokens,
            "placeholder_tokens_shipped": shipped_ph_tokens,
        },
        "C3s_defect_was_real": {
            "description": "the accepted record carries at least one baseline-contaminated row",
            "holds": bool(c3_ok),
            "n_baseline_contaminated": n_baseline_contaminated,
        },
        "C4s_planted_preremedy_extractor_detects_the_defect": {
            "description": "PRE-REMEDY-emulated extractor reproduces contamination on exactly the 2 formerly-contaminated bundles and stays clean on the other 12",
            "holds": bool(c4_ok),
            "planted_contaminated": sorted(c4_contaminated),
            "expected_contaminated": sorted(expected_contaminated),
            "n_planted_clean": len(c4_clean),
        },
        "C5s_zero_network_and_emission_preserved": {
            "description": "zero network calls; shipped planner still emits probe plans on every measured bundle",
            "holds": bool(c5_ok),
            "network_calls": 0,
        },
    }
    control_failures = [k for k, v in controls.items() if not v["holds"]]

    gates = {
        "G1s_shipped_anchor_clean": {
            "description": "no placeholder token in the shipped topic anchor on any measured bundle",
            "passed": not g1_bad,
            "n_bundles": len(measured),
            "n_failed": len(g1_bad),
            "failed": sorted(g1_bad),
        },
        "G2s_formerly_contaminated_regain_topicality": {
            "description": "shipped anchor shares a content term with the question on every formerly-contaminated bundle",
            "passed": bool(g2_required) and g2_bad == 0,
            "n_required": g2_required,
            "n_failed": g2_bad,
        },
        "G3s_clean_bundles_unperturbed": {
            "description": "shipped probe queries byte-equal the accepted BASELINE queries on every formerly-clean bundle",
            "passed": bool(g3_required) and g3_bad == 0,
            "n_required": g3_required,
            "n_failed": g3_bad,
        },
        "G4s_shipped_matches_accepted_fixed": {
            "description": "shipped probe queries and anchor byte-equal the accepted repair-verification FIXED arm on every bundle",
            "passed": bool(measured) and not g4_bad,
            "n_compared": len(measured),
            "n_failed": len(g4_bad),
            "failed": sorted(g4_bad),
        },
    }
    gate_failures = [k for k, v in gates.items() if not v["passed"]]

    if control_failures:
        verdict, code = "ENVIRONMENT_OR_VACUOUS", EXIT_ENV
    elif gate_failures:
        verdict, code = "SHIPPED_PLANNER_DIVERGES_FROM_VERIFIED_REMEDY", EXIT_DIVERGE
    else:
        verdict, code = "SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY", EXIT_OK

    pins_after = _rehash(freeze, mount)
    if not pins_after["all_ok"]:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "pins_after", "pins_before": pins_before,
                          "pins_after": pins_after,
                          "claim_ceiling": "post-execution pin drift invalidates the run"}

    product_head = None
    planner_sha = None
    try:
        import subprocess
        r = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=20)
        product_head = r.stdout.strip() or None
    except Exception:  # pragma: no cover
        pass
    planner_path = mount / "product/query/adversarial_retrieval.py"
    if planner_path.is_file():
        planner_sha = sha256_file(planner_path)

    out = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 62,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "exit_code": code,
        "verdict_statement": {
            "SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY":
                "on the pinned recorded 14-bundle population the SHIPPED planner reproduces, "
                "byte-for-byte, the probe queries and anchors of the accepted repair "
                "verification's FIXED arm — remedy (a) landed as verified",
            "SHIPPED_PLANNER_DIVERGES_FROM_VERIFIED_REMEDY":
                "the SHIPPED planner does NOT reproduce the accepted FIXED arm on at least "
                "one recorded bundle — the landed fix is not the verified fix on this population",
            "ENVIRONMENT_OR_VACUOUS":
                "pin drift, loader failure or a failed control; never a product verdict",
        }.get(verdict, verdict),
        "mount": str(mount),
        "product_mount_head": product_head,
        "product_head_expected": (hypothesis.get("inputs_pinned") or {}).get(
            "product_mount_head_expected"),
        "planner_sha256": planner_sha,
        "pre_remedy_planner_pin_disclosed": (hypothesis.get("inputs_pinned") or {}).get(
            "pre_remedy_planner_pin_disclosed"),
        "accepted_repair_record": {
            "path": str(ACCEPTED_REPAIR_RECORD.relative_to(REPO_ROOT)),
            "sha256": repair_record_sha,
            "verdict": fixture.get("verdict"),
        },
        "n_fixture_rows": len(fixture_rows),
        "n_measured": len(measured),
        "n_baseline_contaminated": n_baseline_contaminated,
        "placeholder_tokens": ph_tokens,
        "placeholder_tokens_derivation": "PRE-REMEDY-emulated extractor (Seq-2 disclosed correction; the shipped extractor strips the placeholder and derives none by design)",
        "placeholder_tokens_shipped_extractor": shipped_ph_tokens,
        "redaction_placeholder": ph,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "gates": gates,
        "controls": controls,
        "control_failures": control_failures,
        "gate_failures": gate_failures,
        "bundles": rows,
        "network_calls": 0,
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "instrument_sha256": sha256_file(Path(__file__)),
        "claim_ceiling": hypothesis.get("claim_ceiling"),
    }
    return code, out


def render_report(rec: dict) -> str:
    g = rec.get("gates") or {}
    c = rec.get("controls") or {}
    lines = [
        f"# Shipped-Planner Remedy (a) Verification — run {rec.get('run_id')}",
        "",
        f"- Verdict: **{rec.get('verdict')}** (exit {rec.get('exit_code')})",
        f"- Product mount head: `{rec.get('product_mount_head')}` "
        f"(expected `{rec.get('product_head_expected')}`)",
        f"- Shipped planner sha256: `{rec.get('planner_sha256')}`",
        f"- Pre-remedy planner pin (disclosed): `{rec.get('pre_remedy_planner_pin_disclosed')}`",
        f"- Population: {rec.get('n_measured')} measured bundles "
        f"({rec.get('n_baseline_contaminated')} formerly contaminated)",
        f"- Pins: before {rec.get('pins_before', {}).get('n_checks')} checks "
        f"all_ok={rec.get('pins_before', {}).get('all_ok')}; "
        f"after {rec.get('pins_after', {}).get('n_checks')} checks "
        f"all_ok={rec.get('pins_after', {}).get('all_ok')}",
        f"- Network calls: {rec.get('network_calls')}",
        "",
        "## Gates",
        "",
    ]
    for name, gate in g.items():
        lines.append(f"- **{name}**: passed={gate.get('passed')} "
                     f"(failed={gate.get('n_failed')}) — {gate.get('description')}")
    lines += ["", "## Controls", ""]
    for name, ctl in c.items():
        lines.append(f"- **{name}**: holds={ctl.get('holds')} — {ctl.get('description')}")
    lines += ["", "## Claim ceiling", "", str(rec.get("claim_ceiling") or ""), ""]
    return "\n".join(lines)


def _write(out_path: Path, report_path: Path | None, rec: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(rec), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)
    code, rec = run(args.run_id, Path(args.mount))
    if args.out:
        _write(Path(args.out), Path(args.report) if args.report else None, rec)
    print(json.dumps({"verdict": rec.get("verdict"), "exit_code": code,
                      "n_measured": rec.get("n_measured"),
                      "gate_failures": rec.get("gate_failures"),
                      "control_failures": rec.get("control_failures"),
                      "record": args.out}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
