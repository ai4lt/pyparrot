"""PyParrot - CLI for Docker pipelines of speech and LLM components."""

__version__ = "0.1.0"
__author__ = "Your Name"

from .config import PipelineConfig, SpeechConfig, LLMConfig, DockerConfig
from .pipeline import Pipeline
from .docker_manager import DockerManager
from .evaluator import Evaluator

__all__ = [
    "PipelineConfig",
    "SpeechConfig",
    "LLMConfig",
    "DockerConfig",
    "Pipeline",
    "DockerManager",
    "Evaluator",
]
