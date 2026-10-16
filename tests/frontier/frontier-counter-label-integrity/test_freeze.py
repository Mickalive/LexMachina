"""Charter acceptance test (1): the rubric was frozen before any label was scored.

Freeze ordering is proven from git commit times, never from a hand-written
frozen_at_utc field, and every frozen input is re-hashed against the mount.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

from conftest import git, freeze_commit_time


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_rules_file_is_the_only_source_of_thresholds(rules, repo_root):
    """No lexicon or threshold may live in the harness code."""
    pkg = os.path.join(repo_root, "frontier", "frontier-counter-label-integrity",
                       "frontier_counter_label_integrity")
    joined = ""
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py"):
            with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                joined += fh.read()
    # Legal vocabulary must not be hard-coded in the harness.
    for token in ("abgewiesen", "rejete", "respinto", "kapitalverletzung", "medico",
                  "nicht zu", "free correspondence", "cited in generated answer"):
        assert token not in joined, f"lexicon token hard-coded in harness code: {token!r}"
    assert rules.data["lexicons"]["counter_intent_markers"]["de"]["product_adversarial_terms"]


def test_rules_blob_at_freeze_commit_matches_working_tree(repo_root):
    """The committed frozen blob and the file on disk are the same bytes."""
    blob = subprocess.run(
        ["git", "-C", repo_root, "cat-file", "blob",
         "HEAD:results/frontier/frontier-counter-label-integrity/RULES.json"],
        check=True, capture_output=True,
    ).stdout
    digest = hashlib.sha256(blob).hexdigest()
    on_disk = _sha256_file(
        os.path.join(repo_root, "results/frontier/frontier-counter-label-integrity/RULES.json")
    )
    assert digest == on_disk, "RULES.json differs from the committed freeze blob"


def test_freeze_commit_predates_the_scoring_commit(repo_root):
    """Freeze ordering proven from commit times (charter test 1)."""
    freeze_at = freeze_commit_time(repo_root)
    assert freeze_at, "RULES.json has no commit"
    scored = git(
        repo_root, "log", "--format=%cI",
        "--", "results/frontier/frontier-counter-label-integrity/REPORT.json",
    ).splitlines()
    assert scored, "REPORT.json has no commit: results cannot be claimed under a frozen rubric"
    assert freeze_at <= scored[-1], (
        f"REPORT.json commit {scored[-1]} is older than the RULES.json freeze {freeze_at}"
    )


def test_report_embeds_the_frozen_rules_sha256(rules, report):
    assert report["rules_sha256"] == rules.sha256
    assert report["charter_version"] == rules.data["charter_version"] == 1
    assert report["team_id"] == rules.data["team_id"] == "frontier-counter-label-integrity"


def test_every_frozen_input_still_hashes_as_frozen(rules, product_mount, report):
    for entry in rules.data["inputs"]:
        path = entry["product_mount_path"]
        assert os.path.exists(path), path
        assert _sha256_file(path) == entry["sha256"], f"input drift: {entry['relpath_under_results_product']}"
    assert report["all_inputs_match_frozen_sha256"] is True


def test_gate_packet_content_sha256_recorded(rules, report):
    """The charter names content_sha256 2e79bf17/b3380de9/7449819e; they must be recorded."""
    seen = {b["qid"]: b.get("content_sha256") for b in report["bundles"] if b["population"] == "primary"}
    assert seen["de-kapitalverletzung"].startswith("2e79bf17")
    assert seen["fr-bail-entretien"].startswith("b3380de9")
    assert seen["it-responsabilita-medica"].startswith("7449819e")


def test_no_post_repair_artifact_is_claimed(report):
    probe = report["coverage"]["post_repair_artifact"]
    assert probe["adversarial_retrieval_results_dir_exists"] is False
    assert probe["adversarial_retrieval_source_exists"] is False
    assert report["coverage"]["before_after_pair"] is None
    assert report["coverage"]["every_scored_bundle_is_pre_repair"] is True


def _leaves_with(node, needle: str, path: str = "$"):
    out = []
    if isinstance(node, dict):
        for k in sorted(node):
            out += _leaves_with(node[k], needle, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _leaves_with(v, needle, f"{path}[{i}]")
    elif isinstance(node, str) and needle in node:
        out.append(path)
    return out


def test_audited_non_accepted_numbers_are_not_used_as_a_support_rate(report):
    """The audited non-accepted run id may appear only in explicit disclaimers."""
    leaks = [p for p in _leaves_with(report, "38828034436")
             if not (p.startswith("$.charter_claims_checked_at_freeze")
                     or p.startswith("$.coverage.before_after_note")
                     or p.startswith("$.populations")
                     or p.startswith("$.bundles")
                     or p.startswith("$.limitations"))]
    assert leaks == [], f"audited non-accepted run referenced outside a disclaimer: {leaks}"
    text = json.dumps(report, ensure_ascii=False)
    assert "22 of 40" not in text and '"22_of_40"' not in text