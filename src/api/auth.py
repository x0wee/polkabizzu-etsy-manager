#!/usr/bin/env python3
"""
Etsy OAuth 2.0 with PKCE authentication flow.

Etsy Open API v3 requires OAuth 2.0 with Proof Key for Code Exchange (PKCE).
This module handles the full auth cycle:
  1. Generate code_verifier + code_challenge
  2. Open browser to Etsy consent screen
  3. Listen for the callback on localhost
  4. Exchange authorization code for access token
  5. Persist token to disk for reuse

Docs: https://developers.etsy.com/documentation/essentials/authentication
"""

import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"

API_KEY = os.getenv("ETSY_API_KEY")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")
TOKEN_FILE = Path(os.getenv("TOKEN_FILE", ".etsy_token.json"))

# Scopes required by this tool
SCOPES = "listings_r listings_w"


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) for PKCE."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _build_auth_url(code_challenge: str, state: str) -> str:
    """Build the Etsy OAuth consent URL."""
    params = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "client_id": API_KEY,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{ETSY_AUTH_URL}?{urllib.parse.urlencode(params)}"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler to capture the OAuth callback."""

    auth_code = None
    state = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.auth_code = params.get("code", [None])[0]
        _CallbackHandler.state = params.get("state", [None])[0]

        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authentication successful!</h2>"
            b"<p>You can close this tab and return to the terminal.</p></body></html>"
        )

    def log_message(self, format, *args):
        pass  # Silence default HTTP server logs


def _exchange_code_for_token(auth_code: str, code_verifier: str) -> dict:
    """Exchange authorization code + verifier for access token."""
    response = requests.post(
        ETSY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": API_KEY,
            "redirect_uri": REDIRECT_URI,
            "code": auth_code,
            "code_verifier": code_verifier,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def authenticate() -> dict:
    """
    Run the full OAuth 2.0 PKCE flow.
    Returns the token dict and saves it to TOKEN_FILE.
    """
    if not API_KEY:
        raise ValueError("ETSY_API_KEY not set in .env")

    code_verifier, code_challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    auth_url = _build_auth_url(code_challenge, state)
    print(f"\nOpening browser for Etsy authorization...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Start local server to catch the redirect
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    print("Waiting for authorization callback on localhost:8080 ...")
    server.handle_request()

    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received.")
    if _CallbackHandler.state != state:
        raise RuntimeError("State mismatch — possible CSRF attack.")

    token = _exchange_code_for_token(_CallbackHandler.auth_code, code_verifier)
    TOKEN_FILE.write_text(json.dumps(token, indent=2))
    print(f"Token saved to {TOKEN_FILE}")
    return token


def load_token() -> dict:
    """Load token from disk, prompting re-auth if missing."""
    if not TOKEN_FILE.exists():
        print("No token found — starting authentication...")
        return authenticate()
    return json.loads(TOKEN_FILE.read_text())


if __name__ == "__main__":
    token = authenticate()
    print(f"\nAuthenticated. Token expires in {token.get('expires_in', '?')} seconds.")
