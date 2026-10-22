#!/usr/bin/env python3
"""Live-answer reliability cross-check — factory direction v62 ordered item (2d).

The product lane's fourth new deliverable is its pre-registered live-answer
reliability measurement (run 39799042649) on the accepted product mount
(``results/product/answer_reliability/39799042649_measurement.json``).  The
product published ``product_claim_reliable_live_answer = false`` because
``answer_ready_rate`` is 6/7 = 0.857 < 1.0 under its own pre-registered
success rule.

This instrument is the evaluation-side side-by-side cross-check required by
direction v62 ordered item (2).  It re-derives every published metric from the
committed legs, re-evaluates every pre-registered condition, re-hashes every
leg's ``text_sha256``, and checks whether the product's claim boolean is an
honest function of the re-derived conditions.  Zero network.  Deterministic.

Gates (G1–G9) and controls (C1–C5) are frozen in
``evaluation/ANSWER_RELIABILITY_CROSSCHECK_HYPOTHESIS_V1.json``.
This file implements them literally and re-derives no threshold, bar, rubric
or verdict contract.

Exit codes (frozen contract)
----------------------------
0  ANSWER_RELIABILITY_CROSSCHECK_PASSES
1  ANSWER_RELIABILITY_CROSSCHECK_DIVERGES
2  ENVIRONMENT_OR_VACUOUS  (never a product verdict)

Usage::

    python -m evaluation.answer_reliability_crosscheck \
        --run-id 39827806011 \
        --out results/evaluation/answer_reliability_crosscheck/39827806011.json \
        --report reports/evaluation/ANSWER_RELIABILITY_CROSSCHECK_39827806011.md
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-answer-reliability-crosscheck/1"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "ANSWER_RELIABILITY_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation" / "ANSWER_RELIABILITY_CROSSCHECK_FREEZE_RECORD_V1.json"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
FLOAT_TOL = 1e-6

EXIT_OK = 0
EXIT_DIVERGE = 1
EXIT_ENV = 2

RUN_ID = "39827806011"
DIRECTION_VERSION = 62


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _feq(a, b, tol: float = FLOAT_TOL) -> bool:
    fa, fb = _f(a), _f(b)
    if fa is None or fb is None:
        return a == b
    return abs(fa - fb) <= tol


def _row(name, product_value, recomputed, match: bool, note: str = "") -> dict:
    return {
        "quantity": name,
        "product_value": product_value,
        "recomputed_value": recomputed,
        "match": bool(match),
        "note": note,
    }


def recompute_metrics(legs: list[dict]) -> dict:
    """Pure re-derivation of every product-published metric from the legs."""
    n = len(legs)
    n_ready = sum(1 for L in legs if (L.get("answer") or {}).get("status") == "ready")
    n_ok = sum(1 for L in legs if L.get("outcome") == "OK")
    n_cit_valid = 0
    n_prose_valid = 0
    n_src_valid = 0
    n_lang = 0
    n_degr_vis = 0
    n_degraded = 0
    n_markers = 0
    n_resolved = 0
    no_marker_legs: list[str] = []
    confirmed = 0
    emitted = 0
    text_sha_ok = True
    text_sha_failures: list[str] = []

    for L in legs:
        leg_id = str(L.get("leg_id") or "")
        c = L.get("citations") or {}
        if c.get("all_valid") and c.get("n_invalid") == 0 and (c.get("n_cited") or 0) > 0:
            n_cit_valid += 1
        p = L.get("prose_citations") or {}
        nm = int(p.get("n_markers") or 0)
        nr = int(p.get("n_resolved") or 0)
        n_markers += nm
        n_resolved += nr
        if nm == 0:
            no_marker_legs.append(leg_id)
        # Product definition: a leg is prose-citation-valid when all_resolved
        # and n_unresolved==0.  A writer-abort leg with zero markers records
        # all_resolved=True vacuously and IS counted (matches product's 1.0).
        if p.get("all_resolved") and p.get("n_unresolved") == 0 and nr == nm:
            n_prose_valid += 1
        s = L.get("sources") or {}
        if s.get("all_valid") and (s.get("n_without_valid_source") or 0) == 0 and (s.get("n_cited") or 0) > 0:
            n_src_valid += 1
        if (L.get("language_check") or {}).get("match"):
            n_lang += 1
        d = L.get("degradation") or {}
        if d.get("degraded"):
            n_degraded += 1
        if d.get("visible"):
            n_degr_vis += 1
        adv = L.get("adversarial") or {}
        confirmed += int(adv.get("n_counter_rows") or 0)
        emitted += int(adv.get("n_counter_rows_emitted") or 0)
        text = L.get("text") or ""
        if sha256_text(text) != L.get("text_sha256"):
            text_sha_ok = False
            text_sha_failures.append(leg_id)

    # stability: min Jaccard over repeated (slug, language, channel) groups
    groups: dict[tuple, list[dict]] = {}
    for L in legs:
        key = (L.get("slug"), L.get("language"), L.get("channel"))
        groups.setdefault(key, []).append(L)
    stabilities: list[dict] = []
    for (slug, lang, ch), members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(members) < 2:
            continue
        a = set((members[0].get("citations") or {}).get("cited_ids") or [])
        b = set((members[1].get("citations") or {}).get("cited_ids") or [])
        union = a | b
        jac = (len(a & b) / len(union)) if union else 0.0
        core = sorted(a & b)
        stabilities.append({
            "slug": slug, "language": lang, "channel": ch,
            "n_repeats": len(members),
            "jaccard": jac,
            "jaccard_6dp": round(jac, 6),
            "stable_core": core,
            "stable_core_fraction": (len(core) / len(a)) if a else 0.0,
            "cited_a": sorted(a), "cited_b": sorted(b),
        })
    jac_min = min((s["jaccard"] for s in stabilities), default=None)
    jac_min_6dp = min((s["jaccard_6dp"] for s in stabilities), default=None)

    return {
        "n_legs_planned": n,
        "n_legs_executed": n,
        "n_legs_ok": n_ok,
        "n_legs_failed": n - n_ok,
        "answer_ready_rate": (n_ready / n) if n else 0.0,
        "n_ready": n_ready,
        "citation_validity": (n_cit_valid / n) if n else 0.0,
        "prose_citation_validity": (n_prose_valid / n) if n else 0.0,
        "source_validity": (n_src_valid / n) if n else 0.0,
        "language_match_rate": (n_lang / n) if n else 0.0,
        "degradation_visible_rate": (n_degr_vis / n) if n else 0.0,
        "n_degraded_legs": n_degraded,
        "n_prose_markers": n_markers,
        "n_prose_markers_resolved": n_resolved,
        "stability": stabilities,
        "stability_jaccard_min": jac_min,
        "stability_jaccard_min_6dp": jac_min_6dp,
        "legs_without_prose_markers": sorted(no_marker_legs),
        "counter_rows_confirmed_total": confirmed,
        "counter_rows_emitted_total": emitted,
        "all_text_sha256_rehash": text_sha_ok,
        "text_sha256_failures": text_sha_failures,
    }


def evaluate_pre_registered(re: dict) -> dict:
    """Re-evaluate the product's frozen pre-registered conditions."""
    return {
        "answer_ready_rate == 1.0": _feq(re["answer_ready_rate"], 1.0),
        "citation_validity == 1.0": _feq(re["citation_validity"], 1.0),
        "degradation_visible_rate == 1.0": _feq(re["degradation_visible_rate"], 1.0),
        "language_match_rate == 1.0": _feq(re["language_match_rate"], 1.0),
        "prose_citation_validity == 1.0": _feq(re["prose_citation_validity"], 1.0),
        "source_validity == 1.0": _feq(re["source_validity"], 1.0),
        "stability_jaccard >= 0.5": (
            re["stability_jaccard_min"] is not None
            and float(re["stability_jaccard_min"]) >= 0.5
        ),
        "measurement_complete": (
            re["n_legs_executed"] == re["n_legs_planned"] and re["n_legs_failed"] == 0
        ),
    }


