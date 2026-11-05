"""
Health check route.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.config import get_settings
from shared.contracts import CONTRACT_VERSION

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
def health_check() -> dict:
    """Return health status, current mock mode flag, and frozen contract version."""
    settings = get_settings()
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_MODE,
        "contract_version": CONTRACT_VERSION,
    }
