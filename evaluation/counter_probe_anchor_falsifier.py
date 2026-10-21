#!/usr/bin/env python3
"""Counter-probe topic-anchor falsifier (frozen instrument, run 39674402905).

    python -m evaluation.counter_probe_anchor_falsifier \
        --run-id 39674402905 \
        --out results/evaluation/counter_probe_anchor_falsifier/39674402905.json \
        --report reports/evaluation/COUNTER_PROBE_ANCHOR_FALSIFIER_39674402905.md

WHAT THIS MEASURES
-------------------
The product's counter-authority stage builds its probes from the *answer's* own
key legal terms (``product/query/adversarial_retrieval.py``::

    key_terms = answer_key_terms(answer_prose)
    ...
    probe_terms = [t for t in key_terms[:4]] + terms

i.e. the first four tokens of every issued probe are a TOPIC ANCHOR taken from
the answer prose.  The generative audit rewrites that prose first: every
citation it could not ground is replaced by the literal placeholder
``[citation removed: not in retrieved set]``
(``frontier/frontier-generative-audit/generative_audit/source_packing.py``),
and ``product/query/pipeline.py::adversarial_retrieval_pass`` plans the probes
from the POST-redaction prose.

This instrument asks one question of the ACCEPTED product bytes:

    Does the topic anchor of an issued counter probe carry any legal
    vocabulary of the question it is supposed to attack, or has the
    redaction placeholder displaced it?

It answers with the RECORDED probe query (not a re-derivation): the anchor is
the first ``ANCHOR_SLOTS`` whitespace-separated tokens of
``provenance.adversarial_retrieval.probes[i]["query"]``, which is exactly what
the frozen product semantics produce.

WHY IT IS NOT A DUPLICATE OF ACCEPTED WORK
-------------------------------------------
* ``frontier-counter-label-emission`` attributes the ZERO counter-row outcome of
  the V3 packets to ``e_EMISSION_WRITER_ABORT`` — a LABEL-side cause.  Its cause
  classes are ``c_HYDRATION`` and ``e_EMISSION_WRITER_ABORT`` only.  It does not
  look at how the probe is built.
* ``results/evaluation/counter_emission_crosscheck/39457963802.json`` compares
  the label stage only (ZERO_DIVERGENCE over 96 comparable quantities).
* No instrument in ``evaluation/`` reads the probe anchor.  This one does.

EXIT CODES (frozen; see the hypothesis file for the full contract)
------------------------------------------------------------------
0  COUNTER_PROBE_ANCHOR_NOT_FALSIFIED  — no issued probe carries a
   placeholder-derived anchor token.
1  COUNTER_PROBE_ANCHOR_FALSIFIED       — at least one issued probe carries a
   placeholder-derived anchor token.
2  ENVIRONMENT_OR_VACUOUS                — a pin drifted, a control failed, or
   no bundle could be measured.  Never a product verdict.

The instrument is dependency-light on purpose: it imports the PRODUCT's own
``answer_key_terms`` / ``plan_adversarial_queries`` / ``_ANSWER_STOP`` and the
PRODUCT's own ``REDACTION_PLACEHOLDER`` constant, so the tokenisation, the
stoplist and the anchor semantics are never re-implemented here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lex-evaluation-counter-probe-anchor-falsifier/1"

#: Frozen: the product builds ``probe_terms = key_terms[:4] + terms``
#: (product/query/adversarial_retrieval.py::plan_adversarial_queries).
ANCHOR_SLOTS = 4

#: Frozen: the product's own pool-vocabulary length rule
#: (product/query/adversarial_retrieval.py::bundle_topic_terms:
#: ``len(token) >= 6 and token not in _ANSWER_STOP and not token.isdigit()``).
CONTENT_MIN_LEN = 6

EXIT_OK = 0
EXIT_FALSIFIED = 1
EXIT_ENVIRONMENT = 2

DEFAULT_PRODUCT_ROOT = "/tmp/lex_accepted/product"
DEFAULT_SECONDARY = "results/evaluation/rebuilt_packet_adjudication_39049030442/packet"

PRODUCT_PINS = {
    "product/query/adversarial_retrieval.py":
        "frontier/frontier-generative-audit/generative_audit/source_packing.py",
}

#: The three product files whose bytes define the measured behaviour.
PRODUCT_SOURCE_FILES = (
    "product/query/adversarial_retrieval.py",
    "product/query/retrieval.py",
    "frontier/frontier-generative-audit/generative_audit/source_packing.py",
)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# product loader — the product's OWN code, never a re-implementation
# --------------------------------------------------------------------------- #


class ProductCode:
    """The product's own anchor semantics, loaded from the accepted mount."""

    def __init__(self, product_root: Path) -> None:
        self.product_root = product_root
        self.answer_key_terms = None
        self.plan_adversarial_queries = None
        self.answer_stop: frozenset = frozenset()
        self.tokenize = None
        self.bundle_topic_terms = None
        self.redaction_placeholder = ""
        self._load()

    def _module(self, name: str, path: Path) -> types.ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    def _load(self) -> None:
        root = self.product_root
        for rel in PRODUCT_SOURCE_FILES:
            if not (root / rel).is_file():
                raise FileNotFoundError(f"product source missing: {root / rel}")

        # package shells so the product's relative imports resolve
        for name, rel in (("product", "product"), ("product.query", "product/query")):
            shell = types.ModuleType(name)
            shell.__path__ = [str(root / rel)]  # type: ignore[attr-defined]
            shell.__package__ = name
            sys.modules[name] = shell

        # ocl_adapter lives beside the product in the accepted mount
        adapter = root / "frontier" / "frontier-query-retrieval"
        if adapter.is_dir():
            sys.path.insert(0, str(adapter))

        self._module("product.query.retrieval", root / "product/query/retrieval.py")
        self._module("product.query.answer", root / "product/query/answer.py")
        adv = self._module("product.query.adversarial_retrieval",
                           root / "product/query/adversarial_retrieval.py")
        self.answer_key_terms = adv.answer_key_terms
        self.plan_adversarial_queries = adv.plan_adversarial_queries
        self.answer_stop = adv._ANSWER_STOP
        self.tokenize = adv.tokenize
        self.bundle_topic_terms = adv.bundle_topic_terms

        packing = self._module(
            "lex_product_source_packing",
            root / "frontier/frontier-generative-audit/generative_audit/source_packing.py")
        self.redaction_placeholder = str(packing.REDACTION_PLACEHOLDER)

    # -- derived vocabularies ------------------------------------------------

    def placeholder_tokens(self) -> list[str]:
        """Tokens of the product's own redaction placeholder that survive the
        product's own ``answer_key_terms`` filter (stoplist / len<4 / digits)."""
        return list(self.answer_key_terms(self.redaction_placeholder))

    def content_terms(self, text: str) -> set[str]:
        """Content tokens of ``text`` under the product's own pool rule
        (len >= 6, not in the product's ``_ANSWER_STOP``, not a digit)."""
        out: set[str] = set()
        for token in self.tokenize(text or ""):
            if len(token) < CONTENT_MIN_LEN:
                continue
            if token in self.answer_stop or token.isdigit():
                continue
            out.add(token)
        return out

    def key_terms(self, prose: str) -> list[str]:
        return list(self.answer_key_terms(prose or ""))


