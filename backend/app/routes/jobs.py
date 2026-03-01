import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import AuthenticatedUser, get_current_user
from app.config import Settings, get_settings
from app.models import (
    CreateJobRequest,
    InfluenceScoreRow,
    JobCreatedResponse,
    JobResponse,
    MessageResponse,
    ScoresResponse,
)
from app.services import supabase_client as db
from app.services import modal_dispatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# ============================================================
# Dependency: Supabase client per-request
# ============================================================


def get_db(settings: Annotated[Settings, Depends(get_settings)]):
    return db.get_supabase_client(settings)


# ============================================================
# POST /api/v1/jobs — Create and dispatch a job
# ============================================================


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CreateJobRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[object, Depends(get_db)],
):
    # Validate: must have either inline data or a file path
    if body.training_pairs is None and body.dataset_file_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either training_pairs or dataset_file_path",
        )
    if body.training_pairs is not None and body.dataset_file_path is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide training_pairs OR dataset_file_path, not both",
        )

    # Validate inline payload size
    if body.training_pairs is not None:
        if len(body.training_pairs) > settings.max_training_examples:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Max {settings.max_training_examples} training examples inline",
            )
        payload_size = len(json.dumps([p.model_dump() for p in body.training_pairs]).encode("utf-8"))
        if payload_size > settings.max_inline_payload_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training data too large for inline submission. Upload as a file instead.",
            )

    if len(body.eval_examples) > settings.max_eval_examples:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max {settings.max_eval_examples} eval questions",
        )

    # 1. Create the job row
    job = await db.create_job(
        client,
        user_id=user.user_id,
        model_name=body.model_name,
        hyperparameters=body.hyperparameters.model_dump(),
        dataset_storage_path=body.dataset_file_path,
    )
    job_id = job["id"]

    # 2. Insert training examples (inline) or validate storage path exists
    if body.training_pairs is not None:
        await db.insert_training_examples(
            client,
            job_id=job_id,
            pairs=[p.model_dump() for p in body.training_pairs],
        )
        # For Modal: serialize inline data to a temp storage path
        # so the container always reads from one source
        inline_data = [
            {"prompt": p.prompt, "completion": p.completion, "category": p.category}
            for p in body.training_pairs
        ]
        # Upload inline data as .jsonl to storage
        jsonl_content = "\n".join(json.dumps(row) for row in inline_data)
        storage_path = f"{user.user_id}/{job_id}/training_data.jsonl"
        client.storage.from_("datasets").upload(
            storage_path,
            jsonl_content.encode(),
            file_options={"content-type": "application/jsonl"},
        )
        await db.update_job(client, job_id=job_id, dataset_storage_path=storage_path)
        dataset_path = storage_path
    else:
        dataset_path = body.dataset_file_path

    # 3. Insert eval examples (question + completion pairs)
    await db.insert_eval_examples(
        client,
        job_id=job_id,
        examples=[ex.model_dump() for ex in body.eval_examples],
    )

    # 4. Generate signed download URL for the Modal container
    signed_url = await db.create_signed_download_url(
        client,
        storage_path=dataset_path,
        expires_in=7200,  # 2 hours — enough for provisioning + download
    )

    # 5. Dispatch to Modal (spawn returns immediately)
    try:
        modal_call_id = await modal_dispatch.dispatch_job(
            settings,
            job_id=job_id,
            dataset_url=signed_url,
            eval_examples=[ex.model_dump() for ex in body.eval_examples],
            config={
                **body.hyperparameters.model_dump(),
                "model_name": body.model_name,
            },
        )
        await db.update_job(
            client,
            job_id=job_id,
            status="provisioning",
            modal_call_id=modal_call_id,
        )
    except Exception as e:
        logger.error(f"Modal dispatch failed for job {job_id}: {e}")
        await db.update_job(
            client,
            job_id=job_id,
            status="failed",
            status_message=f"Failed to dispatch: {str(e)[:500]}",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to dispatch job to GPU provider",
        )

    return JobCreatedResponse(job_id=UUID(job_id), status="provisioning")


# ============================================================
# GET /api/v1/jobs — List user's jobs
# ============================================================


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    client: Annotated[object, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
):
    jobs = await db.get_jobs_for_user(client, user_id=user.user_id, status_filter=status_filter)
    return jobs


# ============================================================
# GET /api/v1/jobs/{job_id} — Get single job
# ============================================================


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    client: Annotated[object, Depends(get_db)],
):
    job = await db.get_job(client, job_id=str(job_id), user_id=user.user_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


# ============================================================
# GET /api/v1/jobs/{job_id}/scores — Get influence scores
# ============================================================


@router.get("/{job_id}/scores", response_model=ScoresResponse)
async def get_scores(
    job_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    client: Annotated[object, Depends(get_db)],
    train_id: Annotated[UUID | None, Query()] = None,
    eval_id: Annotated[UUID | None, Query()] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    sort_by: Annotated[str, Query(pattern="^(tracin_score|datainf_score)$")] = "tracin_score",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    # Verify user owns this job
    job = await db.get_job(client, job_id=str(job_id), user_id=user.user_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not completed (current status: {job['status']})",
        )

    rows, total = await db.get_influence_scores(
        client,
        job_id=str(job_id),
        train_id=str(train_id) if train_id else None,
        eval_id=str(eval_id) if eval_id else None,
        category=category,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    scores = [
        InfluenceScoreRow(
            train_id=row["train_id"],
            eval_id=row["eval_id"],
            train_index=row["training_examples"]["index"],
            train_category=row["training_examples"]["category"],
            eval_index=row["eval_examples"]["index"],
            train_prompt=row["training_examples"]["prompt"],
            eval_question=row["eval_examples"]["question"],
            tracin_score=row["tracin_score"],
            datainf_score=row["datainf_score"],
        )
        for row in rows
    ]

    return ScoresResponse(job_id=job_id, total=total, scores=scores)


# ============================================================
# DELETE /api/v1/jobs/{job_id} — Cancel and delete a job
# ============================================================


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    client: Annotated[object, Depends(get_db)],
):
    job = await db.get_job(client, job_id=str(job_id), user_id=user.user_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # If the job is still running, try to cancel it on Modal
    if job.get("modal_call_id") and job["status"] not in ("completed", "failed"):
        await modal_dispatch.cancel_job(job["modal_call_id"])

    # Delete cascades to training_examples, eval_examples, influence_scores
    deleted = await db.delete_job(client, job_id=str(job_id), user_id=user.user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Clean up storage
    if job.get("dataset_storage_path"):
        try:
            client.storage.from_("datasets").remove([job["dataset_storage_path"]])
        except Exception as e:
            logger.warning(f"Failed to clean up storage for job {job_id}: {e}")

    return MessageResponse(message=f"Job {job_id} deleted")
