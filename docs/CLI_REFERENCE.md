# PyParrot CLI Reference

## Overview

PyParrot provides a CLI for managing Docker-based speech translation pipelines with support for multiple backend modes.

## Installation

```bash
pip install -e .
```

## Commands

### configure

Configure a new pipeline and generate docker-compose files.

**Usage:**
```bash
pyparrot configure CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration
```

**Options:**
```
  --type [end2end|cascaded|LT.2025|dialog|BOOM]
                            Pipeline type (default: end2end)
  --backends [local|distributed|external]
                            Backend integration mode (default: local)
  --stt-backend-url TEXT    External STT backend URL (for backends=external)
  --mt-backend-url TEXT     External MT backend URL (for backends=external)
  --stt-backend-engine [faster-whisper]
                            STT backend engine (default: faster-whisper)
  --stt-backend-model [large-v2]
                            STT model (default: large-v2)
  --stt-backend-gpu TEXT    GPU device ID for STT backend (e.g., 0, 1)
  --port INTEGER            Internal port Traefik listens on (default: 8001)
  --external-port INTEGER   Externally reachable port (for reverse proxy setups)
  --domain TEXT             Domain for the pipeline (default: pyparrot.localhost)
  --website-theme TEXT      Website theme (default: defaulttheme)
  --hf-token TEXT           HuggingFace token for dialog components
  --help                    Show help message
```

**Examples:**
```bash
# Basic end-to-end pipeline with local backends
pyparrot configure my-pipeline

# Cascaded pipeline with GPU-accelerated backends
pyparrot configure my-pipeline --type cascaded --backends local --stt-backend-gpu 0

# Pipeline with external backends
pyparrot configure my-pipeline --backends external \
  --stt-backend-url http://stt.example.com:5008/asr \
  --mt-backend-url http://mt.example.com:5009/translate

# Custom domain and port
pyparrot configure my-pipeline --domain example.com --port 8080 --external-port 443
```

**Backend Modes:**
- **local**: Backends run as Docker containers within the pipeline network
- **distributed**: Backends use message queue routing with local containers
- **external**: Backends are remote services accessed via HTTP URLs

**Notes:**
- Creates a directory under `config/` (or `$PYPARROT_CONFIG_DIR`) with generated files
- Generates `docker-compose.yaml`, `.env`, and authentication configs
- Prompts for admin password during first-time configuration
- For local/distributed modes, automatically sets internal backend URLs

---

### build

Build Docker images for a pipeline configuration.

**Usage:**
```bash
pyparrot build CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration
```

**Options:**
```
  -c, --component TEXT      Specific component(s) to build (can be used multiple times)
  --no-cache                Build without using cache
  --help                    Show help message
```

**Examples:**
```bash
# Build all components
pyparrot build my-pipeline

# Build specific components
pyparrot build my-pipeline -c ltapi -c ltfrontend

# Build without cache
pyparrot build my-pipeline --no-cache
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- Checks Docker daemon before building
- Uses docker-compose to build services defined in the generated configuration
- All components built if no `--component` option specified
- Component names must match service names in docker-compose.yaml

---

### start

Start Docker containers for a pipeline configuration.

**Usage:**
```bash
pyparrot start CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration
```

**Options:**
```
  -c, --component TEXT      Specific component(s) to start (can be used multiple times)
  --help                    Show help message
```

**Examples:**
```bash
# Start all containers
pyparrot start my-pipeline

# Start specific components
pyparrot start my-pipeline -c ltapi -c ltfrontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- Checks Docker daemon before starting
- Creates containers if they don't exist (uses `docker-compose up -d`)
- Waits for ltapi container to be ready before backend registration
- Automatically registers STT/MT backends with ltapi if configured
- Initializes Redis user groups (admin, presenter) on first start

---

### stop

Stop Docker containers for a pipeline configuration.

**Usage:**
```bash
pyparrot stop CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration
```

**Options:**
```
  -c, --component TEXT      Specific component(s) to stop (can be used multiple times)
  --help                    Show help message
```

**Examples:**
```bash
# Stop all containers
pyparrot stop my-pipeline

# Stop specific components
pyparrot stop my-pipeline -c ltapi -c ltfrontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- Uses `docker-compose stop` to gracefully stop containers
- Containers remain and can be restarted with `pyparrot start`
- Use `pyparrot delete` to remove containers and volumes

---

### delete

Delete a pipeline configuration and all its Docker resources.

**Usage:**
```bash
pyparrot delete CONFIG_NAME
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration
```

**Examples:**
```bash
# Delete pipeline
pyparrot delete my-pipeline
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- Stops and removes all containers for the pipeline
- Removes associated volumes with `-v` flag
- Requires user confirmation before deletion
- Does not delete the configuration directory itself

---

### status

Get the status of a pipeline (legacy command).

