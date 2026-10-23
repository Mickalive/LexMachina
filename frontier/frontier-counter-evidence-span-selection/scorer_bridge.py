"""Bridge to the ACCEPTED frozen scorer and product intake seams.

This module does not re-implement or re-derive the scorer.  It loads, by file
path from the accepted product mount:

  * ``product/query/counter_emission_repair.py`` (Outcome A intake seam), and
  * ``product/query/counter_anchor.py`` (Outcome A label seam),

runs them as written (repair -> span selection -> anchor classifier), and
records the frozen evidence gate's own decisions.  The frozen
``RULES_LABEL.json`` is re-hashed before use and never edited.

The bridge is deliberately dependency-free at import time: the product
``product.query`` package imports numpy, so the two modules are loaded as a
synthetic package exactly as the accepted evaluation benchmark does.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

# Import the local selector without requiring a package install.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import span_select  # noqa: E402

SCORED_STATUSES = span_select.SCORED_STATUSES
REPAIR_ID = span_select.REPAIR_ID

#: Language-specific frozen-pattern-matching inversion prefixes for the
#: inverted-evidence control.  Each matches a frozen regex in RULES_LABEL.json.
INVERSION_PREFIX = {
    "de": "Das Urteil der Vorinstanz wird bestatigt. ",
    "fr": "La Cour a rejete le recours. Le jugement de la premiere instance est confirme. ",
    "it": "Il ricorso e stato respinto e la sentenza e stata confermata. ",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(obj: Any) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_product_modules(mount: Path) -> dict[str, Any]:
    """Load counter_anchor + counter_emission_repair by file path.

    A synthetic package is seeded because ``counter_emission_repair`` imports
    ``.counter_anchor`` relatively and the real ``product.query.__init__``
    imports numpy (not installed in this lane).
    """
    query_root = Path(mount) / "product" / "query"
    package_name = "_lex_product_query_span_selection"
    pkg = type(sys)(package_name)
    pkg.__path__ = [str(query_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = pkg

    modules: dict[str, Any] = {}
    for name in ("counter_anchor", "counter_emission_repair"):
        fullname = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(fullname, query_root / f"{name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load product module {name}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        modules[name] = mod
    return modules


def load_classifier(mount: Path) -> tuple[Any, Any]:
    """Return ``(decide_label, load_rules)`` from the accepted vendored package."""
    vendored_root = Path(mount) / "product" / "vendored" / "frontier_counter_anchor_classifier"
    if str(vendored_root) not in sys.path:
        sys.path.insert(0, str(vendored_root))
    from frontier_counter_anchor_classifier.counter_anchor_classifier import (  # noqa: E402
        decide_label,
    )
    from frontier_counter_anchor_classifier.vendored.rules import load_rules  # noqa: E402

    return decide_label, load_rules


def load_rules_verified(mount: Path, expected_sha256: str) -> Any:
    _decide, load_rules = load_classifier(mount)
    rules_path = Path(mount) / "product" / "frozen" / "RULES_LABEL.json"
    rules = load_rules(str(rules_path))
    if rules.sha256 != expected_sha256:
        raise ValueError(
            f"frozen RULES_LABEL.json sha256 {rules.sha256} != protocol {expected_sha256}"
        )
    return rules


def load_bundle(packet_dir: Path, qid: str) -> dict[str, Any]:
    path = Path(packet_dir) / "questions" / f"{qid}.bundle.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing bundle for {qid}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Hash verification
# ---------------------------------------------------------------------------
def verify_input_hashes(protocol: dict[str, Any], mount: Path) -> dict[str, Any]:
    """Re-hash every frozen input named by the protocol.  Fail-closed."""
    mount = Path(mount)
    inputs = protocol["inputs"]
    observed: dict[str, str | None] = {}
    mismatches: list[str] = []

    def check(label: str, path: Path, expected: str) -> None:
        actual = sha256_file(path) if path.is_file() else None
        observed[label] = actual
        if actual != expected:
            mismatches.append(f"{label}: {actual} != {expected}")

    for packet_key in ("packet_of_record", "served_packet_secondary"):
        packet = inputs[packet_key]
        prefix = Path(packet["path_prefix"])
        check(f"{packet_key}.manifest.json", prefix / "manifest.json", packet["manifest_sha256"])
        check(f"{packet_key}.packet.json", prefix / "packet.json", packet["packet_sha256"])
        for qid, meta in (packet.get("bundles") or {}).items():
            check(
                f"{packet_key}.questions/{qid}.bundle.json",
                prefix / "questions" / f"{qid}.bundle.json",
                meta["sha256"],
            )

    rules_meta = inputs["frozen_rules"]
    check("frozen_rules.RULES_LABEL.json", Path(rules_meta["path"]), rules_meta["sha256"])

    scorer = inputs["frozen_scorer"]
    vendored_root = mount / "product" / "vendored" / "frontier_counter_anchor_classifier"
    for relpath, expected in (scorer.get("classifier_files_sha256") or {}).items():
        check(f"classifier.{relpath}", vendored_root / relpath, expected)

    # The emission repair seam carries its own provenance manifest.
    emission_root = mount / "product" / "vendored" / "frontier_counter_label_emission"
    prov_path = emission_root / "PROVENANCE.json"
    emission_provenance: dict[str, Any] = {}
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        emission_provenance = {
            "path": str(prov_path),
            "sha256": sha256_file(prov_path),
            "component": prov.get("component"),
            "accepted": prov.get("accepted"),
        }
        for relpath, meta in (prov.get("vendored_files") or {}).items():
            check(f"emission.{relpath}", emission_root / relpath, meta["sha256"])

    import subprocess

    mount_head = None
    try:
        out = subprocess.run(
            ["git", "-C", str(mount), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=20,
        )
        mount_head = out.stdout.strip() or None
    except Exception:
        mount_head = None

    return {
        "ok": not mismatches,
        "n_checked": len(observed),
        "mismatches": mismatches,
        "observed": observed,
        "mount_head": mount_head,
        "mount_head_expected": scorer.get("product_mount_head"),
        "mount_head_matches": mount_head == scorer.get("product_mount_head"),
        "emission_provenance": emission_provenance,
        "frozen_rules_sha256": observed.get("frozen_rules.RULES_LABEL.json"),
    }


# ---------------------------------------------------------------------------
# Baseline / candidate
# ---------------------------------------------------------------------------
def promoted_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        d for d in (bundle.get("decisions") or [])
        if str(d.get("counter_proposal_source") or "") == REPAIR_ID
        and str(d.get("counter_status") or "") in SCORED_STATUSES
    ]
    return sorted(rows, key=lambda d: (str(d.get("decision_id") or ""), int(d.get("rank") or 0)))


def summary_from_bundle(
    final_bundle: dict[str, Any],
    qid: str,
    *,
    repaired_bundle: dict[str, Any] | None = None,
    span_decisions: Sequence[span_select.SpanDecision] | None = None,
) -> dict[str, Any]:
    prov = ((final_bundle.get("provenance") or {}).get("counter_anchor") or {})
    repair_prov = ((repaired_bundle or {}).get("provenance") or {}).get(
        "counter_label_emission_repair"
    ) or {}
    return {
        "qid": qid,
        "anchor_profile": prov.get("anchor_profile"),
        "anchor_profile_source": prov.get("anchor_profile_source"),
        "n_total_rows": len(final_bundle.get("decisions") or []),
        "n_promoted": int(repair_prov.get("n_promoted") or 0),
        "n_scored": int(prov.get("n_scored") or 0),
        "n_abstained": int(prov.get("n_abstained") or 0),
        "n_emitted": int(prov.get("n_emitted") or 0),
        "support_rate_among_emitted": float(prov.get("support_rate_among_emitted") or 0.0),
        "yield": float(prov.get("yield") or 0.0),
        "abstention_reasons": dict(prov.get("abstention_reasons") or {}),
        "emitted_ids": list(prov.get("emitted_ids") or []),
        "abstained_ids": list(prov.get("abstained_ids") or []),
        "frozen_rules_sha256": prov.get("frozen_rules_sha256"),
        "n_evidenced_by_selector": (
            sum(1 for d in (span_decisions or []) if d.evidenced)
            if span_decisions is not None else None
        ),
        "selector_abstention_reasons": (
            span_select.count_reasons(span_decisions)
            if span_decisions is not None else None
        ),
    }


def run_baseline(bundle: dict[str, Any], qid: str, modules: dict[str, Any]) -> dict[str, Any]:
    """Repair -> frozen classifier, exactly the accepted offline path."""
    repaired = modules["counter_emission_repair"].apply_counter_emission_repair(
        copy.deepcopy(bundle)
    )
    final = modules["counter_anchor"].apply_anchor_labels(repaired, qid=qid)
    return {
        "repaired_bundle": repaired,
        "final_bundle": final,
        "summary": summary_from_bundle(final, qid, repaired_bundle=repaired),
        "promoted_rows": promoted_rows(repaired),
    }


def run_candidate(
    bundle: dict[str, Any],
    qid: str,
    modules: dict[str, Any],
    rules: Any,
    profile: dict[str, Any],
    *,
    min_chars: int,
    max_chars: int,
    max_units: int,
) -> dict[str, Any]:
    """Repair -> span selection -> frozen classifier."""
    repaired = modules["counter_emission_repair"].apply_counter_emission_repair(
        copy.deepcopy(bundle)
    )
    selected, decisions = span_select.apply_span_selection(
        repaired,
        rules,
        profile,
        qid=qid,
        min_chars=min_chars,
        max_chars=max_chars,
        max_units=max_units,
    )
    final = modules["counter_anchor"].apply_anchor_labels(selected, qid=qid)
    return {
        "repaired_bundle": repaired,
        "selected_bundle": selected,
        "final_bundle": final,
        "span_decisions": decisions,
        "summary": summary_from_bundle(
            final, qid, repaired_bundle=repaired, span_decisions=decisions
        ),
        "promoted_rows": promoted_rows(repaired),
    }


def row_details(
    final_bundle: dict[str, Any],
    decisions: Sequence[span_select.SpanDecision],
) -> list[dict[str, Any]]:
    by_id = {d.decision_id: d for d in decisions}
    out: list[dict[str, Any]] = []
    for d in final_bundle.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        sd = by_id.get(did)
        if sd is None:
            continue
        quote = sd.quote if sd.evidenced else ""
        out.append({
            "decision_id": did,
            "rank": d.get("rank"),
            "language": d.get("language"),
            "legal_area": d.get("legal_area"),
            "proposed_status": d.get("counter_status"),
            "span": sd.to_dict(),
            "quote_verbatim_in_full_text": (
                span_select.verify_span(
                    str(d.get("full_text") or ""), quote, sd.char_start, sd.char_end
                ) if sd.evidenced else False
            ),
            "counter_evidence_equals_quote": str(d.get("counter_evidence") or "") == quote,
            "counter_evidence_verified": d.get("counter_evidence_verified"),
            "counter_status_after": d.get("counter_status"),
            "counter_anchor_label": d.get("counter_anchor_label"),
            "counter_reason_code": d.get("counter_reason_code"),
            "counter_uncertainty": d.get("counter_uncertainty"),
            "full_text_len": len(str(d.get("full_text") or "")),
        })
    return out


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
def mutate_quote(quote: str) -> str:
    """Deterministically change one alphabetic character of ``quote``."""
    for i, ch in enumerate(quote):
        if ch.isalpha():
            repl = "q" if ch.lower() != "q" else "z"
            return quote[:i] + repl + quote[i + 1 :]
    return quote + "q"


def find_non_occurring_donor_quote(
    target_row: dict[str, Any],
    target_qid: str,
    donor_bundles: dict[str, dict[str, Any]],
    *,
    max_rows_per_bundle: int = 25,
    quote_chars: int = 400,
) -> dict[str, Any]:
    """Find a deterministic cross-bundle quote absent from the target full_text.

    Donors are visited by sorted qid (excluding the target), then by ascending
    rank / decision_id.  The first 400-char window that does not occur in the
    target's full_text is returned.  If none exists (pathological), a fixed
    synthetic fallback is returned and the record says so.
    """
    target_text = str(target_row.get("full_text") or "")
    for donor_qid in sorted(donor_bundles):
        if donor_qid == target_qid:
            continue
        rows = sorted(
            donor_bundles[donor_qid].get("decisions") or [],
            key=lambda d: (int(d.get("rank") or 0), str(d.get("decision_id") or "")),
        )
        for donor_row in rows[:max_rows_per_bundle]:
            text = str(donor_row.get("full_text") or "")
            if len(text) < quote_chars:
                continue
            quote = text[:quote_chars].strip()
            if len(quote) < 40:
                continue
            if quote in target_text:
                continue
            return {
                "quote": quote,
                "donor_qid": donor_qid,
                "donor_decision_id": donor_row.get("decision_id"),
                "source": "cross_bundle_full_text",
            }
    return {
        "quote": "This passage is intentionally unrelated to the target question and carries no relevant anchor.",
        "donor_qid": None,
        "donor_decision_id": None,
        "source": "synthetic_fallback",
    }


def run_replacement_control(
    selected_bundle: dict[str, Any],
    replacements: dict[str, str],
    qid: str,
    modules: dict[str, Any],
) -> dict[str, Any]:
    """Replace evidence on named rows, then run the SAME frozen classifier."""
    control = copy.deepcopy(selected_bundle)
    applied: list[str] = []
    for d in control.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        if did in replacements:
            d["counter_evidence"] = replacements[did]
            d["counter_evidence_verified"] = False
            applied.append(did)
    final = modules["counter_anchor"].apply_anchor_labels(control, qid=qid)
    prov = ((final.get("provenance") or {}).get("counter_anchor") or {})
    rows = []
    for d in final.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        if did in replacements:
            rows.append({
                "decision_id": did,
                "counter_status_after": d.get("counter_status"),
                "counter_anchor_label": d.get("counter_anchor_label"),
                "counter_reason_code": d.get("counter_reason_code"),
            })
    return {
        "qid": qid,
        "n_replaced": len(applied),
        "n_scored": int(prov.get("n_scored") or 0),
        "n_emitted": int(prov.get("n_emitted") or 0),
        "n_abstained": int(prov.get("n_abstained") or 0),
        "abstention_reasons": dict(prov.get("abstention_reasons") or {}),
        "emitted_ids": list(prov.get("emitted_ids") or []),
        "control_rows": rows,
    }


def run_swapped_control(
    selected_bundle: dict[str, Any],
    qid: str,
    emitted_ids: Sequence[str],
    donor_quotes: dict[str, str],
    modules: dict[str, Any],
) -> dict[str, Any]:
    replacements = {did: donor_quotes[did] for did in emitted_ids if did in donor_quotes}
    return run_replacement_control(selected_bundle, replacements, qid, modules)


def run_inverted_control(
    selected_bundle: dict[str, Any],
    qid: str,
    emitted_ids: Sequence[str],
    modules: dict[str, Any],
) -> dict[str, Any]:
    by_id = {str(d.get("decision_id") or ""): d for d in selected_bundle.get("decisions") or []}
    replacements: dict[str, str] = {}
    for did in emitted_ids:
        row = by_id.get(did)
        if row is None:
            continue
        lang = str(row.get("language") or "de").lower()
        prefix = INVERSION_PREFIX.get(lang, INVERSION_PREFIX["de"])
        replacements[did] = prefix + str(row.get("counter_evidence") or "")
    return run_replacement_control(selected_bundle, replacements, qid, modules)


def score_injection_rows(rules: Any, decide_label: Any) -> dict[str, Any]:
    """Score the frozen non-vacuity injection rows with the same classifier."""
    rows = list((rules.non_vacuity or {}).get("injection_rows") or [])
    results = []
    for row in rows:
        profile_key = str(row.get("anchor_profile") or "")
        profile = rules.anchor_profile(profile_key) if profile_key in rules.anchors else {}
        dec = decide_label(row, rules, profile)
        expected_reason = str(row.get("expected_reason_code") or "")
        expected_class = str(row.get("expected_class") or "")
        results.append({
            "decision_id": row.get("decision_id"),
            "anchor_profile": profile_key,
            "expected_class": expected_class,
            "expected_reason_code": expected_reason,
            "actual_label": dec.label,
            "actual_reason_code": dec.reason_code,
            "pass": dec.reason_code == expected_reason,
        })
    classes = sorted({r["expected_class"] for r in results})
    defect_classes = [c for c in classes if c != "SUPPORTED"]
    return {
        "n_rows": len(results),
        "results": results,
        "classes_exercised": classes,
        "n_defect_classes_exercised": len(defect_classes),
        "min_criteria_flagged": int((rules.non_vacuity or {}).get("min_criteria_flagged") or 2),
        "all_match_expected": all(r["pass"] for r in results),
        "pass": (
            bool(results)
            and all(r["pass"] for r in results)
            and len(defect_classes) >= int((rules.non_vacuity or {}).get("min_criteria_flagged") or 2)
        ),
        "injection_rows_sha256": canonical_sha256(rows),
    }


def _seeded_row(*, decision_id: str, full_text: str) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "court": "seeded-control",
        "language": "de",
        "rank": 10000,
        "score": 0.0,
        "title": "",
        "regeste": "",
        "legal_area": "",
        "full_text": full_text,
        "full_text_status": "fetched",
        "counter_status": "candidate-limiting",
        "counter_evidence": "",
        "counter_evidence_verified": False,
        "counter_uncertainty": 0.5,
    }


def run_seeded_controls(
    rules: Any,
    modules: dict[str, Any],
    *,
    min_chars: int,
    max_chars: int,
    max_units: int,
) -> dict[str, Any]:
    """Positive/negative seeded controls for the combined selector+classifier."""
    profile_key = "de-kapitalverletzung"
    profile = rules.anchor_profile(profile_key)

    positive_text = (
        "Die Sorgepflicht des Arbeitgebers ist begrenzt; eine Kapitalverletzung "
        "kann nur bei einem aktiven Eingriff angenommen werden."
    )
    negative_text = (
        "Die THEMA ist zu pruefen; eine THEMA kann bei einem THEMA angenommen werden."
    )

    results: dict[str, Any] = {}
    for label, text in (("positive", positive_text), ("negative", negative_text)):
        row = _seeded_row(decision_id=f"SEEDED_{label.upper()}_DE", full_text=text)
        dec = span_select.select_span(
            row, rules, profile,
            min_chars=min_chars, max_chars=max_chars, max_units=max_units,
        )
        row["counter_evidence"] = dec.quote if dec.evidenced else ""
        bundle = {"query": profile.get("question") or "", "decisions": [row]}
        final = modules["counter_anchor"].apply_anchor_labels(
            bundle, qid=profile_key
        )
        prov = ((final.get("provenance") or {}).get("counter_anchor") or {})
        results[label] = {
            "span_evidenced": dec.evidenced,
            "span_reason_code": dec.reason_code,
            "span_quote": dec.quote,
            "n_scored": int(prov.get("n_scored") or 0),
            "n_emitted": int(prov.get("n_emitted") or 0),
            "n_abstained": int(prov.get("n_abstained") or 0),
            "emitted_ids": list(prov.get("emitted_ids") or []),
            "abstention_reasons": dict(prov.get("abstention_reasons") or {}),
            "pass": (
                int(prov.get("n_emitted") or 0) == (1 if label == "positive" else 0)
            ),
        }
    return results


def cross_decision_verbatim_controls(
    final_bundle: dict[str, Any],
    decisions: Sequence[span_select.SpanDecision],
    donor_bundles: dict[str, dict[str, Any]],
    qid: str,
) -> dict[str, Any]:
    rows_by_id = {str(d.get("decision_id") or ""): d for d in final_bundle.get("decisions") or []}
    records = []
    for dec in decisions:
        if not dec.evidenced:
            continue
        row = rows_by_id.get(dec.decision_id) or {}
        text = str(row.get("full_text") or "")
        donor = find_non_occurring_donor_quote(row, qid, donor_bundles)
        quote = donor["quote"]
        accepted = span_select.verify_span(text, quote, 0, len(quote))
        records.append({
            "decision_id": dec.decision_id,
            "donor_qid": donor["donor_qid"],
            "donor_decision_id": donor["donor_decision_id"],
            "donor_source": donor["source"],
            "donor_quote": quote,
            "donor_quote_occurs_in_target": quote in text,
            "donor_quote_rejected": not accepted,
        })
    return {
        "n_emitted_rows_checked": len(records),
        "all_donors_rejected": all(r["donor_quote_rejected"] for r in records),
        "records": records,
    }


__all__ = [
    "INVERSION_PREFIX",
    "REPAIR_ID",
    "SCORED_STATUSES",
    "canonical_json",
    "canonical_sha256",
    "cross_decision_verbatim_controls",
    "find_non_occurring_donor_quote",
    "load_bundle",
    "load_classifier",
    "load_product_modules",
    "load_rules_verified",
    "mutate_quote",
    "promoted_rows",
    "row_details",
    "run_baseline",
    "run_candidate",
    "run_inverted_control",
    "run_replacement_control",
    "run_seeded_controls",
    "run_swapped_control",
    "score_injection_rows",
    "sha256_bytes",
    "sha256_file",
    "summary_from_bundle",
    "verify_input_hashes",
]
