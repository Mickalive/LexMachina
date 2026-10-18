"""Claim-admissibility audit for the product-vs-baseline recall falsifier.

Why this module exists
----------------------
Cycle ``39111232991`` built the lane's first claim-bearing PRODUCT-side recall
gate (``evaluation.product_counter_recall``) and got
``FAIL_PARITY_REGRESSION``.  Its independent audit
(``results/audit/evaluation/CYCLE_39111232991_GATE.json``, ``gate=REVISE``)
found two material defects in the *interpretation* of that number, not in the
instrument:

* **D1** the frozen analyst mapping claims that ``corporate-criminal-liability``
  and ``de-kapitalverletzung`` are the "same subject".  They are not: the served
  question is the employment-law duty of care under OR 321 ff., the frozen slug
  is Art. 102 StGB.  ``rent-default`` / ``fr-bail-entretien`` is at best
  *partial*: same article family (CP 257d), different factual predicate
  (arrears vs. landlord's failure to maintain).
* **D2** the comparator is not "the plain OpenCaseLaw top-50".  The frozen
  record carries an explicit ``channel`` field; the scored pool is
  ``baseline`` (3 x 50 rows) UNION ``counter`` (3 x 30 rows, limitation-token
  queries that are themselves a counter-authority search design).

This module does NOT re-measure recall and does NOT touch the frozen v1
hypothesis or the committed v1 record.  It adds the two things that were
missing, both executable:

1. **A mechanical subject-match measurement** per mapping cell, computed from the
   product's OWN ``question.json`` subject text against the frozen slug's OWN
   ``norm_tokens`` and query texts, plus a frozen admissibility rule in which
   the measurement can only **downgrade** a declared admissibility, never
   upgrade it.  That is the auditor's suggested D1 catcher, promoted to a gate.
2. **A channel-split recomputation** of the v1 comparator pool, so "the plain
   top-50 it wraps" becomes a number instead of a phrase (D2).
3. **A question-native product check that uses no analyst mapping at all**: does
   a served bundle get admitted while its own pre-registered concept self-check
   reports that a core legal term of the question retrieved zero rows?

Reuse, not rebuild
------------------
* id matching is the ACCEPTED ``evaluation.retrieval_gate.gates.match_authorities``
  / ``row_cores`` - this module writes no matcher;
* the frozen slug texts / ``norm_tokens`` come from the ACCEPTED frozen spec
  ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json`` (never edited);
* the baseline pool and its per-row ``channel`` labels come from the ACCEPTED
  live record ``results/evaluation/retrieval_benchmark/39101217095.json``;
* the v1 verdict is read from the committed v1 record, never recomputed into a
  different number;
* the served-question subject text and the concept-coverage counts are vendored
  exactly the way v1 vendored ``ACCEPTED_SERVED_ID_INDEX.json``: a sha256-pinned,
  blob-proven derivative of the accepted product mount, re-verified against the
  live mount by ``tests/evaluation/test_subject_match_audit.py`` whenever the
  mount is present.

Zero network requests.  Mount optional: with no mount the pinned vendored
extracts are used and the record says so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402
from evaluation.retrieval_gate import gates as rg_gates  # noqa: E402

SCHEMA = "lex-evaluation-subject-match-audit/1"
SUBJECTS_SCHEMA = "lex-evaluation-served-question-subjects/1"
COVERAGE_SCHEMA = "lex-evaluation-question-native-coverage/1"

V1_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS.json"
V2_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2.json"
V2_1_HYPOTHESIS_RELPATH = "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2_1.json"
# Later frozen amendments supersede earlier ones; earlier files are never edited.
HYPOTHESIS_CANDIDATES = (V2_1_HYPOTHESIS_RELPATH, V2_HYPOTHESIS_RELPATH)
V1_RECORD_RELPATH = "results/evaluation/product_counter_recall/39111232991.json"
FROZEN_SPEC_RELPATH = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
BASELINE_RECORD_RELPATH = "results/evaluation/retrieval_benchmark/39101217095.json"
SUBJECTS_RELPATH = "evaluation/subject_match_audit/SERVED_QUESTION_SUBJECTS.json"
COVERAGE_RELPATH = "evaluation/subject_match_audit/QUESTION_NATIVE_COVERAGE.json"

SERVED_PACKET_ID = "38839347028"
DEFAULT_MOUNT_ENVS = ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT")
DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)

EXIT_OK = 0
EXIT_FALSIFIED = 1
EXIT_NOT_MEASURED_OR_VACUOUS = 2
EXIT_ENVIRONMENT = 3

# --------------------------------------------------------------------------- #
# frozen text normalisation (values live in the v2 hypothesis; these are the
# fallbacks used only when no hypothesis file is supplied, e.g. --build-vendored)
# --------------------------------------------------------------------------- #
MIN_CONCEPT_LENGTH = 5

GENERIC_STOPWORDS = [
    "rechtsprechung", "rechtsprech", "jurisprudence", "jurispruden",
    "giurisprudenza", "giurisprudenz", "entscheidung", "entscheidungen",
    "entscheid", "entscheide", "entscheidungen", "decisioni", "decisions",
    "decision", "droit", "schweizer", "svizzero", "svizzera", "suisse",
    "limite", "limites", "limiti", "grenze", "grenzen", "exception",
    "exceptions", "eccezione", "ausnahme", "vorbehalt", "reserve", "riserva",
    "existent", "exist", "bestehen", "beste", "existono", "sog", "ainsi",
    "welche", "quali", "quelles", "dieser", "diesem", "diese", "queste",
    "gegenuber", "auquel", "della", "delle", "dello", "dello", "pour",
    "unter", "welchem", "einer", "eines", "einem", "sowie", "gegen",
    "secondo", "second", "premiere", "primo",
]

# Swiss code abbreviations a norm reference may be written with.  A bare
# number is never harvested, so docket numbers cannot leak in; a number is only
# read as a norm reference when it is introduced either by an article marker
# ("art. 257d", "articolo 2052") or by one of these codes ("CP 257d",
# "c.c. 2052", "OR 321").
NORM_ABBREVIATIONS = (
    "CP", "CO", "OR", "EOG", "StGB", "CC", "ZGB", "ZPO", "BGG", "DBG", "VRG",
    "ORG", "CPG", "StPO", "SchKG", "DSG",
)
_NORM_ALT = "|".join(re.escape(a) for a in NORM_ABBREVIATIONS)
NORM_REF_RE = re.compile(
    r"(?:\bart(?:ikel)?\.?\s*(\d+[a-z]?)\b)"
    r"|(?:\b(?:CC|c\.c\.|" + _NORM_ALT + r")\s*\.?\s*(\d+[a-z]?)\b)",
    re.IGNORECASE,
)

STOPWORDS_SET = set(GENERIC_STOPWORDS)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deaccent(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm_tokens_of(text: str) -> list[str]:
    """Norm/article references in a text, lowercased and de-duplicated.

    Purely lexical: ``art. 257d`` / ``Art. 257d CO`` / ``art. 257d or`` and
    ``CP 257d ss.`` / ``c.c. 2052 ss.`` / ``OR 321 ff.`` all yield the bare
    number; a number that is not introduced by an article marker or by a Swiss
    code abbreviation is NOT harvested, so docket numbers do not leak in.
    """
    out: list[str] = []
    for m in NORM_REF_RE.finditer(deaccent(text)):
        tok = (m.group(1) or m.group(2) or "").lower()
        if tok and tok not in out:
            out.append(tok)
    return out


def content_tokens(text: str) -> list[str]:
    """Content tokens of a text: de-accented, lowercased, alnum-only, length
    filtered, generic-legal stopwords removed.  Deterministic and frozen."""
    toks = re.split(r"[^0-9a-z]+", deaccent(text).lower())
    out: list[str] = []
    for t in toks:
        if len(t) < MIN_CONCEPT_LENGTH or t in STOPWORDS_SET:
            continue
        if t not in out:
            out.append(t)
    return out


def question_concepts(question_text: str) -> list[str]:
    """The frozen core-concept extraction for the question-native check.

    Core concepts of a legal question are the long content words of the question
    text itself: the legal terms the question is about.  Stopwords and the
    generic-legal stoplist are removed; nothing else is added, dropped or
    weighted, and there is no count threshold here - the coverage threshold is
    the frozen ``>=1-of-set`` semantics of the accepted gates.
    """
    return content_tokens(question_text)


def row_match_text(row: dict) -> str:
    return " ".join(
        str(row.get(k) or "")
        for k in ("title", "regeste", "snippet", "full_text", "citation", "decision_id")
    )


# --------------------------------------------------------------------------- #
# mount / vendored inputs
# --------------------------------------------------------------------------- #
def _mount_candidates(explicit: str | None) -> list[Path]:
    if explicit:
        return [Path(explicit)]
    seen: list[Path] = []
    for env in DEFAULT_MOUNT_ENVS:
        val = os.environ.get(env)
        if val:
            seen.append(Path(val))
    seen.extend(Path(p) for p in DEFAULT_MOUNTS)
    return seen


def resolve_product_mount(explicit: str | None = None) -> Path | None:
    for cand in _mount_candidates(explicit):
        if cand.is_dir():
            return cand
    return None


def question_record_path(mount: Path, qid: str) -> Path:
    return (mount / "results" / "product" / "gate_packet" / SERVED_PACKET_ID
            / "questions" / f"{qid}.question.json")


def bundle_path(mount: Path, qid: str) -> Path:
    return (mount / "results" / "product" / "gate_packet" / SERVED_PACKET_ID
            / "questions" / f"{qid}.bundle.json")


SUBJECT_FIELDS = ("legal_area", "question", "hypothesis", "look_for",
                  "counter_authority_needed", "why_this_question")


def build_subjects(mount: Path, qids: list[str]) -> dict:
    """sha256-pinned derivative of the accepted served questions' subject text."""
    out: dict[str, Any] = {}
    for qid in qids:
        path = question_record_path(mount, qid)
        rec = json.loads(path.read_text(encoding="utf-8"))
        adm = rec.get("admissibility") or {}
        meas = adm.get("measured") or {}
        out[qid] = {
            "qid": rec.get("qid"),
            "language": rec.get("language"),
            "legal_area": rec.get("legal_area"),
            "question": rec.get("question"),
            "hypothesis": rec.get("hypothesis"),
            "look_for": rec.get("look_for"),
            "counter_authority_needed": rec.get("counter_authority_needed"),
            "why_this_question": rec.get("why_this_question"),
            "bundle_content_sha256": ((rec.get("bundle") or {}).get("content_sha256")),
            "source_question_json": str(path.relative_to(mount)),
            "source_question_json_sha256": sha256_file(path),
            "product_admissibility": {
                "admissible": adm.get("admissible"),
                "blocking_count": adm.get("blocking_count"),
                "warning_count": adm.get("warning_count"),
            },
            "product_selfcheck": {
                "query_concepts": meas.get("query_concepts"),
                "query_concept_rows": meas.get("query_concept_rows"),
                "query_concepts_under_covered": meas.get("query_concepts_under_covered"),
                "n_decisions": meas.get("n_decisions"),
            },
        }
    return {
        "schema": SUBJECTS_SCHEMA,
        "served_packet_id": SERVED_PACKET_ID,
        "derived_from": "accepted product mount (read-only), sha256-pinned derivative",
        "questions": out,
    }


