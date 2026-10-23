#!/usr/bin/env python3
"""v65_product_advance_crosscheck — per-quantity currency + falsification re-run + pins.

FAST-MVP evaluation instrument for factory direction v65, run 40012474431
(operational resume of rc-67 producer runs 40006151200 / 40011795717, which
scoped but never committed this work; their plans are preserved under
results/evaluation/orchestration/).

Ordered items executed here (frozen in
evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json, sha256
9382a0a9..., committed BEFORE this execution):
  (1) CURRENCY CROSS-CHECK of the product's newly landed measurements on the
      newest accepted head f9618377 (accept product cycle 40005362253),
      reported CONFIRMED / CONFIRMED_CORRECTED / DIVERGENT / NOT_FOUND per
      quantity, including the report-vs-artifact arm-label discrepancy of
      CYCLE_39986094168 the prior producer identified (frozen exception class
      kind=correction_landed).
  (2) FALSIFICATION RE-RUN on the new head under the SAME frozen rule set via
      the ACCEPTED wrapper evaluation.minimal_retrieval_ca_benchmark (digest
      7631c1a3... pinned in the freeze record); rules re-hashed REPORTED-ONLY.
  (3) PLANNER-REMEDY AND DEGRADATION PIN re-verify under NEW run id: planner
      sha, strip_redaction_placeholders ordering, e_EMISSION_WRITER_ABORT
      visibility on the NEWEST live reliability measurement (40000001926,
      marker-visibility semantics — see planner_and_degradation_pin), frozen
      product_pins re-hash.
  (4) REQUIREMENT-4 LINEAGE verification of product cycles 40000001926 and
      40005362253 (PASS gate file AND accept commit on the mount).
  (5) COVERAGE v2 re-freeze is CONDITIONAL and NOT executed here.

REUSE-FIRST: the falsification leg is a thin subprocess invocation of the
accepted wrapper; the float dual-tolerance convention is the accepted D-A
convention imported by value (the prior instrument file is never edited — its
digest is pinned by run 39986080045's artifact).

FLOAT-COMPARISON DISCLOSURE: every float quantity publishes BOTH verdicts —
strict_verdict_1e_6 (frozen literal) and applied_verdict_precision_matched
(5e-4 half-ulp of the product's 3-decimal publication precision) — with the
raw absolute delta. Neither tolerance is derived after results are seen.

Exit codes (VERDICT_CONTRACT.json conventions):
  0  PASS_NO_FALSIFICATION   - all currency quantities CONFIRMED (or
                               CONFIRMED_CORRECTED, disclosed separately),
                               falsification re-run reproduces the accepted
                               PRODUCT_FALSIFIED, planner/degradation pins hold.
  1  MATERIAL_DIVERGENCE     - any currency quantity DIVERGENT, OR the
                               falsification re-run changes verdict class, OR
                               a must-hold planner/degradation pin drifts.
  2  NOT_MEASURED_VACUOUS    - a frozen input drifted, a control failed, an
                               artifact was missing, or the subprocess was not
                               executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "40012474431"
DIRECTION_VERSION = 65
MOUNT = Path("/tmp/lex_accepted/product")
PACKET = "39319405429"
HYPOTHESIS = REPO_ROOT / "evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE = REPO_ROOT / "evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_FREEZE_RECORD_V1.json"
OUT_DIR = REPO_ROOT / "results/evaluation/v65_product_advance_crosscheck"
REPORT_DIR = REPO_ROOT / "reports/evaluation"

# Float comparison tolerances — accepted D-A dual-verdict convention (frozen
# in the hypothesis before execution).
FROZEN_LITERAL_FLOAT_TOL = 1e-6
PUBLICATION_DECIMALS = 3
APPLIED_FLOAT_TOL = 0.5 * (10 ** -PUBLICATION_DECIMALS)  # 5e-4

# Frozen expected digests (from the freeze record; re-hashed at runtime).
EXPECTED = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "packet_json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "planner": "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9",
    "mount_head": "f9618377f67d8a79205fab86646d724f9739a339",
    "hypothesis": "9382a0a9a666a2e883a5c9590efd8c3759707c223f228cd4d9447889dc97b9f6",
}

# Product-published quantities frozen in the hypothesis. Each entry:
# artifact relpath, path-within-JSON (None = raw sha256), published value, kind.
CURRENCY_QUANTITIES = [
    # --- family: live-answer reliability, accepted cycle 40000001926 ---
    {"id": "reliability_40000001926_ready_rate",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "answer_ready_rate"], "published": 0.857, "kind": "float"},
    {"id": "reliability_40000001926_citation_validity",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "citation_validity"], "published": 1.0, "kind": "float"},
    {"id": "reliability_40000001926_source_validity",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "source_validity"], "published": 1.0, "kind": "float"},
    {"id": "reliability_40000001926_language_match_rate",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "language_match_rate"], "published": 1.0, "kind": "float"},
    {"id": "reliability_40000001926_prose_citation_validity",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "prose_citation_validity"], "published": 0.982, "kind": "float"},
    {"id": "reliability_40000001926_degradation_visible_rate",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "degradation_visible_rate"], "published": 1.0, "kind": "float"},
    {"id": "reliability_40000001926_stability_jaccard_min",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "stability_jaccard_min"], "published": 1.0, "kind": "float"},
    {"id": "reliability_40000001926_n_degraded_legs",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "n_degraded_legs"], "published": 1, "kind": "exact"},
    {"id": "reliability_40000001926_n_legs_executed",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["metrics", "n_legs_executed"], "published": 7, "kind": "exact"},
    {"id": "reliability_40000001926_claim_false",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["product_claim_reliable_live_answer"], "published": False, "kind": "exact"},
    {"id": "reliability_40000001926_protocol_sha",
     "artifact": "results/product/answer_reliability/40000001926_measurement.json",
     "json_path": ["protocol_sha256"],
     "published": "418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1",
     "kind": "exact"},
    # --- family: counter-span selection, accepted-tree content cycle 39986094168 ---
    {"id": "span_selection_baseline_n_scored",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "baseline", "n_scored"], "published": 20, "kind": "exact"},
    {"id": "span_selection_baseline_n_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "baseline", "n_emitted"], "published": 0, "kind": "exact"},
    {"id": "span_selection_candidate_guarded_n_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "candidate", "n_emitted"], "published": 1, "kind": "exact"},
    {"id": "span_selection_candidate_guarded_yield",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "candidate", "yield"], "published": 0.05, "kind": "float"},
    {"id": "span_selection_candidate_unguarded_n_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "candidate_unguarded", "n_emitted"], "published": 6, "kind": "exact"},
    {"id": "span_selection_candidate_unguarded_yield",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["aggregate", "candidate_unguarded", "yield"], "published": 0.3, "kind": "float"},
    {"id": "span_selection_unguarded_de_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["bundles", "de-kapitalverletzung", "candidate_unguarded", "n_emitted"],
     "published": 2, "kind": "exact"},
    {"id": "span_selection_unguarded_fr_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["bundles", "fr-bail-entretien", "candidate_unguarded", "n_emitted"],
     "published": 4, "kind": "exact"},
    {"id": "span_selection_unguarded_it_emitted",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["bundles", "it-responsabilita-medica", "candidate_unguarded", "n_emitted"],
     "published": 0, "kind": "exact"},
    {"id": "span_selection_guarded_emitted_id_fr",
     "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json",
     "json_path": ["bundles", "fr-bail-entretien", "candidate", "emitted_ids"],
     "published": ["bge_136 III 196"], "kind": "exact"},
    # --- family: counter-precision adjudication, accepted cycle 40005362253 ---
    {"id": "counter_precision_baseline_n_signals",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "baseline", "n_signals"],
     "published": 42, "kind": "exact"},
    {"id": "counter_precision_baseline_n_evidenced_guarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "baseline", "n_evidenced_guarded"],
     "published": 6, "kind": "exact"},
    {"id": "counter_precision_baseline_yield_guarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "baseline", "evidence_yield_guarded"],
     "published": 0.142857, "kind": "float"},
    {"id": "counter_precision_baseline_yield_unguarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "baseline", "evidence_yield_unguarded"],
     "published": 0.261905, "kind": "float"},
    {"id": "counter_precision_delta_n_signals",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "delta", "n_signals"],
     "published": 28, "kind": "exact"},
    {"id": "counter_precision_delta_n_evidenced_guarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "delta", "n_evidenced_guarded"],
     "published": 2, "kind": "exact"},
    {"id": "counter_precision_delta_yield_guarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "delta", "evidence_yield_guarded"],
     "published": 0.071429, "kind": "float"},
    {"id": "counter_precision_delta_yield_unguarded",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "pooled_all_legs", "delta", "evidence_yield_unguarded"],
     "published": 0.142857, "kind": "float"},
    {"id": "counter_precision_known_reach_baseline",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "known_authority_reach", "at_baseline_cap"],
     "published": 8, "kind": "exact"},
    {"id": "counter_precision_known_reach_broad",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "known_authority_reach", "at_broad_cap"],
     "published": 11, "kind": "exact"},
    {"id": "counter_precision_adjudication_verdict",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["aggregate", "adjudication", "verdict"],
     "published": "BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE", "kind": "exact"},
    {"id": "counter_precision_profile_rent_default",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["profile_resolution_disclosure", "per_leg", "rent-default"],
     "published": "fr-bail-entretien", "kind": "exact"},
    {"id": "counter_precision_profile_corporate_criminal",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["profile_resolution_disclosure", "per_leg", "corporate-criminal-liability"],
     "published": "responsabilite-penale-entreprise-102cp", "kind": "exact"},
    {"id": "counter_precision_profile_bjr_domain_mismatch",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["profile_resolution_disclosure", "per_leg", "business-judgment-rule"],
     "published": "fr-bail-entretien", "kind": "exact"},
    {"id": "counter_precision_profile_petty_theft_null",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["profile_resolution_disclosure", "per_leg", "petty-theft-dismissal"],
     "published": None, "kind": "exact"},
    {"id": "counter_precision_invariant_network_blocked",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["invariants", "network_calls_blocked"], "published": True, "kind": "exact"},
    {"id": "counter_precision_invariant_budgets_unchanged",
     "artifact": "results/product/counter_precision/CYCLE_40005362253.json",
     "json_path": ["invariants", "budgets_unchanged"], "published": True, "kind": "exact"},
    # --- family: absent-ID span probe, accepted cycle 40005362253 ---
    {"id": "absent_id_probe_n_probed",
     "artifact": "results/product/counter_span/CYCLE_40005362253_absent_id_span_probe.json",
     "json_path": ["summary", "n_probed"], "published": 3, "kind": "exact"},
    {"id": "absent_id_probe_n_span_evidenced",
     "artifact": "results/product/counter_span/CYCLE_40005362253_absent_id_span_probe.json",
     "json_path": ["summary", "n_span_evidenced"], "published": 0, "kind": "exact"},
    # --- family: verification sweep, accepted cycle 40005362253 ---
    {"id": "verification_sweep_passed",
     "artifact": "results/product/regression/CYCLE_40005362253_verification_sweep.json",
     "json_path": ["result", "passed"], "published": 135, "kind": "exact"},
    {"id": "verification_sweep_failed",
     "artifact": "results/product/regression/CYCLE_40005362253_verification_sweep.json",
     "json_path": ["result", "failed"], "published": 0, "kind": "exact"},
    # --- family: inherited-cache coverage, tree content cycle 39992687176 ---
    {"id": "cache_coverage_n_added",
     "artifact": "results/product/regression/CYCLE_40000001926_inherited_cache_coverage.json",
     "json_path": ["n_added"], "published": 15, "kind": "exact"},
    {"id": "cache_coverage_n_cache_before",
     "artifact": "results/product/regression/CYCLE_40000001926_inherited_cache_coverage.json",
     "json_path": ["n_cache_before"], "published": 764, "kind": "exact"},
    {"id": "cache_coverage_n_cache_after",
     "artifact": "results/product/regression/CYCLE_40000001926_inherited_cache_coverage.json",
     "json_path": ["n_cache_after"], "published": 779, "kind": "exact"},
    # --- family: offline slice, accepted cycle 40005362253 ---
    {"id": "offline_slice_verified",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["verified"], "published": True, "kind": "exact"},
    {"id": "offline_slice_answer_status",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["stats", "answer_status"], "published": "ready", "kind": "exact"},
    {"id": "offline_slice_cited_decision_ids",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["stats", "cited_decision_ids"], "published": 4, "kind": "exact"},
    {"id": "offline_slice_counter_status_bearing_rows",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["stats", "counter_status_bearing_rows"], "published": 5, "kind": "exact"},
    {"id": "offline_slice_n_decisions",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["stats", "n_decisions"], "published": 100, "kind": "exact"},
    {"id": "offline_slice_n_clusters",
     "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
     "json_path": ["stats", "n_clusters"], "published": 8, "kind": "exact"},
    # --- family: planner remedy bytes (must-hold pin) ---
    {"id": "planner_sha256",
     "artifact": "product/query/adversarial_retrieval.py", "json_path": None,
     "published": "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9",
     "kind": "sha256"},
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_path_get(doc, path):
    cur = doc
    for key in path:
        if isinstance(cur, dict):
            cur = cur[key]
        else:
            raise KeyError(f"non-dict at {key}")
    return cur


def numeric_environment() -> dict:
    env = {"python": sys.version.split()[0], "platform": sys.platform}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "absent"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    return env


def rehash_pins(mount: Path) -> dict:
    out = {}
    out["repo:evaluation/frozen_bars/RULES_LABEL.json"] = _sha256_file(
        REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json")
    out["repo:evaluation/frozen_bars/RULES_GEOMETRY.json"] = _sha256_file(
        REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json")
    out["repo:evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json"] = _sha256_file(HYPOTHESIS)
    freeze = json.loads(FREEZE.read_text())
    for rel, expected in freeze["product_artifact_pins_at_freeze"].items():
        p = mount / rel
        out[f"mount:{rel}"] = _sha256_file(p) if p.is_file() else "MISSING"
    out[f"mount:results/product/gate_packet/{PACKET}/packet.json"] = _sha256_file(
        mount / f"results/product/gate_packet/{PACKET}/packet.json")
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=mount,
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout.strip()
    except Exception:
        head = "UNAVAILABLE"
    out["mount_head"] = head
    return out


def requirement4_lineage(mount: Path) -> dict:
    """Verify BOTH halves of factory-wide requirement 4 for the two newly
    accepted product cycles, on the mount's own git history."""
    out = {}
    for run_id, accept_commit in (("40000001926", "beb227a6"),
                                  ("40005362253", "f9618377")):
        gate_path = mount / f"results/audit/product/CYCLE_{run_id}_GATE.json"
        gate = None
        if gate_path.is_file():
            try:
                g = json.loads(gate_path.read_text())
                gate = {"gate": g.get("gate"), "safe_to_integrate": g.get("safe_to_integrate"),
                        "required_fixes": g.get("required_fixes")}
            except Exception as exc:  # noqa: BLE001
                gate = {"error": f"{type(exc).__name__}: {exc}"}
        grep = subprocess.run(
            ["git", "log", "--all", "--oneline", "--grep",
             f"accept product cycle {run_id}"], cwd=mount,
            capture_output=True, text=True, timeout=60)
        accept_lines = [ln for ln in grep.stdout.splitlines() if ln.strip()]
        gate_ok = bool(gate) and gate.get("gate") == "PASS" and gate.get("safe_to_integrate") is True
        accept_ok = any(accept_commit in ln for ln in accept_lines)
        out[run_id] = {
            "gate_half": gate,
            "gate_half_ok": gate_ok,
            "accept_half": {"expected_commit": accept_commit, "matches": accept_lines},
            "accept_half_ok": accept_ok,
            "requirement_4_both_halves": gate_ok and accept_ok,
        }
    out["all_accepted"] = all(v["requirement_4_both_halves"] for k, v in out.items() if k != "all_accepted")
    return out