**Usage:**
```bash
pyparrot status NAME
```

**Arguments:**
```
  NAME                      Pipeline name
```

**Examples:**
```bash
# Get status
pyparrot status my-pipeline
```

**Notes:**
- This is a legacy command that loads config from older format
- For docker-compose-based pipelines, use `docker-compose ps` directly

---

### evaluate

Run evaluation on a pipeline (legacy command).

**Usage:**
```bash
pyparrot evaluate NAME [OPTIONS]
```

**Arguments:**
```
  NAME                      Pipeline name
```

**Options:**
```
  --dataset PATH            Path to evaluation dataset
  --output PATH             Path to save evaluation results
  --metrics TEXT            Metrics to compute (multiple)
  --help                    Show help message
```

**Examples:**
```
  CONFIG_NAME               Name of the pipeline configuration (located in PYPARROT_CONFIG_DIR or ./config)
```

**Options:**
```
  -c, --component TEXT      Specific components to stop (can be used multiple times). 
                            Default: stop all components.
  --help                    Show help message
```

**Examples:**
```bash
# Stop all containers for a configuration
pyparrot stop my-pipeline

# Stop specific components only
pyparrot stop my-pipeline -c ltapi -c ltapi-stream

# Stop multiple specific components
pyparrot stop my-pipeline -c qbmediator -c ltapi -c frontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- The configuration directory must contain a valid `docker-compose.yaml` file
- All components are stopped if no `--component` options are specified
- Component names must match service names in the docker-compose.yaml file
- Environment variables from the `.env` file in the config directory are automatically loaded

---

### status

Get the status of a pipeline.

**Usage:**
```bash
pyparrot status [OPTIONS]
```

**Options:**
```
  --name TEXT               Pipeline name (required)
  --help                    Show help message
```

**Examples:**
```bash
# Get status
pyparrot status --name my-pipeline
```

---

### evaluate

Run evaluation on a pipeline.

**Usage:**
```bash
pyparrot evaluate [OPTIONS]
```

**Options:**
```
  --name TEXT               Pipeline name (required)
  --dataset PATH            Path to evaluation dataset (required)
  --output PATH             Path to save evaluation results
  --metrics TEXT            Metrics to compute (multiple)
  --help                    Show help message
```

**Examples:**
```bash
# Evaluate pipeline
pyparrot evaluate --name my-pipeline --dataset eval_data.json

# Evaluate with custom output
pyparrot evaluate --name my-pipeline --dataset eval_data.json --output results.json

# Evaluate with specific metrics
pyparrot evaluate --name my-pipeline --dataset eval_data.json --metrics accuracy --metrics latency
```

---

## Global Options

```
  --version                 Show version
  --help                    Show help message
```

## Dataset Format

PyParrot supports JSON and JSONL dataset formats.

### JSON Format

```json
[
  {
    "input": "What is AI?",
    "expected": "Artificial Intelligence is..."
  },
  {
    "input": "Explain ML",
    "expected": "Machine Learning is..."
  }
]
```

### JSONL Format

```jsonl
{"input": "What is AI?", "expected": "Artificial Intelligence is..."}
{"input": "Explain ML", "expected": "Machine Learning is..."}
```

## Configuration File Format

```yaml
name: my-pipeline
version: "1.0"
description: "My pipeline"

components:
  speech:
    model: whisper
    sample_rate: 16000
    language: en
    device: cpu

  llm:
    model: gpt-3.5-turbo
    temperature: 0.7
    max_tokens: 256
    api_key: ${OPENAI_API_KEY}

docker:
  image_name: my-pipeline
  base_image: python:3.11-slim
  port: 8000
  volumes:
    /data: /app/data
  environment:
    LOG_LEVEL: INFO
```

## Common Workflows

### Complete Pipeline Setup

```bash
# 1. Configure
pyparrot configure --config config.yaml

# 2. Build
pyparrot build --config config.yaml

# 3. Start
pyparrot start --config config.yaml

# 4. Check status
pyparrot status --name my-pipeline

# 5. Evaluate
pyparrot evaluate --name my-pipeline --dataset eval_data.json --output results.json

# 6. Stop
pyparrot stop --name my-pipeline
```

### Development Workflow

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
make format

# Run linters
make lint
```

## Troubleshooting

### See help for any command

```bash
pyparrot [COMMAND] --help
```

### Enable debug output

Set `DEBUG=true` in `.env` or environment.

### View container logs

```bash
docker logs my-pipeline
```

### Clean up containers

```bash
docker stop my-pipeline
docker rm my-pipeline
```

## Performance Tips

1. Use GPU for faster speech recognition: `--device cuda`
2. Adjust temperature for more deterministic output: `--temperature 0.0`
3. Limit max tokens for faster generation: `--max-tokens 128`
4. Use smaller models for faster inference

## More Information

- See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [examples/](../examples/) for code samples
