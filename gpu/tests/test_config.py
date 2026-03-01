from config import JobConfig


class TestJobConfig:
    def test_defaults(self):
        cfg = JobConfig()
        assert cfg.learning_rate == 2e-4
        assert cfg.epochs == 3
        assert cfg.batch_size == 4
        assert cfg.lora_rank == 16
        assert cfg.lora_alpha == 32
        assert cfg.lora_dropout == 0.05
        assert cfg.checkpoint_interval == 50
        assert cfg.max_seq_length == 512
        assert cfg.datainf_damping == 0.1

    def test_from_dict_with_all_keys(self):
        d = {
            "model_name": "gpt2",
            "learning_rate": 1e-3,
            "epochs": 5,
            "batch_size": 8,
            "lora_rank": 32,
            "lora_alpha": 64,
            "lora_dropout": 0.1,
            "checkpoint_interval": 100,
            "max_seq_length": 1024,
            "datainf_damping": 0.5,
        }
        cfg = JobConfig.from_dict(d)
        assert cfg.model_name == "gpt2"
        assert cfg.learning_rate == 1e-3
        assert cfg.epochs == 5
        assert cfg.lora_rank == 32

    def test_from_dict_with_defaults(self):
        cfg = JobConfig.from_dict({"model_name": "gpt2"})
        assert cfg.model_name == "gpt2"
        assert cfg.learning_rate == 2e-4  # default
        assert cfg.epochs == 3  # default

    def test_from_dict_ignores_unknown_keys(self):
        cfg = JobConfig.from_dict({"model_name": "gpt2", "unknown_key": 42})
        assert cfg.model_name == "gpt2"

    def test_from_dict_empty(self):
        cfg = JobConfig.from_dict({})
        assert cfg.model_name == "meta-llama/Llama-2-7b-hf"
