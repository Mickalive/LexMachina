"""CROSS-CHECK table vs Core Evaluation's published re-score (if any).

If Core Evaluation has published a re-score of the rebuilt packet
(content_sha256 2942c3c2...), place its reported numbers beside this team's
recomputation for every quantity; any divergence is the headline finding.
If it has not published by hard stop, record Evaluation's numbers as ABSENT
(never invented, never blocking) and publish this team's recomputation alone.
Product's in-packet claimed numbers (packet.json counter_anchor /
geometry_scoring) are recorded as a SECONDARY reference clearly labelled as
product-claimed, not Evaluation-published.

SCHEMA MAPPING (repair FIX-2 of audit CYCLE_39053132092): Evaluation's
adjudication record (schema lex-evaluation-rebuilt-packet-adjudication/1,
run 39049030442) is consumed through the EXPLICIT dotted-path mapping below.
The former generic first-key resolver (_dig) is retained ONLY as a
non-authoritative fallback for records that do not follow that schema (e.g.
synthetic fixtures); every row records which mapping produced it, so a
mis-resolution can never be silently authoritative again. Evaluation
publishes no mega-cluster quantity: that row is recorded as
absent-not-divergent, never as a divergence.
"""
from __future__ import annotations

import json
from pathlib import Path

from .paths import TEAM_ROOT

# Locations where a Core Evaluation re-score of the rebuilt packet might land.
EVAL_RESCORE_CANDIDATES = (
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/rebuilt_packet_rescore"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/bar_gates"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/label_lineage_gate/adjudications"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/rebuild_preflight"),
)

# This team's vendored read-only copy of the lane's published record (see
# vendored_cross_check_input/PROVENANCE.json). Consulted by discovery so the
# cross-check is reproducible offline; an explicit --evaluation-rescore path
# always takes precedence.
VENDORED_EVAL_RECORD = TEAM_ROOT / "vendored_cross_check_input" / "39049030442_adjudication.json"

# Authoritative mapping: quantity -> dotted paths into Evaluation's
# adjudication record, tried in order. Path names are exact; nothing is
# fuzzy. (audit FIX-2: three_numbers_required_together.*
# and instrument_1_label_gate_population_pinned.geometry_per_bundle_criterion_counts.*)
EVAL_ADJUDICATION_MAPPING = {
    "label.n_scored_on_issued_population": (
        "instrument_2_label_lineage_gate_population_free.n_scored",
        "per_anchor_counter_reading.total.emitted",
    ),
    "label.n_supported_among_issued": (
        "instrument_2_label_lineage_gate_population_free.n_supported",
    ),
    "label.support_rate_among_issued": (
        "three_numbers_required_together.support_rate_among_issued_labels_frozen_rubric",
    ),
    "label.n_abstained": (
        "three_numbers_required_together.abstention_count",
    ),
    "label.yield_over_classifier_population": (
        "three_numbers_required_together.yield_on_packet_row_population",
    ),
}
# Evaluation publishes no mega-cluster quantity (0 occurrences of
# "mega"/"largest_cluster" in run 39049030442); the row is absent-not-divergent.

# Evidence of the search performed for a published Evaluation re-score,
# re-verified at the FINAL resume of this run before promotion (audit FIX-1
# + FIX-4). The earlier ABSENT claim (recorded verbatim below) was falsified
# by this re-sweep: the lane's record was published 2026-10-17T17:05:31Z,
# BEFORE this team's measurement commit (17:14:39Z) and final resume
# (17:39:45Z); the producer's sweep had simply not been re-run at the final
# resume (its own detected_at_run stayed 39048947212).
EVAL_RESCORE_SEARCH_BASIS = {
    "reverified_at_final_resume": True,
    "final_resume_run_id": 39053132092,
    "final_resume_repair_round": 1,
    "rerun_timestamp_utc": "2026-10-17T18:22:00Z",
    "rerun_timestamp_note": "UTC time the final-resume re-sweep was executed (process record; freeze ordering is proven separately by git commit times, never by hand-written timestamps)",
    "git_refs_swept": (
        "all origin/cycle/core/evaluation/* (including origin/cycle/core/evaluation/39052366154/team "
        "@ 27a1d309), origin/lab/evaluation, origin/main — re-swept at the final resume"
    ),
    "found_at_rerun": {
        "lane": "core_evaluation",
        "run_id": 39049030442,
        "record": "results/evaluation/rebuilt_packet_adjudication_39049030442/39049030442_adjudication.json",
        "git_ref": "origin/cycle/core/evaluation/39052366154/team",
        "commit": "27a1d309ea6c76a05d0849351f1067a92c0e030d",
        "commit_time_utc": "2026-10-17T17:05:31Z",
        "packet_json_raw_sha256": "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170",
        "vendored_packet_rehashed_identical": True,
        "published_before": {
            "producer_measurement_commit_utc": "2026-10-17T17:14:39Z",
            "producer_final_resume_utc": "2026-10-17T17:39:45Z",
        },
    },
    "prior_absent_claim": {
        "status": "FALSIFIED at the final-resume re-sweep and deleted from every claim-bearing artifact (audit FIX-1)",
        "cause": (
            "the evaluation-lane sweep was never re-run at the final resume "
            "(detected_at_run 39048947212); the lane's same-bytes adjudication "
            "was published 2026-10-17T17:05:31Z, before the producer's "
            "measurement commit (17:14:39Z)"
        ),
        "disclosed_in": "audit CYCLE_39053132092 required_fix FIX-1",
    },
    "process_rule": (
        "Any absence or 'verified across every ref' claim must be re-verified at the "
        "FINAL resume/attempt of a run before promotion. A future produced-work cycle "
        "shipping a stale absence claim of this same class gates BLOCKED under the "
        "recurring-repair rule, not a further REVISE (audit FIX-4)."
    ),
}


