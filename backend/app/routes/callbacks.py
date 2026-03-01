import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_webhook_signature
from app.config import Settings, get_settings
from app.models import JobUpdateCallback, MessageResponse
from app.services import supabase_client as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/callbacks", tags=["callbacks"])


def get_db(settings: Annotated[Settings, Depends(get_settings)]):
    return db.get_supabase_client(settings)


@router.post(
    "/job-update",
    response_model=MessageResponse,
    dependencies=[Depends(verify_webhook_signature)],
)
async def job_update(
    body: JobUpdateCallback,
    client: Annotated[object, Depends(get_db)],
):
    """
    Receives HMAC-authenticated status updates from the Modal GPU container.
    Updates the jobs table; Supabase Realtime pushes changes to the frontend.
    """
    job_id = str(body.job_id)

    # Verify the job exists (don't scope to user — this is a system callback)
    result = client.table("jobs").select("id, status").eq("id", job_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    current_status = result.data["status"]

    # Prevent backwards status transitions (except to 'failed' which is always allowed)
    status_order = {
        "queued": 0,
        "provisioning": 1,
        "training": 2,
        "computing_tracin": 3,
        "computing_datainf": 4,
        "completed": 5,
        "failed": 6,
    }
    if (
        body.status != "failed"
        and status_order.get(body.status, 0) <= status_order.get(current_status, 0)
    ):
        logger.warning(
            f"Ignoring backward status transition for job {job_id}: "
            f"{current_status} → {body.status}"
        )
        return MessageResponse(message="Status transition ignored (not forward)")

    # Build update payload
    update_fields: dict = {
        "status": body.status,
        "progress": body.progress,
    }

    if body.status_message is not None:
        update_fields["status_message"] = body.status_message

    if body.status == "training" and current_status in ("queued", "provisioning"):
        update_fields["started_at"] = datetime.now(timezone.utc).isoformat()

    if body.status in ("completed", "failed"):
        update_fields["completed_at"] = datetime.now(timezone.utc).isoformat()
        if body.status == "completed":
            update_fields["progress"] = 1.0

    await db.update_job(client, job_id=job_id, **update_fields)

    logger.info(f"Job {job_id} updated: {current_status} → {body.status}")
    return MessageResponse(message=f"Job {job_id} status updated to {body.status}")
