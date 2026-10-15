#!/usr/bin/env python3
"""Deterministic offline replay of a recorded query into a query_result_bundle.

Product-lane tool introduced by run 38766812030 (operational resume of
38763217418) to make `results/product/CYCLE_<run>_bundle.json` artifacts
reproducible by one command and to refuse synthetic fixture content on the
claim path (see reports/product/CYCLE_38759730609.md incident section).

Usage:
    python product/replay_bundle.py --query "<recorded query>" \
        --top-n 120 --out results/product/CYCLE_<run>_bundle.json

Exit codes:
    0  replay written/verified, bundle is genuine OpenCaseLaw-sourced data
    2  bad arguments
    3  bundle failed validate_bundle
    4  synthetic/fabricated content detected (ids or cluster labels)
    5  required claim fields missing (decision_id, citation, canonical_url,
       source_url, x, y, cluster_id, is_outlier)
    6  foreign citation content detected: a citation string shared by two
       decisions, a citation-channel row carrying a citation seed's own
       reference, or an unhydrated citation shell whose citation is neither
       its docket number nor its decision_id
    7  dangling relation detected: a relation names an endpoint that is not
       among the bundle's decisions, or a relation the cached /citations
       envelopes for this query's citation seeds do not support
    8  --check-claim-cache-manifest: the frozen claim-cache manifest is
       broken (entry missing or byte-drifted, or its key count no longer
       equals the n_keys the claim bundle recorded)
    9  --check-claim-cache-manifest: the manifest is intact but a replay
       against that frozen subset does not reproduce the committed
       content_sha256

``--check-claim-cache-manifest`` and ``--build-claim-cache-manifest`` are the
``--query``-free modes (exit 2 if ``--query`` is omitted in replay mode).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

from product.query.bundle import validate_bundle
from product.query.cache_path import product_cache_dir
from product.query.pipeline import CITE_CHANNELS, run_query_initial

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DECISION_FIELDS = (
    "decision_id",
    "citation",
    "canonical_url",
    "x",
    "y",
    "cluster_id",
)

# Field must exist on every decision (value may be null: OpenCaseLaw does not
# return a source_url for every citation-channel record, but the key is part of
# the query_result_bundle contract demanded by the cycle-38759730609 audit).
REQUIRED_DECISION_KEYS = (
    "is_outlier",
    "source_url",
)


def _looks_synthetic(decision_id: str) -> bool:
    """Detect the bge_BGE_test_0000_2024-style ids found in the retired bundle."""
    did = str(decision_id or "").lower()
    return "test_" in did and any(ch.isdigit() for ch in did)


def _norm_ref(value) -> str:
    """Lowercase alphanumeric form of a citation/decision reference."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def citation_findings(bundle: dict) -> dict:
    """Citation-forensics for one query_result_bundle.

    Required-fix provenance:
    results/audit/product/CYCLE_38766812030_GATE.json (gate=REVISE)
    required_fixes[0] ``must_add_guard``:

    * ``citation_duplicates`` — the gate's formula: the number of distinct
      non-empty citation strings must equal the number of distinct decisions
      that carry one, i.e. no citation string is shared by two decisions.
    * ``citation_channel_seed_refs`` — no citation-channel row may carry a
      citation seed's own reference (literal equality, plus a normalised
      containment match so ``6B_31_2019`` is caught against seed
      ``bger_6B_31_2019`` and ``BGE 142 IV 333`` against
      ``bge_BGE_142_IV_333``).

    ``pending_shell_identity`` is the product's own stronger check: an
    unhydrated citation shell has no API-provided citation of its own, so its
    ``citation`` must be exactly its docket number or its decision_id.
    """
    decisions = bundle.get("decisions") or []
    prov = bundle.get("provenance") or {}
    seeds = [
        str(entry.get("seed"))
        for entry in (((prov.get("stage_notes") or {}).get("citations") or {}).get("per_seed") or [])
        if isinstance(entry, dict) and entry.get("seed")
    ]
    seed_norm = {_norm_ref(s): s for s in seeds}

    citation_owner: dict[str, set[str]] = defaultdict(set)
    for d in decisions:
        citation = str(d.get("citation") or "")
        if citation:
            citation_owner[citation].add(str(d.get("decision_id") or ""))
    duplicates = {
        citation: sorted(ids)
        for citation, ids in sorted(citation_owner.items())
        if len(ids) > 1
    }

    seed_refs: list[dict] = []
    pending_identity: list[dict] = []
    for d in decisions:
        channels = set(d.get("channels") or ())
        if not (channels & CITE_CHANNELS):
            continue
        citation = str(d.get("citation") or "")
        decision_id = str(d.get("decision_id") or "")
        norm = _norm_ref(citation)
        hit = next(
            (
                seed
                for nseed, seed in seed_norm.items()
                if norm and nseed and min(len(norm), len(nseed)) >= 6
                and (norm in nseed or nseed in norm)
            ),
            None,
        )
        if hit is not None:
            seed_refs.append({"decision_id": decision_id, "citation": citation, "seed": hit})
        if str(d.get("detail_status") or "") == "pending":
            own = {str(d.get("docket_number") or "").strip(), decision_id}
            if citation not in own:
                pending_identity.append(
                    {"decision_id": decision_id, "citation": citation, "own_identity": sorted(x for x in own if x)}
                )

    return {
        "citation_duplicates": duplicates,
        "citation_channel_seed_refs": seed_refs,
        "pending_shell_identity": pending_identity,
        "citation_seeds_checked": seeds,
    }


