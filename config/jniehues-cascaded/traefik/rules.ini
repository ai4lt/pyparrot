default-action = auth

# set action to "auth" whenever the user is logged is (e.g. the authentication
# cookie is set), since otherwise (in case of action "allow")
# traefik-forward-auth doesn't send the username header value, but # at the
# same time take care not to replace the LogoutHandler for the # /_oauth/logout
# route.
rule.loggedin.action = auth
rule.loggedin.rule = HeadersRegexp("cookie", ".*_forward_auth=.*") && Path("/{path:$|[^_].*$|...............................................................................................................................................................................}")

rule.main.action = allow
rule.main.rule = Path("/") || PathPrefix("/static/") || PathPrefix("/index/live") || PathPrefix("/archive/") || PathPrefix("/index/archive") || PathPrefix("/overview/") || PathPrefix("/session/")

rule.ltapi.action = allow
rule.ltapi.rule = PathPrefix("/ltapi/{session:[0-9]+}/getgraph") || PathPrefix("/ltapi/stream") || PathPrefix("/ltapi/{session:[0-9]+}/{stream:[a-zA-Z0-9_]+}/get_output_language_component") || PathPrefix("/ltapi/{session:[0-9]+}/get_previous_messages") || PathPrefix("/ltapi/do_urlshortening") || PathPrefix("/ltapi/shorten")

