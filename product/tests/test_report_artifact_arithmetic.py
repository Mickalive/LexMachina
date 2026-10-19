"""Report-of-record arithmetic is DERIVED from the artifact, never typed.

Why this exists
---------------
The audit of rejected product cycle 39139648336 (round 3, repaired in round 4)
returned exactly one required fix: ``reports/product/CYCLE_39139648336.md`` §3 F1
described the live sourced answer as "(6 cited, live free model)" while the
artifact of record ``results/product/live_slice/CYCLE_39139648336_F1F2_VERIFY.json``
records ``answer.n_cited=5``, and the answer prose cites exactly those 5 retrieved
decisions. The report overstated the answer by one.

That is the same defect class as the 13 -> 17 test-count error this repair chain
corrected (audit F4), as RF2's "+7 tests" against a measured +10, and as RF-1's
false attribution of a +21 collected-test delta to the cycle that did not produce
it. Every occurrence was a number typed into prose instead of derived from the
measurement it summarises. The lane's rule for correcting such a number is RF2
arithmetic discipline - publish BOTH numbers, side by side, so the correction is
auditable rather than silent.

WHAT THIS GUARD DOES AND DOES NOT COVER (measured, not aspirational)
---------------------------------------------------------------------
Audit RF-2 of the round-4 cycle found the round-4 guard shipped with a claim that
overstated it ("the two ways the sweep could be weakened"), and measured three
escape paths it could not see. This module's scope is therefore stated as a
MEASUREMENT and pinned by ``test_measured_scope_is_published_not_aspirational``:

* covered: citation-count claims, in BOTH directions of phrasing, in every report
  that cites a live-slice artifact by filename (measured: 2 artifacts, 3
  artifact/report pairs, 13 parsed citation claims);
* covered since round 5: the inverted phrasing "cited N decisions", correction
  markers that must be word-boundary and same-sentence, and the internal
  arithmetic of any test-count decomposition ("+21 = +11 + +2 + +4 + +4") in any
  report, which needs no artifact to check;
* covered by a separate module (the attribution is a MEASUREMENT, not a prose
  claim): which commit produced each part of a collected-test delta -
  ``product/test_delta_attribution.py`` + ``product/tests/test_delta_attribution.py``;
* NOT covered, and named here as non-claims rather than left implicit: bare
  test-count claims ("924 collected") in a report that cites SEVERAL regression
  artifacts, or single-module pytest runs in a results table. A report states
  numbers from its own artifact while citing older ones, so attributing a bare
  number to "the artifact this report mentions" is ambiguous, not merely
  unswept. ``testcount_disclosure_artifact_is_current`` measures that candidate
  set on every run and fails if the published measurement has rotted, so the gap
  is a number that cannot quietly grow.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_SLICE_DIR = ROOT / "results" / "product" / "live_slice"
REPORTS_DIR = ROOT / "reports" / "product"
REGRESSION_DIR = ROOT / "results" / "product" / "regression"

#: The schema string ``product/live_slice.py`` stamps on every record it
#: writes. Selected by content, not by filename - see ``_live_slice_artifacts``.
LIVE_SLICE_SCHEMA = "product-live-slice/1"

#: The coverage measurement THIS module checks against. Named by file, not
#: "newest", because it is the artifact ``testcount_disclosure_artifact_is_current``
#: and ``test_measured_scope_is_published_not_aspirational`` compare a fresh
#: sweep to: a later cycle that re-publishes it must not silently change what an
#: earlier report says.
#:
#: PIN REPOINT, recorded TWICE. The pin previously named
#: ``CYCLE_39149741259_report_testcount_disclosure.json``, whose
#: ``bare_testcount_claims`` set is the ten-report candidate set measured in that
#: cycle's tree. The rejected cycle's own report of record,
#: ``CYCLE_39169296466.md``, cites a regression-scope artifact and carries ten
#: bare test-count claims, so it joined the candidate set: 11 live candidates
#: against 10 published, and ``testcount_disclosure_artifact_is_current`` was RED
#: on the very tree that cycle shipped. That is audit D1 of BLOCKED cycle
#: 39160624523 recurring - a staleness guard left behind when the tree grew -
#: and it survived because no ledger claim covered this module (audit F1b). The
#: guard names its own remedy ("re-measure and re-publish"), so it was followed
#: exactly: the sweep was re-run over the repaired tree and published under
#: ``CYCLE_39172315384``. The historical artifact stays on disk untouched as
#: that cycle's evidence and is guarded by
#: ``test_the_previous_disclosure_artifact_is_preserved_as_history``.
#:
#: SECOND PIN REPOINT, this cycle (39193356789). Same remedy, same cause, one
#: cycle later: ``_live_slice_artifacts`` below now selects records by ``schema``
#: rather than by the ``CYCLE_`` filename prefix, because ``live_slice.py`` stamps
#: ``--run-id`` verbatim and a run that omits the flag is named by a UTC
#: timestamp. Run 39187482610 committed ``20261019T022100Z.json``, which was
#: therefore outside the measured scope entirely. Measured effect of the re-point,
#: from the guard's own sweep: ``artifacts_swept`` 2 -> 3,
#: ``artifact_report_pairs`` 3 -> 6, ``citation_claims_parsed`` unchanged at 10.
#: Re-measured, not restated:
#: ``python3 product/report_scope_measurement.py --run-id 39193356789
#: --previous CYCLE_39172315384_report_testcount_disclosure.json
#: --pin-reason "..." --out
#: results/product/regression/CYCLE_39193356789_report_testcount_disclosure.json``.
DISCLOSURE = (ROOT / "results" / "product" / "regression"
              / "CYCLE_39193356789_report_testcount_disclosure.json")
#: The previous pin, kept as a readable constant so a reader can diff the two
#: artifacts instead of trusting prose about them.
DISCLOSURE_PREVIOUS_PIN = (ROOT / "results" / "product" / "regression"
                           / "CYCLE_39172315384_report_testcount_disclosure.json")
#: Every disclosure artifact this pin has ever named, oldest first, each of which
#: must still exist. A pin move moves a CHECK; it never removes evidence.
DISCLOSURE_HISTORY = (
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39149741259_report_testcount_disclosure.json",
    ROOT / "results" / "product" / "regression"
    / "CYCLE_39172315384_report_testcount_disclosure.json",
)

#: The PRE-REPAIR BYTES of the report of record, extracted once from git
#: (``git show 2b0b902:reports/product/CYCLE_39139648336.md``) and pinned by the
#: sha256 of those bytes. Round 4's negative control transcribed the defective
#: line by hand, which meant the control tested a copy rather than the artifact
#: (audit note N1). Reading the real bytes makes that note structurally
#: unanswerable: if the commit's report ever changes, the pin fails.
PRE_REPAIR_BYTES = (ROOT / "product" / "data" / "report_pre_repair_bytes"
                    / "CYCLE_39139648336_pre_repair.md")
PRE_REPAIR_SHA256 = "d4cd8345319bab9f6c058d0b08bc9153741a5cb5acf8b026ba523c9c11144326"

#: ``5 cited`` / ``**5 cited**`` / ``6 cited decisions`` - the count precedes the
#: word, optionally wrapped in emphasis. Matched per PARAGRAPH, so a claim that
#: wraps across a line break inside one paragraph is still seen.
_INLINE_CLAIM = re.compile(r"(?<![\w.])(\d+)\s*\*{0,2}\s*cited\b")
#: Round-5 extension: the INVERTED phrasing, count AFTER the word. Round 4 could
#: not see "the sourced answer cited 9 decisions from the live API" at all,
#: because its regex demanded the count to precede the word.
_INVERTED_CLAIM = re.compile(r"\bcited\s+\*{0,2}(\d+)\b")
#: ``answer.n_cited=5`` - the artifact's own field name used in prose.
_FIELD_CLAIM = re.compile(r"n_cited\s*=\s*(\d+)")
#: Paragraphs are blank-line separated in Markdown.
_PARAGRAPH = re.compile(r"\n[ \t]*\n")
#: Sentences within a paragraph, for scoping a correction marker to the claim it
#: corrects (round 5: a bare substring match over the whole paragraph let a
#: marker in an unrelated run-log line legitimise a wrong number).
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

#: ``+21 = +11 + +2 + +4 + +4`` - a test-count decomposition. Checkable with no
#: artifact at all: the parts must sum to the total they claim.
_DECOMPOSITION = re.compile(
    r"(?<![\w.])(\+?-?\d+)\s*(?:=|\u2192|->)\s*((?:\+(?:\s*\+)*\s*\d+\s*)+)"
)
#: One part of a decomposition, tolerating the spaced form "+11 + +2 + +4" that
#: the tool emits so the sentence stays readable in a Markdown paragraph.
_PART = re.compile(r"\+(?:\s*\+)*\s*\d+")


def _parse_parts(text: str) -> list[int]:
    out = []
    for raw in _PART.findall(text):
        cleaned = re.sub(r"\s+", "", raw)
        while "++" in cleaned:          # "+ +2" reads as "+2", not "2"
            cleaned = cleaned.replace("++", "+")
        out.append(int(cleaned))
    return out
#: What the parts of a decomposition are about - needed so the check does not
#: read an unrelated equation in prose as a test-count claim.
_DELTA_SUBJECT = re.compile(r"\b(collected|passed|failed|skipped|tests?)\b", re.I)

#: Markers that mean "this number is the SUPERSEDED one, not the claim".
#: Round 5: word-boundary patterns, so a JSON key like ``correction_marker_present``
#: or any other identifier that merely CONTAINS a marker word cannot license a
#: wrong number. Round 4 used a bare substring match, which both probes hit.
_CORRECTION_MARKERS = tuple(
    re.compile(pattern, re.I) for pattern in (
        r"\bpre-?repair\b",
        r"\bcorrections?\b",
        r"\bcorrected\b",
        r"\bsuperseded\b",
        r"\bsupersedes\b",
        r"\boverstat(?:ed|es|ing)\b",
        r"\baudit-?required\b",
        r"\brf2 arithmetic\b",
        r"\bwrong number\b",
        r"\berroneous\b",
        r"\bmis-?stated\b",
    )
)


def _paragraphs(text: str) -> list[str]:
    return [p for p in _PARAGRAPH.split(text) if p.strip()]


def _is_quoted(paragraph: str, position: int) -> bool:
    """True when ``position`` sits inside a quotation, not the report's own prose.

    Round 5, from a measured overclaim: the round-4 guard fired on its OWN report's
    §1, which VERBATIM QUOTES the audit's required-fix text ("the sourced answer is
    stated as '(6 cited, live free model)' but the artifact ... records n_cited=5").
    A report documenting what a defect said is not the report asserting it. Two
    contexts count as quotation: a Markdown blockquote (``>``-prefixed line) and a
    fenced code block. Both are excluded from the claim set rather than
    marker-scoped, because a marker cannot be conjured into someone else's words.

    Named non-claim: a wrong number hidden inside a quote is not detected here.
    That is a different defect (concealment, not drift) and is stated in the
    published scope disclosure rather than left implicit.
    """
    line_start = paragraph.rfind("\n", 0, position) + 1
    line_end = paragraph.find("\n", position)
    line = paragraph[line_start:line_end if line_end != -1 else len(paragraph)]
    if line.lstrip().startswith(">"):
        return True
    return paragraph[:position].count("```") % 2 == 1


def cited_claims(paragraph: str) -> list[int]:
    """Every citation-count claim made in one paragraph, both phrasings."""
    return [
        value for value, _ in _claim_hits(paragraph)
    ]


def _claim_hits(paragraph: str) -> list[tuple[int, int]]:
    """(value, position) of every citation-count claim in the report's OWN prose."""
    hits: list[tuple[int, int]] = []
    for pattern in (_INLINE_CLAIM, _INVERTED_CLAIM, _FIELD_CLAIM):
        for m in pattern.finditer(paragraph):
            if _is_quoted(paragraph, m.start()):
                continue
            hits.append((int(m.group(1)), m.start()))
    return hits


