"""Executable frozen-bar gates owned by Core Evaluation (factory direction v50).

Two CI-executable gates, NO new thresholds:

* label_gate    -- scores any query_result_bundle / gate packet with the FROZEN
  RULES_LABEL.json (sha 4457e971...) via the vendored frozen rubric, byte-
  identical to the accepted Frontier harness.
* geometry_gate -- scores any bundle with the FROZEN RULES_GEOMETRY.json
  (sha a7452748...) bars. stdlib-only engine; verdict-equality against the
  accepted GEOMETRY_HALF.json oracle is enforced at runtime.

GATE SEMANTICS (direction v50, stated to avoid a never-green loop): each gate
FAILS CI only on REGRESSION BELOW ITS RECOMPUTED INCUMBENT (label support
below 5/65; any geometry per-bundle criterion-count below de 6 / fr 5 / it 5).
The ABSOLUTE-BAR status (labels vs frozen 1.0; geometry vs all-11) is REPORTED
but NOT enforced as a build blocker.
"""
