import logging

import numpy as np
from supabase import create_client, Client

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def write_telemetry(client: Client, job_id: str, telemetry: list[dict]) -> None:
    """Write the full telemetry array to the jobs.telemetry column."""
    client.table("jobs").update({"telemetry": telemetry}).eq("id", job_id).execute()
    logger.info(f"Wrote {len(telemetry)} telemetry entries for job {job_id}")


def get_client(supabase_url: str, supabase_service_key: str) -> Client:
    """Create a Supabase client with the service role key (bypasses RLS)."""
    return create_client(supabase_url, supabase_service_key)


def fetch_training_example_uuids(client: Client, job_id: str) -> dict[int, str]:
    """Fetch {index: uuid} map for all training examples of a job."""
    result = (
        client.table("training_examples")
        .select("id, index")
        .eq("job_id", job_id)
        .order("index")
        .execute()
    )
    return {row["index"]: row["id"] for row in result.data}


def fetch_eval_example_uuids(client: Client, job_id: str) -> dict[int, str]:
    """Fetch {index: uuid} map for all eval examples of a job."""
    result = (
        client.table("eval_examples")
        .select("id, index")
        .eq("job_id", job_id)
        .order("index")
        .execute()
    )
    return {row["index"]: row["id"] for row in result.data}


def write_influence_scores(
    client: Client,
    job_id: str,
    tracin_scores: np.ndarray,
    datainf_scores: np.ndarray,
    train_uuid_map: dict[int, str],
    eval_uuid_map: dict[int, str],
) -> int:
    """Batch upsert influence scores to Supabase.

    Args:
        tracin_scores: shape (n_train, n_eval)
        datainf_scores: shape (n_train, n_eval)
        train_uuid_map: {train_index: uuid}
        eval_uuid_map: {eval_index: uuid}

    Returns:
        Number of rows upserted.
    """
    n_train, n_eval = tracin_scores.shape
    rows = []

    for i in range(n_train):
        train_id = train_uuid_map[i]
        for j in range(n_eval):
            eval_id = eval_uuid_map[j]
            rows.append({
                "job_id": job_id,
                "train_id": train_id,
                "eval_id": eval_id,
                "tracin_score": float(tracin_scores[i, j]),
                "datainf_score": float(datainf_scores[i, j]),
            })

    total_upserted = 0
    for chunk_start in range(0, len(rows), BATCH_SIZE):
        chunk = rows[chunk_start : chunk_start + BATCH_SIZE]
        client.table("influence_scores").upsert(
            chunk,
            on_conflict="job_id,train_id,eval_id",
        ).execute()
        total_upserted += len(chunk)
        logger.info(f"Upserted {total_upserted}/{len(rows)} influence scores")

    return total_upserted
