"""Frontier team ``frontier-adversarial-discoverability`` — charter v1.

Pre-registered measurement harness.  Every metric, population and threshold
implemented here is frozen in ``results/frontier/frontier-adversarial-discoverability/RULES.json``
(commit 1d50633, 2026-10-15T19:21:04Z) BEFORE any measured artifact existed.

This package is read-only with respect to every other lane.  It reads the
accepted ``lab/product`` mount and writes only under this team's namespace.
"""

__version__ = "1.0.0"
RULES_VERSION = "fad-rules/1"
TEAM_ID = "frontier-adversarial-discoverability"
CHARTER_VERSION = 1

#: Frozen constant used by every deterministic corruption (RULES.json
#: ``non_vacuity.determinism``).  No randomness source is ever consulted.
CORRUPTION_SEED = 20261015

#: ``counter_status`` values that count as counter-authority (RULES.json
#: ``populations.COUNTER_VALUES``).  Charter-literal; excludes ``cited``.
COUNTER_VALUES = (
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "limiting",
)

#: Exact placeholder string the product emits when a counter row's only
#: "evidence" is that the answer cited it (RULES.json ``metrics.e_evidence_quality``).
PLACEHOLDER_EVIDENCE = "cited in generated answer"
