# Frozen-rules profile-coverage falsifier — operational resume 46114243630

- Lane: evaluation; direction_version 68; this run `46114243630`; resumed producer run `46110768588`.
- Generated: 2026-11-28T06:01:37Z.
- Status: producer deliverable COMPLETE and audit-ready; PENDING_INDEPENDENT_AUDIT; no promotion claim is made here.

## 1. Failure diagnosis (machine-established, not inferred)

- GitHub run `46110768588` (`https://api.github.com/repos/Mickalive/LexMachina/actions/runs/46110768588`) concluded `failure`; team job `failure`.
- Failing step: `Run lane cycle`.
- Annotations (verbatim): `Process completed with exit code 78.`; `Agent quantum ended cleanly; workflow must snapshot and resume rather than hang.`; `LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2465`.
- Classification: `LEX_WORK_QUANTUM_EXPIRED` (rc=78, seconds=2700). Per factory-wide requirements this is an orchestration limit — not a verdict, not a product defect and not a human-gate problem.
- Consequence: audit job `skipped`, integrate `skipped`, audit branch exists = False; no gate file and no accept commit for the subject run.

## 2. Snapshot preserved, not restarted

- Snapshot `origin/cycle/core/evaluation/46110768588/team` head `752c3efe335ee847f50961a2230fa7c94a19a574` (`evaluation cycle 46110768588 repair 0`).
- Added file: `evaluation/frozen_rules_profile_coverage_falsifier.py`, sha256 `3583be0c183383dfefa52a63f907e83bbea410de008a80c5a95c4f09f1c00186`. It is used byte-identically; it was NOT edited.
- The resume did not re-execute the failed producer job and did not regenerate the instrument. Freeze-first records were written before the first claim-bearing execution in this run.

## 3. Freeze-first discipline

- Hypothesis `evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_HYPOTHESIS_V1.json` sha256 `28b9c6b8b3e44cad31e5dbfd1069ed9253d3a01f7f11dee773ed03e5aa963219`.
- Freeze `evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_FREEZE_V1.json` sha256 `8bba19abca894b9b6eaf3a9a9a1b1bc0beddc0c58babb45dedb276cba04dc855`; 49 population digests pinned.
- Result reports hypothesis_sha256 `28b9c6b8b3e44cad31e5dbfd1069ed9253d3a01f7f11dee773ed03e5aa963219` and freeze_sha256 `8bba19abca894b9b6eaf3a9a9a1b1bc0beddc0c58babb45dedb276cba04dc855`; cross-check hypothesis_unchanged=True, pins_match_freeze=True.
- Pre-freeze scoping is disclosed verbatim in the hypothesis; no H1/H2/H3 predicate was executed before the freeze was written.

## 4. Measurement of record for this resume

- Verdict **`PROFILE_COVERAGE_FALSIFIED`**, exit_code `1`, controls_all_hold=`True`.
- Population: 49 fixed-path bundles; rent-default.bundle=18, petty-theft-dismissal.bundle=9, corporate-criminal-liability.bundle=9, business-judgment-rule.bundle=10, served=3.
- Falsified legs: `H1_profile_coverage, H2a_profile_norm_alignment`.
- H1 coverage holds=`False`; failing groups=`petty-theft-dismissal.bundle` (fresh resolver returns no frozen profile there).
- H2a norm alignment holds=`False`; failing groups=`business-judgment-rule.bundle, served`.
  - `rent-default.bundle`: profile=`fr-bail-entretien`, applicable=`True`, shared Art. norms=`257d`, holds=`True`.
  - `petty-theft-dismissal.bundle`: profile=`None`, applicable=`False`, shared Art. norms=`∅`, holds=`True`.
  - `corporate-criminal-liability.bundle`: profile=`responsabilite-penale-entreprise-102cp`, applicable=`True`, shared Art. norms=`102`, holds=`True`.
  - `business-judgment-rule.bundle`: profile=`fr-bail-entretien`, applicable=`True`, shared Art. norms=`∅`, holds=`False`.
  - `served`: profile=`kuendigung-mietrecht`, applicable=`True`, shared Art. norms=`∅`, holds=`False`.
- H2b corpus evidence and the whole-token H2a sensitivity variant are REPORT-ONLY, published in the result beside H2a; neither is verdict-bearing and neither silently replaces the frozen Art.-norm definition.
- H3 shipped-provenance agreement holds=`True` (0 disagreements over 49 bundles).
- Controls C1–C7 all hold: `C1_frozen_rules_digest`, `C2_qid_first_resolution_non_vacuous`, `C3_unknown_query_resolves_none`, `C4_norm_extractor_non_vacuity_synthetic`, `C5_determinism_two_full_passes`, `C6_pins_stable_before_after`, `C7_population_pins_match_freeze`.
- C5 two-pass digest `e58ccf9a8029014b89697b8d1767979203d6812cac18f6efbb05b762ee506550` identical in both passes.

## 5. Reproducibility and reused accepted assets

- Independent second process invocation: verdict identical; 18 claim-bearing fields compared, differing fields = `[]`; only `generated_at_utc` differs.
- Reused multilingual/provenance suite `tests/evaluation/test_retrieval_benchmark.py`: `SHIM_PASS` 2 passed, protocol digest `e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e` unchanged (pytest absent; executed under the documented shim).
- Additional coverage/multilingual suites: `SHIM_PASS` 27 passed, 0 failed, 1 unsupported (counted not-run, never passed).
- Numeric environment (requirement 30): numpy 2.5.5 / scipy 1.18.1 / scikit-learn 1.9.1 installed for the reused suite; no BLAS/thread pin and no cross-machine byte-identity claim. The profile-coverage instrument itself imports only the stdlib seam.

