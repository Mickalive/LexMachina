"""Contract-guided generation: the completeness contract is fed to the model *before* it writes.

Why this exists
---------------
Three consecutive live ``petty-theft-dismissal`` legs
(``results/product/reality_check/petty-theft-dismissal_live_20261016T{184421,193340,194228}Z.json``)
failed the frozen truth gate with the same message:

    answer must state that low value is not itself decisive/exclusive

The model was not legally wrong.  Its 19:42Z synthesis opened with

    « Un vol de faible valeur commis par un employé ne justifie pas
      automatiquement un licenciement immédiat au sens de l'art. 337 CO ;
      la réponse dépend des circonstances concrètes. »

— which is the correct nuance in paraphrase.  It is nevertheless incomplete
for a jurist, because the paraphrase never says what the condition *is* (low
value is neither an automatic bar nor an automatic justification), and it is
invisible to the frozen gate, whose positive patterns require the
non-decisiveness phrasing and whose negative pattern
(``ne justifie …pas``) would independently reject the paraphrase.

Two levers were already in the product and neither could close this:

* ``answer_contract.ensure_coverage`` only ever appends a **verbatim sentence
  that exists in the bundle**.  A scan of every cached OpenCaseLaw envelope
  (1116 files under ``results/product/query_cache``) finds **zero** sentences
  matching the element's own patterns, so the fill correctly records
  ``no_retrieved_source_states_it`` and appends nothing.
* The generation prompt is owned by the accepted Frontier component and lists
  topic-generic instructions («distinguish the cure period from the notice
  period»); it does not know which material conditions *this* contract
  requires for *this* query.

So the fix is the missing seam, not a gate change: the product already knows,
before the model writes, which material conditions the answer must contain —
``answer_contract.match_contract`` returns them as labelled elements.  This
module hands those labels to the generation prompt as explicit drafting
instructions.  Nothing is invented: the labels are product-shipped legal
expertise, every proposition the model states still has to be supported by a
retrieved source, and the citation-validation boundary is untouched.  The
deterministic ``ensure_coverage`` fill and the frozen truth gate both stay in
place as independent checks, so a model that ignores the block is caught the
same way as before.

Design
------
``ContractGuidedProvider`` subclasses the Frontier ``Provider`` and overrides
only ``build_prompt``: the entire existing prompt (source selection, citation
rules, language rules, verbatim-quoting rule) is preserved and a bounded
"material conditions" block is appended.  When the query matches no contract
the block is empty and the prompt is byte-identical to the parent's, so the
three legs that already pass cannot regress through a changed prompt.

The block states *what* must be said, never *how the gate spells it*: no gate
regex, normaliser or test fixture is copied in here.  A future gate
strengthening therefore does not silently re-author this prompt.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from .answer_contract import match_contract

#: The accepted Frontier generative-audit component, consumed read-only.
GENAUDIT_ROOT = Path(__file__).resolve().parents[2] / "frontier" / "frontier-generative-audit"

#: Prompt block marker, so tests and auditors can find the intervention.
BLOCK_MARKER = "MATERIAL_CONDITIONS_BLOCK_V1"

#: Longest block: keeps the instruction budget inside the existing prompt.
MAX_CONDITIONS = 4


def material_conditions(query: str) -> list[dict[str, Any]]:
    """The labelled material conditions ``query``'s contract requires.

    Empty list when no contract matches — the caller then leaves the prompt
    untouched rather than inventing a requirement.
    """
    contract = match_contract(query)
    if not contract:
        return []
    return [
        {"topic": contract["topic"], "id": e["id"], "label": e["label"]}
        for e in contract.get("elements", [])[:MAX_CONDITIONS]
    ]


def condition_lines(query: str) -> list[str]:
    """Rendered instruction lines for the prompt (empty when no contract)."""
    conditions = material_conditions(query)
    if not conditions:
        return []
    lines = [
        "",
        f"{BLOCK_MARKER}:",
        "  The research question below has registered material conditions. State "
        "each one EXPLICITLY, in the query language, as a short declarative "
        "sentence that says what the condition is — a reader must be able to "
        "quote the sentence on its own. Do not merely allude to a condition by "
        "paraphrase, and do not bury it inside a description of the facts.",
        "  A condition is STATED only when the sentence asserts the condition "
        "itself (for example whether a factor is or is not decisive for the "
        "outcome), not when the sentence says the answer 'depends on the "
        "circumstances'.",
    ]
    for condition in conditions:
        lines.append(f"    - [{condition['id']}] {condition['label']}")
    lines.append(
        "  Each stated condition must rest on a retrieved source and carry that "
        "source's [DECISION_ID]; if no retrieved source supports a condition, "
        "say so rather than asserting it."
    )
    return lines


def build_provider(
    query: str,
    *,
    model: Optional[str] = None,
    fixture_mode: bool = False,
    fixture_answer: Optional[str] = None,
    fixture_cited_ids: Optional[list] = None,
    timeout: float = 120.0,
):
    """Provider for ``run_generative_audit``, contract-guided when a contract matches.

    Mirrors ``generative_audit.integration_contract.run_generative_audit``'s
    own Provider construction so that passing a provider changes *only* the
    prompt block and nothing else (same model ordering, same runner, same
    timeout, same fixture behaviour).
    """
    if GENAUDIT_ROOT.is_dir() and str(GENAUDIT_ROOT) not in sys.path:
        sys.path.insert(0, str(GENAUDIT_ROOT))
    from generative_audit.provider import Provider  # local import: sys.path set above

    extra = condition_lines(query)
    if not extra:
        return Provider(
            model=model,
            fixture_mode=fixture_mode,
            fixture_answer=fixture_answer,
            fixture_cited_ids=fixture_cited_ids,
            timeout=timeout,
        )

    class ContractGuidedProvider(Provider):
        """Parent prompt + the query's registered material conditions."""

        def build_prompt(self, bundle) -> str:
            base = super().build_prompt(bundle)
            # Guard against a re-entrancy surprise: the block is appended once.
            if BLOCK_MARKER in base:
                return base
            return base + "\n".join(["", *extra])

    return ContractGuidedProvider(
        model=model,
        fixture_mode=fixture_mode,
        fixture_answer=fixture_answer,
        fixture_cited_ids=fixture_cited_ids,
        timeout=timeout,
    )


__all__ = [
    "BLOCK_MARKER",
    "MAX_CONDITIONS",
    "build_provider",
    "condition_lines",
    "material_conditions",
]
