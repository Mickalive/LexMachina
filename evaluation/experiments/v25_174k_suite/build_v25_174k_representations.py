#!/usr/bin/env python3
"""
Build v25 174k evaluation representations for the frozen formal suite.

FREEZES the sample and representation pipelines BEFORE any measurement:
- Row order = exact list order of evaluation/data/174k/metadata_174k.json
- Pipeline parameters frozen in protocol_v25_174k_suite.json
- Deterministic (seed 42)

Outputs:
- results/evaluation/v25_174k_formal_suite/embeddings/<name>.npy
- results/evaluation/v25_174k_formal_suite/embeddings/build_manifest.json
"""
import json
import time
import hashlib
import numpy as np
import logging
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
METADATA_PATH = ROOT / "evaluation/data/174k/metadata_174k.json"
CORPUS_DIR = Path("/tmp/opencode/lexcorpus2/out/canonical")
OUT_DIR = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
SEED = 42
SVD_DIM = 128

PIPELINES = {
    "cited_decisions_tfidf": dict(field="cited_decisions", max_features=5000, ngram_range=(1, 2), min_df=2, max_df=0.95),
    "outcome_tfidf": dict(field="outcome", max_features=3000, ngram_range=(1, 2), min_df=2, max_df=0.95),
    "regeste_tfidf": dict(field="regeste", max_features=10000, ngram_range=(1, 2), min_df=2, max_df=0.95),
    "full_text_tfidf_light": dict(field="full_text", max_features=3000, ngram_range=(1, 1), min_df=5, max_df=0.9),
}


def load_metadata():
    with open(METADATA_PATH) as f:
        return json.load(f)


def load_corpus():
    """dict decision_id -> record, from regenerated pinned-parquet year files."""
    records = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_*.jsonl")):
        with open(year_file) as fh:
            for line in fh:
                if not line.strip():
                    continue
                d = json.loads(line)
                records[d["decision_id"]] = d
    return records


def field_text(rec, field):
    if field == "cited_decisions":
        cited = rec.get("cited_decisions") or []
        return " ".join(str(c) for c in cited)
    if field == "full_text":
        ft = rec.get("full_text") or ""
        return ft[:5000]
    v = rec.get(field)
    if v is None or v == "null":
        return ""
    return str(v)


def tfidf_svd(texts, params, svd_dim=SVD_DIM):
    vec = TfidfVectorizer(
        max_features=params["max_features"],
        ngram_range=tuple(params["ngram_range"]),
        min_df=params["min_df"],
        max_df=params["max_df"],
        sublinear_tf=True,
        strip_accents="unicode",
    )
    nonempty = [i for i, t in enumerate(texts) if t.strip()]
    idxs = np.array(nonempty)
    X = vec.fit_transform([texts[i] for i in nonempty])
    k = min(svd_dim, X.shape[1] - 1, X.shape[0] - 1)
    svd = TruncatedSVD(n_components=k, random_state=SEED)
    R = svd.fit_transform(X)
    R = normalize(R, norm="l2", axis=1)
    out = np.zeros((len(texts), svd_dim), dtype=np.float32)
    out[idxs, :R.shape[1]] = R
    out = normalize(out, norm="l2", axis=1)
    return out


def hybrid(a, b, alpha):
    a = normalize(a, norm="l2", axis=1)
    b = normalize(b, norm="l2", axis=1)
    h = alpha * a + (1 - alpha) * b
    return normalize(h, norm="l2", axis=1)


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()
    corpus = load_corpus()
    logger.info(f"metadata={len(metadata)} corpus_records={len(corpus)}")

    ids = [m["decision_id"] for m in metadata]
    missing = [i for i, did in enumerate(ids) if did not in corpus]
    present = [i for i, did in enumerate(ids) if did in corpus]
    actual_n = len(present)
    logger.info(f"intersection: {actual_n}/{len(ids)}; missing={len(missing)}")
    if missing:
        logger.warning(f"first 20 missing ids: {[ids[i] for i in missing[:20]]}")

    # Precompute text fields once
    texts = {}
    for name, params in PIPELINES.items():
        texts[name] = [field_text(corpus[ids[i]], params["field"]) for i in present]

    emb = {}
    base = {}
    for name, params in PIPELINES.items():
        logger.info(f"building {name} ...")
        e = tfidf_svd(texts[name], params)
        base[name] = e
        np.save(OUT_DIR / f"{name}.npy", e)
        logger.info(f"  {name}: {e.shape}")

    logger.info("building hybrids ...")
    hybrids = {
        "cited_outcome_hybrid_0.5": (base["cited_decisions_tfidf"], base["outcome_tfidf"], 0.5),
        "cited_outcome_hybrid_0.7": (base["cited_decisions_tfidf"], base["outcome_tfidf"], 0.7),
        "regeste_full_text_hybrid_0.5": (base["regeste_tfidf"], base["full_text_tfidf_light"], 0.5),
        "regeste_full_text_hybrid_0.7": (base["regeste_tfidf"], base["full_text_tfidf_light"], 0.7),
    }
    for name, (a, b, alpha) in hybrids.items():
        e = hybrid(a, b, alpha)
        emb[name] = e
        np.save(OUT_DIR / f"{name}.npy", e)
        logger.info(f"  {name}: {e.shape}")

    manifest = {
        "run_id": f"eval_v25_174k_embeddings_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "direction_version": 25,
        "github_run": "36013963912",
        "seed": SEED,
        "metadata_order_defined_by": str(METADATA_PATH),
        "metadata_total": len(ids),
        "actual_n_rows": actual_n,
        "missing_ids": [ids[i] for i in missing[:50]],
        "n_missing": len(missing),
        "corpus_source": "pinned parquet (huggingface voilaj/swiss-caselaw bger.parquet) regenerated via corpus/acquisition/reproduce_full_corpus.py into /tmp/opencode/lexcorpus2/out/canonical",
        "representations": {name: f"{name}.npy" for name in list(base.keys()) + list(hybrids.keys())},
        "dim": SVD_DIM,
        "pipeline_params": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()} for k, v in PIPELINES.items()},
        "empty_row_counts": {
            name: int(sum(1 for t in texts[name] if not t.strip())) for name in texts
        },
        "duration_seconds": round(time.time() - t0, 1),
    }
    with open(OUT_DIR / "build_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"manifest saved; total duration {manifest['duration_seconds']}s")


if __name__ == "__main__":
    main()