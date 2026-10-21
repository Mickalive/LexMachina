# Counter-probe repair-verification falsifier — run 39687372110

**Verdict: `REPAIR_VERIFIED_ON_RECORDED_BYTES`** (exit 0)

on the pinned recorded bytes of the accepted 14-bundle population, the recommended remedy (a) repairs the probe-anchor bounded cause: every FIXED anchor is free of placeholder-derived tokens (G1), both baseline-contaminated German anchors regain a topical anchor (G2), the twelve clean-anchor bundles are byte-for-byte unperturbed (G3), and every FIXED anchor equals the accepted falsifier record 39674402905's published G4 de-redacted anchor (G4), with all five controls held. This is a repair VERIFICATION on recorded bytes, not a live-retrieval or counter-authority-recall measurement.

## What was measured

Two arms per bundle of the accepted 14-bundle population, both computed with the product's OWN `plan_adversarial_queries`:

- **BASELINE** — the shipped planner on the shipped (post-redaction) answer prose; must reproduce the recorded probes byte-for-byte (C1).
- **FIXED** — the recommended remedy (a) emulated: the redaction placeholder stripped from the answer prose, then the same planner.

## Population

- source: `mount` (`/tmp/lex_accepted/product`)
- measurable bundles: **14**
- population manifest sha256: `80306fd5fe05c04e36faa5d2adf6a2b98167280a05eb7ea48ce57ec17bdf73db`

## Gates

| gate | result | detail |
|---|---|---|
| `G1_no_placeholder_token_in_fixed_anchor` | PASS | n_bundles=14, n_failed=0 |
| `G2_fixed_anchor_topical_on_contaminated_bundles` | PASS | n_failed=0, n_required=2 |
| `G3_fixed_is_noop_on_clean_anchor_bundles` | PASS | n_failed=0, n_required=12 |
| `G4_fixed_matches_accepted_counterfactual` | PASS | n_compared=14, n_failed=0 |

## Per-bundle result

| packet | lang | ph | baseline anchor | contaminated | fixed anchor | G1 clean | G2 topical | G3 noop | G4 match |
|---|---|---|---|---|---|---|---|---|---|
| 38838116453 | de | 0 | `fürsorgepflicht entscheidungen arbeitgebers kapitalverletzung` | no | `fürsorgepflicht entscheidungen arbeitgebers kapitalverletzung` | yes | yes | yes | yes |
| 38838116453 | fr | 0 | `termination defect court landlord` | no | `termination defect court landlord` | yes | n/a | yes | yes |
| 38839347028 | de | 3 | `duty care employer fürsorgepflicht` | no | `duty care employer fürsorgepflicht` | yes | yes | yes | yes |
| 38839347028 | fr | 0 | `landlord defects grave rent` | no | `landlord defects grave rent` | yes | n/a | yes | yes |
| 38839347028 | it | 0 | `gerichte medico dell tribunale` | no | `gerichte medico dell tribunale` | yes | yes | yes | yes |
| 39275520116 | de | 11 | `citation removed retrieved fürsorgepflicht` | **YES** | `fürsorgepflicht arbeitgeber nicht pflicht` | yes | yes | n/a | yes |
| 39275520116 | fr | 0 | `défaut résiliation tribunal entretien` | no | `défaut résiliation tribunal entretien` | yes | yes | yes | yes |
| 39275520116 | it | 3 | `tribunale diligenza dell nesso` | no | `tribunale diligenza dell nesso` | yes | yes | yes | yes |
| 39319405429 | de | 9 | `citation removed retrieved nicht` | **YES** | `nicht fürsorgepflicht arbeitgeber bvger` | yes | yes | n/a | yes |
| 39319405429 | fr | 0 | `résiliation bailleur défaut entretien` | no | `résiliation bailleur défaut entretien` | yes | yes | yes | yes |
| 39319405429 | it | 4 | `dell diligenza violazione nesso` | no | `dell diligenza violazione nesso` | yes | yes | yes | yes |
| rebuilt-39027045675 | de | 3 | `duty care employer fürsorgepflicht` | no | `duty care employer fürsorgepflicht` | yes | yes | yes | yes |
| rebuilt-39027045675 | fr | 0 | `landlord defects grave rent` | no | `landlord defects grave rent` | yes | n/a | yes | yes |
| rebuilt-39027045675 | it | 0 | `gerichte medico dell tribunale` | no | `gerichte medico dell tribunale` | yes | yes | yes | yes |

