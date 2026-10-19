"""Mapping-free falsifier for the accepted ``query_native_coverage`` handoff.

The handoff under test (accepted product_handoff of
``question_native_coverage_39113690481``; transferred by accepted transfer run
39120832665 -> commit 034f2043, verdict ``DISCLOSURE_DEFECT_TRANSFERRED``,
covering ``rebuilt-39027045675``) orders Product to:

    emit an admission finding (severity warning) whenever
    measured.query_concepts_under_covered is non-empty, with the under-covered
    terms in the finding detail.

This lane's job is to falsify-or-pass that fix **on the exact served bytes**
and publish the before/after admission records side by side. It is not the
product's job to be re-scored here and this instrument does not touch any
frozen label or geometry bar.

Mapping-free discipline (frozen in COVERAGE_FINDING_FALSIFICATION_HYPOTHESIS_V1)
------------------------------------------------------------------------------
The instrument applies ONE predicate to every served bundle without exception:

    expected_to_fire := len(measured.query_concepts_under_covered) > 0

and decides whether the finding fired by reading the product's OWN emitted
values: a finding counts as firing when its ``severity`` is ``warning`` and
every under-covered term appears somewhere in that finding's own detail or
fields. There is no analyst slug, no frozen decision-id set, no baseline
admission record and no bundle-to-expectation mapping anywhere in this file.
The two bundles whose under-covered set is empty must stay silent, so a
"fix" that fires unconditionally fails the symmetry rule.

Usage
-----
    python -m evaluation.coverage_finding_falsification --run-id 39164900837 \
        --out results/evaluation/coverage_finding_falsification/39164900837.json

Exit codes: 0 the instrument ran and wrote a record (a FAIL verdict is a
            RESULT and exits 0); 2 environment/pin error, nothing recorded.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.insert(0, str(_LANE_ROOT))

SERVED_PACKET = "results/product/gate_packet/rebuilt-39027045675"
FROZEN_PRODUCT_HEAD = "577efeb836757b0b0eee22f7bc2436c52e2addbb"
REEXEC_SCRIPT = """
import json, sys
from product.query.gate_admissibility import verify_bundle
bundle = json.load(open(sys.argv[1], encoding="utf-8"))
question = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 3 else None
checks = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
verdict = verify_bundle(bundle, question=question,
                        min_decisions=checks.get("min_decisions"),
                        max_decisions=checks.get("max_decisions"),
                        require_answer=bool(checks.get("require_answer", True)))
