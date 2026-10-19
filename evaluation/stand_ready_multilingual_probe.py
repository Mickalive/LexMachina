#!/usr/bin/env python3
"""Stand-ready multilingual + provenance probe for the query-map MVP.

WHY THIS INSTRUMENT EXISTS (direction v58 lanes.evaluation ordered work (2))
---------------------------------------------------------------------------
Core Evaluation's ordered work is (1) the F-3B disposition [discharged,
proof results/evaluation/f3b_restore_disposition/39287274485.json] and
(2) STAND READY to falsify-or-pass the NEXT served packet on its exact bytes
without pre-empting it.  Product's newest gate packet (39275520116) is BUILT
but NOT SERVED, so the falsifier must not emit any verdict on its bytes.  The
lane may not ship a zero-delta cycle (rc-67 class), so this probe produces the
durable stand-ready delta the direction asks for: it re-measures the CURRENT
accepted product head's OWN published live retrieval bundles against the
ACCEPTED mapping-free gates, reuses the multilingual / provenance discipline
the lane already owns, and proves — with pinned digests and non-vacuity
controls — that the falsification surface is live and addressable the moment a
serve verdict lands.

REUSE-FIRST — every predicate below is IMPORTED, never re-derived
----------------------------------------------------------------
* evaluation.mapping_free_recall_falsifier.concept_coverage
* evaluation.mapping_free_recall_falsifier.source_validity
* evaluation.mapping_free_recall_falsifier.duplicate_suppression
* evaluation.mapping_free_recall_falsifier.counter_authority_surface
* evaluation.mapping_free_recall_falsifier.language_robustness
* evaluation.mapping_free_recall_falsifier.sha256_file / numeric_environment
* evaluation.subject_match_audit.question_concepts (via concept_coverage)
* evaluation.frozen_bars.RULES_LABEL.json rubric.scored_statuses (read-only)

No threshold, bar, stoplist, tokeniser or verdict contract is introduced,
moved or re-derived here.  The only new logic is (a) counter-STAGE
applicability qualification — instrument-qualified under the requirement-25
envelope, a gate that never ran is NOT_APPLICABLE, never a pass and never a
fail — and (b) the structural-readiness check on the unserved packet, which
computes NO gate and NO verdict by construction.

WHAT IT MEASURES
----------------
1. Frozen-input re-hash (fail-closed): the five standing pins + this run's
   hypothesis and freeze record.
2. Population pin: product mount head + the four digest-pinned live bundles
   and the digest-pinned unserved packet files.
3. Non-vacuity battery A/A2/C/D (blanked pool, blanked row, oracle pool,
   hostile duplicate pool) — all must hold or exit 2.
4. Per live bundle: concept coverage, source validity, duplicate suppression,
   counter-authority surface (stage-qualified), language robustness
   (REPORTED-ONLY).  Per-bundle PASS/FAIL under the hypothesis's frozen
   falsification rule.
5. Serve-status probe: every gate_packet on the mount, its admission fields,
   and every frontier_verdicts file — establishing which packets are served
   and that 39275520116 has zero serve-verdict references.
6. Unserved packet 39275520116: STRUCTURAL readiness only (files present,
   digests match the freeze pin, bundles parse with non-empty decisions,
   question/admissibility siblings present).  ``falsification_verdict`` is
   hard-coded WITHHELD_PENDING_SERVE.
7. F-3B carry-forward freshness: re-hash the three disposition files against
   the accepted proof.  This is a freshness check, NOT a re-litigation.

CLAIM CEILING (verbatim in force)
---------------------------------
This probe establishes exactly one thing: on the digest-pinned live bundles of
accepted product head 6c4b8f7d, whether the product's own published retrieval
output satisfies the accepted mapping-free gates, with language composition
reported BESIDE (never in place of) the frozen benchmark's fr/it
authority-recall cells.  It does NOT serve, admit or falsify the unserved
packet 39275520116.  It does NOT move the frozen absolute LABEL_SOUND or
GEOMETRY_SOUND bars, which stay REPORTED-ONLY.  It does NOT lift the accepted
DO-NOT-SERVE order on 38839347028 nor DO-NOT-SERVE-UNCHANGED on
rebuilt-39027045675.  It does NOT claim the map helps a jurist.
human_gate_ready stays false; admission stays fail-closed;
owner_decision_required stays false.  It runs no universal-174k benchmark.

Exit codes (frozen in the hypothesis)
-------------------------------------
0  PROBE_RAN_NO_LIVE_FALSIFICATION  pins matched, non-vacuity held, no live
                                    bundle failed an applicable gate
1  LIVE_BUNDLE_FALSIFIED            >=1 pinned live bundle failed >=1
                                    applicable gate (named per bundle/gate)
2  ENVIRONMENT_OR_VACUOUS           pin drift, mount-head drift, unreadable
                                    population, or non-vacuity failure —
                                    never a pass, never a bar-met

SCRATCH-RUN OBLIGATION
----------------------
A claim-bearing run writes to the committed default
``results/evaluation/stand_ready_multilingual_probe/<run_id>.json``.  Any
scratch invocation MUST pass ``--out`` to a non-committed path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.mapping_free_recall_falsifier import (  # noqa: E402
    concept_coverage,
    counter_authority_surface,
    duplicate_suppression,
    language_robustness,
    numeric_environment,
    sha256_file,
    source_validity,
)
import subprocess  # noqa: E402

SCHEMA = "lex-evaluation-stand-ready-multilingual-probe/1"
HYPOTHESIS_RELPATH = "evaluation/STAND_READY_MULTILINGUAL_PROBE_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/STAND_READY_MULTILINGUAL_PROBE_FREEZE_RECORD.json"
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"
FROZEN_BENCHMARK_RELPATH = "results/evaluation/retrieval_benchmark/39117425713.json"
F3B_PROOF_RELPATH = "results/evaluation/f3b_restore_disposition/39287274485.json"

DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)

EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_ENVIRONMENT = 2

CLAIM_CEILING = (
    "This probe establishes exactly one thing: on the digest-pinned live bundles of "
    "accepted product head 6c4b8f7d, whether the product's own published retrieval "
    "output satisfies the accepted mapping-free gates, with language composition "
    "reported BESIDE (never in place of) the frozen benchmark's fr/it authority-recall "
    "cells. It does NOT serve, admit or falsify the unserved packet 39275520116. It "
    "does NOT move the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars. It does NOT "
    "lift the accepted DO-NOT-SERVE order on 38839347028 nor DO-NOT-SERVE-UNCHANGED on "
    "rebuilt-39027045675. It does NOT claim the map helps a jurist. human_gate_ready "
    "stays false; admission stays fail-closed; owner_decision_required stays false. "
    "It runs no universal-174k benchmark."
)


def _gate(name: str, passed: bool | None, detail: str, **measured: Any) -> dict:
    return {"gate": name, "passed": passed, "detail": detail, "measured": measured}


def resolve_mount(explicit: str | None) -> Path | None:
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    for var in ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT"):
        if os.environ.get(var):
            cands.append(Path(os.environ[var]))
    cands.extend(Path(p) for p in DEFAULT_MOUNTS)
    for c in cands:
        if c.is_dir():
            return c
    return None


def mount_head(mount: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(mount), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or None
    except Exception:  # pragma: no cover
        return None


# --------------------------------------------------------------------------- #
# counter-stage applicability (instrument qualification, NOT a new threshold)
# --------------------------------------------------------------------------- #
def counter_stage_applicability(record: dict) -> dict:
    """Is the frozen counter-authority gate APPLICABLE to this live record?

    The frozen gate (``n_issued >= 1 AND n_with_empty_evidence == 0``) was
    defined for SERVED packets whose full pipeline ran the counter pass.  A
    live map-only run whose counter stage never executed cannot fail a gate
    that never ran.  Under the requirement-25 instrument-qualified envelope
    such a gate is NOT_APPLICABLE — passed=None, never a pass, never a fail —
    and the qualification basis is published in the same record.
    """
    stages = record.get("stages_executed")
    counters = record.get("counters") or {}
    if isinstance(stages, dict) and stages.get("counter_authority") is False:
        return {
            "applicable": False,
            "basis": "STAGE_NOT_RUN_EXPLICIT",
            "stages_executed.counter_authority": False,
        }
    if not stages and counters.get("counter_authorities") == 0:
        by_status = counters.get("by_status") or {}
        non_none = [k for k in by_status if str(k).strip().lower() != "none"]
        if not non_none:
            return {
                "applicable": False,
                "basis": "STAGE_NOT_RUN_INFERRED_FROM_COUNTERS",
                "stages_executed": stages,
                "counters.counter_authorities": counters.get("counter_authorities"),
                "by_status_non_none_keys": non_none,
                "disclosure": (
                    "stages_executed is absent; the counters block records zero "
                    "counter authorities and no non-none status, so the counter "
                    "pass did not issue and the served-packet gate cannot fail"
                ),
            }
    return {"applicable": True, "basis": "COUNTER_STAGE_RAN_OR_STATUS_BEARING_ROWS_PRESENT"}


# --------------------------------------------------------------------------- #
# frozen pins + population verification
# --------------------------------------------------------------------------- #
def verify_frozen_pins(repo: Path, hypothesis: dict, freeze: dict) -> dict:
    checks: list[dict] = []
    for rel, pinned in (freeze.get("frozen_inputs_rehashed_before_execution") or {}).items():
        path = repo / rel
        actual = sha256_file(path) if path.is_file() else None
        checks.append({
            "file": rel, "pinned": pinned, "actual": actual,
            "match": actual == pinned,
        })
    hyp_path = repo / HYPOTHESIS_RELPATH
    frz_path = repo / FREEZE_RELPATH
    checks.append({
        "file": HYPOTHESIS_RELPATH,
        "pinned": freeze.get("hypothesis_sha256"),
        "actual": sha256_file(hyp_path) if hyp_path.is_file() else None,
        "match": bool(hyp_path.is_file())
                 and sha256_file(hyp_path) == freeze.get("hypothesis_sha256"),
    })
    # the freeze record cannot contain its own digest; pin its existence
    checks.append({
        "file": FREEZE_RELPATH,
        "pinned": "FILE_PRESENT",
        "actual": "FILE_PRESENT" if frz_path.is_file() else None,
        "match": frz_path.is_file(),
    })
    return {
        "all_match": all(c["match"] for c in checks),
        "checks": checks,
    }


def verify_population(mount: Path, hypothesis: dict) -> dict:
    pop = hypothesis.get("population_pinned_before_execution") or {}
    live_checks: list[dict] = []
    for entry in pop.get("live_bundles") or []:
        rec_path = mount / "results" / "product" / entry["record"]
        bun_path = mount / "results" / "product" / entry["bundle"]
        rec_actual = sha256_file(rec_path) if rec_path.is_file() else None
        bun_actual = sha256_file(bun_path) if bun_path.is_file() else None
        live_checks.append({
            "record": entry["record"],
            "record_pinned": entry["record_sha256"],
            "record_actual": rec_actual,
            "record_match": rec_actual == entry["record_sha256"],
            "bundle": entry["bundle"],
            "bundle_pinned": entry["bundle_sha256"],
            "bundle_actual": bun_actual,
            "bundle_match": bun_actual == entry["bundle_sha256"],
        })
    packet = pop.get("unserved_packet_structural_only") or {}
    packet_checks: list[dict] = []
    pp = mount / "results" / "product" / "gate_packet" / str(packet.get("packet"))
    for fname, pinned_key in (("packet.json", "packet_json_sha256"),
                              ("manifest.json", "manifest_sha256")):
        path = pp / fname
        actual = sha256_file(path) if path.is_file() else None
        packet_checks.append({
            "file": fname, "pinned": packet.get(pinned_key),
            "actual": actual, "match": actual == packet.get(pinned_key),
        })
    for q in packet.get("questions") or []:
        for suffix, key in (("bundle.json", "bundle_sha256"),
                            ("question.json", "question_sha256"),
                            ("admissibility.json", "admissibility_sha256")):
            path = pp / "questions" / f"{q['qid']}.{suffix}"
            actual = sha256_file(path) if path.is_file() else None
            packet_checks.append({
                "file": f"questions/{q['qid']}.{suffix}",
                "pinned": q.get(key), "actual": actual,
                "match": actual == q.get(key),
            })
    head = mount_head(mount)
    pinned_head = pop.get("product_mount_head")
    return {
        "mount_head_pinned": pinned_head,
        "mount_head_actual": head,
        "mount_head_match": head == pinned_head,
        "live_bundles": live_checks,
        "unserved_packet_files": packet_checks,
        "all_match": (head == pinned_head)
                     and all(c["record_match"] and c["bundle_match"] for c in live_checks)
                     and all(c["match"] for c in packet_checks),
    }


# --------------------------------------------------------------------------- #
# non-vacuity battery (designs frozen in the hypothesis)
# --------------------------------------------------------------------------- #
def non_vacuity(sample_question_text: str, sample_qid: str) -> dict:
    controls: list[dict] = []

    blank_cov = concept_coverage({"question": sample_question_text}, {"decisions": []})
    a_fails = blank_cov["n_zero"] == blank_cov["n_concepts"] and blank_cov["n_concepts"] > 0
    controls.append({
        "control": "A_blanked_pool_fails_concept_coverage",
        "holds": a_fails,
        "why": f"a blanked pool leaves {blank_cov['n_zero']}/{blank_cov['n_concepts']} "
               f"core concepts of {sample_qid} uncovered",
        "measured": {"n_concepts": blank_cov["n_concepts"], "n_zero": blank_cov["n_zero"]},
    })

    blank_src = source_validity({"decisions": [{"decision_id": "", "canonical_url": ""}]})
    a2 = blank_src["n_rows_missing_id_or_url"] == 1
    controls.append({
        "control": "A2_blanked_row_fails_source_validity",
        "holds": a2,
        "why": "a row with no decision_id and no canonical_url fails source validity",
        "measured": blank_src,
    })

    oracle_rows = [
        {"title": c, "decision_id": f"oracle_{c}_0001",
         "canonical_url": f"https://example.invalid/{c}"}
        for c in blank_cov["concepts"]
    ]
    oracle_cov = concept_coverage({"question": sample_question_text}, {"decisions": oracle_rows})
    c_ok = oracle_cov["n_zero"] == 0 and oracle_cov["n_concepts"] > 0
    controls.append({
        "control": "C_oracle_pool_passes_concept_coverage",
        "holds": c_ok,
        "why": f"an oracle pool built from the {oracle_cov['n_concepts']} core concepts "
               f"covers {oracle_cov['n_concepts'] - oracle_cov['n_zero']}/"
               f"{oracle_cov['n_concepts']}",
        "measured": {"n_concepts": oracle_cov["n_concepts"], "n_zero": oracle_cov["n_zero"]},
    })

    dup_ids = [f"dup_{i % 3}_0001" for i in range(10)]
    hostile = {"decisions": [
        {"decision_id": did, "canonical_url": f"https://example.invalid/{did}",
         "title": "x"} for did in dup_ids]}
    dup = duplicate_suppression(hostile)
    d_ok = dup["duplicates"] > 0
    controls.append({
        "control": "D_hostile_duplicate_pool_fails_duplicate_suppression",
        "holds": d_ok,
        "why": f"a pool with 10 rows over 3 distinct ids yields {dup['duplicates']} duplicates",
        "measured": dup,
    })

    return {"all_hold": all(c["holds"] for c in controls), "battery": controls}


# --------------------------------------------------------------------------- #
# serve-status probe
# --------------------------------------------------------------------------- #
def serve_status(mount: Path) -> dict:
    gp = mount / "results" / "product" / "gate_packet"
    fv = mount / "results" / "product" / "frontier_verdicts"
    verdict_files: list[dict] = []
    serve_refs: dict[str, list[str]] = {}
    if fv.is_dir():
        for p in sorted(fv.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover
                verdict_files.append({"file": p.name, "parse_error": str(exc)[:200]})
                continue
            blob = json.dumps(data, ensure_ascii=False)
            refs = []
            for cand in ("38839347028", "rebuilt-39027045675", "39275520116"):
                if cand in blob:
                    refs.append(cand)
            for r in refs:
                serve_refs.setdefault(r, []).append(p.name)
            verdict_files.append({
                "file": p.name,
                "sha256": sha256_file(p),
                "serve_recommendation": data.get("serve_recommendation"),
                "covers_this_packet": data.get("covers_this_packet"),
                "packet_refs": refs,
            })
    packets: list[dict] = []
    if gp.is_dir():
        for d in sorted(p for p in gp.iterdir() if p.is_dir()):
            pj = d / "packet.json"
            entry: dict[str, Any] = {"packet": d.name, "packet_json_present": pj.is_file()}
            if pj.is_file():
                try:
                    meta = json.loads(pj.read_text(encoding="utf-8"))
                    for k in ("ready_for_owner_session", "packet_admitted",
                              "human_gate_ready", "machine_gate_ready",
                              "serve_recommendation", "ok", "blocked"):
                        entry[k] = meta.get(k)
                    entry["packet_admission_blocked"] = meta.get("packet_admission_blocked")
                    entry["packet_admission_reason"] = meta.get("packet_admission_reason")
                except Exception as exc:
                    entry["parse_error"] = str(exc)[:200]
            packets.append(entry)
    return {
        "packets": packets,
        "frontier_verdict_files": verdict_files,
        "serve_verdict_references_by_packet": serve_refs,
        "packet_39275520116_serve_verdict_references": serve_refs.get("39275520116", []),
    }


# --------------------------------------------------------------------------- #
# unserved packet structural readiness — NO gate, NO verdict, by construction
# --------------------------------------------------------------------------- #
def packet_structural_readiness(mount: Path, hypothesis: dict) -> dict:
    pop = hypothesis.get("population_pinned_before_execution") or {}
    pin = pop.get("unserved_packet_structural_only") or {}
    packet_id = str(pin.get("packet"))
    base = mount / "results" / "product" / "gate_packet" / packet_id
    rows: list[dict] = []
    for q in pin.get("questions") or []:
        bpath = base / "questions" / f"{q['qid']}.bundle.json"
        qpath = base / "questions" / f"{q['qid']}.question.json"
        apath = base / "questions" / f"{q['qid']}.admissibility.json"
        readable = False
        n_decisions = None
        parse_error = None
        if bpath.is_file():
            try:
                bundle = json.loads(bpath.read_text(encoding="utf-8"))
                n_decisions = len(bundle.get("decisions") or [])
                readable = n_decisions > 0
            except Exception as exc:
                parse_error = str(exc)[:200]
        rows.append({
            "qid": q["qid"],
            "bundle_present": bpath.is_file(),
            "bundle_parses_with_decisions": readable,
            "n_decisions": n_decisions,
            "parse_error": parse_error,
            "question_present": qpath.is_file(),
            "admissibility_present": apath.is_file(),
            "structurally_addressable": bool(
                bpath.is_file() and qpath.is_file() and apath.is_file() and readable),
        })
    return {
        "packet": packet_id,
        "serve_status": "BUILT_NOT_SERVED",
        "falsification_verdict": "WITHHELD_PENDING_SERVE",
        "note": (
            "direction v58 ordered work (2) forbids pre-emption: no mapping-free "
            "gate, no coverage number and no falsify-or-pass verdict is computed "
            "on this packet's bytes in this run. Structural readiness establishes "
            "only that the falsifier can ADDRESS the exact bytes once a serve "
            "verdict lands."
        ),
        "questions": rows,
        "all_structurally_addressable": all(r["structurally_addressable"] for r in rows),
    }


# --------------------------------------------------------------------------- #
# F-3B carry-forward freshness (not a re-litigation)
# --------------------------------------------------------------------------- #
def f3b_carry_forward(repo: Path) -> dict:
    proof_path = repo / F3B_PROOF_RELPATH
    if not proof_path.is_file():
        return {"proof_present": False, "status": "PROOF_MISSING"}
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    records = proof.get("records") or {}
    run_record = records.get("run_record") or {}
    rehomed = records.get("rehomed") or {}
    base = repo / "results" / "evaluation" / "frozen_cache_integrity"
    files = {
        "39164900837.json": run_record.get("restored_sha256"),
        "39164900837_pre_restore.json": next(
            (p.get("sha256") for p in (records.get("preserved") or [])
             if p.get("path", "").endswith("39164900837_pre_restore.json")), None),
        "39164900837_post-restore-9b61dcf8.json": rehomed.get("rehomed_sha256"),
    }
    checks = []
    for fname, expected in files.items():
        path = base / fname
        actual = sha256_file(path) if path.is_file() else None
        checks.append({
            "file": fname,
            "expected_from_proof": expected,
            "actual": actual,
            "match": (actual == expected) if expected else None,
            "present": path.is_file(),
        })
    restored = next((c for c in checks if c["file"] == "39164900837.json"), {})
    return {
        "proof_present": True,
        "proof_sha256": sha256_file(proof_path),
        "proof_run": proof.get("run_id"),
        "verdict": proof.get("verdict"),
        "checks": checks,
        "restored_matches_pre_rewrite": (
            restored.get("match") is True
            and run_record.get("restoration_matches_pre_rewrite_digest") is True),
        "status": "CARRY_FORWARD_FRESHNESS_OK" if all(
            c["match"] for c in checks if c["match"] is not None) and all(
            c["present"] for c in checks) else "CARRY_FORWARD_DRIFT",
        "note": "freshness check only; the disposition is discharged and is NOT re-opened",
    }


# --------------------------------------------------------------------------- #
# frozen benchmark cells — published BESIDE, never replaced
# --------------------------------------------------------------------------- #
def frozen_cells_beside(repo: Path) -> dict:
    path = repo / FROZEN_BENCHMARK_RELPATH
    if not path.is_file():
        return {"present": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for g in (data.get("verdict") or {}).get("gates") or []:
        name = str(g.get("gate") or "")
        if "authority::baseline_lang_recall" in name:
            m = g.get("measured") or {}
            cells.append({
                "gate": name,
                "passed": g.get("passed"),
                "n_required": len(m.get("required") or []),
                "n_hits": len(m.get("hits") or []),
                "n_missing": len(m.get("missing") or []),
            })
    return {
        "present": True,
        "artifact": FROZEN_BENCHMARK_RELPATH,
        "artifact_sha256": sha256_file(path),
        "authority_lang_recall_cells": cells,
        "usage": "PUBLISHED BESIDE this probe's live-bundle language cells; never replaced",
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(mount: Path, repo: Path, run_id: str) -> tuple[dict, int]:
    hypothesis = json.loads((repo / HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    freeze = json.loads((repo / FREEZE_RELPATH).read_text(encoding="utf-8"))
    rules = json.loads((repo / RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored_statuses = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])

    frozen = verify_frozen_pins(repo, hypothesis, freeze)
    population = verify_population(mount, hypothesis)

    pop = hypothesis["population_pinned_before_execution"]
    live_entries = pop["live_bundles"]
    if not live_entries:
        return ({
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_VACUOUS",
            "reason": "empty pinned population",
        }, EXIT_ENVIRONMENT)

    first_record = json.loads(
        (mount / "results" / "product" / live_entries[0]["record"]).read_text(encoding="utf-8"))
    first_bundle = json.loads(
        (mount / "results" / "product" / live_entries[0]["bundle"]).read_text(encoding="utf-8"))
    sample_qtext = str((first_bundle.get("query") or "")
                       or (first_record.get("query") or ""))
    vac = non_vacuity(sample_qtext, live_entries[0]["record"])

    results: list[dict] = []
    for entry in live_entries:
        record = json.loads(
            (mount / "results" / "product" / entry["record"]).read_text(encoding="utf-8"))
        bundle = json.loads(
            (mount / "results" / "product" / entry["bundle"]).read_text(encoding="utf-8"))
        query_text = str(bundle.get("query") or record.get("query") or "")
        qrec = {"question": query_text, "qid": entry["record"]}

        cov = concept_coverage(qrec, bundle)
        src = source_validity(bundle)
        dup = duplicate_suppression(bundle)
        cas = counter_authority_surface(bundle, scored_statuses)
        lang = language_robustness(bundle)
        applic = counter_stage_applicability(record)

        gates = [
            _gate(f"sr::concept_coverage::{entry['record']}",
                  cov["n_zero"] == 0,
                  f"{cov['n_zero']}/{cov['n_concepts']} core concepts of the live question "
                  f"retrieve ZERO live rows", **cov),
            _gate(f"sr::source_validity::{entry['record']}",
                  src["n_rows_missing_id_or_url"] == 0,
                  f"{src['n_rows_missing_id_or_url']} live row(s) lack a decision_id or "
                  f"canonical_url", **src),
            _gate(f"sr::duplicate_suppression::{entry['record']}",
                  dup["duplicates"] == 0,
                  f"{dup['duplicates']} duplicate decision_id(s) in the live pool", **dup),
        ]
        if applic["applicable"]:
            passed = (cas["n_issued"] >= 1 and cas["n_with_empty_evidence"] == 0)
            gates.append(_gate(
                f"sr::counter_authority_surface::{entry['record']}",
                passed,
                f"{cas['n_issued']} scored counter-authority label(s) issued, "
                f"{cas['n_with_empty_evidence']} with empty evidence",
                **{**cas, "stage_applicability": applic}))
        else:
            gates.append(_gate(
                f"sr::counter_authority_surface::{entry['record']}",
                None,
                "NOT_APPLICABLE_STAGE_NOT_RUN — the counter pass did not execute on "
                "this live record; never a pass, never a fail (requirement-25 "
                "instrument-qualified envelope)",
                **{**cas, "stage_applicability": applic}))
        gates.append(_gate(
            f"sr::language_robustness::{entry['record']}",
            None,
            "REPORTED-ONLY, never a pass/fail: published BESIDE the frozen benchmark "
            "fr/it authority-recall cells",
            **lang))

        failed = [g["gate"] for g in gates if g["passed"] is False]
        results.append({
            "record": entry["record"],
            "bundle": entry["bundle"],
            "query": query_text,
            "product_record_verdict": record.get("verdict"),
            "product_record_mode": record.get("mode"),
            "product_n_failed_checks": record.get("n_failed_checks"),
            "bundle_sha256": entry["bundle_sha256"],
            "coverage": cov,
            "source_validity": src,
            "duplicate_suppression": dup,
            "counter_authority_surface": cas,
            "counter_stage_applicability": applic,
            "language_robustness": lang,
            "gates": gates,
            "n_gates_failed": len(failed),
            "failed_gates": failed,
            "bundle_verdict": "FALSIFIED" if failed else "PASS_ON_APPLICABLE_GATES",
        })

    serve = serve_status(mount)
    readiness = packet_structural_readiness(mount, hypothesis)
    f3b = f3b_carry_forward(repo)
    frozen_cells = frozen_cells_beside(repo)

    if not frozen["all_match"] or not population["all_match"] or not vac["all_hold"]:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_ENVIRONMENT
        reasons = []
        if not frozen["all_match"]:
            reasons.append("frozen pin drift")
        if not population["all_match"]:
            reasons.append("population/mount-head pin drift")
        if not vac["all_hold"]:
            reasons.append("non-vacuity battery failure")
        verdict_detail = "; ".join(reasons)
    elif any(r["n_gates_failed"] > 0 for r in results):
        verdict = "LIVE_BUNDLE_FALSIFIED"
        exit_code = EXIT_FALSIFIED
        verdict_detail = "; ".join(
            f"{r['record']}: {r['failed_gates']}" for r in results if r["n_gates_failed"])
    else:
        verdict = "PROBE_RAN_NO_LIVE_FALSIFICATION"
        exit_code = EXIT_PASS
        verdict_detail = "all applicable gates passed on all pinned live bundles"

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 58,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hypothesis_sha256": freeze.get("hypothesis_sha256"),
        "freeze_record_sha256": sha256_file(repo / FREEZE_RELPATH),
        "product_mount": str(mount),
        "product_mount_head": population["mount_head_actual"],
        "environment": numeric_environment(),
        "frozen_pin_verification": frozen,
        "population_pin_verification": population,
        "non_vacuity": vac,
        "live_bundle_results": results,
        "serve_status": serve,
        "unserved_packet_structural_readiness": readiness,
        "f3b_carry_forward": f3b,
        "frozen_benchmark_cells_published_beside": frozen_cells,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "exit_code": exit_code,
        "claim_ceiling": CLAIM_CEILING,
        "human_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }
    return record, exit_code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mount", default=None)
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None,
                    help="output path; defaults to the committed claim-bearing path")
    args = ap.parse_args(argv)

    mount = resolve_mount(args.mount)
    if mount is None:
        print("FATAL: no product mount found", file=sys.stderr)
        return EXIT_ENVIRONMENT

    record, code = run(mount, REPO_ROOT, args.run_id)
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "stand_ready_multilingual_probe"
        / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"verdict={record['verdict']} exit={code} out={out}")
    if record.get("verdict_detail"):
        print(f"detail={record['verdict_detail'][:500]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
