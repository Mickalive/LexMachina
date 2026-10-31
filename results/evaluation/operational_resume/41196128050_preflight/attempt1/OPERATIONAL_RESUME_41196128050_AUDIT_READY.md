# Operational resume — evaluation run 41196128050 (direction v68)

**Verdict:** RESUME_VERIFIED_WITH_DISCLOSED_GAPS (exit 2).
No audit gate is minted. This is a non-measurement operational resume; all posture flags stay FALSE.

## 1. Why this run was resumed
Run 41196128050's `team` job failed at `Run lane cycle` after
2704.0 s (exit 78,
`LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2507`) against the
2700 s work quantum. `Validate active MVP producer state` and
`Enforce lane write scope` were SKIPPED; audit and integrate were never scheduled. The
always-guarded persist step published `bcd905aa14441bbf36a2e4de4720352d54a7315b` (parent `77574ac4f0ddf892874ae79de5dd5f0c19f8fe66`) on
`origin/cycle/core/evaluation/41196128050/team`.

## 2. Diagnosis (FACT vs UNOBSERVED)
- FACT: the team job (124522555422) failed at `Run lane cycle`, duration
  2704.0 s, exit 78, annotation
  `LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2507`.
- FACT: `Validate active MVP producer state` and `Enforce lane write scope` were skipped;
  `Clean generated junk` and `Persist team snapshot` succeeded.
- FACT: the persisted tree is a real delta over its parent:
  1 commit(s) / 62 paths.
- UNOBSERVED: the inner agent/provider error that consumed the quantum. Public logs are 403;
  no cause is asserted.

## 3. Snapshot scope
- Base `77574ac4f0ddf892874ae79de5dd5f0c19f8fe66` -> head `bcd905aa14441bbf36a2e4de4720352d54a7315b`.
- 62 paths changed; out of scope:
  [].
- Verdict: **SCOPE_CLEAN**; the team ref resolves to the head.

## 4. Inherited 41192962507 deliverable
- Record: `results/evaluation/operational_resume/41192962507.json` sha256 `c1ffe86a47455c20b583b03716e07da35bcfa6f8ec7eecc5e8174222cd169cd3` (preserved byte-for-byte).
- Verification: **57 checks, 0 failed** ->
  **INHERITED_DELIVERABLE_VERIFIED_WITH_CORRECTIONS**.
- Corrected verifier false negatives (historical bytes untouched):
  - `snapshot_is_new_delta_over_predecessor`: false -> true (committed 4 commits / 57 paths over 326f0e53).
  - `adjudicator_unchanged`: false -> true (sha256 126a1234... matches; predecessor key is `adjudicator_sha256_in_prior_record`).
- Dangling pointer `results/evaluation/orchestration/41192962507_self_check_pytest_shim.json` never existed; the real self-check bytes are at
  `results/evaluation/orchestration/41187766812_self_check_pytest_shim.json` with run_id 41192962507. Correction artifact: `results/evaluation/operational_resume/41196128050_evidence_ref_correction.json`.

## 5. Item (2) currency
- Product mount head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`; expected
  `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`; adjudicator sha256 `126a1234f3fe8a3f10ff736dff7466093000a2fadd8871f02f97efe974543a08`.
- Family regeneration 14/15.
- Protocol executed this run: **False**.
- Status: **NOT_YET_DISCRIMINATING_HEAD_UNCHANGED**.

## 6. Multilingual / provenance supplement
- `tests/evaluation/test_retrieval_benchmark.py` sha256 `558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be`.
- PASS 2/2 under
  numpy 2.5.4 /
  scipy 1.18.1 /
  scikit-learn 1.9.1.

## 7. Gates
- state integrity: **ALL_CHECKS_PASS** (11 checks, 0 failed)
- lane suite overall_pass: **True** (88 passed, 0 failed)
- write scope: **SCOPE_CLEAN**
- nested refs: **UNRESOLVED_REFS_PRESENT**
- self-check: **SHIM_FAIL** (12 passed, 1 failed)

## 8. Claim ceiling
Operational resume and audit-readiness only. No frozen bar, packet, serve verdict,
d2_path_scope_probe, standing falsification or 174k benchmark was scored or re-run.
Both DO-NOT-SERVE orders stand. The next discriminating step is a Product handoff:
regenerate the missing member so the named 15-member family reaches 15/15.

**Audit index:** `results/evaluation/operational_resume/AUDIT_INDEX_41196128050.json` · **Audit brief:** `reports/evaluation/AUDIT_BRIEF_41196128050.md`
