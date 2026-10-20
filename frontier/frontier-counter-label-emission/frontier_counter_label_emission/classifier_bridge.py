"""Bridge to the ACCEPTED counter-anchor classifier (frontier-counter-anchor-classifier).

The classifier is imported READ-ONLY from the accepted product mount (or a
caller-supplied vendored root).  Its config and the frozen rubric are never
re-tuned, re-scored or edited here.  This bridge only:

1. re-hashes the classifier files and RULES_LABEL.json against the frozen pins;
2. loads the frozen rules through the classifier's own loader;
3. runs ``apply_anchor_labels`` (or the equivalent per-row ``decide_label``)
   on a bundle and returns the per-bundle emission record.

Every call re-verifies the hashes first; a mismatch raises and the run is
invalidated.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

#: Frozen rubric identity (charter + RULES.json).  Never re-derived.
FROZEN_LABEL_RULES_SHA256 = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)

#: The accepted classifier file pins (charter + RULES.json, accept d236f599).
CLASSIFIER_FILE_PINS: dict[str, str] = {
    "frontier_counter_anchor_classifier/__init__.py":
        "bd1d4c253b50bb624127e23fae8083ae40fd72fec76bf6fed451dcdfdb59a3d0",
    "frontier_counter_anchor_classifier/counter_anchor_classifier.py":
        "d256e2749f4aef838ba51accd99512bff7ad5f61372225cbf997d2b1110b66b9",
    "frontier_counter_anchor_classifier/run_head_to_head.py":
        "70a276e1b9c3782831ee4f4c1e86e5df0bbf2731e55abd6615a76887be87d1e4",
    "frontier_counter_anchor_classifier/vendored/__init__.py":
        "97c268544b6612925d6fa0552ca21141a7d0f347a65e600c1fc38a7b64d9e523",
    "frontier_counter_anchor_classifier/vendored/extract.py":
        "196969539269323812734e1ccdf7a84714e9c52ab5a09b032c0b6b2652c83eff",
    "frontier_counter_anchor_classifier/vendored/injection.py":
        "21bd06dbf388a9147b5ea783919b6899fc9f00edebed1be227669afcd45765ac",
    "frontier_counter_anchor_classifier/vendored/normalize.py":
        "a835e6dbaf919243f6cbda45ee233b04fe0ac020f8cb7ffcb96af7b98d60d486",
    "frontier_counter_anchor_classifier/vendored/rubric.py":
        "f43698da8b333d8c272eb3f064997a126caf47da202125520602d99a6cf01819",
    "frontier_counter_anchor_classifier/vendored/rules.py":
        "2a03d4634d492e2c8f8860abfb352cb8c266db32929388051627188e2a80756c",
}

#: The accepted product's SCORED_STATUSES (counter_anchor.py, never redefined).
SCORED_STATUSES = (
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "limiting",
)

#: The product-visible marker for an abstained row (counter_anchor.py).
ABSTAINED_STATUS = "abstained_unevidenced"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _default_classifier_root() -> Path:
    """Locate the accepted classifier on a mounted or in-repo layout."""
    env = os.environ.get("LEXMACHINA_CLASSIFIER_ROOT")
    if env:
        return Path(env)
    candidates = [
        Path("/tmp/lex_accepted/core/product/product/vendored/frontier_counter_anchor_classifier"),
        Path(__file__).resolve().parents[3].parent
        / "product" / "vendored" / "frontier_counter_anchor_classifier",
    ]
    for c in candidates:
        if (c / "frontier_counter_anchor_classifier" / "counter_anchor_classifier.py").is_file():
            return c
    raise FileNotFoundError(
        "accepted classifier not found; set LEXMACHINA_CLASSIFIER_ROOT"
    )


def _default_rules_path() -> Path:
    env = os.environ.get("LEXMACHINA_FROZEN_RULES")
    if env:
        return Path(env)
    candidates = [
        Path("/tmp/lex_accepted/core/product/product/frozen/RULES_LABEL.json"),
        Path(__file__).resolve().parents[3].parent / "product" / "frozen" / "RULES_LABEL.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "frozen RULES_LABEL.json not found; set LEXMACHINA_FROZEN_RULES"
    )


def verify_classifier_and_rubric(
    *,
    classifier_root: str | Path | None = None,
    rules_path: str | Path | None = None,
) -> dict[str, Any]:
    """Re-hash the accepted classifier files and the frozen rubric.

    Returns a record with ``ok`` and every actual digest.  Raises on any
    mismatch so an edited artifact can never be scored silently.
    """
    root = Path(classifier_root) if classifier_root else _default_classifier_root()
    rules = Path(rules_path) if rules_path else _default_rules_path()

    file_checks: list[dict[str, Any]] = []
    all_ok = True
    for rel, want in sorted(CLASSIFIER_FILE_PINS.items()):
        p = root / rel
        if not p.is_file():
            file_checks.append({"relpath": rel, "status": "missing", "expected": want})
            all_ok = False
            continue
        got = sha256_file(p)
        ok = got == want
        all_ok = all_ok and ok
        file_checks.append({
            "relpath": rel,
            "status": "ok" if ok else "mismatch",
            "expected": want,
            "actual": got,
        })

    rules_ok = False
    rules_actual = None
    if rules.is_file():
        rules_actual = sha256_file(rules)
        rules_ok = rules_actual == FROZEN_LABEL_RULES_SHA256
        all_ok = all_ok and rules_ok
    else:
        all_ok = False

    record = {
        "ok": all_ok,
        "classifier_root": str(root),
        "rules_path": str(rules),
        "n_classifier_files": len(CLASSIFIER_FILE_PINS),
        "classifier_files": file_checks,
        "frozen_rules_sha256_expected": FROZEN_LABEL_RULES_SHA256,
        "frozen_rules_sha256_actual": rules_actual,
        "frozen_rules_ok": rules_ok,
    }
    if not all_ok:
        raise ValueError(
            "classifier/rubric hash mismatch; run invalidated: "
            + json.dumps({k: record[k] for k in ("frozen_rules_ok",)}, sort_keys=True)
        )
    return record


def _import_component(root: Path):
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from frontier_counter_anchor_classifier.counter_anchor_classifier import (  # type: ignore
        decide_label,
    )
    from frontier_counter_anchor_classifier.vendored.rules import load_rules  # type: ignore
    return decide_label, load_rules


def run_classifier_on_bundle(
    bundle: dict,
    *,
    qid: str | None = None,
    classifier_root: str | Path | None = None,
    rules_path: str | Path | None = None,
    hash_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the accepted classifier on a bundle and return the emission record.

    This is a READ-ONLY decision pass: it never writes into the caller's
    bundle.  It mirrors ``product/query/counter_anchor.py`` semantics exactly
    (score only rows whose counter_status is in SCORED_STATUSES; an abstained
    row is counted with its reason; an emitted label keeps its own status).
    """
    ver = hash_verification or verify_classifier_and_rubric(
        classifier_root=classifier_root, rules_path=rules_path,
    )
    root = Path(ver["classifier_root"])
    rules_file = Path(ver["rules_path"])
    decide_label, load_rules = _import_component(root)
    rules = load_rules(str(rules_file))
    if rules.sha256 != FROZEN_LABEL_RULES_SHA256:
        raise ValueError(f"component re-hash {rules.sha256} != accepted")

    # Resolve the anchor profile the same way the accepted product seam does.
    anchors = getattr(rules, "anchors", {}) or {}
    profile = None
    profile_key = None
    if qid and qid in anchors:
        profile = anchors[qid]
        profile_key = qid
    else:
        # Deterministic fallback: first frozen anchor whose expected_languages
        # contains the bundle language, else first sorted key.
        lang = str(bundle.get("language") or "").lower()
        for key in sorted(anchors):
            expected = [str(x).lower() for x in (anchors[key] or {}).get("expected_languages") or []]
            if lang and lang in expected:
                profile, profile_key = anchors[key], key
                break
        if profile is None and anchors:
            profile_key = sorted(anchors)[0]
            profile = anchors[profile_key]

    decisions = bundle.get("decisions") or []
    n_proposed = 0
    emitted: list[str] = []
    abstained: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    for d in sorted(decisions, key=lambda r: str(r.get("decision_id") or "")):
        status = str(d.get("counter_status") or "")
        if status not in SCORED_STATUSES:
            continue
        n_proposed += 1
        if profile is None:
            # Fail safe, exactly like the accepted product seam: no frozen
            # profile means no re-decision; count as abstention with reason.
            abstained.append({
                "decision_id": str(d.get("decision_id") or ""),
                "reason_code": "no_frozen_anchor_profile_for_query",
            })
            reason_counts["no_frozen_anchor_profile_for_query"] = (
                reason_counts.get("no_frozen_anchor_profile_for_query", 0) + 1
            )
            continue
        dec = decide_label(d, rules, profile)
        if dec.abstained:
            abstained.append({
                "decision_id": str(d.get("decision_id") or ""),
                "reason_code": dec.reason_code,
                "uncertainty": dec.uncertainty,
            })
            reason_counts[dec.reason_code] = reason_counts.get(dec.reason_code, 0) + 1
        else:
            emitted.append(str(d.get("decision_id") or ""))

    n_scored = len(emitted) + len(abstained)
    n_emitted = len(emitted)
    n_abstained = len(abstained)
    n_total_rows = len(decisions)
    return {
        "qid": qid,
        "anchor_profile": profile_key,
        "n_proposed": n_proposed,
        "n_scored": n_scored,
        "n_emitted": n_emitted,
        "n_abstained": n_abstained,
        "n_unevidenced_rows": n_abstained,
        "support_rate_among_issued": (1.0 if n_emitted else 0.0),
        "abstention_count": n_abstained,
        "yield_over_population": (n_emitted / n_total_rows if n_total_rows else 0.0),
        "n_total_rows": n_total_rows,
        "emitted_ids": sorted(emitted),
        "abstained": sorted(abstained, key=lambda r: r["decision_id"]),
        "abstention_reasons": dict(sorted(reason_counts.items())),
        "abstained_status_marker": ABSTAINED_STATUS,
        "classifier_config_sha256": {
            rel: pin for rel, pin in sorted(CLASSIFIER_FILE_PINS.items())
        },
        "frozen_rules_sha256": FROZEN_LABEL_RULES_SHA256,
        "hash_verification_ok": bool(ver.get("ok")),
        "claim_ceiling": (
            "The accepted classifier CONFIRMS or ABSTAINS on the row's own "
            "proposed label under the frozen rubric.  Support-among-issued, "
            "the abstention count and the yield are published together.  "
            "This record never asserts that any decision IS supporting/"
            "contrary/limiting."
        ),
    }


__all__ = [
    "ABSTAINED_STATUS",
    "CLASSIFIER_FILE_PINS",
    "FROZEN_LABEL_RULES_SHA256",
    "SCORED_STATUSES",
    "run_classifier_on_bundle",
    "sha256_file",
    "verify_classifier_and_rubric",
]
