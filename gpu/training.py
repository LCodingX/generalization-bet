import logging

import numpy as np
import torch

from config import JobConfig
from gradient_utils import extract_lora_parameter_vector, get_lora_parameter_names
from tracin import compute_tracin_at_checkpoint
from webhook import WebhookClient

logger = logging.getLogger(__name__)


def _compute_lcs(v_prev: torch.Tensor, v_curr: torch.Tensor, v_next: torch.Tensor) -> float:
    """Compute Linear CKA Similarity: cos(v_curr - v_prev, v_next - v_curr).

    Returns a value in [-1, 1].  -1 = straight path, 0 = orthogonal turn, +1 = reversal.
    """
    d1 = v_curr - v_prev
    d2 = v_next - v_curr
    norm1 = torch.linalg.norm(d1)
    norm2 = torch.linalg.norm(d2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return torch.dot(d1, d2).item() / (norm1.item() * norm2.item())


def _collect_telemetry_entry(
    step: int,
    epoch: int,
    norms: np.ndarray,
    categories: list[str],
    param_snapshots: list[torch.Tensor],
    category_param_snapshots: dict[str, list[torch.Tensor]],
) -> dict:
    """Build a single telemetry entry from checkpoint data."""
    # Global gradient norm = norm of sum of all per-example gradient norms
    # We approximate with the sum of individual norms (the norms vector is per-example)
    global_grad_norm = float(np.linalg.norm(norms))

    # Per-category gradient norms: norm of norms for examples in each category
    unique_cats = sorted(set(categories))
    partition_grad_norms = {}
    for cat in unique_cats:
        cat_indices = [i for i, c in enumerate(categories) if c == cat]
        cat_norms = norms[cat_indices]
        partition_grad_norms[cat] = float(np.linalg.norm(cat_norms))

    # LCS: need at least 3 snapshots
    global_lcs = None
    partition_lcs: dict[str, float] = {}

    if len(param_snapshots) >= 3:
        global_lcs = _compute_lcs(
            param_snapshots[-3], param_snapshots[-2], param_snapshots[-1]
        )
        for cat in unique_cats:
            cat_snaps = category_param_snapshots.get(cat, [])
            if len(cat_snaps) >= 3:
                partition_lcs[cat] = _compute_lcs(
                    cat_snaps[-3], cat_snaps[-2], cat_snaps[-1]
                )

    return {
        "step": step,
        "epoch": epoch,
        "global_grad_norm": global_grad_norm,
        "partition_grad_norms": partition_grad_norms,
        "global_lcs": global_lcs,
        "partition_lcs": partition_lcs,
    }


def run_training_loop(
    model,
    tokenizer,
    train_loader,
    eval_tokens: list[dict],
    training_data: list[dict],
    config: JobConfig,
    device: torch.device,
    webhook: WebhookClient | None = None,
    categories: list[str] | None = None,
) -> tuple[np.ndarray, list[dict]]:
    """Custom training loop with TracIn checkpointing and telemetry.

    At every checkpoint_interval steps, saves current batch gradients,
    runs TracIn computation, then restores gradients and continues training.
    TracIn is purely observational — it does not affect the training process.

    Args:
        model: LoRA-wrapped model.
        tokenizer: Tokenizer (unused but kept for interface consistency).
        train_loader: DataLoader for training batches.
        eval_tokens: Tokenized eval examples for TracIn.
        training_data: Tokenized individual training examples for TracIn.
        config: Job hyperparameters.
        device: Torch device.
        webhook: Optional webhook client for progress updates.
        categories: Per-example category labels (same length as training_data).

    Returns:
        Tuple of:
        - Accumulated TracIn scores: np.ndarray of shape (n_train, n_eval).
        - Telemetry entries: list of dicts.
    """
    n_train = len(training_data)
    n_eval = len(eval_tokens)
    if categories is None:
        categories = ["default"] * n_train

    # Only optimize LoRA parameters
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.learning_rate,
    )

    total_steps = config.epochs * len(train_loader)
    tracin_scores = np.zeros((n_train, n_eval), dtype=np.float32)
    global_step = 0

    # Telemetry state
    telemetry: list[dict] = []
    param_snapshots: list[torch.Tensor] = []
    category_param_snapshots: dict[str, list[torch.Tensor]] = {}

    logger.info(f"Starting training: {config.epochs} epochs, {total_steps} total steps")

    def _snapshot_params() -> None:
        """Take a snapshot of the LoRA parameters for LCS computation."""
        param_names = get_lora_parameter_names(model)
        param_snapshots.append(extract_lora_parameter_vector(model, param_names))

    def _record_telemetry(step: int, epoch: int, norms: np.ndarray) -> None:
        """Record telemetry entry (written to DB after training completes)."""
        entry = _collect_telemetry_entry(
            step=step,
            epoch=epoch,
            norms=norms,
            categories=categories,
            param_snapshots=param_snapshots,
            category_param_snapshots=category_param_snapshots,
        )
        telemetry.append(entry)

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            input_ids, attention_mask, labels = [b.to(device) for b in batch]

            # Forward + backward
            optimizer.zero_grad()
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss
            loss.backward()

            global_step += 1
            epoch_loss += loss.item()

            # TracIn checkpoint
            if global_step % config.checkpoint_interval == 0:
                logger.info(f"TracIn checkpoint at step {global_step}")

                # Save batch gradients
                saved_grads = {}
                for name, param in model.named_parameters():
                    if param.requires_grad and param.grad is not None:
                        saved_grads[name] = param.grad.clone()

                # Snapshot parameters before TracIn (for LCS)
                _snapshot_params()

                # Compute TracIn (this will overwrite gradients)
                checkpoint_scores, checkpoint_norms = compute_tracin_at_checkpoint(
                    model=model,
                    training_data=training_data,
                    eval_tokens=eval_tokens,
                    learning_rate=config.learning_rate,
                    device=device,
                )
                tracin_scores += checkpoint_scores

                # Record telemetry
                _record_telemetry(global_step, epoch + 1, checkpoint_norms)

                # Restore batch gradients
                for name, param in model.named_parameters():
                    if name in saved_grads:
                        param.grad = saved_grads[name]

            # Optimizer step
            optimizer.step()

            # Progress update (training phase = 0.0–0.65)
            if webhook and global_step % max(1, total_steps // 20) == 0:
                progress = 0.65 * (global_step / total_steps)
                webhook.send(
                    "training",
                    progress,
                    f"Epoch {epoch + 1}/{config.epochs}, step {global_step}/{total_steps}, loss={loss.item():.4f}",
                )

        avg_loss = epoch_loss / len(train_loader)
        logger.info(f"Epoch {epoch + 1}/{config.epochs} complete, avg loss={avg_loss:.4f}")

        # Record telemetry at the end of every epoch (if not already recorded at this step)
        if global_step % config.checkpoint_interval != 0:
            _snapshot_params()

            # Compute per-example gradient norms for telemetry
            checkpoint_scores, checkpoint_norms = compute_tracin_at_checkpoint(
                model=model,
                training_data=training_data,
                eval_tokens=eval_tokens,
                learning_rate=config.learning_rate,
                device=device,
            )
            tracin_scores += checkpoint_scores
            _record_telemetry(global_step, epoch + 1, checkpoint_norms)

    if webhook:
        webhook.send("computing_tracin", 0.65, "Training complete, TracIn scores accumulated")

    logger.info(f"Training complete. TracIn scores shape: {tracin_scores.shape}")
    return tracin_scores, telemetry
