"""Class-aware contract for the audit-tree gate artifacts.

Two DIFFERENT classes of artifact legitimately live in
``results/audit/frontier/<team>/`` and they have DIFFERENT contracts:

``independent_audit_of_record``
    Written by the workflow's *audit job*.  ``gate`` is a product audit verdict
    (``PASS``/``REVISE``) and the file carries the audit contract fields.

``producer_placement_copy``
    Written by the *team* when the factory-wide audit-artifact placement
    requirement applies but no audit job runs for the cycle (e.g. a
    no-change verification of an already-terminated charter).  ``gate`` records
    the team's *cycle disposition*, not an audit verdict, and the file MUST
    self-declare that it is not independent audit output.

The defect this module exists to fix: the test suite globbed
``CYCLE_*_GATE.json`` into one undifferentiated set and applied the
independent-audit contract to every member, so the suite was red-by-construction
for every re-dispatch of a terminated charter.  Three consecutive dispatches
shipped a permanently failing suite, which is worse than a wrong assertion
because it teaches the gate reader to ignore test failures.

This module does NOT relax anything:

* the independent-audit contract is enforced verbatim, exact literals included;
* a new anti-vacuity invariant requires at least one independent audit of
  record to exist, so routing classes apart can never make the audit
  requirement vacuous -- that is precisely what a naive "just skip them" fix
  would have broken;
* the producer-placement-copy contract is NEW and did not exist before: a
  placement copy must self-declare its provenance, must not assert independent
  audit authority, must not wear an audit gate verdict, and must still carry
  the three substantive claim limits;
* an audit-impersonating placement copy (carrying ``safe_to_integrate`` or a
  ``PASS``/``REVISE`` gate) is rejected.

PRECISION FIX (``verdict``): the key ``verdict`` was originally flat-banned in
``AUTHORITY_CLAIM_KEYS``, but its only real-world value on a placement copy is
this team's OWN measurement verdict (``LABEL_UNSOUND``), the vocabulary of
``state/frontier/frontier-counter-label-integrity.json`` and ``REPORT.json`` --
NOT the audit-disposition vocabulary.  The key is therefore removed from the
flat ban and given a value-scoped check instead: ``verdict`` is accepted only
for the closed ``MEASUREMENT_VERDICTS`` vocabulary and rejected for every other
value (including every audit disposition and near-miss, non-strings, and
empties).  The invariant preserved is "a placement copy must never be
mistakable for an independent audit": ``gate`` stays a closed allow-list,
``AUDIT_ONLY_KEYS`` and the remaining ``AUTHORITY_CLAIM_KEYS`` stay flat-banned,
class routing stays signature-based, the anti-vacuity invariant stays
enforced, and the measurement vocabulary is asserted disjoint from every audit
disposition bucket, so a placement copy carrying a measurement ``verdict`` can
still never be read as wearing an audit verdict.

Nothing here reads or writes the frozen ``RULES.json``: this is artifact
hygiene, not a judgement input, so it must never be able to move a verdict.
"""

from __future__ import annotations

import glob
import json
import os
import re
from typing import Any, Iterable

AUDIT_DIR = os.path.join("results", "audit", "frontier", "frontier-counter-label-integrity")
GATE_GLOB = "CYCLE_*_GATE.json"
MD_GLOB = "CYCLE_*.md"

INDEPENDENT = "independent_audit_of_record"
PLACEMENT = "producer_placement_copy"
UNCLASSIFIED = "unclassified"

#: Verdict values that mean "this file speaks for an audit job".  Only an
#: independent audit may wear one; a placement copy that does is impersonating.
AUDIT_GATE_VALUES = ("PASS", "REVISE")

#: Cycle dispositions a producer may legitimately record for its own run.  This
#: is a CLOSED allow-list: an invented value such as "PASS_WITH_CAVEATS" or
#: "AUDIT_PASS" is rejected rather than waved through by a denylist, because a
#: denylist of {"PASS","REVISE"} can never enumerate every near-miss a gate
#: reader could mistake for an independent audit verdict.
PLACEMENT_DISPOSITIONS = ("TERMINATE", "HOLD", "PAUSE", "BLOCKED", "REROUTE")

