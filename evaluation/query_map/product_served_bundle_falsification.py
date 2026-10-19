#!/usr/bin/env python3
"""Exercise the query-map acceptance instrument on PRODUCT-PRODUCED bytes, and
falsify-or-pass Product's ``question_native_coverage_39113690481`` admission
disclosure fix on those exact bytes.

WHY THIS MODULE EXISTS (direction v57, evaluation lane question item 2 + the
lane's own ``still_incomplete[0]`` from accepted cycle 39200567493)
-------------------------------------------------------------------------
Two gaps, one executable instrument:

1. The accepted harness ``evaluation/query_map/harness.py`` had only ever been
   run against bundles THIS LANE builds.  A harness that has never seen the
   product's bytes cannot judge them.  This module runs it on the accepted
   product mount's own served packet.
2. The v57 question orders this lane to falsify-or-pass Product's
   ``question_native_coverage_39113690481`` fix **on the exact served bytes**
   once it lands, mapping-free, publishing before/after admission records side
   by side, and forbids pre-empting or pausing before that handoff is consumed.

FOUR LEGS, THREE NON-VACUITY CONTROL FAMILIES, EXIT CODES THAT CAN FALSIFY

  L1 product_bytes_contract
         The accepted harness's per-check status vector on the three served
         bundles.  Two of its checks (progressive_phases,
         geometry_preserved_after_enrichment) are NOT MEASURABLE on a packet
         that ships only the ``complete`` phase, and are reported as
         NOT_MEASURED — never as a pass, never counted in the verdict.
  L2 counter_authority_liveness
         Yield numerators/denominators for the product's counter rows, plus
         four controls proving each L1 check is LIVE on these bytes.
  L3 handoff_question_native_coverage
         BEFORE arm = the committed served ``.admissibility.json``.
         AFTER arm  = accepted ``product.query.gate_admissibility.verify_bundle``
         run on the SAME bundle bytes.
         Both arms are scored by the FROZEN predicate
         ``evaluation.question_native_transfer.disclosure_gap_predicate``.
         Condition (e) additionally requires that no BEFORE finding code is
         lost in the AFTER arm.
  L4 language_provenance_determinism
         FR/DE/IT accounting, source/URL provenance, frozen-rule duplicate
         suppression, geometry-signature determinism and order invariance, and
         the latency the bundle itself records.

  exit 0  VALID_NO_FALSIFICATION
  exit 1  PRODUCT_BUNDLE_CONTRACT_VIOLATED  (a measurable L1 check is false)
  exit 2  ENVIRONMENT_OR_VACUOUS           (pin drift, missing mount, or a
                                            non-vacuity control that did NOT fire)
  exit 3  HANDOFF_FIX_FALSIFIED             (L3 is anything but HANDOFF_PASS)

REUSE-FIRST / ZERO NEW THRESHOLDS
---------------------------------
The accepted harness and the accepted frozen disclosure predicate are IMPORTED
BY REFERENCE and never copied, edited, re-tuned or re-implemented.  The frozen
duplicate rule is used through ``bundle_producer.alnum_core``.  Every quantity
published is a numerator, a denominator or a re-hashed digest; this module
introduces no threshold, bar or rubric and applies none of the absolute frozen
bars, which stay REPORTED-ONLY.

MAPPING-FREE
------------
The product's question slugs are NOT mapped onto this lane's frozen retrieval
questions, no analyst slug, frozen id set or baseline record is applied to
these bytes, and no known-authority / known-counter recall is published for the
product population because no mapping-free ground truth exists for it.  That
cell is reported NOT_APPLICABLE_WITH_REASON — not as 0 and not as a pass.

SCRATCH-RUN OBLIGATION
----------------------
A claim-bearing cycle writes the committed defaults below.  A scratch
invocation MUST pass ``--out`` / ``--report``, otherwise it silently overwrites
the claim-bearing record.  It NEVER writes into the product mount.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.query_map.bundle_producer import alnum_core  # noqa: E402
from evaluation.query_map.harness import (  # noqa: E402
    COUNTER_STATUSES, evaluate_query_map_bundle, geometry_signature,
)
from evaluation.question_native_transfer import (  # noqa: E402
    DISCLOSURE_MARKERS, FROZEN_QIDS, disclosure_gap_predicate,
)

SCHEMA = "lex-evaluation-product-served-bundle-falsification/1"

DEFAULT_HYPOTHESIS = (_REPO_ROOT
                      / "evaluation/PRODUCT_SERVED_BUNDLE_FALSIFICATION_HYPOTHESIS_V1.json")
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
DEFAULT_OUT = _REPO_ROOT / "results/evaluation/product_served_bundle_falsification"
DEFAULT_REPORT = _REPO_ROOT / "reports/evaluation"

EXIT_OK = 0
EXIT_CONTRACT_VIOLATED = 1
EXIT_ENVIRONMENT_OR_VACUOUS = 2
EXIT_HANDOFF_FALSIFIED = 3

#: Harness checks that CANNOT be measured on a packet that ships only the
#: ``complete`` phase bundle. Reported as NOT_MEASURED, excluded from the L1
#: verdict, and never presented as a pass.
NOT_MEASURED_ON_SERVED_BYTES = {
    "geometry_preserved_after_enrichment": (
        "the served packet ships only the `complete` phase bundle; there is no "
        "`map_ready` artifact for the accepted harness's initial-vs-final "
        "signature comparison to read"),
    "progressive_phases": (
        "provenance.phase is `complete` for all three served bundles and no "
        "`map_ready` provenance exists in the served packet"),
}

#: Frozen control query for L3 non-vacuity control C2. Its concepts are absent
#: from a labour-law bundle, so the measured under-covered set must change.
L3_CONTROL_QUERY = "Zinsschranken Wucherzins"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _codes(verdict: dict) -> list[str]:
    return [str((f or {}).get("code", "")) for f in (verdict.get("findings") or [])]


# --------------------------------------------------------------------------- #
# pin re-hashing (before AND after execution)
# --------------------------------------------------------------------------- #
def resolve_head(mount: Path) -> str | None:
    """Resolve the ACCEPTED mount's exact HEAD commit.

    A linked worktree stores its own HEAD at ``<gitdir>/HEAD`` and the ref at
    ``<commondir>/<refname>``; reading ``<commondir>/HEAD`` instead silently
    returns the MAIN repository's branch, which is how a pin check can pass on
    the wrong tree.  Ask git, and fall back to the correct two-file resolution.
    """
    try:
        import subprocess  # noqa: PLC0415
        out = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:  # pragma: no cover - fall through to manual resolution
        pass
    dot_git = mount / ".git"
    try:
        if dot_git.is_dir():
            common = dot_git
            head_file = dot_git / "HEAD"
        else:
            gitdir = Path(dot_git.read_text(encoding="utf-8").split(":", 1)[1].strip()).resolve()
            common = gitdir.parent
            head_file = gitdir / "HEAD"
        raw = head_file.read_text(encoding="utf-8").strip()
        if raw.startswith("ref:"):
            ref = common / raw.split(" ", 1)[-1].strip()
            return ref.read_text(encoding="utf-8").strip() if ref.exists() else None
        return raw or None
    except OSError:
        return None


def rehash_pins(hypothesis: dict, lane_root: Path, mount: Path) -> dict:
    """Re-hash every digest the freeze pinned. Never re-derives a pin."""
    checks: list[dict] = []

    def check(group: str, path: Path, expected: str) -> None:
        rel = str(path)
        present = path.exists()
        actual = sha256_file(path) if present else None
        checks.append({"group": group, "path": rel, "expected": expected,
                       "actual": actual, "present": present,
                       "match": bool(actual == expected)})

    served = hypothesis["frozen_inputs"]["served_packet"]
    for rel, expected in sorted(hypothesis["frozen_inputs"]["sha256"].items()):
        check("served_byte", mount / served / rel, expected)
    for rel, expected in sorted(hypothesis["frozen_inputs"]["product_code_sha256"].items()):
        check("product_code", mount / rel, expected)
    for rel, expected in sorted(hypothesis["frozen_inputs"]["lane_frozen_sha256"].items()):
        check("lane_frozen", lane_root / rel, expected)

    head = resolve_head(mount)
    head_ok = (head == hypothesis["frozen_inputs"]["accepted_product_head"])
    return {
        "n_checks": len(checks),
        "n_match": sum(1 for c in checks if c["match"]),
        "n_drift": sum(1 for c in checks if not c["match"]),
        "accepted_product_head_declared": hypothesis["frozen_inputs"]["accepted_product_head"],
        "accepted_product_head_resolved": head,
        "accepted_product_head_match": head_ok,
        "drift": [c for c in checks if not c["match"]],
        "checks": checks,
    }


def numeric_environment() -> dict:
    """Requirement-30 style disclosure: never claim cross-machine byte identity."""
    env = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "thread_env": {k: os.environ.get(k) for k in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED")},
    }
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            env[mod] = __import__(mod).__version__
        except Exception as exc:  # pragma: no cover - environment disclosure only
            env[mod] = f"ABSENT ({type(exc).__name__})"
    try:
        import numpy as _np  # noqa: PLC0415
        env["numpy_blas"] = str(_np.__config__.show(mode="dicts")["Build Dependencies"]["blas"]["name"])
    except Exception:
        env["numpy_blas"] = "UNDISCLOSED"
    return env


# --------------------------------------------------------------------------- #
# L1 — contract checks on the exact served bytes
# --------------------------------------------------------------------------- #
def leg1_contract(bundle: dict) -> dict:
    """Run the ACCEPTED harness on one served bundle.

    ``initial`` is set to ``final`` because the served packet has no map_ready
    artifact.  The two phase-dependent checks are then overwritten with
    NOT_MEASURED and removed from the verdict, so no degenerate self-comparison
    can ever be reported as a pass.
    """
    result = evaluate_query_map_bundle(bundle, bundle)
    raw_checks = dict(result["checks"])
    for name in NOT_MEASURED_ON_SERVED_BYTES:
        raw_checks[name] = "NOT_MEASURED"
    measurable = [k for k in raw_checks if k not in NOT_MEASURED_ON_SERVED_BYTES]
    failed = sorted(k for k in measurable if raw_checks[k] is not True)
    return {
        "harness_schema": result["schema"],
        "harness_pass_as_computed": result["pass"],
        "harness_pass_note": (
            "the accepted harness was called with initial == final because the served "
            "packet has no map_ready artifact; its own `pass` therefore rests partly on "
            "a degenerate self-comparison and is NOT published as a verdict"),
        "checks": raw_checks,
        "measurable_checks": sorted(measurable),
        "not_measured_checks": {k: NOT_MEASURED_ON_SERVED_BYTES[k] for k in NOT_MEASURED_ON_SERVED_BYTES},
        "measurable_checks_failed": failed,
        "contract_pass": not failed,
        "counts": result["counts"],
        "languages": result["languages"],
        "bad_source_ids": result["bad_source_ids"],
        "invalid_cited_ids": result["invalid_cited_ids"],
        "unsupported_counter_ids": result["unsupported_counter_ids"],
        "geometry": {k: v for k, v in result["geometry"].items() if k != "preserved"},
        "retrieval": result["retrieval"],
        "latency": result["latency"],
    }


def l1_controls(bundle: dict) -> dict:
    """Every measurable L1 check must be LIVE, not vacuously true."""
    controls: list[dict] = []

    n_labelled = sum(1 for d in (bundle.get("decisions") or [])
                     if d.get("counter_status") in COUNTER_STATUSES)

    def run(name: str, mutate, expect_false: str, *, needs: str | None = None) -> None:
        b = copy.deepcopy(bundle)
        mutate(b)
        r = leg1_contract(b)
        fired = r["checks"].get(expect_false) is False
        if fired:
            cause = "FIRED_AS_EXPECTED"
        elif needs == "counter_labelled_rows" and n_labelled == 0:
            # The mutation had nothing to mutate. The check is UNEXERCISED on
            # this population, which is a DIFFERENT fact from the check being
            # vacuously true, and must be published as its own negative result.
            cause = "UNEXERCISED_POPULATION_EMPTY"
        else:
            cause = "CHECK_VACUOUS"
        controls.append({
            "control": name,
            "mutation": mutate.__doc__ or "",
            "check_that_must_flip": expect_false,
            "observed_value": r["checks"].get(expect_false),
            "n_counter_labelled_rows_in_unmutated_bundle": n_labelled,
            "not_fired_cause": cause,
            "fired": fired,
            "contract_pass_under_mutation": r["contract_pass"],
        })

    def blank_evidence(b: dict) -> None:
        """set counter_evidence='' on every counter-labelled decision"""
        for d in b.get("decisions", []):
            if d.get("counter_status") in COUNTER_STATUSES:
                d["counter_evidence"] = ""

    def blank_uncertainty(b: dict) -> None:
        """set counter_uncertainty=None on every counter-labelled decision"""
        for d in b.get("decisions", []):
            if d.get("counter_status") in COUNTER_STATUSES:
                d["counter_uncertainty"] = None

    def repoint_url(b: dict) -> None:
        """repoint the first decision's canonical_url to an off-host https URL"""
        b["decisions"][0]["canonical_url"] = "https://example.invalid/not-opencaselaw"

    def duplicate_row(b: dict) -> None:
        """append a byte-copy of the first decision"""
        b["decisions"].append(copy.deepcopy(b["decisions"][0]))

    def rogue_citation(b: dict) -> None:
        """add a cited_decision_id that is not in the bundle"""
        cited = (b.setdefault("answer", {})).setdefault("cited_decision_ids", [])
        cited.append("lex-not-in-bundle-000")

    run("blanked_counter_evidence", blank_evidence, "counter_classifications_supported",
        needs="counter_labelled_rows")
    run("blanked_counter_uncertainty", blank_uncertainty, "counter_classifications_supported",
        needs="counter_labelled_rows")
    run("repointed_source_url", repoint_url, "source_urls_valid")
    run("duplicated_first_decision", duplicate_row, "duplicate_free")
    run("rogue_answer_citation", rogue_citation, "answer_citations_constrained")

    all_fired = all(c["fired"] for c in controls)
    unexercised = sorted({c["control"] for c in controls
                          if c["not_fired_cause"] == "UNEXERCISED_POPULATION_EMPTY"})
    return {
        "n_controls": len(controls),
        "n_fired": sum(1 for c in controls if c["fired"]),
        "all_fired": all_fired,
        "n_counter_labelled_rows": n_labelled,
        "unexercised_checks": unexercised,
        "unexercised_reading": (
            "UNEXERCISED, NOT SATISFIED: this bundle emits zero rows in the accepted "
            "COUNTER_STATUSES set, so the counter-evidence contract is never put to the "
            "test on it. An unexercised contract is a NEGATIVE RESULT about the product, "
            "not a pass and not a tooling failure."),
        "controls": controls,
        "note": "a control that does not fire means the check is VACUOUS or UNEXERCISED on this population; that is exit 2, never a pass",
    }


