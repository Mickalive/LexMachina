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
  Every leg shells out to ACCEPTED entry points as subprocesses; nothing here
  re-derives a verdict.  TWO accepted label-side entry points are executed on
  every synthetic packet, because the accepted instrument set has two of them
  and a one-instrument envelope is a false admission claim (repair r1, audit
  CYCLE_39033797087 required fix M1):
    1. ``python -m evaluation.frozen_bars.run_bar_gates --adjudicate``
       (accepted 38971202786; its LABEL half is POPULATION-PINNED at 65 rows);
    2. ``python -m evaluation.frozen_bars.run_label_lineage_gate --adjudicate``
       (accepted 39020603510; its label reading is POPULATION-FREE over the
       three-frozen-qid lineage, blocking a lineage packet whose pooled support
       rate is strictly below the derived incumbent rate 5/65).
  Both readings are published side by side on every leg; neither overwrites the
  other; every can/cannot-block statement in the enforcement envelope is
  qualified by the instrument it was measured on.
* It never imports Product code, never uses the network, never re-runs the 174k
  suite, and opens the Product mount read-only.

FROZEN BEFORE EXECUTION
-----------------------
``results/evaluation/rebuild_preflight_39033797087/freeze/
FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json`` (commit 01a4780d).
Legs A-E, the success rule PREFLIGHT_COMPLETE and the claim ceiling were fixed
before any leg ran.  The freeze file is PRESERVED BYTE-UNCHANGED; the repair
erratum ``FREEZE_ERRATA_39033797087_REPAIR_R1.json`` in the same directory
records (a) the ADDITIVE pins for the sibling lineage instrument, (b) the
withdrawal of the rejected cycle report's misstatement of the frozen leg-E
prediction, and (c) the scoping of the freeze's own claim-ceiling phrase
"population-pinned label bar" to the run_bar_gates LABEL half alone.  No
prediction, success rule, threshold, bar or incumbent is edited.  The sha256 of
every pinned instrument (original plus additive) is re-hashed after execution
and compared; a mismatch fails the record.

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
LINEAGE_GATE = [sys.executable, "-m", "evaluation.frozen_bars.run_label_lineage_gate"]
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
SERVED_QUESTIONS = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/38839347028/questions"
)

#: sha256 of every frozen input, copied verbatim from the frozen hypothesis.
#: Re-hashed after execution; a mismatch is an environment error, not a result.
#: This set is EXACTLY the freeze's instrument_pins_sha256 (the freeze file is
#: preserved byte-unchanged; see FREEZE_ERRATA_39033797087_REPAIR_R1.json).
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

#: ADDITIVE pins for the accepted sibling label instrument (repair r1, audit
#: required fix M1).  These three files are the accepted population-free
#: counter-label lineage gate and its verdict contract, accepted in cycle
#: 39020603510.  They are added to this module's re-hash set so the two-bar
#: envelope can never silently rest on a drifted sibling; NO original pin is
#: removed, changed or weakened, and no frozen file is written by this module.
LINEAGE_INSTRUMENT_PINS = {
    "evaluation/frozen_bars/label_lineage_gate.py":
        "754fdd11172f1468e18b7c43a3f745b92406e401a3290a4e1c7ed3c853d0a25b",
    "evaluation/frozen_bars/run_label_lineage_gate.py":
        "c9f4d6e1c9c0f9a0a8348d37d3e7d51d32f3b7ddffcb88906230bae83e419d12",
    "evaluation/frozen_bars/LABEL_LINEAGE_VERDICT.json":
        "016bffe5914ffc9074c948c9e452d05c79639735ed32f6c82aefd3751afcca18",
}

