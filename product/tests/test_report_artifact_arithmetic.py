"""Report-of-record citation counts are DERIVED from the artifact, never typed.

Why this exists
---------------
The audit of rejected product cycle 39139648336 (round 3, repaired in round 4)
returned exactly one required fix: ``reports/product/CYCLE_39139648336.md`` §3 F1
described the live sourced answer as "(6 cited, live free model)" while the
artifact of record ``results/product/live_slice/CYCLE_39139648336_F1F2_VERIFY.json``
records ``answer.n_cited=5``, and the answer prose cites exactly those 5 retrieved
decisions (``bger_6B_750_2020``, ``bger_6B_7_2014``, ``bger_6B_124_2016``,
``bger_6B_31_2019``, ``bstger_CN.2024.18``). The report overstated the answer by one.

That is the same defect class as the 13 -> 17 test-count error this same repair
chain corrected (audit F4) and as RF2's "+7 tests": a number typed into prose
instead of derived from the measurement it summarises. The lane's rule for
correcting such a number is RF2 arithmetic discipline - publish BOTH numbers,
side by side, so the correction is auditable rather than silent.

What this module does
---------------------
It sweeps every committed live-slice verification artifact that carries an
integer ``answer.n_cited``, finds the reports of record that cite that artifact
by name, and requires every citation-count claim in those reports to be either

* equal to the artifact's ``n_cited``; or
* an explicitly SUPERSEDED claim that sits in the same paragraph as (a) a
  correction marker and (b) the true value.

A wrong number appearing with neither a marker nor the true value beside it
fails the build - which is exactly the shape the round-3 report carried. The
controls below prove the predicate fires on that historical defect shape (the
sweep is not vacuous) and that it still accepts both honest text and a properly
marked correction.

Scope is deliberate: only reports that CITE a live-slice artifact are swept.
Historical reports describing other runs' bundles are out of scope and are never
rewritten - reports are evidence, and this lane does not edit numbers it did not
measure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_SLICE_DIR = ROOT / "results" / "product" / "live_slice"
REPORTS_DIR = ROOT / "reports" / "product"

#: ``5 cited`` / ``**5 cited**`` / ``6 cited decisions`` - the count precedes the
#: word, optionally wrapped in emphasis. Matched per PARAGRAPH, so a claim that
#: wraps across a line break inside one paragraph is still seen.
_INLINE_CLAIM = re.compile(r"(?<![\w.])(\d+)\s*\*{0,2}\s*cited\b")
#: ``answer.n_cited=5`` - the artifact's own field name used in prose.
_FIELD_CLAIM = re.compile(r"n_cited\s*=\s*(\d+)")
#: Paragraphs are blank-line separated in Markdown.
_PARAGRAPH = re.compile(r"\n[ \t]*\n")

#: Markers that mean "this number is the SUPERSEDED one, not the claim".
#: Chosen so that a bare wrong number never qualifies: every marker asserts in
#: words that the text is correcting something.
_CORRECTION_MARKERS = (
    "pre-repair",
    "pre-repair text",
    "correction",
    "corrected",
    "superseded",
    "supersede",
    "overstated",
    "overstate",
    "audit-required",
    "rf2 arithmetic",
    "wrong number",
    "erroneous",
    "misstated",
    "mis-stated",
)


def _paragraphs(text: str) -> list[str]:
    return [p for p in _PARAGRAPH.split(text) if p.strip()]


def cited_claims(paragraph: str) -> list[int]:
    """Every citation-count claim made in one paragraph, both phrasings."""
    return (
        [int(m.group(1)) for m in _INLINE_CLAIM.finditer(paragraph)]
        + [int(m.group(1)) for m in _FIELD_CLAIM.finditer(paragraph)]
    )


def violations(report_text: str, n_cited: int) -> list[dict]:
    """Paragraphs whose citation-count claim is neither the artifact's value
    nor an explicitly marked and locally corrected supersession of it."""
    out: list[dict] = []
    for para in _paragraphs(report_text):
        claims = cited_claims(para)
        if not claims:
            continue
        bad = sorted({c for c in claims if c != n_cited})
        if not bad:
            continue
        marked = any(marker in para.lower() for marker in _CORRECTION_MARKERS)
        true_value_present = n_cited in claims
        if not (marked and true_value_present):
            out.append({
                "claimed": bad,
                "expected": n_cited,
                "correction_marker_present": marked,
                "true_value_present_in_paragraph": true_value_present,
                "excerpt": " ".join(para.split())[:240],
            })
    return out


def _live_slice_artifacts() -> list[Path]:
    """Committed live-slice verification artifacts (never the bundles)."""
    return [
        p for p in sorted(LIVE_SLICE_DIR.glob("CYCLE_*.json"))
        if not p.name.endswith("_bundle.json")
    ]


def _reports_citing(name: str) -> list[Path]:
    """Reports of record that cite this artifact by filename."""
    return [
        p for p in sorted(REPORTS_DIR.glob("*.md"))
        if name in p.read_text(encoding="utf-8")
    ]


def test_every_live_slice_report_cites_its_artifact_s_own_count():
    """The sweep itself: report numbers must equal the artifact they cite."""
    artifacts = _live_slice_artifacts()
    assert artifacts, f"no committed live-slice artifacts under {LIVE_SLICE_DIR}"

    offenders: dict[str, list[dict]] = {}
    checked_pairs = 0
    claims_seen = 0
    for art in artifacts:
        payload = json.loads(art.read_text(encoding="utf-8"))
        n_cited = (payload.get("answer") or {}).get("n_cited")
        assert isinstance(n_cited, int), (
            f"{art.name} carries no integer answer.n_cited - the sweep would "
            "degrade to a no-op instead of failing, which is the silent-zero "
            "defect this lane refuses")
        reports = _reports_citing(art.name)
        assert reports, (
            f"artifact {art.name} is cited by no report under {REPORTS_DIR} - "
            "an artifact with no report of record makes the sweep vacuous")
        for report in reports:
            checked_pairs += 1
            claims_seen += len(cited_claims(report.read_text(encoding="utf-8")))
            hits = violations(report.read_text(encoding="utf-8"), n_cited)
            if hits:
                offenders[str(report.relative_to(ROOT))] = hits

    # Non-vacuity: this cycle actually swept more than one pairing and actually
    # parsed citation claims out of the prose it checked.
    assert checked_pairs >= 2, f"only {checked_pairs} artifact/report pairs swept"
    assert claims_seen >= 2, f"only {claims_seen} citation claims parsed"
    assert not offenders, (
        "a report of record states a citation count its own artifact of record "
        f"does not support (RF2 arithmetic discipline): {offenders}")


def test_rejected_cycle_39139648336_report_now_agrees_with_its_artifact():
    """The ordered fix of rejected cycle 39139648336, pinned as an executable check.

    The audit's required_fixes item was one number: §3 F1 said "6 cited" where
    the artifact says ``answer.n_cited=5``. This asserts both halves - the
    artifact still records 5, and the corrected report of record no longer
    claims 6 except as an explicitly marked, locally corrected supersession.
    """
    art = LIVE_SLICE_DIR / "CYCLE_39139648336_F1F2_VERIFY.json"
    payload = json.loads(art.read_text(encoding="utf-8"))
    n_cited = payload["answer"]["n_cited"]
    assert n_cited == 5, (
        f"the artifact of record moved: answer.n_cited={n_cited}, not the 5 the "
        "audit measured - re-derive, do not restate")

    report_path = REPORTS_DIR / "CYCLE_39139648336.md"
    assert report_path.exists(), "the report of record for 39139648336 is missing"
    text = report_path.read_text(encoding="utf-8")
    hits = violations(text, n_cited)
    assert not hits, (
        "the ordered citation-count fix is not in the report of record: "
        f"{hits}")


def test_sweep_fires_on_the_exact_historical_defect_shape():
    """Negative control: the predicate must detect the round-3 defect.

    Reproduced verbatim from the rejected report's own line, then from the same
    line with the true value or the marker removed - each of which must still
    fire, or the sweep would pass text that is wrong in exactly the way the
    audit found.
    """
    wrong_plain = (
        "  The 158-decision vertical slice — retrieval → bundle → sourced answer "
        "(6 cited, live free model)\n  → counter-authority pass → clickable map"
    )
    assert violations(wrong_plain, 5), "the historical defect shape must fire"

    # marker alone is not enough: the true value must be beside it
    marker_only = (
        "**Cited-count correction:** this report's pre-repair text said "
        "**6 cited**, and the answer is described below."
    )
    assert violations(marker_only, 5), (
        "a marked supersession with no true value in the paragraph must fire")

    # true value alone is not enough: it must be marked as a correction
    value_only = "the prose said **6 cited** while n_cited=5"
    assert violations(value_only, 5), (
        "an unmarked wrong number next to the right one must fire - that is a "
        "contradiction, not a correction")


def test_sweep_accepts_honest_text_and_a_properly_marked_correction():
    """Positive controls: honest counts and RF2-style corrections still pass."""
    honest = (
        "answer is **not** degraded: provider `opencode/mimo-v2.6-flash-free`, "
        "`status=ready`, **6 cited\n"
        "decisions** (`bger_6B_750_2020`, `bger_6B_124_2016`)"
    )
    assert violations(honest, 6) == [], "an artifact-matching count must pass"

    corrected = (
        "**Cited-count correction (audit-required fix; RF2 arithmetic discipline):**\n"
        "this report's pre-repair text said **6 cited**, which overstated the "
        "answer by one; the artifact of record says `answer.n_cited=5`. Both "
        "numbers are published side by side so the correction is auditable."
    )
    assert violations(corrected, 5) == [], (
        "a marked correction carrying both numbers is exactly RF2 discipline "
        "and must pass")
