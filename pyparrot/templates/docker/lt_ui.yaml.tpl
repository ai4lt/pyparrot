version: '3.8'

services:
  frontend:
    image: registry.isl.iar.kit.edu/ltfrontend
    build: ${COMPONENTS_DIR}/ltfrontend
    depends_on:
      - traefik
      - ltapi
      - ltapi-stream
    networks:
      - LTPipeline
    environment:
      QUEUE_SYSTEM: '${QUEUE_SYSTEM:-KAFKA}'
      API: 'http://ltapi:5000'
      API_STREAM: 'http://ltapi-stream:5000'
      API_EXTERNAL_HOST: '/webapi'
      ARCHIVE: 'http://archive:5000'
      THEME: '${FRONTEND_THEME:-defaulttheme}'
      REDIS_HOST: 'redis'
{% if environment.ENABLE_HTTPS == 'true' %}
      DOMAIN: 'https://${EXTERNAL_HTTPS_DOMAIN_PORT}'
{% else %}
      DOMAIN: 'http://${EXTERNAL_DOMAIN_PORT}'
{% endif %}
      SLIDE_SUPPORT: '${SLIDE_SUPPORT:-false}'
      {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
      DEBUG_MODE: 'true'
      {% endif %}
    {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
    volumes:
      - ${COMPONENTS_DIR}/ltfrontend/ltweb:/src/ltweb
    {% endif %}
{% if IS_LOCALHOST_DOMAIN %}
    extra_hosts:
      - "${DOMAIN}:host-gateway"
{% endif %}
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.frontend.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.frontend.tls.certresolver=letsencrypt'
{% endif %}
      - 'traefik.http.routers.frontend.entrypoints=http,https'
{% else %}
      - 'traefik.http.routers.frontend.tls=false'
      - 'traefik.http.routers.frontend.entrypoints=http'
{% endif %}
      - 'traefik.http.routers.frontend.rule=Host(`${DOMAIN}`)'
      - 'traefik.http.services.frontend.loadbalancer.server.port=5000'
      - 'traefik.http.routers.frontend.middlewares=logout,traefik-forward-auth'
      - 'autoheal-app=true'
    restart: on-failure

networks:
  LTPipeline: {}