#: Wall-clock fields a replay legitimately re-measures every run.  They are
#: removed from the hashed payload because their value is the measurement, not
#: the artifact.
TIMING_PATHS = (
    ("provenance", "latency_seconds"),
    ("provenance", "timing", "local_total_s"),
    ("provenance", "timing", "upstream_retrieval_s"),
    ("provenance", "timing", "local_map_s"),
    ("provenance", "retrieval", "remote", "latency_seconds"),
)

#: Machine-specific absolute cache roots.  These are NOT timings, and leaving
#: them inside the hashed payload is exactly the portability defect recorded in
#: results/audit/product/CYCLE_38785927063_GATE.json required_fixes[0] (D1):
#: the artifact's "reproducible identity" was one checkout path away from
#: reproducing, and the test that encoded the property only passed on the
#: machine that generated it.  They are replaced by a constant token, so a
#: differing cache root never changes the hash while a differing key count
#: still does.
CACHE_ROOT_PATHS = (
    ("provenance", "cache_stats", "root"),
    ("provenance", "retrieval", "remote", "cache_stats", "root"),
)

CACHE_ROOT_TOKEN = "<cache-root>"

#: Upstream OpenCaseLaw API paths recorded in provenance.stage_notes.*.endpoint.
#: They begin with "/" exactly like a filesystem path but are endpoint
#: identifiers — claim content — so they stay inside the hashed payload.
API_ENDPOINT_PREFIXES = ("/decisions", "/structure", "/citations", "/leading-cases")

#: Defence in depth for D1: any *other* absolute filesystem path that later
#: lands in a bundle is rewritten to this token too, so the next field someone
#: adds cannot silently re-break portability the same way.  ``https://`` URLs,
#: protocol-relative ``//host`` URLs and the API endpoints above are not paths.
ABSOLUTE_PATH_TOKEN = "<absolute-path>"
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")


def is_absolute_fs_path(value) -> bool:
    """True only for a single-machine filesystem path string."""
    if not isinstance(value, str) or len(value) < 2:
        return False
    if value.startswith("//"):  # protocol-relative URL, not a path
        return False
    return value.startswith("/") or bool(_WINDOWS_ABS_RE.match(value))


def is_machine_path(value) -> bool:
    """``is_absolute_fs_path`` minus the recorded upstream API endpoints."""
    if not is_absolute_fs_path(value):
        return False
    return not str(value).startswith(API_ENDPOINT_PREFIXES)


def _scrub_machine_paths(node):
    """Recursively replace machine-specific absolute paths with a constant token."""
    if isinstance(node, dict):
        return {k: _scrub_machine_paths(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_scrub_machine_paths(v) for v in node]
    if is_machine_path(node):
        return ABSOLUTE_PATH_TOKEN
    return node


def _pop_path(root: dict, path: tuple[str, ...]):
    node = root
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, dict):
        node.pop(path[-1], None)


def _portable_cache_root(root) -> str | None:
    """Report the cache root repo-relative when it lives inside the checkout.

    Keeps the CLI's own output stable across machines, for the same reason the
    hash excludes it; an out-of-tree root is still reported verbatim so the
    reviewer can see exactly where the replay read from.
    """
    if not isinstance(root, str) or not root:
        return root
    try:
        return str(Path(root).resolve().relative_to(REPO_ROOT))
    except (ValueError, OSError):
        return root


