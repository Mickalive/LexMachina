"""Re-derivable pins for product cycle run 44862651889.

Entry point for the next independent audit of this operational-resume cycle.
Verifies the orchestration classification, the runnable delta, every headline
number in the report, and the fail-closed posture — all from committed files.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

RUN = "44862651889"
DIAG = ROOT / f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json"
REPORT = ROOT / f"reports/product/CYCLE_{RUN}.md"
FAMILY = ROOT / f"results/product/counter_content_family/CYCLE_{RUN}_post_fix.json"
SMOKE_POST = ROOT / f"results/product/progressive_smoke/CYCLE_{RUN}_post_fix_progressive_smoke.json"
SMOKE_PRE = ROOT / f"results/product/progressive_smoke/CYCLE_{RUN}_progressive_smoke.json"
PRIOR_DIAG = ROOT / "results/product/orchestration/CYCLE_44856191029_resume_diagnosis.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_snapshot_has_zero_durable_delta_and_is_unadjudicated():
    d = _load(DIAG)
    o = d["orchestration_failure"]
    assert d["resumed_snapshot_run_id"] == "44862477576"
    assert o["snapshot_ref"] == "origin/cycle/core/product/44862477576/team"
    assert o["snapshot_head"] == "df5fa61f"
    assert o["durable_delta_classification"] == "ZERO_DURABLE_DELTA"
    assert o["mechanism_status"] == "UNOBSERVED"
    assert o["adjudication"] == "UNADJUDICATED - neither accepted nor rejected; not a product defect and not an audit verdict"
    assert _sha(PRIOR_DIAG) == o["carried_forward_sha256"]


def test_real_delta_files_and_hashes_match_the_dossier():
    d = _load(DIAG)
    files = {f["path"]: f["sha256"] for f in d["real_delta_this_cycle"]["files"]}
    assert set(files) == {
        "product/query/counter_evidence_span.py",
        "product/tests/test_sweep_grounding_parity.py",
    }
    for rel, sha in files.items():
        assert _sha(ROOT / rel) == sha
    assert d["real_delta_this_cycle"]["kind"] == "runnable code + tests, plus verification artifacts"


def test_one_shared_content_predicate_is_wired_into_both_legs():
    # The helper exists, is deterministic and model-free, and the sweep source
    # calls it rather than the weaker passes_content_filter.
    ev = "Kantonsgericht Graubuenden header"
    row = {"decision_id": "SYN", "full_text": ev, "snippet": "", "regeste": "",
           "language": "de"}
    failed, reason, defects, grounded = ces._incumbent_content_failure(ev, row)
    assert failed is True and reason == "d2_letterhead_zone"
    assert defects == ["D2_letterhead_zone"] and grounded == "full_text"
    src = (ROOT / "product/query/counter_evidence_span.py").read_text(encoding="utf-8")
    sweep = src[src.index("def _content_rejection_sweep"):src.index("def apply_verified_span_selection")]
    assert "_incumbent_content_failure" in sweep
    assert "passes_content_filter(ev, d)" not in sweep
    assert "if d.get(\"counter_evidence_span\"):" not in sweep


def test_verification_artifacts_pins_and_success_rule():
    d = _load(DIAG)
    v = d["verification_by_execution"]
    assert v["bounded_mvp_suite"]["result"].startswith("175 passed")
    assert v["p0_subset"]["result"].startswith("49 passed")
    assert v["state_contract"]["result"].startswith("ok=true")

    fam = _load(FAMILY)
    assert _sha(FAMILY) == v["full_fixed_path_family_probe"]["sha256"]
    assert fam["run_id"] == RUN and fam["direction_version"] == 68
    fixed = fam["fixed_path_family"]["bundles"]
    assert len(fixed) == 49
    assert sum(b["n_decisions"] for b in fixed) == 4900
    assert sum(b["n_verified"] for b in fixed) == 55
    assert sum(b["n_verified_defective"] for b in fixed) == 0
    after = fam["before_after"]["per_class_histogram"]["fixed_path_after_population"]
    assert set(after.values()) == {0}
    hist = fam["before_after"]["per_class_histogram"]["historical_before_population"]
    assert hist["D2_letterhead_zone"] == 44
    assert hist["D3_markup_residue"] == 31
    assert hist["D4_language_marker_mismatch"] == 7
    assert fam["false_reject_count"] == 0
    assert fam["confirmed_set"]["still_verified"] is True
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True

    smoke = _load(SMOKE_POST)
    assert _sha(SMOKE_POST) == v["clickable_slice_post_fix"]["sha256"]
    assert smoke["run_id"] == RUN and smoke["verdict"] == "PASS"
    assert (smoke["checks_passed"], smoke["checks_total"]) == (23, 23)
    assert smoke["failures"] == []
    assert all(c["ok"] for c in smoke["checks"])
    assert SMOKE_PRE.is_file(), "pre-fix smoke is preserved, never overwritten"
    assert _sha(SMOKE_PRE) != _sha(SMOKE_POST)


def test_report_names_both_runs_and_keeps_the_claim_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert "44862477576" in text and "44862651889" in text
    assert "175 passed" in text and "23/23" in text
    assert "not an audit verdict" in text
    assert "BOUNDED-NEGATIVE" in text
    assert "continue_recommended=true" in text


def test_state_attributes_the_executing_run_and_stays_fail_closed():
    st = _load(ROOT / "state/product.json")
    assert st["current_cycle_run_id"] == 44862651889
    assert f"cycle_{RUN}_operational_resume" in st
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "ready_for_owner_session",
                 "packet_admitted", "owner_decision_required"):
        assert st[flag] is False, flag
    # accepted pointer is not churned
    assert st["accepted_run_id"] == "CYCLE_40269774540"
