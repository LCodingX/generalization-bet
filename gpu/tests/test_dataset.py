import json

import pytest
from transformers import AutoTokenizer

from dataset import (
    download_and_parse_dataset,
    tokenize_for_training,
    tokenize_examples,
    build_dataloader,
)


@pytest.fixture(scope="module")
def tokenizer():
    tok = AutoTokenizer.from_pretrained("gpt2")
    tok.pad_token = tok.eos_token
    tok.pad_token_id = tok.eos_token_id
    return tok


class TestDownloadAndParse:
    def test_parse_jsonl(self, tmp_path, monkeypatch):
        """Test JSONL parsing (mock the HTTP download)."""
        jsonl_content = "\n".join([
            json.dumps({"prompt": "Q1", "completion": "A1", "category": "cat1"}),
            json.dumps({"prompt": "Q2", "completion": "A2"}),
        ])

        import httpx

        class MockResponse:
            status_code = 200
            text = jsonl_content

            def raise_for_status(self):
                pass

        monkeypatch.setattr(httpx, "get", lambda *a, **kw: MockResponse())

        examples = download_and_parse_dataset("http://fake-url.com/data.jsonl")
        assert len(examples) == 2
        assert examples[0]["prompt"] == "Q1"
        assert examples[0]["category"] == "cat1"
        assert examples[1]["category"] == "default"  # missing category → default


class TestTokenizeForTraining:
    def test_label_masking(self, tokenizer, sample_training_examples):
        """Prompt tokens should be masked with -100 in labels."""
        tokenized = tokenize_for_training(sample_training_examples, tokenizer, max_seq_len=128)

        assert len(tokenized) == 4
        for item in tokenized:
            assert len(item["input_ids"]) == 128
            assert len(item["attention_mask"]) == 128
            assert len(item["labels"]) == 128

            # First token(s) should be -100 (prompt masking)
            assert item["labels"][0] == -100

            # At least some labels should not be -100 (completion tokens)
            non_masked = [l for l in item["labels"] if l != -100]
            assert len(non_masked) > 0

    def test_padding(self, tokenizer):
        """Short sequences should be padded to max_seq_len."""
        examples = [{"prompt": "Hi", "completion": "Hello", "category": "test"}]
        tokenized = tokenize_for_training(examples, tokenizer, max_seq_len=64)

        item = tokenized[0]
        # Should have padding at the end
        assert item["attention_mask"][-1] == 0
        assert item["labels"][-1] == -100


class TestTokenizeExamples:
    def test_eval_tokenization(self, tokenizer, sample_eval_examples):
        tokenized = tokenize_examples(sample_eval_examples, tokenizer, max_seq_len=128, role="eval")
        assert len(tokenized) == 2
        for item in tokenized:
            assert len(item["input_ids"]) == 128
            assert item["labels"][0] == -100  # prompt masked

    def test_train_tokenization(self, tokenizer, sample_training_examples):
        tokenized = tokenize_examples(sample_training_examples, tokenizer, max_seq_len=128, role="train")
        assert len(tokenized) == 4


class TestBuildDataloader:
    def test_dataloader_shape(self, tokenizer, sample_training_examples):
        tokenized = tokenize_for_training(sample_training_examples, tokenizer, max_seq_len=64)
        loader = build_dataloader(tokenized, batch_size=2)

        batch = next(iter(loader))
        input_ids, attention_mask, labels = batch
        assert input_ids.shape == (2, 64)
        assert attention_mask.shape == (2, 64)
        assert labels.shape == (2, 64)
