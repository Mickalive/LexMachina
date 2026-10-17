#!/usr/bin/env python3
"""Pin the served-packet claim-population baseline for the rebuild trigger.

WHAT THIS IS, PRECISELY
-----------------------
Direction v52 deliverable (1) makes a re-run of
``evaluation.packet_admission_conformance`` conditional on Product shipping a
NEW served packet, and calls a re-run over the byte-identical population "the
rc-67 zero-delta pathology".  Executing that condition needs a pinned baseline.

The baseline is built from TWO accepted sources, and the distinction matters:

* ``adjudicated_bundle_sha256`` - the nine bundle digests recorded by this
  lane's ACCEPTED sweep record ``39020603510_sweep.json``.  These are the bytes
  the two frozen bars were last adjudicated on.
* ``manifest`` - the FULL sha manifest of the served-packet claim population
  (every byte under ``results/product/gate_packet/`` plus
  ``state/product.json``) as it stands at the start of run 39027041693.

The trigger compares against ``manifest`` and REQUIRES the nine adjudicated
digests to still be present and byte-identical; that is the set relation that
licenses "the bars were adjudicated on these exact bytes".  It is verified by
intersection and both differences, never by matching counts.

This file is itself the pinned baseline: the next cycle compares against it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANE = Path("/home/runner/work/LexMachina/LexMachina")
sys.path.insert(0, str(LANE))
from evaluation.newhead_recompute import packet_population, set_relation  # noqa: E402

RUN_ID = "39027041693"
PRODUCT = Path("/tmp/lex_accepted/product")
OUT = LANE / "results" / "evaluation" / "newhead_recompute_39027041693"
OUT.mkdir(parents=True, exist_ok=True)

sweep = json.loads((LANE / "results/evaluation/label_lineage_gate"
                    / "39020603510_sweep.json").read_text(encoding="utf-8"))
adjudicated: dict[str, str] = {}
for row in sweep["blocking_matrix"]:
    for qid, sha in row["bundle_sha256"].items():
        adjudicated[f"results/product/gate_packet/{row['packet_id']}/questions/{qid}.bundle.json"] = sha

pop = packet_population(PRODUCT)
rel = set_relation(pop["manifest"], adjudicated)

payload = {
    "schema": "lex-evaluation-served-packet-baseline/1",
    "pinned_for_run_id": RUN_ID,
    "pinned_at_utc": "2026-10-17",
    "product_head": "cc719eebf accept product cycle 39019268074",
    "root": pop["root"],
    "definition": (
        "Every byte under results/product/gate_packet/ plus state/product.json. "
        "A rebuild that changes a bundle without renaming the packet directory is "
        "still a new packet; only a byte manifest can tell the two apart."),
    "n_files": pop["n_files"],
    "n_packet_dirs": pop["packet_dirs"],
    "manifest": pop["manifest"],
    "adjudicated_bundle_sha256": adjudicated,
    "adjudicated_source": (
        "results/evaluation/label_lineage_gate/39020603510_sweep.json (accepted; the "
        "last adjudication of the two frozen bars over the served lineage)"),
    "adjudication_set_relation_at_pin_time": {
        "n_adjudicated": len(adjudicated),
        "n_present_byte_identical": rel["n_byte_identical"],
        "n_changed": rel["n_changed"],
        "added": rel["added"],
        "removed": rel["removed"],
        "all_adjudicated_bundles_still_byte_identical": (
            rel["n_byte_identical"] == len(adjudicated) and not rel["changed"]
            and not rel["removed"]),
        "note": (
            "'added' here means present in the CURRENT manifest but not among the nine "
            "adjudicated digests; those are files of the served tree that the accepted "
            "sweep never needed to score, not evidence of a rebuild. The rebuild test is "
            "the full-manifest comparison, reported separately."),
    },
    "trigger_use": (
        "python -m evaluation.newhead_recompute --mode trigger --baseline-manifest "
        f"results/evaluation/newhead_recompute_{RUN_ID}/served_packet_baseline_{RUN_ID}.json"),
    "claim_ceiling": (
        "A baseline pin is provenance, not a verdict. It authorises NO re-run: it is "
        "the reference against which the next Product head is compared."),
}
path = OUT / f"served_packet_baseline_{RUN_ID}.json"
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in payload.items()
                  if k not in ("manifest", "adjudicated_bundle_sha256")}, indent=2))
print(f"wrote {path}")