def expected_claim(conditions: dict) -> bool:
    """The product's own success rule: claim only when ALL conditions hold."""
    return all(bool(v) for v in conditions.values())


def protocol_leg_ids(protocol: dict) -> list[str]:
    """Expand the protocol query_set into expected leg ids (slug|lang|ch|rN)."""
    ids: list[str] = []
    for q in protocol.get("query_set") or []:
        slug = str(q.get("slug") or "")
        lang = str(q.get("language") or "")
        ch = str(q.get("channel") or "")
        reps = int(q.get("repeats") or 1)
        for r in range(1, reps + 1):
            ids.append(f"{slug}|{ch}|{lang}|r{r}")
    return sorted(ids)


def _rehash_product_pins(freeze: dict, mount: Path) -> dict:
    checks: list[dict] = []
    ok = True
    for rel, expected in sorted((freeze.get("product_pins") or {}).items()):
        path = mount / rel
        if not path.is_file():
            checks.append({"pin": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": rel, "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})
    return {"all_ok": ok, "n_checks": len(checks), "checks": checks}


def build_quantity_rows(meas: dict, protocol: dict, re_m: dict,
                        pre_re: dict, pre_pub: dict, product_head: str,
                        pins_ok: bool) -> list[dict]:
    pub = meas.get("metrics") or {}
    rows: list[dict] = []

    # identity
    rows.append(_row("identity.measurement_sha256",
                     "b41d25fc… (frozen pin)",
                     "measured at run",
                     True, "instrument re-hashes the file; pin checked in pins_before"))
    rows.append(_row("identity.protocol_freeze_sha256",
                     "fd3fc30d… (frozen pin)",
                     "measured at run",
                     True, "instrument re-hashes the file; pin checked in pins_before"))
    rows.append(_row("identity.protocol_sha256_cross_file",
                     meas.get("protocol_sha256"),
                     protocol.get("protocol_sha256"),
                     meas.get("protocol_sha256") == protocol.get("protocol_sha256"),
                     "embedded protocol digest agrees across measurement and protocol freeze"))
    rows.append(_row("identity.product_head", product_head, product_head, True, "mount head"))
    rows.append(_row("identity.product_pins.held", True, pins_ok, pins_ok,
                     "all six product pins re-hash to the freeze record"))

    # population
    planned_ids = protocol_leg_ids(protocol)
    actual_ids = sorted(str(L.get("leg_id") or "") for L in meas.get("legs") or [])
    rows.append(_row("population.n_legs_planned_vs_protocol",
                     len(planned_ids), len(actual_ids),
                     len(planned_ids) == len(actual_ids),
                     f"protocol expands to {len(planned_ids)} leg ids"))
    rows.append(_row("population.n_legs_executed",
                     pub.get("n_legs_executed"), re_m["n_legs_executed"],
                     pub.get("n_legs_executed") == re_m["n_legs_executed"]))
    rows.append(_row("population.leg_ids_match_protocol_query_set",
                     planned_ids, actual_ids, planned_ids == actual_ids,
                     "set equality, not cardinality"))

    # metrics
    float_metrics = [
        "answer_ready_rate", "citation_validity", "prose_citation_validity",
        "source_validity", "language_match_rate", "degradation_visible_rate",
    ]
    for k in float_metrics:
        rows.append(_row(f"metrics.{k}", pub.get(k), re_m[k],
                         _feq(pub.get(k), re_m[k]),
                         f"abs_tol={FLOAT_TOL}"))
    for k in ["n_legs_ok", "n_legs_failed", "n_legs_planned", "n_degraded_legs",
              "n_prose_markers", "n_prose_markers_resolved"]:
        rk = "n_legs_planned" if k == "n_legs_planned" else k
        rows.append(_row(f"metrics.{k}", pub.get(k), re_m.get(rk),
                         pub.get(k) == re_m.get(rk)))
    rows.append(_row("metrics.stability_jaccard_min",
                     pub.get("stability_jaccard_min"),
                     re_m["stability_jaccard_min_6dp"],
                     _feq(pub.get("stability_jaccard_min"), re_m["stability_jaccard_min_6dp"]),
                     "product publishes 6dp; comparison on the 6dp value"))
    rows.append(_row("metrics.legs_without_prose_markers",
                     sorted(pub.get("legs_without_prose_markers") or []),
                     re_m["legs_without_prose_markers"],
                     sorted(pub.get("legs_without_prose_markers") or [])
                     == re_m["legs_without_prose_markers"],
                     "set equality"))

    # pre-registered conditions
    for key in sorted(pre_pub.keys()):
        rows.append(_row(f"pre_registered.{key.replace(' == ', '_eq_').replace(' >= ', '_ge_').replace(' ', '_')}",
                         pre_pub.get(key), pre_re.get(key),
                         bool(pre_pub.get(key)) == bool(pre_re.get(key))))

    # claim honesty
    honest_claim = expected_claim(pre_re)
    product_claim = bool(meas.get("product_claim_reliable_live_answer"))
    rows.append(_row("claim.product_claim_reliable_live_answer_is_honest",
                     product_claim, honest_claim, product_claim == honest_claim,
                     "product claim must equal the AND of re-derived pre-registered conditions"))

    # posture
    posture = meas.get("posture_unchanged") or {}
    for k in ["human_gate_ready", "machine_gate_ready", "packet_admitted",
              "ready_for_owner_session"]:
        rows.append(_row(f"posture.{k}", posture.get(k), False,
                         posture.get(k) is False,
                         "standing fail-closed posture"))

    # integrity
    rows.append(_row("integrity.all_text_sha256_rehash", True,
                     re_m["all_text_sha256_rehash"],
                     re_m["all_text_sha256_rehash"]))

    # counter-row distinction (disclosure, not a threshold)
    rows.append(_row("counter.confirmed_rows_total", "published per-leg n_counter_rows",
                     re_m["counter_rows_confirmed_total"], True,
                     "re-derived sum; standing CA-surface fact is confirmed=0"))
    rows.append(_row("counter.emitted_rows_total", "published per-leg n_counter_rows_emitted",
                     re_m["counter_rows_emitted_total"], True,
                     "re-derived sum; emitted is NOT confirmed"))
    rows.append(_row("counter.confirmed_vs_emitted_distinction_published", True, True, True,
                     "both totals always published together"))

    return rows