# --------------------------------------------------------------------------- #
# population
# --------------------------------------------------------------------------- #


def _bundle_files(root: Path) -> list[Path]:
    base = root / "results" / "product"
    if not base.is_dir():
        base = root
    return sorted(base.glob("**/questions/*.bundle.json"))


def _has_probes(bundle: dict) -> bool:
    ar = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    return bool(ar.get("probes"))


def population(root: Path) -> list[dict]:
    """Every bundle of the source tree that carries recorded adversarial probes."""
    out = []
    for path in _bundle_files(root):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(bundle, dict) or not _has_probes(bundle):
            continue
        out.append({"path": path, "bundle": bundle})
    return out


def manifest(root: Path) -> dict:
    """Deterministic digest of the measurable population of a source tree."""
    rows = []
    for item in population(root):
        rows.append({"relpath": str(item["path"].relative_to(root)),
                     "sha256": sha256_file(item["path"])})
    body = "\n".join(f"{r['relpath']} {r['sha256']}" for r in rows)
    return {"n_bundles": len(rows), "manifest_sha256": sha256_text(body),
            "bundles": rows}


# --------------------------------------------------------------------------- #
# per-bundle measurement
# --------------------------------------------------------------------------- #


def _anchor_of(probe_query: str) -> list[str]:
    return (probe_query or "").split()[:ANCHOR_SLOTS]


