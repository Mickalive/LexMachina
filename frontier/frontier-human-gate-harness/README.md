# frontier-human-gate-harness

One-command offline owner test harness for the Master Prompt **human product gate**
(charter v1 · run `38600279890`).

It makes the gate answerable in a single sitting:

1. a **conventional ranked-list baseline** rendered from the *same* `query_result_bundle`
   the map draws (rank, decision_id, court, date, language, citation, snippet, source link —
   no cluster colour, no proximity, no counter grouping);
2. a **one-click list ↔ map switch** over the identical already-loaded bundle (no
   re-retrieval, no bundle mutation);
3. an **FR/DE owner card** with the four Master Prompt gate questions (scale 1–5 + free text)
   plus one suggested real Swiss-law question taken verbatim from the frozen
   `rent-default` reality-check leg;
4. a **session capture** writing `results/frontier/frontier-human-gate-harness/session_<id>.json`
   with bundle/query hash, view mode per action, decisions opened, counter-authorities
   opened, timestamped answers and wall-clock latency — no personal data, no fabricated
   entries, no silent defaults.

## Run it (one command, offline)

```bash
cd frontier/frontier-human-gate-harness
python -m frontier_human_gate_harness.cli \
    --fixture ../../results/frontier/frontier-human-gate-harness/fixtures/query_result_bundle_kuendigung_101.json \
    --out ../../results/frontier/frontier-human-gate-harness/smoke
```

produces `baseline_view.html`, `owner_card_fr.html`, `owner_card_de.html`,
`owner_card.json`, `session_empty_<hash>.json`, `harness_demo.html` (the clickable
list↔map switch + card + export slice) and `summary.json`.

Smoke everything (fixture check, 42 tests, node assertions, CLI run, output + scope checks):

```bash
bash frontier/frontier-human-gate-harness/smoke.sh
```

Finalise a real owner sitting (missing answer ⇒ exit 2, never invented):

```bash
python -m frontier_human_gate_harness.cli --finalize <draft.json> \
    --fixture <bundle.json> --out results/frontier/frontier-human-gate-harness
```

Exit codes: `0` ok · `2` capture/validation error · `3` missing bundle field (charter
TERMINATE rule — the exact field is named, nothing is invented) · `4` usage error.

## Tests (deterministic, offline, no third-party deps)

```bash
python tests/frontier/frontier-human-gate-harness/run_tests.py          # stdlib runner
node tests/frontier/frontier-human-gate-harness/js/verify_switch.js     # 45 switch assertions
```

Same modules also run under `pytest` when pytest is installed (skips use `unittest.SkipTest`).
Python↔JS row parity is asserted byte-for-byte on the frozen fixture.

## Layout

| Path | Role |
|---|---|
| `frontier_human_gate_harness/bundle_io.py` | contract mirror, canonical hashes, product-validator reuse |
| `frontier_human_gate_harness/baseline_view.py` | conventional ranked-list baseline (acceptance 1) |
| `frontier_human_gate_harness/owner_card.py` | FR/DE card + provenance-labelled suggested question (3) |
| `frontier_human_gate_harness/capture.py` | session record schema, merge, reject-on-missing (4/6) |
| `frontier_human_gate_harness/cli.py` | one-command offline path + offline guard (5) |
| `frontier_human_gate_harness/demo_page.py` | clickable vertical slice (2/3/4 in one page) |
| `static/lex_gate_switch.{js,css}` | product drop-in switch component (2) |
| `tools/make_fixture.py` | deterministic fixture synthesiser, `--check` = byte-identical |
| `smoke.sh` | one-command evidence run |
| `INTEGRATION_CONTRACT.md` / `.json` | acceptance (7): what product copies, exact hooks, ownership |
| `OWNERS_PROTOCOL.md` | the short owner protocol for the sitting |

Evidence lands in `results/frontier/frontier-human-gate-harness/{smoke,evidence}`.

## Rules honoured

* Offline by construction: the package has no HTTP client; `cli.py` installs a socket guard
  for the whole run; `static/lex_gate_switch.js` contains no network capability token.
* Never invent data: missing bundle field ⇒ exit 3 naming it; missing answer ⇒ exit 2; empty
  answer ⇒ treated as missing; `missing_answers` must equal the computed set exactly.
* Fixture provenance: `results/.../fixtures/FIXTURE_PROVENANCE.json` records source branch,
  per-file input hashes, both hash semantics (file bytes vs canonical JSON) and the single
  record dropped for a missing source key — never filled in.
* All fixture `counter_status` values stay `unclassified`; nothing here classifies authority.
* Write scope: only `frontier/…`, `tests/frontier/…`, `results/frontier/…`,
  `reports/frontier/…` and `state/frontier/frontier-human-gate-harness.json`.
