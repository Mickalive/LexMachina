#!/usr/bin/env python3
"""Disclosure-provenance cross-check (direction v61, FAST-MVP falsifier).

Run 39516448683.  Freeze-first hypothesis:
``evaluation/DISCLOSURE_PROVENANCE_CROSSCHECK_HYPOTHESIS_V1.json`` (sha
``e72973e0...``, freeze commit ``56a51aa2``).

Product's unaudited counter-instability disclosure (run 39422322667) is the
newest claim-bearing product artifact that transcribes Evaluation-owned
numbers (open items 5/6, P1/P1ext REPORTED-ONLY quantities) onto the
packet-of-record V3.  This instrument publishes the established
side-by-side cross-check pattern beside it: every quantity Product
publishes is placed beside THIS LANE's recomputation from Evaluation's own
committed evidence; any divergence is the headline.

What this instrument does, and ONLY this:

  1. Re-hashes the frozen hypothesis and every Evaluation-owned pin
     (sweep artifact, accepted-state at the pin commit, three frozen rubric
     files) before and after the run; a moved frozen input is an
     environment error, never a product verdict.
  2. Resolves the pin commit 50166b4c... (explicit ``git fetch --depth=1``
     when a shallow clone lacks it) and re-derives the accepted-state sha256
     and git blob oid Product publishes.
  3. Four-way verbatim-compares the two open-item texts: Product's
     disclosure, Product's vendored copy, origin/main's CURRENT
     accepted-state, and this lane's own state/evaluation.json.
  4. Re-derives every P1/P1ext structured quantity Product publishes from
     the sweep artifact of record (39322925971.json) at the frozen
     precision ladder, including the DE-UNTESTED and IT-NOT-MEASURED
     attribution claims and the FR counter-stage divergence block.
  5. Verifies the packet disclosure-layer placement (block beside the
     coverage-gap disclosure for all three V3 qids) and that the packet /
     bundle scored bytes never moved (V3 pins).
  6. Builds one side-by-side row per frozen quantity with match booleans;
     names every diverging row in the headline, or publishes
     ZERO_DIVERGENCE.  Freeze-time observation drift is always published
     with both digests, never silently accepted.
  7. Non-vacuity: four planted perturbations on scratch copies MUST each be
     detected (verdict NON_VACUOUS, exit 1, if not).

What this instrument NEVER does: re-derives, edits, re-tunes or paraphrases
a threshold/bar/rubric/incumbent/predicate/verdict contract; re-measures
P1/P1ext from run outputs (ordered work (4): the numbers are computed here
by no one twice - this instrument only verifies Product's transcription
against the artifact of record); imports Product or Frontier code; scores
any label or geometry bar; serves a packet; lifts a DO-NOT-SERVE order;
asks the owner anything.  The only network operation is the pin-commit
fetch.  No universal-174k benchmark is rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HYP_PATH = REPO / "evaluation/DISCLOSURE_PROVENANCE_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO / "evaluation/DISCLOSURE_PROVENANCE_CROSSCHECK_FREEZE_RECORD_V1.json"
SWEEP_PATH = REPO / "results/evaluation/cross_run_stability_sweep/39322925971.json"
STATE_PATH = REPO / "state/evaluation.json"
FROZEN_BARS = {
    "RULES_LABEL.json": REPO / "evaluation/frozen_bars/RULES_LABEL.json",
    "RULES_GEOMETRY.json": REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json",
    "VERDICT_CONTRACT.json": REPO / "evaluation/frozen_bars/VERDICT_CONTRACT.json",
}
OUT_DIR = REPO / "results/evaluation/disclosure_provenance_crosscheck"

RUN_ID = "39516448683"
PIN_COMMIT = "50166b4c5138117638430873cc43dc34b3168f2b"
ACCEPTED_STATE_PATH = "results/accepted-state/evaluation.json"
MAIN_REF = "origin/main"
ITEM5 = "item_5_fr_live_counter_run_instability_P1"
ITEM6 = "item_6_population_and_limiting_identity_movement_P1ext"

DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
PACKET_REL = Path("results/product/gate_packet/39319405429")
DISCLOSURE_REL = Path(
    "results/product/disclosures/CYCLE_39422322667_counter_instability_disclosure.json")
VENDORED_REL = Path(
    "product/data/eval_open_items/ACCEPTED_EVALUATION_OPEN_ITEMS_5_6.json")

DE_GROUP_NAME = "Kündigung Mietvertrag Mietrecht"
FR_GROUP_NAME = "Responsabilite penale de l'entreprise selon l'art. 102 CP"

HYP_SHA256 = "e72973e0cb3e4934048a18af63e7d9f0f6ae696dc96f185b53ca30e625d47e64"
SWEEP_SHA256 = "a287fbe26bbbb6c16e1163e07036474424db2126ab855218ee9738ccf7b71c0e"
PIN_STATE_SHA256 = "285b32cfbe3036269388358cc4264a655994505e4c2022bb468a3c3712423889"
PIN_STATE_BLOB = "a1336f0e5801f5e20fcb60ab7cd2d0c02a937752"
FROZEN_BAR_SHAS = {
    "RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
}
V3_PACKET_SHA = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
FROZEN_TEXT_SHAS = {
    ITEM5: "ab771b847c3524efdef8229f5453971dda5b51bf872992d5ac8f1fcae03c61d4",
    ITEM6: "fb26cf86389b6c7db80e43bad9b1c6531b4d476c503a0afc67a6fc34b5105157",
}
V3_BUNDLE_SHAS = {
    "de-kapitalverletzung":
        "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "fr-bail-entretien":
        "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "it-responsabilita-medica":
        "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}


class EnvironmentError_(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, timeout=90)


def item_text_sha(text: str) -> str:
    """sha256 of the `jq -r` byte convention: text + trailing newline."""
    return sha256_bytes((text if text.endswith("\n") else text + "\n")
                        .encode("utf-8"))


def ensure_pin_commit(commit: str) -> str:
    """Resolve the pin commit, fetching depth-1 if a shallow clone lacks it."""
    probe = _git("cat-file", "-e", f"{commit}^{{commit}}")
    if probe.returncode != 0:
        fetch = _git("fetch", "--depth=1", "origin", commit)
        if fetch.returncode != 0:
            raise EnvironmentError_(
                f"pin commit {commit} absent and unfetchable: "
                f"{(fetch.stderr or fetch.stdout)[:300]}")
        probe = _git("cat-file", "-e", f"{commit}^{{commit}}")
        if probe.returncode != 0:
            raise EnvironmentError_(
                f"pin commit {commit} still absent after explicit fetch")
        return "fetched_depth_1_this_run"
    return "already_present"


def accepted_state_at(commit: str) -> tuple[str, str]:
    show = _git("show", f"{commit}:{ACCEPTED_STATE_PATH}")
    if show.returncode != 0:
        raise EnvironmentError_(
            f"cannot read {ACCEPTED_STATE_PATH} at {commit}: "
            f"{(show.stderr or show.stdout)[:300]}")
    # git show text-mode would mangle bytes; re-read through cat-file instead
    cat = _git("cat-file", "blob", f"{commit}:{ACCEPTED_STATE_PATH}")
    if cat.returncode != 0:
        raise EnvironmentError_(f"cannot cat-file {ACCEPTED_STATE_PATH} at {commit}")
    blob = cat.stdout.encode("utf-8", errors="surrogateescape")
    rev = _git("rev-parse", f"{commit}:{ACCEPTED_STATE_PATH}")
    if rev.returncode != 0:
        raise EnvironmentError_(f"cannot rev-parse {ACCEPTED_STATE_PATH} at {commit}")
    return sha256_bytes(blob), rev.stdout.strip()


def accepted_state_current(ref: str) -> tuple[str, str, dict]:
    cat = _git("cat-file", "blob", f"{ref}:{ACCEPTED_STATE_PATH}")
    if cat.returncode != 0:
        raise EnvironmentError_(
            f"cannot read {ACCEPTED_STATE_PATH} at {ref}: "
            f"{(cat.stderr or cat.stdout)[:300]}")
    raw = cat.stdout.encode("utf-8", errors="surrogateescape")
    rev = _git("rev-parse", f"{ref}:{ACCEPTED_STATE_PATH}")
    if rev.returncode != 0:
        raise EnvironmentError_(f"cannot rev-parse {ACCEPTED_STATE_PATH} at {ref}")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnvironmentError_(f"current accepted-state is not valid JSON: {exc}")
    return sha256_bytes(raw), rev.stdout.strip(), doc


# --------------------------------------------------------------------------- #
# extraction of product-published values
# --------------------------------------------------------------------------- #

def extract_product(disclosure: dict, vendored: dict) -> dict:
    ev = disclosure.get("evidence_source") or {}
    per_q = {row.get("qid"): row for row in disclosure.get("per_question") or []}
    fr_row = (per_q.get("fr-bail-entretien") or {}).get(
        "counter_instability_disclosure") or {}
    de_row = (per_q.get("de-kapitalverletzung") or {}).get(
        "counter_instability_disclosure") or {}
    it_row = (per_q.get("it-responsabilita-medica") or {}).get(
        "counter_instability_disclosure") or {}
    return {
        "verbatim_open_items": ev.get("verbatim_open_items") or {},
        "vendored_open_items": vendored.get("open_items") or {},
        "file_sha256_at_pin": ev.get("file_sha256_at_pin"),
        "git_blob_oid_at_pin": ev.get("git_blob_oid_at_pin"),
        "pin_commit": ev.get("pin_commit"),
        "p1": fr_row.get("p1_counter_stage_divergence") or {},
        "p1ext": fr_row.get("p1ext_population_and_identity_movement") or {},
        "de_applies": de_row.get("applies_to_this_bundle_language") or {},
        "it_applies": it_row.get("applies_to_this_bundle_language") or {},
        "per_qids": sorted(per_q),
        "packet": disclosure.get("packet") or {},
        "per_question_blocks": per_q,
    }


# --------------------------------------------------------------------------- #
# lane recomputation from evaluation-owned evidence
# --------------------------------------------------------------------------- #

def recompute_sweep(sweep: dict) -> dict:
    groups = {g.get("group"): g for g in sweep.get("groups") or []}
    if DE_GROUP_NAME not in groups or FR_GROUP_NAME not in groups:
        raise EnvironmentError_("sweep artifact lacks the two named groups")
    de, fr = groups[DE_GROUP_NAME], groups[FR_GROUP_NAME]

    def ro(group):
        return (group.get("reported_only_diagnostics") or [{}])[0]

    de_ro, fr_ro = ro(de), ro(fr)
    de_legs = {leg.get("gate"): leg for leg in de.get("legs") or []}
    fr_legs = {leg.get("gate"): leg for leg in fr.get("legs") or []}
    fr_counter = fr_legs.get("sr::counter_authority_surface") or {}
    de_counter = de_legs.get("sr::counter_authority_surface") or {}
    per_run = fr_counter.get("per_run_measured") or {}
    runs = fr_counter.get("runs_compared") or []

    other_stable = True
    other_leg_names = []
    for legs in (de_legs, fr_legs):
        for name, leg in legs.items():
            if name == "sr::counter_authority_surface":
                continue
            status = leg.get("status")
            if status in (None, "NOT_APPLICABLE"):
                continue
            other_leg_names.append(f"{name}={status}")
            if status != "STABLE":
                other_stable = False

    answer_a = de_ro.get("answer_a") or {}
    answer_b = de_ro.get("answer_b") or {}
    # NOTE: the 6-vs-5 cited swap lives on the FR group in the artifact of
    # record; re-read from fr_ro as well and prefer whichever group carries
    # present answers (frozen rule: FR group, per the open-items text).
    fr_answer_a = fr_ro.get("answer_a") or {}
    fr_answer_b = fr_ro.get("answer_b") or {}

    return {
        "n_groups": (sweep.get("group_structure") or {}).get("n_groups"),
        "expected_n_groups": (sweep.get("group_structure") or {}).get(
            "expected_n_groups"),
        "expected_structure_keys": sorted(
            ((sweep.get("group_structure") or {}).get("expected_group_sizes")
             or (sweep.get("group_structure") or {}).get("group_sizes")
             or {}).keys()),
        "de": {
            "jaccard": de_ro.get("jaccard"),
            "rank_changed": (de_ro.get("rank") or {}).get("n_rank_changed"),
            "cluster": de_ro.get("cluster") or {},
            "counter_leg_status": de_counter.get("status"),
            "counter_leg_runs_compared": de_counter.get("runs_compared") or [],
            "counter_leg_detail": de_counter.get("detail"),
            "counter_stage_applicable_in_any_de_run": any(
                ((m or {}).get("stage_applicability") or {}).get("applicable")
                for m in (de_counter.get("per_run_measured") or {}).values()),
        },
        "fr": {
            "jaccard": fr_ro.get("jaccard"),
            "rank_changed": (fr_ro.get("rank") or {}).get("n_rank_changed"),
            "cluster": fr_ro.get("cluster") or {},
            "counter_changes": fr_ro.get("counter_status_changes") or {},
            "counter_leg": {
                "gate": fr_counter.get("gate"),
                "status": fr_counter.get("status"),
                "runs_compared": runs,
                "per_run_passed": fr_counter.get("per_run_passed") or {},
                "n_issued_by_run": {
                    rid: (per_run.get(rid) or {}).get("n_issued")
                    for rid in runs},
            },
            "answer_a": fr_answer_a,
            "answer_b": fr_answer_b,
        },
        "other_applicable_legs_stable": other_stable,
        "other_applicable_legs": other_leg_names,
        "_de_answer_fallback": {"a": answer_a, "b": answer_b},
    }


def recompute_placement(mount: Path) -> dict:
    packet_dir = mount / PACKET_REL
    out = {"packet_dir_exists": packet_dir.is_dir()}
    if not out["packet_dir_exists"]:
        return out
    out["packet_json_sha256"] = sha256_file(packet_dir / "packet.json")
    for qid in QIDS:
        out[f"{qid}.bundle.sha256"] = sha256_file(
            packet_dir / "questions" / f"{qid}.bundle.json")
    placement = {}
    for layer_name in ("disclosures.json", "handoff.json"):
        layer_path = packet_dir / layer_name
        if not layer_path.is_file():
            placement[layer_name] = {"exists": False}
            continue
        doc = load(layer_path)
        # disclosures.json stores per_bundle {qid: {...}}; handoff.json
        # stores bundles [{qid: ...}, ...]. Accept either shape fail-closed.
        nodes = {}
        if isinstance(doc.get("per_bundle"), dict):
            nodes = {qid: node for qid, node in doc["per_bundle"].items()
                     if isinstance(node, dict)}
        elif isinstance(doc.get("bundles"), list):
            nodes = {node.get("qid"): node for node in doc["bundles"]
                     if isinstance(node, dict)}
        layer_rows = {}
        for qid in QIDS:
            node = nodes.get(qid) or {}
            block = node.get("counter_instability_disclosure")
            cov = (node.get("under_coverage_disclosure")
                   or node.get("coverage_gap_disclosure"))
            layer_rows[qid] = {
                "counter_block_present": isinstance(block, dict),
                "disclosure_code": (block or {}).get("disclosure_code")
                if isinstance(block, dict) else None,
                "coverage_block_present": isinstance(cov, dict)
                or cov is not None,
            }
        placement[layer_name] = {
            "exists": True,
            "sha256": sha256_file(layer_path),
            "per_question": layer_rows,
        }
    out["placement"] = placement
    return out


# --------------------------------------------------------------------------- #
# comparison rows
# --------------------------------------------------------------------------- #

def _row(rid, group, description, product_value, lane_value, match,
         comparability="exact", note=None):
    return {
        "id": rid, "group": group, "description": description,
        "product_published": product_value, "lane_recomputed": lane_value,
        "match": bool(match), "comparability": comparability,
        "note": note,
    }


def build_rows(product: dict, lane_state_items: dict, main_items: dict,
               pins: dict, sweep_re: dict, placement: dict) -> list[dict]:
    rows = []
    # ---- verbatim ---------------------------------------------------------
    for rid, key, label in (("V1", ITEM5, "open item 5"),
                            ("V2", ITEM6, "open item 6")):
        prod_disc = product["verbatim_open_items"].get(key)
        prod_vend = product["vendored_open_items"].get(key)
        lane_txt = lane_state_items.get(key)
        main_txt = main_items.get(key)
        shas = {name: (item_text_sha(txt) if isinstance(txt, str) else None)
                for name, txt in (("product_disclosure", prod_disc),
                                  ("product_vendored", prod_vend),
                                  ("lane_state", lane_txt),
                                  ("origin_main_current", main_txt))}
        match = (len(set(shas.values())) == 1 and None not in shas.values()
                 and shas["lane_state"] == FROZEN_TEXT_SHAS.get(key))
        rows.append(_row(
            rid, "verbatim", f"{label} four-way verbatim equality",
            {"product_disclosure_sha256": shas["product_disclosure"],
             "product_vendored_sha256": shas["product_vendored"]},
            {"lane_state_sha256": shas["lane_state"],
             "origin_main_current_sha256": shas["origin_main_current"],
             "freeze_time_sha256": FROZEN_TEXT_SHAS.get(key),
             "all_four_surfaces": shas},
            match, "exact string",
            "all four surfaces carry identical text and match the freeze-time "
            "pin" if match else "TEXT DIVERGES ACROSS SURFACES OR FREEZE PIN"))

    # ---- pins -------------------------------------------------------------
    rows.append(_row(
        "P1", "pin", "accepted-state sha256 at pin commit re-derives to the "
        "digest Product publishes",
        product["file_sha256_at_pin"], pins["pin_state_sha256"],
        product["file_sha256_at_pin"] == pins["pin_state_sha256"]
        == PIN_STATE_SHA256, "exact sha256"))
    rows.append(_row(
        "P2", "pin", "accepted-state git blob oid at pin commit re-derives to "
        "the oid Product publishes",
        product["git_blob_oid_at_pin"], pins["pin_state_blob"],
        product["git_blob_oid_at_pin"] == pins["pin_state_blob"]
        == PIN_STATE_BLOB, "exact oid"))
    rows.append(_row(
        "P3", "pin", "pin commit resolvability",
        product["pin_commit"],
        {"commit": PIN_COMMIT, "resolution": pins["pin_resolution"],
         "current_file_sha256": pins["current_state_sha256"],
         "current_blob_oid": pins["current_state_blob"]},
        product["pin_commit"] == PIN_COMMIT, "exact",
        "file-level sha/blob drift vs the pin is EXPECTED under Product's own "
        "pin_semantics; the load-bearing live check is the V1/V2 verbatim row"))
    drift = (pins["current_state_sha256"] != PIN_STATE_SHA256)
    rows.append(_row(
        "P4", "pin", "current origin/main accepted-state open items intact "
        "(load-bearing live check of Product's pin_semantics)",
        {"file_sha256_current": pins["current_state_sha256"],
         "file_sha256_at_pin": PIN_STATE_SHA256, "drift_disclosed": drift},
        {"open_items_present_in_current": None},  # filled by V1/V2
        True, "disclosure",
        "file-level drift is disclosed here and never silently accepted; "
        "verbatim equality is carried by V1/V2"))

    # ---- quantities -------------------------------------------------------
    de, fr = sweep_re["de"], sweep_re["fr"]
    p1ext = product["p1ext"]
    jac = p1ext.get("retrieved_set_jaccard") or {}
    rows.append(_row(
        "Q1_jaccard_de", "quantity", "DE retrieved-set jaccard",
        jac.get("de"), de["jaccard"],
        jac.get("de") is not None and round(de["jaccard"], 6)
        == jac.get("de"), "round-6"))
    rows.append(_row(
        "Q2_jaccard_fr", "quantity", "FR retrieved-set jaccard",
        jac.get("fr"), fr["jaccard"],
        jac.get("fr") is not None and round(fr["jaccard"], 6)
        == jac.get("fr"), "round-6"))
    rc = p1ext.get("common_ids_changing_rank") or {}
    rows.append(_row(
        "Q3_rank_changed_de", "quantity", "DE common ids changing rank",
        rc.get("de"), de["rank_changed"],
        rc.get("de") == de["rank_changed"], "exact integer"))
    rows.append(_row(
        "Q4_rank_changed_fr", "quantity", "FR common ids changing rank",
        rc.get("fr"), fr["rank_changed"],
        rc.get("fr") == fr["rank_changed"], "exact integer"))
    cl = p1ext.get("cluster_reassignment") or {}

    def _cluster_row(rid, side, prod, sweep_cluster):
        prod = prod or {}
        exp = {
            "reassigned": sweep_cluster.get("n_reassigned"),
            "common_ids": sweep_cluster.get("n_common_with_cluster"),
            "share": (round(sweep_cluster.get("reassigned_share"), 3)
                      if sweep_cluster.get("reassigned_share") is not None
                      else None),
        }
        match = (prod.get("reassigned") == exp["reassigned"]
                 and prod.get("common_ids") == exp["common_ids"]
                 and prod.get("share") == exp["share"])
        return _row(rid, "quantity", f"{side} cluster reassignment",
                    prod, exp, match, "exact int + round-3 share")

    rows.append(_cluster_row("Q5_cluster_de", "DE", cl.get("de"), de["cluster"]))
    rows.append(_cluster_row("Q6_cluster_fr", "FR", cl.get("fr"), fr["cluster"]))
    lost = sorted(p1ext.get("fr_counter_evidence_lost") or [])
    exp_lost = sorted(fr["counter_changes"].get("evidence_lost_examples") or [])
    rows.append(_row(
        "Q7_fr_evidence_lost", "quantity", "FR counter evidence lost ids",
        lost, exp_lost, lost == exp_lost, "set equality"))
    gained = sorted(p1ext.get("fr_counter_evidence_gained") or [])
    exp_gained = sorted(
        fr["counter_changes"].get("evidence_gained_examples") or [])
    rows.append(_row(
        "Q8_fr_evidence_gained", "quantity", "FR counter evidence gained ids",
        gained, exp_gained, gained == exp_gained, "set equality"))

    p1 = product["p1"]
    fl = fr["counter_leg"]
    p1_expected = {
        "gate": "sr::counter_authority_surface",
        "group": "FR 102-CP same-query group",
        "status": fl.get("status"),
        "passing_run": next((r for r, ok in (fl.get("per_run_passed") or {}).items()
                             if ok is True), None),
        "failing_run": next((r for r, ok in (fl.get("per_run_passed") or {}).items()
                             if ok is False), None),
        "failing_run_n_issued": fl.get("n_issued_by_run", {}).get(
            next((r for r, ok in (fl.get("per_run_passed") or {}).items()
                  if ok is False), "__none__"), None),
        "other_applicable_verdicts":
            "STABLE on both same-query groups"
            if sweep_re["other_applicable_legs_stable"]
            else "NOT-ALL-STABLE",
    }
    q9_match = all(
        p1.get(k) == p1_expected[k]
        for k in ("gate", "status", "passing_run", "failing_run",
                  "failing_run_n_issued", "other_applicable_verdicts"))
    q9_match = q9_match and "FR 102-CP" in str(p1.get("group") or "")
    rows.append(_row(
        "Q9_fr_counter_divergence", "quantity",
        "FR counter-stage divergence block re-derives from the sweep",
        {k: p1.get(k) for k in p1_expected}, p1_expected, q9_match,
        "exact strings/ints", f"other applicable legs: "
        f"{sweep_re['other_applicable_legs']}"))

    de_applies = str((product["de_applies"] or {}).get("counter_stage_evidence") or "")
    de_runs = de.get("counter_leg_runs_compared") or []
    de_runs_both_na = (
        de["counter_leg_status"] == "NOT_APPLICABLE"
        and len(de_runs) == 2
        and "NOT_APPLICABLE in run(s)" in str(de.get("counter_leg_detail") or "")
        and all(r in str(de.get("counter_leg_detail") or "") for r in de_runs))
    q10_match = (de_runs_both_na
                 and "UNTESTED" in de_applies
                 and "NOT_APPLICABLE in both DE runs" in de_applies)
    rows.append(_row(
        "Q10_de_untested", "quantity",
        "DE attribution: counter stability UNTESTED (NOT_APPLICABLE in both "
        "DE runs)",
        de_applies,
        {"counter_leg_status": de["counter_leg_status"],
         "runs_compared": de_runs,
         "detail": de.get("counter_leg_detail"),
         "both_runs_not_applicable": de_runs_both_na},
        q10_match, "exact status + both-runs naming + required phrase"))
    it_applies = str((product["it_applies"] or {}).get("counter_stage_evidence") or "")
    structure_keys = sweep_re["expected_structure_keys"]
    q11_match = (sweep_re["n_groups"] == 2
                 and sweep_re["expected_n_groups"] == 2
                 and len(structure_keys) > 0
                 and not any(k.upper().startswith("IT") for k in structure_keys)
                 and "NOT MEASURED" in it_applies
                 and "no IT same-query group" in it_applies)
    rows.append(_row(
        "Q11_it_not_measured", "quantity",
        "IT attribution: no IT same-query group in the 2-group population",
        it_applies,
        {"n_groups": sweep_re["n_groups"],
         "expected_n_groups": sweep_re["expected_n_groups"],
         "structure_keys": structure_keys},
        q11_match, "exact structure (non-empty keys, no it- prefix) + "
        "required phrase"))
    ans_a = fr["answer_a"].get("n_cited_decision_ids")
    ans_b = fr["answer_b"].get("n_cited_decision_ids")
    prose_differs = (fr["answer_a"].get("prose_sha256")
                     != fr["answer_b"].get("prose_sha256"))
    verbatim_item6 = product["verbatim_open_items"].get(ITEM6) or ""
    q12_match = (ans_a == 6 and ans_b == 5 and prose_differs
                 and "6 cited vs 5 cited" in verbatim_item6)
    rows.append(_row(
        "Q12_answer_cited_swap", "quantity",
        "answer prose 6-vs-5 cited swap re-derives from the sweep FR group",
        {"verbatim_mentions_swap": "6 cited vs 5 cited" in verbatim_item6},
        {"answer_a_n_cited": ans_a, "answer_b_n_cited": ans_b,
         "prose_sha256_differs": prose_differs},
        q12_match, "exact ints + phrase presence"))

    # ---- placement / packet identity --------------------------------------
    l1_ok = True
    l1_detail = {}
    for layer, info in (placement.get("placement") or {}).items():
        per_q = info.get("per_question") or {}
        for qid in QIDS:
            q = per_q.get(qid) or {}
            ok = (q.get("counter_block_present") is True
                  and q.get("disclosure_code") == "run_to_run_counter_instability"
                  and q.get("coverage_block_present") is True)
            l1_detail[f"{layer}:{qid}"] = q
            l1_ok = l1_ok and ok
    rows.append(_row(
        "L1", "placement",
        "packet disclosure layer carries the counter-instability block beside "
        "the coverage-gap block for all three V3 qids",
        product["per_qids"], l1_detail, l1_ok and
        product["per_qids"] == sorted(QIDS), "structure"))
    pub_packet = (product["packet"] or {}).get("packet_json_raw_sha256")
    l2_match = (placement.get("packet_json_sha256") == V3_PACKET_SHA
                and pub_packet == V3_PACKET_SHA
                and all(placement.get(f"{qid}.bundle.sha256") == V3_BUNDLE_SHAS[qid]
                        for qid in QIDS))
    rows.append(_row(
        "L2", "placement",
        "packet.json and the three bundle scored bytes equal the frozen V3 pins",
        {"published_packet_sha": pub_packet,
         "freeze_time_bundles": V3_BUNDLE_SHAS},
        {"observed_packet_sha": placement.get("packet_json_sha256"),
         "observed_bundles": {qid: placement.get(f"{qid}.bundle.sha256")
                              for qid in QIDS}},
        l2_match, "exact sha256",
        "scored bytes never moved by the disclosure-layer regeneration"))
    return rows


# --------------------------------------------------------------------------- #
# non-vacuity
# --------------------------------------------------------------------------- #

def non_vacuity(product: dict, lane_items: dict, main_items: dict, pins: dict,
                sweep_re: dict, placement: dict, base_rows: list[dict]) -> list[dict]:
    """Re-run the REAL row comparator on four planted perturbations.

    Each control must flip its named row from match=True (as in base_rows)
    to match=False; a comparator that cannot report DIFFERENT invalidates
    the run (hypothesis N5).
    """
    import copy as _copy_mod

    base = {r["id"]: r["match"] for r in base_rows}
    controls = []

    def _flip(control_id, planted, mutate, target_row):
        prod = _copy_mod.deepcopy(product)
        mutate(prod)
        rows = build_rows(prod, lane_items, main_items, pins, sweep_re,
                          placement)
        row = next(r for r in rows if r["id"] == target_row)
        controls.append({
            "id": control_id,
            "planted": planted,
            "target_row": target_row,
            "base_match": base.get(target_row),
            "perturbed_match": row["match"],
            "detected": (base.get(target_row) is True
                         and row["match"] is False),
            "expected_detected": True,
        })

    _flip("N1",
          "p1ext.retrieved_set_jaccard.fr = 0.5 (in-memory copy)",
          lambda p: p["p1ext"]["retrieved_set_jaccard"].__setitem__("fr", 0.5),
          "Q2_jaccard_fr")
    _flip("N2",
          "open item 5: first ' DIVERGENT' removed (in-memory copy)",
          lambda p: p["verbatim_open_items"].__setitem__(
              ITEM5, p["verbatim_open_items"][ITEM5].replace(
                  " DIVERGENT", "", 1)),
          "V1")
    _flip("N3",
          "file_sha256_at_pin replaced by 64 zeros (in-memory copy)",
          lambda p: p.__setitem__("file_sha256_at_pin", "0" * 64),
          "P1")
    _flip("N4",
          "fr_counter_evidence_lost drops its last id (in-memory copy)",
          lambda p: p["p1ext"].__setitem__(
              "fr_counter_evidence_lost",
              (p["p1ext"].get("fr_counter_evidence_lost") or [])[:-1]),
          "Q7_fr_evidence_lost")

    for c in controls:
        c["hold"] = bool(c["detected"]) == bool(c.get("expected_detected", True))
    return controls


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def run(mount: Path, out_path: Path | None = None) -> dict:
    started = utcnow()
    t0 = time.time()

    if sha256_file(HYP_PATH) != HYP_SHA256:
        raise EnvironmentError_(
            "frozen hypothesis bytes moved; refusing to run "
            f"(expected {HYP_SHA256})")
    if not FREEZE_PATH.is_file():
        raise EnvironmentError_("freeze record missing")

    pins_before = {
        "sweep": sha256_file(SWEEP_PATH) if SWEEP_PATH.is_file() else None,
        "frozen_bars": {k: sha256_file(p) if p.is_file() else None
                        for k, p in FROZEN_BARS.items()},
    }
    if pins_before["sweep"] != SWEEP_SHA256:
        raise EnvironmentError_(
            f"sweep artifact pin mismatch: {pins_before['sweep']}")
    for k, want in FROZEN_BAR_SHAS.items():
        if pins_before["frozen_bars"].get(k) != want:
            raise EnvironmentError_(f"frozen bar pin mismatch: {k}")

    disclosure_path = mount / DISCLOSURE_REL
    vendored_path = mount / VENDORED_REL
    packet_probe = mount / PACKET_REL / "packet.json"
    if not disclosure_path.is_file() or not vendored_path.is_file() \
            or not packet_probe.is_file():
        raise EnvironmentError_(
            "product mount absent or incomplete "
            f"(disclosure={disclosure_path.is_file()}, "
            f"vendored={vendored_path.is_file()}, "
            f"packet={packet_probe.is_file()}); mount-absent is NEVER a pass")

    disclosure_sha = sha256_file(disclosure_path)
    vendored_sha = sha256_file(vendored_path)
    product = extract_product(load(disclosure_path), load(vendored_path))

    pin_resolution = ensure_pin_commit(PIN_COMMIT)
    pin_state_sha, pin_state_blob = accepted_state_at(PIN_COMMIT)
    cur_sha, cur_blob, cur_doc = accepted_state_current(MAIN_REF)
    current_items = (cur_doc.get("open_items") or {})
    lane_doc = load(STATE_PATH)
    lane_items = (lane_doc.get("open_items") or {})

    sweep = load(SWEEP_PATH)
    sweep_re = recompute_sweep(sweep)
    placement = recompute_placement(mount)

    pins = {
        "pin_resolution": pin_resolution,
        "pin_state_sha256": pin_state_sha,
        "pin_state_blob": pin_state_blob,
        "current_state_sha256": cur_sha,
        "current_state_blob": cur_blob,
    }
    rows = build_rows(product, lane_items, current_items, pins, sweep_re,
                      placement)
    controls = non_vacuity(product, lane_items, current_items, pins, sweep_re,
                           placement, rows)

    # freeze-time observation drift (always disclosed with both digests)
    freeze_obs = {
        "disclosure_artifact": {
            "freeze_time": "ad9e8877742a3cad744dd7bed60dca73bf29b9877e1dfe16f1a339a9e79b4a35",
            "observed": disclosure_sha,
        },
        "vendored_open_items": {
            "freeze_time": "aecab7ff1d30020c4a6052bfbe09892ba352c2a234135b37398de60231126330",
            "observed": vendored_sha,
        },
    }
    for v in freeze_obs.values():
        v["drift_disclosed"] = v["freeze_time"] != v["observed"]

    # P4 carries match=True by design (disclosure row); every other row is
    # compared strictly on its own match flag.
    diverging = [r for r in rows
                 if (r["id"] != "P4") and not r["match"]]
    non_vacuous = all(c["hold"] for c in controls)

    if diverging:
        verdict = "VERDICT_DIVERGENCE_HEADLINE"
        exit_code = 1
        headline = (f"{len(diverging)} of {len(rows) - 1} comparable rows "
                    f"DIVERGE: " + ", ".join(r["id"] for r in diverging))
    elif not non_vacuous:
        verdict = "NON_VACUOUS"
        exit_code = 1
        headline = ("non-vacuity control failed; the instrument cannot "
                    "certify zero divergence")
    else:
        verdict = "VERDICT_DISCLOSURE_PROVENANCE_VERIFIED_ZERO_DIVERGENCE"
        exit_code = 0
        headline = (f"ZERO_DIVERGENCE_ACROSS_{len(rows) - 1}_COMPARABLE_ROWS "
                    f"(verbatim 2/2, pin 3/3, quantity 12/12, placement 2/2); "
                    f"non-vacuity {sum(c['hold'] for c in controls)}/"
                    f"{len(controls)}")

    pins_after = {
        "sweep": sha256_file(SWEEP_PATH) if SWEEP_PATH.is_file() else None,
        "frozen_bars": {k: sha256_file(p) if p.is_file() else None
                        for k, p in FROZEN_BARS.items()},
    }
    safety = {
        "pins_unchanged": pins_before == pins_after,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "hypothesis_unchanged": sha256_file(HYP_PATH) == HYP_SHA256,
        "no_product_mount_writes": True,
        "network_operations": ["git fetch --depth=1 origin <pin-commit> "
                               f"if absent ({pin_resolution})"],
    }
    if not safety["pins_unchanged"] or not safety["hypothesis_unchanged"]:
        raise EnvironmentError_("safety violation: frozen pins moved during run")

    record = {
        "schema": "lex-evaluation-disclosure-provenance-crosscheck/1",
        "lane": "evaluation",
        "direction_version": 61,
        "run_id": RUN_ID,
        "generated_at": utcnow(),
        "started_at": started,
        "elapsed_s": round(time.time() - t0, 3),
        "hypothesis_sha256": HYP_SHA256,
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "instrument": "evaluation/disclosure_provenance_crosscheck.py",
        "instrument_sha256": sha256_file(Path(__file__).resolve()),
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "instrument_strengthening_disclosure": (
            "An initial execution of this run wrote "
            "39516448683_initial_instrument_execution_preserved.json "
            "(preserved, never deleted). Before publication the Q10/Q11 "
            "structural checks were STRENGTHENED only (DE both-runs "
            "not-applicable naming; non-empty structure keys with no it- "
            "prefix; instrument digest + numeric environment recorded). No "
            "check was weakened, no row was dropped, the frozen hypothesis "
            "and success rule are untouched, and this artifact is the "
            "measurement of record for run 39516448683."
            if (OUT_DIR / f"{RUN_ID}_initial_instrument_execution_preserved.json"
                ).is_file() else None),
        "subject_under_test": {
            "product_mount": str(mount),
            "disclosure_artifact": str(disclosure_path),
            "disclosure_artifact_sha256": disclosure_sha,
            "vendored_open_items_sha256": vendored_sha,
            "freeze_time_observations": freeze_obs,
        },
        "evaluation_owned_sources": {
            "sweep_artifact": str(SWEEP_PATH),
            "sweep_artifact_sha256": pins_before["sweep"],
            "pin_commit": PIN_COMMIT,
            "pin_resolution": pin_resolution,
            "pin_state_sha256": pin_state_sha,
            "pin_state_blob_oid": pin_state_blob,
            "current_main_state_sha256": cur_sha,
            "current_main_state_blob_oid": cur_blob,
            "frozen_bar_shas": pins_before["frozen_bars"],
        },
        "comparison_rows": rows,
        "n_rows": len(rows),
        "n_comparable": len([r for r in rows if r["id"] != "P4"]),
        "n_match": len([r for r in rows
                        if r["id"] != "P4" and r["match"]]),
        "n_divergent": len(diverging),
        "diverging_rows": [r["id"] for r in diverging],
        "headline": headline,
        "verdict": verdict,
        "exit_code": exit_code,
        "non_vacuity_controls": controls,
        "non_vacuity_all_hold": non_vacuous,
        "safety": safety,
        "claim_ceiling": (
            "Verifies PROVENANCE FIDELITY of Product's published "
            "counter-instability disclosure against Evaluation-owned "
            "committed evidence. Does NOT re-measure P1/P1ext, scores no "
            "bar, meets no frozen bar, serves no packet, lifts no "
            "DO-NOT-SERVE order, authorises no owner question."),
        "state_flags": {
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "both_do_not_serve_orders_stand": True,
            "no_174k_benchmark_rerun": True,
            "no_new_thresholds": True,
        },
    }

    if out_path is None:
        out_path = OUT_DIR / f"{RUN_ID}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mount", type=Path, default=DEFAULT_MOUNT)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    try:
        rec = run(args.mount, args.out)
    except EnvironmentError_ as exc:
        print(f"ENVIRONMENT_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"verdict": rec["verdict"],
                      "exit_code": rec["exit_code"],
                      "headline": rec["headline"],
                      "n_rows": rec["n_rows"],
                      "n_divergent": rec["n_divergent"]}, indent=2))
    return rec["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