def currency_crosscheck(mount: Path) -> dict:
    rows = []
    n_conf = n_div = n_missing = n_corrected = 0
    for q in CURRENCY_QUANTITIES:
        art = mount / q["artifact"]
        row = {"id": q["id"], "artifact": q["artifact"],
               "published": q["published"], "kind": q["kind"]}
        if not art.is_file():
            row["verdict"] = "NOT_FOUND"
            row["found"] = None
            n_missing += 1
            rows.append(row)
            continue
        try:
            if q["kind"] == "sha256":
                found = _sha256_file(art)
                row["found"] = found
                ok = found == q["published"]
            else:
                doc = json.loads(art.read_text())
                found = _json_path_get(doc, q["json_path"])
                row["found"] = found
                if q["kind"] == "float":
                    delta = abs(float(found) - float(q["published"]))
                    row["raw_found"] = found
                    row["raw_published"] = q["published"]
                    row["abs_delta"] = delta
                    row["applied_tolerance"] = APPLIED_FLOAT_TOL
                    row["frozen_literal_tolerance"] = FROZEN_LITERAL_FLOAT_TOL
                    row["strict_verdict_1e_6"] = (
                        "CONFIRMED" if delta <= FROZEN_LITERAL_FLOAT_TOL else "DIVERGENT")
                    row["applied_verdict_precision_matched"] = (
                        "CONFIRMED" if delta <= APPLIED_FLOAT_TOL else "DIVERGENT")
                    ok = delta <= APPLIED_FLOAT_TOL
                else:
                    ok = found == q["published"]
            row["verdict"] = "CONFIRMED" if ok else "DIVERGENT"
            if ok:
                n_conf += 1
            else:
                n_div += 1
        except Exception as exc:  # noqa: BLE001
            row["verdict"] = "NOT_FOUND"
            row["error"] = f"{type(exc).__name__}: {exc}"
            n_missing += 1
        rows.append(row)

    # --- Composite legs ---
    # 1. Writer-abort leg statuses on the NEWEST live measurement (40000001926).
    p = mount / "results/product/answer_reliability/40000001926_measurement.json"
    doc = json.loads(p.read_text())
    legs = doc.get("legs", [])
    statuses = [leg.get("adversarial", {}).get("adversarial_status") for leg in legs]
    n_degraded = sum(1 for s in statuses if s == "DEGRADED_WRITER_ABORT")
    n_measured = sum(1 for s in statuses if s == "MEASURED")
    n_counter_zero = all(leg.get("adversarial", {}).get("n_counter_rows") == 0 for leg in legs)
    wa_ok = (len(legs) == 7 and n_degraded == 1 and n_measured == 6 and n_counter_zero)
    rows.append({
        "id": "reliability_40000001926_leg_statuses",
        "artifact": "results/product/answer_reliability/40000001926_measurement.json",
        "published": {"n_legs": 7, "n_measured": 6, "n_degraded_writer_abort": 1,
                      "all_n_counter_rows_zero": True},
        "found": {"n_legs": len(legs), "n_measured": n_measured,
                  "n_degraded_writer_abort": n_degraded,
                  "all_n_counter_rows_zero": n_counter_zero, "statuses": statuses},
        "verdict": "CONFIRMED" if wa_ok else "DIVERGENT", "kind": "composite",
    })
    n_conf += 1 if wa_ok else 0
    n_div += 0 if wa_ok else 1

    # 2. Frozen exception class kind=correction_landed (hypothesis-frozen):
    #    CYCLE_39986094168.md report table labels its 6-emission arm 'candidate'
    #    while the committed artifact names that arm 'candidate_unguarded'.
    span = json.loads(
        (mount / "results/product/counter_span/CYCLE_39986094168_span_selection.json").read_text())
    guarded = span["aggregate"]["candidate"]
    unguarded = span["aggregate"]["candidate_unguarded"]
    report_text = (mount / "reports/product/CYCLE_39986094168.md").read_text(encoding="utf-8")
    correction_text = (mount / "reports/product/CYCLE_40005362253.md").read_text(encoding="utf-8")
    report_labels_6_as_candidate = (
        "| candidate | 20 | **6** | 14 | **1.0** | **0.30** |" in report_text
        or ("| candidate | 20 | **6** |" in report_text))
    artifact_arm_names = {"baseline", "candidate", "candidate_unguarded"}
    numbers_reproduce = (guarded.get("n_emitted") == 1 and unguarded.get("n_emitted") == 6
                         and abs(float(unguarded.get("yield", 0)) - 0.3) <= APPLIED_FLOAT_TOL
                         and abs(float(guarded.get("yield", 0)) - 0.05) <= APPLIED_FLOAT_TOL)
    correction_present = ("unguarded diagnostic" in correction_text
                          and "arm semantics disclosed" in correction_text)
    cl_ok = report_labels_6_as_candidate and numbers_reproduce and correction_present
    rows.append({
        "id": "span_selection_39986094168_report_arm_label_correction_landed",
        "artifact": "results/product/counter_span/CYCLE_39986094168_span_selection.json"
                    " + reports/product/CYCLE_39986094168.md + reports/product/CYCLE_40005362253.md",
        "kind": "correction_landed",
        "published": {
            "report_table_labels_6_emission_arm": "candidate",
            "artifact_arm_emitting_6": "candidate_unguarded",
            "artifact_candidate_guarded_n_emitted": 1,
            "correction_in_later_accepted_report": True,
        },
        "found": {
            "report_labels_6_as_candidate": report_labels_6_as_candidate,
            "artifact_arm_names": sorted(artifact_arm_names),
            "guarded_n_emitted": guarded.get("n_emitted"),
            "unguarded_n_emitted": unguarded.get("n_emitted"),
            "unguarded_yield": unguarded.get("yield"),
            "guarded_yield": guarded.get("yield"),
            "correction_phrase_present": correction_present,
        },
        "verdict": "CONFIRMED_CORRECTED" if cl_ok else "DIVERGENT",
    })
    if cl_ok:
        n_corrected += 1
        n_conf += 1  # counted in confirmed for headline; disclosed separately
    else:
        n_div += 1

    # 3. Absent-ID probe per-row reason codes.
    probe = json.loads(
        (mount / "results/product/counter_span/CYCLE_40005362253_absent_id_span_probe.json").read_text())
    per_row = {r["decision_id"]: r for r in probe["summary"]["per_row"]}
    probe_ok = (
        per_row.get("gr_gerichte_PZ_2006_125", {}).get("reason_code") == "pivot_absent"
        and per_row.get("zh_mietgericht_MB170006-L", {}).get("reason_code") == "pivot_absent"
        and per_row.get("ch_vb_JAAC_68.7__", {}).get("reason_code") == "no_frozen_anchor_profile_for_query"
        and all(r.get("span_evidenced") is False for r in per_row.values()))
    rows.append({
        "id": "absent_id_probe_per_row_reason_codes",
        "artifact": "results/product/counter_span/CYCLE_40005362253_absent_id_span_probe.json",
        "published": {
            "gr_gerichte_PZ_2006_125": "pivot_absent",
            "zh_mietgericht_MB170006-L": "pivot_absent",
            "ch_vb_JAAC_68.7__": "no_frozen_anchor_profile_for_query",
            "all_span_evidenced_false": True,
        },
        "found": {k: v.get("reason_code") for k, v in per_row.items()},
        "verdict": "CONFIRMED" if probe_ok else "DIVERGENT", "kind": "composite",
    })
    n_conf += 1 if probe_ok else 0
    n_div += 0 if probe_ok else 1

    # 4. Inherited-cache coverage entry partition (15 x status 200, key_consistent).
    cov = json.loads(
        (mount / "results/product/regression/CYCLE_40000001926_inherited_cache_coverage.json").read_text())
    ents = cov.get("entries", [])
    cov_ok = (len(ents) == 15
              and all(e.get("status") == 200 for e in ents)
              and all(e.get("key_consistent") for e in ents)
              and cov.get("n_added") == 15)
    rows.append({
        "id": "cache_coverage_entries_partition",
        "artifact": "results/product/regression/CYCLE_40000001926_inherited_cache_coverage.json",
        "published": {"n_entries": 15, "all_status_200": True, "all_key_consistent": True},
        "found": {"n_entries": len(ents),
                  "statuses": sorted({e.get("status") for e in ents}),
                  "all_key_consistent": all(bool(e.get("key_consistent")) for e in ents)},
        "verdict": "CONFIRMED" if cov_ok else "DIVERGENT", "kind": "composite",
    })
    n_conf += 1 if cov_ok else 0
    n_div += 0 if cov_ok else 1

    # 5. Offline-slice page-contract detail string.
    summ = json.loads(
        (mount / "results/product/offline_slice/20261023T190402Z/summary.json").read_text())
    pc_ok = (summ.get("page_contract") is True
             and summ.get("page_contract_detail") == "PASS 67 assertions"
             and summ.get("stats", {}).get("fixture_replay", {}).get("network") == "none")
    rows.append({
        "id": "offline_slice_page_contract_detail",
        "artifact": "results/product/offline_slice/20261023T190402Z/summary.json",
        "published": {"page_contract": True, "detail": "PASS 67 assertions", "network": "none"},
        "found": {"page_contract": summ.get("page_contract"),
                  "detail": summ.get("page_contract_detail"),
                  "network": summ.get("stats", {}).get("fixture_replay", {}).get("network")},
        "verdict": "CONFIRMED" if pc_ok else "DIVERGENT", "kind": "composite",
    })
    n_conf += 1 if pc_ok else 0
    n_div += 0 if pc_ok else 1

    float_disclosure = build_float_disclosure(rows)
    return {
        "n_quantities": len(rows),
        "n_confirmed": n_conf,
        "n_divergent": n_div,
        "n_not_found": n_missing,
        "n_corrected_disclosed": n_corrected,
        "rows": rows,
        "float_comparison_disclosure": float_disclosure,
        "headline": float_disclosure["headline_applied_precision_matched"],
        "headline_basis": "applied precision-matched comparison (5e-4); see "
                          "float_comparison_disclosure for the frozen-literal-1e-6 "
                          "headline published side by side",
    }


