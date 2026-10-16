# frontier-counter-label-integrity

Harness for the pre-registered measurement of **counter-label support**: whether the
counter-authority statuses the accepted query map renders (`candidate-limiting`,
`candidate-contrary`, `contrary_or_exception`, `limiting`) are supported by the evidence
each row itself cites.

**Design rule: this package contains no lexicon, no threshold and no judgement.** Every
lexicon, criterion, precedence step, threshold, question anchor and injection fixture is read
from the frozen `RULES.json` passed on the command line, so no code edit can change a verdict
without changing the frozen file whose sha256 is embedded in every report. `test_freeze.py`
asserts this mechanically.

## Run it

```bash
export PYTHONPATH=frontier/frontier-counter-label-integrity
FROZEN=results/frontier/frontier-counter-label-integrity/RULES.json
OUT=results/frontier/frontier-counter-label-integrity

# all frozen inputs (primary + declared replication population)
python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN --all --out $OUT

# one bundle
python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN \
    --bundle /tmp/lex_accepted/core/product/results/product/gate_packet/38799024807/questions/fr-bail-entretien.bundle.json \
    --out $OUT/single

# non-vacuity only (charter test 8)
python3 -m frontier_counter_label_integrity.cli --frozen-rules $FROZEN --non-vacuity-only --out $OUT

# freeze ordering proof from git commit times (charter test 1)
python3 -m frontier_counter_label_integrity.verify_freeze --repo-root . --out $OUT

python3 -m pytest tests/frontier/frontier-counter-label-integrity -q
```

Offline and deterministic: no network, no provider, no paid API, no clock in any
claim-bearing path. The accepted product mount is read read-only; a bundle whose bytes no
longer match the frozen `sha256`, or an unregistered copy of a frozen input, is refused.

## Modules

| module | role |
|---|---|
| `normalize.py` | frozen normalisation: NFKC, diacritic fold, `ue/oe/ae` fold for tokens, frozen suffix stemmer. Marker matching is exact on stemmed tokens; anchor matching is prefix-tolerant; regex patterns see the non-digraph-folded string (see below). |
| `rules.py` | loads and validates `RULES.json`, exposes its sha256 and the frozen lexicons |
| `extract.py` | lifts each counter row's own fields and cited evidence verbatim; separates scored rows from `cited` rows |
| `rubric.py` | criteria (i)–(v), defect signals, and the frozen precedence applied first-match-wins; three passes (`primary`, `lenient-domain-only`, `strict-no-product-vocabulary`) |
| `injection.py` | non-vacuity: scores the frozen injected rows and requires their frozen expected classes |
| `report.py` | population summaries, per-class breakdown, criterion failures, language/rank/uncertainty/marker distributions, verdict, coverage, drift |
| `cli.py` | the command line above |
| `verify_freeze.py` | proves freeze ordering from git commit times and re-hashes every frozen input |
| `scope_guard.py` | mirrors the workflow's `Enforce team scope` allow-list offline, so the producer can run the same check before the workflow does. Mirrors the WORKFLOW rule, never `RULES.json`: the frozen `write_scope` lists the audit dirs because it describes the audit job's checkout, while the producer's enforced allow-list does not include them. |
| `disposition.py` | emits the in-scope audit-tree provenance ledger (`AUDIT_TREE_PROVENANCE.json`): every audit artifact, its sha256, its machine class and the team's **declared** provenance, flagging every file where the two disagree. Reads the audit tree read-only. |
| `audit_contract.py` | routes each gate artifact to the contract of its own class (independent audit of record vs producer placement copy) and validates it; enforces an anti-vacuity invariant that an audit of record must exist |

## Write scope — read this before adding an artifact

The producer writes **only** under `frontier/<team>/`, `tests/frontier/<team>/`,
`results/frontier/<team>/`, `reports/frontier/<team>/`, `state/frontier/<team>.json` and
`data/frontier/<team>/`. It writes **nothing** under `results/audit/**` or
`reports/audit/**`: those paths belong to the audit job, are absent from the workflow's
`Enforce team scope` allow-list, and are outside charter acceptance test (12).

Eight dispatches (`38845649012` → `38851515402`) failed at exactly that step because the team
wrote its own placement copies there; the following `if: always()` persist step committed them
into a clean-looking tree and the lane re-dispatched. Use `--disposition` for the in-scope
provenance ledger and `--scope-check` to verify before you finish.

## Two implementation notes worth knowing

1. **Regex patterns are matched on the diacritic-folded but NOT digraph-folded string.** The
   frozen patterns are authored in natural orthography (`darüber genaue Angaben`); folding
   `ue → u` turns the pattern word into `genau` and the match silently fails. Token-level
   matching keeps the digraph fold because the anchors are authored with it (`ueberwachung`)
   and must match both spellings. This was a real defect caught by the non-vacuity run.
2. **Field presence is measured separately from emptiness.** An accepted row can carry
   `counter_status` with no `counter_evidence_verified` flag at all; conflating that with
   `false` would hide the disclosure defect the measurement is about.

## Re-freezing

Do **not** re-freeze to make a result look better. `freeze_rules.py` refuses to overwrite an
existing `RULES.json` without `--force`, and any later edit changes
`rules_unchanged_since_freeze` in `FREEZE_PROOF.json` to `false`, which invalidates the run.
A new measurement over different bytes is a **new charter**; a re-measurement after a promoted
product repair must reuse **this** `RULES.json` to form a before/after pair.