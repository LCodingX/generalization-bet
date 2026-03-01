from uuid import UUID, uuid4

from supabase import create_client, Client

from app.config import Settings


def get_supabase_client(settings: Settings) -> Client:
    """
    Returns a Supabase client using the SERVICE ROLE key.
    This bypasses RLS — use only in the backend, never expose to frontend.
    """
    return create_client(settings.supabase_url, settings.supabase_secret_key)


# ============================================================
# Jobs
# ============================================================


async def create_job(
    client: Client,
    *,
    user_id: str,
    model_name: str,
    hyperparameters: dict,
    dataset_storage_path: str | None = None,
) -> dict:
    """Insert a new job row and return it."""
    job_id = str(uuid4())
    result = (
        client.table("jobs")
        .insert({
            "id": job_id,
            "user_id": user_id,
            "status": "queued",
            "progress": 0.0,
            "model_name": model_name,
            "hyperparameters": hyperparameters,
            "dataset_storage_path": dataset_storage_path,
        })
        .execute()
    )
    return result.data[0]


async def get_jobs_for_user(
    client: Client,
    *,
    user_id: str,
    status_filter: str | None = None,
) -> list[dict]:
    """List all jobs for a user, optionally filtered by status."""
    query = (
        client.table("jobs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    if status_filter:
        query = query.eq("status", status_filter)
    result = query.execute()
    return result.data


async def get_job(client: Client, *, job_id: str, user_id: str) -> dict | None:
    """Get a single job, scoped to the user."""
    result = (
        client.table("jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def update_job(client: Client, *, job_id: str, **fields) -> dict | None:
    """Update arbitrary fields on a job row."""
    result = (
        client.table("jobs")
        .update(fields)
        .eq("id", job_id)
        .execute()
    )
    return result.data[0] if result.data else None


async def delete_job(client: Client, *, job_id: str, user_id: str) -> bool:
    """Delete a job and all cascaded data. Returns True if a row was deleted."""
    result = (
        client.table("jobs")
        .delete()
        .eq("id", job_id)
        .eq("user_id", user_id)
        .execute()
    )
    return len(result.data) > 0


# ============================================================
# Training & Eval Examples
# ============================================================


async def insert_training_examples(
    client: Client,
    *,
    job_id: str,
    pairs: list[dict],
) -> list[dict]:
    """Batch insert training examples. Each dict has {prompt, completion, category}."""
    rows = [
        {
            "id": str(uuid4()),
            "job_id": job_id,
            "index": i,
            "category": pair.get("category", "default"),
            "prompt": pair["prompt"],
            "completion": pair["completion"],
        }
        for i, pair in enumerate(pairs)
    ]
    # Supabase has a row limit per insert — batch in chunks of 500
    all_inserted = []
    for chunk_start in range(0, len(rows), 500):
        chunk = rows[chunk_start : chunk_start + 500]
        result = client.table("training_examples").insert(chunk).execute()
        all_inserted.extend(result.data)
    return all_inserted


async def insert_eval_examples(
    client: Client,
    *,
    job_id: str,
    examples: list[dict],
) -> list[dict]:
    """Batch insert eval examples. Each dict has {question, completion}."""
    rows = [
        {
            "id": str(uuid4()),
            "job_id": job_id,
            "index": i,
            "question": ex["question"],
            "completion": ex["completion"],
        }
        for i, ex in enumerate(examples)
    ]
    result = client.table("eval_examples").insert(rows).execute()
    return result.data


# ============================================================
# Influence Scores
# ============================================================


async def get_influence_scores(
    client: Client,
    *,
    job_id: str,
    train_id: str | None = None,
    eval_id: str | None = None,
    category: str | None = None,
    sort_by: str = "tracin_score",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    Fetch influence scores with joined training/eval example data.
    Returns (rows, total_count).
    """
    # Build query with joins via select
    query = (
        client.table("influence_scores")
        .select(
            "train_id, eval_id, tracin_score, datainf_score, "
            "training_examples!inner(index, category, prompt), "
            "eval_examples!inner(index, question)",
            count="exact",
        )
        .eq("job_id", job_id)
    )

    if train_id:
        query = query.eq("train_id", train_id)
    if eval_id:
        query = query.eq("eval_id", eval_id)
    if category:
        query = query.eq("training_examples.category", category)

    desc = order == "desc"
    query = query.order(sort_by, desc=desc).range(offset, offset + limit - 1)

    result = query.execute()
    return result.data, result.count or 0


# ============================================================
# Storage
# ============================================================


async def create_signed_upload_url(
    client: Client,
    *,
    user_id: str,
    filename: str,
) -> tuple[str, str]:
    """
    Create a signed upload URL for Supabase Storage.
    Returns (signed_url, storage_path).
    """
    storage_path = f"{user_id}/{uuid4()}/{filename}"
    result = client.storage.from_("datasets").create_signed_upload_url(storage_path)
    return result["signed_url"], storage_path


async def create_signed_download_url(
    client: Client,
    *,
    storage_path: str,
    expires_in: int = 3600,
) -> str:
    """Create a time-limited download URL for the Modal container."""
    result = client.storage.from_("datasets").create_signed_url(storage_path, expires_in)
    return result["signedURL"]


# ============================================================
# Stale Job Recovery
# ============================================================


async def get_stale_jobs(client: Client, *, timeout_minutes: int) -> list[dict]:
    """Find jobs that have been in a running state longer than the timeout."""
    from datetime import datetime, timedelta, timezone

    threshold = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    result = (
        client.table("jobs")
        .select("id, modal_call_id, status, updated_at")
        .in_("status", ["provisioning", "training", "computing_tracin", "computing_datainf"])
        .lt("updated_at", threshold)
        .execute()
    )
    return result.data
