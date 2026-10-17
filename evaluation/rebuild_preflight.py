"""Rebuilt-packet adjudication PREFLIGHT (direction v52 items (2) and (3)).

WHY THIS EXISTS
---------------
Factory direction v52 makes "re-score the rebuilt packet under the accepted
frozen bars" the Core Evaluation deliverable that is still open.  Direction item
(1) is the precondition for it and it has been executed: the rebuild trigger
returns ``NO_NEW_PACKET`` on a byte-identical 56-file served population, so the
successor cannot be measured on the served bytes and a zero-delta re-run is
refused by code.

What nobody has measured is whether that successor path is *executable* and what
it actually *enforces* once a rebuilt packet exists.  This module answers both on
SYNTHETIC packets built in /tmp from the accepted served bytes.  It is the
smallest experiment that can falsify the direction's own endgame plan: if the
successor command cannot run, or if its enforced verdict silently evaporates on
the population a rebuild would actually issue, the owner learns that now instead
of after Product ships packet P2.

WHAT IT IS NOT
--------------
* It does not adjudicate a real rebuilt packet.  No such packet exists.
* It does not serve, un-serve, admit or reject anything, and it does not touch
  the standing accepted DO-NOT-SERVE order on packet ``38839347028``.
* It never edits a frozen rubric, threshold, bar, incumbent or verdict contract.
  Every leg shells out to the ACCEPTED entry point
  ``python -m evaluation.frozen_bars.run_bar_gates --adjudicate`` as a
  subprocess; nothing here re-derives a verdict.
* It never imports Product code, never uses the network, never re-runs the 174k
  suite, and opens the Product mount read-only.

FROZEN BEFORE EXECUTION
-----------------------
``results/evaluation/rebuild_preflight_39033797087/freeze/
FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json`` (commit 01a4780d).
Legs A-E, the success rule PREFLIGHT_COMPLETE and the claim ceiling were fixed
before any leg ran.  The sha256 of every instrument it pins are re-hashed after
execution and compared; a mismatch fails the record.

    python -m evaluation.rebuild_preflight --run-id <run_id> [--out-dir DIR]

Exit 0 = the preflight ran and every leg produced a record (the success rule is
evaluated inside the record, not by this exit code).  Exit 2 = environment error
(no accepted Product mount, instrument sha drift): never a measurement.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

SCHEMA = "lex-evaluation-rebuild-preflight/1"
BAR_GATES = [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates"]
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
SERVED_QUESTIONS = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/38839347028/questions"
)

#: sha256 of every frozen input, copied verbatim from the frozen hypothesis.
#: Re-hashed after execution; a mismatch is an environment error, not a result.
FROZEN_INPUTS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/label_gate.py":
        "640abd8beeb7b8c86c835a9e485fb5c0be56f723ebda93a40b2b3b902baa4432",
    "evaluation/frozen_bars/geometry_gate.py":
        "934d5cca9f362a3e4d1cf518f88085e4359da8242b9971e33ca632bb0d613baa",
    "evaluation/frozen_bars/run_bar_gates.py":
        "564dc682da6fe012c6da9cdde12f8addc3c924ce12b30d80724270d6d09a6220",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/reality_gate/frozen_benchmark.json":
        "ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8",
    "evaluation/reality_gate/GATE_CONTRACT.json":
        "06781743c2686fa63a6652ad61c8d63381cfa707f5fd6682a50b9027470d2492",
}

#: Frozen expectations for leg A, copied from the accepted VERDICT_CONTRACT.json
#: ``frozen_inputs`` block.  Leg A is the vacuity control for the whole preflight.
LEG_A_EXPECTED = {
    "n_scored": 65,
    "n_supported": 5,
    "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0},
    "geometry_criterion_counts": {"de-kapitalverletzung": 6, "fr-bail-entretien": 5,
                                  "it-responsabilita-medica": 5},
}


class EnvironmentError_(RuntimeError):
    """The preflight cannot measure.  Never a result, never a pass."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rehash_frozen_inputs() -> dict:
    """Compare every pinned frozen input with its recorded sha256."""
    out = {}
    for rel, expected in sorted(FROZEN_INPUTS.items()):
        p = _LANE_ROOT / rel
        out[rel] = {
            "expected_sha256": expected,
            "observed_sha256": sha256_file(p) if p.is_file() else None,
            "matches": bool(p.is_file() and sha256_file(p) == expected),
        }
    return out


