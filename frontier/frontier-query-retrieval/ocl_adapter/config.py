"""Adapter configuration.

stdlib-only. All defaults are safe for the charter's documented rate limit
(soft pace <= 5 req/s against https://mcp.opencaselaw.ch/api) and for a
100-300 decision candidate bundle.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional, Sequence, Tuple

DEFAULT_BASE_URL = "https://mcp.opencaselaw.ch/api"
DEFAULT_USER_AGENT = "LexMachina-Frontier-QueryRetrieval/1.0 (open retrieval adapter)"

# Charter dependency: "soft pace <=5 req/s". Default is deliberately under it.
DEFAULT_MAX_RPS = 4.0
CHARTER_MAX_RPS = 5.0

# Repository root = .../frontier/frontier-query-retrieval/ocl_adapter/config.py
PACKAGE_DIR = Path(__file__).resolve().parent
TEAM_DIR = PACKAGE_DIR.parent
REPO_ROOT = TEAM_DIR.parent.parent

DEFAULT_RESULTS_DIR = REPO_ROOT / "results" / "frontier" / "frontier-query-retrieval"
DEFAULT_CACHE_DIR = DEFAULT_RESULTS_DIR / "cache"
DEFAULT_FIXTURE_CACHE_DIR = DEFAULT_RESULTS_DIR / "fixtures" / "cache"

MODES = ("live", "offline", "refresh")
STAGES = ("search", "lang", "leading", "citations")
LANGUAGES = ("de", "fr", "it")


@dataclass(frozen=True)
class AdapterConfig:
    """Immutable adapter configuration.

    ``mode``:
      * ``live``    - read-through/write-through cache, network on miss
      * ``offline`` - cache only; a miss degrades instead of raising
      * ``refresh`` - always network, still writes the cache
    """

    base_url: str = DEFAULT_BASE_URL
    user_agent: str = DEFAULT_USER_AGENT
    mode: str = "live"
    cache_dir: str = str(DEFAULT_CACHE_DIR)

    timeout: float = 45.0
    retries: int = 3
    backoff_seconds: float = 1.5
    max_rps: float = DEFAULT_MAX_RPS

    # Retrieval budget
    target: int = 150
    max_candidates: int = 300
    page_size: int = 100
    max_pages_per_variant: int = 3
    lang_max_pages: int = 1
    max_requests: int = 40
    stop_when_target_met: bool = True
    stages: Tuple[str, ...] = STAGES

    # Remote field/detail level
    fields: str = "full"
    include_pinpoint: bool = False
    sort: str = "relevance"

    # Multilingual expansion (no machine translation: lexicon synonyms only)
    language_filters: Tuple[str, ...] = LANGUAGES
    max_expansion_terms: int = 12

    # Citation-neighbourhood expansion (bounded)
    citation_expansion: bool = True
    citation_seeds: int = 5
    citation_page_size: int = 20
    citation_min_confidence: float = 0.3
    max_new_from_citations: int = 60

    # Leading cases (bounded)
    leading_cases: bool = True
    leading_cases_limit: int = 20

    # Lazy detail hydration
    hydrate_default_limit: int = 5
    hydrate_needs_detail: int = 0

    cache_ttl_seconds: int = 7 * 24 * 3600
    request_log_limit: int = 500

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")
        unknown = [s for s in self.stages if s not in STAGES]
        if unknown:
            raise ValueError(f"unknown stages {unknown}; valid: {STAGES}")
        if not 0 < self.max_rps <= CHARTER_MAX_RPS + 1e-9:
            raise ValueError(
                f"max_rps must be in (0, {CHARTER_MAX_RPS}] to respect the "
                f"documented OpenCaseLaw soft pace; got {self.max_rps}"
            )
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be >= 1")

    def replace(self, **kw) -> "AdapterConfig":
        return replace(self, **kw)

    def cache_path(self) -> Path:
        return Path(self.cache_dir).expanduser()

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["stages"] = list(self.stages)
        d["language_filters"] = list(self.language_filters)
        return d


def config_from_env(base: Optional[AdapterConfig] = None, **overrides) -> AdapterConfig:
    """Build config from ``LEX_OCL_*`` environment variables plus overrides."""
    cfg = base or AdapterConfig()
    env_map = {
        "LEX_OCL_BASE_URL": ("base_url", str),
        "LEX_OCL_MODE": ("mode", str),
        "LEX_OCL_CACHE_DIR": ("cache_dir", str),
        "LEX_OCL_MAX_RPS": ("max_rps", float),
        "LEX_OCL_TARGET": ("target", int),
        "LEX_OCL_MAX_REQUESTS": ("max_requests", int),
    }
    kw = {}
    for var, (attr, cast) in env_map.items():
        raw = os.environ.get(var)
        if raw:
            kw[attr] = cast(raw)
    kw.update(overrides)
    return cfg.replace(**kw) if kw else cfg
