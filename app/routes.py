
# Health check endpoint

import fastapi
import json
from datetime import datetime, timezone
import logging

import fastapi.responses
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from agent_framework import (
    ExecutorInvokedEvent,
    ExecutorCompletedEvent,
    ExecutorFailedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)
from yt_agent import workflow as yt_workflow
from models import ActionableInsight

logger = logging.getLogger(name=__name__)

router = APIRouter()


@router.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "Healthy"


@router.websocket("/ws/generateinsights")
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

        logger.info(f"🤖 WebSocket insights request for video: {video_url}")

        # Send initial acknowledgment
        await websocket.send_json(
            {
                "type": "started",
                "message": "Insights generation workflow initiated...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Run the workflow and stream events
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

            # Send completion message with the workflow output
            await websocket.send_json(
                {
                    "type": "completed",
                    "message": "Workflow completed successfully",
                    "output": workflow_output,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("✅ Insights generation workflow completed")

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