"""Attribution harness: resolve the primary cause of zero counter-label emission.

Pure, offline, deterministic. Reads a packet dir (or a single bundle) and
emits, per bundle, exactly one primary cause class with byte-level evidence,
per the frozen decision tree in RULES.json (team frontier-counter-label-emission,
charter v1). Secondary classes are published but never double-counted.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

CAUSE_A = "a_POPULATION"
CAUSE_B = "b_PLANNER_PROBE"
CAUSE_C = "c_HYDRATION"
CAUSE_D = "d_GATE"
CAUSE_E = "e_EMISSION_WRITER_ABORT"

ALL_CAUSES = (CAUSE_A, CAUSE_B, CAUSE_C, CAUSE_D, CAUSE_E)

#: Evidence-marker vocabulary mirrored from the accepted product module
#: product/query/adversarial_retrieval.py (read-only consumption, never
#: re-tuned).  Kept here so the harness is dependency-free and offline.
_EVIDENCE_MARKERS: dict[str, tuple[str, ...]] = {
    "exception": (
        "ausnahme", "exception", "eccezione",
        "vorbehalt", "réserve", "riserva",
        "carve-out", "vorbehalten", "réservé", "riservato",
    ),
    "contrary": (
        "entgegen", "contraire", "contrario",
        "abweichend", "écarté", "difforme",
        "anders", "dagegen", "néanmoins", "tuttavia",
    ),
    "minority": (
        "minderheit", "minorité", "minoranza",
        "abweichende auffassung", "opinion dissidente", "opinione dissidente",
        "minderheitsauffassung",
    ),
    "older_line": (
        "ältere rechtsprechung", "ancienne jurisprudence", "giurisprudenza precedente",
        "frühere entscheid", "précédent antérieur", "precedente",
    ),
}

_INTENT_ORDER = ("exception", "contrary", "minority", "older_line")

#: Boilerplate / disposal guards (mirrored from the accepted product module).
_BOILERPLATE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"eintretensprüfung",
        r"das gericht tritt\s+nicht\s+ein",
        r"inappellabilit",
        r"irrecevabilité",
        r"es\s+wird\s+nicht\s+eingetreten",
        r"le tribunal\s+n'entre\s+pas\s+en\s+matière",
    )
]

_DISPOSAL_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"abgewiesen",
        r"werden\s+abgelehnt",
        r"rejeté\s+le\s+recours",
        r"respinto\s+il\s+ricorso",
        r"die\s+beschwerde\s+wird\s+abgewiesen",
    )
]


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _split_sentences(text: str, max_len: int = 600) -> list[str]:
    """Local sentence splitter mirroring product/query/answer.py semantics."""
    parts = re.split(r"(?<=[.!?;])\s+(?=[A-ZÄÖÜÉÈÊA-Z0-9«\"'])", (text or "").replace("\n", " "))
    return [p.strip()[:max_len] for p in parts if len(p.strip()) > 40][:400]


def _sentence_eligible(sentence: str, markers: tuple[str, ...] | list[str], *, intent: str) -> bool:
    low = (sentence or "").lower()
    if any(p.search(low) for p in _BOILERPLATE_PATTERNS):
        return False
    if intent == "contrary" and any(p.search(low) for p in _DISPOSAL_PATTERNS):
        return False
    return any(m in low for m in markers)


def _topic_terms_from_bundle(bundle: dict) -> list[str]:
    """Rebuild the bundle's topic vocabulary the same way the product did."""
    prov = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    stored = list(prov.get("label_topic_terms") or [])
    if stored:
        return [str(t).lower() for t in stored]
    # Fallback: derive deterministically from the query (len>=4 tokens).
    import unicodedata
    q = str(bundle.get("query") or "")
    s = unicodedata.normalize("NFKD", q).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    toks = sorted({t for t in re.split(r"[^a-z0-9]+", s) if len(t) >= 4})
    return toks