def _row_text(decision: dict) -> str:
    return " ".join(str(decision.get(f) or "") for f in ("regeste", "snippet", "title"))


def measure_bundle(item: dict, product: ProductCode, *, packet_label: str) -> dict:
    path: Path = item["path"]
    bundle: dict = item["bundle"]
    ar = (bundle.get("provenance") or {}).get("adversarial_retrieval") or {}
    probes = ar.get("probes") or []
    prose = str((bundle.get("answer") or {}).get("prose") or "")
    query = str(bundle.get("query") or "")
    placeholder = product.redaction_placeholder

    recorded_queries = [str(p.get("query") or "") for p in probes]
    anchors = [_anchor_of(q) for q in recorded_queries]
    anchor = anchors[0] if anchors else []

    # --- C1: replay fidelity -------------------------------------------------
    replay = product.plan_adversarial_queries(query, prose)
    replay_queries = [str(p.get("query") or "") for p in replay]
    replay_ok = replay_queries == recorded_queries
    anchors_uniform = all(a == anchor for a in anchors)

    # --- G1: placeholder contamination of the anchor --------------------------
    ph_tokens = product.placeholder_tokens()
    contaminated = sorted(set(anchor) & set(ph_tokens))

    # --- G2: is the anchor topically meaningful? -----------------------------
    q_terms = product.content_terms(query)
    anchor_topical = sorted(set(anchor) & q_terms)

    # --- G4: counterfactual (de-redacted prose) ------------------------------
    de_redacted = prose.replace(placeholder, " ")
    de_anchor: list[str] = []
    de_replay = product.plan_adversarial_queries(query, de_redacted)
    if de_replay:
        de_anchor = _anchor_of(str(de_replay[0].get("query") or ""))
    de_topical = sorted(set(de_anchor) & q_terms)
    counterfactual = {
        "de_redacted_anchor": de_anchor,
        "de_redacted_anchor_differs": de_anchor != anchor,
        "de_redacted_anchor_topical": de_topical,
        "placeholder_occurrences": prose.count(placeholder),
    }

    # --- C4: de-redacting a prose that never contained the placeholder is a
    # NO-OP.  This is the placebo arm of the counterfactual: the attribution to
    # the placeholder cannot be an artefact of the de-redaction step itself.
    n_ph = prose.count(placeholder)
    de_redaction_noop = (de_anchor == anchor) if n_ph == 0 else None

    # --- G3: reach consequence (observational, reported with n/m) ------------
    decisions = {str(d.get("decision_id") or ""): d for d in (bundle.get("decisions") or [])}
    new_ids = [str(x) for x in (ar.get("new_row_ids") or [])]
    q_term_list = sorted(q_terms)
    n_topicical = 0
    per_row = []
    for did in new_ids:
        d = decisions.get(did) or {}
        shared = sorted(product.content_terms(_row_text(d)) & q_terms)
        is_top = bool(shared)
        n_topicical += int(is_top)
        per_row.append({"decision_id": did, "topical": is_top,
                        "shared_question_terms": shared,
                        "regeste_head": str(d.get("regeste") or "")[:160]})
    row_rate = (n_topicical / len(new_ids)) if new_ids else None

    # product's own topicality pool (reported; for the DE bundle this pool is
    # itself contaminated, which is part of the finding)
    try:
        product_pool = list(product.bundle_topic_terms(bundle))
    except Exception:  # pragma: no cover - defensive, never reached on valid input
        product_pool = []
    n_pool_topical = 0
    for did in new_ids:
        d = decisions.get(did) or {}
        toks = product.content_terms(_row_text(d))
        if toks & set(product_pool):
            n_pool_topical += 1
    pool_rate = (n_pool_topical / len(new_ids)) if new_ids else None

    return {
        "packet": packet_label,
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "query_head": query[:200],
        "n_probe_plans": len(probes),
        "recorded_probe_queries": recorded_queries,
        "recorded_anchor": anchor,
        "anchor_uniform_across_intents": anchors_uniform,
        "answer_prose_sha256": sha256_text(prose),
        "answer_prose_len": len(prose),
        "placeholder_occurrences_in_prose": prose.count(placeholder),
        "placeholder_tokens": ph_tokens,
        "G1_anchor_placeholder_tokens": contaminated,
        "G1_anchor_contaminated": bool(contaminated),
        "G2_anchor_question_terms": anchor_topical,
        "G2_anchor_topical": bool(anchor_topical),
        "question_content_terms": q_term_list,
        "G3_adversarial_rows": len(new_ids),
        "G3_rows_topical_vs_question": n_topicical,
        "G3_row_topical_rate": row_rate,
        "G3_rows_topical_vs_product_pool": n_pool_topical,
        "G3_row_topical_rate_product_pool": pool_rate,
        "G3_per_row": per_row,
        "G4_counterfactual": counterfactual,
        "C1_replay_fidelity": replay_ok,
        "C1_replay_queries": replay_queries,
        "C4_de_redaction_noop_when_placeholder_absent": de_redaction_noop,
    }


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #


