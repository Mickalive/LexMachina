"""Tests for the deterministic counter-evidence span selector.

The pure tests use a small FakeRules object so they run without the accepted
mount.  The integration tests pin the real frozen scorer on the accepted mount
and are skipped when the mount is absent.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPONENT = REPO_ROOT / "frontier" / "frontier-counter-evidence-span-selection"
if str(COMPONENT) not in sys.path:
    sys.path.insert(0, str(COMPONENT))

import span_select  # noqa: E402

MOUNT = Path(os.environ.get("LEX_ACCEPTED_PRODUCT", "/tmp/lex_accepted/core/product"))
PROTOCOL = (
    REPO_ROOT
    / "results"
    / "frontier"
    / "frontier-counter-evidence-span-selection"
    / "PROTOCOL.json"
)


class FakeNormalizer:
    """Minimal mirror of the frozen normalizer for pure algorithm tests."""

    _STRIP = ("ungen", "ung", "heit", "keit", "lich", "isch", "ieren", "en", "er", "es", "e", "s")

    def stem(self, token: str) -> str:
        for suf in self._STRIP:
            if token.endswith(suf) and len(token) - len(suf) >= 4:
                return token[: -len(suf)]
        return token

    def stems(self, text: str) -> list[str]:
        raw = re.findall(r"[0-9a-z]+", str(text).lower())
        return [self.stem(t) for t in raw]

    def match_marker(self, tokens: list[str], marker: str) -> str | None:
        want = self.stems(marker)
        if not want:
            return None
        if len(want) == 1:
            return marker if want[0] in tokens else None
        n, m = len(tokens), len(want)
        for i in range(n - m + 1):
            if tokens[i : i + m] == want:
                return marker
        return None

    def match_anchor(self, tokens: list[str], anchor: str) -> str | None:
        want = self.stems(anchor)
        if not want:
            return None
        if len(want) > 1:
            n, m = len(tokens), len(want)
            for i in range(n - m + 1):
                if tokens[i : i + m] == want:
                    return anchor
            return None
        target = want[0]
        for tok in tokens:
            limit = min(len(tok), len(target))
            if limit >= 5 and tok[:limit] == target[:limit]:
                return anchor
        return None

    def regex_text(self, text: str) -> str:
        return str(text).lower()

    def match_regex(self, text: str, pattern: str) -> str | None:
        try:
            return pattern if re.search(pattern, text, flags=re.IGNORECASE) else None
        except re.error:
            return None


class FakeRules:
    def __init__(self) -> None:
        self.normalizer = FakeNormalizer()
        self.lexicons = {
            "counter_intent_markers": {
                "de": {"frozen_additions": ["nicht", "nur", "begrenzt"], "product_adversarial_terms": []},
                "fr": {"frozen_additions": ["ne peut", "sauf"], "product_adversarial_terms": []},
                "it": {"frozen_additions": ["non", "salvo"], "product_adversarial_terms": []},
            },
            "polarity_inversion": {"de": [r"wird\s+bestatigt"], "fr": [], "it": []},
            "fragment_pointer": [r"^\s*bge\s+\d+.*$"],
            "procedural_formula": {"de": ["im sinne der erwagungen"], "fr": [], "it": []},
            "procedural_outcome_words": {"de": ["abgewiesen"], "fr": [], "it": []},
        }
        self.anchors = {
            "q-de": {
                "domain": ["sorgepflicht", "arbeitgeber", "kapitalverletzung", "eingriff"],
                "pivot": ["kapitalverletzung", "eingriff", "untergang"],
                "expected_languages": ["de", "fr", "it"],
                "foreign_legal_area_fields": [],
            }
        }

    def marker_lexicon(self, language: str, variant: str = "primary") -> list[str]:
        entry = self.lexicons["counter_intent_markers"].get(language) or {}
        return list(entry.get("frozen_additions") or []) + list(
            entry.get("product_adversarial_terms") or []
        )

    def anchor_profile(self, key: str) -> dict:
        return self.anchors[key]


def row(
    *,
    decision_id: str = "row-1",
    full_text: str,
    language: str = "de",
    counter_status: str = "candidate-limiting",
    promoted: bool = True,
) -> dict:
    out = {
        "decision_id": decision_id,
        "language": language,
        "legal_area": "",
        "rank": 1,
        "title": "",
        "regeste": "",
        "full_text": full_text,
        "full_text_status": "fetched",
        "counter_status": counter_status,
        "counter_evidence": "",
        "counter_evidence_verified": False,
    }
    if promoted:
        out["counter_proposal_source"] = span_select.REPAIR_ID
    return out


POSITIVE = (
    "Die Sorgepflicht des Arbeitgebers ist begrenzt; eine Kapitalverletzung "
    "kann nur bei einem aktiven Eingriff angenommen werden."
)


class PureSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = FakeRules()
        self.profile = self.rules.anchor_profile("q-de")

    def test_split_passages_offsets_and_max_chars(self) -> None:
        text = "Erster Satz. Zweiter Satz!\n\nDritter Absatz; vierter Teil. " + ("x" * 1200)
        units = span_select.split_passages(text, max_chars=200)
        self.assertTrue(units)
        for u in units:
            self.assertLessEqual(u.end - u.start, 200)
            self.assertGreater(u.end, u.start)
            self.assertFalse(text[u.start].isspace())
            self.assertFalse(text[u.end - 1].isspace())
        self.assertEqual(text[units[0].start : units[0].end], text[units[0].start : units[0].end])

    def test_iter_windows_respects_limits(self) -> None:
        text = "A" * 50 + " " + "B" * 50 + " " + "C" * 50
        units = span_select.split_passages(text, max_chars=100)
        windows = list(span_select.iter_windows(units, min_chars=40, max_chars=100, max_units=2))
        self.assertTrue(windows)
        for w in windows:
            self.assertGreaterEqual(w.end - w.start, 40)
            self.assertLessEqual(w.end - w.start, 100)

    def test_verify_span_rejects_mutated_and_foreign(self) -> None:
        text = POSITIVE
        start = text.index("Die Sorgepflicht")
        end = text.index(";")
        quote = text[start:end]
        self.assertTrue(span_select.verify_span(text, quote, start, end))
        mutated = span_select.mutate_quote(quote) if hasattr(span_select, "mutate_quote") else quote.replace("Sorge", "Xorge", 1)
        self.assertFalse(span_select.verify_span(text, mutated, start, end))
        self.assertFalse(span_select.verify_span(text, "a quote from another decision", 0, 10))

    def test_select_span_emits_verbatim_quote(self) -> None:
        r = row(full_text=POSITIVE)
        dec = span_select.select_span(r, self.rules, self.profile)
        self.assertTrue(dec.evidenced)
        self.assertEqual(dec.reason_code, "supported")
        self.assertIn(dec.quote, POSITIVE)
        self.assertEqual(POSITIVE[dec.char_start : dec.char_end], dec.quote)
        self.assertTrue(dec.intent_marker)
        self.assertTrue(dec.domain_anchor)
        self.assertTrue(dec.pivot_anchor)

    def test_select_span_abstains_without_pivot(self) -> None:
        r = row(
            full_text=(
                "Die Sorgepflicht des Arbeitgebers ist begrenzt; eine Massnahme "
                "kann nur bei einem aktiven Vorgehen angenommen werden."
            )
        )
        dec = span_select.select_span(r, self.rules, self.profile)
        self.assertFalse(dec.evidenced)
        self.assertEqual(dec.reason_code, span_select.REASON_NO_PIVOT_ANCHOR)

    def test_select_span_abstains_on_inversion(self) -> None:
        r = row(
            full_text=(
                "Die Sorgepflicht des Arbeitgebers ist begrenzt und eine "
                "Kapitalverletzung liegt nur vor, wenn das Urteil wird bestatigt."
            )
        )
        dec = span_select.select_span(r, self.rules, self.profile)
        self.assertFalse(dec.evidenced)
        self.assertEqual(dec.reason_code, span_select.REASON_POLARITY_INVERTED)

    def test_select_span_abstains_on_pointer(self) -> None:
        r = row(
            full_text=(
                "BGE 143 III 157 S. 12; die Sorgepflicht des Arbeitgebers ist "
                "begrenzt; eine Kapitalverletzung liegt nur vor."
            )
        )
        dec = span_select.select_span(r, self.rules, self.profile)
        self.assertFalse(dec.evidenced)
        self.assertGreater(dec.diagnostics["pointer_qualified_windows"], 0)

    def test_select_span_abstains_without_full_text(self) -> None:
        r = row(full_text="")
        dec = span_select.select_span(r, self.rules, self.profile)
        self.assertFalse(dec.evidenced)
        self.assertEqual(dec.reason_code, span_select.REASON_NO_RETRIEVED_TEXT)

    def test_select_span_language_gate(self) -> None:
        rules = FakeRules()
        rules.anchors["q-de"]["expected_languages"] = ["de"]
        r = row(full_text=POSITIVE, language="fr")
        dec = span_select.select_span(r, rules, rules.anchor_profile("q-de"))
        self.assertFalse(dec.evidenced)
        self.assertEqual(dec.reason_code, span_select.REASON_LANGUAGE_NOT_EXPECTED)

    def test_apply_span_selection_preserves_status_and_denominator(self) -> None:
        bundle = {
            "decisions": [
                row(decision_id="p1", full_text=POSITIVE),
                row(
                    decision_id="p2",
                    full_text=(
                        "Die Sorgepflicht des Arbeitgebers ist begrenzt; eine "
                        "Massnahme kann nur bei einem aktiven Vorgehen angenommen werden."
                    ),
                ),
                row(decision_id="untouched", full_text=POSITIVE, counter_status="none", promoted=False),
            ]
        }
        out, decisions = span_select.apply_span_selection(bundle, self.rules, self.profile)
        self.assertEqual(len(decisions), 2)
        by_id = {d["decision_id"]: d for d in out["decisions"]}
        self.assertEqual(by_id["p1"]["counter_status"], "candidate-limiting")
        self.assertEqual(by_id["p2"]["counter_status"], "candidate-limiting")
        self.assertEqual(by_id["p1"]["counter_evidence"], decisions[0].quote)
        self.assertEqual(by_id["p1"]["counter_evidence_span"]["quote"], decisions[0].quote)
        self.assertFalse(by_id["p1"]["counter_span_selection"]["abstained"])
        self.assertEqual(by_id["p2"]["counter_evidence"], "")
        self.assertIsNone(by_id["p2"]["counter_evidence_span"])
        self.assertTrue(by_id["p2"]["counter_span_selection"]["abstained"])
        self.assertFalse(by_id["p2"]["counter_evidence_verified"])
        self.assertEqual(by_id["untouched"]["counter_evidence"], "")
        self.assertNotIn("counter_evidence_span", by_id["untouched"])
        self.assertEqual(
            out["provenance"]["counter_evidence_span_selection"]["n_promoted_rows"], 2
        )

    def test_determinism(self) -> None:
        r = row(full_text=POSITIVE)
        d1 = span_select.select_span(r, self.rules, self.profile).to_dict()
        d2 = span_select.select_span(r, self.rules, self.profile).to_dict()
        self.assertEqual(d1, d2)


@unittest.skipUnless(MOUNT.is_dir(), f"accepted mount not present: {MOUNT}")
class FrozenScorerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import scorer_bridge

        cls.bridge = scorer_bridge
        cls.modules = scorer_bridge.load_product_modules(MOUNT)
        decide_label, load_rules = scorer_bridge.load_classifier(MOUNT)
        # staticmethod prevents Python from binding the plain function to the
        # test instance (which would inject ``self`` as a fourth argument).
        cls.decide_label = staticmethod(decide_label)
        cls.rules = load_rules(str(MOUNT / "product" / "frozen" / "RULES_LABEL.json"))
        cls.packet_dir = Path(
            json.loads(PROTOCOL.read_text(encoding="utf-8"))["inputs"]["packet_of_record"]["path_prefix"]
        )
        cls.limits = json.loads(PROTOCOL.read_text(encoding="utf-8"))["span_rule"]["limits"]

    def test_protocol_sha256_matches(self) -> None:
        import hashlib

        payload = PROTOCOL.read_bytes()
        expected = PROTOCOL.with_name("PROTOCOL.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)

    def test_real_baseline_de_reproduced(self) -> None:
        bundle = self.bridge.load_bundle(self.packet_dir, "de-kapitalverletzung")
        base = self.bridge.run_baseline(bundle, "de-kapitalverletzung", self.modules)
        summary = base["summary"]
        self.assertEqual(summary["n_scored"], 8)
        self.assertEqual(summary["n_abstained"], 8)
        self.assertEqual(summary["n_emitted"], 0)
        self.assertEqual(summary["support_rate_among_emitted"], 0.0)
        self.assertEqual(
            summary["abstention_reasons"],
            {"no_domain_anchor": 1, "no_intent_marker": 2, "pivot_absent": 5},
        )

    def test_real_candidate_de_verbatim_and_denominator(self) -> None:
        bundle = self.bridge.load_bundle(self.packet_dir, "de-kapitalverletzung")
        cand = self.bridge.run_candidate(
            bundle, "de-kapitalverletzung", self.modules, self.rules,
            self.rules.anchor_profile("de-kapitalverletzung"),
            min_chars=int(self.limits["min_span_chars"]),
            max_chars=int(self.limits["max_span_chars"]),
            max_units=int(self.limits["max_window_units"]),
        )
        summary = cand["summary"]
        self.assertEqual(summary["n_scored"], 8)
        self.assertGreater(summary["n_emitted"], 0)
        details = self.bridge.row_details(cand["final_bundle"], cand["span_decisions"])
        emitted = [
            d for d in details
            if d["counter_status_after"] in span_select.SCORED_STATUSES
        ]
        self.assertTrue(emitted)
        for d in emitted:
            self.assertTrue(d["quote_verbatim_in_full_text"])
            self.assertEqual(d["counter_reason_code"], "supported")
            self.assertTrue(d["counter_evidence_equals_quote"])

    def test_seeded_controls(self) -> None:
        controls = self.bridge.run_seeded_controls(
            self.rules, self.modules,
            min_chars=int(self.limits["min_span_chars"]),
            max_chars=int(self.limits["max_span_chars"]),
            max_units=int(self.limits["max_window_units"]),
        )
        self.assertTrue(controls["positive"]["pass"])
        self.assertEqual(controls["positive"]["n_emitted"], 1)
        self.assertTrue(controls["negative"]["pass"])
        self.assertEqual(controls["negative"]["n_emitted"], 0)

    def test_frozen_injection_rows(self) -> None:
        injection = self.bridge.score_injection_rows(self.rules, self.decide_label)
        self.assertTrue(injection["pass"])
        self.assertTrue(injection["all_match_expected"])


class ArtifactConsistencyTests(unittest.TestCase):
    """Pin the committed measurement, state and semantic audit together."""

    def setUp(self) -> None:
        results = REPO_ROOT / "results" / "frontier" / "frontier-counter-evidence-span-selection"
        self.measurement = json.loads((results / "MEASUREMENT.json").read_text(encoding="utf-8"))
        self.audit = json.loads((results / "SEMANTIC_AUDIT.json").read_text(encoding="utf-8"))
        self.state = json.loads(
            (REPO_ROOT / "state" / "frontier" / "frontier-counter-evidence-span-selection.json").read_text(
                encoding="utf-8"
            )
        )

    def test_measurement_and_state_side_by_side_agree(self) -> None:
        side = self.measurement["side_by_side"]
        h2h = self.state["head_to_head"]
        self.assertEqual(side["baseline_n_scored"], h2h["baseline"]["n_scored"])
        self.assertEqual(side["baseline_n_abstained"], h2h["baseline"]["n_abstained"])
        self.assertEqual(side["baseline_n_emitted"], h2h["baseline"]["n_emitted"])
        self.assertEqual(side["candidate_n_scored"], h2h["candidate"]["n_scored"])
        self.assertEqual(side["candidate_n_abstained"], h2h["candidate"]["n_abstained"])
        self.assertEqual(side["candidate_n_emitted"], h2h["candidate"]["n_emitted"])
        self.assertEqual(side["candidate_n_evidenced"], h2h["candidate"]["n_evidenced"])
        self.assertEqual(
            side["candidate_support_rate_among_emitted"],
            h2h["candidate"]["support_rate_among_emitted"],
        )
        self.assertEqual(side["control_n_emitted_swapped"], h2h["controls"]["swapped_evidence_emitted"])
        self.assertEqual(side["control_n_emitted_inverted"], h2h["controls"]["inverted_evidence_emitted"])
        self.assertEqual(side["seeded_positive_emitted"], h2h["controls"]["seeded_positive_emitted"])
        self.assertEqual(side["seeded_negative_emitted"], h2h["controls"]["seeded_negative_emitted"])

    def test_semantic_audit_counts_and_role(self) -> None:
        self.assertIn("POST-HOC DIAGNOSTIC", self.audit["role"])
        self.assertEqual(self.audit["n_emitted_rows"], 7)
        self.assertEqual(self.audit["n_exact_anchor"], 2)
        self.assertEqual(self.audit["n_morphological_prefix"], 1)
        self.assertEqual(self.audit["n_string_coincidence_prefix"], 4)
        qualities = [r["anchor_quality"] for r in self.audit["rows"]]
        self.assertEqual(
            qualities,
            [
                "string_coincidence",
                "string_coincidence",
                "string_coincidence",
                "string_coincidence",
                "morphological_prefix",
                "exact",
                "exact",
            ],
        )

    def test_state_records_mechanical_a_and_product_decline(self) -> None:
        self.assertEqual(self.state["charter_version"], 1)
        self.assertEqual(self.state["cycle_status"], "COMPLETE_OUTCOME_A_MECHANICAL_ONLY")
        self.assertFalse(self.state["continue_recommended"])
        self.assertEqual(self.state["product_recommendation"], "DO_NOT_ADOPT_AS_IS")
        self.assertEqual(self.measurement["outcome"], "A_COMPONENT_EVIDENCE_RECOVERED")
        self.assertEqual(self.state["outcome"], "A_COMPONENT_EVIDENCE_RECOVERED_MECHANICAL_ONLY")
        report = (
            REPO_ROOT
            / "reports"
            / "frontier"
            / "frontier-counter-evidence-span-selection"
            / "REPORT.md"
        ).read_text(encoding="utf-8")
        contract = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "frontier"
                / "frontier-counter-evidence-span-selection"
                / "INTEGRATION_CONTRACT.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("DO_NOT_ADOPT_AS_IS", report)
        self.assertEqual(contract["adoption_recommendation"]["decision"], "DECLINE_AS_IS")
        self.assertIn("claim ceiling", report.lower())



if __name__ == "__main__":
    unittest.main()