def _marked(paragraph: str, position: int) -> bool:
    """A correction marker in the SAME SENTENCE as ``position``.

    Sentence-scoped on purpose: round 4 matched markers anywhere in the paragraph,
    so a correction note in one sentence could launder an unmarked wrong number in
    another.
    """
    for sentence in _SENTENCE.split(paragraph):
        start = paragraph.find(sentence)
        if start <= position < start + len(sentence):
            return any(m.search(sentence) for m in _CORRECTION_MARKERS)
    return False


def violations(report_text: str, n_cited: int) -> list[dict]:
    """Paragraphs whose citation-count claim is neither the artifact's value
    nor an explicitly marked and locally corrected supersession of it."""
    out: list[dict] = []
    for para in _paragraphs(report_text):
        claims = cited_claims(para)
        if not claims:
            continue
        hits = _claim_hits(para)
        bad = sorted({value for value, _ in hits if value != n_cited})
        if not bad:
            continue
        # Every wrong claim must be marked in ITS OWN sentence, and the paragraph
        # must still carry the true value somewhere beside it (RF2 form).
        unmarked = [value for value, pos in hits
                    if value != n_cited and not _marked(para, pos)]
        true_value_present = n_cited in claims
        if unmarked or not true_value_present:
            out.append({
                "claimed": bad,
                "expected": n_cited,
                "correction_marker_present": not unmarked,
                "unmarked_claims": sorted(set(unmarked)),
                "true_value_present_in_paragraph": true_value_present,
                "excerpt": " ".join(para.split())[:240],
            })
    return out


