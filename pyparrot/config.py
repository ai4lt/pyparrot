"""Configuration management for PyParrot pipelines."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field
import yaml
import getpass
import bcrypt


class SpeechConfig(BaseModel):
    """Speech component configuration."""
    model: str = Field(default="whisper", description="Speech model to use")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    language: str = Field(default="en", description="Language code")
    device: str = Field(default="cpu", description="Device to run on (cpu/cuda)")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "whisper",
                "sample_rate": 16000,
                "language": "en",
                "device": "cpu",
            }
        }


class LLMConfig(BaseModel):
    """LLM component configuration."""
    model: str = Field(default="gpt-3.5-turbo", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, description="Maximum tokens to generate")
    api_key: Optional[str] = Field(default=None, description="API key for the LLM")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 256,
            }
        }


class DockerConfig(BaseModel):
    """Docker configuration."""
    image_name: str = Field(default="pyparrot-pipeline", description="Docker image name")
    base_image: str = Field(default="python:3.11-slim", description="Base Docker image")
    port: int = Field(default=8000, description="Port to expose")
    volumes: Optional[Dict[str, str]] = Field(default=None, description="Volume mappings")
    environment: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")

    class Config:
        json_schema_extra = {
            "example": {
                "image_name": "pyparrot-pipeline",
                "base_image": "python:3.11-slim",
                "port": 8000,
            }
        }


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    name: str = Field(description="Pipeline name")
    version: str = Field(default="1.0", description="Pipeline version")
    backends: str = Field(default="local", description="Backend integration mode: local, distributed, or external")
    backend_components: List[str] = Field(default_factory=list, description="Required backend components for this pipeline type")
    stt_backend_url: Optional[str] = Field(default=None, description="External backend URL for speech-to-text (used when backends=external)")
    mt_backend_url: Optional[str] = Field(default=None, description="External backend URL for machine translation (used when backends=external)")
    tts_backend_url: Optional[str] = Field(default=None, description="External backend URL for text-to-speech (used when backends=external)")
    tts_backend_engine: Optional[str] = Field(default=None, description="TTS backend engine (e.g., tts-kokoro) for local/distributed modes")
    tts_backend_gpu: Optional[str] = Field(default=None, description="GPU device ID for TTS backend (e.g., '0', '1', or None for CPU)")
    summarizer_backend_url: Optional[str] = Field(default=None, description="External backend URL for summarization")
    text_structurer_online_url: Optional[str] = Field(default=None, description="External backend URL for text structurer online model")
    text_structurer_offline_url: Optional[str] = Field(default=None, description="External backend URL for text structurer offline model")
    llm_backend_url: Optional[str] = Field(default=None, description="External backend URL for LLM")
    llm_backend_engine: Optional[str] = Field(default=None, description="LLM backend engine (e.g., huggingface-tgi) for local/distributed modes")
    llm_backend_model: Optional[str] = Field(default=None, description="LLM backend model ID for local/distributed modes")
    llm_backend_gpu: Optional[str] = Field(default=None, description="GPU device ID for LLM backend (e.g., '0', '1', or None for CPU)")
    stt_backend_engine: str = Field(default="faster-whisper", description="STT backend engine (faster-whisper) for local/distributed modes")
    stt_backend_model: str = Field(default="large-v2", description="STT model (large-v2) for local/distributed modes")
    stt_backend_gpu: Optional[str] = Field(default=None, description="GPU device ID for STT backend (e.g., '0', '1', or None for CPU)")
    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    description: Optional[str] = Field(default=None, description="Pipeline description")
    admin_password: Optional[str] = Field(default=None, description="Admin password")
    domain: str = Field(default="pyparrot.localhost", description="Domain for the pipeline")
    external_port: Optional[int] = Field(default=None, description="Externally reachable port when behind a reverse proxy")
    external_https_port: Optional[int] = Field(default=None, description="Externally reachable HTTPS port when behind a reverse proxy")
    enable_https: bool = Field(default=False, description="Enable HTTPS support")
    https_port: int = Field(default=443, description="Port for HTTPS traffic")
    acme_email: Optional[str] = Field(default=None, description="Email for Let's Encrypt ACME registration")
    acme_staging: bool = Field(default=False, description="Use Let's Encrypt staging server (for testing)")
    force_https_redirect: bool = Field(default=False, description="Force redirect HTTP to HTTPS")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-pipeline",
                "version": "1.0",
                "speech": {
                    "model": "whisper",
                    "sample_rate": 16000,
                },
                "llm": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                },
                "docker": {
                    "image_name": "pyparrot-pipeline",
                    "base_image": "python:3.11-slim",
                    "port": 8000,
                },
            }
        }

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PipelineConfig":
        """Load configuration from a YAML file.
        
        Args:
            yaml_path: Path to the YAML configuration file
            
        Returns:
            PipelineConfig instance
        """
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """Create config from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            PipelineConfig instance
        """
        return cls(**data)

    def to_yaml(self, output_path: str) -> None:
        """Save configuration to a YAML file.
        
        Args:
            output_path: Path to save the YAML file
        """
        with open(output_path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return self.model_dump()

    def save_admin_password(self, config_dir: str) -> None:
        """Save admin password to dex.env file in dex subdirectory with bcrypt encoding.
        
        Args:
            config_dir: Configuration directory path
        """
        if not self.admin_password:
            return
            
        dex_dir = Path(config_dir) / "dex"
        dex_dir.mkdir(parents=True, exist_ok=True)
        
        # Encode password using bcrypt
        password_bytes = self.admin_password.encode('utf-8')
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=10)).decode('utf-8')
        
        env_file = dex_dir / "dex.env"
        with open(env_file, "w") as f:
            f.write(f"ADMIN_PASSHASH='{hashed_password}'\n")
        env_file.chmod(0o600)  # Restrict permissions for security
