"""Workflow modules for the YouTube reviewer."""

from workflows.key_concepts import get_key_concepts_workflow, key_concepts_workflow
from workflows.thesis_argument import get_thesis_argument_workflow, thesis_argument_workflow

__all__ = [
    "get_key_concepts_workflow",
    "get_thesis_argument_workflow",
    "key_concepts_workflow",
    "thesis_argument_workflow",
]
