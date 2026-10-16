"""Machine-readable verdict contract for the two accepted frozen-bar gates.

Every state the gates emit (process verdict, per-gate regression_verdict,
absolute_status) is enumerated in VERDICT_CONTRACT.json with the EXACT
accepted predicate and an explicit certifies / does_not_certify block, so a
packet-admission consumer cannot misread, for example,

    exit 0 + gate_blocks_build False  =>  "the label bar was met"

which is FALSE on any packet outside the pinned 65-row incumbent population
(the accepted trap of record; see VERDICT_CONTRACT.json
naive_consumer_trap and results/evaluation/verdict_contract/).

NO threshold, bar, rubric, lineage rule or incumbent value is defined here.
Every predicate is a literal restatement of the accepted
label_gate.score_packet / geometry_gate.score_packet / run_bar_gates code as
accepted in cycle 38971202786 (audit R1-corrected). Changing this contract is
a frozen-artifact change and requires a disclosed re-freeze, not an edit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
CONTRACT_PATH = _BAR_DIR / "VERDICT_CONTRACT.json"
EXPECTED_CONTRACT_SHA256 = (
    "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract(path: str | Path = CONTRACT_PATH, verify: bool = True) -> dict:
    """Load the contract; refuse a byte-drifted copy unless verify=False."""
    p = Path(path)
    if verify:
        observed = sha256_file(p)
        if observed != EXPECTED_CONTRACT_SHA256:
            raise RuntimeError(
                f"VERDICT_CONTRACT.json sha256 mismatch: expected "
                f"{EXPECTED_CONTRACT_SHA256}, observed {observed}. The contract is a "
                "frozen artifact of the accepted bar gates; changing it requires a "
                "disclosed re-freeze, not an edit. Refusing to classify."
            )
    data = json.loads(p.read_text(encoding="utf-8"))
    if verify and data.get("schema") != "lex-evaluation-bar-verdict-contract/1":
        raise RuntimeError(f"unexpected verdict-contract schema in {p}")
    return data


def contract_digest(path: str | Path = CONTRACT_PATH) -> dict:
    """Re-hash the contract; the only sanctioned way to read its digest."""
    p = Path(path)
    observed = sha256_file(p)
    return {
        "path": str(p),
        "expected_sha256": EXPECTED_CONTRACT_SHA256,
        "observed_sha256": observed,
        "matches": observed == EXPECTED_CONTRACT_SHA256,
    }


def classify_label(regression_verdict: str, absolute_status: str) -> dict:
    """Map one label-gate result to what a consumer may conclude.

    Returns the contract's certifies/does_not_certify text for the observed
    states plus the standing rule that NOT_APPLICABLE is not a pass.
    """
    c = load_contract()["label_gate"]
    out = {
        "gate": "counter-label-support",
        "regression_verdict": regression_verdict,
        "absolute_status": absolute_status,
        "regression_certifies": c["regression_verdict"]["certifies"].get(regression_verdict, "unknown state"),
        "regression_does_not_certify": c["regression_verdict"]["does_not_certify"].get(regression_verdict, ""),
        "absolute_certifies": c["absolute_status"]["certifies"].get(absolute_status, "unknown state"),
        "absolute_does_not_certify": c["absolute_status"]["does_not_certify"],
        "is_regression_not_a_pass": regression_verdict == "NOT_APPLICABLE",
    }
    return out


def classify_geometry(regression_verdict: str, absolute_status: str) -> dict:
    """Map one geometry-gate result to what a consumer may conclude."""
    c = load_contract()["geometry_gate"]
    return {
        "gate": "map-geometry-semantics",
        "regression_verdict": regression_verdict,
        "absolute_status": absolute_status,
        "regression_certifies": c["regression_verdict"]["certifies"].get(regression_verdict, "unknown state"),
        "regression_does_not_certify": c["regression_verdict"]["does_not_certify"].get(regression_verdict, ""),
        "absolute_certifies": c["absolute_status"]["certifies"].get(absolute_status, "unknown state"),
        "absolute_does_not_certify": c["absolute_status"]["does_not_certify"],
        "is_regression_not_a_pass": regression_verdict == "NOT_APPLICABLE",
    }


def admission_reading(label: dict, geometry: dict, exit_code: int) -> dict:
    """The machine-readable admission input Product's obligation (1) consumes.

    States explicitly what the observed gate output DOES and DOES NOT certify.
    It deliberately does NOT decide admission policy for Product; it refuses
    the misreadings that the accepted trap of record falsifies.
    """
    c = load_contract()["process"]
    naive_trap = (
        exit_code == 0
        and label.get("regression_verdict") == "NOT_APPLICABLE"
        and label.get("n_supported") == 0
    )
    return {
        "schema": "lex-evaluation-bar-admission-reading/1",
        "exit_code": exit_code,
        "exit_certifies": c["exit_codes"].get(str(exit_code), "unknown exit code"),
        "label": classify_label(label.get("regression_verdict", "NOT_APPLICABLE"),
                                label.get("absolute_status", "LABEL_UNSOUND")),
        "geometry": classify_geometry(geometry.get("regression_verdict", "NOT_APPLICABLE"),
                                      geometry.get("absolute_status", "GEOMETRY_UNSOUND")),
        "naive_consumer_trap_fires": naive_trap,
        "naive_consumer_trap_meaning": c["naive_consumer_trap"]["meaning"] if naive_trap else None,
        "required_reading": (
            "gate_blocks_build==false / exit 0 is NOT a statement that the counter-label bar "
            "was met; read label absolute_status explicitly for packets outside the pinned "
            "65-row incumbent population"
        ),
    }
