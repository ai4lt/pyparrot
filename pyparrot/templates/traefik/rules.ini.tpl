default-action = auth

# Public routes recognize valid sessions without requiring login.
# Browser favicon requests must not start a second login and replace the CSRF cookie.
# Do not add a competing cookie rule: optional handles both visitor states.
rule.main.action = optional
rule.main.rule = Path("/") || Path("/favicon.ico") || Path("/index/") || Path("/index/home/") || PathPrefix("/static/") || PathPrefix("/index/live") || PathPrefix("/archive/") || PathPrefix("/archivesession/") || PathPrefix("/archivemedia/") || PathPrefix("/archivemediafile/") || PathPrefix("/archive_messages/") || PathPrefix("/thumb/") || PathPrefix("/index/archive") || PathPrefix("/overview/") || PathPrefix("/session/") || Path("/about") || Path("/legals") || Path("/terms") || Path("/contact")

rule.ltapi.action = optional
rule.ltapi.rule = PathPrefix("/ltapi/{session:[0-9]+}/getgraph") || PathPrefix("/ltapi/stream") || PathPrefix("/ltapi/{session:[0-9]+}/{stream:[a-zA-Z0-9_]+}/get_output_language_component") || PathPrefix("/ltapi/{session:[0-9]+}/get_previous_messages") || PathPrefix("/ltapi/shorten")
