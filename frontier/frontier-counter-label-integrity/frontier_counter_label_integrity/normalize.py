"""Deterministic text normalisation for the frozen support rubric.

All behaviour here is a pure function of the frozen ``normalization`` block in
RULES.json.  Nothing in this module encodes a legal judgement: it only folds
text so that the frozen lexicons can be matched mechanically.

Pipeline (frozen order):
  NFKC -> strip soft hyphen -> lowercase -> fold diacritics to ASCII ->
  eszett/ligature expansion -> umlaut-digraph folding -> whitespace collapse ->
  tokenise (alphanumeric runs) -> frozen suffix stemmer.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_SOFT_HYPHEN = "\u00ad"
_DIGRAPHS = (("ue", "u"), ("oe", "o"), ("ae", "a"))


def fold_diacritics(text: str) -> str:
    """ASCII-fold accented Latin letters; expand eszett and the oe/ae ligatures."""
    text = text.replace("\u00df", "ss")
    out: list[str] = []
    for ch in text:
        if ch in ("\u0153", "\u0152"):  # oe ligatures
            out.append("oe" if ch == "\u0153" else "ae")
            continue
        if ch in ("\u2019", "\u02bc"):
            out.append("'")
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
        out.append(stripped)
    return "".join(out)


def normalize_text(text: Any, *, digraphs: bool = True) -> str:
    """Normalised, folded, whitespace-collapsed string.

    ``digraphs=False`` stops before the umlaut-digraph stage.  The frozen regex
    patterns (procedural_formula / polarity_inversion / fragment_pointer) are
    authored in natural orthography ("darueber genaue Angaben"), so they are
    matched against the diacritic-folded but NOT digraph-folded string: folding
    ``ue`` to ``u`` would turn the pattern word "genaue" into "genau" and the
    match would fail.  Token-level anchor/marker matching keeps the digraph
    fold, because the anchors are authored with the digraph spelling
    ("ueberwachung") and must match both "ueberwachung" and "ueberwachung".
    """
    s = "" if text is None else str(text)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace(_SOFT_HYPHEN, "")
    s = s.lower()
    s = fold_diacritics(s)
    if digraphs:
        for src, dst in _DIGRAPHS:
            s = s.replace(src, dst)
    return _WS.sub(" ", s).strip()


def tokenize(text: Any) -> list[str]:
    """Alphanumeric token run of the normalised string."""
    return [t for t in _NON_ALNUM.split(normalize_text(text)) if t]


def stem(token: str, strip_order: list[str], min_stem_len: int) -> str:
    """Frozen suffix stripper: first matching suffix wins, stem kept >= min."""
    for suf in strip_order:
        if token.endswith(suf):
            cand = token[: -len(suf)]
            if len(cand) >= min_stem_len:
                return cand
            return token
    return token


class Normalizer:
    """Configured normalizer built from the frozen ``normalization`` block."""

    def __init__(self, norm_cfg: dict[str, Any]) -> None:
        self._strip_order = list(norm_cfg["stemming"]["strip_order"])
        self._min_stem_len = int(norm_cfg["stemming"]["min_stem_len"])
        self._min_prefix = int(norm_cfg.get("min_anchor_prefix_chars", 5))
        self._min_match = int(norm_cfg.get("min_match_chars", 4))
        self._cache: dict[str, str] = {}

    # -- text level -----------------------------------------------------
    def text(self, value: Any) -> str:
        return normalize_text(value)

    def folded_tokens(self, value: Any) -> list[str]:
        """Stemmed tokens with the digraph fold applied (marker/anchor stage)."""
        return self.stems(value)

    def regex_text(self, value: Any) -> str:
        """Text the frozen regex patterns are matched against (no digraph fold)."""
        return normalize_text(value, digraphs=False)

    # -- token level ----------------------------------------------------
    def stem_token(self, token: str) -> str:
        if len(token) >= self._min_match and token in self._cache:
            return self._cache[token]
        out = stem(token, self._strip_order, self._min_stem_len)
        if len(token) >= self._min_match:
            self._cache[token] = out
        return out

    def stems(self, value: Any) -> list[str]:
        return [self.stem_token(t) for t in tokenize(value)]

    # -- matching primitives -------------------------------------------
    def match_marker(self, hay_tokens: list[str], marker: str) -> str | None:
        """MARKER match = exact stemmed token, or contiguous stemmed subsequence.

        Returns the matched form (for reporting) or None.  Prefix matching is
        deliberately NOT allowed for markers (frozen normalization rule).
        """
        want = self.stems(marker)
        if not want:
            return None
        if len(want) == 1:
            if want[0] in hay_tokens:
                return marker
            return None
        n, m = len(hay_tokens), len(want)
        for i in range(n - m + 1):
            if hay_tokens[i : i + m] == want:
                return marker
        return None

    def match_anchor(self, hay_tokens: list[str], anchor: str) -> str | None:
        """ANCHOR match = stemmed prefix >= min_anchor_prefix_chars, or subsequence."""
        want = self.stems(anchor)
        if not want:
            return None
        if len(want) > 1:
            n, m = len(hay_tokens), len(want)
            for i in range(n - m + 1):
                if hay_tokens[i : i + m] == want:
                    return anchor
            return None
        target = want[0]
        for tok in hay_tokens:
            limit = min(len(tok), len(target))
            if limit >= self._min_prefix and tok[:limit] == target[:limit]:
                return anchor
        return None

    def match_regex(self, hay_text: str, pattern: str) -> str | None:
        try:
            if re.search(pattern, hay_text, flags=re.IGNORECASE):
                return pattern
        except re.error:
            return None
        return None