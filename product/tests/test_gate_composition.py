"""Per-question composition disclosures for the gate packet (direction v54, item 3).

What is pinned here
-------------------
The audit of run 38828034436 and the v54 direction repair named four composition
facts the packet must publish per bundle instead of leaving to inference. Each
one is mechanical and each one is tested against the defect it exists for:

R2  ``largest_cluster_share`` is computed from each cluster's ``size`` field, not
    from ``len(member_ids)``. ``product/query/qmap.py`` truncates ``member_ids``
    at 50, so the two definitions diverge by up to 17.5 points on real bundles and
    the divergence silently suppressed ``map_is_one_mega_cluster`` (a bundle whose
    true share was 55.7% shipped ``warning_count=0``). The threshold
    ``MEGA_CLUSTER_SHARE`` stays 0.5 and is asserted frozen here, because "make
    the disclosure fire" is not a permitted way to fix a missing disclosure.
R3  the dominant cluster's query-language share and its un-hydrated
    (``detail_status != search_hit``) share are measured against the
    pre-registered ``language_coverage_expectation``, so a bundle can no longer
    ship that composition failure while verifying ``admissible=true`` in silence.
R5  the ``source_url`` host distribution is published per bundle, and a bare IP
    literal - a link the researcher cannot open or verify - is blocking rather
    than one more bar in a histogram.
R4  the surfaced counter set's dependence on the request budget is measured and
    disclosed by ``product/query/counter_budget_sensitivity.py``.

Nothing here refuses a bundle for a map weakness, and nothing tunes a threshold:
these are disclosures plus one genuine provenance defect.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from product.query import counter_budget_sensitivity as cbs  # noqa: E402
from product.query import gate_admissibility as ga  # noqa: E402


# --------------------------------------------------------------------------- #
# a hand-built bundle: full control over cluster sizes, languages and hydration
# --------------------------------------------------------------------------- #
def _bundle(*, n: int = 200, dominant: int = 120, dominant_language: str = "it",
            unhydrated: int = 0, cluster_member_ids_cap: int | None = None,
            rest_clusters: int = 1) -> dict:
    """A contract-clean bundle whose clusters, languages and hydration are explicit.

    ``rest_clusters`` splits the non-dominant rows so a test can build a bundle
    whose *largest* cluster holds less than half the map, which is the only way
    to see the mega-cluster disclosure stay silent while still being largest.
    """
    assert rest_clusters >= 1 and 0 <= dominant <= n, "n/2 may be all of it"
    decisions = []
    for i in range(n):
        lang = dominant_language if i < dominant else "de"
        row = {
            "decision_id": f"row_{i:04d}",
            "citation": f"citation {i}",
            "title": f"Entscheidung {i}",
            "court": "Bundesgericht",
            "docket_number": f"docket {i}",
            "rank": i + 1,
            "score": 1.0 - i / 1000.0,
            "snippet": f"Leitsatz {i}",
            "provenance": {"channel": "search"},
            "x": 0.001 * i,
            "y": -0.001 * i,
            "cluster_id": 0 if i < dominant else 1 + (i - dominant) // max(1, (n - dominant)),
            "is_outlier": False,
            "language": lang,
            "detail_status": ("pending" if i < unhydrated else "search_hit"),
            "counter_status": "none",
            "channels": ["search"],
            "source_url": f"https://search.bger.ch/decision/{i}",
            "canonical_url": f"https://mcp.opencaselaw.ch/decision/{i}",
        }
        decisions.append(row)
    cap = cluster_member_ids_cap if cluster_member_ids_cap is not None else ga.CLUSTER_MEMBER_IDS_CAP
    rest_ids = [d["decision_id"] for d in decisions if d["cluster_id"] > 0]
    clusters = [{
        "cluster_id": 0, "label": "dominant", "size": dominant,
        "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 0][:cap],
    }]
    step = -(-len(rest_ids) // rest_clusters)
    for k in range(rest_clusters):
        clusters.append({
            "cluster_id": k + 1, "label": f"rest-{k}", "size": len(rest_ids[k * step:(k + 1) * step]),
            "member_ids": rest_ids[k * step:(k + 1) * step][:cap],
        })
    return {
        "bundle_version": "1.0",
        "query": "Kapitalverletzung aktive Fürsorgepflicht",
        "query_variants": [],
        "answer": {"prose": "probe", "statements": [], "cited_decision_ids": ["row_0000"],
                   "method": "test", "model": "test", "status": "ready"},
        "decisions": decisions,
        "clusters": clusters,
        "relations": [{"source": "row_0000", "target": "row_0001", "kind": "citation",
                       "evidence": "test"}],
        "provenance": {"bundle": "query_result_bundle v1.0"},
    }


def _codes(verdict: dict) -> dict:
    return {f["code"]: f for f in verdict["findings"]}


# --------------------------------------------------------------------------- #
# R2 - the share comes from `size`, and the threshold stays frozen
# --------------------------------------------------------------------------- #
def test_mega_cluster_threshold_is_frozen_at_one_half():
    """Fixing a missing disclosure must never come from moving the threshold."""
    assert ga.MEGA_CLUSTER_SHARE == 0.5


def test_largest_cluster_share_uses_the_size_field_not_the_truncated_member_ids():
    """The exact R2 defect: 120/200 = 0.60 fires, the capped 50/200 = 0.25 does not."""
    bundle = _bundle(n=200, dominant=120, cluster_member_ids_cap=ga.CLUSTER_MEMBER_IDS_CAP)
    assert len(bundle["clusters"][0]["member_ids"]) == ga.CLUSTER_MEMBER_IDS_CAP
    assert bundle["clusters"][0]["size"] == 120

    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    measured = verdict["measured"]
    assert measured["largest_cluster_share"] == 0.6
    assert measured["largest_cluster_share_definition"] == "cluster['size'] / n_decisions"
    # both definitions published, so nobody has to guess which one an artifact used
    assert measured["largest_cluster_member_ids_share"] == 0.25
    assert measured["largest_cluster_member_ids_truncated"] is True
    assert measured["cluster_member_ids_cap"] == 50

    finding = _codes(verdict)["map_is_one_mega_cluster"]
    assert finding["severity"] == "warning"
    assert finding["share"] == 0.6
    assert finding["mega_cluster_share_from_member_ids"] == 0.25
    assert finding["member_ids_truncated"] is True
    assert verdict["admissible"], "a disclosed map weakness never blocks the packet"


def test_a_true_sub_threshold_cluster_still_discloses_nothing():
    bundle = _bundle(n=400, dominant=197, rest_clusters=3,
             cluster_member_ids_cap=ga.CLUSTER_MEMBER_IDS_CAP)
    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    assert verdict["measured"]["largest_cluster_share"] == 0.4925
    assert "map_is_one_mega_cluster" not in _codes(verdict)


def test_cluster_shares_report_every_cluster_and_the_omitted_rows():
    bundle = _bundle(n=200, dominant=120, cluster_member_ids_cap=ga.CLUSTER_MEMBER_IDS_CAP)
    shares = ga.cluster_shares(bundle)
    assert [s["size"] for s in shares] == [120, 80]
    assert shares[0]["member_ids_omitted"] == 70
    assert shares[0]["member_ids_truncated"] is True
    assert shares[0]["label"] == "dominant"


def test_a_cluster_without_a_size_field_falls_back_to_its_members():
    bundle = _bundle(n=120, dominant=120, cluster_member_ids_cap=120)
    bundle["clusters"][0].pop("size")
    assert ga.cluster_shares(bundle)[0]["size"] == 120


# --------------------------------------------------------------------------- #
# R3 - composition of the cluster the map renders at the centre
# --------------------------------------------------------------------------- #
def test_dominant_cluster_language_composition_is_disclosed_and_flags_the_failure():
    """A German question whose dominant cluster is 100% Italian (v54 R3)."""
    bundle = _bundle(n=200, dominant=120, dominant_language="it")
    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    finding = _codes(verdict)["dominant_cluster_language_composition"]
    assert finding["severity"] == "warning"
    assert finding["share"] == 0.0
    assert finding["languages"] == {"it": 120}
    assert verdict["admissible"], "composition is disclosed, not used as a refusal"
    # the bundle-level language check passes while the dominant cluster fails:
    # that gap is the whole point of the new finding
    assert "question_language_underrepresented" not in _codes(verdict)


def test_dominant_cluster_composition_is_a_positive_disclosure_when_it_holds():
    bundle = _bundle(n=200, dominant=120, dominant_language="de")
    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    finding = _codes(verdict)["dominant_cluster_composition"]
    assert finding["severity"] == "info"
    assert verdict["warning_count"] == sum(
        1 for f in verdict["findings"] if f["severity"] == "warning"
    ), "an info disclosure must never inflate warning_count"


def test_unhydrated_share_uses_the_preregistered_detail_status_definition():
    bundle = _bundle(n=200, dominant=120, dominant_language="de", unhydrated=48)
    measured = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})["measured"]
    dom = measured["dominant_cluster"]
    assert dom["members"] == 120
    assert dom["unhydrated_rows"] == 48
    assert dom["unhydrated_share"] == 0.4
    assert dom["detail_status"] == {"pending": 48, "search_hit": 72}


def test_composition_is_measured_from_decisions_not_from_the_truncated_member_list():
    """member_ids covers 50 of 120; the composition must still see all 120."""
    bundle = _bundle(n=200, dominant=120, dominant_language="de", unhydrated=30,
                     cluster_member_ids_cap=ga.CLUSTER_MEMBER_IDS_CAP)
    dom = ga.dominant_cluster_composition(bundle, "de")
    assert len(bundle["clusters"][0]["member_ids"]) == 50
    assert dom["members"] == 120
    assert dom["question_language_rows"] == 120
    assert dom["unhydrated_rows"] == 30


def test_rows_without_a_language_are_counted_not_dropped():
    """A composition that omits 42 of 99 rows is not a composition."""
    bundle = _bundle(n=200, dominant=120, dominant_language="de")
    for row in bundle["decisions"][:40]:
        row["language"] = ""
    dom = ga.dominant_cluster_composition(bundle, "de")
    assert dom["members"] == 120
    assert dom["rows_without_language"] == 40
    assert sum(dom["languages"].values()) + dom["rows_without_language"] == 120
    assert dom["question_language_rows"] == 80


def test_the_preregistered_expectation_is_quoted_in_the_warning():
    bundle = _bundle(n=200, dominant=120, dominant_language="it")
    question = {"qid": "q", "language": "de",
                "language_coverage_expectation": "German-language decisions should be a "
                                                "substantial share of the bundle"}
    verdict = ga.verify_bundle(bundle, question=question)
    assert "substantial share" in _codes(verdict)["dominant_cluster_language_composition"]["detail"]


# --------------------------------------------------------------------------- #
# R5 - where the source links point
# --------------------------------------------------------------------------- #
def test_a_bare_ip_source_url_is_blocking_and_names_the_row():
    bundle = _bundle(n=120, dominant=120)
    bundle["decisions"][3]["source_url"] = "http://192.168.7.9:8080/copy_of_2010_41"
    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    finding = _codes(verdict)["unverifiable_source_url_host"]
    assert finding["severity"] == "blocking"
    assert finding["rows"] == ["row_0003"]
    assert not verdict["admissible"]


def test_an_ipv6_literal_is_also_blocking_but_a_service_name_is_not():
    bundle = _bundle(n=120, dominant=120)
    bundle["decisions"][1]["source_url"] = "http://[2001:db8::1]/x"
    assert ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})["admissible"] is False
    bundle = _bundle(n=120, dominant=120)
    bundle["decisions"][1]["source_url"] = "http://abc:def/x"     # host:port, not an address
    assert "unverifiable_source_url_host" not in _codes(
        ga.verify_bundle(bundle, question={"qid": "q", "language": "de"}))


def test_a_wide_spread_of_real_court_hosts_is_disclosed_not_refused():
    bundle = _bundle(n=120, dominant=120)
    hosts = ["https://search.bger.ch/x", "https://www.sentenze.ti.ch/y",
             "https://jurisprudence.ne.ch/z", "https://www.gerichte-zh.ch/w"]
    for i, row in enumerate(bundle["decisions"]):
        row["source_url"] = hosts[i % len(hosts)]
    # one un-hydrated citation shell: the only row shape where a null source_url
    # is the known, explained behaviour rather than a provenance defect
    bundle["decisions"][7]["source_url"] = ""
    bundle["decisions"][7]["channels"] = ["citation.outgoing"]
    bundle["decisions"][7]["detail_status"] = "pending"
    bundle["decisions"][7]["citation"] = "row_0007"   # a shell carries its own identity
    verdict = ga.verify_bundle(bundle, question={"qid": "q", "language": "de"})
    codes = _codes(verdict)
    assert "unverifiable_source_url_host" not in codes
    distribution = codes["source_url_host_distribution"]
    assert distribution["severity"] == "info"
    assert "search.bger.ch" in distribution["hosts"]
    measured = verdict["measured"]
    assert measured["source_url_n_hosts"] == 4
    assert measured["source_url_rows_without_url"] == 1
    assert measured["source_url_federal_court_hosted_rows"] == 30
    assert measured["source_url_federal_court_hosted_share_of_linked"] == round(30 / 119, 4)
    assert verdict["admissible"]


def test_the_shipped_packet_bundles_publish_the_dominant_cluster_composition():
    """Regression guard on real artifacts, not only synthetic ones.

    The FR bundle of run 38838116453 has a dominant cluster of 167/217 = 0.77,
    which the pre-R2 definition (50/217 = 0.23) hid completely. Both numbers must
    now appear in the product's own verdict for that bundle.
    """
    path = ROOT / "results" / "product" / "gate_packet" / "38838116453" / "questions" / \
        "fr-bail-entretien.bundle.json"
    if not path.is_file():  # pragma: no cover - historical packet absent
        pytest.skip("shipped packet bundle not present in this checkout")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    verdict = ga.verify_bundle(bundle, question={"qid": "fr-bail-entretien", "language": "fr"})
    measured = verdict["measured"]
    assert measured["largest_cluster_share"] == 0.7696
    assert measured["largest_cluster_member_ids_share"] == 0.2304
    assert "map_is_one_mega_cluster" in _codes(verdict), (
        "the R2 reconciliation must make this disclosure fire on the bundle that hid it")
    dom = measured["dominant_cluster"]
    assert dom["unhydrated_rows"] > 0 and dom["languages"]


# --------------------------------------------------------------------------- #
# R4 - budget dependence of the surfaced counter set
# --------------------------------------------------------------------------- #
def test_counter_set_comparison_is_pure_and_symmetric():
    out = cbs.compare_counter_sets(["a", "b", "c"], ["a", "b"])
    assert out["overlap_n"] == 2
    assert out["only_in_full"] == ["c"]
    assert out["only_in_reduced"] == []
    assert out["full_retained_by_reduced_budget"] == round(2 / 3, 4)
    assert out["jaccard"] == round(2 / 3, 4)


def test_a_disjoint_counter_set_is_reported_as_disjoint_not_as_a_count_difference():
    out = cbs.compare_counter_sets(["a", "b"], ["c", "d"])
    assert out["overlap_n"] == 0
    assert out["union_n"] == 4
    assert out["jaccard"] == 0.0
    assert out["full_retained_by_reduced_budget"] == 0.0


def test_an_empty_counter_set_compares_to_none_rather_than_to_zero_evidence():
    out = cbs.compare_counter_sets([], [])
    assert out["jaccard"] is None
    assert out["full_retained_by_reduced_budget"] is None


def test_the_counter_set_definition_is_the_maps_ringed_set_not_a_divergent_copy():
    """Audit 38839347028 D2: the disclosed counter ids must be exactly the rows
    the map rings.  ``gate_admissibility.NON_COUNTER_STATUSES`` is the single
    source of truth (kept in step with ``isCounter()`` in query.html); this
    module must import it, never redefine it.  The rejected cycle's local copy
    omitted ``"cited"`` and disclosed 21/26/29 counter ids where the map ringed
    15/25/25 — answer-cited *supporting* rows counted as contrary authority.
    """
    assert cbs.NON_COUNTER_STATUSES is ga.NON_COUNTER_STATUSES
    assert "cited" in cbs.NON_COUNTER_STATUSES
    rows = [
        {"decision_id": "d1", "counter_status": "candidate-contrary"},
        {"decision_id": "d2", "counter_status": "cited"},          # answer-cited: NOT counter
        {"decision_id": "d3", "counter_status": "candidate-limiting"},
        {"decision_id": "d4", "counter_status": "none"},
        {"decision_id": "d5", "counter_status": "supporting-candidate"},
        {"decision_id": "d6"},                                      # unset: NOT counter
    ]
    assert cbs._counter_ids({"decisions": rows}) == ["d1", "d3"]
    # and the gate's own counter_ids agrees on the same population
    assert ga.counter_ids({"decisions": rows}) == ["d1", "d3"]


def test_an_empty_answer_vocabulary_records_a_skip_instead_of_a_measurement():
    """D4's vacuous guard reaches this tool too: nothing to compare, say so."""
    bundle = _bundle(n=120, dominant=120)
    bundle["answer"]["prose"] = ""
    out = cbs.measure(bundle, mode="fixture")
    assert out["skipped"] is True
    assert "no usable vocabulary" in out["skip_reason"]
    assert out["n_probes"] == 0


