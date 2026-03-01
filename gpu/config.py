from dataclasses import dataclass


@dataclass
class JobConfig:
    """Hyperparameters for fine-tuning + influence computation.

    Defaults match backend Hyperparameters model at backend/app/models.py.
    """

    model_name: str = "meta-llama/Llama-2-7b-hf"
    learning_rate: float = 2e-4
    epochs: int = 3
    batch_size: int = 4
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    checkpoint_interval: int = 50
    max_seq_length: int = 512
    datainf_damping: float = 0.1

    @classmethod
    def from_dict(cls, d: dict) -> "JobConfig":
        """Create a JobConfig from a dict, using defaults for missing keys."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)
