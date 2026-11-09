"""
Authentication API routes.
Implements user registration, login, and profile retrieval (Contract 3, Endpoints 2-4).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app import repository
from backend.app.deps import get_current_user
from backend.app.security import create_access_token, hash_password, verify_password
from shared.contracts import TokenResponse, UserLogin, UserOut, UserRegister

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Auth"])


@router.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(payload: UserRegister) -> UserOut:
    """
    Register a new user account.

    Args:
        payload: Validated UserRegister request containing email, password, and full_name.

    Raises:
        HTTPException: 409 Conflict if email is already registered.

    Returns:
        UserOut: Created user profile.
    """
    existing_user = repository.get_user_by_email(payload.email)
    if existing_user is not None:
        logger.warning("Registration conflict: email '%s' already exists", payload.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    pwd_hash = hash_password(payload.password)
    user_id = repository.create_user(
        email=payload.email,
        password_hash=pwd_hash,
        full_name=payload.full_name,
    )
    return UserOut(
        user_id=user_id,
        email=payload.email,
        full_name=payload.full_name,
    )


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and retrieve a bearer access token",
)
def login(payload: UserLogin) -> TokenResponse:
    """
    Authenticate user credentials and issue a signed JWT access token.

    Args:
        payload: Validated UserLogin request containing email and password.

    Raises:
        HTTPException: 401 Unauthorized if email is unknown or password does not match.

    Returns:
        TokenResponse: Access token and token type.
    """
    user = repository.get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        logger.warning("Failed login attempt for email: %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user["user_id"])
    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )


@router.get(
    "/auth/me",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated user profile",
)
def get_me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    """
    Retrieve profile details for the currently authenticated user.

    Args:
        current_user: UserOut resolved from Bearer JWT by get_current_user dependency.

    Returns:
        UserOut: Current user profile details.
    """
    return current_user

