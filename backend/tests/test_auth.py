"""Unit tests for JWT and HMAC authentication."""

import hashlib
import hmac as hmac_mod
import time

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user, verify_webhook_signature
from app.config import get_settings

from tests.conftest import TEST_JWT_SECRET, TEST_USER_ID, TEST_WEBHOOK_SECRET


# ============================================================
# Build a small test app with the real auth dependencies
# (no overrides — we're testing the auth logic itself)
# ============================================================

auth_app = FastAPI()


@auth_app.get("/protected")
async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
    return {"user_id": user.user_id, "email": user.email}


@auth_app.post("/webhook", dependencies=[Depends(verify_webhook_signature)])
async def webhook_route():
    return {"ok": True}


# Override only settings so it doesn't read real .env
def _test_settings():
    from app.config import Settings

    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_service_key="test-service-key",
        supabase_jwt_secret=TEST_JWT_SECRET,
        modal_token_id="ak-test",
        modal_token_secret="as-test",
        webhook_secret=TEST_WEBHOOK_SECRET,
        callback_base_url="https://test.railway.app",
        hf_token="hf_test",
    )


auth_app.dependency_overrides[get_settings] = _test_settings
auth_client = TestClient(auth_app)


def _make_token(sub=TEST_USER_ID, email="test@example.com", exp_offset=3600, **extra):
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "exp": int(time.time()) + exp_offset,
        **extra,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


# ============================================================
# JWT Tests
# ============================================================


class TestJWTAuth:
    def test_valid_token(self):
        token = _make_token()
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == TEST_USER_ID
        assert data["email"] == "test@example.com"

    def test_missing_auth_header(self):
        resp = auth_client.get("/protected")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    def test_malformed_auth_header(self):
        resp = auth_client.get("/protected", headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    def test_expired_token(self):
        token = _make_token(exp_offset=-3600)
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_wrong_secret(self):
        token = jwt.encode(
            {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_missing_sub_claim(self):
        token = jwt.encode(
            {"email": "test@example.com", "aud": "authenticated", "exp": int(time.time()) + 3600},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "sub" in resp.json()["detail"]

    def test_wrong_audience(self):
        token = jwt.encode(
            {"sub": TEST_USER_ID, "aud": "wrong-audience", "exp": int(time.time()) + 3600},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ============================================================
# HMAC Webhook Tests
# ============================================================


class TestWebhookHMAC:
    def _sign(self, body: bytes, secret: str = TEST_WEBHOOK_SECRET) -> str:
        sig = hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return f"hmac-sha256={sig}"

    def test_valid_signature(self):
        body = b'{"job_id": "test", "status": "training"}'
        sig = self._sign(body)
        resp = auth_client.post(
            "/webhook",
            content=body,
            headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200

    def test_invalid_signature(self):
        body = b'{"job_id": "test"}'
        resp = auth_client.post(
            "/webhook",
            content=body,
            headers={
                "X-Webhook-Signature": "hmac-sha256=badbadbadbad",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    def test_malformed_signature_header(self):
        body = b'{"job_id": "test"}'
        resp = auth_client.post(
            "/webhook",
            content=body,
            headers={
                "X-Webhook-Signature": "not-hmac-format",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert "Malformed" in resp.json()["detail"]

    def test_missing_signature_header(self):
        body = b'{"job_id": "test"}'
        resp = auth_client.post("/webhook", content=body)
        assert resp.status_code == 422  # FastAPI returns 422 for missing required header

    def test_wrong_secret(self):
        body = b'{"job_id": "test"}'
        sig = self._sign(body, secret="wrong-secret-that-is-definitely-wrong")
        resp = auth_client.post(
            "/webhook",
            content=body,
            headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 401
