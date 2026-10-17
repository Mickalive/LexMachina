"""Independent serve/do-not-serve audit of the REBUILT packet (charter v3).

This package consumes the rebuilt packet
(results/product/gate_packet/rebuilt-39027045675, packet.json raw sha256
2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170) and applies
the two accepted frozen rules BYTE-IDENTICALLY from the vendored accepted
frozen_bars instruments, reusing the accepted verdict contract rather than
re-deriving it. It emits ONE machine-checked serve recommendation.
"""
__version__ = "1.0.0"
TEAM_ID = "frontier-rebuilt-packet-serve-audit"
CHARTER_VERSION = 3
