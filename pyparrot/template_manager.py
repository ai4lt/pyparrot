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

    def generate_compose_file(self, pipeline_type: str, domain: str = None) -> Dict[str, Any]:
        """Generate docker-compose configuration for a pipeline type.
        
        Args:
            pipeline_type: Type of pipeline (end2end, cascaded, etc.)
            domain: Domain name (used for conditional rendering)
            
        Returns:
            Complete docker-compose configuration
        """
        if pipeline_type not in self.PIPELINE_TEMPLATES:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        components = self.PIPELINE_TEMPLATES[pipeline_type]
        return self.merge_templates(components, domain)

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
            
            # Restrict permissions for security
            basicauth_file.chmod(0o600)
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
                         external_port: int = None, repo_root: str = None) -> None:
        """Generate .env file for docker-compose with environment variables.
        
        Args:
            output_dir: Directory to save the .env file
            pipeline_name: Name of the pipeline
            domain: Domain for the pipeline
            http_port: HTTP port number
            frontend_theme: Frontend theme name
            repo_root: Absolute path to repository root (contains components dir)
        """
        config_dir = Path(output_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate components directory path
        if repo_root:
            components_dir = str(Path(repo_root) / "components")
        else:
            # Fallback: calculate from template_dir
            components_dir = str(self.template_dir.parent.parent / "components")
        
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
            f.write(f"HF_TOKEN={hf_token or ''}\n")
        
        logger.info(f"Generated .env file: {env_file}")

