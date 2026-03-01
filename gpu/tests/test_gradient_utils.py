import torch
import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

from gradient_utils import (
    get_lora_parameter_names,
    extract_lora_gradient_vector,
    extract_lora_gradients,
    compute_per_example_loss,
)


@pytest.fixture(scope="module")
def lora_model():
    """Create a tiny GPT-2 with LoRA for testing."""
    model = AutoModelForCausalLM.from_pretrained("gpt2")
    lora_config = LoraConfig(
        r=4,
        lora_alpha=8,
        lora_dropout=0.0,
        target_modules=["c_attn"],  # GPT-2 uses c_attn instead of q_proj/v_proj
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.eval()
    return model


@pytest.fixture(scope="module")
def tokenizer():
    tok = AutoTokenizer.from_pretrained("gpt2")
    tok.pad_token = tok.eos_token
    tok.pad_token_id = tok.eos_token_id
    return tok


class TestGetLoraParameterNames:
    def test_returns_lora_params_only(self, lora_model):
        names = get_lora_parameter_names(lora_model)
        assert len(names) > 0
        for name in names:
            assert "lora_A" in name or "lora_B" in name

    def test_sorted(self, lora_model):
        names = get_lora_parameter_names(lora_model)
        assert names == sorted(names)


class TestExtractLoraGradientVector:
    def test_gradient_shape(self, lora_model, tokenizer):
        param_names = get_lora_parameter_names(lora_model)

        # Compute a loss to populate gradients
        tokens = tokenizer("Hello world", return_tensors="pt")
        tokens["labels"] = tokens["input_ids"].clone()
        lora_model.zero_grad()
        outputs = lora_model(**tokens)
        outputs.loss.backward()

        grad_vec = extract_lora_gradient_vector(lora_model, param_names)

        # Should be a 1-D float32 CPU tensor
        assert grad_vec.dim() == 1
        assert grad_vec.dtype == torch.float32
        assert grad_vec.device.type == "cpu"

        # Total size should match sum of LoRA param sizes
        expected_size = sum(
            dict(lora_model.named_parameters())[n].numel() for n in param_names
        )
        assert grad_vec.shape[0] == expected_size

    def test_no_grad_returns_zeros(self, lora_model):
        """If gradients haven't been computed, should return zeros."""
        param_names = get_lora_parameter_names(lora_model)
        lora_model.zero_grad()

        # Clear all gradients
        for name, param in lora_model.named_parameters():
            param.grad = None

        grad_vec = extract_lora_gradient_vector(lora_model, param_names)
        assert torch.all(grad_vec == 0)


class TestExtractLoraGradients:
    def test_per_layer_gradients(self, lora_model, tokenizer):
        param_names = get_lora_parameter_names(lora_model)

        tokens = tokenizer("Test input", return_tensors="pt")
        tokens["labels"] = tokens["input_ids"].clone()
        lora_model.zero_grad()
        outputs = lora_model(**tokens)
        outputs.loss.backward()

        grads = extract_lora_gradients(lora_model, param_names)

        assert len(grads) > 0
        for layer_name, grad_vec in grads.items():
            assert grad_vec.dim() == 1
            assert grad_vec.dtype == torch.float32
            assert "lora" not in layer_name  # prefix should not contain lora_A/B


class TestComputePerExampleLoss:
    def test_loss_and_gradients(self, lora_model, tokenizer):
        text = "The quick brown fox"
        encoded = tokenizer(text, add_special_tokens=False)

        tokens = {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
            "labels": encoded["input_ids"],  # use input as labels
        }

        lora_model.zero_grad()
        loss = compute_per_example_loss(lora_model, tokens, torch.device("cpu"))

        assert loss.dim() == 0  # scalar
        assert loss.item() > 0  # loss should be positive

        # Gradients should be populated
        param_names = get_lora_parameter_names(lora_model)
        for name in param_names:
            param = dict(lora_model.named_parameters())[name]
            assert param.grad is not None