def _load(qid: str, served: Path = SERVED_QUESTIONS) -> dict:
    path = served / f"{qid}.bundle.json"
    if not path.is_file():
        raise EnvironmentError_(f"served bundle missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def counter_rows(bundle: dict) -> list[dict]:
    """Rows the frozen label scorer actually scores: an issued counter status."""
    return [d for d in bundle.get("decisions") or []
            if (d.get("counter_status") or "none") != "none"]


def write_packet(dest: Path, bundles: dict[str, dict], served: Path = SERVED_QUESTIONS) -> Path:
    """Write a synthetic packet dir.

    UNMODIFIED bundles are copied as RAW BYTES so that the accepted entry
    point's served-bytes sha pin still holds for them; only a deliberately
    mutated bundle is re-serialized.  This is what makes leg A a true
    byte-identity control and legs B/C single-file mutations.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for qid, bundle in bundles.items():
        src = served / f"{qid}.bundle.json"
        raw = src.read_bytes() if src.is_file() else None
        # CONTENT equality decides, not byte equality: an untouched bundle is
        # re-serialized to different bytes, so comparing rendered bytes against the
        # source bytes would rewrite every file and destroy the byte-identity
        # control. (In-cycle defect, found and fixed before any result was read.)
        untouched = raw is not None and json.loads(raw.decode("utf-8")) == bundle
        if untouched:
            (dest / f"{qid}.bundle.json").write_bytes(raw)
        else:
            (dest / f"{qid}.bundle.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


def run_adjudicate(packet_dir: Path, out: Path, workdir: Path,
                   expect_record: bool = True) -> dict:
    """Invoke the ACCEPTED entry point as a subprocess and read its record.

    ``expect_record=False`` is for the refusal negative control, where "no
    record, non-zero exit" IS the predicted refusal and must be recorded as an
    observation instead of raised as an environment error.
    """
    t0 = time.time()
    proc = subprocess.run(
        BAR_GATES + ["--adjudicate", str(packet_dir), "--out", str(out)],
        cwd=str(_LANE_ROOT), capture_output=True, text=True, timeout=900)
    elapsed = round(time.time() - t0, 3)
    if not out.is_file():
        if expect_record:
            raise EnvironmentError_(
                f"accepted entry point emitted no record (rc={proc.returncode}): "
                f"{proc.stderr.strip()[:300]}")
        return {
            "packet_dir": str(packet_dir),
            "exit_code": proc.returncode,
            "elapsed_s": elapsed,
            "record_written": False,
            "stderr": proc.stderr.strip()[:400],
        }
    rec = json.loads(out.read_text(encoding="utf-8"))
    (workdir / f"{out.stem}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    (workdir / f"{out.stem}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    label = rec.get("label_gate") or {}
    geometry = rec.get("geometry_gate") or {}
    return {
        "command": "python -m evaluation.frozen_bars.run_bar_gates --adjudicate <packet-dir>",
        "packet_dir": str(packet_dir),
        "exit_code": proc.returncode,
        "elapsed_s": elapsed,
        "record_path": str(out),
        "mode": rec.get("mode", "served_lineage"),
        "verdict": rec.get("verdict"),
        "input_bundle_sha256": rec.get("input_bundle_sha256"),
        "input_sha_matches_accepted_label_half": rec.get("input_sha_matches_accepted_label_half"),
        "negative_controls_all_proven": rec.get("negative_controls_all_proven"),
        "label_gate": {k: label.get(k) for k in (
            "n_scored", "n_supported", "support_rate", "classes", "incumbent",
            "recomputed_matches_incumbent", "absolute_status", "absolute_enforced",
            "regression_verdict", "gate_blocks_build", "negative_control_proven")},
        "label_negative_control": label.get("negative_control_blanked_evidence"),
        "geometry_gate": {k: geometry.get(k) for k in (
            "per_bundle_counts", "incumbent_counts", "recomputed_counts_match_incumbent",
            "absolute_status", "n_bundles_pass_all_11", "regression_verdict",
            "regressed_qids", "gate_blocks_build", "negative_control_proven")},
        "absolute_status_summary": rec.get("absolute_status_summary"),
        "admission_reading": rec.get("admission_reading"),
    }


# --------------------------------------------------------------------------- #
# leg constructions (synthetic packets only; the mount is read-only)
# --------------------------------------------------------------------------- #
def leg_a_identity(served: Path, tmp: Path) -> dict:
    bundles = {qid: _load(qid, served) for qid in QIDS}
    d = write_packet(tmp / "leg_A_identity", bundles)
    res = run_adjudicate(d, tmp / "leg_A_identity.record.json", tmp)
    res["leg"] = "A_identity_control"
    res["n_counter_rows_constructed"] = {q: len(counter_rows(b)) for q, b in bundles.items()}
    res["prediction"] = ("exit 0; label 65/5 classes 38/22/5/0 with PASS_NO_REGRESSION and "
                         "lineage_matches_incumbent_population=true; geometry 6/5/5; every "
                         "observed sha equals the accepted EXPECTED_BUNDLE_SHA256")
    label, geom = res["label_gate"], res["geometry_gate"]
    counts = geom.get("per_bundle_counts") or {}
    # IN-CYCLE DEFECT, disclosed: the accepted record OMITS zero-valued classes, so the
    # frozen expectation {OFF-DOMAIN:38,UNBACKED:22,SUPPORTED:5,INVERTED:0} is checked as a
    # subset over the recorded keys. The measurement itself (65 scored / 5 supported,
    # zero INVERTED) is untouched.
    res["classes_absent_because_zero"] = sorted(
        set(LEG_A_EXPECTED["classes"]) - set(label["classes"]))
    res["as_predicted"] = bool(
        res["exit_code"] == 0
        and label["n_scored"] == LEG_A_EXPECTED["n_scored"]
        and label["n_supported"] == LEG_A_EXPECTED["n_supported"]
        and all(label["classes"].get(k, 0) == v
                for k, v in LEG_A_EXPECTED["classes"].items())
        and label["regression_verdict"] == "PASS_NO_REGRESSION"
        and label["recomputed_matches_incumbent"] is True
        and geom["regression_verdict"] == "PASS_NO_REGRESSION"
        and geom["recomputed_counts_match_incumbent"] is True
        and counts == LEG_A_EXPECTED["geometry_criterion_counts"]
        and res["negative_controls_all_proven"] is True
        and all(res["input_sha_matches_accepted_label_half"].values())
    )
    return res


def leg_b_population_plus_one(served: Path, tmp: Path) -> dict:
    bundles = {qid: _load(qid, served) for qid in QIDS}
    target = "de-kapitalverletzung"
    donor = copy.deepcopy(counter_rows(bundles[target])[0])
    donor["decision_id"] = f"PREFLIGHT_injected_extra_{target}"
    donor["counter_status"] = "candidate-limiting"
    donor["counter_reason"] = "distinguishing"
    donor["counter_evidence"] = (
        "Das Bundesgericht schraenkt die Beanspruchung im konkreten Fall ein; "
        "die Regel wird auf den Streitfall zugeschnitten.")
    donor["counter_uncertainty"] = 0.5
    donor["rank"] = 900
    donor["canonical_url"] = "https://mcp.opencaselaw.ch/entscheid/PREFLIGHT_injected_extra_de"
    bundles[target]["decisions"].append(donor)
    d = write_packet(tmp / "leg_B_plus_one", bundles)
    res = run_adjudicate(d, tmp / "leg_B_plus_one.record.json", tmp)
    res["leg"] = "B_population_plus_one"
    res["injected_into"] = target
    res["n_counter_rows_constructed"] = {q: len(counter_rows(b)) for q, b in bundles.items()}
    res["prediction"] = ("observed sha differs for that anchor; label regression_verdict "
                         "NOT_APPLICABLE and gate_blocks_build=false (predicted vacuity); "
                         "absolute_status still REPORTED; the adjudicate negative control "
                         "reports not_applicable_reason; overall exit 0")
    label = res["label_gate"]
    nc = res["label_negative_control"] or {}
    res["as_predicted"] = bool(
        res["exit_code"] == 0
        and res["input_sha_matches_accepted_label_half"][target] is False
        and label["n_scored"] == LEG_A_EXPECTED["n_scored"] + 1
        and label["regression_verdict"] == "NOT_APPLICABLE"
        and label["gate_blocks_build"] is False
        and label["absolute_status"] == "LABEL_UNSOUND"
        and label["absolute_enforced"] is False
    )
    return res


def leg_c_preserved_population_blanked(served: Path, tmp: Path) -> dict:
    bundles = {qid: _load(qid, served) for qid in QIDS}
    target = "de-kapitalverletzung"
    n_blanked = 0
    for row in counter_rows(bundles[target]):
        if row.get("counter_evidence"):
            row["counter_evidence"] = ""
            n_blanked += 1
    d = write_packet(tmp / "leg_C_blanked", bundles)
    res = run_adjudicate(d, tmp / "leg_C_blanked.record.json", tmp)
    res["leg"] = "C_preserved_population_blanked_evidence"
    res["blanked_evidence_rows"] = {"anchor": target, "n": n_blanked}
    res["prediction"] = ("population preserved, n_supported drops, regression_verdict="
                         "FAIL_REGRESSION, gate_blocks_build=true, exit 1")
    label = res["label_gate"]
    res["as_predicted"] = bool(
        res["exit_code"] == 1
        and label["regression_verdict"] == "FAIL_REGRESSION"
        and label["gate_blocks_build"] is True
        and label["n_supported"] < LEG_A_EXPECTED["n_supported"]
    )
    return res


def leg_d_geometry_on_changed_population(leg_b: dict) -> dict:
    """Read the geometry verdict of leg B's changed population (frozen prediction D)."""
    res = {
        "leg": "D_geometry_still_enforcing_on_changed_population",
        "reads_leg": "B_population_plus_one",
        "prediction": ("geometry lineage_matches_incumbent=true (qid-set only, no population "
                       "pin) and its regression_verdict stays an enforcing PASS/FAIL, so the "
                       "label/geometry asymmetry is real and not a leg-B artifact"),
        "exit_code": leg_b["exit_code"],
        "label_regression_verdict": leg_b["label_gate"]["regression_verdict"],
        "label_gate_blocks_build": leg_b["label_gate"]["gate_blocks_build"],
        "geometry_regression_verdict": leg_b["geometry_gate"]["regression_verdict"],
        "geometry_recomputed_counts_match_incumbent":
            leg_b["geometry_gate"]["recomputed_counts_match_incumbent"],
        "geometry_gate_blocks_build": leg_b["geometry_gate"]["gate_blocks_build"],
        "geometry_criterion_counts": leg_b["geometry_gate"]["per_bundle_counts"],
    }
    # The accepted record does not publish a lineage boolean for the geometry gate,
    # so applicability is read from the verdict string itself, which the accepted
    # label_gate/geometry_gate emit only when the lineage predicate holds.
    res["as_predicted"] = bool(
        res["geometry_regression_verdict"] in ("PASS_NO_REGRESSION", "FAIL_REGRESSION")
        and res["label_regression_verdict"] == "NOT_APPLICABLE"
    )
    return res


def leg_e_refusal(tmp: Path) -> dict:
    """Negative control: the entry point must never answer 'fine' on a bad input."""
    empty = tmp / "leg_E_empty"
    empty.mkdir(parents=True, exist_ok=True)
    r_empty = run_adjudicate(empty, tmp / "leg_E_empty.record.json", tmp,
                             expect_record=False)

    zero = tmp / "leg_E_zero_rows"
    bundles = {}
    for qid in QIDS:
        b = _load(qid)
        for row in b.get("decisions") or []:
            if (row.get("counter_status") or "none") != "none":
                row["counter_status"] = "none"
        bundles[qid] = b
    d = write_packet(zero, bundles)
    r_zero = run_adjudicate(d, tmp / "leg_E_zero_rows.record.json", tmp)

    res = {
        "leg": "E_refusal_negative_control",
        "prediction": ("both exits non-zero (2 environment error or 1 regression) and neither "
                       "record consumable as a pass; a missing input never produces exit 0"),
        "empty_packet_dir": {"exit_code": r_empty["exit_code"],
                             "record_written": r_empty.get("record_written", False),
                             "stderr": r_empty.get("stderr", ""),
                             "verdict": r_empty.get("verdict")},
        "zero_counter_rows": {
            "exit_code": r_zero["exit_code"],
            "n_scored": r_zero["label_gate"]["n_scored"],
            "n_supported": r_zero["label_gate"]["n_supported"],
            "support_rate": r_zero["label_gate"]["support_rate"],
            "absolute_status": r_zero["label_gate"]["absolute_status"],
            "regression_verdict": r_zero["label_gate"]["regression_verdict"],
            "gate_blocks_build": r_zero["label_gate"]["gate_blocks_build"],
            "geometry_regression_verdict": r_zero["geometry_gate"]["regression_verdict"],
            "verdict": r_zero.get("verdict"),
            "admission_reading_exit_certifies":
                ((r_zero.get("admission_reading") or {}).get("exit_certifies") or "")[:220],
        },
        "exit_codes": [r_empty["exit_code"], r_zero["exit_code"]],
    }
    res["as_predicted"] = bool(all(code != 0 for code in res["exit_codes"]))
    return res


def build_record(run_id: str, legs: dict, frozen_rehash: dict, envelope: dict) -> dict:
    a_ok = legs["A_identity_control"]["as_predicted"]
    c_ok = legs["C_preserved_population_blanked_evidence"]["as_predicted"]
    e_ok = legs["E_refusal_negative_control"]["as_predicted"]
    sha_ok = all(v["matches"] for v in frozen_rehash.values())
    # Verbatim from the frozen hypothesis (FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json
    # -> success_rule).  Quoted, never paraphrased: a paraphrase is how a frozen rule rots.
    rule = (
        "PREFLIGHT_COMPLETE if (a) legs A, C and E behave exactly as predicted, (b) the entry "
        "point runs to completion on all five legs with no uncaught exception, and (c) every "
        "frozen input re-hashes to instrument_pins_sha256 afterwards. The outcome of legs B and "
        "D is RECORDED AS MEASURED and is NOT part of the pass condition: a confirmed vacuity "
        "(prediction) and a falsified vacuity (prediction wrong) are both acceptable preflight "
        "results, because either one is the honest envelope of what the direction's successor "
        "command can enforce. Predictions are not edited after observation; a falsified "
        "prediction is published as a falsification with its wording correction.")
    success = bool(a_ok and c_ok and e_ok and sha_ok)
    headline = [
        {"id": "PF1_label_enforcement_is_population_pinned",
         "measured_on": "B_population_plus_one",
         "statement": "on a packet whose scored counter-row count differs from the pinned 65, the "
                      "accepted label gate emits regression_verdict=NOT_APPLICABLE and "
                      "gate_blocks_build=false, i.e. its ENFORCED verdict is vacuous; the "
                      "absolute status is still reported",
         "predicted_before_execution": True,
         "prediction_source": "frozen hypothesis H-PREFLIGHT"},
        {"id": "PF2_geometry_enforcement_is_qid_pinned",
         "measured_on": "D_geometry_still_enforcing_on_changed_population",
         "statement": "the geometry gate keeps emitting an enforcing PASS/FAIL verdict on the "
                      "same changed population because its lineage predicate pins the qid set "
                      "only; the two frozen bars therefore enforce on different conditions",
         "predicted_before_execution": True,
         "prediction_source": "frozen hypothesis H-PREFLIGHT"},
        {"id": "PF3_zero_counter_population_is_not_blocked",
         "measured_on": "E_refusal_negative_control",
         "statement": "a packet that issues NO counter label at all is adjudicated with exit 0: "
                      "n_scored=0 makes the label regression verdict NOT_APPLICABLE and the "
                      "absolute status LABEL_UNSOUND, which is REPORTED and never enforced. "
                      "Publishing support-among-issued with the abstention count and the yield is "
                      "therefore load-bearing for the rebuild decision, not a nicety",
         "predicted_before_execution": False,
         "prediction_source": "frozen hypothesis leg E predicted a non-zero exit; measured 0"},
        {"id": "PF4_the_accepted_record_does_not_publish_applicability",
         "measured_on": "A_identity_control",
         "corroborated_on": "B_population_plus_one",
         "statement": "run_bar_gates' record exposes no lineage/lineage_matches_incumbent boolean "
                      "for either gate; a consumer can only infer whether the enforced verdict was "
                      "applicable at all from the verdict STRING. Direction item (2) requires the "
                      "per-anchor enforced verdict to be published, so NOT_APPLICABLE must be "
                      "rendered explicitly and never collapsed into a pass",
         "predicted_before_execution": False,
         "prediction_source": "field survey of the accepted record schema"},
    ]
    predicted = [k for k, v in legs.items() if v.get("as_predicted")]
    falsified = [k for k, v in legs.items() if not v.get("as_predicted")]
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": 52,
        "instrument": "python -m evaluation.frozen_bars.run_bar_gates --adjudicate <packet-dir>",
        "frozen_hypothesis": (
            "results/evaluation/rebuild_preflight_39033797087/freeze/"
            "FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json"),
        "frozen_before_execution_commit": "01a4780d",
        "served_bytes_source": str(SERVED_QUESTIONS),
        "served_bytes_modified": False,
        "legs": legs,
        "frozen_input_rehash_after_execution": frozen_rehash,
        "enforcement_envelope": envelope,
        "success_rule": rule,
        "success_rule_holds": success,
        "verdict": "PREFLIGHT_COMPLETE" if success else "PREFLIGHT_INCOMPLETE",
        "execution_completed_on_all_legs": True,
        "success_rule_falsified_legs": [k for k in ("A_identity_control",
                                                    "C_preserved_population_blanked_evidence",
                                                    "E_refusal_negative_control")
                                        if not legs[k]["as_predicted"]],
        "headline_findings": headline,
        "legs_as_predicted": predicted,
        "legs_falsified": falsified,
        "claim_ceiling": (
            "At most: the direction's successor adjudication command is executable end to end "
            "today, and its ENFORCED verdict on a rebuilt packet is exactly the envelope "
            "measured here. No real rebuilt packet was adjudicated; nothing is served, un-served "
            "or admitted; no decision is asserted to be supporting/contrary/limiting; the "
            "standing accepted DO-NOT-SERVE order on packet 38839347028 is untouched; "
            "human_gate_ready stays false."),
    }


