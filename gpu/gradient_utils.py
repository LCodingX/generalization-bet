import logging
from collections import OrderedDict

import torch

logger = logging.getLogger(__name__)


def get_lora_parameter_names(model) -> list[str]:
    """Return sorted list of LoRA adapter parameter names (A and B matrices)."""
    names = []
    for name, param in model.named_parameters():
        if param.requires_grad and ("lora_A" in name or "lora_B" in name):
            names.append(name)
    return sorted(names)


def extract_lora_gradient_vector(model, param_names: list[str]) -> torch.Tensor:
    """Concatenate all LoRA gradients into a single flat float32 CPU vector.

    Used for TracIn dot product computation.
    """
    grads = []
    for name in param_names:
        param = dict(model.named_parameters())[name]
        if param.grad is not None:
            grads.append(param.grad.detach().float().cpu().flatten())
        else:
            grads.append(torch.zeros(param.numel(), dtype=torch.float32))
    return torch.cat(grads)


def extract_lora_gradients(model, param_names: list[str]) -> OrderedDict:
    """Extract per-layer flattened LoRA gradients.

    Used for DataInf per-layer computation. Returns an OrderedDict
    mapping layer name prefixes to concatenated A+B gradient vectors.
    """
    # Group params by their layer prefix (everything before lora_A/lora_B)
    layer_groups: dict[str, list[torch.Tensor]] = {}
    for name in param_names:
        # e.g. "base_model.model.model.layers.0.self_attn.q_proj.lora_A.default.weight"
        # prefix: "base_model.model.model.layers.0.self_attn.q_proj"
        if "lora_A" in name:
            prefix = name.split(".lora_A")[0]
        elif "lora_B" in name:
            prefix = name.split(".lora_B")[0]
        else:
            continue

        param = dict(model.named_parameters())[name]
        grad = (
            param.grad.detach().float().cpu().flatten()
            if param.grad is not None
            else torch.zeros(param.numel(), dtype=torch.float32)
        )

        if prefix not in layer_groups:
            layer_groups[prefix] = []
        layer_groups[prefix].append(grad)

    result = OrderedDict()
    for prefix in sorted(layer_groups.keys()):
        result[prefix] = torch.cat(layer_groups[prefix])
    return result


def compute_per_example_loss(
    model,
    tokens: dict,
    device: torch.device,
) -> torch.Tensor:
    """Forward + backward for a single example. Returns scalar loss.

    The caller is responsible for zeroing gradients before calling this.
    After this call, model.parameters() will have .grad populated.
    """
    input_ids = torch.tensor([tokens["input_ids"]], dtype=torch.long, device=device)
    attention_mask = torch.tensor([tokens["attention_mask"]], dtype=torch.long, device=device)
    labels = torch.tensor([tokens["labels"]], dtype=torch.long, device=device)

    outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
    loss = outputs.loss
    loss.backward()

    return loss.detach()
