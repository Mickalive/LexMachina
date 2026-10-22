#!/usr/bin/env python3
"""V2 of the degradation-disclosure cross-check: split the two stages.

V1 (``degradation_disclosure_crosscheck.py``) was frozen and executed first and
is preserved verbatim at
``results/evaluation/degradation_disclosure_crosscheck/39820650174.json`` with
verdict ``DEGRADATION_DISCLOSURE_GAP`` (exit 1).  Its only failing sub-check was
``product_visibility_visible`` on the *bare output of the extractive fallback*.
Source inspection shows that sub-check was stage-blind, not that the product is
silent:

* ``product/answer_reliability.py`` (visible predicate, lines 425-429) defines
  an aborted writer as visible only when ``answer.degradation.code`` is set AND
  the adversarial pass carries ``WRITER_ABORT`` / ``DEGRADED`` / ``VACUOUS``;
* ``product/query/pipeline.py`` builds the fallback at line 1256 and runs the
  adversarial pass afterwards at line 1288, so at the fallback stage there is
  no new ``adversarial_status`` yet.

V2 therefore gates the standalone stage on the answer field, the code, the
disclosure and the mirror (plus ``degradation_visibility().degraded`` and the
code), and gates ``visible=true`` on the complete-bundle stage (G2/G4).  It
changes no other gate, control, exit code or claim ceiling.  The V1 result is
pinned and checked by control C6, so the correction cannot erase it.

Exit: 0 = DEGRADATION_DISCLOSURE_VISIBLE_AT_COMPLETE_BUNDLE_STAGE,
1 = DEGRADATION_DISCLOSURE_GAP, 2 = ENVIRONMENT_OR_VACUOUS.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import degradation_disclosure_crosscheck as v1  # noqa: E402

SCHEMA = "lex-evaluation-degradation-disclosure-crosscheck/1"
FREEZE_PATH = REPO_ROOT / "evaluation" / "DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V2.json"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V2.json"
V1_RESULT = REPO_ROOT / "results" / "evaluation" / "degradation_disclosure_crosscheck" / "39820650174.json"
V1_RESULT_SHA = "4b9bc4324d1e0134207077b5a7ec3d5ecea7550d6bcc6dab11d7c7f7ab075817"
V1_RESULT_VERDICT = "DEGRADATION_DISCLOSURE_GAP"

RUN_ID = "39820650174"
DIRECTION_VERSION = 62
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")

EXIT_OK = 0
EXIT_GAP = 1
EXIT_ENV = 2

PRODUCT_PINS = v1.PRODUCT_PINS
BUNDLE_PINS = v1.BUNDLE_PINS


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def predicate_g1_v2(fallback: dict, source: dict, provider_error: str,
                    visibility: dict) -> dict:
    """V1's G1 without the premature complete-bundle visibility requirement."""
    base = v1.predicate_g1(fallback, source, provider_error, visibility)
    kept = [c for c in base["checks"] if c["check"] != "product_visibility_visible"]
    stage_observation = next(
        (c for c in base["checks"] if c["check"] == "product_visibility_visible"), None
    )
    return {
        "gate": "G1_abort_is_a_first_class_answer_field",
        "passed": all(c["ok"] for c in kept),
        "checks": kept,
        "stage_observation": {
            "check": "product_visibility_visible_at_standalone_fallback",
            "observed": (stage_observation or {}).get("observed"),
            "not_gated_because": (
                "the shipped pipeline runs the adversarial pass after the fallback; "
                "degradation_visibility.visible requires the pass to be marked"
            ),
        },
    }