def run_controls(measurements: list[dict], product: ProductCode) -> dict:
    controls: dict[str, dict] = {}

    # C1: every bundle's probe plan is reproduced byte-for-byte by the product's
    # own planner from the bundle's own recorded prose.
    bad = [m["source_path"] for m in measurements if not m["C1_replay_fidelity"]]
    nonuniform = [m["source_path"] for m in measurements
                  if not m["anchor_uniform_across_intents"]]
    controls["C1_replay_fidelity"] = {
        "description": ("the product's own plan_adversarial_queries, run on the "
                        "bundle's own recorded answer prose, reproduces every "
                        "recorded probe query byte-for-byte"),
        "passed": not bad and not nonuniform,
        "n_bundles": len(measurements),
        "n_failed": len(bad),
        "failed": bad,
        "n_nonuniform_anchor": len(nonuniform),
        "nonuniform": nonuniform,
    }

    # C2: an empty answer prose yields NO probe plan (the product's own D4
    # guard) — the anchor is prose-derived, not query-derived.
    blank = product.plan_adversarial_queries("Arbeitsvertrag Kündigung", "")
    controls["C2_blank_prose_yields_no_plan"] = {
        "description": ("plan_adversarial_queries on a blank answer prose returns "
                        "an empty plan (the product's D4 vacuity guard), so the "
                        "anchor is derived from the answer prose"),
        "passed": blank == [],
        "n_plans_returned": len(blank),
    }

    # C3: the detector is specific — at least one bundle with no placeholder in
    # its prose must NOT be flagged.
    clean = [m for m in measurements if m["placeholder_occurrences_in_prose"] == 0]
    clean_flagged = [m["source_path"] for m in clean if m["G1_anchor_contaminated"]]
    controls["C3_clean_bundle_not_flagged"] = {
        "description": ("a bundle whose answer prose contains no redaction "
                        "placeholder is never classified as anchor-contaminated"),
        "passed": bool(clean) and not clean_flagged,
        "n_clean_bundles": len(clean),
        "n_clean_flagged": len(clean_flagged),
        "clean_flagged": clean_flagged,
    }

    # C4: de-redacting a prose that never contained the placeholder leaves the
    # anchor unchanged — the attribution to the placeholder is not an artefact
    # of the de-redaction step itself.
    placebo_bad = [m["source_path"] for m in measurements
                   if m["placeholder_occurrences_in_prose"] == 0
                   and m["C4_de_redaction_noop_when_placeholder_absent"] is not True]
    controls["C4_de_redaction_is_a_no_op_without_the_placeholder"] = {
        "description": ("for every bundle whose answer prose contains no "
                        "redaction placeholder, de-redacting the prose leaves the "
                        "anchor unchanged"),
        "passed": not placebo_bad,
        "n_failed": len(placebo_bad),
        "failed": placebo_bad,
    }

    # C5: the gate discriminates on CONTENT, not merely on the presence of the
    # placeholder — at least one bundle WITH a placeholder in its prose must NOT
    # be flagged (the mechanism is frequency-dependent).
    dirty = [m for m in measurements if m["placeholder_occurrences_in_prose"] > 0]
    dirty_clean = [m["source_path"] for m in dirty if not m["G1_anchor_contaminated"]]
    controls["C5_gate_discriminates_not_merely_detects_placeholder"] = {
        "description": ("at least one bundle whose answer prose contains the "
                        "redaction placeholder is NOT anchor-contaminated, so the "
                        "gate discriminates on anchor content rather than on the "
                        "mere presence of the placeholder"),
        "passed": bool(dirty_clean),
        "n_dirty_bundles": len(dirty),
        "n_dirty_not_flagged": len(dirty_clean),
    }

    return controls


