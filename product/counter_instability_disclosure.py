#!/usr/bin/env python3
"""Publish (and re-check) Product's run-to-run counter-instability disclosure.

Factory direction v61, product lane ordered work (3)::

    implement Product's run-to-run counter-instability disclosure beside the
    coverage-gap disclosure (evaluation open items 5/6 ...) - a disclosure-only
    change, no measurement claim, no threshold touched.

Where each piece lives
----------------------
* **The disclosure block itself** is emitted by
  ``product/packet_of_record.py::counter_instability_disclosure`` and is
  published in the packet's OWN disclosure layer, in the same per-bundle
  dictionary as ``under_coverage_disclosure`` (the coverage-gap disclosure),
  plus in ``handoff.json``.  ``packet_of_record.py check --packet ...``
  re-derives every block, the new one included.
* **This tool** writes the run-named artifact of record that (a) puts the two
  disclosures side by side for one reader, (b) pins the provenance of the
  verbatim Evaluation evidence, and (c) records the disclosure-surface
  regeneration of packet 39319405429 with before/after digests, so a reader can
  see exactly which cycle added the block and that the scored bytes never moved.

Scope discipline (non-negotiable, asserted by tests)
----------------------------------------------------
DISCLOSURE ONLY.  This module re-derives no measurement, recomputes no frozen
bar, edits no threshold/rubric/success rule, classifies no decision and
changes no admission outcome.  It writes ONLY under ``results/product/``.

Commands
--------
    python3 product/counter_instability_disclosure.py --run-id <run> --write
    python3 product/counter_instability_disclosure.py --check

Exit codes: 0 ok, 1 artifact mismatch (fail-closed), 6 packet I/O problem.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product import packet_of_record as por  # noqa: E402

SCHEMA = "product-counter-instability-disclosure/1"
PACKET_DIR = REPO_ROOT / "results" / "product" / "gate_packet" / "39319405429"
OUT_DIR = REPO_ROOT / "results" / "product" / "disclosures"
#: the run-named artifact this tool ships (direction v61, ordered work (3))
ARTIFACT = OUT_DIR / "CYCLE_39422322667_counter_instability_disclosure.json"
#: The packet's own frozen pin (packet.json raw sha256).  Re-hashed, never
#: rewritten: only the disclosure surface may move.
PACKET_JSON_RAW_SHA256 = (
    "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
)
#: Before/after digests of the disclosure surface this cycle regenerated, and
#: the git revision a reader can re-derive the "before" bytes from.  Published
#: here because a run-named artifact has to say which cycle moved the surface.
SURFACE_REGENERATION = {
    "cycle": 39422322667,
    "reason": (
        "direction v61 ordered work (3): the counter-instability block must be "
        "published BESIDE the coverage-gap disclosure in the packet's own "
        "disclosure layer, and packet_of_record.check() must reproduce it from "
        "the committed bytes; a packet whose layer predates the block fails that "
        "check (measured fail-closed before this regeneration)."
    ),
    "precedent": (
        "disclosure surface, not scored bytes - same class as the accepted "
        "repair_39048942749 D2_minor regeneration (before/after digests published, "
        "packet bytes never regenerated) and the accepted 39319405429 repair-1 "
        "disclosure-layer fix (commit 13f5425)."
    ),
    "before": {
        "disclosures.json": "87147f114fd3bfe278077afa83613f2c586c8c8d95aa77b287c4fce916cb31d3",
        "handoff.json": "5b758a3da820a562dfadb9af1fbb5ff2acd9ba395fa151a36571217645b64544",
        "PACKET_OF_RECORD.json": "a54e05fa9b42d8364ec12540db6f00d9c3987c0ca98323f4cc0ce6f6d4ee8960",
        "rederive_before_with": (
            "git show f463a81:results/product/gate_packet/39319405429/<file> | "
            "sha256sum   # f463a81 is the accepted base of this cycle"
        ),
    },
    "after_recorded_by": "results/product/gate_packet/39319405429/PACKET_OF_RECORD.json",
    "unchanged": [
        "packet.json (raw sha256 " + PACKET_JSON_RAW_SHA256 + ")",
        "manifest.json",
        "all nine questions/*.json files (bundles, admissibility, question specs)",
    ],
    "not_claimed": [
        "no bundle byte, no scored row, no verdict, no frozen bar and no "
        "admission flag changed",
    ],
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _packet_sha_pins() -> dict[str, Any]:
    """Re-hash the packet's frozen bytes and the current disclosure surface."""
    packet = json.loads((PACKET_DIR / "packet.json").read_text(encoding="utf-8"))
    specs = {}
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        if qid:
            specs[qid] = dict(entry)
    return {
        "packet_dir": str(PACKET_DIR.relative_to(REPO_ROOT)),
        "packet_json_raw_sha256": _sha256_file(PACKET_DIR / "packet.json"),
        "packet_json_pin_holds": _sha256_file(PACKET_DIR / "packet.json")
        == PACKET_JSON_RAW_SHA256,
        "manifest_sha256": _sha256_file(PACKET_DIR / "manifest.json"),
        "disclosures_sha256": _sha256_file(PACKET_DIR / "disclosures.json"),
        "handoff_sha256": _sha256_file(PACKET_DIR / "handoff.json"),
        "packet_of_record_sha256": _sha256_file(PACKET_DIR / "PACKET_OF_RECORD.json"),
        "n_bundle_bytes": len(list((PACKET_DIR / "questions").glob("*.bundle.json"))),
    }


