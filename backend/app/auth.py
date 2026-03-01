import hmac
import hashlib
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import Settings, get_settings


class AuthenticatedUser(BaseModel):
    """Extracted from a verified Supabase JWT."""
    user_id: str
    email: str | None = None


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """
    Verify the Supabase JWT from the Authorization header.
    Supabase JWTs use HS256 signed with the project's JWT secret.
    The user_id lives in the 'sub' claim.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing 'sub' claim")

    return AuthenticatedUser(
        user_id=sub,
        email=payload.get("email"),
    )


async def verify_webhook_signature(
    request: Request,
    x_webhook_signature: Annotated[str, Header()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """
    Verify HMAC-SHA256 signature on webhook callbacks from the Modal container.
    The container signs the raw request body with the shared WEBHOOK_SECRET.
    Header format: hmac-sha256=<hex_digest>
    """
    if not x_webhook_signature.startswith("hmac-sha256="):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed signature header")

    provided_sig = x_webhook_signature.removeprefix("hmac-sha256=")
    body = await request.body()

    expected_sig = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
