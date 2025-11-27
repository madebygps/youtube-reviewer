"""Workflow modules for the YouTube reviewer."""

from agent_framework.observability import setup_observability

from workflows.key_concepts import get_key_concepts_workflow, key_concepts_workflow
from workflows.thesis_argument import get_thesis_argument_workflow, thesis_argument_workflow

# Initialize agent framework observability
setup_observability()

__all__ = [
    "get_key_concepts_workflow",
    "get_thesis_argument_workflow",
    "key_concepts_workflow",
    "thesis_argument_workflow",
]
