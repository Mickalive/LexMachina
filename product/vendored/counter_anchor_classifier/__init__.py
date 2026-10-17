"""frontier-counter-anchor-classifier: sentence-anchored counter-label decision.

Charter v1.  Builds the drop-in label decision component and scores it
head-to-head against the incumbent on the served packet 38839347028 under the
FROZEN rubric RULES_LABEL.json (sha256
4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608).

The frozen-rubric scoring modules are vendored byte-identically from the
accepted cycle branch (see ``vendored/``); the candidate decision function is
the new build (see ``counter_anchor_classifier.py``).
"""

from .counter_anchor_classifier import (
    LABEL_ABSTAIN,
    LABEL_CONTRARY,
    LABEL_LIMITING,
    LABEL_SUPPORTING,
    LabelDecision,
    decide_label,
)

__all__ = [
    "LABEL_ABSTAIN",
    "LABEL_CONTRARY",
    "LABEL_LIMITING",
    "LABEL_SUPPORTING",
    "LabelDecision",
    "decide_label",
]