def _scan_gate_pass(text: str, intent: str, topic_terms: list[str]) -> tuple[bool, list[str], str]:
    """Re-run the topical/marker gate on a row's own text (class (d) test).

    Returns (would_pass, markers_found, first_eligible_sentence).
    """
    lowered = (text or "").lower()
    if not lowered or not topic_terms:
        return False, [], ""
    probe_first = [intent] + [i for i in _INTENT_ORDER if i != intent]
    for candidate_intent in probe_first:
        markers = [m for m in _EVIDENCE_MARKERS.get(candidate_intent, ()) if m in lowered]
        if not markers:
            continue
        for sentence in _split_sentences(text):
            low = sentence.lower()
            if not _sentence_eligible(sentence, markers, intent=candidate_intent):
                continue
            if not any(t in low for t in topic_terms):
                continue
            return True, sorted({m for m in markers if m in low})[:6], sentence[:400]
        for line in (text or "").splitlines():
            if not _sentence_eligible(line, markers, intent=candidate_intent):
                continue
            low = line.lower()
            if not any(t in low for t in topic_terms):
                continue
            anchor = line.strip()
            if anchor:
                return True, sorted({m for m in markers if m in low})[:6], anchor[:400]
    return False, [], ""


def _adversarial_rows(bundle: dict) -> list[dict]:
    out = []
    for d in bundle.get("decisions") or []:
        prov = str(d.get("provenance") or "")
        if (
            "adversarial" in prov
            or d.get("adversarial_channel")
            or d.get("adversarial_retrieval_signal")
        ):
            out.append(d)
    return out


def _llm_reviewer_state(bundle: dict) -> dict[str, Any]:
    ga = (bundle.get("provenance") or {}).get("generative_audit") or {}
    adv = ga.get("adversarial") or {}
    return {
        "n_findings": int(adv.get("n_findings") or 0),
        "n_challenging_findings": int(adv.get("n_challenging_findings") or 0),
        "model": str(adv.get("model") or ""),
        "retries": adv.get("retries"),
        "attempts": adv.get("attempts") or [],
        "raw_excerpt": adv.get("raw_excerpt"),
        "counter_surface_suppressed": int(ga.get("counter_surface_suppressed") or 0),
        "status_summary": ga.get("status_summary") or {},
        "present": "adversarial" in ga,
    }


def _scored_status_count(bundle: dict, scored_statuses: tuple[str, ...]) -> int:
    return sum(
        1
        for d in bundle.get("decisions") or []
        if str(d.get("counter_status") or "") in scored_statuses
    )