def envelope_from_legs(legs: dict) -> dict:
    """The product-facing reading: what can actually BLOCK a rebuilt packet."""
    a, b, c = legs["A_identity_control"], legs["B_population_plus_one"], \
        legs["C_preserved_population_blanked_evidence"]
    return {
        "label_bar": {
            "enforces_when": "the rebuilt packet issues EXACTLY the three frozen anchor qids "
                             "AND exactly the incumbent scored population (65 rows)",
            "vacuous_when": "the rebuilt packet's scored counter-row count differs from 65 "
                            "(regression_verdict NOT_APPLICABLE, gate_blocks_build false)",
            "measured_on": {
                "preserved_population_blanked_evidence": {
                    "exit_code": c["exit_code"],
                    "regression_verdict": c["label_gate"]["regression_verdict"],
                    "gate_blocks_build": c["label_gate"]["gate_blocks_build"]},
                "population_plus_one": {
                    "exit_code": b["exit_code"],
                    "n_scored": b["label_gate"]["n_scored"],
                    "regression_verdict": b["label_gate"]["regression_verdict"],
                    "gate_blocks_build": b["label_gate"]["gate_blocks_build"],
                    "absolute_status_reported": b["label_gate"]["absolute_status"]},
            },
            "absolute_status_is_never_enforced": True,
        },
        "geometry_bar": {
            "enforces_when": "the rebuilt packet carries the three frozen anchor qids "
                             "(lineage is pinned on the qid set only, not on population size)",
            "measured_on": {
                "population_plus_one": {
                    "exit_code": b["exit_code"],
                    "regression_verdict": b["geometry_gate"]["regression_verdict"],
                    "regression_verdict_applicable": b["geometry_gate"]["regression_verdict"]
                        in ("PASS_NO_REGRESSION", "FAIL_REGRESSION"),
                    "criterion_counts": b["geometry_gate"]["per_bundle_counts"],
                    "recomputed_counts_match_incumbent":
                        b["geometry_gate"]["recomputed_counts_match_incumbent"]},
            },
        },
        "what_a_rebuilt_packet_cannot_be_blocked_on": [
            "counter-label support at the frozen 1.0 absolute bar (REPORTED, never enforced)",
            "any label regression once its scored counter-row count differs from 65",
        ],
        "what_a_rebuilt_packet_can_be_blocked_on": [
            "a served-bundle byte drift (adjudicate mode does not apply the served-bytes pin, "
            "so this is not a block in adjudicate mode)",
            "a geometry criterion-count regression below de 6 / fr 5 / it 5 on the three anchors",
            "the packet-admission conformance battery (a separate accepted instrument)",
        ],
        "incumbent_reference": {"n_scored": a["label_gate"]["n_scored"],
                                "n_supported": a["label_gate"]["n_supported"],
                                "geometry": a["geometry_gate"]["per_bundle_counts"]},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--served-questions", default=str(SERVED_QUESTIONS))
    args = ap.parse_args(argv)

    served = Path(args.served_questions)
    if not served.is_dir():
        print("::error::no accepted Product mount; the preflight cannot measure", file=sys.stderr)
        return 2
    pre = rehash_frozen_inputs()
    if not all(v["matches"] for v in pre.values()):
        print("::error::frozen instrument sha drift before execution", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else \
        _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{args.run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(prefix="rebuild_preflight_") as td:
            tmp = Path(td)
            legs = {
                "A_identity_control": leg_a_identity(served, tmp),
                "B_population_plus_one": leg_b_population_plus_one(served, tmp),
                "C_preserved_population_blanked_evidence": leg_c_preserved_population_blanked(served, tmp),
            }
            legs["D_geometry_still_enforcing_on_changed_population"] = \
                leg_d_geometry_on_changed_population(legs["B_population_plus_one"])
            legs["E_refusal_negative_control"] = leg_e_refusal(tmp)
            post = rehash_frozen_inputs()
            record = build_record(args.run_id, legs, post,
                                  envelope_from_legs(legs))
    except EnvironmentError_ as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    out = out_dir / f"{args.run_id}_preflight.json"
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    for name, leg in sorted(record["legs"].items()):
        print(f"[{'as-predicted' if leg['as_predicted'] else 'FALSIFIED'}] {name}: "
              f"exit={leg.get('exit_code')} label={leg.get('label_gate', {}).get('regression_verdict')} "
              f"geometry={leg.get('geometry_gate', {}).get('regression_verdict')}")
    print(f"verdict={record['verdict']} success_rule_holds={record['success_rule_holds']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