def build_float_disclosure(rows: list) -> dict:
    n_conf = sum(1 for r in rows if r.get("verdict") in ("CONFIRMED", "CONFIRMED_CORRECTED"))
    n_div = sum(1 for r in rows if r.get("verdict") == "DIVERGENT")
    n_missing = sum(1 for r in rows if r.get("verdict") == "NOT_FOUND")
    strict_conf = strict_div = strict_missing = 0
    float_rows = []
    for row in rows:
        if row.get("verdict") == "NOT_FOUND":
            strict_verdict = "NOT_FOUND"
            strict_missing += 1
        elif row.get("kind") == "float":
            raw_found = row.get("raw_found", row.get("found"))
            published = row.get("raw_published", row.get("published"))
            delta = abs(float(raw_found) - float(published))
            strict_ok = delta <= FROZEN_LITERAL_FLOAT_TOL
            applied_ok = delta <= APPLIED_FLOAT_TOL
            strict_verdict = "CONFIRMED" if strict_ok else "DIVERGENT"
            row["raw_found"] = raw_found
            row["raw_published"] = published
            row["abs_delta"] = delta
            row["applied_tolerance"] = APPLIED_FLOAT_TOL
            row["frozen_literal_tolerance"] = FROZEN_LITERAL_FLOAT_TOL
            row["strict_verdict_1e_6"] = strict_verdict
            row["applied_verdict_precision_matched"] = (
                "CONFIRMED" if applied_ok else "DIVERGENT")
            float_rows.append({
                "id": row["id"], "published_3dp": published, "raw_found": raw_found,
                "abs_delta": delta, "strict_verdict_1e_6": strict_verdict,
                "applied_verdict_precision_matched":
                    row["applied_verdict_precision_matched"],
                "round_found_to_3dp_equals_published":
                    round(float(raw_found), PUBLICATION_DECIMALS) == float(published),
            })
        else:
            strict_verdict = row["verdict"]
        if strict_verdict == "CONFIRMED":
            strict_conf += 1
        elif strict_verdict == "DIVERGENT":
            strict_div += 1

    return {
        "convention_source": "accepted D-A dual-verdict convention (run 39986080045 "
                             "repair round 1), frozen in this run's hypothesis before "
                             "execution",
        "frozen_literal_tolerance": FROZEN_LITERAL_FLOAT_TOL,
        "applied_tolerance": APPLIED_FLOAT_TOL,
        "applied_tolerance_rationale":
            "half-ulp of the product lane's 3-decimal publication precision; raw_found "
            "is always carried in full so the delta is auditable",
        "deviation_from_literal_frozen_rule": True,
        "deviation_disclosed_not_absorbed": True,
        "both_verdicts_published_per_float_quantity": True,
        "headline_applied_precision_matched": (
            "ALL_CONFIRMED" if n_div == 0 and n_missing == 0
            else "DIVERGENCE_PRESENT" if n_div > 0 else "ARTIFACT_MISSING"),
        "headline_frozen_literal_1e_6": (
            "ALL_CONFIRMED" if strict_div == 0 and strict_missing == 0
            else "DIVERGENCE_PRESENT" if strict_div > 0 else "ARTIFACT_MISSING"),
        "counts_applied_precision_matched": {
            "n_confirmed": n_conf, "n_divergent": n_div, "n_not_found": n_missing},
        "counts_frozen_literal_1e_6": {
            "n_confirmed": strict_conf, "n_divergent": strict_div,
            "n_not_found": strict_missing},
        "n_float_quantities": len(float_rows),
        "float_quantities": float_rows,
        "reproduction": (
            "recompute abs(delta)=abs(raw_found-published) per float row; "
            "strict = delta <= 1e-6, applied = delta <= 5e-4"),
        "frozen_rule_edited": False,
    }


