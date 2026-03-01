from unittest.mock import MagicMock, call

import numpy as np
import pytest

from supabase_writer import write_influence_scores, BATCH_SIZE


class TestWriteInfluenceScores:
    def _make_mock_client(self):
        client = MagicMock()
        table = MagicMock()
        upsert = MagicMock()
        execute = MagicMock()

        client.table.return_value = table
        table.upsert.return_value = upsert
        upsert.execute.return_value = MagicMock(data=[])

        return client

    def test_basic_upsert(self):
        client = self._make_mock_client()

        tracin = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        datainf = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        train_map = {0: "train-uuid-0", 1: "train-uuid-1"}
        eval_map = {0: "eval-uuid-0", 1: "eval-uuid-1"}

        n = write_influence_scores(client, "job-1", tracin, datainf, train_map, eval_map)

        assert n == 4  # 2 train x 2 eval
        client.table.assert_called_with("influence_scores")

        # Check the upsert was called with correct data
        upsert_call = client.table().upsert.call_args
        rows = upsert_call[0][0]
        assert len(rows) == 4
        assert rows[0]["job_id"] == "job-1"
        assert rows[0]["train_id"] == "train-uuid-0"
        assert rows[0]["eval_id"] == "eval-uuid-0"
        assert rows[0]["tracin_score"] == pytest.approx(1.0)
        assert rows[0]["datainf_score"] == pytest.approx(0.1)

    def test_on_conflict_parameter(self):
        client = self._make_mock_client()

        tracin = np.array([[1.0]], dtype=np.float32)
        datainf = np.array([[0.1]], dtype=np.float32)

        write_influence_scores(client, "job-1", tracin, datainf, {0: "t0"}, {0: "e0"})

        upsert_call = client.table().upsert.call_args
        assert upsert_call[1]["on_conflict"] == "job_id,train_id,eval_id"

    def test_batch_chunking(self):
        """Verify rows are chunked at BATCH_SIZE=500."""
        client = self._make_mock_client()

        # Create 600 train x 1 eval = 600 rows → should be 2 batches
        n_train = 600
        tracin = np.ones((n_train, 1), dtype=np.float32)
        datainf = np.ones((n_train, 1), dtype=np.float32)
        train_map = {i: f"t-{i}" for i in range(n_train)}
        eval_map = {0: "e-0"}

        n = write_influence_scores(client, "job-1", tracin, datainf, train_map, eval_map)

        assert n == 600
        # Should have been called twice: 500 + 100
        assert client.table().upsert.call_count == 2
        first_chunk = client.table().upsert.call_args_list[0][0][0]
        second_chunk = client.table().upsert.call_args_list[1][0][0]
        assert len(first_chunk) == 500
        assert len(second_chunk) == 100

    def test_float_conversion(self):
        """Scores should be Python floats, not numpy types."""
        client = self._make_mock_client()

        tracin = np.array([[np.float32(1.5)]], dtype=np.float32)
        datainf = np.array([[np.float64(2.5)]], dtype=np.float32)

        write_influence_scores(client, "job-1", tracin, datainf, {0: "t0"}, {0: "e0"})

        rows = client.table().upsert.call_args[0][0]
        assert isinstance(rows[0]["tracin_score"], float)
        assert isinstance(rows[0]["datainf_score"], float)
