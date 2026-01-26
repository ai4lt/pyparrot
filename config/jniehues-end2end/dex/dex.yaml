# The base path of dex and the external name of the OpenID Connect service.
#
# This is the canonical URL that all clients MUST use to refer to dex. If a
# path is provided, dex's HTTP service will listen at a non-root URL.
issuer: {{ getenv "DEX_BASE_URL" }}/dex

grpc:
  addr: 0.0.0.0:5557

storage:
  type: sqlite3
  config:
    file: var/sqlite/dex.db

web:
  http: 0.0.0.0:5556

oauth2:
  skipApprovalScreen: true

staticClients:
- id: traefik-forward-auth
  redirectURIs:
  - {{ getenv "DEX_BASE_URL" }}/_oauth
  - http://{{ getenv "DOMAIN" }}/_oauth
  - https://{{ getenv "DOMAIN" }}/_oauth
  name: 'Lecture Translator'
  secret: {{ getenv "TFA_CLIENT_SECRET" }}

enablePasswordDB: true

staticPasswords:
- email: "admin@example.com"
  # bcrypt hash of the string "password"
  hash: {{ getenv "ADMIN_PASSHASH" }}
  username: "admin"
  userID: "7d3438dc-3f96-4661-be3f-331c01a967d6"

# Configuration for telemetry
telemetry:
  http: 0.0.0.0:5558
  # enableProfiling: true

