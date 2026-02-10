defaultEntryPoints:
  - 'http'
{% if environment.ENABLE_HTTPS == 'true' %}
  - 'https'
{% endif %}

api:
  # Port for the status page
  dashboard: true

ping: {}

entryPoints:
  http:
    address: ':80'
{% if environment.ENABLE_HTTPS == 'true' %}
  https:
    address: ':443'
{% if environment.FORCE_HTTPS_REDIRECT == 'true' %}
    http:
      redirections:
        entryPoint:
          to: https
          scheme: https
{% endif %}
{% endif %}

{% if environment.ENABLE_HTTPS == 'true' and not IS_LOCALHOST_DOMAIN %}
# Let's Encrypt configuration for real domains
certificatesResolvers:
  letsencrypt:
    acme:
      email: {{ environment.ACME_EMAIL }}
      storage: /acme.json
{% if environment.ACME_STAGING == 'true' %}
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory
{% else %}
      caServer: https://acme-v02.api.letsencrypt.org/directory
{% endif %}
      httpChallenge:
        entryPoint: http
{% endif %}

providers:
  docker:
    watch: true
    exposedByDefault: false
    # match this with the value of $PIPELINE_NAME when not running as `main`
    constraints: "Label(`pipeline`,`CONFIG_NAME`)"
{% if environment.ENABLE_HTTPS == 'true' and IS_LOCALHOST_DOMAIN %}
  file:
    # Load self-signed certificates for localhost domains
    directory: /etc/traefik/certs
    watch: true
{% endif %}
