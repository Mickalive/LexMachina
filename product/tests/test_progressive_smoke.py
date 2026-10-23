"""The shipped progressive query API must work end-to-end through a real socket.

Why this exists
---------------
Producer snapshot 39905155175 (commit 845171a) claimed it fixed the progressive
endpoints in ``product/server.py`` (``/api/query/start``, ``/api/query/expand``,
``/api/query/enrich``, ``/api/query/status``, ``/api/query/bundle``) and put the
claim in ``state/product.json`` - but the claim shipped with no artifact that
exercises exactly those endpoints through the shipped launch command, and the
run's independent audit died (exit 2, gate file absent) without recomputing it.

``product/progressive_smoke.py`` is that artifact: it boots
``python3 product/server.py <port> --query-mode`` as a real subprocess and
drives start -> status -> expand -> enrich -> bundle -> static assets over a
real socket in fixture mode.  This test keeps the smoke inside the frozen
suite so the claim cannot drift again without a red test.

It is offline and deterministic: fixture retrieval replays from the local
query cache, generation uses the fixture provider, no network, no paid
inference, no gate-readiness claim.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.progressive_smoke import run as progressive_run  # noqa: E402


def test_progressive_api_answers_end_to_end_over_a_real_socket():
    record = progressive_run("pytest")
    failed = [c for c in record["checks"] if not c["ok"]]
    assert record["verdict"] == "PASS", (
        "the shipped progressive query API must pass its real-socket smoke; "
        f"failures={[f['check'] + ': ' + str(f['detail']) for f in failed]}"
    )
    assert record["checks_passed"] == record["checks_total"], record
    # the headline numbers the state claims, re-derived here
    assert record["timings_s"]["server_boot_s"] < 60, record["timings_s"]
    assert record["timings_s"]["start_s"] < 120, record["timings_s"]


def test_the_smoke_artifact_schema_is_stable():
    record = progressive_run("pytest-schema")
    assert record["schema"] == "product-progressive-smoke/1"
    assert record["mode"].startswith("fixture")
    assert "claim_ceiling" in record and record["claim_ceiling"]
    names = {c["check"] for c in record["checks"]}
    for required in ("health_query_mode", "start_returns_run_id",
                     "answer_status_ready", "counter_status_rows_present",
                     "cluster_labels_present", "bundle_endpoint_returns_bundle"):
        assert required in names, f"missing smoke check: {required}"
