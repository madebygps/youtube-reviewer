from typing import List, Optional
from agent_framework import WorkflowEvent
from pydantic import BaseModel, Field


class ActionableInsight(BaseModel):
    description: str = Field(
        ...,
        description="The actionable insight derived from the video captions.",
    )
    timestamp: str = Field(
        ...,
        description="The timestamp from when the actionable insight is based off of.",
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
    insights: List[ActionableInsight] = Field(
        default_factory=list, description="List of actionable insights"
    )
    message: Optional[str] = Field(
        None, description="Optional message or error details"
    )


class GenerateInsightsEvent(WorkflowEvent):
    """Event emitted when insights generation is complete."""

    def __init__(self, insights_data: "ActionableInsightsAgentResponse"):
        super().__init__(
            f"Insights generation complete with {len(insights_data.insights)} insights"
        )
        self.insights_data = insights_data


class ActionableInsightsAgentResponse(BaseModel):
    insights: List[ActionableInsight] = Field(
        ...,
        description="A list of actionable insights derived from the video captions.",
    )
