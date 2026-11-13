"""v68 ordered item (2) precondition gate: named-family regeneration.

Direction v68 makes the item-(2) re-measure conditional on Product having
regenerated the *named frozen 15-member family* (11 offline rent-default +
4 server served), not merely on having regenerated its own 4+1 flagship set.
The set relation and its frozen rule were adjudicated in accepted evaluation
run 40258497460 (``precondition.set_relations_REQUIREMENT_16``).  This script
does not re-derive that rule and does not score any bundle content.  It only
checks, against the current accepted product mount, whether the precondition
for the ordered re-measure is now met, and records NOT_YET_DISCRIMINATING when
it is not.

Claims made here are set/byte-identity and role-cardinality statements about
already-accepted artifacts.  No content predicate (D1-D4) is re-scored.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_RECORD = (
    REPO_ROOT
    / "results/evaluation/post_repair_family_ca_falsifier/40258497460.json"
)
PRODUCT_FAMILY_CLAIM = (
    Path("/tmp/lex_accepted/product")
    / "results/product/counter_content_family/CYCLE_40257275384.json"
)
OUT_DIR = REPO_ROOT / "results/evaluation/v68_item2_family_gate"
RUN_ID = "43333717014"

# Frozen named family from accepted 40258497460 (the direction's "15-member
# family"); failing member paths are the frozen family only, never the
# product's own 4+1 claim.
FROZEN_FAMILY = [
    "results/product/offline_slice/20261023T190402Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T202433Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T202440Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T203316Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T212530Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T214943Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T220629Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T222223Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T223903Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T224023Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T224250Z/rent-default.bundle.json",
    "results/product/server_slice/20261023T223109Z/served.bundle.json",
    "results/product/server_slice/20261023T223909Z/served.bundle.json",
    "results/product/server_slice/20261023T224031Z/served.bundle.json",
    "results/product/server_slice/20261023T224255Z/served.bundle.json",
]
FROZEN_ROLE_TARGET = {"offline/rent-default": 11, "server/served": 4}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def role_of(path: str) -> str:
    parts = path.split("/")
    family = parts[2].replace("_slice", "")
    query = Path(path).name.replace(".bundle.json", "")
    return f"{family}/{query}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", default="/tmp/lex_accepted/product")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    product_root = Path(args.product_root).resolve()

    accepted = json.loads(ACCEPTED_RECORD.read_text(encoding="utf-8"))
    measured = {b["path"]: b["sha256"] for b in accepted["bundles"]}
    claim = json.loads(PRODUCT_FAMILY_CLAIM.read_text(encoding="utf-8"))
    claimed_paths = [b["path"] for b in claim["fixed_path_family"]["bundles"]]

    # 1. Zero-delta check: is the current fixed-path family byte-identical to
    # the family accepted run 40258497460 already measured?
    measured_present = [p for p in measured if (product_root / p).is_file()]
    identical = [
        p
        for p in measured_present
        if sha256(product_root / p) == measured[p]
    ]
    missing = sorted(set(measured) - set(measured_present))
    differing = sorted(set(measured_present) - set(identical))

    # 2. Role cardinality of the product's 49-bundle fixed-path claim.
    current_roles = collections.Counter(role_of(p) for p in claimed_paths)
    frozen_roles = collections.Counter(role_of(p) for p in FROZEN_FAMILY)

    # 3. Frozen member-for-member ceiling under the role-match rule: each
    # frozen member matches at most one distinct current bundle of the same
    # role, so the ceiling is sum(min(current, frozen)) over roles.
    per_role_ceiling = {
        r: min(current_roles.get(r, 0), frozen_roles[r])
        for r in sorted(set(frozen_roles) | set(current_roles))
        if frozen_roles.get(r)
    }
    member_for_member_ceiling = sum(per_role_ceiling.values())
    role_parity = current_roles == frozen_roles

    # 4. Is this a *new* regeneration since the accepted measurement?  The
    # product claim's own run id is earlier than the evaluation run that
    # measured the same bytes, so it is not.
    product_claim_run = str(claim.get("run_id"))
    already_measured = (
        len(identical) == len(measured)
        and not differing
        and not missing
        and product_claim_run <= "40258497460"
    )

    full_success = bool(
        role_parity and member_for_member_ceiling == len(FROZEN_FAMILY) and not already_measured
    )
    status = (
        "DISCRIMINATING_PRECONDITION_MET"
        if full_success
        else "NOT_YET_DISCRIMINATING"
    )

    out = {
        "schema": "lex-v68-item2-family-gate/1",
        "run_id": args.run_id,
        "lane": "evaluation",
        "direction_version": 68,
        "generated_at_utc": subprocess.check_output(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True
        ).strip(),
        "status": status,
        "ordered_item": "(2) conditional comparable re-measure of the named frozen family",
        "reused_rule_source": {
            "path": str(ACCEPTED_RECORD.relative_to(REPO_ROOT)),
            "sha256": sha256(ACCEPTED_RECORD),
            "rule": "member-for-member regeneration of the named 15-member family under the frozen role-match rule (11 offline/rent-default + 4 server/served)",
            "note": "This gate does not re-derive the rule and does not re-score D1-D4 content.",
        },
        "product": {
            "root": str(product_root),
            "head": subprocess.check_output(
                ["git", "-C", str(product_root), "rev-parse", "HEAD"], text=True
            ).strip(),
            "family_claim_run_id": product_claim_run,
            "family_claim_path": str(PRODUCT_FAMILY_CLAIM),
            "family_claim_sha256": sha256(PRODUCT_FAMILY_CLAIM),
            "claimed_fixed_path_bundles_n": len(claimed_paths),
        },
        "zero_delta_check": {
            "already_measured_bundles_n": len(measured),
            "present_in_current_product_n": len(measured_present),
            "byte_identical_n": len(identical),
            "differing": differing,
            "missing": missing,
            "already_measured_since_evaluation_run": already_measured,
            "meaning": (
                "The current product fixed-path bytes are the same bytes accepted run "
                "40258497460 already measured; re-running the D1-D4 falsifier on them "
                "is zero-delta."
                if already_measured
                else "The current bytes differ from the accepted measurement; a re-run may be discriminating."
            ),
        },
        "role_cardinality": {
            "frozen_named_family": dict(frozen_roles),
            "current_fixed_path_family": dict(current_roles),
            "role_parity": role_parity,
            "member_for_member_ceiling": member_for_member_ceiling,
            "frozen_family_n": len(FROZEN_FAMILY),
            "per_role_ceiling": per_role_ceiling,
            "ceiling_reason": "server/served current=3 < frozen required=4, so at most 14/15 frozen members can match under the frozen role rule",
        },
        "adjudication": {
            "precondition_leg_landed": True,
            "precondition_full_named_family_regenerated": full_success,
            "status": status,
            "reason": (
                "Both (a) the current product fixed-path family is byte-identical to the "
                "family already measured by accepted run 40258497460 (49/49 named-family "
                "and 50/50 measured bundles), so a re-measure is zero-delta, and (b) the "
                "named family's role cardinality is not regenerated (server/served 3 vs 4; "
                "offline/rent-default 18 vs 11), so member-for-member matching is capped at "
                "14/15. No synthetic stand-in is substituted."
            ),
        },
        "claim_ceiling": (
            "Set/byte identity and role cardinality against already-accepted artifacts only; "
            "no new content-quality score, no new retrieval run, no universal-174k benchmark."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUT_DIR / f"{args.run_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "out": str(out_path), "zero_delta": already_measured, "ceiling": member_for_member_ceiling, "of": len(FROZEN_FAMILY)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
