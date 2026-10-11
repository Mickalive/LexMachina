"""
LexMachina Frontier — Generative Audit v2

Provider-agnostic sourced legal answer generation plus an independent
counter-authority/adversarial pass.

This package answers the charter question:
  Can a query_result_bundle be turned into a genuinely generative,
  source-grounded legal answer and then independently challenged
  for contradictory, limiting, distinguishing or exception authorities,
  with every surfaced citation constrained to retrieved OpenCaseLaw
  decision IDs and verifiable against sources?
"""

from .provider import Provider, ProviderResult
from .source_packing import CitationValidator, DecisionBundle, Decision
from .adversarial import AdversarialPass, AdversarialFinding
from .models import StatusLabel, DecisionStatus, AnswerPackage, uncertainty_from_evidence
from .integration_contract import package_answer
from .opencaselaw import OpenCaseLawAttestor, PostGenerationValidator, validate_bundle_against_ocl

__version__ = "2.0.0"