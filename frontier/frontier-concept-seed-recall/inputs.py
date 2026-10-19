"""Accepted-input loading and digest verification.  Strictly READ-ONLY.

Every accepted artefact this harness reads is re-hashed before use and the
digest is compared with the digest the predecessor's accepted OUTCOME_B record
itself pinned.  A mismatch is a HEADLINE, never a warning: the run reproduces
nothing and ends as a bounded negative on non-reproduction.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PRODUCT_MOUNT = Path("/tmp/lex_accepted/core/product")
EVALUATION_MOUNT = Path("/tmp/lex_accepted/core/evaluation")
PREDECESSOR_EXTRACT = Path("/tmp/opencode/lm_forensic")

SERVED_QUESTIONS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")

#: Digests the accepted OUTCOME_B record of ``frontier-query-concept-recall``
#: pinned in its own ``RULES.json`` ``inputs.files`` block.  These are the
#: acceptance-test-(2) reproduction targets.
ACCEPTED_DIGESTS = {
    "frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "FREEZE_RECORD.json":
        "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    "retrieval_benchmark/39117425713.json":
        "f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75",
    "subject_match_audit/39113690481.json":
        "0adb78762e91090670728cf1441b75f14719a6066eb0a8ca8bfdf90a83845f61",
    "de-kapitalverletzung.bundle.json":
        "c4005d4b78553b0aebd92bba59001c87a376146873f807d575255a4f721dd7f2",
    "fr-bail-entretien.bundle.json":
        "0b3a224e3493479bc84628531eb7c56cac7dcfa978b29afbfc1305cb52574517",
    "it-responsabilita-medica.bundle.json":
        "6b43341242b5e1d4c305dcf29f12428541ceedc0b6cc89b5f2c8ae8d634f82b4",
    "concept_coverage.py":
        "ad4d768da915d7ddbfdb1ef2c11df1092316aca91760a51cf5ce296adad0f64d",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_evaluation_modules(mount: Path | None = None):
    """Import the ACCEPTED evaluation metric implementations by package path.

    ``evaluation.subject_match_audit`` supplies the frozen concept extraction and
    the coverage counting rule; ``evaluation.retrieval_gate.gates`` supplies the
    frozen authority-id matcher and every frozen gate.  This harness writes no
    matcher of its own.
    """
    m = Path(mount) if mount else EVALUATION_MOUNT
    if str(m) not in sys.path:
        sys.path.insert(0, str(m))
    import evaluation.retrieval_gate.frozen as rg_frozen  # noqa: PLC0415
    import evaluation.retrieval_gate.gates as rg_gates  # noqa: PLC0415
    import evaluation.subject_match_audit as sma  # noqa: PLC0415
    return sma, rg_gates, rg_frozen


def bundle_path(qid: str, product_mount: Path | None = None) -> Path:
    root = Path(product_mount) if product_mount else PRODUCT_MOUNT
    return root / "results/product/gate_packet/rebuilt-39027045675/questions" / f"{qid}.bundle.json"


def question_path(qid: str, product_mount: Path | None = None) -> Path:
    root = Path(product_mount) if product_mount else PRODUCT_MOUNT
    return root / "results/product/gate_packet/rebuilt-39027045675/questions" / f"{qid}.question.json"


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_digests(product_mount: Path | None = None,
                   evaluation_mount: Path | None = None) -> dict:
    """Re-hash every accepted input this run depends on."""
    prod = Path(product_mount) if product_mount else PRODUCT_MOUNT
    ev = Path(evaluation_mount) if evaluation_mount else EVALUATION_MOUNT
    targets: dict[str, Path] = {
        "frozen_retrieval_benchmark.json":
            ev / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
        "FREEZE_RECORD.json":
            ev / "evaluation/retrieval_gate/FREEZE_RECORD.json",
        "gates.py": ev / "evaluation/retrieval_gate/gates.py",
        "subject_match_audit.py": ev / "evaluation/subject_match_audit.py",
        "retrieval_benchmark/39117425713.json":
            ev / "results/evaluation/retrieval_benchmark/39117425713.json",
        "subject_match_audit/39113690481.json":
            ev / "results/evaluation/subject_match_audit/39113690481.json",
        "concept_coverage.py": prod / "product/query/concept_coverage.py",
    }
    for qid in SERVED_QUESTIONS:
        targets[f"{qid}.bundle.json"] = bundle_path(qid, prod)
        targets[f"{qid}.question.json"] = question_path(qid, prod)

    out: dict[str, Any] = {}
    for name, path in targets.items():
        present = Path(path).is_file()
        digest = sha256_file(path) if present else None
        expected = ACCEPTED_DIGESTS.get(name)
        out[name] = {
            "path": str(path),
            "present": present,
            "sha256": digest,
            "expected_sha256": expected,
            "match": (digest == expected) if (expected and digest) else None,
        }
    return out


__all__ = ["PRODUCT_MOUNT", "EVALUATION_MOUNT", "PREDECESSOR_EXTRACT",
           "SERVED_QUESTIONS", "ACCEPTED_DIGESTS", "sha256_file",
           "load_evaluation_modules", "bundle_path", "question_path",
           "load_json", "verify_digests"]


def _unused(_spec):  # pragma: no cover - keeps importlib import meaningful
    return importlib.util