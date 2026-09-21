package tfa

import "net/http"

// OptionalAuthHandler recognizes valid sessions without requiring a public visitor to log in.
func (s *Server) OptionalAuthHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Del("X-Forwarded-User")
		cookie, err := r.Cookie(config.CookieName)
		if err == nil {
			email, err := ValidateCookie(r, cookie)
			if err == nil && ValidateEmail(email) {
				w.Header().Set("X-Forwarded-User", email)
			} else {
				http.SetCookie(w, ClearCookie(r))
			}
		}
		w.WriteHeader(http.StatusOK)
	}
}
