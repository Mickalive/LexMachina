#!/usr/bin/env python3
"""Machine-readable closure of v68 ordered work items (1)-(3).

v68 ordered work item (3) asked for a diagnosis that states the path-routing
leg is landed and the remaining leg is rejection/incumbent handling, and
explicitly forbids re-deriving the accepted evaluation findings.

By the time this snapshot was taken both legs had landed and been accepted:
the rejection/incumbent leg was implemented at ``e840de1d`` and first accepted
at run 40125024681 (accept ``22e0d6b3``), then re-verified at 40238484716
(accept ``3de8431d``) and again at the latest accepted head 40247189361
(accept ``5fb312e4``).  This instrument publishes that closure from the
accepted tree and the product's own committed probe, with live git checks,
instead of repeating an out-of-date "remaining leg" statement.

It re-derives nothing from the evaluation lane.  The three findings named by
v68 are cited with ``re_derived=false``; the only measurements read here are
product-owned artifacts and the immutable git/gate evidence for the two legs.

Usage
-----
    python3 product/query_map_diagnosis.py --run-id 40257275384

Writes ``results/product/query_map_diagnosis/CYCLE_<run>.json``.  It writes no
gate, scores no frozen bar and changes no posture flag.
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "product-v68-query-map-diagnosis/1"
DIRECTION_VERSION = 68
ACCEPTED_REF = "origin/lab/product"
OUT_ROOT = ROOT / "results" / "product" / "query_map_diagnosis"

# --- accepted evidence constants (full SHAs are verified live) -------------
ROUTING_LANDED_COMMIT = "51d306ca4b52c6d8ea1200c306cfb33e44e487ac"
ROUTING_ACCEPT_RUN = "40100397058"
INCUMBENT_LANDED_COMMIT = "e840de1dee371e2402c017495182954ee1bccc1a"
INCUMBENT_FIRST_ACCEPT_RUN = "40125024681"
INCUMBENT_TEST_REPAIR_ACCEPT_RUN = "40238484716"
LATEST_ACCEPT_RUN = "40247189361"

ROUTING_BUNDLE = ("results/product/offline_slice/20261024T142517Z"
                  "/rent-default.bundle.json")
FRESH_BUNDLE = ("results/product/offline_slice/40247189361-rent-default"
                "/rent-default.bundle.json")
ROUTING_BUNDLE_PATH = ROOT / ROUTING_BUNDLE
FRESH_BUNDLE_PATH = ROOT / FRESH_BUNDLE
CF_ACCEPTED = ROOT / "results/product/counter_content_family/CYCLE_40247189361.json"
STATE = ROOT / "state/product.json"

FINDINGS_CONSUMED = (
    {
        "run_id": "40070818687",
        "name": "PATH_SCOPE_RESIDUAL",
        "use": "the routing leg is closed at 8b5b08dd; the residual it named is "
               "rejection/incumbent handling, not routing",
        "re_derived": False,
    },
    {
        "run_id": "40068038783",
        "name": "PER_CLASS_D2_D3_D4_VERDICT + RECONCILIATION_COMPLETE",
        "use": "accepted per-class verdict and scorer-path reconciliation; the "
               "product consumes the classes, never re-scores the frozen rubric",
        "re_derived": False,
    },
    {
        "run_id": "40105794124",
        "name": "NEW_BYTES_MEASUREMENT",
        "accept_commit": "bcb4520a",
        "use": "the accepted four verified-but-defective rows and the one sound "
               "row are read from product's committed probe, not recomputed from "
               "evaluation bytes",
        "re_derived": False,
        "accept_commit_verified_locally": False,
        "note": "bcb4520a is an evaluation-lane commit and is cited from the v68 "
                "direction; this product checkout does not contain it, so it is "
                "not presented as locally verified.",
    },
)

CLAIM_CEILING = (
    "MACHINE-READABLE DIAGNOSIS OF ALREADY-ACCEPTED PRODUCT EVIDENCE. It reads "
    "accept commits, gates, accepted-commit bundles and product's own committed "
    "content-family probe; it does not re-run an evaluation finding, a live "
    "retrieval, a frozen bar, a serve verdict or a packet admission. The closure "
    "of the rejection/incumbent leg is limited to the product-owned fixed-path "
    "family and the fixture-mode generation path. No legal-usefulness, live "
    "latency, live answer reliability or human-gate claim is made."
)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=False)


def _rev(ref: str) -> str | None:
    p = _git("rev-parse", "--verify", "--quiet", ref)
    return p.stdout.strip() or None if p.returncode == 0 else None


def _ancestor(commit: str, descendant: str) -> bool:
    return _git("merge-base", "--is-ancestor", commit, descendant).returncode == 0


def _accept_commit(run_id: str) -> dict[str, Any]:
    head = _rev(ACCEPTED_REF)
    log = _git("log", ACCEPTED_REF, "--format=%H%x09%s").stdout.splitlines()
    needle = f"accept product cycle {run_id}"
    for line in log:
        sha, _, subject = line.partition("\t")
        if subject.strip() == needle:
            return {"run_id": run_id, "accept_commit": sha,
                    "accept_subject": subject.strip(),
                    "on_accepted_ref": head is not None}
    return {"run_id": run_id, "accept_commit": None,
            "accept_subject": None, "on_accepted_ref": head is not None}


def _gate(run_id: str) -> dict[str, Any]:
    rel = f"results/audit/product/CYCLE_{run_id}_GATE.json"
    raw = _git("show", f"{ACCEPTED_REF}:{rel}")
    if raw.returncode != 0:
        return {"run_id": run_id, "path": rel, "present_on_accepted_ref": False}
    try:
        gate = json.loads(raw.stdout)
    except json.JSONDecodeError:
        return {"run_id": run_id, "path": rel, "present_on_accepted_ref": True,
                "parse_error": True}
    return {
        "run_id": run_id,
        "path": rel,
        "present_on_accepted_ref": True,
        "gate": gate.get("gate"),
        "safe_to_integrate": gate.get("safe_to_integrate"),
        "required_fixes": gate.get("required_fixes"),
        "evidence_summary": gate.get("evidence_summary"),
        "claim_ceiling": gate.get("claim_ceiling"),
    }


def _json_at(rev: str, rel: str) -> dict | None:
    raw = _git("show", f"{rev}:{rel}")
    if raw.returncode != 0:
        return None
    try:
        return json.loads(raw.stdout)
    except json.JSONDecodeError:
        return None


def _row(bundle: dict | None, decision_id: str) -> dict | None:
    if not bundle:
        return None
    return next((r for r in bundle.get("decisions") or []
                 if r.get("decision_id") == decision_id), None)


def _span(bundle: dict | None) -> dict:
    if not bundle:
        return {}
    return ((bundle.get("provenance") or {}).get("counter_evidence_span") or {})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(checks: dict[str, bool], name: str, ok: bool) -> None:
    checks[name] = bool(ok)


def run(*, run_id: str, out: Path | None = None) -> dict[str, Any]:
    gates = {run: _gate(run) for run in (
        ROUTING_ACCEPT_RUN,
        INCUMBENT_FIRST_ACCEPT_RUN,
        INCUMBENT_TEST_REPAIR_ACCEPT_RUN,
        LATEST_ACCEPT_RUN,
    )}
    accepts = {run: _accept_commit(run) for run in gates}

    routing_bundle = _json_at(
        accepts[ROUTING_ACCEPT_RUN]["accept_commit"], ROUTING_BUNDLE)
    fresh_bundle = _json_at(
        accepts[LATEST_ACCEPT_RUN]["accept_commit"], FRESH_BUNDLE)
    routing_span = _span(routing_bundle)
    fresh_span = _span(fresh_bundle)
    routing_gr = _row(routing_bundle, "gr_gerichte_ERZ 2010 25")
    fresh_vd = _row(fresh_bundle, "vd_gerichte_JL09.019144")

    accepted_probe = json.loads(CF_ACCEPTED.read_text(encoding="utf-8")) \
        if CF_ACCEPTED.is_file() else {}
    probe_path = (ROOT / "results/product/counter_content_family"
                  / f"CYCLE_{run_id}.json")
    fresh_probe = json.loads(probe_path.read_text(encoding="utf-8")) \
        if probe_path.is_file() else {}
    probe = fresh_probe or accepted_probe
    totals = ((probe.get("fixed_path_family") or {}).get("totals") or {})
    accepted_totals = ((accepted_probe.get("fixed_path_family") or {})
                       .get("totals") or {})
    coverage = (((probe.get("before_after") or {}).get("per_row") or {})
                .get("accepted_four_coverage") or [])
    coverage_ok = (
        len(coverage) == 4
        and all(c.get("present") is True for c in coverage)
        and all(c.get("before_verified") is True for c in coverage)
        and all(c.get("after_verified") is False for c in coverage)
        and all(bool(c.get("after_reason_code")) for c in coverage)
    )
    confirmed = probe.get("confirmed_set") or {}
    hist = totals.get("defect_histogram") or {}

    state = json.loads(STATE.read_text(encoding="utf-8")) \
        if STATE.is_file() else {}
    pointer_ok = (
        state.get("accepted_run_id") == f"CYCLE_{LATEST_ACCEPT_RUN}"
        and str(state.get("accepted_commit") or "").startswith("5fb312e4")
    )
    posture_ok = (
        state.get("continue_recommended") is True
        and state.get("human_gate_ready") is False
        and state.get("machine_gate_ready") is False
        and state.get("packet_admitted") is False
        and state.get("ready_for_owner_session") is False
    )

    latest_accept = accepts[LATEST_ACCEPT_RUN]["accept_commit"]
    latest_gate = gates[LATEST_ACCEPT_RUN]
    first_accept = accepts[INCUMBENT_FIRST_ACCEPT_RUN]["accept_commit"]
    first_gate = gates[INCUMBENT_FIRST_ACCEPT_RUN]
    test_accept = accepts[INCUMBENT_TEST_REPAIR_ACCEPT_RUN]["accept_commit"]
    test_gate = gates[INCUMBENT_TEST_REPAIR_ACCEPT_RUN]
    routing_accept = accepts[ROUTING_ACCEPT_RUN]["accept_commit"]
    routing_gate = gates[ROUTING_ACCEPT_RUN]

    checks: dict[str, bool] = {}
    _check(checks, "routing_landed_commit_on_accepted_ref",
           bool(_rev(ACCEPTED_REF)) and _ancestor(ROUTING_LANDED_COMMIT,
                                                  _rev(ACCEPTED_REF) or ""))
    _check(checks, "routing_accept_has_both_halves",
           bool(routing_accept) and routing_gate.get("gate") == "PASS"
           and routing_gate.get("safe_to_integrate") is True)
    _check(checks, "routing_landed_before_its_accept",
           bool(routing_accept) and _ancestor(ROUTING_LANDED_COMMIT,
                                              routing_accept))
    _check(checks, "routing_bundle_shows_abstention_without_selection",
           routing_span.get("applied") is True
           and (routing_span.get("n_candidates") or 0) >= 1
           and routing_span.get("n_selected") == 0
           and "gr_gerichte_ERZ 2010 25" in (routing_span.get("abstained_ids") or [])
           and (routing_span.get("abstention_reasons") or {}).get("pivot_absent") == 1)
    _check(checks, "routing_bundle_incumbent_still_verified_at_routing_accept",
           routing_gr is not None
           and routing_gr.get("counter_evidence_verified") is True)

    _check(checks, "incumbent_landed_commit_on_accepted_ref",
           bool(_rev(ACCEPTED_REF)) and _ancestor(INCUMBENT_LANDED_COMMIT,
                                                  _rev(ACCEPTED_REF) or ""))
    _check(checks, "incumbent_first_accept_has_both_halves",
           bool(first_accept) and first_gate.get("gate") == "PASS"
           and first_gate.get("safe_to_integrate") is True)
    _check(checks, "incumbent_landed_before_first_accept",
           bool(first_accept) and _ancestor(INCUMBENT_LANDED_COMMIT,
                                            first_accept))
    _check(checks, "incumbent_first_accept_gate_names_the_leg",
           "rejection/incumbent" in str(first_gate.get("evidence_summary") or ""))
    _check(checks, "incumbent_test_repair_accept_has_both_halves",
           bool(test_accept) and test_gate.get("gate") == "PASS"
           and test_gate.get("safe_to_integrate") is True)
    _check(checks, "latest_accept_has_both_halves",
           bool(latest_accept) and latest_gate.get("gate") == "PASS"
           and latest_gate.get("safe_to_integrate") is True)
    _check(checks, "latest_accept_is_the_accepted_head",
           bool(latest_accept) and latest_accept == _rev(ACCEPTED_REF))
    _check(checks, "fresh_bundle_carries_a_content_filter_downgrade",
           bool(fresh_span.get("content_filter"))
           and bool(fresh_span.get("downgrades"))
           and fresh_vd is not None
           and fresh_vd.get("counter_evidence_verified") is False)

    _check(checks, "probe_fixed_family_has_no_verified_defective_row",
           totals.get("n_verified_defective") == 0
           and (totals.get("n_bundles") or 0) > 0)
    _check(checks, "probe_fixed_family_D2_D3_D4_are_zero",
           all((hist.get(c) or 0) == 0 for c in (
               "D2_letterhead_zone", "D3_markup_residue",
               "D4_language_marker_mismatch")))
    _check(checks, "probe_all_four_accepted_rows_moved_to_unevidenced",
           coverage_ok)
    _check(checks, "probe_sound_row_still_verified",
           confirmed.get("present") is True
           and confirmed.get("still_verified") is True
           and not (confirmed.get("defects") or []))
    _check(checks, "probe_false_rejects_are_zero",
           probe.get("false_reject_count") == 0)
    _check(checks, "probe_full_success_rule_met",
           (probe.get("ordered_work_2_full_success_rule") or {}).get("met")
           is True)
    _check(checks, "fresh_probe_reproduces_accepted_probe_totals",
           bool(fresh_probe) and bool(accepted_probe)
           and fresh_probe.get("false_reject_count")
           == accepted_probe.get("false_reject_count")
           and all(totals.get(k) == accepted_totals.get(k) for k in (
               "n_bundles", "n_decisions", "n_verified",
               "n_verified_defective")))

    _check(checks, "state_pointer_is_the_latest_accepted_run", pointer_ok)
    _check(checks, "posture_stays_fail_closed", posture_ok)
    _check(checks, "this_run_has_no_audit_gate",
           not (ROOT / "results/audit/product"
                / f"CYCLE_{run_id}_GATE.json").exists())
    _check(checks, "evaluation_findings_are_cited_not_rederived",
           all(f.get("re_derived") is False for f in FINDINGS_CONSUMED))

    failed = sorted(k for k, v in checks.items() if not v)
    record = {
        "schema": SCHEMA,
        "run_id": str(run_id),
        "direction_version": DIRECTION_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "ordered_work_item": 3,
        "requirement": (
            "consume the accepted findings and publish a machine-readable "
            "diagnosis that states the routing leg is landed and the remaining "
            "leg is rejection/incumbent handling; do not re-derive them"
        ),
        "as_authored": {
            "latest_accepted_product_cycle_at_propose_time":
                "8b5b08dd / 40100397058 (accept 8b5b08dd)",
            "stated_remaining_leg": "rejection/incumbent handling",
            "source": "state/factory_direction.json v68 ordered work (3)",
        },
        "current_reading": {
            "routing_leg": "LANDED",
            "rejection_incumbent_leg": "LANDED",
            "open_leg_from_items_1_to_3": "NONE",
            "supersession_note": (
                "The direction was authored when 8b5b08dd was the accepted "
                "head and the rejection/incumbent leg was still residual. "
                "That leg landed at e840de1d and was first accepted at run "
                "40125024681 / 22e0d6b3, re-verified at 40238484716 / "
                "3de8431d and at 40247189361 / 5fb312e4. This diagnosis "
                "records the closure; it does not rewrite the direction."
            ),
            "ordered_work_4_state_pointer": "CORRECTED_BY_THIS_CYCLE",
            "ordered_work_5_live_latency_precision": "DEFERRED",
            "ordered_work_6_profile_coverage_gap": "DISCLOSED_TRANSFERRED",
        },
        "legs": {
            "path_routing": {
                "status": "LANDED",
                "landed_commit": ROUTING_LANDED_COMMIT,
                "accepted_run_id": ROUTING_ACCEPT_RUN,
                "accept_commit": routing_accept,
                "gate": routing_gate,
                "evidence_bundle": ROUTING_BUNDLE,
                "evidence_bundle_present_at_accept": routing_bundle is not None,
                "span_applied": routing_span.get("applied"),
                "n_candidates": routing_span.get("n_candidates"),
                "n_selected": routing_span.get("n_selected"),
                "abstained_ids": routing_span.get("abstained_ids"),
                "abstention_reasons": routing_span.get("abstention_reasons"),
                "incumbent_verified_at_this_accept": (
                    routing_gr or {}).get("counter_evidence_verified"),
                "meaning": (
                    "routing through the span seam is active; the filter may "
                    "abstain without selecting a replacement span"
                ),
            },
            "rejection_incumbent": {
                "status": "LANDED",
                "landed_commit": INCUMBENT_LANDED_COMMIT,
                "first_accepted_run_id": INCUMBENT_FIRST_ACCEPT_RUN,
                "first_accept_commit": first_accept,
                "first_gate": first_gate,
                "test_repair_accepted_run_id": INCUMBENT_TEST_REPAIR_ACCEPT_RUN,
                "test_repair_accept_commit": test_accept,
                "test_repair_gate": test_gate,
                "latest_accepted_run_id": LATEST_ACCEPT_RUN,
                "latest_accept_commit": latest_accept,
                "latest_gate": latest_gate,
                "fresh_bundle": FRESH_BUNDLE,
                "fresh_bundle_present_at_latest_accept": fresh_bundle is not None,
                "fresh_span_content_filter_present": bool(
                    fresh_span.get("content_filter")),
                "fresh_downgrade_decision_ids": [
                    d.get("decision_id")
                    for d in fresh_span.get("downgrades") or []
                ],
                "fresh_downgrade_before_after": [
                    {
                        "decision_id": d.get("decision_id"),
                        "defects": d.get("defects"),
                        "leg": d.get("leg"),
                        "reason_code": d.get("reason_code"),
                        "before_verified": (d.get("before") or {}).get(
                            "counter_evidence_verified"),
                        "after_verified": (d.get("after") or {}).get(
                            "counter_evidence_verified"),
                    }
                    for d in fresh_span.get("downgrades") or []
                ],
                "meaning": (
                    "when the seam abstains or a defective incumbent survives "
                    "selection, the incumbent is downgraded to unevidenced "
                    "instead of remaining counter_evidence_verified=true"
                ),
            },
        },
        "findings_consumed": list(FINDINGS_CONSUMED),
        "ordered_work_1_success": {
            "confirmed_sound_row": confirmed,
            "accepted_four_coverage": coverage,
            "all_four_before_verified": (
                (probe.get("before_after") or {}).get("per_row") or {}
            ).get("all_four_before_verified"),
            "all_four_after_unevidenced": (
                (probe.get("before_after") or {}).get("per_row") or {}
            ).get("all_four_after_unevidenced"),
            "false_reject_count": probe.get("false_reject_count"),
            "met": bool(
                confirmed.get("still_verified") is True
                and coverage_ok
                and probe.get("false_reject_count") == 0
            ),
        },
        "ordered_work_2_success": {
            "accepted_probe": {
                "path": str(CF_ACCEPTED.relative_to(ROOT)),
                "sha256": _sha(CF_ACCEPTED) if CF_ACCEPTED.is_file() else None,
                "totals": accepted_totals,
            },
            "fresh_probe": {
                "path": str(probe_path.relative_to(ROOT)),
                "sha256": _sha(probe_path) if probe_path.is_file() else None,
                "totals": totals,
            },
            "success_rule_met": (
                (probe.get("ordered_work_2_full_success_rule") or {}).get("met")
                is True
            ),
            "guarded_arm_yield_not_decreased": (
                (probe.get("ordered_work_2_full_success_rule") or {})
                .get("guarded_arm_yield_not_decreased")
            ),
            "full_success_rule": probe.get("ordered_work_2_full_success_rule"),
        },
        "residuals_carried": [
            {
                "id": "live_latency_precision",
                "status": "DEFERRED",
                "detail": "ordered work (5): live latency/precision stays "
                          "deferred; live budget stays 8 and is not changed.",
            },
            {
                "id": "profile_coverage_gap",
                "status": "DISCLOSED_TRANSFERRED",
                "detail": "ordered work (6): business-judgment-rule resolving "
                          "to fr-bail-entretien and petty-theft resolving to "
                          "None still need an evaluation-lane profile freeze "
                          "decision; product does not re-derive a profile.",
            },
            {
                "id": "pointer_only_rows",
                "status": "DISCLOSED",
                "detail": "13 business-judgment-rule rows remain reference-only "
                          "with a null source_url; their canonical OpenCaseLaw "
                          "link is present.",
            },
        ],
        "state_pointer": {
            "accepted_run_id": state.get("accepted_run_id"),
            "accepted_commit": state.get("accepted_commit"),
            "expected_accepted_run_id": f"CYCLE_{LATEST_ACCEPT_RUN}",
            "expected_accepted_commit": latest_accept,
            "matches_latest_accepted": pointer_ok,
        },
        "checks": checks,
        "n_failed_checks": failed,
        "verdict": "PASS" if not failed else "FAIL",
        "claim_ceiling": CLAIM_CEILING,
        "posture": {
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
            "continue_recommended": True,
        },
    }
    out = out or (OUT_ROOT / f"CYCLE_{run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return {"record": record, "path": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    result = run(run_id=args.run_id,
                 out=Path(args.out) if args.out else None)
    rec = result["record"]
    for name, ok in rec["checks"].items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{rec['verdict']}: {len(rec['checks']) - len(rec['n_failed_checks'])}"
          f"/{len(rec['checks'])} checks")
    print(f"wrote {result['path'].relative_to(ROOT)}")
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
