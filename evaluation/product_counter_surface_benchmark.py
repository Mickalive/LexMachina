#!/usr/bin/env python3
"""Measure the SHIPPED product counter-signal layer on the frozen 24-row sample.

WHY THIS EXISTS
---------------
Accepted evaluation run ``39834312064`` measured a *marker rule* and found
counter-authority discovery empty for two of four frozen questions.  Accepted
run ``39771077625`` attributed the marker-rule blind spot but explicitly did
NOT measure the shipped product classifier.  This is the smallest executable
bridge across that gap: it runs the product's own
``classify_against_intent`` over the same 24 cached OpenCaseLaw envelopes and
asks whether its signals ever land on a frozen known-counter authority.

WHAT IS MEASURED
----------------
Primary surface (the product's offline cached path): the classifier input is
``full_text or regeste``, exactly the fallback used by
``apply_adversarial_pass``.  The cached envelopes carry no full text, so this
is the regeste surface.  A separate *optimistic* sensitivity surface feeds
``title + regeste + snippet``; it is disclosed but not the gate.

Topic vocabulary is the product's deterministic extractive-answer proxy:
``answer.build_answer`` (``model: none-local-extractive``) then
``adversarial_retrieval.bundle_topic_terms``.  The live generative answer and
the later independent LLM counter reviewer are NOT measured.  This is a
claim ceiling, not an apology: it isolates the heuristic signal layer that
decides which rows reach the reviewer.

FREEZE-FIRST
------------
Hypothesis and freeze record are committed before the claim-bearing run:
``evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_HYPOTHESIS_V1.json`` and
``evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_FREEZE_RECORD_V1.json``.
Pre-freeze scratch reconnaissance is disclosed in the freeze record.

EXIT CONTRACT
-------------
0  PRODUCT_COUNTER_SURFACE_NOT_FALSIFIED   all frozen gates pass
1  PRODUCT_COUNTER_SURFACE_FALSIFIED       G1 and/or G2 failed
2  ENVIRONMENT_OR_CONTROL_FAILURE          invalid measurement, never a pass

ZERO NETWORK.  The instrument wraps ``socket.socket.connect`` and
``socket.create_connection`` and fails closed if either is called.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import socket
import subprocess
import sys
import time
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCHEMA = "lex-product-counter-surface-benchmark/1"
RUN_ID = "39838415410"
DEFAULT_PRODUCT_ROOT = Path("/tmp/lex_accepted/product")
SPEC_PATH = REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
CACHE_DIR = REPO_ROOT / "results/evaluation/retrieval_benchmark/cache"
ACCEPTED_RECORD_PATH = (
    REPO_ROOT / "results/evaluation/query_map_cached_bundle_benchmark/39834312064.json"
)
MARKER_RECORD_PATH = (
    REPO_ROOT / "results/evaluation/counter_marker_attribution/39771077625.json"
)
BUNDLE_PRODUCER_PATH = REPO_ROOT / "evaluation/query_map/bundle_producer.py"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO_ROOT / "evaluation/PRODUCT_COUNTER_SURFACE_BENCHMARK_FREEZE_RECORD_V1.json"
OUT_DIR = REPO_ROOT / "results/evaluation/product_counter_surface_benchmark"
PRODUCT_QUERY_CACHE = "results/product/query_cache"

PRODUCT_FILES = (
    "product/query/adversarial_retrieval.py",
    "product/query/answer.py",
    "product/query/retrieval.py",
    "product/query/query_texts.py",
)
COUNTER_STATUSES = {
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "contrary-or-exception",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_fingerprint(cache_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(cache_dir)): sha256(path)
        for path in sorted(Path(cache_dir).glob("*/*.json"))
    }


def manifest_sha256(files: dict[str, str]) -> str:
    payload = "\n".join(f"{name}:{digest}" for name, digest in sorted(files.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def index_product_docs(product_root: Path) -> dict[str, Any]:
    """Read-only index of the product cache detail envelopes.

    Search envelopes have no decision_id at top level; detail envelopes do.
    Only detail docs are useful for the hydrated sensitivity surface.  No file
    is written; the caller re-hashes the directory before and after.
    """
    from evaluation.query_map.bundle_producer import alnum_core

    cache_dir = product_root / PRODUCT_QUERY_CACHE
    files = (
        {str(path.relative_to(cache_dir)): sha256(path)
         for path in sorted(cache_dir.glob("*/*.json"))}
        if cache_dir.exists() else {}
    )
    by_id: dict[str, dict] = {}
    by_core: dict[str, dict] = {}
    n_detail = 0
    n_full_text = 0
    for path in sorted(cache_dir.glob("*/*.json")) if cache_dir.exists() else []:
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            body = envelope.get("body")
            doc = json.loads(body) if isinstance(body, str) else body
        except Exception:
            continue
        if not isinstance(doc, dict) or not doc.get("decision_id"):
            continue
        n_detail += 1
        did = str(doc["decision_id"])
        existing = by_id.get(did)
        if existing is None:
            by_id[did] = doc
        else:
            # The product cache can hold several detail envelopes for the same
            # decision; prefer non-empty prose instead of whichever file sorts
            # first.  This is a read-only merge, never a content rewrite.
            for field in ("full_text", "regeste", "title", "snippet"):
                if not str(existing.get(field) or "").strip() and str(doc.get(field) or "").strip():
                    existing[field] = doc[field]
    for did, doc in by_id.items():
        if str(doc.get("full_text") or "").strip():
            n_full_text += 1
        core = alnum_core(did)
        current = by_core.get(core)
        if current is None or (
            str(doc.get("full_text") or "").strip()
            and not str(current.get("full_text") or "").strip()
        ):
            by_core[core] = doc
    return {
        "cache_dir": str(cache_dir),
        "n_files": len(files),
        "manifest_sha256": manifest_sha256(files),
        "n_detail_docs": n_detail,
        "n_unique_docs": len(by_id),
        "n_full_text_docs": n_full_text,
        "by_id": by_id,
        "by_core": by_core,
    }


def doc_for_row(row: dict, docs: dict[str, Any]) -> dict | None:
    from evaluation.query_map.bundle_producer import alnum_core

    did = str(row.get("decision_id") or "")
    return docs["by_id"].get(did) or docs["by_core"].get(alnum_core(did))


class NetworkGuard:
    """Fail-closed recorder for any socket connection attempt."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._orig_connect = None
        self._orig_create = None

    def __enter__(self) -> "NetworkGuard":
        self._orig_connect = socket.socket.connect
        self._orig_create = socket.create_connection

        def blocked_connect(sock, address):  # type: ignore[no-untyped-def]
            self.calls.append(f"connect:{address!r}")
            raise RuntimeError("NETWORK DISABLED by benchmark")

        def blocked_create(address, *args, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append(f"create_connection:{address!r}")
            raise RuntimeError("NETWORK DISABLED by benchmark")

        socket.socket.connect = blocked_connect  # type: ignore[assignment]
        socket.create_connection = blocked_create  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        if self._orig_connect is not None:
            socket.socket.connect = self._orig_connect  # type: ignore[assignment]
        if self._orig_create is not None:
            socket.create_connection = self._orig_create  # type: ignore[assignment]


def load_product(product_root: Path) -> dict[str, Any]:
    """Load exactly the shipped modules, bypassing the package __init__.

    The product package __init__ pulls in numpy/sklearn and unrelated UI code.
    Loading the pure counter module by file path keeps the measurement pinned
    to the shipped bytes without importing more than the signal layer needs.
    """
    query_root = product_root / "product" / "query"
    package_name = "_lex_product_query"
    pkg = types.ModuleType(package_name)
    pkg.__path__ = [str(query_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = pkg
    retrieval_root = product_root / "frontier" / "frontier-query-retrieval"
    if str(retrieval_root) not in sys.path:
        sys.path.insert(0, str(retrieval_root))

    modules: dict[str, Any] = {}
    for name in ("answer", "retrieval", "adversarial_retrieval"):
        fullname = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(fullname, query_root / f"{name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load product module {name}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        modules[name] = mod
    return modules


def product_text_primary(row: dict) -> str:
    """Exact offline fallback in apply_adversarial_pass (no hydration)."""
    return str(row.get("full_text") or row.get("regeste") or "")


def product_text_optimistic(row: dict) -> str:
    """Sensitivity-only surface: more text than the offline product sees."""
    return " ".join(
        str(row.get(field) or "") for field in ("title", "regeste", "snippet")
    )


def signal_of(ar: Any, text: str, topic_terms: list[str]) -> dict[str, Any]:
    status, evidence, markers = ar.classify_against_intent(
        text, "exception", topic_terms=topic_terms
    )
    return {
        "status": status,
        "evidence": evidence,
        "markers": markers,
        "is_signal": bool(status and evidence),
    }


def marker_hits(ar: Any, text: str) -> list[str]:
    low = (text or "").lower()
    hits = set()
    for group in ar.EVIDENCE_MARKERS.values():
        hits.update(m for m in group if m in low)
    return sorted(hits)


def topic_hits(topic_terms: list[str], text: str) -> list[str]:
    low = (text or "").lower()
    return [term for term in topic_terms if term and term.lower() in low]


def frozen_limitation_hits(question: dict, row: dict) -> list[str]:
    from evaluation.query_map.bundle_producer import normalise_text

    tokens = list(question.get("queries", {}).get("limitation_tokens") or [])
    text = normalise_text(row.get("title"), row.get("regeste"), row.get("snippet"))
    return [token for token in tokens if normalise_text(token) in text]


def build_measurement(
    *,
    spec: dict,
    product_root: Path,
    freeze: dict,
) -> dict[str, Any]:
    from evaluation.query_map.bundle_producer import (
        build_bundle,
        index_cache,
        match_frozen_id,
        read_cache,
    )

    modules = load_product(product_root)
    ar = modules["adversarial_retrieval"]
    ans = modules["answer"]
    min_core = int(spec["id_match_rules"]["min_core_length"])
    envelopes = read_cache(CACHE_DIR)
    index = index_cache(envelopes, spec)
    accepted = load_json(ACCEPTED_RECORD_PATH)
    accepted_by_slug = {q["slug"]: q for q in accepted["questions"]}
    product_docs = index_product_docs(product_root)

    questions: list[dict[str, Any]] = []
    aggregate = Counter()
    reached_rows: list[dict[str, Any]] = []

    for question in spec["questions"]:
        slug = question["slug"]
        bundle = build_bundle(slug, index, spec)
        decisions = list(bundle["final"]["decisions"])
        query_text = question["queries"]["baseline"]["fr"]
        answer = ans.build_answer(query_text, decisions)
        topic_terms = ar.bundle_topic_terms(
            {
                "query": query_text,
                "answer": {"prose": answer.get("prose") or ""},
                "decisions": decisions,
            }
        )
        query_only_terms = ar.bundle_topic_terms(
            {"query": query_text, "answer": {"prose": ""}, "decisions": []}
        )

        signals: list[dict[str, Any]] = []
        optimistic_signals: list[dict[str, Any]] = []
        blank_topic_signals = 0
        for row in decisions:
            primary_text = product_text_primary(row)
            primary = signal_of(ar, primary_text, topic_terms)
            if primary["is_signal"]:
                signals.append(
                    {
                        "decision_id": str(row.get("decision_id") or ""),
                        "retrieved_by": list(row.get("retrieved_by") or []),
                        **primary,
                    }
                )
            optimistic = signal_of(ar, product_text_optimistic(row), topic_terms)
            if optimistic["is_signal"]:
                optimistic_signals.append(
                    {"decision_id": str(row.get("decision_id") or ""), **optimistic}
                )
            if signal_of(ar, primary_text, [])["is_signal"]:
                blank_topic_signals += 1

        signal_ids = {s["decision_id"] for s in signals}
        optimistic_ids = {s["decision_id"] for s in optimistic_signals}

        known_rows: list[dict[str, Any]] = []
        known_reached_rows: set[str] = set()
        known_signal_rows: set[str] = set()
        known_marker_rows: set[str] = set()
        known_hydrated_rows: set[str] = set()
        known_hydrated_signal_rows: set[str] = set()
        known_optimistic_signal_rows: set[str] = set()
        known_ids = list(question.get("known_counter_ids") or [])
        for known in known_ids:
            frozen_id = str(known.get("id") if isinstance(known, dict) else known)
            match = None
            for row in decisions:
                match = match_frozen_id(row, frozen_id, min_core_length=min_core)
                if match:
                    break
            if not match:
                known_rows.append(
                    {
                        "frozen_id": frozen_id,
                        "reached": False,
                        "row_decision_id": None,
                        "signalled": False,
                        "marker_rule_labelled": False,
                        "hydrated": False,
                        "hydrated_signalled": False,
                    }
                )
                continue
            row = next(
                r for r in decisions if str(r.get("decision_id")) == match["row_decision_id"]
            )
            primary_text = product_text_primary(row)
            primary = signal_of(ar, primary_text, topic_terms)
            query_only = signal_of(ar, primary_text, query_only_terms)
            optimistic_known = signal_of(ar, product_text_optimistic(row), topic_terms)
            row_id = str(row.get("decision_id") or "")
            doc = doc_for_row(row, product_docs)
            full_text = str((doc or {}).get("full_text") or "").strip()
            hydrated = bool(full_text)
            hydrated_result = (
                signal_of(ar, full_text, topic_terms)
                if hydrated else
                {"status": None, "evidence": "", "markers": [], "is_signal": False}
            )
            labelled = bool(
                row.get("counter_status") in COUNTER_STATUSES
                and str(row.get("counter_evidence") or "").strip()
            )
            known_reached_rows.add(row_id)
            if primary["is_signal"]:
                known_signal_rows.add(row_id)
            if labelled:
                known_marker_rows.add(row_id)
            if optimistic_known["is_signal"]:
                known_optimistic_signal_rows.add(row_id)
            if hydrated:
                known_hydrated_rows.add(row_id)
                if hydrated_result["is_signal"]:
                    known_hydrated_signal_rows.add(row_id)
            m_hits = marker_hits(ar, primary_text)
            t_hits = topic_hits(topic_terms, primary_text)
            lim_hits = frozen_limitation_hits(question, row)
            if m_hits:
                why = "marker_present_but_no_eligible_topical_sentence"
            elif lim_hits:
                why = "product_marker_lexicon_misses_frozen_limitation_token"
            else:
                why = "no_product_marker_and_no_frozen_limitation_token"
            record = {
                "frozen_id": frozen_id,
                "reached": True,
                "row_decision_id": row_id,
                "retrieved_by": list(row.get("retrieved_by") or []),
                "signalled": primary["is_signal"],
                "signal_status": primary["status"],
                "signal_evidence": primary["evidence"],
                "marker_rule_labelled": labelled,
                "marker_rule_status": row.get("counter_status"),
                "marker_rule_evidence": row.get("counter_evidence") or "",
                "product_marker_hits": m_hits,
                "topic_hits": t_hits,
                "frozen_limitation_hits": lim_hits,
                "query_only_topic_signalled": query_only["is_signal"],
                "optimistic_signalled": optimistic_known["is_signal"],
                "diagnosis": why,
                "doc_found": bool(doc),
                "full_text_len": len(full_text),
                "hydrated": hydrated,
                "hydrated_signalled": hydrated_result["is_signal"],
                "hydrated_status": hydrated_result["status"],
                "hydrated_evidence": hydrated_result["evidence"],
                "hydrated_marker_hits": (
                    marker_hits(ar, full_text) if hydrated else []
                ),
                "hydrated_topic_hits": (
                    topic_hits(topic_terms, full_text) if hydrated else []
                ),
            }
            known_rows.append(record)
            reached_rows.append({"slug": slug, **record})

        language_signals = Counter()
        channel_signals = Counter()
        for signal in signals:
            for tag in signal["retrieved_by"]:
                if ":" in tag:
                    channel, lang = tag.split(":", 1)
                    channel_signals[channel] += 1
                    language_signals[lang] += 1

        expected = accepted_by_slug.get(slug, {})
        expected_counts = (
            expected.get("leg1_producer_baseline", {}).get("counts", {})
        )
        actual_counts = {
            "n_decisions": len(decisions),
            "n_marker_labelled": sum(
                1 for row in decisions if row.get("counter_status") in COUNTER_STATUSES
            ),
            "n_duplicates_suppressed": int(bundle["meta"].get("n_duplicates_suppressed") or 0),
            "duplicate_free": len({str(d.get("decision_id")) for d in decisions}) == len(decisions),
        }
        questions.append(
            {
                "slug": slug,
                "query_text": query_text,
                "pool_n": len(decisions),
                "accepted_pool_n": expected_counts.get("initial_decisions"),
                "accepted_marker_labelled_n": expected_counts.get("counter_decisions"),
                "marker_labelled_n": actual_counts["n_marker_labelled"],
                "duplicates_suppressed_n": actual_counts["n_duplicates_suppressed"],
                "duplicate_free": actual_counts["duplicate_free"],
                "topic_terms": topic_terms,
                "query_only_topic_terms": query_only_terms,
                "answer_proxy_method": answer.get("method"),
                "product_signal_n": len(signals),
                "product_signals": signals,
                "product_signal_by_language": dict(sorted(language_signals.items())),
                "product_signal_by_channel": dict(sorted(channel_signals.items())),
                "optimistic_signal_n": len(optimistic_signals),
                "optimistic_signal_ids": sorted(optimistic_ids),
                "blank_topic_signal_n": blank_topic_signals,
                "hydration": {
                    "product_cache_files": product_docs["n_files"],
                    "product_cache_manifest_sha256": product_docs["manifest_sha256"],
                    "product_cache_detail_docs": product_docs["n_detail_docs"],
                    "product_cache_full_text_docs": product_docs["n_full_text_docs"],
                    "reached_known_hydrated_n": len(known_hydrated_rows),
                    "reached_known_hydrated_signalled_n": len(known_hydrated_signal_rows),
                    "reached_known_unhydrated_n": len(known_reached_rows - known_hydrated_rows),
                },
                "known_counter": {
                    "expected_n": len(known_ids),
                    "reached_n": len(known_reached_rows),
                    "signalled_n": len(known_signal_rows),
                    "marker_labelled_n": len(known_marker_rows),
                    "product_only_n": len(known_signal_rows - known_marker_rows),
                    "marker_only_n": len(known_marker_rows - known_signal_rows),
                    "neither_n": len(known_reached_rows - known_signal_rows - known_marker_rows),
                    "unreached_ids": [
                        r["frozen_id"] for r in known_rows if not r["reached"]
                    ],
                    "reached": known_rows,
                },
            }
        )
        aggregate["pool_n"] += len(decisions)
        aggregate["marker_labelled_n"] += actual_counts["n_marker_labelled"]
        aggregate["product_signal_n"] += len(signals)
        aggregate["optimistic_signal_n"] += len(optimistic_signals)
        aggregate["known_expected_n"] += len(known_ids)
        aggregate["known_reached_n"] += len(known_reached_rows)
        aggregate["known_signalled_n"] += len(known_signal_rows)
        aggregate["known_marker_labelled_n"] += len(known_marker_rows)
        aggregate["known_product_only_n"] += len(known_signal_rows - known_marker_rows)
        aggregate["known_marker_only_n"] += len(known_marker_rows - known_signal_rows)
        aggregate["known_hydrated_n"] += len(known_hydrated_rows)
        aggregate["known_hydrated_signalled_n"] += len(known_hydrated_signal_rows)
        aggregate["known_optimistic_signalled_n"] += len(known_optimistic_signal_rows)
        aggregate["product_cache_files"] = product_docs["n_files"]
        aggregate["product_cache_detail_docs"] = product_docs["n_detail_docs"]
        aggregate["product_cache_full_text_docs"] = product_docs["n_full_text_docs"]
        aggregate["questions_with_zero_product_signal"] += int(not signals)
        aggregate["questions_with_zero_known_signal"] += int(not known_signal_rows)

    # Frozen gates.  G1/G2/G4/G5 are the product falsification gates;
    # G3 is the hydrated sensitivity diagnostic; G6/G7 are validity.
    per_question_signals = {q["slug"]: q["product_signal_n"] for q in questions}
    gates = {
        "G1_offline_product_signal_on_every_question": {
            "passed": all(v > 0 for v in per_question_signals.values()),
            "detail": per_question_signals,
        },
        "G2_offline_product_signal_reaches_known_counter_authority": {
            "passed": aggregate["known_signalled_n"] > 0,
            "detail": {
                "known_reached_n": aggregate["known_reached_n"],
                "known_signalled_n": aggregate["known_signalled_n"],
            },
        },
        "G3_hydrated_product_signal_reaches_known_counter_authority": {
            "passed": aggregate["known_hydrated_signalled_n"] > 0,
            "detail": {
                "known_hydrated_n": aggregate["known_hydrated_n"],
                "known_hydrated_signalled_n": aggregate["known_hydrated_signalled_n"],
            },
        },
        "G4_hydration_surface_available_for_g3": {
            "passed": aggregate["known_hydrated_n"] > 0,
            "detail": {
                "known_reached_n": aggregate["known_reached_n"],
                "known_hydrated_n": aggregate["known_hydrated_n"],
                "coverage": round(
                    aggregate["known_hydrated_n"] / max(1, aggregate["known_reached_n"]), 4
                ),
                "note": "coverage is reported, not thresholded; it bounds G3",
            },
        },
        "G5_same_surface_product_signal_not_worse_than_marker_rule_on_known": {
            "passed": (
                aggregate["known_optimistic_signalled_n"]
                >= aggregate["known_marker_labelled_n"]
            ),
            "detail": {
                "known_optimistic_signalled_n": aggregate["known_optimistic_signalled_n"],
                "known_marker_labelled_n": aggregate["known_marker_labelled_n"],
                "surface": "title + regeste + snippet, the frozen marker rule's own text surface",
            },
        },
        "G6_every_signal_has_verbatim_evidence": {
            "passed": all(
                s["status"] in COUNTER_STATUSES and bool(s["evidence"].strip())
                for q in questions
                for s in q["product_signals"]
            ),
            "detail": "all emitted offline signals carry a status and non-empty evidence",
        },
        "G7_pool_provenance_and_duplicate_free": {
            "passed": all(
                q["duplicate_free"]
                and q["pool_n"] > 0
                and q["pool_n"] == q["accepted_pool_n"]
                for q in questions
            ),
            "detail": {
                q["slug"]: {
                    "pool_n": q["pool_n"],
                    "accepted_pool_n": q["accepted_pool_n"],
                    "duplicates_suppressed_n": q["duplicates_suppressed_n"],
                    "duplicate_free": q["duplicate_free"],
                }
                for q in questions
            },
        },
    }

    return {
        "product": {
            "root": str(product_root),
            "head": freeze.get("product_head"),
            "version": ar.ADVERSARIAL_RETRIEVAL_VERSION,
            "files": freeze.get("product_files", {}),
        },
        "cache": {
            "n_envelopes": len(envelopes),
            "fingerprint": cache_fingerprint(CACHE_DIR),
            "product_query_cache": {
                "n_files": product_docs["n_files"],
                "manifest_sha256": product_docs["manifest_sha256"],
                "n_detail_docs": product_docs["n_detail_docs"],
                "n_full_text_docs": product_docs["n_full_text_docs"],
            },
        },
        "questions": questions,
        "aggregate": dict(aggregate),
        "gates": gates,
        "reached_known_rows": reached_rows,
    }


def controls_report(
    *,
    spec: dict,
    product_root: Path,
    freeze: dict,
    measurement: dict[str, Any],
    modules: dict[str, Any],
    cache_before: dict[str, str],
    cache_after: dict[str, str],
    pins_before: dict[str, str],
    pins_after: dict[str, str],
    network_calls: list[str],
    deterministic: bool,
) -> dict[str, Any]:
    ar = modules["adversarial_retrieval"]
    planted_text = (
        "Dies ist eine Ausnahme von der Regel. Der Mieter kann den Mietvertrag "
        "wegen Zahlungsverzugs kündigen. Der Vermieter muss die Kündigung "
        "schriftlich begründen."
    )
    planted_topic = ["mieter", "mietvertrag", "kündigung"]
    planted_status, planted_evidence, planted_markers = ar.classify_against_intent(
        planted_text, "exception", topic_terms=planted_topic
    )
    blank_status, blank_evidence, blank_markers = ar.classify_against_intent(
        planted_text, "exception", topic_terms=[]
    )
    negative_text = "Das Gericht weist die Beschwerde ab. Der Mieter schuldet die Miete."
    negative_status, negative_evidence, negative_markers = ar.classify_against_intent(
        negative_text, "exception", topic_terms=planted_topic
    )

    product_files_after = {
        rel: sha256(product_root / rel) for rel in PRODUCT_FILES
    }
    expected_product_files = freeze.get("product_files", {})
    product_files_unchanged = product_files_after == expected_product_files
    spec_unchanged = sha256(SPEC_PATH) == freeze.get("sample_pins", {}).get("frozen_spec_sha256")
    accepted_unchanged = sha256(ACCEPTED_RECORD_PATH) == freeze.get("sample_pins", {}).get(
        "accepted_cached_bundle_record_sha256"
    )
    producer_unchanged = sha256(BUNDLE_PRODUCER_PATH) == freeze.get("sample_pins", {}).get(
        "bundle_producer_sha256"
    )
    cache_unchanged = cache_before == cache_after and len(cache_after) == 24
    product_cache = measurement.get("cache", {}).get("product_query_cache", {})
    sample_pins = freeze.get("sample_pins", {})
    product_cache_unchanged = (
        product_cache.get("manifest_sha256") == sample_pins.get("product_query_cache_manifest_sha256")
        and product_cache.get("n_files") == sample_pins.get("product_query_cache_n_files")
    )
    pool_parity = controls_pool_parity(measurement)
    pool_parity_ok = all(v["passed"] for v in pool_parity.values())
    try:
        head_now = subprocess.check_output(
            ["git", "-C", str(product_root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        head_now = ""
    head_ok = head_now == freeze.get("product_head")

    planted_ok = (
        planted_status == "candidate-limiting"
        and bool(planted_evidence)
        and "ausnahme" in planted_markers
        and blank_status is None
        and negative_status is None
    )
    controls = {
        "C1_pins_unchanged": {
            "passed": (
                pins_before == pins_after
                and product_files_unchanged
                and spec_unchanged
                and accepted_unchanged
                and producer_unchanged
            ),
            "detail": {
                "pins_before": pins_before,
                "pins_after": pins_after,
                "product_files_unchanged": product_files_unchanged,
                "spec_unchanged": spec_unchanged,
                "accepted_record_unchanged": accepted_unchanged,
                "bundle_producer_unchanged": producer_unchanged,
            },
        },
        "C2_cache_and_pool_parity": {
            "passed": cache_unchanged and pool_parity_ok and product_cache_unchanged,
            "detail": {
                "n_cache_envelopes": len(cache_after),
                "cache_unchanged": cache_unchanged,
                "product_query_cache_unchanged": product_cache_unchanged,
                "product_query_cache": product_cache,
                "pool_parity": pool_parity,
            },
        },
        "C3_product_module_identity": {
            "passed": (
                ar.ADVERSARIAL_RETRIEVAL_VERSION == "adversarial_retrieval/3"
                and hasattr(ar, "classify_against_intent")
                and hasattr(ar, "bundle_topic_terms")
                and hasattr(modules["answer"], "build_answer")
            ),
            "detail": {
                "version": ar.ADVERSARIAL_RETRIEVAL_VERSION,
                "source_sha256": expected_product_files.get(
                    "product/query/adversarial_retrieval.py"
                ),
            },
        },
        "C4_planted_detection_and_blank_topic_vacuity": {
            "passed": planted_ok,
            "detail": {
                "planted_status": planted_status,
                "planted_markers": planted_markers,
                "planted_evidence": planted_evidence,
                "blank_topic_status": blank_status,
                "negative_control_status": negative_status,
            },
        },
        "C5_zero_network": {
            "passed": not network_calls,
            "detail": {"n_calls": len(network_calls), "calls": network_calls},
        },
        "C6_deterministic_repeat": {
            "passed": deterministic,
            "detail": "primary signal id sets are identical across two passes",
        },
        "C7_product_head_matches_freeze": {
            "passed": head_ok,
            "detail": {"head_now": head_now, "head_frozen": freeze.get("product_head")},
        },
    }
    return controls


def controls_pool_parity(measurement: dict[str, Any]) -> dict[str, Any]:
    return {
        q["slug"]: {
            "pool_n": q["pool_n"],
            "accepted_pool_n": q["accepted_pool_n"],
            "marker_labelled_n": q["marker_labelled_n"],
            "accepted_marker_labelled_n": q["accepted_marker_labelled_n"],
            "passed": (
                q["pool_n"] == q["accepted_pool_n"]
                and q["marker_labelled_n"] == q["accepted_marker_labelled_n"]
            ),
        }
        for q in measurement["questions"]
    }


def run(product_root: Path, run_id: str, out_path: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    for required in (SPEC_PATH, ACCEPTED_RECORD_PATH, MARKER_RECORD_PATH, BUNDLE_PRODUCER_PATH):
        if not required.exists():
            raise SystemExit(f"missing required input: {required}")
    if sha256(HYPOTHESIS_PATH) != load_json(FREEZE_PATH).get("hypothesis_sha256"):
        raise SystemExit("hypothesis bytes do not match freeze record")
    freeze = load_json(FREEZE_PATH)
    spec = load_json(SPEC_PATH)
    cache_before = cache_fingerprint(CACHE_DIR)
    pins_before = {
        "spec": sha256(SPEC_PATH),
        "accepted_record": sha256(ACCEPTED_RECORD_PATH),
        "marker_record": sha256(MARKER_RECORD_PATH),
        "bundle_producer": sha256(BUNDLE_PRODUCER_PATH),
        "hypothesis": sha256(HYPOTHESIS_PATH),
        "freeze_record": sha256(FREEZE_PATH),
        **{rel: sha256(product_root / rel) for rel in PRODUCT_FILES},
    }

    network = NetworkGuard()
    with network:
        measurement = build_measurement(spec=spec, product_root=product_root, freeze=freeze)
        # Second independent pass for determinism.  Rebuild from freshly loaded
        # modules and cached bytes, not from the first result object.
        repeat = build_measurement(spec=spec, product_root=product_root, freeze=freeze)

    first_ids = {
        q["slug"]: sorted(s["decision_id"] for s in q["product_signals"])
        for q in measurement["questions"]
    }
    second_ids = {
        q["slug"]: sorted(s["decision_id"] for s in q["product_signals"])
        for q in repeat["questions"]
    }
    deterministic = first_ids == second_ids

    cache_after = cache_fingerprint(CACHE_DIR)
    pins_after = {
        "spec": sha256(SPEC_PATH),
        "accepted_record": sha256(ACCEPTED_RECORD_PATH),
        "marker_record": sha256(MARKER_RECORD_PATH),
        "bundle_producer": sha256(BUNDLE_PRODUCER_PATH),
        "hypothesis": sha256(HYPOTHESIS_PATH),
        "freeze_record": sha256(FREEZE_PATH),
        **{rel: sha256(product_root / rel) for rel in PRODUCT_FILES},
    }
    modules = load_product(product_root)
    controls = controls_report(
        spec=spec,
        product_root=product_root,
        freeze=freeze,
        measurement=measurement,
        modules=modules,
        cache_before=cache_before,
        cache_after=cache_after,
        pins_before=pins_before,
        pins_after=pins_after,
        network_calls=network.calls,
        deterministic=deterministic,
    )

    gates = measurement["gates"]
    validity_ok = all(
        gates[name]["passed"]
        for name in ("G6_every_signal_has_verbatim_evidence", "G7_pool_provenance_and_duplicate_free")
    )
    controls_ok = all(c["passed"] for c in controls.values())
    falsifiers = (
        "G1_offline_product_signal_on_every_question",
        "G2_offline_product_signal_reaches_known_counter_authority",
        "G5_same_surface_product_signal_not_worse_than_marker_rule_on_known",
    )
    failed_falsifiers = [name for name in falsifiers if not gates[name]["passed"]]

    if not controls_ok or not validity_ok:
        verdict = "ENVIRONMENT_OR_CONTROL_FAILURE"
        exit_code = 2
        reason = "Frozen control or measurement-validity gate failed; no product claim."
    elif failed_falsifiers:
        verdict = "PRODUCT_COUNTER_SIGNAL_LAYER_FALSIFIED_ON_CACHED_SURFACE"
        exit_code = 1
        reason = (
            "The shipped adversarial_retrieval/3 signal layer reached zero of " +
            f"{measurement['aggregate']['known_reached_n']} frozen known-counter " +
            "authorities on the offline cached regeste surface (G2); on the " +
            "marker rule's own title+regeste+snippet surface the product " +
            "signalled " +
            f"{measurement['aggregate']['known_optimistic_signalled_n']} vs the " +
            f"marker rule's {measurement['aggregate']['known_marker_labelled_n']} " +
            "known rows (G5). Hydrated sensitivity is reported separately (G3): " +
            f"{measurement['aggregate']['known_hydrated_signalled_n']} of " +
            f"{measurement['aggregate']['known_hydrated_n']} hydrated reached " +
            "known rows signalled; hydration covered only " +
            f"{measurement['aggregate']['known_hydrated_n']} of " +
            f"{measurement['aggregate']['known_reached_n']} reached rows."
        )
    else:
        verdict = "PRODUCT_COUNTER_SIGNAL_LAYER_NOT_FALSIFIED"
        exit_code = 0
        reason = "All frozen product-counter-signal gates and controls passed."

    out = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "hypothesis_sha256": sha256(HYPOTHESIS_PATH),
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256(FREEZE_PATH),
        **measurement,
        "controls": controls,
        "claim_ceiling": {
            "measured": (
                "The shipped adversarial_retrieval/3 heuristic signal layer on the "
                "24 frozen cached OpenCaseLaw regeste surfaces (primary offline "
                "path) and on product-cache full_text where available (hydrated "
                "sensitivity), with the product's deterministic extractive-answer "
                "topic proxy."
            ),
            "not_measured": [
                "live generative answer quality or live product UI",
                "the later independent LLM counter reviewer (the sole writer of user-visible counter_status)",
                "live top-12 hydration selection; hydrated sensitivity uses full_text "
                "where the product cache happens to contain it",
                "legal correctness of the frozen known_counter_ids beyond their frozen provenance",
                "any universal-174k benchmark or external retrieval run",
            ],
            "primary_surface": "product/query/adversarial_retrieval.py apply_adversarial_pass fallback: full_text or regeste; cached rows have no full_text",
            "optimistic_surface": "title + regeste + snippet, reported only as a sensitivity upper bound",
            "zero_network": True,
        },
        "elapsed_s": round(time.perf_counter() - started, 3),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (OUT_DIR / f"{run_id}.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", default=str(DEFAULT_PRODUCT_ROOT))
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = run(Path(args.product_root), args.run_id, Path(args.out) if args.out else None)
    print(json.dumps({
        "run_id": out["run_id"],
        "verdict": out["verdict"],
        "exit_code": out["exit_code"],
        "aggregate": out["aggregate"],
        "failed_gates": [k for k, v in out["gates"].items() if not v["passed"]],
    }, indent=2))
    return int(out["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