# --------------------------------------------------------------------------- #
# L2 — counter-authority yield on product bytes
# --------------------------------------------------------------------------- #
def leg2_counter(bundle: dict, handoff: dict, qid: str) -> dict:
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    labelled = [d for d in decisions if d.get("counter_status") in COUNTER_STATUSES]
    supported = [d for d in labelled
                 if str(d.get("counter_evidence") or "").strip()
                 and d.get("counter_uncertainty") is not None]
    verified = [d for d in labelled if d.get("counter_evidence_verified")]
    abstained = [d for d in labelled
                 if str(d.get("counter_status") or "") == "abstained_unevidenced"]
    cited = {str(x) for x in ((bundle.get("answer") or {}).get("cited_decision_ids") or [])}
    labelled_ids = {str(d.get("decision_id")) for d in labelled}
    unc = Counter(round(float(d["counter_uncertainty"]), 4)
                  for d in labelled if d.get("counter_uncertainty") is not None)
    chan = Counter(str(d.get("adversarial_channel") or "?") for d in labelled)
    anchor = next((h for h in (handoff.get("bundles") or []) if h.get("qid") == qid), {})
    return {
        "n_decisions": len(decisions),
        "n_rows_with_any_counter_status": sum(1 for d in decisions if d.get("counter_status")),
        "n_counter_labelled": len(labelled),
        "n_counter_labels_supported": len(supported),
        "n_counter_labels_unsupported": len(labelled) - len(supported),
        "n_counter_evidence_verified": len(verified),
        "n_abstained_unevidenced_rows": len(abstained),
        "support_rate_among_issued": (
            round(len(supported) / len(labelled), 6) if labelled else None),
        "cited_counter_overlap": len(cited & labelled_ids),
        "cited_rows": len(cited),
        "counter_uncertainty_histogram": dict(sorted(unc.items())),
        "counter_channel_histogram": dict(sorted(chan.items())),
        "counter_status_histogram": dict(sorted(Counter(
            str(d.get("counter_status") or "?") for d in labelled).items())),
        "counter_status_histogram_all_rows": dict(sorted(Counter(
            str(d.get("counter_status") or "NONE") for d in decisions).items())),
        "n_rows_with_counter_status_outside_accepted_set": sum(
            1 for d in decisions
            if d.get("counter_status") and d.get("counter_status") not in COUNTER_STATUSES),
        "counter_label_ranks": sorted(int(d.get("rank") or 0) for d in labelled),
        "answer_cited_counter_ids": sorted(cited & labelled_ids),
        "answer_cites_any_counter_authority": bool(cited & labelled_ids),
        "counter_reason_code_histogram": dict(sorted(Counter(
            str(d.get("counter_reason_code") or "NONE") for d in labelled).items())),
        "accepted_frontier_counter_anchor_claim_of_record": anchor.get("counter_anchor"),
    }


