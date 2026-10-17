"""Product-owned adapter for the accepted counter-anchor-classifier component.

Why this module exists
----------------------
Factory direction v50, product obligation (4): *"integrate accepted Frontier
components in the cycle they are promoted and never wait for them."*

The Frontier component ``frontier-counter-anchor-classifier`` (charter v1,
team run 38964146628, independent audit ``CYCLE_38964146628_GATE.json`` PASS /
``safe_to_integrate=true``, accept commit ``d236f599``) delivered a
sentence-anchored counter-label decision function ``decide_label`` that
verifies the product's own proposed counter labels against the FROZEN
support rubric (``RULES_LABEL.json``, sha256
``4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608``).

The accepted measurement (``LABEL_HALF.json``) recorded that the served packet
38839347028 issued 65 counter labels of which only 5 were supported by their
own cited evidence under the frozen rubric (support rate 0.0769).  The
defect was mechanical: 38 rows were OFF-DOMAIN and 16 were UNBACKED with
empty cited evidence.  ``decide_label`` converts those rows into counted
abstentions instead of shipping unsupported labels.

Integration mode: abstain-and-disclose
---------------------------------------
The product's generative audit proposes counter labels (via the LLM
adversarial pass).  This adapter then runs ``decide_label`` on each proposed
label:

* **Emitted** (the row's own cited evidence passes every frozen criterion
  (i)-(v)): the label is served with ``counter_uncertainty=0.2`` and
  ``counter_evidence_verified=True``.
* **Abstained** (the cited evidence fails a frozen criterion): the row is
  kept visible with ``counter_status="abstained_unevidenced"``, the per-reason
  ``counter_uncertainty`` and ``counter_reason_code`` recorded, so the map
  renders it as unevidenced rather than as counter-authority.

Abstentions are COUNTED and published side by side with the support rate and
yield, so the yield/support trade is auditable, not hidden.

Fail-closed on unknown qid
--------------------------
The frozen rubric's ``question_anchors`` are authored for the five frozen
benchmark queries.  For a query whose text does not match any authored
anchor profile, the adapter abstains on EVERY proposed label with reason
``no_anchor_profile`` — the product does not invent anchor profiles for
queries it has not authored them for.  This is disclosed in provenance.

Claim ceiling
-------------
This adapter never asserts that a specific decision IS supporting, contrary
or limiting.  It confirms or abstains on the product's own proposed labels
under the frozen rubric.  The component's own claim ceiling (copied from
``CLAIM_CEILING.json``) applies verbatim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDORED_ROOT = REPO_ROOT / "product" / "vendored"

#: Frozen rubric hash.  The adapter refuses to run if the vendored copy does
#: not match, so an edited rubric can never silently change a verdict.
FROZEN_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

#: Path to the frozen rules (vendored byte-identical from the accepted cycle).
RULES_PATH = _VENDORED_ROOT / "counter_anchor_classifier" / "RULES_LABEL.json"

#: Marker for abstained rows.  The map renders these as unevidenced, not as
#: counter-authority.
ABSTAINED_STATUS = "abstained_unevidenced"

#: Reason code when the query matches no authored anchor profile.
NO_ANCHOR_REASON = "no_anchor_profile"

#: Counter statuses that carry a proposed legal label (not "none"/"cited").
_LABELED_STATUSES = frozenset({
    "candidate-contrary", "candidate-limiting", "candidate-distinguishing",
    "contrary", "contrary_or_exception", "limiting", "supporting",
})


def _load_frozen_rules() -> dict[str, Any]:
    """Load and verify the frozen RULES_LABEL.json.  Refuses on hash mismatch."""
    raw = RULES_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != FROZEN_RULES_SHA256:
        raise RuntimeError(
            f"frozen RULES_LABEL.json sha256 mismatch: {sha} != {FROZEN_RULES_SHA256}"
        )
    return json.loads(raw.decode("utf-8"))


def _import_decide_label():
    """Import the vendored accepted component lazily (keeps startup light)."""
    if str(_VENDORED_ROOT) not in sys.path:
        sys.path.insert(0, str(_VENDORED_ROOT))
    from counter_anchor_classifier import decide_label  # noqa: E402
    return decide_label


def resolve_qid(query: str, rules: dict[str, Any]) -> str | None:
    """Match the query text to an authored anchor profile.

    The frozen rubric's ``question_anchors`` are keyed by qid, each carrying
    the ``question`` text the anchors were authored for.  The product matches
    the incoming query against those texts (case-insensitive substring in
    either direction) so the five frozen benchmark queries resolve to their
    authored profiles.  Returns ``None`` when no profile matches — the
    adapter then abstains on every proposed label (fail closed).
    """
    q = (query or "").strip().lower()
    if not q:
        return None
    anchors = rules.get("question_anchors") or {}
    for qid, profile in anchors.items():
        authored = str(profile.get("question") or "").strip().lower()
        if not authored:
            continue
        if q in authored or authored in q:
            return qid
    return None


def apply_counter_anchor_decisions(
    bundle: dict,
    *,
    qid: str | None = None,
) -> dict:
    """Verify the bundle's proposed counter labels under the frozen rubric.

    For every decision whose ``counter_status`` carries a proposed legal
    label, run the accepted ``decide_label`` component:

    * emitted  -> keep the label, set ``counter_uncertainty=0.2``,
      ``counter_evidence_verified=True``;
    * abstained -> set ``counter_status="abstained_unevidenced"``, record
      ``counter_reason_code`` and the per-reason ``counter_uncertainty``.

    Rows with ``counter_status`` in ``{"none", "cited", ""}`` are untouched.
    The bundle's geometry, answer, provenance and every other field are
    preserved; only the counter-label fields are patched.

    Provenance records the qid, the frozen rules sha256, the emitted and
    abstained counts, the support rate among emitted labels, and the
    abstention reason histogram, so the yield/support trade is auditable.
    """
    out = bundle if isinstance(bundle, dict) else {}
    decisions = out.get("decisions") or []
    if not decisions:
        out.setdefault("provenance", {})["counter_anchor"] = {
            "component": "frontier-counter-anchor-classifier/1",
            "frozen_rules_sha256": FROZEN_RULES_SHA256,
            "qid": qid,
            "n_proposed": 0,
            "n_emitted": 0,
            "n_abstained": 0,
            "support_rate_emitted": None,
            "yield_rate": None,
            "abstention_reasons": {},
            "claim_ceiling": "no decisions to verify",
        }
        return out

    # No proposed labels -> nothing to verify.  Record the pass-through so
    # the provenance chain is complete.
    proposed = [
        d for d in decisions
        if str(d.get("counter_status") or "none") in _LABELED_STATUSES
    ]
    if not proposed:
        out.setdefault("provenance", {})["counter_anchor"] = {
            "component": "frontier-counter-anchor-classifier/1",
            "frozen_rules_sha256": FROZEN_RULES_SHA256,
            "qid": qid,
            "n_proposed": 0,
            "n_emitted": 0,
            "n_abstained": 0,
            "support_rate_emitted": None,
            "yield_rate": None,
            "abstention_reasons": {},
            "claim_ceiling": "no proposed counter labels to verify",
        }
        return out

    rules = _load_frozen_rules()
    decide_label = _import_decide_label()

    # Resolve the qid from the query text when the caller did not supply one.
    resolved_qid = qid
    if resolved_qid is None:
        resolved_qid = resolve_qid(str(out.get("query") or ""), rules)

    anchors = rules.get("question_anchors") or {}
    anchor_profile = anchors.get(resolved_qid) if resolved_qid else None

    n_emitted = 0
    n_abstained = 0
    abstention_reasons: dict[str, int] = {}

    for d in decisions:
        status = str(d.get("counter_status") or "none")
        if status not in _LABELED_STATUSES:
            continue

        if anchor_profile is None:
            # Fail closed: no authored anchor profile for this query, so no
            # label can be verified against the frozen rubric.  Abstain.
            d["counter_status"] = ABSTAINED_STATUS
            d["counter_reason_code"] = NO_ANCHOR_REASON
            d["counter_uncertainty"] = 1.0
            d["counter_evidence_verified"] = False
            n_abstained += 1
            abstention_reasons[NO_ANCHOR_REASON] = (
                abstention_reasons.get(NO_ANCHOR_REASON, 0) + 1
            )
            continue

        decision = decide_label(d, _FrozenRulesView(rules), anchor_profile)
        if decision.abstained:
            d["counter_status"] = ABSTAINED_STATUS
            d["counter_reason_code"] = decision.reason_code
            d["counter_uncertainty"] = decision.uncertainty
            d["counter_evidence_verified"] = False
            n_abstained += 1
            abstention_reasons[decision.reason_code] = (
                abstention_reasons.get(decision.reason_code, 0) + 1
            )
        else:
            # Emitted: the row's own cited evidence passes every frozen
            # criterion.  Keep the product's proposed label.
            d["counter_uncertainty"] = decision.uncertainty
            d["counter_evidence_verified"] = True
            d["counter_reason_code"] = "supported"
            n_emitted += 1

    n_proposed = n_emitted + n_abstained
    # Support rate among emitted labels: every emitted label passed all frozen
    # criteria (i)-(v) by construction, so this is 1.0 whenever n_emitted > 0.
    support_rate_emitted = 1.0 if n_emitted else None
    # Yield: the fraction of proposed labels that were emitted (served).
    yield_rate = round(n_emitted / n_proposed, 4) if n_proposed else None
    out.setdefault("provenance", {})["counter_anchor"] = {
        "component": "frontier-counter-anchor-classifier/1",
        "frozen_rules_sha256": FROZEN_RULES_SHA256,
        "qid": resolved_qid,
        "n_proposed": n_proposed,
        "n_emitted": n_emitted,
        "n_abstained": n_abstained,
        "support_rate_emitted": support_rate_emitted,
        "yield_rate": yield_rate,
        "abstention_reasons": dict(sorted(abstention_reasons.items())),
        "claim_ceiling": (
            "confirms or abstains on the product's own proposed counter labels "
            "under the frozen rubric; never asserts that a specific decision IS "
            "supporting, contrary or limiting"
        ),
    }
    return out


class _FrozenRulesView:
    """Adapt the frozen rules dict to the component's FrozenRules protocol.

    The vendored component expects a ``FrozenRules`` instance with
    ``normalizer``, ``lexicons``, ``marker_lexicon`` and ``stems``.  The
    frozen RULES_LABEL.json carries the same data in its ``normalization``
    and ``lexicons`` blocks.  This view exposes the dict as the protocol
    the component already consumes, without re-authoring any rubric data.
    """

    def __init__(self, rules: dict[str, Any]) -> None:
        from counter_anchor_classifier.vendored.normalize import Normalizer
        self._rules = rules
        self.normalizer = Normalizer(rules.get("normalization") or {})
        self.lexicons = rules.get("lexicons") or {}

    def marker_lexicon(self, language: str, variant: str = "primary") -> list[str]:
        """Return the frozen marker lexicon for a language.

        ``variant='primary'`` uses the product's own ADVERSARIAL_TERMS plus
        the frozen additions; ``variant='strict-no-product-vocabulary'``
        drops the product's terms (pre-declared sensitivity analysis).
        """
        entry = (
            (self._rules.get("lexicons") or {})
            .get("counter_intent_markers", {})
            .get(language)
            or {}
        )
        terms = list(entry.get("frozen_additions") or [])
        if variant != "strict-no-product-vocabulary":
            terms = list(entry.get("product_adversarial_terms") or []) + terms
        return terms


__all__ = [
    "ABSTAINED_STATUS",
    "FROZEN_RULES_SHA256",
    "NO_ANCHOR_REASON",
    "RULES_PATH",
    "apply_counter_anchor_decisions",
    "resolve_qid",
]
