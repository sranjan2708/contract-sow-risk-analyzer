"""
Main FastAPI application entry point.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.routes import auth, health, mock

logger = logging.getLogger(__name__)


def create_app(mock_mode: Optional[bool] = None) -> FastAPI:
    """
    Factory function to initialize and configure the FastAPI application.

    Args:
        mock_mode: Whether to enable mock mode routes. If None, defaults to
                   settings.MOCK_MODE.

    Returns:
        FastAPI application instance configured with CORS, health check,
        and either mock routes or real auth routes.
    """
    settings = get_settings()
    is_mock = settings.MOCK_MODE if mock_mode is None else mock_mode

    application = FastAPI(
        title="Contract & SOW Risk Analyzer API",
        version="1.0.0",
        description="Automated legal playbook risk analysis, dependency graphing, and MSA-vs-SOW contradiction detection.",
    )

    # Configure CORS (Always included)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Health router is always included
    application.include_router(health.router)

    # 2. Real auth or mock router based on mock_mode
    if is_mock:
        application.include_router(mock.router)
    else:
        application.include_router(auth.router)

    return application


app = create_app()
