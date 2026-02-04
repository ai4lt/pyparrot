"""Manage docker-compose templates and merging."""

from pathlib import Path
from typing import Dict, Any, List
import yaml
import logging
from jinja2 import Template

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manage docker-compose templates for different pipeline types."""

    # Mapping of pipeline types to component templates
    PIPELINE_TEMPLATES = {
        "end2end": ["middleware", "asr"],
        "cascaded": ["middleware", "asr", "mt"],
        "LT.2025": ["middleware", "asr", "mt", "tts", "dialog", "markup"],
        "dialog": ["middleware", "asr", "tts", "dialog"],
        "BOOM": ["middleware", "asr"],
    }

    def __init__(self):
        """Initialize template manager."""
        self.template_dir = Path(__file__).parent / "templates" / "docker"
        self.traefik_template_dir = Path(__file__).parent / "templates" / "traefik"
        self.dex_template_dir = Path(__file__).parent / "templates" / "dex"

    def get_template_path(self, component: str) -> Path:
        """Get path to a component template.
        
        Args:
            component: Component name (middleware, asr, mt)
            
        Returns:
            Path to the template file
        """
        # Check for .tpl version first
        tpl_path = self.template_dir / f"{component}.yaml.tpl"
        if tpl_path.exists():
            return tpl_path
        return self.template_dir / f"{component}.yaml"

    def load_template(self, component: str, domain: str = None) -> Dict[str, Any]:
        """Load a single template file.
        
        Args:
            component: Component name
            domain: Domain name (used for conditional rendering)
            
        Returns:
            Parsed YAML template as dictionary
        """
        template_path = self.get_template_path(component)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, "r") as f:
            content = f.read()
        
        # If it's a .tpl file, render it with Jinja2
        if template_path.suffix == ".tpl":
            # Determine if it's a localhost domain
            is_localhost = domain and ".localhost" in domain
            
            template = Template(content)
            content = template.render(IS_LOCALHOST_DOMAIN=is_localhost)
        
        return yaml.safe_load(content)

    def merge_templates(self, components: List[str], domain: str = None) -> Dict[str, Any]:
        """Merge multiple component templates into a single docker-compose file.
        
        Args:
            components: List of component names to merge
            domain: Domain name (used for conditional rendering)
            
        Returns:
            Merged docker-compose configuration
        """
        if not components:
            raise ValueError("At least one component must be specified")

        # Load base template from first component
        merged = self.load_template(components[0], domain)
        
        # Merge remaining components
        for component in components[1:]:
            template = self.load_template(component, domain)
            self._merge_services(merged, template)
        
        logger.info(f"Merged templates for components: {', '.join(components)}")
        return merged

    def _merge_services(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """Merge services from overlay template into base template.
        
        Args:
            base: Base docker-compose configuration (modified in place)
            overlay: Overlay docker-compose configuration to merge
        """
        if "services" not in base:
            base["services"] = {}
        
        if "services" in overlay:
            base["services"].update(overlay["services"])
        
        # Merge networks (avoid duplication)
        if "networks" in overlay and "networks" in base:
            for network_name, network_config in overlay["networks"].items():
                if network_name not in base["networks"]:
                    base["networks"][network_name] = network_config
        
        # Merge volumes (avoid duplication)
        if "volumes" in overlay:
            if "volumes" not in base:
                base["volumes"] = {}
            for volume_name, volume_config in overlay["volumes"].items():
                if volume_name not in base["volumes"]:
                    base["volumes"][volume_name] = volume_config

    def generate_compose_file(self, pipeline_type: str, domain: str = None, backends_mode: str = "local", 
                             stt_backend_engine: str = "faster-whisper", stt_backend_gpu: str = None,
                             repo_root: str = None) -> Dict[str, Any]:
        """Generate docker-compose configuration for a pipeline type.
        
        Args:
            pipeline_type: Type of pipeline (end2end, cascaded, etc.)
            domain: Domain name (used for conditional rendering)
            backends_mode: Backend integration mode (local, distributed, external)
            stt_backend_engine: STT backend engine (e.g., faster-whisper)
            stt_backend_gpu: GPU device ID for local/distributed backends
            repo_root: Repository root path for locating backend services
            
        Returns:
            Complete docker-compose configuration
        """
        if pipeline_type not in self.PIPELINE_TEMPLATES:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        components = self.PIPELINE_TEMPLATES[pipeline_type]
        composed = self.merge_templates(components, domain)
        
        # Add backend services for local/distributed modes
        if backends_mode in ["local", "distributed"]:
            backend_compose = self._load_backend_compose(stt_backend_engine, stt_backend_gpu, repo_root)
            if backend_compose:
                self._merge_services(composed, backend_compose)
        
        return composed

    def _load_backend_compose(self, backend_engine: str, gpu_device: str = None, repo_root: str = None) -> Dict[str, Any]:
        """Load backend service configuration.
        
        Args:
            backend_engine: Backend engine name (e.g., faster-whisper, vllm)
            gpu_device: GPU device ID (e.g., '0', '1', or None for CPU)
            repo_root: Repository root path
            
        Returns:
            Backend docker-compose configuration or None if not found
        """
        # Map backend engines to their directory names
        backend_dirs = {
            "faster-whisper": "faster-whisper",
            "vllm": "vllmserver"
        }
        
        if backend_engine not in backend_dirs:
            logger.warning(f"Backend engine '{backend_engine}' not yet supported")
            return None
        
        backend_dir_name = backend_dirs[backend_engine]
        
        # Try to find the backend docker-compose
        if repo_root:
            backend_path = Path(repo_root) / "backends" / backend_dir_name / "docker-compose.yaml"
        else:
            # Fallback: calculate from template_dir
            backend_path = self.template_dir.parent.parent / "backends" / backend_dir_name / "docker-compose.yaml"
        
        if not backend_path.exists():
            logger.warning(f"Backend compose file not found: {backend_path}")
            return None
        
        with open(backend_path, "r") as f:
            backend_config = yaml.safe_load(f)
        
        # Modify backend services for integration
        if "services" in backend_config:
            for service_name, service in backend_config["services"].items():
                # Update build path to use BACKENDS_DIR
                if "build" in service and service["build"] == ".":
                    if repo_root:
                        service["build"] = "${BACKENDS_DIR}/" + backend_dir_name
                    else:
                        service["build"] = str(backend_path.parent)
                
                # Remove external port exposure (keep internal only)
                if "ports" in service:
                    del service["ports"]
                
                # Add to LTPipeline network
                if "networks" not in service:
                    service["networks"] = ["LTPipeline"]
                elif isinstance(service["networks"], list) and "LTPipeline" not in service["networks"]:
                    service["networks"].append("LTPipeline")
                
                # Modify GPU settings if provided
                # For vllm backend, only apply to vllm-server service, not vllm service
                should_apply_gpu = gpu_device is not None and not (backend_engine == "vllm" and service_name == "vllm")
                if should_apply_gpu:
                    if "environment" in service:
                        # Handle environment as list (YAML format with dashes)
                        if isinstance(service["environment"], list):
                            # Update NVIDIA_VISIBLE_DEVICES or CUDA_VISIBLE_DEVICES in list
                            updated = False
                            for i, env_var in enumerate(service["environment"]):
                                if isinstance(env_var, str):
                                    if env_var.startswith("NVIDIA_VISIBLE_DEVICES=") or env_var.startswith("CUDA_VISIBLE_DEVICES="):
                                        service["environment"][i] = f"NVIDIA_VISIBLE_DEVICES={gpu_device}"
                                        updated = True
                                        break
                            if not updated:
                                service["environment"].append(f"CUDA_VISIBLE_DEVICES={gpu_device}")
                        # Handle environment as dict
                        else:
                            service["environment"]["CUDA_VISIBLE_DEVICES"] = gpu_device
                    else:
                        service["environment"] = {"CUDA_VISIBLE_DEVICES": gpu_device}
        
        # Ensure networks section exists
        if "networks" not in backend_config:
            backend_config["networks"] = {}
        if "LTPipeline" not in backend_config["networks"]:
            backend_config["networks"]["LTPipeline"] = {}
        
        logger.info(f"Loaded backend configuration from {backend_path}")
        return backend_config

    def save_compose_file(self, compose_config: Dict[str, Any], output_path: str) -> None:
        """Save docker-compose configuration to file.
        
        Args:
            compose_config: Docker-compose configuration dictionary
            output_path: Path to save the file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved docker-compose file: {output_file}")

    def generate_traefik_files(self, config_name: str, encrypted_admin_password: str, output_dir: str) -> None:
        """Generate traefik configuration files from templates.
        
        Args:
            config_name: Configuration name for the pipeline label
            encrypted_admin_password: Bcrypt encrypted admin password
            output_dir: Directory to save the generated traefik files
        """
        traefik_dir = Path(output_dir) / "traefik"
        traefik_dir.mkdir(parents=True, exist_ok=True)
        
        # Create auth subdirectory
        auth_dir = traefik_dir / "auth"
        auth_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate traefik.yaml
        traefik_template_path = self.traefik_template_dir / "traefik.yaml.tpl"
        if traefik_template_path.exists():
            with open(traefik_template_path, "r") as f:
                traefik_content = f.read()
            
            # Replace CONFIG_NAME with actual config name
            traefik_content = traefik_content.replace("CONFIG_NAME", config_name)
            
            traefik_file = traefik_dir / "traefik.yaml"
            with open(traefik_file, "w") as f:
                f.write(traefik_content)
            
            logger.info(f"Generated traefik config: {traefik_file}")
        
        # Generate basicauth.txt
        basicauth_template_path = self.traefik_template_dir / "basicauth.txt.tpl"
        if basicauth_template_path.exists():
            with open(basicauth_template_path, "r") as f:
                basicauth_content = f.read()
            
            # Replace ENCRYPTED_ADMIN_PASSWORD with actual encrypted password
            basicauth_content = basicauth_content.replace("ENCRYPTED_ADMIN_PASSWORD", encrypted_admin_password)
            
            basicauth_file = auth_dir / "basicauth.txt"
            with open(basicauth_file, "w") as f:
                f.write(basicauth_content)
            
            # Set readable permissions (owner rw, group and others read)
            basicauth_file.chmod(0o644)
            logger.info(f"Generated basicauth file: {basicauth_file}")

    def generate_dex_config(self, output_dir: str) -> None:
        """Generate dex configuration file from template.
        
        Args:
            output_dir: Directory to save the generated dex config
        """
        dex_dir = Path(output_dir) / "dex"
        dex_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate dex.yaml
        dex_template_path = self.dex_template_dir / "dex.yaml.tpl"
        if dex_template_path.exists():
            with open(dex_template_path, "r") as f:
                dex_content = f.read()
            
            dex_file = dex_dir / "dex.yaml"
            with open(dex_file, "w") as f:
                f.write(dex_content)
            
            logger.info(f"Generated dex config: {dex_file}")

    def generate_traefik_rules(self, output_dir: str) -> None:
        """Generate traefik rules configuration file from template.
        
        Args:
            output_dir: Directory to save the generated rules.ini
        """
        traefik_dir = Path(output_dir) / "traefik"
        traefik_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate rules.ini
        rules_template_path = self.traefik_template_dir / "rules.ini.tpl"
        if rules_template_path.exists():
            with open(rules_template_path, "r") as f:
                rules_content = f.read()
            
            rules_file = traefik_dir / "rules.ini"
            with open(rules_file, "w") as f:
                f.write(rules_content)
            
            logger.info(f"Generated traefik rules: {rules_file}")

    def generate_env_file(self, output_dir: str, pipeline_name: str, domain: str,
                         http_port: int, frontend_theme: str, hf_token: str = None,
                         external_port: int = None, repo_root: str = None,
                         backends: str = "local", stt_backend_url: str = None,
                         mt_backend_url: str = None, stt_backend_engine: str = None) -> None:
        """Generate .env file for docker-compose with environment variables.
        
        Args:
            output_dir: Directory to save the .env file
            pipeline_name: Name of the pipeline
            domain: Domain for the pipeline
            http_port: HTTP port number
            frontend_theme: Frontend theme name
            repo_root: Absolute path to repository root (contains components dir)
            backends: Backend integration mode (local, distributed, external)
            stt_backend_url: External STT backend URL
            mt_backend_url: External MT backend URL
            stt_backend_engine: STT backend engine (e.g., faster-whisper)
        """
        config_dir = Path(output_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate components directory path
        if repo_root:
            components_dir = str(Path(repo_root) / "components")
            backends_dir = str(Path(repo_root) / "backends")
        else:
            # Fallback: calculate from template_dir
            components_dir = str(self.template_dir.parent.parent / "components")
            backends_dir = str(self.template_dir.parent.parent / "backends")
        
        # Use an externally reachable port if provided (e.g., behind Nginx), otherwise fall back to http_port
        effective_external_port = external_port if external_port else http_port
        env_file = config_dir / ".env"
        with open(env_file, "w") as f:
            f.write(f"DOMAIN={domain}\n")
            f.write(f"FRONTEND_THEME={frontend_theme}\n")
            f.write(f"HTTP_PORT={http_port}\n")
            f.write(f"DOMAIN_PORT={domain}:{http_port}\n")
            f.write(f"EXTERNAL_PORT={effective_external_port}\n")
            f.write(f"EXTERNAL_DOMAIN_PORT={domain}:{effective_external_port}\n")
            f.write(f"PIPELINE_NAME={pipeline_name}\n")
            f.write(f"COMPONENTS_DIR={components_dir}\n")
            f.write(f"BACKENDS_DIR={backends_dir}\n")
            f.write(f"HF_TOKEN={hf_token or ''}\n")
            f.write(f"BACKENDS={backends}\n")
            
            # Write STT_BACKEND_URL based on backend mode and engine
            if backends == "external" and stt_backend_url:
                # External backends use provided URL
                f.write(f"STT_BACKEND_URL={stt_backend_url}\n")
            elif backends in ["local", "distributed"]:
                # Local/distributed backends use internal Docker network address
                if stt_backend_engine == "faster-whisper":
                    f.write(f"STT_BACKEND_URL=http://whisper-worker:5008/asr\n")
                elif stt_backend_engine == "vllm":
                    f.write(f"STT_BACKEND_URL=http://vllm:8001/asr\n")
            
            if mt_backend_url:
                f.write(f"MT_BACKEND_URL={mt_backend_url}\n")

