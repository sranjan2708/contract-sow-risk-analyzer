"""
Main FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.routes import health, mock

settings = get_settings()

app = FastAPI(
    title="Contract & SOW Risk Analyzer API",
    version="1.0.0",
    description="Automated legal playbook risk analysis, dependency graphing, and MSA-vs-SOW contradiction detection.",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Health router is always included
app.include_router(health.router)

# ---------------------------------------------------------------------------
# REAL routers go HERE, above the mock router — FastAPI uses the first matching
# route, so real routes replace mock ones path by path
# ---------------------------------------------------------------------------
# Example when implementing real auth/documents:
# app.include_router(auth.router)
# app.include_router(documents.router)
# ---------------------------------------------------------------------------

# 2. Mock router is conditionally included in mock mode
if settings.MOCK_MODE:
    app.include_router(mock.router)
