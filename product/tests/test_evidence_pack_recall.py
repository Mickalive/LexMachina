"""Evidence-pack recall: the durable instrument for the accepted RED BJR leg.

The accepted frozen leg ``recall::citation_controlling_authority`` was RED at
executions 38920872324 / 38934722443 / 38945976309 and the only measurement of
its repair was n=2 live runs (run 38984833779), which is not durability.
``product/evidence_pack_recall.py`` measures the *precondition* for that leg
offline from the frozen cache: whether a frozen controlling authority survives
into the hydrated evidence pack the generator is given.

Every test here is offline and deterministic. Each behavioural test carries its
own non-vacuity control, so a harness that stopped measuring anything would fail
rather than pass quietly.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

import evidence_pack_recall as harness  # noqa: E402
from query import relevance as R  # noqa: E402

#: The value the direction records as the accepted RED baseline and the value the
#: shipped head-recall configuration reproduces.  Frozen as the regression floor.
BJR_ACCEPTED_RED = 3
#: The value this cycle's change reaches, measured offline from the frozen cache.
BJR_AFTER_FIX = 4


def _report():
    return harness.measure_all()


# --------------------------------------------------------------------------- #
# 1. the structural invariant that the fix restores
# --------------------------------------------------------------------------- #
def test_reserved_recall_tail_tiles_the_evidence_pack_exactly():
    """The splice is only useful if every recalled row lands inside the pack.

    Only the top ``evidence_count`` rows are hydrated with ``full_text``, so a
    recalled row past the pack is invisible to the generator while still having
    displaced whatever it pushed down. The shipped values tile the pack's tail:
    ``INSERT_AT + MAX_MOVED - 1 == EVIDENCE_PACK``.
    """
    tail_end = R.REMOTE_HEAD_RECALL_INSERT_AT + R.REMOTE_HEAD_RECALL_MAX_MOVED - 1
    assert tail_end == R.REMOTE_HEAD_RECALL_EVIDENCE_PACK, (
        f"reserved recall tail ends at rank {tail_end} but the hydrated evidence "
        f"pack is {R.REMOTE_HEAD_RECALL_EVIDENCE_PACK} rows; rows beyond it are "
        "recalled into a position the generator never sees"
    )
    assert R.REMOTE_HEAD_RECALL_INSERT_AT >= 1
    assert R.REMOTE_HEAD_RECALL_MAX_MOVED >= 4, (
        "fewer than four movable rows leaves the source index's own top "
        "authorities outside the pack (measured: 3 rows = 3/5)"
    )


def test_evidence_pack_anchor_matches_the_durable_leg_harness():
    """The anchor must be the pack the frozen path really uses, not a guess."""
    import inspect

    import ci_reality_legs

    sig = inspect.signature(ci_reality_legs.run_legs)
    assert sig.parameters["evidence_count"].default == R.REMOTE_HEAD_RECALL_EVIDENCE_PACK, (
        "REMOTE_HEAD_RECALL_EVIDENCE_PACK drifted from ci_reality_legs.run_legs; "
        "the reserved tail must be sized against the pack the generator receives"
    )
    assert sig.parameters["top_n"].default == harness.SERVED_TOP_N


# --------------------------------------------------------------------------- #
# 2. the measurement itself, with its own non-vacuity control
# --------------------------------------------------------------------------- #
def test_bjr_controlling_authorities_reach_the_evidence_pack():
    """The accepted RED leg's precondition improves 3/5 -> 4/5, offline.

    Non-vacuity is proved by the same measurement with the splice ablated: the
    count must fall, so the harness is observing the mechanism and not the pool.
    """
    bjr = next(leg for leg in _report()["legs"]
               if leg["slug"] == "business-judgment-rule")
    assert bjr["direct_total"] == 5
    assert bjr["direct_in_evidence_pack"] >= BJR_AFTER_FIX, (
        f"expected >= {BJR_AFTER_FIX}/5 frozen controlling authorities inside the "
        f"evidence pack, measured {bjr['direct_in_evidence_pack']}/5; "
        f"ranks={[ (a['decision_id'], a['served_rank']) for a in bjr['authorities'] ]}"
    )
    assert bjr["direct_in_evidence_pack"] > BJR_ACCEPTED_RED

    nc = harness.negative_control()
    assert nc["mechanism_observable"], (
        "ablating the head-recall splice did not change the measured count, so "
        "this test cannot distinguish the mechanism working from the pool "
        "happening to contain the authorities"
    )
    assert nc["ablated_in_evidence_pack"] < nc["baseline_in_evidence_pack"]


def test_the_fifth_authority_is_a_retrieval_ordering_fact_not_a_reranking_bug():
    """Freeze the ACCEPTED NEGATIVE so the failed hypothesis is not re-tried.

    ``bger_4A_62_2024`` sits far below the other four in the source index's own
    ranking for this question (measured answer-channel rank 37 against 2/3/4/8),
    i.e. outside the recall window. Measured over the frozen cache, widening the
    window to 20/25/30/35/40/50 never reaches 5/5 and at 30+ makes it *worse*
    (3/5, then 2/5), because every extra answer-channel slot is claimed by an
    off-domain federal row first. 5/5 would require outranking the source index
    on its own question, which is not a reranking defect this mechanism can fix.
    """
    bjr = next(leg for leg in _report()["legs"]
               if leg["slug"] == "business-judgment-rule")
    by_id = {a["decision_id"]: a for a in bjr["authorities"]}
    fifth = by_id["bger_4A_62_2024"]
    assert fifth["retrieved"] is True, "assumed a ranking miss"
    assert fifth["answer_channel_rank"] >= 30, (
        "if the source index now ranks the fifth authority inside the window, "
        "the recorded negative is stale and 5/5 may be reachable"
    )
    assert fifth["answer_channel_rank"] > R.REMOTE_HEAD_RECALL_REMOTE_TOP
    for other in ("bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
                  "bger_4A_603_2014"):
        assert by_id[other]["answer_channel_rank"] <= 8
    assert fifth["in_evidence_pack"] is False
    assert "bger_4A_62_2024" in bjr["ranking_miss_ids"]

    saved = R.REMOTE_HEAD_RECALL_REMOTE_TOP
    try:
        for wider in (20, 25, 30, 35, 40, 50):
            R.REMOTE_HEAD_RECALL_REMOTE_TOP = wider
            leg = harness.measure_leg("business-judgment-rule")
            assert leg["direct_in_evidence_pack"] <= BJR_AFTER_FIX, (
                f"widening the recall window to {wider} unexpectedly reached "
                f"{leg['direct_in_evidence_pack']}/5; the recorded negative is stale"
            )
    finally:
        R.REMOTE_HEAD_RECALL_REMOTE_TOP = saved
    assert saved == 15


# --------------------------------------------------------------------------- #
# 3. no regression on the other three frozen legs
# --------------------------------------------------------------------------- #
def test_other_frozen_legs_do_not_regress():
    legs = {leg["slug"]: leg for leg in _report()["legs"]}
    assert legs["petty-theft-dismissal"]["direct_in_evidence_pack"] == 1
    assert legs["corporate-criminal-liability"]["direct_in_evidence_pack"] == 2
    assert legs["rent-default"]["direct_in_evidence_pack"] == 0
    for slug, leg in legs.items():
        assert leg["cache_degraded"] is False, (
            f"{slug} measured against a degraded cache; the number is not evidence"
        )
        assert leg["served_size"] == harness.SERVED_TOP_N


def test_retrieval_miss_and_ranking_miss_are_never_collapsed():
    """``bger_4A_228_2015`` is absent from the cached petty-theft pool.

    That is a RETRIEVAL miss and no reranker can reach it; the frozen petty-theft
    gate intersects with either id, so the leg still holds. Keeping the two
    failure modes apart is what stops this instrument from being read as a
    retrieval-quality score.
    """
    legs = {leg["slug"]: leg for leg in _report()["legs"]}
    petty = legs["petty-theft-dismissal"]
    assert petty["retrieval_miss_ids"] == ["bger_4A_228_2015"]
    assert petty["ranking_miss_ids"] == [], (
        "bger_4A_177_2017 must be inside the pack; a ranking miss here is new"
    )
    assert petty["direct_retrieved"] == 1
    assert petty["direct_in_evidence_pack"] == 1


# --------------------------------------------------------------------------- #
# 4. the harness cannot drift from the gate it instruments
# --------------------------------------------------------------------------- #
def test_frozen_authority_sets_match_the_frozen_truth_gates():
    """Parse ``reality_check.py`` and require the harness to agree with it.

    The harness must never re-tune a frozen gate, so it is checked against the
    frozen source rather than trusted. Read-only: no frozen file is edited.
    """
    source = (PRODUCT / "reality_check.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals: dict[str, set[str]] = {}

    def _compared_slug(node: ast.expr) -> str | None:
        """Return the slug literal an ``if slug == "..."`` branch tests for."""
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name):
            for comp in node.comparators:
                if isinstance(node.left, ast.Name) \
                        and node.left.id == "slug" and isinstance(comp, ast.Constant) \
                        and isinstance(comp.value, str):
                    return comp.value
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "truth_gates":
            continue
        for branch in ast.walk(node):
            if not isinstance(branch, ast.If):
                continue
            slug = _compared_slug(branch.test)
            if not slug:
                continue
            literals[slug] = {n.value for n in ast.walk(branch)
                              if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "business-judgment-rule" in literals, "could not locate the frozen BJR branch"

    spec = harness.FROZEN_AUTHORITIES["business-judgment-rule"]
    gate = literals["business-judgment-rule"]
    assert set(spec["required_any"]) <= gate, (
        "the harness claims an authority the frozen gate does not name"
    )
    assert set(spec["direct"]) <= set(spec["required_any"])

    petty = harness.FROZEN_AUTHORITIES["petty-theft-dismissal"]
    assert set(petty["required_any"]) <= literals["petty-theft-dismissal"]

    corp = harness.FROZEN_AUTHORITIES["corporate-criminal-liability"]
    assert set(corp["required_any"]) <= literals["corporate-criminal-liability"]


# --------------------------------------------------------------------------- #
# 5. honest scope
# --------------------------------------------------------------------------- #
def test_harness_is_offline_and_makes_no_llm_call():
    report = _report()
    assert report["network"] is False
    assert report["llm_calls"] == 0
    assert report["mode"] == "offline_cache_only"
    assert "RECALL INTO THE HYDRATED EVIDENCE PACK" in report["claim_ceiling"], (
        "the report must state that it measures recall, not citation"
    )
    for leg in report["legs"]:
        assert leg["question_sha256"], "every leg must pin the exact question used"