"""Unit tests for JWT (JWKS/RS256) and HMAC authentication."""

import hashlib
import hmac as hmac_mod
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user, verify_webhook_signature
from app.config import get_settings

from tests.conftest import TEST_USER_ID, TEST_WEBHOOK_SECRET


# ============================================================
# RSA key pair for test JWT signing (simulates Supabase JWKS)
# ============================================================

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()


def _make_token(sub=TEST_USER_ID, email="test@example.com", exp_offset=3600, **extra):
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "exp": int(time.time()) + exp_offset,
        **extra,
    }
    return jwt.encode(payload, _private_key, algorithm="RS256", headers={"kid": "test-kid"})


def _mock_jwks_signing_key():
    """Create a mock signing key that returns our test public key."""
    mock_key = MagicMock()
    mock_key.key = _public_key
    return mock_key


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


def _test_settings():
    from app.config import Settings

    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        supabase_secret_key="sb_secret_test",
        modal_token_id="ak-test",
        modal_token_secret="as-test",
        webhook_secret=TEST_WEBHOOK_SECRET,
        callback_base_url="https://test.railway.app",
        hf_token="hf_test",
    )


auth_app.dependency_overrides[get_settings] = _test_settings
auth_client = TestClient(auth_app)


# ============================================================
# JWT Tests
# ============================================================


class TestJWTAuth:
    @patch("app.auth._get_jwks_client")
    def test_valid_token(self, mock_get_jwks):
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = _mock_jwks_signing_key()
        mock_get_jwks.return_value = mock_client

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

    @patch("app.auth._get_jwks_client")
    def test_expired_token(self, mock_get_jwks):
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = _mock_jwks_signing_key()
        mock_get_jwks.return_value = mock_client

        token = _make_token(exp_offset=-3600)
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    @patch("app.auth._get_jwks_client")
    def test_wrong_key(self, mock_get_jwks):
        """Token signed with a different key should fail verification."""
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
            other_key,
            algorithm="RS256",
            headers={"kid": "other-kid"},
        )

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = _mock_jwks_signing_key()
        mock_get_jwks.return_value = mock_client

        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @patch("app.auth._get_jwks_client")
    def test_missing_sub_claim(self, mock_get_jwks):
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = _mock_jwks_signing_key()
        mock_get_jwks.return_value = mock_client

        token = jwt.encode(
            {"email": "test@example.com", "aud": "authenticated", "exp": int(time.time()) + 3600},
            _private_key,
            algorithm="RS256",
            headers={"kid": "test-kid"},
        )
        resp = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "sub" in resp.json()["detail"]

    @patch("app.auth._get_jwks_client")
    def test_wrong_audience(self, mock_get_jwks):
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = _mock_jwks_signing_key()
        mock_get_jwks.return_value = mock_client

        token = jwt.encode(
            {"sub": TEST_USER_ID, "aud": "wrong-audience", "exp": int(time.time()) + 3600},
            _private_key,
            algorithm="RS256",
            headers={"kid": "test-kid"},
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
