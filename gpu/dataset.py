import json
import logging

import httpx
import torch
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = "### Question:\n{prompt}\n\n### Answer:\n{completion}"


def download_and_parse_dataset(url: str) -> list[dict]:
    """Download a JSONL file and return list of {prompt, completion, category} dicts."""
    resp = httpx.get(url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()

    examples = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        examples.append({
            "prompt": obj["prompt"],
            "completion": obj["completion"],
            "category": obj.get("category", "default"),
        })

    logger.info(f"Downloaded {len(examples)} training examples")
    return examples


def tokenize_for_training(
    examples: list[dict],
    tokenizer,
    max_seq_len: int,
) -> list[dict]:
    """Tokenize training examples with prompt-masked labels.

    The full text is: "### Question:\n{prompt}\n\n### Answer:\n{completion}<eos>"
    Labels for prompt tokens are set to -100 so loss is only computed on the completion.
    """
    tokenized = []
    for ex in examples:
        prompt_text = f"### Question:\n{ex['prompt']}\n\n### Answer:\n"
        full_text = prompt_text + ex["completion"] + tokenizer.eos_token

        prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
        full_ids = tokenizer.encode(full_text, add_special_tokens=False)

        # Truncate to max_seq_len
        full_ids = full_ids[:max_seq_len]
        prompt_len = min(len(prompt_ids), len(full_ids))

        # Labels: -100 for prompt, token ids for completion
        labels = [-100] * prompt_len + full_ids[prompt_len:]

        # Pad to max_seq_len
        pad_len = max_seq_len - len(full_ids)
        input_ids = full_ids + [tokenizer.pad_token_id or 0] * pad_len
        attention_mask = [1] * len(full_ids) + [0] * pad_len
        labels = labels + [-100] * pad_len

        tokenized.append({
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        })

    return tokenized


def tokenize_examples(
    examples: list[dict],
    tokenizer,
    max_seq_len: int,
    role: str = "eval",
) -> list[dict]:
    """Tokenize individual examples for per-example gradient computation.

    For eval: uses question + completion.
    For train: uses prompt + completion.
    """
    tokenized = []
    for ex in examples:
        if role == "eval":
            prompt_text = f"### Question:\n{ex['question']}\n\n### Answer:\n"
            full_text = prompt_text + ex["completion"] + tokenizer.eos_token
        else:
            prompt_text = f"### Question:\n{ex['prompt']}\n\n### Answer:\n"
            full_text = prompt_text + ex["completion"] + tokenizer.eos_token

        prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
        full_ids = tokenizer.encode(full_text, add_special_tokens=False)

        full_ids = full_ids[:max_seq_len]
        prompt_len = min(len(prompt_ids), len(full_ids))

        labels = [-100] * prompt_len + full_ids[prompt_len:]

        pad_len = max_seq_len - len(full_ids)
        input_ids = full_ids + [tokenizer.pad_token_id or 0] * pad_len
        attention_mask = [1] * len(full_ids) + [0] * pad_len
        labels = labels + [-100] * pad_len

        tokenized.append({
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        })

    return tokenized


def build_dataloader(
    tokenized_data: list[dict],
    batch_size: int,
) -> DataLoader:
    """Build a DataLoader from tokenized data."""
    input_ids = torch.tensor([t["input_ids"] for t in tokenized_data], dtype=torch.long)
    attention_mask = torch.tensor([t["attention_mask"] for t in tokenized_data], dtype=torch.long)
    labels = torch.tensor([t["labels"] for t in tokenized_data], dtype=torch.long)

    dataset = TensorDataset(input_ids, attention_mask, labels)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)
