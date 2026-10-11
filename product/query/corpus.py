"""Query-specific corpus: deterministic local fixture + OpenCaseLaw live fetch with cache.

Canonical source doctrine: OpenCaseLaw public infrastructure is the default data
plane. This sandbox cannot always reach it (TLS egress), so every live call has
a graceful fallback to the vendored trilingual fixture (100 decisions,
DE/FR/IT, full_text) copied from ACCEPTED evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = BASE_DIR / "results" / "query_fixtures"
CACHE_DIR = BASE_DIR / "results" / "query_cache"

ACCEPTED_FIXTURE_CANDIDATES = [
    Path("/tmp/lex_accepted/frontier/frontier-query-retrieval/results/corpus/bger_2024_2026_sample_100.jsonl"),
    Path("/tmp/lex_accepted/frontier/frontier-generative-audit/results/corpus/bger_2024_2026_sample_100.jsonl"),
    Path("/tmp/lex_accepted/frontier/frontier-query-map-ui/results/corpus/bger_2024_2026_sample_100.jsonl"),
]

# OpenCaseLaw public search endpoints (tried in order; all optional).
OCL_ENDPOINTS = [
    "https://opencaselaw.org/api/search",
    "https://www.opencaselaw.org/api/search",
]


def ensure_fixture() -> Path:
    """Copy the ACCEPTED 100-decision fixture into product-owned space if needed."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    dest = FIXTURE_DIR / "bger_sample_100.jsonl"
    if dest.exists():
        return dest
    for src in ACCEPTED_FIXTURE_CANDIDATES:
        if src.exists():
            dest.write_bytes(src.read_bytes())
            return dest
    raise FileNotFoundError("No fixture source available (accepted mounts missing)")


def load_fixture_decisions() -> list[dict]:
    path = ensure_fixture()
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out.append({
                "decision_id": r.get("decision_id", ""),
                "court": r.get("court", "bger"),
                "language": r.get("language", "?"),
                "decision_date": r.get("decision_date", ""),
                "docket_number": r.get("docket_number", ""),
                "full_text": r.get("full_text", ""),
                "provenance": "fixture:bger_sample_100",
            })
    return out


def ocl_live_search(query: str, limit: int = 50, timeout: int = 12) -> tuple[list[dict], str]:
    """Try OpenCaseLaw live search. Returns (decisions, provenance_note). Never raises."""
    for base in OCL_ENDPOINTS:
        try:
            url = base + "?" + urllib.parse.urlencode({"q": query, "limit": limit})
            req = urllib.request.Request(url, headers={"User-Agent": "LexMachina-MVP/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read(2_000_000).decode("utf-8", "replace")
            data = json.loads(payload)
            items = data if isinstance(data, list) else data.get("results", data.get("items", []))
            out = []
            for it in items[:limit]:
                if not isinstance(it, dict):
                    continue
                out.append({
                    "decision_id": str(it.get("id") or it.get("decision_id") or it.get("docket_number") or "?"),
                    "court": str(it.get("court", "?")),
                    "language": str(it.get("language", "?")),
                    "decision_date": str(it.get("date") or it.get("decision_date") or ""),
                    "docket_number": str(it.get("docket_number", "")),
                    "full_text": str(it.get("text") or it.get("full_text") or it.get("snippet") or ""),
                    "canonical_url": str(it.get("url") or it.get("canonical_url") or ""),
                    "provenance": f"live:{base}",
                })
            if out:
                return out, f"live:{base}"
        except Exception:
            continue
    return [], "live:unreachable"


def cached_live_search(query: str, limit: int = 50, ttl_seconds: int = 86400) -> tuple[list[dict], str, bool]:
    """File-cached live search. Returns (decisions, provenance, from_cache)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{query}|{limit}".encode()).hexdigest()[:16]
    cpath = CACHE_DIR / f"ocl_{key}.json"
    if cpath.exists():
        try:
            cached = json.loads(cpath.read_text(encoding="utf-8"))
            if time.time() - cached.get("_cached_at", 0) < ttl_seconds:
                return cached["decisions"], cached.get("provenance", "live:cache"), True
        except Exception:
            pass
    decisions, prov = ocl_live_search(query, limit)
    if decisions:
        try:
            cpath.write_text(json.dumps(
                {"_cached_at": time.time(), "query": query, "provenance": prov, "decisions": decisions},
                ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return decisions, prov, False


def get_query_corpus(query: str, limit: int = 50) -> tuple[list[dict], dict]:
    """Combined corpus for one query: live OCL (cached) + fixture fallback.

    Returns (decisions, info) where info records provenance mix.
    """
    live, live_prov, from_cache = cached_live_search(query, limit)
    fixture = load_fixture_decisions()
    seen = set()
    merged: list[dict] = []
    for d in live:
        if d["decision_id"] and d["decision_id"] not in seen:
            seen.add(d["decision_id"])
            merged.append(d)
    for d in fixture:
        if d["decision_id"] not in seen:
            seen.add(d["decision_id"])
            merged.append(d)
    info = {
        "n_live": len(live),
        "n_fixture": len(fixture),
        "n_total": len(merged),
        "live_provenance": live_prov,
        "live_from_cache": from_cache,
    }
    return merged, info
