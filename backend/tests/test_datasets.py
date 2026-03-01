"""Unit tests for the dataset upload URL endpoint."""

from unittest.mock import AsyncMock, patch


class TestGetUploadUrl:
    @patch("app.services.supabase_client.create_signed_upload_url", new_callable=AsyncMock)
    def test_valid_filename(self, mock_sign, client):
        mock_sign.return_value = ("https://signed.url/upload", "user/uuid/data.jsonl")

        resp = client.post(
            "/api/v1/datasets/upload-url",
            params={"filename": "training_data.jsonl"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["upload_url"] == "https://signed.url/upload"
        assert data["storage_path"] == "user/uuid/data.jsonl"

    def test_invalid_extension_rejected(self, client):
        resp = client.post(
            "/api/v1/datasets/upload-url",
            params={"filename": "data.csv"},
        )
        assert resp.status_code == 422  # Pattern validation fails

    def test_missing_filename(self, client):
        resp = client.post("/api/v1/datasets/upload-url")
        assert resp.status_code == 422

    def test_empty_filename(self, client):
        resp = client.post(
            "/api/v1/datasets/upload-url",
            params={"filename": ""},
        )
        assert resp.status_code == 422
