# Timestamped slide navigation

BOOM and BOOM-light set `VIDEO_SLIDE_SYNC=true` on the API and slide worker.
When a session has a slide stream, its original media input is additionally
routed to `slide:0`. ASR routing and video context are independent of this path.
Other pipeline configurations do not add this route.

## Event contract

```json
{
  "session": "42",
  "sender": "slide:0",
  "controll": "SLIDE_NAVIGATE",
  "slide_stream": "3",
  "upload_id": "0123456789abcdef0123456789abcdef",
  "page": 2,
  "start": 12.0,
  "source": "video",
  "live": false
}
```

- `page` is 1-based and belongs to `upload_id` in `slide_stream`.
- `start` is seconds on the media playback clock, **not** processing time or
  Unix wall time. A page remains active until the next event.
- `live: false` means analysis/replay data. It must not change the live Redis
  current page or navigate a viewer merely because the event arrived.
- `live: true` updates the current Redis page before publishing, and live
  synchronized viewers apply the page in the event directly.
- Legacy events without `start` still work live, but are not archived as timed
  navigation. Legacy notifications without `live` retain immediate behavior.
- `slide:0` is the graph node. `slide_stream` identifies presentation storage;
  it is not assumed to be `1`.

`SlideViewer.publish_navigation()` validates and publishes accepted changes.
Events for a replaced deck are ignored. Navigation no longer requires the
browser to make a separate Redis-state update request.

## Video sampling and embedding alignment

`components/streamingslide/video_sync.py` contains `VideoSlideJob` and
`sample_video()`. The worker copies inline or Redis-linked encoded media into
an owned temporary file before acknowledging it. A background job waits up to
300 seconds for the rendered deck, then decodes PNG samples at one-second media
intervals. It survives ASR's END message and closes its temporary file on
completion or failure. Repeated delivery of the same input in the worker
process does not start another job. Audio-only inputs produce no video frames.

With `IMAGE_EMBEDDING_BACKEND_URL` configured, `alignment.py` sends rendered
slides and sampled frames to the stateless GPU backend. It caches deck vectors
by upload ID and model version and compares normalized vectors on the CPU.
The initial acceptance settings are cosine similarity >= 0.93, a margin >= 0.02
over the runner-up, and two consecutive samples identifying the same page.
These are initial defaults requiring calibration on real recordings.
A confirmed change uses the first matching sample's media timestamp plus the
input's `start` offset. Backward navigation is allowed. Weak or ambiguous
matches and backend failures send no event and leave the current page unchanged.
There is no OCR or unknown-page event.

Without a backend URL the worker skips automatic video matching; manual
navigation remains available. See [backend setup](../backends/image-embeddings/README.md).

The current ingestion path accepts complete encoded files. A future live-video
producer must supply decodable media and playback-relative offsets, and mark
live input explicitly. This change does not add camera/screen capture or a
continuous live-video transport.

## Archive and frontend

The logger writes canonical timed navigation to
`slides/<upload_id>/timeline.json`. Writes are atomic, events are sorted by
`start`, and redelivery at the same timestamp replaces that entry. This also
works when navigation arrives before SLIDES_READY or after ASR completes.

The existing slide archive manifest includes a validated `timeline` for each
exposed deck. It requires no live Redis state and uses the existing archive
access checks. The current archive UI still exposes the latest uploaded deck.

The shared viewer provides `setTimeline()`, `pageAtTime()`, and `syncToTime()`.
The archive binds these to the media player's time and seek events. Before the
first timed event it displays page 1; archives without a timeline retain manual
navigation. A live viewer with an optional `config.media` element follows that
player's clock instead of applying events immediately.

Manual recording navigation uses a recording-relative clock based on captured
audio samples, excluding pauses and dropped queued packets, matching the
archive's concatenated recording. The existing wall-clock ASR input timestamps
are not modified. Hosts without a media-clock provider retain untimed navigation;
an embedding frontend can supply `config.getMediaTime()`.

## Activation and validation

Regenerate pipeline compose configuration and rebuild the API, slide worker,
logger, archive and frontend services. The slide image now includes FFmpeg.
No deployment or restart is performed by the source changes.

Focused checks:

```sh
python -m pytest -q tests/test_slide_sync.py tests/test_slide_archiving.py \
  tests/test_archive_slide_files.py tests/test_archive_slide_routes.py \
  tests/test_archive_recording_slides.py
node tests/slide_sync_js.cjs
```