def canonical_payload(bundle: dict) -> dict:
    """The exact structure ``content_sha256`` hashes.

    Exposed as its own function (run 38807538467, required fix D1 of the
    cycle-38799024807 gate) so a test can name *which leaves* two replays
    disagree on instead of only seeing two opaque digests.  Timings are
    dropped, declared cache roots are tokenised, every other absolute
    filesystem path is scrubbed; nothing else is touched.
    """
    canonical = copy.deepcopy(bundle)
    for path in TIMING_PATHS:
        _pop_path(canonical, path)
    for path in CACHE_ROOT_PATHS:
        node = canonical
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and path[-1] in node:
            node[path[-1]] = CACHE_ROOT_TOKEN
    return _scrub_machine_paths(canonical)


def content_sha256(bundle: dict) -> str:
    """Path- and machine-independent sha256 of a query_result_bundle.

    The raw file hash can never match across runs because it embeds wall-clock
    timings; audit F2 of cycle 38779139471 compared raw hashes across machines
    and read the difference as a data difference.

    This is the identity that is supposed to be stable: same cache, same query,
    same code -> same value, *regardless of where the checkout lives*.  Three
    classes of value are excluded, and nothing else is:

    1. ``TIMING_PATHS`` - wall-clock measurements.
    2. ``CACHE_ROOT_PATHS`` - absolute cache roots, replaced by
       ``CACHE_ROOT_TOKEN`` (required fix D1 of cycle 38785927063).
    3. Any remaining machine-specific absolute filesystem path, replaced by
       ``ABSOLUTE_PATH_TOKEN``.  The recorded upstream API endpoints
       (``/citations``, ``/leading-cases``, ...) begin with ``/`` but are claim
       content, not locations, so they stay in the payload.

    Verified off the generating machine, not merely under a different
    ``PYTHONHASHSEED`` on the generating host: see
    ``reports/product/CYCLE_38789874982.md`` and the regression test
    ``product/tests/test_cache_non_orphan.py::
    test_content_hash_is_invariant_under_a_rewritten_cache_root``.

    ``cache_stats.n_keys`` deliberately STAYS in the payload (see
    ``CACHE_ROOT_PATHS``): a replay that silently ran against a partial cache
    must not hash like the real one.  Because the committed cache keeps
    growing with unrelated envelopes, the reproducibility test replays the
    claim query against the frozen subset in
    ``results/product/CYCLE_38759730609_cache_manifest.json`` — not against
    whatever the cache happens to hold today.  The identity function itself is
    unchanged by that (required fix D1, run 38807538467).
    """
    canonical = canonical_payload(bundle)
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Frozen claim-cache subset
#
# Required fix D1 of results/audit/product/CYCLE_38799024807_GATE.json
# (gate=REVISE, repair round 1): after run 38799024807 committed 123 live
# preflight envelopes (392 -> 515 keys) the frozen test
# ``test_claim_bundle_content_hash_matches_a_fresh_replay`` turned red, because
# ``content_sha256`` deliberately keeps ``cache_stats.n_keys`` in its payload
# (see CACHE_ROOT_PATHS: "a differing cache root never changes the hash while a
# differing key count still does").  A full-cache replay therefore reported a
# different identity for byte-identical claim content.
#
# The rule is NOT weakened here — ``n_keys`` stays inside the hash, so a replay
# run against an empty or partial cache still fails the equality.  What changes
# is the *cache the replay is pointed at*: the claim artifact is reproducible
# from the cache subset that existed when it was generated, frozen here as a
# manifest of content-addressed entries.  Appending unrelated envelopes (another
# query's live preflight, a new decision's citations) can no longer move the
# identity of an older claim artifact, because those envelopes are outside the
# frozen subset.  The other half of the property is asserted separately by
# ``test_claim_bundle_full_cache_replay_differs_only_in_cache_size``: against
# the *whole* growing cache the only leaves that may differ are the two
# ``n_keys`` counters.
# ---------------------------------------------------------------------------

CLAIM_BUNDLE_RELPATH = "results/product/CYCLE_38759730609_bundle.json"
CLAIM_CACHE_MANIFEST_RELPATH = "results/product/CYCLE_38759730609_cache_manifest.json"
CLAIM_CACHE_ROOT_RELPATH = "results/product/query_cache"

CLAIM_BUNDLE_PATH = REPO_ROOT / CLAIM_BUNDLE_RELPATH
CLAIM_CACHE_MANIFEST_PATH = REPO_ROOT / CLAIM_CACHE_MANIFEST_RELPATH

