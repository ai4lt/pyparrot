"""Docker container management."""

import docker
from docker.types import Mount
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class DockerManager:
    """Manage Docker containers and images for pipelines."""

    def __init__(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise

    def build_image(
        self,
        dockerfile_path: str,
        image_name: str,
        tag: str = "latest",
        buildargs: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build a Docker image.
        
        Args:
            dockerfile_path: Path to the Dockerfile
            image_name: Name for the image
            tag: Image tag
            buildargs: Build arguments
            
        Returns:
            Image ID
        """
        try:
            image, build_logs = self.client.images.build(
                path=dockerfile_path,
                tag=f"{image_name}:{tag}",
                buildargs=buildargs or {},
            )
            logger.info(f"Built image {image_name}:{tag}")
            for log in build_logs:
                if "stream" in log:
                    logger.debug(log["stream"].strip())
            return image.id
        except Exception as e:
            logger.error(f"Failed to build image: {e}")
            raise

    def start_container(
        self,
        image_name: str,
        container_name: str,
        tag: str = "latest",
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> str:
        """Start a Docker container.
        
        Args:
            image_name: Name of the image to run
            container_name: Name for the container
            tag: Image tag
            ports: Port mappings {container_port: host_port}
            volumes: Volume mappings
            environment: Environment variables
            
        Returns:
            Container ID
        """
        try:
            container = self.client.containers.run(
                f"{image_name}:{tag}",
                name=container_name,
                ports=ports or {},
                volumes=volumes or {},
                environment=environment or {},
                detach=True,
            )
            logger.info(f"Started container {container_name} with ID {container.id}")
            return container.id
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            raise

    def stop_container(self, container_name: str) -> None:
        """Stop a running container.
        
        Args:
            container_name: Name of the container to stop
        """
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container {container_name}")
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            raise

    def remove_container(self, container_name: str, force: bool = False) -> None:
        """Remove a container.
        
        Args:
            container_name: Name of the container to remove
            force: Force removal even if running
        """
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=force)
            logger.info(f"Removed container {container_name}")
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            raise

    def get_container_logs(self, container_name: str) -> str:
        """Get logs from a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Container logs
        """
        try:
            container = self.client.containers.get(container_name)
            return container.logs(decode=True)
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            raise

    def list_containers(self, all: bool = False) -> List[Dict]:
        """List containers.
        
        Args:
            all: If True, include stopped containers
            
        Returns:
            List of container info
        """
        containers = self.client.containers.list(all=all)
        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags,
            }
            for c in containers
        ]

    def container_exists(self, container_name: str) -> bool:
        """Check if a container exists.
        
        Args:
            container_name: Name of the container
            
        Returns:
            True if container exists
        """
        try:
            self.client.containers.get(container_name)
            return True
        except docker.errors.NotFound:
            return False

    def image_exists(self, image_name: str, tag: str = "latest") -> bool:
        """Check if an image exists.
        
        Args:
            image_name: Name of the image
            tag: Image tag
            
        Returns:
            True if image exists
        """
        try:
            self.client.images.get(f"{image_name}:{tag}")
            return True
        except docker.errors.ImageNotFound:
            return False
