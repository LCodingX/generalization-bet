import logging

import modal

from app.config import Settings

logger = logging.getLogger(__name__)


async def dispatch_job(
    settings: Settings,
    *,
    job_id: str,
    dataset_url: str,
    eval_examples: list[dict],
    config: dict,
) -> str:
    """
    Spawn a fine-tuning + influence computation job on Modal.

    Returns the Modal call ID for tracking/cancellation.

    Modal SDK reads MODAL_TOKEN_ID and MODAL_TOKEN_SECRET from env vars
    automatically — no credential injection needed.
    """
    try:
        f = modal.Function.from_name(settings.modal_app_name, settings.modal_function_name)

        call = f.spawn(
            dataset_url=dataset_url,
            eval_examples=eval_examples,
            config=config,
            job_id=job_id,
            supabase_url=settings.supabase_url,
            supabase_service_key=settings.supabase_secret_key,
            callback_url=f"{settings.callback_base_url}/api/v1/callbacks/job-update",
            webhook_secret=settings.webhook_secret,
            hf_token=settings.hf_token,
        )

        logger.info(f"Dispatched job {job_id} to Modal, call_id={call.object_id}")
        return call.object_id

    except modal.exception.NotFoundError:
        logger.error(
            f"Modal function {settings.modal_app_name}/{settings.modal_function_name} not found. "
            "Ensure the Modal app is deployed."
        )
        raise
    except Exception as e:
        logger.error(f"Failed to dispatch job {job_id} to Modal: {e}")
        raise


async def check_job_status(call_id: str) -> str:
    """
    Check the status of a Modal function call.
    Used by the stale job recovery process.

    Returns one of: 'pending', 'running', 'completed', 'failed', 'cancelled', 'unknown'
    """
    try:
        fc = modal.functions.FunctionCall.from_id(call_id)
        # .get(timeout=0) will raise TimeoutError if still running
        try:
            fc.get(timeout=0)
            return "completed"
        except TimeoutError:
            return "running"
        except Exception:
            return "failed"
    except Exception as e:
        logger.warning(f"Could not check Modal call {call_id}: {e}")
        return "unknown"


async def cancel_job(call_id: str) -> bool:
    """Attempt to cancel a running Modal job. Returns True if cancellation was sent."""
    try:
        fc = modal.functions.FunctionCall.from_id(call_id)
        fc.cancel()
        logger.info(f"Cancelled Modal call {call_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cancel Modal call {call_id}: {e}")
        return False