#: Exit codes for the manifest mode of this CLI (documented in the module
#: docstring): 8 = manifest integrity failure, 9 = subset replay identity
#: mismatch.  0 = verified.
EXIT_MANIFEST_INTEGRITY = 8
EXIT_SUBSET_IDENTITY_MISMATCH = 9


def load_claim_cache_manifest(path: Path | None = None) -> dict:
    """Read the frozen claim-cache manifest (default: the committed one)."""
    src = Path(path) if path else CLAIM_CACHE_MANIFEST_PATH
    with open(src, encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("schema") != "product-claim-cache-manifest/1":
        raise ValueError(f"unsupported claim-cache manifest schema in {src}")
    return manifest


def build_claim_cache_manifest(frozen_from_commit: str, *, out: Path | None = None) -> dict:
    """Freeze the cache entries a claim bundle was generated against.

    ``frozen_from_commit`` is the commit whose tree still holds exactly the
    cache the bundle recorded (``provenance.cache_stats.n_keys``).  The command
    that produced the committed manifest is recorded inside it, so the freeze
    is re-derivable from git history without this function being trusted.
    """
    import subprocess  # noqa: PLC0415  (build path only; git is CI-local)

    with open(CLAIM_BUNDLE_PATH, encoding="utf-8") as fh:
        bundle = json.load(fh)
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", frozen_from_commit, CLAIM_CACHE_ROOT_RELPATH],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    entries = []
    for relpath in sorted(p for p in listed if p.endswith(".json")):
        blob = (REPO_ROOT / relpath).read_bytes()
        entries.append({
            "key": Path(relpath).stem,
            "path": relpath,
            "sha256": hashlib.sha256(blob).hexdigest(),
        })
    n_keys = ((bundle.get("provenance") or {}).get("cache_stats") or {}).get("n_keys")
    manifest = {
        "schema": "product-claim-cache-manifest/1",
        "bundle": CLAIM_BUNDLE_RELPATH,
        "bundle_query": bundle.get("query"),
        "bundle_top_n": ((bundle.get("provenance") or {}).get("targets") or {}).get("target"),
        "bundle_content_sha256": content_sha256(bundle),
        "bundle_cache_n_keys": n_keys,
        "n_keys": len(entries),
        "frozen_from_commit": frozen_from_commit,
        "freeze_command": (
            "python product/replay_bundle.py --build-claim-cache-manifest "
            f"--frozen-from-commit {frozen_from_commit}"
        ),
        "verify_command": "python product/replay_bundle.py --check-claim-cache-manifest",
        "purpose": (
            "Frozen subset of results/product/query_cache that "
            f"{CLAIM_BUNDLE_RELPATH} was generated from. The offline claim "
            "replay is pointed at exactly these envelopes so that cache "
            "entries appended later by unrelated queries cannot change the "
            "recorded content_sha256 of this artifact. cache_stats.n_keys "
            "stays inside content_sha256; it is the subset, not the hash, that "
            "is frozen."
        ),
        "entries": entries,
    }
    if n_keys is not None and n_keys != len(entries):
        raise ValueError(
            f"freeze mismatch: bundle records n_keys={n_keys} but commit "
            f"{frozen_from_commit} holds {len(entries)} cache entries"
        )
    if out is not None:
        Path(out).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return manifest


def verify_claim_cache_manifest(manifest: dict | None = None) -> dict:
    """Check the frozen subset against the committed cache and the claim bundle.

    Append-tolerant by construction: the repository cache may hold *more*
    envelopes than the manifest (that is the growth that caused D1); every
    manifest entry must still exist with the recorded bytes, and the count must
    still equal the ``n_keys`` the claim bundle recorded when it was written.
    """
    man = manifest if manifest is not None else load_claim_cache_manifest()
    missing, mismatched = [], []
    for entry in man["entries"]:
        path = REPO_ROOT / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            mismatched.append(entry["path"])
    bundle = {}
    if CLAIM_BUNDLE_PATH.is_file():
        with open(CLAIM_BUNDLE_PATH, encoding="utf-8") as fh:
            bundle = json.load(fh)
    bundle_n_keys = ((bundle.get("provenance") or {}).get("cache_stats") or {}).get("n_keys")
    bundle_hash = content_sha256(bundle) if bundle else None
    findings = {
        "manifest": CLAIM_CACHE_MANIFEST_RELPATH,
        "n_entries": len(man["entries"]),
        "manifest_n_keys": man.get("n_keys"),
        "cache_files_present": sum(
            1 for _ in (REPO_ROOT / CLAIM_CACHE_ROOT_RELPATH).rglob("*.json")
        ),
        "missing": missing,
        "mismatched": mismatched,
        "bundle_cache_n_keys": bundle_n_keys,
        "bundle_content_sha256": bundle_hash,
        "manifest_bundle_content_sha256": man.get("bundle_content_sha256"),
    }
    findings["ok"] = bool(bundle) and not missing and not mismatched and (
        man.get("n_keys") == len(man["entries"]) == bundle_n_keys
        and man.get("bundle_content_sha256") == bundle_hash
    )
    return findings


def materialize_claim_cache(dest, manifest: dict | None = None) -> Path:
    """Copy the frozen subset into ``dest`` so a replay can be pointed at it."""
    import shutil  # noqa: PLC0415  (only used on this path)

    man = manifest if manifest is not None else load_claim_cache_manifest()
    root = Path(dest) / "claim_cache_subset"
    if root.exists():
        shutil.rmtree(root)
    for entry in man["entries"]:
        src = REPO_ROOT / entry["path"]
        target = root / Path(entry["path"]).relative_to(CLAIM_CACHE_ROOT_RELPATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return root


def replay_claim_bundle_against_frozen_cache(dest=None) -> tuple[dict, Path]:
    """Offline replay of the claim query with ``product_cache_dir`` pointed at
    the frozen subset.

    Returns ``(bundle, cache_root)``.  ``product.query.pipeline`` reads the
    cache root at configuration time, so the module-global binding is swapped
    for the duration of the replay and restored in ``finally`` — no frontier
    code is touched and the process is left exactly as it was found.
    """
    import tempfile  # noqa: PLC0415

    from product.query import pipeline as _pipeline  # noqa: PLC0415

    with open(CLAIM_BUNDLE_PATH, encoding="utf-8") as fh:
        committed = json.load(fh)
    query = committed["query"]
    top_n = int(((committed.get("provenance") or {}).get("targets") or {}).get("target") or 120)

    base = Path(dest) if dest else Path(tempfile.mkdtemp(prefix="lex_claim_cache_"))
    root = materialize_claim_cache(base)
    original = _pipeline.product_cache_dir
    _pipeline.product_cache_dir = lambda: root
    try:
        bundle = run_query_initial(query, top_n=top_n, retrieval_mode="offline")
    finally:
        _pipeline.product_cache_dir = original
    return bundle, root


def _cache_bodies(cache_root) -> list[dict]:
    """Every cached envelope body under ``cache_root``, reusing the adapter's reader."""
    try:
        from ocl_adapter.cache import FileCache  # noqa: PLC0415  (frontier adapter, sys.path set by product.query.pipeline)
    except Exception:  # adapter unavailable: disclosure degrades, the claim stands
        return []
    out = []
    for key in FileCache(cache_root).keys():
        entry = FileCache(cache_root).get(key)
        if not entry:
            continue
        body = entry.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                continue
        if isinstance(body, dict):
            out.append({"path": str(entry.get("path") or entry.get("url") or ""), "body": body})
    return out


def relation_recall(bundle: dict, cache_root=None) -> dict:
    """How much of the available on-map citation evidence the bundle kept.

    Advisory A1 of cycle 38785927063: the recovered relation set was presented
    as "the" typed-relation view without saying how much of the on-map evidence
    it covers.  This recomputes the denominator from the raw cached
    ``/citations`` envelopes for the bundle's own citation seeds, so the number
    ships with the artifact instead of living only in an audit report.

    ``fabricated`` must stay 0: every bundle edge has to appear in the raw
    upstream records.  ``recall`` below 1.0 is a disclosed coverage limit, not a
    fabrication, and the dropped edges are named.
    """
    decisions = bundle.get("decisions") or []
    on_map = {str(d.get("decision_id")) for d in decisions}
    shipped = {
        (str(r.get("source")), str(r.get("target")), str(r.get("kind") or ""))
        for r in (bundle.get("relations") or [])
    }
    notes = ((bundle.get("provenance") or {}).get("stage_notes") or {}).get("citations") or {}
    seeds = [
        str(e.get("seed"))
        for e in (notes.get("per_seed") or [])
        if isinstance(e, dict) and e.get("seed")
    ]
    raw: set[tuple[str, str, str]] = set()
    if seeds and cache_root is None:
        cache_root = product_cache_dir()
    for envelope in _cache_bodies(cache_root) if cache_root else []:
        if "/citations" not in envelope["path"]:
            continue
        body = envelope["body"]
        seed = str(body.get("decision_id") or "")
        if seed not in seeds:
            continue
        for edge in body.get("outgoing") or []:
            target = edge.get("target_decision_id") or edge.get("target_ref")
            if target:
                raw.add((seed, str(target), "citation"))
        for edge in body.get("incoming") or []:
            source = edge.get("source_decision_id") or edge.get("source_ref")
            if source:
                raw.add((str(source), seed, "citation"))

    available = {e for e in raw if e[0] in on_map and e[1] in on_map}
    kept = shipped & available
    return {
        "seeds": seeds,
        "raw_typed_edges": len(raw),
        "on_map_typed_edges": len(available),
        "in_bundle": len(kept),
        "recall": (len(kept) / len(available)) if available else None,
        "fabricated": sorted(f"{s}->{t}" for s, t, _ in (shipped - available)),
        "dropped_on_map": sorted(f"{s}->{t}" for s, t, _ in (available - shipped)),
        "scope_note": (
            "denominator is the typed edges recorded in the cached /citations envelopes "
            "for this query's own citation seeds whose BOTH endpoints reached the map; "
            "it is not a verified citation graph over the whole corpus"
        ),
    }


def field_coverage(decisions: list[dict]) -> dict:
    """Which per-decision claim fields are actually populated, not merely present.

    Advisory A7 of cycle 38785927063: ``source_url`` is a *required key* but is
    null on some rows, so "N/N rows are source-linked" holds through
    ``canonical_url`` and must not be read as both fields being populated.
    Reporting the split keeps the claim honest without weakening the key
    requirement in REQUIRED_DECISION_KEYS.
    """
    total = len(decisions)
    out: dict[str, dict] = {}
    for field in ("decision_id", "citation", "canonical_url", "source_url",
                  "court", "language", "decision_date", "x", "y", "cluster_id"):
        populated = sum(1 for d in decisions if d.get(field) not in (None, "", []))
        out[field] = {"populated": populated, "null_or_empty": total - populated, "of": total}
    return out


def inspect_bundle(bundle: dict) -> dict:
    """Return the machine-readable inspection used by the CLI and the tests."""
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    prov = bundle.get("provenance") or {}
    retrieval = prov.get("retrieval") or {}
    remote = retrieval.get("remote") or {}
    request_summary = remote.get("request_summary") or prov.get("request_summary") or {}
    dedupe = retrieval.get("dedupe") or {}
    timing = prov.get("timing") or {}

    synthetic_ids = [d.get("decision_id") for d in decisions if _looks_synthetic(d.get("decision_id"))]
    synthetic_labels = [
        c.get("label") for c in clusters if "test decision group" in str(c.get("label") or "").lower()
    ]
    missing_fields = []
    for i, d in enumerate(decisions):
        for f in REQUIRED_DECISION_FIELDS:
            if f not in d or d.get(f) is None or d.get(f) == "":
                missing_fields.append(f"decisions[{i}].{f}")
        for f in REQUIRED_DECISION_KEYS:
            if f not in d:
                missing_fields.append(f"decisions[{i}].{f} (key absent)")
        for f in ("x", "y"):
            if isinstance(d.get(f), float) and not math.isfinite(d[f]):
                missing_fields.append(f"decisions[{i}].{f} (non-finite)")
    decision_ids = {d.get("decision_id") for d in decisions}
    orphan_members = [
        c.get("cluster_id")
        for c in clusters
        for m in (c.get("member_ids") or [])
        if m not in decision_ids
    ]
    hosts = Counter(urllib.parse.urlparse(str(d.get("canonical_url") or "")).netloc for d in decisions)
    languages = Counter(str(d.get("language")) for d in decisions)
    citations = citation_findings(bundle)
    # A relation is only useful if the researcher can open both endpoints, so a
    # relation naming a decision that is not on the map is refused exactly like
    # an orphan cluster member (cycle-38779139471 typed-relation guard).
    dangling_relations = [
        {"index": i, "source": r.get("source"), "target": r.get("target"), "kind": r.get("kind")}
        for i, r in enumerate(bundle.get("relations") or [])
        if r.get("source") not in decision_ids or r.get("target") not in decision_ids
    ]
    relation_kinds = Counter(str(r.get("kind") or "?") for r in (bundle.get("relations") or []))

    return {
        "n_decisions": len(decisions),
        "n_clusters": len(clusters),
        "n_relations": len(bundle.get("relations") or []),
        "relation_kinds": dict(sorted(relation_kinds.items())),
        "dangling_relations": dangling_relations,
        "content_sha256": content_sha256(bundle),
        "relation_recall": relation_recall(bundle),
        "decision_field_coverage": field_coverage(decisions),
        "n_outliers": sum(1 for d in decisions if d.get("is_outlier") is True),
        "languages": dict(sorted(languages.items())),
        "hosts": dict(sorted(hosts.items())),
        "synthetic_decision_ids": synthetic_ids,
        "synthetic_cluster_labels": synthetic_labels,
        "missing_required_fields": missing_fields,
        "orphan_cluster_member_ids": orphan_members,
        "citation_duplicates": citations["citation_duplicates"],
        "citation_channel_seed_refs": citations["citation_channel_seed_refs"],
        "pending_shell_identity": citations["pending_shell_identity"],
        "citation_seeds_checked": citations["citation_seeds_checked"],
        "validate_bundle_errors": validate_bundle(bundle),
        "n_candidates": retrieval.get("n_candidates"),
        "dedupe": dedupe,
        "degraded": bool(prov.get("degraded")) if "degraded" in prov else None,
        "request_summary": request_summary,
        "targets": prov.get("targets"),
        "stages": prov.get("stages"),
        "base_url": prov.get("base_url") or remote.get("base_url"),
        "query_variants": [
            (
                {
                    "variant_id": v.get("variant_id"),
                    "kind": v.get("kind"),
                    "language_filter": v.get("language_filter"),
                    "text": v.get("text"),
                }
                if isinstance(v, dict)
                else {"text": str(v)}
            )
            for v in (prov.get("query_variants") or bundle.get("query_variants") or [])
        ],
        "searches": [
            {
                "stage": s.get("stage"),
                "variant_id": s.get("variant_id"),
                "language_filter": s.get("language_filter"),
                "page": s.get("page"),
                "limit": s.get("limit"),
                "offset": s.get("offset"),
                "returned": s.get("returned"),
                "total": s.get("total"),
            }
            for s in (prov.get("searches") or [])
        ],
        "stage_notes": prov.get("stage_notes"),
        "timing": timing,
        "latency_seconds": prov.get("latency_seconds"),
        "answer_status": (bundle.get("answer") or {}).get("status"),
        "answer_method": (bundle.get("answer") or {}).get("method"),
        "cache_root": _portable_cache_root((prov.get("cache_stats") or {}).get("root")),
        "cache_keys": (prov.get("cache_stats") or {}).get("n_keys"),
        "hashed_payload_paths": hashed_payload_paths(bundle),
    }


def hashed_payload_paths(bundle: dict) -> dict:
    """What ``content_sha256`` had to neutralise, and what it deliberately kept.

    ``content_sha256`` rewrites every machine path to a constant token, so the
    hash stays portable; this lists those locations so a reviewer can see *what*
    was neutralised instead of trusting the hash.  ``api_endpoints`` are the
    recorded upstream paths (``/citations``, ``/leading-cases``, ...) that begin
    with ``/`` but are claim content, so they stay inside the payload and are
    listed to show they were not swept up with the machine paths.
    """
    canonical = copy.deepcopy(bundle)
    for path in TIMING_PATHS:
        _pop_path(canonical, path)

    machine: list[str] = []
    endpoints: list[str] = []

    def walk(node, where: str):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")
        elif is_machine_path(node):
            machine.append(where)
        elif is_absolute_fs_path(node):
            endpoints.append(where)

    walk(canonical, "")
    return {
        "machine_paths": sorted(machine),
        "api_endpoints": sorted(endpoints),
        "timings_dropped": len(TIMING_PATHS),
    }


def genuine(insp: dict) -> bool:
    return not (
        insp["synthetic_decision_ids"]
        or insp["synthetic_cluster_labels"]
        or insp["missing_required_fields"]
        or insp["orphan_cluster_member_ids"]
        or insp["citation_duplicates"]
        or insp["citation_channel_seed_refs"]
        or insp["pending_shell_identity"]
        or insp["dangling_relations"]
        or insp["relation_recall"]["fabricated"]
        or insp["validate_bundle_errors"]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=False, help="recorded research query")
    ap.add_argument("--top-n", type=int, default=120)
    ap.add_argument("--out", default=None, help="write the replayed bundle here")
    ap.add_argument("--retrieval-mode", default="offline", choices=["offline", "live"])
    ap.add_argument(
        "--check-claim-cache-manifest", action="store_true",
        help="verify the frozen claim-cache subset and that it reproduces the "
             "committed claim bundle's content_sha256 (no --query needed)",
    )
    ap.add_argument(
        "--build-claim-cache-manifest", action="store_true",
        help="(re)freeze results/product/CYCLE_38759730609_cache_manifest.json "
             "from --frozen-from-commit after the claim bundle is regenerated",
    )
    ap.add_argument("--frozen-from-commit", default=None,
                    help="commit whose cache tree the claim bundle was generated from")
    ap.add_argument("--manifest-out", default=None,
                    help="where to write a rebuilt manifest (default: the committed path)")
    args = ap.parse_args(argv)

    if args.check_claim_cache_manifest:
        findings = verify_claim_cache_manifest()
        print(json.dumps(findings, ensure_ascii=False, indent=1))
        if not findings["ok"]:
            return EXIT_MANIFEST_INTEGRITY
        bundle, root = replay_claim_bundle_against_frozen_cache()
        committed_hash = findings["bundle_content_sha256"]
        replay_hash = content_sha256(bundle)
        report = {
            "committed_content_sha256": committed_hash,
            "frozen_subset_replay_sha256": replay_hash,
            "frozen_subset_cache_root": _portable_cache_root(str(root)),
            "frozen_subset_n_keys": (bundle.get("provenance") or {}).get("cache_stats", {}).get("n_keys"),
            "network_calls": ((bundle.get("provenance") or {}).get("request_summary") or {}).get("network_calls"),
            "match": replay_hash == committed_hash,
        }
        print(json.dumps(report, ensure_ascii=False, indent=1))
        # The subset lives in a scratch tree, never inside results/product/.
        shutil.rmtree(root.parent, ignore_errors=True)
        return 0 if report["match"] else EXIT_SUBSET_IDENTITY_MISMATCH

    if args.build_claim_cache_manifest:
        if not args.frozen_from_commit:
            print(json.dumps({"error": "frozen_from_commit_required"}))
            return 2
        out = Path(args.manifest_out) if args.manifest_out else CLAIM_CACHE_MANIFEST_PATH
        manifest = build_claim_cache_manifest(args.frozen_from_commit, out=out)
        print(json.dumps({
            "written": str(out),
            "n_keys": manifest["n_keys"],
            "bundle_content_sha256": manifest["bundle_content_sha256"],
            "frozen_from_commit": manifest["frozen_from_commit"],
        }, ensure_ascii=False, indent=1))
        return 0

    if not args.query:
        print(json.dumps({"error": "query_required_without_manifest_mode"}))
        return 2

    bundle = run_query_initial(args.query, top_n=args.top_n, retrieval_mode=args.retrieval_mode)
    insp = inspect_bundle(bundle)

    if insp["validate_bundle_errors"]:
        print(json.dumps({"error": "validate_bundle_failed", "errors": insp["validate_bundle_errors"]}, indent=2))
        return 3
    if insp["synthetic_decision_ids"] or insp["synthetic_cluster_labels"]:
        print(json.dumps({"error": "synthetic_content_refused", "inspection": insp}, indent=2))
        return 4
    if insp["missing_required_fields"]:
        print(json.dumps({"error": "missing_claim_fields", "missing": insp["missing_required_fields"][:20]}, indent=2))
        return 5
    if insp["citation_duplicates"] or insp["citation_channel_seed_refs"] or insp["pending_shell_identity"]:
        print(json.dumps({
            "error": "foreign_citation_content_refused",
            "citation_duplicates": insp["citation_duplicates"],
            "citation_channel_seed_refs": insp["citation_channel_seed_refs"][:20],
            "pending_shell_identity": insp["pending_shell_identity"][:20],
        }, ensure_ascii=False, indent=2))
        return 6
    if insp["dangling_relations"]:
        print(json.dumps({
            "error": "dangling_relation_refused",
            "dangling_relations": insp["dangling_relations"][:20],
        }, ensure_ascii=False, indent=2))
        return 7

    out_path = Path(args.out) if args.out else None
    if out_path is not None:
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        out_path.write_text(payload, encoding="utf-8")
        try:
            insp["out"] = str(out_path.relative_to(REPO_ROOT))
        except ValueError:
            # Absolute --out outside the repository (scratch/inspection runs):
            # report the path as given instead of crashing after the write.
            insp["out"] = str(out_path)
        insp["out_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        insp["out_bytes"] = len(payload.encode("utf-8"))
    insp["genuine"] = genuine(insp)
    print(json.dumps(insp, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
