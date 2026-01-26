# PyParrot Architecture

## Overview

PyParrot is a modular framework for managing Docker-based pipelines that combine speech recognition and LLM components with middleware services. The architecture is designed to be extensible and support multiple implementations of each component.

## Project Structure

```
pyparrot/
├── pyparrot/                  # Main package
│   ├── config.py              # Configuration management (Pydantic models)
│   ├── cli.py                 # Click-based CLI interface
│   ├── pipeline.py            # Pipeline orchestration and lifecycle
│   ├── docker_manager.py      # Docker container and image management
│   ├── evaluator.py           # Evaluation framework and metrics
│   ├── template_manager.py    # Docker-compose template management
│   ├── components/            # External service components (submodules)
│   │   └── qbmediator/        # Queue-based mediator service
│   └── templates/             # Configuration templates
│       ├── docker/            # Docker-compose component templates
│       ├── traefik/           # Reverse proxy and auth templates
│       └── dex/               # OIDC server templates
```

## External Components (Git Submodules)

PyParrot integrates external services as Git submodules in the `components/` directory:

### Core Services

#### qbmediator
- **Purpose**: Queue-based mediator for orchestrating pipeline components
- **Location**: `components/qbmediator/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/qbmediator.git

#### kafka_post_task
- **Purpose**: Kafka post-processing task handler
- **Location**: `components/kafka_post_task/`
- **Type**: Local component (not a separate repository)

#### lt_api
- **Purpose**: LT API service for handling requests
- **Location**: `components/lt_api/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt_api.git

#### lt_api_stream
- **Purpose**: Streaming API for real-time processing
- **Location**: `components/lt_api_stream/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt_api_stream.git

#### loggingwoker
- **Purpose**: Logger service for handling and archiving logs
- **Location**: `components/loggingwoker/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/loggingwoker.git

#### ltfrontend
- **Purpose**: Web frontend for the pipeline
- **Location**: `components/ltfrontend/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/ltfrontend.git

#### lt-archive
- **Purpose**: Archive service for storing and retrieving translations
- **Location**: `components/lt-archive/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt-archive.git

#### streamingasr
- **Purpose**: Streaming automatic speech recognition service
- **Location**: `components/streamingasr/`
- **Repository**: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/streamingasr.git

### Why Submodules?

- ✅ Allows local development and customization of components
- ✅ Version control keeps component versions in sync with main project
- ✅ Flexible: can use local builds or pre-built images via docker-compose
- ✅ Users can modify source code and rebuild components independently

## Core Components

### Configuration (`config.py`)

Manages pipeline configuration using Pydantic for validation and serialization:

- **PipelineConfig**: Top-level configuration containing speech, LLM, Docker, domain, and admin settings
- **SpeechConfig**: Speech recognition component configuration
- **LLMConfig**: Language model component configuration
- **DockerConfig**: Docker container and image settings

Supports loading/saving from YAML files and Python dictionaries.

### CLI (`cli.py`)

Command-line interface built with Click providing subcommands for:

- `configure`: Create and configure pipelines with interactive setup
- `build`: Build Docker images
- `start`: Start containers
- `stop`: Stop containers
- `status`: Check pipeline status
- `evaluate`: Run evaluation on pipelines

### Template Manager (`template_manager.py`)

Manages docker-compose and configuration templates:

- Merges component templates (middleware, ASR, MT) based on pipeline type
- Generates docker-compose files for different pipeline configurations
- Creates traefik reverse proxy configurations
- Generates dex OIDC server configurations
- Handles environment variable substitution

### Pipeline (`pipeline.py`)

Orchestrates pipeline lifecycle:

- Generates Dockerfiles from configuration
- Manages container lifecycle (start/stop)
- Provides pipeline status monitoring
- Handles environment configuration

### Docker Manager (`docker_manager.py`)

Wraps Docker Python SDK for:

- Building images
- Starting/stopping containers
- Managing volumes and ports
- Retrieving logs
- Checking container/image existence

### Evaluator (`evaluator.py`)

Framework for evaluating pipeline performance:

- Loads datasets (JSON/JSONL)
- Computes metrics
- Generates evaluation reports
- Supports custom evaluation logic

### Components

#### Speech Components (`components/speech/`)

- `SpeechComponent`: Abstract base class
- `WhisperComponent`: OpenAI Whisper implementation

#### LLM Components (`components/llm/`)

- `LLMComponent`: Abstract base class
- `OpenAIComponent`: OpenAI API implementation

## Configuration Flow

```
User Input (CLI or Config File)
         ↓
    PipelineConfig
         ↓
    Pipeline Instance
         ↓
    Docker Manager
         ↓
    Container Running
```

## Extension Points

### Adding New Speech Components

1. Inherit from `SpeechComponent` in `components/speech/__init__.py`
2. Implement the `transcribe()` method
3. Update the pipeline to instantiate your component

```python
class MyComponent(SpeechComponent):
    def transcribe(self, audio_path: str) -> str:
        # Implementation
        pass
```

### Adding New LLM Components

1. Inherit from `LLMComponent` in `components/llm/__init__.py`
2. Implement the `generate()` method
3. Update the pipeline to instantiate your component

```python
class MyComponent(LLMComponent):
    def generate(self, prompt: str) -> str:
        # Implementation
        pass
```

### Custom Evaluation Metrics

Extend the `Evaluator` class to add custom metric computation:

```python
class CustomEvaluator(Evaluator):
    def _evaluate_sample(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        # Custom evaluation logic
        pass
```

## Data Flow

```
Audio Input
    ↓
Speech Component (Whisper)
    ↓
Text Output
    ↓
LLM Component (GPT-3.5)
    ↓
Generated Response
    ↓
Evaluation Framework
    ↓
Metrics & Reports
```

## Deployment

PyParrot supports deployment via Docker:

1. **Configuration**: Define pipeline in YAML
2. **Build**: `pyparrot build --config config.yaml`
3. **Start**: `pyparrot start --config config.yaml`
4. **Monitor**: `pyparrot status --name pipeline-name`
5. **Evaluate**: `pyparrot evaluate --name pipeline-name --dataset data.json`

## State Management

- **Pipeline State**: Stored in Docker containers
- **Configuration State**: Persisted in YAML files
- **Evaluation Results**: Saved as JSON reports

## Error Handling

- Configuration validation via Pydantic
- Docker connectivity checks
- Container operation timeouts
- Dataset loading error handling
- Graceful degradation with logging

## Future Extensions

- REST API server for remote management
- Kubernetes deployment support
- Advanced metrics and monitoring
- Model serving optimization
- Multi-container orchestration
