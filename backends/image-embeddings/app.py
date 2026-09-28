"""Stateless, bounded image embedding API. No session or slide state is stored."""
import base64
import binascii
from contextlib import asynccontextmanager
from io import BytesIO
import json
import logging
import os
import threading
import warnings

from fastapi import FastAPI, HTTPException, Request
from PIL import Image, ImageOps, UnidentifiedImageError
import numpy as np
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
MAX_BATCH = 16
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 20_000_000


def decode_image(encoded):
    if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
        raise HTTPException(413, 'Image exceeds the size limit')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(413, 'Invalid image size')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP'):
                    raise HTTPException(422, 'Only PNG, JPEG and WebP images are supported')
                if image.width * image.height > MAX_PIXELS:
                    raise HTTPException(413, 'Image exceeds the pixel limit')
                return ImageOps.exif_transpose(image).convert('RGB')
    except (binascii.Error, ValueError, OSError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise HTTPException(422, 'Invalid image') from error


def create_app(encoder=None):
    @asynccontextmanager
    async def lifespan(app):
        if encoder is None:
            from encoder import SiglipEncoder
            app.state.encoder = await run_in_threadpool(SiglipEncoder)
        else:
            app.state.encoder = encoder
        yield
        app.state.encoder = None

    app = FastAPI(lifespan=lifespan)
    app.state.encoder = None
    inference_slot = threading.BoundedSemaphore(1)

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    @app.get('/readyz')
    def ready():
        if app.state.encoder is None:
            raise HTTPException(503, 'Model is not loaded')
        return {'status': 'ready', 'model_version': app.state.encoder.model_version,
                'max_batch_size': MAX_BATCH}

    def embed(images):
        if app.state.encoder is None:
            raise HTTPException(503, 'Model is not loaded')
        if not inference_slot.acquire(blocking=False):
            raise HTTPException(429, 'Embedding worker is busy', headers={'Retry-After': '1'})
        decoded = []
        try:
            for image in images:
                decoded.append(decode_image(image))
            vectors = np.asarray(app.state.encoder.encode(decoded), dtype=np.float32)
            if vectors.ndim != 2 or vectors.shape[0] != len(images) or vectors.shape[1] == 0:
                raise ValueError('Invalid embedding shape')
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if not np.isfinite(vectors).all() or not np.isfinite(norms).all() or (norms <= 0).any():
                raise ValueError('Invalid embedding values')
            vectors = vectors / norms
            return {'model_version': app.state.encoder.model_version,
                    'embeddings': vectors.tolist()}
        except HTTPException:
            raise
        except Exception as error:
            logger.exception('Image embedding failed')
            raise HTTPException(503, 'Image embedding failed') from error
        finally:
            for image in decoded:
                image.close()
            inference_slot.release()

    @app.post('/embed/images')
    async def images(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                raise HTTPException(413, 'Request exceeds the size limit')
            body.extend(chunk)
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError) as error:
            raise HTTPException(422, 'Invalid JSON') from error
        batch = payload.get('images') if isinstance(payload, dict) else None
        if not isinstance(batch, list) or not 1 <= len(batch) <= MAX_BATCH:
            raise HTTPException(422, f'Provide between 1 and {MAX_BATCH} images')
        return await run_in_threadpool(embed, batch)

    return app


app = create_app()