def attribute_bundle(bundle: dict, scored_statuses: tuple[str, ...]) -> dict[str, Any]:
    """Resolve exactly one primary cause class for one bundle, with evidence."""
    prov = bundle.get("provenance") or {}
    adv_prov = prov.get("adversarial_retrieval") or {}
    rows = bundle.get("decisions") or []
    adv_rows = _adversarial_rows(bundle)
    topic_terms = _topic_terms_from_bundle(bundle)
    llm = _llm_reviewer_state(bundle)

    # Per-row evidence table (byte-level, deterministic order).
    row_evidence: list[dict[str, Any]] = []
    for d in sorted(adv_rows, key=lambda r: str(r.get("decision_id") or "")):
        sig = d.get("adversarial_retrieval_signal") or {}
        heur = sig.get("heuristic_status")
        ev = str(sig.get("evidence") or "")
        ft = str(d.get("full_text") or "")
        row_evidence.append({
            "decision_id": str(d.get("decision_id") or ""),
            "provenance": str(d.get("provenance") or ""),
            "adversarial_channel": str(d.get("adversarial_channel") or ""),
            "adversarial_intent": str(d.get("adversarial_intent") or ""),
            "heuristic_status": heur,
            "heuristic_evidence_len": len(ev),
            "heuristic_evidence_head": ev[:120],
            "counter_status": str(d.get("counter_status") or ""),
            "counter_evidence_len": len(str(d.get("counter_evidence") or "")),
            "full_text_status": str(d.get("full_text_status") or ""),
            "full_text_len": len(ft),
        })

    n_heuristic_positive = sum(
        1 for r in row_evidence if r["heuristic_status"] and r["heuristic_evidence_len"] > 0
    )
    n_scored = _scored_status_count(bundle, scored_statuses)
    n_exception_only = sum(
        1
        for r in row_evidence
        if "adversarial:exception" in r["provenance"]
        and not r["heuristic_status"]
    )
    n_adv = len(row_evidence)
    n_lazy_no_text = sum(
        1 for r in row_evidence if r["full_text_status"] == "lazy" and r["full_text_len"] == 0
    )

    # Step 1: planner/probe
    attempted = bool(adv_prov.get("attempted"))
    n_candidates = int(adv_prov.get("n_candidates") or 0)
    probes = adv_prov.get("probes") or []
    channels = adv_prov.get("channels") or []
    if (not attempted) or n_candidates == 0 or (not probes and not channels):
        return {
            "primary_cause": CAUSE_B,
            "secondary_causes": [],
            "evidence": {
                "attempted": attempted,
                "n_candidates": n_candidates,
                "n_probes": len(probes),
                "channels": channels,
                "adversarial_rows": n_adv,
            },
            "row_evidence": row_evidence,
            "llm_reviewer": llm,
            "topic_terms_sample": topic_terms[:12],
        }

    # Step 2: population
    if n_heuristic_positive == 0 and n_adv > 0 and n_exception_only == n_adv:
        return {
            "primary_cause": CAUSE_A,
            "secondary_causes": [],
            "evidence": {
                "adversarial_rows": n_adv,
                "n_heuristic_positive": n_heuristic_positive,
                "n_exception_only": n_exception_only,
                "note": "every adversarial row is exception-variant fallback with no gate-passed heuristic evidence",
            },
            "row_evidence": row_evidence,
            "llm_reviewer": llm,
            "topic_terms_sample": topic_terms[:12],
        }

    # Step 3: hydration — lazy rows are exactly the rows with no heuristic signal
    lazy_without_signal = [
        r for r in row_evidence
        if r["full_text_status"] == "lazy" and r["full_text_len"] == 0 and not r["heuristic_status"]
    ]
    hydrated_without_signal = [
        r for r in row_evidence
        if r["full_text_len"] > 0 and not r["heuristic_status"]
    ]
    if n_adv > 0 and len(lazy_without_signal) == n_adv and not hydrated_without_signal:
        return {
            "primary_cause": CAUSE_C,
            "secondary_causes": [],
            "evidence": {
                "adversarial_rows": n_adv,
                "n_lazy_no_text": n_lazy_no_text,
                "n_hydrated_without_signal": len(hydrated_without_signal),
                "note": "every adversarial row is snippet-only/lazy with no eligible evidence sentence",
            },
            "row_evidence": row_evidence,
            "llm_reviewer": llm,
            "topic_terms_sample": topic_terms[:12],
        }

    # Step 4: gate — rows with full text that WOULD pass the topical/marker
    # gate on re-scan but carry no heuristic signal.
    gate_suppressed: list[dict[str, Any]] = []
    for d in sorted(adv_rows, key=lambda r: str(r.get("decision_id") or "")):
        sig = d.get("adversarial_retrieval_signal") or {}
        if sig.get("heuristic_status") and str(sig.get("evidence") or ""):
            continue
        text = str(d.get("full_text") or "") or str(d.get("regeste") or "")
        intent = str(d.get("adversarial_intent") or "exception")
        would_pass, markers, sentence = _scan_gate_pass(text, intent, topic_terms)
        if would_pass:
            gate_suppressed.append({
                "decision_id": str(d.get("decision_id") or ""),
                "intent": intent,
                "markers": markers,
                "sentence_head": sentence[:120],
            })
    if gate_suppressed:
        return {
            "primary_cause": CAUSE_D,
            "secondary_causes": [],
            "evidence": {
                "adversarial_rows": n_adv,
                "n_gate_suppressed": len(gate_suppressed),
                "gate_suppressed_rows": gate_suppressed,
                "note": "rows carry eligible evidence sentences that the topical/marker gate suppressed",
            },
            "row_evidence": row_evidence,
            "llm_reviewer": llm,
            "topic_terms_sample": topic_terms[:12],
        }

    # Step 5: emission-writer abort — heuristic signal exists and passed, but
    # zero rows carry a scored counter_status (the LLM reviewer is the sole
    # writer and aborted / failed its precision gate).
    if n_heuristic_positive > 0 and n_scored == 0:
        secondary: list[str] = []
        if n_lazy_no_text > 0:
            secondary.append(CAUSE_C)
        return {
            "primary_cause": CAUSE_E,
            "secondary_causes": secondary,
            "evidence": {
                "adversarial_rows": n_adv,
                "n_heuristic_positive": n_heuristic_positive,
                "n_scored_before": n_scored,
                "llm_reviewer_n_findings": llm["n_findings"],
                "llm_reviewer_model": llm["model"],
                "llm_reviewer_attempts": llm["attempts"],
                "llm_reviewer_present": llm["present"],
                "counter_surface_suppressed": llm["counter_surface_suppressed"],
                "n_lazy_no_text": n_lazy_no_text,
                "note": (
                    "heuristic proposals exist and passed the topical/marker gate, "
                    "but the LLM adversarial reviewer (sole writer of counter_status "
                    "per product/query/adversarial_retrieval.py) aborted or failed "
                    "its verified-evidence precision gate, so no scored proposal "
                    "reached the accepted classifier"
                ),
            },
            "row_evidence": row_evidence,
            "llm_reviewer": llm,
            "topic_terms_sample": topic_terms[:12],
        }

    # Fallback: name the closest bounded cause honestly.
    return {
        "primary_cause": CAUSE_A if n_heuristic_positive == 0 else CAUSE_E,
        "secondary_causes": [],
        "evidence": {
            "adversarial_rows": n_adv,
            "n_heuristic_positive": n_heuristic_positive,
            "n_scored_before": n_scored,
            "note": "no decision-tree rule matched exactly; nearest bounded cause published",
        },
        "row_evidence": row_evidence,
        "llm_reviewer": llm,
        "topic_terms_sample": topic_terms[:12],
    }