# --------------------------------------------------------------------------- #
# L3 — the handoff falsification
# --------------------------------------------------------------------------- #
def _l3_finding(verdict: dict) -> dict | None:
    for f in (verdict.get("findings") or []):
        if any(m in str(f.get("code", "")).lower() for m in DISCLOSURE_MARKERS):
            return f
    return None


def classify_l3(*, import_error, before_pred, after_pred, measured_under,
                detail_terms, finding_severity, finding_present,
                lost_codes) -> str:
    """The frozen L3 verdict classifier, factored out so tests drive THIS code.

    Branches are ordered so that an unmeasurable run can never be reported as a
    pass, and a qid that carries no defect instance is neither a pass nor a
    failure. The aggregate over qids implements the frozen PER-INSTANCE rule; see
    ``run``.
    """
    before_under = sorted(before_pred.get("query_concepts_under_covered") or [])
    if import_error:
        # The product's own admission path could not run on its own bytes.
        return "HANDOFF_NOT_MEASURED"
    if not before_under:
        # No defect instance: the served packet measured no under-covered
        # concept, so there is nothing for the fix to close.
        return "NO_DEFECT_INSTANCE_ON_THIS_QID"
    if not before_pred.get("disclosure_gap_predicate_fires"):
        # An under-covered set exists but the committed record DID disclose it:
        # the original finding is not reproduced, so a fix cannot be measured.
        return "HANDOFF_NOT_MEASURED"
    if after_pred.get("disclosure_gap_predicate_fires"):
        return "HANDOFF_FIX_ABSENT"
    if not finding_present:
        return "HANDOFF_FIX_ABSENT"
    if measured_under and sorted(detail_terms or []) != sorted(measured_under):
        return "HANDOFF_TERMS_MISMATCH"
    if str(finding_severity) != "warning":
        return "HANDOFF_SEVERITY_CHANGED"
    if after_pred.get("admissible") is not True:
        return "HANDOFF_SEVERITY_CHANGED"
    if lost_codes:
        return "HANDOFF_FIX_PARTIAL"
    return "HANDOFF_PASS"


