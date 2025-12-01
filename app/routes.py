# Health check endpoint

import fastapi
import json
import contextlib
from datetime import datetime, timezone
import logging
from typing import Any, Callable

import fastapi.responses
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from opentelemetry.trace import SpanKind

from agent_framework import (
    ExecutorInvokedEvent,
    ExecutorFailedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)
from agent_framework.observability import get_tracer
from workflows import key_concepts_workflow, thesis_argument_workflow, connections_workflow, claim_verifier_workflow
from models import KeyConceptsResponse, ThesisArgumentResponse, ConnectionsResponse, ClaimVerifierResponse

logger = logging.getLogger(__name__)


router = APIRouter()

def _timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def _send_error(websocket: WebSocket, message: str, phase: int | None = None) -> None:
    """Send an error message via WebSocket."""
    payload: dict[str, Any] = {
        "type": "error",
        "message": message,
        "timestamp": _timestamp(),
    }
    if phase is not None:
        payload["phase"] = phase
    await websocket.send_json(payload)


async def _stream_workflow_events(
    websocket: WebSocket,
    workflow,
    input_data: str,
    phase: int,
    output_processor: Callable | None = None,
) -> Any:
    """
    Stream workflow events to the WebSocket and return the final output.
    
    Args:
        websocket: The WebSocket connection
        workflow: The workflow to run
        input_data: JSON string input for the workflow
        phase: Phase number for event tagging
        output_processor: Optional function to process workflow output before returning
    
    Returns:
        The workflow output (processed if output_processor provided)
    """
    workflow_output = None
    
    async for event in workflow.run_stream(input_data):
        now = _timestamp()
        event_data = None

        if isinstance(event, WorkflowStartedEvent):
            event_data = {
                "type": "workflow_started",
                "event": str(event.data),
                "timestamp": now,
                "phase": phase,
            }
        elif isinstance(event, WorkflowOutputEvent):
            workflow_output = event.data
            if output_processor:
                workflow_output = output_processor(workflow_output)
            
            event_data = {
                "type": "workflow_output",
                "event": workflow_output if isinstance(workflow_output, dict) else workflow_output,
                "timestamp": now,
                "phase": phase,
            }
        elif isinstance(event, ExecutorInvokedEvent):
            event_data = {
                "type": "step_started",
                "event": event.data,
                "id": event.executor_id,
                "timestamp": now,
                "phase": phase,
            }
        elif isinstance(event, ExecutorFailedEvent):
            event_data = {
                "type": "step_failed",
                "event": event.details.message,
                "id": event.executor_id,
                "timestamp": now,
                "phase": phase,
            }
        else:
            continue

        await websocket.send_json(event_data)
        logger.info(f"📤 Phase {phase} - Sent event: {event_data['type']}")

    return workflow_output


@router.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "Healthy"