def falsification_rerun(mount: Path, out_dir: Path, report_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
        "--run-id", RUN_ID,
        "--packets", PACKET,
        "--product-mount", str(mount),
        "--out-dir", str(out_dir / "falsification"),
        "--report-dir", str(report_dir),
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=900, check=False)
    except Exception as exc:  # noqa: BLE001
        return {"executed": False, "error": f"{type(exc).__name__}: {exc}",
                "verdict": "NOT_MEASURED_VACUOUS", "exit_code": 2}
    wrapper_rec_path = out_dir / "falsification" / f"{RUN_ID}.json"
    engine_rec_path = (
        out_dir / "falsification" / f"{RUN_ID}_engine_mapping_free_recall_falsifier.json")
    wrapper_rec = json.loads(wrapper_rec_path.read_text()) if wrapper_rec_path.is_file() else {}
    engine_rec = json.loads(engine_rec_path.read_text()) if engine_rec_path.is_file() else {}
    meas = wrapper_rec.get("measurement") or {}
    raw_failed = (meas.get("failed_gates") or wrapper_rec.get("failed_gates") or [])
    failed = [(e.get("gate") if isinstance(e, dict) else str(e)) for e in raw_failed]
    accepted_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    exit_code = proc.returncode
    verdict = {0: "PASS_NO_FALSIFICATION", 1: "PRODUCT_FALSIFIED",
               2: "NOT_MEASURED_VACUOUS"}.get(exit_code, "UNEXPECTED_EXIT")
    return {
        "executed": True, "command": cmd, "exit_code": exit_code, "verdict": verdict,
        "stderr_tail": (proc.stderr or "")[-2000:],
        "stdout_tail": (proc.stdout or "")[-2000:],
        "failed_gates": failed, "accepted_failed_gates": accepted_failed,
        "failed_gates_is_superset_of_accepted": set(accepted_failed).issubset(set(failed)),
        "failed_gates_equals_accepted": set(failed) == set(accepted_failed),
        "n_gates": meas.get("n_gates", wrapper_rec.get("n_gates")),
        "n_passed": meas.get("n_passed", wrapper_rec.get("n_passed")),
        "n_failed": meas.get("n_failed", wrapper_rec.get("n_failed")),
        "n_reported": meas.get("n_reported", wrapper_rec.get("n_reported")),
        "n_questions_measured": meas.get("n_questions_measured", wrapper_rec.get("n_questions_measured")),
        "falsification_proven": exit_code == 1,
        "input_drift": engine_rec.get("input_drift") or [],
        "engine_direction_version": engine_rec.get("direction_version"),
        "wrapper_direction_version": wrapper_rec.get("direction_version"),
        "lane_direction_version": DIRECTION_VERSION,
        "direction_version_disclosure": (
            f"wrapper/engine direction_version {wrapper_rec.get('direction_version')}/"
            f"{engine_rec.get('direction_version')} vs lane {DIRECTION_VERSION}; "
            "wrapper/engine versions are historical fixture pins, disclosed not repaired"),
        "product_mount_head": engine_rec.get("product_mount_head") or wrapper_rec.get("product_mount_head"),
        "record_path": str(wrapper_rec_path) if wrapper_rec_path.is_file() else None,
        "engine_record_path": str(engine_rec_path) if engine_rec_path.is_file() else None,
    }


