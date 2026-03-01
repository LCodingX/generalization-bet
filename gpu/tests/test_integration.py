"""End-to-end integration test with GPT-2 on CPU.

Tests the full pipeline: tokenize → train with TracIn → compute DataInf → verify shapes.
Uses a tiny config (checkpoint_interval=1) for fast execution.
"""

import numpy as np
import torch
import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

from config import JobConfig
from dataset import tokenize_for_training, tokenize_examples, build_dataloader
from training import run_training_loop
from datainf import compute_datainf_scores


@pytest.fixture(scope="module")
def setup():
    """Set up model, tokenizer, and data for the integration test."""
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

    training_examples = [
        {"prompt": "What is 2+2?", "completion": "4", "category": "math"},
        {"prompt": "Capital of France?", "completion": "Paris", "category": "geography"},
        {"prompt": "What color is the sky?", "completion": "Blue", "category": "science"},
        {"prompt": "Who wrote Hamlet?", "completion": "Shakespeare", "category": "literature"},
    ]

    eval_examples_raw = [
        {"question": "What is 3+3?", "completion": "6"},
        {"question": "Capital of Germany?", "completion": "Berlin"},
    ]

    config = JobConfig(
        model_name="gpt2",
        learning_rate=1e-4,
        epochs=1,
        batch_size=2,
        lora_rank=4,
        lora_alpha=8,
        lora_dropout=0.0,
        checkpoint_interval=1,  # TracIn at every step
        max_seq_length=64,
        datainf_damping=0.1,
    )

    return model, tokenizer, training_examples, eval_examples_raw, config


class TestIntegration:
    def test_full_pipeline(self, setup):
        """Run the full pipeline: training+TracIn → DataInf → verify shapes."""
        model, tokenizer, training_examples, eval_examples_raw, config = setup
        device = torch.device("cpu")

        # Tokenize
        tokenized_training = tokenize_for_training(
            training_examples, tokenizer, config.max_seq_length,
        )
        train_loader = build_dataloader(tokenized_training, config.batch_size)
        training_tokens = tokenize_examples(
            training_examples, tokenizer, config.max_seq_length, role="train",
        )
        eval_tokens = tokenize_examples(
            eval_examples_raw, tokenizer, config.max_seq_length, role="eval",
        )

        n_train = len(training_examples)
        n_eval = len(eval_examples_raw)

        # Training + TracIn
        tracin_scores = run_training_loop(
            model=model,
            tokenizer=tokenizer,
            train_loader=train_loader,
            eval_tokens=eval_tokens,
            training_data=training_tokens,
            config=config,
            device=device,
            webhook=None,
        )

        assert tracin_scores.shape == (n_train, n_eval)
        assert tracin_scores.dtype == np.float32
        assert np.all(np.isfinite(tracin_scores))

        # DataInf
        datainf_scores = compute_datainf_scores(
            model=model,
            training_data=training_tokens,
            eval_tokens=eval_tokens,
            damping=config.datainf_damping,
            device=device,
        )

        assert datainf_scores.shape == (n_train, n_eval)
        assert datainf_scores.dtype == np.float32
        assert np.all(np.isfinite(datainf_scores))

        # Both score matrices should have non-zero entries
        assert np.any(tracin_scores != 0)
        assert np.any(datainf_scores != 0)

    def test_config_from_dict_roundtrip(self):
        """Verify config can be created from the dict format the backend sends."""
        backend_config = {
            "learning_rate": 2e-4,
            "epochs": 3,
            "batch_size": 4,
            "lora_rank": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "checkpoint_interval": 50,
            "max_seq_length": 512,
            "datainf_damping": 0.1,
        }
        config = JobConfig.from_dict(backend_config)
        assert config.learning_rate == 2e-4
        assert config.epochs == 3
