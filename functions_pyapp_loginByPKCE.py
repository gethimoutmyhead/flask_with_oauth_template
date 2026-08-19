"""Auth0 PKCE (Authorization Code + PKCE) token helper.

Opens the system browser for login, catches the redirect on a local
HTTP listener, then exchanges the authorization code for tokens.

Requires: requests  (pip install requests)

The redirect URI (http://localhost:<port>/callback) must be listed in
your Auth0 application's "Allowed Callback URLs".
"""

import base64
import hashlib
import secrets
import urllib.parse
import webbrowser
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests


def get_tokens_pkce(
    client_id: str,
    auth_server_url: str,
    audience: str,
    scope: str = "openid profile read:current_user",
    redirect_port: int = 4125,
    timeout: int = 300,
    login_hint: str = '',
) -> dict:
    """Run the Auth0 PKCE flow and return the token response.

    Args:
        client_id: Auth0 application (SPA/Native) client ID.
        auth_server_url: Tenant base URL, e.g. "https://your-tenant.au.auth0.com".
        audience: API identifier — always specify this so you get a JWT
            access token rather than an opaque one.
        scope: OAuth scopes (default "openid profile read:current_user").
        redirect_port: Local port for the callback listener.
        timeout: Seconds to wait for the user to complete login.

    Returns:
        dict with keys including "access_token", "id_token",
        "expires_in", "token_type" (and "refresh_token" if
        offline_access was requested).
    """
    base = auth_server_url.rstrip("/")
    logout_url = f"{base}/v2/logout?" + urllib.parse.urlencode(
        {"client_id": client_id}
    )
    webbrowser.open(logout_url)

    redirect_uri = f"http://localhost:{redirect_port}/callback"

    # --- PKCE verifier / challenge ---
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_urlsafe(16)

    # --- Build /authorize URL and open browser ---
    auth_url = f"{base}/authorize?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "audience": audience,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "login_hint":login_hint,
        }
    )

    # --- Local listener to catch the redirect ---
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            result.update({k: v[0] for k, v in params.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Login complete. You can close this tab.</body></html>")

        def log_message(self, *args):  # silence request logging
            pass

    server = HTTPServer(("localhost", redirect_port), CallbackHandler)
    server.timeout = timeout

    webbrowser.open(auth_url)
    # os.system(f"chrome -incognito {auth_url}")
    print(f"If the browser didn't open, visit:\n{auth_url}\n")

    server.handle_request()  # blocks until one request (the callback) arrives
    server.server_close()

    if "error" in result:
        if result["error"] == "access_denied":
            # User refused consent — clear the Auth0 SSO session so a
            # retry forces a fresh login instead of reusing the session.
            logout_url = f"{base}/v2/logout?" + urllib.parse.urlencode(
                {"client_id": client_id}
            )
            webbrowser.open(logout_url)
        raise RuntimeError(f"Auth0 error: {result['error']} — {result.get('error_description', '')}")
    if result.get("state") != state:
        raise RuntimeError("State mismatch — possible CSRF; aborting.")
    if "code" not in result:
        raise RuntimeError("No authorization code received (timed out or bad callback).")

    # --- Exchange code for tokens ---
    token_resp = requests.post(
        f"{base}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": result["code"],
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    token_resp.raise_for_status()
    return token_resp.json()


# if __name__ == "__main__":
#     tokens = get_tokens_pkce(
#         client_id="X6bsScVAOMzAWygoosDvqhsP1raE1cGV",
#         auth_server_url="https://dev-ei6babp7krz2qnk3.au.auth0.com",
#         audience="https://dev-ei6babp7krz2qnk3.au.auth0.com/api/v2/",
#     )
#     print("access_token:", tokens["access_token"][:40], "...")
#     print("id_token:", tokens["id_token"][:40], "...")