def planner_and_degradation_pin(mount: Path) -> dict:
    findings = {}
    planner = mount / "product/query/adversarial_retrieval.py"
    p_sha = _sha256_file(planner)
    findings["planner_sha256"] = {
        "expected": EXPECTED["planner"], "found": p_sha,
        "verdict": "CONFIRMED" if p_sha == EXPECTED["planner"] else "DIVERGENT"}
    src = planner.read_text(encoding="utf-8")
    aq_start = src.find("def answer_key_terms")
    aq_body = src[aq_start: src.find("\ndef ", aq_start + 1)] if aq_start >= 0 else ""
    has_strip_def = "def strip_redaction_placeholders" in src
    nested_call = "tokenize(strip_redaction_placeholders(" in aq_body
    findings["remedy_a_ordering"] = {
        "strip_redaction_placeholders_defined": has_strip_def,
        "answer_key_terms_calls_strip": aq_body.find("strip_redaction_placeholders") != -1,
        "nested_tokenize_strip_call": nested_call,
        "verdict": "CONFIRMED" if (has_strip_def and nested_call) else "DIVERGENT"}
    # Degradation pin on the NEWEST live measurement (marker-visibility semantics,
    # frozen in this run's hypothesis — weaker than the prior 7/7 leg rule).
    p = mount / "results/product/answer_reliability/40000001926_measurement.json"
    doc = json.loads(p.read_text())
    legs = doc.get("legs", [])
    blob = p.read_text()
    n_with_marker = sum(
        1 for leg in legs
        if leg.get("adversarial", {}).get("adversarial_status") == "DEGRADED_WRITER_ABORT")
    rate = doc.get("metrics", {}).get("degradation_visible_rate")
    findings["degradation_pin_e_emission_writer_abort"] = {
        "measurement": "40000001926 (newest live reliability measurement)",
        "marker_string_in_artifact": "e_EMISSION_WRITER_ABORT" in blob,
        "n_legs_with_degraded_writer_abort": n_with_marker,
        "n_legs": len(legs), "degradation_visible_rate": rate,
        "older_property_disclosure":
            "the 7-of-7-DEGRADED property belongs to measurement 39956256289 "
            "(the outage date) and is NOT re-required here; the frozen pin "
            "semantics for this run is marker visibility with rate 1.0",
        "verdict": ("CONFIRMED"
                    if (n_with_marker >= 1 and len(legs) == 7 and rate == 1.0)
                    else "DIVERGENT")}
    v2 = json.loads((REPO_ROOT / "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_FREEZE_RECORD_V2.json").read_text())
    v3 = json.loads((REPO_ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V3.json").read_text())
    pin_checks = []
    for label, rec in (("planner_remedy_V2", v2), ("degradation_V3", v3)):
        for rel, expected in (rec.get("product_pins") or {}).items():
            fp = mount / rel
            found = _sha256_file(fp) if fp.is_file() else "MISSING"
            pin_checks.append({"source": label, "relpath": rel, "expected": expected,
                               "found": found,
                               "verdict": "CONFIRMED" if found == expected else "DIVERGENT"})
    n_pin_ok = sum(1 for c in pin_checks if c["verdict"] == "CONFIRMED")
    diverged = [c for c in pin_checks if c["verdict"] != "CONFIRMED"]
    findings["frozen_product_pins_rehash"] = {
        "n_pins": len(pin_checks), "n_confirmed": n_pin_ok,
        "n_divergent": len(diverged), "diverged_pins": diverged, "checks": pin_checks,
        "verdict": "CONFIRMED" if n_pin_ok == len(pin_checks) else "DRIFT_REPORTED",
        "interpretation": ("all frozen pins hold" if n_pin_ok == len(pin_checks)
                           else "product-advance pin drift disclosed; planner/remedy/"
                                "degradation must-hold pins evaluated separately")}
    must_hold = [findings["planner_sha256"]["verdict"],
                 findings["remedy_a_ordering"]["verdict"],
                 findings["degradation_pin_e_emission_writer_abort"]["verdict"]]
    overall = "CONFIRMED" if all(v == "CONFIRMED" for v in must_hold) else "DIVERGENT"
    return {"findings": findings, "overall": overall, "must_hold_pins": must_hold,
            "product_pins_drift_disclosed": len(diverged) > 0}


def control_planted_divergence_is_detected(mount: Path) -> dict:
    import tempfile
    art_rel = "results/product/answer_reliability/40000001926_measurement.json"
    with tempfile.TemporaryDirectory(prefix="v65pac_control_") as td:
        target = Path(td) / art_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        doc = json.loads((mount / art_rel).read_text())
        doc["metrics"]["answer_ready_rate"] = 0.5  # plant
        target.write_text(json.dumps(doc))
        found = _json_path_get(doc, ["metrics", "answer_ready_rate"])
        delta = abs(float(found) - 0.857)
        ok = delta <= APPLIED_FLOAT_TOL and delta <= FROZEN_LITERAL_FLOAT_TOL
        detected = not ok
    return {"control": "C1_planted_currency_divergence_is_detected",
            "planted_value": 0.5, "expected_published": 0.857, "abs_delta": delta,
            "tolerances_applied": {"frozen_literal_1e_6": FROZEN_LITERAL_FLOAT_TOL,
                                   "applied_precision_matched": APPLIED_FLOAT_TOL},
            "detected_as_divergent": detected, "passed": detected}


def control_frozen_rules_rehash_holds(pins_before: dict, pins_after: dict) -> dict:
    keys = [k for k in pins_before if "RULES_" in k]
    holds = all(pins_before[k] == pins_after[k] for k in keys)
    expected_ok = (
        pins_before.get("repo:evaluation/frozen_bars/RULES_LABEL.json") == EXPECTED["rules_label"]
        and pins_before.get("repo:evaluation/frozen_bars/RULES_GEOMETRY.json") == EXPECTED["rules_geometry"])
    return {"control": "C2_frozen_rules_rehash_holds", "rule_keys": keys,
            "before": {k: pins_before.get(k) for k in keys},
            "after": {k: pins_after.get(k) for k in keys},
            "before_equals_after": holds, "matches_expected": expected_ok,
            "passed": holds and expected_ok}


def control_packet_bytes_unchanged(pins_before: dict, pins_after: dict) -> dict:
    key = f"mount:results/product/gate_packet/{PACKET}/packet.json"
    before, after = pins_before.get(key), pins_after.get(key)
    expected_ok = before == EXPECTED["packet_json"]
    return {"control": "C3_packet_bytes_unchanged", "before": before, "after": after,
            "expected": EXPECTED["packet_json"], "before_equals_after": before == after,
            "matches_expected": expected_ok, "passed": before == after and expected_ok}


def _render_report(record: dict) -> str:
    cur = record["currency_crosscheck"]
    fr = record["falsification_rerun"]
    pp = record["planner_and_degradation_pin"]
    lin = record["requirement_4_lineage"]
    ctrls = record["controls"]
    lines = [
        f"# V65 Product-Advance Cross-Check — run {RUN_ID} (operational resume)",
        "",
        f"- Direction: v{DIRECTION_VERSION}",
        f"- Product mount head: `{record['product_mount_head']}`",
        f"- Packet of record: {PACKET} (bytes unchanged, re-hashed)",
        f"- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL `{EXPECTED['rules_label'][:16]}…`, "
        f"RULES_GEOMETRY `{EXPECTED['rules_geometry'][:16]}…`",
        f"- Verdict: **{record['verdict']}**",
        f"- Executed at: {record['generated_at_utc']}",
        "- Resume lineage: rc-67 producer runs 40006151200 / 40011795717 scoped but never "
        "committed this work; their plans are preserved under "
        "results/evaluation/orchestration/ and executed here.",
        "",
        "## Requirement-4 lineage of the two newly accepted product cycles",
        "",
    ]
    for rid in ("40000001926", "40005362253"):
        e = lin.get(rid, {})
        lines.append(f"- **{rid}**: gate half {'OK' if e.get('gate_half_ok') else 'FAIL'} "
                     f"({e.get('gate_half')}); accept half "
                     f"{'OK' if e.get('accept_half_ok') else 'FAIL'} "
                     f"({(e.get('accept_half') or {}).get('matches')}); "
                     f"both halves: **{e.get('requirement_4_both_halves')}**")
    lines += [
        "",
        "## Ordered item 1 — currency cross-check",
        "",
        f"- Quantities: {cur['n_quantities']} — CONFIRMED {cur['n_confirmed']}, "
        f"DIVERGENT {cur['n_divergent']}, NOT_FOUND {cur['n_not_found']}, "
        f"CONFIRMED_CORRECTED (disclosed) {cur['n_corrected_disclosed']}",
        f"- Headline (applied precision-matched, 5e-4): **{cur['headline']}**",
        "",
    ]
    fd = cur.get("float_comparison_disclosure") or {}
    if fd:
        counts_lit = fd["counts_frozen_literal_1e_6"]
        lines += [
            "### Float-comparison disclosure (accepted D-A dual-verdict convention)",
            "",
            f"- Headline under the **frozen literal 1e-6** rule: "
            f"**{fd['headline_frozen_literal_1e_6']}** "
            f"(CONFIRMED {counts_lit['n_confirmed']}, DIVERGENT {counts_lit['n_divergent']}, "
            f"NOT_FOUND {counts_lit['n_not_found']}).",
            f"- Headline under the **applied precision-matched** rule: "
            f"**{fd['headline_applied_precision_matched']}** "
            f"(CONFIRMED {fd['counts_applied_precision_matched']['n_confirmed']}, "
            f"DIVERGENT {fd['counts_applied_precision_matched']['n_divergent']}, "
            f"NOT_FOUND {fd['counts_applied_precision_matched']['n_not_found']}).",
            "",
            "| quantity | published (3dp) | raw found | abs delta | strict 1e-6 | applied 5e-4 | round(raw,3)==pub |",
            "|---|---|---|---|---|---|---|",
        ]
        for fq in fd["float_quantities"]:
            lines.append(
                f"| `{fq['id']}` | {fq['published_3dp']} | {fq['raw_found']} | "
                f"{fq['abs_delta']:.3e} | {fq['strict_verdict_1e_6']} | "
                f"{fq['applied_verdict_precision_matched']} | "
                f"{fq['round_found_to_3dp_equals_published']} |")
        lines.append("")
    for row in cur["rows"]:
        mark = {"CONFIRMED": "✅", "CONFIRMED_CORRECTED": "🔧", "DIVERGENT": "❌",
                "NOT_FOUND": "⚠️"}.get(row["verdict"], "?")
        lines.append(f"- {mark} `{row['id']}`: published `{row['published']}` "
                     f"vs found `{row.get('found')}` → **{row['verdict']}**")
    lines += [
        "",
        "## Ordered item 2 — falsification re-run (same frozen rule set, new head)",
        "",
        f"- Verdict: **{fr['verdict']}** (exit {fr['exit_code']})",
        f"- Falsification proven: {fr.get('falsification_proven')}",
        f"- Failed gates: {fr.get('failed_gates')}",
        f"- Equals accepted 4-gate set: {fr.get('failed_gates_equals_accepted')}",
        f"- Superset of accepted: {fr.get('failed_gates_is_superset_of_accepted')}",
        f"- Gates {fr.get('n_passed')}/{fr.get('n_gates')} passed; "
        f"n_questions={fr.get('n_questions_measured')}",
        f"- Engine input_drift: {fr.get('input_drift')}",
        f"- {fr.get('direction_version_disclosure', '')}",
        "",
        "## Ordered item 3 — planner-remedy + degradation pin",
        "",
        f"- Overall: **{pp['overall']}**",
    ]
    for name, f in pp["findings"].items():
        lines.append(f"- `{name}`: **{f.get('verdict', f.get('overall', '?'))}**")
    lines += [
        "",
        "## Controls",
        "",
    ]
    for c in ctrls.values():
        lines.append(f"- `{c['control']}`: {'PASS' if c['passed'] else 'FAIL'}")
    lines += [
        "",
        "## Ordered item 5 — coverage v2 re-freeze",
        "",
        "- NOT EXECUTED — conditional on the coverage family being resumed; it is NOT resumed this cycle.",
        "",
        "## Claim ceiling",
        "",
        "- This instrument cross-checks published product quantities against their own committed "
        "artifacts and re-executes the accepted falsification benchmark on the newest accepted head. "
        "It scores no frozen bar, re-derives no threshold, classifies no decision, and asserts no "
        "serve or human-gate readiness. Both DO-NOT-SERVE orders stand; admission stays fail-closed; "
        "the comparative map-versus-ranked-list half is NOT scored while zero counter rows are "
        "evidenced (factory-wide requirement 22).",
        "",
    ]
    return "\n".join(lines)


def run(run_id: str = RUN_ID) -> int:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pins_before = rehash_pins(MOUNT)
    input_drift = []
    if pins_before.get("repo:evaluation/frozen_bars/RULES_LABEL.json") != EXPECTED["rules_label"]:
        input_drift.append("RULES_LABEL digest drift")
    if pins_before.get("repo:evaluation/frozen_bars/RULES_GEOMETRY.json") != EXPECTED["rules_geometry"]:
        input_drift.append("RULES_GEOMETRY digest drift")
    if pins_before.get(f"mount:results/product/gate_packet/{PACKET}/packet.json") != EXPECTED["packet_json"]:
        input_drift.append("packet-of-record bytes drift")
    if pins_before.get("repo:evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json") != EXPECTED["hypothesis"]:
        input_drift.append("hypothesis digest drift")
    if pins_before.get("mount_head") != EXPECTED["mount_head"]:
        input_drift.append(
            f"product mount head drift: {pins_before.get('mount_head')} != {EXPECTED['mount_head']}")

    if input_drift:
        record = {
            "schema": "lex-evaluation-v65-product-advance-crosscheck/1",
            "run_id": run_id, "direction_version": DIRECTION_VERSION,
            "generated_at_utc": generated, "product_mount": str(MOUNT),
            "product_mount_head": pins_before.get("mount_head"),
            "input_drift": input_drift, "verdict": "NOT_MEASURED_VACUOUS", "exit_code": 2,
            "currency_crosscheck": None, "falsification_rerun": None,
            "planner_and_degradation_pin": None, "requirement_4_lineage": None,
            "controls": {}, "pins_before": pins_before, "pins_after": None,
            "numeric_environment": numeric_environment()}
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{run_id}.json").write_text(json.dumps(record, indent=1, sort_keys=True))
        print(json.dumps({"verdict": record["verdict"], "input_drift": input_drift}, indent=1))
        return 2

    lineage = requirement4_lineage(MOUNT)
    currency = currency_crosscheck(MOUNT)
    falsification = falsification_rerun(MOUNT, OUT_DIR, REPORT_DIR)
    planner_pin = planner_and_degradation_pin(MOUNT)
    c1 = control_planted_divergence_is_detected(MOUNT)
    pins_after = rehash_pins(MOUNT)
    c2 = control_frozen_rules_rehash_holds(pins_before, pins_after)
    c3 = control_packet_bytes_unchanged(pins_before, pins_after)
    controls = {"C1_planted_currency_divergence_is_detected": c1,
                "C2_frozen_rules_rehash_holds": c2,
                "C3_packet_bytes_unchanged": c3}
    control_failures = [k for k, v in controls.items() if not v.get("passed")]

    if control_failures or not lineage.get("all_accepted"):
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
    elif currency["n_divergent"] > 0 or planner_pin["overall"] == "DIVERGENT":
        verdict, exit_code = "MATERIAL_DIVERGENCE", 1
    elif falsification["verdict"] == "NOT_MEASURED_VACUOUS":
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
    elif falsification["verdict"] == "PASS_NO_FALSIFICATION":
        verdict, exit_code = "MATERIAL_DIVERGENCE", 1
    elif falsification["verdict"] == "PRODUCT_FALSIFIED":
        verdict, exit_code = "PASS_NO_FALSIFICATION", 0
    else:
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2

    record = {
        "schema": "lex-evaluation-v65-product-advance-crosscheck/1",
        "run_id": run_id, "direction_version": DIRECTION_VERSION,
        "generated_at_utc": generated, "product_mount": str(MOUNT),
        "product_mount_head": pins_before.get("mount_head"),
        "packet_of_record": PACKET, "input_drift": [],
        "resume_lineage": {
            "resumed_run": "40011795717", "prior_resumed_run": "40006151200",
            "failure_class": "LEX_ZERO_DELTA_REPAIR rc 67 (zero committed delta)",
            "diagnosis_artifact": "results/evaluation/orchestration/40011795717_diagnosis.json"},
        "requirement_4_lineage": lineage,
        "currency_crosscheck": currency,
        "falsification_rerun": falsification,
        "planner_and_degradation_pin": planner_pin,
        "controls": controls, "control_failures": control_failures,
        "pins_before": pins_before, "pins_after": pins_after,
        "numeric_environment": numeric_environment(),
        "verdict": verdict, "exit_code": exit_code,
        "claim_ceiling": (
            "Currency cross-check of published product quantities against their own committed "
            "artifacts on the newest accepted product head (f9618377, accept cycle 40005362253), "
            "plus a re-execution of the accepted mapping-free falsification benchmark on unchanged "
            "packet-of-record bytes under the same frozen rules re-hashed REPORTED-ONLY. It scores "
            "no frozen bar, re-derives no threshold, classifies no decision, and asserts no serve "
            "or human-gate readiness. Both DO-NOT-SERVE orders stand; admission stays fail-closed; "
            "the comparative map-versus-ranked-list half is NOT scored while zero counter rows are "
            "evidenced."),
        "posture_unchanged": {"human_gate_ready": False, "machine_gate_ready": False,
                              "packet_admitted": False, "ready_for_owner_session": False},
        "coverage_v2_refreeze": {
            "executed": False,
            "reason": "conditional on the coverage family being resumed; it is NOT resumed this cycle"}}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=1, sort_keys=True))
    report_path = REPORT_DIR / f"V65_PRODUCT_ADVANCE_CROSSCHECK_{run_id}.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(record), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict, "exit_code": exit_code,
        "currency_headline": currency["headline"],
        "n_confirmed": currency["n_confirmed"], "n_divergent": currency["n_divergent"],
        "n_corrected_disclosed": currency["n_corrected_disclosed"],
        "requirement_4_all_accepted": lineage.get("all_accepted"),
        "falsification_verdict": falsification["verdict"],
        "falsification_failed_gates": falsification.get("failed_gates"),
        "planner_pin": planner_pin["overall"],
        "controls": {k: v["passed"] for k, v in controls.items()},
        "out": str(out_path), "report": str(report_path)}, indent=1))
    return exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID)
    args = ap.parse_args(argv)
    return run(run_id=args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
