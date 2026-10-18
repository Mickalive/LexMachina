#!/usr/bin/env python3
"""Does the ACCEPTED question-native concept-gap DISCLOSURE defect transfer to
the REBUILT served packet?

    python -m evaluation.question_native_transfer --run-id <run_id> \
        [--hypothesis evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json] \
        [--product-mount /tmp/lex_accepted/product] \
        [--out results/evaluation/question_native_transfer/<run_id>.json]

WHY
---
Cycle 39113690481 established, on served packet ``38839347028``, that a bundle
may ship ``admissible=true, warning_count=0`` while its OWN measured
``query_concepts_under_covered`` is non-empty - the jurist is never told the
bundle retrieved zero rows for a core concept of the question it claims to
answer. Evaluation handed Product ONE disclosure change. The accepted serve
verdict DO-NOT-SERVE-UNCHANGED (outcome B) covers the REBUILT packet
``rebuilt-39027045675``. This module measures whether that one disclosure change
is present on those exact bytes, using the SAME three frozen served_question_ids
(a scored-population transfer; no new anchor set, no new bar, no new threshold).

FREEZE DISCIPLURE
-----------------
The verdict classes, the disclosure predicate (substring markers), the pin set
and the non-vacuity controls are frozen in
``evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json``. An exploratory
feasibility probe was run in the producer's own context BEFORE that freeze and
is disclosed inside the hypothesis file itself; this module is therefore the
claim-bearing instrument and the hypothesis is honestly labelled
hypothesis-after-exploratory-peek, not a blind pre-registration.

REUSE-FIRST
-----------
The concept extraction and row matching are imported BYTE-IDENTICALLY from the
accepted instrument ``evaluation/subject_match_audit.py`` (pinned by sha256 in
the hypothesis); this module never re-implements or re-tunes them. It adds no
gate to any frozen verdict file, writes no frozen file, re-scores no accepted
record and changes no accepted DO-NOT-SERVE order.

Exit 0 = DISCLOSURE_DEFECT_NOT_TRANSFERRED
Exit 1 = DISCLOSURE_DEFECT_TRANSFERRED (the negative result is KEPT)
Exit 2 = NOT_MEASURED / environment / pin mismatch / vacuous control - no
         verdict is ever emitted, never a silent pass
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-question-native-transfer/1"

# --------------------------------------------------------------------------- #
# frozen constants (mirrored from the hypothesis; asserted against it at runtime)
# --------------------------------------------------------------------------- #
FROZEN_QIDS = (
    "de-kapitalverletzung",
    "fr-bail-entretien",
    "it-responsabilita-medica",
)
DISCLOSURE_MARKERS = ("concept", "under_covered", "undercovered", "query_concept")
PACKET_A = "38839347028"
PACKET_B = "rebuilt-39027045675"
HYPOTHESIS_RELPATH = "evaluation/QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json"
PRIOR_RECORD_RELPATH = "results/evaluation/subject_match_audit/39117425713.json"

EXIT_OK = 0
EXIT_FALSIFIED = 1
EXIT_NOT_MEASURED = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# the frozen disclosure predicate (written in the hypothesis before execution)
# --------------------------------------------------------------------------- #
def disclosure_gap_predicate(admissibility: dict) -> dict:
    """Return the predicate's measurement. NEVER upgrades a verdict by itself."""
    under = (admissibility.get("measured") or {}).get("query_concepts_under_covered")
    if under is None:
        under = admissibility.get("query_concepts_under_covered")
    if under is None:
        under = []
    if not isinstance(under, list):
        under = [str(under)]
    findings = admissibility.get("findings") or admissibility.get("warnings") or []
    codes = [str((f or {}).get("code", "")) for f in findings if isinstance(f, dict)]
    disclosing = [
        c for c in codes
        if any(m in c.lower() for m in DISCLOSURE_MARKERS)
    ]
    admissible = bool(admissibility.get("admissible"))
    gap = bool(under) and admissible and not disclosing
    return {
        "query_concepts_under_covered": under,
        "n_under_covered": len(under),
        "admissible": admissible,
        "warning_count": admissibility.get("warning_count"),
        "blocking_count": admissibility.get("blocking_count"),
        "finding_codes": codes,
        "disclosing_finding_codes": disclosing,
        "disclosure_gap_predicate_fires": gap,
    }