def attribute_packet(packet_dir: str | Path, scored_statuses: tuple[str, ...]) -> dict[str, Any]:
    """Attribute every bundle in a packet dir. Deterministic, offline."""
    packet_dir = Path(packet_dir)
    qdir = packet_dir / "questions"
    results: dict[str, Any] = {}
    for path in sorted(qdir.glob("*.bundle.json")):
        qid = path.name[: -len(".bundle.json")]
        bundle = json.loads(path.read_text(encoding="utf-8"))
        results[qid] = attribute_bundle(bundle, scored_statuses)
    return results


def verify_input_hashes(packet_dir: str | Path, expected: dict[str, str]) -> dict[str, Any]:
    """Re-hash the packet files against the frozen RULES.json pins."""
    packet_dir = Path(packet_dir)
    actual: dict[str, str] = {}
    mismatches: list[dict[str, str]] = []
    for rel, want in sorted(expected.items()):
        p = packet_dir / rel
        if not p.is_file():
            mismatches.append({"relpath": rel, "status": "missing"})
            continue
        got = sha256_file(p)
        actual[rel] = got
        if got != want:
            mismatches.append({"relpath": rel, "status": "mismatch", "expected": want, "actual": got})
    return {
        "ok": not mismatches,
        "n_checked": len(expected),
        "mismatches": mismatches,
        "actual": actual,
    }


__all__ = [
    "ALL_CAUSES",
    "CAUSE_A",
    "CAUSE_B",
    "CAUSE_C",
    "CAUSE_D",
    "CAUSE_E",
    "attribute_bundle",
    "attribute_packet",
    "sha256_bytes",
    "sha256_file",
    "verify_input_hashes",
]
