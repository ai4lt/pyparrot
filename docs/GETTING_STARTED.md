# Getting Started with PyParrot

## Installation

### Prerequisites

- Python 3.9+
- Docker with compose support
- Git (for cloning with submodules)

### Clone the Repository

PyParrot uses Git submodules for component and backend dependencies:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/ai4lt/pyparrot.git
cd pyparrot

# If already cloned without submodules, initialize them:
git submodule update --init --recursive
```

### Install from Source

```bash
# Install in development mode
pip install -e .

# Install with development dependencies (optional)
pip install -e ".[dev]"
```

### Verify Installation

```bash
python -m pyparrot.cli --help
```

## Project Components

PyParrot uses Git submodules to manage external service components:

### Components (in `components/` directory)

Middleware services as Git submodules:
- **qbmediator** - Queue-based mediator for orchestrating components
- **lt_api** - LT API service for handling requests
- **lt_api_stream** - Streaming API for real-time processing
- **ltfrontend** - Web frontend interface
- **lt-archive** - Archive service for storing translations
- **loggingwoker** - Logger service for handling and archiving logs
- **streamingasr** - Streaming automatic speech recognition service
- **streamingmt** - Streaming machine translation service
- **kafka_post_task** - Kafka post-processing task handler

### Backends (in `backends/` directory)

Backend inference engines as Git submodules:
- **faster-whisper** - STT backend using faster-whisper for speech recognition

These are included as submodules so you can:
- Modify component code locally during development
- Build components from source
- Update components independently while keeping them versioned

## Quick Start

### 1. Configure a Pipeline

PyParrot supports different backend modes:

**Local backends (default)** - Backends run as Docker containers:
```bash
pyparrot configure my-pipeline --type end2end --backends local --stt-backend-gpu 0
```

**Distributed backends** - Backends use message queue routing:
```bash
pyparrot configure my-pipeline --type cascaded --backends distributed --stt-backend-gpu 0
```

**External backends** - Connect to remote backend services:
```bash
pyparrot configure my-pipeline --type end2end --backends external \
  --stt-backend-url http://my-stt-server:5008/asr \
  --mt-backend-url http://my-mt-server:5009/translate
```

Pipeline types:
- `end2end` - Speech-to-text only
- `cascaded` - Speech-to-text + Machine translation
- `LT.2025` - Full translation suite with TTS and dialog
- `dialog` - ASR + TTS + Dialog system
- `BOOM` - Basic ASR pipeline

Configuration options:
- `--domain` - Domain for the pipeline (default: pyparrot.localhost)
- `--port` - Internal Traefik port (default: 8001)
- `--external-port` - Public port if behind reverse proxy
- `--website-theme` - Frontend theme (default: defaulttheme)
- `--hf-token` - HuggingFace token for dialog components
- `--enable-https` - Enable HTTPS support
- `--https-port` - Port for HTTPS traffic (default: 443)
- `--acme-email` - Email for Let's Encrypt (required for production domains)
- `--acme-staging` - Use Let's Encrypt staging (for testing, avoids rate limits)
- `--force-https-redirect` - Redirect HTTP to HTTPS automatically

**HTTPS Examples:**

For local development with self-signed certificate:
```bash
pyparrot configure my-pipeline --enable-https --domain app.localhost
```

For production with Let's Encrypt:
```bash
pyparrot configure my-pipeline \
  --enable-https \
  --domain myapp.example.com \
  --acme-email admin@example.com \
  --force-https-redirect
```

For testing with Let's Encrypt staging (avoids rate limits):
```bash
pyparrot configure my-pipeline \
  --enable-https \
  --domain myapp.example.com \
  --acme-email admin@example.com \
  --acme-staging
```

**⚠️ Let's Encrypt Rate Limits:**
- Production: 50 certificates per domain per week
- Use `--acme-staging` for testing to avoid hitting limits
- **Certificates are shared across pipelines**:
  - Self-signed (localhost): Stored in `~/.pyparrot/certs/<domain>/`
  - Let's Encrypt: Stored in Docker volume `acme_data_<domain>`
  - Multiple pipelines using the same domain share the same certificate
  - Deleting a pipeline does NOT delete the shared certificate
  - Only manually deleting the volume/directory triggers new requests

The configure command will:
- Create a configuration directory under `config/<name>/`
- Generate docker-compose.yaml with selected components
- Create .env file with environment variables
- Generate authentication configs (Dex, Traefik)
- Prompt for admin password (for OIDC)

### 2. Build Docker Images

Build all components for your pipeline:

```bash
pyparrot build my-pipeline
```

Build specific components only:

```bash
pyparrot build my-pipeline -c ltapi -c ltfrontend
```

Build without cache:

```bash
pyparrot build my-pipeline --no-cache
```

### 3. Start the Pipeline

Start all containers:

```bash
pyparrot start my-pipeline
```

The start command will:
- Start all Docker containers with `docker-compose up -d`
- Wait for ltapi to be ready
- Initialize Redis user groups (admin, presenter)
- Register configured backends with ltapi

Access the frontend at `http://pyparrot.localhost:8001` (or your configured domain/port).

### 4. Manage the Pipeline

Check container status:
```bash
docker-compose -f config/my-pipeline/docker-compose.yaml ps
```

View logs:
```bash
docker-compose -f config/my-pipeline/docker-compose.yaml logs -f
```

Stop the pipeline:
```bash
pyparrot stop my-pipeline
```

Delete the pipeline (removes containers and volumes):
```bash
pyparrot delete my-pipeline
```

### 5. Backend Configuration

For **local** and **distributed** backends:
- Backends run as Docker containers within the pipeline
- STT backend URL is automatically set to `http://whisper-worker:5008/asr`
- Specify GPU with `--stt-backend-gpu 0` (or omit for CPU)
- Backend volumes (e.g., model cache) are automatically managed

For **external** backends:
- Provide URLs to remote backend services
- Example: `--stt-backend-url http://my-server:5008/asr`
- Backends are registered with ltapi on startup

## Backend Engines

### STT Backend: faster-whisper

Currently supported:
- Engine: `faster-whisper` (default)
- Model: `large-v2` (default)
- GPU support via `--stt-backend-gpu <device_id>`

The faster-whisper backend:
- Uses CUDA for GPU acceleration
- Caches models in Docker volume
- Supports CPU fallback if no GPU specified

### MT Backend

Currently configured via external URL only.
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