# --------------------------------------------------------------------------- #
# independent recomputation using the FROZEN imported instrument functions
# --------------------------------------------------------------------------- #
def _instrument():
    """Import the accepted instrument lazily and verify its pinned sha."""
    from evaluation import subject_match_audit as sma  # noqa: PLC0415
    return sma


def independent_zero_set(question: dict, bundle: dict, sma) -> dict:
    qfields = []
    for k in ("question", "question_text", "query", "text", "title"):
        if isinstance(question.get(k), str):
            qfields.append(question[k])
    if not qfields:
        qfields = [json.dumps(question, ensure_ascii=False)]
    concepts = sma.question_concepts(" ".join(qfields))
    rows = bundle.get("decisions") or bundle.get("rows") or []
    counts = {c: 0 for c in concepts}
    for r in rows:
        t = sma.deaccent(sma.row_match_text(r).lower())
        for c in concepts:
            if c in t:
                counts[c] += 1
    zero = sorted(c for c, n in counts.items() if n == 0)
    return {
        "concepts": concepts,
        "per_concept_rows": counts,
        "zero_set": zero,
        "n_rows": len(rows),
    }


# --------------------------------------------------------------------------- #
# non-vacuity controls (frozen in the hypothesis)
# --------------------------------------------------------------------------- #
def _synthetic_admissibility(under, findings, admissible=True):
    return {
        "admissible": admissible,
        "warning_count": len(findings),
        "blocking_count": 0,
        "measured": {"query_concepts_under_covered": under},
        "findings": [{"code": c, "severity": "warning"} for c in findings],
    }


def run_non_vacuity_controls(sma) -> list[dict]:
    controls: list[dict] = []

    m = disclosure_gap_predicate(
        _synthetic_admissibility(["kapitalverletzung"], []))
    controls.append({
        "control": "control_gap_detector_fires",
        "passed": m["disclosure_gap_predicate_fires"] is True,
        "measured": m,
    })

    m = disclosure_gap_predicate(
        _synthetic_admissibility(["kapitalverletzung"], ["query_concepts_under_covered"]))
    controls.append({
        "control": "control_disclosure_detector_fires",
        "passed": m["disclosure_gap_predicate_fires"] is False
                   and bool(m["disclosing_finding_codes"]),
        "measured": m,
    })

    m = disclosure_gap_predicate(_synthetic_admissibility([], []))
    controls.append({
        "control": "control_empty_gap_is_not_a_defect",
        "passed": m["disclosure_gap_predicate_fires"] is False,
        "measured": m,
    })

    fake_q = {"question": "Kapitalverletzung und Uberwachungspflicht des Arbeitgebers"}
    covered = {"decisions": [{"decision_id": "x", "title": "Zur Kapitalverletzung"}]}
    rec = independent_zero_set(fake_q, covered, sma)
    controls.append({
        "control": "control_independent_recompute_covers",
        "passed": "kapitalverletzung" not in rec["zero_set"],
        "measured": rec,
    })

    empty = {"decisions": [{"decision_id": "y", "title": "Nichts Relevantes"}]}
    rec2 = independent_zero_set(fake_q, empty, sma)
    controls.append({
        "control": "control_independent_recompute_zero",
        "passed": "kapitalverletzung" in rec2["zero_set"],
        "measured": rec2,
    })

    return controls