@router.websocket("/ws/phase1")
async def websocket_phase1(websocket: WebSocket):
    """
    WebSocket endpoint for Phase 1: Extract key concepts from a YouTube video.

    Protocol:
    1. Client connects and sends JSON: {"video_url": "https://...", "knowledge_level": "beginner|intermediate|advanced"}
    2. Server streams workflow events and outputs key concepts
    3. Final output includes captions for use in subsequent phases
    """
    await websocket.accept()

    try:
        initial_text = await websocket.receive_text()
        request_data = json.loads(initial_text)

        video_url = request_data.get("video_url") if isinstance(request_data, dict) else None
        if not video_url:
            await _send_error(websocket, "video_url is required")
            await websocket.close(code=1008, reason="video_url required")
            return

        logger.info(f"🎬 Starting Phase 1 for video: {video_url}")

        await websocket.send_json({
            "type": "phase_started",
            "phase": 1,
            "message": "Extracting key concepts...",
            "timestamp": _timestamp(),
        })

        def process_output(output):
            if isinstance(output, KeyConceptsResponse):
                result = output.model_dump()
                result["video_id"] = output.video_id  # Include video_id for Phase 2 cache lookup
                return result
            return output

        try:
            with get_tracer().start_as_current_span(
                "Phase 1: Key Concepts", kind=SpanKind.INTERNAL
            ) as span:
                span.set_attribute("video.url", video_url)
                
                workflow_output = await _stream_workflow_events(
                    websocket=websocket,
                    workflow=key_concepts_workflow,
                    input_data=json.dumps(request_data),
                    phase=1,
                    output_processor=process_output,
                )

                if workflow_output:
                    span.set_attribute("concepts.count", len(workflow_output.get("key_concepts", [])))

            await websocket.send_json({
                "type": "phase_completed",
                "phase": 1,
                "message": "Key concepts ready",
                "output": workflow_output,
                "timestamp": _timestamp(),
            })
            logger.info("✅ Phase 1 completed")

        except Exception as e:
            logger.error(f"❌ Phase 1 error: {e}")
            await _send_error(websocket, f"Workflow error: {str(e)}", phase=1)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await _send_error(websocket, str(e))
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/ws/phase2")
async def websocket_phase2(websocket: WebSocket):
    """
    WebSocket endpoint for Phase 2: Extract thesis and argument chains.

    Protocol:
    1. Client connects and sends JSON: {"captions": "..."} or {"video_url": "https://..."}
    2. Server streams workflow events and outputs thesis + argument chains
    """
    await websocket.accept()

    try:
        initial_text = await websocket.receive_text()
        request_data = json.loads(initial_text)

        video_id = request_data.get("video_id") if isinstance(request_data, dict) else None
        
        if not video_id:
            await _send_error(websocket, "video_id is required")
            await websocket.close(code=1008, reason="video_id required")
            return

        logger.info("🎬 Starting Phase 2")

        await websocket.send_json({
            "type": "phase_started",
            "phase": 2,
            "message": "Extracting thesis and arguments...",
            "timestamp": _timestamp(),
        })

        def process_output(output):
            if isinstance(output, ThesisArgumentResponse):
                return output.model_dump()
            return output

        try:
            with get_tracer().start_as_current_span(
                "Phase 2: Thesis & Arguments", kind=SpanKind.INTERNAL
            ) as span:
                span.set_attribute("video.id", video_id)
                
                workflow_output = await _stream_workflow_events(
                    websocket=websocket,
                    workflow=thesis_argument_workflow,
                    input_data=json.dumps({"video_id": video_id}),
                    phase=2,
                    output_processor=process_output,
                )

                if workflow_output:
                    span.set_attribute("argument_chains.count", len(workflow_output.get("argument_chains", [])))

            await websocket.send_json({
                "type": "phase_completed",
                "phase": 2,
                "message": "Thesis and arguments ready",
                "output": workflow_output,
                "timestamp": _timestamp(),
            })
            logger.info("✅ Phase 2 completed")

        except Exception as e:
            logger.error(f"❌ Phase 2 error: {e}")
            await _send_error(websocket, f"Workflow error: {str(e)}", phase=2)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await _send_error(websocket, str(e))
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/ws/phase3")
async def websocket_phase3(websocket: WebSocket):
    """
    WebSocket endpoint for Phase 3: Find connections between key concepts.

    Protocol:
    1. Client connects and sends JSON: {"key_concepts": [...]}
    2. Server streams workflow events and outputs connections + synthesis
    """
    await websocket.accept()

    try:
        initial_text = await websocket.receive_text()
        request_data = json.loads(initial_text)

        key_concepts = request_data.get("key_concepts") if isinstance(request_data, dict) else None
        
        if not key_concepts:
            await _send_error(websocket, "key_concepts is required")
            await websocket.close(code=1008, reason="key_concepts required")
            return

        logger.info("🔗 Starting Phase 3")

        await websocket.send_json({
            "type": "phase_started",
            "phase": 3,
            "message": "Finding connections between concepts...",
            "timestamp": _timestamp(),
        })

        def process_output(output):
            if isinstance(output, ConnectionsResponse):
                return output.model_dump()
            return output

        try:
            with get_tracer().start_as_current_span(
                "Phase 3: Connections", kind=SpanKind.INTERNAL
            ) as span:
                span.set_attribute("concepts.count", len(key_concepts))
                
                workflow_output = await _stream_workflow_events(
                    websocket=websocket,
                    workflow=connections_workflow,
                    input_data=json.dumps({"key_concepts": key_concepts}),
                    phase=3,
                    output_processor=process_output,
                )

                if workflow_output:
                    span.set_attribute("connections.count", len(workflow_output.get("connections", [])))

            await websocket.send_json({
                "type": "phase_completed",
                "phase": 3,
                "message": "Connections ready",
                "output": workflow_output,
                "timestamp": _timestamp(),
            })
            logger.info("✅ Phase 3 completed")

        except Exception as e:
            logger.error(f"❌ Phase 3 error: {e}")
            await _send_error(websocket, f"Workflow error: {str(e)}", phase=3)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await _send_error(websocket, str(e))
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/ws/phase4")
async def websocket_phase4(websocket: WebSocket):
    """
    WebSocket endpoint for Phase 4: Verify claims made in the video.

    Protocol:
    1. Client connects and sends JSON: {"thesis": "...", "argument_chains": [...], "claims": [...]}
    2. Server streams workflow events and outputs verification results
    """
    await websocket.accept()

    try:
        initial_text = await websocket.receive_text()
        request_data = json.loads(initial_text)

        thesis = request_data.get("thesis") if isinstance(request_data, dict) else None
        argument_chains = request_data.get("argument_chains", []) if isinstance(request_data, dict) else []
        claims = request_data.get("claims", []) if isinstance(request_data, dict) else []
        
        if not thesis and not argument_chains and not claims:
            await _send_error(websocket, "At least one of thesis, argument_chains, or claims is required")
            await websocket.close(code=1008, reason="No content to verify")
            return

        logger.info("🔍 Starting Phase 4")

        await websocket.send_json({
            "type": "phase_started",
            "phase": 4,
            "message": "Verifying claims...",
            "timestamp": _timestamp(),
        })

        def process_output(output):
            if isinstance(output, ClaimVerifierResponse):
                return output.model_dump()
            return output

        try:
            with get_tracer().start_as_current_span(
                "Phase 4: Claim Verification", kind=SpanKind.INTERNAL
            ) as span:
                span.set_attribute("claims.count", len(claims))
                span.set_attribute("argument_chains.count", len(argument_chains))
                
                workflow_output = await _stream_workflow_events(
                    websocket=websocket,
                    workflow=claim_verifier_workflow,
                    input_data=json.dumps({
                        "thesis": thesis,
                        "argument_chains": argument_chains,
                        "claims": claims,
                    }),
                    phase=4,
                    output_processor=process_output,
                )

                if workflow_output:
                    span.set_attribute("verified_claims.count", len(workflow_output.get("verified_claims", [])))

            await websocket.send_json({
                "type": "phase_completed",
                "phase": 4,
                "message": "Claim verification complete",
                "output": workflow_output,
                "timestamp": _timestamp(),
            })
            logger.info("✅ Phase 4 completed")

        except Exception as e:
            logger.error(f"❌ Phase 4 error: {e}")
            await _send_error(websocket, f"Workflow error: {str(e)}", phase=4)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        with contextlib.suppress(Exception):
            await _send_error(websocket, str(e))
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


# Root endpoint
@router.get("/", response_class=fastapi.responses.HTMLResponse)
async def root():
    """Root endpoint."""
    logger.info("Root endpoint called")
    return """
    <html>
        <head><title>YouTube Reviewer API</title></head>
        <body>
            <h1>YouTube Reviewer API</h1>
            <p>API service is running.</p>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><strong>WS /ws/phase1</strong> - Phase 1: Extract key concepts</li>
                <li><strong>WS /ws/phase2</strong> - Phase 2: Extract thesis and arguments</li>
                <li><strong>WS /ws/phase3</strong> - Phase 3: Find connections</li>
                <li><strong>WS /ws/phase4</strong> - Phase 4: Verify claims</li>
            </ul>
        </body>
    </html>
    """
