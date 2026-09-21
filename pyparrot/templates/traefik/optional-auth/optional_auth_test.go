package tfa

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func optionalConfig(t *testing.T) {
	t.Helper()
	var err error
	config, err = NewConfig([]string{
		"--config=optional_auth_rules.ini",
		"--secret=isolated-test-secret",
		"--providers.google.client-id=test",
		"--providers.google.client-secret=test",
	})
	require.NoError(t, err)
	require.NoError(t, config.Providers.Google.Setup())
	for _, rule := range config.Rules {
		require.NoError(t, rule.Validate(config))
	}
}

func optionalRequest(path, state string) *http.Request {
	req := newHttpRequest("GET", "https://example.com/", path)
	// An untrusted incoming identity must never be reflected.
	req.Header.Set("X-Forwarded-User", "forged@example.com")
	switch state {
	case "valid":
		req.AddCookie(MakeCookie(req, "presenter@example.com"))
	case "expired":
		lifetime := config.Lifetime
		config.Lifetime = -time.Hour
		req.AddCookie(MakeCookie(req, "presenter@example.com"))
		config.Lifetime = lifetime
	case "invalid":
		req.AddCookie(&http.Cookie{Name: config.CookieName, Value: "invalid"})
	case "tampered":
		cookie := MakeCookie(req, "presenter@example.com")
		cookie.Value += "tampered"
		req.AddCookie(cookie)
	}
	return req
}

func TestOptionalPublicRoutes(t *testing.T) {
	optionalConfig(t)
	paths := []string{
		"/", "/favicon.ico", "/index/", "/index/home/", "/static/site.css", "/index/live/", "/archive/public",
		"/archivesession/123", "/archivemedia/123", "/archivemediafile/123",
		"/archive_messages/123", "/thumb/123", "/index/archive/",
		"/overview/meeting", "/session/123", "/about", "/legals", "/terms", "/contact",
		"/ltapi/123/getgraph", "/ltapi/stream",
		"/ltapi/123/audio/get_output_language_component",
		"/ltapi/123/get_previous_messages", "/ltapi/shorten",
	}
	for _, path := range paths {
		for _, state := range []string{"anonymous", "valid", "expired", "invalid", "tampered"} {
			t.Run(path+"/"+state, func(t *testing.T) {
				// Rebuild routes each time to exercise randomized map iteration order.
				recorder := httptest.NewRecorder()
				NewServer().RootHandler(recorder, optionalRequest(path, state))
				require.Equal(t, http.StatusOK, recorder.Code)
				require.Empty(t, recorder.Header().Get("Location"))
				user := ""
				if state == "valid" {
					user = "presenter@example.com"
				}
				require.Equal(t, user, recorder.Header().Get("X-Forwarded-User"))
				if state == "expired" || state == "invalid" || state == "tampered" {
					cookies := recorder.Result().Cookies()
					require.Len(t, cookies, 1)
					require.Equal(t, config.CookieName, cookies[0].Name)
					require.True(t, cookies[0].Expires.Before(time.Now()))
				}
			})
		}
	}
}

func TestOptionalProtectedRoutes(t *testing.T) {
	optionalConfig(t)
	for _, path := range []string{"/login", "/favicon.ico/private", "/create", "/meeting", "/upload_lecture", "/stop_sessions", "/index/settings/", "/archive_configure/123"} {
		for _, state := range []string{"anonymous", "valid", "expired", "invalid", "tampered"} {
			t.Run(path+"/"+state, func(t *testing.T) {
				req := optionalRequest(path, state)
				if path != "/login" {
					req.Header.Set("X-Forwarded-Method", "POST")
				}
				recorder := httptest.NewRecorder()
				NewServer().RootHandler(recorder, req)
				switch state {
				case "valid":
					require.Equal(t, http.StatusOK, recorder.Code)
					require.Equal(t, "presenter@example.com", recorder.Header().Get("X-Forwarded-User"))
				case "invalid", "tampered":
					require.Equal(t, http.StatusUnauthorized, recorder.Code)
				default:
					require.Equal(t, http.StatusTemporaryRedirect, recorder.Code)
				}
			})
		}
	}
}

func TestOptionalDisallowedIdentity(t *testing.T) {
	optionalConfig(t)
	config.Domains = []string{"allowed.example"}
	recorder := httptest.NewRecorder()
	NewServer().RootHandler(recorder, optionalRequest("/", "valid"))
	require.Equal(t, http.StatusOK, recorder.Code)
	require.Empty(t, recorder.Header().Get("X-Forwarded-User"))
}

func TestOptionalCallbackAndLogout(t *testing.T) {
	optionalConfig(t)
	for _, state := range []string{"anonymous", "valid", "expired"} {
		recorder := httptest.NewRecorder()
		NewServer().RootHandler(recorder, optionalRequest("/_oauth", state))
		require.Equal(t, http.StatusUnauthorized, recorder.Code)

		config.LogoutRedirect = "https://example.com/"
		recorder = httptest.NewRecorder()
		NewServer().RootHandler(recorder, optionalRequest("/_oauth/logout", state))
		require.Equal(t, http.StatusTemporaryRedirect, recorder.Code)
		require.Equal(t, config.LogoutRedirect, recorder.Header().Get("Location"))
		require.NotEmpty(t, recorder.Result().Cookies())
	}
}

func TestOptionalFaviconPreservesLoginCSRF(t *testing.T) {
	optionalConfig(t)
	server := NewServer()
	login := httptest.NewRecorder()
	server.RootHandler(login, optionalRequest("/login", "anonymous"))
	require.Equal(t, http.StatusTemporaryRedirect, login.Code)
	var csrf *http.Cookie
	for _, cookie := range login.Result().Cookies() {
		if cookie.Name == "_forward_auth_csrf" {
			csrf = cookie
		}
	}
	require.NotNil(t, csrf)
	favicon := httptest.NewRecorder()
	req := optionalRequest("/favicon.ico", "anonymous")
	req.AddCookie(csrf)
	server.RootHandler(favicon, req)
	require.Equal(t, http.StatusOK, favicon.Code)
	require.Empty(t, favicon.Header().Get("Location"))
	require.Empty(t, favicon.Result().Cookies())
}
