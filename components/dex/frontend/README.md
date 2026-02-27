# Dex Frontend Overrides

This folder contains Dex-specific templates and static assets.

Dex parses templates from `/srv/dex/frontend/templates` and can only include
template files loaded from that directory.

## How this is wired

- `components/dex/Dockerfile` builds a Dex wrapper image.
- In non-debug runs, the image includes:
  - this frontend directory at `/srv/dex/frontend`
  - LT themes at `/opt/lt-themes`
- `entrypoint.sh` copies `${DEX_THEME_NAME}/html/*.dex.html` into
  `/srv/dex/frontend/templates/` so includes like
  `{{ template "header.dex.html" . }}` work without per-file mounts.

## Debug mode

When `DEBUG_MODE=true`, docker compose mounts directories instead of using baked
files:

- `${COMPONENTS_DIR}/dex/frontend:/srv/dex/frontend:ro`
- `${COMPONENTS_DIR}/ltfrontend/ltweb/static/themes/${FRONTEND_THEME:-defaulttheme}:/srv/dex/frontend/static/lt-theme:ro`

The same entrypoint sync still runs and copies `*.dex.html` partials from the
mounted theme into Dex templates.

## Starter files

- `templates/login.html`: starter page skeleton to adapt into Dex templates
- `static/styles.css`: placeholder stylesheet