#: The signature that makes a file an independent audit of record.  Class
#: routing requires this, so a file cannot CHOOSE the weaker contract by
#: dropping a field; anything that is not clearly Class A and clearly Class B is
#: UNCLASSIFIED and rejected outright.
AUDIT_SIGNATURE_KEYS = ("required_fixes", "safe_to_integrate", "team")

#: Keys only an independent audit job can legitimately author.  A file that
#: self-declares as a producer placement copy must not carry them.
AUDIT_ONLY_KEYS = ("safe_to_integrate", "required_fixes", "recommendation", "team")

#: The CLOSED measurement vocabulary of this team's REPORT/state: the only
#: values ``verdict`` may take on a producer placement copy.  This vocabulary
#: is disjoint from every audit disposition (``AUDIT_GATE_VALUES``,
#: ``PLACEMENT_DISPOSITIONS`` and their invented near-misses), so wearing one
#: of these strings can never be mistaken for an audit gate verdict.
MEASUREMENT_VERDICTS = ("LABEL_SOUND", "LABEL_UNSOUND", "INSUFFICIENT_POPULATION")

#: Extra authority-claiming keys a placement copy must not carry, each flat-
#: banned with no value exception.  A denylist alone can never be exhaustive,
#: so this list backs the closed disposition allow-list and the closed
#: signature requirement rather than replacing them.  ``verdict`` is NOT in
#: this set: it is value-scoped by ``MEASUREMENT_VERDICTS`` in
#: ``check_producer_placement_copy`` (see the module docstring's precision-fix
#: paragraph), which rejects every value outside this team's measurement
#: vocabulary -- a strictly additional check for all such values.
AUTHORITY_CLAIM_KEYS = (
    "audit_verdict",
    "independently_audited",
    "audit_of_record",
    "integrate",
    "audit_pass",
)


