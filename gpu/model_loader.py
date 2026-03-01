import logging

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType

logger = logging.getLogger(__name__)


def load_model_and_tokenizer(
    model_name: str,
    hf_token: str | None = None,
    max_seq_len: int = 512,
    use_quantization: bool = True,
):
    """Load a HuggingFace causal LM with optional 4-bit NF4 quantization.

    Args:
        model_name: HuggingFace model ID (e.g. "meta-llama/Llama-2-7b-hf")
        hf_token: HuggingFace access token for gated models
        max_seq_len: Maximum sequence length for tokenizer
        use_quantization: If True, load in 4-bit NF4 (requires GPU). Set False for CPU testing.

    Returns:
        (model, tokenizer) tuple
    """
    logger.info(f"Loading model: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=hf_token,
        model_max_length=max_seq_len,
        padding_side="right",
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model_kwargs = {
        "token": hf_token,
        "torch_dtype": torch.float32 if not use_quantization else torch.float16,
    }

    if use_quantization:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["device_map"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    if use_quantization:
        model = prepare_model_for_kbit_training(model)

    logger.info(f"Model loaded: {model.num_parameters():,} parameters")
    return model, tokenizer


def create_lora_model(
    model,
    rank: int = 16,
    alpha: int = 32,
    dropout: float = 0.05,
):
    """Wrap the model with LoRA adapters on q_proj and v_proj."""
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=["q_proj", "v_proj"],
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    logger.info(f"LoRA applied: {trainable:,} trainable / {total:,} total parameters")
    return model