def build(run_id: int) -> dict[str, Any]:
    """Assemble the run-named artifact from the COMMITTED packet bytes.

    Read-only over the packet: nothing under the packet directory is written
    here (the surface regeneration happened in ``packet_of_record.py assemble``
    and is recorded in :data:`SURFACE_REGENERATION`).
    """
    packet = json.loads((PACKET_DIR / "packet.json").read_text(encoding="utf-8"))
    disclosures = json.loads((PACKET_DIR / "disclosures.json").read_text(encoding="utf-8"))
    record = json.loads((PACKET_DIR / "PACKET_OF_RECORD.json").read_text(encoding="utf-8"))
    by_qid = {q.get("qid"): q for q in (packet.get("questions") or [])}
    specs = por._question_specs(PACKET_DIR, packet)

    per_question: list[dict[str, Any]] = []
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        bundle_path = por._resolve(PACKET_DIR, entry.get("bundle_path"),
                                   f"questions/{qid}.bundle.json")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        spec = specs.get(qid) or {"qid": qid, "language": entry.get("language")}
        # read-only re-derivation of BOTH disclosures from the committed bytes,
        # so this artifact and the packet's own layer can never disagree.
        coverage = por.under_coverage_disclosure(
            por.verify_bundle(bundle, question=spec))
        instability = por.counter_instability_disclosure(
            entry.get("language") or por._language_of(qid))
        published = (disclosures.get("per_bundle") or {}).get(qid) or {}
        per_question.append({
            "qid": qid,
            "language": entry.get("language") or por._language_of(qid),
            "coverage_gap_disclosure": coverage,
            "counter_instability_disclosure": instability,
            "published_in_packet_disclosures_json": {
                "coverage_gap_disclosure": published.get("under_coverage_disclosure"),
                "counter_instability_disclosure": published.get(
                    "counter_instability_disclosure"),
                "matches_rederivation": (
                    json.dumps(published.get("under_coverage_disclosure") or {},
                               sort_keys=True) == json.dumps(coverage, sort_keys=True)
                    and json.dumps(published.get("counter_instability_disclosure") or {},
                                   sort_keys=True) == json.dumps(instability, sort_keys=True)
                ),
            },
        })

    source = por.load_counter_instability_source()
    check = por.check(PACKET_DIR)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": 61,
        "generated_at": _now(),
        "ordered_work": (
            "factory direction v61, product lane ordered work (3): run-to-run "
            "counter-instability disclosure beside the coverage-gap disclosure"
        ),
        "packet": _packet_sha_pins(),
        "packet_of_record_check": {
            "ok": bool(check.get("ok")),
            "mismatches": check.get("mismatches"),
        },
        "disclosure_surface_regeneration": SURFACE_REGENERATION,
        "evidence_source": {
            "lane": "evaluation",
            "accepted_state_path": (
                f"{(source.get('source') or {}).get('ref')}:"
                f"{(source.get('source') or {}).get('repo_path')}"
            ),
            "git_blob_oid_at_pin": (source.get("source") or {}).get("git_blob_oid_at_pin"),
            "file_sha256_at_pin": (source.get("source") or {}).get("file_sha256_at_pin"),
            "file_sha256_at_pin_pinned_in_code":
                por.COUNTER_INSTABILITY_ACCEPTED_EVALUATION_SHA256_AT_PIN,
            "pin_commit": (source.get("source") or {}).get("pin_commit"),
            "pin_semantics": (source.get("source") or {}).get("pin_semantics"),
            "vendored_copy": (
                "product/data/eval_open_items/ACCEPTED_EVALUATION_OPEN_ITEMS_5_6.json"
            ),
            "vendored_copy_sha256": _sha256_file(por.COUNTER_INSTABILITY_SOURCE_FILE),
            "json_pointers": (source.get("source") or {}).get("json_pointers"),
            "measuring_run": ((source.get("source") or {}).get("measurement_of_record")
                              or {}).get("measuring_run"),
            "measurement_evidence_path": ((source.get("source") or {})
                                          .get("measurement_of_record") or {}).get(
                                              "evidence_path"),
            "transcription_rule": source.get("transcription_rule"),
            "verbatim_open_items": source.get("open_items"),
        },
        "per_question": per_question,
        "scope": {
            "disclosure_only": True,
            "measurement_rederived_by_product": False,
            "threshold_touched": False,
            "threshold_or_bar_edits": [],
            "frozen_geometry_rules_sha256": por.FROZEN_GEOMETRY_RULES_SHA256,
            "mega_cluster_share_threshold": por.MEGA_CLUSTER_SHARE,
            "admission_flags_unchanged": {
                "packet_admitted": bool((packet.get("packet_admission") or {}).get(
                    "packet_admitted")),
                "packet_admission_blocked": bool(packet.get("packet_admission_blocked")),
                "ready_for_owner_session": bool(packet.get("ready_for_owner_session")),
                "human_gate_ready": False,
                "machine_gate_ready": False,
            },
        },
        "non_claims": [
            "no frozen bar, rubric, threshold, success rule or .github/** file "
            "was read, re-derived, edited or re-tuned by this disclosure",
            "no decision is classified supporting/contrary/limiting here; row "
            "classifications stay exactly as evidenced on each row",
            "no legal-usefulness, answer-quality, latency, map-quality or "
            "serve claim is made",
            "no owner session, no owner question and no human gate: the accepted "
            "BOUNDED-NEGATIVE serve verdict carries owner_decision_required=false "
            "and both DO-NOT-SERVE orders stand",
            "the DE/FR/IT figures are Core Evaluation's REPORTED-ONLY evidence "
            "from run 39322925971, never re-measured by Product",
        ],
        "claim_ceiling": (
            "A run-named, byte-reproducible PUBLICATION of two disclosures side "
            "by side: the packet's coverage-gap disclosure (query_concepts_under_"
            "covered, re-derived read-only from the committed bundles) and Product's "
            "run-to-run counter-instability disclosure (Evaluation open items 5/6 "
            "transcribed from a byte-pinned vendored copy). It measures nothing, "
            "changes no threshold and changes no admission outcome."
        ),
    }


