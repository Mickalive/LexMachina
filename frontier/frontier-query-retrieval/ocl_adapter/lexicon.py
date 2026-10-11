"""Multilingual legal-term lexicon (DE/FR/IT).

REUSE-FIRST provenance: the synonym table below is copied verbatim from the
ACCEPTED product lane module ``product/query/retrieval.py`` (mount
``/tmp/lex_accepted/core/product``) so that query expansion behaves
identically once the adapter is absorbed by the product lane.

Two rules are load-bearing for charter acceptance (6):

1. Expansion terms come **only** from this fixed lexicon. The adapter never
   machine-translates user input, so no fabricated FR/DE/IT equivalents can
   appear in a bundle.
2. Every added term is reported with ``origin="accepted_lexicon"`` so the
   provenance of a query variant stays auditable.
"""
from __future__ import annotations

LEXICON_PROVENANCE = (
    "copied_from:accepted/product/product/query/retrieval.py#EXPANSION"
)

# --- accepted product lexicon (verbatim) -------------------------------------
EXPANSION = {
    "miete": ["mietrecht", "loyer", "bail", "locazione", "affitto", "mietvertrag", "mietzins", "rent"],
    "mietrecht": ["miete", "loyer", "bail", "locazione", "mietvertrag", "mietzins"],
    "loyer": ["miete", "mietrecht", "bail", "locazione", "mietvertrag"],
    "bail": ["miete", "mietrecht", "loyer", "locazione"],
    "arbeit": ["arbeitsrecht", "travail", "emploi", "lavoro", "kündigung", "licenciement", "dismissal"],
    "kündigung": ["arbeit", "licenciement", "dismissal", "congé", "disdetta"],
    "licenciement": ["kündigung", "arbeit", "dismissal", "congé"],
    "strafe": ["strafrecht", "peine", "pénal", "pena", "penale", "sanction"],
    "pénal": ["strafe", "strafrecht", "pena", "penale"],
    "asyl": ["asile", "asilo", "migration", "flüchtling", "réfugié", "rifugiato"],
    "asile": ["asyl", "asilo", "migration"],
    "sozialversicherung": ["assurance", "sociale", "assicurazione", "invalidität", "invalidité", "invalidità", "ahv", "avs"],
    "invalidität": ["invalidité", "invalidità", "sozialversicherung", "assurance"],
    "steuer": ["impôt", "fiscal", "imposta", "tax", "steuerrecht", "droit fiscal"],
    "familie": ["famille", "famiglia", "scheidung", "divorce", "divorzio", "ehe"],
    "scheidung": ["divorce", "divorzio", "familie", "ehe"],
    "vertrag": ["contrat", "contratto", "obligation", "obbligazione", "schuld"],
    "haftung": ["responsabilité", "responsabilità", "liability", "schadenersatz", "dommages"],
    "eigentum": ["propriété", "proprietà", "property"],
    "umwelt": ["environnement", "ambiente", "environment"],
    "datenschutz": ["protection des données", "protezione dei dati", "data protection"],
}
# -----------------------------------------------------------------------------

# Aliases that only make sense as *search-side* synonyms for the OpenCaseLaw
# FTS index. Kept separate from the accepted table so the reuse boundary stays
# auditable; every entry is an already-existing legal term, never a translation.
SEARCH_ALIASES = {
    "miete": ["mietvertrag", "mietzins", "wohnung"],
    "mietvertrag": ["miete", "mietrecht"],
    "kündigung": ["kuendigung", "fristlose kündigung"],
    "haftung": ["schadenersatz"],
    "datenschutz": ["dsg", "revsg"],
    "asyl": ["asylgesetz", "asylg"],
}

KNOWN_TOKENS = tuple(sorted(set(EXPANSION) | set(SEARCH_ALIASES)))


def lookup(token: str) -> list[str]:
    """Return lexicon synonyms for a token (never invents new strings)."""
    t = (token or "").strip().lower()
    out: list[str] = []
    for src in (EXPANSION, SEARCH_ALIASES):
        for term in src.get(t, []):
            if term not in out:
                out.append(term)
    return out
