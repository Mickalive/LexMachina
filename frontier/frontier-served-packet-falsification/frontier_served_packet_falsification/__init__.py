"""Frontier served-packet falsification: one verdict cycle, two frozen halves.

MEASURE, NEVER FIX. Reuses two accepted frozen RULES.json files byte-identically
and applies them to the exact gate packet a human owner session will render:
results/product/gate_packet/38839347028.

  * LABEL half: frozen counter-label support rubric
    (rules_sha256 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608)
  * GEOMETRY half: frozen map-semantics rule
    (rules_sha256 a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633)

No new threshold is frozen. No product file is touched. No placement/visibility
score is produced. Exactly one verdict cycle.
"""

__version__ = "1.0.0"

TEAM_ID = "frontier-served-packet-falsification"
CHARTER_VERSION = 1

RULES_LABEL_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
RULES_GEOMETRY_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"

# Served gate packet (the only population measured by this team).
GATE_PACKET = "results/product/gate_packet/38839347028"
BUNDLES = (
    "de-kapitalverletzung",
    "fr-bail-entretien",
    "it-responsabilita-medica",
)
BUNDLE_SHA256 = {
    "de-kapitalverletzung": "2441ff2b16722afcd22dca9ad39eafcbeb079b2dfc367d763fbe53fce1356f9c",
    "fr-bail-entretien": "6c5ea31d4b9af4abfa39e9f8025cfa3d34279ff1f04d0f643e571e27b23a2618",
    "it-responsabilita-medica": "76e7f7ad998f3878e7b08635663e2d594a7a77bdaeb33bcf5fa52d0af00b7aff",
}

# Accepted pre-repair baselines, quoted as baselines and NEVER as statements
# about the served packet.
BASELINE_LABEL_RUN = "38839354961"
BASELINE_LABEL_VERDICT = "LABEL_UNSOUND"
BASELINE_LABEL_SUPPORT_RATE_PRIMARY = 0.0
BASELINE_LABEL_SUPPORT_RATE_SECONDARY = 0.0
BASELINE_GEOMETRY_RUN = "38839351403"
BASELINE_GEOMETRY_PASS_COUNTS = {
    "de-kapitalverletzung": 5,
    "fr-bail-entretien": 5,
    "it-responsabilita-medica": 4,
}
BASELINE_GEOMETRY_LARGEST_SHARES = {
    "de-kapitalverletzung": 0.41044776119402987,
    "fr-bail-entretien": 0.5572519083969466,
    "it-responsabilita-medica": 0.3409090909090909,
}

WRITE_SCOPE = (
    "frontier/frontier-served-packet-falsification/",
    "tests/frontier/frontier-served-packet-falsification/",
    "reports/frontier/frontier-served-packet-falsification/",
    "results/frontier/frontier-served-packet-falsification/",
)
FORBIDDEN_WRITE_PREFIXES = (
    "product/",
    "evaluation/",
    "results/product/",
    "state/product.json",
    "state/blockers/",
    ".github/",
    "results/audit/",
)
