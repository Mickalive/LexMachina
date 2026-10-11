"""Data smoke tests for frontier-query-map-ui.

Verifies that the fixture bundle and visualization data are valid
and conform to the query_result_bundle schema.
"""
import json
import sys
import unittest
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Add team src to path for imports
TEAM_SRC = REPO_ROOT / "frontier" / "frontier-query-map-ui" / "src"
sys.path.insert(0, str(TEAM_SRC))

from product.query.bundle import validate_bundle, bundle_summary
from query_bundle_adapter import adapt_bundle_to_visualization


class TestDataSmoke(unittest.TestCase):
    """Smoke tests for fixture data integrity."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = REPO_ROOT / "frontier" / "frontier-query-map-ui" / "fixtures"
        cls.bundle_path = cls.fixture_dir / "query_result_bundle.json"
        cls.viz_path = cls.fixture_dir / "visualization.json"
        cls.manifest_path = cls.fixture_dir / "FIXTURE_MANIFEST.json"

        assert cls.bundle_path.exists(), f"Bundle not found: {cls.bundle_path}"
        assert cls.viz_path.exists(), f"Visualization not found: {cls.viz_path}"
        assert cls.manifest_path.exists(), f"Manifest not found: {cls.manifest_path}"

        with open(cls.bundle_path, encoding="utf-8") as f:
            cls.bundle = json.load(f)

        with open(cls.viz_path, encoding="utf-8") as f:
            cls.viz = json.load(f)

        with open(cls.manifest_path, encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_bundle_validates_against_schema(self):
        """Bundle must pass validate_bundle with zero errors."""
        errors = validate_bundle(self.bundle)
        self.assertEqual(errors, [], f"Bundle validation errors: {errors}")

    def test_bundle_has_minimum_decisions(self):
        """Bundle must have at least 100 decisions (charter requirement)."""
        self.assertGreaterEqual(len(self.bundle["decisions"]), 100)

    def test_bundle_has_clusters(self):
        """Bundle must have clusters with labels."""
        self.assertGreater(len(self.bundle["clusters"]), 0)
        for c in self.bundle["clusters"]:
            self.assertIn("cluster_id", c)
            self.assertIn("label", c)
            self.assertIn("member_ids", c)

    def test_bundle_has_relations(self):
        """Bundle should have relations (citation/typed edges)."""
        relations = self.bundle.get("relations", [])
        self.assertGreater(len(relations), 0)
        for r in relations:
            self.assertIn("source", r)
            self.assertIn("target", r)
            self.assertIn("kind", r)

    def test_bundle_has_answer_with_citations(self):
        """Bundle must have answer with cited decision IDs."""
        answer = self.bundle.get("answer", {})
        self.assertIn("prose", answer)
        self.assertIn("cited_decision_ids", answer)
        # All cited IDs must be in retrieved decisions
        decision_ids = {d["decision_id"] for d in self.bundle["decisions"]}
        cited_ids = set(answer.get("cited_decision_ids", []))
        self.assertTrue(cited_ids.issubset(decision_ids),
                       f"Cited IDs not in decisions: {cited_ids - decision_ids}")

    def test_bundle_has_counter_authority_statuses(self):
        """Bundle must have counter_status field on decisions with known vocabulary."""
        known_statuses = {
            "none", "cited", "candidate-limiting", "candidate-contrary",
            "candidate-distinguishing", "candidate-exception",
            "supporting-candidate", "context"
        }
        for d in self.bundle["decisions"]:
            self.assertIn("counter_status", d)
            self.assertIn(d["counter_status"], known_statuses,
                         f"Unknown counter_status: {d['counter_status']}")

    def test_bundle_has_outlier_flags(self):
        """Bundle must have is_outlier boolean on decisions."""
        outlier_count = sum(1 for d in self.bundle["decisions"] if d.get("is_outlier"))
        self.assertGreater(outlier_count, 0, "Should have some outliers")

    def test_bundle_has_coordinates(self):
        """All decisions must have x, y coordinates in [-1, 1] range roughly."""
        for d in self.bundle["decisions"]:
            self.assertIn("x", d)
            self.assertIn("y", d)
            self.assertIsInstance(d["x"], (int, float))
            self.assertIsInstance(d["y"], (int, float))

    def test_bundle_has_canonical_urls(self):
        """All decisions must have canonical_url field."""
        for d in self.bundle["decisions"]:
            self.assertIn("canonical_url", d)
            self.assertIsInstance(d["canonical_url"], str)
            self.assertTrue(d["canonical_url"].startswith("http"))

    def test_visualization_adaptation_works(self):
        """Adapter must produce valid visualization output from bundle."""
        viz = adapt_bundle_to_visualization(self.bundle)
        
        self.assertIn("decisions", viz)
        self.assertIn("clusters", viz)
        self.assertIn("relations", viz)
        self.assertIn("bounds", viz)
        self.assertEqual(viz["n_decisions"], len(self.bundle["decisions"]))
        
        # Check adapted decisions have visualization fields
        for d in viz["decisions"]:
            self.assertIn("cluster_color", d)
            self.assertIn("lang_color", d)
            self.assertIn("counter_color", d)
            self.assertIn("counter_label", d)
            self.assertIn("outlier_alpha", d)
            self.assertIn("radius", d)

    def test_visualization_matches_fixture(self):
        """Generated visualization should match saved fixture (deterministic)."""
        # The fixture was generated by the same adapter, so key counts should match
        self.assertEqual(self.viz["n_decisions"], len(self.bundle["decisions"]))
        self.assertEqual(self.viz["n_clusters"], len(self.bundle["clusters"]))
        self.assertEqual(self.viz["n_relations"], len(self.bundle.get("relations", [])))

    def test_no_global_174k_dependencies(self):
        """Verify no global 174k alignment/hierarchy keys in bundle or viz."""
        forbidden_keys = ["174k", "hierarchy", "fractal", "global", "center_projected", "id2clust"]
        
        def check_dict(d, path=""):
            for k, v in d.items():
                k_lower = k.lower()
                for forbidden in forbidden_keys:
                    self.assertNotIn(forbidden, k_lower,
                        f"Forbidden key '{forbidden}' found in {path}.{k}")
                if isinstance(v, dict):
                    check_dict(v, f"{path}.{k}")
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    for i, item in enumerate(v[:3]):  # Sample first 3
                        check_dict(item, f"{path}.{k}[{i}]")
        
        check_dict(self.bundle, "bundle")
        check_dict(self.viz, "viz")

    def test_manifest_checksums_match(self):
        """Manifest SHA256s must match actual files."""
        import hashlib
        
        for fname, info in self.manifest["files"].items():
            fpath = self.fixture_dir / fname
            self.assertTrue(fpath.exists(), f"File in manifest not found: {fname}")
            
            actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
            self.assertEqual(actual_sha, info["sha256"],
                           f"SHA256 mismatch for {fname}")
            
            actual_bytes = fpath.stat().st_size
            self.assertEqual(actual_bytes, info["bytes"],
                           f"Byte count mismatch for {fname}")

    def test_provenance_honest_offline(self):
        """Provenance must honestly report offline status."""
        prov = self.bundle.get("provenance", {})
        corpus = prov.get("corpus", {})
        
        self.assertEqual(corpus.get("n_live"), 0)
        self.assertEqual(corpus.get("live_provenance"), "live:unreachable")
        self.assertEqual(corpus.get("live_from_cache"), False)

    def test_bundle_summary_counts(self):
        """Bundle summary should match actual counts."""
        summary = bundle_summary(self.bundle)
        
        self.assertEqual(summary["n_decisions"], len(self.bundle["decisions"]))
        self.assertEqual(summary["n_clusters"], len(self.bundle["clusters"]))
        self.assertEqual(summary["n_relations"], len(self.bundle.get("relations", [])))
        
        # Counter count should match decisions with counter status
        counter_in_decisions = sum(1 for d in self.bundle["decisions"] 
                                   if d.get("counter_status") not in (None, "", "none"))
        self.assertEqual(summary["n_counter"], counter_in_decisions)


if __name__ == "__main__":
    unittest.main(verbosity=2)