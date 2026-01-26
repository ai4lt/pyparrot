"""Tests for evaluator."""

import pytest
import json
import tempfile
from pathlib import Path
from pyparrot.evaluator import Evaluator, EvaluationResult


def test_evaluation_result():
    """Test EvaluationResult creation."""
    result = EvaluationResult("test-pipeline", "test.json")
    assert result.pipeline_name == "test-pipeline"
    assert result.dataset_path == "test.json"


def test_evaluation_result_add_metric():
    """Test adding metrics to result."""
    result = EvaluationResult("test-pipeline", "test.json")
    result.add_metric("accuracy", 0.95)
    assert result.metrics["accuracy"] == 0.95


def test_evaluation_result_add_sample():
    """Test adding samples to result."""
    result = EvaluationResult("test-pipeline", "test.json")
    sample = {"input": "test", "output": "test"}
    result.add_sample(sample)
    assert len(result.samples) == 1


def test_evaluation_result_to_dict():
    """Test converting result to dict."""
    result = EvaluationResult("test-pipeline", "test.json")
    result.add_metric("accuracy", 0.95)
    result.add_sample({"input": "test"})
    
    result_dict = result.to_dict()
    assert result_dict["pipeline"] == "test-pipeline"
    assert result_dict["metrics"]["accuracy"] == 0.95
    assert len(result_dict["samples"]) == 1


def test_evaluator_load_json_dataset():
    """Test loading JSON dataset."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_path = Path(tmpdir) / "dataset.json"
        data = [
            {"input": "hello", "expected": "world"},
            {"input": "test", "expected": "data"},
        ]
        with open(dataset_path, "w") as f:
            json.dump(data, f)

        evaluator = Evaluator("test-pipeline")
        samples = evaluator.load_dataset(str(dataset_path))
        assert len(samples) == 2


def test_evaluator_load_jsonl_dataset():
    """Test loading JSONL dataset."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_path = Path(tmpdir) / "dataset.jsonl"
        with open(dataset_path, "w") as f:
            f.write(json.dumps({"input": "hello", "expected": "world"}) + "\n")
            f.write(json.dumps({"input": "test", "expected": "data"}) + "\n")

        evaluator = Evaluator("test-pipeline")
        samples = evaluator.load_dataset(str(dataset_path))
        assert len(samples) == 2


def test_evaluator_evaluate():
    """Test evaluation workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_path = Path(tmpdir) / "dataset.json"
        output_path = Path(tmpdir) / "results.json"
        
        data = [
            {"input": "hello", "expected": "world"},
        ]
        with open(dataset_path, "w") as f:
            json.dump(data, f)

        evaluator = Evaluator("test-pipeline")
        result = evaluator.evaluate(
            str(dataset_path),
            output_path=str(output_path),
        )

        assert result.metrics["total_samples"] == 1
        assert output_path.exists()
