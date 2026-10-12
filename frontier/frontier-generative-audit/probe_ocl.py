#!/usr/bin/env python3
"""Live OpenCaseLaw reachability / method probe.

Re-runs the exact probes that disprove the cycle-38176699303 negative
("CI sandbox has no egress to opencaselaw.org") and records the correct
host + methods for the source-validation path.

Usage::

    python3 frontier/frontier-generative-audit/probe_ocl.py \
        --out results/frontier/frontier-generative-audit/ocl_live_probe.json

Probe set (all against ``https://mcp.opencaselaw.ch/api``):

* ``GET  /openapi.json``                 — API identity (OpenCaseLaw API 1.0.0)
* ``GET  /decisions?query=…&limit=1``    — search
* ``GET  /decisions/{real_id}``          — decision existence
* ``GET  /integrity/{real_id}``          — RFC-6962 inclusion proof
* ``POST /attest``                       — draft audit (draft_text + audit_quotes)
* ``POST /verify-claim``                 — claim-support judge
* ``GET  https://opencaselaw.org/api/attest`` — the retired WRONG host (expected to fail)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

DEFAULT_BASE = "https://mcp.opencaselaw.ch/api"
RETIRED_BASE = "https://opencaselaw.org/api"
PROBE_DECISION_ID = "bge_BGE_89_II_126"


def _get(url: str, timeout: float) -> Tuple[Any, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "LexMachina-GenAudit-probe",
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return exc.code, {"_raw": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return None, {"_exception": repr(exc)}


def _post(url: str, payload: Dict[str, Any], timeout: float) -> Tuple[Any, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "LexMachina-GenAudit-probe"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return exc.code, {"_raw": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return None, {"_exception": repr(exc)}


def _summarise(status: Any, body: Any, keys: tuple = ()) -> Dict[str, Any]:
    out: Dict[str, Any] = {"http_status": status}
    if isinstance(body, dict):
        out["reachable"] = status is not None and 200 <= int(status) < 300
        for key in keys:
            if key in body:
                value = body[key]
                out[key] = value if not isinstance(value, str) else value[:200]
        if "_exception" in body:
            out["_exception"] = body["_exception"]
        if "detail" in body:
            out["detail"] = str(body["detail"])[:200]
        if "error" in body:
            out["error"] = str(body["error"])[:200]
    else:
        out["reachable"] = False
    return out


def run_probe(base: str = DEFAULT_BASE, timeout: float = 30.0) -> Dict[str, Any]:
    probes: Dict[str, Any] = {}

    status, body = _get(f"{base}/openapi.json", timeout)
    info = body.get("info", {}) if isinstance(body, dict) else {}
    probes["openapi"] = _summarise(status, body, ("title", "version"))
    probes["openapi"]["api_title"] = info.get("title")
    probes["openapi"]["api_version"] = info.get("version")

    status, body = _get(f"{base}/decisions?query=Konkurrenzklausel&limit=1&full_text=false", timeout)
    summary = _summarise(status, body, ("total", "returned"))
    if isinstance(body, dict) and body.get("results"):
        summary["first_decision_id"] = body["results"][0].get("decision_id")
        summary["first_docket_number"] = body["results"][0].get("docket_number")
    probes["search"] = summary

    status, body = _get(f"{base}/decisions/{PROBE_DECISION_ID}?full_text=false", timeout)
    probes["decision_exists"] = _summarise(status, body, ("decision_id", "docket_number", "court"))

    status, body = _get(f"{base}/integrity/{PROBE_DECISION_ID}", timeout)
    probes["integrity_proof"] = _summarise(status, body, ("decision_id", "root", "algorithm",
                                                          "leaf_hash", "leaf_index"))

    status, body = _post(
        f"{base}/attest",
        {"draft_text": f"Laut {PROBE_DECISION_ID} ist ein Konkurrenzverbot auslegungsbedürftig.",
         "audit_quotes": True},
        timeout,
    )
    probes["attest_post"] = _summarise(status, body, ("ok", "citations_found", "citations_ok",
                                                      "issues_count"))
    probes["attest_post"]["note"] = "POST-only route; a GET against it is method-mismatched"

    status, body = _post(
        f"{base}/verify-claim",
        {"claim": "Ein Konkurrenzverbot in einem Werklieferungsvertrag ist auslegungsbedürftig.",
         "decision_id": PROBE_DECISION_ID},
        timeout,
    )
    probes["verify_claim"] = _summarise(status, body, ("supports", "confidence", "decision_id",
                                                       "checked_text_source", "canonical_url"))

    # The retired host from cycle 38176699303: expected to fail (wrong host).
    status, body = _get(f"{RETIRED_BASE}/attest", timeout)
    probes["retired_wrong_host"] = _summarise(status, body)
    probes["retired_wrong_host"]["note"] = (
        "https://opencaselaw.org is NOT the API host (TLS handshake fails, curl rc=35); "
        "kept only as the audited negative that cycle 38181577763 repaired"
    )

    live_keys = ("openapi", "search", "decision_exists", "integrity_proof", "attest_post", "verify_claim")
    reachable = all(probes[k].get("reachable") for k in live_keys)
    return {
        "probe": "opencaselaw-live-reachability",
        "base": base,
        "probed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "probes": probes,
        "live_host_reachable": reachable,
        "retired_host_reachable": probes["retired_wrong_host"].get("reachable"),
        "conclusion": (
            "The documented OpenCaseLaw API host is reachable from this sandbox; "
            "the prior 'no egress to opencaselaw.org' negative was misattributed "
            "(wrong host + GET against a POST-only route)."
            if reachable and not probes["retired_wrong_host"].get("reachable")
            else "Unexpected probe outcome — inspect per-route results."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    report = run_probe(args.base, args.timeout)
    print(json.dumps({k: v for k, v in report.items() if k != "probes"}, indent=2))
    for name, probe in report["probes"].items():
        print(f"  {name:22} http={probe.get('http_status')} reachable={probe.get('reachable')}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"wrote {args.out}")
    return 0 if report["live_host_reachable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