def build_coverage(mount: Path, subjects: dict, concepts_fn) -> dict:
    """Independent, question-native concept coverage over each served bundle."""
    out: dict[str, Any] = {}
    for qid, entry in (subjects.get("questions") or {}).items():
        bpath = bundle_path(mount, qid)
        bundle = json.loads(bpath.read_text(encoding="utf-8"))
        decisions = bundle.get("decisions") or []
        texts = [deaccent(row_match_text(d)).lower() for d in decisions]
        concepts = concepts_fn(entry.get("question") or "")
        counts = {c: sum(1 for t in texts if c in t) for c in concepts}
        out[qid] = {
            "source_bundle": str(bpath.relative_to(mount)),
            "source_bundle_sha256": sha256_file(bpath),
            "n_rows": len(decisions),
            "concepts": concepts,
            "concept_row_counts": counts,
            "concepts_with_zero_rows": sorted(c for c, n in counts.items() if n == 0),
        }
    return {
        "schema": COVERAGE_SCHEMA,
        "served_packet_id": SERVED_PACKET_ID,
        "derived_from": "accepted product mount (read-only), sha256-pinned derivative",
        "method": "core concepts = de-accented lowercase alnum tokens of the question "
                  "text with len>=5 and the frozen generic stoplist removed; a concept is "
                  "COVERED iff at least one bundle row's (title/regeste/snippet/full_text/"
                  "citation/decision_id) contains it as a substring (conservative: "
                  "substring containment can only over-report coverage)",
        "questions": out,
    }


