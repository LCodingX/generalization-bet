import hashlib
import hmac as hmac_mod
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user, verify_webhook_signature
from app.config import Settings, get_settings
from app.main import app
from app.routes.admin import get_db as admin_get_db
from app.routes.callbacks import get_db as callbacks_get_db
from app.routes.datasets import get_db as datasets_get_db
from app.routes.jobs import get_db as jobs_get_db


# ============================================================
# Constants
# ============================================================

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_JOB_ID = "22222222-2222-2222-2222-222222222222"
TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests-32b+"
TEST_WEBHOOK_SECRET = "a" * 64


# ============================================================
# Settings
# ============================================================


@pytest.fixture()
def test_settings() -> Settings:
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


# ============================================================
# Mock Supabase Client
# ============================================================


@pytest.fixture()
def mock_db():
    """A MagicMock standing in for the Supabase Client."""
    client = MagicMock()
    # Storage mock chain
    storage_bucket = MagicMock()
    client.storage.from_.return_value = storage_bucket
    storage_bucket.upload.return_value = None
    storage_bucket.remove.return_value = None
    storage_bucket.create_signed_upload_url.return_value = {
        "signed_url": "https://test.supabase.co/upload/signed",
    }
    storage_bucket.create_signed_url.return_value = {
        "signedURL": "https://test.supabase.co/download/signed",
    }
    return client


# ============================================================
# Fake authenticated user
# ============================================================


@pytest.fixture()
def fake_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=TEST_USER_ID, email="test@example.com")


# ============================================================
# TestClient with dependency overrides
# ============================================================


@pytest.fixture()
def client(test_settings, mock_db, fake_user):
    """
    FastAPI TestClient with all external dependencies replaced.
    """

    def override_settings():
        return test_settings

    def override_user():
        return fake_user

    def override_db():
        return mock_db

    async def override_webhook():
        return None

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[verify_webhook_signature] = override_webhook
    app.dependency_overrides[jobs_get_db] = override_db
    app.dependency_overrides[callbacks_get_db] = override_db
    app.dependency_overrides[datasets_get_db] = override_db
    app.dependency_overrides[admin_get_db] = override_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ============================================================
# Helpers
# ============================================================


def make_job_row(
    *,
    job_id: str = TEST_JOB_ID,
    user_id: str = TEST_USER_ID,
    status: str = "queued",
    progress: float = 0.0,
    model_name: str = "meta-llama/Llama-2-7b-hf",
    modal_call_id: str | None = None,
    dataset_storage_path: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": job_id,
        "user_id": user_id,
        "status": status,
        "status_message": None,
        "progress": progress,
        "model_name": model_name,
        "hyperparameters": {},
        "dataset_storage_path": dataset_storage_path,
        "modal_call_id": modal_call_id,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }


def make_create_job_body(**overrides) -> dict:
    body = {
        "model_name": "meta-llama/Llama-2-7b-hf",
        "training_pairs": [
            {"prompt": "What is 2+2?", "completion": "4", "category": "math"},
        ],
        "eval_examples": [
            {"question": "What is 3+3?", "completion": "6"},
        ],
    }
    body.update(overrides)
    return body


def sign_webhook_payload(payload: dict, secret: str = TEST_WEBHOOK_SECRET) -> str:
    body = json.dumps(payload).encode()
    sig = hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"hmac-sha256={sig}"


def make_jwt(
    sub: str = TEST_USER_ID,
    email: str = "test@example.com",
    secret: str = TEST_JWT_SECRET,
) -> str:
    return jwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated"},
        secret,
        algorithm="HS256",
    )
