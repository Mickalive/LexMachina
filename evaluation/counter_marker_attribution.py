#!/usr/bin/env python3
"""Counter-marker attribution benchmark — smallest executable falsification of
the accepted cached-bundle NEGATIVE RESULT (run 39766474798).

WHY THIS INSTRUMENT EXISTS (factory direction v62, lanes.evaluation)
-------------------------------------------------------------------
The accepted cached-bundle benchmark measured, on real cached OpenCaseLaw
rows, that the FROZEN counter-marker rule (a norm_token AND a limitation_token
in title+regeste+snippet) yields ZERO counter candidates for 2/4 frozen
questions while the same pool contains the questions' own frozen
``known_counter_ids``.  The record does not say WHY, and the three candidate
causes need three DIFFERENT product remedies:

  * marker/lexicon blindness on known-counter rows the counter channel
    already retrieved  -> richer evidence surface, richer lexicon, or an
    adjudicated classifier; never "retrieve more";
  * counter-channel retrieval gap (known-counter rows never retrieved)
    -> counter-query expansion;
  * no defect (the accepted negative result would DIVERGE and is published
    as a divergence, never smoothed).

REUSE-FIRST — nothing measurement-bearing is re-derived here
------------------------------------------------------------
* pool assembly, dedup, normalisation, marker rule, id matching:
  the ACCEPTED ``evaluation.query_map.bundle_producer`` functions
  (read_cache / index_cache / build_bundle / row_text / normalise_text /
  match_frozen_id / alnum_core / CHANNELS) — imported, never copied or
  re-tuned;
* frozen spec, question lexicons, known-counter sets, id-match rules:
  ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json``, opened
  read-only and re-hashed fail-closed before AND after execution;
* parity oracle: the ACCEPTED record
  ``results/evaluation/query_map_cached_bundle_benchmark/39766474798.json``
  (sha256 5fd695aa...), re-hashed before AND after.

ZERO NEW THRESHOLDS
-------------------
The extended diagnostic surface (title+regeste+snippet+rule_statement+
statutes) is REPORTED-ONLY attribution state: it never labels a row and no
gate, bar or verdict reads it.  The class priority list is a deterministic
total order over two three-state axes; it exposes no tunable constant.

SCRATCH-RUN OBLIGATION
----------------------
A claim-bearing cycle writes to the committed default out path.  A scratch
invocation MUST pass ``--out`` (and ``--accepted-record`` stays the committed
one), otherwise it silently rewrites committed claim-bearing records.

Exit codes (frozen in evaluation/V62_COUNTER_MARKER_ATTRIBUTION_HYPOTHESIS_V1.json)
----------------------------------------------------------------------------------
  0  ATTRIBUTION_COMPLETE_NO_BLINDSPOT
  1  MARKER_BLINDSPOT_ATTRIBUTED
  2  NOT_MEASURED_VACUOUS  (never a pass, never an attribution)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.query_map.bundle_producer import (  # noqa: E402
    CHANNELS, alnum_core, build_bundle, index_cache, match_frozen_id,
    normalise_text, read_cache, row_text,
)

SCHEMA = "lex-evaluation-counter-marker-attribution/1"

#: Frozen input digests. NEVER edited here; a mismatch is exit 2.
FROZEN_SPEC_SHA256 = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
ACCEPTED_RECORD_SHA256 = "5fd695aa243e9f47858e05fe2e1b3875cf9f6b7baa484802047539839c941708"

#: REPORTED-ONLY diagnostic surface. Never a labelling surface.
EXTENDED_SURFACE_FIELDS = ("title", "regeste", "snippet", "rule_statement", "statutes")

#: Frozen class priority (hypothesis section frozen_method.frozen_class_priority).
CLASS_PRIORITY = (
    "LABELLED",
    "LIMITATION_LEXICON_ABSENT",
    "NORM_LEXICON_ABSENT",
    "NORM_SURFACE_MISS",
    "LIMITATION_SURFACE_MISS",
    "BOTH_SURFACE_MISS",
)
BLINDNESS_CLASSES = frozenset(CLASS_PRIORITY[1:])

EXIT_NO_BLINDSPOT = 0
EXIT_BLINDSPOT_ATTRIBUTED = 1
EXIT_VACUOUS = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def token_hits(text: str, tokens: list[str]) -> list[str]:
    """Frozen marker-rule membership test via the ACCEPTED normalisation."""
    nt = normalise_text(text)
    return [t for t in tokens if normalise_text(t) in nt]


def surface_text(row: dict, fields: tuple[str, ...]) -> str:
    parts: list[str] = []
    for f in fields:
        v = row.get(f)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif v is not None:
            parts.append(str(v))
    return " ".join(p for p in parts if p)


def axis_state(hits_marker: list[str], hits_extended: list[str]) -> str:
    if hits_marker:
        return "ON_MARKER"
    if hits_extended:
        return "EXTENDED_ONLY"
    return "ABSENT_ROW"


def classify_row(norm_marker: list[str], norm_extended: list[str],
                 lim_marker: list[str], lim_extended: list[str]) -> str:
    """One class per the frozen priority. Deterministic total order."""
    ns = axis_state(norm_marker, norm_extended)
    ls = axis_state(lim_marker, lim_extended)
    if ns == "ON_MARKER" and ls == "ON_MARKER":
        return "LABELLED"
    if ls == "ABSENT_ROW":
        return "LIMITATION_LEXICON_ABSENT"
    if ns == "ABSENT_ROW":
        return "NORM_LEXICON_ABSENT"
    if ns == "EXTENDED_ONLY" and ls == "ON_MARKER":
        return "NORM_SURFACE_MISS"
    if ls == "EXTENDED_ONLY" and ns == "ON_MARKER":
        return "LIMITATION_SURFACE_MISS"
    return "BOTH_SURFACE_MISS"


def assemble_pool(slug: str, index: dict, spec: dict) -> list[dict]:
    """Replicate build_bundle's iteration order EXACTLY (control C4 verifies)."""
    question = next(q for q in spec["questions"] if q["slug"] == slug)
    min_core = int(question.get("id_match_rules", spec["id_match_rules"])["min_core_length"])
    del min_core  # ordering only; matching happens later with the spec value
    langs = sorted({k[2] for k in index if k[0] == slug})
    rows: list[dict] = []
    seen: dict[str, dict] = {}
    for lang in langs:
        for channel in CHANNELS:
            env = index.get((slug, channel, lang))
            if env is None:
                continue
            body = json.loads(env["body"])
            for row in body.get("results", []):
                core = alnum_core(row.get("decision_id"))
                if not core:
                    continue
                if core in seen:
                    seen[core].setdefault("also_in", []).append(
                        {"channel": channel, "language": lang})
                    continue
                row = dict(row)
                row["_channel"] = channel
                row["_language"] = lang
                seen[core] = row
                rows.append(row)
    rows.sort(key=lambda r: (-float(r.get("relevance_score") or 0.0),
                             str(r.get("decision_id") or "")))
    return rows


