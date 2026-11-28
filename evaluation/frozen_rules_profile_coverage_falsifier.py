#!/usr/bin/env python3
"""FAST-MVP frozen-rules PROFILE-COVERAGE counter-authority falsifier (direction v68).

What this instrument measures (and nothing else)
------------------------------------------------
The shipped counter-authority seam resolves, for every query it labels, an
**anchor profile** from the frozen rubric ``product/frozen/RULES_LABEL.json``
(sha256 ``4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608``)
through ``product.query.counter_anchor.resolve_anchor_profile``.  The rubric
carries FIVE frozen anchor profiles; the MVP's flagship offline/server query
family carries FIVE query groups.  Core Product's accepted cycle report
*disclosed* that one flagship query resolves to a domain-mismatched profile and
one resolves to ``None`` and **transferred the coverage question to this lane**
(product ordered work item 6, "frozen-rules profile coverage gap - DISCLOSED and
TRANSFERRED to evaluation").

This instrument converts that disclosure into an independent, executable,
falsifiable measurement on the accepted product bytes:

* **H1 coverage** - does a fresh resolution (executed here, never copied from
  Product's provenance) return a non-``None`` frozen profile for every flagship
  query group of the shipped content-filter family?
* **H2a norm alignment** - for each group whose profile resolves, do the
  profile's frozen *norm-bearing* pivot anchors (e.g. ``257d``, ``102``) appear
  as ``Art. <token>`` citations in that query's OWN ``query`` +
  ``query_variants`` text?  This is an independent domain signal: the resolver
  itself only compares token overlap between the query and the profile, so a
  profile can win the resolver's overlap score while sharing no legal norm with
  the question it is attached to.
* **H2b corpus evidence (REPORT-ONLY, never verdict-bearing)** - the same
  intersection computed over the union of the retrieved decisions' own
  ``regeste``/``title``/``snippet`` text, plus a whole-token sensitivity variant
  of H2a.  Both are published side by side with H2a precisely because two
  definitions of "the query's own norm text" exist; no number is silently
  preferred (factory-wide requirement 12).
* **H3 shipped-provenance agreement** - does the fresh resolution equal the
  ``provenance.counter_evidence_span.anchor_profile`` recorded by the shipped
  bundle for every bundle?  A disagreement would be a shipped-honesty defect.

Claim ceiling
-------------
This benchmark proves only that the SHIPPED anchor-profile coverage/alignment of
the frozen-rules seam is or is not complete over the frozen flagship family, as
measured by this frozen protocol on committed bytes.  It does NOT prove that any
decision IS supporting, contrary or limiting; it does NOT score the frozen
``RULES_LABEL`` rubric, any frozen bar, threshold or verdict contract; it does
NOT re-run, move or replace the benchmark of record (mapping-free falsifier,
``PRODUCT_FALSIFIED`` on packet-of-record 39319405429); it does NOT issue a
serve verdict, admit a packet or make any jurist-usefulness claim; it runs NO
universal-174k benchmark; it makes NO recall claim against a live baseline.

Freeze discipline
-----------------
``evaluation/FROZEN_RULES_PROFILE_COVERAGE_<RUN>_HYPOTHESIS_V1.json`` and its
companion ``..._FREEZE_V1.json`` are committed BEFORE this instrument is first
executed for claim-bearing purposes.  Nothing frozen there may be edited after
execution begins; an edit invalidates the run.

Import discipline
-----------------
The product seam module is loaded **by file path** (with its sha256 re-hashed
against the freeze pin) so that importing it does not pull the
``product.query`` package ``__init__`` -> ``pipeline`` -> ``qmap`` -> ``numpy``
chain.  The seam's own logic (``resolve_anchor_profile`` /
``load_frozen_rules``) is executed unmodified; nothing is re-implemented and
nothing is re-tuned.

Usage
-----
    python3 -m evaluation.frozen_rules_profile_coverage_falsifier \
        --run-id <RUN> \
        --hypothesis evaluation/FROZEN_RULES_PROFILE_COVERAGE_<RUN>_HYPOTHESIS_V1.json \
        --freeze evaluation/FROZEN_RULES_PROFILE_COVERAGE_<RUN>_FREEZE_V1.json \
        --product-mount /tmp/lex_accepted/product \
        --out results/evaluation/frozen_rules_profile_coverage/<RUN>.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lex-evaluation-frozen-rules-profile-coverage-falsifier/1"
INSTRUMENT = "evaluation/frozen_rules_profile_coverage_falsifier.py"

#: The frozen rubric identity.  Read only; never edited, never re-derived.
FROZEN_RULES_SHA256 = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
#: The frozen retrieval benchmark spec that pins the flagship query family.
FROZEN_SPEC_SHA256 = (
    "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
)

#: Claim-bearing flagship groups = the four frozen MVP questions plus the
#: shipped server/served group that is a member of the frozen 15-family.
FLAGSHIP_GROUPS = (
    "rent-default",
    "business-judgment-rule",
    "corporate-criminal-liability",
    "petty-theft-dismissal",
    "served",
)

SELECTION_RULE_FROZEN = (
    "Every bundle at the frozen product mount under "
    "results/product/{offline_slice,server_slice}/*/*.bundle.json whose "
    "provenance.counter_evidence_span.content_filter is a non-empty object "
    "(the fixed-path regeneration marker). Selection uses provenance PRESENCE "
    "only and is independent of any profile resolution or alignment result. "
    "This is the same marker rule the accepted post-repair family population "
    "(run 40258497460) used."
)

#: ``Art. 257d`` / ``Artikel 102`` style Swiss norm citation, after
#: accent-stripping and punctuation collapsing (``Art. 257d`` -> ``art 257d``).
ART_NORM_RE = re.compile(r"\bart\s+(\d+[a-z]{0,3})\b")
#: A frozen pivot token counts as "norm-bearing" when it contains a digit.
DIGIT_RE = re.compile(r"\d")

#: Text fields of a retrieved decision used for the REPORT-ONLY corpus probe.
CORPUS_FIELDS = ("regeste", "title", "snippet")

#: Number of distinct decisions contributed per bundle to the report-only
#: corpus probe (rank order; deterministic).
CORPUS_TOP_N = 50


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize(text: str) -> str:
    """Deterministic accent-stripped, lowercased, space-collapsed text.

    Used ONLY for locating frozen norm tokens in text that is already public in
    the committed artifacts.  It is not the frozen rubric normaliser and it
    never rewrites any input.
    """
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def art_norm_tokens(text: str) -> set[str]:
    """Norm tokens quoted as ``Art. <token>`` inside ``text``."""
    return set(ART_NORM_RE.findall(normalize(text)))


def whole_word_tokens(text: str, candidates: set[str]) -> set[str]:
    """Subset of ``candidates`` appearing as whole whitespace-delimited words."""
    words = set(normalize(text).split())
    return {c for c in candidates if c in words}


def load_seam(mount: Path) -> Any:
    """Load ``product/query/counter_anchor.py`` by file path (stdlib only)."""
    target = mount / "product" / "query" / "counter_anchor.py"
    if not target.is_file():
        raise FileNotFoundError(f"seam module not found: {target}")
    spec = importlib.util.spec_from_file_location("lex_counter_anchor", target)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load seam module from {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lex_counter_anchor"] = module
    spec.loader.exec_module(module)
    return module


def group_of(bundle_path: Path) -> str:
    if bundle_path.name == "served.bundle.json":
        return "served"
    return bundle_path.stem


def select_population(mount: Path) -> list[Path]:
    paths: list[Path] = []
    for family in ("offline_slice", "server_slice"):
        for p in sorted((mount / "results" / "product" / family).glob("*/*.bundle.json")):
            paths.append(p)
    selected = []
    for p in paths:
        try:
            bundle = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        span = (bundle.get("provenance") or {}).get("counter_evidence_span")
        if isinstance(span, dict) and span.get("content_filter"):
            selected.append(p)
    return selected


def measure(mount: Path, paths: list[Path]) -> dict[str, Any]:
    """One full, self-contained measurement pass (used twice for determinism)."""
    seam = load_seam(mount)
    rules, digest = seam.load_frozen_rules()
    if digest != FROZEN_RULES_SHA256:
        raise SystemExit(f"frozen rules digest {digest} != {FROZEN_RULES_SHA256}")

    anchors = dict(getattr(rules, "anchors", {}) or {})
    bundles = []
    for p in paths:
        bundle = json.loads(p.read_text(encoding="utf-8"))
        query = str(bundle.get("query") or "")
        qid = bundle.get("qid") or None
        profile = seam.resolve_anchor_profile(rules, qid=qid, query=query)
        key = None
        if profile is not None:
            key = next((k for k, v in anchors.items() if v is profile), None)
            if key is None:  # defensive: match by identity OR structural equality
                key = next((k for k, v in anchors.items() if v == profile), None)
        span = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
        bundles.append({
            "path": str(p),
            "rel_path": str(p.relative_to(mount)),
            "group": group_of(p),
            "sha256": sha256_file(p),
            "query": query,
            "qid": qid,
            "n_decisions": len(bundle.get("decisions") or []),
            "fresh_profile_key": key,
            "recorded_profile_key": span.get("anchor_profile"),
            "recorded_applied": span.get("applied"),
            "recorded_reason": span.get("reason"),
            "span": {
                "n_candidates": span.get("n_candidates"),
                "n_selected": span.get("n_selected"),
                "n_abstained": span.get("n_abstained"),
                "n_downgraded": span.get("n_downgraded"),
                "n_incumbent_downgraded": span.get("n_incumbent_downgraded"),
                "abstention_reasons": span.get("abstention_reasons") or {},
            },
            "_bundle": bundle,
        })

    # ---- per-group resolution consistency + H1 coverage -------------------
    groups: dict[str, dict[str, Any]] = {}
    for b in bundles:
        g = groups.setdefault(b["group"], {
            "group": b["group"], "n_bundles": 0, "query": b["query"],
            "fresh_keys": Counter(), "recorded_keys": Counter(),
            "recorded_applied": Counter(), "queries": set(),
            "abstention_reasons": Counter(),
            "n_candidates_sum": 0, "n_selected_sum": 0, "n_abstained_sum": 0,
            "n_downgraded_sum": 0, "n_incumbent_downgraded_sum": 0,
            "paths": [],
        })
        g["n_bundles"] += 1
        g["queries"].add(b["query"])
        g["fresh_keys"][b["fresh_profile_key"]] += 1
        g["recorded_keys"][b["recorded_profile_key"]] += 1
        g["recorded_applied"][b["recorded_applied"]] += 1
        g["paths"].append(b["path"])
        for reason, n in (b["span"]["abstention_reasons"] or {}).items():
            g["abstention_reasons"][reason] += n
        for field in ("n_candidates", "n_selected", "n_abstained",
                      "n_downgraded", "n_incumbent_downgraded"):
            v = b["span"][field]
            if isinstance(v, (int, float)):
                g[f"{field}_sum"] += v

    # ---- H2a / H2b per group ---------------------------------------------
    for name, g in groups.items():
        keys = [k for k in g["fresh_keys"] if k is not None]
        profile_key = keys[0] if len(keys) == 1 else None
        profile = anchors.get(profile_key) if profile_key else None
        query_text = " ".join(sorted(g["queries"]))
        bundle_variants = []
        for b in bundles:
            if b["group"] == name:
                bundle_variants.extend(
                    str(v) for v in (b["_bundle"].get("query_variants") or [])
                )
        query_side = query_text + " " + " ".join(bundle_variants)

        pivot = [str(x) for x in ((profile or {}).get("pivot") or [])]
        norm_pivots = sorted({t for t in pivot if DIGIT_RE.search(t)})
        shared_art = sorted(set(art_norm_tokens(query_side)) & set(norm_pivots))
        shared_whole = sorted(whole_word_tokens(query_side, set(norm_pivots)))

        # REPORT-ONLY corpus probe (never verdict-bearing).
        corpus_text: list[str] = []
        corpus_ids: set[str] = set()
        for b in bundles:
            if b["group"] != name:
                continue
            for dec in (b["_bundle"].get("decisions") or [])[:CORPUS_TOP_N]:
                did = str(dec.get("decision_id") or "")
                if did and did in corpus_ids:
                    continue
                if did:
                    corpus_ids.add(did)
                corpus_text.extend(str(dec.get(f) or "") for f in CORPUS_FIELDS)
        corpus = " ".join(corpus_text)
        corpus_art = sorted(set(art_norm_tokens(corpus)) & set(norm_pivots))
        corpus_whole = sorted(whole_word_tokens(corpus, set(norm_pivots)))

        fresh = list(g["fresh_keys"])
        g["resolution"] = {
            "profile_key": profile_key if len(fresh) == 1 else None,
            "fresh_key_counts": {str(k): v for k, v in g["fresh_keys"].items()},
            "consistent_across_bundles": len(g["fresh_keys"]) == 1,
        }
        g["h2a_norm_alignment"] = {
            "applicable": profile is not None and bool(norm_pivots),
            "profile_key": profile_key,
            "norm_pivot_tokens": norm_pivots,
            "query_art_norm_tokens": sorted(set(art_norm_tokens(query_side))),
            "shared_art_norm_tokens": shared_art,
            "shared_whole_token_sensitivity_REPORT_ONLY": shared_whole,
            "holds": (not (profile is not None and norm_pivots)) or bool(shared_art),
        }
        g["h2b_corpus_evidence_REPORT_ONLY"] = {
            "n_distinct_decisions_scanned": len(corpus_ids),
            "corpus_art_norm_tokens": sorted(set(art_norm_tokens(corpus))),
            "corpus_shared_art_norm_tokens": corpus_art,
            "corpus_shared_whole_token_norm_tokens": corpus_whole,
        }
        g["h1_coverage"] = {
            "resolves": profile is not None,
            "applicable": True,
        }
        # internal structure cleanup for serialisation
        g["queries"] = sorted(g["queries"])
        g["fresh_keys"] = {str(k): v for k, v in g["fresh_keys"].items()}
        g["recorded_keys"] = {str(k): v for k, v in g["recorded_keys"].items()}
        g["recorded_applied"] = {str(k): v for k, v in g["recorded_applied"].items()}
        g["abstention_reasons"] = dict(g["abstention_reasons"])

    # ---- H3 shipped-provenance agreement ---------------------------------
    disagreements = [
        {"path": b["path"], "fresh": b["fresh_profile_key"],
         "recorded": b["recorded_profile_key"]}
        for b in bundles
        if b["fresh_profile_key"] != b["recorded_profile_key"]
    ]

    return {
        "rules_sha256": digest,
        "n_bundles": len(bundles),
        "groups": groups,
        "bundles": [{k: v for k, v in b.items() if k != "_bundle"} for b in bundles],
        "h3_provenance_agreement": {
            "n_compared": len(bundles),
            "n_disagreements": len(disagreements),
            "disagreements": disagreements,
            "holds": not disagreements,
        },
        "anchors_available": sorted(anchors),
    }


def _population_pin_check(bundles: list[dict], pop_pins: dict) -> dict:
    observed = {b["rel_path"]: b["sha256"] for b in bundles}
    missing = sorted(set(pop_pins) - set(observed))
    extra = sorted(set(observed) - set(pop_pins))
    changed = sorted(k for k in set(observed) & set(pop_pins)
                     if observed[k] != pop_pins[k])
    return {
        "holds": bool(pop_pins) and not missing and not extra and not changed,
        "n_frozen": len(pop_pins),
        "n_observed": len(observed),
        "missing_from_tree": missing,
        "selected_but_not_frozen": extra,
        "sha_changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--product-mount", default="/tmp/lex_accepted/product")
    ap.add_argument("--out", default=None)
    ap.add_argument("--spec", default="evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    args = ap.parse_args(argv)

    run_id = args.run_id
    mount = Path(args.product_mount).resolve()
    repo = Path(__file__).resolve().parents[1]
    out_path = Path(args.out) if args.out else (
        repo / "results" / "evaluation" / "frozen_rules_profile_coverage" / f"{run_id}.json"
    )
    hyp_path = repo / args.hypothesis
    freeze_path = repo / args.freeze
    spec_path = repo / args.spec

    pins_before = {
        "hypothesis": sha256_file(hyp_path),
        "freeze": sha256_file(freeze_path),
        "frozen_spec": sha256_file(spec_path),
        "mount:product/frozen/RULES_LABEL.json":
            sha256_file(mount / "product" / "frozen" / "RULES_LABEL.json"),
        "mount:product/query/counter_anchor.py":
            sha256_file(mount / "product" / "query" / "counter_anchor.py"),
        "mount_head": _mount_head(mount),
    }

    paths = select_population(mount)

    try:
        freeze_record = json.loads(freeze_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read freeze record: {exc}", file=sys.stderr)
        return 2
    pop_pins: dict[str, str] = dict(
        freeze_record.get("population_sha256_at_freeze") or {})

    first = measure(mount, paths)
    second = measure(mount, paths)
    first_digest = sha256_bytes(json.dumps(first, sort_keys=True).encode())
    second_digest = sha256_bytes(json.dumps(second, sort_keys=True).encode())

    # ---- controls ---------------------------------------------------------
    seam = load_seam(mount)
    rules, rules_digest = seam.load_frozen_rules()
    anchors = dict(getattr(rules, "anchors", {}) or {})

    c2_details = {}
    c2_ok = True
    for key in sorted(anchors):
        resolved = seam.resolve_anchor_profile(rules, qid=key, query="")
        ok = resolved is anchors[key]
        c2_details[key] = ok
        c2_ok = c2_ok and ok

    unknown = seam.resolve_anchor_profile(
        rules, qid=None, query="quantum zebra xylophone 987654")
    c3_ok = unknown is None

    synthetic_query = "Le bailleur resilie le bail. Art. 257d OR."
    synthetic_profile = anchors.get("fr-bail-entretien") or {}
    synthetic_pivots = {str(x) for x in (synthetic_profile.get("pivot") or [])
                        if DIGIT_RE.search(str(x))}
    synthetic_shared = set(art_norm_tokens(synthetic_query)) & synthetic_pivots
    c4_ok = bool(synthetic_shared)

    pins_after = {
        "frozen_spec": sha256_file(spec_path),
        "mount:product/frozen/RULES_LABEL.json":
            sha256_file(mount / "product" / "frozen" / "RULES_LABEL.json"),
        "mount:product/query/counter_anchor.py":
            sha256_file(mount / "product" / "query" / "counter_anchor.py"),
        "mount_head": _mount_head(mount),
    }
    pins_ok = (
        pins_after["frozen_spec"] == pins_before["frozen_spec"] == FROZEN_SPEC_SHA256
        and pins_after["mount:product/frozen/RULES_LABEL.json"] == FROZEN_RULES_SHA256
        and pins_after["mount:product/query/counter_anchor.py"]
        == pins_before["mount:product/query/counter_anchor.py"]
        and pins_after["mount_head"] == pins_before["mount_head"]
    )

    controls = {
        "C1_frozen_rules_digest": {
            "holds": rules_digest == FROZEN_RULES_SHA256,
            "observed": rules_digest,
            "expected": FROZEN_RULES_SHA256,
        },
        "C2_qid_first_resolution_non_vacuous": {
            "holds": c2_ok, "detail": c2_details,
            "expected": "each of the five frozen anchor keys resolves to itself",
        },
        "C3_unknown_query_resolves_none": {"holds": c3_ok},
        "C4_norm_extractor_non_vacuity_synthetic": {
            "holds": c4_ok,
            "synthetic_shared_norm_tokens": sorted(synthetic_shared),
            "note": "synthetic control string, never product data",
        },
        "C5_determinism_two_full_passes": {
            "holds": first_digest == second_digest,
            "first_sha256": first_digest, "second_sha256": second_digest,
        },
        "C6_pins_stable_before_after": {"holds": pins_ok},
        "C7_population_pins_match_freeze": _population_pin_check(
            first["bundles"], pop_pins),
    }
    controls_ok = all(c["holds"] for c in controls.values())

    groups = first["groups"]
    h1_failures = sorted(
        n for n, g in groups.items() if not g["h1_coverage"]["resolves"])
    h2a_failures = sorted(
        n for n, g in groups.items()
        if g["h2a_norm_alignment"]["applicable"]
        and not g["h2a_norm_alignment"]["holds"])

    falsified = []
    if h1_failures:
        falsified.append("H1_profile_coverage")
    if h2a_failures:
        falsified.append("H2a_profile_norm_alignment")

    if not controls_ok:
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
    elif falsified:
        verdict, exit_code = "PROFILE_COVERAGE_FALSIFIED", 1
    elif first["h3_provenance_agreement"]["holds"]:
        verdict, exit_code = "COVERAGE_AND_ALIGNMENT_HOLD", 0
    else:
        verdict, exit_code = "PARTIAL_OR_UNEXPECTED", 0

    payload = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instrument": INSTRUMENT,
        "instrument_sha256": sha256_file(repo / INSTRUMENT),
        "hypothesis_file": args.hypothesis,
        "hypothesis_sha256": pins_before["hypothesis"],
        "freeze_file": args.freeze,
        "freeze_sha256": pins_before["freeze"],
        "product_mount": str(mount),
        "product_mount_head": pins_before["mount_head"],
        "frozen_rules_sha256": rules_digest,
        "frozen_spec_sha256": pins_before["frozen_spec"],
        "anchors_available": first["anchors_available"],
        "selection_rule_FROZEN": SELECTION_RULE_FROZEN,
        "population": {
            "n_bundles": first["n_bundles"],
            "groups": {n: g["n_bundles"] for n, g in groups.items()},
            "bundle_digests": {b["path"]: b["sha256"] for b in first["bundles"]},
        },
        "controls": controls,
        "controls_all_hold": controls_ok,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "H1_profile_coverage": {
            "holds": not h1_failures,
            "failing_groups": h1_failures,
            "per_group": {n: g["h1_coverage"] for n, g in groups.items()},
        },
        "H2a_profile_norm_alignment": {
            "holds": not h2a_failures,
            "failing_groups": h2a_failures,
            "per_group": {n: g["h2a_norm_alignment"] for n, g in groups.items()},
            "definition_FROZEN": (
                "shared_art_norm_tokens = {frozen pivot tokens containing a "
                "digit} INTERSECT {tokens captured by r'\\bart\\s+(\\d+[a-z]{0,3})\\b' "
                "over normalised (query + all query_variants)}; holds when the "
                "set is non-empty, or vacuously when the group resolved no "
                "profile or has no digit-bearing pivot token (H1 covers the "
                "former)."
            ),
        },
        "H2b_corpus_evidence_REPORT_ONLY": {
            n: g["h2b_corpus_evidence_REPORT_ONLY"] for n, g in groups.items()},
        "H2a_whole_token_sensitivity_REPORT_ONLY": {
            n: g["h2a_norm_alignment"]["shared_whole_token_sensitivity_REPORT_ONLY"]
            for n, g in groups.items()},
        "H3_shipped_provenance_agreement": first["h3_provenance_agreement"],
        "groups": groups,
        "bundles": first["bundles"],
        "impact_attribution_REPORT_ONLY": {
            n: {
                "n_bundles": g["n_bundles"],
                "n_candidates_sum": g["n_candidates_sum"],
                "n_selected_sum": g["n_selected_sum"],
                "n_abstained_sum": g["n_abstained_sum"],
                "n_downgraded_sum": g["n_downgraded_sum"],
                "n_incumbent_downgraded_sum": g["n_incumbent_downgraded_sum"],
                "abstention_reasons": g["abstention_reasons"],
                "recorded_applied": g["recorded_applied"],
                "recorded_profile_keys": g["recorded_keys"],
            } for n, g in groups.items()},
        "verdict": verdict,
        "exit_code": exit_code,
        "falsification_proven": bool(falsified),
        "falsified_legs": falsified,
        "reproduction": (
            f"python3 -m evaluation.frozen_rules_profile_coverage_falsifier "
            f"--run-id {run_id} --hypothesis {args.hypothesis} "
            f"--freeze {args.freeze} --product-mount {args.product_mount} "
            f"--out {out_path}"
        ),
        "network": {"network_calls": 0,
                    "note": "no OpenCaseLaw / model / paid-API call; reads "
                            "only committed bytes on a local read-only mount"},
        "numeric_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "claim_ceiling": (
            "This benchmark proves only whether, on the committed accepted "
            "product bytes at the pinned mount head, every flagship query group "
            "of the shipped content-filter family resolves a frozen anchor "
            "profile and, where it does, whether that profile's frozen "
            "norm-bearing pivot anchors are cited as Art. norms in the query's "
            "own text. It does NOT prove that any decision is supporting, "
            "contrary or limiting; scores NO frozen bar, rubric, threshold or "
            "verdict contract; replaces NO benchmark of record; issues NO serve "
            "verdict; admits NO packet; claims NO jurist usefulness; makes NO "
            "recall claim against a live baseline; runs NO universal-174k "
            "benchmark."
        ),
        "not_claimed": [
            "no frozen bar, rubric, threshold or verdict contract is edited",
            "no serve verdict is re-run or issued; both DO-NOT-SERVE orders stand",
            "the benchmark of record (mapping-free falsifier, PRODUCT_FALSIFIED "
            "on packet-of-record 39319405429) is untouched and not re-run",
            "counter labels are not re-decided; the frozen decide_label gate is "
            "never called by this instrument",
            "frontier-counter-evidence-content-filter stays TERMINATED and is "
            "never consulted",
            "comparative map-versus-ranked-list half is NOT scored",
            "posture flags stay FALSE; owner_decision_required stays false",
            "no cross-machine byte-identity claim for the numeric environment",
        ],
        "reused_accepted_assets": [
            "frozen RULES_LABEL.json (sha4457e971...) re-hashed, never re-derived",
            "frozen retrieval spec evaluation/retrieval_gate/"
            "frozen_retrieval_benchmark.json (sha187b0e54) re-hashed",
            "product.query.counter_anchor.resolve_anchor_profile executed "
            "unmodified (sha pinned)",
            "accepted post-repair population marker rule (run 40258497460)",
            "accepted multilingual/provenance suite "
            "tests/evaluation/test_retrieval_benchmark.py (protocol digest "
            "e1a0b18d) executed separately via evaluation/no_pytest_runner.py",
        ],
    }

    # freeze-record cross-check (recorded, not silently trusted)
    expected = freeze_record.get("expected_pins_before_execution", {})
    hyp_sha = pins_before["hypothesis"]
    checked = {k: {"expected": v, "observed": pins_before.get(k),
                   "match": pins_before.get(k) == v}
               for k, v in expected.items()}
    payload["freeze_crosscheck"] = {
        "hypothesis_sha256_at_freeze": freeze_record.get("hypothesis_sha256_at_freeze"),
        "hypothesis_sha256_now": hyp_sha,
        "hypothesis_unchanged_since_freeze":
            freeze_record.get("hypothesis_sha256_at_freeze") == hyp_sha,
        "expected_pins": expected,
        "checked": checked,
        "pins_match_freeze": bool(checked) and all(c["match"] for c in checked.values()),
        "population_pins_frozen": len(pop_pins),
    }
    payload["controls"]["C6_pins_stable_before_after"]["holds"] = (
        payload["controls"]["C6_pins_stable_before_after"]["holds"]
        and payload["freeze_crosscheck"]["hypothesis_unchanged_since_freeze"]
        and payload["freeze_crosscheck"]["pins_match_freeze"]
    )
    payload["controls_all_hold"] = all(
        c["holds"] for c in payload["controls"].values())

    if not payload["controls_all_hold"] and exit_code != 2:
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
        payload["verdict"], payload["exit_code"] = verdict, exit_code

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "verdict": payload["verdict"],
        "exit_code": payload["exit_code"],
        "controls_all_hold": payload["controls_all_hold"],
        "falsified_legs": payload["falsified_legs"],
        "n_bundles": payload["population"]["n_bundles"],
        "h1_failing_groups": payload["H1_profile_coverage"]["failing_groups"],
        "h2a_failing_groups": payload["H2a_profile_norm_alignment"]["failing_groups"],
        "out": str(out_path),
    }, indent=2))
    return payload["exit_code"]


def _mount_head(mount: Path) -> str:
    git_dir = mount / ".git"
    if not git_dir.exists():
        return "NOT_A_GIT_CHECKOUT"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head.split(" ", 1)[1]
            ref_path = git_dir / ref
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
            packed = git_dir / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(" " + ref):
                        return line.split(" ", 1)[0]
            return f"UNRESOLVED_REF:{ref}"
        return head
    except OSError:  # pragma: no cover
        return "HEAD_UNREADABLE"


if __name__ == "__main__":
    sys.exit(main())
