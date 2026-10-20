#!/usr/bin/env python3
"""Charter-entry CLI: python -m frontier_packet_serve_audit.cli --packet <dir> --frozen-rules <dir>

Thin dispatcher to the canonical serve-audit harness (the accepted,
machine-checked package at frontier/frontier-packet-serve-audit/
frontier_packet_serve_audit/). The previous in-file draft was retired
during the operational resume of run 39365348585: its non-vacuity control
asserted criteria movement without running the frozen seeded controls.
This wrapper exists so the charter's literal invocation from the repo root
runs the canonical harness and nothing else.

Because the canonical package shares this package's import name, the wrapper
evicts the partially-initialized root package from sys.modules before
importing the canonical copy from the team directory; the canonical
package's internal absolute imports then resolve to itself.

Offline, deterministic, stdlib only. No network, no paid API, no product
import, no writes outside the caller-designated output path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CANONICAL = Path(__file__).resolve().parent.parent / "frontier" / "frontier-packet-serve-audit"


def _load_canonical_main():
    if not _CANONICAL.is_dir():
        raise RuntimeError(f"canonical harness not found at {_CANONICAL}")
    for name in [m for m in sys.modules
                 if m == "frontier_packet_serve_audit" or m.startswith("frontier_packet_serve_audit.")]:
        del sys.modules[name]
    if str(_CANONICAL) not in sys.path:
        sys.path.insert(0, str(_CANONICAL))
    import frontier_packet_serve_audit.cli as canonical_cli
    return canonical_cli.main


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    canonical_main = _load_canonical_main()
    # Translate the charter's --output spelling to the canonical --out.
    translated = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a == "--output" and i + 1 < len(argv):
            translated.extend(["--out", argv[i + 1]])
            skip = True
        else:
            translated.append(a)
    return canonical_main(translated)


if __name__ == "__main__":
    raise SystemExit(main())
