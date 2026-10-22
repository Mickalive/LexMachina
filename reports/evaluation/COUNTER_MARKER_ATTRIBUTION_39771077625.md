# Counter-marker attribution benchmark — run 39771077625

- Schema: `lex-evaluation-counter-marker-attribution/1`
- Hypothesis: `evaluation/V62_COUNTER_MARKER_ATTRIBUTION_HYPOTHESIS_V1.json` (sha256 `039c0c7f…`), freeze record `evaluation/V62_COUNTER_MARKER_ATTRIBUTION_FREEZE_RECORD_V1.json`, both committed FREEZE-FIRST at `0f08f400` before any claim-bearing execution
- Verdict: **MARKER_BLINDSPOT_ATTRIBUTED** (exit 1)
- Controls: **7/7 hold** (C1 spec pin re-hashed before+after; C2 cache parity 24/24; C3 accepted-record parity on pool sizes {223,218,221,205} and marker counts {16,0,0,4}; C4 build_bundle agreement on every question; C5 planted detection 2/2; C6 known-counter sets non-empty 9/6/4/9; C7 zero network)
- Frozen inputs: spec sha256 `187b0e54…`, accepted record sha256 `5fd695aa…` — both unchanged before/after; drift `{}`

## Question

The accepted cached-bundle benchmark (run 39766474798) measured a NEGATIVE RESULT on real cached OpenCaseLaw rows: the frozen counter-marker rule (a norm_token AND a limitation_token in title+regeste+snippet) yields ZERO counter candidates for 2/4 frozen questions (corporate-criminal-liability, business-judgment-rule) while the SAME pool contains 4/6 and 1/4 of those questions' own frozen `known_counter_ids`. This run attributes that accepted negative result to exactly one frozen cause class per question.

## Per-question verdicts

| question | pool | marker-labelled | known-counter reached | question verdict | dominant reached class |
|---|---|---|---|---|---|
| rent-default | 223 | 16 | 3/9 | MIXED_REPORTED_ONLY | LIMITATION_LEXICON_ABSENT (3/3) |
| corporate-criminal-liability | 218 | **0** | 4/6 | **MARKER_RULE_BLINDSPOT_ATTRIBUTED** | LIMITATION_LEXICON_ABSENT (4/4) |
| business-judgment-rule | 221 | **0** | 1/4 | **MARKER_RULE_BLINDSPOT_ATTRIBUTED** | LIMITATION_LEXICON_ABSENT (1/1) |
| petty-theft-dismissal | 205 | 4 | 7/9 | MIXED_REPORTED_ONLY | LABELLED 1, LIMITATION_LEXICON_ABSENT 6 |

Aggregate over all 28 frozen known-counter ids: **15 reached, 13 NOT_REACHED; of the 15 reached rows, 14 are UNLABELLED by the marker rule and 13 of those 14 carry ZERO limitation tokens anywhere on the extended diagnostic surface** (title+regeste+snippet+rule_statement+statutes). Exactly one reached known-counter row is labelled (petty-theft, `ar_gerichte_KG_ARGVP_2005_3462`, norm `art. 337` + limitation `billigkeit`/`treu und glauben`).

## Attribution (the finding)

**The accepted 2/4 zero yield is caused by the marker/lexicon layer, not by retrieval and not by assembly.** For both zero-yield questions, the counter channel (and baseline channel) DID retrieve known contrary/limiting authorities — 4/6 and 1/4 of the frozen sets — and the frozen marker rule cannot label them because the frozen limitation lexicons do not express the vocabulary of those rows: the limitation tokens are ABSENT FROM THE WHOLE ROW, not merely missing from the 3-field marker surface. The three rows whose norm token lives only on the extended surface (`bger_6B_7_2014` fr, `bge_BGE_138_I_113` de, `ge_gerichte_CAPH_107_2004` fr) still carry ZERO limitation tokens anywhere, so the frozen priority correctly classes them LIMITATION_LEXICON_ABSENT — widening the marker surface ALONE would not label any of them.

The named remedies, per the frozen cause classes:

1. **Marker/lexicon layer (dominant, both zero-yield questions)**: richer evidence surface alone is INSUFFICIENT; the remedy is lexicon enrichment and/or an adjudicated counter classifier over retrieved rows — directionally consistent with the emission charter's honest-abstention outcome (n_scored=8/n_abstained=8/n_emitted=0 per v3 bundle), not with more paging and not with an assembly change.
2. **Channel gap (co-existing, reported separately per H4)**: 13/28 known-counter ids were NOT reached by any channel of the question's own cached retrieval (rent 6/9, corporate 2/6, bjr 3/4, petty 2/9). That gap's remedy is counter-query expansion and is never folded into the marker attribution.

## Multilingual cut (REPORTED-ONLY, never gated)

Reached known-counter rows by language: de 11 (10 LIMITATION_LEXICON_ABSENT, 1 LABELLED), fr 4 (all LIMITATION_LEXICON_ABSENT), it 0 reached. No language is exempt from the lexicon blindness; the FR rows of the German-norm questions are as blind as the DE rows.

## Divergence check

`diverged_questions` is empty: NO_MARKER_DEFECT did not occur on any zero-yield question, so there is no divergence from the accepted record to headline. C3 parity reproduced the accepted counts exactly.

## Claim ceiling

This run attributes the accepted cached-bundle negative result (39766474798) on the evaluation FIXTURE's frozen marker rule over the accepted cached rows. It does NOT measure the product's shipped counter classifier, the emission repair, the anchor classifier or any Frontier build, and it claims nothing about them. It meets/moves/re-derives NO frozen absolute bar (LABEL_SOUND and GEOMETRY_SOUND stay REPORTED-ONLY and unmet); it lifts NO DO-NOT-SERVE order; it certifies NO packet admission; it claims NO jurist usefulness; human_gate_ready, machine_gate_ready, packet_admitted and ready_for_owner_session stay false; owner_decision_required stays false; no obsolete universal-174k benchmark was run; zero network calls.

Machine record: `results/evaluation/counter_marker_attribution/39771077625.json`
