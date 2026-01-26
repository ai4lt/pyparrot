# Getting Started with PyParrot

## Installation

### Prerequisites

- Python 3.9+
- Docker
- pip
- Git (for cloning with submodules)

### Clone the Repository

PyParrot uses Git submodules for component dependencies (like qbmediator). Clone with submodules:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/your-org/pyparrot.git
cd pyparrot

# If already cloned without submodules, initialize them:
git submodule update --init --recursive
```

### Install from Source

```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
pyparrot --help
```

## Project Components

### External Components (Git Submodules)

PyParrot uses Git submodules to manage external service components in the `components/` directory:

- **qbmediator** - Queue-based mediator for orchestrating components
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/qbmediator.git
  
- **kafka_post_task** - Kafka post-processing task handler (local component)
  - Location: `components/kafka_post_task/`
  
- **lt_api** - LT API service for handling requests
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt_api.git
  
- **lt_api_stream** - Streaming API for real-time processing
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt_api_stream.git
  
- **loggingwoker** - Logger service for handling and archiving logs
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/loggingwoker.git
  
- **ltfrontend** - Web frontend interface
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/ltfrontend.git
  
- **lt-archive** - Archive service for storing translations
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/lt-archive.git
  
- **streamingasr** - Streaming automatic speech recognition service
  - Repository: https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/streamingasr.git

These are included as submodules so you can:
- Modify component code locally during development
- Build components from source with `docker-compose --build`
- Update components independently while keeping them versioned with the main project

## Quick Start

### 1. Configure a Pipeline

Create a pipeline configuration from the command line:

```bash
pyparrot configure my-pipeline
```

This creates an interactive configuration with prompts for:
- Pipeline type (end2end, cascaded, LT.2025, BOOM)
- Domain (default: localhost)
- Port (default: 8001)
- Admin password (for dex OIDC)
- Website theme (default: default)

Example with options:

```bash
pyparrot configure my-pipeline \
  --type cascaded \
  --domain example.com \
  --port 8080
```

Or use the example configuration:

```bash
cp examples/config.yaml my-config.yaml
```

### 2. Build the Docker Image

Build an image for your pipeline:

```bash
pyparrot build --config my-config.yaml
```

This will:
- Generate a Dockerfile
- Create requirements.txt
- Build the Docker image

### 3. Start the Pipeline

Start a container from the image:

```bash
pyparrot start --config my-config.yaml
```

Check the status:

```bash
pyparrot status --name my-pipeline
```

### 4. Run Evaluation

Evaluate the pipeline on a dataset:

```bash
pyparrot evaluate \
  --name my-pipeline \
  --dataset examples/eval_dataset.json \
  --output results.json
```

### 5. Stop the Pipeline

Stop the running container:

```bash
pyparrot stop --name my-pipeline
```

## Configuration File Format

PyParrot uses YAML for configuration. See the structure below:

```yaml
name: my-pipeline
version: "1.0"
description: "My custom pipeline"

components:
  speech:
    model: whisper              # Speech model
    sample_rate: 16000          # Audio sample rate (Hz)
    language: en                # Language code
    device: cpu                 # Device (cpu/cuda)

  llm:
    model: gpt-3.5-turbo        # LLM model
    temperature: 0.7            # Generation temperature (0-2)
    max_tokens: 256             # Max tokens to generate
    api_key: ${OPENAI_API_KEY}  # Optional API key

docker:
  image_name: my-pipeline       # Docker image name
  base_image: python:3.11-slim  # Base Docker image
  port: 8000                    # Exposed port
  volumes:                      # Volume mappings
    /data: /app/data
  environment:                  # Environment variables
    LOG_LEVEL: INFO
    DEBUG: "false"
```

## Programmatic Usage

You can also use PyParrot as a Python library:

```python
from pyparrot.config import PipelineConfig
from pyparrot.pipeline import Pipeline
from pyparrot.evaluator import Evaluator

# Create configuration
config = PipelineConfig(
    name="my-pipeline",
    speech={"model": "whisper"},
    llm={"model": "gpt-3.5-turbo"},
)

# Create and manage pipeline
pipeline = Pipeline(config)
pipeline.build()
pipeline.start()

# Evaluate
evaluator = Evaluator("my-pipeline")
results = evaluator.evaluate("eval_dataset.json")

pipeline.stop()
```

## Common Tasks

### Load Configuration from File

```bash
pyparrot configure --config my-config.yaml
```

### View Pipeline Status

```bash
pyparrot status --name my-pipeline
```

### Run Tests

```bash
pytest tests/ -v
```

### Format Code

```bash
make format
```

### Run Linting

```bash
make lint
```

## Troubleshooting

### Docker Daemon Not Running

Error: `Error: Error while fetching server API version`

**Solution**: Start Docker daemon
```bash
# macOS
open /Applications/Docker.app

# Linux
sudo systemctl start docker
```

### Image Not Found

Error: `Error: No such image: pyparrot-pipeline:1.0`

**Solution**: Build the image first
```bash
pyparrot build --config my-config.yaml
```

### Port Already in Use

Error: `Error: Bind for 0.0.0.0:8000 failed`

**Solution**: Use a different port in config or stop the conflicting container
```bash
docker stop conflicting-container
```

### Missing Dependencies

Error: `ModuleNotFoundError: No module named 'click'`

**Solution**: Reinstall dependencies
```bash
pip install -e .
```

## Next Steps

- See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture
- Check [examples/](../examples/) for more examples
- Run tests: `pytest tests/ -v`
- Contribute: Create a fork and submit a PR
