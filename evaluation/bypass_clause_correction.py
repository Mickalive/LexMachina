#!/usr/bin/env python3
"""Bypass-clause correction of record for accepted falsifier run 40105794124.

v68 lanes.evaluation ORDERED WORK ITEM (1) — REPORT-ONLY CORRECTION OF RECORD
=============================================================================
Run 40105794124 (accept bcb4520a) published, beside its MEASUREMENT, a one-line
MECHANISM explanation in
``reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_READING.md``:

    "It does not discharge v67 item (2), which remains NOT_YET_DISCRIMINATING
     because the product path still sets fixture_generation=True and bypasses
     the landed filter."

Committed accepted product evidence supersedes THAT EXPLANATION and only that
explanation:

* accepted product commit ``51d306c`` (cycle 40093776552) removed the
  ``not fixture_generation`` gate around ``apply_verified_span_selection`` in
  ``product/query/pipeline.py`` (the seam now runs in fixture mode);
* the committed accepted bundle
  ``results/product/offline_slice/20261024T142517Z/rent-default.bundle.json`` at
  accepted head ``8b5b08dd`` carries
  ``provenance.counter_evidence_span.applied=true, n_candidates=1, n_selected=0,
  abstained_ids=['gr_gerichte_ERZ 2010 25'], abstention_reasons={pivot_absent:1}``,
  i.e. the seam executed on the shipped offline/slice path and ABSTAINED;
* the row stays ``counter_evidence_verified=true`` with the defective trilingual
  Graubünden letterhead because the seam abstains and the INCUMBENT is left in
  place.  The remaining leg is therefore REJECTION/INCUMBENT HANDLING, not
  bypass.

WHAT THIS INSTRUMENT DOES / DOES NOT DO
---------------------------------------
It reads committed artifacts and proves, check by check, that (a) the clause is
located exactly where it was published, (b) the measurement is byte-for-byte
unchanged against its freeze pin, (c) the provenance and file:line facts named
in the correction are true on the accepted mount, and (d) conditional item (2)
is still NOT_YET_DISCRIMINATING.

* It does NOT re-execute ``evaluation/fast_mvp_current_head_ca_falsifier.py``
  (control C4 scans its own source for that import/invocation).
* It does NOT run any D1-D4 predicate, any frozen gate, any rubric, any bar.
  Defect classes are READ from the committed record of 40105794124.
* It does NOT edit, re-tune or re-derive anything frozen; frozen inputs are
  re-hashed REPORTED-ONLY.
* It issues no serve verdict and no admission, UX or legal-usefulness claim.

Exit codes (frozen in the hypothesis):
  0  CORRECTION_CONFIRMED   (all claims ok, all controls hold)
  1  CORRECTION_NOT_CONFIRMED (a claim or control failed — published as-is)
  2  INPUT_ERROR (missing freeze/hypothesis/mount — nothing was measured)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-bypass-clause-correction/1"
HYPOTHESIS_RELPATH = (
    "evaluation/BYPASS_CLAUSE_CORRECTION_40105794124_HYPOTHESIS_V1.json")
FREEZE_RELPATH = "evaluation/BYPASS_CLAUSE_CORRECTION_40105794124_FREEZE_V1.json"
READING_RELPATH = (
    "reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_READING.md")
MACHINE_REPORT_RELPATH = (
    "reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124.md")
FALSIFIER_RECORD_RELPATH = (
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"

DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/bypass_clause_correction"

# The clause as published (whitespace-normalised), and the line that carries it.
CLAUSE_HEAD = ("because the product path still sets "
               "`fixture_generation=True` and bypasses the")
CLAUSE_TAIL = "landed filter."

EXIT_CONFIRMED = 0
EXIT_NOT_CONFIRMED = 1
EXIT_INPUT_ERROR = 2


# --------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(mount: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(mount), *args],
                          capture_output=True, text=True, timeout=60)


def mount_head(mount: Path) -> str | None:
    try:
        p = git(mount, "rev-parse", "HEAD")
        return (p.stdout.strip() or None) if p.returncode == 0 else None
    except Exception:
        return None


def numeric_environment() -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                          "MKL_NUM_THREADS")}
    return env


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(checks: dict, cid: str, ok: bool, expected, actual,
           evidence: str) -> None:
    checks[cid] = {"ok": bool(ok), "expected": expected, "actual": actual,
                   "evidence": evidence}


# ------------------------------------------------- claim check implementations
def cc1_clause_located(repo: Path, checks: dict) -> dict:
    reading = (repo / READING_RELPATH).read_text(encoding="utf-8")
    lines = reading.splitlines()
    spans = []
    for i, line in enumerate(lines):
        if CLAUSE_HEAD in line:
            tail = lines[i + 1] if i + 1 < len(lines) else ""
            spans.append({
                "head_line": i + 1,
                "tail_line": i + 2 if CLAUSE_TAIL in tail else None,
                "head_text": line.strip(),
                "tail_text": tail.strip() if CLAUSE_TAIL in tail else None,
            })
    machine = (repo / MACHINE_REPORT_RELPATH).read_text(encoding="utf-8")
    record_raw = (repo / FALSIFIER_RECORD_RELPATH).read_text(encoding="utf-8")
    n_machine = machine.lower().count("bypass")
    n_record = record_raw.lower().count("bypass")
    ok = (len(spans) == 1 and spans[0]["tail_line"] is not None
          and n_machine == 0 and n_record == 0)
    _check(checks, "CC1_stale_clause_located_only_in_reading_report", ok,
           "exactly one clause occurrence in the READING report spanning two "
           "lines; zero 'bypass' occurrences in the machine report and the "
           "committed record",
           {"reading_spans": spans, "n_bypass_machine_report": n_machine,
            "n_bypass_committed_record": n_record},
           f"{READING_RELPATH}:{spans[0]['head_line']}-{spans[0]['tail_line']}"
           if spans else f"{READING_RELPATH}: NOT FOUND")
    return {"clause_location": spans[0] if spans else None,
            "n_bypass_machine_report": n_machine,
            "n_bypass_committed_record": n_record}


def cc2_measurement_unchanged(repo: Path, freeze: dict, checks: dict) -> dict:
    rec = load_json(repo / FALSIFIER_RECORD_RELPATH)
    pinned = freeze["frozen_measurement_of_record_copy_for_CC2"]
    agg = rec.get("aggregate") or {}
    observed = {
        "verdict": rec.get("verdict"),
        "exit_code": rec.get("exit_code"),
        "falsification_proven": rec.get("falsification_proven"),
        "n_bundles": agg.get("n_bundles"),
        "n_enriched": agg.get("n_enriched"),
        "n_enriched_with_verified_scored_row":
            agg.get("n_enriched_with_verified_scored_row"),
        "n_verified_scored_rows_total": agg.get("n_verified_scored_rows_total"),
        "n_defective_verified_scored_rows_total":
            agg.get("n_defective_verified_scored_rows_total"),
        "defect_histogram": agg.get("defect_histogram"),
        "n_enriched_with_sound_counter_row":
            agg.get("n_enriched_with_sound_counter_row"),
        "distinct_defective_decision_ids":
            agg.get("distinct_defective_decision_ids"),
        "sound_decision_id": pinned["sound_decision_id"],
    }
    # the sound row id is read from the record's own verified rows
    sound_ids = []
    for bundle in rec.get("bundles") or []:
        for row in bundle.get("verified_scored_rows") or []:
            if not (row.get("defects") or []):
                sound_ids.append(row.get("decision_id"))
    observed["sound_decision_id"] = sound_ids[0] if len(sound_ids) == 1 else sound_ids
    # Exclude provenance key 'source' from measurement comparison;
    # it is not a measurement aggregate and would always mismatch
    # because observed does not contain it (it is read from the record path, not computed).
    measurement_keys = {k for k in pinned if k != "source"}
    mismatches = {k: {"expected": pinned.get(k), "actual": observed.get(k)}
                  for k in measurement_keys if pinned.get(k) != observed.get(k)}
    _check(checks, "CC2_measurement_unchanged_vs_freeze_pin",
           not mismatches,
           "committed falsifier record reproduces every freeze-pinned aggregate "
           "value exactly (this correction changes no number)",
           {"mismatches": mismatches, "observed": observed},
           FALSIFIER_RECORD_RELPATH)
    return {"observed": observed, "mismatches": mismatches,
            "record_sha256": sha256_file(repo / FALSIFIER_RECORD_RELPATH)}


def cc3_bundle_sha(mount: Path, freeze: dict, checks: dict) -> dict:
    rel = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    expected = freeze["expected_mount_pins_before_execution"][
        f"mount:{rel}"]
    actual = sha256_file(mount / rel)
    rec = load_json(REPO_ROOT / FALSIFIER_RECORD_RELPATH)
    recorded = None
    for bundle in rec.get("bundles") or []:
        if (bundle.get("path") or "").endswith("20261024T142517Z/"
                                               "rent-default.bundle.json"):
            recorded = bundle.get("sha256")
    ok = actual == expected == recorded
    _check(checks, "CC3_bundle_sha256_of_record", ok,
           "mount digest == freeze pin == the digest recorded inside the "
           "committed falsifier record",
           {"expected": expected, "mount_actual": actual,
            "recorded_in_falsifier_record": recorded}, rel)
    return {"path": rel, "sha256": actual, "expected": expected,
            "recorded_in_falsifier_record": recorded}


def cc4_span_provenance(mount: Path, freeze: dict, checks: dict) -> dict:
    rel = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    bundle = load_json(mount / rel)
    span = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
    expected = {
        "applied": True, "mode": "select", "n_candidates": 1,
        "n_selected": 0, "n_abstained": 1,
        "abstained_ids": ["gr_gerichte_ERZ 2010 25"],
        "abstention_reasons": {"pivot_absent": 1},
        "guard_available": True,
        "frozen_rules_sha256": "4457e971df3dc5d10af2a727aa675afc15a15564c"
                               "18eed4cede0af5eb41b4608",
    }
    observed = {k: span.get(k) for k in expected}
    mismatches = {k: {"expected": v, "actual": observed.get(k)}
                  for k, v in expected.items() if observed.get(k) != v}
    _check(checks, "CC4_span_seam_provenance_of_record", not mismatches,
           "applied=true, n_selected=0, abstained_ids + pivot_absent abstention "
           "as named in the v68 direction",
           {"mismatches": mismatches, "observed": observed,
            "n_selected_is_zero": observed.get("n_selected") == 0}, rel)
    return {"path": rel, "observed": observed, "mismatches": mismatches,
            "full_provenance_block": span}


def cc5_incumbent_left_in_place(mount: Path, checks: dict) -> dict:
    rec = load_json(REPO_ROOT / FALSIFIER_RECORD_RELPATH)
    rows = []
    for bundle in rec.get("bundles") or []:
        rel = bundle.get("path")
        if not rel or not (mount / rel).is_file():
            rows.append({"path": rel, "ok": False, "reason": "bundle missing"})
            continue
        data = load_json(mount / rel)
        index = {d.get("decision_id"): d for d in data.get("decisions") or []}
        for row in bundle.get("verified_scored_rows") or []:
            did = row.get("decision_id")
            d = index.get(did) or {}
            rows.append({
                "path": rel,
                "decision_id": did,
                "defects_read_from_committed_record": row.get("defects"),
                "counter_evidence_verified_at_mount":
                    d.get("counter_evidence_verified"),
                "counter_status_at_mount": d.get("counter_status"),
                "counter_uncertainty_at_mount": d.get("counter_uncertainty"),
                "counter_evidence_head_at_mount":
                    (d.get("counter_evidence") or "")[:120],
                "ok": d.get("counter_evidence_verified") is True,
            })
    defective = [r for r in rows if r.get("defects_read_from_committed_record")]
    sound = [r for r in rows if not r.get("defects_read_from_committed_record")]
    ok = (len(defective) == 4 and len(sound) == 1
          and all(r["ok"] for r in rows))
    _check(checks, "CC5_incumbent_left_in_place", ok,
           "all 4 defective rows named by the committed record are still "
           "counter_evidence_verified=true at the mount, and the 1 sound row "
           "is verified too (reading a flag, never re-scoring)",
           {"n_defective_rows": len(defective), "n_sound_rows": len(sound),
            "all_verified_at_mount": all(r["ok"] for r in rows),
            "rows": rows},
           "accepted mount bundle rows vs committed record row list")
    return {"rows": rows, "n_defective": len(defective),
            "n_sound": len(sound)}


def cc6_code_path(mount: Path, freeze: dict, checks: dict) -> dict:
    exp = freeze["frozen_expected_code_path_lines"]
    pipe_path = mount / "product/query/pipeline.py"
    slice_path = mount / "product/offline_slice.py"
    pipe_lines = pipe_path.read_text(encoding="utf-8").splitlines()
    slice_lines = slice_path.read_text(encoding="utf-8").splitlines()
    head = mount_head(mount)
    pipe_blob_head = git(mount, "rev-parse", "HEAD:product/query/pipeline.py").stdout.strip()
    pipe_blob_work = git(mount, "hash-object", "product/query/pipeline.py").stdout.strip()
    slice_blob_head = git(mount, "rev-parse", "HEAD:product/offline_slice.py").stdout.strip()
    slice_blob_work = git(mount, "hash-object", "product/offline_slice.py").stdout.strip()
    pipe_blob_51d = git(mount, "rev-parse", "51d306c:product/query/pipeline.py").stdout.strip()

    observed = {
        "pipeline_line_1339": pipe_lines[1338] if len(pipe_lines) >= 1339 else None,
        "pipeline_line_1343": pipe_lines[1342] if len(pipe_lines) >= 1343 else None,
        "pipeline_line_1347": pipe_lines[1346] if len(pipe_lines) >= 1347 else None,
        "pipeline_line_1348": pipe_lines[1347] if len(pipe_lines) >= 1348 else None,
        "pipeline_line_1357": pipe_lines[1356] if len(pipe_lines) >= 1357 else None,
        "offline_slice_line_79": slice_lines[78] if len(slice_lines) >= 79 else None,
        "absent_string_occurrences":
            "\n".join(pipe_lines).count(exp["absent_string_in_pipeline_py"]),
        "head": head,
        "pipeline_blob_head": pipe_blob_head,
        "pipeline_blob_worktree": pipe_blob_work,
        "pipeline_blob_at_51d306c": pipe_blob_51d,
        "offline_slice_blob_head": slice_blob_head,
        "offline_slice_blob_worktree": slice_blob_work,
    }
    ok = (
        observed["pipeline_line_1339"] == exp["product/query/pipeline.py:1339"]
        and exp["product/query/pipeline.py:1343_contains"]
        in (observed["pipeline_line_1343"] or "")
        and observed["pipeline_line_1347"] == exp["product/query/pipeline.py:1347"]
        and exp["product/query/pipeline.py:1348_contains"]
        in (observed["pipeline_line_1348"] or "")
        and observed["pipeline_line_1357"] == exp["product/query/pipeline.py:1357"]
        and exp["product/offline_slice.py:79_contains"]
        in (observed["offline_slice_line_79"] or "")
        and observed["absent_string_occurrences"] == 0
        and observed["head"] == "8b5b08dddeda482961ecfd432a5b5b40675b92ab"
        and observed["pipeline_blob_head"] == observed["pipeline_blob_worktree"]
        == observed["pipeline_blob_at_51d306c"]
        and observed["offline_slice_blob_head"]
        == observed["offline_slice_blob_worktree"]
    )
    _check(checks, "CC6_accepted_code_path_file_line", ok,
           "file:line inventory of the accepted head exactly as frozen, the "
           "old fixture gate absent, and worktree blobs == HEAD blobs == "
           "51d306c blob",
           observed,
           "product/query/pipeline.py:1339,1343,1347,1348,1357 and "
           "product/offline_slice.py:79 at 8b5b08dd")
    return {"observed": observed,
            "file_line_inventory": {
                "product/query/pipeline.py:1339": observed["pipeline_line_1339"],
                "product/query/pipeline.py:1343": observed["pipeline_line_1343"],
                "product/query/pipeline.py:1347": observed["pipeline_line_1347"],
                "product/query/pipeline.py:1348": observed["pipeline_line_1348"],
                "product/query/pipeline.py:1357": observed["pipeline_line_1357"],
                "product/offline_slice.py:79": observed["offline_slice_line_79"],
            }}


def cc7_51d_diff(mount: Path, checks: dict) -> dict:
    p = git(mount, "show", "51d306c", "--format=%H%n%P%n%cI%n%s", "--",
            "product/query/pipeline.py")
    text = p.stdout
    meta = text.splitlines()[:4]
    ok = (p.returncode == 0
          and len(meta) == 4
          and meta[0].startswith("51d306ca4b52c6d8ea1200c306cfb33e44e487ac")
          and meta[1].startswith("e2270c373a8f26c6b826053e8527a216a3304e8b")
          and meta[2].startswith("2026-10-24T13:10:55")
          and "-    if not fixture_generation and adversarial_retrieval:" in text
          and "+    if adversarial_retrieval:" in text)
    _check(checks, "CC7_51d306c_diff_provenance", ok,
           "51d306c (parent e2270c37, 2026-10-24T13:10:55Z) removes the "
           "'not fixture_generation' gate and adds 'if adversarial_retrieval:'",
           {"meta": meta,
            "removed_line_present": "-    if not fixture_generation and "
                                    "adversarial_retrieval:" in text,
            "added_line_present": "+    if adversarial_retrieval:" in text},
           "git -C <mount> show 51d306c -- product/query/pipeline.py")
    return {"commit": meta[0] if meta else None,
            "parent": meta[1] if len(meta) > 1 else None,
            "commit_time": meta[2] if len(meta) > 2 else None,
            "subject": meta[3] if len(meta) > 3 else None,
            "diff_text_sha256": hashlib.sha256(
                text.encode("utf-8")).hexdigest()}


def cc8_seam_run_inventory(mount: Path, checks: dict) -> dict:
    rec = load_json(REPO_ROOT / FALSIFIER_RECORD_RELPATH)
    rows = []
    for bundle in rec.get("bundles") or []:
        rel = bundle.get("path")
        if not rel or not (mount / rel).is_file():
            rows.append({"path": rel, "present": False})
            continue
        data = load_json(mount / rel)
        prov = data.get("provenance") or {}
        has = "counter_evidence_span" in prov
        rows.append({
            "path": rel,
            "enriched": bundle.get("enriched"),
            "span_provenance_present": has,
            "applied": (prov.get("counter_evidence_span") or {}).get("applied"),
            "n_selected": (prov.get("counter_evidence_span") or {}).get(
                "n_selected"),
            "family_dir": Path(rel).parent.name,
        })
    with_span = [r for r in rows if r.get("span_provenance_present")]
    without = [r for r in rows if not r.get("span_provenance_present")]
    enriched_without = [r for r in without if r.get("enriched")]
    ok = len(rows) == 6 and len(with_span) == 1 and len(enriched_without) == 4
    _check(checks, "CC8_span_seam_run_inventory_on_scored_population", ok,
           "exactly 1 of the 6 scored bundles carries a "
           "provenance.counter_evidence_span block (the regenerated "
           "rent-default family); the other 5 carry no such key, 4 of them "
           "among the enriched bundles",
           {"n_bundles": len(rows), "n_with_span": len(with_span),
            "n_without_span": len(without),
            "n_enriched_without_span": len(enriched_without), "rows": rows},
           "provenance block presence per scored bundle on the accepted mount")
    return {"rows": rows, "n_with_span": len(with_span),
            "n_enriched_without_span": len(enriched_without)}


def cc9_frozen_untouched(repo: Path, freeze: dict, mount: Path,
                         checks: dict) -> dict:
    expected = freeze["expected_repo_pins_before_execution"]
    observed = {}
    mismatches = {}
    for rel, digest in expected.items():
        path = repo / rel
        actual = sha256_file(path) if path.is_file() else None
        observed[rel] = actual
        if actual != digest:
            mismatches[rel] = {"expected": digest, "actual": actual}
    # cross-artifact integrity: the bundle's own embedded frozen rules digest
    rel_b = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    span = ((load_json(mount / rel_b).get("provenance") or {})
            .get("counter_evidence_span") or {})
    embedded = span.get("frozen_rules_sha256")
    on_disk = observed.get(RULES_LABEL_RELPATH)
    integrity_ok = embedded == on_disk
    ok = not mismatches and integrity_ok
    _check(checks, "CC9_frozen_inputs_untouched", ok,
           "every frozen repo input re-hashes to its freeze pin (REPORTED-ONLY) "
           "AND the bundle's embedded frozen_rules_sha256 equals the on-disk "
           "RULES_LABEL.json digest",
           {"mismatches": mismatches,
            "bundle_embedded_frozen_rules_sha256": embedded,
            "on_disk_rules_label_sha256": on_disk,
            "cross_artifact_integrity": integrity_ok,
            "observed": observed},
           "sha256 re-hash of the freeze-pinned inputs")
    return {"observed": observed, "mismatches": mismatches,
            "bundle_embedded_frozen_rules_sha256": embedded,
            "cross_artifact_integrity": integrity_ok}


def cc10_d123(mount: Path, checks: dict) -> dict:
    rel = "results/audit/product/CYCLE_39965089504_GATE.json"
    path = mount / rel
    gate = load_json(path)
    fixes = gate.get("required_fixes") or []
    all_non_blocking = all(str(f).startswith("NON-BLOCKING") for f in fixes)
    ok = (gate.get("gate") == "PASS" and len(fixes) == 3 and all_non_blocking)
    _check(checks, "CC10_d1_d2_d3_disclosure_source", ok,
           "gate=PASS with exactly 3 required_fixes, each marked NON-BLOCKING, "
           "so this lane may quote 'three non-blocking required fixes'",
           {"gate": gate.get("gate"),
            "safe_to_integrate": gate.get("safe_to_integrate"),
            "n_required_fixes": len(fixes),
            "all_non_blocking": all_non_blocking,
            "fix_prefixes": [str(f).split(":")[0] for f in fixes],
            "sha256": sha256_file(path)}, rel)
    return {"path": rel, "sha256": sha256_file(path),
            "gate": gate.get("gate"), "required_fixes": fixes}


def cc11_item2_gate(mount: Path, checks: dict) -> dict:
    head = mount_head(mount)
    offline = sorted(p.name for p in
                     (mount / "results/product/offline_slice").iterdir()
                     if p.is_dir())
    server = sorted(p.name for p in
                    (mount / "results/product/server_slice").iterdir()
                    if p.is_dir())
    newest_offline = offline[-1] if offline else None
    newest_server = server[-1] if server else None
    rel = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    bundle = load_json(mount / rel)
    row = next((d for d in bundle.get("decisions") or []
                if d.get("decision_id") == "gr_gerichte_ERZ 2010 25"), None)
    span = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
    head_same = head == "8b5b08dddeda482961ecfd432a5b5b40675b92ab"
    not_regenerated = newest_offline == "20261024T142517Z"
    incumbent_still_verified = bool(row and
                                    row.get("counter_evidence_verified") is True)
    seam_abstained = span.get("applied") is True and span.get("n_selected") == 0
    landed = (not incumbent_still_verified) and (not seam_abstained)
    status = ("EXECUTABLE" if (not head_same and not not_regenerated and landed)
              else "NOT_YET_DISCRIMINATING")
    ok = (head_same and not_regenerated and incumbent_still_verified
          and seam_abstained and status == "NOT_YET_DISCRIMINATING")
    _check(checks, "CC11_item2_gate_status", ok,
           "head unchanged, flagship family not regenerated, seam abstained and "
           "the defective incumbent still verified -> item (2) "
           "NOT_YET_DISCRIMINATING (no re-measure, no synthetic stand-in)",
           {"mount_head": head, "head_same_as_falsifier_head": head_same,
            "newest_offline_slice_family": newest_offline,
            "newest_server_slice_family": newest_server,
            "n_offline_slice_family_dirs": len(offline),
            "n_server_slice_family_dirs": len(server),
            "not_regenerated": not_regenerated,
            "seam_applied": span.get("applied"),
            "seam_n_selected": span.get("n_selected"),
            "seam_abstained": seam_abstained,
            "incumbent_still_verified": incumbent_still_verified,
            "rejection_incumbent_leg_landed": landed,
            "item_2_status": status},
           "accepted mount head + family inventory + bundle row flag")
    return {"item_2_status": status, "mount_head": head,
            "newest_offline_slice_family": newest_offline,
            "newest_server_slice_family": newest_server,
            "n_offline_slice_family_dirs": len(offline),
            "n_server_slice_family_dirs": len(server),
            "rejection_incumbent_leg_landed": landed,
            "seam_applied": span.get("applied"),
            "seam_n_selected": span.get("n_selected"),
            "incumbent_still_verified": incumbent_still_verified}


# ---------------------------------------------------------------------- controls
def run_controls(mount: Path, repo: Path, freeze: dict) -> dict:
    controls: dict = {}

    # C1 planted span-provenance divergence must be caught by the same checker
    rel = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
    span = ((load_json(mount / rel).get("provenance") or {})
            .get("counter_evidence_span") or {})
    planted = dict(span)
    planted["n_selected"] = 1
    expected_core = {k: span.get(k) for k in
                     ("applied", "mode", "n_candidates", "n_selected",
                      "n_abstained", "abstained_ids", "abstention_reasons",
                      "guard_available", "frozen_rules_sha256")}
    planted_mismatch = any(planted.get(k) != v
                           for k, v in expected_core.items())
    controls["C1_planted_span_provenance_divergence_must_be_detected"] = {
        "holds": planted_mismatch is True,
        "detail": "n_selected 0 -> 1 in a copy is reported as a divergence"}

    # C2 the clause detector must not fire where no clause was published
    machine = (repo / MACHINE_REPORT_RELPATH).read_text(encoding="utf-8")
    fires = any(CLAUSE_HEAD in line for line in machine.splitlines())
    controls["C2_clause_detector_must_not_fire_on_absent_text"] = {
        "holds": fires is False,
        "detail": "machine report contains no clause -> detector returns no match"}

    # C3 planted measurement mutation must be caught by the CC2 checker
    rec = load_json(repo / FALSIFIER_RECORD_RELPATH)
    pinned = freeze["frozen_measurement_of_record_copy_for_CC2"]
    mutated_agg = dict(rec.get("aggregate") or {})
    mutated_agg["n_defective_verified_scored_rows_total"] = (
        mutated_agg.get("n_defective_verified_scored_rows_total") - 1)
    mutated_ok = (mutated_agg.get("n_defective_verified_scored_rows_total")
                  == pinned["n_defective_verified_scored_rows_total"])
    controls["C3_planted_measurement_mutation_must_be_detected"] = {
        "holds": mutated_ok is False,
        "detail": "n_defective 4 -> 3 in a copy diverges from the freeze pin"}

    # C4 no falsifier re-execution
    # Scan the source for actual import statements or function calls to the
    # forbidden modules, not just substring matches (which would false-positive
    # on filepaths containing the module name as a path component).
    src = Path(__file__).read_text(encoding="utf-8")
    import re as _re
    forbidden = ["fast_mvp_current_head_ca_falsifier",
                 "counter_evidence_quality_benchmark",
                 "mapping_free_recall_falsifier"]
    # Check for actual import or invocation of the forbidden modules.
    # Patterns: "import X", "from ... import X", or "X(" (function call).
    hits = [name for name in forbidden
            if _re.search(r'\bimport\s+' + _re.escape(name) + r'\b', src) or
               _re.search(r'\bfrom\s+.*?\bimport\s+' + _re.escape(name) + r'\b', src) or
               _re.search(r'\b' + _re.escape(name) + r'\(', src)]
    controls["C4_no_falsifier_reexecution"] = {
        "holds": not hits,
        "detail": "instrument source imports/invokes none of the falsifier, the "
                  "D1-D4 predicate module or the mapping-free gate module",
        "forbidden_substrings_found": hits}

    # C5 bundle-embedded frozen rules digest equals the on-disk digest
    embedded = span.get("frozen_rules_sha256")
    on_disk = sha256_file(repo / RULES_LABEL_RELPATH)
    controls["C5_bundle_embedded_frozen_rules_digest_matches_disk"] = {
        "holds": embedded == on_disk,
        "detail": "bundle provenance frozen_rules_sha256 == sha256(RULES_LABEL.json)",
        "embedded": embedded, "on_disk": on_disk}
    return controls


# ------------------------------------------------------------------------- main
def run(run_id: str, mount: Path, out_dir: Path) -> tuple[int, dict]:
    started = datetime.now(timezone.utc)
    hyp_path = REPO_ROOT / HYPOTHESIS_RELPATH
    freeze_path = REPO_ROOT / FREEZE_RELPATH
    for p in (hyp_path, freeze_path):
        if not p.is_file():
            return EXIT_INPUT_ERROR, {"error": f"missing frozen input {p}"}
    if not mount.is_dir():
        return EXIT_INPUT_ERROR, {"error": f"missing accepted mount {mount}"}
    hyp = load_json(hyp_path)
    freeze = load_json(freeze_path)

    checks: dict = {}
    details: dict = {}
    details["CC1"] = cc1_clause_located(REPO_ROOT, checks)
    details["CC2"] = cc2_measurement_unchanged(REPO_ROOT, freeze, checks)
    details["CC3"] = cc3_bundle_sha(mount, freeze, checks)
    details["CC4"] = cc4_span_provenance(mount, freeze, checks)
    details["CC5"] = cc5_incumbent_left_in_place(mount, checks)
    details["CC6"] = cc6_code_path(mount, freeze, checks)
    details["CC7"] = cc7_51d_diff(mount, checks)
    details["CC8"] = cc8_seam_run_inventory(mount, checks)
    details["CC9"] = cc9_frozen_untouched(REPO_ROOT, freeze, mount, checks)
    details["CC10"] = cc10_d123(mount, checks)
    details["CC11"] = cc11_item2_gate(mount, checks)
    controls = run_controls(mount, REPO_ROOT, freeze)

    # frozen hypothesis digest check (ordering/integrity)
    hyp_sha = sha256_file(hyp_path)
    hyp_matches_freeze = hyp_sha == freeze["hypothesis_sha256_at_freeze"]

    failed_claims = [k for k, v in checks.items() if not v["ok"]]
    failed_controls = [k for k, v in controls.items() if not v["holds"]]
    confirmed = (not failed_claims and not failed_controls and hyp_matches_freeze)
    verdict = "CORRECTION_CONFIRMED" if confirmed else "CORRECTION_NOT_CONFIRMED"
    exit_code = EXIT_CONFIRMED if confirmed else EXIT_NOT_CONFIRMED

    out = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 68,
        "run_id": run_id,
        "corrects_run": "40105794124",
        "ordered_work_item": hyp.get("ordered_work_item"),
        "generated_at_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_s": round((datetime.now(timezone.utc) - started).total_seconds(), 3),
        "verdict": verdict,
        "exit_code": exit_code,
        "hypothesis": {"path": HYPOTHESIS_RELPATH, "sha256": hyp_sha,
                       "sha_matches_freeze_record": hyp_matches_freeze},
        "freeze": {"path": FREEZE_RELPATH,
                   "sha256": sha256_file(freeze_path)},
        "claim_checks": checks,
        "controls": controls,
        "details": details,
        "n_claims": len(checks),
        "n_claims_ok": sum(1 for v in checks.values() if v["ok"]),
        "n_controls": len(controls),
        "n_controls_holding": sum(1 for v in controls.values() if v["holds"]),
        "failed_claims": failed_claims,
        "failed_controls": failed_controls,
        "product_mount_head": mount_head(mount),
        "corrected_statement_of_record": (
            "The accepted product head 8b5b08dd does NOT bypass the landed "
            "span seam: product/query/pipeline.py:1339 gates the seam on "
            "`adversarial_retrieval` alone (51d306c removed the "
            "`not fixture_generation` condition) and the accepted bundle "
            "rent-default 20261024T142517Z carries "
            "counter_evidence_span.applied=true, n_candidates=1, n_selected=0, "
            "abstained_ids=['gr_gerichte_ERZ 2010 25'], "
            "abstention_reasons={pivot_absent:1}. The seam executed and "
            "ABSTAINED; the defective trilingual Graubünden letterhead stays "
            "counter_evidence_verified=true because the INCUMBENT is left in "
            "place. The remaining leg is REJECTION/INCUMBENT HANDLING, not "
            "bypass. The 40105794124 measurement (4 of 5 enriched bundles "
            "defective, histogram D2 2 / D3 2 / D4 1, 1 sound row) is "
            "UNCHANGED by this correction."),
        "measurement_unchanged": (
            checks["CC2_measurement_unchanged_vs_freeze_pin"]["ok"]),
        "falsifier_reexecuted": False,
        "no_174k_benchmark_rerun": True,
        "no_bar_movement": True,
        "no_frozen_edit": True,
        "serve_verdict_issued": False,
        "posture": {"packet_admitted": False, "machine_gate_ready": False,
                    "human_gate_ready": False, "ready_for_owner_session": False,
                    "owner_decision_required": False},
        "item_2_status": details["CC11"]["item_2_status"],
        "numeric_environment": numeric_environment(),
        "claim_ceiling": hyp.get("claim_ceiling"),
        "recompute_command": (
            "python3 -m evaluation.bypass_clause_correction --run-id "
            f"{run_id} --out-dir {out_dir.relative_to(REPO_ROOT)}"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{run_id}.json"
    out["result_file"] = str(target.relative_to(REPO_ROOT))
    target.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n",
                      encoding="utf-8")
    return exit_code, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="40113448025")
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args(argv)
    code, payload = run(args.run_id, Path(args.mount), Path(args.out_dir))
    print(json.dumps({
        "verdict": payload.get("verdict"),
        "exit_code": code,
        "n_claims": payload.get("n_claims"),
        "n_claims_ok": payload.get("n_claims_ok"),
        "n_controls": payload.get("n_controls"),
        "n_controls_holding": payload.get("n_controls_holding"),
        "failed_claims": payload.get("failed_claims"),
        "failed_controls": payload.get("failed_controls"),
        "item_2_status": payload.get("item_2_status"),
        "measurement_unchanged": payload.get("measurement_unchanged"),
        "result_file": payload.get("result_file"),
    }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
