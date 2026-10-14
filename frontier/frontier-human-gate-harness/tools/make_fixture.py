#!/usr/bin/env python3
"""Deterministic offline synthesizer for the harness `query_result_bundle` fixture.

Charter v1 (frontier-human-gate-harness) dependency: "A frozen query_result_bundle
fixture with >=100 decisions, synthesized deterministically from the accepted
retrieval fixtures (results/frontier/frontier-query-retrieval/fixtures/ in the
accepted lab/frontier/frontier-query-retrieval branch) rather than duplicating
live retrieval."

What is copied verbatim from the accepted fixtures
    decision_id, court, language, decision_date, docket_number, citation,
    canonical_url, source_url, snippet/regeste/title, relevance_score.
What is derived by declared deterministic rules (never invented legal content)
    rank            ordering rule: relevance_score DESC, decision_id ASC
    cluster_id/x/y  TEST geometry: court x language groups, golden-angle layout
    counter_status  literal "unclassified" for every decision - no
                    counter-authority classification is ever claimed here.
    relations       [] (the fixture makes no relation claim)

Usage
    python3 tools/make_fixture.py                # write fixture + provenance
    python3 tools/make_fixture.py --check        # byte-compare, write nothing
    python3 tools/make_fixture.py --source DIR   # override accepted source root

Exit codes: 0 ok, 1 --check mismatch, 3 source/contract defect (missing field).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HARNESS_ROOT = HERE.parent
REPO_ROOT = HARNESS_ROOT.parents[1]
FIXTURE_DIR = REPO_ROOT / "results" / "frontier" / "frontier-human-gate-harness" / "fixtures"
FIXTURE_NAME = "query_result_bundle_kuendigung_101.json"
PROVENANCE_NAME = "FIXTURE_PROVENANCE.json"

MIN_DECISIONS = 100
REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                "decisions", "clusters", "relations", "provenance"]
REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                     "provenance", "snippet", "cluster_id", "x", "y",
                     "counter_status", "canonical_url", "citation"]
# Fields a conventional ranked list needs (charter stop/promote rule).
CONVENTIONAL_FIELDS = ["rank", "decision_id", "court", "decision_date",
                       "language", "citation", "canonical_url", "snippet"]
GOLDEN_ANGLE = 2.399963229728653

SOURCE_CANDIDATES = [
    REPO_ROOT / "results" / "frontier" / "frontier-query-retrieval" / "fixtures",
    Path("/tmp/lex_accepted/core/product/results/frontier/frontier-query-retrieval/fixtures"),
    Path("/tmp/lex_accepted/core/evaluation/results/frontier/frontier-query-retrieval/fixtures"),
    Path("/tmp/lex_accepted/frontier/frontier-query-retrieval/fixtures"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def resolve_source(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_dir():
            raise SystemExit(f"3: --source does not exist or is not a directory: {p}")
        return p
    for cand in SOURCE_CANDIDATES:
        if cand.is_dir():
            return cand.resolve()
    raise SystemExit(
        "3: no accepted retrieval fixture root found. Looked for:\n  "
        + "\n  ".join(str(c) for c in SOURCE_CANDIDATES)
        + "\nPass --source <dir>. The accepted source lives on branch "
        "lab/frontier/frontier-query-retrieval at results/frontier/frontier-query-retrieval/fixtures/."
    )


def _load_body(entry: dict) -> Any:
    body = entry.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return None
    return body


def load_candidates(source: Path) -> tuple[list[dict], list[dict], dict | None]:
    """Read accepted OCL cache entries -> unique candidate records + file digests.

    De-duplication key: decision_id. On collision the record with the higher
    relevance_score wins; on a further tie the lexicographically smaller source
    cache file path wins (both deterministic, no wall-clock input).
    """
    meta_path = source / "FIXTURE_META.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else None

    best: dict[str, dict] = {}
    tiebreak: dict[str, str] = {}
    touched_files: set[str] = set()

    for path in sorted(source.glob("cache/*/*.json")):
        rel = f"cache/{path.parent.name}/{path.name}"
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        body = _load_body(entry)
        if not isinstance(body, dict):
            continue
        results = body.get("results")
        if not isinstance(results, list):
            continue
        params = entry.get("params") or {}
        param_summary = "&".join(f"{k}={params[k]}" for k in sorted(params))
        for rec in results:
            if not isinstance(rec, dict):
                continue
            did = rec.get("decision_id")
            if not did or not isinstance(did, str):
                continue
            has_citation = any(rec.get(f"citation_string_{lg}") for lg in ("de", "fr", "it"))
            if not (rec.get("canonical_url") or has_citation):
                continue
            try:
                score = float(rec.get("relevance_score") or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            enriched = dict(rec)
            enriched["_score"] = score
            enriched["_src_rel"] = rel
            enriched["_src_param"] = param_summary
            prev = best.get(did)
            if prev is None or (score, ) > (prev["_score"], ) or (
                    score == prev["_score"] and rel < tiebreak[did]):
                best[did] = enriched
                tiebreak[did] = rel
                touched_files.add(rel)

    digest_by_rel = {
        f"cache/{p.parent.name}/{p.name}": sha256_bytes(p.read_bytes())
        for p in sorted(source.glob("cache/*/*.json"))
    }
    used_counts: dict[str, int] = {}
    for rec in best.values():
        used_counts[rec["_src_rel"]] = used_counts.get(rec["_src_rel"], 0) + 1
    file_rows = [{"path": rel, "sha256": digest_by_rel.get(rel), "records_used": count}
                 for rel, count in sorted(used_counts.items()) if rel in touched_files]
    if meta_path.is_file():
        file_rows.insert(0, {"path": "FIXTURE_META.json",
                             "sha256": sha256_bytes(meta_path.read_bytes()),
                             "records_used": 0})
    return list(best.values()), file_rows, meta


def citation_for(rec: dict) -> str:
    lang = (rec.get("language") or "").lower()
    order = [f"citation_string_{lang}"] if lang in ("de", "fr", "it") else []
    order += ["citation_string_de", "citation_string_fr", "citation_string_it"]
    seen: set[str] = set()
    for key in order:
        if key in seen:
            continue
        seen.add(key)
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def anchor_from_key(key: str) -> tuple[float, float]:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    ax = int.from_bytes(digest[0:4], "big") / 0xFFFFFFFF
    ay = int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF
    return round(-0.7 + 1.4 * ax, 6), round(-0.7 + 1.4 * ay, 6)


def build(source: Path) -> tuple[dict, dict]:
    candidates, file_rows, meta = load_candidates(source)
    if len(candidates) < MIN_DECISIONS:
        raise SystemExit(
            f"3: accepted fixtures yielded {len(candidates)} usable decisions (<{MIN_DECISIONS}). "
            "Product contract defect: source fixtures lack decision_id/citation/canonical_url coverage."
        )

    # --- conventional-field contract check: never invent a missing value -----
    # "Missing" means the accepted source record does not carry the key at all.
    # A key that exists with an empty value (e.g. one decision with no date) is
    # kept verbatim and counted in provenance -- dropping or filling it would
    # hide a real source condition.
    dropped: list[dict] = []
    usable: list[dict] = []
    for rec in candidates:
        missing = missing_source_keys(rec)
        if missing:
            dropped.append({"decision_id": rec.get("decision_id"), "missing": missing})
        else:
            usable.append(rec)
    if dropped:
        fields = sorted({m for d in dropped for m in d["missing"]})
        print(f"NOTE: dropped {len(dropped)} accepted record(s) lacking source key(s): "
              f"{', '.join(fields)} -> {[d['decision_id'] for d in dropped]}", file=sys.stderr)
    if len(usable) < MIN_DECISIONS:
        fields = sorted({m for d in dropped for m in d["missing"]}) or ["<none>"]
        raise SystemExit(
            "3: PRODUCT CONTRACT DEFECT - after dropping records whose accepted source "
            f"entry lacks a conventional ranked-list field, only {len(usable)} decisions "
            f"remain (<{MIN_DECISIONS}). Exact missing bundle field(s): {', '.join(fields)}. "
            "Charter stop rule: terminate instead of inventing data."
        )

    # --- rank: relevance_score DESC, decision_id ASC (fixture ordering rule) --
    usable.sort(key=lambda r: (-r["_score"], r["decision_id"]))

    # --- clusters: court x language groups (deterministic TEST geometry) -----
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in usable:
        court = str(rec.get("court") or "unknown")
        lang = str(rec.get("language") or "unknown")
        groups.setdefault((court, lang), []).append(rec)
    group_keys = sorted(groups)
    cluster_id_of: dict[tuple[str, str], int] = {k: i for i, k in enumerate(group_keys)}
    position_in_group: dict[str, int] = {}
    for key in group_keys:
        for pos, rec in enumerate(groups[key]):
            position_in_group[rec["decision_id"]] = pos

    decisions: list[dict] = []
    empty_values: dict[str, list[str]] = {}
    lang_fallback: list[str] = []
    for idx, rec in enumerate(usable, start=1):
        court = str(rec.get("court") or "unknown")
        lang = str(rec.get("language") or "unknown")
        if not rec.get("language"):
            lang_fallback.append(rec["decision_id"])
        key = (court, lang)
        cid = cluster_id_of[key]
        members = groups[key]
        pos = position_in_group[rec["decision_id"]]
        ax, ay = anchor_from_key(f"{court}|{lang}")
        radius = 0.06 + 0.10 * math.sqrt((pos + 1) / max(1, len(members)))
        angle = pos * GOLDEN_ANGLE
        x = round(max(-1.0, min(1.0, ax + radius * math.cos(angle))), 6)
        y = round(max(-1.0, min(1.0, ay + radius * math.sin(angle))), 6)
        snippet = rec.get("snippet") or rec.get("regeste") or rec.get("title") or ""
        decision = {
            "decision_id": rec["decision_id"],
            "court": court,
            "court_name": rec.get("court_name") or "",
            "language": lang,
            "decision_date": str(rec.get("decision_date") or ""),
            "docket_number": str(rec.get("docket_number") or ""),
            "rank": idx,
            "score": round(rec["_score"], 6),
            "provenance": f"ocl_fixture:{rec['_src_rel']}#{rec['_src_param']}",
            "snippet": str(snippet),
            "regeste": str(rec.get("regeste") or ""),
            "title": str(rec.get("title") or ""),
            "citation": citation_for(rec),
            "canonical_url": str(rec.get("canonical_url") or ""),
            "source_url": str(rec.get("source_url") or ""),
            "cluster_id": cid,
            "x": x,
            "y": y,
            "counter_status": "unclassified",
            "counter_evidence": None,
            "is_outlier": False,
            "detail_status": "fixture",
        }
        for field in CONVENTIONAL_FIELDS:
            value = decision[field]
            if value in ("", None) or (field == "rank" and value == 0):
                empty_values.setdefault(field, []).append(decision["decision_id"])
        decisions.append(decision)

    clusters = []
    for key in group_keys:
        cid = cluster_id_of[key]
        court, lang = key
        clusters.append({
            "cluster_id": cid,
            "label": f"[FIXTURE] {court} · {lang} — groupe déterministe de test "
                     "(règle tribunal×langue), pas une sémantique produit",
            "size": len(groups[key]),
            "court": court,
            "language": lang,
        })

    query = "Kündigung Mietvertrag Mietrecht"
    variants: list[str] = []
    if isinstance(meta, dict):
        query = str(meta.get("query") or query)
        searches = meta.get("searches") if isinstance(meta.get("searches"), list) else []
        variants = sorted({str(s.get("variant_id")) for s in searches
                           if isinstance(s, dict) and s.get("variant_id")})
    if not variants:
        variants = [f"fixture:{query}"]
    recorded_at = meta.get("recorded_at") if isinstance(meta, dict) else None

    lang_counts: dict[str, int] = {}
    for d in decisions:
        lang_counts[d["language"]] = lang_counts.get(d["language"], 0) + 1

    inputs_digest = sha256_bytes("".join(
        f"{r['path']}:{r['sha256']}\n" for r in sorted(file_rows, key=lambda r: r["path"])
    ).encode("utf-8"))

    bundle = {
        "bundle_version": "1.0",
        "query": query,
        "query_variants": variants,
        "answer": {
            "status": "fixture",
            "prose": "",
            "method": "fixture: aucune génération hors-ligne dans ce jeu de données",
            "model": None,
            "cited_decision_ids": [],
        },
        "decisions": decisions,
        "clusters": clusters,
        "relations": [],
        "provenance": {
            "generator": "frontier/frontier-human-gate-harness/tools/make_fixture.py",
            "team_id": "frontier-human-gate-harness",
            "charter_version": 1,
            "fixture_notice": (
                "FIXTURE. decision_id/court/date/language/citation/canonical_url/snippet are "
                "verbatim OpenCaseLaw records from the accepted retrieval fixtures; cluster_id/x/y "
                "are deterministic TEST geometry (court x language rule); counter_status is the "
                "literal 'unclassified' for every decision (no counter-authority classification is "
                "claimed); rank is a fixture ordering rule (relevance_score DESC, decision_id ASC), "
                "not product reranking; relations is empty by construction."
            ),
            "source_root": str(source),
            "source_branch": "lab/frontier/frontier-query-retrieval (results/frontier/frontier-query-retrieval/fixtures/)",
            "source_files": sorted(file_rows, key=lambda r: r["path"]),
            "source_inputs_sha256": inputs_digest,
            "recorded_at_source": recorded_at,
            "counts": {
                "decisions": len(decisions),
                "clusters": len(clusters),
                "languages": dict(sorted(lang_counts.items())),
                "min_rank": 1,
                "max_rank": len(decisions),
                "dropped_records_missing_source_key": len(dropped),
                "dropped_decision_ids": sorted(d["decision_id"] or "" for d in dropped),
                "language_fallback_unknown_ids": sorted(lang_fallback),
            },
            "empty_conventional_values": {k: sorted(v) for k, v in sorted(empty_values.items())},
            "rules": {
                "rank": "relevance_score DESC, decision_id ASC (fixture ordering rule)",
                "citation_fallback": "citation_string_<lang> then de, fr, it",
                "cluster": "group by (court, language), groups sorted lexicographically",
                "geometry": "sha256-derived cluster anchor + golden-angle radius, rounded to 6 decimals",
                "counter_status": "literal 'unclassified' for all decisions — no classification claimed",
                "dropped_records": "records whose accepted source entry lacks a conventional "
                                   "ranked-list key are dropped and listed, never filled in",
                "empty_values": "a source key present with an empty value is kept verbatim "
                                "and listed under empty_conventional_values",
            },
        },
    }

    prov = {
        "fixture_file": FIXTURE_NAME,
        "generator": "frontier/frontier-human-gate-harness/tools/make_fixture.py",
        "source_root_used": str(source),
        "source_inputs_sha256": inputs_digest,
        "n_decisions": len(decisions),
        "n_clusters": len(clusters),
        "how_to_regenerate": (
            "cd frontier/frontier-human-gate-harness && python3 tools/make_fixture.py  "
            "(verify without writing: python3 tools/make_fixture.py --check)"
        ),
        "accepted_source_branch": (
            "lab/frontier/frontier-query-retrieval @ results/frontier/frontier-query-retrieval/fixtures/ "
            "(the same accepted fixtures are also present in the accepted lab/product worktree)"
        ),
        "convention_fields_checked": CONVENTIONAL_FIELDS,
    }
    return bundle, prov


def missing_source_keys(rec: dict) -> list[str]:
    """Conventional-list fields the accepted source record does not carry at all."""
    missing: list[str] = []
    if "decision_id" not in rec:
        missing.append("decision_id")
    if "court" not in rec:
        missing.append("court")
    if "decision_date" not in rec:
        missing.append("decision_date")
    if "language" not in rec:
        missing.append("language")
    if not any(k in rec for k in ("citation_string_de", "citation_string_fr", "citation_string_it")):
        missing.append("citation")
    if "canonical_url" not in rec:
        missing.append("canonical_url")
    # rank is assigned by the declared fixture ordering rule, never read from source
    return missing


def serialize(bundle: dict) -> bytes:
    return (json.dumps(bundle, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def canonical_bundle_sha256(bundle: dict) -> str:
    """Hash of the canonical JSON form (the hash the harness CLI records)."""
    canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def serialize_prov(prov: dict, fixture_bytes: bytes, generator_bytes: bytes) -> bytes:
    prov = dict(prov)
    prov["fixture_sha256"] = sha256_bytes(fixture_bytes)
    prov["fixture_file_sha256"] = sha256_bytes(fixture_bytes)
    prov["bundle_canonical_sha256"] = canonical_bundle_sha256(
        json.loads(fixture_bytes.decode("utf-8")))
    prov["hash_semantics"] = (
        "fixture_sha256 / fixture_file_sha256 = sha256 of the fixture file BYTES; "
        "bundle_canonical_sha256 = sha256 of the canonical JSON object "
        "(sorted keys, separators ',' ':', ensure_ascii=False), which is the value "
        "recorded as bundle_sha256 in session capture records. The two differ by design."
    )
    prov["generator_sha256"] = sha256_bytes(generator_bytes)
    return (json.dumps(prov, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def local_validate(bundle: dict) -> list[str]:
    errors = [f"missing top-level key: {k}" for k in REQUIRED_TOP if k not in bundle]
    if errors:
        return errors
    if not isinstance(bundle["decisions"], list) or not bundle["decisions"]:
        return ["decisions must be a non-empty list"]
    ids: set[str] = set()
    for i, d in enumerate(bundle["decisions"]):
        for key in REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)  # type: ignore[arg-type]
    for c in bundle.get("clusters", []):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster missing id/label: {c}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=None, help="accepted retrieval fixtures root")
    ap.add_argument("--check", action="store_true",
                    help="regenerate in memory and byte-compare with the committed fixture; write nothing")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    source = resolve_source(args.source)
    bundle, prov = build(source)
    errors = local_validate(bundle)
    if errors:
        print("3: bundle failed the product bundle contract: " + "; ".join(errors), file=sys.stderr)
        return 3
    if len(bundle["decisions"]) < MIN_DECISIONS:
        print(f"3: only {len(bundle['decisions'])} decisions (<{MIN_DECISIONS})", file=sys.stderr)
        return 3

    fixture_bytes = serialize(bundle)
    generator_bytes = Path(__file__).read_bytes()
    prov_bytes = serialize_prov(prov, fixture_bytes, generator_bytes)
    fixture_path = FIXTURE_DIR / FIXTURE_NAME
    prov_path = FIXTURE_DIR / PROVENANCE_NAME

    if args.check:
        if not fixture_path.is_file():
            print(f"1: committed fixture missing: {fixture_path}", file=sys.stderr)
            return 1
        current = fixture_path.read_bytes()
        if current == fixture_bytes:
            print(f"OK byte-identical ({len(fixture_bytes)} bytes, "
                  f"sha256={sha256_bytes(fixture_bytes)}, "
                  f"n={len(bundle['decisions'])})")
            return 0
        print(f"MISMATCH: committed sha256={sha256_bytes(current)} "
              f"regenerated sha256={sha256_bytes(fixture_bytes)}", file=sys.stderr)
        return 1

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path.write_bytes(fixture_bytes)
    prov_path.write_bytes(prov_bytes)
    summary = {
        "fixture": str(fixture_path),
        "fixture_sha256": sha256_bytes(fixture_bytes),
        "provenance": str(prov_path),
        "n_decisions": len(bundle["decisions"]),
        "n_clusters": len(bundle["clusters"]),
        "languages": bundle["provenance"]["counts"]["languages"],
        "source_root": str(source),
        "source_inputs_sha256": prov["source_inputs_sha256"],
        "validation_errors": errors,
    }
    if not args.quiet:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
