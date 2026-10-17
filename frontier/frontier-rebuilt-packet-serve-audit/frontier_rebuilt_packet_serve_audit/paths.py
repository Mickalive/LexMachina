"""Path resolution + vendored-instrument bootstrap for this team's harness."""
from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
TEAM_ROOT = PACKAGE_ROOT.parent  # frontier/frontier-rebuilt-packet-serve-audit
REPO_ROOT = TEAM_ROOT.parent.parent
VENDORED_ACCEPTED = TEAM_ROOT / "vendored_accepted"
VENDORED_BARS = VENDORED_ACCEPTED / "evaluation" / "frozen_bars"

# Where the rebuilt / old packets are mounted for this workflow. The rebuilt
# packet is read from the product cycle snapshot the charter names when the
# product audit is not accepted; both locations are acceptable as long as the
# raw packet.json sha256 matches the frozen pin.
DEFAULT_PACKET_CANDIDATES = (
    Path("/tmp/lex_work/results/product/gate_packet/rebuilt-39027045675"),
    REPO_ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675",
    Path("/tmp/lex_accepted/core/product/results/product/gate_packet/rebuilt-39027045675"),
)
DEFAULT_OLD_PACKET_CANDIDATES = (
    Path("/tmp/lex_accepted/core/product/results/product/gate_packet/38839347028"),
    REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028",
)

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


def bootstrap_vendored_instruments() -> None:
    """Put the vendored accepted evaluation package on sys.path exactly once.

    The accepted instruments do ``sys.path.insert(0, _BAR_DIR.parent.parent)``
    and import ``evaluation.frozen_bars.vendored...``; our vendored tree is
    laid out so that import resolves against the byte-identical copies under
    this team's namespace. The real repository ``evaluation/`` package is
    deliberately NOT used: this team must not write or shadow it, and the
    vendored copies are re-hashed before any scoring.
    """
    root = str(VENDORED_ACCEPTED)
    if root not in sys.path:
        sys.path.insert(0, root)
    # Ensure the team package itself is importable when run as a module.
    team_parent = str(TEAM_ROOT.parent)
    if team_parent not in sys.path:
        sys.path.insert(0, team_parent)


def resolve_packet(explicit: str | None = None, candidates=DEFAULT_PACKET_CANDIDATES) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_dir():
            raise FileNotFoundError(f"packet dir not found: {p}")
        return p
    for c in candidates:
        if (c / "packet.json").is_file():
            return c
    raise FileNotFoundError(
        "packet dir not found in candidates: "
        + ", ".join(str(c) for c in candidates)
    )