def test_the_measurement_changes_only_the_budget(tmp_path, monkeypatch):
    """Same plan, same exclusions, same cache; ``max_requests`` is the only knob."""
    bundle = _bundle(n=120, dominant=120)
    bundle["answer"]["prose"] = "Der Arbeitgeber hat eine aktive Fürsorgepflicht bei der " \
                                "Kapitalverletzung und muss nicht bloss überwachen."
    seen: dict[int, list[str]] = {}

    def fake_fetch(query, plan, *, mode, exclude_ids, exclude_identities,
                   max_requests, **kwargs):
        seen[max_requests] = [p["query"] for p in plan]
        return {"candidates": [], "provenance": {"probes": [], "hydrated_ids": [],
                                                 "request_summary": {"network_calls": 0,
                                                                     "cache_hits": 0}}}

    monkeypatch.setattr(cbs, "fetch_adversarial_candidates", fake_fetch)
    out = cbs.measure(bundle, mode="fixture", full_budget=24, reduced_budget=8)
    assert out["skipped"] is False
    assert sorted(seen) == [8, 24]
    assert seen[8] == seen[24], "the plan must be identical across budgets"
    assert out["full"]["budget"] == 24 and out["reduced"]["budget"] == 8
    assert out["counter_set"]["overlap_n"] == 0  # no rows fetched at all, honestly empty
    assert "budget" in out["interpretation"]
    assert "tunes nothing" in out["claim_ceiling"]


