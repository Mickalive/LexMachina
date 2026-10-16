"""Digest-pinned gate thresholds that ``frozen_benchmark.json`` does not carry.

WHY THIS EXISTS (cycle 38945976309)
-----------------------------------
``frozen_benchmark.json`` pins the four questions, their truth phrases, the
controlling-authority id sets, the answer-language set and the 300 s latency
budget.  Its SHA-256 is pinned in :data:`FROZEN_SHA256` and re-verified before
every execution, so any edit to those is caught.

Several *other* thresholds are gate values: they decide whether an artifact
passes or fails, but they lived only as literals inside ``gates.py`` —

=========================  ==================  =========================
gate                       literal              guarded by FROZEN_SHA256?
=========================  ==================  =========================
``structural::answer_method``      "generative_audit_llm_v2"      NO
``structural::adversarial_method`` "independent_llm_adversarial_v2" NO
``structural::prose_min_length``   120                            NO
``structural::source_urls_valid``  host "mcp.opencaselaw.ch"      NO
``corruption::clean``              8-gram / 60w / 0.35 / 4x / 0.01 NO
``multilingual::<bundle>``         >= 2 Swiss languages          NO
=========================  ==================  =========================

``AGENTS.md`` forbids weakening a frozen benchmark, but nothing mechanically
prevented any of those literals from moving.  ``GATE_CONTRACT.json`` gives them
a digest of their own; ``gates.py`` now reads its values from here, so editing a
literal in ``gates.py`` no longer has any effect and a silent edit anywhere
trips the pin in the tests.

Nothing was relaxed: every value equals the literal it replaced, the frozen
benchmark spec is untouched, and the recorded execution record recomputes to a
byte-identical verdict (see ``reports/evaluation/``).

Pure standard library; the evaluation harness does not import Product code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

GATE_CONTRACT_SHA256 = "06781743c2686fa63a6652ad61c8d63381cfa707f5fd6682a50b9027470d2492"

_DIR = Path(__file__).resolve().parent
_PATH = _DIR / "GATE_CONTRACT.json"


class GateContractError(RuntimeError):
    """The gate contract was tampered with or is structurally invalid."""


def load_contract() -> dict:
    raw = _PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != GATE_CONTRACT_SHA256:
        raise GateContractError(
            f"gate contract digest mismatch: {digest} != {GATE_CONTRACT_SHA256}. "
            "A gate threshold changed without a recorded re-freeze. Revert, or pin a "
            "new digest AND record the old and new value in the cycle report."
        )
    contract = json.loads(raw.decode("utf-8"))
    _validate(contract)
    return contract


def _validate(contract: dict) -> None:
    if contract.get("schema") != "lex-reality-gate-contract/1":
        raise GateContractError(f"unexpected schema {contract.get('schema')!r}")
    for key in ("answer", "source", "corruption", "multilingual", "recall"):
        if not isinstance(contract.get(key), dict) or not contract[key]:
            raise GateContractError(f"gate contract section {key!r} missing or empty")
    if not contract["answer"]["expected_answer_method"]:
        raise GateContractError("expected_answer_method must be a non-empty string")
    if not contract["answer"]["expected_adversarial_method"]:
        raise GateContractError("expected_adversarial_method must be a non-empty string")
    if int(contract["answer"]["min_prose_chars"]) <= 0:
        raise GateContractError("min_prose_chars must be positive")
    if int(contract["multilingual"]["min_swiss_languages"]) < 1:
        raise GateContractError("min_swiss_languages must be >= 1")
    if not contract["multilingual"]["swiss_languages"]:
        raise GateContractError("swiss_languages must list at least one language")
    for key, value in contract["corruption"].items():
        if not isinstance(value, (int, float)) or value <= 0:
            raise GateContractError(f"corruption.{key} must be a positive number")


def section(name: str, contract: dict | None = None) -> dict:
    """One contract section, loaded (and digest-verified) on first use."""
    contract = contract if contract is not None else load_contract()
    try:
        return contract[name]
    except KeyError as exc:  # pragma: no cover - validated at load
        raise GateContractError(f"unknown gate contract section {name!r}") from exc


_CACHED: dict | None = None


def cached() -> dict:
    """Process-level cache so gates never re-hash the contract per artifact."""
    global _CACHED
    if _CACHED is None:
        _CACHED = load_contract()
    return _CACHED