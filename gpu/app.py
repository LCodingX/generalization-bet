import logging
import sys

import modal

from config import JobConfig
from webhook import WebhookClient

logger = logging.getLogger(__name__)

app = modal.App("tracin-runner")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.2.0",
        "transformers>=4.40.0",
        "peft>=0.10.0",
        "bitsandbytes>=0.43.0",
        "accelerate>=0.30.0",
        "supabase>=2.9.0",
        "httpx>=0.27.0",
        "sentencepiece>=0.2.0",
        "protobuf>=5.26.0",
        "numpy>=1.26.0",
    )
    .add_local_file("config.py", "/root/config.py")
    .add_local_file("model_loader.py", "/root/model_loader.py")
    .add_local_file("dataset.py", "/root/dataset.py")
    .add_local_file("gradient_utils.py", "/root/gradient_utils.py")
    .add_local_file("tracin.py", "/root/tracin.py")
    .add_local_file("datainf.py", "/root/datainf.py")
    .add_local_file("training.py", "/root/training.py")
    .add_local_file("webhook.py", "/root/webhook.py")
    .add_local_file("supabase_writer.py", "/root/supabase_writer.py")
)


@app.function(
    image=image,
    gpu="A100-80GB",
    timeout=6 * 3600,
    memory=32768,
    retries=0,
)
def train_and_compute_influence(
    dataset_url: str,
    eval_examples: list[dict],
    config: dict,
    job_id: str,
    supabase_url: str,
    supabase_service_key: str,
    callback_url: str,
    webhook_secret: str,
    hf_token: str | None = None,
):
    """Main entry point: fine-tune with LoRA, compute TracIn + DataInf scores.

    Function signature matches exactly what the backend dispatches via:
    backend/app/services/modal_dispatch.py:29-38
    """
    # Configure logging inside the container
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    # Add /root to sys.path so local modules can be imported
    if "/root" not in sys.path:
        sys.path.insert(0, "/root")

    import torch
    from model_loader import load_model_and_tokenizer, create_lora_model
    from dataset import (
        download_and_parse_dataset,
        tokenize_for_training,
        tokenize_examples,
        build_dataloader,
    )
    from training import run_training_loop
    from datainf import compute_datainf_scores
    from supabase_writer import (
        get_client,
        fetch_training_example_uuids,
        fetch_eval_example_uuids,
        write_influence_scores,
    )

    webhook = WebhookClient(callback_url, webhook_secret, job_id)
    job_config = JobConfig.from_dict(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    try:
        # ---- Provisioning ----
        webhook.send("provisioning", 0.0, "Loading model and data")

        model, tokenizer = load_model_and_tokenizer(
            model_name=job_config.model_name,
            hf_token=hf_token,
            max_seq_len=job_config.max_seq_length,
            use_quantization=torch.cuda.is_available(),
        )
        model = create_lora_model(
            model,
            rank=job_config.lora_rank,
            alpha=job_config.lora_alpha,
            dropout=job_config.lora_dropout,
        )

        # Download and tokenize training data
        raw_training = download_and_parse_dataset(dataset_url)
        tokenized_training = tokenize_for_training(raw_training, tokenizer, job_config.max_seq_length)
        train_loader = build_dataloader(tokenized_training, job_config.batch_size)

        # Tokenize individual examples for per-example gradient computation
        training_tokens = tokenize_examples(raw_training, tokenizer, job_config.max_seq_length, role="train")
        eval_tokens = tokenize_examples(eval_examples, tokenizer, job_config.max_seq_length, role="eval")

        webhook.send("provisioning", 0.05, f"Loaded {len(raw_training)} training, {len(eval_examples)} eval examples")

        # ---- Training + TracIn ----
        webhook.send("training", 0.05, "Starting fine-tuning")

        tracin_scores = run_training_loop(
            model=model,
            tokenizer=tokenizer,
            train_loader=train_loader,
            eval_tokens=eval_tokens,
            training_data=training_tokens,
            config=job_config,
            device=device,
            webhook=webhook,
        )

        # ---- DataInf ----
        webhook.send("computing_datainf", 0.70, "Computing DataInf influence scores")

        datainf_scores = compute_datainf_scores(
            model=model,
            training_data=training_tokens,
            eval_tokens=eval_tokens,
            damping=job_config.datainf_damping,
            device=device,
            webhook=webhook,
        )

        # ---- Write scores to Supabase ----
        webhook.send("computing_datainf", 0.95, "Writing scores to database")

        sb_client = get_client(supabase_url, supabase_service_key)
        train_uuid_map = fetch_training_example_uuids(sb_client, job_id)
        eval_uuid_map = fetch_eval_example_uuids(sb_client, job_id)

        n_written = write_influence_scores(
            client=sb_client,
            job_id=job_id,
            tracin_scores=tracin_scores,
            datainf_scores=datainf_scores,
            train_uuid_map=train_uuid_map,
            eval_uuid_map=eval_uuid_map,
        )

        # ---- Done ----
        webhook.send("completed", 1.0, f"Done. {n_written} influence scores computed.")
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        webhook.send("failed", 0.0, str(e)[:500])
        raise
