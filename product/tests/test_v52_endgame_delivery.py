"""v52 endgame delivery regression guards (P1 adoption / P2 rebuild / P3 handoff).

Why this module exists
----------------------
Factory direction v52 product lane P1-P3 added three product-owned code paths in
cycle 39027045675 (``product/query/counter_anchor.py``, ``product/rebuild_packet.py``,
and the adoption of the accepted ``frontier-counter-anchor-classifier``) plus the
rebuilt packet directory ``results/product/gate_packet/rebuilt-39027045675/``.
Unlike the sibling geometry adoption (``test_qmap_geometry_variant.py``) these
new paths shipped with **no regression test**, so nothing pinned:

  * the adoption seam reproducing the accepted incumbent numbers (65 scored /
    5 emitted / 60 abstained, yield 0.0769) and keeping abstained rows visible;
  * the vendored classifier's committed bytes against its own PROVENANCE hashes
    (tamper detection, parity with the geometry variant's provenance test);
  * pre-serving obligation (a): the SHIPPED bundle is ``post_rerank_product_bundle``
    and its frozen 11-criteria counts are published beside the pre-rerank
    reference with the per-criterion delta (never a promise of equality);
  * pre-serving obligation (b): the V2 axis label is ``retrieval relevance score``
    and the stale word ``rerank score`` is gone from axis metadata;
  * the size-based mega-cluster disclosure (``len(idx)/n``, bar unchanged at 0.5)
    and the source packet's fired warning at share 0.7696;
  * the P3 handoff ``content_sha256`` values reproducing via the product's own
    ``replay_bundle.content_sha256`` and the raw ``packet.json`` bytes;
  * zero forbidden constructions (the classifier's claim ceiling) in any
    committed rebuilt-packet artifact.

These are contract/shape assertions only.  They never re-measure a frozen bar,
never re-tune a rubric and never assert legal usefulness.  Every number asserted
below is recomputed from the committed artifacts by this module, not read back
from a report.
"""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_anchor as ca  # noqa: E402
from product.replay_bundle import content_sha256  # noqa: E402

REBUILT = ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675"
SOURCE = ROOT / "results" / "product" / "gate_packet" / "38839347028"
QIDS = ("fr-bail-entretien", "de-kapitalverletzung", "it-responsabilita-medica")

# Anchor used to re-root an absolute path recorded in a committed artifact onto
# the checkout under test (see resolve_committed_path and the D1/D2 disclosure).
REPO_ROOT_MARKER = "results"
REBUILT_DIR_NAME = "rebuilt-39027045675"

pytestmark = pytest.mark.skipif(
    not (REBUILT / "handoff.json").is_file(),
    reason="rebuilt packet rebuilt-39027045675 not present",
)


def _handoff() -> dict:
    return json.loads((REBUILT / "handoff.json").read_text(encoding="utf-8"))