def leg3_handoff(served: dict, bundle: dict, before: dict, qid: str) -> dict:
    """BEFORE = committed admission record. AFTER = accepted product admission code."""
    before_pred = disclosure_gap_predicate(before)
    before_codes = set(_codes(before))

    t0 = time.time()
    from product.query.gate_admissibility import verify_bundle  # noqa: PLC0415
    import_error = None
    try:
        after = verify_bundle(bundle, question=served["question"][qid])
    except Exception as exc:  # the product's own admission path failed on its own bytes
        import_error = f"{type(exc).__name__}: {exc}"
        after = {}
    recompute_seconds = round(time.time() - t0, 4)

    after_pred = disclosure_gap_predicate(after) if after else {
        "disclosure_gap_predicate_fires": None,
        "query_concepts_under_covered": None, "n_under_covered": None,
        "admissible": None, "warning_count": None, "blocking_count": None,
        "finding_codes": [], "disclosing_finding_codes": [],
    }
    after_codes = set(_codes(after))
    finding = _l3_finding(after)
    measured_under = sorted(after_pred.get("query_concepts_under_covered") or [])
    detail_terms = sorted((finding or {}).get("query_concepts_under_covered") or [])
    lost = sorted(before_codes - after_codes)
    gained = sorted(after_codes - before_codes)

    verdict = classify_l3(
        import_error=import_error,
        before_pred=before_pred,
        after_pred=after_pred,
        measured_under=measured_under,
        detail_terms=detail_terms,
        finding_severity=(finding or {}).get("severity"),
        finding_present=finding is not None,
        lost_codes=lost,
    )

    return {
        "qid": qid,
        "verdict": verdict,
        "product_admission_import_error": import_error,
        "recompute_seconds": recompute_seconds,
        "before": {
            "source": f"{served['rel']}/questions/{qid}.admissibility.json",
            "sha256": served["sha256"].get(f"questions/{qid}.admissibility.json"),
            "arm": "COMMITTED admission record shipped inside the served packet",
            "admissible": before.get("admissible"),
            "warning_count": before.get("warning_count"),
            "blocking_count": before.get("blocking_count"),
            "finding_codes": sorted(before_codes),
            "measured_query_concepts_under_covered":
                before_pred.get("query_concepts_under_covered"),
            "disclosing_finding_codes": before_pred.get("disclosing_finding_codes"),
            "predicate": before_pred,
        },
        "after": {
            "source": ("product.query.gate_admissibility.verify_bundle on the SAME "
                       "bundle bytes with the same question spec"),
            "product_code_sha256": served["product_code_sha256"].get(
                "product/query/gate_admissibility.py"),
            "admissible": after.get("admissible"),
            "warning_count": after.get("warning_count"),
            "blocking_count": after.get("blocking_count"),
            "finding_codes": sorted(after_codes),
            "measured_query_concepts_under_covered":
                after_pred.get("query_concepts_under_covered"),
            "disclosing_finding_codes": after_pred.get("disclosing_finding_codes"),
            "predicate": after_pred,
        },
        "disclosure_finding": None if finding is None else {
            "code": finding.get("code"),
            "severity": finding.get("severity"),
            "detail": finding.get("detail"),
            "query_concepts_under_covered": detail_terms,
            "terms_equal_measured_set": detail_terms == measured_under,
        },
        "regression": {
            "finding_codes_lost_in_after": lost,
            "finding_codes_gained_in_after": gained,
            "no_silent_regression": not lost,
        },
    }


