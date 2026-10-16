"""Offline tests for the frontier-map-semantics harness (no network, no /tmp)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
PKG = HERE / ".." / ".." / ".." / "frontier" / "frontier-map-semantics"
RULES = Path("results/frontier/frontier-map-semantics/RULES.json")


def _synth_bundle(path: Path):
    # 24 rows: 12 DE jurisprudence texts, 12 FR tenancy texts, one pending shell
    de = ("Fürsorgepflicht des Arbeitgebers Arbeitsverhältnis Kündigung "
          "missbräuchliche Entlassung Lohnfortzahlung ")
    fr = ("bail à loyer résiliation défaut entretien grave négligence loyer ")
    de_extra = ["betrieb", "vertrag", "schutz", "pflichtverletzung", "abfindung",
                "zeugnis", "überstunden", "ferien", "lohn", "frist", "klage", "gericht"]
    fr_extra = ["congé", "tribunal", "juge", "dégât", "réparation", "terme",
                "dépôt", "plainte", "cour", "droit", "cause", "dommage"]
    decs, clusters = [], []
    for i in range(12):
        decs.append({"decision_id": f"de_{i}", "language": "de", "rank": i + 1,
                     "score": 100 - i, "cluster_id": 0, "x": 0.1 + 0.01 * i,
                     "y": 0.1, "is_outlier": i == 11, "title": f"de {i}",
                     "regeste": "", "snippet": de, "full_text": (de + de_extra[i] + " ") * 8,
                     "citation": f"DE {i}", "detail_status": "search_hit",
                     "full_text_status": "full", "counter_status": "none"})
    for i in range(12):
        decs.append({"decision_id": f"fr_{i}", "language": "fr", "rank": 13 + i,
                     "score": 80 - i, "cluster_id": 1, "x": -0.5,
                     "y": -0.4 - 0.01 * i, "is_outlier": False, "title": f"fr {i}",
                     "regeste": "", "snippet": fr, "full_text": (fr + fr_extra[i] + " ") * 8,
                     "citation": f"FR {i}", "detail_status": "search_hit",
                     "full_text_status": "full", "counter_status": "none"})
    bundle = {"bundle_version": "test/1",
              "query": "Fürsorgepflicht des Arbeitgebers bei Kündigung",
              "decisions": decs,
              "clusters": [{"cluster_id": 0, "label": "fürsorgepflicht, arbeitgebers, kündigung",
                            "size": 12, "member_ids": [f"de_{i}" for i in range(12)]},
                           {"cluster_id": 1, "label": "bail, loyer, résiliation",
                            "size": 12, "member_ids": [f"fr_{i}" for i in range(12)]}],
              "relations": [{"source": "de_0", "target": "de_1", "kind": "citation",
                             "direction": "outgoing", "confidence": 0.9,
                             "seed_decision_id": "de_0", "mention_count": 1.0}
                            for _ in range(11)]}
    path.write_text(json.dumps(bundle, ensure_ascii=False))
    return str(path)


def _run_cli(bundle, outdir, key="de-kapitalverletzung"):
    env = {"PYTHONPATH": str(PKG), "PATH": "/usr/bin:/bin"}
    cmd = [sys.executable, "-m", "frontier_map_semantics.cli",
           "--bundle", bundle, "--out", outdir,
           "--rules", str(RULES), "--bundle-key", key]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(Path(outdir, "report.json").read_text())


def test_report_schema_and_frozen_bars(tmp_path):
    rep = _run_cli(_synth_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    rules = json.loads(RULES.read_text())
    assert rep["n_decisions"] == 24
    assert set(rep["criteria"]) == {"COHERENCE_QUERY_LANG", "COHERENCE_QUERY_TERM",
                                    "PROJ_RANK", "PROJ_SPEARMAN", "PROJ_KNN10",
                                    "STRUCTURE_LARGEST", "STRUCTURE_SEP",
                                    "LABEL_CONTENT_FRACTION", "LABEL_JACCARD",
                                    "OUTLIER_VALIDITY", "RELATIONS"}
    assert rep["criteria"]["PROJ_RANK"]["bar"] == 0.30
    assert "0.30" in str(rules["criteria"]["PROJ_RANK"]["bar"])
    assert rep["criteria"]["LABEL_CONTENT_FRACTION"]["bar"] == 0.80
    assert "0.80" in str(rules["criteria"]["LABEL_CONTENT_FRACTION"]["bar"])
    assert rep["ablation"]["predicate_used"] == "detail_status != 'search_hit'"
    assert "ARTIFACT" in rep["ablation"]
    assert set(rep["nonvacuity"]) >= {"charter", "full", "passed"}


def _strip_timings(raw: bytes) -> bytes:
    # Wall-clock timings are environment-dependent by nature and live in
    # *time_s/elapsed_s fields; every measured metric must be byte-identical.
    import re
    return re.sub(rb'"(hydrated_time_s|recompute_all_time_s|elapsed_s)": [0-9.eE+-]+,?\n?', b'', raw)


def test_byte_identical_rerun(tmp_path):
    b = _synth_bundle(tmp_path / "b.json")
    _run_cli(b, str(tmp_path / "o1"))
    _run_cli(b, str(tmp_path / "o2"))
    r1 = (tmp_path / "o1" / "report.json").read_bytes()
    r2 = (tmp_path / "o2" / "report.json").read_bytes()
    assert _strip_timings(r1) == _strip_timings(r2)
    rep = json.loads(r1.decode())
    assert rep["ablation"]["recompute_all_time_s"] < 2.0
    assert rep["ablation"]["hydrated_time_s"] < 2.0


def test_frozen_rules_command():
    env = {"PYTHONPATH": str(PKG), "PATH": "/usr/bin:/bin"}
    cmd = [sys.executable, "-m", "frontier_map_semantics.cli",
           "--frozen-rules", "--rules", str(RULES)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    fr = json.loads(r.stdout)
    assert "0.30" in str(fr["criteria"]["PROJ_RANK"]["bar"])
    assert "fürsorgepflicht" in fr["query_term_lexicons"]["de-kapitalverletzung"]


def test_alternatives_offline(tmp_path):
    sys.path.insert(0, str(PKG))
    from frontier_map_semantics import alt_eval
    bundle = json.loads(Path(_synth_bundle(tmp_path / "b.json")).read_text())
    out = alt_eval.evaluate(bundle, {"query_language": "de",
                                     "query_term_lexicon": ["fürsorgepflicht", "arbeitgeber", "kündigung"]})
    assert set(out) >= {"A1_drop_unhydrated", "A2_language_aware_tfidf",
                        "A3_mds_cosine", "best"}
    for name in ("A1_drop_unhydrated", "A2_language_aware_tfidf", "A3_mds_cosine"):
        assert out[name]["error"] is None, out[name]["error"]
        assert out[name]["elapsed_s"] < 2.0


SBS_REQUIRED = {"dominant_query_lang_share", "bundle_lang_baseline",
                "dominant_query_term_share", "bundle_term_baseline",
                "largest_share", "sep_ratio", "spearman_2d_vs_cosine",
                "knn10_overlap", "rank_rho"}


def test_ablation_side_by_side_numbers(tmp_path):
    """Acceptance test 2b: coherence, separation AND projection numbers are
    computed twice (all rows vs un-hydrated rows excluded) and reported side by
    side inside the per-bundle report."""
    rep = _run_cli(_synth_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    sbs = rep["ablation"]["side_by_side"]
    assert sbs["predicate_used"] == "detail_status != 'search_hit'"
    for side in ("shipped_fields", "all_rows", "hydrated_only"):
        assert side in sbs and sbs[side] is not None, side
        missing = SBS_REQUIRED - set(sbs[side])
        assert not missing, f"{side} missing {sorted(missing)}"
    # panel 1 is literally what the frozen criteria read over all rows
    assert (sbs["shipped_fields"]["dominant_query_lang_share"]
            == rep["criteria"]["COHERENCE_QUERY_LANG"]["value"])
    assert sbs["shipped_fields"]["knn10_overlap"] == rep["criteria"]["PROJ_KNN10"]["value"]
    # both sides are computed on their own row set: same method, different rows
    assert sbs["all_rows"]["n_rows"] == rep["n_decisions"]
    assert sbs["hydrated_only"]["n_rows"] <= sbs["all_rows"]["n_rows"]
    # the block is additive: frozen criterion verdicts still carry their bars
    assert rep["criteria"]["PROJ_RANK"]["bar"] == 0.30
    assert isinstance(rep["ablation"]["ARTIFACT"], bool)


def test_alternatives_flag_writes_alternatives_json(tmp_path):
    env = {"PYTHONPATH": str(PKG), "PATH": "/usr/bin:/bin"}
    cmd = [sys.executable, "-m", "frontier_map_semantics.cli",
           "--bundle", _synth_bundle(tmp_path / "b.json"),
           "--out", str(tmp_path / "o2"), "--rules", str(RULES),
           "--bundle-key", "de-kapitalverletzung", "--alternatives"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    alts = json.loads(Path(tmp_path, "o2", "alternatives.json").read_text())
    assert set(alts) >= {"A1_drop_unhydrated", "A2_language_aware_tfidf",
                         "A3_mds_cosine", "best"}
    for name in ("A1_drop_unhydrated", "A2_language_aware_tfidf", "A3_mds_cosine"):
        assert alts[name]["error"] is None, alts[name]["error"]
        assert alts[name]["elapsed_s"] < 2.0
    assert json.loads(r.stdout)["alternatives_best"] == alts["best"]


def _synth_incoherent_bundle(path: Path):
    """24 rows whose DOMINANT shipped cluster is deliberately incoherent: it
    mixes de/fr/it rows and none of its bodies contains a query term, so both
    COHERENCE_* criteria FAIL on the shipped geometry and a query-relevance
    re-assignment can flip them. The easy fixture above cannot exercise a flip
    because its dominant cluster is already pure-language and on-term.
    """
    query_term = "fürsorgepflicht"
    other_term = "lohnfortzahlung"
    langs = (["de"] * 2 + ["fr"] * 8 + ["it"] * 4) + (["de"] * 10)
    on_term = [False] * 14 + [True] * 10
    decs = []
    for i, (lg, hit) in enumerate(zip(langs, on_term)):
        word = query_term if hit else other_term
        decs.append({"decision_id": f"r_{i}", "language": lg, "rank": i + 1,
                     "score": 100 - i, "cluster_id": 0 if i < 14 else 1,
                     "x": 0.01 * i, "y": 0.01 * (i % 5), "is_outlier": False,
                     "title": f"row {i} {lg}", "regeste": "",
                     "snippet": f"{lg} {word}",
                     "full_text": f"{word} {lg} " * 12,
                     "citation": f"C {i}", "detail_status": "search_hit",
                     "full_text_status": "full", "counter_status": "none"})
    bundle = {"bundle_version": "test/2",
              "query": "Fürsorgepflicht des Arbeitgebers bei Kündigung",
              "decisions": decs,
              "clusters": [{"cluster_id": 0, "label": "lohnfortzahlung, gericht, urteil",
                            "size": 14, "member_ids": [f"r_{i}" for i in range(14)]},
                           {"cluster_id": 1, "label": "fürsorgepflicht, arbeitgeber",
                            "size": 10, "member_ids": [f"r_{i}" for i in range(14, 24)]}],
              "relations": [{"source": f"r_{i}", "target": f"r_{i+1}", "kind": "citation",
                             "direction": "outgoing", "confidence": 0.8,
                             "seed_decision_id": f"r_{i}", "mention_count": 1.0}
                            for i in range(12)]}
    path.write_text(json.dumps(bundle, ensure_ascii=False))
    return str(path)


def test_positive_control_meets_frozen_nonvacuity_assertion(tmp_path):
    """Acceptance test 4, repaired in cycle 38846038296.

    The frozen corruption control can only MOVE the criteria that read the
    cluster assignment; on a geometry that already fails those axes a scramble
    almost never lands on the passing side, so the >=2-shift assertion is capped.
    The positive control re-assigns cluster ids by query relevance (no RNG) and
    must flip >= 2 criteria, i.e. the failing criteria are reachable bars and not
    vacuously failing. It must not touch any verdict, the criterion table or the
    frozen control's own numbers.
    """
    rep = _run_cli(_synth_incoherent_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    nv = rep["nonvacuity"]
    pc = nv["positive_control"]
    # the fixture must actually exercise the failure the control repairs
    assert rep["criteria"]["COHERENCE_QUERY_LANG"]["pass"] is False
    assert rep["criteria"]["COHERENCE_QUERY_TERM"]["pass"] is False
    assert pc.get("error") is None, pc.get("error")
    assert pc["n_flips"] >= 2, pc
    assert pc["passed"] is True
    assert pc["control_kind"] == "positive_control_not_corruption"
    # the frozen control's own numbers and verdict are untouched by the addition
    for mode in ("charter", "full"):
        assert set(nv[mode]) >= {"flips", "n_flips", "corrupted_overall",
                                 "movable_criteria", "n_movable_criteria"}
    assert isinstance(nv["passed"], bool)


def test_movability_is_measured_not_asserted(tmp_path):
    """A criterion is 'movable' iff its emitted value actually changes under the
    control. Under the frozen id+label permutation only the three
    assignment-reading criteria can move."""
    rep = _run_cli(_synth_incoherent_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    nv = rep["nonvacuity"]
    assert set(nv["charter"]["movable_criteria"]) <= {
        "COHERENCE_QUERY_LANG", "COHERENCE_QUERY_TERM", "STRUCTURE_SEP"}
    assert nv["charter"]["n_movable_criteria"] + \
        nv["charter"]["n_invariant_criteria"] == 11
    assert "movability_note" in nv
    # every listed movable criterion really does change value
    orig = {c: v["value"] for c, v in rep["criteria"].items()}
    for mode in ("charter", "full"):
        for c in nv[mode]["movable_criteria"]:
            assert nv[mode]["corrupted_values"][c] != orig[c], (mode, c)


def test_positive_control_reachability_is_machine_checkable(tmp_path):
    """A bundle whose query-language rows cannot fill the dominant cluster makes
    COHERENCE_QUERY_LANG provably unreachable under ANY partition; that must be
    reported as a bound, not asserted as a cause."""
    rep = _run_cli(_synth_incoherent_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    pc = rep["nonvacuity"]["positive_control"]
    for k in ("max_reachable_query_lang_share", "max_reachable_query_term_share",
              "coherence_lang_reachable", "coherence_term_reachable",
              "n_rows_query_language", "dominant_cluster_size", "n_decisions"):
        assert k in pc, k
    assert pc["max_reachable_query_lang_share"] <= 1.0
    assert pc["coherence_lang_reachable"] == (
        pc["max_reachable_query_lang_share"] >= rep["criteria"]["COHERENCE_QUERY_LANG"]["bar"])
    # the control reaches the bound it claims
    assert pc["values"]["COHERENCE_QUERY_LANG"] <= pc["max_reachable_query_lang_share"] + 1e-9


def test_positive_control_feeds_no_verdict(tmp_path):
    """The added control must not move `overall`, the criterion table or the
    promoted decision inputs."""
    rep = _run_cli(_synth_incoherent_bundle(tmp_path / "b.json"), str(tmp_path / "o1"))
    pc = rep["nonvacuity"]["positive_control"]
    # overall is decided by the shipped criterion table alone
    assert rep["overall"] == ("PASS" if all(v["pass"] for v in rep["criteria"].values())
                              else "FAIL")
    for mode in ("charter", "full"):
        assert rep["nonvacuity"][mode]["corrupted_overall"] in ("PASS", "FAIL")
    # the control reaches a different verdict than the shipped geometry, yet the
    # shipped verdict is unchanged: the addition is inert for every verdict.
    assert pc["criteria"]["COHERENCE_QUERY_LANG"] is True
    assert rep["criteria"]["COHERENCE_QUERY_LANG"]["pass"] is False
    assert rep["nonvacuity"]["passed"] == (
        max(rep["nonvacuity"][m]["n_flips"] for m in ("charter", "full")) >= 2
        and any(rep["nonvacuity"][m]["corrupted_overall"] == "FAIL"
                for m in ("charter", "full")))


def test_claim_checkers_pass_against_committed_artifacts():
    """Both machine checks must pass on the committed, claim-bearing artifacts:
    check_decision.py proves DECISION.txt is true of the tables (charter-1 RF1);
    check_report_numbers.py proves the section-9 addendum prose is true of the
    emitted report.json (same defect class)."""
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PKG)
    for script in ("check_decision.py", "check_report_numbers.py"):
        r = subprocess.run([sys.executable, str(PKG / script)],
                           capture_output=True, text=True, env=env)
        assert r.returncode == 0, f"{script}: {r.stdout}\n{r.stderr}"
        assert "ALL-CHECKS-PASSED" in r.stdout, script
