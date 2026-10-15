"""Tests for the human-gate evidence admissibility scanner.

`product/human_gate_evidence.py` exists because the human-gate evidence
directories must be checkable by an auditor running one command, not by reading
prose. Cycle 38726191935 committed five pytest byproducts into
`results/product/human_gate_sessions_simulated/`, two of which carried
`simulated: true` next to the claim ceiling *"this record documents one
owner/jurist session"*. These tests freeze the scanner's verdict on that exact
shape — and on the preserved copy of it in
`reports/product/incidents/pytest_byproducts_human_gate_sessions_38726191935.RETIRED.json`,
so the pathology stays detectable as negative evidence.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
INCIDENT = (
    REPO_ROOT
    / "reports"
    / "product"
    / "incidents"
    / "pytest_byproducts_human_gate_sessions_38726191935.RETIRED.json"
)

if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

from human_gate_evidence import (  # noqa: E402
    CANONICAL_DIR,
    SIMULATED_DIR,
    main,
    scan,
    scan_record,
)


def codes(findings) -> set[str]:
    return {finding["code"] for finding in findings}


def simulated_record(**overrides) -> dict:
    record = {
        "record_type": "lex_human_gate_session",
        "session_id": "owner-2026-10-20T120000Z",
        "simulated": True,
        "status": "finalized",
        "claim_ceiling": "SIMULATED SESSION: machine-generated; not an owner/jurist session.",
        "finalized_by": None,
        "run_id": None,
        "session_metrics": {"wall_clock_seconds": 12.0},
        "bundle_hash_status": "verified",
        "bundle_evidence": {"bundle_supplied": True, "bundle_decision_count": 120},
    }
    record.update(overrides)
    return record


def real_record(**overrides) -> dict:
    record = {
        "record_type": "lex_human_gate_session",
        "session_id": "owner-2026-10-20T120000Z",
        "simulated": False,
        "status": "finalized",
        "claim_ceiling": (
            "human gate EVIDENCE only: this record documents one owner/jurist session. "
            "human_gate_ready is set by the director from these records, never by this tool."
        ),
        "finalized_by": "owner",
        "run_id": "38732097101",
        "owner_session_confirmed": True,
        "session_metrics": {"wall_clock_seconds": 612.0},
        "bundle_hash_status": "verified",
        "bundle_evidence": {"bundle_supplied": True, "bundle_decision_count": 180},
    }
    record.update(overrides)
    return record


def write(directory: Path, name: str, record: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# the committed tree
# --------------------------------------------------------------------------


def test_repository_evidence_tree_is_admissible() -> None:
    report = scan()
    assert report["blocking_count"] == 0, report["findings"]
    assert report["admissible"] is True


def test_scanner_cli_exits_zero_on_the_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(PRODUCT_ROOT / "human_gate_evidence.py")],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ADMISSIBLE" in result.stdout


# --------------------------------------------------------------------------
# the defect classes the scanner must catch
# --------------------------------------------------------------------------


def test_simulated_record_claiming_to_be_an_owner_session_is_blocking() -> None:
    """The exact pathology: simulated=true next to the real claim ceiling."""
    record = simulated_record(
        claim_ceiling=(
            "human gate EVIDENCE only: this record documents one owner/jurist session. "
            "human_gate_ready is set by the director from these records, never by this tool."
        )
    )
    findings = scan_record(record, directory=SIMULATED_DIR, source="session_x.json")
    assert "contradictory_claim_ceiling" in codes(findings)
    assert findings[0]["severity"] == "blocking"


def test_the_preserved_incident_record_is_still_detected_as_a_defect() -> None:
    """The five retired pytest byproducts stay provable non-evidence, not evidence.

    Two of them carried the false "documents one owner/jurist session" ceiling and
    must still be caught; the other three were structurally honest, which is why
    the audit's complaint about them is provenance (they are pytest scratch in
    results/), not self-contradiction. The incident file states the verdict for
    all five explicitly.
    """
    incident = json.loads(INCIDENT.read_text(encoding="utf-8"))
    preserved = incident["records"]
    assert len(preserved) >= 5
    assert incident["status"] == "RETIRED"
    assert incident["admissibility_of_these_records"].startswith("NONE")
    assert all(entry["file"].startswith("session_session-") for entry in preserved)

    contradictory = [
        entry for entry in preserved
        if "contradictory_claim_ceiling" in codes(
            scan_record(entry["record"], directory=SIMULATED_DIR, source=entry["file"])
        )
    ]
    assert len(contradictory) == 2, "the two self-contradictory records are the ones the audit named"
    assert all(entry["record"]["simulated"] is True for entry in contradictory)
    for entry in preserved:
        assert entry["file_sha256"], "the retired record must stay byte-reproducible in the incident file"


def test_simulated_record_in_the_canonical_directory_is_blocking(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_a.json", simulated_record(session_id="session-session-20261015T113329Z"))
    found = codes(scan([directory])["findings"])
    assert "simulated_in_canonical_dir" in found
    assert "missing_finalized_by" in found
    assert "missing_run_id" in found
    assert "test_scratch_session_id" in found


def test_real_record_filed_in_the_simulated_directory_is_blocking(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions_simulated"
    write(directory, "session_b.json", real_record())
    findings = scan([directory])["findings"]
    assert "real_record_in_simulated_dir" in codes(findings)


def test_canonical_record_without_provenance_is_blocked_on_every_axis(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(
        directory,
        "session_c.json",
        real_record(
            finalized_by=None,
            run_id=None,
            session_metrics={"wall_clock_seconds": 0.0},
            bundle_hash_status="not_verified",
            bundle_evidence={"bundle_supplied": False},
        ),
    )
    found = codes(scan([directory])["findings"])
    assert {"missing_finalized_by", "missing_run_id", "non_positive_wall_clock", "bundle_not_verified"} <= found


def test_canonical_record_without_an_owner_session_declaration_is_blocked(tmp_path: Path) -> None:
    """A rehearsal / autonomous run must not be able to file itself as gate evidence.

    This is the exact accident this cycle hit once: the one-command runner dropped
    ``--out`` and wrote a machine-authored rehearsal into the canonical directory,
    where it passed every structural rule. The declaration is what separates the two.
    """
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_rehearsal.json", real_record(owner_session_confirmed=False))
    assert "unconfirmed_owner_session" in codes(scan([directory])["findings"])
    write(directory, "session_rehearsal2.json", real_record())
    (directory / "session_rehearsal2.json").unlink()
    write(directory, "session_ok.json", real_record(owner_session_confirmed=True))
    found = codes(scan([directory])["findings"])
    assert "unconfirmed_owner_session" in found
    (directory / "session_rehearsal.json").unlink()
    assert scan([directory])["findings"] == []


def test_canonical_record_bound_to_a_fixture_sized_bundle_is_blocked(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_d.json", real_record(bundle_evidence={"bundle_supplied": True, "bundle_decision_count": 2}))
    assert "implausible_decision_count" in codes(scan([directory])["findings"])


def test_record_that_claims_the_gate_passed_is_blocked(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_e.json", real_record(human_gate_ready=True))
    assert "claims_human_gate_ready" in codes(scan([directory])["findings"])


def test_a_clean_real_session_in_the_canonical_directory_is_admissible(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_f.json", real_record())
    assert scan([directory])["findings"] == []


def test_unreadable_record_is_reported_not_crashed(tmp_path: Path) -> None:
    directory = tmp_path / "human_gate_sessions"
    directory.mkdir(parents=True)
    (directory / "session_broken.json").write_text("{not json", encoding="utf-8")
    assert "unreadable_record" in codes(scan([directory])["findings"])


def test_cli_returns_one_when_a_directory_has_a_defect(tmp_path: Path, capsys) -> None:
    directory = tmp_path / "human_gate_sessions"
    write(directory, "session_g.json", simulated_record())
    assert main(["--dir", str(directory)]) == 1
    assert "NOT ADMISSIBLE" in capsys.readouterr().out
    assert main(["--dir", str(SIMULATED_DIR), "--quiet"]) == 0


def test_scanner_paths_are_the_repository_evidence_directories() -> None:
    assert CANONICAL_DIR.name == "human_gate_sessions"
    assert SIMULATED_DIR.name == "human_gate_sessions_simulated"
    assert CANONICAL_DIR.is_relative_to(REPO_ROOT / "results" / "product")
    assert SIMULATED_DIR.is_relative_to(REPO_ROOT / "results" / "product")