# --------------------------------------------------------------------------- #
# measurement
# --------------------------------------------------------------------------- #
def _out(gate: str, passed: bool, detail: str, **measured: Any) -> dict:
    return {"gate": gate, "passed": bool(passed), "detail": detail, "measured": measured}


def _baseline_channels(record: dict, slug: str) -> dict[str, list[dict]]:
    """Split the frozen baseline pool by the record's own ``channel`` field."""
    chans: dict[str, list[dict]] = {}
    for q in record.get("queries") or []:
        if q.get("slug") != slug:
            continue
        chans.setdefault(str(q.get("channel") or "unlabelled"), []).extend(
            list(q.get("rows") or []))
    return chans


def subject_axis(cell: dict, slug_spec: dict, subj: dict) -> dict:
    """The two mechanical axes plus the frozen admissibility decision."""
    frozen_side = " ".join(
        [str(v) for v in ((slug_spec.get("queries") or {}).get("baseline") or {}).values()]
        + [str(v) for v in ((slug_spec.get("queries") or {}).get("counter") or {}).values()]
    )
    product_side = " ".join(str(subj.get(f) or "") for f in SUBJECT_FIELDS)

    frozen_norms = sorted({str(t).lower() for t in (slug_spec.get("norm_tokens") or [])})
    frozen_measured_norms = norm_tokens_of(frozen_side)
    for n in frozen_measured_norms:          # merge lexical + declared
        if n not in frozen_norms:
            frozen_norms.append(n)
    frozen_norms = sorted(frozen_norms)
    product_norms = sorted(set(norm_tokens_of(product_side)))

    shared_norms = sorted(set(frozen_norms) & set(product_norms))
    if shared_norms:
        norm_axis = "SAME_NORM"
    elif frozen_norms and product_norms:
        norm_axis = "DIFFERENT_NORM"
    else:
        norm_axis = "UNANCHORED_ON_ONE_SIDE"

    f_tok = set(content_tokens(frozen_side))
    p_tok = set(content_tokens(product_side))
    shared_tokens = sorted(f_tok & p_tok)
    subject_axis_value = "SAME_SUBJECT_TERMS" if shared_tokens else "NO_SHARED_SUBJECT_TERMS"

    declared = bool(cell.get("product_layer_claim_admissible"))
    measured = declared and norm_axis == "SAME_NORM" and subject_axis_value == "SAME_SUBJECT_TERMS"
    if measured:
        scope = "PRODUCT_LAYER_CLAIM_ADMISSIBLE"
    elif declared:
        scope = "DECLARED_ADMISSIBLE_DOWNGRADED_BY_MEASUREMENT"
    else:
        scope = "NOT_ADMISSIBLE_TO_A_PRODUCT_LAYER_CLAIM"

    return {
        "slug": cell["slug"],
        "served_question_id": cell["served_question_id"],
        "frozen_norm_tokens": frozen_norms,
        "product_norm_tokens": product_norms,
        "shared_norm_tokens": shared_norms,
        "norm_axis": norm_axis,
        "shared_content_tokens": shared_tokens,
        "subject_axis": subject_axis_value,
        "declared_product_layer_claim_admissible": declared,
        "declared_reason": cell.get("product_layer_claim_inadmissible_reason"),
        "measured_product_layer_claim_admissible": measured,
        "claim_scope": scope,
        "product_legal_area": subj.get("legal_area"),
        "product_question": subj.get("question"),
    }


