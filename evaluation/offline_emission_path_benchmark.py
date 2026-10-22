#!/usr/bin/env python3
"""Offline emission-path falsifier on the packet-of-record v3 heuristic signals.

Ordered work (1) of factory direction v63 evaluation: remedy (a) has landed on
the accepted product mount; this instrument re-scores the mapping-free
counter_authority_surface predicate on the POST-PATH bundle bytes after the
shipped offline emission path (emission repair + anchor classifier) runs.

What is measured
----------------
For each of de-kapitalverletzung / fr-bail-entretien / it-responsabilita-medica
on packet 39319405429 (accepted product mount bytes only, ZERO network):

1. count the existing adversarial_retrieval_signal rows with non-empty evidence;
2. apply product/query/counter_emission_repair.apply_counter_emission_repair
   (vendored frontier-counter-label-emission, Outcome A);
3. apply product/query/counter_anchor.apply_anchor_labels (vendored
   frontier-counter-anchor-classifier, Outcome A, abstain-and-disclose);
4. re-score the frozen mapping-free predicate imported from
   evaluation.mapping_free_recall_falsifier.counter_authority_surface (no
   re-derivation);
5. publish n_scored / n_abstained / n_emitted / yield beside the gate.

Exit codes
----------
0  PATH_MEASURED_NO_FALSIFICATION  every measured gate held
1  PRODUCT_PATH_FALSIFIED          a promotion/vocabulary/publication gate failed
2  ENVIRONMENT_OR_VACUOUS          a control failed, a pin drifted, network fired
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.mapping_free_recall_falsifier import (  # noqa: E402
    counter_authority_surface as mf_counter_surface,
)

SCHEMA = "lex-evaluation-offline-emission-path-benchmark/1"
HYPOTHESIS_RELPATH = "evaluation/OFFLINE_EMISSION_PATH_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/OFFLINE_EMISSION_PATH_FREEZE_RECORD_V1.json"
DEFAULT_MOUNT = "/tmp/lex_accepted/product"
PACKET = "39319405429"
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/offline_emission_path"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_VACUOUS = 2

CLAIM_CEILING = (
    "This instrument establishes exactly one thing: on the accepted product mount "
    "and the packet-of-record v3 bundle bytes, whether the shipped offline emission "
    "path promotes the existing heuristic signals, publishes the three numbers, and "
    "what the frozen mapping-free counter_authority_surface predicate scores on the "
    "post-path bytes. It does NOT meet, move or re-derive the frozen absolute "
    "LABEL_SOUND or GEOMETRY_SOUND bars; it does NOT lift either DO-NOT-SERVE order; "
    "it does NOT certify packet admission; it does NOT claim the map helps a jurist; "
    "it does NOT claim the comparative map-versus-ranked-list question is non-vacuous "
    "unless n_emitted>0 is measured; it does NOT rebuild any Frontier component; it "
    "runs no obsolete universal-174k benchmark; human_gate_ready stays false."
)

REUSED = {
    "apply_counter_emission_repair": "product/query/counter_emission_repair.py (Outcome A frontier-counter-label-emission)",
    "apply_anchor_labels": "product/query/counter_anchor.py (Outcome A frontier-counter-anchor-classifier)",
    "mf_counter_surface": "evaluation.mapping_free_recall_falsifier.counter_authority_surface (accepted gate predicate)",
    "scored_statuses": "evaluation/frozen_bars/RULES_LABEL.json rubric.scored_statuses (re-hashed)",
    "packets": "results/product/gate_packet/39319405429/questions/*.bundle.json on the accepted product mount",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def numeric_environment() -> dict[str, Any]:
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
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[var] = os.environ.get(var, "unset")
    return env


def mount_head(mount: Path) -> str | None:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(mount), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


class NetworkGuard:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._orig_connect = None
        self._orig_create = None

    def __enter__(self) -> "NetworkGuard":
        self._orig_connect = socket.socket.connect
        self._orig_create = socket.create_connection

        def blocked_connect(sock, address):
            self.calls.append(f"connect:{address!r}")
            raise RuntimeError("NETWORK DISABLED by offline emission path benchmark")

        def blocked_create(address, *args, **kwargs):
            self.calls.append(f"create_connection:{address!r}")
            raise RuntimeError("NETWORK DISABLED by offline emission path benchmark")

        socket.socket.connect = blocked_connect  # type: ignore[assignment]
        socket.create_connection = blocked_create  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        if self._orig_connect is not None:
            socket.socket.connect = self._orig_connect  # type: ignore[assignment]
        if self._orig_create is not None:
            socket.create_connection = self._orig_create  # type: ignore[assignment]


def load_product_modules(mount: Path) -> dict[str, Any]:
    """Load the three product modules by file path from the accepted mount."""
    query_root = mount / "product" / "query"
    package_name = "_lex_product_query_emission_path"
    pkg = type(sys)(package_name)
    pkg.__path__ = [str(query_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = pkg

    # counter_emission_repair imports .counter_anchor relatively; seed both.
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


def load_bundle(mount: Path, qid: str) -> dict:
    path = mount / "results" / "product" / "gate_packet" / PACKET / "questions" / f"{qid}.bundle.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing bundle for {qid}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def signal_rows(bundle: dict) -> list[dict]:
    out = []
    for d in bundle.get("decisions") or []:
        sig = d.get("adversarial_retrieval_signal") or {}
        status = str(sig.get("heuristic_status") or "").strip()
        evidence = str(sig.get("evidence") or "").strip()
        if status and evidence:
            out.append(d)
    return out


def measure_question(
    mount: Path,
    qid: str,
    modules: dict[str, Any],
    scored_statuses: list[str],
    network: NetworkGuard,
) -> dict[str, Any]:
    cer = modules["counter_emission_repair"]
    ca = modules["counter_anchor"]

    baseline_bundle = load_bundle(mount, qid)
    baseline_signals = signal_rows(baseline_bundle)
    baseline_anchor = (baseline_bundle.get("provenance") or {}).get("counter_anchor") or {}
    baseline_emission = (baseline_bundle.get("provenance") or {}).get("counter_emission_repair")
    baseline_mf = mf_counter_surface(baseline_bundle, scored_statuses)

    # --- promotion (emission repair) ---
    promoted_bundle = cer.apply_counter_emission_repair(copy.deepcopy(baseline_bundle))
    emission_prov = (promoted_bundle.get("provenance") or {}).get("counter_emission_repair") or {}
    n_promoted = int(emission_prov.get("n_promoted") or 0)
    n_scored_status_after = sum(
        1 for d in promoted_bundle.get("decisions") or []
        if str(d.get("counter_status") or "").strip() in set(scored_statuses)
    )
    out_of_vocab = [
        str(d.get("decision_id") or "")[:80]
        for d in promoted_bundle.get("decisions") or []
        if str(d.get("counter_proposal_source") or "") == "heuristic_proposal_promotion_v1"
        and str(d.get("counter_status") or "").strip() not in set(scored_statuses)
        and str(d.get("counter_status") or "").strip() not in ("none", "cited", "")
    ]

    # --- classifier (anchor labels) ---
    final_bundle = ca.apply_anchor_labels(promoted_bundle, qid=qid)
    anchor_prov = (final_bundle.get("provenance") or {}).get("counter_anchor") or {}
    mf_final = mf_counter_surface(final_bundle, scored_statuses)

    n_scored = int(anchor_prov.get("n_scored") or 0)
    n_abstained = int(anchor_prov.get("n_abstained") or 0)
    n_emitted = int(anchor_prov.get("n_emitted") or 0)
    yield_v = anchor_prov.get("yield")
    support = anchor_prov.get("support_rate_among_emitted")

    # language distribution of abstained/emitted (multilingual coverage)
    lang_emitted: dict[str, int] = {}
    lang_abstained: dict[str, int] = {}
    for d in final_bundle.get("decisions") or []:
        lang = str(d.get("language") or "UNLABELLED")
        st = str(d.get("counter_status") or "")
        if st in set(scored_statuses):
            lang_emitted[lang] = lang_emitted.get(lang, 0) + 1
        elif st == str(ca.ABSTAINED_STATUS):
            lang_abstained[lang] = lang_abstained.get(lang, 0) + 1

    gates = {
        "E1_promotion_matches_heuristic_signal_count": {
            "passed": n_promoted == len(baseline_signals),
            "detail": (
                f"n_promoted={n_promoted} vs heuristic-signal rows with evidence="
                f"{len(baseline_signals)}"
            ),
            "measured": {
                "n_promoted": n_promoted,
                "n_heuristic_signal_rows": len(baseline_signals),
            },
        },
        "E2_scored_statuses_after_repair": {
            "passed": (
                n_promoted > 0 and n_scored_status_after == n_promoted
            ) or (n_promoted == 0),
            "detail": (
                f"after repair, {n_scored_status_after}/{n_promoted} promoted rows "
                f"carry a frozen scored status; out_of_vocab={out_of_vocab[:5]}"
            ),
            "measured": {
                "n_scored_status_after_repair": n_scored_status_after,
                "n_promoted": n_promoted,
                "out_of_vocab_examples": out_of_vocab[:5],
                "scored_statuses": list(scored_statuses),
            },
        },
        "E3_three_number_publication": {
            "passed": all(
                isinstance(v, (int, float))
                for v in (n_scored, n_abstained, n_emitted, yield_v)
            ) and "yield" in anchor_prov,
            "detail": (
                f"n_scored={n_scored} n_abstained={n_abstained} "
                f"n_emitted={n_emitted} yield={yield_v}"
            ),
            "measured": {
                "n_scored": n_scored,
                "n_abstained": n_abstained,
                "n_emitted": n_emitted,
                "yield": yield_v,
                "support_rate_among_emitted": support,
                "abstention_reasons": anchor_prov.get("abstention_reasons") or {},
            },
        },
        "E4_mapping_free_counter_surface_rescored": {
            "passed": None,  # REPORTED, never pass/fail by design of this gate
            "detail": (
                f"post-path mf::counter_authority_surface n_issued="
                f"{mf_final['n_issued']} n_with_empty_evidence="
                f"{mf_final['n_with_empty_evidence']}; gate_pass="
                f"{mf_final['n_issued'] >= 1 and mf_final['n_with_empty_evidence'] == 0}"
            ),
            "measured": {
                "baseline": baseline_mf,
                "post_path": mf_final,
                "gate_pass": mf_final["n_issued"] >= 1
                and mf_final["n_with_empty_evidence"] == 0,
            },
        },
        "E5_multilingual_coverage": {
            "passed": True,  # all three QIDS are always measured; this is structural
            "detail": f"qid={qid} language_emitted={lang_emitted} language_abstained={lang_abstained}",
            "measured": {
                "language_emitted": lang_emitted,
                "language_abstained": lang_abstained,
            },
        },
    }

    # --- C3 blanked promotion control on a copy ---
    blanked = copy.deepcopy(baseline_bundle)
    for d in blanked.get("decisions") or []:
        d.pop("adversarial_retrieval_signal", None)
    blanked_out = cer.apply_counter_emission_repair(blanked)
    blanked_n = int(
        ((blanked_out.get("provenance") or {}).get("counter_emission_repair") or {}).get("n_promoted") or 0
    )

    return {
        "qid": qid,
        "baseline": {
            "n_heuristic_signal_rows": len(baseline_signals),
            "counter_emission_repair_present": baseline_emission is not None,
            "counter_anchor": {
                k: baseline_anchor.get(k)
                for k in ("n_scored", "n_emitted", "n_abstained", "yield")
            },
            "mf_counter_surface": baseline_mf,
        },
        "post_path": {
            "n_promoted": n_promoted,
            "n_scored_status_after_repair": n_scored_status_after,
            "n_scored": n_scored,
            "n_abstained": n_abstained,
            "n_emitted": n_emitted,
            "yield": yield_v,
            "support_rate_among_emitted": support,
            "abstention_reasons": anchor_prov.get("abstention_reasons") or {},
            "mf_counter_surface": mf_final,
            "mf_gate_pass": mf_final["n_issued"] >= 1
            and mf_final["n_with_empty_evidence"] == 0,
        },
        "gates": gates,
        "controls": {
            "C3_blanked_promotion_control": {
                "passed": blanked_n == 0,
                "detail": f"blanked bundle n_promoted={blanked_n} (expected 0)",
                "measured": {"n_promoted": blanked_n},
            }
        },
        "network_calls_during_question": list(network.calls),
    }


def run(run_id: str, out_dir: Path, report_dir: Path,
        product_mount: str | None = None) -> tuple[int, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    mount = Path(product_mount or DEFAULT_MOUNT)
    if not mount.is_dir():
        rec = {
            "schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
            "exit_code": EXIT_VACUOUS,
            "reason": f"product mount missing: {mount}",
            "claim_ceiling": CLAIM_CEILING, "human_gate_ready": False,
            "generated_at_utc": utc_now(),
            "aggregate": {
                "n_promoted_total": 0, "n_scored_total": 0,
                "n_abstained_total": 0, "n_emitted_total": 0,
                "comparative_map_vs_ranked_list": "VACUOUS",
                "packet_admitted": False, "human_gate_ready": False,
                "machine_gate_ready": False,
            },
        }
        return EXIT_VACUOUS, rec

    # pins before
    pins_before: dict[str, str] = {}
    freeze = json.loads((REPO_ROOT / FREEZE_RELPATH).read_text(encoding="utf-8"))
    for label, expected in (freeze.get("pins_before_execution") or {}).items():
        if label.startswith("product_mount:"):
            path = mount / label.split(":", 1)[1]
        else:
            path = REPO_ROOT / label
        observed = sha256_file(path) if path.is_file() else None
        pins_before[label] = observed or "MISSING"
        if observed != expected:
            rec = {
                "schema": SCHEMA, "run_id": run_id,
                "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_VACUOUS,
                "reason": f"pin drift before execution: {label} {observed} != {expected}",
                "claim_ceiling": CLAIM_CEILING, "human_gate_ready": False,
                "generated_at_utc": utc_now(),
                "aggregate": {
                    "n_promoted_total": 0, "n_scored_total": 0,
                    "n_abstained_total": 0, "n_emitted_total": 0,
                    "comparative_map_vs_ranked_list": "VACUOUS",
                    "packet_admitted": False, "human_gate_ready": False,
                    "machine_gate_ready": False,
                },
            }
            return EXIT_VACUOUS, rec

    rules = json.loads((REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json").read_text(encoding="utf-8"))
    scored_statuses = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])

    try:
        modules = load_product_modules(mount)
    except Exception as exc:
        rec = {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_VACUOUS,
            "reason": f"cannot load product modules: {type(exc).__name__}: {exc}",
            "claim_ceiling": CLAIM_CEILING, "human_gate_ready": False,
            "generated_at_utc": utc_now(),
            "aggregate": {"n_promoted_total": 0, "n_scored_total": 0,
                          "n_abstained_total": 0, "n_emitted_total": 0,
                          "comparative_map_vs_ranked_list": "VACUOUS",
                          "packet_admitted": False, "human_gate_ready": False,
                          "machine_gate_ready": False},
        }
        return EXIT_VACUOUS, rec

    cer = modules["counter_emission_repair"]
    ca = modules["counter_anchor"]

    controls: dict[str, Any] = {}
    # C1 vendored repair rehash
    try:
        vend = cer.verify_vendored()
        controls["C1_vendored_repair_rehash"] = {
            "passed": bool(vend.get("ok")), "detail": "verify_vendored ok",
            "measured": {"component": vend.get("component")},
        }
    except Exception as exc:
        controls["C1_vendored_repair_rehash"] = {
            "passed": False,
            "detail": f"verify_vendored failed: {type(exc).__name__}: {exc}",
        }
        rec = {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_VACUOUS,
            "reason": "C1 failed", "controls": controls,
            "claim_ceiling": CLAIM_CEILING, "human_gate_ready": False,
            "generated_at_utc": utc_now(),
            "aggregate": {"n_promoted_total": 0, "n_scored_total": 0,
                          "n_abstained_total": 0, "n_emitted_total": 0,
                          "comparative_map_vs_ranked_list": "VACUOUS",
                          "packet_admitted": False, "human_gate_ready": False,
                          "machine_gate_ready": False},
        }
        return EXIT_VACUOUS, rec

    # C2 frozen rubric rehash (before)
    rules_sha = sha256_file(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json")
    expected_rules = (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    )
    controls["C2_frozen_rubric_rehash"] = {
        "passed": rules_sha == expected_rules,
        "detail": f"RULES_LABEL.json sha256 {rules_sha}",
        "measured": {"observed": rules_sha, "expected": expected_rules},
    }
    if not controls["C2_frozen_rubric_rehash"]["passed"]:
        rec = {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_VACUOUS,
            "reason": "C2 failed", "controls": controls,
            "claim_ceiling": CLAIM_CEILING, "human_gate_ready": False,
            "generated_at_utc": utc_now(),
            "aggregate": {"n_promoted_total": 0, "n_scored_total": 0,
                          "n_abstained_total": 0, "n_emitted_total": 0,
                          "comparative_map_vs_ranked_list": "VACUOUS",
                          "packet_admitted": False, "human_gate_ready": False,
                          "machine_gate_ready": False},
        }
        return EXIT_VACUOUS, rec

    # C5 planted-row non-vacuity: the classifier must DECIDE (emit or abstain
    # with a reason code) on a planted scored-status row under a FROZEN anchor
    # profile. A qid that does not resolve to a frozen profile makes the seam
    # fail safe with applied=false, which is not a classification.
    planted = {
        "query": (
            "Unter welchen Voraussetzungen haftet der Arbeitgeber bei "
            "Kapitalverletzung und Ueberwachungspflicht?"
        ),
        "decisions": [{
            "decision_id": "planted_control_0001",
            "decision_type": "bger",
            "court": "Bundesgericht",
            "language": "de",
            "legal_area": "arbeitsrecht",
            "title": "Kapitalverletzung und Ueberwachungspflicht des Arbeitgebers",
            "regeste": "Art. 328 OR; Kapitalverletzung; Ueberwachungspflicht.",
            "counter_status": "candidate-limiting",
            "counter_evidence": (
                "Das Bundesgericht hielt unter Hinweis auf die Ueberwachungspflicht "
                "des Arbeitgebers fest, dass eine Kapitalverletzung die "
                "arbeitsrechtliche Sorgepflicht konkretisiert und die "
                "Aufloesungsklage nur subsidiar zulaessig ist."
            ),
            "counter_markers": ["limiting"],
        }],
        "provenance": {},
    }
    try:
        planted_out = ca.apply_anchor_labels(copy.deepcopy(planted), qid="de-kapitalverletzung")
        planted_prov = (planted_out.get("provenance") or {}).get("counter_anchor") or {}
        planted_row = (planted_out.get("decisions") or [{}])[0]
        classified = (
            planted_prov.get("applied") is True
            and (
                "counter_anchor_decision" in planted_row
                or "counter_reason_code" in planted_row
                or int(planted_prov.get("n_scored") or 0) >= 1
            )
        )
        controls["C5_anchor_classifier_nonvacuity"] = {
            "passed": bool(classified),
            "detail": (
                f"planted row classified={classified} applied="
                f"{planted_prov.get('applied')} n_scored={planted_prov.get('n_scored')} "
                f"reason={planted_row.get('counter_reason_code')} "
                f"final_status={planted_row.get('counter_status')}"
            ),
            "measured": {
                "applied": planted_prov.get("applied"),
                "n_scored": planted_prov.get("n_scored"),
                "n_emitted": planted_prov.get("n_emitted"),
                "n_abstained": planted_prov.get("n_abstained"),
                "reason_code": planted_row.get("counter_reason_code"),
                "final_status": planted_row.get("counter_status"),
            },
        }
    except Exception as exc:
        controls["C5_anchor_classifier_nonvacuity"] = {
            "passed": False,
            "detail": f"planted classification raised: {type(exc).__name__}: {exc}",
        }

    # --- main measurement under network guard ---
    network = NetworkGuard()
    questions: list[dict] = []
    with network:
        for qid in QIDS:
            try:
                questions.append(measure_question(mount, qid, modules, scored_statuses, network))
            except Exception as exc:
                rec = {
                    "schema": SCHEMA, "run_id": run_id,
                    "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_VACUOUS,
                    "reason": f"measure_question({qid}) raised: {type(exc).__name__}: {exc}",
                    "controls": controls, "claim_ceiling": CLAIM_CEILING,
                    "human_gate_ready": False, "generated_at_utc": utc_now(),
                    "aggregate": {"n_promoted_total": 0, "n_scored_total": 0,
                                  "n_abstained_total": 0, "n_emitted_total": 0,
                                  "comparative_map_vs_ranked_list": "VACUOUS",
                                  "packet_admitted": False, "human_gate_ready": False,
                                  "machine_gate_ready": False},
                }
                return EXIT_VACUOUS, rec

    controls["C4_zero_network"] = {
        "passed": len(network.calls) == 0,
        "detail": f"network calls={len(network.calls)}",
        "measured": {"calls": list(network.calls)},
    }

    # C3 aggregate
    c3_all = all(
        (q.get("controls") or {}).get("C3_blanked_promotion_control", {}).get("passed")
        for q in questions
    )
    controls["C3_blanked_promotion_control"] = {
        "passed": c3_all,
        "detail": "every blanked bundle yielded n_promoted=0" if c3_all
        else "at least one blanked bundle promoted a row",
        "measured": {
            q["qid"]: (q.get("controls") or {}).get("C3_blanked_promotion_control", {}).get("measured")
            for q in questions
        },
    }

    # pins after
    pins_after: dict[str, str] = {}
    for label in pins_before:
        if label.startswith("product_mount:"):
            path = mount / label.split(":", 1)[1]
        else:
            path = REPO_ROOT / label
        pins_after[label] = sha256_file(path) if path.is_file() else "MISSING"
    drift = [k for k in pins_before if pins_before[k] != pins_after.get(k)]

    all_controls_hold = all(c.get("passed") for c in controls.values())

    # Gates across questions: E1, E2, E3 must hold on every question.
    e1_ok = all(q["gates"]["E1_promotion_matches_heuristic_signal_count"]["passed"] for q in questions)
    e2_ok = all(q["gates"]["E2_scored_statuses_after_repair"]["passed"] for q in questions)
    e3_ok = all(q["gates"]["E3_three_number_publication"]["passed"] for q in questions)

    total_emitted = sum(int(q["post_path"]["n_emitted"] or 0) for q in questions)
    total_scored = sum(int(q["post_path"]["n_scored"] or 0) for q in questions)
    total_abstained = sum(int(q["post_path"]["n_abstained"] or 0) for q in questions)
    total_promoted = sum(int(q["post_path"]["n_promoted"] or 0) for q in questions)
    mf_gates_pass = [
        bool(q["post_path"]["mf_gate_pass"]) for q in questions
    ]

    if drift or not all_controls_hold:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        code = EXIT_VACUOUS
        reason = (
            f"pin drift={drift}" if drift else
            "a control failed: " + ", ".join(k for k, c in controls.items() if not c.get("passed"))
        )
    elif not (e1_ok and e2_ok and e3_ok):
        verdict = "PRODUCT_PATH_FALSIFIED"
        code = EXIT_FALSIFIED
        failed = []
        if not e1_ok:
            failed.append("E1")
        if not e2_ok:
            failed.append("E2")
        if not e3_ok:
            failed.append("E3")
        reason = f"gate(s) failed on the exact accepted bytes: {','.join(failed)}"
    else:
        verdict = "PATH_MEASURED_NO_FALSIFICATION"
        code = EXIT_PASS
        reason = (
            f"promotion and three-number publication held; total "
            f"n_scored={total_scored} n_abstained={total_abstained} "
            f"n_emitted={total_emitted}; comparative half "
            f"{'NON_VACUOUS (n_emitted>0)' if total_emitted > 0 else 'VACUOUS (n_emitted=0)'}"
        )

    comparative = (
        "NON_VACUOUS" if total_emitted > 0 else "VACUOUS"
    )

    rec: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "lane": "evaluation",
        "direction_version": freeze.get("direction_version"),
        "verdict": verdict,
        "exit_code": code,
        "reason": reason,
        "claim_ceiling": CLAIM_CEILING,
        "reused_accepted_assets": REUSED,
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "packet": PACKET,
        "questions_measured": list(QIDS),
        "scored_statuses": list(scored_statuses),
        "aggregate": {
            "n_promoted_total": total_promoted,
            "n_scored_total": total_scored,
            "n_abstained_total": total_abstained,
            "n_emitted_total": total_emitted,
            "comparative_map_vs_ranked_list": comparative,
            "mf_counter_surface_gate_pass_per_question": dict(zip(QIDS, mf_gates_pass)),
            "frozen_absolute_bars": "REPORTED-ONLY and unmet on the v3 bytes; not re-derived here",
            "packet_admitted": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
        },
        "gates_summary": {
            "E1_all_questions": e1_ok,
            "E2_all_questions": e2_ok,
            "E3_all_questions": e3_ok,
            "E4_reported_only": True,
            "E5_all_languages": True,
        },
        "controls": controls,
        "questions": questions,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "input_drift": drift,
        "numeric_environment": numeric_environment(),
        "network_calls": list(network.calls),
        "human_gate_ready": False,
        "packet_admitted": False,
    }

    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = report_dir / f"OFFLINE_EMISSION_PATH_{run_id}.md"
    report.write_text(_render_report(rec), encoding="utf-8")
    rec["result_file"] = str(out_path)
    rec["report_file"] = str(report)
    return code, rec


def _render_report(rec: dict) -> str:
    lines = [
        f"# Offline Emission Path Benchmark — run {rec['run_id']}",
        "",
        f"- Verdict: **{rec['verdict']}** (exit {rec['exit_code']})",
        f"- Reason: {rec['reason']}",
        f"- Product mount head: `{rec.get('product_mount_head')}`",
        f"- Packet: {rec.get('packet')}",
        f"- Generated: {rec['generated_at_utc']}",
        "",
        "## Aggregate (three-number publication)",
        "",
        f"- n_promoted total: {rec['aggregate']['n_promoted_total']}",
        f"- n_scored total: {rec['aggregate']['n_scored_total']}",
        f"- n_abstained total: {rec['aggregate']['n_abstained_total']}",
        f"- n_emitted total: {rec['aggregate']['n_emitted_total']}",
        f"- Comparative map-versus-ranked-list half: **{rec['aggregate']['comparative_map_vs_ranked_list']}**",
        f"- Frozen absolute bars: {rec['aggregate']['frozen_absolute_bars']}",
        "",
        "## Per-question",
        "",
    ]
    for q in rec.get("questions") or []:
        pp = q["post_path"]
        lines.append(f"### {q['qid']}")
        lines.append("")
        lines.append(
            f"- baseline heuristic signals: {q['baseline']['n_heuristic_signal_rows']}; "
            f"baseline emission repair present: {q['baseline']['counter_emission_repair_present']}; "
            f"baseline anchor: {q['baseline']['counter_anchor']}"
        )
        lines.append(
            f"- post-path: n_promoted={pp['n_promoted']} n_scored={pp['n_scored']} "
            f"n_abstained={pp['n_abstained']} n_emitted={pp['n_emitted']} "
            f"yield={pp['yield']} abstention_reasons={pp['abstention_reasons']}"
        )
        lines.append(
            f"- post-path mf::counter_authority_surface n_issued="
            f"{pp['mf_counter_surface']['n_issued']} gate_pass={pp['mf_gate_pass']}"
        )
        e = q["gates"]["E1_promotion_matches_heuristic_signal_count"]
        lines.append(f"- E1: {e['passed']} — {e['detail']}")
        lines.append("")
    lines += [
        "## Controls",
        "",
    ]
    for name, c in (rec.get("controls") or {}).items():
        lines.append(f"- **{name}**: {c.get('passed')} — {c.get('detail')}")
    lines += [
        "",
        "## Claim ceiling",
        "",
        rec.get("claim_ceiling") or "",
        "",
        f"Input drift: {rec.get('input_drift')}",
        f"Network calls: {rec.get('network_calls')}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report-dir", default=None)
    ap.add_argument("--product-mount", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else DEFAULT_OUT_DIR
    report = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    code, rec = run(args.run_id, out, report, args.product_mount)
    print(json.dumps({
        "verdict": rec.get("verdict"),
        "exit_code": rec.get("exit_code"),
        "reason": rec.get("reason"),
        "result_file": rec.get("result_file"),
    }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
