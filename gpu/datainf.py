import logging

import numpy as np
import torch

from gradient_utils import (
    compute_per_example_loss,
    extract_lora_gradients,
    get_lora_parameter_names,
)

logger = logging.getLogger(__name__)


def compute_datainf_scores(
    model,
    training_data: list[dict],
    eval_tokens: list[dict],
    damping: float,
    device: torch.device,
    webhook=None,
) -> np.ndarray:
    """Compute DataInf influence scores using 3-pass streaming.

    Memory-efficient design: recomputes gradients 3 times to avoid
    storing all training gradients in RAM.

    Pass 1: Compute per-layer lambda values (running mean of squared gradient norms).
    Pass 2: For each training example, compute gradient and update HVP
             accumulators for all eval examples via Sherman-Morrison.
    Pass 3: For each training example, recompute gradient and compute
             final IF scores against all eval HVP vectors.

    Args:
        model: The fine-tuned LoRA model.
        training_data: Tokenized training examples.
        eval_tokens: Tokenized eval examples.
        damping: Base damping parameter (lambda_0).
        device: Torch device.
        webhook: Optional WebhookClient for progress updates.

    Returns:
        np.ndarray of shape (n_train, n_eval).
    """
    param_names = get_lora_parameter_names(model)
    n_train = len(training_data)
    n_eval = len(eval_tokens)

    # ================================================================
    # Pass 1: Compute per-layer lambda values
    # ================================================================
    logger.info("DataInf Pass 1/3: Computing per-layer lambda values")
    layer_sq_sums: dict[str, torch.Tensor] = {}
    layer_counts: dict[str, int] = {}

    for i in range(n_train):
        model.zero_grad()
        compute_per_example_loss(model, training_data[i], device)
        grads = extract_lora_gradients(model, param_names)

        for layer_name, grad_vec in grads.items():
            sq_norm = torch.sum(grad_vec ** 2)
            if layer_name not in layer_sq_sums:
                layer_sq_sums[layer_name] = sq_norm
                layer_counts[layer_name] = 1
            else:
                layer_sq_sums[layer_name] += sq_norm
                layer_counts[layer_name] += 1

        if webhook and i % max(1, n_train // 10) == 0:
            progress = 0.70 + 0.07 * (i / n_train)
            webhook.send("computing_datainf", progress, f"DataInf pass 1: {i}/{n_train}")

    # Lambda per layer = damping + mean(squared gradient norms)
    lambdas: dict[str, float] = {}
    for layer_name in layer_sq_sums:
        mean_sq = layer_sq_sums[layer_name].item() / layer_counts[layer_name]
        lambdas[layer_name] = damping + mean_sq
    logger.info(f"Lambda values computed for {len(lambdas)} layers")

    # ================================================================
    # Compute eval gradients (needed for passes 2 and 3)
    # ================================================================
    logger.info(f"Computing {n_eval} eval gradients for DataInf")
    eval_grads_by_layer: list[dict[str, torch.Tensor]] = []
    for j in range(n_eval):
        model.zero_grad()
        compute_per_example_loss(model, eval_tokens[j], device)
        grads = extract_lora_gradients(model, param_names)
        eval_grads_by_layer.append(grads)

    # ================================================================
    # Pass 2: Accumulate HVP via Sherman-Morrison
    # ================================================================
    logger.info("DataInf Pass 2/3: Accumulating HVP vectors")

    # Initialize HVP accumulators: hvp[j][layer] = lambda_inv * eval_grad
    # This is H_0^{-1} @ eval_grad where H_0 = lambda * I
    hvp: list[dict[str, torch.Tensor]] = []
    for j in range(n_eval):
        hvp_j = {}
        for layer_name, grad_vec in eval_grads_by_layer[j].items():
            hvp_j[layer_name] = grad_vec / lambdas[layer_name]
        hvp.append(hvp_j)

    for i in range(n_train):
        model.zero_grad()
        compute_per_example_loss(model, training_data[i], device)
        train_grads = extract_lora_gradients(model, param_names)

        # Sherman-Morrison update for each eval example's HVP
        # H_{k+1}^{-1} v = H_k^{-1} v - (H_k^{-1} g_k)(g_k^T H_k^{-1} v) / (lambda_l + g_k^T H_k^{-1} g_k)
        for j in range(n_eval):
            for layer_name in train_grads:
                g = train_grads[layer_name]  # training gradient for this layer
                h_inv_v = hvp[j][layer_name]  # current HVP for this eval/layer

                # g^T @ H_k^{-1} @ g  (use cached H_k^{-1} applied to g)
                # We need H_k^{-1} @ g, but we only store H_k^{-1} @ v_j
                # For efficiency, compute the dot products directly
                g_dot_h_inv_v = torch.dot(g, h_inv_v)

                # We also need H_k^{-1} @ g. Approximate: g / lambda_l for the
                # initial inverse. For the full Sherman-Morrison recursion, we'd
                # need to track H_k^{-1} separately. Use the rank-1 approximation:
                # factor = dot(g, h_inv_v) / (lambda_l + ||g||^2)
                g_sq_norm = torch.dot(g, g)
                denom = lambdas[layer_name] + g_sq_norm.item()

                # Update: h_inv_v -= (g * g_dot_h_inv_v) / denom
                hvp[j][layer_name] = h_inv_v - (g * g_dot_h_inv_v) / denom

        if webhook and i % max(1, n_train // 10) == 0:
            progress = 0.77 + 0.10 * (i / n_train)
            webhook.send("computing_datainf", progress, f"DataInf pass 2: {i}/{n_train}")

    # ================================================================
    # Pass 3: Compute final influence scores
    # ================================================================
    logger.info("DataInf Pass 3/3: Computing influence scores")
    scores = np.zeros((n_train, n_eval), dtype=np.float32)

    for i in range(n_train):
        model.zero_grad()
        compute_per_example_loss(model, training_data[i], device)
        train_grads = extract_lora_gradients(model, param_names)

        for j in range(n_eval):
            score = 0.0
            for layer_name in train_grads:
                g = train_grads[layer_name]
                h_inv_v = hvp[j][layer_name]
                # IF[i, j] = -sum_l dot(g_i_l, H^{-1} v_j_l)
                score -= torch.dot(g, h_inv_v).item()
            scores[i, j] = score

        if webhook and i % max(1, n_train // 10) == 0:
            progress = 0.87 + 0.08 * (i / n_train)
            webhook.send("computing_datainf", progress, f"DataInf pass 3: {i}/{n_train}")

    logger.info(f"DataInf scores computed: shape={scores.shape}")
    return scores
