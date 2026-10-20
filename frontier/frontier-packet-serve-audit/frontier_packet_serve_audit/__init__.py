"""frontier_packet_serve_audit: independent serve audit on the packet-of-record v3.

Charter v1, run 39355384602. Independently recomputes the frozen label and
geometry scoring on the packet-of-record v3 bytes (39319405429) as a
cross-check of Core Evaluation's published numbers, measures marginal
discovery on the same bytes, and emits ONE serve recommendation.

REUSE-FIRST: the label rubric and geometry primitives are vendored from the
accepted instruments (evaluation/frozen_bars/vendored/...). No threshold,
bar, rubric or verdict contract is re-derived.
"""

__version__ = "1.0.0"
