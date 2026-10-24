#!/usr/bin/env python3
"""Deterministic fixture extraction for team frontier-counter-evidence-content-filter.

Builds INPUT FIXTURES ONLY. No filter package, CLI or acceptance harness is
imported, referenced or executed. No filter verdict is computed. Python 3.12
stdlib only. Re-running with the same inputs produces byte-identical outputs.

Usage:
  python3 -B frontier/frontier-counter-evidence-content-filter/extract_fixtures.py \
      --h2 <path> \
      --product-mount /tmp/lex_accepted/core/product \
      --out-dir results/frontier/frontier-counter-evidence-content-filter/fixtures
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any

EVAL_ROOT = "/tmp/lex_accepted/core/evaluation"
DEFAULT_H2 = os.path.join(
    EVAL_ROOT, "results/evaluation/v65_head_advance_crosscheck/40044626742.json"
)
DEFAULT_PRODUCT_MOUNT = "/tmp/lex_accepted/core/product"
DEFAULT_OUT_DIR = "results/frontier/frontier-counter-evidence-content-filter/fixtures"

H2_EXPECTED_SHA256 = (
    "59f6b1fc5b0658ea40e0cdb03d84f7d3ff641ec6a56ec91ba151f064c162249a"
)
EXPECTED_H2_ROWS = 14
EXPECTED_HISTOGRAM = {
    "D2_letterhead_zone": 10,
    "D3_markup_residue": 4,
    "D4_language_marker_mismatch": 4,
}
EXPECTED_CONFIRMED_OCCURRENCES = 7
EXPECTED_CONFIRMED_UNIQUE = 6
EXPECTED_FLAGSHIP_BUNDLES = 15

SPAN_REL = "results/product/counter_span/CYCLE_39986094168_span_selection.json"
PACKET_QUESTIONS_REL = "results/product/gate_packet/39319405429/questions"
PLANT_BUNDLE_REL = "results/product/offline_slice/20261023T212530Z/rent-default.bundle.json"
EXCLUDED_PLANT_DECISION_ID = "gr_gerichte_ERZ 2010 25"
VARIANT_ORDER = ("baseline", "candidate", "candidate_unguarded")

BUNDLE_VERSION = "frontier-counter-evidence-content-filter/fixture/1"
NO_FILTER_INVOLVED = (
    "fixtures are assembled only from accepted committed evidence; no filter, "
    "CLI or acceptance harness was invoked by this extraction"
)

FILE_H2 = "h2_defective_14.bundle.json"
FILE_CONFIRMED = "confirmed_set_6.bundle.json"
FILE_PLANTS = "planted_controls.bundle.json"
FILE_PROVENANCE = "FIXTURE_PROVENANCE.json"

SCRIPT_PATH = os.path.abspath(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_PATH)))

COURT_HEADER_ALTERNATION = (
    r"Kantonsgericht|Dretgira\s+chantunala|Tribunale\s+cantonale|Bundesgericht|"
    r"Tribunal\s+f[ée]d[ée]ral|Tribunale\s+federale|Obergericht|Bezirksgericht|"
    r"cour\s+d'appel|tribunal\s+cantonal"
)

RULE_PLANT_LETTERHEAD_A = (
    'source row = first row in document order of that bundle with decision_id != '
    '"gr_gerichte_ERZ 2010 25" AND re.match(court_header_alternation, '
    'full_text.lstrip()) is not None AND len(full_text) >= 400. '
    'decision_id = "PLANT_LETTERHEAD_A"; counter_evidence = source full_text[0:120]; '
    "full_text = source full_text; language = source language; "
    "snippet/regeste/full_text_status copied; fixture_rule recorded. "
    "abort if no such row."
)

RULE_PLANT_SUBSTANTIVE_B = (
    'source row = the row with decision_id == "gr_gerichte_ERZ 2010 25" in that '
    "bundle (abort if absent). text = source full_text; find the paragraph window "
    'deterministically: pos = text.find("\\n\\n", 2000); if pos >= 0: start = pos + 2 '
    'else: nl = text.find("\\n", 2000); start = (nl + 1) if nl >= 0 else 2000; '
    'end_pos = text.find("\\n\\n", start + 300); if end_pos >= 0: end = end_pos + 2 '
    'else: nl2 = text.find("\\n", start + 300); '
    "end = (nl2 + 1) if nl2 >= 0 else min(len(text), start + 300); "
    "span = text[start:end]; abort if len(span) < 200; "
    'decision_id = "PLANT_SUBSTANTIVE_B"; counter_evidence = span; '
    "full_text = source full_text; language = source language; record fixture_rule "
    "with start/end/len/offset (offset=start) as plain integers."
)


def fail(message: str) -> None:
    print("ERROR: " + message, file=sys.stderr)
    raise SystemExit(1)


def check(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, payload: Any) -> tuple[str, int]:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    data = text.encode("utf-8")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(data).hexdigest(), len(data)


def repo_relative(path: str) -> str:
    return os.path.relpath(os.path.abspath(path), REPO_ROOT).replace(os.sep, "/")


def label_for(
    decision_id: str, label: str, expect_filter: str, expected_defects: list, note: str
) -> dict:
    return {
        "decision_id": decision_id,
        "label": label,
        "expect_filter": expect_filter,
        "expected_defects": list(expected_defects),
        "note": note,
    }


def assert_labels_aligned(decisions: list, labels: list, fixture_name: str) -> None:
    check(
        len(decisions) == len(labels),
        f"{fixture_name}: expected_labels length {len(labels)} != decisions length "
        f"{len(decisions)}",
    )
    for index, (decision, label) in enumerate(zip(decisions, labels)):
        check(
            decision["decision_id"] == label["decision_id"],
            f"{fixture_name}: expected_labels[{index}] decision_id "
            f"{label['decision_id']!r} != decisions[{index}] decision_id "
            f"{decision['decision_id']!r}",
        )


def bundle_sha(pins: dict, relpath: str, product_mount: str) -> tuple[str, str]:
    key = "mount:" + relpath
    check(key in pins, f"pins_after has no entry for {key}")
    expected = pins[key]
    check(
        isinstance(expected, str) and len(expected) == 64,
        f"pins_after[{key!r}] is not a sha256 string: {expected!r}",
    )
    absolute = os.path.join(product_mount, relpath)
    check(os.path.isfile(absolute), f"missing evidence file: {absolute}")
    actual = sha256_file(absolute)
    check(
        actual == expected,
        f"sha256 mismatch for {absolute}: expected {expected}, got {actual}",
    )
    return absolute, expected


def find_bundle_row(bundle: dict, decision_id: str, where: str) -> dict:
    matches = [
        row for row in bundle.get("decisions", []) if row.get("decision_id") == decision_id
    ]
    check(
        len(matches) >= 1,
        f"{where}: decision_id {decision_id!r} not found in bundle decisions",
    )
    return matches[0]


# --------------------------------------------------------------------------- #
# (A) h2_defective_14.bundle.json
# --------------------------------------------------------------------------- #
def build_h2_fixture(
    h2_path: str, h2_sha: str, artifact: dict, product_mount: str
) -> tuple[dict, dict]:
    probe = artifact["shipped_slice_counter_evidence_probe"]
    pins = artifact["pins_after"]

    flagship_rels: list[str] = [entry["bundle"] for entry in probe["bundles"]]
    control = probe["prior_cycle_control"]
    flagship_rels.append(control["bundle"])
    check(
        len(flagship_rels) == EXPECTED_FLAGSHIP_BUNDLES,
        f"expected {EXPECTED_FLAGSHIP_BUNDLES} flagship bundle files, got "
        f"{len(flagship_rels)}",
    )
    check(
        len(set(flagship_rels)) == EXPECTED_FLAGSHIP_BUNDLES,
        "flagship bundle list contains duplicates",
    )

    resolved: dict[str, tuple[str, str]] = {}
    source_inputs = [{"path": h2_path, "sha256": h2_sha}]
    for relpath in flagship_rels:
        absolute, digest = bundle_sha(pins, relpath, product_mount)
        resolved[relpath] = (absolute, digest)
        source_inputs.append({"path": absolute, "sha256": digest})

    pairs: list[tuple[str, dict]] = []
    for entry in probe["bundles"]:
        for row in entry["verified_rows"]:
            pairs.append((entry["bundle"], row))
    check(
        len(control["verified_rows"]) >= 1,
        "prior_cycle_control.verified_rows is empty",
    )
    pairs.append((control["bundle"], control["verified_rows"][0]))

    check(
        len(pairs) == EXPECTED_H2_ROWS,
        f"expected {EXPECTED_H2_ROWS} H2 rows, got {len(pairs)}",
    )

    recomputed: dict[str, int] = {}
    for _, row in pairs:
        for defect in row["defects"]:
            recomputed[defect] = recomputed.get(defect, 0) + 1
    published = probe["defect_histogram"]
    check(
        recomputed == EXPECTED_HISTOGRAM,
        f"recomputed histogram {recomputed} != published numbers "
        f"{EXPECTED_HISTOGRAM}",
    )
    check(
        recomputed == published,
        f"recomputed histogram {recomputed} != artifact defect_histogram {published}",
    )

    bundle_cache: dict[str, dict] = {}
    decisions: list[dict] = []
    labels: list[dict] = []

    for relpath, row in pairs:
        if relpath not in bundle_cache:
            bundle_cache[relpath] = load_json(resolved[relpath][0])
        bundle = bundle_cache[relpath]
        where = f"{relpath} :: {row['decision_id']}"
        bundle_row = find_bundle_row(bundle, row["decision_id"], where)

        head = row["evidence_head"]
        check(len(head) <= 160, f"{where}: evidence_head length {len(head)} > 160")
        check(
            len(head) == row["detail"]["evidence_len"],
            f"{where}: len(evidence_head)={len(head)} != detail.evidence_len="
            f"{row['detail']['evidence_len']}",
        )
        check(
            bundle_row.get("counter_evidence") == head,
            f"{where}: bundle counter_evidence != artifact evidence_head "
            "(identity check failed)",
        )

        full_text = bundle_row.get("full_text") or ""
        if row["detail"]["grounded_in"] == "full_text":
            offset = full_text.find(head)
            check(
                offset == row["detail"]["first_offset"],
                f"{where}: full_text.find(counter_evidence)={offset} != "
                f"detail.first_offset={row['detail']['first_offset']}",
            )

        decisions.append(
            {
                "decision_id": row["decision_id"],
                "language": row["language"],
                "counter_status": row["counter_status"],
                "counter_uncertainty": row["counter_uncertainty"],
                "counter_evidence": head,
                "counter_evidence_verified": True,
                "full_text": full_text,
                "snippet": bundle_row.get("snippet"),
                "regeste": bundle_row.get("regeste"),
                "full_text_status": bundle_row.get("full_text_status"),
                "h2_detail": row["detail"],
                "h2_defects": row["defects"],
                "h2_class": row["class"],
                "source_bundle": relpath,
                "source_bundle_sha256": pins["mount:" + relpath],
            }
        )
        labels.append(
            label_for(
                row["decision_id"],
                "H2_DEFECT",
                "reject",
                row["defects"],
                row["class"],
            )
        )

    check(
        len(decisions) == EXPECTED_H2_ROWS,
        f"h2 fixture: expected {EXPECTED_H2_ROWS} decisions, got {len(decisions)}",
    )
    assert_labels_aligned(decisions, labels, FILE_H2)

    fixture = {
        "bundle_version": BUNDLE_VERSION,
        "fixture_kind": "h2_defective_14",
        "provenance": {
            "no_filter_involved": NO_FILTER_INVOLVED,
            "source_inputs": source_inputs,
            "rows_source": (
                "14 verified defective rows read verbatim from the H2 artifact: "
                "shipped_slice_counter_evidence_probe.bundles[*].verified_rows in "
                "artifact order, then shipped_slice_counter_evidence_probe."
                "prior_cycle_control.verified_rows[0]"
            ),
            "published_histogram": published,
            "recomputed_histogram": recomputed,
            "published_histogram_asserted_equal": True,
            "n_rows_asserted": EXPECTED_H2_ROWS,
        },
        "expected_labels": labels,
        "decisions": decisions,
    }
    histogram_provenance = {
        "published_histogram": published,
        "recomputed_histogram": recomputed,
        "published_histogram_asserted_equal": True,
    }
    return fixture, {
        "source_inputs": source_inputs,
        "histogram": histogram_provenance,
    }


# --------------------------------------------------------------------------- #
# (B) confirmed_set_6.bundle.json
# --------------------------------------------------------------------------- #
def build_confirmed_fixture(product_mount: str) -> tuple[dict, dict]:
    span_path = os.path.join(product_mount, SPAN_REL)
    check(os.path.isfile(span_path), f"missing span measurement: {span_path}")
    span_sha = sha256_file(span_path)
    span = load_json(span_path)
    check(
        isinstance(span.get("bundles"), dict) and span["bundles"],
        f"{SPAN_REL}: missing .bundles",
    )

    packet_cache: dict[str, tuple[str, str, dict]] = {}
    for qid in span["bundles"]:
        relpath = f"{PACKET_QUESTIONS_REL}/{qid}.bundle.json"
        absolute = os.path.join(product_mount, relpath)
        check(os.path.isfile(absolute), f"missing packet bundle: {absolute}")
        digest = sha256_file(absolute)
        expected = span["bundles"][qid].get("bundle_sha256")
        check(
            expected is not None,
            f"{SPAN_REL}: .bundles[{qid!r}].bundle_sha256 missing",
        )
        check(
            digest == expected,
            f"sha256 mismatch for {absolute}: expected {expected}, got {digest}",
        )
        packet_cache[qid] = (absolute, digest, load_json(absolute))

    occurrences: list[dict] = []
    for qid, bundle_entry in span["bundles"].items():
        packet_absolute, packet_sha, packet_bundle = packet_cache[qid]
        for variant in VARIANT_ORDER:
            check(
                variant in bundle_entry,
                f"{SPAN_REL}: .bundles[{qid!r}] missing variant {variant!r}",
            )
            for record in bundle_entry[variant].get("emitted", []):
                if record.get("counter_evidence_verified") is not True:
                    continue
                occurrences.append(
                    {
                        "decision_id": record["decision_id"],
                        "counter_evidence": record["counter_evidence"],
                        "counter_status": record["counter_status"],
                        "qid": qid,
                        "variant": variant,
                        "packet_absolute": packet_absolute,
                        "packet_sha": packet_sha,
                        "packet_bundle": packet_bundle,
                    }
                )

    check(
        len(occurrences) == EXPECTED_CONFIRMED_OCCURRENCES,
        f"expected {EXPECTED_CONFIRMED_OCCURRENCES} verified emitted occurrences, "
        f"got {len(occurrences)}",
    )

    first_seen: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for occurrence in occurrences:
        key = (occurrence["decision_id"], occurrence["counter_evidence"])
        if key not in first_seen:
            first_seen[key] = occurrence
            order.append(key)
            continue
        prior = first_seen[key]
        check(
            prior["counter_status"] == occurrence["counter_status"],
            f"inconsistent counter_status for {key[0]!r}: "
            f"{prior['counter_status']!r} vs {occurrence['counter_status']!r}",
        )
        check(
            prior["qid"] == occurrence["qid"],
            f"inconsistent qid for unique pair {key[0]!r}: "
            f"{prior['qid']!r} vs {occurrence['qid']!r}",
        )
    check(
        len(order) == EXPECTED_CONFIRMED_UNIQUE,
        f"expected {EXPECTED_CONFIRMED_UNIQUE} unique (decision_id, "
        f"counter_evidence) pairs, got {len(order)}",
    )

    decisions: list[dict] = []
    labels: list[dict] = []
    note = "emitted and counter_evidence_verified=true in CYCLE_39986094168"

    for key in order:
        decision_id, counter_evidence = key
        members = [
            occurrence
            for occurrence in occurrences
            if (occurrence["decision_id"], occurrence["counter_evidence"]) == key
        ]
        first = members[0]
        qid = first["qid"]
        packet_absolute, packet_sha, packet_bundle = packet_cache[qid]
        packet_row = find_bundle_row(
            packet_bundle, decision_id, f"{PACKET_QUESTIONS_REL}/{qid}.bundle.json"
        )

        variants = sorted((m["qid"], m["variant"]) for m in members)
        decisions.append(
            {
                "decision_id": decision_id,
                "counter_evidence": counter_evidence,
                "counter_evidence_verified": True,
                "counter_status": first["counter_status"],
                "language": packet_row["language"],
                "full_text": packet_row.get("full_text") or "",
                "snippet": packet_row.get("snippet"),
                "regeste": packet_row.get("regeste"),
                "full_text_status": packet_row.get("full_text_status"),
                "qid": qid,
                "variants": [list(pair) for pair in variants],
                "source_row_count": len(members),
                "packet_bundle_path": packet_absolute,
                "packet_bundle_sha256": packet_sha,
                "span_measurement_path": span_path,
                "span_measurement_sha256": span_sha,
            }
        )
        labels.append(
            label_for(decision_id, "FROZEN_GATE_CONFIRMED", "accept", [], note)
        )

    check(
        len(decisions) == EXPECTED_CONFIRMED_UNIQUE,
        f"{FILE_CONFIRMED}: expected {EXPECTED_CONFIRMED_UNIQUE} decisions, got "
        f"{len(decisions)}",
    )
    assert_labels_aligned(decisions, labels, FILE_CONFIRMED)

    source_inputs = [{"path": span_path, "sha256": span_sha}]
    for qid in span["bundles"]:
        absolute, digest, _ = packet_cache[qid]
        source_inputs.append({"path": absolute, "sha256": digest})

    fixture = {
        "bundle_version": BUNDLE_VERSION,
        "fixture_kind": "confirmed_set_6",
        "provenance": {
            "no_filter_involved": NO_FILTER_INVOLVED,
            "source_inputs": source_inputs,
            "emitted_occurrences": EXPECTED_CONFIRMED_OCCURRENCES,
            "unique_decision_counter_evidence_pairs": EXPECTED_CONFIRMED_UNIQUE,
            "occurrence_vs_unique": (
                f"{EXPECTED_CONFIRMED_OCCURRENCES} emitted occurrences / "
                f"{EXPECTED_CONFIRMED_UNIQUE} unique"
            ),
            "language_source": (
                "language comes from the packet bundle row for the same decision_id"
            ),
            "variants_traversed": list(VARIANT_ORDER),
            "text_analysis": (
                "no offsets or text analysis computed for these rows"
            ),
        },
        "expected_labels": labels,
        "decisions": decisions,
    }
    return fixture, {"source_inputs": source_inputs}


# --------------------------------------------------------------------------- #
# (C) planted_controls.bundle.json
# --------------------------------------------------------------------------- #
def build_plant_fixture(
    pins: dict, product_mount: str
) -> tuple[dict, dict, dict[str, Any]]:
    absolute, digest = bundle_sha(pins, PLANT_BUNDLE_REL, product_mount)
    plant_bundle = load_json(absolute)

    extraction_rule_plants = {
        "plant_source_bundle": PLANT_BUNDLE_REL,
        "plant_source_bundle_sha256": digest,
        "court_header_alternation": COURT_HEADER_ALTERNATION,
        "court_header_alternation_flags": "python re, IGNORECASE",
        "PLANT_LETTERHEAD_A": RULE_PLANT_LETTERHEAD_A,
        "PLANT_SUBSTANTIVE_B": RULE_PLANT_SUBSTANTIVE_B,
    }

    letterhead_source = None
    for row in plant_bundle.get("decisions", []):
        full_text = row.get("full_text") or ""
        if row.get("decision_id") == EXCLUDED_PLANT_DECISION_ID:
            continue
        if re.match(COURT_HEADER_ALTERNATION, full_text.lstrip(), re.IGNORECASE) is None:
            continue
        if len(full_text) < 400:
            continue
        letterhead_source = row
        break
    check(
        letterhead_source is not None,
        f"{PLANT_BUNDLE_REL}: no source row satisfies the PLANT_LETTERHEAD_A rule",
    )
    letterhead_text = letterhead_source.get("full_text") or ""
    check(
        len(letterhead_text) >= 400,
        "PLANT_LETTERHEAD_A: selected source full_text shorter than 400",
    )

    substantive_rows = [
        row
        for row in plant_bundle.get("decisions", [])
        if row.get("decision_id") == EXCLUDED_PLANT_DECISION_ID
    ]
    check(
        len(substantive_rows) >= 1,
        f"{PLANT_BUNDLE_REL}: decision_id {EXCLUDED_PLANT_DECISION_ID!r} absent "
        "(PLANT_SUBSTANTIVE_B source row)",
    )
    substantive_source = substantive_rows[0]
    text = substantive_source.get("full_text") or ""
    check(bool(text), "PLANT_SUBSTANTIVE_B: source full_text missing or empty")

    pos = text.find("\n\n", 2000)
    if pos >= 0:
        start = pos + 2
    else:
        newline = text.find("\n", 2000)
        start = (newline + 1) if newline >= 0 else 2000
    end_pos = text.find("\n\n", start + 300)
    if end_pos >= 0:
        end = end_pos + 2
    else:
        newline_two = text.find("\n", start + 300)
        if newline_two >= 0:
            end = newline_two + 1
        else:
            end = min(len(text), start + 300)
    span_text = text[start:end]
    check(
        len(span_text) >= 200,
        f"PLANT_SUBSTANTIVE_B: paragraph window length {len(span_text)} < 200",
    )

    window = {"start": start, "end": end, "len": len(span_text), "offset": start}
    rule_b_with_window = (
        RULE_PLANT_SUBSTANTIVE_B
        + " window="
        + json.dumps(window, sort_keys=True)
    )

    decisions = [
        {
            "decision_id": "PLANT_LETTERHEAD_A",
            "counter_evidence": letterhead_text[0:120],
            "full_text": letterhead_text,
            "language": letterhead_source.get("language"),
            "snippet": letterhead_source.get("snippet"),
            "regeste": letterhead_source.get("regeste"),
            "full_text_status": letterhead_source.get("full_text_status"),
            "fixture_rule": RULE_PLANT_LETTERHEAD_A,
        },
        {
            "decision_id": "PLANT_SUBSTANTIVE_B",
            "counter_evidence": span_text,
            "full_text": text,
            "language": substantive_source.get("language"),
            "snippet": substantive_source.get("snippet"),
            "regeste": substantive_source.get("regeste"),
            "full_text_status": substantive_source.get("full_text_status"),
            "fixture_rule": rule_b_with_window,
        },
    ]
    labels = [
        label_for(
            "PLANT_LETTERHEAD_A",
            "PLANT_LETTERHEAD",
            "reject",
            ["D2_letterhead_zone"],
            RULE_PLANT_LETTERHEAD_A,
        ),
        label_for(
            "PLANT_SUBSTANTIVE_B",
            "PLANT_SUBSTANTIVE",
            "accept",
            [],
            rule_b_with_window,
        ),
    ]
    assert_labels_aligned(decisions, labels, FILE_PLANTS)

    fixture = {
        "bundle_version": BUNDLE_VERSION,
        "fixture_kind": "planted_controls",
        "provenance": {
            "no_filter_involved": NO_FILTER_INVOLVED,
            "source_inputs": [{"path": absolute, "sha256": digest}],
            "extraction_rule_plants": extraction_rule_plants,
            "plant_source_decision_ids": {
                "PLANT_LETTERHEAD_A": letterhead_source.get("decision_id"),
                "PLANT_SUBSTANTIVE_B": substantive_source.get("decision_id"),
            },
            "plant_substantive_window": window,
        },
        "expected_labels": labels,
        "decisions": decisions,
    }
    extra = {
        "source_inputs": [{"path": absolute, "sha256": digest}],
        "extraction_rule_plants": extraction_rule_plants,
        "window": window,
        "source_decision_ids": {
            "PLANT_LETTERHEAD_A": letterhead_source.get("decision_id"),
            "PLANT_SUBSTANTIVE_B": substantive_source.get("decision_id"),
        },
    }
    return fixture, extra, window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract deterministic input fixtures for the "
            "frontier-counter-evidence-content-filter team. Input fixtures only: "
            "no filter, CLI or acceptance harness is invoked."
        )
    )
    parser.add_argument("--h2", default=DEFAULT_H2, help="H2 artifact path")
    parser.add_argument(
        "--product-mount",
        default=DEFAULT_PRODUCT_MOUNT,
        help="read-only product evidence mount",
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help="output directory for fixture files",
    )
    args = parser.parse_args(argv)

    h2_path = args.h2
    product_mount = args.product_mount
    out_dir = args.out_dir

    check(os.path.isfile(h2_path), f"H2 artifact not found: {h2_path}")
    h2_sha = sha256_file(h2_path)
    check(
        h2_sha == H2_EXPECTED_SHA256,
        f"H2 artifact sha256 mismatch for {h2_path}: expected "
        f"{H2_EXPECTED_SHA256}, got {h2_sha}",
    )
    artifact = load_json(h2_path)
    check(
        isinstance(artifact.get("shipped_slice_counter_evidence_probe"), dict),
        "H2 artifact missing .shipped_slice_counter_evidence_probe",
    )
    check(isinstance(artifact.get("pins_after"), dict), "H2 artifact missing .pins_after")

    h2_fixture, h2_extra = build_h2_fixture(
        h2_path, h2_sha, artifact, product_mount
    )
    confirmed_fixture, confirmed_extra = build_confirmed_fixture(product_mount)
    plant_fixture, plant_extra, _window = build_plant_fixture(
        artifact["pins_after"], product_mount
    )

    os.makedirs(out_dir, exist_ok=True)
    outputs: dict[str, dict] = {}
    written: dict[str, tuple[str, int]] = {}

    for filename, payload in (
        (FILE_H2, h2_fixture),
        (FILE_CONFIRMED, confirmed_fixture),
        (FILE_PLANTS, plant_fixture),
    ):
        path = os.path.join(out_dir, filename)
        digest, size = write_json(path, payload)
        written[filename] = (digest, size)
        outputs[filename] = {
            "sha256": digest,
            "byte_size": size,
            "n_decisions": len(payload["decisions"]),
        }

    provenance_doc = {
        "generator": repo_relative(SCRIPT_PATH),
        "bundle_version": BUNDLE_VERSION,
        "no_filter_involved": NO_FILTER_INVOLVED,
        "fixtures": [
            {
                "path": f"{repo_relative(out_dir)}/{FILE_H2}",
                "sha256": written[FILE_H2][0],
                "byte_size": written[FILE_H2][1],
                "n_decisions": len(h2_fixture["decisions"]),
                "source_inputs": h2_extra["source_inputs"],
            },
            {
                "path": f"{repo_relative(out_dir)}/{FILE_CONFIRMED}",
                "sha256": written[FILE_CONFIRMED][0],
                "byte_size": written[FILE_CONFIRMED][1],
                "n_decisions": len(confirmed_fixture["decisions"]),
                "source_inputs": confirmed_extra["source_inputs"],
            },
            {
                "path": f"{repo_relative(out_dir)}/{FILE_PLANTS}",
                "sha256": written[FILE_PLANTS][0],
                "byte_size": written[FILE_PLANTS][1],
                "n_decisions": len(plant_fixture["decisions"]),
                "source_inputs": plant_extra["source_inputs"],
            },
        ],
        "extraction_rule_plants": plant_extra["extraction_rule_plants"],
        "published_histogram": h2_extra["histogram"]["published_histogram"],
        "recomputed_histogram": h2_extra["histogram"]["recomputed_histogram"],
        "published_histogram_asserted_equal": h2_extra["histogram"][
            "published_histogram_asserted_equal"
        ],
    }
    provenance_path = os.path.join(out_dir, FILE_PROVENANCE)
    digest, size = write_json(provenance_path, provenance_doc)
    written[FILE_PROVENANCE] = (digest, size)
    outputs[FILE_PROVENANCE] = {"sha256": digest, "byte_size": size}

    summary = {
        "counts": {
            "h2_defective_14": len(h2_fixture["decisions"]),
            "confirmed_occurrences": EXPECTED_CONFIRMED_OCCURRENCES,
            "confirmed_set_6": len(confirmed_fixture["decisions"]),
            "planted_controls": len(plant_fixture["decisions"]),
            "flagship_bundles_verified": EXPECTED_FLAGSHIP_BUNDLES,
        },
        "outputs": outputs,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