def evaluate(hypothesis: dict, spec: dict, baseline_record: dict, v1_record: dict,
             subjects: dict, coverage: dict, subjects_origin: str, coverage_origin: str,
             mount: Path | None, hypothesis_relpath: str = V2_1_HYPOTHESIS_RELPATH) -> dict:
    min_len = int(((spec.get("id_match_rules") or {}).get("min_core_length")) or 6)
    spec_by_slug = {q["slug"]: q for q in spec["questions"]}
    gates: list[dict] = []

    # ---- 1. subject-match admissibility, per mapping cell -------------------- #
    subject_rows: list[dict] = []
    for cell in hypothesis["analyst_mapping_V2_FROZEN_BEFORE_EXECUTION"]["cells"]:
        qid = cell["served_question_id"]
        subj = (subjects.get("questions") or {}).get(qid)
        if subj is None:
            subject_rows.append({"slug": cell["slug"], "served_question_id": qid,
                                 "status": "NOT_MEASURED",
                                 "reason": "served question absent from the pinned subject extract"})
            gates.append({"gate": f"subject_match::{cell['slug']}", "passed": None,
                          "detail": "served question absent from the pinned subject extract; "
                                    "never counted as a pass",
                          "measured": {"served_question_id": qid}})
            continue
        row = subject_axis(cell, spec_by_slug[cell["slug"]], subj)
        row["status"] = "MEASURED"
        subject_rows.append(row)
        gates.append(_out(
            f"subject_match::{cell['slug']}",
            not row["declared_product_layer_claim_admissible"],
            (f"frozen v2 declaration {row['declared_product_layer_claim_admissible']} for "
             f"{cell['slug']}<->{qid} is confirmed by measurement: norm axis "
             f"{row['norm_axis']}, subject axis {row['subject_axis']}; claim scope "
             f"{row['claim_scope']}")
            if not row["declared_product_layer_claim_admissible"] and
            row["claim_scope"] == "NOT_ADMISSIBLE_TO_A_PRODUCT_LAYER_CLAIM"
            else (f"v2 declares product-layer claim admissibility "
                  f"{row['declared_product_layer_claim_admissible']} but measurement says "
                  f"{row['claim_scope']} (norm axis {row['norm_axis']}, subject axis "
                  f"{row['subject_axis']}) - DECLARATION IS NOT SUPPORTED"),
            **{k: row[k] for k in (
                "slug", "served_question_id", "frozen_norm_tokens", "product_norm_tokens",
                "shared_norm_tokens", "norm_axis", "shared_content_tokens", "subject_axis",
                "declared_product_layer_claim_admissible", "measured_product_layer_claim_admissible",
                "claim_scope", "product_legal_area", "product_question")},
        ))

    admissible_cells = [r for r in subject_rows
                        if r.get("status") == "MEASURED" and r.get("measured_product_layer_claim_admissible")]

    # ---- 2. comparator channel split (D2, executed not asserted) ------------- #
    v1_hyp = json.loads((REPO_ROOT / V1_HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    v1_cells = v1_hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]
    index_path = REPO_ROOT / "evaluation" / "product_counter_recall" / "ACCEPTED_SERVED_ID_INDEX.json"
    v1_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else None

    channel_rows: list[dict] = []
    for cell in v1_cells:
        slug = cell["slug"]
        sspec = spec_by_slug.get(slug)
        if sspec is None:
            continue
        chans = _baseline_channels(baseline_record, slug)
        base_rows = chans.get("baseline", [])
        counter_rows = chans.get("counter", [])
        authority_ids = list(sspec.get("authority_ids") or [])
        counter_ids = [r["id"] for r in (sspec.get("known_counter_ids") or [])]

        prod_rows = None
        if v1_index is not None:
            entry = (v1_index.get("questions") or {}).get(cell["served_question_id"])
            if entry is not None:
                prod_rows = list(entry.get("rows") or [])

        def hits(ids: list[str], rows: list[dict]) -> list[str]:
            if not ids or rows is None:
                return []
            m = rg_gates.match_authorities(ids, rows, min_len=min_len)
            return sorted(k for k, v in m.items() if v)

        b_all = hits(counter_ids, base_rows + counter_rows)
        b_base = hits(counter_ids, base_rows)
        b_ctr = hits(counter_ids, counter_rows)
        p_cnt = hits(counter_ids, prod_rows) if prod_rows is not None else None
        a_all = hits(authority_ids, base_rows + counter_rows)
        a_base = hits(authority_ids, base_rows)
        a_ctr = hits(authority_ids, counter_rows)

        channel_rows.append({
            "slug": slug,
            "served_question_id": cell["served_question_id"],
            "n_baseline_channel_rows": len(base_rows),
            "n_counter_channel_rows": len(counter_rows),
            "n_pool_rows_as_scored_by_v1": len(base_rows) + len(counter_rows),
            "counter_channel_query_texts": sorted(
                str(v) for v in ((sspec.get("queries") or {}).get("counter") or {}).values()),
            "known_counter": {
                "n_frozen": len(counter_ids),
                "product_hits": p_cnt,
                "baseline_union_hits": b_all,
                "baseline_channel_only_hits": b_base,
                "counter_channel_only_hits": b_ctr,
                "plain_baseline_channel_is_itself_a_top50_union": True,
                "baseline_only_ids_attributable_to_counter_channel": sorted(
                    set(b_all) - set(b_base)),
            },
            "authority": {
                "n_frozen": len(authority_ids),
                "baseline_union_hits": a_all,
                "baseline_channel_only_hits": a_base,
                "counter_channel_only_hits": a_ctr,
            },
        })
        gates.append(_out(
            f"comparator_channel_split::{slug}",
            "baseline" in chans and "counter" in chans,
            (f"the comparator scored by v1 is the frozen record's baseline U counter pool "
             f"({len(base_rows)}+{len(counter_rows)}={len(base_rows) + len(counter_rows)} rows), not a "
             f"plain top-50; of the known-counter ids the comparator recalls, "
             f"{len(set(b_all) - set(b_base))} are reachable only through the counter channel"),
            slug=slug,
            channels_present=sorted(chans),
            baseline_channel_only_hits=b_base,
            counter_channel_only_hits=b_ctr,
            counter_channel_only_baseline_advantage=sorted(set(b_all) - set(b_base)),
            n_baseline_channel_rows=len(base_rows), n_counter_channel_rows=len(counter_rows),
        ))

    # ---- 3. question-native coverage: no analyst mapping at all ------------- #
    coverage_rows: list[dict] = []
    for qid, entry in sorted((coverage.get("questions") or {}).items()):
        subj = (subjects.get("questions") or {}).get(qid) or {}
        concepts = list(entry.get("concepts") or [])
        counts = dict(entry.get("concept_row_counts") or {})
        zero = sorted(entry.get("concepts_with_zero_rows") or [])
        prod_zero = sorted((subj.get("product_selfcheck") or {}).get("query_concepts_under_covered") or [])
        agreement = sorted(zero) == prod_zero
        coverage_rows.append({
            "served_question_id": qid,
            "n_bundle_rows": entry.get("n_rows"),
            "concepts": concepts,
            "concept_row_counts": counts,
            "concepts_with_zero_rows": zero,
            "product_reported_query_concepts_under_covered": prod_zero,
            "independent_and_product_selfcheck_agree": agreement,
            "product_admissibility": subj.get("product_admissibility"),
        })
        gates.append(_out(
            f"question_native_concept_coverage::{qid}",
            not zero,
            (f"all {len(concepts)} core concepts of the served question retrieve at least one "
             f"of the {entry.get('n_rows')} bundle rows")
            if not zero else
            (f"{len(zero)}/{len(concepts)} core concepts of the served question retrieve ZERO of "
             f"the {entry.get('n_rows')} bundle rows: {zero}"),
            **{k: coverage_rows[-1][k] for k in (
                "served_question_id", "n_bundle_rows", "concepts", "concept_row_counts",
                "concepts_with_zero_rows", "product_reported_query_concepts_under_covered",
                "independent_and_product_selfcheck_agree")},
        ))

    # The decisive, mapping-free product gate: an admitted bundle whose own
    # pre-registered concept self-check reports zero-row concepts and whose
    # admission record carries no warning about it.
    admission_rows: list[dict] = []
    for row in coverage_rows:
        adm = row.get("product_admissibility") or {}
        zero = row.get("concepts_with_zero_rows") or []
        admitted_clean = bool(adm.get("admissible")) and int(adm.get("warning_count") or 0) == 0 \
            and int(adm.get("blocking_count") or 0) == 0
        fires = bool(zero) and admitted_clean
        admission_rows.append({**row, "admitted_without_any_warning": admitted_clean,
                               "admission_gate_fires": fires})
        gates.append(_out(
            f"admission::selfcheck_disagreement::{row['served_question_id']}",
            not fires,
            (f"bundle admitted admissible=True with warning_count=0 and blocking_count=0 while its "
             f"own pre-registered concept self-check reports {len(zero)} concept(s) with zero rows: "
             f"{zero}; the product computed the miss and the admission record does not disclose it")
            if fires else
            (f"no admission gap: zero-row concepts={zero}, warning_count={adm.get('warning_count')}, "
             f"blocking_count={adm.get('blocking_count')}"),
            **{k: admission_rows[-1][k] for k in (
                "served_question_id", "concepts_with_zero_rows",
                "product_reported_query_concepts_under_covered",
                "independent_and_product_selfcheck_agree", "admitted_without_any_warning",
                "admission_gate_fires", "product_admissibility")},
        ))

    # ---- 4. non-vacuity ----------------------------------------------------- #
    battery: list[dict] = []
    first = next((r for r in coverage_rows if r.get("concepts")), None)
    if first is None:
        battery.append({"control": "concept_coverage_gate_is_not_vacuous", "holds": False,
                        "why": "no served question with concepts; NOT_MEASURED, never a pass"})
        battery.append({"control": "oracle_bundle_covers_every_concept", "holds": False,
                        "why": "no served question with concepts; NOT_MEASURED, never a pass"})
    else:
        qid = first["served_question_id"]
        concepts = first["concepts"]
        blanked = _score_concepts(concepts, [])
        holds_blank = len(blanked["covered"]) == 0
        battery.append({
            "control": "concept_coverage_gate_is_not_vacuous",
            "holds": bool(holds_blank),
            "why": (f"scoring a deliberately BLANKED bundle covers {len(blanked['covered'])} of "
                    f"{len(concepts)} core concepts; a gate that passed this input would be vacuous"),
            "served_question_id": qid, "blanked_covered": blanked["covered"],
        })
        oracle_rows = [{"title": c} for c in concepts]
        oracle = _score_concepts(concepts, oracle_rows)
        holds_oracle = len(oracle["covered"]) == len(concepts)
        battery.append({
            "control": "oracle_bundle_covers_every_concept",
            "holds": bool(holds_oracle),
            "why": (f"a payload-equivalence oracle that contains every concept text reaches "
                    f"{len(oracle['covered'])}/{len(concepts)} covered; the gate can go green"),
            "served_question_id": qid, "oracle_covered": oracle["covered"],
        })
    subject_control_ok = any(r.get("norm_axis") == "DIFFERENT_NORM" for r in subject_rows)
    battery.append({
        "control": "subject_match_gate_is_not_vacuous",
        "holds": bool(subject_control_ok),
        "why": ("at least one frozen v2 cell is measured norm_axis=DIFFERENT_NORM against the "
                "product's own question.json, so the admissibility gate demonstrably discriminates; "
                "if every cell measured SAME_NORM the gate would never fire and would be vacuous"),
        "measured_norm_axes": {r.get("slug"): r.get("norm_axis") for r in subject_rows},
    })
    all_hold = all(b["holds"] for b in battery)

# ---- 5. provenance ------------------------------------------------------ #
    pins = hypothesis.get("frozen_inputs") or {}
    v1_sha = sha256_file(REPO_ROOT / V1_RECORD_RELPATH)
    subj_sha = sha256_file(REPO_ROOT / SUBJECTS_RELPATH) if (REPO_ROOT / SUBJECTS_RELPATH).is_file() else None
    cov_sha = sha256_file(REPO_ROOT / COVERAGE_RELPATH) if (REPO_ROOT / COVERAGE_RELPATH).is_file() else None
    pins_match = (
        v1_sha == pins.get("v1_record_sha256")
        and sha256_file(REPO_ROOT / FROZEN_SPEC_RELPATH) == pins.get("frozen_spec_sha256")
        and sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH) == pins.get("baseline_record_sha256")
        and sha256_file(REPO_ROOT / V1_HYPOTHESIS_RELPATH) == pins.get("v1_hypothesis_sha256")
    )
    gates.append(_out(
        "provenance::v1_and_extract_identity",
        pins_match and rg_frozen.load_frozen() is not None,
        (f"every frozen input re-hashes to the value pinned in this hypothesis "
         f"({hypothesis_relpath}: frozen_inputs) and the accepted frozen spec loads; "
         f"the v1 record is read, never re-derived: verdict {v1_record.get('verdict')} "
         f"exit {v1_record.get('exit_code')}")
        if pins_match else
        (f"pinned input digest mismatch: "
         f"v1_record {v1_sha} vs pinned {pins.get('v1_record_sha256')}"),
        instrument_sha256=sha256_file(Path(__file__).resolve()),
        instrument_sha256_pinned=pins.get("instrument_sha256"),
        frozen_spec_sha256=sha256_file(REPO_ROOT / FROZEN_SPEC_RELPATH),
        frozen_sha256_pinned=rg_frozen.FROZEN_SHA256,
        v1_hypothesis_sha256=sha256_file(REPO_ROOT / V1_HYPOTHESIS_RELPATH),
        v1_record=V1_RECORD_RELPATH,
        v1_record_sha256=v1_sha,
        v1_verdict=v1_record.get("verdict"),
        baseline_record=BASELINE_RECORD_RELPATH,
        baseline_record_sha256=sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH),
        subjects_extract=SUBJECTS_RELPATH,
        subjects_extract_sha256=subj_sha,
        subjects_extract_sha256_pinned=pins.get("subjects_extract_sha256"),
        coverage_extract=COVERAGE_RELPATH,
        coverage_extract_sha256=cov_sha,
        coverage_extract_sha256_pinned=pins.get("coverage_extract_sha256"),
        subjects_origin=subjects_origin,
        coverage_origin=coverage_origin,
        served_packet_id=SERVED_PACKET_ID,
        product_mount=str(mount) if mount else None,
    ))

    failed = [g["gate"] for g in gates if g["passed"] is False]
    not_measurable = [g["gate"] for g in gates if g["passed"] is None]
    coverage_failures = [g for g in failed if g.startswith("question_native_concept_coverage::")]
    admission_failures = [g for g in failed if g.startswith("admission::")]
    scope_failures = [g for g in failed if g.startswith("subject_match::")]
    mapping_free_failures = sorted(set(coverage_failures) | set(admission_failures))

    if not all_hold:
        verdict = "ENVIRONMENT_OR_VACUOUS"
    elif mapping_free_failures:
        verdict = ("QUESTION_NATIVE_PRODUCT_DEFECT_ESTABLISHED"
                   if not admissible_cells else
                   "QUESTION_NATIVE_PRODUCT_DEFECT_AND_HARNESS_FALSIFICATION_STAND")
    else:
        verdict = ("HARNESS_FALSIFICATION_STANDS_NO_ADMISSIBLE_PRODUCT_CLAIM"
                   if not admissible_cells else
                   "NO_MAPPING_FREE_PRODUCT_DEFECT_FOUND")

    return {
        "verdict": verdict,
        "exit_code": (EXIT_OK if verdict in ("NO_MAPPING_FREE_PRODUCT_DEFECT_FOUND",)
                      else EXIT_FALSIFIED if verdict != "ENVIRONMENT_OR_VACUOUS"
                      else EXIT_NOT_MEASURED_OR_VACUOUS),
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": len(failed),
        "n_not_measurable": len(not_measurable),
        "failed_gates": failed,
        "not_measurable_gates": not_measurable,
        "mapping_free_failed_gates": mapping_free_failures,
        "gates": gates,
        "subject_match": {
            "rows": subject_rows,
            "admissible_cells": [r["slug"] for r in admissible_cells],
            "n_admissible_cells": len(admissible_cells),
        },
        "comparator_channel_split": channel_rows,
        "question_native_coverage": coverage_rows,
        "admission_gap": admission_rows,
        "v1_harness_result": {
            "run_id": v1_record.get("run_id"),
            "record": V1_RECORD_RELPATH,
            "sha256": sha256_file(REPO_ROOT / V1_RECORD_RELPATH),
            "verdict": v1_record.get("verdict"),
            "exit_code": v1_record.get("exit_code"),
            "status_after_this_audit": "STANDS_AS_A_HARNESS_RESULT; product_layer_claim_admissible="
                                       f"{bool(admissible_cells)}",
        },
        "non_vacuity": {"all_hold": all_hold, "battery": battery},
        "success_rule": hypothesis.get("decision_rule_V2_FROZEN", {}).get("statement"),
        "claim_ceiling": hypothesis.get("claim_ceiling"),
    }


