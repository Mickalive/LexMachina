"""Shared fixtures for frontier-counter-label-emission tests."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TEAM_ROOT = REPO_ROOT / "frontier" / "frontier-counter-label-emission"
if str(TEAM_ROOT) not in sys.path:
    sys.path.insert(0, str(TEAM_ROOT))

ACCEPTED = Path("/tmp/lex_accepted")
PACKET = ACCEPTED / "core" / "product" / "results" / "product" / "gate_packet" / "39319405429"
CLASSIFIER_ROOT = ACCEPTED / "core" / "product" / "product" / "vendored" / "frontier_counter_anchor_classifier"
RULES_PATH = ACCEPTED / "core" / "product" / "product" / "frozen" / "RULES_LABEL.json"

if CLASSIFIER_ROOT.is_dir():
    os.environ.setdefault("LEXMACHINA_CLASSIFIER_ROOT", str(CLASSIFIER_ROOT))
if RULES_PATH.is_file():
    os.environ.setdefault("LEXMACHINA_FROZEN_RULES", str(RULES_PATH))


def _has_accepted() -> bool:
    return CLASSIFIER_ROOT.is_dir() and RULES_PATH.is_file() and PACKET.is_dir()


requires_accepted = pytest.mark.skipif(
    not _has_accepted(),
    reason="accepted evidence mounts not available at /tmp/lex_accepted",
)


@pytest.fixture(scope="session")
def packet_dir() -> Path:
    return PACKET


@pytest.fixture(scope="session")
def classifier_root() -> Path:
    return CLASSIFIER_ROOT


@pytest.fixture(scope="session")
def rules_path() -> Path:
    return RULES_PATH


@pytest.fixture(scope="session")
def scored_statuses() -> tuple[str, ...]:
    from frontier_counter_label_emission import SCORED_STATUSES
    return SCORED_STATUSES


@pytest.fixture()
def base_bundle() -> dict:
    """A minimal synthetic bundle for attribution-tree tests."""
    return {
        "query": "Testfrage zur Fürsorgepflicht des Arbeitgebers",
        "language": "de",
        "decisions": [
            {
                "decision_id": "bge_1 III 1",
                "provenance": "ocl:adversarial.exception variant=adversarial:exception page=0",
                "adversarial_channel": "adversarial.exception",
                "adversarial_intent": "exception",
                "adversarial_retrieval_signal": {
                    "heuristic_status": "candidate-limiting",
                    "evidence": "Vorbehaltlich der ausdrücklichen Ausnahme begrenzt die Fürsorgepflicht die Überwachungspflicht bei Kapitalverletzung des Arbeitgebers.",
                    "markers": ["ausnahme"],
                },
                "counter_status": "none",
                "counter_evidence": "",
                "full_text_status": "fetched",
                "full_text": "Erwägungen. Vorbehaltlich der ausdrücklichen Ausnahme begrenzt die Fürsorgepflicht die Überwachungspflicht bei Kapitalverletzung des Arbeitgebers.",
                "language": "de",
                "rank": 1,
            },
            {
                "decision_id": "bge_2 III 2",
                "provenance": "ocl:search variant=original:any:deadbeef page=0",
                "counter_status": "none",
                "counter_evidence": "",
                "full_text_status": "lazy",
                "full_text": "",
                "language": "de",
                "rank": 2,
            },
        ],
        "provenance": {
            "qid": "de-kapitalverletzung",
            "adversarial_retrieval": {
                "component": "adversarial_retrieval/2",
                "attempted": True,
                "n_candidates": 20,
                "n_hydrated": 12,
                "probes": [{"intent": "exception", "query": "ausnahme fürsorgepflicht"}],
                "channels": ["adversarial.exception"],
                "label_topic_terms": ["fürsorgepflicht", "arbeitgeber", "überwachung"],
            },
            "generative_audit": {
                "adversarial": {
                    "n_findings": 0,
                    "model": "opencode/longcat-2.5-preview-free",
                    "attempts": [{"model": "opencode/space-bunny-free", "error": "rc=1"}],
                },
                "counter_surface_suppressed": 0,
            },
        },
    }
