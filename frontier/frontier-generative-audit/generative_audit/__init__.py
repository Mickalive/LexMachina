"""LexMachina Frontier — generative audit package (canonical in-scope tree).

Provider-agnostic, source-grounded legal answer generation plus an
independent counter-authority / adversarial pass.

This tree is the CANONICAL deliverable of Frontier team
``frontier-generative-audit`` (charter v2).  The repository-root
``generative_audit/`` package is the frozen historical artifact of accepted
cycle 38172462365 and is kept only as provenance; new work happens here.

Narrow integration surface for the product lane::

    from generative_audit.integration_contract import run_generative_audit
    audited_bundle = run_generative_audit(product_bundle_dict)

See README.md one directory up for the full contract.
"""

__version__ = "2.1.0"
CANONICAL_TREE = "frontier/frontier-generative-audit"