#: Accepted evidence, cited rather than re-derived (repair r1, M1).  The
#: population-free lineage gate blocking an off-incumbent-population lineage
#: packet is an ACCEPTED finding of cycle 39020603510, not a new claim of this
#: preflight; the live readings below are a consistency measurement of the
#: accepted instrument on synthetic packets, executed under that gate's own
#: accepted freeze FROZEN_HYPOTHESIS_39020603510.json.
ACCEPTED_TWO_BAR_EVIDENCE = {
    "source": "results/evaluation/label_lineage_gate/39020603510_sweep.json",
    "accepted_run_id": "39020603510",
    "accepted_gate_of_record":
        "results/audit/evaluation/CYCLE_39020603510_GATE.json (gate=PASS, safe_to_integrate=true)",
    "packet_id": "38799024807",
    "n_scored": 7,
    "n_supported": 0,
    "support_rate": 0.0,
    "lineage_gate": {"regression_verdict": "FAIL_REGRESSION", "gate_blocks_build": True},
    "accepted_label_gate_run_bar_gates":
        {"regression_verdict": "NOT_APPLICABLE", "gate_blocks_build": False},
    "parity": {"readings_disagree_on_this_packet": True,
               "label_geometry_parity_achieved": True},
    "cited_not_rederived": (
        "the divergence between the two accepted label-side instruments on an "
        "off-incumbent-population lineage packet is measured and accepted in that "
        "sweep; this preflight cites it and does not re-derive it as a new finding"),
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


def all_pins_match(rehash: dict) -> bool:
    """True when every instrument pin in every block of a re-hash matches."""
    return all(v["matches"] for block in rehash.values() if isinstance(block, dict)
               for v in block.values())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rehash_frozen_inputs() -> dict:
    """Compare every pinned frozen input with its recorded sha256.

    Covers BOTH the original freeze pins (``FROZEN_INPUTS``) and the additive
    sibling-lineage pins (``LINEAGE_INSTRUMENT_PINS``).  The two blocks are
    returned separately so the record can never blur which set a hash came
    from (repair r1, M1: an instrument-unqualified envelope is the defect class
    this repair exists to remove).
    """
    out: dict[str, dict] = {"freeze_pinned_instruments": {}, "additive_lineage_instruments": {}}
    for block, pins in (("freeze_pinned_instruments", FROZEN_INPUTS),
                        ("additive_lineage_instruments", LINEAGE_INSTRUMENT_PINS)):
        for rel, expected in sorted(pins.items()):
            p = _LANE_ROOT / rel
            observed = sha256_file(p) if p.is_file() else None
            out[block][rel] = {
                "expected_sha256": expected,
                "observed_sha256": observed,
                "matches": bool(observed == expected),
            }
    return out


def _load(qid: str, served: Path = SERVED_QUESTIONS) -> dict:
    path = served / f"{qid}.bundle.json"
    if not path.is_file():
        raise EnvironmentError_(f"served bundle missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def counter_rows(bundle: dict) -> list[dict]:
    """Decisions with ANY issued counter status.

    DISCLOSED PRECISION (repair r1): this is a SUPERSET of the frozen label
    scorer's scored-row population.  The frozen rubric scores only the four
    statuses in ``label_lineage_gate.SCORED_STATUSES``
    (candidate-limiting / candidate-contrary / contrary_or_exception /
    limiting); the served packet also carries 11 rows with status ``cited``,
    which are issued but not scored.  On the served packet this predicate
    returns 76 rows while the accepted gate's authoritative ``n_scored`` is 65.
    The two are never conflated: every ``n_scored`` in this module's records is
    read from the ACCEPTED entry point's own record, never computed here.  The
    predicate is kept as-is because the frozen leg constructions (freeze
    legs_frozen A-E) were defined over it and changing it would change the
    experiment post-freeze.
    """
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


def run_lineage_adjudicate(packet_dir: Path, out: Path, workdir: Path,
                           expect_record: bool = True) -> dict:
    """Invoke the ACCEPTED population-free lineage entry point on the same packet.

    ``python -m evaluation.frozen_bars.run_label_lineage_gate --adjudicate``
    (accepted cycle 39020603510) is the SECOND accepted label-side instrument.
    It emits its own two-bar admission input (label-lineage OR accepted geometry
    blocks) and always writes a record when ``--out`` is given, including on the
    off-lineage and environment-error paths, which it distinguishes explicitly.
    ``expect_record=False`` is retained for symmetry with ``run_adjudicate`` and
    is used only where "no record, non-zero exit" is itself the observation.
    """
    t0 = time.time()
    proc = subprocess.run(
        LINEAGE_GATE + ["--adjudicate", str(packet_dir), "--out", str(out)],
        cwd=str(_LANE_ROOT), capture_output=True, text=True, timeout=900)
    elapsed = round(time.time() - t0, 3)
    if not out.is_file():
        if expect_record:
            raise EnvironmentError_(
                f"accepted lineage entry point emitted no record (rc={proc.returncode}): "
                f"{proc.stderr.strip()[:300]}")
        return {
            "command": "python -m evaluation.frozen_bars.run_label_lineage_gate "
                       "--adjudicate <packet-dir>",
            "packet_dir": str(packet_dir),
            "exit_code": proc.returncode,
            "elapsed_s": elapsed,
            "record_written": False,
            "stderr": proc.stderr.strip()[:400],
        }
    rec = json.loads(out.read_text(encoding="utf-8"))
    (workdir / f"{out.stem}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    (workdir / f"{out.stem}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    lg = rec.get("label_lineage_gate") or {}
    admission = rec.get("admission_input") or {}
    acc_label = rec.get("accepted_label_gate_side_by_side") or {}
    geom = rec.get("accepted_geometry_gate") or {}
    return {
        "command": "python -m evaluation.frozen_bars.run_label_lineage_gate "
                   "--adjudicate <packet-dir>",
        "packet_dir": str(packet_dir),
        "exit_code": rec.get("exit_code", proc.returncode),
        "elapsed_s": elapsed,
        "record_path": str(out),
        "verdict": rec.get("verdict"),
        "verdict_scope": rec.get("verdict_scope"),
        "off_lineage": rec.get("off_lineage"),
        "n_frozen_qids_present": rec.get("n_frozen_qids_present"),
        "detail": rec.get("detail"),
        "label_lineage_gate": {k: lg.get(k) for k in (
            "n_scored", "n_supported", "support_rate", "classes", "incumbent",
            "lineage_matches_frozen_qid_set", "regression_verdict", "gate_blocks_build",
            "is_pass", "absolute_status")},
        "accepted_label_gate_side_by_side": acc_label,
        "accepted_geometry_gate": {k: geom.get(k) for k in (
            "per_bundle_counts", "regression_verdict", "gate_blocks_build",
            "absolute_status", "n_bundles_pass_all_11")},
        "admission_input": {k: admission.get(k) for k in (
            "blocks_build", "block_reasons", "label_regression_verdict",
            "label_support_rate", "label_enforced_predicate_rate", "label_absolute_status",
            "geometry_regression_verdict", "absolute_bars_enforced")},
    }


# --------------------------------------------------------------------------- #
# leg constructions (synthetic packets only; the mount is read-only)
# --------------------------------------------------------------------------- #
def leg_a_identity(served: Path, tmp: Path) -> dict:
    bundles = {qid: _load(qid, served) for qid in QIDS}
    d = write_packet(tmp / "leg_A_identity", bundles)
    res = run_adjudicate(d, tmp / "leg_A_identity.record.json", tmp)
    res["lineage_instrument"] = run_lineage_adjudicate(
        d, tmp / "leg_A_identity.lineage.record.json", tmp)
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
    res["lineage_instrument"] = run_lineage_adjudicate(
        d, tmp / "leg_B_plus_one.lineage.record.json", tmp)
    res["leg"] = "B_population_plus_one"
    res["injected_into"] = target
    res["n_counter_rows_constructed"] = {q: len(counter_rows(b)) for q, b in bundles.items()}
    res["prediction"] = ("observed sha differs for that anchor; label regression_verdict "
                         "NOT_APPLICABLE and gate_blocks_build=false (predicted vacuity); "
                         "absolute_status still REPORTED; the adjudicate negative control "
                         "reports not_applicable_reason; overall exit 0")
    label = res["label_gate"]
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
    res["lineage_instrument"] = run_lineage_adjudicate(
        d, tmp / "leg_C_blanked.lineage.record.json", tmp)
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
    lin = leg_b.get("lineage_instrument") or {}
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
        # ADDITIVE (repair r1, M1): the second accepted instrument's reading of the
        # same changed population, published beside the run_bar_gates reading.  This
        # is a measurement of an already-accepted instrument, not a new prediction of
        # this preflight's freeze.
        "lineage_instrument_on_same_population": {
            "verdict": lin.get("verdict"),
            "exit_code": lin.get("exit_code"),
            "label_lineage_regression_verdict":
                (lin.get("label_lineage_gate") or {}).get("regression_verdict"),
            "label_lineage_gate_blocks_build":
                (lin.get("label_lineage_gate") or {}).get("gate_blocks_build"),
            "n_scored": (lin.get("label_lineage_gate") or {}).get("n_scored"),
            "n_supported": (lin.get("label_lineage_gate") or {}).get("n_supported"),
            "support_rate": (lin.get("label_lineage_gate") or {}).get("support_rate"),
            "admission_blocks_build": (lin.get("admission_input") or {}).get("blocks_build"),
            "admission_block_reasons": (lin.get("admission_input") or {}).get("block_reasons"),
        },
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
    """Negative control: the entry point must never answer 'fine' on a bad input.

    Both accepted label-side entry points are run on both sub-packets.  The FROZEN
    prediction under test is about the run_bar_gates entry point's exit codes and
    is evaluated on those exit codes only; the lineage instrument's exits are
    published beside them and are NOT silently substituted into the prediction
    (repair r1, M3: the frozen wording is quoted verbatim below and the rejected
    cycle report's parenthetical restatement is withdrawn by the freeze erratum).
    """
    empty = tmp / "leg_E_empty"
    empty.mkdir(parents=True, exist_ok=True)
    r_empty = run_adjudicate(empty, tmp / "leg_E_empty.record.json", tmp,
                             expect_record=False)
    r_empty_lin = run_lineage_adjudicate(empty, tmp / "leg_E_empty.lineage.record.json", tmp)

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
    r_zero_lin = run_lineage_adjudicate(d, tmp / "leg_E_zero_rows.lineage.record.json", tmp)

    res = {
        "leg": "E_refusal_negative_control",
        # VERBATIM from results/evaluation/rebuild_preflight_39033797087/freeze/
        # FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json -> legs_frozen[4].prediction.
        # Quoted, never paraphrased, never restated post hoc (repair r1, M3).
        "prediction": ("both exits are non-zero (2 environment error or 1 regression) and "
                       "neither record may be consumed as a pass; a missing input must never "
                       "produce exit 0"),
        "prediction_scope": ("the two run_bar_gates --adjudicate exit codes of this leg's two "
                             "sub-packets; the accepted lineage entry point's exits on the same "
                             "sub-packets are published below as ADDITIVE readings and are not "
                             "part of the frozen pass condition"),
        "empty_packet_dir": {"exit_code": r_empty["exit_code"],
                             "record_written": r_empty.get("record_written", False),
                             "stderr": r_empty.get("stderr", ""),
                             "verdict": r_empty.get("verdict")},
        "empty_packet_dir_lineage_instrument": {
            "exit_code": r_empty_lin.get("exit_code"),
            "verdict": r_empty_lin.get("verdict"),
            "detail": r_empty_lin.get("detail"),
        },
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
        "zero_counter_rows_lineage_instrument": {
            "exit_code": r_zero_lin.get("exit_code"),
            "verdict": r_zero_lin.get("verdict"),
            "label_lineage_regression_verdict":
                (r_zero_lin.get("label_lineage_gate") or {}).get("regression_verdict"),
            "label_lineage_gate_blocks_build":
                (r_zero_lin.get("label_lineage_gate") or {}).get("gate_blocks_build"),
            "n_scored": (r_zero_lin.get("label_lineage_gate") or {}).get("n_scored"),
            "n_supported": (r_zero_lin.get("label_lineage_gate") or {}).get("n_supported"),
            "admission_blocks_build": (r_zero_lin.get("admission_input") or {}).get("blocks_build"),
        },
        "exit_codes": [r_empty["exit_code"], r_zero["exit_code"]],
        "exit_codes_lineage_instrument":
            [r_empty_lin.get("exit_code"), r_zero_lin.get("exit_code")],
    }
    res["as_predicted"] = bool(all(code != 0 for code in res["exit_codes"]))
    return res


def build_record(run_id: str, legs: dict, frozen_rehash: dict, envelope: dict) -> dict:
    a_ok = legs["A_identity_control"]["as_predicted"]
    c_ok = legs["C_preserved_population_blanked_evidence"]["as_predicted"]
    e_ok = legs["E_refusal_negative_control"]["as_predicted"]
    sha_ok = all_pins_match(frozen_rehash)
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
    lin_b = (legs["B_population_plus_one"].get("lineage_instrument")
             or {}).get("label_lineage_gate") or {}
    lin_e_zero = legs["E_refusal_negative_control"].get(
        "zero_counter_rows_lineage_instrument") or {}
    headline = [
        {"id": "PF1_run_bar_gates_label_enforcement_is_population_pinned",
         "measured_on": "B_population_plus_one",
         "instrument": "run_bar_gates LABEL half (accepted 38971202786)",
         "statement": ("INSTRUMENT-QUALIFIED (repair r1, M1): under the accepted run_bar_gates "
                       "LABEL half, on a packet whose scored counter-row count differs from "
                       "the pinned 65, the gate emits regression_verdict=NOT_APPLICABLE and "
                       "gate_blocks_build=false, i.e. that half's ENFORCED verdict is vacuous "
                       "off the incumbent population; the absolute status is still reported. "
                       "This statement is NOT a property of the accepted label-side "
                       "instrument set as a whole: see PF5."),
         "predicted_before_execution": True,
         "prediction_source": "frozen hypothesis H-PREFLIGHT"},
        {"id": "PF2_geometry_enforcement_is_qid_pinned",
         "measured_on": "D_geometry_still_enforcing_on_changed_population",
         "instrument": "run_bar_gates geometry half (accepted 38971202786)",
         "statement": "the geometry gate keeps emitting an enforcing PASS/FAIL verdict on the "
                      "same changed population because its lineage predicate pins the qid set "
                      "only; the two frozen bars therefore enforce on different conditions",
         "predicted_before_execution": True,
         "prediction_source": "frozen hypothesis H-PREFLIGHT"},
        {"id": "PF3_zero_counter_population_is_not_blocked",
         "measured_on": "E_refusal_negative_control",
         "instrument": "both accepted label-side instruments",
         "statement": ("a packet that issues NO counter label at all is adjudicated with "
                       "exit 0 by the run_bar_gates entry point (n_scored=0 makes its label "
                       "regression verdict NOT_APPLICABLE and the absolute status "
                       "LABEL_UNSOUND, which is REPORTED and never enforced) and with "
                       f"exit {lin_e_zero.get('exit_code')} / record-level verdict "
                       f"{lin_e_zero.get('verdict')!r} by the accepted lineage entry point, "
                       "whose own label gate is in state NOT_MEASURED (neither a pass nor a "
                       "block; LABEL_LINEAGE_VERDICT.json: NOT_MEASURED certifies NOTHING). "
                       "NEITHER instrument certifies such a packet as sound; the lineage "
                       "entry point's record-level PASS_NO_REGRESSION string on it is an "
                       "aggregation artefact of gate_blocks_build, not a label pass, and is "
                       "disclosed as a naive-consumer trap rather than hidden. Publishing "
                       "support-among-issued with the abstention count and the yield is "
                       "therefore load-bearing for the rebuild decision, not a nicety"),
         "predicted_before_execution": False,
         "prediction_source": ("frozen hypothesis leg E predicted BOTH run_bar_gates exits "
                               "non-zero (2 environment error or 1 regression) and neither "
                               "record consumable as a pass; a missing input must never "
                               "produce exit 0 — MEASURED exit_codes [2, 0], so the frozen "
                               "prediction is FALSIFIED and this finding is published as a "
                               "falsification with its wording correction, per the freeze's "
                               "own success-rule clause")},
        {"id": "PF4_the_accepted_record_does_not_publish_applicability",
         "measured_on": "A_identity_control",
         "corroborated_on": "B_population_plus_one",
         "instrument": "run_bar_gates (both halves)",
         "statement": "run_bar_gates' record exposes no lineage/lineage_matches_incumbent "
                      "boolean for either gate; a consumer can only infer whether the "
                      "enforced verdict was applicable at all from the verdict STRING. "
                      "Direction item (2) requires the per-anchor enforced verdict to be "
                      "published, so NOT_APPLICABLE must be rendered explicitly and never "
                      "collapsed into a pass",
         "predicted_before_execution": False,
         "prediction_source": "field survey of the accepted record schema"},
        {"id": "PF5_the_two_bar_label_envelope_is_wider_than_the_population_pinned_half",
         "measured_on": "B_population_plus_one",
         "corroborated_on": ["C_preserved_population_blanked_evidence",
                             "accepted packet 38799024807 (cited, not re-derived)"],
         "instrument": "label_lineage_gate (accepted 39020603510)",
         "statement": ("INSTRUMENT-QUALIFIED (repair r1, M1): the accepted population-free "
                       "label_lineage_gate BLOCKS the very population the rejected cycle "
                       "declared unblockable. Live: leg B (n_scored=66, n_supported=5, "
                       f"rate {lin_b.get('support_rate')}) -> "
                       f"{lin_b.get('regression_verdict')} / gate_blocks_build "
                       f"{lin_b.get('gate_blocks_build')}, while the run_bar_gates LABEL half "
                       "on the same bytes is NOT_APPLICABLE / blocks false. Accepted "
                       "evidence (cited): 39020603510_sweep.json packet 38799024807 "
                       "(n_scored=7, n_supported=0): lineage FAIL_REGRESSION blocks true, "
                       "run_bar_gates LABEL half NOT_APPLICABLE blocks false."),
         "predicted_before_execution": False,
         "prediction_source": ("ADDITIVE reading of an already-accepted instrument under its "
                               "own accepted freeze FROZEN_HYPOTHESIS_39020603510.json; the "
                               "preflight freeze made no prediction about it and none is "
                               "invented here")},
    ]
    predicted = [k for k, v in legs.items() if v.get("as_predicted")]
    falsified = [k for k, v in legs.items() if not v.get("as_predicted")]
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": 52,
        "repair_round": 1,
        "repairs_cycle": "39033797087",
        "instruments": [
            "python -m evaluation.frozen_bars.run_bar_gates --adjudicate <packet-dir>",
            "python -m evaluation.frozen_bars.run_label_lineage_gate --adjudicate <packet-dir>",
        ],
        "instrument": ("two accepted entry points, both executed on every synthetic packet and "
                       "published side by side: run_bar_gates --adjudicate (accepted 38971202786; "
                       "its LABEL half is population-pinned at 65 rows) and "
                       "run_label_lineage_gate --adjudicate (accepted 39020603510; population-free "
                       "rate predicate over the three-frozen-qid lineage). See repair r1 audit "
                       "CYCLE_39033797087 required fix M1."),
        "frozen_hypothesis": (
            "results/evaluation/rebuild_preflight_39033797087/freeze/"
            "FROZEN_HYPOTHESIS_REBUILD_PREFLIGHT_39033797087.json"),
        "freeze_erratum": (
            "results/evaluation/rebuild_preflight_39033797087/freeze/"
            "FREEZE_ERRATA_39033797087_REPAIR_R1.json"),
        "frozen_before_execution_commit": "01a4780d",
        "freeze_file_byte_unchanged": True,
        "served_bytes_source": str(SERVED_QUESTIONS),
        "served_bytes_modified": False,
        "legs": legs,
        "frozen_input_rehash_after_execution": frozen_rehash,
        "enforcement_envelope": envelope,
        "accepted_evidence_cited_not_rederived": ACCEPTED_TWO_BAR_EVIDENCE,
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
            "At most, and only as the two-bar envelope measured here: the direction's successor "
            "adjudication command is executable end to end today, and its ENFORCED verdict on a "
            "rebuilt packet is the measured TWO-BAR envelope — the accepted run_bar_gates LABEL "
            "half blocks only on the exact 65-row incumbent population, while the accepted "
            "population-free label_lineage_gate DOES block a three-frozen-qid lineage packet "
            "whose pooled support rate is strictly below the derived incumbent rate 5/65 even "
            "when its scored counter-row count differs from 65; a packet that issues NO scored "
            "counter row at all is blocked by NEITHER label instrument (NOT_APPLICABLE / "
            "NOT_MEASURED) and is certified sound by NEITHER. No real rebuilt packet was "
            "adjudicated; nothing is served, un-served or admitted; no decision is asserted to "
            "be supporting/contrary/limiting; the standing accepted DO-NOT-SERVE order on "
            "packet 38839347028 is untouched; human_gate_ready stays false."),
    }


def envelope_from_legs(legs: dict) -> dict:
    """The product-facing reading: what can actually BLOCK a rebuilt packet.

    REPAIR R1 (audit CYCLE_39033797087 required fix M1): every statement here is
    QUALIFIED BY THE INSTRUMENT it was measured on.  The accepted label-side
    instrument set has TWO entry points and the rejected cycle published one of
    them as if it were the whole envelope.  The corrected two-bar label envelope
    is:
      * the accepted ``run_bar_gates`` LABEL half is POPULATION-PINNED at 65
        scored counter rows and goes NOT_APPLICABLE (never blocks) off that
        population;
      * the accepted population-free ``label_lineage_gate`` BLOCKS a lineage
        packet (the three frozen qids) whose pooled support rate is strictly
        below the derived incumbent rate 5/65, whatever its scored-row count,
        and returns NOT_MEASURED (neither pass nor block) when there are no
        scored rows at all.
    The divergence is accepted evidence of cycle 39020603510 on real packet
    38799024807 (n_scored=7, n_supported=0: lineage FAIL_REGRESSION blocks,
    run_bar_gates label half NOT_APPLICABLE does not) and is CITED, not
    re-derived; the live readings below are this preflight's measurement of the
    same two accepted instruments on synthetic packets.
    """
    a, b, c, e = (legs["A_identity_control"], legs["B_population_plus_one"],
                  legs["C_preserved_population_blanked_evidence"],
                  legs["E_refusal_negative_control"])
    lin_b = (b.get("lineage_instrument") or {}).get("label_lineage_gate") or {}
    lin_b_adm = (b.get("lineage_instrument") or {}).get("admission_input") or {}
    lin_c = (c.get("lineage_instrument") or {}).get("label_lineage_gate") or {}
    lin_a = (a.get("lineage_instrument") or {}).get("label_lineage_gate") or {}
    lin_e_zero = e.get("zero_counter_rows_lineage_instrument") or {}
    lin_e_empty = e.get("empty_packet_dir_lineage_instrument") or {}
    return {
        "instruments_measured": {
            "run_bar_gates_label_half":
                "python -m evaluation.frozen_bars.run_bar_gates --adjudicate "
                "(accepted 38971202786; LABEL half population-pinned at 65 rows)",
            "label_lineage_gate":
                "python -m evaluation.frozen_bars.run_label_lineage_gate --adjudicate "
                "(accepted 39020603510; population-free rate predicate over the three "
                "frozen qids; blocks when pooled support_rate < 5/65 with n_scored > 0)",
            "run_bar_gates_geometry_half":
                "the geometry half of run_bar_gates --adjudicate (qid-set lineage, no "
                "population pin)",
        },
        "label_bar_run_bar_gates_population_pinned": {
            "instrument": "run_bar_gates LABEL half",
            "enforces_when": ("the rebuilt packet issues EXACTLY the three frozen anchor "
                              "qids AND exactly the incumbent scored population (65 rows)"),
            "vacuous_when": ("the rebuilt packet's scored counter-row count differs from 65 "
                             "(regression_verdict NOT_APPLICABLE, gate_blocks_build false)"),
            "measured_on": {
                "preserved_population_blanked_evidence": {
                    "exit_code": c["exit_code"],
                    "n_scored": c["label_gate"]["n_scored"],
                    "n_supported": c["label_gate"]["n_supported"],
                    "support_rate": c["label_gate"]["support_rate"],
                    "regression_verdict": c["label_gate"]["regression_verdict"],
                    "gate_blocks_build": c["label_gate"]["gate_blocks_build"]},
                "population_plus_one": {
                    "exit_code": b["exit_code"],
                    "n_scored": b["label_gate"]["n_scored"],
                    "n_supported": b["label_gate"]["n_supported"],
                    "support_rate": b["label_gate"]["support_rate"],
                    "regression_verdict": b["label_gate"]["regression_verdict"],
                    "gate_blocks_build": b["label_gate"]["gate_blocks_build"],
                    "absolute_status_reported": b["label_gate"]["absolute_status"]},
                "identity_control": {
                    "n_scored": a["label_gate"]["n_scored"],
                    "n_supported": a["label_gate"]["n_supported"],
                    "regression_verdict": a["label_gate"]["regression_verdict"],
                    "gate_blocks_build": a["label_gate"]["gate_blocks_build"]},
            },
            "absolute_status_is_never_enforced": True,
        },
        "label_bar_label_lineage_gate_population_free": {
            "instrument": "label_lineage_gate (accepted 39020603510)",
            "predicate": ("lineage := set(bundles) == the three frozen qids; FAIL_REGRESSION "
                          ":= lineage AND n_scored > 0 AND support_rate < 5/65 (strict; the "
                          "rate is derived at runtime from the accepted incumbent 5/65)"),
            "enforces_when": ("the rebuilt packet carries the three frozen anchor qids AND "
                              "issues at least one scored counter row whose pooled support "
                              "rate is strictly below 5/65"),
            "not_measured_when": ("the rebuilt packet carries the three frozen anchor qids "
                                  "but issues NO scored counter row (NOT_MEASURED: neither a "
                                  "pass nor a block; it certifies nothing)"),
            "measured_on": {
                "population_plus_one": {
                    "exit_code": (b.get("lineage_instrument") or {}).get("exit_code"),
                    "n_scored": lin_b.get("n_scored"),
                    "n_supported": lin_b.get("n_supported"),
                    "support_rate": lin_b.get("support_rate"),
                    "regression_verdict": lin_b.get("regression_verdict"),
                    "gate_blocks_build": lin_b.get("gate_blocks_build"),
                    "admission_blocks_build": lin_b_adm.get("blocks_build"),
                    "admission_block_reasons": lin_b_adm.get("block_reasons")},
                "preserved_population_blanked_evidence": {
                    "exit_code": (c.get("lineage_instrument") or {}).get("exit_code"),
                    "n_scored": lin_c.get("n_scored"),
                    "n_supported": lin_c.get("n_supported"),
                    "support_rate": lin_c.get("support_rate"),
                    "regression_verdict": lin_c.get("regression_verdict"),
                    "gate_blocks_build": lin_c.get("gate_blocks_build")},
                "identity_control": {
                    "n_scored": lin_a.get("n_scored"),
                    "n_supported": lin_a.get("n_supported"),
                    "support_rate": lin_a.get("support_rate"),
                    "regression_verdict": lin_a.get("regression_verdict"),
                    "gate_blocks_build": lin_a.get("gate_blocks_build")},
                "zero_counter_rows": lin_e_zero,
                "empty_packet_dir": lin_e_empty,
            },
            "absolute_status_is_never_enforced": True,
        },
        "geometry_bar": {
            "instrument": "run_bar_gates geometry half",
            "enforces_when": ("the rebuilt packet carries the three frozen anchor qids "
                              "(lineage is pinned on the qid set only, not on population "
                              "size)"),
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
        "accepted_evidence_cited_not_rederived": ACCEPTED_TWO_BAR_EVIDENCE,
        "what_a_rebuilt_packet_cannot_be_blocked_on": [
            {"statement": "counter-label support at the frozen 1.0 absolute bar "
                          "(REPORTED, never enforced)",
             "qualified_by_instrument": "both accepted label-side instruments "
                                        "(run_bar_gates LABEL half and label_lineage_gate)"},
            {"statement": ("a label regression once its scored counter-row count differs "
                           "from 65 — ONLY under the accepted run_bar_gates LABEL half "
                           "alone; this is NOT a property of the two-bar label enforcement"),
             "qualified_by_instrument": "run_bar_gates LABEL half ONLY",
             "correction_of_record": (
                 "the rejected cycle 39033797087 published this statement UNQUALIFIED as "
                 "the whole enforcement envelope. That is false: the accepted population-free "
                 "label_lineage_gate DOES block a lineage packet whose pooled support rate is "
                 "strictly below the derived incumbent rate 5/65 even when its scored "
                 "counter-row count differs from 65. Accepted evidence: "
                 "results/evaluation/label_lineage_gate/39020603510_sweep.json, packet "
                 "38799024807 (n_scored=7 != 65, n_supported=0, rate 0.0): lineage gate "
                 "FAIL_REGRESSION / gate_blocks_build true, run_bar_gates LABEL half "
                 "NOT_APPLICABLE / gate_blocks_build false, readings_disagree_on_this_packet "
                 "true. Live consistency measurement this cycle: leg B_population_plus_one "
                 "(n_scored=66, n_supported=5, rate 5/66 = 0.07576 < 5/65 = 0.07692) is "
                 "blocked by the lineage gate and is NOT blocked by the run_bar_gates LABEL "
                 "half — the exact population the rejected cycle declared unblockable.")},
            {"statement": ("a packet that issues NO scored counter row at all: neither "
                           "accepted label-side instrument blocks it (run_bar_gates LABEL "
                           "half NOT_APPLICABLE; label_lineage_gate NOT_MEASURED), and "
                           "NEITHER certifies it as sound — a NOT_APPLICABLE or NOT_MEASURED "
                           "verdict is never a pass (LABEL_LINEAGE_VERDICT.json: "
                           "NOT_MEASURED 'certifies NOTHING. It is an absence of "
                           "measurement, not a pass'; gate_blocks_build == false 'is NOT a "
                           "statement that the counter-label bar was met')"),
             "qualified_by_instrument": "both accepted label-side instruments "
                                        "(measured on leg E_refusal_negative_control)",
             "naive_consumer_disclosure": ("the accepted lineage entry point's RECORD-LEVEL "
                                           "two-bar verdict on the zero-counter-row packet is "
                                           "PASS_NO_REGRESSION with exit 0, because the "
                                           "record-level verdict aggregates only "
                                           "gate_blocks_build (FAIL_REGRESSION if EITHER bar "
                                           "blocks, else PASS_NO_REGRESSION) while its own "
                                           "label gate is in state NOT_MEASURED. A consumer "
                                           "that reads only the record-level verdict string "
                                           "or the exit code would misread an absence of "
                                           "measurement as a pass. This is the same "
                                           "naive-consumer-trap class the accepted "
                                           "LABEL_LINEAGE_VERDICT.json exists to prevent, and "
                                           "it is disclosed here rather than hidden; it is a "
                                           "property of the ACCEPTED instrument's aggregation "
                                           "and is NOT changed, patched or re-frozen by this "
                                           "preflight.")},
        ],
        "what_a_rebuilt_packet_can_be_blocked_on": [
            {"statement": ("a counter-label support-rate regression on a three-frozen-qid "
                           "lineage packet with at least one scored counter row and pooled "
                           "support rate strictly below 5/65"),
             "qualified_by_instrument": "label_lineage_gate (accepted 39020603510)",
             "measured_live_on": ["leg_B_population_plus_one (5/66 = 0.07576 < 0.07692 -> "
                                  "FAIL_REGRESSION, blocks)",
                                  "leg_C_preserved_population_blanked_evidence "
                                  "(0/65 = 0.0 < 0.07692 -> FAIL_REGRESSION, blocks)"]},
            {"statement": ("a counter-label support regression on the EXACT 65-row incumbent "
                           "population"),
             "qualified_by_instrument": "run_bar_gates LABEL half (accepted 38971202786)",
             "measured_live_on": ["leg_C_preserved_population_blanked_evidence "
                                  "(0/65 -> FAIL_REGRESSION, blocks)"]},
            {"statement": ("a geometry criterion-count regression below de 6 / fr 5 / it 5 "
                           "on the three anchors"),
             "qualified_by_instrument": "run_bar_gates geometry half",
             "measured_live_on": []},
            {"statement": "the packet-admission conformance battery "
                          "(a separate accepted instrument)",
             "qualified_by_instrument": "evaluation.packet_admission_conformance",
             "measured_live_on": []},
        ],
        "incumbent_reference": {"n_scored": a["label_gate"]["n_scored"],
                                "n_supported": a["label_gate"]["n_supported"],
                                "geometry": a["geometry_gate"]["per_bundle_counts"],
                                "lineage_predicate_rate":
                                    lin_a.get("incumbent") and
                                    (a["label_gate"]["n_supported"]
                                     / a["label_gate"]["n_scored"])},
        "two_bar_label_divergence_measured_this_cycle": {
            "population_plus_one": {
                "run_bar_gates_label_half_blocks": b["label_gate"]["gate_blocks_build"],
                "label_lineage_gate_blocks": lin_b.get("gate_blocks_build"),
                "readings_disagree": bool(b["label_gate"]["gate_blocks_build"]
                                          != lin_b.get("gate_blocks_build"))},
            "preserved_population_blanked_evidence": {
                "run_bar_gates_label_half_blocks": c["label_gate"]["gate_blocks_build"],
                "label_lineage_gate_blocks": lin_c.get("gate_blocks_build"),
                "readings_disagree": bool(c["label_gate"]["gate_blocks_build"]
                                          != lin_c.get("gate_blocks_build"))},
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--served-questions", default=str(SERVED_QUESTIONS))
    ap.add_argument("--record-name", default=None,
                    help="name of the record file inside --out-dir; defaults to "
                         "<run-id>_preflight.json. A re-execution MUST name a fresh file: a "
                         "committed preflight record is claim-bearing history and is never "
                         "overwritten.")
    ap.add_argument("--allow-overwrite", action="store_true",
                    help="explicitly permit overwriting an existing record file (never used "
                         "for a claim-bearing committed record; retained only so a local "
                         "scratch re-run can be scripted without --record-name)")
    args = ap.parse_args(argv)

    served = Path(args.served_questions)
    if not served.is_dir():
        print("::error::no accepted Product mount; the preflight cannot measure", file=sys.stderr)
        return 2
    pre = rehash_frozen_inputs()
    if not all_pins_match(pre):
        print("::error::frozen instrument sha drift before execution", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else \
        _LANE_ROOT / "results" / "evaluation" / f"rebuild_preflight_{args.run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # A committed preflight record is claim-bearing history.  It is NEVER
    # overwritten (AGENTS.md non-negotiable: never overwrite claim-bearing
    # outputs); a re-execution must name its own record file.
    record_name = args.record_name or f"{args.run_id}_preflight.json"
    out = out_dir / record_name
    if out.exists() and not args.allow_overwrite:
        print(f"::error::refusing to overwrite claim-bearing record {out}; "
              f"pass --record-name <new-name>.json for a re-execution", file=sys.stderr)
        return 2

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

    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    for name, leg in sorted(record["legs"].items()):
        lin = leg.get("lineage_instrument") or {}
        print(f"[{'as-predicted' if leg['as_predicted'] else 'FALSIFIED'}] {name}: "
              f"exit={leg.get('exit_code')} label={leg.get('label_gate', {}).get('regression_verdict')} "
              f"geometry={leg.get('geometry_gate', {}).get('regression_verdict')} "
              f"| lineage_instrument verdict={lin.get('verdict')} "
              f"blocks={(lin.get('admission_input') or {}).get('blocks_build')}")
    print(f"verdict={record['verdict']} success_rule_holds={record['success_rule_holds']} "
          f"falsified_legs={record['success_rule_falsified_legs']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
