# State minimal-CA provenance repair v2 — run 39866970583

- Verdict: **REPAIR_VERIFIED_SUITE_GREEN** (exit 0)
- Direction: v63
- v1 attempt preserved verbatim: `results/evaluation/state_minimal_ca_provenance_repair/39866970583.json` (sha256 8e0e8bb84fec..., REPAIR_FAILED_OR_VACUOUS on a node-id comparison defect; its substantive gates G0/G2/G3/G4/G5/G6 all passed)
- Cycle hypothesis SHA256: `1b11b4d76b22615d65da2c7a3d26a510975a1204483b095a3a1a8f54a866757b` (frozen at 93dd639c, unchanged)
- Freeze record SHA256: `744a9b1f9efd2a4357b04b341af2659ca46e8607cd02abdad2896b62aeb3bbbb`; amendment V1_1: `31ed3dd453834d6b74d7a0a8706d70db22ca59f15f0f364fd47339ac7f9624e8`
- Instrument v2 SHA256: `9db47e2747077e2245b291e52b8e62fa2200c54b79f07e9e7bda206f03a294d6`; v1: `18eab54d5c23835455eace4de2795d1864167b9b9de5798de2da369289835ce1` (bytes unchanged)
- Pre-repair state (from a7e3565fcb7a) SHA256: `99544d85374797cf2a90a8bebda0bcae6afd2cf7f103b29a066f681cbf890c20` — dedicated suite 8 passed / 3 failed, exactly the 3 KeyError state-block tests
- Post-repair dedicated suite: 11 passed / 0 failed / 0 skipped (pytest, test_minimal_ca_benchmark.py)
- Sibling suites: test_minimal_retrieval_ca_benchmark.py 21/0/0; test_mapping_free_recall_falsifier.py 24/0/0
- Frozen inputs re-hashed after all runs: unchanged
- Stand-ready: product head fe219a197e4bfb129984a732ab9adca917556eac (expected fe219a197e4bfb129984a732ab9adca917556eac); ordered items (1)(2)(5) NOT_TRIGGERED, (3)(4) STANDING_OK
- Failed gates: none

## Claim ceiling
Establishes only that the dedicated provenance suite of the accepted minimal-CA falsification benchmark was failing solely due to lost state metadata and that a re-derived-pin restoration turns it green with no test/frozen-file/threshold change. Not a new retrieval/counter-authority/label/geometry/serve measurement; does not re-run the v3 falsification claim; no bar moved; no DO-NOT-SERVE order lifted; all admission/human flags stay false; no universal-174k benchmark run.

## Provenance
- Machine record: `results/evaluation/state_minimal_ca_provenance_repair/39866970583_v2.json`
- v1 machine record (preserved): `results/evaluation/state_minimal_ca_provenance_repair/39866970583.json`
- Hypothesis: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json`
- Freeze record: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1.json`
- Amendment: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1_1.json`
- No test file, frozen file, rubric, bar, threshold or benchmark record was edited.
