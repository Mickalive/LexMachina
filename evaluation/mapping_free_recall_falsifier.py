#!/usr/bin/env python3
"""Mapping-free retrieval / counter-authority falsifier for the query-map MVP.

WHY THIS INSTRUMENT EXISTS
--------------------------
Core Evaluation already owns two retrieval instruments and neither can carry a
product claim:

* ``evaluation/benchmark_retrieval_counter_authority.py`` re-runs the FROZEN
  LABEL and GEOMETRY bar gates against a served packet.  It measures the
  *gate*, not retrieval, and says so in its own claim ceiling.
* ``evaluation/product_counter_recall.py`` produced
  ``results/evaluation/product_counter_recall/39111232991.json`` =
  ``FAIL_PARITY_REGRESSION``, but the accepted correction run 39113690481
  RETRACTED it as a product-layer claim because *no cell is subject-matched to
  the question the product serves*.  Its three cells are driven by the analyst
  ``analyst_mapping_FROZEN_BEFORE_EXECUTION`` block in
  ``evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS.json``.

This instrument closes that hole by making admissibility a HARD PRE-REGISTERED
PREDICATE instead of a property of an analyst mapping.  It enumerates the full
cross product of (frozen slug) x (served question) and admits a pair ONLY when a
mechanical subject match holds.  No analyst mapping is read into any cell; the
mapping file is opened only to digest-pin it and to record that its mapping
block exists and is not consumed.

REUSE-FIRST
-----------
Every measurement rule is imported from accepted lane code and is NOT
re-derived here:

* ``evaluation.subject_match_audit.question_concepts`` - the accepted
  question-native core-concept rule (de-accented lowercase alnum tokens,
  length >= 5, frozen generic stoplist removed).
* ``evaluation.subject_match_audit.row_match_text`` / ``deaccent`` - the
  accepted row text projection.
* ``evaluation.subject_match_audit.norm_tokens_of`` / ``content_tokens`` - the
  accepted tokenisers used by the admissibility predicate.
* ``evaluation.retrieval_gate.gates.row_cores`` - the ACCEPTED id matcher.
* ``evaluation/frozen_bars/RULES_LABEL.json`` ``rubric.scored_statuses`` - the
  FROZEN vocabulary of counter-authority statuses.  Read at run time; never
  hardcoded here, so this instrument introduces no new vocabulary.

The instrument adds no threshold, no bar, no tokeniser, no stoplist and no
re-tuned rule.  Every numeric condition it uses is either an accepted constant
imported from the modules above or an exact structural identity.

CLAIM CEILING (verbatim in force)
---------------------------------
This instrument establishes ONE thing and nothing more: on the exact accepted
packet bytes, whether the served bundles satisfy the frozen mapping-free
gates below.  It does NOT meet, move or re-derive the frozen absolute
LABEL_SOUND or GEOMETRY_SOUND bars (they stay REPORTED-ONLY); it does NOT lift
the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED
on rebuilt-39027045675; it does NOT certify admission of any packet; it does
NOT claim the map helps a jurist; it does NOT re-issue the retracted 39111232991
parity claim; it does NOT build or re-score any candidate for Frontier team
frontier-query-concept-recall.  ``human_gate_ready`` stays false.

Exit codes
----------
0  PASS_NO_FALSIFICATION   - every measured mapping-free gate passed and every
                            non-vacuity control held.
1  PRODUCT_FALSIFIED       - at least one mapping-free gate failed on the exact
                            accepted bytes, naming packet / question / gate /
                            measured values.
2  NOT_MEASURED_VACUOUS    - no bundle could be read, or a non-vacuity control
                            did not hold.  Never a pass, never a bar-met.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import subject_match_audit as SMA  # noqa: E402
from evaluation.retrieval_gate import gates as RG  # noqa: E402

SCHEMA = "lex-evaluation-mapping-free-recall-falsifier/1"
HYPOTHESIS_RELPATH = "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"
FROZEN_SPEC_RELPATH = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"
RETRACTED_MAPPING_RELPATH = "evaluation/PRODUCT_COUNTER_RECALL_HYPOTHESIS.json"
RETRACTED_RECORD_RELPATH = "results/evaluation/product_counter_recall/39111232991.json"
CORRECTION_RECORD_RELPATH = "results/evaluation/subject_match_audit/39113690481.json"

DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)
PACKETS = ("38839347028", "rebuilt-39027045675")

EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_VACUOUS = 2

CLAIM_CEILING = (
    "This instrument establishes exactly one thing: on the exact accepted packet bytes, "
    "whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, "
    "move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay "
    "REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 "
    "nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675. It does NOT certify admission of any "
    "packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that "
    "remains the human product gate's question. It does NOT re-issue the retracted 39111232991 "
    "parity claim. It builds and re-scores no candidate for Frontier team "
    "frontier-query-concept-recall. human_gate_ready stays false. It runs no obsolete "
    "universal-174k geometry benchmark."
)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_environment() -> dict[str, Any]:
    """Factory-wide requirement 30: disclose the numeric environment."""
    import platform

    env: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "byteorder": sys.byteorder,
    }
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:  # pragma: no cover - environment disclosure only
            env[mod] = "NOT_IMPORTABLE"
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[var] = os.environ.get(var, "unset")
    try:
        env["blas"] = str(__import__("numpy").__config__.get_info("blas_opt_info"))[:400]
    except Exception:  # pragma: no cover
        env["blas"] = "NOT_AVAILABLE"
    return env


def _gate(name: str, passed: bool | None, detail: str, **measured: Any) -> dict:
    return {"gate": name, "passed": passed, "detail": detail, "measured": measured}


def resolve_mount(explicit: str | None) -> Path | None:
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    for var in ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT"):
        if os.environ.get(var):
            cands.append(Path(os.environ[var]))
    cands.extend(Path(p) for p in DEFAULT_MOUNTS)
    for c in cands:
        if c.is_dir():
            return c
    return None


def mount_head(mount: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:  # pragma: no cover
        return None


def packet_paths(mount: Path, packet: str, qid: str) -> tuple[Path, Path]:
    base = mount / "results" / "product" / "gate_packet" / packet / "questions"
    return base / f"{qid}.bundle.json", base / f"{qid}.admissibility.json"


def served_question_ids(mount: Path, packet: str) -> list[str]:
    base = mount / "results" / "product" / "gate_packet" / packet / "questions"
    if not base.is_dir():
        return []
    return sorted(p.name[: -len(".question.json")]
                  for p in base.glob("*.question.json"))


# --------------------------------------------------------------------------- #
# the frozen admissibility predicate (mapping-free)
# --------------------------------------------------------------------------- #
def slug_query_text(slug_spec: dict) -> str:
    q = slug_spec.get("queries") or {}
    parts: list[str] = []
    for channel in ("baseline", "counter"):
        for lang, text in (q.get(channel) or {}).items():
            parts.append(f"{channel} {lang} {text}")
    return " ".join(parts)


def slug_norm_tokens(slug_spec: dict) -> list[str]:
    """Declared norm tokens merged with lexically harvested ones.

    Identical merge to ``SMA.subject_axis``; no new regex or norm vocabulary.
    """
    declared = {str(t).lower() for t in (slug_spec.get("norm_tokens") or [])}
    merged = set(declared)
    merged.update(SMA.norm_tokens_of(slug_query_text(slug_spec)))
    return sorted(merged)


def question_subject_text(rec: dict) -> str:
    return " ".join(str(rec.get(f) or "") for f in SMA.SUBJECT_FIELDS)


def admissibility(slug_spec: dict, qrec: dict) -> dict:
    """The frozen predicate.  Returns the two mechanical axes and the decision."""
    frozen_side = slug_query_text(slug_spec)
    product_side = question_subject_text(qrec)

    frozen_norms = set(slug_norm_tokens(slug_spec))
    product_norms = set(SMA.norm_tokens_of(product_side))
    shared_norms = sorted(frozen_norms & product_norms)
    if shared_norms:
        norm_axis = "SAME_NORM"
    elif frozen_norms and product_norms:
        norm_axis = "DIFFERENT_NORM"
    else:
        norm_axis = "UNANCHORED_ON_ONE_SIDE"

    shared_terms = sorted(set(SMA.content_tokens(frozen_side))
                          & set(SMA.content_tokens(product_side)))
    subject_axis = "SAME_SUBJECT_TERMS" if shared_terms else "NO_SHARED_SUBJECT_TERMS"

    admitted = bool(shared_norms) and subject_axis == "SAME_SUBJECT_TERMS"
    return {
        "slug": slug_spec.get("slug"),
        "served_question_id": qrec.get("qid"),
        "norm_axis": norm_axis,
        "shared_norm_tokens": shared_norms,
        "subject_axis": subject_axis,
        "shared_content_tokens": shared_terms,
        "admitted": admitted,
        "claim_scope": ("MAPPING_FREE_MEASURED" if admitted
                        else "NOT_MEASURED_ADMISSIBILITY"),
    }


# --------------------------------------------------------------------------- #
# mapping-free gates
# --------------------------------------------------------------------------- #
def concept_coverage(qrec: dict, bundle: dict) -> dict:
    decisions = bundle.get("decisions") or []
    texts = [SMA.deaccent(SMA.row_match_text(d)).lower() for d in decisions]
    concepts = SMA.question_concepts(str(qrec.get("question") or ""))
    counts = {c: sum(1 for t in texts if c in t) for c in concepts}
    zero = sorted(c for c, n in counts.items() if n == 0)
    return {"n_rows": len(decisions), "concepts": concepts,
            "concept_row_counts": counts, "concepts_with_zero_rows": zero,
            "n_concepts": len(concepts), "n_zero": len(zero)}


def admission_disclosure(cov: dict, adm: dict) -> dict:
    """Frozen rule: the packet's own admission record must disclose every
    zero-row concept THIS instrument measured.  Disclosed means the record's
    ``measured.query_concepts_under_covered`` names it, or a finding whose text
    names it while ``warning_count > 0``."""
    zero = list(cov["concepts_with_zero_rows"])
    measured = ((adm.get("measured") or {}).get("query_concepts_under_covered") or [])
    measured_set = {str(m) for m in measured}
    findings = adm.get("findings") or []
    blob = json.dumps(findings, ensure_ascii=False).lower()
    warning_count = adm.get("warning_count")
    finding_named = bool(findings) and isinstance(warning_count, int) and warning_count > 0
    undisclosed = [c for c in zero
                   if c not in measured_set and not (finding_named and c.lower() in blob)]
    return {
        "zero_row_concepts": zero,
        "product_reported_query_concepts_under_covered": sorted(measured_set),
        "product_warning_count": warning_count,
        "product_finding_count": len(findings),
        "undisclosed_zero_row_concepts": undisclosed,
        "n_undisclosed": len(undisclosed),
    }


def source_validity(bundle: dict) -> dict:
    decisions = bundle.get("decisions") or []
    bad = [str(d.get("decision_id") or d.get("canonical_url") or "")[:80]
           for d in decisions
           if not str(d.get("decision_id") or "").strip()
           or not str(d.get("canonical_url") or "").strip()]
    return {"n_rows": len(decisions), "n_rows_missing_id_or_url": len(bad),
            "examples": bad[:5]}


def duplicate_suppression(bundle: dict) -> dict:
    decisions = bundle.get("decisions") or []
    ids = [str(d.get("decision_id") or "") for d in decisions]
    distinct = len(set(ids))
    return {"n_rows": len(decisions), "n_distinct_decision_ids": distinct,
            "duplicates": len(ids) - distinct}


def counter_authority_surface(bundle: dict, scored_statuses: list[str]) -> dict:
    decisions = bundle.get("decisions") or []
    issued: list[dict] = []
    for d in decisions:
        status = str(d.get("counter_status") or "").strip().lower()
        if status in {str(s).strip().lower() for s in scored_statuses}:
            issued.append(d)
    empty = [str(d.get("decision_id") or "")[:80] for d in issued
             if not str(d.get("counter_evidence") or "").strip()]
    return {"n_issued": len(issued), "n_with_empty_evidence": len(empty),
            "empty_evidence_examples": empty[:5],
            "statuses_seen": sorted({str(d.get("counter_status") or "") for d in issued}),
            "scored_statuses_from_frozen_rubric": list(scored_statuses)}


def language_robustness(bundle: dict) -> dict:
    decisions = bundle.get("decisions") or []
    dist: dict[str, int] = {}
    for d in decisions:
        lang = str(d.get("language") or "").strip() or "UNLABELLED"
        dist[lang] = dist.get(lang, 0) + 1
    return {"n_rows": len(decisions), "language_distribution": dist,
            "n_distinct_languages": len(dist)}


# --------------------------------------------------------------------------- #
# non-vacuity controls (frozen)
# --------------------------------------------------------------------------- #
def non_vacuity(questions: list[dict], scored_statuses: list[str]) -> dict:
    controls: list[dict] = []

    # Control A - a deliberately BLANKED pool must fail concept coverage.
    any_q = questions[0]
    blank_cov = concept_coverage(any_q["question_record"], {"decisions": []})
    a_fails = blank_cov["n_zero"] == blank_cov["n_concepts"] and blank_cov["n_concepts"] > 0
    controls.append({
        "control": "A_blanked_pool_must_fail_concept_coverage",
        "holds": a_fails,
        "why": f"a deliberately BLANKED pool leaves {blank_cov['n_zero']}/{blank_cov['n_concepts']} "
               f"core concepts of {any_q['qid']} uncovered; a gate that passed it would be vacuous",
        "measured": {"n_concepts": blank_cov["n_concepts"], "n_zero": blank_cov["n_zero"]},
    })

    # Control A2 - the blanked pool must also fail source validity.
    blank_src = source_validity({"decisions": [{"decision_id": "", "canonical_url": ""}]})
    a2 = blank_src["n_rows_missing_id_or_url"] == 1
    controls.append({
        "control": "A2_blanked_row_must_fail_source_validity",
        "holds": a2,
        "why": "a served row with no decision_id and no canonical_url fails source validity",
        "measured": blank_src,
    })

    # Control C - an ORACLE pool built from the question's own concepts must pass.
    oracle_rows = [{"title": c, "decision_id": f"oracle_{c}_0001",
                    "canonical_url": f"https://example.invalid/{c}"} for c in any_q["coverage"]["concepts"]]
    oracle_cov = concept_coverage(any_q["question_record"], {"decisions": oracle_rows})
    c_ok = oracle_cov["n_zero"] == 0 and oracle_cov["n_concepts"] > 0
    controls.append({
        "control": "C_oracle_pool_must_pass_concept_coverage",
        "holds": c_ok,
        "why": f"an oracle pool built from the {oracle_cov['n_concepts']} core concepts of "
               f"{any_q['qid']} covers {oracle_cov['n_concepts'] - oracle_cov['n_zero']}/"
               f"{oracle_cov['n_concepts']}; the concept rule can go green, so a zero is a "
               f"real signal and not an artefact of a broken rule",
        "measured": {"n_concepts": oracle_cov["n_concepts"], "n_zero": oracle_cov["n_zero"]},
    })

    # Control B - a deliberately subject-SWAPPED pair must be rejected.
    b_ok = True
    b_detail: list[dict] = []
    if len(questions) >= 2:
        for i in range(len(questions)):
            for j in range(len(questions)):
                if i == j:
                    continue
                spec = {"slug": f"SWAPPED_{questions[i]['qid']}",
                        "queries": {"baseline": {"xx": questions[j]["question_record"].get("question") or ""},
                                    "counter": {}}}
                verdict = admissibility(spec, questions[i]["question_record"])
                b_detail.append({"swapped_into": questions[i]["qid"],
                                 "subject_taken_from": questions[j]["qid"],
                                 "admitted": verdict["admitted"]})
                if verdict["admitted"]:
                    b_ok = False
    controls.append({
        "control": "B_admissibility_predicate_must_reject_a_subject_swapped_pair",
        "holds": b_ok,
        "why": "every ordered (frozen text, served question) swap across the served question set "
               "must be rejected by the predicate; if any swap is admitted the predicate is vacuous",
        "measured": {"n_swaps": len(b_detail), "n_admitted": sum(1 for d in b_detail if d["admitted"])},
    })

    return {"all_hold": all(c["holds"] for c in controls), "battery": controls}


# --------------------------------------------------------------------------- #
# main measurement pass
# --------------------------------------------------------------------------- #
def measure(mount: Path, repo: Path, packets: tuple[str, ...]) -> dict:
    spec = json.loads((repo / FROZEN_SPEC_RELPATH).read_text(encoding="utf-8"))
    rules = json.loads((repo / RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored_statuses = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])
    min_core = int(((spec.get("id_match_rules") or {}).get("min_core_length")) or 6)

    results: list[dict] = []
    for packet in packets:
        for qid in served_question_ids(mount, packet):
            bpath, apath = packet_paths(mount, packet, qid)
            if not bpath.is_file():
                continue
            bundle = json.loads(bpath.read_text(encoding="utf-8"))
            adm = json.loads(apath.read_text(encoding="utf-8")) if apath.is_file() else {}
            qrec = {"qid": qid}
            qjson = bpath.with_name(f"{qid}.question.json")
            if qjson.is_file():
                qrec = json.loads(qjson.read_text(encoding="utf-8"))
                qrec["qid"] = qid

            cov = concept_coverage(qrec, bundle)
            gates = [
                _gate(f"mf::concept_coverage::{packet}::{qid}",
                      cov["n_zero"] == 0,
                      f"{cov['n_zero']}/{cov['n_concepts']} core concepts of the served question "
                      f"retrieve ZERO served rows",
                      **cov),
                _gate(f"mf::admission_disclosure::{packet}::{qid}",
                      admission_disclosure(cov, adm)["n_undisclosed"] == 0,
                      f"{admission_disclosure(cov, adm)['n_undisclosed']} zero-row concept(s) "
                      f"are not disclosed by the packet's own admission record",
                      **admission_disclosure(cov, adm)),
                _gate(f"mf::source_validity::{packet}::{qid}",
                      source_validity(bundle)["n_rows_missing_id_or_url"] == 0,
                      f"{source_validity(bundle)['n_rows_missing_id_or_url']} served row(s) lack a "
                      f"decision_id or a canonical_url", **source_validity(bundle)),
                _gate(f"mf::duplicate_suppression::{packet}::{qid}",
                      duplicate_suppression(bundle)["duplicates"] == 0,
                      f"{duplicate_suppression(bundle)['duplicates']} duplicate decision_id(s) in the "
                      f"served pool", **duplicate_suppression(bundle)),
                _gate(f"mf::counter_authority_surface::{packet}::{qid}",
                      (counter_authority_surface(bundle, scored_statuses)["n_issued"] >= 1
                       and counter_authority_surface(bundle, scored_statuses)["n_with_empty_evidence"] == 0),
                      f"{counter_authority_surface(bundle, scored_statuses)['n_issued']} counter-authority "
                      f"row(s) issued, {counter_authority_surface(bundle, scored_statuses)['n_with_empty_evidence']} "
                      f"with empty evidence",
                      **counter_authority_surface(bundle, scored_statuses)),
            ]
            gates.append(_gate(f"mf::language_robustness::{packet}::{qid}", None,
                               "REPORTED, never a pass/fail: frozen FR/DE/IT recall defects are owned by "
                               "Frontier team frontier-query-concept-recall and are NOT re-scored here",
                               **language_robustness(bundle)))
            results.append({
                "packet": packet, "qid": qid,
                "bundle_sha256": sha256_file(bpath),
                "admissibility_sha256": sha256_file(apath) if apath.is_file() else None,
                "coverage": cov, "question_record": qrec, "bundle": bundle,
                "gates": gates,
            })

    # admissible-only frozen id-set overlap, over the FULL cross product
    overlap: list[dict] = []
    for slug_spec in spec.get("questions") or []:
        for packet in packets:
            for entry in [r for r in results if r["packet"] == packet]:
                verdict = admissibility(slug_spec, entry["question_record"])
                row = dict(verdict)
                row["packet"] = packet
                row["label"] = "NOT_A_PARITY_CLAIM: a raw overlap count only; this is NOT a comparison " \
                               "against the plain OpenCaseLaw baseline and does NOT re-issue the retracted " \
                               "39111232991 parity claim"
                if verdict["admitted"]:
                    cores: set[str] = set()
                    for d in entry["bundle"].get("decisions") or []:
                        cores |= RG.row_cores({
                            "decision_id": d.get("decision_id"),
                            "canonical_decision_id": d.get("canonical_decision_id"),
                            "docket_number": d.get("docket_number"),
                            "court": d.get("court"),
                            "canonical_url": d.get("canonical_url"),
                            "citation_string_de": str(d.get("citation") or ""),
                            "citation_string_fr": "", "citation_string_it": "",
                        }, min_core)
                    auth = sorted(cores & set(RG.frozen.alnum_core(i) for i in (slug_spec.get("authority_ids") or [])))
                    ctr = sorted(cores & set(RG.frozen.alnum_core(i) for i in (slug_spec.get("known_counter_ids") or [])))
                    row.update({
                        "n_bundle_cores": len(cores),
                        "n_frozen_authority_ids": len(slug_spec.get("authority_ids") or []),
                        "n_frozen_known_counter_ids": len(slug_spec.get("known_counter_ids") or []),
                        "frozen_authority_ids_present": auth,
                        "frozen_counter_ids_present": ctr,
                        "authority_recall": f"{len(auth)}/{len(slug_spec.get('authority_ids') or [])}",
                        "counter_recall": f"{len(ctr)}/{len(slug_spec.get('known_counter_ids') or [])}",
                    })
                else:
                    row.update({"note": "contributes ZERO to every aggregate and every claim"})
                overlap.append(row)

    n_admissible = sum(1 for r in overlap if r["admitted"])
    return {"spec_sha256": sha256_file(repo / FROZEN_SPEC_RELPATH),
            "rules_label_sha256": sha256_file(repo / RULES_LABEL_RELPATH),
            "scored_statuses_from_frozen_rubric": scored_statuses,
            "packets": list(packets), "questions": results, "frozen_id_overlap": overlap,
            "n_pairs_enumerated": len(overlap), "n_pairs_admissible": n_admissible}


def verdict_of(measured: dict, vac: dict) -> tuple[str, int]:
    if not measured["questions"]:
        return "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    if not vac["all_hold"]:
        return "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    failed = [g for q in measured["questions"] for g in q["gates"] if g["passed"] is False]
    if failed:
        return "PRODUCT_FALSIFIED", EXIT_FALSIFIED
    return "PASS_NO_FALSIFICATION", EXIT_PASS


def _emit(out: Path | None, record: dict) -> None:
    """Write the artifact of record on EVERY exit path.

    A refusal that writes no record is unreproducible from the committed tree:
    the report-of-record's own command could not re-derive its committed
    artifact.  The vacuous/environment exit is therefore as claim-bearing as
    the passing one and is written identically.
    """
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")


def run(run_id: str, out: Path, mount_arg: str | None, repo: Path,
        packets: tuple[str, ...]) -> tuple[int, dict]:
    freeze = json.loads((repo / FREEZE_RELPATH).read_text(encoding="utf-8"))
    mount = resolve_mount(mount_arg)
    if mount is None:
        rec = {
            "schema": SCHEMA, "run_id": run_id, "verdict": "NOT_MEASURED_VACUOUS",
            "exit_code": EXIT_VACUOUS,
            "frozen_hypothesis": {"path": HYPOTHESIS_RELPATH,
                                  "sha256": sha256_file(repo / HYPOTHESIS_RELPATH)},
            "freeze_record": {"path": FREEZE_RELPATH, "sha256": sha256_file(repo / FREEZE_RELPATH)},
            "entry_point": "python -m evaluation.mapping_free_recall_falsifier",
            "detail": "no accepted product mount available; admission of a packet is never certified "
                      "from an absent input, and this exit is NOT a pass",
            "not_a_pass": True, "human_gate_ready": False, "packet_admitted": False,
            "machine_gate_ready": False, "ready_for_owner_session": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        _emit(out, rec)
        return EXIT_VACUOUS, rec

    before = {rel: sha256_file(repo / rel) for rel in freeze["frozen_repo_input_digests_before_execution"]
              if (repo / rel).is_file()}
    mount_before: dict[str, str] = {}
    for rel, _digest in freeze["frozen_mount_input_digests_before_execution"].items():
        if rel == "mount":
            continue
        p = mount / rel
        if p.is_file():
            mount_before[rel] = sha256_file(p)

    measured = measure(mount, repo, packets)
    vac = non_vacuity(measured["questions"], measured["scored_statuses_from_frozen_rubric"])
    verdict, code = verdict_of(measured, vac)

    after = {rel: sha256_file(repo / rel) for rel in freeze["frozen_repo_input_digests_before_execution"]
             if (repo / rel).is_file()}
    mount_after: dict[str, str] = {}
    for rel in mount_before:
        mount_after[rel] = sha256_file(mount / rel)

    drift = sorted({rel for rel, d in before.items() if after.get(rel) != d}
                   | {rel for rel, d in mount_before.items() if mount_after.get(rel) != d})

    # The analyst mapping block is recorded as NOT consumed, and is provably not
    # in the input path of any gate: this instrument never reads it.
    mapping_rel = json.loads((repo / RETRACTED_MAPPING_RELPATH).read_text(encoding="utf-8"))
    mapping_blocks = sorted(k for k in mapping_rel
                            if "analyst_mapping" in k.lower())

    gates = [g for q in measured["questions"] for g in q["gates"]]
    failed = [g for g in gates if g["passed"] is False]
    record = {
        "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
        "direction_version": 57, "verdict": verdict, "exit_code": code,
        "entry_point": "python -m evaluation.mapping_free_recall_falsifier",
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_hypothesis": {"path": HYPOTHESIS_RELPATH,
                              "sha256": sha256_file(repo / HYPOTHESIS_RELPATH)},
        "freeze_record": {"path": FREEZE_RELPATH, "sha256": sha256_file(repo / FREEZE_RELPATH)},
        "product_mount": str(mount), "product_mount_head": mount_head(mount),
        "packets_measured": list(packets),
        "rehash_before_execution": {"repo": before, "mount": mount_before},
        "rehash_after_execution": {"repo": after, "mount": mount_after},
        "input_drift": drift,
        "input_drift_invalidates_run": bool(drift),
        "numeric_environment": numeric_environment(),
        "frozen_spec": {"path": FROZEN_SPEC_RELPATH, "sha256": measured["spec_sha256"]},
        "frozen_label_rubric": {"path": RULES_LABEL_RELPATH, "sha256": measured["rules_label_sha256"],
                                "scored_statuses": measured["scored_statuses_from_frozen_rubric"]},
        "analyst_mapping_not_consumed": {
            "path": RETRACTED_MAPPING_RELPATH,
            "sha256": sha256_file(repo / RETRACTED_MAPPING_RELPATH),
            "mapping_blocks_present": mapping_blocks,
            "read_into_any_gate": False,
            "how_enforced": "this module never reads the mapping file for a value; it opens it only "
                            "to list which mapping blocks exist and to digest-pin the bytes",
        },
        "retraction_provenance": {
            "retracted_record": RETRACTED_RECORD_RELPATH,
            "retracted_record_sha256": sha256_file(repo / RETRACTED_RECORD_RELPATH),
            "correction_record": CORRECTION_RECORD_RELPATH,
            "correction_record_sha256": sha256_file(repo / CORRECTION_RECORD_RELPATH),
            "why": "the 39111232991 FAIL_PARITY_REGRESSION result stands as a HARNESS result and does "
                   "NOT establish a product-layer recall defect, because no cell is subject-matched to "
                   "the question the product serves; this instrument therefore refuses any analyst "
                   "mapping and admits only mechanically matched pairs",
        },
        "n_questions_measured": len(measured["questions"]),
        "n_gates": len(gates), "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": len(failed), "n_reported": sum(1 for g in gates if g["passed"] is None),
        "failed_gates": [{"gate": g["gate"], "detail": g["detail"], "measured": g["measured"]}
                         for g in failed],
        "gates": gates,
        "per_question": [{"packet": q["packet"], "qid": q["qid"],
                          "bundle_sha256": q["bundle_sha256"],
                          "admissibility_sha256": q["admissibility_sha256"],
                          "concepts": q["coverage"]["concepts"],
                          "concepts_with_zero_rows": q["coverage"]["concepts_with_zero_rows"],
                          "concept_row_counts": q["coverage"]["concept_row_counts"]}
                         for q in measured["questions"]],
        "admissibility": {
            "rule": "SAME_NORM AND SAME_SUBJECT_TERMS, computed at run time with no analyst judgement",
            "n_pairs_enumerated": measured["n_pairs_enumerated"],
            "n_pairs_admissible": measured["n_pairs_admissible"],
            "pairs": measured["frozen_id_overlap"],
        },
        "non_vacuity": vac,
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "claim_ceiling": CLAIM_CEILING,
        "human_gate_ready": False, "packet_admitted": False,
        "machine_gate_ready": False, "ready_for_owner_session": False,
    }
    _emit(out, record)
    return code, record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--product-mount", default=None)
    ap.add_argument("--packets", default=",".join(PACKETS))
    args = ap.parse_args(argv)
    packets = tuple(p.strip() for p in args.packets.split(",") if p.strip())
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "mapping_free_recall_falsifier" / f"{args.run_id}.json")
    code, rec = run(args.run_id, out, args.product_mount, REPO_ROOT, packets)
    print(json.dumps({
        "verdict": rec.get("verdict"), "exit_code": code,
        "n_questions_measured": rec.get("n_questions_measured"),
        "n_gates": rec.get("n_gates"), "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"), "n_reported": rec.get("n_reported"),
        "input_drift": rec.get("input_drift"),
        "non_vacuity_all_hold": (rec.get("non_vacuity") or {}).get("all_hold"),
        "n_pairs_admissible": ((rec.get("admissibility") or {}).get("n_pairs_admissible")),
        "failed_gates": [g["gate"] for g in rec.get("failed_gates") or []],
        "record": str(out),
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())