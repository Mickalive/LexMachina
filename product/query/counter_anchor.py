"""Product-owned adoption seam for ``frontier-counter-anchor-classifier`` (Outcome A).

Why this module exists
----------------------
The Frontier team ``frontier-counter-anchor-classifier`` (charter v1, team run
``38964146628``, independent audit ``CYCLE_38964146628_GATE.json`` gate=PASS /
``safe_to_integrate=true``, accept commit ``d236f5990``) built a *pure,
deterministic, dependency-free* counter-label decision function
``decide_label(row, frozen_rules, anchor_profile)``.  Its ``INTEGRATION_CONTRACT.json``
asks Core Product to:

    *"replace the label-decision step that writes counter_status /
    counter_evidence / counter_uncertainty with a call to
    ``decide_label(row, frozen_rules, anchor_profile)``"* and, on adoption, ship
    **abstain-and-disclose**: emitted labels keep their evidence-backed
    ``counter_status``; abstained rows stay visible as explicitly-marked
    unevidenced rows, and the product publishes **support-among-issued, the
    abstention count and the yield side by side**.

This module is that seam.  It vendors the component byte-identically (see
``product/vendored/frontier_counter_anchor_classifier/PROVENANCE.json``) and
loads the FROZEN rubric ``RULES_LABEL.json`` (sha256
``4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608``) after
proving its re-hash.  It never re-scores, re-tunes or re-derives a rubric.

Claim ceiling (binds every product artifact, copied verbatim from the accepted
``CLAIM_CEILING.json`` / ``ACCEPTED_frontier-served-packet-falsification``):

    This component measures and decides the SUPPORT OF COUNTER LABELS AS ISSUED
    under the frozen support rubric.  It NEVER asserts that any specific
    decision IS supporting, contrary or limiting.  Those remain the product's
    labels: the component confirms or abstains on them, it does not re-assign
    them.  The abstention count, support rate and yield are published side by
    side so the yield/support trade is auditable, not hidden.

Adopted default
---------------
The adoption decision recorded in ``state/product.json`` is **ADOPT** in
abstain-and-disclose mode.  The seam is therefore the default
(``LEXMACHINA_COUNTER_LABELS=anchor``); ``incumbent`` keeps the historical
label path available for comparison and tests, and ``off`` is a no-op.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_ROOT = REPO_ROOT / "product" / "vendored" / "frontier_counter_anchor_classifier"
FROZEN_RULES_PATH = REPO_ROOT / "product" / "frozen" / "RULES_LABEL.json"

#: Frozen rubric identity.  Any mismatch raises: a re-frozen rubric invalidates
#: the measurement, so the adapter refuses to run rather than silently re-score.
FROZEN_LABEL_RULES_SHA256 = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)

#: Env var selecting the label decision.  ``anchor`` is the adopted default.
LABEL_ENV = "LEXMACHINA_COUNTER_LABELS"
MODE_ANCHOR = "anchor"
MODE_INCUMBENT = "incumbent"
MODE_OFF = "off"

#: The product-visible marker for a row the component ABSTAINS on.  The row stays
#: on the map as an explicitly unevidenced row; it is never silently dropped.
ABSTAINED_STATUS = "abstained_unevidenced"

#: Statuses the frozen rubric SCORES (``rubric.scored_statuses``).  ``cited`` is
#: reported separately and never scored.
SCORED_STATUSES = (
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "limiting",
)
REPORTED_ONLY_STATUSES = ("cited",)

#: Acceptance provenance, for every artifact the seam writes.
ADOPTION = {
    "component": "frontier-counter-anchor-classifier",
    "charter_version": 1,
    "team_run_id": "38964146628",
    "audit_of_record": "results/audit/frontier/frontier-counter-anchor-classifier/CYCLE_38964146628_GATE.json",
    "audit_gate": "PASS",
    "safe_to_integrate": True,
    "accept_commit": "d236f5990",
    "accept_branch": "lab/frontier/frontier-counter-anchor-classifier",
    "mode": "abstain-and-disclose",
}

#: Forbidden construction patterns (copied verbatim from the accepted
#: ``CLAIM_CEILING.json`` / falsification snapshot).  No product artifact may
#: assert that a specific decision IS supporting/contrary/limiting.
FORBIDDEN_CONSTRUCTION_PATTERNS = [
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+not\s+(supporting|contrary|limiting)\b",
    r"\b[A-Za-z0-9_.\-]+\s+is\s+(a\s+)?(supporting|contrary|limiting)\s+(authority|decision|case)\b",
    r"\bwe\s+(classify|label|find)\s+[A-Za-z0-9_.\-]+\s+as\s+(supporting|contrary|limiting)\b",
    r"\basserts?\s+that\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
]

_RULES_CACHE: dict[str, Any] = {}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _import_component():
    """Import the vendored accepted package lazily (keeps startup light)."""
    if str(VENDORED_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDORED_ROOT))
    from frontier_counter_anchor_classifier.counter_anchor_classifier import (  # noqa: E402
        decide_label,
    )
    from frontier_counter_anchor_classifier.vendored.rules import load_rules  # noqa: E402

    return decide_label, load_rules


def load_frozen_rules(*, path: Path | None = None) -> tuple[Any, str]:
    """Load the frozen rubric, proving its re-hash before use.

    Returns ``(rules, sha256)``.  Raises ``ValueError`` on a digest mismatch so
    an edited rubric can never be scored silently.
    """
    p = Path(path) if path is not None else FROZEN_RULES_PATH
    payload = p.read_bytes()
    digest = sha256_bytes(payload)
    if digest != FROZEN_LABEL_RULES_SHA256:
        raise ValueError(
            f"frozen RULES_LABEL.json sha256 {digest} != accepted "
            f"{FROZEN_LABEL_RULES_SHA256}; an edited rubric invalidates the run"
        )
    _decide, load_rules = _import_component()
    rules = load_rules(str(p))
    if rules.sha256 != FROZEN_LABEL_RULES_SHA256:
        raise ValueError(
            f"component re-hash {rules.sha256} != accepted {FROZEN_LABEL_RULES_SHA256}"
        )
    return rules, digest


def resolve_anchor_profile(
    rules: Any,
    *,
    qid: str | None = None,
    query: str = "",
    language: str | None = None,
) -> dict[str, Any] | None:
    """The row's own question anchor profile from the frozen rules.

    Resolution order (deterministic):

    1. the bundle's own ``qid`` when it is a frozen anchor key;
    2. otherwise the frozen anchor whose ``expected_languages`` contains the
       query language AND whose DOMAIN anchors overlap the query tokens most.

    Returns ``None`` when no frozen profile can be named for the query; the
    caller then abstains from changing labels rather than inventing a profile.
    """
    anchors = getattr(rules, "anchors", {}) or {}
    if qid and qid in anchors:
        return anchors[qid]
    if not query:
        return None

    lang = (language or "").lower()
    q_tokens = set(_normalize_query(query))
    if not q_tokens:
        return None

    best_key: str | None = None
    best_overlap = 0
    for key in sorted(anchors):
        prof = anchors[key] or {}
        expected = [str(x).lower() for x in (prof.get("expected_languages") or [])]
        if expected and lang and lang not in expected:
            continue
        # DOMAIN anchors are a list of anchor strings; count those whose
        # normalized first token appears in the query.
        overlap = 0
        for anchor in (prof.get("domain") or []):
            toks = _normalize_query(str(anchor))
            if toks and any(t in q_tokens for t in toks):
                overlap += 1
        if overlap > best_overlap:
            best_overlap, best_key = overlap, key
    if best_key is None or best_overlap <= 0:
        return None
    return anchors[best_key]


def _normalize_query(text: str) -> list[str]:
    """Cheap, dependency-free token set for profile resolution only.

    This is NOT the frozen normalizer (that is the component's, and it is used
    for the actual decision).  It is only a deterministic similarity signal for
    choosing which frozen anchor profile a new query belongs to.
    """
    import unicodedata

    s = unicodedata.normalize("NFKD", str(text or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return sorted({t for t in re.split(r"[^a-z0-9]+", s) if len(t) >= 4})


def _mode(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    raw = str(env.get(LABEL_ENV) or MODE_ANCHOR).strip().lower()
    if raw in ("", "anchor", "adopt", "on"):
        return MODE_ANCHOR
    if raw in (MODE_INCUMBENT, "off", "none"):
        return raw
    raise ValueError(f"unknown {LABEL_ENV}={raw!r}; known: anchor, incumbent, off")


def apply_anchor_labels(
    bundle: dict,
    *,
    qid: str | None = None,
    mode: str | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Apply the adopted label decision to a bundle's scored counter rows.

    ``mode='anchor'`` (the adopted default): for every decision whose
    ``counter_status`` is a frozen scored status, call ``decide_label``.  An
    emitted label keeps its own evidence-backed ``counter_status``; an abstained
    row is kept on the map as ``counter_status='abstained_unevidenced'`` with
    the reason code and uncertainty, and its full decision is recorded for
    audit.  ``mode='incumbent'``/``'off'`` returns the bundle unchanged (with a
    provenance note) so the historical path stays available for comparison.

    The function never touches geometry, relations or any payload other than
    the counter-authority fields, so the rendered map never moves.
    """
    import copy

    out = copy.deepcopy(bundle)
    chosen = mode or _mode(env)
    if chosen != MODE_ANCHOR:
        out.setdefault("provenance", {}).setdefault("counter_anchor", {
            "component": ADOPTION["component"],
            "mode": chosen,
            "applied": False,
            "reason": "label decision left to the incumbent path",
        })
        return out

    rules, digest = load_frozen_rules()
    query = str(out.get("query") or "")
    profile = resolve_anchor_profile(rules, qid=qid, query=query)
    decide_label, _load = _import_component()

    prov: dict[str, Any] = {
        "component": ADOPTION["component"],
        "charter_version": ADOPTION["charter_version"],
        "team_run_id": ADOPTION["team_run_id"],
        "accept_commit": ADOPTION["accept_commit"],
        "mode": "abstain-and-disclose",
        "applied": True,
        "frozen_rules_sha256": digest,
        "qid": qid,
        "anchor_profile": None,
        "anchor_profile_source": None,
    }
    if profile is None:
        # No frozen profile can be named for this query.  Fail safe: change
        # nothing and say so; an invented profile would be worse than none.
        prov.update({
            "applied": False,
            "reason": "no_frozen_anchor_profile_for_query",
            "claim_ceiling": (
                "No label was re-decided: the query does not resolve to a frozen "
                "anchor profile, so the incumbent labels are unchanged and no "
                "support/abstention claim is made."
            ),
        })
        out.setdefault("provenance", {})["counter_anchor"] = prov
        return out

    prof_key = next((k for k, v in (getattr(rules, "anchors", {}) or {}).items()
                     if v is profile), None)
    prov["anchor_profile"] = prof_key
    prov["anchor_profile_source"] = "qid" if (qid and prof_key == qid) else "query_fallback"

    emitted = 0
    abstained = 0
    reason_counts: dict[str, int] = {}
    emitted_ids: list[str] = []
    abstained_ids: list[str] = []
    for d in out.get("decisions") or []:
        status = str(d.get("counter_status") or "")
        if status not in SCORED_STATUSES:
            continue
        dec = decide_label(d, rules, profile)
        record = dec.to_dict()
        d["counter_anchor_decision"] = record
        if dec.abstained:
            abstained += 1
            abstained_ids.append(str(d.get("decision_id") or ""))
            reason_counts[dec.reason_code] = reason_counts.get(dec.reason_code, 0) + 1
            # Keep the row VISIBLE as explicitly unevidenced.  Never drop it.
            d["counter_status"] = ABSTAINED_STATUS
            d["counter_uncertainty"] = dec.uncertainty
            d["counter_reason_code"] = dec.reason_code
            d["counter_anchor_label"] = "ABSTAIN"
            # An abstained row is NOT evidenced as a counter label, even if a
            # quote was proposed.  The quote stays visible for the amber ring,
            # but the verified flag must not claim verbatim support.
            d["counter_evidence_verified"] = False
        else:
            emitted += 1
            emitted_ids.append(str(d.get("decision_id") or ""))
            # Emitted labels keep their own evidence-backed status; the
            # component CONFIRMS, it never re-assigns a polarity.
            d["counter_anchor_label"] = dec.label
            d["counter_reason_code"] = "supported"
            d["counter_uncertainty"] = dec.uncertainty
            # Only a span this product verified byte-exactly against a named
            # text field may claim evidenced support.  The incumbent short
            # evidence strings are often not substrings of the raw body.
            d["counter_evidence_verified"] = bool(
                (d.get("counter_evidence_span") or {}).get("verified") is True
            )

    n_scored = emitted + abstained
    prov.update({
        "n_scored": n_scored,
        "n_emitted": emitted,
        "n_abstained": abstained,
        # Every emitted label is supported by construction (the emission gate is
        # exactly the frozen criteria i-v), so the support rate AMONG EMITTED
        # labels is 1.0; the YIELD is the emitted share of the scored population.
        "support_rate_among_emitted": 1.0 if emitted else 0.0,
        "yield": (emitted / n_scored if n_scored else 0.0),
        "abstention_reasons": dict(sorted(reason_counts.items())),
        "emitted_ids": emitted_ids,
        "abstained_ids": abstained_ids,
        "abstained_status_marker": ABSTAINED_STATUS,
        "claim_ceiling": (
            "Support rate, abstention count and yield are published together. The "
            "component CONFIRMS or ABSTAINS on the row's own proposed label; it "
            "never asserts that any specific decision IS supporting/contrary/"
            "limiting. An abstained row is unevidenced AS A COUNTER LABEL and stays "
            "visible on the map; it is not off-topic."
        ),
    })
    out.setdefault("provenance", {})["counter_anchor"] = prov
    return out


