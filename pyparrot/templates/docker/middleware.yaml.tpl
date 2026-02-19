version: '3.8'

services:
  traefik:
    image: 'traefik'
{% if environment.ENABLE_HTTPS == 'true' and not IS_LOCALHOST_DOMAIN %}
    user: '${HOST_UID:-0}:${HOST_GID:-0}'
    cap_add:
      - NET_BIND_SERVICE
    group_add:
      - '${DOCKER_GID:-0}'
{% endif %}
    volumes:
      - '/var/run/docker.sock:/var/run/docker.sock:ro'
      - './traefik/traefik.yaml:/etc/traefik/traefik.yaml:ro'
      - './traefik/auth/basicauth.txt:/basicauth.txt'
{% if environment.ENABLE_HTTPS == 'true' %}
{% if IS_LOCALHOST_DOMAIN %}
      - './traefik/certs:/etc/traefik/certs:ro'
      - './traefik/certs/certs.yaml:/etc/traefik/certs/certs.yaml:ro'
{% else %}
      - '${ACME_DATA_DIR}:/acme.json'
{% endif %}
{% endif %}
    ports:
      - '${HTTP_PORT:-80}:80'
{% if environment.ENABLE_HTTPS == 'true' %}
      - '${HTTPS_PORT:-443}:443'
{% endif %}
    networks:
      - LTPipeline
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
      - 'traefik.http.middlewares.basicauth.basicauth.usersFile=/basicauth.txt'
      # Traefik dashboard
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.traefik.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.traefik.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.traefik.tls=false'
{% endif %}
      - 'traefik.http.routers.traefik.rule=Host(`${DOMAIN}`) && (PathPrefix(`/dashboard`) || PathPrefix(`/api`))'
      - 'traefik.http.routers.traefik.service=api@internal'
      - 'traefik.http.routers.traefik.middlewares=basicauth'
    healthcheck:
      test: ["CMD", "traefik", "healthcheck", "--ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: 'unless-stopped'

  dex:
    image: dexidp/dex
    user: 'root'
    env_file:
      ${DEX_FILES:-.}/dex/dex.env
    environment:
      DOMAIN: "${DOMAIN}"
      HTTP_PORT: "${HTTP_PORT:-8001}"
{% if environment.ENABLE_HTTPS == 'true' %}
      DEX_BASE_URL: "https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}"
      DEX_ISSUER: "https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}"
{% else %}
      DEX_BASE_URL: "http://${EXTERNAL_DOMAIN_PORT:-${DOMAIN_PORT:-${DOMAIN}}}"
      DEX_ISSUER: "http://${EXTERNAL_DOMAIN_PORT:-${DOMAIN_PORT:-${DOMAIN}}}"
{% endif %}
      TFA_CLIENT_SECRET: "${TFA_CLIENT_SECRET:-bar}"
    volumes:
      - ./dex/dex.yaml:/etc/dex/config.docker.yaml:ro
      - dex_data:/var/sqlite
    networks:
      - LTPipeline
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.dex.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.dex.tls.certresolver=letsencrypt'
{% endif %}
      - 'traefik.http.routers.dex.entrypoints=http,https'
{% else %}
      - 'traefik.http.routers.dex.tls=false'
      - 'traefik.http.routers.dex.entrypoints=http'
{% endif %}
    {% if IS_LOCALHOST_DOMAIN %}
      - "traefik.http.routers.dex.rule=(Host(`${DOMAIN}`) || Host(`host.docker.internal`) || Host(`traefik`)) && PathPrefix(`/dex`)"
    {% else %}
      - "traefik.http.routers.dex.rule=Host(`${DOMAIN}`) && PathPrefix(`/dex`)"
    {% endif %}
      - "traefik.http.services.dex.loadbalancer.server.port=5556"

  traefik-forward-auth:
    image: 'thomseddon/traefik-forward-auth:latest'
    depends_on:
      traefik:
        condition: service_healthy
      dex:
        condition: service_started
    command: '--config /auth-rules.ini'
    environment:
      LOG_LEVEL: 'debug'
      DEFAULT_PROVIDER: oidc
      SECRET: "${TFA_SIGNING_SECRET:-XFxy833ngUuK7BgIfIQcot3Jb3H8oHdXrCfTTBCne8E}"
      PROVIDERS_OIDC_CLIENT_ID: traefik-forward-auth
      PROVIDERS_OIDC_CLIENT_SECRET: "${TFA_CLIENT_SECRET:-bar}"
{% if environment.ENABLE_HTTPS == 'true' %}
{% if IS_LOCALHOST_DOMAIN %}
      PROVIDERS_OIDC_ISSUER_URL: 'https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}/dex'
      LOGOUT_REDIRECT: 'https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}/'
      INSECURE_COOKIE: "false"
      INSECURE_SKIP_VERIFY: "true"
      AUTH_HOST: '${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}'
{% else %}
{% if environment.ACME_STAGING == 'true' %}
  PROVIDERS_OIDC_ISSUER_URL: 'http://dex:5556/dex'
{% else %}
      PROVIDERS_OIDC_ISSUER_URL: 'https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}/dex'
{% endif %}
      LOGOUT_REDIRECT: 'https://${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}/'
      INSECURE_COOKIE: "false"
      INSECURE_SKIP_VERIFY: "true"
      AUTH_HOST: '${EXTERNAL_HTTPS_DOMAIN_PORT:-${DOMAIN}:${HTTPS_PORT:-443}}'
{% endif %}
{% else %}
      PROVIDERS_OIDC_ISSUER_URL: 'http://${EXTERNAL_DOMAIN_PORT:-${DOMAIN}:${HTTP_PORT:-8001}}/dex'
      LOGOUT_REDIRECT: 'http://${EXTERNAL_DOMAIN_PORT:-${DOMAIN}}/'
      INSECURE_COOKIE: "true"
      AUTH_HOST: '${EXTERNAL_DOMAIN_PORT:-${DOMAIN}:${HTTP_PORT:-8001}}'
{% endif %}
      LIFETIME: 604800
      COOKIE_DOMAIN: "${DOMAIN}"
{% if IS_LOCALHOST_DOMAIN %}
    extra_hosts:
      - "${DOMAIN}:host-gateway"
{% endif %}
    volumes:
      - './traefik/rules.ini:/auth-rules.ini:ro'
{% if environment.ENABLE_HTTPS == 'true' %}
{% if IS_LOCALHOST_DOMAIN %}
      - './traefik/certs/cert.pem:/etc/ssl/certs/ca-certificates.crt:ro'
{% endif %}
{% endif %}
    networks:
      - LTPipeline
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
      - 'traefik.http.middlewares.traefik-forward-auth.forwardauth.address=http://traefik-forward-auth:4181'
      - 'traefik.http.middlewares.traefik-forward-auth.forwardauth.authResponseHeaders=X-Forwarded-User'
      - 'traefik.http.services.traefik-forward-auth.loadbalancer.server.port=4181'
      - 'traefik.http.middlewares.logout.replacepathregex.regex=^/logout$$'
      - 'traefik.http.middlewares.logout.replacepathregex.replacement=/_oauth/logout'
    restart: 'unless-stopped'

  zookeeper:
    image: 'bitnami/zookeeper:latest'
    #ports:
    #  - '2181:2181'
    environment:
      - ALLOW_ANONYMOUS_LOGIN=yes
    networks:
      - LTPipeline
    restart: on-failure

  kafka:
    image: 'bitnamilegacy/kafka:3.9.0'
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_CFG_ZOOKEEPER_CONNECT=zookeeper:2181
      - ALLOW_PLAINTEXT_LISTENER=yes
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CLIENT:PLAINTEXT,EXTERNAL:PLAINTEXT
      - KAFKA_CFG_LISTENERS=CLIENT://:9092,EXTERNAL://:${MEDIATOR_PORT:-9093}
      - KAFKA_CFG_ADVERTISED_LISTENERS=CLIENT://kafka:9092,EXTERNAL://localhost:${MEDIATOR_PORT:-9093}
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=CLIENT
      - KAFKA_ENABLE_KRAFT="false"
    depends_on:
     - zookeeper
    networks:
      - LTPipeline
    healthcheck:
        test: ["CMD-SHELL", "kafka-topics.sh --bootstrap-server localhost:9092 --list || exit 1"]
        interval: 5s
        timeout: 5s
        start_period: 5s
    restart: on-failure

  kafka_post_task:
    image: registry.isl.iar.kit.edu/kafka_post_task
    build: ${COMPONENTS_DIR}/kafka_post_task
    depends_on:
      kafka:
        condition: service_healthy
    networks:
      - LTPipeline

  redis:
    image: redis
    volumes:
      - 'redis_data:/data'
    networks:
      - LTPipeline
    restart: on-failure

  qbmediator:
    image: registry.isl.iar.kit.edu/qbmediator
    build: ${COMPONENTS_DIR}/qbmediator
    depends_on:
      redis:
        condition: service_started
      kafka_post_task:
        condition: service_completed_successfully
    environment:
      - QUEUE_SYSTEM=${QUEUE_SYSTEM:-KAFKA}
    command: python -u mediator.py --queue-server kafka --queue-port 9092 --redis-server redis
    networks:
      - LTPipeline
    restart: on-failure

  ltapi:
    image: registry.isl.iar.kit.edu/ltapi
    build: ${COMPONENTS_DIR}/lt_api
    depends_on:
      - qbmediator
    environment:
      - QUEUE_SYSTEM=${QUEUE_SYSTEM:-KAFKA}
      - QUEUE_SERVER=kafka
      - QUEUE_PORT=9092
    networks:
      - LTPipeline
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'

      - 'traefik.http.services.ltapi.loadbalancer.server.port=5000'

{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.ltapi.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.ltapi.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.ltapi.tls=false'
{% endif %}
      - 'traefik.http.routers.ltapi.rule=Host(`${DOMAIN}`) && PathPrefix(`/ltapi`)'
      - 'traefik.http.routers.ltapi.service=ltapi'
      - 'traefik.http.routers.ltapi.middlewares=basicauth'

{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.webapi.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.webapi.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.webapi.tls=false'
{% endif %}
      - 'traefik.http.routers.webapi.rule=Host(`${DOMAIN}`) && PathPrefix(`/webapi`)'
      - 'traefik.http.routers.webapi.service=ltapi'
      - 'traefik.http.routers.webapi.middlewares=webapi-compat,traefik-forward-auth'

      - 'traefik.http.middlewares.webapi-compat.replacepathregex.regex=^/webapi'
      - 'traefik.http.middlewares.webapi-compat.replacepathregex.replacement=/ltapi'
    restart: on-failure

  ltapi-stream:
    image: registry.isl.iar.kit.edu/ltapi-stream
    build: ${COMPONENTS_DIR}/lt_api_stream
    depends_on:
      - qbmediator
    networks:
      - LTPipeline
    environment:
      - QUEUE_SYSTEM=${QUEUE_SYSTEM:-KAFKA}
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'

      - 'traefik.http.services.ltapi-stream.loadbalancer.server.port=5000'

{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.ltapi-stream.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.ltapi-stream.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.ltapi-stream.tls=false'
{% endif %}
      - 'traefik.http.routers.ltapi-stream.rule=Host(`${DOMAIN}`) && PathPrefix(`/ltapi/stream`)'
      - 'traefik.http.routers.ltapi-stream.service=ltapi-stream'
      - 'traefik.http.routers.ltapi-stream.middlewares=basicauth'

{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.webapi-stream.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.webapi-stream.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.webapi-stream.tls=false'
{% endif %}
      - 'traefik.http.routers.webapi-stream.rule=Host(`${DOMAIN}`) && PathPrefix(`/webapi/stream`)'
      - 'traefik.http.routers.webapi-stream.service=ltapi-stream'
      - 'traefik.http.routers.webapi-stream.middlewares=webapi-compat,traefik-forward-auth'
    restart: on-failure

  streamingasr:
    image: registry.isl.iar.kit.edu/streamingasr
    build: ${COMPONENTS_DIR}/streamingasr
    depends_on:
      - qbmediator
    networks:
      - LTPipeline
    environment:
      - QUEUE_SYSTEM=${QUEUE_SYSTEM:-KAFKA}
      - QUEUE_SERVER=kafka
      - QUEUE_PORT=9092
    restart: on-failure

  log:
    image: registry.isl.iar.kit.edu/loggingwoker
    build: ${COMPONENTS_DIR}/loggingwoker
    depends_on:
      - qbmediator
    command: python -u logger.py --queue-server kafka --queue-port 9092 --redis-server redis --location /logs/
    networks:
      - LTPipeline
    environment:
      - QUEUE_SYSTEM=${QUEUE_SYSTEM:-KAFKA}
    restart: on-failure
    volumes:
      - logs:/logs
      - archive:/logs/archive

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
      DOMAIN: 'http://${environment.EXTERNAL_DOMAIN_PORT}'
{% endif %}
      SLIDE_SUPPORT: '${SLIDE_SUPPORT:-false}'
      {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
      DEBUG_MODE: 'true'
      {% endif %}
    {% if 'DEBUG_MODE' in environment and environment.DEBUG_MODE == 'true' %}
    volumes:
      - ${COMPONENTS_DIR}/ltfrontend/ltweb:/src/ltweb
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

  archive:
    image: registry.isl.iar.kit.edu/lt-archive
    build: ${COMPONENTS_DIR}/lt-archive
    networks:
      - LTPipeline
    environment:
      QUEUE_SYSTEM: '${QUEUE_SYSTEM:-KAFKA}'
      LT_ARCHIVE_DIR: '/data'
      REDIS_HOST: 'redis'
    volumes:
      - 'archive:/data'
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.archive.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.archive.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.archive.tls=false'
{% endif %}
      - 'traefik.http.routers.archive.rule=Host(`${DOMAIN}`) && PathPrefix(`/ltarchive`)'
      - 'traefik.http.services.archive.loadbalancer.server.port=5000'
      - 'traefik.http.routers.archive.middlewares=traefik-forward-auth'
      - 'autoheal-app=true'
    restart: on-failure

  mlflow:
    image: ghcr.io/mlflow/mlflow
    command: mlflow server --static-prefix /mlflow --host 0.0.0.0
    networks:
      - LTPipeline
    labels:
      - 'pipeline=${PIPELINE_NAME:-main}'
      - 'traefik.enable=true'
{% if environment.ENABLE_HTTPS == 'true' %}
      - 'traefik.http.routers.mlflow.tls=true'
{% if not IS_LOCALHOST_DOMAIN %}
      - 'traefik.http.routers.mlflow.tls.certresolver=letsencrypt'
{% endif %}
{% else %}
      - 'traefik.http.routers.mlflow.tls=false'
{% endif %}
      - 'traefik.http.routers.mlflow.rule=Host(`${DOMAIN}`) && PathPrefix(`/mlflow`)'
      - 'traefik.http.services.mlflow.loadbalancer.server.port=5000'
    volumes:
      - 'mlflow_data:/mlruns'

  autoheal:
    image: willfarrell/autoheal:latest
    network_mode: none
    environment:
      AUTOHEAL_CONTAINER_LABEL: autoheal-app
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock
    restart: always


networks:
  LTPipeline: {}
volumes:
  certs:
    name: 'certs'
  logs: {}
  archive: {}
  redis_data: {}
  mlflow_data: {}
  dex_data: {}
