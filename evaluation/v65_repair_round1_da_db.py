#!/usr/bin/env python3
"""v65_repair_round1_da_db — same-cycle repair of rejected evaluation cycle 39986080045 (round 1).

Independent audit `results/audit/evaluation/CYCLE_39986080045_GATE.json`
(gate=REVISE, safe_to_integrate=false) ordered exactly three required fixes:

  D-A (material)  The frozen success rule states "(float tolerance 1e-6)"
                  literally, while the instrument compared floats at 5e-4 with
                  an undisclosed deviation, and its docstring/`FLOAT_TOL`
                  constant actively misstated the implementation. REPAIR:
                  publish BOTH verdicts (strict literal 1e-6 and applied
                  precision-matched 5e-4) per float quantity with raw deltas in
                  the committed run record, fix the instrument docstring and
                  replace the false constant. Repaired here by reusing the
                  instrument's own shared pure function
                  `evaluation.v65_currency_crosscheck.build_float_disclosure`,
                  so a fresh run and this repair agree by construction.

  D-B (material)  The multilingual reuse record claimed "(i) one decision per
                  bundle lacks the `language` field; (ii) the bundle has no
                  top-level `query` field". Byte recomputation on the exact
                  packet-of-record bytes shows both are wrong: every bundle
                  carries a top-level `query` string (what is absent is the
                  `query` key INSIDE the provenance block, which is what the
                  V61-era script actually checks at
                  run_v3_multilingual_provenance_reuse.py:88), and every
                  decision carries a `language` key whose value is explicitly
                  null on de 50 / fr 37 / it 47 rows (the same counts the
                  accepted engine reports as UNLABELLED). REPAIR: recompute the
                  byte facts on the exact packet bytes, rewrite the
                  interpretation to match them, and keep every original
                  script-produced row field intact (REUSE-FIRST: the accepted
                  script is unchanged).

  D-C (cosmetic)  Duplicate "Ordered item 4" sections in the V65 report —
                  merged separately in the report file by this repair round.

Properties:
  * IDEMPOTENT — a second run writes byte-identical artifacts (verify with the
    committed test tests/evaluation/test_v65_repair_round1_da_db.py).
  * FAIL-CLOSED — exits 2 and writes nothing if the product mount, packet bytes,
    bundle SHAs, engine cross-check record or any frozen pin is missing or has
    drifted.
  * NO FROZEN EDIT — the hypothesis, freeze record, RULES_LABEL, RULES_GEOMETRY
    and the packet-of-record are re-hashed before and after and must be
    unchanged; nothing is re-scored, no bar is moved, no gate is re-run.
  * NO FALSIFICATION RE-EXECUTION — the audit independently reproduced the
    falsification (PRODUCT_FALSIFIED, identical 4-gate set); this repair is
    disclosure/wording-scoped exactly as ordered ("No re-execution required").

Exit codes:
  0  repaired (or already repaired — idempotent no-op with identical bytes)
  2  FAIL_CLOSED — required input missing or a frozen pin drifted; nothing written
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v65_currency_crosscheck import (  # noqa: E402
    APPLIED_FLOAT_TOL,
    FROZEN_LITERAL_FLOAT_TOL,
    PUBLICATION_DECIMALS,
    build_float_disclosure,
)

RUN_ID = "39986080045"
DIRECTION_VERSION = 65
PACKET = "39319405429"
MOUNT = Path("/tmp/lex_accepted/product")
PACKET_DIR = MOUNT / f"results/product/gate_packet/{PACKET}"
QUESTIONS_DIR = PACKET_DIR / "questions"
OUT_DIR = REPO_ROOT / "results/evaluation/v65_currency_crosscheck"
RUN_JSON = OUT_DIR / f"{RUN_ID}.json"
MULTILINGUAL_JSON = OUT_DIR / f"{RUN_ID}_multilingual_provenance_reuse.json"
REPAIR_LOG = OUT_DIR / f"{RUN_ID}_repair_round1.json"
ENGINE_RECORD = OUT_DIR / "falsification" / f"{RUN_ID}_engine_mapping_free_recall_falsifier.json"
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


class FailClosed(Exception):
    """A required input is missing or a frozen pin drifted: write nothing, exit 2."""

# Frozen pins — re-hashed, never edited (V65 freeze record / accepted rules).
FROZEN_PINS = {
    "evaluation/V65_CURRENCY_CROSSCHECK_HYPOTHESIS_V1.json":
        "34fbbe1ad7c83b47d31146690631fdc0c105fff39150be1e532d2a85710a82a2",
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
}
PACKET_PIN = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_sha(doc) -> str:
    return hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def rehash_frozen() -> dict:
    out = {}
    for rel, expected in FROZEN_PINS.items():
        p = REPO_ROOT / rel
        found = _sha256_file(p) if p.is_file() else "MISSING"
        out[rel] = {"expected": expected, "found": found, "ok": found == expected}
    pkt = PACKET_DIR / "packet.json"
    found_pkt = _sha256_file(pkt) if pkt.is_file() else "MISSING"
    out[f"gate_packet/{PACKET}/packet.json"] = {
        "expected": PACKET_PIN, "found": found_pkt, "ok": found_pkt == PACKET_PIN}
    return out


def byte_recompute_bundles() -> dict:
    """Recompute the D-B byte facts on the exact packet-of-record bundle bytes.

    Fail-closed on: missing bundle, SHA mismatch against the frozen pin already
    recorded in the multilingual row, or a disagreement with the committed
    engine record's language_distribution.
    """
    if not QUESTIONS_DIR.is_dir():
        raise FailClosed(f"FAIL_CLOSED: packet questions dir missing: {QUESTIONS_DIR}")
    engine = json.loads(ENGINE_RECORD.read_text()) if ENGINE_RECORD.is_file() else None
    if engine is None:
        raise FailClosed(f"FAIL_CLOSED: engine record missing: {ENGINE_RECORD}")

    # The accepted engine record carries language_distribution under
    # gates[i].measured for gates named "mf::<family>::<packet>::<qid>".
    engine_unlabelled_sets: dict = {}

    def _walk(obj):
        if isinstance(obj, dict):
            g = obj.get("gate")
            if isinstance(g, str):
                for qid in QIDS:
                    if g.endswith("::" + qid):
                        meas = obj.get("measured") or {}
                        ld = meas.get("language_distribution")
                        if isinstance(ld, dict) and "UNLABELLED" in ld:
                            engine_unlabelled_sets.setdefault(qid, set()).add(
                                ld.get("UNLABELLED"))
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(engine)
    missing = [q for q in QIDS if q not in engine_unlabelled_sets]
    ambiguous = {q: sorted(s, key=str) for q, s in engine_unlabelled_sets.items()
                 if len(s) != 1}
    if missing or ambiguous:
        raise FailClosed(
            f"FAIL_CLOSED: engine language_distribution unusable: missing={missing} "
            f"ambiguous={ambiguous}")
    engine_unlabelled = {q: next(iter(s))
                         for q, s in engine_unlabelled_sets.items()}

    out = {}
    for qid in QIDS:
        bp = QUESTIONS_DIR / f"{qid}.bundle.json"
        if not bp.is_file():
            raise FailClosed(f"FAIL_CLOSED: bundle missing: {bp}")
        raw = bp.read_bytes()
        bundle = json.loads(raw)
        decisions = bundle.get("decisions", [])
        n_null = sum(1 for d in decisions if d.get("language") is None)
        n_absent_key = sum(1 for d in decisions if "language" not in d)
        n_engine_unlabelled = sum(
            1 for d in decisions if not str(d.get("language") or "").strip())
        first_null = next(
            (d.get("decision_id") for d in decisions if d.get("language") is None), None)
        prov = bundle.get("provenance")
        row = {
            "qid": qid,
            "bundle_sha256": hashlib.sha256(raw).hexdigest(),
            "top_level_query_field_present": "query" in bundle,
            "top_level_query_type": type(bundle.get("query")).__name__,
            "top_level_query_prefix": str(bundle.get("query"))[:60] if "query" in bundle else None,
            "provenance_query_key_present": (
                isinstance(prov, dict) and "query" in prov),
            "n_decisions": len(decisions),
            "n_language_null": n_null,
            "n_language_key_absent": n_absent_key,
            "n_engine_unlabelled_predicate": n_engine_unlabelled,
            "first_null_language_decision_id": first_null,
        }
        # cross-check 1: null count == engine predicate count == engine record
        row["null_equals_engine_predicate"] = n_null == n_engine_unlabelled
        eng = engine_unlabelled.get(qid)
        row["engine_record_unlabelled"] = eng
        row["null_equals_engine_record_unlabelled"] = (n_null == eng)
        # cross-check 2: bundle sha equals the frozen pin recorded in the row
        out[qid] = row
    return out


def repair_currency_record() -> dict:
    """D-A: attach the dual-tolerance disclosure to the committed run record.

    The embedded block is a pure function of the committed rows (no digests of
    the file itself), so a second run is byte-idempotent.
    """
    doc = json.loads(RUN_JSON.read_text())
    before_sha = _sha256_file(RUN_JSON)
    rows = doc["currency_crosscheck"]["rows"]
    disclosure = build_float_disclosure(rows)
    doc["currency_crosscheck"]["float_comparison_disclosure"] = disclosure
    doc["currency_crosscheck"]["headline"] = (
        disclosure["headline_applied_precision_matched"])
    doc["currency_crosscheck"]["headline_basis"] = (
        "applied precision-matched comparison (5e-4, half-ulp of the product's "
        "3-decimal publication precision); the frozen-literal-1e-6 headline is "
        "published side by side in float_comparison_disclosure")
    doc["repair_round1"] = {
        "repairs_audit_gate": "results/audit/evaluation/CYCLE_39986080045_GATE.json",
        "audit_gate": "REVISE",
        "required_fixes_applied": ["D-A"],
        "fix_D_A": (
            "float comparison tolerance now disclosed in the result JSON: applied "
            f"{APPLIED_FLOAT_TOL} (half-ulp of 3-decimal publication precision) vs "
            f"frozen literal {FROZEN_LITERAL_FLOAT_TOL}; both verdicts published per "
            "float quantity with raw absolute deltas; instrument docstring and the "
            "false FLOAT_TOL constant replaced by FROZEN_LITERAL_FLOAT_TOL / "
            "APPLIED_FLOAT_TOL in evaluation/v65_currency_crosscheck.py"),
        "strict_1e_6_counts": disclosure["counts_frozen_literal_1e_6"],
        "applied_precision_matched_counts": disclosure["counts_applied_precision_matched"],
        "reexecuted": False,
        "reexecution_note": (
            "audit ordered 'No re-execution required'; the falsification, pins and "
            "controls of this run are untouched byte-for-byte"),
        "frozen_rule_edited": False,
    }
    RUN_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True))
    return {"artifact": str(RUN_JSON.relative_to(REPO_ROOT)),
            "pre_repair_sha256": before_sha,
            "post_repair_sha256": _sha256_file(RUN_JSON),
            "changed": before_sha != _sha256_file(RUN_JSON),
            "strict_counts": disclosure["counts_frozen_literal_1e_6"],
            "applied_counts": disclosure["counts_applied_precision_matched"],
            "n_float_quantities": disclosure["n_float_quantities"]}


def validate_multilingual_pins(byte_facts: dict) -> None:
    """Validate BEFORE any write: bundle SHAs vs the frozen pins carried by the
    committed rows, and language-null counts vs the committed engine record."""
    doc = json.loads(MULTILINGUAL_JSON.read_text())
    row_sha = {r["qid"]: r["bundle_sha256"] for r in doc.get("rows", [])}
    for qid, facts in byte_facts.items():
        if row_sha.get(qid) != facts["bundle_sha256"]:
            raise FailClosed(
                f"bundle sha drift for {qid}: "
                f"row={row_sha.get(qid)} recomputed={facts['bundle_sha256']}")
        if not facts["null_equals_engine_record_unlabelled"]:
            raise FailClosed(
                f"language-null count disagrees with committed engine "
                f"UNLABELLED for {qid}: {facts['n_language_null']} vs "
                f"{facts['engine_record_unlabelled']}")


def repair_multilingual_record(byte_facts: dict) -> dict:
    """D-B: correct the interpretation against the recomputed byte facts."""
    validate_multilingual_pins(byte_facts)  # idempotent re-check, no write yet
    doc = json.loads(MULTILINGUAL_JSON.read_text())
    before_sha = _sha256_file(MULTILINGUAL_JSON)

    counts = {qid: f["n_language_null"] for qid, f in byte_facts.items()}
    counts_str = ", ".join(f"{k} {v}" for k, v in counts.items())
    interpretation = (
        "The three frozen bundle SHAs match their V61 pins byte-for-byte and the "
        "expected language is present in every bundle (language robustness holds). "
        "Two schema-completeness checks fail ON THE PACKET-OF-RECORD BYTES "
        "THEMSELVES — CORRECTED AGAINST THE BYTES by repair round 1 of run "
        f"39986080045 (audit D-B): (i) the provenance block has NO 'query' key, "
        "which is what the V61-era script actually tests at "
        "run_v3_multilingual_provenance_reuse.py:88 ('query' in "
        "bundle['provenance']) — the top-level 'query' field DOES exist on all "
        "three bundles as a non-empty string (e.g. de: 'Aktive Fürsorgepflicht "
        "des Arbeitgebers bei einer Kapitalverletzung...'); (ii) every decision "
        "carries a 'language' key, but its value is explicitly null on "
        f"{counts_str} decisions (the field is present with a null value, not "
        "absent; the V61-era check d.get('language') is None counts null as "
        "missing and samples only the first such decision per bundle — de "
        "bge_126 V 75 / fr bger_4A_173_2017 / it bge_130 V 229). Those null "
        "counts are exactly the UNLABELLED counts the accepted engine reports "
        "for the same bundles. The original claim 'one decision per bundle lacks "
        "the language field' UNDERSTATES the count and 'the bundle has no "
        "top-level query field' was factually WRONG; both wordings are "
        "retracted. These remain PRE-EXISTING structural properties of served "
        "packet 39319405429, not a regression introduced by product head "
        "f4cd7d7: the packet bytes are unchanged (sha256 32ac8126... re-hashed "
        "before and after) and the accepted mapping-free engine already scores "
        "language_robustness as REPORTED-only. Disclosed, never repaired by this "
        "lane; the accepted reuse script stays unchanged (REUSE-FIRST).")
    doc["interpretation"] = interpretation
    doc["field_semantics"] = {
        "row.query_field_present": (
            "V61-era SCRIPT OUTPUT: tests 'query' in bundle['provenance'] — i.e. a "
            "query key INSIDE the provenance block. False on all three bundles. It "
            "does NOT test the top-level bundle query field."),
        "row.top_level_query_field_present": (
            "byte-recomputed: 'query' exists as a non-empty top-level string on all "
            "three bundles"),
        "row.missing_fields_sample": (
            "V61-era script sample of the FIRST decision whose d.get(field) is None; "
            "the language key is present on every decision with an explicit null "
            "value on the counts recorded in byte_recomputation_at_repair"),
        "repaired_by": (
            "evaluation/v65_repair_round1_da_db.py under audit "
            "CYCLE_39986080045 required_fixes D-B; the accepted script "
            "evaluation/run_v3_multilingual_provenance_reuse.py is unchanged"),
    }
    doc["top_level_query_field_present"] = all(
        f["top_level_query_field_present"] for f in byte_facts.values())
    doc["provenance_query_key_present"] = any(
        f["provenance_query_key_present"] for f in byte_facts.values())
    for row in doc.get("rows", []):
        facts = byte_facts[row["qid"]]
        row["top_level_query_field_present"] = facts["top_level_query_field_present"]
        row["provenance_query_key_present"] = facts["provenance_query_key_present"]
        row["n_language_null"] = facts["n_language_null"]
        row["n_language_key_absent"] = facts["n_language_key_absent"]
        row["n_language_present_non_null"] = (
            facts["n_decisions"] - facts["n_language_null"])
        row["first_null_language_decision_id"] = (
            facts["first_null_language_decision_id"])
        row["null_count_equals_engine_unlabelled"] = (
            facts["null_equals_engine_record_unlabelled"])
        # the script's original fields stay exactly as the accepted script wrote them
        row["script_query_field_present_semantics"] = (
            "provenance-block query key (V61 script), not the top-level query field")
    doc["byte_recomputation_at_repair"] = {
        "performed_by": "evaluation/v65_repair_round1_da_db.py",
        "performed_on": "exact packet-of-record bundle bytes "
                        f"({PACKET}/questions/*.bundle.json)",
        "packet_sha256": PACKET_PIN,
        "facts": byte_facts,
        "audit_defect": "D-B (multilingual reuse characterization wrong against packet bytes)",
        "script_unchanged": "evaluation/run_v3_multilingual_provenance_reuse.py",
    }
    doc["repair_round1"] = {
        "repairs_audit_gate": "results/audit/evaluation/CYCLE_39986080045_GATE.json",
        "audit_gate": "REVISE",
        "required_fixes_applied": ["D-B"],
        "fix_D_B": (
            "interpretation corrected against the exact packet bytes: the top-level "
            "query field EXISTS on all three bundles (absent is only the "
            "provenance-block query key the V61 script tests at line 88); every "
            "decision carries a language key, null-valued on "
            f"{counts_str} decisions, equal to the engine's UNLABELLED counts; "
            "original 'one decision per bundle lacks the language field' and "
            "'the bundle has no top-level query field' wordings retracted; "
            "accepted script unchanged"),
        "language_null_counts": counts,
        "frozen_bundle_shas_unchanged": True,
    }
    MULTILINGUAL_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True))
    return {"artifact": str(MULTILINGUAL_JSON.relative_to(REPO_ROOT)),
            "pre_repair_sha256": before_sha,
            "post_repair_sha256": _sha256_file(MULTILINGUAL_JSON),
            "changed": before_sha != _sha256_file(MULTILINGUAL_JSON),
            "language_null_counts": counts,
            "top_level_query_present": doc["top_level_query_field_present"],
            "provenance_query_key_present": doc["provenance_query_key_present"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--out-log", default=str(REPAIR_LOG))
    args = ap.parse_args(argv)

    try:
        return _run_repair(args)
    except FailClosed as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "reason": str(exc)}, indent=1))
        return 2
    except (KeyError, TypeError, ValueError, FileNotFoundError,
            json.JSONDecodeError) as exc:
        # Every input validation (frozen pins, packet bytes, bundle pins, engine
        # cross-check) runs BEFORE any write, so this is either a pre-write
        # failure with nothing touched, or an unexpected input shape; in both
        # cases fail closed rather than publishing a partial claim.
        print(json.dumps({"verdict": "FAIL_CLOSED",
                          "reason": f"{type(exc).__name__}: {exc}"}, indent=1))
        return 2


def _run_repair(args) -> int:
    # 0) frozen pins BEFORE
    pins_before = rehash_frozen()
    bad_before = [k for k, v in pins_before.items() if not v["ok"]]
    if bad_before:
        print(json.dumps({"verdict": "FAIL_CLOSED",
                          "reason": "frozen pin mismatch before repair",
                          "bad": bad_before}, indent=1))
        return 2
    if not RUN_JSON.is_file() or not MULTILINGUAL_JSON.is_file():
        print(json.dumps({"verdict": "FAIL_CLOSED",
                          "reason": "committed run artifacts missing"}, indent=1))
        return 2

    # 1) byte recomputation on the exact packet bytes (D-B), then validate all
    #    cross-checks BEFORE any write so a failure can never leave a partial state
    byte_facts = byte_recompute_bundles()
    validate_multilingual_pins(byte_facts)

    # 2) repairs (idempotent)
    da = repair_currency_record()
    db = repair_multilingual_record(byte_facts)

    # 3) frozen pins AFTER — must be untouched
    pins_after = rehash_frozen()
    bad_after = [k for k, v in pins_after.items() if not v["ok"]]
    if bad_after:
        print(json.dumps({"verdict": "FAIL_CLOSED",
                          "reason": "frozen pin drift caused by repair",
                          "bad": bad_after}, indent=1))
        return 2
    pins_unchanged = _canonical_sha(pins_before) == _canonical_sha(pins_after)

    # --- assemble the repair log (byte-stable across reruns) ----------------
    # Volatile first-pass-only values (the pre-repair digests, the changed flags
    # and the timestamp) are INHERITED from an existing log so a second run of
    # this instrument rewrites byte-identical artifacts and a byte-identical log
    # (true idempotency, verified by tests/evaluation/test_v65_repair_round1_da_db.py).
    da_blk = {k: v for k, v in da.items() if k != "changed"}
    db_blk = {k: v for k, v in db.items() if k != "changed"}
    log = {
        "schema": "lex-evaluation-v65-repair-round1/1",
        "run_id": args.run_id,
        "direction_version": DIRECTION_VERSION,
        "repairs_audit_gate": "results/audit/evaluation/CYCLE_39986080045_GATE.json",
        "audit_gate": "REVISE",
        "audit_repair_round": 1,
        "required_fixes_targeted": ["D-A", "D-B", "D-C"],
        "required_fixes_applied_here": ["D-A", "D-B"],
        "D_C_applied_in": "reports/evaluation/V65_CURRENCY_CROSSCHECK_39986080045.md "
                          "(duplicate 'Ordered item 4' sections merged)",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "D_A": da_blk,
        "D_B": db_blk,
        "first_pass": {"D_A_changed": da["changed"], "D_B_changed": db["changed"]},
        "frozen_pins_before": pins_before,
        "frozen_pins_after": pins_after,
        "frozen_pins_unchanged": pins_unchanged,
        "falsification_reexecuted": False,
        "falsification_untouched_note": (
            "audit independently reproduced PRODUCT_FALSIFIED with the identical "
            "4-gate set and ordered 'No re-execution required'; "
            f"{OUT_DIR.relative_to(REPO_ROOT)}/falsification/{args.run_id}*.json "
            "are byte-untouched by this repair"),
        "controls_untouched": True,
        "claim_ceiling": (
            "Disclosure/wording repair only: publishes the already-measured float "
            "deltas under both tolerances and corrects the multilingual schema "
            "characterization against the exact packet bytes. Re-scores nothing, "
            "moves no bar, edits no frozen rule, lifts no DO-NOT-SERVE order, "
            "certifies no admission, and claims no jurist usefulness. "
            "human_gate_ready/machine_gate_ready/packet_admitted/"
            "ready_for_owner_session remain false."),
        "posture_unchanged": {
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
        },
        "idempotent": True,
        "verdict": "REPAIR_APPLIED_D_A_D_B",
    }
    log_path = Path(args.out_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rerun = log_path.is_file()
    if rerun:
        prev = json.loads(log_path.read_text())
        log["generated_at_utc"] = prev.get(
            "generated_at_utc", log["generated_at_utc"])
        log["first_pass"] = prev.get("first_pass", log["first_pass"])
        for key in ("D_A", "D_B"):
            prev_pre = (prev.get(key) or {}).get("pre_repair_sha256")
            if prev_pre:
                log[key]["pre_repair_sha256"] = prev_pre
    log_path.write_text(json.dumps(log, indent=1, sort_keys=True))
    print(json.dumps({
        "verdict": log["verdict"],
        "rerun_of_existing_repair_log": rerun,
        "D_A_strict_counts": da["strict_counts"],
        "D_A_applied_counts": da["applied_counts"],
        "D_B_language_null_counts": db["language_null_counts"],
        "D_B_top_level_query_present": db["top_level_query_present"],
        "D_B_provenance_query_key_present": db["provenance_query_key_present"],
        "frozen_pins_unchanged": pins_unchanged,
        "log": str(log_path),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
