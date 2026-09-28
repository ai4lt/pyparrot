# Image embedding backend

Stateless SigLIP GPU service for video-to-slide matching. Only model weights and
preprocessing live here; slide caching, comparisons, temporal confirmation and
navigation events live in `components/streamingslide`. No OCR is used.

## Configuration

Add these settings to a BOOM or BOOM-light pipeline YAML using local or
distributed backends:

```yaml
image_embedding_backend_engine: siglip
image_embedding_backend_model: ViT-B-16-SigLIP
image_embedding_backend_pretrained: webli
image_embedding_backend_gpu: "0"
```

Regenerate the pipeline configuration and build/start its services through the
usual pipeline workflow. The generated service joins the pipeline network;
streamingslide receives `http://image-embeddings:8010`. Existing backend settings
remain necessary. GPU selection is the host GPU ID exposed by Docker.

For an independently hosted backend, set this instead:

```yaml
image_embedding_backend_url: http://gpu-host:8010
```

An explicit URL takes precedence over creating a local service. All five fields
also have corresponding `--image-embedding-backend-*` configure options.
Without an URL or engine, automatic matching is disabled. Other pipeline types
do not enable this feature.

To run the standalone backend on the GPU host:

```sh
docker compose -f backends/image-embeddings/docker-compose.yml up --build -d
```

The image uses PyTorch 2.7.1 / torchvision 0.22.1 with CUDA 12.8 wheels,
including Blackwell support (such as RTX PRO 6000). Rebuild the image after
updating from the older CUDA 12.4 image.

This requires NVIDIA Container Toolkit and downloads model weights on first
startup. The named cache volume retains downloaded weights. Set
`IMAGE_EMBEDDING_BACKEND_GPU`, `IMAGE_EMBEDDING_BACKEND_MODEL`,
`IMAGE_EMBEDDING_BACKEND_PRETRAINED`, or `IMAGE_EMBEDDING_PORT` in the host
environment to override defaults. The standalone port defaults to 8010.
The API has no authentication; expose it only on a trusted backend network.
Model implementation uses [OpenCLIP](https://github.com/mlfoundations/open_clip).

## API

- `GET /healthz`: process health.
- `GET /readyz`: loaded model version and maximum batch size.
- `POST /embed/images`: `{"images": ["<base64 PNG/JPEG/WebP>", "..."]}`.
  Returns `{"model_version": "...", "embeddings": [[...], [...]]}` in input
  order. Vectors have unit L2 norm.

Limits: 16 images, 8 MiB decoded bytes per image, 20 million pixels per image,
32 MiB request body, one concurrent model inference. Busy requests return 429;
the client retries transient failures and splits batches by count and size.
The model version fingerprints weights, preprocessing and relevant library
versions. A model change forces the frontend to rebuild deck vectors.
No presentation or session data is retained by the API.

## Matching behavior

The frontend samples once per second and caches up to eight decks per worker
process. It requires similarity 0.93, a 0.02 lead over the second candidate and
two consecutive matching frames. Worker environment variables
`SLIDE_MATCH_THRESHOLD`, `SLIDE_MATCH_MARGIN`, and `SLIDE_MATCH_CONFIRMATIONS`
can override these initial settings. They require calibration against real
recordings, especially slides with small edits or camera views.

Confirmed changes use the first matching frame's media timestamp and the
existing `SLIDE_NAVIGATE` event. Weak, ambiguous or failed matches send no event.
Backward jumps are supported. This consumes the existing complete-file video
input path; it does not introduce a continuous live-video transport.
