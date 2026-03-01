import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.models import MessageResponse
from app.services import supabase_client as db
from app.services import modal_dispatch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_db(settings: Annotated[Settings, Depends(get_settings)]):
    return db.get_supabase_client(settings)


async def verify_admin_key(
    x_admin_key: Annotated[str, Header()],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Simple shared-secret auth for admin/cron endpoints.
    The webhook secret doubles as the admin key to keep config minimal.
    In production, use a dedicated admin secret.
    """
    if x_admin_key != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


@router.post(
    "/recover-stale-jobs",
    response_model=MessageResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def recover_stale_jobs(
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[object, Depends(get_db)],
):
    """
    Called by an external cron (e.g., Supabase Edge Function, Railway cron,
    or a simple cron-job.org webhook) every 15 minutes.

    Finds jobs stuck in running states beyond the timeout threshold,
    checks their actual status on Modal, and marks dead ones as failed.
    """
    stale_jobs = await db.get_stale_jobs(client, timeout_minutes=settings.job_timeout_minutes)

    if not stale_jobs:
        return MessageResponse(message="No stale jobs found")

    recovered = 0
    for job in stale_jobs:
        job_id = job["id"]
        call_id = job.get("modal_call_id")

        if not call_id:
            # No call ID means dispatch never completed — mark as failed
            await db.update_job(
                client,
                job_id=job_id,
                status="failed",
                status_message="Job dispatch never completed (no Modal call ID)",
            )
            recovered += 1
            continue

        # Check actual status on Modal
        modal_status = await modal_dispatch.check_job_status(call_id)

        if modal_status in ("completed", "failed", "cancelled", "unknown"):
            await db.update_job(
                client,
                job_id=job_id,
                status="failed",
                status_message=f"Job recovered from stale state. Modal status: {modal_status}",
            )
            recovered += 1
            logger.info(f"Recovered stale job {job_id}: modal_status={modal_status}")
        else:
            # Still running on Modal — leave it alone but log
            logger.info(f"Stale job {job_id} is still running on Modal, skipping")

    return MessageResponse(message=f"Recovered {recovered} of {len(stale_jobs)} stale jobs")


@router.get("/health")
async def health():
    return {"status": "ok"}