def test_a_shipped_bundle_can_be_measured_in_fixture_mode():
    """The tool must run offline against a shipped bundle (CI has no network)."""
    path = ROOT / "results" / "product" / "gate_packet" / "38838116453" / "questions" / \
        "de-kapitalverletzung.bundle.json"
    if not path.is_file():  # pragma: no cover - historical packet absent
        pytest.skip("shipped packet bundle not present in this checkout")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    out = cbs.measure(bundle, mode="fixture", full_budget=24, reduced_budget=8)
    assert out["schema"] == cbs.SCHEMA
    assert "counter_set" in out or out.get("skipped") is True

# --------------------------------------------------------------------------- #
# the packet-level tool: one command, four disclosures, no side effects by default
# --------------------------------------------------------------------------- #
def test_packet_disclosures_publish_all_four_for_every_question(tmp_path):
    """One command re-verifies the packet and writes the v54 disclosures."""
    import shutil

    import gate_packet as gp
    import gate_packet_disclosures as gpd

    src = ROOT / "results" / "product" / "gate_packet" / "38839347028"
    if not (src / "packet.json").is_file():  # pragma: no cover - no packet in this checkout
        pytest.skip("shipped packet not present in this checkout")
    packet = tmp_path / "packet"
    shutil.copytree(src, packet)
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    # The committed packet stores the absolute paths it was written with; a
    # copy at another checkout must not ``relative_to`` them (audit 38839347028
    # D1: ValueError at any path other than the producing machine).  Resolve
    # through the product's own portable mechanism instead.
    for entry in summary["questions"]:          # the copy is self-contained
        for key in ("bundle_path", "question_path"):
            if entry.get(key):
                entry[key] = str(gp._resolve_artifact(entry[key], packet))
    (packet / "packet.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    (packet / "disclosures.json").unlink(missing_ok=True)   # the copy ships one
    out = gpd.run(packet, mode="fixture", write_verdicts=False)
    assert out["ok"], out
    assert out["n_reverified"] == 3
    for q in out["questions"]:
        d = q["v54_disclosures"]
        assert d["a_dominant_cluster_language_and_hydration"]["published"] is True
        assert d["b_source_url_host_distribution"]["published"] is True
        assert d["c_counter_budget_sensitivity"]["published"] is True
        assert d["d_mega_cluster_share_from_size"]["published"] is True
        assert d["d_mega_cluster_share_from_size"]["threshold_unchanged"] == 0.5
        assert d["d_mega_cluster_share_from_size"]["definition"].startswith("cluster['size']")
    assert not (packet / "disclosures.json").exists(), "write_verdicts=False writes nothing"


def test_the_owner_card_carries_the_budget_sensitivity_line(tmp_path):
    """The disclosure has to reach the jurist, not just the artifact directory."""
    import gate_packet as gp

    qid = "q-test"
    (tmp_path / "questions").mkdir()
    (tmp_path / "questions" / f"{qid}.budget_sensitivity.json").write_text(json.dumps({
        "skipped": False,
        "full": {"budget": 24}, "reduced": {"budget": 8},
        "counter_set": {"full_n": 21, "reduced_n": 27, "overlap_n": 20, "union_n": 28,
                        "jaccard": 0.7143},
    }), encoding="utf-8")
    recheck = {"packet_id": "p", "mode": "live", "checked_at": "now", "packet_dir": str(tmp_path),
               "questions": [{"qid": qid, "language": "fr", "question": "q", "admissible": True,
                              "bundle_path": "b", "verdict": {"findings": [], "measured": {}}}]}
    card = gp.owner_card(recheck, base_url="http://127.0.0.1:1", top_n=150)
    assert "budget-dependent" in card
    assert "'what this run surfaced'" in card
    assert "20 shared of 28" in card
    # audit 38839347028 D3: the leading clause names the survivors, not the
    # full set — "{overlap_n} of {full_n} survive", never "{full_n} of the
    # surfaced counter rows".
    assert "20 of 21 survive" in card
    assert "21 of the surfaced counter rows survive" not in card


def test_a_skipped_budget_measurement_is_stated_on_the_card_rather_than_hidden(tmp_path):
    import gate_packet as gp

    qid = "q-skip"
    (tmp_path / "questions").mkdir()
    (tmp_path / "questions" / f"{qid}.budget_sensitivity.json").write_text(json.dumps({
        "skipped": True, "skip_reason": "the answer carries no usable vocabulary"}),
        encoding="utf-8")
    recheck = {"packet_id": "p", "mode": "live", "checked_at": "now", "packet_dir": str(tmp_path),
               "questions": [{"qid": qid, "language": "de", "question": "q", "admissible": True,
                              "bundle_path": "b", "verdict": {"findings": [], "measured": {}}}]}
    card = gp.owner_card(recheck, base_url="http://127.0.0.1:1", top_n=150)
    assert "not measured" in card
    assert "no usable vocabulary" in card
