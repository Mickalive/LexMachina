"""Repairs landed by product cycle 39861042507 (operational resume of 39859552290).

Two durable contracts, both offline and deterministic:

1. ``verify_claim_cache_manifest`` separates STRUCTURAL integrity and
   ATTRIBUTED drift from the strict byte-equality flag, so accepted in-place
   cache rewrites (the D3 class) cannot make the guard permanently red while
   an unattributable (silent) rewrite still fails.
2. ``materialize_claim_cache`` materializes the frozen subset from its
   recorded git blobs (hash-verified against the manifest sha256), so the
   subset replay is reproducible forever even after accepted working-tree
   rewrites; a blob that cannot be verified fails CLOSED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from product.replay_bundle import (
    REPO_ROOT,
    _commit_is_ancestor,
    _frozen_entry_bytes,
    _last_touching_commit,
    load_claim_cache_manifest,
    materialize_claim_cache,
    verify_claim_cache_manifest,
)


def test_verifier_split_flags_hold_on_this_tree():
    findings = verify_claim_cache_manifest()
    assert findings["ok_structural"] is True, findings
    assert findings["ok_drift_attributed"] is True, findings
    # The strict flag keeps its historical meaning and is False while drift
    # exists; the split flags are what the sibling guards assert.
    for entry in findings["mismatched_attributed"]:
        assert entry["attributed"] is True, entry
        assert entry["commit"] and entry["subject"], entry
        assert _commit_is_ancestor(entry["commit"]), entry


def test_every_drifted_entry_is_attributed_to_a_committed_rewrite():
    findings = verify_claim_cache_manifest()
    man = load_claim_cache_manifest()
    recorded = {e["path"]: e["sha256"] for e in man["entries"]}
    for relpath in findings["mismatched"]:
        info = _last_touching_commit(relpath)
        assert info is not None, f"no git history for drifted entry {relpath}"
        assert _commit_is_ancestor(info["commit"]), (relpath, info)
        # The drift is real (working tree differs from the manifest).
        current = hashlib.sha256(
            (REPO_ROOT / relpath).read_bytes()).hexdigest()
        assert current != recorded[relpath], relpath


def test_frozen_bytes_are_readable_for_a_drifted_entry(tmp_path):
    findings = verify_claim_cache_manifest()
    man = load_claim_cache_manifest()
    by_path = {e["path"]: e for e in man["entries"]}
    assert findings["mismatched"], "expected the known attributed drift"
    for relpath in findings["mismatched"][:3]:
        entry = by_path[relpath]
        blob = _frozen_entry_bytes(entry, man.get("frozen_from_commit"))
        assert blob is not None, relpath
        assert hashlib.sha256(blob).hexdigest() == entry["sha256"], relpath


def test_materialize_uses_frozen_bytes_even_when_tree_drifted(tmp_path):
    from product.replay_bundle import CLAIM_CACHE_ROOT_RELPATH

    findings = verify_claim_cache_manifest()
    man = load_claim_cache_manifest()
    by_path = {e["path"]: e for e in man["entries"]}
    root = materialize_claim_cache(tmp_path)
    for relpath in findings["mismatched"]:
        entry = by_path[relpath]
        materialized = root / Path(relpath).relative_to(CLAIM_CACHE_ROOT_RELPATH)
        assert materialized.is_file(), relpath
        assert hashlib.sha256(materialized.read_bytes()).hexdigest() == (
            entry["sha256"]), (
            f"materialized bytes for {relpath} do not match the manifest sha256"
        )


def test_materialize_fails_closed_on_an_unverifiable_entry(tmp_path):
    man = load_claim_cache_manifest()
    tampered = json.loads(json.dumps(man))
    tampered["entries"][0]["sha256"] = "0" * 64
    try:
        materialize_claim_cache(tmp_path, manifest=tampered)
    except ValueError as exc:
        assert "cannot be materialized" in str(exc)
    else:
        raise AssertionError(
            "materialization must fail closed when an entry's recorded bytes "
            "are neither in git history nor intact in the working tree"
        )
