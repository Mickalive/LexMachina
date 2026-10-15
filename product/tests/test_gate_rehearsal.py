"""Tests for the committed gate-rehearsal chain (product/gate_rehearsal.py).

Direction v51 delta 1 is *"finalize an exported session draft into
results/product/ via the accepted CLI"*, and two consecutive audits named the
same next step: exercise the chain against a run end to end. Until this
artifact existed, the export half was produced by an ad-hoc harness nobody could
reproduce, so the chain

    query -> progressive bundle -> REAL query.html in a real DOM ->
    accepted switch -> "Exporter la session" -> accepted finalizer ->
    evidence scanner

was never asserted as one runnable command. These tests freeze it:

1. the driver walks the owner card through the real page and carries the
   answer card into the draft (and fails loudly, exit 3, when that wiring is
   removed — a copy is mutated, never the shared page);
2. without answers the draft reports all four questions missing — the chain
   records `incomplete` instead of inventing an opinion;
3. the one-command rehearsal default is offline (no network without ``--live``)
   and its fixture run lands an ADMISSIBLE simulated record whose answers came
   from the page, with `owner_session_confirmed: false` and no
   `human_gate_ready` field anywhere.

Everything here is offline and zero-cost; the live rehearsal is a separate
human-visible run, never part of the unit suite.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

import gate_rehearsal  # noqa: E402
import human_gate_finalize as hgf  # noqa: E402

QUERY_HTML = PRODUCT_ROOT / "static" / "query.html"
SWITCH_JS = PRODUCT_ROOT / "static" / "lex_gate_switch.js"
DRIVER = PRODUCT_ROOT / "export_session_draft.js"

NODE = shutil.which("node")
QUERY = "Kündigung Mietvertrag Mietrecht"

needs_node = pytest.mark.skipif(NODE is None, reason="node runtime unavailable")


def _has_gate_key(node) -> bool:
    if isinstance(node, dict):
        return "human_gate_ready" in node or any(_has_gate_key(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_gate_key(item) for item in node)
    return False


def fixture_bundle(tmp_path: Path) -> Path:
    from query import run_query_initial

    bundle = run_query_initial(QUERY, top_n=100, retrieval_mode="fixture")
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


def answers_file(tmp_path: Path) -> Path:
    path = tmp_path / "answers.json"
    path.write_text(
        json.dumps(
            {
                "q1": {"rating": "yes", "note": "unit rehearsal answer (SIMULATED only)"},
                "q2": {"rating": "partly", "note": "unit rehearsal note"},
                "q3": {"rating": "yes", "note": ""},
                "q4": {"rating": "yes", "note": ""},
            }
        ),
        encoding="utf-8",
    )
    return path


def run_driver(*extra: str) -> subprocess.CompletedProcess:
    assert NODE is not None
    return subprocess.run(
        [NODE, str(DRIVER), *extra],
        capture_output=True, text=True, cwd=str(REPO_ROOT), check=False,
    )


# -------------------------------------------------------------------------- #
# the export half: real page -> accepted switch -> draft
# -------------------------------------------------------------------------- #
@needs_node
def test_driver_walks_the_owner_card_and_carries_the_answer_card_into_the_draft(tmp_path: Path) -> None:
    bundle_path = fixture_bundle(tmp_path)
    answers_path = answers_file(tmp_path)
    draft_path = tmp_path / "downloads" / "draft.json"

    proc = run_driver(
        "--bundle", str(bundle_path),
        "--out", str(draft_path),
        "--answers", str(answers_path),
        "--session-id", "driver-test",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads(proc.stdout)
    draft = json.loads(draft_path.read_text(encoding="utf-8"))

    # the draft comes from the accepted switch, not from the driver
    assert draft["record_type"] == "lex_human_gate_session"
    assert draft["session_id"] == "driver-test"
    assert draft["session_id_origin"] == "driver"
    assert draft["view_mode_initial"] == "map"
    assert summary["view_mode_final"] == "map", "the owner card ends back on the product map"
    assert [a["event"] for a in draft["actions"]].count("switch") == 2
    assert len(draft["decisions_opened"]) >= 3

    # the answer card, through the page's own exportDraft decoration
    assert summary["answers_supplied"] == ["q1", "q2", "q3", "q4"]
    assert summary["answers_in_draft"] == ["q1", "q2", "q3", "q4"]
    assert draft["missing_answers"] == []
    assert draft["answers"]["q1"]["rating"] == "yes"
    assert draft["answers"]["q2"]["rating"] == "partly"

    # the draft is bound to the exact bundle the page rendered
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert draft["bundle_ref"]["query"] == QUERY
    assert draft["bundle_ref"]["n_decisions"] == len(bundle["decisions"])


@needs_node
def test_driver_without_answers_records_the_missing_questions_honestly(tmp_path: Path) -> None:
    bundle_path = fixture_bundle(tmp_path)
    draft_path = tmp_path / "draft.json"

    proc = run_driver("--bundle", str(bundle_path), "--out", str(draft_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["answers"] == {}
    assert draft["missing_answers"] == ["q1", "q2", "q3", "q4"]
    # an unanswered draft is still a valid export — the finalizer, not the
    # driver, is what records it as incomplete
    assert draft["status"] == "draft"


@needs_node
def test_driver_fails_loudly_when_the_answer_card_wiring_is_broken(tmp_path: Path) -> None:
    """Non-vacuity: exit 3 must be reachable, not dead code.

    The shared page is never touched — the product directory is copied into
    ``tmp_path`` and the copy's ``draft.answers=answers;`` merge is deleted, so
    supplied answers cannot reach the export. The driver must refuse (exit 3)
    instead of writing a draft that would silently finalize as `incomplete`.
    """
    copy_root = tmp_path / "product"
    (copy_root / "static").mkdir(parents=True)
    for source in (QUERY_HTML, SWITCH_JS):
        shutil.copy2(source, copy_root / "static" / source.name)
    for source in (PRODUCT_ROOT / "dom_shim.js", DRIVER):
        shutil.copy2(source, copy_root / source.name)

    original_bytes = QUERY_HTML.read_bytes()
    before = hashlib.sha256(original_bytes).hexdigest()
    mutated_html = original_bytes.decode("utf-8")
    merge_line = "    draft.answers=answers;\n"
    assert mutated_html.count(merge_line) == 1, "the wiring line moved; update this test"
    (copy_root / "static" / "query.html").write_text(
        mutated_html.replace(merge_line, ""), encoding="utf-8"
    )

    answers_path = answers_file(tmp_path)
    bundle_path = fixture_bundle(tmp_path)
    proc = subprocess.run(
        [NODE, str(copy_root / "export_session_draft.js"),
         "--bundle", str(bundle_path),
         "--out", str(tmp_path / "draft.json"),
         "--answers", str(answers_path)],
        capture_output=True, text=True, cwd=str(tmp_path), check=False,
    )

    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "did not reach the export" in proc.stderr
    assert not (tmp_path / "draft.json").exists(), "a failed chain must not leave a draft"
    # the shared product page is byte-identical after the injection
    assert hashlib.sha256(QUERY_HTML.read_bytes()).hexdigest() == before


# -------------------------------------------------------------------------- #
# the one-command rehearsal
# -------------------------------------------------------------------------- #
def test_rehearsal_is_offline_unless_live_is_explicitly_requested() -> None:
    args = gate_rehearsal.build_parser().parse_args([])
    assert args.live is False, "the default rehearsal must not touch the network"


@needs_node
def test_fixture_rehearsal_finalizes_an_admissible_simulated_record(tmp_path: Path) -> None:
    out_dir = tmp_path / "human_gate_sessions_simulated"
    summary_path = tmp_path / "summary.json"
    answers_path = answers_file(tmp_path)

    code = gate_rehearsal.main(
        [
            "--fixture", "--quiet",
            "--run-id", "38747797021",
            "--operator", "product-test-rehearsal",
            "--work-dir", str(tmp_path / "work"),
            "--out", str(out_dir),
            "--answers", str(answers_path),
            "--session-id", "gate-rehearsal-test-fixture",
            "--summary", str(summary_path),
            "--wait-s", "60",
            "--stage-timeout-s", "60",
        ]
    )
    assert code == 0, summary_path.read_text(encoding="utf-8") if summary_path.exists() else "no summary"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    # every stage of the chain ran against the server that served the page
    assert summary["ok"] is True
    assert summary["mode"] == "fixture"
    assert summary["stages"]["start"]["decisions"] >= 100
    assert summary["stages"]["expand"]["job"] == "done"
    assert summary["stages"]["enrich"]["job"] == "done"
    assert summary["bundle"]["answer_status"] in ("ready", "degraded", None)
    assert summary["driver"]["exit_code"] == 0
    assert summary["runner"]["exit_code"] == 0

    # the record: simulated, verified, answered through the page, never a gate claim
    record_path = Path(summary["runner"]["record_path"])
    assert out_dir in record_path.parents, "a rehearsal may only write to its own --out"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["simulated"] is True
    assert record["claim_ceiling"] == hgf.CLAIM_CEILING_SIMULATED
    assert record["status"] == "finalized"
    assert record["bundle_hash_status"] == "verified"
    assert record["missing_answers"] == []
    assert set(record["answers"]) == {"q1", "q2", "q3", "q4"}
    assert record["answers"]["q1"]["rating"] == "yes"
    assert record["owner_session_confirmed"] is False
    assert record["session_metrics"]["n_decisions_opened"] >= 3
    assert not _has_gate_key(record), "the record must never carry a human_gate_ready field"

    # admissibility, judged independently of the runner's own printout
    scan = summary["evidence_scan"]
    assert scan["admissible"] is True and scan["blocking_count"] == 0
    assert str(out_dir) in " ".join(scan["scanned"])


@needs_node
def test_fixture_rehearsal_without_answers_is_recorded_as_incomplete(tmp_path: Path) -> None:
    """No answers file -> the chain still completes, honestly incomplete."""
    out_dir = tmp_path / "human_gate_sessions_simulated"
    summary_path = tmp_path / "summary.json"

    code = gate_rehearsal.main(
        [
            "--fixture", "--quiet",
            "--run-id", "38747797021",
            "--operator", "product-test-rehearsal",
            "--work-dir", str(tmp_path / "work"),
            "--out", str(out_dir),
            "--session-id", "gate-rehearsal-test-incomplete",
            "--summary", str(summary_path),
            "--wait-s", "60",
            "--stage-timeout-s", "60",
        ]
    )
    assert code == 0, summary_path.read_text(encoding="utf-8") if summary_path.exists() else "no summary"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["runner"]["exit_code"] == 3, "incomplete evidence, not a silent pass"
    record = json.loads(Path(summary["runner"]["record_path"]).read_text(encoding="utf-8"))
    assert record["status"] == "incomplete"
    assert record["answers"] == {}
    assert record["missing_answers"] == ["q1", "q2", "q3", "q4"]
    assert record["simulated"] is True
    assert record["claim_ceiling"] == hgf.CLAIM_CEILING_SIMULATED
    assert summary["evidence_scan"]["admissible"] is True
