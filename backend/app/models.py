from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Request Models
# ============================================================


class TrainingPair(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=50_000)
    completion: str = Field(..., min_length=1, max_length=50_000)
    category: str = Field(default="default", min_length=1, max_length=100)


class Hyperparameters(BaseModel):
    learning_rate: float = Field(default=2e-4, gt=0, le=1.0)
    epochs: int = Field(default=3, ge=1, le=50)
    batch_size: int = Field(default=4, ge=1, le=64)
    lora_rank: int = Field(default=16, ge=4, le=256)
    lora_alpha: int = Field(default=32, ge=4, le=512)
    lora_dropout: float = Field(default=0.05, ge=0.0, le=0.5)
    checkpoint_interval: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Steps between TracIn gradient computations",
    )
    max_seq_length: int = Field(default=512, ge=64, le=4096)
    datainf_damping: float = Field(
        default=0.1,
        gt=0,
        le=10.0,
        description="Damping parameter λ for DataInf Sherman-Morrison approximation. "
        "Controls regularization. Smaller values = more sensitive to individual examples, "
        "larger values = more stable but less discriminative.",
    )


class EvalExample(BaseModel):
    question: str = Field(..., min_length=1, max_length=50_000)
    completion: str = Field(..., min_length=1, max_length=50_000)


class CreateJobRequest(BaseModel):
    model_name: str = Field(..., min_length=1, examples=["meta-llama/Llama-2-7b-hf"])
    hyperparameters: Hyperparameters = Field(default_factory=Hyperparameters)
    training_pairs: list[TrainingPair] | None = Field(
        default=None,
        description="Inline training data. Omit if using dataset_file_path.",
    )
    eval_examples: list[EvalExample] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Eval questions with expected completions. Completions are required for gradient computation.",
    )
    dataset_file_path: str | None = Field(
        default=None,
        description="Supabase Storage path to a .jsonl file. Use instead of training_pairs for large datasets.",
    )

    @field_validator("eval_examples")
    @classmethod
    def eval_examples_non_empty(cls, v: list[EvalExample]) -> list[EvalExample]:
        for ex in v:
            if not ex.question.strip() or not ex.completion.strip():
                raise ValueError("Eval examples must have non-empty question and completion")
        return v

    @field_validator("training_pairs")
    @classmethod
    def validate_training_pairs(cls, v: list[TrainingPair] | None) -> list[TrainingPair] | None:
        if v is not None and len(v) == 0:
            raise ValueError("training_pairs cannot be an empty list")
        return v


class ScoresQuery(BaseModel):
    train_id: UUID | None = None
    eval_id: UUID | None = None
    category: str | None = None
    sort_by: str = Field(default="tracin_score", pattern="^(tracin_score|datainf_score)$")
    order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ============================================================
# Webhook Models
# ============================================================


class JobUpdateCallback(BaseModel):
    job_id: UUID
    status: str = Field(
        ...,
        pattern="^(provisioning|training|computing_tracin|computing_datainf|completed|failed)$",
    )
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    status_message: str | None = None


# ============================================================
# Response Models
# ============================================================


class JobResponse(BaseModel):
    id: UUID
    status: str
    status_message: str | None
    progress: float
    model_name: str
    hyperparameters: dict
    telemetry: list = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobCreatedResponse(BaseModel):
    job_id: UUID
    status: str = "queued"


class InfluenceScoreRow(BaseModel):
    train_id: UUID
    eval_id: UUID
    train_index: int
    train_category: str
    eval_index: int
    train_prompt: str
    eval_question: str
    tracin_score: float
    datainf_score: float


class ScoresResponse(BaseModel):
    job_id: UUID
    total: int
    scores: list[InfluenceScoreRow]


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_path: str


class MessageResponse(BaseModel):
    message: str
