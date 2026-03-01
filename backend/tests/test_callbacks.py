"""Unit tests for the webhook callback endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import TEST_JOB_ID, make_job_row


# ============================================================
# POST /api/v1/callbacks/job-update
# ============================================================


class TestJobUpdateCallback:
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    def test_valid_status_update(self, mock_update, client, mock_db):
        # Mock the direct client.table() call in the callback route
        mock_result = MagicMock()
        mock_result.data = {"id": TEST_JOB_ID, "status": "provisioning"}
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "training",
                "progress": 0.1,
            },
        )

        assert resp.status_code == 200
        assert "training" in resp.json()["message"]
        mock_update.assert_called_once()
        update_kwargs = mock_update.call_args.kwargs
        assert update_kwargs["status"] == "training"

    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    def test_backward_transition_ignored(self, mock_update, client, mock_db):
        # Job is already in "training", callback tries to set "provisioning"
        mock_result = MagicMock()
        mock_result.data = {"id": TEST_JOB_ID, "status": "training"}
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "provisioning",
                "progress": 0.0,
            },
        )

        assert resp.status_code == 200
        assert "ignored" in resp.json()["message"].lower()
        mock_update.assert_not_called()

    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    def test_failed_always_accepted(self, mock_update, client, mock_db):
        # Even if job is "completed", "failed" is always accepted
        mock_result = MagicMock()
        mock_result.data = {"id": TEST_JOB_ID, "status": "completed"}
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "failed",
                "progress": 0.0,
                "status_message": "OOM error",
            },
        )

        assert resp.status_code == 200
        mock_update.assert_called_once()
        assert mock_update.call_args.kwargs["status"] == "failed"

    def test_nonexistent_job(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.data = None
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "training",
            },
        )

        assert resp.status_code == 404

    def test_invalid_status_value(self, client):
        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "bogus",
            },
        )
        assert resp.status_code == 422  # Pydantic validation

    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    def test_completed_sets_progress_to_one(self, mock_update, client, mock_db):
        mock_result = MagicMock()
        mock_result.data = {"id": TEST_JOB_ID, "status": "computing_datainf"}
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "completed",
                "progress": 0.9,  # Even if caller says 0.9, should be overridden to 1.0
            },
        )

        assert resp.status_code == 200
        assert mock_update.call_args.kwargs["progress"] == 1.0

    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    def test_training_sets_started_at(self, mock_update, client, mock_db):
        mock_result = MagicMock()
        mock_result.data = {"id": TEST_JOB_ID, "status": "provisioning"}
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/callbacks/job-update",
            json={
                "job_id": TEST_JOB_ID,
                "status": "training",
                "progress": 0.0,
            },
        )

        assert resp.status_code == 200
        assert "started_at" in mock_update.call_args.kwargs