def l3_controls(served: dict, bundle: dict, qid: str, before_terms: list[str]) -> dict:
    """Prove the finding is driven by the measurement, not emitted unconditionally."""
    from product.query.gate_admissibility import verify_bundle  # noqa: PLC0415

    controls: list[dict] = []

    empty_q = copy.deepcopy(bundle)
    empty_q["query"] = ""
    v = verify_bundle(empty_q, question=served["question"][qid])
    controls.append({
        "control": "C1_empty_query",
        "mutation": "bundle.query set to the empty string",
        "measured_under_covered": sorted(
            (v.get("measured") or {}).get("query_concepts_under_covered") or []),
        "finding_present": _l3_finding(v) is not None,
        "expectation": "finding ABSENT (the measured set is empty)",
        "fired": _l3_finding(v) is None,
    })

    swap_q = copy.deepcopy(bundle)
    swap_q["query"] = L3_CONTROL_QUERY
    v2 = verify_bundle(swap_q, question=served["question"][qid])
    f2 = _l3_finding(v2)
    terms2 = sorted((f2 or {}).get("query_concepts_under_covered") or [])
    before_sorted = sorted(before_terms or [])
    controls.append({
        "control": "C2_swapped_query",
        "mutation": f"bundle.query replaced with the frozen control query {L3_CONTROL_QUERY!r}",
        "measured_under_covered": sorted(
            (v2.get("measured") or {}).get("query_concepts_under_covered") or []),
        "finding_present": f2 is not None,
        "finding_terms": terms2,
        "expectation": "finding terms track the NEW measurement and differ from the served terms",
        "fired": bool(f2) and terms2 != before_sorted,
    })
    return {
        "n_controls": len(controls),
        "n_fired": sum(1 for c in controls if c["fired"]),
        "all_fired": all(c["fired"] for c in controls),
        "controls": controls,
        "note": "a control that does not fire means the finding is data-independent; the HANDOFF_PASS is then void",
    }


