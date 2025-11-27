from typing import List, Optional
from pydantic import BaseModel, Field


class ConceptExplanation(BaseModel):
    """A key concept that needs explanation for full comprehension."""

    term: str = Field(
        ...,
        description="The term, acronym, or concept name (e.g., 'ESF', 'SDRs', 'Bretton Woods')",
    )
    definition: str = Field(
        ...,
        description="A clear, concise definition of the concept",
    )
    historical_context: Optional[str] = Field(
        None,
        description="When/why this was created, what problem it solved",
    )
    how_it_works: Optional[str] = Field(
        None,
        description="Explanation of the mechanism or process",
    )
    relevance_to_content: str = Field(
        ...,
        description="Why this concept matters in the context of the video's argument",
    )
    timestamp: Optional[str] = Field(
        None,
        description="Timestamp where this concept is first discussed",
    )


class ArgumentChain(BaseModel):
    """A logical chain of reasoning presented in the video."""

    title: str = Field(
        ...,
        description="A short title for this argument chain",
    )
    premise: str = Field(
        ...,
        description="The starting assumption or fact",
    )
    reasoning_steps: List[str] = Field(
        ...,
        description="The logical steps that connect premise to conclusion",
    )
    conclusion: str = Field(
        ...,
        description="The conclusion drawn from the reasoning",
    )
    implications: Optional[str] = Field(
        None,
        description="What this means for the viewer or broader context",
    )


class ConnectionInsight(BaseModel):
    """A relationship or connection between concepts."""

    concept_a: str = Field(..., description="First concept")
    concept_b: str = Field(..., description="Second concept")
    relationship: str = Field(
        ...,
        description="How these concepts relate or interact",
    )
    significance: str = Field(
        ...,
        description="Why this connection matters",
    )

class ThesisArgumentResponse(BaseModel):
    """Phase 2: Main thesis and argument chains"""

    main_thesis: str = Field(
        ...,
        description="The central argument or main point of the video in 1-2 sentences",
    )
    argument_chains: List[ArgumentChain] = Field(
        ...,
        description="The logical chains of reasoning presented in the video",
    )


class KeyConceptsResponse(BaseModel):
    """Phase 1: Key concepts extracted from video content."""
    key_concepts: List[ConceptExplanation]
    captions: Optional[str] = Field(
        default=None,
        description="Original captions text used to generate concepts (for subsequent phases)",
    )

class ClaimVerifierResponse(BaseModel):
    """Phase 2: Verifies Claims made in videos"""
    claim: str
    verdict: str