def counter_anchor_summary(bundle: dict) -> dict[str, Any]:
    """Aggregate the seam's own counters for owner-card / disclosure rendering.

    Prefers the counters the seam wrote into ``provenance.counter_anchor``
    (those are the authoritative pre-abstention counts).  Falls back to a
    direct count of the abstain marker so the summary still renders for a
    bundle the seam has not been applied to.
    """
    prov = (bundle.get("provenance") or {}).get("counter_anchor") or {}
    if prov.get("applied") and "n_scored" in prov:
        n_scored = int(prov.get("n_scored") or 0)
        n_emitted = int(prov.get("n_emitted") or 0)
        n_abstained = int(prov.get("n_abstained") or 0)
    else:
        decisions = bundle.get("decisions") or []
        n_scored = sum(1 for d in decisions
                       if str(d.get("counter_status") or "") in SCORED_STATUSES)
        n_emitted = sum(1 for d in decisions
                        if str(d.get("counter_status") or "") in SCORED_STATUSES
                        and d.get("counter_anchor_label") not in (None, "ABSTAIN"))
        n_abstained = sum(1 for d in decisions
                          if str(d.get("counter_status") or "") == ABSTAINED_STATUS)
    n_unevidenced = sum(1 for d in (bundle.get("decisions") or [])
                        if str(d.get("counter_status") or "") == ABSTAINED_STATUS)
    return {
        "component": ADOPTION["component"],
        "n_scored": n_scored,
        "n_emitted": n_emitted,
        "n_abstained": n_abstained,
        "n_unevidenced_rows": n_unevidenced,
        "support_rate_among_emitted": (1.0 if n_emitted else 0.0),
        "yield": (n_emitted / n_scored if n_scored else 0.0),
        "abstained_status_marker": ABSTAINED_STATUS,
    }


