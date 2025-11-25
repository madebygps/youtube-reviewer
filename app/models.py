from typing import List, Optional
from agent_framework import WorkflowEvent
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

class KeyConceptsResponse(BaseModel):
    """Phase 1: Just the key concepts"""
    key_concepts: List[ConceptExplanation]

class DeepComprehensionNotes(BaseModel):
    """Comprehensive study notes for deep understanding of video content."""

    main_thesis: str = Field(
        ...,
        description="The central argument or main point of the video in 1-2 sentences",
    )
    key_concepts: List[ConceptExplanation] = Field(
        ...,
        description="Key terms, acronyms, and concepts that need explanation",
    )
    argument_chains: List[ArgumentChain] = Field(
        ...,
        description="The logical chains of reasoning presented in the video",
    )
    connections: List[ConnectionInsight] = Field(
        default_factory=list,
        description="Important relationships between concepts",
    )
    synthesis: str = Field(
        ...,
        description="A synthesized understanding tying everything together",
    )
    open_questions: List[str] = Field(
        default_factory=list,
        description="Questions left unanswered or areas for further research",
    )


class GenerateInsightsRequest(BaseModel):
    """Request model for generating insights from a YouTube video."""

    video_url: str = Field(..., description="The YouTube video URL to analyze")
    custom_prompt: Optional[str] = Field(
        None, description="Optional custom prompt for insight generation"
    )


class GenerateInsightsResponse(BaseModel):
    """Response model for insights generation."""

    success: bool = Field(..., description="Whether the operation was successful")
    notes: Optional[DeepComprehensionNotes] = Field(
        None, description="Deep comprehension notes"
    )
    message: Optional[str] = Field(
        None, description="Optional message or error details"
    )


class GenerateInsightsEvent(WorkflowEvent):
    """Event emitted when insights generation is complete."""

    def __init__(self, notes: DeepComprehensionNotes):
        super().__init__(
            f"Deep comprehension complete with {len(notes.key_concepts)} concepts"
        )
        self.notes = notes


class DeepComprehensionAgentResponse(BaseModel):
    """Response from the deep comprehension agent."""

    notes: DeepComprehensionNotes = Field(
        ...,
        description="The comprehensive study notes",
    )
