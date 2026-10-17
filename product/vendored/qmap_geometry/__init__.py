"""Frontier team: query-conditioned map geometry (charter v1, run 38964153228).

Builds runnable, adoptable geometry candidates behind the ``query_result_bundle``
seam and scores them with the FROZEN geometry rule. No rendering, no UI.
"""
from .variants import VARIANTS, build_variant_geometry  # noqa: F401
