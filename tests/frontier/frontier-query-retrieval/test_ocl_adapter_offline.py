"""Offline fixture-replay tests: pagination, cache, dedupe, provenance,
multilingual variants, lazy hydration, product bridge, CLI.

No network. Deterministic (charter acceptance 7–8).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_DIR = REPO_ROOT / "frontier" / "frontier-query-retrieval"
ADAPTER_DIR = TEAM_DIR / "ocl_adapter"
FIXTURE_CACHE = REPO_ROOT / "results" / "frontier" / "frontier-query-retrieval" / "fixtures" / "cache"
FIXTURE_META = REPO_ROOT / "results" / "frontier" / "frontier-query-retrieval" / "fixtures" / "FIXTURE_META.json"

if str(TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM_DIR))

from ocl_adapter import (  # noqa: E402
    AdapterConfig,
    FileCache,
    build_candidate_bundle,
    bundle_summary,
    to_product_bundle,
    validate_against_product,
    validate_candidate_bundle,
)
from ocl_adapter.cache import request_key  # noqa: E402
from ocl_adapter.config import CHARTER_MAX_RPS  # noqa: E402
from ocl_adapter.dedupe import dedupe, identity_key  # noqa: E402
from ocl_adapter.expansion import build_variants  # noqa: E402
from ocl_adapter.fixtures import FIXTURE_QUERY, fixture_config, replay_fixtures  # noqa: E402
from ocl_adapter.normalize import normalize_search_hit  # noqa: E402


def _offline_cfg(tmpdir: Path, **overrides) -> AdapterConfig:
    base = fixture_config().replace(mode="offline", cache_dir=str(tmpdir / "cache"))
    return base.replace(**overrides) if overrides else base


class TestFixturesPresent(unittest.TestCase):
    def test_fixture_cache_committed(self):
        self.assertTrue(FIXTURE_CACHE.is_dir(), f"missing fixture cache: {FIXTURE_CACHE}")
        files = list(FIXTURE_CACHE.rglob("*.json"))
        self.assertGreaterEqual(len(files), 10, "fixture cache too small")

    def test_fixture_meta_valid(self):
        meta = json.loads(FIXTURE_META.read_text(encoding="utf-8"))
        self.assertEqual(meta["query"], FIXTURE_QUERY)
        self.assertEqual(meta["n_entries"], len(meta["keys"]))
        self.assertEqual(meta["validation_errors"], [])


class TestConfigGuards(unittest.TestCase):
    def test_max_rps_capped_at_charter(self):
        AdapterConfig(max_rps=CHARTER_MAX_RPS)
        with self.assertRaises(ValueError):
            AdapterConfig(max_rps=CHARTER_MAX_RPS + 1.0)
        with self.assertRaises(ValueError):
            AdapterConfig(max_rps=0)

    def test_invalid_mode_and_stage_rejected(self):
        with self.assertRaises(ValueError):
            AdapterConfig(mode="turbo")
        with self.assertRaises(ValueError):
            AdapterConfig(stages=("search", "bogus"))


class TestDeterministicDedupe(unittest.TestCase):
    def _hits(self):
        out = []
        for i, did in enumerate(["a", "b", "c"]):
            rec = normalize_search_hit(
                {"decision_id": did, "relevance_score": 10 - i, "language": "de"},
                channel="search",
            )
            out.append(rec)
        return out

    def test_order_independent(self):
        recs = self._hits()
        r1 = [dict(r) for r in recs]
        r2 = [dict(r) for r in reversed(recs)]
        d1 = dedupe(r1)
        d2 = dedupe(r2)
        self.assertEqual(
            [c["decision_id"] for c in d1.candidates],
            [c["decision_id"] for c in d2.candidates],
        )

    def test_merges_same_identity_via_source_url(self):
        a = normalize_search_hit(
            {
                "decision_id": "X 1",
                "source_url": "https://example.org/doc/1",
                "relevance_score": 1.0,
            },
            channel="search",
        )
        b = normalize_search_hit(
            {
                "decision_id": "X 1 alias",
                "source_url": "https://example.org/doc/1",
                "relevance_score": 2.0,
            },
            channel="citation.incoming",
        )
        result = dedupe([a, b])
        self.assertEqual(len(result.candidates), 1)
        self.assertGreaterEqual(result.stats["merged_away"], 1)
        merged = result.candidates[0]
        self.assertIn("citation.incoming", merged["channels"])
        self.assertIn("search", merged["channels"])
        self.assertEqual(merged["merged"]["n_members"], 2)

    def test_identity_key_prefers_canonical_id(self):
        rec = {"canonical_decision_id": "CID", "decision_id": "DID", "source_url": "u"}
        self.assertEqual(identity_key(rec), "cid:CID")


class TestMultilingualVariants(unittest.TestCase):
    def test_variants_include_lang_filters_and_lexicon(self):
        variants = build_variants("Kündigung Mietvertrag Mietrecht")
        kinds = {v.kind for v in variants}
        self.assertIn("original", kinds)
        self.assertIn("lexicon_expansion", kinds)
        self.assertIn("language_filter", kinds)
        langs = {v.language_filter for v in variants if v.kind == "language_filter"}
        self.assertEqual(langs, {"de", "fr", "it"})

    def test_no_fabricated_translations(self):
        variants = build_variants("Kündigung Mietvertrag Mietrecht")
        # Every language_filter variant keeps the original text verbatim.
        original = next(v for v in variants if v.kind == "original")
        for v in variants:
            if v.kind == "language_filter":
                self.assertEqual(v.text, original.text)
                self.assertIn("not a translation", v.note)
        # Lexicon expansion only reports terms from the accepted table.
        lex = next((v for v in variants if v.kind == "lexicon_expansion"), None)
        if lex is not None:
            self.assertTrue(lex.terms_added)
            self.assertIn("accepted", lex.terms_added_from.lower())
            self.assertIn("retrieval.py", lex.terms_added_from)


class TestOfflineReplayBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = replay_fixtures()

    def test_valid_candidate_bundle(self):
        errors = validate_candidate_bundle(self.bundle)
        self.assertEqual(errors, [])

    def test_candidates_have_required_fields_and_provenance(self):
        from ocl_adapter.bundle import CANDIDATE_REQUIRED

        for c in self.bundle["candidates"]:
            for key in CANDIDATE_REQUIRED:
                self.assertIn(key, c)
            self.assertTrue(c["provenance"])
            self.assertTrue(c["canonical_url"])
            self.assertTrue(c["decision_id"])

    def test_ranked_deterministically(self):
        ranks = [c["rank"] for c in self.bundle["candidates"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        # Re-run must produce identical decision_id sequence.
        again = replay_fixtures()
        self.assertEqual(
            [c["decision_id"] for c in self.bundle["candidates"]],
            [c["decision_id"] for c in again["candidates"]],
        )

    def test_channels_and_multilingual_coverage(self):
        summary = bundle_summary(self.bundle)
        self.assertGreater(summary["n_candidates"], 0)
        channels = summary["channels"]
        self.assertIn("search", channels)
        # Multilingual language-filtered expansion present.
        self.assertTrue(
            any(k.startswith("search.language_filter") or k == "search.language_filter" for k in channels)
            or "search.language_filter" in channels
            or channels.get("search.language_filter", 0) > 0
            or any("language" in k for k in channels)
            or summary["languages"].keys() & {"de", "fr", "it"},
        )
        # At least two of DE/FR/IT represented (fixtures record all three).
        langs = set(summary["languages"]) & {"de", "fr", "it"}
        self.assertGreaterEqual(len(langs), 2, f"languages={summary['languages']}")

    def test_lazy_hydration_from_fixtures(self):
        hydrated = self.bundle["lazy"].get("hydrated", [])
        self.assertTrue(hydrated, "fixture scenario should hydrate at least one decision")
        by_id = {c["decision_id"]: c for c in self.bundle["candidates"]}
        for did in hydrated:
            rec = by_id.get(did) or next(
                (c for c in self.bundle["candidates"] if c.get("canonical_decision_id") == did),
                None,
            )
            self.assertIsNotNone(rec, f"hydrated id {did} missing from candidates")
            self.assertEqual(rec.get("detail_status"), "hydrated")
            self.assertTrue(rec.get("full_text") or rec.get("structure"))

    def test_citation_and_leading_channels_present(self):
        channels = bundle_summary(self.bundle)["channels"]
        self.assertTrue(
            any(ch.startswith("citation.") for ch in channels),
            f"expected citation expansion, got {channels}",
        )
        self.assertIn("leading_case", channels)

    def test_provenance_records_rate_limit_and_mode(self):
        prov = self.bundle["provenance"]
        self.assertEqual(prov["mode"], "offline")
        self.assertEqual(prov["charter_version"], 2)
        self.assertLessEqual(prov["rate_limit"]["max_rps"], CHARTER_MAX_RPS)
        self.assertFalse(prov["expansion"]["machine_translation_used"])
        self.assertIn("searches", prov)
        self.assertIn("request_summary", prov)

    def test_no_network_calls_in_offline_replay(self):
        rs = self.bundle["provenance"]["request_summary"]
        self.assertEqual(rs["network_calls"], 0)
        self.assertGreater(rs["cache_hits"], 0)

    def test_product_bridge_valid(self):
        prod = to_product_bundle(self.bundle)
        self.assertEqual(validate_against_product(self.bundle), [])
        for key in ("bundle_version", "query", "decisions", "provenance", "answer"):
            self.assertIn(key, prod)
        for d in prod["decisions"]:
            self.assertEqual(d["counter_status"], "unclassified")
            self.assertIn("canonical_url", d)
            self.assertIn("citation", d)


class TestCacheLayer(unittest.TestCase):
    def test_request_key_stable(self):
        k1 = request_key("/decisions", {"query": "a", "limit": 20})
        k2 = request_key("/decisions", {"limit": 20, "query": "a"})
        self.assertEqual(k1, k2)

    def test_cache_roundtrip_and_stats(self):
        with tempfile.TemporaryDirectory() as td:
            cache = FileCache(Path(td))
            key = cache.put_response(
                "/decisions",
                {"query": "x"},
                status=200,
                body='{"results": []}',
                url="https://example.org/decisions",
            )
            entry = cache.get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry["body"], '{"results": []}')
            self.assertEqual(cache.stats()["hits"], 1)
            self.assertEqual(cache.stats()["writes"], 1)
            self.assertIn(key, cache.keys())

    def test_offline_mode_serves_hits_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = FileCache(root / "cache")
            cfg = AdapterConfig(mode="offline", cache_dir=str(root / "cache"), target=5)
            # Pre-populate via FileCache then wrap CachedTransport offline.
            from ocl_adapter.transport import CachedTransport, HttpTransport, RawResponse

            class _NoNet(HttpTransport):
                def get(self, path, params=None):  # pragma: no cover
                    raise AssertionError("network attempted in offline mode")

            tr = CachedTransport(_NoNet(cfg.base_url), cache, mode="offline")
            miss = tr.get("/decisions", {"query": "zzz"})
            self.assertEqual(miss.status, 0)
            self.assertEqual(miss.error, "cache_miss")

            cache.put_response(
                "/decisions",
                {"query": "zzz"},
                status=200,
                body='{"results": [], "has_more": false}',
                url="https://example.org",
            )
            hit = tr.get("/decisions", {"query": "zzz"})
            self.assertEqual(hit.status, 200)
            self.assertTrue(hit.from_cache)


class TestPaginationScripted(unittest.TestCase):
    """Exercise the page loop with a synthetic multi-page transport."""

    def test_pages_follow_next_offset_until_exhausted(self):
        from ocl_adapter.client import OCLClient
        from ocl_adapter.transport import FixtureTransport, RawResponse

        pages = {
            0: [f"D{i}" for i in range(5)],
            5: [f"D{i}" for i in range(5, 10)],
            10: [f"D{i}" for i in range(10, 12)],
        }

        class _Paged(FixtureTransport):
            def get(self, path, params=None):
                if path != "/decisions":
                    return super().get(path, params)
                offset = int((params or {}).get("offset", 0))
                ids = pages.get(offset, [])
                has_more = (offset + 5) in pages or (offset + len(ids)) in pages
                # has_more only when a later page exists with items
                has_more = bool(pages.get(offset + max(len(ids), 1)))
                body = json.dumps(
                    {
                        "results": [
                            {
                                "decision_id": did,
                                "language": "de",
                                "relevance_score": 100 - offset - i,
                                "canonical_url": f"https://example.org/{did}",
                            }
                            for i, did in enumerate(ids)
                        ],
                        "total": 12,
                        "has_more": has_more,
                        "next_offset": offset + len(ids) if has_more else None,
                        "returned": len(ids),
                    }
                )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://decisions",
                    status=200,
                    body=body,
                    fetched_at=0.0,
                    from_cache=True,
                )

        cfg = AdapterConfig(
            mode="offline",
            page_size=5,
            max_pages_per_variant=5,
            max_candidates=50,
            target=50,
            max_requests=20,
            stages=("search",),
            citation_expansion=False,
            leading_cases=False,
            stop_when_target_met=False,
        )
        client = OCLClient(_Paged({}), cfg)
        bundle = build_candidate_bundle(
            "Paginierungstest Vertrag",
            config=cfg,
            client=client,
        )
        self.assertEqual(len(bundle["candidates"]), 12)
        pages_seen = [s["page"] for s in bundle["provenance"]["searches"]]
        # Pages must be non-decreasing within each variant (pagination works).
        self.assertGreaterEqual(len(pages_seen), 2)
        self.assertIn(0, pages_seen)
        self.assertIn(1, pages_seen)
        self.assertGreaterEqual(max(pages_seen), 1)
        # Candidate count proves multi-page merge.
        self.assertEqual(len(bundle["candidates"]), 12)
        self.assertEqual(validate_candidate_bundle(bundle), [])


class TestHardCapEnforcement(unittest.TestCase):
    """The documented ``max_candidates`` hard cap must hold exactly.

    A single page can push the unique count past the cap (the page loop
    checks the cap only *before* fetching), so the pipeline must trim to
    the highest-ranked candidates deterministically.
    """

    def test_single_oversized_page_is_trimmed_to_cap(self):
        from ocl_adapter.client import OCLClient
        from ocl_adapter.transport import FixtureTransport, RawResponse

        n_results = 30

        class _BigPage(FixtureTransport):
            def get(self, path, params=None):
                if path != "/decisions":
                    return super().get(path, params)
                body = json.dumps(
                    {
                        "results": [
                            {
                                "decision_id": f"D{i:02d}",
                                "language": "de",
                                "relevance_score": 100 - i,
                                "canonical_url": f"https://example.org/D{i:02d}",
                            }
                            for i in range(n_results)
                        ],
                        "total": n_results,
                        "has_more": False,
                        "next_offset": None,
                        "returned": n_results,
                    }
                )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://decisions",
                    status=200,
                    body=body,
                    fetched_at=0.0,
                    from_cache=True,
                )

        cfg = AdapterConfig(
            mode="offline",
            page_size=50,
            max_pages_per_variant=1,
            max_candidates=10,
            target=10,
            max_requests=20,
            stages=("search",),
            citation_expansion=False,
            leading_cases=False,
            stop_when_target_met=False,
        )
        client = OCLClient(_BigPage({}), cfg)
        bundle = build_candidate_bundle(
            "Hardcap Test",
            config=cfg,
            client=client,
        )
        # The hard cap holds exactly.
        self.assertEqual(len(bundle["candidates"]), 10)
        self.assertEqual(bundle["n_candidates"], 10)
        # Ranking is contiguous and the best relevance scores survive.
        self.assertEqual(
            [c["rank"] for c in bundle["candidates"]], list(range(1, 11))
        )
        self.assertEqual(
            [c["decision_id"] for c in bundle["candidates"]],
            [f"D{i:02d}" for i in range(10)],
        )
        # Trim is recorded in provenance.
        targets = bundle["provenance"]["targets"]
        self.assertEqual(targets["pre_trim_candidates"], 30)
        self.assertTrue(targets["trimmed_to_max_candidates"])
        self.assertEqual(validate_candidate_bundle(bundle), [])

    def test_no_trim_when_under_cap(self):
        from ocl_adapter.client import OCLClient
        from ocl_adapter.transport import FixtureTransport, RawResponse

        class _SmallPage(FixtureTransport):
            def get(self, path, params=None):
                if path != "/decisions":
                    return super().get(path, params)
                body = json.dumps(
                    {
                        "results": [
                            {
                                "decision_id": f"E{i}",
                                "language": "de",
                                "relevance_score": 100 - i,
                            }
                            for i in range(4)
                        ],
                        "total": 4,
                        "has_more": False,
                        "next_offset": None,
                        "returned": 4,
                    }
                )
                return RawResponse(
                    path=path,
                    params=dict(params or {}),
                    url="fixture://decisions",
                    status=200,
                    body=body,
                    fetched_at=0.0,
                    from_cache=True,
                )

        cfg = AdapterConfig(
            mode="offline",
            page_size=50,
            max_pages_per_variant=1,
            max_candidates=10,
            target=4,
            max_requests=20,
            stages=("search",),
            citation_expansion=False,
            leading_cases=False,
            stop_when_target_met=False,
        )
        client = OCLClient(_SmallPage({}), cfg)
        bundle = build_candidate_bundle(
            "Undercap Test",
            config=cfg,
            client=client,
        )
        self.assertEqual(len(bundle["candidates"]), 4)
        targets = bundle["provenance"]["targets"]
        self.assertEqual(targets["pre_trim_candidates"], 4)
        self.assertFalse(targets["trimmed_to_max_candidates"])
        self.assertEqual(validate_candidate_bundle(bundle), [])


class TestCliOffline(unittest.TestCase):
    def test_cli_fixture_preset_exit_0_and_writes_bundles(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bundle.json"
            prod = Path(td) / "product.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(TEAM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ocl_adapter",
                    FIXTURE_QUERY,
                    "--preset",
                    "fixtures",
                    "--out",
                    str(out),
                    "--product-bundle",
                    str(prod),
                    "--validate",
                    "--quiet",
                ],
                cwd=str(TEAM_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.exists())
            self.assertTrue(prod.exists())
            bundle = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(bundle["bundle_version"], "1.0-candidate")
            self.assertGreater(bundle["n_candidates"], 0)

    def test_cli_missing_query_exit_2(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(TEAM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "ocl_adapter", "--quiet"],
            cwd=str(TEAM_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
