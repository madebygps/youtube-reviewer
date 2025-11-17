#!/usr/bin/env python3
"""
FastAPI Backend for YouTube Reviewer
Provides REST API endpoints for generating actionable insights from YouTube videos.
"""
import contextlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import fastapi
import fastapi.responses
import fastapi.staticfiles
import opentelemetry.instrumentation.fastapi as otel_fastapi
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import telemetry
from agent_framework import (
    ChatMessage,
    ExecutorInvokedEvent,
    ExecutorCompletedEvent,
    ExecutorFailedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)
from yt_agent import workflow, ActionableInsight

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Pydantic models for API
class GenerateInsightsRequest(BaseModel):
    """Request model for generating insights from a YouTube video."""
    video_url: str = Field(..., description="The YouTube video URL to analyze")
    custom_prompt: Optional[str] = Field(None, description="Optional custom prompt for insight generation")


class GenerateInsightsResponse(BaseModel):
    """Response model for insights generation."""
    success: bool = Field(..., description="Whether the operation was successful")
    insights: List[ActionableInsight] = Field(default_factory=list, description="List of actionable insights")
    message: Optional[str] = Field(None, description="Optional message or error details")


@contextlib.asynccontextmanager
async def lifespan(app):
    """Manage application lifespan - startup and shutdown events"""
    logger.info("🚀 Starting YouTube Reviewer API Server...")
    telemetry.configure_opentelemetry()
    yield
    logger.info("🛑 Shutting down YouTube Reviewer API Server...")


app = FastAPI(
    title="YouTube Reviewer API",
    description="REST API for generating actionable insights from YouTube videos",
    version="1.0.0",
    lifespan=lifespan
)

otel_fastapi.FastAPIInstrumentor.instrument_app(app, exclude_spans=["send"])


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "Healthy"


