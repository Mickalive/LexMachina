"""Design-phase notes (disclosed, not scored).

Everything in this module was measured BEFORE any variant score was computed,
during the design of V1/V2, on the same three served bundles and the same
frozen rule.  It is recorded because the charter's hypothesis makes a claim
about PROJ_* that the frozen rule does not support, and because a reader must
be able to see why the shipped variants use the operators they use.

Scripts that produced these numbers live in the run artifacts as
DESIGN_PROBES.json (values transcribed here by the same driver that scores the
variants, so there is one provenance chain).
"""
from __future__ import annotations

FROZEN_RULE_PROPERTIES = {
    "PROJ_RANK_is_coordinate_invariant": {
        "statement": (
            "PROJ_RANK is spearman(TF-IDF cosine distance from each row to the "
            "query vector, retrieval rank) computed in metrics.projection(). It "
            "never reads x or y. No layout variant of any kind can move it."
        ),
        "consequence": (
            "de-kapitalverletzung fails PROJ_RANK (0.093 < 0.30) under every "
            "variant; fr and it pass it under every variant. The charter "
            "hypothesis that a relevance axis makes PROJ_RANK 'definitional' is "
            "NOT supported by the frozen rule as written."
        ),
    },
    "PROJ_SPEARMAN_and_PROJ_KNN10_reference_space": {
        "statement": (
            "Both read the TF-IDF cosine structure of ALL decision rows in the "
            "bundle, including un-hydrated shells whose bodies are a docket "
            "number only (median TF-IDF nnz 0-1). 57-76 percent of all row pairs "
            "sit at cosine distance exactly 1.0."
        ),
        "consequence": (
            "The bars are attainable but not by a linear 2-D truncation; a "
            "neighbourhood-preserving layout is required."
        ),
    },
    "STRUCTURE_SEP_is_unreachable_on_two_of_three_bundles": {
        "statement": (
            "STRUCTURE_SEP = mean intra-cluster cosine / mean inter-cluster "
            "cosine over the frozen TF-IDF space. On the served bundles the "
            "hydrated-hydrated cosine distances have mean 0.978-0.984 and the "
            "10th percentile is 0.936-0.958. Even an ORACLE partition that "
            "assigns the most similar pairs to the intra side (k=8, the qmap "
            "cluster-count rule) yields a best-possible ratio of 0.914 (de), "
            "0.886 (fr) and 0.919 (it) against a 0.90 bar."
        ),
        "consequence": (
            "de and it cannot pass STRUCTURE_SEP under ANY clustering of these "
            "rows; fr can only do so under an oracle partition that no "
            "implementable clustering reaches. Reported as a measured ceiling, "
            "not as a variant failure."
        ),
    },
    "OUTLIER_VALIDITY_is_structurally_false_on_it": {
        "statement": (
            "The accepted artifact records citation_graph_degenerate=true for "
            "it-responsabilita-medica (no two rows share a BGE/ATF citation), "
            "and the frozen predicate is DEGENERATE->FAIL."
        ),
        "consequence": "it can never pass OUTLIER_VALIDITY under any variant.",
    },
}

DEFECTS_FIXED_DURING_BUILD = {
    "spectral_affinity_silent_fallback": {
        "found_by": "full driver run, scikit-learn 1.9.1 UserWarning emitted 12x",
        "symptom": (
            "SpectralEmbedding(affinity='nearest_neighbors') with sparse TF-IDF "
            "input emits 'Nearest neighbors affinity currently does not support "
            "sparse input, falling back to rbf affinity'. The operator that ran "
            "was therefore a dense RBF affinity, not the kNN graph the variant "
            "claims to use."
        ),
        "fix": (
            "The kNN similarity graph is now built explicitly "
            "(geometry_core.knn_similarity, cosine distance, k=12, "
            "distance-weighted, symmetrised) and passed as affinity='precomputed'."
        ),
        "effect_on_scores": (
            "V1 hydrate_then_cluster is re-measured with the explicit graph; V2 "
            "relevance_ordered does not use the spectral operator at all (its "
            "coordinates are the rerank axis and the language bands), so V2's "
            "numbers are unaffected. Both the pre-fix and post-fix V1 numbers "
            "are recorded in REPRODUCIBILITY.json."
        ),
    },
    "acceptance_check_key_error": {
        "found_by": "full driver run",
        "symptom": "acceptance_checks indexed a per-bundle control dict as if it "
                   "carried the aggregate non-vacuity flag.",
        "fix": "iterate controls[variant][qid]['harness_non_vacuous'].",
        "effect_on_scores": "none; artifact emission only.",
    },
}

DESIGN_PHASE_PROBES = {
    "note": (
        "Measured during variant design, before the variants were frozen, on the "
        "rule's own reference space (TF-IDF fit over ALL rows of each bundle). "
        "Recorded as evidence for the operator choice; NOT a scored candidate."
    ),
    "projection_operators_spearman_rho_knn10": {
        "de-kapitalverletzung": {
            "truncated_svd_2d": {"rho": 0.054, "knn10": 0.161},
            "metric_mds_cosine": {"rho": 0.338, "knn10": 0.186},
            "isomap": {"rho": 0.237, "knn10": 0.214},
            "spectral_nearest_neighbors": {"rho": 0.551, "knn10": 0.225},
            "tsne": {"rho": 0.564, "knn10": 0.342},
        },
        "fr-bail-entretien": {
            "truncated_svd_2d": {"rho": 0.210, "knn10": 0.180},
            "metric_mds_cosine": {"rho": 0.431, "knn10": 0.244},
            "isomap": {"rho": 0.477, "knn10": 0.239},
            "spectral_nearest_neighbors": {"rho": 0.573, "knn10": 0.289},
            "tsne": {"rho": 0.582, "knn10": 0.391},
        },
        "it-responsabilita-medica": {
            "truncated_svd_2d": {"rho": 0.176, "knn10": 0.199},
            "metric_mds_cosine": {"rho": 0.325, "knn10": 0.200},
            "isomap": {"rho": 0.357, "knn10": 0.227},
            "spectral_nearest_neighbors": {"rho": 0.564, "knn10": 0.288},
            "tsne": {"rho": 0.560, "knn10": 0.408},
        },
    },
    "why_v1_uses_spectral_on_the_clusterable_rows_only": (
        "V1 is required to project the hydrated rows only. The spectral layout "
        "is the cheapest operator that preserves neighbourhoods of the "
        "query-conditioned rows; shells are placed outside the hull as "
        "unclustered context, which is what pulls V1's PROJ_SPEARMAN down to "
        "0.31-0.32 (still the best of the two shipped variants) and leaves both "
        "projection bars unmet."
    ),
    "why_v2_is_scored_even_though_its_projection_is_weaker": (
        "V2 is the charter's relevance-ordered layout. Its purpose is the "
        "relevance axis and the language bands, not distance fidelity; it is "
        "scored under exactly the same rule and its projection numbers are "
        "reported as measured."
    ),
    "why_no_third_variant_was_opened": (
        "A layout whose 2-D coordinates are fitted to maximise the very "
        "correlation the frozen rule measures (spectral over ALL rows reaches "
        "rho 0.551-0.573, above the 0.50 bar) is technically in budget, but "
        "opening it after V1/V2 scores were visible would be score-fishing, and "
        "deciding whether proximity may be bought that way is a product "
        "question for the human gate, not a builder's call. The number is "
        "published here so the owner can see it exists."
    ),
}
