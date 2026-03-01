import logging

import numpy as np
import torch

from gradient_utils import (
    compute_per_example_loss,
    extract_lora_gradient_vector,
    get_lora_parameter_names,
)

logger = logging.getLogger(__name__)


def compute_tracin_at_checkpoint(
    model,
    training_data: list[dict],
    eval_tokens: list[dict],
    learning_rate: float,
    device: torch.device,
) -> np.ndarray:
    """Compute TracIn influence scores at a single checkpoint.

    For each eval example, computes its gradient, then dots it with each
    training example's gradient, scaled by the learning rate.

    Args:
        model: The LoRA-wrapped model at the current checkpoint state.
        training_data: Tokenized training examples (list of dicts with input_ids, etc.)
        eval_tokens: Tokenized eval examples.
        learning_rate: Current learning rate.
        device: Torch device.

    Returns:
        np.ndarray of shape (n_train, n_eval) — this checkpoint's contribution.
    """
    param_names = get_lora_parameter_names(model)
    n_train = len(training_data)
    n_eval = len(eval_tokens)

    # Step 1: Compute eval gradients
    logger.info(f"Computing {n_eval} eval gradients for TracIn checkpoint")
    eval_grads = []
    for j in range(n_eval):
        model.zero_grad()
        compute_per_example_loss(model, eval_tokens[j], device)
        grad_vec = extract_lora_gradient_vector(model, param_names)
        eval_grads.append(grad_vec)

    # Stack into matrix: (n_eval, d)
    eval_grad_matrix = torch.stack(eval_grads)  # (n_eval, d)

    # Step 2: Stream training gradients, dot product with all eval grads
    logger.info(f"Computing {n_train} training gradients for TracIn checkpoint")
    scores = np.zeros((n_train, n_eval), dtype=np.float32)

    for i in range(n_train):
        model.zero_grad()
        compute_per_example_loss(model, training_data[i], device)
        train_grad = extract_lora_gradient_vector(model, param_names)

        # Dot product with all eval grads: (n_eval,)
        dots = torch.mv(eval_grad_matrix, train_grad).numpy()
        scores[i, :] = learning_rate * dots

    return scores
