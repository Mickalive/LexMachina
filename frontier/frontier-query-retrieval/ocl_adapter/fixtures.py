"""Canonical offline fixture scenario + recorder.

The adapter's tests must be deterministic and offline (charter acceptance 7),
while still exercising the *real* OpenCaseLaw response shapes. The recorder
runs the normal pipeline against the live API with ``results/.../fixtures/cache``
as its cache directory, which stores one content-addressed envelope per
request. Tests then replay the identical request sequence in ``mode="offline"``.

Both the recorder and the tests call :func:`fixture_config`, so the recorded
request keys and the replayed request keys can never drift apart silently.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional

from .bundle import bundle_summary, validate_candidate_bundle
from .cache import FileCache
from .config import AdapterConfig, DEFAULT_FIXTURE_CACHE_DIR, DEFAULT_RESULTS_DIR
from .pipeline import build_candidate_bundle

# The frozen fixture query. Real Swiss tenancy-law question; hits all three
# official languages through the accepted LexMachina lexicon.
FIXTURE_QUERY = "Kündigung Mietvertrag Mietrecht"
FIXTURE_META_PATH = DEFAULT_RESULTS_DIR / "fixtures" / "FIXTURE_META.json"


def fixture_config(**overrides) -> AdapterConfig:
    """Deterministic configuration shared by recording and replay."""
    base = dict(
        mode="live",
        cache_dir=str(DEFAULT_FIXTURE_CACHE_DIR),
        target=40,
        max_candidates=200,
        page_size=20,
        max_pages_per_variant=2,
        lang_max_pages=1,
        max_requests=30,
        max_rps=4.0,
        stages=("search", "lang", "leading", "citations"),
        stop_when_target_met=False,
        citation_expansion=True,
        citation_seeds=3,
        citation_page_size=8,
        leading_cases=True,
        leading_cases_limit=10,
        language_filters=("de", "fr", "it"),
        hydrate_default_limit=2,
        hydrate_needs_detail=2,
    )
    base.update(overrides)
    return AdapterConfig(**base)


def record_fixtures(
    query: str = FIXTURE_QUERY,
    *,
    config: Optional[AdapterConfig] = None,
    hydrate_top: int = 2,
    force: bool = False,
) -> Dict:
    """Run the pipeline live against the fixture cache dir. Idempotent."""
    cfg = (config or fixture_config()).replace(mode="live")
    cache_dir = Path(cfg.cache_dir)
    if force and cache_dir.exists():
        import shutil

        shutil.rmtree(cache_dir)
    cache = FileCache(cache_dir)
    bundle = build_candidate_bundle(
        query,
        config=cfg,
        cache=cache,
        hydrate_top=hydrate_top,
        include_structure=True,
    )
    keys = cache.keys()
    meta = {
        "recorded_at": time.time(),
        "query": query,
        "cache_dir": str(cache_dir),
        "n_entries": len(keys),
        "keys": keys,
        "request_summary": bundle["provenance"]["request_summary"],
        "searches": bundle["provenance"]["searches"],
        "stage_notes": bundle["provenance"]["stage_notes"],
        "failures": bundle["provenance"]["failures"],
        "degraded": bundle["provenance"]["degraded"],
        "summary": bundle_summary(bundle),
        "validation_errors": validate_candidate_bundle(bundle),
        "config": cfg.to_dict(),
        "hydrate_top": hydrate_top,
    }
    FIXTURE_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def replay_fixtures(query: str = FIXTURE_QUERY, *, config: Optional[AdapterConfig] = None, hydrate_top: int = 2) -> dict:
    """Offline replay of the recorded scenario (no network)."""
    cfg = (config or fixture_config()).replace(mode="offline")
    cache = FileCache(cfg.cache_path())
    return build_candidate_bundle(
        query,
        config=cfg,
        cache=cache,
        hydrate_top=hydrate_top,
        include_structure=True,
    )


__all__ = [
    "FIXTURE_QUERY",
    "FIXTURE_META_PATH",
    "fixture_config",
    "record_fixtures",
    "replay_fixtures",
]
