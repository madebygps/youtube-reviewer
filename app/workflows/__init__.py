"""Workflow modules for the YouTube reviewer."""

from workflows.key_concepts import get_key_concepts_workflow, key_concepts_workflow
from workflows.thesis_argument import get_thesis_argument_workflow, thesis_argument_workflow
from workflows.concept_connections import get_connections_workflow, connections_workflow
from workflows.claim_verifier import get_claim_verifier_workflow, claim_verifier_workflow
from workflows.quiz_generator import get_quiz_generator_workflow, quiz_generator_workflow

__all__ = [
    "get_key_concepts_workflow",
    "get_thesis_argument_workflow",
    "get_connections_workflow",
    "get_claim_verifier_workflow",
    "get_quiz_generator_workflow",
    "key_concepts_workflow",
    "thesis_argument_workflow",
    "connections_workflow",
    "claim_verifier_workflow",
    "quiz_generator_workflow",
]
