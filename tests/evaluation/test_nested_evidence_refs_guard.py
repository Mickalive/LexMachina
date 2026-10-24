"""Tests for the nested evidence_refs operational-resume guard (item 1c)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import nested_evidence_refs_guard as guard


def test_ref_regex_matches_path_shapes():
    assert guard._REF_RE.match("results/evaluation/foo/4001.json")
    assert guard._REF_RE.match("evaluation/mod.py")
    assert not guard._REF_RE.match("just a phrase")
    assert not guard._REF_RE.match("https://example.com/x")


def test_first_token_strips_prose():
    assert guard._first_token("a/b.json (annotated note)") == "a/b.json"
    assert guard._first_token("a/b.json") == "a/b.json"


def test_walk_classifies_and_resolves(tmp_path):
    state = {
        "evidence_refs": ["docs/RESEARCH_PROTOCOL.md",
                          "results/does/not/exist_4000.json"],
        "nested": {"deeper": [{"ref": "evaluation/nested_evidence_refs_guard.py"}]},
        "prose": "pipeline.py e105bfed... drift note",
    }
    hits = []
    guard.walk_state(state, "$", hits)
    tokens = {h["token"]: h["status"] for h in hits}
    assert tokens["docs/RESEARCH_PROTOCOL.md"] == "RESOLVED_WORKTREE"
    assert tokens["evaluation/nested_evidence_refs_guard.py"] == "RESOLVED_WORKTREE"
    assert tokens["results/does/not/exist_4000.json"] == "UNRESOLVED"
    # prose values that are not ref-shaped are not classified as refs
    assert "pipeline.py" not in tokens


def test_guard_run_on_real_state(tmp_path):
    code, record = guard.run("scratch_test_guard", tmp_path)
    assert record["schema"] == guard.SCHEMA
    assert record["n_ref_shaped_values_total"] > 0
    # top-level refs must all resolve (accepted hygiene invariant)
    assert record["n_top_level_unresolved"] == 0
    # the guard must actually resolve nested values, not only the top level
    assert record["n_ref_shaped_values_total"] > record["n_top_level_evidence_refs"]
    if code == 1:
        # if unresolved refs exist they must be listed with json paths
        assert record["unresolved"]
        for u in record["unresolved"]:
            assert u["json_path"].startswith("$")
