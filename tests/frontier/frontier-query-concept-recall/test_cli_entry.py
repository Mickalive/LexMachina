"""Tests for the acceptance-test-(3) entry point (``cli_entry.py``).

Run::

    PYTHONPATH=frontier python -m pytest tests/frontier/frontier-query-concept-recall \
        -q
    PYTHONPATH=frontier python tests/frontier/frontier-query-concept-recall \
        /test_cli_entry.py          # stdlib fallback, no pytest needed

Every test here is OFFLINE and asserts ``network_calls == 0``.  Nothing in this
file writes outside a temporary directory.

What is pinned
--------------
* **F** -- the defect this file exists for: the accepted harness raises a raw
  ``KeyError`` when ``--bundle`` names a strict subset of the served questions,
  so the one invocation charter acceptance test (3) names is not runnable in the
  one-bundle form the charter names.  ``cli_entry`` must complete the served set
  from the RULES-pinned read-only accepted bytes and say so.
* **G** -- a stale, different-schema ``RULES.json`` sits in the in-scope
  directory with input pins that do not match the accepted bytes.  Pin
  resolution must read the CANONICAL rules file and refuse a moved freeze.
* record shape -- ``rows_per_concept``, ``under_covered`` and per-language
  authority recall must resolve under the names the charter uses, and the alias
  must be the SAME object, never a recomputation.
* neutrality -- a one-bundle run must produce a claim-bearing body identical to
  the full run, so the repair is measurement-neutral.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_HERE = Path(__file__).resolve().parent
for _p in (str(_REPO / "frontier"), str(_REPO / "frontier/frontier-query-concept-recall")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_spec = importlib.util.spec_from_file_location(
    "fqc_cli_entry", _HERE.parent.parent.parent / "frontier/frontier-query-concept-recall/cli_entry.py")
cli_entry = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cli_entry)

SERVED = cli_entry.SERVED_QUESTIONS
BUNDLE_DIR = Path(cli_entry.harness_cli.BUNDLE_DIR)


def _bundle_path(qid: str) -> Path:
    return BUNDLE_DIR / f"{qid}.bundle.json"


def _require_mount() -> None:
    if not BUNDLE_DIR.is_dir():
        raise unittest.SkipTest(
            "accepted product mount not present; set LEX_ACCEPTED_PRODUCT_MOUNT")


class TestCanonicalRulesResolution(unittest.TestCase):
    def test_both_canonical_copies_re_hash_to_the_same_digest(self):
        """freeze_ordering.json claims the two canonical copies are identical."""
        pins = cli_entry.rules_bundle_pins()
        self.assertEqual(set(pins), set(SERVED))
        self.assertEqual(
            cli_entry.sha256_file(cli_entry.RULES_PATH),
            cli_entry.sha256_file(cli_entry.RESULTS_RULES_PATH))
        self.assertEqual(cli_entry.sha256_file(cli_entry.RULES_PATH),
                         cli_entry.EXPECTED_RULES_SHA256)

    def test_every_pinned_bundle_re_hashes(self):
        _require_mount()
        for qid, pin in cli_entry.rules_bundle_pins().items():
            self.assertEqual(cli_entry.sha256_file(Path(pin["path"])),
                             pin["content_sha256"], qid)

    def test_stale_rules_in_this_directory_is_reported_not_used(self):
        report = cli_entry.stale_rules_report()
        if not report["present"]:
            self.skipTest("no stale RULES.json in the in-scope directory")
        self.assertFalse(report["is_canonical"])
        self.assertNotEqual(report["sha256"], cli_entry.EXPECTED_RULES_SHA256)
        # The stale file must never be what the entry point resolves pins from.
        self.assertNotEqual(cli_entry.RULES_PATH.resolve(),
                            cli_entry.STALE_RULES_PATH.resolve())


class TestServedSetCompletion(unittest.TestCase):
    def test_single_bundle_completes_the_served_set(self):
        """DEFECT F: this used to raise KeyError('fr-bail-entretien')."""
        _require_mount()
        bundles, completed, unresolved = cli_entry.resolve_served_set(
            [str(_bundle_path("de-kapitalverletzung"))])
        self.assertEqual(unresolved, [])
        self.assertEqual(set(bundles), set(SERVED))
        self.assertEqual(sorted(completed),
                         ["fr-bail-entretien", "it-responsabilita-medica"])

    def test_no_bundle_argument_uses_the_accepted_served_set(self):
        _require_mount()
        bundles, completed, unresolved = cli_entry.resolve_served_set(None)
        self.assertEqual(unresolved, [])
        self.assertEqual(completed, [])
        self.assertEqual(set(bundles), set(SERVED))

    def test_two_bundles_complete_only_the_third(self):
        _require_mount()
        _bundles, completed, _unresolved = cli_entry.resolve_served_set(
            [str(_bundle_path("de-kapitalverletzung")),
             str(_bundle_path("it-responsabilita-medica"))])
        self.assertEqual(completed, ["fr-bail-entretien"])


class TestCharterNamedFields(unittest.TestCase):
    def test_aliases_are_the_same_object_not_a_recomputation(self):
        arm = {"concept_row_counts": {"kapitalverletzung": 0},
               "concepts_with_zero_rows": ["kapitalverletzung"]}
        record = {"served_questions": {"q": {"A0_baseline_shipped": arm}}}
        added = cli_entry.add_charter_named_fields(record)
        out = record["served_questions"]["q"]["A0_baseline_shipped"]
        self.assertIs(out["rows_per_concept"], out["concept_row_counts"])
        self.assertIs(out["under_covered"], out["concepts_with_zero_rows"])
        self.assertTrue(added)

    def test_aliasing_never_overwrites_an_existing_key(self):
        arm = {"concept_row_counts": {"a": 1}, "rows_per_concept": {"sentinel": True}}
        cli_entry.add_charter_named_fields({"served_questions": {"q": {"A": arm}}})
        self.assertEqual(arm["rows_per_concept"], {"sentinel": True})

    def test_authority_recall_alias_on_frozen_legs(self):
        record = {"frozen_legs": {"leg": {"per_language": {
            "fr": {"A1_union": {"recall": 0.0}}}}}}
        cli_entry.add_charter_named_fields(record)
        cell = record["frozen_legs"]["leg"]["per_language"]["fr"]["A1_union"]
        self.assertEqual(cell["authority_recall"], 0.0)


class TestEndToEndOffline(unittest.TestCase):
    """The repaired entry point actually runs where the accepted one crashes."""

    @classmethod
    def setUpClass(cls):
        _require_mount()
        cls._tmp = tempfile.TemporaryDirectory()
        out = Path(cls._tmp.name) / "out"
        code = cli_entry.main([
            "--bundle", str(_bundle_path("de-kapitalverletzung")),
            "--out", str(out), "--offline"])
        cls.code = code
        cls.out = out
        cls.record = json.loads((out / "harness_results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_exit_code_is_zero(self):
        self.assertEqual(self.code, 0)

    def test_no_network(self):
        self.assertEqual(self.record["latency_budget"]["n_network_calls_this_run"], 0)

    def test_baseline_reproduced(self):
        self.assertTrue(self.record["verdict"]["accepted_baseline_reproduced"])

    def test_accepted_finding_still_reproduced_exactly(self):
        q = self.record["served_questions"]["de-kapitalverletzung"]
        arm = q["A0_baseline_shipped"]
        self.assertEqual(arm["n_rows"], 214)
        self.assertEqual(sorted(arm["under_covered"]),
                         ["kapitalverletzung", "uberwachungspflicht"])

    def test_charter_named_fields_resolve(self):
        q = self.record["served_questions"]["de-kapitalverletzung"]["A0_baseline_shipped"]
        self.assertEqual(q["rows_per_concept"]["kapitalverletzung"], 0)
        leg = self.record["frozen_legs"]["corporate-criminal-liability"]
        self.assertEqual(leg["per_language"]["fr"]["A1_union"]["authority_recall"], 0.0)

    def test_completion_is_disclosed_in_the_record(self):
        self.assertEqual(
            sorted(self.record["entry_point"]
                   ["served_questions_completed_from_pinned_readonly_mount"]),
            ["fr-bail-entretien", "it-responsabilita-medica"])

    def test_completion_does_not_change_any_number(self):
        """Measurement neutrality: the repaired one-bundle run equals the full run."""
        full = Path(self._tmp.name) / "full"
        cli_entry.main(["--out", str(full), "--offline"])
        other = json.loads((full / "harness_results.json").read_text())
        here = copy.deepcopy(self.record)
        for rec in (here, other):
            rec.pop("generated_at", None)
            rec.pop("run_id", None)
            rec.pop("entry_point", None)
        self.assertEqual(json.dumps(here, sort_keys=True),
                         json.dumps(other, sort_keys=True))

    def test_empty_cache_aborts_loudly_instead_of_fabricating(self):
        """Defect C: a replay with no cache must not invent a gate regression."""
        committed = cli_entry.committed_cache_roots()
        if not committed:
            self.skipTest("committed A1 cache not present in this checkout")
        saved = cli_entry.COMMITTED_CACHE_DIRS
        try:
            # Hide every committed cache AND point --out at an empty dir: the
            # entry point must abort with exit 2, not emit a record with a
            # fabricated transport::all_queries_ok regression.
            cli_entry.COMMITTED_CACHE_DIRS = ()
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(cli_entry.main(["--out", tmp, "--offline"]), 2)
                self.assertFalse((Path(tmp) / "harness_results.json").exists())
        finally:
            cli_entry.COMMITTED_CACHE_DIRS = saved


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