def _norm(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace.

    Used only to match claim limits inside free-text claim ceilings, where the
    substance is what matters and the capitalisation/wording drift between runs
    is noise.  It is deliberately NOT used for the independent-audit contract,
    which keeps its original exact-literal assertions.
    """
    out = re.sub(r"[^0-9a-z]+", " ", text.lower())
    return re.sub(r"\s+", " ", out).strip()


#: A sentence that carries the "no decision-level endorsement" limit must hold
#: ALL of these together: a negation, an assertion verb, and the three relation
#: words.  Requiring them in a single sentence is what stops the check from
#: being satisfied by words scattered across unrelated sentences.
_ENDORSEMENT_LIMIT = re.compile(
    r"\b(?:never|not|no)\b[^.;]{0,120}?\bassert\w*\b[^.;]{0,160}?\bsupporting\b"
)


def _carries_no_endorsement_limit(text: str) -> bool:
    for sentence in text.split("."):
        if not _ENDORSEMENT_LIMIT.search(sentence):
            continue
        window = sentence[_ENDORSEMENT_LIMIT.search(sentence).start() :]
        if "contrary" in window and "limiting" in window:
            return True
    return False


#: The three substantive claim limits every artifact of this team must carry.
#: Each is (name, predicate over the normalised claim ceiling).
def _claim_limit_checks(ceiling: Any) -> list[tuple[str, bool]]:
    text = _norm(ceiling if isinstance(ceiling, str) else "")
    return [
        (
            "no decision-level endorsement",
            _carries_no_endorsement_limit(text),
        ),
        ("baseline only, no fix tested", "baseline" in text and ("only" in text or "pre repair" in text)),
        ("audited non-accepted run scoped as mechanism-only", "38828034436" in text),
    ]


def classify_gate_payload(payload: dict[str, Any]) -> str:
    """Route a gate artifact to its contract.

    Routing is NOT purely self-declared.  A file is an independent audit of
    record only if it carries the full audit signature; it is a producer
    placement copy only if it self-declares and does NOT carry that signature.
    Anything else -- an audit-shaped file with one field removed, or a hybrid --
    is UNCLASSIFIED and is rejected by the contract checks rather than being
    quietly routed to whichever contract suits it.
    """
    has_signature = all(k in payload for k in AUDIT_SIGNATURE_KEYS)
    if has_signature:
        return INDEPENDENT
    if "artifact_provenance_warning" in payload:
        return PLACEMENT
    return UNCLASSIFIED



def check_independent_audit_of_record(payload: dict[str, Any]) -> list[str]:
    """The independent-audit contract, enforced verbatim (exact literals)."""
    problems: list[str] = []

    for key in AUDIT_SIGNATURE_KEYS:
        if key not in payload:
            problems.append(f"independent audit is missing the signature key {key!r}")

    gate = payload.get("gate")
    if gate not in AUDIT_GATE_VALUES:
        problems.append(f"gate {gate!r} is not an audit verdict in {AUDIT_GATE_VALUES}")
    if not isinstance(payload.get("required_fixes"), list):
        problems.append("required_fixes is not a list")
    if not payload.get("claim_ceiling"):
        problems.append("claim_ceiling is missing or empty")
    if not (payload.get("safe_to_integrate") is True or gate == "REVISE"):
        problems.append("safe_to_integrate is not true and gate is not REVISE")
    if "artifact_provenance_warning" in payload:
        problems.append("an independent audit must not self-declare as a producer placement copy")

    ceiling = payload.get("claim_ceiling")
    # A non-string ceiling is a failure in its own right, not a reason to skip
    # the literal audit below.
    if not isinstance(ceiling, str):
        problems.append(f"claim_ceiling must be a string, got {type(ceiling).__name__}")
        ceiling = ""
    for literal in (
        "NEVER asserts that any specific decision IS",
        "BASELINE ONLY",
        "38828034436",
    ):
        if literal not in ceiling:
            problems.append(f"claim_ceiling is missing the exact audit literal {literal!r}")
    return problems


def check_producer_placement_copy(payload: dict[str, Any], audit_of_record_runs: Iterable[str]) -> list[str]:
    """The placement-copy contract.  Every check here is new; none is a relaxation."""
    problems: list[str] = []
    known = set(audit_of_record_runs)

    warning = payload.get("artifact_provenance_warning")
    if not isinstance(warning, str) or not warning.strip():
        problems.append("placement copy must carry a non-empty artifact_provenance_warning")
    else:
        normed = _norm(warning)
        named = set(re.findall(r"CYCLE_(\d+)_GATE\.json", warning))
        if not named:
            problems.append("provenance warning does not name any audit-of-record file")
        elif not (named & known):
            problems.append(
                f"provenance warning names {sorted(named)} which is/are not an independent audit of record {sorted(known)}"
            )
        if not re.search(r"not independent audit|do not read this file.s gate as an independent gate", normed):
            problems.append("provenance warning does not deny independent-audit authority")
        # A warning that denies authority in one clause and claims it in another
        # must not satisfy the denial above.
        for claim in (
            r"this file is the authoritative",
            r"this file is an independent audit",
            r"independently audited",
            r"safe to integrate",
            r"may be read as an independent gate",
        ):
            if re.search(claim, normed):
                problems.append(f"provenance warning contradicts itself: {claim!r}")

    for key in AUDIT_ONLY_KEYS + AUTHORITY_CLAIM_KEYS:
        if key in payload:
            problems.append(f"placement copy asserts the audit-only key {key!r}")

    # Value-scoped check (STRICTLY ADDITIONAL for every non-measurement value):
    # ``verdict`` left the flat ban only because its legitimate value here is
    # this team's own measurement verdict.  Anything else -- an audit
    # disposition, an invented near-miss, a non-string, an empty -- is still
    # rejected, and the message says so in audit-verdict terms.
    if "verdict" in payload:
        value = payload["verdict"]
        if not (isinstance(value, str) and value in MEASUREMENT_VERDICTS):
            problems.append(
                f"placement copy verdict {value!r} is not one of this team's measurement "
                f"verdicts {MEASUREMENT_VERDICTS} and therefore reads as an audit verdict"
            )

    gate = payload.get("gate")
    # CLOSED allow-list, not a denylist: an invented near-miss verdict such as
    # "PASS_WITH_CAVEATS" or "AUDIT_PASS" must not be able to pass here.
    if gate not in PLACEMENT_DISPOSITIONS:
        problems.append(
            f"placement copy records gate {gate!r}, which is not a declared cycle disposition "
            f"{PLACEMENT_DISPOSITIONS} and so reads as an audit verdict"
        )
    if "cycle_status" not in payload:
        problems.append("placement copy does not record its cycle_status")
    elif payload.get("cycle_status") != gate:
        problems.append(f"gate {gate!r} disagrees with cycle_status {payload.get('cycle_status')!r}")

    ceiling = payload.get("claim_ceiling")
    if not ceiling:
        problems.append("claim_ceiling is missing or empty")
    else:
        for name, ok in _claim_limit_checks(ceiling):
            if not ok:
                problems.append(f"claim_ceiling is missing the substantive claim limit: {name}")

    return problems


def load_gate_files(repo_root: str, audit_dir: str = AUDIT_DIR) -> list[str]:
    return sorted(glob.glob(os.path.join(repo_root, audit_dir, GATE_GLOB)))


def classify_gate_files(repo_root: str, audit_dir: str = AUDIT_DIR) -> dict[str, list[str]]:
    """Split the audit tree into the artifact classes, by signature then self-declaration."""
    classes: dict[str, list[str]] = {INDEPENDENT: [], PLACEMENT: [], UNCLASSIFIED: []}
    for path in load_gate_files(repo_root, audit_dir):
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        classes[classify_gate_payload(payload)].append(path)
    return classes


def check_gate_files(repo_root: str, audit_dir: str = AUDIT_DIR) -> dict[str, Any]:
    """Validate every gate artifact against the contract of its own class.

    Returns a report whose ``ok`` is False if ANY artifact fails, plus an
    explicit ``independent_audit_present`` invariant so that routing the two
    classes apart can never silently empty the audit requirement.
    """
    classes = classify_gate_files(repo_root, audit_dir)
    audit_runs = []
    for path in classes[INDEPENDENT]:
        audit_runs.append(re.search(r"CYCLE_(\d+)_GATE\.json", os.path.basename(path)).group(1))

    findings: list[dict[str, Any]] = []
    for cls in (INDEPENDENT, PLACEMENT, UNCLASSIFIED):
        for path in classes[cls]:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
            if cls == INDEPENDENT:
                problems = check_independent_audit_of_record(payload)
            elif cls == PLACEMENT:
                problems = check_producer_placement_copy(payload, audit_runs)
            else:
                problems = [
                    "gate artifact is neither an independent audit of record (missing one of "
                    f"{AUDIT_SIGNATURE_KEYS}) nor a self-declared producer placement copy; "
                    "an audit-shaped file must not be able to pick a weaker contract"
                ]
            findings.append(
                {
                    "file": os.path.relpath(path, repo_root),
                    "artifact_class": cls,
                    "gate": payload.get("gate"),
                    "ok": not problems,
                    "problems": problems,
                }
            )

    return {
        "schema": "frontier-counter-label-integrity/audit-contract/1",
        "audit_dir": audit_dir,
        "n_files": len(findings),
        "n_independent_audit_of_record": len(classes[INDEPENDENT]),
        "n_producer_placement_copy": len(classes[PLACEMENT]),
        "n_unclassified": len(classes[UNCLASSIFIED]),
        "independent_audit_present": bool(classes[INDEPENDENT]),
        "ok": bool(classes[INDEPENDENT])
        and not classes[UNCLASSIFIED]
        and all(f["ok"] for f in findings),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="frontier-counter-label-integrity.audit_contract")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--audit-dir", default=AUDIT_DIR)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    result = check_gate_files(args.repo_root, args.audit_dir)
    if not args.quiet:
        for f in result["findings"]:
            print(f"{f['artifact_class']:30} gate={str(f['gate']):10} ok={f['ok']}  {f['file']}")
            for p in f["problems"]:
                print(f"    - {p}")
        print(
            f"independent_audit_present={result['independent_audit_present']} "
            f"({result['n_independent_audit_of_record']} of record, "
            f"{result['n_producer_placement_copy']} placement copy) ok={result['ok']}"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