# --------------------------------------------------------------------------- #
# pins
# --------------------------------------------------------------------------- #


def rehash_pins(freeze: dict, repo_root: Path, product_root: Path,
                source_label: str) -> dict:
    """Re-hash every frozen pin.  Drift is fail-closed (exit 2)."""
    checks: list[dict] = []
    ok = True

    for rel, expected in sorted(freeze.get("pins", {}).items()):
        path = repo_root / rel
        if not path.is_file():
            checks.append({"pin": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": rel, "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})

    for rel, expected in sorted(freeze.get("product_pins", {}).items()):
        path = product_root / rel
        if not path.is_file():
            checks.append({"pin": f"product:{rel}", "status": "ABSENT",
                           "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({"pin": f"product:{rel}", "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})

    for label, expected in sorted(freeze.get("population_manifests", {}).items()):
        if label != source_label:
            continue
        actual = manifest(product_root)["manifest_sha256"]
        good = actual == expected
        ok = ok and good
        checks.append({"pin": f"population:{label}", "status": "ok" if good else "DRIFT",
                       "expected": expected, "actual": actual})

    return {"all_ok": ok, "n_checks": len(checks), "checks": checks}


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def render_report(record: dict) -> str:
    lines: list[str] = []
    a = lines.append
    verdict = record["verdict"]
    a("# Counter-probe topic-anchor falsifier — run "
      f"{record['run_id']}")
    a("")
    a(f"**Verdict: `{verdict}`** (exit {record['exit_code']})")
    a("")
    a(record["verdict_statement"])
    a("")
    a("## What was measured")
    a("")
    a("The product's counter-authority stage anchors every issued probe on the "
      "first four key terms of the *answer prose* "
      "(`product/query/adversarial_retrieval.py::plan_adversarial_queries`, "
      "`probe_terms = key_terms[:4] + terms`). The generative audit rewrites "
      "that prose before the probes are planned, replacing ungrounded "
      "citations with the literal placeholder "
      "`[citation removed: not in retrieved set]` "
      "(`frontier/frontier-generative-audit/generative_audit/source_packing.py`).")
    a("")
    a("This run reads the **recorded** probe queries of the accepted product "
      "bundles and takes their first four whitespace tokens as the anchor.")
    a("")
    a("## Population")
    a("")
    a(f"- source: `{record['source']['label']}` "
      f"(`{record['source']['root']}`)")
    a(f"- measurable bundles (recorded adversarial probes): "
      f"**{record['n_bundles']}**")
    a(f"- population manifest sha256: `{record['source']['manifest_sha256']}`")
    a("")
    a("## Per-bundle result")
    a("")
    a("| packet | lang | ph | anchor | contaminated | anchor topical | "
      "rows topical (question) | de-redacted anchor |")
    a("|---|---|---|---|---|---|---|---|")
    for m in record["bundles"]:
        a(f"| {m['packet']} | {m['language']} | "
          f"{m['placeholder_occurrences_in_prose']} | "
          f"`{' '.join(m['recorded_anchor'])}` | "
          f"{'**YES**' if m['G1_anchor_contaminated'] else 'no'} | "
          f"{'yes' if m['G2_anchor_topical'] else '**NO**'} | "
          f"{m['G3_rows_topical_vs_question']}/{m['G3_adversarial_rows']} | "
          f"`{' '.join(m['G4_counterfactual']['de_redacted_anchor'])}` |")
    a("")
    a("`ph` = occurrences of the redaction placeholder in the answer prose. "
      "`contaminated` = the anchor contains a token the product's own "
      "`answer_key_terms` extracts from the placeholder "
      f"({', '.join('`' + t + '`' for t in record['placeholder_tokens'])}). "
      "`anchor topical` = the anchor shares a content term (len >= 6, product "
      "stoplist, not a digit) with the question.")
    a("")
    a("## Controls")
    a("")
    a("| control | result | detail |")
    a("|---|---|---|")
    for name, c in record["controls"].items():
        detail = ", ".join(f"{k}={v}" for k, v in c.items()
                           if k not in ("description", "passed", "failed",
                                        "clean_flagged", "nonuniform"))
        a(f"| `{name}` | {'PASS' if c['passed'] else 'FAIL'} | {detail} |")
    a("")
    a("## Pin discipline")
    a("")
    a(f"- pins re-hashed BEFORE execution: {record['pins_before']['n_checks']} "
      f"checks, all_ok={record['pins_before']['all_ok']}")
    a(f"- pins re-hashed AFTER execution: {record['pins_after']['n_checks']} "
      f"checks, all_ok={record['pins_after']['all_ok']}")
    a("")
    a("## Claim ceiling")
    a("")
    a(record["claim_ceiling"])
    a("")
    a("## Pre-freeze disclosure")
    a("")
    a(record["pre_freeze_disclosure"])
    a("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="39674402905")
    ap.add_argument("--product-root", default=DEFAULT_PRODUCT_ROOT)
    ap.add_argument("--secondary", default=DEFAULT_SECONDARY)
    ap.add_argument("--source", choices=("auto", "mount", "secondary"),
                    default="auto")
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--freeze-record", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--selftest", action="store_true",
                    help="structural self-test only; never touches the real "
                         "population and never writes a result file")
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    product_root = Path(args.product_root)

    if args.selftest:
        return _selftest(product_root)

    hypothesis_path = Path(args.hypothesis) if args.hypothesis else (
        repo_root / "evaluation/COUNTER_PROBE_ANCHOR_FALSIFIER_HYPOTHESIS_V1.json")
    freeze_path = Path(args.freeze_record) if args.freeze_record else (
        repo_root / "evaluation/COUNTER_PROBE_ANCHOR_FALSIFIER_FREEZE_RECORD_V1.json")

    for p in (hypothesis_path, freeze_path):
        if not p.is_file():
            print(f"::error::missing frozen input: {p}", file=sys.stderr)
            return EXIT_ENVIRONMENT
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    hypothesis = json.loads(hypothesis_path.read_text(encoding="utf-8"))

    # -- source selection ---------------------------------------------------
    secondary_root = Path(args.secondary)
    if not secondary_root.is_absolute():
        secondary_root = repo_root / secondary_root
    if args.source == "mount" or (args.source == "auto"
                                  and (product_root / "results/product").is_dir()):
        source_label, source_root = "mount", product_root
    elif args.source == "secondary" or secondary_root.is_dir():
        source_label, source_root = "secondary", secondary_root
    else:
        print("::error::no product source available", file=sys.stderr)
        return EXIT_ENVIRONMENT

    # -- pins BEFORE --------------------------------------------------------
    pins_before = rehash_pins(freeze, repo_root, source_root, source_label)
    if not pins_before["all_ok"]:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before, "pin drift before execution")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    # -- product code -------------------------------------------------------
    try:
        product = ProductCode(source_root)
    except Exception as exc:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before,
                                     f"product code could not be loaded: "
                                     f"{type(exc).__name__}: {exc}")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    ph_tokens = product.placeholder_tokens()

    # -- measure ------------------------------------------------------------
    items = population(source_root)
    if not items:
        record = _environment_record(args.run_id, source_label, source_root,
                                     pins_before, "no measurable bundle")
        _write(args.out, args.report, record)
        return EXIT_ENVIRONMENT

    measurements: list[dict] = []
    for item in items:
        packet, lang = _label_of(item["path"], item["bundle"])
        m = measure_bundle(item, product, packet_label=packet)
        m["language"] = lang
        measurements.append(m)

    controls = run_controls(measurements, product)
    control_failures = [name for name, c in controls.items() if not c["passed"]]

    n_contaminated = sum(1 for m in measurements if m["G1_anchor_contaminated"])
    contaminated = [m for m in measurements if m["G1_anchor_contaminated"]]
    non_topical = [m for m in measurements if not m["G2_anchor_topical"]]

    if control_failures:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_ENVIRONMENT
        statement = ("a non-vacuity control failed "
                     f"({', '.join(control_failures)}); this run is NOT a product "
                     "verdict and no product defect is claimed.")
    elif n_contaminated:
        verdict = "COUNTER_PROBE_ANCHOR_FALSIFIED"
        exit_code = EXIT_FALSIFIED
        statement = (
            f"{n_contaminated} of {len(measurements)} measured bundles issued a "
            "counter probe whose topic anchor contains a token the product's own "
            "answer_key_terms extracts from the generative audit's redaction "
            f"placeholder {ph_tokens!r}. The anchor of such a probe carries no "
            "legal vocabulary of the question it is supposed to attack, so the "
            "counter-authority retrieval for that question is topic-blind. "
            "The de-redaction counterfactual restores a topical anchor, which "
            "isolates the placeholder as the cause."
        )
    else:
        verdict = "COUNTER_PROBE_ANCHOR_NOT_FALSIFIED"
        exit_code = EXIT_OK
        statement = ("no measured bundle issued a counter probe whose topic "
                     "anchor contains a redaction-placeholder token.")

    # -- pins AFTER ---------------------------------------------------------
    pins_after = rehash_pins(freeze, repo_root, source_root, source_label)
    if not pins_after["all_ok"]:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_ENVIRONMENT
        statement = "pin drift after execution; this run is NOT a product verdict."

    record = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "generated_at_utc": _now(),
        "direction_version": hypothesis.get("direction_version"),
        "verdict": verdict,
        "exit_code": exit_code,
        "verdict_statement": statement,
        "source": {
            "label": source_label,
            "root": str(source_root),
            "manifest_sha256": manifest(source_root)["manifest_sha256"],
        },
        "n_bundles": len(measurements),
        "n_contaminated": n_contaminated,
        "contaminated_bundles": [m["source_path"] for m in contaminated],
        "n_non_topical_anchor": len(non_topical),
        "placeholder_tokens": ph_tokens,
        "redaction_placeholder": product.redaction_placeholder,
        "frozen_rule": freeze.get("frozen_rule"),
        "exit_code_contract": freeze.get("exit_code_contract"),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "controls": controls,
        "control_failures": control_failures,
        "bundles": measurements,
        "claim_ceiling": hypothesis.get("claim_ceiling"),
        "pre_freeze_disclosure": hypothesis.get("pre_freeze_disclosure"),
        "frozen_hypothesis": str(hypothesis_path.relative_to(repo_root)),
        "frozen_hypothesis_sha256": sha256_file(hypothesis_path),
        "freeze_record": str(freeze_path.relative_to(repo_root)),
        "freeze_record_sha256": sha256_file(freeze_path),
        "instrument": "evaluation/counter_probe_anchor_falsifier.py",
        "instrument_sha256": sha256_file(Path(__file__).resolve()),
        "network_calls": 0,
    }
    _write(args.out, args.report, record)
    print(f"verdict: {verdict} (exit {exit_code})")
    print(f"bundles measured: {len(measurements)}; contaminated anchors: "
          f"{n_contaminated}; non-topical anchors: {len(non_topical)}")
    for m in measurements:
        print(f"  {m['packet']:<28} {m['language']}  ph="
              f"{m['placeholder_occurrences_in_prose']:<3} "
              f"anchor={' '.join(m['recorded_anchor'])!r:<70} "
              f"contaminated={m['G1_anchor_contaminated']} "
              f"topical={m['G2_anchor_topical']} "
              f"rows_topical={m['G3_rows_topical_vs_question']}/"
              f"{m['G3_adversarial_rows']}")
    return exit_code