`ph` = occurrences of the redaction placeholder in the answer prose. `G2 topical`/`G3 noop` are gates only where marked required (contaminated baseline anchors / clean baseline anchors respectively).

## Repaired probe queries on the contaminated bundles (acceptance fixture)

### 39275520116 / de

- intent#0: `citation removed retrieved fürsorgepflicht ausnahme exception eccezione vorbehalt réserve riserva einschränkung excepté fatta eccezione` → `fürsorgepflicht arbeitgeber nicht pflicht ausnahme exception eccezione vorbehalt réserve riserva einschränkung excepté fatta eccezione`
- intent#1: `citation removed retrieved fürsorgepflicht abweichend a contrario contrario entgegen contraire respinto anderer auffassung contrairement inammissibile` → `fürsorgepflicht arbeitgeber nicht pflicht abweichend a contrario contrario entgegen contraire respinto anderer auffassung contrairement inammissibile`
- intent#2: `citation removed retrieved fürsorgepflicht minderheit minorité minoranza minderheitsmeinung minoritaire dissenso dissens avis minoritaire abweichende meinung` → `fürsorgepflicht arbeitgeber nicht pflicht minderheit minorité minoranza minderheitsmeinung minoritaire dissenso dissens avis minoritaire abweichende meinung`
- intent#3: `citation removed retrieved fürsorgepflicht ältere rechtsprechung ancienne jurisprudence precedente giurisprudenza früher autrefois in passato früheren rechtsprechung désormais mittlerweile` → `fürsorgepflicht arbeitgeber nicht pflicht ältere rechtsprechung ancienne jurisprudence precedente giurisprudenza früher autrefois in passato früheren rechtsprechung désormais mittlerweile`

### 39319405429 / de

- intent#0: `citation removed retrieved nicht ausnahme exception eccezione vorbehalt réserve riserva einschränkung excepté fatta eccezione` → `nicht fürsorgepflicht arbeitgeber bvger ausnahme exception eccezione vorbehalt réserve riserva einschränkung excepté fatta eccezione`
- intent#1: `citation removed retrieved nicht abweichend a contrario contrario entgegen contraire respinto anderer auffassung contrairement inammissibile` → `nicht fürsorgepflicht arbeitgeber bvger abweichend a contrario contrario entgegen contraire respinto anderer auffassung contrairement inammissibile`
- intent#2: `citation removed retrieved nicht minderheit minorité minoranza minderheitsmeinung minoritaire dissenso dissens avis minoritaire abweichende meinung` → `nicht fürsorgepflicht arbeitgeber bvger minderheit minorité minoranza minderheitsmeinung minoritaire dissenso dissens avis minoritaire abweichende meinung`
- intent#3: `citation removed retrieved nicht ältere rechtsprechung ancienne jurisprudence precedente giurisprudenza früher autrefois in passato früheren rechtsprechung désormais mittlerweile` → `nicht fürsorgepflicht arbeitgeber bvger ältere rechtsprechung ancienne jurisprudence precedente giurisprudenza früher autrefois in passato früheren rechtsprechung désormais mittlerweile`

## Controls

| control | result | detail |
|---|---|---|
| `C1_baseline_reproduces_recorded_probes` | PASS | n_bundles=14, n_failed=0 |
| `C2_blank_prose_yields_no_plan_in_both_arms` | PASS | n_plans_baseline=0, n_plans_fixed=0 |
| `C3_repair_target_exists` | PASS | n_baseline_contaminated=2 |
| `C4_fix_is_noop_without_the_placeholder` | PASS | n_failed=0 |
| `C5_fix_does_not_kill_probe_emission` | PASS | n_failed=0 |

