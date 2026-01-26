"""Pipeline management and orchestration."""

from typing import Dict, Optional
from .config import PipelineConfig
from .docker_manager import DockerManager
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Pipeline:
    """Manage speech and LLM pipeline."""

    def __init__(self, config: PipelineConfig):
        """Initialize pipeline with configuration.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.docker_manager = DockerManager()
        self.container_id: str = None

    def get_dockerfile(self) -> str:
        """Generate Dockerfile for the pipeline.
        
        Returns:
            Dockerfile content
        """
        dockerfile = f"""FROM {self.config.docker.base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
"""
        if self.config.docker.environment:
            for key, value in self.config.docker.environment.items():
                dockerfile += f"ENV {key}={value}\n"

        dockerfile += f"""
# Expose port
EXPOSE {self.config.docker.port}

# Default command
CMD ["python", "-m", "pyparrot.server"]
"""
        return dockerfile

    def create_requirements_file(self, output_path: str = "requirements.txt") -> None:
        """Create requirements.txt for the pipeline.
        
        Args:
            output_path: Path to save requirements.txt
        """
        requirements = [
            "click>=8.1.0",
            "pydantic>=2.0.0",
            "pyyaml>=6.0",
            "docker>=6.0.0",
        ]

        # Add speech component dependencies
        if self.config.speech.model == "whisper":
            requirements.append("openai-whisper>=20230314")

        # Add LLM component dependencies
        if "gpt" in self.config.llm.model.lower():
            requirements.append("openai>=1.0.0")

        with open(output_path, "w") as f:
            f.write("\n".join(requirements) + "\n")

        logger.info(f"Created requirements file: {output_path}")

    def build(self, dockerfile_dir: str = None) -> str:
        """Build Docker image for the pipeline.
        
        Args:
            dockerfile_dir: Directory containing Dockerfile
            
        Returns:
            Image ID
        """
        if dockerfile_dir is None:
            dockerfile_dir = Path.cwd()

        # Generate Dockerfile
        dockerfile_path = Path(dockerfile_dir) / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(self.get_dockerfile())

        # Create requirements file
        self.create_requirements_file(str(Path(dockerfile_dir) / "requirements.txt"))

        # Build image
        image_id = self.docker_manager.build_image(
            dockerfile_path=str(dockerfile_dir),
            image_name=self.config.docker.image_name,
            tag=self.config.version,
        )

        logger.info(f"Built pipeline image: {image_id}")
        return image_id

    def start(self) -> str:
        """Start the pipeline container.
        
        Returns:
            Container ID
        """
        ports = {self.config.docker.port: self.config.docker.port}
        volumes = self.config.docker.volumes or {}
        environment = self.config.docker.environment or {}

        # Add pipeline-specific environment variables
        environment.update({
            "PIPELINE_NAME": self.config.name,
            "SPEECH_MODEL": self.config.speech.model,
            "SPEECH_SAMPLE_RATE": str(self.config.speech.sample_rate),
            "LLM_MODEL": self.config.llm.model,
            "LLM_TEMPERATURE": str(self.config.llm.temperature),
        })

        self.container_id = self.docker_manager.start_container(
            image_name=self.config.docker.image_name,
            container_name=self.config.name,
            tag=self.config.version,
            ports=ports,
            volumes=volumes,
            environment=environment,
        )

        return self.container_id

    def stop(self) -> None:
        """Stop the pipeline container."""
        self.docker_manager.stop_container(self.config.name)
        self.container_id = None

    def status(self) -> Dict:
        """Get pipeline status.
        
        Returns:
            Pipeline status information
        """
        if self.docker_manager.container_exists(self.config.name):
            try:
                logs = self.docker_manager.get_container_logs(self.config.name)
                return {
                    "name": self.config.name,
                    "status": "running",
                    "logs": logs[-500:] if len(logs) > 500 else logs,
                }
            except Exception as e:
                return {
                    "name": self.config.name,
                    "status": "error",
                    "error": str(e),
                }
        else:
            return {
                "name": self.config.name,
                "status": "not_running",
            }
