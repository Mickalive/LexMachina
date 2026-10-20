"""Test configuration: put the team namespace on sys.path, load frozen fixtures."""
import sys
from pathlib import Path

import pytest

TEAM_ROOT = Path(__file__).resolve().parents[3] / "frontier" / "frontier-packet-serve-audit"
if str(TEAM_ROOT) not in sys.path:
    sys.path.insert(0, str(TEAM_ROOT))

FROZEN_RULES_DIR = Path("/tmp/lex_accepted/core/evaluation/evaluation/frozen_bars")
PACKET_DIR = Path("/tmp/lex_accepted/core/product/results/product/gate_packet/39319405429")
PRODUCT_MOUNT = Path("/tmp/lex_accepted/core/product")
EVAL_MOUNT = Path("/tmp/lex_accepted/core/evaluation")


@pytest.fixture(scope="session")
def frozen_rules_dir():
    return FROZEN_RULES_DIR


@pytest.fixture(scope="session")
def packet_dir():
    return PACKET_DIR


@pytest.fixture(scope="session")
def product_mount():
    return PRODUCT_MOUNT


@pytest.fixture(scope="session")
def eval_mount():
    return EVAL_MOUNT


@pytest.fixture(scope="session")
def label_rules():
    from frontier_packet_serve_audit.label_gate import load_frozen_rules
    return load_frozen_rules(FROZEN_RULES_DIR / "RULES_LABEL.json")


@pytest.fixture(scope="session")
def geometry_rules():
    from frontier_packet_serve_audit.geometry_gate import load_frozen_geometry_rules
    return load_frozen_geometry_rules(FROZEN_RULES_DIR / "RULES_GEOMETRY.json")


@pytest.fixture(scope="session")
def real_bundles():
    import json
    qids = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
    return {qid: json.loads((PACKET_DIR / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8"))
            for qid in qids}


def _mini_bundle(n=30, seed=0):
    """A small deterministic synthetic bundle for unit tests."""
    import random
    rng = random.Random(seed)
    decisions = []
    for i in range(n):
        decisions.append({
            "decision_id": f"dec_{i:03d}",
            "rank": i + 1,
            "language": "de" if i % 3 == 0 else ("fr" if i % 3 == 1 else "it"),
            "title": f"Case {i} about kapitalverletzung and sorgepflicht",
            "regeste": "Arbeitgeber kapitalverletzung sorgepflicht eingriff",
            "snippet": "text",
            "full_text": "full text about the case " * 20,
            "counter_status": "none",
            "counter_evidence": "",
            "cluster_id": i % 3,
            "x": rng.random(),
            "y": rng.random(),
            "is_outlier": i % 7 == 0,
            "score": 100.0 - i,
        })
    clusters = [
        {"cluster_id": 0, "label": "kapitalverletzung arbeitgeber", "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 0], "size": sum(1 for d in decisions if d["cluster_id"] == 0)},
        {"cluster_id": 1, "label": "sorgepflicht eingriff", "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 1], "size": sum(1 for d in decisions if d["cluster_id"] == 1)},
        {"cluster_id": 2, "label": "ueberwachungpflicht", "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 2], "size": sum(1 for d in decisions if d["cluster_id"] == 2)},
    ]
    relations = [
        {"source": decisions[0]["decision_id"], "target": decisions[1]["decision_id"],
         "kind": "cites", "direction": "forward", "confidence": 0.9, "evidence": "x",
         "mention_count": 1, "seed_decision_id": decisions[0]["decision_id"]},
    ]
    return {
        "query": "Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung",
        "decisions": decisions,
        "clusters": clusters,
        "relations": relations,
        "provenance": {"mode": "test", "fixture_mode": True},
    }