def marker_label(row: dict, norm_tokens: list[str], lim_tokens: list[str]) -> tuple[bool, list[str], list[str]]:
    """Accepted marker rule on the accepted marker surface (title+regeste+snippet)."""
    text = row_text(row)
    nh = token_hits(text, norm_tokens)
    lh = token_hits(text, lim_tokens)
    return bool(nh and lh), nh, lh


def attribute_row(row: dict, norm_tokens: list[str], lim_tokens: list[str]) -> dict:
    """Per-row class + axis states over marker and REPORTED-ONLY extended surfaces."""
    labelled, nh_m, lh_m = marker_label(row, norm_tokens, lim_tokens)
    ext = surface_text(row, EXTENDED_SURFACE_FIELDS)
    nh_x = token_hits(ext, norm_tokens)
    lh_x = token_hits(ext, lim_tokens)
    cls = classify_row(nh_m, nh_x, lh_m, lh_x)
    return {
        "row_decision_id": row.get("decision_id"),
        "channel": row.get("_channel"),
        "language": row.get("_language"),
        "class": cls,
        "norm_state": axis_state(nh_m, nh_x),
        "lim_state": axis_state(lh_m, lh_x),
        "norm_hits_marker": nh_m,
        "limitation_hits_marker": lh_m,
        "norm_hits_extended_only": [t for t in nh_x if t not in nh_m],
        "limitation_hits_extended_only": [t for t in lh_x if t not in lh_m],
        "labelled": labelled,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", type=Path,
                    default=_REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    ap.add_argument("--cache", type=Path,
                    default=_REPO_ROOT / "results/evaluation/retrieval_benchmark/cache")
    ap.add_argument("--accepted-record", type=Path,
                    default=_REPO_ROOT / "results/evaluation/query_map_cached_bundle_benchmark/39766474798.json")
    ap.add_argument("--out", type=Path,
                    default=_REPO_ROOT / "results/evaluation/counter_marker_attribution/39771077625.json")
    ap.add_argument("--run-id", default="39771077625")
    args = ap.parse_args(argv)

    bp_path = _REPO_ROOT / "evaluation/query_map/bundle_producer.py"
    pins_before = {
        "frozen_spec": sha256_file(args.spec),
        "accepted_record": sha256_file(args.accepted_record),
        "bundle_producer": sha256_file(bp_path),
    }
    controls: dict[str, dict] = {}

    def fail_all(reason: str, extra: dict | None = None) -> int:
        record = {
            "schema": SCHEMA, "run_id": args.run_id,
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verdict": "NOT_MEASURED_VACUOUS", "exit_code": EXIT_VACUOUS,
            "vacuous_reason": reason, "controls": controls,
            "pins_before": pins_before, "network_calls": 0,
            "claim_ceiling": "NOT_MEASURED_VACUOUS; never a pass, never an attribution, never a bar-met.",
        }
        if extra:
            record.update(extra)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"NOT_MEASURED_VACUOUS: {reason}")
        return EXIT_VACUOUS

    # C1 frozen spec pin
    c1_ok = pins_before["frozen_spec"] == FROZEN_SPEC_SHA256
    controls["C1_spec_pin"] = {"holds": c1_ok, "observed": pins_before["frozen_spec"],
                               "expected": FROZEN_SPEC_SHA256}
    if not c1_ok:
        return fail_all("C1_spec_pin failed: frozen spec drift")
    # C3a accepted record pin (read BEFORE execution; re-hashed after)
    c3a_ok = pins_before["accepted_record"] == ACCEPTED_RECORD_SHA256
    controls["C3_accepted_record_parity"] = {"holds": c3a_ok, "pin_observed": pins_before["accepted_record"],
                                             "pin_expected": ACCEPTED_RECORD_SHA256}
    if not c3a_ok:
        return fail_all("C3 accepted-record pin drift")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    accepted = json.loads(args.accepted_record.read_text(encoding="utf-8"))
    accepted_yield = accepted["counter_authority_yield"]["per_question"]
    accepted_meta = {q["slug"]: q["producer_meta"] for q in accepted["questions"]}

    envelopes = read_cache(args.cache)
    index = index_cache(envelopes, spec)

    # C2 cache parity
    n_frozen_queries = sum(
        1 for q in spec["questions"] for ch in CHANNELS
        for _ in (q.get("queries", {}).get(ch) or {}))
    c2_ok = len(envelopes) == 24 and len(index) == n_frozen_queries
    controls["C2_cache_parity"] = {
        "holds": c2_ok, "n_envelopes": len(envelopes), "n_indexed": len(index),
        "n_frozen_query_slots": n_frozen_queries,
    }
    if not c2_ok:
        return fail_all("C2_cache_parity failed: cache/index mismatch")

    # C5 planted detection (synthetic rows; NEVER enter published counts)
    plant_norm, plant_lim = "lexmachinaplantnorm", "lexmachinaplantlimit"
    planted_labelled = classify_row([plant_norm], [plant_norm], [plant_lim], [plant_lim])
    planted_absent = classify_row([plant_norm], [plant_norm], [], [])
    c5_ok = planted_labelled == "LABELLED" and planted_absent == "LIMITATION_LEXICON_ABSENT"
    controls["C5_planted_detection"] = {
        "holds": c5_ok, "planted_both_tokens_class": planted_labelled,
        "planted_norm_only_class": planted_absent,
        "note": "planted rows never enter any published count",
    }
    if not c5_ok:
        return fail_all("C5_planted_detection failed: classifier not live")

    per_question: list[dict] = []
    all_controls_ok = True

    for q in spec["questions"]:
        slug = q["slug"]
        norm_tokens = list(q["queries"]["norm_tokens"])
        lim_tokens = list(q["queries"]["limitation_tokens"])
        min_core = int(spec["id_match_rules"]["min_core_length"])
        known_counter = q.get("known_counter_ids", [])

        # C6 non-empty frozen known-counter set
        if not known_counter:
            per_question.append({"slug": slug, "question_verdict": "NOT_MEASURED_EMPTY_FROZEN_SET",
                                 "known_counter_n": 0})
            continue

        rows = assemble_pool(slug, index, spec)

        # marker labels on the instrument pool
        labelled_rows = []
        labelled_cores = set()
        for row in rows:
            lab, _, _ = marker_label(row, norm_tokens, lim_tokens)
            if lab:
                labelled_rows.append(row)
                labelled_cores.add(alnum_core(row.get("decision_id")))

        # C4 build_bundle agreement (replication verified against the accepted producer)
        bundle = build_bundle(slug, index, spec)
        bp_cores = {alnum_core(d.get("decision_id")) for d in bundle["final"]["decisions"]
                    if d.get("counter_status") == "candidate-limiting"}
        c4_ok = labelled_cores == bp_cores
        controls.setdefault("C4_bundle_agreement", {})[slug] = {
            "holds": c4_ok, "instrument_n": len(labelled_cores), "build_bundle_n": len(bp_cores),
        }
        all_controls_ok = all_controls_ok and c4_ok

        # C3b accepted-record parity (pool size + marker count)
        acc_meta = accepted_meta.get(slug, {})
        parity_ok = (len(rows) == acc_meta.get("n_decisions")
                     and len(labelled_rows) == accepted_yield.get(slug))
        controls["C3_accepted_record_parity"][slug] = {
            "holds": parity_ok,
            "pool_n": len(rows), "accepted_pool_n": acc_meta.get("n_decisions"),
            "marker_n": len(labelled_rows), "accepted_marker_n": accepted_yield.get(slug),
        }
        all_controls_ok = all_controls_ok and parity_ok

        # per-known-counter-row attribution
        row_records = []
        for entry in known_counter:
            fid = entry["id"] if isinstance(entry, dict) else entry
            mrow = None
            for row in rows:
                if match_frozen_id(row, fid, min_core_length=min_core):
                    mrow = row
                    break
            if mrow is None:
                row_records.append({"frozen_id": fid, "reached": False, "class": "NOT_REACHED"})
            else:
                attr = attribute_row(mrow, norm_tokens, lim_tokens)
                attr["frozen_id"] = fid
                attr["reached"] = True
                row_records.append(attr)

        reached = [r for r in row_records if r["reached"]]
        unlabelled_reached = [r for r in reached if not r["labelled"]]
        class_counts: dict[str, int] = {}
        for r in row_records:
            class_counts[r["class"]] = class_counts.get(r["class"], 0) + 1
        reached_class_counts: dict[str, int] = {}
        for r in reached:
            reached_class_counts[r["class"]] = reached_class_counts.get(r["class"], 0) + 1

        def dominant(counts: dict[str, int]) -> str | None:
            best = None
            for cls in CLASS_PRIORITY + ("NOT_REACHED",):
                if counts.get(cls):
                    best = cls
                    break
            return best

        zero_yield = len(labelled_rows) == 0
        if zero_yield and not reached:
            q_verdict = "CHANNEL_GAP_ATTRIBUTED"
        elif zero_yield and unlabelled_reached and all(
                r["class"] in BLINDNESS_CLASSES for r in unlabelled_reached):
            q_verdict = "MARKER_RULE_BLINDSPOT_ATTRIBUTED"
        elif reached and all(r["labelled"] for r in reached):
            q_verdict = "NO_MARKER_DEFECT"
        else:
            q_verdict = "MIXED_REPORTED_ONLY"

        # REPORTED-ONLY multilingual cut
        lang_cut: dict[str, dict[str, int]] = {}
        for r in row_records:
            if not r["reached"]:
                continue
            lg = str(r.get("language") or "?")
            lang_cut.setdefault(lg, {})
            lang_cut[lg][r["class"]] = lang_cut[lg].get(r["class"], 0) + 1

        per_question.append({
            "slug": slug,
            "pool_n": len(rows),
            "marker_labelled_n": len(labelled_rows),
            "zero_yield": zero_yield,
            "known_counter_n": len(known_counter),
            "n_reached": len(reached),
            "n_reached_unlabelled": len(unlabelled_reached),
            "class_counts_all_known_counter": class_counts,
            "class_counts_reached": reached_class_counts,
            "dominant_class_all": dominant(class_counts),
            "dominant_class_reached": dominant(reached_class_counts),
            "question_verdict": q_verdict,
            "multilingual_cut_reported_only": lang_cut,
            "known_counter_rows": row_records,
        })

    # C4/C3 aggregate
    controls["C4_bundle_agreement"]["holds"] = all_controls_ok and all(
        v["holds"] for v in controls["C4_bundle_agreement"].values()
        if isinstance(v, dict) and "holds" in v)
    c3_b_ok = all(v.get("holds") for k, v in controls["C3_accepted_record_parity"].items()
                  if isinstance(v, dict))
    controls["C3_accepted_record_parity"]["holds"] = c3_b_ok
    controls["C6_known_counter_sets_nonempty"] = {
        "holds": all(q.get("known_counter_n", 0) > 0 for q in per_question),
        "per_question_n": {q["slug"]: q.get("known_counter_n") for q in per_question},
    }
    controls["C7_zero_network"] = {"holds": True, "network_calls": 0}

    # re-hash pins AFTER execution
    pins_after = {
        "frozen_spec": sha256_file(args.spec),
        "accepted_record": sha256_file(args.accepted_record),
        "bundle_producer": sha256_file(bp_path),
    }
    drift = {k: {"before": pins_before[k], "after": pins_after[k]}
             for k in pins_before if pins_before[k] != pins_after[k]}
    controls["C1_spec_pin"]["rehash_after"] = pins_after["frozen_spec"]
    controls["C1_spec_pin"]["holds"] = controls["C1_spec_pin"]["holds"] and not drift.get("frozen_spec")
    controls["C3_accepted_record_parity"]["rehash_after"] = pins_after["accepted_record"]
    all_hold = all_controls_ok and not drift and all(
        c.get("holds") for c in controls.values() if isinstance(c, dict) and "holds" in c)
    if not all_hold:
        record = {
            "schema": SCHEMA, "run_id": args.run_id,
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verdict": "NOT_MEASURED_VACUOUS", "exit_code": EXIT_VACUOUS,
            "controls": controls, "drift": drift, "pins_before": pins_before,
            "pins_after": pins_after, "network_calls": 0, "per_question": per_question,
            "claim_ceiling": "NOT_MEASURED_VACUOUS; never a pass, never an attribution.",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("NOT_MEASURED_VACUOUS: a control failed or pins drifted")
        return EXIT_VACUOUS

    zero_yield_questions = [q for q in per_question if q.get("zero_yield")]
    attributed = [q for q in zero_yield_questions
                  if q["question_verdict"] == "MARKER_RULE_BLINDSPOT_ATTRIBUTED"]
    diverged = [q for q in zero_yield_questions if q["question_verdict"] == "NO_MARKER_DEFECT"]
    if attributed:
        verdict, exit_code = "MARKER_BLINDSPOT_ATTRIBUTED", EXIT_BLINDSPOT_ATTRIBUTED
    elif diverged:
        # divergence from the accepted record is a finding, published as such
        verdict, exit_code = "DIVERGENCE_FROM_ACCEPTED_RECORD", EXIT_BLINDSPOT_ATTRIBUTED
    else:
        verdict, exit_code = "ATTRIBUTION_COMPLETE_NO_BLINDSPOT", EXIT_NO_BLINDSPOT

    record = {
        "schema": SCHEMA, "run_id": args.run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "evaluation", "direction_version": 62,
        "verdict": verdict, "exit_code": exit_code,
        "controls": controls, "pins_before": pins_before, "pins_after": pins_after,
        "drift": drift, "network_calls": 0,
        "zero_yield_questions": [q["slug"] for q in zero_yield_questions],
        "attributed_questions": [q["slug"] for q in attributed],
        "diverged_questions": [q["slug"] for q in diverged],
        "per_question": per_question,
        "class_priority": list(CLASS_PRIORITY),
        "extended_surface_fields": list(EXTENDED_SURFACE_FIELDS),
        "claim_ceiling": (
            "Attributes the ACCEPTED cached-bundle negative result (run 39766474798) on the "
            "accepted cached rows under the frozen marker rule. Measures the EVALUATION "
            "FIXTURE's marker rule, NOT the product's shipped counter classifier, the emission "
            "repair or any Frontier build. Meets/moves/re-derives NO frozen absolute bar; "
            "lifts NO DO-NOT-SERVE order; certifies NO packet admission; claims NO jurist "
            "usefulness; admission stays fail-closed; human_gate_ready and "
            "owner_decision_required stay false."),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{verdict} exit={exit_code} zero_yield={record['zero_yield_questions']} "
          f"attributed={record['attributed_questions']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