def write(run_id: int) -> Path:
    artifact = build(run_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"CYCLE_{run_id}_counter_instability_disclosure.json"
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return out


def check_artifact() -> dict[str, Any]:
    """Re-derive from committed bytes and compare with the shipped artifact.

    ``generated_at``/``run_id`` are provenance stamps of the shipping cycle and
    are excluded; every substantive field must reproduce.
    """
    candidates = sorted(OUT_DIR.glob("CYCLE_*_counter_instability_disclosure.json"))
    if not candidates:
        return {"ok": False, "reason": "no committed artifact under results/product/disclosures",
                "mismatches": ["artifact:missing"]}
    shipped = json.loads(candidates[-1].read_text(encoding="utf-8"))
    fresh = build(int(shipped.get("run_id") or 0))
    mismatches: list[str] = []
    for key in ("schema", "direction_version", "ordered_work", "packet",
                "packet_of_record_check", "disclosure_surface_regeneration",
                "evidence_source", "per_question", "scope", "non_claims",
                "claim_ceiling"):
        a = json.dumps(shipped.get(key), sort_keys=True)
        b = json.dumps(fresh.get(key), sort_keys=True)
        if a != b:
            mismatches.append(key)
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "artifact": str(candidates[-1].relative_to(REPO_ROOT)),
        "checked_at": _now(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", type=int, default=None)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.write:
            if args.run_id is None:
                print("--write requires --run-id", file=sys.stderr)
                return 2
            out = write(args.run_id)
            print(f"wrote {out.relative_to(REPO_ROOT)}")
            return 0
        result = check_artifact()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"packet unusable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
