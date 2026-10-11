"""Remote-failure degradation tests (charter acceptance 8).

A stage or transport outage must never abort the bundle: it is recorded in
``provenance.failures`` and the bundle is marked ``degraded``.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_DIR = REPO_ROOT / "frontier" / "frontier-query-retrieval"

if str(TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM_DIR))

from ocl_adapter import AdapterConfig, build_candidate_bundle, validate_candidate_bundle  # noqa: E402
from ocl_adapter.client import OCLClient  # noqa: E402
from ocl_adapter.errors import OCLHTTPError, OCLTransportError  # noqa: E402
from ocl_adapter.fixtures import FIXTURE_QUERY, fixture_config  # noqa: E402
from ocl_adapter.ratelimit import RequestBudget  # noqa: E402
from ocl_adapter.transport import (  # noqa: E402
    FixtureTransport,
    RawResponse,
    ScriptedTransport,
)


def _search_body(ids, has_more=False, next_offset=None):
    return json.dumps(
        {
            "results": [
                {
                    "decision_id": did,
                    "language": "de",
                    "relevance_score": 10.0 - i,
                    "canonical_url": f"https://example.org/{did}",
                }
                for i, did in enumerate(ids)
            ],
            "total": len(ids),
            "has_more": has_more,
            "next_offset": next_offset,
            "returned": len(ids),
        }
    )


class TestTransportOutageDegrades(unittest.TestCase):
    def test_search_outage_yields_degraded_bundle(self):
        base = FixtureTransport({})

        class _AlwaysFail(FixtureTransport):
            def get(self, path, params=None):
                if path.startswith("/decisions") and "{" not in path:
                    raise OCLTransportError("injected outage", url=path)
                return super().get(path, params)

        cfg = fixture_config().replace(
            mode="offline",
            stages=("search",),
            citation_expansion=False,
            leading_cases=False,
            target=5,
            max_requests=5,
        )
        client = OCLClient(_AlwaysFail({}), cfg)
        bundle = build_candidate_bundle(FIXTURE_QUERY, config=cfg, client=client)
        self.assertTrue(bundle["provenance"]["degraded"])
        self.assertTrue(bundle["provenance"]["failures"])
        # Bundle is still structurally valid (empty candidates are the failure signal).
        self.assertIn("candidates", bundle)
        errors = validate_candidate_bundle(bundle)
        self.assertTrue(any("non-empty" in e for e in errors) or not bundle["candidates"])

    def test_partial_stage_failure_keeps_search_results(self):
        class _Partial(FixtureTransport):
            def get(self, path, params=None):
                if path.startswith("/leading"):
                    raise OCLTransportError("leading cases down", url=path)
                if path.startswith("/citations"):
                    raise OCLTransportError("citations down", url=path)
                if path == "/decisions":
                    body = _search_body(["A1", "A2", "A3"])
                    return RawResponse(
                        path=path,
                        params=dict(params or {}),
                        url="fixture://d",
                        status=200,
                        body=body,
                        fetched_at=0.0,
                        from_cache=True,
                    )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://x",
                    status=404,
                    body="{}",
                    fetched_at=0.0,
                )

        cfg = fixture_config().replace(
            mode="offline",
            stages=("search", "leading", "citations"),
            target=50,
            stop_when_target_met=False,
            max_requests=30,
        )
        client = OCLClient(_Partial({}), cfg)
        bundle = build_candidate_bundle("Test query Vertrag", config=cfg, client=client)
        self.assertGreaterEqual(len(bundle["candidates"]), 3)
        self.assertTrue(bundle["provenance"]["degraded"])
        stages_failed = {f.get("stage") for f in bundle["provenance"]["failures"]}
        self.assertTrue({"leading", "citations"} & stages_failed or "leading" in stages_failed)
        self.assertEqual(validate_candidate_bundle(bundle), [])

    def test_http_error_recorded(self):
        class _HttpFail(FixtureTransport):
            def get(self, path, params=None):
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://500",
                    status=500,
                    body='{"detail": "boom"}',
                    fetched_at=0.0,
                )

        cfg = fixture_config().replace(mode="offline", stages=("search",), max_requests=3)
        client = OCLClient(_HttpFail({}), cfg)
        bundle = build_candidate_bundle("x", config=cfg, client=client)
        self.assertTrue(bundle["provenance"]["degraded"])
        kinds = [f.get("status", f.get("kind")) for f in bundle["provenance"]["failures"]]
        self.assertTrue(kinds)


class TestBudgetExhaustion(unittest.TestCase):
    def test_tiny_budget_stops_and_marks_degraded(self):
        class _Ok(FixtureTransport):
            def get(self, path, params=None):
                if path == "/decisions":
                    return RawResponse(
                        path=path,
                        params=dict(params or {}),
                        url="fixture://d",
                        status=200,
                        body=_search_body(["B1", "B2", "B3"], has_more=True, next_offset=3),
                        fetched_at=0.0,
                        from_cache=True,
                    )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://x",
                    status=404,
                    body="{}",
                    fetched_at=0.0,
                )

        cfg = fixture_config().replace(
            mode="offline",
            stages=("search", "leading", "citations"),
            max_requests=1,
            target=100,
            stop_when_target_met=False,
            page_size=2,
        )
        client = OCLClient(_Ok({}), cfg, budget=RequestBudget(1))
        bundle = build_candidate_bundle("Budgettest", config=cfg, client=client)
        self.assertTrue(bundle["provenance"]["degraded"])
        self.assertLessEqual(bundle["provenance"]["request_summary"]["budget_used"], 1)
        # At least the first page landed before the budget closed.
        self.assertGreaterEqual(len(bundle["candidates"]), 2)


class TestOfflineCacheMissDegrades(unittest.TestCase):
    def test_unknown_query_offline_yields_empty_degraded_not_raise(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            cfg = fixture_config().replace(mode="offline", cache_dir=td, max_requests=5)
            # Transport stack uses CachedTransport offline: every miss is status=0.
            bundle = build_candidate_bundle("Unbekannte Anfrage XYZ", config=cfg)
            self.assertTrue(bundle["provenance"]["degraded"])
            self.assertEqual(bundle["candidates"], [])


class TestHydrationNotFound(unittest.TestCase):
    def test_404_on_hydration_marks_not_found(self):
        class _Hydrate404(FixtureTransport):
            def get(self, path, params=None):
                if path == "/decisions":
                    return RawResponse(
                        path=path,
                        params=dict(params or {}),
                        url="fixture://d",
                        status=200,
                        body=_search_body(["MISSING-1"]),
                        fetched_at=0.0,
                        from_cache=True,
                    )
                if path.startswith("/decisions/"):
                    return RawResponse(
                        path=path,
                        params=dict(params or {}),
                        url="fixture://404",
                        status=404,
                        body='{"detail": "not found"}',
                        fetched_at=0.0,
                    )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://x",
                    status=404,
                    body="{}",
                    fetched_at=0.0,
                )

        cfg = fixture_config().replace(
            mode="offline",
            stages=("search",),
            citation_expansion=False,
            leading_cases=False,
            target=5,
        )
        client = OCLClient(_Hydrate404({}), cfg)
        bundle = build_candidate_bundle(
            "Hydrate 404", config=cfg, client=client, hydrate_top=1
        )
        self.assertEqual(len(bundle["candidates"]), 1)
        cand = bundle["candidates"][0]
        self.assertEqual(cand["detail_status"], "not_found")
        self.assertEqual(cand["full_text_status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
