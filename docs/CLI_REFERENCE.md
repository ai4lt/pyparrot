# PyParrot CLI Reference

## Overview

PyParrot provides a comprehensive CLI for managing Docker-based speech and LLM pipelines.

## Installation

```bash
pip install -e .
```

## Main Commands

### configure

Configure a new pipeline.

**Usage:**
```bash
pyparrot configure [OPTIONS]
```

**Options:**
```
  --config PATH              Path to YAML configuration file
  --name TEXT                Pipeline name (required without --config)
  --model TEXT              LLM model (default: gpt-3.5-turbo)
  --speech-model TEXT       Speech model (default: whisper)
  --sample-rate INTEGER     Audio sample rate (default: 16000)
  --temperature FLOAT       LLM temperature (default: 0.7)
  --output PATH             Save config to file
  --help                    Show help message
```

**Examples:**
```bash
# Configure from CLI options
pyparrot configure --name my-pipeline --model gpt-3.5-turbo --sample-rate 16000

# Configure from file
pyparrot configure --config config.yaml

# Configure and save to file
pyparrot configure --name my-pipeline --output my-config.yaml
```

---

### build

Build Docker images for a pipeline configuration using docker-compose.

**Usage:**
```bash
pyparrot build CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration (located in PYPARROT_CONFIG_DIR or ./config)
```

**Options:**
```
  -c, --component TEXT      Specific components to build (can be used multiple times). 
                            Default: build all components.
  --no-cache                Build without using cache
  --help                    Show help message
```

**Examples:**
```bash
# Build all components for a configuration
pyparrot build my-pipeline

# Build specific components only
pyparrot build my-pipeline -c kafka -c traefik

# Build without cache
pyparrot build my-pipeline --no-cache

# Build multiple specific components
pyparrot build my-pipeline -c qbmediator -c ltapi -c frontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- The configuration directory must contain a valid `docker-compose.yaml` file
- All components are built if no `--component` options are specified
- Component names must match service names in the docker-compose.yaml file
- Environment variables from the `.env` file in the config directory are automatically loaded

---

### compose-build

Build Docker images for a pipeline configuration using docker-compose.

**Usage:**
```bash
pyparrot compose-build CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration (located in PYPARROT_CONFIG_DIR or ./config)
```

**Options:**
```
  -c, --component TEXT      Specific components to build (can be used multiple times). 
                            Default: build all components.
  --no-cache                Build without using cache
  --help                    Show help message
```

**Examples:**
```bash
# Build all components for a configuration
pyparrot compose-build my-pipeline

# Build specific components only
pyparrot compose-build my-pipeline -c kafka -c traefik

# Build without cache
pyparrot compose-build my-pipeline --no-cache

# Build multiple specific components
pyparrot compose-build my-pipeline -c qbmediator -c ltapi -c frontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- The configuration directory must contain a valid `docker-compose.yaml` file
- All components are built if no `--component` options are specified
- Component names must match service names in the docker-compose.yaml file
- Environment variables from the `.env` file in the config directory are automatically loaded

---

### start

Start Docker containers for a pipeline configuration using docker-compose.

**Usage:**
```bash
pyparrot start CONFIG_NAME [OPTIONS]
```

**Arguments:**
```
  CONFIG_NAME               Name of the pipeline configuration (located in PYPARROT_CONFIG_DIR or ./config)
```

**Options:**
```
  -c, --component TEXT      Specific components to start (can be used multiple times). 
                            Default: start all components.
  --help                    Show help message
```

**Examples:**
```bash
# Start all containers for a configuration
pyparrot start my-pipeline

# Start specific components only
pyparrot start my-pipeline -c ltapi -c ltapi-stream

# Start multiple specific components
pyparrot start my-pipeline -c qbmediator -c ltapi -c frontend
```

**Environment Variables:**
- `PYPARROT_CONFIG_DIR`: Directory containing pipeline configurations (default: `./config`)

**Notes:**
- The configuration directory must contain a valid `docker-compose.yaml` file
- All components are started if no `--component` options are specified
- Component names must match service names in the docker-compose.yaml file
- Environment variables from the `.env` file in the config directory are automatically loaded
- Creates containers if they don't exist (uses `docker-compose up -d`)

---

### stop

Stop Docker containers for a pipeline configuration using docker-compose.

**Usage:**
```bash
pyparrot stop CONFIG_NAME [OPTIONS]
```

**Arguments:**
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