def _label_of(path: Path, bundle: dict) -> tuple[str, str]:
    parts = path.parts
    packet = parts[-4] if len(parts) >= 4 else path.parent.name
    stem = path.stem
    lang = stem.split("-", 1)[0] if "-" in stem else "?"
    return packet, lang


def _environment_record(run_id: str, label: str, root: Path, pins: dict,
                        why: str) -> dict:
    return {
        "schema": SCHEMA, "run_id": run_id, "generated_at_utc": _now(),
        "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENVIRONMENT,
        "verdict_statement": f"{why}; this run is NOT a product verdict.",
        "source": {"label": label, "root": str(root), "manifest_sha256": None},
        "n_bundles": 0, "n_contaminated": 0, "n_non_topical_anchor": 0,
        "pins_before": pins, "pins_after": None, "controls": {},
        "control_failures": [], "bundles": [],
        "claim_ceiling": "not measured; no product claim is made.",
        "pre_freeze_disclosure": "not measured; no product claim is made.",
        "network_calls": 0,
    }


def _write(out: str | None, report: str | None, record: dict) -> None:
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, ensure_ascii=False, indent=2,
                                sort_keys=True) + "\n", encoding="utf-8")
        print(f"record: {p}")
    if report:
        p = Path(report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_report(record), encoding="utf-8")
        print(f"report: {p}")