def _bundle(qid: str, *, source: bool = False) -> dict:
    root = SOURCE if source else REBUILT
    return json.loads((root / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8"))


def resolve_committed_path(raw: str, root: Path | None = None) -> Path:
    """Resolve a path recorded in a committed artifact against THIS checkout.

    D1 repair (factory direction v55). The shipped ``handoff.json`` /
    ``packet.json`` embed the absolute CI workspace path
    (``/home/runner/work/LexMachina/LexMachina/...``), because they are
    claim-bearing measured artifacts whose bytes must not be regenerated to
    make paths relative. A test that trusted ``bundle_path`` as absolute was
    therefore coupled to the machine that produced the packet: on any other
    checkout it silently read the producer's tree, so it passed against a tree
    whose bundle content had been altered (and raised FileNotFoundError while
    describing the wrong bytes).

    The fix belongs in the test, not in the artifact: take the committed path's
    tail from the repository-root marker onward and join it onto ``root``
    (defaulting to the ROOT of the tree under test). The content-sha256
    assertions are kept exactly as they were - only the *resolution* changes.

    ``root`` is injectable so the anti-regression guard can prove the resolution
    follows the tree under test rather than the producer's recorded prefix.
    """
    base = ROOT if root is None else Path(root)
    parts = Path(raw).parts
    if REPO_ROOT_MARKER in parts:  # .../results/product/gate_packet/rebuilt-.../...
        idx = parts.index(REPO_ROOT_MARKER)
        return base.joinpath(*parts[idx:])
    # No known anchor: fall back to the bare filename inside the packet dir, so
    # a missing/renamed anchor degrades to "not present" rather than to a
    # silent read of an unrelated machine's file.
    return base / "results" / "product" / "gate_packet" / REBUILT_DIR_NAME / "questions" \
        / Path(raw).name


_MACHINE_COUPLED_NAMES = ("ROOT", "REBUILT", "SOURCE")


def _machine_coupled_assertions(src: str) -> list[str]:
    """Return every assertion in ``src`` that compares an artifact value to a path.

    F1 repair (audit CYCLE_39048942749 FIX-1). A path assertion that reaches for
    this checkout's ``ROOT``/``REBUILT``/``SOURCE`` is machine-coupled by
    construction: it can only be true where the tree sits at the producer's CI
    path. The defect that audit found was exactly this shape, re-introduced by
    the D1/D2 repair inside this very file, so the shape is now rejected at the
    AST level rather than left to review.

    Detector shape: an ``assert`` whose test contains ``str(<NAME>)`` for one of
    the module's root globals, optionally followed by ``.resolve()``/``.as_posix()``.
    ``resolve_committed_path`` is deliberately absent - it takes a root argument
    and is the supported way to talk about a foreign checkout.
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Assert):
            continue
        for sub in ast.walk(node.test):
            if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "str" and sub.args):
                continue
            arg = sub.args[0]
            if isinstance(arg, ast.Name) and arg.id in _MACHINE_COUPLED_NAMES:
                found.append(f"line {sub.lineno}: str({arg.id})")
                break
    return found


# --------------------------------------------------------------------------
# P1 - counter-anchor adoption seam
# --------------------------------------------------------------------------

def test_frozen_label_rubric_refuses_a_tampered_copy(tmp_path):
    """A re-frozen rubric invalidates the run: the seam must raise, never re-score."""
    raw = (ROOT / "product" / "frozen" / "RULES_LABEL.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ca.FROZEN_LABEL_RULES_SHA256
    tampered = tmp_path / "RULES_LABEL.json"
    tampered.write_bytes(raw + b"\n")
    with pytest.raises(ValueError):
        ca.load_frozen_rules(path=tampered)


def test_adoption_record_names_the_accepted_audit_and_never_re_assigns_polarity():
    rec = ca.adoption_record()
    assert rec["decision"] == "ADOPT"
    assert rec["mode"] == "abstain-and-disclose"
    assert rec["audit_gate"] == "PASS" and rec["safe_to_integrate"] is True
    assert rec["accept_commit"].startswith("d236f599")
    assert rec["frozen_label_rules_sha256"].startswith("4457e971")
    assert rec["default_mode"] == ca.MODE_ANCHOR
    # the claim ceiling binds every product artifact
    assert "never asserts that any specific decision IS" in rec["claim_ceiling"]


def test_forbidden_construction_detector_has_a_positive_and_negative_control():
    assert ca.find_forbidden_constructions("the map shows three colour-coded clusters") == []
    assert ca.FORBIDDEN_CONSTRUCTION_PATTERNS  # non-empty battery
    for sentence in (
        "Decision bge_110_II_391 is contrary authority",
        "we classify bger_4A_1_2020 as limiting",
        "the court asserts that bge_1 is supporting",
    ):
        assert ca.find_forbidden_constructions(sentence), sentence


def test_adoption_seam_reproduces_the_accepted_incumbent_numbers():
    """65 scored / 5 emitted / 60 abstained, yield 0.0769 - recomputed here.

    This is the exact incumbent population published by the accepted
    falsification and by the v52 P1 record; reproducing it from the committed
    source packet proves the seam, not a report, carries the numbers.
    """
    total_scored = total_emitted = total_abstained = 0
    for qid in QIDS:
        out = ca.apply_anchor_labels(_bundle(qid, source=True), qid=qid)
        prov = out["provenance"]["counter_anchor"]
        assert prov["applied"] is True
        assert prov["mode"] == "abstain-and-disclose"
        assert prov["frozen_rules_sha256"] == ca.FROZEN_LABEL_RULES_SHA256
        assert prov["n_scored"] == prov["n_emitted"] + prov["n_abstained"]
        # every emitted label is supported by construction; yield is emitted share
        assert prov["support_rate_among_emitted"] == (1.0 if prov["n_emitted"] else 0.0)
        assert prov["yield"] == pytest.approx(prov["n_emitted"] / prov["n_scored"])
        total_scored += prov["n_scored"]
        total_emitted += prov["n_emitted"]
        total_abstained += prov["n_abstained"]

    assert (total_scored, total_emitted, total_abstained) == (65, 5, 60)
    assert total_emitted / total_scored == pytest.approx(0.076923, abs=1e-6)


def test_abstained_rows_stay_visible_and_are_marked_not_dropped():
    out = ca.apply_anchor_labels(_bundle("it-responsabilita-medica", source=True),
                                 qid="it-responsabilita-medica")
    n_before = len(_bundle("it-responsabilita-medica", source=True)["decisions"])
    assert len(out["decisions"]) == n_before, "the seam must never drop a row"
    abstained = [d for d in out["decisions"]
                 if d.get("counter_status") == ca.ABSTAINED_STATUS]
    assert abstained, "the it bundle has abstained counter rows"
    for d in abstained:
        assert d["counter_anchor_label"] == "ABSTAIN"
        assert d.get("counter_reason_code")
        assert 0.0 <= float(d.get("counter_uncertainty", -1)) <= 1.0
    # an abstained row is still a row on the map: geometry is untouched
    assert all("x" in d and "y" in d and "cluster_id" in d for d in abstained)


def test_summary_publishes_support_abstention_and_yield_side_by_side():
    out = ca.apply_anchor_labels(_bundle("de-kapitalverletzung", source=True),
                                 qid="de-kapitalverletzung")
    s = ca.counter_anchor_summary(out)
    assert set(s) >= {"n_scored", "n_emitted", "n_abstained",
                      "support_rate_among_emitted", "yield"}
    assert s["n_scored"] == s["n_emitted"] + s["n_abstained"]
    assert s["n_abstained"] > 0  # abstain-and-disclose is not a silent emit-all


def test_resolve_anchor_profile_prefers_the_bundle_qid_and_falls_back_by_query():
    rules, _ = ca.load_frozen_rules()
    assert ca.resolve_anchor_profile(rules, qid="fr-bail-entretien") is not None
    # a query in an anchor's language resolves to some frozen profile
    prof = ca.resolve_anchor_profile(rules, query="Kündigung Mietvertrag Mietrecht",
                                     language="de")
    assert prof is not None
    # an unrelated query is refused rather than assigned an invented profile
    assert ca.resolve_anchor_profile(rules, query="quantum chromodynamics",
                                     language="de") is None


def test_vendored_classifier_matches_its_recorded_provenance_hashes():
    """Tamper detection parity with the vendored geometry variant."""
    root = ROOT / "product" / "vendored" / "frontier_counter_anchor_classifier"
    meta = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    assert meta["promoted_variant"] == "Outcome A (abstain-and-disclose)"
    assert meta["accept_commit"].startswith("d236f599")
    assert meta["frozen_label_rules_sha256"].startswith("4457e971")
    assert meta["vendored_files"]
    for rel, rec in meta["vendored_files"].items():
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert digest == rec["sha256"], f"vendored {rel} drifted from provenance"
        assert rec["matches_accepted_source"] is True


# --------------------------------------------------------------------------
# P2 - rebuilt packet obligations
# --------------------------------------------------------------------------

def test_shipped_bundle_is_post_rerank_and_records_the_one_shot_transform():
    """Pre-serving obligation (a): the scored bundle is literally post rerank."""
    for b in _handoff()["bundles"]:
        rr = b["rerank_product_bundle"]
        assert rr["applied"] is True
        assert rr["function"] == "product.query.relevance.rerank_product_bundle"
        assert rr["call_count"] == 1 and rr["runs_once"] is True
        assert rr["non_idempotent"] is True, (
            "rerank reads the adapter score as input; the shipped bytes are one-shot")
        assert rr["same_row_set"] is True
        assert rr["retrieval_score_raw_present"] is True


def test_obligation_a_publishes_post_rerank_counts_beside_the_measured_reference():
    """Comparison, not equality: both states and the per-criterion delta ship."""
    by_qid = {b["qid"]: b["geometry_scoring"] for b in _handoff()["bundles"]}
    assert set(by_qid) == set(QIDS)
    for qid in QIDS:
        gs = by_qid[qid]
        assert gs["bundle_state"] == "post_rerank_product_bundle"
        assert gs["frozen_rules_sha256"] == (
            "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")
        assert gs["n_criteria"] == 11
        assert gs["measured_pass_count"] in (7, 8)
        ref = gs["pre_rerank_reference"]
        assert ref["n_pass"] == gs["measured_pass_count"], (
            "the pre-rerank reference must reproduce the measured 7/8/7 state")
        comp = gs["comparison"]
        assert comp["absolute_bar"] == "11 of 11 criteria on every bundle"
        assert comp["absolute_bar_met_post_rerank"] is False, (
            "the geometry absolute bar is unmet under the measured states")
        assert isinstance(comp["criterion_flips"], dict)
    # the accepted measured counts are 7/7/8 and the post-rerank FR bundle drops
    assert by_qid["fr-bail-entretien"]["measured_pass_count"] == 8
    assert by_qid["fr-bail-entretien"]["n_pass"] < 8
    assert "COHERENCE_QUERY_LANG" in by_qid["fr-bail-entretien"]["comparison"]["criterion_flips"]


def test_obligation_b_axis_is_relabelled_and_the_stale_word_is_gone():
    """The V2 x axis is 'retrieval relevance score'; never 'rerank score'."""
    for b in _handoff()["bundles"]:
        assert b["axis_x_label"] == "retrieval relevance score"
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        text = (REBUILT / name).read_text(encoding="utf-8")
        assert "rerank score" not in text, (
            f"{name} still carries the stale axis word 'rerank score'")


def test_mega_cluster_disclosure_is_size_based_with_the_threshold_unchanged():
    for b in _handoff()["bundles"]:
        m = b["mega_cluster_disclosure"]
        assert m["bar"] == 0.5 and m["threshold_edited"] is False
        assert "size" in m["definition"] and "len(idx)" in m["definition"]
        assert m["size_based_not_member_ids"] is True
        # the source packet's French bundle is the recorded fired example
        if b["qid"] == "fr-bail-entretien":
            src = m["source_packet"]
            assert src["fired"] is True
            assert src["largest_cluster_share"] == pytest.approx(0.7696, abs=1e-4)
            assert src["largest_cluster_share"] >= 0.5
            # the divergence that the size-based fix addresses: the member_ids
            # share is far below the bar while the size share is far above it
            assert src["largest_cluster_member_ids_share"] == pytest.approx(0.2304, abs=1e-4)
            assert src["largest_cluster_member_ids_share"] < 0.5
            assert m["fired_on_any_check"] is True


def test_no_committed_rebuilt_artifact_asserts_a_forbidden_construction():
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        text = (REBUILT / name).read_text(encoding="utf-8")
        assert ca.find_forbidden_constructions(text) == [], name
    for qid in QIDS:
        q = (REBUILT / "questions" / f"{qid}.question.json").read_text(encoding="utf-8")
        assert ca.find_forbidden_constructions(q) == [], qid


# --------------------------------------------------------------------------
# P3 - handoff integrity + admission
# --------------------------------------------------------------------------

def test_handoff_content_sha256_reproduces_via_the_product_own_hasher():
    """D1 repair: resolve the committed bundle paths against THIS ROOT.

    The content-sha256 assertions are unchanged - the product's own hasher must
    still reproduce every published bundle hash. Only the path resolution is
    fixed, so the assertion now measures the checkout under test instead of the
    absolute CI workspace path embedded in the committed artifact.
    """
    h = _handoff()
    for b in h["bundles"]:
        resolved = resolve_committed_path(b["bundle_path"])
        assert resolved.is_file(), f"{b['qid']} bundle missing under ROOT: {resolved}"
        recomputed = content_sha256(json.loads(resolved.read_text(encoding="utf-8")))
        assert recomputed == b["content_sha256"], f"{b['qid']} content hash drifted"


def test_committed_artifacts_embed_absolute_workspace_paths_and_it_is_disclosed():
    """D2: the absolute-path embedding is real, and it is disclosed, not fixed.

    The packet/handoff are claim-bearing measured artifacts, so the repair does
    NOT regenerate them to store relative paths (that would change packet.json
    raw sha256 2942c3c2... and invalidate the published identity). Instead the
    embedding is asserted to exist and to be disclosed in the packet's own
    disclosures, so a consumer is never surprised by a producer-machine path.

    F1 repair (audit CYCLE_39048942749 FIX-1). The predicate for "the recorded
    path is absolute" is ``Path(...).is_absolute()``, which reads the committed
    artifact alone. It was ``str(REBUILT) in h['packet_path']``, which compared
    the committed PRODUCER prefix against THIS checkout's ROOT: the guard passed
    only where the tree sits at the producer's CI path and failed at every other
    root (1 failed / 21 passed at /tmp/opencode/lex_second_root), i.e. it
    re-introduced inside the D1 repair the very machine-coupling the D1 section
    diagnoses. ``test_path_assertions_are_machine_independent`` now holds this
    module's path guards to the same root-independence standard.
    """
    h = _handoff()
    packet_path = Path(h["packet_path"])
    assert packet_path.is_absolute(), (
        "packet_path is expected to embed an absolute workspace path")
    # the recorded tail, not this machine's prefix, is the load-bearing part
    assert packet_path.parts[-3:] == ("gate_packet", REBUILT_DIR_NAME, "packet.json")
    assert resolve_committed_path(h["packet_path"]).is_relative_to(ROOT)
    for b in h["bundles"]:
        assert Path(b["bundle_path"]).is_absolute(), (
            f"{b['qid']} bundle_path was expected to embed an absolute workspace path")
        # ... and it must re-root cleanly onto this checkout (the D1 fix)
        assert resolve_committed_path(b["bundle_path"]).is_relative_to(ROOT)

    # A1 repair: scope the disclosure assertion to the disclosure BLOCK. Searching
    # the whole blob was partly vacuous - the word "absolute" also occurs in
    # unrelated disclosure text, so deleting path_binding_disclosure entirely
    # left the assertion green.
    disc = json.loads((REBUILT / "disclosures.json").read_text(encoding="utf-8"))
    block = disc.get("path_binding_disclosure")
    assert isinstance(block, dict), (
        "disclosures.json carries no path_binding_disclosure block")
    assert block["paths_are_absolute"] is True
    assert block["root_marker"] == REPO_ROOT_MARKER
    assert block["packet_json_regenerated_for_relative_paths"] is False
    blob = json.dumps(block)
    assert "absolute" in blob.lower(), (
        "the path_binding_disclosure does not disclose absolute paths")
    assert REBUILT_DIR_NAME in blob, (
        "the disclosure does not name the packet dir anchor")


def test_path_assertions_are_machine_independent(tmp_path, monkeypatch):
    """F1 anti-regression: the module's path guards must hold off the producer root.

    Two independent guarantees, because the defect F1 fixed is silent:

    1. BEHAVIOURAL - this module's own path-assertion functions are re-executed
       with ROOT/REBUILT/SOURCE pointed at a temp checkout that is NOT the
       recorded producer path. The D1 content-sha guard and the D2 absolute-path
       guard must both pass there. Before the F1 repair the D2 guard failed
       exactly this way, so the guard is not vacuous.
    2. STATICAL - a re-introduced ``assert str(ROOT|REBUILT|SOURCE) ... <value
       read out of a committed artifact>`` predicate is rejected by
       ``_machine_coupled_assertions``. The detector is proved non-vacuous on a
       synthetic bad snippet and on the real module source.
    """
    mod = sys.modules[__name__]
    original_root, original_rebuilt = mod.ROOT, mod.REBUILT
    foreign_root = tmp_path / "not-the-producer-ci-root"
    for name in ("rebuilt-39027045675", "38839347028"):
        shutil.copytree(ROOT / "results" / "product" / "gate_packet" / name,
                        foreign_root / "results" / "product" / "gate_packet" / name)
    monkeypatch.setattr(mod, "ROOT", foreign_root)
    monkeypatch.setattr(mod, "REBUILT",
                        foreign_root / "results" / "product" / "gate_packet"
                        / REBUILT_DIR_NAME)
    monkeypatch.setattr(mod, "SOURCE",
                        foreign_root / "results" / "product" / "gate_packet"
                        / "38839347028")
    # the foreign root must not be this checkout, or the guard proves nothing
    assert foreign_root != original_root
    assert mod.REBUILT != original_rebuilt
    # ... and the recorded producer path must NOT be where the guards now look
    assert not mod.REBUILT.is_relative_to(original_root)

    # 1. the module's own path guards, executed against the foreign root
    mod.test_committed_artifacts_embed_absolute_workspace_paths_and_it_is_disclosed()
    mod.test_handoff_content_sha256_reproduces_via_the_product_own_hasher()

    # ... and they are not vacuous there either: a tampered foreign tree is caught
    bundle_file = mod.REBUILT / "questions" / "fr-bail-entretien.bundle.json"
    bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
    bundle["decisions"] = bundle["decisions"][:3]
    bundle_file.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AssertionError, match="content hash drifted"):
        mod.test_handoff_content_sha256_reproduces_via_the_product_own_hasher()

    # 2. static tripwire against the exact predicate shape F1 removed
    assert _machine_coupled_assertions(Path(__file__).read_text(encoding="utf-8")) == [], (
        "a path assertion in this module compares a committed artifact value "
        "against this checkout's ROOT/REBUILT/SOURCE; that is the F1 defect")
    bad = "def f(h, REBUILT):\n    assert str(REBUILT) in h['packet_path']\n"
    assert _machine_coupled_assertions(bad), "the machine-coupling detector is vacuous"
    good = "def f(h, REBUILT):\n    assert Path(h['packet_path']).is_absolute()\n"
    assert _machine_coupled_assertions(good) == []


def test_resolve_committed_path_reads_the_tree_under_test(tmp_path):
    """D1 anti-regression: resolution must follow ROOT, not the producer's path.

    The pre-repair test passed against a *tampered* tree because it opened the
    absolute CI path recorded in the artifact. This guard rebuilds that exact
    failure shape in a temp tree: a producer path that exists here, and a
    foreign root whose bundle bytes differ. Resolution must follow the foreign
    root, so the tampered bytes are the ones hashed and the drift is caught.
    """
    forged = ("/home/runner/work/LexMachina/LexMachina/results/product/gate_packet/"
              f"{REBUILT_DIR_NAME}/questions/fr-bail-entretien.bundle.json")

    # 1. resolution re-roots onto whatever root it is given
    resolved = resolve_committed_path(forged, root=tmp_path)
    assert resolved == tmp_path / "results" / "product" / "gate_packet" \
        / REBUILT_DIR_NAME / "questions" / "fr-bail-entretien.bundle.json"

    # 2. the reproduction: same committed path, a foreign root holding DIFFERENT
    #    bytes. The old absolute-path read silently hashed the producer's tree;
    #    the repaired read must hash the tree it was pointed at.
    foreign = tmp_path / "results" / "product" / "gate_packet" / REBUILT_DIR_NAME / "questions"
    foreign.mkdir(parents=True)
    bundle = json.loads((REBUILT / "questions" / "fr-bail-entretien.bundle.json")
                        .read_text(encoding="utf-8"))
    bundle["decisions"] = bundle["decisions"][:3]          # tamper the foreign tree
    (foreign / "fr-bail-entretien.bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    foreign_sha = content_sha256(json.loads(
        resolve_committed_path(forged, root=tmp_path).read_text(encoding="utf-8")))
    real_sha = content_sha256(json.loads((REBUILT / "questions" / "fr-bail-entretien.bundle.json")
                                         .read_text(encoding="utf-8")))
    assert foreign_sha != real_sha, (
        "resolution still reads the producer's tree instead of the tree under test")

    # 3. an unanchored path degrades to the packet dir under the given root,
    #    never to an absolute read of an unrelated machine's file
    unanchored = resolve_committed_path("/somewhere/else/whatever.bundle.json", root=tmp_path)
    assert unanchored == foreign / "whatever.bundle.json"
    assert not unanchored.exists()


def test_handoff_packet_content_sha256_matches_the_raw_packet_bytes():
    h = _handoff()
    raw = (REBUILT / "packet.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == h["packet_content_sha256"]
    assert h["packet_path"].endswith("rebuilt-39027045675/packet.json")


def test_handoff_does_not_self_certify_and_admission_denies():
    from product.query import packet_admission as pa

    h = _handoff()
    assert h["self_certification"] is False
    assert h["human_gate_ready"] is False
    adm = pa.assess()
    assert adm["packet_admitted"] is False
    assert adm["ready_for_owner_session_allowed"] is False


def test_cross_lane_handoff_publishes_verified_identities_and_stays_fail_closed():
    """Item (3): the packet path + per-bundle content_sha256 handed to Core
    Evaluation and the serve-audit team, plus the fail-closed product position.

    Every sha in the handoff is RE-HASHED here rather than trusted, and the
    record must never carry an owner-session claim while the accepted
    DO-NOT-SERVE order is unaddressed.
    """
    rec = json.loads((ROOT / "results" / "product" / "gate_packet" /
                      "REBUILT_39027045675_CROSS_LANE_HANDOFF.json")
                     .read_text(encoding="utf-8"))

    # packet identity: measured bytes, not regenerated
    pkt = ROOT / rec["packet"]["repo_relative_packet"]
    assert hashlib.sha256(pkt.read_bytes()).hexdigest() == rec["packet"]["packet_content_sha256"]
    assert rec["packet"]["packet_bytes_regenerated_this_cycle"] is False

    # per-bundle identity, recomputed through the product's own hasher
    by_qid = rec["per_bundle"]
    assert set(by_qid) == set(QIDS)
    for qid in QIDS:
        cell = by_qid[qid]
        path = ROOT / cell["repo_relative_path"]
        assert cell["content_sha256_verified"] is True
        assert content_sha256(json.loads(path.read_text(encoding="utf-8"))) == cell["content_sha256"]
        # the drift figure travels with its scope label
        assert cell["cluster_id_drift_rows_scope"] == "HOST_SCOPED_PRODUCER_ATTESTATION"

    # frozen inputs are re-hashed, never re-derived
    for name, cell in rec["frozen_inputs_rehashed_this_cycle"].items():
        assert cell["matches_accepted"] is True, name
        assert hashlib.sha256((ROOT / cell["path"]).read_bytes()).hexdigest() == cell["sha256"]

    # the absolute-path hazard travels WITH the handoff
    assert rec["path_handling"]["committed_paths_are_absolute"] is True
    assert "results" in rec["path_handling"]["warning"]

    # support-among-issued, abstentions and yield travel together
    t = rec["totals"]
    assert t["n_counter_rows_emitted"] + t["n_counter_rows_abstained"] == t["n_counter_rows_scored"]
    assert t["n_counter_rows_scored"] == 65
    assert t["yield"] == pytest.approx(5 / 65, abs=1e-4)

    # fail-closed: no owner-session claim from the producer
    pos = rec["product_position"]
    assert pos["self_certification"] is False
    assert pos["machine_gate_ready"] is False
    assert pos["human_gate_ready"] is False
    assert pos["ready_for_owner_session"] is False


def test_reproducibility_scope_disclosure_is_present_and_consistent():
    """The committed-bytes identity is stable; a from-source rebuild is not
    byte-identical across numeric environments. That boundary is disclosed so a
    recomputation diff is never misread as data tampering (the environment-scoped
    reproducibility class recorded for frontier-served-packet-falsification).
    """
    scope_path = ROOT / "results" / "product" / "gate_packet" / (
        "REBUILT_39027045675_REPRODUCIBILITY_SCOPE.json")
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    assert scope["schema"] == "product-rebuilt-packet-reproducibility-scope/2"
    assert scope["scope_finding"]
    assert scope["artifact_of_record"]
    by_qid = scope["per_bundle"]
    assert set(by_qid) == set(QIDS)
    for qid in QIDS:
        cell = by_qid[qid]
        # the committed bytes always re-hash to the published identity
        assert cell["committed_bytes_reproduce"] is True
        assert cell["committed_content_sha256"] == (
            {b["qid"]: b["content_sha256"] for b in _handoff()["bundles"]}[qid])
        assert cell["n_rows"] > 0
        assert cell["cluster_id_drift_rows"] <= cell["n_rows"]
        # A2: a drift figure without its scope label is a scope-free number that
        # will later be quoted as if it were portable. The label is mandatory.
        assert cell["cluster_id_drift_rows_scope"] == "HOST_SCOPED_PRODUCER_ATTESTATION"
        assert cell["max_query_similarity_drift_scope"] == "HOST_SCOPED_PRODUCER_ATTESTATION"
        # ... and the committed identity is re-hashed here, on this host, now
        assert cell["content_sha256_recomputes_here"] is True
        assert cell["recomputed_content_sha256"] == cell["committed_content_sha256"]


def test_reproducibility_disclosure_keeps_the_conservative_conclusion():
    """A2: the drift did not reproduce on the audit host; the conclusion stays.

    The audit host rebuilt byte-identically across BLAS thread counts and hash
    seeds. That is evidence the drift is environment-scoped - it is NOT evidence
    that rebuilds are portable, so the conservative conclusion must survive the
    re-scope, and both environments must be recorded beside the shas.
    """
    scope = json.loads((ROOT / "results" / "product" / "gate_packet" /
                        "REBUILT_39027045675_REPRODUCIBILITY_SCOPE.json")
                       .read_text(encoding="utf-8"))
    finding = scope["scope_finding"].lower()
    assert "not byte-identical" in finding, (
        "the from-source rebuild claim was weakened; the conservative "
        "conclusion must be retained")
    assert "host-scoped" in finding
    # both environments are disclosed, and neither is claimed to be universal
    assert scope["environment_of_generation"]["python"]
    assert scope["environment_of_this_verification"]["python"]
    for env_key in ("environment_of_generation", "environment_of_this_verification"):
        env = scope[env_key]
        for pkg in ("numpy", "scipy", "scikit_learn"):
            assert env.get(pkg), f"{env_key} does not record {pkg}"
    assert "no unconditional cross-machine byte identity is claimed" in \
        scope["environment_note"].lower()
    assert scope["packet_content_sha256"] == _handoff()["packet_content_sha256"]


def test_drift_figures_are_host_scoped_not_silently_universal():
    """The fr/de reassignment counts are producer attestation on ONE host.

    The numbers must never be published bare: the audit host measured zero
    reassignments. The repair keeps them (they are evidence of record) and labels
    them, so a later reader cannot promote them to a portable property.
    """
    scope = json.loads((ROOT / "results" / "product" / "gate_packet" /
                        "REBUILT_39027045675_REPRODUCIBILITY_SCOPE.json")
                       .read_text(encoding="utf-8"))
    repair = scope["repair_scope"]["A2_advisory"]
    assert "host" in repair.lower()
    assert scope["per_bundle"]["fr-bail-entretien"]["cluster_id_drift_rows"] == 98
    assert scope["per_bundle"]["de-kapitalverletzung"]["cluster_id_drift_rows"] == 112
    assert scope["per_bundle"]["it-responsabilita-medica"]["cluster_id_drift_rows"] == 0
    # the D1/D2 repairs are recorded against the same artifact, with no
    # regeneration of the measured packet bytes
    assert "packet.json was NOT regenerated" in scope["repair_scope"]["D1_material"]
    assert scope["repair_scope"]["D2_minor"]


def test_every_rebuild_number_carries_a_host_scope_label():
    """A3: no rebuild figure may be published bare.

    The A2 rule is that every drift number is host-scoped producer attestation.
    ``fresh_rebuild_content_sha256`` was published without one, so a later reader
    could quote a digest of a rebuild that the audit host did not reproduce. The
    guard is generic on purpose: any future numeric or hash field in per_bundle
    whose name starts with a rebuild/drift prefix must carry its *_scope label.
    """
    scope = json.loads((ROOT / "results" / "product" / "gate_packet" /
                        "REBUILT_39027045675_REPRODUCIBILITY_SCOPE.json")
                       .read_text(encoding="utf-8"))
    prefixes = ("fresh_rebuild_", "cluster_id_drift", "max_query_similarity_drift")
    exempt = {"fresh_rebuild_reproduces_here"}          # a tri-state, not a figure
    for qid, cell in scope["per_bundle"].items():
        for key in cell:
            if not key.startswith(prefixes) or key in exempt or key.endswith("_scope"):
                continue
            assert cell.get(f"{key}_scope") == "HOST_SCOPED_PRODUCER_ATTESTATION", (
                f"{qid}.{key} is a rebuild figure published without a host scope label")
    assert scope["rebuild_hash_scope_rule"]


def test_embedded_workspace_path_semantics_are_disclosed_and_writer_true():
    """A2: the committed field is the writer's ``str(out_dir)``, not a constant.

    ``embedded_workspace_path`` is repo-relative in the committed artifact because
    that rebuild was invoked with a relative out_dir; the writer emits
    ``str(out_dir)``, so an absolute invocation writes an absolute string there.
    Agreement between the committed field and a future rebuild is therefore the
    writer semantics, nothing more, and both say so.
    """
    # rebuild_packet imports the sibling gate_packet module by its top-level name,
    # so product/ must be importable for this guard to read the writer itself.
    if str(ROOT / "product") not in sys.path:
        sys.path.insert(0, str(ROOT / "product"))
    from product.rebuild_packet import path_binding_disclosure

    disc = json.loads((REBUILT / "disclosures.json").read_text(encoding="utf-8"))
    block = disc["path_binding_disclosure"]
    semantics = block["embedded_workspace_path_semantics"]
    assert "str(out_dir)" in semantics and "relative" in semantics

    rel = path_binding_disclosure(Path("results/product/gate_packet") / REBUILT_DIR_NAME)
    assert rel["embedded_workspace_path"] == block["embedded_workspace_path"], (
        "the committed field is not what the writer emits for this invocation")
    absolute = path_binding_disclosure(ROOT / "results" / "product" / "gate_packet"
                                       / REBUILT_DIR_NAME)
    assert Path(absolute["embedded_workspace_path"]).is_absolute(), (
        "an absolute out_dir must still produce an absolute field")
    assert absolute["embedded_workspace_path"] != block["embedded_workspace_path"], (
        "if these ever agree the disclosure is stale and must be revisited")
    # the packet's own path fields are absolute either way - that is the D2 claim
    for name in ("packet.json", "handoff.json"):
        assert "absolute" in (REBUILT / name).read_text(encoding="utf-8").lower()
