FROM dexidp/dex:latest

USER root

# Bundle Dex frontend overrides and LT themes into the image for non-debug runs.
COPY dex/frontend /srv/dex/frontend
COPY ltfrontend/ltweb/static/themes /opt/lt-themes
COPY dex/entrypoint.sh /usr/local/bin/dex-entrypoint.sh

RUN chmod +x /usr/local/bin/dex-entrypoint.sh \
    && mkdir -p /srv/dex/frontend/templates /srv/dex/frontend/static

ENTRYPOINT ["/usr/local/bin/dex-entrypoint.sh"]