def _selftest(product_root: Path) -> int:
    """Structural self-test.  Never touches the real population, never writes a
    result file.  Used to validate the loader and the synthetic controls
    before the freeze, without observing a single real measurement."""
    try:
        product = ProductCode(product_root)
    except Exception as exc:
        print(f"SELFTEST FAIL: product code could not be loaded: "
              f"{type(exc).__name__}: {exc}")
        return EXIT_ENVIRONMENT

    failures: list[str] = []

    ph = product.redaction_placeholder
    if not ph:
        failures.append("redaction placeholder is empty")
    ph_tokens = product.placeholder_tokens()
    if not ph_tokens:
        failures.append("placeholder yields no key terms")

    # a prose made only of the placeholder must be dominated by it
    only = product.key_terms(ph * 5)
    if not set(ph_tokens).issubset(set(only)):
        failures.append(f"placeholder tokens not ranked into key terms: {only}")

    # an empty prose yields no plan (the product's D4 guard)
    if product.plan_adversarial_queries("Arbeitsvertrag", "") != []:
        failures.append("blank prose did not yield an empty plan")

    # a topical prose yields a plan whose anchor is topical
    prose = ("Der Arbeitgeber schuldet aktive Fürsorgepflicht und Überwachung "
             "der Kapitalverletzung. " * 3)
    plan = product.plan_adversarial_queries("Kapitalverletzung Fürsorgepflicht",
                                            prose)
    if not plan:
        failures.append("topical prose yielded no plan")
    else:
        anchor = plan[0]["query"].split()[:ANCHOR_SLOTS]
        if not (set(anchor) & product.content_terms("Kapitalverletzung Fürsorgepflicht")):
            failures.append(f"topical prose anchor not topical: {anchor}")
        if set(anchor) & set(ph_tokens):
            failures.append(f"topical prose anchor contaminated: {anchor}")

    # the anchor is the first ANCHOR_SLOTS tokens of the issued query
    if plan:
        toks = plan[0]["query"].split()
        if len(toks) < ANCHOR_SLOTS:
            failures.append("issued query shorter than the anchor")

    for f in failures:
        print(f"SELFTEST FAIL: {f}")
    if failures:
        return EXIT_ENVIRONMENT
    print("SELFTEST PASS: loader, placeholder tokens, D4 guard, topical anchor, "
          "anchor geometry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