def _controls(fallback: dict, degraded_pass: dict, healthy_pass: dict,
              degraded_source: dict, healthy_source: dict, provider_error: str,
              visibility_reliability, pins_before: dict, pins_after: dict,
              bundle_pins_before: dict, bundle_pins_after: dict,
              inputs_unchanged: bool, network_attempts: int) -> dict:
    controls: dict[str, dict] = {}

    c1 = copy.deepcopy(fallback)
    (c1.get("answer") or {}).pop("degradation", None)
    c1_gate = predicate_g1_v2(c1, degraded_source, provider_error,
                              v1._visibility(visibility_reliability, c1))
    controls["C1_deleting_the_answer_field_fails_G1"] = {
        "holds": c1_gate["passed"] is False,
        "mutated_gate_passed": c1_gate["passed"],
    }

    c2 = copy.deepcopy(degraded_pass)
    c2_adv = (c2.get("provenance") or {}).get("adversarial_retrieval") or {}
    c2_adv.update({"degraded": False, "degradation_code": None,
                   "adversarial_status": "MEASURED"})
    c2_gate = v1.predicate_g2(c2, fallback, v1._visibility(visibility_reliability, c2))
    controls["C2_relabelling_the_pass_as_measured_fails_G2"] = {
        "holds": c2_gate["passed"] is False,
        "mutated_gate_passed": c2_gate["passed"],
    }

    c3 = copy.deepcopy(healthy_pass)
    c3_adv = (c3.get("provenance") or {}).get("adversarial_retrieval") or {}
    c3_adv.update({"degraded": True,
                   "degradation_code": v1.WRITER_ABORT_CODE,
                   "adversarial_status": "DEGRADED_WRITER_ABORT"})
    c3_gate = v1.predicate_g4(c3, healthy_source,
                              v1._visibility(visibility_reliability, c3))
    controls["C3_injecting_an_abort_into_the_healthy_leg_fails_G4"] = {
        "holds": c3_gate["passed"] is False,
        "mutated_gate_passed": c3_gate["passed"],
    }

    guard_probe = v1.NetworkGuard()
    guard_raised = False
    with guard_probe:
        try:
            import socket
            socket.socket()
        except RuntimeError:
            guard_raised = True
    controls["C4_network_guard_is_armed_and_unused"] = {
        "holds": bool(guard_raised and network_attempts == 0),
        "guard_raised_when_probed": guard_raised,
        "unexpected_attempts_during_product_calls": network_attempts,
    }

    controls["C5_product_and_input_pins_hold_before_and_after"] = {
        "holds": bool(pins_before["all_hold"] and pins_after["all_hold"]
                      and bundle_pins_before["all_hold"] and bundle_pins_after["all_hold"]
                      and inputs_unchanged),
        "product_pins_before_hold": pins_before["all_hold"],
        "product_pins_after_hold": pins_after["all_hold"],
        "bundle_pins_before_hold": bundle_pins_before["all_hold"],
        "bundle_pins_after_hold": bundle_pins_after["all_hold"],
        "inputs_unchanged": inputs_unchanged,
    }

    v1_rec = None
    v1_err = None
    try:
        v1_rec = json.loads(V1_RESULT.read_text(encoding="utf-8"))
    except Exception as exc:
        v1_err = f"{type(exc).__name__}: {exc}"
    controls["C6_v1_result_is_preserved_verbatim"] = {
        "holds": bool(
            V1_RESULT.is_file()
            and sha256_file(V1_RESULT) == V1_RESULT_SHA
            and v1_rec is not None
            and v1_rec.get("verdict") == V1_RESULT_VERDICT
            and v1_rec.get("exit_code") == 1
        ),
        "v1_result_sha256": sha256_file(V1_RESULT) if V1_RESULT.is_file() else None,
        "v1_result_verdict": (v1_rec or {}).get("verdict"),
        "v1_result_exit_code": (v1_rec or {}).get("exit_code"),
        "error": v1_err,
    }
    return controls


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    base = {"schema": SCHEMA, "run_id": run_id, "lane": "evaluation",
            "direction_version": DIRECTION_VERSION, "instrument_version": "V2"}
    if str(run_id) != RUN_ID:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "run id does not match the frozen run_id_of_record",
                          "expected_run_id": RUN_ID}
    if not FREEZE_PATH.is_file() or not HYPOTHESIS_PATH.is_file():
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "V2 hypothesis or freeze record absent"}
    if not mount.is_dir():
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV, "reason": "accepted product mount absent",
                          "mount": str(mount)}

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pins_before = v1._pin_map(mount, PRODUCT_PINS)
    bundle_pins_before = v1._pin_map(mount, BUNDLE_PINS)
    if not pins_before["all_hold"] or not bundle_pins_before["all_hold"]:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "frozen product or bundle pin does not hold",
                          "product_pins_before": pins_before,
                          "bundle_pins_before": bundle_pins_before}

    degraded_source = json.loads((mount / v1.DEGRADED_BUNDLE).read_text(encoding="utf-8"))
    healthy_source = json.loads((mount / v1.HEALTHY_BUNDLE).read_text(encoding="utf-8"))
    degraded_copy = copy.deepcopy(degraded_source)
    healthy_copy = copy.deepcopy(healthy_source)
    provider_error = v1._text(
        ((degraded_source.get("provenance") or {}).get("generative_audit") or {})
        .get("provider_error")
    )

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(mount))
    try:
        pipeline = importlib.import_module("product.query.pipeline")
        reliability = importlib.import_module("product.answer_reliability")
    except Exception as exc:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": f"shipped product import failed: {type(exc).__name__}: {exc}"}

    timings: dict[str, float] = {}
    guard = v1.NetworkGuard()
    with guard:
        t0 = time.time()
        fallback = pipeline._extractive_degraded_fallback(
            degraded_source, provider_error, max_cites=4
        )
        timings["extractive_fallback_seconds"] = round(time.time() - t0, 4)
        vis_g1 = v1._visibility(reliability, fallback)

        t0 = time.time()
        degraded_pass = pipeline.adversarial_retrieval_pass(
            fallback, retrieval_mode="offline", max_new=0, hydrate_top=0
        )
        timings["degraded_adversarial_pass_seconds"] = round(time.time() - t0, 4)
        vis_g2 = v1._visibility(reliability, degraded_pass)

        empty_prose = copy.deepcopy(fallback)
        empty_prose.setdefault("answer", {})["prose"] = ""
        t0 = time.time()
        vacuous_pass = pipeline.adversarial_retrieval_pass(
            empty_prose, retrieval_mode="offline", max_new=0, hydrate_top=0
        )
        timings["vacuous_adversarial_pass_seconds"] = round(time.time() - t0, 4)

        t0 = time.time()
        healthy_pass = pipeline.adversarial_retrieval_pass(
            healthy_source, retrieval_mode="offline", max_new=0, hydrate_top=0
        )
        timings["healthy_adversarial_pass_seconds"] = round(time.time() - t0, 4)
        vis_g4 = v1._visibility(reliability, healthy_pass)

    network_attempts = guard.attempts

    gates = {
        "G1_abort_is_a_first_class_answer_field":
            predicate_g1_v2(fallback, degraded_source, provider_error, vis_g1),
        "G2_adversarial_pass_inherits_the_abort":
            v1.predicate_g2(degraded_pass, fallback, vis_g2),
        "G3_empty_prose_is_vacuous_not_measured":
            v1.predicate_g3(vacuous_pass, fallback),
        "G4_healthy_bundle_stays_non_degraded":
            v1.predicate_g4(healthy_pass, healthy_source, vis_g4),
    }

    inputs_unchanged = (degraded_source == degraded_copy
                        and healthy_source == healthy_copy)
    pins_after = v1._pin_map(mount, PRODUCT_PINS)
    bundle_pins_after = v1._pin_map(mount, BUNDLE_PINS)
    controls = _controls(fallback, degraded_pass, healthy_pass, degraded_source,
                         healthy_source, provider_error, reliability,
                         pins_before, pins_after, bundle_pins_before,
                         bundle_pins_after, inputs_unchanged, network_attempts)

    gate_failures = [k for k, v in gates.items() if not v.get("passed")]
    control_failures = [k for k, v in controls.items() if not v.get("holds")]
    if control_failures:
        code, verdict = EXIT_ENV, "ENVIRONMENT_OR_VACUOUS"
    elif gate_failures:
        code, verdict = EXIT_GAP, "DEGRADATION_DISCLOSURE_GAP"
    else:
        code, verdict = EXIT_OK, "DEGRADATION_DISCLOSURE_VISIBLE_AT_COMPLETE_BUNDLE_STAGE"

    env = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }
    for mod in ("numpy", "sklearn"):
        try:
            m = importlib.import_module(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = None

    return code, {
        **base,
        "generated_at_utc": started,
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "v1_result_path": str(V1_RESULT.relative_to(REPO_ROOT)),
        "v1_result_sha256": sha256_file(V1_RESULT) if V1_RESULT.is_file() else None,
        "v1_result_verdict": V1_RESULT_VERDICT,
        "mount": str(mount),
        "product_mount_head": v1._mount_head(mount),
        "product_pins_expected": PRODUCT_PINS,
        "bundle_pins_expected": BUNDLE_PINS,
        "product_pins_before": pins_before,
        "product_pins_after": pins_after,
        "bundle_pins_before": bundle_pins_before,
        "bundle_pins_after": bundle_pins_after,
        "provider_error_measured": provider_error,
        "n_decisions_degraded": v1._decisions_n(degraded_source),
        "n_decisions_healthy": v1._decisions_n(healthy_source),
        "gates": gates,
        "controls": controls,
        "gate_failures": gate_failures,
        "control_failures": control_failures,
        "timings_seconds": timings,
        "environment": env,
        "network_calls": 0,
        "network_attempts": network_attempts,
        "verdict": verdict,
        "exit_code": code,
        "claim_ceiling": hypothesis["claim_ceiling"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    code, rec = run(args.run_id, Path(args.mount))
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "gate_failures": rec.get("gate_failures"),
        "control_failures": rec.get("control_failures"),
        "record": args.out,
    }, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
