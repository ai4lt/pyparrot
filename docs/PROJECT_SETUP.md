# PyParrot Project Setup Summary

## Overview

PyParrot is a comprehensive Python CLI tool for managing Docker pipelines that combine speech recognition and large language models. The project provides a modular, extensible architecture for building, deploying, and evaluating AI pipelines.

## Project Structure

```
pyparrot/
├── pyparrot/                    # Main package
│   ├── __init__.py             # Package initialization
│   ├── cli.py                  # Click-based CLI commands
│   ├── config.py               # Pydantic configuration models
│   ├── pipeline.py             # Pipeline orchestration
│   ├── docker_manager.py       # Docker operations wrapper
│   ├── evaluator.py            # Evaluation framework
│   ├── template_manager.py     # Docker-compose template management
│   ├── components/             # External component submodules
│   │   ├── qbmediator/         # Queue-based mediator service│   │   ├── kafka_post_task/    # Kafka post-processing task│   │   ├── lt_api/             # LT API service
│   │   ├── lt_api_stream/      # Streaming API service
│   │   ├── loggingwoker/       # Logger service
│   │   ├── ltfrontend/         # Web frontend
│   │   ├── lt-archive/         # Archive service
│   │   └── streamingasr/       # Streaming ASR service
│   └── templates/              # Configuration templates
│       ├── docker/             # Docker-compose templates
│       │   ├── middleware.yaml # Middleware pipeline template
│       │   ├── asr.yaml        # ASR component template
│       │   └── mt.yaml         # Machine translation template
│       ├── traefik/            # Traefik reverse proxy templates
│       │   ├── traefik.yaml.tpl
│       │   ├── basicauth.txt.tpl
│       │   └── rules.ini.tpl
│       └── dex/                # Dex OIDC server templates
│           └── dex.yaml.tpl
├── tests/                       # Test suite
│   ├── conftest.py             # Pytest configuration
│   ├── test_config.py          # Configuration tests
│   ├── test_pipeline.py        # Pipeline tests
│   └── test_evaluator.py       # Evaluator tests
├── examples/                    # Example configurations and data
│   ├── config.yaml             # Example pipeline configuration
│   ├── eval_dataset.json       # Example evaluation dataset
│   └── example_usage.py        # Programmatic usage example
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # System design and architecture
│   ├── GETTING_STARTED.md      # Quick start guide
│   └── CLI_REFERENCE.md        # CLI command reference
├── config/                      # Configuration instances (generated)
│   └── {config_name}/          # Each pipeline configuration directory
│       ├── .env                # Environment variables for docker-compose
│       ├── docker-compose.yaml # Generated docker-compose file
│       ├── {config_name}.yaml  # Pipeline configuration
│       ├── dex/
│       │   └── dex.env         # Dex OIDC encrypted credentials
│       └── traefik/
│           ├── traefik.yaml    # Generated traefik config
│           ├── rules.ini       # Generated auth rules
│           └── auth/
│               ├── basicauth.txt # Generated basic auth file
│               └── dex.yaml    # Generated dex configuration
├── pyproject.toml              # Project metadata and dependencies
├── requirements.txt            # Direct dependencies list
├── Makefile                    # Convenience commands
├── setup_project.py            # Project setup utilities
├── .gitignore                  # Git ignore rules
├── .gitmodules                 # Git submodule configuration
├── README.md                   # Project overview
└── LICENSE                     # License file
```

## Key Features

### 1. **Configuration Management**
- YAML-based pipeline configuration
- CLI-based configuration creation
- Pydantic validation and serialization
- Support for speech, LLM, and Docker settings

### 2. **CLI Commands**
- `configure`: Create and configure pipelines
- `build`: Build Docker images from configuration
- `start`: Start pipeline containers
- `stop`: Stop running containers
- `status`: Get pipeline status
- `evaluate`: Run evaluations on pipelines

### 3. **Docker Integration**
- Automatic Dockerfile generation
- Image building and management
- Container lifecycle management
- Volume and port mappings
- Environment variable configuration

### 4. **Evaluation Framework**
- JSON/JSONL dataset support
- Metric computation
- Result persistence
- Extensible evaluation logic

### 5. **Component Architecture**
- Abstract base classes for extensibility
- Speech component implementations (Whisper)
- LLM component implementations (OpenAI)
- Easy addition of new components

