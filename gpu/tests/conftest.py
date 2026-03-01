import sys
from pathlib import Path

import pytest

# Add gpu/ to sys.path so tests can import modules directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_training_examples():
    """Sample training data in the format returned by download_and_parse_dataset."""
    return [
        {"prompt": "What is 2+2?", "completion": "4", "category": "math"},
        {"prompt": "Capital of France?", "completion": "Paris", "category": "geography"},
        {"prompt": "What color is the sky?", "completion": "Blue", "category": "science"},
        {"prompt": "Who wrote Hamlet?", "completion": "Shakespeare", "category": "literature"},
    ]


@pytest.fixture
def sample_eval_examples():
    """Sample eval data matching the EvalExample model."""
    return [
        {"question": "What is 3+3?", "completion": "6"},
        {"question": "Capital of Germany?", "completion": "Berlin"},
    ]
