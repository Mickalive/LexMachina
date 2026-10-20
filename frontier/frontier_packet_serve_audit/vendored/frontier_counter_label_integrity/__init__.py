"""frontier-counter-label-integrity: pre-registered counter-label support harness.

Frozen-rubric harness.  Every judgement input (lexicons, criteria, thresholds,
question anchors, injection manifest, input inventory) is read from the frozen
RULES.json passed on the command line.  This package contains NO lexicon and NO
threshold of its own, so no code edit can change a verdict without changing the
frozen file whose sha256 every report embeds.

Read-only w.r.t. the accepted product mount.  Writes only inside the team's
namespace (results/frontier/, reports/frontier/, state/frontier/).
"""

__all__ = [
    "normalize",
    "rules",
    "extract",
    "rubric",
    "injection",
    "report",
    "cli",
]