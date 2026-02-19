"""Manage docker-compose templates and merging."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import yaml
import logging
import subprocess
from jinja2 import Template
from .pipeline_types import get_pipeline_templates, has_pipeline_type, uses_slt, uses_url

logger = logging.getLogger(__name__)


def generate_self_signed_cert(domain: str, cert_path: str, key_path: str) -> None:
    """Generate a self-signed certificate for localhost domains.
    
    Args:
        domain: Domain name (e.g., app.localhost)
        cert_path: Path to save the certificate file
        key_path: Path to save the private key file
    """
    try:
        # Generate self-signed certificate using openssl
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_path,
            "-out", cert_path,
            "-days", "365",
            "-nodes",
            "-subj", f"/CN={domain}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Set appropriate permissions
        Path(cert_path).chmod(0o644)
        Path(key_path).chmod(0o600)
        
        logger.info(f"Generated self-signed certificate: {cert_path}")
        logger.info(f"Generated private key: {key_path}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate self-signed certificate: {e.stderr}")
        raise RuntimeError(f"Certificate generation failed: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("openssl command not found. Please install OpenSSL.")


class TemplateManager:
    """Manage docker-compose templates for different pipeline types."""

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

    def load_template(self, component: str, domain: str = None, debug: bool = False, enable_https: bool = False,
                      acme_staging: bool = False) -> Dict[str, Any]:
        """Load a single template file.
        
        Args:
            component: Component name
            domain: Domain name (used for conditional rendering)
            debug: Debug mode enabled (for conditional volume mounts)
            enable_https: Enable HTTPS support
            
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
            
            # Create environment dict for template (mimics .env file)
            environment = {
                "DEBUG_MODE": "true" if debug else "false",
                "ENABLE_HTTPS": "true" if enable_https else "false",
                "FORCE_HTTPS_REDIRECT": "false",  # Can be overridden by .env
                "ACME_EMAIL": "",  # Placeholder, will be set by .env
                "ACME_STAGING": "true" if acme_staging else "false",
            }
            
            template = Template(content)
            content = template.render(IS_LOCALHOST_DOMAIN=is_localhost, DOMAIN=domain or "", environment=environment)
        
        return yaml.safe_load(content)

    def merge_templates(self, components: List[str], domain: str = None, debug: bool = False, enable_https: bool = False,
                        acme_staging: bool = False) -> Dict[str, Any]:
        """Merge multiple component templates into a single docker-compose file.
        
        Args:
            components: List of component names to merge
            domain: Domain name (used for conditional rendering)
            debug: Debug mode enabled
            enable_https: Enable HTTPS support
            
        Returns:
            Merged docker-compose configuration
        """
        if not components:
            raise ValueError("At least one component must be specified")

        # Load base template from first component
        merged = self.load_template(components[0], domain, debug, enable_https, acme_staging)
        
        # Merge remaining components
        for component in components[1:]:
            template = self.load_template(component, domain, debug, enable_https, acme_staging)
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
                             mt_backend_engine: str = None, mt_backend_gpu: str = None,
                             tts_backend_engine: str = None, tts_backend_gpu: str = None,
                             llm_backend_engine: str = None, llm_backend_gpu: str = None,
                             repo_root: str = None, enable_https: bool = False, debug: bool = False,
                             acme_staging: bool = False) -> Dict[str, Any]:
        """Generate docker-compose configuration for a pipeline type.
        
        Args:
            pipeline_type: Type of pipeline (end2end, cascaded, etc.)
            domain: Domain name (used for conditional rendering)
            backends_mode: Backend integration mode (local, distributed, external)
            stt_backend_engine: STT backend engine (e.g., faster-whisper)
            stt_backend_gpu: GPU device ID for local/distributed backends
            mt_backend_engine: MT backend engine (e.g., vllm)
            mt_backend_gpu: GPU device ID for MT backend
            tts_backend_engine: TTS backend engine (e.g., tts-kokoro)
            tts_backend_gpu: GPU device ID for TTS backend
            llm_backend_engine: LLM backend engine (e.g., huggingface-tgi)
            llm_backend_gpu: GPU device ID for LLM backend
            repo_root: Repository root path for locating backend services
            enable_https: Enable HTTPS support
            debug: Debug mode enabled
            
        Returns:
            Complete docker-compose configuration
        """
        if not has_pipeline_type(pipeline_type):
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        components = get_pipeline_templates(pipeline_type)
        composed = self.merge_templates(components, domain, debug, enable_https, acme_staging)
        
        # Add backend services for local/distributed modes
        if backends_mode in ["local", "distributed"]:
            if uses_url(pipeline_type, "stt"):
                backend_compose = self._load_backend_compose(stt_backend_engine, stt_backend_gpu, repo_root)
                if backend_compose:
                    self._merge_services(composed, backend_compose)
            else:
                logger.info("STT backend not required for this pipeline type")

            if uses_url(pipeline_type, "mt"):
                if mt_backend_engine:
                    logger.info(f"Loading MT backend: {mt_backend_engine}")
                    mt_compose = self._load_backend_compose(mt_backend_engine, mt_backend_gpu, repo_root, backend_type="mt")
                    if mt_compose:
                        self._merge_services(composed, mt_compose)
                    else:
                        logger.warning(f"Failed to load MT backend: {mt_backend_engine}")
                else:
                    logger.info("No MT backend engine specified")
            else:
                logger.info("MT backend not required for this pipeline type")

            if uses_url(pipeline_type, "tts"):
                if tts_backend_engine:
                    logger.info(f"Loading TTS backend: {tts_backend_engine}")
                    tts_compose = self._load_backend_compose(tts_backend_engine, tts_backend_gpu, repo_root, backend_type="tts")
                    if tts_compose:
                        self._merge_services(composed, tts_compose)
                    else:
                        logger.warning(f"Failed to load TTS backend: {tts_backend_engine}")
                else:
                    logger.info("No TTS backend engine specified")
            else:
                logger.info("TTS backend not required for this pipeline type")

            if uses_url(pipeline_type, "llm"):
                if llm_backend_engine:
                    logger.info(f"Loading LLM backend: {llm_backend_engine}")
                    llm_compose = self._load_backend_compose(llm_backend_engine, llm_backend_gpu, repo_root, backend_type="llm")
                    if llm_compose:
                        self._merge_services(composed, llm_compose)
                    else:
                        logger.warning(f"Failed to load LLM backend: {llm_backend_engine}")
                else:
                    logger.info("No LLM backend engine specified")
            else:
                logger.info("LLM backend not required for this pipeline type")
        
        return composed

    def _load_backend_compose(self, backend_engine: str, gpu_device: str = None, repo_root: str = None, backend_type: str = "stt") -> Dict[str, Any]:
        """Load backend service configuration.
        
        Args:
            backend_engine: Backend engine name (e.g., faster-whisper, vllm)
            gpu_device: GPU device ID (e.g., '0', '1', or None for CPU)
            repo_root: Repository root path
            backend_type: Type of backend ("stt", "mt", "tts", or "llm")
            
        Returns:
            Backend docker-compose configuration or None if not found
        """
        # Map backend engines to their directory names
        backend_dirs = {
            "faster-whisper": "faster-whisper",
            "vllm": "vllmserver",
            "tts-kokoro": "tts-kokoro",
            "huggingface-tgi": "huggingface-tgi",
        }
        
        if backend_engine not in backend_dirs:
            logger.warning(f"Backend engine '{backend_engine}' not yet supported")
            return None
        
        backend_dir_name = backend_dirs[backend_engine]
        
        # Try to find the backend docker-compose
        if repo_root:
            backend_dir = Path(repo_root) / "backends" / backend_dir_name
        else:
            # Fallback: calculate from template_dir
            backend_dir = self.template_dir.parent.parent / "backends" / backend_dir_name

        backend_path = backend_dir / "docker-compose.yaml"
        if not backend_path.exists():
            backend_path = backend_dir / "docker-compose.yml"
        
        if not backend_path.exists():
            logger.warning(f"Backend compose file not found: {backend_path}")
            return None
        
        with open(backend_path, "r") as f:
            backend_config = yaml.safe_load(f)
        
        # Modify backend services for integration
        if "services" in backend_config:
            # Create a list of items to iterate over to avoid "dictionary changed during iteration" error
            services_items = list(backend_config["services"].items())
            for original_service_name, service in services_items:
                # Rename services for MT backend to avoid conflicts with STT
                service_name = original_service_name
                if backend_type == "mt":
                    if service_name == "vllm-server":
                        service_name = "vllm-server-mt"
                    elif service_name == "vllm":
                        service_name = "vllm-mt"
                    elif service_name == "whisper-worker":
                        service_name = "whisper-worker-mt"
                    
                    # Update the service in the config dict with new name
                    backend_config["services"][service_name] = backend_config["services"].pop(original_service_name)
                
                # Update VLLM_URL and depends_on references when renaming services for MT backend
                if backend_type == "mt" and backend_engine == "vllm":
                    if "environment" in service:
                        if isinstance(service["environment"], dict):
                            # Update VLLM_URL to point to the renamed service
                            if "VLLM_URL" in service["environment"]:
                                service["environment"]["VLLM_URL"] = service["environment"]["VLLM_URL"].replace(
                                    "vllm-server:", "vllm-server-mt:"
                                )
                        elif isinstance(service["environment"], list):
                            # Update VLLM_URL in list format
                            for i, env_var in enumerate(service["environment"]):
                                if isinstance(env_var, str) and env_var.startswith("VLLM_URL="):
                                    service["environment"][i] = env_var.replace(
                                        "vllm-server:", "vllm-server-mt:"
                                    )
                    
                    # Update depends_on references to renamed services
                    if "depends_on" in service:
                        if isinstance(service["depends_on"], list):
                            for i, dep in enumerate(service["depends_on"]):
                                if dep == "vllm-server":
                                    service["depends_on"][i] = "vllm-server-mt"
                                elif dep == "vllm":
                                    service["depends_on"][i] = "vllm-mt"
                        elif isinstance(service["depends_on"], dict):
                            # Handle dict format (with conditions)
                            new_depends_on = {}
                            for dep_name, dep_config in service["depends_on"].items():
                                if dep_name == "vllm-server":
                                    new_depends_on["vllm-server-mt"] = dep_config
                                elif dep_name == "vllm":
                                    new_depends_on["vllm-mt"] = dep_config
                                else:
                                    new_depends_on[dep_name] = dep_config
                            service["depends_on"] = new_depends_on
                
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
                
                # Ensure vLLM model name comes from env (set via CLI)
                if backend_engine == "vllm":
                    if "vllm-server" in service_name:
                        command = service.get("command")
                        if isinstance(command, list):
                            if "--model" in command:
                                model_index = command.index("--model") + 1
                                if model_index < len(command):
                                    model_var = f"${{STT_BACKEND_MODEL}}" if backend_type == "stt" else "${MT_BACKEND_MODEL}"
                                    command[model_index] = model_var
                            else:
                                model_var = f"${{STT_BACKEND_MODEL}}" if backend_type == "stt" else "${MT_BACKEND_MODEL}"
                                command = ["--model", model_var] + command
                            service["command"] = command
                        elif isinstance(command, str):
                            model_var = f"${{STT_BACKEND_MODEL}}" if backend_type == "stt" else "${MT_BACKEND_MODEL}"
                            service["command"] = command.replace(
                                "--model Qwen/Qwen2.5-7B-Instruct",
                                f"--model {model_var}"
                            )
                    elif "vllm" in service_name and service_name != "vllm-server" and service_name != "vllm-server-mt":
                        if "environment" not in service:
                            service["environment"] = {}
                        if isinstance(service["environment"], dict):
                            model_var = f"${{STT_BACKEND_MODEL}}" if backend_type == "stt" else "${MT_BACKEND_MODEL}"
                            service["environment"]["MODEL_ID"] = model_var

                # Modify GPU settings if provided
                # For vllm backend, only apply to vllm-server service, not vllm service
                should_apply_gpu = gpu_device is not None and not (backend_engine == "vllm" and "vllm" in service_name and "vllm-server" not in service_name)
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

    def generate_traefik_files(self, config_name: str, encrypted_admin_password: str, output_dir: str,
                              enable_https: bool = False, acme_staging: bool = False,
                              acme_email: str = None, force_https_redirect: bool = False,
                              domain: str = None) -> None:
        """Generate traefik configuration files from templates.
        
        Args:
            config_name: Configuration name for the pipeline label
            encrypted_admin_password: Bcrypt encrypted admin password
            output_dir: Directory to save the generated traefik files
            enable_https: Enable HTTPS support
            acme_staging: Use Let's Encrypt staging
            acme_email: Email for Let's Encrypt
            force_https_redirect: Force HTTPS redirect
            domain: Domain name
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
            
            # Render Jinja2 template with environment variables
            is_localhost = domain and ".localhost" in domain
            environment = {
                "ENABLE_HTTPS": "true" if enable_https else "false",
                "ACME_STAGING": "true" if acme_staging else "false",
                "ACME_EMAIL": acme_email or "",
                "FORCE_HTTPS_REDIRECT": "true" if force_https_redirect else "false",
            }
            
            template = Template(traefik_content)
            traefik_content = template.render(IS_LOCALHOST_DOMAIN=is_localhost, environment=environment)
            
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
                         external_port: int = None, external_https_port: int = None,
                         repo_root: str = None,
                         backends: str = "local", stt_backend_url: str = None,
                         mt_backend_url: str = None, tts_backend_url: str = None,
                         summarizer_backend_url: str = None,
                         slide_translator_url: str = None,
                         text_structurer_online_url: str = None, text_structurer_offline_url: str = None,
                         llm_backend_url: str = None,
                         stt_backend_engine: str = None, tts_backend_engine: str = None,
                         summarizer_backend_engine: str = None, summarizer_backend_model: str = None,
                         summarizer_backend_gpu: str = None,
                         text_structurer_backend_engine: str = None, text_structurer_backend_model: str = None,
                         text_structurer_backend_gpu: str = None,
                         slide_translator_engine: str = None, slide_translator_model: str = None,
                         slide_translator_gpu: str = None,
                         llm_backend_engine: str = None, llm_backend_model: str = None,
                         stt_backend_model: str = None, mt_backend_engine: str = None,
                         mt_backend_model: str = None, enable_https: bool = False,
                         https_port: int = 443, acme_email: str = None,
                         acme_staging: bool = False, force_https_redirect: bool = False,
                         slide_support: bool = False,
                         pipeline_type: str = None,
                         debug: bool = False) -> None:
        """Generate .env file for docker-compose with environment variables.
        
        Args:
            output_dir: Directory to save the .env file
            pipeline_name: Name of the pipeline
            domain: Domain for the pipeline
            http_port: HTTP port number
            frontend_theme: Frontend theme name
            repo_root: Absolute path to repository root (contains components dir)
            external_https_port: External HTTPS port for reverse proxy
            backends: Backend integration mode (local, distributed, external)
            stt_backend_url: External STT backend URL
            mt_backend_url: External MT backend URL
            tts_backend_url: External TTS backend URL
            tts_backend_engine: TTS backend engine (e.g., tts-kokoro)
            summarizer_backend_url: External Summarizer backend URL
            slide_translator_url: External Slide Translator backend URL
            text_structurer_online_url: External Text Structurer online model URL
            text_structurer_offline_url: External Text Structurer offline model URL
            summarizer_backend_engine: Summarizer backend engine
            summarizer_backend_model: Summarizer backend model
            summarizer_backend_gpu: Summarizer backend GPU device
            text_structurer_backend_engine: Text structurer backend engine
            text_structurer_backend_model: Text structurer backend model
            text_structurer_backend_gpu: Text structurer backend GPU device
            slide_translator_engine: Slide translator backend engine
            slide_translator_model: Slide translator backend model
            slide_translator_gpu: Slide translator backend GPU device
            llm_backend_url: External LLM backend URL
            stt_backend_engine: STT backend engine (e.g., faster-whisper)
            stt_backend_model: STT backend model name (e.g., Qwen2.5-Omni-7B)
            mt_backend_engine: MT backend engine (e.g., vllm)
            mt_backend_model: MT backend model name (e.g., Qwen/Qwen2.5-7B-Instruct)
            llm_backend_engine: LLM backend engine (e.g., huggingface-tgi)
            llm_backend_model: LLM backend model ID (e.g., google/gemma-3-12b-it)
            enable_https: Enable HTTPS support
            https_port: HTTPS port number
            acme_email: Email for Let's Encrypt
            acme_staging: Use Let's Encrypt staging server
            force_https_redirect: Force redirect HTTP to HTTPS
            slide_support: Enable slide viewer support
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
        # Use an externally reachable HTTPS port if provided (e.g., behind Nginx), otherwise fall back to https_port
        effective_external_https_port = external_https_port if external_https_port else https_port
        env_file = config_dir / ".env"
        with open(env_file, "w") as f:
            try:
                host_uid = os.getuid()
                host_gid = os.getgid()
            except AttributeError:
                host_uid = 0
                host_gid = 0
            try:
                docker_gid = os.stat("/var/run/docker.sock").st_gid
            except (FileNotFoundError, PermissionError, AttributeError):
                docker_gid = 0
            f.write(f"DOMAIN={domain}\n")
            f.write(f"FRONTEND_THEME={frontend_theme}\n")
            f.write(f"HTTP_PORT={http_port}\n")
            f.write(f"DOMAIN_PORT={domain}:{http_port}\n")
            f.write(f"EXTERNAL_PORT={effective_external_port}\n")
            f.write(f"EXTERNAL_DOMAIN_PORT={domain}:{effective_external_port}\n")
            f.write(f"HTTPS_DOMAIN_PORT={domain}:{https_port}\n")
            f.write(f"EXTERNAL_HTTPS_DOMAIN_PORT={domain}:{effective_external_https_port}\n")
            f.write(f"PIPELINE_NAME={pipeline_name}\n")
            f.write(f"HOST_UID={host_uid}\n")
            f.write(f"HOST_GID={host_gid}\n")
            f.write(f"DOCKER_GID={docker_gid}\n")
            f.write(f"COMPONENTS_DIR={components_dir}\n")
            f.write(f"BACKENDS_DIR={backends_dir}\n")
            f.write(f"HF_TOKEN={hf_token or ''}\n")
            f.write(f"BACKENDS={backends}\n")
            f.write(f"DEBUG_MODE={'true' if debug else 'false'}\n")
            f.write(f"SLIDE_SUPPORT={'true' if slide_support else 'false'}\n")
            if pipeline_type:
                f.write(f"PIPELINE_TYPE={pipeline_type}\n")
            f.write(f"ENABLE_HTTPS={'true' if enable_https else 'false'}\n")
            f.write(f"HTTPS_PORT={https_port}\n")
            f.write(f"FORCE_HTTPS_REDIRECT={'true' if force_https_redirect else 'false'}\n")
            f.write(f"ACME_STAGING={'true' if acme_staging else 'false'}\n")
            if acme_email:
                f.write(f"ACME_EMAIL={acme_email}\n")
            
            # ACME data directory for Let's Encrypt certificates (persistent across pipelines)
            acme_data_dir = str(Path.home() / ".pyparrot" / "acme" / domain / "acme.json")
            f.write(f"ACME_DATA_DIR={acme_data_dir}\n")
            
            if stt_backend_model:
                f.write(f"STT_BACKEND_MODEL={stt_backend_model}\n")
            if mt_backend_model:
                f.write(f"MT_BACKEND_MODEL={mt_backend_model}\n")
            
            known_pipeline_type = pipeline_type and has_pipeline_type(pipeline_type)
            should_write_stt = uses_url(pipeline_type, "stt") if known_pipeline_type else True
            should_write_mt = uses_url(pipeline_type, "mt") if known_pipeline_type else True
            should_write_tts = uses_url(pipeline_type, "tts") if known_pipeline_type else True
            should_write_summarizer = uses_url(pipeline_type, "summarizer") if known_pipeline_type else True
            should_write_text_structurer_online = uses_url(pipeline_type, "text_structurer_online") if known_pipeline_type else True
            should_write_text_structurer_offline = uses_url(pipeline_type, "text_structurer_offline") if known_pipeline_type else True
            should_write_slide_translator = uses_url(pipeline_type, "slide_translator") if known_pipeline_type else True
            should_write_llm = uses_url(pipeline_type, "llm") if known_pipeline_type else True

            # Write STT_BACKEND_URL based on backend mode, engine, and pipeline type
            use_slt = uses_slt(pipeline_type)
            if should_write_stt:
                if backends == "external" and stt_backend_url:
                    # External backends use provided URL as-is
                    f.write(f"STT_BACKEND_URL={stt_backend_url}\n")
                elif backends in ["local", "distributed"]:
                    # Local/distributed backends use internal Docker network address
                    if stt_backend_engine == "faster-whisper":
                        # Use /slt endpoint for pipeline types that require SLT; /asr for others
                        endpoint = "slt" if use_slt else "asr"
                        f.write(f"STT_BACKEND_URL=http://whisper-worker:5008/{endpoint}\n")
                    elif stt_backend_engine == "vllm":
                        f.write("STT_BACKEND_URL=http://vllm:8001/asr\n")

            if should_write_mt:
                if mt_backend_url:
                    f.write(f"MT_BACKEND_URL={mt_backend_url}\n")
                elif backends in ["local", "distributed"] and mt_backend_engine == "vllm":
                    f.write("MT_BACKEND_URL=http://vllm-mt:8001/mt/\n")

            if should_write_tts:
                if backends == "external" and tts_backend_url:
                    f.write(f"TTS_BACKEND_URL={tts_backend_url}\n")
                elif backends in ["local", "distributed"] and tts_backend_engine == "tts-kokoro":
                    f.write("TTS_BACKEND_URL=http://tts-kokoro:5058/tts\n")

            if should_write_summarizer and summarizer_backend_url:
                f.write(f"SUM_BACKEND_URL={summarizer_backend_url}\n")

            if should_write_text_structurer_online and text_structurer_online_url:
                f.write(f"TEXT_STRUCTURER_ONLINE_URL={text_structurer_online_url}\n")

            if should_write_text_structurer_offline and text_structurer_offline_url:
                f.write(f"TEXT_STRUCTURER_OFFLINE_URL={text_structurer_offline_url}\n")

            if should_write_slide_translator and slide_translator_url:
                f.write(f"SLIDE_TRANSLATOR_URL={slide_translator_url}\n")

            if should_write_summarizer and summarizer_backend_engine:
                f.write(f"SUM_BACKEND_ENGINE={summarizer_backend_engine}\n")
            if should_write_summarizer and summarizer_backend_model:
                f.write(f"SUM_BACKEND_MODEL={summarizer_backend_model}\n")
            if should_write_summarizer and summarizer_backend_gpu:
                f.write(f"SUM_BACKEND_GPU={summarizer_backend_gpu}\n")

            if should_write_text_structurer_online and text_structurer_backend_engine:
                f.write(f"TEXT_STRUCTURER_BACKEND_ENGINE={text_structurer_backend_engine}\n")
            if should_write_text_structurer_online and text_structurer_backend_model:
                f.write(f"TEXT_STRUCTURER_BACKEND_MODEL={text_structurer_backend_model}\n")
            if should_write_text_structurer_online and text_structurer_backend_gpu:
                f.write(f"TEXT_STRUCTURER_BACKEND_GPU={text_structurer_backend_gpu}\n")

            if should_write_slide_translator and slide_translator_engine:
                f.write(f"SLIDE_TRANSLATOR_ENGINE={slide_translator_engine}\n")
            if should_write_slide_translator and slide_translator_model:
                f.write(f"SLIDE_TRANSLATOR_MODEL={slide_translator_model}\n")
            if should_write_slide_translator and slide_translator_gpu:
                f.write(f"SLIDE_TRANSLATOR_GPU={slide_translator_gpu}\n")

            if should_write_llm:
                if llm_backend_url:
                    f.write(f"LLM_BACKEND_URL={llm_backend_url}\n")
                elif backends in ["local", "distributed"] and llm_backend_engine == "huggingface-tgi":
                    f.write("LLM_BACKEND_URL=http://llm:80\n")

            if should_write_llm and llm_backend_engine == "huggingface-tgi":
                if llm_backend_model:
                    f.write(f"MODEL_ID={llm_backend_model}\n")
                if hf_token:
                    f.write(f"HUGGING_FACE_HUB_TOKEN={hf_token}\n")