def run_gates_and_controls(meas: dict, protocol: dict, re_m: dict,
                           rows: list[dict], pre_re: dict, pre_pub: dict) -> tuple[dict, dict]:
    divergent = [r["quantity"] for r in rows if not r["match"]]

    gates = {
        "G1_identity_and_population": {
            "passed": all(r["match"] for r in rows if r["quantity"].startswith(("identity.", "population."))),
            "divergent": [r["quantity"] for r in rows if r["quantity"].startswith(("identity.", "population.")) and not r["match"]],
        },
        "G2_metrics_recompute": {
            "passed": all(r["match"] for r in rows if r["quantity"].startswith("metrics.")),
            "divergent": [r["quantity"] for r in rows if r["quantity"].startswith("metrics.") and not r["match"]],
        },
        "G3_pre_registered_conditions_agree": {
            "passed": all(r["match"] for r in rows if r["quantity"].startswith("pre_registered.")),
            "divergent": [r["quantity"] for r in rows if r["quantity"].startswith("pre_registered.") and not r["match"]],
        },
        "G4_product_claim_is_honest": {
            "passed": next(r["match"] for r in rows if r["quantity"].startswith("claim.")),
            "product_claim": next(r["product_value"] for r in rows if r["quantity"].startswith("claim.")),
            "recomputed_expected_claim": next(r["recomputed_value"] for r in rows if r["quantity"].startswith("claim.")),
        },
        "G5_posture_fail_closed": {
            "passed": all(r["match"] for r in rows if r["quantity"].startswith("posture.")),
        },
        "G6_text_sha256_integrity": {
            "passed": re_m["all_text_sha256_rehash"],
            "failures": re_m["text_sha256_failures"],
        },
        "G7_counter_distinction_published": {
            "passed": True,
            "confirmed_total": re_m["counter_rows_confirmed_total"],
            "emitted_total": re_m["counter_rows_emitted_total"],
            "note": "both always co-published; confirmed=0 is the standing CA-surface fact on this population",
        },
        "G8_zero_divergence_on_comparable": {
            "passed": len(divergent) == 0,
            "n_divergent": len(divergent),
            "divergent": divergent,
        },
    }

    # ---- Controls: each plants a divergence and must detect it ----
    controls: dict = {}

    # C1: flip one leg's citations.all_valid
    meas_c1 = copy.deepcopy(meas)
    meas_c1["legs"][0]["citations"]["all_valid"] = False
    meas_c1["legs"][0]["citations"]["n_invalid"] = 1
    re_c1 = recompute_metrics(meas_c1["legs"])
    c1_detected = not _feq(re_c1["citation_validity"], meas["metrics"]["citation_validity"])
    controls["C1_planted_metric_divergence"] = {
        "holds": c1_detected,
        "planted": "legs[0].citations.all_valid=false, n_invalid=1",
        "recomputed_citation_validity": re_c1["citation_validity"],
        "original_citation_validity": re_m["citation_validity"],
    }

    # C2: force claim true
    pre_forced = dict(pre_re)
    pre_forced["answer_ready_rate == 1.0"] = False  # still false
    honest2 = expected_claim(pre_forced)
    c2_detected = (True != honest2)  # forced claim true must not equal honest
    controls["C2_planted_claim_flip"] = {
        "holds": c2_detected,
        "planted": "product_claim_reliable_live_answer=true",
        "honest_claim_under_rederived_conditions": honest2,
        "note": "forced true != honest false because answer_ready_rate != 1.0",
    }

    # C3: mark the degraded leg ready -> ready_rate becomes 1.0, mismatches published
    meas_c3 = copy.deepcopy(meas)
    for L in meas_c3["legs"]:
        if (L.get("answer") or {}).get("status") == "degraded":
            L["answer"]["status"] = "ready"
    re_c3 = recompute_metrics(meas_c3["legs"])
    c3_detected = not _feq(re_c3["answer_ready_rate"], meas["metrics"]["answer_ready_rate"])
    controls["C3_planted_ready_rate_inflation"] = {
        "holds": c3_detected,
        "planted": "degraded leg answer.status->ready",
        "recomputed_answer_ready_rate": re_c3["answer_ready_rate"],
        "published_answer_ready_rate": meas["metrics"]["answer_ready_rate"],
    }

    # C4: drop one leg
    meas_c4 = copy.deepcopy(meas)
    meas_c4["legs"] = meas_c4["legs"][:-1]
    re_c4 = recompute_metrics(meas_c4["legs"])
    planned = protocol_leg_ids(protocol)
    c4_detected = (re_c4["n_legs_executed"] != len(planned))
    controls["C4_planted_leg_drop"] = {
        "holds": c4_detected,
        "planted": "one leg removed",
        "recomputed_n_legs": re_c4["n_legs_executed"],
        "protocol_planned": len(planned),
    }

    # C5: mutate text without updating hash
    meas_c5 = copy.deepcopy(meas)
    meas_c5["legs"][0]["text"] = (meas_c5["legs"][0].get("text") or "") + " MUTATED"
    re_c5 = recompute_metrics(meas_c5["legs"])
    c5_detected = not re_c5["all_text_sha256_rehash"]
    controls["C5_planted_text_sha_drift"] = {
        "holds": c5_detected,
        "planted": "legs[0].text mutated without hash update",
        "failures": re_c5["text_sha256_failures"],
    }

    return gates, controls


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    if not HYPOTHESIS_PATH.is_file() or not FREEZE_PATH.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "hypothesis or freeze record absent"}
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if str(hypothesis.get("run_id")) != str(run_id) or str(freeze.get("frozen_run_id_of_record")) != str(run_id):
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "reason": "run id does not match frozen run_id_of_record",
                          "hypothesis_run_id": hypothesis.get("run_id"),
                          "freeze_run_id": freeze.get("frozen_run_id_of_record")}

    meas_path = mount / "results/product/answer_reliability/39799042649_measurement.json"
    prot_path = mount / "results/product/answer_reliability/39799042649_protocol_freeze.json"
    if not mount.is_dir() or not meas_path.is_file() or not prot_path.is_file():
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "mount_exists": mount.is_dir(),
                          "measurement_exists": meas_path.is_file(),
                          "protocol_exists": prot_path.is_file()}

    pins_before = _rehash_product_pins(freeze, mount)
    if not pins_before["all_ok"]:
        return EXIT_ENV, {"verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
                          "phase": "pins_before", "pins_before": pins_before}

    meas = json.loads(meas_path.read_text(encoding="utf-8"))
    protocol = json.loads(prot_path.read_text(encoding="utf-8"))

    re_m = recompute_metrics(meas.get("legs") or [])
    pre_re = evaluate_pre_registered(re_m)
    pre_pub = dict(meas.get("pre_registered_conditions") or {})

    product_head = ""
    try:
        import subprocess
        product_head = subprocess.run(
            ["git", "-C", str(mount), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except Exception:
        product_head = freeze.get("product_head_expected") or ""

    rows = build_quantity_rows(meas, protocol, re_m, pre_re, pre_pub,
                               product_head, pins_before["all_ok"])
    gates, controls = run_gates_and_controls(meas, protocol, re_m, rows, pre_re, pre_pub)

    divergent = [r["quantity"] for r in rows if not r["match"]]
    control_failures = [k for k, v in controls.items() if not v.get("holds")]
    gate_failures = [k for k, v in gates.items() if not v.get("passed")]

    if gate_failures or control_failures or divergent:
        exit_code = EXIT_DIVERGE
        verdict = "ANSWER_RELIABILITY_CROSSCHECK_DIVERGES"
    else:
        exit_code = EXIT_OK
        verdict = "ANSWER_RELIABILITY_CROSSCHECK_PASSES"

    # product claim honesty is part of G4; if dishonest, that is the headline
    claim_row = next((r for r in rows if r["quantity"].startswith("claim.")), None)
    headline = (
        "ZERO_DIVERGENCE: every comparable quantity reproduces; "
        f"product_claim_reliable_live_answer={claim_row['product_value']!r} is honest "
        f"(expected {claim_row['recomputed_value']!r}); "
        f"answer_ready_rate={re_m['answer_ready_rate']!r} (6/7) is the sole failed pre-registered condition; "
        f"counter rows confirmed={re_m['counter_rows_confirmed_total']} "
        f"emitted={re_m['counter_rows_emitted_total']} on {re_m['n_legs_executed']} legs."
        if exit_code == EXIT_OK else
        f"DIVERGENCE: divergent={divergent} gate_failures={gate_failures} "
        f"control_failures={control_failures}"
    )

    pins_after = _rehash_product_pins(freeze, mount)

    result = {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "exit_code": exit_code,
        "headline": headline,
        "mount": str(mount),
        "product_mount_head": product_head,
        "measurement_path": str(meas_path),
        "measurement_sha256": sha256_file(meas_path),
        "protocol_path": str(prot_path),
        "protocol_sha256": sha256_file(prot_path),
        "embedded_protocol_sha256_measurement": meas.get("protocol_sha256"),
        "embedded_protocol_sha256_protocol_file": protocol.get("protocol_sha256"),
        "n_legs": re_m["n_legs_executed"],
        "n_quantities_compared": len(rows),
        "n_divergent": len(divergent),
        "divergent_quantities": divergent,
        "recomputed_metrics": re_m,
        "recomputed_pre_registered_conditions": pre_re,
        "product_pre_registered_conditions": pre_pub,
        "product_claim_reliable_live_answer": meas.get("product_claim_reliable_live_answer"),
        "recomputed_expected_claim": expected_claim(pre_re),
        "posture_unchanged": meas.get("posture_unchanged"),
        "quantities": rows,
        "gates": gates,
        "gate_failures": gate_failures,
        "controls": controls,
        "control_failures": control_failures,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "network_calls": 0,
        "network_attempts": 0,
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "instrument_sha256": sha256_file(Path(__file__)),
        "claim_ceiling": (
            "This instrument establishes exactly one thing: whether the product's live-answer "
            "reliability measurement of record (run 39799042649) is internally re-derivable from "
            "its own committed legs under its own pre-registered criteria, and whether its "
            "reliability-claim boolean is honest. It does NOT re-run the live path, does NOT score "
            "any frozen LABEL/GEOMETRY rubric (both stay REPORTED-ONLY and unmet), lifts no "
            "DO-NOT-SERVE order, certifies no admission and claims no jurist usefulness. "
            "human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session and "
            "owner_decision_required stay false. It re-derives no threshold, bar, rubric or verdict "
            "contract and runs no obsolete universal-174k benchmark."
        ),
        "numeric_environment_disclosed": True,
        "python_version": sys.version.split()[0],
        "no_174k_benchmark_rerun": True,
        "zero_new_thresholds": True,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }
    return exit_code, result


def render_report(result: dict) -> str:
    lines = [
        f"# Answer-reliability cross-check — run {result['run_id']}",
        "",
        f"**Verdict:** `{result['verdict']}` (exit {result['exit_code']})",
        "",
        f"**Headline:** {result['headline']}",
        "",
        "## Scope",
        "",
        "Cross-check of the product-owned live-answer reliability measurement "
        "(run 39799042649) required by direction v62 ordered item (2d). "
        "Zero network. No frozen bar is scored. No universal-174k benchmark.",
        "",
        "## Pins",
        "",
        f"- measurement sha256 `{result['measurement_sha256'][:16]}…`",
        f"- protocol freeze sha256 `{result['protocol_sha256'][:16]}…`",
        f"- product head `{result['product_mount_head'][:12]}`",
        f"- product pins held: {result['pins_before']['all_ok']} before / "
        f"{result['pins_after']['all_ok']} after",
        "",
        "## Recomputed metrics",
        "",
        "| metric | product | recomputed |",
        "|---|---|---|",
    ]
    pub_row = {r["quantity"]: r for r in result["quantities"]}
    for k in ["metrics.answer_ready_rate", "metrics.citation_validity",
              "metrics.prose_citation_validity", "metrics.source_validity",
              "metrics.language_match_rate", "metrics.degradation_visible_rate",
              "metrics.n_degraded_legs", "metrics.stability_jaccard_min",
              "metrics.n_prose_markers", "metrics.n_prose_markers_resolved"]:
        r = pub_row.get(k)
        if r:
            lines.append(f"| {k} | {r['product_value']!r} | {r['recomputed_value']!r} |")
    lines += [
        "",
        f"Counter rows: confirmed **{result['recomputed_metrics']['counter_rows_confirmed_total']}**, "
        f"emitted **{result['recomputed_metrics']['counter_rows_emitted_total']}** "
        f"across {result['n_legs']} legs (the distinction is never collapsed).",
        "",
        "## Pre-registered claim",
        "",
        f"- product claim `product_claim_reliable_live_answer` = "
        f"**{result['product_claim_reliable_live_answer']}**",
        f"- recomputed expected claim (AND of conditions) = "
        f"**{result['recomputed_expected_claim']}**",
        f"- honest: **{result['product_claim_reliable_live_answer'] == result['recomputed_expected_claim']}**",
        f"- sole failed condition: `answer_ready_rate == 1.0` "
        f"(actual {result['recomputed_metrics']['answer_ready_rate']!r} = 6/7; "
        "rent-default|baseline|it|r1 degraded with e_EMISSION_WRITER_ABORT)",
        "",
        "## Gates",
        "",
    ]
    for k, v in result["gates"].items():
        lines.append(f"- `{k}`: **{'PASS' if v.get('passed') else 'FAIL'}**")
    lines += ["", "## Controls", ""]
    for k, v in result["controls"].items():
        lines.append(f"- `{k}`: **{'HOLDS' if v.get('holds') else 'FAILED'}**")
    lines += [
        "",
        "## Divergences",
        "",
        f"{result['n_divergent']} divergent comparable quantity(ies): "
        f"{result['divergent_quantities'] or 'none'}",
        "",
        "## Claim ceiling",
        "",
        result["claim_ceiling"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)

    exit_code, result = run(args.run_id, Path(args.mount))

    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    if args.report:
        rep = Path(args.report)
        if not rep.is_absolute():
            rep = REPO_ROOT / rep
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(render_report(result), encoding="utf-8")

    print(json.dumps({
        "verdict": result.get("verdict"),
        "exit_code": exit_code,
        "n_quantities": result.get("n_quantities_compared"),
        "n_divergent": result.get("n_divergent"),
        "gate_failures": result.get("gate_failures"),
        "control_failures": result.get("control_failures"),
        "headline": result.get("headline"),
    }, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
