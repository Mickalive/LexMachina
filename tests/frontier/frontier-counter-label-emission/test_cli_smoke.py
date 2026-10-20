"""CLI smoke test (acceptance test 2: runnable `python -m ...cli --packet`)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import PACKET, TEAM_ROOT, requires_accepted


@requires_accepted
def test_cli_smoke(tmp_path: Path):
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, "-m", "frontier_counter_label_emission.cli",
            "--packet", str(PACKET),
            "--out", str(out),
            "--determinism-runs", "1",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(Path(__file__).resolve().parents[3]),
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(TEAM_ROOT),
        },
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    for name in (
        "ATTRIBUTION.json", "EMISSION.json", "DETERMINISM.json",
        "NON_VACUITY.json", "MEASUREMENT_SUMMARY.json", "ARTIFACT_DIGESTS.json",
    ):
        assert (out / name).is_file(), f"missing {name}"
    summary = json.loads((out / "MEASUREMENT_SUMMARY.json").read_text(encoding="utf-8"))
    assert summary["input_hash_verification"]["ok"] is True
    assert summary["classifier_config_byte_identical_after"] is True
    stdout = json.loads(proc.stdout)
    assert stdout["input_hashes_ok"] is True
    assert stdout["classifier_ok_before"] is True
    assert stdout["classifier_ok_after"] is True
    # Emission before is zero-scored on all three; after is >0 on at least one.
    before_scores = [v["n_scored"] for v in stdout["emission_before"].values()]
    after_scores = [v["n_scored"] for v in stdout["emission_after"].values()]
    assert all(s == 0 for s in before_scores)
    assert any(s > 0 for s in after_scores)
