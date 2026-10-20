"""Public surface of the frontier-counter-label-emission drop-in module."""

from __future__ import annotations

from .attribution import (
    ALL_CAUSES,
    CAUSE_A,
    CAUSE_B,
    CAUSE_C,
    CAUSE_D,
    CAUSE_E,
    attribute_bundle,
    attribute_packet,
    sha256_file,
    verify_input_hashes,
)
from .classifier_bridge import (
    ABSTAINED_STATUS,
    CLASSIFIER_FILE_PINS,
    FROZEN_LABEL_RULES_SHA256,
    SCORED_STATUSES,
    run_classifier_on_bundle,
    verify_classifier_and_rubric,
)
from .determinism import run_determinism, run_non_vacuity
from .emission import MIN_EVIDENCE_CHARS, REPAIR_ID, promote_heuristic_proposals

__all__ = [
    "ABSTAINED_STATUS",
    "ALL_CAUSES",
    "CAUSE_A",
    "CAUSE_B",
    "CAUSE_C",
    "CAUSE_D",
    "CAUSE_E",
    "CLASSIFIER_FILE_PINS",
    "FROZEN_LABEL_RULES_SHA256",
    "MIN_EVIDENCE_CHARS",
    "REPAIR_ID",
    "SCORED_STATUSES",
    "attribute_bundle",
    "attribute_packet",
    "promote_heuristic_proposals",
    "run_classifier_on_bundle",
    "run_determinism",
    "run_non_vacuity",
    "sha256_file",
    "verify_classifier_and_rubric",
    "verify_input_hashes",
]
