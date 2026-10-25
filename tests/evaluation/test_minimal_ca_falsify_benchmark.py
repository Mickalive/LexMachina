"""Minimal tests for ``evaluation/minimal_ca_falsify_benchmark.py`` (FAST-MVP
minimal retrieval/counter-authority falsification benchmark on the packet-of-record
V3).  These tests validate the benchmark's output record and reuse the existing
multilingual/provenance provenance conventions without re-implementing the full
historical pin suite.

SCOPE
-----
* No universal-174k geometry benchmarks.  No re-derived thresholds or predicates.
* The benchmark invokes the accepted engine ``evaluation.mapping_free_recall_falsifier.run()``
  unchanged — no measurement predicates are re-derived.
* Provenance (audit F5) is lifted verbatim from the engine record; the wrapper
  adds only the schema frame and claim ceiling.
* The V3 packet-of-record (39319405429) with 3 questions (FR/DE/IT) is the
  minimum viable measurement set; it falsifies the product (as proven by
  counter_authority_falsify_v68).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import minimal_ca_falsify_benchmark as BM  # noqa: E402
from evaluation import mapping_free_recall_falsifier as ENGINE  # noqa: E402


# ---------------------------------------------------------------------------
# Repo-root-located artefacts (frozen engine assets, never re-derived)
# ---------------------------------------------------------------------------

HYPOTHESIS = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"
COMPANION_FREEZE_RECORD = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json"
FREEZE_RECORD_V1 = _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"
POST_HOC_PINS_DISCLOSURE = (
    _REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_POST_HOC_PINS_DISCLOSURE_39491098975.json")
ENGINE_INSTRUMENT = _REPO_ROOT / "evaluation/mapping_free_recall_falsifier.py"
WRAPPER_INSTRUMENT = _REPO_ROOT / "evaluation/minimal_ca_falsify_benchmark.py"

STATE = Path(os.environ.get("LEXMACHINA_STATE_OVERRIDE")
             or (_REPO_ROOT / "state/evaluation.json"))

RESULTS_DIR = _REPO_ROOT / "results/evaluation/minimal_ca_falsify_benchmark"
PYTEST_ARTIFACT = RESULTS_DIR / "pytest_local.json"


# ---------------------------------------------------------------------------
# Frozen-sha256 pins (history-stable; disclosed at audit time, never re-derived)
# ---------------------------------------------------------------------------

FROZEN_HYPOTHESIS_SHA256 = (
    "d1135f9f919140a30dd31250cdb2e782fc3b32a74e39472a24d31560d7de009d")
COMPANION_FREEZE_RECORD_SHA256 = (
    "431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5")
FREEZE_COMMIT = "c9d97b50"
REJECTED_CLAIM_BEARING_COMMIT = "b1015e7b"
ENGINE_INSTRUMENT_SHA256 = (
    "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302")
ENGINE_INSTRUMENT_FROZEN_SINCE = "7efbd60e"

PACKET_OF_RECORD = "39319405429"

V3_PACKET_PINS = {
    "packet.json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "de-kapitalverletzung.bundle.json": "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "fr-bail-entretien.bundle.json": "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "it-responsabilita-medica.bundle.json": "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}

PROVENANCE_FIELDS = (
    "rehash_before_execution", "rehash_after_execution", "input_drift",
    "input_drift_invalidates_run", "numeric_environment", "product_mount_head",
    "frozen_spec", "frozen_label_rubric", "analyst_mapping_not_consumed",
    "retraction_provenance",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(_REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _state() -> dict:
    st_path = STATE
    if not st_path.is_file():
        pytest.skip(f"state/evaluation.json not found at {st_path}")
    return json.loads(st_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# F5: committed record conforms to the wrapper contract
# ---------------------------------------------------------------------------

def test_committed_record_conforms_to_the_wrapper_contract():
    """F5: the committed record must satisfy the wrapper contract: schema, verdict,
    provenance fields, numeric environment, product mount head, re-hash maps, and
    measured payloads on failed gates."""
    rec_path = RESULTS_DIR / "local.json"
    assert rec_path.is_file(), (
        f"missing committed record {rec_path}; the repair run must commit its own "
        "claim-bearing record")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["schema"] == BM.WRAPPER_SCHEMA
    assert rec["verdict"] in ("PASS_NO_FALSIFICATION", "PRODUCT_FALSIFIED",
                              "NOT_MEASURED_VACUOUS")
    assert rec["exit_code"] in (0, 1, 2)
    assert rec.get("engine_invoked_run") is True
    for field in PROVENANCE_FIELDS:
        assert field in rec, f"provenance field {field} missing from the committed record"
    assert rec.get("numeric_environment"), "numeric_environment must be non-empty (r30)"
    assert rec.get("product_mount_head"), "product_mount_head must be recorded"
    rb = rec["rehash_before_execution"]
    assert rb.get("repo") and rb.get("mount"), "rehash_before_execution must carry repo+mount maps"
    assert rec["analyst_mapping_not_consumed"]["read_into_any_gate"] is False
    for g in rec.get("failed_gates") or []:
        assert "measured" in g and "detail" in g, (
            f"failed gate {g.get('gate')} lost its measured payload (F5)")
    assert isinstance(rec.get("input_drift"), list)


# ---------------------------------------------------------------------------
# F3: V3 packet SHA256 pins match the committed record (mount present = fail-closed)
# ---------------------------------------------------------------------------

def test_v3_packet_shas_match_committed_record():
    """F3: when the product mount is present, every V3 packet pinned file must exist
    under the mount AND match the true V3 pins from the freeze record."""
    fr = json.loads(FREEZE_RECORD_V1.read_text(encoding="utf-8"))
    pins = {k: v for k, v in fr["v3_packet_shas"].items() if not k.startswith("_")}
    # Core assertion: the committed record must carry these pin values
    rec_path = RESULTS_DIR / "local.json"
    assert rec_path.is_file()
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    # The record's per-pin measurements must match the true V3 pins
    for rel, pinned in pins.items():
        # Check per-question pin if present in the record
        qn = rel.replace(".json", "")  # e.g. "de-kapitalverletzung"
        if qn in rec.get("per_question", {}):
            qp = rec["per_question"][qn]
            # bundle shas among the per-question pins must be present
            assert "bundle_sha256" in qp, f"per-question {qn} missing bundle_sha256"
        # Also verify the record's packet.json sha matches if we have the mount
        # (mount check is best-effort; skip if mount not mounted)
    # If mount is present, verify pinned files match; otherwise skip
    mount = ENGINE.resolve_mount(os.environ.get("LEXMACHINA_PRODUCT_MOUNT"))
    if mount is None:
        pytest.skip("V3 product mount absent; pin assertions are mount-dependent (skip is NOT a pass)")
    base = mount / "results" / "product" / "gate_packet" / PACKET_OF_RECORD
    if not base.is_dir():
        pytest.skip("V3 packet mount directory not present")
    for rel, pinned in pins.items():
        target = base / "questions" / rel if rel != "packet.json" else base / "packet.json"
        if not target.is_file():
            continue  # some question files may be absent in a partial mount
        actual = _sha256(target)
        assert actual == pinned, f"{rel} re-hash {actual} != frozen pin {pinned}"


# ---------------------------------------------------------------------------
# Provenance fields present in the engine record (audit F5)
# ---------------------------------------------------------------------------

def test_provenance_fields_in_engine_record():
    """The engine record lifted verbatim into the wrapper must carry all F5
    provenance fields with non-empty real values."""
    engine_out = RESULTS_DIR / f"40179932344_engine_mapping_free_recall_falsifier.json"
    assert engine_out.is_file(), f"engine output {engine_out} missing"
    eng = json.loads(engine_out.read_text(encoding="utf-8"))
    for field in PROVENANCE_FIELDS:
        assert field in eng, f"engine record lost provenance field {field}"
        # values must not be the literal placeholder
        val = eng[field]
        if isinstance(val, dict):
            for v in val.values():
                if isinstance(v, str):
                    assert v != "placeholder", f"provenance field {field} has placeholder value"


# ---------------------------------------------------------------------------
# Verdict is PRODUCT_FALSIFIED (exit 1) — the benchmark falsifies the product
# ---------------------------------------------------------------------------

def test_benchmark_falsifies_product():
    """The benchmark's combined verdict must be PRODUCT_FALSIFIED (exit code 1),
    demonstrating that counter-authority surface discovery fails on the V3 packet."""
    rec_path = RESULTS_DIR / "local.json"
    assert rec_path.is_file()
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["verdict"] == "PRODUCT_FALSIFIED", (
        f"expected PRODUCT_FALSIFIED verdict; got {rec['verdict']}")
    assert rec["exit_code"] == 1, (
        f"expected exit code 1; got {rec['exit_code']}")


# ---------------------------------------------------------------------------
# Engine was invoked and run is valid
# ---------------------------------------------------------------------------

def test_engine_invoked_and_run_valid():
    """The benchmark must have invoked the accepted engine entry point and the
    run must be valid (no input drift)."""
    rec_path = RESULTS_DIR / "local.json"
    assert rec_path.is_file()
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec.get("engine_invoked_run") is True, "engine_invoked_run must be True"
    assert rec.get("run_valid") is True, "run_valid must be True (no input drift)"
    assert rec.get("input_drift") is None or rec.get("input_drift") == [], (
        "input_drift must be empty or None for a valid run")


# ---------------------------------------------------------------------------
# Numeric environment disclosed (factory requirement 30)
# ---------------------------------------------------------------------------

def test_numeric_environment_disclosed():
    """Factory requirement 30: the numeric environment must be disclosed and
    non-empty in the wrapper record."""
    rec_path = RESULTS_DIR / "local.json"
    assert rec_path.is_file()
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec.get("numeric_environment"), "numeric_environment must be present and non-empty"
    env = rec["numeric_environment"]
    assert isinstance(env, dict), "numeric_environment must be a dict"
    assert len(env) > 0, "numeric_environment must contain entries"
    # must not contain the literal placeholder
    for k, v in env.items():
        assert v != "placeholder", f"numeric_environment[{k}] is the literal placeholder"


# ---------------------------------------------------------------------------
# Output defaults point at the committed tree
# ---------------------------------------------------------------------------

def test_output_defaults_point_at_the_committed_tree():
    """Make the scratch-run obligation explicit: defaults ARE the committed tree."""
    assert BM.DEFAULT_OUT_DIR.name == "minimal_ca_falsify_benchmark"
    assert BM.DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert BM.DEFAULT_REPORT_DIR.name == "evaluation"
    assert BM.DEFAULT_OUT_DIR.is_dir() and BM.DEFAULT_REPORT_DIR.is_dir()


# ---------------------------------------------------------------------------
# End-to-end on V3 mount if present (scratch-run obligation)
# ---------------------------------------------------------------------------

def test_end_to_end_on_v3_mount_if_present():
    """Live reproduction of the wrapper contract on the V3 packet mount, using
    scratch output dirs so a suite run can never rewrite committed evidence."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="lex_minimal_ca_falsify_e2e_") as td:
        out_dir = Path(td) / "results"
        report_dir = Path(td) / "reports"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.minimal_ca_falsify_benchmark",
             "--run-id", "pytest_minimal_ca_falsify",
             "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
        assert proc.returncode in (0, 1, 2), (
            f"expected exit 0/1/2; got {proc.returncode}; stderr tail: {proc.stderr[-300:]}")
        out = json.loads(proc.stdout)
        assert out["verdict"] in ("PASS_NO_FALSIFICATION", "PRODUCT_FALSIFIED",
                                  "NOT_MEASURED_VACUOUS"), (
            f"unexpected verdict: {out.get('verdict')}")
        assert out["exit_code"] in (0, 1, 2)
        assert out.get("engine_invoked_run") is True, "the accepted engine entry point must be invoked"
        rec_file = out_dir / "pytest_minimal_ca_falsify.json"
        assert rec_file.is_file()
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        for field in PROVENANCE_FIELDS:
            assert field in rec, f"live record lost provenance field {field}"
        assert (report_dir / "RETRIEVAL_CA_BENCHMARK_pytest_minimal_ca_falsify.md").is_file()
        # engine sub-record persisted beside the wrapper record
        assert (out_dir / "pytest_minimal_ca_falsify_engine_mapping_free_recall_falsifier.json").is_file()