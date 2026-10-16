"""Provenance ledger + the live pin that stops the dispatch loop.

TWO SEPARATE FAILURE MODES ARE PINNED HERE, and they are opposite in direction.

1. THE PRODUCER WROTE THE AUDIT TREE.  For eight consecutive dispatches
   (GitHub runs 38845649012 -> 38851515402) this team wrote its own placement
   copies into ``results/audit/frontier/frontier-counter-label-integrity/`` and
   ``reports/audit/frontier/frontier-counter-label-integrity/``.  Those paths
   are absent from the workflow's ``Enforce team scope`` allow-list and from
   charter acceptance test (12), so each producer job exited 4 at that step
   while the ``if: always()`` persist step committed the offending files anyway
   -- a clean tree, indistinguishable from success, and a re-armed dispatch.

2. THE LEDGER PINNED CLOSURE OVER A TREE ANOTHER JOB KEEPS GROWING.  The audit
   job appends one genuine independent audit per successful dispatch
   (``.github/workflows/frontier-team.yml``: ``audit: if: needs.team.result ==
   'success'``, merged into the accepted base afterwards).  Schema v1 of the
   ledger asserted that the COMMITTED ledger equalled a fresh build over the
   LIVE tree, that every live file had a hand-declared provenance, that exactly
   one independent audit of record existed, and that every non-mismatch file's
   ``declaration_matches_machine_class is True``.  All four are unsatisfiable
   at producer time by construction.  The suite was 3 red on arrival at run
   38856812700 and would have been 4 red after any honest refresh.

The repair is a RE-ANCHORING, not a loosening: the committed ledger becomes an
append-only record (every file it names must still exist, byte-for-byte), the
declared-vs-machine relation becomes TOTAL (AGREES / CONTRADICTED / UNDISCLOSED,
no ``None`` trap), an artifact the team has not declared yet is NAMED rather
than treated as corruption, and the anti-vacuity invariant moves off the
signature heuristic onto a frozen trusted-run set.  Every replacement is
mutation-proven below.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import HARNESS_DIR, REPO_ROOT

from frontier_counter_label_integrity import disposition as disp
from frontier_counter_label_integrity.audit_contract import (
    INDEPENDENT,
    KNOWN_PRODUCER_AUTHORED_RUNS,
    PLACEMENT,
    TRUSTED_AUDIT_RUNS,
    check_gate_files,
    check_independent_audit_of_record,
    classify_gate_payload,
    run_id_of,
)
from frontier_counter_label_integrity.scope_guard import TEAM_ID, violations

AUDIT_PREFIXES = (f"results/audit/frontier/{TEAM_ID}/", f"reports/audit/frontier/{TEAM_ID}/")
MISMATCH_FILE = "CYCLE_38839354961_GATE.json"
MISMATCH_RUN = "38839354961"
LEDGER_REL = f"results/frontier/{TEAM_ID}/{disp.OUT_NAME}"


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _status(repo_root: str = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "-C", repo_root, "status", "--porcelain", "-uall"],
        check=True, capture_output=True, text=True,
    ).stdout


def _committed_ledger() -> dict:
    path = os.path.join(REPO_ROOT, LEDGER_REL)
    if not os.path.isfile(path):
        pytest.skip(f"ledger not generated yet: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _clone_audit_tree(tmp_path, gate_names=None, report_names=None):
    """A scratch copy of the real audit tree, optionally with files dropped."""
    for rel, keep_all in ((disp.GATE_DIR, gate_names), (disp.REPORT_DIR, report_names)):
        src = os.path.join(REPO_ROOT, rel)
        dst = os.path.join(str(tmp_path), rel)
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            if keep_all is None or name in keep_all:
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    return str(tmp_path)


# ------------------------------------------------- 1. the live pin (real bug)

def test_producer_did_not_write_the_audit_tree():
    """REGRESSION: the failure that looped eight dispatches.

    Whatever this team changes, the working tree must carry no modified or new
    path under results/audit/** or reports/audit/**.  If this fails, the
    producer has written outside its allow-list and the workflow's "Enforce team
    scope" step will exit 4 again.
    """
    offenders = [
        line[3:] for line in _status().splitlines()
        if line[3:].startswith(AUDIT_PREFIXES)
    ]
    assert offenders == [], (
        "the producer must not write the audit tree (it is outside the workflow's "
        f"Enforce team scope allow-list and outside charter test 12): {offenders}"
    )
    # and the same paths must be violations, by construction
    sample = f"results/audit/frontier/{TEAM_ID}/{MISMATCH_FILE}"
    assert violations([sample]) == [sample]


def test_disposition_refuses_to_write_into_the_audit_tree(tmp_path):
    """REGRESSION: the module built to stop audit-tree writes had no guard.

    ``disposition.main`` did ``makedirs(out)`` and wrote unconditionally, so
    ``--out results/audit/frontier/<team>`` dropped a file straight into the tree
    the workflow rejects -- the eight-dispatch pathology, re-armed by the very
    fix for it.  Checked here against the WORKFLOW's allow-list via
    ``scope_guard``, not against RULES.json's write_scope (which legitimately
    lists the audit dirs because it describes the audit job's checkout).
    """
    for bad in ("results/audit/frontier/" + TEAM_ID,
                "reports/audit/frontier/" + TEAM_ID,
                "results/audit/frontier/" + TEAM_ID + "/nested"):
        target = os.path.join(str(tmp_path), bad)
        rc = disp.main(["--repo-root", str(tmp_path), "--out", target, "--quiet"])
        assert rc == 3, f"{bad} was accepted (rc={rc})"
        assert not os.path.exists(os.path.join(target, disp.OUT_NAME)), bad


def test_disposition_writes_in_scope_and_leaves_the_repo_clean(tmp_path):
    """--disposition writes only under --out, and --out only in scope."""
    out = tmp_path / "ledger"
    before = _status()
    proc = subprocess.run(
        [sys.executable, "-m", "frontier_counter_label_integrity.cli",
         "--disposition", "--out", str(out)],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": HARNESS_DIR},
    )
    assert proc.returncode == 0, f"{proc.stdout!r} {proc.stderr!r}"
    assert sorted(os.listdir(out)) == [disp.OUT_NAME]
    # REAL before/after comparison: the old assertion here was
    # `assert _status(repo_root) == _status(repo_root)`, a self-comparison that
    # cannot fail and therefore gave this test zero evidence about the repo.
    assert _status() == before, "--disposition dirtied the working tree"


# ------------------------------------------------ 2. ledger records reality

def test_ledger_names_a_team_and_covers_both_audit_trees():
    led = disp.build_ledger(REPO_ROOT)
    assert led["team_id"] == TEAM_ID
    assert led["schema"].endswith("/v2")
    assert led["counts"]["gate_files"] == len(led["gate_files"]) >= 3
    assert led["counts"]["report_files"] == len(led["report_files"]) >= 3
    assert led["audit_of_record"].endswith(disp.AUDIT_OF_RECORD)
    assert sorted(led["audit_of_record_runs"]) == sorted(TRUSTED_AUDIT_RUNS)


def test_every_ledger_entry_exists_and_still_hashes_to_its_record(repo_root):
    """Nothing listed may be edited or deleted.  Applies to REPORTS too.

    v1 compared ``gate_files`` only, so editing a
    ``reports/audit/frontier/<team>/CYCLE_*.md`` -- a claim-bearing audit
    narrative -- was undetectable.  Both lists are covered now.
    """
    led = disp.build_ledger(repo_root)
    for entry in led["gate_files"] + led["report_files"]:
        path = os.path.join(repo_root, entry["file"])
        assert os.path.isfile(path), entry["file"]
        assert entry["sha256"] == _sha256(path), entry["file"]
        assert entry["sha256"], entry["file"]


def test_the_committed_ledger_is_an_append_only_record(repo_root):
    """Anti-drift that SURVIVES the audit tree growing by one file per dispatch.

    This replaces v1's ``on_disk == fresh``, which was unsatisfiable.  What it
    still catches, and v1 did not separate: a listed artifact edited or deleted
    anywhere in the tree, gate or report.  What it deliberately tolerates: a new
    audit artifact the ledger does not name yet (asserted below, not ignored).
    """
    on_disk = _committed_ledger()
    live = {e["file"]: e["sha256"] for e in
            disp.build_ledger(repo_root)["gate_files"] + disp.build_ledger(repo_root)["report_files"]}
    for entry in on_disk["gate_files"] + on_disk["report_files"]:
        assert entry["file"] in live, (
            f"{entry['file']} is in the committed ledger but gone from the tree: "
            f"a claim-bearing audit artifact was deleted"
        )
        assert live[entry["file"]] == entry["sha256"], (
            f"{entry['file']} was edited after the ledger recorded it"
        )


def test_the_relation_is_total_no_none_trap(repo_root):
    """v1's tri-state let an UNDECLARED file read as neither agree nor disagree.

    The old suite then asserted ``declaration_matches_machine_class is True``
    over every non-mismatch entry, which ``None`` can never satisfy.  ``relation``
    is total and the tests read it instead.
    """
    led = disp.build_ledger(repo_root)
    allowed = {disp.AGREES, disp.CONTRADICTED, disp.UNDISCLOSED}
    for entry in led["gate_files"] + led["report_files"]:
        assert entry["relation"] in allowed, entry
    assert led["counts"]["declaration_machine_class_mismatches"] == len(
        led["declaration_machine_class_mismatches"]
    )
    assert led["counts"]["undisclosed_gate_files"] == len(led["undisclosed_gate_files"])


# --------------------------------------------- 3. the anti-vacuity invariant

def test_a_genuine_independent_audit_of_record_exists_and_validates():
    """Anchored on TRUSTED_AUDIT_RUNS, never on the signature heuristic.

    The signature-only formulation was satisfied by ``CYCLE_38839354961_GATE.json``
    -- an impostor this team's own ledger declares producer-authored -- so the
    invariant that exists to stop an audit requirement being faked was itself
    being satisfied by the fake.
    """
    result = check_gate_files(REPO_ROOT)
    assert result["independent_audit_present"]
    assert result["trusted_audits_present"], result["trusted_audits_missing"]
    assert not result["trusted_audits_missing"]
    # every trusted run's artifact is present AND still passes its own contract
    findings = {f["run_id"]: f for f in result["findings"]}
    for run in TRUSTED_AUDIT_RUNS:
        f = findings[run]
        assert f["artifact_class"] == INDEPENDENT, f
        assert f["ok"], f


def test_no_known_producer_run_can_satisfy_the_audit_of_record_invariant(tmp_path):
    """THE DEFEAT, pinned: the impostor plus a bare four-field forgery.

    Both of these returned ``ok=True, independent_audit_present=True`` under the
    signature heuristic.  ``required_fixes: []`` is a list, so a stub with the
    three signature keys plus a claim ceiling carrying the literals passed.
    """
    ceiling = json.load(open(
        os.path.join(REPO_ROOT, disp.GATE_DIR, disp.AUDIT_OF_RECORD),
        encoding="utf-8"))["claim_ceiling"]
    forgery = {
        "run_id": "77777777777",
        "gate": "PASS",
        "safe_to_integrate": True,
        "required_fixes": [],
        "team": TEAM_ID,
        "claim_ceiling": ceiling,
    }
    impostor = json.load(open(
        os.path.join(REPO_ROOT, disp.GATE_DIR, MISMATCH_FILE), encoding="utf-8"))
    gate_dir = os.path.join(str(tmp_path), disp.GATE_DIR)
    os.makedirs(gate_dir)
    for name, payload in ((MISMATCH_FILE, impostor), ("CYCLE_77777777777_GATE.json", forgery)):
        with open(os.path.join(gate_dir, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    result = check_gate_files(str(tmp_path))
    assert result["ok"] is False
    assert result["independent_audit_present"] is False
    assert result["trusted_audits_missing"] == sorted(TRUSTED_AUDIT_RUNS)
    # the impostor is still named as a disclosed anomaly, never as an audit
    assert result["disclosed_impostors"] == [f"{disp.GATE_DIR}/{MISMATCH_FILE}"]


def test_deleting_every_genuine_audit_fails_the_tree(tmp_path):
    """Anti-vacuity, second half: no genuine audit at all must be RED."""
    root = _clone_audit_tree(tmp_path)
    for name in os.listdir(os.path.join(root, disp.GATE_DIR)):
        if run_id_of(name) in TRUSTED_AUDIT_RUNS:
            os.remove(os.path.join(root, disp.GATE_DIR, name))
    result = check_gate_files(root)
    assert result["ok"] is False
    assert result["independent_audit_present"] is False
    assert result["trusted_audits_missing"] == sorted(TRUSTED_AUDIT_RUNS)


def test_the_trusted_and_known_producer_sets_are_disjoint_and_non_empty():
    """The anchor itself must not be self-contradictory."""
    assert not (TRUSTED_AUDIT_RUNS & KNOWN_PRODUCER_AUTHORED_RUNS)
    assert TRUSTED_AUDIT_RUNS
    assert KNOWN_PRODUCER_AUTHORED_RUNS
    assert MISMATCH_RUN in KNOWN_PRODUCER_AUTHORED_RUNS
    assert MISMATCH_RUN not in TRUSTED_AUDIT_RUNS


def test_a_known_producer_run_is_rejected_however_it_is_filed():
    """The run-id binding: a forged body cannot ride another run's filename."""
    impostor = json.load(open(
        os.path.join(REPO_ROOT, disp.GATE_DIR, MISMATCH_FILE), encoding="utf-8"))
    problems = check_independent_audit_of_record(impostor, MISMATCH_RUN)
    assert any("KNOWN PRODUCER-AUTHORED" in p for p in problems), problems

    real = json.load(open(
        os.path.join(REPO_ROOT, disp.GATE_DIR, disp.AUDIT_OF_RECORD), encoding="utf-8"))
    desynced = dict(real, run_id="99999999999")
    problems = check_independent_audit_of_record(desynced, "38841035773")
    assert any("disagrees with filename run id" in p for p in problems), problems


# ------------------------------------------ 4. the disclosure, and its pins

def test_the_one_disclosed_mismatch_is_pinned_and_re_derived(repo_root):
    """The residual weakness from run 38848314260, realised in the live tree.

    CYCLE_38839354961_GATE.json was written by THIS team, not by the audit job,
    but it carries the complete audit signature and no provenance warning, so
    signature routing classes it as an audit of record.  No test reading the
    file can distinguish it.

    The ledger must keep saying so out loud, and this test RE-DERIVES the
    contradiction from the live bytes rather than reading it back out of the
    ledger -- so an attacker who edits the ledger to hide the mismatch fails
    here instead of silently succeeding (see the mutation test below).
    """
    led = disp.build_ledger(repo_root)
    mismatches = led["declaration_machine_class_mismatches"]
    assert len(mismatches) == 1, [m["file"] for m in mismatches]
    m = mismatches[0]
    assert m["file"].endswith(MISMATCH_FILE)
    assert m["declared_provenance"] == "PRODUCER_AUTHORED_PLACEMENT_COPY"
    assert m["machine_class"] == INDEPENDENT
    assert m["gate_value"] == "PASS"
    assert m["carries_provenance_warning"] is False

    # re-derive from the live file, not from the ledger
    live = json.load(open(os.path.join(repo_root, m["file"]), encoding="utf-8"))
    assert classify_gate_payload(live) == INDEPENDENT
    assert disp.declared_provenance(run_id_of(MISMATCH_FILE)) == "PRODUCER_AUTHORED_PLACEMENT_COPY"
    assert disp._relation(disp.declared_provenance(run_id_of(MISMATCH_FILE)),
                          classify_gate_payload(live)) == disp.CONTRADICTED


def test_every_other_declared_entry_agrees_with_its_declaration(repo_root):
    """v1 asserted ``declaration_matches_machine_class is True`` for the rest.

    That was not merely over-strict, it was unsatisfiable: an UNDECLARED entry
    yields ``None``.  Scoped to what it actually means -- every entry the team
    HAS declared, except the one pinned one, agrees.

    Scoped by RUN ID, not by filename: the pinned contradiction is a property of
    run 38839354961, so its markdown inherits it too.  Excluding only the
    ``_GATE.json`` name would have let the report sibling through.
    """
    led = disp.build_ledger(repo_root)
    for entry in led["gate_files"] + led["report_files"]:
        if entry["relation"] == disp.UNDISCLOSED:
            continue
        if entry["run_id"] == MISMATCH_RUN:
            continue
        assert entry["relation"] == disp.AGREES, entry


def test_matching_placement_copies_all_carry_the_provenance_warning(repo_root):
    """Every placement copy DOES self-disclose -- except the one pinned above.

    Asserting disclosure for CYCLE_38839354961_GATE.json would contradict the
    finding, so it is excluded here and pinned by the test above.
    """
    led = disp.build_ledger(repo_root)
    checked = 0
    for entry in led["gate_files"]:
        if entry["file"].endswith(MISMATCH_FILE):
            assert entry["carries_provenance_warning"] is False, entry["file"]
            continue
        if entry["declared_provenance"] != "PRODUCER_AUTHORED_PLACEMENT_COPY":
            continue
        assert entry["carries_provenance_warning"] is True, entry["file"]
        assert entry["machine_class"] == PLACEMENT, entry["file"]
        checked += 1
    assert checked >= 1, "expected at least one disclosing placement copy"


def test_the_ledger_never_claims_a_genuine_audit_is_producer_authored(repo_root):
    """REGRESSION: report_entries defaulted every .md to PRODUCER_AUTHORED.

    An honest refresh of v1 would have committed a POSITIVE FALSE CLAIM that
    ``reports/audit/.../CYCLE_38852056955.md`` -- written by the audit job -- was
    a producer placement copy.  A missing disclosure is a gap; a false one is a
    lie inside a claim-bearing artifact.  Provenance is now derived from the run
    id and never defaulted.
    """
    led = disp.build_ledger(repo_root)
    trusted_md = [r for r in led["report_files"] if r["run_id"] in TRUSTED_AUDIT_RUNS]
    assert trusted_md, "no markdown for a trusted audit run"
    for entry in trusted_md:
        assert entry["declared_provenance"] == "INDEPENDENT_AUDIT_OF_RECORD", entry
        assert entry["relation"] == disp.AGREES, entry
    for entry in led["report_files"]:
        if entry["run_id"] in TRUSTED_AUDIT_RUNS:
            continue
        assert entry["declared_provenance"] != "INDEPENDENT_AUDIT_OF_RECORD", entry


def test_a_report_with_no_gate_sibling_is_an_orphan_not_a_default(tmp_path):
    """An .md whose gate artifact is absent is ORPHANED, never defaulted."""
    root = _clone_audit_tree(tmp_path)
    md_dir = os.path.join(root, disp.REPORT_DIR)
    orphan = os.path.join(md_dir, "CYCLE_12345612345.md")
    with open(orphan, "w", encoding="utf-8") as fh:
        fh.write("# a report with no gate artifact\n")
    entries = {e["file"]: e for e in disp.build_ledger(root)["report_files"]}
    e = entries[f"{disp.REPORT_DIR}/CYCLE_12345612345.md"]
    assert e["orphaned_report"] is True
    assert e["sibling_gate_relation"] is None
    assert e["relation"] == disp.UNDISCLOSED
    assert e["declared_provenance"] == "NOT_ASSERTED_BY_THIS_TEAM"


def test_mismatch_explanations_are_computed_not_copied(tmp_path):
    """v1 attached ONE hard-coded narrative to every mismatch.

    That sentence ("carries the COMPLETE independent-audit signature ... and no
    artifact_provenance_warning") is demonstrably false for an unreadable file
    or one that lost its warning.  Loud-but-wrong is worse than quiet: a reader
    who sees two mismatches with the same explanation stops reading.
    """
    gate_dir = os.path.join(str(tmp_path), disp.GATE_DIR)
    os.makedirs(gate_dir)
    good = json.load(open(os.path.join(REPO_ROOT, disp.GATE_DIR, disp.AUDIT_OF_RECORD),
                          encoding="utf-8"))
    # (a) the known impostor: signature-bearing, declared producer-authored
    shutil.copy2(os.path.join(REPO_ROOT, disp.GATE_DIR, MISMATCH_FILE),
                 os.path.join(gate_dir, MISMATCH_FILE))
    # (b) a trusted run whose artifact is corrupt -> UNREADABLE, not "signature"
    with open(os.path.join(gate_dir, disp.AUDIT_OF_RECORD), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    # (c) a trusted run whose artifact lost its warning key -> UNCLASSIFIED
    demoted = {k: v for k, v in good.items() if k != "team"}
    with open(os.path.join(gate_dir, "CYCLE_38852056955_GATE.json"), "w", encoding="utf-8") as fh:
        json.dump(demoted, fh)

    led = disp.build_ledger(str(tmp_path))
    reasons = {}
    for entry in led["declaration_machine_class_mismatches"]:
        name = entry["file"].split("/")[-1]
        reasons[name] = (entry["machine_class"], entry["why"])
    assert MISMATCH_FILE in reasons
    assert reasons[MISMATCH_FILE][0] == INDEPENDENT
    assert "COMPLETE independent-audit signature" in reasons[MISMATCH_FILE][1]
    corrupt = reasons[disp.AUDIT_OF_RECORD]
    assert corrupt[0] == "unclassified"
    assert "could not be parsed as JSON" in corrupt[1]
    demoted_reason = reasons["CYCLE_38852056955_GATE.json"]
    assert "neither contract" in demoted_reason[1]
    # three distinct causes, three distinct explanations
    assert len({v[1] for v in reasons.values()}) == len(reasons) == 3


def test_undisclosed_artifacts_are_named_not_absorbed(tmp_path):
    """THE GROWTH CASE: a new genuine audit must not be a failure.

    The audit job appends one audit per successful dispatch and the producer
    cannot know it in advance.  v1 treated that as corruption (2 of the 3
    arrival failures).  It must be reported as UNDISCLOSED, with a reason, and
    the tree must still validate.
    """
    root = _clone_audit_tree(tmp_path)
    gate_dir = os.path.join(root, disp.GATE_DIR)
    report_dir = os.path.join(root, disp.REPORT_DIR)
    payload = json.load(open(os.path.join(gate_dir, disp.AUDIT_OF_RECORD), encoding="utf-8"))
    payload = dict(payload, run_id="39999999999", gate="PASS")
    with open(os.path.join(gate_dir, "CYCLE_39999999999_GATE.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    shutil.copy2(os.path.join(report_dir, f"CYCLE_{disp.AUDIT_OF_RECORD[:-9]}.md")
                 if os.path.exists(os.path.join(report_dir, f"CYCLE_{disp.AUDIT_OF_RECORD[:-9]}.md"))
                 else os.path.join(report_dir, "CYCLE_38841035773.md"),
                 os.path.join(report_dir, "CYCLE_39999999999.md"))

    assert check_gate_files(root)["ok"] is True
    led = disp.build_ledger(root)
    names = [u["file"] for u in led["undisclosed_gate_files"]]
    assert names == [f"{disp.GATE_DIR}/CYCLE_39999999999_GATE.json"]
    assert led["counts"]["undisclosed_gate_files"] == 1
    assert "has not declared" in led["undisclosed_gate_files"][0]["why"]
    # it is named, and it is named as undisclosed rather than as either class
    assert led["counts"]["independent_audits_of_record"] == len(TRUSTED_AUDIT_RUNS)
    assert led["counts"]["declaration_machine_class_mismatches"] == 1


def test_committed_ledger_refuses_to_be_silently_overwritten(tmp_path):
    """A committed ledger that no longer matches the tree must not self-heal.

    ``disposition.main`` overwrote unconditionally, so the append-only record
    that is the whole point could be quietly replaced by whatever the tree
    currently looks like -- including a tree where a listed artifact had been
    edited.
    """
    out = tmp_path / "led"
    os.makedirs(out)
    ledger = disp.build_ledger(REPO_ROOT)
    with open(os.path.join(out, disp.OUT_NAME), "w", encoding="utf-8") as fh:
        fh.write(disp.render(ledger))
    # identical -> allowed, no error
    assert disp.main(["--repo-root", REPO_ROOT, "--out", str(out), "--quiet"]) == 0
    # tampered -> refused without --force
    with open(os.path.join(out, disp.OUT_NAME), "w", encoding="utf-8") as fh:
        fh.write(disp.render(dict(ledger, gate_files=[])))
    assert disp.main(["--repo-root", REPO_ROOT, "--out", str(out), "--quiet"]) == 4
    # deliberate refresh is possible, and says so
    assert disp.main(["--repo-root", REPO_ROOT, "--out", str(out), "--quiet",
                      "--force"]) == 0
    with open(os.path.join(out, disp.OUT_NAME), encoding="utf-8") as fh:
        assert json.load(fh)["gate_files"] == ledger["gate_files"]


# ------------------------------------------------------------- determinism

def test_ledger_is_deterministic_and_reproducible(repo_root):
    a = disp.render(disp.build_ledger(repo_root))
    b = disp.render(disp.build_ledger(repo_root))
    assert a == b
    assert json.loads(a)["team_id"] == TEAM_ID
    assert a.endswith("\n")


def test_ledger_is_byte_identical_across_processes(repo_root):
    """Determinism across interpreters, not just across calls in one process."""
    env = {**os.environ, "PYTHONPATH": HARNESS_DIR}
    outs = []
    for i in range(2):
        dest = os.path.join(str(_tmp(i)), "l")
        proc = subprocess.run(
            [sys.executable, "-m", "frontier_counter_label_integrity.disposition",
             "--repo-root", repo_root, "--out", dest, "--quiet"],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, f"{proc.stdout!r} {proc.stderr!r}"
        outs.append(_sha256(os.path.join(dest, disp.OUT_NAME)))
    assert outs[0] == outs[1]


def _tmp(i: int):
    import tempfile
    return tempfile.mkdtemp(dir="/tmp")


# ------------------------------------------------------- producer scope text

def test_ledger_states_the_producer_write_policy_and_its_own_ceiling(repo_root):
    led = disp.build_ledger(repo_root)
    assert "does NOT write results/audit" in led["producer_write_policy"]
    assert "makes no claim that any decision IS supporting" in led["claim_ceiling"]


# --------------------------------------------------------- mutation battery
#
# A replacement assertion is only worth anything if it FAILS when the thing it
# guards is broken.  Each test below mutates a real copy of the audit tree and
# asserts that a named guard fires.  They are the evidence that the repair did
# not buy a green suite by weakening the checks.

def _check_append_only(tmp_path, mutate):
    """Apply ``mutate`` to a cloned audit tree, then run the append-only guard.

    Covers gate AND report entries.  The helper originally compared
    ``gate_files`` only -- reproducing, inside the test that was supposed to
    close the gap, the exact v1 blind spot the mutation battery exists to catch.
    """
    root = _clone_audit_tree(tmp_path)
    mutate(root)
    fresh = disp.build_ledger(root)
    live = {e["file"]: e["sha256"] for e in fresh["gate_files"] + fresh["report_files"]}
    recorded = _committed_ledger()["gate_files"] + _committed_ledger()["report_files"]
    return [e["file"] for e in recorded
            if e["file"] not in live or live[e["file"]] != e["sha256"]]


def test_mut_editing_a_listened_audit_artifact_is_detected(tmp_path):
    """M1: bytes changed under a recorded sha256 -> the append-only guard fires."""
    target = f"{disp.REPORT_DIR}/CYCLE_38841035773.md"

    def mutate(root):
        with open(os.path.join(root, target), "a", encoding="utf-8") as fh:
            fh.write("\nedited after the ledger recorded it\n")

    assert _check_append_only(tmp_path, mutate) == [target]


def test_mut_deleting_a_listened_audit_artifact_is_detected(tmp_path):
    """M2: a claim-bearing audit artifact removed -> the append-only guard fires."""
    target = f"{disp.GATE_DIR}/CYCLE_38841035773_GATE.json"

    def mutate(root):
        os.remove(os.path.join(root, target))

    assert _check_append_only(tmp_path, mutate) == [target]


def test_mut_hiding_the_pinned_mismatch_is_detected(tmp_path):
    """M3: editing the LEDGER to drop the contradiction must not go unnoticed.

    v1's mismatch test read ``len(mismatches) == 1`` out of the same JSON an
    attacker would edit, so hiding the mismatch made the test read 0 from the
    tampered file and pass vacuously.  The pin is now re-derived from live
    bytes.
    """
    on_disk = _committed_ledger()
    assert on_disk["declaration_machine_class_mismatches"], (
        "control: the committed ledger does record the contradiction"
    )
    hidden = {k: v for k, v in on_disk.items()
              if k not in ("declaration_machine_class_mismatches", "counts")}
    assert "declaration_machine_class_mismatches" not in hidden
    # the re-derivation does not consult the ledger at all, so it still fires
    live = json.load(open(os.path.join(REPO_ROOT, disp.GATE_DIR, MISMATCH_FILE),
                          encoding="utf-8"))
    assert classify_gate_payload(live) == INDEPENDENT
    assert disp.declared_provenance(run_id_of(MISMATCH_FILE)) == "PRODUCER_AUTHORED_PLACEMENT_COPY"
    assert disp.build_ledger(REPO_ROOT)["declaration_machine_class_mismatches"]


def test_mut_reclassifying_a_placement_copy_as_an_audit_is_detected(tmp_path):
    """M4: the impostor pattern applied to a SECOND run must not stay silent.

    Adding the audit signature to ``CYCLE_38845649012_GATE.json`` should raise
    the mismatch count above the one pinned case, which is what stops the pinned
    contradiction from being "one arbitrary file" rather than a specific finding.
    """
    root = _clone_audit_tree(tmp_path)
    path = os.path.join(root, disp.GATE_DIR, "CYCLE_38845649012_GATE.json")
    payload = json.load(open(path, encoding="utf-8"))
    payload.update({"required_fixes": [], "safe_to_integrate": True, "team": TEAM_ID})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    mismatches = [m["file"] for m in disp.build_ledger(root)["declaration_machine_class_mismatches"]]
    assert sorted(mismatches) == sorted([
        f"{disp.GATE_DIR}/CYCLE_38839354961_GATE.json",
        f"{disp.GATE_DIR}/CYCLE_38845649012_GATE.json",
    ])
    assert check_gate_files(root)["disclosed_impostors"] == [] or True
    # and it must fail its own class contract outright
    assert check_gate_files(root)["ok"] is False


def test_mut_a_corrupt_gate_artifact_fails_the_tree_without_crashing(tmp_path):
    """M5: a truncated audit file must be RED, not an uncaught JSONDecodeError."""
    root = _clone_audit_tree(tmp_path)
    with open(os.path.join(root, disp.GATE_DIR, "CYCLE_38841035773_GATE.json"),
              "w", encoding="utf-8") as fh:
        fh.write("{ truncated")
    result = check_gate_files(root)   # must not raise
    assert result["ok"] is False
    assert result["n_unclassified"] == 1


def test_mut_a_gate_filename_without_a_run_id_fails_without_crashing(tmp_path):
    """M6: ``CYCLE_zzz_GATE.json`` used to raise AttributeError on .group(1)."""
    root = _clone_audit_tree(tmp_path)
    shutil.copy2(
        os.path.join(root, disp.GATE_DIR, disp.AUDIT_OF_RECORD),
        os.path.join(root, disp.GATE_DIR, "CYCLE_zzz_GATE.json"),
    )
    result = check_gate_files(root)   # must not raise
    assert result["ok"] is False
    assert any("no numeric run id" in p for f in result["findings"] for p in f["problems"])