# --------------------------------------------------------------------------- #
# pin re-hash
# --------------------------------------------------------------------------- #
def rehash_pins(hyp: dict, root: Path, mount: Path) -> dict:
    pins = hyp["frozen_inputs"]
    results: dict[str, dict] = {}
    ok = True

    def check(name: str, path: Path, expected: str) -> None:
        nonlocal ok
        if not path.is_file():
            results[name] = {"present": False, "expected": expected}
            ok = False
            return
        actual = sha256_file(path)
        match = actual == expected
        results[name] = {
            "present": True, "expected": expected, "actual": actual, "match": match,
        }
        if not match:
            ok = False

    check("v2_1_hypothesis", root / "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2_1.json",
          pins["v2_1_hypothesis_sha256"])
    check("subject_match_audit_instrument", root / "evaluation/subject_match_audit.py",
          pins["subject_match_audit_instrument_sha256"])
    check("prior_accepted_question_native_record", root / PRIOR_RECORD_RELPATH,
          pins["prior_accepted_question_native_record_sha256"])

    bdir = mount / "results" / "product" / "gate_packet" / PACKET_B
    check("rebuilt_packet_json", bdir / "packet.json", pins["rebuilt_packet_json_sha256"])
    for qid in FROZEN_QIDS:
        check(f"rebuilt_bundle::{qid}", bdir / "questions" / f"{qid}.bundle.json",
              pins["rebuilt_bundle_sha256"][qid])
        check(f"rebuilt_question::{qid}", bdir / "questions" / f"{qid}.question.json",
              pins["rebuilt_question_sha256"][qid])
        check(f"rebuilt_admissibility::{qid}", bdir / "questions" / f"{qid}.admissibility.json",
              pins["rebuilt_admissibility_sha256"][qid])
    return {"all_match": ok, "checks": results}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(run_id: str, hypothesis_path: Path, mount: Path, root: Path) -> dict:
    if not hypothesis_path.is_file():
        raise FileNotFoundError(f"hypothesis not found: {hypothesis_path}")
    hyp = _load_json(hypothesis_path)

    # assert the module's frozen constants mirror the hypothesis file
    frozen_rule = hyp["success_rule_FROZEN"]
    assert tuple(hyp["frozen_inputs"]["frozen_qids_UNCHANGED"]) == FROZEN_QIDS, \
        "qid set drift between module and hypothesis"
    assert PACKET_B in hyp["frozen_inputs"]["packet_b_rebuilt"], "packet id drift"

    pins = rehash_pins(hyp, root, mount)
    sma = _instrument()
    instrument_actual = sha256_file(root / "evaluation/subject_match_audit.py")
    controls = run_non_vacuity_controls(sma)
    controls_ok = all(c["passed"] for c in controls)

    bdir = mount / "results" / "product" / "gate_packet" / PACKET_B
    adir = mount / "results" / "product" / "gate_packet" / PACKET_A
    per_qid = []
    for qid in FROZEN_QIDS:
        qpath = bdir / "questions" / f"{qid}.question.json"
        bpath = bdir / "questions" / f"{qid}.bundle.json"
        apath = bdir / "questions" / f"{qid}.admissibility.json"
        if not (qpath.is_file() and bpath.is_file() and apath.is_file()):
            return {
                "schema": SCHEMA, "run_id": run_id, "verdict": "NOT_MEASURED",
                "reason": f"missing artifact for {qid} under {bdir}",
            }
        q = _load_json(qpath)
        b = _load_json(bpath)
        a = _load_json(apath)
        pred = disclosure_gap_predicate(a)
        indep = independent_zero_set(q, b, sma)
        product_zero = set(pred["query_concepts_under_covered"])
        indep_zero = set(indep["zero_set"])
        # packet-A admissibility for side-by-side (optional)
        a_prior = None
        prior_apath = adir / "questions" / f"{qid}.admissibility.json"
        if prior_apath.is_file():
            a_prior = disclosure_gap_predicate(_load_json(prior_apath))
        per_qid.append({
            "qid": qid,
            "rebuilt_predicate": pred,
            "rebuilt_independent_recomputation": indep,
            "product_vs_independent_agreement": {
                "product_zero_set": sorted(product_zero),
                "independent_zero_set": sorted(indep_zero),
                "agree": product_zero == indep_zero,
                "only_product": sorted(product_zero - indep_zero),
                "only_independent": sorted(indep_zero - product_zero),
            },
            "prior_packet_38839347028_predicate": a_prior,
        })

    any_fires = any(r["rebuilt_predicate"]["disclosure_gap_predicate_fires"] for r in per_qid)
    if not pins["all_match"]:
        verdict, exit_code = "NOT_MEASURED", EXIT_NOT_MEASURED
        reason = "pin re-hash mismatch"
    elif not controls_ok:
        verdict, exit_code = "NOT_MEASURED", EXIT_NOT_MEASURED
        reason = "non-vacuity control failed"
    elif any_fires:
        verdict, exit_code = "DISCLOSURE_DEFECT_TRANSFERRED", EXIT_FALSIFIED
        reason = "at least one qid measures a non-empty under-covered set, is admissible, and ships no disclosing finding code"
    else:
        verdict, exit_code = "DISCLOSURE_DEFECT_NOT_TRANSFERRED", EXIT_OK
        reason = "no qid satisfies the disclosure_gap_predicate on the rebuilt packet"

    disagreements = [
        r["qid"] for r in per_qid
        if not r["product_vs_independent_agreement"]["agree"]
    ]

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": hyp["direction_version_at_freeze"],
        "hypothesis_path": str(hypothesis_path.relative_to(root)) if hypothesis_path.is_relative_to(root) else str(hypothesis_path),
        "hypothesis_sha256": sha256_file(hypothesis_path),
        "hypothesis_label": "hypothesis-after-exploratory-peek (disclosed inside the hypothesis file)",
        "packet_measured": PACKET_B,
        "packet_prior": PACKET_A,
        "product_mount": str(mount),
        "network_requests": 0,
        "frozen_qids": list(FROZEN_QIDS),
        "disclosure_markers": list(DISCLOSURE_MARKERS),
        "pins": pins,
        "instrument_subject_match_audit_sha256": instrument_actual,
        "non_vacuity_controls": controls,
        "non_vacuity_all_passed": controls_ok,
        "per_qid": per_qid,
        "independent_recomputation_disagreements": disagreements,
        "any_disclosure_gap_fires": any_fires,
        "verdict": verdict,
        "verdict_reason": reason,
        "exit_code": exit_code,
        "claim_ceiling": hyp["claim_ceiling"],
        "success_rule": {
            "disclosure_gap_predicate": frozen_rule["disclosure_gap_predicate"],
            "verdict_classes": frozen_rule["verdict_classes"],
        },
        "unchanged": [
            "human_gate_ready=false",
            "accepted DO-NOT-SERVE order on 38839347028",
            "accepted rebuilt-packet verdict DO-NOT-SERVE-UNCHANGED (outcome B)",
            "frozen absolute bars LABEL_UNSOUND 5/65 and GEOMETRY_UNSOUND 0/3",
            "no frozen rubric, threshold or bar edited",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    hyp_path = Path(args.hypothesis) if args.hypothesis else root / HYPOTHESIS_RELPATH
    mount = Path(args.product_mount) if args.product_mount else None
    if mount is None:
        import os
        for env in ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT"):
            if os.environ.get(env):
                mount = Path(os.environ[env])
                break
        if mount is None:
            mount = Path("/tmp/lex_accepted/product")

    try:
        record = run(args.run_id, hyp_path, mount, root)
    except Exception as exc:  # environment / parse error -> NOT_MEASURED, exit 2
        record = {
            "schema": SCHEMA, "run_id": args.run_id,
            "verdict": "NOT_MEASURED", "exit_code": EXIT_NOT_MEASURED,
            "error": f"{type(exc).__name__}: {exc}",
            "network_requests": 0,
        }

    out = Path(args.out) if args.out else (
        root / "results" / "evaluation" / "question_native_transfer" / f"{args.run_id}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"verdict={record.get('verdict')} exit={record.get('exit_code')} out={out}")
    return int(record.get("exit_code", EXIT_NOT_MEASURED))


if __name__ == "__main__":
    sys.exit(main())
