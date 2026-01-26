# PyParrot

CLI tool for managing Docker pipelines of speech and LLM components.

## Features

- **Configure**: Define pipeline configuration via CLI arguments or YAML config files
- **Build**: Build Docker images for your pipeline configuration
- **Manage**: Start and stop containers
- **Evaluate**: Run evaluation workflows on the pipeline

## Installation

### Clone Repository

PyParrot uses Git submodules for component dependencies. Clone the repository and initialize submodules:

```bash
# Clone the repository
git clone https://github.com/ai4lt/pyparrot.git
cd pyparrot

# Initialize and update submodules
git submodule update --init --recursive
```

### Install PyParrot

```bash
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Configure Pipeline

```bash
# From command line arguments
pyparrot configure --name my-pipeline --model gpt-3.5 --sample-rate 16000

# From config file
pyparrot configure --config config.yaml
```

### Build Docker Image

```bash
pyparrot build --config config.yaml
```

### Start Container

```bash
pyparrot start --name my-pipeline
```

### Stop Container

```bash
pyparrot stop --name my-pipeline
```

### Run Evaluation

```bash
pyparrot evaluate --name my-pipeline --dataset test_data.json
```

## Configuration File Format

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
  image_name: pyparrot-pipeline
  base_image: python:3.11-slim
  port: 8000
```

## Project Structure

```
pyparrot/
├── __init__.py
├── cli.py                 # CLI entry point
├── config.py              # Configuration management
├── docker_manager.py      # Docker operations
├── pipeline.py            # Pipeline logic
├── evaluator.py           # Evaluation framework
├── components/            # Component implementations
│   ├── speech/
│   └── llm/
└── tests/
    ├── test_config.py
    ├── test_docker_manager.py
    └── test_pipeline.py
```

## License

MIT
