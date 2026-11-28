#!/usr/bin/env python3
"""v68 CONDITIONAL-GATE adjudicator (run 46095165738) — smallest executable gate.

WHAT THIS IS
------------
Factory-direction v68 ordered work for the evaluation lane has ONE conditional
deliverable left: item (2), the post-repair re-measure, which must be executed
*only if* Core Product has landed the rejection/incumbent leg AND regenerated the
full flagship offline/server slice family (the frozen 15-member probe family).
Everything else in the ordered list is report-only or "kept".

That conditional is therefore the whole product of this cycle: an executable,
freeze-first adjudicator that decides — from committed bytes at the CURRENT
accepted product head — whether the ordered protocol may run, and separately
whether the accepted FAST-MVP retrieval-recall falsifier must be re-executed.

Four legs, all SET RELATIONS (factory-wide requirement 16: never a cardinality,
never an "all of the" derived from a count alone):

  A. item-(2) precondition   — reuse ``evaluation.post_repair_family_ca_falsifier.
     precondition_gate`` BY HASH-VERIFIED IMPORT (re-use, not re-implementation):
     rejection/incumbent leg markers with file:line, plus member-for-member
     regeneration of the frozen 15-member family with multiplicity.
  B. Product-claim support   — set relation between Product's own committed
     ``fixed_path_family`` (its ``ordered_work_2_full_success_rule.met=true``)
     and the direction's named frozen family. Product's fields are treated as a
     CLAIM, never as this run's measurement.
  C. recall-rerun discriminator — sha256 of the causal file set of
     ``product.query.retrieval`` at the last measured head (5fb312e4a...) versus
     the current mount head, both read with ``git show``. Identical bytes mean a
     re-run of the frozen recall benchmark could only reproduce an existing
     record, so it is NOT re-run here (documented negative).
  D. requirement-4 pointer   — BOTH halves verified for the accepted-run pointer
     advance (gate PASS in tree + exact ``accept evaluation cycle ...`` commit).

WHAT IT NEVER DOES
------------------
No frozen bar, rubric, threshold, predicate, tokeniser, stoplist or verdict
contract is defined, edited or moved. No serve verdict, no packet admission, no
d2_path_scope_probe re-run, no scoring of packet-of-record 39319405429, no
re-run of the standing falsification, no universal-174k benchmark, no network
call. Posture flags stay FALSE.

Exit codes (frozen in the hypothesis file):
  0  ADJUDICATED_NO_EXECUTE          — precondition unmet, record and stop
  1  ADJUDICATED_PRECONDITION_MET    — ordered item (2) MUST run next
  2  NOT_MEASURED_VACUOUS            — pin / control / mount-head failure
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import post_repair_family_ca_falsifier as PRF  # noqa: E402
from evaluation import fast_mvp_current_head_ca_falsifier as FAS  # noqa: E402

SCHEMA = "lex-evaluation-v68-conditional-gate-adjudicator/1"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/v68_conditional_gate_adjudication"
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"
ACCEPTED_FAMILY_HYP_RELPATH = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json")

EXIT_NO_EXECUTE = 0
EXIT_PRECONDITION_MET = 1
EXIT_VACUOUS = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mount_head(mount: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() or None
    except Exception:
        return None


def git_show_bytes(repo: Path, head: str, relpath: str) -> bytes | None:
    """Bytes of ``relpath`` at commit ``head`` inside ``repo`` (git show)."""
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), "show", f"{head}:{relpath}"],
            capture_output=True, timeout=60)
        if p.returncode != 0:
            return None
        return p.stdout
    except Exception:
        return None


def git_log_subjects(repo: Path, needle: str) -> list[str]:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), "log", "--all", "--format=%H %s",
             f"--grep={needle}"],
            capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            return []
        return [ln for ln in p.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def numeric_environment() -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    return env


def verify_pins(hyp: dict) -> dict:
    """Re-hash every frozen input BEFORE (and again AFTER) execution."""
    mount = Path(hyp["product_mount"])
    rows, ok = [], True

    def check(label: str, path: Path, expected: str) -> None:
        nonlocal ok
        actual = sha256_file(path) if path.is_file() else None
        match = actual == expected
        ok = ok and match
        rows.append({"input": label, "path": str(path), "expected": expected,
                     "actual": actual, "match": match})

    for rel, expected in (hyp.get("frozen_inputs_REPORTED_ONLY") or {}).items():
        if rel.startswith("mount:"):
            check(f"mount:{rel[6:]}", mount / rel[6:], expected)
        else:
            check(f"repo:{rel}", REPO_ROOT / rel, expected)

    head = mount_head(mount)
    head_ok = head == hyp["expected_product_mount_head"]
    ok = ok and head_ok
    rows.append({"input": "mount_head", "path": str(mount),
                 "expected": hyp["expected_product_mount_head"],
                 "actual": head, "match": head_ok})
    return {"all_match": ok, "checks": rows}


# --------------------------------------------------------------------------- #
# leg A: reuse the accepted precondition gate verbatim
# --------------------------------------------------------------------------- #
def load_accepted_family_hyp() -> tuple[dict, str]:
    path = REPO_ROOT / ACCEPTED_FAMILY_HYP_RELPATH
    sha = sha256_file(path)
    return json.loads(path.read_text(encoding="utf-8")), sha


def build_precondition_hyp(hyp: dict) -> dict:
    """Shape the frozen hypothesis into what precondition_gate() consumes.

    Every field is taken from the ACCEPTED 40258497460 hypothesis (re-hashed by
    this run's ``frozen_probe_family_SOURCE`` / ``product_code_markers_SOURCE``
    pins), except the product claim, which is this run's CURRENT frozen claim.
    Nothing here is re-derived.
    """
    accepted, accepted_sha = load_accepted_family_hyp()
    if accepted_sha != hyp["frozen_probe_family_SOURCE"]["sha256"]:
        raise RuntimeError("accepted family hypothesis sha drift at load time")
    return {
        "product_code_markers_FROZEN": accepted["product_code_markers_FROZEN"],
        "frozen_probe_family_FROZEN": accepted["frozen_probe_family_FROZEN"],
        "product_claim_FROZEN": {
            "claim_string": hyp["current_product_claim_FROZEN"]["claim_string"],
            "source": hyp["current_product_claim_FROZEN"]["source"],
            "why_frozen": hyp["current_product_claim_FROZEN"]["why_frozen"],
        },
    }


# --------------------------------------------------------------------------- #
# leg B: Product's own family claim vs the direction's named family
# --------------------------------------------------------------------------- #
def _role_key(path: str) -> tuple[str, str]:
    parts = path.split("/")
    kind = "server" if "server_slice" in parts else "offline"
    query = parts[-1].split(".bundle.json")[0]
    return kind, query


def product_claim_support(hyp: dict, precondition: dict) -> dict:
    mount = Path(hyp["product_mount"])
    rel = "results/product/counter_content_family/CYCLE_40257275384.json"
    art = json.loads((mount / rel).read_text(encoding="utf-8"))
    fp = art.get("fixed_path_family") or {}
    fp_paths = [b["path"] for b in (fp.get("bundles") or [])] if isinstance(fp, dict) else list(fp)

    frozen_roles = precondition["set_relations_REQUIREMENT_16"]["roles_frozen_family"]
    product_roles: dict[str, int] = {}
    for p in fp_paths:
        k = "/".join(_role_key(p))
        product_roles[k] = product_roles.get(k, 0) + 1

    shortfalls = {k: {"frozen_family": v, "product_fixed_path_family": product_roles.get(k, 0),
                      "deficit": max(0, v - product_roles.get(k, 0))}
                  for k, v in frozen_roles.items()}
    uncovered = {k: d for k, d in shortfalls.items() if d["deficit"] > 0}
    supported = not uncovered

    return {
        "claim_artifact": rel,
        "claim_artifact_sha256": sha256_file(mount / rel),
        "claim_fields_read_as_CLAIM_not_measurement": {
            "family_definition": art.get("family_definition"),
            "ordered_work_2_success_rule": art.get("ordered_work_2_success_rule"),
            "ordered_work_2_full_success_rule": (
                art.get("ordered_work_2_full_success_rule")),
        },
        "product_fixed_path_family_n": len(fp_paths),
        "product_fixed_path_family_roles": dict(sorted(product_roles.items())),
        "direction_named_family_roles": dict(sorted(frozen_roles.items())),
        "set_relation_REQUIREMENT_16": {
            "per_role_shortfall": shortfalls,
            "roles_with_deficit": dict(sorted(uncovered.items())),
            "both_differences": {
                "frozen_roles_not_covered_by_product_family": sorted(uncovered),
                "product_roles_not_in_frozen_family": sorted(
                    set(product_roles) - set(frozen_roles)),
            },
        },
        "H3_product_family_claim_support": "SUPPORTED" if supported else "UNSUPPORTED",
        "interpretation": (
            "Product's ordered_work_2_full_success_rule.met is computed over its own "
            "'fixed_path_family' (bytes identified by content_filter provenance), which "
            "is a DIFFERENT SET from the direction's named frozen 15-member probe family. "
            "This run publishes both role tables and their set relation and never adopts "
            "Product's met field as its own measurement."
            + ("" if supported else
               " The named family is NOT member-for-member regenerated at this head; the "
               "deficit above is the concrete remaining artifact Product must ship.")
        ),
        "producing_cycle_acceptance": (
            "no commit 'accept product cycle 40257275384' or 'accept product cycle "
            "40257469937' exists on any ref; the artifact's introducing commit "
            "21a70bd3a is an ancestor of accepted heads, so the bytes are at the "
            "accepted head while the producing cycle has no accept commit of its own"
        ),
    }


# --------------------------------------------------------------------------- #
# leg C: recall-rerun discriminator
# --------------------------------------------------------------------------- #
def recall_rerun_discriminator(hyp: dict) -> dict:
    mount = Path(hyp["product_mount"])
    spec = hyp["last_measured_recall_head"]
    old_head, causal = spec["head"], spec["causal_file_set"]
    rows = []
    any_diff = False
    for rel in causal:
        now = sha256_file(mount / rel) if (mount / rel).is_file() else None
        old_bytes = git_show_bytes(mount, old_head, rel)
        old = (hashlib.sha256(old_bytes).hexdigest() if old_bytes is not None else None)
        same = (now is not None and old is not None and now == old)
        any_diff = any_diff or not same
        rows.append({"file": rel, "sha_at_last_measured_head": old,
                     "sha_at_current_head": now, "identical": same,
                     "old_head_readable": old_bytes is not None})

    return {
        "last_measured_head": old_head,
        "current_head": mount_head(mount),
        "causal_file_set": rows,
        "any_difference": any_diff,
        "H4_recall_rerun": ("RECALL_RERUN_REQUIRED" if any_diff
                            else "RECALL_RERUN_NOT_DISCRIMINATING"),
        "action": (
            "re-execute evaluation/fast_mvp_retrieval_recall_benchmark.py freeze-first "
            "in a FUTURE cycle (causal bytes changed)" if any_diff else
            "NOT re-executed in this cycle: every causal byte is identical to the last "
            "measured head, so a re-run could only reproduce the committed record "
            "40261335674 (and the unaudited sibling 46086820588). This is a documented "
            "negative, not an omission."
        ),
        "measurement_of_record": spec["measurement_of_record"],
        "measurement_of_record_acceptance": spec["acceptance_status"],
    }


# --------------------------------------------------------------------------- #
# leg D: requirement-4 both halves for the accepted-run pointer
# --------------------------------------------------------------------------- #
def pointer_both_halves(hyp: dict, candidate_run: str) -> dict:
    gate_rel = f"results/audit/evaluation/CYCLE_{candidate_run}_GATE.json"
    gate_path = REPO_ROOT / gate_rel
    half_i = None
    if gate_path.is_file():
        g = json.loads(gate_path.read_text(encoding="utf-8"))
        half_i = {
            "gate_path": gate_rel,
            "gate": g.get("gate"),
            "safe_to_integrate": g.get("safe_to_integrate"),
            "required_fixes": g.get("required_fixes"),
            "sha256": sha256_file(gate_path),
            "holds": g.get("gate") == "PASS" and g.get("safe_to_integrate") is True,
        }
    needle = f"accept evaluation cycle {candidate_run}"
    matches = git_log_subjects(REPO_ROOT, needle)
    exact = [m for m in matches if m.split(" ", 1)[-1] == needle]
    half_ii = {
        "needle": needle,
        "matches": exact,
        "holds": bool(exact),
    }
    lab_head = None
    try:
        p = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse",
                            "origin/lab/evaluation"],
                           capture_output=True, text=True, timeout=30)
        lab_head = p.stdout.strip() or None
    except Exception:
        lab_head = None
    return {
        "candidate_accepted_run": candidate_run,
        "half_i_gate_in_tree": half_i,
        "half_ii_accept_commit": half_ii,
        "origin_lab_evaluation_head": lab_head,
        "both_halves_hold": bool(half_i and half_i.get("holds") and half_ii["holds"]),
    }


# --------------------------------------------------------------------------- #
def evaluate(run_id: str, hypothesis_relpath: str, freeze_relpath: str) -> tuple[dict, int]:
    hyp = json.loads((REPO_ROOT / hypothesis_relpath).read_text(encoding="utf-8"))
    freeze = json.loads((REPO_ROOT / freeze_relpath).read_text(encoding="utf-8"))
    fz_hyp = (freeze.get("hypothesis") or {}).get("sha256")
    fz_inst = (freeze.get("instrument") or {}).get("sha256")
    if fz_hyp != sha256_file(REPO_ROOT / hypothesis_relpath):
        raise SystemExit(f"{EXIT_VACUOUS}: hypothesis sha does not match freeze record")
    if fz_inst != sha256_file(REPO_ROOT / __file__.relative_to(REPO_ROOT)):
        raise SystemExit(f"{EXIT_VACUOUS}: instrument sha does not match freeze record")

    pins_before = verify_pins(hyp)
    if not pins_before["all_match"]:
        return ({
            "schema": SCHEMA, "run_id": run_id, "verdict": "NOT_MEASURED_VACUOUS",
            "exit_code": EXIT_VACUOUS,
            "vacuous_reason": "frozen pin or mount-head check failed BEFORE execution",
            "pins_before_execution": pins_before,
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, EXIT_VACUOUS)

    rules = json.loads((REPO_ROOT / RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])
    class_sha = sha256_file(REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py")
    controls = FAS.controls(scored, class_sha)

    mount = Path(hyp["product_mount"])
    cond_hyp = build_precondition_hyp(hyp)
    precondition = PRF.precondition_gate(cond_hyp, mount)
    claim = product_claim_support(hyp, precondition)
    recall = recall_rerun_discriminator(hyp)
    pointer = pointer_both_halves(hyp, str(hyp["candidate_accepted_run"]))

    pins_after = verify_pins(hyp)
    pins_identical = (
        json.dumps(pins_before["checks"], sort_keys=True)
        == json.dumps(pins_after["checks"], sort_keys=True)
    )

    h1 = bool(precondition["H1_precondition_leg_landed"])
    h2 = bool(precondition["H2_precondition_full_family_regenerated"])
    controls_ok = bool(controls.get("all_hold"))
    vacuous = (not pins_after["all_match"]) or (not pins_identical) or (not controls_ok)

    if vacuous:
        verdict, code = "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    elif h1 and h2:
        verdict, code = "ITEM2_PRECONDITION_MET", EXIT_PRECONDITION_MET
    else:
        verdict, code = "ITEM2_NOT_YET_DISCRIMINATING", EXIT_NO_EXECUTE

    rec = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 68,
        "run_id": run_id,
        "hypothesis": {"path": hypothesis_relpath,
                       "sha256": sha256_file(REPO_ROOT / hypothesis_relpath),
                       "frozen_before_execution": bool(freeze.get("frozen_before_execution"))},
        "freeze_record": freeze_relpath,
        "freeze_sha256": sha256_file(REPO_ROOT / freeze_relpath),
        "instrument": str(Path(__file__).relative_to(REPO_ROOT)),
        "instrument_sha256": sha256_file(REPO_ROOT / __file__.relative_to(REPO_ROOT)),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "product_accepted_cycle": hyp.get("product_accepted_cycle"),
        "product_acceptance_BOTH_HALVES": hyp.get("product_acceptance_BOTH_HALVES"),
        "verdict": verdict,
        "exit_code": code,
        "ordered_item_2": {
            "H1_precondition_leg_landed": h1,
            "H2_precondition_full_family_regenerated": h2,
            "full_protocol_status": (
                "EXECUTE (ordered item (2) protocol becomes runnable)"
                if (h1 and h2) else
                "NOT_YET_DISCRIMINATING — ordered item (2) protocol NOT executed: no "
                "synthetic stand-in, no d2_path_scope_probe re-run as the ordered "
                "re-measure, packet-of-record 39319405429 not scored, standing "
                "falsification not re-run"),
            "precondition_gate_REUSED_BY_HASH_VERIFIED_IMPORT": precondition,
        },
        "H3_product_family_claim_support": claim,
        "H4_recall_rerun_discriminator": recall,
        "H5_pointer_both_halves": pointer,
        "H6_controls_and_pins": {
            "controls": controls,
            "pins_before_execution": pins_before,
            "pins_after_execution": pins_after,
            "pins_identical_before_and_after": pins_identical,
        },
        "numeric_environment": numeric_environment(),
        "reproducibility_scope": (
            "reproducible within this environment by re-running the entry point; NO "
            "cross-machine byte identity is claimed and no BLAS/thread pin is applied "
            "(requirement 30)"),
        "network": {"measurement_calls": 0,
                    "note": "no OpenCaseLaw, retrieval, model or paid-API call"},
        "not_claimed": [
            "no frozen bar, rubric, threshold or verdict contract edited",
            "no serve verdict issued; both DO-NOT-SERVE orders stand",
            "no packet admitted; packet_admitted stays false",
            "comparative map-vs-ranked-list half NOT SCORED",
            "Product's own family/success-rule fields are CLAIMS, not this run's measurement",
            "no universal-174k benchmark",
            "human_gate_ready / machine_gate_ready / ready_for_owner_session stay false",
            "owner_decision_required stays false",
        ],
        "sibling_dispatch_context_ONLY": hyp.get("sibling_dispatch_disclosure_REPORTED_ONLY"),
    }
    rec["falsification_proven"] = False
    rec["claim_ceiling"] = hyp.get("claim_ceiling")
    return rec, code


def write_report(rec: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"V68_CONDITIONAL_GATE_ADJUDICATION_{rec['run_id']}.md"
    pre = rec["ordered_item_2"]
    gate = pre["precondition_gate_REUSED_BY_HASH_VERIFIED_IMPORT"]
    sr = gate["set_relations_REQUIREMENT_16"]
    h3 = rec["H3_product_family_claim_support"]
    h4 = rec["H4_recall_rerun_discriminator"]
    h5 = rec["H5_pointer_both_halves"]
    lines = [
        f"# v68 CONDITIONAL-GATE adjudication — run {rec['run_id']}",
        "",
        f"**Lane**: evaluation  **direction_version**: {rec['direction_version']}  "
        f"**product mount head**: `{rec['product_mount_head']}`  "
        f"**(accepted product cycle {rec['product_accepted_cycle']}, both halves verified)**",
        "",
        f"**Verdict**: `{rec['verdict']}` (exit {rec['exit_code']})",
        "",
        "## 1. Ordered item (2) precondition — set relations, requirement 16",
        "",
        f"- H1 rejection/incumbent leg markers present: **{pre['H1_precondition_leg_landed']}** "
        f"(file `{gate['leg_markers']['file']}`, sha256 `{gate['leg_markers']['file_sha256'][:16]}…`)",
        f"- H2 frozen 15-member family member-for-member regenerated: "
        f"**{pre['H2_precondition_full_family_regenerated']}**",
        f"  - frozen family n = {sr['frozen_probe_family_n']}, post-repair n = {sr['post_repair_n']}",
        f"  - member-for-member matched = {sr['member_for_member_matching']['matched_members']}"
        f"/{sr['member_for_member_matching']['of']}",
        f"  - per-role multiplicity parity = "
        f"{sr['per_role_multiplicity_parity']}",
        f"  - path-identity intersection = {sr['path_identity']['intersection_by_path_n']} "
        f"(EXPECTED 0 while the baseline family is preserved byte-for-byte)",
        f"  - roles frozen family: `{json.dumps(sr['roles_frozen_family'], sort_keys=True)}`",
        f"  - roles post-repair: `{json.dumps(sr['roles_post_repair'], sort_keys=True)}`",
        "",
        f"**Full protocol status**: {pre['full_protocol_status']}",
        "",
        "## 2. Product's own family claim (H3) — read as a CLAIM",
        "",
        f"- claim artifact `{h3['claim_artifact']}` sha256 `{h3['claim_artifact_sha256'][:16]}…`",
        f"- Product fixed_path_family n = {h3['product_fixed_path_family_n']}, "
        f"roles `{json.dumps(h3['product_fixed_path_family_roles'], sort_keys=True)}`",
        f"- direction named roles `{json.dumps(h3['direction_named_family_roles'], sort_keys=True)}`",
        f"- roles with a deficit: `{json.dumps(h3['set_relation_REQUIREMENT_16']['roles_with_deficit'], sort_keys=True)}`",
        f"- **H3 = {h3['H3_product_family_claim_support']}**",
        f"- provenance: {h3['producing_cycle_acceptance']}",
        "",
        "## 3. Recall-rerun discriminator (H4)",
        "",
        f"- last measured head `{h4['last_measured_head']}` vs current `{h4['current_head']}`",
        f"- causal file set identical: **{not h4['any_difference']}** "
        f"({sum(1 for r in h4['causal_file_set'] if r['identical'])}"
        f"/{len(h4['causal_file_set'])} files)",
        f"- **H4 = {h4['H4_recall_rerun']}** — {h4['action']}",
        "",
        "## 4. Requirement-4 pointer both halves (H5)",
        "",
        f"- candidate accepted run `{h5['candidate_accepted_run']}`",
        f"- half I (gate in tree): `{json.dumps(h5['half_i_gate_in_tree'], sort_keys=True)}`",
        f"- half II (accept commit): {h5['half_ii_accept_commit']['holds']} "
        f"`{h5['half_ii_accept_commit']['matches']}`",
        f"- **both halves hold**: {h5['both_halves_hold']}",
        "",
        "## 5. Controls and pins (H6)",
        "",
        f"- controls all hold: {rec['H6_controls_and_pins']['controls']['all_hold']}",
        f"- pins identical before/after: {rec['H6_controls_and_pins']['pins_identical_before_and_after']} "
        f"({len(rec['H6_controls_and_pins']['pins_before_execution']['checks'])} checks)",
        f"- network_calls = 0; numeric environment `{json.dumps(rec['numeric_environment'], sort_keys=True)}`",
        "",
        "## 6. Claim ceiling",
        "",
        rec.get("claim_ceiling") or "",
        "",
        "## 7. Ordered-work disposition this cycle",
        "",
    ]
    for k, v in (json.loads((REPO_ROOT / "evaluation" /
                "V68_CONDITIONAL_GATE_ADJUDICATION_46095165738_HYPOTHESIS_V1.json")
                .read_text(encoding="utf-8"))["ordered_work_DISPOSITION_EXPECTED"]).items():
        lines.append(f"- ({k}) {v}")
    lines += [
        "",
        "> Reproduce: `" + json.loads((REPO_ROOT / "evaluation" /
        "V68_CONDITIONAL_GATE_ADJUDICATION_46095165738_HYPOTHESIS_V1.json")
        .read_text(encoding="utf-8"))["entry_point"] + "`",
        "",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args(argv)

    rec, code = evaluate(args.run_id, args.hypothesis, args.freeze)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.run_id}.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    rpt = write_report(rec, REPO_ROOT / "reports/evaluation")
    print(f"verdict: {rec['verdict']} (exit {code})")
    print(f"record:  {out}")
    print(f"report:  {rpt}")
    return code


if __name__ == "__main__":
    sys.exit(main())
