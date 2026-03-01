import numpy as np
import torch
import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

from tracin import compute_tracin_at_checkpoint


@pytest.fixture(scope="module")
def model_and_tokenizer():
    model = AutoModelForCausalLM.from_pretrained("gpt2")
    lora_config = LoraConfig(
        r=4,
        lora_alpha=8,
        lora_dropout=0.0,
        target_modules=["c_attn"],
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )
    model = get_peft_model(model, lora_config)

    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    return model, tokenizer


def _make_tokens(tokenizer, text, max_len=64):
    """Create a token dict for a single example."""
    prompt = f"### Question:\n{text}\n\n### Answer:\n"
    full = prompt + "Answer" + tokenizer.eos_token

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    full_ids = tokenizer.encode(full, add_special_tokens=False)[:max_len]
    prompt_len = min(len(prompt_ids), len(full_ids))

    labels = [-100] * prompt_len + full_ids[prompt_len:]
    pad_len = max_len - len(full_ids)

    return {
        "input_ids": full_ids + [tokenizer.pad_token_id] * pad_len,
        "attention_mask": [1] * len(full_ids) + [0] * pad_len,
        "labels": labels + [-100] * pad_len,
    }


class TestTracIn:
    def test_score_matrix_shape(self, model_and_tokenizer):
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        train_data = [
            _make_tokens(tokenizer, "What is 2+2?"),
            _make_tokens(tokenizer, "Capital of France?"),
            _make_tokens(tokenizer, "Color of sky?"),
        ]
        eval_data = [
            _make_tokens(tokenizer, "What is 3+3?"),
            _make_tokens(tokenizer, "Capital of Germany?"),
        ]

        scores = compute_tracin_at_checkpoint(
            model=model,
            training_data=train_data,
            eval_tokens=eval_data,
            learning_rate=1e-4,
            device=device,
        )

        assert scores.shape == (3, 2)  # n_train x n_eval
        assert scores.dtype == np.float32

    def test_lr_scaling(self, model_and_tokenizer):
        """Scores should scale linearly with learning rate."""
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        train_data = [_make_tokens(tokenizer, "Test")]
        eval_data = [_make_tokens(tokenizer, "Test eval")]

        scores_1x = compute_tracin_at_checkpoint(
            model, train_data, eval_data, learning_rate=1e-4, device=device,
        )
        scores_2x = compute_tracin_at_checkpoint(
            model, train_data, eval_data, learning_rate=2e-4, device=device,
        )

        # scores_2x should be approximately 2x scores_1x
        ratio = scores_2x[0, 0] / scores_1x[0, 0] if scores_1x[0, 0] != 0 else 0
        assert abs(ratio - 2.0) < 0.01

    def test_scores_are_finite(self, model_and_tokenizer):
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        train_data = [_make_tokens(tokenizer, "Hello")]
        eval_data = [_make_tokens(tokenizer, "World")]

        scores = compute_tracin_at_checkpoint(
            model, train_data, eval_data, learning_rate=1e-4, device=device,
        )

        assert np.all(np.isfinite(scores))
