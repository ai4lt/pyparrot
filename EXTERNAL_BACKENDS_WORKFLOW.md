# External Backends Workflow

## Overview

The PyParrot CLI now supports external backend integration with a complete workflow:
1. Configuration via `pyparrot configure` command
2. Backend URLs stored in `.env` file
3. Automatic registration during `pyparrot start` command

**Supported Backend Types:**
- **STT (Speech-to-Text)**: Automatic registration as ASR component
- **MT (Machine Translation)**: Automatic registration as MT component  
- **TTS (Text-to-Speech)**: Automatic registration as TTS component
- **Summarizer**: Available via environment variable (no registration needed)

## Command Flow

### 1. Configure Pipeline with External Backends

```bash
pyparrot configure my-pipeline \
  --type end2end \
  --backends external \
  --stt-backend-url http://my-stt-server.com:5000 \
  --domain example.com \
  --port 8001
```

Or for cascaded with both STT and MT:

```bash
pyparrot configure my-pipeline \
  --type cascaded \
  --backends external \
  --stt-backend-url http://my-stt-server.com:5000 \
  --mt-backend-url http://my-mt-server.com:5000 \
  --domain example.com \
  --port 8001
```

Or for dialog with external TTS:

```bash
pyparrot configure my-pipeline \
  --type dialog \
  --backends external \
  --stt-backend-url http://my-stt-server.com:5000 \
  --tts-backend-url http://my-tts-server.com:5000 \
  --domain example.com \
  --port 8001
```

Or for any pipeline with external summarizer backend:

```bash
pyparrot configure my-pipeline \
  --type end2end \
  --backends external \
  --stt-backend-url http://my-stt-server.com:5000 \
  --summarizer-backend-url http://my-summarizer.com:3123 \
  --domain example.com \
  --port 8001
```

### 2. Generated .env File

The `.env` file in the config directory will contain:

```env
DOMAIN=example.com
FRONTEND_THEME=defaulttheme
HTTP_PORT=8001
DOMAIN_PORT=example.com:8001
EXTERNAL_PORT=8001
EXTERNAL_DOMAIN_PORT=example.com:8001
PIPELINE_NAME=my-pipeline
COMPONENTS_DIR=/Users/jniehues/src/pyparrot/components
HF_TOKEN=
BACKENDS=external
STT_BACKEND_URL=http://my-stt-server.com:5000
MT_BACKEND_URL=http://my-mt-server.com:5000
TTS_BACKEND_URL=http://my-tts-server.com:5000
SUM_BACKEND_URL=http://my-summarizer.com:3123
```

### 3. Start Pipeline with Automatic Backend Registration

```bash
pyparrot start my-pipeline
```

During start, the following operations occur:

1. Docker containers are started with `docker-compose up -d`
2. Redis groups are initialized:
   - `admin@example.com` added to `groups:admin`
   - `admin@example.com` added to `groups:presenter`
3. External backends are registered (if configured):
   - **STT Backend**: `curl` to `ltapi:5000/ltapi/register_worker` with:
     ```json
     {"component": "asr", "name": "mult57", "server": "http://my-stt-server.com:5000"}
     ```
   - **MT Backend**: `curl` to `ltapi:5000/ltapi/register_worker` with:
     ```json
     {"component": "mt", "name": "mt", "server": "http://my-mt-server.com:5000"}
     ```
   - **TTS Backend**: `curl` to `ltapi:5000/ltapi/register_worker` with:
     ```json
     {"component": "tts", "name": "tts", "server": "http://my-tts-server.com:5000"}
     ```

## Backend Modes

### local (default)
- All components run in Docker containers
- No external backends needed
- `BACKENDS=local` in .env

### distributed
- Components communicate via message queues
- All components still containerized
- `BACKENDS=distributed` in .env

### external
- External backend services for STT/MT/TTS
- Only requires URLs in configuration
- `BACKENDS=external` in .env
- Backend URLs stored in `.env` and read during start
- Automatic registration with ltapi service

## Backend Components by Pipeline Type

- **end2end**: Requires `stt` backend
- **cascaded**: Requires `stt` and `mt` backends
- **LT.2025**: Requires `stt` backend
- **dialog**: Requires `stt` backend
- **BOOM**: No specific backend requirements

## Implementation Details

### Configuration (cli.py)

```python
@main.command()
@click.option("--backends", type=click.Choice(["local", "distributed", "external"]))
@click.option("--stt-backend-url", default=None)
@click.option("--mt-backend-url", default=None)
@click.option("--tts-backend-url", default=None)
def configure(config_name, backends, stt_backend_url, mt_backend_url, tts_backend_url, ...):
    # Passed to template_manager.generate_env_file()
```

### Environment File Generation (template_manager.py)

```python
def generate_env_file(self, ..., backends="local", stt_backend_url=None, mt_backend_url=None, tts_backend_url=None):
  # Writes BACKENDS, STT_BACKEND_URL, MT_BACKEND_URL, TTS_BACKEND_URL to .env
```

### Start Command (cli.py)

```python
def start(config_name, component):
    # 1. Start containers with docker-compose up -d
    # 2. Initialize Redis groups
    # 3. If backends=external:
    #    - Register STT backend via curl (if url provided)
    #    - Register MT backend via curl (if url provided)
    #    - Register TTS backend via curl (if url provided)
```

## Configuration Model (config.py)

```python
class PipelineConfig(BaseModel):
    backends: str = "local"
    backend_components: List[str] = []
    stt_backend_url: Optional[str] = None
    mt_backend_url: Optional[str] = None
  tts_backend_url: Optional[str] = None
```

## Error Handling

The workflow includes graceful error handling:

- ⚠️ **Warning**: If backend registration fails, the pipeline continues running
- Messages indicate which backends were successfully registered
- Stderr is captured and displayed to the user

## Examples

### End-to-End with External STT

```bash
pyparrot configure prod-e2e \
  --type end2end \
  --backends external \
  --stt-backend-url http://192.168.1.100:5000 \
  --domain prod.example.com \
  --port 443 \
  --external-port 443

pyparrot start prod-e2e
# Output:
# ✓ Successfully started Docker containers
# ✓ Redis groups initialized (admin, presenter)
# Registering external backends...
# ✓ STT backend registered: http://192.168.1.100:5000
```

### Cascaded with Both STT and MT

```bash
pyparrot configure prod-cascaded \
  --type cascaded \
  --backends external \
  --stt-backend-url http://stt.internal:5000 \
  --mt-backend-url http://mt.internal:5000 \
  --domain prod.example.com

pyparrot start prod-cascaded
# Output:
# ✓ Successfully started Docker containers
# ✓ Redis groups initialized (admin, presenter)
# Registering external backends...
# ✓ STT backend registered: http://stt.internal:5000
# ✓ MT backend registered: http://mt.internal:5000
```

## Next Steps

- **Distributed backends**: Implement distributed backend mode with message queue routing
- **Local backends**: Implement local backend mode with containerized services
- **Health checks**: Add backend health checks before registering
- **Backend discovery**: Support dynamic backend discovery (e.g., from service registry)
- **Failover**: Support multiple backends with failover logic