def adoption_record() -> dict[str, Any]:
    """The machine-readable adoption decision, for state/report artifacts."""
    return {
        "decision": "ADOPT",
        "mode": "abstain-and-disclose",
        **ADOPTION,
        "frozen_label_rules_sha256": FROZEN_LABEL_RULES_SHA256,
        "abstained_status_marker": ABSTAINED_STATUS,
        "env": LABEL_ENV,
        "default_mode": MODE_ANCHOR,
        "claim_ceiling": (
            "The component measures and decides the SUPPORT OF COUNTER LABELS AS "
            "ISSUED; it never asserts that any specific decision IS "
            "supporting/contrary/limiting. Support-among-issued, the abstention "
            "count and the yield are published side by side."
        ),
    }


def find_forbidden_constructions(text: str) -> list[str]:
    """Names of forbidden constructions in ``text`` (empty list when clean)."""
    hits: list[str] = []
    for pat in FORBIDDEN_CONSTRUCTION_PATTERNS:
        if re.search(pat, text or ""):
            hits.append(pat)
    return hits


__all__ = [
    "ABSTAINED_STATUS",
    "ADOPTION",
    "FROZEN_LABEL_RULES_SHA256",
    "FORBIDDEN_CONSTRUCTION_PATTERNS",
    "LABEL_ENV",
    "MODE_ANCHOR",
    "MODE_INCUMBENT",
    "MODE_OFF",
    "REPORTED_ONLY_STATUSES",
    "SCORED_STATUSES",
    "adoption_record",
    "apply_anchor_labels",
    "counter_anchor_summary",
    "find_forbidden_constructions",
    "load_frozen_rules",
    "resolve_anchor_profile",
]