## Pin discipline

- pins re-hashed BEFORE execution: 8 checks, all_ok=True
- pins re-hashed AFTER execution: 8 checks, all_ok=True

## Claim ceiling

This instrument establishes exactly one thing: whether the RECOMMENDED product remedy (a) — strip the redaction placeholder from the answer prose before the product's own probe planner — repairs the probe-anchor bounded cause on the pinned recorded bytes of the accepted 14-bundle population, under four frozen gates (G1 no placeholder token in any FIXED anchor; G2 topical FIXED anchor on every baseline-contaminated bundle; G3 byte-for-byte no-op on every clean-anchor bundle; G4 FIXED anchors equal the accepted record 39674402905's published G4 de-redacted anchors). It is a REPAIR VERIFICATION computed offline from committed bytes with zero network calls: the FIXED probes are never executed against OpenCaseLaw, so it is NOT a counter-authority recall measurement, NOT a live-retrieval measurement, NOT a label-emission measurement, NOT a measurement of the mapping-free counter_authority_surface gates, NOT a claim about LABEL_SOUND or GEOMETRY_SOUND (both stay REPORTED-ONLY), NOT a claim about jurist usefulness or the map, and NOT a serve recommendation. It lifts no DO-NOT-SERVE order; packet admission stays fail-closed; human_gate_ready and owner_decision_required stay false. It does NOT authorise the product lane to skip re-measuring after it lands the fix: when the product bytes change, this freeze's product pins drift and a NEW freeze under a NEW run id must verify the shipped planner itself. No universal-174k benchmark is run and no product source file is modified by this instrument.

## Pre-freeze disclosure

Reconnaissance preceded this freeze and is disclosed verbatim so no reader mistakes this run for a blind confirmation. WHAT I OBSERVED BEFORE FREEZING: (1) the accepted falsifier record 39674402905 in full — its verdict COUNTER_PROBE_ANCHOR_FALSIFIED, its 14-bundle population, its 2 contaminated bundles (39275520116 de with 11 placeholder occurrences and anchor [citation, removed, retrieved, fürsorgepflicht]; 39319405429 de with 9 and anchor [citation, removed, retrieved, nicht]), and its per-bundle G4 de-redaction counterfactual arms, from which the G2 prediction follows directly: the published de-redacted anchors are [fürsorgepflicht, arbeitgeber, nicht, pflicht] and [nicht, fürsorgepflicht, arbeitgeber, bvger], both carrying the question content term fürsorgepflicht, while all twelve other bundles published de_differs=False (the counterfactual is a no-op on them); (2) the accepted falsifier's product_handoff naming remedy (a) — exclude the redaction placeholder from the probe key terms in product/query/adversarial_retrieval.py — as the recommended fix and stating remedy (b) (plan from pre-redaction prose) alone is insufficient if the answer lacks legal vocabulary; (3) that the product mount's current shipped planner (product/query/adversarial_retrieval.py, sha256 57b6a6f9...) still contains the unfixed `probe_terms = [t for t in key_terms[:4]] + terms` reading the raw post-redaction prose, i.e. the fix has NOT landed; (4) a local reproduction of the accepted falsifier on the pinned mount (run id local_verify_39687372110, results/evaluation/counter_probe_anchor_falsifier/local_verify_39687372110.json) reproducing the accepted verdict, the same 14 bundles, the same 2 contaminated bundles and the same anchors — a reproduction of accepted EXPLORATORY evidence, not a new claim; (5) a --selftest run of this instrument on SYNTHETIC prose only (loader works; a synthetic placeholder-heavy prose yields a contaminated BASELINE anchor and a clean topical FIXED anchor; a clean prose is a no-op under the fix; placeholder-only prose yields a plan in the BASELINE arm and none in the FIXED arm, reproducing the D4 restoration), which by construction never touches the real bundle population and never writes a result file. No repair-verification measurement on the real population, no gate outcome, no control outcome and no result file existed at the moment of this freeze.

