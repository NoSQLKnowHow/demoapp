"""
HTTP Basic Authentication for the Prism API.

All endpoints require valid credentials. Credentials are configured
via environment variables (PRISM_AUTH_USERNAME, PRISM_AUTH_PASSWORD).
"""

import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic()


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency that verifies HTTP Basic Auth credentials.
    Returns the authenticated username.

    Uses secrets.compare_digest to prevent timing attacks.
    """
    username_correct = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.auth_username.encode("utf-8"),
    )
    password_correct = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.auth_password.encode("utf-8"),
    )

    if not (username_correct and password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
