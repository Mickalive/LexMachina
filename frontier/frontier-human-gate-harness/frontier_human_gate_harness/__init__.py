"""frontier-human-gate-harness: owner test harness for the Master Prompt human product gate.

Charter v1 (team frontier-human-gate-harness) delivers four things, nothing else:

1. a conventional ranked-list baseline rendered from the SAME ``query_result_bundle``
   the map is rendered from (``baseline_view``);
2. a list<->map switch over the identical already-loaded bundle (``static/lex_gate_switch.js``);
3. the four Master Prompt human-gate questions as a short FR/DE owner card (``owner_card``);
4. a session capture writing a structured, claim-bearing record to disk (``capture``).

This team owns no ``product/`` file. Integration is product's job and is specified
in ``frontier/frontier-human-gate-harness/INTEGRATION_CONTRACT.md``.
"""

__all__ = [
    "__version__",
    "TEAM_ID",
    "CHARTER_VERSION",
]

__version__ = "1.0.0"
TEAM_ID = "frontier-human-gate-harness"
CHARTER_VERSION = 1
