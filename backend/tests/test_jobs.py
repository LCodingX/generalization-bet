"""Unit tests for job CRUD and score endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tests.conftest import TEST_JOB_ID, TEST_USER_ID, make_create_job_body, make_job_row


# ============================================================
# POST /api/v1/jobs — Create Job
# ============================================================


class TestCreateJob:
    @patch("app.services.modal_dispatch.dispatch_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_signed_download_url", new_callable=AsyncMock)
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.insert_eval_examples", new_callable=AsyncMock)
    @patch("app.services.supabase_client.insert_training_examples", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_job", new_callable=AsyncMock)
    def test_create_with_inline_data(
        self, mock_create, mock_insert_train, mock_insert_eval,
        mock_update, mock_sign_url, mock_dispatch, client
    ):
        mock_create.return_value = make_job_row()
        mock_sign_url.return_value = "https://signed.url"
        mock_dispatch.return_value = "modal-call-id-123"

        resp = client.post("/api/v1/jobs", json=make_create_job_body())

        assert resp.status_code == 201
        data = resp.json()
        assert data["job_id"] == TEST_JOB_ID
        assert data["status"] == "provisioning"
        mock_create.assert_called_once()
        mock_insert_train.assert_called_once()
        mock_insert_eval.assert_called_once()
        mock_dispatch.assert_called_once()

    @patch("app.services.modal_dispatch.dispatch_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_signed_download_url", new_callable=AsyncMock)
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.insert_eval_examples", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_job", new_callable=AsyncMock)
    def test_create_with_file_path(
        self, mock_create, mock_insert_eval, mock_update,
        mock_sign_url, mock_dispatch, client
    ):
        mock_create.return_value = make_job_row()
        mock_sign_url.return_value = "https://signed.url"
        mock_dispatch.return_value = "modal-call-id-123"

        body = make_create_job_body(
            training_pairs=None,
            dataset_file_path="user/job/data.jsonl",
        )
        resp = client.post("/api/v1/jobs", json=body)

        assert resp.status_code == 201

    def test_create_missing_both_sources(self, client):
        body = make_create_job_body(training_pairs=None, dataset_file_path=None)
        resp = client.post("/api/v1/jobs", json=body)
        assert resp.status_code == 400
        assert "Provide either" in resp.json()["detail"]

    @patch("app.services.supabase_client.create_job", new_callable=AsyncMock)
    def test_create_both_sources_rejected(self, mock_create, client):
        body = make_create_job_body(dataset_file_path="user/job/data.jsonl")
        resp = client.post("/api/v1/jobs", json=body)
        assert resp.status_code == 400
        assert "not both" in resp.json()["detail"]

    def test_create_empty_eval_rejected(self, client):
        body = make_create_job_body(eval_examples=[])
        resp = client.post("/api/v1/jobs", json=body)
        assert resp.status_code == 422  # Pydantic validation

    @patch("app.services.modal_dispatch.dispatch_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_signed_download_url", new_callable=AsyncMock)
    @patch("app.services.supabase_client.update_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.insert_eval_examples", new_callable=AsyncMock)
    @patch("app.services.supabase_client.insert_training_examples", new_callable=AsyncMock)
    @patch("app.services.supabase_client.create_job", new_callable=AsyncMock)
    def test_create_modal_failure_marks_job_failed(
        self, mock_create, mock_insert_train, mock_insert_eval,
        mock_update, mock_sign_url, mock_dispatch, client
    ):
        mock_create.return_value = make_job_row()
        mock_sign_url.return_value = "https://signed.url"
        mock_dispatch.side_effect = Exception("Modal down")

        resp = client.post("/api/v1/jobs", json=make_create_job_body())

        assert resp.status_code == 502
        # Verify the job was marked as failed
        calls = mock_update.call_args_list
        failed_call = [c for c in calls if c.kwargs.get("status") == "failed"]
        assert len(failed_call) == 1


# ============================================================
# GET /api/v1/jobs — List Jobs
# ============================================================


class TestListJobs:
    @patch("app.services.supabase_client.get_jobs_for_user", new_callable=AsyncMock)
    def test_list_jobs(self, mock_list, client):
        mock_list.return_value = [make_job_row(), make_job_row(job_id=str(uuid4()))]
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("app.services.supabase_client.get_jobs_for_user", new_callable=AsyncMock)
    def test_list_jobs_empty(self, mock_list, client):
        mock_list.return_value = []
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("app.services.supabase_client.get_jobs_for_user", new_callable=AsyncMock)
    def test_list_jobs_with_status_filter(self, mock_list, client):
        mock_list.return_value = [make_job_row(status="completed")]
        resp = client.get("/api/v1/jobs", params={"status": "completed"})
        assert resp.status_code == 200
        mock_list.assert_called_once()
        assert mock_list.call_args.kwargs["status_filter"] == "completed"


# ============================================================
# GET /api/v1/jobs/{job_id} — Get Job
# ============================================================


class TestGetJob:
    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_existing_job(self, mock_get, client):
        mock_get.return_value = make_job_row()
        resp = client.get(f"/api/v1/jobs/{TEST_JOB_ID}")
        assert resp.status_code == 200
        assert resp.json()["id"] == TEST_JOB_ID

    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_nonexistent_job(self, mock_get, client):
        mock_get.return_value = None
        resp = client.get(f"/api/v1/jobs/{TEST_JOB_ID}")
        assert resp.status_code == 404


# ============================================================
# GET /api/v1/jobs/{job_id}/scores — Get Scores
# ============================================================


class TestGetScores:
    @patch("app.services.supabase_client.get_influence_scores", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_scores_completed_job(self, mock_get_job, mock_get_scores, client):
        mock_get_job.return_value = make_job_row(status="completed")
        train_id = str(uuid4())
        eval_id = str(uuid4())
        mock_get_scores.return_value = (
            [
                {
                    "train_id": train_id,
                    "eval_id": eval_id,
                    "tracin_score": 0.85,
                    "datainf_score": -0.12,
                    "training_examples": {"index": 0, "category": "math", "prompt": "Q"},
                    "eval_examples": {"index": 0, "question": "Q?"},
                },
            ],
            1,
        )

        resp = client.get(f"/api/v1/jobs/{TEST_JOB_ID}/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["scores"]) == 1
        assert data["scores"][0]["tracin_score"] == 0.85
        assert data["scores"][0]["datainf_score"] == -0.12
        assert data["scores"][0]["train_category"] == "math"

    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_scores_incomplete_job(self, mock_get_job, client):
        mock_get_job.return_value = make_job_row(status="training")
        resp = client.get(f"/api/v1/jobs/{TEST_JOB_ID}/scores")
        assert resp.status_code == 409
        assert "not completed" in resp.json()["detail"]

    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_scores_nonexistent_job(self, mock_get_job, client):
        mock_get_job.return_value = None
        resp = client.get(f"/api/v1/jobs/{TEST_JOB_ID}/scores")
        assert resp.status_code == 404

    @patch("app.services.supabase_client.get_influence_scores", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_get_scores_with_category_filter(self, mock_get_job, mock_get_scores, client):
        mock_get_job.return_value = make_job_row(status="completed")
        mock_get_scores.return_value = ([], 0)

        resp = client.get(
            f"/api/v1/jobs/{TEST_JOB_ID}/scores",
            params={"category": "math", "sort_by": "datainf_score", "order": "asc"},
        )
        assert resp.status_code == 200
        mock_get_scores.assert_called_once()
        assert mock_get_scores.call_args.kwargs["category"] == "math"
        assert mock_get_scores.call_args.kwargs["sort_by"] == "datainf_score"
        assert mock_get_scores.call_args.kwargs["order"] == "asc"


# ============================================================
# DELETE /api/v1/jobs/{job_id} — Delete Job
# ============================================================


class TestDeleteJob:
    @patch("app.services.modal_dispatch.cancel_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.delete_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_delete_completed_job(self, mock_get, mock_delete, mock_cancel, client):
        mock_get.return_value = make_job_row(status="completed")
        mock_delete.return_value = True

        resp = client.delete(f"/api/v1/jobs/{TEST_JOB_ID}")
        assert resp.status_code == 200
        assert TEST_JOB_ID in resp.json()["message"]
        mock_cancel.assert_not_called()  # Completed jobs don't need cancelling

    @patch("app.services.modal_dispatch.cancel_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.delete_job", new_callable=AsyncMock)
    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_delete_running_job_cancels_modal(self, mock_get, mock_delete, mock_cancel, client):
        mock_get.return_value = make_job_row(
            status="training",
            modal_call_id="modal-call-123",
        )
        mock_delete.return_value = True

        resp = client.delete(f"/api/v1/jobs/{TEST_JOB_ID}")
        assert resp.status_code == 200
        mock_cancel.assert_called_once_with("modal-call-123")

    @patch("app.services.supabase_client.get_job", new_callable=AsyncMock)
    def test_delete_nonexistent_job(self, mock_get, client):
        mock_get.return_value = None
        resp = client.delete(f"/api/v1/jobs/{TEST_JOB_ID}")
        assert resp.status_code == 404
