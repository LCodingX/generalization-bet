from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_publishable_key: str  # Client-safe, respects RLS
    supabase_secret_key: str  # Server-side only, bypasses RLS

    # Modal (read automatically by Modal SDK from env, but we validate presence)
    modal_token_id: str
    modal_token_secret: str

    # Webhook
    webhook_secret: str  # Shared with Modal container for HMAC verification
    callback_base_url: str  # e.g. https://your-api.railway.app

    # HuggingFace
    hf_token: str

    # Modal app/function references
    modal_app_name: str = "tracin-runner"
    modal_function_name: str = "train_and_compute_influence"

    # Limits
    max_training_examples: int = 5000
    max_eval_examples: int = 100
    max_inline_payload_bytes: int = 2_000_000  # 2MB — above this, require file upload
    job_timeout_minutes: int = 360  # 6 hours before stale job recovery kicks in

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