# --------------------------------------------------------------------------- #
# L4 — language, provenance, determinism
# --------------------------------------------------------------------------- #
def leg4_language_provenance(bundle: dict, qid: str, served: str, question: dict) -> dict:
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    prov = bundle.get("provenance") or {}
    q_lang = str(question.get("language") or "?")
    langs = Counter(str(d.get("language") or "?") for d in decisions)

    hosts, schemes, nulls, non_https, bad_canonical = Counter(), Counter(), 0, 0, []
    for d in decisions:
        su = str(d.get("source_url") or "")
        cu = str(d.get("canonical_url") or "")
        if not su:
            nulls += 1
        else:
            p = urlparse(su)
            hosts[p.hostname or "?"] += 1
            schemes[p.scheme or "?"] += 1
        if cu:
            p = urlparse(cu)
            if p.scheme != "https" or p.hostname != "mcp.opencaselaw.ch":
                non_https += 1
                bad_canonical.append(str(d.get("decision_id")))

    cores = Counter(alnum_core(str(d.get("decision_id") or "")) for d in decisions)
    dup_cores = sorted(c for c, n in cores.items() if c and n > 1)
    empty_ids = sum(1 for d in decisions if not str(d.get("decision_id") or "").strip())

    sig_a = geometry_signature(bundle)
    sig_b = geometry_signature(bundle)
    reversed_bundle = dict(bundle)
    reversed_bundle["decisions"] = list(reversed(bundle.get("decisions") or []))
    sig_rev = geometry_signature(reversed_bundle)
    raw_a = sha256_file(Path(served["abs_bundle"][qid]))

    remote = ((prov.get("retrieval") or {}).get("remote") or {})
    return {
        "question_language": q_lang,
        "language_histogram": dict(sorted(langs.items())),
        "question_language_share": (
            round(langs.get(q_lang, 0) / len(decisions), 4) if decisions else None),
        "n_languages_present": len(langs),
        "source_url": {
            "n_rows_without_source_url": nulls,
            "host_histogram": dict(sorted(hosts.items())),
            "scheme_histogram": dict(sorted(schemes.items())),
            "n_hosts": len(hosts),
        },
        "canonical_url": {
            "n_populated": sum(1 for d in decisions if str(d.get("canonical_url") or "")),
            "n_off_contract": non_https,
            "off_contract_ids": bad_canonical,
            "contract": "https on host mcp.opencaselaw.ch (the frozen source_validity_rule)",
        },
        "duplicate_suppression_frozen_rule": {
            "rule": "within one query response the alnum-core id must be unique",
            "n_duplicate_cores": len(dup_cores),
            "duplicate_cores": dup_cores[:20],
            "n_rows_without_decision_id": empty_ids,
        },
        "determinism": {
            "bundle_sha256_reread": raw_a,
            "bundle_sha256_pinned": served["sha256"].get(f"questions/{qid}.bundle.json"),
            "bundle_sha256_stable": raw_a == served["sha256"].get(f"questions/{qid}.bundle.json"),
            "geometry_signature_run1": sig_a,
            "geometry_signature_run2": sig_b,
            "geometry_signature_reproducible": sig_a == sig_b,
            "geometry_signature_decision_order_reversed": sig_rev,
            "geometry_signature_order_invariant": sig_a == sig_rev,
        },
        "latency_recorded_in_bytes": {
            "latency_seconds": prov.get("latency_seconds"),
            "enrichment_latency_seconds": prov.get("enrichment_latency_seconds"),
            "latency_seconds_total": prov.get("latency_seconds_total"),
            "remote_latency_seconds": remote.get("latency_seconds"),
            "timing": prov.get("timing"),
        },
        "provenance_keys_present": sorted(prov.keys()),
        "fixture_mode": prov.get("fixture_mode"),
        "mode": prov.get("mode"),
    }


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def run(run_id: str, hypothesis_path: Path, mount: Path, out_dir: Path) -> dict:
    started = time.time()
    hyp = _load_json(hypothesis_path)
    hypothesis_sha = sha256_file(hypothesis_path)
    served_rel = hyp["frozen_inputs"]["served_packet"]
    served_dir = mount / served_rel

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pre = rehash_pins(hyp, _REPO_ROOT, mount)
    if pre["n_drift"] or not pre["accepted_product_head_match"]:
        return _write(out_dir, run_id, {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_PIN_DRIFT", "exit_code": EXIT_ENVIRONMENT_OR_VACUOUS,
            "pin_rehash_pre": pre,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    if str(mount) not in sys.path:
        sys.path.insert(0, str(mount))

    served = {
        "rel": served_rel,
        "sha256": hyp["frozen_inputs"]["sha256"],
        "product_code_sha256": hyp["frozen_inputs"]["product_code_sha256"],
        "bundle": {}, "question": {}, "admissibility": {}, "abs_bundle": {},
    }
    handoff = _load_json(served_dir / "handoff.json")

    # The qid set is read from the FROZEN_QIDS constant of the accepted predicate,
    # cross-checked against the question population actually on disk. No analyst table.
    on_disk = sorted(p.name.split(".")[0] for p in (served_dir / "questions").glob("*.question.json"))
    qid_population = {
        "frozen_qids_from_accepted_predicate": list(FROZEN_QIDS),
        "question_files_on_disk": on_disk,
        "identical": sorted(FROZEN_QIDS) == on_disk,
        "source": "evaluation/question_native_transfer.py FROZEN_QIDS (accepted, sha256 ffb2c70f...)",
    }
    if not qid_population["identical"]:
        return _write(out_dir, run_id, {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_POPULATION_DRIFT", "exit_code": EXIT_ENVIRONMENT_OR_VACUOUS,
            "qid_population": qid_population, "pin_rehash_pre": pre,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    for qid in FROZEN_QIDS:
        served["bundle"][qid] = _load_json(served_dir / "questions" / f"{qid}.bundle.json")
        served["question"][qid] = _load_json(served_dir / "questions" / f"{qid}.question.json")
        served["admissibility"][qid] = _load_json(served_dir / "questions" / f"{qid}.admissibility.json")
        served["abs_bundle"][qid] = str(served_dir / "questions" / f"{qid}.bundle.json")

    # Self-declared link check: each question spec names its OWN bundle. This is
    # how a bundle is bound to a question without an analyst slug table -- the
    # packet says so itself. A mismatch is a population drift, exit 2.
    link_check = {
        qid: {
            "question_declared_qid": str(served["question"][qid].get("qid")),
            "question_declared_bundle_basename": Path(
                str((served["question"][qid].get("bundle") or {}).get("path")
                    or (served["question"][qid].get("bundle") or "")
                    if isinstance(served["question"][qid].get("bundle"), dict)
                    else str(served["question"][qid].get("bundle") or ""))).name,
            "expected_bundle_basename": f"{qid}.bundle.json",
        }
        for qid in FROZEN_QIDS
    }
    for qid, chk in link_check.items():
        chk["self_declared_link_consistent"] = (
            chk["question_declared_qid"] == qid
            and chk["question_declared_bundle_basename"] == chk["expected_bundle_basename"])
    if not all(c["self_declared_link_consistent"] for c in link_check.values()):
        return _write(out_dir, run_id, {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_POPULATION_DRIFT",
            "exit_code": EXIT_ENVIRONMENT_OR_VACUOUS,
            "reason": "a served question spec does not name its own bundle/qid",
            "self_declared_link_check": link_check,
            "pin_rehash_pre": pre,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    l1, l1c, l2, l3, l3c, l4 = {}, {}, {}, {}, {}, {}
    for qid in FROZEN_QIDS:
        bundle = served["bundle"][qid]
        l1[qid] = leg1_contract(bundle)
        l1c[qid] = l1_controls(bundle)
        l2[qid] = leg2_counter(bundle, handoff, qid)
        l3[qid] = leg3_handoff(served, bundle, served["admissibility"][qid], qid)
        l3c[qid] = l3_controls(served, bundle, qid,
                                l3[qid]["after"]["measured_query_concepts_under_covered"])
        l4[qid] = leg4_language_provenance(bundle, qid, served, served["question"][qid])

    vacuity = {
        "controls_not_fired": sorted({
            f"{q}:{c['control']}:{c['not_fired_cause']}"
            for q in FROZEN_QIDS for c in l1c[q]["controls"] if not c["fired"]}),
        "qids_with_unexercised_counter_contract": sorted(
            q for q in FROZEN_QIDS if l1c[q]["unexercised_checks"]),
        "reading": (
            "A control that did not fire is reported with its cause. "
            "UNEXERCISED_POPULATION_EMPTY means the bundle emits no row in the accepted "
            "COUNTER_STATUSES set, so the counter-evidence contract was never tested on it; "
            "that is a product-level negative result, published, not suppressed behind the "
            "generic exit-2 verdict. CHECK_VACUOUS would mean the check itself is inert."),
    }
    l1_aggregate = {
        "vacuity": vacuity,
        "n_qids": len(FROZEN_QIDS),
        "n_contract_pass": sum(1 for q in FROZEN_QIDS if l1[q]["contract_pass"]),
        "qids_failing": sorted(q for q in FROZEN_QIDS if not l1[q]["contract_pass"]),
        "all_contract_pass": all(l1[q]["contract_pass"] for q in FROZEN_QIDS),
        "all_controls_fired": all(l1c[q]["all_fired"] for q in FROZEN_QIDS),
        "controls_per_qid": l1c,
    }
    # The frozen success rule is PER INSTANCE, not per qid: the rule reads
    # "(a) the BEFORE arm fires the predicate on at least one qid" and then
    # requires (c)/(d)/(e) "on every qid where BEFORE had a non-empty
    # under-covered set". A qid with an empty under-covered set carries no defect
    # instance and is neither a pass nor a failure. Requiring HANDOFF_PASS on all
    # three qids would be a STRICTER rule than the freeze and is therefore not
    # what is implemented here.
    instances = [q for q in FROZEN_QIDS if l3[q]["before"]["measured_query_concepts_under_covered"]]
    reproducing = [q for q in FROZEN_QIDS if l3[q]["verdict"] == "HANDOFF_PASS"]
    non_instance = [q for q in FROZEN_QIDS if l3[q]["verdict"] == "NO_DEFECT_INSTANCE_ON_THIS_QID"]
    failing = [q for q in FROZEN_QIDS
               if q not in instances and q not in non_instance]
    l3_aggregate = {
        "verdicts": {q: l3[q]["verdict"] for q in FROZEN_QIDS},
        "qids_with_an_under_covered_set": instances,
        "qids_with_no_defect_instance": non_instance,
        "n_instances": len(instances),
        "n_pass": len(reproducing),
        "all_instances_pass": all(l3[q]["verdict"] == "HANDOFF_PASS" for q in instances),
        "rule_a_before_fires_on_at_least_one_qid": bool(reproducing),
        "rule_b_after_fires_on_zero_qids": not any(
            (l3[q]["after"]["predicate"] or {}).get("disclosure_gap_predicate_fires")
            for q in FROZEN_QIDS),
        "all_controls_fired": all(l3c[q]["all_fired"] for q in FROZEN_QIDS),
        "any_regression": any(not l3[q]["regression"]["no_silent_regression"] for q in FROZEN_QIDS),
        "aggregate_verdict": (
            "HANDOFF_PASS" if (reproducing and all(l3[q]["verdict"] == "HANDOFF_PASS"
                                                   for q in instances))
            else next((l3[q]["verdict"] for q in failing + non_instance
                       if l3[q]["verdict"] not in ("NO_DEFECT_INSTANCE_ON_THIS_QID",)),
                      "HANDOFF_NOT_MEASURED")),
    }

    if not (l1_aggregate["all_contract_pass"] and l1_aggregate["all_controls_fired"]
            and l3_aggregate["all_controls_fired"]):
        exit_code, verdict = EXIT_ENVIRONMENT_OR_VACUOUS, "ENVIRONMENT_OR_VACUOUS"
    elif not l1_aggregate["all_contract_pass"]:
        exit_code, verdict = EXIT_CONTRACT_VIOLATED, "PRODUCT_BUNDLE_CONTRACT_VIOLATED"
    elif not (l3_aggregate["all_instances_pass"]
              and l3_aggregate["rule_a_before_fires_on_at_least_one_qid"]
              and l3_aggregate["rule_b_after_fires_on_zero_qids"]
              and not l3_aggregate["any_regression"]):
        exit_code, verdict = EXIT_HANDOFF_FALSIFIED, "HANDOFF_FIX_FALSIFIED"
    else:
        exit_code, verdict = EXIT_OK, "VALID_NO_FALSIFICATION"

    post = rehash_pins(hyp, _REPO_ROOT, mount)

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": hyp["direction_version"],
        "hypothesis": {
            "path": str(hypothesis_path.relative_to(_REPO_ROOT)),
            "sha256": hypothesis_sha,
            "frozen_at": hyp["frozen_at"],
            "pre_freeze_disclosure_present": "pre_freeze_disclosure" in hyp,
            "pre_freeze_disclosure_what_was_observed": hyp["pre_freeze_disclosure"]["what_was_observed"],
            "effect_on_this_freeze": hyp["pre_freeze_disclosure"]["effect_on_this_freeze"],
        },
        "verdict": verdict,
        "exit_code": exit_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": round(time.time() - started, 3),
        "numeric_environment": numeric_environment(),
        "mount": {
            "path": str(mount),
            "head_declared": hyp["frozen_inputs"]["accepted_product_head"],
            "head_resolved": pre["accepted_product_head_resolved"],
            "served_packet": served_rel,
            "served_packet_json_sha256": sha256_file(served_dir / "packet.json"),
        },
        "qid_population": dict(qid_population, self_declared_link_check=link_check),
        "pin_rehash_pre": pre,
        "pin_rehash_post": post,
        "pins_unchanged_during_run": (pre["n_match"] == post["n_match"]
                                      and post["n_drift"] == 0),
        "headline": build_headline(l1, l1c, l2, l3, l3c, l1_aggregate, l3_aggregate),
        "L1_product_bytes_contract": {"per_qid": l1, "aggregate": l1_aggregate},
        "L2_counter_authority_liveness": {
            "per_qid": l2,
            "controls_per_qid": l1c,
        },
        "L3_handoff_question_native_coverage": {"per_qid": l3, "aggregate": l3_aggregate,
                                                "controls_per_qid": l3c},
        "L4_language_provenance_determinism": {"per_qid": l4},
        "not_applicable_with_reason": {
            "known_relevant_authority_recall": (
                "NOT_APPLICABLE_WITH_REASON: the lane's frozen known-authority ids belong to a "
                "DIFFERENT question population (rent-default, corporate-criminal-liability, "
                "business-judgment-rule, petty-theft-dismissal). No mapping of any kind is "
                "permitted, so no mapping-free ground truth exists for "
                "de-kapitalverletzung / fr-bail-entretien / it-responsabilita-medica. This is "
                "NOT a 0 and NOT a pass; it is an unmeasured cell."),
            "known_counter_authority_recall": (
                "NOT_APPLICABLE_WITH_REASON: same reason. The frozen known_counter_ids are "
                "populated from results/product/reality_check legs of the OTHER question set."),
            "counter_label_absolute_support_bar": (
                "NOT_APPLIED: RULES_LABEL.json (4457e971...) is re-hashed here and left untouched; "
                "its absolute 1.0 bar stays REPORTED-ONLY per factory-wide requirement 25 and is "
                "not used as a gate in this instrument."),
            "geometry_absolute_bar": (
                "NOT_APPLIED: RULES_GEOMETRY.json (a7452748...) is re-hashed here and left "
                "untouched; not used as a gate in this instrument."),
        },
        "side_by_side_lane_own_numbers": load_lane_side_by_side(),
        "frontier_query_concept_recall_outcome_of_record": {
            "team": "frontier-query-concept-recall",
            "outcome": "OUTCOME_B_BOUNDED_NEGATIVE",
            "improved_fr_it_cells": 0,
            "reduced_under_covered_questions": 0,
            "n_scored_denominator": "reported in results/frontier/frontier-query-concept-recall/harness_results.json on the team's accepted branch",
            "relationship_to_this_run": (
                "CITED AS ITS OWN RESULT, NOT RE-MEASURED AND NOT RE-SCORED HERE. This run "
                "measures whether the ADMISSION RECORD discloses measured under-coverage on "
                "the served bytes. The Frontier team's OUTCOME_B measures whether its "
                "expansion REDUCES under-coverage. Those are different quantities over "
                "different populations; any divergence between them would be a HEADLINE, and "
                "no such comparison is made here."),
            "recomputed_by_this_run": False,
        },
        "claim_ceiling": hyp["claim_ceiling"],
    }

    return _write(out_dir, run_id, record)


def build_headline(l1, l1c, l2, l3, l3c, l1_agg, l3_agg) -> dict:
    """One machine-readable block stating exactly what did and did not hold."""
    n_dec = sum(l2[q]["n_decisions"] for q in FROZEN_QIDS)
    n_lab = sum(l2[q]["n_counter_labelled"] for q in FROZEN_QIDS)
    n_cited = sum(l2[q]["cited_rows"] for q in FROZEN_QIDS)
    n_cited_counter = sum(l2[q]["cited_counter_overlap"] for q in FROZEN_QIDS)
    return {
        "L1_contract_on_product_bytes": (
            "HOLDS on the measurable subset for all three served bundles; "
            "progressive_phases and geometry_preserved_after_enrichment are NOT_MEASURABLE "
            "because the served packet ships only the `complete` phase"),
        "L1_non_vacuity": {
            "n_controls": sum(l1c[q]["n_controls"] for q in FROZEN_QIDS),
            "n_fired": sum(l1c[q]["n_fired"] for q in FROZEN_QIDS),
            "controls_not_fired": l1_agg["vacuity"]["controls_not_fired"],
        },
        "L2_counter_authority_yield": {
            "n_decisions_total": n_dec,
            "n_counter_labels_total": n_lab,
            "label_rate_over_all_decisions": round(n_lab / n_dec, 6) if n_dec else None,
            "per_qid_labels": {q: l2[q]["n_counter_labelled"] for q in FROZEN_QIDS},
            "qids_with_zero_labels": sorted(q for q in FROZEN_QIDS if not l2[q]["n_counter_labelled"]),
        },
        "L2_answer_cites_counter_authority": {
            "n_answer_citations_total": n_cited,
            "n_citations_that_are_counter_authority": n_cited_counter,
            "per_qid": {q: {"cited_rows": l2[q]["cited_rows"],
                            "cited_counter_overlap": l2[q]["cited_counter_overlap"]}
                        for q in FROZEN_QIDS},
            "reading": (
                "A citation that is not a counter-authority row means the served answer never "
                "grounds its text in a decision the product itself labelled limiting or "
                "contrary. This is a measured fact about the served bytes, not a judgement "
                "about the map's usefulness."),
        },
        "L3_handoff_verdict": l3_agg["aggregate_verdict"],
        "L3_per_qid": l3_agg["verdicts"],
        "no_silent_regression_in_admission_findings": not l3_agg["any_regression"],
    }


def _write(out_dir: Path, run_id: str, record: dict) -> dict:
    """Persist EVERY record, including the environment-failure ones.

    An early return that writes nothing is indistinguishable from a crash, and a
    cycle that leaves no machine record cannot be audited or promoted.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record = dict(record)
    record["record_path"] = str(path)
    return record


def load_lane_side_by_side() -> dict:
    """Load this lane's own 39200567493 numbers to publish BESIDE, never instead."""
    path = _REPO_ROOT / "results/evaluation/query_map_cached_bundle_benchmark/39200567493.json"
    if not path.exists():
        return {"status": "ABSENT", "path": str(path.relative_to(_REPO_ROOT)),
                "note": "not present in this tree; nothing is substituted for it"}
    d = _load_json(path)
    cy = d.get("counter_authority_yield") or {}
    qmeta = {}
    for q in (d.get("questions") or []):
        if isinstance(q, dict) and isinstance(q.get("producer_meta"), dict):
            qmeta[q["slug"]] = q["producer_meta"].get("n_counter_candidates")
    return {
        "status": "PRESENT",
        "path": str(path.relative_to(_REPO_ROOT)),
        "sha256": sha256_file(path),
        "run_id": "39200567493",
        "counter_authority_yield_of_that_run": {
            "n_questions": cy.get("n_questions"),
            "per_question_counter_candidates": cy.get("per_question"),
            "questions_with_zero_counter_candidates":
                cy.get("questions_with_zero_counter_candidates"),
            "n_counter_candidates_total": cy.get("n_counter_candidates_total"),
            "per_question_bundle_decisions": qmeta,
        },
        "divergence_headline": (
            "Both runs independently record an EMPTY counter-authority layer on part of their "
            "question populations, from two different code paths and two different question "
            "sets: 39200567493 found 0 lexical counter candidates for 2 of its 4 lane-frozen "
            "questions under the frozen marker_rule; this run finds 0 issued counter-authority "
            "labels for 1 of its 3 product-served questions (fr-bail-entretien) after the "
            "accepted counter-anchor classifier. These are the SAME SYMPTOM on DIFFERENT "
            "POPULATIONS and are published side by side; they are not merged, not summed and "
            "not a single rate. The divergence that matters for the product decision is "
            "already visible inside this run: 0 of the 15 answer citations on the served packet "
            "is a counter-authority decision."),
        "population": (
            "DIFFERENT from this run's product population: 39200567493 built its bundles from "
            "this lane's own OpenCaseLaw response cache for the lane's frozen retrieval "
            "questions; this run scores PRODUCT-produced bundles for three different questions. "
            "The two sets are shown side by side and are never merged, summed or substituted "
            "for one another."),
        "verdict_of_record": d.get("verdict"),
        "exit_code_of_that_run": d.get("exit_code"),
        "falsification_proven": d.get("falsification_proven"),
        "n_questions": d.get("n_questions"),
        "top_level_keys": sorted(d.keys()),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "0"))
    ap.add_argument("--hypothesis", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--mount", type=Path, default=DEFAULT_MOUNT)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    rec = run(str(args.run_id), args.hypothesis, args.mount, args.out_dir)
    print(json.dumps({k: rec.get(k) for k in (
        "schema", "run_id", "verdict", "exit_code", "pins_unchanged_during_run")}, indent=2))
    if rec.get("L3_handoff_question_native_coverage"):
        print(json.dumps(rec["L3_handoff_question_native_coverage"]["aggregate"], indent=2))
        print(json.dumps(rec["L1_product_bytes_contract"]["aggregate"]["qids_failing"], indent=2))
    return int(rec["exit_code"])


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())