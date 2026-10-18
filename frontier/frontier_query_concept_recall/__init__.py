"""frontier-query-concept-recall: a deterministic, corpus-derived,
multilingual query-expansion layer measured behind the existing bundle seam.

The charter's acceptance test (3) requires the runnable entry point

    python -m frontier_query_concept_recall.cli --bundle <path> --out <dir>

so the package name carries underscores.  The predecessor run placed this code
in a hyphenated directory (``frontier/frontier-query-concept-recall``), which
``python -m`` cannot import at all; that directory is kept only as a pointer.
"""

__version__ = "2.0.0"
