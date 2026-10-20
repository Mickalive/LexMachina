# Integration Contract — frontier-packet-serve-audit (charter v1)

This contract names the exact artifacts Core Product and Core Evaluation must
consume. The team writes NO product file and makes NO gate-flag change.

The charter ran exactly ONE verdict cycle (HARD STOP). Run `39355384602`
produced the verdict; producer run `39359987809` suffered a state-before-artifact
write-ordering failure (stale state claim, no report artifacts); producer run
`39362948819` left a provenance mislabeling (state pointed at another run's
verdict/narrative; its own were never written). Operational resume run
`39363768044` re-verified the measurement byte-identically, hardened the
harness (`--run-id`), back-filled the `39362948819` verdict/narrative, and
corrected every state path. The verdict is unchanged. Consume the `39363768044`
records (the verified latest) or the original `39355384602` records — all
carry the same numbers.

## Verdict

**BOUNDED-NEGATIVE** — the packet-of-record v3 (`gate_packet/39319405429`,
packet.json sha256 `32ac8126…`, manifest `8ea3c92d…`) is **not served**. Both
frozen absolute bars remain unmet as written on the packet's own bytes, and the
map adds no marginal discovery over a conventional ranked list on the same
bundles. `owner_decision_required=false`; no owner card, no owner session, no
`ready_for_owner_session=true`, no `human_gate_ready=true` is produced, staged
or readied.

## Artifacts to consume

| Artifact | Path (team namespace) | Consumer |
|---|---|---|
| Verdict record (verified latest, run 39363768044) | `results/frontier/frontier-packet-serve-audit/VERDICT_39363768044.json` | Product (packet admission), Evaluation (cross-check) |
| Audit report (run 39363768044) | `results/frontier/frontier-packet-serve-audit/audit_report_39363768044.json` | Director |
| Operational-resume report (run 39363768044) | `reports/frontier/frontier-packet-serve-audit/REPORT_39363768044.md` | Director |
| Verdict record (original run 39355384602) | `results/frontier/frontier-packet-serve-audit/VERDICT_39355384602.json` | Product, Evaluation (historical) |
| Audit report (original) | `results/frontier/frontier-packet-serve-audit/audit_report.json` | Director (historical) |
| Back-filled verdict (run 39362948819) | `results/frontier/frontier-packet-serve-audit/VERDICT_39362948819.json` | Director (provenance back-fill) |
| Back-filled narrative (run 39362948819) | `reports/frontier/frontier-packet-serve-audit/REPORT_39362948819.md` | Director (provenance back-fill) |
| Freeze record (committed before scoring) | `results/frontier/frontier-packet-serve-audit/RULES.json` | Evaluation (freeze-ordering proof) |
| This contract | `reports/frontier/frontier-packet-serve-audit/INTEGRATION_CONTRACT.md` | Product, Evaluation |
| Audit report (narrative, original) | `reports/frontier/frontier-packet-serve-audit/REPORT_39355384602.md` | Director |
| Operational-resume report | `reports/frontier/frontier-packet-serve-audit/REPORT_39359987809.md` | Director |
| Team state | `state/frontier/frontier-packet-serve-audit.json` | Director |

## What the verdict record contains

- `input_identity` — packet.json / manifest / per-bundle raw + content sha256,
  all matching the charter pins (re-hashed before any scoring).
- `label_half` — `n_scored=0`, `n_supported=0`, `support_rate=null` (0/0),
  `absolute_status=LABEL_UNSOUND`, population-pinned `regression_verdict=NOT_APPLICABLE`,
  population-free `label_lineage_gate_verdict=NOT_MEASURED` (neither is a pass),
  `n_abstain`, `yield_over_population=0.0`.
- `geometry_half` — per-criterion counts on the SHIPPED post-rerank bundles:
  de 3/11, fr 4/11, it 4/11; `absolute_status=GEOMETRY_UNSOUND`; per-bundle
  `mega_cluster` disclosure (fires on all three).
- `marginal_discovery` — 0 of 0 issued counter rows marginally discovered
  (K=20); the map adds nothing on this packet.
- `crosscheck` — this team's recomputation beside Core Evaluation's published
  numbers (39338699604 stand-ready, 39325867172 audit, product's own
  disclosures.json rescore). Geometry matches exactly (3/4/4); the label
  divergence vs the packet admission record is named (the record cites the OLD
  packet's 65-row population; v3 scores 0).
- `non_vacuity` — seeded geometry control (≥2 criteria move on de/fr), frozen
  label injection battery (7/7 pass, ≥2 defect classes), and verdict
  reachability (both SERVE and DO-NOT-SERVE reachable).
- `verdict` — the single machine-checked recommendation with the owner-session
  guard (all gate flags false).

## How to re-run (offline, deterministic)

```
cd frontier/frontier-packet-serve-audit
python3 -m frontier_packet_serve_audit.cli \
  --packet /tmp/lex_accepted/core/product/results/product/gate_packet/39319405429 \
  --frozen-rules /tmp/lex_accepted/core/evaluation/evaluation/frozen_bars \
  --out <team-namespace>/VERDICT.json
```

Tests (20, deterministic, offline):
```
python3 -m pytest tests/frontier/frontier-packet-serve-audit/ -v
```

## What this team did NOT do

- No product file, no `results/product/` write, no `state/product.json` write,
  no `.github/**` write, no `evaluation/` write.
- No threshold, bar, rubric or verdict contract edited or re-derived.
- No frozen bar weakened; no contrary output deleted; no historical
  claim-bearing result overwritten.
- No owner card / session / gate flag produced or readied.
- No claim that any case IS supporting/contrary/limiting without evidence.
