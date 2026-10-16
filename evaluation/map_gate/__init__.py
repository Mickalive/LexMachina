"""Frozen query-map CONTRACT benchmark (evaluation lane, v49).

Measures whether the map Product actually ships satisfies the Master Prompt's
minimum map semantics. See ``frozen.py`` for the freeze discipline and
``gates.py`` for the five contract properties.
"""
from .frozen import (  # noqa: F401
    FROZEN_SHA256,
    FrozenBenchmarkError,
    bundle_specs,
    freeze_record,
    infer_query_language,
    load_frozen,
    normalize_text,
    sha256_file,
    tokenize,
)
from .gates import (  # noqa: F401
    counter_statuses,
    evaluate_bundle,
    label_language,
    relation_degrees,
    summarize,
)

__all__ = [
    "FROZEN_SHA256",
    "FrozenBenchmarkError",
    "bundle_specs",
    "counter_statuses",
    "evaluate_bundle",
    "freeze_record",
    "infer_query_language",
    "label_language",
    "load_frozen",
    "normalize_text",
    "relation_degrees",
    "sha256_file",
    "summarize",
    "tokenize",
]