class CrossCheckError(RuntimeError):
    """Re-score identity/schema error: environment error, never a product verdict."""


def _load_rescore(explicit_paths) -> dict | None:
    """Use an explicitly supplied Evaluation re-score if the lane published one."""
    for raw in explicit_paths or ():
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"evaluation re-score not found: {p}")
        return {"path": str(p), "record": json.loads(p.read_text(encoding="utf-8")), "source": "explicit_path"}
    return None


def _dig(record, *names):
    """First present key among ``names`` in a nested mapping (no invention).

    NON-AUTHORITATIVE FALLBACK ONLY (retained for records that do not follow
    the adjudication schema, e.g. synthetic test fixtures). Never used for a
    quantity the explicit mapping in EVAL_ADJUDICATION_MAPPING resolves.
    """
    if not isinstance(record, dict):
        return None
    if "bars" in record and isinstance(record["bars"], dict):
        for name in names:
            for bar in record["bars"].values():
                if isinstance(bar, dict) and name in bar:
                    return bar[name]
    for name in names:
        if name in record:
            return record[name]
    for value in record.values():
        if isinstance(value, dict):
            hit = _dig(value, *names)
            if hit is not None:
                return hit
    return None


def _explicit(record, *paths):
    """First present DOTTED path among ``paths`` in the adjudication record."""
    for path in paths:
        node = record
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                node = None
                break
            node = node[part]
        if node is not None:
            return node
    return None


def _resolve(record, quantity, fallback_names=()):
    """Resolve one quantity: explicit schema first, _dig fallback second.

    Returns (value, mapping) where mapping is "explicit_schema",
    "fallback_dig_non_authoritative" or "explicit_schema_miss" (explicit paths
    were defined for this quantity but the record does not carry them and no
    fallback key exists); value is None when nothing is found.
    """
    paths = EVAL_ADJUDICATION_MAPPING.get(quantity)
    if paths:
        hit = _explicit(record, *paths)
        if hit is not None:
            return hit, "explicit_schema"
    hit = _dig(record, *fallback_names) if fallback_names else None
    if hit is not None:
        return hit, "fallback_dig_non_authoritative"
    if paths:
        return None, "explicit_schema_miss"
    return None, "fallback_dig_non_authoritative"


def _geometry_count(record, qid):
    """Geometry per-bundle criterion count from the adjudication record.

    Explicit path (authoritative): instrument_1_label_gate_population_pinned
    .geometry_per_bundle_criterion_counts[qid]. Fallback (non-authoritative):
    _dig for n_pass_<qid> / <qid> keys, for non-adjudication records only.
    """
    counts = (record or {}).get("instrument_1_label_gate_population_pinned", {}).get(
        "geometry_per_bundle_criterion_counts", {})
    if qid in counts:
        return counts[qid], "explicit_schema"
    hit = _dig(record, f"n_pass_{qid}", qid) if record else None
    return hit, "fallback_dig_non_authoritative"


