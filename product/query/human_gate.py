"""Product-side adapter for the accepted human-gate list<->map switch.

Why this module exists
----------------------
The Master Prompt's human product gate is comparative: *answer + map* versus the
conventional *answer + ranked list*.  Until this cycle the clickable slice had no
conventional baseline at all, so the owner could not answer the gate.  The
accepted team ``frontier-human-gate-harness`` ships that baseline (rank, court,
date, language, citation, snippet, source link — no cluster colour, no
proximity, no counter grouping) and declares in
``INTEGRATION_CONTRACT.json`` that ``product_owns_final_integration: true``.

Product therefore *adopts* the assets rather than reimplementing them:

* ``product/static/lex_gate_switch.js``  — sha256 ``38d4b20f...``
* ``product/static/lex_gate_switch.css`` — sha256 ``1a8cf486...``

The digests are pinned here from the accepted contract so the adoption stays
verifiable offline, with no dependency on the peer mount still being present.
This is the same reuse discipline the retrieval and generative-audit seams
follow: a narrow adapter in front of an accepted component, never a fork.

What the switch does and does not do to the product
---------------------------------------------------
* ``getBundle()`` returns the already-loaded ``query_result_bundle`` object the
  map just drew.  The switch has no HTTP client, so a view change can never
  re-retrieve and cannot silently mix a second result set into a gate session.
* The switch writes ``#status`` while applying visibility.  Product registers a
  listener *after* ``attach()`` so the product's own status (phase pill, result
  count, latency) is re-applied immediately afterwards — the harness owns the
  click, product owns the wording.
* ``human_gate_ready`` is never written here.  This module can make the gate
  *answerable*; only a real owner/jurist session can make it *passed*.

Usage
-----
    python -m product.query.human_gate --verify      # human-readable report
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PRODUCT_ROOT.parent
STATIC_DIR = PRODUCT_ROOT / "static"
QUERY_HTML = STATIC_DIR / "query.html"

TEAM_ID = "frontier-human-gate-harness"

#: Accepted artifacts, pinned by digest from the team's INTEGRATION_CONTRACT.json.
ACCEPTED_ASSETS: dict[str, dict[str, Any]] = {
    "lex_gate_switch.js": {
        "sha256": "38d4b20fd08b68ac1fc76753fd080a3f67dfbdf908641134bbd7857ac2e3aaa3",
        "repo_source": f"frontier/{TEAM_ID}/static/lex_gate_switch.js",
        "provides": ["list<->map switch", "capture draft export"],
    },
    "lex_gate_switch.css": {
        "sha256": "1a8cf48683ae80c673f00ba4747ff4312f4ad8b6faeef8fcfb8dd79ba6ff3a21",
        "repo_source": f"frontier/{TEAM_ID}/static/lex_gate_switch.css",
        "provides": ["baseline row styling", "toggle styling"],
    },
}

#: Where the peer repository may be mounted during a cycle.  Absent mounts are
#: fine: the pinned digests above are the durable contract.
ACCEPTED_MOUNT_CANDIDATES = (
    Path("/tmp/lex_accepted") / "frontier" / TEAM_ID / "frontier" / TEAM_ID / "static",
    REPO_ROOT / "frontier" / TEAM_ID / "static",
)

#: The hooks the product page implements (INTEGRATION_CONTRACT.json "hooks").
REQUIRED_HTML_HOOKS: dict[str, str] = {
    "list_element": 'id="lexListView"',
    "script_asset": '/static/lex_gate_switch.js',
    "style_asset": '/static/lex_gate_switch.css',
    "attach_call": "LexGateSwitch.attach({",
    "bundle_hook": "getBundle:function(){return BUNDLE}",
    "map_element": 'document.getElementById("mapWrap")',
    "toolbar_host": 'document.getElementById("toolbar")',
    "bundle_changed": "LexGateSwitch.notifyBundleChanged()",
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def accepted_source_dir() -> Path | None:
    for candidate in ACCEPTED_MOUNT_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return None


def installed_path(name: str) -> Path:
    return STATIC_DIR / name


def verify_assets() -> dict:
    """Check every adopted asset against its accepted digest.

    Returns a machine-readable report; never raises, so a partially installed
    switch shows up as ``ok: false`` rather than crashing the server.
    """
    source_dir = accepted_source_dir()
    assets: dict[str, dict] = {}
    for name, spec in ACCEPTED_ASSETS.items():
        path = installed_path(name)
        present = path.is_file()
        digest = sha256_of(path) if present else None
        upstream = (source_dir / name) if source_dir else None
        upstream_present = bool(upstream and upstream.is_file())
        upstream_digest = sha256_of(upstream) if upstream_present else None
        assets[name] = {
            "installed_path": str(path),
            "present": present,
            "sha256": digest,
            "expected_sha256": spec["sha256"],
            "digest_matches": digest == spec["sha256"],
            "accepted_source": str(upstream) if upstream else None,
            "accepted_source_present": upstream_present,
            "byte_identical_to_accepted": (
                upstream_digest == digest if upstream_present else None
            ),
            "repo_source": spec["repo_source"],
            "provides": spec["provides"],
        }
    ok = all(a["digest_matches"] for a in assets.values())
    return {"team_id": TEAM_ID, "ok": ok, "assets": assets,
            "accepted_mount": str(source_dir) if source_dir else None}


def verify_html_hooks() -> dict:
    """Check that product/static/query.html implements the accepted hooks."""
    html = QUERY_HTML.read_text(encoding="utf-8") if QUERY_HTML.is_file() else ""
    hooks = {name: (needle in html) for name, needle in REQUIRED_HTML_HOOKS.items()}
    return {
        "ok": all(hooks.values()),
        "html": str(QUERY_HTML),
        "hooks": hooks,
        "missing": sorted(name for name, present in hooks.items() if not present),
    }


def integration_report() -> dict:
    """Full adoption report used by tests, cycle reports and lane state."""
    assets = verify_assets()
    html = verify_html_hooks()
    return {
        "schema": "product-human-gate-integration/1",
        "team_id": TEAM_ID,
        "assets_ok": assets["ok"],
        "html_hooks_ok": html["ok"],
        "ok": assets["ok"] and html["ok"],
        "assets": assets["assets"],
        "html_hooks": html["hooks"],
        "accepted_mount": assets["accepted_mount"],
        "ownership": "product owns final integration; the team keeps its own files",
        "claim_ceiling": (
            "The switch makes the comparative human gate answerable in one sitting from the "
            "same bundle. It does not answer the gate: only a real owner/jurist session can "
            "set human_gate_ready."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verify the adopted human-gate switch assets")
    ap.add_argument("--verify", action="store_true", help="kept for symmetry; verification is default")
    args = ap.parse_args(argv)
    print(json.dumps(integration_report(), indent=2, ensure_ascii=False))
    return 0 if integration_report()["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())