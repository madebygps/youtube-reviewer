#!/usr/bin/env python3
"""
FastAPI Backend for YouTube Reviewer
Provides REST API endpoints for generating actionable insights from YouTube videos.
"""

import contextlib
import logging
import os

import fastapi
import fastapi.staticfiles
import opentelemetry.instrumentation.fastapi as otel_fastapi
from agent_framework.observability import setup_observability

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router as api_router


@contextlib.asynccontextmanager
async def lifespan(app):
    # Bridge Aspire's OTEL_EXPORTER_OTLP_ENDPOINT to agent_framework's expected OTLP_ENDPOINT
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    setup_observability(otlp_endpoint=otlp_endpoint)
    
    # Ensure root logger level allows INFO logs to propagate to OTEL handler
    # TODO: Replace with setup_logging() once available in agent-framework PyPI release
    logging.getLogger().setLevel(logging.INFO)
    yield


app = FastAPI(
    title="YouTube Reviewer API",
    description="REST API for generating actionable insights from YouTube videos",
    version="1.0.0",
    lifespan=lifespan,
)
otel_fastapi.FastAPIInstrumentor.instrument_app(app, exclude_spans=["send"])

logger = logging.getLogger(__name__)


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


app.include_router(api_router)


# Serve static files directly from root, if the "static" directory exists
if os.path.exists("static"):
    app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory="static", html=True),
        name="static",
    )