def _score_concepts(concepts: list[str], rows: list[dict]) -> dict:
    texts = [deaccent(row_match_text(r)).lower() for r in rows]
    covered = [c for c in concepts if any(c in t for t in texts)]
    return {"covered": covered, "uncovered": [c for c in concepts if c not in covered]}


# --------------------------------------------------------------------------- #
# entry points
# --------------------------------------------------------------------------- #
def run(run_id: str, out_path: Path | None, mount_arg: str | None = None,
        repo_root: Path = REPO_ROOT) -> tuple[int, dict | None, str]:
    hyp_rel = next((rel for rel in HYPOTHESIS_CANDIDATES if (repo_root / rel).is_file()), None)
    if hyp_rel is None:
        sys.stderr.write("no v2 hypothesis file present\n")
        return EXIT_ENVIRONMENT, None, "no v2 hypothesis"
    hyp_path = repo_root / hyp_rel
    hypothesis = json.loads(hyp_path.read_text(encoding="utf-8"))
    if not hypothesis.get("frozen_before_execution"):
        sys.stderr.write("v2 hypothesis is not marked frozen_before_execution\n")
        return EXIT_ENVIRONMENT, None, "hypothesis not frozen"

    spec = rg_frozen.load_frozen()
    baseline_record = json.loads((repo_root / BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    v1_record = json.loads((repo_root / V1_RECORD_RELPATH).read_text(encoding="utf-8"))

    subj_path = repo_root / SUBJECTS_RELPATH
    cov_path = repo_root / COVERAGE_RELPATH
    mount = resolve_product_mount(mount_arg)
    if mount is not None:
        qids = [c["served_question_id"] for c in
                hypothesis["analyst_mapping_V2_FROZEN_BEFORE_EXECUTION"]["cells"]]
        subjects = build_subjects(mount, qids)
        coverage = build_coverage(mount, subjects, question_concepts)
        subjects_origin = f"rebuilt_live_from_mount:{mount}"
        coverage_origin = f"rebuilt_live_from_mount:{mount}"
    elif subj_path.is_file() and cov_path.is_file():
        subjects = json.loads(subj_path.read_text(encoding="utf-8"))
        coverage = json.loads(cov_path.read_text(encoding="utf-8"))
        subjects_origin = f"vendored_extract:{SUBJECTS_RELPATH}"
        coverage_origin = f"vendored_extract:{COVERAGE_RELPATH}"
    else:
        sys.stderr.write("no accepted product mount and no pinned vendored extracts\n")
        return EXIT_NOT_MEASURED_OR_VACUOUS, None, "no served-question subject data"

    verdict = evaluate(hypothesis, spec, baseline_record, v1_record, subjects, coverage,
                       subjects_origin, coverage_origin, mount, hyp_rel)
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis["direction_version_at_freeze"],
        "entry_point": "python -m evaluation.subject_match_audit",
        "hypothesis": {
            "path": hyp_rel,
            "sha256": sha256_file(hyp_path),
            "frozen_before_execution": True,
            "supersedes": {"path": V1_HYPOTHESIS_RELPATH,
                           "sha256": sha256_file(repo_root / V1_HYPOTHESIS_RELPATH),
                           "note": "v1 is retained byte-unchanged as the record of the first "
                                   "freeze; its declared mappings are RETRACTED by this cycle"},
        },
        "frozen_spec": {
            "path": FROZEN_SPEC_RELPATH,
            "sha256": sha256_file(repo_root / FROZEN_SPEC_RELPATH),
            "frozen_sha256": rg_frozen.FROZEN_SHA256,
        },
        "baseline": {
            "record": BASELINE_RECORD_RELPATH,
            "sha256": sha256_file(repo_root / BASELINE_RECORD_RELPATH),
            "note": "read-only; its own per-query 'channel' field is the channel split label",
        },
        "product": {
            "served_packet_id": SERVED_PACKET_ID,
            "subjects_origin": subjects_origin,
            "coverage_origin": coverage_origin,
            "mount": str(mount) if mount else None,
        },
        "network_requests": 0,
        **verdict,
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        record_path = str(out_path.relative_to(repo_root)) if out_path.is_relative_to(repo_root) else str(out_path)
    else:
        record_path = ""
    return record["exit_code"], record, record_path or ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--build-vendored", action="store_true",
                    help="rebuild and write the pinned served-question subject and coverage extracts")
    ap.add_argument("--qids", default=None,
                    help="comma-separated served question ids (build-vendored only)")
    args = ap.parse_args(argv)

    if args.build_vendored:
        mount = resolve_product_mount(args.product_mount)
        if mount is None:
            sys.stderr.write("no accepted product mount available for --build-vendored\n")
            return EXIT_ENVIRONMENT
        qids = ([q.strip() for q in args.qids.split(",") if q.strip()] if args.qids
                else ["fr-bail-entretien", "de-kapitalverletzung", "it-responsabilita-medica"])
        subjects = build_subjects(mount, qids)
        coverage = build_coverage(mount, subjects, question_concepts)
        written = {}
        for rel, obj in ((SUBJECTS_RELPATH, subjects), (COVERAGE_RELPATH, coverage)):
            dest = REPO_ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                            encoding="utf-8")
            written[rel] = sha256_file(dest)
        print(json.dumps({"written": written, "questions": qids}, indent=1))
        return EXIT_OK

    out = (Path(args.out) if args.out
           else REPO_ROOT / "results" / "evaluation" / "subject_match_audit" / f"{args.run_id}.json")
    code, record, path = run(args.run_id, out, args.product_mount)
    if record is None:
        print(json.dumps({"verdict": "ENVIRONMENT_ERROR", "detail": path}, indent=1))
        return code
    print(json.dumps({
        "run_id": record["run_id"], "record": path, "verdict": record["verdict"],
        "exit_code": record["exit_code"], "n_gates": record["n_gates"],
        "n_passed": record["n_passed"], "n_failed": record["n_failed"],
        "n_not_measurable": record["n_not_measurable"],
        "mapping_free_failed_gates": record["mapping_free_failed_gates"],
        "n_admissible_cells": record["subject_match"]["n_admissible_cells"],
        "non_vacuity_all_hold": record["non_vacuity"]["all_hold"],
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())