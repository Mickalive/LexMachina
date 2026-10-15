"""Live progressive-slice smoke: real OpenCaseLaw -> real model -> clickable map.

    python product/slice_smoke.py --run-id CYCLE_38665681083 --port 8797

Drives the *shipped* product server the way the browser does (no pipeline
shortcuts, no fixtures) and records, as evidence:

* how long the first page of the map takes (the number the owner waits before
  seeing anything);
* how long the background expansion and the answer/counter-authority job take;
* that the server keeps answering while those jobs run;
* the final bundle itself, so the human-gate session can be reproduced from it.

Everything is written to ``results/product/progressive_slice/<run>.json``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "results" / "product" / "progressive_slice"

DEFAULT_QUERY = "Responsabilite penale de l'entreprise selon l'art. 102 CP"


class Client:
    def __init__(self, base: str):
        self.base = base

    def get(self, path: str, timeout: float = 900.0):
        t0 = time.time()
        try:
            with urllib.request.urlopen(self.base + path, timeout=timeout) as resp:
                payload = json.loads(resp.read())
                code = resp.status
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read() or b"{}")
            code = exc.code
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            # The server needs a few seconds to import the numeric stack; the
            # readiness loop must not treat that as a failure.
            return 0, {"error": str(exc)}, round(time.time() - t0, 3)
        return code, payload, round(time.time() - t0, 3)

    def wait_job(self, run_id: str, name: str, *, on_poll=None, limit: float = 1800.0):
        deadline = time.time() + limit
        polls = 0
        while time.time() < deadline:
            _code, st, _s = self.get("/api/query/status?run_id=" + run_id)
            polls += 1
            job = (st.get("jobs") or {}).get(name) or {}
            if on_poll:
                on_poll(st, job)
            if job.get("status") in {"done", "error"}:
                return st, job, polls
            time.sleep(2.0)
        raise TimeoutError(f"job {name} did not finish in {limit}s")


def health_probe(base: str, stop: threading.Event, out: list) -> None:
    client = Client(base)
    while not stop.is_set():
        code, payload, secs = client.get("/api/health", timeout=10)
        out.append({"ok": payload.get("ok"), "status": code, "seconds": secs})
        stop.wait(1.0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="manual")
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--fixture", action="store_true")
    ap.add_argument("--timeout", type=float, default=1800.0)
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{args.run_id}.json"

    server = subprocess.Popen(
        [sys.executable, str(PRODUCT_ROOT / "query_app.py"), "--host", args.host,
         "--port", str(args.port), "--quiet"] + (["--fixture"] if args.fixture else []),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://{args.host}:{args.port}"
    client = Client(base)
    stop = threading.Event()
    probes: list = []
    report: dict = {"run_id": args.run_id, "query": args.query, "n": args.n,
                    "mode": "fixture" if args.fixture else "live", "stages": {}}
    try:
        for _ in range(100):
            code, payload, _s = client.get("/api/health", timeout=3)
            if code == 200 and payload.get("ok"):
                break
            time.sleep(0.2)
        else:  # pragma: no cover
            raise RuntimeError("server did not become healthy")

        threading.Thread(target=health_probe, args=(base, stop, probes), daemon=True).start()

        t_wall = time.time()
        code, first, secs = client.get(
            "/api/query/start?" + urllib.parse.urlencode({"q": args.query, "n": args.n}))
        if code != 200:
            raise RuntimeError(f"start failed: {first}")
        run_id = first["run_id"]
        timing0 = first["bundle"]["provenance"]["timing"]
        report["stages"]["first_page"] = {
            "http_seconds": secs,
            "wall_seconds": round(time.time() - t_wall, 3),
            "decisions": len(first["bundle"]["decisions"]),
            "clusters": len(first["bundle"]["clusters"]),
            "upstream_retrieval_s": timing0.get("upstream_retrieval_s"),
            "local_map_s": timing0.get("local_map_s"),
            "phase": first["bundle"]["provenance"]["phase"],
            "expand_job_started": first.get("expand_started"),
        }
        print(json.dumps(report["stages"]["first_page"], indent=2), flush=True)

        # The map is interactive here; expansion continues in the background.
        _st, expand_job, expand_polls = client.wait_job(run_id, "expand", limit=args.timeout)
        _code, expanded, _s = client.get("/api/query/bundle?run_id=" + run_id)
        prog = expanded["bundle"]["provenance"]["progressive"]
        report["stages"]["expand"] = {
            "status": expand_job["status"],
            "seconds": expand_job.get("elapsed_s"),
            "polls": expand_polls,
            "decisions_after": len(expanded["bundle"]["decisions"]),
            "n_added": prog.get("n_added"),
            "points_moved": prog.get("points_moved"),
            "expand_upstream_s": expanded["bundle"]["provenance"]["timing"].get("expand_upstream_s"),
            "expand_local_s": expanded["bundle"]["provenance"]["timing"].get("expand_local_s"),
        }
        print(json.dumps(report["stages"]["expand"], indent=2), flush=True)

        _code, ack, ack_s = client.get("/api/query/enrich?run_id=" + run_id)
        report["stages"]["enrich_ack"] = {"http_status": _code, "ack_seconds": ack_s,
                                          "deduplicated": ack.get("deduplicated")}
        _st, enrich_job, enrich_polls = client.wait_job(run_id, "enrich", limit=args.timeout)
        _code, final, _s = client.get("/api/query/bundle?run_id=" + run_id)
        bundle = final["bundle"]
        tfin = bundle["provenance"]["timing"]
        report["stages"]["enrich"] = {
            "status": enrich_job["status"],
            "seconds": enrich_job.get("elapsed_s"),
            "polls": enrich_polls,
            "answer_status": bundle["answer"]["status"],
            "method": bundle["answer"]["method"],
            "model": bundle["answer"]["model"],
            "cited": len(bundle["answer"].get("cited_decision_ids") or []),
            "counter": sum(1 for d in bundle["decisions"]
                           if d.get("counter_status") not in (None, "", "none")),
            "enrich_total_s": tfin.get("enrich_total_s"),
            "enrich_model_s": tfin.get("enrich_model_s"),
            "enrich_non_model_s": tfin.get("enrich_non_model_s"),
        }
        print(json.dumps(report["stages"]["enrich"], indent=2), flush=True)

        geo0 = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"])
                for d in first["bundle"]["decisions"]}
        geo1 = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"])
                for d in bundle["decisions"] if d["decision_id"] in geo0}
        failures = [p for p in probes if not p.get("ok")]
        report["map_stability"] = {
            "points_checked": len(geo0),
            "moved": sum(1 for k, v in geo0.items() if geo1.get(k) != v),
        }
        report["server_responsiveness"] = {
            "probes": len(probes),
            "failures": len(failures),
            "max_seconds": max((p["seconds"] for p in probes), default=None),
            "p95_seconds": (sorted(p["seconds"] for p in probes)[int(0.95 * (len(probes) - 1))]
                            if probes else None),
        }
        report["provenance"] = {
            "retrieval": bundle["provenance"]["retrieval"],
            "generative_audit": bundle["provenance"].get("generative_audit"),
            "product_audit_seam": bundle["provenance"].get("product_audit_seam"),
            "progressive": bundle["provenance"]["progressive"],
            "timing": tfin,
        }
        report["bundle_path"] = str(OUT_DIR / f"bundle_{args.run_id}.json")
        # The bundle is written next to the report rather than inlined twice:
        # the human-gate session can be reproduced from it directly.
        (OUT_DIR / f"bundle_{args.run_id}.json").write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        report["budget"] = {
            "first_map_visible_under_10s": secs < 10.0,
            "first_map_visible_under_30s": secs < 30.0,
            "local_map_overhead_under_1_5s": (timing0.get("local_map_s") or 0) < 1.5,
            "cached_or_warm_total_local_under_2s": (
                (timing0.get("local_map_s") or 0)
                + (bundle["provenance"]["timing"].get("expand_local_s") or 0) < 2.0
            ),
            "server_unresponsive_probes": len(failures),
            "points_moved_after_first_map": report["map_stability"]["moved"],
        }
        report["ok"] = bool(
            report["budget"]["first_map_visible_under_30s"]
            and report["budget"]["local_map_overhead_under_1_5s"]
            and report["map_stability"]["moved"] == 0
            and len(failures) == 0
            and bundle["answer"]["status"] in {"ready", "degraded"}
        )
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["ok"] = False
    finally:
        stop.set()
        time.sleep(0.2)
        server.terminate()
        try:
            log, _ = server.communicate(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover
            server.kill()
            log, _ = server.communicate()
        report["server_log_tail"] = (log or "")[-2000:]

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "bundle"}
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"written: {out_path}", flush=True)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())