def _check_identity(record: dict, packet_content_sha256: str) -> None:
    """A re-score is consumed only against the bytes it actually names.

    If the record declares the packet it scored, that declaration must match
    this team's measured packet; mismatched bytes are an environment error,
    never a silent cross-check of a different packet.
    """
    declared = (record.get("packet_provenance") or {}).get("packet_json_raw_sha256")
    if declared and declared != packet_content_sha256:
        raise CrossCheckError(
            f"evaluation re-score names packet {declared}, this team measured "
            f"{packet_content_sha256}; refusing to cross-check different bytes"
        )


def _find_evaluation_rescore(packet_content_sha256: str) -> dict | None:
    """Best-effort discovery of an Evaluation re-score naming this packet.

    Returns None when nothing is published: the charter requires recording
    absence rather than inventing numbers or blocking.
    """
    needles = ("39027045675", "rebuilt-39027045675", packet_content_sha256[:16])
    for root in EVAL_RESCORE_CANDIDATES:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.json")):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(n in text for n in needles) and "rescore" in (p.name + text[:2000]).lower():
                try:
                    return {"path": str(p), "record": json.loads(text)}
                except json.JSONDecodeError:
                    return {"path": str(p), "record": None, "parse_error": True}
    # The lane's published record, vendored byte-identically inside this
    # team's namespace (provenance: vendored_cross_check_input/PROVENANCE.json).
    # Identity of the bytes it names is enforced by _check_identity in build().
    if VENDORED_EVAL_RECORD.is_file():
        record = json.loads(VENDORED_EVAL_RECORD.read_text(encoding="utf-8"))
        return {"path": str(VENDORED_EVAL_RECORD), "record": record,
                "source": "vendored_cross_check_input"}
    return None


def product_claimed_numbers(packet_json: Path) -> dict:
    """Product's OWN in-packet claimed numbers (secondary reference only)."""
    packet = json.loads(Path(packet_json).read_text(encoding="utf-8"))
    out = {"per_bundle": {}}
    for q in packet.get("questions") or []:
        qid = q.get("qid")
        ca = q.get("counter_anchor") or {}
        gs = q.get("geometry_scoring") or {}
        mega = q.get("mega_cluster_disclosure") or {}
        out["per_bundle"][qid] = {
            "product_claimed_counter_anchor": ca,
            "product_claimed_geometry_n_pass": gs.get("n_pass"),
            "product_claimed_geometry_overall": gs.get("overall"),
            "product_claimed_mega_cluster_fired_on_rebuilt": (mega.get("rebuilt_packet") or {}).get("fired"),
        }
    admission = packet.get("packet_admission") or {}
    out["product_claimed_packet_admission"] = {
        "packet_admitted": admission.get("packet_admitted"),
        "blocking_reason": admission.get("blocking_reason"),
        "bars": admission.get("bars"),
    }
    out["label"] = "product-claimed in-packet numbers, NOT Core Evaluation's independent re-score"
    return out


def _evaluation_instrument_verdicts(record: dict, team_half_a: dict, team_half_b: dict) -> dict:
    """Evaluation's instrument verdicts beside this team's, same explicit mapping."""
    if not record:
        return {"status": "CORE_EVALUATION_RESCORE_ABSENT"}
    i1 = record.get("instrument_1_label_gate_population_pinned") or {}
    i2 = record.get("instrument_2_label_lineage_gate_population_free") or {}
    team_label_gate = team_half_a.get("accepted_label_gate_as_written") or {}
    team_lineage = team_half_a.get("accepted_label_lineage_gate_as_written") or {}
    team_geo = {
        "absolute_status": team_half_b.get("absolute_status"),
        "regression_verdict": (team_half_b.get("regression") or {}).get("regression_verdict"),
        "n_bundles_pass_all_11": team_half_b.get("n_bundles_pass_all_11"),
    }
    pairs = (
        ("label_absolute_status", i1.get("label_absolute_status"), team_label_gate.get("absolute_status")),
        ("label_regression_verdict_population_pinned", i1.get("label_regression_verdict"),
         team_label_gate.get("regression_verdict")),
        ("label_lineage_regression_verdict_population_free", i2.get("regression_verdict"),
         team_lineage.get("regression_verdict")),
        ("geometry_absolute_status", i1.get("geometry_absolute_status"), team_geo["absolute_status"]),
        ("geometry_regression_verdict", i1.get("geometry_regression_verdict"), team_geo["regression_verdict"]),
        ("n_bundles_pass_all_11", i1.get("n_bundles_pass_all_11"), team_geo["n_bundles_pass_all_11"]),
    )
    rows = [
        {
            "quantity": f"instrument.{name}",
            "this_team_recomputed": mine,
            "core_evaluation_published": theirs,
            "divergence": None if theirs is None else (theirs != mine),
        }
        for name, theirs, mine in pairs
    ]
    return {
        "status": "CORE_EVALUATION_RESCORE_PRESENT",
        "mapping": "explicit_schema",
        "note": "Evaluation's accepted-instrument verdicts beside this team's recomputation of the same verdicts; NOT_APPLICABLE from any regression instrument is not a pass.",
        "rows": rows,
    }


