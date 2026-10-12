"""Typed OpenCaseLaw REST client (thin, stdlib-only, rate-limit aware).

Endpoints used by the charter:

* ``GET /decisions``                     relevance search + pagination
* ``GET /decisions/{id}``                full decision (lazy)
* ``GET /structure/{id}``                structured reasoning (lazy)
* ``GET /citations/{id}``                incoming/outgoing citation graph
* ``GET /leading-cases``                 leading / landmark cases
* ``GET /regeste/{id}``                  official head-note (lazy fallback)

Every call goes through the injected transport (live / offline / fixture),
is paced by the shared :class:`RateLimiter`, and is recorded in a bounded
request log so bundles can prove how they were produced.
"""
from __future__ import annotations

import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from .config import AdapterConfig
from .errors import OCLBudgetExceeded, OCLHTTPError, OCLTransportError
from .ratelimit import RateLimiter, RequestBudget
from .transport import Transport

P_SEARCH = "/decisions"
P_DECISION = "/decisions/{id}"
P_STRUCTURE = "/structure/{id}"
P_REGESTE = "/regeste/{id}"
P_CITATIONS = "/citations/{id}"
P_LEADING = "/leading-cases"


def enc(decision_id: str) -> str:
    """URL-encode a decision id (ids contain spaces, slashes and quotes)."""
    return urllib.parse.quote(str(decision_id), safe="")


class OCLClient:
    def __init__(
        self,
        transport: Transport,
        config: Optional[AdapterConfig] = None,
        *,
        limiter: Optional[RateLimiter] = None,
        budget: Optional[RequestBudget] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.transport = transport
        self.config = config or AdapterConfig()
        self.limiter = limiter or RateLimiter(self.config.max_rps)
        self.budget = budget or RequestBudget(self.config.max_requests)
        self._clock = clock
        self.requests: List[dict] = []
        self.failures: List[dict] = []
        self.cache_hits = 0
        self.network_calls = 0

    # -- plumbing --------------------------------------------------------
    def _log(self, entry: dict) -> None:
        if len(self.requests) < self.config.request_log_limit:
            self.requests.append(entry)

    def _call(self, stage: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """One paced, budgeted, logged request. Raises typed errors."""
        if self.budget.exhausted:
            raise OCLBudgetExceeded(f"request budget exhausted before {path}")
        self.budget.consume(stage=stage)
        t0 = self._clock()
        try:
            resp = self.transport.get(path, params)
        except OCLTransportError as exc:
            self.failures.append({"stage": stage, "path": path, "error": str(exc)})
            self._log({
                "stage": stage, "path": path, "params": dict(params or {}),
                "status": 0, "error": str(exc), "from_cache": False,
            })
            raise
        elapsed = round(self._clock() - t0, 4)
        if resp.from_cache:
            self.cache_hits += 1
        else:
            self.network_calls += 1
        self._log({
            "stage": stage,
            "path": path,
            "params": dict(resp.params or {}),
            "status": resp.status,
            "from_cache": resp.from_cache,
            "error": resp.error,
            "seconds": elapsed,
        })
        if resp.status == 0:
            err = OCLTransportError(
                f"{stage}: transport returned no data ({resp.error or 'unknown'})", url=resp.url
            )
            self.failures.append({"stage": stage, "path": path, "error": str(err)})
            raise err
        if not (200 <= resp.status < 300):
            detail = resp.detail()
            exc = OCLHTTPError(resp.status, detail, url=resp.url)
            self.failures.append({"stage": stage, "path": path, "status": resp.status, "error": detail})
            raise exc
        return resp.json()

    # -- endpoints -------------------------------------------------------
    def search_page(
        self,
        *,
        query: Optional[str] = None,
        language: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        stage: str = "search",
        sort: Optional[str] = None,
        fields: Optional[str] = None,
        include_pinpoint: Optional[bool] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        court: Optional[str] = None,
    ) -> dict:
        cfg = self.config
        params: Dict[str, Any] = {
            "query": query,
            "limit": limit or cfg.page_size,
            "offset": int(offset),
            "sort": sort or cfg.sort,
            "fields": fields or cfg.fields,
            "include_pinpoint": "true" if (cfg.include_pinpoint if include_pinpoint is None else include_pinpoint) else "false",
        }
        if language:
            params["language"] = language
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if court:
            params["court"] = court
        payload = self._call(stage, P_SEARCH, params)
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "search payload is not an object", url=P_SEARCH)
        payload.setdefault("results", [])
        if not isinstance(payload["results"], list):
            payload["results"] = []
        return payload

    def get_decision(self, decision_id: str, *, full_text: bool = True) -> dict:
        payload = self._call(
            "decision",
            P_DECISION.format(id=enc(decision_id)),
            {"full_text": "true" if full_text else "false"},
        )
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "decision payload is not an object", url=decision_id)
        return payload

    def get_structure(self, decision_id: str, *, paragraph_excerpt_chars: int = 400) -> dict:
        payload = self._call(
            "structure",
            P_STRUCTURE.format(id=enc(decision_id)),
            {"paragraph_excerpt_chars": paragraph_excerpt_chars},
        )
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "structure payload is not an object", url=decision_id)
        return payload

    def get_regeste(self, decision_id: str) -> dict:
        payload = self._call("regeste", P_REGESTE.format(id=enc(decision_id)), {})
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "regeste payload is not an object", url=decision_id)
        return payload

    def get_citations(
        self,
        decision_id: str,
        *,
        direction: str = "both",
        limit: Optional[int] = None,
        offset: int = 0,
        min_confidence: Optional[float] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "direction": direction,
            "limit": limit or self.config.citation_page_size,
            "offset": int(offset),
        }
        mc = self.config.citation_min_confidence if min_confidence is None else min_confidence
        params["min_confidence"] = mc
        payload = self._call("citations", P_CITATIONS.format(id=enc(decision_id)), params)
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "citations payload is not an object", url=decision_id)
        payload.setdefault("incoming", [])
        payload.setdefault("outgoing", [])
        return payload

    def get_leading_cases(
        self,
        *,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        include_pinpoint: bool = False,
        court: Optional[str] = None,
        law_code: Optional[str] = None,
    ) -> dict:
        params: Dict[str, Any] = {
            "query": query,
            "limit": limit or self.config.leading_cases_limit,
            "include_pinpoint": "true" if include_pinpoint else "false",
        }
        if court:
            params["court"] = court
        if law_code:
            params["law_code"] = law_code
        payload = self._call("leading", P_LEADING, params)
        if not isinstance(payload, dict):
            raise OCLHTTPError(200, "leading-cases payload is not an object", url=P_LEADING)
        payload.setdefault("results", [])
        return payload

    # -- reporting -------------------------------------------------------
    def stats(self) -> dict:
        return {
            "requests_logged": len(self.requests),
            "cache_hits": self.cache_hits,
            "network_calls": self.network_calls,
            "budget_used": self.budget.used,
            "budget_max": self.budget.max_requests,
            "rate_limit_rps": self.limiter.rps,
            "min_interval_seconds": round(self.limiter.min_interval, 4),
        }

    def summary(self) -> dict:
        by_stage: Dict[str, int] = {}
        for r in self.requests:
            by_stage[r.get("stage", "?")] = by_stage.get(r.get("stage", "?"), 0) + 1
        out = self.stats()
        out["requests_by_stage"] = dict(sorted(by_stage.items()))
        out["failures"] = len(self.failures)
        return out
