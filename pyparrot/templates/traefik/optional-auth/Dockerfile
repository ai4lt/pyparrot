FROM golang:1.24.0-alpine AS builder
RUN apk add --no-cache git ca-certificates
WORKDIR /src
# Pin the existing proxy release; only the optional-auth extension is applied.
RUN git init && git remote add origin https://github.com/thomseddon/traefik-forward-auth.git \
    && git fetch --depth 1 origin 9e5994b959a4ea9868a7aa91f2f209bff43e68a6 \
    && git checkout --detach FETCH_HEAD
COPY optional-auth.patch /tmp/optional-auth.patch
RUN git apply --check /tmp/optional-auth.patch && git apply /tmp/optional-auth.patch
COPY optional_auth.go optional_auth_test.go internal/
COPY rules.ini internal/optional_auth_rules.ini
RUN go test ./internal/... && go test ./internal -run TestOptional -count=20
RUN CGO_ENABLED=0 go build -o /traefik-forward-auth ./cmd

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /traefik-forward-auth /traefik-forward-auth
USER 65532:65532
ENTRYPOINT ["/traefik-forward-auth"]
