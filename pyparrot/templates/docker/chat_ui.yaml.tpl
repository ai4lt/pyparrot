version: '3.8'

services:
  chatfrontend:
    image: registry.isl.iar.kit.edu/chatfrontend
    build: ${COMPONENTS_DIR}/chatfrontend
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
      CHAT_BOTS_CONFIG: '/config/bots.json'
      {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
      DEBUG_MODE: 'true'
      {% endif %}
    volumes:
      - ${CHAT_BOTS_CONFIG_DIR}:/config:ro
    {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
      - ${COMPONENTS_DIR}/chatfrontend/chatweb:/src/chatweb
    {% endif %}
{% if IS_LOCALHOST_DOMAIN %}
    extra_hosts:
      - "${DOMAIN}:host-gateway"
{% endif %}
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.chatfrontend.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.chatfrontend.tls.certresolver=letsencrypt'
{% endif %}
      - 'traefik.http.routers.chatfrontend.entrypoints=http,https'
{% else %}
      - 'traefik.http.routers.chatfrontend.tls=false'
      - 'traefik.http.routers.chatfrontend.entrypoints=http'
{% endif %}
      - 'traefik.http.routers.chatfrontend.rule=Host(`${DOMAIN}`)'
      - 'traefik.http.services.chatfrontend.loadbalancer.server.port=5000'
      - 'traefik.http.routers.chatfrontend.middlewares=logout,traefik-forward-auth'
      - 'autoheal-app=true'
    restart: on-failure

networks:
  LTPipeline: {}