def build(team_half_a: dict, team_half_b: dict, packet_json: Path,
          packet_content_sha256: str = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170",
          evaluation_rescore_paths=None) -> dict:
    evaluation = _load_rescore(evaluation_rescore_paths) or _find_evaluation_rescore(packet_content_sha256)
    record = (evaluation or {}).get("record") or {}
    if record:
        _check_identity(record, packet_content_sha256)
    rows = []
    # Label quantities
    pooled = team_half_a["pooled"]
    label_quantities = [
        ("label.n_scored_on_issued_population", pooled["n_issued"], ("n_scored", "scored_counter_rows")),
        ("label.n_supported_among_issued", pooled["n_supported"], ("n_supported",)),
        ("label.support_rate_among_issued", pooled["support_rate_among_issued"], ("support_rate",)),
        ("label.n_abstained", pooled["n_abstained"], ("n_abstained",)),
        ("label.yield_over_classifier_population", pooled["yield_over_classifier_population"],
         ("yield", "yield_over_classifier_population")),
    ]
    for quantity, mine, fallback_names in label_quantities:
        theirs, mapping = _resolve(record, quantity, fallback_names) if record else (None, "explicit_schema")
        rows.append({
            "quantity": quantity,
            "this_team_recomputed": mine,
            "core_evaluation_published": theirs,
            "divergence": None if theirs is None else (theirs != mine),
            "mapping": mapping,
        })
    for qid, n_pass in sorted(team_half_b["criterion_counts"].items()):
        theirs, mapping = _geometry_count(record, qid)
        rows.append({
            "quantity": f"geometry.{qid}.n_pass_of_11",
            "this_team_recomputed": n_pass,
            "core_evaluation_published": theirs if isinstance(theirs, int) else None,
            "divergence": None if not isinstance(theirs, int) else (theirs != n_pass),
            "mapping": mapping,
        })
    mega_mine = team_half_b.get("mega_cluster_fires_on_any_rebuilt_bundle")
    # Evaluation publishes no mega-cluster quantity: absent, NOT divergent.
    mega_theirs, mega_mapping = (
        _resolve(record, "geometry.mega_cluster_disclosure_fires_on_any_rebuilt_bundle",
                 ("mega_cluster_fires", "mega_cluster_disclosure_fires"))
        if record else (None, "explicit_schema")
    )
    rows.append({
        "quantity": "geometry.mega_cluster_disclosure_fires_on_any_rebuilt_bundle",
        "this_team_recomputed": mega_mine,
        "core_evaluation_published": mega_theirs,
        "divergence": None if mega_theirs is None else (mega_theirs != mega_mine),
        "mapping": mega_mapping,
        "absent_not_divergent": mega_theirs is None,
        "note": ("Evaluation publishes no mega-cluster quantity in its adjudication record; "
                 "recorded as absent, never as a divergence") if mega_theirs is None else None,
    })
    if evaluation is None:
        status = "CORE_EVALUATION_RESCORE_ABSENT"
        headline = (
            "Core Evaluation's re-score of the rebuilt packet had not published at "
            "this team's hard stop; this team's recomputation is published alone and "
            "Evaluation's numbers are recorded as ABSENT (never invented, never blocking)."
        )
    else:
        status = "CORE_EVALUATION_RESCORE_PRESENT"
        divergences = [r["quantity"] for r in rows if r["divergence"]]
        headline = (
            f"Divergence on: {', '.join(divergences)}" if divergences
            else "No divergence detected between this team's recomputation and Evaluation's published numbers."
        )
    return {
        "status": status,
        "packet_content_sha256": packet_content_sha256,
        "core_evaluation_record_path": None if not evaluation else evaluation.get("path"),
        "core_evaluation_record_source": None if not evaluation else evaluation.get("source", "discovery"),
        "cross_check_rows": rows,
        "headline_finding": headline,
        "evaluation_search_basis": EVAL_RESCORE_SEARCH_BASIS,
        "evaluation_instrument_verdicts": _evaluation_instrument_verdicts(record, team_half_a, team_half_b),
        "threshold_re_derived": False,
        "product_claimed_secondary_reference": product_claimed_numbers(packet_json),
    }
