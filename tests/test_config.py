"""Tests for configuration management."""

import pytest
from pyparrot.config import PipelineConfig, SpeechConfig, LLMConfig, DockerConfig
import tempfile
from pathlib import Path


def test_speech_config():
    """Test SpeechConfig creation."""
    config = SpeechConfig(model="whisper", sample_rate=16000)
    assert config.model == "whisper"
    assert config.sample_rate == 16000


def test_llm_config():
    """Test LLMConfig creation."""
    config = LLMConfig(model="gpt-3.5-turbo", temperature=0.7)
    assert config.model == "gpt-3.5-turbo"
    assert config.temperature == 0.7


def test_docker_config():
    """Test DockerConfig creation."""
    config = DockerConfig(image_name="test-image", port=8000)
    assert config.image_name == "test-image"
    assert config.port == 8000


def test_pipeline_config():
    """Test PipelineConfig creation."""
    config = PipelineConfig(name="test-pipeline")
    assert config.name == "test-pipeline"
    assert config.speech.model == "whisper"
    assert config.llm.model == "gpt-3.5-turbo"


def test_pipeline_config_to_dict():
    """Test converting PipelineConfig to dictionary."""
    config = PipelineConfig(name="test-pipeline")
    config_dict = config.to_dict()
    assert config_dict["name"] == "test-pipeline"
    assert "speech" in config_dict
    assert "llm" in config_dict
    assert "docker" in config_dict


def test_pipeline_config_from_dict():
    """Test creating PipelineConfig from dictionary."""
    data = {
        "name": "test-pipeline",
        "speech": {"model": "whisper"},
        "llm": {"model": "gpt-3.5-turbo"},
    }
    config = PipelineConfig.from_dict(data)
    assert config.name == "test-pipeline"


def test_pipeline_config_yaml_roundtrip():
    """Test YAML save and load roundtrip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = PipelineConfig(name="test-pipeline")
        yaml_path = Path(tmpdir) / "config.yaml"

        # Save to YAML
        config.to_yaml(str(yaml_path))
        assert yaml_path.exists()

        # Load from YAML
        loaded_config = PipelineConfig.from_yaml(str(yaml_path))
        assert loaded_config.name == config.name
        assert loaded_config.speech.model == config.speech.model
