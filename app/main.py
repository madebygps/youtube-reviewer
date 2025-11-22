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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router as api_router
import telemetry


# Configure logging (will be enhanced with OpenTelemetry during startup)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    lifespan=lifespan,
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


app.include_router(api_router)


# Serve static files directly from root, if the "static" directory exists
if os.path.exists("static"):
    app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory="static", html=True),
        name="static",
    )
