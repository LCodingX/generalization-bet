from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth import AuthenticatedUser, get_current_user
from app.config import Settings, get_settings
from app.models import UploadUrlResponse
from app.services import supabase_client as db

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def get_db(settings: Annotated[Settings, Depends(get_settings)]):
    return db.get_supabase_client(settings)


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    client: Annotated[object, Depends(get_db)],
    filename: Annotated[str, Query(min_length=1, max_length=255, pattern=r"^[\w\-. ]+\.jsonl$")],
):
    """
    Generate a presigned upload URL for Supabase Storage.
    The frontend uploads the .jsonl file directly to this URL,
    bypassing FastAPI entirely for large files.
    """
    signed_url, storage_path = await db.create_signed_upload_url(
        client,
        user_id=user.user_id,
        filename=filename,
    )

    return UploadUrlResponse(upload_url=signed_url, storage_path=storage_path)
