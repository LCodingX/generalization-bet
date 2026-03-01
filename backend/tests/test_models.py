"""Unit tests for Pydantic request/response models."""

import pytest
from pydantic import ValidationError

from app.models import (
    CreateJobRequest,
    EvalExample,
    Hyperparameters,
    JobUpdateCallback,
    ScoresQuery,
    TrainingPair,
)


# ============================================================
# TrainingPair
# ============================================================


class TestTrainingPair:
    def test_valid(self):
        tp = TrainingPair(prompt="Hello", completion="World")
        assert tp.category == "default"

    def test_with_category(self):
        tp = TrainingPair(prompt="Hello", completion="World", category="math")
        assert tp.category == "math"

    def test_empty_prompt_rejected(self):
        with pytest.raises(ValidationError):
            TrainingPair(prompt="", completion="World")

    def test_empty_completion_rejected(self):
        with pytest.raises(ValidationError):
            TrainingPair(prompt="Hello", completion="")


# ============================================================
# EvalExample
# ============================================================


class TestEvalExample:
    def test_valid(self):
        ex = EvalExample(question="What is 2+2?", completion="4")
        assert ex.question == "What is 2+2?"

    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            EvalExample(question="", completion="4")

    def test_empty_completion_rejected(self):
        with pytest.raises(ValidationError):
            EvalExample(question="What is 2+2?", completion="")


# ============================================================
# Hyperparameters
# ============================================================


class TestHyperparameters:
    def test_defaults(self):
        hp = Hyperparameters()
        assert hp.learning_rate == 2e-4
        assert hp.epochs == 3
        assert hp.lora_rank == 16
        assert hp.datainf_damping == 0.1
        assert hp.checkpoint_interval == 50

    def test_zero_learning_rate_rejected(self):
        with pytest.raises(ValidationError):
            Hyperparameters(learning_rate=0)

    def test_negative_learning_rate_rejected(self):
        with pytest.raises(ValidationError):
            Hyperparameters(learning_rate=-0.1)

    def test_lora_rank_too_small(self):
        with pytest.raises(ValidationError):
            Hyperparameters(lora_rank=2)

    def test_lora_rank_too_large(self):
        with pytest.raises(ValidationError):
            Hyperparameters(lora_rank=512)

    def test_datainf_damping_zero_rejected(self):
        with pytest.raises(ValidationError):
            Hyperparameters(datainf_damping=0)

    def test_datainf_damping_valid(self):
        hp = Hyperparameters(datainf_damping=5.0)
        assert hp.datainf_damping == 5.0

    def test_checkpoint_interval_bounds(self):
        with pytest.raises(ValidationError):
            Hyperparameters(checkpoint_interval=5)
        with pytest.raises(ValidationError):
            Hyperparameters(checkpoint_interval=2000)


# ============================================================
# CreateJobRequest
# ============================================================


class TestCreateJobRequest:
    def test_valid_inline(self):
        req = CreateJobRequest(
            model_name="meta-llama/Llama-2-7b-hf",
            training_pairs=[
                {"prompt": "Q", "completion": "A", "category": "math"},
            ],
            eval_examples=[{"question": "Q?", "completion": "A."}],
        )
        assert req.model_name == "meta-llama/Llama-2-7b-hf"
        assert len(req.training_pairs) == 1
        assert req.dataset_file_path is None

    def test_valid_file_path(self):
        req = CreateJobRequest(
            model_name="model",
            dataset_file_path="user/job/data.jsonl",
            eval_examples=[{"question": "Q?", "completion": "A."}],
        )
        assert req.training_pairs is None
        assert req.dataset_file_path == "user/job/data.jsonl"

    def test_empty_eval_examples_rejected(self):
        with pytest.raises(ValidationError):
            CreateJobRequest(
                model_name="model",
                training_pairs=[{"prompt": "Q", "completion": "A"}],
                eval_examples=[],
            )

    def test_whitespace_only_eval_rejected(self):
        with pytest.raises(ValidationError):
            CreateJobRequest(
                model_name="model",
                training_pairs=[{"prompt": "Q", "completion": "A"}],
                eval_examples=[{"question": "  ", "completion": "A."}],
            )

    def test_empty_training_pairs_list_rejected(self):
        with pytest.raises(ValidationError):
            CreateJobRequest(
                model_name="model",
                training_pairs=[],
                eval_examples=[{"question": "Q?", "completion": "A."}],
            )

    def test_empty_model_name_rejected(self):
        with pytest.raises(ValidationError):
            CreateJobRequest(
                model_name="",
                training_pairs=[{"prompt": "Q", "completion": "A"}],
                eval_examples=[{"question": "Q?", "completion": "A."}],
            )

    def test_default_hyperparameters(self):
        req = CreateJobRequest(
            model_name="model",
            training_pairs=[{"prompt": "Q", "completion": "A"}],
            eval_examples=[{"question": "Q?", "completion": "A."}],
        )
        assert req.hyperparameters.learning_rate == 2e-4


# ============================================================
# JobUpdateCallback
# ============================================================


class TestJobUpdateCallback:
    def test_valid(self):
        cb = JobUpdateCallback(
            job_id="22222222-2222-2222-2222-222222222222",
            status="training",
            progress=0.5,
        )
        assert cb.progress == 0.5

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            JobUpdateCallback(
                job_id="22222222-2222-2222-2222-222222222222",
                status="invalid_status",
            )

    def test_progress_out_of_range(self):
        with pytest.raises(ValidationError):
            JobUpdateCallback(
                job_id="22222222-2222-2222-2222-222222222222",
                status="training",
                progress=1.5,
            )

    def test_completed_status_valid(self):
        cb = JobUpdateCallback(
            job_id="22222222-2222-2222-2222-222222222222",
            status="completed",
            progress=1.0,
        )
        assert cb.status == "completed"


# ============================================================
# ScoresQuery
# ============================================================


class TestScoresQuery:
    def test_defaults(self):
        sq = ScoresQuery()
        assert sq.sort_by == "tracin_score"
        assert sq.order == "desc"
        assert sq.limit == 50
        assert sq.offset == 0

    def test_invalid_sort_by_rejected(self):
        with pytest.raises(ValidationError):
            ScoresQuery(sort_by="invalid_field")

    def test_invalid_order_rejected(self):
        with pytest.raises(ValidationError):
            ScoresQuery(order="random")

    def test_limit_bounds(self):
        with pytest.raises(ValidationError):
            ScoresQuery(limit=0)
        with pytest.raises(ValidationError):
            ScoresQuery(limit=1001)

    def test_datainf_sort(self):
        sq = ScoresQuery(sort_by="datainf_score", order="asc")
        assert sq.sort_by == "datainf_score"
