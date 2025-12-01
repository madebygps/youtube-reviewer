from typing import List, Optional
from pydantic import BaseModel, Field


class ConceptExplanation(BaseModel):
    """A key concept from the video."""

    term: str = Field(..., description="Concept name")
    definition: str = Field(..., description="One sentence definition")
    relevance: str = Field(..., description="One sentence: why it matters in this video")
    timestamp: Optional[str] = Field(None, description="e.g. '00:05:30'")
    timestamp_seconds: Optional[int] = Field(None, description="Timestamp in seconds for video seeking")


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


class ConnectionsResponse(BaseModel):
    """Phase 3: Connections between key concepts."""

    connections: List[ConnectionInsight] = Field(
        ...,
        description="Relationships and connections between the key concepts",
    )
    synthesis: str = Field(
        ...,
        description="A brief synthesis of how all the concepts work together",
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
    video_id: Optional[str] = Field(
        default=None,
        description="Video ID for cache lookup in subsequent phases",
    )

class ClaimVerifierResponse(BaseModel):
    """Phase 2: Verifies Claims made in videos"""
    claim: str
    verdict: str