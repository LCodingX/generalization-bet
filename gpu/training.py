import logging

import numpy as np
import torch

from config import JobConfig
from tracin import compute_tracin_at_checkpoint
from webhook import WebhookClient

logger = logging.getLogger(__name__)


def run_training_loop(
    model,
    tokenizer,
    train_loader,
    eval_tokens: list[dict],
    training_data: list[dict],
    config: JobConfig,
    device: torch.device,
    webhook: WebhookClient | None = None,
) -> np.ndarray:
    """Custom training loop with TracIn checkpointing.

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

    Returns:
        Accumulated TracIn scores: np.ndarray of shape (n_train, n_eval).
    """
    n_train = len(training_data)
    n_eval = len(eval_tokens)

    # Only optimize LoRA parameters
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.learning_rate,
    )

    total_steps = config.epochs * len(train_loader)
    tracin_scores = np.zeros((n_train, n_eval), dtype=np.float32)
    global_step = 0

    logger.info(f"Starting training: {config.epochs} epochs, {total_steps} total steps")

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

                # Compute TracIn (this will overwrite gradients)
                checkpoint_scores = compute_tracin_at_checkpoint(
                    model=model,
                    training_data=training_data,
                    eval_tokens=eval_tokens,
                    learning_rate=config.learning_rate,
                    device=device,
                )
                tracin_scores += checkpoint_scores

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

    # Final TracIn checkpoint if last step wasn't one
    if global_step % config.checkpoint_interval != 0:
        logger.info(f"Final TracIn checkpoint at step {global_step}")
        # Need a forward/backward to populate gradients for the last state
        # Use the last batch (already have model in trained state)
        checkpoint_scores = compute_tracin_at_checkpoint(
            model=model,
            training_data=training_data,
            eval_tokens=eval_tokens,
            learning_rate=config.learning_rate,
            device=device,
        )
        tracin_scores += checkpoint_scores

    if webhook:
        webhook.send("computing_tracin", 0.65, "Training complete, TracIn scores accumulated")

    logger.info(f"Training complete. TracIn scores shape: {tracin_scores.shape}")
    return tracin_scores