## 6. Product decision and claim ceiling

- The transferred coverage gap is CONFIRMED on the current accepted bytes: H1 fails for petty-theft-dismissal and H2a fails for business-judgment-rule and served. This bounds the counter-authority seam's ability to attach the correct frozen anchor to every flagship question; Product owns the repair of the resolver, this lane owns the probe.
- This measurement does NOT label any decision supporting/contrary/limiting, scores NO frozen bar/rubric/threshold/verdict contract, does NOT re-run or replace the benchmark of record (mapping-free falsifier, PRODUCT_FALSIFIED on packet-of-record 39319405429), issues NO serve verdict, admits NO packet, makes NO jurist-usefulness or live-recall claim, and runs NO universal-174k benchmark.
- Both DO-NOT-SERVE orders stand. `packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`, `owner_decision_required=false`.

## 7. Disclosures

- The preserved instrument pins the mount head as the stable string `HEAD_UNREADABLE` because `/tmp/lex_accepted/product/.git` is a worktree file, not a directory. The true git head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` is pinned in the hypothesis and re-checked independently; the instrument was not edited to work around it.
- Offline bundle group keys read `rent-default.bundle` etc. because the instrument uses `Path.stem`; the five claim-bearing groups are the same flagship roles. This naming quirk is preserved, not 'corrected', to keep the instrument byte-identical to the snapshot.
- GitHub REST evidence was fetched unauthenticated; job-log download is HTTP 403 without admin rights, so no log-line attribution is claimed. Pip installs and REST calls are network calls; there were ZERO OpenCaseLaw/retrieval/model/paid-API calls for the measurement.
- The result's H2b and whole-token numbers are definitions-dependent diagnostics: no number is silently preferred over H2a (factory-wide requirement 12).

## 8. Audit-readiness manifest (digests recomputed here)

| artifact | sha256 |
| --- | --- |
| `evaluation/frozen_rules_profile_coverage_falsifier.py` | `3583be0c183383dfefa52a63f907e83bbea410de008a80c5a95c4f09f1c00186` |
| `evaluation/operational_resume_46114243630_diagnosis.py` | `15bf3d01737f29bbeef9338545698b1aa5baeb0922f528ebb43224ad736506ff` |
| `evaluation/operational_resume_46114243630_freeze.py` | `2a20820ddfd2c0641f2237347033521681ac0fa5054b4e3a0b3c5e390766aa6e` |
| `evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_HYPOTHESIS_V1.json` | `28b9c6b8b3e44cad31e5dbfd1069ed9253d3a01f7f11dee773ed03e5aa963219` |
| `evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_FREEZE_V1.json` | `8bba19abca894b9b6eaf3a9a9a1b1bc0beddc0c58babb45dedb276cba04dc855` |
| `results/evaluation/orchestration/CYCLE_46110768588_resume_diagnosis.json` | `5e7a28d1c46da939a28c0d0ad22f51b6b66fdf8386f37d63279a559b11d759ef` |
| `results/evaluation/orchestration/CYCLE_46110768588_run.json` | `365c96e0838cb1aaae6d0919ef00dab90e98c77e42840e268e785d66123b35f6` |
| `results/evaluation/orchestration/CYCLE_46110768588_jobs.json` | `eb4de4223c67ad4c31bd773874adea926f403ea46635de84a0ca6e8e30e4770f` |
| `results/evaluation/orchestration/CYCLE_46110768588_team_annotations.json` | `c1377476db93bf12e384ab0cea6c6d9ea07cc278c5eb54637818b343db0cbfb6` |
| `results/evaluation/frozen_rules_profile_coverage/46114243630.json` | `1f5cfc2a422505d2c1d1e3b9e6ff4dd22cede9e591ab4d3c62252d03d1acfb8a` |
| `results/evaluation/frozen_rules_profile_coverage/46114243630_REPRO.json` | `c9a77c0a29d7c050f2aff7cddd4ced250c0a36db2e4da8e8bacfb46b93c8fabb` |
| `results/evaluation/frozen_rules_profile_coverage/46114243630_REPRO_CHECK.json` | `8ac7264df0442de8762a56727c7a9d700dc77de2c95910c26f933d059cc589cf` |
| `results/evaluation/orchestration/46114243630_retrieval_benchmark_shim.json` | `ea8a3829bd867d4f7582cf32125771558dfbecbe80cbffa65def7a7f155f2891` |
| `results/evaluation/orchestration/46114243630_reused_suites_shim.json` | `d46173a9b690a0f6bbf4c08c60fcda562e1a690ae7ab38b6fd9c30ed38b41af5` |

## 9. Exact reproduction commands

```bash
python3 -m evaluation.frozen_rules_profile_coverage_falsifier --run-id 46114243630 --hypothesis evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_HYPOTHESIS_V1.json --freeze evaluation/FROZEN_RULES_PROFILE_COVERAGE_46114243630_FREEZE_V1.json --product-mount /tmp/lex_accepted/product --out results/evaluation/frozen_rules_profile_coverage/46114243630.json
PYTHONPATH=/tmp/lex_accepted/product python3 -m evaluation.no_pytest_runner --run-id 46114243630 --test-file tests/evaluation/test_retrieval_benchmark.py --out results/evaluation/orchestration/46114243630_retrieval_benchmark_shim.json
```

Claim ceiling of this report: it certifies that the resumed producer deliverable exists, is reproducible and is ready for an INDEPENDENT audit. It is not an audit gate, not an acceptance and not a promotion.
