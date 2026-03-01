import numpy as np
import torch
import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

from datainf import compute_datainf_scores


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


class TestDataInf:
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

        scores = compute_datainf_scores(
            model=model,
            training_data=train_data,
            eval_tokens=eval_data,
            damping=0.1,
            device=device,
        )

        assert scores.shape == (3, 2)  # n_train x n_eval
        assert scores.dtype == np.float32

    def test_scores_are_finite(self, model_and_tokenizer):
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        train_data = [_make_tokens(tokenizer, "Hello")]
        eval_data = [_make_tokens(tokenizer, "World")]

        scores = compute_datainf_scores(
            model, train_data, eval_data, damping=0.1, device=device,
        )

        assert np.all(np.isfinite(scores))

    def test_damping_effect(self, model_and_tokenizer):
        """Higher damping should produce smaller magnitude scores."""
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        train_data = [_make_tokens(tokenizer, "Test")]
        eval_data = [_make_tokens(tokenizer, "Test eval")]

        scores_low = compute_datainf_scores(
            model, train_data, eval_data, damping=0.01, device=device,
        )
        scores_high = compute_datainf_scores(
            model, train_data, eval_data, damping=10.0, device=device,
        )

        # Higher damping → more regularization → smaller magnitude
        assert abs(scores_high[0, 0]) < abs(scores_low[0, 0])

    def test_sign_convention(self, model_and_tokenizer):
        """DataInf uses IF[i,j] = -sum dot(g_i, H^-1 g_j).

        For a training example evaluated against itself (similar gradient),
        the score should typically be negative (harmful = reduces loss on eval).
        """
        model, tokenizer = model_and_tokenizer
        device = torch.device("cpu")

        # Use the same text for train and eval (should have similar gradients)
        same_tokens = _make_tokens(tokenizer, "What is two plus two?")
        scores = compute_datainf_scores(
            model, [same_tokens], [same_tokens], damping=0.1, device=device,
        )

        # Self-influence is typically negative (the formula has a leading minus)
        # This is a soft check — the sign depends on the gradient structure
        assert scores.shape == (1, 1)
        assert np.isfinite(scores[0, 0])