## Technology Stack

- **Python 3.9+**: Programming language
- **Click 8.1+**: CLI framework
- **Pydantic 2.0+**: Data validation
- **PyYAML 6.0+**: Configuration format
- **Docker SDK**: Container management
- **Pytest**: Testing framework
- **Optional: Whisper, OpenAI**: Component implementations

## Installation

```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Configure pipeline
pyparrot configure --name my-pipeline --model gpt-3.5-turbo --output config.yaml

# Build Docker image
pyparrot build --config config.yaml

# Start container
pyparrot start --config config.yaml

# Run evaluation
pyparrot evaluate --name my-pipeline --dataset examples/eval_dataset.json

# Stop container
pyparrot stop --name my-pipeline
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=pyparrot

# Format code
make format

# Run linters
make lint

# Clean build artifacts
make clean
```

## Core Modules

### config.py
- `SpeechConfig`: Speech component configuration
- `LLMConfig`: Language model configuration
- `DockerConfig`: Docker settings
- `PipelineConfig`: Complete pipeline configuration
- YAML serialization/deserialization

### cli.py
- Command-line interface
- User-friendly error handling
- Colored output
- Command documentation

### pipeline.py
- Pipeline lifecycle management
- Dockerfile generation
- Requirements file creation
- Container orchestration

### docker_manager.py
- Docker client wrapper
- Image building
- Container management
- Logging and monitoring

### evaluator.py
- Dataset loading (JSON/JSONL)
- Metric computation
- Result serialization
- Evaluation workflows

### components/
- Speech recognition components
- Language model components
- Abstract base classes
- Extensible architecture

## Extensibility

### Adding Speech Components

```python
from pyparrot.components.speech import SpeechComponent

class MyComponent(SpeechComponent):
    def transcribe(self, audio_path: str) -> str:
        # Implementation
        pass
```

### Adding LLM Components

```python
from pyparrot.components.llm import LLMComponent

class MyComponent(LLMComponent):
    def generate(self, prompt: str) -> str:
        # Implementation
        pass
```

### Custom Evaluation Logic

```python
from pyparrot.evaluator import Evaluator

class CustomEvaluator(Evaluator):
    def _evaluate_sample(self, sample):
        # Custom metrics
        pass
```

## Configuration Example

```yaml
name: my-pipeline
version: "1.0"
components:
  speech:
    model: whisper
    sample_rate: 16000
  llm:
    model: gpt-3.5-turbo
    temperature: 0.7
docker:
  image_name: my-pipeline
  base_image: python:3.11-slim
  port: 8000
```

## Testing

Comprehensive test suite included:
- Configuration validation tests
- Pipeline functionality tests
- Evaluator workflow tests
- ~95% code coverage target

Run tests with:
```bash
pytest tests/ -v
```

## Documentation

- **README.md**: Project overview
- **docs/GETTING_STARTED.md**: Quick start guide
- **docs/ARCHITECTURE.md**: System design details
- **docs/CLI_REFERENCE.md**: Complete CLI documentation
- **examples/**: Working examples and sample data

## Dependencies

### Core
- click: CLI framework
- pydantic: Data validation
- pyyaml: Configuration format
- docker: Container management
- python-dotenv: Environment variables

### Optional
- openai-whisper: Speech recognition
- openai: Language model API

### Development
- pytest: Testing
- pytest-cov: Coverage reporting
- black: Code formatting
- flake8: Linting
- mypy: Type checking

## Next Steps

1. **Install**: `pip install -e ".[dev]"`
2. **Explore**: Check `examples/` directory
3. **Test**: Run `pytest tests/ -v`
4. **Configure**: Create custom config.yaml
5. **Build**: Build Docker image for your pipeline
6. **Deploy**: Start and monitor containers
7. **Evaluate**: Run evaluations on your pipeline
8. **Extend**: Add custom components

## Support & Contribution

- Check documentation for help
- Run tests to verify functionality
- Use `--help` flag on any CLI command
- Submit issues or contribute improvements

## License

MIT License - See LICENSE file for details

---

**Ready to go!** The project is fully set up with:
✓ Complete CLI interface
✓ Configuration management
✓ Docker integration
✓ Component architecture
✓ Evaluation framework
✓ Comprehensive tests
✓ Full documentation
✓ Example files
✓ Development tools
