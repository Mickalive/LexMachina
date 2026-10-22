#!/usr/bin/env python3
"""Degradation-disclosure cross-check on the recorded writer-abort slice.

Why this exists
---------------
Product cycle 39667945530 recorded a served slice whose generative writer
failed.  The answer was served through the extractive fallback with
``answer.status = "degraded"`` but with **no** machine-readable degradation
record: a downstream reader could only parse a free-text provider error, and an
empty counter set could be rendered as "no contrary authority exists".  The
product audit of cycle 39815102517 ordered item 3: publish the abort as a
first-class field and make the adversarial pass inherit it.

This instrument is the evaluation lane's smallest executable cross-check of
that disclosure.  It executes the *shipped* code at the accepted product mount
on the two recorded bundles and asks four frozen questions:

G1 the extractive fallback stamps ``answer.degradation`` (code, stage,
   disclosure) and mirrors it under ``provenance.generative_audit``;
G2 the independent adversarial pass inherits the abort and marks itself
   DEGRADED, with a measurement-gap disclosure;
G3 an answer with no usable legal vocabulary takes the VACUOUS branch rather
   than claiming a measured empty result;
G4 the recorded healthy slice stays MEASURED and non-degraded (no blanket
   false positive).

Exit codes: 0 = DEGRADATION_DISCLOSURE_VISIBLE, 1 = DEGRADATION_DISCLOSURE_GAP,
2 = ENVIRONMENT_OR_VACUOUS (never a product verdict).

Claim ceiling: disclosure only.  No retrieval quality, no counter-authority
recall, no label/geometry bar, no serve recommendation.  Zero network.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-degradation-disclosure-crosscheck/1"
FREEZE_PATH = REPO_ROOT / "evaluation" / "DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V1.json"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V1.json"

RUN_ID = "39820650174"
DIRECTION_VERSION = 62
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
WRITER_ABORT_CODE = "e_EMISSION_WRITER_ABORT"

DEGRADED_BUNDLE = "results/product/live_slice/CYCLE_39667945530_bundle.json"
HEALTHY_BUNDLE = "results/product/live_slice/CYCLE_39667945530_FIX1_bundle.json"
PRODUCT_PINS = {
    "product/query/pipeline.py":
        "f59bba1fe41433d74f3fc5e962c20d3b957959caf27df501173e2a144029c078",
    "product/query/adversarial_retrieval.py":
        "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9",
    "product/query/answer.py":
        "acbc161436429e95c4bff04234e69be2e7a1e7333837e589753bbaae727f5f08",
    "product/answer_reliability.py":
        "46e195dea1c034a6d736fcddf7bcec71a5c2210aa2ada76e234d19085c1ffffb",
}
BUNDLE_PINS = {
    DEGRADED_BUNDLE:
        "d58eea71818ec8515e47a3e115fca4c9446f311baa740b3f267097b841bdbf2d",
    HEALTHY_BUNDLE:
        "f8123012f1b9d61314cd06bb1563260ca9393aee4f06fdadc717566a81edd1b0",
}

EXIT_OK = 0
EXIT_GAP = 1
EXIT_ENV = 2


# --------------------------------------------------------------------------- #
# helpers (pure where possible; importable without the product mount)
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _check(checks: list[dict], name: str, ok: bool, observed=None, expected=None) -> None:
    checks.append({"check": name, "ok": bool(ok), "observed": observed, "expected": expected})


def _text(value) -> str:
    return str(value or "")


def _decisions_n(bundle: dict) -> int:
    return len(bundle.get("decisions") or [])


def _pin_map(root: Path, pins: dict[str, str]) -> dict:
    checks = []
    ok = True
    for rel, expected in sorted(pins.items()):
        p = root / rel
        if not p.is_file():
            checks.append({"path": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(p)
        good = actual == expected
        ok = ok and good
        checks.append({"path": rel, "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    return {"all_hold": ok, "checks": checks}


def _visibility(product_reliability, bundle: dict) -> dict:
    try:
        return product_reliability.degradation_visibility(bundle)
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- #
# frozen predicates
# --------------------------------------------------------------------------- #


def predicate_g1(fallback: dict, source: dict, provider_error: str,
                 visibility: dict) -> dict:
    checks: list[dict] = []
    a = fallback.get("answer") or {}
    deg = a.get("degradation") or {}
    ga = (fallback.get("provenance") or {}).get("generative_audit") or {}
    ga_deg = ga.get("degradation") or {}
    disclosure = _text(deg.get("disclosure")).lower()
    _check(checks, "answer_status_degraded", a.get("status") == "degraded",
           a.get("status"), "degraded")
    _check(checks, "degradation_code", deg.get("code") == WRITER_ABORT_CODE,
           deg.get("code"), WRITER_ABORT_CODE)
    _check(checks, "degradation_stage", deg.get("stage") == "generative_writer",
           deg.get("stage"), "generative_writer")
    _check(checks, "disclosure_says_not_measured",
           "not measured" in disclosure, deg.get("disclosure"), "contains 'not measured'")
    _check(checks, "disclosure_says_contrary_authority",
           "contrary authority" in disclosure, deg.get("disclosure"),
           "contains 'contrary authority'")
    _check(checks, "generative_audit_mirrors_code",
           ga_deg.get("code") == WRITER_ABORT_CODE, ga_deg.get("code"), WRITER_ABORT_CODE)
    _check(checks, "generative_audit_emission_status",
           ga.get("emission_status") == "WRITER_ABORT",
           ga.get("emission_status"), "WRITER_ABORT")
    _check(checks, "generative_audit_degraded_true", ga.get("degraded") is True,
           ga.get("degraded"), True)
    _check(checks, "provider_error_preserved", ga.get("provider_error") == provider_error,
           ga.get("provider_error"), provider_error)
    _check(checks, "decisions_preserved", _decisions_n(fallback) == _decisions_n(source),
           _decisions_n(fallback), _decisions_n(source))
    _check(checks, "product_visibility_degraded", visibility.get("degraded") is True,
           visibility.get("degraded"), True)
    _check(checks, "product_visibility_visible", visibility.get("visible") is True,
           visibility.get("visible"), True)
    _check(checks, "product_visibility_code",
           visibility.get("degradation_code") == WRITER_ABORT_CODE,
           visibility.get("degradation_code"), WRITER_ABORT_CODE)
    return {"gate": "G1_abort_is_a_first_class_answer_field",
            "passed": all(c["ok"] for c in checks), "checks": checks}


def predicate_g2(pass_bundle: dict, fallback: dict, visibility: dict) -> dict:
    checks: list[dict] = []
    adv = ((pass_bundle.get("provenance") or {}).get("adversarial_retrieval") or {})
    status = _text(adv.get("adversarial_status"))
    disclosure = _text(adv.get("disclosure")).lower()
    _check(checks, "adversarial_degraded_true", adv.get("degraded") is True,
           adv.get("degraded"), True)
    _check(checks, "adversarial_degradation_code",
           adv.get("degradation_code") == WRITER_ABORT_CODE,
           adv.get("degradation_code"), WRITER_ABORT_CODE)
    _check(checks, "adversarial_status_names_writer_abort",
           "WRITER_ABORT" in status, status, "contains 'WRITER_ABORT'")
    _check(checks, "adversarial_disclosure_names_measurement_gap",
           ("measurement gap" in disclosure
            or "not evidence that no contrary authority" in disclosure),
           adv.get("disclosure"), "measurement-gap disclosure")
    _check(checks, "decisions_preserved",
           _decisions_n(pass_bundle) == _decisions_n(fallback),
           _decisions_n(pass_bundle), _decisions_n(fallback))
    _check(checks, "answer_degradation_preserved",
           ((pass_bundle.get("answer") or {}).get("degradation") or {}).get("code")
           == WRITER_ABORT_CODE,
           ((pass_bundle.get("answer") or {}).get("degradation") or {}).get("code"),
           WRITER_ABORT_CODE)
    _check(checks, "product_visibility_visible", visibility.get("visible") is True,
           visibility.get("visible"), True)
    _check(checks, "network_calls_zero", int(adv.get("network_calls") or 0) == 0,
           adv.get("network_calls"), 0)
    return {"gate": "G2_adversarial_pass_inherits_the_abort",
            "passed": all(c["ok"] for c in checks), "checks": checks}


def predicate_g3(pass_bundle: dict, fallback: dict) -> dict:
    checks: list[dict] = []
    adv = ((pass_bundle.get("provenance") or {}).get("adversarial_retrieval") or {})
    status = _text(adv.get("adversarial_status"))
    _check(checks, "vacuous_skipped", adv.get("skipped") is True,
           adv.get("skipped"), True)
    _check(checks, "vacuous_skip_reason",
           "vacuous_pass" in _text(adv.get("skip_reason")),
           adv.get("skip_reason"), "contains 'vacuous_pass'")
    _check(checks, "vacuous_status", status == "VACUOUS_WRITER_ABORT",
           status, "VACUOUS_WRITER_ABORT")
    _check(checks, "vacuous_degraded_true", adv.get("degraded") is True,
           adv.get("degraded"), True)
    _check(checks, "vacuous_degradation_code",
           adv.get("degradation_code") == WRITER_ABORT_CODE,
           adv.get("degradation_code"), WRITER_ABORT_CODE)
    _check(checks, "vacuous_disclosure_present", bool(adv.get("disclosure")),
           adv.get("disclosure"), "non-empty")
    _check(checks, "decisions_preserved",
           _decisions_n(pass_bundle) == _decisions_n(fallback),
           _decisions_n(pass_bundle), _decisions_n(fallback))
    return {"gate": "G3_empty_prose_is_vacuous_not_measured",
            "passed": all(c["ok"] for c in checks), "checks": checks}


def predicate_g4(pass_bundle: dict, healthy_source: dict, visibility: dict) -> dict:
    checks: list[dict] = []
    adv = ((pass_bundle.get("provenance") or {}).get("adversarial_retrieval") or {})
    status = _text(adv.get("adversarial_status"))
    a = pass_bundle.get("answer") or {}
    _check(checks, "adversarial_degraded_false", adv.get("degraded") is False,
           adv.get("degraded"), False)
    _check(checks, "adversarial_degradation_code_null", not adv.get("degradation_code"),
           adv.get("degradation_code"), None)
    _check(checks, "adversarial_status_measured", status == "MEASURED",
           status, "MEASURED")
    _check(checks, "no_writer_abort_code", "WRITER_ABORT" not in status,
           status, "no 'WRITER_ABORT'")
    _check(checks, "answer_status_ready", a.get("status") == "ready",
           a.get("status"), "ready")
    _check(checks, "answer_degradation_absent", not a.get("degradation"),
           a.get("degradation"), None)
    _check(checks, "decisions_preserved",
           _decisions_n(pass_bundle) == _decisions_n(healthy_source),
           _decisions_n(pass_bundle), _decisions_n(healthy_source))
    _check(checks, "product_visibility_degraded_false",
           visibility.get("degraded") is False, visibility.get("degraded"), False)
    _check(checks, "product_visibility_visible", visibility.get("visible") is True,
           visibility.get("visible"), True)
    return {"gate": "G4_healthy_bundle_stays_non_degraded",
            "passed": all(c["ok"] for c in checks), "checks": checks}


# --------------------------------------------------------------------------- #
# network guard
# --------------------------------------------------------------------------- #


class NetworkGuard:
    def __init__(self):
        self.attempts = 0
        self._orig = None

    def __enter__(self):
        self._orig = socket.socket
        guard = self

        def _blocked(*_a, **_kw):
            guard.attempts += 1
            raise RuntimeError("NO_NETWORK_DEGRADATION_CROSSCHECK")

        socket.socket = _blocked  # type: ignore[assignment]
        return self

    def __exit__(self, *_exc):
        if self._orig is not None:
            socket.socket = self._orig  # type: ignore[assignment]
        return False


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    base = {"schema": SCHEMA, "run_id": run_id, "lane": "evaluation",
            "direction_version": DIRECTION_VERSION}
    if str(run_id) != RUN_ID:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "run id does not match the frozen run_id_of_record",
                          "expected_run_id": RUN_ID}
    if not FREEZE_PATH.is_file() or not HYPOTHESIS_PATH.is_file():
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "hypothesis or freeze record absent"}
    if not mount.is_dir():
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV, "reason": "accepted product mount absent",
                          "mount": str(mount)}

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pins_before = _pin_map(mount, PRODUCT_PINS)
    bundle_pins_before = _pin_map(mount, BUNDLE_PINS)
    if not pins_before["all_hold"] or not bundle_pins_before["all_hold"]:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "frozen product or bundle pin does not hold",
                          "pins_before": pins_before,
                          "bundle_pins_before": bundle_pins_before}

    degraded_source = json.loads((mount / DEGRADED_BUNDLE).read_text(encoding="utf-8"))
    healthy_source = json.loads((mount / HEALTHY_BUNDLE).read_text(encoding="utf-8"))
    degraded_copy = copy.deepcopy(degraded_source)
    healthy_copy = copy.deepcopy(healthy_source)
    provider_error = _text(
        ((degraded_source.get("provenance") or {}).get("generative_audit") or {})
        .get("provider_error")
    )
    pre_fix_state = {
        "recorded_answer_status": (degraded_source.get("answer") or {}).get("status"),
        "recorded_answer_degradation": (degraded_source.get("answer") or {}).get("degradation"),
        "recorded_generative_audit_has_emission_status":
            "emission_status" in (
                (degraded_source.get("provenance") or {}).get("generative_audit") or {}
            ),
        "recorded_generative_audit_has_degradation":
            "degradation" in (
                (degraded_source.get("provenance") or {}).get("generative_audit") or {}
            ),
        "interpretation": (
            "the recorded slice predates ordered item 3; the absence of the field is the "
            "defect the fix addresses and is NOT scored as a current failure"
        ),
    }

    # Import the shipped code lazily and without writing bytecode into the mount.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(mount))
    import importlib
    try:
        pipeline = importlib.import_module("product.query.pipeline")
        reliability = importlib.import_module("product.answer_reliability")
    except Exception as exc:
        return EXIT_ENV, {**base, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": f"shipped product import failed: {type(exc).__name__}: {exc}"}

    timings: dict[str, float] = {}
    guard = NetworkGuard()
    with guard:
        t0 = time.time()
        fallback = pipeline._extractive_degraded_fallback(
            degraded_source, provider_error, max_cites=4
        )
        timings["extractive_fallback_seconds"] = round(time.time() - t0, 4)

        vis_g1 = _visibility(reliability, fallback)

        t0 = time.time()
        degraded_pass = pipeline.adversarial_retrieval_pass(
            fallback, retrieval_mode="offline", max_new=0, hydrate_top=0
        )
        timings["degraded_adversarial_pass_seconds"] = round(time.time() - t0, 4)
        vis_g2 = _visibility(reliability, degraded_pass)

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
        vis_g4 = _visibility(reliability, healthy_pass)

    network_attempts = guard.attempts

    gates = {
        "G1_abort_is_a_first_class_answer_field":
            predicate_g1(fallback, degraded_source, provider_error, vis_g1),
        "G2_adversarial_pass_inherits_the_abort":
            predicate_g2(degraded_pass, fallback, vis_g2),
        "G3_empty_prose_is_vacuous_not_measured":
            predicate_g3(vacuous_pass, fallback),
        "G4_healthy_bundle_stays_non_degraded":
            predicate_g4(healthy_pass, healthy_source, vis_g4),
    }

    # ------------------------------------------------------------------ #
    # controls (in-memory mutations; no file is written)
    # ------------------------------------------------------------------ #
    controls: dict[str, dict] = {}

    c1 = copy.deepcopy(fallback)
    (c1.get("answer") or {}).pop("degradation", None)
    c1_gate = predicate_g1(c1, degraded_source, provider_error,
                           _visibility(reliability, c1))
    controls["C1_deleting_the_answer_field_fails_G1"] = {
        "holds": c1_gate["passed"] is False,
        "mutated_gate_passed": c1_gate["passed"],
    }

    c2 = copy.deepcopy(degraded_pass)
    c2_adv = (c2.get("provenance") or {}).get("adversarial_retrieval") or {}
    c2_adv["degraded"] = False
    c2_adv["degradation_code"] = None
    c2_adv["adversarial_status"] = "MEASURED"
    c2_gate = predicate_g2(c2, fallback, _visibility(reliability, c2))
    controls["C2_relabelling_the_pass_as_measured_fails_G2"] = {
        "holds": c2_gate["passed"] is False,
        "mutated_gate_passed": c2_gate["passed"],
    }

    c3 = copy.deepcopy(healthy_pass)
    c3_adv = (c3.get("provenance") or {}).get("adversarial_retrieval") or {}
    c3_adv["degraded"] = True
    c3_adv["degradation_code"] = WRITER_ABORT_CODE
    c3_adv["adversarial_status"] = "DEGRADED_WRITER_ABORT"
    c3_gate = predicate_g4(c3, healthy_source, _visibility(reliability, c3))
    controls["C3_injecting_an_abort_into_the_healthy_leg_fails_G4"] = {
        "holds": c3_gate["passed"] is False,
        "mutated_gate_passed": c3_gate["passed"],
    }

    # Prove the guard is armed: a direct socket construction must raise.
    guard_probe = NetworkGuard()
    guard_raised = False
    with guard_probe:
        try:
            socket.socket()
        except RuntimeError:
            guard_raised = True
    controls["C4_network_guard_is_armed_and_unused"] = {
        "holds": bool(guard_raised and network_attempts == 0),
        "guard_raised_when_probed": guard_raised,
        "unexpected_attempts_during_product_calls": network_attempts,
    }

    pins_after = _pin_map(mount, PRODUCT_PINS)
    bundle_pins_after = _pin_map(mount, BUNDLE_PINS)
    inputs_unchanged = (degraded_source == degraded_copy
                        and healthy_source == healthy_copy)
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

    gate_failures = [k for k, v in gates.items() if not v.get("passed")]
    control_failures = [k for k, v in controls.items() if not v.get("holds")]
    if control_failures:
        code, verdict = EXIT_ENV, "ENVIRONMENT_OR_VACUOUS"
    elif gate_failures:
        code, verdict = EXIT_GAP, "DEGRADATION_DISCLOSURE_GAP"
    else:
        code, verdict = EXIT_OK, "DEGRADATION_DISCLOSURE_VISIBLE"

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
        "mount": str(mount),
        "product_mount_head": _mount_head(mount),
        "product_pins_expected": PRODUCT_PINS,
        "bundle_pins_expected": BUNDLE_PINS,
        "product_pins_before": pins_before,
        "product_pins_after": pins_after,
        "bundle_pins_before": bundle_pins_before,
        "bundle_pins_after": bundle_pins_after,
        "recorded_artifact_pre_fix_state": pre_fix_state,
        "provider_error_measured": provider_error,
        "n_decisions_degraded": _decisions_n(degraded_source),
        "n_decisions_healthy": _decisions_n(healthy_source),
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


def _mount_head(mount: Path) -> str | None:
    import subprocess
    try:
        proc = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30)
        return (proc.stdout or "").strip() or None
    except Exception:
        return None


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
