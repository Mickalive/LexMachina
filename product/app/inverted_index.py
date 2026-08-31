"""In-memory inverted index for fast full-text search across corpus documents.

Provides TF-IDF ranked retrieval with support for multi-word AND queries,
optional language filtering, and incremental index updates. Handles Unicode
text from Swiss case law (German, French, Italian) without external dependencies
beyond numpy.
"""

import math
import re
from typing import Dict, List, Optional, Tuple

import numpy as np


# Internal hyphen patterns for Swiss languages: keep compound words intact
# e.g., "Ober-gerichtshof" stays as one token, but "Bundes- und Verwaltungsgericht"
# gets split at the spaces around the dash.
_TOKEN_RE = re.compile(r"[^\w-]+|(?<!\w)-|-(?!\w)")

# Minimum token length after lowercasing
_MIN_TOKEN_LEN = 2


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on whitespace/punctuation, drop short tokens.

    Preserves internal hyphens in compound words common in German/French/Italian
    Swiss legal texts (e.g., ``Obergericht``, ``Verwaltungsgericht``).
    """
    lower = text.lower()
    # Split on non-word, non-hyphen sequences, or on hyphens that are at word
    # boundaries (so "Ober-gericht" is kept, but "word1 - word2" splits).
    raw = _TOKEN_RE.split(lower)
    return [t for t in raw if len(t) >= _MIN_TOKEN_LEN]


class InvertedIndex:
    """In-memory inverted index with TF-IDF ranking.

    Build once from a ``{decision_id: full_text}`` mapping, then query with
    optional language filtering.  The index supports incremental additions and
    document removal without a full rebuild (though removals leave the index
    in a slightly degraded state until the next full build).

    Attributes are prefixed with underscore to signal "internal, do not mutate".
    """

    def __init__(self) -> None:
        # term -> {doc_id: term_count_in_doc}
        self._term_to_doc_ids: Dict[str, Dict[str, int]] = {}
        # doc_id -> total token count
        self._doc_lengths: Dict[str, int] = {}
        # doc_id -> ISO 639-1 language code
        self._doc_languages: Dict[str, str] = {}
        # total number of documents currently in the index
        self._total_docs: int = 0
        # whether a full build has been completed
        self._built: bool = False

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        documents: Dict[str, str],
        languages: Optional[Dict[str, str]] = None,
    ) -> None:
        """Build the index from a ``{decision_id: full_text}`` mapping.

        Parameters
        ----------
        documents:
            Mapping of document identifiers to their full text content.
        languages:
            Optional mapping of document identifiers to ISO 639-1 language
            codes (e.g. ``"de"``, ``"fr"``, ``"it"``).  When provided the
            index will store them for query-time filtering.

        After calling this method the index is ready for :meth:`search`.
        """
        # Reset all internal state so repeated builds are safe.
        self._term_to_doc_ids.clear()
        self._doc_lengths.clear()
        self._doc_languages.clear()
        self._total_docs = 0

        if languages is not None:
            self._doc_languages.update(languages)

        for doc_id, text in documents.items():
            self._add_document_internal(doc_id, text)

        self._built = True

    # ------------------------------------------------------------------
    # Incremental mutations
    # ------------------------------------------------------------------

    def add_document(
        self, doc_id: str, text: str, language: Optional[str] = None
    ) -> None:
        """Add a single document to the existing index.

        If ``doc_id`` already exists it is replaced (the old entry is removed
        first).  This is safe to call even before :meth:`build` – the index
        will simply grow from an empty state.

        Parameters
        ----------
        doc_id:
            Unique document identifier.
        text:
            Full text content to index.
        language:
            Optional ISO 639-1 language code for query-time filtering.
        """
        if doc_id in self._doc_lengths:
            self.remove_document(doc_id)

        if language is not None:
            self._doc_languages[doc_id] = language

        self._add_document_internal(doc_id, text)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index.

        The removal updates all posting lists and metadata.  After many
        removals the IDF values may become slightly stale; call :meth:`build`
        again to get a perfectly accurate index.

        Parameters
        ----------
        doc_id:
            Identifier of the document to remove.

        Raises
        ------
        KeyError
            If ``doc_id`` is not in the index.
        """
        if doc_id not in self._doc_lengths:
            raise KeyError(doc_id)

        length = self._doc_lengths.pop(doc_id)
        self._doc_languages.pop(doc_id, None)
        self._total_docs -= 1

        # Remove doc_id from every posting list that references it.
        empty_terms: List[str] = []
        for term, posting in self._term_to_doc_ids.items():
            posting.pop(doc_id, None)
            if not posting:
                empty_terms.append(term)
        for term in empty_terms:
            del self._term_to_doc_ids[term]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 20,
        language: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """Search the index for documents matching *all* query terms.

        Parameters
        ----------
        query:
            Free-text query.  Terms are extracted with the same tokeniser used
            at index time.  All terms must appear in a document for it to be
            returned (AND semantics).
        limit:
            Maximum number of results to return.
        language:
            Optional ISO 639-1 language code.  When provided, only documents
            indexed with a matching language are considered.

        Returns
        -------
        list of (doc_id, score)
            Pairs sorted by descending score.
        """
        if not self._built and not self._total_docs:
            return []

        query_terms = _tokenize(query)
        if not query_terms:
            return []

        # De-duplicate query terms but preserve order for deterministic output.
        seen: set = set()
        unique_terms: List[str] = []
        for t in query_terms:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        # Collect candidate doc_ids that contain every query term AND match
        # the language filter.
        candidate_sets: List[set] = []
        for term in unique_terms:
            posting = self._term_to_doc_ids.get(term)
            if posting is None:
                # Term not in the index at all → zero results.
                return []
            if language is not None:
                docs = {
                    d
                    for d in posting
                    if self._doc_languages.get(d) == language
                }
            else:
                docs = set(posting.keys())
            candidate_sets.append(docs)

        # Intersection of all posting sets → documents containing all terms.
        candidate_ids: set = candidate_sets[0]
        for s in candidate_sets[1:]:
            candidate_ids = candidate_ids & s

        if not candidate_ids:
            return []

        n = self._total_docs if self._total_docs else 1

        # Pre-compute IDF for each unique query term.  We always use the
        # global document count (including documents filtered out by language)
        # so that IDF remains a stable statistic of the corpus.
        idf: Dict[str, float] = {}
        for term in unique_terms:
            df = len(self._term_to_doc_ids.get(term, {}))
            idf[term] = math.log(n / df) if df else 0.0

        # Score each candidate.
        scores: List[Tuple[str, float]] = []
        for doc_id in candidate_ids:
            doc_len = self._doc_lengths.get(doc_id, 1)
            score = 0.0
            matched_terms = 0
            for term in unique_terms:
                tf = self._term_to_doc_ids[term].get(doc_id, 0) / doc_len
                score += tf * idf[term]
                if tf > 0:
                    matched_terms += 1

            # Boost: multiply by fraction of query terms matched.  This
            # rewards documents that match more of the query even when the
            # base TF-IDF score is similar.
            score *= matched_terms / len(unique_terms)
            scores.append((doc_id, score))

        # Sort descending by score, then ascending by doc_id for stability.
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:limit]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_document_internal(self, doc_id: str, text: str) -> None:
        """Index a single document.  Caller must not pass a duplicate doc_id."""
        tokens = _tokenize(text)
        length = len(tokens)
        if length == 0:
            # Empty document: still record it so it can be filtered out later.
            self._doc_lengths[doc_id] = 0
            self._total_docs += 1
            return

        self._doc_lengths[doc_id] = length
        self._total_docs += 1

        # Count term frequencies in this document.
        tf_counts: Dict[str, int] = {}
        for token in tokens:
            tf_counts[token] = tf_counts.get(token, 0) + 1

        # Update the global inverted index.
        for term, count in tf_counts.items():
            if term not in self._term_to_doc_ids:
                self._term_to_doc_ids[term] = {}
            self._term_to_doc_ids[term][doc_id] = count

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def doc_count(self) -> int:
        """Number of documents currently indexed."""
        return self._total_docs

    @property
    def term_count(self) -> int:
        """Number of unique terms in the index."""
        return len(self._term_to_doc_ids)
