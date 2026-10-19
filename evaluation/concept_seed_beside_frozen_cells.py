#!/usr/bin/env python3
"""Publish the accepted concept-seed numbers BESIDE the frozen benchmark cells.

DIRECTION v58 ORDERED WORK (3)(b)
---------------------------------
"The new Frontier team frontier-concept-seed-recall (portfolio v30) will
publish its natural-language concept-seed numbers BESIDE your frozen-benchmark
cells (the 0/2, 0/5, 0/2 fr/it authority-recall cells in accepted record
results/evaluation/retrieval_benchmark/39117425713.json), never in place of
them, with any divergence named as the headline; this lane issues no
candidates and re-tunes nothing."

STATE AT FREEZE TIME (pre-registered readings of two ACCEPTED artifacts)
------------------------------------------------------------------------
* frontier-concept-seed-recall TERMINATED at portfolio v31 with the accepted
  OUTCOME_A_COMPONENT verdict (run 39251875368; independent audit
  CYCLE_39251875368_GATE.json gate=PASS safe_to_integrate=true
  required_fixes=[]; Product ADOPT at run 39262796670).
* The team's own harness record does NOT contain a side-by-side table with
  the frozen benchmark cells (its per-unit numbers and acceptance tests 4/6
  confirm the comparison; no beside-table is published in the evaluation
  namespace).  This instrument closes that publication gap.

WHAT THIS INSTRUMENT DOES
-------------------------
1. Re-hashes every input READ-ONLY and fails closed on any drift (freeze-first:
   hypothesis + freeze record committed at d9037df7 before this execution).
2. Extracts the six frozen fr/it authority::baseline_lang_recall cells from the
   accepted frozen benchmark record, UNCHANGED.
3. Extracts the concept-seed A0 / A1_candidate_only / A1_union / A2_blanked /
   A3_rotated numbers per unit from the accepted team harness record.
4. Re-derives the comparison from the two pinned records (never trusting the
   team's verdict prose) and publishes ONE side-by-side table.
5. Names the DIVERGENCE as the headline: 1 of 6 cells improved
   (corporate-criminal-liability::fr 0/2 -> 1/2 via bge_BGE_142_IV_333), 5 of 6
   unchanged at zero, 8 of 9 unique frozen authority ids still missing
   everywhere, coverage axis null.
6. Re-verifies (carry-forward, never re-opened) that the F-3B disposition is
   intact and that packet 39275520116 is still BUILT_NOT_SERVED - and
   computes NO verdict on the packet's bytes.

WHAT THIS INSTRUMENT NEVER DOES
-------------------------------
Edits no frozen file, rubric, bar, threshold, packet byte or admission record;
issues no candidate; re-tunes nothing; re-scores no frontier component;
derives no new threshold.  The frozen cells are published UNCHANGED, never
replaced by the new numbers.  A zero count is published as a retrieval signal,
never as proof of corpus absence.

Exit codes
----------
0  CONCEPT_SEED_BESIDE_FROZEN_CELLS_PUBLISHED (divergence named as headline)
1  CONCEPT_SEED_BESIDE_FROZEN_CELLS_FAILED (any pin drift, any contradiction
   between the published table and the pinned accepted records, or any
   forbidden edit)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-concept-seed-beside-frozen-cells/1"
HYPOTHESIS_RELPATH = "evaluation/CONCEPT_SEED_BESIDE_FROZEN_CELLS_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/CONCEPT_SEED_BESIDE_FROZEN_CELLS_FREEZE_RECORD.json"

FROZEN_RECORD = "results/evaluation/retrieval_benchmark/39117425713.json"
RULES_LABEL = "evaluation/frozen_bars/RULES_LABEL.json"
RULES_GEOMETRY = "evaluation/frozen_bars/RULES_GEOMETRY.json"
F3B_RESTORED = "results/evaluation/frozen_cache_integrity/39164900837.json"
F3B_PRE_RESTORE = "results/evaluation/frozen_cache_integrity/39164900837_pre_restore.json"
F3B_REHOMED = "results/evaluation/frozen_cache_integrity/39164900837_post-restore-9b61dcf8.json"
F3B_PREIMAGE = "results/evaluation/frozen_cache_integrity/39164900837_preimage_recovered.json"

FRONTIER_REF = "origin/lab/frontier/frontier-concept-seed-recall"
FRONTIER_HARNESS = "results/frontier/frontier-concept-seed-recall/harness_results_39237146851.json"
FRONTIER_GATE = "results/audit/frontier/frontier-concept-seed-recall/CYCLE_39251875368_GATE.json"
FRONTIER_RULES = "results/frontier/frontier-concept-seed-recall/RULES.json"

# Git blob object ids (content-addressed, ref-independent) frozen in the
# hypothesis; the instrument re-hashes the blob content and compares.
PINS = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_benchmark_record": "f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75",
    "frontier_harness": "01fdf0f868f8ad163bf812570ccd5cb36677dac1",
    "frontier_gate": "18f828c25362dc4e459113aaa04af0ecddda41e1",
    "frontier_rules": "4e988256c9cb3f4126d620dd197c0c1ad9404b29",
    "f3b_restored_39164900837": "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e",
}

FROZEN_SPEC_DIGEST = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
FREEZE_RECORD_DIGEST = "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49"

FROZEN_SLUGS = ("corporate-criminal-liability", "business-judgment-rule", "petty-theft-dismissal")
FROZEN_LANGS = ("fr", "it")
ADOPTION_VERDICT = Path("/tmp/lex_accepted/product/results/product/frontier_verdicts/frontier-concept-seed-recall_adoption_39262796670.json")
ADOPTION_SHA256 = "17189fcd1c9d6ba45baaf5a159fb0fb51a15388f32202ba1c0e28455078ae816"
UNSERVED_PACKET = Path("/tmp/lex_accepted/product/results/product/gate_packet/39275520116/packet.json")

OUT_DIR = "results/evaluation/concept_seed_beside_frozen_cells"


def fail(msg: str) -> None:
    print(f"CONCEPT_SEED_BESIDE_FROZEN_CELLS_FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_show(ref: str, path: str) -> bytes:
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True)
    if proc.returncode != 0:
        fail(f"git show {ref}:{path} failed: {proc.stderr.decode(errors='replace')[:200]}")
    return proc.stdout


def git_blob_sha(ref: str, path: str) -> str:
    proc = subprocess.run(["git", "rev-parse", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True)
    if proc.returncode != 0:
        fail(f"git rev-parse {ref}:{path} failed")
    return proc.stdout.decode().strip()


def load_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f"{label} is not valid JSON: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args()
    run_id = args.run_id

    # ------------------------------------------------------------------ #
    # 1. freeze-first contract: hypothesis + freeze record exist and pin
    # ------------------------------------------------------------------ #
    hyp_path = REPO_ROOT / HYPOTHESIS_RELPATH
    frz_path = REPO_ROOT / FREEZE_RELPATH
    if not hyp_path.is_file() or not frz_path.is_file():
        fail("hypothesis/freeze record missing - freeze-first violated")
    hypothesis = load_json_bytes(hyp_path.read_bytes(), "hypothesis")
    freeze_record = load_json_bytes(frz_path.read_bytes(), "freeze record")
    if hypothesis.get("direction_version") != 58:
        fail("hypothesis direction_version != 58")

    # ------------------------------------------------------------------ #
    # 2. re-hash every input read-only; fail closed on drift
    # ------------------------------------------------------------------ #
    rehashes: dict[str, str] = {}
    for rel, pin in (
        (RULES_LABEL, PINS["rules_label"]),
        (RULES_GEOMETRY, PINS["rules_geometry"]),
        (FROZEN_RECORD, PINS["frozen_benchmark_record"]),
        (F3B_RESTORED, PINS["f3b_restored_39164900837"]),
    ):
        p = REPO_ROOT / rel
        if not p.is_file():
            fail(f"missing input {rel}")
        digest = sha256_file(p)
        rehashes[rel] = digest
        if digest != pin:
            fail(f"PIN DRIFT: {rel} sha256 {digest} != pinned {pin}")

    for rel_path, pin in (
        (FRONTIER_RULES, PINS["frontier_rules"]),
        (FRONTIER_GATE, PINS["frontier_gate"]),
        (FRONTIER_HARNESS, PINS["frontier_harness"]),
    ):
        blob = git_blob_sha(FRONTIER_REF, rel_path)
        if blob != pin:
            fail(f"PIN DRIFT: {FRONTIER_REF}:{rel_path} blob {blob} != pinned {pin}")

    # Frontier audit gate must be PASS (read-only)
    gate = load_json_bytes(git_show(FRONTIER_REF, FRONTIER_GATE), "frontier audit gate")
    if gate.get("gate") != "PASS" or gate.get("safe_to_integrate") is not True:
        fail("frontier audit gate is not PASS/safe_to_integrate")

    # Frozen record's embedded pins must match the frozen spec + freeze record
    frozen = load_json_bytes((REPO_ROOT / FROZEN_RECORD).read_bytes(), "frozen benchmark record")
    if frozen.get("frozen_sha256") != FROZEN_SPEC_DIGEST:
        fail("frozen record embedded frozen_sha256 drift")
    if frozen.get("freeze_record_sha256") != FREEZE_RECORD_DIGEST:
        fail("frozen record embedded freeze_record_sha256 drift")

    # ------------------------------------------------------------------ #
    # 3. F-3B carry-forward: disposition intact, NOT re-opened.
    #    Expected digests are READ from the accepted disposition record
    #    (39287274485, re-hash verified), never hand-typed in this source.
    # ------------------------------------------------------------------ #
    f3b_record_path = REPO_ROOT / "results/evaluation/f3b_restore_disposition/39287274485.json"
    if not f3b_record_path.is_file():
        fail("accepted F-3B disposition record missing")
    f3b_accepted = load_json_bytes(f3b_record_path.read_bytes(), "F-3B disposition record")
    if f3b_accepted.get("verdict") != "F3B_DISPOSITION_COMPLETE":
        fail("accepted F-3B disposition verdict is not F3B_DISPOSITION_COMPLETE")
    f3b_expected = {
        "restored": f3b_accepted["records"]["run_record"]["restored_sha256"],
        "pre_rewrite": f3b_accepted["records"]["run_record"]["pre_rewrite_sha256"],
        "pre_restore_sibling": next(
            p["sha256"] for p in f3b_accepted["records"]["preserved"] if p["path"] == F3B_PRE_RESTORE
        ),
        "preimage": next(
            p["sha256"] for p in f3b_accepted["records"]["preserved"] if p["path"] == F3B_PREIMAGE
        ),
        "rehomed": f3b_accepted["records"]["rehomed"]["rehomed_sha256"],
    }
    f3b = {
        "restored_sha256": sha256_file(REPO_ROOT / F3B_RESTORED),
        "pre_restore_sha256": sha256_file(REPO_ROOT / F3B_PRE_RESTORE),
        "rehomed_sha256": sha256_file(REPO_ROOT / F3B_REHOMED),
        "preimage_sha256": sha256_file(REPO_ROOT / F3B_PREIMAGE),
    }
    f3b_intact = (
        f3b["restored_sha256"] == f3b_expected["restored"]
        and f3b["restored_sha256"] == f3b_expected["pre_rewrite"]
        and f3b["restored_sha256"] == PINS["f3b_restored_39164900837"]
        and f3b["restored_sha256"] == f3b["preimage_sha256"]
        and f3b["pre_restore_sha256"] == f3b_expected["pre_restore_sibling"]
        and f3b["rehomed_sha256"] == f3b_expected["rehomed"]
        and f3b_accepted["records"]["deleted"] == []
        and f3b_accepted["records"]["siblings_preserved_intact"] is True
    )

    # ------------------------------------------------------------------ #
    # 4. unserved packet: re-verify BUILT_NOT_SERVED; NO verdict on bytes
    # ------------------------------------------------------------------ #
    packet_state: dict[str, Any] = {"packet": "39275520116", "verdict_computed_on_bytes": False}
    if UNSERVED_PACKET.is_file():
        pkt = load_json_bytes(UNSERVED_PACKET.read_bytes(), "unserved packet manifest")
        admission = pkt.get("packet_admission") or {}
        packet_state.update(
            serve_status="BUILT_NOT_SERVED",
            packet_admitted=admission.get("packet_admitted"),
            ready_for_owner_session_allowed=admission.get("ready_for_owner_session_allowed"),
            falsification_verdict="WITHHELD_PENDING_SERVE",
        )
        if admission.get("packet_admitted") is not False or admission.get("ready_for_owner_session_allowed") is not False:
            fail("packet 39275520116 no longer BUILT_NOT_SERVED - stop and re-baseline")
    else:
        packet_state["serve_status"] = "MOUNT_ABSENT"

    # ------------------------------------------------------------------ #
    # 5. frozen cells, UNCHANGED, from the frozen benchmark record
    # ------------------------------------------------------------------ #
    frozen_cells: dict[str, Any] = {}
    for gate in frozen["verdict"]["gates"]:
        name = gate["gate"]
        if not name.startswith("authority::baseline_lang_recall::"):
            continue
        parts = name.split("::")
        slug, lang = parts[2], parts[3]
        if slug in FROZEN_SLUGS and lang in FROZEN_LANGS:
            frozen_cells[name] = {
                "slug": slug,
                "language": lang,
                "passed": gate["passed"],
                "required": gate["measured"]["required"],
                "hits": gate["measured"]["hits"],
                "missing": gate["measured"]["missing"],
                "n_rows": gate["measured"]["n_rows"],
            }
    if len(frozen_cells) != 6:
        fail(f"expected 6 frozen fr/it authority cells, found {len(frozen_cells)}")

    # ------------------------------------------------------------------ #
    # 6. concept-seed numbers from the accepted team harness record
    # ------------------------------------------------------------------ #
    harness = load_json_bytes(git_show(FRONTIER_REF, FRONTIER_HARNESS), "frontier harness record")
    if harness.get("verdict", {}).get("outcome") != "OUTCOME_A_COMPONENT":
        fail("frontier harness outcome is not the accepted OUTCOME_A_COMPONENT")
    per_unit = harness["measurement"]["per_unit"]

    def recall_of(unit: dict, arm: str) -> Any:
        return unit["authority_recall"][arm]["recall"]

    concept_seed_cells: dict[str, Any] = {}
    for slug in FROZEN_SLUGS:
        for lang in FROZEN_LANGS:
            unit_id = f"frozen::{slug}::{lang}"
            unit = per_unit.get(unit_id)
            if unit is None:
                fail(f"team record missing unit {unit_id}")
            ar = unit["authority_recall"]
            concept_seed_cells[unit_id] = {
                "slug": slug,
                "language": lang,
                "A0_baseline_shipped": {
                    "required": ar["A0_baseline_shipped"]["required"],
                    "hits": ar["A0_baseline_shipped"]["hits"],
                    "recall": recall_of(unit, "A0_baseline_shipped"),
                },
                "A1_candidate_only": {
                    "hits": ar["A1_candidate_only"]["hits"],
                    "recall": recall_of(unit, "A1_candidate_only"),
                },
                "A1_union": {
                    "hits": ar["A1_union"]["hits"],
                    "missing": ar["A1_union"]["missing"],
                    "recall": recall_of(unit, "A1_union"),
                    "n_rows": unit["A1_union"]["n_rows"],
                },
                "A2_blanked": {"recall": recall_of(unit, "A2_blanked")},
                "A3_rotated": {"recall": recall_of(unit, "A3_rotated")},
                "candidate_beats_blanked_on_recall": unit["control_summary"]["candidate_beats_blanked_on_recall"],
            }

    # ------------------------------------------------------------------ #
    # 7. re-derive the comparison from the two pinned records
    # ------------------------------------------------------------------ #
    side_by_side: list[dict[str, Any]] = []
    for slug in FROZEN_SLUGS:
        for lang in FROZEN_LANGS:
            gate_name = f"authority::baseline_lang_recall::{slug}::{lang}"
            frozen_cell = frozen_cells[gate_name]
            cs = concept_seed_cells[f"frozen::{slug}::{lang}"]
            # the frozen cell's A0 must equal the team's A0 (both 0 hits)
            if frozen_cell["hits"] != cs["A0_baseline_shipped"]["hits"]:
                fail(f"A0 mismatch on {gate_name}: frozen {frozen_cell['hits']} vs team {cs['A0_baseline_shipped']['hits']}")
            if frozen_cell["required"] != cs["A0_baseline_shipped"]["required"]:
                fail(f"required-id mismatch on {gate_name}")
            n_req = len(frozen_cell["required"])
            frozen_hits = len(frozen_cell["hits"])
            a1_hits = len(cs["A1_union"]["hits"])
            side_by_side.append(
                {
                    "frozen_gate": gate_name,
                    "slug": slug,
                    "language": lang,
                    "frozen_cell": {
                        "hits": f"{frozen_hits}/{n_req}",
                        "hits_list": frozen_cell["hits"],
                        "required": frozen_cell["required"],
                        "missing": frozen_cell["missing"],
                        "n_rows": frozen_cell["n_rows"],
                        "frozen_passed": frozen_cell["passed"],
                    },
                    "concept_seed_A0": {
                        "hits": f"{frozen_hits}/{n_req}",
                        "hits_list": cs["A0_baseline_shipped"]["hits"],
                    },
                    "concept_seed_A1_union": {
                        "hits": f"{a1_hits}/{n_req}",
                        "hits_list": cs["A1_union"]["hits"],
                        "missing": cs["A1_union"]["missing"],
                        "n_rows": cs["A1_union"]["n_rows"],
                    },
                    "delta_hits": a1_hits - frozen_hits,
                    "improved": a1_hits > frozen_hits,
                }
            )

    improved = [c for c in side_by_side if c["improved"]]
    unchanged = [c for c in side_by_side if not c["improved"]]

    # unique frozen authority ids and recovery accounting (re-derived)
    unique_required: set[str] = set()
    for cell in side_by_side:
        unique_required.update(cell["frozen_cell"]["required"])
    recovered: set[str] = set()
    still_missing: set[str] = set()
    for cell in side_by_side:
        recovered.update(cell["concept_seed_A1_union"]["hits_list"])
        still_missing.update(cell["concept_seed_A1_union"]["missing"])
    still_missing -= recovered

    # controls re-derived per unit
    controls_hold = all(
        concept_seed_cells[f"frozen::{c['slug']}::{c['language']}"]["A2_blanked"]["recall"]
        == concept_seed_cells[f"frozen::{c['slug']}::{c['language']}"]["A0_baseline_shipped"]["recall"]
        and concept_seed_cells[f"frozen::{c['slug']}::{c['language']}"]["A3_rotated"]["recall"] == 0.0
        for c in side_by_side
    )
    n_beats_blanked = sum(1 for c in side_by_side if concept_seed_cells[f"frozen::{c['slug']}::{c['language']}"]["candidate_beats_blanked_on_recall"])

    # coverage axis (de served unit), re-derived
    de_unit = per_unit.get("served::de-kapitalverletzung")
    if de_unit is None:
        fail("team record missing served::de-kapitalverletzung unit")
    coverage_null = (
        de_unit["coverage"]["A0_baseline_shipped"]["concept_row_counts"].get("kapitalverletzung") == 0
        and de_unit["coverage"]["A0_baseline_shipped"]["concept_row_counts"].get("uberwachungspflicht") == 0
        and de_unit["coverage"]["A1_union"]["concept_row_counts"].get("kapitalverletzung") == 0
        and de_unit["coverage"]["A1_union"]["concept_row_counts"].get("uberwachungspflicht") == 0
    )

    # ------------------------------------------------------------------ #
    # 8. divergence headline, pre-registered
    # ------------------------------------------------------------------ #
    expected = hypothesis["pre_registered_expected_result"]
    headline_checks = {
        "cells_total == 6": len(side_by_side) == expected["cells_total"] == 6,
        "cells_improved == 1": len(improved) == expected["cells_improved"] == 1,
        "improved cell is corporate-criminal-liability::fr": len(improved) == 1 and improved[0]["slug"] == "corporate-criminal-liability" and improved[0]["language"] == "fr",
        "improved 0/2 -> 1/2 via bge_BGE_142_IV_333": len(improved) == 1 and improved[0]["frozen_cell"]["hits"] == "0/2" and improved[0]["concept_seed_A1_union"]["hits"] == "1/2" and improved[0]["concept_seed_A1_union"]["hits_list"] == ["bge_BGE_142_IV_333"],
        "cells_unchanged_at_zero == 5": len(unchanged) == expected["cells_unchanged_at_zero"] == 5,
        "unique frozen authority ids == 9": len(unique_required) == expected["unique_frozen_authority_ids"] == 9,
        "ids_recovered == 1 (bge_BGE_142_IV_333)": recovered == set(expected["ids_recovered_list"]) and len(recovered) == expected["ids_recovered"],
        "ids_still_missing_everywhere == 8": len(still_missing) == expected["ids_still_missing_everywhere"] == 8,
        "coverage axis NULL": coverage_null,
        "A2 blanked == A0 on all units; A3 raises nothing": controls_hold,
        "candidate beats blanked on exactly 1 unit": n_beats_blanked == 1,
    }
    failed_checks = [k for k, v in headline_checks.items() if not v]
    if failed_checks:
        fail("divergence headline contradicts pre-registration: " + "; ".join(failed_checks))

    headline = (
        "DIVERGENCE (named as required, never smoothed over): exactly 1 of the 6 frozen fr/it "
        "authority-recall cells improves under the accepted natural-language concept-seed arm "
        "(corporate-criminal-liability::fr 0/2 -> 1/2 via bge_BGE_142_IV_333); the other 5 cells "
        "are unchanged at zero recall; 8 of the 9 unique frozen authority ids remain unrecovered "
        "everywhere; the concept-coverage axis stays null (de-kapitalverletzung 214 -> 220 rows, "
        "0 rows carrying either under-covered concept). The recovery is cell-level, not a "
        "corpus-level gap closure. Auditor caveats published beside: the recovered id was already "
        "present in the de pools (cell-level fr recovery only); latency in-budget (max per-call "
        "22.702s < 30s; A1 pass span 143.75s < 240s). This lane issues no candidates and re-tunes nothing."
    )

    # ------------------------------------------------------------------ #
    # 9. product adoption context (read-only digest) + write the record
    # ------------------------------------------------------------------ #
    adoption: dict[str, Any] = {"record": str(ADOPTION_VERDICT), "sha256": None, "decision": None}
    if ADOPTION_VERDICT.is_file():
        if sha256_file(ADOPTION_VERDICT) != ADOPTION_SHA256:
            fail("product adoption verdict digest drift")
        adoption["sha256"] = ADOPTION_SHA256
        adoption["decision"] = load_json_bytes(ADOPTION_VERDICT.read_bytes(), "adoption verdict").get("decision")

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 58,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane_question_item": "v58 ordered work (3)(b): concept-seed numbers BESIDE the frozen-benchmark cells, never in place of them, divergence named as headline",
        "freeze_first": {
            "hypothesis": HYPOTHESIS_RELPATH,
            "freeze_record": FREEZE_RELPATH,
            "input_rehashes_at_execution": rehashes,
            "frontier_blob_pins_verified": {
                FRONTIER_HARNESS: PINS["frontier_harness"],
                FRONTIER_GATE: PINS["frontier_gate"],
                FRONTIER_RULES: PINS["frontier_rules"],
            },
            "frozen_record_embedded_pins": {
                "frozen_sha256": frozen["frozen_sha256"],
                "freeze_record_sha256": frozen["freeze_record_sha256"],
            },
        },
        "frozen_cells_published_unchanged": frozen_cells,
        "concept_seed_cells": concept_seed_cells,
        "side_by_side": side_by_side,
        "divergence_headline": headline,
        "divergence_checks": headline_checks,
        "cells_improved": len(improved),
        "cells_unchanged_at_zero": len(unchanged),
        "unique_frozen_authority_ids": sorted(unique_required),
        "ids_recovered": sorted(recovered),
        "ids_still_missing_everywhere": sorted(still_missing),
        "coverage_axis_null": coverage_null,
        "controls": {
            "A2_blanked_equals_A0_on_all_units": controls_hold,
            "A3_rotated_raises_nothing_on_any_target": controls_hold,
            "candidate_beats_blanked_on_exactly_one_unit": n_beats_blanked == 1,
            "n_units_candidate_beats_blanked": n_beats_blanked,
        },
        "de_coverage": {
            "unit": "served::de-kapitalverletzung",
            "A0_rows": de_unit["coverage"]["A0_baseline_shipped"]["n_rows"],
            "A1_union_rows": de_unit["coverage"]["A1_union"]["n_rows"],
            "kapitalverletzung_rows_A0": de_unit["coverage"]["A0_baseline_shipped"]["concept_row_counts"].get("kapitalverletzung"),
            "kapitalverletzung_rows_A1_union": de_unit["coverage"]["A1_union"]["concept_row_counts"].get("kapitalverletzung"),
            "uberwachungspflicht_rows_A0": de_unit["coverage"]["A0_baseline_shipped"]["concept_row_counts"].get("uberwachungspflicht"),
            "uberwachungspflicht_rows_A1_union": de_unit["coverage"]["A1_union"]["concept_row_counts"].get("uberwachungspflicht"),
            "interpretation": "coverage axis NULL: a zero count is a retrieval signal, not proof of corpus absence",
        },
        "auditor_caveats_published_beside": [
            "C1: recovered id bge_BGE_142_IV_333 was already present in the de pools (cell-level fr recovery only)",
            "C2: coverage axis honestly null (de-kapitalverletzung 0 rows carrying either under-covered concept in A0, A1 candidate-only, A1 union and rotated control)",
            "C5: latency in-budget (max per-call 22.702s < 30s; A1 pass span 143.75s < 240s)",
            "C6: eight frozen authority ids remain missing everywhere",
        ],
        "product_adoption_context": adoption,
        "f3b_carry_forward": {
            "status": "INTACT_NOT_REOPENED" if f3b_intact else "DRIFT",
            "digests": f3b,
            "expected_digests_source": "results/evaluation/f3b_restore_disposition/39287274485.json (accepted, re-hash verified; never hand-typed)",
            "restored_matches_pre_rewrite_digest": f3b["restored_sha256"] == f3b_expected["pre_rewrite"],
            "siblings_preserved": f3b_accepted["records"]["siblings_preserved_intact"],
            "deleted": f3b_accepted["records"]["deleted"],
        },
        "unserved_packet": packet_state,
        "no_candidate_no_retune": {
            "new_thresholds": 0,
            "new_bars": 0,
            "new_gates": 0,
            "frozen_files_edited": 0,
            "candidates_issued": 0,
            "packet_verdicts_computed": 0,
        },
        "claim_ceiling": hypothesis["claim_ceiling"],
        "verdict": "CONCEPT_SEED_BESIDE_FROZEN_CELLS_PUBLISHED",
        "exit_code": 0,
    }

    out_dir = REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        shown = out_path.relative_to(REPO_ROOT)
    except ValueError:
        shown = out_path
    print(f"published {shown}")
    print(f"verdict CONCEPT_SEED_BESIDE_FROZEN_CELLS_PUBLISHED: 1/6 cells improved, 5/6 unchanged at zero, "
          f"{len(recovered)}/9 ids recovered, {len(still_missing)}/9 still missing, coverage axis null")
    return 0


if __name__ == "__main__":
    sys.exit(main())