sys.stdout.write(json.dumps(verdict, ensure_ascii=False))
"""


def _utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finding_blob(finding: dict) -> str:
    """Every value the product itself emitted in this finding."""
    return " ".join(
        [str(finding.get("detail") or "")]
        + [f"{k}={v}" for k, v in finding.items()
           if k not in ("severity", "detail")])


def firing_findings(findings: list[dict], under: list[str],
                    severity: str | None = "warning") -> list[int]:
    """Indices of findings that DISCLOSE every under-covered term.

    Matching is on the product's own emitted values only. ``severity=None``
    is the disclosed loose variant used for reporting, never for the verdict.
    """
    if not under:
        return []
    out = []
    for i, f in enumerate(findings or []):
        if severity is not None and str(f.get("severity") or "").lower() != severity:
            continue
        blob = finding_blob(f)
        if all(str(t) in blob for t in under):
            out.append(i)
    return out


def summarise(verdict: dict, label: str) -> dict:
    measured = verdict.get("measured") or {}
    under = [str(x) for x in (measured.get("query_concepts_under_covered") or [])]
    findings = verdict.get("findings") or []
    strict = firing_findings(findings, under, "warning")
    loose = firing_findings(findings, under, None)
    return {
        "record": label,
        "admissible": verdict.get("admissible"),
        "warning_count": verdict.get("warning_count"),
        "blocking_count": verdict.get("blocking_count"),
        "notice_count": verdict.get("notice_count"),
        "n_findings": len(findings),
        "findings": [{"index": i, "code": f.get("code"), "severity": f.get("severity"),
                      "detail": str(f.get("detail") or "")[:400],
                      "discloses_under_covered": i in strict,
                      "mentions_under_covered_any_severity": i in loose}
                     for i, f in enumerate(findings)],
        "measured_query_concepts_under_covered": under,
        "measured_query_concepts": measured.get("query_concepts"),
        "expected_to_fire": bool(under),
        "observed_fire_strict_warning_severity": bool(strict),
        "firing_finding_indices_strict": strict,
        "firing_finding_indices_any_severity": loose,
        "observed_fire_loose_any_severity": bool(loose),
    }


def reexecute(product_root: Path, bundle: Path, question: Path | None,
              checks: dict) -> tuple[dict | None, dict]:
    with tempfile.TemporaryDirectory(prefix="lex-coverage-falsifier-") as tmp:
        script = Path(tmp) / "_reexec.py"
        script.write_text(REEXEC_SCRIPT, encoding="utf-8")
        cmd = [sys.executable, str(script), str(bundle)]
        if question is not None:
            cmd += [str(question), json.dumps(checks)]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(product_root)
        proc = subprocess.run(cmd, cwd=str(product_root), env=env,
                              capture_output=True, text=True, timeout=900)
    info = {"exit_code": proc.returncode,
            "stderr_tail": (proc.stderr or "").strip().splitlines()[-12:],
            "command_shape": "python <inline> <bundle> [<question> <checks>]",
            "cwd": str(product_root), "PYTHONPATH": str(product_root),
            "product_root_written_to": False}
    if proc.returncode != 0 or not proc.stdout.strip():
        info["error"] = "re-execution produced no verdict"
        return None, info
    return json.loads(proc.stdout), info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--product-root", default="/tmp/lex_accepted/product")
    ap.add_argument("--packet-dir", default=None)
    ap.add_argument("--repo-root", default=str(_LANE_ROOT))
    ap.add_argument("--frozen-digests",
                    default="evaluation/COVERAGE_FINDING_FALSIFICATION_HYPOTHESIS_V1.json")
    args = ap.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    product_root = Path(args.product_root).resolve()
    packet_dir = Path(args.packet_dir) if args.packet_dir else product_root / SERVED_PACKET
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = repo / out_path

    hyp_path = repo / args.frozen_digests
    if not hyp_path.is_file():
        print(f"::error::frozen hypothesis missing: {hyp_path}", file=sys.stderr)
        return 2
    frozen = json.loads(hyp_path.read_text(encoding="utf-8"))

    head = subprocess.run(["git", "-C", str(product_root), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    head_sha = head.stdout.strip() if head.returncode == 0 else None
    if head_sha != FROZEN_PRODUCT_HEAD:
        print(f"::error::accepted product head moved: {head_sha} != frozen "
              f"{FROZEN_PRODUCT_HEAD}; refusing (frozen hypothesis: the falsifier "
              f"decides the handoff on the exact served bytes it was frozen against)",
              file=sys.stderr)
        return 2

    bundles = sorted(packet_dir.glob("questions/*.bundle.json"))
    if not bundles:
        print(f"::error::no served bundles under {packet_dir}", file=sys.stderr)
        return 2

    record: dict = {
        "schema": "lex-coverage-finding-falsification/1",
        "run_id": args.run_id,
        "lane": "evaluation",
        "direction_version": 57,
        "generated_at": _utc_now(),
        "instrument": "evaluation/coverage_finding_falsification.py",
        "handoff_under_test": frozen["handoff_under_test"]["order_verbatim"],
        "accepted_product_head": head_sha,
        "accepted_product_head_matches_frozen": True,
        "served_packet_dir": str(packet_dir),
        "frozen_hypothesis": str(hyp_path.relative_to(repo)),
        "frozen_hypothesis_sha256": _sha256_file(hyp_path),
        "mapping_free_predicate": "expected_to_fire := len(measured.query_concepts_under_covered) > 0",
        "firing_rule": ("a finding fires when its own severity is 'warning' and every "
                        "under-covered term appears in that finding's own detail or "
                        "fields; no code name chosen by this lane is used"),
        "claim_ceiling": (
            "decides ONE thing: whether the ordered coverage disclosure is present on "
            "the exact served bytes of rebuilt-39027045675 under the accepted product "
            "code. It does not evaluate overall admission correctness, re-score any "
            "frozen label or geometry bar, move a threshold, or unblock the human gate."),
        "bundles": [],
    }

    digest_mismatch = []
    n_pass = n_fail = 0
    committed_vs_reexecuted_equal = 0
    for bundle_path in bundles:
        stem = bundle_path.name[: -len(".bundle.json")]
        admis = bundle_path.with_name(f"{stem}.admissibility.json")
        question = bundle_path.with_name(f"{stem}.question.json")
        if not admis.is_file():
            continue
        entry: dict = {"bundle": stem,
                       "bundle_path": str(bundle_path.relative_to(product_root)),
                       "bundle_sha256": _sha256_file(bundle_path),
                       "admissibility_path": str(admis.relative_to(product_root)),
                       "admissibility_sha256": _sha256_file(admis)}
        for key, expected_sha in ((f"{stem}.bundle.json", entry["bundle_sha256"]),
                                  (f"{stem}.admissibility.json", entry["admissibility_sha256"])):
            frozen_sha = (frozen["served_byte_digests_frozen"] or {}).get(key)
            if frozen_sha is None:
                entry.setdefault("served_digest_vs_frozen", {})[key] = {
                    "expected": None, "actual": expected_sha,
                    "match": None,
                    "note": "not enumerated in the frozen digest list; recorded, not assumed"}
                continue
            match = expected_sha == frozen_sha
            entry.setdefault("served_digest_vs_frozen", {})[key] = {
                "expected": frozen_sha, "actual": expected_sha, "match": match}
            if not match:
                digest_mismatch.append(f"{key}: {expected_sha} != {frozen_sha}")

        committed = json.loads(admis.read_text(encoding="utf-8"))
        before = summarise(committed, "committed served admission artifact")
        checks = committed.get("checks") or {}
        fresh, info = reexecute(product_root, bundle_path,
                                question if question.is_file() else None, checks)
        entry["reexecution"] = info
        if fresh is None:
            entry["after"] = None
            entry["outcome"] = "REEXECUTION_FAILED"
            n_fail += 1
            record["bundles"].append(entry)
            continue
        entry["after"] = summarise(fresh, "accepted product code re-executed on the served bytes")
        # REPAIR 39167917715 / audit CYCLE_39164900837 F6: the previous version
        # bound ``b, a = entry["after"], before`` and then wrote ``b`` into the
        # ``committed_*`` keys and ``a`` into the ``reexecuted_*`` keys, i.e.
        # the two labels were SWAPPED.  It was harmless only while the two
        # agreed 3/3; the first real divergence would have published a false
        # claim, which is exactly the case the block exists to expose.  The
        # binding is now explicit by name and cannot be inverted by a
        # one-character assignment.
        reexecuted = entry["after"]
        entry["comparison"] = {
            "committed_admissible": before["admissible"],
            "reexecuted_admissible": reexecuted["admissible"],
            "committed_warning_count": before["warning_count"],
            "reexecuted_warning_count": reexecuted["warning_count"],
            "committed_under_covered": before["measured_query_concepts_under_covered"],
            "reexecuted_under_covered": reexecuted["measured_query_concepts_under_covered"],
            "committed_finding_codes": [f["code"] for f in before["findings"]],
            "reexecuted_finding_codes": [f["code"] for f in reexecuted["findings"]],
            "identical_finding_code_and_severity_list": (
                [(f["code"], f["severity"]) for f in before["findings"]]
                == [(f["code"], f["severity"]) for f in reexecuted["findings"]]),
            "differences": sorted(set(
                [f"{c}:{s}" for c, s in [(f["code"], f["severity"]) for f in before["findings"]]]
                + [f"{c}:{s}" for c, s in [(f["code"], f["severity"]) for f in reexecuted["findings"]]])),
        }
        # The verdict is decided on the RE-EXECUTED product code run against
        # the served bytes (that is what "falsify-or-pass the fix on the exact
        # served bytes" means).  The committed artifact is published beside it
        # and a disagreement would be surfaced by
        # identical_finding_code_and_severity_list, never smoothed over.
        entry["outcome"] = ("PASS_FIRES_AS_ORDERED"
                            if reexecuted["expected_to_fire"]
                            == reexecuted["observed_fire_strict_warning_severity"]
                            else "FAIL_NOT_LANDED")
        n_pass += entry["outcome"].startswith("PASS")
        n_fail += entry["outcome"].startswith("FAIL")
        committed_vs_reexecuted_equal += int(
            entry["comparison"]["identical_finding_code_and_severity_list"])
        record["bundles"].append(entry)

    # S3 is the SYMMETRY rule and nothing else: a bundle whose measured
    # under-covered set is EMPTY must produce no coverage disclosure. A product
    # that emitted one unconditionally would satisfy S1 on the bundles that DO
    # have under-covered concepts while violating the rule that makes the
    # disclosure meaningful. No bundle is named here on purpose.
    symmetry_detail = [
        {"bundle": e["bundle"],
         "expected_to_fire": e["after"]["expected_to_fire"],
         "observed_fire": e["after"]["observed_fire_strict_warning_severity"],
         "silence_required": not e["after"]["expected_to_fire"]}
        for e in record["bundles"] if e.get("after")]
    symmetry = all((not d["silence_required"]) or (not d["observed_fire"])
                   for d in symmetry_detail)
    verdict = {
        "n_bundles": len(record["bundles"]),
        "n_pass": n_pass,
        "n_fail": n_fail,
        "committed_vs_reexecuted_identical": committed_vs_reexecuted_equal,
        "served_digest_mismatch": digest_mismatch,
        "S1_pass_all_bundles_match_predicate": n_fail == 0 and n_pass == len(record["bundles"]),
        "S2_outcome": ("HANDOFF_CONSUMED" if n_fail == 0 and n_pass
                       else "HANDOFF_STILL_OPEN"),
        "S3_symmetry_required": symmetry,
        "S3_symmetry_detail": symmetry_detail,
        "S5_pause_bar": ("Item 2 is NOT consumed, so this lane may not propose a pause; "
                         "continue_recommended stays true (audit CYCLE_39122016679 F3)"
                         if n_fail else
                         "Item 2 is consumed; a pause may only be proposed with a named "
                         "successor deliverable"),
        "failing_bundles": [e["bundle"] for e in record["bundles"]
                            if str(e.get("outcome", "")).startswith("FAIL")],
    }
    record["verdict"] = verdict
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(f"::notice::wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())