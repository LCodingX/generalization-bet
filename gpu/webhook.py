import hashlib
import hmac
import json
import logging

import httpx

logger = logging.getLogger(__name__)


class WebhookClient:
    """Sends HMAC-SHA256-signed status updates to the backend callback URL.

    Signature format matches backend verification at backend/app/auth.py:58-81.
    Failures are non-fatal — the backend has stale job recovery.
    """

    def __init__(self, callback_url: str, webhook_secret: str, job_id: str):
        self.callback_url = callback_url
        self.webhook_secret = webhook_secret
        self.job_id = job_id

    def send(
        self,
        status: str,
        progress: float = 0.0,
        message: str | None = None,
    ) -> bool:
        """POST a signed status update. Returns True on success, False on failure."""
        progress = max(0.0, min(1.0, progress))

        payload = {
            "job_id": self.job_id,
            "status": status,
            "progress": progress,
        }
        if message is not None:
            payload["status_message"] = message

        body = json.dumps(payload)
        signature = hmac.new(
            self.webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        try:
            resp = httpx.post(
                self.callback_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": f"hmac-sha256={signature}",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            logger.info(f"Webhook sent: {status} progress={progress:.2f}")
            return True
        except Exception as e:
            logger.warning(f"Webhook failed (non-fatal): {e}")
            return False
