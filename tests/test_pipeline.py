"""Tests for pipeline."""

import pytest
from pyparrot.pipeline import Pipeline
from pyparrot.config import PipelineConfig


def test_pipeline_creation():
    """Test Pipeline creation."""
    config = PipelineConfig(name="test-pipeline")
    pipeline = Pipeline(config)
    assert pipeline.config.name == "test-pipeline"


def test_pipeline_get_dockerfile():
    """Test Dockerfile generation."""
    config = PipelineConfig(name="test-pipeline")
    pipeline = Pipeline(config)
    dockerfile = pipeline.get_dockerfile()
    
    assert "FROM python:3.11-slim" in dockerfile
    assert "WORKDIR /app" in dockerfile
    assert "ffmpeg" in dockerfile
    assert f"EXPOSE {config.docker.port}" in dockerfile


def test_pipeline_status():
    """Test getting pipeline status."""
    config = PipelineConfig(name="test-pipeline")
    pipeline = Pipeline(config)
    status = pipeline.status()
    
    assert "name" in status
    assert "status" in status
    assert status["name"] == "test-pipeline"
