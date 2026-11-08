"""
FastAPI authentication and dependency injection layer.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app import repository
from backend.app.security import decode_access_token
from shared.contracts import UserOut

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> UserOut:
    """
    Authenticate request via Bearer JWT token and return current UserOut.

    Args:
        credentials: Optional Bearer authorization credentials.

    Raises:
        HTTPException: 401 Unauthorized if token is missing, invalid, or user does not exist.

    Returns:
        UserOut: Validated user contract model.
    """
    if credentials is None or not credentials.credentials:
        logger.debug("Authentication failed: Missing bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        logger.warning("Authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repository.get_user_by_id(user_id)
    if user is None:
        logger.warning("Authentication failed: User %d not found in repository", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserOut(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
    )

