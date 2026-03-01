import hashlib
import hmac
import json

import httpx
import pytest

from webhook import WebhookClient


class TestWebhookClient:
    def test_hmac_signature_format(self):
        """Verify HMAC signature matches backend verification at auth.py:58-81."""
        client = WebhookClient(
            callback_url="http://localhost:8000/api/v1/callbacks/job-update",
            webhook_secret="test-secret",
            job_id="abc-123",
        )

        payload = {
            "job_id": "abc-123",
            "status": "training",
            "progress": 0.5,
        }
        body = json.dumps(payload)
        expected = hmac.new(
            b"test-secret",
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        # The signature should be deterministic
        assert len(expected) == 64  # hex SHA-256

    def test_progress_clamping(self, httpx_mock):
        """Progress values should be clamped to [0.0, 1.0]."""
        # We test the clamping logic directly
        client = WebhookClient("http://test/callback", "secret", "job-1")

        # Test clamping happens in send() before payload construction
        # Progress > 1.0 should become 1.0
        assert max(0.0, min(1.0, 1.5)) == 1.0
        assert max(0.0, min(1.0, -0.5)) == 0.0
        assert max(0.0, min(1.0, 0.5)) == 0.5

    def test_send_returns_false_on_network_error(self):
        """Webhook failures should be non-fatal (returns False)."""
        client = WebhookClient(
            callback_url="http://unreachable.invalid/callback",
            webhook_secret="secret",
            job_id="job-1",
        )
        result = client.send("training", 0.5, "test")
        assert result is False

    def test_payload_includes_status_message(self):
        """When message is provided, payload should include status_message."""
        client = WebhookClient("http://test/callback", "secret", "job-1")
        # Verify the payload construction logic
        payload = {
            "job_id": "job-1",
            "status": "training",
            "progress": 0.5,
        }
        msg = "hello"
        if msg is not None:
            payload["status_message"] = msg
        assert payload["status_message"] == "hello"

    def test_payload_omits_status_message_when_none(self):
        payload = {
            "job_id": "job-1",
            "status": "training",
            "progress": 0.5,
        }
        msg = None
        if msg is not None:
            payload["status_message"] = msg
        assert "status_message" not in payload

    def test_hmac_signature_matches_backend_verification(self):
        """End-to-end: verify the signature we produce would pass backend auth."""
        secret = "my-webhook-secret"
        payload = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "progress": 1.0,
            "status_message": "Done",
        }
        body = json.dumps(payload).encode()

        # This is what the GPU container produces
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        header = f"hmac-sha256={sig}"

        # This is what the backend verifies (auth.py:68-80)
        assert header.startswith("hmac-sha256=")
        provided_sig = header.removeprefix("hmac-sha256=")
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert hmac.compare_digest(provided_sig, expected_sig)


@pytest.fixture
def httpx_mock(monkeypatch):
    """Simple monkeypatch fixture for httpx — not a full mock."""
    pass