@app.post("/generateinsights", response_model=GenerateInsightsResponse)
async def generate_insights(request: GenerateInsightsRequest) -> GenerateInsightsResponse:
    """
    Generate actionable insights from a YouTube video.
    
    This endpoint processes a YouTube video URL, extracts captions,
    and generates actionable insights using an AI agent workflow.
    
    Args:
        request: Contains the YouTube video URL to analyze
        
    Returns:
        GenerateInsightsResponse with success status and insights list
    """
    try:
        logger.info(f"📹 Generating insights for video: {request.video_url}")
        
        # Create input message for the workflow
        # Format: video_url|||PROMPT_SEPARATOR|||custom_prompt (if provided)
        message_text = request.video_url
        if request.custom_prompt:
            message_text = f"{request.video_url}|||PROMPT_SEPARATOR|||{request.custom_prompt}"
        input_message = ChatMessage(role="user", text=message_text)
        
        # Run the workflow and collect the output
        workflow_output = None
        async for event in workflow.run_stream(input_message):
            if isinstance(event, WorkflowOutputEvent):
                # Capture the workflow output (list of insights)
                workflow_output = event.data
                count = len(workflow_output) if workflow_output else 0
                logger.info(f"✅ Workflow completed with {count} insights")
                break
            elif isinstance(event, ExecutorFailedEvent):
                error_msg = event.details.message or "Workflow failed"
                logger.error(f"❌ Workflow failed: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate insights: {error_msg}"
                )
        
        if workflow_output is None:
            raise HTTPException(
                status_code=500,
                detail="Workflow did not produce output"
            )
        
        # Convert output to response format
        insights = []
        if isinstance(workflow_output, list):
            for item in workflow_output:
                if isinstance(item, ActionableInsight):
                    insights.append(item)
                elif isinstance(item, dict):
                    insights.append(ActionableInsight(**item))
        
        logger.info(f"✅ Successfully generated {len(insights)} insights")
        
        return GenerateInsightsResponse(
            success=True,
            insights=insights,
            message=f"Generated {len(insights)} actionable insights"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@app.websocket("/ws/generateinsights")
async def websocket_generate_insights(websocket: WebSocket):
    """
    WebSocket endpoint for real-time insights generation.
    Streams workflow events back to the frontend as they occur.
    
    Protocol:
    1. Client connects and sends JSON: {"video_url": "https://..."}
    2. Server streams events: {"type": "...", "event": "...", "timestamp": "..."}
    3. Final message: {"type": "completed", "output": [...], "timestamp": "..."}
    """
    await websocket.accept()
    
    try:
        # Receive the initial request from the client
        data = await websocket.receive_text()
        request_data = json.loads(data)
        
        video_url = request_data.get('video_url')
        if not video_url:
            await websocket.send_json({
                "type": "error",
                "message": "video_url is required",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=1008, reason="video_url required")
            return
        
        custom_prompt = request_data.get('custom_prompt')
        logger.info(f"🤖 WebSocket insights request for video: {video_url}")
        
        # Send initial acknowledgment
        await websocket.send_json({
            "type": "started",
            "message": "Insights generation workflow initiated...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Create input message for the workflow
        # Format: video_url|||PROMPT_SEPARATOR|||custom_prompt (if provided)
        message_text = video_url
        if custom_prompt:
            message_text = f"{video_url}|||PROMPT_SEPARATOR|||{custom_prompt}"
        input_message = ChatMessage(role="user", text=message_text)
        
        # Run the workflow and stream events
        workflow_output = None
        try:
            async for event in workflow.run_stream(input_message):
                now = datetime.now(timezone.utc).isoformat()
                
                if isinstance(event, WorkflowStartedEvent):
                    event_data = {
                        "type": "workflow_started",
                        "event": str(event.data),
                        "timestamp": now
                    }
                elif isinstance(event, WorkflowOutputEvent):
                    # Capture the workflow output
                    workflow_output = event.data
                    # Convert insights to dict format
                    if isinstance(workflow_output, list):
                        insights_list = []
                        for item in workflow_output:
                            if isinstance(item, ActionableInsight):
                                insights_list.append(item.model_dump())
                            elif isinstance(item, dict):
                                insights_list.append(item)
                        workflow_output = insights_list
                    
                    event_data = {
                        "type": "workflow_output",
                        "event": workflow_output,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorInvokedEvent):
                    event_data = {
                        "type": "step_started",
                        "event": event.data,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorCompletedEvent):
                    event_data = {
                        "type": "step_completed",
                        "event": event.data,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorFailedEvent):
                    event_data = {
                        "type": "step_failed",
                        "event": event.details.message,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                else:
                    # Generic event
                    event_data = {
                        "type": "event",
                        "event": str(event),
                        "timestamp": now
                    }
                
                await websocket.send_json(event_data)
                logger.info(f"📤 Sent event: {event_data['type']}")
            
            # Send completion message with the workflow output
            await websocket.send_json({
                "type": "completed",
                "message": "Workflow completed successfully",
                "output": workflow_output,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.info("✅ Insights generation workflow completed")
            
        except Exception as workflow_error:
            logger.error(f"❌ Workflow error: {workflow_error}")
            await websocket.send_json({
                "type": "error",
                "message": f"Workflow error: {str(workflow_error)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Root endpoint
@app.get("/", response_class=fastapi.responses.HTMLResponse)
async def root():
    """Root endpoint."""
    return """
    <html>
        <head><title>YouTube Reviewer API</title></head>
        <body>
            <h1>YouTube Reviewer API</h1>
            <p>API service is running.</p>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><strong>POST /generateinsights</strong> - Generate insights from YouTube video</li>
                <li><strong>WS /ws/generateinsights</strong> - WebSocket for real-time insights streaming</li>
            </ul>
        </body>
    </html>
    """


# Serve static files directly from root, if the "static" directory exists
if os.path.exists("static"):
    app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory="static", html=True),
        name="static"
    )
