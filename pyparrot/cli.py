"""CLI for PyParrot pipeline management."""

import click
import logging
import os
import sys
import getpass
import subprocess
from pathlib import Path
from .config import PipelineConfig
from .pipeline import Pipeline
from .evaluator import Evaluator
from .template_manager import TemplateManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_docker_compose_command():
    """Detect which docker-compose command is available.
    
    Returns:
        list: Command to use (e.g., ['docker', 'compose'] or ['docker-compose'])
        
    Raises:
        RuntimeError: If neither 'docker compose' nor 'docker-compose' is available
    """
    # Try 'docker compose' first (newer Docker versions)
    result = subprocess.run(["docker", "compose", "--version"], capture_output=True)
    if result.returncode == 0:
        return ["docker", "compose"]
    
    # Fall back to 'docker-compose' (older standalone)
    result = subprocess.run(["docker-compose", "--version"], capture_output=True)
    if result.returncode == 0:
        return ["docker-compose"]
    
    # Neither found
    raise RuntimeError(
        "Neither 'docker compose' nor 'docker-compose' command found. "
        "Please install Docker with compose support or docker-compose separately."
    )


@click.group()
@click.version_option()
def main():
    """PyParrot - CLI for Docker pipelines of speech and LLM components."""
    pass


@main.command()
@click.argument("config_name")
@click.option(
    "--type",
    type=click.Choice(["end2end", "cascaded", "LT.2025", "dialog", "BOOM"]),
    default="end2end",
    help="Configuration type",
)
@click.option("--port", type=int, default=8001, help="Internal port Traefik listens on (mapped from host)")
@click.option("--external-port", type=int, default=None, help="Externally reachable port (e.g., when behind Nginx). Defaults to --port.")
@click.option("--domain", default="pyparrot.localhost", help="Domain for the pipeline (use a real domain for public deployments)")
@click.option("--website-theme", default="defaulttheme", help="Website theme")
@click.option("--hf-token", default=None, help="HF token for dialog components")
def configure(config_name, type, port, external_port, domain, website_theme, hf_token):
    """Configure a new pipeline and create its configuration directory."""
    try:
        # Determine config directory
        config_dir = os.getenv("PYPARROT_CONFIG_DIR")
        if not config_dir:
            config_dir = Path(__file__).parent.parent / "config"
        else:
            config_dir = Path(config_dir)

        # Check if configuration already exists
        config_subdir = config_dir / config_name
        if config_subdir.exists():
            if not click.confirm(
                click.style(
                    f"Configuration '{config_name}' already exists. Overwrite?",
                    fg="yellow"
                )
            ):
                click.echo(click.style("Configuration creation cancelled.", fg="yellow"))
                sys.exit(0)
            logger.info(f"Overwriting existing configuration directory: {config_subdir}")
        else:
            config_subdir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created configuration directory: {config_subdir}")

        # Create configuration data
        config_data = {
            "name": config_name,
            "type": type,
            "domain": domain,
        }
        if port:
            config_data["port"] = port
        if website_theme:
            config_data["website_theme"] = website_theme
        if hf_token:
            config_data["hf_token"] = hf_token
        if external_port:
            config_data["external_port"] = external_port

        # Prompt for admin password
        click.echo()
        admin_password = getpass.getpass(
            click.style("Enter admin password: ", fg="cyan"),
            stream=None
        )
        if admin_password:
            config_data["admin_password"] = admin_password
        
        # Create PipelineConfig instance
        pipeline_config = PipelineConfig(**config_data)
        
        # Save admin password to .env file
        if admin_password:
            pipeline_config.save_admin_password(config_subdir)
            logger.info(f"Saved admin password to {config_subdir / 'dex' / 'dex.env'}")

        # Generate and save docker-compose file
        template_manager = TemplateManager()
        try:
            compose_config = template_manager.generate_compose_file(type, domain=domain)
            compose_file = config_subdir / "docker-compose.yaml"
            template_manager.save_compose_file(compose_config, str(compose_file))
            logger.info(f"Generated docker-compose file: {compose_file}")
        except Exception as e:
            logger.warning(f"Could not generate docker-compose file: {e}")

        # Generate .env file for docker-compose
        try:
            # Calculate repo root path (parent of pyparrot package)
            repo_root = str(Path(__file__).parent.parent)
            
            template_manager.generate_env_file(
                str(config_subdir),
                pipeline_name=config_name,
                domain=domain,
                http_port=port,
                frontend_theme=website_theme,
                hf_token=hf_token,
                external_port=external_port,
                repo_root=repo_root
            )
            logger.info(f"Generated .env file for docker-compose")
        except Exception as e:
            logger.warning(f"Could not generate .env file: {e}")

        # Generate traefik configuration files
        if admin_password:
            try:
                # Get the hashed password from the config (saved to dex.env)
                from .config import PipelineConfig as PC
                config_instance = PC(**config_data)
                # Extract the bcrypt hash
                import bcrypt
                password_bytes = admin_password.encode('utf-8')
                hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=10)).decode('utf-8')
                
                template_manager.generate_traefik_files(config_name, hashed_password, str(config_subdir))
                logger.info(f"Generated traefik configuration files in {config_subdir}/traefik")
                
                # Generate dex configuration
                template_manager.generate_dex_config(str(config_subdir))
                logger.info(f"Generated dex configuration in {config_subdir}/dex")
                
                # Generate traefik rules
                template_manager.generate_traefik_rules(str(config_subdir))
                logger.info(f"Generated traefik rules in {config_subdir}/traefik")
            except Exception as e:
                logger.warning(f"Could not generate traefik/dex files: {e}")

        logger.info(f"Created configuration for pipeline: {config_name} (type: {type})")

        # Display configuration
        click.echo(click.style("Pipeline Configuration:", fg="cyan", bold=True))
        click.echo(f"  Name: {config_name}")
        click.echo(f"  Type: {type}")
        click.echo(f"  Domain: {domain}")
        if port:
            click.echo(f"  Port: {port}")
        if website_theme:
            click.echo(f"  Website Theme: {website_theme}")
        if admin_password:
            click.echo(f"  Admin Password: {'*' * len(admin_password)}")

        # Save configuration to the subdirectory
        config_file = config_subdir / f"{config_name}.yaml"
        logger.info(f"Saved configuration to {config_file}")
        click.echo(f"\nConfiguration saved to {click.style(str(config_file), fg='green')}")
        click.echo(f"Configuration directory: {click.style(str(config_subdir), fg='green')}")
        click.echo(f"Environment file: {click.style(str(config_subdir / '.env'), fg='green')}")
        click.echo(f"Docker-compose file: {click.style(str(config_subdir / 'docker-compose.yaml'), fg='green')}")
        if admin_password:
            click.echo(f"Admin password saved to: {click.style(str(config_subdir / 'dex' / 'dex.env'), fg='green')}")
            click.echo(f"Traefik config: {click.style(str(config_subdir / 'traefik' / 'traefik.yaml'), fg='green')}")
            click.echo(f"Traefik rules: {click.style(str(config_subdir / 'traefik' / 'rules.ini'), fg='green')}")
            click.echo(f"Basic auth file: {click.style(str(config_subdir / 'traefik' / 'auth' / 'basicauth.txt'), fg='green')}")
            click.echo(f"Dex config: {click.style(str(config_subdir / 'dex' / 'dex.yaml'), fg='green')}")

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.argument("config_name")
@click.option(
    "--component",
    "-c",
    multiple=True,
    help="Specific components to build (can be used multiple times). Default: build all.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Build without using cache",
)
def build(config_name, component, no_cache):
    """Build Docker images for a pipeline configuration using docker-compose."""
    try:
        # Determine config directory
        config_dir = os.getenv("PYPARROT_CONFIG_DIR")
        if not config_dir:
            config_dir = Path(__file__).parent.parent / "config"
        else:
            config_dir = Path(config_dir)

        config_subdir = config_dir / config_name

        if not config_subdir.exists():
            click.echo(click.style(f"Error: Configuration '{config_name}' not found at {config_subdir}", fg="red"), err=True)
            sys.exit(1)

        docker_compose_file = config_subdir / "docker-compose.yaml"
        if not docker_compose_file.exists():
            click.echo(click.style(f"Error: docker-compose.yaml not found at {docker_compose_file}", fg="red"), err=True)
            sys.exit(1)

        # Get appropriate docker-compose command
        try:
            docker_cmd = get_docker_compose_command()
        except RuntimeError as e:
            click.echo(click.style(f"Error: {e}", fg="red"), err=True)
            sys.exit(1)

        # Build command
        cmd = docker_cmd + ["-f", str(docker_compose_file), "build"]

        if no_cache:
            cmd.append("--no-cache")

        # Add specific components if provided
        if component:
            cmd.extend(component)

        click.echo(click.style(f"Building Docker images for pipeline: {config_name}", fg="cyan", bold=True))
        click.echo(f"Config directory: {config_subdir}")
        if component:
            click.echo(f"Components: {', '.join(component)}")
        else:
            click.echo("Components: all")

        # Run docker-compose build
        result = subprocess.run(cmd, cwd=str(config_subdir), capture_output=False)

        if result.returncode == 0:
            click.echo(click.style("✓ Successfully built Docker images", fg="green"))
        else:
            click.echo(click.style(f"✗ Build failed with exit code {result.returncode}", fg="red"), err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.argument("config_name")
@click.option(
    "--component",
    "-c",
    multiple=True,
    help="Specific components to start (can be used multiple times). Default: start all.",
)
def start(config_name, component):
    """Start Docker containers for a pipeline configuration using docker-compose."""
    try:
        # Determine config directory
        config_dir = os.getenv("PYPARROT_CONFIG_DIR")
        if not config_dir:
            config_dir = Path(__file__).parent.parent / "config"
        else:
            config_dir = Path(config_dir)

        config_subdir = config_dir / config_name

        if not config_subdir.exists():
            click.echo(click.style(f"Error: Configuration '{config_name}' not found at {config_subdir}", fg="red"), err=True)
            sys.exit(1)

        docker_compose_file = config_subdir / "docker-compose.yaml"
        if not docker_compose_file.exists():
            click.echo(click.style(f"Error: docker-compose.yaml not found at {docker_compose_file}", fg="red"), err=True)
            sys.exit(1)

        # Get appropriate docker-compose command
        try:
            docker_cmd = get_docker_compose_command()
        except RuntimeError as e:
            click.echo(click.style(f"Error: {e}", fg="red"), err=True)
            sys.exit(1)

        # Start command - use 'up -d' instead of 'start' to create containers if they don't exist
        cmd = docker_cmd + ["-f", str(docker_compose_file), "up", "-d"]

        # Add specific components if provided
        if component:
            cmd.extend(component)

        click.echo(click.style(f"Starting Docker containers for pipeline: {config_name}", fg="cyan", bold=True))
        click.echo(f"Config directory: {config_subdir}")
        if component:
            click.echo(f"Components: {', '.join(component)}")
        else:
            click.echo("Components: all")

        # Run docker-compose start
        result = subprocess.run(cmd, cwd=str(config_subdir), capture_output=False)

        if result.returncode == 0:
            click.echo(click.style("✓ Successfully started Docker containers", fg="green"))
            
            # Initialize Redis admin group
            click.echo("Initializing Redis groups...")
            docker_cmd = get_docker_compose_command()
            
            # Add to admin group
            redis_admin_cmd = docker_cmd + ["-f", str(config_subdir / "docker-compose.yaml"), 
                        "exec", "-T", "redis", "redis-cli", "sadd", "groups:admin", "admin@example.com"]
            admin_result = subprocess.run(redis_admin_cmd, capture_output=True, text=True)
            
            # Add to presenter group
            redis_presenter_cmd = docker_cmd + ["-f", str(config_subdir / "docker-compose.yaml"), 
                        "exec", "-T", "redis", "redis-cli", "sadd", "groups:presenter", "admin@example.com"]
            presenter_result = subprocess.run(redis_presenter_cmd, capture_output=True, text=True)
            
            if admin_result.returncode == 0 and presenter_result.returncode == 0:
                click.echo(click.style("✓ Redis groups initialized (admin, presenter)", fg="green"))
            else:
                if admin_result.returncode != 0:
                    click.echo(click.style(f"⚠ Warning: Could not initialize Redis admin group: {admin_result.stderr}", fg="yellow"))
                if presenter_result.returncode != 0:
                    click.echo(click.style(f"⚠ Warning: Could not initialize Redis presenter group: {presenter_result.stderr}", fg="yellow"))
        else:
            click.echo(click.style(f"✗ Start failed with exit code {result.returncode}", fg="red"), err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.argument("config_name")
@click.option(
    "--component",
    "-c",
    multiple=True,
    help="Specific components to stop (can be used multiple times). Default: stop all.",
)
def stop(config_name, component):
    """Stop Docker containers for a pipeline configuration using docker-compose."""
    try:
        # Determine config directory
        config_dir = os.getenv("PYPARROT_CONFIG_DIR")
        if not config_dir:
            config_dir = Path(__file__).parent.parent / "config"
        else:
            config_dir = Path(config_dir)

        config_subdir = config_dir / config_name

        if not config_subdir.exists():
            click.echo(click.style(f"Error: Configuration '{config_name}' not found at {config_subdir}", fg="red"), err=True)
            sys.exit(1)

        docker_compose_file = config_subdir / "docker-compose.yaml"
        if not docker_compose_file.exists():
            click.echo(click.style(f"Error: docker-compose.yaml not found at {docker_compose_file}", fg="red"), err=True)
            sys.exit(1)

        # Stop command
        cmd = ["docker-compose", "-f", str(docker_compose_file), "stop"]

        # Add specific components if provided
        if component:
            cmd.extend(component)

        click.echo(click.style(f"Stopping Docker containers for pipeline: {config_name}", fg="cyan", bold=True))
        click.echo(f"Config directory: {config_subdir}")
        if component:
            click.echo(f"Components: {', '.join(component)}")
        else:
            click.echo("Components: all")

        # Run docker-compose stop
        result = subprocess.run(cmd, cwd=str(config_subdir), capture_output=False)

        if result.returncode == 0:
            click.echo(click.style("✓ Successfully stopped Docker containers", fg="green"))
        else:
            click.echo(click.style(f"✗ Stop failed with exit code {result.returncode}", fg="red"), err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--name",
    required=True,
    help="Pipeline name",
)
def status(name):
    """Get pipeline status."""
    try:
        pipeline_config = PipelineConfig(name=name)
        pipeline = Pipeline(pipeline_config)

        status_info = pipeline.status()

        click.echo(click.style("Pipeline Status:", fg="cyan", bold=True))
        click.echo(f"  Name: {status_info['name']}")
        click.echo(f"  Status: {click.style(status_info['status'], fg='green' if status_info['status'] == 'running' else 'yellow')}")

        if "logs" in status_info:
            click.echo(f"  Recent logs:\n{status_info['logs']}")

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--name",
    required=True,
    help="Pipeline name",
)
@click.option(
    "--dataset",
    type=click.Path(exists=True),
    required=True,
    help="Path to evaluation dataset",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Path to save evaluation results",
)
@click.option(
    "--metrics",
    multiple=True,
    help="Metrics to compute",
)
def evaluate(name, dataset, output, metrics):
    """Run evaluation on the pipeline."""
    try:
        evaluator = Evaluator(name)

        click.echo(click.style(f"Evaluating pipeline: {name}", fg="cyan", bold=True))
        click.echo(f"Dataset: {dataset}")

        # Run evaluation
        metrics_list = list(metrics) if metrics else None
        result = evaluator.evaluate(
            dataset_path=dataset,
            metrics=metrics_list,
            output_path=output,
        )

        # Display results
        click.echo(click.style("\nEvaluation Results:", fg="cyan", bold=True))
        click.echo(f"  Samples evaluated: {result.metrics.get('total_samples', 0)}")
        click.echo(f"  Successful: {result.metrics.get('successful_samples', 0)}")

        for metric_name, metric_value in result.metrics.items():
            if metric_name not in ["total_samples", "successful_samples"]:
                click.echo(f"  {metric_name}: {metric_value}")

        if output:
            click.echo(click.style(f"\n✓ Results saved to {output}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
