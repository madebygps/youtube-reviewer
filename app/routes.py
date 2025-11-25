# Health check endpoint

import fastapi
import json
from datetime import datetime, timezone
import logging

import fastapi.responses
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from agent_framework import (
    ExecutorInvokedEvent,
    ExecutorFailedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)
from yt_agent import workflow as yt_workflow
from models import KeyConceptsResponse

logger = logging.getLogger(name=__name__)

router = APIRouter()


@router.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "Healthy"


@router.websocket("/ws/generateinsights")
async def websocket_generate_insights(websocket: WebSocket):
    """
    WebSocket endpoint for real-time deep comprehension notes generation.
    Streams workflow events back to the frontend as they occur.

    Protocol:
    1. Client connects and sends JSON: {"video_url": "https://..."}
    2. Server streams events: {"type": "...", "event": "...", "timestamp": "..."}
    3. Final message: {"type": "completed", "output": {...}, "timestamp": "..."}
    """
    await websocket.accept()

    try:
        data = await websocket.receive_text()
        request_data = json.loads(data)

        video_url = request_data.get("video_url")
        if not video_url:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "video_url is required",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await websocket.close(code=1008, reason="video_url required")
            return

        logger.info(f"🎬 Starting deep comprehension for video: {video_url}")

        await websocket.send_json(
            {
                "type": "started",
                "message": "Deep comprehension workflow initiated...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        workflow_output = None
        try:
            async for event in yt_workflow.run_stream(json.dumps(request_data)):
                now = datetime.now(timezone.utc).isoformat()
                event_data = None

                if isinstance(event, WorkflowStartedEvent):
                    event_data = {
                        "type": "workflow_started",
                        "event": str(event.data),
                        "timestamp": now,
                    }
                elif isinstance(event, WorkflowOutputEvent):
                    workflow_output = event.data
                    if isinstance(workflow_output, KeyConceptsResponse):
                        workflow_output = workflow_output.model_dump()

                    event_data = {
                        "type": "workflow_output",
                        "event": workflow_output,
                        "timestamp": now,
                    }
                elif isinstance(event, ExecutorInvokedEvent):
                    event_data = {
                        "type": "step_started",
                        "event": event.data,
                        "id": event.executor_id,
                        "timestamp": now,
                    }

                elif isinstance(event, ExecutorFailedEvent):
                    event_data = {
                        "type": "step_failed",
                        "event": event.details.message,
                        "id": event.executor_id,
                        "timestamp": now,
                    }
                else:
                    continue

                await websocket.send_json(event_data)
                logger.info(f"📤 Sent event: {event_data['type']}")

            await websocket.send_json(
                {
                    "type": "completed",
                    "message": "Workflow completed successfully",
                    "output": workflow_output,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("✅ Deep comprehension workflow completed")

        except Exception as workflow_error:
            logger.error(f"❌ Workflow error: {workflow_error}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Workflow error: {str(workflow_error)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Root endpoint
@router.get("/", response_class=fastapi.responses.HTMLResponse)
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