def decomposition_violations(text: str) -> list[dict]:
    """Test-count decompositions whose parts do not sum to their own total.

    Artifact-free by construction: "the +21 = +17 + +4" form is wrong whether or
    not any artifact is in scope, which is why it is checkable across every
    report rather than only the ones that cite a live slice. Round 4's sweep could
    not see test-count arithmetic at all (audit RF-2 escape path 3).
    """
    out: list[dict] = []
    for para in _paragraphs(text):
        if not _DELTA_SUBJECT.search(para):
            continue
        for m in _DECOMPOSITION.finditer(para):
            total = int(m.group(1))
            parts = _parse_parts(m.group(2))
            if not parts:
                continue
            if sum(parts) == total:
                continue
            if _marked(para, m.start()) and re.search(rf"(?<![\w.+-]){re.escape(str(total))}\b", para):
                # A marked correction that shows the true total beside it is the
                # RF2 form; publishing both numbers is how this lane corrects.
                continue
            out.append({
                "claimed_total": total,
                "claimed_parts": parts,
                "parts_sum": sum(parts),
                "excerpt": " ".join(para.split())[:240],
            })
    return out


def _live_slice_artifacts() -> list[Path]:
    """Committed live-slice verification artifacts (never the bundles).

    GLOB REPAIR, this cycle.  This swept ``CYCLE_*.json`` only, and
    ``product/live_slice.py`` stamps ``--run-id`` into the artifact filename
    verbatim - a run that omits the flag is named by a UTC timestamp instead.
    So ``results/product/live_slice/20261019T022100Z.json``, committed by run
    39187482610, was outside EVERY live-slice sweep in this repository: no
    citation-count arithmetic, no report-of-record requirement, nothing.  That
    is how an artifact publishing ``verdict: "PASS"`` with a zero-citation
    answer and zero counter authorities reached the tree unexamined.

    The fix is to sweep the records the instrument actually writes, selected by
    content rather than by filename: any ``*.json`` in the directory whose
    ``schema`` is the live-slice record schema.  Bundles carry no ``schema`` key
    with that value, so they stay excluded, and a future artifact named anything
    at all is swept from now on.
    """
    out: list[Path] = []
    for path in sorted(LIVE_SLICE_DIR.glob("*.json")):
        if path.name.endswith("_bundle.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(payload, dict) and payload.get("schema") == LIVE_SLICE_SCHEMA:
            out.append(path)
    return out


def _reports_citing(name: str) -> list[Path]:
    """Reports of record that cite this artifact by filename."""
    return [
        p for p in sorted(REPORTS_DIR.glob("*.md"))
        if name in p.read_text(encoding="utf-8")
    ]


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_every_report_of_record_decomposition_sums_to_its_own_total():
    """The artifact-free half of the class: decomposition arithmetic, everywhere."""
    offenders: dict[str, list[dict]] = {}
    checked = 0
    for report in sorted(REPORTS_DIR.glob("*.md")):
        text = report.read_text(encoding="utf-8")
        hits = decomposition_violations(text)
        if not hits:
            continue
        offenders[report.name] = hits
        checked += len(hits)
    assert checked >= 0  # a sweep that cannot find a decomposition is not a failure
    assert not offenders, (
        "a report of record decomposes a count into parts that do not sum to it: "
        f"{offenders}")


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


def test_negative_control_sweeps_the_real_pre_repair_bytes():
    """The round-3 defect shape, swept from the ACTUAL git bytes.

    Round 4 hardcoded a faithful transcription of the defective line, so the
    control tested a copy and its report described it as "the pre-repair bytes of
    this very report" (audit note N1). The real bytes are committed once, pinned by
    the sha256 the audit published for ``git show 2b0b902:...``, and swept here.
    """
    assert PRE_REPAIR_BYTES.exists(), (
        f"the pinned pre-repair bytes are missing: {PRE_REPAIR_BYTES}")
    pinned = _sha256(PRE_REPAIR_BYTES)
    assert pinned == PRE_REPAIR_SHA256, (
        f"the pinned pre-repair bytes changed: sha256 {pinned} != the audit's "
        f"{PRE_REPAIR_SHA256}; if the commit's report moved, re-extract and "
        "re-derive rather than re-pin twice")

    hits = violations(PRE_REPAIR_BYTES.read_text(encoding="utf-8"), 5)
    assert hits, "the historical defect shape must fire on the real pre-repair bytes"
    assert [6] in [h["claimed"] for h in hits], (
        f"expected the pre-repair report to claim 6 against an artifact value of "
        f"5, got {hits}")

    corrected = violations((REPORTS_DIR / "CYCLE_39139648336.md").read_text(
        encoding="utf-8"), 5)
    assert corrected == [], f"the corrected report still violates: {corrected}"


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


def test_round_4_escape_paths_are_now_closed():
    """Audit RF-2's three measured escape paths, replayed against this guard.

    Each probe below is the auditor's own probe text. In round 4 none of them
    fired; if any of them stops firing again, the guard has silently narrowed.
    """
    # 1. inverted phrasing
    assert violations("The sourced answer cited 9 decisions from the live API.", 5), (
        "the inverted phrasing escape path is open again")
    # 2a. incidental correction marker in the same paragraph, different sentence
    assert violations(
        "A correction: the answer cited 9 decisions from the live API.", 5), (
        "a correction marker in an unrelated sentence must not license a wrong number")
    # 2b. a run-log line that merely CONTAINS the marker word
    assert violations(
        'The run log printed {"correction_marker_present": false} and the answer '
        "cited 9 decisions.", 5), (
        "an identifier containing a marker word must not license a wrong number")
    # 3. test-count arithmetic is a different class; it is now covered by
    #    decomposition_violations, which needs no artifact:
    assert decomposition_violations(
        "The collected-test delta is +21 = +17 + +6 across the two cycles."), (
        "a decomposition whose parts do not sum to its total must fire")
    #    ...and the round-4 sentence, whose arithmetic was CORRECT and whose
    #    ATTRIBUTION was false, must still pass here - the defect it had was not
    #    an arithmetic one, and the attribution is measured by the other module:
    assert decomposition_violations(
        "The collected-test delta is +21 = +17 + +4 across the two cycles.") == []


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


def test_measured_scope_is_published_not_aspirational():
    """The guard's coverage is a MEASUREMENT that is asserted, not a claim.

    Round 4 asserted that the controls "pin the two ways the sweep could be
    weakened"; the auditor measured at least two further escape paths plus a
    scope gap. The lesson is published here as a live measurement of this
    sweep's real coverage so the number cannot be quietly overstated upward.
    """
    artifacts = _live_slice_artifacts()
    pairs = 0
    claims = 0
    for art in artifacts:
        payload = json.loads(art.read_text(encoding="utf-8"))
        n_cited = (payload.get("answer") or {}).get("n_cited")
        if not isinstance(n_cited, int):
            continue
        for report in _reports_citing(art.name):
            pairs += 1
            claims += len(cited_claims(report.read_text(encoding="utf-8")))

    disclosure = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
    assert pairs == disclosure["citation_sweep"]["artifact_report_pairs"], (
        f"measured {pairs} artifact/report pairs but the published scope says "
        f"{disclosure['citation_sweep']['artifact_report_pairs']}; the published "
        "scope is stale and must be re-measured, not restated")
    assert claims == disclosure["citation_sweep"]["citation_claims_parsed"], (
        f"measured {claims} citation claims but the published scope says "
        f"{disclosure['citation_sweep']['citation_claims_parsed']}")
    assert disclosure["non_claims"], (
        "the disclosure must name what the sweep does NOT cover; an unnamed gap "
        "is how the round-4 overclaim happened")


def citation_claim_coverage() -> dict:
    """Measured coverage of the citation sweep, quoted and own-prose separated.

    ``claims_in_own_prose`` is what the guard actually checks; ``claims_in_quotation``
    is reported beside it so the difference between this and a round-4 reading is a
    published number instead of a discrepancy an auditor has to rediscover.
    """
    pairs = own = quoted = 0
    artifacts: list[str] = []
    for art in _live_slice_artifacts():
        payload = json.loads(art.read_text(encoding="utf-8"))
        if not isinstance((payload.get("answer") or {}).get("n_cited"), int):
            continue
        artifacts.append(art.name)
        for report in _reports_citing(art.name):
            pairs += 1
            for para in _paragraphs(report.read_text(encoding="utf-8")):
                own += len(_claim_hits(para))
                all_hits = sum(
                    1 for pattern in (_INLINE_CLAIM, _INVERTED_CLAIM, _FIELD_CLAIM)
                    for _ in pattern.finditer(para))
                quoted += all_hits - len(_claim_hits(para))
    return {
        "artifacts_swept": artifacts,
        "artifact_report_pairs": pairs,
        "citation_claims_parsed": own,
        "claims_excluded_as_quotation": quoted,
    }


def sweep_testcount_candidates() -> dict:
    """Bare test-count claims, per report, over the artifacts that report cites.

    Deliberately a MEASUREMENT, not an assertion: a report states numbers from its
    OWN artifact while citing older ones, so a bare "924 collected" cannot be
    attributed to "an artifact this report mentions" without inventing a defect.
    The candidate set is published so the gap is a number rather than a silence.
    """
    count_pattern = re.compile(
        r"(?<![\w.+-])(\d+)\s*\*{0,2}\s*(collected|passed|failed|skipped)\b"
        r"|\b(collected|passed|failed|skipped)\b\s*[:=]\s*\*{0,2}\s*(\d+)", re.I)
    per_report: dict[str, dict] = {}
    for report in sorted(REPORTS_DIR.glob("*.md")):
        text = report.read_text(encoding="utf-8")
        cited = sorted({p.name for p in REGRESSION_DIR.glob("CYCLE_*_regression_scope.json")
                        if p.name in text})
        if not cited:
            continue
        claims = sum(len(count_pattern.findall(p)) for p in _paragraphs(text))
        per_report[report.name] = {
            "regression_artifacts_cited": len(cited),
            "bare_testcount_claims": claims,
            "ambiguous_by_construction": len(cited) > 1,
        }
    return per_report


def testcount_disclosure_artifact_is_current():
    """The published non-coverage measurement must match a fresh sweep.

    Fail-closed against rot: if reports or artifacts move, this fails rather than
    leaving a stale "we measured this" claim in the tree.
    """
    live = sweep_testcount_candidates()
    published = json.loads(DISCLOSURE.read_text(encoding="utf-8"))["bare_testcount_claims"]
    assert set(published) == set(live), (
        "the set of reports with bare test-count claims moved; re-measure and "
        f"re-publish: published {sorted(set(published) ^ set(live))}")
    for name, entry in live.items():
        assert published[name]["bare_testcount_claims"] == entry["bare_testcount_claims"], (
            f"{name}: the bare test-count claim count moved "
            f"({published[name]['bare_testcount_claims']} -> "
            f"{entry['bare_testcount_claims']}); re-measure the disclosure")
    assert live, "the candidate sweep found no reports at all - it is vacuous"


def test_the_previous_disclosure_artifact_is_preserved_as_history():
    """The re-pointed pin moves a CHECK, never a piece of evidence.

    Every disclosure artifact this pin has named must still exist on disk with
    its own ``run_id`` and schema intact, and the newest must still name the one
    it replaced. Re-pointing DISCLOSURE must never delete or rewrite one: the
    reason the pin moved is recorded at the constant, and the old numbers stay
    readable so a reader can compare the artifacts instead of trusting prose
    about them. This is the same preservation contract
    ``product/tests/test_delta_attribution.py`` applies to the sibling
    attribution pin.

    The pin has now moved twice (39169296466 -> 39172315384 -> 39193356789), so
    this test follows ``DISCLOSURE_HISTORY`` rather than hard-coding one run id.
    """
    assert DISCLOSURE_PREVIOUS_PIN.exists(), (
        "the historical disclosure artifact the previous pin named is gone - a "
        "pin move must never remove evidence")
    assert DISCLOSURE_PREVIOUS_PIN in DISCLOSURE_HISTORY
    for path in DISCLOSURE_HISTORY:
        assert path.exists(), f"disclosure artifact {path.name} was removed"
        historical = json.loads(path.read_text(encoding="utf-8"))
        assert historical["schema"] == "product-report-arithmetic-scope/1", (
            f"{path.name}'s schema was rewritten")
        assert historical["run_id"] is not None, (
            f"{path.name} no longer records the run it was published for")

    historical_reports = set(
        json.loads(DISCLOSURE_HISTORY[0].read_text(encoding="utf-8"))["bare_testcount_claims"])
    current = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
    current_reports = set(current["bare_testcount_claims"])
    # The re-publish may ADD reports (that is what the pin moved for) and it may
    # update a report's claim count; it may not DROP one without a reason.
    assert historical_reports <= current_reports, (
        "the re-published disclosure dropped a report the historical measurement "
        f"carried: {sorted(historical_reports - current_reports)}")
    assert current["pin_repoint"]["previous_artifact"] == DISCLOSURE_PREVIOUS_PIN.name, (
        "the re-published disclosure does not name the artifact it replaced, so "
        "the pin move is not auditable from the artifact alone")
    assert current["pin_repoint"]["reason"], (
        "the re-published disclosure records no reason for the pin move")


def test_the_current_pin_is_measured_on_this_cycle_not_copied_from_the_previous():
    """The re-publish must be a MEASUREMENT of this tree, not an edited copy."""
    current = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
    live = sweep_testcount_candidates()
    assert set(current["bare_testcount_claims"]) == set(live), (
        "the pinned disclosure does not match a fresh sweep of this tree; "
        "re-measure rather than edit the artifact by hand")
    for name, entry in live.items():
        assert current["bare_testcount_claims"][name]["bare_testcount_claims"] == \
            entry["bare_testcount_claims"], (
            f"{name}: the published claim count {current['bare_testcount_claims'][name]['bare_testcount_claims']} "
            f"is not what a fresh sweep measures ({entry['bare_testcount_claims']})")

def test_quotation_is_excluded_and_that_exclusion_is_bounded():
    """The quote-context exclusion is a boundary, stated in both directions.

    Round 5 found the sentence-scoped marker predicate firing on the round-4
    report's own §1, which quotes the audit's required-fix text verbatim. A report
    documenting what a defect said is not the report asserting it - but the
    exclusion must not become a laundering channel, so the SAME number in the
    report's own prose must still fire, in the same paragraph as the quote.
    """
    quoted_only = (
        "> Correct reports/product/CYCLE_39139648336.md §3 F1: the sourced answer is "
        "stated as '(6 cited, live free model)' but the artifact of record records "
        "n_cited=5.\n"
    )
    assert violations(quoted_only, 5) == [], (
        "a verbatim quotation of a defect must not be re-counted as this report's claim")

    quote_plus_own_claim = (
        "> the pre-repair text said (6 cited, live free model)\n"
    ) + (
        "\n"
        "The live slice ran with 6 cited decisions."
    )
    assert violations(quote_plus_own_claim, 5), (
        "quoting the defect must not excuse the report's own unmarked claim of the "
        "same wrong number")
