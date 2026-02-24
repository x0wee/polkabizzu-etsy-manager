#!/usr/bin/env python3
"""
Rate-limited HTTP client for Etsy Open API v3.

Handles:
- Authorization header injection
- Automatic retry on 429 (rate limit)
- JSON response parsing
- Error reporting

Base URL: https://openapi.etsy.com/v3
Docs: https://developers.etsy.com/documentation/reference/
"""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from .auth import load_token

load_dotenv()

BASE_URL = "https://openapi.etsy.com/v3"
API_KEY = os.getenv("ETSY_API_KEY")

# Etsy rate limit: 10 requests/second for most endpoints
REQUEST_INTERVAL = 0.12  # seconds between requests (conservative)


class EtsyClient:
    """Thin wrapper around requests for Etsy API v3."""

    def __init__(self):
        self._token = load_token()
        self._last_request_at = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key": API_KEY,
            "Authorization": f"Bearer {self._token['access_token']}",
            "Content-Type": "application/json",
        })

    def _throttle(self):
        """Enforce minimum interval between requests."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    def get(self, path: str, params: dict | None = None) -> dict:
        """GET request to Etsy API."""
        self._throttle()
        url = f"{BASE_URL}{path}"
        response = self._session.get(url, params=params, timeout=15)
        self._handle_response(response)
        return response.json()

    def patch(self, path: str, data: dict) -> dict:
        """PATCH request to Etsy API."""
        self._throttle()
        url = f"{BASE_URL}{path}"
        response = self._session.patch(url, json=data, timeout=15)
        self._handle_response(response)
        return response.json()

    def _handle_response(self, response: requests.Response):
        """Raise on HTTP errors with useful context."""
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            raise RuntimeError("Rate limited — retry the request.")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Etsy API error {response.status_code}: {response.text}"
            ) from exc
