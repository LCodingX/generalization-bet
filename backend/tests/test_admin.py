"""Unit tests for admin endpoints (health check, stale job recovery)."""

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import TEST_WEBHOOK_SECRET


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/api/v1/admin/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestStaleJobRecovery:
    @patch("app.services.modal_dispatch.check_job_status", new_callable=AsyncMock)
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_stale_jobs", new_callable=AsyncMock)
    def test_recovers_stale_jobs(self, mock_stale, mock_update, mock_check, client):
        mock_stale.return_value = [
            {"id": "job-1", "modal_call_id": "call-1", "status": "training", "updated_at": "old"},
            {"id": "job-2", "modal_call_id": None, "status": "provisioning", "updated_at": "old"},
        ]
        mock_check.return_value = "failed"

        resp = client.post(
            "/api/v1/admin/recover-stale-jobs",
            headers={"X-Admin-Key": TEST_WEBHOOK_SECRET},
        )

        assert resp.status_code == 200
        assert "2" in resp.json()["message"]  # Recovered 2
        assert mock_update.call_count == 2

    @patch("app.services.supabase_client.get_stale_jobs", new_callable=AsyncMock)
    def test_no_stale_jobs(self, mock_stale, client):
        mock_stale.return_value = []

        resp = client.post(
            "/api/v1/admin/recover-stale-jobs",
            headers={"X-Admin-Key": TEST_WEBHOOK_SECRET},
        )

        assert resp.status_code == 200
        assert "No stale" in resp.json()["message"]

    @patch("app.services.modal_dispatch.check_job_status", new_callable=AsyncMock)
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_stale_jobs", new_callable=AsyncMock)
    def test_still_running_on_modal_skipped(self, mock_stale, mock_update, mock_check, client):
        mock_stale.return_value = [
            {"id": "job-1", "modal_call_id": "call-1", "status": "training", "updated_at": "old"},
        ]
        mock_check.return_value = "running"  # Still alive on Modal

        resp = client.post(
            "/api/v1/admin/recover-stale-jobs",
            headers={"X-Admin-Key": TEST_WEBHOOK_SECRET},
        )

        assert resp.status_code == 200
        assert "0" in resp.json()["message"]  # Recovered 0
        mock_update.assert_not_called()

    def test_invalid_admin_key(self, client):
        resp = client.post(
            "/api/v1/admin/recover-stale-jobs",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_missing_admin_key(self, client):
        resp = client.post("/api/v1/admin/recover-stale-jobs")
        assert resp.status_code == 422  # Missing required header
