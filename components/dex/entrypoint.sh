#!/bin/sh
set -eu

DEX_FRONTEND_DIR="${DEX_FRONTEND_DIR:-/srv/dex/frontend}"
DEX_THEME_NAME="${DEX_THEME_NAME:-defaulttheme}"
THEMES_ROOT="${THEMES_ROOT:-/opt/lt-themes}"
DEX_CONFIG_TEMPLATE="${DEX_CONFIG_TEMPLATE:-/etc/dex/config.docker.yaml}"
DEX_CONFIG_RENDERED="${DEX_CONFIG_RENDERED:-/tmp/dex-config.yaml}"
THEME_DIR="${THEMES_ROOT}/${DEX_THEME_NAME}"
THEME_HTML_DIR="${THEME_DIR}/html"
THEME_STATIC_TARGET="${DEX_FRONTEND_DIR}/static/lt-theme"
TEMPLATES_DIR="${DEX_FRONTEND_DIR}/templates"

mkdir -p "${TEMPLATES_DIR}" "${DEX_FRONTEND_DIR}/static"

# If no debug mount is present, hydrate theme assets from the bundled themes.
if [ ! -d "${THEME_STATIC_TARGET}" ] && [ -d "${THEME_DIR}" ]; then
  cp -a "${THEME_DIR}" "${THEME_STATIC_TARGET}"
fi

# In debug mode, theme files are mounted directly to static/lt-theme.
if [ ! -d "${THEME_HTML_DIR}" ] && [ -d "${THEME_STATIC_TARGET}/html" ]; then
  THEME_HTML_DIR="${THEME_STATIC_TARGET}/html"
fi

# Dex can only include templates it has parsed from its own template directory.
# Copy all theme *.dex.html partials into the Dex templates directory at startup.
if [ -d "${THEME_HTML_DIR}" ]; then
  for template in "${THEME_HTML_DIR}"/*.dex.html; do
    [ -e "${template}" ] || continue
    cp -f "${template}" "${TEMPLATES_DIR}/$(basename "${template}")"
  done
fi

escape_sed_replacement() {
  printf '%s' "$1" | sed -e 's/[&|]/\\&/g'
}

DEX_BASE_URL_ESCAPED="$(escape_sed_replacement "${DEX_BASE_URL:-}")"
DEX_FRONTEND_DIR_ESCAPED="$(escape_sed_replacement "${DEX_FRONTEND_DIR}")"
DOMAIN_ESCAPED="$(escape_sed_replacement "${DOMAIN:-}")"
TFA_CLIENT_SECRET_ESCAPED="$(escape_sed_replacement "${TFA_CLIENT_SECRET:-}")"
ADMIN_PASSHASH_ESCAPED="$(escape_sed_replacement "${ADMIN_PASSHASH:-}")"

sed \
  -e "s|{{ getenv \"DEX_BASE_URL\" }}|${DEX_BASE_URL_ESCAPED}|g" \
  -e "s|{{ getenv \"DEX_FRONTEND_DIR\" }}|${DEX_FRONTEND_DIR_ESCAPED}|g" \
  -e "s|{{ getenv \"DOMAIN\" }}|${DOMAIN_ESCAPED}|g" \
  -e "s|{{ getenv \"TFA_CLIENT_SECRET\" }}|${TFA_CLIENT_SECRET_ESCAPED}|g" \
  -e "s|{{ getenv \"ADMIN_PASSHASH\" }}|${ADMIN_PASSHASH_ESCAPED}|g" \
  "${DEX_CONFIG_TEMPLATE}" > "${DEX_CONFIG_RENDERED}"

exec /usr/local/bin/dex serve "${DEX_CONFIG_RENDERED}"
