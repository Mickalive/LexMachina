"""Freeze verification: re-hash every pinned input before any scoring."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .paths import REPO_ROOT, VENDORED_BARS

RULES_PATH = REPO_ROOT / "results" / "frontier" / "frontier-rebuilt-packet-serve-audit" / "RULES.json"

# Directories that this team is forbidden to write (proved by tests via a
# write-scope guard, not by this constant alone).
FORBIDDEN_WRITE_PREFIXES = (
    "product/",
    "evaluation/",
    "results/product/",
    "state/product.json",
    ".github/",
)


class FreezeError(RuntimeError):
    """Frozen input mismatch: environment error, never a product verdict."""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_freeze(path: Path = RULES_PATH) -> dict:
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8"))


def verify_packet_files(packet_dir: Path, freeze: dict) -> dict:
    """Re-hash every rebuilt-packet file pinned in the freeze."""
    pinned = freeze["inputs"]["rebuilt_packet"]["files"]
    observed = {}
    for rel, meta in sorted(pinned.items()):
        p = packet_dir / rel
        if not p.is_file():
            observed[rel] = {"exists": False, "matches": False}
            continue
        obs = sha256_file(p)
        observed[rel] = {
            "exists": True,
            "expected_sha256": meta["sha256"],
            "observed_sha256": obs,
            "matches": obs == meta["sha256"],
            "bytes": p.stat().st_size,
        }
    bad = [k for k, v in observed.items() if not v.get("matches")]
    if bad:
        raise FreezeError(
            f"rebuilt packet byte drift vs freeze on {bad}; refusing to score "
            "(rebind to accepted successor and re-freeze in a NEW charter if the "
            "packet was repaired)"
        )
    return observed


def verify_frozen_instruments(freeze: dict) -> dict:
    """Re-hash the vendored accepted instruments against the freeze pins."""
    pinned = freeze["inputs"]["frozen_instruments"]
    observed = {}
    for name, expected in sorted(pinned.items()):
        if name == "policy":
            continue
        p = VENDORED_BARS / name
        if not p.is_file():
            observed[name] = {"exists": False, "matches": False}
            continue
        obs = sha256_file(p)
        observed[name] = {
            "expected_sha256": expected,
            "observed_sha256": obs,
            "matches": obs == expected,
        }
    bad = [k for k, v in observed.items() if not v.get("matches")]
    if bad:
        raise FreezeError(
            f"vendored frozen instrument sha drift on {bad}; refusing to score"
        )
    return observed


def verify_old_packet_files(old_dir: Path, freeze: dict) -> dict:
    pinned = freeze["inputs"]["old_packet_before"]["files"]
    observed = {}
    for rel, meta in sorted(pinned.items()):
        p = old_dir / rel
        if not p.is_file():
            observed[rel] = {"exists": False, "matches": False}
            continue
        obs = sha256_file(p)
        observed[rel] = {
            "expected_sha256": meta["sha256"],
            "observed_sha256": obs,
            "matches": obs == meta["sha256"],
        }
    bad = [k for k, v in observed.items() if not v.get("matches")]
    if bad:
        raise FreezeError(f"old-packet byte drift vs freeze on {bad}; refusing before/after")
    return observed


def verify_all(packet_dir: Path, old_dir: Path | None, freeze: dict | None = None) -> dict:
    freeze = freeze or load_freeze()
    out = {
        "packet": verify_packet_files(packet_dir, freeze),
        "instruments": verify_frozen_instruments(freeze),
    }
    if old_dir is not None:
        out["old_packet"] = verify_old_packet_files(old_dir, freeze)
    out["all_match"] = all(
        v.get("matches")
        for section in out.values()
        if isinstance(section, dict)
        for v in section.values()
        if isinstance(v, dict)
    )
    return out
