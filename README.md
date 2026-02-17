# PyParrot

CLI tool for managing Docker-based speech translation pipelines with support for local, distributed, and external backends.

## Features

- **Configure**: Create pipeline configurations with docker-compose templates
- **Build**: Build Docker images for all pipeline components
- **Start/Stop**: Manage Docker containers with automatic backend registration
- **Delete**: Clean up pipeline resources including volumes
- **Status**: View pipeline and component status
- **Evaluate**: Run evaluation workflows on deployed pipelines

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Installation and quick start guide
- **[CLI Reference](docs/CLI_REFERENCE.md)** - Complete command documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and components
- **[Project Setup](docs/PROJECT_SETUP.md)** - Development and contribution guide

## Installation

### Clone Repository

PyParrot uses Git submodules for component dependencies. Clone the repository and initialize submodules:

```bash
# Clone the repository
git clone https://github.com/ai4lt/pyparrot.git
cd pyparrot

# Initialize and update submodules
git submodule sync --recursive
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

## Quick Start

### Configure a Pipeline

```bash
# Create an end-to-end pipeline with local backends
pyparrot configure my-pipeline --type end2end --port 8001

# Create a cascaded pipeline with specific GPU
pyparrot configure my-pipeline --type cascaded --backends local --stt-backend-gpu 0

# Create a pipeline with external backends
pyparrot configure my-pipeline --type end2end --backends external \
  --stt-backend-url http://my-stt-server:5008/asr \
  --mt-backend-url http://my-mt-server:5009/translate

# Enable HTTPS for localhost development (auto-generates self-signed certificate)
pyparrot configure my-pipeline --enable-https --domain app.localhost

# Enable HTTPS for production with Let's Encrypt
pyparrot configure my-pipeline \
  --enable-https \
  --domain myapp.example.com \
  --acme-email admin@example.com \
  --force-https-redirect
```

### Build and Start

```bash
# Build all components
pyparrot build my-pipeline

# Start the pipeline
pyparrot start my-pipeline

# Check status
pyparrot status my-pipeline
```

### Stop and Clean Up

```bash
# Stop the pipeline
pyparrot stop my-pipeline

# Delete pipeline and volumes
pyparrot delete my-pipeline
```

## Backend Modes

PyParrot supports three backend integration modes:

- **local**: Run backends as local Docker containers (default)
- **distributed**: Use message queue routing with local containers
- **external**: Connect to remote backend services via URLs

For local/distributed modes, specify:
- `--stt-backend-engine faster-whisper` (currently the only supported engine)
- `--stt-backend-model large-v2` (currently the only supported model)
- `--stt-backend-gpu <device_id>` (e.g., 0, 1, or omit for CPU)

## Project Structure

```
pyparrot/
├── pyparrot/
│   ├── cli.py                 # CLI entry point  
│   ├── config.py              # Configuration models
│   ├── template_manager.py    # Docker-compose template generation
│   ├── pipeline.py            # Pipeline logic (legacy)
│   ├── evaluator.py           # Evaluation framework
│   ├── docker_manager.py      # Docker operations (legacy)
│   ├── components/            # Component implementations
│   └── templates/             # Docker-compose and config templates
│       ├── docker/            # Service templates (middleware, asr, mt, etc.)
│       ├── dex/               # Dex OIDC templates
│       └── traefik/           # Traefik config templates
├── components/                # External service components (Git submodules)
│   ├── qbmediator/           # Queue-based mediator
│   ├── ltfrontend/           # Web frontend
│   ├── lt_api/               # LT API service
│   ├── lt_api_stream/        # Streaming API
│   ├── streamingasr/         # Streaming ASR service
│   ├── streamingmt/          # Streaming MT service
│   └── ...                   # Other components
├── backends/                  # Backend services (Git submodules)
│   └── faster-whisper/       # Faster-whisper STT backend
├── config/                    # Generated pipeline configurations
│   └── <config-name>/        # Each pipeline gets its own directory
│       ├── docker-compose.yaml
│       ├── .env
│       ├── dex/
│       └── traefik/
├── docs/                      # Documentation
└── tests/                     # Test suite
```

## License

MIT
